#!/usr/bin/env python3
"""Your year and the monthly recap (Nicole's v28, her wrapped.html; ours: wrapped.py on the posting server).

    python3 tests/guard.py 3000 python3 tests/wrapped_check.py [--port 9870] [--work <a folder to keep>] [--no-chrome]

What it does, on a pretend Assistant in a throwaway folder under /private/tmp (tests/fake_kit.py: two pretend
kits; a scratch STUDIO_HOME; pretend records written into the kits and the scratch home; no real kit, no real
drive, nothing of the real ~/.studio; the day is fixed with STUDIO_TODAY; the folder button opens nothing):
  * a PNG is really a PNG: the size, every chunk's checksum, nothing after the end; anything else refused;
  * the counts, each from the record it is counted from: reels (each reel ONCE however often it was made, on the day of its first make,
    Nicole's v29 2.2: the reel page's makes, a chat reel, talking reels of every version; and the case that fails
    if the switch is turned back: three makes of one reel in a month are 1 reel made), carousels and sets of stories (one per design saved from, by the first save), posts,
    photos off the cards (shoots of 10 or more), the shoots, the top shoot, the weeks posted, since; a month and
    a year; never a path in what the page is handed;
  * the home page's two answers: which month the recap card shows ("so far." / "recapped." / no card) and when
    the Your year bar shows (Dec 1 to Jan 15, first activity by Jan 31 of that year, or forced);
  * the routes: the page, the numbers (not for another website), saving a story (only this server's own page;
    only a real 1080x1920 PNG; a name made by the server; never over a file; a new name each time), the folder
    button;
  * her words on the page, compared with her own page when her handoff is on this computer; "your assistant",
    never "Claude"; no em dash; nothing from the internet;
  * the page in a HIDDEN Chrome: the stories play, Next / Back / Pause / Start over and the arrow keys, Save this
    one and Save all of them (the files really are 1080x1920 PNGs in "Stories to share"), the Open the folder
    button beside the line that says where they went, nothing moving under prefers-reduced-motion, phone width.

The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only. The pretend kits are drawn with the
Mac's own sips (fake_kit.py), so on a PC everything is skipped.
"""
import argparse
import http.client
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/nicole_nov22.py
import nicole_nov22  # noqa: E402  Nicole, Nov 22: everything is the Assistant

TODAY = "2026-11-17"
A, B = "2026-11-01 Hannah", "2026-11-01 Katie Austin Maternity"


def skip(line):
    print("SKIP  " + line, flush=True)


def ts(iso):
    return datetime.fromisoformat(iso).timestamp()


def png(w=1080, h=1920, tail=b"", break_crc=False, colour=2):
    """A real PNG of one flat colour, made in plain Python."""
    def chunk(kind, data, bad=False):
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc ^ (1 if bad else 0))
    px = 3 if colour == 2 else 4
    raw = (b"\x00" + bytes([240, 127, 90, 255][:px]) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, colour, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 1), bad=break_crc) + chunk(b"IEND", b"") + tail)


def png_size(b):
    return struct.unpack(">II", b[16:24]) if b[:8] == b"\x89PNG\r\n\x1a\n" else None


def her_page():
    roots = [ROOT / "reference-private"]
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"], capture_output=True, text=True, timeout=20).stdout.strip()
        if out:
            roots.append((ROOT / out).resolve().parent / "reference-private")
    except (OSError, subprocess.SubprocessError):
        pass
    for r in roots:
        for f in sorted(r.glob("nicole-handoff-v28-*/Carousel designer and reel picker/pages/wrapped.html")):
            return f
    return None


