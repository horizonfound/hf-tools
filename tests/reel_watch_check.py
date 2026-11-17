#!/usr/bin/env python3
"""Nicole's v27, Lane A stage 4: Watch your reel before you make it (A10), Would you like to direct this edit? (A13)
and B-roll on the page with its words on screen (A14), checked on the server and on the real page in a HIDDEN
Chrome, on a pretend kit and small clips this test makes itself.

    python3 tests/guard.py 800 python3 tests/reel_watch_check.py --work /private/tmp/somewhere [--port 8816]
        [--only words|status|preview|direct|broll|page]

What it holds:
  her words     reel_page.DIRECT_WORDS, WATCH_WORDS and ONSCREEN_WORDS against her v27 reel-maker.html, both ways,
                and her style rules for the watch step as she wrote them
  the status    reel.py make --dry-run --status writes the pieces as the page plays them (a photo by its number, a
                clip by c1, c2... and where it starts), the song's start and length, and the mix; a reel of clips
                only (B-roll) is planned; --hook-whole puts the words over the whole reel
  the preview   POST /reel-preview: the pieces add up to the plan's length, photos by number only (no path, no file
                name), Try another mix changes the beats, Another part moves where the song starts, a start past
                the song's end is refused in plain words, the preview for another reel is refused, nothing is
                written to the record and nothing into Make my reel's own folder; Make my reel and the chat's make
                carry variation and song_start (the job's ask, the status JSON, the made entry)
  direct        saved up to 800 characters (801 refused), the section hidden on B-roll, reel_page.py show and note
                print it; reel_page.py direct sets the style, the clips and the order in one go, refuses an unknown
                clip, a clip of another reel, a 13th clip and a B-roll reel, and run twice writes nothing
  B-roll        a make with three clips and no photos plans "clip N, clip N, clip N" and makes a CapCut project
                whose text layer carries the words for the whole reel; a photos reel still refuses an empty pick;
                onscreen is saved field by field (x, y, size as numbers in range; a string, an out-of-range number,
                a font or style that isn't hers refused); the made entry carries footage "broll" and no picks;
                today's eight kept projects are unchanged (tests/capcut_even.py)
  the page      in a hidden Chrome: the watch step and her words, the preview arrives with her line under it, Try
                another mix says Mix 2, Undo and Redo, Another part of this song, a change in step 2 refreshes the
                preview, Make this one in CapCut sends the watched mix and start; the direct box and its line's
                four shapes; on B-roll: the words block drawn from the box, dragged to a new place and sized by
                the dot (saved as x, y, size), the bar "N clips · B-roll"; Save my video pressed on the page: her
                saving line, then her Saved line with the file's name and Open the folder
  Save my video POST /reel-video (A15): a job the page follows, the finished MP4 in <shoot>/Reels as
                "<short> B-roll - <reel name>.mp4" (1080 x 1920, with sound, as long as the job says), a second save
                " 2", the made entry with the video's name (Lane D's contract), reels_for_kit and reel_page.py show
                saying so, Open the folder; no clips, bad words, an unknown field, a stale list and a reel of another
                kind refused in plain words; on a PC the named gap and nothing started

Nothing here touches the real ~/.studio, a real kit, CapCut, the real Trash or a visible window. Every line
says PASS, FAIL or SKIP; exit 1 only when something FAILED.
"""
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import reel_page_check as rpc  # noqa: E402
import reel_footage_check as rfc  # noqa: E402   (its clips, its LIGHT Chrome, its helpers; it sets rpc.PHOTOS to 12)

KIT = rpc.KIT
KQ = KIT.replace(" ", "%20")
PHOTOS = rpc.PHOTOS
PICKS = "3,1+,7,4,12-,9,2,10+"


def rp():
    sys.path.insert(0, str(SCRIPTS))
    import reel_page
    return reel_page


def V():
    sys.path.insert(0, str(REEL))
    import video
    return video


def her_page():
    return rpc.her_v27_page()


def record(s):
    return rfc.record(s)


def write_record(s, rec):
    (s.kit / ".kit" / "reel-page.json").write_text(json.dumps(rec, ensure_ascii=False))


def no_path(obj):
    return rfc.no_path(obj)


def preview(s, body):
    st = s.state()
    b = {"kit": KIT, "stamp": st["stamp"]}
    b.update(body)
    return s.http("POST", "/reel-preview", b)


def wait(c, cond, seconds=8):
    return rfc.wait(c, cond, seconds)


# ---------- 1. her words ----------

def check_words():
    R = rp()
    hers = her_page()
    tables = {"DIRECT_WORDS": R.DIRECT_WORDS, "WATCH_WORDS": R.WATCH_WORDS, "ONSCREEN_WORDS": R.ONSCREEN_WORDS}
    case("the three tables are there and apart from WORDS (the whole-build check compares each with her page)",
         all(isinstance(t, dict) and t for t in tables.values()) and not (set(R.DIRECT_WORDS) | set(R.WATCH_WORDS) | set(R.ONSCREEN_WORDS)) & set(R.WORDS))
    if hers is None:
        print("SKIP  her words against her v27 page: her handoff (reference-private) isn't on this computer", flush=True)
        return
    text = html.unescape(hers).replace("\\'", "'")
    for name, table in tables.items():
        bad = []
        for k, v in table.items():
            for frag in re.split(r"\{\w+\}", v):
                if len(frag.strip()) >= 2 and frag not in text:
                    bad.append((k, frag))
        case("every word of reel_page.%s (%d) is in her v27 reel page, word for word" % (name, len(table)), not bad, bad[:4])
    # both ways: every line her markup shows in the direct step and the watch step is one of ours, whole
    def block(id_):
        m = re.search(r'<section class="step[^"]*" id="%s"[^>]*>(.*?)</section>' % id_, hers, re.S)
        return m.group(1) if m else ""
    direct, watch = block("stepDirect"), block("watch")
    case("(her two sections are in her page)", bool(direct) and bool(watch))
    shown = re.findall(r">([^<>]{3,})<", direct + watch)
    shown = [html.unescape(x).strip() for x in shown if x.strip() and not x.strip().startswith("&#")]
    ours = set()
    for table in tables.values():
        for v in table.values():
            ours.add(re.sub(r"<[^>]+>", "", html.unescape(v)).strip())
            for frag in re.split(r"<[^>]+>", v):
                if frag.strip():
                    ours.add(html.unescape(frag).strip())
    ours |= {R.WORDS["copy"]} | {R.WORDS["vibe_%s_b" % v] for v in R.VIBES} | {R.WORDS["style_%s_b" % st] for st in R.STYLES}
    hidden = {"Top", "Middle", "Bottom", "Where I put them", "On the first clip", "The whole reel"}   # her hidden selects (not built)
    missing = [x for x in shown if x not in ours and x not in hidden and not re.fullmatch(r"[\s▶↶↷]*", x)]
    case("...and every line her direct step and watch step show is one of ours, whole (her hidden Top/Middle/Bottom and 'how long' selects aside)", not missing, missing)
    for attr in ("placeholder", "title", "aria-label"):
        vals = [html.unescape(v) for v in re.findall(r'%s="([^"]+)"' % attr, direct + watch)]
        miss = [v for v in vals if v not in ours and v not in ("Where on the screen", "How long it shows")]
        case("...her %ss there too" % attr, not miss, miss)
    sty = re.search(r"<style>(.*?)</style>", hers, re.S).group(1)
    for rule in (".watch .wgrid{", ".pvphone{", ".pvplay{", ".pvbar{", ".wctl{", ".chips button.on{", ".pvtext{", ".pvknob{", "#osBox{", "#osText{", ".wrow.os select{"):
        line = next((x for x in sty.splitlines() if x.startswith(rule)), None)
        case("her style rule %s is in the page as she wrote it" % rule, line is not None and line.split("}")[0] + "}" in R.WATCH_CSS, line)


# ---------- 2. reel.py's status ----------

