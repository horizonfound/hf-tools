#!/usr/bin/env python3
"""The other options on the report, under "Anything you'd like to change?" (Dustin, Nov 19: nothing is asked
before a backup; what used to be a question is a button afterwards): This shoot continues on another card, Change
how my shoots are named, Use a different drive next time, Write a note to my client on each shoot, the one quiet
line when the photos are on the computer's own disk, and the same-page-only guard on every POST of the report's
server.

Everything here is pretend: a scratch STUDIO_HOME, pretend drives (temp folders handed over through the tests'
switch STUDIO_DRIVES_FOR_TESTS, so the drives really plugged in are never looked at), pretend cards (temp folders
with a DCIM), and whole pretend backups made by night.py itself (copied, checked, sorted, settled), because the
naming option renames real folders and needs the backup's own records to prove it. The report's server runs on
a scratch port with STUDIO_NO_WINDOWS_FOR_TESTS.

    python3 tests/report_options_check.py
    python3 tests/guard.py 3000 python3 tests/report_options_check.py --chrome    (also presses the panels in a hidden Chrome)
"""
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pc_smoke as t  # noqa: E402
import this_computer  # noqa: E402  (pc_smoke put the scripts folder on the path)

FAILED = []
SKIPPED = []
GB = 1024 ** 3
TODAY = datetime.now()
DAY1 = (TODAY - timedelta(days=2)).strftime("%Y-%m-%d")     # the first card's backup
DAY2 = (TODAY - timedelta(days=1)).strftime("%Y-%m-%d")     # the second card's
HARD = 'Smith <b>"Family"</b> & co'                         # a shoot's name that must stay text


def check(what, ok, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {str(detail)[-900:]}"), flush=True)
    if not ok:
        FAILED.append(what)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree(folder):
    """{relative path: sha256} of every file under a folder."""
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): sha(p) for p in sorted(folder.rglob("*")) if p.is_file()} if folder.is_dir() else {}


def photos_on(drive):
    """Every photo on a pretend drive by its place and hash, the Assistant's own hidden records left out."""
    return {k: v for k, v in tree(drive).items() if not k.startswith(".studio/") and "/_studio/" not in k and not k.startswith("_studio/")}


def jread(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


# ---------------------------------------------------------------- a pretend world, and whole backups in it

def new_world(work, name):
    base = work / name
    home, folders = base / "home", base / "folders"
    home.mkdir(parents=True)
    (folders / "Pictures").mkdir(parents=True)
    listing = base / "drives.json"
    listing.write_text("[]", encoding="utf-8")
    env = {"STUDIO_HOME": str(home), "STUDIO_DRIVES_FOR_TESTS": str(listing),
           "STUDIO_FOLDERS_FOR_TESTS": str(folders), "STUDIO_NO_WINDOWS_FOR_TESTS": "1"}
    return {"base": base, "home": home, "folders": folders, "listing": listing, "env": env}


def new_drive(w, name, free_gb=1000):
    p = w["base"] / "drives" / name
    p.mkdir(parents=True)
    rows = json.loads(w["listing"].read_text(encoding="utf-8"))
    rows.append({"path": str(p), "name": name, "shown": name, "total": 2000 * GB, "free": int(free_gb * GB),
                 "system": False, "removable": False, "id": None})
    w["listing"].write_text(json.dumps(rows), encoding="utf-8")
    return p


def a_backup(w, card_name, name, date, groups, shoots, dest):
    """One whole pretend backup made by night.py: copied and checked, sorted into the named shoots, settled.
    Returns {"records", "card", "before", "session"} or None."""
    card = w["base"] / card_name
    t.make_card(card, groups=groups)
    before = t.card_snapshot(card)
    night = ["night.py", "--source", card, "--name", name, "--date", date, "--no-peeks"]
    code, out = t.run(*night, env=w["env"])
    session = f"{date} {name}"
    st = Path(dest) / session / "_studio"
    if code != 4:
        check(f"the pretend backup '{name}' reaches the look (exit 4)", False, out)
        return None
    groups_ = json.loads((st / "groups.json").read_text(encoding="utf-8"))["groups"]
    rows = [{"id": f"s{i}", "suggested": shoots[i - 1], "groups": [g["id"]], "photos": g.get("count", 0),
             "recap": "Test frames.", "why": "test"} for i, g in enumerate(groups_, 1)]
    (st / "shoots.json").write_text(json.dumps({"decided_by": "test", "shoots": rows}), encoding="utf-8")
    code, out = t.run(*night, env=w["env"])
    records = Path(dest) / ".studio" / session
    ok = code == 0 and (records / "settled.json").is_file()
    check(f"the pretend backup '{name}' finishes and settles (exit 0)", ok, out)
    return {"records": records, "card": card, "before": before, "session": session} if ok else None


def serve(w, records):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = subprocess.Popen([sys.executable, str(t.SCRIPTS / "serve_report.py"), str(records), "--port", str(port)],
                           env=t.child_env(w["env"]), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding="utf-8", errors="replace")
    line = srv.stdout.readline()
    base = line.split("Report:", 1)[1].strip().rsplit("/", 1)[0] if "Report:" in line else f"http://127.0.0.1:{port}"
    return srv, base


def get(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=90) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def post(base, path, body, **headers):
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method="POST", headers=dict({"Content-Type": "application/json"}, **headers))
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def jget(base, path):
    code, body = get(base, path)
    return jread_text(body)


