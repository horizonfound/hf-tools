#!/usr/bin/env python3
"""The Assistant, by Horizon Found. A talking reel, made in CapCut (Nicole's handoffs v23 and v24, built our way).

Their talking-to-camera video, cut where they and the assistant cut it, with the photos and videos they put on
their words, the punch ins, slow zooms and speed-ups they pressed, themselves in the corner where they dragged
themselves, and the captions where they dragged them: written as a NEW CapCut project, "<shoot> talking reel"
(a second one is "... talking reel 2"). It never opens, changes or writes over a project that is there.

    python3 talking_make.py make --kit "<shoot>"      the shoot's folder, its name, or a few words of it
        [--dry-run]            work everything out and write nothing (not in CapCut, not in the record)
        [--status <file>]      a small JSON of what happened, for the page's job (ok, dry, project, listed,
                               left_to_capcut, waiting, plan, stop), so it never reads the words to tell
        [--store <folder>]     another CapCut projects folder (tests)
        [--ignore-open]        tests only: treat CapCut as closed

The page's Make it in CapCut button runs this in a job of its own (talking_rec.start_make). What it prints is
what the page's result box shows, every line of it, so a make prints ONE line and nothing else: Nicole's
    Made "<project>" in CapCut. Open CapCut and it's at the top of your projects.
    Made "<project>" in CapCut. CapCut is open, so it will show up in your projects in a moment; if it isn't there, quit and reopen CapCut.
(on a PC "quit" is "close"). When neither is true (the reel is waiting to go into CapCut's list of projects),
the one line is "Made "<project>" in CapCut." and then capcut.py's own words about what to do: saying it is at
the top of their projects would not be true.

One make of a shoot's reel at a time: while it writes, it holds .kit/talking-make.lock, and another make of the
same shoot (the page's job, or the chat) waits a moment and then stops with her "I'm still working on the last
one. Give it a minute.". Anything unforeseen (a list of the shoot's that can't be read) is a plain line and exit
2, never a Python error; the real words go to the log. --status only ever writes a status file (a .json that is
not there yet, or one that is a status now).

It stops, with nothing written anywhere, when (hers) there is no script yet, the talking video is no longer in
the Talking folder, or every word is cut; and (ours) when the video was exported again since its script was made,
while a video is still being turned into words, and when a photo or a Footage video they put on their words has
gone (hers leaves that stretch out without a word; ours says which kind is missing: talking_rec.OUR_MAKE_WORDS).

Sizes are read fresh, as each picture is SHOWN (video.facts: a phone video held upright is stored turned).
Every path stays on this side: the plan is kept in the shoot's hidden folder (.kit/talking-make.json: the
Assistant's own working file, replaced by each make), and no path is ever printed.

NOT YET SEEN IN CAPCUT BY ANYONE (docs/handoff-v24-build-2026-11-12.md, section 5, item 3): the project is
written the way Nicole read her own CapCut projects; nobody has opened one of these.

Exit: 0 made (or a dry run) · 2 STOP (nothing was written).

A Mac and a PC: needs nothing only a Mac has (a video's facts are read from its own header). On a PC the
project is written CapCut for Windows' way (capcut.py: unproven there).
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "studio-manager" / "scripts"))
import this_computer   # noqa: E402
import arrange         # noqa: E402
import kit as kitmod   # noqa: E402
import reel_page       # noqa: E402
import talking_rec     # noqa: E402
import capcut          # noqa: E402
import talking         # noqa: E402
import video           # noqa: E402

PLAN_FILE = "talking-make.json"        # in the kit's hidden folder: the last plan handed to capcut.py (ours, replaced each time)
MAKE_LOCK = "talking-make.lock"        # in the kit's hidden folder: held while one make writes this shoot's reel into CapCut
MAKE_LOCK_WAIT = 2.0                   # another make of the same shoot is waited for this long, then her "still working" line
QUIT = capcut.QUIT
# Hers, word for word (talking_capcut.py); "quit" is the PC's "close" there (decision 2b.11).
MADE_LISTED = "Made \"{project}\" in CapCut. Open CapCut and it's at the top of your projects."
MADE_OPEN = ("Made \"{project}\" in CapCut. CapCut is open, so it will show up in your projects in a moment; "
             "if it isn't there, " + QUIT + " and reopen CapCut.")
MADE_ONLY = "Made \"{project}\" in CapCut."      # ours: only when neither of hers would be true; capcut.py's note follows on the same line
# Hers (talking_capcut.py's dry run): for the assistant and the tests, never the page.
DRY_PLAN = ("Plan: {pieces} pieces of talking, {secs:.1f} seconds, {photos} photos, {videos} videos, {zooms} zooms, "
            "{sped} sped-up pieces, {captions} caption lines.")
DRY_DONE = "Dry run: nothing made in CapCut."


def say(msg):
    capcut.say(msg)


class Stop(Exception):
    """The reel can't be made: `code` names the line (talking_rec.make_line); nothing was written."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _shown_size(path, f=None):
    """(w, h, length) of a video as it is shown, from its own header."""
    f = f if isinstance(f, dict) and f.get("w") else video.facts(path)
    return int(f.get("w") or 0), int(f.get("h") or 0), float(f.get("length") or 0)


