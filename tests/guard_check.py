#!/usr/bin/env python3
"""The memory guard (tests/guard.py), tried on small programs this test writes itself.

    python3 tests/guard_check.py [--work <scratch folder>]

No video, no server, no page, nothing outside its scratch folder. The programs it starts take 320 MB at the
very most, in 16 MB steps, and only until the guard stops them (limits here are 80 to 120 MB); each ends by
itself after 40 seconds whatever happens, so a guard that failed leaves nothing behind for long.

What it checks:
  1. a command under the limit finishes with its own exit code, its own output passed through, and the guard's
     one line about the most memory it saw;
  2. a command that takes more than the limit is stopped: exit 9, a plain line naming the limit, and the
     program really is gone;
  3. the tree counts, not just the command: a child of the command that takes too much is stopped, and so is
     the command;
  4. memory is added up across the tree: two children each under the limit, together over it, are stopped;
  5. a program started "detached" (a session of its own, as a page server is) is still counted and stopped;
  6. a program whose parent has gone is still watched, once it has been seen;
  7. a command that a signal ended gives 128 + the signal's number;
  8. a stop sent to the guard itself (Ctrl+C) stops the whole tree;
  9. programs a finished command left running are named in the guard's line, and not stopped;
 10. called wrongly: exit 2 with how to call it (a limit of inf, or under 1 MB, too); a command that can't be
     started: exit 127;
 11. where memory can't be read (a PC): the command runs unguarded, one line says so, same exit code;
 12. bystanders are left alone: a program started before the guard (in the test's own group, and in a session
     of its own) is still running after a stop for memory and after a Ctrl+C;
 13. a server started detached by a go-between that ends at once (how the Assistant starts its page servers)
     is still found, by the mark the guard puts in the command's environment, and stopped;
 14. after Ctrl+C every program of the tree gets its seconds to tidy up, not only the command;
 15. the tree's own arithmetic on made-up tables: a process group is forgotten once nothing of the tree is in
     it, so a stranger handed the same number later is not counted; the command's own number likewise;
 16. the test's own clean-up only ever touches programs this run started, and a guard that hangs is a FAIL
     line, not a crash.
On Windows only 10, 11 and 15 run; the rest SKIP. Every line says PASS, FAIL or SKIP. Exit 1 only when
something FAILED; the scratch folder is kept then.

Every run keeps its programs and its lists of program numbers in a folder of its own inside the scratch
folder, so it is safe to run twice, or two at once, with the same --work. GUARD_UNDER_TEST=<file> tries
another copy of the guard (for showing that a broken guard fails).
"""
import importlib.util
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = Path(os.environ.get("GUARD_UNDER_TEST") or ROOT / "tests" / "guard.py")
RUN = [None]         # this run's own folder: its programs and pid files live here and nowhere else
PY = sys.executable
PC = os.name == "nt"

RESULTS = {"PASS": 0, "FAIL": 0, "SKIP": 0}


def check(what, ok, detail=""):
    RESULTS["PASS" if ok else "FAIL"] += 1
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:500]}]" if detail and not ok else ""), flush=True)
    return ok


def skip(what, why):
    RESULTS["SKIP"] += 1
    print(f"SKIP  {what}   [{why}]", flush=True)


# A program that takes memory a step at a time, writes its number to a file first, and ends by itself.
EATER = r'''
import os, sys, time
mb, pidfile = int(sys.argv[1]), sys.argv[2]
with open(pidfile, "a") as f:
    f.write(str(os.getpid()) + "\n")
if len(sys.argv) > 3:
    time.sleep(float(sys.argv[3]))      # stay small this long first
held, end = [], time.time() + 40
while len(held) * 16 < mb and time.time() < end:
    held.append(b"\x01" * (16 * 1024 * 1024))
    time.sleep(0.05)
while time.time() < end:
    time.sleep(0.2)
'''

# A command that starts eaters and waits. argv: pidfile, how ("plain" | "detached" | "orphan"), then one MB per eater.
PARENT = r'''
import os, subprocess, sys, time
pidfile, how, sizes = sys.argv[1], sys.argv[2], sys.argv[3:]
eater = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eater.py")
with open(pidfile, "a") as f:
    f.write(str(os.getpid()) + "\n")
if how == "orphan":
    # a go-between starts the eater in a session of its own; the eater stays small for 4 seconds; the go-between
    # stays 2 (long enough for the guard to have seen the eater), then goes, so the eater has no parent when it grows
    mid = ("import subprocess, sys, time\n"
           "subprocess.Popen([sys.executable] + sys.argv[1:], start_new_session=True)\n"
           "time.sleep(2)\n")
    subprocess.Popen([sys.executable, "-c", mid, eater, sizes[0], pidfile, "4"])
else:
    for mb in sizes:
        subprocess.Popen([sys.executable, eater, mb, pidfile], start_new_session=(how == "detached"))
end = time.time() + 40
while time.time() < end:
    time.sleep(0.2)
'''

