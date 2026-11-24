#!/usr/bin/env python3
"""The backup's engine, as Nicole's Nov 23 answers have it:

  - ONE backup at a time on this computer (backup_lock.py, taken by night.py): a second start, from the chat or
    from a page, says "A backup is already running." and changes nothing; eject refuses while a backup runs
    from that card; a holder that dies lets go
  - sorting with nobody looking (night.py --by-time): shoots split at FOUR quiet hours, midnight alone is not a
    split, placeholder names that never clash, six first-look photos per shoot chosen by a script, never exit 4
    or 7; the typed shoot name used only when the card holds one shoot
  - the page-started job (backup_job.py): a whole pretend backup by time through to "done"; its record; Start
    pressed twice; a job that died is a "problem", never "running"; a stop is run again once under the same
    name; a card that is gone; a file that will not read (then Try again carries on); the watchdog; the second
    copy afterwards; a folder instead of a card, with a HEIC dated by the file's own time and what was set aside
    said honestly
  - no keyword is written beside any photo, no note to a client, nothing put in the editing queue

Everything is pretend: a scratch STUDIO_HOME, pretend drives (STUDIO_DRIVES_FOR_TESTS), pretend cards (temp
folders with a DCIM). No browser, no window, nothing on the real ~/.studio, no real card or drive.

    python3 tests/backup_job_check.py [--only lock,bytime,job,trouble,second,folder,units,alone]
"""
import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pc_smoke as t  # noqa: E402
import this_computer  # noqa: E402  (pc_smoke put the scripts folder on the path)

FAILED, SKIPPED = [], []
GB = 1024 ** 3
BUSY = "A backup is already running."


