#!/usr/bin/env python3
"""Checks for what the reviewers of the carousel designer found (safety, and holding up).

Run as part of tests/design_check.py (--only fixes runs just this part), or by itself:

    python3 tests/design_fix_check.py --port 9211 --work /private/tmp/somewhere [--only server | browser]

Every case here failed before its fix (or fails with the fix taken out); the cases say what must hold:

  * a slide that has been in the Carousel folder is never moved out of it because the photographer renamed,
    moved or changed another slide of its set, and is never cleared
  * "Already saved" is only said when saving now would make the very same slides: a photo exported again, a
    font that is there now and was not then, or a new name for the design each make a new set
  * unfinished saves can never lock Save slides for good, and Claude has a command for them
  * a drive that will not take a change is said as that, never as "trying again"
  * the line for Claude can be cleared after the shoot's folder is renamed
  * a name in any alphabet does not stop a command on a computer whose own output can't spell it
  * names nobody can see a difference between, and Windows' reserved words with a dot
  * /kit-photo refuses another website

It needs Pillow (the slides it sends are real JPEGs drawn here) and, for the browser part, Chrome. It makes
its own pretend kits in the work folder, points STUDIO_HOME at them, and stops every server it starts.
"""
import hashlib
import json
import os
import re
import stat
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
W, H = 1080, 1350


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _everywhere(folder):
    """The hash of every file under a folder (to ask: does this slide still exist anywhere in the kit?)."""
    out = set()
    for dp, _, fn in os.walk(folder):
        for f in fn:
            try:
                out.add(_sha(Path(dp) / f))
            except OSError:
                pass
    return out


