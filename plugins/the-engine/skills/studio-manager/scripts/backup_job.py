#!/usr/bin/env python3
"""A backup started from a page (the home page's Back up a card popup, Nov 23), not from the chat.

    python3 backup_job.py start --source "<card or folder>" --dest "<the exact folder backups go in>"
                                [--second "<drive or folder>"] [--shoot-name "<name>"]
    python3 backup_job.py status            the job's record, one line of JSON
    python3 backup_job.py status --words    the same in a few plain lines (for the chat)

start begins ONE detached job (it outlives the page, the page server and the command that started it) and prints
one line of JSON: {"ok": true}, or {"ok": false, "why": "<plain words>"} (a backup is already running, the card
is gone...). The job copies nothing itself. It runs night.py --by-time, the very backup the chat runs, with
nobody looking: shoots split wherever the camera was quiet for four hours, placeholder names, six first-look
photos per shoot chosen by a script. --dest is used exactly as given (no guessing where on the drive). Then,
when a second drive was asked for, second_copy.py makes the second copy of the finished backup. A second drive
saved in the Studio File is NOT used (Nicole, Nov 23: the second drive is asked each time): only --second is. A folder is
backed up the same way as a card ("Back up a folder instead").

What the job adds around night.py:
  - one at a time: night.py's own computer-wide lock (backup_lock.py) plus the job's own, held for its whole life
  - the computer is kept awake for as long as it runs
  - the record, <STUDIO_HOME>/backup-job.json, written whole after every change: what a page shows comes from
    this file and nothing else, so a reload, a closed pane or a page server that starts over loses nothing
  - a stop that is not "done", "problems" or "stop" (a pause, a crash, a kill) is run again ONCE, under the same
    name and day, and carries on from the backup's own records
  - a watchdog: no progress for a few minutes means the card or the drive has stopped answering; the job stops
    night.py and says so in plain words
  - a job whose process has died is reported as "problem", never as "running" for ever (status() looks)

The record: {"state": "idle"|"running"|"done"|"problem", "step": "copying"|"sorting"|"second"|"done",
"done", "total", "card", "drive", "folders", "second", "shoots", "backup", "records", "line", "started",
"finished"}, plus "already" (the card was backed up before: nothing was copied), "set_aside" (what could not be
sorted into a shoot, said honestly: {"undated", "other", "kinds"}), "unsorted" (how many files, when nothing at
all could be sorted), "second_ok" and "second_line" (how the second copy went). On a finished record "done" and
"total" are the backup's own count, whatever became of the second copy. "records" and
everything under "private" are paths, for the server only: NEVER sent to a page.

No notification is sent (Nicole, Nov 23: "no"). The shoots are registered as night.py registers them (Your
backups, Uploaded shoots); they are never put in the editing queue.
"""
import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backup_lock  # noqa: E402
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)

HOME = backup_lock.HOME
JOB = backup_lock.JOB
START_LOCK = HOME / "backup-job.start.lock"   # held for the instant a start checks and writes, so two presses never both start
STARTING_SECONDS = 30       # a record written this recently with no process yet is a job on its way up, not a dead one
QUIET_COPY_SECONDS = 300    # copying: no line from the backup AND no change in the drive's free room for this long
QUIET_SORT_SECONDS = 1500   # after the copy (previews, sorting, the first look): no line for this long
QUIET_SECOND_SECONDS = 600  # the second copy: its own record not moving for this long
RERUNS = 1                  # a stop that is not done / problems / stop is run again this many times, same name


def _for_tests(name, default=None):
    """A number only a test sets (never a photographer's computer): STUDIO_BACKUP_JOB_<NAME>_FOR_TESTS.
    PAUSE: seconds the job waits, holding its lock, before it touches anything (so a test can press Start twice,
    eject, or take the card away while a job is plainly alive). QUIET: the watchdog's limit, in seconds, for every
    step. BUDGET: the first run of night.py is given this --budget (0 pauses it after one file: a stop to rerun)."""
    v = os.environ.get(f"STUDIO_BACKUP_JOB_{name}_FOR_TESTS")
    try:
        return float(v) if v not in (None, "") else default
    except ValueError:
        return default

