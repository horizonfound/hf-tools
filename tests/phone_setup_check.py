#!/usr/bin/env python3
"""The "get a tap on your phone" page (Dustin, Nov 11): the picture of where the Remote Control switch is, shown
when a shoot is on more than one card and the Assistant cannot switch it on itself. Checks the page and that the
page server serves it, on a scratch folder (never the real ~/.studio).

    python3 tests/phone_setup_check.py
"""
import importlib
import shutil
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pc_smoke as t  # noqa: E402

SCRIPTS = t.SCRIPTS
FAILED = []


def check(what, ok, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {detail}"), flush=True)
    if not ok:
        FAILED.append(what)


def main():
    work = Path(tempfile.mkdtemp(prefix="phone-check-"))
    try:
        sys.path.insert(0, str(SCRIPTS))
        with t.environ(STUDIO_HOME=str(work / "home")):
            import phone_setup
            page = phone_setup.page_html()
            check("the page has its three steps in plain words", all(x in page for x in ("Open the panel", "Switch Remote Control on", "Check your phone", "say \u201cgo\u201d")))
            check("both pictures are in the page itself, and both files are in the plugin",
                  page.count("data:image/png;base64,") == 2 and all((phone_setup.PICTURES / n).stat().st_size > 2000 for n in ("phone-step-1.png", "phone-step-2.png")))
            check("nothing in the page comes from the internet", "http://" not in page and "https://" not in page)
            check("no tool names or code words a photographer would not know", not any(x in page for x in ("mcp__", "session", "config", "toggle", "CCD")))
            pq = importlib.import_module("posting_queue")
            srv = pq.fresh.Server(("127.0.0.1", 0), pq.Handler)
            port = srv.server_address[1]
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                body = opener.open(f"http://127.0.0.1:{port}/phone-setup", timeout=10).read().decode("utf-8")
                check("the page server serves it", "Get a tap on your phone" in body and body.count("data:image/png") == 2)
            finally:
                srv.shutdown()
                srv.server_close()
        text = (SCRIPTS.parent / "parts" / "backup.md").read_text(encoding="utf-8")
        check("the backup instructions look first, switch it on for them, and keep the picture for when they can't",
              all(x in text for x in ("get_session", "set_remote_control", "phone_setup.py url", "Never for one card")))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
