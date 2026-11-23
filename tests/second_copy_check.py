#!/usr/bin/env python3
"""Make a second copy, from the report, after the backup (Dustin, Nov 19: nothing is asked before the copy;
"they can choose whether they want to do a second backup or not"). second_copy.py copies photos onto a drive, so
this holds it to backup.py's promises: nothing deleted, nothing written over, safe to run twice, safe to cut off,
and "checked" meaning a hash matched.

Since Nov 23 (Nicole: "it should look just like the main drive"; second drive: "ask each time") a new second copy
has the photo drive's own shoot folders and photo names, follows a rename or a join (second_copy.follow), and
nothing is remembered for the next backup. A copy made before that, in the card's own layout, is left as it is.

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


MIRROR = ".studio-second"       # the hidden folder on a second drive that keeps a copy's own records


def tree(folder):
    """{relative path: sha256} of every file under a folder, the hidden _studio left out."""
    folder = Path(folder)
    out = {}
    for p in sorted(folder.rglob("*")) if folder.is_dir() else []:
        rel = p.relative_to(folder).as_posix()
        if p.is_file() and not rel.startswith("_studio/"):
            out[rel] = sha(p)
    return out


def mirror_tree(to, session=SESSION):
    """{relative path: sha256} of everything on a second drive, apart from the copy's own two record files and
    whatever it set aside."""
    own = (f"{MIRROR}/{session}/manifest.json", f"{MIRROR}/{session}/second-copy.json")
    return {k: v for k, v in tree(to).items() if k not in own and not k.startswith(f"{MIRROR}/{session}/set-aside/")}


def listing(folder):
    """Every file's name under a folder exactly as the folders list it (capital letters as they are)."""
    out = []
    for dirpath, _, names in os.walk(folder):
        out += [(Path(dirpath) / n).relative_to(folder).as_posix() for n in names]
    return sorted(out)


def shoot_folders(records):
    sh = json.loads((Path(records) / "shoots.json").read_text(encoding="utf-8"))["shoots"]
    return sorted({s["folder"] for s in sh if s.get("folder")})


def expected(records, session=SESSION):
    """What a second copy of this backup must hold, worked out here from the photo drive itself and from nothing
    second_copy.py says: every file in the shoots' own folders under the very same folder and name (inside the day
    folder while the backup has not settled), and what the sort set aside, in the copy's hidden records."""
    records = Path(records)
    if records.name == "_studio":
        root, pre = records.parent, records.parent.name + "/"
    else:
        root, pre = records.parent.parent, ""
    out = {}
    for folder in shoot_folders(records):
        for rel, h in tree(root / folder).items():
            out[f"{pre}{folder}/{rel}"] = h
    for key in json.loads((records / "manifest.json").read_text(encoding="utf-8"))["files"]:
        aside = records / "from-the-card" / key
        if aside.is_file():
            out[f"{MIRROR}/{session}/from-the-card/{key}"] = sha(aside)
    return out


def rel_of(b):
    """card path -> where that file's copy belongs on a second drive (the test's own working-out)."""
    index = json.loads((b["records"] / "index.json").read_text(encoding="utf-8"))
    now = {p["original"]: p["file"] for p in index["photos"] if p.get("original")}
    out = {}
    for key in manifest(b)["files"]:
        photo = now.get(str(Path(key).with_suffix(".JPG").as_posix()))
        if key in now:
            out[key] = now[key]
        elif key.lower().endswith(".xmp") and photo:
            out[key] = Path(photo).with_suffix(Path(key).suffix).as_posix()
        else:
            out[key] = f"{MIRROR}/{SESSION}/from-the-card/{key}"
    return out


def numbers(folder):
    """{the drive's own number for a file: its modified time} for every file under a folder: the same set before
    and after means files were renamed, never copied."""
    folder = Path(folder)
    return {p.stat().st_ino: p.stat().st_mtime_ns for p in folder.rglob("*") if p.is_file() and MIRROR not in p.parts}


def follow(b, *more, env=None):
    code, out = t.run("second_copy.py", "follow", b["records"], "--json", *more, env=dict(b["env"], **(env or {})))
    try:
        return code, json.loads(out.strip().splitlines()[-1]), out
    except (ValueError, IndexError):
        return code, {}, out


def rename(b, shoot, name):
    return t.run("rename_shoot.py", b["records"], "--shoot", shoot, "--name", name, env=b["env"])


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
    for name in ("second-copy.json", "manifest.before-second-copy.json", "second-follow-log.json", "second-missed.json"):
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
    print("From the card, while it is still in: the copy looks like the photo drive")
    to = new_drive(b, "LaCie Rugged")
    safe_before = safe_of(b)
    code, out = second(b, to, "--check")
    check("--check says ready and writes nothing", code == 0 and "Ready:" in out and not any(to.iterdir())
          and not (b["records"] / "second-copy.json").exists(), out)
    code, out = second(b, to)
    got, want = mirror_tree(to), expected(b["records"])
    m = manifest(b)
    check("it finishes (exit 0) and says every file was checked", code == 0 and f"Second copy made on LaCie Rugged: {b['n']} files, every one checked." in out, out)
    check("and that it has the same folders and photo names as the photo drive", "It has the same folders and photo names as Big Kahuna." in out, out)
    check("every file is on the second drive under the very folder and name it has on the photo drive, byte for byte",
          got == want and len(want) == b["n"], f"{sorted(set(got) ^ set(want))}")
    check("all a person sees at the top of the second drive is the shoots' own folders, as on the photo drive",
          sorted(x.name for x in to.iterdir() if not x.name.startswith(".")) == shoot_folders(b["records"]), str(sorted(x.name for x in to.iterdir())))
    check("no folder named for the backup and no DCIM: nothing of the card's own layout",
          not (to / SESSION).exists() and not (to / "DCIM").exists() and not (to / "MISC").exists())
    check("the card's sidecar sits beside its photo under the photo's name, and the camera's own file is in the hidden records",
          any(k.endswith(".xmp") and not k.startswith(MIRROR) for k in got) and f"{MIRROR}/{SESSION}/from-the-card/MISC/M01.CTG" in got, str(sorted(got)))
    rec = record(b)
    check("every file was read from the card, and the record says so",
          rec.get("state") == "done" and rec.get("from_card") == b["n"] and rec.get("from_drive") == 0, str({k: rec.get(k) for k in ("state", "from_card", "from_drive")}))
    check("the record says which kind of copy it is, where each file is on the second drive, and which folders it made",
          rec.get("layout") == "main" and {k: r.get("at") for k, r in rec["files"].items()} == rel_of(b)
          and sorted(rec.get("folders") or []) == shoot_folders(b["records"]), str(rec.get("folders")))
    check("the done line does not speak of the drive when the card was used", "made from the copy" not in out and "upright" not in out, out)
    check("the backup's manifest now names the second copy and its kind, every file checked there",
          m.get("second") and Path(m["second"]).resolve() == to.resolve() and m.get("second_layout") == "main"
          and all(v.get("second", {}).get("ok") for v in m["files"].values()))
    check("the manifest before is kept beside it, once", (b["records"] / "manifest.before-second-copy.json").read_bytes() == b["clean"])
    copy = json.loads((to / MIRROR / SESSION / "manifest.json").read_text(encoding="utf-8"))
    check("the second drive has its own copy of the manifest, in a hidden folder that is not .studio",
          copy.get("files", {}).keys() == m["files"].keys() and copy.get("second") == m["second"] and not (to / ".studio").exists())
    check("the card is exactly as it was", t.card_snapshot(b["card"]) == b["card_before"])
    now = safe_of(b)
    check("the backup is still safe to format, and now has a second copy", safe_before.get("safe") is True and now.get("safe") is True
          and safe_before.get("second") is False and now.get("second") is True, f"{safe_before} {now}")
    page = (b["records"] / "report.html").read_text(encoding="utf-8")
    check("the report was rebuilt and says Second copy made on LaCie Rugged, in place of the button",
          "Second copy made on LaCie Rugged." in page and "id='sc-open' hidden" in page, page[-1500:] if "sc-open" not in page else "")
    check("and does not call it a copy of the earlier kind", "the earlier way" not in page)
    st = status_of(b)
    check("the status for the page is done, with the honest line, nothing behind, and no path",
          st.get("state") == "done" and st.get("behind") == "" and st.get("old") is False and str(b["base"]) not in json.dumps(st), str(st))

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
    code, got_, out = follow(b)
    check("follow with nothing renamed says so, moves nothing and writes nothing",
          code == 0 and got_.get("state") == "same" and stamps(to) == before_stamps and not (b["records"] / "second-follow-log.json").exists(), out)
    reset(b)