# Every line here may be shown on a page, so none of them ever holds a path. All ours, all drafts for Dustin and Nicole.
OUR_WORDS = {
    "busy": backup_lock.BUSY,
    "no_source": "I can't see that memory card or folder any more. Is it still there?",
    "no_card": "I can't see that memory card any more. Is it still in?",
    "no_folder": "I can't see that folder any more.",
    "no_dest": "I can't see the folder your photos go in. Is the drive plugged in?",
    "no_second": "I can't see the drive for your second copy. Is it plugged in?",
    "cant_start": "I couldn't start the backup. Nothing was copied. Try again in a moment.",
    "died": "The backup stopped before it finished. Nothing is lost: press Try again and it picks up where it left off.",
    "quiet": ("Your memory card or your drive has stopped answering, so I stopped the backup. Nothing on your card was "
              "changed, and what was already copied is kept. Check the card and the drive, then press Try again."),
    "problem": "The backup stopped with a problem. Nothing on your card was changed. See the report for what it found.",
    "stopped": "The backup stopped before it started copying. Nothing was changed.",
    "already": "This card was already backed up, so there was nothing to copy.",
    "second_missed": "Your photos are backed up and checked. The second copy isn't made yet: {why}",
    "second_plain": "Your photos are backed up and checked. The second copy isn't finished: use Make a second copy on the report to carry on.",
    "aside_undated": "{n} with no date could not be sorted into a shoot. Copied and checked, and kept with the backup's records.",
    # every file that is not a photo or a video: the camera's own small files on a card, but in a folder also a
    # Photoshop file, a PDF, a text file of theirs. Never called "camera housekeeping": the kinds are named instead.
    "aside_other": "{n} not a photo or a video clip ({kinds}) {was} copied and checked, and set aside with the backup's records, not in a shoot's folder. Nothing was deleted. Ask the Assistant where {it}.",
    "unsorted": ("Nothing here has a date the Assistant can read, so it could not be sorted into shoots. All {n} are copied "
                 "and checked, and kept together in one folder: {folder}."),
    "still_going": ("The backup was interrupted, and one of its steps is still at work by itself. Nothing is lost. "
                    "Give it a few minutes, then press Try again."),
}


def now():
    return datetime.now().isoformat(timespec="seconds")


def read():
    try:
        got = json.loads(JOB.read_text(encoding="utf-8"))
        return got if isinstance(got, dict) else None
    except (OSError, ValueError):
        return None


def write(rec):
    backup_lock.write_whole(JOB, rec)


def no_path(line, private=None):
    """A line that is safe to show on a page: the places this job knows are said by name, and a line that
    still holds something that looks like a path is not shown at all (None)."""
    line = " ".join(str(line or "").split())
    names = []
    for k, word in (("source", "your card"), ("dest", "your drive"), ("second", "your second drive"), ("session", "the backup")):
        v = (private or {}).get(k)
        if v:
            names.append((str(v), word))
    names.append((str(HOME), "the Assistant's own folder"))
    names.append((str(Path.home()), "your home folder"))
    for v, word in sorted(names, key=lambda x: -len(x[0])):
        line = line.replace(v, word)
    if re.search(r"(^|[\s\"'(:])(/[^\s/]+/|~/|[A-Za-z]:\\|\\\\)", line) or "_studio" in line or ".py" in line:
        return None
    return line[:400] or None


def place_words(dest):
    """(drive, folders): how a page says where the photos go, by name. The drive is one of the drives plugged in
    (studio_file.drives(), which a test can stand in for), else the drive's own name, else this computer."""
    dest = Path(dest)
    try:
        real = dest.resolve()
    except OSError:
        real = dest
    try:
        import studio_file
        for d in studio_file.drives():
            root = Path(d["path"])
            try:
                rel = real.relative_to(root.resolve())
            except (ValueError, OSError):
                continue
            return d["name"], [p for p in rel.parts if p not in (".", "")]
    except Exception:  # noqa: BLE001
        pass
    name = this_computer.drive_words(dest)
    if name:
        parts = dest.parts
        tail = list(parts[3:]) if len(parts) > 2 and parts[1] == "Volumes" else [p for p in parts[1:] if p not in ("\\", "/")]
        return name, tail
    try:
        rel = real.relative_to(Path.home().resolve())
        return f"This {this_computer.COMPUTER}", list(rel.parts)
    except (ValueError, OSError):
        return f"This {this_computer.COMPUTER}", [dest.name] if dest.name else []


def card_words(source):
    source = Path(source)
    name = source.name or this_computer.drive_words(source) or str(source).rstrip("\\/")
    return name


