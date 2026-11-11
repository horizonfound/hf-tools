#!/usr/bin/env python3
"""Checks on reminders.py (posting-day reminders on their calendar): Nicole's 19 acceptance checks from handoff
v21, ported, plus ours. Everything runs against a PRETEND calendar in a throwaway STUDIO_HOME. No real calendar,
no Calendar app and no osascript are ever touched: the one function that would is replaced by a tripwire, and
the last check says it was never reached.

    python3 tests/reminders_check.py

Every line must say PASS. Nicole's checks 17 to 19 are on the queue page's own words (wired in stage 4): they read
posting_queue.py's page, and tests/posting_reminders_page_check.py checks the same on the real page in a browser.
Python 3.9, standard library only, a Mac or a PC.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
TMP = Path(tempfile.mkdtemp(prefix="reminders-check-")).resolve()
STUDIO = TMP / "studio"
os.environ["STUDIO_HOME"] = str(STUDIO)
os.environ["REMINDERS_BACKEND"] = "file"          # anything that asks for "the usual" calendar gets files, never the Mac's
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS))
import reminders as R   # noqa: E402

REAL = []


def tripwire(*a, **k):
    REAL.append(a)
    raise AssertionError("a test reached the real Calendar")


REAL_OSA = R._osascript            # kept only to be run with the Mac's programs replaced (see "Mac runner")
R._osascript = tripwire
fails = 0
count = 0


def check(name, cond, seen=None):
    global fails, count
    count += 1
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond or seen is None else "\n      saw: " + repr(seen)[:600]), flush=True)
    fails += 0 if cond else 1


class Pretend:
    """A pretend Calendar app behind MacCalendar's runner: it understands the three scripts by which one it is."""

    def __init__(self):
        self.events, self.calls, self.fail, self.n = {}, [], None, 0
        self.cals = [("Home", "true"), ("Work", "true"), ("Birthdays", "true"), ("US Holidays", "false"),
                     ("Siri Suggestions", "true"), ("Scheduled Reminders", "true"), ("Shared by Sam", "false"),
                     ("0123456789abcdef0123456789abcdef", "true"), ("Home", "true"), ("Café ☕", "true")]
        self.during = None

    def run(self, script, args):
        if self.during:
            self.during()
        if self.fail is not None:
            self.calls.append(("fail",))
            raise self.fail
        if script is R.MAC_SET:
            cal, uid, y, mo, dd, hh, mi, mins, ttl, nts, keep = args
            there = bool(uid) and uid in self.events and self.events[uid]["cal"] == cal
            if keep == "keep":
                self.calls.append(("move", uid))
                if not there:
                    return "\n"                      # ours is gone: with "keep" nothing is made, nothing printed
                nts = self.events[uid]["notes"]
            elif not there:
                self.n += 1
                uid = f"UID-{self.n}"
            self.events[uid] = {"cal": cal, "when": f"{int(y)}-{int(mo):02d}-{int(dd):02d} {int(hh):02d}:{int(mi):02d}",
                                "mins": mins, "title": ttl, "notes": nts}
            if keep == "keep":
                return uid + "\n"
            self.calls.append(("set", uid))
            return uid + "\n"
        if script is R.MAC_REMOVE:
            cal, uid = args
            self.calls.append(("remove", uid))
            if uid in self.events and self.events[uid]["cal"] == cal:
                del self.events[uid]
                return "removed"
            return "gone"
        if script is R.MAC_LIST:
            self.calls.append(("list",))
            return "\n".join(n for n, _ in self.cals) + "\n" + R.MAC_LIST_MARK + "\n" + "\n".join(w for _, w in self.cals) + "\n"
        raise AssertionError("a script the pretend calendar doesn't know")


CAPTION = "MINI SESSIONS are coming to Laguna Beach on December 4th!!!\n\nThis was Hannah's mommy & me session."
WORDS = {"caption": CAPTION, "hooks": ["Hook one", "The photos you'll want framed on your wall by Christmas."], "picked": [1]}


def words(x):
    return WORDS if x["kind"] == "reel" else {"caption": "Carousel caption."}


def queue():
    return {"pieces": [
        {"id": "kit:2026-09-23-hannah-reel", "shoot_id": "kit:2026-09-23-hannah", "shoot_name": "Hannah", "kind": "reel",
         "status": "green", "date": "2026-11-11", "cover": "Photos/41777_06.jpg", "slot": 1},
        {"id": "kit:2026-09-23-hannah-carousel", "shoot_id": "kit:2026-09-23-hannah", "shoot_name": "Hannah", "kind": "carousel",
         "status": "green", "date": "2026-11-13", "cover": "Carousel/Hannah carousel - slide 02.jpg", "slot": 2}],
        "interval": 3.5, "reminded": {}}


def fresh_home():
    shutil.rmtree(STUDIO, ignore_errors=True)
    STUDIO.mkdir(parents=True)


def go(p, backend, **kw):
    """One sync, then its changes merged into the queue, as the caller will do."""
    kw.setdefault("words", words)
    res = R.sync(p, backend, **kw)
    R.merge(p, res["changes"])
    return res


def unfold(data):
    """A calendar file's content lines, unfolded, as text; and whether every rule of the file's shape held."""
    ok = data.endswith(b"\r\n") and b"\n" not in data.replace(b"\r\n", b"") and b"\r" not in data.replace(b"\r\n", b"")
    lines = []
    for raw in data.split(b"\r\n")[:-1]:
        ok = ok and len(raw) <= 75
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            ok = False
        if raw[:1] == b" " and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return [b.decode("utf-8") for b in lines], ok


def ics_text(value):
    out, i = "", 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            out += {"n": "\n", "N": "\n"}.get(value[i + 1], value[i + 1])
            i += 2
        else:
            out += value[i]
            i += 1
    return out


def prop(lines, key, nth=0):
    got = [ln.split(":", 1)[1] for ln in lines if ln.split(":", 1)[0] == key]
    return got[nth] if len(got) > nth else None