def check_status(run):
    photos = run / "status-photos"
    photos.mkdir(parents=True, exist_ok=True)
    for n in range(1, 7):
        rpc.tiny_jpeg(photos / ("p%d.jpg" % n), 1200, 1600)
    status = run / "status.json"
    work = run / "status-work"
    env = dict(os.environ, STUDIO_HOME=str(run / "status-home"))
    cmd = [sys.executable, str(REEL / "reel.py"), "make", "--dry-run", "--folder", str(photos), "--shoot", "Pretend", "--picks", "2,5+,1,3-",
           "--song", str(rpc.BEAT60), "--status", str(status), "--work", str(work)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)
    st = json.loads(status.read_text()) if status.exists() else {}
    case("reel.py make --dry-run --status: ok, and the pieces as the page plays them, a photo by its number in play order",
         r.returncode == 0 and st.get("ok") and st.get("dry") and [p.get("n") for p in st.get("pieces", [])] == [2, 5, 1, 3]
         and all(p["kind"] == "photo" for p in st["pieces"]), (r.returncode, st, r.stdout[-300:]))
    ps = st.get("pieces") or []
    case("each piece has its start and length, they run on from 0 and add up to the plan's length, and the song's start and length are there",
         ps and ps[0]["start"] == 0 and all(abs(ps[k]["start"] - (ps[k - 1]["start"] + ps[k - 1]["dur"])) < 0.001 for k in range(1, len(ps)))
         and abs(ps[-1]["start"] + ps[-1]["dur"] - st["plan"]["length"]) < 0.001 and st.get("song", {}).get("length") == 60.0
         and isinstance(st["song"].get("from"), (int, float)) and st.get("variation") == 0, st)
    case("no path in the status (the photos by number only)", no_path(st) and not any("file" in p or "path" in p for p in ps), st)
    case("the working folder was --work (reel.json there), not the studio's", (work / "reel.json").is_file() and not (run / "status-home" / "reels").exists())
    # a reel of clips only (B-roll) with --hook-whole: the words over the whole reel
    clips = run / "status-clips.json"
    vid = str(run / "pretend.mov")
    clips.write_text(json.dumps([{"path": vid, "src": 1.0, "seconds": 4.0, "w": 1080, "h": 1920, "length": 20.0},
                                 {"path": vid, "src": 6.0, "seconds": 3.0, "w": 1080, "h": 1920, "length": 20.0},
                                 {"path": vid, "src": 10.0, "seconds": 5.0, "w": 1080, "h": 1920, "length": 20.0}]))
    r = subprocess.run([sys.executable, str(REEL / "reel.py"), "make", "--dry-run", "--folder", str(photos), "--shoot", "Pretend", "--picks", "c1,c2,c3",
                        "--song", str(rpc.BEAT60), "--status", str(status), "--work", str(work), "--clips", str(clips), "--variation", "2",
                        "--hook", "the  words  on   screen", "--hook-whole"], capture_output=True, text=True, env=env, timeout=180)
    st = json.loads(status.read_text()) if status.exists() else {}
    beats = next((x for x in r.stdout.splitlines() if x.startswith("Beats per piece")), "")
    case("a reel of clips only (B-roll: c1,c2,c3, no photo numbers) is planned, every piece a clip with its c and src, the mix noted",
         r.returncode == 0 and st.get("ok") and [(p["kind"], p["c"], p["src"]) for p in st.get("pieces", [])] == [("clip", 1, 1.0), ("clip", 2, 6.0), ("clip", 3, 10.0)]
         and re.fullmatch(r"Beats per piece: clip \d+, clip \d+, clip \d+", beats) and st.get("variation") == 2, (r.returncode, beats, st, r.stdout[-300:]))
    plan = json.loads((work / "reel.json").read_text())["plan"]
    case("--hook-whole: the words stay on for the whole reel (dur = the plan's length, in frames too)",
         plan["hook"]["text"] == "the  words  on   screen" and abs(plan["hook"]["dur"] - st["plan"]["length"]) < 1e-6
         and plan["hook"]["dur_f"] == sum(p["dur_f"] for p in plan["photos"]), plan.get("hook"))
    r = subprocess.run([sys.executable, str(REEL / "reel.py"), "make", "--dry-run", "--folder", str(photos), "--shoot", "Pretend", "--picks", "c1,2",
                        "--song", "none", "--work", str(work), "--clips", str(clips), "--hook", "Hi"], capture_output=True, text=True, env=env, timeout=180)
    case("--hook without --hook-whole still puts the words on the first piece only (c2 and c3 left out of --picks: her STOP)",
         r.returncode == 2 and "isn't in --picks" in r.stdout, r.stdout[-200:])
    clips.write_text(json.dumps([{"path": vid, "src": 1.0, "seconds": 4.0, "w": 1080, "h": 1920, "length": 20.0}]))
    r = subprocess.run([sys.executable, str(REEL / "reel.py"), "make", "--dry-run", "--folder", str(photos), "--shoot", "Pretend", "--picks", "c1,2,4",
                        "--song", "none", "--work", str(work), "--clips", str(clips), "--hook", "Hi"], capture_output=True, text=True, env=env, timeout=180)
    plan = json.loads((work / "reel.json").read_text())["plan"]
    case("...the first piece's length, as before", r.returncode == 0 and plan["hook"]["dur"] == plan["photos"][0]["dur"] and plan["hook"]["dur_f"] == plan["photos"][0]["dur_f"], plan.get("hook"))


# ---------- 3. the preview on the server, and the make that carries the mix ----------

