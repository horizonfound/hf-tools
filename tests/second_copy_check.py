#!/usr/bin/env python3
"""Make a second copy, from the report, after the backup (Dustin, Nov 19: nothing is asked before the copy;
"they can choose whether they want to do a second backup or not"). second_copy.py copies photos onto a drive, so
this holds it to backup.py's promises: nothing deleted, nothing written over, safe to run twice, safe to cut off,
and "checked" meaning a hash matched.

Everything here is pretend: a scratch STUDIO_HOME, pretend drives (temp folders handed to the scripts through the
tests' switch STUDIO_DRIVES_FOR_TESTS, so the drives really plugged in are never looked at), a pretend card (a
temp folder with a DCIM), and one whole pretend backup made by night.py itself (copied, checked, sorted, settled,
one shoot renamed). The report's server runs on a scratch port with STUDIO_NO_WINDOWS_FOR_TESTS. No browser.

    python3 tests/second_copy_check.py
    python3 tests/guard.py 3000 python3 tests/second_copy_check.py --chrome    (also presses the button in a hidden Chrome)
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pc_smoke as t  # noqa: E402
import this_computer  # noqa: E402  (pc_smoke put the scripts folder on the path)

FAILED = []
SKIPPED = []
GB = 1024 ** 3
SESSION = "2026-11-19 copy card"
PAUSE = "STUDIO_SECOND_COPY_PAUSE_FOR_TESTS"


def check(what, ok, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {str(detail)[-900:]}"), flush=True)
    if not ok:
        FAILED.append(what)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree(folder):
    """{relative path: sha256} of every file under a folder, the hidden _studio left out."""
    folder = Path(folder)
    out = {}
    for p in sorted(folder.rglob("*")) if folder.is_dir() else []:
        rel = p.relative_to(folder).as_posix()
        if p.is_file() and not rel.startswith("_studio/"):
            out[rel] = sha(p)
    return out


def stamps(folder):
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): p.stat().st_mtime_ns for p in sorted(folder.rglob("*")) if p.is_file()}


def py(code, *args, env=None):
    """Run a few lines of Python beside the scripts, the way a script of the Assistant's would run them."""
    return t.run_python(["-c", f"import sys; sys.path.insert(0, {str(t.SCRIPTS)!r})\n" + code, *map(str, args)], env=env)


def status_of(b):
    code, out = py("import json, second_copy; print(json.dumps(second_copy.status(sys.argv[1])))", b["records"], env=b["env"])
    try:
        return json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"state": "?", "line": out}


def safe_of(b):
    code, out = py("import json, home_base; print(json.dumps(home_base.backup_status(sys.argv[1])))", b["records"], env=b["env"])
    try:
        return json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"error": out}


def manifest(b):
    return json.loads((b["records"] / "manifest.json").read_text(encoding="utf-8"))


