#!/usr/bin/env python3
"""A page server that notices the Assistant has been updated since it started, and starts over.

The little servers behind the pages (home and posting, the editing queue, a backup's report) can run for
days. Each one loads the Assistant's code once, when it starts. When the Assistant updates, a running
server keeps drawing yesterday's pages until someone stops and starts it, and a photographer has no idea
that is a thing (Dustin's first-run test, Nov 5: a change made minutes earlier vanished from the report,
and the home page needed a hand restart after every update).

So every server asks, when a page is requested: is the code on disk newer than what I loaded? If it is,
it answers with a one-line "one moment" page that tries again by itself, and starts over on the same
port with the code on disk. If the code on disk does not even compile (a half-written file), it stays
as it is and says so in its log: an old page beats no page.

    in a server's do_GET:
        if fresh.page_path(path) and fresh.stale() and fresh.restart(self):
            return
"""
import os
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def code_stamp():
    """When the newest script in this folder was last written."""
    newest = 0
    for f in HERE.glob("*.py"):
        try:
            newest = max(newest, f.stat().st_mtime_ns)
        except OSError:
            pass
    return newest


STARTED_WITH = code_stamp()
_last = {"t": 0.0, "stale": False}
_restarting = threading.Event()


def stale():
    """True when the code on disk is newer than what this process loaded (looked at most every 2 s, and only
    once the newest file has been still for a second, so a file being written is not caught half way)."""
    now = time.time()
    if now - _last["t"] < 2:
        return _last["stale"]
    stamp = code_stamp()
    _last["t"] = now
    _last["stale"] = stamp != STARTED_WITH and now - stamp / 1e9 > 1.0
    return _last["stale"]


def page_path(path):
    """Only a request for a page restarts the server; the small background questions a page asks do not."""
    return path in ("", "/", "/home") or path.endswith(".html")


def code_ok():
    """None if every script here compiles; otherwise which one does not."""
    for f in sorted(HERE.glob("*.py")):
        try:
            compile(f.read_text(), str(f), "exec")
        except (SyntaxError, ValueError, OSError) as e:
            return f"{f.name}: {e}"
    return None


WAIT_PAGE = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
             "<meta http-equiv='refresh' content='2'><title>One moment</title>"
             "<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#FAF9F6;color:#1F2430;"
             "font:500 17px/1.5 -apple-system,'Helvetica Neue',Arial,sans-serif}p{max-width:26rem;text-align:center;padding:0 1.5rem}"
             "small{display:block;margin-top:.5rem;color:#6B7280;font-weight:400;font-size:14px}</style></head>"
             "<body><p>One moment.<small>The Assistant just got an update. This page comes back by itself in a couple of seconds.</small></p>"
             "<script>setTimeout(function(){location.reload()},1800)</script></body></html>").encode()


def _send_wait(handler):
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(WAIT_PAGE)))
    handler.end_headers()
    handler.wfile.write(WAIT_PAGE)
    try:
        handler.wfile.flush()
    except OSError:
        pass


def restart(handler):
    """Answer this request with the "one moment" page, then start over with the code on disk, on the same
    port. Returns True if it answered (the caller returns), False if the server stays as it is."""
    if _restarting.is_set():
        _send_wait(handler)
        return True
    bad = code_ok()
    if bad:
        sys.stderr.write(f"fresh: newer code on disk does not compile ({bad}); staying on what is loaded\n")
        _last["t"] = time.time() + 30      # ask again in half a minute, not on every page
        _last["stale"] = False
        return False
    _restarting.set()
    port = handler.server.server_address[1]
    _send_wait(handler)

    def go():
        time.sleep(0.4)                    # let the "one moment" page leave
        argv, skip = [], False
        for a in sys.argv:
            if skip:
                skip = False
                continue
            if a == "--port":
                skip = True
                continue
            if a.startswith("--port="):
                continue
            argv.append(a)
        argv += ["--port", str(port)]      # the same address the open pages are pointing at
        sys.stderr.write("fresh: the Assistant was updated; starting over with the new code\n")
        try:
            sys.stderr.flush()
            sys.stdout.flush()
        except OSError:
            pass
        # exec closes this process's listening socket (Python opens sockets close-on-exec), so the port is free
        os.execv(sys.executable, [sys.executable] + argv)

    threading.Thread(target=go).start()
    return True


if __name__ == "__main__":
    print("code on disk last written:", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(code_stamp() / 1e9)))
    print("compiles:", code_ok() or "yes")
