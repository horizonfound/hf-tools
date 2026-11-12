#!/usr/bin/env python3
"""The whole night, one command. Runs every step in order and stops only
when something is wrong or when Claude's one look is needed:

  copy + verify (backup.py)  ->  index  ->  groups  ->  contact sheet
  ->  [Claude reads the sheet, writes shoots.json]  ->  sort with the
  suggested names  ->  the morning report (verdict, numbers, the shoots
  with their previews and name boxes, where the photos are)

Safe to run again at any point; each step is skipped once its result exists.

    python3 night.py --source /Volumes/EOS_DIGITAL --dest "/Volumes/Drive" --name "Saturday card"
    python3 night.py --session "<session folder>"          continue a session already started

Exit codes: 0 done · 1 problems (read the report) · 2 stop (missing source
or drive) · 3 paused (run again) · 4 needs Claude's look (read
_studio/groups-sheet.png, write _studio/shoots.json, run again) · 5 needs
setup (no Studio File yet: ask their drive and naming, save with
studio_file.py, run again) · 7 needs the sneak peeks (read the pages it names,
peek_sheets.py pick ..., run again).

Their drive, second copy and naming come from ~/.studio (studio_file.py), so
after the first run the command is just:  night.py --source /Volumes/CARD
A card the ledger (cards.py) already knows is not copied again.
"""
import argparse
import errno
import json
import os
import stat
import subprocess
import threading
import time
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cards  # noqa: E402
import clips  # noqa: E402  (which files are video, and how to say a count)
import studio_file  # noqa: E402
from where import locate  # noqa: E402
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()


# A closed output never stops the backup part way (the Oct 24 rule: "say() never lets a closed pipe stop the work").
# Before Nov 6 it did, on a Mac too: run through `| head -1`, the copy stopped at its first line (exit 120), the card
# not copied; and night.py stopped at its own next line. Our outputs whose reader has gone away ("out", "err").
_GONE = set()


def _reader_gone(e):
    """Is this error the reader of our output having gone away (a `| head` that has read enough, a closed window)?
    A broken pipe on both computers; on a PC also "invalid argument" (EINVAL), which is how Windows reports it
    (as kit.py's say; unproven on a real PC). Anything else is not, and a Mac raises it as before."""
    return isinstance(e, BrokenPipeError) or (this_computer.WINDOWS and isinstance(e, OSError) and e.errno == errno.EINVAL)


def _let_go(which):
    """From now on this output ("out" or "err") goes nowhere: neither a later line nor Python's own last flush at the
    end trips over the closed pipe, which would turn night.py's exit code (0, 4, 7..., read by the skill) into 120."""
    _GONE.add(which)
    stream = sys.stdout if which == "out" else sys.stderr
    try:
        fd = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(fd, stream.fileno())
        finally:
            os.close(fd)
    except (OSError, ValueError, AttributeError):
        null = open(os.devnull, "w", encoding="utf-8")
        if which == "out":
            sys.stdout = null
        else:
            sys.stderr = null


def say(msg):
    """Print one line. If whatever reads our output has gone away, the line goes nowhere and the backup carries on."""
    try:
        print(msg, flush=True)
    except OSError as e:
        if not _reader_gone(e):
            raise
        _let_go("out")


def _can_close(stream):
    """Can the reader of this output go away while we still write to it? A pipe or a socket can (`| head`); a
    terminal or a file can't, and with those the steps write straight to it, exactly as before."""
    try:
        mode = os.fstat(stream.fileno()).st_mode
    except (OSError, ValueError, AttributeError):
        return False
    return stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)


def _same_pipe(a, b):
    """Are our two outputs one and the same pipe (`2>&1 | ...`)? Then a step's two outputs share one pipe here too,
    so its lines and its errors keep their order. Never on a PC: Windows gives every pipe the number 0, so there a
    step's errors travel apart from its lines and may land a few lines away from where they were printed (nothing
    stops, no file changes; this_computer has no way yet to ask Windows whether two outputs are one pipe)."""
    try:
        x, y = os.fstat(a.fileno()), os.fstat(b.fileno())
    except (OSError, ValueError, AttributeError):
        return False
    return x.st_ino != 0 and (x.st_dev, x.st_ino) == (y.st_dev, y.st_ino)