def record(b):
    try:
        return json.loads((b["records"] / "second-copy.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def second(b, to, *more, env=None):
    return t.run("second_copy.py", b["records"], "--to", to, *more, env=dict(b["env"], **(env or {})))


def reset(b):
    """Put the pretend backup back to "no second copy", for the next case (a test's own tidying of its own
    scratch records; the Assistant itself never removes these)."""
    (b["records"] / "manifest.json").write_bytes(b["clean"])
    for name in ("second-copy.json", "manifest.before-second-copy.json"):
        try:
            (b["records"] / name).unlink()
        except OSError:
            pass
    for p in b["records"].glob("second-copy.older-*.json"):
        p.unlink()


def pull_card(b):
    """The card comes out: its folder is not where it was."""
    for _ in range(40):
        try:
            os.rename(b["card"], b["card_away"])
            return True
        except OSError:
            time.sleep(0.1)
    return False


def push_card(b):
    if b["card_away"].exists() and not b["card"].exists():
        os.rename(b["card_away"], b["card"])


def new_drive(b, name, free_gb=1000):
    """One more pretend drive plugged in."""
    p = b["base"] / "drives" / name
    p.mkdir(parents=True)
    rows = json.loads(b["listing"].read_text(encoding="utf-8"))
    rows.append({"path": str(p), "name": name, "shown": name, "total": 2000 * GB, "free": int(free_gb * GB),
                 "system": False, "removable": False, "id": None})
    b["listing"].write_text(json.dumps(rows), encoding="utf-8")
    return p


def a_finished_backup(work):
    """One whole pretend backup, made by night.py: copied and checked, sorted into two shoots, settled, and one
    shoot renamed afterwards. Returns what the cases need, or None when it could not be made."""
    base = work / "world"
    home, folders = base / "home", base / "folders"
    home.mkdir(parents=True)
    (folders / "Pictures").mkdir(parents=True)
    drive = base / "drives" / "Big Kahuna"
    drive.mkdir(parents=True)
    listing = base / "drives.json"
    listing.write_text(json.dumps([{"path": str(drive), "name": "Big Kahuna", "shown": "Big Kahuna", "total": 4000 * GB,
                                    "free": 2000 * GB, "system": False, "removable": False, "id": None}]), encoding="utf-8")
    env = {"STUDIO_HOME": str(home), "STUDIO_DRIVES_FOR_TESTS": str(listing),
           "STUDIO_FOLDERS_FOR_TESTS": str(folders), "STUDIO_NO_WINDOWS_FOR_TESTS": "1"}
    card = base / "CARD"
    photos = t.make_card(card, groups=(5, 4))
    (photos[0].with_suffix(".xmp")).write_bytes(b"<x:xmpmeta>a rating made in the camera</x:xmpmeta>")   # a sidecar from the card
    before = t.card_snapshot(card)
    t.run("studio_file.py", "set", "--drive", drive, "--offered", "1", "--file-names", "shoot", env=env)
    night = ["night.py", "--source", card, "--name", "copy card", "--date", "2026-11-19", "--no-peeks"]
    code, out = t.run(*night, env=env)
    st = drive / SESSION / "_studio"
    if code != 4:
        check("the pretend backup reaches the look (exit 4)", False, out)
        return None
    groups = json.loads((st / "groups.json").read_text(encoding="utf-8"))["groups"]
    shoots = [{"id": f"s{i}", "suggested": f"Shoot {i}", "groups": [g["id"]], "photos": g.get("count", 0),
               "recap": "Test frames.", "why": "test"} for i, g in enumerate(groups, 1)]
    (st / "shoots.json").write_text(json.dumps({"decided_by": "test", "shoots": shoots}), encoding="utf-8")
    code, out = t.run(*night, env=env)
    records = drive / ".studio" / SESSION
    check("the pretend backup finishes and settles (exit 0)", code == 0 and (records / "settled.json").is_file(), out)
    if not (records / "settled.json").is_file():
        return None
    code, out = t.run("rename_shoot.py", records, "--shoot", "s1", "--name", "Renamed beach", env=env)
    check("and one of its shoots is renamed afterwards", code == 0, out)
    m = json.loads((records / "manifest.json").read_text(encoding="utf-8"))
    check("the pretend backup holds the photos, the card's sidecar and a camera file that is not a photo",
          len(m["files"]) == len(photos) + 2 and "MISC/M01.CTG" in m["files"] and not m.get("second"), str(sorted(m["files"])))
    return {"base": base, "home": home, "env": env, "listing": listing, "drive": drive, "card": card,
            "card_away": base / "CARD (pulled out)", "records": records, "card_before": before,
            "clean": (records / "manifest.json").read_bytes(), "n": len(m["files"])}


# ---------------------------------------------------------------- the cases

def from_the_card(b):
    print("From the card, while it is still in")
    to = new_drive(b, "LaCie Rugged")
    safe_before = safe_of(b)
    code, out = second(b, to, "--check")
    check("--check says ready and writes nothing", code == 0 and "Ready:" in out and not any(to.iterdir())
          and not (b["records"] / "second-copy.json").exists(), out)
    code, out = second(b, to)
    got = tree(to / SESSION)
    m = manifest(b)
    want = {k: v["sha256"] for k, v in m["files"].items()}
    check("it finishes (exit 0) and says every file was checked", code == 0 and f"Second copy made on LaCie Rugged: {b['n']} files, every one checked." in out, out)
    check("every file is at its card path on the second drive, byte for byte the card's", got == want and got == {k: sha(b["card"] / k) for k in want},
          f"{sorted(set(got) ^ set(want))}")
    rec = record(b)
    check("every file was read from the card, and the record says so",
          rec.get("state") == "done" and rec.get("from_card") == b["n"] and rec.get("from_drive") == 0, str({k: rec.get(k) for k in ("state", "from_card", "from_drive")}))
    check("the done line does not speak of the drive when the card was used", "made from the copy" not in out and "upright" not in out, out)
    check("the backup's manifest now names the second copy, every file checked there",
          m.get("second") and Path(m["second"]).resolve() == (to / SESSION).resolve() and all(v.get("second", {}).get("ok") for v in m["files"].values()))
    check("the manifest before is kept beside it, once", (b["records"] / "manifest.before-second-copy.json").read_bytes() == b["clean"])
    copy = json.loads((to / SESSION / "_studio" / "manifest.json").read_text(encoding="utf-8"))
    check("the second drive has its own copy of the manifest, in a hidden _studio", copy.get("files", {}).keys() == m["files"].keys() and copy.get("second") == m["second"])
    check("the card is exactly as it was", t.card_snapshot(b["card"]) == b["card_before"])
    now = safe_of(b)
    check("the backup is still safe to format, and now has a second copy", safe_before.get("safe") is True and now.get("safe") is True
          and safe_before.get("second") is False and now.get("second") is True, f"{safe_before} {now}")
    page = (b["records"] / "report.html").read_text(encoding="utf-8")
    check("the report was rebuilt and says Second copy made on LaCie Rugged, in place of the button",
          "Second copy made on LaCie Rugged." in page and "id='sc-open' hidden" in page, page[-1500:] if "sc-open" not in page else "")
    check("the status for the page is done, with the honest line and no path",
          status_of(b).get("state") == "done" and str(b["base"]) not in json.dumps(status_of(b)), str(status_of(b)))

    print("Run twice")
    before_stamps, before_manifest = stamps(to), (b["records"] / "manifest.json").read_bytes()
    code, out = second(b, to)
    check("a second run says there is nothing to do (exit 0) and writes nothing",
          code == 0 and "already has a second copy, on LaCie Rugged. Nothing to do." in out and stamps(to) == before_stamps
          and (b["records"] / "manifest.json").read_bytes() == before_manifest, out)
    other = new_drive(b, "Another Drive")
    code, out = second(b, other)
    check("a second copy somewhere else is refused once one is complete, and nothing is written there",
          code == 2 and "already has a second copy, on LaCie Rugged" in out and not any(other.iterdir()), out)
    reset(b)


def from_the_drive(b):
    print("From the drive, after the settle and a rename, with the card out")
    to = new_drive(b, "Orange Drive")
    check("(the card comes out)", pull_card(b))
    code, out = second(b, to)
    want = {k: v["sha256"] for k, v in manifest(b)["files"].items()}
    got = tree(to / SESSION)
    check("it finishes (exit 0) in the same layout, the card's own, with the same hashes", code == 0 and got == want, f"{out[-500:]} {sorted(set(got) ^ set(want))}")
    check("the sidecar from the card and the camera's own file came along at their card paths",
          "MISC/M01.CTG" in got and any(k.endswith(".xmp") for k in got), str(sorted(got)))
    check("the done line says it was made from the copy on the drive, since the card wasn't in",
          "It was made from the copy on Big Kahuna, since the card wasn't in." in out, out)
    rec = record(b)
    check("the record says every file came from the drive", rec.get("from_drive") == b["n"] and rec.get("from_card") == 0, str(rec.get("from_drive")))
    check("nothing on the photo drive was renamed, moved or added outside the records",
          not (b["drive"] / SESSION).exists() and all(p.name != ".studio-partial" for p in b["drive"].rglob("*.studio-partial")))
    push_card(b)
    reset(b)


def a_turned_clip(b):
    print("A video clip the backup turned upright (36 bytes different from the card's)")
    m = manifest(b)
    index = json.loads((b["records"] / "index.json").read_text(encoding="utf-8"))
    p = next(x for x in index["photos"] if x.get("original"))
    key, at = p["original"], b["drive"] / p["file"]
    card_hash = m["files"][key]["sha256"]
    raw = bytearray(at.read_bytes())
    for i in range(40, 76):
        raw[i] ^= 0xFF
    at.write_bytes(bytes(raw))                      # the test plays clips.py rotate: same size, 36 bytes changed in place
    turned_hash = sha(at)
    m["files"][key].update({"sha256": turned_hash, "card_sha256": card_hash, "turned": 90})
    turned = json.dumps(m, indent=1).encode("utf-8")
    (b["records"] / "manifest.json").write_bytes(turned)
    clean, b["clean"] = b["clean"], turned
    try:
        to = new_drive(b, "Clip Drive A")
        code, out = second(b, to)
        check("read from the card, the clip is matched against the card's own hash and is the card's file",
              code == 0 and sha(to / SESSION / key) == card_hash and "upright" not in out, out)
        reset(b)
        to = new_drive(b, "Clip Drive B")
        pull_card(b)
        code, out = second(b, to)
        check("read from the drive, it is matched against the turned hash and is the upright file",
              code == 0 and sha(to / SESSION / key) == turned_hash, out)
        check("and the done line says so: 1 video clip is the upright one from your drive",
              "1 video clip is the upright one from your drive." in out, out)
        check("the manifest marks that one file's second copy as the turned one",
              manifest(b)["files"][key].get("second") == {"ok": True, "turned": True}, str(manifest(b)["files"][key].get("second")))
        push_card(b)
        reset(b)
    finally:
        push_card(b)
        raw = bytearray(at.read_bytes())
        for i in range(40, 76):
            raw[i] ^= 0xFF
        at.write_bytes(bytes(raw))                  # the pretend clip back as it was, for the cases after this
        b["clean"] = clean
        reset(b)
    check("(the pretend clip is back as the card's)", sha(at) == card_hash)


def start(b, to, pause="0.4"):
    cmd = [sys.executable, str(t.SCRIPTS / "second_copy.py"), str(b["records"]), "--to", str(to)]
    return subprocess.Popen(cmd, env=t.child_env(dict(b["env"], **{PAUSE: pause})), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding="utf-8", errors="replace")


def wait_done(b, n, limit=60):
    end = time.time() + limit
    while time.time() < end:
        if (record(b).get("done") or 0) >= n:
            return True
        time.sleep(0.05)
    return False


def cut_off(b):
    print("Cut off part way (the process killed), then run again")
    to = new_drive(b, "Cut Drive")
    safe_before = safe_of(b)
    p = start(b, to)
    try:
        check("(three files in)", wait_done(b, 3), str(record(b)))
        check("while it runs, the backup's manifest says nothing of a second copy", (b["records"] / "manifest.json").read_bytes() == b["clean"])
        check("and the backup's safe-to-format answer is what it was", safe_of(b) == safe_before, f"{safe_before} {safe_of(b)}")
        st = status_of(b)
        check("the status for the page is copying, reading the card, with a line and no path",
              st.get("state") == "copying" and st.get("card") is True and "Copying to Cut Drive:" in st.get("line", "")
              and str(b["base"]) not in json.dumps(st), str(st))
        code, out = second(b, to)
        check("a second run while one holds the lock is refused (exit 2)", code == 2 and "already being made" in out, out)
        other = new_drive(b, "Lock Drive")
        code, out = second(b, other, "--check")
        check("and so is a check for another drive, with nothing written there", code == 2 and "already being made" in out and not any(other.iterdir()), out)
        # The real answer is asked first, on this computer as it is; then eject() is walked past its PC refusal
        # with that same answer. Never ask copying_from() again with WINDOWS flipped off on a PC: with no fcntl
        # there it would ask still_running() the Mac way, and os.kill(pid, 0) is Ctrl+C on Windows.
        code, out = py("import eject_card as e\n"
                       "busy = e.copying_from(sys.argv[1])\n"
                       "print('COPYING' if busy else 'free')\n"
                       "e.copying_from = lambda p: busy\n"
                       "e.this_computer.WINDOWS = False\n"
                       "e.cards.answers = lambda p: True; e.is_card = lambda p: True; e.backed_up = lambda p: True\n"
                       "e.let_go = lambda p: (True, 'EJECTED')\n"
                       "print(e.eject(sys.argv[1]))", b["card"], env=b["env"])
        check("Eject my card refuses while the second copy is reading that card, with one plain line",
              "COPYING" in out and "(2, \"A second copy is still being made from this card. It won't be long.\")" in out, out)
    finally:
        p.kill()
        p.communicate()
    time.sleep(0.2)
    at_kill = record(b)
    done_then = [k for k, r in at_kill.get("files", {}).items() if r.get("ok")]
    stamps_then = {k: (to / SESSION / k).stat().st_mtime_ns for k in done_then}
    idents_then = {k: (to / SESSION / k).stat().st_ino for k in done_then}
    check("killed part way: some files done, not all, and the manifest still untouched",
          0 < len(done_then) < b["n"] and (b["records"] / "manifest.json").read_bytes() == b["clean"], f"{len(done_then)} of {b['n']}")
    st = status_of(b)
    check("the status now says it stopped, in plain words, that nothing was removed, and how to carry on",
          st.get("state") == "stopped" and "Nothing was removed. Press Make a second copy to carry on." in st.get("line", "")
          and str(b["base"]) not in json.dumps(st), str(st))
    check("the backup is still safe to format, with no second copy claimed", safe_of(b) == safe_before, str(safe_of(b)))
    code, out = py("import eject_card as e\nprint('COPYING' if e.copying_from(sys.argv[1]) else 'free')", b["card"], env=b["env"])
    check("and Eject my card no longer waits for it", "free" in out, out)
    (to / SESSION / "DCIM").mkdir(parents=True, exist_ok=True)
    code, out = second(b, to)
    got, want = tree(to / SESSION), {k: v["sha256"] for k, v in manifest(b)["files"].items()}
    check("the next run finishes it (exit 0), every file there and right", code == 0 and got == want, out)
    check("nothing was copied twice: the files done before the kill are the very same files",
          all((to / SESSION / k).stat().st_mtime_ns == stamps_then[k] and (to / SESSION / k).stat().st_ino == idents_then[k] for k in done_then))
    check("no unfinished file is left on the second drive", not list(to.rglob("*.studio-partial")), str(list(to.rglob("*.studio-partial"))))
    reset(b)


def card_pulled(b):
    print("The card pulled half way")
    to = new_drive(b, "Pulled Drive")
    p = start(b, to)
    try:
        check("(three files in, from the card)", wait_done(b, 3) and record(b).get("reading") == "card", str(record(b).get("reading")))
        check("(the card comes out)", pull_card(b))
        out, _ = p.communicate(timeout=120)
    finally:
        if p.poll() is None:
            p.kill()
            p.communicate()
        push_card(b)
    rec = record(b)
    got, want = tree(to / SESSION), {k: v["sha256"] for k, v in manifest(b)["files"].items()}
    check("the copy carries on from the drive and finishes (exit 0), every file right", p.returncode == 0 and got == want, out)
    check("some files came from the card and the rest from the drive", (rec.get("from_card") or 0) >= 3 and (rec.get("from_drive") or 0) >= 1
          and rec.get("from_card") + rec.get("from_drive") == b["n"], f"{rec.get('from_card')} + {rec.get('from_drive')}")
    check("and the done line says how many came from the drive", f"{rec.get('from_drive')} of them came from the copy on Big Kahuna, since the card wasn't in for those." in out, out)
    check("no unfinished file is left", not list(to.rglob("*.studio-partial")))
    reset(b)


def already_there(b):
    print("A file already on the second drive")
    to = new_drive(b, "Busy Drive")
    keys = sorted(manifest(b)["files"])
    differs, same = keys[0], keys[1]
    (to / SESSION / differs).parent.mkdir(parents=True)
    (to / SESSION / differs).write_bytes(b"somebody else's file, kept")
    shutil.copy2(b["card"] / same, to / SESSION / same)
    same_stamp = (to / SESSION / same).stat().st_mtime_ns
    safe_before = safe_of(b)
    for attempt in ("first", "second"):
        code, out = second(b, to)
        check(f"a different file already there is never written over ({attempt} run): exit 1, the file as it was",
              code == 1 and (to / SESSION / differs).read_bytes() == b"somebody else's file, kept", out)
    check("it is a problem that says so in plain words, counted honestly",
          "1 file already on Busy Drive is different from your backup, so I left it alone." in out
          and f"{b['n'] - 1} of {b['n']} files are copied and checked so far." in out, out)
    rec = record(b)
    check("the record keeps it as exists-and-differs, and the state is stopped", rec.get("files", {}).get(differs, {}).get("note") == "exists and differs"
          and rec.get("state") == "stopped" and rec.get("done") == b["n"] - 1, str(rec.get("files", {}).get(differs)))
    check("an identical file already there is kept as it is and counted as checked",
          rec["files"][same].get("ok") and "already there" in rec["files"][same].get("note", "") and (to / SESSION / same).stat().st_mtime_ns == same_stamp)
    check("the backup's manifest is not changed, and safe to format is what it was",
          (b["records"] / "manifest.json").read_bytes() == b["clean"] and safe_of(b) == safe_before and safe_before.get("safe") is True, str(safe_of(b)))
    st = status_of(b)
    check("the page's line holds no path", st.get("state") == "stopped" and str(b["base"]) not in json.dumps(st) and "DCIM" not in st.get("line", ""), str(st))
    reset(b)


def own_failed_copy(b):
    print("Only this copy's own failed attempt may be written again")
    to = new_drive(b, "Redo Drive")
    keys = sorted(manifest(b)["files"])
    ours, theirs = keys[2], keys[3]
    for k, body in ((ours, b"half of a copy that broke off"), (theirs, b"put here by somebody since")):
        (to / SESSION / k).parent.mkdir(parents=True, exist_ok=True)
        (to / SESSION / k).write_bytes(body)
    st = (to / SESSION / ours).stat()
    # the record of a run that broke off on both: for one, what is there is exactly what that run left; for the
    # other, something else is there now (its size, time and number are not what the run left)
    rec = {"to": str((to / SESSION).resolve()), "to_name": "Redo Drive", "state": "stopped", "files": {
        ours: {"ok": False, "note": "OSError", "left": [st.st_size, st.st_mtime_ns, st.st_ino]},
        theirs: {"ok": False, "note": "OSError", "left": [1, 2, 3]}}}
    (b["records"] / "second-copy.json").write_text(json.dumps(rec), encoding="utf-8")
    code, out = second(b, to)
    want = manifest(b)["files"]
    check("its own failed copy is written again and is right", sha(to / SESSION / ours) == want[ours]["sha256"], out)
    check("a file that is not what the failed run left is never written over (exit 1)",
          code == 1 and (to / SESSION / theirs).read_bytes() == b"put here by somebody since", out)
    check("and the manifest is not changed", (b["records"] / "manifest.json").read_bytes() == b["clean"])
    reset(b)


def changed_source(b):
    print("A source that no longer matches what the backup recorded")
    to = new_drive(b, "Careful Drive")
    index = json.loads((b["records"] / "index.json").read_text(encoding="utf-8"))
    p = [x for x in index["photos"] if x.get("original")][2]
    key, at = p["original"], b["drive"] / p["file"]
    good = at.read_bytes()
    bad = bytearray(good)
    bad[100] ^= 0xFF
    pull_card(b)
    try:
        at.write_bytes(bytes(bad))                  # the copy on their drive has changed since the backup (same size)
        code, out = second(b, to)
        check("a changed photo on the drive is a problem (exit 1), not counted",
              code == 1 and "1 photo on your drive no longer matches what the backup recorded, so it was not copied." in out
              and f"{b['n'] - 1} of {b['n']} files" in out, out)
        check("it is not left under the photo's name on the second drive", not (to / SESSION / key).exists(), str(list((to / SESSION / key).parent.iterdir())))
        check("the others were copied and are right", len(tree(to / SESSION)) >= b["n"] - 1 - 1 + 0 and
              all(v == manifest(b)["files"][k]["sha256"] for k, v in tree(to / SESSION).items() if not k.endswith(".studio-partial")))
        check("the manifest is not changed", (b["records"] / "manifest.json").read_bytes() == b["clean"])
        at.write_bytes(good)                        # the photo is right again
        code, out = second(b, to)
        got = {k: v for k, v in tree(to / SESSION).items()}
        check("once the photo is right again, the next run finishes (exit 0) with no unfinished file left",
              code == 0 and got == {k: v["sha256"] for k, v in manifest(b)["files"].items()}, f"{out[-400:]} {sorted(got)}")
    finally:
        at.write_bytes(good)
        push_card(b)
        reset(b)


def edited_since(b):
    print("Photos saved over since the backup, with the card out (Nov 19 review)")
    to = new_drive(b, "Edits Drive")
    index = json.loads((b["records"] / "index.json").read_text(encoding="utf-8"))
    two = [b["drive"] / x["file"] for x in index["photos"] if x.get("original")][:2]
    good = [p.read_bytes() for p in two]
    pull_card(b)
    try:
        for p in two:
            p.write_bytes(p.read_bytes() + b" a rating written into the file")     # an editing program saved over it
        outs = [second(b, to, *more) for more in (("--check",), (), ())]
        check("refused up front (exit 2), with --check and without, every time: never 'Ready', never part of a copy",
              all(c == 2 and "Ready" not in o for c, o in outs) and not any(to.iterdir())
              and not (b["records"] / "second-copy.json").exists(), str(outs))
        out = outs[0][1]
        check("it says the photos were changed, that they are still on the drive, and what would make a copy possible",
              "2 photos on Big Kahuna have been changed since the backup" in out and "Your photos on Big Kahuna are still there." in out
              and "put it in and press Make a second copy" in out and "can't get a checked second copy any more" in out, out)
        check("it never says they could not be found", "could not be found" not in " ".join(o for _, o in outs), out)
        check("the two photos were not touched by any of it", all(p.read_bytes() == g + b" a rating written into the file" for p, g in zip(two, good)))
        push_card(b)
        code, out = second(b, to)
        check("with the card back in, the copy is made from the card (exit 0), every file checked",
              code == 0 and {k: v for k, v in tree(to / SESSION).items()} == {k: v["sha256"] for k, v in manifest(b)["files"].items()}, out[-400:])
    finally:
        for p, g in zip(two, good):
            p.write_bytes(g)
        push_card(b)
        reset(b)


def refusals(b):
    print("Refused before a byte is written")
    def refused(what, to, words, **edit):
        m = json.loads(b["clean"].decode("utf-8"))
        if edit:
            edit["change"](m)
            (b["records"] / "manifest.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
        held = (b["records"] / "manifest.json").read_bytes()
        before = stamps(to) if Path(to).is_dir() else None
        ok = True
        said = ""
        for more in (("--check",), ()):
            code, out = second(b, to, *more)
            said = out
            ok = ok and code == 2 and words in out and (stamps(to) if Path(to).is_dir() else None) == before \
                and not (b["records"] / "second-copy.json").exists() and (b["records"] / "manifest.json").read_bytes() == held
        check(f"{what}: refused (exit 2) with --check and without, nothing written", ok, said)
        if edit:
            (b["records"] / "manifest.json").write_bytes(b["clean"])

    spare = new_drive(b, "Spare Drive")
    refused("onto the drive the photos are on", b["drive"], "That is the drive your photos are already on (Big Kahuna).")
    (b["drive"] / "Second copies").mkdir()
    refused("into a folder on the drive the photos are on", b["drive"] / "Second copies", "That is the drive your photos are already on (Big Kahuna).")
    refused("onto the memory card", b["card"], "That is the memory card itself.")
    # Nov 19 review: any memory card, not only this backup's own while it is in under the name the backup recorded
    other_card = b["base"] / "drives" / "EOS_DIGITAL 2"
    (other_card / "DCIM" / "100CANON").mkdir(parents=True)
    (other_card / "DCIM" / "100CANON" / "IMG_0001.JPG").write_bytes(b"a photo not backed up yet")
    (other_card / "Second copies").mkdir()
    refused("onto another memory card", other_card, "That is a memory card.")
    refused("into a folder on another memory card", other_card / "Second copies", "That is a memory card.")
    video_card = b["base"] / "drives" / "XQD_VIDEO"
    (video_card / "PRIVATE" / "M4ROOT" / "CLIP").mkdir(parents=True)
    refused("onto a video camera's card (no DCIM)", video_card, "That is a memory card.")
    shoot = json.loads((b["records"] / "shoots.json").read_text(encoding="utf-8"))["shoots"][0]["folder"]
    refused("inside the backup's own folders", b["drive"] / shoot, "inside the backup's own folder")
    tiny = new_drive(b, "Tiny Drive", free_gb=0.5)
    refused("not enough room", tiny, "Not enough room on Tiny Drive")
    refused("a drive that is not there", b["base"] / "drives" / "Nowhere", "I can't see that drive right now.")
    refused("a sample backup", spare, "was a sample of the card", change=lambda m: m.update(sample={"kept": 3, "of": 9}))
    refused("an unfinished backup", spare, "isn't finished yet", change=lambda m: m.pop("finished"))
    refused("a backup with a file not checked", spare, "isn't finished yet",
            change=lambda m: m["files"][sorted(m["files"])[0]].update(dest={"ok": False}))
    refused("a backup that stopped with a problem", spare, "stopped with a problem", change=lambda m: m.update(problems=["x would not copy"]))
    code, out = t.run("second_copy.py", b["base"] / "no such backup", "--to", spare, env=b["env"])
    check("records that cannot be found: refused (exit 2)", code == 2 and "I can't find that backup's records." in out and not any(spare.iterdir()), out)
    # a folder of the same name on the second drive that holds a different backup
    (spare / SESSION / "_studio").mkdir(parents=True)
    (spare / SESSION / "_studio" / "manifest.json").write_text(json.dumps({"files": {"DCIM/100CANON/OTHER.JPG": {"size": 3, "sha256": "ab"}}}), encoding="utf-8")
    refused("a folder of that name holding another backup", spare, "holding a different backup")
    code, out = second(b, spare, "--check", "--json")
    try:
        last = json.loads(out.strip().splitlines()[-1])
    except ValueError:
        last = {}
    check("--json ends with one line the report's server can read", last.get("ok") is False and last.get("state") == "another_there" and "words" in last, out)
    check("no refusal line holds a path", str(b["base"]) not in last.get("words", "x" + str(b["base"])))


def the_page(b):
    print("The report's button and its routes")
    code, out = t.run("report_page.py", b["records"], env=b["env"])
    page = (b["records"] / "report.html").read_text(encoding="utf-8")
    start_at = page.find("<section class='wrap opts'")
    section = page[start_at:page.find("</section>", start_at)] if start_at >= 0 else ""
    check("the report has the section under the shoots: the heading and its line",
          "Anything you&#x27;d like to change?" in section and "Your photos are safe either way. These are here if you want them." in section
          and 0 < page.find("class='shoot") < start_at, section[:300])
    for words in ("Make a second copy", "Which drive should the second copy go on?", "Look again", "Do this after every backup",
                  "Make the second copy", "Keep your card in until this is done.", "I can&#x27;t see another drive. Plug one in, then press Look again."):
        check(f"the panel says: {words.replace('&#x27;', chr(39))}", words in section)
    check("no path is written anywhere in the section, and no em dash", str(b["base"]) not in section and "/Volumes" not in section and "—" not in section)
    check("its routes are asked for by relative address, so they work inside /card/N/ too",
          "fetch('second-status'" in page and "fetch('second-drives'" in page and "fetch('second-copy'" in page)

    to = new_drive(b, "LaCie Page")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = subprocess.Popen([sys.executable, str(t.SCRIPTS / "serve_report.py"), str(b["records"]), "--port", str(port)],
                           env=t.child_env(b["env"]), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding="utf-8", errors="replace")
    try:
        line = srv.stdout.readline()
        base = line.split("Report:", 1)[1].strip().rsplit("/", 1)[0] if "Report:" in line else f"http://127.0.0.1:{port}"

        def get(path):
            with urllib.request.urlopen(base + path, timeout=20) as r:
                return r.status, r.read().decode("utf-8")

        def post(path, body, **headers):
            req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                                         headers=dict({"Content-Type": "application/json"}, **headers))
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return r.status, r.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                return e.code, e.read().decode("utf-8")

        code, body = get("/second-drives")
        rows = json.loads(body).get("drives", [])
        names = [r["name"] for r in rows]
        check("second-drives lists the other drives by name and free space, not the photo drive",
              code == 200 and "LaCie Page" in names and "Big Kahuna" not in names and all(r["free"].endswith(" free") for r in rows), body)
        check("and never a path", str(b["base"]) not in body and "path" not in body and "/" not in body and "\\" not in body, body)
        me = next(r for r in rows if r["name"] == "LaCie Page")
        code, body = get("/second-status")
        check("second-status with nothing started says none", code == 200 and json.loads(body).get("state") == "none", body)
        code, body = post("/second-copy", {"drive": me["i"], "name": "LaCie Page", "always": False}, Origin="http://evil.example")
        check("the POST from another website's page is refused (403)", code == 403, f"{code} {body}")
        code, body = post("/second-copy", {"drive": me["i"], "name": "LaCie Page", "always": False}, **{"Sec-Fetch-Site": "cross-site"})
        check("and one the browser marks cross-site is refused (403)", code == 403, f"{code} {body}")
        time.sleep(0.5)
        check("and nothing was started or written by them", not any(to.iterdir()) and not (b["records"] / "second-copy.json").exists()
              and (b["records"] / "manifest.json").read_bytes() == b["clean"])
        wrong = next(r for r in rows if r["name"] != "LaCie Page")
        code, body = post("/second-copy", {"drive": wrong["i"], "name": "LaCie Page", "always": False})
        check("a drive index whose name does not match is refused, in plain words", code == 409 and json.loads(body).get("ok") is False
              and "Look again" in json.loads(body).get("words", ""), f"{code} {body}")
        code, body = post("/second-copy", {"drive": "0", "name": "LaCie Page"})
        check("a body that is not {drive, name, always} is refused", code == 400, f"{code} {body}")
        code, body = post("/second-copy", {"drive": 99, "name": "LaCie Page", "always": False})
        check("a drive that is not on the list is refused", code == 409, f"{code} {body}")
        check("still nothing written", not any(to.iterdir()) and (b["records"] / "manifest.json").read_bytes() == b["clean"])
        tiny = next(r for r in rows if r["name"] == "Tiny Drive")
        code, body = post("/second-copy", {"drive": tiny["i"], "name": "Tiny Drive", "always": False})
        check("a drive without room is refused beside the button, in second_copy's own plain words",
              code == 200 and json.loads(body).get("ok") is False and "Not enough room on Tiny Drive" in json.loads(body).get("words", "")
              and str(b["base"]) not in body, body)
        code, body = post("/second-copy", {"drive": me["i"], "name": "LaCie Page", "always": True})
        check("the right press starts the copy", code == 200 and json.loads(body).get("ok") is True and "LaCie Page" in json.loads(body).get("words", ""), body)
        seen, st = [], {}
        end = time.time() + 120
        while time.time() < end:
            code, body = get("/second-status")
            st = json.loads(body)
            seen.append(body)
            if st.get("state") in ("done", "stopped"):
                break
            time.sleep(0.2)
        check("second-status follows it to done, with the honest line", st.get("state") == "done"
              and f"Second copy made on LaCie Page: {b['n']} files, every one checked." in st.get("line", ""), str(st))
        check("no status the page was given ever held a path", all(str(b["base"]) not in s and "DCIM" not in s for s in seen))
        got, want = tree(to / SESSION), {k: v["sha256"] for k, v in manifest(b)["files"].items()}
        check("the copy the button made is whole and right", got == want)
        sf = json.loads((b["home"] / "studio.json").read_text(encoding="utf-8"))
        check("Do this after every backup saved that drive as the second copy in the Studio File",
              sf.get("drives", {}).get("second") and Path(sf["drives"]["second"]).resolve() == to.resolve(), str(sf.get("drives")))
        code, page = get("/report.html")
        check("the report now shows Second copy made on LaCie Page in place of the button",
              "Second copy made on LaCie Page." in page and "id='sc-open' hidden" in page)
        code, body = get("/second-drives")
        me = next(r for r in json.loads(body)["drives"] if r["name"] == "LaCie Page")
        code, body = post("/second-copy", {"drive": me["i"], "name": "LaCie Page", "always": False})
        check("pressing again when it is made changes nothing and says so", code == 200 and json.loads(body).get("ok") is False
              and "already has a second copy" in json.loads(body).get("words", ""), body)
    finally:
        srv.kill()
        srv.communicate()
    t.run("studio_file.py", "set", "--no-second", env=b["env"])
    reset(b)


def the_page_in_a_browser(b, work):
    """The same button pressed by a real page, in a hidden Chrome (only with --chrome; run under tests/guard.py)."""
    print("The report's button, pressed in a hidden browser")
    import chrome_drive
    t.run("report_page.py", b["records"], env=b["env"])     # the report as it stands now: no second copy yet
    to = new_drive(b, "LaCie Browser")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = subprocess.Popen([sys.executable, str(t.SCRIPTS / "serve_report.py"), str(b["records"]), "--port", str(port)],
                           env=t.child_env(dict(b["env"], **{PAUSE: "0.5"})), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           encoding="utf-8", errors="replace")
    try:
        line = srv.stdout.readline()
        base = line.split("Report:", 1)[1].strip().rsplit("/", 1)[0]
        with chrome_drive.Chrome(work=str(work / "chrome"), size=(1280, 900)) as c:
            c.open(base + "/report.html")
            check("the section is on the page, its panel closed and nothing said yet",
                  c.js("document.querySelector('#opts h2').textContent") == "Anything you'd like to change?"
                  and c.js("document.getElementById('sc-panel').hidden && !document.getElementById('sc-open').hidden && document.getElementById('sc-say').textContent === ''"),
                  c.js("JSON.stringify([document.querySelector('#opts h2').textContent, document.getElementById('sc-panel').hidden, document.getElementById('sc-open').hidden, document.getElementById('sc-say').textContent])"))
            c.js("document.getElementById('sc-open').click(); true")
            c.wait_for("document.querySelectorAll('#sc-drives label').length > 0", seconds=15)
            labels = c.js("[...document.querySelectorAll('#sc-drives label')].map(l => l.textContent)")
            check("a press opens the panel right there, with each other drive by name and free space",
                  c.js("!document.getElementById('sc-panel').hidden") and any(x.startswith("LaCie Browser, ") and x.endswith(" free") for x in labels)
                  and not any("Big Kahuna" in x or "/" in x for x in labels), str(labels))
            check("Make the second copy waits for a drive to be chosen", c.js("document.getElementById('sc-go').disabled") is True)
            if os.environ.get("SECOND_COPY_SHOT"):      # a picture of the open panel, for a person to look at
                c.js("document.getElementById('opts').scrollIntoView({block:'center'}); true")
                shutil.copy(c.screenshot("second-copy-panel.png"), os.environ["SECOND_COPY_SHOT"])
            c.js("[...document.querySelectorAll('#sc-drives label')].find(l => l.textContent.startsWith('LaCie Browser')).querySelector('input').click(); true")
            check("and is ready once one is", c.js("document.getElementById('sc-go').disabled") is False)
            c.js("document.getElementById('sc-go').click(); true")
            c.wait_for("/^Copying to LaCie Browser: \\d+ of \\d+\\.$/.test(document.getElementById('sc-say').textContent)", seconds=30)
            check("the progress is said beside the button, the panel closed and the button resting",
                  c.js("document.getElementById('sc-panel').hidden && document.getElementById('sc-open').disabled")
                  and c.js("(() => { const a = document.getElementById('sc-open').getBoundingClientRect(), s = document.getElementById('sc-say').getBoundingClientRect();"
                           " return Math.abs(a.top - s.top) < 60 && s.width > 0; })()"),
                  c.js("JSON.stringify([document.getElementById('sc-panel').hidden, document.getElementById('sc-open').disabled, document.getElementById('sc-open').getBoundingClientRect().top, document.getElementById('sc-say').getBoundingClientRect().top, document.getElementById('sc-say').getBoundingClientRect().width])"))
            check("with the keep-your-card-in line while it reads the card",
                  c.js("!document.getElementById('sc-keep').hidden && document.getElementById('sc-keep').textContent") == "Keep your card in until this is done.")
            c.reload()
            c.wait_for("/^Copying to LaCie Browser/.test(document.getElementById('sc-say').textContent)", seconds=30)
            check("a reload picks the running copy up again", True)
            c.wait_for("!document.getElementById('sc-made').hidden && /every one checked/.test(document.getElementById('sc-made').textContent)", seconds=120)
            check("when it is done the page says so in place of the button, with the honest line",
                  c.js("document.getElementById('sc-open').hidden && document.getElementById('sc-keep').hidden")
                  and f"Second copy made on LaCie Browser: {b['n']} files, every one checked." in c.js("document.getElementById('sc-made').textContent"),
                  c.js("document.getElementById('sc-made').textContent"))
            check("nothing on the page holds a path", str(b["base"]) not in c.js("document.getElementById('opts').innerText"))
    finally:
        srv.kill()
        srv.communicate()
        chrome_drive.stop_all()
    got, want = tree(to / SESSION), {k: v["sha256"] for k, v in manifest(b)["files"].items()}
    check("and the copy the page asked for is whole and right", got == want)
    reset(b)


def drive_not_plugged_in(b, work):
    print("A saved second drive that is not plugged in no longer stops a backup")
    gone = b["base"] / "drives" / "Not Plugged In"
    gone.mkdir(parents=True)
    t.run("studio_file.py", "set", "--second", gone, env=b["env"])
    gone.rmdir()
    card = b["base"] / "CARD 2"
    t.make_card(card, groups=(3,))
    for p in (card / "DCIM" / "100CANON").glob("*.JPG"):     # other photos than the first card's
        p.write_bytes(p.read_bytes() + b"second card")
    code, out = t.run("night.py", "--source", card, "--check", env=b["env"])
    check("the quiet check passes and notes it, for the assistant only", code == 0 and "PREFLIGHT OK" in out and "is not plugged in" in out, out)
    code, out = t.run("night.py", "--source", card, "--name", "missed card", "--date", "2026-11-19", "--no-peeks", env=b["env"])
    st = b["drive"] / "2026-11-19 missed card" / "_studio"
    m = json.loads((st / "manifest.json").read_text(encoding="utf-8")) if (st / "manifest.json").is_file() else {}
    check("backup now carries on with one copy (exit 4, the look) where it used to stop",
          code == 4 and m.get("files") and all(v.get("dest", {}).get("ok") for v in m["files"].values()) and not m.get("second"), out)
    check("and puts on record that the second drive was missed", (st / "second-missed.json").is_file())
    t.run("report_page.py", st.parent, env=b["env"])
    page = (st / "report.html").read_text(encoding="utf-8") if (st / "report.html").is_file() else ""
    check("the report's top says so, pointing at the button",
          "Your second drive wasn&#x27;t plugged in, so there&#x27;s one copy for now. Plug it in and press Make a second copy." in page
          and "safe to format" in page, page[:200])
    card3 = b["base"] / "CARD 3"
    t.make_card(card3, groups=(2,))
    code, out = t.run("night.py", "--source", card3, "--name", "typed card", "--date", "2026-11-19", "--second", gone, "--check", env=b["env"])
    check("a second drive typed for that one backup still stops it (exit 2)", code == 2 and "second-copy folder is not there" in out, out)
    t.run("studio_file.py", "set", "--no-second", env=b["env"])


def words_and_help():
    print("Words")
    import second_copy
    import report_page
    lines = list(second_copy.OUR_WORDS.values()) + list(report_page.OUR_WORDS.values())
    check("no line of ours has an em dash, names Claude, or says she or he",
          not any("—" in w or "Claude" in w or " she " in f" {w.lower()} " or " he " in f" {w.lower()} " for w in lines))
    check("no line of ours holds a path or a Python word", not any("/" in w or "\\" in w or "Error" in w or "Traceback" in w for w in lines),
          str([w for w in lines if "/" in w or "\\" in w]))
    check("the plan's exact lines are there", report_page.OUR_WORDS["opts_h"] == "Anything you'd like to change?"
          and report_page.OUR_WORDS["opts_lede"] == "Your photos are safe either way. These are here if you want them."
          and second_copy.OUR_WORDS["eject_wait"] == "A second copy is still being made from this card. It won't be long."
          and second_copy.OUR_WORDS["missed"].startswith("Your second drive wasn't plugged in, so there's one copy for now."))
    src = (t.SCRIPTS / "second_copy.py").read_text(encoding="utf-8")
    check("second_copy.py uses backup.py's own functions and has no copy of them",
          all(f"backup.{f}(" in src for f in ("copy_with_hash", "sha256_of", "identity", "ours_to_redo", "onto_itself"))
          and "def copy_with_hash" not in src and "def ours_to_redo" not in src and "def sha256_of" not in src)
    code, out = t.run("second_copy.py", "--help")
    check("its help names --to, --check and the exit codes", code == 0 and "--to" in out and "--check" in out and "refused before anything was written" in " ".join(out.split()), out)


def main():
    os.environ.pop("STUDIO_DRIVES_FOR_TESTS", None)
    work = Path(tempfile.mkdtemp(prefix="second-copy-"))
    try:
        words_and_help()
        ok, how = t.pictures.ready()
        if not ok:
            SKIPPED.append("everything that needs a whole backup")
            print(f"  SKIP  everything that needs a whole backup   [this computer cannot make the small pictures yet: {how}]", flush=True)
        else:
            print("One whole pretend backup, for every case below")
            b = a_finished_backup(work)
            if b:
                from_the_card(b)
                from_the_drive(b)
                a_turned_clip(b)
                cut_off(b)
                card_pulled(b)
                already_there(b)
                own_failed_copy(b)
                changed_source(b)
                edited_since(b)
                refusals(b)
                the_page(b)
                if "--chrome" in sys.argv:
                    the_page_in_a_browser(b, work)
                drive_not_plugged_in(b, work)
                check("after everything, the first card is exactly as it was", t.card_snapshot(b["card"]) == b["card_before"])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}" + (f" ({len(SKIPPED)} skipped)" if SKIPPED else ""))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