def stretches(rec, pcs):
    """Each photo stretch's place on the reel: [(the stretch, {"at", "dur"})], in reel order. As talking.shot_spans
    for stretches that don't overlap (every stretch her page makes). Where two overlap, a word belongs to the later
    one (talking.pieces' own rule), so each stretch gets only the pieces that are its own, as one run or several:
    two clips can then never sit on the same moment of CapCut's one photo layer."""
    shots = talking.shots(rec)
    owner = {}
    for k, x in enumerate(shots):
        for i in range(max(0, x["a"]), x["b"] + 1):
            owner[i] = k
    out, run = [], None
    for p in pcs:
        k = owner.get(p["words"][0])
        if run is not None and run[0] == k:
            run[2] = p
            continue
        if run is not None and run[0] is not None:
            out.append(run)
        run = [k, p, p]
    if run is not None and run[0] is not None:
        out.append(run)
    return [(shots[k], {"at": a["at"], "dur": round(b["at"] + b["dur"] - a["at"], 3)}) for k, a, b in out]


def _sheet_damaged(kit):
    """Is the shoot's numbered photo list there and not readable as one? (Then every photo would look gone.)"""
    f = Path(kit) / ".kit" / "sheet.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False
    except (OSError, ValueError):
        return True
    return not (isinstance(d, dict) and isinstance(d.get("photos"), list))


