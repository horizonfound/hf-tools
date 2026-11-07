#!/usr/bin/env python3
"""Show a backup's report inside the Claude app (or any browser) at
http://127.0.0.1:<port>/report.html, and let its folder links open Finder (File Explorer on a PC).

A page served from localhost is not allowed to open file:// links itself, so
the page asks this server to do it: GET /open?path=<folder>. Only folders the
report names (the source, their drive, the second copy) or folders inside them
may be opened; anything else is refused. Listens on 127.0.0.1 only, so nothing outside this computer can
reach it. Opened by double-click in Safari, the same links work on their own.

Its log is ~/.studio/logs/report <backup> <tag>.log (log_name), never inside the backup's records.

    python3 serve_report.py "<session folder>" [--port 8765]
"""
import argparse
import hashlib
import json
import subprocess
import threading
import sys
import time
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from finder import open_folder as show_in_finder
import fresh  # noqa: E402  (read at startup: which code this process loaded; see fresh.py)
import look  # noqa: E402  (the pages' own font: GET /look-font)
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()


HERE = Path(__file__).resolve().parent


def quiet():
    """How this server runs its helpers (a rename, the report rebuilt): on a PC with no window of their own
    (unproven on a real PC). A server started from a page has no console, and Windows gives every console program
    such a process starts a new, visible black window; closing it by hand would cut a rename off half way.
    CREATE_NO_WINDOW gives the helper a console with no window instead. A Mac: nothing changes."""
    return {"creationflags": 0x08000000} if this_computer.WINDOWS else {}   # CREATE_NO_WINDOW


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
                               capture_output=True, encoding="utf-8", errors="replace", **quiet())
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
                    if not why or "/" in why or "\\" in why:   # no file paths on the page (a PC's use backslashes)
                        why = "Something stopped the rename, and nothing was changed."
                    self.state[shoot_id] = {"state": "problem", "name": name, "line": why + " Tell Claude and it'll sort it out."}
            try:  # the report shows the new name and folder
                rebuild_report(self.session)
            except Exception as ex:
                sys.stderr.write(f"report not rebuilt: {ex}\n")


def rebuild_report(session):
    """Write the report again, in a fresh process. This server can run for days, and a page built with the
    code it loaded at start comes out in yesterday's look after the Assistant has been updated (Dustin, Nov 5:
    "Use these" on Show me more rebuilt the report and a change made minutes earlier was gone from it). A
    fresh process always uses the code on disk."""
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "report_page.py"), str(session)],
                       capture_output=True, encoding="utf-8", errors="replace", **quiet())
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[-300:])


def log_name(studio):
    """The name of the log for one backup's report server: "report <the backup's name> <a short tag>". Kept in
    ~/.studio/logs (fresh.server_log), not in the backup's records, which the settle step moves: on a PC a log a
    running server holds open would stop that move. The tag tells two backups with the same name apart."""
    studio = Path(studio)
    night = studio.parent.name if studio.name == "_studio" else studio.name
    try:
        whole = studio.resolve()
    except OSError:
        whole = studio
    from where import place_key
    tag = hashlib.sha1(place_key(whole).encode("utf-8", "replace")).hexdigest()[:8]
    return f"report {night[:60]} {tag}"


def report_url(studio):
    """The live report's address for one backup, starting its little server if none answers for it. Used by the
    home page's "See the report" (Dustin, Nov 5: once he pressed Back to home there was no way back to the
    report). A port can be taken over by another backup's server later, so "alive" is not enough: the server
    has to say it serves this backup (/which). Asked never through a proxy (this_computer.open_local): a proxy
    can't see this computer's own pages, so the server would always look gone and another one be started."""
    studio = Path(studio)
    f = studio / "report-url.txt"

    def serving(url):
        try:
            d = json.loads(this_computer.open_local(url.rsplit("/", 1)[0] + "/which", timeout=1).read())
            return Path(d.get("studio", "")).resolve() == studio.resolve()
        except Exception:  # noqa: BLE001
            return False

    if f.exists():
        old = f.read_text(encoding="utf-8").strip()
        if old and serving(old):
            return old
    if not (studio / "report.html").exists():
        return None
    try:
        fresh.start_server([sys.executable, str(Path(__file__).resolve()), str(studio)], log_name(studio))
    except OSError:
        return None
    for _ in range(60):
        time.sleep(0.1)
        if f.exists():
            url = f.read_text(encoding="utf-8").strip()
            if url and serving(url):
                return url
    return None


