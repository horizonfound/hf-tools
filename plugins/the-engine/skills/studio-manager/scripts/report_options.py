#!/usr/bin/env python3
"""The other options on the report, under "Anything you'd like to change?" (Dustin, Nov 19: nothing is asked
before a backup; "give them options to make little adjustments after the fact"). The report's server
(serve_report.py) runs one of these in a fresh process for each press, so a server that has been up for days
still does it with the code on disk, and hands the page the answer.

    python3 report_options.py other-backups "<backup>"      the finished backups that could be this shoot's other card
    python3 report_options.py link "<backup>"               {"backup": <index>, "name": "<its name>"} on stdin
    python3 report_options.py naming "<backup>"             the two offered folder names, with this backup's own shoot
    python3 report_options.py set-naming "<backup>"         {"offered": 1|2, "apply": true|false} on stdin
    python3 report_options.py next-drives "<backup>"        the drives the next backup could go on
    python3 report_options.py set-next-drive "<backup>"     {"drive": <index>, "name": "<its name>"} on stdin

Each prints one line of JSON, last. What a page is given never holds a path: a backup or a drive is a name and
its place in a list, and the list is made again (and the name must still match) before anything is changed.
What each one changes:
  link            shoot.json in each card's records and the report pages (shoot_report.link); no photo is read
  set-naming      the Studio File's folder pattern; the renames themselves are the report server's own queue
                  (rename_shoot.py, one shoot at a time), which this only lists under "rename"
  set-next-drive  the Studio File's drive, by the same place rule as the first backup's own choice; nothing moves
Every word a photographer sees is in report_page.OUR_WORDS (ours, drafts).
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
from where import locate, same_place  # noqa: E402
this_computer.utf8_output()

DAYS_BACK = 30      # how far back another card's backup is offered
MOST = 8            # and how many at the most


def words():
    import report_page
    return report_page.OUR_WORDS


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def plain_name(session):
    """ "2026-11-17 tuesday card" -> "tuesday card"."""
    session = str(session or "")
    return session.split(" ", 1)[1] if session[:10].count("-") == 2 and " " in session else session


def day_words(iso):
    """ "2026-11-17..." -> "Nov 17"; "" when it is not a date."""
    try:
        return this_computer.strftime(datetime.fromisoformat(str(iso)[:10]), "%b %-d")
    except (ValueError, TypeError):
        return ""


# ---------------------------------------------------------------- this shoot continues on another card

def other_backups(studio):
    """The finished backups that could be the other card of this shoot: from the card ledger (so a sample,
    which is never in it, is never offered), newest first, the last DAYS_BACK days, at most MOST, whose records
    can be found right now, that finished clean, and that are not already on this report. A backup that is
    itself part of another shoot of several cards is offered only when this one is not (two shoots of several
    cards are never joined from a button). Each row: records (never given to a page), name, day, count, when,
    started."""
    import cards
    import second_copy
    import shoot_report
    studio = Path(studio)
    mine = shoot_report.read(studio, heal=False)
    on_report = [str(studio)] + [c["found"] for c in (mine or {}).get("cards", []) if c.get("found")]
    since = (datetime.now() - timedelta(days=DAYS_BACK)).isoformat(timespec="seconds")
    seen, rows = [], []
    sessions = [s for entry in (cards.load().get("cards") or {}).values() for s in (entry.get("sessions") or [])
                if isinstance(s, dict) and s.get("folder")]
    for s in sorted(sessions, key=lambda x: str(x.get("when") or ""), reverse=True):
        when = str(s.get("when") or "")
        if when < since:
            continue
        try:
            _, rec = locate(s["folder"])
        except SystemExit:
            continue        # its drive is not plugged in, or it is gone
        rec = Path(rec)
        if any(same_place(str(rec), x) for x in on_report + seen):
            continue
        seen.append(str(rec))
        manifest = read_json(rec / "manifest.json", {}) or {}
        if second_copy.whole(manifest) is not None:
            continue        # unfinished, with problems, or a sample
        if mine and shoot_report.read(rec, heal=False):
            continue
        try:
            f = shoot_report.facts(rec)
        except Exception:  # noqa: BLE001  (records that cannot be read are simply not offered)
            continue
        session = manifest.get("session") or rec.name
        rows.append({"records": str(rec), "name": plain_name(session), "day": day_words(session) or day_words(when),
                     "count": f["words"], "when": when, "started": str(manifest.get("started") or when)})
        if len(rows) >= MOST:
            break
    return rows


def link(studio, ask):
    """Put this backup and the chosen one on one report. The list is made again and the name at that place must
    be the one the page showed. The older backup is card 1; a backup that is already a shoot of several cards
    keeps its cards and gains the other. Records and pages only (shoot_report.link): each card's photos stay in
    their own folders."""
    import shoot_report
    W = words()
    studio = Path(studio)
    try:
        i, name = ask["backup"], ask["name"]
        assert type(i) is int and isinstance(name, str)
    except (KeyError, AssertionError, TypeError):
        return {"ok": False, "words": W["oc_changed"]}
    rows = other_backups(studio)
    if not (0 <= i < len(rows)) or rows[i]["name"] != name:
        return {"ok": False, "again": True, "words": W["oc_changed"]}
    other = rows[i]
    me = read_json(studio / "manifest.json", {}) or {}
    if shoot_report.read(studio, heal=False):
        order = [str(studio), other["records"]]            # this shoot's cards, then the new one
    elif shoot_report.read(other["records"], heal=False):
        order = [other["records"], str(studio)]            # that shoot's cards, then this one
    else:
        order = sorted([str(studio), other["records"]],
                       key=lambda r: other["started"] if r == other["records"] else str(me.get("started") or ""))
    import contextlib
    import io
    said = io.StringIO()
    with contextlib.redirect_stdout(said):     # shoot_report says its own lines; the page gets ours
        code = shoot_report.link(order)
    if code != 0:
        sys.stderr.write(said.getvalue())
        return {"ok": False, "words": W["oc_cant"]}
    n = len((shoot_report.read(studio, heal=False) or {}).get("cards", []))
    return {"ok": True, "words": W["oc_done"] if n == 2 else W["oc_done_many"].format(n=n)}


# ---------------------------------------------------------------- change how my shoots are named

def shoots_of(studio):
    """This backup's shoots that are filed in a folder: [(id, the name it has now)]."""
    sh = (read_json(Path(studio) / "shoots.json", {}) or {}).get("shoots") or []
    return [(str(s["id"]), " ".join(str(s.get("name") or s.get("suggested") or "").split()))
            for s in sh if isinstance(s, dict) and s.get("id") and s.get("folder") and (s.get("name") or s.get("suggested"))]


