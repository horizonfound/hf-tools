#!/usr/bin/env python3
"""Posting-day reminders: on the day a post is due, their phone tells them, with the caption inside, ready to
copy (Nicole's handoff v21, Nov 10, built our way; Dustin's decisions 3 and 9).

Each reminded post is ONE event on their calendar, on its posting day at the time they chose for that post,
15 minutes long, with an alert at the start. Its title is "Post your <shoot> <kind> today"; its notes hold the
reel's picked hook, the cover line, and the whole caption last, so it can be copied straight from the
notification. Offered, never assumed; each post has its own time; nothing is made before a calendar is chosen.

This file never touches the posting queue's file or its lock. It is handed the queue (a dict, as
posting_queue.load() gives), works out what the calendar should hold, talks to the calendar, and hands back
the few fields that changed for the caller to merge into a freshly loaded queue under its own lock, so a slow
calendar can never write over a newer queue. (posting_queue.py already has a function called reminders(): the
taps in the chat. Import this file as `import reminders as posting_reminders` there.)

    python3 reminders.py status       which calendar, and every post's reminder, in plain words
    python3 reminders.py calendars    the calendars a reminder could go on (a Mac asks the Calendar app)
    python3 reminders.py sync [--all] bring the calendar in step with the queue now (--all sends every one again)
    python3 reminders.py open         a PC: open the calendar files that are waiting to be added

A post whose kit can't be read right now (its drive is unplugged, or its words can't be read) still has its
reminder MOVED when its day or time changes; only the notes are left as they were, and sent once the kit is
back. A reminder that does not exist yet is not made until then, and that is said plainly. A post whose date
is not a real day is left alone, with a plain line; neither ever stops the other posts' reminders.

What is kept in the queue, as in Nicole's: p["remind"] = {"calendar", "time"} (time: the last one used, only to
pre-fill the time box), and on a piece remind_on, remind_time, event_uid, event_sig, event_cal.
Our own small notes live in <STUDIO_HOME>/reminders/: made.json (which event belongs to which post, written the
moment the calendar answers, so a save that fails afterwards never leads to a second event), and on a PC the
calendar files and state.json.

A Mac: the Calendar app, through AppleScript ("osascript -", the script on stdin and every value an argument,
so a caption with quotes or new lines needs no escaping). What Nicole's Mac taught (her "How it talks to
Calendar"): the calendar list is read as two lists (names, writable) and paired here; an event that moves
later has its end set before its start; Calendar is started hidden first when it isn't running; 120 seconds
for each call. Only an event this file made is ever changed or removed, found by the uid it saved.

A PC (decision 3): there is no Calendar app to ask, so each reminded post is a calendar file (.ics) in
<STUDIO_HOME>/reminders/, one event with an alert, the notes, a steady id per post and a number that goes up
with every change. WHAT A PC CANNOT MATCH, said plainly:
  - Nothing reaches their calendar until they open the file and accept it in their calendar app. Every change
    (a new date, a new time, an edited caption) is a new file to accept; the Mac does all of that unasked.
  - Whether opening a changed file REPLACES the earlier event or adds a second one is the calendar app's
    choice. The file does what the standard asks (same UID, higher SEQUENCE). Not tried on any PC calendar app.
  - A removal is a file that says the event is cancelled (METHOD:CANCEL, STATUS:CANCELLED). Whether the app
    takes the event away is the app's choice; several ignore a cancel that comes from a file. If theirs does,
    they delete that one event by hand; the page should say so.
  - There is no list of calendars to choose from: their calendar app asks which calendar when the file opens.
    So "nothing is made before a calendar is chosen" does not apply; turning a reminder on is enough.
  - This file cannot see their calendar, so it cannot tell an event they deleted from one that is still there.
  - Whether the phone shows it depends on that calendar syncing to their phone, as on a Mac, but here nothing
    was chosen with that in mind.
  - THE ALERT ITSELF MAY NOT SURVIVE. The file carries an alert at the start (VALARM), but keeping it is the
    calendar app's choice. Google Calendar's import is widely reported to ignore a file's alert and use the
    calendar's own default notification (or none); Outlook.com and the new Outlook put their own default
    reminder in its place. So a PC photographer can see the event and still hear nothing at 9 am.
  - Google Calendar is a website, not an app: opening the file starts whatever Windows has for .ics (the new
    Outlook, or a "choose an app" box), not Google. Someone whose calendar is Google's imports the file by
    hand (Settings, Import), and may get no alert (above).
  - A reminder they deleted by hand may not come back from the same file: Google's import quietly skips an
    id it has seen before, and every file of a post carries that post's one steady id.
  (The last three are from general knowledge of those apps, not tried on a PC. Nothing about a PC's calendar
  may be promised before it is tried on the new Outlook and on Google's import. PC_GAPS below holds the
  short form of this list for the page and the chat to say from.)
Opening a file in their calendar app is a step of its own (open_waiting), never part of a sync: a sync runs in
the background and must not pop windows up.

Exit: 0 done, 1 the calendar could not be reached (said in plain words), 2 no command given.
Python 3.9, nothing installed, UTF-8 everywhere. Nothing here posts or sends anything (rule 5).
"""
import argparse
import contextlib
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer   # noqa: E402

MINUTES = 15                       # how long the event is
DEFAULT_TIME = "18:00"             # only when neither the post nor the queue has one (Nicole's 6 pm)
TIMEOUT = 120                      # seconds for one call to Calendar
TIME = re.compile(r"([01]\d|2[0-3]):[0-5]\d")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
FIELDS = ("event_uid", "event_sig", "event_cal")
PIECE_KEYS = ("id", "shoot_name", "kind", "status", "date", "cover", "kit", "n", "remind_on", "remind_time") + FIELDS
SKIP_CALENDARS = {"birthdays", "united states holidays", "us holidays", "holidays", "siri suggestions",
                  "scheduled reminders"}
HEX_NAME = re.compile(r"[0-9a-f]{24,}|[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", re.I)
FILE_CALENDAR = "calendar file"    # what event_cal says on a PC, where no calendar is chosen
NO_CAPTION = "No caption yet. Write it on your words page in the post kit."
KIND_WORDS = {"reel": "reel", "carousel": "carousel", "single": "single post"}   # "single post" is ours: hers has no singles
AWAY = "away-"                     # event_sig after a move made without the notes: never equal to a whole one,
                                   # so the notes are sent the first time the kit can be read again