def queue_url():
    """The live queue page's address. If no queue server answers, start one (edit_queue.py serve) and wait for its line.
    "Is it up?" is asked never through a proxy (this_computer.open_local), as in report_url."""
    try:
        import edit_queue
        f = edit_queue.HOME / "queue-url.txt"
        if f.exists():
            old = f.read_text(encoding="utf-8").strip()
            try:
                this_computer.open_local(old, timeout=1).read(1)
                return old
            except Exception:  # noqa: BLE001
                pass
        fresh.start_server([sys.executable, str(Path(__file__).resolve().parent / "edit_queue.py"), "serve"], "queue")
        for _ in range(40):
            time.sleep(0.1)
            if f.exists():
                url = f.read_text(encoding="utf-8").strip()
                try:
                    this_computer.open_local(url, timeout=1).read(1)
                    return url
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        pass
    return None


class Picks:
    """"Use these six" from the report, run in the background: record the picks as the photographer's,
    mark them in Lightroom (and set aside the keyword of any dropped pick), make the previews, rebuild
    the report. One at a time; the page polls /picks-status."""
    def __init__(self, session, studio):
        self.session, self.studio = session, studio
        self.state = {}
        self.queue = []
        self.lock = threading.Lock()
        self.worker = None

    def ask(self, shoot_id, nums):
        with self.lock:
            self.state[shoot_id] = {"state": "queued", "line": "Saving your picks..."}
            self.queue = [q for q in self.queue if q[0] != shoot_id] + [(shoot_id, nums)]
            if not self.worker or not self.worker.is_alive():
                self.worker = threading.Thread(target=self._run, daemon=True)
                self.worker.start()

    def _run(self):
        while True:
            with self.lock:
                if not self.queue:
                    return
                shoot_id, nums = self.queue.pop(0)
                self.state[shoot_id] = {"state": "running", "line": "Saving your picks and marking them in Lightroom..."}
            spec = f"{shoot_id}=" + ",".join(str(n) for n in nums)
            r = subprocess.run([sys.executable, str(HERE / "peek_sheets.py"), "pick", self.session, spec, "--by", "photographer"],
                               capture_output=True, encoding="utf-8", errors="replace", **quiet())
            ok = r.returncode == 0
            if ok:
                r2 = subprocess.run([sys.executable, str(HERE / "sneak_peeks.py"), "--night", self.session], capture_output=True,
                                    encoding="utf-8", errors="replace", **quiet())
                ok = r2.returncode in (0, 2)
                subprocess.run([sys.executable, str(HERE / "first_look.py"), self.session], capture_output=True, encoding="utf-8",
                               errors="replace", **quiet())
            with self.lock:
                self.state[shoot_id] = ({"state": "done", "line": "Done. These are your sneak peeks now, marked in Lightroom."} if ok
                                        else {"state": "problem", "line": "Something stopped it, and nothing was changed. Tell Claude and it'll sort it out."})
            try:
                rebuild_report(self.session)
            except Exception as ex:
                sys.stderr.write(f"report not rebuilt: {ex}\n")


def named_as_text(want, folders):
    """A PC: is `want`, read the way Windows reads a name (either slash, any capitals, "." and ".." worked out), one
    of `folders` or inside one? Text only: nothing is looked up, so no other computer is asked anything. Windows can't
    climb above \\\\computer\\share with "..", so a match also pins the computer and the share to one of the report's
    own (unproven on a real PC). A folder whose name has no drive letter, or no computer and share, never matches."""
    import ntpath   # how Windows reads a name, on any computer (only ever asked on a PC)

    def whole(drive):   # "E:", or "\\computer\share" with both named (not "\\", "\\?\...", "\\.\...")
        if len(drive) == 2 and drive[1] == ":" and drive[0].isalpha():
            return True
        bits = drive[2:].split("\\") if drive.startswith("\\\\") else []
        return len(bits) == 2 and all(bits) and bits[0] not in ("?", ".")

    try:   # Windows' own normpath (Python 3.12 and later) refuses a name with a stray NUL in it: not a folder of ours
        w = ntpath.normcase(ntpath.normpath(want)).rstrip("\\")
        for a in folders:
            f = ntpath.normcase(ntpath.normpath(str(a))).rstrip("\\")
            if not whole(ntpath.splitdrive(f)[0]):
                continue
            if w == f or w.startswith(f + "\\"):
                return True
    except (TypeError, ValueError):
        pass
    return False