def jpost(base, path, body, **headers):
    code, text = post(base, path, body, **headers)
    return code, jread_text(text)


def jread_text(text):
    try:
        return json.loads(text)
    except ValueError:
        return {"not json": text[:300]}


def no_path(w, text):
    """Nothing a page is given holds a place on a drive."""
    text = text if isinstance(text, str) else json.dumps(text)
    return str(w["base"]) not in text and "/Volumes" not in text and str(Path(tempfile.gettempdir())) not in text and "\\\\" not in text


def wait_naming(base, prefix="", limit=90):
    end = time.monotonic() + limit
    j = {}
    while time.monotonic() < end:
        j = jget(base, prefix + "/naming")
        if not j.get("busy") and j.get("line"):
            return j
        time.sleep(0.3)
    return j


# ---------------------------------------------------------------- the cases

def the_words(w, b):
    print("The report: the options, the note line, the words")
    t.run("report_page.py", b["records"], env=w["env"])
    page = (b["records"] / "report.html").read_text(encoding="utf-8")
    at = page.find("<section class='wrap opts'")
    section = page[at:page.find("</section>", at)] if at >= 0 else ""
    for words in ("This shoot continues on another card", "Which backup is the other card?", "Put them on one report",
                  "Back up the other card first: put it in and say backup now. Then come back here and pick it.",
                  "Each card&#x27;s photos stay in their own folders.",
                  "Change how my shoots are named", "How should a shoot folder be named?", "Rename this backup&#x27;s shoots to match",
                  "Name them your own way? Copy this into the chat:",
                  "Use a different drive next time", "Where should your next backup go?"):
        check(f"the section says: {words.replace('&#x27;', chr(39))}", words in section)
    check("Make a second copy is still there, first", 0 < section.find("id='opt-second'") < section.find("id='opt-card'") < section.find("id='opt-naming'") < section.find("id='opt-drive'"))
    check("every panel starts closed", all(f"id='{i}-panel' hidden" in section for i in ("oc", "nm", "nd")))
    check("each button has its line right beside it (the same row)",
          all(f"id='{i}-open'" in row and f"id='{i}-say'" in row for i in ("oc", "nm", "nd")
              for row in [section[section.find(f"id='{i}-open'") - 200:section.find(f"id='{i}-say'") + 80]] if "opt-row" in row)
          and section.count("class='opt-row'") == 4)
    check("no path, no em dash, no 'Claude' in the section", no_path(w, section) and "—" not in section and "Claude" not in section)
    check("the routes are asked for by relative address, so they work inside /card/N/",
          all(f"('{r}'" in page for r in ("other-backups", "link-card", "naming", "next-drives", "next-drive")) and "fetch('/" not in page)
    # the note line, per shoot
    check("each shoot has Write a note to my client, with the line to copy hidden until it is pressed",
          page.count("class='note-open'") == 2 and page.count("class='note-how' hidden") == 2 and page.count("Copy this into the chat:") >= 3)
    check("the line names the shoot", "<span class='copy-text'>Write a note for the Beach shoot</span>" in page
          and "<span class='copy-text'>Write a note for the Palms shoot</span>" in page, page[page.find("note-ask"):page.find("note-ask") + 500])
    check("with no form anywhere in it", "<form" not in page and "<textarea" not in page[page.find("note-ask"):page.find("note-ask") + 900])
    check("the own-disk line is not on a report whose photos are on an external drive", "id='own-disk'" not in page)
    rp = t.run_python(["-c", f"import sys; sys.path.insert(0, {str(t.SCRIPTS)!r}); import report_page, first_look, json; "
                             "print(json.dumps([report_page.OUR_WORDS, first_look.OUR_WORDS]))"], env=w["env"])[1]
    try:
        ours = json.loads(rp.strip().splitlines()[-1])
        text = " ".join(ours[0].values()) + " ".join(ours[1].values())
    except (ValueError, IndexError):
        text = "—"
    check("none of our words has an em dash, 'she', 'he' or 'Claude'",
          "—" not in text and "Claude" not in text and " she " not in f" {text.lower()} " and " he " not in f" {text.lower()} ", text[:200])


def a_hard_name(w, b, base):
    print("A shoot whose name has <b> and quotes in it")
    code, out = t.run("rename_shoot.py", b["records"], "--shoot", "s2", "--name", HARD, env=w["env"])
    t.run("report_page.py", b["records"], env=w["env"])
    page = (b["records"] / "report.html").read_text(encoding="utf-8")
    want = "Write a note for the Smith &lt;b&gt;&quot;Family&quot;&lt;/b&gt; &amp; co shoot"
    check("the renamer took the name", code == 0, out)
    check("the note line carries it as text, never as markup", want in page and "the Smith <b>" not in page, page[page.find("Write a note for the Smith"):][:200])
    j = jget(base, "/naming")
    check("and the naming panel's answer is data, the name whole", isinstance(j.get("ways"), list) and no_path(w, j))
    code, out = t.run("rename_shoot.py", b["records"], "--shoot", "s2", "--name", "Palms", env=w["env"])
    t.run("report_page.py", b["records"], env=w["env"])
    check("(the shoot goes back to Palms for the cases below)", code == 0, out)


