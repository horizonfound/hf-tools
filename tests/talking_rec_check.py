#!/usr/bin/env python3
"""Checks on talking_rec.py: a talking reel's record, a save from the page field by field, the Talking folder,
and the assistant's commands in the chat (Nicole's handoffs v23 and v24, built our way).

    python3 tests/talking_rec_check.py

Runs in a throwaway folder with its own pretend Assistant (STUDIO_HOME is set to it, so nothing lands in the
real one); starts no server and makes no video (the one video it uses is the tiny tests/fixtures/loud-tone-3s.mp4,
copied in and only ever read by its header). Her rules are compared with her own file character for character
when her v24 folder is beside the repo, or beside the main checkout when this is a worktree (SKIP when it is
not); her v25 and v27 packs leave talking.py unchanged, so v24 stays the file compared.

Every line must say PASS (or SKIP). Python 3.9, standard library only, a Mac or a PC.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "the-engine" / "skills"
SCRIPTS = SKILLS / "studio-manager" / "scripts"
REEL = SKILLS / "assistant-make-a-reel" / "scripts"
CLI = SCRIPTS / "talking_rec.py"
CLIP = ROOT / "tests" / "fixtures" / "loud-tone-3s.mp4"
SHOOT = "2026-09-23 Hannah & Zoë's beach"
SHORT = "Hannah & Zoë's beach"
fails = 0

TMP = Path(tempfile.mkdtemp(prefix="talking-rec-check-")).resolve()
STUDIO = TMP / "studio"
HOME = TMP / "The Assistant"
CONTENT = HOME / "Your Content"
KIT = CONTENT / SHOOT
REC = KIT / ".kit" / "talking.json"
PREV = KIT / ".kit" / "talking.prev.json"
WORDSF = KIT / ".kit" / "talking-words.json"
os.environ["STUDIO_HOME"] = str(STUDIO)
os.environ["PYTHONIOENCODING"] = "utf-8"
ENV = dict(os.environ)

REAL = Path.home() / (".stu" + "dio")       # only ever listed, to prove this test leaves it alone


def real_listing():
    try:
        return sorted((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in REAL.iterdir())
    except OSError:
        return None


REAL_BEFORE = real_listing()


def check(name, cond, got=None):
    global fails
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond or got is None else f"\n        got: {got!r}"))
    fails += 0 if cond else 1


def run(*args):
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, encoding="utf-8", env=ENV)


N = [0]


def jfile(d, bom=False):
    N[0] += 1
    f = TMP / f"in{N[0]}.json"
    f.write_text(d if isinstance(d, str) else json.dumps(d, ensure_ascii=False), encoding="utf-8-sig" if bom else "utf-8")
    return str(f)


def rec():
    return json.loads(REC.read_text(encoding="utf-8"))


def make_kit(folder, photos=12):
    k = CONTENT / folder
    (k / ".kit").mkdir(parents=True)
    (k / "Photos").mkdir()
    (k / ".kit" / "kit.json").write_text(json.dumps({"name": folder.split(" ", 1)[1]}), encoding="utf-8")
    (k / ".kit" / "sheet.json").write_text(json.dumps({"photos": [{"n": i, "file": f"IMG_{i:04d}.jpg"} for i in range(1, photos + 1)]}), encoding="utf-8")
    return k


# Eighteen words, two sentences (the first ends at word 7, "beach."). Every word 0.25 s long, one every half second.
SAID = "OK so um we were at the beach. And when when the kids ran in it was awesome.".split()
WORDS = [{"w": w, "start": round(i * 0.5, 3), "end": round(i * 0.5 + 0.25, 3), "conf": 0.9} for i, w in enumerate(SAID)]
NW = len(WORDS)
E1 = 7          # the last word of the first sentence

try:
    STUDIO.mkdir(parents=True)
    (STUDIO / "studio.json").write_text(json.dumps({"posts": {"home": str(HOME)}}), encoding="utf-8")
    make_kit(SHOOT)
    make_kit("2026-10-01 Hannah")
    make_kit("2026-10-08 Hannah minis")

    sys.path.insert(0, str(SCRIPTS))
    import talking_rec as TR      # noqa: E402
    import reel_page              # noqa: E402
    import arrange                # noqa: E402
    eng = TR._engine()
    check("the test's own Assistant folder is the scratch one", Path(arrange.HOME) == STUDIO, str(arrange.HOME))

    # ------------------------------------------------------------ finding the kit from the pasted name
    check("find: the short name the page writes finds its shoot, accent and apostrophe and all", TR.find(SHORT) == KIT)
    check("find: a short name that is exactly one shoot's wins over another shoot that holds the same word",
          TR.find("Hannah") == CONTENT / "2026-10-01 Hannah" and TR.find("hannah minis") == CONTENT / "2026-10-08 Hannah minis")
    check("find: a few words still do (kit.find_kit)", TR.find("zoë beach") == KIT and TR.find(str(KIT)) == KIT)
    check("short_name is hers: the folder without its date", TR.short_name(KIT) == SHORT)

    # ------------------------------------------------------------ nothing yet
    before_files = sorted(p.name for p in (KIT / ".kit").iterdir())
    st = TR.state_for_page(KIT)
    check("no record yet: an empty state in her shape",
          st["ok"] and st["folder"] is False and st["videos"] == [] and st["working"] is False and st["rec"]["words"] == []
          and st["pieces"] == [] and st["shots"] == [] and st["zooms"] == [] and st["captions"] == [] and st["rev"] == 0
          and st["rec"]["claude_cut"] is None and st["rec"]["captions"] is True and st["short"] == SHORT, st)
    check("... and asking wrote nothing", sorted(p.name for p in (KIT / ".kit").iterdir()) == before_files)
    r = run("show", SHORT)
    check("show with no script: her STOP line, exit 2",
          r.returncode == 2 and r.stdout.strip() == "STOP: there's no script for this shoot yet: on the page, add their video and press Edit my video", r.stdout)
    r = run("cut", SHORT, "--file", jfile({"cut": [[0, 1]]}))
    check("cut with no script: her STOP line", r.returncode == 2 and r.stdout.strip() == "STOP: no script yet", r.stdout)
    r = run("place", SHORT, "--file", jfile({"shots": []}))
    check("place with no script: her STOP line", r.returncode == 2 and r.stdout.strip() == "STOP: no script yet", r.stdout)
    r = run("photos", SHORT)
    check("photos with no script: her STOP line", r.returncode == 2 and "there's no script for this shoot yet" in r.stdout, r.stdout)
    check("... and none of them made a record", not REC.exists())

    # ------------------------------------------------------------ the Talking folder
    (KIT / "Talking").mkdir()
    (KIT / "Footage").mkdir()
    shutil.copyfile(CLIP, KIT / "Talking" / "my talk.mp4")
    shutil.copyfile(CLIP, KIT / "Talking" / "second take.MOV")
    (KIT / "Talking" / ".hidden.mp4").write_bytes(CLIP.read_bytes())
    (KIT / "Talking" / "notes.txt").write_text("not a video", encoding="utf-8")
    shutil.copyfile(CLIP, KIT / "Footage" / "clip one.mp4")
    foot_before = reel_page.list_videos(KIT)
    foot_facts = (KIT / ".kit" / "footage" / "facts.json").read_bytes()
    talks = TR.list_talks(KIT)
    check("list_talks: the videos in Talking, in name order; dot files and other files left out",
          [v["name"] for v in talks] == ["my talk.mp4", "second take.MOV"], [v["name"] for v in talks])
    check("... each with its key and its facts (read from the header only)",
          all(TR.KEY.fullmatch(v["key"]) and v["facts"].get("length") and v["facts"].get("has_audio") for v in talks), talks)
    check("... their facts are kept in a file of Talking's own", (KIT / ".kit" / "talking" / "facts.json").is_file()
          and set(json.loads((KIT / ".kit" / "talking" / "facts.json").read_text(encoding="utf-8"))) == {v["key"] for v in talks})
    check("... and Footage's listing and its facts file are exactly as before",
          reel_page.list_videos(KIT) == foot_before and [v["name"] for v in foot_before] == ["clip one.mp4"]
          and (KIT / ".kit" / "footage" / "facts.json").read_bytes() == foot_facts)
    check("talk_by_key and talk_by_name find a video; a made-up key or name finds none",
          TR.talk_by_key(KIT, talks[0]["key"])["name"] == "my talk.mp4" and TR.talk_by_name(KIT, "MY TALK.mp4")["key"] == talks[0]["key"]
          and TR.talk_by_key(KIT, "0" * 12) is None and TR.talk_by_key(KIT, "../x") is None and TR.talk_by_name(KIT, "nope.mp4") is None)
    if hasattr(os, "symlink"):
        other = make_kit("2026-10-15 Linked")
        try:
            os.symlink(KIT / "Talking", other / "Talking")
            check("a Talking folder that is a link out of the shoot is never listed", TR.list_talks(other) == [] and not TR.talking_ok(other)
                  and TR.state_for_page(other)["folder"] is False)
        except OSError:
            print("SKIP  a linked Talking folder (this computer won't make a link)")
    KEY1 = talks[0]["key"]
    FOOT_KEY = foot_before[0]["key"]

    # ------------------------------------------------------------ the words arrive (stage B does this for real)
    TR.put_words(KIT, "my talk.mp4", KEY1, WORDS + [{"w": " ", "start": 9, "end": 9.1}], {"dur": 3.0, "w": 640, "h": 360}, {"how": "pretend", "ondevice": True})
    r0 = rec()
    wf = json.loads(WORDSF.read_text(encoding="utf-8"))
    check("put_words: the record is ready on that video and holds no words itself",
          r0["video"] == "my talk.mp4" and r0["status"] == "ready" and r0["rev"] == 1 and "words" not in r0 and "sentences" not in r0 and r0["captions"] is True, r0)
    check("... the words, sentences and facts are in a file of their own, cleaned (an empty word left out)",
          len(wf["videos"]["my talk.mp4"]["words"]) == NW and wf["videos"]["my talk.mp4"]["sentences"] == [[0, E1], [E1 + 1, NW - 1]]
          and wf["videos"]["my talk.mp4"]["key"] == KEY1 and wf["videos"]["my talk.mp4"]["info"]["dur"] == 3.0, wf["videos"]["my talk.mp4"]["sentences"])
    full = TR.load(KIT)
    check("load: the record with its words joined on, in her shape",
          len(full["words"]) == NW and full["sentences"] == [[0, E1], [E1 + 1, NW - 1]] and full["video_key"] == KEY1 and full["info"]["dur"] == 3.0)
    words_bytes = WORDSF.read_bytes()
    TR.put_words(KIT, "my talk.mp4", KEY1, WORDS, {"dur": 3.0, "w": 640, "h": 360}, {"how": "pretend", "ondevice": True})
    check("put_words twice with the same words: nothing is written the second time", WORDSF.read_bytes() == words_bytes and rec() == r0)

    st = TR.state_for_page(KIT)
    check("state: her keys, and ours beside them",
          {"ok", "folder", "videos", "working", "rec", "pieces", "zooms", "shots", "captions"} <= set(st)
          and {"rev", "stamp", "short", "coming", "video_state"} <= set(st), sorted(st))
    check("state: rec holds what her page reads (made, v27: whether this reel was made, never which project), and nothing else of ours",
          set(st["rec"]) == {"words", "sentences", "cut", "video", "status", "step", "problem", "info", "transcribed", "claude_cut",
                             "photo_mode", "cap_size", "captions", "updated", "kept_for", "made"} and st["rec"]["made"] is False
          and set(st["rec"]["words"][0]) == {"w", "start", "end"} and st["rec"]["info"] == {"dur": 3.0}, sorted(st["rec"]))
    check("state: videos are {key, name}; the record's video is its name; it is the one the script was made from",
          st["videos"] == [{"key": KEY1, "name": "my talk.mp4"}, {"key": talks[1]["key"], "name": "second take.MOV"}]
          and st["rec"]["video"] == "my talk.mp4" and st["video_state"] == "here" and st["folder"] is True, st["videos"])
    check("state: each piece carries words, sentence, zoom, speed, from, to, at, dur",
          st["pieces"] and all(set(p) == {"words", "sentence", "zoom", "speed", "from", "to", "at", "dur"} for p in st["pieces"]))
    check("state: one caption a word", len(st["captions"]) == NW and st["captions"][0]["text"] == "OK")
    check("state: no path anywhere in it", str(TMP) not in json.dumps(st) and "/Talking" not in json.dumps(st) and "\\\\" not in json.dumps(st))
    light = TR.state_for_page(KIT, rev=st["rev"])
    check("state with the counter the page already has: only {ok, rev, mark, working, step}",
          light == {"ok": True, "rev": st["rev"], "mark": st["mark"], "working": False, "step": ""}, light)
    check("state with an older counter: the whole state", "rec" in TR.state_for_page(KIT, rev=st["rev"] - 1))

    # ------------------------------------------------------------ a save from the page, field by field
    PAGE = "pageAAAA1"

    def sv(saved, base=None, page=PAGE, **more):
        body = {"kit": SHOOT, "base": TR.state_for_page(KIT, rev=-1)["rev"] if base is None else base, "page": page, "saved": saved}
        body.update(more)
        return TR.save_from_page(KIT, body)

    def good(name, saved, field, want):
        code, ans = sv(saved)
        got = rec().get(field)
        check("save: " + name, code == 200 and ans.get("ok") and got == want, (code, got))

    def refused(name, saved, **more):
        before = REC.read_bytes()
        code, ans = sv(saved, **more)
        check("save refused: " + name, code == 400 and ans == {"ok": False, "words": TR.NOT_UNDERSTOOD} and REC.read_bytes() == before, (code, ans))

    L = NW - 1
    good("a cut on the first word", {"cut": [[0, 0]]}, "cut", [[0, 0]])
    good("a cut to the last word", {"cut": [[0, L]]}, "cut", [[0, L]])
    good("2000 cuts", {"cut": [[1, 1]] * 2000}, "cut", [[1, 1]] * 2000)
    refused("2001 cuts", {"cut": [[1, 1]] * 2001})
    refused("a cut past the last word", {"cut": [[0, NW]]})
    refused("a cut that runs backwards", {"cut": [[2, 1]]})
    refused("a cut before the first word", {"cut": [[-1, 0]]})
    refused("a cut whose number is text", {"cut": [[0, "1"]]})
    refused("a cut whose number is true", {"cut": [[True, 1]]})
    refused("a cut of three numbers", {"cut": [[0, 1, 2]]})
    refused("a cut that isn't a list", {"cut": "0-1"})
    good("cuts put back to two", {"cut": [[0, 2], [8, 8]]}, "cut", [[0, 2], [8, 8]])

    good("splits: doubles dropped, in order", {"splits": [9, 1, L, 9]}, "splits", [1, 9, L])
    refused("a split at the first word (nothing before it)", {"splits": [0]})
    refused("a split past the last word", {"splits": [NW]})
    refused("a split that is half a word", {"splits": [1.5]})
    good("splits emptied", {"splits": []}, "splits", [])

    good("speeds: 1.25, 1.5 and 2; a speed of 1 is dropped", {"speeds": [{"a": 0, "b": 1, "v": 1.25}, {"a": 2, "b": 3, "v": 1.5},
                                                                      {"a": 4, "b": 5, "v": 2}, {"a": 6, "b": 6, "v": 1}]},
         "speeds", [{"a": 0, "b": 1, "v": 1.25}, {"a": 2, "b": 3, "v": 1.5}, {"a": 4, "b": 5, "v": 2.0}])
    refused("a speed of 3", {"speeds": [{"a": 0, "b": 1, "v": 3}]})
    refused("a speed that is text", {"speeds": [{"a": 0, "b": 1, "v": "2"}]})
    refused("a speed with a field too many", {"speeds": [{"a": 0, "b": 1, "v": 2, "x": 1}]})
    refused("a speed past the last word", {"speeds": [{"a": 0, "b": NW, "v": 2}]})
    refused("501 speeds", {"speeds": [{"a": 0, "b": 0, "v": 2}] * 501})
    good("speeds emptied", {"speeds": []}, "speeds", [])

    TR.change(KIT, lambda r: r.update(moves={"0": "punch"}, photos={"0": {"n": 3, "spot": "full"}}))
    check("(v23's older fields are read while the newer are empty)", TR.state_for_page(KIT)["zooms"] == [{"a": 0, "b": E1, "kind": "punch"}]
          and TR.state_for_page(KIT)["shots"][0]["ns"] == [3])
    good("zooms: a punch in and a slow zoom", {"zooms": [{"a": 0, "b": 1, "kind": "punch"}, {"a": 3, "b": L, "kind": "zoom"}]},
         "zooms", [{"a": 0, "b": 1, "kind": "punch"}, {"a": 3, "b": L, "kind": "zoom"}])
    check("... and saving zooms empties v23's moves", rec()["moves"] == {} and rec()["photos"] != {})
    refused("a zoom of a kind that isn't one", {"zooms": [{"a": 0, "b": 1, "kind": "spin"}]})
    refused("a zoom with no kind", {"zooms": [{"a": 0, "b": 1}]})
    refused("a zoom that runs backwards", {"zooms": [{"a": 3, "b": 1, "kind": "zoom"}]})
    refused("501 zooms", {"zooms": [{"a": 0, "b": 0, "kind": "zoom"}] * 501})
    # how much and how fast (Dustin, Nov 13): two fields a zoom may carry, written only when they were chosen
    plain = [{"a": 0, "b": 1, "kind": "punch"}, {"a": 3, "b": L, "kind": "zoom"}]
    check("a zoom nobody set is stored exactly as it always was: a, b and kind, in that order, and no word of an amount or a pace in the file",
          json.dumps(rec()["zooms"]) == json.dumps(plain) and b"amount" not in REC.read_bytes() and b"pace" not in REC.read_bytes(), rec()["zooms"])
    good("zooms: how much and how fast, each kind its own", {"zooms": [{"a": 0, "b": 1, "kind": "punch", "amount": "strong", "pace": "push"},
                                                                       {"a": 3, "b": L, "kind": "zoom", "pace": "quick", "amount": "subtle"}]},
         "zooms", [{"a": 0, "b": 1, "kind": "punch", "amount": "strong", "pace": "push"}, {"a": 3, "b": L, "kind": "zoom", "amount": "subtle", "pace": "quick"}])
    check("... the page is told them with its zooms, and they are still there in the engine's reading",
          TR.state_for_page(KIT)["zooms"] == rec()["zooms"] and TR._engine().zooms(rec()) == rec()["zooms"])
    before_rev = rec()["rev"]
    good("zooms: what a zoom has by itself (Medium; Instant; Whole clip) is never written, so choosing it takes the field away",
         {"zooms": [{"a": 0, "b": 1, "kind": "punch", "amount": "medium", "pace": "instant"}, {"a": 3, "b": L, "kind": "zoom", "amount": "medium", "pace": "whole"}]},
         "zooms", plain)
    check("... and the record's zooms are byte for byte what a save with no such fields leaves", json.dumps(rec()["zooms"]) == json.dumps(plain)
          and rec()["rev"] == before_rev + 1)
    code, ans = sv({"zooms": [{"a": 0, "b": 1, "kind": "punch", "amount": "medium"}, {"a": 3, "b": L, "kind": "zoom", "pace": "whole"}]})
    check("... saving the same thing again, spelled with its defaults, is nothing to write (no new step)", code == 200 and rec()["rev"] == before_rev + 1, (code, rec()["rev"]))
    refused("a zoom with an amount that isn't one", {"zooms": [{"a": 0, "b": 1, "kind": "zoom", "amount": "huge"}]})
    refused("a zoom whose amount is a number", {"zooms": [{"a": 0, "b": 1, "kind": "zoom", "amount": 1.3}]})
    refused("a zoom whose amount is nothing", {"zooms": [{"a": 0, "b": 1, "kind": "zoom", "amount": None}]})
    refused("a zoom with a pace that isn't one", {"zooms": [{"a": 0, "b": 1, "kind": "zoom", "pace": "slowly"}]})
    refused("a slow zoom with a punch in's pace (Quick push)", {"zooms": [{"a": 0, "b": 1, "kind": "zoom", "pace": "push"}]})
    refused("a slow zoom with a punch in's pace (Instant)", {"zooms": [{"a": 0, "b": 1, "kind": "zoom", "pace": "instant"}]})
    refused("a punch in with a slow zoom's pace (Whole clip)", {"zooms": [{"a": 0, "b": 1, "kind": "punch", "pace": "whole"}]})
    refused("a punch in with a slow zoom's pace (Quick)", {"zooms": [{"a": 0, "b": 1, "kind": "punch", "pace": "quick"}]})
    refused("a zoom whose pace is a list", {"zooms": [{"a": 0, "b": 1, "kind": "punch", "pace": ["push"]}]})
    refused("a zoom with a field too many", {"zooms": [{"a": 0, "b": 1, "kind": "punch", "speed": 2}]})
    good("zooms emptied", {"zooms": []}, "zooms", [])

    def shot(a, b, **kw):
        d = {"a": a, "b": b, "ns": [1], "v": None, "from": 0, "spot": "full", "pos": None, "me": None}
        d.update(kw)
        return d

    def S(a, b, ns, spot, v=None, frm=0.0, pos=None, me=None):
        return {"a": a, "b": b, "ns": ns, "v": v, "from": frm, "spot": spot, "pos": pos, "me": me}

    good("shots: her four spots", {"shots": [shot(0, 0, spot="full"), shot(1, 1, spot="pip"), shot(2, 2, spot="center"), shot(3, 3, spot="corner")]},
         "shots", [S(0, 0, [1], "full"), S(1, 1, [1], "pip"), S(2, 2, [1], "center"), S(3, 3, [1], "corner")])
    check("... and saving shots empties v23's photos", rec()["photos"] == {})
    refused("Behind you (read from an old record, never saved)", {"shots": [shot(0, 0, spot="behind")]})
    refused("Across the top (the same)", {"shots": [shot(0, 0, spot="top")]})
    refused("a spot that isn't one", {"shots": [shot(0, 0, spot=["full"])]})
    refused("a photo that isn't on this shoot's numbered list", {"shots": [shot(0, 0, ns=[1, 13])]})
    refused("a photo number that is text", {"shots": [shot(0, 0, ns=["1"])]})
    refused("a stretch with no photo and no video", {"shots": [shot(0, 0, ns=[])]})
    refused("a stretch past the last word", {"shots": [shot(0, NW)]})
    refused("a stretch that runs backwards", {"shots": [shot(4, 3)]})
    refused("a stretch with a field too many", {"shots": [shot(0, 0, path="/etc")]})
    refused("a start point before the video's start", {"shots": [shot(0, 0, v=FOOT_KEY, **{"from": -1})]})
    refused("a video that isn't a key (a file name is never taken from the page)", {"shots": [shot(0, 0, v="clip one.mp4")]})
    refused("a video that is a path", {"shots": [shot(0, 0, v="../../x.mp4")]})
    refused("a photo box with a part missing", {"shots": [shot(0, 0, pos={"x": 0.5, "y": 0.5})]})
    refused("a photo box that is text", {"shots": [shot(0, 0, me="corner")]})
    refused("501 stretches", {"shots": [shot(0, 0)] * 501})
    good("shots: 31 photos chosen for one stretch keeps the first 30, without a word (hers)",
         {"shots": [shot(0, 3, ns=[(i % 12) + 1 for i in range(31)])]}, "shots", [S(0, 3, [(i % 12) + 1 for i in range(30)], "full")])
    good("shots: a Footage video by its key is kept by its name, with its start, and no photos",
         {"shots": [shot(0, 3, ns=[2], v=FOOT_KEY, spot="pip", **{"from": 1.23456})]}, "shots", [S(0, 3, [], "pip", v="clip one.mp4", frm=1.235)])
    stv = TR.state_for_page(KIT)["shots"][0]["v"]
    check("... and the page is given it back as {key, name}, with the video's own shape (a wide video is drawn wide from the first frame, as hers: stage G)",
          stv == {"key": FOOT_KEY, "name": "clip one.mp4", "w": 320, "h": 180}, stv)
    b4 = REC.read_bytes()
    code, ans = sv({"shots": [shot(0, 3, ns=[], v=stv, spot="pip", **{"from": 1.235})]})
    check("... and that very thing sent back as it came is taken (nothing to write), the shape never kept in the record",
          code == 200 and REC.read_bytes() == b4 and "\"w\"" not in json.dumps(rec()["shots"]), (code, ans))
    good("shots: boxes are held to hers (x, y -0.5 to 1.5; w 0.08 to 2), to 4 places",
         {"shots": [shot(0, 0, spot="center", pos={"x": -9, "y": 9, "w": 0.01}), shot(1, 1, spot="pip", me={"x": 0.123456, "y": 0.5, "w": 5})]},
         "shots", [S(0, 0, [1], "center", pos={"x": -0.5, "y": 1.5, "w": 0.08}), S(1, 1, [1], "pip", me={"x": 0.1235, "y": 0.5, "w": 2.0})])
    # stage G: her page can never send two stretches that share a word (all it saves goes through setRange,
    # which trims around the new one and sorts), so such a set is refused, and a set out of order is kept in order
    good("shots: stretches sent out of order are kept in order of their first word (hers: setRange sorts)",
         {"shots": [shot(6, 9, ns=[2]), shot(0, 5, ns=[3])]}, "shots", [S(0, 5, [3], "full"), S(6, 9, [2], "full")])
    refused("two stretches that share a word (her page can never send them)", {"shots": [shot(0, 5, ns=[3]), shot(4, 9, ns=[2])]})
    refused("... the same, sent the other way round", {"shots": [shot(4, 9, ns=[2]), shot(0, 5, ns=[3])]})
    refused("... and one stretch inside another", {"shots": [shot(3, 9, ns=[2]), shot(5, 6, ns=[3])]})
    good("shots: a stretch whose words are all cut still saves (cutting after placing makes one)",
         {"shots": [shot(0, 2, ns=[3]), shot(8, 8, ns=[2])]}, "shots", [S(0, 2, [3], "full"), S(8, 8, [2], "full")])
    # a record changed by hand can hold an overlap: it is still read (the later stretch has the shared words),
    # and the page can still save from it (never locked out of its own record)
    TR.change(KIT, lambda r: r.update(shots=[S(4, 9, [2], "full"), S(0, 5, [3], "full")]))
    code, ans = sv({"shots": [shot(0, 5, ns=[3]), shot(4, 9, ns=[2], spot="pip")]})
    check("a record that already overlaps (changed by hand): a save from the page is still taken", code == 200 and rec()["shots"][1]["spot"] == "pip", (code, ans))
    TR.change(KIT, lambda r: r.update(shots=[S(4, 9, [2], "full"), S(0, 5, [3], "full")]))
    stp = TR.state_for_page(KIT)
    # cut is [[0, 2], [8, 8]]: word 3 is the first stretch's alone; 4 to 7 are shared, so they are the later one's
    check("... read in order of first word, the later one having the words they share",
          [x["a"] for x in stp["shots"]] == [0, 4] and [p["words"] for p in stp["pieces"]][:3] == [[3], [4, 5, 6, 7], [9]], [p["words"] for p in stp["pieces"]])
    code, ans = sv({"shots": [shot(0, 1, ns=[4]), shot(2, 3, v="0123456789ab"), shot(5, 6, ns=[5], spot="corner")]})
    check("shots: an Undo that names a Footage video since gone leaves that one stretch out and saves the rest (hers)",
          code == 200 and rec()["shots"] == [S(0, 1, [4], "full"), S(5, 6, [5], "corner")], (code, rec()["shots"]))

    good("cap_pos held to 0.02 to 0.98", {"cap_pos": {"x": 0, "y": 1}}, "cap_pos", {"x": 0.02, "y": 0.98})
    good("cap_pos put back (null)", {"cap_pos": None}, "cap_pos", None)
    refused("a cap_pos that is text", {"cap_pos": {"x": "a", "y": 0.5}})
    refused("a cap_pos with a part too many", {"cap_pos": {"x": 0.5, "y": 0.5, "w": 1}})
    good("cap_size held to 3", {"cap_size": 5}, "cap_size", 3.0)
    good("cap_size held to 0.4", {"cap_size": 0.1}, "cap_size", 0.4)
    good("cap_size to 2 places", {"cap_size": 1.2345}, "cap_size", 1.23)
    good("cap_size 0 reads as 1", {"cap_size": 0}, "cap_size", 1.0)
    sv({"cap_size": 2})
    good("cap_size null reads as 1", {"cap_size": None}, "cap_size", 1.0)
    refused("a cap_size that is text", {"cap_size": "big"})
    refused("a cap_size that is true", {"cap_size": True})
    good("captions off", {"captions": False}, "captions", False)
    good("captions on", {"captions": True}, "captions", True)
    refused("captions as a number", {"captions": 1})
    good("who places the photos: me", {"photo_mode": "me"}, "photo_mode", "me")
    good("... the Assistant", {"photo_mode": "assistant"}, "photo_mode", "assistant")
    good("... not chosen", {"photo_mode": ""}, "photo_mode", "")
    refused("... anyone else", {"photo_mode": "claude"})
    for k, v in (("photos", {}), ("moves", {}), ("words", []), ("video", "x.mp4"), ("status", "ready"), ("claude_cut", []), ("rev", 9), ("earlier", {})):
        refused(f"a field her page never sends ({k})", {k: v})
    refused("one good field beside one bad one: nothing is saved", {"captions": False, "cut": [[0, NW]]})
    refused("nothing to save", {})
    refused("a body with a key too many", {"captions": False}, extra=1)
    refused("a page name that isn't one", {"captions": False}, page="../x")
    refused("a counter that isn't a number", {"captions": False}, base="1")
    check("a save's answer is the whole new state", sv({"captions": True})[1].get("rec", {}).get("captions") is True)

    # ------------------------------------------------------------ the counter, the version before, running twice
    before, rev = REC.read_bytes(), rec()["rev"]
    code, ans = sv({"captions": True})
    check("saving exactly what is stored writes nothing", code == 200 and REC.read_bytes() == before and ans["rev"] == rev)
    code, ans = sv({"captions": False})
    check("a save keeps the version before beside the record", code == 200 and PREV.read_bytes() == before and rec()["rev"] == rev + 1)
    check("... and says which page saved it, from which counter", rec()["from"] == {"page": PAGE, "base": rev})
    code, ans = sv({"captions": False, "cap_size": 1.5}, base=rev)
    check("the same page sending again from the same counter (its answer never arrived) is taken", code == 200 and rec()["cap_size"] == 1.5)
    sv({"cut": [[0, 2]], "shots": [], "captions": True})

    # the chat cuts; a page that hasn't seen it can't wipe it
    stale = rec()["rev"]
    r = run("cut", SHORT, "--file", jfile({"cut": [[0, 2]], "why": ["the warm-up"]}))
    check("(a cut of theirs is in the way: the assistant's cut stops without --replace)", r.returncode == 2 and rec()["rev"] == stale, r.stdout)
    r = run("cut", SHORT, "--file", jfile({"cut": [[0, 2], [8, 8]], "why": ["the warm-up", "a word said twice"]}), "--replace")
    check("cut: her line, with the reel's own length",
          r.returncode == 0 and re.fullmatch(r"Saved: 2 cuts\. The reel is now \d+\.\d seconds of talking\. The page shows it in a few seconds\.", r.stdout.strip()), r.stdout + r.stderr)
    want_secs = eng.reel_seconds(eng.pieces(TR.load(KIT)))
    check("... the seconds are the reel's (each piece's time on the reel, added up)", f"{want_secs:.1f} seconds" in r.stdout, (want_secs, r.stdout))
    after_chat = rec()
    check("... it saved cut, claude_cut and claude_why, and moved the counter on", after_chat["cut"] == [[0, 2], [8, 8]] and after_chat["claude_cut"] == [[0, 2], [8, 8]]
          and after_chat["claude_why"] == ["the warm-up", "a word said twice"] and after_chat["rev"] > stale and "from" not in after_chat)
    code, ans = sv({"cut": []}, base=stale, page="pageBBBB2")
    check("a save from a page that hasn't seen the chat's cut is refused, and given the newest",
          code == 409 and ans["ok"] is False and ans["why"] == "newer" and ans["words"] == TR.NEWER and ans["state"]["rec"]["cut"] == [[0, 2], [8, 8]]
          and rec() == after_chat, (code, ans.get("why")))
    code, ans = sv({"captions": False}, base=stale, page="pageBBBB2")
    check("... even a save of some other field", code == 409 and rec() == after_chat)
    code, ans = sv({"captions": False})
    check("once the page has seen it, its save is taken, and the chat's cut stands", code == 200 and rec()["cut"] == [[0, 2], [8, 8]] and rec()["captions"] is False)
    check("state: claude_cut is the assistant's cut", TR.state_for_page(KIT)["rec"]["claude_cut"] == [[0, 2], [8, 8]])

    # ------------------------------------------------------------ the chat's commands
    r = run("show", SHORT)
    out = r.stdout
    check("show: her rules first, every time", r.returncode == 0 and out.startswith(eng.RULES + "\n"), out[:80])
    check("show: her header line", f"\n{SHOOT}: my talk.mp4, {NW} words. Each word is number:word (seconds).\n" in out)
    lines = [ln for ln in out.splitlines() if ln.startswith("[")]
    check("show: every word numbered, by sentence, each sentence with the second it starts at",
          lines == ["[0] 0.0s  " + " ".join(f"{i}:{SAID[i]}" for i in range(0, E1 + 1)), "[1] 4.0s  " + " ".join(f"{i}:{SAID[i]}" for i in range(E1 + 1, NW))], lines)
    check("show: her Already cut line", out.rstrip().endswith("Already cut (theirs or yours): 0-2, 8-8"), out[-80:])
    r2 = run("show", "hannah zoë")
    check("show: a few words of the name do as well", r2.stdout == out)

    before = REC.read_bytes()
    r = run("cut", SHORT, "--file", jfile({"cut": [[0, 2], [8, 8]], "why": ["the warm-up", "a word said twice"]}))
    check("cut: its own cut done again needs no --replace, and changes nothing the second time", r.returncode == 0 and REC.read_bytes() == before, r.stdout)
    r = run("cut", SHORT, "--file", jfile({"cut": [[8, 8], [0, 1], [2, 2], [1, 2]]}, bom=True))
    check("cut: touching and overlapping cuts are made one, in order (a file with a byte-order mark reads too)",
          r.returncode == 0 and rec()["cut"] == [[0, 2], [8, 8]] and "Saved: 2 cuts." in r.stdout, (r.stdout, rec()["cut"]))
    before = REC.read_bytes()
    r = run("cut", SHORT, "--file", jfile({"cut": [[0, NW]]}))
    check("cut: her STOP for a range that isn't word numbers", r.returncode == 2 and r.stdout.strip() == f"STOP: 0-{NW} isn't a range of word numbers (0 to {NW - 1})", r.stdout)
    r = run("cut", SHORT, "--file", jfile({"cut": [[3, 1]]}))
    check("cut: ... or runs backwards", r.returncode == 2 and "3-1 isn't a range of word numbers" in r.stdout)
    r = run("cut", SHORT, "--file", jfile({"cut": [[1]]}))
    check("cut: a cut that isn't two numbers stops in plain words", r.returncode == 2 and r.stdout.startswith("STOP: each cut is two word numbers"), r.stdout)
    r = run("cut", SHORT, "--file", jfile("{not json"))
    check("cut: a file that isn't JSON stops in plain words", r.returncode == 2 and r.stdout.startswith("STOP: the file isn't JSON"), r.stdout)
    r = run("cut", SHORT, "--file", str(TMP / "nope.json"))
    check("cut: a file that isn't there stops in plain words", r.returncode == 2 and r.stdout.startswith("STOP: the file can't be read"), r.stdout)
    check("... and none of those changed the record", REC.read_bytes() == before)
    r = run("cut", SHORT, "--file", jfile({"cut": [[0, 0]], "why": ["x" * 300] + ["r"] * 30}))
    check("cut: up to 20 reasons, 120 characters each", r.returncode == 0 and len(rec()["claude_why"]) == 20 and len(rec()["claude_why"][0]) == 120)

    # they cut on the page; the assistant may not replace theirs without asking
    sv({"cut": [[0, 0], [5, 6]], "zooms": [{"a": 9, "b": 10, "kind": "punch"}], "splits": [4], "speeds": [{"a": 11, "b": 12, "v": 1.5}],
        "shots": [shot(12, 13, ns=[7], spot="corner")]})
    before = REC.read_bytes()
    r = run("cut", SHORT, "--file", jfile({"cut": [[0, 2]]}))
    check("cut: their own cuts are never replaced without asking: her STOP line",
          r.returncode == 2 and r.stdout.strip() == "STOP: they've already made their own cuts on the page. Ask before replacing them (then run again with --replace)"
          and REC.read_bytes() == before, r.stdout)
    r = run("cut", SHORT, "--file", jfile({"cut": [[0, 2]], "why": ["the warm-up"]}), "--replace")
    rp = rec().get("replaced") or []
    check("cut --replace: theirs is replaced, and what was there is kept in the record",
          r.returncode == 0 and rec()["cut"] == [[0, 2]] and len(rp) == 2 and rp[-1]["cut"] == [[0, 0], [5, 6]] and rp[-1]["splits"] == [4]
          and rp[-1]["zooms"] == [{"a": 9, "b": 10, "kind": "punch"}] and rp[-1]["speeds"] == [{"a": 11, "b": 12, "v": 1.5}]
          and rp[-1]["shots"][0]["ns"] == [7] and rp[-1]["why"] == "cut --replace" and rp[-1]["when"] and rp[-1]["video"] == "my talk.mp4", rp)
    before = REC.read_bytes()
    r = run("cut", SHORT, "--file", jfile({"cut": [[0, 2]], "why": ["the warm-up"]}), "--replace")
    check("cut --replace run twice: nothing changes the second time", r.returncode == 0 and REC.read_bytes() == before)
    # every cut of the assistant's brought back on the page: that empty list is THEIR work (stage E's review)
    sv({"cut": []})
    before = REC.read_bytes()
    st_out = run("status", SHORT).stdout
    r = run("cut", SHORT, "--file", jfile({"cut": [[0, 2]], "why": ["the warm-up"]}))
    check("cut: after they bring back everything the assistant cut, a fresh cut stops without --replace, as status says",
          r.returncode == 2 and r.stdout.strip() == "STOP: " + TR.THEIR_CUTS and REC.read_bytes() == before
          and "their own cuts (ask before replacing them)" in st_out, (r.stdout, st_out))
    r = run("cut", SHORT, "--file", jfile({"cut": [[0, 2]], "why": ["the warm-up"]}), "--replace")
    check("... and with --replace it is saved", r.returncode == 0 and rec()["cut"] == [[0, 2]] and rec()["claude_cut"] == [[0, 2]], r.stdout)
    r = run("cut", SHORT, "--file", jfile({"cut": []}))
    check("an empty cut is still a cut: claude_cut is a list, even an empty one (hers)",
          r.returncode == 0 and rec()["claude_cut"] == [] and rec()["cut"] == [] and TR.state_for_page(KIT)["rec"]["claude_cut"] == []
          and "Saved: 0 cuts." in r.stdout, r.stdout)
    run("cut", SHORT, "--file", jfile({"cut": [[0, 2], [8, 8]], "why": ["the warm-up", "a word said twice"]}))

    # photos and place
    r = run("photos", SHORT)
    out = r.stdout
    check("photos: her rules first, every time", r.returncode == 0 and out.startswith(eng.PHOTO_RULES + "\n"), out[:80])
    check("photos: her header line", f"\n{SHOOT}: the kept words, by sentence. Each word is number:word.\n" in out)
    lines = [ln for ln in out.splitlines() if ln.startswith("[")]
    check("photos: the KEPT words by sentence (cut words left out)",
          lines == ["[0] " + " ".join(f"{i}:{SAID[i]}" for i in range(3, E1 + 1)), "[1] " + " ".join(f"{i}:{SAID[i]}" for i in range(E1 + 2, NW))], lines)
    check("photos: where the photos are, and the sheet command (the page's numbers)",
          f"\nTheir photos: {KIT / 'Photos'}\n" in out and "See them on the reel maker's contact sheet (the numbers match the page):\n" in out
          and "kit.py" in out and " sheet " in out and SHOOT in out.split("contact sheet")[1], out[-400:])
    check("photos: her line when photos are already placed", out.rstrip().endswith("They already have photos placed: ask before replacing them (then place with --replace)."), out[-120:])
    run("cut", SHORT, "--file", jfile({"cut": [[0, E1]]}), "--replace")
    lines = [ln for ln in run("photos", SHORT).stdout.splitlines() if ln.startswith("[")]
    check("photos: a sentence wholly cut is left out", len(lines) == 1 and lines[0].startswith("[1] 8:And"), lines)
    run("cut", SHORT, "--file", jfile({"cut": [[0, 2], [8, 8]]}))

    before = REC.read_bytes()
    r = run("place", SHORT, "--file", jfile({"shots": [{"a": 3, "b": 6, "ns": [4], "spot": "full"}]}))
    check("place: refused whenever any stretch exists: her STOP line",
          r.returncode == 2 and r.stdout.strip() == "STOP: they already have photos placed. Ask before replacing them (then run again with --replace)"
          and REC.read_bytes() == before, r.stdout)
    PL = {"shots": [{"a": 9, "b": 12, "ns": [1, 2, 3], "spot": "pip"}, {"a": 3, "b": 6, "ns": [4], "spot": "full"}, {"a": 13, "b": 15, "ns": [5], "spot": "center"}]}
    r = run("place", SHORT, "--file", jfile(PL), "--replace")
    check("place --replace: her line", r.returncode == 0 and r.stdout.strip() == "Saved: 3 photo stretches, 5 photos. The page shows them in a few seconds.", r.stdout + r.stderr)
    now = rec()
    check("... stretches in order, pos and me empty, claude_shots set, v23's photos emptied",
          now["shots"] == [S(3, 6, [4], "full"), S(9, 12, [1, 2, 3], "pip"), S(13, 15, [5], "center")] and now["claude_shots"] is True and now["photos"] == {}, now["shots"])
    check("... and the stretch of theirs it replaced is kept", len(now["replaced"]) == 4 and now["replaced"][-1]["why"] == "place --replace" and now["replaced"][-1]["shots"][0]["ns"] == [7])
    before = REC.read_bytes()
    r = run("place", SHORT, "--file", jfile(PL), "--replace")
    check("place --replace run twice: nothing changes the second time", r.returncode == 0 and REC.read_bytes() == before)

    r = run("status", SHORT)
    check("status straight after a place: the photo stretches are '(placed by you)'", "Photo stretches: 3 (placed by you);" in r.stdout, r.stdout)
    r = run("place", SHORT, "--file", jfile(PL))
    check("place: the assistant's own set sent again WITHOUT --replace (a run cut off or doubted) saves, changes nothing, asks nothing",
          r.returncode == 0 and r.stdout.strip() == "Saved: 3 photo stretches, 5 photos. The page shows them in a few seconds."
          and REC.read_bytes() == before, r.stdout)
    r = run("place", SHORT, "--file", jfile({"shots": PL["shots"][:2]}))
    check("... a different set still stops without --replace", r.returncode == 2 and r.stdout.strip() == "STOP: " + TR.THEIR_PHOTOS and REC.read_bytes() == before, r.stdout)
    r = run("place", SHORT, "--file", jfile({"shots": [{"a": 3, "b": 6, "ns": [999], "spot": "full"}]}))
    check("... and a file with a mistake in it, photos already there: 'already placed' is still said first",
          r.returncode == 2 and r.stdout.strip() == "STOP: " + TR.THEIR_PHOTOS and REC.read_bytes() == before, r.stdout)

    def place_stop(name, shots, has):
        b4 = REC.read_bytes()
        r = run("place", SHORT, "--file", jfile({"shots": shots}), "--replace")
        check("place refused: " + name, r.returncode == 2 and r.stdout.startswith("STOP: ") and has in r.stdout and REC.read_bytes() == b4, r.stdout)

    place_stop("stretches that overlap (her line)", [{"a": 3, "b": 6, "ns": [4], "spot": "full"}, {"a": 6, "b": 7, "ns": [5], "spot": "full"}],
               "6-7 isn't a range of word numbers that follows the one before it")
    place_stop("a stretch past the last word (her line)", [{"a": 3, "b": NW, "ns": [4], "spot": "full"}], f"3-{NW} isn't a range of word numbers that follows the one before it")
    place_stop("a stretch with no photos (her line)", [{"a": 3, "b": 6, "ns": [], "spot": "full"}], "3-6: each stretch needs photo numbers and a spot (pip, full, center, corner)")
    place_stop("a spot that isn't one of the four (her line)", [{"a": 3, "b": 6, "ns": [4], "spot": "behind"}], "3-6: each stretch needs photo numbers and a spot (pip, full, center, corner)")
    place_stop("a video (place takes photos only)", [{"a": 3, "b": 6, "ns": [4], "v": "clip one.mp4", "spot": "full"}], "3-6: place takes photos only, never a video")
    place_stop("a photo number that doesn't exist (ours)", [{"a": 3, "b": 6, "ns": [4, 99], "spot": "full"}], "3-6: photo 99 isn't one of this shoot's photos")
    place_stop("a stretch with no kept word (ours)", [{"a": 0, "b": 2, "ns": [4], "spot": "full"}], "0-2: every word there is cut")
    place_stop("a stretch with no word numbers", [{"ns": [4], "spot": "full"}], "each stretch needs a first word (a) and a last word (b)")
    r = run("place", SHORT, "--file", jfile({"shots": [{"a": 3, "b": 6, "ns": [(i % 12) + 1 for i in range(31)], "spot": "full"}]}), "--replace")
    check("place: more than 30 photos in one stretch keeps the first 30 (hers)", r.returncode == 0 and len(rec()["shots"][0]["ns"]) == 30 and "1 photo stretches, 30 photos" in r.stdout, r.stdout)
    run("place", SHORT, "--file", jfile(PL), "--replace")
    sv({"zooms": [], "splits": [], "speeds": []})
    stp = TR.state_for_page(KIT)
    check("state after a place: each stretch, and pieces that break at its edges",
          [(x["a"], x["b"], x["ns"], x["spot"], x["v"]) for x in stp["shots"]] == [(3, 6, [4], "full", None), (9, 12, [1, 2, 3], "pip", None), (13, 15, [5], "center", None)]
          and [p["words"] for p in stp["pieces"]] == [[3, 4, 5, 6], [7], [9, 10, 11, 12], [13, 14, 15], [16, 17]], [p["words"] for p in stp["pieces"]])

    # what a --replace replaced is still there after ten page saves
    kept_replaced = rec()["replaced"]
    for i in range(10):
        code, _ = sv({"cap_size": 1 + i / 10, "captions": i % 2 == 0, "shots": [shot(3, 6, ns=[i + 1])], "cut": [[0, 2], [8, 8 + i % 2]]})
        if code != 200:
            check(f"(page save {i} was taken)", False, code)
    check("what --replace replaced is still in the record after ten page saves", rec()["replaced"] == kept_replaced and len(kept_replaced) >= 3, len(rec()["replaced"]))
    TR.change(KIT, lambda r: [TR.keep_replaced(r, f"round {i}") for i in range(20)] and None)
    check("... and only the last 12 are kept", len(rec()["replaced"]) == 12 and rec()["replaced"][-1]["why"] == "round 19")

    r = run("status", SHORT)
    check("status after the page changed the photos the assistant placed: no longer '(placed by you)'; it says to ask before replacing them (stage G)",
          rec().get("claude_shots") is True and "(placed by you)" not in r.stdout
          and "Photo stretches: 1 (changed on the page since you placed them: ask before replacing them);" in r.stdout, r.stdout)
    TR.change(KIT, lambda r_: r_.pop("claude_placed", None) and None)
    r = run("status", SHORT)
    check("... and an older record (the flag, but not which set was placed) makes neither claim", "Photo stretches: 1;" in r.stdout, r.stdout)
    r = run("status", SHORT)
    check("status: where the reel stands, in a few plain lines",
          r.returncode == 0 and "my talk.mp4" in r.stdout and f"{NW} words" in r.stdout and "Photo stretches: 1" in r.stdout and "Talking folder: 2 videos" in r.stdout, r.stdout)
    r = run("show", "no such shoot at all")
    check("a shoot that isn't there stops in plain words", r.returncode == 2 and r.stdout.startswith("STOP: nothing in Content matches"), r.stdout)

    # ------------------------------------------------------------ another video, and back
    run("place", SHORT, "--file", jfile(PL), "--replace")
    run("cut", SHORT, "--file", jfile({"cut": [[0, 2], [8, 8]], "why": ["the warm-up"]}), "--replace")
    sv({"zooms": [{"a": 3, "b": 4, "kind": "zoom"}], "splits": [5], "speeds": [{"a": 13, "b": 15, "v": 2}], "cap_size": 1.4, "photo_mode": "assistant"})
    first = rec()
    out = TR.use_video(KIT, "second take.MOV")
    now = rec()
    check("another video: every word-numbered field starts empty for it",
          now["video"] == "second take.MOV" and not any(k in now for k in TR.EDIT_FIELDS) and out["words"] == [] and now["status"] == "", {k: now.get(k) for k in TR.EDIT_FIELDS})
    check("... the first video's whole edit is kept in the record, under its name",
          all(now["earlier"]["my talk.mp4"].get(k) == first.get(k) for k in TR.EDIT_FIELDS if k in first) and now["earlier"]["my talk.mp4"]["cut"] == [[0, 2], [8, 8]])
    check("... captions, their size and who places the photos stay as they were", now["cap_size"] == 1.4 and now["photo_mode"] == "assistant" and now["captions"] == first["captions"])
    stp = TR.state_for_page(KIT)
    check("... the page is told whose edit is kept, and has no script for the new one yet",
          stp["rec"]["kept_for"] == ["my talk.mp4"] and stp["rec"]["words"] == [] and stp["pieces"] == [] and stp["shots"] == [] and stp["rec"]["claude_cut"] is None, stp["rec"]["kept_for"])
    W2 = [{"w": w, "start": i * 0.5, "end": i * 0.5 + 0.25} for i, w in enumerate("A second go at it.".split())]
    TR.put_words(KIT, "second take.MOV", talks[1]["key"], W2, {"dur": 3.0})
    sv({"cut": [[0, 0]]})
    for i in range(3):
        sv({"captions": i % 2 == 0})
    check("... and it is still kept after more saves (hers lost it at the next save)", rec()["earlier"]["my talk.mp4"]["cut"] == [[0, 2], [8, 8]])
    words_bytes = WORDSF.read_bytes()
    back = TR.use_video(KIT, "my talk.mp4")
    now = rec()
    check("back to the first video: its edit is restored, with its script, and no new transcription",
          all(now.get(k) == first.get(k) for k in TR.EDIT_FIELDS) and now["status"] == "ready" and len(back["words"]) == NW
          and WORDSF.read_bytes() == words_bytes and "my talk.mp4" not in now["earlier"], {k: now.get(k) for k in ("cut", "status")})
    check("... and the second video's edit is the one kept now", now["earlier"]["second take.MOV"]["cut"] == [[0, 0]])
    before = REC.read_bytes()
    TR.use_video(KIT, "my talk.mp4")
    check("choosing the video it is already on changes nothing", REC.read_bytes() == before)

    # ------------------------------------------------------------ words made again for the same video
    WORDS3 = [dict(w, start=w["start"] + 0.1, end=w["end"] + 0.1) for w in WORDS[:10]]
    TR.put_words(KIT, "my talk.mp4", KEY1, WORDS3, {"dur": 3.0})
    now = rec()
    check("Edit my video again on the same video: the edit starts afresh, and what was there is kept in replaced",
          not any(k in now for k in TR.EDIT_FIELDS) and now["replaced"][-1]["why"] == "Edit my video again" and now["replaced"][-1]["cut"] == [[0, 2], [8, 8]]
          and len(TR.load(KIT)["words"]) == 10, now.get("replaced", [])[-1:])
    check("... the words file as it was before is kept beside it", (KIT / ".kit" / "talking-words.prev.json").read_bytes() == words_bytes)
    TR.put_words(KIT, "my talk.mp4", KEY1, WORDS, {"dur": 3.0})

    # ------------------------------------------------------------ the video exported again, or gone
    p = KIT / "Talking" / "my talk.mp4"
    os.utime(p, (time.time() - 5000, time.time() - 5000))
    stp = TR.state_for_page(KIT)
    check("the talking video exported again under the same name: the state says so (its script is the old file's)",
          stp["video_state"] == "changed" and stp["videos"][0]["key"] != KEY1 and stp["rec"]["video"] == "my talk.mp4", stp["video_state"])
    check("... show says so to the assistant, status too", "exported again since this script was made" in run("show", SHORT).stdout
          and "exported again since its script was made" in run("status", SHORT).stdout)
    out = run("photos", SHORT).stdout
    check("... and photos ends with the same note (the place steps never run show)",
          out.rstrip().endswith("press Edit my video again on the page before you cut or place.") and "exported again since this script was made" in out, out[-200:])
    TR.put_words(KIT, "my talk.mp4", stp["videos"][0]["key"], WORDS, {"dur": 3.0})
    check("... and once its words are made again it is the one", TR.state_for_page(KIT)["video_state"] == "here")
    aside = TMP / "aside.mp4"
    os.rename(p, aside)
    check("the talking video taken out of the folder: the state says gone", TR.state_for_page(KIT)["video_state"] == "gone")
    os.rename(aside, p)
    sv({"shots": [shot(0, 3, v=FOOT_KEY, spot="pip")]})
    os.rename(KIT / "Footage" / "clip one.mp4", TMP / "clip-aside.mp4")
    v = TR.state_for_page(KIT)["shots"][0]["v"]
    check("a Footage video that has gone: the stretch still shows its name, marked gone, with a key no file can have",
          v["name"] == "clip one.mp4" and v.get("gone") is True and TR.KEY.fullmatch(v["key"]) and v["key"] != FOOT_KEY, v)
    os.rename(TMP / "clip-aside.mp4", KIT / "Footage" / "clip one.mp4")

    # ------------------------------------------------------------ a record that can't be read
    good_bytes = REC.read_bytes()
    REC.write_text('{"video": "my talk.mp4", "cut": [[0, 2', encoding="utf-8")
    damaged = REC.read_bytes()
    stp = TR.state_for_page(KIT)
    check("a damaged record reads as an empty one, and reading leaves it where it is", stp["rec"]["words"] == [] and REC.read_bytes() == damaged)
    code, ans = sv({"captions": False}, base=0)
    aside = [f for f in (KIT / ".kit").iterdir() if f.name.startswith("talking.damaged-")]
    check("the next change sets it aside under a dated name, never writes over it",
          code == 200 and len(aside) == 1 and aside[0].read_bytes() == damaged and re.fullmatch(r"talking\.damaged-\d{8}-\d{6}\.json", aside[0].name)
          and rec()["captions"] is False and rec()["rev"] == 1, [f.name for f in aside])
    REC.write_bytes(good_bytes)

    # ============================================================ the fix round (Nov 12): each of these fails without its fix
    def damaged_files():
        return sorted(f.name for f in (KIT / ".kit").iterdir() if ".damaged-" in f.name)

    # ---- a record that can't be READ just now is not a damaged record
    TR.put_words(KIT, "my talk.mp4", TR.state_for_page(KIT)["videos"][0]["key"], WORDS, {"dur": 3.0})
    sv({"shots": [shot(0, 3, ns=[2], spot="pip")]})
    sv({"cut": [[4, 5]]})
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() != 0:
        good_rec, was_aside = REC.read_bytes(), damaged_files()
        os.chmod(REC, 0)
        try:
            stp = TR.state_for_page(KIT)
            check("a record the computer won't let be read just now: the state says so, never an empty edit",
                  stp.get("ok") is False and stp.get("why") == "trouble" and stp.get("words") == TR.TROUBLE and "rec" not in stp, stp)
            code, ans = sv({"captions": False}, base=0)
            check("... a save from the page is told to try again (503), in plain words", code == 503 and ans["words"] == TR.TROUBLE and ans.get("why") == "trouble", (code, ans))
            r = run("cut", SHORT, "--file", jfile({"cut": [[0, 1]]}))
            check("... the chat's cut stops in plain words, exit 2", r.returncode == 2 and r.stdout.strip() == "STOP: " + TR.TROUBLE and "Traceback" not in r.stderr, (r.stdout, r.stderr[-300:]))
            try:
                TR.use_video(KIT, "second take.MOV")
                raised = False
            except TR.Unreadable:
                raised = True
            check("... choosing another video is refused too", raised)
        finally:
            os.chmod(REC, 0o644)
        check("... and the record is still there under its own name, byte for byte, nothing set aside",
              REC.read_bytes() == good_rec and damaged_files() == was_aside, damaged_files())
        good_words = WORDSF.read_bytes()
        os.chmod(WORDSF, 0)
        try:
            try:
                TR.put_words(KIT, "my talk.mp4", "0" * 12, WORDS[:5], {"dur": 3.0})
                raised = False
            except TR.Unreadable:
                raised = True
            stp = TR.state_for_page(KIT)
        finally:
            os.chmod(WORDSF, 0o644)
        check("the words file the same: nothing is moved or written, and the state does not show a script gone",
              raised and WORDSF.read_bytes() == good_words and REC.read_bytes() == good_rec and damaged_files() == was_aside and stp.get("ok") is False)
    else:
        print("SKIP  a record that can't be read just now (no way to take a file's permission away here)")

    # ---- a write that fails, and a number too large to be a number
    before = REC.read_bytes()
    real_write = arrange.write_whole

    def no_room(path, obj):
        raise OSError(28, "No space left on device")
    arrange.write_whole = no_room
    try:
        try:
            code, ans = sv({"cap_size": 2.5})
        except Exception as e:  # noqa: BLE001
            code, ans = None, repr(e)
    finally:
        arrange.write_whole = real_write
    check("a save that can't be written (a full or unplugged drive): 503 and plain words, never a Python error, the record as it was",
          code == 503 and ans["words"] == TR.TROUBLE and REC.read_bytes() == before, (code, ans))
    HUGE = 10 ** 400
    for name, saved in (("cap_size", {"cap_size": HUGE}), ("cap_pos", {"cap_pos": {"x": HUGE, "y": 0.5}}),
                        ("a stretch's place", {"shots": [shot(0, 0, pos={"x": HUGE, "y": 0.5, "w": 0.5})]}),
                        ("a stretch's start in its video", {"shots": [shot(0, 0, v=FOOT_KEY, **{"from": HUGE})]}),
                        ("a speed", {"speeds": [{"a": 0, "b": 1, "v": HUGE}]}), ("a negative one", {"cap_size": -HUGE})):
        try:
            code, ans = sv(saved)
        except Exception as e:  # noqa: BLE001
            code, ans = None, {"words": repr(e)}
        check(f"a whole number too large to be one ({name}): refused in plain words, nothing saved",
              code == 400 and ans["words"] == TR.NOT_UNDERSTOOD and REC.read_bytes() == before, (code, ans["words"]))
    check("the engine reads past such a number in a record too",
          eng.pieces({"words": WORDS[:3] + [{"w": "x", "start": HUGE, "end": 2}], "speeds": [{"a": 0, "b": 1, "v": HUGE}],
                      "shots": [{"a": 0, "b": 0, "ns": [HUGE, 2], "spot": "full", "from": HUGE, "pos": {"x": HUGE, "y": 0, "w": 1}}]}) != []
          and eng.clean([{"w": "x", "start": HUGE, "end": 2}]) == [])

    # ---- a record that holds the wrong kind of thing
    good_rec = REC.read_bytes()
    junk = json.loads(good_rec)
    junk.update({"rev": "abc", "cut": 5, "splits": "x", "speeds": 3, "zooms": {"a": 1}, "shots": True, "earlier": 7, "replaced": 5,
                 "cap_size": "big", "cap_pos": 4, "step": 9, "problem": ["x"], "status": 3, "updated": "then", "claude_cut": "no", "shot_keys": [1]})
    REC.write_text(json.dumps(junk), encoding="utf-8")
    try:
        stp = TR.state_for_page(KIT)
        ok = (stp["ok"] and stp["rev"] == 0 and stp["rec"]["cut"] == [] and stp["shots"] == [] and len(stp["pieces"]) > 0 and stp["rec"]["cap_size"] == 1
              and stp["rec"]["cap_pos"] is None and stp["rec"]["step"] == "" and stp["rec"]["kept_for"] == [])
    except Exception as e:  # noqa: BLE001
        ok, stp = False, repr(e)
    check("a record holding the wrong kind of thing in every field: the state is still made, the unreadable parts read as empty", ok, stp if not ok else None)
    r1, r2 = run("show", SHORT), run("status", SHORT)
    check("... show and status still answer", r1.returncode == 0 and r2.returncode == 0 and "Traceback" not in r1.stderr + r2.stderr, (r1.stderr[-300:], r2.stderr[-300:]))
    try:
        code, ans = TR.save_from_page(KIT, {"base": 0, "page": PAGE, "saved": {"captions": False}})
    except Exception as e:  # noqa: BLE001
        code, ans = None, repr(e)
    check("... and a save is taken (the counter starts again from 1)", code == 200 and rec()["rev"] == 1 and rec()["captions"] is False, (code, ans if code != 200 else None))
    try:
        TR.use_video(KIT, "second take.MOV")
        TR.use_video(KIT, "my talk.mp4")
        ok = True
    except Exception as e:  # noqa: BLE001
        ok = repr(e)
    check("... and choosing another video and coming back does not stop either", ok is True, ok)
    REC.write_bytes(good_rec)

    # ---- put_words cut off between its two writes
    def cut_off_put(words):
        real = TR.change

        def stop(*a, **k):
            raise KeyboardInterrupt("cut off")
        TR.change = stop
        try:
            TR.put_words(KIT, "my talk.mp4", KEY_NOW, words, {"dur": 3.0})
        except KeyboardInterrupt:
            pass
        finally:
            TR.change = real

    KEY_NOW = TR.state_for_page(KIT)["videos"][0]["key"]
    NINE = [dict(w, w=w["w"].upper()) for w in WORDS[:9]]
    cut_off_put(NINE)
    check("put_words cut off after the words file was written: the words are the new ones, the record still the old edit",
          len(json.loads(WORDSF.read_text(encoding="utf-8"))["videos"]["my talk.mp4"]["words"]) == 9 and rec()["cut"] == [[4, 5]])
    TR.put_words(KIT, "my talk.mp4", KEY_NOW, NINE, {"dur": 3.0})
    now = rec()
    check("... run again with the same words: the old cuts and photos are NOT left on the new script's word numbers; they are in replaced",
          "cut" not in now and "shots" not in now and now["replaced"][-1]["cut"] == [[4, 5]] and now["replaced"][-1]["shots"][0]["ns"] == [2]
          and now["words_of"] == json.loads(WORDSF.read_text(encoding="utf-8"))["videos"]["my talk.mp4"]["id"], {k: now.get(k) for k in ("cut", "shots", "words_of")})
    before = REC.read_bytes()
    TR.put_words(KIT, "my talk.mp4", KEY_NOW, NINE, {"dur": 3.0})
    check("... and once more changes nothing", REC.read_bytes() == before)
    sv({"cut": [[1, 2]]})
    cut_off_put(WORDS)
    code, ans = sv({"cap_size": 2})
    now = rec()
    check("cut off, and the job never runs again: the very next change of any kind starts the edit afresh (kept in replaced)",
          code == 200 and "cut" not in now and now["replaced"][-1]["cut"] == [[1, 2]] and now["cap_size"] == 2.0 and ans["rec"]["cut"] == [] and len(ans["rec"]["words"]) == NW, now.get("cut"))
    sv({"cut": [[1, 2]]})
    cut_off_put(NINE)
    stale = rec()["rev"] - 1
    code, ans = sv({"cut": [[0, 0]]}, base=stale, page="pageCCCC3")
    check("... even when that change is itself turned down as stale", code == 409 and "cut" not in rec() and rec()["replaced"][-1]["cut"] == [[1, 2]], (code, rec().get("cut")))
    TR.put_words(KIT, "my talk.mp4", KEY_NOW, WORDS, {"dur": 3.0})

    # ---- Edit my video pressed again: a stated choice, not a side effect of the words happening to differ
    sv({"cut": [[0, 2]]})
    before = REC.read_bytes()
    TR.put_words(KIT, "my talk.mp4", KEY_NOW, WORDS, {"dur": 3.0})
    check("the same words for the same file, not asked for again (a job that ran twice): nothing changes", REC.read_bytes() == before)
    words_bytes2 = WORDSF.read_bytes()
    TR.put_words(KIT, "my talk.mp4", KEY_NOW, WORDS, {"dur": 3.0}, again=True)
    now = rec()
    check("Edit my video again (again=True), the words coming back the same: the edit is emptied and the old one is in replaced (hers always clears)",
          "cut" not in now and now.get("claude_cut") is None and now["replaced"][-1]["cut"] == [[0, 2]] and now["replaced"][-1]["why"] == "Edit my video again"
          and WORDSF.read_bytes() == words_bytes2, now.get("cut"))
    before = REC.read_bytes()
    TR.put_words(KIT, "my talk.mp4", KEY_NOW, WORDS, {"dur": 3.0}, again=True)
    check("... and the same call twice changes nothing the second time", REC.read_bytes() == before)

    # ---- a Footage video whose file was exported again (or just touched) keeps its stretch
    clip = KIT / "Footage" / "clip one.mp4"
    key_a = reel_page.list_videos(KIT)[0]["key"]
    sv({"shots": [shot(0, 1, ns=[1]), shot(3, 5, v=key_a, spot="pip", **{"from": 0.5})]})
    VID = S(3, 5, [], "pip", v="clip one.mp4", frm=0.5)
    check("a Footage video saved by its key is stored by name", rec()["shots"][1] == VID and rec()["shot_keys"] == {key_a: "clip one.mp4"}, rec().get("shot_keys"))
    os.utime(clip, (time.time() - 7000, time.time() - 7000))
    key_b = reel_page.list_videos(KIT)[0]["key"]
    code, ans = sv({"shots": [shot(0, 2, ns=[1]), shot(3, 5, v=key_a, spot="pip", **{"from": 0.5})]})
    check("its file exported again under the same name (a new key), the page still holding the old key: the stretch survives a save of another stretch",
          key_b != key_a and code == 200 and rec()["shots"] == [S(0, 2, [1], "full"), VID], (code, rec()["shots"]))
    os.utime(clip, (time.time() - 9000, time.time() - 9000))
    code, ans = sv({"shots": [shot(0, 1, ns=[1]), shot(3, 5, v={"key": "0123456789ab", "name": "clip one.mp4"}, spot="pip", **{"from": 0.5})]})
    check("the state's own {key, name} sent back as it came, with a key that is no longer any file's: found by its name", code == 200 and rec()["shots"][1] == VID, (code, rec()["shots"]))
    code, ans = sv({"shots": [shot(0, 1, ns=[1]), shot(3, 5, v={"key": "0123456789ab", "name": "../x.mp4"})]})
    check("... a name that is not a plain file name refuses the save", code == 400)
    os.rename(clip, TMP / "clip-aside.mp4")
    gone = TR.state_for_page(KIT)["shots"][1]["v"]
    code, ans = sv({"shots": [shot(0, 2, ns=[3]), shot(3, 5, v=gone["key"], spot="pip", **{"from": 0.5})]})
    check("a stored stretch whose video has gone, sent back with the rest: it stays in the record (shown as gone), the other change is saved",
          gone.get("gone") is True and code == 200 and rec()["shots"] == [S(0, 2, [3], "full"), VID] and ans["shots"][1]["v"].get("gone") is True, (code, rec()["shots"]))
    code, ans = sv({"shots": [shot(0, 2, ns=[3]), shot(3, 5, v=TR.gone_key("never was.mp4")), shot(6, 7, v="abcdefabcdef")]})
    check("... while a video no stretch holds and no file has is still left out (hers: an Undo that names one since gone)", code == 200 and rec()["shots"] == [S(0, 2, [3], "full")], rec()["shots"])
    os.rename(TMP / "clip-aside.mp4", clip)

    # ---- the short answer notices what changes without the record changing
    st0 = TR.state_for_page(KIT)
    check("the short answer carries the mark; with the mark the page holds it stays short",
          TR.state_for_page(KIT, rev=st0["rev"], mark=st0["mark"]) == {"ok": True, "rev": st0["rev"], "mark": st0["mark"], "working": False, "step": ""})
    shutil.copyfile(CLIP, KIT / "Talking" / "third.mp4")
    got = TR.state_for_page(KIT, rev=st0["rev"], mark=st0["mark"])
    check("a video dropped into the Talking folder: the page (same counter, old mark) gets the whole state, with the new video",
          "rec" in got and got["mark"] != st0["mark"] and "third.mp4" in [v["name"] for v in got["videos"]], sorted(got))
    os.remove(KIT / "Talking" / "third.mp4")
    check("... taken out again, the mark is back", TR.folder_mark(KIT) == st0["mark"])
    os.utime(clip, (time.time() - 11000, time.time() - 11000))
    m1 = TR.folder_mark(KIT)
    os.utime(KIT / "Talking" / "my talk.mp4", (time.time() - 12000, time.time() - 12000))
    got = TR.state_for_page(KIT, rev=st0["rev"], mark=m1)
    check("a Footage video exported again moves the mark; the talking video exported again brings the whole state, saying so",
          m1 != st0["mark"] and got.get("video_state") == "changed", (m1, got.get("video_state")))
    sheet = KIT / ".kit" / "sheet.json"
    sheet_bytes = sheet.read_bytes()

    # ---- a photo that has left the numbered list
    KEY_NOW = TR.state_for_page(KIT)["videos"][0]["key"]
    TR.put_words(KIT, "my talk.mp4", KEY_NOW, WORDS, {"dur": 3.0})
    sv({"shots": [shot(0, 1, ns=[12, 3]), shot(4, 5, ns=[2])]})
    m2 = TR.folder_mark(KIT)
    sheet.write_text(json.dumps({"photos": [{"n": i, "file": f"IMG_{i:04d}.jpg"} for i in range(1, 12)]}), encoding="utf-8")
    stp = TR.state_for_page(KIT)
    check("a photo on a stretch that has left the numbered list: the state names it (photos_gone), and the mark moved",
          stp["photos_gone"] == [12] and stp["shots"][0]["ns"] == [12, 3] and stp["mark"] != m2, stp.get("photos_gone"))
    code, ans = sv({"shots": [shot(0, 1, ns=[12, 3]), shot(4, 6, ns=[2], spot="pip")]})
    check("... the page can send that stretch back with the rest: moving another stretch is saved, not refused",
          code == 200 and rec()["shots"] == [S(0, 1, [12, 3], "full"), S(4, 6, [2], "pip")], (code, rec()["shots"]))
    refused("... a photo number that was never there is still refused", {"shots": [shot(0, 1, ns=[12, 3]), shot(4, 6, ns=[99])]})
    code, ans = sv({"shots": [shot(4, 6, ns=[2], spot="pip")]})
    refused("... and once no stretch holds the gone photo it can't come back", {"shots": [shot(0, 1, ns=[12])]})
    sheet.write_bytes(sheet_bytes)

    # ---- 500 splits, and 501 (a script long enough to have them)
    LONG = CONTENT / "2026-10-01 Hannah"
    MANY = [{"w": f"w{i}", "start": round(i * 0.3, 3), "end": round(i * 0.3 + 0.2, 3)} for i in range(600)]
    TR.put_words(LONG, "long talk.mp4", "a" * 12, MANY, {"dur": 180.0})
    LREC = LONG / ".kit" / "talking.json"

    def svl(saved):
        return TR.save_from_page(LONG, {"base": json.loads(LREC.read_text(encoding="utf-8"))["rev"], "page": PAGE, "saved": saved})
    code, ans = svl({"splits": list(range(1, 501))})
    check("500 splits are taken", code == 200 and json.loads(LREC.read_text(encoding="utf-8"))["splits"] == list(range(1, 501)), code)
    before = LREC.read_bytes()
    code, ans = svl({"splits": list(range(1, 502))})
    check("501 splits are refused, the record byte for byte as it was", code == 400 and ans["words"] == TR.NOT_UNDERSTOOD and LREC.read_bytes() == before, code)
    code, ans = svl({"splits": list(range(1, 501)) + [5, 7]})
    check("... 500 with doubles among them are the same 500 (nothing to write)", code == 200 and LREC.read_bytes() == before, code)

    # ---- the chat's files: a number written as text, and a file with no cut in it
    r = run("cut", "Hannah", "--file", jfile({"cut": [["0", "2"], [" 7 ", 8.0]]}))
    check('cut: numbers written as text ("0", "2") are taken as hers takes them',
          r.returncode == 0 and json.loads(LREC.read_text(encoding="utf-8"))["cut"] == [[0, 2], [7, 8]], r.stdout)
    before = LREC.read_bytes()
    for bad in ({}, {"cuts": [[0, 1]]}, {"cut": None}):
        r = run("cut", "Hannah", "--file", jfile(bad))
        check(f"cut: a file with no cut list in it ({json.dumps(bad)}) stops; it is never read as an empty cut",
              r.returncode == 2 and r.stdout.startswith('STOP: the file should be {"cut": ') and LREC.read_bytes() == before, r.stdout)
    r = run("cut", "Hannah", "--file", jfile({"cut": [["²", 3]]}))
    check("cut: a number that is not one stops in plain words", r.returncode == 2 and "isn't a range of word numbers (0 to 599)" in r.stdout and "Traceback" not in r.stderr, r.stdout)

    # ---- something else holds the record
    holder = subprocess.Popen([sys.executable, "-c",
                               "import sys; sys.path.insert(0, sys.argv[1]); import this_computer\n"
                               "f = open(sys.argv[2], 'ab'); print('held' if this_computer.try_lock(f) else 'no', flush=True); sys.stdin.read()",
                               str(SCRIPTS), str(LONG / ".kit" / "talking.lock")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=ENV)
    try:
        if holder.stdout.readline().strip() == "held":
            before = LREC.read_bytes()
            wait, TR.LOCK_WAIT = TR.LOCK_WAIT, 0.4
            try:
                code, ans = svl({"captions": False})
            finally:
                TR.LOCK_WAIT = wait
            check("another program holding the record: a page save is told to try again (503, the busy line), nothing written",
                  code == 503 and ans == {"ok": False, "words": TR.BUSY, "why": "busy"} and LREC.read_bytes() == before, (code, ans))
            r = run("cut", "Hannah", "--file", jfile({"cut": [[0, 1]]}))
            check("... and the chat's cut stops with the same line, exit 2, nothing written",
                  r.returncode == 2 and r.stdout.strip() == "STOP: " + TR.BUSY and LREC.read_bytes() == before, r.stdout)
        else:
            print("SKIP  a held record lock (this drive has no such locks)")
    finally:
        holder.stdin.close()
        holder.wait(timeout=20)
    code, ans = svl({"captions": False})
    check("... once it lets go, the save goes through", code == 200)

    # ---- several writers at once
    import threading
    errors, codes = [], []

    def page_writer(k):
        try:
            for i in range(12):
                base = json.loads(LREC.read_text(encoding="utf-8"))["rev"]
                c, _ = TR.save_from_page(LONG, {"base": base, "page": f"pageHAMR{k}", "saved": {"cap_size": round(0.5 + (k * 12 + i) / 100, 2)}})
                codes.append(c)
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))

    def chat_cutter():
        try:
            for i in range(12):
                TR.save_cut(LONG, {"cut": [[i, i + 1]], "why": ["a restart"]})
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))
    rev0 = json.loads(LREC.read_text(encoding="utf-8"))["rev"]
    ths = [threading.Thread(target=page_writer, args=(k,)) for k in range(4)] + [threading.Thread(target=chat_cutter)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    end = json.loads(LREC.read_text(encoding="utf-8"))
    check("four pages and the chat saving at once: no error, every answer a plain 200 or 409, the record whole, the chat's last cut in it, no scratch file left",
          not errors and set(codes) <= {200, 409} and end["cut"] == [[11, 12]] and end["rev"] >= rev0 + 12
          and not [f.name for f in (LONG / ".kit").iterdir() if f.name.endswith(".tmp")], (errors[:2], sorted(set(codes)), end.get("cut")))

    # ------------------------------------------------------------ fix a word (her v27, Nov 17): the record, the save, the engine
    # Hers rewrites the word inside the record and keeps the heard word beside it as w0. Ours keeps the words
    # file as it was written and lays {"fixes": {"<word number>": "the right words"}} over the words when the
    # record is read: every reader sees her shape (w the fixed word, w0 the heard one).
    FK = make_kit("2026-10-05 Aurora fixes")
    FSHORT = "Aurora fixes"
    FREC, FWORDS = FK / ".kit" / "talking.json", FK / ".kit" / "talking-words.json"
    (FK / "Talking").mkdir()
    shutil.copyfile(CLIP, FK / "Talking" / "aurora.mp4")
    shutil.copyfile(CLIP, FK / "Talking" / "take two.mp4")
    ftalks = TR.list_talks(FK)
    FKEY = ftalks[0]["key"]
    TR.put_words(FK, "aurora.mp4", FKEY, WORDS, {"dur": 3.0, "w": 640, "h": 360}, {"how": "pretend", "ondevice": True})
    fwords_bytes = FWORDS.read_bytes()
    FPAGE = "pageFIX01"

    def frec():
        return json.loads(FREC.read_text(encoding="utf-8"))

    def fsv(saved, base=None):
        return TR.save_from_page(FK, {"kit": "2026-10-05 Aurora fixes", "base": TR.state_for_page(FK, rev=-1)["rev"] if base is None else base,
                                      "page": FPAGE, "saved": saved})

    def frefused(name, saved):
        before, rev = FREC.read_bytes(), frec()["rev"]
        code, ans = fsv(saved)
        check("fixes refused: " + name + " (the whole save, nothing written)",
              code == 400 and ans == {"ok": False, "words": TR.NOT_UNDERSTOOD} and FREC.read_bytes() == before and frec()["rev"] == rev, (code, ans))

    # "so" (word 1) heard for "want to"; "um" (word 2) typed away; "beach." (word 7) fixed to "beach!"
    code, ans = fsv({"fixes": {"1": "want to", "2": "", "7": "beach!"}})
    st = ans.get("rec", {}) if code == 200 else {}
    check("a save of fixes lands: the record holds the map by word number, nothing else of the words",
          code == 200 and frec()["fixes"] == {"1": "want to", "2": "", "7": "beach!"} and "words" not in frec(), (code, frec().get("fixes")))
    check("... the page's state is her shape: w is the fixed word and w0 the heard one, on the fixed words only",
          st.get("words", [{}])[1] == {"w": "want to", "w0": "so", "start": 0.5, "end": 0.75}
          and st["words"][2] == {"w": "", "w0": "um", "start": 1.0, "end": 1.25} and st["words"][7]["w"] == "beach!" and st["words"][7]["w0"] == "beach."
          and all("w0" not in w for i, w in enumerate(st["words"]) if i not in (1, 2, 7)) and len(st["words"]) == NW, st.get("words", [])[:3])
    check("... every word keeps its number: a typed-away word is still there (her captions skip it, her pieces play it)",
          len(TR.load(FK)["words"]) == NW and TR.load(FK)["words"][2]["w"] == "" and TR.load(FK)["words"][3]["w"] == "we")
    caps = TR.state_for_page(FK)["captions"]
    # one piece from 0 (word 0 starts at 0.0; 0.08 before is clamped): a caption starts at its word's start, and the
    # caption before the typed-away word ("want to", word 1, 0.5) stays up until the next kept one ("we", word 3, 1.5)
    check("... the captions use the fixed words, at the heard word's times, and none for the word typed away",
          [c["text"] for c in caps] == ["OK", "want to", "we", "were", "at", "the", "beach!"] + SAID[8:] and caps[1]["start"] == 0.5
          and caps[1]["end"] == caps[2]["start"] == 1.5, [(c["text"], c["start"], c["end"]) for c in caps][:4])
    check("... pieces, cuts and timing are untouched by a fix", TR.state_for_page(FK)["pieces"] == TR.state_for_page(FK)["pieces"]
          and len(TR.state_for_page(FK)["pieces"]) == len(eng.pieces({"words": WORDS})) and TR.state_for_page(FK)["rec"]["cut"] == [])
    check("... the words file is byte for byte as it was written", FWORDS.read_bytes() == fwords_bytes)
    before, rev = FREC.read_bytes(), frec()["rev"]
    code, ans = fsv({"fixes": {"1": "want to", "2": "", "7": "beach!"}})
    check("the same map sent again writes nothing (the counter stays)", code == 200 and FREC.read_bytes() == before and ans["rev"] == rev)
    code, ans = fsv({"fixes": {"1": " want   to ", "7": "beach!", "2": ""}})
    check("... whitespace collapsed and in any order, it is still the same map: nothing written", code == 200 and FREC.read_bytes() == before)
    code, ans = fsv({"fixes": {"1": "want to", "7": "beach!", "2": "", "3": "we"}})
    check("a fix equal to the heard word is dropped (hers does the same), so that too writes nothing", code == 200 and FREC.read_bytes() == before)
    code, ans = fsv({"fixes": {"1": "so", "2": "", "7": "beach!"}})
    check("a fix put back to the heard word goes out of the map, and the word is simply the word again",
          code == 200 and frec()["fixes"] == {"2": "", "7": "beach!"} and ans["rec"]["words"][1] == {"w": "so", "start": 0.5, "end": 0.75})
    code, ans = fsv({"fixes": {}})
    check("Undo: the earlier map (empty) brings every heard word back, and the record holds no fix",
          code == 200 and frec().get("fixes") == {} and all("w0" not in w for w in ans["rec"]["words"]) and [c["text"] for c in ans["captions"]] == SAID)
    fsv({"fixes": {"1": "want to", "2": ""}})
    frefused("a map that is a list", {"fixes": [["1", "x"]]})
    frefused("a key past the last word", {"fixes": {str(NW): "x"}})
    frefused("a key that isn't digits", {"fixes": {"a": "x"}})
    frefused("a key with a sign", {"fixes": {"-1": "x"}})
    frefused("a key that is a number, not text (a hand-made request)", {"fixes": {1: "x"}})
    frefused("a value that isn't text (hers would store \"['a']\")", {"fixes": {"1": ["a"]}})
    frefused("a value that is a number", {"fixes": {"1": 5}})
    frefused("81 characters (hers cuts to 80 without a word)", {"fixes": {"1": "x" * 81}})
    frefused("two keys naming one word (\"01\" and \"1\")", {"fixes": {"01": "x", "1": "y"}})
    frefused("more entries than words", {"fixes": {str(i): "x" for i in range(NW + 1)}})
    frefused("one good field beside bad fixes", {"captions": False, "fixes": {"x": "y"}})
    code, ans = fsv({"fixes": {"1": "x" * 80, "2": ""}})
    check("80 characters is taken, and the key \"01\" is read as word 1", code == 200 and frec()["fixes"]["1"] == "x" * 80
          and fsv({"fixes": {"01": "y", "2": ""}})[1]["rec"]["words"][1]["w"] == "y" and frec()["fixes"] == {"1": "y", "2": ""})
    check("... and none of the refusals wrote anything to the words file", FWORDS.read_bytes() == fwords_bytes)
    fsv({"fixes": {"1": "want to", "2": "", "7": "beach!"}})
    # a stretch on a fixed word and on the word typed away: still on those numbers (nothing was renumbered)
    fsv({"shots": [{"a": 2, "b": 3, "ns": [1], "spot": "pip", "pos": None, "me": None}], "cut": [[7, 7]]})
    stf = TR.state_for_page(FK)
    span = eng.shot_spans(TR.load(FK), stf["pieces"])[0]
    piece2 = next((p for p in stf["pieces"] if p["words"][0] == 2), None)
    check("a stretch on the typed-away word and a cut on a fixed word sit on those very words (no one-off from an empty word)",
          stf["shots"][0]["a"] == 2 and stf["rec"]["cut"] == [[7, 7]] and "beach!" not in [c["text"] for c in stf["captions"]]
          and piece2 is not None and piece2["from"] == round(1.0 - 0.08, 3) and span == {"at": piece2["at"], "dur": piece2["dur"]}, (stf["shots"], span, piece2))
    # a fix on a cut word is kept (hers allows it: the word shows crossed out and fixed)
    check("a fix on a cut word is kept", frec()["fixes"]["7"] == "beach!" and stf["rec"]["words"][7]["w0"] == "beach.")
    # the assistant's side: show and photos print the fixed word as THE word; status counts the fixes
    # ("w0", the record's own name for the word as it was heard, must never be printed. It is looked for in what
    # was said with this test's own folders taken out: photos prints where the photos are, and a computer's
    # scratch folder may itself have "w0" in its name, as GitHub's Mac had: /var/folders/h5/..._w0000gn/T.)
    def said(out):
        for place in sorted({str(TMP), str(ROOT), tempfile.gettempdir(), str(Path(tempfile.gettempdir()).resolve())}, key=len, reverse=True):
            out = out.replace(place, "")
        return out

    out = run("show", FSHORT).stdout
    check("show: the fixed word is simply the word to the assistant (rule 3: it never touches a caption word); a typed-away word is empty",
          "0:OK 1:want to 2: 3:we" in out and "7:beach!" in out and "w0" not in said(out) and "1:so" not in out and "2:um" not in out, out[-300:])
    out = run("photos", FSHORT).stdout
    check("photos: the same (the cut word 7 left out, as any cut word)", "0:OK 1:want to 2: 3:we" in out and "7:beach" not in out and "w0" not in said(out), said(out)[-600:])
    out = run("status", FSHORT).stdout
    check("status: one line of ours says how many words were fixed, and nothing else about them",
          "  Words fixed on the page: 3." in out and "want to" not in out and "w0" not in said(out), out)
    out = run("status", SHORT).stdout
    check("... and no such line when nothing was fixed", "Words fixed" not in out, out)
    # a fix is not "their own work" for cut --replace: fixes never touch cuts or stretches
    TR.change(FK, lambda r: r.update(cut=[]) or r.pop("shots", None) and None)
    r = run("cut", FSHORT, "--file", jfile({"cut": [[0, 0]], "why": ["the warm-up"]}))
    check("the assistant may cut a script whose only edit is fixes (a fix is not their own cut)", r.returncode == 0 and frec()["cut"] == [[0, 0]]
          and frec()["fixes"] == {"1": "want to", "2": "", "7": "beach!"}, (r.returncode, r.stdout[-200:]))
    # another video, and back: the fixes move with the rest of the edit
    TR.use_video(FK, "take two.mp4")
    now = frec()
    check("another video: the fixes go into \"earlier\" with the edit, and the new video starts with none",
          "fixes" not in now and now["earlier"]["aurora.mp4"]["fixes"] == {"1": "want to", "2": "", "7": "beach!"}
          and TR.state_for_page(FK)["rec"]["words"] == [], now.get("earlier"))
    TR.use_video(FK, "aurora.mp4")
    check("... and come back with it", frec()["fixes"] == {"1": "want to", "2": "", "7": "beach!"} and TR.state_for_page(FK)["rec"]["words"][1]["w"] == "want to")
    # the script made again (Edit my video again): the fixes belong to the old word numbers; kept in replaced
    WORDS_AGAIN = [dict(w, start=w["start"] + 0.1, end=w["end"] + 0.1) for w in WORDS[:10]]
    TR.put_words(FK, "aurora.mp4", FKEY, WORDS_AGAIN, {"dur": 3.0})
    now = frec()
    check("Edit my video again: the fixes are kept in replaced with the cuts (hers loses them without a word), and the edit starts afresh",
          "fixes" not in now and now["replaced"][-1]["fixes"] == {"1": "want to", "2": "", "7": "beach!"} and now["replaced"][-1]["cut"] == [[0, 0]]
          and now["replaced"][-1]["why"] == "Edit my video again" and all("w0" not in w for w in TR.state_for_page(FK)["rec"]["words"]), now.get("replaced", [])[-1:])
    TR.put_words(FK, "aurora.mp4", FKEY, WORDS, {"dur": 3.0})
    fwords_bytes = FWORDS.read_bytes()                     # the words were made again (twice): written by put_words, as ever; never by a fix
    fsv({"fixes": {"4": "WERE"}})
    # several talking reels (v25): a reel's fixes are put away and brought back with its other fields
    code, ans = TR.version_op(FK, {"op": "new"})
    check("a new talking reel starts with no fixes, and the first reel's are put away with the rest of it",
          code == 200 and ans["current"] == "v2" and "fixes" not in frec() and frec()["versions"][0]["data"]["fixes"] == {"4": "WERE"}
          and TR.state_for_page(FK)["rec"]["words"] == [], (code, frec().get("versions")))
    check("... load(kit, reel) shows the other reel's fixed word", TR.load(FK, "v1")["words"][4] == dict(WORDS[4], w="WERE", w0="were"))
    code, ans = TR.version_op(FK, {"op": "switch", "id": "v1"})
    check("... and switching back brings them up", code == 200 and frec()["fixes"] == {"4": "WERE"} and TR.state_for_page(FK)["rec"]["words"][4]["w"] == "WERE")
    # Open CapCut (v27): the newest project made from the OPEN reel; each talking reel keeps its own made list
    check("last_made: nothing made from this reel yet, and the page's state says so (rec.made, her REC.made.length)",
          TR.last_made(FK) is None and TR.state_for_page(FK)["rec"]["made"] is False)
    rev_before = frec()["rev"]
    TR.note_made(FK, "Aurora talking reel")
    TR.note_made(FK, "Aurora talking reel 2")
    stm = TR.state_for_page(FK)
    check("last_made names the newest project made from the open reel; the state tells the page only THAT one was made, never a project's name; the counter did not move",
          TR.last_made(FK) == "Aurora talking reel 2" and stm["rec"]["made"] is True and "Aurora talking reel" not in json.dumps(stm) and frec()["rev"] == rev_before,
          (TR.last_made(FK), stm["rec"].get("made"), frec()["rev"], rev_before))
    code, ans = TR.version_op(FK, {"op": "switch", "id": "v2"})
    check("another talking reel of the shoot has its own made list (none yet): last_made is None there and the page shows no Open CapCut, while the first reel's list is put away whole",
          code == 200 and TR.last_made(FK) is None and TR.state_for_page(FK)["rec"]["made"] is False
          and [m["project"] for m in frec()["versions"][0]["data"]["made"]] == ["Aurora talking reel", "Aurora talking reel 2"], frec().get("versions"))
    TR.note_made(FK, "Aurora talking reel 3")
    check("... a make noted while it is open goes to it alone", TR.last_made(FK) == "Aurora talking reel 3" and TR.state_for_page(FK)["rec"]["made"] is True)
    code, ans = TR.version_op(FK, {"op": "switch", "id": "v1"})
    check("... and back on the first reel, its own newest", code == 200 and TR.last_made(FK) == "Aurora talking reel 2"
          and [m["project"] for m in frec()["versions"][1]["data"]["made"]] == ["Aurora talking reel 3"])
    TR.change(FK, lambda r: r.update(made=[{"project": 3}, "x", {"when": 1}, {"project": ""}]))
    check("a record changed by hand: entries of made that don't name a project don't count, and the page shows no Open CapCut",
          TR.last_made(FK) is None and TR.state_for_page(FK)["rec"]["made"] is False)
    TR.change(FK, lambda r: r.update(made="no"))
    check("... made that isn't a list at all reads as none", TR.last_made(FK) is None and TR.state_for_page(FK)["ok"] and TR.state_for_page(FK)["rec"]["made"] is False)
    TR.change(FK, lambda r: r.pop("made", None) and None)
    # a record changed by hand: fixes that aren't a map, or an entry that isn't a digit key and text, are left out
    TR.change(FK, lambda r: r.update(fixes={"4": "WERE", "x": "no", "5": 3, "99": "far"}))
    stf = TR.state_for_page(FK)
    check("a record changed by hand: only the entries that are a word number and text are laid over; a number past the words is ignored",
          stf["rec"]["words"][4]["w"] == "WERE" and all("w0" not in w for i, w in enumerate(stf["rec"]["words"]) if i != 4), stf["rec"]["words"][4:6])
    TR.change(FK, lambda r: r.update(fixes="not a map"))
    check("... fixes that aren't a map at all read as none", all("w0" not in w for w in TR.state_for_page(FK)["rec"]["words"]) and TR.state_for_page(FK)["ok"])
    check("... and the words file was never touched by any of it", FWORDS.read_bytes() == fwords_bytes)

    # ------------------------------------------------------------ + Add more photos (her v27): photos dropped in while the pop-up is open
    # The page's look sends photos=1 only while its photo pop-up is open; the state then has any photo dropped into
    # the Photos folder numbered first (talking_rec.photos_landed -> reel_page.relist_if_changed -> kit.py sheet,
    # the one writer, handed the list from last time), so the mark moves and the whole state comes back. Lane A's
    # contract, proved from this side: every earlier number is kept, a new photo takes the next number after the
    # highest ever given, a photo gone keeps its number unused.
    sys.path.insert(0, str(ROOT / "tests"))
    import words_page_check as wpc         # its tiny picture
    MK = make_kit("2026-10-09 More photos", photos=2)          # the pretend list names IMG_0001 and IMG_0002: neither is in the folder
    msheet = MK / ".kit" / "sheet.json"
    st_a = TR.state_for_page(MK)

    def drop(name, old=True):
        f = MK / "Photos" / name
        f.write_bytes(wpc.TINY)
        if old:
            os.utime(f, (time.time() - 30, time.time() - 30))
        return f

    def listed():
        return [(x["n"], Path(x["file"]).name) for x in arrange.sheet_rows(MK)]

    drop("sunset-001.jpg")
    plain = TR.state_for_page(MK, rev=st_a["rev"], mark=st_a["mark"])
    check("without photos=1 (the pop-up closed) a photo dropped into the Photos folder is not numbered: the short answer, the list as it was",
          "rec" not in plain and listed() == [(1, "IMG_0001.jpg"), (2, "IMG_0002.jpg")], (sorted(plain), listed()))
    got = TR.state_for_page(MK, rev=st_a["rev"], mark=st_a["mark"], photos=True)
    check("with photos=1 the photo is numbered first, after the highest number ever given (3; the two gone keep theirs unused), and the whole state comes back with the mark moved",
          "rec" in got and got["mark"] != st_a["mark"] and got["stamp"] != st_a["stamp"] and listed() == [(3, "sunset-001.jpg")], (sorted(got)[:4], listed()))
    reel_page._RELIST.clear()                                   # the folder is compared at most every 4 s a kit: the next look, now
    drop("sunset-000.jpg")                                      # sorts BEFORE the one listed: it still takes the next number, never 3
    m_b = TR.state_for_page(MK)["mark"]
    TR.state_for_page(MK, photos=True)
    check("a second photo, though it sorts first by name, takes the next number (4) and the one before keeps 3",
          listed() == [(3, "sunset-001.jpg"), (4, "sunset-000.jpg")] and TR.state_for_page(MK)["mark"] != m_b, listed())
    reel_page._RELIST.clear()
    drop("sunset-002.jpg", old=False)                           # changed just now: still being copied in
    m_c = TR.state_for_page(MK)["mark"]
    TR.state_for_page(MK, photos=True)
    check("a photo still being copied in (changed this moment) is not numbered yet: the list and the mark as they were",
          listed() == [(3, "sunset-001.jpg"), (4, "sunset-000.jpg")] and TR.state_for_page(MK)["mark"] == m_c, listed())
    os.utime(MK / "Photos" / "sunset-002.jpg", (time.time() - 30, time.time() - 30))
    reel_page._RELIST.clear()
    TR.state_for_page(MK, photos=True)
    check("...settled, it is numbered at the next look (5)", listed() == [(3, "sunset-001.jpg"), (4, "sunset-000.jpg"), (5, "sunset-002.jpg")], listed())
    reel_page._RELIST.clear()
    sb = msheet.read_bytes()
    TR.state_for_page(MK, photos=True)
    check("nothing landed: photos=1 writes nothing (the list byte for byte)", msheet.read_bytes() == sb)
    check("no path of the Photos folder is in the state", str(MK) not in json.dumps(TR.state_for_page(MK)) and "sunset" not in json.dumps(TR.state_for_page(MK)))

    # ------------------------------------------------------------ her rules, character for character
    # Her v24 talking.py: her v25 and v27 packs say it is unchanged since v24 and carry no copy (her v27
    # talking_core.py differs from v24 by one captions line only, diffed Nov 17; its rule blocks are not in it).
    roots = [ROOT.parent / "hf-tools" / "reference-private", ROOT / "reference-private"]
    try:                                                   # a worktree: the main checkout's reference-private too
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"], capture_output=True, text=True, timeout=20).stdout.strip()
        if out:
            roots.append((ROOT / out).resolve().parent / "reference-private")
    except (OSError, subprocess.SubprocessError):
        pass
    HERS = next((r / "nicole-handoff-v24-2026-11-11" / "Carousel designer and reel picker" / "talking.py" for r in roots
                 if (r / "nicole-handoff-v24-2026-11-11" / "Carousel designer and reel picker" / "talking.py").is_file()), roots[0] / "none")
    if HERS.is_file():
        her = HERS.read_text(encoding="utf-8")                 # read as text, never run
        hr = re.search(r'^RULES = """(.*?)"""', her, re.S | re.M)
        hp = re.search(r'^PHOTO_RULES = """(.*?)"""', her, re.S | re.M)
        check("RULES is hers, character for character", bool(hr) and hr.group(1) == eng.RULES)
        check("PHOTO_RULES is hers, character for character", bool(hp) and hp.group(1) == eng.PHOTO_RULES)
        for line in (TR.NO_SCRIPT_SHOW, TR.NO_SCRIPT, TR.THEIR_CUTS, TR.THEIR_PHOTOS, TR.PHOTOS_PLACED,
                     "Already cut (theirs or yours): ", " isn't a range of word numbers (0 to ", " isn't a range of word numbers that follows the one before it",
                     ": each stretch needs photo numbers and a spot (pip, full, center, corner)", " cuts. The reel is now ",
                     " seconds of talking. The page shows it in a few seconds.", " photo stretches, ", " photos. The page shows them in a few seconds.",
                     " words. Each word is number:word (seconds).", ": the kept words, by sentence. Each word is number:word.",
                     "See them on the reel maker's contact sheet (the numbers match the page):"):
            check(f"her command line is in her file: {line.strip()[:60]}", line in her)
        core = (HERS.parent / "talking_core.py").read_text(encoding="utf-8")
        check("NOT_IN_TALKING is her line", reel_page.NOT_IN_TALKING in core)
    else:
        print("SKIP  her rules against her own file (her v24 folder is not beside the repo)")

    # ------------------------------------------------------------ our way: no spelled-out home, nothing outside the kit
    for f in (REEL / "talking.py", SCRIPTS / "talking_rec.py"):
        src = f.read_text(encoding="utf-8")
        check(f"{f.name}: no home spelled out (everything on the computer's own disk goes through arrange.HOME)",
              "expanduser" not in src and (".stu" + "dio") not in src and "Path.home" not in src)
    check("the log is the Assistant's own, in its logs folder", TR.LOG == Path(STUDIO) / "logs" / "talking.log")
    inside = {p.name for p in (KIT / ".kit").iterdir()}
    check("everything it wrote is in the kit's hidden folder",
          {"talking.json", "talking.prev.json", "talking-words.json", "talking-words.prev.json", "talking.lock", "talking"} <= inside
          and {p.name for p in KIT.iterdir()} == {".kit", "Photos", "Talking", "Footage"}, sorted(inside))
    check("nothing of theirs was changed: the videos are byte for byte the fixture",
          all((KIT / d / n).read_bytes() == CLIP.read_bytes() for d, n in (("Talking", "my talk.mp4"), ("Talking", "second take.MOV"), ("Footage", "clip one.mp4"))))
    check("the scratch Assistant folder holds no talking file (nothing of theirs is kept there)",
          not any("talking" in p.name.lower() and p.name != "talking.log" for p in STUDIO.rglob("*")), [p.name for p in STUDIO.rglob("*")])
    check("the real Assistant folder on this computer is exactly as it was", real_listing() == REAL_BEFORE)
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print()
print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
