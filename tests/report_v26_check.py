#!/usr/bin/env python3
"""The report after a backup, as Nicole's notes of Nov 13 ask (section 2): why there are several folders, "Does
everything look right?" above Add to my editing queue, each shoot's own Open this folder, the sneak peeks
explained, and the next step in place of the old line about a reel.

    python3 tests/report_v26_check.py [--port 9470] [--work <a folder to keep the run in>] [--no-chrome]

What it checks:
  * the words: hers whole (compared with her notes file when it is on this computer: reference-private/, never
    pushed), ours named; the old reel line is in no script and no instruction any more
  * pretend backups made here with no add-on (so this runs on Apple's own Python too): two shoots on two days
    of RAW photos; two shoots in one day of JPEGs; one shoot with some RAW and some JPEG picks; four picks;
    a card of only video clips; shoots not filed yet; a shoot already in the editing queue; a shoot on two cards
  * the report's server: GET open-shoot opens only a shoot's own folder, by its id, follows a rename, says
    Nicole's line for a folder that is gone, and refuses another website
  * the real page in a hidden Chrome: every new line where it belongs, Open this folder, Add to my editing
    queue, Pick again, and (with Pillow, on tests/fake_night.py) Show me more and Rename, phone width

Nothing under ~/.studio is touched (STUDIO_HOME is a scratch folder), no window is ever opened
(STUDIO_NO_WINDOWS_FOR_TESTS), the servers are the test's own on 127.0.0.1 and are stopped before it ends.
"""
import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/the-engine/skills/studio-manager/scripts"
PARTS = ROOT / "plugins/the-engine/skills/studio-manager/parts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/nicole_nov22.py
import nicole_nov22  # noqa: E402  Nicole, Nov 22: everything is the Assistant

# the smallest picture a browser will take: every "preview" in the pretend backups is this
TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=")

HERS = {   # Nicole's notes of Nov 13, section 2, as she wrote them
    "why": "Since these were two days, I put them in two separate folders. You can name them in the boxes below.",
    "look_right": "Does everything look right? If so, add it to your editing queue.",
    "open": "Open this folder",
    "peeks": ("I picked six photos that could be great sneak peeks to send your client. They're marked 'sneak peek' in "
              "Lightroom, if you want to do a quick edit on them."),
    "start": "Open your folder to start editing",
    "gone": "When you're finished with your edits, let me know and I'll turn your favorites into a reel.",
}
ENV = {}


def skip(line):
    print("SKIP  " + line, flush=True)


def her_notes():
    roots = [ROOT / "reference-private"]
    try:                                                   # a worktree: the main checkout's reference-private too
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"], capture_output=True, text=True, timeout=20).stdout.strip()
        if out:
            roots.append((ROOT / out).resolve().parent / "reference-private")
    except (OSError, subprocess.SubprocessError):
        pass
    for r in roots:
        for f in sorted(r.glob("nicole-handoff-v26-*/Carousel designer and reel picker/NOTES-from-Nicole-Nov-13.md")):
            return f
    return None


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPTS / args[0]), *args[1:]], capture_output=True, text=True, env=dict(os.environ, **ENV))
    return r.returncode, r.stdout + r.stderr


def http(url, headers=None, method="GET", body=None):
    req = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read()


# ---------------------------------------------------------------- pretend backups, no add-on needed

