#!/usr/bin/env python3
"""Mark the Studio's picks with the keyword "Studio pick", so they are easy to find in Lightroom.

The picks are the few photos Claude chose from a shoot for a first look and a
quick note to the client. Each one gets a small sidecar file next to it
(<same name>.xmp) carrying the keyword "Studio pick" and nothing else. Lightroom
reads it on import, and filtering by the keyword finds exactly the picks. No star
rating is written (Dustin, Oct 25): stars stay the photographer's.

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

    python3 mark_picks.py --night "<night folder or records>" [--picks picks.json] [--dry-run]
    python3 mark_picks.py --night "<night>" --files "2022-06-24 Black-sand beach/Black-sand-beach_0182_062422_2291.CR2" ...

--picks defaults to the night's records/picks.json ({"picks": [{"file": "<path from the drive folder>"}]}).
Every run is logged to records/picks-log.json before anything is written.
Exit codes: 0 done, 1 a problem (nothing written), 2 nothing to do.
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from where import locate  # noqa: E402

TOOL = "The Studio, by Horizon Found"
NO_SIDECAR = {".jpg", ".jpeg", ".heic", ".heif", ".dng", ".tif", ".tiff", ".png"}
KEYWORD = "Studio pick"
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
# what earlier versions wrote, byte for byte: only these may be replaced, and only by us
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
        text = sidecar.read_text()
    except (OSError, UnicodeDecodeError):
        return False
    return any(text == o.format(tool=TOOL, keyword=KEYWORD) for o in OLD_SIDECARS)


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


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
        return sidecar.read_text() == current()
    except (OSError, UnicodeDecodeError):
        return False


def rating_in(sidecar):
    try:
        text = sidecar.read_text(errors="replace")
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


def write_log(studio, entry):
    log = studio / "picks-log.json"
    data = []
    if log.exists():
        try:
            data = json.loads(log.read_text())
        except ValueError:
            data = []
    data.append(entry)
    tmp = log.with_name(log.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    os.replace(tmp, log)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--night", required=True)
    ap.add_argument("--picks")
    ap.add_argument("--files", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    root, studio = locate(a.night)
    if a.files:
        files = a.files
    else:
        pf = Path(a.picks) if a.picks else studio / "picks.json"
        if not pf.exists():
            say(f"STOP: no picks to mark ({pf} is not there).")
            return 1
        files = [p["file"] for p in json.loads(pf.read_text())["picks"]]

    todo, upgrade, skipped, problems = plan(root, files)
    if problems:
        say("STOP: nothing was written, because:")
        for p in problems:
            say("  " + p)
        return 1
    for f, why in skipped:
        say(f"Left alone: {Path(f).name} ({why}).")
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
    rel = lambda side: str(side.relative_to(root)) if side.is_relative_to(root) else str(side)

    write_log(studio, {"at": datetime.now().isoformat(timespec="seconds"),
                       "marked": [rel(side) for _, _, side in todo],
                       "updated": [rel(side) for _, _, side in upgrade],
                       "keyword": KEYWORD,
                       "skipped": [[f, why] for f, why in skipped]})
    made = 0
    for f, photo, side in todo:
        try:
            with open(side, "x") as fh:  # "x": never replaces a file that appeared meanwhile
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
        tmp.write_text(current())
        os.replace(tmp, side)
        updated += 1
    say(f"Done: {made} new, {updated} brought up to date. In Lightroom, filter by the keyword {KEYWORD!r} to jump to them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
