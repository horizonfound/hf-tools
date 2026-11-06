#!/usr/bin/env python3
"""The Canva half of a post kit: the file moves around Claude's Canva connector.

Claude talks to Canva through the Canva connector (connected once in claude.ai, no developer
account, works on Canva Pro). The connector does the thinking parts: find their Brand
Templates, read a template's fields, autofill, export. Two things it cannot do from a chat
are moving bytes, and that is what this script is for, on the photographer's own Mac:

    python3 canva_kit.py upload "<file>" --url "<single-use upload link from the connector>"
        POSTs the file's bytes to Canva. Prints {"mediaId": ...} on success (the asset id for autofill).
        One link, one file, once. Ask the connector for a fresh link for each file.

    python3 canva_kit.py fetch "<kit>" --into Carousel --urls urls.json [--names "Slide {n}"]
        Downloads a design export's files (the connector's list of download links, good for a day)
        into that folder of the kit, numbered in order. The Canva files go in as
        "Slide 01 (Canva).jpg" beside the Studio's own, and the kit page shows the Canva ones first.
        A fresh export (they fine-tuned the design in Canva, then said "export that again") takes
        the same names; the earlier Canva files are set aside, dated, in the kit's hidden folder.
        Nothing is ever deleted, and the Studio's own plain files are never touched.

    python3 canva_kit.py fetch "<kit>" --into Stories --start 2 --urls '["..."]'
        One story at a time: lands as "Story 02 (Canva).jpg"; the other stories are left alone.

    python3 canva_kit.py which "<kit>" --piece carousel|cover|story [--n 2]
        Which Canva design that piece is (so "export the beach carousel" needs no id).

    python3 canva_kit.py note "<kit>" --piece carousel|cover --design-id D... --edit-url "https://..." [--template "<name>"]
        Remembers which Canva design is which, so the kit page can say "Open in Canva".

    python3 canva_kit.py templates [--carousel ID --cover ID]
        Which of their Brand Templates the Studio uses for the carousel and the reel cover
        (asked once; kept in the Studio File under "canva").

Nothing here posts anything. The curl is the Mac's own.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit as kit_mod  # noqa: E402
import studio_file  # noqa: E402


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


def curl():
    c = shutil.which("curl")
    if not c:
        say("STOP: curl isn't on this computer, so I can't move files to Canva.")
        sys.exit(2)
    return c


def upload(path, url):
    p = Path(path)
    if not p.is_file():
        say(f"STOP: {p} isn't a file I can see.")
        return 2
    r = subprocess.run([curl(), "-sS", "-m", "180", "-X", "POST", "-H", "Content-Type: application/octet-stream",
                        "--data-binary", f"@{p}", url, "-w", "\n%{http_code}"], capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    if r.returncode != 0 or not code.startswith(("200", "201")):
        say(f"STOP: Canva didn't take {p.name} ({code or r.stderr.strip()[:120]}). Ask for a fresh upload link and try once more.")
        return 1
    try:
        d = json.loads(body)
    except ValueError:
        say(f"STOP: Canva answered with something I couldn't read for {p.name}.")
        return 1
    say(json.dumps(d))
    return 0


def set_aside_older(kit, into, folder, only=None):
    """A fresh export replaces the earlier Canva files under the same names. The earlier ones are
    moved (same drive, never deleted) into the kit's hidden folder, dated, so nothing is lost.
    `only`: just these file names (one story re-exported leaves the other stories alone)."""
    older = [p for p in folder.iterdir() if p.is_file() and " (Canva)" in p.name and not p.name.endswith(".part")
             and (only is None or p.name in only)]
    if not older:
        return None
    stamp = datetime.now().strftime("%Y-%m-%d %H%M%S")
    dest = kit / ".kit" / "canva-older" / f"{into} {stamp}"
    dest.mkdir(parents=True, exist_ok=True)
    for p in sorted(older):
        p.rename(dest / p.name)
    return dest


def fetch(kit, into, urls, names, start=1):
    folder = kit / into
    folder.mkdir(exist_ok=True)
    # Download everything first (as .part files), and only then swap the earlier Canva files out.
    # A failed download leaves the kit exactly as it was.
    pending = []
    for i, u in enumerate(urls, start):
        ext = ".jpg"
        m = re.search(r"\.(jpe?g|png|mp4|pdf)(?:\?|$)", u, re.I)
        if m:
            ext = "." + m.group(1).lower().replace("jpeg", "jpg")
        dst = folder / (names.format(n=f"{i:02d}") + f" (Canva){ext}")
        tmp = dst.with_name(dst.name + ".part")
        r = subprocess.run([curl(), "-sS", "-L", "-m", "300", "-o", str(tmp), u, "-w", "%{http_code}"], capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip().startswith("200") or not tmp.exists() or tmp.stat().st_size == 0:
            for _, t in pending + [(dst, tmp)]:
                if t.exists():
                    t.unlink()
            say(f"STOP: couldn't download file {i} from Canva ({r.stdout.strip() or r.stderr.strip()[:80]}). The links last a day; ask for a fresh export if it's older. Nothing in the kit changed.")
            return 1
        pending.append((dst, tmp))
    aside = set_aside_older(kit, into, folder, only=None if start == 1 and into != "Stories" else [d.name for d, _ in pending])
    got = []
    for dst, tmp in pending:
        tmp.rename(dst)
        got.append(dst.name)
    rec = kit_mod.load_rec(kit)
    c = rec.setdefault("canva", {})
    if into == "Stories" or start != 1:   # one at a time: keep the others listed
        had = [n for n in c.get("files", {}).get(into, []) if n not in got]
        got_all = sorted(set(had + got))
    else:
        got_all = got
    c.setdefault("files", {})[into] = got_all
    c.setdefault("fetched", {})[into] = datetime.now().isoformat(timespec="seconds")
    kit_mod.save_rec(kit, rec)
    kit_mod.write_page(kit)
    refresh_posting(kit)
    say(f"{len(got)} file{'s' if len(got) != 1 else ''} from Canva in {into}: " + ", ".join(got))
    if aside:
        say(f"The earlier Canva files from {into} were set aside (not deleted) in the kit's hidden folder.")
    return 0


def refresh_posting(kit):
    """If this kit's pieces are already in the posting queue, their thumbnails follow the fresh files."""
    try:
        import posting_queue as pq
        p = pq.load()
        if not any(Path(x.get("kit", "")).name == kit.name for x in p.get("pieces", [])):
            return
        pq.add_for_kit(p, kit)
        pq.save(p)
        pq.write_page(p)
    except Exception as e:  # the posting queue is a nicety here; the kit itself is already right
        say(f"(The posting queue's thumbnails weren't refreshed: {e})")


