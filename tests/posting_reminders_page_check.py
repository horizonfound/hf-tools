#!/usr/bin/env python3
"""Posting-day reminders on the posting queue's page (Nicole's v21 section 3, stage 4 of the v21 build): the
reminder drop-down in a post's panel, and the calendar kept in step IN THE BACKGROUND. Checked by request and on
the real page in a HIDDEN Chrome, against a PRETEND calendar: never the Calendar app, never a real calendar.

    python3 tests/posting_reminders_page_check.py [--port 8970] [--work <a folder to keep the run in>] [--no-chrome]

The pretend calendar is reminders.PretendCalendar (REMINDERS_BACKEND=pretend), which only works in a practice
STUDIO_HOME that holds reminders/pretend.json: this test writes that file, and can make the calendar slow or
make it say no while the page server runs. The PC way is REMINDERS_BACKEND=file with a pretend file opener.

What it checks:
  * the test switch is refused anywhere but a test's own folder (the page server will not start);
  * the routes: GET /posting/calendars, GET /posting/reminding, POST /posting {action: "remind" | "remind-calendar"
    | "remind-sync" | "remind-open"} and every refusal; what the page is handed (remind, remind_on, remind_time);
  * nothing is made before a calendar is chosen; each post its own time; off removes; not ready removes; a caption
    edited on the words page follows when the page is opened;
  * the background: a calendar that takes 3 seconds never delays a queue save, a press, or the page's own answers;
    a calendar that says no leaves the queue saved and a plain line for the page; two quick changes end with the
    calendar matching the last one; a slow calendar LIST does not hold up anything else;
  * the command line: with the page server running it is asked to do the calendar work; with none, a helper of its
    own finishes it; either way the command comes back at once and says so; nothing to change says nothing;
  * the PC way end to end: the calendar file written, what the page is told, the open button calling the opener,
    a change waiting to be added again, turning off;
  * the page itself (when there is a Chrome): every state of the drop-down in her words, the toasts, the button's
    pale yellow state, the first-time calendar question asked once only, "I'll post it myself" setting nothing,
    Turn off, the waiting line and the failing line with Try again, and the PC's own lines;
  * her checks 17 to 19 (the four times and their own, Remind me always opens the times, I'll post it myself).
  * the fix round (Nov 11): a command that changes the queue while a round is inside a calendar call (with the
    page server, and with the command's own helper) ends with the calendar matching the queue; a fault on this
    computer reaches the page as one plain line, never a path, with the real words in logs/reminders.log; a press
    in the moment the server starts over after an update starts no round in the old server (the server runs
    from a copy of the scripts for this one); a post with no posting day never says its reminder is set.

The page server, the helper and the hidden Chrome are this test's own and are stopped at the end. Every line says
PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only, a Mac or a PC.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import words_page_check as wpc  # noqa: E402  (its pretend Assistant: kits, the page server, words.py from the chat)
import posting_panel_check as ppc  # noqa: E402  (the panel's own helpers)

KIT, SHORT, HOOKS, SCRIPTS = wpc.KIT, wpc.SHORT, wpc.HOOKS, wpc.SCRIPTS
CAPTION = "MINI SESSIONS are coming to Laguna Beach on December 4th!!!\n\nBring \"quotes\", a new line, and Zoë 🤍."
CALENDARS = ["Home", "Work", "Zoë's <b>family</b>"]
SOURCE = (SCRIPTS / "posting_queue.py").read_text(encoding="utf-8")

# her words, as v21 has them (UPDATE-v21.md section 3, and the page in plugin-changes/posting_queue-since-v20.diff)
SET = "Set a reminder to post"
ASK = "Want a reminder on its posting day? Your phone will tell you when to post, with your caption ready to copy."
FINDING = "Finding your calendars…"
WHICH = "Which calendar does your phone show? Your reminders go there."
CANT = "I can’t reach your Calendar right now."
T_OFF = "No reminder for this one."
# ours
TROUBLE = "I couldn’t update your calendar just now."
SAID_NO = "Calendar took too long to answer."
# ours, a PC only
PC_ASK = "Want a reminder on its posting day? I’ll make a calendar file to add to your calendar, with your caption in it."


def skip(line):
    print("SKIP  " + line, flush=True)


def day(iso):
    d = date.fromisoformat(iso)
    return "%s, %s %d" % (d.strftime("%a"), d.strftime("%b"), d.day)


def cfg(s, **kw):
    f = s.studio / "reminders" / "pretend.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name("pretend.json.test")
    tmp.write_text(json.dumps(dict({"calendars": CALENDARS}, **kw), ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(f))


def book(s):
    try:
        return json.loads((s.studio / "reminders" / "pretend-calendar.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def calls(s, kind=None):
    try:
        rows = [json.loads(x) for x in (s.studio / "reminders" / "pretend-calls.log").read_text(encoding="utf-8").splitlines() if x.strip()]
    except (OSError, ValueError):
        rows = []
    return [r for r in rows if kind is None or r[0] == kind]


def events(s, pid):
    return [e for e in book(s).values() if e.get("id") == pid]


def reminding(s):
    return s.http("GET", "/posting/reminding")[1] or {}


def settle(s, seconds=20):
    """Wait for the background round to finish. True when it did."""
    end = time.time() + seconds
    time.sleep(0.05)
    while time.time() < end:
        if not reminding(s).get("busy"):
            return True
        time.sleep(0.05)
    return False


def until(fn, seconds=20):
    end = time.time() + seconds
    while time.time() < end:
        try:
            if fn():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.05)
    return False


def press(s, body, headers=None):
    t = time.time()
    code, j, _ = s.http("POST", "/posting", body, headers)
    return code, j, time.time() - t


def qpiece(s, pid):
    return next((x for x in s.posting().get("pieces", []) if x.get("id") == pid), {})


def fresh_queue(s, backend, **kw):
    """A page server of this test's own on a brand-new queue: the kit's reel and carousel both ready to post."""
    s.stop()
    for f in (s.studio / "posting.json", s.studio / "posting-url.txt"):
        if f.exists():
            f.unlink()
    shutil.rmtree(str(s.studio / "reminders"), ignore_errors=True)
    cfg(s, **kw)
    s.env["REMINDERS_BACKEND"] = backend
    s.start()
    s.http("POST", "/words-rhythm", {"text": "3 a week"})
    for p in ("reel", "carousel"):
        code = s.http("POST", "/words-queue", {"kit": KIT, "piece": p})[0]
        if code != 200:
            raise RuntimeError("the %s could not be added to the queue (%s)" % (p, code))
    st = ppc.page_state(s)
    g = {x["role"]: x for x in st.get("greens", [])}
    settle(s)
    return g["reel"], g["carousel"]


# ---------------------------------------------------------------- the switch, and the routes

def check_switch(s, port):
    env = dict(s.env, REMINDERS_BACKEND="pretend", STUDIO_HOME=str(s.work / "no-pretend-here"))
    (s.work / "no-pretend-here").mkdir(exist_ok=True)
    r = subprocess.run([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(port + 15)], capture_output=True,
                       text=True, encoding="utf-8", env=env, timeout=30)
    case("the pretend calendar is refused outside a test's own folder: the page server will not start",
         r.returncode != 0 and "STOP" in (r.stdout + r.stderr) and "tests only" in (r.stdout + r.stderr), (r.returncode, (r.stdout + r.stderr)[-200:]))
    import reminders as R
    old = {k: os.environ.get(k) for k in ("STUDIO_HOME", "REMINDERS_BACKEND")}
    try:
        os.environ["STUDIO_HOME"], os.environ["REMINDERS_BACKEND"] = str(s.work / "no-pretend-here"), "pretend"
        try:
            R.default_backend()
            got = "a calendar"
        except R.CalendarProblem as e:
            got = str(e)
        case("...and reminders.default_backend says so in words instead of handing one out", got == R.PRETEND_ONLY, got)
        os.environ["REMINDERS_BACKEND"] = "file"
        case("...and without pretend.json the PC way has its real opener", R.default_backend().opener is R.open_file)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def check_routes(s):
    reel, car = fresh_queue(s, "pretend")
    rid, cid = reel["id"], car["id"]
    st = ppc.page_state(s)
    case("the page is handed: remind (nothing yet), each post's remind_on and remind_time, and how reminders go here",
         st.get("remind") == {} and reel["remind_on"] is False and reel["remind_time"] is None and st["reminding"]["way"] == "calendar"
         and st["reminding"]["problem"] is None, (st.get("remind"), st.get("reminding")))
    case("the two posts have their days (Wed, Nov 11 and Fri, Nov 13)", (reel["date"], car["date"]) == ("2026-11-11", "2026-11-13"), (reel["date"], car["date"]))

    # the calendar list
    code, j, _ = s.http("GET", "/posting/calendars")
    case("GET /posting/calendars: the calendars a reminder could go on", code == 200 and j == {"ok": True, "calendars": CALENDARS}, (code, j))
    case("...refused for a page of another website, and for another host",
         s.http("GET", "/posting/calendars", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
         and s.http("GET", "/posting/calendars", headers={"Host": "evil.example:80"})[0] == 403
         and s.http("GET", "/posting/reminding", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403)

    # refusals: nothing changes
    before = (s.studio / "posting.json").read_bytes()
    bad = [press(s, {"action": "remind", "id": rid, "time": "9am"})[0], press(s, {"action": "remind", "id": rid, "time": "24:00"})[0],
           press(s, {"action": "remind", "id": rid, "time": 900})[0], press(s, {"action": "remind", "id": "no-such", "time": "09:00"})[0],
           press(s, {"action": "remind", "id": ["x"], "time": "09:00"})[0],
           press(s, {"action": "remind-calendar", "calendar": "Birthdays"})[0], press(s, {"action": "remind-calendar", "calendar": None})[0],
           press(s, {"action": "remind-calendar"})[0]]
    case("a time that isn't HH:MM, a post that isn't there, a calendar that isn't on the list: 400 each, nothing changed",
         bad == [400] * 8 and (s.studio / "posting.json").read_bytes() == before, bad)
    cross = [press(s, {"action": a, "id": rid, "time": "09:00", "calendar": "Home"}, {"Origin": "http://evil.example"})[0]
             for a in ("remind", "remind-calendar", "remind-sync", "remind-open")]
    case("every reminder press from another page is refused (403), nothing changed", cross == [403] * 4 and (s.studio / "posting.json").read_bytes() == before, cross)

    # on, before a calendar is chosen
    code, j, _ = press(s, {"action": "remind", "id": rid, "time": "09:00"})
    settle(s)
    g = next(x for x in j["greens"] if x["id"] == rid)
    case("a reminder turned on: saved on the post with its own time, and the time box's next start kept",
         code == 200 and g["remind_on"] is True and g["remind_time"] == "09:00" and j["remind"] == {"time": "09:00"}
         and qpiece(s, rid).get("remind_on") is True, (code, g, j.get("remind")))
    case("nothing is made before a calendar is chosen", book(s) == {} and not calls(s, "set") and not qpiece(s, rid).get("event_uid"))

    # the calendar chosen: the event appears, in the background
    code, j, took = press(s, {"action": "remind-calendar", "calendar": "Home"})
    ok = until(lambda: len(events(s, rid)) == 1) and settle(s)
    e = (events(s, rid) or [{}])[0]
    case("the calendar is chosen (one the list gave), and the page is told", code == 200 and j["remind"] == {"calendar": "Home", "time": "09:00"}, (code, j.get("remind")))
    case("...and the post's event is made: its day, its time, the caption last in its notes, on that calendar",
         ok and e.get("cal") == "Home" and e.get("date") == "2026-11-11" and e.get("time") == "09:00" and e.get("title") == "Post your %s reel today" % SHORT
         and str(e.get("notes")).endswith(CAPTION) and "Your caption (copy everything below):" in str(e.get("notes")), e)
    case("...the post remembers which event is its own", until(lambda: bool(qpiece(s, rid).get("event_uid")) and qpiece(s, rid)["event_uid"] in book(s)), qpiece(s, rid))
    case("a calendar with a tag and an accent in its name can be chosen (and Home again)",
         press(s, {"action": "remind-calendar", "calendar": CALENDARS[2]})[0] == 200 and settle(s) and events(s, rid)[0]["cal"] == CALENDARS[2]
         and press(s, {"action": "remind-calendar", "calendar": "Home"})[0] == 200 and settle(s) and [x["cal"] for x in events(s, rid)] == ["Home"], events(s, rid))

    # each post its own time
    press(s, {"action": "remind", "id": cid, "time": "20:00"})
    ok = until(lambda: len(events(s, cid)) == 1) and settle(s)
    case("each post its own time: the carousel at 8 pm, the reel still at 9 am; only the time box's start moved",
         ok and events(s, cid)[0]["time"] == "20:00" and events(s, cid)[0]["date"] == "2026-11-13" and events(s, rid)[0]["time"] == "09:00"
         and s.posting()["remind"] == {"calendar": "Home", "time": "20:00"} and qpiece(s, rid)["remind_time"] == "09:00",
         (events(s, cid), events(s, rid), s.posting().get("remind")))

    # nothing changed: nothing sent
    n = len(calls(s))
    s.http("GET", "/posting.html")
    settle(s)
    case("the page opened with nothing changed: the calendar isn't touched", len(calls(s)) == n, calls(s)[n:])

    # a caption edited on the words page: the notes follow when the page is opened
    s.words("draft", "reel", {"caption": "Edited caption."})
    time.sleep(0.2)
    case("a caption edited on the words page alone sends nothing yet", len(calls(s)) == n)
    uid = qpiece(s, rid).get("event_uid")
    s.http("GET", "/posting.html")
    ok = until(lambda: str(events(s, rid)[0]["notes"]).endswith("Edited caption.")) and settle(s)
    case("...opening the posting page brings the notes up to date, on the same event", ok and qpiece(s, rid).get("event_uid") == uid and len(events(s, rid)) == 1, events(s, rid))
    s.words("draft", "reel", {"caption": CAPTION})

    # a slow calendar never delays anything
    cfg(s, sleep=3)
    t0 = time.time()
    code, j, took = press(s, {"action": "remind", "id": rid, "time": "10:15"})
    busy = j["reminding"]["busy"] if j else None
    t1 = time.time(); r1 = reminding(s); t_state = time.time() - t1
    t1 = time.time(); c_page = s.http("GET", "/posting.html")[0]; t_page = time.time() - t1
    c2, j2, took2 = press(s, {"action": "order", "ids": [cid, rid]})          # another queue save while the calendar is still answering
    t1 = time.time(); c_panel = s.http("GET", "/posting/panel?id=" + wpc.quote(rid, safe=""))[0]; t_panel = time.time() - t1
    still = reminding(s).get("busy")
    case("a calendar that takes 3 seconds: the press that set the time is answered at once, and says the calendar is being updated",
         code == 200 and took < 1.5 and busy is True and qpiece(s, rid)["remind_time"] == "10:15", (code, round(took, 2), busy))
    case("...the page's own questions are answered at once while it works (how it's going, the page, a post's panel)",
         r1.get("busy") is True and t_state < 1 and c_page == 200 and t_page < 1.5 and c_panel == 200 and t_panel < 1.5, (round(t_state, 2), round(t_page, 2), round(t_panel, 2)))
    case("...and another queue save (a new order) is not held up by it", c2 == 200 and took2 < 1.5 and still is True and time.time() - t0 < 3, (c2, round(took2, 2), still))
    cfg(s)
    ok = settle(s, 40)
    dates = {x["id"]: x["date"] for x in ppc.page_state(s)["greens"]}
    case("...when it has answered, the calendar holds the last of it: the new time, and both posts on their new days",
         ok and events(s, rid)[0]["time"] == "10:15" and events(s, rid)[0]["date"] == dates[rid] and events(s, cid)[0]["date"] == dates[cid]
         and dates[cid] < dates[rid] and len(book(s)) == 2, (dates, book(s)))
    press(s, {"action": "order", "ids": [rid, cid]})
    settle(s)

    # two quick changes
    cfg(s, sleep=1.2)
    press(s, {"action": "remind", "id": rid, "time": "07:00"})
    time.sleep(0.2)
    press(s, {"action": "remind", "id": rid, "time": "07:30"})
    press(s, {"action": "remind", "id": cid, "time": "21:45"})
    ok = settle(s, 40)
    case("two quick changes (and a third on the other post): the calendar ends up matching the last, one event a post",
         ok and [x["time"] for x in events(s, rid)] == ["07:30"] and [x["time"] for x in events(s, cid)] == ["21:45"] and len(book(s)) == 2, book(s))
    press(s, {"action": "remind", "id": rid, "time": "08:00"})
    time.sleep(0.2)
    press(s, {"action": "remind", "id": rid, "time": None})
    ok = settle(s, 40)
    case("on and straight off again: no event is left for that post, and its uid is forgotten",
         ok and events(s, rid) == [] and not qpiece(s, rid).get("event_uid") and qpiece(s, rid).get("remind_on") is False, (events(s, rid), qpiece(s, rid)))
    cfg(s)

    # a calendar that says no
    cfg(s, fail=SAID_NO)
    code, j, took = press(s, {"action": "remind", "id": rid, "time": "09:00"})
    ok = settle(s)
    r = reminding(s)
    case("a calendar that says no: the press is still answered and the queue is saved", code == 200 and qpiece(s, rid)["remind_on"] is True and qpiece(s, rid)["remind_time"] == "09:00", code)
    case("...and the page is handed the trouble as a plain line", ok and r.get("problem") == SAID_NO and r.get("busy") is False and events(s, rid) == [], r)
    case("...a queue save still goes through while the calendar is saying no", press(s, {"action": "unready", "id": cid})[0] == 200 and qpiece(s, cid)["status"] == "yellow")
    cfg(s)
    code, j, took = press(s, {"action": "remind-sync"})
    ok = until(lambda: len(events(s, rid)) == 1) and settle(s)
    case("Try again (remind-sync) changes nothing in the queue, and the calendar catches up: the trouble is gone",
         code == 200 and ok and reminding(s).get("problem") is None and events(s, rid)[0]["time"] == "09:00" and events(s, cid) == [], (reminding(s), book(s)))
    case("...the post that went back to not ready lost its event (only ours, by its uid)", not qpiece(s, cid).get("event_uid") and qpiece(s, cid).get("remind_on") is True)
    press(s, {"action": "ready", "id": cid})
    case("ready again: its reminder comes back by itself, on its new day",
         until(lambda: len(events(s, cid)) == 1 and events(s, cid)[0]["date"] == qpiece(s, cid).get("date")) and settle(s), events(s, cid))

    # a slow, then failing, calendar LIST
    cfg(s, list_sleep=3)
    got = {}
    th = threading.Thread(target=lambda: got.update(r=s.http("GET", "/posting/calendars"), t=time.time()))
    t0 = time.time(); th.start(); time.sleep(0.3)
    t1 = time.time(); a = reminding(s); c_page = s.http("GET", "/posting.html")[0]; c_press = press(s, {"action": "remind", "id": rid, "time": "09:30"})[0]; quick = time.time() - t1
    th.join(20)
    case("a calendar list that takes 3 seconds holds nothing else up (the page, a press, how it's going)",
         "r" in got and got["r"][1] == {"ok": True, "calendars": CALENDARS} and got["t"] - t0 >= 2.5 and quick < 1.5 and c_page == 200 and c_press == 200 and "way" in a,
         (round(quick, 2), round(got.get("t", 0) - t0, 2)))
    cfg(s, list_fail="Calendar isn't allowed to be used yet. Say yes when your Mac asks.")
    time.sleep(3.2)
    code, j, _ = s.http("GET", "/posting/calendars")
    case("a calendar list that can't be read: the reason in plain words, for the page to show", code == 200 and j == {"ok": False, "problem": "Calendar isn't allowed to be used yet. Say yes when your Mac asks."}, (code, j))
    cfg(s, calendars=[])
    time.sleep(3.2)
    code, j, _ = s.http("GET", "/posting/calendars")
    case("no calendar a reminder could go on: said plainly, never an empty question", code == 200 and j.get("ok") is False and "No calendar" in j.get("problem", ""), j)
    cfg(s)
    settle(s)
    return rid, cid


# ---------------------------------------------------------------- the command line

def check_commands(s, rid, cid):
    # with the page server running: it is asked to do the calendar work
    press(s, {"action": "remind", "id": rid, "time": "09:00"})
    settle(s)
    have = len(events(s, rid)) == 1 and len(events(s, cid)) == 1
    cfg(s, sleep=3)
    t = time.time()
    code, out = s.cmd("posting_queue.py", "unready", "carousel")
    took = time.time() - t
    case("a command that takes a reminded post out of line (page server running) comes back at once and says the calendar is being updated",
         have and code == 0 and took < 2.9 and "back to in progress" in out and "being brought into step in the background" in out, (round(took, 2), out[-240:]))
    cfg(s)
    case("...and the page server takes its event away", until(lambda: events(s, cid) == []) and settle(s) and len(events(s, rid)) == 1, book(s))
    n = len(calls(s))
    code, out = s.cmd("posting_queue.py", "tank")
    code2, out2 = s.cmd("posting_queue.py", "interval", "3 a week")
    settle(s)
    case("a command that changes nothing a reminder cares about says nothing about reminders and touches nothing",
         code == 0 and code2 == 0 and "reminder" not in (out + out2).lower() and len(calls(s)) == n, out2[-200:])

    # with no page server: a helper of the command's own, started and left to finish
    s.stop()
    try:
        (s.studio / "posting-url.txt").unlink()
    except OSError:
        pass
    cfg(s, sleep=1.5)
    t = time.time()
    code, out = s.cmd("posting_queue.py", "ready", "carousel")
    took = time.time() - t
    case("with no page server running, the command still comes back at once and says the calendar is being updated",
         code == 0 and took < 1.4 + 1.5 and "ready to post" in out and "being brought into step in the background" in out and events(s, cid) == [], (round(took, 2), out[-260:]))
    ok = until(lambda: len(events(s, cid)) == 1 and bool(qpiece(s, cid).get("event_uid")), 30)
    case("...and its helper finishes the calendar by itself: the event made, the post remembering it", ok and qpiece(s, cid).get("event_uid") in book(s), (book(s), qpiece(s, cid)))
    cfg(s, fail=SAID_NO)
    code, out = s.cmd("posting_queue.py", "move", "carousel", "--to", "1")
    last = s.studio / "reminders" / "last.json"
    ok = until(lambda: json.loads(last.read_text(encoding="utf-8")).get("problem") == SAID_NO, 30)
    case("...a calendar that says no to the helper: the command was not stopped, and the trouble is kept for the page", code == 0 and ok, out[-200:])
    s.env["REMINDERS_BACKEND"] = "pretend"
    s.start()                              # (the server tries once as it comes up; the calendar still says no)
    told = settle(s) and reminding(s).get("problem") == SAID_NO
    cfg(s)
    case("...the page, opened later, is handed that trouble, and catches the calendar up by itself",
         told and s.http("GET", "/posting.html")[0] == 200
         and until(lambda: reminding(s).get("problem") is None and events(s, cid)[0]["date"] == qpiece(s, cid)["date"]) and settle(s), (reminding(s), events(s, cid)))
    code, out = s.cmd("reminders.py", "status")
    case("reminders.py status says where each one stands", code == 0 and "Home calendar" in out, out[-300:])


# ---------------------------------------------------------------- the PC way

def ics_files(s):
    return sorted((s.studio / "reminders").glob("*.ics"))


def check_pc(s):
    reel, car = fresh_queue(s, "file", opener="log")
    rid, cid = reel["id"], car["id"]
    st = ppc.page_state(s)
    case("a PC: the page is told a reminder is a calendar file here, with nothing waiting yet",
         st["reminding"]["way"] == "file" and st["reminding"].get("waiting") == {} and st["reminding"].get("handed") == [], st["reminding"])
    code, j, took = press(s, {"action": "remind", "id": rid, "time": "09:00"})
    ok = until(lambda: len(ics_files(s)) == 1) and settle(s)
    text = ics_files(s)[0].read_text(encoding="utf-8") if ics_files(s) else ""
    case("turning a reminder on needs no calendar chosen: the post's calendar file is written, with its alert and the caption",
         code == 200 and ok and "BEGIN:VEVENT" in text and "BEGIN:VALARM" in text and "DTSTART" in text and "20261111T090000" in text
         and "MINI SESSIONS are coming" in text.replace("\r\n ", "").replace("\n ", ""), text[:300])
    r = reminding(s)
    case("...the page is told that file is waiting to be added (new), and that nothing was opened", r.get("waiting") == {rid: "new"} and r.get("handed") == [] and not calls(s, "open"), r)
    code, j, _ = press(s, {"action": "remind-open"})
    r = reminding(s)
    case("the open button: the file is handed to their calendar app (the opener is called with it), and the page is told it was opened",
         code == 200 and j.get("opened") == 1 and j.get("open_problem") is None and [c[1] for c in calls(s, "open")] == [ics_files(s)[0].name]
         and r.get("waiting") == {} and r.get("handed") == [rid], (j.get("opened"), calls(s, "open"), r))
    press(s, {"action": "remind", "id": rid, "time": "12:00"})
    ok = until(lambda: reminding(s).get("waiting") == {rid: "again"}) and settle(s)
    case("a change (a new time) is a file to add AGAIN, and it is no longer counted as on their calendar", ok and reminding(s).get("handed") == [] and "T120000" in ics_files(s)[0].read_text(encoding="utf-8"), reminding(s))
    press(s, {"action": "remind", "id": rid, "time": None})
    ok = until(lambda: reminding(s).get("waiting") == {rid: "off"}) and settle(s)
    text = ics_files(s)[0].read_text(encoding="utf-8") if ics_files(s) else ""
    case("turned off after it was opened once: a file that cancels it is waiting (the page says what a PC can't promise)", ok and "METHOD:CANCEL" in text and "STATUS:CANCELLED" in text, reminding(s))
    code, j, _ = press(s, {"action": "remind-open"})
    case("...opening that one too leaves nothing waiting", j.get("opened") == 1 and reminding(s).get("waiting") == {} and len(calls(s, "open")) == 2, reminding(s))
    press(s, {"action": "remind", "id": cid, "time": "18:00"})
    until(lambda: reminding(s).get("waiting") == {cid: "new"}) and settle(s)
    press(s, {"action": "remind", "id": cid, "time": None})
    ok = until(lambda: reminding(s).get("waiting") == {}) and settle(s)
    case("turned off before it was ever opened: the file just goes, nothing to take off any calendar", ok and len(ics_files(s)) == 1, [f.name for f in ics_files(s)])
    cfg(s, opener="fail")
    press(s, {"action": "remind", "id": cid, "time": "18:00"})
    until(lambda: reminding(s).get("waiting") == {cid: "new"}) and settle(s)
    code, j, _ = press(s, {"action": "remind-open"})
    case("a file that can't be opened: said in words, and it stays waiting", code == 200 and j.get("opened") == 0 and bool(j.get("open_problem")) and reminding(s).get("waiting") == {cid: "new"}, j.get("open_problem"))
    cfg(s, opener="log")
    code, out = s.cmd("posting_queue.py", "unready", "carousel")
    case("a command on a PC does the file work itself, at once, and says what happened",
         code == 0 and "Reminder turned off" in out and reminding(s).get("waiting") == {}, out[-300:])
    code, out = s.cmd("posting_queue.py", "ready", "carousel")
    case("...and says a file is waiting to be opened, and that nothing is on the calendar until then",
         code == 0 and "Reminder ready to add to your calendar" in out and "waiting to be opened in your calendar app" in out, out[-400:])
    case("the calendar list is never offered on a PC", s.http("GET", "/posting/calendars")[1].get("ok") is False and s.posting().get("remind", {}).get("calendar") is None)


# ---------------------------------------------------------------- the fix round (Nov 11)

STOPPED_HERE = "Something on this computer got in the way. Tell Claude and it'll sort it out."
WAITING = "🔔 Your reminder at 9 am is waiting until this post has a posting day."


def calendar_chosen(s):
    s.http("GET", "/posting/calendars")
    code = press(s, {"action": "remind-calendar", "calendar": "Home"})[0]
    settle(s)
    return code == 200


def still(fn, seconds=2.0):
    """True when fn() holds now and keeps holding for `seconds`."""
    end = time.time() + seconds
    while time.time() < end:
        if not fn():
            return False
        time.sleep(0.1)
    return True


def check_another_program(s):
    """A command in the chat changes the queue WHILE a round is inside a calendar call. The command's own look
    finds nothing to do (the event is not made yet), so the round has to look again itself."""
    reel, car = fresh_queue(s, "pretend")
    rid, cid = reel["id"], car["id"]
    ok = calendar_chosen(s)
    cfg(s, sleep=3)
    code, _, took = press(s, {"action": "remind", "id": cid, "time": "09:00"})
    time.sleep(1.0)
    c2, out = s.cmd("posting_queue.py", "unready", "carousel")
    inside = [c for c in calls(s, "set") if c[1] == cid] != [] and events(s, cid) == []
    cfg(s, sleep=0.2)
    gone = until(lambda: len(calls(s, "remove")) >= 1 and events(s, cid) == [] and not qpiece(s, cid).get("event_uid"), 25)
    case("page server running: a post taken out of line by a command while its reminder was being made (the command said nothing) ends with NO event",
         ok and code == 200 and c2 == 0 and inside and "brought into step" not in out and gone
         and still(lambda: events(s, cid) == [] and not qpiece(s, cid).get("event_uid")) and qpiece(s, cid)["status"] == "yellow",
         (inside, out[-160:], book(s), qpiece(s, cid), calls(s)))
    code, out = s.cmd("reminders.py", "status")
    case("...and reminders.py status says the true thing (waiting, nothing on the calendar)", code == 0 and "waiting until" in out and events(s, cid) == [], out[-300:])

    # the same with no page server: the first command's helper is making the event when the second command runs
    settle(s)
    s.stop()
    try:
        (s.studio / "posting-url.txt").unlink()
    except OSError:
        pass
    n_set = len([c for c in calls(s, "set") if c[1] == cid])
    cfg(s, sleep=3)
    c1, out1 = s.cmd("posting_queue.py", "ready", "carousel")
    started = until(lambda: len([c for c in calls(s, "set") if c[1] == cid]) == n_set + 1, 10)
    time.sleep(0.5)
    c2, out2 = s.cmd("posting_queue.py", "unready", "carousel")
    inside = started and events(s, cid) == []
    cfg(s, sleep=0.2)
    gone = until(lambda: len([c for c in calls(s, "remove") if c[1] == cid]) >= 2 and events(s, cid) == [] and not qpiece(s, cid).get("event_uid"), 25)
    case("no page server: the helper that was making the event takes it away again by itself (ready, then not ready a moment later)",
         c1 == 0 and c2 == 0 and inside and gone and still(lambda: events(s, cid) == [] and not qpiece(s, cid).get("event_uid")),
         (inside, out2[-160:], book(s), qpiece(s, cid), calls(s)[-4:]))
    s.env["REMINDERS_BACKEND"] = "pretend"
    s.start()
    settle(s)


def check_plain_words(s):
    """Something on this computer stops the calendar file being written: the page gets a plain line, never
    Python's wording or a file's path; the real words are in the log."""
    reel, car = fresh_queue(s, "file", opener="log")
    rid = reel["id"]
    state = s.studio / "reminders" / "state.json"
    if state.exists():
        state.unlink()
    state.mkdir(parents=True)                     # the file backend can't save its own notes now
    code = press(s, {"action": "remind", "id": rid, "time": "09:00"})[0]
    until(lambda: bool(reminding(s).get("problem"))) and settle(s)
    r = reminding(s)
    page = s.http("GET", "/posting.html")[2].decode("utf-8")
    settle(s)
    last = (s.studio / "reminders" / "last.json").read_text(encoding="utf-8")
    home = str(s.studio)
    case("a fault on this computer: the page is handed one plain line, with no file path and none of Python's words",
         code == 200 and r.get("problem") == STOPPED_HERE and home not in json.dumps(r) and "state.json" not in page and "Error" not in json.dumps(r)
         and "state.json" not in last and home not in last, (r, last[:300]))
    try:
        log = (s.studio / "logs" / "reminders.log").read_text(encoding="utf-8")
    except OSError:
        log = ""
    case("...the real words are kept in logs/reminders.log for Claude", "state.json" in log and "Error" in log, log[-300:])
    state.rmdir()
    press(s, {"action": "remind-sync"})
    case("...put right and tried again: the trouble is gone and the calendar file is written",
         until(lambda: reminding(s).get("problem") is None and len(ics_files(s)) == 1) and settle(s), (reminding(s), [f.name for f in ics_files(s)]))


def check_starting_over(s):
    """A press that lands in the moment between the "one moment" page and the new server: no round may start in
    the old one (it would be cut off mid-call, leaving an event nobody recorded, and the next round would make a
    second). The server here runs from a COPY of the scripts, and "newer code" is the real folder."""
    if os.name != "posix":
        skip("a press while the server starts over: a Mac's way of starting over only (a PC's is in pc_servers.py)")
        return
    reel, car = fresh_queue(s, "pretend")
    rid, cid = reel["id"], car["id"]
    ok = calendar_chosen(s)
    s.stop()
    copy_of = s.work / "code"
    shutil.rmtree(str(copy_of), ignore_errors=True)
    shutil.copytree(str(SCRIPTS.parents[2]), str(copy_of), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    script = copy_of / SCRIPTS.relative_to(SCRIPTS.parents[2]) / "posting_queue.py"
    pointer = s.studio / "code-home.txt"
    if pointer.exists():
        pointer.unlink()
    said = []
    s.proc = subprocess.Popen([sys.executable, str(script), "serve", "--port", str(s.want)], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, encoding="utf-8", env=s.env)
    first = s.proc.stdout.readline()
    s.port = int(first.rsplit(":", 1)[1].split("/")[0])
    threading.Thread(target=lambda: [said.append(x) for x in s.proc.stdout], daemon=True).start()
    until(lambda: s.http("GET", "/posting/reminding")[0] == 200, 10)
    settle(s)
    n_set = len(calls(s, "set"))
    cfg(s, sleep=1.5)
    pointer.write_text(str(SCRIPTS) + "\n", encoding="utf-8")     # "the Assistant lives over there now": newer code
    code, _, raw = s.http("GET", "/posting.html")
    waiting_page = code == 200 and b"id='data'" not in raw
    c2 = press(s, {"action": "remind", "id": cid, "time": "09:00"})[0]      # inside the 0.4 s before it starts over
    back = until(lambda: any("starting over" in x for x in said) and s.http("GET", "/posting/reminding")[0] == 200, 20)
    made = until(lambda: len(events(s, cid)) == 1 and qpiece(s, cid).get("event_uid") in book(s), 20) and settle(s)
    sets = [c for c in calls(s, "set")[n_set:] if c[1] == cid]
    case("a press as the server starts over: answered, and NO round is started in the server that is about to go (one call to the calendar, by the new one)",
         ok and waiting_page and c2 == 200 and back and made and len(sets) == 1 and sets[0][3] == "", (waiting_page, c2, back, sets, said[-3:]))
    case("...the new server brings that reminder into step as it comes up, with no page opened: one event, remembered",
         made and len(events(s, cid)) == 1 and qpiece(s, cid).get("remind_on") is True, (book(s), qpiece(s, cid)))
    s.stop()
    cfg(s)
    s.start()
    settle(s)


def no_day(s):
    """Both posts ready with NO posting day (no rhythm set); the reel's reminder is on. The page server is
    stopped while the queue's file is changed, as a command would have left it."""
    reel, car = fresh_queue(s, "pretend")
    calendar_chosen(s)
    s.stop()
    f = s.studio / "posting.json"
    p = json.loads(f.read_text(encoding="utf-8"))
    p["interval"] = None
    for x in p["pieces"]:
        x.pop("date", None)
        if x["id"] == reel["id"]:
            x["remind_on"], x["remind_time"] = True, "09:00"
    f.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding="utf-8")
    s.start()
    settle(s)
    return reel["id"], car["id"]


