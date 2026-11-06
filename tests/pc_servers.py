#!/usr/bin/env python3
"""The page servers on a PC, tried for real: written to run on GitHub's Windows machine (and on a Mac).

    python tests/pc_servers.py

In scratch folders it makes itself, on ports 9150 and 9151 (nothing else of the Assistant uses those; ASSISTANT_TEST_PORT moves them):
  1. a page server comes up from a folder with a space in its name, and its log is in STUDIO_HOME/logs;
  2. a second server asked for the same port takes the next one: two servers never share a port
     (on Windows, Python's own server would have shared it; fresh.Server is what stops that);
  3. after an update the server starts over by itself on the same port with the new code: on a Mac the
     same process (exec), on a PC a new one, the old one gone, the log carried on;
  4. code that does not compile is not started; the page keeps working.
It never touches the real scripts: it copies them and changes the copy.
"""
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(os.environ.get("ASSISTANT_SCRIPTS") or ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts")
WINDOWS = os.name == "nt"
BASE = int(os.environ.get("ASSISTANT_TEST_PORT", "9150"))   # this port and the next
results = []


def check(what, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{detail}]" if detail and not ok else ""), flush=True)


def pid_on(port):
    """The PIDs listening on 127.0.0.1:port (netstat on Windows, lsof elsewhere)."""
    if WINDOWS:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, encoding="utf-8", errors="replace").stdout
        return sorted({int(ln.split()[-1]) for ln in out.splitlines()
                       if re.search(rf"127\.0\.0\.1:{port}\s", ln) and "LISTENING" in ln})
    out = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], capture_output=True, encoding="utf-8").stdout
    return sorted(int(x) for x in out.split())


def page(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/queue.html", timeout=3) as r:
            b = r.read().decode("utf-8", "replace")
            return "wait" if "One moment" in b else ("queue" if "Editing queue" in b else "other")
    except Exception:  # noqa: BLE001
        return "down"


def wait_for(fn, secs=12.0):
    end = time.time() + secs
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(0.2)
    return None


def kill(pid):
    try:
        os.kill(pid, signal.SIGTERM)          # TerminateProcess on Windows
    except OSError:
        pass


def main():
    work = Path(tempfile.mkdtemp(prefix="assistant pc servers "))
    code, home = work / "code with a space", work / "home"
    shutil.copytree(SCRIPTS, code, ignore=shutil.ignore_patterns("__pycache__"))
    home.mkdir()
    sys.path.insert(0, str(code))
    os.environ["STUDIO_HOME"] = str(home)
    import fresh
    for p in range(BASE, BASE + 2):
        if pid_on(p):
            sys.exit(f"port {p} is in use here; not touching it")

    # 1. up, with its log in STUDIO_HOME/logs (started the way the Assistant starts it)
    log, before = fresh.start_server([sys.executable, str(code / "edit_queue.py"), "serve", "--port", str(BASE)], "queue")
    check("the log lives in STUDIO_HOME/logs", log == home / "logs" / "queue.log", str(log))
    check("a page server comes up from a folder with a space in its name", wait_for(lambda: page(BASE) == "queue") is not None,
          fresh.log_since(log, before)[-400:])
    first = pid_on(BASE)
    check("its address is the first new line of its log", f"Editing queue: http://127.0.0.1:{BASE}/queue.html" in fresh.log_since(log, before))

    # 2. two servers never share one port
    log2, b2 = fresh.start_server([sys.executable, str(code / "edit_queue.py"), "serve", "--port", str(BASE)], "queue second")
    got = wait_for(lambda: re.search(r"127\.0\.0\.1:(\d+)/", fresh.log_since(log2, b2)))
    port2 = int(got.group(1)) if got else None
    check("a second server asked for a taken port takes the next one", port2 == BASE + 1, fresh.log_since(log2, b2)[-300:])
    check("...and the first one still answers alone on its port", pid_on(BASE) == first and page(BASE) == "queue")
    for p in pid_on(BASE + 1):
        kill(p)

    # 3. code that does not compile is not started
    time.sleep(1.2)
    (code / "broken_on_purpose.py").write_text("def x(:\n", encoding="utf-8")
    time.sleep(2.6)
    check("newer code that does not compile: the page keeps working", page(BASE) == "queue")
    (code / "broken_on_purpose.py").unlink()
    time.sleep(31)                                    # it waits 30 s before looking again

    # 4. an update: starts over by itself, same port, new code
    f = code / "edit_queue.py"
    f.write_text(f.read_text(encoding="utf-8").replace('print(f"Editing queue: {url}"', 'print(f"Editing queue (new code): {url}"', 1),
                 encoding="utf-8")
    time.sleep(2.6)
    saw = page(BASE)
    check("the first page after an update is the 'one moment' page", saw == "wait", saw)
    check("then the page comes back by itself on the same port", wait_for(lambda: page(BASE) == "queue") is not None,
          fresh.log_since(log, before)[-600:])
    text = fresh.log_since(log, before)
    check("the new code is what runs, writing to the same log", f"Editing queue (new code): http://127.0.0.1:{BASE}/queue.html" in text, text[-600:])
    now = pid_on(BASE)
    if WINDOWS or os.environ.get("ASSISTANT_TRY_PC_RESTART") == "1":
        check("the PC way: one new process holds the port, the old one is gone", len(now) == 1 and now != first, f"{now} vs {first}")
    else:
        check("the Mac way: the same process carries on", now == first, f"{now} vs {first}")
    check("no error in the log", "Traceback" not in text, text[-800:])

    for p in pid_on(BASE) + pid_on(BASE + 1):
        kill(p)
    wait_for(lambda: not pid_on(BASE), 5)
    ok = sum(results)
    print(f"\n{ok} of {len(results)} passed." + ("" if ok == len(results) else f"  (scratch folder: {work})"))
    if ok == len(results):
        shutil.rmtree(work, ignore_errors=True)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
