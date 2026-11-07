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

An installed copy updates into a NEW folder (one folder per version), so a running server would never see
newer files beside itself. So the commands Claude runs say where the Assistant lives now (announce(), a
line in ~/.studio/code-home.txt), and a server that finds itself running from somewhere else starts over
from there. The folder comes from that file on this computer, never from a web request.

    in a server's do_GET:
        if fresh.page_path(path) and fresh.stale() and fresh.restart(self):
            return
    in a command's main() (never a server's):
        fresh.announce()
    a server's listening socket (the same on a Mac; on a PC, one that never shares its port):
        srv = fresh.Server(("127.0.0.1", port), handler)
    starting a server from a command, its log kept out of any folder that moves:
        log, before = fresh.start_server([sys.executable, script, ...], "report <night>")

Starting over: on a Mac the process swaps itself for a fresh copy of itself (exec), as it always has. On a
PC that swap does not work the same way, so there the server stops listening, starts a new server on the
same port, and leaves (unproven on a real PC). ASSISTANT_TRY_PC_RESTART=1 takes the PC way on any computer,
so it can be tried on a Mac.
"""
import os
import socket
import stat
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer
import socketserver
from pathlib import Path
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()
from where import place_key  # noqa: E402  (one spelling of a path, for comparing two on a PC)

HERE = Path(__file__).resolve().parent
STUDIO_HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
POINTER = STUDIO_HOME / "code-home.txt"
LOGS = STUDIO_HOME / "logs"   # every page server's log, one file each (never inside a backup's records)

# A server started over on a PC is asked to come back on the port it had (see restart()). Read once here and
# taken out of the environment, so nothing this server starts later (a rename, the queue's server) sees it.
_RESTART_PORT = os.environ.pop("ASSISTANT_RESTART_PORT", None)


def announce():
    """Called by the commands Claude runs, never by a server: this folder is where the Assistant's code is
    now. Quiet about any trouble; a page a little out of date beats a command that fails."""
    try:
        try:
            if place_key(POINTER.read_text(encoding="utf-8").strip()) == place_key(HERE):
                return
        except OSError:
            pass
        POINTER.parent.mkdir(parents=True, exist_ok=True)
        tmp = POINTER.with_name(POINTER.name + ".part")
        tmp.write_text(str(HERE) + "\n", encoding="utf-8")
        this_computer.replace(tmp, POINTER)
    except OSError:
        pass


def moved():
    """The folder the Assistant runs from now, when that is not this one and it holds this server's script."""
    try:
        there = Path(POINTER.read_text(encoding="utf-8").strip())
    except OSError:
        return None
    if not str(there) or place_key(there) == place_key(HERE) or not there.is_dir():
        return None
    return there if (there / Path(sys.argv[0]).name).is_file() else None


def _newest(folder):
    newest = 0
    for f in folder.glob("*.py"):
        try:
            newest = max(newest, f.stat().st_mtime_ns)
        except OSError:
            pass
    return newest


def code_stamp():
    """When the newest script in this folder was last written."""
    return _newest(HERE)


def _reel_folder(scripts=None):
    """The reel's scripts (capcut.py, sound.py...) beside these: ../../assistant-make-a-reel/scripts."""
    return (scripts or HERE).parent.parent / "assistant-make-a-reel" / "scripts"


def _reel_loaded():
    """True once this process has loaded one of the reel's scripts. Only the posting server does, when "Open in
    CapCut" is pressed (capcut.py, and sound.py with it); the report and queue servers never do, so for them
    nothing here changes. Such a server also starts over when only the reel's scripts were updated."""
    folder = _reel_folder()
    try:
        names = [f.stem for f in folder.glob("*.py")]
        want = os.path.normcase(os.path.realpath(str(folder)))
    except OSError:
        return False
    for name in names:
        f = getattr(sys.modules.get(name), "__file__", None)
        if f and os.path.normcase(os.path.dirname(os.path.realpath(f))) == want:
            return True
    return False


STARTED_WITH = code_stamp()
REEL_STARTED_WITH = _newest(_reel_folder())
_last = {"t": 0.0, "stale": False}
_restarting = threading.Event()


def stale():
    """True when the code on disk is newer than what this process loaded (looked at most every 2 s, and only
    once the newest file has been still for a second, so a file being written is not caught half way). A server
    that has loaded the reel's scripts looks at those too."""
    now = time.time()
    if now - _last["t"] < 2:
        return _last["stale"]
    stamp = code_stamp()
    _last["t"] = now
    _last["stale"] = bool(moved()) or (stamp != STARTED_WITH and now - stamp / 1e9 > 1.0)
    if not _last["stale"] and _reel_loaded():
        reel = _newest(_reel_folder())
        _last["stale"] = reel != REEL_STARTED_WITH and now - reel / 1e9 > 1.0
    return _last["stale"]


