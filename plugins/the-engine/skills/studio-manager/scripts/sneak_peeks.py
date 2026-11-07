#!/usr/bin/env python3
"""The sneak peeks: mark them for Lightroom and make their previews for the report.

The sneak peeks are the few photos Claude chose from a shoot, for variety and
flow, as the first thing the photographer sees in the report, the ones to edit
first, and the ones that go to the client with a note. Each gets a small sidecar
file next to it (<same name>.xmp) with the keyword "sneak peek" and nothing else,
so in Lightroom they are one filter away. No star rating is written (Dustin,
Oct 28): stars stay the photographer's, and a star filter would mix in older
one-star photos. The same photos are
made into small previews in the records (sneak-peeks/) and the report shows them
at the top.

Rules:
  - The photo itself is never changed. Only a new, small sidecar file is made.
  - A sidecar that is already there is never changed or replaced: it may hold
    the photographer's own rating or edits. That photo is skipped and named.
  - JPEG, HEIC, DNG, TIFF and PNG keep their ratings inside the file, which we
    never write into, so they are skipped and named (the page still shows them).
  - Safe to run twice: a photo that already has our current sidecar is left as is.
    A sidecar from an earlier version of this script is brought up to date only
    if it is still exactly what we wrote (Lightroom has not touched it).
  - A photo that is not where the records say stops the run before anything is written.

    python3 sneak_peeks.py --night "<night folder or records>" [--picks sneak-peeks.json] [--dry-run] [--no-previews]
    python3 sneak_peeks.py --night "<night>" --files "2022-06-24 Black-sand beach/Black-sand-beach_0182_062422_2291.CR2" ...

--picks defaults to the night's records/sneak-peeks.json:
  {"picks": [{"file": "<path from the drive folder>", "shoot": "s1", "why": "..."}], "picked_by": "..."}
("shoot" and "why" are optional; the older picks.json is read if that is all there is.)
Previews go to records/sneak-peeks/<photo name>.jpg with the Mac's own sips, or on a PC through
pictures.py (the JPEG inside the RAW, sized with Pillow), sidecars or not.
Every run is logged to records/picks-log.json before anything is written.
Exit codes: 0 done, 1 a problem (nothing written), 2 nothing to do.
"""
import argparse
import errno
import json
import os
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from where import locate  # noqa: E402
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
import pictures  # noqa: E402  (every small picture, on a Mac or a PC)
this_computer.utf8_output()

TOOL = "The Assistant, by Horizon Found"
OLD_TOOLS = ("The Studio, by Horizon Found",)   # the name until Nov 5; sidecars written then are still ours
NO_SIDECAR = {".jpg", ".jpeg", ".heic", ".heif", ".dng", ".tif", ".tiff", ".png"}
KEYWORD = "sneak peek"
OLD_KEYWORD = "Studio pick"   # what the Oct 25 version called them
SIDECAR = """<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="{tool}">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:dc="http://purl.org/dc/elements/1.1/">
   <dc:subject>
    <rdf:Bag>
     <rdf:li>{keyword}</rdf:li>
    </rdf:Bag>
   </dc:subject>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
"""
# what earlier versions wrote, byte for byte (with either keyword): only these may be replaced, and only by us
OLD_SIDECARS = ["""<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="{tool}">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmp:Rating="1">
   <dc:subject>
    <rdf:Bag>
     <rdf:li>{keyword}</rdf:li>
    </rdf:Bag>
   </dc:subject>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
""", """<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="{tool}">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
   xmp:Rating="1"/>
 </rdf:RDF>
</x:xmpmeta>
"""]


def current():
    return SIDECAR.format(tool=TOOL, keyword=KEYWORD)


def old_ours(sidecar):
    try:
        text = sidecar.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    tools = (TOOL,) + OLD_TOOLS
    if any(text == SIDECAR.format(tool=t, keyword=k) for t in tools for k in (OLD_KEYWORD, KEYWORD)) and text != current():
        return True
    return any(text == o.format(tool=t, keyword=k) for o in OLD_SIDECARS for t in tools for k in (OLD_KEYWORD, KEYWORD))


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass
    except OSError as e:
        # A PC only (as kit.py's say): Windows reports a reader that has gone away as "invalid argument" (EINVAL),
        # not as a broken pipe, and the work goes on, as it does on a Mac. A Mac raises anything else, as before.
        if not (this_computer.WINDOWS and e.errno == errno.EINVAL):   # unproven on a real PC
            raise