def check_preview(s):
    R = rp()
    st = s.state()
    music = s.kit / "Music"
    music.mkdir(exist_ok=True)
    if not (music / "Test beat.wav").exists():
        shutil.copy(rpc.BEAT60, music / "Test beat.wav")
    sid = rpc.song_of(s, KIT, "Test beat")
    case("(set up: the test beat in Music)", bool(sid), sid)
    before = (s.kit / ".kit" / "reel-page.json").read_bytes() if (s.kit / ".kit" / "reel-page.json").exists() else b""
    reels_before = sorted(os.listdir(s.kit / ".kit" / "reels")) if (s.kit / ".kit" / "reels").exists() else None
    page_picks = rpc.pk(PICKS)
    code, j, _ = preview(s, {"picks": page_picks, "song": sid, "vibe": "beat"})
    ps = (j or {}).get("pieces") or []
    case("POST /reel-preview answers ok, the pieces (one per photo, by number, in play order), the length and the song",
         code == 200 and j["ok"] and [p["n"] for p in ps] == [3, 1, 7, 4, 12, 9, 2, 10] and all(p["kind"] == "photo" for p in ps)
         and isinstance(j.get("length"), (int, float)) and j["song"]["id"] == sid and j["song"]["length"] == 60.0, (code, j))
    case("the pieces' starts add up to the plan's length", ps and ps[0]["start"] == 0 and abs(ps[-1]["start"] + ps[-1]["dur"] - j["length"]) < 0.001, ps)
    case("photos by number only: no path, no file name in the answer", no_path(j) and not re.search(r"\.jpe?g|\.png", json.dumps(j), re.I), j)
    case("her Plan line is among the words, and the mix is 0", any(w.startswith("Plan: 8 photos, ") for w in j["words"]) and j["variation"] == 0, j["words"])
    case("the preview wrote nothing to the record and nothing into Make my reel's folder; its own folder is beside it",
         ((s.kit / ".kit" / "reel-page.json").read_bytes() if (s.kit / ".kit" / "reel-page.json").exists() else b"") == before
         and (sorted(os.listdir(s.kit / ".kit" / "reels")) if (s.kit / ".kit" / "reels").exists() else None) == reels_before
         and (s.kit / ".kit" / R.PREVIEW_WORK / "reel.json").is_file())
    durs0 = [p["dur"] for p in ps]
    from0 = j["song"]["from"]
    code, j2, _ = preview(s, {"picks": page_picks, "song": sid, "vibe": "beat", "variation": 1})
    case("Try another mix (variation 1): a plan again, the mix said back", code == 200 and j2["ok"] and j2["variation"] == 1 and len(j2["pieces"]) == 8, (code, j2))
    # the mixes: A little of everything has room to differ (On every beat on an even test beat may land the same)
    mixes = []
    for v in range(4):
        code, jx, _ = preview(s, {"picks": page_picks, "song": sid, "vibe": "mixed", "variation": v})
        mixes.append([p["dur"] for p in (jx or {}).get("pieces", [])] if code == 200 and jx.get("ok") else None)
    case("four mixes of A little of everything: each a plan of 8, and not all the same holds", all(m and len(m) == 8 for m in mixes) and len({tuple(m) for m in mixes}) > 1, mixes)
    code, j3, _ = preview(s, {"picks": page_picks, "song": sid, "vibe": "beat", "song_start": from0 + 12.0})
    case("Another part of this song (song_start 12 s on): the song starts at or after what was asked, on a beat",
         code == 200 and j3["ok"] and j3["song"]["from"] >= from0 + 12.0 - 0.03 and j3["song"]["from"] < from0 + 12.0 + 3.0, (code, j3.get("song")))
    code, j4, _ = preview(s, {"picks": page_picks, "song": sid, "vibe": "beat", "song_start": j3["song"]["from"]})
    case("the watched start sent back gives the same start again (what plays is what is made)", code == 200 and j4["ok"] and j4["song"]["from"] == j3["song"]["from"], (j3.get("song"), j4.get("song")))
    code, j5, _ = preview(s, {"picks": page_picks, "song": sid, "vibe": "beat", "song_start": 59.5})
    case("a start past the song's end is refused in plain words (ours)", code == 200 and j5["ok"] is False and j5["problem"] == R.OUR_WORDS["song_start_past"], (code, j5))
    code, j6, _ = preview(s, {"picks": page_picks, "song": None, "vibe": "beat"})
    case("no song picked yet: the preview plays with no song (hers), the song null", code == 200 and j6["ok"] and j6["song"] is None and j6["pieces"], (code, j6))
    code, j7, _ = preview(s, {"picks": page_picks, "song": sid, "vibe": "calm"})
    case("Calm: a longer reel than On every beat", code == 200 and j7["ok"] and j7["length"] > j["length"], (j7.get("length"), j.get("length")))
    for name, body, want, words in (
            ("no photos (a photos reel)", {"picks": [], "song": sid, "vibe": "beat"}, 400, R.WORDS["pick_photos"]),
            ("a mix as words", {"picks": page_picks, "song": sid, "vibe": "beat", "variation": "2"}, 400, None),
            ("a mix below 0", {"picks": page_picks, "song": sid, "vibe": "beat", "variation": -1}, 400, None),
            ("a start as words", {"picks": page_picks, "song": sid, "vibe": "beat", "song_start": "12"}, 400, None),
            ("a vibe that isn't hers", {"picks": page_picks, "song": sid, "vibe": "fast"}, 400, R.WORDS["pick_vibe"]),
            ("a song by its path", {"picks": page_picks, "song": "Music/Test beat.wav", "vibe": "beat"}, 400, None),
            ("a field it doesn't know", {"picks": page_picks, "song": sid, "vibe": "beat", "test": True}, 400, None),
            ("a numbered list from before", {"picks": page_picks, "song": sid, "vibe": "beat", "stamp": "old"}, 409, None),
            ("another reel", {"picks": page_picks, "song": sid, "vibe": "beat", "reel": "v9"}, 409, None)):
        code, jb, _ = preview(s, body)
        case("the preview refuses %s" % name, code == want and jb and jb.get("ok") is False and (words is None or jb.get("words") == words), (code, jb))
    case("the preview refuses another Origin", s.http("POST", "/reel-preview", {"kit": KIT, "stamp": st["stamp"], "picks": page_picks, "song": sid, "vibe": "beat"},
                                                        headers={"Origin": "http://evil.example"})[0] == 403)
    # Make my reel carries the mix and the start that were watched
    body = {"kit": KIT, "stamp": st["stamp"], "picks": page_picks, "song": sid, "vibe": "beat", "test": True, "variation": 2, "song_start": j3["song"]["from"]}
    code, jm, _ = s.http("POST", "/reel-make", body)
    jid = (jm or {}).get("job", {}).get("id")
    job = None
    end = time.time() + 120
    while jid and time.time() < end:
        _, jj, _ = s.http("GET", "/reel-job?kit=%s&id=%s" % (KQ, jid))
        job = (jj or {}).get("job")
        if job and job["state"] in ("done", "problem"):
            break
        time.sleep(0.3)
    jrec = json.loads((s.kit / ".kit" / "reel-job.json").read_text())
    stj = json.loads((s.kit / ".kit" / "reel-job-status.json").read_text())
    case("Make my reel (a test run) with variation 2 and the watched start: the job's ask carries them, reel.py got them (the status JSON says mix 2 and that start)",
         code == 200 and job and job["state"] == "done" and jrec["ask"].get("variation") == 2 and jrec["ask"].get("song_start") == j3["song"]["from"]
         and stj.get("variation") == 2 and stj.get("song", {}).get("from") == j3["song"]["from"], (code, jrec.get("ask"), stj.get("variation"), stj.get("song")))
    _, jm2, _ = s.http("POST", "/reel-make", dict(body, song_start=59.5))
    jid2 = (jm2 or {}).get("job", {}).get("id")
    job2 = None
    end = time.time() + 60
    while jid2 and time.time() < end:
        _, jj, _ = s.http("GET", "/reel-job?kit=%s&id=%s" % (KQ, jid2))
        job2 = (jj or {}).get("job")
        if job2 and job2["state"] in ("done", "problem"):
            break
        time.sleep(0.3)
    case("...and a start past the song's end stops the job in the same plain words", job2 and job2["state"] == "problem" and job2["problem"] == R.OUR_WORDS["song_start_past"], job2)
    for name, extra in (("a mix as words", {"variation": "2"}), ("a start as words", {"song_start": "1"}), ("a mix past the most", {"variation": 1000})):
        code, jb, _ = s.http("POST", "/reel-make", dict(body, **extra))
        case("Make my reel refuses %s" % name, code == 400 and jb.get("ok") is False, (code, jb))
    # the chat's make takes them too
    code, jsv, _ = s.http("POST", "/reel-save", rpc.save_body(s.state(), {"picks": page_picks, "mine": True, "song": sid, "vibe": "beat", "kind": "photos"}, page="watch0"))
    rc, out = s.cmd("reel_page.py", "make", KIT, "--dry-run", "--variation", "3", "--song-start", "%.3f" % j3["song"]["from"])
    stj = json.loads((s.kit / ".kit" / "reel-job-status.json").read_text())
    case("reel_page.py make --variation 3 --song-start: the dry run says its Plan, and reel.py got mix 3 and that start",
         rc == 0 and "Plan: 8 photos" in out and stj.get("variation") == 3 and stj.get("song", {}).get("from") == j3["song"]["from"], (rc, out[-200:], stj.get("variation")))
    rc, out = s.cmd("reel_page.py", "make", KIT, "--dry-run", "--variation", "-1")
    case("reel_page.py make --variation -1 stops in plain words", rc == 1 and "STOP: --variation" in out, out[-200:])
    # a real make (CapCut's pretend folder): the made entry notes the mix and the start
    code, jm3, _ = s.http("POST", "/reel-make", dict(body, test=False, variation=1))
    jid3 = (jm3 or {}).get("job", {}).get("id")
    job3 = None
    end = time.time() + 120
    while jid3 and time.time() < end:
        _, jj, _ = s.http("GET", "/reel-job?kit=%s&id=%s" % (KQ, jid3))
        job3 = (jj or {}).get("job")
        if job3 and job3["state"] in ("done", "problem"):
            break
        time.sleep(0.3)
    made = (record(s).get("made") or [])
    case("a reel made with the watched mix and start: the made entry notes variation 1 and where the song started",
         job3 and job3["state"] == "done" and job3.get("project") and made and made[-1].get("variation") == 1 and made[-1].get("song_start") == j3["song"]["from"]
         and made[-1].get("project") == job3["project"], (job3, made[-1:] if made else made))
    rc, out = s.cmd("reel_page.py", "show", KIT)
    case("reel_page.py show says the newest reel's mix and where its song started", "(mix 2, the song from %.1f s)" % j3["song"]["from"] in out, out[-400:])


# ---------- 4. direct this edit ----------