def _relay(src, which):
    """Pass one step's output on, byte for byte, as it comes. Once our own output has gone, the step's output is
    still read and dropped, so the step never meets the closed pipe and never waits on a full one."""
    try:
        while True:
            try:
                chunk = os.read(src.fileno(), 65536)
            except OSError:
                return
            if not chunk:
                return
            if which in _GONE:
                continue
            stream = sys.stdout if which == "out" else sys.stderr
            try:
                stream.buffer.write(chunk)
                stream.buffer.flush()
            except Exception as e:  # noqa: BLE001  (never let this die: the step would wait on a full pipe)
                if isinstance(e, OSError) and _reader_gone(e):
                    _let_go(which)
                else:
                    _GONE.add(which)
    finally:
        try:
            src.close()
        except OSError:
            pass


def run(script, *args):
    """Run one of the scripts beside this one, streaming its output; return its exit code.
    The computer is asked not to doze off in the middle of a long copy (the Mac's caffeinate; on a PC,
    Windows' own request, made in this_computer.py).
    Written to a terminal or a file, the step writes straight to it, as always. Written to a pipe, the step's output
    comes through here (_relay), so a reader that goes away part way never stops the step: a step meeting the
    closed pipe itself stops there, or ends with Python's 120 (`| head -30` on a pretend card stopped the backup
    at finding the shoots, exit 1, even with every say() of night.py and backup.py made safe).
    A step must never hand a process that outlives it this output (a page server, say): give it a log of its own, as
    fresh.start_server does. Otherwise, written to a pipe, each such step waits 10 more seconds here, and that
    process meets the closed pipe once night.py has gone. No step does today."""
    cmd = this_computer.awake_command([sys.executable, str(HERE / script), *map(str, args)])
    outputs = (("out", sys.stdout), ("err", sys.stderr))
    if not any(which in _GONE or _can_close(stream) for which, stream in outputs):
        return subprocess.run(cmd).returncode   # a terminal or a file: exactly as before
    for which, stream in outputs:
        if which in _GONE:
            continue
        try:   # our own lines first, so the step's come after them
            stream.flush()
        except OSError as e:
            if not _reader_gone(e):
                raise
            _let_go(which)
    # a gone output: the step's goes nowhere too; a pipe: through here; a terminal or a file: straight to it
    route = {which: subprocess.DEVNULL if which in _GONE else (subprocess.PIPE if _can_close(stream) else None)
             for which, stream in outputs}
    if route["out"] == subprocess.PIPE and route["err"] == subprocess.PIPE and _same_pipe(sys.stdout, sys.stderr):
        route["err"] = subprocess.STDOUT
    p = subprocess.Popen(cmd, stdout=route["out"], stderr=route["err"])
    relays = [threading.Thread(target=_relay, args=(src, which), daemon=True)
              for src, which in ((p.stdout, "out"), (p.stderr, "err")) if src is not None]
    for t in relays:
        t.start()
    try:
        code = p.wait()
    except BaseException:
        p.kill()   # as subprocess.run does (Ctrl+C, say)
        p.wait()
        raise
    finally:
        for t in relays:
            t.join(timeout=10)   # the rest of its output, a moment after it ends
    return code


def fresh(a, b):
    """True when file a exists and is newer than file b (or b is missing)."""
    return a.exists() and (not b.exists() or a.stat().st_mtime >= b.stat().st_mtime)


def gb(n):
    return f"{n / 1e12:.1f} TB" if n >= 1e12 else f"{n / 1e9:.0f} GB"


def pictures_missing():
    """None when this computer can make the small pictures the backup needs; otherwise what is missing, in
    plain words (pictures.ready()). Only ever asked where the Mac's own picture tool is not used: on a Mac
    nothing here runs. A pictures.py that cannot be loaded is not the photographer's problem, so it never
    stops the backup here; the preview step says so loudly if it really is broken."""
    try:
        import pictures
        if pictures.use_sips():
            return None
        ok, how = pictures.ready()
        return None if ok else how
    except Exception:  # noqa: BLE001
        return None


def stop_without_pictures():
    """Exit 2 with plain words when this computer cannot make the backup's previews (see pictures_missing).
    Used where a backup is picked up again, so there is nothing to copy and no preflight runs."""
    why = pictures_missing()
    if why:
        say("STOP, before going on:")
        say(f"  - {why}")
        sys.exit(2)


