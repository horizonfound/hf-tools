#!/usr/bin/env python3
"""The reel page after its reviewers (v19, fix-a): each finding that was fixed, checked so that the check fails on
the code from before the fix.

    /usr/bin/python3 tests/reel_fixes_check.py --work /private/tmp/somewhere [--port 9200]

On pretend kits it makes itself (tests/fake_kit.py and a few header-only JPEGs; nothing of a client's), with the
page server and, for one part, a hidden Chrome, both its own and both stopped at the end. CapCut's projects folder
is a pretend one; CapCut is never started and no folder is ever opened. A pretend `afconvert` (a few lines of sh,
written into this run's folder and put first on the page server's PATH) passes every call to the Mac's own one,
except while a part of this test asks it to hang or to be stopped part way.

  1. the result box never shows reel.py's "Wide photos..." line (it counts by photo number; hers has none)
  2. the kit page's reel link says her "Create my reel" / "Make a new version", shows before Claude has picked,
     and the line beside it points at it, not at the chat; "The cover is in the Covers folder" only when it is
  3. a plain click (no pointer before it: VoiceOver, Switch Control) on All your photos adds and takes out
  4. a chat reel with --kit uses the kit's numbered list, never a list the page left behind that went stale
  5. a CapCut project stopped part way is never left under a name CapCut would list; a job stopped after CapCut
     had it never says "Nothing was made"
  6. one hard limit for a job: reel.py and everything it started are stopped at it, the recording's sound is
     held to it too, and a job past its time is told as too long even while its lock is held
  7. a recording's sound is written under a hidden name first; a sound beside it that can't be read is left as it
     is and a new one made beside it ("<name> sound 2.m4a")
  8. "It's in CapCut ... at the top of your projects" only when it is in CapCut's list; else what to do
  9. a Music folder that is a link is never listed, written into or opened
 10. the reel page asked for by another website is the plain "can't find" page, with nothing written

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED.
"""
import argparse
import html
import json
import os
import shutil
import signal
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
import reel_page_check as rpc  # noqa: E402
from chrome_drive import case, group  # noqa: E402

LIMIT = 8            # the jobs' MAKE_LIMIT in this test (ASSISTANT_TEST_MAKE_LIMIT), and 2 s of grace
WIDE_KIT = "2026-11-03 Wide shoot"
CANT_FIND = "I can't reach this shoot right now. Check that the photo drive is plugged in, then reload."
HER_OPEN_SAY = "Open CapCut, click it at the top of your projects, add your look, and export."

FAKE_AFCONVERT = r"""#!/bin/sh
mode=$(cat "$FAKE_AFC_FLAG" 2>/dev/null)
if [ "$mode" = "hang" ]; then
  sleep 120 &
  echo "$$ $!" >> "$FAKE_AFC_PIDS"
  wait
  exit 1
fi
if [ "$mode" = "partial" ]; then
  for last; do :; done
  head -c 3000 /dev/zero > "$last"
  kill -9 $PPID
  sleep 1
  exit 1
fi
exec /usr/bin/afconvert "$@"
"""


class Fake:
    """The pretend afconvert and its switch."""
    def __init__(self, run):
        self.dir = run / "fakebin"
        self.dir.mkdir()
        (self.dir / "afconvert").write_text(FAKE_AFCONVERT)
        (self.dir / "afconvert").chmod(0o755)
        self.flag = run / "fake-afconvert-mode"
        self.pids = run / "fake-afconvert-pids"
        self.env = {"PATH": str(self.dir) + os.pathsep + os.environ.get("PATH", ""), "FAKE_AFC_FLAG": str(self.flag),
                    "FAKE_AFC_PIDS": str(self.pids)}

    def mode(self, m):
        if m:
            self.flag.write_text(m)
        elif self.flag.exists():
            self.flag.unlink()

    def started(self):
        try:
            return [int(x) for x in self.pids.read_text().split()]
        except (OSError, ValueError):
            return []

    def alive(self):
        out = []
        for p in self.started():
            try:
                os.kill(p, 0)
                out.append(p)
            except OSError:
                pass
        return out

    def sweep(self):
        for p in self.alive():
            try:
                os.kill(p, signal.SIGKILL)
            except OSError:
                pass


