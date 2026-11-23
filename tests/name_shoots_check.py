#!/usr/bin/env python3
"""Name your shoots: the page after a backup (name_shoots.py; Nicole's v31 section 6, screenshots 09 and 10; her
answers of Nov 23), and the report's way in to it.

    python3 tests/name_shoots_check.py                                             the routes, the job, the report
    python3 tests/guard.py 3000 python3 tests/name_shoots_check.py --chrome        also the page itself in a hidden Chrome

What it holds: the page and its data by a backup's NAME (never a path, in or out); her words whole, with the three
that are no longer true replaced and named; each shoot's three pictures, when, how many and its name; the
"safe to format" line only when the backup's own records say so; every POST through the same-page-only guard and
checked field by field; two shoots that would share a folder, and a folder name already taken, refused in plain
words before anything is renamed; Save the names as ONE background job that outlives the page server, one shoot
at a time, its record true after a restart, and a job whose process died said to have stopped, never "working"
for ever; mini sessions joined through join_shoots.py; the report's "Put these shoots in one folder".

Everything is pretend: a scratch STUDIO_HOME, pretend drives and cards, whole pretend backups made by night.py, a
page server on a scratch port with STUDIO_NO_WINDOWS_FOR_TESTS. Nothing of the real ~/.studio, no /Volumes.
"""
import http.client
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# Nothing here may ever look at the real ~/.studio: even the modules this test imports itself get a scratch home
# (every script it runs gets its own pretend world's on top of this).
os.environ["STUDIO_HOME"] = tempfile.mkdtemp(prefix="scratch-studio-home-")
os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
import report_options_check as r  # noqa: E402
t = r.t
sys.path.insert(0, str(t.SCRIPTS))

FAILED = []
N = [0]
HERS = HERE.parent.parent / "hf-tools" / "reference-private" / "nicole-handoff-v31-2026-11-22" / "The Assistant - handoff v31"


def check(what, ok, detail=""):
    N[0] += 1
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {str(detail)[-900:]}"), flush=True)
    if not ok:
        FAILED.append(what)


