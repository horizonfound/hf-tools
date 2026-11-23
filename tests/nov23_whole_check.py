#!/usr/bin/env python3
"""Nicole's Nov 23 answers, the four lanes together: one whole pretend backup started from the home page.

    python3 tests/nov23_whole_check.py [--only units,whole,trouble,chat] [--work <a folder to keep>] [--port 9930]
    /usr/bin/lockf -t 5400 <the shared chrome.lock> python3 tests/guard.py 3000 python3 tests/nov23_whole_check.py --chrome
    python3 tests/nov23_whole_check.py --no-chrome      (the same as with no flag: the pages are not opened in a browser)

Each lane was built against a stand-in for the others. This runs them as one, with nothing standing in:
  * whole    a pretend card, a photo drive and a second drive; the Back up a card box's own routes on the page
             server (GET /backup-popup, POST /backup-start); the REAL job (backup_job.py) copying, sorting by time
             with nobody looking and making the second copy; the home card saying each true step; while it runs,
             a second Start, the chat's "backup now", Eject, a rename and a join are each refused in plain words;
             Done with "Name them"; the Name your shoots page for THAT backup (the name the job gives is the name
             the page takes), with no name made up for "Shoot 1" and the name typed before the backup said back;
             one shoot renamed from the page and two joined; the second copy takes the same folders and names
             each time; the report rebuilt, with a first look and no sneak peeks, no client note;
  * trouble  a second copy that cannot be made leaves the backup Done with the reason on the card and the step
             not ticked; a photo that will not read stops the backup with Try again on the card, and Try again
             (POST /backup-again, nothing sent by the page) carries on under the same name;
  * chat     "backup now" the chat's way (night.py, no --by-time) still stops for the look (exit 4) and for the
             six first-look photos (exit 7) and finishes, onto the folder the box saved;
  * units    the one rule that says a backup is still being made (backup_lock.working_on).
With --chrome the home card and the Name your shoots page are also pressed in a hidden Chrome.

Everything is pretend: a scratch STUDIO_HOME, drives and a card that are temp folders named in
STUDIO_DRIVES_FOR_TESTS, no window on the screen, nothing of the real ~/.studio, no /Volumes.
Every line says ok, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only.
"""
import argparse
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
_SCRATCH = tempfile.mkdtemp(prefix="nov23-never-used-home-")
os.environ["STUDIO_HOME"] = _SCRATCH            # nothing here may ever look at the real ~/.studio
os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
for _k in ("STUDIO_DRIVES_FOR_TESTS", "STUDIO_BACKUP_JOB_FOR_TESTS", "STUDIO_PICK_FOLDER_FOR_TESTS"):
    os.environ.pop(_k, None)
import pc_smoke as t  # noqa: E402
import this_computer  # noqa: E402  (pc_smoke put the scripts folder on the path)
import backup_job_check as bj  # noqa: E402  (its pretend card with dated photos)

SCRIPTS = t.SCRIPTS
FAILED, SKIPPED = [], []
GB = 1024 ** 3
JSON_H = {"Content-Type": "application/json"}
D4 = datetime(2026, 6, 4)
# three shoots by time: a morning with a 40 minute break, an afternoon five quiet hours later, a late one past midnight
THREE = [(D4.replace(hour=9), 4), (D4.replace(hour=9, minute=45), 3), (D4.replace(hour=15), 4),
         (D4.replace(hour=23, minute=50), 2), (D4 + timedelta(days=1, minutes=10), 2)]


