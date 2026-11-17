#!/usr/bin/env python3
"""Posted, on the post itself (Nicole's v27 section 8, stage 3 of Lane D): the Not posted / Posted switch beside
Done in a post's panel, a post marked Posted shown in the grid at once as an ordinary feed post with no date,
and "unposted" (the switch back, and the chat's command) putting it back in line. Checked in this program, by
request, from the command line, and on the real page in a HIDDEN Chrome.

    python3 tests/posting_posted_check.py [--port 8840] [--work <a folder to keep the run in>] [--no-chrome]

What it does, on a pretend Assistant with a pretend kit it makes itself in a throwaway folder (a few tiny
pictures; nothing of a client's, nothing of the real ~/.studio, no drive, no calendar: REMINDERS_BACKEND=file):
  * state()["posted"], in this program: the posted pieces shown are those posted since the grid was last read,
    or in the last 30 days when it never was; newest first; a posted piece with no posted_at, or one whose
    posted_at is not a string, is left out and never crashes the page; each carries posted_at and its reel's name;
  * her words both ways: every line of hers on the page, and (with her pack beside the project) only lines her
    diff has;
  * the routes: POST /posting {action: "posted"} then {action: "unposted"}: green again, posted_at gone, the
    last slot, a new date (not the one that had passed), green_at set; the refusals (another Origin, another
    website's page, a body too big, no such post, a piece that is neither posted nor ready); a second press is
    harmless;
  * the command line: `unposted "<piece>"` on a posted reel found by its reel's name, its line, and the shoot's
    name alone stopping when two of its reels are posted;
  * the page itself (when there is a Chrome): the switch beside Done on an upcoming post (role=switch, aria-checked
    said plainly, the row of buttons and the photos still there); flipping it moves the tile after the upcoming
    ones with no date and the small Reel mark, her toast, the panel staying open as the posted post's (her line,
    the switch and Done only, nothing fetched); clicking the feed tile opens it; flipping back puts the tile in
    line with its new date and her other toast; Enter on the tile opens it; the row's Posted button's new toast;
    two posted posts newest first; a second reel's post saying "· <reel name>"; a phone's width; a clean page.

The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only, a Mac or a PC.
"""
import argparse

import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import words_page_check as wpc  # noqa: E402  (its pretend Assistant: kits, the page server, words.py from the chat)
import posting_panel_check as ppc  # noqa: E402  (the panel's own helpers)

KIT, SHORT, HOOKS, SCRIPTS = wpc.KIT, wpc.SHORT, wpc.HOOKS, wpc.SCRIPTS
SOURCE = (SCRIPTS / "posting_queue.py").read_text(encoding="utf-8")
CAPTION = "MINI SESSIONS are coming to Laguna Beach on December 4th!!!"
SECOND = "White Backdrop"

# her words, as v27 has them (UPDATE-v27.md section 8 and plugin-changes/posting_queue-since-v26.diff)
NOT_POSTED = "Not posted"
POSTED = "Posted"
IN_FEED = "It’s in your feed. If it didn’t actually go out, switch it back to Not posted and it goes back in your queue."
TIP = "Click if this one didn’t go out after all"
T_BACK = "Back in your queue, ready to post."
T_POSTED = "Posted. Nice. It’s in your feed now."
HERS = (NOT_POSTED, POSTED, IN_FEED, TIP, T_BACK, T_POSTED)


def skip(line):
    print("SKIP  " + line, flush=True)


def her_diff():
    """Her v27 diff of posting_queue.py (plugin-changes/posting_queue-since-v26.diff), when her pack sits beside
    the project or beside the main checkout (reference-private is not in git), or None."""
    for base in (HERE.parent, Path("/Users/dustindamron/Projects/hf-tools")):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v27-*"), reverse=True):
            f = h / "Carousel designer and reel picker" / "plugin-changes" / "posting_queue-since-v26.diff"
            if f.is_file():
                return f.read_text(encoding="utf-8")
    return None


def posted_ids(s):
    return [x["id"] for x in ppc.page_state(s).get("posted", [])]


def piece(s, pid):
    return ppc.piece(s, pid)


def press(s, body, headers=None):
    return s.http("POST", "/posting", body, headers)