def jread(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


class Server:
    def __init__(self, w, **extra):
        self.w, self.proc, self.port, self.extra = w, None, None, extra     # extra: more environment for the server and its jobs

    def start(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port0 = s.getsockname()[1]
        f = self.w["home"] / "posting-url.txt"
        if f.exists():
            f.unlink()
        kw = {"creationflags": 0x00000200} if os.name == "nt" else {"start_new_session": True}
        self.proc = subprocess.Popen([sys.executable, str(t.SCRIPTS / "posting_queue.py"), "serve", "--port", str(port0)],
                                     env=t.child_env(dict(self.w["env"], **self.extra)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
        end = time.time() + 40
        while time.time() < end and not (f.exists() and f.read_text(encoding="utf-8").strip()):
            time.sleep(0.1)
        self.port = int(re.search(r":(\d+)/", f.read_text(encoding="utf-8")).group(1))
        end = time.time() + 40
        while time.time() < end:
            try:
                if self.http("GET", "/name-shoots.html?backup=x")[0] in (200, 404):
                    return
            except OSError:
                time.sleep(0.1)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def http(self, method, path, body=None, headers=None, raw=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        try:
            h = dict(headers or {})
            data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
            if data is not None:
                h.setdefault("Content-Type", "application/json")
            c.request(method, path, body=data, headers=h)
            x = c.getresponse()
            return x.status, x.read()
        finally:
            c.close()

    def json(self, method, path, body=None, **kw):
        code, raw = self.http(method, path, body, **kw)
        try:
            return code, json.loads(raw.decode("utf-8"))
        except ValueError:
            return code, {"not json": raw[:200].decode("utf-8", "replace")}

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"


def no_path(w, text):
    text = text if isinstance(text, str) else json.dumps(text)
    return (str(w["base"]) not in text and str(Path(w["base"]).resolve()) not in text and "/Volumes" not in text
            and str(Path(tempfile.gettempdir())) not in text and "\\\\" not in text)


def wait_job(s, q, limit=120):
    end = time.time() + limit
    d = {}
    while time.time() < end:
        code, d = s.json("GET", "/name-shoots-data" + q)
        if (d.get("job") or {}).get("state") != "working":
            return d
        time.sleep(0.2)
    return d


def save(s, name, names, mini=False, mini_name="", **kw):
    return s.json("POST", "/name-shoots-save", {"backup": name, "names": names, "mini": mini, "mini_name": mini_name}, **kw)


def world(work, name, groups=(5, 4, 3), shoots=("Shoot 1", "Shoot 2", "Shoot 3")):
    w = r.new_world(work, name)
    w["drive"] = r.new_drive(w, "G PAPA", 2000)
    (w["drive"] / "CLIENT WORK").mkdir()
    t.run("studio_file.py", "set", "--drive", w["drive"] / "CLIENT WORK", "--offered", "1", "--file-names", "shoot", env=w["env"])
    b = r.a_backup(w, "CARD", "first card", r.DAY1, groups, list(shoots), w["drive"] / "CLIENT WORK")
    return w, b


# ---------------------------------------------------------------- the cases

def the_words():
    print("Her words, whole")
    import name_shoots
    W, O = name_shoots.WORDS, name_shoots.OUR_WORDS
    page = name_shoots.page_html("a backup")
    for k in ("found", "mini", "placeholder", "mini_placeholder", "mini_default", "save", "later", "another", "another_note", "see_all"):
        check(f"the page carries her line: {W[k][:60]}", json.dumps(W[k], ensure_ascii=False)[1:-1] in page, k)
    text = " ".join(list(W.values()) + list(O.values()))
    check("never 'client name', 'your assistant' or 'Claude' in any line; no example name like Smith",
          "client" not in text.lower() and "your assistant" not in text.lower() and "Claude" not in text and "Smith" not in text)
    check("no em dash, no 'she' or 'he' in our words", "—" not in text and " she " not in f" {text.lower()} " and " he " not in f" {text.lower()} ")
    check("no web font and nothing loaded from the internet", "http://" not in page and "https://" not in page and "@import" not in page)
    check("the three lines of hers that are no longer true are named, each with its reason, and are not on the page for someone whose photos take the shoot's name",
          len(name_shoots.HERS_NOT_TRUE) == 3 and "in your editing queue" not in page)
    mock = HERS / "pages" / "idea-naming-after-the-backup.html"
    if mock.is_file():
        hers = mock.read_text(encoding="utf-8")
        hers_all = hers + (HERS / "UPDATE-v31.md").read_text(encoding="utf-8")
        for k in ("mini", "placeholder", "mini_placeholder", "save", "later", "keep_names", "another", "another_note", "see_all"):
            check(f"her own file has this line word for word: {W[k][:50]}", W[k] in hers, k)
        check("her safe line, her found line and her mini lines match her file but for the names filled in",
              "Every photo is checked and safe on " in hers and "It's safe to format your card." in hers
              and "shoots on your card, sorted by when you took them. Give each one a name, or do it later." in hers
              and "photos, together" in hers and "'Mini sessions'" in hers and "Folder: " in hers)
        check("each line of hers we do not use is in her file", all(k in hers_all for k in name_shoots.HERS_NOT_TRUE))
    else:
        print("  SKIP  her own file is not on this computer (the comparison runs where her handoff is)")


def the_instructions():
    print("The Assistant's instructions")
    skill = HERE.parent / "plugins" / "the-engine" / "skills" / "studio-manager"
    part = (skill / "parts" / "after-the-report.md").read_text(encoding="utf-8")
    core = (skill / "SKILL.md").read_text(encoding="utf-8")
    at = part.find("## Naming the shoots after the backup, and putting shoots in one folder")
    sec = part[at:part.find("\n## ", at + 5)] if at >= 0 else ""
    check("after-the-report.md has the section on naming after the backup and joining", bool(sec))
    for words in ("name_shoots.py url", "join_shoots.py \"<the backup's folder>\" --list", "--shoots s1 s2", "--all --name \"Mini sessions\"",
                  "--dry-run", "--finish", "join the two beach shoots", "never \"client name\"", "Exit 2 is a refusal", "Exit 1 is a stop part way",
                  "never move or rename anything by hand", "Shoots from two different backups can't be joined yet",
                  "Taking a joined shoot apart again is not built", "Take it out of your queue first"):
        check(f"it says: {words[:60]}", words in sec, words)
    check("it never tells the Assistant to say the photos keep their own names to someone whose photos take the shoot's name",
          "Never say \"your photos keep their own names\" to anyone else" in sec)
    check("no 'your assistant', no 'Claude', no em dash in the section", "your assistant" not in sec.lower() and "Claude" not in sec and "—" not in sec)
    row = next((ln for ln in core.splitlines() if "join the two beach shoots" in ln), "")
    check("the core's table sends naming and joining to that section",
          "parts/after-the-report.md" in row and "Name them" in row and "mini sessions" in row, row)
    desc = core.split("---")[1] if core.startswith("---") else ""
    check("the core's description was not touched (still under its limit)", 0 < len(desc) < 1200 and "join" not in desc.lower())


def the_routes(work):
    print("The page and what it draws from")
    w, b = world(work, "routes")
    if not b:
        return
    st = b["records"]
    name = b["session"]
    q = "?backup=" + quote(name)
    s = Server(w)
    s.start()
    try:
        code, raw = s.http("GET", "/name-shoots.html" + q)
        page = raw.decode("utf-8")
        check("the page opens for a backup by its name", code == 200 and "Name your <em>shoots</em>" in page and json.dumps(name) in page)
        check("the page itself holds no path", str(w["base"]) not in page and str(Path(w["base"]).resolve()) not in page and "/Volumes" not in page)
        code, raw = s.http("GET", "/name-shoots.html?backup=no%20such%20backup")
        check("a backup it does not know: 404, with a plain line, not an error page", code == 404 and "I can&#x27;t find that backup." in raw.decode("utf-8"), raw[:300])
        for bad in ("../" + name, str(st), "/etc", ".."):
            code, d = s.json("GET", "/name-shoots-data?backup=" + quote(bad, safe=""))
            check(f"a path where a name belongs finds nothing ({bad[:12]}...)", code == 404 and d.get("ok") is False and no_path(w, d), d)
        code, d = s.json("GET", "/name-shoots-data" + q)
        check("the data: three shoots by id, in shooting order", code == 200 and d.get("ok") and [x["id"] for x in d["shoots"]] == ["s1", "s2", "s3"], d)
        check("the data holds no path anywhere", no_path(w, d))
        check("her safe line, with the drive and the folder on it, because every file's copy is checked",
              d.get("safe") is True and d.get("safe_line") == "✓ Every photo is checked and safe on G PAPA › CLIENT WORK. It's safe to format your card.", d.get("safe_line"))
        s1 = d["shoots"][0]
        check("each shoot: when it was taken in her shape, how many, its folder now, three pictures",
              s1["when"] == "Thursday 9:00 to 9:03 am" and s1["count"] == "5 photos" and s1["folder"] == "Shoot 1_06-04-26" and s1["pics"] == 3, s1)
        check("a name nobody gave is not shown as theirs: the box starts empty", all(x["named"] == "" for x in d["shoots"]), d["shoots"])
        check("the folder pattern carries the photos' own date with dashes, and a mark where the name goes",
              s1["tpl"] == d["mark"] + "_06-04-26" and d["mini_tpl"] == d["mark"] + "_06-04-26", s1["tpl"])
        check("her 'All N photos, together' for mini sessions counts every shoot", d["mini_all"] == "All 12 photos, together", d["mini_all"])
        check("the note under the buttons is true: the photos take the first word of the name, shown with a real photo's camera name",
              "start with the first word of that name, like Name_0001_IMG_4471.JPG" in d["note"] and "Your photos keep their own names" not in d["note"], d["note"])
        code, raw = s.http("GET", "/name-shoots-pic" + q + "&shoot=s2&i=1")
        check("a picture is asked for by the shoot's id and 0, 1 or 2, and is a JPEG", code == 200 and raw[:2] == b"\xff\xd8", raw[:10])
        for bad in ("&shoot=s2&i=3", "&shoot=s9&i=0", "&shoot=s2&i=../manifest.json", "&shoot=s2"):
            check(f"anything else is not found ({bad})", s.http("GET", "/name-shoots-pic" + q + bad)[0] == 404)
        code, d2 = s.json("GET", "/name-shoots-data" + q, headers={"Sec-Fetch-Site": "cross-site"})
        check("another website's page gets nothing from the data", code == 403 and d2 == {"ok": False}, d2)
        check("nor a picture", s.http("GET", "/name-shoots-pic" + q + "&shoot=s1&i=0", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403)
        code, d2 = s.json("GET", "/name-shoots-data" + q, headers={"Host": "evil.example:80"})
        check("nor a request sent under another name", code in (403, 400) and "shoots" not in d2, d2)

        print("Save the names: what is refused")
        before = sorted(os.listdir(w["drive"] / "CLIENT WORK"))

        def refused(what, body, code_want, words=None, **kw):
            code, d = s.json("POST", "/name-shoots-save", body, **kw)
            check(f"{what}: refused ({code_want})" + (", in plain words" if words else ""),
                  (code in code_want if isinstance(code_want, tuple) else code == code_want) and d.get("ok") is False and (not words or words in d.get("words", "")) and no_path(w, d)
                  and sorted(os.listdir(w["drive"] / "CLIENT WORK")) == before and not list((w["home"] / "name-shoots").glob("*.json")), d)
        ok_body = {"backup": name, "names": {"s1": "Aurora"}, "mini": False, "mini_name": ""}
        refused("from another website (Origin)", ok_body, 403, headers={"Origin": "https://evil.example"})
        refused("from another website (Sec-Fetch-Site)", ok_body, 403, headers={"Sec-Fetch-Site": "cross-site"})
        refused("not JSON by type", ok_body, (400, 403, 415), headers={"Content-Type": "text/plain"})
        refused("a field too many", dict(ok_body, path="/tmp"), 400)
        refused("a field missing", {"backup": name, "names": {}}, 400)
        refused("a shoot that is not this backup's", dict(ok_body, names={"s9": "X"}), 400)
        refused("a name that is not text", dict(ok_body, names={"s1": 5}), 400)
        refused("a name far too long", dict(ok_body, names={"s1": "x" * 500}), 400)
        refused("a backup it does not know", dict(ok_body, backup="nope"), 404, "I can't find that backup.")
        refused("a path for a backup", dict(ok_body, backup=str(st)), 404)
        refused("two shoots given one name", dict(ok_body, names={"s1": "Aurora", "s2": "aurora"}), 200, "they would share a folder")
        refused("a name another shoot of this backup already has", dict(ok_body, names={"s1": "Shoot 2"}), 200, "Two shoots can't both be called Shoot 2")
        (w["drive"] / "CLIENT WORK" / "Katie_06-04-26").mkdir()
        before = sorted(os.listdir(w["drive"] / "CLIENT WORK"))
        refused("a folder of that name already there, from some other day's work", dict(ok_body, names={"s3": "katie"}), 200,
                "There is already a folder called Katie_06-04-26 next to these. Give katie another name.")
        os.rmdir(w["drive"] / "CLIENT WORK" / "Katie_06-04-26")

        print("Save the names: one job, one shoot at a time")
        code, d = save(s, name, {"s1": "  The   Aurora Family ", "s3": "Katie", "s2": "   "})
        check("the save is taken and answered at once", code == 200 and d == {"ok": True, "state": "working"}, d)
        code, d2 = save(s, name, {"s2": "Hannah"})
        d = wait_job(s, q)
        job = d.get("job") or {}
        check("it finishes, two of two (the empty box is left alone)", job.get("state") == "done" and job.get("done") == 2 and job.get("total") == 2, job)
        check("a second press while it works is told to wait, or is taken once the first is done; never two at once",
              d2.get("words") == "A rename or a join is already at work. Give it a moment." or d2.get("ok") is True, d2)
        if d2.get("ok"):
            d = wait_job(s, q)
            t.run("rename_shoot.py", st, "--shoot", "s2", "--name", "Shoot 2", env=w["env"])
            code, d = s.json("GET", "/name-shoots-data" + q)
        folders = [x["folder"] for x in d["shoots"]]
        check("the folders have their names, spaces tidied, the date kept", folders == ["The Aurora Family_06-04-26", "Shoot 2_06-04-26", "Katie_06-04-26"], folders)
        got = sorted(os.listdir(w["drive"] / "CLIENT WORK" / "The Aurora Family_06-04-26"))
        check("and the photos take the first word of the name (The passed over), numbers and camera names kept",
              got == [f"Aurora_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 6)], got)
        bad, n = t.photos_match(w["drive"] / "CLIENT WORK", jread(st / "index.json"), b["card"])
        check(f"every photo is still the card's, byte for byte ({n}), and the card is as it was", not bad and n == 12 and t.card_snapshot(b["card"]) == b["before"], bad)
        check("the names they gave now show in their boxes; the one they left does not",
              [x["named"] for x in d["shoots"]] == ["The Aurora Family", "", "Katie"], [x["named"] for x in d["shoots"]])
        rec = jread(next((w["home"] / "name-shoots").glob("*.json")))
        check("the job's record is kept by the Assistant (not in the backup's records), whole, with what was asked",
              rec.get("state") == "done" and rec.get("finished") and rec.get("ask", {}).get("names") == {"s1": "The Aurora Family", "s3": "Katie"}, rec)
        check("the report was built again with the new names", "The Aurora Family" in (st / "report.html").read_text(encoding="utf-8"))
        s.stop()
        s.start()
        code, d = s.json("GET", "/name-shoots-data" + q)
        check("after the page server starts again the page still knows the names were saved", (d.get("job") or {}).get("state") == "done", d.get("job"))

        print("A job that outlives the page server, and one whose process died")
        code, d = save(s, name, {"s2": "Hannah"})
        s.stop()                                   # the page and its server go away while the job works
        end = time.time() + 60
        f = next((w["home"] / "name-shoots").glob("*.json"))
        while time.time() < end and (jread(f) or {}).get("state") == "working":
            time.sleep(0.2)
        check("the job carried on with no page server and finished", (jread(f) or {}).get("state") == "done"
              and (w["drive"] / "CLIENT WORK" / "Hannah_06-04-26").is_dir(), jread(f))
        s.start()
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        rec = dict(jread(f), state="working", pid=dead.pid, started="2026-11-01T10:00:00", finished=None)
        f.write_text(json.dumps(rec), encoding="utf-8")
        code, d = s.json("GET", "/name-shoots-data" + q)
        job = d.get("job") or {}
        check("a job whose process is gone is said to have stopped, with what to do, never 'working' for ever",
              job.get("state") == "stopped" and job.get("line") == "This stopped before it was done. Nothing is lost. Press Save the names to try again.", job)
        # after a power cut and a restart, the dead job's number belongs to some other program that is alive
        f.write_text(json.dumps(dict(rec, pid=os.getppid() if os.name != "nt" else os.getpid())), encoding="utf-8")
        code, d = s.json("GET", "/name-shoots-data" + q)
        check("so is one whose number now belongs to another, living program: told by the job's own lock, never by its number",
              (d.get("job") or {}).get("state") == "stopped", d.get("job"))
        code, out = t.run("name_shoots.py", "status", st, env=w["env"])
        check("and the chat's status says the same", '"state": "stopped"' in out, out)
        rec = dict(rec, pid=None)
        f.write_text(json.dumps(rec), encoding="utf-8")
        code, d = s.json("GET", "/name-shoots-data" + q)
        check("so is one that never came up at all", (d.get("job") or {}).get("state") == "stopped", d.get("job"))
        code, d = save(s, name, {"s2": "Hannah"})
        d = wait_job(s, q)
        check("pressing Save again is taken and ends done", (d.get("job") or {}).get("state") == "done", d.get("job"))

        print("These are mini sessions. Keep them in one folder.")
        code, d = save(s, name, {}, mini=True, mini_name="")
        d = wait_job(s, q)
        check("the three shoots are one, in her default name's folder", (d.get("job") or {}).get("state") == "done"
              and [x["folder"] for x in d["shoots"]] == ["Mini sessions_06-04-26"], d)
        got = sorted(x for x in os.listdir(w["drive"] / "CLIENT WORK") if not x.startswith("."))
        inside = sorted(os.listdir(w["drive"] / "CLIENT WORK" / "Mini sessions_06-04-26")) if got == ["Mini sessions_06-04-26"] else []
        check("on the drive: one folder, the photos numbered on across all three in shooting order",
              inside == [f"Mini_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 13)], str(got) + str(inside))
        bad, n = t.photos_match(w["drive"] / "CLIENT WORK", jread(st / "index.json"), b["card"])
        check(f"every photo is still the card's, byte for byte ({n})", not bad and n == 12, bad)
        code, d = save(s, name, {}, mini=True, mini_name="Again")
        check("mini sessions with one shoot left has nothing to put together, and says so",
              d.get("ok") is False and d.get("words") == "There is only one shoot here, so there is nothing to put together.", d)

        print("The safe line only when the records say so")
        m = jread(st / "manifest.json")
        keep = json.dumps(m)
        m["sample"] = {"kept": 3, "of": 12}
        (st / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
        code, d = s.json("GET", "/name-shoots-data" + q)
        check("a sample is never called safe to format", d.get("safe") is False and "safe to format" not in d.get("safe_line", "") and "Keep your card" in d.get("safe_line", ""), d.get("safe_line"))
        m.pop("sample")
        m["problems"] = ["pretend"]
        time.sleep(0.02)
        (st / "manifest.json").write_text(json.dumps(m) + " ", encoding="utf-8")
        code, d = s.json("GET", "/name-shoots-data" + q)
        check("nor a backup with a problem on record", d.get("safe") is False and "safe to format" not in d.get("safe_line", "").replace("before you format", ""), d.get("safe_line"))
        (st / "manifest.json").write_text(keep, encoding="utf-8")
    finally:
        s.stop()
    return w, b


def cut_off_and_stuck(work):
    import name_shoots
    HALF = "This was cut off part way. Nothing is lost. Press Finish it and it will carry on."
    LOOK = "This stopped on something I can't sort out from this page. Nothing is lost. Tell the Assistant and it will take a look."
    check("a line that names a file of ours never reaches the page", name_shoots.plain("STOP: no shoot s2 in shoots.json.", "fallback") == "fallback"
          and name_shoots.plain("STOP: a folder named Katie_06-04-26 already exists. Nothing renamed.", "x").startswith("a folder named Katie"))

    def queue_of(w, st):
        return sorted(x["shoot"] for x in (jread(w["home"] / "queue.json", {}) or {}).get("shoots", [])
                      if Path(x.get("studio", "")).resolve() == Path(st).resolve())

    print("A mini-sessions join cut off right after its records were written")
    w, b = world(work, "cut-after")
    if b:
        st, name = b["records"], b["session"]
        q = "?backup=" + quote(name)
        s = Server(w, STUDIO_JOIN_CUT_FOR_TESTS="after-records")
        s.start()
        try:
            code, d = save(s, name, {}, mini=True, mini_name="Minis")
            d = wait_job(s, q)
            job = d.get("job") or {}
            check("the job is said to have been cut off, with the one thing to press", job.get("state") == "stopped" and job.get("line") == HALF and d.get("half") is True and d.get("stuck") is False, d)
            s.stop()
            s = Server(w)
            s.start()
            code, d = s.json("GET", "/name-shoots-data" + q)
            check("after the server starts again the page still knows it is half done", d.get("half") is True and (d.get("job") or {}).get("line") == HALF, d.get("job"))
            code, d = save(s, name, {})                    # what Finish it sends: no names, no tick
            check("Finish it is taken as a job, never answered 'done' with nothing run", code == 200 and d == {"ok": True, "state": "working"}, d)
            d = wait_job(s, q)
            e = (jread(st / "join-log.json", {}).get("joins") or [{}])[0]
            check("the job ends done, and the join really is finished in its log", (d.get("job") or {}).get("state") == "done" and e.get("finished") and not e.get("problems")
                  and d.get("half") is False, {k: v for k, v in e.items() if k != "moves"})
            check("the editing queue's list (what Your backups draws from) has the one joined shoot", queue_of(w, st) == ["s1"], queue_of(w, st))
            rep_ = (st / "report.html").read_text(encoding="utf-8")
            check("the report was built again with the joined shoot", "Minis" in rep_ and "Shoot 2" not in rep_)
            check("on the drive: the one folder", sorted(x for x in os.listdir(w["drive"] / "CLIENT WORK") if not x.startswith(".")) == ["Minis_06-04-26"])
        finally:
            s.stop()

    print("A mini-sessions join cut off before its records were written, then names sent by a page a step behind")
    w, b = world(work, "cut-before")
    if b:
        st, name = b["records"], b["session"]
        q = "?backup=" + quote(name)
        s = Server(w, STUDIO_JOIN_CUT_FOR_TESTS="moves:3")
        s.start()
        try:
            save(s, name, {}, mini=True, mini_name="Minis")
            d = wait_job(s, q)
            check("cut off part way: half done, nothing else offered", d.get("half") is True and (d.get("job") or {}).get("state") == "stopped", d.get("job"))
            s.stop()
            s = Server(w)
            s.start()
            code, d = save(s, name, {"s1": "Fam0", "s2": "Fam1", "s3": "Fam2"})
            d = wait_job(s, q)
            job = d.get("job") or {}
            check("names sent while a join is half done only finish the join: no name is given, no line of ours about a file",
                  job.get("state") == "done" and job.get("finish") is True and [x["folder"] for x in d["shoots"]] == ["Minis_06-04-26"]
                  and "shoots.json" not in json.dumps(d), d)
            bad, n = t.photos_match(w["drive"] / "CLIENT WORK", jread(st / "index.json"), b["card"])
            check(f"every photo is still the card's, byte for byte ({n})", not bad and n == 12, bad)
        finally:
            s.stop()

    print("A Save pressed while the job before it is winding up")
    w, b = world(work, "winding-up")
    if b:
        st, name = b["records"], b["session"]
        q = "?backup=" + quote(name)
        s = Server(w, STUDIO_NAME_JOB_HOLD_FOR_TESTS="before-last-write:4")
        s.start()
        try:
            save(s, name, {"s1": "Shoot 2", "s2": "Zed"})            # the renamer refuses the first: that folder is there
            time.sleep(2.0)
            code, d = s.json("GET", "/name-shoots-data" + q)
            check("until the job has done its last thing the page says it is working, never its outcome early", (d.get("job") or {}).get("state") == "working", d.get("job"))
            code, d2 = save(s, name, {"s3": "Katie"})
            check("a Save pressed meanwhile is told to wait, never taken and then lost",
                  d2.get("ok") is False and d2.get("words") == "A rename or a join is already at work. Give it a moment.", d2)
            d = wait_job(s, q)
            job = d.get("job") or {}
            check("then the outcome, in plain words", job.get("state") == "problem" and "already exists" in job.get("line", "") and job.get("line", "").endswith("Nothing is lost."), job)
            s.stop()
            s = Server(w)
            s.start()
            code, d2 = save(s, name, {"s3": "Katie"})
            d = wait_job(s, q)
            check("and the next Save is taken and done", d2.get("ok") is True and (d.get("job") or {}).get("state") == "done"
                  and (w["drive"] / "CLIENT WORK" / "Katie_06-04-26").is_dir(), d.get("job"))
        finally:
            s.stop()

    print("A rename that can't be finished by pressing again")
    w, b = world(work, "stuck")
    if b:
        st, name = b["records"], b["session"]
        q = "?backup=" + quote(name)
        gone = w["drive"] / "CLIENT WORK" / "Shoot 3_06-04-26" / "Shoot_0002_IMG_4481.JPG"
        check("a photo of the third shoot is there to be moved out by hand", gone.is_file(), sorted(os.listdir(gone.parent)))
        away = w["drive"] / "stray.JPG"
        os.rename(gone, away)
        s = Server(w)
        s.start()
        try:
            save(s, name, {"s1": "Aurora", "s3": "Katie"})
            d = wait_job(s, q)
            job = d.get("job") or {}
            check("the first Save gives the true line, and the page offers Finish it", job.get("state") == "problem" and "stopped part way on something unexpected" in job.get("line", "")
                  and d.get("half") is True, d.get("job"))
            save(s, name, {})
            d = wait_job(s, q)
            job = d.get("job") or {}
            check("when finishing it fails too, the page no longer promises that pressing again will finish it: tell the Assistant",
                  job.get("state") == "stopped" and job.get("line") == LOOK and d.get("stuck") is True and d.get("half") is False, d.get("job"))
            code, d2 = save(s, name, {"s2": "Hannah"})
            check("and another press is answered with the same line, nothing started", d2.get("ok") is False and d2.get("words") == LOOK, d2)
            check("no path and no file name of ours anywhere in what the page gets", no_path(w, d) and ".json" not in json.dumps(d))
            # the photo is put back where the log left it; the chat's finish command mends it
            os.rename(away, w["drive"] / "CLIENT WORK" / "Katie_06-04-26" / "Shoot_0002_IMG_4481.JPG")
            code, out = t.run("join_shoots.py", st, "--finish", env=w["env"])
            code2, d = s.json("GET", "/name-shoots-data" + q)
            check("once the Assistant has finished it from the chat the page is itself again", code == 0 and d.get("stuck") is False and d.get("half") is False
                  and [x["folder"] for x in d["shoots"]] == ["Aurora_06-04-26", "Shoot 2_06-04-26", "Katie_06-04-26"], out + str(d.get("shoots")))
        finally:
            s.stop()


def the_report(work):
    print("The report's way in")
    w, b = world(work, "report", groups=(3, 3), shoots=("Beach", "Palms"))
    if not b:
        return
    st = b["records"]
    t.run("report_page.py", st, env=w["env"])
    page = (st / "report.html").read_text(encoding="utf-8")
    at = page.find("id='opt-join'")
    part = page[at:at + 900] if at >= 0 else ""
    check("a backup with two shoots has Put these shoots in one folder among its options, with its line beside it and what it does under it",
          "id='ns-open'>Put these shoots in one folder</button>" in part and "id='ns-say'" in part
          and "This opens Name your shoots" in part and "tell the Assistant which ones" in part, part)
    check("it asks its own server by a relative address (so it works inside a card's frame)", "fetch('name-shoots-url'" in page)
    srv, base = r.serve(w, st)
    try:
        code, body = r.get(base, "/name-shoots-url")
        check("the report's server answers for THIS backup; inside a test no page server is started and no path is given",
              code == 503 and json.loads(body) == {"url": None}, body)
        code, body = r.post(base, "/name-shoots-url", {})
        check("it is only ever asked, never posted to", code in (403, 404, 405, 501), code)
    finally:
        srv.terminate()
    import name_shoots
    with t.environ(**w["env"]):
        check("no page address is made inside a test", name_shoots.url_for(st) is None)
    code, out = t.run("join_shoots.py", st, "--all", env=w["env"])
    t.run("report_page.py", st, env=w["env"])
    page = (st / "report.html").read_text(encoding="utf-8")
    check("a backup with one shoot has no such button (there is nothing to put together)", code == 0 and "id='ns-open'" not in page)


def the_page(work, shot=None):
    print("The page in a hidden Chrome")
    import chrome_drive
    if not chrome_drive.find_chrome():
        print("  SKIP  no Chrome on this computer")
        return
    w, b = world(work, "chrome")
    if not b:
        return
    name = b["session"]
    s = Server(w)
    s.start()
    try:
        with chrome_drive.Chrome(work=str(work / "chrome-profile"), size=(1100, 900)) as c:
            c.open(s.url("/name-shoots.html?backup=" + quote(name)))
            c.wait_for("document.querySelectorAll('.nshoot').length === 3", 15)
            check("her title, with the last word in her accent", c.js("document.getElementById('title').innerHTML") == "Name your <em>shoots</em>")
            check("her safe line, bold, then her found line",
                  c.js("document.getElementById('safe').textContent") == "✓ Every photo is checked and safe on G PAPA › CLIENT WORK. It's safe to format your card."
                  and c.js("document.getElementById('sub').textContent") == "We found 3 shoots on your card, sorted by when you took them. Give each one a name, or do it later.")
            check("her mini sessions box, not ticked", c.js("document.querySelector('.mini').textContent") == "These are mini sessions. Keep them in one folder."
                  and c.js("document.getElementById('mini').checked") is False)
            try:
                c.wait_for("[...document.querySelectorAll('.nshoot img')].every(i => i.complete && i.naturalWidth > 0)", 15)
            except Exception:  # noqa: BLE001  (the check below says what is missing)
                pass
            check("each shoot: three pictures that loaded, when and how many, a box that says Shoot name, the folder it has now",
                  c.js("[...document.querySelectorAll('.nshoot')].every(b => b.querySelectorAll('img').length === 3 && [...b.querySelectorAll('img')].every(i => i.complete && i.naturalWidth > 0))")
                  and c.js("document.querySelector('.nshoot small').textContent") == "Thursday 9:00 to 9:03 am · 5 photos"
                  and c.js("document.getElementById('name-s1').placeholder") == "Shoot name"
                  and c.js("document.querySelector('.nshoot .pv').textContent") == "Folder: Shoot 1_06-04-26")
            check("Save the names and Do it later side by side, the true note under them",
                  c.js("document.getElementById('save').textContent") == "Save the names" and c.js("document.getElementById('later').textContent") == "Do it later"
                  and "start with the first word of that name" in c.js("document.querySelector('.note').textContent"))
            c.click("#name-s1")
            c.type_text("Aurora")
            check("the folder name updates as they type, in their pattern, with the photos' own date",
                  c.js("document.querySelector('.nshoot .pv').textContent") == "Folder: Aurora_06-04-26", c.js("document.querySelector('.nshoot .pv').textContent"))
            c.click("#name-s2")
            c.type_text('<b>Ka"tie</b>')
            check("a name is only ever text on the page, and the folder shows what the drive will take",
                  c.js("document.querySelectorAll('.nshoot b').length") == 0
                  and c.js("document.querySelectorAll('.nshoot .pv')[1].textContent") == "Folder: b Ka tie b_06-04-26", c.js("document.querySelectorAll('.nshoot .pv')[1].textContent"))
            c.js("(() => { const i = document.getElementById('name-s2'); i.value = 'Aurora'; i.dispatchEvent(new Event('input')); })()")
            c.click("#save")
            c.wait_for("document.getElementById('line').textContent.length > 0", 10)
            check("two shoots with one name: told right under the buttons, and the names they typed are still in their boxes",
                  "they would share a folder" in c.js("document.getElementById('line').textContent")
                  and c.js("document.getElementById('name-s1').value") == "Aurora" and c.js("document.getElementById('save').disabled") is False)
            c.js("(() => { const i = document.getElementById('name-s2'); i.value = 'Hannah'; i.dispatchEvent(new Event('input')); })()")
            if shot:
                shutil.copyfile(c.screenshot("name-shoots-form.png"), Path(shot) / "name-shoots-form.png")
            c.click("#save")
            c.wait_for("document.getElementById('named') !== null", 60)
            check("All set: her title, the safe line, the folders as they are on the drive now",
                  c.js("document.getElementById('title').innerHTML") == "All <em>set.</em>"
                  and c.js("[...document.querySelectorAll('#named p')].map(p => p.textContent)") == ["Aurora_06-04-26", "Hannah_06-04-26", "Shoot 3_06-04-26"],
                  c.js("[...document.querySelectorAll('#named p')].map(p => p.textContent)"))
            check("the line under them says Your backups, never the editing queue", c.js("document.querySelector('.dest').textContent") == "Each in its own folder, in Your backups.")
            check("Back up another card with her line beside it, See all my backups, and a way back to the names",
                  c.js("document.getElementById('another').textContent") == "Back up another card"
                  and c.js("document.querySelector('.row small').textContent") == "Got another card from the same day? It goes in with these."
                  and c.js("document.getElementById('seeAll').getAttribute('href')") == "/backups"
                  and c.js("document.getElementById('change').getAttribute('href')").endswith("&again=1"))
            if shot:
                shutil.copyfile(c.screenshot("name-shoots-all-set.png"), Path(shot) / "name-shoots-all-set.png")
            c.reload()
            c.wait_for("document.getElementById('named') !== null", 15)
            check("a reload shows where it stands: still All set", c.js("document.getElementById('title').innerHTML") == "All <em>set.</em>")
            c.open(s.url("/name-shoots.html?backup=" + quote(name) + "&again=1"))
            c.wait_for("document.querySelectorAll('.nshoot').length === 3", 15)
            check("Change the names opens the boxes again, with the names they gave in them",
                  c.js("document.getElementById('name-s1').value") == "Aurora" and c.js("document.getElementById('name-s3').value") == "")
            c.click("#mini")
            c.wait_for("document.getElementById('name-mini') !== null", 5)
            check("mini sessions: one block, one picture from each shoot, her 'All 12 photos, together', her placeholder and her default folder",
                  c.js("document.querySelectorAll('.nshoot').length") == 1 and c.js("document.querySelectorAll('.nshoot img').length") == 3
                  and c.js("document.querySelector('.nshoot small').textContent") == "All 12 photos, together"
                  and c.js("document.getElementById('name-mini').placeholder") == "Name the mini sessions"
                  and c.js("document.querySelector('.nshoot .pv').textContent") == "Folder: Mini sessions_06-04-26")
            c.click("#name-mini")
            c.type_text("Fall minis")
            check("its folder updates as they type too", c.js("document.querySelector('.nshoot .pv').textContent") == "Folder: Fall minis_06-04-26")
            c.click("#save")
            c.wait_for("document.getElementById('named') !== null", 60)
            check("All set shows the one folder, and says In one folder",
                  c.js("[...document.querySelectorAll('#named p')].map(p => p.textContent)") == ["Fall minis_06-04-26"]
                  and c.js("document.querySelector('.dest').textContent") == "In one folder, in Your backups.",
                  c.js("document.querySelector('.dest').textContent"))
            check("nothing on the page scrolls sideways at this width", c.js("document.documentElement.scrollWidth <= window.innerWidth"))
            got = sorted(os.listdir(w["drive"] / "CLIENT WORK" / "Fall minis_06-04-26"))
            check("and on the drive the twelve photos are in it, in order", got == [f"Fall_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 13)], got)

            print("The page when a join was cut off")
            w2, b2 = world(work, "chrome-half")
            if b2:
                s.stop()
                s = Server(w2)
                s.start()
                code, out = t.run("join_shoots.py", b2["records"], "--all", "--name", "Minis", env=dict(w2["env"], STUDIO_JOIN_CUT_FOR_TESTS="moves:3"))
                c.open(s.url("/name-shoots.html?backup=" + quote(b2["session"])))
                c.wait_for("document.getElementById('finish') !== null", 15)
                check("only the line and one button, Finish it, right under it: no name boxes, no tick box, no Save",
                      code == 70 and c.js("document.getElementById('line').textContent") == "This was cut off part way. Nothing is lost. Press Finish it and it will carry on."
                      and c.js("document.getElementById('finish').textContent") == "Finish it"
                      and c.js("document.querySelectorAll('.nshoot, #mini, #save').length") == 0, c.js("document.getElementById('top').textContent"))
                c.click("#finish")
                c.wait_for("document.getElementById('named') !== null", 60)
                check("Finish it finishes the join: All set, the one folder",
                      c.js("[...document.querySelectorAll('#named p')].map(p => p.textContent)") == ["Minis_06-04-26"],
                      c.js("document.getElementById('top').textContent"))
                # a join that has stopped on a problem (written by hand here): pressing again is not the answer
                jl = b2["records"] / "join-log.json"
                log = jread(jl)
                log["joins"].append({"ids": ["s8", "s9"], "name": "X", "moves": [], "problems": ["pretend"], "started": "x"})
                jl.write_text(json.dumps(log), encoding="utf-8")
                c.reload()
                c.wait_for("document.getElementById('line') !== null", 15)
                check("stopped on a problem: one line that says to tell the Assistant, and nothing to press",
                      c.js("document.getElementById('line').textContent") == "This stopped on something I can't sort out from this page. Nothing is lost. Tell the Assistant and it will take a look."
                      and c.js("document.querySelectorAll('#finish, #save, .nshoot, #named').length") == 0, c.js("document.getElementById('top').textContent"))
    finally:
        s.stop()
        chrome_drive.stop_all()


def main():
    chrome = "--chrome" in sys.argv
    shot = sys.argv[sys.argv.index("--shot") + 1] if "--shot" in sys.argv else None
    work = Path(tempfile.mkdtemp(prefix="name-shoots-check-"))
    try:
        the_words()
        the_instructions()
        the_routes(work)
        cut_off_and_stuck(work)
        the_report(work)
        if chrome:
            the_page(work, shot)
        else:
            print("The page in a hidden Chrome\n  SKIP  not asked for (--chrome)")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{N[0] - len(FAILED)} of {N[0]} passed" + (f"; FAILED: {len(FAILED)}" if FAILED else ""))
    for f in FAILED:
        print("  FAILED: " + f)
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