def the_guard(w, b, base, prefix=""):
    where = f" (inside {prefix}/)" if prefix else ""
    print("Every POST is for this report's own page" + where)
    studio_file = w["home"] / "studio.json"
    def state():
        return (studio_file.read_bytes() if studio_file.exists() else b"", tree(b["records"]), sorted(photos_on(w["drive"])),
                get(base, prefix + "/rename-status")[1], get(base, prefix + "/picks-status")[1],
                (w["home"] / "queue.json").read_bytes() if (w["home"] / "queue.json").exists() else b"")
    before = state()
    bodies = {"/rename": {"shoot": "s1", "name": "Hacked"}, "/queue": {"shoot": "s1", "due": "2027-01-01"},
              "/peeks-again": {"shoot": "s1", "note": "x"}, "/peeks-choose": {"shoot": "s1", "nums": [1, 2, 3, 4, 5, 6]},
              "/names": {"s1": "Hacked"}, "/second-copy": {"drive": 0, "name": "LaCie Rugged", "always": True},
              "/link-card": {"backup": 0, "name": "second card"}, "/naming": {"offered": 2, "apply": True},
              "/next-drive": {"drive": 1, "name": "LaCie Rugged"}}
    for path, body in bodies.items():
        c1, _ = post(base, prefix + path, body, Origin="https://evil.example")
        c2, _ = post(base, prefix + path, body, **{"Sec-Fetch-Site": "cross-site"})
        c3, _ = post(base, prefix + path, json.dumps(body).encode(), **{"Content-Type": "text/plain"})
        check(f"POST {path}: another Origin 403, a cross-site press 403, not JSON 415", (c1, c2, c3) == (403, 403, 415), str((c1, c2, c3)))
    time.sleep(0.5)
    check("and nothing was changed by any of them: the Studio File, the records, the folders, the queues", state() == before)
    code, _ = post(base, prefix + "/next-drive", b"x" * 70000)
    check("a body over the cap is refused (413)", code == 413, str(code))