# ---------- 1. state()["posted"], in this program ----------

def check_state(s, pq):
    t = date.fromisoformat(wpc.TODAY)
    def at(days_ago, hour="10"):
        return (t - timedelta(days=days_ago)).isoformat() + "T%s:00:00" % hour
    def mk(i, status="posted", **more):
        return dict({"id": "s-%d-reel" % i, "shoot_id": "s-%d" % i, "shoot_name": "Shoot %d" % i, "kind": "reel", "status": status,
                     "thumb": None, "added": "2026-11-01T10:00:00"}, **more)
    p = {"pieces": [mk(1, posted_at=at(3)), mk(2, posted_at=at(31)), mk(3, posted_at=at(29)), mk(4), mk(5, posted_at=5),
                    mk(6, posted_at=at(0, "09"), reel_name=SECOND), mk(7, "green", slot=1), mk(8, posted_at=["x"])],
         "interval": 3.0, "reminded": {}}
    feed = s.studio / "feed.json"
    if feed.exists():
        feed.unlink()
    st = pq.state(p)
    ids = [x["id"] for x in st.get("posted", [])]
    case("the grid never read: the posts marked Posted in the last 30 days are shown, newest first (31 days ago is not)",
         ids == ["s-6-reel", "s-1-reel", "s-3-reel"], ids)
    case("a posted piece with no posted_at (older than Oct 28) is left out, and one whose posted_at is not a string (a number, a list) too, with no crash",
         "s-4-reel" not in ids and "s-5-reel" not in ids and "s-8-reel" not in ids)
    case("the upcoming post is still an upcoming post, not a posted one", [x["id"] for x in st["greens"]] == ["s-7-reel"] and "s-7-reel" not in ids)
    one = next(x for x in st["posted"] if x["id"] == "s-6-reel")
    case("each posted entry carries its posted_at, its status and the reel's name (text only), like an upcoming one's entry",
         one["posted_at"] == at(0, "09") and one["status"] == "posted" and one["reel_name"] == SECOND and set(st["greens"][0]) <= set(one), one)
    feed.write_text(json.dumps({"handle": "h", "read_at": at(2, "12"), "posts": []}), encoding="utf-8")
    ids = [x["id"] for x in pq.state(p).get("posted", [])]
    case("once the grid was read: only the posts marked Posted since that reading (3 days ago is not; this morning is)", ids == ["s-6-reel"], ids)
    feed.write_text(json.dumps({"handle": "h", "read_at": at(0, "11"), "posts": []}), encoding="utf-8")
    case("...read after the last one: none", pq.state(p).get("posted") == [])
    feed.write_text(json.dumps({"handle": "h", "read_at": 7, "posts": []}), encoding="utf-8")
    ids = [x["id"] for x in pq.state(p).get("posted", [])]
    case("a read_at that is not a string counts as never read", ids == ["s-6-reel", "s-1-reel", "s-3-reel"], ids)
    feed.unlink()
    case("schedule() with a posted_at that is not a date never crashes, and still dates the upcoming post", bool(st["greens"][0].get("date")))

    # unpost, in this program
    x = p["pieces"][0]
    x["date"], x["remind_on"], x["event_uid"], x["event_cal"] = "2026-11-01", True, "uid-1", "Home"
    pq.unpost(p, x, by="page")
    case("unpost: ready to post again, posted_at gone, the date that had passed gone and a new one given, the last slot, green_at set, changed by the page",
         x["status"] == "green" and "posted_at" not in x and x.get("date") and x["date"] > wpc.TODAY and x["date"] != "2026-11-01" and x["slot"] == 2
         and x.get("green_at") and x["changed_by"] == "page", x)
    case("...its reminder is left as it was, and the event it had is still its own (so the round updates it, never makes a second)",
         x["remind_on"] is True and x["event_uid"] == "uid-1" and x["event_cal"] == "Home")
    before = json.dumps(x, sort_keys=True)
    pq.unpost(p, x, by="page")
    case("a second unpost of a piece already in line changes nothing (a second press is harmless)", json.dumps(x, sort_keys=True) == before)
    for st_ in ("yellow", "red", "skipped"):
        y = mk(9, st_)
        try:
            pq.unpost(p, y)
            got = "took it"
        except ValueError as e:
            got = str(e)
        case("unpost of a piece that is %s is refused in plain words, nothing changed" % st_, got == "not a posted post" and y["status"] == st_, got)