def is_card(source):
    """The top of a memory card (backup.source_kind: the same answer the backup's own records will hold)."""
    try:
        from backup import source_kind
        return source_kind(source) == "card"
    except Exception:  # noqa: BLE001
        try:
            return (Path(source) / "DCIM").is_dir()
        except OSError:
            return False


def ensure_naming():
    """A very first backup started from a page has no Studio File yet, so no folder naming is on file, and the
    shoots would be filed with no date at all. The naming every new backup gets (studio_file.OFFERED[0]:
    "Aurora_11-22-26", photos named for the shoot) is written then, exactly as the chat's first backup writes it.
    A naming already on file is never touched. The drive is NOT saved here: the page that started the backup
    does that, when Start is pressed."""
    import studio_file
    sf = studio_file.load()
    n = sf.setdefault("naming", {})
    if n.get("folder_pattern"):
        return False
    n.update(studio_file.OFFERED[0])
    n.pop("example", None)
    n.setdefault("file_names", "shoot")
    studio_file.save(sf)
    return True


def facts_of(p):
    """What a backup's own records say, from the job's private notes: (records folder, its name, how many shoots,
    what was set aside, how many files could not be sorted at all). All None when the records can't be found."""
    from where import locate
    try:
        _, studio = locate(p["session"])
    except (SystemExit, KeyError, TypeError):
        # a card backed up before, on another day or under another name: the card ledger knows where
        try:
            import cards
            _, held = cards.check(p["source"])
            _, studio = locate(held["studio"])
        except (Exception, SystemExit):  # noqa: BLE001
            return None, None, None, None, None

    def load(name):
        try:
            return json.loads((studio / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    name = (load("manifest.json") or {}).get("session")
    try:
        shoots = len(load("shoots.json")["shoots"])
    except (KeyError, TypeError):
        shoots = None
    aside = unsorted = None
    log = load("sort-log.json")
    try:
        if log is not None:
            undated = set(log.get("set_aside_undated") or [])
            # what is theirs or the camera's, never the computer's own hidden notes (.DS_Store, Thumbs.db)
            other = [e["from"] for e in (log.get("set_aside") or [])
                     if e["from"] not in undated and not this_computer.housekeeping_file(Path(e["from"]).name)]
            if undated or other:
                aside = {"undated": len(undated), "other": len(other),
                         "kinds": sorted({Path(f).suffix.lower().lstrip(".") or "no ending" for f in other})}
        elif not shoots:
            # nothing was sorted at all (a folder of photos with no date inside them): every file is still
            # loose in the backup's own folder, and no record said so
            unsorted = len((load("manifest.json") or {}).get("files") or {}) or None
    except (KeyError, TypeError, AttributeError):
        pass
    return studio, name or Path(str(p.get("session") or "")).name, shoots, aside, unsorted


def said_aside(rec, aside, unsorted, folder):
    """The lines that say honestly what was not sorted into a shoot; also noted on the record."""
    lines = []
    if unsorted:
        rec["unsorted"] = unsorted
        lines.append(OUR_WORDS["unsorted"].format(n=f"{unsorted:,} file{'s' if unsorted != 1 else ''}", folder=folder))
    if aside:
        rec["set_aside"] = aside
        n = aside["undated"]
        if n:
            lines.append(OUR_WORDS["aside_undated"].format(n=f"{n:,} photo{'s' if n != 1 else ''} or video clip{'s' if n != 1 else ''}"))
        n = aside["other"]
        if n:
            lines.append(OUR_WORDS["aside_other"].format(n=f"{n:,} file{'s that are' if n != 1 else ' that is'}", kinds=", ".join(aside.get("kinds") or []),
                                                         was="were" if n != 1 else "was", it="they are" if n != 1 else "it is"))
    return lines


def files_in(studio, fallback=0):
    try:
        return len(json.loads((Path(studio) / "manifest.json").read_text(encoding="utf-8")).get("files") or {}) or fallback
    except (OSError, ValueError, AttributeError):
        return fallback


def left_alone(rec):
    """A record that says "running" whose job has died. The job starts night.py (and the second copy) so that they
    outlive it, so the job dying is not the backup dying (Nov 23 review: the record said "stopped, press Try
    again" while the backup carried on, Try again said "already running", and when the backup finished by itself
    the record said problem for good). So: (the record as it truly stands, whether to save it).
      - the backup, or its second copy, is still at work: still "running", nothing saved
      - it finished by itself (settled, every file checked): "done", with the same lines the job would have written
      - otherwise: a problem, Try again picks it up"""
    p = rec.get("private") or {}
    info = backup_lock.running()
    if info is not None and (not info.get("source") or not p.get("source") or backup_lock._same(info.get("source"), p.get("source"))):
        return rec, False
    studio = bname = None
    if p.get("session"):
        studio, bname, shoots, aside, unsorted = facts_of(p)
    whole = False
    if studio is not None and (studio / "settled.json").exists():
        try:    # read only: a look at the record must never change a backup's own records
            m = json.loads((studio / "manifest.json").read_text(encoding="utf-8"))
            files = m.get("files") or {}
            whole = (bool(m.get("finished")) and not m.get("problems") and not m.get("sample") and bool(files)
                     and all((v.get("dest") or {}).get("ok") for v in files.values()))
        except (OSError, ValueError, AttributeError):
            whole = False
    if not whole:
        rec.update({"state": "problem", "line": OUR_WORDS["died"], "finished": now()})
        return rec, True
    second_ok = None
    if p.get("second"):
        try:
            import second_copy
            at = second_copy.running()
            if at and backup_lock._same(at.get("studio"), studio):
                rec.update(step="second", records=str(studio), backup=bname)
                return rec, False
            second_ok = second_copy.status(studio).get("state") == "done"
        except Exception:  # noqa: BLE001
            second_ok = False
    lines = said_aside(rec, aside, unsorted, bname)
    if second_ok is not None:
        rec["second_ok"] = second_ok
        if not second_ok:
            rec["second_line"] = OUR_WORDS["second_plain"]
            lines.append(rec["second_line"])
    n = files_in(studio, rec.get("total") or 0)
    rec.update(state="done", step="done", done=n, total=n, shoots=shoots, records=str(studio), backup=bname,
               line=" ".join(lines), finished=now())
    return rec, True


def blank(**kw):
    rec = {"state": "idle", "step": "copying", "done": 0, "total": 0, "card": None, "drive": None, "folders": [],
           "second": None, "shoots": None, "backup": None, "records": None, "line": "", "started": None, "finished": None}
    rec.update(kw)
    return rec


def alive():
    """Is a page-started job's process alive right now? (Its lock is held; the computer lets go when it dies.)"""
    return backup_lock.job_running() is not None


def status():
    """The job's record, true right now. A record that says "running" whose process has died is looked into here
    (left_alone): still running when the backup itself is, done when it finished by itself, otherwise a problem
    (and saved so), unless it was written a moment ago and its process is still on its way up."""
    rec = read()
    if rec is None:
        return blank()
    if rec.get("state") == "running" and not alive():
        try:
            age = (datetime.now() - datetime.fromisoformat(rec.get("started") or "")).total_seconds()
        except ValueError:
            age = 1e9
        if (rec.get("private") or {}).get("pid") or age > STARTING_SECONDS:
            again = read() or rec           # it may have finished between the two looks
            if again.get("state") == "running" and not alive():
                try:
                    again, save = left_alone(again)
                except Exception:  # noqa: BLE001  (a record that can't be worked out is a problem, never "running" for ever)
                    again.update({"state": "problem", "line": OUR_WORDS["died"], "finished": now()})
                    save = True
                if save:
                    try:
                        write(again)
                    except OSError:
                        pass
            rec = again
    return rec


def for_page(rec=None):
    """The record as a page may have it: no paths (no "records", nothing under "private")."""
    rec = dict(rec if rec is not None else status())
    rec.pop("records", None)
    rec.pop("private", None)
    return rec


def words(rec=None):
    """How a page-started backup stands, in a few plain lines for the chat."""
    rec = rec if rec is not None else status()
    st = rec.get("state")
    if st == "idle":
        return ["No backup has been started from the home page."]
    where = rec.get("drive") or "your drive"
    if rec.get("folders"):
        where = f"{' / '.join(rec['folders'])} on {where}"
    out = []
    if st == "running":
        step = rec.get("step")
        if step == "copying":
            out.append(f"A backup started from the home page is running: copying and checking ({rec.get('done', 0):,} of {rec.get('total', 0):,}), from {rec.get('card')} to {where}.")
        elif step == "sorting":
            out.append(f"A backup started from the home page is running: everything is copied and checked ({rec.get('total', 0):,} files), and it is sorting into shoots.")
        else:
            out.append(f"A backup started from the home page is running: the photos are backed up and checked, and the second copy is being made on {rec.get('second')}.")
    elif st == "done":
        if rec.get("already"):
            out.append(OUR_WORDS["already"])
        else:
            n = rec.get("shoots")
            out.append(f"The backup started from the home page is done: {rec.get('total', 0):,} files from {rec.get('card')} copied to {where} and checked"
                       + (f", in {n} shoot{'s' if n != 1 else ''}" if n else "") + ".")
        if rec.get("second"):
            out.append(f"Second copy on {rec['second']}: " + ("made and checked." if rec.get("second_ok") else "not finished."))
        if rec.get("line"):
            out.append(rec["line"])
    else:
        out.append("The backup started from the home page stopped: " + (rec.get("line") or OUR_WORDS["died"]))
    if rec.get("records"):
        out.append(f"Its records (for the report): {rec['records']}")
    return out


def start(source, dest, second=None, shoot_name=None):
    """Start the one detached job. {"ok": True} or {"ok": False, "why": plain words}. Nothing is copied here;
    nothing on the card is read beyond whether it is there."""
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        gate, got = backup_lock._try(START_LOCK, tries=20)
    except OSError:
        return {"ok": False, "why": OUR_WORDS["cant_start"]}
    if got is False:
        return {"ok": False, "why": OUR_WORDS["busy"]}
    try:
        before = status()
        if alive() or backup_lock.running() is not None or before.get("state") == "running":
            return {"ok": False, "why": OUR_WORDS["busy"]}
        source, dest = Path(str(source)).expanduser(), Path(str(dest)).expanduser()
        if this_computer.WINDOWS:
            source, dest = this_computer.drive_root(source), this_computer.drive_root(dest)
        second = Path(str(second)).expanduser() if second else None
        try:
            if not source.is_dir():
                return {"ok": False, "why": OUR_WORDS["no_source"]}
            if not dest.is_dir():
                return {"ok": False, "why": OUR_WORDS["no_dest"]}
            if second is not None and not second.is_dir():
                return {"ok": False, "why": OUR_WORDS["no_second"]}
        except OSError:
            return {"ok": False, "why": OUR_WORDS["no_source"]}
        drive, folders = place_words(dest)
        private = {"pid": None, "source": str(source), "dest": str(dest), "second": str(second) if second else None,
                   "shoot_name": " ".join(str(shoot_name or "").split()) or None, "name": None, "date": None, "session": None,
                   "is_card": is_card(source)}
        # a Try again after a stop: the same card to the same place carries on under the same name and day
        old = before.get("private") or {}
        if before.get("state") == "problem" and old.get("name") and old.get("date") \
                and backup_lock._same(old.get("source"), source) and backup_lock._same(old.get("dest"), dest):
            private["resume"] = {"name": old["name"], "date": old["date"]}
        rec = blank(state="running", step="copying", card=card_words(source), drive=drive, folders=folders,
                    second=(place_words(second)[0] if second else None), started=now(), private=private)
        write(rec)
        try:
            logs = HOME / "logs"
            logs.mkdir(parents=True, exist_ok=True)
            with open(logs / "backup-job.log", "ab") as log:
                this_computer.popen_detached([sys.executable, str(Path(__file__).resolve()), "run"],
                                             stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True)
        except OSError:
            rec.update({"state": "problem", "line": OUR_WORDS["cant_start"], "finished": now()})
            write(rec)
            return {"ok": False, "why": OUR_WORDS["cant_start"]}
        return {"ok": True}
    finally:
        try:
            this_computer.unlock(gate)
            gate.close()
        except OSError:
            pass


# ---------------------------------------------------------------- the job itself (the detached process)

class Job:
    def __init__(self, rec):
        self.rec = rec
        self.p = rec["private"]
        self.log_lines = []

    def save(self, **kw):
        self.rec.update(kw)
        write(self.rec)

    def problem(self, line):
        self.save(state="problem", line=line or OUR_WORDS["died"], finished=now())
        return 1

    def log(self, text):
        try:
            print(text, flush=True)      # the job's own output is its log file (~/.studio/logs/backup-job.log)
        except OSError:
            pass

    def partial(self):
        """The file being copied right now, as (how many, their sizes added up): backup.py writes each file under
        <name>.studio-partial and only then gives it its name, so while one big file copies, this number moves
        though no line is printed. (The drive's free room would be no proof: other programs change it.)"""
        n = size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.p["session"]):
                dirnames[:] = [d for d in dirnames if d != "_studio"]
                for fn in filenames:
                    if fn.endswith(".studio-partial"):
                        try:
                            size += os.stat(os.path.join(dirpath, fn)).st_size
                            n += 1
                        except OSError:
                            pass
        except OSError:
            pass
        return n, size

    def night(self, budget=None):
        """Run night.py once, following its lines. (exit code, why-lines after a STOP, the last lines).
        Stopped by the watchdog: code "quiet"."""
        cmd = [sys.executable, "-u", str(HERE / "night.py"), "--source", self.p["source"], "--dest", self.p["dest"],
               "--name", self.p["name"], "--date", self.p["date"], "--by-time", "--no-second"]
        if self.p.get("shoot_name"):
            cmd += ["--shoot-name", self.p["shoot_name"]]
        if budget is not None:
            cmd += ["--budget", str(budget)]
        env = dict(os.environ, STUDIO_BACKUP_JOB=str(os.getpid()), PYTHONUNBUFFERED="1")
        try:
            proc = this_computer.popen_detached(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        except OSError as e:
            self.log(f"could not start night.py: {e}")
            return None, [], []
        lines = queue.Queue()

        def pump():
            try:
                for raw in iter(proc.stdout.readline, b""):
                    lines.put(raw.decode("utf-8", "replace").rstrip("\r\n"))
            except (OSError, ValueError):
                pass
            lines.put(None)
        threading.Thread(target=pump, daemon=True).start()
        why, tail, stopping, ended = [], [], False, False
        last, part, looked = time.monotonic(), None, 0.0
        quiet = _for_tests("QUIET")
        while not ended:
            try:
                ln = lines.get(timeout=2)
            except queue.Empty:
                ln = ""
            changed = False
            while ln is not None and ln != "":
                last = time.monotonic()
                self.log(ln)
                tail = (tail + [ln])[-30:]
                m = re.match(r"\s+dest: (\d+)/(\d+) files", ln)
                if m:
                    if self.rec["step"] != "copying" or (int(m.group(1)), int(m.group(2))) != (self.rec["done"], self.rec["total"]):
                        self.rec.update(step="copying", done=int(m.group(1)), total=int(m.group(2)))
                        changed = True
                elif re.match(r"\s*1\. Already copied and verified", ln) or re.match(r"\s*([2-7])[ab]?\. ", ln):
                    if self.rec["step"] != "sorting":
                        self.rec.update(step="sorting", done=self.rec["total"] or self.rec["done"])
                        changed = True
                elif ln.startswith("This card is already safe") or ln.startswith("This backup is finished and settled"):
                    self.rec["already"] = True
                    changed = True
                elif ln.startswith("This card is already copied and verified"):
                    self.rec.update(step="sorting", done=self.rec["total"] or self.rec["done"])
                    changed = True
                if ln.startswith("STOP"):
                    stopping = True
                    rest = ln.split(":", 1)[1].strip() if ":" in ln and not ln.rstrip().endswith(":") else ""
                    if rest:
                        why.append(rest)
                elif stopping and ln.strip().startswith("- "):
                    why.append(ln.strip()[2:])
                try:
                    ln = lines.get_nowait()
                except queue.Empty:
                    ln = ""
            if ln is None:
                ended = True
            if changed:
                self.save()
            # the watchdog: while copying, one big file gives no line for minutes, so the file being written
            # growing counts as progress too (looked at only once the lines have gone quiet for a little while)
            if not ended:
                limit = quiet or (QUIET_COPY_SECONDS if self.rec["step"] == "copying" else QUIET_SORT_SECONDS)
                idle = time.monotonic() - last
                if self.rec["step"] == "copying" and idle > min(10, limit / 2) and time.monotonic() - looked > min(10, limit / 4):
                    looked = time.monotonic()
                    now_part = self.partial()
                    if part is not None and now_part != part:
                        last = time.monotonic()
                    part = now_part
                if time.monotonic() - last > limit:
                    self.log(f"WATCHDOG: no progress for {limit} s; stopping the backup")
                    this_computer.stop_tree(proc.pid)
                    try:
                        proc.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        pass
                    return "quiet", why, tail
        try:
            code = proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            this_computer.stop_tree(proc.pid)
            code = None
        return code, why, tail

    def finished_facts(self):
        """What a finished backup's own records say (facts_of)."""
        return facts_of(self.p)

    def wait_for_a_step(self):
        """night.py has ended, but one of its steps (the copy, most likely) is still at work and holds the backup
        lock: wait for it, so the rerun never starts a second copy beside it. False when it has not let go after
        a long while with nothing moving."""
        last, part = time.monotonic(), None
        limit = _for_tests("QUIET") or QUIET_SORT_SECONDS
        while backup_lock.running() is not None:
            now_part = self.partial()
            if now_part != part:
                part, last = now_part, time.monotonic()
            if time.monotonic() - last > limit:
                return False
            time.sleep(1)
        return True

    def second_copy(self, studio):
        """The second copy of the finished backup (second_copy.py, exactly as night.py's step 1b runs it), followed
        through its own record. (ok, plain words when it did not finish)."""
        cmd = [sys.executable, "-u", str(HERE / "second_copy.py"), str(studio), "--to", self.p["second"], "--json"]
        try:
            proc = this_computer.popen_detached(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except OSError:
            return False, None
        out = []

        def pump():
            try:
                for raw in iter(proc.stdout.readline, b""):
                    out.append(raw.decode("utf-8", "replace").rstrip("\r\n"))
            except (OSError, ValueError):
                pass
        threading.Thread(target=pump, daemon=True).start()
        last, seen = time.monotonic(), None
        while proc.poll() is None:
            time.sleep(2)
            try:
                rec = json.loads((Path(studio) / "second-copy.json").read_text(encoding="utf-8"))
                now_at = (rec.get("done"), rec.get("total"), rec.get("state"))
            except (OSError, ValueError):
                now_at = None
            if now_at != seen or len(out) != getattr(self, "_n_out", 0):
                seen, last, self._n_out = now_at, time.monotonic(), len(out)
                if now_at and isinstance(now_at[0], int) and isinstance(now_at[1], int):
                    self.save(done=now_at[0], total=now_at[1])
            if time.monotonic() - last > (_for_tests("QUIET") or QUIET_SECOND_SECONDS):
                self.log("WATCHDOG: the second copy has not moved; stopping it")
                this_computer.stop_tree(proc.pid)
                return False, None
        for ln in out:
            self.log(ln)
        said = None
        try:
            said = json.loads(out[-1]) if out else None
        except ValueError:
            said = None
        if proc.returncode == 0:
            return True, None
        return False, no_path((said or {}).get("words"), self.p) if isinstance(said, dict) else None

    def run(self):
        import cards
        src = self.p["source"]
        if not Path(src).is_dir():
            return self.problem(OUR_WORDS["no_card"] if self.p.get("is_card") else OUR_WORDS["no_folder"])
        if not cards.answers(src):
            return self.problem(no_path(cards.QUIET_CARD.replace("say go", "press Try again")) or OUR_WORDS["quiet"])
        # the name and the day, chosen ONCE and used for every run of this job, so a rerun carries on in the
        # same folder (night.py's own rule for a card with no name: the weekday, and the next free one if taken)
        import night
        today = datetime.now()
        date, base = today.strftime("%Y-%m-%d"), today.strftime("%A").lower() + (" card" if self.p.get("is_card") else " folder")
        session = name = None
        res = self.p.get("resume")
        try:
            if res:
                s, st, cand, clash = night.folder_for(src, self.p["dest"], res["date"], res["name"], False)
                if not clash and st is None and (s / "_studio" / "manifest.json").exists():
                    session, name, date = s, cand, res["date"]
            if session is None:
                session, _, name, clash = night.folder_for(src, self.p["dest"], date, base, True)
                if clash:
                    return self.problem(no_path(clash, self.p) or OUR_WORDS["stopped"])
        except (OSError, SystemExit) as e:
            self.log(f"could not work out the backup's folder: {e}")
            return self.problem(OUR_WORDS["no_card"] if not Path(src).is_dir() else OUR_WORDS["cant_start"])
        self.p.update(name=name, date=date, session=str(session))
        try:
            ensure_naming()
        except Exception as e:  # noqa: BLE001  (the backup still runs; its folders then carry no date)
            self.log(f"could not write the default naming: {e}")
        try:
            from backup import inventory
            total = len(inventory(Path(src))[0])
        except OSError:
            total = 0
        self.save(total=total, backup=session.name)

        code, why, tail = None, [], []
        for attempt in range(RERUNS + 1):
            code, why, tail = self.night(budget=_for_tests("BUDGET") if attempt == 0 else None)
            if code in (0, 1, 2, "quiet"):
                break
            self.log(f"night.py ended with {code}; " + ("running it again, same name" if attempt < RERUNS else "not running it again"))
            if attempt < RERUNS and backup_lock.running() is not None:
                self.log("one of its steps is still at work; waiting for it before running again")
                if not self.wait_for_a_step():
                    code = "held"
                    break
        studio, bname, shoots, aside, unsorted = self.finished_facts()
        if studio is not None:
            self.rec.update(records=str(studio), backup=bname)
        if code == "quiet":
            return self.problem(OUR_WORDS["quiet"])
        if code == "held":
            return self.problem(OUR_WORDS["still_going"])
        if code == 2:
            said = [w for w in (no_path(x, self.p) for x in why) if w]
            return self.problem(" ".join(said)[:600] if said else OUR_WORDS["stopped"])
        if code == 1:
            last = next((w for w in (no_path(x, self.p) for x in reversed(tail) if "Close it and say go" in x) if w), None)
            return self.problem(last.replace("say go", "press Try again") if last else OUR_WORDS["problem"])
        if code != 0:
            return self.problem(OUR_WORDS["died"])
        if studio is None:
            return self.problem(OUR_WORDS["died"])
        lines = []
        if self.rec.get("already"):
            lines.append(OUR_WORDS["already"])
        lines += said_aside(self.rec, aside, unsorted, bname)
        self.save(step="sorting", shoots=shoots, done=self.rec["total"] or self.rec["done"], line=" ".join(lines))
        if self.p.get("second"):
            self.save(step="second", done=0)
            ok, said = self.second_copy(studio)
            self.rec["second_ok"] = bool(ok)
            if not ok:
                self.rec["second_line"] = OUR_WORDS["second_missed"].format(why=said) if said else OUR_WORDS["second_plain"]
                lines.append(self.rec["second_line"])
        # the numbers on a finished record are the BACKUP's: every file copied and checked. How far a second copy
        # got is said in words (second_line), never as "0 of 10" on a card that says Done.
        n = files_in(studio, self.rec["total"] or self.rec["done"])
        self.save(state="done", step="done", done=n, total=n, line=" ".join(lines), finished=now())
        return 0


def run_job():
    """The detached process. Holds the job's lock for its whole life."""
    this_computer.utf8_output()
    f, got = backup_lock._try(backup_lock.JOB_LOCK)
    if got is False:
        return 0                    # another job is already at work: this one was never needed
    rec = read()
    if not rec or rec.get("state") != "running" or not isinstance(rec.get("private"), dict):
        return 0
    rec["private"]["pid"] = os.getpid()
    write(rec)
    this_computer.awake_while()     # the computer stays awake for as long as this job runs
    job = Job(rec)
    try:
        time.sleep(_for_tests("PAUSE") or 0)
        return job.run()
    except BaseException as e:  # noqa: BLE001  (whatever happens, the record never stays "running")
        try:
            job.log(f"the job broke: {e.__class__.__name__}: {e}")
            job.problem(OUR_WORDS["died"])
        except Exception:  # noqa: BLE001
            pass
        return 1


def main():
    ap = argparse.ArgumentParser(description="A backup started from a page: one detached job that runs night.py --by-time.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--source", required=True, help="the memory card, or a folder to back up instead")
    s.add_argument("--dest", required=True, help="the exact folder backups go in (used as given)")
    s.add_argument("--second", default=None, help="a drive or folder for a second copy, made after the backup")
    s.add_argument("--shoot-name", default=None, help="the shoot's name; used only when the card holds exactly one shoot")
    st = sub.add_parser("status")
    st.add_argument("--words", action="store_true", help="a few plain lines instead of JSON")
    st.add_argument("--page", action="store_true", help="the record as a page may have it: no paths")
    sub.add_parser("run")           # the detached job itself; started by `start`, never by hand
    a = ap.parse_args()
    this_computer.utf8_output()
    if a.cmd == "start":
        got = start(a.source, a.dest, a.second, a.shoot_name)
        print(json.dumps(got, ensure_ascii=False), flush=True)
        return 0 if got.get("ok") else 2
    if a.cmd == "status":
        rec = status()
        if a.words:
            print("\n".join(words(rec)), flush=True)
        else:
            print(json.dumps(for_page(rec) if a.page else rec, ensure_ascii=False), flush=True)
        return 0
    return run_job()


if __name__ == "__main__":
    sys.exit(main())