def existing_sidecar(photo):
    """The sidecar already beside this photo, whatever its case (.xmp or .XMP), or None."""
    want = (photo.stem + ".xmp").lower()
    try:
        for p in photo.parent.iterdir():
            if p.name.lower() == want:
                return p
    except OSError:
        pass
    return None


def ours(sidecar):
    try:
        return sidecar.read_text(encoding="utf-8") == current()
    except (OSError, UnicodeDecodeError):
        return False


def rating_in(sidecar):
    try:
        text = sidecar.read_text(errors="replace", encoding="utf-8")
    except OSError:
        return None
    i = text.find("xmp:Rating=")
    if i < 0:
        i = text.find("<xmp:Rating>")
        if i < 0:
            return None
        return text[i + 12:text.find("<", i + 12)].strip()
    q = text[i + 11]
    return text[i + 12:text.find(q, i + 12)]


def plan(root, files):
    todo, upgrade, skipped, problems = [], [], [], []
    for f in files:
        photo = Path(f) if os.path.isabs(f) else root / f
        if not photo.is_file():
            problems.append(f"{f}: not on the drive where the records say.")
            continue
        if photo.suffix.lower() in NO_SIDECAR:
            skipped.append((f, "this kind of file keeps its rating inside, which the Studio never writes into"))
            continue
        side = existing_sidecar(photo)
        if side:
            if ours(side):
                skipped.append((f, "already marked by the Studio"))
            elif old_ours(side):
                upgrade.append((f, photo, side))
            else:
                r = rating_in(side)
                skipped.append((f, f"already has a sidecar{' rated ' + r if r else ''}; left exactly as it is"))
            continue
        todo.append((f, photo, photo.with_suffix(".xmp")))
    return todo, upgrade, skipped, problems


def make_previews(root, files, studio, size=2000):
    """JPEGs of the sneak peeks for the report: the Mac's own sips, or on a PC the JPEG inside the RAW sized
    with Pillow (pictures.py). 2000 px on the long side, so the click-to-enlarge view on the report is sharp
    on a big screen (about 0.6 s and 400 KB each on a Mac; on a PC never bigger than what the camera stored).
    Returns (made, names)."""
    ok, words = pictures.ready()
    if not ok:
        say(f"No previews of the sneak peeks for the report yet: {words}")
        return 0, []
    out = studio / "sneak-peeks"
    out.mkdir(parents=True, exist_ok=True)
    names, made = [], 0
    for f in files:
        photo = Path(f) if os.path.isabs(f) else root / f
        dst = out / (photo.stem + ".jpg")
        if dst.exists():
            names.append(dst.name)
            continue
        if pictures.make_jpeg(photo, dst, size, 82):
            names.append(dst.name)
            made += 1
        else:
            why = pictures.why_not(photo)
            say(f"Could not make a preview of {photo.name} (the photo is fine; the report just won't show it)." + (f" {why}" if why else ""))
    return made, names


def set_aside_dropped(root, studio, files):
    """A photo that was a sneak peek and no longer is (the photographer chose different ones) loses the
    keyword: its sidecar, if it is still exactly ours, is moved (never deleted) into the records' folder
    sidecars-set-aside/, so Lightroom's filter shows only the current picks. A sidecar that is not ours
    any more (they rated or edited it in Lightroom) is left alone and named. Returns (moved, left)."""
    log = studio / "picks-log.json"
    try:
        entries = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
    except ValueError:
        entries = []
    marked = set()
    for e in entries:
        for rel in e.get("marked", []) + e.get("updated", []):
            marked.add(rel)
        for rel in e.get("set_aside", []):
            marked.discard(rel)
    want = set()
    for f in files:
        photo = Path(f) if os.path.isabs(f) else root / f
        # spelled with forward slashes like the log's records, on a PC too (where str() would give backslashes
        # and every current sneak peek would look dropped)
        want.add(photo.with_suffix(".xmp").relative_to(root).as_posix() if photo.is_relative_to(root) else str(photo.with_suffix(".xmp")))
    moved, left = [], []
    aside = studio / "sidecars-set-aside"
    for rel in sorted(marked - want):
        side = root / rel if not os.path.isabs(rel) else Path(rel)
        if not side.is_file():
            continue
        if not (ours(side) or old_ours(side)):
            left.append(rel)
            continue
        aside.mkdir(parents=True, exist_ok=True)
        dst = aside / (Path(rel).stem + "_" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".xmp")
        try:
            this_computer.replace(side, dst)
            moved.append(rel)
        except OSError as ex:
            left.append(f"{rel} ({ex})")
    if moved:
        write_log(studio, {"at": datetime.now().isoformat(timespec="seconds"), "set_aside": moved, "to": str(aside)})
    return moved, left


