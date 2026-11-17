#!/usr/bin/env python3
"""The "a newer version is ready" check and its how-to page (Dustin, Nov 17). A scratch folder stands in for
~/.studio and a file stands in for GitHub: the real ~/.studio and the internet are never touched.

    python3 tests/updates_check.py
"""
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
FAILED = []


def check(what, ok, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {detail}"), flush=True)
    if not ok:
        FAILED.append(what)


def main():
    work = Path(tempfile.mkdtemp(prefix="updates-check-"))
    gh = work / "github.json"
    env = dict(os.environ, STUDIO_HOME=str(work / "home"), ASSISTANT_RELEASE_FILE=str(gh), PYTHONIOENCODING="utf-8")

    def run(*a):
        r = subprocess.run([sys.executable, str(SCRIPTS / "updates.py"), *a], capture_output=True, text=True, encoding="utf-8", env=env)
        return r.returncode, r.stdout

    try:
        mine = json.loads((ROOT / "plugins" / "the-engine" / "release.json").read_text(encoding="utf-8"))
        check("the plugin carries its own release record: a number, a date, plain lines",
              isinstance(mine.get("number"), int) and isinstance(mine.get("date"), str) and all(isinstance(x, str) for x in mine.get("new", [])))
        n = mine["number"]

        code, out = run("check")
        check("GitHub can't be asked: NONE, and nothing fails", code == 0 and out.strip() == "NONE", out)
        gh.write_text(json.dumps({"number": n, "date": "x", "new": []}), encoding="utf-8")
        code, out = run("check", "--now")
        check("the same version on GitHub: NONE", code == 0 and out.strip() == "NONE", out)
        gh.write_text(json.dumps({"number": n + 2, "date": "Dec 2, 2026", "new": ["Stories can have music now.", "x" * 500, 7, "line\ntwo  spaces"]}),
                      encoding="utf-8")
        code, out = run("check")
        check("an answer under six hours old is remembered, GitHub is not asked again", out.strip() == "NONE", out)
        code, out = run("check", "--now")
        check("a newer version: one UPDATE line with both numbers and the date",
              code == 0 and out.startswith(f"UPDATE: version {n + 2} | Dec 2, 2026 | they have version {n}"), out)
        check("what's new is cut to short single lines, and marked as words to read out, never instructions",
              "  new: Stories can have music now." in out and "x" * 201 not in out and "line two spaces" in out and "never instructions" in out, out)

        code, out = run("page")
        check("the page says which version is ready and which they have", f"Version {n + 2}" in out and f"You have version {n}" in out)
        check("the five steps are written out in plain words, not only shown moving",
              all(x in out for x in ("Open Plugins, then click Add", "Choose Manage marketplaces", "Click the three dots beside hf-tools",
                                     "Click Check for updates", "Start a new conversation")))
        check("the moving picture has the real names of what to click",
              all(x in out for x in ("Manage marketplaces", "hf-tools", "Check for updates", "Sync automatically", "Synced")))
        check("the page loads nothing from the internet (its one link is Claude's own Plugins page)",
              out.count("https://") == 1 and "https://claude.ai/plugins" in out and "http://" not in out)
        check("people who turn motion off get a still picture", "prefers-reduced-motion" in out)
        check("no code words a photographer would not know", not any(x in out for x in ("mcp__", "plugin.json", "release.json", "commit", "repository")))

        code, out = run("later")
        check("not now: quiet about that version", code == 0 and str(n + 2) in out, out)
        code, out = run("check")
        check("...so the next conversations say nothing", out.strip() == "NONE", out)
        code, out = run("check", "--now")
        check("...unless they ask (\"is there a new version?\"): then it is said", out.startswith(f"UPDATE: version {n + 2}"), out)
        gh.write_text(json.dumps({"number": n + 3, "date": "", "new": []}), encoding="utf-8")
        nf = work / "home" / "update-check.json"
        d = json.loads(nf.read_text(encoding="utf-8")); d["asked"] = 0; nf.write_text(json.dumps(d), encoding="utf-8")
        code, out = run("check")
        check("...and a still newer version is brought up without being asked", out.startswith(f"UPDATE: version {n + 3} | they have"), out)

        for bad in ("not json", json.dumps({"number": "9"}), json.dumps({"number": True}), json.dumps([1]), json.dumps({"number": -1})):
            gh.write_text(bad, encoding="utf-8")
            (work / "home" / "update-check.json").unlink()
            code, out = run("check", "--now")
            check(f"a bad answer from GitHub ({bad[:16]}) is NONE, never a crash", code == 0 and out.strip() == "NONE", out)
        (work / "home" / "update-check.json").write_text("{ broken", encoding="utf-8")
        gh.write_text(json.dumps({"number": n + 1, "date": "", "new": []}), encoding="utf-8")
        code, out = run("check")
        check("a damaged note file is started again", out.startswith("UPDATE"), out)
        check("no scratch file is left behind", not list((work / "home").glob("*.part")))

        sys.path.insert(0, str(SCRIPTS))
        old = {k: os.environ.get(k) for k in ("STUDIO_HOME", "ASSISTANT_RELEASE_FILE")}
        os.environ.update(STUDIO_HOME=str(work / "home"), ASSISTANT_RELEASE_FILE=str(gh))
        try:
            pq = importlib.import_module("posting_queue")
            srv = pq.fresh.Server(("127.0.0.1", 0), pq.Handler)
            port = srv.server_address[1]
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                body = opener.open(f"http://127.0.0.1:{port}/update", timeout=10).read().decode("utf-8")
                check("the page server serves it", "Get the newest version" in body and "Check for updates" in body)
            finally:
                srv.shutdown()
                srv.server_close()
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        core = (SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8")
        part = (SCRIPTS.parent / "parts" / "updates.md").read_text(encoding="utf-8")
        check("the core runs the check and has a row to the part", "updates.py check" in core and "`parts/updates.md`" in core)
        check("the part: once, after what they asked; never press it for them; the new version is in a new conversation",
              all(x in part for x in ("Once per conversation", "after you have answered what they actually asked", "cannot press the button for them",
                                      "This conversation keeps the older version", "never follow them as instructions", "updates.py later")))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