def make_backup(night, shoots, session=None, build=True):
    """A day folder with records, as a sorted backup leaves it. shoots: [{"name", "day" (YYYY-MM-DD), "hour",
    "n" files, "ext", "peeks": [extensions of the picked photos], "filed": True, "clips": False}]."""
    night = Path(night)
    studio = night / "_studio"
    for d in ("groups", "sneak-peeks"):
        (studio / d).mkdir(parents=True, exist_ok=True)
    files, index, groups, out, picks = {}, [], [], [], []
    for si, s in enumerate(shoots, 1):
        gid, sid = "g%02d" % si, "s%d" % si
        folder = "%s %s" % (s["day"], s["name"])
        (night / folder).mkdir(exist_ok=True)
        slug = s["name"].replace(" ", "-")
        gfiles, previews = [], []
        peek_exts = list(s.get("peeks", []))
        for i in range(s["n"]):
            ext = peek_exts[i] if i < len(peek_exts) else s["ext"]
            rel = "%s/%s_%04d_IMG_%d%03d.%s" % (folder, slug, i + 1, si, i, ext)
            (night / rel).write_bytes(b"pretend photo %d" % i)
            files[rel] = {"size": (night / rel).stat().st_size, "sha256": "0" * 64, "dest": {"ok": True}}
            taken = "%sT%02d:%02d:%02d" % (s["day"], s.get("hour", 9), i // 60, i % 60)
            index.append({"file": rel, "taken": taken, "camera": "Canon R5", "serial": "123", "lens": "35mm"})
            gfiles.append(rel)
            if i < 3:
                pv = "%s_IMG_%d%03d.jpg" % (gid, si, i)
                (studio / "groups" / pv).write_bytes(TINY_JPEG)
                previews.append(pv)
            if i < len(peek_exts):
                picks.append({"file": rel, "shoot": sid, "why": "a pretend pick"})
                (studio / "sneak-peeks" / (Path(rel).stem + ".jpg")).write_bytes(TINY_JPEG)
        g = {"id": gid, "files": gfiles, "previews": previews, "start": index[-len(gfiles)]["taken"], "end": index[-1]["taken"],
             "bodies": 1, "lenses": ["35mm"], "photos": 0 if s.get("clips") else len(gfiles), "clips": len(gfiles) if s.get("clips") else 0}
        if s.get("clips"):
            g["clip_previews"] = list(previews)
        groups.append(g)
        rec = {"id": sid, "groups": [gid], "name": s["name"], "suggested": s["name"], "photos": s["n"],
               "recap": "%d frames, %s." % (s["n"], s["name"].lower()), "why": "same people, same place"}
        if s.get("filed", True):
            rec["folder"] = folder
        out.append(rec)
    w = lambda name, data: (studio / name).write_text(json.dumps(data, indent=1), encoding="utf-8")   # noqa: E731
    w("manifest.json", {"session": session or night.name, "dest": str(night), "files": files, "started": "2026-06-25T22:00:00",
                        "finished": "2026-06-25T22:07:00", "work_seconds": 420, "problems": [], "skipped_system_files": 0})
    w("index.json", {"photos": index})
    w("groups.json", {"groups": groups})
    w("shoots.json", {"shoots": out})
    if picks:
        w("sneak-peeks.json", {"picked_by": "the Assistant", "picks": picks})
    if build:
        code, said = run("report_page.py", str(night))
        assert code == 0, said
    return night


def page(night, name="report.html"):
    return (Path(night) / "_studio" / name).read_text(encoding="utf-8")


def text_of(html_text, cls):
    """The words of every element whose class list has `cls`, tags taken out, entities turned back."""
    import html as H
    out = []
    for m in re.finditer(r"<(\w+)[^>]*class='[^']*\b%s\b[^']*'[^>]*>(.*?)</\1>" % re.escape(cls), html_text, re.S):
        out.append(re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", "", m.group(2)))).strip())
    return out


class Server:
    def __init__(self, night, port):
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "serve_report.py"), str(night), "--port", str(port)],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=dict(os.environ, **ENV))
        self.base = None
        for _ in range(200):
            line = self.proc.stdout.readline()
            if line.startswith("Report:"):
                self.base = line.split(":", 1)[1].split()[0].rsplit("/", 1)[0]
                break
            if not line:
                break
        self.port = int(self.base.rsplit(":", 1)[1]) if self.base else None

    def stop(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            try:
                self.proc.kill()
            except Exception:  # noqa: BLE001
                pass
        try:
            self.proc.stdout.close()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------- the words

def check_words():
    import first_look
    import home_base
    W, O = first_look.WORDS, first_look.OUR_WORDS
    case("her line for two days of shooting, word for word", W["why_days"].format(n="two") == HERS["why"], W["why_days"])
    case("her line above Add to my editing queue, word for word", W["look_right"] == HERS["look_right"])
    case("her button's name: Open this folder", W["open_folder"] == HERS["open"])
    case("her sneak peeks line, word for word", W["peeks"].format(n="six") == HERS["peeks"], W["peeks"])
    case("her next step: Open your folder to start editing", W["start"].rstrip(".") == HERS["start"], W["start"])
    case("a folder that is gone is said in the Back up a card screen's own words",
         W["unplugged"] == home_base.WORDS["b_unplugged"] and W["moved"].format(files_app="Finder") == home_base.WORDS["b_moved"])
    notes = her_notes()
    if notes:
        hers = nicole_nov22.read(notes)   # Nicole, Nov 22: everything is the Assistant
        for k in ("why", "look_right", "open", "peeks", "start", "gone"):
            case("her notes hold the line this test calls hers: %s" % k, HERS[k] in hers, HERS[k])
    else:
        skip("her notes are not on this computer (reference-private is never pushed): her lines are compared with this test's own copy")
    case("counts are written as words up to twelve, then as numbers",
         [first_look.count_word(n) for n in (2, 6, 12, 13, 1200)] == ["two", "six", "twelve", "13", "1,200"])
    every = list(W.values()) + list(O.values())
    case("no line says Claude, and none has an em dash", not any("Claude" in x or "—" in x for x in every))
    case("our line for a split that was not days claims no days", "day" not in O["why_shoots"].lower() and "{n}" in O["why_shoots"])
    # the sneak peeks line, true to the shoot
    case("six picks, all a kind that gets the mark: her line", first_look.peeks_words(6, 6) == HERS["peeks"])
    none = first_look.peeks_words(6, 0)
    case("six picks, none marked (JPEG): it never says they are marked in Lightroom",
         none.startswith("I picked six photos that could be great sneak peeks to send your client.") and "aren't marked in Lightroom" in none
         and "They're marked" not in none, none)
    some = first_look.peeks_words(6, 4)
    case("six picks, four marked: it says four are, and why the others are not",
         "Four of them are marked 'sneak peek' in Lightroom" in some and "The others" in some and "They're marked" not in some, some)
    case("four picks: it says four, not six", first_look.peeks_words(4, 4).startswith("I picked four photos") and "six" not in first_look.peeks_words(4, 4))
    # the old line is gone from everything a photographer or the assistant reads
    left = []
    for f in list((ROOT / "plugins").rglob("*.py")) + list((ROOT / "plugins").rglob("*.md")):
        t = f.read_text(encoding="utf-8", errors="replace")
        if "turn your favorites into a reel" in t or "I pulled six to get things rolling" in t:
            left.append(str(f.relative_to(ROOT)))
    case("the old reel line and the old sneak peeks line are in no script and no instruction", not left, left)
    for f in ("first_look.py", "report_page.py", "shoot_report.py", "serve_report.py"):
        t = (SCRIPTS / f).read_text(encoding="utf-8")
        said = [ln.strip()[:90] for ln in t.splitlines() if re.search(r"(tell|Tell|Ask|ask) Claude", ln)]
        case("%s: nothing the report says tells them to talk to Claude" % f, not said, said)
    # the instructions
    part = lambda n: (PARTS / n).read_text(encoding="utf-8")   # noqa: E731
    b = part("backup.md")
    case("backup.md: the closing words are the new next step, with the one-line why for several folders",
         "Open your folder to start editing." in b and O["come_back"] in b and "Never say days when it was a break in one day" in b)
    # (Nov 22, v30: the home page has no Make posts from a shoot button any more; the come-back line names the four
    # photo tiles that are there, in the report, the backup's closing words, the part after the report and the reel skill)
    reel_skill = (PARTS.parent.parent / "assistant-make-a-reel" / "SKILL.md").read_text(encoding="utf-8")
    case("the come-back line names the home page's four photo tiles, never the Make posts from a shoot button that is gone",
         "Make posts from a shoot" not in O["come_back"] and all(w in O["come_back"] for w in ("Reels", "Carousels", "Stories", "Captions"))
         and "click Make posts from a shoot" not in b and O["come_back"] in reel_skill and "click Make posts from a shoot" not in reel_skill, O["come_back"])
    a = part("after-the-report.md")
    case("after-the-report.md: Open this folder, the look-right line, and the honest answer for a moved folder",
         "**Open this folder**" in a and HERS["look_right"] in a and "no command that re-points" in a and O["come_back"] in a)
    s = part("sneak-peeks.md")
    case("sneak-peeks.md: her line, and never 'marked in Lightroom' to someone who shoots JPEG",
         HERS["peeks"] in s and "never tell someone who shoots JPEG" in s)
    f = part("first-backup-setup.md")
    # Since Nov 19 (Dustin: nothing is asked before the copy) the first backup has no opening speech and no
    # folder-naming question: these two cases held the old run of questions, and now hold that it is gone. Why there
    # are several folders is said on the report itself (WORDS["why_days"], checked above) and in backup.md's closing.
    case("first-backup-setup.md: no questions before the copy; the starting message says what the report lets them change, and no more",
         "**Question " not in f and "On the report afterwards you can add a second copy, rename your shoots, and change where the next backup goes." in f)
    case("first-backup-setup.md: folder naming is not asked; year first is the usual way and the other ways are changed on ask",
         '"2026-10-18 Smith Family"' in f and "studio_file.py set --offered 2" in f and "studio_file.py set --example" in f)
    reel = (ROOT / "plugins/the-engine/skills/assistant-make-a-reel/SKILL.md").read_text(encoding="utf-8")
    case("the reel skill: with only a backup, it says the new next step", "Open your folder to start editing. When your edits are done" in reel)


# ---------------------------------------------------------------- the pages, as written

def check_pages(work):
    import first_look
    W, O = first_look.WORDS, first_look.OUR_WORDS
    RAW6, JPG6 = ["cr3"] * 6, ["jpg"] * 6
    two_days = make_backup(work / "2026-06-25 two days", [
        {"name": "Beach", "day": "2026-06-24", "n": 12, "ext": "cr3", "peeks": RAW6},
        {"name": "Palm grove", "day": "2026-06-25", "n": 10, "ext": "cr3", "peeks": RAW6}])
    p = page(two_days)
    case("two shoots on two days: her line says why there are two folders", text_of(p, "why-folders") == [HERS["why"]], text_of(p, "why-folders"))
    case("... and it takes the place of the older line about folders (said once, not twice)", "Each one is already in its own folder" not in p)
    case("each shoot has its own Open this folder, by the shoot's id, with no place on the drive in it",
         p.count("class='open-row' data-shoot='s1'") == 1 and p.count("class='open-row' data-shoot='s2'") == 1
         and p.count("class='open-shoot'") == 2 and str(two_days) not in "".join(re.findall(r"<div class='open-row'.*?</div>", p, re.S)))
    case("the where-box at the bottom is still there", "where-card" in p and "Open photo folder" in p)
    order = [m.start() for m in (re.search(r"class='name'", p), re.search(r"class='open-row'", p), re.search(r"class='queue'", p))]
    case("on a shoot: the name box, then Open this folder, then the editing queue", order == sorted(order), order)
    case("above Add to my editing queue: her line, once per shoot, right before the button",
         p.count("<span class='q-ask'>" + HERS["look_right"] + "</span><button class='add' type='button'>Add to my editing queue</button>") == 2)
    lines = text_of(p, "peeks-line")
    case("RAW shooters: her sneak peeks line in full, then the way to change them",
         len(lines) == 2 and all(x == HERS["peeks"] + " " + O["peeks_change"] for x in lines), lines)
    case("Pick again and Show me more are still under it", p.count("class='pk again'") == 2 and p.count("class='pk more'") == 2)
    case("under the shoots, once: open the folder to start editing, and where to come back to",
         text_of(p, "next-step") == [W["start"] + " " + O["come_back"]], text_of(p, "next-step"))
    case("the page never says Claude, never offers a reel, and has no em dash in its new lines",
         "Claude" not in p and "into a reel" not in p and "—" not in "".join(text_of(p, "next-step") + lines + text_of(p, "why-folders")))

    one_day = make_backup(work / "2026-06-24 one day", [
        {"name": "Family one", "day": "2026-06-24", "hour": 9, "n": 8, "ext": "jpg", "peeks": JPG6},
        {"name": "Family two", "day": "2026-06-24", "hour": 15, "n": 8, "ext": "jpg", "peeks": JPG6}])
    p = page(one_day)
    why = text_of(p, "why-folders")
    case("two shoots in ONE day: the line never says days", why == [O["why_shoots"].format(n="two")] and "day" not in why[0].lower(), why)
    lines = text_of(p, "peeks-line")
    case("JPEG shooters: the line says what the picks are for and that they are NOT marked in Lightroom",
         len(lines) == 2 and all(x.startswith("I picked six photos that could be great sneak peeks to send your client.")
                                 and "aren't marked in Lightroom" in x and "They're marked" not in x and x.endswith(O["peeks_change"]) for x in lines), lines)

    across = make_backup(work / "2026-06-26 across", [
        {"name": "Wedding", "day": "2026-06-24", "n": 8, "ext": "cr3", "peeks": RAW6},
        {"name": "Brunch", "day": "2026-06-25", "n": 8, "ext": "cr3", "peeks": RAW6},
        {"name": "Portraits", "day": "2026-06-25", "hour": 16, "n": 8, "ext": "cr3", "peeks": RAW6}])
    why = text_of(page(across), "why-folders")
    case("three shoots over two days: three folders, and no claim that they were three days", why == [O["why_shoots"].format(n="three")], why)

    single = make_backup(work / "2026-06-24 single", [
        {"name": "Garcia", "day": "2026-06-24", "n": 10, "ext": "cr3", "peeks": ["cr3", "cr3", "jpg", "cr3", "jpg", "cr3"]}])
    p = page(single)
    case("one shoot: no line about several folders, the older line stays", text_of(p, "why-folders") == [] and "Each one is already in its own folder" in p)
    lines = text_of(p, "peeks-line")
    case("four RAW picks and two JPEG: four are marked, and it says so", len(lines) == 1 and "Four of them are marked 'sneak peek' in Lightroom" in lines[0]
         and "They're marked" not in lines[0], lines)
    case("one shoot still has its Open this folder, the look-right line and the next step",
         p.count("class='open-shoot'") == 1 and p.count("class='q-ask'") == 1 and len(text_of(p, "next-step")) == 1)

    four = make_backup(work / "2026-06-24 four picks", [
        {"name": "Minis", "day": "2026-06-24", "n": 10, "ext": "cr3", "peeks": ["cr3"] * 4}])
    p = page(four)
    lines = text_of(p, "peeks-line")
    case("a shoot with four sneak peeks: the line says four, in her words otherwise, and there are no buttons to lead into",
         lines == [HERS["peeks"].replace("six", "four")] and "class='pk again'" not in p, lines)

    clips_only = make_backup(work / "2026-06-24 clips", [
        {"name": "Garden demo", "day": "2026-06-24", "n": 5, "ext": "mp4", "clips": True}])
    p = page(clips_only)
    case("a card of only video clips: no sneak peeks line, its own words kept (video clips, See all, Open video folder)",
         text_of(p, "peeks-line") == [] and "5 video clips" in p and "See all 5 video clips" in p and "Open video folder" in p and "photos" not in "".join(text_of(p, "next-step")))
    case("... its shoot still has Open this folder and the look-right line; the next step says only to open the folder",
         p.count("class='open-shoot'") == 1 and p.count("class='q-ask'") == 1 and text_of(p, "next-step") == [W["start"]], text_of(p, "next-step"))

    unfiled = make_backup(work / "2026-06-24 unfiled", [
        {"name": "One", "day": "2026-06-24", "n": 6, "ext": "cr3", "filed": False},
        {"name": "Two", "day": "2026-06-25", "n": 6, "ext": "cr3", "filed": False}])
    p = page(unfiled)
    case("shoots not filed in folders yet: no line about folders, and no Open this folder button to nowhere",
         text_of(p, "why-folders") == [] and "class='open-shoot'" not in p and "Give each one a name and it is filed" in p)

    code, said = run("edit_queue.py", "add", "--night", str(two_days), "--shoot", "s1", "--due", "2027-01-15")
    case("(a shoot is put in the editing queue)", code == 0, said[-300:])
    run("report_page.py", str(two_days))
    p = page(two_days)
    case("a shoot already in the queue: no 'Does everything look right?' on it; the other shoot keeps the line",
         p.count("class='q-ask'") == 1 and "In your editing queue, due" in p and p.count("class='add'") == 1)
    before = p
    run("report_page.py", str(two_days))
    case("the report built twice is the same page", page(two_days) == before)
    return {"two_days": two_days, "one_day": one_day, "single": single, "clips": clips_only}


def check_cards(work):
    import first_look
    W, O = first_look.WORDS, first_look.OUR_WORDS
    c1 = make_backup(work / "2026-06-24 Fake wedding", [
        {"name": "Getting ready", "day": "2026-06-24", "n": 8, "ext": "cr3", "peeks": ["cr3"] * 6},
        {"name": "Ceremony", "day": "2026-06-25", "n": 8, "ext": "cr3", "peeks": ["cr3"] * 6}])
    c2 = make_backup(work / "2026-06-24 Fake wedding, card 2", [
        {"name": "Reception", "day": "2026-06-25", "hour": 19, "n": 8, "ext": "cr3", "peeks": ["cr3"] * 6}])
    code, said = run("shoot_report.py", "link", str(c1), str(c2))
    case("(two backups are linked as one shoot on two cards)", code == 0, said[-300:])
    card = page(c1, "report-card.html")
    case("a card's section of the shoot's page: why two folders, Open this folder on each shoot, the look-right line",
         text_of(card, "why-folders") == [HERS["why"]] and card.count("class='open-shoot'") == 2 and card.count("class='q-ask'") == 2)
    case("... and no next-step line of its own (the shoot's page says it once)", text_of(card, "next-step") == [])
    shoot = page(c1, "shoot-report.html")
    case("the shoot's page says the next step once, for every card", text_of(shoot, "next-step") == [W["start"] + " " + O["come_back"]]
         and ".next-step{" in shoot, text_of(shoot, "next-step"))
    case("a card's own full report still has the next step", len(text_of(page(c1), "next-step")) == 1)
    return c1, c2


# ---------------------------------------------------------------- the report's server

def check_routes(base, night, cards_base, c1, c2):
    import first_look
    import this_computer
    APP = this_computer.FILES_APP
    ask = lambda q, headers=None, b=base: http(b + "/open-shoot" + q, headers)   # noqa: E731
    st, body = ask("?shoot=s1")
    d = json.loads(body) if st == 200 else {}
    case("open-shoot by a shoot's id: that shoot's own folder is opened, and the words name it", st == 200 and d.get("ok") and d.get("words") == "Opened 2026-06-24 Beach in %s." % APP, (st, body[:200]))
    st, body = ask("?shoot=s2")
    case("the second shoot opens its own folder, not the first's", st == 200 and json.loads(body).get("words") == "Opened 2026-06-25 Palm grove in %s." % APP, body[:200])
    st, body = ask("?shoot=s9")
    case("a shoot the backup does not have: nothing opened, said plainly", st == 200 and json.loads(body) == {"ok": False, "words": first_look.OUR_WORDS["no_shoot"]}, body[:200])
    st, body = ask("?path=" + urllib.parse.quote(str(night)))
    case("a place on the drive in the ask is not looked at: no shoot named, nothing opened", st == 200 and json.loads(body).get("ok") is False, body[:200])
    st, body = ask("?shoot=s1", {"Sec-Fetch-Site": "cross-site"})
    case("another website's ask is refused (403)", st == 403, st)
    st, body = ask("?shoot=s1", {"Host": "evil.example:%s" % base.rsplit(":", 1)[1]})
    case("an ask under another name is refused (403)", st == 403, st)
    st, body = ask("?shoot=s1", {"Sec-Fetch-Site": "same-origin"})
    case("the report's own page may ask", st == 200 and json.loads(body).get("ok") is True, (st, body[:120]))
    # the three older routes that open a folder window or play a clip: another website's ask is refused there too
    for route in ("/open?path=" + urllib.parse.quote(str(night)), "/play?file=x.mp4", "/open-clips?shoot=s1"):
        st, body = http(base + route, {"Sec-Fetch-Site": "cross-site"})
        case("another website's ask of %s is refused (403)" % route.split("?")[0], st == 403, st)
    st, body = http(base + "/open?path=" + urllib.parse.quote("/no folder of this report"), {"Sec-Fetch-Site": "same-origin"})
    case("...and the report's own page is still answered there (a folder the report does not name: said plainly, nothing opened)",
         st == 200 and json.loads(body).get("ok") is False, (st, body[:160]))
    # a folder that is gone, and one that the records point outside the backup
    studio = Path(night) / "_studio"
    keep = (studio / "shoots.json").read_text(encoding="utf-8")
    shutil.move(str(Path(night) / "2026-06-25 Palm grove"), str(Path(night) / "moved away"))
    st, body = ask("?shoot=s2")
    case("a folder moved or renamed by hand: her line, and nothing opened",
         st == 200 and json.loads(body) == {"ok": False, "words": first_look.WORDS["moved"].format(files_app=APP)}, body[:300])
    d = json.loads(keep)
    d["shoots"][1]["folder"] = "moved away"
    (studio / "shoots.json").write_text(json.dumps(d), encoding="utf-8")
    st, body = ask("?shoot=s2")
    case("the folder is read from the records each time: after a rename the same button opens the new folder", st == 200 and json.loads(body).get("words") == "Opened moved away in %s." % APP, body[:200])
    outside = Path(night).parent / "outside the backup"
    outside.mkdir(exist_ok=True)
    for bad in ("../outside the backup", str(outside), ".", ""):
        d["shoots"][1]["folder"] = bad
        (studio / "shoots.json").write_text(json.dumps(d), encoding="utf-8")
        st, body = ask("?shoot=s2")
        case("records that point %r: nothing outside the backup's own shoot folders is opened" % bad, st == 200 and json.loads(body).get("ok") is False, body[:200])
    d["shoots"][1]["folder"] = 7
    (studio / "shoots.json").write_text(json.dumps(d), encoding="utf-8")
    st, body = ask("?shoot=s2")
    case("a folder that is not text in the records: an answer in plain words, never an error page", st == 200 and json.loads(body).get("ok") is False, (st, body[:200]))
    shutil.move(str(Path(night) / "moved away"), str(Path(night) / "2026-06-25 Palm grove"))
    (studio / "shoots.json").write_text(keep, encoding="utf-8")
    st, body = ask("?shoot=s2")
    case("put back: it opens again", st == 200 and json.loads(body).get("ok") is True, body[:200])
    # a shoot on two cards: each card's section asks its own card
    st, body = ask("?shoot=s1", b=cards_base + "/card/1")
    case("card 1's section opens card 1's shoot", st == 200 and json.loads(body).get("words") == "Opened 2026-06-24 Getting ready in %s." % APP, (st, body[:200]))
    st, body = ask("?shoot=s1", b=cards_base + "/card/2")
    case("card 2's section opens card 2's shoot (the same id, another card)", st == 200 and json.loads(body).get("words") == "Opened 2026-06-25 Reception in %s." % APP, (st, body[:200]))
    st, body = http(cards_base + "/report.html")
    case("the shoot's page is served with its one next-step line", st == 200 and body.count(b"class='next-step'") == 1, st)


# ---------------------------------------------------------------- the real page

def no_sideways(c, width):
    """Nothing on the page is wider than the phone (measured against the phone's own width: a phone zooms out to
    fit a page that is too wide, so the window as it then stands proves nothing)."""
    return c.js("document.documentElement.scrollWidth <= %d + 1 && window.innerWidth <= %d + 1" % (width, width))


def check_browser(c, base, night):
    import first_look
    import this_computer
    W, O = first_look.WORDS, first_look.OUR_WORDS
    APP = this_computer.FILES_APP
    # put the queue back to empty for this backup's second shoot only: s1 was queued by the page checks
    c.open(base + "/report.html")
    c.wait_for("document.querySelectorAll('article.shoot').length === 2", 15)
    shown = lambda sel: c.js("(() => { const e = document.querySelector(%s); if (!e) return false; const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; })()" % json.dumps(sel))   # noqa: E731
    case("in the browser: her line about the two folders shows above the shoots", shown(".why-folders") and c.text(".why-folders") == HERS["why"], c.text(".why-folders"))
    case("each shoot shows its Open this folder button, inside that shoot's own block, above its queue line",
         c.js("Array.from(document.querySelectorAll('article.shoot')).every(a => { const o = a.querySelector('.open-row .open-shoot'), q = a.querySelector('.queue');"
              " return o && q && o.textContent.trim().startsWith('Open this folder') && (o.compareDocumentPosition(q) & Node.DOCUMENT_POSITION_FOLLOWING) && o.getBoundingClientRect().height > 20; })"))
    c.click("article.shoot:nth-of-type(2) .open-shoot")
    c.wait_for("document.querySelector('article.shoot:nth-of-type(2) .open-state').textContent.startsWith('Opened')", 10)
    said = c.text("article.shoot:nth-of-type(2) .open-state")
    case("a press on it: what happened is said right under that button, and only there", said == "Opened 2026-06-25 Palm grove in %s." % APP
         and c.text("article.shoot:nth-of-type(1) .open-state") == "" and c.js("document.getElementById('open-toast').textContent") == "", said)
    r1, r2 = c.rect("article.shoot:nth-of-type(2) .open-shoot"), c.rect("article.shoot:nth-of-type(2) .open-state")
    case("... the line sits directly under the button it belongs to", 0 <= r2["y"] - r1["bottom"] < 24, (r1, r2))
    # the first shoot is in the queue already; the second has the line and the button
    case("the shoot already in the queue has no look-right line; the other has it right above its button",
         c.js("!document.querySelector('article.shoot:nth-of-type(1) .q-ask') && (() => { const k = document.querySelector('article.shoot:nth-of-type(2) .q-ask'), b = document.querySelector('article.shoot:nth-of-type(2) .add');"
              " return k.textContent === %s && k.nextElementSibling === b && k.getBoundingClientRect().bottom <= b.getBoundingClientRect().top + 1; })()" % json.dumps(HERS["look_right"])))
    c.click("article.shoot:nth-of-type(2) .add")
    case("Add to my editing queue still opens the calendar right there", shown("article.shoot:nth-of-type(2) .pick"))
    c.set_value("article.shoot:nth-of-type(2) .pick input[type=date]", "2027-02-03")
    c.click("article.shoot:nth-of-type(2) .save")
    c.wait_for("!!document.querySelector('article.shoot:nth-of-type(2) .queued')", 15)
    case("Save: the shoot is in the queue, the card says so, and the look-right line is gone with the button",
         "In your editing queue, due" in c.text("article.shoot:nth-of-type(2) .queued")
         and c.js("!document.querySelector('article.shoot:nth-of-type(2) .q-ask') && !document.querySelector('article.shoot:nth-of-type(2) .add')"))
    q = json.loads((Path(ENV["STUDIO_HOME"]) / "queue.json").read_text(encoding="utf-8"))
    case("... and it really is in the scratch queue with that date", any(x.get("shoot") == "s2" and x.get("due") == "2027-02-03" for x in q["shoots"]))
    # the sneak peeks
    line = c.text("article.shoot:nth-of-type(1) .peeks-line")
    case("the sneak peeks line in the browser: hers, then the way to change them; only its first sentence is bold",
         line == HERS["peeks"] + " " + O["peeks_change"]
         and c.text("article.shoot:nth-of-type(1) .peeks-line b") == "I picked six photos that could be great sneak peeks to send your client.", line)
    c.click("article.shoot:nth-of-type(1) .pk.again")
    case("Pick again still opens its box", shown("article.shoot:nth-of-type(1) .peeks-ask"))
    c.click("article.shoot:nth-of-type(1) .peeks-ask input")
    c.type_text("more wide shots")
    c.click("article.shoot:nth-of-type(1) .peeks-ask .send")
    c.wait_for("document.querySelector('article.shoot:nth-of-type(1) .peeks-state').textContent.length > 0", 10)
    asks = Path(night) / "_studio" / "peeks-asks.json"
    case("... and sending a note still reaches the Assistant", asks.exists() and "more wide shots" in asks.read_text(encoding="utf-8"), c.text("article.shoot:nth-of-type(1) .peeks-state"))
    case("the next step is under the shoots and above the details", c.text(".next-step") == W["start"] + " " + O["come_back"]
         and c.js("(() => { const n = document.querySelector('.next-step').getBoundingClientRect(), s = document.querySelector('.shoots').getBoundingClientRect(), d = document.querySelector('.cards').getBoundingClientRect(); return n.top >= s.bottom - 1 && n.bottom <= d.top + 1; })()"))
    case("nothing the page shows says Claude or offers a reel", c.js("!/Claude|into a reel/.test(document.body.innerText)"))
    c.click("a.where")
    c.wait_for("document.getElementById('open-toast').classList.contains('on')", 10)
    case("the where-box's own button still works", c.js("document.getElementById('open-toast').textContent").startswith("Opened"), c.js("document.getElementById('open-toast').textContent"))
    case("the page asked for nothing outside this computer and threw no error", not c.outside_requests() and not c.page_errors(), (c.outside_requests(), c.page_errors()))
    # the server gone: the button says so in place
    c.js("window.__f = window.fetch; window.fetch = () => Promise.reject(new Error('gone'))")
    c.click("article.shoot:nth-of-type(1) .open-shoot")
    c.wait_for("document.querySelector('article.shoot:nth-of-type(1) .open-state').textContent.length > 12", 10)
    case("the Assistant not answering: the line under the button says so, with 'the Assistant'", c.text("article.shoot:nth-of-type(1) .open-state") == O["not_running"])
    c.js("window.fetch = window.__f")
    for width in (390, 336):
        c.phone(width, 844)
        c.open(base + "/report.html")
        c.wait_for("document.querySelectorAll('article.shoot').length === 2", 15)
        case("a phone (%d wide): no sideways scroll, and Open this folder is big enough to press" % width,
             no_sideways(c, width) and c.rect("article.shoot:nth-of-type(1) .open-shoot")["h"] >= 36,
             c.js("[document.documentElement.scrollWidth, window.innerWidth]"))
    c.desktop()


def check_cards_browser(c, cards_base):
    import this_computer
    APP = this_computer.FILES_APP
    c.open(cards_base + "/report.html")
    c.wait_for("document.querySelectorAll('iframe.card-frame').length === 2", 15)
    c.wait_for("Array.from(document.querySelectorAll('iframe.card-frame')).every(f => f.contentDocument && f.contentDocument.querySelector('.open-shoot'))", 20)
    case("the shoot's page: each card's section has Open this folder on every shoot",
         c.js("Array.from(document.querySelectorAll('iframe.card-frame')).map(f => f.contentDocument.querySelectorAll('.open-shoot').length)") == [2, 1])
    c.js("document.querySelectorAll('iframe.card-frame')[1].contentDocument.querySelector('.open-shoot').click()")
    c.wait_for("document.querySelectorAll('iframe.card-frame')[1].contentDocument.querySelector('.open-state').textContent.startsWith('Opened')", 10)
    case("pressed inside card 2's section, it opens card 2's shoot", c.js("document.querySelectorAll('iframe.card-frame')[1].contentDocument.querySelector('.open-state').textContent") == "Opened 2026-06-25 Reception in %s." % APP)
    case("the next step shows once, on the shoot's page, not inside the cards",
         c.js("document.querySelectorAll('.next-step').length") == 1
         and c.js("Array.from(document.querySelectorAll('iframe.card-frame')).every(f => !f.contentDocument.querySelector('.next-step'))"))


def check_fake_night(c, work, port):
    """With Pillow: the pretend backup with real pictures and a real index, so Show me more and Rename run for real."""
    import fake_night
    import first_look
    import this_computer
    APP = this_computer.FILES_APP
    night = work / "2026-06-24 fake card"
    fake_night.main(str(night))
    code, said = run("report_page.py", str(night))
    case("(the pretend backup with pictures is made)", code == 0, said[-200:])
    srv = Server(night, port)
    try:
        c.open(srv.base + "/report.html")
        c.wait_for("document.querySelectorAll('article.shoot').length === 2", 15)
        case("two JPEG shoots in one day: no 'days', and the sneak peeks are not called marked",
             c.text(".why-folders") == first_look.OUR_WORDS["why_shoots"].format(n="two") and "aren't marked in Lightroom" in c.text("article.shoot:nth-of-type(1) .peeks-line"))
        c.click("article.shoot:nth-of-type(1) .pk.more")
        c.wait_for("document.querySelectorAll('article.shoot:nth-of-type(1) .peeks-more .slot .cand').length === 6", 15)
        case("Show me more still opens their six in six spots", True)
        c.click("article.shoot:nth-of-type(1) .pk.cancel2")
        # Rename on the page: the press still reaches the Assistant and the card says what happened, in plain
        # words that say "the Assistant" (Nicole, Nov 22). (The pretend backup has no sorted-photo records, so the rename itself
        # stops, as it should; a rename followed by Open this folder is checked on the routes.)
        c.click("#s1")
        c.type_text("Lani swim")
        c.click(".go[data-shoot='s1']")
        c.wait_for("/the Assistant/.test(document.querySelector(\".state[data-for='s1']\").textContent)", 40)
        said = c.text(".state[data-for='s1']")
        case("Rename on the page still reaches the Assistant, and what stopped it is said with 'the Assistant', never Claude",
             "Tell the Assistant and it'll sort it out." in said and "Claude" not in said, said)
        c.click("article.shoot:nth-of-type(1) .open-shoot")
        c.wait_for("document.querySelector('article.shoot:nth-of-type(1) .open-state').textContent.startsWith('Opened')", 10)
        case("Open this folder works on the pretend backup with pictures too", c.text("article.shoot:nth-of-type(1) .open-state") == "Opened 2026-06-24 Beach in %s." % APP,
             c.text("article.shoot:nth-of-type(1) .open-state"))
    finally:
        srv.stop()


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=9470)
    ap.add_argument("--no-chrome", action="store_true", help="the words, the pages as written and the routes only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792, 8799) for p in range(a.port, a.port + 70)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="report-v26-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    ENV.update({"STUDIO_HOME": str(work / "studio-home"), "STUDIO_NO_WINDOWS_FOR_TESTS": "1", "STUDIO_CARD_FOR_TESTS": "none"})
    os.environ.update(ENV)   # this program reads first_look's words itself; nothing here may touch the real ~/.studio
    servers = []
    try:
        group("the words", check_words)
        made = group("the pages, as written", check_pages, work)
        cards = group("a shoot on two cards", check_cards, work)
        if made and cards:
            one = Server(made["two_days"], a.port)
            servers.append(one)
            two = Server(cards[1], a.port + 30)
            servers.append(two)
            case("the report servers are this test's own", bool(one.base and two.base) and a.port <= one.port < a.port + 20 and a.port + 30 <= two.port < a.port + 50)
            if one.base and two.base:
                group("the report's server", check_routes, one.base, made["two_days"], two.base, cards[0], cards[1])
                if a.no_chrome or not chrome_drive.find_chrome():
                    skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
                else:
                    with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                        group("the report in a browser", check_browser, c, one.base, made["two_days"])
                        group("a shoot on two cards in a browser", check_cards_browser, c, two.base)
                        try:
                            import PIL  # noqa: F401
                            have = True
                        except ImportError:
                            have = False
                        if have:
                            group("Show me more and Rename, on a pretend backup with pictures", check_fake_night, c, work, a.port + 55)
                        else:
                            skip("Show me more and Rename in a browser: no Pillow here, so the pretend backup with pictures cannot be made")
    finally:
        for s in servers:
            s.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