def next_drive(w, b, base):
    print("Use a different drive next time")
    j = jget(base, "/next-drives")
    rows = j.get("drives") or []
    names = [r.get("name") for r in rows]
    at = {n: i for i, n in enumerate(names)}
    LACIE, OLD, HERE_ = at.get("LaCie Rugged", -1), at.get("Old Shoots", -1), len(rows) - 1
    check("GET next-drives: the drives by name and room, the one in use marked, the computer itself last",
          sorted(names[:-1]) == ["Big Kahuna", "LaCie Rugged", "Old Shoots"] and names[-1] == f"This {this_computer.COMPUTER}"
          and [r.get("name") for r in rows if r.get("now")] == ["Big Kahuna"] and rows[LACIE].get("free") == "1.0 TB free" and rows[-1].get("free") == "",
          str(rows))
    check("with no path in the answer", no_path(w, j) and all(set(r) == {"i", "name", "free", "now"} for r in rows))
    sf0, drive0, rec0 = (w["home"] / "studio.json").read_bytes(), photos_on(w["drive"]), tree(b["records"])
    code, j = jpost(base, "/next-drive", {"drive": LACIE, "name": "Big Kahuna"})
    check("a name that is not the one at that place: 'The drives changed...', nothing written",
          j.get("ok") is False and j.get("words") == "The drives changed since this was opened. Press the button again."
          and (w["home"] / "studio.json").read_bytes() == sf0, str(j))
    code, j = jpost(base, "/next-drive", {"drive": 0, "name": "Big Kahuna"})
    check("the drive already in use: 'Your backups already go to Big Kahuna. Nothing changed.'",
          j.get("ok") is True and j.get("words") == "Your backups already go to Big Kahuna. Nothing changed."
          and (w["home"] / "studio.json").read_bytes() == sf0, str(j))
    code, j = jpost(base, "/next-drive", {"drive": LACIE, "name": "LaCie Rugged"})
    sf = jread(w["home"] / "studio.json", {})
    check("Save: the line the plan gives", j.get("ok") is True and j.get("words") ==
          "Saved. Your next backup goes to LaCie Rugged. The photos from this backup stay where they are." and no_path(w, j), str(j))
    check("the Studio File now names that drive", Path(sf["drives"]["session"]).resolve() == w["lacie"].resolve(), str(sf.get("drives")))
    check("and only the Studio File changed: every photo where it was, the records as they were",
          photos_on(w["drive"]) == drive0 and tree(b["records"]) == rec0 and photos_on(w["lacie"]) == {})
    before = (w["home"] / "studio.json").read_bytes()
    code, j = jpost(base, "/next-drive", {"drive": LACIE, "name": "LaCie Rugged"})
    check("pressed again: nothing written", j.get("ok") is True and "already go to LaCie Rugged" in j.get("words", "")
          and (w["home"] / "studio.json").read_bytes() == before, str(j))
    code, j = jpost(base, "/next-drive", {"drive": OLD, "name": "Old Shoots"})
    sf = jread(w["home"] / "studio.json", {})
    check("a drive with an obvious shoot folder: the place is that folder, by the first backup's own rule",
          j.get("ok") is True and Path(sf["drives"]["session"]).resolve() == (w["old"] / "Photo Shoots").resolve(), str(sf.get("drives")))
    check("and the page is told where on the drive, not only which drive (Nov 19 review)",
          "goes to Old Shoots, in Photo Shoots." in j.get("words", "") and no_path(w, j), str(j))
    # A drive an earlier version saved for second copies is no longer set apart (Nicole, Nov 23: the second drive
    # is asked each time, so nothing is saved for it): it can be chosen for the next backup like any other drive.
    t.run("studio_file.py", "set", "--second", w["lacie"], env=w["env"])
    code, j = jpost(base, "/next-drive", {"drive": LACIE, "name": "LaCie Rugged"})
    sf = jread(w["home"] / "studio.json", {})
    check("a drive once saved for second copies is no longer refused as the next backup's drive",
          j.get("ok") is True and "where your second copies go" not in j.get("words", "")
          and Path(sf["drives"]["session"]).resolve() == Path(w["lacie"]).resolve(), str(j))
    t.run("studio_file.py", "set", "--no-second", env=w["env"])
    code, out = t.run_python(["-c", f"import sys; sys.path.insert(0, {str(t.SCRIPTS)!r}); import second_copy; print(second_copy.REMEMBER_SECOND)"], env=w["env"])
    check("(the one switch for all of this is off: second_copy.REMEMBER_SECOND)", out.strip().endswith("False"), out)
    code, j = jpost(base, "/next-drive", {"drive": HERE_, "name": f"This {this_computer.COMPUTER}"})
    sf = jread(w["home"] / "studio.json", {})
    shoots = w["folders"] / "Pictures" / "Shoots"
    check("the computer itself: a Shoots folder inside Pictures, made, and said as 'this Mac'",
          j.get("ok") is True and shoots.is_dir() and Path(sf["drives"]["session"]).resolve() == shoots.resolve()
          and f"goes to this {this_computer.COMPUTER}." in j.get("words", ""), str(j))
    rows = jget(base, "/next-drives").get("drives") or []
    check("and the list marks the computer as where they go now", [r.get("name") for r in rows if r.get("now")] == [f"This {this_computer.COMPUTER}"], str(rows))
    code, j = jpost(base, "/next-drive", {"drive": 0, "name": "Big Kahuna"})
    sf = jread(w["home"] / "studio.json", {})
    check("back to Big Kahuna for the cases below", j.get("ok") is True and Path(sf["drives"]["session"]).resolve() == w["drive"].resolve(), str(j))
    check("through all of it, no photo moved", photos_on(w["drive"]) == drive0 and tree(b["records"]) == rec0)


