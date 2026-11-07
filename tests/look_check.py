#!/usr/bin/env python3
"""The pages' shared look (look.py), checked: the font route refuses everything but its three files, the shared
styles have no serif and nothing from the internet, and the report and the editing queue are built on it.

    python3 tests/look_check.py

Python 3.9, standard library only, a Mac or a PC. In scratch folders it makes itself; the two page servers it
starts (the report's and the editing queue's) are on ports 9830 and up (LOOK_TEST_PORT moves them) and are
stopped at the end.
"""
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
FONTS = ROOT / "plugins" / "the-engine" / "shared" / "fonts"
BASE = int(os.environ.get("LOOK_TEST_PORT", "9830"))
WINDOWS = os.name == "nt"
SERIF = re.compile(r"Fraunces|Cormorant|Georgia|Iowan|Palatino|serif(?!-)|var\(--display\)|--display|googleapis|gstatic", re.I)
results = []


def case(what, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:300]}]" if detail and not ok else ""), flush=True)


class FakeHandler:
    """Just enough of a request handler to see what look.serve_font answers."""
    def __init__(self):
        self.code, self.headers, self.wfile = None, {}, io.BytesIO()

    def send_error(self, code, *a):
        self.code = code

    def send_response(self, code):
        self.code = code

    def send_header(self, k, v):
        self.headers[k] = v

    def end_headers(self):
        pass


def sans_only(css):
    """The CSS with the 'sans-serif' fallback word taken out, so a search for serif finds only a real one."""
    return css.replace("sans-serif", "")