WHY = {"kit": "its post kit isn't plugged in right now", "words": "its words couldn't be read just now"}
BACK = {"kit": "Plug its drive in and it will be made.", "words": "It will be tried again next time."}
# What a PC's calendar files cannot promise, in short (the long form is at the top of this file). For the page
# and the chat to say from; the final wording is Dustin and Nicole's.
PC_GAPS = (
    "Nothing is on your calendar until you open the calendar file and accept it in your calendar app, and again after every change.",
    "Your calendar app decides whether a changed file replaces the earlier event or adds a second one.",
    "Your calendar app may ignore the file that turns a reminder off; then delete that one event by hand.",
    "The alert may be dropped or swapped for your calendar app's own default: Google Calendar's import and Outlook are reported to do this, so the event can be there with no sound at its time.",
    "Google Calendar is a website: the file has to be imported there by hand (Settings, Import).",
    "A reminder deleted by hand may not come back from the same file (Google's import skips one it has seen).",
    "The Assistant cannot see your calendar, so it cannot tell whether a reminder is really there.",
)
_ONE_SYNC = threading.Lock()       # one sync at a time in this program, so two never make the same event twice


class CalendarProblem(Exception):
    """The calendar could not be reached or said no. The message is in plain words, for the photographer."""


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass
    except OSError as e:
        import errno
        if not (this_computer.WINDOWS and e.errno == errno.EINVAL):
            raise


def home():
    """The Assistant's own folder (STUDIO_HOME or ~/.studio), asked every time so a test's scratch one is used."""
    return Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))


def notes_dir():
    return home() / "reminders"