def plan_for(kit, rec=None):
    """The plan capcut.build_talking makes a project from, with real paths. Raises Stop(code) with nothing made."""
    kit = Path(kit)
    rec = rec if rec is not None else talking_rec.load(kit)
    code = talking_rec.make_problem(kit, rec)
    if code:
        raise Stop(code)
    hit = talking_rec._plain_videos(kit, talking_rec.TALKING).get(talking_rec._nfc(rec["video"]).casefold())
    if hit is None:                                    # it went between the check and now
        raise Stop("gone")
    src = hit[1]
    try:
        vw, vh, length = _shown_size(src)
    except (OSError, video.NotAVideo):
        raise Stop("gone")
    pcs = talking.pieces(rec)
    if not pcs:
        raise Stop("all_cut")
    files = [str(src)]
    kit_rec = kitmod.load_rec(kit)
    rows = {x["n"]: x for x in arrange.sheet_rows(kit)}
    footage = None
    shots, cover = [], None
    for x, span in stretches(rec, pcs):
        one = {"at": span["at"], "dur": span["dur"], "spot": x["spot"], "pos": x["pos"], "me": x["me"]}
        if x.get("v"):                                 # a video from this shoot's Footage folder
            footage = reel_page.list_videos(kit) if footage is None else footage
            v = reel_page.video_by_name(kit, x["v"], footage)
            if v is None or (v.get("facts") or {}).get("refused"):
                raise Stop("video_gone")
            try:
                w, h, vlen = _shown_size(v["path"], v.get("facts"))
            except (OSError, video.NotAVideo):
                raise Stop("video_gone")
            one["video"] = {"path": str(v["path"]), "w": w, "h": h, "length": vlen, "from": float(x.get("from") or 0)}
            files.append(str(v["path"]))
        else:
            one["photos"] = []
            for n in x["ns"]:
                row = rows.get(n)
                p = arrange.photo_path(kit, kit_rec, row) if row else None
                if p is None:
                    # a numbered list that can't be read is not a photo that has gone: never say theirs is missing
                    raise Stop("trouble" if _sheet_damaged(kit) else "photo_gone")
                w, h = int(row.get("w") or 0), int(row.get("h") or 0)
                if not (w and h):
                    w, h = capcut.photo_size(p)
                one["photos"].append({"path": str(p), "w": w, "h": h})
                files.append(str(p))
                cover = cover or str(p)
            if not one["photos"]:
                continue
        shots.append(one)
    caps = talking.captions(rec) if rec.get("captions", True) is not False else None
    cp = rec.get("cap_pos")
    cp = {"x": float(cp["x"]), "y": float(cp["y"])} if isinstance(cp, dict) and all(talking._num(cp.get(k)) is not None for k in ("x", "y")) else None
    return {"name": f"{talking_rec.short_name(kit)} talking reel", "photos": [], "song": None, "hook": None,
            "files": sorted(set(files)), "cover": cover,
            "video": {"path": str(src), "w": vw, "h": vh, "length": length},
            "pieces": [{k: p[k] for k in ("from", "to", "speed", "zoom", "sentence", "at", "dur")} for p in pcs],
            "zooms": talking.zooms(rec), "shots": shots, "captions": caps,
            "cap_pos": cp, "cap_size": float(talking._num(rec.get("cap_size")) or 1)}


def plan_facts(plan):
    """The plan in numbers (hers: the dry run's line), for --status and the dry run."""
    return {"pieces": len(plan["pieces"]), "secs": round(talking.reel_seconds(plan["pieces"]), 3),
            "photos": sum(len(x.get("photos") or []) for x in plan["shots"]),
            "videos": sum(1 for x in plan["shots"] if x.get("video")), "zooms": len(plan["zooms"]),
            "sped": sum(1 for p in plan["pieces"] if p.get("speed", 1.0) != 1.0), "captions": len(plan["captions"] or [])}


def write_status(a, **what):
    """--status: what happened, written whole or not at all; the job's own mark ("for") is kept (reel.py's way)."""
    if not getattr(a, "status", None):
        return
    f = Path(a.status)
    tmp = f.with_name(f".{f.name}.{os.getpid()}.tmp")
    # Only ever a status file: a name ending .json that is not there yet, or one that is a status now (the job's
    # mark, or an earlier status of ours). Pointed at anything else (a photo, the shoot's own kit.json, by a slip
    # in the command), nothing is written: no file of theirs or of the Assistant's is written over.
    if f.suffix.lower() != ".json":
        return
    try:
        old = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(old, dict) or not (isinstance(old.get("for"), str) or {"ok", "dry", "stop"} <= set(old)):
            return
        mine = {"for": old["for"]} if isinstance(old.get("for"), str) else {}
    except FileNotFoundError:
        mine = {}
    except (OSError, ValueError):
        return
    try:
        tmp.write_text(json.dumps(dict({"ok": False, "dry": bool(a.dry_run), "project": None, "plan": None, "stop": None},
                                       **mine, **what), indent=1), encoding="utf-8")
        this_computer.replace(tmp, f)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