def check_no_day(s):
    rid, cid = no_day(s)
    st = ppc.page_state(s)
    g = {x["id"]: x for x in st.get("greens", [])}
    case("a post that is ready but has no posting day yet: the page is handed no date, and nothing is on the calendar",
         not g[rid].get("date") and not g[cid].get("date") and g[rid].get("remind_on") is True and book(s) == {} and not calls(s, "set"), (g, book(s)))


def check_page_no_day(c, s):
    rid, cid = no_day(s)
    c.open(s.url("/posting.html"))
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    ppc.open_panel(c, cid)
    time.sleep(0.4)
    row = c.js("Array.from(document.querySelectorAll('#pick .pw > *')).filter(function(e){ return e.textContent; }).map(function(e){ return e.textContent; })")
    case("no posting day yet, no reminder: there is no reminder button (nothing can say 'Reminder set:  at 9 am.')",
         c.js(BTN) is None and SET not in row and "Copy caption" in row, row)
    ppc.open_panel(c, rid)
    case("no posting day yet, its reminder on: the button gives the time with no hole where the day goes",
         btn_is(c, "🔔 Reminder: 9 am") is True, c.js(BTN))
    c.click("#pick [data-r]")
    case("...and the drop-down says it is waiting for a posting day, never that they will be reminded; only Turn off",
         line_is(c, WAITING) is True and c.js(BUTTONS) == ["Turn off", "×"] and book(s) == {}, (c.js(LINE), c.js(BUTTONS), book(s)))
    c.click("#pick .pr [data-m=off]")
    toast = ppc.wait_toast(c, T_OFF)
    case("...Turn off: her 'No reminder for this one.', and the button goes", toast is True and btn_is(c, None) is True and qpiece(s, rid).get("remind_on") is False, (toast, c.js(BTN)))
    seen = c.js("document.body.innerText")
    case("nowhere on the page: 'Reminder: ,' or 'on  at'", "Reminder: ," not in seen and "on  at" not in seen and "set:  at" not in seen)