def get(url, host=None):
    req = urllib.request.Request(url, headers={"Host": host} if host else {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, b"", {}


def wait(url):
    for _ in range(100):
        try:
            urllib.request.urlopen(url, timeout=2).read()
            return True
        except Exception:  # noqa: BLE001
            time.sleep(0.2)
    return False


def main():
    work = Path(tempfile.mkdtemp(prefix="look check "))
    studio_home = work / "studio"
    studio_home.mkdir()
    env = dict(os.environ, STUDIO_HOME=str(studio_home), PYTHONIOENCODING="utf-8")
    os.environ["STUDIO_HOME"] = str(studio_home)
    sys.path.insert(0, str(SCRIPTS))
    import look

    # ---- 1. the font route, without a server
    semi = (FONTS / "DMSans-SemiBold.ttf").read_bytes()
    h = FakeHandler()
    look.serve_font(h, "f=DMSans-SemiBold")
    case("serve_font: DMSans-SemiBold comes back byte for byte as a font", h.code == 200 and h.wfile.getvalue() == semi
         and h.headers.get("Content-Type") == "font/ttf" and h.headers.get("Content-Length") == str(len(semi)), h.code)
    for q in ("f=../DMSans-SemiBold", "f=..%2FDMSans-SemiBold", "f=Fraunces-Italic", "f=", "", "f=DMSans-Regular&f=DMSans-Medium",
              "f=DMSans-Regular.ttf", "f=/etc/passwd", "f=DMSans-Regular&x=1", "x=DMSans-Regular", "f=dmsans-regular",
              "f=CormorantGaramond-Italic", "f=DMSans-Regular%00"):
        h = FakeHandler()
        look.serve_font(h, q)
        case("serve_font refuses %r" % q, h.code == 404 and h.wfile.getvalue() == b"", h.code)
    for key, _ in look.FACES:
        h = FakeHandler()
        look.serve_font(h, "f=" + key)
        case("serve_font serves %s" % key, h.code == 200 and h.wfile.getvalue() == (FONTS / (key + ".ttf")).read_bytes())

    # ---- 2. the shared styles
    head = look.head_css()
    case("head_css: no serif, no --display, nothing from the internet", not SERIF.search(sans_only(head)), SERIF.findall(sans_only(head)))
    case("head_css: the only addresses are the pages' own font route",
         re.findall(r"url\('([^']*)'\)", head) == ["/look-font?f=" + k for k, _ in look.FACES])
    case("head_css: the font is the plugin's DM Sans under the pages' own name, first in the font list",
         "font-family:'Assistant Sans'" in head and look.SANS.startswith("'Assistant Sans','DM Sans'") and "--sans:" + look.SANS in head)
    case("head_css: no backslash (it goes into raw strings and pages as it is)", "\\" not in head)
    for name, val in (("cream", "#FAFAF6"), ("ink", "#1F2430"), ("coral-2", "#D4643F"), ("line", "rgba(31,36,48,.12)")):
        case("ROOT has --%s %s (the reel page's)" % (name, val), "--%s:%s;" % (name, val) in look.ROOT)

    # ---- 3. the pages built on it
    import report_page
    import first_look
    import edit_queue
    import reel_page
    for label, css in (("report_page.CSS", report_page.CSS), ("first_look.CSS", first_look.CSS), ("edit_queue.CSS", edit_queue.CSS),
                       ("reel_page.STYLE", reel_page.STYLE), ("reel_page.OUR_CSS", reel_page.OUR_CSS)):
        case(label + ": no serif, no --display, nothing from the internet", not SERIF.search(sans_only(css)), SERIF.findall(sans_only(css)))
        case(label + ": no italic left on a heading or a quiet line (DM Sans has no italic of its own)",
             not re.search(r"font:\s*italic", css), re.findall(r"[^}]*font:\s*italic[^}]*", css)[:2])
    case("report_page and edit_queue no longer name Google Fonts", not hasattr(report_page, "FONTS") and not hasattr(edit_queue, "FONTS"))

    # a small backup's report, written for real
    session = work / "2026-11-07 look test"
    st = session / "_studio"
    st.mkdir(parents=True)
    (st / "manifest.json").write_text(json.dumps({"session": "2026-11-07 look test", "source": str(work / "card"), "dest": str(session),
                                                 "files": {}, "problems": [], "started": "2026-11-07T10:00:00", "finished": "2026-11-07T10:05:00"}),
                                      encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "report_page.py"), str(session)], env=env, capture_output=True, encoding="utf-8")
    page = (st / "report.html").read_text(encoding="utf-8") if (st / "report.html").exists() else ""
    case("the report is written", r.returncode == 0 and page, (r.stdout + r.stderr)[-300:])
    case("the report: no link to the internet, the shared look first in its styles",
         "<link" not in page and not re.search(r"https?://", page) and "<style>" + look.head_css() in page)
    case("the report: no serif anywhere in it", not SERIF.search(sans_only(page)), SERIF.findall(sans_only(page)))
    q = edit_queue.page_html(edit_queue.load())
    case("the editing queue page: no link to the internet, the shared look first, no serif",
         "<link" not in q and "fonts.googleapis" not in q and "<style>" + look.head_css() in q and not SERIF.search(sans_only(q)),
         SERIF.findall(sans_only(q)))

    # ---- 4. the font from the two servers this part of the look puts it on
    procs = []
    try:
        def start(*a):
            kw = {"creationflags": 0x00000200} if WINDOWS else {"start_new_session": True}
            p = subprocess.Popen([sys.executable, *map(str, a)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
            procs.append(p)
        start(SCRIPTS / "serve_report.py", session, "--port", str(BASE))
        start(SCRIPTS / "edit_queue.py", "serve", "--port", str(BASE + 5))
        def port_in(f, fallback):
            # each server writes the address it took (the asked-for port may be taken)
            for _ in range(100):
                try:
                    return f.read_text(encoding="utf-8").strip().split(":")[2].split("/")[0]
                except (OSError, IndexError):
                    time.sleep(0.2)
            return str(fallback)
        rport = port_in(st / "report-url.txt", BASE)
        qport = port_in(studio_home / "queue-url.txt", BASE + 5)
        case("both servers came up", wait(f"http://127.0.0.1:{rport}/report.html") and wait(f"http://127.0.0.1:{qport}/queue.html"))
        for label, port in (("report server", rport), ("editing queue server", qport)):
            code, body, hd = get(f"http://127.0.0.1:{port}/look-font?f=DMSans-SemiBold")
            case(label + ": /look-font gives DMSans-SemiBold byte for byte", code == 200 and body == semi and hd.get("Content-Type") == "font/ttf", code)
            for bad in ("../DMSans-SemiBold", "Fraunces-Italic", ""):
                code, body, _ = get(f"http://127.0.0.1:{port}/look-font?f={bad}")
                case(label + ": /look-font refuses %r" % bad, code == 404 and not body, code)
            code, body, _ = get(f"http://127.0.0.1:{port}/look-font?f=DMSans-Regular", host="example.com")
            case(label + ": a request naming another host gets no font", code == 403 and not body, code)
        code, body, _ = get(f"http://127.0.0.1:{rport}/report.html")
        case("report server: the report it serves asks for no outside address", code == 200 and b"googleapis" not in body and b"/look-font?f=" in body)
        code, body, _ = get(f"http://127.0.0.1:{qport}/queue.html")
        case("editing queue server: its page asks for no outside address", code == 200 and b"googleapis" not in body and b"/look-font?f=" in body)
    finally:
        for p in procs:
            try:
                if WINDOWS:
                    p.terminate()
                else:
                    os.killpg(p.pid, signal.SIGTERM)
            except Exception:  # noqa: BLE001
                pass
        for p in procs:
            try:
                p.wait(5)
            except Exception:  # noqa: BLE001
                p.kill()
        shutil.rmtree(work, ignore_errors=True)

    print(f"\n{sum(results)} of {len(results)} passed.")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
