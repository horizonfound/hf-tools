#!/usr/bin/env python3
"""One report for a shoot on more than one card (shoot_report.py, report_page.py's card mode, serve_report.py's
/card/N/ routes), on two pretend backups (tests/fake_night.py, needs Pillow).

    python3 tests/shoot_report_check.py [--port 8871]

Nothing under ~/.studio is touched (STUDIO_HOME points at a scratch folder); the servers run on 127.0.0.1 only.
The report server is on --port; the editing-queue server the test starts for the queue-url route is on --port + 30
(or the next free one of the 20 after it). Both are the test's own programs and are stopped before it ends.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/the-engine/skills/studio-manager/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))

PASSED, FAILED = 0, []


def check(what, ok, more=""):
    global PASSED
    if ok:
        PASSED += 1
    else:
        FAILED.append(what + (f"  [{more}]" if more else ""))
        print("FAIL:", what, more)


def run(*args, env=None):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run([sys.executable, str(SCRIPTS / args[0]), *args[1:]], capture_output=True, text=True, env=e)
    return r.returncode, r.stdout + r.stderr


def get(url, method="GET", body=None):
    req = urllib.request.Request(url, method=method, data=body)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as ex:
        return ex.code, ex.headers, ex.read()


def first_line(proc, starts):
    """The address a page server prints as it comes up (the second word of its line that starts so), or None if
    the program ended without printing it."""
    for _ in range(100):
        line = proc.stdout.readline()
        if line.startswith(starts):
            return line.split(":", 1)[1].split()[0]
        if not line:
            break
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8871)
    a = ap.parse_args()
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("(no Pillow here: the pretend backups cannot be made; nothing checked)")
        print("0 passed, 0 failed\nALL OK")
        return 0
    import fake_night
    import shoot_report
    with tempfile.TemporaryDirectory(prefix="shoot-report-") as d:
        work = Path(d).resolve()   # a Mac's temp folder is a link (/var -> /private/var); the records are written resolved
        env = {"STUDIO_HOME": str(work / "studio-home")}
        n1, n2 = work / "2026-06-24 Fake wedding", work / "2026-06-24 Fake wedding, card 2"
        for n in (n1, n2):
            fake_night.main(str(n))
            m = json.loads((n / "_studio" / "manifest.json").read_text(encoding="utf-8"))
            m["session"] = n.name
            (n / "_studio" / "manifest.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
        s1, s2 = n1 / "_studio", n2 / "_studio"

        # before the link: a report on its own
        code, out = run("report_page.py", str(n1), env=env)
        page = (s1 / "report.html").read_text(encoding="utf-8")
        check("a backup on its own: its report has the top bar and the footer, no card line", code == 0 and "class='bar'" in page and "class='foot'" in page and "Card 1 of" not in page, out[-200:])
        check("no card page and no shoot page before the link", not (s1 / "report-card.html").exists() and not (s1 / "shoot-report.html").exists())
        check("every route the report asks for is relative (so it works at /card/N/ too)", "fetch('/" not in page and "'/play?" not in page and "'/open-clips?" not in page)
        code, out = run("shoot_report.py", "link", str(n1), env=env)
        check("linking one backup alone is nothing to do (exit 2)", code == 2 and "two or more" in out, out[-200:])
        code, out = run("shoot_report.py", "show", str(n1), env=env)
        check("show on an unlinked backup says so (exit 2)", code == 2 and "Not part of a shoot" in out, out[-200:])

        # the link
        code, out = run("shoot_report.py", "link", str(n1), str(n2), env=env)
        check("two backups link (exit 0), the shoot named from the first card's name", code == 0 and "Fake wedding: 2 cards linked" in out and "card 2: 2026-06-24 Fake wedding, card 2" in out, out[-300:])
        link1 = json.loads((s1 / "shoot.json").read_text(encoding="utf-8"))
        link2 = json.loads((s2 / "shoot.json").read_text(encoding="utf-8"))
        check("shoot.json is in both records, the same, with both cards in order", link1 == link2 and link1["shoot"] == "Fake wedding" and [c["card"] for c in link1["cards"]] == [1, 2]
              and link1["cards"][1]["records"] == str(s2), json.dumps(link1))
        check("card_of says which card each one is", shoot_report.card_of(s1) == {"n": 1, "of": 2, "shoot": "Fake wedding"} and shoot_report.card_of(s2)["n"] == 2)
        for s, n in ((s1, 1), (s2, 2)):
            check(f"card {n}: its report, its card page and the shoot page are written", (s / "report.html").exists() and (s / "report-card.html").exists() and (s / "shoot-report.html").exists())
        card = (s1 / "report-card.html").read_text(encoding="utf-8")
        check("the card page has no top bar and no footer, says Card 1 of 2, and carries the frame fix", "class='bar'" not in card and "class='foot'" not in card and "Card 1 of 2" in card and "window.frameElement" in card)
        check("the card page still has the shoots, the numbers and the folder button", "Open photo folder" in card and "checked byte for byte" in card and "class='stats'" in card)
        plain = (s1 / "report.html").read_text(encoding="utf-8")
        check("the plain report is untouched by the link (bar, footer, no card line, no frame fix)", "class='bar'" in plain and "class='foot'" in plain and "Card 1 of" not in plain and "window.frameElement" not in plain)
        shoot = (s1 / "shoot-report.html").read_text(encoding="utf-8")
        check("the shoot page: the verdict for both cards, the cards added up, a section per card in a frame",
              "on both cards, safely backed up and" in shoot and "<b>2</b><span class='eyebrow'>cards" in shoot and "src='card/1/report-card.html'" in shoot
              and "src='card/2/report-card.html'" in shoot and "Card 2 of 2" in shoot and "The cards are safe to format" in shoot, "")
        check("the shoot page's numbers are both cards' together", f"<b>{2 * 70:,}</b><span class='eyebrow'>files" in shoot, "")
        check("the shoot page is the same in both records", shoot == (s2 / "shoot-report.html").read_text(encoding="utf-8"))
        code, out = run("shoot_report.py", "link", str(n1), str(n2), env=env)
        check("linking again changes nothing (still 2 cards)", code == 0 and "2 cards linked" in out and json.loads((s1 / "shoot.json").read_text(encoding="utf-8")) == link1, out[-200:])
        code, out = run("shoot_report.py", "show", str(n2), env=env)
        check("show prints the link as JSON", code == 0 and '"shoot": "Fake wedding"' in out, out[-200:])

        # the verdict follows the cards
        m2 = json.loads((s2 / "manifest.json").read_text(encoding="utf-8"))
        keep = json.dumps(m2)
        m2["problems"] = ["a pretend copy error on IMG_2003.jpg"]
        (s2 / "manifest.json").write_text(json.dumps(m2), encoding="utf-8")
        run("report_page.py", str(n2), env=env)
        shoot = (s1 / "shoot-report.html").read_text(encoding="utf-8")
        check("a problem on card 2: the shoot page names it on top and does not call the cards safe", "Card 2 needs you before this is" in shoot and "safe to format when" not in shoot and "Not finished" in shoot, "")
        m2 = json.loads(keep); m2["sample"] = {"kept": 70, "of": 3000}
        (s2 / "manifest.json").write_text(json.dumps(m2), encoding="utf-8")
        run("report_page.py", str(n2), env=env)
        shoot = (s1 / "shoot-report.html").read_text(encoding="utf-8")
        import re
        check("a sample on card 2: the shoot page says so, and never that the cards are safe to format",
              "A sample: part of card 2 was copied" in shoot and "safe to format when" not in shoot and "is not safe to format" in shoot and "A sample, not a backup" in shoot, "")
        (s2 / "manifest.json").write_text(keep, encoding="utf-8")
        run("report_page.py", str(n2), env=env)
        check("card 2 whole again: the shoot page calls both cards safe again", "on both cards, safely backed up" in (s1 / "shoot-report.html").read_text(encoding="utf-8"))

        # a card that cannot be found (its drive unplugged)
        hidden = work / "away"
        shutil.move(str(n2), str(hidden))
        data = shoot_report.read(s1)
        check("read: a card whose records are gone is 'found: None', the link kept", data and data["cards"][1]["found"] is None and data["cards"][1]["records"] == str(s2))
        pages = shoot_report.write_pages(s1)
        shoot = (s1 / "shoot-report.html").read_text(encoding="utf-8")
        check("the shoot page says it can't see card 2 right now, and shows card 1", len(pages) == 1 and "I can't see card 2 right" in shoot and "Not found right now" in shoot and "src='card/1/report-card.html'" in shoot, "")
        shutil.move(str(hidden), str(n2))

        # the records move when the night settles: the link heals itself
        place = work / ".studio"
        place.mkdir()
        shutil.move(str(s2), str(place / n2.name))
        data = shoot_report.read(s1)
        healed = json.loads((s1 / "shoot.json").read_text(encoding="utf-8"))
        check("a settled card's records are found again at their new place, and the link is written back", data["cards"][1]["found"] == str(place / n2.name) and healed["cards"][1]["records"] == str(place / n2.name), json.dumps(healed))
        check("card_of still works from the moved records", shoot_report.card_of(place / n2.name) == {"n": 2, "of": 2, "shoot": "Fake wedding"})
        shutil.move(str(place / n2.name), str(s2))
        shoot_report.read(s1)   # heals back

        # the server, started on card 2, serves the shoot's page and every card
        proc = subprocess.Popen([sys.executable, str(SCRIPTS / "serve_report.py"), str(n2), "--port", str(a.port)],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=dict(os.environ, **env))
        # The queue-url route starts an editing-queue server that is meant to outlive its starter when none answers
        # (serve_report.queue_url). Left to do that here, it stayed running after every run of this test: on a Mac
        # a stray program per run, on a PC a program holding logs/queue.log open, so the scratch folder could not
        # be removed and the test ended in an error with every check passed. So the test starts the queue server
        # itself, as its own program it can stop, and the route must find that one and start no second.
        qproc = subprocess.Popen([sys.executable, str(SCRIPTS / "edit_queue.py"), "serve", "--port", str(a.port + 30)],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=dict(os.environ, **env))
        try:
            queue_page = first_line(qproc, "Editing queue:")
            check("the test's own editing-queue server starts", bool(queue_page), "")
            base = first_line(proc, "Report:")
            base = base and base.rsplit("/", 1)[0]
            check("the server starts", bool(base), "")
            if base:
                st, hd, body = get(base + "/report.html")
                check("/report.html on a card's server is the shoot's page", st == 200 and b"on both cards, safely backed up" in body and b"src='card/2/report-card.html'" in body, f"{st} {body[:120]!r}")
                st, hd, body = get(base + "/report.html", method="HEAD")
                check("HEAD /report.html answers with Last-Modified (the page's own refresh check)", st == 200 and hd.get("Last-Modified"), str(st))
                st, hd, body = get(base + "/card/1/report-card.html")
                check("/card/1/report-card.html is card 1's section", st == 200 and b"Card 1 of 2" in body, str(st))
                st, hd, body = get(base + "/card/2/report-card.html")
                check("/card/2/report-card.html is card 2's section", st == 200 and b"Card 2 of 2" in body, str(st))
                st, hd, body = get(base + "/card/2/report.html")
                check("/card/2/report.html is card 2's own full report", st == 200 and b"class='bar'" in body and b"Card 2 of" not in body, str(st))
                pic = next(p for p in sorted((s1 / "groups").glob("*.jpg")))
                st, hd, body = get(base + f"/card/1/groups/{pic.name}")
                check("a picture under a card's prefix comes from that card's records", st == 200 and hd.get("Content-Type", "").startswith("image/") and body == pic.read_bytes(), str(st))
                st, hd, body = get(base + "/card/1/which")
                check("/card/1/which names card 1's records", st == 200 and json.loads(body)["studio"] == str(s1), body[:100])
                st, hd, body = get(base + "/which")
                check("/which still names the backup the server was started for", st == 200 and json.loads(body)["studio"] == str(s2), body[:100])
                st, hd, body = get(base + "/card/9/report.html")
                check("a card that does not exist is 404", st == 404, str(st))
                st, hd, body = get(base + "/card/1/")
                check("a card's bare address goes to that card's own report, never a list of its records", st == 200 and b"index.json" not in body and b"class='bar'" in body and b"Card 1 of" not in body, str(st))
                st, hd, body = get(base + "/")
                check("the bare address goes to the shoot's page", st == 200 and b"on both cards, safely backed up" in body, str(st))
                st, hd, body = get(base + "/card/1/queue-url")
                if queue_page:
                    check("a small route under a card's prefix answers (queue-url), with the queue page already running",
                          st == 200 and json.loads(body).get("url") == queue_page, f"{st} {body[:120]!r}")
                    check("the report server started no second queue server (nothing left running after the test)",
                          not (work / "studio-home" / "logs" / "queue.log").exists())
                else:
                    print("SKIPPED: the queue-url route (the test's own editing-queue server did not start, and asking "
                          "the route without it would leave a queue server running after the test)")
                st, hd, body = get(base + "/card/2/rename", method="POST", body=json.dumps({"shoot": "s1", "name": "Fake beach renamed"}).encode())
                time.sleep(0.3)
                st1, _, b1 = get(base + "/card/1/rename-status")
                st2, _, b2 = get(base + "/card/2/rename-status")
                check("a rename asked on card 2's section goes to card 2's worker, not card 1's", st == 200 and body == b"queued" and "s1" in json.loads(b2) and json.loads(b1) == {}, b1[:80] + b2[:80])
                for _ in range(100):   # let that rename finish (it runs rename_shoot.py in the background) before the server goes
                    time.sleep(0.2)
                    _, _, b2 = get(base + "/card/2/rename-status")
                    if json.loads(b2).get("s1", {}).get("state") in ("done", "problem"):
                        break
        finally:
            for pr in (proc, qproc):
                pr.terminate()
                try:
                    pr.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pr.kill()
                    pr.wait(timeout=10)
                pr.stdout.close()

        # night.py --with links as the card is backed up (the arguments are read; a whole night is pc_smoke's job)
        code, out = run("night.py", "--help", env=env)
        check("night.py has --with", code == 0 and "--with" in out, out[-200:])

    print(f"{PASSED} passed, {len(FAILED)} failed")
    if FAILED:
        for f in FAILED:
            print("  ", f)
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