def page_path(path):
    """Only a request for a page restarts the server; the small background questions a page asks do not."""
    return path in ("", "/", "/home") or path.endswith(".html")


def code_ok(folder=None):
    """None if every script in the folder (this one, unless told) compiles; otherwise which one does not. A
    server that has loaded the reel's scripts asks the same of the reel's scripts beside that folder."""
    folders = [folder or HERE]
    if _reel_loaded():
        folders.append(_reel_folder(folder))
    for d in folders:
        for f in sorted(d.glob("*.py")):
            try:
                compile(f.read_text(encoding="utf-8"), str(f), "exec")
            except (SyntaxError, ValueError, OSError) as e:
                # the log says which folder, for one of the reel's scripts (the server's own: as it always was)
                return f"{f.name}: {e}" if d is folders[0] else f"the reel's {f.name}, in {d}: {e}"
    return None


# ---------------------------------------------------------------- the listening socket

class _QuickServer(ThreadingHTTPServer):
    """Python's own page server, minus one step: it never looks up this computer's own name when it starts.

    Python's server_bind asks socket.getfqdn("127.0.0.1"), a reverse name lookup, only to fill a name that
    nothing here reads (only Python's CGI handler uses it). On a Mac whose network is slow or misconfigured
    (GitHub's Mac machines, Nov 7; a VPN, a hotel network) that lookup can hang about 30 seconds, so a page
    took half a minute to come up, or a starter gave up on it. Binding is otherwise exactly Python's own."""

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


class _PCServer(_QuickServer):
    """The page server's socket on a PC (unproven on a real PC).

    Python's web server asks for SO_REUSEADDR, which on a Mac only lets a server come back quickly after a
    restart. On Windows the same switch lets a second socket take a port another one is already listening on
    (Microsoft, "Using SO_REUSEADDR and SO_EXCLUSIVEADDRUSE": two sockets that both set it on 127.0.0.1 both
    succeed, and which one answers is then anyone's guess). Every server here looks for the next free port when
    its first choice is taken, so on a PC that switch would put two backups' reports on one port. Without it
    a taken port is refused (WSAEADDRINUSE) and the server moves on, as it does on a Mac.

    SO_EXCLUSIVEADDRUSE is left off on purpose: Microsoft says a port held that way may not be bound again
    until the connections it accepted have fully closed, which would keep a restarted server off its own port.

    A server that is starting over (restart(), below) waits up to ten seconds for its old port, which the
    process it replaces has only just let go of, before it settles for the next one."""
    allow_reuse_address = False

    def server_bind(self):
        port = str(self.server_address[1])
        give_up = time.monotonic() + (10.0 if _RESTART_PORT and _RESTART_PORT == port else 0.0)
        while True:
            try:
                return super().server_bind()
            except OSError:
                if time.monotonic() >= give_up:
                    raise
            time.sleep(0.25)
            try:  # a fresh socket for each try: a refused bind is not retried on the same one
                self.socket.close()
            except OSError:
                pass
            self.socket = socket.socket(self.address_family, self.socket_type)


# Every page server makes its socket with this. On a Mac it is Python's own server, without the name lookup.
Server = _PCServer if this_computer.WINDOWS else _QuickServer


# ---------------------------------------------------------------- the servers' logs

def server_log(name):
    """Where a page server's log lives: <STUDIO_HOME>/logs/<name>.log, one file per server. Never inside a
    backup's records: on a PC a file a running server holds open keeps its folder from being moved (the
    settle step moves the records folder), and a Mac does not care where it is."""
    LOGS.mkdir(parents=True, exist_ok=True)
    return LOGS / (this_computer.safe_name(name, 90, "server") + ".log")


def start_server(cmd, name):
    """Start a page server so it outlives this command, its output going to its own log. Returns (the log,
    how long the log was before), so the starter can read just the lines this server writes (each server
    prints its address first). Raises OSError if it could not be started."""
    log = server_log(name)
    try:
        before = log.stat().st_size
    except OSError:
        before = 0
    with open(log, "a", encoding="utf-8") as fh:   # the server has its own copy of the handle; ours closes
        this_computer.popen_detached(cmd, stdout=fh, stderr=subprocess.STDOUT)
    return log, before


def log_since(log, before):
    """What a server has written to its log since `before` (a length from start_server), as text."""
    try:
        with open(log, "rb") as f:
            f.seek(before)
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