def naming(w, b, base):
    print("Change how my shoots are named")
    j = jget(base, "/naming")
    check("GET naming: the two ways, shown with this backup's own first shoot and its day; the shoot's name then the date is theirs now",
          j.get("current") == 1 and [x.get("example") for x in j.get("ways") or []] == ["Beach_06-04-26", "2026-06-04 Beach"]
          and j.get("shoots") == 2 and not j.get("line"), str(j))
    folders0 = sorted(p.name for p in w["drive"].iterdir() if p.is_dir() and not p.name.startswith("."))
    drive0 = photos_on(w["drive"])
    code, j = jpost(base, "/naming", {"offered": 3, "apply": True})
    check("a way that is not one of the two is refused, nothing changed",
          j.get("ok") is False and jread(w["home"] / "studio.json", {})["naming"]["folder_pattern"] == "{shoot}_{date}", str(j))
    code, j = jpost(base, "/naming", {"offered": 2, "apply": False})
    sf = jread(w["home"] / "studio.json", {})
    check("Save without the tick: only the next backup, said so",
          j.get("ok") is True and j.get("words") == "Saved. Your next backup's shoots will be named like 2026-06-04 Beach."
          and not j.get("busy") and sf["naming"]["folder_pattern"] == "{date} {shoot}", str(j))
    check("and this backup's folders are as they were", sorted(p.name for p in w["drive"].iterdir() if p.is_dir() and not p.name.startswith(".")) == folders0
          and photos_on(w["drive"]) == drive0)
    check("the panel now marks year first as theirs", jget(base, "/naming").get("current") == 2)
    # with the tick: each shoot goes through the report's own rename queue
    code, j = jpost(base, "/naming", {"offered": 2, "apply": True})
    check("Save with the tick: 'Saved. Renaming this backup's shoots to match...'",
          j.get("ok") is True and j.get("busy") is True and j.get("words") == "Saved. Renaming this backup's shoots to match...", str(j))
    j = wait_naming(base)
    check("the line beside the button ends on Done, and a reloaded page is given it again",
          j.get("line") == "Done. This backup's shoots are renamed to match, and your next backup's will be named like 2026-06-04 Beach."
          and jget(base, "/naming").get("line") == j.get("line"), str(j))
    folders = sorted(p.name for p in w["drive"].iterdir() if p.is_dir() and not p.name.startswith("."))
    check("the folders took the new shape", folders == ["2026-06-04 Beach", "2026-06-04 Palms"], str(folders))
    sh = jread(b["records"] / "shoots.json", {}).get("shoots", [])
    index = jread(b["records"] / "index.json", {})
    check("the records follow: each shoot's folder, each photo's place", [s.get("folder") for s in sh] == ["2026-06-04 Beach", "2026-06-04 Palms"]
          and all(p["file"].split("/")[0] in folders for p in index.get("photos", []) if p.get("original")), str([s.get("folder") for s in sh]))
    bad, n = t.photos_match(w["drive"], index, b["card"])
    check("every photo is under its recorded name and byte for byte the card's", not bad and n == 9, str(bad)[:300])
    check("the same photos, only their folders changed", sorted(photos_on(w["drive"]).values()) == sorted(drive0.values())
          and {k.split("/", 1)[1] for k in photos_on(w["drive"])} == {k.split("/", 1)[1] for k in drive0})
    log = (jread(b["records"] / "rename-log.json", {}) or {}).get("renames", [])
    mine = [r for r in log if r.get("to_name") in ("Beach", "Palms") and r.get("from_name") == r.get("to_name")]
    check("by the renamer's own proof: each rename logged first, every file checked, no problem",
          len(mine) >= 2 and all(r.get("verified") == len(r.get("moves", [])) and not r.get("problems") for r in mine[-2:]),
          str([(r.get("shoot"), r.get("verified"), len(r.get("moves", [])), r.get("problems")) for r in log]))
    status = jread_text(get(base, "/rename-status")[1])
    check("each shoot's own line says it was renamed", all(status.get(s, {}).get("line") == "Done. Folder and photos renamed." for s in ("s1", "s2")), str(status))
    page = (b["records"] / "report.html").read_text(encoding="utf-8")
    check("the report was rebuilt with nothing lost: both shoots, their names, the options", page.count("class='note-open'") == 2 and "id='opt-naming'" in page)
    # pressed again: nothing to do
    drive1, n_log = photos_on(w["drive"]), len(log)
    code, j = jpost(base, "/naming", {"offered": 2, "apply": True})
    j = wait_naming(base)
    status = jread_text(get(base, "/rename-status")[1])
    check("pressed again: every shoot is 'Already called that.', nothing moved, nothing logged",
          all(status.get(s, {}).get("line") == "Already called that." for s in ("s1", "s2")) and photos_on(w["drive"]) == drive1
          and len((jread(b["records"] / "rename-log.json", {}) or {}).get("renames", [])) == n_log, str(status))
    # and back to name then date, by the same button
    code, j = jpost(base, "/naming", {"offered": 1, "apply": True})
    j = wait_naming(base)
    folders = sorted(p.name for p in w["drive"].iterdir() if p.is_dir() and not p.name.startswith("."))
    check("and name then date again by the same button puts every folder back as it was", folders == folders0 and photos_on(w["drive"]) == drive0, str(folders))
    check("the card is exactly as it was", t.card_snapshot(b["card"]) == b["before"])