def check_direct(s, clips):
    R = rp()
    st = s.state()
    code, j, _ = s.http("POST", "/reel-save", rpc.save_body(st, {"direct": "x" * R.DIRECT_MAX}, page="direct1"))
    case("direct saved at its longest (%d)" % R.DIRECT_MAX, code == 200 and j["ok"] and (s.state()["saved"] or {}).get("direct") == "x" * R.DIRECT_MAX, (code, j))
    code, j, _ = s.http("POST", "/reel-save", rpc.save_body(s.state(), {"direct": "x" * (R.DIRECT_MAX + 1)}, page="direct1"))
    case("one more character refused, nothing written", code == 400 and j["ok"] is False and (s.state()["saved"] or {}).get("direct") == "x" * R.DIRECT_MAX, (code, j))
    code, j, _ = s.http("POST", "/reel-save", rpc.save_body(s.state(), {"direct": 12}, page="direct1"))
    case("direct as a number refused", code == 400, (code, j))
    note = "Start with the clip of the stove, then the photos of the cake, then the dancing."
    code, j, _ = s.http("POST", "/reel-save", rpc.save_body(s.state(), {"direct": note, "footage": True, "style": "first", "kind": "bts"}, page="direct1"))
    rc, out = s.cmd("reel_page.py", "show", KIT)
    case("reel_page.py show prints their direction", rc == 0 and "Their direction for how this reel should go" in out and note in out, out[-400:])
    rc, out = s.cmd("reel_page.py", "note", KIT)
    case("reel_page.py note prints it too", rc == 0 and note in out, out[-400:])
    for kind in ("bts", "photos", "broll"):      # a reel's own kind wins over the address (stage 2), so each kind's page is read on a reel of that kind
        rc, out = s.cmd("reel_page.py", "reels", KIT, "--new", "--name", "Kind " + kind, "--kind", kind)
        code, _j, raw = s.http("GET", "/reel.html?kit=%s&kind=%s" % (KQ, kind))
        pg = raw.decode("utf-8", "replace")
        m = re.search(r"<section class='step' id='stepDirect'([^>]*)>", pg)
        case("%s: the direct step is %s" % (kind, "hidden" if kind == "broll" else "shown"), rc == 0 and bool(m) and (("data-kind-hidden" in m.group(1)) == (kind == "broll")), (rc, m and m.group(1)))
    rc, out = s.cmd("reel_page.py", "reels", KIT, "--open", "Reel 1")
    # the command: the style, the clips and the order in one go
    rec = record(s)
    a = next(v for v in rfc.foot(s)[1]["videos"] if v["name"] == "clip.mov")
    b = next(v for v in rfc.foot(s)[1]["videos"] if v["name"] == "Sideways é.mov")
    ms = [{"id": "m1-aaaaaa", "video": "Footage/clip.mov", "start": 0.5, "end": 3.5, "label": "The stove", "photo": 5, "keep": True},
          {"id": "m2-bbbbbb", "video": "Footage/Sideways é.mov", "start": 1.0, "end": 4.0, "label": "The cake", "photo": None, "keep": True},
          {"id": "u1-cccccc", "video": "Footage/clip.mov", "start": 2.0, "end": 5.0, "label": "Dancing", "photo": None, "keep": True, "by": "you", "named": True}]
    rec["moments"] = ms
    write_record(s, rec)
    case("(set up: three clips in the reel, two videos ready)", a and b and len(R.moments_of(record(s))) == 3)
    rev0 = int(record(s).get("rev") or 0)
    rc, out = s.cmd("reel_page.py", "direct", KIT, "--style", "backforth", "--clips", "u1-cccccc", "m1-aaaaaa", "--order", "7+,2,11-,4")
    st = s.state()
    sv = st["saved"] or {}
    case("reel_page.py direct: the style, the clips in play order and the order, in one go; the page is set to follow the assistant's order",
         rc == 0 and sv.get("style") == "backforth" and sv.get("sel", {}).get("backforth") == ["u1-cccccc", "m1-aaaaaa"] and sv.get("mine") is False
         and [str(x["n"]) + x["h"] for x in st["claude"]] == ["7+", "2", "11-", "4"] and "Set up" in out and "Back and forth" in out, (rc, out, sv.get("style"), sv.get("sel"), st["claude"]))
    rev1 = int(record(s).get("rev") or 0)
    case("the rev moved on (an open page redraws), the version before kept", rev1 > rev0 and (s.kit / ".kit" / "reel-page.prev.json").exists(), (rev0, rev1))
    bytes1 = (s.kit / ".kit" / "reel-page.json").read_bytes()
    kit1 = (s.kit / ".kit" / "kit.json").read_bytes()
    rc, out = s.cmd("reel_page.py", "direct", KIT, "--style", "backforth", "--clips", "u1-cccccc", "m1-aaaaaa", "--order", "7+,2,11-,4")
    case("run twice: writes nothing (the record and kit.json byte for byte), and says so",
         rc == 0 and (s.kit / ".kit" / "reel-page.json").read_bytes() == bytes1 and (s.kit / ".kit" / "kit.json").read_bytes() == kit1 and "nothing written" in out, (rc, out))
    for name, args, words in (
            ("an unknown clip", ["--clips", "m9-zzzzzz"], "no clip \"m9-zzzzzz\""),
            ("a clip twice", ["--clips", "m1-aaaaaa", "m1-aaaaaa"], "named twice"),
            ("a 3rd clip for Bookends", ["--style", "bookends", "--clips", "m1-aaaaaa", "m2-bbbbbb", "u1-cccccc"], "uses at most 2 clips"),
            ("a style she hasn't got", ["--style", "sideways"], "no style called"),
            ("a photo not on the sheet", ["--order", "7,99"], "no photo numbered 99"),
            ("a photo twice", ["--order", "7,7"], "in that order twice"),
            ("nothing to set up", [], "say what to set up")):
        rc, out = s.cmd("reel_page.py", "direct", KIT, *args)
        case("direct refuses %s, in plain words, writing nothing" % name, rc == 1 and "STOP" in out and words in out and (s.kit / ".kit" / "reel-page.json").read_bytes() == bytes1, (rc, out[-200:]))
    # a second reel: its clips are its own
    rc, out = s.cmd("reel_page.py", "reels", KIT, "--new", "--name", "Second", "--kind", "bts")
    case("(set up: a second reel, Second)", rc == 0, out[-200:])
    rec = record(s)
    rec["moments"] = rec["moments"] + [{"id": "u9-999999", "video": "Footage/clip.mov", "start": 0.0, "end": 2.0, "label": "Only in Second", "photo": None, "keep": True, "by": "you"}]
    write_record(s, rec)
    rc, out = s.cmd("reel_page.py", "direct", KIT, "--reel", "Reel 1", "--clips", "u9-999999")
    case("direct for a reel that doesn't hold that clip refuses it (each reel's clips are its own)", rc == 1 and "no clip \"u9-999999\"" in out, out[-200:])
    rc, out = s.cmd("reel_page.py", "direct", KIT, "--reel", "Reel 1", "--style", "first", "--clips", "m2-bbbbbb")
    case("direct --reel \"Reel 1\" sets up the first reel while Second is open", rc == 0 and "Set up \"Reel 1\"" in out, out[-200:])
    rc, out = s.cmd("reel_page.py", "reels", KIT, "--open", "Reel 1")
    sv = s.state()["saved"] or {}
    case("...and Reel 1, opened again, has Moment first with that clip (Second untouched)", rc == 0 and sv.get("style") == "first" and sv.get("sel", {}).get("first") == ["m2-bbbbbb"], sv)
    rc, out = s.cmd("reel_page.py", "reels", KIT, "--open", "Kind broll")
    rc, out = s.cmd("reel_page.py", "direct", KIT, "--style", "first")
    case("direct on a B-roll reel is refused (her v27: no direction there)", rc == 1 and "B-roll reel" in out, out[-200:])
    rc, out = s.cmd("reel_page.py", "reels", KIT, "--rename", "Kind broll", "--to", "Broll one")
    rc, out = s.cmd("reel_page.py", "reels", KIT, "--open", "Reel 1")


# ---------- 5. B-roll on the server ----------

def wait_job(s, jid, seconds=120):
    end = time.time() + seconds
    while time.time() < end:
        _, jj, _ = s.http("GET", "/reel-job?kit=%s&id=%s" % (KQ, jid))
        job = (jj or {}).get("job")
        if job and job["state"] in ("done", "problem"):
            return job
        time.sleep(0.3)
    return None