# ---------------------------------------------------------------- starting over

WAIT_PAGE = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
             "<meta http-equiv='refresh' content='2'><title>One moment</title>"
             "<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#FAF9F6;color:#1F2430;"
             "font:500 17px/1.5 -apple-system,'Helvetica Neue','Segoe UI',system-ui,Arial,sans-serif}p{max-width:26rem;text-align:center;padding:0 1.5rem}"
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


def _spawn_instead():
    """True where a server starts over by starting a new one beside it (a PC) rather than by exec (a Mac)."""
    return this_computer.WINDOWS or os.environ.get("ASSISTANT_TRY_PC_RESTART") == "1"


def _log_handle():
    """This server's own log (its output), when that is a file the new server can carry on writing to."""
    try:
        if stat.S_ISREG(os.fstat(sys.stdout.fileno()).st_mode):
            return sys.stdout
    except (OSError, ValueError, AttributeError):
        pass
    return None


def _spawn_over(server, argv, port):
    """The PC's way of starting over (unproven on a real PC). In this order, so the page is down for as
    short a time as possible and two servers never hold the port at once:
      1. leave serve_forever cleanly (closing the socket under it would end it with an error instead),
      2. let go of the port,
      3. start the new server on the same port, writing to the same log, told to wait for the port if Windows
         has not quite let go of it yet (_PCServer),
      4. leave. This runs in a thread that is not a daemon, so the process cannot end before step 3."""
    t = threading.Thread(target=server.shutdown, daemon=True)
    t.start()
    t.join(5)                              # serve_forever looks every half second; never wait for ever
    try:
        server.server_close()
    except OSError:
        pass
    out = _log_handle()
    env = dict(os.environ, ASSISTANT_RESTART_PORT=str(port))   # PYTHONUTF8 rides along (this_computer sets it)
    try:
        this_computer.popen_detached([sys.executable] + argv, env=env,     # a list: a space in a path is fine
                                     stdout=out if out is not None else subprocess.DEVNULL,
                                     stderr=subprocess.STDOUT if out is not None else subprocess.DEVNULL)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"fresh: could not start the new server ({e}); this page stays down until it is started again\n")
        try:
            sys.stderr.flush()
        except OSError:
            pass
        os._exit(1)
    os._exit(0)


def restart(handler):
    """Answer this request with the "one moment" page, then start over with the code on disk, on the same
    port. Returns True if it answered (the caller returns), False if the server stays as it is."""
    if _restarting.is_set():
        _send_wait(handler)
        return True
    there = moved()
    bad = code_ok(there)
    if bad:
        sys.stderr.write(f"fresh: newer code on disk does not compile ({bad}); staying on what is loaded\n")
        _last["t"] = time.time() + 30      # ask again in half a minute, not on every page
        _last["stale"] = False
        return False
    spawn = _spawn_instead()
    if spawn:
        # Starting a new process can fail where exec would not get that far; check what it needs first, so a
        # server never closes its port with nothing to take over.
        script = (there / Path(sys.argv[0]).name) if there else Path(os.path.abspath(sys.argv[0]))
        if not (sys.executable and Path(sys.executable).is_file() and script.is_file()):
            sys.stderr.write(f"fresh: cannot find {sys.executable} or {script}; staying on what is loaded\n")
            _last["t"] = time.time() + 30
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
        if there:                          # an update landed in a new folder: run this same server from there
            argv[0] = str(there / Path(argv[0]).name)
            sys.stderr.write(f"fresh: the Assistant now lives in {there}\n")
        sys.stderr.write("fresh: the Assistant was updated; starting over with the new code\n")
        try:
            sys.stderr.flush()
            sys.stdout.flush()
        except OSError:
            pass
        # A video program this server started (a preview copy, a still) stops here: exec keeps this process's
        # number, so it would carry on with nobody to take its answer, holding the video lock (v19 review, Nov 7).
        # The new server starts it again from the beginning.
        this_computer.stop_scripts()
        if spawn:
            if not there:
                argv[0] = os.path.abspath(argv[0])
            _spawn_over(handler.server, argv, port)
            return
        # exec closes this process's listening socket (Python opens sockets close-on-exec), so the port is free
        os.execv(sys.executable, [sys.executable] + argv)

    # On a PC the thread must not be a daemon: the server's main thread ends as soon as it stops serving, and
    # a daemon thread would be cut off before it started the new server. On a Mac, exactly as before.
    threading.Thread(target=go, daemon=False if spawn else None).start()
    return True


if __name__ == "__main__":
    print("code on disk last written:", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(code_stamp() / 1e9)))
    print("compiles:", code_ok() or "yes")
