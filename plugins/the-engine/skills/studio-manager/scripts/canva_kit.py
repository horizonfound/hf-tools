#!/usr/bin/env python3
"""The Canva half of a post kit: the file moves around Claude's Canva connector.

Claude talks to Canva through the Canva connector (connected once in claude.ai, no developer
account, works on Canva Pro). The connector does the thinking parts: find their Brand
Templates, read a template's fields, autofill, export. Two things it cannot do from a chat
are moving bytes, and that is what this script is for, on the photographer's own computer:

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
        (On a PC, always put the list in a file and pass the file: quotes inside a list can be lost
        on the way into a script there.)

    python3 canva_kit.py which "<kit>" --piece carousel|cover|story [--n 2]
        Which Canva design that piece is (so "export the beach carousel" needs no id).

    python3 canva_kit.py note "<kit>" --piece carousel|cover --design-id D... --edit-url "https://..." [--template "<name>"]
        Remembers which Canva design is which, so the kit page can say "Open in Canva".

    python3 canva_kit.py templates [--carousel ID --cover ID]
        Which of their Brand Templates the Studio uses for the carousel and the reel cover
        (asked once; kept in the Studio File under "canva").

Nothing here posts anything. The curl is the computer's own: a Mac comes with it, and so do Windows 10 and 11.
"""
import argparse
import errno
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit as kit_mod  # noqa: E402
import studio_file  # noqa: E402
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)


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


def curl():
    c = None
    if this_computer.WINDOWS:
        # unproven on a real PC. Windows 10 (from build 17063, 2018) and Windows 11 come with curl.exe in
        # System32 (Microsoft, "Tar and Curl Come to Windows!"). It is asked for by its full path, so a curl.exe
        # sitting in the current folder is never the one that runs; and since subprocess starts the program
        # itself, with no shell, PowerShell's own "curl" (its other name for Invoke-WebRequest) never comes in.
        own = Path(os.environ.get("SystemRoot") or r"C:\Windows") / "System32" / "curl.exe"
        if own.is_file():
            c = str(own)
    c = c or shutil.which("curl")
    if not c:
        say("STOP: curl isn't on this computer, so I can't move files to Canva.")
        sys.exit(2)
    return c


def upload(path, url):
    p = Path(path)
    if not p.is_file():
        say(f"STOP: {p} isn't a file I can see.")
        return 2
    # The bytes reach curl through its input ("--data-binary @-", which curl reads in binary on both computers),
    # never by the file's name: curl.exe on a PC may not open a name with letters outside the PC's own code page
    # (an emoji, a Polish ł), and this way the name never reaches curl at all. Canva gets the same bytes either way.
    try:
        f = open(p, "rb")
    except OSError as e:
        say(f"STOP: I couldn't read {p.name} ({e.strerror or e}).")
        return 2
    with f:
        r = subprocess.run([curl(), "-sS", "-m", "180", "-X", "POST", "-H", "Content-Type: application/octet-stream",
                            "--data-binary", "@-", url, "-w", "\n%{http_code}"], stdin=f, capture_output=True,
                           encoding="utf-8", errors="replace")
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


def _fold(name):
    """A name the way a drive that ignores capitals sees it, with accented letters spelled one way (a Mac drive can
    keep "ë" as one letter or as "e" plus a mark): "slide 01 (canva).JPG" and "Slide 01 (Canva).jpg" are one name there."""
    return unicodedata.normalize("NFC", name).casefold()


def _in_the_way(folder, coming, older):
    """Files the drive would take for one of the fresh names although they are spelled differently ("slide 01
    (canva).jpg" on a drive that ignores capitals, as most Mac drives and every PC drive do). Left there, the fresh
    file would be written over it on a Mac, or refused on a PC; so it is set aside with the earlier ones instead."""
    listing = list(folder.iterdir())
    names = {p.name for p in listing}
    taken = {p.name for p in older}
    extra = []
    for d in coming:
        if d.name in names or not os.path.lexists(d):   # the exact name is there (already set aside), or nothing is
            continue
        for p in listing:
            if p.name not in taken and _fold(p.name) == _fold(d.name) and p.is_file() and not p.name.endswith(".part"):
                extra.append(p)
                taken.add(p.name)
    return extra


