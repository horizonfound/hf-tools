#!/usr/bin/env python3
"""The memory guard: run a command, and stop it and everything it started if together they take too much memory.

    python3 tests/guard.py 800 /usr/bin/python3 tests/video_check.py --work /private/tmp/somewhere

Why: this Mac once ran out of memory during a video test (a 4K clip, Nov 6). Every test that makes or reads a
video, or drives a hidden Chrome, is run under this, ONE at a time. The first word is the limit in MB; the
rest is the command, exactly as it would be typed.

What it does: starts the command, and every half second adds up the memory (what `ps` calls RSS) of the command
and of every program that came from it. Past the limit it stops them all at once, says so in one plain line, and
exits 9. Otherwise the command's own output passes straight through and the guard exits with the command's own
exit code (128 + the signal's number when a signal ended it), after one line on stderr saying the most memory it saw.

Which programs count as "came from it":
  - the command, its children, their children, and so on (by each program's parent);
  - any program in a process group that a living program of the tree is in (a page server started "detached"
    has a group of its own). A group is forgotten the moment nothing of the tree is left in it, so a stranger
    later handed the same group number is never counted;
  - any program seen once among them, for as long as it lives (so one whose parent has gone is still watched);
  - any program with no parent left that carries this run's mark. The guard gives the command one extra line
    of environment, GUARD_TREE_<the guard's number>=<a random word>, which everything it starts inherits. So a
    page server started detached by a short command that ends at once (`arrange.py open`, `design.py open`:
    how the Assistant starts its own servers) is still found, even though the guard never saw its parent.

What the guard cannot see (so "tiny clips only, one video test at a time" stays the real protection, and a low
"the most it took" line is never proof that a test is light):
  - a program started detached, with its parent gone, AND given an environment of its own that leaves the
    mark out (a test that builds `env=` from nothing). Start such a server straight from the test instead;
  - anything the system itself starts on a program's behalf: macOS starting an app (the transcriber), or the
    system's own video decoding helpers. They are outside the tree altogether;
  - memory taken and given back between two looks (half a second apart): a quick balloon is never seen, and
    the "most it took" line leaves it out;
  - memory macOS has compressed or swapped out. `ps` counts only what is in real memory now (RSS), so when the
    Mac is truly short a program can read lower than what it holds, exactly when it matters;
  - and the other way round: memory shared between programs is counted once per program, so a hidden Chrome
    with its many helpers reads higher than it really is, and may be stopped a little early.

When the command ends by itself the guard ends too. Programs the command left running are NOT stopped (a test
stops its own servers); the guard names how many there are on stderr, so a leftover is seen.

Ctrl+C, or a stop sent to the guard, is passed on to the whole tree, and every program of it gets up to 5
seconds to tidy up and end; whatever is still there then is stopped for good. (Typed in a terminal, Ctrl+C
reaches the command twice: once from the terminal and once passed on by the guard.) A stop for memory is at
once and without warning, so a test stopped that way leaves its scratch folders and lock files behind.

Mac (and Linux) only: memory is read with `ps`. On Windows the command is run unguarded and one line says so
(no clip is made on a PC, so nothing heavy runs there). The same when `ps` can't be run at all. Unguarded, a
stop sent to the guard ends the command itself only, not what it started.

Exit codes: the command's own; 9 = stopped for memory; 2 = the guard was called wrongly; 127 = the command
could not be started. (A command that itself exits 9 looks the same from outside; the guard's line tells them apart.)
"""
import math
import os
import signal
import subprocess
import sys
import time

EVERY = 0.5          # seconds between looks
STOPPED = 9          # the exit code when the tree was stopped for memory
GRACE = 5.0          # seconds a tree gets to end by itself after Ctrl+C, before it is stopped for good
PS = ["ps", "-axo", "pid=,ppid=,pgid=,rss=,lstart=,comm="]
PS_ENV = ["ps", "eww", "-o", "pid=,command="]     # + -p <pids>: each program's command line and environment
LEAST = 1            # MB: the smallest limit taken

USAGE = "How to call it: python3 tests/guard.py <limit in MB> <command> [its arguments...]"


def say(line):
    try:
        sys.stderr.write("guard: " + line + "\n")
        sys.stderr.flush()
    except (OSError, ValueError):
        pass