def check(what, ok, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {str(detail)[-1500:]}"), flush=True)
    if not ok:
        FAILED.append(what)
    return bool(ok)


def skip(what, why):
    SKIPPED.append(what)
    print(f"  SKIP  {what}   [{why}]", flush=True)


class World:
    """A pretend computer: a card, a photo drive, a second drive, its own Studio home, and the page server."""

    def __init__(self, work, name, port):
        self.base = work / name
        self.home = self.base / "home"
        self.mac = self.base / "mac"
        self.vol = self.base / "vol"
        self.gpapa, self.lacie = self.vol / "G PAPA", self.vol / "LaCie"
        self.dest = self.gpapa / "CLIENT WORK"
        self.listing = self.base / "drives.json"
        self.port0, self.port, self.proc, self.cards = port, None, None, []
        self.home.mkdir(parents=True)
        (self.mac / "Pictures").mkdir(parents=True)
        self.dest.mkdir(parents=True)
        self.lacie.mkdir(parents=True)
        self.env = {"STUDIO_HOME": str(self.home), "STUDIO_DRIVES_FOR_TESTS": str(self.listing), "STUDIO_FOLDERS_FOR_TESTS": str(self.mac),
                    "STUDIO_NO_WINDOWS_FOR_TESTS": "1", "STUDIO_SAMPLES_FOR_TESTS": "none", "PYTHONIOENCODING": "utf-8",
                    "PEEK_FACES_PRETEND": str(self.base / "no-faces.json"), "ASSISTANT_CARD_ANSWER_SECONDS": "20"}
        self.drives()

    def card(self, name, bursts, first_number=4471):
        c = self.vol / name
        bj.card_at(c, bursts, first_number=first_number)
        return c

    def drives(self, card=None):
        rows = [{"path": str(self.mac), "name": "Macintosh HD", "total": 500 * GB, "free": 200 * GB, "system": True}]
        if card is not None:
            rows.append({"path": str(card), "name": card.name, "total": 64 * GB, "free": 10 * GB, "removable": True})
        rows.append({"path": str(self.gpapa), "name": "G PAPA", "total": 4000 * GB, "free": 1200 * GB, "removable": False})
        rows.append({"path": str(self.lacie), "name": "LaCie", "total": 2000 * GB, "free": 840 * GB, "removable": False})
        self.listing.write_text(json.dumps(rows), encoding="utf-8")

    def start(self, **env):
        f = self.home / "posting-url.txt"
        if f.exists():
            f.unlink()
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.port0)],
                                     env=t.child_env(dict(self.env, **env)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     start_new_session=(os.name != "nt"))
        wait_for(lambda: f.exists() and f.read_text(encoding="utf-8").strip(), 40, "the page server's address")
        self.port = int(re.search(r":(\d+)/", f.read_text(encoding="utf-8")).group(1))
        wait_for(lambda: self.http("GET", "/home")[0] == 200, 40, "the home page")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def http(self, method, path, raw=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        try:
            c.request(method, path, body=raw, headers=dict(headers or {}))
            r = c.getresponse()
            return r.status, r.read()
        finally:
            c.close()

    def get(self, path):
        code, raw = self.http("GET", path)
        try:
            return code, json.loads(raw.decode("utf-8"))
        except ValueError:
            return code, None

    def post(self, path, obj):
        code, raw = self.http("POST", path, raw=json.dumps(obj).encode("utf-8"), headers=JSON_H)
        try:
            return code, json.loads(raw.decode("utf-8"))
        except ValueError:
            return code, None

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def record(self):
        try:
            return json.loads((self.home / "backup-job.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def drive_no(self, name):
        code, d = self.get("/backup-popup")
        return next(x["d"] for x in d["drives"] if x["name"] == name)

    def watch(self, seconds=240, during=None):
        """Poll /backup-job as the home card does until the job is no longer running. Returns (every head seen, in
        order, each once; the last view). `during(view)` is called on every look while it runs."""
        heads, v, end = [], {}, time.time() + seconds
        while time.time() < end:
            code, v = self.get("/backup-job")
            v = v or {}
            if v.get("head") and (not heads or heads[-1] != v["head"]):
                heads.append(v["head"])
            if v.get("state") != "running":
                return heads, v
            if during:
                during(v)
            time.sleep(0.15)
        return heads, v


def wait_for(fn, seconds, what):
    end = time.time() + seconds
    while time.time() < end:
        try:
            got = fn()
        except (OSError, ValueError, ConnectionError):
            got = None
        if got:
            return got
        time.sleep(0.1)
    raise RuntimeError("waited %d s for %s" % (seconds, what))


def shoots_tree(root, hidden=(".studio", "_studio", ".studio-second")):
    """Every file under a drive's backup place by its path and size, the hidden records left out."""
    out = {}
    root = Path(root)
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(h in p.relative_to(root).parts for h in hidden) and p.name != ".DS_Store":
            out[p.relative_to(root).as_posix()] = p.stat().st_size
    return out


def no_path(w, obj):
    s = json.dumps(obj, ensure_ascii=False)
    return str(w.base) not in s and "/private/" not in s and "/var/folders" not in s


# ---------------------------------------------------------------- units
def unit_checks(work):
    print("A backup that is still being made (backup_lock.working_on): what a rename or a join asks first")
    base = work / "units"
    home = base / "home"
    home.mkdir(parents=True)
    env = {"STUDIO_HOME": str(home)}
    unsettled = base / "drive" / "2026-11-23 monday card" / "_studio"
    other = base / "drive" / "2026-11-20 friday card" / "_studio"
    settled = base / "drive" / ".studio" / "2026-11-23 monday card"
    for p in (unsettled, other, settled):
        p.mkdir(parents=True)
    (settled / "settled.json").write_text("{}", encoding="utf-8")

    def asks(studio):
        code = ("import sys; sys.path.insert(0, %r); import backup_lock; print(backup_lock.working_on(%r))" % (str(SCRIPTS), str(studio)))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, encoding="utf-8", env=t.child_env(env))
        return r.stdout.strip()
    check("no backup running: nothing is being made", asks(unsettled) == "False")
    holder = ("import sys, time; sys.path.insert(0, %r); import backup_lock; "
              "print('HELD' if backup_lock.take(%r, 'monday card') else 'NOT', flush=True); time.sleep(600)" % (str(SCRIPTS), str(base / "card")))
    p = subprocess.Popen([sys.executable, "-c", holder], stdout=subprocess.PIPE, env=t.child_env(env), encoding="utf-8")
    try:
        check("(a backup called monday card is running)", p.stdout.readline().strip() == "HELD")
        check("its own folders, not put away yet: still being made", asks(unsettled) == "True")
        check("a backup that has settled is finished with its folders: a rename there may go ahead", asks(settled) == "False")
        check("an older backup with another name is not the one being made", asks(other) == "False")
    finally:
        p.kill()
        p.wait()
    time.sleep(0.2)
    check("the backup ends: nothing is being made any more", asks(unsettled) == "False")
    import backup_lock
    check("the line is plain and says to try again", "still being made" in backup_lock.BEING_MADE and "Try this again" in backup_lock.BEING_MADE)


# ---------------------------------------------------------------- the whole walk
def whole_checks(work, port, chrome=False):
    print("One whole backup started from the home page: the box, the job, by time, a second copy, naming, joining")
    ok, how = t.pictures.ready()
    if not ok:
        skip("the whole walk", how)
        return None
    w = World(work, "whole", port)
    card = w.card("EOS_DIGITAL", THREE)
    before = t.card_snapshot(card)
    w.drives(card)
    # slow enough to be seen step by step: a pause per file while copying, and per file of the second copy
    w.start(STUDIO_BACKUP_PAUSE_FOR_TESTS="0.25", STUDIO_SECOND_COPY_PAUSE_FOR_TESTS="0.6")
    try:
        code, d = w.get("/backup-popup")
        check("the box is told the card that is in, the two drives by name, and that nothing is saved yet (never a path)",
              code == 200 and d["card"]["name"] == "EOS_DIGITAL" and d["card"]["files"] >= 15 and [x["name"] for x in d["drives"]] == ["G PAPA", "LaCie"]
              and d["first"] is True and d["job"]["state"] == "idle" and no_path(w, d), str(d)[:600])
        body = {"source": "card", "card": "EOS_DIGITAL", "dest": {"d": w.drive_no("G PAPA"), "name": "G PAPA", "path": ["CLIENT WORK"]},
                "second": {"d": w.drive_no("LaCie"), "name": "LaCie"}, "shoot_name": "Aurora"}
        code, d = w.post("/backup-start", body)
        check("Start the backup: the REAL job starts (no stand-in), and the answer is words and names only",
              code == 200 and d.get("ok") is True and d["job"]["state"] == "running" and d.get("second") == "LaCie" and no_path(w, d), str(d)[:600])
        sf = json.loads((w.home / "studio.json").read_text(encoding="utf-8"))
        check("where backups go is saved as exactly the folder picked; the second drive is not saved (asked each time)",
              Path(sf["drives"]["session"]).resolve() == w.dest.resolve() and not sf["drives"].get("second"), str(sf.get("drives")))
        code, again = w.post("/backup-start", body)
        check("Start pressed again while it runs: nothing more is started, and the box shows how it is going",
              again.get("ok") is False and again.get("running") is True, str(again)[:300])
        code, out = t.run("night.py", "--source", card, env=w.env)
        check("\"backup now\" in the chat while the page's backup runs: 'A backup is already running.' (exit 2)", code == 2 and "A backup is already running." in out, out[-300:])
        code, out = t.run("backup_job.py", "status", "--words", env=w.env)
        check("the chat can say how the page's backup is going (backup_job.py status --words)", code == 0 and "started from the home page is running" in out, out[-300:])
        if this_computer.WINDOWS:
            skip("Eject while the backup runs", "eject is a Mac's")
        else:
            code, out = t.run("eject_card.py", card, env=w.env)
            check("Eject my card while the backup runs from it: refused, 'A backup is still running from this card.'",
                  code == 2 and "A backup is still running from this card." in out, out[-300:])

        seen = {"second": None, "sorting_refused": None}

        def during(v):
            rec = w.record()
            records = rec.get("records") or ((rec.get("private") or {}).get("session") and str(Path(rec["private"]["session"]) / "_studio"))
            if v.get("step") == "sorting" and seen["sorting_refused"] is None and records and (Path(records) / "shoots.json").exists() \
                    and (Path(records) / "sort-log.json").exists():
                code, out = t.run("rename_shoot.py", records, "--shoot", "s1", "--name", "Too early", env=w.env)
                seen["sorting_refused"] = (code, out)
            if v.get("step") == "second" and seen["second"] is None and rec.get("records"):
                rn = t.run("rename_shoot.py", rec["records"], "--shoot", "s1", "--name", "Too early", env=w.env)
                jn = t.run("join_shoots.py", rec["records"], "--shoots", "s2", "s3", env=w.env)
                ej = t.run("eject_card.py", card, env=w.env) if not this_computer.WINDOWS else None
                home = w.http("GET", "/home")[1].decode("utf-8", "replace")
                seen["second"] = {"rename": rn, "join": jn, "eject": ej, "tree": shoots_tree(w.dest), "view": v, "home": home}
        heads, v = w.watch(during=during)
        check("the home card said each true step, in order: Copying and checking (n of N), Sorting into shoots, Making your second copy, Done",
              v.get("state") == "done" and any(re.match(r"Copying and checking \(\d+ of \d+\)$", h) for h in heads) and "Sorting into shoots" in heads
              and any(h.startswith("Making your second copy") for h in heads) and heads[-1] == "Done. Every photo checked."
              and heads.index("Sorting into shoots") < next(i for i, h in enumerate(heads) if h.startswith("Making your second copy")), f"{heads} {v}")
        check("... with the second copy's own count while it was being made", any(re.match(r"Making your second copy \(\d+ of \d+\)$", h) for h in heads), str(heads))
        s = seen["second"]
        if s is None:
            check("(the second-copy step was seen while it ran)", False, str(heads))
        else:
            busy = ("This backup is still being made.", "second copy of this backup is being made right now")
            check("a rename while the page's job is making the second copy: refused in plain words (exit 2), nothing moved",
                  s["rename"][0] == 2 and any(b in s["rename"][1] for b in busy) and "Traceback" not in s["rename"][1], s["rename"][1][-400:])
            check("a join then: refused the same way, nothing moved",
                  s["join"][0] == 2 and any(b in s["join"][1] for b in busy) and "Traceback" not in s["join"][1], s["join"][1][-400:])
            if s["eject"] is not None:
                check("Eject while the second copy is being made: still refused", s["eject"][0] == 2, s["eject"][1][-300:])
            check("... the home page, loaded then, drew the same step on the card (a reload keeps it)",
                  "Making your second copy" in s["home"] and "class='bar2'" in s["home"], s["home"][-0:200])
        if seen["sorting_refused"] is not None:
            code, out = seen["sorting_refused"]
            check("a rename while the backup is still sorting and putting its shoots away: refused, 'This backup is still being made.'",
                  code == 2 and "This backup is still being made." in out, out[-400:])
        else:
            skip("a rename while the backup is still sorting", "the sorting step was over before it could be tried (unit checks hold the rule)")

        rec = w.record()
        records = Path(rec["records"])
        check("the job's own record: done, every file, three shoots, the second copy made, and what was asked kept for the server only",
              rec.get("state") == "done" and rec.get("done") == rec.get("total") and rec["total"] >= 15 and rec.get("shoots") == 3
              and rec.get("second") == "LaCie" and rec.get("second_ok") is True and (rec.get("private") or {}).get("is_card") is True, str(rec)[:800])
        check("the name the job gives the backup is its records folder's name, settled beside the shoots",
              rec.get("backup") == records.name and records.parent == w.dest / ".studio" and (records / "settled.json").exists(), f"{rec.get('backup')} {records}")
        check("Done on the card: checked, 'We found 3 shoots on your card', Name them, every step ticked, the card safe to format, never a path",
              v["head"] == "Done. Every photo checked." and v["checked"] is True and v["sub"] == "We found 3 shoots on your card"
              and v["link"] == {"kind": "name", "words": "Name them"} and all(x["dn"] for x in v["steps"]) and len(v["steps"]) == 4
              and v["safe_format"] is True and v["from_folder"] is False and v["backup"] == rec["backup"] and not v.get("second_bad") and no_path(w, v), str(v))
        check("the memory card is byte for byte what it was", t.card_snapshot(card) == before)
        sh = json.loads((records / "shoots.json").read_text(encoding="utf-8"))
        names = [x["suggested"] for x in sh["shoots"]]
        check("split by time with nobody looking: three shoots (the 40 minute break and midnight are not splits), placeholder names",
              sh.get("decided_by") == "the backup, by time" and names == ["Shoot 1", "Shoot 2", "Shoot 3"] and all(x.get("placeholder") for x in sh["shoots"]), str(names))
        told = json.loads((records / "told.json").read_text(encoding="utf-8")).get("text", "") if (records / "told.json").exists() else ""
        check("the name typed in the box was not put on a shoot by guessing: it is kept for the naming", "Shoot name typed before the backup: Aurora" in told, told)
        main_tree = shoots_tree(w.dest)
        folders = sorted({k.split("/")[0] for k in main_tree})
        check("the photo drive: three shoot folders named name_date, photos named for the shoot with the camera's name inside",
              folders == ["Shoot 1_06-04-26", "Shoot 2_06-04-26", "Shoot 3_06-04-26"] and "Shoot 1_06-04-26/Shoot_0001_IMG_4471.JPG" in main_tree
              and len(main_tree) == 15, str(sorted(main_tree))[:600])
        second_tree = shoots_tree(w.lacie)
        check("the second copy looks just like the main drive: the same folders, the same photo names, the same sizes", second_tree == main_tree,
              f"{sorted(set(second_tree) ^ set(main_tree))[:8]}")
        m = json.loads((records / "manifest.json").read_text(encoding="utf-8"))
        check("... every file's second copy checked, and the records say it is laid out like the photo drive",
              m.get("second_layout") == "main" and all((f.get("second") or {}).get("ok") for f in m["files"].values()), str(m.get("second_layout")))
        check("no 'sneak peek' keyword file anywhere on either drive, and the six first-look photos were chosen by the script",
              not [p for p in list(w.dest.rglob("*.xmp")) + list(w.lacie.rglob("*.xmp"))]
              and json.loads((records / "sneak-peeks.json").read_text(encoding="utf-8")).get("picked_by") == "the backup, by time")
        q = json.loads((w.home / "queue.json").read_text(encoding="utf-8")) if (w.home / "queue.json").exists() else {"shoots": []}
        check("the three shoots are in Your backups, none in the editing queue",
              len([x for x in q.get("shoots", []) if x.get("status") == "waiting"]) == 0 and len(q.get("shoots", [])) == 3, str([(x.get("name"), x.get("status")) for x in q.get("shoots", [])]))
        home = w.http("GET", "/home")[1].decode("utf-8", "replace")
        check("the home page after a reload: Done on the card with Name them as a button", "Done. Every photo checked." in home and "data-bk='name'>Name them</button>" in home)

        # ---- the Done card's Name them link opens lane C's page for THIS backup
        name_q = "?backup=" + __import__("urllib.parse").parse.quote(v["backup"])
        code, raw = w.http("GET", "/name-shoots.html" + name_q)
        check("Name them: /name-shoots.html?backup=<the job's backup> is there (200), by the very name the card sends", code == 200 and b"Name your" in raw, str(code))
        code, d = w.get("/name-shoots-data" + name_q)
        check("the page has the three shoots of that backup, and the safe line names both drives",
              code == 200 and d.get("ok") and d["backup"] == v["backup"] and [x["id"] for x in d["shoots"]] == ["s1", "s2", "s3"]
              and "G PAPA" in d["safe_line"] and "LaCie" in d["safe_line"] and "safe to format" in d["safe_line"] and no_path(w, d), str(d)[:900])
        check("no box is filled in with a stand-in: 'Shoot 1' is only the folder's name under an empty box",
              [x["named"] for x in d["shoots"]] == ["", "", ""] and [x["folder"] for x in d["shoots"]] == ["Shoot 1_06-04-26", "Shoot 2_06-04-26", "Shoot 3_06-04-26"], str(d["shoots"]))
        check("the name typed before the backup arrives on the page, to be put on the shoot it belongs to", d.get("typed") == "Aurora" and d.get("from_folder") is False, str(d.get("typed")))
        code, raw = w.http("GET", "/name-shoots.html?backup=no%20such%20backup")
        check("a backup the Assistant does not know is a plain 404, so the card's link falls back to the report", code == 404, str(code))

        if chrome:
            chrome_checks(w, v, d)

        # ---- one shoot named from the page: the second copy follows
        code, sv = w.post("/name-shoots-save", {"backup": v["backup"], "names": {"s1": "Aurora"}, "mini": False, "mini_name": ""})
        check("Save the names with one name typed: the job is started", code == 200 and sv.get("ok"), str(sv)[:400])

        def saved():
            c, dd = w.get("/name-shoots-data" + name_q)
            return dd if dd and (dd.get("job") or {}).get("state") not in ("working", "starting") else None
        d = wait_for(saved, 120, "the names being saved")
        main_tree = shoots_tree(w.dest)
        check("the shoot is renamed on the photo drive: Aurora_06-04-26, photos Aurora_0001_IMG_4471.JPG; the others as they were",
              "Aurora_06-04-26/Aurora_0001_IMG_4471.JPG" in main_tree and not any(k.startswith("Shoot 1_") for k in main_tree)
              and sorted({k.split("/")[0] for k in main_tree}) == ["Aurora_06-04-26", "Shoot 2_06-04-26", "Shoot 3_06-04-26"] and len(main_tree) == 15,
              f"{(d.get('job') or {})} {sorted(main_tree)[:6]}")
        check("... and the second copy took the same new folder and names by itself (second_copy.follow was really called)",
              shoots_tree(w.lacie) == main_tree, f"{sorted(set(shoots_tree(w.lacie)) ^ set(main_tree))[:8]}")
        check("... the page now shows the name they gave, and the typed-before line is gone", d["shoots"][0]["named"] == "Aurora" and not d.get("typed"), str(d["shoots"][0]))
        flog = json.loads((records / "second-follow-log.json").read_text(encoding="utf-8")) if (records / "second-follow-log.json").exists() else None
        check("... logged in the backup's records before it happened (second-follow-log.json)", bool(flog), "no follow log")

        # ---- two shoots joined (the chat's command): the second copy follows again
        code, out = t.run("join_shoots.py", str(records), "--shoots", "s2", "s3", "--name", "Evening", env=w.env)
        main_tree = shoots_tree(w.dest)
        check("two shoots joined into one folder, photos numbered on in shooting order",
              code == 0 and sorted({k.split("/")[0] for k in main_tree}) == ["Aurora_06-04-26", "Evening_06-04-26"] and len(main_tree) == 15
              and len([k for k in main_tree if k.startswith("Evening_06-04-26/Evening_")]) == 8, out[-500:])
        check("... and the second copy has the joined folder and names too", shoots_tree(w.lacie) == main_tree, f"{sorted(set(shoots_tree(w.lacie)) ^ set(main_tree))[:8]}")
        code, out = t.run("second_copy.py", "follow", str(records), "--json", env=w.env)
        check("... run again, the follow has nothing to do and changes nothing", code == 0 and shoots_tree(w.lacie) == main_tree and '"moved": 0' in out.replace(" ", "").replace('"moved":0', '"moved": 0'), out[-300:])
        check("the memory card is still byte for byte what it was", t.card_snapshot(card) == before)
        report = (records / "report.html").read_text(encoding="utf-8")
        check("the report was rebuilt with the names: Aurora and Evening, a first look, the second copy made",
              "Aurora" in report and "Evening" in report and "first look" in report.lower() and "LaCie" in report)
        seen_words = re.sub(r"<script\b.*?</script>", " ", report, flags=re.S).lower()     # what a photographer can read
        check("... and nothing on it says sneak peek or offers a note to a client",
              "sneak peek" not in seen_words and "note to my client" not in seen_words and "note to your client" not in seen_words)
        code, d = w.get("/name-shoots-data" + name_q)
        check("Name your shoots after the join: two shoots, still found by the same name", code == 200 and len(d["shoots"]) == 2, str(d)[:300])
        code, out = t.run("backup_lock.py", env=w.env)
        check("nothing is left locked", code == 0, out)
        if not this_computer.WINDOWS:
            code, out = t.run("eject_card.py", card, env=w.env)
            check("Eject after everything is done is no longer refused for a running backup", "A backup is still running" not in out, out[-300:])
        return w
    except Exception:
        w.stop()
        raise


def chrome_checks(w, view, data):
    print("  (the same, pressed in a hidden Chrome)")
    import chrome_drive
    try:
        with chrome_drive.Chrome(work=str(w.base / "chrome"), size=(1280, 900)) as c:
            c.open(w.url("/home"))
            c.wait_for("document.querySelector('#n1 button[data-bk=\"name\"]')", 20)
            text = c.js("document.querySelector('#n1').innerText")
            check("in the browser: the home card says Done. Every photo checked. · Name them", "Done. Every photo checked." in text and "Name them" in text, text)
            c.js("document.querySelector('#n1 button[data-bk=\"name\"]').click()")
            c.wait_for("location.pathname === '/name-shoots.html' && document.querySelectorAll('.nshoot').length === 3", 30)
            got = c.js("JSON.stringify({q: new URLSearchParams(location.search).get('backup'), boxes: [...document.querySelectorAll('.nshoot input')].map(i => i.value),"
                       " pv: [...document.querySelectorAll('.nshoot .pv')].map(e => e.textContent), typed: (document.getElementById('typed') || {}).textContent || '',"
                       " sub: document.getElementById('sub').textContent})")
            got = json.loads(got)
            check("in the browser: Name them lands on Name your shoots for that backup", got["q"] == view["backup"], str(got))
            check("... three empty boxes, each with its real folder under it, and the typed name said back",
                  got["boxes"] == ["", "", ""] and got["pv"] == ["Folder: Shoot 1_06-04-26", "Folder: Shoot 2_06-04-26", "Folder: Shoot 3_06-04-26"]
                  and "Aurora" in got["typed"] and "We found 3 shoots on your card" in got["sub"], str(got))
            c.js("document.getElementById('mini').click()")
            c.wait_for("document.getElementById('name-mini')", 10)
            check("... ticking mini sessions offers the typed name as the one folder's name", c.js("document.getElementById('name-mini').value") == "Aurora")
            c.js("document.getElementById('mini').click()")
    except chrome_drive.NoChrome as e:
        skip("the pages in a hidden Chrome", str(e))


# ---------------------------------------------------------------- trouble, on the same computer
def trouble_checks(w):
    print("Trouble on the page route: a second copy that cannot be made, and a backup that stops, then Try again")
    if w is None:
        skip("trouble", "the whole walk did not run")
        return
    w.stop()
    card = w.card("CARD B", [(D4.replace(month=8, hour=9), 4), (D4.replace(month=8, hour=16), 3)], first_number=8001)
    w.drives(card)
    w.start()
    try:
        # the second drive already holds a folder with the name the first shoot will get, and it is not the copy's
        (w.lacie / "Shoot 1_08-04-26").mkdir()
        (w.lacie / "Shoot 1_08-04-26" / "theirs.txt").write_text("their own file", encoding="utf-8")
        code, d = w.get("/backup-popup")
        check("the box opens filled in with where backups went last time, and still asks about the second copy (nothing remembered)",
              d["first"] is False and d["saved"]["drive"] == "G PAPA" and d["saved"]["folders"] == ["CLIENT WORK"] and d["saved"]["here"] is True, str(d.get("saved")))
        body = {"source": "card", "card": "CARD B", "dest": {"saved": True}, "second": {"d": w.drive_no("LaCie"), "name": "LaCie"}, "shoot_name": ""}
        bad = None
        if this_computer.WINDOWS or os.geteuid() == 0:
            skip("a photo that will not read, then Try again", "needs a file this user cannot read")
        else:
            bad = sorted((card / "DCIM" / "100CANON").glob("*.JPG"))[2]
            bad.chmod(0)
        try:
            code, d = w.post("/backup-start", body)
            check("(the second backup starts)", code == 200 and d.get("ok") is True, str(d)[:300])
            heads, v = w.watch()
            if bad is not None:
                rec = w.record()
                check("a photo that will not read: the backup stops, the card says so in plain words with Try again and no path",
                      v.get("state") == "problem" and v.get("bad") is True and v.get("again") == "Try again" and "Start the backup again" not in json.dumps(v)
                      and v["head"] and no_path(w, v), str(v))
                home = w.http("GET", "/home")[1].decode("utf-8", "replace")
                check("... on a reload of the home page too, as a button", "data-bk='again'>Try again</button>" in home)
                name_before = rec.get("backup") or (rec.get("private") or {}).get("name")
                code, d = w.post("/backup-again", {})
                check("Try again with the photo still unreadable: it runs again and stops again, nothing made up", code == 200 and d.get("ok") is True, str(d)[:300])
                heads, v = w.watch()
                check("... still a problem, still Try again", v.get("state") == "problem" and v.get("again") == "Try again", str(v)[:400])
        finally:
            if bad is not None:
                bad.chmod(0o644)
        if bad is not None:
            code, d = w.post("/backup-again", {})
            check("the photo can be read again, Try again: the same backup is started again (the page sent nothing)", code == 200 and d.get("ok") is True and d["job"]["state"] == "running", str(d)[:300])
            heads, v = w.watch()
            rec = w.record()
            check("... and it finishes under the same name (one backup, not two), every photo once",
                  v.get("state") == "done" and name_before and (rec.get("private") or {}).get("name") in str(name_before) + str(rec.get("backup"))
                  and len([p for p in (w.dest / ".studio").iterdir() if "card" in p.name.lower()]) == 2
                  and len([k for k in shoots_tree(w.dest) if "_08-04-26/" in k]) == 7, f"{name_before} {rec.get('backup')} {[p.name for p in (w.dest / '.studio').iterdir()]}")
        rec = w.record()
        steps = {x["t"]: x for x in v.get("steps", [])}
        check("the second copy could not be made (a folder of theirs has that name): the backup is still Done and checked",
              v.get("state") == "done" and v["head"] == "Done. Every photo checked." and rec.get("second_ok") is False, str(v)[:600])
        check("... the card says so: the second step is not ticked, and the reason is there in plain words, no path",
              v.get("second_bad") is True and "Second copy not made" in steps and steps["Second copy not made"]["dn"] is False
              and "second copy isn't made yet" in v.get("note", "") and "Shoot 1_08-04-26" in v.get("note", "") and no_path(w, v), str(v)[:900])
        check("... their own folder on the second drive was not touched, and nothing was copied into it",
              sorted(p.name for p in (w.lacie / "Shoot 1_08-04-26").iterdir()) == ["theirs.txt"])
        code, out = t.run("backup_job.py", "status", "--words", env=w.env)
        check("... and the chat is told the same (status --words)", "Second copy on LaCie: not finished." in out, out[-400:])
    finally:
        w.stop()


# ---------------------------------------------------------------- the chat route
def chat_checks(w):
    print("\"backup now\" the chat's way still works start to finish (night.py without --by-time)")
    if w is None:
        skip("the chat route", "the whole walk did not run")
        return
    card = w.card("CARD C", [(D4.replace(month=9, hour=9), 4), (D4.replace(month=9, hour=11), 4)], first_number=9001)
    w.drives(card)
    before = t.card_snapshot(card)
    night = ["night.py", "--source", card, "--name", "chat card", "--date", "2026-09-05"]
    env = {k: v for k, v in w.env.items() if k != "PEEK_FACES_PRETEND"}      # the close look's own face check, as a photographer's Mac runs it
    code, out = t.run(*night, env=env)
    session = w.dest / "2026-09-05 chat card"
    st = session / "_studio"
    check("it copies onto the folder the box saved, checks, and stops for the look (exit 4): it does not sort by time by itself",
          code == 4 and (st / "groups.json").exists() and not (st / "shoots.json").exists(), out[-500:])
    if code != 4:
        return
    groups = json.loads((st / "groups.json").read_text(encoding="utf-8"))["groups"]
    shoots = [{"id": f"s{i}", "suggested": f"Chat shoot {i}", "groups": [g["id"]], "photos": g.get("count", 0), "recap": "Test frames.", "why": "test"}
              for i, g in enumerate(groups, 1)]
    (st / "shoots.json").write_text(json.dumps({"decided_by": "test", "shoots": shoots}), encoding="utf-8")
    code, out = t.run(*night, env=env)
    check("after the look it sorts and stops for the six first-look photos (exit 7), and its words say first look, never sneak peek",
          code == 7 and (st / "peek-sheets.json").is_file() and "sneak peek" not in out.lower(), out[-600:])
    if code != 7:
        return
    sheets = json.loads((st / "peek-sheets.json").read_text(encoding="utf-8"))["shoots"]
    spec, checked = [], []
    for sid, s in sheets.items():
        n = s.get("moments") if isinstance(s.get("moments"), int) else len(s.get("list") or [])
        spec.append(f"{sid}=" + ",".join(str(k) for k in range(1, min(6, n) + 1)))
        checked += [f"--checked={sid} {k}: eyes open, mouth closed, sharp (a pretend photo)" for k in range(1, min(6, n) + 1)]
    t.run("peek_sheets.py", "closer", session, *spec, env=env)
    code, out = t.run("peek_sheets.py", "pick", session, *spec, *checked, env=env)
    check("the pick is saved with a checked line per photo", code == 0, out[-400:])
    code, out = t.run(*night, env=env)
    records = w.dest / ".studio" / session.name
    check("it finishes (exit 0): shoots put away beside the page's, the card as it was",
          code == 0 and (records / "settled.json").is_file() and not session.exists() and t.card_snapshot(card) == before, out[-600:])
    tree = shoots_tree(w.dest)
    check("its shoots carry the names from the look, in the same name_date folders", len([k for k in tree if k.startswith("Chat shoot 1_09-04-26/Chat_")]) == 4, str(sorted(tree))[-400:])
    check("no keyword file was written for Lightroom (the first look marks nothing)", not list(w.dest.rglob("*.xmp")))
    check("no second copy was made by itself (asked each time)", not [k for k in shoots_tree(w.lacie) if k.startswith("Chat")])
    code, out = t.run("backup_job.py", "status", env=env)
    check("the page's job record is not touched by a chat backup", '"card": "CARD B"' in out or '"card": "EOS_DIGITAL"' in out, out[-300:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--work", help="a folder under /private/tmp for this run, kept afterwards")
    ap.add_argument("--port", type=int, default=9930)
    ap.add_argument("--chrome", action="store_true", help="also press the pages in a hidden Chrome (run under tests/guard.py)")
    ap.add_argument("--no-chrome", action="store_true", help="the default: no browser")
    a = ap.parse_args()
    this_computer.utf8_output()
    only = [x for x in a.only.split(",") if x]
    work = Path(a.work) if a.work else Path(tempfile.mkdtemp(prefix="nov23-whole-"))
    if a.work:
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    work = work.resolve()       # a Mac's temp folder is reached by two spellings (/var and /private/var): one, for comparing
    w = None
    try:
        if not only or "units" in only:
            unit_checks(work)
        if not only or {"whole", "trouble", "chat"} & set(only):
            w = whole_checks(work, a.port, chrome=a.chrome and not a.no_chrome)
        if w is not None and (not only or "trouble" in only):
            trouble_checks(w)
        if w is not None and (not only or "chat" in only):
            w.stop()
            chat_checks(w)
    finally:
        if w is not None:
            w.stop()
        if not a.work:
            shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(_SCRATCH, ignore_errors=True)
    print()
    if SKIPPED:
        print(f"{len(SKIPPED)} skipped.")
    if FAILED:
        print(f"{len(FAILED)} FAILED:")
        for f in FAILED:
            print("  - " + f)
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