# ---------------------------------------------------------------- the page, in a hidden Chrome

BTN = "(function(){ var b = document.querySelector('#pick [data-r]'); return b ? b.textContent : null; })()"
LINE = "(function(){ var l = document.querySelector('#pick .pr .prl'); return l ? l.querySelector('.prh').textContent : null; })()"
BUTTONS = "Array.from(document.querySelectorAll('#pick .pr .prl button')).map(function(b){ return b.textContent; })"
NOTE = "(function(){ var n = document.querySelector('#pick .pn'); return n ? n.textContent : null; })()"


def line_is(c, text, seconds=10):
    try:
        c.wait_for("%s === %s" % (LINE, json.dumps(text)), seconds)
        return True
    except Exception:  # noqa: BLE001
        return c.js(LINE)


def closed(c, seconds=5):
    try:
        c.wait_for("%s === null" % LINE, seconds)
        return True
    except Exception:  # noqa: BLE001
        return c.js(LINE)


def btn_is(c, text, seconds=10):
    try:
        c.wait_for("%s === %s" % (BTN, json.dumps(text)), seconds)
        return True
    except Exception:  # noqa: BLE001
        return c.js(BTN)


def check_page(c, s):
    reel, car = fresh_queue(s, "pretend", list_sleep=1.2)
    rid, cid = reel["id"], car["id"]
    d1, d2 = day(reel["date"]), day(car["date"])
    c.open(s.url("/posting.html"))
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    c.js(ppc.STUB_COPY)
    ppc.open_panel(c, rid)
    c.wait_for("%s !== null" % BTN, 10)

    # the button, and the drop-down closed
    row = c.js("Array.from(document.querySelectorAll('#pick .pw > *')).filter(function(e){ return e.textContent; }).map(function(e){ return e.textContent; })")
    case("the button row: Copy caption, Copy my hook, Set a reminder to post, Open my words →", row == ["Copy caption", "Copy my hook", SET, "Open my words →"], row)
    case("the drop-down is closed until they press the button, and takes no room", c.js(LINE) is None and c.js("document.querySelector('#pick .pr').getBoundingClientRect().height") == 0
         and c.js("Array.from(%s.children).map(function(e){ return e.className; }).join(' ')" % ppc.PANEL) == "ph pw pr pn strip warn")
    c.click("#pick [data-r]")
    case("pressed: 'Want a reminder on its posting day? ...' [Remind me] [I'll post it myself] and a small ×, hers",
         line_is(c, ASK) is True and c.js(BUTTONS) == ["Remind me", "I'll post it myself", "×"], (c.js(LINE), c.js(BUTTONS)))
    look = c.js("(function(){ var l = document.querySelector('#pick .pr .prl'), x = l.querySelector('.prx'), r = l.getBoundingClientRect(), s = document.querySelector('#pick .strip').getBoundingClientRect(), w = document.querySelector('#pick .pw').getBoundingClientRect();"
                " return {bg: getComputedStyle(l).backgroundColor, lines: Array.from(l.children).map(function(e){ return Math.round(e.getBoundingClientRect().top + e.getBoundingClientRect().height / 2); }),"
                " xright: Math.round(r.right - x.getBoundingClientRect().right), below: r.top >= w.bottom - 1, above: r.bottom <= s.top + 1, h: r.height,"
                " dark: getComputedStyle(l.querySelector('[data-m=yes]')).backgroundColor, title: x.title}; })()")
    case("...one pale yellow strip, text then its buttons together (wrapping under the text when the panel is narrow, as hers), the × at the right end, between the button row and the photos",
         look["bg"] == "rgb(251, 242, 214)" and max(look["lines"][1:]) - min(look["lines"][1:]) <= 3 and 0 <= look["xright"] <= 16 and look["below"] and look["above"] and look["h"] < 90
         and look["dark"] == "rgb(31, 36, 48)", look)
    case("her check 18: there is no time on the Remind me button", c.js("document.querySelector('#pick .pr [data-m=yes]').textContent") == "Remind me")
    c.click("#pick [data-r]")
    case("pressing the button again closes it (a toggle)", closed(c) is True)
    c.click("#pick [data-r]"); line_is(c, ASK)
    c.click("#pick .pr .prx")
    case("the × closes it", closed(c) is True)
    c.click("#pick [data-r]"); line_is(c, ASK)
    c.click("#pick .pr [data-m=no]")
    time.sleep(0.4)
    case("her check 19: I'll post it myself closes it, and nothing is set (no reminder, no calendar asked, nothing sent)",
         closed(c) is True and not qpiece(s, rid).get("remind_on") and s.posting().get("remind") in (None, {}) and not calls(s) and c.js(BTN) == SET, (qpiece(s, rid), calls(s)))

    # the very first time: which calendar, then the times
    c.click("#pick [data-r]"); line_is(c, ASK)
    c.click("#pick .pr [data-m=yes]")
    case("Remind me, the very first time: a waiting line while the calendars are found", line_is(c, FINDING, 3) is True and c.js(BUTTONS) == ["×"], (c.js(LINE), c.js(BUTTONS)))
    case("...then 'Which calendar does your phone show? Your reminders go there.' with a button for each, the name as text",
         line_is(c, WHICH) is True and c.js(BUTTONS) == CALENDARS + ["×"] and c.js("document.querySelectorAll('#pick .pr .prl button *').length") == 0
         and c.js("document.querySelector('#pick .pr .prh b').textContent") == "Which calendar does your phone show?", (c.js(LINE), c.js(BUTTONS)))
    c.click("#pick .pr [data-cal=Home]")
    case("a calendar chosen: straight on to 'What time?' [9 am] [Noon] [6 pm] [8 pm] or a time box and [Set] (her check 17)",
         line_is(c, "What time?") is True and c.js(BUTTONS) == ["9 am", "Noon", "6 pm", "8 pm", "Set", "×"]
         and c.js("Array.from(document.querySelectorAll('#pick .pr [data-t]')).map(function(b){ return b.dataset.t; })") == ["09:00", "12:00", "18:00", "20:00"]
         and c.js("document.querySelector('#pick .pr .prt').textContent.trim().indexOf('or') === 0") and c.count("#pick .pr input[type=time]") == 1, (c.js(LINE), c.js(BUTTONS)))
    case("the time box starts at 6 pm when neither the post nor anyone has a time yet", c.js("document.querySelector('#pick .pr input[type=time]').value") == "18:00")
    case("nothing is saved by getting this far except the calendar", s.posting().get("remind") == {"calendar": "Home"} and not qpiece(s, rid).get("remind_on") and not calls(s, "set"))
    c.click("#pick .pr [data-t=\"09:00\"]")
    toast = ppc.wait_toast(c, "Reminder set: %s at 9 am." % d1)
    case("9 am: saved, the drop-down closes, and the toast says 'Reminder set: %s at 9 am.'" % d1, toast is True and closed(c) is True and qpiece(s, rid).get("remind_time") == "09:00", toast)
    case("the button turns pale yellow and reads '🔔 Reminder: %s, 9 am'" % d1, btn_is(c, "🔔 Reminder: %s, 9 am" % d1) is True
         and c.js("getComputedStyle(document.querySelector('#pick [data-r]')).backgroundColor") == "rgb(251, 242, 214)", c.js(BTN))
    case("...and the event is on the pretend calendar, made in the background", until(lambda: len(events(s, rid)) == 1 and events(s, rid)[0]["time"] == "09:00" and events(s, rid)[0]["cal"] == "Home"), book(s))
    case("no line about trouble when there was none", c.js(NOTE) == "")

    # reminder on
    c.click("#pick [data-r]")
    on = "🔔 I'll remind you on %s at 9 am on your Home calendar, with your caption in it." % d1
    case("pressed again, reminder on: \"%s\" [Change time] [Turn off]" % on, line_is(c, on) is True and c.js(BUTTONS) == ["Change time", "Turn off", "×"]
         and c.js("document.querySelector('#pick .pr .prh b').textContent") == "%s at 9 am" % d1, (c.js(LINE), c.js(BUTTONS)))
    c.click("#pick .pr [data-m=time]")
    case("Change time: the times, the box starting at the post's own time", line_is(c, "What time?") is True and c.js("document.querySelector('#pick .pr input[type=time]').value") == "09:00")
    c.js("(function(){ var i = document.querySelector('#pick .pr input[type=time]'); i.value = '19:30'; })()")
    c.click("#pick .pr [data-own]")
    toast = ppc.wait_toast(c, "Reminder set: %s at 7:30 pm." % d1)
    case("their own time, typed in the box and Set: 'Reminder set: %s at 7:30 pm.', the same event moved" % d1,
         toast is True and btn_is(c, "🔔 Reminder: %s, 7:30 pm" % d1) is True and until(lambda: [e["time"] for e in events(s, rid)] == ["19:30"]), (toast, book(s)))

    # the other post: its own time, and the calendar is not asked again
    lists = len(calls(s, "list"))
    ppc.open_panel(c, cid)
    c.wait_for("%s === %s" % (BTN, json.dumps(SET)), 10)
    row = c.js("Array.from(document.querySelectorAll('#pick .pw > *')).filter(function(e){ return e.textContent; }).map(function(e){ return e.textContent; })")
    case("the carousel's row: Copy caption, Set a reminder to post, Open my words → (no hook)", row == ["Copy caption", SET, "Open my words →"], row)
    c.click("#pick [data-r]"); line_is(c, ASK)
    c.click("#pick .pr [data-m=yes]")
    case("the next post: Remind me opens the times straight away, and the calendar question is not asked again (asked once only)",
         line_is(c, "What time?", 3) is True and len(calls(s, "list")) == lists, (c.js(LINE), len(calls(s, "list")), lists))
    case("...Remind me set nothing by itself (her check 18: never the last time reused silently); the last time only pre-fills the box",
         not qpiece(s, cid).get("remind_on") and c.js("document.querySelector('#pick .pr input[type=time]').value") == "19:30")
    c.click("#pick .pr [data-t=\"12:00\"]")
    toast = ppc.wait_toast(c, "Reminder set: %s at noon." % d2)
    case("Noon: 'Reminder set: %s at noon.'; each post has its own time" % d2, toast is True and btn_is(c, "🔔 Reminder: %s, noon" % d2) is True
         and until(lambda: [e["time"] for e in events(s, cid)] == ["12:00"] and [e["time"] for e in events(s, rid)] == ["19:30"]), (toast, book(s)))

    # a typed time survives a redraw; the drop-down's state survives too
    c.click("#pick [data-r]")
    c.wait_for("%s !== null" % LINE, 5)
    c.click("#pick .pr [data-m=time]"); line_is(c, "What time?")
    c.js("(function(){ var i = document.querySelector('#pick .pr input[type=time]'); i.value = '06:45'; })()")
    c.js("render(LAST)")
    time.sleep(0.5)
    case("a redraw of the page keeps the drop-down as it was, with the time being typed", c.js(LINE) == "What time?" and c.js("document.querySelector('#pick .pr input[type=time]').value") == "06:45")
    c.click("#pick .pr .prx")

    # turn off
    ppc.open_panel(c, rid)
    btn_is(c, "🔔 Reminder: %s, 7:30 pm" % d1)
    c.click("#pick [data-r]"); c.wait_for("%s !== null" % LINE, 5)
    c.click("#pick .pr [data-m=off]")
    toast = ppc.wait_toast(c, T_OFF)
    case("Turn off: 'No reminder for this one.', the button back to 'Set a reminder to post', its event removed, the other post's left",
         toast is True and btn_is(c, SET) is True and closed(c) is True and until(lambda: events(s, rid) == []) and len(events(s, cid)) == 1
         and c.js("getComputedStyle(document.querySelector('#pick [data-r]')).backgroundColor") != "rgb(251, 242, 214)", (toast, book(s)))

    # a calendar that says no: the queue is saved, the plain line, Try again
    cfg(s, fail=SAID_NO)
    c.click("#pick [data-r]"); line_is(c, ASK)
    c.click("#pick .pr [data-m=yes]"); line_is(c, "What time?")
    c.click("#pick .pr [data-t=\"20:00\"]")
    toast = ppc.wait_toast(c, "Reminder set: %s at 8 pm." % d1)
    try:
        c.wait_for("%s.indexOf(%s) === 0" % (NOTE, json.dumps(TROUBLE)), 10)
    except Exception:  # noqa: BLE001
        pass
    note = c.js(NOTE)
    case("a calendar that says no: the reminder is saved all the same, and one plain line says the calendar couldn't be updated, with Try again",
         toast is True and qpiece(s, rid).get("remind_time") == "20:00" and note == TROUBLE + " " + SAID_NO + "Try again" and events(s, rid) == [], note)
    cfg(s, list_sleep=1.2)
    c.click("#pick .pn [data-retry]")
    try:
        c.wait_for("%s === ''" % NOTE, 10)
    except Exception:  # noqa: BLE001
        pass
    case("Try again: the calendar catches up and the line goes", c.js(NOTE) == "" and until(lambda: [e["time"] for e in events(s, rid)] == ["20:00"]), (c.js(NOTE), book(s)))

    # a slow calendar: the press is answered at once on the page too
    cfg(s, sleep=3)
    c.click("#pick [data-r]"); c.wait_for("%s !== null" % LINE, 5)
    c.click("#pick .pr [data-m=time]"); line_is(c, "What time?")
    t = time.time()
    c.click("#pick .pr [data-t=\"09:00\"]")
    toast = ppc.wait_toast(c, "Reminder set: %s at 9 am." % d1)
    took = time.time() - t
    case("a calendar that takes 3 seconds: the toast and the yellow button come at once", toast is True and took < 2 and btn_is(c, "🔔 Reminder: %s, 9 am" % d1, 2) is True
         and [e["time"] for e in events(s, rid)] == ["20:00"], (toast, round(took, 2)))
    cfg(s)
    case("...and the calendar follows when it answers", until(lambda: [e["time"] for e in events(s, rid)] == ["09:00"], 30) and settle(s, 30), book(s))

    # the calendar list failing, then slow: the plain line, Try again, the hint
    p = s.posting(); p["remind"].pop("calendar", None)
    for x in p["pieces"]:
        x["remind_on"] = False
    s.write_posting(p)
    cfg(s, list_fail="Calendar took too long to answer.")
    time.sleep(3.2)
    c.open(s.url("/posting.html"))
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    ppc.open_panel(c, rid)
    c.wait_for("%s === %s" % (BTN, json.dumps(SET)), 10)
    c.click("#pick [data-r]"); line_is(c, ASK)
    c.click("#pick .pr [data-m=yes]")
    case("the calendars can't be read: 'I can’t reach your Calendar right now.' and the reason, with Try again",
         line_is(c, CANT + " Calendar took too long to answer.") is True and c.js(BUTTONS) == ["Try again", "×"], (c.js(LINE), c.js(BUTTONS)))
    cfg(s, list_sleep=10)
    time.sleep(3.2)
    c.click("#pick .pr [data-m=again]")
    case("Try again asks again: the waiting line", line_is(c, FINDING, 3) is True)
    time.sleep(4)
    case("...still only her waiting line after four seconds (Calendar opening by itself takes about that)", c.js(LINE) == FINDING, c.js(LINE))
    slow = line_is(c, FINDING + " If your Mac asks whether this can use your Calendar, say yes.", 6)
    case("...a list that is slow to come (macOS may be asking its question): after eight seconds the waiting line says what to do", slow is True, slow)
    case("...and then the question", line_is(c, WHICH, 10) is True)
    c.click("#pick .pr .prx")
    cfg(s)

    # her checks 17 to 19, on our page's own source
    case("her check 17: the page offers 9 am, Noon, 6 pm, 8 pm and their own",
         all(k in SOURCE for k in ("['09:00','9 am']", "['12:00','Noon']", "['18:00','6 pm']", "['20:00','8 pm']")) and "inp.type='time'" in SOURCE)
    case("her check 18: Remind me always opens the times", "r.querySelector('[data-m=\"yes\"]').onclick=()=>pickRemind(el,x,'time')" in SOURCE)
    case("her check 19: I'll post it myself closes it", "I'll post it myself" in SOURCE)
    case("nothing of theirs became a tag or ran", c.js("window.pwned") is None)