def preflight(source, dest, second):
    """Plain-words problems that would stop the night, found now rather than at 2am."""
    problems = []
    why = pictures_missing()
    if why:
        # On a PC the previews, the contact sheet and the sneak peeks need one add-on (Pillow). Without it the
        # backup would copy everything and then stop at the first preview, so it is said now, before a byte is
        # copied. (A Mac makes them with its own tool, so on a Mac this never says anything.)
        problems.append(why)
    if not source.is_dir():
        problems.append(f"The card is not there: {source}")
        return problems
    try:
        files = cards.files_on(source)
    except OSError as e:
        return [f"Cannot read the card ({e.__class__.__name__})."]
    if not files:
        problems.append(f"Nothing on the card to copy: {source}")
        return problems
    need = sum(s for _, s in files)
    # Never onto the card itself (on a PC the card can get the letter the photo drive had yesterday). Asked
    # before the test file below is written, so not even that ever lands on the card.
    from backup import onto_itself
    onto_card = onto_itself(source, dest, "the backup")
    if onto_card:
        problems.append(onto_card)
    if second is not None:
        why = onto_itself(source, second, "the second copy")
        if why:
            problems.append(why)
    if not dest.is_dir():
        problems.append(f"The drive is not plugged in or the folder is not there: {dest}")
    elif onto_card:
        pass
    else:
        try:
            probe = dest / ".studio-write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError:
            problems.append(f"Cannot write to the drive: {dest}")
    if second and not second.is_dir():
        problems.append(f"The second-copy folder is not there: {second}")
    # Room: the card's size plus a margin, per physical drive. The main drive and the second copy
    # on one disk need room for both. Found now, before a byte is copied.
    per_copy = need * 1.05 + 2 * 1024 ** 3
    by_dev = {}
    for label, root in (("the drive", dest), ("the second-copy drive", second)):
        if root is None or not root.is_dir():
            continue
        dev = os.stat(root).st_dev
        by_dev.setdefault(dev, {"labels": [], "root": root, "need": 0})
        by_dev[dev]["labels"].append(label)
        by_dev[dev]["need"] += per_copy
    for d in by_dev.values():
        free = this_computer.free_bytes(d["root"])
        if free is None:
            problems.append(f"Cannot tell how much room is on {' and '.join(d['labels'])}: {d['root']}")
            continue
        if free < d["need"]:
            both = len(d["labels"]) > 1
            problems.append(f"Not enough room on {' and '.join(d['labels'])}{' (they are the same drive)' if both else ''}: "
                            f"the card holds {gb(need)}{' and both copies go there' if both else ''}, about {gb(d['need'])} is needed, "
                            f"and there is {gb(free)} free. Free up about {gb(d['need'] - free)} or pick another drive.")
    return problems


def another_card(studio, source, name):
    """Plain words when this backup's folder already holds a backup made from a different card
    (backup.not_this_card); None when it holds nothing yet, or this card's own."""
    mpath = studio / "manifest.json"
    if not mpath.exists():
        return None
    from backup import inventory, not_this_card
    files, _ = inventory(source)
    return not_this_card(json.loads(mpath.read_text(encoding="utf-8")), source, files, name)


