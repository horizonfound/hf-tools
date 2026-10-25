#!/usr/bin/env python3
"""Show a session's morning report inside the Claude app (or any browser) at
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
import sys
import time
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from finder import open_folder as show_in_finder


class Handler(SimpleHTTPRequestHandler):
    allowed = ()
    last_open = {}  # path -> time, so one click never opens two Finder windows

    def do_GET(self):
        parts = urlsplit(self.path)
        if parts.path != "/open":
            return super().do_GET()
        want = parse_qs(parts.query).get("path", [""])[0]
        target = Path(want).expanduser()
        ok = target.is_dir() and any(target.resolve().is_relative_to(Path(a).resolve()) for a in self.allowed)
        if ok:
            now = time.monotonic()
            if now - self.last_open.get(str(target), 0) > 1.0:
                show_in_finder(target)  # brings Finder to the front, so the click visibly does something
            self.last_open[str(target)] = now
        self.send_response(HTTPStatus.OK if ok else HTTPStatus.FORBIDDEN)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"opened" if ok else b"not a folder this report names")

    def do_POST(self):
        """The first-look page sends the names they typed: {shoot id: name}. Kept in _studio/names.json."""
        if urlsplit(self.path).path != "/names":
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
    print(f"Morning report: http://127.0.0.1:{port}/report.html", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