# ---------- 2. her words, both ways ----------

def check_words():
    missing = [w for w in HERS if w not in SOURCE]
    case("every line of hers on the page: the switch's two words, her line in the posted post's panel, the tile's tooltip, the two toasts", not missing, missing)
    diff = her_diff()
    if diff is None:
        skip("her v27 diff is not beside the project: her lines are not compared the other way")
        return
    not_hers = [w for w in HERS if w not in diff]
    case("...and none of them is ours: each is in her v27 diff, word for word", not not_hers, not_hers)
    case("her state() rule is ours: posted since the grid was read, else the last 30 days", "timedelta(days=30)" in diff and "POSTED_DAYS = 30" in SOURCE)
    case("the action is hers by name: unposted", '"unposted"' in diff and 'act == "unposted"' in SOURCE)
    case("her second filter on the page (by read_at again) is not copied: the page draws S.posted as the server hands it",
         "x.posted_at>S.feed.read_at" in diff and "posted_at>S.feed" not in SOURCE and "(S.posted||[]).forEach" in SOURCE)
    case("her innerHTML switch is not copied: ours is built as text, aria-checked said as 'true'/'false'",
         "aria-checked=\"${done}\"" in diff and "setAttribute('aria-checked',on?'true':'false')" in SOURCE and "pswitch" in SOURCE and ".pswitch" in SOURCE)
    case("her mouse-only posted tile has a keyboard and a focus ring here", ".tile.justposted:focus-visible" in SOURCE and "e.key==='Enter'||e.key===' '" in SOURCE
         and "justposted:focus-visible" not in diff)
    case("the page's colours are the look's names (her diff's var(--line), var(--green), var(--ink-2)), no hex of ours beyond her two greys",
         all(v in SOURCE for v in (".pswitch.on i{background:var(--green)}", "border:1px solid var(--line)", "color:var(--ink-2)"))
         and "#F1F0F4" in diff and "#C9C7D1" in diff)


# ---------- 3. the routes, and the command line ----------

def fresh_queue(s):
    """The kit's reel and carousel both ready to post, a rhythm set; the page server running."""
    s.stop()
    for f in (s.studio / "posting.json", s.studio / "posting-url.txt", s.studio / "feed.json"):
        if f.exists():
            f.unlink()
    s.start()
    s.http("POST", "/words-rhythm", {"text": "3 a week"})
    for p in ("reel", "carousel"):
        code = s.http("POST", "/words-queue", {"kit": KIT, "piece": p})[0]
        if code != 200:
            raise RuntimeError("the %s could not be added to the queue (%s)" % (p, code))
    g = {x["role"]: x for x in ppc.page_state(s).get("greens", [])}
    return g["reel"], g["carousel"]


