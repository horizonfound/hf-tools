#!/usr/bin/env python3
"""ONE backup at a time on this computer (Nov 23), whoever starts it: the chat (night.py run by the Assistant)
or a page (backup_job.py, started from the home page). night.py takes this lock before it copies a byte and
holds it for as long as it runs; a second start says "A backup is already running." and changes nothing.

Why: night.py and backup.py took no lock. Two runs on one card would write the same .studio-partial files and
save the same manifest over each other, and two cards started in the same minute could race for the next free
folder name of the day.

The lock is the computer's own file lock (this_computer.try_lock, as second_copy.py's): the computer lets go of
it by itself when its holder dies, so a backup that was killed never leaves the next one locked out. A small
note beside it says who holds it (never shown on a page as it is: it holds paths).

    python3 backup_lock.py            says whether a backup is running (one line), exit 0 no, 3 yes

Nothing here touches a card or a drive.
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
LOCK = HOME / "backup.lock"                  # held by night.py for as long as it runs
RUNNING = HOME / "backup.running.json"       # who holds it: {pid, source, name, started}
JOB_LOCK = HOME / "backup-job.lock"          # held by a page-started job (backup_job.py) for its whole life
JOB = HOME / "backup-job.json"               # that job's record (backup_job.py writes it)

BUSY = "A backup is already running."        # the one line a second start gets, from the chat or a page
BUSY_CARD = "A backup is still running from this card. It won't be long."   # ours, a draft: eject_card.py says it

_held = []                                   # the open lock files of this process (kept so they are not let go of)


def _read(path):
    try:
        got = json.loads(Path(path).read_text(encoding="utf-8"))
        return got if isinstance(got, dict) else None
    except (OSError, ValueError):
        return None


def write_whole(path, obj):
    """A record written whole or not at all: a scratch name of our own, then put in place."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
        this_computer.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()        # our own scratch copy, never the real file
        except OSError:
            pass
        raise


def _try(path, tries=10):
    """Take the lock at `path` for this process. (file, True) held; (None, False) another program holds it;
    (file, None) this computer or drive has no such locks. A look by someone else (held()) takes the lock for an
    instant, so a refusal is asked again for a second before it is believed (as second_copy.py does)."""
    HOME.mkdir(parents=True, exist_ok=True)
    f = open(path, "a+", encoding="utf-8")
    got = this_computer.try_lock(f)
    for _ in range(tries):
        if got is not False:
            break
        time.sleep(0.1)
        got = this_computer.try_lock(f)
    if got is False:
        f.close()
        return None, False
    return f, got


def held(path, note=None):
    """Is the lock at `path` held by a living program right now? Asked by trying it for an instant. Where this
    computer has no such lock, the holder's own number in the note beside it is asked instead."""
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        with open(path, "a+", encoding="utf-8") as f:
            got = this_computer.try_lock(f, shared=True)
            if got:
                this_computer.unlock(f)
                return False
            if got is None:
                info = _read(note) if note else None
                return bool(info) and bool(this_computer.still_running(info.get("pid")))
            return True
    except OSError:
        return False


def take(source=None, name=None):
    """night.py's own call, before anything is written: True when this process now holds the one backup lock
    (it keeps it until it ends, however it ends); False when another backup is running. With no locks on this
    computer, the note's own process number decides."""
    f, got = _try(LOCK)
    if got is False:
        return False
    if got is None:
        info = _read(RUNNING)
        if info and info.get("pid") != os.getpid() and this_computer.still_running(info.get("pid")):
            f.close()
            return False
    _held.append(f)
    try:
        write_whole(RUNNING, {"pid": os.getpid(), "source": str(source) if source else None, "name": name,
                              "started": datetime.now().isoformat(timespec="seconds")})
    except OSError:
        pass                    # the lock itself is what counts; the note only says whose it is
    return True


def for_a_step():
    """What night.py adds when it starts one of its steps (the copy, the sort, the settle...), so the step holds
    the one backup lock too: {"pass_fds": (...)} for subprocess. A Mac's lock belongs to the open lock file, and a
    step that is handed that open file keeps the lock for as long as it lives. Why (Nov 23 review): night.py
    alone held the lock, so when only night.py was killed its copy carried on with the lock free, and the next
    backup started a second copy into the same folder at the same moment, the very case the lock is for.
    A PC's lock cannot be handed on (and subprocess has no pass_fds there): {} there, a gap that is named."""
    if this_computer.WINDOWS:
        return {}
    fds = []
    for f in _held:
        try:
            fds.append(f.fileno())
        except (OSError, ValueError):
            pass
    return {"pass_fds": tuple(fds)} if fds else {}


def let_go():
    """Give the lock back before the process ends (the tests' own use; a process that ends lets go by itself)."""
    while _held:
        f = _held.pop()
        try:
            this_computer.unlock(f)
            f.close()
        except OSError:
            pass


def running():
    """The backup running on this computer right now ({pid, source, name, started}), or None."""
    if not held(LOCK, RUNNING):
        return None
    return _read(RUNNING) or {}


def job_running():
    """The page-started job that is alive right now (its record), or None."""
    if not held(JOB_LOCK, JOB):
        return None
    return _read(JOB) or {}


def _same(a, b):
    if not a or not b:
        return False
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return str(a) == str(b)


def reading_card(card):
    """True while a backup is running that was started on this very card (eject_card.py asks before it lets go):
    night.py itself, or a page-started job between two of its steps. A backup whose note cannot be read just now
    counts as reading it: wait."""
    info = running()
    if info is not None and (not info.get("source") or _same(info.get("source"), card)):
        return True
    job = job_running()
    src = ((job or {}).get("private") or {}).get("source")
    if job is not None and (not src or _same(src, card)):
        return True
    return False


if __name__ == "__main__":
    this_computer.utf8_output()
    busy = running() is not None or job_running() is not None
    print(BUSY if busy else "No backup is running.", flush=True)
    sys.exit(3 if busy else 0)