def _older(folder, only=None, coming=()):
    """The files a fresh export sets aside: the earlier Canva files (`only`: just these names), and anything the
    drive takes for one of the fresh names (`coming`)."""
    older = [p for p in folder.iterdir() if p.is_file() and " (Canva)" in p.name and not p.name.endswith(".part")
             and (only is None or p.name in only)]
    return older + _in_the_way(folder, coming, older)


def set_aside_older(kit, into, folder, only=None, coming=(), moved=None):
    """A fresh export replaces the earlier Canva files under the same names. The earlier ones are
    moved (same drive, never deleted) into the kit's hidden folder, dated, so nothing is lost.
    `only`: just these file names (one story re-exported leaves the other stories alone).
    `coming`: the fresh files' places; anything the drive takes for one of them goes aside too.
    `moved`: a list that gets (the file, where it went) as each goes aside, so a stop part way still says what moved."""
    older = _older(folder, only, coming)
    if not older:
        return None
    stamp = datetime.now().strftime("%Y-%m-%d %H%M%S")
    dest = kit / ".kit" / "canva-older" / f"{into} {stamp}"
    dest.mkdir(parents=True, exist_ok=True)
    for p in sorted(older):
        # Never over a file already set aside (two exports within one second share the dated folder): the
        # later one then gets " (2)". On a PC a file held open for a moment gets a few short waits.
        target, k = dest / p.name, 2
        while not this_computer.rename_new(p, target):
            if k > 999:
                raise FileExistsError(f"no free name for {p.name} in {dest}")
            target, k = dest / f"{Path(p.name).stem} ({k}){Path(p.name).suffix}", k + 1
        if moved is not None:
            moved.append((p, target))
    return dest


def _drop(t):
    """Take away one of this script's own unfinished downloads (never anything else)."""
    try:
        if t.exists():
            t.unlink()
    except OSError:   # a PC's virus checker can hold a file just written for a moment; it is ours, and harmless
        pass


def _part_name(dst, i):
    """The download's scratch name, beside its real one. curl is handed only this name (it runs inside the
    folder), never the kit's whole path, so an accent or an emoji in a kit's name never reaches it: curl.exe
    on a PC may not open such a name. A name that is not plain letters itself gets a plain one."""
    name = dst.name + ".part"
    return name if name.isascii() else f".canva-download {i:02d}.part"


NAME_MOST = 255   # the longest file name a drive takes: the Mac's own (APFS, HFS+), a PC's (NTFS) and exFAT alike


def _places(name):
    """How long a file name is to a drive: they count in UTF-16, where an emoji takes two places."""
    return len(name.encode("utf-16-le", "surrogatepass")) // 2


def _shown(name):
    return name if len(name) <= 90 else name[:60] + "..." + name[-25:]


def _plan(folder, urls, names, start):
    """Where each download goes, worked out before anything is touched: ([(fresh file, its scratch copy)], None),
    or (None, the words for why it can't be done)."""
    plan = []
    for i, u in enumerate(urls, start):
        ext = ".jpg"
        m = re.search(r"\.(jpe?g|png|mp4|pdf)(?:\?|$)", u, re.I)
        if m:
            ext = "." + m.group(1).lower().replace("jpeg", "jpg")
        try:
            stem = names.format(n=f"{i:02d}")
        except (KeyError, IndexError, ValueError, AttributeError):
            return None, (f"STOP: the name pattern \"{names}\" can't be used: it may hold only {{n}}, where the number "
                          f"goes (\"Slide {{n}}\"). Nothing in the kit changed.")
        # A name every Mac and PC accepts (no colon, no slash, not a name Windows keeps for itself); the usual
        # "Slide 01", "Story 02" come through exactly as they are. Never cut short: a cut could take the number with
        # it and give two downloads one name. A name too long for any drive is stopped just below instead.
        dst = folder / (this_computer.safe_name(stem, limit=NAME_MOST, fallback=f"{i:02d}") + f" (Canva){ext}")
        plan.append((dst, folder / _part_name(dst, i)))
    for dst, tmp in plan:
        if _places(dst.name) > NAME_MOST or _places(tmp.name) > NAME_MOST:
            return None, (f"STOP: \"{_shown(dst.name)}\" is too long for a file name. Nothing in the kit changed. "
                          f"A shorter name pattern fixes it.")
    seen = set()
    for dst, _ in plan:
        if _fold(dst.name) in seen:   # the same name, or the same to a drive that ignores capitals
            return None, (f"STOP: two of these downloads would both be called \"{_shown(dst.name)}\", and I never write "
                          f"over a file. Use a name pattern with {{n}} in it, where the number goes. Nothing in the kit changed.")
        seen.add(_fold(dst.name))
    return plan, None