try:
    # ------------------------------------------------------------ Nicole's 19, in her order
    print("Nicole's checks (handoff v21)")
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    p = queue()
    reel, car = p["pieces"]

    R.set_reminder(p, reel["id"], "09:00")
    p.pop("remind")                                     # the time was chosen, a calendar never was
    res = go(p, mac)
    check("1 no calendar chosen yet: nothing is made", res["changed"] is False and not cal.calls and "event_uid" not in reel)

    p["remind"] = {"calendar": "Home", "time": "09:00"}
    R.set_reminder(p, car["id"], "18:30")
    res = go(p, mac)
    check("2 both reminders made", res["changed"] is True and len(cal.events) == 2 and res["problem"] is None)
    e = cal.events[reel["event_uid"]]
    check("3 reel: on its day, at its own time, on the chosen calendar", e["when"] == "2026-11-11 09:00" and e["cal"] == "Home" and reel["event_cal"] == "Home")
    check("4 carousel: its own time", cal.events[car["event_uid"]]["when"] == "2026-11-13 18:30")
    check("5 title says what to post", e["title"] == "Post your Hannah reel today")
    check("6 notes: the picked hook", "Your hook, on the first second:\nThe photos you'll want framed on your wall by Christmas." in e["notes"])
    check("7 notes: the cover reminder", "When you post, tap Edit cover and choose the photo you picked for your grid." in e["notes"])
    check("8 notes: the whole caption, last", e["notes"].endswith(CAPTION) and "Your caption (copy everything below):" in e["notes"])
    check("9 carousel notes: not slide 1 warning", "Your grid photo isn't slide 1: move it to the front before you post." in cal.events[car["event_uid"]]["notes"])

    cal.calls.clear()
    res = go(p, mac)
    check("10 nothing changed: the calendar isn't touched", res["changed"] is False and not cal.calls and not res["did"])

    uid = reel["event_uid"]
    reel["date"] = "2026-11-12"
    go(p, mac)
    check("11 date moved: the same event moves", reel["event_uid"] == uid and cal.events[uid]["when"] == "2026-11-12 09:00" and len(cal.events) == 2)

    WORDS["caption"] = "Edited caption."
    cal.calls.clear()
    go(p, mac)
    check("12 caption edited: the notes follow", cal.calls == [("set", uid)] and cal.events[uid]["notes"].endswith("Edited caption."))

    car["status"] = "yellow"
    cuid = car["event_uid"]
    go(p, mac)
    check("13 not ready any more: its reminder is removed", cuid not in cal.events and "event_uid" not in car and "event_sig" not in car and "event_cal" not in car)

    reel["status"] = "posted"
    cal.calls.clear()
    go(p, mac)
    check("14 posted: its event stays", uid in cal.events and not cal.calls and reel["event_uid"] == uid)

    reel["status"] = "green"
    R.set_reminder(p, reel["id"], None)
    go(p, mac)
    check("15 turned off: removed", uid not in cal.events and "event_uid" not in reel)

    q2 = queue()
    ok = True
    for t in ("09:00", "12:00", "18:00", "20:00", "07:45", "23:59", "00:00"):
        R.set_reminder(q2, q2["pieces"][0]["id"], t)
        ok = ok and q2["pieces"][0]["remind_time"] == t and q2["pieces"][0]["remind_on"] is True and q2["remind"]["time"] == t
    for bad in ("24:00", "9:00", "09:60", "0900", "09:00 ", "9 am", 900, "09:00\n", True):
        try:
            R.set_reminder(q2, q2["pieces"][0]["id"], bad)
            ok = False
        except ValueError:
            pass
    check("16 times are HH:MM (the four on offer and their own are taken; anything else is refused)", ok and q2["pieces"][0]["remind_time"] == "00:00")
    check("17 (our side) the four times in words, as the page says them", [R.time_words(t) for t in ("09:00", "12:00", "18:00", "20:00", "18:30", "00:05")] == ["9 am", "noon", "6 pm", "8 pm", "6:30 pm", "12:05 am"])
    q3 = queue()
    R.set_reminder(q3, q3["pieces"][0]["id"], "09:00")
    check("18 (our side) each post its own time: one post's time never turns another's reminder on", "remind_on" not in q3["pieces"][1] and "remind_time" not in q3["pieces"][1])
    R.set_reminder(q3, q3["pieces"][0]["id"], None)
    check("19 (our side) no reminder is a real answer: off keeps nothing on the calendar side", q3["pieces"][0]["remind_on"] is False and not R.plan(R.snapshot(q3), words=words))
    # her checks 17 to 19 are on the queue page's own source (stage 4 wired the page). Hers looked for type="time"
    # in a line of HTML; ours builds the time box as an element (inp.type='time'), so nothing of theirs is ever HTML.
    # The same three are checked on the real page in a browser by tests/posting_reminders_page_check.py.
    page = (SCRIPTS / "posting_queue.py").read_text(encoding="utf-8")
    check("17 the page offers 9 am, Noon, 6 pm, 8 pm and their own", all(k in page for k in ("['09:00','9 am']", "['12:00','Noon']", "['18:00','6 pm']", "['20:00','8 pm']", "inp.type='time'")))
    check("18 Remind me always opens the times", "r.querySelector('[data-m=\"yes\"]').onclick=()=>pickRemind(el,x,'time')" in page)
    check("19 I'll post it myself closes it", "I'll post it myself" in page)

    # ------------------------------------------------------------ ours
    print("\nOurs")
    WORDS["caption"] = CAPTION

    # the words
    check("title: a carousel, and a single post", R.title(car) == "Post your Hannah carousel today" and R.title({"shoot_name": "Hannah", "kind": "single", "n": 2}) == "Post your Hannah single post 2 today")
    check("notes: no caption yet", R.notes(reel, {}).endswith("Your caption (copy everything below):\n\nNo caption yet. Write it on your words page in the post kit."))
    check("notes: their own caption when that's all there is", R.notes(car, {"own": " Mine. "}).endswith("\n\nMine."))
    check("notes: a reel with no picked hook and no grid photo has only the caption", R.notes({"kind": "reel"}, {"caption": "C", "hooks": ["a"], "picked": []}) == "Your caption (copy everything below):\n\nC")
    check("notes: a pick that points nowhere is no hook, never a crash", "Your hook" not in R.notes(reel, {"caption": "C", "hooks": ["a"], "picked": [7]}) and "Your hook" not in R.notes(reel, {"caption": "C", "picked": [0]}))
    check("notes: the whole words record works too", R.notes(reel, {"pieces": {"reel": WORDS}}) == R.notes(reel, WORDS))
    check("notes: a carousel on slide 1 has no warning (01, 1, Canva's name, a second save)",
          all("isn't slide 1" not in R.notes(dict(car, cover=c), {"caption": "C"}) for c in
              ("Carousel/Hannah carousel - slide 01.jpg", "Carousel/Slide 1.jpg", "Carousel/Slide 01 (Canva).jpg", "Carousel\\Hannah carousel (2) - slide 01.jpg"))
          and "isn't slide 1" in R.notes(dict(car, cover="Carousel/Hannah carousel (2) - slide 03.jpg"), {"caption": "C"}))
    check("signature: the same for the same, different when any part changes",
          R.signature("Home", "2026-11-11", "09:00", "t", "n") == R.signature("Home", "2026-11-11", "09:00", "t", "n")
          and len({R.signature(*a) for a in (("Home", "2026-11-11", "09:00", "t", "n"), ("Work", "2026-11-11", "09:00", "t", "n"), ("Home", "2026-11-12", "09:00", "t", "n"),
                                             ("Home", "2026-11-11", "09:01", "t", "n"), ("Home", "2026-11-11", "09:00", "T", "n"), ("Home", "2026-11-11", "09:00", "t", "N"))}) == 6)

    # the calendar list
    check("calendars: writable ones only, no Birthdays, Holidays, Siri, Scheduled Reminders or hex ids, each once", R.calendars(mac) == ["Home", "Work", "Café ☕"])
    q4 = queue()
    R.set_calendar(q4, "Work", mac)
    ok = q4["remind"]["calendar"] == "Work"
    for bad in ("Birthdays", "Shared by Sam", "Nope", "", None):
        try:
            R.set_calendar(q4, bad, mac)
            ok = False
        except ValueError:
            pass
    check("set_calendar: only one the list gives", ok and q4["remind"]["calendar"] == "Work")
    try:
        R.pair_calendars("Home\nWork\n" + R.MAC_LIST_MARK + "\ntrue\n")
        ok = False
    except R.CalendarProblem:
        ok = True
    check("calendars: names and writable that don't pair up are a problem, never a guess", ok)
    try:
        R.set_reminder(queue(), "no-such", "09:00")
        ok = False
    except ValueError:
        ok = True
    check("set_reminder: a post that isn't in the queue is refused", ok)

    # what the Mac's Calendar is handed
    fresh_home()
    cal = Pretend()
    seen = []
    mac = R.MacCalendar(run=lambda s, a: (seen.append((s, a)), cal.run(s, a))[1])
    p = queue()
    p["remind"] = {"calendar": "Home"}
    reel, car = p["pieces"]
    hard = "She said \"yes\" — it's Zoë's day \U0001f389\n\nLine two; with, commas\\ and a back\\slash\n\ttabbed 'single' `tick` $HOME %s"
    R.set_reminder(p, reel["id"], "09:00")
    go(p, mac, words=lambda x: {"caption": hard, "hooks": ["“Wait for it” \U0001f440"], "picked": [0]})
    s, a = seen[-1]
    check("Mac: the script on stdin is ours and the values are its arguments, in order",
          s is R.MAC_SET and a[:8] == ("Home", "", 2026, 11, 11, 9, 0, 15) and a[8] == "Post your Hannah reel today" and len(a) == 11 and a[10] == "")
    check("Mac: quotes, new lines, an emoji and accents in a caption arrive untouched", a[9].endswith(hard) and "“Wait for it” \U0001f440" in a[9])
    check("Mac: 15 minutes long, an alert at the start, the end set before the start when it moves later",
          "trigger interval:0" in R.MAC_SET and R.MAC_SET.index("if d > (end date of e) then") < R.MAC_SET.index("set end date of e to dEnd\n        set start date of e to d")
          and "display alarm" in R.MAC_SET and R.MINUTES == 15)
    check("Mac: the calendar list is read as two whole lists, never 'whose writable'", "name of every calendar" in R.MAC_LIST and "writable of every calendar" in R.MAC_LIST and "whose" not in R.MAC_LIST)
    check("Mac: the remove script only ever looks for the uid it is handed", "whose uid is uidIn" in R.MAC_REMOVE and R.MAC_REMOVE.count("delete") == 1)

    # the real runner, with the Mac's programs replaced: what it would run, never run
    ran = []
    real_run, real_sleep, real_mac = R.subprocess.run, R.time.sleep, R.this_computer.MAC

    class Done:
        def __init__(self, code=0, out="", err=""):
            self.returncode, self.stdout, self.stderr = code, out, err

    state = {"running": False, "osa": Done(0, "UID-9\n")}

    def fake_run(cmd, **kw):
        ran.append((list(cmd), kw))
        if cmd[0] == "pgrep":
            return Done(0 if state["running"] else 1)
        if cmd[0] == "open":
            state["running"] = True
            return Done()
        if isinstance(state["osa"], BaseException):
            raise state["osa"]
        return state["osa"]

    try:
        R.subprocess.run, R.time.sleep, R.this_computer.MAC = fake_run, lambda s: None, True
        ran.clear()
        got = REAL_OSA("SCRIPT", ("Home", "it's \"x\"\nline"))
        cmds = [c for c, _ in ran]
        osa_kw = ran[-1][1]
        check("Mac runner: Calendar is started hidden first when it isn't running, then asked",
              got == "UID-9" and cmds[0][0] == "pgrep" and cmds[1] == ["open", "-g", "-a", "Calendar"] and cmds[-1] == ["osascript", "-", "Home", "it's \"x\"\nline"])
        check("Mac runner: the script goes in on stdin, as UTF-8, with 120 seconds to answer",
              osa_kw.get("input") == "SCRIPT" and osa_kw.get("timeout") == 120 and osa_kw.get("encoding") == "utf-8")
        ran.clear()
        REAL_OSA("S", ())
        check("Mac runner: a Calendar already open isn't started again", [c[0] for c, _ in ran] == ["pgrep", "osascript"])
        state["osa"] = subprocess.TimeoutExpired("osascript", 120)
        try:
            REAL_OSA("S", ())
            ok = False
        except R.CalendarProblem as ex:
            ok = str(ex) == "Calendar took too long to answer."
        check("Mac runner: no answer in time is said in plain words", ok)
        state["osa"] = Done(1, "", "execution error: Not authorized to send Apple events to Calendar. (-1743)")
        try:
            REAL_OSA("S", ())
            ok = False
        except R.CalendarProblem as ex:
            ok = "hasn't been allowed to use Calendar" in str(ex)
        check("Mac runner: macOS saying no is said in plain words", ok)
        R.this_computer.MAC = False
        ran.clear()
        try:
            REAL_OSA("S", ())
            ok = False
        except R.CalendarProblem:
            ok = not ran
        check("Mac runner: on a PC nothing of the Mac's is run", ok)
    finally:
        R.subprocess.run, R.time.sleep, R.this_computer.MAC = real_run, real_sleep, real_mac

    # twice, deleted, only ours
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    cal.events["THEIRS-1"] = {"cal": "Home", "when": "2026-11-11 09:00", "title": "Dentist", "notes": ""}
    cal.events["THEIRS-2"] = {"cal": "Home", "when": "2026-11-11 09:00", "title": "Post your Hannah reel today", "notes": "their own, same title"}
    p = queue()
    p["remind"] = {"calendar": "Home"}
    reel, car = p["pieces"]
    R.set_reminder(p, reel["id"], "09:00")
    R.set_reminder(p, car["id"], "12:00")
    first = go(p, mac)
    cal.calls.clear()
    second = go(p, mac)
    check("run twice: the second sends nothing", first["changed"] and not second["changed"] and not cal.calls and second["problem"] is None)
    check("sync never changes the queue it is handed", (lambda q, b: (R.sync(q, mac, words=words), q == b)[1])(copy.deepcopy(p), copy.deepcopy(p)))

    del cal.events[reel["event_uid"]]                     # they deleted it in Calendar
    old = reel["event_uid"]
    cal.calls.clear()
    res = go(p, mac)
    check("deleted in Calendar, nothing else changed: left alone until something changes", not cal.calls)
    res = go(p, mac, force=True)
    check("deleted in Calendar: sending all again makes it again, under its new uid", reel["event_uid"] != old and reel["event_uid"] in cal.events and len([c for c in cal.calls if c[0] == "set"]) == 2)
    del cal.events[reel["event_uid"]]
    old = reel["event_uid"]
    reel["date"] = "2026-11-14"
    go(p, mac)
    check("deleted in Calendar, then the date moves: made again on the new day", reel["event_uid"] != old and cal.events[reel["event_uid"]]["when"] == "2026-11-14 09:00")

    cal.calls.clear()
    ours = {reel["event_uid"], car["event_uid"]}
    car["status"] = "red"
    R.set_reminder(p, reel["id"], None)
    go(p, mac)
    removed = [c[1] for c in cal.calls if c[0] == "remove"]
    check("only our own events are ever removed, by the uid we saved (theirs stay, even one with our title)",
          set(removed) == ours and len(removed) == 2 and set(cal.events) == {"THEIRS-1", "THEIRS-2"})
    cal.calls.clear()
    p2 = queue()
    p2["remind"] = {"calendar": "Home"}
    p2["pieces"][0]["status"] = "yellow"
    go(p2, mac)
    check("a post with no event of ours is never looked for in the calendar", not cal.calls)

    # the calendar changes
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    p = queue()
    p["remind"] = {"calendar": "Home"}
    reel = p["pieces"][0]
    R.set_reminder(p, reel["id"], "09:00")
    go(p, mac)
    p["remind"]["calendar"] = "Work"
    go(p, mac)
    check("another calendar chosen: ours leaves the old one and is made on the new one, once",
          len(cal.events) == 1 and cal.events[reel["event_uid"]]["cal"] == "Work" and reel["event_cal"] == "Work")

    # a calendar that fails
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    p = queue()
    p["remind"] = {"calendar": "Home"}
    reel, car = p["pieces"]
    R.set_reminder(p, reel["id"], "09:00")
    R.set_reminder(p, car["id"], "12:00")
    for err, want in ((R.CalendarProblem("Calendar took too long to answer."), "(reminders not updated: Calendar took too long to answer.)"),
                      (subprocess.TimeoutExpired("osascript", 120), "(reminders not updated: Calendar took too long to answer.)"),
                      (RuntimeError("boom"), "(reminders not updated: RuntimeError: boom)"),
                      (OSError(5, "no"), None)):
        cal.fail = err
        cal.calls.clear()
        before = copy.deepcopy(p)
        try:
            res = go(p, mac)
            ok = res["problem"] and res["note"].startswith("(reminders not updated: ") and (want is None or res["note"] == want) and not res["changed"] and p == before and len(cal.calls) == 1
        except BaseException:
            ok = False
        check(f"a calendar that fails ({type(err).__name__}) never stops the caller, says so in words, and is asked once, not once per post", bool(ok))
    cal.fail = None
    res = go(p, mac)
    check("the calendar answers again: both reminders are made, nothing lost", res["problem"] is None and len(cal.events) == 2 and reel.get("event_uid") and car.get("event_uid"))

    class HalfWay:
        name, needs_calendar, opens_files = "mac", True, False

        def __init__(self):
            self.sets = 0

        def set(self, pid, c, uid, day, t, ttl, nts):
            self.sets += 1
            if self.sets > 1:
                raise R.CalendarProblem("Calendar took too long to answer.")
            return "UID-HALF"

        def remove(self, *a):
            raise AssertionError("nothing to remove here")

    fresh_home()
    p = queue()
    p["remind"] = {"calendar": "Home"}
    R.set_reminder(p, p["pieces"][0]["id"], "09:00")
    R.set_reminder(p, p["pieces"][1]["id"], "12:00")
    res = go(p, HalfWay())
    check("a failure part way: what was done before it is still handed back", res["changed"] and res["problem"] and p["pieces"][0].get("event_uid") == "UID-HALF" and "event_uid" not in p["pieces"][1])
    cal = Pretend()
    cal.fail = R.CalendarProblem("Calendar said no.")
    mac = R.MacCalendar(run=cal.run)
    p["pieces"][0]["status"] = "yellow"
    res = go(p, mac)
    check("a removal that fails keeps the uid, so it is tried again", res["problem"] and p["pieces"][0].get("event_uid") == "UID-HALF")
    try:
        R.calendars(R.MacCalendar(run=cal.run))
        ok = False
    except R.CalendarProblem as ex:
        ok = str(ex) == "Calendar said no."
    check("calendars(): a calendar that can't be read is a plain-words problem", ok)

    # the merge
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    p = queue()
    p["remind"] = {"calendar": "Home"}
    reel, car = p["pieces"]
    R.set_reminder(p, reel["id"], "09:00")
    R.set_reminder(p, car["id"], "12:00")
    res = R.sync(p, mac, words=words)
    newer = queue()                                           # what the queue became while the calendar was busy
    newer["remind"] = {"calendar": "Home", "time": "20:00"}
    newer["pieces"][0].update(remind_on=True, remind_time="20:00", date="2026-12-01", slot=2)
    newer["pieces"][1].update(remind_on=True, remind_time="12:00", slot=1, status="green")
    newer["pieces"].append({"id": "kit:new-reel", "shoot_name": "New", "kind": "reel", "status": "red"})
    newer["interval"] = 7
    want = copy.deepcopy(newer)
    changed, strays = R.merge(newer, res["changes"])
    for x in newer["pieces"][:2]:
        for k in R.FIELDS:
            x.pop(k)
    check("merge: only the three event fields are written; everything newer in the queue stays", changed and not strays and newer == want)
    check("merge: the same changes a second time change nothing", R.merge((lambda q: (R.merge(q, res["changes"]), q)[1])(copy.deepcopy(want)), res["changes"]) == (False, []))
    gone = queue()
    gone["pieces"].pop(0)
    changed, strays = R.merge(gone, res["changes"])
    check("merge: a post taken out of the queue meanwhile is a stray, not written anywhere", [s["id"] for s in strays] == [reel["id"]] and "event_uid" in gone["pieces"][0])
    n_before = len(cal.events)
    R.forget(strays, mac)
    check("forget: the stray event is taken away, and only it", len(cal.events) == n_before - 1 and strays[0]["uid"] not in cal.events)
    raced = queue()
    raced["pieces"][0]["event_uid"] = "UID-OTHER"
    raced["pieces"][0]["event_sig"] = "x"
    changed, strays = R.merge(raced, {reel["id"]: res["changes"][reel["id"]]})
    check("merge: a piece whose event changed meanwhile is left exactly as it is", not changed and raced["pieces"][0]["event_uid"] == "UID-OTHER" and raced["pieces"][0]["event_sig"] == "x" and len(strays) == 1)

    # the whole round, as a background thread will run it
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    store = {"q": queue(), "saves": 0, "loads": 0}
    store["q"]["remind"] = {"calendar": "Home"}
    R.set_reminder(store["q"], store["q"]["pieces"][0]["id"], "09:00")
    lock = threading.Lock()
    held = []

    def load():
        store["loads"] += 1
        return copy.deepcopy(store["q"])

    def save(q):
        store["saves"] += 1
        store["q"] = copy.deepcopy(q)

    def during():
        held.append(lock.locked())
        with lock:                                           # a press on the page, while the calendar is busy
            store["q"]["pieces"][1]["status"] = "red"
            store["q"]["interval"] = 2
            store["q"]["pieces"][0]["remind_time"] = "20:00"

    cal.during = during
    out = []
    th = threading.Thread(target=lambda: out.append(R.run(load, save, lock, mac, words=words)))
    th.start()
    th.join(30)
    q = store["q"]
    check("run: the queue's lock is never held while the calendar is asked", held and not any(held) and not th.is_alive(), held)
    check("run: a queue changed during the calendar call is not written over", q["interval"] == 2 and q["pieces"][1]["status"] == "red" and q["pieces"][0]["remind_time"] == "20:00"
          and q["pieces"][0].get("event_uid") in cal.events)
    # (the fix round, Nov 11) the round looks at the queue again after it changed the calendar: a change made
    # meanwhile by ANOTHER program (a command in the chat) has nobody else to start a round for it
    check("run: a time changed during the calendar call is caught up by the same round (it looks again), one event",
          out and out[0]["changed"] and len(cal.events) == 1 and cal.events[q["pieces"][0]["event_uid"]]["when"].endswith("20:00") and len(held) == 2, (held, cal.events))
    cal.during = None
    saves = store["saves"]
    res2 = R.run(load, save, lock, mac, words=words)
    check("run: a round with nothing to do saves nothing and asks the calendar nothing", not res2["changed"] and store["saves"] == saves and len(held) == 2)

    # a post taken out of line by a command while its reminder is still being made: no event may be left
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    store = {"q": queue(), "saves": 0, "loads": 0}
    store["q"]["remind"] = {"calendar": "Home"}
    R.set_reminder(store["q"], store["q"]["pieces"][0]["id"], "09:00")
    seen = []

    def unready_meanwhile():
        if not seen:                                         # "posting_queue.py unready reel", mid-call
            x = store["q"]["pieces"][0]
            x["status"] = "yellow"
            x.pop("date", None)
            seen.append(R.plan(R.snapshot(store["q"]), made=R._made(), words=words))   # what that command's own look finds
        else:
            seen.append("again")

    cal.during = unready_meanwhile
    res = R.run(load, save, lock, mac, words=words)
    x = store["q"]["pieces"][0]
    check("run: a post taken out of line while its reminder was being made (the command itself saw nothing to do) is left with NO event",
          seen[:1] == [[]] and cal.events == {} and "event_uid" not in x and "event_sig" not in x and x["status"] == "yellow" and res["problem"] is None
          and R._made() == {} and R.plan(R.snapshot(store["q"]), made=R._made(), words=words) == [], (seen, cal.events, x))
    check("...and the round says both things it did (set, then removed)", [d.split(":")[0] for d in res["did"]] == ["Reminder set", "Reminder removed"], res["did"])

    # it can't go round for ever: a queue that changes during EVERY call stops after PASSES passes
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    store = {"q": queue(), "saves": 0, "loads": 0}
    store["q"]["remind"] = {"calendar": "Home"}
    R.set_reminder(store["q"], store["q"]["pieces"][0]["id"], "09:00")
    turns = []

    def always():
        turns.append(1)
        store["q"]["pieces"][0]["remind_time"] = "%02d:00" % (10 + len(turns))

    cal.during = always
    res = R.run(load, save, lock, mac, words=words)
    check("run: a queue that changes during every call ends the round after %d passes, one event, no trouble" % R.PASSES,
          len(turns) == R.PASSES and len(cal.events) == 1 and res["problem"] is None and not lock.locked(), (len(turns), cal.events))
    cal.during = None

    # a calendar that says no is asked once, never again by the same round
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    store = {"q": queue(), "saves": 0, "loads": 0}
    store["q"]["remind"] = {"calendar": "Home"}
    for i in (0, 1):
        R.set_reminder(store["q"], store["q"]["pieces"][i]["id"], "09:00")
    cal.fail = R.CalendarProblem("Calendar took too long to answer.")
    res = R.run(load, save, lock, mac, words=words)
    check("run: a calendar that says no is asked once by a round, never again", cal.calls == [("fail",)] and res["problem"] == "Calendar took too long to answer." and store["saves"] == 0, cal.calls)
    cal.fail = None
    fresh_home()                                             # back to one reminded post with its event, for what follows
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    store = {"q": queue(), "saves": 0, "loads": 0}
    store["q"]["remind"] = {"calendar": "Home"}
    R.set_reminder(store["q"], store["q"]["pieces"][0]["id"], "09:00")
    R.run(load, save, lock, mac, words=words)

    # ---- words fit for a page (the fix round): Python's wording and a file's path never reach one
    res = R._stopped({"changes": {}}, IsADirectoryError(21, "Is a directory", "/Users/someone/.studio/reminders/state.json"))
    check("a fault that is not the calendar's is a plain line for the page; the real words are kept apart for the log",
          res["problem"] == R.STOPPED_HERE and "/" not in res["problem"] and "Error" not in res["problem"]
          and "IsADirectoryError" in res["detail"] and "state.json" in res["detail"] and res["note"].startswith("(reminders not updated: IsADirectoryError"), res)
    res = R._stopped({"changes": {}}, R.CalendarProblem("That calendar isn't in Calendar any more."))
    check("...a calendar's own plain words still go through as they are", res["problem"] == "That calendar isn't in Calendar any more." == res["detail"], res)

    class Broken:
        needs_calendar = True

        def calendars(self):
            raise PermissionError(13, "Permission denied", "C:\\Users\\someone\\.studio\\reminders\\x.ics")

    try:
        R.calendars(Broken())
        said = None
    except R.CalendarProblem as e:
        said = str(e)
    check("calendars(): a fault that is not the calendar's never hands a path to the page", said == "Calendar couldn't be asked.", said)

    def bad_load():
        sys.exit("STOP: posting.json could not be read. Nothing changed.")

    res = R.run(bad_load, save, lock, mac, words=words)
    check("run: a queue that can't be read is words, never a crash", res["problem"] and res["note"].startswith("(reminders not updated: ") and not lock.locked())
    gate, inside = threading.Event(), threading.Event()
    cal.during = lambda: (inside.set(), gate.wait(20))
    store["q"]["pieces"][0]["date"] = "2026-11-20"
    th = threading.Thread(target=lambda: out.append(R.run(load, save, lock, mac, words=words)))
    th.start()
    inside.wait(20)
    busy = R.run(load, save, lock, mac, words=words)
    gate.set()
    th.join(30)
    cal.during = None
    check("run: two at once never both talk to the calendar (the second says busy and does nothing)", busy.get("busy") is True and not busy["changed"] and len(cal.events) == 1)

    # made, but the queue never heard (the save failed): no second event
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    p = queue()
    p["remind"] = {"calendar": "Home"}
    R.set_reminder(p, p["pieces"][0]["id"], "09:00")
    R.sync(p, mac, words=words)                                # the changes are dropped on the floor
    res = go(p, mac)
    check("an event made whose uid the queue never got is found again, never made twice", len(cal.events) == 1 and p["pieces"][0].get("event_uid") in cal.events)
    R.set_reminder(p, p["pieces"][0]["id"], None)
    go(p, mac)
    check("and turned off, it is removed and forgotten", not cal.events and not json.loads((STUDIO / "reminders" / "made.json").read_text(encoding="utf-8")))

    # the words come from the kit's own record, and a kit that is away is left alone
    fresh_home()
    kit = TMP / "The Assistant" / "Your Content" / "2026-09-23 Hannah"
    (kit / ".kit").mkdir(parents=True)
    rec = {"pieces": {"reel": {"answers": {}, "caption": "From the record ✨", "hooks": ["h0", "h1"], "picked": [1]}, "carousel": {"answers": {}, "own": "Their own words"}}}
    (kit / ".kit" / "post-words.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    p = queue()
    p["remind"] = {"calendar": "Home"}
    for x in p["pieces"]:
        x["kit"] = str(kit)
        R.set_reminder(p, x["id"], "09:00")
    p["pieces"].append({"id": "kit:2026-09-23-hannah-single-1", "shoot_name": "Hannah", "kind": "single", "n": 1, "status": "green", "date": "2026-11-15", "kit": str(kit)})
    R.set_reminder(p, p["pieces"][2]["id"], "09:00")
    go(p, mac, words=None)
    n0, n1, n2 = (cal.events[x["event_uid"]]["notes"] for x in p["pieces"])
    check("the words are read from the kit's own words record (words.py), in process", n0.endswith("From the record ✨") and "h1" in n0 and n1.endswith("Their own words") and n2.endswith(R.NO_CAPTION))
    one = dict(p["pieces"][1], kind="single")
    check("a carousel saved as one slide is a single post with the carousel's words", R.words_for(one).get("own") == "Their own words" and "isn't slide 1" not in R.notes(one, R.words_for(one)))
    away = TMP / "The Assistant" / "Your Content" / "moved away"
    kit.rename(away)
    cal.calls.clear()
    before = copy.deepcopy(cal.events)
    res = go(p, mac, words=None)
    check("a kit that isn't plugged in: its reminder is left exactly as it is, and said so", not cal.calls and cal.events == before and not res["changed"] and any("left as it is" in d for d in res["did"]))
    away.rename(kit)
    cal.calls.clear()
    go(p, mac, words=None)
    check("the kit back: still nothing to send", not cal.calls)


    # ------------------------------------------------------------ the fix round (five reviewers' findings)
    print("\nThe fix round")

    # 1. a kit that is away: the day and the time still follow, the notes are left, and the truth is said
    fresh_home()
    kit = TMP / "The Assistant" / "Your Content" / "2026-09-23 Hannah"
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    p = queue()
    p["remind"] = {"calendar": "Home"}
    reel, car = p["pieces"]
    for x in p["pieces"]:
        x["kit"] = str(kit)
    R.set_reminder(p, reel["id"], "09:00")
    go(p, mac, words=None)
    uid = reel["event_uid"]
    notes_before = cal.events[uid]["notes"]
    kit.rename(away)                                           # the drive is unplugged
    reel["date"] = "2026-11-20"                                # ... and the post is dragged to another day
    R.set_reminder(p, car["id"], "12:00")                      # ... and another post of that kit gets a reminder
    cal.calls.clear()
    res = go(p, mac, words=None)
    check("kit away, date moved: the same event moves to the new day, its notes untouched",
          cal.calls == [("move", uid)] and reel["event_uid"] == uid and cal.events[uid]["when"] == "2026-11-20 09:00"
          and cal.events[uid]["notes"] == notes_before and notes_before.endswith("From the record ✨") and len(cal.events) == 1)
    check("kit away, date moved: said as it is", any(d.startswith("Reminder moved: Hannah reel, Fri, Nov 20 at 9 am.") and "caption inside is as it was" in d for d in res["did"]))
    check("kit away, a new reminder: not made, and said truthfully (never 'left as it is')",
          "event_uid" not in car and any("Hannah carousel: no reminder made yet" in d and "isn't plugged in" in d for d in res["did"])
          and not any("Hannah carousel" in d and "left as it is" in d for d in res["did"]))
    cal.calls.clear()
    res = go(p, mac, words=None)
    check("kit still away, nothing moved: the calendar isn't touched again", not cal.calls and not res["changed"] and any("Hannah reel" in d and "left as it is" in d for d in res["did"]))
    R.set_reminder(p, reel["id"], "20:00")
    go(p, mac, words=None)
    check("kit away, time changed: the event follows", cal.events[uid]["when"] == "2026-11-20 20:00" and cal.events[uid]["notes"] == notes_before)
    (STUDIO / "reminders" / "made.json").unlink()              # our own note lost: the queue's own field still says where it is
    cal.calls.clear()
    go(p, mac, words=None)
    check("kit away, our note of it lost: still not sent twice", not cal.calls)
    rec2 = json.loads((away / ".kit" / "post-words.json").read_text(encoding="utf-8"))
    rec2["pieces"]["reel"]["caption"] = "Edited while away"
    (away / ".kit" / "post-words.json").write_text(json.dumps(rec2, ensure_ascii=False), encoding="utf-8")
    away.rename(kit)                                           # plugged back in
    cal.calls.clear()
    go(p, mac, words=None)
    check("the kit back: the notes are sent, the same event, and the waiting reminder is made",
          ("set", uid) in cal.calls and cal.events[uid]["notes"].endswith("Edited while away") and cal.events[uid]["when"] == "2026-11-20 20:00"
          and car.get("event_uid") in cal.events and len(cal.events) == 2)
    cal.calls.clear()
    go(p, mac, words=None)
    check("and then nothing more to send", not cal.calls)
    kit.rename(away)
    del cal.events[uid]                                        # deleted by hand, and the kit is away, and the date moves
    reel["date"] = "2026-11-22"
    n_events = len(cal.events)
    res = go(p, mac, words=None)
    check("kit away and our event deleted by hand: nothing is made without its words, the uid is let go, and it says so",
          len(cal.events) == n_events and "event_uid" not in reel and any("Hannah reel: no reminder made yet" in d for d in res["did"]))
    away.rename(kit)
    go(p, mac, words=None)
    check("the kit back: it is made, on the new day, with its words", cal.events[reel["event_uid"]]["when"] == "2026-11-22 20:00" and cal.events[reel["event_uid"]]["notes"].endswith("Edited while away"))
    check("Mac: 'keep' leaves the notes alone and never makes a new event",
          'if keepNotes is not "keep" then set description of e to nts' in R.MAC_SET
          and R.MAC_SET.index('if keepNotes is "keep" then return ""') < R.MAC_SET.index("make new event"))
    # the same on a PC's calendar files
    fresh_home()
    clock2 = [1794000000.0]
    files2 = R.CalendarFiles(opener=lambda f: None, clock=lambda: clock2[0])
    p = queue()
    reel, car = p["pieces"]
    reel["kit"] = str(kit)
    R.set_reminder(p, reel["id"], "09:00")
    go(p, files2, words=None)
    ics = next((STUDIO / "reminders").glob("*.ics"))
    l0 = unfold(ics.read_bytes())[0]
    kit.rename(away)
    reel["date"] = "2026-11-20"
    clock2[0] += 60
    res = go(p, files2, words=None)
    l1 = unfold(ics.read_bytes())[0]
    check("PC, kit away, date moved: the file moves to the new day with the same notes and a higher number",
          prop(l1, "DTSTART") == "20261120T090000" and prop(l1, "DESCRIPTION") == prop(l0, "DESCRIPTION") and "Edited while away" in prop(l1, "DESCRIPTION")
          and int(prop(l1, "SEQUENCE")) > int(prop(l0, "SEQUENCE")) and prop(l1, "UID") == prop(l0, "UID")
          and any(d.startswith("Reminder moved, ready to add to your calendar again: Hannah reel, Fri, Nov 20 at 9 am.") for d in res["did"]))
    away.rename(kit)

    # 2. looking for our event never hides an error
    check("Mac: no bare try around the search for our event (a busy Calendar is an error, never 'not there' and a second event)",
          "try" not in R.MAC_SET and "set found to (every event of c whose uid is uidIn)" in R.MAC_SET
          and R.MAC_SET.index("set found to (every event of c whose uid is uidIn)") < R.MAC_SET.index("make new event"))
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    p = queue()
    p["remind"] = {"calendar": "Home"}
    reel = p["pieces"][0]
    R.set_reminder(p, reel["id"], "09:00")
    go(p, mac)
    uid = reel["event_uid"]
    reel["date"] = "2026-11-19"
    cal.fail = R.CalendarProblem("Calendar took too long to answer.")
    res = go(p, mac)
    cal.fail = None
    go(p, mac)
    check("an update that fails keeps the uid, and the next round moves that same event (never a second one)",
          res["problem"] and reel["event_uid"] == uid and len(cal.events) == 1 and cal.events[uid]["when"] == "2026-11-19 09:00")

    # 3. what a PC cannot promise is written down where the page and the chat can say it from
    gaps = " ".join(R.PC_GAPS)
    check("PC gaps: the alert may not survive, Google is a website, a hand-deleted reminder may not come back",
          "alert may be dropped" in gaps and "Google Calendar is a website" in gaps and "deleted by hand may not come back" in gaps
          and "THE ALERT ITSELF MAY NOT SURVIVE" in R.__doc__ and "Google Calendar is a website" in R.__doc__ and "deleted by hand may not come back" in R.__doc__)

    # 4. on a PC the words say what happened: a file is ready, nothing is on a calendar yet
    fresh_home()
    files3 = R.CalendarFiles(opener=lambda f: None, clock=lambda: 1794000000.0)
    p = queue()
    reel, car = p["pieces"]
    R.set_reminder(p, reel["id"], "09:00")
    res = go(p, files3)
    st_before = R.status_lines(p, files3)
    check("PC: a new reminder is 'ready to add to your calendar', never 'set'",
          res["did"] == ["Reminder ready to add to your calendar: Hannah reel, Wed, Nov 11 at 9 am."])
    check("PC status: waiting to be added until its file is opened",
          "Hannah reel: Wed, Nov 11 at 9 am, waiting to be added to your calendar." in st_before and not any(ln.rstrip().endswith("9 am.") for ln in st_before))
    R.open_waiting(files3)
    check("PC status: after opening, 'opened in your calendar app' (all that can be known)", "Hannah reel: Wed, Nov 11 at 9 am, opened in your calendar app." in R.status_lines(p, files3))
    reel["date"] = "2026-11-12"
    res = go(p, files3)
    check("PC: a change is 'ready to add again', and it is waiting again",
          res["did"] == ["Reminder changed, ready to add to your calendar again: Hannah reel, Thu, Nov 12 at 9 am."]
          and "Hannah reel: Thu, Nov 12 at 9 am, waiting to be added to your calendar." in R.status_lines(p, files3))
    R.open_waiting(files3)
    R.set_reminder(p, reel["id"], None)
    res = go(p, files3)
    check("PC: turned off after it was opened: says a file is ready that takes it off", res["did"] == ["Reminder turned off: Hannah reel. A calendar file is ready that takes it off your calendar."])
    R.set_reminder(p, car["id"], "12:00")
    go(p, files3)
    R.set_reminder(p, car["id"], None)
    res = go(p, files3)
    check("PC: turned off before it was ever opened: just 'turned off'", res["did"] == ["Reminder turned off: Hannah carousel."])
    cal = Pretend()
    q5 = queue()
    q5["remind"] = {"calendar": "Home"}
    R.set_reminder(q5, q5["pieces"][0]["id"], "09:00")
    res = go(q5, R.MacCalendar(run=cal.run))
    check("Mac: the words are as before ('Reminder set', on the Home calendar)", res["did"] == ["Reminder set: Hannah reel, Wed, Nov 11 at 9 am."]
          and "Hannah reel: Wed, Nov 11 at 9 am, on the Home calendar." in R.status_lines(q5, R.MacCalendar(run=cal.run)))

    # 5. one post's trouble never stops another's
    for label, be in (("PC files", lambda: R.CalendarFiles(opener=lambda f: None)), ("Mac", lambda: R.MacCalendar(run=Pretend().run))):
        fresh_home()
        p = queue()
        p["remind"] = {"calendar": "Home"}
        reel, car = p["pieces"]
        reel["date"] = "2026-02-30"
        R.set_reminder(p, reel["id"], "09:00")
        R.set_reminder(p, car["id"], "12:00")
        res = go(p, be())
        check(f"{label}: a post with an impossible date gets no reminder, says so in plain words, and the next post's is still made",
              res["problem"] is None and res["note"] is None and "event_uid" not in reel and car.get("event_uid")
              and any("Hannah reel: its posting date can't be read" in d for d in res["did"]) and not any("ValueError" in d for d in res["did"]))
    check("a real day is a real day", R.real_day("2026-02-28") and R.real_day("2028-02-29") and not any(R.real_day(d) for d in ("2026-02-30", "2026-13-01", "2026-11-31", "20261111", "2026-11-1", "", None, "soon")))
    cal = Pretend()
    try:
        R.MacCalendar(run=cal.run).set("x", "Home", "", "2026-02-30", "09:00", "t", "n")
        ok = False
    except R.CalendarProblem:
        ok = not cal.calls
    check("Mac: an impossible date is never handed to Calendar (AppleScript would roll it into March)", ok)
    fresh_home()
    cal = Pretend()
    mac = R.MacCalendar(run=cal.run)
    p = queue()
    p["remind"] = {"calendar": "Home"}
    reel, car = p["pieces"]
    R.set_reminder(p, reel["id"], "09:00")
    R.set_reminder(p, car["id"], "12:00")
    go(p, mac)
    ruid = reel["event_uid"]
    reel["date"] = "2026-02-30"                                # an event of ours is there, then the date goes bad
    go(p, mac)
    check("an impossible date on a post whose reminder is there: left as it is, not removed", ruid in cal.events and reel["event_uid"] == ruid)
    reel["date"] = "2026-11-11"

    def some_words_break(x):
        if x["kind"] == "reel":
            raise ValueError("a words record that can't be read")
        return {"caption": "Carousel caption, edited."}

    car["date"] = "2026-11-18"
    res = go(p, mac, words=some_words_break)
    check("one post's words that can't be read: the other post's reminder still follows, nothing stops, plain words",
          res["problem"] is None and cal.events[car["event_uid"]]["when"] == "2026-11-18 12:00" and cal.events[car["event_uid"]]["notes"].endswith("edited.")
          and ruid in cal.events and any("Hannah reel: its words couldn't be read just now" in d for d in res["did"]) and not any("ValueError" in d for d in res["did"]))

    # ------------------------------------------------------------ a PC: calendar files
    print("\nA PC: calendar files")
    fresh_home()
    opened = []
    clock = [1794000000.0]
    files = R.CalendarFiles(opener=lambda f: opened.append(f), clock=lambda: clock[0])
    p = queue()
    reel, car = p["pieces"]
    R.set_reminder(p, reel["id"], "09:00")
    p.pop("remind")
    res = go(p, files, words=lambda x: {"caption": hard, "hooks": ["A hook, with; marks\\"], "picked": [0]})
    folder = STUDIO / "reminders"
    made = sorted(folder.glob("*.ics"))
    check("PC: a reminder needs no calendar chosen; one file per reminded post, in the reminders folder", res["changed"] and len(made) == 1 and reel["event_cal"] == R.FILE_CALENDAR and not opened)
    check("PC: the file's name is safe on a PC", made[0].name == R.this_computer.safe_name(made[0].name) and made[0].name.startswith("Post your Hannah reel today ("))
    data = made[0].read_bytes()
    lines, shape = unfold(data)
    check("PC file: CRLF line ends, no line over 75 octets, no letter cut in two, UTF-8", shape and max(len(x) for x in data.split(b"\r\n")) <= 75 and any(x.startswith(b" ") for x in data.split(b"\r\n")))
    check("PC file: one event inside one calendar, with what a calendar app needs",
          lines[0] == "BEGIN:VCALENDAR" and lines[-1] == "END:VCALENDAR" and lines.count("BEGIN:VEVENT") == 1 and lines.count("END:VEVENT") == 1
          and prop(lines, "VERSION") == "2.0" and prop(lines, "PRODID") and prop(lines, "METHOD") == "PUBLISH" and prop(lines, "STATUS") == "CONFIRMED" and len(prop(lines, "DTSTAMP")) == 16)
    check("PC file: on its day at its time, 15 minutes, in local (floating) time", prop(lines, "DTSTART") == "20261111T090000" and prop(lines, "DTEND") == "20261111T091500")
    a0 = lines.index("BEGIN:VALARM")
    check("PC file: an alert at the start", lines[a0:a0 + 5] == ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Post your Hannah reel today", "TRIGGER:PT0M", "END:VALARM"])
    wanted_notes = R.notes(reel, {"caption": hard, "hooks": ["A hook, with; marks\\"], "picked": [0]})
    raw_desc = prop(lines, "DESCRIPTION")
    check("PC file: the title and the notes come back exactly (quotes, new lines, emoji, accents, commas, semicolons, backslashes)",
          ics_text(prop(lines, "SUMMARY")) == "Post your Hannah reel today" and ics_text(raw_desc) == wanted_notes.replace("\t", " ")
          and "\\n" in raw_desc and "\\," in raw_desc and "\\;" in raw_desc and "\\\\" in raw_desc and "\n" not in raw_desc)
    uid1, seq1 = prop(lines, "UID"), int(prop(lines, "SEQUENCE"))
    check("PC file: the post's own steady id", uid1 == reel["event_uid"] == R.steady_uid(reel["id"]) and uid1 != R.steady_uid(car["id"]))

    again = go(p, files, words=lambda x: {"caption": hard, "hooks": ["A hook, with; marks\\"], "picked": [0]})
    check("PC: run twice, the second writes nothing", not again["changed"] and made[0].read_bytes() == data)
    check("PC: the file waits to be opened; opening is a step of its own", [w["file"] for w in again["to_open"]] == [str(made[0])] and not opened)
    got = R.open_waiting(files)
    check("PC: open_waiting hands each waiting file to their calendar app, once", opened == [str(made[0])] and not got["problem"] and not R.open_waiting(files)["opened"] and len(opened) == 1)

    reel["date"] = "2026-11-12"
    R.set_reminder(p, reel["id"], "23:55")
    go(p, files, words=lambda x: {"caption": "Short."})
    lines2, shape2 = unfold(made[0].read_bytes())
    check("PC: a change is the same file, the same id, a higher number", shape2 and sorted(folder.glob("*.ics")) == made and prop(lines2, "UID") == uid1 and int(prop(lines2, "SEQUENCE")) > seq1)
    check("PC: 11:55 pm ends the next day", prop(lines2, "DTSTART") == "20261112T235500" and prop(lines2, "DTEND") == "20261113T001000")
    seq2 = int(prop(lines2, "SEQUENCE"))
    reel["date"] = "2026-11-13"
    go(p, files, words=lambda x: {"caption": "Short."})                     # the clock has not moved
    seq3 = int(prop(unfold(made[0].read_bytes())[0], "SEQUENCE"))
    check("PC: two changes in the same second still go up", seq3 == seq2 + 1 and len(R.open_waiting(files)["opened"]) == 1)
    (folder / "state.json").write_text(json.dumps({uid1: {"id": reel["id"], "file": made[0].name, "date": "2026-11-13", "time": "23:55", "title": "t", "ever_opened": True}}), encoding="utf-8")
    clock[0] += 3600
    reel["date"] = "2026-11-14"
    go(p, files, words=lambda x: {"caption": "Short."})
    check("PC: the number still goes up after its record is lost", int(prop(unfold(made[0].read_bytes())[0], "SEQUENCE")) > seq3)
    R.open_waiting(files)

    reel["status"] = "yellow"
    clock[0] += 5
    res = go(p, files, words=lambda x: {"caption": "Short."})
    lines4, shape4 = unfold(made[0].read_bytes())
    check("PC: not ready any more: the file says the event is cancelled, same id, a higher number",
          shape4 and prop(lines4, "METHOD") == "CANCEL" and prop(lines4, "STATUS") == "CANCELLED" and prop(lines4, "UID") == uid1
          and int(prop(lines4, "SEQUENCE")) > seq3 and "BEGIN:VALARM" not in lines4 and prop(lines4, "DTSTART") == "20261114T235500" and "event_uid" not in reel)
    check("PC: the cancel waits to be opened too", [w["cancel"] for w in res["to_open"]] == [True])
    R.open_waiting(files)
    reel["status"] = "green"
    go(p, files, words=lambda x: {"caption": "Back."})
    lines5 = unfold(made[0].read_bytes())[0]
    check("PC: ready again: the same id comes back as a live event with a higher number", prop(lines5, "METHOD") == "PUBLISH" and prop(lines5, "UID") == uid1 and int(prop(lines5, "SEQUENCE")) > int(prop(lines4, "SEQUENCE")))

    R.set_reminder(p, car["id"], "12:00")
    go(p, files, words=lambda x: {"caption": "C."})
    check("PC: a second post has its own file and id", len(list(folder.glob("*.ics"))) == 2)
    R.set_reminder(p, car["id"], None)
    go(p, files, words=lambda x: {"caption": "C."})
    check("PC: a reminder turned off before its file was ever opened just goes (nothing to cancel)", len(list(folder.glob("*.ics"))) == 1 and "event_uid" not in car)
    files.remove("x", R.FILE_CALENDAR, "not-ours@elsewhere")
    check("PC: an id that isn't ours is never written about", len(list(folder.glob("*.ics"))) == 1 and "not-ours@elsewhere" not in (folder / "state.json").read_text(encoding="utf-8"))
    reel["status"] = "posted"
    before = made[0].read_bytes()
    go(p, files, words=lambda x: {"caption": "Back."})
    check("PC: posted keeps its event", made[0].read_bytes() == before and reel.get("event_uid") == uid1)

    def cant(f):
        raise OSError("no program opens .ics")

    reel["status"] = "green"
    reel["date"] = "2026-11-21"
    go(p, R.CalendarFiles(opener=cant, clock=lambda: clock[0] + 99), words=lambda x: {"caption": "Back."})
    got = R.CalendarFiles(opener=cant).open_waiting()
    check("PC: a file that can't be opened is words, and it stays waiting", got["problem"] and not got["opened"] and len(files.waiting()) == 1)
    check("PC: there is no list of calendars to choose from", R.calendars(files) == [] and files.needs_calendar is False)
    long_line = b"".join(R.ics_fold("DESCRIPTION:" + "é\U0001f389" * 200))
    check("folding: every piece is whole UTF-8 and at most 75 octets", all(len(x) <= 75 and x.decode("utf-8") is not None for x in R.ics_fold("DESCRIPTION:" + "é\U0001f389" * 200))
          and long_line.replace(b" ", b"", 0).decode("utf-8").replace(" ", "") == "DESCRIPTION:" + "é\U0001f389" * 200)
    stamp = datetime(2026, 11, 10, 22, 4, 3, tzinfo=timezone.utc)
    check("the file is the same bytes for the same event (nothing random in it)", R.ics_bytes("u", 3, "2026-11-11", "09:00", "t", "n", stamp=stamp) == R.ics_bytes("u", 3, "2026-11-11", "09:00", "t", "n", stamp=stamp))

    # ------------------------------------------------------------ the command line, as the chat runs it
    print("\nThe command line")
    fresh_home()
    kit = TMP / "The Assistant" / "Your Content" / "2026-09-23 Hannah"
    q = queue()
    q["pieces"][0]["kit"] = str(kit)
    R.set_reminder(q, q["pieces"][0]["id"], "09:00")
    (STUDIO / "posting.json").write_text(json.dumps(q, indent=1, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ, STUDIO_HOME=str(STUDIO), REMINDERS_BACKEND="file", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")

    def cli(*args):
        return subprocess.run([sys.executable, str(SCRIPTS / "reminders.py"), *args], capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=120)

    r = cli("status")
    check("status: every reminder in plain words", r.returncode == 0 and "Hannah reel: Wed, Nov 11 at 9 am, not on the calendar yet." in r.stdout)
    r = cli("sync")
    saved = json.loads((STUDIO / "posting.json").read_text(encoding="utf-8"))
    check("sync: makes the reminder, says so, and the queue gets only its three fields",
          r.returncode == 0 and "Reminder ready to add to your calendar: Hannah reel, Wed, Nov 11 at 9 am." in r.stdout and saved["pieces"][0].get("event_uid") == R.steady_uid(q["pieces"][0]["id"])
          and {k: v for k, v in saved["pieces"][0].items() if k not in R.FIELDS} == q["pieces"][0] and saved["pieces"][1] == q["pieces"][1] and len(list((STUDIO / "reminders").glob("*.ics"))) == 1)
    r = cli("sync")
    check("sync again: nothing sent", r.returncode == 0 and "No reminder has changed since last time." in r.stdout)
    r = cli("calendars")
    check("calendars, on a computer with calendar files: says there is none to choose", r.returncode == 0 and "no calendars to choose from" in r.stdout)
    # ---- "calendar <name>": the choice can be changed (Nov 11; before, a wrong tap or a deleted calendar was a dead end)
    print("\nChoosing the calendar again, from the chat")
    import time as _time
    fresh_home()
    (STUDIO / "reminders").mkdir()
    (STUDIO / "reminders" / "pretend.json").write_text(json.dumps({"calendars": ["Home", "Work", "Family"]}), encoding="utf-8")
    q = queue()
    q["pieces"][0]["kit"] = str(kit)
    R.set_reminder(q, q["pieces"][0]["id"], "09:00")
    (STUDIO / "posting.json").write_text(json.dumps(q, indent=1, ensure_ascii=False), encoding="utf-8")
    env = dict(env, REMINDERS_BACKEND="pretend")

    def posting():
        return json.loads((STUDIO / "posting.json").read_text(encoding="utf-8"))

    def book(want, secs=30):
        """The pretend calendar's events once `want` is true of them (the round runs in a helper of its own)."""
        end = _time.time() + secs
        while True:
            try:
                b = json.loads((STUDIO / "reminders" / "pretend-calendar.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                b = {}
            if want(b) or _time.time() > end:
                return b
            _time.sleep(0.2)

    r = cli("calendar", "Holidays")
    check("calendar <a name that isn't there>: nothing changed, the names listed, exit 1",
          r.returncode == 1 and 'No calendar called "Holidays" was found. Nothing was changed.' in r.stdout and "Home\nWork\nFamily" in r.stdout
          and "remind" in posting() and not (posting().get("remind") or {}).get("calendar"), r.stdout + r.stderr)
    r = cli("calendar", "home")
    b = book(lambda b: len(b) == 1)
    check("calendar <name>, the first time (capital letters aside): chosen, said, and the reminder is made there in the background",
          r.returncode == 0 and "Reminders now go on the Home calendar." in r.stdout and posting()["remind"]["calendar"] == "Home"
          and [e["cal"] for e in b.values()] == ["Home"], r.stdout + r.stderr + repr(b))
    end = _time.time() + 30
    while not posting()["pieces"][0].get("event_uid") and _time.time() < end:
        _time.sleep(0.2)
    first_uid = posting()["pieces"][0].get("event_uid")
    r = cli("calendar", "Work")
    b = book(lambda b: [e["cal"] for e in b.values()] == ["Work"])
    end = _time.time() + 30
    while posting()["pieces"][0].get("event_cal") != "Work" and _time.time() < end:
        _time.sleep(0.2)
    check("calendar <another name>: changed, said with the one before, and our one event is moved (never a second left behind)",
          r.returncode == 0 and "Reminders now go on the Work calendar. They were on Home." in r.stdout and posting()["remind"]["calendar"] == "Work"
          and [e["cal"] for e in b.values()] == ["Work"] and first_uid and posting()["pieces"][0].get("event_cal") == "Work", r.stdout + r.stderr + repr(b))
    r = cli("calendar", "Work")
    check("calendar <the same name>: says so and changes nothing", r.returncode == 0 and "Reminders already go on the Work calendar. Nothing was changed." in r.stdout)
    r = cli("status")
    check("status afterwards names the new calendar", r.returncode == 0 and "Reminders go on the Work calendar." in r.stdout and "on the Work calendar." in r.stdout.split("\n", 1)[1], r.stdout)
    env = dict(env, REMINDERS_BACKEND="file")
    r = cli("calendar", "Work")
    check("calendar <name> on a computer with calendar files: says there is none to choose", r.returncode == 0 and "no calendars to choose from" in r.stdout)

    check("no stray scratch files are left beside the records", not [f.name for f in (STUDIO / "reminders").iterdir() if f.name.endswith(".tmp")] and not list(STUDIO.glob("*.tmp")))

    check("the real Calendar was never reached by any check", not REAL)
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\nAll {count} passed." if not fails else f"\n{fails} of {count} failed.")
sys.exit(1 if fails else 0)