def check_routes(s):
    reel, car = fresh_queue(s)
    rid, cid = reel["id"], car["id"]
    d_reel, d_car = reel["date"], car["date"]
    case("to start: the reel first in line, down for %s, the carousel after it" % d_reel, reel["slot"] == 1 and car["slot"] == 2 and d_reel < d_car, (reel, car))
    code, j, _ = press(s, {"action": "posted", "id": rid})
    x = piece(s, rid)
    case("Posted (the switch, or the row's button): the piece leaves the line, posted_at set, its slot gone, the carousel now first",
         code == 200 and x["status"] == "posted" and isinstance(x.get("posted_at"), str) and "slot" not in x and j["greens"][0]["id"] == cid and j["greens"][0]["slot"] == 1, (code, x))
    case("...the answer's posted list has it, with its posted_at, and the page it writes shows it so", [y["id"] for y in j["posted"]] == [rid] and j["posted"][0]["posted_at"] == x["posted_at"]
         and posted_ids(s) == [rid])
    own = "http://127.0.0.1:%d" % s.port
    refused = [
        ("another Origin", press(s, {"action": "unposted", "id": rid}, {"Origin": "http://evil.example"})[0], 403),
        ("another website's page", press(s, {"action": "unposted", "id": rid}, {"Origin": own, "Sec-Fetch-Site": "cross-site"})[0], 403),
        ("a body too big", press(s, b"{" + b" " * 70000 + b"}", {"Origin": own})[0], 413),
        ("no such post", press(s, {"action": "unposted", "id": "kit:nobody-reel"})[0], 400),
        ("not a press", press(s, {"action": "unposted", "id": 7})[0], 400),
    ]
    bad = [(w, c, want) for w, c, want in refused if c != want]
    case("unposted is refused like every press: another Origin, another website, a body too big (413), no such post and a bad id (400, never a crash)", not bad, bad)
    case("...and nothing changed by the refusals", piece(s, rid)["status"] == "posted")
    time.sleep(1.1)        # so the new green_at is a different second
    code, j, _ = press(s, {"action": "unposted", "id": rid})
    x = piece(s, rid)
    case("unposted: ready to post again, posted_at gone, at the END of the line with a new date after the carousel's, green_at set, by the page",
         code == 200 and x["status"] == "green" and "posted_at" not in x and x["slot"] == 2 and x.get("date") and x["date"] > d_car and x.get("green_at") and x["changed_by"] == "page", (code, x))
    case("...the answer: no posted list entry, two upcoming posts, the reel last", j["posted"] == [] and [y["id"] for y in j["greens"]] == [cid, rid] and posted_ids(s) == [])
    code, j, _ = press(s, {"action": "unposted", "id": rid})
    case("unposted again on a post already in line: answered, and nothing changed (a double click is harmless)", code == 200 and piece(s, rid) == x)
    press(s, {"action": "unready", "id": cid})
    code, _, _ = press(s, {"action": "unposted", "id": cid})
    case("unposted on a post that is still finishing (yellow) is refused (400) and leaves it", code == 400 and piece(s, cid)["status"] == "yellow")
    press(s, {"action": "ready", "id": cid})
    return rid, cid


def check_commands(s, rid, cid):
    base = rid
    code, out = s.cmd("posting_queue.py", "posted", "boys reel")
    case("posted \"boys reel\" from the chat, as before", code == 0 and piece(s, rid)["status"] == "posted", out[-200:])
    code, out = s.cmd("posting_queue.py", "unposted", "boys reel")
    x = piece(s, rid)
    case("unposted \"boys reel\": back in line at the end with a new date, and the line says so",
         code == 0 and x["status"] == "green" and "posted_at" not in x and x["slot"] == 2
         and out.startswith("%s reel: back in your queue, ready to post, down for " % SHORT) and "2 pieces ready" in out, (code, out[-240:]))
    code, out = s.cmd("posting_queue.py", "unposted", "boys reel")
    case("unposted with nothing posted stops in plain words", code != 0 and "STOP: nothing in the posting queue matches" in out, out[-200:])
    # a second reel of the shoot (v25's -reel-v2 piece), posted: found by its reel's name
    p = s.posting()
    second = dict(next(y for y in p["pieces"] if y["id"] == rid), id=base + "-v2", status="posted", posted_at="2026-11-10T10:00:00", reel_name=SECOND)
    second.pop("slot", None); second.pop("date", None)
    p["pieces"].append(second)
    s.write_posting(p)
    code, out = s.cmd("posting_queue.py", "posted", "boys reel")
    case("posted \"boys reel\" with the shoot's second reel in the queue too stops and names both (as v25 has it)", code != 0 and "could mean more than one" in out, out[-240:])
    s.cmd("posting_queue.py", "posted", rid)                  # the first reel posted too, by its id
    code, out = s.cmd("posting_queue.py", "unposted", "boys reel")
    case("\"boys reel\" alone, with two of the shoot's reels posted, stops and names both", code != 0 and "could mean more than one" in out and SECOND in out, out[-240:])
    code, out = s.cmd("posting_queue.py", "unposted", "boys reel white backdrop")
    x = piece(s, base + "-v2")
    case("the second reel found by its name: back in line, the first reel left posted",
         code == 0 and x["status"] == "green" and "posted_at" not in x and piece(s, rid)["status"] == "posted" and out.startswith("%s reel (%s): back in your queue" % (SHORT, SECOND)), (code, out[-240:]))
    p = s.posting()
    p["pieces"] = [y for y in p["pieces"] if y["id"] != base + "-v2"]
    s.write_posting(p)
    s.cmd("posting_queue.py", "unposted", "boys reel")