def look():
    """Every program on this computer now: {pid: (ppid, pgid, rss in KB, when it started, its name)}; None if ps failed."""
    env = dict(os.environ, LC_ALL="C", LANG="C")
    try:
        got = subprocess.run(PS, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if got.returncode != 0:
        return None
    table = {}
    for line in got.stdout.decode("utf-8", "replace").splitlines():
        bits = line.split(None, 9)          # pid ppid pgid rss + five words of start time + the name
        if len(bits) < 9:
            continue
        try:
            pid, ppid, pgid, rss = int(bits[0]), int(bits[1]), int(bits[2]), int(bits[3])
        except ValueError:
            continue
        table[pid] = (ppid, pgid, rss, " ".join(bits[4:9]), bits[9] if len(bits) > 9 else "")
    return table or None


def marked(pids, mark):
    """Which of these programs carry this run's mark in their environment (read with ps; own programs only)."""
    pids = sorted(pids)
    found = set()
    env = dict(os.environ, LC_ALL="C", LANG="C")
    for i in range(0, len(pids), 200):
        try:
            got = subprocess.run(PS_ENV + ["-p", ",".join(str(p) for p in pids[i:i + 200])],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, timeout=20)
        except (OSError, subprocess.SubprocessError):
            continue
        for line in got.stdout.decode("utf-8", "replace").splitlines():
            bits = line.split(None, 1)
            if len(bits) == 2 and bits[0].isdigit() and mark in bits[1].split():
                found.add(int(bits[0]))
    return found


class Tree:
    """The command and everything that came from it, remembered from one look to the next."""

    def __init__(self, root, mark=None, before=None, marked=marked):
        self.root = root
        self.root_seen = False    # the command is taken in by its number once only (the number can be handed on)
        self.me = os.getpid()
        self.my_group = os.getpgrp()
        self.known = {}       # pid -> when it started (so a number handed to a new program is not mistaken)
        self.mark = mark      # "GUARD_TREE_<n>=<word>", in the environment of everything the command starts
        self.marked = marked
        # programs already looked at and found not to be this run's: (pid, when it started). Everything that was
        # running before the command started is here from the beginning.
        self.not_ours = set((pid, row[3]) for pid, row in (before or {}).items())

    def members(self, table):
        """The pids in `table` that belong to the tree now."""
        mine = set()
        for pid, started in list(self.known.items()):
            if pid in table and table[pid][3] == started:
                mine.add(pid)
            else:
                del self.known[pid]
        if not self.root_seen and self.root in table:
            mine.add(self.root)
            self.root_seen = True
        children = {}
        for pid, row in table.items():
            children.setdefault(row[0], []).append(pid)
        while True:
            grew = True
            while grew:
                grew = False
                todo = list(mine)
                while todo:
                    for kid in children.get(todo.pop(), ()):
                        if kid not in mine and kid != self.me:
                            mine.add(kid)
                            todo.append(kid)
                            grew = True
                # the groups living programs of the tree are in NOW (never the guard's own). Nothing is carried
                # over from an earlier look: a group with no tree program left in it is no longer the tree's.
                groups = set(table[pid][1] for pid in mine)
                groups.discard(self.my_group)
                for pid, row in table.items():
                    if row[1] > 1 and row[1] in groups and pid not in mine and pid != self.me:
                        mine.add(pid)
                        grew = True
            if not self.mark:
                break
            # programs with no parent left that nobody has looked at yet: this run's if they carry its mark
            loose = [pid for pid, row in table.items()
                     if row[0] == 1 and pid not in mine and pid != self.me and (pid, row[3]) not in self.not_ours]
            if not loose:
                break
            ours = set(self.marked(loose, self.mark)) & set(loose)
            for pid in loose:
                if pid not in ours:
                    self.not_ours.add((pid, table[pid][3]))
            if not ours:
                break
            mine |= ours
        mine.discard(self.me)
        for pid in mine:
            self.known[pid] = table[pid][3]
        return mine

    def send(self, table, sig):
        sent = 0
        for pid in self.members(table):
            try:
                os.kill(pid, sig)
                sent += 1
            except (ProcessLookupError, PermissionError):
                pass
        return sent

    def stop_for_good(self, proc):
        """Stop every program of the tree, looking again until none is left (a program can start another as it goes).
        Gives back how many were still there when it gave up (0 when all are gone)."""
        left = 0
        until = time.time() + 10
        while time.time() < until:
            try:
                proc.kill()
            except OSError:
                pass
            table = look()
            if table is None:
                break
            gone = proc.poll() is not None      # the command itself has ended (and is no longer in the way)
            alive = [p for p in self.members(table) if not (p == self.root and gone)]
            left = len(alive)
            if not alive:
                break
            for pid in alive:
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            try:
                proc.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        if left:
            table = look()
            if table is not None:
                gone = proc.poll() is not None
                left = len([p for p in self.members(table) if not (p == self.root and gone)])
        return left

    def wait_out(self, proc, seconds):
        """After a stop was passed on: give every program of the tree up to `seconds` to end by itself."""
        until = time.time() + seconds
        while time.time() < until:
            gone = proc.poll() is not None
            table = look()
            if table is None:
                if gone:
                    return
            elif not [p for p in self.members(table) if not (p == self.root and gone)]:
                return
            try:
                proc.wait(timeout=min(EVERY, max(0.05, until - time.time())))
            except subprocess.TimeoutExpired:
                pass


def not_stopped(left):
    return f" BUT {left} program{'s' if left != 1 else ''} could not be stopped and may still be running." if left else ""


def mb(kb):
    return int(round(kb / 1024.0))


def biggest(table, pids, n=3):
    rows = sorted(((table[p][2], p, os.path.basename(table[p][4]) or "?") for p in pids), reverse=True)[:n]
    return ", ".join(f"{name} {mb(kb)} MB" for kb, _pid, name in rows)


def code_of(returncode):
    return 128 - returncode if returncode < 0 else returncode


def main(argv):
    if len(argv) < 3:
        say(USAGE)
        return 2
    try:
        limit = float(argv[1])
    except ValueError:
        limit = 0
    if not (math.isfinite(limit) and limit >= LEAST):
        say(f"The limit has to be a number of MB, {LEAST} or more, and \"{argv[1]}\" is not. " + USAGE)
        return 2
    command = argv[2:]
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        say(USAGE)
        return 2

    # everything running before the command starts (GUARD_NO_PS=1, for the guard's own test, plays a PC)
    before = None if (os.name == "nt" or os.environ.get("GUARD_NO_PS")) else look()
    watching = before is not None
    if not watching:
        say("This computer's memory can't be read here (no ps), so the command runs unguarded.")

    # whatever is run under the guard can never build or start the real transcriber app (transcribe.py's
    # TALKING_NO_REAL): a video test that forgets to say so itself still cannot raise the Mac's permission box
    os.environ.setdefault("TALKING_NO_REAL", "1")

    # this run's mark: one line of environment that everything the command starts inherits
    mark_name, mark_word = f"GUARD_TREE_{os.getpid()}", os.urandom(8).hex()
    try:
        proc = subprocess.Popen(command, env=dict(os.environ, **{mark_name: mark_word}) if watching else None)
    except OSError as e:
        say(f"Couldn't start \"{command[0]}\": {e.strerror or e}.")
        return 127

    asked = []            # a stop the guard itself was sent (Ctrl+C, kill)

    def note(signum, _frame):
        asked.append(signum)

    for name in ("SIGINT", "SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            try:
                signal.signal(getattr(signal, name), note)
            except (OSError, ValueError):
                pass

    if not watching:
        while True:
            try:
                return code_of(proc.wait(timeout=EVERY))
            except subprocess.TimeoutExpired:
                pass
            if asked:
                try:
                    proc.terminate()
                    proc.wait(timeout=GRACE)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                except OSError:
                    pass
                return 128 + asked[0]

    tree = Tree(proc.pid, mark=f"{mark_name}={mark_word}", before=before)
    limit_kb = limit * 1024
    peak = 0
    blind = 0             # looks in a row that failed
    table = None
    while True:
        if asked:
            table = look()
            if table is not None:
                tree.send(table, asked[0])
            else:
                try:
                    proc.send_signal(asked[0])
                except OSError:
                    pass
            tree.wait_out(proc, GRACE)
            left = tree.stop_for_good(proc)
            say("Stopped, because the guard itself was told to stop." + not_stopped(left))
            return 128 + asked[0]

        looked = look()
        if looked is None:
            blind += 1
            if blind == 20:
                say("ps has not answered for 10 seconds; the command is running unwatched until it does.")
        else:
            blind = 0
            table = looked
            pids = tree.members(table)
            total = sum(table[p][2] for p in pids)
            peak = max(peak, total)
            if total > limit_kb:
                top = biggest(table, pids)
                left = tree.stop_for_good(proc)
                say(f"STOPPED. This run reached {mb(total)} MB, past the {mb(limit_kb)} MB limit, "
                    f"so it and everything it started were stopped ({len(pids)} program{'s' if len(pids) != 1 else ''}; the biggest: {top})."
                    + not_stopped(left))
                return STOPPED

        try:
            returncode = proc.wait(timeout=EVERY)
        except subprocess.TimeoutExpired:
            continue
        left = 0
        after = look()
        if after is not None:
            left = len([p for p in tree.members(after) if p != proc.pid])
        say(f"finished under the limit: the most it took was {mb(peak)} MB of {mb(limit_kb)} MB."
            + (f" {left} program{'s' if left != 1 else ''} it started {'are' if left != 1 else 'is'} still running "
               f"(not stopped; not watched from here on)." if left else ""))
        return code_of(returncode)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