def check_fixes(case, work, port, make_kit, Server, post, get_json, ask, run, jpeg):
    target = work / "fix"
    ok, out = make_kit(target, "Fix beach", 10)
    if not case("fixes: the pretend kit was made (tests/fake_kit.py)", ok, out):
        return
    ok, out = make_kit(target, "Fix export", 8)
    case("fixes: a second pretend kit", ok, out)
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE", "PYTHONIOENCODING"):
        env.pop(k, None)
    content = target / "The Assistant" / "Your Content"
    kit_name = "2026-11-01 Fix beach"
    kit = content / kit_name
    car = kit / "Carousel"
    sets = kit / ".kit" / "designs" / "sets"
    staging = kit / ".kit" / "design-staging"
    designs = kit / ".kit" / "designs"
    aside = work / "fix-aside"
    aside.mkdir(exist_ok=True)
    sheet = json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]
    answers = []
    toks = [0]
    box = {"P": None}

    def tok():
        toks[0] += 1
        return f"fixtok{toks[0]:05d}"

    def keep(where, data):
        answers.append((where, data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")))

    def POST(path, obj, name=kit_name):
        code, out = post(box["P"], path, dict(obj, kit=name) if isinstance(obj, dict) and "kit" not in obj else obj)
        keep("POST " + path, out)
        return code, out

    def state(did=None, name=kit_name):
        code, st = get_json(box["P"], f"/design-state?kit={quote(name)}" + (f"&design={did}" if did else ""))
        keep("GET /design-state", st)
        return st

    def new(name, slides=2, blocks=None, kitname=kit_name):
        body = {"token": tok(), "state": {"slides": slides, "bg": "#101010", "blocks": blocks or []}}
        if name is not None:
            body["name"] = name
        code, out = POST("/design-new", body, kitname)
        assert code == 200, (code, out)
        return out["design"]

    def stage(did, t, n, seed, quality=85, name=kit_name, only=None):
        last = (None, None)
        for i in (only or range(1, n + 1)):
            code, _, data = ask(box["P"], "POST", f"/design-slide?kit={quote(name)}&design={did}&set={t}&i={i}&of={n}",
                                body=jpeg(seed=seed + i, quality=quality), headers={"Content-Type": "image/jpeg"})
            try:
                last = (code, json.loads(data))
            except ValueError:
                last = (code, None)
            keep("POST /design-slide", data)
            if code != 200:
                break
        return last

    def commit(did, t, rev, drawn=None, name=kit_name):
        body = {"design": did, "set": t, "rev": rev}
        if drawn is not None:
            body["drawn"] = drawn
        return POST("/design-commit", body, name)

    def save(did, rev, n, seed, drawn=None, quality=85, name=kit_name):
        """One whole press of Save slides, as the page does it. -> (status, answer)"""
        t = tok()
        code, out = stage(did, t, n, seed, quality, name)
        if code != 200:
            return code, out
        return commit(did, t, rev, drawn, name)

    def cli(did, t, rev, stop=None, k=kit, extra=()):
        return run(env, "design.py", "commit", str(k), "--design", did, "--set", t, "--rev", str(rev), *extra, more={"DESIGN_TEST_STOP": stop} if stop else None)

    def record(did, t):
        return json.loads((sets / f"{did}-{t}.json").read_text(encoding="utf-8"))

    def in_car(prefix):
        return sorted(n for n in os.listdir(car) if n.startswith(prefix)) if car.is_dir() else []

    def set_folders():
        return sorted(n for n in os.listdir(staging) if (staging / n).is_dir()) if staging.is_dir() else []

    def age(folder, seconds):
        old = time.time() - seconds
        os.utime(folder, (old, old))

    def frame(i, n, x):
        return {"id": i, "n": n, "x": x, "y": 0, "w": W, "h": H, "ox": 0.5, "oy": 0.5, "zoom": 1}

    box["srv"] = Server(env, port)
    try:
        box["P"] = box["srv"].start()
        print(f"      (fixes: page server on port {box['P']}, STUDIO_HOME={studio})", flush=True)
        first = state()
        if not case("fixes: the designer answers for the pretend shoot", bool(first) and first.get("ok") is True, first):
            return

        # ================= 1. a slide that has been in the Carousel folder stays there =================
        def part_1():
            A = new("Family story", 7)
            ta = tok()
            stage(A["id"], ta, 7, 600)
            code, o = cli(A["id"], ta, 0, stop="after-record")
            names_a = [f"Family story - slide {i:02d}.jpg" for i in range(1, 8)]
            case("cut off after the last slide went in: all 7 are in the Carousel folder and the record still says moving",
                 code == 9 and in_car("Family story - ") == names_a and record(A["id"], ta)["state"] == "moving", (code, in_car("Family")))
            hashes_a = {n: _sha(car / n) for n in names_a}
            os.rename(car / names_a[0], car / "Family cover.jpg")          # the photographer renames one slide in their own folder
            B = new("Something else", 7)
            code, o = save(B["id"], 0, 7, 620)
            case("...then they rename one slide, and another design of the shoot is saved: that save works", code == 200 and o.get("ok") and o.get("base") == "Something else", (code, o))
            case("...and the other six slides are STILL in the Carousel folder, byte for byte (none was moved out)",
                 in_car("Family story - ") == names_a[1:] and all(_sha(car / n) == hashes_a[n] for n in names_a[1:]), in_car("Family"))
            case("...and the one they renamed is where they put it, as it was", (car / "Family cover.jpg").is_file() and _sha(car / "Family cover.jpg") == hashes_a[names_a[0]])
            ra = record(A["id"], ta)
            case("...and the record is closed as it stands (done), naming the slide that is now theirs",
                 ra["state"] == "done" and ra.get("theirs") == [names_a[0]] and not ra.get("back"), (ra["state"], ra.get("theirs"), ra.get("back")))
            case("...and nothing of that set is in the hidden waiting folder", f"{A['id']}-{ta}" not in set_folders(), set_folders())
            sa = state(A["id"])["design"]
            case("...and the page for that design is not told 'Already saved' (a slide of the set is no longer under its name)",
                 (sa["set"] or {}).get("base") == "Family story" and sa["set"]["same"] is False and sa["unfinished"] is False, sa["set"])
            for f in set_folders():
                age(staging / f, 2 * 86400)
            C = new("Third", 7)
            code, o = save(C["id"], 0, 7, 640)
            everywhere = _everywhere(kit)
            case("...and two days and another save later, all 7 of those slides still exist in the kit",
                 code == 200 and all(h in everywhere for h in hashes_a.values()), sum(1 for h in hashes_a.values() if h in everywhere))

            D = new("Edited by hand", 7)
            td = tok()
            stage(D["id"], td, 7, 660)
            code, o = cli(D["id"], td, 0, stop="after-record")
            names_d = [f"Edited by hand - slide {i:02d}.jpg" for i in range(1, 8)]
            hashes_d = {n: _sha(car / n) for n in names_d}
            mine = jpeg(seed=999, quality=70)
            (car / names_d[2]).write_bytes(mine)                            # the photographer saves their own edit over slide 03
            E = new("After the edit", 2)
            code, o = save(E["id"], 0, 2, 680)
            rd = record(D["id"], td)
            case("cut off after the last slide, then they save their own edit over one slide: no slide is moved out, and their edit is as they left it",
                 code == 200 and in_car("Edited by hand - ") == names_d and _sha(car / names_d[2]) == hashlib.sha256(mine).hexdigest()
                 and all(_sha(car / n) == hashes_d[n] for n in names_d if n != names_d[2]), in_car("Edited"))
            case("...and that record is closed as done, naming the slide they changed", rd["state"] == "done" and rd.get("theirs") == [names_d[2]], (rd["state"], rd.get("theirs")))

            # a set that was only PART WAY in, and cannot be finished, is put back; what came back is never cleared
            G = new("Half way", 7)
            tg = tok()
            stage(G["id"], tg, 7, 700)
            code, o = cli(G["id"], tg, 0, stop="after-2")
            two = ["Half way - slide 01.jpg", "Half way - slide 02.jpg"]
            hashes_g = {n: _sha(car / n) for n in two} if in_car("Half way - ") == two else {}
            gfolder = staging / f"{G['id']}-{tg}"
            os.rename(gfolder / "slide-03.jpg", aside / "half-way-slide-03.jpg")       # a waiting slide is lost
            Hd = new("Next one", 2)
            code, o = save(Hd["id"], 0, 2, 720)
            rg = record(G["id"], tg)
            case("cut off after 2 of 7, and a waiting slide is lost: the set cannot be finished, so it is put back and the record says which slides came back",
                 code == 200 and bool(hashes_g) and rg["state"] == "undone" and rg.get("back") == ["slide-01.jpg", "slide-02.jpg"] and in_car("Half way - ") == []
                 and sorted(os.listdir(gfolder)) == ["slide-01.jpg", "slide-02.jpg", "slide-04.jpg", "slide-05.jpg", "slide-06.jpg", "slide-07.jpg"],
                 (rg["state"], rg.get("back"), in_car("Half way"), sorted(os.listdir(gfolder)) if gfolder.is_dir() else None))
            never_in = [_sha(gfolder / f"slide-{i:02d}.jpg") for i in range(4, 8)] if gfolder.is_dir() else []
            age(gfolder, 2 * 86400)
            I = new("Day after", 2)
            code, o = save(I["id"], 0, 2, 740)
            older = kit / ".kit" / "design-slides-older"
            kept = sorted(p for p in older.rglob("*.jpg")) if older.is_dir() else []
            case("...two days later the waiting folder is cleared, but the two slides that had been in the Carousel folder are set aside under their own names, not cleared",
                 code == 200 and not gfolder.exists() and [p.name for p in kept] == two and bool(hashes_g) and all(_sha(p) == hashes_g[p.name] for p in kept)
                 and all(p.parent.name.endswith(" Half way") for p in kept), ([str(p.relative_to(kit)) for p in kept], gfolder.exists()))
            everywhere = _everywhere(kit)
            case("...and the four that never reached the Carousel folder (the Assistant's own scratch) are gone", bool(never_in) and not any(h in everywhere for h in never_in))

            # the hash written down is what says a slide is in: a different picture under its name is never taken for it
            Hh = new("Planted", 7)
            th = tok()
            stage(Hh["id"], th, 7, 760)
            code, o = cli(Hh["id"], th, 0, stop="after-journal")
            hfolder = staging / f"{Hh['id']}-{th}"
            os.rename(hfolder / "slide-01.jpg", aside / "planted-slide-01.jpg")
            planted = jpeg(seed=998, quality=60)
            (car / "Planted - slide 01.jpg").write_bytes(planted)
            code, o = cli(Hh["id"], th, 0)
            rh = record(Hh["id"], th)
            case("a waiting slide is gone and a different picture already has its name in the Carousel folder: the set is NOT called saved, and that picture is untouched",
                 code == 1 and rh["state"] == "undone" and in_car("Planted - ") == ["Planted - slide 01.jpg"]
                 and _sha(car / "Planted - slide 01.jpg") == hashlib.sha256(planted).hexdigest() and "RESULT" in o and '"state": "done"' not in o, (code, rh["state"], in_car("Planted"), o[-200:]))

        # ================= 2. "Already saved" only when the very same slides would be made =================
        def part_2():
            rows = [x for x in sheet][:10]
            P_ = new("Marks", len(rows), [frame(i + 1, x["n"], i * W) for i, x in enumerate(rows)])
            st = state(P_["id"])
            v_of = {str(x["n"]): x["v"] for x in st["photos"]}
            body = {"design": P_["id"], "stamp": st["stamp"], "base": P_["rev"], "page": "fixpage001", "state": st["design"]["state"]}
            code, o = POST("/design", body)
            marks = o.get("marks") if o else None
            case("marks: a save's answer gives each photo in use the same mark the page was given with that photo (all 10 photos)",
                 code == 200 and marks == {str(x["n"]): v_of[str(x["n"])] for x in rows} and all(re.fullmatch(r"[0-9a-f]{8}", m) for m in marks.values()), (code, marks))
            marks = marks or {str(x["n"]): v_of[str(x["n"])] for x in rows}
            n_sl = len(rows)
            code, o = save(P_["id"], P_["rev"], n_sl, 800, drawn={"photos": marks, "fell": []})
            case("marks: Save slides with what the slides were drawn from is taken, and named after the design", code == 200 and o.get("base") == "Marks" and not o.get("already"), (code, o))
            s1 = state(P_["id"])["design"]["set"]
            case("marks: with nothing changed the page is told 'Already saved', and that no font was missing", s1["same"] is True and s1.get("fell") == [] and "Already saved" in s1["words"], s1)
            rj = record(P_["id"], f"fixtok{toks[0]:05d}")
            case("marks: the save's record holds what the slides were drawn from", rj.get("drawn") == {"photos": marks, "fell": []}, rj.get("drawn"))
            row = next(x for x in rows if x["file"].lower().endswith(".jpg") and (kit / "Photos" / Path(x["file"]).name).is_file())
            photo = kit / "Photos" / Path(row["file"]).name
            photo.write_bytes(jpeg(w=row["w"], h=row["h"], seed=777, quality=88))   # the same photo, exported again with a new edit
            later = time.time() + 7
            os.utime(photo, (later, later))
            st2 = state(P_["id"])
            v2 = {str(x["n"]): x["v"] for x in st2["photos"]}
            key = str(row["n"])
            case("photo exported again: the page is given a new mark for that photo, and is no longer told 'Already saved'",
                 v2[key] != v_of[key] and st2["design"]["set"]["same"] is False and st2["design"]["set"]["words"] == "", (v2[key], v_of[key], st2["design"]["set"]))
            code, o = POST("/design", dict(body, stamp=st2["stamp"]))
            case("photo exported again: the save's answer says so too (set.same false, the new mark)", code == 200 and o["set"]["same"] is False and (o.get("marks") or {}).get(key) == v2[key], (code, o.get("set")))
            before = in_car("")
            code, o = commit(P_["id"], tok(), P_["rev"])
            case("photo exported again: a commit with no new slides is NOT answered 'already saved'", code == 400 and o.get("why") == "missing" and in_car("") == before, (code, o))
            t2 = tok()
            stage(P_["id"], t2, n_sl, 820)
            code, o = commit(P_["id"], t2, P_["rev"], {"photos": marks, "fell": []})
            case("photo exported again: slides drawn by a page that still has the old picture are refused, with the reason and what to press, and nothing is added",
                 code == 409 and o.get("why") == "photos" and "exported again" in o.get("words", "") and "Reload" in o["words"] and "Nothing was added" in o["words"] and in_car("") == before, (code, o))
            marks2 = dict(marks)
            marks2[key] = v2[key]
            code, o = commit(P_["id"], t2, P_["rev"], {"photos": marks2, "fell": []})
            case("photo exported again: slides drawn from the new picture become a new set beside the first", code == 200 and o.get("base") == "Marks (2)" and not o.get("already")
                 and len(in_car("Marks (2) - ")) == n_sl and len(in_car("Marks - ")) == n_sl, (code, o))
            case("...and now it is 'Already saved' again", state(P_["id"])["design"]["set"]["same"] is True)
            code, o = save(P_["id"], P_["rev"], n_sl, 840, drawn={"photos": marks2, "fell": ["Lora"]})
            s3 = state(P_["id"])["design"]["set"]
            case("font: a set saved while a font could not be loaded is written down as such, and the page is told which font",
                 code == 200 and o.get("base") == "Marks (3)" and s3.get("fell") == ["Lora"] and s3["same"] is True, (code, o, s3))
            code, o = commit(P_["id"], tok(), P_["rev"], {"photos": marks2, "fell": []})
            case("font: once the font is there, a commit is NOT answered 'already saved' (the words would be drawn in the real font now)", code == 400 and o.get("why") == "missing", (code, o))
            code, o = commit(P_["id"], tok(), P_["rev"], {"photos": marks2, "fell": ["Lora"]})
            case("font: with the same font still missing it is 'already saved'", code == 200 and o.get("already") is True and o.get("base") == "Marks (3)", (code, o))
            for label, bad in (("a number", 5), ("photos as a list", {"photos": []}), ("a photo key that is no number", {"photos": {"x": "abcdef12"}}),
                               ("a mark that is no mark", {"photos": {"1": "../../etc"}}), ("a font that is no font's name", {"photos": {}, "fell": ["<script>"]}),
                               ("too many fonts", {"photos": {}, "fell": ["Lora"] * 41})):
                code, o = commit(P_["id"], tok(), P_["rev"], bad)
                case(f"drawn: {label} is refused in plain words", code == 400 and o.get("ok") is False and o.get("words"), (code, o))
            code, o = cli(P_["id"], tok(), P_["rev"], extra=("--drawn", "{not json"))
            case("drawn: the command refuses a --drawn that is not what a page sends", code == 2 and "STOP" in o, (code, o[-200:]))

        # ================= 3. a new name is a change =================
        def part_3():
            R = new("Beach one", 2)
            code, o = save(R["id"], 0, 2, 860)
            stR = state(R["id"])
            bodyR = {"design": R["id"], "stamp": stR["stamp"], "base": 0, "page": "fixpage002", "state": stR["design"]["state"], "name": "Garcia family"}
            code, o = POST("/design", bodyR)
            case("rename: after the design is renamed, the page is not told 'Already saved' under the old name", code == 200 and o["rev"] == 1 and o["set"]["same"] is False, (code, o))
            code, o = save(R["id"], 1, 2, 860)
            case("rename: Save slides then makes the slides under the new name", code == 200 and o.get("base") == "Garcia family" and not o.get("already")
                 and in_car("Garcia family - ") == ["Garcia family - slide 01.jpg", "Garcia family - slide 02.jpg"] and len(in_car("Beach one - ")) == 2, (code, o, in_car("Garcia")))
            code, o = POST("/design", dict(bodyR, base=1, name="garcia FAMILY"))
            case("rename: a change of capitals alone is not a new set (the drive would take the two names for one)", code == 200 and o["set"]["same"] is True and o["set"]["base"] == "Garcia family", (code, o.get("set")))

        # ================= 4. unfinished saves never lock Save slides for good =================
        def part_4():
            Q = new("Waiting", 2)
            for f in set_folders():
                age(staging / f, 2 * 86400)
            state()                                                         # (asking for the page's state clears nothing by itself)
            code, _, _ = ask(box["P"], "GET", f"/design.html?kit={quote(kit_name)}")
            case("waiting slides: opening the designer clears day-old slides of saves that were never finished", code == 200 and set_folders() == [], set_folders())
            staging.mkdir(parents=True, exist_ok=True)
            for k in range(60):
                (staging / f"note-{k:02d}.txt").write_text("not a set of slides", encoding="utf-8")
            code, o = stage(Q["id"], tok(), 2, 880, only=[1])
            case("waiting slides: 60 stray files in the hidden waiting folder do not count as unfinished saves", code == 200, (code, o))
            for k in range(59):
                code, o = stage(Q["id"], tok(), 2, 880, only=[1])
            case("waiting slides: 60 unfinished saves can be waiting", code == 200 and len(set_folders()) == 60, (code, len(set_folders())))
            code, o = stage(Q["id"], tok(), 2, 880, only=[1])
            case("waiting slides: with 60 waiting, all just started, one more is refused in plain words", code == 503 and o.get("why") == "waiting" and o.get("words"), (code, o))
            code, o = run(env, "design.py", "show", kit_name)
            case("waiting slides: design.py show says how many unfinished saves are waiting and names the command", code == 0 and "60 unfinished saves" in o and "design.py tidy" in o, o[-400:])
            code, o = run(env, "design.py", "tidy", kit_name)
            case("waiting slides: design.py tidy leaves alone what was started within the hour", code == 0 and "Nothing was old enough" in o and len(set_folders()) == 60, (code, o))
            for f in set_folders():
                age(staging / f, 2 * 3600)
            code, o = stage(Q["id"], tok(), 2, 880, only=[1])
            case("waiting slides: two hours later Save slides works again by itself (the abandoned ones are cleared first)", code == 200 and len(set_folders()) == 1, (code, o, len(set_folders())))
            S_ = new("On its way", 2)
            ts = tok()
            stage(S_["id"], ts, 2, 900)
            code, o = cli(S_["id"], ts, 0, stop="after-journal")
            for f in set_folders():
                age(staging / f, 3 * 86400)
            code, o = run(env, "design.py", "tidy", kit_name)
            sfolder = staging / f"{S_['id']}-{ts}"
            case("waiting slides: design.py tidy clears an abandoned save and says so, and never touches a set that is on its way in",
                 code == 0 and "Cleared the waiting slides of 1 unfinished save" in o and sorted(os.listdir(sfolder)) == ["slide-01.jpg", "slide-02.jpg"] and set_folders() == [sfolder.name], (code, o, set_folders()))
            code, o = cli(S_["id"], ts, 0)
            case("...and that set then finishes under its name", code == 0 and in_car("On its way - ") == ["On its way - slide 01.jpg", "On its way - slide 02.jpg"], (code, o[-200:]))

        # ================= 5. a drive that will not take a change is said as that =================
        def part_5():
            R = new("Drive", 2)
            stR = state(R["id"])
            changed = dict(stR["design"]["state"], bg="#abcdef")
            before = (designs / f"{R['id']}.json").read_bytes()
            mode = stat.S_IMODE(designs.stat().st_mode)
            os.chmod(designs, 0o555)
            try:
                code, o = POST("/design", {"design": R["id"], "stamp": stR["stamp"], "base": stR["design"]["rev"], "page": "fixpage003", "state": changed})
                case("drive: a design that can't be written is answered with the reason ('why': 'drive'), not 'could not reach the Assistant'",
                     code == 500 and o.get("why") == "drive" and o.get("words", "").startswith("Your changes can't be saved right now: a folder in this kit can't be written to")
                     and "/" not in o["words"] and (designs / f"{R['id']}.json").read_bytes() == before, (code, o))
                code, o = POST("/design-new", {"token": tok(), "name": "No room"})
                case("drive: a new design that can't be written says why too", code == 500 and o.get("why") == "drive" and o.get("words", "").startswith("That couldn't be saved: "), (code, o))
            finally:
                os.chmod(designs, mode)
            code, o = POST("/design", {"design": R["id"], "stamp": stR["stamp"], "base": stR["design"]["rev"], "page": "fixpage003", "state": changed})
            case("drive: once the folder can be written again the same save goes through", code == 200 and o.get("ok"), (code, o))
            staging.mkdir(parents=True, exist_ok=True)
            mode = stat.S_IMODE(staging.stat().st_mode)
            os.chmod(staging, 0o555)
            try:
                code, o = stage(R["id"], tok(), 2, 920, only=[1])
                case("drive: a slide that can't be kept says why, in the words Save slides shows", code == 500 and o.get("why") == "drive" and o.get("words", "").startswith("Couldn't save the slides: ")
                     and "Nothing was lost" in o["words"], (code, o))
            finally:
                os.chmod(staging, mode)

        # ================= names =================
        def part_6():
            d = new("Plain‍")
            d2 = new("‎Plain‮ copy")
            case("names: marks nobody can see are not kept at the ends of a design's name, and direction marks nowhere", d["name"] == "Plain" and d2["name"] == "Plain copy", (d["name"], d2["name"]))
            Z = new("In‍visible", 2)
            code, o = save(Z["id"], 0, 2, 940)
            case("names: a mark nobody can see never reaches a file name", code == 200 and o.get("base") == "Invisible" and in_car("Invisible - ") == ["Invisible - slide 01.jpg", "Invisible - slide 02.jpg"], (code, o))
            X = new("aux.txt", 2)
            code, o = save(X["id"], 0, 2, 960)
            case("names: a word Windows keeps for itself gets its underscore straight after the word, before the dot", code == 200 and o.get("base") == "aux_.txt"
                 and in_car("aux") == ["aux_.txt - slide 01.jpg", "aux_.txt - slide 02.jpg"], (code, o, in_car("aux")))
            T1 = new("Twin", 2)
            code, o = save(T1["id"], 0, 2, 980)
            for n in in_car("Twin - "):
                os.rename(car / n, aside / n)                              # they move that set's slides out by hand
            T2 = new("Twin", 2)
            code, o = save(T2["id"], 0, 2, 990, quality=40)
            s_t1 = state(T1["id"])["design"]["set"]
            case("names: two designs with one name: the first is not told 'Already saved' when the files under those names are the second's",
                 code == 200 and o.get("base") == "Twin" and s_t1["same"] is False, (code, o, s_t1))

        # ================= /kit-photo and another website =================
        def part_7():
            n1 = sheet[0]["n"]
            ask(box["P"], "GET", f"/design.html?kit={quote(kit_name)}")       # opening the page has the small copies made
            for _ in range(150):
                if ask(box["P"], "GET", f"/kit-photo?kit={quote(kit_name)}&n={n1}&size=s")[0] == 200:
                    break
                time.sleep(0.2)
            code, h, data = ask(box["P"], "GET", f"/kit-photo?kit={quote(kit_name)}&n={n1}&size=s", headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Dest": "image"})
            case("kit-photo: a picture asked for by another website through the browser is refused", code == 403 and data[:2] != b"\xff\xd8", code)
            code, h, data = ask(box["P"], "GET", f"/kit-photo?kit={quote(kit_name)}&n={n1}&size=s", headers={"Sec-Fetch-Site": "same-origin"})
            case("kit-photo: the page's own request is answered, marked as for this page only", code == 200 and data[:2] == b"\xff\xd8" and h.get("cross-origin-resource-policy") == "same-origin", (code, h))

        # ================= 6. the line for Claude after the folder is renamed =================
        def part_8():
            kit2_name = "2026-11-01 Fix export"
            st = state(name=kit2_name)
            X2 = st["design"]
            n2 = X2["state"]["slides"]
            code, o = save(X2["id"], X2["rev"], n2, 1000, name=kit2_name)

            def lines():
                c, out = run(env, "home.py", "pending")
                return [ln for ln in out.splitlines() if ln.startswith("ARRANGED:") and "| design |" in ln]

            case("took: after Save slides the line for Claude names the kit's folder", code == 200 and len([ln for ln in lines() if "Fix export |" in ln]) == 1, lines())
            os.rename(content / kit2_name, content / "2026-11-01 Fix export renamed")
            code, o = run(env, "design.py", "took", "2026-11-01 Fix export renamed")
            case("took: after the folder is renamed, took under its NEW name clears the line left under the old one", code == 0 and "Cleared" in o and not [ln for ln in lines() if "Fix export" in ln], (code, o, lines()))
            k3 = "2026-11-01 Fix export renamed"
            st = state(name=k3)
            bodyX = {"design": X2["id"], "stamp": st["stamp"], "base": st["design"]["rev"], "page": "fixpage004", "state": dict(st["design"]["state"], bg="#123456")}
            code, o = POST("/design", bodyX, k3)
            code, o = save(X2["id"], o["rev"], n2, 1020, name=k3)
            os.rename(content / k3, content / "2026-11-02 Moved shoot")
            was = [ln for ln in lines() if "Fix export renamed |" in ln]
            code, o = run(env, "design.py", "took", k3)
            case("took: the kit name exactly as the line gives it clears the line even though no folder has that name any more",
                 len(was) == 1 and code == 0 and "Cleared" in o and not [ln for ln in lines() if "Fix export" in ln], (was, code, o, lines()))

        # ================= 8. a name in any alphabet, on a computer whose own output can't spell it =================
        def part_9():
            Pz = new("Plaża \U0001F30A", 2)
            pc = {"PYTHONIOENCODING": "cp1252"}
            code, o = run(env, "design.py", "show", kit_name, more=pc)
            case("code page: design.py show lists a design named in Polish with an emoji when the output is a PC's own code page", code == 0 and "Traceback" not in o and Pz["id"] in o, (code, o[-300:]))
            box["srv"].stop()
            box["srv"] = Server(dict(env, **pc), port + 1)
            box["P"] = box["srv"].start()
            code, o = save(Pz["id"], 0, 2, 1040)
            case("code page: Save slides on that design says it worked (it did), on a server whose output is a PC's own code page",
                 code == 200 and o.get("ok") and len(in_car("Plaża")) == 2, (code, o, in_car("Pla")))
            box["srv"].stop()
            box["srv"] = Server(dict(env, DESIGN_TEST_STOP="after-done"), port + 2)
            box["P"] = box["srv"].start()
            Nr = new("No result", 2)
            code, o = save(Nr["id"], 0, 2, 1060)
            case("no result line: when the command that places the slides stops without saying how it went, the record on the drive is read: the set is in, and the page is told so",
                 code == 200 and o.get("ok") and o.get("base") == "No result" and len(in_car("No result - ")) == 2, (code, o))

        # ================= nothing leaked, nothing fell over =================
        def part_10():
            leaks = []
            for where, data in answers:
                text = data.decode("utf-8", "replace")
                for bad in (str(work), "/private/", "/Users/", "/Volumes/", "Traceback", ".kit"):
                    if bad in text:
                        leaks.append((where, bad))
            case(f"fixes: none of the {len(answers)} answers given here holds a path or an error's innards", not leaks, sorted(set(leaks))[:6])
            log = (studio / "arrange.log").read_text(encoding="utf-8", errors="replace") if (studio / "arrange.log").is_file() else ""
            case("fixes: the server's log holds no Python error", "Traceback" not in log, [ln for ln in log.splitlines() if "Traceback" in ln][:3])
        import traceback
        want = [x for x in os.environ.get("DESIGN_FIX_PARTS", "").split(",") if x]      # e.g. "1,2": only those parts
        for part in (part_1, part_2, part_3, part_4, part_5, part_6, part_7, part_8, part_9, part_10):
            if want and part.__name__.split("_")[1] not in want:
                continue
            try:
                part()
            except Exception as e:  # noqa: BLE001
                case(f"fixes: {part.__name__} of the checks ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-500:]}")
    finally:
        box["srv"].stop()
        for p in (designs, staging):
            try:
                os.chmod(p, 0o755)
            except OSError:
                pass


def check_fixes_browser(case, work, port, make_kit, Server, post, get_json, jpeg):
    """The same findings where they show on the real page, in a hidden Chrome. -> "skipped" when there is no Chrome."""
    sys.path.insert(0, str(ROOT / "tests"))
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  the real-browser checks of the reviewers' findings: no Chrome on this computer", flush=True)
        return "skipped"
    import design_save_check
    target = work / "fix-browser"
    ok, out = make_kit(target, "Fix page", 10)
    if not case("fixes browser: the pretend kit was made", ok, out):
        return None
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE", "PYTHONIOENCODING"):
        env.pop(k, None)
    kit_name = "2026-11-01 Fix page"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    designs = kit / ".kit" / "designs"
    car = kit / "Carousel"
    sheet = json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]
    srv = Server(env, port)
    P = srv.start()
    base = f"http://127.0.0.1:{P}"
    toks = [0]
    mode = None
    try:
        with cd.Chrome(work=work / "chrome-fixes", size=(1280, 900)) as c:
            c.init_script(design_save_check.NO_FINDER_JS)

            def J(expr):
                return json.loads(c.js("JSON.stringify(" + expr + ")"))

            def new_design(state, name):
                toks[0] += 1
                code, out = post(P, "/design-new", {"kit": kit_name, "token": f"fixbrowser{toks[0]:04d}", "state": state, "name": name})
                assert code == 200, (code, out)
                return out["design"]["id"]

            def disk(i):
                return json.loads((designs / f"{i}.json").read_text(encoding="utf-8"))

            def ready(seconds=25):
                c.wait_for("window.Designer && Designer.saver && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", seconds,
                           tell="document.body.innerText.slice(0, 300)")

            def saved(seconds=12):
                try:
                    c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", seconds)
                    return True
                except cd.Timeout:
                    return False

            def press_save(seconds=90):
                c.click("#save-slides")
                c.wait_for("!Designer.saver.busy() || Designer.saver.asking()", seconds, tell="document.getElementById('save-line').textContent")
                return c.text("#save-line")

            def in_car(prefix):
                return sorted(n for n in os.listdir(car) if n.startswith(prefix)) if car.is_dir() else []

            # ---- the page going out of sight saves at once, with every timer held ----
            D1 = new_design({"slides": 3, "bg": "#ffffff", "blocks": []}, "Out of sight")
            c.hold_timers()
            try:
                c.open(f"{base}/design.html?kit={KQ}&design={D1}")
                c.wait_for("window.Designer && Designer.st && Designer.S", 15)
                c.click("#slides-plus")
                case("out of sight: with timers held a change is on the page and not yet on the drive", J("Designer.st.slides") == 4 and disk(D1)["state"]["slides"] == 3 and c.text("#d-status") == "Saving...",
                     (J("Designer.st.slides"), disk(D1)["state"]["slides"], c.text("#d-status")))
                c.js("Object.defineProperty(document, 'hidden', {configurable: true, get: function(){ return true; }}); document.dispatchEvent(new Event('visibilitychange'));")
                try:
                    got = cd.wait_until(lambda: disk(D1)["state"]["slides"] == 4, 6)
                except cd.Timeout:
                    got = False
                case("out of sight: when the page is hidden the change is saved at once, waiting on no timer", bool(got) and disk(D1)["rev"] == 1, disk(D1)["rev"])
                c.js("delete document.hidden")
            finally:
                c.free_timers()

            # ---- a drive that will not take the change: the line says why, and it saves by itself afterwards ----
            c.open(f"{base}/design.html?kit={KQ}&design={D1}")
            ready()
            mode = stat.S_IMODE(designs.stat().st_mode)
            os.chmod(designs, 0o555)
            try:
                c.click("#slides-plus")
                try:
                    c.wait_for("document.getElementById('d-trouble').textContent.indexOf('can\\'t be saved right now') >= 0", 8)
                    said = c.text("#d-trouble")
                except cd.Timeout:
                    said = c.text("#d-trouble")
                case("drive: when the kit's folder can't be written, the name has 'Not saved' beside it and the line in the bar at the bottom says why (not 'Trying again')",
                     c.text("#d-status") == "Not saved" and said.startswith("Your changes can't be saved right now: a folder in this kit can't be written to") and "Trying again" not in said and "/" not in said, said)
                line = press_save(30)
                case("drive: Save slides then says the design couldn't be saved and nothing was added, and makes nothing", "couldn’t be saved" in line and "Nothing was added" in line and in_car("Out of sight") == [], line)
            finally:
                os.chmod(designs, mode)
                mode = None
            case("drive: once the folder can be written again the change saves by itself", saved(12) and disk(D1)["state"]["slides"] == J("Designer.st.slides") == 5, (c.text("#d-status"), disk(D1)["state"]["slides"]))

            # ---- a photo exported again ----
            row = next(x for x in sheet if x["file"].lower().endswith(".jpg") and (kit / "Photos" / Path(x["file"]).name).is_file())
            n = row["n"]
            D2 = new_design({"slides": 2, "bg": "#ffffff", "blocks": [{"id": 1, "n": n, "x": 0, "y": 0, "w": W, "h": H, "ox": 0.5, "oy": 0.5, "zoom": 1}]}, "Reexport")
            c.open(f"{base}/design.html?kit={KQ}&design={D2}")
            ready()
            saved()
            line = press_save()
            if c.js("Designer.saver.asking()"):
                c.click("#save-yes")                                    # slide 2 is bare: save anyway
                c.wait_for("!Designer.saver.busy()", 60)
                line = c.text("#save-line")
            first = in_car("Reexport - ")
            case("re-export: the first Save slides makes the set", "Saved 2 slides" in line and first == ["Reexport - slide 01.jpg", "Reexport - slide 02.jpg"], (line, first))
            h1 = _sha(car / first[0]) if first else ""
            line = press_save()
            case("re-export: pressed again with nothing changed it says Already saved", "Already saved as \"Reexport\"" in line and in_car("Reexport") == first, line)
            photo = kit / "Photos" / Path(row["file"]).name
            from PIL import Image
            Image.new("RGB", (row["w"], row["h"]), (250, 30, 200)).save(photo, "JPEG", quality=90)      # a new edit under the same file name
            later = time.time() + 9
            os.utime(photo, (later, later))
            line = press_save()
            note = c.text("#d-note")
            case("re-export: with the page still showing the old picture, Save slides says a photo was exported again, makes nothing, and Reload is at the top of the page",
                 "exported again" in line and "Already saved" not in line and "Reload" in line and "Reload" in note and c.count("#d-note button") == 1 and in_car("Reexport") == first, (line, note))
            c.open(f"{base}/design.html?kit={KQ}&design={D2}")
            ready()
            c.wait_for("Designer.S.photos.every(function(p){ return p.have || p.missing; })", 40)
            saved()
            line = press_save()
            if c.js("Designer.saver.asking()"):
                c.click("#save-yes")
                c.wait_for("!Designer.saver.busy()", 60)
                line = c.text("#save-line")
            second = in_car("Reexport (2) - ")
            case("re-export: after Reload, Save slides makes a new set from the new edit (not 'Already saved')",
                 "Saved 2 slides" in line and "Reexport (2)" in line and len(second) == 2 and in_car("Reexport - ") == first and _sha(car / first[0]) == h1, (line, in_car("Reexport")))
            if second:
                px = Image.open(car / second[0]).convert("RGB").getpixel((540, 675))
                case("re-export: the new slide shows the new edit", abs(px[0] - 250) < 14 and abs(px[1] - 30) < 14 and abs(px[2] - 200) < 14, px)
            line = press_save()
            case("re-export: and pressed once more it is Already saved, under the new set's name", "Already saved as \"Reexport (2)\"" in line, line)

            # ---- a new name ----
            c.js("(function(e){ e.focus(); e.select(); })(document.getElementById('d-name-box'))")
            c.type_text("Garcia family")
            c.key("Enter")
            saved()
            line = press_save()
            if c.js("Designer.saver.asking()"):
                c.click("#save-yes")
                c.wait_for("!Designer.saver.busy()", 60)
                line = c.text("#save-line")
            case("rename: after the design is renamed in its box, Save slides makes the slides under the new name",
                 "Saved 2 slides" in line and "Garcia family" in line and in_car("Garcia family - ") == ["Garcia family - slide 01.jpg", "Garcia family - slide 02.jpg"], (line, in_car("Garcia")))
            errs = [e for e in c.page_errors() if "500" not in str(e)]
            case("fixes browser: the page had no errors of its own", errs == [], errs[:3])
    finally:
        srv.stop()
        if mode is not None:
            try:
                os.chmod(designs, mode)
            except OSError:
                pass
    return None


def main():
    import argparse
    sys.path.insert(0, str(ROOT / "tests"))
    import design_check as dc
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a new folder under /private/tmp for this run")
    ap.add_argument("--port", type=int, default=8931)
    ap.add_argument("--only", choices=["server", "browser"])
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if dc.SAFE not in work.parents:
        print(f"STOP: {work} is not under {dc.SAFE}.")
        return 2
    if (work / "fix").exists() or (work / "fix-browser").exists():
        print(f"STOP: {work} already holds a pretend kit from an earlier run. Give a new --work folder.")
        return 2
    work.mkdir(parents=True, exist_ok=True)
    os.environ["STUDIO_HOME"] = str(work / "no-studio")
    if a.only in (None, "server"):
        check_fixes(dc.case, work, a.port, dc.make_kit, dc.Server, dc.post, dc.get_json, dc.ask, dc.run, dc.jpeg)
    if a.only in (None, "browser"):
        check_fixes_browser(dc.case, work, a.port + 3, dc.make_kit, dc.Server, dc.post, dc.get_json, dc.jpeg)
    bad = [n for n, ok in dc.results if not ok]
    print()
    print(f"{len(dc.results)} cases, {len(dc.results) - len(bad)} passed, {len(bad)} failed.  Work folder: {work}")
    for n in bad:
        print("  FAILED:", n)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