# ---------- 4. the page ----------

PANEL = ppc.PANEL
OPEN_ID = ppc.OPEN_ID
SWITCH = "(function(){ var b = document.querySelector('#pick .pswitch'); return b ? [b.getAttribute('role'), b.getAttribute('aria-checked'), b.textContent, b.classList.contains('on')] : null; })()"
KIDS = "Array.from(%s.children).map(function(e){ return e.className; }).join(' ')" % PANEL
PHR = "Array.from(document.querySelectorAll('#pick .phr > *')).map(function(e){ return e.tagName + ':' + e.className.split(' ')[0]; })"
GRID = ("Array.from(document.querySelectorAll('#grid > .tile')).map(function(t){ return (t.classList.contains('mine') ? 'mine' : t.classList.contains('justposted') ? 'posted' : t.classList.contains('ghost') ? 'ghost' : 'real')"
        " + (t.dataset.id ? ':' + t.dataset.id : '') + (t.querySelector('.d') ? ' d=' + t.querySelector('.d').textContent : '') + (t.querySelector('.rk') ? ' rk=' + t.querySelector('.rk').getAttribute('aria-label') : ''); })")
WATCH = ("window.__got = []; (function(){ var f = window.fetch; window.fetch = function(u, o){ window.__got.push(String(u)); return f.apply(this, arguments); }; })()")


def ptile(pid):
    return "#grid .tile.justposted[data-id=%s]" % json.dumps(pid)


def nice(iso):
    d = date.fromisoformat(iso)
    return "%s, %s %d" % (d.strftime("%a"), d.strftime("%b"), d.day)


