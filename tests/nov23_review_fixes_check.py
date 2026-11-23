#!/usr/bin/env python3
"""Version 10's last review (three reviewers on the joined build, Nov 23): one check per finding.

    python3 tests/nov23_review_fixes_check.py [--only files,pages,words] [--work <a folder to keep>] [--port 9960]

  * files  the same card backed up again to ANOTHER place is copied there (never "already backed up" with the new
           drive named and nothing on it); a card whose photos are no longer where its backup put them is copied
           again (never "already safe" from the ledger and the hidden records alone); a sort cut off after its
           index was written is finished and checked by the next run (never called sorted, never left unsettled
           for good); a file left under two names on the second drive by a kill between link and unlink loses its
           old name; a photo deleted from a shoot folder (culling) never stops or jams a rename or a join.
  * pages  the Back up a card box never says "safe to format" over a card that is not the one backed up; a folder
           with a card's DCIM inside, picked with Back up a folder instead, is a folder everywhere; the photo
           drive unplugged after Done is not "something needs a look"; Save the names during a backup is refused
           as a passing line that does not outlive the backup; an empty card has words of its own and no Try
           again; a second copy made after "Second copy not made" reaches the job's record.
  * words  the instructions name the two ways of naming folders as the scripts really behave, carry every part
           of a stopped backup over from the chat, and describe the stopped card as it is.

Everything is pretend: a scratch STUDIO_HOME, drives and cards that are temp folders, no window, no /Volumes.
Every line says ok or FAIL; exit 1 only when something FAILED. Python 3.9, standard library only. No browser.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nov23_whole_check as nw  # noqa: E402  (its pretend computer; it gives even its imports a scratch home)

t, bj = nw.t, nw.bj
SCRIPTS = t.SCRIPTS
PARTS = SCRIPTS.parent / "parts"
D4, THREE, GB = nw.D4, nw.THREE, nw.GB
FAILED = nw.FAILED
COUNT = [0]


def check(what, ok, detail=""):
    COUNT[0] += 1
    return nw.check(what, ok, detail)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def photos(root, skip=(".studio", "_studio", ".studio-second")):
    """The hash of every .JPG under a place, the hidden records left out, sorted."""
    root = Path(root)
    return sorted(sha(p) for p in root.rglob("*") if p.is_file() and p.suffix.upper() == ".JPG"
                  and not any(x in skip for x in p.relative_to(root).parts))


def names(root, skip=(".studio", "_studio", ".studio-second")):
    root = Path(root)
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
                  and not any(x in skip for x in p.relative_to(root).parts))


def whole(block):
    """Run one finding's checks; whatever breaks in it is that finding's FAIL, and the others still run."""
    try:
        block()
    except Exception as e:  # noqa: BLE001
        check(f"this part ran to its end ({block.__name__})", False, f"{e.__class__.__name__}: {e}")


class W(nw.World):
    """The pretend computer, with the scripts run as commands too."""

    def run(self, script, *args, env=None, timeout=300):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], env=t.child_env(dict(self.env, **(env or {}))),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return r.returncode, r.stdout + r.stderr

    def status(self):
        c, o = self.run("backup_job.py", "status")
        try:
            return json.loads(o.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {"_raw": o}

    def job(self, source, dest=None, second=None, name=None, env=None, more=()):
        a = ["start", "--source", source, "--dest", dest or self.dest]
        if second:
            a += ["--second", second]
        if name:
            a += ["--shoot-name", name]
        self.run("backup_job.py", *a, *more, env=env)
        end = time.time() + 240
        r = {}
        while time.time() < end:
            r = self.status()
            if r.get("state") != "running":
                return r
            time.sleep(0.2)
        return r

    def more_drives(self, card, *extra):
        self.drives(card)
        rows = json.loads(self.listing.read_text(encoding="utf-8"))
        rows += [{"path": str(p), "name": p.name, "total": 2000 * GB, "free": 900 * GB, "removable": False} for p in extra]
        self.listing.write_text(json.dumps(rows), encoding="utf-8")

    def view(self):
        """backup_popup.job_view() as the page server would give it, asked in a process of its own."""
        code = ("import json,sys;sys.path.insert(0,%r);import backup_popup;print(json.dumps(backup_popup.job_view()))" % str(SCRIPTS))
        r = subprocess.run([sys.executable, "-c", code], env=t.child_env(self.env), capture_output=True, text=True, encoding="utf-8")
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {"_raw": r.stdout + r.stderr}


def backed_up(work, name, port=0, second=True):
    w = W(work, name, port)
    card = w.card("EOS_DIGITAL", THREE)
    w.drives(card)
    r = w.job(card, second=w.lacie if second else None)
    assert r.get("state") == "done", r
    w.card0, w.rec0, w.on_card = card, Path(r["records"]), photos(card)
    return w


# ---------------------------------------------------------------- files

def files_part(work):
    def _block1():
        print("\nThe same card, backed up again somewhere else", flush=True)
        w = backed_up(work, "other-place", second=False)
        other = w.vol / "OTHER"
        other.mkdir()
        w.more_drives(w.card0, other)
        r = w.job(w.card0, dest=other)
        v = w.view()
        check("picked another drive: the card is copied there, every photo", photos(other) == w.on_card, f"{len(photos(other))} of {len(w.on_card)} on OTHER; {r.get('line')}")
        check("... and nothing says \"already backed up\" about a drive that had nothing on it", not r.get("already") and "already backed up" not in str(r.get("line")), r)
        check("... the card on the home page names the drive the photos are really on", v.get("where") == "OTHER" and photos(other) == w.on_card, v)
        r = w.job(w.card0)             # and again to the first place, where its backup still is, whole
        before = names(w.dest)
        check("the first place again, its backup whole: already backed up, nothing copied twice",
              r.get("state") == "done" and r.get("already") is True and names(w.dest) == before and photos(w.dest) == w.on_card, r)

    def _block2():
        print("\nA card whose photos are no longer where its backup put them", flush=True)
        w = backed_up(work, "all-gone", second=False)
        for d in list(w.dest.iterdir()):
            if not d.name.startswith("."):
                d.rename(w.vol / ("moved-away-" + d.name))
        r = w.job(w.card0)
        v = w.view()
        check("every shoot folder gone, the hidden records left: the card is copied again, never \"already backed up\"",
              r.get("state") == "done" and not r.get("already") and photos(w.dest) == w.on_card, f"{len(photos(w.dest))} of {len(w.on_card)}; {r}")
        check("... \"safe to format\" is only said with every photo on the drive", not v.get("safe_format") or photos(w.dest) == w.on_card, v)
        check("... under the next free name of the day", str(r.get("backup") or "").endswith(" 2"), r.get("backup"))
        w = backed_up(work, "one-gone", second=False)
        gone = sorted(d for d in w.dest.iterdir() if not d.name.startswith("."))[1]
        gone.rename(w.vol / "moved-away")
        r = w.job(w.card0)
        have = set(photos(w.dest))
        check("one shoot folder gone: every photo of the card is on the drive again after the backup",
              r.get("state") == "done" and set(w.on_card) <= have, f"{len(set(w.on_card) & have)} of {len(w.on_card)}; {r.get('line')}")
        w2 = backed_up(work, "chat-gone", second=False)
        for d in list(w2.dest.iterdir()):
            if not d.name.startswith("."):
                d.rename(w2.vol / ("moved-away-" + d.name))
        c, o = w2.run("night.py", "--source", w2.card0, "--dest", w2.dest, "--by-time", "--no-second")
        check("the chat's backup says so too, and copies the card again (never \"This card is already safe\")",
              "already safe" not in o and "no longer where the backup put them" in o and photos(w2.dest) == w2.on_card, o[-700:])
        import second_copy
        w3 = backed_up(work, "saved-over", second=False)
        one = next(p for p in sorted(w3.dest.rglob("*.JPG")) if ".studio" not in p.parts)
        one.write_bytes(one.read_bytes() + b"a rating written into the photo")
        from where import locate
        root, studio = locate(w3.rec0)
        check("a photo saved over since (another size) is still in place: the look counts names, not bytes",
              second_copy.not_in_place(root, studio)[0] == 0, second_copy.not_in_place(root, studio))
        one.rename(one.with_name("renamed by hand.JPG"))
        check("... a photo renamed by hand is not where the backup put it", second_copy.not_in_place(root, studio)[0] == 1, second_copy.not_in_place(root, studio))

    def _block3():
        print("\nA sort cut off after its index was written", flush=True)
        w = W(work, "sort-cut", 0)
        card = w.card("EOS_DIGITAL", THREE)
        w.drives(card)
        marker = w.base / "stopped-once"
        env = {"STUDIO_SORT_STOP_FOR_TESTS": f"after-index|{marker}"}
        r = w.job(card, second=w.lacie, env=env)
        cut = sorted(w.dest.glob("*/_studio/sort-log.json"))
        log = json.loads(cut[0].read_text(encoding="utf-8")) if cut else {}
        check("the sort was stopped once, after the index and before its log said finished", marker.exists() and bool(cut) and not log.get("finished"), f"{r}")
        check("... and the backup is not called done", r.get("state") != "done", r)
        check("... what the sort had proved is already on record (every move checked)", bool(log.get("moves")) and log.get("verified") == len(log["moves"]), f"{log.get('verified')} of {len(log.get('moves') or [])}")
        r = w.job(card, second=w.lacie, env=env)
        studio = Path(r.get("records") or "")
        log = json.loads((studio / "sort-log.json").read_text(encoding="utf-8")) if (studio / "sort-log.json").exists() else {}
        check("Try again finishes it: done, the shoots put away, the second copy made",
              r.get("state") == "done" and r.get("second_ok") is True and (studio / "settled.json").exists() and not list(w.dest.glob("*/_studio")), r)
        check("... the log says finished, with every move of the first run checked (never an empty log over an unchecked one)",
              bool(log.get("finished")) and len(log.get("moves") or []) == 15 and log.get("verified") == 15 and not log.get("problems"),
              f"{len(log.get('moves') or [])} moves, {log.get('verified')} checked, {log.get('finished')}")
        check("... every photo once on both drives", photos(w.dest) == photos(card) and photos(w.lacie) == photos(card))
        # the state the older code left for good: index says sorted, log says nothing checked and not finished
        w = W(work, "sort-old-stuck", 0)
        card = w.card("EOS_DIGITAL", THREE)
        w.drives(card)
        marker = w.base / "stopped-once"
        w.job(card, env={"STUDIO_SORT_STOP_FOR_TESTS": f"after-index|{marker}"})
        lp = sorted(w.dest.glob("*/_studio/sort-log.json"))[0]
        log = json.loads(lp.read_text(encoding="utf-8"))
        log["verified"] = 0
        lp.write_text(json.dumps(log), encoding="utf-8")
        c, o = w.run("sort.py", lp.parent.parent)
        log = json.loads(lp.read_text(encoding="utf-8"))
        check("sort.py by hand on a cut-off sort checks its moves (never \"0 of 0 checked ... Sorted\")",
              c == 0 and log.get("verified") == 15 and len(log.get("moves") or []) == 15 and bool(log.get("finished")), o[-400:])

    def _block4():
        print("\nOne file under two names on the second drive", flush=True)
        w = backed_up(work, "two-names")
        marker = w.base / "link-stop"
        c, o = w.run("join_shoots.py", w.rec0, "--all", "--name", "All of it", env={"STUDIO_LINK_STOP_FOR_TESTS": f"All_0003|{marker}"})
        twice = [p for p in w.lacie.rglob("*.JPG") if p.stat().st_nlink > 1]
        check("a follow killed between the link and the unlink leaves one file under two names", marker.exists() and len(twice) == 2, f"{c} {[p.name for p in twice]}")
        c, o = w.run("second_copy.py", "follow", w.rec0, "--json")
        check("the next follow drops the old name: the second drive has the photo drive's names, no more and no fewer",
              names(w.lacie) == names(w.dest) and not [p for p in w.lacie.rglob("*.JPG") if p.stat().st_nlink > 1],
              f"only on second: {sorted(set(names(w.lacie)) - set(names(w.dest)))}; {o[-200:]}")
        check("... and every photo is still there, once", photos(w.lacie) == w.on_card)
        # a leftover second name from before this fix, on a name a later rename wants
        w = backed_up(work, "leftover-name")
        s1 = sorted(d for d in w.lacie.iterdir() if not d.name.startswith("."))[0]
        f1 = sorted(s1.glob("*.JPG"))[0]
        os.link(f1, f1.with_name(f1.name.replace("Shoot_", "Aurora_", 1)))
        c, o = w.run("rename_shoot.py", w.rec0, "--shoot", "s1", "--name", "Aurora")
        check("a rename whose new name lands on the leftover is not blocked: the second copy follows",
              c == 0 and names(w.lacie) == names(w.dest) and photos(w.lacie) == w.on_card,
              f"only on second: {sorted(set(names(w.lacie)) - set(names(w.dest)))[:3]}; only on main: {sorted(set(names(w.dest)) - set(names(w.lacie)))[:3]}; {o[-300:]}")
        theirs = s1.parent / "theirs.JPG"
        theirs.write_bytes(b"not ours")
        import this_computer
        check("only a second NAME of the same file is ever dropped: another file is never unlinked",
              this_computer.drop_old_name(theirs, sorted(w.lacie.rglob("Aurora_*.JPG"))[0]) is False and theirs.exists())

    def _block5():
        print("\nA photo deleted from a shoot folder (culling)", flush=True)
        w = backed_up(work, "culled")
        s = sorted(d for d in w.dest.iterdir() if not d.name.startswith("."))
        sorted(s[0].glob("*.JPG"))[1].unlink()
        sorted(s[1].glob("*.JPG"))[0].unlink()
        (s[0] / (sorted(s[0].glob("*.JPG"))[0].stem + ".xmp")).write_text("<their edit/>", encoding="utf-8")
        left = photos(w.dest)
        c, o = w.run("rename_shoot.py", w.rec0, "--shoot", "s1", "--name", "Culled")
        check("a rename after a cull goes through (exit 0), the rest renamed, and says the photo was left out",
              c == 0 and (w.dest / "Culled_06-04-26").is_dir() and "no longer in its folder" in o, o[-500:])
        check("... their own sidecar travels with its photo", (w.dest / "Culled_06-04-26" / "Culled_0001_IMG_4471.xmp").is_file())
        c2, o2 = w.run("rename_shoot.py", w.rec0, "--shoot", "s3", "--name", "Third")
        c3, o3 = w.run("join_shoots.py", w.rec0, "--shoots", "s2", "s3", "--name", "Joined")
        check("... and nothing is jammed: another shoot renames and two join afterwards", c2 == 0 and c3 == 0 and (w.dest / "Joined_06-04-26").is_dir(), (o2 + o3)[-600:])
        check("... nothing of theirs was lost on the way", photos(w.dest) == left)
        # the state the older code left: a rename stopped part way on the missing photo, then every run stopped on it
        w = backed_up(work, "culled-jam", second=False)
        c, o = w.run("rename_shoot.py", w.rec0, "--shoot", "s1", "--name", "Jam")
        lp = w.rec0 / "rename-log.json"
        log = json.loads(lp.read_text(encoding="utf-8"))
        e = log["renames"][-1]
        e.pop("finished", None)
        ghost = dict(e["moves"][0], **{"from": "Shoot 1_06-04-26/Shoot_0099_IMG_9999.JPG", "to": "Jam_06-04-26/Jam_0099_IMG_9999.JPG"})
        ghost.pop("moved", None)
        e["moves"].append(ghost)
        e["problems"] = ["missing: Shoot 1_06-04-26/Shoot_0099_IMG_9999.JPG"]
        lp.write_text(json.dumps(log), encoding="utf-8")
        c, o = w.run("rename_shoot.py", w.rec0, "--shoot", "s2", "--name", "After the jam")
        c2, o2 = w.run("join_shoots.py", w.rec0, "--shoots", "s1", "s3", "--name", "Both")
        log = json.loads(lp.read_text(encoding="utf-8"))
        check("a rename left unfinished on a photo that is gone is finished by the next run, which then does its own job",
              c == 0 and (w.dest / "After the jam_06-04-26").is_dir() and not log["renames"][0].get("problems") and bool(log["renames"][0].get("finished")), o[-500:])
        check("... and a join goes through after it", c2 == 0 and (w.dest / "Both_06-04-26").is_dir(), o2[-400:])
    for block in (_block1, _block2, _block3, _block4, _block5):
        whole(block)


# ---------------------------------------------------------------- pages

def pages_part(work, port):
    body = {"source": "card", "card": "EOS_DIGITAL", "dest": {"d": 0, "name": "G PAPA", "path": ["CLIENT WORK"]}, "second": None, "shoot_name": ""}

    def _block1():
        print("\nAnother card in the slot after Done", flush=True)
        w = W(work, "other-card", port)
        card = w.card("EOS_DIGITAL", THREE)
        w.drives(card)
        w.start()
        try:
            w.post("/backup-start", body)
            heads, v = w.watch()
            check("card 1 is backed up: Done, safe to format", v.get("state") == "done" and v.get("safe_format") is True and not v.get("other_card"), v)
            card.rename(w.vol / "card-1-taken-out")
            card2 = w.card("EOS_DIGITAL", [(D4.replace(hour=11), 6)], first_number=7000)
            w.drives(card2)
            p = w.get("/backup-popup")[1]
            check("card 2 in (same name, never backed up): nothing says it is safe to format",
                  p["card"]["name"] == "EOS_DIGITAL" and p["job"].get("safe_format") is False and p["job"].get("other_card") is True, p.get("job"))
            home = w.http("GET", "/home")[1].decode("utf-8", "replace")
            check("... and the box leaves the finished backup's lines out over that card", "!job.other_card) top.append(prog())" in home)
            shutil.rmtree(card2)
            (w.vol / "card-1-taken-out").rename(card)
            w.drives(card)
            p = w.get("/backup-popup")[1]
            check("card 1 back in: its Done lines are back, safe to format", p["job"].get("safe_format") is True and not p["job"].get("other_card"), p.get("job"))

            print("\nThe photo drive unplugged after Done", flush=True)
            backup = v.get("backup")
            shutil.move(str(w.gpapa), str(w.base / "gpapa-unplugged"))
            rows = [r for r in json.loads(w.listing.read_text(encoding="utf-8")) if r["name"] != "G PAPA"]
            w.listing.write_text(json.dumps(rows), encoding="utf-8")
            v = w.get("/backup-job")[1]
            check("the card says the drive isn't plugged in, never \"Something needs a look\"",
                  v.get("head") == "Done." and "G PAPA isn't plugged in right now" in str(v.get("sub")) and "needs a look" not in str(v.get("sub")) and not v.get("bad"), v)
            check("... with nothing to open and nothing claimed", v.get("link") is None and not v.get("safe_format") and not v.get("checked"), v)
            shutil.move(str(w.base / "gpapa-unplugged"), str(w.gpapa))
            w.drives(card)
            v = w.get("/backup-job")[1]
            check("plugged back in: Done. Every photo checked.", v.get("head") == "Done. Every photo checked." and v.get("backup") == backup, v)
        finally:
            w.stop()

    def _block2():
        print("\nA folder with a card's DCIM inside, picked with Back up a folder instead", flush=True)
        w = W(work, "card-dump", port)
        dump = w.mac / "Desktop" / "card dump"
        bj.card_at(dump, [(D4.replace(hour=9), 3), (D4.replace(hour=16), 3)])
        w.drives()
        w.start(STUDIO_PICK_FOLDER_FOR_TESTS=str(dump))
        try:
            r = w.post("/backup-start", dict(body, source="folder", card=None))
            heads, v = w.watch()
            check("it is backed up as a folder: Done, \"in your folder\", nothing about formatting a card",
                  v.get("state") == "done" and v.get("from_folder") is True and v.get("safe_format") is False and "in your folder" in str(v.get("sub")), (r, v))
            rec = w.record()
            m = json.loads((Path(rec["records"]) / "manifest.json").read_text(encoding="utf-8"))
            check("... the backup's own records say folder", m.get("source_kind") == "folder", m.get("source_kind"))
            from urllib.parse import quote
            d = w.get("/name-shoots-data?backup=" + quote(v.get("backup") or ""))[1] or {}
            check("... and Name your shoots says so too (no \"safe to format your card\")", d.get("from_folder") is True and "format" not in json.dumps(d), {k: d.get(k) for k in ("from_folder", "safe_line")})
            rp = (Path(rec["records"]) / "report.html").read_text(encoding="utf-8")
            check("... nor does the report", "safe to format" not in rp)
        finally:
            w.stop()

    def _block3():
        print("\nSave the names while the backup is still being made", flush=True)
        w = W(work, "save-early", port)
        card = w.card("EOS_DIGITAL", THREE)
        w.drives(card)
        w.start(STUDIO_SECOND_COPY_PAUSE_FOR_TESTS="0.6")
        try:
            from urllib.parse import quote
            w.post("/backup-start", dict(body, second={"d": w.drive_no("LaCie"), "name": "LaCie"}))
            asked = {}

            def during(v):
                if v.get("step") == "second" and not asked and v.get("backup"):
                    asked["b"] = v["backup"]
                    asked["r"] = w.post("/name-shoots-save", {"backup": v["backup"], "names": {"s1": "Early Bird"}, "mini": False, "mini_name": ""})[1]
            heads, v = w.watch(during=during)
            r = asked.get("r") or {}
            check("Save the names during the second copy is refused there and then, in the page's own line",
                  r.get("ok") is False and "still being made" in str(r.get("words")), asked)
            d = w.get("/name-shoots-data?backup=" + quote(v.get("backup") or ""))[1] or {}
            check("... and once the backup is done nothing on the page still says so", v.get("state") == "done" and "still being made" not in json.dumps(d), d.get("job"))
            import name_shoots
            studio = Path(w.record()["records"])
            code = ("import sys,json;sys.path.insert(0,%r);import name_shoots;from pathlib import Path;s=Path(%r);"
                    "name_shoots.job_write(s,{'state':'problem','line':name_shoots.OUR_WORDS['problem'].format(line=name_shoots.BEING_MADE),'ask':{}});"
                    "print(json.dumps(name_shoots.job_for_page(s)))" % (str(SCRIPTS), str(studio)))
            out = subprocess.run([sys.executable, "-c", code], env=t.child_env(w.env), capture_output=True, text=True, encoding="utf-8")
            check("a record an earlier version left saying \"still being made\" is not shown once the backup is done", out.stdout.strip().endswith("null"), out.stdout + out.stderr)
            r = w.post("/name-shoots-save", {"backup": v["backup"], "names": {"s1": "Early Bird"}, "mini": False, "mini_name": ""})[1]
            check("... and Save the names works now", (r or {}).get("ok") is True, r)
        finally:
            w.stop()

    def _block4():
        print("\nA card with nothing on it", flush=True)
        w = W(work, "empty-card", port)
        empty = w.vol / "EMPTYCARD"
        (empty / "DCIM" / "100CANON").mkdir(parents=True)
        w.drives(empty)
        w.start()
        try:
            w.post("/backup-start", dict(body, card="EMPTYCARD"))
            heads, v = w.watch()
            check("it says there is nothing on the card to back up, in words of its own",
                  v.get("state") == "problem" and "nothing on this card to back up" in str(v.get("head")) and "your card" not in str(v.get("head")).replace("this card", ""), v)
            check("... with no Try again, and nothing about photos already copied", not v.get("again") and not v.get("sub") and v.get("link") is None, v)
            check("... and Try again by request starts nothing", (w.post("/backup-again", {})[1] or {}).get("ok") is False)
        finally:
            w.stop()

    def _block5():
        print("\nA second copy made after \"Second copy not made\"", flush=True)
        w = W(work, "second-later", 0)
        card = w.card("EOS_DIGITAL", THREE)
        w.drives(card)
        theirs = w.lacie / "Shoot 1_06-04-26"
        theirs.mkdir()
        (theirs / "theirs.txt").write_text("a folder of their own with that name", encoding="utf-8")
        r = w.job(card, second=w.lacie)
        c, o = w.run("backup_job.py", "status", "--words")
        check("the second copy could not be made: the backup is done and says so", r.get("state") == "done" and r.get("second_ok") is False and "not finished" in o, (r, o))
        theirs.rename(w.lacie / "their own folder")
        c, o = w.run("second_copy.py", r["records"], "--to", w.lacie)
        check("made afterwards, as the card's own note says", c == 0, o[-300:])
        c, o = w.run("backup_job.py", "status", "--words")
        r = w.status()
        v = w.view()
        check("the job's record hears of it: \"made and checked\", and the \"isn't made yet\" line is gone",
              "made and checked" in o and "not finished" not in o and r.get("second_ok") is True and "second copy isn" not in str(r.get("line")), (o, r.get("line")))
        check("... and the home card no longer says Second copy not made", not v.get("second_bad") and "Second copy not made" not in json.dumps(v), v.get("steps"))
    for block in (_block1, _block2, _block3, _block4, _block5):
        whole(block)


# ---------------------------------------------------------------- words

def words_part(work):
    def _block1():
        print("\nThe instructions say what the scripts do", flush=True)
        home = work / "words-home"
        home.mkdir(parents=True, exist_ok=True)
        env = t.child_env({"STUDIO_HOME": str(home), "STUDIO_NO_WINDOWS_FOR_TESTS": "1", "PYTHONIOENCODING": "utf-8"})

        def offered(n):
            r = subprocess.run([sys.executable, str(SCRIPTS / "studio_file.py"), "set", "--offered", str(n)], env=env, capture_output=True, text=True, encoding="utf-8")
            return r.stdout + r.stderr
        one, two = offered(1), offered(2)
        check("--offered 1 is the name first, --offered 2 the year first (the scripts)", "Smith Family_10-18-26" in one and "2026-10-18 Smith Family" in two, one + two)
        after = (PARTS / "after-the-report.md").read_text(encoding="utf-8")
        setup = (PARTS / "first-backup-setup.md").read_text(encoding="utf-8")
        import re

        def says(text, n):
            """The words an instruction puts right after `--offered n`, up to the next full stop or `--offered`."""
            m = re.search(r"--offered %d`? ?\(([^)]*)\)" % n, text)
            return m.group(1) if m else ""
        check("after-the-report.md: --offered 1 is described as the name first", "name first" in says(after, 1) and "Smith Family_10-18-26" in says(after, 1), says(after, 1))
        check("after-the-report.md: --offered 2 is described as the year first", "year first" in says(after, 2) and "2026-10-18 Smith Family" in says(after, 2), says(after, 2))
        check("first-backup-setup.md: --offered 2 is described as the year first", "2026-10-18 Smith Family" in says(setup, 2) and "Oct 18 2026" not in setup, says(setup, 2))
        usual = next((ln for ln in setup.splitlines() if ln.startswith("- **Folder names:**")), "")
        check("first-backup-setup.md: the usual folder name is the shoot's name, then the date", "name first" in usual and "Smith Family_10-18-26" in usual and "the date first" not in usual, usual)
        check("after-the-report.md: the naming panel is described with today's two examples", "Black-sand beach_11-19-26" in after and "Black-sand beach, Nov 19 2026" not in after)
        backup = (PARTS / "backup.md").read_text(encoding="utf-8")
        line = next((ln for ln in backup.splitlines() if ln.startswith("- **A problem:**")), "")
        check("backup.md: carrying a stopped backup on from the chat keeps the shoot's name and the folder word",
              "--shoot-name" in line and "--second" in line and "--as-folder" in line, line[:300])
        hello = (PARTS / "hello.md").read_text(encoding="utf-8")
        check("hello.md: the stopped card is described with Try again and See the report, as it is",
              "pressing Start the backup again carries on" not in hello and "**Try again**" in hello and "**See the report**" in hello)
        # the same, done: a one-shoot card stopped on a photo that will not read, carried on from the chat as written
        w = W(work, "carry-on", 0)
        card = w.card("EOS_DIGITAL", [(D4.replace(hour=9), 4)])
        w.drives(card)
        bad = sorted((card / "DCIM").rglob("*.JPG"))[1]
        os.chmod(bad, 0)
        try:
            r = w.job(card, name="Aurora")
        finally:
            os.chmod(bad, 0o644)
        p = r.get("private") or {}
        check("a stopped backup's record holds the name they typed", r.get("state") == "problem" and p.get("shoot_name") == "Aurora", r)
        r = w.job(p.get("source"), dest=p.get("dest"), name=p.get("shoot_name"))
        check("carried on with everything the record holds: the shoot keeps its name", r.get("state") == "done" and (w.dest / "Aurora_06-04-26").is_dir(),
              sorted(d.name for d in w.dest.iterdir()))
    for block in (_block1,):
        whole(block)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="files,pages,words")
    ap.add_argument("--work", default=None)
    ap.add_argument("--port", type=int, default=9960)
    a = ap.parse_args()
    if os.name == "nt":
        print("  SKIP  the whole file   [its pretend drives and hard links are a Mac's; the page tests run there]")
        return 0
    work = Path(a.work) if a.work else Path(tempfile.mkdtemp(prefix="nov23-review-"))
    work.mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(","))
    try:
        if "files" in only:
            files_part(work)
        if "pages" in only:
            pages_part(work, a.port)
        if "words" in only:
            words_part(work)
    finally:
        if not a.work:
            shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'OK' if not FAILED else 'FAILED'}: {COUNT[0] - len(FAILED)} of {COUNT[0]} passed" + ("".join(f"\n  - {f}" for f in FAILED)), flush=True)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