def design_for(kit, piece, n=None):
    """Which Canva design a kit's piece is, so 'export that again' needs no id from anyone.
    Stories are one design each: --piece story --n 2."""
    rec = kit_mod.load_rec(kit)
    if piece == "story":
        allst = (rec.get("canva") or {}).get("stories") or {}
        if n is None:
            say(json.dumps({"stories": allst, "into": "Stories"}))
            return 0 if allst else 1
        d = allst.get(str(n))
        if not d:
            say(json.dumps({"design_id": None, "note": f"This kit has no Canva story {n} yet."}))
            return 1
        say(json.dumps({"design_id": d.get("design_id"), "edit_url": d.get("edit_url"), "template": d.get("template"), "into": "Stories", "n": n}))
        return 0
    d = (rec.get("canva") or {}).get(piece)
    if not d:
        say(json.dumps({"design_id": None, "note": f"This kit has no Canva {piece} yet."}))
        return 1
    say(json.dumps({"design_id": d.get("design_id"), "edit_url": d.get("edit_url"), "template": d.get("template"),
                    "into": {"carousel": "Carousel", "cover": "Covers", "single": "Singles", "story": "Stories"}[piece]}))
    return 0


def note(kit, piece, design_id, edit_url, template, n=None):
    rec = kit_mod.load_rec(kit)
    c = rec.setdefault("canva", {})
    entry = {"design_id": design_id, "edit_url": edit_url, "template": template, "made": datetime.now().isoformat(timespec="seconds")}
    if piece == "story":
        c.setdefault("stories", {})[str(n or 1)] = entry
    else:
        if piece == "carousel":
            # which photos, in which order, these Canva slides were filled from: how the Assistant knows
            # later whether they still match the carousel (kit.canva_behind)
            entry["picks"] = list((rec.get("picks") or {}).get("carousel") or [])
        c[piece] = entry
    kit_mod.save_rec(kit, rec)
    kit_mod.write_page(kit)
    say(f"Noted: the {piece} is Canva design {design_id}. The kit page has an Open in Canva button for it.")


def templates(carousel, cover, story=None):
    sf = studio_file.load()
    c = sf.setdefault("canva", {})
    if carousel:
        c["carousel_template"] = carousel
    if cover:
        c["cover_template"] = cover
    if story:
        c["story_template"] = story
    if carousel or cover or story:
        sf["canva"] = c
        studio_file.save(sf)
    say(json.dumps({"carousel_template": c.get("carousel_template"), "cover_template": c.get("cover_template"), "story_template": c.get("story_template")}))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("upload"); u.add_argument("file"); u.add_argument("--url", required=True)
    f = sub.add_parser("fetch"); f.add_argument("kit"); f.add_argument("--into", required=True, choices=["Carousel", "Covers", "Singles", "Stories"])
    f.add_argument("--urls", required=True, help="a JSON file holding the list of download links, or the list itself")
    f.add_argument("--names", default=None, help='name pattern with {n}, e.g. "Slide {n}"')
    f.add_argument("--start", type=int, default=1, help="number the first file this (one story at a time: --into Stories --start 2)")
    n = sub.add_parser("note"); n.add_argument("kit"); n.add_argument("--piece", required=True, choices=["carousel", "cover", "single", "story"])
    n.add_argument("--design-id", required=True); n.add_argument("--edit-url", required=True); n.add_argument("--template"); n.add_argument("--n", type=int, help="which story (1, 2, 3...)")
    t = sub.add_parser("templates"); t.add_argument("--carousel"); t.add_argument("--cover"); t.add_argument("--story")
    w = sub.add_parser("which"); w.add_argument("kit"); w.add_argument("--piece", required=True, choices=["carousel", "cover", "single", "story"]); w.add_argument("--n", type=int)
    a = ap.parse_args()
    if a.cmd == "upload":
        return upload(a.file, a.url)
    if a.cmd == "templates":
        templates(a.carousel, a.cover, a.story); return 0
    k = kit_mod.find_kit(a.kit)
    if a.cmd == "fetch":
        raw = a.urls
        if Path(raw).is_file():
            raw = Path(raw).read_text()
        urls = json.loads(raw)
        if isinstance(urls, dict):
            urls = urls.get("urls") or urls.get("job", {}).get("urls") or []
        names = a.names or {"Carousel": "Slide {n}", "Covers": "Reel cover {n}", "Singles": "Single {n}", "Stories": "Story {n}"}[a.into]
        return fetch(k, a.into, urls, names, a.start)
    if a.cmd == "note":
        note(k, a.piece, a.design_id, a.edit_url, a.template, a.n); return 0
    if a.cmd == "which":
        return design_for(k, a.piece, a.n)


if __name__ == "__main__":
    sys.exit(main())