def job_q(kit):
    return "/reel-job?kit=" + kit.replace(" ", "%20")


def wide_kit(s):
    """A kit of header-only JPEGs inside Your Content, some wide, with no reel pick from Claude, a song in Music."""
    k = s.kit.parent / WIDE_KIT
    photos = k / "Photos"
    photos.mkdir(parents=True)
    for n in range(1, 9):
        rpc.tiny_jpeg(photos / ("%02d.jpg" % n), *((1600, 1067) if n in (2, 5, 7) else (1080, 1350)))
    (k / ".kit").mkdir()
    (k / ".kit" / "kit.json").write_text(json.dumps({"name": "Wide shoot", "date": "2026-11-03", "folder": WIDE_KIT,
                                                     "source": "folder", "photos_dir": str(photos),
                                                     "photos": sorted(os.listdir(photos))}))
    (k / "Music").mkdir()
    (k / "Music" / "Beat.wav").write_bytes(rpc.BEAT60.read_bytes())
    code, out = s.cmd("kit.py", "sheet", str(k))
    return k, code == 0 and (k / ".kit" / "sheet.json").is_file(), out


# ---------- 1, 2, 4: the wide kit ----------

def check_wide_kit(s):
    k, ok, out = wide_kit(s)
    case("(a pretend kit with wide photos and no reel pick from Claude)", ok, out[-300:])
    sid = rpc.song_of(s, WIDE_KIT, "Beat")
    _, job = rpc.make_job(s, WIDE_KIT, rpc.picks([1, 2, 3, 5, 7, 8]), sid, "beat")
    case("a test make with wide photos in it is done", job and job["state"] == "done", job)
    case("1. its lines hold no 'Wide photos...' line (it counts by photo number; her page has no such line)",
         job and job["words"] and not any(w.startswith("Wide") for w in job["words"]), job and job["words"])
    # 2. the kit page
    code, out = s.cmd("kit.py", "page", str(k))
    page = (k / ".kit" / "Post kit.html").read_text(encoding="utf-8") if (k / ".kit" / "Post kit.html").is_file() else ""
    case("2. the kit page's Reel card (her post kit) links to the reel page before Claude has picked, in her words", code == 0
         and "<a class='piece' data-piece='reel' href='/reel.html?kit=%s'>" % WIDE_KIT.replace(" ", "%20") in page
         and "<span class='cta'>Create my reel &rarr;</span>" in page, out[-200:])
    case("2. with her line for a shoot not picked yet, and nothing pointing at the chat",
         "Your assistant hasn&#x27;t picked the reel photos yet. Click to pick them yourself." in page and "Say “make the reel” to Claude" not in page)
    case("2. no Covers folder named on a kit with no Covers folder",
         "data-sub='Covers'" not in page and "The reel cover" not in page and not (k / "Covers").exists())
    # 4. a chat reel after the numbers were re-made under the list the page left in .kit/reels
    left = k / ".kit" / "reels" / "photos.json"
    case("(the page's make left its list in .kit/reels)", left.is_file())
    rpc.tiny_jpeg(k / "Photos" / "0000 newly exported.jpg", 1080, 1350)
    code, out = s.cmd("kit.py", "sheet", str(k))
    sheet = json.loads((k / ".kit" / "sheet.json").read_text())["photos"]
    case("(kit.py sheet numbered the new export 1)", code == 0 and Path(sheet[0]["file"]).name == "0000 newly exported.jpg", out[-200:])
    code, out = s.cmd(str(REEL / "reel.py"), "make", "--folder", str(k / "Photos"), "--shoot", "Wide shoot", "--kit", str(k),
                      "--picks", "1,2", "--song", "none", "--dry-run")
    plan = json.loads((k / ".kit" / "reels" / "reel.json").read_text())["plan"]
    got = [Path(p["path"]).name for p in plan["photos"]]
    case("4. a chat reel with --kit puts in the photos the kit's numbers mean, not the stale list's", code == 0
         and got == ["0000 newly exported.jpg", "01.jpg"], (got, out[-200:]))
    return k