def from_the_drive(b):
    print("From the drive, after the settle and a rename, with the card out")
    to = new_drive(b, "Orange Drive")
    check("(the card comes out)", pull_card(b))
    code, out = second(b, to)
    want, got = expected(b["records"]), mirror_tree(to)
    check("it finishes (exit 0) in the same layout, the photo drive's own, with the same hashes", code == 0 and got == want, f"{out[-500:]} {sorted(set(got) ^ set(want))}")
    check("every file's hash is the one the backup recorded for it",
          {rel_of(b)[k]: v["sha256"] for k, v in manifest(b)["files"].items()} == got)
    check("the done line says it was made from the copy on the drive, since the card wasn't in",
          "It was made from the copy on Big Kahuna, since the card wasn't in." in out, out)
    rec = record(b)
    check("the record says every file came from the drive", rec.get("from_drive") == b["n"] and rec.get("from_card") == 0, str(rec.get("from_drive")))
    check("nothing on the photo drive was renamed, moved or added outside the records",
          not (b["drive"] / SESSION).exists() and all(p.name != ".studio-partial" for p in b["drive"].rglob("*.studio-partial")))
    push_card(b)
    reset(b)


def a_turned_clip(b):
    print("A video clip the backup turned upright (36 bytes different from the card's): the copy holds what the photo drive holds")
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
        check("with the card in, the clip is still read from the photo drive: the copy is the upright file, not the card's",
              code == 0 and sha(to / p["file"]) == turned_hash and sha(to / p["file"]) != sha(b["card"] / key), out)
        rec = record(b)
        check("everything else came from the card", rec.get("from_card") == b["n"] - 1 and rec.get("from_drive") == 1
              and rec["files"][key].get("from") == "drive", f"{rec.get('from_card')} {rec.get('from_drive')}")
        check("the done line says 1 video clip is the upright one, and never that the card wasn't in",
              "1 video clip is the upright one from your drive." in out and "wasn't in" not in out, out)
        check("the whole copy matches the photo drive", mirror_tree(to) == expected(b["records"]))
        reset(b)
        to = new_drive(b, "Clip Drive B")
        pull_card(b)
        code, out = second(b, to)
        check("with the card out, it is matched against the turned hash and is the upright file",
              code == 0 and sha(to / p["file"]) == turned_hash, out)
        check("and the done line says so: 1 video clip is the upright one from your drive",
              "1 video clip is the upright one from your drive." in out, out)
        check("the manifest marks that one file's second copy as the turned one",
              manifest(b)["files"][key].get("second") == {"ok": True, "turned": True}, str(manifest(b)["files"][key].get("second")))
        push_card(b)
        reset(b)
        # the card's own sideways file put where the upright one belongs is not "already there, identical"
        to = new_drive(b, "Clip Drive C")
        p0 = start(b, to, pause="0.4")
        try:
            wait_done(b, 3)
        finally:
            p0.kill()
            p0.communicate()
        time.sleep(0.2)
        rec = record(b)
        if rec.get("files", {}).get(key, {}).get("ok"):
            rec["files"].pop(key)
            (b["records"] / "second-copy.json").write_text(json.dumps(rec), encoding="utf-8")
            os.rename(to / p["file"], to / (p["file"] + ".moved-by-the-test"))
            shutil.copy2(b["card"] / key, to / p["file"])
            code, out = second(b, to)
            check("the card's sideways file sitting where the upright one belongs is not taken for the right one (exit 1), and is left alone",
                  code == 1 and sha(to / p["file"]) == card_hash and "is different from your backup" in out, out)
        else:
            check("(the clip was among the first files copied)", False, str(sorted(rec.get("files", {}))))
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
        code, got, out = follow(b)
        check("follow while the copy runs answers busy and touches nothing (the copy brings itself in line)",
              code == 3 and got.get("state") == "busy", out)
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
    done_then = {k: r["at"] for k, r in at_kill.get("files", {}).items() if r.get("ok")}
    stamps_then = {k: (to / at).stat().st_mtime_ns for k, at in done_then.items()}
    idents_then = {k: (to / at).stat().st_ino for k, at in done_then.items()}
    check("killed part way: some files done, not all, and the manifest still untouched",
          0 < len(done_then) < b["n"] and (b["records"] / "manifest.json").read_bytes() == b["clean"], f"{len(done_then)} of {b['n']}")
    st = status_of(b)
    check("the status now says it stopped, in plain words, that nothing was removed, and how to carry on",
          st.get("state") == "stopped" and "Nothing was removed. Press Make a second copy to carry on." in st.get("line", "")
          and str(b["base"]) not in json.dumps(st), str(st))
    check("the backup is still safe to format, with no second copy claimed", safe_of(b) == safe_before, str(safe_of(b)))
    code, out = py("import eject_card as e\nprint('COPYING' if e.copying_from(sys.argv[1]) else 'free')", b["card"], env=b["env"])
    check("and Eject my card no longer waits for it", "free" in out, out)
    # a shoot is renamed on the photo drive while the copy is half made, with the second drive unplugged
    away = to.with_name("Cut Drive (unplugged)")
    os.rename(to, away)
    code, out = rename(b, "s1", "Half way")
    check("(a shoot is renamed while the second drive is out: the rename itself is done)", code == 0, out)
    os.rename(away, to)
    code, out = second(b, to)
    got, want = mirror_tree(to), expected(b["records"])
    check("the next run finishes it (exit 0): every file there and right, under the names the photo drive has NOW", code == 0 and got == want,
          f"{out[-600:]} {sorted(set(got) ^ set(want))}")
    now_at = {k: r["at"] for k, r in record(b)["files"].items()}
    check("nothing was copied twice: the files done before the kill are the very same files, renamed where the shoot was",
          all((to / now_at[k]).stat().st_mtime_ns == stamps_then[k] and (to / now_at[k]).stat().st_ino == idents_then[k] for k in done_then)
          and any(now_at[k] != done_then[k] for k in done_then))
    check("no unfinished file is left on the second drive, and no folder under the old name",
          not list(to.rglob("*.studio-partial")) and sorted(x.name for x in to.iterdir() if not x.name.startswith(".")) == shoot_folders(b["records"]),
          str(sorted(x.name for x in to.iterdir())))
    reset(b)
    code, out = rename(b, "s1", "Renamed beach")
    check("(the shoot gets its name back, for the cases after this)", code == 0, out)


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
    got, want = mirror_tree(to), expected(b["records"])
    check("the copy carries on from the drive and finishes (exit 0), every file right", p.returncode == 0 and got == want, out)
    check("some files came from the card and the rest from the drive", (rec.get("from_card") or 0) >= 3 and (rec.get("from_drive") or 0) >= 1
          and rec.get("from_card") + rec.get("from_drive") == b["n"], f"{rec.get('from_card')} + {rec.get('from_drive')}")
    check("and the done line says how many came from the drive", f"{rec.get('from_drive')} of them came from the copy on Big Kahuna, since the card wasn't in for those." in out, out)
    check("no unfinished file is left", not list(to.rglob("*.studio-partial")))
    reset(b)