def _write_whole(path, data):
    """Save a file whole (bytes or text): under a scratch name beside it, then put in place in one step."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        if isinstance(data, bytes):
            tmp.write_bytes(data)
        else:
            tmp.write_text(data, encoding="utf-8")
        this_computer.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _read_json(path, empty):
    try:
        got = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty
    return got if isinstance(got, type(empty)) else empty


# ---------------------------------------------------------------- the words, pure

def time_words(t):
    """"09:00" -> "9 am", "12:00" -> "noon", "18:30" -> "6:30 pm" (as Nicole's page says them)."""
    if not t or not TIME.fullmatch(str(t)):
        return ""
    h, m = (int(v) for v in t.split(":"))
    ap = "pm" if h >= 12 else "am"
    h12 = h % 12 or 12
    if h == 12 and m == 0:
        return "noon"
    return f"{h12}{':%02d' % m if m else ''} {ap}"


def day_words(iso):
    """"2026-11-11" -> "Wed, Nov 11"."""
    try:
        d = date.fromisoformat(str(iso))
    except ValueError:
        return str(iso or "")
    return this_computer.strftime(d, "%a, %b %-d")


def when_words(iso, t):
    return f"{day_words(iso)} at {time_words(t)}"


def piece_words(x):
    """"Hannah reel", "Hannah carousel", "Hannah single post 2"."""
    return f"{x.get('shoot_name') or 'your'} {KIND_WORDS.get(x.get('kind'), x.get('kind') or 'post')}" + (f" {x['n']}" if x.get("n") else "")


def title(piece):
    """The event's title: "Post your Hannah reel today"."""
    return f"Post your {piece_words(piece)} today"


def words_piece(piece):
    """Which part of a kit's words record a queue piece reads: the reel's, or the carousel's (a carousel saved
    as one slide is a single post whose words are the carousel's; a photo from the Singles folder has none)."""
    if piece.get("kind") == "reel":
        return "reel"
    if piece.get("kind") == "carousel" or str(piece.get("id") or "").endswith("-carousel"):
        return "carousel"
    return None


def first_slide(cover):
    """Whether a carousel's grid photo is its slide 1, from the file's name: the last number in it is 1
    ("Hannah carousel - slide 01.jpg", "Slide 01 (Canva).jpg", "Hannah carousel (2) - slide 01.jpg")."""
    nums = re.findall(r"\d+", Path(str(cover).replace("\\", "/")).stem)
    return bool(nums) and int(nums[-1]) == 1


def _clean(text):
    """Text as a calendar can hold it: one kind of line end, no other control characters."""
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


def picked_hook(w):
    """The first hook they picked, or ""."""
    hooks, picked = w.get("hooks"), w.get("picked")
    if not isinstance(hooks, list) or not isinstance(picked, list) or not picked:
        return ""
    i = picked[0]
    if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(hooks):
        return ""
    return _clean(hooks[i]).strip()


def notes(piece, words_record):
    """The event's notes, word for word as Nicole's: for a reel the picked hook and the cover line, for a
    carousel the "isn't slide 1" line, then the whole caption last. words_record is the piece's part of the
    kit's words record ({"caption", "own", "hooks", "picked"}), or the whole record ({"pieces": {...}})."""
    w = words_record if isinstance(words_record, dict) else {}
    if isinstance(w.get("pieces"), dict):
        w = w["pieces"].get(words_piece(piece) or "") or {}
        w = w if isinstance(w, dict) else {}
    cap = _clean(w.get("caption") or w.get("own") or "").strip()
    lines = []
    if piece.get("kind") == "reel":
        hook = picked_hook(w)
        if hook:
            lines += ["Your hook, on the first second:", hook, ""]
        if piece.get("cover"):
            lines += ["When you post, tap Edit cover and choose the photo you picked for your grid.", ""]
    elif piece.get("kind") == "carousel" and piece.get("cover") and not first_slide(piece["cover"]):
        lines += ["Your grid photo isn't slide 1: move it to the front before you post.", ""]
    lines += ["Your caption (copy everything below):", "", cap or NO_CAPTION]
    return "\n".join(lines)


def signature(cal, day, t, ttl, nts):
    """What the event holds, as one short text: when it matches the one saved, the calendar isn't touched."""
    return hashlib.sha1(json.dumps([cal, day, t, ttl, nts]).encode("utf-8")).hexdigest()[:16]


class KitAway(Exception):
    """A post's kit can't be reached right now (its drive is unplugged), so its words can't be read."""


def words_for(piece):
    """The piece's part of its kit's words record, read straight from words.py (never over the network).
    {} for a piece with no kit or no words. KitAway when the kit's folder isn't there right now: its reminder is
    then left exactly as it is, never rewritten as if the caption had been taken out."""
    which = words_piece(piece)
    if not piece.get("kit") or not which:
        return {}
    kit = Path(piece["kit"])
    if not kit.is_dir():
        raise KitAway(str(kit))
    import words as words_mod     # here, not at the top: it brings kit.py and its friends with it
    got = (words_mod.load(kit).get("pieces") or {}).get(which)
    return got if isinstance(got, dict) else {}


# ---------------------------------------------------------------- what should be there, pure

def snapshot(p):
    """A copy of only what the reminders read from the queue, safe to keep after the queue's lock is let go."""
    r = p.get("remind") if isinstance(p.get("remind"), dict) else {}
    return {"remind": {"calendar": r.get("calendar"), "time": r.get("time")},
            "pieces": [copy.deepcopy({k: x[k] for k in PIECE_KEYS if k in x}) for x in p.get("pieces") or [] if isinstance(x, dict) and x.get("id")]}


def _time_of(x, cfg):
    for t in (x.get("remind_time"), cfg.get("time"), DEFAULT_TIME):
        if t and TIME.fullmatch(str(t)):
            return t
    return DEFAULT_TIME


def real_day(day):
    """Whether a date is a real day written YYYY-MM-DD ("2026-02-30" is not)."""
    if not DAY.fullmatch(str(day or "")):
        return False
    try:
        date.fromisoformat(str(day))
    except ValueError:
        return False
    return True


def when_sig(cal, day, t, ttl):
    """Everything the event holds except its notes, as one short text (for a post whose kit can't be read)."""
    return signature(cal, day, t, ttl, "")[:11]


def wanted(p, need_calendar=True, words=None):
    """What each reminded post should have on the calendar: {piece id: {cal, date, time, title, notes, sig}} for
    every piece that is green, has a date, has its reminder on, and (on a Mac) a calendar is chosen.
    A piece whose words can't be read right now (its kit's drive is unplugged: why "kit"; reading them failed:
    why "words") has {"away": True, "why", cal, date, time, title} instead: its day and time can still be
    followed, its notes can't. A piece whose date is not a real day has {"skip": "date"}: leave it alone.
    One piece's trouble never stops another's."""
    words = words or words_for
    cfg = p.get("remind") if isinstance(p.get("remind"), dict) else {}
    cal = cfg.get("calendar") if need_calendar else FILE_CALENDAR
    out = {}
    for x in p.get("pieces") or []:
        if not (x.get("remind_on") and x.get("status") == "green" and x.get("date") and cal):
            continue
        if not real_day(x["date"]):
            out[x["id"]] = {"skip": "date"}
            continue
        t = _time_of(x, cfg)
        ttl = title(x)
        try:
            nts, why = notes(x, words(x)), None
        except KitAway:
            why = "kit"
        except Exception:  # noqa: BLE001  (one post's words that can't be read are that post's trouble only)
            why = "words"
        if why:
            out[x["id"]] = {"away": True, "why": why, "cal": cal, "date": x["date"], "time": t, "title": ttl}
            continue
        out[x["id"]] = {"cal": cal, "date": x["date"], "time": t, "title": ttl, "notes": nts,
                        "sig": signature(cal, x["date"], t, ttl, nts)}
    return out


def plan(p, need_calendar=True, words=None, made=None, force=False):
    """What to do to the calendar, in order: a list of {"do": "make" | "update" | "move" | "remove" | "leave",
    "id", "name", ...}.
    make: no event yet. update: ours is there (uid) and what it should hold changed. remove: ours is there and
    the post is no longer ready, or its reminder was turned off (a POSTED post keeps its event). A calendar
    that changed is a remove from the old one, then a make. move: the post's words can't be read right now and
    its day, time or title changed: ours is moved where it is, its notes untouched ("sig" is then AWAY + the
    when-signature, so the notes follow once the words can be read). leave: nothing to do to the calendar,
    with "why" ("kit", "words" or "date") and "made" (whether an event of ours is there).
    made: our own note of events made ({id: {uid, cal, when}}), used when the queue never got the uid, and to
    tell whether a post whose words can't be read has moved. force: send every wanted one again (a repair)."""
    want = wanted(p, need_calendar, words)
    made = made or {}
    acts = []
    for x in p.get("pieces") or []:
        pid, w = x["id"], want.get(x["id"])
        uid, cal_was = x.get("event_uid"), x.get("event_cal")
        note = made.get(pid) if isinstance(made.get(pid), dict) else {}
        if not uid and note.get("uid"):
            uid, cal_was = note["uid"], note.get("cal")          # made, but the queue never heard
            known = False
        else:
            known = True
        name = piece_words(x)
        if w and w.get("skip"):
            acts.append({"do": "leave", "id": pid, "name": name, "why": w["skip"], "made": bool(uid)})
            continue
        if w and w.get("away"):
            if not uid:
                acts.append({"do": "leave", "id": pid, "name": name, "why": w["why"], "made": False})
                continue
            at = cal_was or w["cal"]                 # where ours is; a new calendar waits until it can be made there
            ws = when_sig(at, w["date"], w["time"], w["title"])
            in_step = (note.get("uid") == uid and note.get("when") == ws) or x.get("event_sig") == AWAY + ws
            if in_step and known and not force:
                acts.append({"do": "leave", "id": pid, "name": name, "why": w["why"], "made": True})
            else:
                acts.append({"do": "move", "id": pid, "name": name, "uid": uid, "cal": at, "date": w["date"],
                             "time": w["time"], "title": w["title"], "sig": AWAY + ws, "why": w["why"]})
            continue
        if w:
            if uid and cal_was and cal_was != w["cal"]:
                acts.append({"do": "remove", "id": pid, "name": name, "uid": uid, "cal": cal_was, "then": "make"})
                uid = None
            if not uid:
                acts.append(dict(w, do="make", id=pid, name=name, uid=""))
            elif force or not known or w["sig"] != x.get("event_sig"):
                acts.append(dict(w, do="update", id=pid, name=name, uid=uid))
        elif uid and x.get("status") != "posted":
            acts.append({"do": "remove", "id": pid, "name": name, "uid": uid,
                         "cal": cal_was or (p.get("remind") or {}).get("calendar") or ""})
    return acts


# ---------------------------------------------------------------- a Mac: the Calendar app

# Make or change one event. argv: calendar, uid ("" for a new one), year, month, day, hour, minute, minutes long,
# title, notes, and "keep" to leave the notes as they are (a move made while the post's words can't be read).
# Prints the event's uid. An event we made that has since been deleted is made again; with "keep" it is NOT
# (there are no notes to give it) and nothing is printed.
# Looking for our event is a plain "every event ... whose uid is" with NO try around it: no such event is an
# empty list, and anything else that goes wrong (Calendar busy, a time-out) is an error that reaches us, so the
# uid is kept and the next round tries again. A bare try here once meant any error looked like "not there" and
# a second event was made beside the first.
MAC_SET = r'''
on run argv
  set {calName, uidIn, y, mo, dd, hh, mi, mins, ttl, nts, keepNotes} to argv
  set d to current date
  set day of d to 1
  set year of d to (y as integer)
  set month of d to (mo as integer)
  set day of d to (dd as integer)
  set hours of d to (hh as integer)
  set minutes of d to (mi as integer)
  set seconds of d to 0
  set dEnd to d + (mins as integer) * minutes
  tell application "Calendar"
    set c to first calendar whose name is calName
    set e to missing value
    if uidIn is not "" then
      set found to (every event of c whose uid is uidIn)
      if (count of found) > 0 then set e to item 1 of found
    end if
    if e is missing value then
      if keepNotes is "keep" then return ""
      set e to make new event at end of events of c with properties {summary:ttl, start date:d, end date:dEnd, description:nts}
      make new display alarm at end of display alarms of e with properties {trigger interval:0}
    else
      if d > (end date of e) then
        set end date of e to dEnd
        set start date of e to d
      else
        set start date of e to d
        set end date of e to dEnd
      end if
      set summary of e to ttl
      if keepNotes is not "keep" then set description of e to nts
    end if
    return uid of e
  end tell
end run
'''
# Remove one event of ours. argv: calendar, uid. Prints "removed", or "gone" when it (or its calendar) is no
# longer there. Anything else that goes wrong is an error, so the uid is kept and the removal tried again.
MAC_REMOVE = r'''
on run argv
  set {calName, uidIn} to argv
  if uidIn is "" then return "gone"
  tell application "Calendar"
    if not (exists calendar calName) then return "gone"
    set es to (every event of calendar calName whose uid is uidIn)
    if (count of es) is 0 then return "gone"
    repeat with e in es
      delete e
    end repeat
  end tell
  return "removed"
end run
'''
# The calendars, as two lists read whole (about a second; asking Calendar for "every calendar whose writable is
# true" took 25 seconds and more on Nicole's Mac). Paired in Python (pair_calendars).
MAC_LIST_MARK = "----writable----"
MAC_LIST = r'''
tell application "Calendar"
  set ns to name of every calendar
  set ws to writable of every calendar
end tell
set out to ""
repeat with n in ns
  set out to out & (n as text) & linefeed
end repeat
set out to out & "----writable----" & linefeed
repeat with w in ws
  set out to out & (w as text) & linefeed
end repeat
return out
'''


def pair_calendars(text):
    """MAC_LIST's answer -> the names a reminder could go on: writable, not Birthdays, Holidays, Siri
    Suggestions or Scheduled Reminders, not a long hex id, each name once, in Calendar's order."""
    rows = [r.strip() for r in str(text).replace("\r", "\n").split("\n")]
    if MAC_LIST_MARK not in rows:
        raise CalendarProblem("Calendar's answer couldn't be read.")
    cut = rows.index(MAC_LIST_MARK)
    names, writable = rows[:cut], [r for r in rows[cut + 1:] if r]
    while names and not names[-1]:
        names.pop()
    if len(names) != len(writable):
        raise CalendarProblem("Calendar's answer couldn't be read.")
    out = []
    for n, w in zip(names, writable):
        if w.lower() != "true" or not n or n.lower() in SKIP_CALENDARS or HEX_NAME.fullmatch(n) or n in out:
            continue
        out.append(n)
    return out


def _problem_words(err):
    """Calendar's or macOS's error, in plain words."""
    e = str(err or "").strip()
    low = e.lower()
    if "-1743" in e or "not authorized" in low or "not allowed" in low:
        return ("This Mac hasn't been allowed to use Calendar yet. Open System Settings, Privacy & Security, "
                "Automation, and turn on Calendar for the app you run the Assistant in.")
    if "-1712" in e or "timed out" in low:
        return "Calendar took too long to answer."
    if "-1728" in e or "can\u2019t get calendar" in low or "can't get calendar" in low or "can\u2019t get first calendar" in low or "can't get first calendar" in low:
        return "That calendar isn't in Calendar any more."
    if "-600" in e or "isn\u2019t running" in low or "isn't running" in low:
        return "Calendar wasn't open and couldn't be started."
    return ("Calendar said no: " + e[:160]) if e else "Calendar said no."


def _calendar_running():
    r = subprocess.run(["pgrep", "-x", "Calendar"], capture_output=True)   # pc-ok: only a Mac gets here (MacCalendar's own runner)
    return r.returncode == 0


def _osascript(script, args=(), timeout=TIMEOUT):
    """Run one AppleScript against Calendar: the script on stdin, the values as arguments. What it printed.
    Calendar is started hidden first when it isn't running (AppleScript's own launch said "Application isn't
    running" on Nicole's Mac). CalendarProblem, in plain words, for anything that goes wrong.
    NEVER run by a test: MacCalendar takes a pretend runner."""
    if not this_computer.MAC:
        raise CalendarProblem("The Calendar app is on a Mac only.")
    try:
        if not _calendar_running():
            subprocess.run(["open", "-g", "-a", "Calendar"], capture_output=True, timeout=30)   # pc-ok: only a Mac gets here
            end = time.time() + 15
            while time.time() < end and not _calendar_running():
                time.sleep(0.5)
            time.sleep(3)
        r = subprocess.run(["osascript", "-", *[str(a) for a in args]], input=script, capture_output=True,   # pc-ok: only a Mac gets here
                           encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CalendarProblem("Calendar took too long to answer.")
    except OSError as e:
        raise CalendarProblem(f"Calendar couldn't be asked ({e}).")
    if r.returncode != 0:
        raise CalendarProblem(_problem_words(r.stderr))
    return r.stdout.strip()


class MacCalendar:
    """The Mac's Calendar app. run(script, args) -> text is the one thing that talks to it; a test hands in a
    pretend one."""
    name = "mac"
    needs_calendar = True
    opens_files = False

    def __init__(self, run=None):
        self.run = run or _osascript

    def calendars(self):
        return pair_calendars(self.run(MAC_LIST, ()))

    def set(self, piece_id, cal, uid, day, t, ttl, nts, keep_notes=False):
        """Make or change the event; its uid. keep_notes: move ours and leave its notes as they are; None when
        ours isn't there any more (nothing is made: there are no notes to give it)."""
        if not real_day(day):
            raise CalendarProblem("That posting date isn't a real day.")   # AppleScript would roll Feb 30 into March
        y, mo, dd = (int(v) for v in day.split("-"))
        hh, mi = (int(v) for v in t.split(":"))
        if keep_notes and not uid:
            return None
        got = str(self.run(MAC_SET, (cal, uid or "", y, mo, dd, hh, mi, MINUTES, _clean(ttl), _clean(nts),
                                     "keep" if keep_notes else ""))).strip()
        if not got:
            if keep_notes:
                return None
            raise CalendarProblem("Calendar didn't say which event it made.")
        return got

    def remove(self, piece_id, cal, uid):
        if uid and cal:
            self.run(MAC_REMOVE, (cal, uid))


# ---------------------------------------------------------------- a PC: a calendar file per post

def ics_escape(text):
    """Text as a calendar file holds it (RFC 5545, 3.3.11): backslash, semicolon and comma escaped, a new line
    as \\n."""
    return _clean(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n").replace("\t", " ")


def ics_fold(line):
    """One content line as bytes, folded so no line is longer than 75 octets (RFC 5545, 3.1): each further line
    starts with one space, and a letter of several bytes is never cut in two. Without the line ends."""
    out, cur, room = [], b"", 75
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > room:
            out.append(cur)
            cur, room = b" ", 75
        cur += b
    out.append(cur)
    return out


def steady_uid(piece_id):
    """The same id for a post every time, so a changed file is the same event to their calendar app."""
    return "post-" + hashlib.sha1(str(piece_id).encode("utf-8")).hexdigest()[:20] + "@the-assistant.horizonfound"


def ics_bytes(uid, seq, day, t, ttl, nts, cancel=False, stamp=None):
    """One calendar file: one event with an alert at its start (or, cancel=True, the word that it is off).
    Local "floating" time, so 9 am is 9 am wherever they are. CRLF line ends, UTF-8."""
    start = datetime.strptime(f"{day} {t}", "%Y-%m-%d %H:%M")
    end = start + timedelta(minutes=MINUTES)
    stamp = stamp or datetime.now(timezone.utc)
    rows = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Horizon Found//The Assistant//EN", "CALSCALE:GREGORIAN",
            "METHOD:CANCEL" if cancel else "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            "UID:" + uid,
            "DTSTAMP:" + stamp.strftime("%Y%m%dT%H%M%SZ"),
            f"SEQUENCE:{int(seq)}",
            "DTSTART:" + start.strftime("%Y%m%dT%H%M%S"),
            "DTEND:" + end.strftime("%Y%m%dT%H%M%S"),
            "SUMMARY:" + ics_escape(ttl),
            "DESCRIPTION:" + ics_escape(nts),
            "STATUS:CANCELLED" if cancel else "STATUS:CONFIRMED",
            "TRANSP:TRANSPARENT"]
    if not cancel:
        rows += ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + ics_escape(ttl), "TRIGGER:PT0M", "END:VALARM"]
    rows += ["END:VEVENT", "END:VCALENDAR"]
    return b"".join(part + b"\r\n" for row in rows for part in ics_fold(row))


def open_file(path):
    """Open a calendar file in their calendar app. A PC: Windows' own "open this file" (os.startfile). Unproven
    on a real PC. Anywhere else: said plainly, nothing opened."""
    if this_computer.WINDOWS:
        os.startfile(str(path))   # noqa  (a PC only; os.startfile does not exist elsewhere)
        return
    raise CalendarProblem("Opening a calendar file is set up for a PC only.")


class CalendarFiles:
    """The PC way: a calendar file per reminded post in <STUDIO_HOME>/reminders/. Writing a file is all a sync
    does; opening them (open_waiting) is a step of its own. state.json remembers each event's number (SEQUENCE)
    and which files have not been opened since they last changed."""
    name = "file"
    needs_calendar = False
    opens_files = True

    def __init__(self, folder=None, opener=None, clock=None):
        self.folder = Path(folder) if folder else None
        self.opener = opener or open_file
        self.clock = clock or time.time

    def _dir(self):
        return self.folder or notes_dir()

    def _state(self):
        return _read_json(self._dir() / "state.json", {})

    def _save(self, st):
        _write_whole(self._dir() / "state.json", json.dumps(st, indent=1, ensure_ascii=False))

    def _next(self, st, uid):
        """A number higher than any this event has had: the seconds since 2026 began, so it still goes up if
        state.json is ever lost, and one more than the last when two changes fall in the same second."""
        by_clock = max(0, int(self.clock()) - 1767225600)
        return max(by_clock, int((st.get(uid) or {}).get("seq") or 0) + 1)

    def calendars(self):
        return []

    def file_for(self, piece_id, ttl):
        tag = hashlib.sha1(str(piece_id).encode("utf-8")).hexdigest()[:6]
        return this_computer.safe_name(f"{ttl} ({tag})", limit=70, fallback=f"Reminder ({tag})") + ".ics"

    def set(self, piece_id, cal, uid, day, t, ttl, nts, keep_notes=False):
        """Write the post's calendar file; its id. keep_notes: the same notes as last time (kept in state.json);
        None when there is no live file of ours to move."""
        st = self._state()
        uid = steady_uid(piece_id)
        if keep_notes:
            was = st.get(uid)
            if not isinstance(was, dict) or was.get("cancelled") or not isinstance(was.get("notes"), str):
                return None
            nts = was["notes"]
        seq = self._next(st, uid)
        old = (st.get(uid) or {}).get("file")
        name = old or self.file_for(piece_id, ttl)
        _write_whole(self._dir() / name, ics_bytes(uid, seq, day, t, ttl, nts))
        st[uid] = {"id": piece_id, "seq": seq, "file": name, "date": day, "time": t, "title": ttl, "notes": nts, "opened": None,
                   "cancelled": False, "ever_opened": bool((st.get(uid) or {}).get("ever_opened"))}
        self._save(st)
        return uid

    def remove(self, piece_id, cal, uid):
        st = self._state()
        e = st.get(uid)
        if not isinstance(e, dict) or e.get("cancelled"):       # not one of ours, or already off: nothing to do
            return
        seq = self._next(st, uid)
        if not e.get("ever_opened"):
            # never opened through open_waiting, so never handed to their calendar: there is nothing to cancel
            # there, and the file (ours, in our own folder) just goes
            try:
                (self._dir() / e["file"]).unlink()
            except OSError:
                pass
            st[uid] = dict(e, seq=seq, cancelled=True, opened=seq)
        else:
            _write_whole(self._dir() / e["file"], ics_bytes(uid, seq, e["date"], e["time"], e["title"],
                                                           "This reminder was turned off.", cancel=True))
            st[uid] = dict(e, seq=seq, cancelled=True, opened=None)
        self._save(st)

    def waiting(self):
        """The files that changed since they were last opened: [{"id", "file" (full path), "title", "cancel"}]."""
        out = []
        for uid, e in sorted(self._state().items(), key=lambda kv: (kv[1].get("date") or "", kv[0])):
            if isinstance(e, dict) and e.get("opened") != e.get("seq") and (self._dir() / str(e.get("file"))).is_file():
                out.append({"id": e.get("id"), "uid": uid, "file": str(self._dir() / e["file"]), "title": e.get("title"), "cancel": bool(e.get("cancelled"))})
        return out

    def handed(self):
        """The ids of the posts whose latest file was opened in their calendar app (through open_waiting). That
        is all that can be known: whether they accepted it there can't be seen."""
        return {e.get("id") for e in self._state().values()
                if isinstance(e, dict) and e.get("ever_opened") and not e.get("cancelled") and e.get("opened") == e.get("seq")}

    def open_waiting(self):
        """Open each waiting file in their calendar app. {"opened": [...], "problem": words or None}."""
        opened = []
        for w in self.waiting():
            try:
                self.opener(w["file"])
            except Exception as e:  # noqa: BLE001  (whatever the opener says, in words; nothing is lost)
                return {"opened": opened, "problem": str(e)[:200] or "That calendar file couldn't be opened."}
            st = self._state()
            if isinstance(st.get(w["uid"]), dict):
                st[w["uid"]]["opened"] = st[w["uid"]].get("seq")
                st[w["uid"]]["ever_opened"] = True
                self._save(st)
            opened.append(w)
        return {"opened": opened, "problem": None}


# ---------------------------------------------------------------- which one

def default_backend():
    """A Mac: the Calendar app. A PC (and anything else): calendar files. REMINDERS_BACKEND=file | mac | none
    says otherwise (a test's programs say file, so a Mac's real calendar is never asked)."""
    which = os.environ.get("REMINDERS_BACKEND", "").strip().lower()
    if which == "none":
        return None
    if which == "file" or (which != "mac" and not this_computer.MAC):
        return CalendarFiles()
    return MacCalendar()


def calendars(backend=None):
    """The calendar names for the first-time question "Which calendar does your phone show?" A Mac asks the
    Calendar app (CalendarProblem in plain words if it can't); a PC has none to choose ([])."""
    backend = backend or default_backend()
    if backend is None:
        return []
    try:
        return list(backend.calendars())
    except CalendarProblem:
        raise
    except Exception as e:  # noqa: BLE001
        raise CalendarProblem(str(e)[:200] or "Calendar couldn't be asked.")


def set_calendar(p, name, backend=None):
    """Choose the calendar reminders go on (changes p; the caller saves). ValueError("no such calendar")
    unless it is one calendars() gives."""
    name = str(name or "")
    if not name or name not in calendars(backend):
        raise ValueError("no such calendar")
    if not isinstance(p.get("remind"), dict):
        p["remind"] = {}
    p["remind"]["calendar"] = name
    return p


def set_reminder(p, piece_id, when):
    """Turn a post's reminder on at "HH:MM", or off with None (changes p; the caller saves, then syncs).
    ValueError("bad time") / ValueError("no such post"). The time also becomes the one the time box starts
    at next time; it is never used for another post by itself."""
    x = next((y for y in p.get("pieces") or [] if y.get("id") == piece_id), None)
    if x is None:
        raise ValueError("no such post")
    if when is None or when == "":
        x["remind_on"] = False
        return x
    if not isinstance(when, str) or not TIME.fullmatch(when):
        raise ValueError("bad time")
    if not isinstance(p.get("remind"), dict):
        p["remind"] = {}
    p["remind"]["time"] = when
    x["remind_on"], x["remind_time"] = True, when
    return x


# ---------------------------------------------------------------- keeping the calendar in step

def _made():
    return _read_json(notes_dir() / "made.json", {})


def _note_made(pid, uid=None, cal=None, when=None):
    """Our own note of which event is which post's (and, as when_sig, where it was put), written the moment the
    calendar answers. Never raises."""
    try:
        m = _made()
        if uid:
            m[pid] = {"uid": uid, "cal": cal, "when": when}
        else:
            m.pop(pid, None)
        _write_whole(notes_dir() / "made.json", json.dumps(m, indent=1, ensure_ascii=False))
    except Exception:  # noqa: BLE001  (a note only; the queue's own fields are what count)
        pass


def sync(p, backend=None, force=False, words=None):
    """Bring the calendar in step with the queue. Never raises, never changes p, holds no lock of the queue's:
    it works from a snapshot, so the caller lets go of its lock first and merges result["changes"] into a
    freshly loaded queue afterwards (merge). Safe to run twice: the second run sends nothing.

    Returns {"changed": bool, "changes": {piece id: {"was": uid before, "event_uid", "event_sig", "event_cal"}}
    (None for a field means take it away), "did": [plain lines], "problem": None or plain words,
    "note": None or "(reminders not updated: ...)", "to_open": the PC's files waiting to be opened}.
    The first calendar problem stops the rest for this run (so a calendar that isn't answering is asked once,
    not once per post); what was done before it is still handed back."""
    res = {"changed": False, "changes": {}, "did": [], "problem": None, "note": None, "to_open": []}
    try:
        snap = snapshot(p)
        if backend is None:
            backend = default_backend()
        if backend is None:
            return res
        acts = plan(snap, need_calendar=getattr(backend, "needs_calendar", True), words=words, made=_made(), force=force)
    except Exception as e:  # noqa: BLE001
        return _stopped(res, e)
    by_id = {x["id"]: x for x in snap["pieces"]}
    files = bool(getattr(backend, "opens_files", False))    # a PC: a file is written, nothing is on a calendar yet
    for a in acts:
        pid = a["id"]
        was = by_id[pid].get("event_uid")
        try:
            if a["do"] == "leave":
                res["did"].append(_left_words(a))
            elif a["do"] == "remove":
                backend.remove(pid, a["cal"], a["uid"])
                _note_made(pid)
                res["changes"][pid] = {"was": was, "event_uid": None, "event_sig": None, "event_cal": None}
                if not a.get("then"):
                    res["did"].append(_did_words("remove", a, files, backend))
            elif a["do"] == "move":
                uid = backend.set(pid, a["cal"], a["uid"], a["date"], a["time"], a["title"], None, keep_notes=True)
                if uid is None:                    # ours isn't there any more, and without its words it can't be made
                    _note_made(pid)
                    res["changes"][pid] = {"was": was, "event_uid": None, "event_sig": None, "event_cal": None}
                    res["did"].append(_left_words(dict(a, made=False)))
                else:
                    _note_made(pid, uid, a["cal"], when_sig(a["cal"], a["date"], a["time"], a["title"]))
                    res["changes"][pid] = {"was": was, "event_uid": uid, "event_sig": a["sig"], "event_cal": a["cal"]}
                    res["did"].append(_did_words("move", a, files, backend))
            else:
                uid = backend.set(pid, a["cal"], a["uid"], a["date"], a["time"], a["title"], a["notes"])
                _note_made(pid, uid, a["cal"], when_sig(a["cal"], a["date"], a["time"], a["title"]))
                res["changes"][pid] = {"was": was, "event_uid": uid, "event_sig": a["sig"], "event_cal": a["cal"]}
                res["did"].append(_did_words(a["do"], a, files, backend))
        except Exception as e:  # noqa: BLE001  (a calendar problem never stops the caller)
            _stopped(res, e)
            break
    res["changed"] = bool(res["changes"])
    try:
        if getattr(backend, "opens_files", False):
            res["to_open"] = backend.waiting()
    except Exception:  # noqa: BLE001
        pass
    return res


def _left_words(a):
    """The plain line for a post nothing was done for, and why."""
    if a.get("why") == "date":
        return (f"({a['name']}: its posting date can't be read, so its reminder is left as it is.)" if a.get("made")
                else f"({a['name']}: its posting date can't be read, so no reminder is made for it.)")
    why = WHY.get(a.get("why"), WHY["kit"])
    if a.get("made"):
        return f"({a['name']}: {why}, so its reminder is left as it is.)"
    return f"({a['name']}: no reminder made yet, because {why}. {BACK.get(a.get('why'), BACK['kit'])})"


def _did_words(do, a, files, backend=None):
    """The plain line for what was done. On a PC (files) nothing is on their calendar yet: a file is ready to be
    added, and the line says only that."""
    if do == "remove":
        if not files:
            return f"Reminder removed: {a['name']}."
        try:
            cancel = any(w.get("id") == a["id"] and w.get("cancel") for w in backend.waiting())
        except Exception:  # noqa: BLE001
            cancel = False
        return f"Reminder turned off: {a['name']}." + (" A calendar file is ready that takes it off your calendar." if cancel else "")
    when = when_words(a["date"], a["time"])
    if do == "move":
        tail = f" ({WHY.get(a.get('why'), WHY['kit']).capitalize()}, so the caption inside is as it was.)"
        return (f"Reminder moved, ready to add to your calendar again: {a['name']}, {when}." if files
                else f"Reminder moved: {a['name']}, {when}.") + tail
    if files:
        return (f"Reminder ready to add to your calendar: {a['name']}, {when}." if do == "make"
                else f"Reminder changed, ready to add to your calendar again: {a['name']}, {when}.")
    return f"Reminder {'set' if do == 'make' else 'updated'}: {a['name']}, {when}."


def _stopped(res, e):
    words = str(e).strip() if isinstance(e, CalendarProblem) else (f"{type(e).__name__}: {e}" if str(e).strip() else type(e).__name__)
    if isinstance(e, subprocess.TimeoutExpired):
        words = "Calendar took too long to answer."
    res["problem"] = words[:200]
    res["note"] = f"(reminders not updated: {res['problem']})"
    res["changed"] = bool(res["changes"])
    return res


def merge(p, changes):
    """Put a sync's field changes into a FRESHLY LOADED queue (the caller holds its lock and saves if the first
    answer is True). Only event_uid, event_sig and event_cal are ever written, and only on a piece whose
    event_uid is still what the sync saw: anything newer in the queue is left exactly as it is.
    Returns (changed, strays): strays are events the sync made that the queue no longer has a place for (the
    post was taken out, or another sync got there first): [{"id", "uid", "cal"}], for forget()."""
    changed, strays = False, []
    pieces = {x.get("id"): x for x in p.get("pieces") or [] if isinstance(x, dict)}
    for pid, c in (changes or {}).items():
        x = pieces.get(pid)
        if x is None or x.get("event_uid") != c.get("was"):
            if c.get("event_uid") and (x is None or x.get("event_uid") != c["event_uid"]):
                strays.append({"id": pid, "uid": c["event_uid"], "cal": c.get("event_cal")})
            continue
        for k in FIELDS:
            if c.get(k) is None:
                if k in x:
                    del x[k]
                    changed = True
            elif x.get(k) != c[k]:
                x[k] = c[k]
                changed = True
    return changed, strays


def forget(strays, backend=None):
    """Take away events a sync made that the queue has no place for (merge's strays): only ever by the uid
    this file was handed back by the calendar. Never raises; the words of a problem, or None."""
    backend = backend or default_backend()
    for s in strays or []:
        try:
            if backend is not None:
                backend.remove(s["id"], s.get("cal") or "", s["uid"])
            if (_made().get(s["id"]) or {}).get("uid") == s["uid"]:
                _note_made(s["id"])
        except Exception as e:  # noqa: BLE001
            return str(e)[:200] or type(e).__name__
    return None


@contextlib.contextmanager
def _one_at_a_time():
    """One sync at a time, in this program (a lock) and across programs (a lock file in the reminders folder).
    Yields False when another one is at work: the caller does nothing, since that one is doing it."""
    if not _ONE_SYNC.acquire(False):
        yield False
        return
    f = None
    try:
        try:
            notes_dir().mkdir(parents=True, exist_ok=True)
            f = open(notes_dir() / "sync.lock", "ab")
        except OSError:
            f = None
        if f is not None and this_computer.try_lock(f) is False:
            yield False
            return
        yield True
    finally:
        if f is not None:
            this_computer.unlock(f)
            f.close()
        _ONE_SYNC.release()


def run(load, save, lock=None, backend=None, force=False, words=None):
    """The whole round, for a background thread or a command: read the queue under the caller's lock, let go,
    talk to the calendar, then load the queue again under the lock, merge the few fields and save only if
    something changed. load() and save(p) are the queue's own (posting_queue.load, posting_queue.save); lock is
    the queue's lock (anything usable with `with`), or None. Never raises. Returns sync's result, with
    "busy": True (and nothing done) when another sync is already at work."""
    lock = lock or contextlib.nullcontext()
    with _one_at_a_time() as mine:
        if not mine:
            return {"changed": False, "changes": {}, "did": [], "problem": None, "note": None, "to_open": [], "busy": True}
        try:
            with lock:
                snap = snapshot(load())
        except (Exception, SystemExit) as e:  # noqa: BLE001  (posting_queue.load stops the program on a file it can't read)
            return _stopped({"changed": False, "changes": {}, "did": [], "problem": None, "note": None, "to_open": []}, e)
        res = sync(snap, backend, force=force, words=words)
        if res["changes"]:
            strays = []
            try:
                with lock:
                    fresh = load()
                    changed, strays = merge(fresh, res["changes"])
                    if changed:
                        save(fresh)
            except (Exception, SystemExit) as e:  # noqa: BLE001
                _stopped(res, e)          # the events are in made.json, so the next run picks them up, not twice
            if strays:
                forget(strays, backend if backend is not None else default_backend())
        return res


def open_waiting(backend=None):
    """A PC: open the calendar files that changed since they were last opened, in their calendar app.
    {"opened": [...], "problem": words or None}. A Mac has nothing to open."""
    backend = backend or default_backend()
    if backend is None or not getattr(backend, "opens_files", False):
        return {"opened": [], "problem": None}
    return backend.open_waiting()


def status_lines(p, backend=None):
    """Every post's reminder, in plain words (for the chat)."""
    backend = backend if backend is not None else default_backend()
    cfg = p.get("remind") if isinstance(p.get("remind"), dict) else {}
    need = getattr(backend, "needs_calendar", True)
    lines = []
    if need:
        lines.append(f"Reminders go on the {cfg['calendar']} calendar." if cfg.get("calendar") else "No calendar chosen for reminders yet.")
    else:
        lines.append("On this computer a reminder is a calendar file to open in your calendar app.")
    handed = set()
    if not need:
        try:
            handed = set(backend.handed())
        except Exception:  # noqa: BLE001
            pass
    on = [x for x in p.get("pieces") or [] if x.get("remind_on")]
    if not on:
        lines.append("No post has a reminder.")
    for x in on:
        t = _time_of(x, cfg)
        name = piece_words(x)
        if x.get("status") == "posted":
            lines.append(f"{name}: posted.")
        elif x.get("status") != "green" or not x.get("date"):
            lines.append(f"{name}: reminder at {time_words(t)}, waiting until it's ready to post and has a date.")
        elif need and not cfg.get("calendar"):
            lines.append(f"{name}: {when_words(x['date'], t)}, waiting for a calendar to be chosen.")
        elif not real_day(x["date"]):
            lines.append(f"{name}: its posting date can't be read, so it has no reminder.")
        elif x.get("event_uid") and need:
            lines.append(f"{name}: {when_words(x['date'], t)}, on the {x.get('event_cal')} calendar.")
        elif x.get("event_uid"):
            lines.append(f"{name}: {when_words(x['date'], t)}, " + ("opened in your calendar app." if x.get("id") in handed
                                                                    else "waiting to be added to your calendar."))
        else:
            lines.append(f"{name}: {when_words(x['date'], t)}, not on the calendar yet.")
    return lines


# ---------------------------------------------------------------- the command line

def main(argv=None):
    this_computer.utf8_output()
    ap = argparse.ArgumentParser(description="Posting-day reminders on their calendar.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("status")
    sub.add_parser("calendars")
    s = sub.add_parser("sync")
    s.add_argument("--all", action="store_true", help="send every reminder again, changed or not")
    sub.add_parser("open")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 2
    backend = default_backend()
    if a.cmd == "calendars":
        if backend is None or not getattr(backend, "needs_calendar", True):
            say("There are no calendars to choose from on this computer: a reminder is a calendar file, and your calendar app asks which calendar when it opens.")
            return 0
        try:
            names = calendars(backend)
        except CalendarProblem as e:
            say(f"(calendars not read: {e})")
            return 1
        say("\n".join(names) if names else "No calendar a reminder could go on was found.")
        return 0
    if a.cmd == "open":
        got = open_waiting(backend)
        for w in got["opened"]:
            say(f"Opened: {w['title']}" + (" (turned off)" if w["cancel"] else ""))
        if got["problem"]:
            say(f"(not opened: {got['problem']})")
            return 1
        if not got["opened"]:
            say("Nothing is waiting to be opened.")
        return 0
    import posting_queue as queue      # here, not at the top: only the commands that read the queue need it
    if a.cmd == "status":
        for line in status_lines(queue.load(), backend):
            say(line)
        return 0
    res = run(queue.load, queue.save, queue._POSTING_LOCK, backend, force=a.all)
    if res.get("busy"):
        say("Another reminders check is running right now. Nothing else was done.")
        return 0
    for line in res["did"]:
        say(line)
    if res["note"]:
        say(res["note"])
        return 1
    files = bool(getattr(backend, "opens_files", False))
    if not res["did"]:
        say("No reminder has changed since last time." if files else "Every reminder is already in step. Nothing was sent to the calendar.")
    if res["to_open"]:
        k = len(res["to_open"])
        say(f"{k} calendar file{' is' if k == 1 else 's are'} waiting to be opened in your calendar app. Nothing is on your calendar until then.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