def another_card(w, b, base):
    print("This shoot continues on another card")
    j = jget(base, "/other-backups")
    check("with no other backup: an empty list (the page then says 'Back up the other card first...')", j == {"backups": []}, str(j))
    b2 = a_backup(w, "CARD 2", "second card", DAY2, (3,), ["Ceremony"], w["drive"])
    if not b2:
        return None
    j = jget(base, "/other-backups")
    rows = j.get("backups") or []
    day = this_computer.strftime(datetime.fromisoformat(DAY2), "%b %-d")
    check("GET other-backups: the other card's backup by name, day and count, and nothing else",
          rows == [{"i": 0, "name": "second card", "day": day, "count": "3 photos"}] and no_path(w, j), str(j))
    # older than 30 days: not offered
    ledger = w["home"] / "cards.json"
    kept = ledger.read_bytes()
    led = json.loads(kept)
    for entry in led["cards"].values():
        for s in entry["sessions"]:
            if "second card" in s["folder"]:
                s["when"] = (TODAY - timedelta(days=45)).isoformat(timespec="seconds")
    ledger.write_text(json.dumps(led), encoding="utf-8")
    check("a backup from more than 30 days ago is not offered", jget(base, "/other-backups") == {"backups": []})
    ledger.write_bytes(kept)
    # a backup with a problem is not offered
    m = b2["records"] / "manifest.json"
    clean = m.read_bytes()
    mm = json.loads(clean)
    mm["problems"] = ["a pretend problem"]
    m.write_text(json.dumps(mm), encoding="utf-8")
    check("a backup with a problem is not offered", jget(base, "/other-backups") == {"backups": []})
    m.write_bytes(clean)
    code, j = jpost(base, "/link-card", {"backup": 0, "name": "some other card"})
    check("a name that is not the one at that place: refused, no link written",
          j.get("ok") is False and j.get("again") is True and not (b["records"] / "shoot.json").exists() and not (b2["records"] / "shoot.json").exists(), str(j))
    code, page = get(base, "/report.html")
    check("before the link, /report.html is this backup's own report", "Backup report · first card" in page and "2 cards" not in page)
    drive0 = photos_on(w["drive"])
    code, j = jpost(base, "/link-card", {"backup": 0, "name": "second card"})
    check("Put them on one report: 'Done. Both cards are on one report now.'",
          j.get("ok") is True and j.get("words") == "Done. Both cards are on one report now. Picked the wrong one? Tell the Assistant and it will take them apart." and no_path(w, j), str(j))
    link1, link2 = jread(b["records"] / "shoot.json", {}), jread(b2["records"] / "shoot.json", {})
    check("both backups hold the same link, the older card first",
          [c.get("name") for c in link1.get("cards", [])] == [b["session"], b2["session"]] and link1.get("cards") and
          [(c["card"], c["name"]) for c in link1["cards"]] == [(c["card"], c["name"]) for c in link2.get("cards", [])], str(link1))
    code, page = get(base, "/report.html")
    check("the running server shows the shoot's page at once: both cards on one report",
          code == 200 and "2 cards" in page and "card/1/report-card.html" in page and "card/2/report-card.html" in page
          and "on both cards, safely backed up" in page, page[page.find("<h1"):][:300])
    c1, p1 = get(base, "/card/1/report-card.html")
    c2, p2 = get(base, "/card/2/report-card.html")
    check("each card's own report is served in its frame, options and all",
          c1 == 200 and c2 == 200 and "Card 1 of 2" in p1 and "Card 2 of 2" in p2 and "Ceremony" in p2 and "id='opt-naming'" in p2 and "Beach" in p1)
    code, again = get(base, "/report.html")
    check("it survives a reload", "2 cards" in again and "card/2/report-card.html" in again)
    check("linking moved no photo: each card's shoots stay in their own folders", photos_on(w["drive"]) == drive0)
    check("the linked backup is no longer offered", jget(base, "/other-backups") == {"backups": []} and jget(base, "/card/2/other-backups") == {"backups": []})
    # the routes inside a card's frame
    j = jget(base, "/card/2/naming")
    check("inside /card/2/, GET naming shows card 2's own shoot", [x.get("example") for x in j.get("ways") or []][:1] == ["Ceremony_06-04-26"], str(j))
    code, j = jpost(base, "/card/2/naming", {"offered": 2, "apply": True}, Origin=base)
    j = wait_naming(base, "/card/2")
    folders = sorted(p.name for p in w["drive"].iterdir() if p.is_dir() and not p.name.startswith("."))
    check("and a POST from inside /card/2/ (this server's own Origin) renames card 2's shoot only",
          "2026-06-04 Ceremony" in folders and "Beach_06-04-26" in folders and "Palms_06-04-26" in folders and (j.get("line") or "").startswith("Done."), str((folders, j)))
    t.run("studio_file.py", "set", "--offered", "1", env=w["env"])
    the_guard(w, b2, base, "/card/2")
    return b2


def a_restart(w, b):
    print("A server started afresh on a linked backup")
    srv, base = serve(w, b["records"])
    try:
        code, page = get(base, "/report.html")
        check("still the shoot's page, both cards", "2 cards" in page and get(base, "/card/2/report-card.html")[0] == 200)
    finally:
        srv.kill()
        srv.communicate()


def own_disk(work):
    print("The quiet line when the photos are on the computer's own disk")
    w = new_world(work, "own-disk")
    code, out = t.run("studio_file.py", "defaults", "--computer", env=w["env"])
    shoots = w["folders"] / "Pictures" / "Shoots"
    b = a_backup(w, "CARD", "home card", DAY1, (3,), ["Garden"], shoots)
    if not b:
        return
    page = (b["records"] / "report.html").read_text(encoding="utf-8")
    line = (f"Your photos are on this {this_computer.COMPUTER}&#x27;s own disk. An external drive is safer: if anything happens to the computer, "
            "the photos on it go too. Plug one in and press Use a different drive next time.")
    check("the line is on the report, once, under the where-card, with the button it names on the page",
          page.count(line) == 1 and page.count("id='own-disk'") == 1 and page.find("where-card'>") < page.find("id='own-disk'")
          and "id='nd-open'" in page, page[page.find("where-card'>"):][:600])
    m = b["records"] / "manifest.json"
    mm = json.loads(m.read_text(encoding="utf-8"))
    mm["problems"] = ["a pretend problem"]
    m.write_text(json.dumps(mm), encoding="utf-8")
    t.run("report_page.py", b["records"], env=w["env"])
    page = (b["records"] / "report.html").read_text(encoding="utf-8")
    check("and not on a report that has no options to press (a backup with a problem)", "id='own-disk'" not in page and "id='opts'" not in page)