def check_page(c, s, ids):
    rid, cid = ids
    reel, car = fresh_queue(s)
    rid, cid = reel["id"], car["id"]
    c.open(s.url("/posting.html"))
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    c.js(WATCH)
    grid = c.js(GRID)
    case("to start: the two upcoming posts (the carousel top-left, the reel next up with its date), no posted one",
         grid[0] == "mine:%s d=%s" % (cid, nice(car["date"])) and grid[1] == "mine:%s d=Next up · %s" % (rid, nice(reel["date"]))
         and not any(g.startswith("posted") for g in grid), grid)

    # the switch on an upcoming post's panel
    ppc.open_panel(c, rid)
    case("an upcoming post's panel: a grey switch beside Done, role=switch, aria-checked 'false', reading 'Not posted'",
         c.js(SWITCH) == ["switch", "false", NOT_POSTED, False] and c.js(PHR) == ["BUTTON:pswitch", "BUTTON:x"], (c.js(SWITCH), c.js(PHR)))
    case("...the rest of the panel is as it was: the header, the row of buttons, the reminder's place, the photos, the warning's place",
         c.js(KIDS) == "ph pw pr pn ps warn" and c.text("#pick .ph p") == ppc.REEL_LINE and c.count("#pick .ps .c") > 0, c.js(KIDS))
    look = c.js("(function(){ var b = document.querySelector('#pick .pswitch'), k = b.querySelector('i'), s = getComputedStyle(b), r = b.getBoundingClientRect(), d = document.querySelector('#pick .x').getBoundingClientRect();"
                " return {grey: s.backgroundColor, knob: getComputedStyle(k).backgroundColor, round: s.borderRadius, left_of_done: r.right <= d.left, same_row: Math.abs((r.top + r.height / 2) - (d.top + d.height / 2)) < 4}; })()")
    case("...hers: a grey pill with a grey knob, round, on the same row as Done and to its left",
         look["grey"] == "rgb(241, 240, 244)" and look["knob"] == "rgb(201, 199, 209)" and look["round"] == "999px" and look["left_of_done"] and look["same_row"], look)

    # flip it: Posted
    c.click("#pick .pswitch")
    toast = ppc.wait_toast(c, T_POSTED)
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 1", 10)
    grid = c.js(GRID)
    case("Posted: her toast, the tile leaves the upcoming ones and sits after them as a feed post with NO date and a small Reel mark",
         toast is True and grid[0].startswith("mine:" + cid) and grid[1] == "posted:%s rk=Reel" % rid, (toast, grid))
    case("...its tooltip is hers, it is dimmed like a real post, and it is not an upcoming tile (never dragged)",
         c.js("document.querySelector(%s).title" % json.dumps(ptile(rid))) == TIP
         and c.js("getComputedStyle(document.querySelector(%s + ' img')).filter" % json.dumps(ptile(rid))) == "saturate(0.85)"
         and c.count(".tile.mine[data-id=%s]" % json.dumps(rid)) == 0, c.js("document.querySelector(%s).title" % json.dumps(ptile(rid))))
    case("...the panel stays open as the posted post's: 'Your <shoot> reel', her line, the switch on and reading 'Posted', Done, and nothing else",
         c.js(OPEN_ID) == rid and c.text("#pick .ph b") == "Your %s reel" % SHORT and c.text("#pick .ph p") == IN_FEED
         and c.js(SWITCH) == ["switch", "true", POSTED, True] and c.js(KIDS) == "ph" and c.js(PHR) == ["BUTTON:pswitch", "BUTTON:x"], (c.text("#pick .ph p"), c.js(SWITCH), c.js(KIDS)))
    case("...the switch turned green", c.js("getComputedStyle(document.querySelector('#pick .pswitch i')).backgroundColor") == "rgb(79, 178, 134)")
    w = c.js(ppc.WHERE)
    case("...under the posted tile's row, that tile outlined", w["before"] == 2 and w["picking"] == [rid], w)
    case("...the queue: the reel posted, the carousel alone in line and next up", piece(s, rid)["status"] == "posted" and "Next up" in grid[0] and c.count("#greens .row") == 1)
    c.click("#pick .x")
    case("Done closes it", c.js("%s.hidden" % PANEL) is True and c.count(".tile.picking") == 0)

    # the feed tile opens the posted post's panel, with nothing fetched
    n = len([u for u in c.js("window.__got") if u.startswith("/posting/panel")])
    c.click(ptile(rid))
    c.wait_for("%s === %s" % (OPEN_ID, json.dumps(rid)), 5)
    case("clicking the feed tile: the posted post's panel, her line and the switch only, and nothing was asked of the server for it",
         c.text("#pick .ph p") == IN_FEED and c.js(SWITCH) == ["switch", "true", POSTED, True] and c.js(KIDS) == "ph"
         and len([u for u in c.js("window.__got") if u.startswith("/posting/panel")]) == n, c.js("window.__got"))
    c.click(ptile(rid))
    c.wait_for("%s === ''" % OPEN_ID, 5)
    case("clicking it again closes it", c.js("%s.hidden" % PANEL) is True)

    # flip it back: Not posted
    c.click(ptile(rid))
    c.wait_for("%s === %s" % (OPEN_ID, json.dumps(rid)), 5)
    c.click("#pick .pswitch")
    toast = ppc.wait_toast(c, T_BACK)
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    x = piece(s, rid)
    grid = c.js(GRID)
    case("switched back: her toast, back in line at the END (so top-left, newest first) with its NEW date, the posted tile gone",
         toast is True and x["status"] == "green" and x["slot"] == 2 and x["date"] > car["date"] and grid[0] == "mine:%s d=%s" % (rid, nice(x["date"]))
         and grid[1].startswith("mine:" + cid) and not any(g.startswith("posted") for g in grid), (toast, grid, x))
    c.wait_for("%s === %s && %s" % (OPEN_ID, json.dumps(rid), ppc.READY), 10)
    case("...its panel is the upcoming post's again: the switch off, the photos and the row of buttons back",
         c.js(SWITCH) == ["switch", "false", NOT_POSTED, False] and c.js(KIDS) == "ph pw pr pn ps warn" and c.count("#pick .ps .c") > 0, (c.js(SWITCH), c.js(KIDS)))
    c.click("#pick .x")

    # the keyboard: Enter on a posted tile
    press(s, {"action": "posted", "id": rid})
    c.reload()
    c.wait_for("document.querySelectorAll('#grid .tile.justposted').length === 1", 10)
    case("a posted tile can take the keyboard's focus (ours; hers is mouse-only)", c.js("document.querySelector(%s).tabIndex" % json.dumps(ptile(rid))) == 0)
    c.js("document.querySelector(%s).focus()" % json.dumps(ptile(rid)))
    c.key("Enter")
    c.wait_for("%s === %s" % (OPEN_ID, json.dumps(rid)), 5)
    case("Enter on it opens its panel", c.js(OPEN_ID) == rid and c.js(SWITCH) == ["switch", "true", POSTED, True])
    c.click("#pick .x")

    # the row's Posted button: her new toast, two posted posts newest first
    time.sleep(1.1)
    c.click("#greens [data-a='posted'][data-id=%s]" % json.dumps(cid))
    toast = ppc.wait_toast(c, T_POSTED)
    c.wait_for("document.querySelectorAll('#grid .tile.justposted').length === 2", 10)
    grid = c.js(GRID)
    case("the row's Posted button says her new toast, and the two posted posts sit newest first, each with its mark, no date, no upcoming tile left",
         toast is True and grid[0] == "posted:%s rk=Carousel" % cid and grid[1] == "posted:%s rk=Reel" % rid and c.count("#grid .tile.mine") == 0, (toast, grid))
    case("...the rows: nothing ready to post, and the grid's rows are still whole (ghosts fill to a row of three)",
         c.text("#greens .empty") == "Nothing ready to post yet." and c.js("document.querySelectorAll('#grid > .tile').length % 3") == 0, c.js(GRID))

    # a second reel's post says its name
    p = s.posting()
    second = dict(next(y for y in p["pieces"] if y["id"] == rid), id=rid + "-v2", status="posted", posted_at="2026-11-10T11:00:00", reel_name=SECOND)
    p["pieces"].append(second)
    s.write_posting(p)
    c.reload()
    c.wait_for("document.querySelectorAll('#grid .tile.justposted').length === 3", 10)
    c.click(ptile(rid + "-v2"))
    c.wait_for("%s === %s" % (OPEN_ID, json.dumps(rid + "-v2")), 5)
    case("a second reel's post, posted: its panel says 'Your <shoot> reel · <reel name>', the name as text",
         c.text("#pick .ph b") == "Your %s reel · %s" % (SHORT, SECOND) and c.count("#pick .ph b *") == 0, c.text("#pick .ph b"))
    c.phone()
    c.wait_for("%s === %s" % (OPEN_ID, json.dumps(rid + "-v2")), 5)
    case("at a phone's width the posted post's panel never makes the page scroll sideways", c.js("document.documentElement.scrollWidth <= window.innerWidth"),
         c.js("[document.documentElement.scrollWidth, window.innerWidth]"))
    c.desktop()
    errs = [e for e in c.page_errors() if "favicon" not in e]
    case("the page ran clean (no error), asked nothing of the internet, and nothing of theirs ran as code",
         not errs and not c.outside_requests() and c.js("window.pwned === undefined"), (errs, c.outside_requests()))
    p = s.posting()
    p["pieces"] = [y for y in p["pieces"] if y["id"] != rid + "-v2"]
    s.write_posting(p)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=8840)
    ap.add_argument("--no-chrome", action="store_true", help="the routes and the command line only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS for p in range(a.port, a.port + 10)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="posting-posted-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    s = wpc.Setup(work, a.port)
    s.env["REMINDERS_BACKEND"] = "file"       # never the real Calendar
    s.env["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    os.environ["REMINDERS_BACKEND"] = "file"
    os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    os.environ["STUDIO_TODAY"] = wpc.TODAY
    s.make()
    s.reel_made()
    s.slides_made(4)
    s.words("draft", "reel", {"caption": CAPTION, "hooks": HOOKS})
    s.words("draft", "carousel", {"caption": "A carousel caption."})
    wpc.page_module(s)
    import posting_queue as pq
    try:
        group("state()[\"posted\"] and unpost, in this program", check_state, s, pq)
        group("her words, both ways", check_words)
        ids = group("the routes", check_routes, s)
        if ids:
            group("the command line", check_commands, s, *ids)
        else:
            skip("the command line: the routes did not run to their end")
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        elif not ids:
            skip("the page in a browser: the routes did not run to their end")
        else:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                group("the page", check_page, c, s, ids)
    finally:
        s.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return wpc.summary()


if __name__ == "__main__":
    sys.exit(main())