def check_broll(s):
    R = rp()
    rc, out = s.cmd("reel_page.py", "reels", KIT, "--open", "Broll one")
    case("(set up: the B-roll reel open)", rc == 0, out[-200:])
    rec = record(s)
    rec["moments"] = [{"id": "u1-111111", "video": "Footage/clip.mov", "start": 0.5, "end": 4.5, "label": "One", "photo": None, "keep": True, "by": "you", "named": True},
                      {"id": "u2-222222", "video": "Footage/Sideways é.mov", "start": 1.0, "end": 4.0, "label": "Two", "photo": None, "keep": True, "by": "you", "named": True},
                      {"id": "u3-333333", "video": "Footage/clip.mov", "start": 2.0, "end": 5.5, "label": "Three", "photo": None, "keep": True, "by": "you", "named": True}]
    write_record(s, rec)
    sid = rpc.song_of(s, KIT, "Test beat")
    st = s.state()
    ids = ["u1-111111", "u2-222222", "u3-333333"]
    body = {"kit": KIT, "stamp": st["stamp"], "picks": [], "song": sid, "vibe": "beat", "test": True, "footage": True, "style": "broll", "clips": ids}
    code, j, _ = s.http("POST", "/reel-make", body)
    job = wait_job(s, (j or {}).get("job", {}).get("id"))
    beats = rpc.beats_of(job)
    case("a B-roll make (three clips, no photos) builds the plan: her Plan line with 3 clips and 0 photos, Beats per piece: clip N, clip N, clip N",
         code == 200 and job and job["state"] == "done" and re.fullmatch(r"Beats per piece: clip \d+, clip \d+, clip \d+", beats or "")
         and any(w.startswith("Plan: 3 clips and 0 photos") for w in job["words"]), (code, job))
    case("no path in what the page is told", no_path(job), job)
    code, jp, _ = preview(s, {"picks": [], "song": sid, "vibe": "beat", "footage": True, "style": "broll", "clips": ids})
    case("the preview of a B-roll reel: three clip pieces, each by its video's key, its id and where it starts, no photos",
         code == 200 and jp["ok"] and [p["kind"] for p in jp["pieces"]] == ["clip"] * 3 and [p["id"] for p in jp["pieces"]] == ids
         and all(re.fullmatch(r"[0-9a-f]{12}", p["key"] or "") for p in jp["pieces"]) and [p["src"] for p in jp["pieces"]] == [0.5, 1.0, 2.0] and no_path(jp), (code, jp))
    code, jb, _ = s.http("POST", "/reel-make", dict(body, footage=False, style="first"))
    case("a photos reel still refuses an empty pick", code == 400 and jb["words"] == R.WORDS["pick_photos"], (code, jb))
    code, jb, _ = s.http("POST", "/reel-make", dict(body, style="first", picks=[]))
    case("Moment first with no photos is refused too (only B-roll needs none)", code == 400 and jb["words"] == R.WORDS["pick_photos"], (code, jb))
    # the words on screen, saved field by field
    good = {"text": "Golden hour at the barn", "font": "georgia", "style": "whitebox", "pos": "custom", "x": 0.31, "y": 0.72, "size": 1.4, "hold": "all"}
    code, j, _ = s.http("POST", "/reel-save", rpc.save_body(s.state(), {"onscreen": good, "kind": "broll"}, page="broll1"))
    sv = s.state()["saved"] or {}
    case("onscreen saved: the words, the font, the style, x, y and size as numbers", code == 200 and j["ok"] and sv.get("onscreen") == good, (code, j, sv.get("onscreen")))
    for name, bad in (("x as a string", dict(good, x="0.31")), ("x out of her bounds", dict(good, x=0.9)), ("y out of bounds", dict(good, y=0.01)),
                      ("a size of 3", dict(good, size=3)), ("a size that is true", dict(good, size=True)), ("a font that isn't hers", dict(good, font="comic")),
                      ("a style that isn't hers", dict(good, style="red")), ("a place that isn't custom", dict(good, pos="top")), ("words over 300", dict(good, text="w" * 301)),
                      ("a field it doesn't know", dict(good, colour="red")), ("not a dict", "words")):
        code, j, _ = s.http("POST", "/reel-save", rpc.save_body(s.state(), {"onscreen": bad}, page="broll1"))
        case("onscreen refuses %s, nothing written" % name, code == 400 and j["ok"] is False and (s.state()["saved"] or {}).get("onscreen") == good, (code, j))
    # a real B-roll make: the project in CapCut's pretend folder carries the words for the whole reel
    code, j, _ = s.http("POST", "/reel-make", dict(body, test=False, stamp=s.state()["stamp"]))
    job = wait_job(s, (j or {}).get("job", {}).get("id"))
    case("a B-roll reel made: It's in CapCut, a project", job and job["state"] == "done" and job.get("project"), job)
    made = record(s).get("made") or []
    mine = [m for m in made if m.get("project") == (job or {}).get("project")]
    case("the made entry: footage broll, no picks, the clips, the reel's version", mine and mine[-1].get("footage") == "broll" and mine[-1].get("picks") == ""
         and mine[-1].get("clips") == ids and mine[-1].get("version") == s.state()["current"], mine[-1:] or made[-1:])
    draft = None
    for d in s.store.iterdir():
        if d.is_dir() and d.name == (job or {}).get("project"):
            for name in ("draft_info.json", "draft_content.json"):
                if (d / name).exists():
                    draft = json.loads((d / name).read_text(encoding="utf-8"))
    tracks = (draft or {}).get("tracks") or []
    vtrack = next((t for t in tracks if t.get("type") == "video"), {})
    ttrack = next((t for t in tracks if t.get("type") == "text"), {})
    end_us = max((sg["target_timerange"]["start"] + sg["target_timerange"]["duration"] for sg in vtrack.get("segments", [])), default=0)
    texts = {t["id"]: t for t in (draft or {}).get("materials", {}).get("texts", [])}
    seg = (ttrack.get("segments") or [{}])[0]
    tm = texts.get(seg.get("material_id"), {})
    content = json.loads(tm.get("content") or "{}")
    case("the project: three clips on the video track, and a text layer with the words for the whole length (start 0, duration = the reel's end)",
         draft is not None and len(vtrack.get("segments", [])) == 3 and ttrack and seg.get("target_timerange") == {"start": 0, "duration": end_us} and end_us > 0
         and content.get("text") == "Golden hour at the barn", (bool(draft), len(vtrack.get("segments", [])), seg.get("target_timerange"), end_us, content.get("text")))
    rc, out = s.cmd("reel_page.py", "show", KIT)
    case("reel_page.py show: B-roll (clips only), 3 clips, the words on screen", "Footage: yes, B-roll (clips only, no photos), 3 clips selected" in out
         and 'Words on screen (B-roll): "Golden hour at the barn", Georgia, White text on black' in out, out[-600:])
    code, j, _ = s.http("POST", "/reel-save", rpc.save_body(s.state(), {"song": sid, "vibe": "beat"}, page="broll1"))
    rc, out = s.cmd("reel_page.py", "make", KIT, "--dry-run")
    case("the chat's make of a B-roll reel: no order needed, her Plan line with 3 clips", rc == 0 and "Plan: 3 clips and 0 photos" in out, out[-300:])
    r = subprocess.run([sys.executable, str(HERE / "capcut_even.py")], capture_output=True, text=True, timeout=300)
    case("tests/capcut_even.py: today's eight kept projects are byte for byte the same, and the short clip's", r.returncode == 0 and "the same (8 projects)" in r.stdout, r.stdout[-200:])

    # Save my video (her v27, section 4; A15): the finished MP4 with the song and the words, in the shoot's Reels folder
    short = R.short_name(KIT)
    good2 = {"text": "Golden hour at the barn", "font": "georgia", "style": "whitebox", "pos": "custom", "x": 0.5, "y": 0.6, "size": 1.0, "hold": "all"}
    st = s.state()
    vbody = {"kit": KIT, "stamp": st["stamp"], "song": sid, "clips": ids, "variation": 0, "onscreen": good2}
    code, j, _ = s.http("POST", "/reel-video", vbody)
    job = wait_job(s, (j or {}).get("job", {}).get("id")) if code == 200 and (j or {}).get("job") else None
    name = "%s B-roll - Broll one.mp4" % short
    vfile = s.kit / "Reels" / name
    case("POST /reel-video starts a job the page follows (kind video), and it finishes: Saved \"<short> B-roll - <reel name>.mp4\" (several reels), its length",
         code == 200 and j["ok"] and j["job"]["kind"] == "video" and job and job["state"] == "done" and job.get("kind") == "video" and job.get("video") == name
         and isinstance(job.get("seconds"), (int, float)) and job["seconds"] > 5, (code, j, job))
    case("no path in the job's answer", no_path(job or {}), job)
    f = V().facts(vfile) if vfile.is_file() else {}
    case("the file is in <shoot>/Reels: 1080 x 1920, 30 a second, with sound, as long as the job says",
         vfile.is_file() and (f.get("w"), f.get("h")) == (1080, 1920) and f.get("has_audio") and abs(f.get("length", 0) - (job or {}).get("seconds", -1)) < 0.001, f)
    case("...and nothing else in the Reels folder (no half-made file, no plan file)", sorted(p.name for p in (s.kit / "Reels").iterdir()) == [name], sorted(p.name for p in (s.kit / "Reels").iterdir()))
    rec = record(s)
    vm = [m for m in rec.get("made") or [] if m.get("video")]
    case("the made entry: video (the file name), footage broll, the clips, no picks, the reel's version, the song and its start, the mix (Lane D's contract)",
         vm and vm[-1]["video"] == name and vm[-1]["footage"] == "broll" and vm[-1]["clips"] == ids and vm[-1]["picks"] == "" and vm[-1]["version"] == st["current"]
         and vm[-1]["song_id"] == sid and isinstance(vm[-1].get("song_start"), (int, float)) and vm[-1]["variation"] == 0 and no_path(vm[-1]), vm[-1:])
    ks = {v["id"]: v for v in R.reels_for_kit(s.kit)}
    case("reels_for_kit: this reel is made, with its video's file name (the post kit and the queue show a saved video as made)",
         ks.get(st["current"], {}).get("made") and ks[st["current"]].get("video") == name and ks[st["current"]].get("kind") == "broll", ks.get(st["current"]))
    case("GET /reel-state says it is made too", s.state()["made"].get(st["current"]) is True, s.state()["made"])
    rc, out = s.cmd("reel_page.py", "show", KIT)
    case("reel_page.py show: Videos saved from the page, the newest by name", rc == 0 and 'Videos saved from the page (Save my video, in this shoot\'s Reels folder): 1, the newest "%s"' % name in out, out[-400:])
    code, j, _ = s.http("POST", "/reel-video", dict(vbody, stamp=s.state()["stamp"]))
    job2 = wait_job(s, (j or {}).get("job", {}).get("id")) if code == 200 and (j or {}).get("job") else None
    name2 = "%s B-roll - Broll one 2.mp4" % short
    case("a second save never writes over the first: \"... 2.mp4\", both files there", job2 and job2.get("video") == name2 and (s.kit / "Reels" / name2).is_file() and vfile.is_file()
         and len([m for m in record(s).get("made") or [] if m.get("video")]) == 2, job2)
    code, j, _ = s.http("POST", "/reel-open", {"kit": KIT, "what": "reels"})
    case("Open the folder (POST /reel-open what reels): opens the shoot's Reels folder and says so (nothing opened in a test)",
         code == 200 and j["ok"] and j["words"].startswith(R.OUR_WORDS["reels_open"].rstrip(".")), (code, j))
    code, j, _ = s.http("POST", "/reel-video", dict(vbody, stamp=s.state()["stamp"], clips=[]))
    case("no clips: her line, no job", code == 400 and j["words"] == R.VIDEO_WORDS["no_clips"], (code, j))
    code, j, _ = s.http("POST", "/reel-video", dict(vbody, stamp=s.state()["stamp"], onscreen=dict(good2, x="0.5")))
    case("words on screen that fail the check (x as text): refused, no job", code == 400 and j["ok"] is False, (code, j))
    code, j, _ = s.http("POST", "/reel-video", dict(vbody, stamp=s.state()["stamp"], colour="red"))
    case("a field it doesn't know: refused", code == 400, (code, j))
    code, j, _ = s.http("POST", "/reel-video", dict(vbody, stamp="old"))
    case("a stale list (stamp): refused with our photos-changed line", code == 409 and j.get("why") == "photos", (code, j))
    case("(the Reels folder still holds the two videos only)", sorted(p.name for p in (s.kit / "Reels").iterdir()) == sorted([name, name2]))
    s.cmd("reel_page.py", "reels", KIT, "--open", "Reel 1")
    s.http("POST", "/reel-save", rpc.save_body(s.state(), {"kind": "photos", "picks": rpc.pk(PICKS), "mine": True, "song": sid, "vibe": "beat", "footage": False}, page="broll9"))
    code, j, _ = s.http("POST", "/reel-video", dict(vbody, stamp=s.state()["stamp"]))
    case("a reel of another kind (Just photos) can't be saved as a video: our line, no job", code == 400 and j["words"] == R.OUR_WORDS["video_broll_only"], (code, j))
    s.cmd("reel_page.py", "reels", KIT, "--open", "Broll one")
    # a PC: the named gap, nothing started
    s.stop()
    s.start(ASSISTANT_NO_AVFOUNDATION="1")
    try:
        code, j, _ = s.http("POST", "/reel-video", dict(vbody, stamp=s.state()["stamp"]))
        case("on a PC (ASSISTANT_NO_AVFOUNDATION=1): this_computer.NO_VIDEO_PC, no job started, nothing made",
             code == 200 and j["ok"] is False and j.get("pc") is True and j["words"] == rp().this_computer.NO_VIDEO_PC and (s.state()["job"] or {}).get("id") == (job2 or {}).get("id")
             and sorted(p.name for p in (s.kit / "Reels").iterdir()) == sorted([name, name2]), (code, j))
    finally:
        s.stop()
        s.start()