def already_there(b):
    print("Something already on the second drive")
    to = new_drive(b, "Busy Drive")
    where = rel_of(b)
    folder = shoot_folders(b["records"])[0]
    (to / folder).mkdir()
    (to / folder / "their own picture.jpg").write_bytes(b"somebody else's file, kept")
    safe_before = safe_of(b)
    outs = [second(b, to, *more) for more in (("--check",), (), ())]
    check("a folder with a shoot's name that this copy did not make is refused (exit 2) by name, with --check and without",
          all(c == 2 and f"Busy Drive already has a folder called {folder} that isn't part of this second copy." in o for c, o in outs), str(outs[1]))
    check("nothing was written into it or beside it, and no record was started",
          listing(to) == [f"{folder}/their own picture.jpg"] and not (b["records"] / "second-copy.json").exists(), str(listing(to)))
    check("the line holds no path", str(b["base"]) not in outs[0][1].split("REFUSED")[-1])
    to = new_drive(b, "Busy Drive 2")
    p = start(b, to)
    try:
        check("(three files in)", wait_done(b, 3), str(record(b)))
    finally:
        p.kill()
        p.communicate()
    time.sleep(0.2)
    rec = record(b)
    todo = [k for k in sorted(manifest(b)["files"]) if not rec["files"].get(k, {}).get("ok")
            and where[k].split("/")[0] in (rec.get("folders") or [])]
    if len(todo) < 2:
        check("(two files of a folder the copy made are still to copy)", False, f"{todo} {rec.get('folders')}")
        reset(b)
        return
    differs, same = todo[0], todo[1]
    for k in (differs, same):
        try:
            (to / where[k]).unlink()         # (the test's own tidying: whatever the killed run left half written)
        except OSError:
            pass
    rec["files"].pop(differs, None)
    rec["files"].pop(same, None)
    (b["records"] / "second-copy.json").write_text(json.dumps(rec), encoding="utf-8")
    (to / where[differs]).write_bytes(b"somebody else's file, kept")
    shutil.copy2(b["drive"] / where[same], to / where[same])
    same_stamp = (to / where[same]).stat().st_mtime_ns
    for attempt in ("first", "second"):
        code, out = second(b, to)
        check(f"a different file already in the copy's own folder is never written over ({attempt} run): exit 1, the file as it was",
              code == 1 and (to / where[differs]).read_bytes() == b"somebody else's file, kept", out)
    check("it is a problem that says so in plain words, counted honestly",
          "1 file already on Busy Drive 2 is different from your backup, so I left it alone." in out
          and f"{b['n'] - 1} of {b['n']} files are copied and checked so far." in out, out)
    rec = record(b)
    check("the record keeps it as exists-and-differs, and the state is stopped", rec.get("files", {}).get(differs, {}).get("note") == "exists and differs"
          and rec.get("state") == "stopped" and rec.get("done") == b["n"] - 1, str(rec.get("files", {}).get(differs)))
    check("an identical file already there is kept as it is and counted as checked",
          rec["files"][same].get("ok") and "already there" in rec["files"][same].get("note", "") and (to / where[same]).stat().st_mtime_ns == same_stamp)
    check("the backup's manifest is not changed, and safe to format is what it was",
          (b["records"] / "manifest.json").read_bytes() == b["clean"] and safe_of(b) == safe_before and safe_before.get("safe") is True, str(safe_of(b)))
    st = status_of(b)
    check("the page's line holds no path", st.get("state") == "stopped" and str(b["base"]) not in json.dumps(st) and "DCIM" not in st.get("line", ""), str(st))
    reset(b)


def own_failed_copy(b):
    print("Only this copy's own failed attempt may be written again")
    to = new_drive(b, "Redo Drive")
    where = rel_of(b)
    keys = sorted(manifest(b)["files"])
    ours, theirs = keys[2], keys[3]
    for k, body in ((ours, b"half of a copy that broke off"), (theirs, b"put here by somebody since")):
        (to / where[k]).parent.mkdir(parents=True, exist_ok=True)
        (to / where[k]).write_bytes(body)
    st = (to / where[ours]).stat()
    # the record of a run that broke off on both: for one, what is there is exactly what that run left; for the
    # other, something else is there now (its size, time and number are not what the run left)
    rec = {"to": str(to.resolve()), "place": str(to.resolve()), "layout": "main", "mirror": SESSION, "prefix": "",
           "folders": sorted({where[k].split("/")[0] for k in (ours, theirs)}), "to_name": "Redo Drive", "state": "stopped", "files": {
               ours: {"ok": False, "note": "OSError", "left": [st.st_size, st.st_mtime_ns, st.st_ino]},
               theirs: {"ok": False, "note": "OSError", "left": [1, 2, 3]}}}
    (b["records"] / "second-copy.json").write_text(json.dumps(rec), encoding="utf-8")
    code, out = second(b, to)
    want = manifest(b)["files"]
    check("its own failed copy is written again and is right", sha(to / where[ours]) == want[ours]["sha256"], out)
    check("a file that is not what the failed run left is never written over (exit 1)",
          code == 1 and (to / where[theirs]).read_bytes() == b"put here by somebody since", out)
    check("and the manifest is not changed", (b["records"] / "manifest.json").read_bytes() == b["clean"])
    reset(b)


def changed_source(b):
    print("A source that no longer matches what the backup recorded")
    to = new_drive(b, "Careful Drive")
    index = json.loads((b["records"] / "index.json").read_text(encoding="utf-8"))
    p = [x for x in index["photos"] if x.get("original")][2]
    at = b["drive"] / p["file"]
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
        check("it is not left under the photo's name on the second drive", not (to / p["file"]).exists(), str(list((to / p["file"]).parent.iterdir())))
        want = {rel_of(b)[k]: v["sha256"] for k, v in manifest(b)["files"].items()}
        got = {k: v for k, v in mirror_tree(to).items() if not k.endswith(".studio-partial")}
        check("the others were copied and are right", len(got) == b["n"] - 1 and all(want[k] == v for k, v in got.items()), str(sorted(got)))
        check("the manifest is not changed", (b["records"] / "manifest.json").read_bytes() == b["clean"])
        at.write_bytes(good)                        # the photo is right again
        code, out = second(b, to)
        got = mirror_tree(to)
        check("once the photo is right again, the next run finishes (exit 0) with no unfinished file left",
              code == 0 and got == expected(b["records"]), f"{out[-400:]} {sorted(got)}")
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
        want = {rel_of(b)[k]: v["sha256"] for k, v in manifest(b)["files"].items()}
        check("with the card back in, the copy is made from the card (exit 0), every file what the backup recorded, under its name on the drive",
              code == 0 and mirror_tree(to) == want, out[-400:])
    finally:
        for p, g in zip(two, good):
            p.write_bytes(g)
        push_card(b)
        reset(b)