def write_log(studio, entry):
    log = studio / "picks-log.json"
    data = []
    if log.exists():
        try:
            data = json.loads(log.read_text(encoding="utf-8"))
        except ValueError:
            data = []
    data.append(entry)
    tmp = log.with_name(log.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    this_computer.replace(tmp, log)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--night", required=True)
    ap.add_argument("--picks")
    ap.add_argument("--files", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-previews", action="store_true", help="only the sidecars, no previews for the report")
    a = ap.parse_args()

    root, studio = locate(a.night)
    if a.files:
        files = a.files
    else:
        pf = Path(a.picks) if a.picks else studio / "sneak-peeks.json"
        if not pf.exists() and not a.picks and (studio / "picks.json").exists():
            pf = studio / "picks.json"
        if not pf.exists():
            say(f"STOP: no sneak peeks to mark ({pf} is not there).")
            return 1
        files = [p["file"] for p in json.loads(pf.read_text(encoding="utf-8"))["picks"]]

    todo, upgrade, skipped, problems = plan(root, files)
    if not a.dry_run and not a.files:
        moved, left = set_aside_dropped(root, studio, files)
        for rel in moved:
            say(f"No longer a sneak peek: {Path(rel).stem} (its keyword was set aside, not deleted).")
        for rel in left:
            say(f"Left alone: {Path(rel).stem} was a sneak peek before, but its sidecar has your own changes in it.")
    if problems:
        say("STOP: nothing was written, because:")
        for p in problems:
            say("  " + p)
        return 1
    for f, why in skipped:
        say(f"Left alone: {Path(f).name} ({why}).")
    if not a.dry_run and not a.no_previews:
        made, names = make_previews(root, files, studio)
        say(f"Previews for the report: {len(names)} ({made} new) in the records' sneak-peeks folder.")
    if not todo and not upgrade:
        say("Nothing to mark.")
        return 2
    if a.dry_run:
        for f, _, side in todo:
            say(f"Would mark: {Path(f).name} (new file {side.name})")
        for f, _, side in upgrade:
            say(f"Would update: {Path(f).name} ({side.name} is still exactly as the Studio wrote it)")
        say(f"Dry run: {len(todo)} new, {len(upgrade)} brought up to date; nothing was written.")
        return 0
    rel = lambda side: side.relative_to(root).as_posix() if side.is_relative_to(root) else str(side)

    write_log(studio, {"at": datetime.now().isoformat(timespec="seconds"),
                       "marked": [rel(side) for _, _, side in todo],
                       "updated": [rel(side) for _, _, side in upgrade],
                       "keyword": KEYWORD,
                       "skipped": [[f, why] for f, why in skipped]})
    made = 0
    for f, photo, side in todo:
        try:
            # "x": never replaces a file that appeared meanwhile. newline: the same bytes on a Mac and a PC.
            with open(side, "x", encoding="utf-8", newline="\n") as fh:
                fh.write(current())
            made += 1
        except FileExistsError:
            say(f"Left alone: {photo.name} (a sidecar appeared while working; not touched).")
    updated = 0
    for f, photo, side in upgrade:
        if not old_ours(side):  # changed since we planned: leave it
            say(f"Left alone: {photo.name} (its sidecar changed while working; not touched).")
            continue
        tmp = side.with_name(side.name + ".studio-partial")
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(current())
        this_computer.replace(tmp, side)
        updated += 1
    say(f"Done: {made} new, {updated} brought up to date. In Lightroom, filter by the keyword {KEYWORD!r} to jump to them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