def example_shoot(studio):
    """(name, date) to show the two ways with: this backup's first shoot and the day it was shot. With no shoot
    filed yet, "Smith Family" and the backup's own day."""
    studio = Path(studio)
    sh = (read_json(studio / "shoots.json", {}) or {}).get("shoots") or []
    groups = {g.get("id"): g for g in (read_json(studio / "groups.json", {}) or {}).get("groups") or []}
    for s in sh:
        name = " ".join(str(s.get("name") or s.get("suggested") or "").split())
        starts = sorted(str(groups[g].get("start") or "") for g in s.get("groups") or [] if g in groups)
        if name and starts and starts[0]:
            return name, starts[0]
    manifest = read_json(studio / "manifest.json", {}) or {}
    return "Smith Family", str(manifest.get("finished") or manifest.get("started") or datetime.now().isoformat())


def naming(studio):
    """The two offered ways, each shown with one of this backup's own shoots, and which one is theirs now (0
    when they name folders their own way)."""
    import studio_file
    now = studio_file.load().get("naming") or {}
    name, when = example_shoot(studio)
    ways, current = [], 0
    for n, way in enumerate(studio_file.OFFERED, 1):
        try:
            shown = studio_file.render(way, name, when)
        except Exception:  # noqa: BLE001
            shown = way["label"]
        ways.append({"n": n, "example": shown})
        if now.get("folder_pattern") == way["folder_pattern"] and now.get("date_format") == way["date_format"]:
            current = n
    return {"current": current, "ways": ways, "shoots": len(shoots_of(studio))}