def in_a_browser(work):
    """The panels pressed by a real page, in a hidden Chrome (only with --chrome; run under tests/guard.py)."""
    print("The panels, pressed in a hidden browser")
    import chrome_drive
    w = new_world(work, "browser")
    w["drive"] = new_drive(w, "Big Kahuna", 2000)
    w["lacie"] = new_drive(w, "LaCie Rugged", 1000)
    t.run("studio_file.py", "set", "--drive", w["drive"], "--offered", "1", "--file-names", "shoot", env=w["env"])
    b = a_backup(w, "CARD", "first card", DAY1, (5, 4), ["Beach", HARD], w["drive"])
    b2 = a_backup(w, "CARD 2", "second card", DAY2, (3,), ["Ceremony"], w["drive"])
    if not b or not b2:
        return
    srv, base = serve(w, b["records"])
    say = "document.getElementById('%s').textContent"
    beside = ("(() => { const a = document.getElementById('%s-open').getBoundingClientRect(), s = document.getElementById('%s-say').getBoundingClientRect();"
              " return Math.abs(a.top - s.top) < 60 && s.width > 0; })()")
    try:
        with chrome_drive.Chrome(work=str(work / "chrome"), size=(1280, 900)) as c:
            c.open(base + "/report.html")
            check("the three options are on the page, panels closed, nothing said",
                  c.js("['oc','nm','nd'].every(i => document.getElementById(i+'-panel').hidden && document.getElementById(i+'-say').textContent === '')"))
            # the note line
            c.js("document.querySelectorAll('.note-open')[1].click(); true")
            line = c.js("(() => { const how = document.querySelectorAll('.note-how')[1]; return [how.hidden, how.querySelector('.copy-text').textContent, how.querySelector('.how-q').textContent, how.querySelectorAll('b').length]; })()")
            check("Write a note to my client shows the line right there, the shoot's name as text",
                  line == [False, f"Write a note for the {HARD} shoot", "Copy this into the chat:", 0], str(line))
            check("the first shoot's line stays closed", c.js("document.querySelectorAll('.note-how')[0].hidden") is True)
            c.click(".note-how:not([hidden]) .copy-line")
            c.wait_for("document.querySelectorAll('.note-how')[1].querySelector('.copy-said').textContent !== ''", seconds=10)
            said = c.js("document.querySelectorAll('.note-how')[1].querySelector('.copy-said').textContent")
            check("Copy says what it did, beside the button", said in ("Copied. Paste it in the chat.", "I couldn't copy it for you. Select the line and copy it yourself."), said)
            # a different drive next time
            c.js("document.getElementById('nd-open').click(); true")
            c.wait_for("document.querySelectorAll('#nd-list label').length > 0", seconds=20)
            labels = c.js("[...document.querySelectorAll('#nd-list label')].map(l => l.textContent)")
            check("Use a different drive next time opens right there: each drive, the one in use marked, the computer last",
                  labels == ["Big Kahuna, 2.0 TB free (where they go now)", "LaCie Rugged, 1.0 TB free", f"This {this_computer.COMPUTER}"], str(labels))
            if os.environ.get("REPORT_OPTIONS_SHOT"):
                c.js("document.getElementById('opts').scrollIntoView({block:'start'}); true")
                shutil.copy(c.screenshot("report-options.png"), os.environ["REPORT_OPTIONS_SHOT"])
            c.js("document.querySelectorAll('#nd-list input')[1].click(); document.getElementById('nd-go').click(); true")
            c.wait_for("/^Saved\\./.test(%s)" % (say % "nd-say"), seconds=30)
            check("Save: the line shows beside the button, the panel closed",
                  c.js(say % "nd-say") == "Saved. Your next backup goes to LaCie Rugged. The photos from this backup stay where they are."
                  and c.js("document.getElementById('nd-panel').hidden") and c.js(beside % ("nd", "nd")), c.js(say % "nd-say"))
            check("and the Studio File names that drive", Path(jread(w["home"] / "studio.json", {})["drives"]["session"]).resolve() == w["lacie"].resolve())
            # naming
            c.js("document.getElementById('nm-open').click(); true")
            c.wait_for("document.querySelectorAll('#nm-list label').length === 2", seconds=20)
            labels = c.js("[...document.querySelectorAll('#nm-list label')].map(l => l.textContent)")
            check("Change how my shoots are named: the two ways with this backup's own shoot, the one in use marked, the tick box ticked",
                  labels == ["Beach_06-04-26 (how they're named now)", "2026-06-04 Beach"] and c.js("document.getElementById('nm-apply').checked && !document.getElementById('nm-apply-row').hidden"), str(labels))
            check("with the line to copy for their own way", c.js("document.querySelector('#nm-panel .copy-text').textContent") == "Change how my shoots are named")
            c.js("document.querySelectorAll('#nm-list input')[1].click(); document.getElementById('nm-go').click(); true")
            c.wait_for("/^Done\\./.test(%s)" % (say % "nm-say"), seconds=90)
            check("Save: the shoots are renamed, and the line beside the button says so (through the page's own reloads)",
                  c.js(say % "nm-say") == "Done. This backup's shoots are renamed to match, and your next backup's will be named like 2026-06-04 Beach."
                  and c.js(beside % ("nm", "nm")), c.js(say % "nm-say"))
            folders = sorted(p.name for p in w["drive"].iterdir() if p.is_dir() and not p.name.startswith("."))
            check("on the drive too", "2026-06-04 Beach" in folders and "Beach_06-04-26" not in folders, str(folders))
            check("nothing in the section holds a path", no_path(w, c.js("document.getElementById('opts').innerText")))
            # another card, last: the page becomes the shoot's page
            c.wait_for("!document.getElementById('nm-open').disabled", seconds=20)
            c.js("document.getElementById('oc-open').click(); true")
            c.wait_for("document.querySelectorAll('#oc-list label').length > 0", seconds=30)
            labels = c.js("[...document.querySelectorAll('#oc-list label')].map(l => l.textContent)")
            day = this_computer.strftime(datetime.fromisoformat(DAY2), "%b %-d")
            check("This shoot continues on another card: the other backup by name, day and count, and the quiet line",
                  labels == [f"second card · {day} · 3 photos"] and c.js("document.getElementById('oc-none').hidden && !document.getElementById('oc-quiet').hidden")
                  and c.js(say % "oc-quiet") == "Each card's photos stay in their own folders.", str(labels))
            c.js("document.getElementById('oc-go').click(); true")
            c.wait_for("/^Done\\./.test(%s)" % (say % "oc-say"), seconds=60)
            check("Put them on one report: 'Done. Both cards are on one report now.' beside the button",
                  c.js(say % "oc-say") == "Done. Both cards are on one report now. Picked the wrong one? Tell the Assistant and it will take them apart.")
            c.wait_for("document.querySelectorAll('iframe.card-frame').length === 2", seconds=30)
            check("and the page reloads into the shoot's page, both cards in their frames",
                  "2 cards" in c.js("document.querySelector('.eyebrow').textContent") and c.js("location.pathname") == "/report.html")
            c.wait_for("(() => { const d = document.querySelectorAll('iframe.card-frame')[1].contentDocument; return !!(d && d.getElementById('oc-open')); })()", seconds=30)
            c.js("document.querySelectorAll('iframe.card-frame')[1].contentDocument.getElementById('oc-open').click(); true")
            c.wait_for("!document.querySelectorAll('iframe.card-frame')[1].contentDocument.getElementById('oc-none').hidden", seconds=30)
            check("inside card 2's frame the button works too, and with no backup left it says to back the other card up first",
                  c.js("document.querySelectorAll('iframe.card-frame')[1].contentDocument.getElementById('oc-none').textContent")
                  == "Back up the other card first: put it in and say backup now. Then come back here and pick it."
                  and c.js("document.querySelectorAll('iframe.card-frame')[1].contentDocument.getElementById('oc-go').hidden"))
            c.reload()
            c.wait_for("document.querySelectorAll('iframe.card-frame').length === 2", seconds=30)
            check("a reload keeps the shoot's page", True)
    finally:
        srv.kill()
        srv.communicate()
        chrome_drive.stop_all()
    check("after the browser, both cards are exactly as they were", t.card_snapshot(b["card"]) == b["before"] and t.card_snapshot(b2["card"]) == b2["before"])