# ---------- 6. the page ----------

def pv(c):
    return c.js("""({words: document.getElementById('pvWords').textContent, mix: document.getElementById('pvMixSay').textContent,
                   empty: document.getElementById('pvEmpty').hidden, emptyText: document.getElementById('pvEmpty').textContent,
                   undo: document.getElementById('pvUndo').disabled, redo: document.getElementById('pvRedo').disabled,
                   song: document.getElementById('pvSong').value, vibe: (document.querySelector('[data-pv-vibe].on') || {}).dataset ? (document.querySelector('[data-pv-vibe].on') || {dataset: {}}).dataset.pvVibe : null,
                   img: !document.getElementById('pvImg').hidden && document.getElementById('pvImg').getAttribute('src'),
                   sum: document.getElementById('sum').textContent, makeOff: document.getElementById('makeBtn').disabled,
                   style: (document.querySelector('[data-pv-style].on') || {dataset: {}}).dataset.pvStyle || null})""")


def check_page(c, s):
    R = rp()
    W = dict(R.WATCH_WORDS, **R.DIRECT_WORDS)
    rc, out = s.cmd("reel_page.py", "reels", KIT, "--open", "Reel 1")
    sid = rpc.song_of(s, KIT, "Test beat")
    code, j, _ = s.http("POST", "/reel-save", rpc.save_body(s.state(), {"picks": rpc.pk(PICKS), "mine": True, "song": sid, "vibe": "beat", "footage": False, "kind": "photos", "direct": ""}, page="pagewatch0"))
    case("(set up: Reel 1 as a just-photos reel with the test beat)", code == 200 and j["ok"], (code, j))
    c.open(s.page_url("photos") + "&test=1")
    c.wait_for("window.Reel && window.Reel.state()", 20)
    t = c.js("""({h2: document.querySelector('#watch h2').textContent.replace(/^\\d+/, ''), say: document.getElementById('pvSayReel').innerHTML,
                 broll: !!document.getElementById('pvSayBroll'), empty: document.getElementById('pvEmpty').textContent,
                 wls: Array.from(document.querySelectorAll('#watch .wl')).map(function(x){ return x.textContent; }),
                 btns: ['pvPart', 'pvMix', 'pvUndo', 'pvRedo', 'pvMake'].map(function(i){ return document.getElementById(i).textContent; }),
                 chips: Array.from(document.querySelectorAll('#pvPace button')).map(function(b){ return b.textContent; }),
                 styleBox: !!document.getElementById('pvStyleBox'), osBox: !!document.getElementById('osBox'), saveVid: !!document.getElementById('pvSaveVid'),
                 play: document.getElementById('pvPlay').getAttribute('aria-label'), undoTitle: document.getElementById('pvUndo').title,
                 direct: {h2: document.querySelector('#stepDirect h2').textContent.replace(/^\\d+/, ''), say: document.querySelector('#stepDirect .say').textContent,
                          b: document.querySelector('#stepDirect label b').textContent, ex: document.querySelector('#stepDirect .ex').textContent,
                          ph: document.getElementById('directIn').placeholder, then: document.querySelector('#stepDirect .paste > p').textContent,
                          line: document.getElementById('directPaste').textContent, max: document.getElementById('directIn').maxLength},
                 last: Array.from(document.querySelectorAll('section.step:not([hidden])')).pop().id,
                 num: document.querySelector('#watch .num').textContent, dnum: document.querySelector('#stepDirect .num').textContent})""")
    case("her words on the watch step: the heading, her line for a reel, the empty phone's line, Song and Pace, the buttons, the pace chips, Play the reel, Undo's title; no B-roll words, no style box on a photos reel",
         t["h2"] == W["watch_h2"] and t["say"] == W["pv_say_reel_html"] and not t["broll"] and t["empty"] == W["pv_empty"] and t["wls"] == [W["pv_song"], W["pv_pace"]]
         and t["btns"] == [W["pv_part"], W["pv_mix"], W["pv_undo"], W["pv_redo"], W["pv_make"]] and t["chips"] == [R.WORDS["vibe_%s_b" % v] for v in R.VIBES]
         and not t["styleBox"] and not t["osBox"] and not t["saveVid"] and t["play"] == W["pv_play"] and t["undoTitle"] == W["pv_undo_title"], t)
    case("her words on the direct step, and its line \"Edit my reel for <shoot>, <reel>\" (several reels, no note)",
         t["direct"]["h2"] == W["direct_h2"] and t["direct"]["say"] == W["direct_say"] and t["direct"]["b"] == W["direct_b"] and t["direct"]["ex"] == W["direct_ex"]
         and t["direct"]["ph"] == W["direct_placeholder"] and t["direct"]["then"] == W["direct_then"] and t["direct"]["line"] == "Edit my reel for Fake beach, Reel 1" and t["direct"]["max"] == R.DIRECT_MAX, t["direct"])
    case("the watch step is the last step (hers), numbered after the direct step: 4 and 6 on a just-photos page", t["last"] == "watch" and t["dnum"] == "3" and t["num"] == "5", (t["last"], t["dnum"], t["num"]))
    ok = wait(c, "document.getElementById('pvWords').textContent.indexOf('On every beat: ') === 0", 40)
    p = pv(c)
    marks = " 1 of your 8 photos are set to Quicker and 2 to Longer" + R.WATCH_WORDS["pv_marks_tail"]
    case("the preview arrives by itself: her line under it (On every beat: N seconds, photos about N s each, and her marks sentence: 3 of 8 are marked), the first photo on the phone, the phone's empty line gone",
         ok and re.match(r"On every beat: \d+\.\d seconds, photos about \d\.\d s each\." + re.escape(marks) + "$", p["words"]) and p["empty"] and p["img"] and "/kit-photo?" in p["img"] and "n=3&" in p["img"]
         and p["mix"] == "" and p["undo"] and p["redo"] and p["song"] == sid and p["vibe"] == "beat", p)
    case("no path on the page", not re.search(r"/private/|/Users/", c.js("document.documentElement.outerHTML")))
    words0 = p["words"]
    c.click("#pvMix")
    ok = wait(c, "document.getElementById('pvMixSay').textContent === 'Mix 2' && document.getElementById('pvWords').textContent.indexOf('Working') < 0 && document.getElementById('pvWords').textContent.indexOf('On every beat') === 0", 40)
    p = pv(c)
    case("Try another mix: \"Mix 2\", the preview made again, Undo on", ok and p["mix"] == "Mix 2" and not p["undo"] and p["redo"], p)
    c.click("[data-pv-vibe='calm']")
    ok = wait(c, "document.getElementById('pvWords').textContent.indexOf('Calm: ') === 0", 40)
    p = pv(c)
    case("the Calm chip: her line says Calm, what On every beat gave in brackets, the chip on in step 5 too",
         ok and re.match(r"Calm: \d+\.\d seconds \(On every beat: \d+\.\d s\), photos about", p["words"]) and p["vibe"] == "calm"
         and c.js("document.querySelector('#vibes .opt.on').dataset.vibe") == "calm", p)
    c.click("#pvUndo")
    ok = wait(c, "document.getElementById('pvWords').textContent.indexOf('On every beat: ') === 0", 40)
    p = pv(c)
    case("Undo: back to On every beat (the chip in step 5 follows), Mix 2 still, Redo on", ok and p["vibe"] == "beat" and p["mix"] == "Mix 2" and not p["redo"]
         and c.js("document.querySelector('#vibes .opt.on').dataset.vibe") == "beat", p)
    c.click("#pvRedo")
    ok = wait(c, "document.getElementById('pvWords').textContent.indexOf('Calm: ') === 0", 40)
    case("Redo: Calm again", ok and pv(c)["vibe"] == "calm", pv(c))
    c.click("#pvUndo"); c.click("#pvUndo")
    ok = wait(c, "document.getElementById('pvMixSay').textContent === '' && document.getElementById('pvWords').textContent.indexOf('On every beat: ') === 0 && document.getElementById('pvUndo').disabled", 40)
    case("two Undos: the first mix, On every beat (what Calm gave in brackets, hers), Undo off", ok and pv(c)["words"].split(" (")[0] == words0.split(",")[0], (ok, pv(c), words0))
    c.click("#pvPart")
    ok = wait(c, "document.getElementById('pvWords').textContent.indexOf('Working') < 0 && !document.getElementById('pvUndo').disabled", 40)
    case("Another part of this song: the preview made again from further into the song, Undo on", ok and pv(c)["undo"] is False, pv(c))
    # a change in step 2 refreshes the preview
    before = c.js("document.getElementById('pvWords').textContent")
    c.click("#reel .tile:nth-child(2) .qk")
    ok = wait(c, "document.getElementById('pvWords').textContent === %s" % json.dumps(W["pv_working"]), 5)
    ok2 = wait(c, "document.getElementById('pvWords').textContent.indexOf('On every beat: ') === 0", 40)
    case("a change in step 2 (Quicker on the first photo) refreshes the preview within a moment (Working out the cut…, then her line)", ok and ok2, (ok, ok2, c.js("document.getElementById('pvWords').textContent")))
    # Make this one in CapCut sends the watched mix and start (a test run: nothing made)
    c.click("#pvMix")
    wait(c, "document.getElementById('pvMixSay').textContent === 'Mix 2' && document.getElementById('pvWords').textContent.indexOf('On every beat') === 0", 40)
    c.click("#pvMake")
    ok = wait(c, "document.querySelector('#result h3') && document.querySelector('#result h3').textContent === 'Test run: nothing was made'", 60)
    jrec = json.loads((s.kit / ".kit" / "reel-job.json").read_text())
    stj = json.loads((s.kit / ".kit" / "reel-job-status.json").read_text())
    case("Make this one in CapCut: the make (a test run here) carries the mix that was watched (variation 1) and where the song started, and reel.py used them",
         ok and jrec["ask"].get("variation") == 1 and isinstance(jrec["ask"].get("song_start"), (int, float)) and stj.get("variation") == 1
         and stj.get("song", {}).get("from") == jrec["ask"]["song_start"], (jrec.get("ask"), stj.get("variation"), stj.get("song")))
    # the direct box and its line
    c.click("#directIn"); c.key("Mod+A")
    c.type_text("Stove first")
    ok = wait(c, "document.getElementById('directPaste').textContent === 'Edit my reel for Fake beach, Reel 1, and follow my direction'", 5)
    case("a direction typed: the line gains \", and follow my direction\"", ok, c.js("document.getElementById('directPaste').textContent"))
    ok = rpc.on_disk(s, {"direct": "Stove first"}, 6)
    case("...and saved by itself", ok, (s.state()["saved"] or {}).get("direct"))
    c.click("#copyDirect")
    case("Copy copies the line", wait(c, "window.__copied === 'Edit my reel for Fake beach, Reel 1, and follow my direction'", 4), c.js("window.__copied"))
    rc, out = s.cmd("reel_page.py", "reels", KIT, "--rename", "Reel 1", "--to", "Barn")
    ok = wait(c, "document.getElementById('directPaste').textContent === 'Edit my reel for Fake beach, Barn, and follow my direction'", 8)
    case("the line names the reel (after a rename from the chat, the page follows)", ok, c.js("document.getElementById('directPaste').textContent"))
    errs = c.page_errors()
    case("no errors on the page", not errs, errs[:3])
    case("nothing asked of the internet", not c.outside_requests(), c.outside_requests()[:3])