def _too_deep(kit, into, plan, only):
    """On a PC: the name of a file Windows could not hold, because the folders on the way to it are too long; None
    when all is well. It looks at each fresh file (File Explorer's limit, since the photographer opens it), its
    scratch copy (curl writes it), and every file that goes aside, now or at the next export, in the kit's hidden
    folder (a copy File Explorer made, "Slide 02 (Canva) - Copy.jpg", has a longer name than the fresh one).
    A Mac: never (this_computer)."""
    for dst, tmp in plan:
        if this_computer.path_too_long(dst) or this_computer.path_too_long(tmp):
            return dst.name
    going = [dst.name for dst, _ in plan]
    try:
        going += [p.name for p in _older(kit / into, only, [d for d, _ in plan])]
    except OSError:   # no such folder yet: nothing to set aside
        pass
    aside = kit / ".kit" / "canva-older" / f"{into} 0000-00-00 000000"
    for name in going:
        p = Path(name)
        if this_computer.records_path_too_long(aside / f"{p.stem} (999){p.suffix}"):
            return name
    return None


def fetch(kit, into, urls, names, start=1):
    folder = kit / into
    plan, words = _plan(folder, urls, names, start)
    if plan is None:
        say(words)
        return 1
    only = None if start == 1 and into != "Stories" else [d.name for d, _ in plan]
    deep = _too_deep(kit, into, plan, only)
    if deep:
        theirs = "" if deep in {d.name for d, _ in plan} else f" So does moving {_shown(deep)} out of the {into} folder."
        say(f"STOP: Windows can't keep {_shown(deep)} where it goes: the folders on the way to it have too "
            f"many letters in all. Nothing in the kit changed. A shorter name for the shoot, or the Assistant's folder "
            f"nearer the top of the drive, fixes it.{theirs}")
        return 1
    c_url = curl()
    folder.mkdir(exist_ok=True)
    # Download everything first (as .part files), and only then swap the earlier Canva files out.
    # A failed download leaves the kit exactly as it was.
    pending = []
    for (dst, tmp), (i, u) in zip(plan, enumerate(urls, start)):
        # A scratch copy left by a run cut off at just the wrong moment can share its bytes with a kept file (the
        # Mac gives a file its name by a link, then drops the old name); it goes first, so curl never writes into those.
        _drop(tmp)
        r = subprocess.run([c_url, "-sS", "-L", "-m", "300", "-o", tmp.name, u, "-w", "%{http_code}"], cwd=str(folder),
                           capture_output=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not r.stdout.strip().startswith("200") or not tmp.exists() or tmp.stat().st_size == 0:
            for _, t in pending + [(dst, tmp)]:
                _drop(t)
            say(f"STOP: couldn't download file {i} from Canva ({r.stdout.strip() or r.stderr.strip()[:80]}). The links last a day; ask for a fresh export if it's older. Nothing in the kit changed.")
            return 1
        pending.append((dst, tmp))
    got, blocked, stop, aside = [], [], None, []
    try:
        set_aside_older(kit, into, folder, only=only, coming=[d for d, _ in pending], moved=aside)
        for dst, tmp in pending:
            # The fresh file takes its name, never over another: one that turned up there just now stays as it is.
            if this_computer.rename_new(tmp, dst):
                got.append(dst.name)
            else:
                blocked.append(dst.name)
                _drop(tmp)
    except OSError as e:   # nothing is written over in any case; what is not in place yet is only a download
        stop = e
        for dst, tmp in pending:
            if dst.name not in got:
                _drop(tmp)
    if stop is not None:
        why = (f"{Path(stop.filename).name}: " if getattr(stop, "filename", None) else "") + str(stop.strerror or stop)
        if isinstance(stop, PermissionError) and this_computer.WINDOWS:
            say(f"STOP: something on this {this_computer.COMPUTER} has a file in {into} open right now (a photo viewer, or a "
                f"folder window showing it), so not every fresh Canva file could go in. Nothing was written over or lost. "
                f"Close it and say go, then run the same command again (the links last a day).")
        elif isinstance(stop, PermissionError):
            hint = (f" One of them may be locked: select it in {this_computer.FILES_APP}, choose File > Get Info, and "
                    f"untick Locked. Then run" if this_computer.MAC else " Run")
            say(f"STOP: I wasn't allowed to change the files in {into} ({why}), so not every fresh Canva file could go "
                f"in. Nothing was written over or lost.{hint} the same command again (the links last a day).")
        else:
            say(f"STOP: I couldn't finish putting the fresh Canva files in {into} ({why}). Nothing was written over or "
                f"lost. Run the same command again (the links last a day).")
    if blocked:
        say(f"STOP: {', '.join(blocked)} didn't go in: a file by that name turned up in {into} while I was working, and I "
            f"never write over a file. Run the same command again (the links last a day).")
    stopped = stop is not None or bool(blocked)
    rec = kit_mod.load_rec(kit)
    c = rec.setdefault("canva", {})
    if stopped:   # it says what is really there: the Canva files it knew of that are still in place, and the new ones
        try:
            there = {p.name for p in folder.iterdir()}
        except OSError:
            there = set(got)
        got_all = sorted(n for n in set(c.get("files", {}).get(into, [])) | set(got) if n in there)
    elif into == "Stories" or start != 1:   # one at a time: keep the others listed
        had = [n for n in c.get("files", {}).get(into, []) if n not in got]
        got_all = sorted(set(had + got))
    else:
        got_all = got
    c.setdefault("files", {})[into] = got_all
    if got or not stopped:
        c.setdefault("fetched", {})[into] = datetime.now().isoformat(timespec="seconds")
    kit_mod.save_rec(kit, rec)
    kit_mod.write_page(kit)
    refresh_posting(kit)
    if got or not stopped:
        say(f"{len(got)} file{'s' if len(got) != 1 else ''} from Canva in {into}: " + ", ".join(got))
    if aside and not stopped:
        say(f"The earlier Canva files from {into} were set aside (not deleted) in the kit's hidden folder.")
    elif aside:
        say(f"{len(aside)} of the earlier Canva files from {into} {'was' if len(aside) == 1 else 'were'} set aside (not "
            f"deleted) in the kit's hidden folder before it stopped.")
    return 1 if stopped else 0


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


def links(raw):
    """The download links from --urls: the list itself, or a file holding it. None if it can't be read.
    A file is read as bytes and Python's json works out how it was saved: UTF-8 (with or without the mark some
    editors put at the front) or UTF-16 (what a PC's PowerShell writes with >)."""
    try:
        a_file = Path(raw).is_file()
    except (OSError, ValueError):   # a long list of links is far too long for a file's name ("File name too long")
        a_file = False
    try:
        urls = json.loads(Path(raw).read_bytes() if a_file else raw)
    except (OSError, ValueError):
        return None
    if isinstance(urls, dict):
        job = urls.get("job")
        urls = urls.get("urls") or (job.get("urls") if isinstance(job, dict) else None) or []
    if not isinstance(urls, list) or not urls or not all(isinstance(u, str) and u.strip() for u in urls):
        return None
    return urls


def main():
    this_computer.utf8_output()
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
        urls = links(a.urls)
        if urls is None:
            say("STOP: I couldn't read the list of download links. Save the list Canva gave to a file and pass the file "
                "(--urls <file>). Nothing in the kit changed.")
            return 1
        names = a.names or {"Carousel": "Slide {n}", "Covers": "Reel cover {n}", "Singles": "Single {n}", "Stories": "Story {n}"}[a.into]
        return fetch(k, a.into, urls, names, a.start)
    if a.cmd == "note":
        note(k, a.piece, a.design_id, a.edit_url, a.template, a.n); return 0
    if a.cmd == "which":
        return design_for(k, a.piece, a.n)


if __name__ == "__main__":
    sys.exit(main())