def check_shoots(studio):
    """shoots.json must give every group to exactly one shoot, with a suggested name each."""
    groups = [g["id"] for g in json.loads((studio / "groups.json").read_text(encoding="utf-8"))["groups"]]
    try:
        shoots = json.loads((studio / "shoots.json").read_text(encoding="utf-8"))["shoots"]
    except (ValueError, KeyError, OSError) as e:
        return f"shoots.json could not be read ({e.__class__.__name__})"
    seen = []
    for s in shoots:
        if not s.get("id") or not s.get("suggested") or not s.get("groups"):
            return f"a shoot is missing id, suggested name or groups: {s}"
        seen += s["groups"]
    missing = [g for g in groups if g not in seen]
    doubled = [g for g in seen if seen.count(g) > 1]
    if missing or doubled:
        return f"groups not assigned: {missing}; assigned twice: {doubled}"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--dest", help="the session drive or folder")
    ap.add_argument("--name")
    ap.add_argument("--second", default=None)
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--session", help="an existing session folder, to continue")
    ap.add_argument("--gap", default="15", help="quiet minutes that start a new group")
    ap.add_argument("--budget", default=None, help="seconds the copy may run before pausing cleanly")
    ap.add_argument("--no-open", action="store_true", help="(kept for old callers; the report is never opened by the backup now)")
    ap.add_argument("--open", action="store_true", help="show the report of a finished backup in the browser (via serve_report.py in its own pane)")
    ap.add_argument("--again", action="store_true", help="copy even if the ledger says this card is already backed up")
    ap.add_argument("--no-peeks", action="store_true", help="skip the sneak peeks (the backup still finishes and settles)")
    ap.add_argument("--check", action="store_true", help="preflight only: is everything in place for the night to run unattended? (a few seconds)")
    a = ap.parse_args()

    # their drive and second copy come from the Studio File unless given here
    sf = studio_file.load()
    drives = sf.get("drives", {})
    dest_from_file = bool(a.source and not a.dest)       # the usual drive, not one named for this backup only
    second_from_file = bool(a.source and a.second is None and drives.get("second"))
    if a.source and not a.dest:
        a.dest = drives.get("session")
    if a.source and a.second is None and drives.get("second"):
        a.second = drives["second"]
    if a.source and not a.dest:
        say("5. NEEDS SETUP. No Studio File yet: ask which drive their sessions go on (studio_file.py drives lists them), "
            "whether they keep a second copy, and how they name shoot folders, then save it with studio_file.py set.")
        sys.exit(5)
    if a.source and not a.name:
        a.name = datetime.now().strftime("%A").lower() + " card"  # "saturday card"
    if this_computer.WINDOWS:
        # unproven on a real PC: a bare "E:" means the top of drive E; Python alone reads it as wherever it last
        # was on E. (A Mac's paths are left exactly as given.)
        for k in ("source", "dest", "second"):
            if getattr(a, k):
                setattr(a, k, str(this_computer.drive_root(getattr(a, k))))

    # Does the card answer at all? Asked first, by a small program of its own with a time limit, so a card that has
    # gone quiet stops the backup in plain words within half a minute, instead of a silent wait with no end.
    if a.source and not cards.answers(a.source):
        say("STOP, before anything is copied:")
        say(f"  - {cards.QUIET_CARD}")
        sys.exit(2)

    # the ledger: a card already backed up is not copied again
    if a.source and not a.session and not a.again:
        fp, held = cards.check(a.source)
        if held:
            root, held_studio = Path(held["root"]), Path(held["studio"])
            # done means settled: the shoots moved up into their place and the day folder gone. first-look.html
            # plus sneak-peeks.json is not enough (Oct 28: the picks are written before they are marked and before
            # the settle, and that test called the backup done at that point, leaving the peeks unmarked and the
            # day folder in place). An old backup that never settled picks up at the settle, which is right.
            if (held_studio / "settled.json").exists():
                # the whole night ran on this card already: copied, verified, sorted, settled, report written
                say(f"This card is already safe: {fp['count']:,} files backed up to {root} on {held['when'][:10]}. Nothing to do.")
                say("(To copy it again anyway, run with --again.)")
                say(f"Report: {held_studio / 'report.html'}")
                if a.open:
                    open_report(held_studio, held_studio)
                sys.exit(0)
            # copied and verified, but the night did not finish (Claude's look, the sort, the report): pick it up there
            say(f"This card is already copied and verified, in {root}. Picking up where the backup left off.")
            if a.check:
                stop_without_pictures()
                return
            if held_studio.name != "_studio":
                # The settle had already moved the records into <their place>/.studio/<night> when it stopped (the
                # power went, or it ended "done with problems"): only the settle is left to finish. Without this,
                # root is their place itself, which holds no _studio, so the whole card was copied again into a new
                # folder and index.py then stopped on a missing index (found Nov 6). Nothing is copied here.
                code = run("settle.py", held_studio)
                if code not in (0, 6):
                    sys.exit(1)
                run("first_look.py", held_studio)
                run("report_page.py", held_studio)
                run("edit_queue.py", "register", "--night", held_studio)
                say(f"\nDone. Report: {held_studio / 'report.html'}")
                return
            a.session = str(root)

    if a.session:
        session = Path(a.session).expanduser().resolve()
        if not (session / "_studio").exists():
            try:
                root, st = locate(session)
            except SystemExit:
                root, st = None, None
            if st is not None and (st / "settled.json").exists():
                say(f"This backup is finished and settled: the shoots are in {root}.")
                if a.open:
                    open_report(st, st)
                return
    elif a.source and a.dest and a.name:
        session = Path(a.dest).expanduser() / this_computer.safe_name(f"{a.date} {a.name.strip()}", limit=120)
    else:
        sys.exit("usage: --source [--dest --name], or --session <folder>")
    studio = session / "_studio"
    if a.session:
        stop_without_pictures()   # picking up a backup: the next steps make previews (on a Mac this says nothing)

    # preflight: everything the night needs, checked before they walk away, so nothing stops it later
    if a.source and not a.session:
        # On a PC, the usual drive's letter may belong to another drive today (often the memory card itself).
        # Asked first, so not even the preflight's test file lands on the wrong drive. Never on a Mac (None there).
        moved = [w for w in (studio_file.drive_moved(drives, "session") if dest_from_file else None,
                             studio_file.drive_moved(drives, "second") if second_from_file else None) if w]
        problems = moved or preflight(Path(a.source), Path(a.dest), Path(a.second) if a.second else None)
        if Path(a.source).is_dir() and not moved:
            # a folder of the same name from earlier today may hold a different card's backup (two cards, no name
            # given: both "<weekday> card"); the card ledger did not know this card, so it is checked here
            why = another_card(studio, Path(a.source), a.name)
            if why:
                problems.append(why)
        if problems:
            say("STOP, before anything is copied:")
            for p in problems:
                say(f"  - {p}")
            sys.exit(2)
        if a.check:
            say("PREFLIGHT OK: card readable, drive there with room to spare, Studio File set. You can walk away once it starts.")
            try:  # the one gentle nudge for shoots kept on the computer's own disk (Dustin, Oct 30)
                if studio_file.on_internal_disk(a.dest):
                    total, free = this_computer.disk(a.dest)
                    if free / max(total, 1) < 0.15:
                        say(f"NOTE: your shoots are on this computer's own disk and it is down to {free / 1e9:.0f} GB free. "
                            "An external drive would keep the photos safe if anything happens to the computer and give it room to breathe.")
            except Exception:
                pass
            return

    # 1. copy and verify (backup.py also builds the index and the report page)
    manifest = studio / "manifest.json"
    done = False
    if manifest.exists():
        m = json.loads(manifest.read_text(encoding="utf-8"))
        done = not m.get("problems") and all(v.get("dest", {}).get("ok") for v in m.get("files", {}).values()) and bool(m.get("files"))
        if done and a.source and Path(a.source).is_dir():
            # Done means every file on the card is copied and checked, not just every file the records reached: a
            # backup cut off part way (paused, or the computer went off mid-copy) has only good records, and was
            # taken for finished, so the rest of the card was never copied (found Nov 6). It carries on now.
            from backup import inventory, not_copied
            card_files, _ = inventory(Path(a.source))
            if not_copied(m, Path(a.source), card_files):
                done = False
    if not done:
        if not (a.source and a.dest and a.name):
            sys.exit(f"STOP: {session} is not fully backed up, and I need --source, --dest and --name to continue it.")
        say("1. Copying and verifying")
        args = ["--source", a.source, "--dest", a.dest, "--name", a.name, "--date", a.date]
        if a.second:
            args += ["--second", a.second]
        if a.budget:
            args += ["--budget", a.budget]
        code = run("backup.py", *args)
        if code != 0:
            sys.exit(code)  # 1 problems, 2 stop, 3 paused: backup.py already said why
        cards.register(a.source, session)  # now the ledger knows this card
    else:
        say("1. Already copied and verified")

    # 2. the index (backup.py makes it; make sure)
    if not (studio / "index.json").exists():
        say("2. Indexing")
        if run("index.py", session) != 0:
            sys.exit(1)
    else:
        say("2. Index is there")

    # a dozen previews spread across the card, for the report's teasers (seconds)
    if not (studio / "previews").is_dir():
        run("previews.py", session, "--count", "12")

    # 3. groups and the sheet
    if not fresh(studio / "groups.json", studio / "index.json"):
        say("3. Finding the shoots")
        if run("groups.py", session, "--gap", a.gap) != 0:
            sys.exit(1)
    else:
        say("3. Groups are there")
    if not fresh(studio / "groups-sheet.png", studio / "groups.json"):
        if run("sheet.py", session) != 0:
            sys.exit(1)

    # 4. Claude's one look
    if not (studio / "shoots.json").exists():
        groups = json.loads((studio / "groups.json").read_text(encoding="utf-8"))["groups"]
        # groups of nothing but video clips: three frames from each clip (start, middle, end) on pages of their
        # own, so the look can tell what happens in them and name them for it (Dustin, Nov 11). A Mac only for now.
        if not (studio / "clip-sheets.json").exists() and any(g.get("clips") and not g.get("photos") for g in groups):
            run("clips.py", "sheets", session)
        say("\n4. NEEDS A LOOK. Read this image: " + str(studio / "groups-sheet.png"))
        say("   One row per group, in this order:")
        for i, g in enumerate(groups, 1):
            gap = f"after a {g['gap_before_min']} min gap" if g.get("gap_before_min") is not None else "first of the day"
            what = clips.words(g.get("photos", g["count"]), g.get("clips", 0))
            say(f"   {i:02d} {g['id']}  {g['start'][:16].replace('T', ' ')} to {g['end'][11:16]}  {what:>22}  {gap}")
        for line in clips.sheet_words(studio):
            say(line)
        if any(g.get("clips") for g in groups):
            say("   Some of these are video clips. On the first image, a row of clips shows one still from each clip (no picture at all on a PC):")
            say("   clips shot the same day and place as photos belong to that shoot (behind the scenes). In a recap, say")
            say("   \"video clips\", never \"photos\" and never \"clips\" on its own, for video, and if a row shows no picture say only what the times tell you.")
        say("   Decide which rows are one shoot (same people, same place, same day) and write " + str(studio / "shoots.json") + ".")
        say("   The suggested name is the place or subject only (\"Black-sand beach\"); the date goes on by the folder naming, so never put it in the name:")
        say('   {"decided_by": "Claude, from the contact sheet", "shoots": [{"id": "s1", "suggested": "<place or subject, no date: the folder naming adds the date>",'
            ' "groups": ["g01", "g02"], "photos": 1234, "recap": "<two or three warm sentences about what is in it>", "why": "<one line>"}, ...]}')
        say("   Then run this command again.")
        sys.exit(4)
    err = check_shoots(studio)
    if err:
        say(f"\n4. shoots.json needs fixing: {err}")
        sys.exit(4)
    say("4. Shoots decided")

    # 5. sort with the names there are (theirs, or the suggested ones)
    index = json.loads((studio / "index.json").read_text(encoding="utf-8"))
    if any(not p.get("original") for p in index["photos"] if p.get("taken")):
        say("5. Sorting into folders")
        if run("sort.py", session) != 0:
            sys.exit(1)
    else:
        say("5. Already sorted")

    # 6. the pages
    say("6. Writing the report")
    if run("first_look.py", session) != 0 or run("report_page.py", session) != 0:
        sys.exit(1)

    # 6b. the sneak peeks: the script thins each shoot to its moments and lays them on numbered pages;
    # Claude picks six per shoot (exit 7, then run again); then they are marked for Lightroom and shown
    # on the report. Nothing is on screen yet: Claude shows the report once, after the picks and the notes.
    if not a.no_peeks and not (studio / "sneak-peeks.json").exists():
        if not (studio / "peek-sheets.json").exists():
            say("6b. Thinning each shoot to its moments, for the sneak peeks")
            if run("peek_sheets.py", "make", studio) != 0:
                say("   (could not make the pages; going on without sneak peeks)")
        sheets = {}
        if (studio / "peek-sheets.json").exists():
            sheets = json.loads((studio / "peek-sheets.json").read_text(encoding="utf-8"))["shoots"]
            # sneak peeks are photos only: a shoot of nothing but video clips has none, and is never asked about
            none = [sh["name"] for sh in sheets.values() if not sh.get("moments")]
            sheets = {sid: sh for sid, sh in sheets.items() if sh.get("moments")}
            if none and not sheets:
                say("6b. No photos on this card, only video clips, so there are no sneak peeks to pick.")
            elif none:
                say("6b. No sneak peeks for " + ", ".join(none) + ": video clips only.")
        if sheets:
            say("\n6b. NEEDS THE PICKS. For each shoot, read its page(s) and choose six sneak peeks by number:")
            for sid, sh in sheets.items():
                say(f"   {sid} {sh['name']}: {sh['moments']} moments on {len(sh['pages'])} page(s)")
                for pg in sh["pages"]:
                    say(f"      {pg}")
            say("   Pick six per shoot, in the order they will sit on the report: the hero first (a scroll-stopper that")
            say("   survives a square crop), two that set it off, three that keep changing (a wide, a medium, a close, a")
            say("   detail, a different look); no two neighbors alike; every one a frame they'd be glad to see.")
            say("   First, the close look: shortlist 10 to 16 per shoot from the pages, then")
            say("      python3 " + str(HERE / "peek_sheets.py") + " closer \"" + str(studio) + "\" s1=61,64,71,18,... s2=...")
            say("   and read the -close pages it writes (four per page, full size). Drop anything soft, mid-blink, awkward,")
            say("   or with crew in the frame. Choose the six from what is left.")
            say(f"   Then: python3 {HERE / 'peek_sheets.py'} pick \"{studio}\" s1=14,3,27,9,41,18 s2=...   and run this command again.")
            sys.exit(7)
    if (studio / "sneak-peeks.json").exists():
        say("6b. Marking the sneak peeks for Lightroom")
        if run("sneak_peeks.py", "--night", studio) not in (0, 2):
            say("   (the sneak peeks could not all be marked; the report still shows them)")
        run("first_look.py", session)
        run("report_page.py", session)

    # 7. settle: the shoot folders go up into the place they chose, the day folder goes away,
    # the records move to a hidden .studio folder there. Left together (exit 6) only for a good reason.
    say("7. Putting the shoots where they belong")
    code = run("settle.py", session)
    if code not in (0, 6):
        sys.exit(1)
    if code == 0:
        root, studio = locate(session)
        session = studio  # every script finds the photos from the records now
        run("first_look.py", studio)
        run("report_page.py", studio)  # the report's "where your photos are" now points at the new place
    # every shoot of the night goes on "your shoots" (the archive below the queue); the queue question comes when they're back
    run("edit_queue.py", "register", "--night", studio)
    say(f"\nDone. Report: {studio / 'report.html'}")
    # The report is not opened here. The backup is only the first half: Claude still picks the sneak
    # peeks and writes the notes, and the report is shown once, by Claude, when all of that is done
    # (Dustin, Oct 28: it opened early, twice, in two browsers). `night.py --open` shows it on request.
    say("Not on screen yet: the sneak peeks and the notes come next, then the report is shown once.")