def check(what, ok, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {str(detail)[-1200:]}"), flush=True)
    if not ok:
        FAILED.append(what)


def skip(what, why):
    SKIPPED.append(what)
    print(f"  SKIP  {what}   [{why}]", flush=True)


def world(work, name, drives=(("G PAPA", 4000), ("LaCie", 2000))):
    """One pretend computer: its own Studio home, and the drives 'plugged in'."""
    base = work / name
    home, folders = base / "home", base / "folders"
    home.mkdir(parents=True)
    (folders / "Pictures").mkdir(parents=True)
    rows = []
    for dname, total in drives:
        p = base / "drives" / dname
        p.mkdir(parents=True)
        rows.append({"path": str(p), "name": dname, "shown": dname, "total": total * GB, "free": (total // 2) * GB,
                     "system": False, "removable": False, "id": None})
    listing = base / "drives.json"
    listing.write_text(json.dumps(rows), encoding="utf-8")
    env = {"STUDIO_HOME": str(home), "STUDIO_DRIVES_FOR_TESTS": str(listing), "STUDIO_FOLDERS_FOR_TESTS": str(folders),
           "STUDIO_NO_WINDOWS_FOR_TESTS": "1", "PEEK_FACES_PRETEND": str(base / "no-faces.json"),
           "ASSISTANT_CARD_ANSWER_SECONDS": "20"}
    return base, home, env


def card_at(card, bursts, first_number=4471, folder="DCIM/100CANON", housekeeping=True):
    """A pretend card: `bursts` is [(when the burst starts, how many photos)], photos 45 seconds apart."""
    d = card / folder
    d.mkdir(parents=True)
    if housekeeping:
        (card / "MISC").mkdir()
        (card / "MISC" / "M01.CTG").write_bytes(b"camera housekeeping")
    n = 0
    for start, count in bursts:
        when = start
        for i in range(count):
            base = (40 + (n * 9) % 200, 120 + (n * 5) % 120, 200 - (n * 7) % 180)

            def color(bx, by, base=base, i=i):
                return (20, 20, 20) if by < 16 and bx % 8 < 1 + i % 3 else base
            (d / f"IMG_{first_number + n}.JPG").write_bytes(t.jpeg_bytes(600, 400, color, t.exif_blob(when)))
            when += timedelta(seconds=45)
            n += 1
    return sorted(d.glob("*.JPG"))


D4 = datetime(2026, 6, 4)
THREE = [(D4.replace(hour=9), 5), (D4.replace(hour=9, minute=45), 4),              # one shoot: a 40 minute break
         (D4.replace(hour=15), 4),                                               # five quiet hours: a second shoot
         (D4.replace(hour=23, minute=50), 3), (D4 + timedelta(days=1, minutes=10), 3)]   # past midnight: one shoot


def job(env, *args):
    code, out = t.run("backup_job.py", *args, env=env)
    try:
        return code, json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return code, {"_raw": out}


def status(env):
    return job(env, "status")[1]


def wait(env, seconds=180, until=lambda r: r.get("state") != "running"):
    end = time.time() + seconds
    r = {}
    while time.time() < end:
        r = status(env)
        if until(r):
            return r
        time.sleep(0.4)
    return r


def start(env, card, dest, *more):
    return job(env, "start", "--source", card, "--dest", dest, *more)


def log_of(home):
    try:
        return (home / "logs" / "backup-job.log").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def tree(root):
    """Every file under a folder with its size (the Assistant's hidden records left out)."""
    out = {}
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and ".studio" not in p.parts and "_studio" not in p.parts and p.name != ".DS_Store":
            out[p.relative_to(root).as_posix()] = p.stat().st_size
    return out


def photos_on(root):
    return [p for p in Path(root).rglob("*") if p.is_file() and p.suffix.lower() in (".jpg", ".heic") and ".studio" not in p.parts and "_studio" not in p.parts]


def holder(env, source):
    """A separate program that holds the one backup lock, the way a running night.py does, until it is stopped."""
    code = ("import sys, time; sys.path.insert(0, %r); import backup_lock; "
            "ok = backup_lock.take(%r, 'held by the test'); print('HELD' if ok else 'NOT', flush=True); time.sleep(600)"
            % (str(t.SCRIPTS), str(source)))
    p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, env=t.child_env(env), encoding="utf-8")
    said = p.stdout.readline().strip()
    return p, said


# ---------------------------------------------------------------- the lock

def lock_checks(work):
    print("One backup at a time on this computer")
    base, home, env = world(work, "lock")
    drive = base / "drives" / "G PAPA"
    card = base / "CARD"
    card_at(card, [(D4.replace(hour=9), 4)])
    before_card = t.card_snapshot(card)
    p, said = holder(env, card)
    try:
        check("(a pretend backup holds the lock)", said == "HELD", said)
        code, out = t.run("backup_lock.py", env=env)
        check("backup_lock.py says a backup is running (exit 3)", code == 3 and BUSY in out, out)
        code, out = t.run("night.py", "--source", card, "--dest", drive, "--check", env=env)
        check("the quiet check from the chat says so, and stops (exit 2)", code == 2 and BUSY in out, out)
        code, out = t.run("night.py", "--source", card, "--dest", drive, "--name", "second start", "--date", "2026-06-05", env=env)
        check("a second backup from the chat: 'A backup is already running.' (exit 2)", code == 2 and BUSY in out, out)
        check("... and it changed nothing: nothing on the drive, no Studio File, the card as it was",
              not any(drive.iterdir()) and not (home / "studio.json").exists() and t.card_snapshot(card) == before_card, str(list(drive.iterdir())))
        code, got = start(env, card, drive)
        check("a second backup from a page: {ok: false, why: 'A backup is already running.'}", got == {"ok": False, "why": BUSY}, str(got))
        check("... and it changed nothing: no job record, nothing on the drive",
              not (home / "backup-job.json").exists() and not any(drive.iterdir()))
        import importlib
        with t.environ(**env):
            import backup_lock
            import eject_card
            importlib.reload(backup_lock)
            if this_computer.WINDOWS:
                skip("eject refuses while a backup runs from that card", "a PC cannot eject yet")
            else:
                code, words = eject_card.eject(str(card))
                check("Eject my card is refused while a backup is running from that card, in one plain line",
                      code == 2 and words == backup_lock.BUSY_CARD and "/" not in words, f"{code} {words}")
                check("... the answer comes from the lock, before the card is even asked whether it answers",
                      eject_card.backing_up(str(card)) is True and eject_card.backing_up(str(base / "ANOTHER CARD")) is False)
    finally:
        p.kill()
        p.wait()
    time.sleep(0.3)
    code, out = t.run("backup_lock.py", env=env)
    check("the holder died: the computer let go of the lock by itself", code == 0 and "No backup is running." in out, out)
    code, out = t.run("night.py", "--source", card, "--dest", drive, "--check", env=env)
    check("... and the next backup's quiet check is fine again", code == 0 and "PREFLIGHT OK" in out, out)
    with t.environ(**env):
        importlib.reload(backup_lock)
        if not this_computer.WINDOWS:
            code, words = eject_card.eject(str(card))
            check("... and eject no longer says a backup is running (it now says the card is not backed up)",
                  words != backup_lock.BUSY_CARD and code == 2, f"{code} {words}")
    # two real backups at the same moment: exactly one runs
    drive2 = base / "drives" / "LaCie"
    procs = [subprocess.Popen([sys.executable, str(t.SCRIPTS / "night.py"), "--source", str(card), "--dest", str(drive2),
                               "--name", "twins", "--date", "2026-06-05", "--by-time"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=t.child_env(env), encoding="utf-8") for _ in range(2)]
    outs = [p.communicate(timeout=300)[0] for p in procs]
    codes = sorted(p.returncode for p in procs)
    ok, how = t.pictures.ready()
    if ok:
        check("two backups of one card started at the same moment: one runs to the end, the other is told one is running",
              codes == [0, 2] and sum(BUSY in o for o in outs) == 1, f"{codes}\n{outs[0][-300:]}\n---\n{outs[1][-300:]}")
        files = tree(drive2)
        check("... and the one that ran left every photo once, none half-written",
              len([f for f in files if f.endswith(".JPG")]) == 4 and not [f for f in files if "partial" in f], str(files))
    else:
        skip("two backups at the same moment", how)


# ---------------------------------------------------------------- units: by time

def unit_checks(work):
    print("Sorting by time, the rules themselves")
    import importlib
    import groups
    import night
    import peek_sheets
    check("the gap is four hours, a new day alone is not a split, and both are named constants",
          night.BY_TIME_GAP_MIN == 240 and night.BY_TIME_NEW_DAY_SPLITS is False)

    def photos(times):
        return [{"file": f"DCIM/IMG_{i:04d}.JPG", "taken": x.isoformat(timespec="seconds")} for i, x in enumerate(times)]
    day = D4.replace(hour=9)
    times = [day, day + timedelta(hours=3, minutes=59), day + timedelta(hours=8), day + timedelta(hours=8, minutes=1)]
    got, _ = groups.find_groups(photos(times), 240, across_midnight=True)
    check("3 h 59 quiet: still one shoot; 4 h 01: a new one", [g["count"] for g in got] == [2, 2], str([g["count"] for g in got]))
    late = [D4.replace(hour=23, minute=50), D4 + timedelta(days=1, minutes=5)]
    got, _ = groups.find_groups(photos(late), 240, across_midnight=True)
    check("a shoot that runs past midnight stays one shoot by time", len(got) == 1 and got[0]["count"] == 2)
    got, _ = groups.find_groups(photos(late), 15)
    check("the chat's own grouping is untouched: 15 minutes, and a new day still splits", len(got) == 2)
    got, _ = groups.find_groups(photos([D4.replace(hour=20), D4 + timedelta(days=1, hours=7)]), 240, across_midnight=True)
    check("an evening and the next morning are two shoots (eleven quiet hours)", len(got) == 2)

    # placeholder names
    base, home, env = world(work, "units")
    place = base / "drives" / "G PAPA"
    session = place / "2026-06-05 friday card"
    studio = session / "_studio"
    studio.mkdir(parents=True)
    (place / "Shoot 1_06-04-26").mkdir()
    (place / "shoot 3_06-04-26").mkdir()          # most drives ignore capitals
    gs = [{"id": f"g{i:02d}", "start": "2026-06-04T09:00:00", "end": "2026-06-04T09:10:00", "photos": 5, "count": 5, "files": []} for i in (1, 2, 3)]
    (studio / "groups.json").write_text(json.dumps({"groups": gs}), encoding="utf-8")
    with t.environ(**env):
        import studio_file
        importlib.reload(studio_file)
        sf = studio_file.load()
        sf.setdefault("naming", {}).update(studio_file.OFFERED[0])
        studio_file.save(sf)
        importlib.reload(night)
        shoots, used = night.by_time_shoots(session, studio, "Garcia")
    names = [s["suggested"] for s in shoots]
    check("three shoots get three placeholder names that differ, with no date in them",
          len(set(names)) == 3 and all("2026" not in n and "06" not in n for n in names), str(names))
    check("a placeholder never takes a folder that is already where the shoots will settle (capitals ignored)",
          names == ["Shoot 2", "Shoot 4", "Shoot 5"], str(names))
    rec = json.loads((studio / "shoots.json").read_text(encoding="utf-8"))
    check("shoots.json says who decided, one group per shoot, each marked as a placeholder, and passes the backup's own check",
          rec["decided_by"] == night.BY_TIME and [s["groups"] for s in rec["shoots"]] == [["g01"], ["g02"], ["g03"]]
          and all(s["placeholder"] for s in rec["shoots"]) and night.check_shoots(studio) is None, str(rec)[:300])
    told = json.loads((studio / "told.json").read_text(encoding="utf-8"))["text"] if (studio / "told.json").exists() else ""
    check("the typed shoot name is not used for three shoots; it is kept, word for word, for the naming afterwards",
          used is False and "Garcia" not in names and told == "Shoot name typed before the backup: Garcia", told)
    (studio / "shoots.json").unlink()
    (studio / "groups.json").write_text(json.dumps({"groups": gs[:1]}), encoding="utf-8")
    # a folder of theirs with an accent, spelled the way a Mac's drives list it (the e and its mark as two letters)
    import unicodedata
    theirs = place / unicodedata.normalize("NFD", "Zo\u00eb_06-04-26")
    theirs.mkdir()
    with t.environ(**env):
        shoots, used = night.by_time_shoots(session, studio, "Zo\u00eb")
    check("a typed name with an accent never wants a folder that is already there, however the drive spells the accent",
          used is False and shoots[0]["suggested"] != "Zo\u00eb" and shoots[0]["placeholder"] is True
          and night.same_name(theirs.name) == night.same_name("ZO\u00cb_06-04-26"), str(shoots))
    (studio / "shoots.json").unlink()
    (studio / "told.json").unlink()
    with t.environ(**env):
        shoots, used = night.by_time_shoots(session, studio, "  The Johnson   Family ")
    check("one shoot on the card: the typed name is the shoot's name (spaces tidied), not a placeholder",
          used is True and shoots[0]["suggested"] == "The Johnson Family" and shoots[0]["placeholder"] is False, str(shoots))

    # the six, by script
    ms = [{"n": i} for i in range(1, 19)]
    six = peek_sheets.auto_choose(ms, {})
    check("six first-look photos spread from the first moment to the last", six == [1, 4, 8, 11, 15, 18], str(six))
    check("the same moments give the same six (it is a rule, not a draw)", peek_sheets.auto_choose(ms, {}) == six)
    flagged = {str(n): {"flags": ["mouth open"], "judged": True, "notes": []} for n in (1, 4, 8, 11, 15, 18)}
    got = peek_sheets.auto_choose(ms, flagged)
    check("a face the check flagged is passed over while there are six others", len(got) == 6 and not set(got) & {1, 4, 8, 11, 15, 18}, str(got))
    best = {"9": {"flags": [], "judged": True, "notes": [], "measured": {"quality": 0.9, "face": 0.1}}}
    got = peek_sheets.auto_choose([{"n": i} for i in (1, 5, 9, 13, 17, 21)], best)
    check("the clearest face looking at the camera goes first (the big spot)", got[0] == 9 and sorted(got) == [1, 5, 9, 13, 17, 21], str(got))
    away = {"9": {"flags": [], "judged": True, "notes": ["looking away"], "measured": {"quality": 0.9, "face": 0.1}}}
    check("... never one that is looking away", peek_sheets.auto_choose([{"n": i} for i in (1, 5, 9)], away)[0] == 1)
    check("fewer than six moments: all of them; none: none",
          peek_sheets.auto_choose(ms[:4], {}) == [1, 2, 3, 4] and peek_sheets.auto_choose([], {}) == [])
    few = peek_sheets.auto_choose(ms[:7], {str(n): {"flags": ["x"]} for n in range(1, 6)})
    check("too few without a fault: the clean ones are all in, flagged ones only make up the six", {6, 7} <= set(few) and len(few) == 6, str(few))

    # no keyword beside a photo (a RAW is the kind that used to get a small 'sneak peek' file beside it)
    night_dir = base / "an older night"
    st = night_dir / "_studio"
    (night_dir / "Beach").mkdir(parents=True)
    st.mkdir()
    for n in (1, 2):
        (night_dir / "Beach" / f"Beach_000{n}_IMG_{n}.CR3").write_bytes(b"a pretend raw photo %d" % n)
    old = night_dir / "Beach" / "Beach_0002_IMG_2.xmp"
    old.write_bytes(b"<x:xmpmeta>a sidecar an older backup wrote: sneak peek</x:xmpmeta>")
    (st / "manifest.json").write_text(json.dumps({"session": "an older night", "files": {}}), encoding="utf-8")
    (st / "sneak-peeks.json").write_text(json.dumps({"picks": [{"file": f"Beach/Beach_000{n}_IMG_{n}.CR3", "shoot": "s1"} for n in (1, 2)]}), encoding="utf-8")
    code, out = t.run("sneak_peeks.py", "--night", night_dir, "--no-previews", env=env)
    xmps = sorted(x.name for x in night_dir.rglob("*.xmp"))
    check("the first-look photos get NO keyword: nothing is written beside a RAW pick",
          code == 0 and xmps == ["Beach_0002_IMG_2.xmp"], f"{code} {xmps} {out[-200:]}")
    check("... and a sidecar an older backup wrote is left exactly as it is",
          old.read_bytes() == b"<x:xmpmeta>a sidecar an older backup wrote: sneak peek</x:xmpmeta>" and not (st / "sidecars-set-aside").exists())
    import sneak_peeks
    check("the switch that would mark them again is off", sneak_peeks.MARK_IN_LIGHTROOM is False)

    # words
    import backup_job
    lines = list(backup_job.OUR_WORDS.values()) + [backup_lock_words()]
    instructions_checks()
    check("none of the job's words holds a path, 'Claude', 'your assistant', an em dash or 'sneak peek'",
          not [x for x in lines if "/" in x.replace("and/or", "") or "Claude" in x or "your assistant" in x.lower() or "—" in x or "sneak" in x.lower()], str(lines))
    check("a line with a path in it is never shown: the known places are said by name, anything else is dropped",
          backup_job.no_path("The card is not there: /Volumes/EOS", {"source": "/Volumes/EOS"}) == "The card is not there: your card"
          and backup_job.no_path("Cannot write to /Volumes/Other/x", {}) is None
          and backup_job.no_path("see C:\\Users\\me\\x", {}) is None and backup_job.no_path("look in _studio/report.html", {}) is None)

    record_read_checks(work)


RECORD_READ = r"""
import json, sys, time
sys.path.insert(0, sys.argv[1])
import backup_job as J
from pathlib import Path
J.write(J.blank(state="running", card="EOS_DIGITAL"))
real = Path.read_text
left = {"n": int(sys.argv[2])}
def held(self, *a, **k):
    if self == J.JOB and left["n"] > 0:
        left["n"] -= 1
        raise PermissionError(13, "The process cannot access the file because it is being used by another process")
    return real(self, *a, **k)
Path.read_text = held
t0 = time.time()
got = J.read()
print(json.dumps({"state": (got or {}).get("state"), "card": (got or {}).get("card"), "took": round(time.time() - t0, 2), "left": left["n"]}))
"""


def record_read_checks(work):
    """A PC won't open the job's record in the instant a newer one is being put in its place. Before Nov 23 that
    one look read as "no job at all" (state idle), and GitHub's PC caught it: a job just started was told as
    nothing running. Played here on either computer by refusing the first reads the way a PC does."""
    print("The job's record, read in the instant it is being saved (a PC refuses the open for a moment)")
    home = work / "record-read"
    home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, STUDIO_HOME=str(home), PYTHONIOENCODING="utf-8")

    def ask(refusals):
        r = subprocess.run([sys.executable, "-c", RECORD_READ, str(t.SCRIPTS), str(refusals)], env=env, capture_output=True, text=True, timeout=60)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {"error": (r.stdout + r.stderr)[-600:]}
    got = ask(3)
    check("refused three times and then let in: the record is read (running, the card), never taken for no job",
          got.get("state") == "running" and got.get("card") == "EOS_DIGITAL" and got.get("left") == 0, str(got))
    got = ask(10 ** 6)
    check("refused for good: no record (as before), after about half a second, never a wait without end",
          got.get("state") is None and "error" not in got and 0.2 <= got.get("took", 99) < 5, str(got))
    got = ask(0)
    check("never refused (a Mac, and a PC nearly always): read at once", got.get("state") == "running" and got.get("took", 99) < 0.2, str(got))


def instructions_checks():
    part = (t.SCRIPTS.parent / "parts" / "backup.md").read_text(encoding="utf-8")
    check("the instructions say where files that are not a photo were set aside, that a folder is never called a card, "
          "and that a record can say running after its job stopped",
          "`from-the-card`" in part and "is never called a card" in part and "turns to done by itself" in part
          and "nothing could be sorted into shoots" in part)


def backup_job_words():
    import backup_job
    return backup_job.OUR_WORDS


def backup_lock_words():
    import backup_lock
    return backup_lock.BUSY + " " + backup_lock.BUSY_CARD


# ---------------------------------------------------------------- a whole backup by time, from a page

def job_checks(work):
    print("A whole pretend backup started from a page, sorted by time")
    ok, how = t.pictures.ready()
    if not ok:
        skip("everything that needs a whole backup", how)
        return None
    base, home, env = world(work, "job")
    dest = base / "drives" / "G PAPA" / "CLIENT WORK"
    dest.mkdir()
    card = base / "EOS_DIGITAL"
    card_at(card, THREE)
    before = t.card_snapshot(card)
    check("before anything: the record says idle", status(env).get("state") == "idle")
    slow = dict(env, STUDIO_BACKUP_JOB_PAUSE_FOR_TESTS="4")
    code, got = start(slow, card, dest, "--shoot-name", "Garcia")
    check("Start: one line of JSON, {ok: true}", code == 0 and got == {"ok": True}, str(got))
    r = status(env)
    check("at once the record says running, copying, the card, the drive and the folder by name",
          r.get("state") == "running" and r.get("step") == "copying" and r.get("card") == "EOS_DIGITAL"
          and r.get("drive") == "G PAPA" and r.get("folders") == ["CLIENT WORK"] and r.get("second") is None and r.get("finished") is None, str(r))
    code, again = start(env, card, dest)
    check("Start pressed again while it runs: 'A backup is already running.', and the record is the first job's still",
          again == {"ok": False, "why": BUSY} and status(env).get("started") == r.get("started"), str(again))
    code, out = t.run("night.py", "--source", card, "--dest", dest, "--name", "from the chat", env=env)
    check("the chat starting a backup while a page's job is alive is told the same (exit 2), nothing made",
          code == 2 and BUSY in out and not any(dest.iterdir()), out[-300:])
    if not this_computer.WINDOWS:
        with t.environ(**env):
            import importlib
            import backup_lock
            import eject_card
            importlib.reload(backup_lock)
            code, words = eject_card.eject(str(card))
        check("Eject my card is refused while the page's job is alive (even between its steps)", code == 2 and words == backup_lock.BUSY_CARD, f"{code} {words}")
    r = wait(env)
    log = log_of(home)
    check("the job runs to done with nobody looking: never a stop for the look (4) or the picks (7)",
          r.get("state") == "done" and r.get("step") == "done" and "NEEDS A LOOK" not in log and "NEEDS THE PICKS" not in log, json.dumps(r)[:500] + log[-1500:])
    if r.get("state") != "done":
        return None
    n_files = len(before)
    check("the record: every file counted, three shoots, when it finished, the backup's name, and where its records are",
          r["done"] == r["total"] == n_files and r["shoots"] == 3 and r["finished"] and r["backup"].endswith(" card")
          and Path(r["records"]).is_dir() and (Path(r["records"]) / "report.html").is_file(), str(r))
    page = job(env, "status", "--page")[1]
    check("the record as a page may have it holds no path at all (no records, nothing private)",
          "records" not in page and "private" not in page and str(base) not in json.dumps(page) and page.get("state") == "done", str(page))
    records = Path(r["records"])
    folders = sorted(p.name for p in dest.iterdir() if p.is_dir() and not p.name.startswith("."))
    check("three shoot folders, split at four quiet hours: 40 minutes is one shoot, five hours a new one, midnight alone is not a split",
          folders == ["Shoot 1_06-04-26", "Shoot 2_06-04-26", "Shoot 3_06-04-26"], str(folders))
    counts = [len(list((dest / f).glob("*.JPG"))) for f in folders]
    check("... holding 9, 4 and 6 photos", counts == [9, 4, 6], str(counts))
    check("the day folder is gone (settled), and the photos are named for the placeholder with the camera's name kept",
          not [p for p in dest.iterdir() if "card" in p.name and p.is_dir() and not p.name.startswith(".")]
          and (dest / "Shoot 1_06-04-26" / "Shoot_0001_IMG_4471.JPG").is_file(), str(sorted(x.name for x in (dest / "Shoot 1_06-04-26").iterdir())[:3]))
    index = json.loads((records / "index.json").read_text(encoding="utf-8"))
    manifest = json.loads((records / "manifest.json").read_text(encoding="utf-8"))
    check("every photo on the drive is byte for byte the card's", t.photos_match(dest, index, card))
    check("every file's copy was checked, no problems on record", bool(manifest["files"]) and not manifest.get("problems")
          and all(v.get("dest", {}).get("ok") for v in manifest["files"].values()))
    check("the card is exactly as it was", t.card_snapshot(card) == before)
    shoots = json.loads((records / "shoots.json").read_text(encoding="utf-8"))
    check("shoots.json: decided by time, each a placeholder", shoots["decided_by"] == "the backup, by time" and all(s.get("placeholder") for s in shoots["shoots"]))
    told = json.loads((records / "told.json").read_text(encoding="utf-8"))["text"] if (records / "told.json").exists() else ""
    check("the shoot name typed in the popup is not used (three shoots) and is kept for the naming afterwards", "Garcia" in told and "Garcia" not in " ".join(folders), told)
    picks = json.loads((records / "sneak-peeks.json").read_text(encoding="utf-8"))
    per = {s: [p for p in picks["picks"] if p["shoot"] == s] for s in ("s1", "s2", "s3")}
    check("six first-look photos per shoot (four in the shoot of four), chosen by the backup itself, never by Claude",
          [len(v) for v in per.values()] == [6, 4, 6] and picks["picked_by"] == "the backup, by time", str({k: len(v) for k, v in per.items()}))
    check("... each with its picture for the report", len(list((records / "sneak-peeks").glob("*.jpg"))) == 16)
    sidecars = [p for p in dest.rglob("*") if p.suffix.lower() == ".xmp"]
    check("no keyword is written beside any photo (no sidecar anywhere on the drive)", not sidecars, str(sidecars))
    report = (records / "report.html").read_text(encoding="utf-8")
    import re
    seen = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", report, flags=re.S)
    check("the report: 'A first look at your shoot.' under the six, and nothing about sneak peeks, Lightroom or a note to a client",
          seen.count("A first look at your shoot.") >= 3 and not re.search(r"sneak peek|Lightroom|note to (my|your) client|Write a note", seen, re.I),
          str(re.findall(r".{40}(?:sneak peek|Lightroom|Write a note).{40}", seen, re.I | re.S)[:3]))
    check("no note to a client anywhere in the records", not (records / "notes").exists())
    check("a CARD's report still says the card is safe to format, and its records say it was a card",
          "The card is safe to format when you're ready" in (records / "report.html").read_text(encoding="utf-8")
          and manifest.get("source_kind") == "card", str(manifest.get("source_kind")))
    q = json.loads((home / "queue.json").read_text(encoding="utf-8")) if (home / "queue.json").exists() else {"shoots": []}
    mine = [s for s in q["shoots"] if "Shoot" in str(s.get("name"))]
    check("the three shoots are registered (Your backups, Uploaded shoots) and NOT put in the editing queue",
          len(mine) == 3 and all(s.get("status") != "waiting" and not s.get("due") for s in mine), str([(s.get("name"), s.get("status")) for s in mine]))
    code, out = t.run("backup_job.py", "status", "--words", env=env)
    check("for the chat: how the page's backup went, in plain words", code == 0 and "is done" in out and "3 shoots" in out and "EOS_DIGITAL" in out, out)
    check("the Studio File got the naming every new backup gets (a very first backup from a page has none on file)",
          json.loads((home / "studio.json").read_text(encoding="utf-8"))["naming"].get("folder_pattern") == "{shoot}_{date}")

    # the same card again: nothing copied
    on_drive = tree(dest)
    code, got = start(env, card, dest)
    r2 = wait(env)
    check("the same card again: done, 'already backed up', and not a file copied",
          got.get("ok") is True and r2.get("state") == "done" and r2.get("already") is True and "already backed up" in (r2.get("line") or "")
          and tree(dest) == on_drive and Path(r2.get("records") or "x").is_dir(), str(r2))

    # a second card the same day, same dates: its own backup, its placeholders never clash with the first card's
    card2 = base / "CARD TWO"
    card_at(card2, [(D4.replace(hour=10), 3), (D4.replace(hour=18), 3)], first_number=9001)
    code, got = start(env, card2, dest)
    r3 = wait(env)
    folders2 = sorted(p.name for p in dest.iterdir() if p.is_dir() and not p.name.startswith("."))
    check("a second card of the same day: its own backup (the next free name), done",
          r3.get("state") == "done" and r3.get("backup") != r.get("backup") and r3.get("shoots") == 2, str(r3))
    check("... its shoots take the next placeholder numbers, so nothing clashes and everything settles",
          folders2 == folders + ["Shoot 4_06-04-26", "Shoot 5_06-04-26"] and not [f for f in folders2 if "card" in f], str(folders2))
    check("... and the first card's folders are exactly as they were", {k: v for k, v in tree(dest).items() if k in on_drive} == on_drive)

    # one shoot and a name
    card3 = base / "CARD THREE"
    card_at(card3, [(D4.replace(month=7, hour=11), 5)], first_number=7001)
    code, got = start(env, card3, dest, "--shoot-name", "The Johnson Family")
    r4 = wait(env)
    check("a card with ONE shoot and a name typed in the popup: the folder and the photos take it",
          r4.get("state") == "done" and (dest / "The Johnson Family_07-04-26" / "Johnson_0001_IMG_7001.JPG").is_file(),
          str(sorted(p.name for p in dest.iterdir())))
    return base, home, env, dest


# ---------------------------------------------------------------- trouble

def trouble_checks(work):
    print("Trouble: a job that dies, a stop that is run again, a card that goes, a file that will not read, the watchdog")
    ok, how = t.pictures.ready()
    if not ok:
        skip("everything that needs a whole backup", how)
        return
    base, home, env = world(work, "trouble")
    dest = base / "drives" / "G PAPA"

    # the job's process dies
    card = base / "CARD A"
    card_at(card, [(D4.replace(hour=9), 6)])
    before = t.card_snapshot(card)
    code, got = start(dict(env, STUDIO_BACKUP_JOB_PAUSE_FOR_TESTS="60"), card, dest)
    r = wait(env, 20, lambda r: (r.get("private") or {}).get("pid"))
    pid = (r.get("private") or {}).get("pid")
    check("(the job is up and waiting)", isinstance(pid, int) and r.get("state") == "running", str(r))
    this_computer.stop_tree(pid)
    time.sleep(0.5)
    r = status(env)
    check("the job's process was killed: the record says problem, in plain words, never 'running' for ever",
          r.get("state") == "problem" and "Try again" in (r.get("line") or "") and r.get("finished"), str(r))
    check("... and that is what the record on disk now says too (a page reload reads the same)",
          json.loads((home / "backup-job.json").read_text(encoding="utf-8")).get("state") == "problem")
    code, out = t.run("backup_lock.py", env=env)
    check("... and nothing is left locked", code == 0, out)

    # a stop that is not 'done', 'problems' or 'stop' is run again once, under the same name
    code, got = start(dict(env, STUDIO_BACKUP_JOB_BUDGET_FOR_TESTS="0.001"), card, dest)
    r = wait(env)
    log = log_of(home)
    check("the backup paused part way (exit 3): the job ran it again by itself, once, and it finished",
          r.get("state") == "done" and "night.py ended with 3; running it again, same name" in log and log.count("PAUSED after") == 1, str(r) + log[-800:])
    days = [p.name for p in (dest / ".studio").iterdir()] if (dest / ".studio").is_dir() else []
    check("... in ONE backup folder (the rerun used the same name and day), every photo once, the card as it was",
          len(days) == 1 and len(photos_on(dest)) == 6 and t.card_snapshot(card) == before, f"{days} {len(photos_on(dest))}")
    records = Path(r["records"])
    m = json.loads((records / "manifest.json").read_text(encoding="utf-8"))
    check("... every file checked, and the first file was not copied a second time over itself",
          all(v["dest"]["ok"] for v in m["files"].values()) and not m.get("problems"))

    # the card is gone when the job gets to it
    card_b = base / "CARD B"
    card_at(card_b, [(D4.replace(hour=13), 5)], first_number=5001)
    on_drive = tree(dest)
    code, got = start(dict(env, STUDIO_BACKUP_JOB_PAUSE_FOR_TESTS="3"), card_b, dest)
    card_b.rename(base / "CARD B pulled out")
    r = wait(env)
    check("the card is pulled before the copy: a problem in plain words, with no path, and not a file copied",
          r.get("state") == "problem" and "memory card" in (r.get("line") or "") and str(base) not in (r.get("line") or "") and tree(dest) == on_drive, str(r))
    (base / "CARD B pulled out").rename(card_b)
    code, got = start(env, base / "NO SUCH CARD", dest)
    check("Start on a card that is not there: {ok: false} in plain words, and the record is not touched",
          got.get("ok") is False and "can't see" in got.get("why", "") and status(env).get("card") == "CARD B", str(got))

    # a photo that will not read, mid-copy; then Try again
    if this_computer.WINDOWS or os.geteuid() == 0:
        skip("a photo that will not read mid-copy", "needs a file this user cannot read")
    else:
        bad = sorted((card_b / "DCIM" / "100CANON").glob("*.JPG"))[2]
        bad.chmod(0)
        try:
            code, got = start(env, card_b, dest)
            r = wait(env)
            check("a photo on the card will not read mid-copy: the job stops as a problem, never 'done'",
                  r.get("state") == "problem" and r.get("step") == "copying" and r.get("line") and str(base) not in r["line"], str(r))
            session = Path(r["private"]["session"])
            m = json.loads((session / "_studio" / "manifest.json").read_text(encoding="utf-8"))
            good = [k for k, v in m["files"].items() if v.get("dest", {}).get("ok")]
            check("... what was copied before it is kept and on record; the card is not in the ledger (not called backed up)",
                  len(good) >= 2 and not (home / "cards.json").exists() or str(card_b) not in (home / "cards.json").read_text(encoding="utf-8"), str(good))
            first = (session / good[0])
            stamp = first.stat().st_mtime_ns, first.stat().st_ino
        finally:
            bad.chmod(0o644)
        # ... and they only press Try again the NEXT day: made to look so here, by giving the stopped backup
        # yesterday's day and name (its folder, and what the job's record remembers of it)
        rec = json.loads((home / "backup-job.json").read_text(encoding="utf-8"))
        old = session.with_name("2026-06-01 monday card")
        session.rename(old)
        m["session"] = old.name
        (old / "_studio" / "manifest.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
        rec["private"].update(name="monday card", date="2026-06-01", session=str(old))
        rec["backup"] = old.name
        (home / "backup-job.json").write_text(json.dumps(rec), encoding="utf-8")
        code, got = start(env, card_b, dest)
        r2 = wait(env)
        check("Try again once the photo reads, even on a later day: the same backup carries on under the same name and day, and finishes",
              r2.get("state") == "done" and r2.get("backup") == "2026-06-01 monday card" and r2.get("total") == r2.get("done"), str(r2))
        check("... no second backup folder was started for that card (nothing copied twice)",
              sorted(x.name for x in (dest / ".studio").iterdir() if "card" in x.name).count("2026-06-01 monday card") == 1
              and not [x for x in dest.iterdir() if x.is_dir() and x.name.endswith(" card")]
              and len([x for x in (dest / ".studio").iterdir() if x.is_dir()]) == 2, str(sorted(x.name for x in (dest / ".studio").iterdir())))
        check("... every photo of that card once, byte for byte, none half-written",
              len([p for p in photos_on(dest) if "IMG_50" in p.name]) == 5 and not list(dest.rglob("*.studio-partial")))

    # the watchdog
    if not hasattr(os, "mkfifo"):
        skip("the watchdog", "this computer cannot make a file that never answers")
    else:
        card_c = base / "CARD C"
        card_at(card_c, [(D4.replace(hour=16), 4)], first_number=6001)
        fifo = card_c / "DCIM" / "100CANON" / "ZZZ_NEVER_ANSWERS.JPG"
        os.mkfifo(fifo)          # reading it waits for ever, the way a card that has gone quiet does
        try:
            t0 = time.time()
            code, got = start(dict(env, STUDIO_BACKUP_JOB_QUIET_FOR_TESTS="6"), card_c, dest)
            r = wait(env, 120)
            check("the card stops answering mid-copy: after the quiet limit the job stops the backup and says so plainly",
                  r.get("state") == "problem" and "stopped answering" in (r.get("line") or "") and time.time() - t0 < 90
                  and "WATCHDOG" in log_of(home), str(r))
            time.sleep(1)
            code, out = t.run("backup_lock.py", env=env)
            check("... the stuck backup was really stopped: nothing is left running or locked", code == 0, out)
            check("... and the photos copied before it went quiet are kept",
                  len([p for p in Path(r["private"]["session"]).rglob("IMG_60*.JPG")]) == 4)
        finally:
            fifo.unlink()
        code, got = start(env, card_c, dest)
        r2 = wait(env)
        check("Try again once the card answers: the same backup finishes", r2.get("state") == "done" and r2.get("backup") == r.get("backup"), str(r2))


# ---------------------------------------------------------------- the second copy

def second_checks(work):
    print("A second copy asked for in the popup: made after the backup, by second_copy.py")
    ok, how = t.pictures.ready()
    if not ok:
        skip("the second copy", how)
        return
    base, home, env = world(work, "second")
    dest, second = base / "drives" / "G PAPA", base / "drives" / "LaCie"
    card = base / "CARD"
    card_at(card, [(D4.replace(hour=9), 5), (D4.replace(hour=16), 4)])
    code, got = start(env, card, dest, "--second", second)
    r = status(env)
    check("the record names the second drive from the start", got == {"ok": True} and r.get("second") == "LaCie", str(r))
    r = wait(env)
    check("done only after the second copy: second_ok, and the count is every file",
          r.get("state") == "done" and r.get("second_ok") is True and r.get("done") == r.get("total") and r["total"] > 0, str(r))
    check("the second drive holds every photo of the card", len(photos_on(second)) + len(list(second.rglob("_studio/../**/*.JPG"))) >= 9
          or len([p for p in second.rglob("*.JPG")]) == 9, str(len(list(second.rglob("*.JPG")))))
    m = json.loads((Path(r["records"]) / "manifest.json").read_text(encoding="utf-8"))
    check("the backup's own records say every file's second copy was checked",
          bool(m.get("second")) and all((v.get("second") or {}).get("ok") for v in m["files"].values()))
    log = log_of(home)
    check("the second copy came after the backup itself was finished (never inside the copy)",
          0 < log.find("Done. Report:") < log.find("Second copy of") or "Second copy" in log[log.find("Done. Report:"):], log[-600:])
    # a second drive remembered from before is NOT used by a page's backup: the popup asks each time (Nicole, Nov 23)
    t.run("studio_file.py", "set", "--drive", dest, "--second", second, env=env)
    saved = json.loads((home / "studio.json").read_text(encoding="utf-8")).get("drives", {}).get("second")
    card3 = base / "CARD 3"
    card_at(card3, [(D4.replace(month=9, hour=9), 3)], first_number=3001)
    had = len(list(second.rglob("*.JPG")))
    code, got = start(env, card3, dest)
    r = wait(env)
    check("a second drive saved before, and none asked for in the popup: the backup is done with ONE copy (it is asked each time)",
          bool(saved) and r.get("state") == "done" and r.get("second") is None and len(list(second.rglob("*.JPG"))) == had
          and "second_ok" not in r, f"saved={saved} {r}")
    # a second drive that cannot take it never breaks the backup
    card2 = base / "CARD 2"
    card_at(card2, [(D4.replace(month=8, hour=9), 4)], first_number=8001)
    code, got = start(env, card2, dest, "--second", dest / "a folder on the same drive")
    check("a second place that is not there: Start says so, nothing begun", got.get("ok") is False and "second copy" in got.get("why", ""), str(got))
    (dest / "Second here").mkdir()
    code, got = start(env, card2, dest, "--second", dest / "Second here")
    r = wait(env)
    check("a second copy that is refused (the same drive): the backup itself is DONE and checked; the record says the second copy is not made, and why",
          r.get("state") == "done" and r.get("second_ok") is False and "second copy" in (r.get("line") or "").lower()
          and str(base) not in (r.get("line") or "") and r.get("shoots") == 1, str(r))
    check("... and the numbers on that finished record are the backup's own (every file), never '0 of 4'",
          r.get("done") == r.get("total") and r.get("total", 0) >= 4, f"{r.get('done')} of {r.get('total')}")


# ---------------------------------------------------------------- a folder instead of a card

def folder_checks(work):
    print("Back up a folder instead, through the same job")
    ok, how = t.pictures.ready()
    if not ok:
        skip("a folder instead", how)
        return
    base, home, env = world(work, "folder")
    dest = base / "drives" / "G PAPA"
    src = base / "folders" / "Downloads" / "Lake trip"
    photos = card_at(src, [(D4.replace(hour=9), 4)], folder="from my phone", housekeeping=False)
    heic = src / "from my phone" / "IMG_0099.HEIC"
    heic.write_bytes(b"\x00\x00\x00\x18ftypheic" + b"not a real picture, and no date inside" * 20)
    when = D4.replace(hour=9, minute=10).timestamp()
    os.utime(heic, (when, when))
    (src / "from my phone" / "no date at all.JPG").write_bytes(t.jpeg_bytes(300, 200, lambda x, y: (90, 90, 200)))
    (src / "notes.txt").write_text("the lake, in June", encoding="utf-8")
    (src / "Zo\u00eb final.psd").write_bytes(b"8BPS" + b"a Photoshop file of theirs" * 40)
    (src / "contract.pdf").write_bytes(b"%PDF-1.4 a contract of theirs")
    before = t.card_snapshot(src)
    code, got = start(env, src, dest)
    r = wait(env)
    check("a folder is backed up like a card: done, named for the folder, not called a card",
          got == {"ok": True} and r.get("state") == "done" and r.get("card") == "Lake trip" and r.get("backup", "").endswith(" folder"), str(r))
    if r.get("state") != "done":
        print(log_of(home)[-2500:])
        return
    records = Path(r["records"])
    index = json.loads((records / "index.json").read_text(encoding="utf-8"))
    h = next((p for p in index["photos"] if p["file"].upper().endswith(".HEIC") or "IMG_0099" in p["file"]), {})
    check("a HEIC whose date cannot be read is dated by the file's own time, and the record says so",
          h.get("taken") == datetime.fromtimestamp(when).isoformat(timespec="seconds") and h.get("taken_from") == "the file's own time", str(h))
    shoot = next(p for p in dest.iterdir() if p.is_dir() and not p.name.startswith("."))
    names = sorted(p.name for p in shoot.iterdir())
    check("... so it is sorted into its shoot with the photos around it, not set aside out of sight",
          any("IMG_0099" in n for n in names) and len(names) == 5, str(names))
    check("the record says honestly what was set aside: one photo with no date, three files that are not a photo, by kind",
          r.get("set_aside") == {"undated": 1, "other": 3, "kinds": ["pdf", "psd", "txt"]} and "1 photo or video clip with no date" in r.get("line", "")
          and "3 files that are not a photo or a video clip (pdf, psd, txt)" in r["line"] and str(base) not in r["line"],
          str(r.get("set_aside")) + " " + str(r.get("line")))
    check("... and their own Photoshop file, PDF and notes are never called camera housekeeping",
          "housekeeping" not in r.get("line", "") and "housekeeping" not in " ".join(backup_job_words().values()), r.get("line"))
    # the report of a folder never talks about a memory card (least of all one that is safe to format)
    manifest = json.loads((records / "manifest.json").read_text(encoding="utf-8"))
    page = (records / "report.html").read_text(encoding="utf-8")
    text = " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", page)).split())
    lied = [w for w in ("memory card", "safe to format", "against the card", "What's on the card", "eep the card") if w in text]
    check("the backup's records say a folder was backed up, not a card", manifest.get("source_kind") == "folder", str(manifest.get("source_kind")))
    check("the report of a folder never says memory card, 'checked against the card' or 'safe to format'", not lied, str(lied))
    check("... it says the folder is as it was, that everything is copied and checked, and what was in the folder",
          "The folder you backed up is exactly as it was" in text and "Everything is copied and checked" in text
          and "What was in the folder" in text and "checked against the original, byte for byte" in text, text[:600])
    check("... and names the undated photo as a photo, apart from the three files that are not",
          "1 photo or video clip with no date" in text and "3 files that are not a photo or a video clip (pdf, psd, txt)" in text, text[-900:])
    plain = (records / "morning-report.md").read_text(encoding="utf-8") if (records / "morning-report.md").exists() else ""
    check("the plain-text report says the same (no memory card, nothing safe to format)",
          "the folder you backed up is exactly as it was" in plain and "memory card" not in plain and "safe to format" not in plain, plain[-500:])
    with t.environ(**env):
        import home_base
        st = home_base.backup_status(records)
    check("the Back up a card screen: this backup is a folder ('Copied and checked'), not a card that is safe to format",
          st.get("folder") is True and st.get("safe") is True and "W.folder_safe" in Path(home_base.__file__).read_text(encoding="utf-8")
          and home_base.OUR_WORDS.get("folder_safe") == "Copied and checked", str(st))
    log = log_of(home)
    check("the sorter's own words no longer call an undated photo 'not a photo'",
          "1 photo or video clip with no date could not be sorted into a shoot" in log and "3 files that are not photos set aside" in log, log[-900:])
    aside = records / "from-the-card"
    check("what was set aside is kept, copied and checked, with the backup's records (nothing deleted)",
          (aside / "from my phone" / "no date at all.JPG").is_file() and (aside / "notes.txt").is_file())
    check("the folder that was backed up is exactly as it was", t.card_snapshot(src) == before)
    (dest / "Backups go here").mkdir()
    code, got = start(env, dest, dest / "Backups go here")
    r = wait(env)
    # a folder whose photos carry no date at all (web exports with the date stripped)
    bare = base / "folders" / "Downloads" / "Web exports"
    bare.mkdir(parents=True)
    for i in range(4):
        (bare / f"export-{i}.jpg").write_bytes(t.jpeg_bytes(300, 200, lambda x, y, i=i: (40 * i, 90, 200)))
    was = t.card_snapshot(bare)
    code, got = start(env, bare, dest)
    r2 = wait(env)
    check("a folder of photos with no date: done, every file copied and checked, and the record SAYS none could be sorted into a shoot",
          r2.get("state") == "done" and r2.get("done") == r2.get("total") == 4 and not r2.get("shoots") and r2.get("unsorted") == 4
          and "could not be sorted into shoots" in (r2.get("line") or "") and "All 4 files are copied and checked" in r2["line"], str(r2))
    check("... it names the one folder they are in, by name only (no path), and that folder holds them",
          (r2.get("backup") or "") in (r2.get("line") or "") and bool(r2.get("backup")) and str(base) not in r2["line"] and "/" not in r2["line"]
          and len(list((dest / r2["backup"]).glob("export-*.jpg"))) == 4, str(r2.get("line")))
    check("... and the folder that was backed up is exactly as it was", t.card_snapshot(bare) == was)
    on_drive = tree(dest)
    check("a folder that would be backed up into itself is refused in plain words with no path, and nothing is copied",
          r.get("state") == "problem" and "inside the very folder being backed up" in (r.get("line") or "")
          and str(base) not in r["line"] and "/" not in r["line"] and tree(dest) == on_drive, str(r))