# A program that only waits (a bystander: nothing to do with the guard). Ends by itself.
BYSTANDER = r'''
import time
end = time.time() + 60
while time.time() < end:
    time.sleep(0.2)
'''

# A command and its child that tidy up when told to stop. argv: pidfile, the file the child writes when it has
# tidied, then "child" for the child. Told to stop, the command ends at once; the child takes 1.5 seconds first.
TIDY = r'''
import os, signal, subprocess, sys, time
pidfile, done = sys.argv[1], sys.argv[2]
child = len(sys.argv) > 3
with open(pidfile, "a") as f:
    f.write(str(os.getpid()) + "\n")
def stop(*_):
    if child:
        time.sleep(1.5)
        with open(done, "w") as f:
            f.write("tidied")
    os._exit(0)
signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
if not child:
    subprocess.Popen([sys.executable, os.path.abspath(__file__), pidfile, done, "child"])
end = time.time() + 40
while time.time() < end:
    time.sleep(0.1)
'''


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    out = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(out) and not out.startswith("Z")


def ours(pid):
    """Is this number, right now, a program THIS run started? (Its command line names this run's own folder.)
    A number in a pid file is only a number: by the time it is read it may belong to something else entirely."""
    if not alive(pid):
        return False
    out = subprocess.run(["ps", "-ww", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout
    return str(RUN[0]) in out


def pids_in(pidfile):
    try:
        return [int(x) for x in Path(pidfile).read_text().split()]
    except OSError:
        return []


def all_gone(pidfile, wait=5.0):
    end = time.time() + wait
    while time.time() < end:
        if not any(ours(p) for p in pids_in(pidfile)):
            return True
        time.sleep(0.1)
    return False


def sweep(pidfile):
    """Stop what is left of this run's programs in this list. Never a number that is not this run's any more."""
    for p in pids_in(pidfile):
        if ours(p):
            try:
                os.kill(p, signal.SIGKILL)
            except OSError:
                pass


def sweep_all():
    for f in sorted(RUN[0].glob("pids-*.txt")):
        sweep(f)


def text(x):
    return x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "")


def guard(args, timeout=60, env=None):
    """Run the guard. A guard that does not finish in time is a result (-1), not a crash, and nothing is left."""
    t = time.time()
    try:
        got = subprocess.run([PY, str(GUARD)] + [str(a) for a in args], capture_output=True, text=True,
                             timeout=timeout, env=env)
    except subprocess.TimeoutExpired as e:
        sweep_all()
        return -1, text(e.stdout), text(e.stderr) + f"\n(the guard did not finish in {timeout} seconds)", time.time() - t
    return got.returncode, got.stdout, got.stderr, time.time() - t


def both(a, b):
    out = dict(a)
    out.update(b)
    return out


def tree_checks():
    """15. The tree's own arithmetic, on made-up tables (no program is started; runs on every computer)."""
    spec = importlib.util.spec_from_file_location("guard_under_test", str(GUARD))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    me, mygroup = os.getpid(), (os.getpgrp() if hasattr(os, "getpgrp") else -7)
    if not hasattr(os, "getpgrp"):
        os.getpgrp = lambda: mygroup          # a PC has no process groups; the arithmetic is the same
    T0, T1, T2 = "Thu Nov 12 10:00:00 2026", "Thu Nov 12 10:00:05 2026", "Thu Nov 12 10:00:09 2026"
    base = {1: (0, 1, 10, T0, "launchd"), me: (1, mygroup, 10, T0, "guard")}

    def row(ppid, pgid, when=T0):
        return (ppid, pgid, 100, when, "x")

    # a detached server (group 500) comes and goes; later a stranger is handed 500 and leads group 500
    tree = g.Tree(100, marked=lambda pids, mark: set())
    a = tree.members(both(base, {100: row(me, mygroup), 500: row(100, 500)}))
    b = tree.members(both(base, {100: row(me, mygroup)}))
    c = tree.members(both(base, {100: row(me, mygroup), 500: row(1, 500, T1), 501: row(500, 500, T1)}))
    check("the tree: a detached program is counted while it lives", a == {100, 500} and b == {100}, (a, b))
    check("the tree: a stranger later handed the same group number (and its child) is NOT counted", c == {100}, c)

    # a group still holding a tree program keeps drawing in what joins it
    tree = g.Tree(100, marked=lambda pids, mark: set())
    tree.members(both(base, {100: row(me, mygroup), 500: row(100, 500), 510: row(500, 500)}))
    d = tree.members(both(base, {100: row(me, mygroup), 510: row(1, 500), 520: row(1, 500, T1)}))
    check("the tree: a group with a tree program still in it draws in what joins that group", d == {100, 510, 520}, d)

    # the command's own number, handed to a stranger after the command has gone
    tree = g.Tree(100, marked=lambda pids, mark: set())
    tree.members(both(base, {100: row(me, mygroup), 200: row(100, mygroup)}))
    tree.members(both(base, {200: row(1, mygroup)}))
    e = tree.members(both(base, {200: row(1, mygroup), 100: row(1, 100, T2), 101: row(100, 100, T2)}))
    check("the tree: the command's own number, handed on after it ended, is not taken for the command", e == {200}, e)

    # the mark: a parentless program is asked about once; taken in (with its children) only if it carries the mark
    asked = []

    def carries(pids, mark):
        asked.append(sorted(pids))
        return set(p for p in pids if p == 700)

    before = both(base, {50: row(1, 50)})
    tree = g.Tree(100, mark="GUARD_TREE_1=word", before=before, marked=carries)
    table = both(before, {100: row(me, mygroup), 700: row(1, 700, T1), 701: row(700, 700, T1), 800: row(1, 800, T1)})
    f1 = tree.members(table)
    f2 = tree.members(table)
    check("the tree: a parentless program carrying this run's mark is taken in, with what it started", f1 == {100, 700, 701} and f2 == f1, (f1, f2))
    check("the tree: programs running before the command are never asked about, and each newcomer only once",
          asked == [[700, 800]], asked)


def main():
    code = run()
    if RUN[0] is not None and not PC:
        sweep_all()
    return code


def run():
    work = None
    if "--work" in sys.argv:
        work = Path(sys.argv[sys.argv.index("--work") + 1])
        work.mkdir(parents=True, exist_ok=True)
    made = work is None
    if made:
        work = Path(tempfile.mkdtemp(prefix="guard-check-"))
    # this run's own folder inside the scratch folder: a second run (or one at the same moment) with the same
    # --work never reads this run's lists of program numbers, and this run never reads another's
    run_dir = RUN[0] = Path(tempfile.mkdtemp(prefix="run-", dir=str(work))).resolve()
    for name, body in (("eater.py", EATER), ("parent.py", PARENT), ("bystander.py", BYSTANDER), ("tidy.py", TIDY)):
        (run_dir / name).write_text(body, encoding="utf-8")
    stale = sorted(f.name for f in run_dir.glob("pids-*.txt"))
    check("this run's lists of program numbers are in a folder of its own, empty at the start (safe to run twice in one --work)",
          run_dir != work.resolve() and run_dir.parent == work.resolve() and not stale, (str(run_dir), stale))
    eater, parent, bystander, tidy = (run_dir / n for n in ("eater.py", "parent.py", "bystander.py", "tidy.py"))
    n = [0]

    def pidfile():
        n[0] += 1
        return run_dir / f"pids-{n[0]}.txt"

    def stand_by(own_session):
        b = subprocess.Popen([PY, str(bystander)], start_new_session=own_session,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return b

    # 10. called wrongly (every computer)
    code, out, err, _ = guard([])
    check("no limit and no command: exit 2, and it says how to call it", code == 2 and "How to call it" in err, (code, err))
    code, out, err, _ = guard(["lots", PY, "-c", "pass"])
    check("a limit that is not a number: exit 2, in plain words", code == 2 and "lots" in err and "Traceback" not in err, (code, err))
    code, out, err, _ = guard(["0", PY, "-c", "pass"])
    check("a limit of 0: exit 2", code == 2, (code, err))
    for bad in ("inf", "1e999", "nan", "-5", "0.001"):
        code, out, err, _ = guard([bad, PY, "-c", "pass"])
        check(f"a limit of {bad}: exit 2, in plain words", code == 2 and bad in err and "Traceback" not in err, (code, err))
    code, out, err, _ = guard(["100"])
    check("a limit and no command: exit 2", code == 2, (code, err))
    code, out, err, _ = guard(["100", str(work / "no-such-program")])
    check("a command that can't be started: exit 127, in plain words", code == 127 and "Couldn't start" in err and "Traceback" not in err, (code, err))

    # 11. where memory can't be read
    env = dict(os.environ, GUARD_NO_PS="1")
    code, out, err, _ = guard(["100", PY, "-c", "import sys; print('through'); sys.exit(4)"], env=env)
    check("memory can't be read: the command still runs, with its own exit code and output", code == 4 and "through" in out, (code, out, err))
    check("memory can't be read: one line says it runs unguarded", err.count("unguarded") == 1 and len(err.strip().splitlines()) == 1, err)
    if PC:
        code, out, err, _ = guard(["100", PY, "-c", "import sys; sys.exit(6)"])
        check("on a PC: unguarded by itself, one line, own exit code", code == 6 and "unguarded" in err, (code, err))
        for what in ("under the limit", "over the limit", "a child over the limit", "two children together",
                     "a detached program", "a program whose parent has gone", "ended by a signal",
                     "a stop sent to the guard", "programs left running", "bystanders left alone",
                     "a server started by a go-between that ends at once", "time to tidy up after Ctrl+C",
                     "the test's own clean-up"):
            skip(what, "the guard reads memory with ps; on a PC it runs the command unguarded")
        tree_checks()
        return finish(work, made)

    # 15. the tree's arithmetic
    tree_checks()

    # 16. the test's own clean-up (before anything heavy is started)
    pf = pidfile()
    stranger = subprocess.Popen(["sleep", "30"])        # its command line does not name this run's folder
    pf.write_text(f"{stranger.pid}\n", encoding="utf-8")
    gone = all_gone(pf, wait=0.5)
    sweep(pf)
    time.sleep(0.3)
    check("the clean-up: a number in a list that is not this run's program is left alone", stranger.poll() is None and gone,
          (stranger.poll(), gone))
    stranger.kill()
    stranger.wait()
    pf = pidfile()
    try:
        code, out, err, _ = guard(["200", PY, eater, "1", pf], timeout=3)
        crashed = ""
    except subprocess.TimeoutExpired as e:
        code, err, crashed = None, "", repr(e)
        sweep(pf)
    check("a guard that does not finish in time is a result, not a crash, and its programs are swept",
          code == -1 and "did not finish" in err and all_gone(pf), (code, err, crashed, pids_in(pf)))

    # 1. under the limit
    code, out, err, _ = guard(["200", PY, "-c", "import sys; print('its own words'); sys.exit(3)"])
    check("under the limit: the command's own exit code", code == 3, (code, err))
    check("under the limit: its output passes through untouched", out == "its own words\n", out)
    check("under the limit: one line about the most memory it took", "finished under the limit" in err and "of 200 MB" in err
          and len(err.strip().splitlines()) == 1, err)
    code, out, err, _ = guard(["200", "--", PY, "-c", "pass"])
    check("under the limit: exit 0 when the command gives 0 (and a -- before the command is allowed)", code == 0, (code, err))

    # 2. over the limit (12: with two bystanders started first, which must be left alone)
    near, apart = stand_by(False), stand_by(True)
    time.sleep(0.3)
    pf = pidfile()
    code, out, err, took = guard(["80", PY, eater, "320", pf])
    check("over the limit: exit 9", code == 9, (code, err))
    check("over the limit: a plain line that names the limit and what it reached", "STOPPED" in err and "80 MB limit" in err
          and "Traceback" not in err, err)
    check("over the limit: stopped soon after, not at the program's own end", took < 20, took)
    check("over the limit: the program really is gone", all_gone(pf), pids_in(pf))
    sweep(pf)
    check("a stop for memory leaves a bystander in the test's own group running", code == 9 and near.poll() is None, (code, near.poll()))
    check("a stop for memory leaves a bystander in a session of its own running", code == 9 and apart.poll() is None, (code, apart.poll()))

    # 3. a child of the command
    pf = pidfile()
    code, out, err, took = guard(["80", PY, parent, pf, "plain", "320"])
    check("a child over the limit: exit 9", code == 9, (code, err))
    check("a child over the limit: the child and the command are both gone", len(pids_in(pf)) == 2 and all_gone(pf), pids_in(pf))
    sweep(pf)

    # 4. added up across the tree: 80 + 80 (plus the programs themselves) against 120; one alone is under it
    pf = pidfile()
    code, out, err, took = guard(["120", PY, parent, pf, "plain", "80", "80"])
    check("two children, each under the limit, together over it: exit 9", code == 9, (code, err))
    check("two children: all three programs are gone", len(pids_in(pf)) == 3 and all_gone(pf), pids_in(pf))
    sweep(pf)
    pf = pidfile()
    g = subprocess.Popen([PY, str(GUARD), "120", PY, str(parent), str(pf), "plain", "64"],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(5)
    check("one such child alone stays under the same limit: still running after 5 seconds", g.poll() is None, g.poll())

    # 8. a stop sent to the guard (the same run)
    g.send_signal(signal.SIGINT)
    try:
        out, err = g.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        g.kill()
        out, err = g.communicate()
    check("Ctrl+C on the guard: exit 128 + 2", g.returncode == 130, (g.returncode, err))
    check("Ctrl+C on the guard: the command and its child are gone", len(pids_in(pf)) == 2 and all_gone(pf), pids_in(pf))
    sweep(pf)
    check("Ctrl+C on the guard leaves both bystanders running", g.returncode == 130 and near.poll() is None and apart.poll() is None,
          (g.returncode, near.poll(), apart.poll()))
    for b in (near, apart):
        b.kill()
        b.wait()

    # 14. after Ctrl+C the whole tree gets its seconds to tidy up, not only the command
    pf, done = pidfile(), run_dir / "tidied.txt"
    g = subprocess.Popen([PY, str(GUARD), "200", PY, str(tidy), str(pf), str(done)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(2.5)
    g.send_signal(signal.SIGINT)
    try:
        out, err = g.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        g.kill()
        out, err = g.communicate()
    check("Ctrl+C: a child that needs 1.5 seconds to tidy up gets them, though the command ended at once",
          g.returncode == 130 and done.exists() and len(pids_in(pf)) == 2, (g.returncode, done.exists(), pids_in(pf), err))
    check("Ctrl+C: and then all of it is gone", all_gone(pf), pids_in(pf))
    sweep(pf)

    # 5. detached
    pf = pidfile()
    code, out, err, took = guard(["80", PY, parent, pf, "detached", "320"])
    check("a detached program (a session of its own) over the limit: exit 9", code == 9, (code, err))
    check("a detached program: it and the command are gone", len(pids_in(pf)) == 2 and all_gone(pf), pids_in(pf))
    sweep(pf)

    # 6. its parent has gone
    pf = pidfile()
    code, out, err, took = guard(["80", PY, parent, pf, "orphan", "320"])
    check("a program whose parent went away, over the limit: exit 9", code == 9, (code, err))
    check("a program whose parent went away: it and the command are gone", len(pids_in(pf)) == 2 and all_gone(pf), pids_in(pf))
    sweep(pf)

    # 13. a go-between starts a detached program and ends AT ONCE, before the guard can have seen either
    pf = pidfile()
    mid = ("import subprocess, sys\n"
           "subprocess.Popen([sys.executable] + sys.argv[1:], start_new_session=True,\n"
           "                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n")
    starter = ("import subprocess, sys, time\n"
               "subprocess.run([sys.executable, '-c', sys.argv[1]] + sys.argv[2:])\n"
               "end = time.time() + 40\n"
               "while time.time() < end: time.sleep(0.2)\n")
    code, out, err, took = guard(["80", PY, "-c", starter, mid, eater, "320", pf, "3"])
    check("a server started by a go-between that ended at once, over the limit: found by its mark, exit 9", code == 9, (code, err))
    check("a server started by a go-between that ended at once: it is gone", len(pids_in(pf)) == 1 and all_gone(pf), pids_in(pf))
    sweep(pf)

    # 7. ended by a signal
    code, out, err, _ = guard(["200", PY, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"])
    check("a command a signal ended: 128 + its number", code == 128 + signal.SIGTERM, (code, err))

    # 9. left running
    pf = pidfile()
    leave = ("import subprocess, sys\n"
             "subprocess.Popen([sys.executable, sys.argv[1], '1', sys.argv[2]], start_new_session=True,\n"
             "                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
             "import time; time.sleep(1.5)\n")
    code, out, err, _ = guard(["200", PY, "-c", leave, eater, pf])
    left = pids_in(pf)
    check("a command that leaves a program running: its own exit code", code == 0, (code, err))
    check("a command that leaves a program running: the guard's line says 1 is still running", "1 program it started is still running" in err, err)
    check("a command that leaves a program running: that program was not stopped", len(left) == 1 and alive(left[0]), left)
    sweep(pf)
    check("(the test's own leftover is stopped)", all_gone(pf), left)

    return finish(work, made)


def finish(work, made):
    print(f"\n{RESULTS['PASS']} passed, {RESULTS['FAIL']} failed, {RESULTS['SKIP']} skipped")
    if RESULTS["FAIL"]:
        print(f"The scratch folder is kept: {work}")
        return 1
    if made:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