class Handler(SimpleHTTPRequestHandler):
    studio = ""
    allowed = ()
    renames = None
    picks = None
    last_open = {}  # path -> time, so one click never opens two Finder windows

    def ours(self):
        """Was this request sent to this server by its own name (127.0.0.1 or localhost, and this port)? The report
        is always opened that way. A web page on another site pointed at this computer by a trick of names still
        carries its own name in Host, and is refused before anything is looked at (it would otherwise read the
        backup's records: what they said for the client notes, the notes, the index). As the posting server and
        the editing queue's."""
        port = self.server.server_address[1]
        host = (self.headers.get("Host") or "").strip().lower()
        if host in (f"127.0.0.1:{port}", f"localhost:{port}"):
            return True
        self.send_error(HTTPStatus.FORBIDDEN)
        try:
            sys.stderr.write(f"refused: a request for {urlsplit(self.path).path[:60]!r} named another host ({host[:80]!r})\n")
        except Exception:  # noqa: BLE001  (the log is only for reading a miss later; the answer has gone out)
            pass
        return False

    def do_HEAD(self):
        # the report's own "has it been rebuilt?" check asks for report.html this way, every 4 seconds
        if self.ours():
            super().do_HEAD()

    def list_directory(self, path):
        # Never a bare list of the backup's records (Dustin, Nov 5: the pane's play button opened the server's
        # bare address and he got "Directory listing for /" with index.json and manifest.json in it).
        self.send_error(HTTPStatus.NOT_FOUND, "Nothing to show here")
        return None

    def do_GET(self):
        if not self.ours():
            return
        parts = urlsplit(self.path)
        if fresh.page_path(parts.path) and fresh.stale() and fresh.restart(self):
            return
        if parts.path == look.FONT_ROUTE:
            # the report's font: the plugin's own DM Sans (look.py), never a file from the backup's folder
            return look.serve_font(self, parts.query)
        if parts.path in ("", "/"):
            # the bare address is the report
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/report.html")
            self.end_headers()
            return
        if parts.path == "/which":
            body = json.dumps({"studio": self.studio}).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if parts.path == "/rename-status":
            body = json.dumps(self.renames.state if self.renames else {}).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if parts.path == "/picks-status":
            body = json.dumps(self.picks.state if self.picks else {}).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if parts.path == "/peeks-more":
            # the report's "Show me more": the close-look shortlist for one shoot, with previews
            sid = parse_qs(parts.query).get("shoot", [""])[0][:40]
            try:
                import peek_sheets
                c = peek_sheets.candidates(self.picks.session if self.picks else self.directory, sid,
                                           everything=parse_qs(parts.query).get("all", [""])[0] == "1")
            except Exception as ex:  # noqa: BLE001
                c = None
                sys.stderr.write(f"peeks-more: {ex}\n")
            body = json.dumps(c or {"error": "nothing to show for that shoot"}).encode()
            self.send_response(HTTPStatus.OK if c else HTTPStatus.NOT_FOUND)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if parts.path == "/queue-url":
            # the report's "Show my editing queue" link: the queue page's address, starting its server if it is not up
            url = queue_url()
            body = json.dumps({"url": url}).encode()
            self.send_response(HTTPStatus.OK if url else HTTPStatus.SERVICE_UNAVAILABLE)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if parts.path != "/open":
            return super().do_GET()
        want = parse_qs(parts.query).get("path", [""])[0]
        target = Path(want).expanduser()
        # A PC only: a network path ("//computer/share", "\\computer\share", or Windows' own "\??\UNC\computer\share")
        # is refused as text, before resolve() or
        # is_dir() could look it up: asking Windows about one reaches out to that computer first (and offers it the
        # sign-in of whoever is using this one), and any web page can ask this server for one, even if it can't
        # read the answer. Unless, as text, it is one of the report's own folders or inside one: a photo drive on the
        # network, given a letter (Z:) or not, is written as \\computer\share\... in the records once the backup has
        # settled (Windows' own resolve() turns the letter into the computer's address), and its Open photo folder
        # opens as before. A drive letter is looked at as before. A Mac: as before.
        spelled = want.replace("\\", "/")
        network = (this_computer.WINDOWS and (spelled.startswith("//") or spelled.startswith("/??/"))
                   and not named_as_text(want, self.allowed))   # unproven on a real PC
        try:   # a name Windows cannot even look up (a stray ? or *) is simply not a folder this report names
            allowed = not network and any(target.resolve().is_relative_to(Path(a).resolve()) for a in self.allowed)
        except (OSError, ValueError):
            allowed = False
        if network:
            ok, words = False, "That isn't a folder this report names."
        elif not target.is_dir():
            ok, words = False, f"That folder isn't there right now. Is {this_computer.drive_words(target) or 'the drive'} plugged in?"
        elif not allowed:
            ok, words = False, "That isn't a folder this report names."
        else:
            now = time.monotonic()
            # Never opened yet, or more than a second ago. (Apple's own Python counts this clock from the server's
            # start, so a click in its first second was taken for a second click and nothing opened.)
            last = self.last_open.get(str(target))
            if last is None or now - last > 1.0:
                ok, why = show_in_finder(target)  # opens it and brings Finder to the front when macOS allows
                name = target.name or str(target)
                APP = this_computer.FILES_APP   # "Finder" on a Mac, "File Explorer" on a PC
                words = (f"Opened {name} in {APP}, behind this window. Click {APP} in {this_computer.APP_BAR} to see it." if why == "behind"
                         else f"Opened {name} in {APP}.") if ok else f"Couldn't open {APP}. The folder is {target}. ({why})"
            else:
                ok, words = True, f"Opened {target.name or str(target)} in {this_computer.FILES_APP}."
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
        if not self.ours():
            return
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
        if path == "/queue":
            # the report's "Add to my editing queue" button: {"shoot": id, "due": "YYYY-MM-DD"}
            try:
                n = int(self.headers.get("Content-Length", "0"))
                d = json.loads(self.rfile.read(n) or b"{}")
                shoot, due = str(d["shoot"])[:40], str(d["due"])[:10]
                assert shoot and due
            except (ValueError, KeyError, AssertionError, TypeError):
                self.send_error(HTTPStatus.BAD_REQUEST, "expected {shoot, due}")
                return
            try:
                import edit_queue
                q = edit_queue.load()
                entry, new = edit_queue.add_from_night(q, self.directory, shoot, due)
                edit_queue.save(q)
                edit_queue.write_page(q)
                words = f"Added to your queue: {entry['name']}, {edit_queue.due_words(entry['due'])}."
                out = {"ok": True, "due": entry["due"], "words": words}
            except SystemExit as ex:
                self.send_error(HTTPStatus.BAD_REQUEST, str(ex)[:200])
                return
            body = json.dumps(out).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            sys.stderr.write(f"queue: {shoot} due {due}\n")
            return
        if path == "/peeks-again":
            # "Pick again" with a note: remembered for Claude, kept as taste
            try:
                n = int(self.headers.get("Content-Length", "0"))
                d = json.loads(self.rfile.read(n) or b"{}")
                shoot, note = str(d["shoot"])[:40], " ".join(str(d.get("note", "")).split())[:500]
                assert shoot
                import peek_sheets
                peek_sheets.ask_again(self.picks.session if self.picks else self.directory, shoot, note)
            except (ValueError, KeyError, AssertionError, TypeError) as ex:
                self.send_error(HTTPStatus.BAD_REQUEST, str(ex)[:100])
                return
            words = ("Got it. Next time you say anything to me, I'll have another go at these" + (" with that in mind." if note else "."))
            body = json.dumps({"ok": True, "words": words}).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            sys.stderr.write(f"peeks-again: {shoot}: {note}\n")
            return
        if path == "/peeks-choose":
            # "Use these six": {"shoot": id, "nums": [..]} in their order, the first is the hero
            try:
                n = int(self.headers.get("Content-Length", "0"))
                d = json.loads(self.rfile.read(n) or b"{}")
                shoot = str(d["shoot"])[:40]
                nums = [int(x) for x in d["nums"]][:12]
                assert shoot and nums
            except (ValueError, KeyError, AssertionError, TypeError):
                self.send_error(HTTPStatus.BAD_REQUEST, "expected {shoot, nums}")
                return
            self.picks.ask(shoot, nums)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"queued")
            sys.stderr.write(f"peeks-choose: {shoot}: {nums}\n")
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
        (Path(self.directory) / "names.json").write_text(json.dumps(clean, indent=1, ensure_ascii=False), encoding="utf-8")
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
    manifest = json.loads((studio / "manifest.json").read_text(encoding="utf-8"))
    Handler.allowed = tuple(p for p in (manifest.get("source"), manifest.get("dest"), manifest.get("second")) if p)
    Handler.renames = Renames(a.session, studio)
    Handler.picks = Picks(a.session, studio)
    Handler.studio = str(studio)
    # the asked-for port, or the next free one: another session's server may be holding it
    srv = None
    for port in range(a.port, a.port + 20):
        try:
            srv = fresh.Server(("127.0.0.1", port), partial(Handler, directory=str(studio)))  # Python's own on a Mac
            break
        except OSError:
            continue
    if not srv:
        sys.exit(f"STOP: no free port between {a.port} and {a.port + 19}.")
    try:  # where this backup's report can be found, for the home page's "See the report"
        (studio / "report-url.txt").write_text(f"http://127.0.0.1:{port}/report.html\n", encoding="utf-8")
    except OSError:
        pass
    print(f"Report: http://127.0.0.1:{port}/report.html", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