def open_report(session, studio):
    """Start the little report server (unless one is already up for this session) and open the report
    in the default browser. Falls back to opening the file itself if the server will not start."""
    url_file = studio / "report-url.txt"
    url = None
    if url_file.exists():
        old = url_file.read_text(encoding="utf-8").strip()
        try:  # is that server still alive? (asked never through a proxy, which can't see this computer's own pages)
            this_computer.open_local(old, timeout=1).read(1)
            url = old
        except Exception:
            url = None
    if not url:
        try:
            # The server's log lives in ~/.studio/logs, not in the backup's records: on a PC a log held open by the
            # running server would stop the settle step from moving that folder. It is one file per backup that
            # grows, so only what this server writes after it starts is read.
            import fresh
            from serve_report import log_name
            log, before = fresh.start_server([sys.executable, str(HERE / "serve_report.py"), str(session)], log_name(studio))
            for _ in range(30):  # the server prints its address on the first line
                time.sleep(0.1)
                text = fresh.log_since(log, before)
                hit = [ln for ln in text.splitlines() if "http://" in ln]
                if hit:
                    url = hit[-1].split("http://", 1)[1].split()[0]
                    url = "http://" + url
                    break
        except Exception:
            url = None
    if url:
        url_file.write_text(url, encoding="utf-8")
    target = url or str(studio / "report.html")
    if this_computer.WINDOWS:
        # unproven on a real PC. Windows' own "open this with whatever opens it". Not `cmd /c start`, which reads
        # the & in an address as the start of another command.
        try:
            os.startfile(target)
        except OSError as e:
            say(f"(could not open it: {e})")
    else:
        opener = {"darwin": ["open"], "linux": ["xdg-open"]}.get(sys.platform)  # pc-ok: Mac and Linux branch
        if opener:
            subprocess.run([*opener, target], check=False)
    say(f"Report on screen: {target}")


if __name__ == "__main__":
    main()
