#!/usr/bin/env python3
"""Show a backup's report inside the Claude app (or any browser) at
http://127.0.0.1:<port>/report.html, and let its folder links open Finder.

A page served from localhost is not allowed to open file:// links itself, so
the page asks this server to do it: GET /open?path=<folder>. Only folders the
report names (the source, their drive, the second copy) or folders inside them
may be opened; anything else is refused. Listens on 127.0.0.1 only, so nothing outside this Mac can
reach it. Opened by double-click in Safari, the same links work on their own.

    python3 serve_report.py "<session folder>" [--port 8765]
"""
import argparse
import json
import subprocess
import threading
import subprocess
import sys
import time
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from finder import open_folder as show_in_finder


HERE = Path(__file__).resolve().parent


class Renames:
    """Renames asked for from the page, run one at a time in the background. Each shoot's state is
    queued, running, done or problem, with a line for the page."""
    def __init__(self, session, studio):
        self.session, self.studio = session, studio
        self.state = {}
        self.queue = []
        self.lock = threading.Lock()
        self.worker = None

    def ask(self, shoot_id, name):
        with self.lock:
            self.state[shoot_id] = {"state": "queued", "name": name, "line": "Waiting its turn." if self.queue or self._busy() else "Renaming now."}
            self.queue = [q for q in self.queue if q[0] != shoot_id] + [(shoot_id, name)]
            if not self.worker or not self.worker.is_alive():
                self.worker = threading.Thread(target=self._run, daemon=True)
                self.worker.start()

    def _busy(self):
        return any(v["state"] == "running" for v in self.state.values())

    def _run(self):
        while True:
            with self.lock:
                if not self.queue:
                    return
                shoot_id, name = self.queue.pop(0)
                self.state[shoot_id] = {"state": "running", "name": name, "line": "Renaming the folder and every photo in it..."}
            r = subprocess.run([sys.executable, str(HERE / "rename_shoot.py"), self.session, "--shoot", shoot_id, "--name", name],
                               capture_output=True, text=True)
            out = (r.stdout + r.stderr).strip().splitlines()
            last = out[-1] if out else ""
            ok = r.returncode == 0
            with self.lock:
                if ok and "Nothing to do" in last:
                    self.state[shoot_id] = {"state": "done", "name": name, "line": "Already called that."}
                elif ok:
                    self.state[shoot_id] = {"state": "done", "name": name, "line": "Done. Folder and photos renamed."}
                else:
                    why = last.replace("STOP: ", "")
                    if not why or "/" in why:   # no file paths on the page
                        why = "Something stopped the rename, and nothing was changed."
                    self.state[shoot_id] = {"state": "problem", "name": name, "line": why + " Tell Claude and it'll sort it out."}
            try:  # the report shows the new name and folder
                import report_page
                report_page.write_page(self.session)
            except Exception as ex:
                sys.stderr.write(f"report not rebuilt: {ex}\n")


class Handler(SimpleHTTPRequestHandler):
    allowed = ()
    renames = None
    last_open = {}  # path -> time, so one click never opens two Finder windows

    def do_GET(self):
        parts = urlsplit(self.path)
        if parts.path == "/rename-status":
            body = json.dumps(self.renames.state if self.renames else {}).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if parts.path != "/open":
            return super().do_GET()
        want = parse_qs(parts.query).get("path", [""])[0]
        target = Path(want).expanduser()
        allowed = any(target.resolve().is_relative_to(Path(a).resolve()) for a in self.allowed)
        if not target.is_dir():
            ok, words = False, f"That folder isn't there right now. Is {target.parts[2] if len(target.parts) > 2 and target.parts[1] == 'Volumes' else 'the drive'} plugged in?"
        elif not allowed:
            ok, words = False, "That isn't a folder this report names."
        else:
            now = time.monotonic()
            if now - self.last_open.get(str(target), 0) > 1.0:
                ok, why = show_in_finder(target)  # opens it and brings Finder to the front when macOS allows
                name = target.name or str(target)
                words = (f"Opened {name} in Finder, behind this window. Click Finder in the Dock to see it." if why == "behind"
                         else f"Opened {name} in Finder.") if ok else f"Couldn't open Finder. The folder is {target}. ({why})"
            else:
                ok, words = True, f"Opened {target.name or str(target)} in Finder."
            self.last_open[str(target)] = now
        print(f"open asked: {target} -> {'ok' if ok else 'no'}: {words}", flush=True)
        out = json.dumps({"ok": ok, "words": words}).encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(out)

    def do_POST(self):
        """The page sends one name to rename right away: {"shoot": id, "name": name} to /rename (queued, run one at a
        time). The older /names takes {shoot id: name} and only keeps them in _studio/names.json for Claude."""
        path = urlsplit(self.path).path
        if path == "/rename":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                d = json.loads(self.rfile.read(n) or b"{}")
                shoot, name = str(d["shoot"])[:40], " ".join(str(d["name"]).split())[:120]
                assert shoot and name
            except (ValueError, KeyError, AssertionError, TypeError):
                self.send_error(HTTPStatus.BAD_REQUEST, "expected {shoot, name}")
                return
            self.renames.ask(shoot, name)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"queued")
            sys.stderr.write(f"rename asked: {shoot} -> {name}\n")
            return
        if path != "/names":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            names = json.loads(self.rfile.read(n) or b"{}")
            assert isinstance(names, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in names.items())
        except (ValueError, AssertionError):
            self.send_error(HTTPStatus.BAD_REQUEST, "expected {shoot id: name}")
            return
        clean = {k[:40]: " ".join(v.split())[:120] for k, v in names.items() if v.strip()}
        (Path(self.directory) / "names.json").write_text(json.dumps(clean, indent=1, ensure_ascii=False))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"saved")
        sys.stderr.write(f"names saved: {clean}\n")

    def log_message(self, fmt, *args):  # quieter: only the opens
        if "/open" in str(args[0] if args else ""):
            sys.stderr.write("%s\n" % (fmt % args))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from where import locate
    _, studio = locate(a.session)
    manifest = json.loads((studio / "manifest.json").read_text())
    Handler.allowed = tuple(p for p in (manifest.get("source"), manifest.get("dest"), manifest.get("second")) if p)
    Handler.renames = Renames(a.session, studio)
    # the asked-for port, or the next free one: another session's server may be holding it
    srv = None
    for port in range(a.port, a.port + 20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(studio)))
            break
        except OSError:
            continue
    if not srv:
        sys.exit(f"STOP: no free port between {a.port} and {a.port + 19}.")
    print(f"Report: http://127.0.0.1:{port}/report.html", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