def refusals(b):
    print("Refused before a byte is written")
    def refused(what, to, words, change=None, around=None):
        m = json.loads(b["clean"].decode("utf-8"))
        if change:
            change(m)
            (b["records"] / "manifest.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
        undo = around() if around else None
        held = (b["records"] / "manifest.json").read_bytes()
        before = stamps(to) if Path(to).is_dir() else None
        ok = True
        said = ""
        try:
            for more in (("--check",), ()):
                code, out = second(b, to, *more)
                said = out
                ok = ok and code == 2 and words in out and (stamps(to) if Path(to).is_dir() else None) == before \
                    and not (b["records"] / "second-copy.json").exists() and (b["records"] / "manifest.json").read_bytes() == held
        finally:
            if undo:
                undo()
        check(f"{what}: refused (exit 2) with --check and without, nothing written", ok, said)
        if change:
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

    # Nov 23: a copy that looks like the shoots needs the shoots
    def hidden_log(name):
        def go():
            os.rename(b["records"] / name, b["records"] / (name + ".aside-for-the-test"))
            return lambda: os.rename(b["records"] / (name + ".aside-for-the-test"), b["records"] / name)
        return go
    refused("a backup whose photos are not sorted into shoots yet", spare, "aren't sorted into shoots yet", around=hidden_log("sort-log.json"))

    def half_rename():
        log = b["records"] / "rename-log.json"
        kept = log.read_bytes()
        d = json.loads(kept.decode("utf-8"))
        d["renames"].append({"shoot": "s2", "from_name": "a", "to_name": "b", "moves": [], "problems": []})    # never finished
        log.write_text(json.dumps(d), encoding="utf-8")
        return lambda: log.write_bytes(kept)
    refused("a backup with a shoot part way through a rename", spare, "part way through being renamed", around=half_rename)

    code, out = t.run("second_copy.py", b["base"] / "no such backup", "--to", spare, env=b["env"])
    check("records that cannot be found: refused (exit 2)", code == 2 and "I can't find that backup's records." in out and not any(spare.iterdir()), out)
    # the copy's own hidden records of the same name on the second drive, holding a different backup
    (spare / MIRROR / SESSION).mkdir(parents=True)
    (spare / MIRROR / SESSION / "manifest.json").write_text(json.dumps({"files": {"DCIM/100CANON/OTHER.JPG": {"size": 3, "sha256": "ab"}}}), encoding="utf-8")
    refused("records of that name holding another backup", spare, "holding a different backup")
    code, out = second(b, spare, "--check", "--json")
    try:
        last = json.loads(out.strip().splitlines()[-1])
    except ValueError:
        last = {}
    check("--json ends with one line the report's server can read", last.get("ok") is False and last.get("state") == "another_there" and "words" in last, out)
    check("no refusal line holds a path", str(b["base"]) not in last.get("words", "x" + str(b["base"])))
    fresh = new_drive(b, "Not Remembered")
    code, out = second(b, fresh, "--always")
    sf = json.loads((b["home"] / "studio.json").read_text(encoding="utf-8"))
    check("--always no longer saves the drive for every backup (Nicole, Nov 23: ask each time), and says so",
          code == 0 and not sf.get("drives", {}).get("second") and "asked each time" in out, f"{sf.get('drives')} {out[-300:]}")
    reset(b)


# ---------------------------------------------------------------- the copy follows a rename or a join (Nov 23)

def follow_log(b):
    try:
        return json.loads((b["records"] / "second-follow-log.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def follows_a_rename(b):
    print("A shoot renamed on the photo drive: the second copy takes the same folder and names")
    to = new_drive(b, "Follow Drive")
    code, out = second(b, to)
    check("(a second copy is made)", code == 0 and mirror_tree(to) == expected(b["records"]), out[-300:])
    before = numbers(to)
    old_folders = shoot_folders(b["records"])
    made_manifest = (b["records"] / "manifest.json").read_bytes()
    code, out = rename(b, "s2", "Garcia family")
    check("the rename says the second copy has the same folders and names again",
          code == 0 and "Your second copy on Follow Drive has the same folders and names as Big Kahuna again." in out, out)
    got, want = mirror_tree(to), expected(b["records"])
    check("the second drive now has the photo drive's folder and photo names, every file byte for byte",
          got == want and any("Garcia" in k for k in got), str(sorted(set(got) ^ set(want))))
    check("spelled exactly as on the photo drive, letter for letter",
          [x for x in listing(to) if not x.startswith(MIRROR)] == sorted(k for k in want if not k.startswith(MIRROR)))
    check("the files were renamed on the second drive, never copied: the very same files, their times untouched", numbers(to) == before)
    check("no folder under the old name is left, and nothing half moved",
          sorted(x.name for x in to.iterdir() if not x.name.startswith(".")) == shoot_folders(b["records"]) != old_folders
          and not list(to.rglob("*.studio-moving")), str(sorted(x.name for x in to.iterdir())))
    log = follow_log(b)
    run = (log.get("runs") or [{}])[-1]
    check("every move is in the follow log, written in the backup's records, and the run is marked finished",
          run.get("finished") and run.get("folders") and all(f.get("moved") for f in run["folders"])
          and run.get("moves") and all(m.get("moved") and m.get("ident") for m in run["moves"]), str(run)[:600])
    rec = record(b)
    check("the record says where each file is now, and which folders are the copy's",
          {k: r["at"] for k, r in rec["files"].items()} == rel_of(b) and sorted(rec["folders"]) == shoot_folders(b["records"])
          and rec.get("follow", {}).get("state") == "done", str(rec.get("folders")))
    check("the backup's manifest was not touched by it, and the backup still has its second copy",
          (b["records"] / "manifest.json").read_bytes() == made_manifest and safe_of(b).get("second") is True and safe_of(b).get("safe") is True)
    st = status_of(b)
    check("the status has nothing behind", st.get("state") == "done" and st.get("behind") == "", str(st))

    print("Follow run twice")
    held, held_log, held_rec = stamps(to), (b["records"] / "second-follow-log.json").read_bytes(), (b["records"] / "second-copy.json").read_bytes()
    code, got_, out = follow(b)
    check("a second follow moves nothing and writes nothing", code == 0 and got_.get("state") == "same" and got_.get("moved") == 0
          and stamps(to) == held and (b["records"] / "second-follow-log.json").read_bytes() == held_log
          and (b["records"] / "second-copy.json").read_bytes() == held_rec, out)

    print("A rename that only changes capital letters")
    code, out = rename(b, "s2", "garcia Family")
    got, want = mirror_tree(to), expected(b["records"])
    names_now = [x for x in listing(to) if not x.startswith(MIRROR)]
    check("the second drive takes the new capitals too, read from its folders' own listings (never a case-blind look)",
          code == 0 and names_now == sorted(k for k in want if not k.startswith(MIRROR)) and any("garcia" in x for x in names_now)
          and not any("Garcia" in x for x in names_now), f"{out[-300:]} {names_now}")
    check("still the very same files", numbers(to) == before and got == want)
    return to, before


def waits_for_the_drive(b, to, before):
    print("A shoot renamed while the second drive is not plugged in")
    away = to.with_name(to.name + " (unplugged)")
    os.rename(to, away)
    held = stamps(away)
    code, out = rename(b, "s2", "Lopez wedding")
    check("the rename itself is done, and says the copy still has the names from before and what to do",
          code == 0 and "Your second copy on Follow Drive still has the folders and names from before. Plug Follow Drive in and it will catch up." in out, out)
    check("nothing on the unplugged drive was touched (it could not be)", stamps(away) == held)
    rec = record(b)
    check("it is on record as waiting", rec.get("follow", {}).get("state") == "waiting", str(rec.get("follow")))
    st = status_of(b)
    check("the status says so for the report, in plain words with no path, and does not offer to catch up while the drive is out",
          "still has the folders and names from before" in st.get("behind", "") and st.get("catch") is False
          and st.get("state") == "done" and str(b["base"]) not in json.dumps(st), str(st))
    check("the backup still has its second copy and is still safe: every file of it is checked, only its names are behind",
          safe_of(b).get("second") is True and safe_of(b).get("safe") is True, str(safe_of(b)))
    t.run("report_page.py", b["records"], env=b["env"])
    page = (b["records"] / "report.html").read_text(encoding="utf-8")
    check("the report says it under Second copy made, where the button was",
          "id='sc-behind' role='status'>Your second copy on Follow Drive still has the folders and names from before." in page, page[page.find("sc-behind") - 80:][:400])
    code, got_, out = follow(b)
    check("follow with the drive still out answers waiting again and writes nothing new", code == 3 and got_.get("state") == "waiting"
          and record(b).get("follow") == rec.get("follow"), out)
    code, out = rename(b, "s2", "Lopez family")
    check("a second rename while it is out is fine too", code == 0 and "Plug Follow Drive in" in out, out)
    os.rename(away, to)
    check("with the drive back in, the status offers to catch up", status_of(b).get("catch") is True, str(status_of(b)))
    # the report's own status check is the command that sees the drive: its server starts the follow
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = subprocess.Popen([sys.executable, str(t.SCRIPTS / "serve_report.py"), str(b["records"]), "--port", str(port)],
                           env=t.child_env(b["env"]), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding="utf-8", errors="replace")
    try:
        line = srv.stdout.readline()
        base = line.split("Report:", 1)[1].strip().rsplit("/", 1)[0] if "Report:" in line else f"http://127.0.0.1:{port}"
        seen, st = [], {}
        end = time.time() + 60
        while time.time() < end:
            with urllib.request.urlopen(base + "/second-status", timeout=20) as r:
                body = r.read().decode("utf-8")
            seen.append(body)
            st = json.loads(body)
            if not st.get("behind"):
                break
            time.sleep(0.3)
        check("the report's status check brings it in line by itself, and the line goes", st.get("behind") == "" and st.get("state") == "done" and len(seen) > 1, str(seen[-2:]))
        check("the page is never handed 'catch' or a path", all("catch" not in json.loads(x) and str(b["base"]) not in x for x in seen))
    finally:
        srv.kill()
        srv.communicate()
    got, want = mirror_tree(to), expected(b["records"])
    check("the second drive has the newest names (both renames at once), the very same files", got == want and numbers(to) == before
          and any("Lopez family" in k for k in got), str(sorted(set(got) ^ set(want))))

    print("follow --all, as a backup runs it: every copy that was waiting for its drive")
    os.rename(to, away)
    rename(b, "s2", "Waiting again")
    os.rename(away, to)
    code, out = t.run("second_copy.py", "follow", "--all", env=b["env"])
    check("it finds this backup through the card ledger and brings its copy in line", code == 0 and "1 second copy brought in line." in out
          and mirror_tree(to) == expected(b["records"]) and status_of(b).get("behind") == "", out)


def a_follow_cut_off(b, to, before):
    print("A follow cut off part way is finished by the next one")
    away = to.with_name(to.name + " (unplugged)")
    os.rename(to, away)
    was = rel_of(b)
    rename(b, "s2", "Cut off shoot")
    os.rename(away, to)
    now = rel_of(b)
    moved = [k for k in sorted(was) if was[k] != now[k]]
    old_top, new_top = was[moved[0]].split("/")[0], now[moved[0]].split("/")[0]
    # what a run killed after the folder and its first two files would leave: the log written first and never
    # marked finished, the folder under its new name, two files under theirs, and the record not yet told
    idents = {}
    for k in moved:
        st = (to / was[k]).stat()
        idents[k] = [st.st_ino, st.st_size, st.st_mtime_ns]
    os.rename(to / old_top, to / new_top)
    for k in moved[:2]:
        os.rename(to / new_top / Path(was[k]).relative_to(old_top), to / now[k])
    log = follow_log(b)
    log.setdefault("runs", []).append({"place": str(to.resolve()), "started": "2026-11-23T10:00:00",
                                       "folders": [{"from": old_top, "to": new_top}],
                                       "moves": [{"key": k, "from": new_top + was[k][len(old_top):], "to": now[k], "ident": idents[k]} for k in moved]})
    (b["records"] / "second-follow-log.json").write_text(json.dumps(log), encoding="utf-8")
    code, got_, out = follow(b)
    got, want = mirror_tree(to), expected(b["records"])
    check("the next follow finishes it: every file under its new name, none moved twice, none lost",
          code == 0 and got_.get("state") == "followed" and got == want and numbers(to) == before, f"{out[-400:]} {sorted(set(got) ^ set(want))}")
    runs = follow_log(b).get("runs", [])
    check("the cut-off run is marked as picked up, and the record says where every file is",
          all(r.get("finished") for r in runs) and {k: r["at"] for k, r in record(b)["files"].items()} == now, str([r.get("finished") for r in runs]))
    code, got_, out = follow(b)
    check("and once more changes nothing", got_.get("state") == "same" and mirror_tree(to) == want and numbers(to) == before, out)


def something_in_the_way(b, to, before):
    print("Something of theirs in the way on the second drive is never moved or taken over")
    away = to.with_name(to.name + " (unplugged)")
    os.rename(to, away)
    rename(b, "s2", "In the way")
    os.rename(away, to)
    new_folder = next(f for f in shoot_folders(b["records"]) if f.startswith("In the way"))
    (to / new_folder).mkdir()
    (to / new_folder / "notes.txt").write_bytes(b"their own folder, put here by them")
    held = {k: v for k, v in stamps(to).items() if not k.startswith(MIRROR)}
    code, got_, out = follow(b)
    check("a folder of theirs with the shoot's new name stops it (a problem), by the folder's name, in plain words",
          code == 1 and got_.get("state") == "problem" and f"a folder called {new_folder} is already there that isn't part of the copy." in got_.get("words", "")
          and "Nothing was removed or written over." in got_.get("words", "") and str(b["base"]) not in got_.get("words", ""), out)
    check("no file was moved, and their folder is exactly as it was", {k: v for k, v in stamps(to).items() if not k.startswith(MIRROR)} == held and set(before) <= set(numbers(to))
          and (to / new_folder / "notes.txt").read_bytes() == b"their own folder, put here by them")
    check("the status carries the same line for the report", "isn't part of the copy" in status_of(b).get("behind", "") and status_of(b).get("catch") is False, str(status_of(b)))
    os.rename(to / new_folder, to / "Their own folder")        # (they rename their folder out of the way)
    code, got_, out = follow(b)
    check("once it is out of the way, follow finishes", got_.get("state") == "followed" and mirror_tree(to) == {**expected(b["records"]), "Their own folder/notes.txt": sha(to / "Their own folder" / "notes.txt")}, out)
    shutil.rmtree(to / "Their own folder")                       # (the test's own tidying of its own pretend folder)

    os.rename(to, away)
    was = rel_of(b)
    rename(b, "s2", "Second try")
    os.rename(away, to)
    now = rel_of(b)
    k = next(k for k in sorted(was) if was[k] != now[k])
    blocker = to / Path(was[k]).parent / Path(now[k]).name       # in the copy's own folder, under a name a photo should take
    blocker.write_bytes(b"a file of theirs with that very name")
    code, got_, out = follow(b)
    check("a file of theirs under a name one of the photos should take stops it too, and is not written over",
          got_.get("state") == "problem" and "something else already has a name one of its files should take." in got_.get("words", "")
          and b"a file of theirs" in (to / Path(now[k]).parent / Path(now[k]).name).read_bytes(), out)
    check("every photo of the copy is still there, the very same files (the folder took its new name; no photo was renamed onto anything)",
          set(numbers(to)) - {(to / Path(now[k]).parent / Path(now[k]).name).stat().st_ino} == set(before) and
          {r["at"] for r in record(b)["files"].values()} <= set(listing(to)), str(sorted(listing(to)))[:500])
    os.rename(to / Path(now[k]).parent / Path(now[k]).name, to / "theirs.txt")
    code, got_, out = follow(b)
    check("and with it gone, follow finishes", got_.get("state") == "followed" and set(numbers(to)) - {(to / "theirs.txt").stat().st_ino} == set(before), out)
    (to / "theirs.txt").unlink()                                  # (the test's own tidying)
    check("the copy matches the photo drive again", mirror_tree(to) == expected(b["records"]))


def a_join(b, to, before):
    print("Two shoots joined on the photo drive (as Name your shoots will do it): files change folder, and names go round in a ring")
    index_path = b["records"] / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    shoots_path = b["records"] / "shoots.json"
    sh = json.loads(shoots_path.read_text(encoding="utf-8"))
    s1, s2 = sh["shoots"][0], sh["shoots"][1]
    one = [p for p in index["photos"] if p.get("original") and p["file"].startswith(s1["folder"] + "/")]
    two = [p for p in index["photos"] if p.get("original") and p["file"].startswith(s2["folder"] + "/")]
    (to / s2["folder"] / ".DS_Store").write_bytes(b"the computer's own note in the folder that will empty")
    # the test plays the join on the photo drive: shoot 2's photos go into shoot 1's folder under shoot 1's names,
    # and two of shoot 1's photos (without a sidecar) swap names, as a renumbering by time would do
    prefix = Path(one[0]["file"]).name.split("_")[0]
    for n, p in enumerate(two, len(one) + 1):
        new = f"{s1['folder']}/{prefix}_{n:04d}_{Path(p['original']).name}"
        os.rename(b["drive"] / p["file"], b["drive"] / new)
        p["file"] = new
    a_, b_ = one[1], one[2]
    os.rename(b["drive"] / a_["file"], b["drive"] / (a_["file"] + ".tmp"))
    os.rename(b["drive"] / b_["file"], b["drive"] / a_["file"])
    os.rename(b["drive"] / (a_["file"] + ".tmp"), b["drive"] / b_["file"])
    a_["file"], b_["file"] = b_["file"], a_["file"]
    (b["drive"] / s2["folder"]).rmdir()
    gone_folder = s2["folder"]
    s2["folder"] = s1["folder"]
    index_path.write_text(json.dumps(index, indent=1), encoding="utf-8")
    shoots_path.write_text(json.dumps(sh, indent=1), encoding="utf-8")
    code, got_, out = follow(b)
    got, want = mirror_tree(to), expected(b["records"])
    check("follow brings the second drive in line: one folder, every photo under the name it has on the photo drive",
          code == 0 and got_.get("state") == "followed" and got == want, f"{out[-400:]} {sorted(set(got) ^ set(want))}")
    check("the two photos that swapped names swapped on the second drive too (each name holds the right photo)",
          sha(to / a_["file"]) == sha(b["drive"] / a_["file"]) and sha(to / b_["file"]) == sha(b["drive"] / b_["file"]))
    check("the very same files, none copied, and no stepping-aside name left behind",
          numbers(to) == before and not [x for x in listing(to) if x.endswith(".studio-moving")])
    check("the emptied folder came down, and the computer's own note in it was set aside in the hidden records, not deleted",
          not (to / gone_folder).exists() and (to / MIRROR / SESSION / "set-aside" / gone_folder / ".DS_Store").read_bytes().startswith(b"the computer's own note"))
    check("the record's folders are the ones that are there", sorted(record(b)["folders"]) == shoot_folders(b["records"]), str(record(b)["folders"]))
    code, got_, out = follow(b)
    check("and once more changes nothing", got_.get("state") == "same", out)

    print("A file of the copy that has gone from the second drive")
    k = sorted(k for k, v in rel_of(b).items() if not v.startswith(MIRROR))[-1]
    os.rename(to / rel_of(b)[k], to / "taken away by the test.jpg")
    mover = one[3]                                              # (a photo with no sidecar)
    keep = mover["file"]
    mover["file"] = keep.replace(f"{prefix}_{Path(keep).name.split('_')[1]}_", f"{prefix}_0099_")
    os.rename(b["drive"] / keep, b["drive"] / mover["file"])
    index_path.write_text(json.dumps(index, indent=1), encoding="utf-8")
    p_gone = next(p for p in index["photos"] if p.get("original") == k)
    new_gone = p_gone["file"].replace(prefix + "_", prefix + "x_")
    os.rename(b["drive"] / p_gone["file"], b["drive"] / new_gone)
    p_gone["file"] = new_gone
    index_path.write_text(json.dumps(index, indent=1), encoding="utf-8")
    code, got_, out = follow(b)
    check("it is said plainly as a problem, and the files that are there still take their new names",
          got_.get("state") == "problem" and "1 file of the copy is not where it was left." in got_.get("words", "")
          and (to / mover["file"]).is_file(), out)
    os.rename(to / "taken away by the test.jpg", to / record(b)["files"][k]["at"])
    code, got_, out = follow(b)
    check("put back, the next follow finishes and the line goes", got_.get("state") == "followed" and status_of(b).get("behind") == ""
          and mirror_tree(to) == expected(b["records"]) and numbers(to) == before, out)
    reset(b)


# ---------------------------------------------------------------- the report

def the_page(b):
    print("The report's button and its routes")
    code, out = t.run("report_page.py", b["records"], env=b["env"])
    page = (b["records"] / "report.html").read_text(encoding="utf-8")
    start_at = page.find("<section class='wrap opts'")
    section = page[start_at:page.find("</section>", start_at)] if start_at >= 0 else ""
    check("the report has the section under the shoots: the heading and its line",
          "Anything you&#x27;d like to change?" in section and "Your photos are safe either way. These are here if you want them." in section
          and 0 < page.find("class='shoot") < start_at, section[:300])
    for words in ("Make a second copy", "Which drive should the second copy go on?", "Look again",
                  "Make the second copy", "Keep your card in until this is done.", "I can&#x27;t see another drive. Plug one in, then press Look again."):
        check(f"the panel says: {words.replace('&#x27;', chr(39))}", words in section)
    check("Do this after every backup is no longer offered (Nicole, Nov 23: the second drive is asked each time)",
          "Do this after every backup" not in page and "sc-always'" not in section and "id='sc-always'" not in page)
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
        got, want = mirror_tree(to), expected(b["records"])
        check("the copy the button made is whole, right, and laid out like the photo drive", got == want)
        sf = json.loads((b["home"] / "studio.json").read_text(encoding="utf-8"))
        check("a press that asks for 'always' (an older page still open) saves nothing: no second drive in the Studio File",
              not sf.get("drives", {}).get("second"), str(sf.get("drives")))
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
            check("the panel has no tick box: nothing is offered for every backup",
                  c.js("document.getElementById('sc-always') === null && !/every backup/.test(document.getElementById('sc-panel').innerText)") is True)
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
            check("and nothing is said to be behind", c.js("document.getElementById('sc-behind').hidden") is True)
            check("nothing on the page holds a path", str(b["base"]) not in c.js("document.getElementById('opts').innerText"))
            # a shoot renamed with the second drive out: the open page says the copy is behind, then that it caught up
            away = to.with_name("LaCie Browser (unplugged)")
            os.rename(to, away)
            rename(b, "s1", "Browser rename")
            c.reload()
            c.wait_for("!document.getElementById('sc-behind').hidden", seconds=30)
            check("with the drive out after a rename, the page says the copy still has the names from before",
                  "still has the folders and names from before" in c.js("document.getElementById('sc-behind').textContent")
                  and c.js("!document.getElementById('sc-made').hidden") is True, c.js("document.getElementById('sc-behind').textContent"))
            os.rename(away, to)
            c.wait_for("document.getElementById('sc-behind').hidden", seconds=60)
            check("plugged back in, the line goes by itself once the copy has caught up", mirror_tree(to) == expected(b["records"]))
    finally:
        srv.kill()
        srv.communicate()
        chrome_drive.stop_all()
    got, want = mirror_tree(to), expected(b["records"])
    check("and the copy the page asked for is whole and right", got == want)
    reset(b)
    rename(b, "s1", "Renamed beach")


def the_earlier_kind(b):
    print("A second copy made before Nov 23, in the card's own layout, is left exactly as it is")
    to = new_drive(b, "Old Copy Drive")
    m = json.loads(b["clean"].decode("utf-8"))
    old = to / SESSION
    for key in m["files"]:                               # the test plays the copy the earlier version made
        (old / key).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(b["card"] / key, old / key)
        m["files"][key]["second"] = {"ok": True}
    m["second"] = str(old.resolve())
    (old / "_studio").mkdir()
    (old / "_studio" / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    (b["records"] / "manifest.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    (b["records"] / "second-copy.json").write_text(json.dumps({
        "to": str(old.resolve()), "to_name": "Old Copy Drive", "state": "done", "total": b["n"], "done": b["n"],
        "line": f"Second copy made on Old Copy Drive: {b['n']} files, every one checked.",
        "files": {k: {"ok": True, "from": "card"} for k in m["files"]}}), encoding="utf-8")
    held = stamps(to)
    st = status_of(b)
    check("it still counts as this backup's second copy, and the status marks it as the earlier kind",
          st.get("state") == "done" and st.get("old") is True and st.get("behind") == "" and safe_of(b).get("second") is True, str(st))
    t.run("report_page.py", b["records"], env=b["env"])
    page = (b["records"] / "report.html").read_text(encoding="utf-8")
    check("the report says truthfully what it is: laid out as the memory card was, every file checked",
          "Second copy made on Old Copy Drive." in page and "its folders and names are the memory card&#x27;s, not your shoots&#x27;" in page, page[page.find("sc-made") - 100:][:600])
    code, got_, out = follow(b)
    check("follow leaves it alone and says why", code == 0 and got_.get("state") == "card" and "left as it is" in got_.get("words", "") and stamps(to) == held, out)
    code, out = rename(b, "s1", "Old copy rename")
    check("a rename on the photo drive does not touch it", code == 0 and stamps(to) == held and "second copy" not in out, out)
    code, out = second(b, to)
    check("asking for a second copy on that same drive says there is one (exit 0), and nothing is converted or added",
          code == 0 and "already has a second copy, on Old Copy Drive. Nothing to do." in out and stamps(to) == held, out)
    rename(b, "s1", "Renamed beach")
    reset(b)

    print("One of the earlier kind that stopped part way is finished the way it was begun")
    to = new_drive(b, "Half Old Drive")
    old = to / SESSION
    keys = sorted(json.loads(b["clean"].decode("utf-8"))["files"])
    done = keys[:3]
    for key in done:
        (old / key).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(b["card"] / key, old / key)
    (old / "_studio").mkdir()
    (b["records"] / "second-copy.json").write_text(json.dumps({
        "to": str(old.resolve()), "to_name": "Half Old Drive", "state": "stopped", "total": b["n"], "done": 3,
        "files": {k: {"ok": True, "from": "card"} for k in done}}), encoding="utf-8")
    first = {k: (old / k).stat().st_ino for k in done}
    code, out = second(b, to)
    got = tree(old)
    check("it finishes (exit 0) in the card's own layout, in its own folder, every file the card's",
          code == 0 and got == {k: sha(b["card"] / k) for k in keys} and not any(x.name != SESSION for x in to.iterdir()), f"{out[-300:]} {sorted(x.name for x in to.iterdir())}")
    check("the files copied before are the very same files", all((old / k).stat().st_ino == first[k] for k in done))
    mm = manifest(b)
    check("the manifest names it without calling it the new kind, and the done line does not claim the photo drive's names",
          Path(mm["second"]).resolve() == old.resolve() and "second_layout" not in mm and "same folders and photo names" not in out, out[-300:])
    reset(b)


def a_saved_second_drive(b, work):
    print("A second drive saved for every backup is no longer used by itself (Nicole, Nov 23: ask each time)")
    saved = new_drive(b, "Saved Second")
    sf_path = b["home"] / "studio.json"
    sf = json.loads(sf_path.read_text(encoding="utf-8"))
    sf.setdefault("drives", {}).update({"second": str(saved), "second_label": "Saved Second"})     # as an older version saved it
    sf_path.write_text(json.dumps(sf, indent=1), encoding="utf-8")
    code, out = t.run("studio_file.py", "glance", env=b["env"])
    check("their settings no longer say a second copy goes onto it by itself", "A second copy goes onto" not in out and "ask" in out.lower(), out)
    card = b["base"] / "CARD 2"
    t.make_card(card, groups=(3,))
    for p in (card / "DCIM" / "100CANON").glob("*.JPG"):     # other photos than the first card's
        p.write_bytes(p.read_bytes() + b"second card")
    code, out = t.run("night.py", "--source", card, "--check", env=b["env"])
    check("the quiet check passes and notes it, for the Assistant only", code == 0 and "PREFLIGHT OK" in out
          and "was saved for every backup" in out and "asked for each time" in out, out)
    night = ["night.py", "--source", card, "--name", "saved card", "--date", "2026-11-19", "--no-peeks"]
    code, out = t.run(*night, env=b["env"])
    st = b["drive"] / "2026-11-19 saved card" / "_studio"
    m = json.loads((st / "manifest.json").read_text(encoding="utf-8")) if (st / "manifest.json").is_file() else {}
    check("backup now copies the card (exit 4, the look) and makes no second copy on the saved drive",
          code == 4 and m.get("files") and all(v.get("dest", {}).get("ok") for v in m["files"].values()) and not m.get("second")
          and not any(saved.iterdir()), out)
    groups = json.loads((st / "groups.json").read_text(encoding="utf-8"))["groups"]
    (st / "shoots.json").write_text(json.dumps({"decided_by": "test", "shoots": [
        {"id": f"s{i}", "suggested": f"Saved {i}", "groups": [g["id"]], "photos": g.get("count", 0), "recap": "Test frames.", "why": "test"}
        for i, g in enumerate(groups, 1)]}), encoding="utf-8")
    code, out = t.run(*night, env=b["env"])
    records = b["drive"] / ".studio" / "2026-11-19 saved card"
    check("it finishes and settles (exit 0), still with nothing on the saved drive", code == 0 and (records / "settled.json").is_file()
          and not any(saved.iterdir()), out[-400:])
    page = (records / "report.html").read_text(encoding="utf-8") if (records / "report.html").is_file() else ""
    check("that backup's report says so once, plainly, beside the button",
          "You had Saved Second saved for a second copy after every backup. I ask each time now instead: press Make a second copy whenever you want one." in page
          and "safe to format" in page and "Make a second copy" in page, page[:300])
    sf = json.loads(sf_path.read_text(encoding="utf-8"))
    check("the Studio File remembers it was said, and still holds the drive (nothing of theirs is thrown away)",
          sf["drives"].get("second_asked_each_time") and sf["drives"].get("second") == str(saved), str(sf["drives"]))
    card3 = b["base"] / "CARD 3"
    t.make_card(card3, groups=(2,))
    for p in (card3 / "DCIM" / "100CANON").glob("*.JPG"):
        p.write_bytes(p.read_bytes() + b"third card")
    code, out = t.run("night.py", "--source", card3, "--check", env=b["env"])
    check("the next backup says nothing about it again", code == 0 and "was saved for every backup" not in out, out)
    code, out = t.run("report_options.py", "next-drives", b["records"], env=b["env"])
    check("and the saved drive can be chosen for the next backup's photos like any other (it is no longer set apart for second copies)",
          "Saved Second" in out, out)
    gone = b["base"] / "drives" / "Nowhere At All"
    code, out = t.run("night.py", "--source", card3, "--name", "typed card", "--date", "2026-11-19", "--second", gone, "--check", env=b["env"])
    check("a second drive typed for one backup that is not there still stops it up front (exit 2)", code == 2 and "second-copy folder is not there" in out, out)
    sf["drives"]["second"] = None
    sf_path.write_text(json.dumps(sf, indent=1), encoding="utf-8")


def a_typed_second_drive(b):
    print("A second drive named for one backup (--second): made after the settle, like the photo drive; and a backup left in its day folder")
    typed = new_drive(b, "Typed Second")
    card = b["base"] / "CARD 4"
    t.make_card(card, groups=(3, 2))
    for p in (card / "DCIM" / "100CANON").glob("*.JPG"):
        p.write_bytes(p.read_bytes() + b"fourth card")
    session = "2026-11-20 typed card"
    night = ["night.py", "--source", card, "--name", "typed card", "--date", "2026-11-20", "--no-peeks", "--second", typed]
    code, out = t.run(*night, env=b["env"])
    st = b["drive"] / session / "_studio"
    m = json.loads((st / "manifest.json").read_text(encoding="utf-8")) if (st / "manifest.json").is_file() else {}
    check("the card is copied and checked first (exit 4), and nothing is on the second drive yet: no copy in the card's layout",
          code == 4 and m.get("files") and not m.get("second") and not any(typed.iterdir()), out[-400:])
    groups = json.loads((st / "groups.json").read_text(encoding="utf-8"))["groups"]
    shoots = [{"id": f"s{i}", "suggested": f"Typed {i}", "groups": [g["id"]], "photos": g.get("count", 0), "recap": "Test frames.", "why": "test"}
              for i, g in enumerate(groups, 1)]
    (st / "shoots.json").write_text(json.dumps({"decided_by": "test", "shoots": shoots}), encoding="utf-8")
    # a folder with the first shoot's name is already on the photo drive, so the settle leaves this backup together
    _, said = py("import studio_file, sort\n"
                 "print(sort.safe_folder(studio_file.render(studio_file.load().get('naming', {}), 'Typed 1', '2026-06-04T09:00:00')))", env=b["env"])
    clash = said.strip().splitlines()[-1]
    (b["drive"] / clash).mkdir()
    code, out = t.run(*night, env=b["env"])
    check("the backup finishes, left together in its day folder (the settle's own reason)", code == 0 and (st / "manifest.json").is_file()
          and "Left together" in out, out[-600:])
    got, want = mirror_tree(typed, session), expected(st, session)
    check("the second copy was made after the sort, with the same folders and names, inside the same day folder as on the photo drive",
          got == want and all(k.startswith(session + "/") or k.startswith(MIRROR) for k in got) and "7b. The second copy" in out,
          f"{sorted(set(got) ^ set(want))} {out[-300:]}")
    check("and the manifest names it as the new kind", json.loads((st / "manifest.json").read_text(encoding="utf-8")).get("second_layout") == "main")
    before = numbers(typed)
    (b["drive"] / clash).rmdir()                               # (they move their folder out of the way; the test's own empty folder)
    code, out = t.run("settle.py", b["drive"] / session, env=b["env"])
    records = b["drive"] / ".studio" / session
    check("the settle then goes through, and says the second copy has the same folders again",
          code == 0 and (records / "settled.json").is_file() and "Your second copy on Typed Second has the same folders and names as Big Kahuna again." in out, out)
    got, want = mirror_tree(typed, session), expected(records, session)
    check("on the second drive the shoots moved up out of the day folder the same way, the very same files, and the empty day folder came down",
          got == want and numbers(typed) == before and not (typed / session).exists()
          and sorted(x.name for x in typed.iterdir() if not x.name.startswith(".")) == shoot_folders(records), f"{sorted(set(got) ^ set(want))} {sorted(x.name for x in typed.iterdir())}")
    check("the fourth card is exactly as it was", all(sha(card / k) == v["card_sha256"] if v.get("card_sha256") else sha(card / k) == v["sha256"]
                                                     for k, v in json.loads((records / "manifest.json").read_text(encoding="utf-8"))["files"].items()))


def words_and_help():
    print("Words")
    import second_copy
    import report_page
    lines = list(second_copy.OUR_WORDS.values()) + list(report_page.OUR_WORDS.values())
    check("no line of ours has an em dash, names Claude, or says she or he",
          not any("—" in w or "Claude" in w or " she " in f" {w.lower()} " or " he " in f" {w.lower()} " for w in lines))
    check("no line of ours holds a path or a Python word", not any("/" in w or "\\" in w or "Error" in w or "Traceback" in w for w in lines),
          str([w for w in lines if "/" in w or "\\" in w]))
    check("none says 'your assistant': it is the Assistant", not any("your assistant" in w.lower() for w in lines))
    check("the plan's exact lines are there", report_page.OUR_WORDS["opts_h"] == "Anything you'd like to change?"
          and report_page.OUR_WORDS["opts_lede"] == "Your photos are safe either way. These are here if you want them."
          and second_copy.OUR_WORDS["eject_wait"] == "A second copy is still being made from this card. It won't be long."
          and second_copy.OUR_WORDS["missed"].startswith("Your second drive wasn't plugged in, so there's one copy for now."))
    check("the two switches are as Nicole answered: looks like the photo drive, and nothing remembered",
          second_copy.REMEMBER_SECOND is False and second_copy.LAYOUT_MAIN == "main" and second_copy.MIRROR_RECORDS == MIRROR)
    check("no line still says the copy is as the card wrote it (but the one for a copy of the earlier kind)",
          not any("card wrote" in w or "copy of the card" in w for w in lines) and "memory card's" in second_copy.OUR_WORDS["card_layout"])
    src = (t.SCRIPTS / "second_copy.py").read_text(encoding="utf-8")
    check("second_copy.py uses backup.py's own functions and has no copy of them",
          all(f"backup.{f}(" in src for f in ("copy_with_hash", "sha256_of", "identity", "ours_to_redo", "onto_itself"))
          and "def copy_with_hash" not in src and "def ours_to_redo" not in src and "def sha256_of" not in src)
    check("nothing in it deletes: no unlink but of its own scratch file, no rmtree, no remove",
          src.count(".unlink()") == 2 and "rmtree" not in src and "os.remove" not in src, str(src.count(".unlink()")))
    code, out = t.run("second_copy.py", "--help")
    check("its help names --to, --check and the exit codes", code == 0 and "--to" in out and "--check" in out and "refused before anything was written" in " ".join(out.split()), out)
    # the proof a moved file must pass, on its own: the same file by its number, else its hash; never neither
    work = Path(tempfile.mkdtemp(prefix="second-proof-"))
    try:
        a, c = work / "a.jpg", work / "c.jpg"
        a.write_bytes(b"the photo")
        c.write_bytes(b"another one")
        st = a.stat()
        ident, entry = [st.st_ino, st.st_size, st.st_mtime_ns], {"size": 9, "sha256": hashlib.sha256(b"the photo").hexdigest()}
        check("proved(): the same file by its identity", second_copy.proved(a, ident, entry) is True)
        check("proved(): another file is not proved by a stale identity, nor by a hash that is not its own",
              second_copy.proved(c, ident, entry) is False and second_copy.proved(c, None, entry) is False)
        check("proved(): with no identity to go by (a drive that numbers no file), the hash proves it, and a missing hash proves nothing",
              second_copy.proved(a, [0, st.st_size, st.st_mtime_ns], entry) is True and second_copy.proved(a, None, {"size": 9}) is False)
    finally:
        shutil.rmtree(work, ignore_errors=True)


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
                the_earlier_kind(b)
                to, before = follows_a_rename(b)
                waits_for_the_drive(b, to, before)
                a_follow_cut_off(b, to, before)
                something_in_the_way(b, to, before)
                a_join(b, to, before)
                a_saved_second_drive(b, work)
                a_typed_second_drive(b)
                check("after everything, the first card is exactly as it was", t.card_snapshot(b["card"]) == b["card_before"])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}" + (f" ({len(SKIPPED)} skipped)" if SKIPPED else ""))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