def check_broll_page(c, s):
    R = rp()
    W = dict(R.WATCH_WORDS, **R.ONSCREEN_WORDS)
    rc, out = s.cmd("reel_page.py", "reels", KIT, "--open", "Broll one")
    rec = record(s)
    case("(set up: the B-roll reel open, with its three clips)", rc == 0 and len(R.moments_of(rec)) == 3, out[-200:])
    c.open(s.page_url("broll") + "&test=1")
    c.wait_for("window.Reel && window.Reel.state()", 20)
    t = c.js("""({say: document.getElementById('pvSayBroll').innerHTML, reel: !!document.getElementById('pvSayReel'), pace: !!document.getElementById('pvPace'),
                 styleBox: !!document.getElementById('pvStyleBox'), wls: Array.from(document.querySelectorAll('#watch .wl')).map(function(x){ return x.textContent; }),
                 ph: document.getElementById('osText').placeholder, hint: document.querySelector('#osBox .oshint').innerHTML, max: document.getElementById('osText').maxLength,
                 fonts: Array.from(document.querySelectorAll('#osFont option')).map(function(o){ return [o.value, o.textContent]; }),
                 styles: Array.from(document.querySelectorAll('#osStyle option')).map(function(o){ return [o.value, o.textContent]; }),
                 btns: ['pvSaveVid', 'pvMake'].map(function(i){ return document.getElementById(i).textContent; }),
                 mainBtn: document.getElementById('pvSaveVid').classList.contains('main') && !document.getElementById('pvMake').classList.contains('main'),
                 titles: [document.getElementById('pvText').title, document.getElementById('pvKnob').title],
                 direct: document.getElementById('stepDirect').hidden, text: document.getElementById('osText').value, textShown: !document.getElementById('pvText').hidden})""")
    case("her B-roll words: her line, Words on screen with its placeholder, hint, the three fonts and four styles, Save my video (the main button) and Make this one in CapCut, the drag titles; no pace chips, no style box, no direct step",
         t["say"] == W["pv_say_broll_html"] and not t["reel"] and not t["pace"] and not t["styleBox"] and t["wls"] == [W["pv_song"], W["os_wl"]]
         and t["ph"] == W["os_placeholder"] and t["hint"] == W["os_hint_html"] and t["max"] == R.ONSCREEN_TEXT_MAX
         and t["fonts"] == [[f, W["os_" + f]] for f in R.OS_FONTS] and t["styles"] == [[x, W["os_" + x]] for x in R.OS_STYLES]
         and t["btns"] == [W["os_save"], W["pv_make"]] and t["mainBtn"] and t["titles"] == [W["os_move"], W["os_size"]] and t["direct"]
         and t["text"] == "Golden hour at the barn" and t["textShown"], t)
    ok = wait(c, "document.getElementById('pvWords').textContent.indexOf('B-roll: ') === 0", 60)
    p = pv(c)
    case("the preview of the B-roll reel: her line (B-roll: N seconds, 3 clips, each cut on the beat.), the bar \"3 clips · B-roll · Test beat\", Make my reel on",
         ok and re.match(r"B-roll: \d+\.\d seconds, 3 clips, each cut on the beat\.$", p["words"]) and p["sum"] == "3 clips · B-roll · Test beat" and not p["makeOff"], p)
    case("the first clip plays on the phone (a video, not a picture)", wait(c, "!document.getElementById('pvVid').hidden && document.getElementById('pvVid').getAttribute('src').indexOf('/reel-video?') === 0", 10),
         c.js("document.getElementById('pvVid').getAttribute('src')"))
    # the words: typed into the box, drawn on the phone, in the saved font and style, where they were saved
    sv = s.state()["saved"]["onscreen"]
    d = c.js("""(function(){ var el = document.getElementById('pvText'), ph = document.getElementById('pvPhone').getBoundingClientRect(), r = el.getBoundingClientRect();
                 return {cx: (r.left + r.width / 2 - ph.left) / ph.width, cy: (r.top + r.height / 2 - ph.top) / ph.height, font: el.style.fontFamily, color: el.style.color,
                         bg: el.querySelector('span').style.background, size: el.style.fontSize, text: el.textContent, knob: !document.getElementById('pvKnob').hidden}; })()""")
    case("the words block sits where it was saved (x 0.31, y 0.72), Georgia, white on black, 1.4 times the size, the dot in its corner",
         abs(d["cx"] - sv["x"]) < 0.03 and abs(d["cy"] - sv["y"]) < 0.03 and "Georgia" in d["font"] and d["color"] == "rgb(255, 255, 255)" and d["bg"] in ("rgb(0, 0, 0)", "#000")
         and d["size"] == "8.54cqw" and d["text"] == "Golden hour at the barn" and d["knob"], d)
    c.click("#osText"); c.key("Mod+A"); c.type_text("Barn")
    c.set_value("#osFont", "avenir"); c.set_value("#osStyle", "black")
    ok = chrome_drive.wait_until(lambda: (s.state()["saved"]["onscreen"].get("text"), s.state()["saved"]["onscreen"].get("font"), s.state()["saved"]["onscreen"].get("style")) == ("Barn", "avenir", "black"), 8)
    d = c.js("(function(){ var el = document.getElementById('pvText'); return {text: el.textContent, color: el.style.color, bg: el.querySelector('span').style.background}; })()")
    case("new words, Avenir, Black text: drawn at once and saved (without a new preview: the words don't change the cut)",
         ok and d["text"] == "Barn" and d["color"] == "rgb(20, 20, 20)" and not d["bg"] and c.js("document.getElementById('pvWords').textContent").startswith("B-roll: "), (ok, d))
    # drag the words to a new place, and the dot to size them
    r0 = c.rect("#pvText")
    c.drag("#pvText", (r0["cx"] - 60, r0["cy"] - 120), steps=10)
    ok = chrome_drive.wait_until(lambda: s.state()["saved"]["onscreen"].get("x", 1) < 0.31 - 0.1 and s.state()["saved"]["onscreen"].get("y", 1) < 0.72 - 0.15, 8)
    sv = s.state()["saved"]["onscreen"]
    case("dragged up and left: saved at the new place (x, y smaller), still inside her bounds", ok and R.OS_X[0] <= sv["x"] <= R.OS_X[1] and R.OS_Y[0] <= sv["y"] <= R.OS_Y[1], sv)
    size0 = sv["size"]
    k = c.rect("#pvKnob")
    c.drag("#pvKnob", (k["cx"] + 40, k["cy"] + 20), steps=10)
    ok = chrome_drive.wait_until(lambda: s.state()["saved"]["onscreen"].get("size", 0) > size0 + 0.1, 8)
    sv = s.state()["saved"]["onscreen"]
    case("the dot dragged right and down: the words bigger, saved, within her 0.5 to 2.6", ok and sv["size"] <= R.OS_SIZE[1] and sv["x"] != 0.31, sv)
    c.drag("#pvText", (10, 10), steps=6)
    ok = chrome_drive.wait_until(lambda: s.state()["saved"]["onscreen"].get("x") == R.OS_X[0] and s.state()["saved"]["onscreen"].get("y") == R.OS_Y[0], 8)
    case("dragged off the top left corner: held at her bounds (0.12, 0.05)", ok, s.state()["saved"]["onscreen"])
    # Save my video (her v27, A15): the press, her saving line with the spinner, then her Saved line with Open the folder
    n_before = len(list((s.kit / "Reels").iterdir())) if (s.kit / "Reels").is_dir() else 0
    c.click("#pvSaveVid")
    ok = wait(c, "document.getElementById('pvSaved').textContent.trim() === %s && document.getElementById('pvSaveVid').disabled" % json.dumps(W["os_saving"]), 6)
    case("Save my video pressed: her saving line, the button off while it is saved", ok, c.js("document.getElementById('pvSaved').textContent"))
    ok = wait(c, "document.getElementById('openReels') !== null && !document.getElementById('pvSaveVid').disabled", 120)
    saved_line = c.js("document.getElementById('pvSaved').textContent")
    vm = [m for m in record(s).get("made") or [] if m.get("video")]
    case("...then her Saved line: the file's name, its length, in this shoot's Reels folder, with Open the folder; the file is there and the record notes it",
         ok and vm and re.search(r'^Saved "%s B-roll - Broll one 3\.mp4" \(\d+\.\d seconds\) in this shoot\'s Reels folder\. It\'s ready to post\. Open the folder$' % re.escape(R.short_name(KIT)), saved_line.strip())
         and (s.kit / "Reels" / vm[-1]["video"]).is_file() and len(list((s.kit / "Reels").iterdir())) == n_before + 1, (saved_line, vm[-1:]))
    c.click("#openReels")
    case("Open the folder: the Reels folder opened (nothing opened in a test) and our line said beside it",
         wait(c, "document.getElementById('reelsWent').textContent.indexOf(%s) === 0" % json.dumps(R.OUR_WORDS["reels_open"].rstrip(".")), 6), c.js("document.getElementById('reelsWent').textContent"))
    case("the queue's bar shows under Your reels: the reel counts as made", c.js("!document.getElementById('toqBar') || !document.getElementById('toqBar').hidden"))
    # no clips chosen: her line on the phone and under Save my video, Make my reel off
    c.js("Array.from(document.querySelectorAll('#clist .ci .cin')).forEach(function(b){ b.click(); })")
    ok = wait(c, "document.getElementById('makeBtn').disabled && document.getElementById('pvEmpty').textContent === %s" % json.dumps(W["os_clips_first"]), 10)
    p = pv(c)
    case("every clip taken out of the reel: \"Choose a clip or two first.\" on the phone, the bar says 0 clips, Make my reel off", ok and p["sum"].startswith("0 clips · B-roll"), p)
    c.click("#pvSaveVid")
    case("...and Save my video says it too", wait(c, "document.getElementById('pvSaved').textContent === %s" % json.dumps(W["os_clips_first"]), 4), c.js("document.getElementById('pvSaved').textContent"))
    errs = c.page_errors()
    case("no errors on the page", not errs, errs[:3])
    case("nothing asked of the internet", not c.outside_requests(), c.outside_requests()[:3])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=8816)
    ap.add_argument("--only", choices=("words", "status", "preview", "direct", "broll", "page"))
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp")
        return 2
    run = work / time.strftime("watch-%H%M%S")
    run.mkdir(parents=True)
    group("her words for the direct step, the watch step and B-roll's words on screen, both ways", check_words)
    if a.only == "words":
        return rpc.summary()
    group("reel.py's status: the pieces, a reel of clips only, --hook-whole", check_status, run)
    if a.only == "status":
        return rpc.summary()
    if not Path("/usr/bin/sips").exists():
        print("SKIP  the rest: the pretend kit and the clips are made with the Mac's own tools", flush=True)
        return rpc.summary()
    clips = rfc.make_clips(run / "clips")
    s = rpc.Setup(run, a.port)
    s.make()
    s.start()
    try:
        case("the page server is on a port of this test's own (%d)" % s.port, a.port <= s.port < a.port + 10)
        code, out = s.cmd("reel_page.py", "open", str(s.kit))
        case("(set up: the page's small copies made first)", code == 0, out[-200:])
        s.http("POST", "/reel-open", {"kit": KIT, "what": "footage"})
        shutil.copy(clips["clip.mov"], s.kit / "Footage" / "clip.mov")
        shutil.copy(clips["sideways.mov"], s.kit / "Footage" / "Sideways é.mov")
        j = rfc.wait_ready(s)
        case("(set up: two clips in the Footage folder, ready)", j and len(j["videos"]) == 2 and all(v["preview"] == "ready" for v in j["videos"]), j)
        group("the preview on the server, and the make that carries the mix", check_preview, s)
        if a.only == "preview":
            return rpc.summary()
        group("direct this edit: the note, and reel_page.py direct", check_direct, s, clips)
        if a.only == "direct":
            return rpc.summary()
        group("B-roll on the server: clips only, the words on screen, the project", check_broll, s)
        if a.only == "broll":
            return rpc.summary()
        if not chrome_drive.find_chrome():
            print("SKIP  the page in a browser: no Chrome on this computer", flush=True)
        else:
            with chrome_drive.Chrome(work=str(run), size=(1100, 1000), extra_args=rfc.LIGHT) as c:
                c.init_script("document.addEventListener('copy', function(){ window.__copied = String(window.getSelection()); }, true);")
                group("the watch step and the direct step on the page", check_page, c, s)
            with chrome_drive.Chrome(work=str(run), size=(1100, 1000), extra_args=rfc.LIGHT) as c:
                group("B-roll on the page: the words on screen", check_broll_page, c, s)
    finally:
        s.stop()
    return rpc.summary()


if __name__ == "__main__":
    sys.exit(main())