def main():
    os.environ.pop("STUDIO_DRIVES_FOR_TESTS", None)
    work = Path(tempfile.mkdtemp(prefix="report-options-"))
    try:
        ok, how = t.pictures.ready()
        if not ok:
            SKIPPED.append("everything that needs a whole backup")
            print(f"  SKIP  everything that needs a whole backup   [this computer cannot make the small pictures yet: {how}]", flush=True)
        else:
            print("A pretend world: two drives, one whole backup")
            w = new_world(work, "world")
            w["drive"] = new_drive(w, "Big Kahuna", 2000)
            w["lacie"] = new_drive(w, "LaCie Rugged", 1000)
            w["old"] = new_drive(w, "Old Shoots", 500)
            for name in ("2025-01-04 Jones", "2025-02-11 Lee", "2025-03-09 Park"):
                (w["old"] / "Photo Shoots" / name).mkdir(parents=True)
            t.run("studio_file.py", "set", "--drive", w["drive"], "--offered", "1", "--file-names", "shoot", env=w["env"])
            b = a_backup(w, "CARD", "first card", DAY1, (5, 4), ["Beach", "Palms"], w["drive"])
            if b:
                the_words(w, b)
                srv, base = serve(w, b["records"])
                try:
                    a_hard_name(w, b, base)
                    the_guard(w, b, base)
                    next_drive(w, b, base)
                    naming(w, b, base)
                    b2 = another_card(w, b, base)
                finally:
                    srv.kill()
                    srv.communicate()
                if b2:
                    a_restart(w, b)
                    check("after everything, both cards are exactly as they were",
                          t.card_snapshot(b["card"]) == b["before"] and t.card_snapshot(b2["card"]) == b2["before"])
            own_disk(work)
            if "--chrome" in sys.argv:
                in_a_browser(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}" + (f" ({len(SKIPPED)} skipped)" if SKIPPED else ""))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