def set_naming(studio, ask):
    """Save one of the two offered ways for every backup from now on. With apply, also list this backup's shoots
    for the report server's rename queue: each is renamed to the name it already has, and rename_shoot.py, which
    reads the pattern afresh, gives its folder the new shape (proven on a pretend backup, Nov 19: the folder
    moves, the photos keep their names, every file is proved the same file). A shoot already in that shape
    answers "nothing to do"."""
    import studio_file
    W = words()
    try:
        n, apply = ask["offered"], ask.get("apply", False)
        assert type(n) is int and 1 <= n <= len(studio_file.OFFERED) and isinstance(apply, bool)
    except (KeyError, AssertionError, TypeError):
        return {"ok": False, "words": W["nm_cant"]}
    if apply and shoots_of(studio):
        try:    # a rename while a second copy reads the same folders could make that copy miss a photo: wait
            import second_copy
            if second_copy.status(studio).get("state") == "copying":
                return {"ok": False, "words": W["nm_wait"]}
        except Exception:  # noqa: BLE001
            pass
    sf = studio_file.load()
    now = sf.setdefault("naming", {})
    way = studio_file.OFFERED[n - 1]
    if not (now.get("folder_pattern") == way["folder_pattern"] and now.get("date_format") == way["date_format"]):
        now.update(way)
        now.pop("example", None)
        studio_file.save(sf)
    shown = next((w["example"] for w in naming(studio)["ways"] if w["n"] == n), way["label"])
    todo = shoots_of(studio) if apply else []
    return {"ok": True, "example": shown, "rename": [list(x) for x in todo],
            "words": (W["nm_saved_renaming"] if todo else W["nm_saved"]).format(example=shown)}


# ---------------------------------------------------------------- use a different drive next time

def next_drives(studio=None):
    """Where the next backup could go: the drives plugged in (studio_file.drives(): never a memory card or Time
    Machine), then the computer itself, last. Each row: path (never given to a page; None for the computer),
    name, free, now (backups go there today)."""
    import second_copy
    import studio_file
    now = (studio_file.load().get("drives") or {}).get("session")
    rows = []
    for d in studio_file.drives():
        rows.append({"path": d["path"], "name": str(d["name"]), "free": second_copy.free_words(int(d.get("free_gb") or 0)),
                     "now": bool(now) and studio_file._inside(now, d["path"])})
    here = f"This {this_computer.COMPUTER}"
    rows.append({"path": None, "name": here, "free": "", "now": bool(now) and not any(r["now"] for r in rows)
                 and studio_file.on_internal_disk(now)})
    return rows


def set_next_drive(studio, ask):
    import studio_file
    W = words()
    try:
        i, name = ask["drive"], ask["name"]
        assert type(i) is int and isinstance(name, str)
    except (KeyError, AssertionError, TypeError):
        return {"ok": False, "words": W["nd_changed"]}
    rows = next_drives(studio)
    if not (0 <= i < len(rows)) or rows[i]["name"] != name:
        return {"ok": False, "again": True, "words": W["nd_changed"]}
    row = rows[i]
    got = studio_file.use_next(computer=True) if row["path"] is None else studio_file.use_next(drive=row["path"])
    drive = row["name"] if row["path"] else f"this {this_computer.COMPUTER}"
    if got["state"] == "saved":
        return {"ok": True, "words": W["nd_saved"].format(drive=drive)}
    if got["state"] == "same":
        return {"ok": True, "words": W["nd_same"].format(drive=drive)}
    if got["state"] == "second":
        return {"ok": False, "words": W["nd_second"].format(drive=drive)}
    return {"ok": False, "words": W["nd_gone"].format(drive=drive)}


# ---------------------------------------------------------------- the command the report's server runs

def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    try:
        _, studio = locate(sys.argv[2])
    except SystemExit:
        print(json.dumps({"ok": False, "words": words()["opt_cant"]}))
        return 1
    studio = Path(studio)
    ask = {}
    if cmd in ("link", "set-naming", "set-next-drive"):
        try:
            ask = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
            assert isinstance(ask, dict)
        except (ValueError, AssertionError):
            ask = {}
    if cmd == "other-backups":
        out = {"backups": [{"i": i, "name": r["name"], "day": r["day"], "count": r["count"]} for i, r in enumerate(other_backups(studio))]}
    elif cmd == "link":
        out = link(studio, ask)
    elif cmd == "naming":
        out = naming(studio)
    elif cmd == "set-naming":
        out = set_naming(studio, ask)
    elif cmd == "next-drives":
        out = {"drives": [{"i": i, "name": r["name"], "free": r["free"], "now": r["now"]} for i, r in enumerate(next_drives(studio))]}
    elif cmd == "set-next-drive":
        out = set_next_drive(studio, ask)
    else:
        sys.exit(__doc__)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