def check_page_pc(c, s):
    reel, car = fresh_queue(s, "file", opener="log")
    rid = reel["id"]
    d1 = day(reel["date"])
    c.open(s.url("/posting.html"))
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    ppc.open_panel(c, rid)
    c.wait_for("%s === %s" % (BTN, json.dumps(SET)), 10)
    c.click("#pick [data-r]")
    case("a PC: the first line promises only a calendar file, never the phone", line_is(c, PC_ASK) is True and c.js(BUTTONS) == ["Remind me", "I'll post it myself", "×"], c.js(LINE))
    c.click("#pick .pr [data-m=yes]")
    case("a PC: Remind me goes straight to the times (there is no calendar to choose)", line_is(c, "What time?", 3) is True and s.posting().get("remind") in (None, {}), c.js(LINE))
    c.click("#pick .pr [data-t=\"09:00\"]")
    toast = ppc.wait_toast(c, "Reminder ready: %s at 9 am. Add it to your calendar." % d1)
    new = "🔔 Your reminder for %s at 9 am is ready. It isn’t on your calendar until you add it." % d1
    case("a PC: the toast says ready, not set; the line stays open and says it is not on the calendar until they add it, with the button",
         toast is True and line_is(c, new) is True and c.js(BUTTONS) == ["Add to my calendar", "Change time", "Turn off", "×"], (toast, c.js(LINE), c.js(BUTTONS)))
    case("...the row's button is the same pale yellow one", c.js(BTN) == "🔔 Reminder: %s, 9 am" % d1)
    c.click("#pick .pr [data-m=add]")
    toast = ppc.wait_toast(c, "Opened in your calendar app. Say yes to it there.")
    handed = "🔔 Reminder for %s at 9 am: opened in your calendar app. I can’t see your calendar, so check that it’s there and that it has an alert." % d1
    case("Add to my calendar: the file is opened (the opener was called), and the line says what is known and what isn't",
         toast is True and len(calls(s, "open")) == 1 and line_is(c, handed) is True and c.js(BUTTONS) == ["Change time", "Turn off", "×"], (toast, c.js(LINE), calls(s, "open")))
    c.click("#pick .pr [data-m=time]"); line_is(c, "What time?")
    c.click("#pick .pr [data-t=\"12:00\"]")
    again = "🔔 Your reminder for %s at noon has changed. Add it to your calendar again." % d1
    case("a new time on a PC: the line says it changed and has to be added again", line_is(c, again) is True and c.js(BUTTONS) == ["Add it again", "Change time", "Turn off", "×"], (c.js(LINE), c.js(BUTTONS)))
    c.click("#pick .pr [data-m=off]")
    toast = ppc.wait_toast(c, "Reminder off. Take it off your calendar too.")
    off = "This reminder is off. If it’s already on your calendar, take it off there too. If your calendar app keeps it, delete that one event by hand."
    case("Turn off on a PC, after it was opened once: the line says what a PC cannot promise, with the file that takes it off",
         toast is True and line_is(c, off) is True and c.js(BUTTONS) == ["Take it off my calendar", "Set a new reminder", "×"] and c.js(BTN) == SET, (toast, c.js(LINE), c.js(BUTTONS)))
    c.click("#pick .pr [data-m=take]")
    toast = ppc.wait_toast(c, "Opened in your calendar app. Say yes to it there.")
    case("...Take it off my calendar opens that file, and the drop-down is back to the first question", toast is True and len(calls(s, "open")) == 2 and line_is(c, PC_ASK) is True, (toast, c.js(LINE)))
    c.click("#pick .pr [data-m=yes]"); line_is(c, "What time?")
    c.click("#pick .pr [data-t=\"18:00\"]")
    line_is(c, "🔔 Your reminder for %s at 6 pm has changed. Add it to your calendar again." % d1)
    cfg(s, opener="fail")
    c.click("#pick .pr [data-m=add]")
    toast = ppc.wait_toast(c, "I couldn’t open that calendar file. Tell Claude instead.")
    case("a file that can't be opened: said plainly, and it is still waiting", toast is True and reminding(s).get("waiting") == {rid: "again"}, toast)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=8970)
    ap.add_argument("--no-chrome", action="store_true", help="the routes and the command line only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="posting-reminders-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    s = wpc.Setup(work, a.port)
    s.env["REMINDERS_BACKEND"] = "pretend"    # never the real Calendar
    os.environ["REMINDERS_BACKEND"] = "none"
    s.make()
    s.reel_made()
    s.slides_made(4)
    s.words("draft", "reel", {"caption": CAPTION, "hooks": HOOKS})
    s.words("draft", "carousel", {"caption": "A carousel caption."})
    wpc.page_module(s)
    try:
        group("the test switch", check_switch, s, a.port)
        ids = group("the routes and the background", check_routes, s)
        if ids:
            group("the command line", check_commands, s, *ids)
        else:
            skip("the command line: the routes did not run to their end")
        group("the PC way", check_pc, s)
        group("the fix round: a change by another program during a calendar call", check_another_program, s)
        group("the fix round: plain words for the page", check_plain_words, s)
        group("the fix round: a press while the server starts over", check_starting_over, s)
        group("the fix round: a post with no posting day", check_no_day, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                group("the page: every state of the drop-down", check_page, c, s)
                group("the page on a PC's way", check_page_pc, c, s)
                group("the page: a post with no posting day", check_page_no_day, c, s)
    finally:
        s.stop()
        chrome_drive.stop_all()
        time.sleep(0.3)
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return wpc.summary()


if __name__ == "__main__":
    sys.exit(main())