class World:
    def __init__(self, work, port):
        self.work, self.port0, self.port, self.proc = work, port, None, None
        self.home = work / "studio"
        self.assistant = work / "The Assistant"
        self.content = self.assistant / "Your Content"
        self.share = self.assistant / "Stories to share"
        self.env = dict(os.environ, STUDIO_HOME=str(self.home), STUDIO_TODAY=TODAY, PYTHONIOENCODING="utf-8",
                        ASSISTANT_TEST_OPEN="front", STUDIO_CARD_FOR_TESTS="none")

    def build(self):
        for name, n in (("Hannah", 14), ("Katie Austin Maternity", 12)):
            r = subprocess.run([sys.executable, str(HERE / "fake_kit.py"), str(self.work), "--photos", str(n), "--name", name],
                               capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                raise RuntimeError("fake_kit.py: " + (r.stdout + r.stderr)[-300:])
        a, b = self.content / A, self.content / B
        # kit A: three makes on the reel page (two in November, one in October; one a saved video), a line that is
        # no reel (no project), a chat reel the page's list already knows (never counted twice); two talking
        # reels (the open one made in November, the other in September); a carousel design saved twice (once in
        # October, again in November: ONE carousel, October's), another in November; a set of stories in November
        self.put(a / ".kit" / "reel-page.json", {"v": 1, "saved": {"picks": [{"n": 3, "h": ""}, {"n": 1, "h": "+"}, {"n": 999, "h": ""}]}, "made": [
            {"project": "Hannah reel", "when": ts("2026-11-03T10:00:00")},
            {"video": "Hannah b-roll.mp4", "when": ts("2026-11-09T10:00:00"), "version": "v2"},
            {"project": "Hannah reel old", "when": ts("2026-10-20T10:00:00")},
            {"picks": "1,2", "when": ts("2026-11-10T10:00:00")}, "odd"]})
        self.put(a / ".kit" / "talking.json", {"v": 1, "current": "v2", "made": [{"project": "Hannah talking reel 2", "when": ts("2026-11-12T09:00:00")}],
                                                "versions": [{"id": "v1", "name": "Talking reel 1", "data": {"made": [{"project": "Hannah talking reel", "when": ts("2026-09-05T09:00:00")}]}},
                                                             {"id": "v2", "name": "Talking reel 2"}]})
        rec = json.loads((a / ".kit" / "kit.json").read_text(encoding="utf-8"))
        rec["reel"] = {"project": "Hannah reel", "made": "2026-11-03T10:00:01"}
        rec["laid_out"] = [{"base": "Hannah carousel 1", "files": [], "saved": "2026-10-25T08:00:00", "design": "d1", "token": "t1"},
                           {"base": "Hannah carousel 1 (2)", "files": [], "saved": "2026-11-05T08:00:00", "design": "d1", "token": "t2"},
                           {"base": "Hannah carousel 2", "files": [], "saved": "2026-11-06T08:00:00", "design": "d2", "token": "t3"}]
        rec["carousel_set"] = {"kind": "laid-out", "base": "Hannah carousel 2", "files": [], "saved": "2026-11-06T08:00:00", "design": "d2", "token": "t3"}
        rec["stories_laid_out"] = [{"base": "Hannah stories 1", "files": [], "saved": "2026-11-07T08:00:00", "design": "s1", "token": "t4"}]
        self.put(a / ".kit" / "kit.json", rec)
        # kit B: only a reel made from the chat the older way (the page's list knows nothing of it), in November
        rec = json.loads((b / ".kit" / "kit.json").read_text(encoding="utf-8"))
        rec["reel"] = {"project": "Katie reel", "made": "2026-11-15T12:00:00"}
        self.put(b / ".kit" / "kit.json", rec)
        self.put(self.home / "posting.json", {"interval": None, "reminded": {}, "pieces": [
            {"id": "p1", "name": "Hannah reel", "status": "posted", "posted_at": "2026-11-04T18:00:00"},
            {"id": "p2", "name": "Hannah carousel", "status": "posted", "posted_at": "2026-11-11T18:00:00"},
            {"id": "p3", "name": "Old one", "status": "posted", "posted_at": "2026-10-02T18:00:00"},
            {"id": "p4", "name": "No day", "status": "posted"},
            {"id": "p5", "name": "Katie reel", "status": "green", "date": "2026-11-20"},
            {"id": "p6", "name": "Not started", "status": "red"}, "odd"]})
        # the editing queue: a November backup with a shoot of 231 photos and one of 9 (too few to count), an
        # October backup of 120, and the November backup's big shoot listed twice (one backup, one shoot)
        nov, octo = str(self.work / "gone" / "2026-11-02 card" / "_studio"), str(self.work / "gone" / "2026-10-10 card" / "_studio")
        self.put(self.home / "queue.json", {"asked": True, "on": True, "shoots": [
            {"id": "q1", "shoot": "s1", "name": "Hannah", "studio": nov, "count": 231, "status": "waiting", "added": "2026-11-02T20:00:00", "thumbs": []},
            {"id": "q2", "shoot": "s2", "name": "Test frames", "studio": nov, "count": 9, "status": "archived", "added": "2026-11-02T20:00:00", "thumbs": []},
            {"id": "q3", "shoot": "s1", "name": "Autumn", "studio": octo, "count": 120, "status": "finished", "added": "2026-10-10T20:00:00", "thumbs": []}]})
        (self.assistant / "brand-homebase.md").write_text("# Brand Homebase\n\n- Name / business: Nicole Hill Photography\n- Instagram: @nicolelhill_.\n", encoding="utf-8")

    @staticmethod
    def put(path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")

    def start(self):
        f = self.home / "posting-url.txt"
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.port0)], env=self.env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        chrome_drive.wait_until(lambda: f.exists() and f.read_text(encoding="utf-8").strip(), 30, every=0.1, what="the page server's address")
        self.port = int(re.search(r":(\d+)/", f.read_text(encoding="utf-8")).group(1))
        chrome_drive.wait_until(lambda: self.http("GET", "/wrapped.html")[0] == 200, 30, every=0.1, what="the page")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def http(self, method, path, raw=None, headers=None, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        try:
            h = dict(headers or {})
            if host:
                h["Host"] = host
            c.request(method, path, body=raw, headers=h)
            r = c.getresponse()
            return r.status, r.read()
        finally:
            c.close()

    def get_json(self, path, headers=None):
        code, raw = self.http("GET", path, headers=headers)
        try:
            return code, json.loads(raw.decode("utf-8"))
        except ValueError:
            return code, None

    def base(self):
        return "http://127.0.0.1:%d" % self.port

    def shared(self):
        return sorted(p.name for p in self.share.iterdir()) if self.share.is_dir() else []


# ---------------------------------------------------------------- a PNG is a PNG

def check_png(wr):
    good = png()
    case("a real 1080x1920 PNG is taken", wr.png_ok(good))
    case("one with see-through colour too", wr.png_ok(png(colour=6)))
    case("a PNG of another size is refused", not wr.png_ok(png(1080, 1350)))
    case("a PNG with anything after its end is refused", not wr.png_ok(good + b"<script>"))
    case("a PNG cut short is refused", not wr.png_ok(good[:-20]))
    case("a PNG whose checksum is wrong is refused", not wr.png_ok(png(break_crc=True)))
    case("a JPEG is refused", not wr.png_ok(b"\xff\xd8" + b"\x00" * 5000 + b"\xff\xd9"))
    case("text that says it is a PNG is refused", not wr.png_ok(b"\x89PNG\r\n\x1a\n" + b"A" * 5000))
    case("something that is not bytes is refused", not wr.png_ok("data:image/png;base64,AAAA"))


# ---------------------------------------------------------------- the counts

def check_counts(wr, w):
    day = date.fromisoformat(TODAY)
    d = wr.data(month="2026-11")
    t = d["totals"]
    case("the switch as it ships: each reel once (Nicole, v29 2.2), not every make", wr.COUNT_EACH_MAKE is False)
    case("November: 3 reels (a second reel on the reel page, a talking reel, a chat reel; reel 1 was first made in October, so its November make is no new reel)", t["reels"] == 3, t["reels"])
    by = {s["name"]: s for s in d["shoots"]}
    case("November: Hannah has 2 reels (1 on the page, 1 talking), Katie 1 (from the chat)", by.get(A, {}).get("reels") == 2 and by.get(B, {}).get("reels") == 1, {k: v["reels"] for k, v in by.items()})
    case("a line with no project or video is no reel", by[A]["reels"] == 2)
    case("November: 1 carousel (the design first saved in October stays October's, however often it was saved again)", t["carousels"] == 1, t["carousels"])
    case("November: 1 set of stories", t["stories"] == 1, t["stories"])
    case("November: 2 posts; a post with no day is not counted; 1 ready to go", t["posted"] == 2 and t["ready"] == 1, (t["posted"], t["ready"]))
    case("November: 231 photos taken at 1 photo shoot (9 photos are not a shoot; October's backup is October's)", t["shot"] == 231 and t["photo_shoots"] == 1, (t["shot"], t["photo_shoots"]))
    case("November: 2 shoots shared; the top shoot is Hannah", t["shared_shoots"] == 2 and d["top"] == A, (t["shared_shoots"], d["top"]))
    case("the time saved is hers: 45 a reel, 30 a carousel, 20 a set of stories", t["minutes_saved"] == 3 * 45 + 30 + 20 and d["minutes_each"] == {"reel": 45, "carousel": 30, "stories": 20}, t["minutes_saved"])
    case("November so far: 4 weeks, 2 with a post", t["weeks"] == 4 and t["weeks_posted"] == 2, (t["weeks"], t["weeks_posted"]))
    case("the label, the next month, so far", d["label"] == "November" and d["next"] == "December" and d["so_far"] is True and d["month"] == "2026-11", (d["label"], d["next"], d["so_far"]))
    case("their name and handle, from their Brand Homebase", d["me"] == "Nicole" and d["handle"] == "@nicolelhill_", (d["me"], d["handle"]))
    case("since: the first thing that ever happened (the September talking reel)", d["since"] == "2026-09-05", d["since"])
    case("a shoot's photos: the reel page's order first, only numbers on the list", by[A]["favs"][:2] == [3, 1] and 999 not in by[A]["favs"], by[A]["favs"])
    case("a shoot with no reel order: its first photos", by[B]["favs"][:3] == [1, 2, 3], by[B]["favs"])
    o = wr.data(month="2026-10")
    case("October: 1 reel, 1 carousel, 1 post, 120 photos; recapped, not so far", (o["totals"]["reels"], o["totals"]["carousels"], o["totals"]["posted"], o["totals"]["shot"], o["so_far"]) == (1, 1, 1, 120, False), o["totals"])
    case("October's whole month: 5 weeks", o["totals"]["weeks"] == 5, o["totals"]["weeks"])
    n = wr.data(month="2026-08")
    case("a month with nothing in it says so", n["anything"] is False and n["shoots"] == [] and n["top"] == "", n["totals"])
    y = wr.data(year="2026")
    ty = y["totals"]
    case("2026: 5 reels (six makes, one of them a second make of reel 1), 2 carousels, 1 set of stories, 3 posts, 351 photos", (ty["reels"], ty["carousels"], ty["stories"], ty["posted"], ty["shot"]) == (5, 2, 1, 3, 351), ty)
    case("2026: the label is the year, next year after it, no weeks", y["label"] == "2026" and y["next"] == "next year" and ty["weeks"] == 0 and y["month"] == "", (y["label"], y["next"]))
    case("a year counts only that year (hers counted everything ever)", wr.data(year="2025")["anything"] is False)
    case("with no year named: this year (and last year from Jan 1 to 15)", wr.default_year(day) == 2026 and wr.default_year(date(2027, 1, 15)) == 2026 and wr.default_year(date(2027, 1, 16)) == 2027)
    blob = json.dumps([d, o, y])
    case("what the page is handed holds no path", str(w.work) not in blob and "/private/" not in blob and "\\\\" not in blob)
    ships = wr.COUNT_EACH_MAKE                  # put back exactly as it ships, so a switch turned back still fails below
    wr.COUNT_EACH_MAKE = True
    try:
        e = (wr.data(year="2026")["totals"]["reels"], wr.data(month="2026-11")["totals"]["reels"])
    finally:
        wr.COUNT_EACH_MAKE = ships
    case("the other way of counting (every make, her v28 way): 6 in 2026, 4 in November", e == (6, 4), e)
    case("the chips: hers, a zero left out, one of a thing in the singular", wr.chips(t) == ["231 photos", "3 reels", "1 carousel", "2 posts", "3 hours saved"], wr.chips(t))


def check_once(wr, w):
    """Nicole's v29 2.2: one reel made three times in a month is ONE reel made, and the time saved is one reel's.
    Kit B's reel page gets three makes of its one reel in July (a month with nothing else in it) for these cases
    only; the file is taken away again afterwards, so every other group sees the kit as it was built."""
    f = w.content / B / ".kit" / "reel-page.json"
    case("kit B has no reel page record of its own before this", not f.exists())
    w.put(f, {"v": 1, "saved": {}, "made": [
        {"project": "Katie reel", "when": ts("2026-07-06T10:00:00")},
        {"project": "Katie reel 2", "when": ts("2026-07-06T10:20:00")},
        {"project": "Katie reel 3", "when": ts("2026-07-21T16:00:00"), "variation": 2}]})
    try:
        d = wr.data(month="2026-07")
        t = d["totals"]
        case("three makes of one reel in July: 1 reel made, not 3 (fails if the switch is turned back)", t["reels"] == 1, t["reels"])
        case("the time saved is one reel's: 45 minutes", t["minutes_saved"] == 45, t["minutes_saved"])
        chips = wr.chips(t)
        case("the home page's recap chips follow: \"1 reel\" in the singular, \"45 minutes saved\"", "1 reel" in chips and "45 minutes saved" in chips and not any(c.endswith(" reels") for c in chips), chips)
        by = {s["name"]: s for s in d["shoots"]}
        case("the shoot's own count is 1 too", by.get(B, {}).get("reels") == 1, {k: v["reels"] for k, v in by.items()})
        r = wr.home_answers(day=date(2026, 7, 25), got=wr.gather())["recap"]
        case("the recap card for July says 1 reel", bool(r) and r["month"] == "2026-07" and "1 reel" in r["chips"] and "3 reels" not in r["chips"], r and r["chips"])
        case("the story's line is in the singular for one: \"reel made\"", "pl(D.totals.reels, 'reel made', 'reels made')" in wr.STORIES_JS)
        case("a reel made again in a later month stays in the month it was first made (November has none of Katie's)",
             {s["name"]: s["reels"] for s in wr.data(month="2026-11")["shoots"]}.get(B, 0) == 0)
        ships = wr.COUNT_EACH_MAKE
        wr.COUNT_EACH_MAKE = True
        try:
            every = wr.data(month="2026-07")["totals"]
        finally:
            wr.COUNT_EACH_MAKE = ships
        case("with the switch turned back the same month would say 3 reels and 135 minutes", (every["reels"], every["minutes_saved"]) == (3, 135), every)
    finally:
        f.unlink()
    case("afterwards kit B is as it was built: November has its one chat reel again", {s["name"]: s["reels"] for s in wr.data(month="2026-11")["shoots"]}.get(B) == 1)


def check_home(wr, w):
    got = wr.gather()
    h = wr.home_answers(day=date(2026, 11, 17), got=got)
    r = h["recap"]
    case("Nov 17: the card shows November, so far., with its chips, three photos and where Watch goes",
         bool(r) and (r["month"], r["word"], r["url"]) == ("2026-11", "so far.", "/wrapped.html?m=2026-11") and len(r["photos"]) == 3 and r["chips"][0] == "231 photos", r)
    case("the card's photos are a kit's name and a number, never a path", bool(r) and all(set(p) == {"kit", "n"} and p["kit"] in (A, B) for p in r["photos"]))
    r = wr.home_answers(day=date(2026, 12, 3), got=got)["recap"]
    case("Dec 3 (the first 7 days): last month, recapped.", bool(r) and (r["month"], r["word"], r["label"]) == ("2026-11", "recapped.", "November"), r)
    case("Dec 10 with nothing in December: no card", wr.home_answers(day=date(2026, 12, 10), got=got)["recap"] is None)
    r = wr.home_answers(day=date(2026, 9, 3), got=got)["recap"]
    case("Sep 3 with nothing in August: this month, so far.", bool(r) and (r["month"], r["word"]) == ("2026-09", "so far."), r)
    early = dict(got, since="2026-01-20")
    late = dict(got, since="2026-02-01")
    yb = lambda d, g, force=False: wr.home_answers(day=d, got=g, force_year=force)["year"]  # noqa: E731
    case("the Your year bar: Dec 1, first activity by Jan 31 of that year: shown", yb(date(2026, 12, 1), early) == {"year": "2026", "url": "/wrapped.html?y=2026"}, yb(date(2026, 12, 1), early))
    case("first activity on Feb 1 of that year: not shown", yb(date(2026, 12, 20), late) is None)
    case("Nov 30: not shown", yb(date(2026, 11, 30), early) is None)
    case("Jan 15 of the next year: still shown, for the year that ended", (yb(date(2027, 1, 15), early) or {}).get("year") == "2026")
    case("Jan 16: not shown", yb(date(2027, 1, 16), early) is None)
    case("no activity at all: not shown", yb(date(2026, 12, 10), dict(got, since="")) is None)
    case("?wrapped=1 (forced): shown any time", (yb(date(2026, 6, 1), late, True) or {}).get("year") == "2026")


# ---------------------------------------------------------------- the words

HER_STORY_LINES = ["in photos.", "photos taken", "finished photos", "You had", "You shared", "and every one of them counted", "with the world",
                   "reels made", "You saved about", "making reels, carousels and stories", "That's a whole evening back.", "workday", "created",
                   "Your top shoot", "You posted", "Your posts", "are on their way", "Every single week. So consistent!", "on Instagram. Keep it going!",
                   "on Instagram. Way to show up!", "more ready to go", "Here's to", "next year.", "Made with"]
HERS_NOT_OURS = ("Sample · test pages only", "Monthly recap · test pages only", "All the animation samples",
                 "The numbers are real, but some come from testing (every test reel counts), so they look busier than they were.")


def check_words(wr, w):
    year, month = wr.page_html(None, "2026"), wr.page_html("2026-11", None)
    for name, page in (("the year's page", year), ("the month's page", month)):
        case(name + ": never \"Claude\", no em dash, nothing from the internet",
             "claude" not in page.lower() and "—" not in page and not re.search(r"https?://", page) and "fonts.googleapis" not in page)
    case("the year: her heading, her lede with \"the Assistant\"", "Your year, <em>wrapped.</em>" in year and "Your year with the Assistant, story by story" in year)
    case("the month: \"Your November, so far.\" and her lede", "Your November, <em>so far.</em>" in month and "Your November in photos, reels and posts." in month)
    case("a month that is over: \"recapped.\"", "Your October, <em>recapped.</em>" in wr.page_html("2026-10", None))
    case("her buttons, by her names", all((">%s<" % b) in year for b in ("‹ Back", "Pause", "Next ›", "Start over", "Save this one to share", "Save all of them")))
    case("the page says the time saved is an estimate, beside her line about it", "Time saved counts about 45 minutes a reel, 30 a carousel and 20 a set of stories, done by hand. It is an estimate." in year)
    case("her story lines are all there", all(l in wr.STORIES_JS for l in HER_STORY_LINES), [l for l in HER_STORY_LINES if l not in wr.STORIES_JS])
    case("none of her test-only lines", not any(l in year or l in month for l in HERS_NOT_OURS))
    case("every story is skipped as an animation under prefers-reduced-motion", "prefers-reduced-motion: reduce" in wr.STORIES_JS and "STILL ? S[P.i].dur : P.t" in wr.STORIES_JS)
    case("no serif unless it is switched on", wr.ACCENT_SERIF is False and "Assistant Serif" not in year.split("<script>")[0])
    hers = her_page()
    if not hers:
        return skip("her own page is not on this computer (reference-private): her words were compared with the list above only")
    her = nicole_nov22.read(hers)   # Nicole, Nov 22: everything is the Assistant
    side = ["Tap the right side for the next one, the left side to go back, and hold to pause.", "Save this one to share", "Save all of them", "Start over",
            "Each one is a 1080×1920 picture, the size of an Instagram story, saved in your Assistant folder under Stories to share.",
            "Time saved counts about 45 minutes a reel, 30 a carousel and 20 a set of stories, done by hand.", "Getting your year ready…",
            "I can't reach your records right now.", "No shoots yet. Make posts from a shoot first.", "in your Assistant folder, under Stories to share."]
    plain = year + json.dumps(wr.WORDS, ensure_ascii=False)
    case("these lines of ours are on her page, letter for letter", all(l.replace("'", "\\'") in her or l in her for l in side + HER_STORY_LINES), [l for l in side + HER_STORY_LINES if l not in her and l.replace("'", "\\'") not in her])
    case("and hers are on ours", all(l in plain or l in wr.STORIES_JS for l in side))
    # every quoted line of her nine stories is in ours (the text() calls: her words on the pictures)
    her_text = set(re.findall(r"text\((?:`([^`$]{6,})`|'([^'$]{6,})'|\"([^\"$]{6,})\")", her))
    lines = [next(x for x in m if x) for m in her_text]
    made_with = "Made with The Assistant by Horizon Found"      # ours spells it from brand.py (the name is one switch)
    case("\"Made with The Assistant by Horizon Found\" is put together from the product's own name", made_with in lines and "`Made with ${CFG.product} ${CFG.maker}`" in wr.STORIES_JS
         and "Made with %s %s" % (wr.brand.PRODUCT, wr.brand.MAKER) == made_with)
    lines = [l for l in lines if l != made_with]
    case("every plain line her stories draw is drawn by ours (%d lines)" % len(lines), lines and all(l in wr.STORIES_JS for l in lines), [l for l in lines if l not in wr.STORIES_JS])


# ---------------------------------------------------------------- the routes

def check_routes(wr, w):
    code, raw = w.http("GET", "/wrapped.html?m=2026-11")
    case("the month's page opens", code == 200 and b"Your November" in raw)
    case("the year's page opens", w.http("GET", "/wrapped.html")[0] == 200 and w.http("GET", "/wrapped.html?y=2026")[0] == 200)
    case("the page asked for under another name (not this server's) gets nothing", w.http("GET", "/wrapped.html", host="evil.example:%d" % w.port)[0] == 403)
    code, d = w.get_json("/wrapped-data?m=2026-11")
    case("the numbers arrive, the same as counted", code == 200 and d and d["ok"] and d["totals"]["reels"] == 3 and d["totals"]["shot"] == 231, d and d.get("totals"))
    case("the numbers are not for another website", w.get_json("/wrapped-data?m=2026-11", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403)
    case("a month that is not a month: nothing", w.get_json("/wrapped-data?m=2026-13")[0] == 404 and w.get_json("/wrapped-data?m=../../etc")[0] == 404 and w.get_json("/wrapped-data?m=2026-11&y=2026")[0] == 404)
    case("the serif's file is not served while the serif is off", w.http("GET", "/wrapped-font")[0] == 404)
    good = png()
    own = {"Content-Type": "image/png", "Origin": w.base()}

    def post(path, raw=good, headers=own):
        code, out = w.http("POST", path, raw=raw, headers=headers)
        try:
            return code, json.loads(out.decode("utf-8"))
        except ValueError:
            return code, None
    before = w.shared()
    code, r = post("/share-image?i=3&m=2026-11")
    name1 = "My November 2026 recap - 3 %s.png" % TODAY
    case("a story is saved, under a name the server made", code == 200 and r and r.get("ok") and r.get("file") == name1 and w.shared() == before + [name1], (code, r, w.shared()))
    case("the saved file is the picture, byte for byte", (w.share / name1).read_bytes() == good)
    case("it is in \"Stories to share\", beside Your Content", w.share.parent == w.content.parent)
    other = png(colour=6)
    code, r = post("/share-image?i=3&m=2026-11", raw=other)
    name2 = "My November 2026 recap - 3 %s 2.png" % TODAY
    case("saved again: a new name, the first one untouched", code == 200 and r and r.get("file") == name2 and (w.share / name1).read_bytes() == good and (w.share / name2).read_bytes() == other, (code, r))
    code, r = post("/share-image?i=1&y=2026")
    case("a year's story has the year's name", code == 200 and r and r.get("file") == "My 2026 with The Assistant - 1 %s.png" % TODAY, (code, r))
    n = len(w.shared())
    case("answers hold a file's name, never a path", "/" not in (r or {}).get("file", "/"))
    case("a press from another website is refused (its Origin)", post("/share-image?i=1&m=2026-11", headers=dict(own, Origin="http://evil.example"))[0] == 403)
    case("a press another website's page made is refused (the browser's own mark)", post("/share-image?i=1&m=2026-11", headers=dict(own, **{"Sec-Fetch-Site": "cross-site"}))[0] == 403)
    case("sent to another name: refused", w.http("POST", "/share-image?i=1&m=2026-11", raw=good, headers=own, host="evil.example:%d" % w.port)[0] == 403)
    case("anything but image/png is refused", post("/share-image?i=1&m=2026-11", headers={"Content-Type": "application/json", "Origin": w.base()})[0] == 415)
    code, r = post("/share-image?i=1&m=2026-11", raw=b"\x89PNG\r\n\x1a\n" + b"<html>" * 800)
    case("something that only says it is a PNG is refused, in her words", code == 400 and r and r.get("words") == "That isn't a picture.", (code, r))
    case("a PNG of another size is refused", post("/share-image?i=1&m=2026-11", raw=png(1080, 1350))[0] == 400)
    case("a body over the limit is refused before it is read", w.http("POST", "/share-image?i=1&m=2026-11", raw=b"x", headers=dict(own, **{"Content-Length": str(wr.PNG_CAP + 1)}))[0] == 413)
    case("a story number that is not 1 to 9, or none: refused", post("/share-image?i=0&m=2026-11")[0] == 400 and post("/share-image?i=10&m=2026-11")[0] == 400 and post("/share-image?m=2026-11")[0] == 400)
    case("a name from the page is not taken (any extra word in the address is refused)", post("/share-image?i=1&m=2026-11&name=../../evil")[0] == 400)
    case("a month that is not a month: refused", post("/share-image?i=1&m=../../x")[0] == 400)
    case("nothing was written by any refused press", len(w.shared()) == n and not [p for p in w.assistant.rglob("*evil*")], w.shared())
    j = {"Content-Type": "application/json", "Origin": w.base()}
    code, r = post("/share-open", raw=b"{}", headers=j)
    case("the folder button: the line says what opened (nothing is opened in this test)", code == 200 and r and r.get("ok") and r.get("words", "").startswith("Opened Stories to share in "), (code, r))
    case("the folder button takes nothing from the page", post("/share-open", raw=b'{"path": "/"}', headers=j)[0] == 400)
    case("the folder button is not for another website", post("/share-open", raw=b"{}", headers=dict(j, Origin="http://evil.example"))[0] == 403)


# ---------------------------------------------------------------- the page, in a hidden Chrome

def check_page(c, w, wr):
    before = w.shared()
    c.open(w.base() + "/wrapped.html?m=2026-11")
    c.wait_for("window.__wrapped && document.getElementById('wait').hidden", seconds=120)
    n = c.js("window.__wrapped.stories()")
    case("all nine stories have something to say for this month", n == 9, n)
    case("a bar at the top for each story", c.count("#bars i") == n)
    case("the photos on the stories came through the kit's small copies", c.js("performance.getEntriesByType('resource').filter(r => r.name.includes('/kit-photo?')).length") > 5)
    case("the canvas is 1080x1920", c.js("[document.getElementById('cv').width, document.getElementById('cv').height]") == [1080, 1920])
    colours = "(() => { const d = document.getElementById('cv').getContext('2d').getImageData(0, 0, 1080, 1920).data; let s = new Set(); for (let i = 0; i < d.length; i += 40001 * 4) s.add(d[i] + ',' + d[i+1] + ',' + d[i+2]); return s.size; })()"
    try:                                        # the first story fades in: give it its two seconds
        c.wait_for(colours + " > 3", seconds=15, every=0.2)
        drawn = True
    except chrome_drive.Timeout:
        drawn = False
    case("the stories are drawn (the first one is not blank)", drawn)
    c.screenshot("wrapped-month.png")
    c.click("#next")
    case("Next goes to the next story", c.js("window.__wrapped.at()") == 1)
    c.click("#prev")
    case("Back goes back", c.js("window.__wrapped.at()") == 0)
    c.key("ArrowRight"); c.key("ArrowRight")
    case("the right arrow key goes on", c.js("window.__wrapped.at()") == 2)
    c.key("ArrowLeft")
    case("the left arrow key goes back", c.js("window.__wrapped.at()") == 1)
    c.click("#pp")
    case("Pause pauses, and the button then says Play", c.text("#pp") == "Play")
    c.click("#pp")
    case("and Play plays", c.text("#pp") == "Pause")
    c.click("#tapR")
    case("a tap on the right side goes on", c.js("window.__wrapped.at()") == 2)
    c.click("#tapL")
    case("a tap on the left side goes back", c.js("window.__wrapped.at()") == 1)
    c.click("#again")
    case("Start over starts over", c.js("window.__wrapped.at()") == 0)
    case("the folder button is not there before anything is saved", c.js("document.getElementById('openF').hidden") is True)
    c.click("#pp")
    c.click("#saveOne")
    c.wait_for("document.getElementById('said').textContent.startsWith('Saved')", seconds=60)
    new = [x for x in w.shared() if x not in before]
    name = "My November 2026 recap - 1 %s.png" % TODAY
    case("Save this one to share: one picture in Stories to share", len(new) == 1 and new[0].startswith("My November 2026 recap - 1 "), new)
    case("her line says where it went", c.text("#said") == "Saved \"%s\" in your Assistant folder, under Stories to share." % (new[0] if new else name), c.text("#said"))
    data = (w.share / new[0]).read_bytes() if new else b""
    case("the saved picture is a real 1080x1920 PNG", wr.png_ok(data) and png_size(data) == (1080, 1920))
    case("the Open the folder button is right beside that line", c.js("(() => { const b = document.getElementById('openF'), s = document.getElementById('said'); return !b.hidden && b.parentElement === s.parentElement && b.textContent === 'Open the folder'; })()"))
    c.click("#openF")
    c.wait_for("document.getElementById('said').textContent.startsWith('Opened')", seconds=20)
    case("pressing it says what opened", c.text("#said").startswith("Opened Stories to share in "), c.text("#said"))
    before2 = w.shared()
    c.click("#saveAll")
    c.wait_for("document.getElementById('said').textContent.startsWith('Saved all')", seconds=180)
    new = [x for x in w.shared() if x not in before2]
    case("Save all of them: one picture for each story, none written over", len(new) == n and set(before2) <= set(w.shared()), new)
    case("each a real 1080x1920 PNG, and not all the same picture", all(wr.png_ok((w.share / x).read_bytes()) for x in new) and len({(w.share / x).stat().st_size for x in new}) > 3)
    case("her line for all of them", c.text("#said") == "Saved all %d in your Assistant folder, under Stories to share." % n, c.text("#said"))
    case("the page asked for nothing from the internet", not c.outside_requests(), c.outside_requests()[:3])
    case("no errors on the page", not c.page_errors(), c.page_errors()[:3])
    # a month with nothing in it; a year
    c.open(w.base() + "/wrapped.html?m=2026-08")
    c.wait_for("document.getElementById('wait').textContent.startsWith('Nothing')", seconds=30)
    case("a month with nothing in it says so, in her words", c.text("#wait") == "Nothing from August yet.", c.text("#wait"))
    c.open(w.base() + "/wrapped.html?y=2026")
    c.wait_for("window.__wrapped && document.getElementById('wait').hidden", seconds=120)
    case("the year plays too, with its own numbers", c.js("window.__wrapped.data().totals.reels") == 5 and c.js("window.__wrapped.data().month") == "")
    # less motion asked for: each story is shown finished
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
    c.open(w.base() + "/wrapped.html?m=2026-11")
    c.wait_for("window.__wrapped && document.getElementById('wait').hidden", seconds=120)
    case("under prefers-reduced-motion the page knows", c.js("window.__wrapped.still") is True)
    snap = "(() => { const d = document.getElementById('cv').getContext('2d').getImageData(0, 0, 1080, 1920).data; let s = 0; for (let i = 0; i < d.length; i += 997 * 4) s = (s * 31 + d[i] + d[i+1] * 3 + d[i+2] * 7) >>> 0; return s; })()"
    c.click("#next"); c.click("#pp")           # the second story (photos falling in hers), paused or not it must not move
    c.click("#pp")
    time.sleep(0.3)
    one = c.js(snap)
    time.sleep(0.9)
    two = c.js(snap)
    case("and nothing moves: the story is shown finished", c.js("window.__wrapped.at()") == 1 and one == two, (one, two))
    c.cdp("Emulation.setEmulatedMedia", {"features": []})
    c.phone(390, 844)
    c.open(w.base() + "/wrapped.html?m=2026-11")
    c.wait_for("window.__wrapped && document.getElementById('wait').hidden", seconds=120)
    case("phone width: no sideways scroll", c.js("document.documentElement.scrollWidth <= window.innerWidth + 1"), c.js("[document.documentElement.scrollWidth, window.innerWidth]"))
    case("phone width: the buttons are on the screen's width", c.js("[...document.querySelectorAll('.btn:not([hidden])')].every(b => { const r = b.getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth + 1; })"))


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder under /private/tmp for this run, kept afterwards (default: a throwaway one, removed at the end)")
    ap.add_argument("--port", type=int, default=9870)
    ap.add_argument("--no-chrome", action="store_true", help="everything but the page in a browser")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792, 8799) for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    if os.name == "nt" or not shutil.which("sips"):
        skip("the pretend kits are drawn with the Mac's own sips: nothing here runs on this computer")
        return 0
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="wrapped-check-", dir="/private/tmp")).resolve()
    work = base / time.strftime("run-%H%M%S")
    w = World(work, a.port)
    os.environ.update(STUDIO_HOME=str(w.home), STUDIO_TODAY=TODAY, ASSISTANT_TEST_OPEN="front", STUDIO_CARD_FOR_TESTS="none")
    try:
        w.build()
        sys.path.insert(0, str(SCRIPTS))
        import wrapped as wr
        case("the test's own scratch home, never the real one", Path(wr.HOME) == w.home and ".studio" not in str(wr.HOME))
        group("a PNG is a PNG", check_png, wr)
        group("the counts", check_counts, wr, w)
        group("each reel once", check_once, wr, w)
        group("the home page's two answers", check_home, wr, w)
        group("the words", check_words, wr, w)
        w.start()
        case("the page server is this test's own (port %d)" % w.port, a.port <= w.port < a.port + 20)
        group("the routes", check_routes, wr, w)
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1000)) as c:
                group("the page", check_page, c, w, wr)
    finally:
        w.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(base), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
