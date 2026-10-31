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

    python3 canva_kit.py which "<kit>" --piece carousel|cover
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


def set_aside_older(kit, into, folder):
    """A fresh export replaces the earlier Canva files under the same names. The earlier ones are
    moved (same drive, never deleted) into the kit's hidden folder, dated, so nothing is lost."""
    older = [p for p in folder.iterdir() if p.is_file() and " (Canva)" in p.name and not p.name.endswith(".part")]
    if not older:
        return None
    stamp = datetime.now().strftime("%Y-%m-%d %H%M%S")
    dest = kit / ".kit" / "canva-older" / f"{into} {stamp}"
    dest.mkdir(parents=True, exist_ok=True)
    for p in sorted(older):
        p.rename(dest / p.name)
    return dest


def fetch(kit, into, urls, names):
    folder = kit / into
    folder.mkdir(exist_ok=True)
    # Download everything first (as .part files), and only then swap the earlier Canva files out.
    # A failed download leaves the kit exactly as it was.
    pending = []
    for i, u in enumerate(urls, 1):
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
    aside = set_aside_older(kit, into, folder)
    got = []
    for dst, tmp in pending:
        tmp.rename(dst)
        got.append(dst.name)
    rec = kit_mod.load_rec(kit)
    c = rec.setdefault("canva", {})
    c.setdefault("files", {})[into] = got
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


def design_for(kit, piece):
    """Which Canva design a kit's piece is, so 'export that again' needs no id from anyone."""
    rec = kit_mod.load_rec(kit)
    d = (rec.get("canva") or {}).get(piece)
    if not d:
        say(json.dumps({"design_id": None, "note": f"This kit has no Canva {piece} yet."}))
        return 1
    say(json.dumps({"design_id": d.get("design_id"), "edit_url": d.get("edit_url"), "template": d.get("template"),
                    "into": {"carousel": "Carousel", "cover": "Covers", "single": "Singles", "story": "Stories"}[piece]}))
    return 0


def note(kit, piece, design_id, edit_url, template):
    rec = kit_mod.load_rec(kit)
    c = rec.setdefault("canva", {})
    c[piece] = {"design_id": design_id, "edit_url": edit_url, "template": template, "made": datetime.now().isoformat(timespec="seconds")}
    kit_mod.save_rec(kit, rec)
    kit_mod.write_page(kit)
    say(f"Noted: the {piece} is Canva design {design_id}. The kit page has an Open in Canva button for it.")


def templates(carousel, cover):
    sf = studio_file.load()
    c = sf.setdefault("canva", {})
    if carousel:
        c["carousel_template"] = carousel
    if cover:
        c["cover_template"] = cover
    if carousel or cover:
        sf["canva"] = c
        studio_file.save(sf)
    say(json.dumps({"carousel_template": c.get("carousel_template"), "cover_template": c.get("cover_template")}))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("upload"); u.add_argument("file"); u.add_argument("--url", required=True)
    f = sub.add_parser("fetch"); f.add_argument("kit"); f.add_argument("--into", required=True, choices=["Carousel", "Covers", "Singles", "Stories"])
    f.add_argument("--urls", required=True, help="a JSON file holding the list of download links, or the list itself")
    f.add_argument("--names", default=None, help='name pattern with {n}, e.g. "Slide {n}"')
    n = sub.add_parser("note"); n.add_argument("kit"); n.add_argument("--piece", required=True, choices=["carousel", "cover", "single", "story"])
    n.add_argument("--design-id", required=True); n.add_argument("--edit-url", required=True); n.add_argument("--template")
    t = sub.add_parser("templates"); t.add_argument("--carousel"); t.add_argument("--cover")
    w = sub.add_parser("which"); w.add_argument("kit"); w.add_argument("--piece", required=True, choices=["carousel", "cover", "single", "story"])
    a = ap.parse_args()
    if a.cmd == "upload":
        return upload(a.file, a.url)
    if a.cmd == "templates":
        templates(a.carousel, a.cover); return 0
    k = kit_mod.find_kit(a.kit)
    if a.cmd == "fetch":
        raw = a.urls
        if Path(raw).is_file():
            raw = Path(raw).read_text()
        urls = json.loads(raw)
        if isinstance(urls, dict):
            urls = urls.get("urls") or urls.get("job", {}).get("urls") or []
        names = a.names or {"Carousel": "Slide {n}", "Covers": "Reel cover {n}", "Singles": "Single {n}", "Stories": "Story {n}"}[a.into]
        return fetch(k, a.into, urls, names)
    if a.cmd == "note":
        note(k, a.piece, a.design_id, a.edit_url, a.template); return 0
    if a.cmd == "which":
        return design_for(k, a.piece)


if __name__ == "__main__":
    sys.exit(main())