# ---------------------------------------------------------------- the job dies, the backup does not (Nov 23 review)

def kill_one(pid):
    """Stop ONE process and nothing it started (the job without its night.py; night.py without its copy)."""
    try:
        os.kill(int(pid), signal.SIGTERM if this_computer.WINDOWS else signal.SIGKILL)
    except (OSError, TypeError, ValueError):
        pass


def busy(env):
    return t.run("backup_lock.py", env=env)[0] == 3


def night_at(home, source):
    """The number of the night.py that holds the backup lock for this card right now, or None."""
    try:
        note = json.loads((home / "backup.running.json").read_text(encoding="utf-8"))
        if Path(note.get("source") or "").resolve() != Path(source).resolve() or not this_computer.still_running(note.get("pid")):
            return None
        return note.get("pid")
    except (OSError, ValueError):
        return None


def wait_for(what, seconds=60):
    end = time.time() + seconds
    while time.time() < end:
        got = what()
        if got:
            return got
        time.sleep(0.2)
    return what()


def alone_checks(work):
    print("Only one process dies: the job without its backup, the backup without its copy")
    ok, how = t.pictures.ready()
    if not ok:
        skip("everything that needs a whole backup", how)
        return
    base, home, env = world(work, "alone")
    dest, second = base / "drives" / "G PAPA", base / "drives" / "LaCie"

    # 1. a step of night.py holds the backup lock too: night.py killed alone never frees the lock under its copy
    if this_computer.WINDOWS:
        skip("a step keeps the lock when night.py alone is killed", "a PC's lock cannot be handed to a step: a named gap")
    else:
        for how_out in ("a pipe", "a file"):
            sleeper, note = base / "sleeper.py", base / f"sleeper-{how_out[2:]}.pid"
            sleeper.write_text("import os, sys, time\nopen(sys.argv[1], 'w').write(str(os.getpid()))\ntime.sleep(600)\n", encoding="utf-8")
            code = ("import sys; sys.path.insert(0, %r); import backup_lock, night; "
                    "ok = backup_lock.take('x', 'held by the test'); sys.stderr.write('HELD\\n' if ok else 'NOT\\n'); sys.stderr.flush(); "
                    "night.run(%r, %r)" % (str(t.SCRIPTS), str(sleeper), str(note)))
            out = subprocess.PIPE if how_out == "a pipe" else open(base / "night-out.txt", "wb")
            p = subprocess.Popen([sys.executable, "-c", code], stdout=out, stderr=subprocess.PIPE, env=t.child_env(env))
            said = p.stderr.readline().decode().strip()
            end = time.time() + 20
            while time.time() < end and not (note.exists() and note.read_text().strip()):
                time.sleep(0.1)
            child = int(note.read_text().strip()) if note.exists() and note.read_text().strip() else None
            p.kill()
            p.wait()
            time.sleep(0.5)
            held = busy(env)
            if child:
                os.kill(child, signal.SIGKILL)
            end = time.time() + 10
            while time.time() < end and busy(env):
                time.sleep(0.2)
            check(f"night.py killed alone while a step is at work (output to {how_out}): the lock is STILL held, by the step; it is free once the step ends",
                  said == "HELD" and child is not None and held is True and not busy(env), f"said={said} child={child} held={held}")
            if out is not subprocess.PIPE:
                out.close()

    # 2. the job is killed while night.py runs: night.py carries on, and the record must say so, then say done
    card = base / "CARD A"
    card_at(card, [(D4.replace(hour=9), 6)])
    code, got = start(dict(env, STUDIO_NIGHT_PAUSE_FOR_TESTS="4"), card, dest)
    npid = wait_for(lambda: night_at(home, card))
    r = status(env)
    pid = (r.get("private") or {}).get("pid")
    check("(the job is up and its backup holds the lock)", isinstance(pid, int) and isinstance(npid, int) and pid != npid, f"{pid} {npid}")
    kill_one(pid)
    time.sleep(0.6)
    r = status(env)
    check("the job alone was killed, the backup itself is still running: the record says running, not 'stopped, press Try again'",
          r.get("state") == "running" and busy(env), str(r))
    code, again = start(env, card, dest)
    check("... Try again meanwhile says a backup is already running, which now agrees with the record", again == {"ok": False, "why": BUSY}, str(again))
    end = time.time() + 180
    while time.time() < end and busy(env):
        time.sleep(0.5)
    r = status(env)
    check("the backup then finished by itself: the record says done, every file, one shoot (never 'problem, 0 of 6' for good)",
          r.get("state") == "done" and r.get("step") == "done" and r.get("done") == r.get("total") == 7 and r.get("shoots") == 1
          and r.get("finished") and r.get("records"), str(r))
    check("... saved so (a page reload reads the same), and the shoot is settled on the drive",
          json.loads((home / "backup-job.json").read_text(encoding="utf-8")).get("state") == "done"
          and len(photos_on(dest)) == 6 and not any(p.name.endswith(" card") for p in dest.iterdir()), str(sorted(p.name for p in dest.iterdir())))

    # 3. the job is killed while the second copy is being made: second_copy.py carries on
    card = base / "CARD B"
    card_at(card, [(D4.replace(month=7, hour=9), 6)], first_number=6001)
    code, got = start(dict(env, STUDIO_SECOND_COPY_PAUSE_FOR_TESTS="1"), card, dest, "--second", second)
    r = wait(env, 180, lambda r: r.get("step") == "second" or r.get("state") != "running")
    pid = (r.get("private") or {}).get("pid")
    check("(the job reached the second copy)", r.get("state") == "running" and r.get("step") == "second", str(r))
    time.sleep(1.5)
    kill_one(pid)
    time.sleep(0.6)
    r = status(env)
    check("the job alone was killed during the second copy: the photos are backed up and the second copy is still being made, so the record says running, step second",
          r.get("state") == "running" and r.get("step") == "second", str(r))
    r = wait(env, 120)
    check("... and when the second copy finished by itself: done, second copy made and checked",
          r.get("state") == "done" and r.get("second_ok") is True and r.get("done") == r.get("total") == 7, str(r))

    # 4. night.py alone is killed mid-copy: its copy carries on, and the job's rerun WAITS for it (never two copies at once)
    if this_computer.WINDOWS:
        skip("the rerun waits for a copy that outlived night.py", "a PC's lock cannot be handed to a step: a named gap")
        return
    card = base / "CARD C"
    card_at(card, [(D4.replace(month=8, hour=9), 8)], first_number=8001)
    before = t.card_snapshot(card)
    code, got = start(dict(env, STUDIO_BACKUP_PAUSE_FOR_TESTS="0.7"), card, dest)
    seen = lambda: [p for p in dest.rglob("*IMG_80*.JPG")]       # noqa: E731
    wait_for(lambda: len(seen()) >= 2)
    npid = night_at(home, card)
    check("(the copy is under way)", isinstance(npid, int) and 2 <= len(seen()) < 8, f"{npid} {len(seen())}")
    kill_one(npid)
    r = wait(env, 240)
    log = log_of(home)
    tail = log[log.rfind("night.py ended with"):]
    check("night.py alone was killed mid-copy: the job waited for the copy that was still at work before running the backup again",
          "one of its steps is still at work; waiting for it before running again" in tail, tail[:600])
    check("... and the backup finished: done, nothing 'would not copy', no problem on record",
          r.get("state") == "done" and "would not copy" not in tail
          and not json.loads((Path(r["records"]) / "manifest.json").read_text(encoding="utf-8")).get("problems"), str(r) + tail[-600:])
    check("... every photo of that card once, none half-written, the card as it was",
          len(seen()) == 8 and not list(dest.rglob("*.studio-partial")) and t.card_snapshot(card) == before, str(len(seen())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    only = {x for x in a.only.split(",") if x}
    for k in ("STUDIO_DRIVES_FOR_TESTS", "STUDIO_BACKUP_JOB"):
        os.environ.pop(k, None)
    work = Path(tempfile.mkdtemp(prefix="backup-job-"))
    os.environ["STUDIO_HOME"] = str(work / "never-used-home")     # nothing here may ever look at the real ~/.studio
    try:
        for name, fn in (("units", unit_checks), ("lock", lock_checks), ("job", job_checks), ("trouble", trouble_checks),
                         ("second", second_checks), ("folder", folder_checks), ("alone", alone_checks)):
            if only and name not in only:
                continue
            fn(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if SKIPPED:
        print(f"\nSkipped: {len(SKIPPED)}")
    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}")
    for f in FAILED:
        print("   " + f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