def made_line(project):
    """The one line a make prints (see the top of this file)."""
    w = capcut.write
    if w.left_to_capcut:
        return MADE_OPEN.replace("{project}", project)
    if w.listed:
        return MADE_LISTED.replace("{project}", project)
    return MADE_ONLY.replace("{project}", project) + (" " + w.note if w.note else "")


def _trouble(a, kit, what, e, code="trouble"):
    """Anything unforeseen: the real words go to the log, the photographer gets a plain line, exit 2, no traceback."""
    talking_rec.log(f"{kit.name}: the talking reel's {what} ({e.__class__.__name__}: {str(e)[:300]})")
    write_status(a, stop=code)
    say("STOP: " + talking_rec.make_line(code))
    return 2


def cmd_make(a):
    kit = talking_rec.find(a.kit)
    try:
        plan = plan_for(kit)
    except Stop as e:
        write_status(a, stop=e.code)
        say("STOP: " + talking_rec.make_line(e.code))
        return 2
    except Exception as e:  # noqa: BLE001  (a record of the shoot's that can't be read, a drive gone: plain words, never a Python error)
        return _trouble(a, kit, "plan could not be made", e)
    facts = plan_facts(plan)
    if a.dry_run:
        say(DRY_PLAN.format(**facts))
        say(DRY_DONE)
        write_status(a, ok=True, plan=facts)
        return 0
    # One make of a shoot's reel at a time, from the page's job or from the chat: two at the same moment would
    # choose the same project name. The other is waited for a moment, then told her "still working" line.
    with kitmod._held(kit / ".kit" / MAKE_LOCK, MAKE_LOCK_WAIT) as got:
        if got is False:
            write_status(a, stop="making")
            say("STOP: " + talking_rec.make_line("making"))
            return 2
        try:                                           # the Assistant's own working file: which plan was handed over
            arrange.write_whole(kit / ".kit" / PLAN_FILE, plan)
        except OSError:
            pass                                       # a convenience; the reel is made either way
        store = Path(a.store).expanduser() if a.store else capcut.default_store()
        # capcut.write stops by itself (exit 2, a STOP line) when CapCut's projects folder is not there or a file
        # went in the last moment: nothing is written then, and its words never name one of their files' places.
        try:
            dest, draft = capcut.write(plan, store, a.ignore_open, builder=capcut.build_talking)
        except Exception as e:  # noqa: BLE001  (a number CapCut could not read, say: nothing is left in CapCut's folder)
            return _trouble(a, kit, "project could not be written", e, "went_wrong")
        line = made_line(dest.name)
        no_frame = int(getattr(capcut.build_talking, "no_frame", 0) or 0)
        if no_frame:                                   # 30 photos on half a second: the rest have no frame to be on
            talking_rec.log(f"{kit.name}: \"{dest.name}\": {no_frame} photo(s) had no frame to be on (more photos than frames on their words)")
        write_status(a, ok=True, project=dest.name, line=line, plan=facts, listed=bool(capcut.write.listed),
                     left_to_capcut=bool(capcut.write.left_to_capcut), waiting=bool(capcut.write.waiting), photos_no_frame=no_frame)
        try:                                           # hers: the record keeps what was made, and when
            talking_rec.note_made(kit, dest.name)
        except (talking_rec.Busy, talking_rec.Unreadable, OSError) as e:
            talking_rec.log(f"{kit.name}: \"{dest.name}\" is in CapCut, but the record could not note it ({e.__class__.__name__})")
        say(line)
        return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--kit", required=True, help="the shoot's folder, its name, or a few words of it")
    m.add_argument("--dry-run", action="store_true")
    m.add_argument("--status", help="write what happened here as a small JSON, for the page's job")
    m.add_argument("--store", help="another CapCut projects folder (tests)")
    m.add_argument("--ignore-open", action="store_true", help="tests only: treat CapCut as closed")
    a = ap.parse_args(argv)
    return cmd_make(a)


if __name__ == "__main__":
    sys.exit(main())
