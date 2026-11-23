#!/usr/bin/env python3
"""Back up a card, from the home page (Nicole's v31, sections 1 to 4 and 6; her answers of Nov 23).

    /usr/bin/lockf -t 5400 <the shared chrome.lock> python3 tests/guard.py 3000 python3 tests/backup_popup_check.py
        [--port 9860] [--work <a folder to keep>] [--no-chrome] [--shot]

What it holds, on a pretend computer of its own (a scratch STUDIO_HOME; pretend drives and a pretend card named in
STUDIO_DRIVES_FOR_TESTS; a pretend Pictures; the folder window answered by STUDIO_PICK_FOLDER_FOR_TESTS; a STAND-IN
for the backup job named in STUDIO_BACKUP_JOB_FOR_TESTS, so no backup is ever run; nothing of the real ~/.studio, no
/Volumes, no real card, no window on the screen):
  * the words: hers whole, "the Assistant", nothing that promises a notification, nothing about an editing queue;
  * what the box is told (/backup-popup): the card, the drives, where backups go, the two ways of naming with an
    example in the real spelling (Aurora_11-22-26, never periods), and never a path;
  * every guard of the folder browser, by request: the drive by number AND name, folder NAMES only, the exact
    listing (never case-blind), no dot names, no ".." or slashes, no links, packages or hidden and system folders,
    the listing capped and time-limited, GETs refusing another website and any other Host, POSTs through the
    pickers' guard; + New folder a plain mkdir (never over anything; a taken name opens the folder that is there);
  * where backups go is saved only when Start is pressed, EXACTLY the folder picked, after the checks (a memory
    card, onto itself, can't be written to, no room); the second copy is asked each time and never saved;
  * Start calls the job (the contract: start(source, dest, second, shoot_name)); a second Start while one runs
    starts nothing; Back up a folder instead goes through the computer's own folder window;
  * the job as the home card says it: "Copying and checking (128 of 181)", "Sorting into shoots", "Making your
    second copy", "Done. Every photo checked." only when the backup's own records say so, a problem in plain
    words, and never a path;
  * Your backups: only the heading and the list, See the report first;
  * in a HIDDEN Chrome: the whole walk, first time to Done, by real presses.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only.
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
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402

GB = 1024 ** 3
JSON_H = {"Content-Type": "application/json"}

STAND_IN = r'''
"""A stand-in for backup_job.py (the contract in the build's COMMON.md): it starts nothing. start() writes the
record as a job that has just begun and notes what it was asked; status() reads the record back."""
import json, os
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ["STUDIO_HOME"])
JOB = HOME / "backup-job.json"
CALLS = HOME / "stand-in-calls.json"


def status():
    try:
        return json.loads(JOB.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"state": "idle"}


def start(source, dest, second=None, shoot_name=None):
    if status().get("state") == "running":
        return {"ok": False, "why": "A backup is already running."}
    calls = json.loads(CALLS.read_text(encoding="utf-8")) if CALLS.exists() else []
    calls.append({"source": str(source), "dest": str(dest), "second": second, "shoot_name": shoot_name})
    CALLS.write_text(json.dumps(calls), encoding="utf-8")
    d = Path(dest)
    drive = os.environ.get("STAND_IN_DRIVE") or d.parts[-1]
    rec = {"state": "running", "step": "copying", "done": 0, "total": 5, "card": Path(source).name, "drive": drive,
           "folders": json.loads(os.environ.get("STAND_IN_FOLDERS") or "[]"), "second": Path(second).name if second else None,
           "shoots": 0, "backup": "monday card", "records": "", "line": "", "started": datetime.now().isoformat(timespec="seconds"),
           "finished": None}
    JOB.write_text(json.dumps(rec), encoding="utf-8")
    return {"ok": True}
'''


def skip(line):
    print("SKIP  " + line, flush=True)


class World:
    """A pretend computer: a card, two drives, a Pictures folder, a scratch STUDIO_HOME, the page server."""

    def __init__(self, work, port):
        self.work, self.port0, self.port, self.proc = work, port, None, None
        self.home = work / "studio"
        self.card = work / "vol" / "EOS_DIGITAL"
        self.gpapa = work / "vol" / "G PAPA"
        self.lacie = work / "vol" / "LaCie"
        self.tiny = work / "vol" / "Full Drive"
        self.mac = work / "mac"
        self.drives_file = work / "drives.json"
        self.stand_in = work / "stand_in_job.py"
        self.env = dict(os.environ, STUDIO_HOME=str(self.home), PYTHONIOENCODING="utf-8", STUDIO_NO_WINDOWS_FOR_TESTS="1",
                        STUDIO_DRIVES_FOR_TESTS=str(self.drives_file), STUDIO_FOLDERS_FOR_TESTS=str(self.mac),
                        STUDIO_BACKUP_JOB_FOR_TESTS=str(self.stand_in), STUDIO_SAMPLES_FOR_TESTS="none",
                        STAND_IN_DRIVE="G PAPA", ASSISTANT_TEST_OPEN="front")
        self.env.pop("STUDIO_CARD_FOR_TESTS", None)
        self.env.pop("STUDIO_PICK_FOLDER_FOR_TESTS", None)

    def build(self):
        self.home.mkdir(parents=True)
        (self.mac / "Pictures").mkdir(parents=True)
        d = self.card / "DCIM" / "100CANON"
        d.mkdir(parents=True)
        for i in range(5):
            (d / ("IMG_%04d.JPG" % (i + 1))).write_bytes(b"\xff\xd8photo %d" % i + b"\x00" * 200)
        # G PAPA: her sample folders, and everything the browser must never show
        for n in ("CLIENT WORK", "CLIENT WORK 25", "Family photos", "Personal", "Presets", "Selects", "Test shoots", "The Assistant", "Videos", "zebra", "Archive"):
            (self.gpapa / n).mkdir(parents=True)
        for n in ("2025", "2026", "2025-09-14 At home with the little ones", "2026-07-13 Patio"):
            (self.gpapa / "CLIENT WORK" / n).mkdir()
        (self.gpapa / "CLIENT WORK" / "2026" / "keep.txt").write_text("theirs", encoding="utf-8")
        for n in (".studio", "_studio", ".hidden things", "$RECYCLE.BIN", "System Volume Information", "Family.photoslibrary", "Old.lrdata"):
            (self.gpapa / n).mkdir()
        # (a Backups.backupdb at the very top would make the whole drive a Time Machine drive, which is never listed)
        (self.gpapa / "Personal" / "Backups.backupdb").mkdir()
        (self.gpapa / "Personal" / "Trips").mkdir()
        (self.gpapa / "notes.txt").write_text("a file", encoding="utf-8")
        (self.gpapa / "Taken by a file").write_text("a file", encoding="utf-8")
        self.outside = self.work / "outside the drive"
        (self.outside / "secret client").mkdir(parents=True)
        self.links = hasattr(os, "symlink") and os.name != "nt"
        if self.links:
            os.symlink(str(self.outside), str(self.gpapa / "A link out"))
            os.symlink(str(self.gpapa / "Personal"), str(self.gpapa / "A link in"))
        many = self.gpapa / "Archive"
        for i in range(450):
            (many / ("shoot %03d" % i)).mkdir()
        (self.lacie / "Client backups").mkdir(parents=True)
        (self.tiny / "Photos").mkdir(parents=True)
        self.stand_in.write_text(STAND_IN, encoding="utf-8")
        self.drives(card=True)

    def drives(self, card=True, gpapa=True, lacie=True, tiny=False):
        rows = [{"path": str(self.mac), "name": "Macintosh HD", "total": 500 * GB, "free": 200 * GB, "system": True}]
        if card:
            rows.append({"path": str(self.card), "name": "EOS_DIGITAL", "total": 64 * GB, "free": 10 * GB, "removable": True})
        if gpapa:
            rows.append({"path": str(self.gpapa), "name": "G PAPA", "total": 4000 * GB, "free": 1200 * GB, "removable": False})
        if lacie:
            rows.append({"path": str(self.lacie), "name": "LaCie", "total": 2000 * GB, "free": 840 * GB, "removable": False})
        if tiny:
            rows.append({"path": str(self.tiny), "name": "Full Drive", "total": 500 * GB, "free": 1 * GB, "removable": False})
        self.drives_file.write_text(json.dumps(rows), encoding="utf-8")

    def start(self, **env):
        f = self.home / "posting-url.txt"
        if f.exists():
            f.unlink()
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.port0)], env=dict(self.env, **env),
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=(os.name != "nt"))
        chrome_drive.wait_until(lambda: f.exists() and f.read_text(encoding="utf-8").strip(), 40, every=0.1, what="the page server's address")
        self.port = int(re.search(r":(\d+)/", f.read_text(encoding="utf-8")).group(1))
        chrome_drive.wait_until(lambda: self.http("GET", "/home")[0] == 200, 40, every=0.1, what="the home page")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def http(self, method, path, raw=None, headers=None, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        try:
            h = dict(headers or {})
            if host:
                h["Host"] = host
            c.request(method, path, body=raw, headers=h)
            r = c.getresponse()
            return r.status, r.read()
        finally:
            c.close()

    def get(self, path, **kw):
        code, raw = self.http("GET", path, **kw)
        try:
            return code, json.loads(raw.decode("utf-8"))
        except ValueError:
            return code, None

    def post(self, path, obj, headers=None, **kw):
        code, raw = self.http("POST", path, raw=json.dumps(obj).encode("utf-8"), headers=dict(JSON_H, **(headers or {})), **kw)
        try:
            return code, json.loads(raw.decode("utf-8"))
        except ValueError:
            return code, None

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def studio(self):
        try:
            return json.loads((self.home / "studio.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def session(self):
        return (self.studio().get("drives") or {}).get("session")

    def calls(self):
        f = self.home / "stand-in-calls.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []

    def job(self, **rec):
        """Write the job's record as the job itself would (whole, in the contract's shape)."""
        f = self.home / "backup-job.json"
        if not rec:
            if f.exists():
                f.unlink()
            return
        base = {"state": "running", "step": "copying", "done": 0, "total": 181, "card": "EOS_DIGITAL", "drive": "G PAPA",
                "folders": ["CLIENT WORK"], "second": None, "shoots": 0, "backup": "monday card", "records": "", "line": "",
                "started": datetime.now().isoformat(timespec="seconds"), "finished": None}
        base.update(rec)
        tmp = f.with_name("backup-job.json.part")
        tmp.write_text(json.dumps(base), encoding="utf-8")
        os.replace(str(tmp), str(f))

    def queue(self, rec):
        """Two shoots of one finished backup, as the editing queue's own record lists them."""
        (self.home / "queue.json").write_text(json.dumps({"asked": True, "on": True, "shoots": [
            {"id": "q1", "shoot": "s1", "name": "Aurora", "studio": str(rec), "count": 120, "status": "archived", "added": "2026-11-22T20:00:00", "thumbs": []},
            {"id": "q2", "shoot": "s2", "name": "Patio", "studio": str(rec), "count": 61, "status": "archived", "added": "2026-11-22T20:00:00", "thumbs": []}]}), encoding="utf-8")

    def records(self, name="monday card", ok=True, sample=False, where=None):
        """A finished backup's records, as home_base.backup_status reads them: every file's copy checked, or not."""
        rec = (where or (self.gpapa / "CLIENT WORK")) / ".studio" / name
        rec.mkdir(parents=True, exist_ok=True)
        m = {"finished": "2026-11-23T10:00:00", "problems": [] if ok else ["one file did not match"],
             "files": {"DCIM/100CANON/IMG_0001.JPG": {"dest": {"ok": ok}}, "DCIM/100CANON/IMG_0002.JPG": {"dest": {"ok": True}}}}
        if sample:
            m["sample"] = {"kept": 2, "of": 5}
        (rec / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
        # its two shoots, each in a folder of its own beside the records' hidden folder (a settled backup)
        root = rec.parent.parent
        for sid, folder in (("s1", "Aurora_11-22-26"), ("s2", "Patio_11-22-26")):
            (root / folder).mkdir(exist_ok=True)
        (rec / "shoots.json").write_text(json.dumps({"shoots": [{"id": "s1", "name": "Aurora", "folder": "Aurora_11-22-26"},
                                                                 {"id": "s2", "name": "Patio", "folder": "Patio_11-22-26"}]}), encoding="utf-8")
        return rec


def no_path(w, obj):
    raw = json.dumps(obj)
    return str(w.work) not in raw and "/private/" not in raw and "/vol/" not in raw


# ---------------------------------------------------------------- the words and the pages, with no server

def check_words(w):
    import backup_popup as bp
    import home
    import home_base
    everything = " ".join(list(bp.WORDS.values()) + list(bp.OUR_WORDS.values()))
    case("her safety words, whole, with \"The Assistant\"", bp.W("safety").startswith("The Assistant copies every photo on your card to your drive, and it can save a second copy on another drive too.")
         and "double-checks every single photo against your card" in bp.W("safety") and bp.W("safety").endswith("sorts them into shoots you can rename."))
    case("... and her bold line that the card is never changed", bp.W("safe") == "✓ Nothing on your card is ever changed or deleted. It stays exactly as it is until you decide to format it.")
    case("never \"your assistant\", never Claude, no em dash", "your assistant" not in everything.lower() and "claude" not in everything.lower() and "—" not in everything)
    case("nothing promises a notification (Nicole said no): no \"lets you know\"", "lets you know" not in everything.lower() and "notif" not in everything.lower())
    case("nothing says the shoots are in an editing queue (they are not)", "editing queue" not in everything.lower())
    case("the steps are Copying and checking, Sorting into shoots, Done: no checking step of its own",
         bp.W("copying") == "Copying and checking ({done} of {total})" and bp.W("sorting") == "Sorting into shoots" and "Checking every photo" not in everything)
    case("\"shoot name\", never \"client name\"", bp.W("who_label") == "What would you like to name this shoot?" and bp.W("who_ph") == "Shoot name" and "client name" not in everything.lower())
    case("the second copy is not said to be made at the same time", "same time" not in everything.lower() and bp.W("second_on") == "A second copy goes to <b>{drive}</b>, in the same folders")
    case("her \"Test only, to preview\" line is left out", "Test only" not in everything and "preview" not in everything.lower())
    page = home.page_html()
    case("the home card is a button that opens the box, with See all my backups as its link to the list",
         "id='s1' data-item='backup' role='button' tabindex='0'" in page and "<a class='seeall' id='seeAll' href='/backups'>See all my backups</a>" in page)
    case("the box is on the home page, hidden, her title in her accent", "<div class='bkp' id='bk' hidden>" in page and "<h3 id='bkT'>Back up <em>a card</em></h3>" in page and "aria-modal='true'" in page)
    case("the home page waits with its own reload while the box is open", "window.MK_HOLD || window.BK_HOLD" in page)
    case("a press on Back up a card is answered by the page: the chat is not told to explain it", "backup" in home.ANSWERED_BY_PAGE)
    b = home_base.backups_html()
    text = re.sub(r"<script.*", "", b, flags=re.S)
    case("Your backups: only her heading and the list", "<h1>Your <em>backups.</em></h1>" in b and "id='backups'" in b and "id='find'" in b
         and "Every card you've backed up, newest first." in b)
    case("... the explanation and the two steps are gone (no \"Paste this in the chat\", no \"backup now\", no card line)",
         "Paste this in the chat" not in b and "backup now" not in text and "cardStatus" not in b and "How to back up a card" not in b and "class='steps" not in b)
    at_report, at_open = b.find('data-report="${esc(s.id)}"'), b.find('data-open="${esc(s.id)}"')
    case("... See the report is the main button, Open this folder under it", 0 < at_report < at_open and 'class="btn solid" data-report' in b and 'class="btn" data-open' in b)


# ---------------------------------------------------------------- what the box is told, and the guards, by request

def check_state(w):
    code, d = w.get("/backup-popup")
    case("/backup-popup: the card that is in, by name and about how many files", code == 200 and d["ok"] and d["card"] == {"name": "EOS_DIGITAL", "files": 5}, d and d.get("card"))
    case("... the drives a backup could go on, by number, name and room (never the card, never the computer's own disk)",
         d["drives"] == [{"d": 0, "name": "G PAPA", "free": "1.2 TB"}, {"d": 1, "name": "LaCie", "free": "840 GB"}], d["drives"])
    case("... the first time: nothing saved yet", d["saved"] is None and d["first"] is True)
    ways = d["naming"]["ways"]
    case("... the two ways of naming, each named from its own pattern", [x["label"] for x in ways] == ["Shoot name_Date", "Date Shoot name"] and d["naming"]["current"] == 1, d["naming"])
    case("... each with an example in the real spelling: Aurora_11-22-26, never periods",
         re.fullmatch(r"Aurora_\d\d-\d\d-\d\d", ways[0]["example"]) and re.fullmatch(r"\d{4}-\d\d-\d\d Aurora", ways[1]["example"]) and "." not in ways[0]["example"], ways)
    case("... never a path", no_path(w, d))
    case("... no job yet", d["job"]["state"] == "idle" and d["job"]["show"] is False)
    for path in ("/backup-popup", "/backup-job", "/backup-report"):
        c1, _ = w.get(path, headers={"Sec-Fetch-Site": "cross-site"})
        c2, _ = w.get(path, host="evil.example")
        c3, _ = w.get(path, host="127.0.0.1:1")
        case("GET %s: refused to another website, and to any other Host" % path, (c1, c2, c3) == (403, 403, 403), (c1, c2, c3))


def check_guards(w):
    G = {"d": 0, "name": "G PAPA"}
    code, d = w.post("/backup-folders", dict(G, path=[]))
    names = d.get("folders") if d else None
    case("the top of the drive: its plain folders, in order", code == 200 and d["ok"] and names == sorted(names, key=lambda s: (s.casefold(), s))
         and {"CLIENT WORK", "CLIENT WORK 25", "Family photos", "The Assistant", "zebra", "Archive"} <= set(names), names)
    hidden = {".studio", "_studio", ".hidden things", "$RECYCLE.BIN", "System Volume Information"}
    code2, d2 = w.post("/backup-folders", dict(G, path=["Personal"]))
    case("... never the Assistant's own records, a dot folder, Time Machine or the computer's housekeeping", not (hidden & set(names)) and d2["folders"] == ["Trips"], (hidden & set(names or []), d2))
    case("... never a package (a Photos library, a Lightroom data folder)", "Family.photoslibrary" not in names and "Old.lrdata" not in names)
    case("... never a file", "notes.txt" not in names and "Taken by a file" not in names)
    if w.links:
        case("... never a link, wherever it points", "A link out" not in names and "A link in" not in names)
    else:
        skip("links: this computer makes none")
    case("... names only, never a path", no_path(w, d))
    code, d = w.post("/backup-folders", dict(G, path=["CLIENT WORK"]))
    case("a folder opened by its name: what is inside it", code == 200 and d["folders"] == ["2025", "2025-09-14 At home with the little ones", "2026", "2026-07-13 Patio"], d)
    code, d = w.post("/backup-folders", dict(G, path=["Archive"]))
    case("a folder with 450 folders: 400 are listed, and it says there are more", code == 200 and len(d["folders"]) == 400 and d["more"] is True, (code, d and len(d.get("folders", []))))
    refused = [
        ("\"..\"", [".."]), ("\".\"", ["."]), ("a name with a slash", ["CLIENT WORK/2026"]), ("a name with a backslash", ["CLIENT WORK\\2026"]),
        ("up and out with \"..\" after a real folder", ["CLIENT WORK", "..", ".."]), ("a dot folder", [".studio"]), ("the hidden dot folder", [".hidden things"]),
        ("the Assistant's old records folder", ["_studio"]), ("Time Machine's folder", ["Personal", "Backups.backupdb"]), ("the recycle bin", ["$RECYCLE.BIN"]),
        ("a package", ["Family.photoslibrary"]), ("a file", ["notes.txt"]), ("an empty name", [""]), ("a name with a control character", ["CLIENT\nWORK"]),
        ("a name that is not text", [7]), ("a name that is not there", ["Nope"]),
        ("the same name in other capitals (the exact listing decides, never a case-blind look)", ["client work"]),
        ("thirteen folders deep", ["CLIENT WORK"] * 13)]
    if w.links:
        refused += [("a link out of the drive", ["A link out"]), ("a folder behind a link out of the drive", ["A link out", "secret client"]), ("a link to a folder on the drive", ["A link in"])]
    for what, path in refused:
        code, d = w.post("/backup-folders", dict(G, path=path))
        case("refused: " + what, code in (400, 409) and d and d["ok"] is False and "folders" not in d and no_path(w, d), (code, d))
    for what, body in (("a path in place of the names", dict(G, path="/etc")), ("no names at all", G), ("an extra field", dict(G, path=[], root="/")),
                       ("the drive's number without its name", {"d": 0, "path": []})):
        code, d = w.post("/backup-folders", body)
        case("refused: " + what, code == 400 and d["ok"] is False, (code, d))
    for what, body in (("the right number with another drive's name", {"d": 0, "name": "LaCie", "path": []}), ("a number past the list", {"d": 9, "name": "G PAPA", "path": []}),
                       ("a number that is not a number", {"d": "0", "name": "G PAPA", "path": []}), ("a number below the list", {"d": -1, "name": "LaCie", "path": []}),
                       ("true for the number", {"d": True, "name": "LaCie", "path": []})):
        code, d = w.post("/backup-folders", body)
        case("the drive is its number AND its name, checked again: " + what + " is refused, pick again", code == 409 and "Pick the drive again" in d["words"], (code, d))
    # the POST guard, on every route
    for path in ("/backup-folders", "/backup-folder-new", "/backup-pick", "/backup-naming", "/backup-start"):
        body = json.dumps(dict(G, path=[])).encode()
        c1, _ = w.http("POST", path, raw=body, headers=dict(JSON_H, Origin="http://evil.example"))
        c2, _ = w.http("POST", path, raw=body, headers=dict(JSON_H, **{"Sec-Fetch-Site": "cross-site"}))
        c3, _ = w.http("POST", path, raw=body, headers={"Content-Type": "text/plain"})
        c4, _ = w.http("POST", path, raw=body, headers=JSON_H, host="evil.example")
        c5, _ = w.http("POST", path, raw=b'{"x":"' + b"a" * 7000 + b'"}', headers=JSON_H)
        case("POST %s: refused from another website, as plain text, to another Host, and when too long" % path, (c1, c2, c3, c4, c5) == (403, 403, 415, 403, 413), (c1, c2, c3, c4, c5))
    case("none of that saved where backups go, or made a folder", w.session() is None and not (w.gpapa / "Nope").exists())


def check_new_folder(w):
    G = {"d": 0, "name": "G PAPA"}
    before = sorted(os.listdir(str(w.gpapa / "CLIENT WORK")))
    code, d = w.post("/backup-folder-new", dict(G, path=["CLIENT WORK"], new="Minis 2026"))
    case("+ New folder: made inside the folder that was open, and opened", code == 200 and d["ok"] and d["path"] == ["CLIENT WORK", "Minis 2026"] and d["existed"] is False
         and (w.gpapa / "CLIENT WORK" / "Minis 2026").is_dir() and no_path(w, d), (code, d))
    code, d = w.post("/backup-folder-new", dict(G, path=["CLIENT WORK"], new="minis 2026"))
    case("a name that is taken, in other capitals: the folder that is there is opened, no second one is made",
         code == 200 and d["ok"] and d["existed"] is True and d["path"] == ["CLIENT WORK", "Minis 2026"] and "already a folder called Minis 2026" in d["words"]
         and sorted(os.listdir(str(w.gpapa / "CLIENT WORK"))) == sorted(before + ["Minis 2026"]), (code, d))
    code, d = w.post("/backup-folder-new", dict(G, path=["CLIENT WORK"], new="2026"))
    case("... and what was in a folder that was already there is untouched", code == 200 and d["existed"] is True
         and (w.gpapa / "CLIENT WORK" / "2026" / "keep.txt").read_text(encoding="utf-8") == "theirs")
    code, d = w.post("/backup-folder-new", dict(G, path=[], new="Taken by a file"))
    case("a name taken by a file: refused in plain words, the file untouched", code == 409 and d["ok"] is False and (w.gpapa / "Taken by a file").read_text(encoding="utf-8") == "a file", (code, d))
    code, d = w.post("/backup-folder-new", dict(G, path=[], new="Smith / Jones: day 2"))
    case("characters a drive can't take are cleaned out of the name, and it says so", code == 200 and d["ok"] and d["cleaned"] is True and d["path"] == ["Smith Jones day 2"]
         and "Smith Jones day 2" in d["words"] and (w.gpapa / "Smith Jones day 2").is_dir(), (code, d))
    for what, new in (("a name starting with a dot", ".secret"), ("an empty name", "   "), ("only dots", ".."), ("a name that is not text", 7), ("the Assistant's records name", "_studio")):
        code, d = w.post("/backup-folder-new", dict(G, path=[], new=new))
        case("refused: " + what, code == 400 and d["ok"] is False, (code, d))
    case("... and nothing was made for them", not (w.gpapa / ".secret").exists() and len([n for n in os.listdir(str(w.gpapa)) if n == "_studio"]) == 1)
    code, d = w.post("/backup-folder-new", dict(G, path=["Nope"], new="x"))
    case("a new folder inside a folder that is not there: refused, nothing made", code == 409 and not (w.gpapa / "Nope").exists(), (code, d))
    if w.links:
        code, d = w.post("/backup-folder-new", dict(G, path=["A link out"], new="planted"))
        case("a new folder through a link out of the drive: refused, nothing made outside", code == 400 and not (w.outside / "planted").exists(), (code, d))
    code, d = w.post("/backup-folder-new", {"d": 0, "name": "LaCie", "path": [], "new": "x"})
    case("a new folder on a drive named wrongly: refused, nothing made", code == 409 and not (w.gpapa / "x").exists() and not (w.lacie / "x").exists(), (code, d))
    case("a new folder never saves where backups go", w.session() is None)


def check_naming(w):
    code, d = w.post("/backup-naming", {"offered": 2})
    n = w.studio().get("naming") or {}
    case("Change the naming: year first is saved for every backup from now on", code == 200 and d["ok"] and d["naming"]["current"] == 2
         and n.get("folder_pattern") == "{date} {shoot}" and n.get("date_format") == "%Y-%m-%d", (code, n))
    for bad in ({"offered": 3}, {"offered": 0}, {"offered": "1"}, {"offered": True}, {"offered": 1, "apply": True}, {}):
        code, d = w.post("/backup-naming", bad)
        case("refused: %s" % json.dumps(bad), code == 400 and d["ok"] is False, (code, d))
    code, d = w.post("/backup-naming", {"offered": 1})
    n = w.studio().get("naming") or {}
    case("... and back: the shoot's name, then the date", code == 200 and d["naming"]["current"] == 1 and n.get("folder_pattern") == "{shoot}_{date}" and n.get("date_format") == "%m-%d-%y", n)
    case("the naming alone never saves where backups go", w.session() is None)


def check_start(w):
    exact = str((w.gpapa / "CLIENT WORK" / "2026").resolve())
    dest = {"d": 0, "name": "G PAPA", "path": ["CLIENT WORK", "2026"]}
    case("before Start nothing is saved, however much was picked", w.session() is None and not w.calls())
    for what, body, codes in (
            ("the card is not the one that is in", {"source": "card", "card": "OTHER_CARD", "dest": dest, "second": None, "shoot_name": ""}, (409,)),
            ("no card named", {"source": "card", "dest": dest, "second": None, "shoot_name": ""}, (409,)),
            ("the top of the drive with no folder", {"source": "card", "card": "EOS_DIGITAL", "dest": {"d": 0, "name": "G PAPA", "path": []}, "second": None}, (400,)),
            ("a folder that is not there", {"source": "card", "card": "EOS_DIGITAL", "dest": {"d": 0, "name": "G PAPA", "path": ["Nope"]}, "second": None}, (409,)),
            ("a path in place of the names", {"source": "card", "card": "EOS_DIGITAL", "dest": {"d": 0, "name": "G PAPA", "path": [str(w.outside)]}, "second": None}, (400,)),
            ("a path as the place itself", {"source": "card", "card": "EOS_DIGITAL", "dest": str(w.outside), "second": None}, (400,)),
            ("\"the place I saved\" with nothing saved", {"source": "card", "card": "EOS_DIGITAL", "dest": {"saved": True}, "second": None}, (409,)),
            ("this computer while a drive is plugged in", {"source": "card", "card": "EOS_DIGITAL", "dest": {"computer": True}, "second": None}, (409,)),
            ("a second copy on the same drive as the first", {"source": "card", "card": "EOS_DIGITAL", "dest": dest, "second": {"d": 0, "name": "G PAPA"}}, (400,)),
            ("a second copy on a drive named wrongly", {"source": "card", "card": "EOS_DIGITAL", "dest": dest, "second": {"d": 1, "name": "G PAPA"}}, (409,)),
            ("a second copy as a path", {"source": "card", "card": "EOS_DIGITAL", "dest": dest, "second": str(w.lacie)}, (400,)),
            ("a source that is neither a card nor a folder", {"source": str(w.outside), "dest": dest}, (400,)),
            ("an extra field", {"source": "card", "card": "EOS_DIGITAL", "dest": dest, "second": None, "name": "x"}, (400,))):
        code, d = w.post("/backup-start", body)
        case("Start refused: " + what, code in codes and d["ok"] is False and no_path(w, d), (code, d))
    case("... and none of them saved a place or started anything", w.session() is None and not w.calls() and not (w.home / "backup-job.json").exists())
    # a drive with no room for the card: said plainly, nothing saved
    w.drives(tiny=True)
    code, d = w.post("/backup-start", {"source": "card", "card": "EOS_DIGITAL", "dest": {"d": 2, "name": "Full Drive", "path": ["Photos"]}, "second": None, "shoot_name": ""})
    case("a drive with no room for this card: said in plain words, nothing saved, nothing started", code == 409 and "does not have room" in d["words"] and w.session() is None and not w.calls(), (code, d))
    w.drives()
    # the real thing
    code, d = w.post("/backup-start", {"source": "card", "card": "EOS_DIGITAL", "dest": dest, "second": {"d": 1, "name": "LaCie"}, "shoot_name": "  Aurora   Family "})
    calls = w.calls()
    case("Start: the job is asked once, with the card, the EXACT folder picked, the second drive and the shoot's name",
         code == 200 and d["ok"] and len(calls) == 1 and calls[0] == {"source": str(w.card), "dest": exact, "second": str(w.lacie), "shoot_name": "Aurora Family"}, (code, d, calls))
    case("... where backups go is saved now: exactly that folder, not the top of the drive, not a likelier folder", w.session() == exact, w.session())
    case("... the second drive is never saved: it is asked each time", "second" not in (w.studio().get("drives") or {}), w.studio().get("drives"))
    case("... the answer names the card and the place in words, never a path", d["from"] == "EOS_DIGITAL" and d["where"] == "G PAPA › CLIENT WORK › 2026" and d["second"] == "LaCie" and no_path(w, d), d)
    case("... and carries the job as the card will show it", d["job"]["state"] == "running" and d["job"]["head"] == "Copying and checking (0 of 5)", d["job"])
    code, d = w.post("/backup-start", {"source": "card", "card": "EOS_DIGITAL", "dest": {"saved": True}, "second": None, "shoot_name": ""})
    case("a second Start while one runs: nothing is started, and it says one is running", code == 200 and d["ok"] is False and d["running"] is True
         and "already running" in d["words"] and len(w.calls()) == 1, (code, d))
    code, d = w.get("/backup-popup")
    case("the box now opens filled in: the drive and the folder, by name", d["saved"] == {"drive": "G PAPA", "folders": ["CLIENT WORK", "2026"], "here": True, "computer": False}
         and d["first"] is False and no_path(w, d), d["saved"])
    # after it: the saved place, started again
    w.job()
    stamp = (w.home / "studio.json").stat().st_mtime_ns
    time.sleep(0.02)
    code, d = w.post("/backup-start", {"source": "card", "card": "EOS_DIGITAL", "dest": {"saved": True}, "second": None, "shoot_name": ""})
    calls = w.calls()
    case("the next time: Start with the saved place asks the job for the same folder, no second copy unless asked again",
         code == 200 and d["ok"] and len(calls) == 2 and calls[1] == {"source": str(w.card), "dest": exact, "second": None, "shoot_name": None}, (code, d, calls[-1]))
    case("... and writes nothing new in their settings", (w.home / "studio.json").stat().st_mtime_ns == stamp)
    w.job()


def check_writer(w):
    """studio_file.set_backup_place itself: the checks before a place is ever saved."""
    import studio_file as sf
    was = w.session()
    for what, kw in (("a folder on the memory card", {"place": str(w.card / "DCIM")}), ("the card itself", {"place": str(w.card)}),
                     ("a folder that is not there", {"place": str(w.gpapa / "Nope")}), ("no folder at all", {"place": ""}),
                     ("a folder that is not a full path", {"place": "CLIENT WORK"}),
                     ("the very folder being backed up", {"place": str(w.gpapa / "Personal"), "source": str(w.gpapa / "Personal")}),
                     ("a folder inside what is being backed up", {"place": str(w.gpapa / "CLIENT WORK" / "2025"), "source": str(w.gpapa / "CLIENT WORK")}),
                     ("a folder that holds what is being backed up", {"place": str(w.gpapa / "CLIENT WORK"), "source": str(w.gpapa / "CLIENT WORK" / "2025")}),
                     ("a drive with no room", {"place": str(w.lacie / "Client backups"), "need": 900 * GB})):
        got = sf.set_backup_place(**kw)
        case("never saved: " + what, got["state"] == "stop" and got.get("why") and w.session() == was, got)
    if os.name != "nt" and os.geteuid() != 0:
        ro = w.lacie / "Read only"
        ro.mkdir()
        os.chmod(str(ro), 0o555)
        got = sf.set_backup_place(str(ro))
        os.chmod(str(ro), 0o755)
        case("never saved: a folder that can only be read", got["state"] == "stop" and "can be read but not written" in got["why"] and w.session() == was, got)
    place = w.lacie / "Client backups"
    got = sf.set_backup_place(str(place), source=str(w.card))
    case("saved: exactly the folder given", got["state"] == "saved" and w.session() == str(place.resolve()), got)
    stamp = (w.home / "studio.json").stat().st_mtime_ns
    time.sleep(0.02)
    got = sf.set_backup_place(str(place), source=str(w.card))
    case("... twice writes once", got["state"] == "same" and (w.home / "studio.json").stat().st_mtime_ns == stamp, got)
    case("... the top of a drive is taken as given too (nothing is swapped in)", sf.set_backup_place(str(w.gpapa))["state"] == "saved" and w.session() == str(w.gpapa.resolve()))
    case("... it leaves no test file behind on the drive", not (w.gpapa / ".studio-write-test").exists() and not (place / ".studio-write-test").exists())
    try:
        sf.set_offered(3)
        ok = False
    except ValueError:
        ok = True
    case("the naming writer takes only the two offered ways", ok and sf.set_offered(1) is False)
    sf.set_backup_place(str(w.gpapa / "CLIENT WORK" / "2026"))


def check_job(w):
    def view():
        code, d = w.get("/backup-job")
        return d
    w.job()
    case("no job: nothing shows", view() == {"ok": True, "state": "idle", "show": False})
    (w.home / "backup-job.json").write_text("{ not json", encoding="utf-8")
    case("a record that can't be read: nothing shows (never a backup nobody can vouch for)", view()["state"] == "idle")
    w.job(state="running", step="copying", done=128, total=181)
    v = view()
    case("copying: \"Copying and checking (128 of 181)\", the bar part way", v["head"] == "Copying and checking (128 of 181)" and abs(v["frac"] - 128 / 181) < 1e-6 and v["show"], v)
    case("... what is going where, in words", v["sub"] == "Backing up EOS_DIGITAL to G PAPA › CLIENT WORK" and v["where"] == "G PAPA › CLIENT WORK", v)
    case("... the steps: Copying and checking, Sorting into shoots, Done", [s["t"] for s in v["steps"]] == ["Copying and checking", "Sorting into shoots", "Done"]
         and [s["on"] for s in v["steps"]] == [True, False, False], v["steps"])
    w.job(state="running", step="copying", done=0, total=0)
    case("copying before the count is known: no numbers are made up", view()["head"] == "Copying and checking" and view()["frac"] == 0.0)
    w.job(state="running", step="sorting", done=181, total=181)
    v = view()
    case("sorting: \"Sorting into shoots\", the bar full", v["head"] == "Sorting into shoots" and v["frac"] == 1.0 and [s["dn"] for s in v["steps"]] == [True, False, False], v)
    w.job(state="running", step="second", done=0, total=0, second="LaCie")
    v = view()
    case("a second copy asked for: \"Making your second copy\" is a step of its own, after the sorting", v["head"] == "Making your second copy" and "LaCie" in v["sub"]
         and [s["t"] for s in v["steps"]] == ["Copying and checking", "Sorting into shoots", "Making your second copy", "Done"] and v["second"] == "LaCie", v)
    w.job(state="running", step="second", done=3, total=10, second="LaCie")
    v = view()
    case("... with how far the second copy is, once the job says (its own count, the bar following it)",
         v["head"] == "Making your second copy (3 of 10)" and abs(v["frac"] - 0.3) < 1e-9, v)
    rec = w.records()
    now = datetime.now().isoformat(timespec="seconds")
    w.job(state="done", step="done", done=181, total=181, shoots=3, records=str(rec), finished=now)
    v = view()
    case("done, and the records say every copy was checked: \"Done. Every photo checked.\"", v["head"] == "Done. Every photo checked." and v["checked"] is True and v["show"], v)
    case("... \"We found 3 shoots on your card\" with Name them; \"Your 3 shoots are backed up.\"", v["sub"] == "We found 3 shoots on your card" and v["link"] == {"kind": "name", "words": "Name them"}
         and v["backed"] == "Your 3 shoots are backed up." and v["backup"] == "monday card", v)
    case("... never a path, and never the records' place", no_path(w, v) and "records" not in v)
    w.job(state="done", step="done", shoots=1, records=str(rec), finished=now)
    v = view()
    case("one shoot is one shoot", v["sub"] == "We found 1 shoot on your card" and v["link"]["words"] == "Name it" and v["backed"] == "Your shoot is backed up.", v)
    bad = w.records("bad card", ok=False)
    w.job(state="done", step="done", shoots=3, records=str(bad), finished=now)
    v = view()
    case("done, but the records do NOT say every copy was checked: only \"Done.\", and see the report", v["head"] == "Done." and v["checked"] is False
         and "Every photo checked" not in json.dumps(v) and v["link"]["kind"] == "report" and v["safe_format"] is False, v)
    w.job(state="done", step="done", shoots=3, records="", finished=now)
    v = view()
    case("done with no records to read: no claim is made", v["head"] == "Done." and v["checked"] is False and v["safe_format"] is False, v)
    smp = w.records("sample card", sample=True)
    w.job(state="done", step="done", shoots=1, records=str(smp), finished=now)
    v = view()
    case("a sample backup is never called checked or safe to format", v["head"] == "Done." and v["sub"] == "Keep the card: this was a sample" and v["safe_format"] is False, v)
    w.job(state="done", step="done", shoots=3, records=str(rec), finished=(datetime.now() - timedelta(hours=13)).isoformat(timespec="seconds"))
    case("a backup that finished yesterday no longer sits on the card", view()["show"] is False)
    w.job(state="problem", step="copying", done=40, total=181, line="Your memory card stopped answering.\nTake it out and put it back in.", finished=now)
    v = view()
    case("a backup that stopped: the job's own plain words, on one line, and what to do", v["head"] == "Your memory card stopped answering. Take it out and put it back in."
         and "Start the backup again" in v["sub"] and v["bad"] is True and v["show"], v)
    w.job(state="problem", line="", finished=now)
    case("... with no words from the job: ours", view()["head"] == "The backup stopped before it finished.")
    # the real job's record (backup_job.py): what was asked is kept under "private", so the card has Try again
    case("a stopped backup whose record does not say what was asked has no Try again", "again" not in view())
    private = {"pid": 1, "source": str(w.card), "dest": str(w.gpapa / "CLIENT WORK"), "second": str(w.lacie), "shoot_name": "Aurora", "is_card": True}
    w.job(state="problem", step="copying", done=40, total=181, finished=now, private=private,
          line="The backup stopped before it finished. Nothing is lost: press Try again and it picks up where it left off.")
    v = view()
    case("the job's own stopped backup: Try again on the card, and no line telling them to press Start the backup again",
         v.get("again") == "Try again" and "Start the backup again" not in json.dumps(v) and "press Try again" in v["head"] and no_path(w, v) and "private" not in v, v)
    box = bp_card_box()
    case("... drawn by the server on a reload too, as a button", "data-bk='again'>Try again</button>" in box and "class='bad'" in box, box)
    had = len(w.calls())
    code, d = w.post("/backup-again", {"source": "/tmp/x"})
    case("Try again takes nothing from the page (a body with anything in it is refused, nothing started)", code == 400 and len(w.calls()) == had, d)
    code, d = w.post("/backup-again", {}, headers={"Origin": "http://evil.example"})
    case("... and another website can't press it", code == 403 and len(w.calls()) == had, d)
    code, d = w.post("/backup-again", {})
    last = (w.calls() or [{}])[-1]
    case("Try again starts the same backup again: the same card, the exact same folder, the same second drive and name, from the record",
         code == 200 and d.get("ok") is True and len(w.calls()) == had + 1 and last == {"source": str(w.card), "dest": str(w.gpapa / "CLIENT WORK"),
                                                                                       "second": str(w.lacie), "shoot_name": "Aurora"}
         and d["job"]["state"] == "running" and no_path(w, d), (code, d, last))
    code, d = w.post("/backup-again", {})
    case("... pressed again while it runs: nothing more is started", d.get("ok") is False and d.get("running") is True and len(w.calls()) == had + 1, d)
    w.job(state="done", step="done", shoots=3, records=str(rec), finished=now)
    code, d = w.post("/backup-again", {})
    case("... and there is nothing to try again on a backup that finished", d.get("ok") is False and len(w.calls()) == had + 1 and d.get("words"), d)
    # a folder, said by the job's own record; a second copy that did not finish; what the job has to add
    w.job(state="done", step="done", shoots=2, records=str(rec), finished=now, private={"source": "x", "dest": "y", "is_card": False})
    v = view()
    case("the job's record says it was a folder: \"in your folder\", and nothing is called safe to format",
         v["from_folder"] is True and v["sub"] == "We found 2 shoots in your folder" and v["safe_format"] is False, v)
    line = "3 files that are not a photo were set aside. Your photos are backed up and checked. The second copy isn't made yet: LaCie already has a folder called Shoot 1."
    w.job(state="done", step="done", shoots=3, records=str(rec), finished=now, second="LaCie", second_ok=False, second_line="x", line=line)
    v = view()
    steps = {s["t"]: s for s in v["steps"]}
    case("a second copy that did not finish: the backup is still Done and checked, the second step is NOT ticked, and the job's own words are on the card",
         v["head"] == "Done. Every photo checked." and v.get("second_bad") is True and steps["Second copy not made"]["dn"] is False
         and steps["Second copy not made"].get("bad") is True and steps["Sorting into shoots"]["dn"] is True and v["note"] == line, v)
    box = bp_card_box()
    case("... on a reload too", "<small class='nt'>" in box and "The second copy isn&#x27;t made yet" in box, box)
    w.job(state="done", step="done", shoots=3, records=str(rec), finished=now, second="LaCie", second_ok=True, line="")
    v = view()
    case("a second copy that was made: every step ticked, nothing more to say", all(s["dn"] for s in v["steps"]) and not v.get("second_bad") and v["note"] == "", v)
    import backup_popup as bp
    w.job(state="running", step="copying", done=3, total=5)
    box = bp.card_box()
    case("the home card, drawn by the server on a reload: the count, the thin bar, and bold \"No need to wait. Keep working.\"",
         "<b>Copying and checking (3 of 5)</b>" in box and "class='bar2'><i style='width:60%'>" in box and "<small class='nw'>No need to wait. Keep working.</small>" in box, box)
    w.job(state="done", step="done", shoots=3, records=str(rec), finished=now, card="<b>x</b>")
    box = bp.card_box()
    case("... Done on a reload, with Name them as a button", "<b class='dn'>Done. Every photo checked.</b>" in box and "data-bk='name'>Name them</button>" in box and "<b>x</b>" not in box, box)
    w.job()
    case("... and nothing when there is no job (the card as it always was)", bp.card_box() is None)
    case("a listing that takes too long is given up on, not waited for", _slow(bp))
    code, d = w.get("/backup-report")
    case("the report of a job that is not there: plain words, no address", code == 200 and d["ok"] is False and d["words"], d)


def bp_card_box():
    import backup_popup as bp
    return bp.card_box()


def _slow(bp):
    t0 = time.time()
    try:
        bp._limited(lambda: time.sleep(3), 0.3)
    except bp.Refused as r:
        return r.code == 504 and time.time() - t0 < 2 and "long time" in r.words
    return False


def check_folder_source(w):
    """Back up a folder instead: the computer's own folder window (answered by the tests' switch), then the same job."""
    import backup_popup as bp
    w.job()
    os.environ.pop("STUDIO_PICK_FOLDER_FOR_TESTS", None)
    n = len(w.calls())
    got = bp.start({"source": "folder", "dest": {"saved": True}, "second": None, "shoot_name": ""})
    case("the folder window closed without a choice: nothing starts, nothing is said to be wrong", got["ok"] is False and got.get("cancelled") is True and len(w.calls()) == n, got)
    src = w.work / "phone photos"
    src.mkdir()
    (src / "a.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 50)
    os.environ["STUDIO_PICK_FOLDER_FOR_TESTS"] = str(src)
    got = bp.start({"source": "folder", "dest": {"saved": True}, "second": None, "shoot_name": ""})
    calls = w.calls()
    case("a folder picked in the window: the same job, with that folder as what is backed up", got["ok"] and len(calls) == n + 1 and calls[-1]["source"] == str(src)
         and calls[-1]["dest"] == w.session() and got["from"] == "phone photos" and no_path(w, got), (got, calls[-1]))
    w.job(state="done", step="done", shoots=2, records=str(w.records()), finished=datetime.now().isoformat(timespec="seconds"))
    v = bp.job_view()
    case("... when it is done it speaks of the folder, never of formatting a card", v["sub"] == "We found 2 shoots in your folder" and v["from_folder"] is True and v["safe_format"] is False, v)
    w.job()
    os.environ["STUDIO_PICK_FOLDER_FOR_TESTS"] = str(w.gpapa / "CLIENT WORK")
    got_ok = None
    try:
        bp.start({"source": "folder", "dest": {"saved": True}, "second": None, "shoot_name": ""})
    except bp.Refused as r:
        got_ok = r.words
    case("a folder that holds the place the backups go: refused before anything starts", bool(got_ok) and len(w.calls()) == n + 1, got_ok)
    # the folder window as a fallback for the place itself
    os.environ["STUDIO_PICK_FOLDER_FOR_TESTS"] = str(w.gpapa / "CLIENT WORK" / "2025")
    got = bp.picked_in_window(os.environ["STUDIO_PICK_FOLDER_FOR_TESTS"])
    case("the folder window as a fallback: a folder on a listed drive comes back as the drive and folder NAMES", got == {"ok": True, "d": 0, "name": "G PAPA", "path": ["CLIENT WORK", "2025"]}, got)
    for what, p in (("a folder on no listed drive", w.outside), ("the top of a drive", w.gpapa), ("a hidden folder on the drive", w.gpapa / "_studio"), ("a folder on the card", w.card / "DCIM")):
        try:
            bp.picked_in_window(str(p))
            ok = False
        except bp.Refused:
            ok = True
        case("... refused: " + what, ok)
    os.environ.pop("STUDIO_PICK_FOLDER_FOR_TESTS", None)


def check_computer(w):
    """No external drive at all: the two choices; this computer is <Pictures>/Shoots, saved only on Start."""
    import backup_popup as bp
    import studio_file as sf
    w.drives(gpapa=False, lacie=False)
    old = w.session()
    st = bp.state()
    case("no external drive: no drives are listed (the box offers the two choices)", st["drives"] == [] and st["card"]["name"] == "EOS_DIGITAL", st["drives"])
    got = bp.start({"source": "card", "card": "EOS_DIGITAL", "dest": {"computer": True}, "second": None, "shoot_name": ""})
    shoots = (w.mac / "Pictures" / "Shoots").resolve()
    case("On this Mac for now: Shoots inside Pictures is made and saved, and the job is given it", got["ok"] and shoots.is_dir() and w.session() == str(shoots)
         and w.calls()[-1]["dest"] == str(shoots) and w.session() != old, (got, w.session()))
    st = bp.state()
    case("... and the box shows it in words", st["saved"]["computer"] is True and st["saved"]["folders"][-1] == "Shoots" and no_path(w, st), st["saved"])
    w.job()
    w.drives()
    keep = (w.home / "studio.json").read_text(encoding="utf-8")
    (w.home / "studio.json").write_text(json.dumps({"drives": {"session": str(w.work / "vol" / "Unplugged" / "My Shoots")}}), encoding="utf-8")
    st = bp.state()
    case("the saved drive not plugged in: said not to be there, never offered as ready, never a path",
         st["saved"]["here"] is False and st["saved"]["computer"] is False and st["first"] is False and no_path(w, st), st["saved"])
    try:
        bp.start({"source": "card", "card": "EOS_DIGITAL", "dest": {"saved": True}, "second": None, "shoot_name": ""})
        words = ""
    except bp.Refused as r:
        words = r.words
    case("... and Start with it says to plug it in or press Change", "isn't plugged in" in words and "Change" in words, words)
    (w.home / "studio.json").write_text(keep, encoding="utf-8")
    sf.set_backup_place(str(w.gpapa / "CLIENT WORK" / "2026"))


# ---------------------------------------------------------------- the whole walk, in a hidden Chrome

BOX = ("(() => { const q = s => document.querySelector(s), t = s => (q(s) || {}).innerText || ''; return {open: !q('#bk').hidden, sub: t('#bkS'), card: t('#bkCard'), drive: t('#bkDrive'), "
       "driveCls: (q('#bkDrive') || {}).className || '', drives: [...document.querySelectorAll('#bkDrives .dv')].map(b => b.innerText.replace(/\\s+/g, ' ').trim()), "
       "lab: [...document.querySelectorAll('#bkTop .bklab')].map(x => x.textContent), notes: [...document.querySelectorAll('#bkTop .bknote')].filter(x => !x.hidden).map(x => x.textContent), "
       "go: q('#bkGo') ? {disabled: q('#bkGo').disabled, text: q('#bkGo').textContent, why: q('#bkGo').parentElement.querySelector('small').textContent} : null, "
       "rows: [...document.querySelectorAll('#bkFl .bkfrow')].map(r => r.dataset.in), crumbs: [...document.querySelectorAll('.bkcrumbs button')].map(b => b.textContent), "
       "find: !!q('#bkFind'), here: t('#bkHere'), newf: t('#bkNew'), naming: t('#bkNaming'), second: t('#bkSecond'), who: !!q('#bkWho'), msg: q('#bkMsg') && !q('#bkMsg').hidden ? t('#bkMsg') : '', "
       "prog: t('#bkProg'), recent: [...document.querySelectorAll('#bkL .bkr')].map(r => r.innerText.replace(/\\s+/g, ' ').trim()), recentLab: !q('#bkLab').hidden, "
       "foldline: t('.bkfoldline')}; })()")
CARD = "(() => { const n = document.getElementById('n1'); return {text: n.innerText.replace(/\\s+/g, ' ').trim(), bar: (n.querySelector('.bar2 i') || {style: {}}).style.width || '', " \
       "bold: [...n.querySelectorAll('b, .nw')].map(x => x.textContent), nwWeight: n.querySelector('.nw') ? getComputedStyle(n.querySelector('.nw')).fontWeight : '', " \
       "link: (n.querySelector('button[data-bk]') || {}).textContent || ''}; })()"
TOAST = "(() => { const t = document.getElementById('bkToast'); return {on: t.classList.contains('on'), text: t.textContent}; })()"


def box(c):
    return c.js(BOX)


def open_box(c):
    c.click("#s1 .n")
    c.wait_for("!document.getElementById('bk').hidden && !!document.getElementById('bkCard')", 15)
    time.sleep(0.15)


def check_browser(c, w, shot=None):
    w.job()
    (w.home / "studio.json").unlink()
    c.open(w.url("/home"))
    c.wait_for("!!document.getElementById('s1') && !!document.getElementById('bk')", 20)
    idle = c.js(CARD)
    case("the home card with a card in and nothing running: as it always was", "A card is in" in idle["text"] and "EOS_DIGITAL" in idle["text"], idle)
    case("See all my backups is a link on the card, to the list", c.js("(() => { const a = document.getElementById('seeAll'); return a.getAttribute('href') + '|' + a.textContent; })()") == "/backups|See all my backups")
    open_box(c)
    b = box(c)
    case("tapping Back up a card opens her box, on the home page", b["open"] and c.js("location.pathname") == "/home" and c.js("document.getElementById('bkT').textContent") == "Back up a card")
    case("... her safety words, then her line in bold on its own", "The Assistant copies every photo on your card to your drive" in b["sub"] and "✓ Nothing on your card is ever changed or deleted." in b["sub"]
         and int(c.js("getComputedStyle(document.querySelector('#bkS .bksafe')).fontWeight")) >= 700, b["sub"])
    case("... the card as a picture: its name and about how many files", "EOS_DIGITAL" in b["card"] and "Your card · about 5 files" in b["card"] and c.count("#bkCard .bksd") == 1, b["card"])
    case("... the first time, the drive is an empty dashed \"Pick a drive\"", "Pick a drive" in b["drive"] and "Where your backups go" in b["drive"] and " e" in b["driveCls"]
         and c.js("getComputedStyle(document.getElementById('bkDrive')).borderTopStyle") == "dashed", b["drive"])
    case("... \"Where should your backups go?\" with their drives by name and room", b["lab"][:1] == ["Where should your backups go?"] and b["drives"] == ["G PAPA 1.2 TB free →", "LaCie 840 GB free →"], (b["lab"], b["drives"]))
    case("... her \"only this once\" line", "This is the only thing it asks, and only this once. After that it remembers, and you can change it here anytime." in b["notes"], b["notes"])
    case("... Start is grey until there is a place: \"Pick where it goes first.\"", b["go"] == {"disabled": True, "text": "Start the backup", "why": "Pick where it goes first."}, b["go"])
    case("... \"Back up a folder instead\" under it", "Photos that aren’t on a card, like from a phone or a download?" in b["foldline"] and "Back up a folder instead" in b["foldline"], b["foldline"])
    case("... no test-only line, no list of backups the first time", "Test only" not in c.js("document.getElementById('bk').innerText") and not b["recentLab"])
    if shot:
        c.screenshot("popup-1-first.png")
    # the folder, like Finder
    c.click("#bkDrives .dv[data-d='0']")
    c.wait_for("document.querySelectorAll('#bkFl .bkfrow').length > 3", 15)
    b = box(c)
    case("picking a drive asks \"Which folder on G PAPA?\"", "Which folder on G PAPA?" in b["lab"] and "G PAPA" in b["drive"] and "Now pick a folder" in b["drive"], (b["lab"], b["drive"]))
    case("... its folders, by name, and none it must never show", "CLIENT WORK" in b["rows"] and "The Assistant" in b["rows"] and not [r for r in b["rows"] if r.startswith((".", "_", "$")) or r.endswith(".photoslibrary") or "link" in r], b["rows"])
    case("... a path at the top, a Find a folder box, and + New folder", b["crumbs"] == ["G PAPA"] and b["find"] and b["newf"] == "+ New folder", (b["crumbs"], b["find"], b["newf"]))
    case("... at the top of the drive there is no \"Put my backups in\" yet: a folder is asked for", not b["here"] and b["go"]["why"] == "Pick a folder first.", (b["here"], b["go"]))
    c.click("#bkFind")
    c.type_text("client")
    time.sleep(0.2)
    b = box(c)
    case("Find a folder narrows the list as they type, and keeps the cursor in the box", b["rows"] == ["CLIENT WORK", "CLIENT WORK 25"] and c.js("document.activeElement.id") == "bkFind", b["rows"])
    c.click("#bkFl .bkfrow[data-in='CLIENT WORK']")
    c.wait_for("document.querySelectorAll('.bkcrumbs button').length === 2 && document.querySelectorAll('#bkFl .bkfrow').length >= 4", 15)
    b = box(c)
    case("tapping a folder opens it: G PAPA › CLIENT WORK, and what is inside", b["crumbs"] == ["G PAPA", "CLIENT WORK"] and "2026" in b["rows"] and b["here"] == "Put my backups in CLIENT WORK"
         and b["newf"] == "+ New folder in CLIENT WORK", b)
    case("... her note about what lands in here", "Each shoot gets its own folder in here, named your way, right next to your other shoots." in b["notes"])
    if shot:
        c.screenshot("popup-2-folder.png")
    c.click("#bkNew")
    c.wait_for("!!document.getElementById('bkName') && document.activeElement.id === 'bkName'", 10)
    c.type_text("Fall minis")
    c.key("Enter")
    c.wait_for("document.querySelectorAll('.bkcrumbs button').length === 3", 15)
    b = box(c)
    case("+ New folder: type a name, Make it, and it opens the new folder", b["crumbs"] == ["G PAPA", "CLIENT WORK", "Fall minis"] and (w.gpapa / "CLIENT WORK" / "Fall minis").is_dir()
         and b["here"] == "Put my backups in Fall minis", b)
    c.click(".bkcrumbs button[data-up='1']")
    c.wait_for("document.querySelectorAll('.bkcrumbs button').length === 2 && document.querySelectorAll('#bkFl .bkfrow').length >= 5", 15)
    case("the path at the top goes back up", "Fall minis" in box(c)["rows"])
    c.click("#bkNew")
    c.wait_for("!!document.getElementById('bkName')", 10)
    c.key("Escape")
    time.sleep(0.2)
    case("Escape in the new folder's name box only closes that box, not the whole thing", box(c)["open"] and not c.js("!!document.getElementById('bkName')"))
    case("nothing is saved while they are still picking", w.session() is None)
    c.click("#bkHere")
    c.wait_for("!!document.getElementById('bkChange')", 10)
    b = box(c)
    case("\"Put my backups in CLIENT WORK\": the drive box shows G PAPA, the folder, and Change", "G PAPA" in b["drive"] and "CLIENT WORK" in b["drive"] and "Change" in b["drive"] and c.count("#bkDrive .bkfo") == 1, b["drive"])
    case("... one line says how the shoot folders are named, with Change", b["naming"].startswith("Each shoot gets its own folder inside CLIENT WORK, named Shoot name_Date") and "Change" in b["naming"], b["naming"])
    case("... the optional \"What would you like to name this shoot?\" box, with her note",
         b["who"] and "Optional. Leave it blank if there's more than one shoot on this card: you'll name them after." in c.js("document.querySelector('.bkwho').innerText")
         and c.js("document.getElementById('bkWho').placeholder") == "Shoot name")
    case("... \"+ Also save a second copy on another drive\"", b["second"] == "+ Also save a second copy on another drive", b["second"])
    case("... Start is ready: \"No need to wait. Keep working while it backs up.\"", b["go"] == {"disabled": False, "text": "Start the backup", "why": "No need to wait. Keep working while it backs up."}, b["go"])
    case("... and still nothing is saved: only Start saves it", w.session() is None)
    c.click("#bkNs")
    c.wait_for("!!document.getElementById('bkWays')", 10)
    ways = c.js("[...document.querySelectorAll('#bkWays button')].map(b => b.innerText.replace(/\\s+/g, ' ').trim())")
    case("Change shows only the two ways, each with an example in the real spelling", len(ways) == 2 and re.fullmatch(r"Shoot name_Date Like Aurora_\d\d-\d\d-\d\d", ways[0])
         and re.fullmatch(r"Date Shoot name Like \d{4}-\d\d-\d\d Aurora", ways[1]) and "It remembers this. You can always rename a shoot after." in box(c)["notes"], ways)
    c.click("#bkWays button[data-ns='2']")
    c.wait_for("document.getElementById('bkNaming').innerText.includes('Date Shoot name')", 10)
    case("... picking one is remembered at once", (w.studio().get("naming") or {}).get("folder_pattern") == "{date} {shoot}" and w.session() is None)
    c.click("#bkWays button[data-ns='1']")
    c.wait_for("document.getElementById('bkNaming').innerText.includes('Shoot name_Date')", 10)
    c.click("#bkWho")
    c.type_text("Aurora")
    c.click("#bkAdd2")
    c.wait_for("!!document.getElementById('bkNo2')", 10)
    b = box(c)
    case("one tap: \"A second copy goes to LaCie, in the same folders\" with Remove", b["second"].startswith("A second copy goes to LaCie, in the same folders") and "Remove" in b["second"], b["second"])
    case("... and what they typed for the shoot's name is still there", c.js("document.getElementById('bkWho').value") == "Aurora")
    if shot:
        c.screenshot("popup-3-ready.png")
    c.click("#bkChange")
    c.wait_for("!!document.getElementById('bkDrives')", 10)
    b = box(c)
    case("Change clears everything: back to the empty \"Pick a drive\", nothing selected, Start grey, no second copy",
         "Pick a drive" in b["drive"] and b["go"]["disabled"] and not b["second"] and not b["naming"] and c.count("#bkDrives .dv.on") == 0, b)
    # again, and Start
    c.click("#bkDrives .dv[data-d='0']")
    c.wait_for("document.querySelectorAll('#bkFl .bkfrow').length > 3", 15)
    c.click("#bkFl .bkfrow[data-in='CLIENT WORK']")
    c.wait_for("document.querySelectorAll('.bkcrumbs button').length === 2 && document.querySelectorAll('#bkFl .bkfrow').length >= 4", 15)
    time.sleep(0.2)
    c.click("#bkHere")
    c.wait_for("!!document.getElementById('bkAdd2')", 10)
    c.click("#bkAdd2")
    c.wait_for("!!document.getElementById('bkNo2')", 10)
    case("(the shoot's name they typed is kept through Change: it is about the shoot, not the place)", c.js("document.getElementById('bkWho').value") == "Aurora")
    n = len(w.calls())
    c.click("#bkGo")
    c.wait_for("document.getElementById('bk').hidden", 15)
    exact = str((w.gpapa / "CLIENT WORK").resolve())
    calls = w.calls()
    case("Start the backup: the box closes and the job is asked once, with the exact folder, the second drive and the name",
         len(calls) == n + 1 and calls[-1] == {"source": str(w.card), "dest": exact, "second": str(w.lacie), "shoot_name": "Aurora"}, calls[-1:])
    case("... where backups go is saved now, exactly that folder; the second drive is not saved", w.session() == exact and "second" not in w.studio()["drives"], w.studio().get("drives"))
    t = c.js(TOAST)
    case("... a note at the bottom of the screen says what is going where, and promises no notification",
         t["on"] and t["text"].startswith("Backing up EOS_DIGITAL to G PAPA › CLIENT WORK + LaCie.") and "No need to wait: keep working." in t["text"] and "lets you know" not in t["text"], t)
    cd = c.js(CARD)
    case("the home card shows how it is going: \"Copying and checking (0 of 5)\" and bold \"No need to wait. Keep working.\"",
         "Copying and checking (0 of 5)" in cd["text"] and "No need to wait. Keep working." in cd["bold"] and int(cd["nwWeight"]) >= 700, cd)
    w.job(state="running", step="copying", done=128, total=181, second="LaCie")
    c.wait_for("document.getElementById('n1').innerText.includes('128 of 181')", 15)
    cd = c.js(CARD)
    case("... it follows the job by itself: (128 of 181), and the thin bar has moved", "Copying and checking (128 of 181)" in cd["text"] and cd["bar"] == "71%", cd)
    if shot:
        c.screenshot("popup-4-running.png")
    open_box(c)
    b = box(c)
    case("tapping the card while it runs reopens the box with the same two pictures and the progress",
         "EOS_DIGITAL" in b["card"] and "G PAPA" in b["drive"] and "CLIENT WORK" in b["drive"] and "Copying and checking (128 of 181)" in b["prog"] and b["go"] is None, b)
    case("... its steps: Copying and checking, Sorting into shoots, Making your second copy, Done", re.sub(r"\s+", " ", c.js("document.querySelector('#bkProg .bksteps').innerText")).strip()
         == "Copying and checking · Sorting into shoots · Making your second copy · Done")
    case("... \"No need to wait here\", and nothing that promises to let them know", b["sub"].startswith("No need to wait here. Close this and keep working") and "No need to wait here." in b["prog"]
         and "lets you know" not in c.js("document.getElementById('bk').innerText"), (b["sub"], b["prog"]))
    case("... no Change and no Start while it runs", not c.js("!!document.getElementById('bkChange')") and "And a second copy on LaCie" in c.js("document.getElementById('bkTop').innerText"))
    w.job(state="running", step="sorting", done=181, total=181, second="LaCie")
    c.wait_for("document.getElementById('bkProg').innerText.includes('Sorting into shoots') && document.getElementById('n1').innerText.includes('Sorting into shoots')", 15)
    case("then \"Sorting into shoots\", on the card and in the box", "Almost done" in c.js(CARD)["text"])
    w.job(state="running", step="second", done=181, total=181, second="LaCie")
    c.wait_for("document.getElementById('n1').innerText.includes('Making your second copy')", 15)
    case("then \"Making your second copy\", since one was asked for", "LaCie" in c.js(CARD)["text"])
    c.key("Escape")
    time.sleep(0.2)
    case("Escape closes the box; the backup carries on", not box(c)["open"] and c.js("document.activeElement.id") == "s1")
    rec = w.records(where=w.gpapa / "CLIENT WORK")
    w.job(state="done", step="done", done=181, total=181, second="LaCie", shoots=3, records=str(rec), finished=datetime.now().isoformat(timespec="seconds"))
    c.wait_for("document.getElementById('n1').innerText.includes('Done.')", 15)
    cd = c.js(CARD)
    case("Done: \"Done. Every photo checked.\" on the card, in green", "Done. Every photo checked." in cd["text"] and c.js("getComputedStyle(document.querySelector('#n1 .dn')).color") == "rgb(47, 125, 86)", cd)
    case("... \"We found 3 shoots on your card · Name them\"", "We found 3 shoots on your card · Name them" in cd["text"] and cd["link"] == "Name them", cd)
    t = c.js(TOAST)
    case("... and the note: \"Your card is backed up. Every photo checked. Your 3 shoots are backed up.\"", t["on"] and t["text"] == "Your card is backed up. Every photo checked. Your 3 shoots are backed up.", t)
    case("... nothing on the page says the shoots are in an editing queue", "in your editing queue" not in c.js("document.body.innerText"))
    if shot:
        c.screenshot("popup-5-done.png")
    c.click("#n1 button[data-bk='name']")
    time.sleep(1.2)
    case("Name them, while the naming page is not there: it falls back to the report (here, its plain line), and the box stays shut",
         c.js("location.pathname") in ("/home", "/name-shoots.html") and (c.js("location.pathname") != "/home" or (not box(c)["open"] and "report" in c.js("document.getElementById('n1').innerText").lower())),
         c.js("document.getElementById('n1').innerText"))
    if c.js("location.pathname") != "/home":
        c.open(w.url("/home"))
    c.reload()
    c.wait_for("!!document.getElementById('s1') && !!document.getElementById('bk')", 20)
    cd = c.js(CARD)
    case("after a reload the card still says Done (the server draws it from the job's own record)", "Done. Every photo checked." in cd["text"] and cd["link"] == "Name them", cd)
    # the next time: filled in
    w.queue(rec)
    time.sleep(0.3)
    c.reload()
    c.wait_for("!!document.getElementById('s1') && !!document.getElementById('bk')", 20)
    open_box(c)
    b = box(c)
    case("after the first time the box opens filled in: G PAPA and CLIENT WORK, Start ready", "G PAPA" in b["drive"] and "CLIENT WORK" in b["drive"] and b["go"]["disabled"] is False and not b["drives"], b)
    case("... the second copy is asked again each time, never remembered", b["second"] == "+ Also save a second copy on another drive", b["second"])
    case("... the last backup said Done at the top, with what to do next", "Done. Every photo checked." in b["prog"] and "It’s safe to format your card." in b["prog"] and "Your 3 shoots are backed up." in b["prog"], b["prog"])
    case("... the last few backups and See all my backups at the bottom", b["recentLab"] and len(b["recent"]) == 1 and "2 shoots · 181 photos, every one checked" in b["recent"][0]
         and c.js("document.querySelector('#bkLab a').getAttribute('href')") == "/backups", b["recent"])
    c.click("#bkChange")
    c.wait_for("!!document.getElementById('bkDrives')", 10)
    case("... Change, after the first time: \"Where should it go?\" and \"It remembers what you pick for next time.\"", box(c)["lab"][:1] == ["Where should it go?"]
         and "It remembers what you pick for next time." in box(c)["notes"], box(c)["lab"])
    case("... and Change alone changes nothing that is saved", w.session() == exact)
    c.click((5, 5))
    time.sleep(0.2)
    case("a press outside closes the box", not box(c)["open"])
    # a backup that stopped
    w.job(state="problem", step="copying", done=40, total=181, line="Your memory card stopped answering. Take the card out, put it back in.", finished=datetime.now().isoformat(timespec="seconds"))
    c.wait_for("document.getElementById('n1').innerText.includes('stopped answering')", 15)
    cd = c.js(CARD)
    case("a backup that stopped: plain words on the card, and what to do", "Your memory card stopped answering." in cd["text"] and "Start the backup again" in cd["text"]
         and c.js("getComputedStyle(document.querySelector('#n1 .bad')).color") != "rgb(47, 125, 86)", cd)
    w.job()
    # no card in: the dashed box, and a card that shows up by itself
    w.drives(card=False)
    c.reload()
    c.wait_for("!!document.getElementById('s1') && !!document.getElementById('bk')", 20)
    open_box(c)
    b = box(c)
    case("no card in: the card picture is an empty dashed \"Put your card in\", and Start waits", "Put your card in" in b["card"] and "It shows up here by itself" in b["card"]
         and b["go"] == {"disabled": True, "text": "Start the backup", "why": "Put your card in first."}, b)
    w.drives(card=True)
    c.wait_for("document.getElementById('bkCard').innerText.includes('EOS_DIGITAL')", 20)
    case("... the card shows up by itself when it goes in, and Start is ready", box(c)["go"]["disabled"] is False)
    c.key("Escape")
    # no external drive: the two choices, in plain words
    w.drives(gpapa=False, lacie=False)
    (w.home / "studio.json").unlink()
    c.reload()
    c.wait_for("!!document.getElementById('s1') && !!document.getElementById('bk')", 20)
    open_box(c)
    b = box(c)
    two = c.js("[...document.querySelectorAll('#bkDrives .bktwo button')].map(b => b.textContent)")
    case("no external drive: the two choices, in plain words", "I don't see an external drive. Where should your backups go?" in c.js("document.getElementById('bkDrives').innerText")
         and len(two) == 2 and two[0] == "I'll plug one in" and two[1].startswith("On this ") and two[1].endswith(" for now"), two)
    c.click("#bkPlug")
    time.sleep(0.2)
    case("\"I'll plug one in\": it waits, and says the drive shows up by itself", "Plug it in and it shows up here by itself." in box(c)["notes"])
    w.drives(gpapa=True, lacie=False)
    c.wait_for("document.querySelectorAll('#bkDrives .dv').length === 1", 20)
    case("... and it does", box(c)["drives"] == ["G PAPA 1.2 TB free →"])
    w.drives(gpapa=False, lacie=False)
    c.wait_for("!!document.getElementById('bkComputer')", 20)
    c.click("#bkComputer")
    c.wait_for("!!document.getElementById('bkChange')", 10)
    b = box(c)
    case("\"On this Mac for now\": the drive box says this computer, and where", b["drive"].startswith("This ") and "In Shoots, inside Pictures" in b["drive"] and b["go"]["disabled"] is False, b["drive"])
    case("... nothing is saved until Start", w.session() is None)
    c.key("Escape")
    w.drives()
    # phone width
    c.cdp("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 800, "deviceScaleFactor": 1, "mobile": False})
    c.reload()
    c.wait_for("!!document.getElementById('s1') && !!document.getElementById('bk')", 20)
    open_box(c)
    case("at phone width the box fits: nothing scrolls sideways", c.js("document.documentElement.scrollWidth <= window.innerWidth + 1 && document.querySelector('.bkbox').scrollWidth <= document.querySelector('.bkbox').clientWidth + 1"))
    c.cdp("Emulation.clearDeviceMetricsOverride", {})
    errs = [e for e in (c.page_errors() if hasattr(c, "page_errors") else [])]
    case("no error on the page through all of it", not errs, errs[:3])


def check_backups_page(c, w):
    w.queue(w.records(where=w.gpapa / "CLIENT WORK"))
    c.open(w.url("/backups"))
    c.wait_for("document.querySelectorAll('#backups .shoot').length >= 1 || !!document.querySelector('#backups .empty')", 20)
    time.sleep(0.3)
    d = c.js("(() => ({h1: document.querySelector('h1').textContent, title: document.title, steps: !!document.querySelector('.steps'), paste: !!document.querySelector('.paste'), "
             "text: document.body.innerText, btns: [...document.querySelectorAll('#backups .shoot')].slice(0, 1).map(s => [...s.querySelectorAll('.acts button')].map(b => b.textContent + '|' + b.className)), "
             "shoots: document.querySelectorAll('#backups .shoot').length, find: !!document.getElementById('find')}))()")
    case("Your backups: \"Your backups.\" and the list draws (no script error from the card line that went)", d["h1"] == "Your backups." and d["shoots"] == 2 and d["find"], d)
    case("... nothing else: no steps, nothing to paste, no \"backup now\"", not d["steps"] and not d["paste"] and "backup now" not in d["text"] and "Paste this" not in d["text"], d["text"][:300])
    case("... See the report is the main button on each shoot, Open this folder under it", d["btns"] == [["See the report|btn solid", "Open this folder|btn"]], d["btns"])
    y = c.js("(() => { const b = document.querySelectorAll('#backups .shoot .acts button'); return [b[0].getBoundingClientRect().top, b[1].getBoundingClientRect().top]; })()")
    case("... and it really sits above it", y[0] < y[1], y)


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder under /private/tmp for this run, kept afterwards")
    ap.add_argument("--port", type=int, default=9860)
    ap.add_argument("--no-chrome", action="store_true")
    ap.add_argument("--shot", action="store_true", help="keep screenshots of the box (popup-*.png) in the work folder; use with --work")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8790, 8791, 8792, 8799) for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    tmp = "/private/tmp" if os.path.isdir("/private/tmp") else None
    base = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="backup-popup-check-", dir=tmp)).resolve()
    work = base / time.strftime("run-%H%M%S")
    work.mkdir(parents=True)
    w = World(work, a.port)
    for k in ("STUDIO_HOME", "STUDIO_NO_WINDOWS_FOR_TESTS", "STUDIO_DRIVES_FOR_TESTS", "STUDIO_FOLDERS_FOR_TESTS", "STUDIO_BACKUP_JOB_FOR_TESTS", "STUDIO_SAMPLES_FOR_TESTS",
              "STAND_IN_DRIVE", "ASSISTANT_TEST_OPEN"):
        os.environ[k] = w.env[k]
    os.environ.pop("STUDIO_CARD_FOR_TESTS", None)
    os.environ.pop("STUDIO_PICK_FOLDER_FOR_TESTS", None)
    try:
        w.build()
        sys.path.insert(0, str(SCRIPTS))
        import backup_popup
        import studio_file
        case("the test's own scratch home, never the real one", Path(backup_popup.HOME) == w.home and Path(studio_file.HOME) == w.home and ".studio" not in str(backup_popup.HOME))
        group("the words and the pages", check_words, w)
        w.start()
        group("what the box is told", check_state, w)
        group("the folder browser's guards, by request", check_guards, w)
        group("+ New folder", check_new_folder, w)
        group("the naming", check_naming, w)
        group("Start the backup", check_start, w)
        group("the writer's own checks", check_writer, w)
        group("the job, as the card says it", check_job, w)
        group("Back up a folder instead, and the folder window", check_folder_source, w)
        group("no external drive", check_computer, w)
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the box in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work), size=(1440, 900)) as c:
                group("the whole walk in a browser", check_browser, c, w, a.shot)
                (w.home / "studio.json").write_text(json.dumps({"drives": {"session": str((w.gpapa / "CLIENT WORK").resolve())}}), encoding="utf-8")
                group("Your backups in a browser", check_backups_page, c, w)
    finally:
        w.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(base), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