# ---------- 5: a CapCut project stopped part way ----------

KILL_WRITE = r"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import capcut
plan = json.loads(Path(sys.argv[2]).read_text())["plan"]
real = capcut.write_json
def write_then_stop(path, obj):
    real(path, obj)
    os._exit(9)              # stopped for good after the first file, as a job killed part way is
capcut.write_json = write_then_stop
capcut.write(plan, Path(sys.argv[3]), ignore_open=True)
"""


def check_capcut_stopped(s, k):
    sid = rpc.song_of(s, WIDE_KIT, "Beat")
    rpc.make_job(s, WIDE_KIT, rpc.picks([2, 3, 4]), sid, "beat")          # a plan, with the song, in .kit/reels
    store = s.work / "stopped-store"
    store.mkdir()
    script = s.work / "kill_write.py"
    script.write_text(KILL_WRITE)
    r = subprocess.run([sys.executable, str(script), str(REEL), str(k / ".kit" / "reels" / "reel.json"), str(store)],
                       capture_output=True, text=True, env=s.env, timeout=60)
    seen = sorted(os.listdir(store))
    case("(the pretend write was stopped part way)", r.returncode == 9, (r.returncode, r.stderr[-300:]))
    case("5. a CapCut project stopped part way leaves no folder CapCut would list (only a hidden one of ours)",
         seen and all(f.startswith(".") for f in seen), seen)
    # a job stopped after reel.py had made the project, before the page noted it
    jl = k / ".kit" / "reel-job.json"
    jl.write_text(json.dumps({"id": "c" * 12, "state": "running", "t": time.time(), "t0": time.time(), "pid": 99999999, "dry": False}))
    (k / ".kit" / "reel-job-status.json").write_text(json.dumps({"for": "c" * 12, "ok": True, "dry": False, "project": "2026-11-03 Wide shoot reel"}))
    code, j, _ = s.http("GET", job_q(WIDE_KIT) + "&id=" + "c" * 12)
    p = ((j or {}).get("job") or {}).get("problem") or ""
    case("5. a job stopped once CapCut had the reel never says 'Nothing was made'; it names the project",
         "Nothing was made" not in p and "2026-11-03 Wide shoot reel" in p, p)


# ---------- 6: one hard limit ----------

def check_limit(s, fake):
    k = s.kit
    music = k / "Music"
    (music / "Hang song.m4a").write_bytes((rpc.FIX / "click-100bpm.m4a").read_bytes())
    rpc.make_recording(music / "Hang rec.mov")                        # made with the real afconvert, before the switch
    hid = rpc.song_of(s, rpc.KIT, "Hang song")
    rid = rpc.song_of(s, rpc.KIT, "Hang rec")
    fake.mode("hang")
    try:
        t0 = time.time()
        _, job = rpc.make_job(s, rpc.KIT, rpc.picks([1, 4, 7, 10]), hid, "beat", seconds=60)
        took = time.time() - t0
        case("6. reel.py stuck reading its song: the job is stopped at its limit and says hers 'That took too long'",
             job and job["state"] == "problem" and job["problem"].startswith("That took too long") and took < LIMIT + 6,
             (round(took, 1), job))
        time.sleep(0.5)
        case("6. ...and everything reel.py had started is stopped with it (nothing left running)",
             fake.started() and not fake.alive(), (fake.started(), fake.alive()))
        fake.sweep()
        t0 = time.time()
        _, job = rpc.make_job(s, rpc.KIT, rpc.picks([1, 4, 7, 10]), rid, "beat", seconds=60)
        took = time.time() - t0
        case("6. taking a recording's sound is held to the same limit", job and job["state"] == "problem"
             and job["problem"].startswith("That took too long") and took < LIMIT + 6, (round(took, 1), job))
        case("6. ...and no sound was left under its real name", not (music / "Hang rec sound.m4a").exists(), sorted(os.listdir(music)))
    finally:
        fake.mode(None)
        fake.sweep()
    # a job past its time while its lock is held (a step that hangs): told as too long, not spinning for ever
    sys.path.insert(0, str(SCRIPTS))
    import this_computer
    lockf = open(k / ".kit" / "reel-job.lock", "a")
    try:
        held = this_computer.try_lock(lockf)
        jl = k / ".kit" / "reel-job.json"
        keep = jl.read_bytes() if jl.exists() else None
        jl.write_text(json.dumps({"id": "d" * 12, "state": "running", "t": time.time(), "t0": time.time() - LIMIT - 10,
                                  "pid": os.getpid(), "dry": True}))
        code, j, _ = s.http("GET", job_q(rpc.KIT) + "&id=" + "d" * 12)
        jb = (j or {}).get("job") or {}
        case("6. a job past its time is told as too long even while its lock is held", held and jb.get("state") == "problem"
             and (jb.get("problem") or "").startswith("That took too long"), (held, jb))
        if keep is not None:
            jl.write_bytes(keep)
    finally:
        this_computer.unlock(lockf)
        lockf.close()


# ---------- 7: the recording's sound ----------

EXTRACT = r"""
import sys
sys.path.insert(0, sys.argv[1])
import sound
print(sound.extract_audio(sys.argv[2], sys.argv[3]))
"""


def check_sound(s, fake):
    music = s.kit / "Music"
    rpc.make_recording(music / "Rec two.mov")
    (music / "Rec two sound.m4a").write_bytes(b"")                    # cut off by a make from before
    rid = rpc.song_of(s, rpc.KIT, "Rec two")
    _, job = rpc.make_job(s, rpc.KIT, rpc.picks([1, 4, 7, 10, 13, 16]), rid, "beat")
    spare = music / "Rec two sound 2.m4a"
    case("7. a sound beside a recording that can't be read: the make still works, from a new one beside it",
         job and job["state"] == "done" and spare.is_file() and spare.stat().st_size > 2000, job)
    case("7. the one that couldn't be read is left exactly as it was", (music / "Rec two sound.m4a").stat().st_size == 0)
    st = s.http("GET", "/reel-songs?kit=" + rpc.KIT.replace(" ", "%20"))[1]
    names = [x["name"] for x in st["songs"]]
    case("7. neither sound is listed as a song of its own; the recording is listed once",
         names.count("Rec two") == 1 and not any(n.startswith("Rec two sound") for n in names), names)
    h = rpc.sha(spare)
    _, job = rpc.make_job(s, rpc.KIT, rpc.picks([1, 4, 7, 10, 13, 16]), rid, "calm")
    case("7. the next make uses that same new sound: nothing written over, no third one",
         job and job["state"] == "done" and rpc.sha(spare) == h and not (music / "Rec two sound 3.m4a").exists(), job)
    # written under a hidden name: a make stopped while the sound was being written leaves nothing under the real name
    out = s.work / "sound-out"
    out.mkdir()
    script = s.work / "extract.py"
    script.write_text(EXTRACT)
    fake.mode("partial")
    try:
        r = subprocess.run([sys.executable, str(script), str(REEL), str(music / "Rec two.mov"), str(out / "Cut sound.m4a")],
                           capture_output=True, text=True, env=dict(s.env, **fake.env), timeout=60)
    finally:
        fake.mode(None)
    case("(the pretend afconvert stopped the make while it was writing)", r.returncode != 0, (r.returncode, r.stdout[-200:]))
    case("7. a sound stopped part way leaves nothing under its real name", not (out / "Cut sound.m4a").exists(), sorted(os.listdir(out)))


# ---------- 8: in CapCut's list, or not ----------

def check_waiting(s):
    sys.path.insert(0, str(REEL))
    import capcut
    if capcut.capcut_open():
        print("SKIP  8. CapCut is open on this Mac, so a reel made now would be left to CapCut to list", flush=True)
        return
    root = s.store / "root_meta_info.json"
    if root.exists():
        root.rename(s.store / "root_meta_info.json.aside")
    root.mkdir()                     # CapCut's list can't be saved: the reel waits
    try:
        sid = rpc.song_of(s, rpc.KIT, "Beat one")
        _, job = rpc.make_job(s, rpc.KIT, rpc.picks([2, 5, 8, 11]), sid, "beat", test=False)
        say = (job or {}).get("capcut_say") or ""
        case("8. a reel that couldn't go into CapCut's list: the page is told what to do, not 'at the top of your projects'",
             job and job["state"] == "done" and say.startswith("CapCut was open, so your reel is waiting") and "Open CapCut" in say, job)
        status = json.loads((s.kit / ".kit" / "reel-job-status.json").read_text())
        case("8. reel.py's --status says it is waiting, not listed", status.get("waiting") is True and status.get("listed") is False, status)
    finally:
        root.rmdir()
        if (s.store / "root_meta_info.json.aside").exists():
            (s.store / "root_meta_info.json.aside").rename(root)
    sys.path.insert(0, str(SCRIPTS))
    import inspect
    import posting_queue
    case("8. Open CapCut's 'press ... again' line names the button the page has",
         "button" in inspect.signature(posting_queue.open_capcut).parameters)


# ---------- 9 and 10: a linked Music folder; another website ----------

def check_link_and_site(s):
    k = s.kit
    music = k / "Music"
    aside = k / "Music.real"
    music.rename(aside)
    elsewhere = s.work / "Somewhere else"
    elsewhere.mkdir()
    (elsewhere / "Linked song.wav").write_bytes(rpc.BEAT60.read_bytes())
    before = sorted(os.listdir(elsewhere))
    music.symlink_to(elsewhere)
    try:
        st = s.http("GET", "/reel-songs?kit=" + rpc.KIT.replace(" ", "%20"))[1]
        case("9. a Music folder that is a link: none of its songs are listed, and it isn't called the Music folder",
             st and not any(x["name"] == "Linked song" for x in st["songs"]) and st["music"] is False, st)
        code, j, _ = s.http("POST", "/reel-open", {"kit": rpc.KIT, "what": "music"})
        case("9. Add my music doesn't open it", code == 200 and j and j["ok"] is False, j)
        case("9. the folder it points to is exactly as it was", sorted(os.listdir(elsewhere)) == before)
    finally:
        music.unlink()
        aside.rename(music)
    dot = k / ".kit"
    snap = {f: (dot / f).stat().st_mtime_ns for f in os.listdir(dot)}
    code, _, raw = s.http("GET", "/reel.html?kit=" + rpc.KIT.replace(" ", "%20"), headers={"Sec-Fetch-Site": "cross-site"})
    body = html.unescape(raw.decode("utf-8", "replace"))
    case("10. the reel page asked for by another website is the plain 'can't find' page",
         CANT_FIND in body and "Put your photos in order" not in body, body[:200])
    case("10. ...and nothing in the kit's records was written", {f: (dot / f).stat().st_mtime_ns for f in os.listdir(dot)} == snap)
    code, _, raw = s.http("GET", "/reel.html?kit=" + rpc.KIT.replace(" ", "%20"), headers={"Sec-Fetch-Site": "same-origin"})
    case("10. the page itself still opens for the pane", "Put your photos in order" in raw.decode("utf-8", "replace"))


# ---------- 1 (the server's own words) and 3: in the page ----------

def check_units():
    sys.path.insert(0, str(SCRIPTS))
    import reel_page as rp
    out = ("Plan: 6 photos, 7.0 seconds, every cut on the beat at about 120 beats a minute.\n"
           "Wide photos zoomed to fill the screen: 2, 7 (slide them in CapCut if a face is cut off).\n"
           "Beats per piece: 1, 1, 2, 1, 1, 2\n")
    for dry in (True, False):
        case("1. %s: reel.py's Wide line never reaches the page" % ("a test make" if dry else "a real make"),
             not any(w.startswith("Wide") for w in rp._her_lines(out, dry, None, [])), rp._her_lines(out, dry, None, []))
    case("8. in CapCut's list: her line", rp.capcut_say({"listed": True}) == HER_OPEN_SAY)
    case("8. left to an open CapCut on a Mac (it lists it by itself): her line", rp.capcut_say({"listed": False, "left_to_capcut": True}) == HER_OPEN_SAY)
    case("8. not listed and nothing waiting: what to do if it isn't there",
         rp.capcut_say({"listed": False, "waiting": False}).startswith("Open CapCut. If your reel isn't at the top"))


def check_click(c, s):
    c.open(s.page_url())
    c.wait_for(rpc.READY, 30)
    before = c.js(rpc.ORDER)
    n = next(x for x in range(1, rpc.PHOTOS + 1) if x not in before)
    c.js("document.querySelector('#all .pick[data-n=\"%d\"]').click()" % n)
    time.sleep(0.4)
    after = c.js(rpc.ORDER)
    case("3. a plain click (no pointer before it) on a photo below adds it, as hers does", after == before + [n], (before, after))
    c.js("document.querySelector('#all .pick[data-n=\"%d\"]').click()" % n)
    time.sleep(0.3)
    case("3. ...and a second one takes it out again", c.js(rpc.ORDER) == before, c.js(rpc.ORDER))
    c.js("(function(){ var d = document.querySelector('#all').closest('details'); if (d) d.open = true; })()")
    time.sleep(0.3)
    c.js("document.querySelector('#all .pick[data-n=\"%d\"]').scrollIntoView({block: 'center'})" % n)
    time.sleep(0.4)
    c.click("#all .pick[data-n=\"%d\"]" % n)
    time.sleep(0.4)
    case("3. a real press still adds it once (not twice)", c.js(rpc.ORDER) == before + [n], c.js(rpc.ORDER))
    c.click("#all .pick[data-n=\"%d\"]" % n)
    time.sleep(0.4)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=9200)
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp")
        return 2
    run = work / time.strftime("fixes-%H%M%S")
    run.mkdir(parents=True)
    if not Path("/usr/bin/sips").exists():
        print("SKIP  the pretend kit is drawn with the Mac's sips", flush=True)
        return rpc.summary()
    s = rpc.Setup(run, a.port)
    os.environ.update(HOME=s.env["HOME"], STUDIO_HOME=s.env["STUDIO_HOME"])     # this process's imports: never ~/.studio
    group("the words, on their own", check_units)
    fake = Fake(run)
    s.make()
    s.start(ASSISTANT_TEST_MAKE_LIMIT=str(LIMIT), **fake.env)
    try:
        case("(the page server is this test's own: %d)" % s.port, a.port <= s.port < a.port + 10)
        (s.kit / "Music").mkdir(exist_ok=True)
        (s.kit / "Music" / "Beat one.wav").write_bytes(rpc.BEAT60.read_bytes())
        k = group("the wide kit: the Wide line, the kit page's link, a stale list", check_wide_kit, s)
        if k is not None:
            group("a CapCut project stopped part way", check_capcut_stopped, s, k)
        group("one hard limit for a job", check_limit, s, fake)
        group("a recording's sound", check_sound, s, fake)
        group("in CapCut's list, or not", check_waiting, s)
        group("a linked Music folder, and another website", check_link_and_site, s)
        if chrome_drive.find_chrome():
            with chrome_drive.Chrome(work=str(run), size=(1280, 1700)) as c:
                group("a plain click on All your photos", check_click, c, s)
        else:
            print("SKIP  3. no Chrome on this computer", flush=True)
    finally:
        fake.sweep()
        s.stop()
    return rpc.summary()


if __name__ == "__main__":
    sys.exit(main())
