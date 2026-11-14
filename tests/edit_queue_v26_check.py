#!/usr/bin/env python3
"""The editing queue page after Nicole's v26 (stage A of the v26 build): the check mark is Mark as delivered,
Take out of my queue, one Find a shoot over everything, Uploaded shoots, Delivered and Archived.

    python3 tests/edit_queue_v26_check.py [--port 8990] [--work <a folder to keep the run in>] [--no-chrome]

What it does, on a pretend Assistant in a throwaway folder (a scratch STUDIO_HOME, shoots that are only names;
nothing of the real ~/.studio, no drive, no photo):
  * the lists: every shoot is in exactly one of the queue, Uploaded shoots, Delivered and Archived, and what
    each chat command (done, undo, unqueue, store, unstore, list --all, offers, reminders) does to them;
  * the page server: each new action (unqueue, store, unstore) and what it leaves in the record; requeue and undo
    clearing "stored"; every refusal a plain 400 with nothing changed (no such shoot, an id that is not text, no
    such action); a second press (a shoot already where the press would put it) answered 200 with nothing
    changed; a press that does not fit where the shoot is answered 409 with the newest lists; a press from
    another website (its Origin, a cross-site press, a wrong Host), or one too big, refused with nothing changed;
  * the review round's fixes (Nov 14): a double press never says "That did not save"; a page a step behind the
    chat redraws; Make posts from this shoot is on every delivered shoot and starts the Assistant's page server
    when it is not running (the test's own, on the test's own port, stopped at the end);
  * the words: her lines on the page, compared with her own changed file when her handoff is on this computer
    (reference-private/, never pushed), both ways; "your assistant", never "Claude"; none of her test-only bits
    (port 8799, ?home=test, sessionStorage) and none of her removed Share my queue;
  * the Make posts link: only to the Assistant's own page server, and left out when its address is not known;
  * the page itself in a HIDDEN Chrome (when there is one): the two sections start closed, the check mark and
    its toast, Take out of my queue, the search across all four sections (opening Delivered or Archived on a
    match, "No shoot by that name." only when nothing matches anywhere), Archive behind "Are you sure you want to
    archive this?", Cancel, Bring it back, and a shoot's name with <, & and a script only ever shown as text.

The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only, a Mac or a PC.
"""
import argparse
import http.client
import json
import os
import re
import shutil
import threading
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402

WINDOWS = os.name == "nt"
TODAY = "2026-11-14"
NASTY = "Tom & <img src=x onerror=\"window.__got=1\"> 'Jo'"

# her words, as v26 has them (UPDATE-v26.md section 4, her notes 11 and 13, her changed edit_queue.py)
HERS = [
    'title="Mark as delivered"',
    'aria-label="Mark ${esc(s.name)} as delivered"',
    "${s.name}: delivered, moved to Delivered below",
    "Take out of my queue",
    "${s.name} is back in your uploaded shoots",
    "placeholder='Find a shoot'",
    "Looks through every shoot: your queue, uploaded, delivered and archived.",
    "No shoot by that name.",
    "<span>Uploaded shoots</span>",
    "Every shoot you back up lands here. When one is a client gallery you need to edit and deliver, add it to your editing queue.",
    "Delivered (${d.length})",
    "Archived (${st.length})",
    "Galleries you've delivered, newest first. When you're done with one, archive it to keep this list tidy. Nothing is deleted.",
    "Shoots you've archived. Bring one back any time.",
    "Open photo folder",
    "Make posts from this shoot",
    "Put back in my editing queue",
    ">Archive</button>",
    "Are you sure you want to archive this?",
    "Yes, archive it",
    ">Cancel</button>",
    "Bring it back",
    "Nothing delivered yet. Press the check mark on a shoot once its gallery is delivered.",
    "Nothing archived.",
    "Archived. You can bring it back any time.",
    "Back in Delivered.",
    "Back in your editing queue. No due date yet.",
    "Added to your editing queue. No due date yet.",
    "Delivered ${nice(s.finished_at.slice(0,10))}",
    "This is your editing queue: the client shoots you need to edit and deliver. The soonest due date is always on top, and shoots with "
    "no due date keep the order you put them in. Press Set a due date on any shoot, or drag one up or down. When a gallery is delivered, "
    "press the check mark. Not a client shoot? Take it out of your queue and it goes back to your uploaded shoots below.",
    "<b>Nothing waiting.</b><span>Shoots land here when you add them after a backup.</span>",
    "Open the queue through your assistant to save changes",
    "Ask your assistant to “show my shoots” to open folders from here",
    "This is a saved copy. Ask your assistant to pull up your queue, then add it there.",
    "Could not add it. Tell your assistant instead.",
    "This is a saved copy. Ask your assistant to “pull up my queue” to check things off and change dates.",
]
# hers, left out of ours on purpose (her test-only bits; each with its reason in the v26 notes)
HERS_NOT_OURS = ["8799", "home=test", "sessionStorage", "home-test.html", "make-posts.html"]
# her removed Share my queue: its leftover styles are not carried
SHARE_LEFTOVERS = [".modal", "#sharecv", ".addbtn.share", ".names button", ".mbox"]


def skip(line):
    print("SKIP  " + line, flush=True)


def her_file():
    roots = [ROOT / "reference-private"]
    try:                                                   # a worktree: the main checkout's reference-private too
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"], capture_output=True, text=True, timeout=20).stdout.strip()
        if out:
            roots.append((ROOT / out).resolve().parent / "reference-private")
    except (OSError, subprocess.SubprocessError):
        pass
    for r in roots:
        for f in sorted(r.glob("nicole-handoff-v26-*/Carousel designer and reel picker/plugin-changes/changed/edit_queue.py")):
            return f
    return None


class Pretend(BaseHTTPRequestHandler):
    """A stand-in for the Assistant's own page server: /home and /make-posts answer with a line of text."""
    def do_GET(self):
        out = ("<!doctype html><title>pretend</title><p id='where'>%s</p>" % self.path).encode()
        self.send_response(200 if self.path in ("/home", "/make-posts") else 404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


def pretend_server(port):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Pretend)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def stop_listener(port):
    """Stop whatever program is listening on this port (the page server the queue server started for this test)."""
    try:
        if WINDOWS:
            out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=30).stdout
            pids = set(l.split()[-1] for l in out.splitlines() if "LISTENING" in l and (":%d " % port) in l)
            for pid in pids:
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=30)
        else:
            out = subprocess.run(["lsof", "-nP", "-iTCP:%d" % port, "-sTCP:LISTEN", "-t"], capture_output=True, text=True, timeout=30).stdout
            pids = set(out.split())
            for pid in pids:
                os.kill(int(pid), 15)
        return bool(pids)
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


class Setup:
    def __init__(self, work, port):
        self.work, self.port0, self.port = work, port, None
        self.home = work / "studio-home"
        self.home.mkdir(parents=True, exist_ok=True)
        # STUDIO_POSTING_PORT: a page server the queue server starts is this test's own, on this test's port;
        # REMINDERS_BACKEND=none: it never asks a calendar
        self.env = dict(os.environ, STUDIO_HOME=str(self.home), STUDIO_TODAY=TODAY, PYTHONIOENCODING="utf-8",
                        STUDIO_POSTING_PORT=str(port + 10), REMINDERS_BACKEND="none")
        self.started = []           # ports of page servers the queue server started (stopped at the end)
        self.proc = None

    def run(self, *args):
        r = subprocess.run([sys.executable, str(SCRIPTS / "edit_queue.py"), *args], env=self.env, capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
        return r.returncode, (r.stdout + r.stderr).strip()

    def queue(self):
        return json.loads((self.home / "queue.json").read_text(encoding="utf-8"))

    def shoot(self, name):
        return next(s for s in self.queue()["shoots"] if s["name"] == name)

    def start(self):
        f = self.home / "queue-url.txt"
        if f.exists():
            f.unlink()
        kw = {"creationflags": 0x00000200} if WINDOWS else {"start_new_session": True}
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "edit_queue.py"), "serve", "--port", str(self.port0)], env=self.env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
        chrome_drive.wait_until(lambda: f.exists() and f.read_text(encoding="utf-8").strip(), 30, every=0.1, what="the queue server's address")
        self.port = int(re.search(r":(\d+)/", f.read_text(encoding="utf-8")).group(1))
        chrome_drive.wait_until(lambda: self.http("GET", "/queue.html")[0] == 200, 30, every=0.1, what="the queue page")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
        for p in self.started:
            stop_listener(p)
        self.started = []

    def http(self, method, path, body=None, headers=None, raw=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            h = dict(headers or {})
            data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
            if data is not None:
                h.setdefault("Content-Type", "application/json")
            c.request(method, path, body=data, headers=h)
            r = c.getresponse()
            return r.status, r.read()
        finally:
            c.close()

    def http_at(self, port, path):
        try:
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
            c.request("GET", path)
            return c.getresponse().status
        except OSError:
            return 0

    def post(self, body, **kw):
        code, raw = self.http("POST", "/queue", body, **kw)
        try:
            return code, json.loads(raw.decode("utf-8"))
        except ValueError:
            return code, raw.decode("utf-8", "replace")

    def url(self):
        return "http://127.0.0.1:%d/queue.html" % self.port


def names(rows):
    return [s["name"] for s in rows]


def where(state, name):
    return [k for k in ("waiting", "archive", "delivered", "stored") if name in names(state[k])]


def check_lists(s):
    """The chat's commands, and the four lists."""
    for n, due in (("Garcia wedding", "2026-11-20"), ("Patio session", "2026-11-16"), ("Beach day", None), ("Lee family", None), (NASTY, None)):
        code, out = s.run("add-manual", "--name", n, *(["--due", due] if due else []))
        if code:
            case("add-manual " + n, False, out)
    sys.path.insert(0, str(SCRIPTS))
    os.environ["STUDIO_HOME"], os.environ["STUDIO_TODAY"] = str(s.home), TODAY
    import edit_queue as eq
    case("the test's own Assistant, not the real one", Path(eq.HOME) == s.home)
    code, out = s.run("done", "patio")
    case("done: \"Delivered: Patio session.\"", code == 0 and out.startswith("Delivered: Patio session."), out)
    code, out = s.run("done", "patio")
    case("done again: already delivered, nothing changed", code == 0 and "already delivered" in out, out)
    code, out = s.run("store", "beach")
    case("store refuses a shoot that is not delivered, and says where it is (never that it does not exist)",
         code != 0 and "Beach day is in the editing queue" in out and "only a delivered shoot can be archived" in out and "no shoot" not in out and "stored" not in s.shoot("Beach day"), out)
    code, out = s.run("store", "patio")
    rec = s.shoot("Patio session")
    case("store: a delivered shoot is archived, still \"finished\", with stored and stored_at",
         code == 0 and out.startswith("Archived: Patio session.") and rec["status"] == "finished" and rec.get("stored") is True and rec.get("stored_at") and rec.get("finished_at"), out)
    code, out = s.run("unqueue", "beach")
    rec = s.shoot("Beach day")
    case("unqueue: back to the uploaded shoots, no date", code == 0 and "back in your uploaded shoots" in out and rec["status"] == "archived" and not rec.get("due"), out)
    before = (s.home / "queue.json").read_bytes()
    code, out = s.run("unqueue", "beach")
    case("unqueue again: already there, said so, nothing changed", code == 0 and out == "Beach day is already in your uploaded shoots." and (s.home / "queue.json").read_bytes() == before, out)
    code, out = s.run("store", "patio")
    case("store again: already archived, said so, nothing changed (the archived time is not rewritten)", code == 0 and out == "Patio session is already archived." and (s.home / "queue.json").read_bytes() == before, out)
    code, out = s.run("unqueue", "patio")
    case("unqueue on an archived shoot: stops and says where it is", code != 0 and "Patio session is in Archived" in out and "no shoot" not in out and (s.home / "queue.json").read_bytes() == before, out)
    code, out = s.run("unstore", "garcia")
    case("unstore on a shoot in the queue: stops and says where it is", code != 0 and "Garcia wedding is in the editing queue" in out and "isn't archived" in out and (s.home / "queue.json").read_bytes() == before, out)
    code, out = s.run("due", "patio", "1w")
    case("due on a shoot that is not in the queue: says where it is, never \"no shoot matches\"", code != 0 and "Patio session isn't in the editing queue: it is in Archived" in out and "no shoot matches" not in out and (s.home / "queue.json").read_bytes() == before, out)
    code, out = s.run("where", "garcia")
    case("where: the shoot and where it is, nothing changed", code == 0 and out.startswith("Garcia wedding: in the editing queue, due") and (s.home / "queue.json").read_bytes() == before, out)
    code, out = s.run("where", "patio")
    case("where: an archived shoot", code == 0 and out == "Patio session: in Archived." and (s.home / "queue.json").read_bytes() == before, out)
    code, out = s.run("done", "beach")
    case("done on an uploaded shoot marks nothing", code == 0 and "isn't in the editing queue" in out and s.shoot("Beach day")["status"] == "archived", out)
    q = eq.load()
    st = eq.state(q)
    every = names(q["shoots"])
    case("every shoot is in exactly one list", all(len(where(st, n)) == 1 for n in every), {n: where(st, n) for n in every})
    case("the queue, Uploaded shoots, Delivered, Archived hold what they should",
         names(st["waiting"]) == ["Garcia wedding", "Lee family", NASTY] and names(st["archive"]) == ["Beach day"] and st["delivered"] == [] and names(st["stored"]) == ["Patio session"],
         {k: names(st[k]) for k in ("waiting", "archive", "delivered", "stored")})
    code, out = s.run("list", "--all")
    case("list --all names the page's sections", "Uploaded shoots (1):" in out and "Delivered (0):" in out and "Archived (1):" in out and "Your shoots" not in out and "(edited)" not in out, out)
    # offers: a shoot delivered on the page is offered once; not while it is archived; never twice
    q = eq.load()
    lee = next(x for x in q["shoots"] if x["name"] == "Lee family")
    eq.mark_delivered(lee, "page")
    eq.save(q)
    code, out = s.run("offers")
    case("offers: a shoot marked as delivered on the page", "Lee family" in out, out)
    s.run("store", "lee")
    code, out = s.run("offers", "--mark")
    case("offers: not one they have archived (and it is not marked as offered)", "Lee family" not in out and not s.shoot("Lee family").get("offered"), out)
    s.run("unstore", "lee")
    code, out = s.run("offers", "--mark")
    code2, out2 = s.run("offers", "--mark")
    case("offers: brought back, offered once, never twice", "Lee family" in out and "Lee family" not in out2, (out, out2))
    s.run("store", "lee")
    s.run("unstore", "lee")
    code, out = s.run("offers")
    case("offers: archive and bring back does not offer it again", "Lee family" not in out and s.shoot("Lee family").get("offered"), out)
    code, out = s.run("reminders")
    case("reminders: only shoots in the queue (the delivered and archived Patio session, due in 2 days, is not one)", "Patio" not in out, out)
    code, out = s.run("undo", "patio")
    rec = s.shoot("Patio session")
    case("undo from Archived: in the queue, nothing of the delivery kept", code == 0 and rec["status"] == "waiting" and not any(k in rec for k in ("stored", "stored_at", "finished_at", "finished_by")), rec)
    s.run("done", "patio")
    before = (s.home / "queue.json").read_bytes()
    code, out = s.run("unstore", "lee")
    case("unstore again: already in Delivered, said so, nothing changed", code == 0 and out == "Lee family is already in Delivered." and (s.home / "queue.json").read_bytes() == before, out)
    return eq


def check_words(eq):
    page = eq.page_html(eq.load())
    src = (SCRIPTS / "edit_queue.py").read_text(encoding="utf-8")
    missing = [w for w in HERS if w not in page]
    case("her words are on the page, whole (%d lines)" % len(HERS), not missing, missing)
    case("\"your assistant\", never \"Claude\", anywhere on the page", "Claude" not in page and "claude" not in page.lower().replace("claude-", ""), re.findall(r".{30}[Cc]laude.{30}", page)[:3])
    case("the old words are gone (Mark finished, Your shoots as a heading, finished, moved to your shoots below, the screenshot line)",
         not any(w in page for w in ('"Mark finished"', "<span>Your shoots</span>", "moved to your shoots below", "Send Claude a screenshot", ">Edited", "when you finish editing one")))
    case("none of her test-only bits in our file (port 8799, ?home=test, sessionStorage)", not any(w in src for w in HERS_NOT_OURS), [w for w in HERS_NOT_OURS if w in src])
    case("none of her removed Share my queue", not any(w in page for w in SHARE_LEFTOVERS) and "Share my queue" not in page, [w for w in SHARE_LEFTOVERS if w in page])
    case("the two sections start closed", re.search(r"<details class='fold' id='delivered'>", page) and re.search(r"<details class='fold' id='stored'>", page) and "<details open" not in page and " open>" not in page.split("<script")[0])
    order = [page.find(x) for x in ("id='list'", "class='findall'", "id='nomatch'", "<span>Uploaded shoots</span>", "id='delivered'", "id='stored'")]
    case("the order: the queue, Find a shoot, Uploaded shoots, Delivered, Archived", -1 not in order and order == sorted(order), order)
    case("one search box", page.count("id='q'") == 1 and page.count("type='search'") == 1)
    part = (SCRIPTS.parent / "parts" / "editing-queue.md").read_text(encoding="utf-8")
    case("the assistant's instructions use the page's words and know the three new commands",
         all(w in part for w in ("Mark as delivered", "Take out of my queue", "Uploaded shoots", "Delivered (n)", "Archived (n)", "Are you sure you want to archive this?",
                                 "edit_queue.py unqueue", "edit_queue.py store", "edit_queue.py unstore", "edit_queue.py where", "`#delivered`", "`#stored`"))
         and not any(w in part for w in ("tick to finish", "below the line", "Put back in the queue,")))
    kitp = (SCRIPTS.parent / "parts" / "post-kit.md").read_text(encoding="utf-8")
    step2 = kitp.split("\n2. ", 1)[1].split("\n3. ", 1)[0]
    case("\"I'm done editing\" does not mark the shoot as delivered: the two parts agree",
         "edit_queue.py where" in step2 and "Do not mark it as delivered here" in step2 and "stays in the editing queue until" in step2
         and not step2.startswith("Mark it as delivered") and "does not mark it as delivered" in part, step2[:200])
    hers = her_file()
    if not hers:
        skip("her words against her own file: her handoff (reference-private) isn't on this computer")
        return
    theirs = hers.read_text(encoding="utf-8")
    absent = [w for w in HERS if w not in theirs and w.replace("${esc(s.count_words)}", "") not in theirs]
    case("each of those lines is in her changed file, letter for letter", not absent, absent)
    # the other way: everything her page says in a toast, and every sentence of her page's own HTML, is in ours
    toasts = set(m.group(2) for m in re.finditer(r"toast\((['\"`])(.+?)\1\)", theirs))
    lost = sorted(t for t in toasts if t not in src)
    case("every toast of hers is one of ours (%d)" % len(toasts), toasts and not lost, lost)
    body = theirs[theirs.index("def page_html"):theirs.index("def write_page")]
    said = set(t.strip() for t in re.findall(r">([^<>{}\"\n]{12,})<", body))
    lost = sorted(t for t in said if t not in page and not any(w in t for w in HERS_NOT_OURS))
    case("every sentence of her page is on ours (%d)" % len(said), said and not lost, lost)
    script = theirs[theirs.index('SCRIPT = r"""'):theirs.index("def state")]
    said = set(t.strip() for t in re.findall(r">([A-Z][^<>${}`]{11,})<", script))
    lost = sorted(t for t in said if t not in src)
    case("every button and line her script draws is in ours (%d)" % len(said), said and not lost, lost)


def check_link(eq, s):
    f = s.home / "posting-url.txt"
    if f.exists():
        f.unlink()
    st = eq.state(eq.load())
    page = eq.page_html(eq.load())
    case("no posting server known: no address written into the page, no Home link", st["make_posts"] is None and "homelink' href" not in page)
    src = (SCRIPTS / "edit_queue.py").read_text(encoding="utf-8")
    case("Make posts from this shoot is drawn on every delivered shoot, address known or not", "Q.make_posts ?" not in src and "Q.make_posts || '#'" in src)
    for bad in ("javascript:alert(1)/x", "http://evil.example/posting.html", "http://127.0.0.1:8991'><script>alert(1)</script>/posting.html", "http://127.0.0.1:8799x/p"):
        f.write_text(bad, encoding="utf-8")
        page = eq.page_html(eq.load())
        case("an address that is not this computer's is never put on the page: " + bad[:40], eq.state(eq.load())["make_posts"] is None and "homelink' href" not in page and "alert(1)" not in page)
    f.write_text("http://127.0.0.1:%d/posting.html" % (s.port0 + 15), encoding="utf-8")
    st = eq.state(eq.load())
    page = eq.page_html(eq.load())
    case("Make posts from this shoot goes to /make-posts on the Assistant's own page server", st["make_posts"] == "http://127.0.0.1:%d/make-posts" % (s.port0 + 15))
    case("the Home link is still there", "<a class='homelink' href='http://127.0.0.1:%d/home'>" % (s.port0 + 15) in page)


def check_server(s):
    """Each press, by request. Before: Garcia, NASTY in the queue; Beach uploaded; Patio, Lee delivered."""
    code, st = s.post({"action": "nothing"})
    case("no such action: a plain 400", code == 400)
    before = (s.home / "queue.json").read_bytes()
    garcia, beach, patio, lee = (s.shoot(n)["id"] for n in ("Garcia wedding", "Beach day", "Patio session", "Lee family"))
    refusals = [
        ("unqueue, no such shoot", {"action": "unqueue", "id": "nobody-here"}),
        ("store, no such shoot", {"action": "store", "id": "nobody-here"}),
        ("unstore, no such shoot", {"action": "unstore", "id": "nobody-here"}),
        ("requeue, no such shoot", {"action": "requeue", "id": "nobody-here"}),
        ("done, no such shoot", {"action": "done", "id": "nobody-here"}),
        ("unqueue, no id", {"action": "unqueue"}),
        ("store, an id that is a list", {"action": "store", "id": [patio]}),
        ("unstore, an id that is a number", {"action": "unstore", "id": 7}),
        ("unqueue, an id that is an object", {"action": "unqueue", "id": {"a": 1}}),
        ("a body that is a list", ["store", patio]),
        ("add, a name that is not text", {"action": "add", "name": ["x"]}),
        ("add, a name of 5,000 letters", {"action": "add", "name": "x" * 5000}),
    ]
    # a second press: the shoot is already where the press would put it. 200, the lists, nothing changed or saved
    again = [
        ("done, a shoot that is already delivered", {"action": "done", "id": patio}, "delivered"),
        ("unstore, a shoot already in Delivered", {"action": "unstore", "id": patio}, "delivered"),
        ("unqueue, a shoot already in Uploaded shoots", {"action": "unqueue", "id": beach}, "archive"),
        ("requeue, a shoot already in the queue", {"action": "requeue", "id": garcia}, "waiting"),
        ("undo, a shoot already in the queue", {"action": "undo", "id": garcia}, "waiting"),
    ]
    for label, body, place in again:
        code, out = s.post(body)
        case("a second press is harmless (200, the lists, nothing changed): " + label,
             code == 200 and isinstance(out, dict) and where(out, s.queue()["shoots"][[x["id"] for x in s.queue()["shoots"]].index(body["id"])]["name"]) == [place]
             and (s.home / "queue.json").read_bytes() == before, (code, str(out)[:200]))
    # a press that does not fit where the shoot is (a page a step behind the chat): 409 with the newest lists
    elsewhere = [
        ("unqueue, a shoot that is delivered", {"action": "unqueue", "id": patio}),
        ("store, a shoot in the queue", {"action": "store", "id": garcia}),
        ("store, a shoot that is uploaded", {"action": "store", "id": beach}),
        ("unstore, a shoot in the queue", {"action": "unstore", "id": garcia}),
        ("done, a shoot that is uploaded", {"action": "done", "id": beach}),
        ("due, a shoot that is delivered", {"action": "due", "id": patio, "due": "2026-12-01"}),
        ("due, a shoot that is uploaded", {"action": "due", "id": beach, "due": "2026-12-01"}),
    ]
    for label, body in elsewhere:
        code, out = s.post(body)
        case("does not fit where the shoot is: 409 with the newest lists, nothing changed: " + label,
             code == 409 and isinstance(out, dict) and set(out) >= {"waiting", "archive", "delivered", "stored"} and (s.home / "queue.json").read_bytes() == before, (code, str(out)[:200]))
    for label, body in refusals:
        code, out = s.post(body)
        case("refused, a plain 400, nothing changed: " + label, code == 400 and (s.home / "queue.json").read_bytes() == before, (code, str(out)[:200]))
    code, out = s.post(None, raw=b"{not json")
    case("refused: a body that is not JSON", code == 400 and (s.home / "queue.json").read_bytes() == before, code)
    code, out = s.post({"action": "store", "id": patio}, headers={"Host": "evil.example"})
    case("refused: sent under another website's name", code == 403 and (s.home / "queue.json").read_bytes() == before, code)
    # the same-page-only rule (the posting page's): another website's press never reaches the queue
    code, out = s.post({"action": "unstore", "id": patio}, headers={"Origin": "http://evil.example", "Sec-Fetch-Site": "cross-site", "Content-Type": "text/plain"})
    case("refused (403): a press from another website (its Origin, as plain text)", code == 403 and (s.home / "queue.json").read_bytes() == before, code)
    code, out = s.post({"action": "done", "id": garcia}, headers={"Origin": "http://127.0.0.1:%d" % (s.port + 1)})
    case("refused (403): the Origin of another page on this computer", code == 403 and (s.home / "queue.json").read_bytes() == before, code)
    code, out = s.post({"action": "done", "id": garcia}, headers={"Sec-Fetch-Site": "cross-site"})
    case("refused (403): a cross-site press with no Origin", code == 403 and (s.home / "queue.json").read_bytes() == before, code)
    code, out = s.post(None, raw=json.dumps({"action": "add", "name": "Big", "pad": "x" * 70000}).encode())
    case("refused (413): a press over 64 KB", code == 413 and (s.home / "queue.json").read_bytes() == before, code)
    code, out = s.http("POST", "/queue", headers={"Content-Length": "-5", "Content-Type": "application/json"})
    case("refused: a length below nothing (it does not wait for ever)", code == 413 and (s.home / "queue.json").read_bytes() == before, code)
    code, out = s.http("GET", "/open?id=" + patio, headers={"Sec-Fetch-Site": "cross-site"})
    case("refused (403): another website asking for a folder's window", code == 403, code)
    code, out = s.http("GET", "/make-posts-url", headers={"Sec-Fetch-Site": "cross-site"})
    case("refused (403): another website asking to start the page server", code == 403, code)
    for own in ("http://127.0.0.1:%d" % s.port, "http://localhost:%d" % s.port):
        code, out = s.post({"action": "done", "id": patio}, headers={"Origin": own, "Sec-Fetch-Site": "same-origin"})
        case("the page's own press still works: Origin " + own, code == 200 and (s.home / "queue.json").read_bytes() == before, code)

    # Make posts from this shoot / Back to home: where they go, started if it is not running
    f = s.home / "posting-url.txt"
    code, raw = s.http("GET", "/make-posts-url")
    case("the page server is up (the test's pretend one): its Make posts address", code == 200 and json.loads(raw) == {"url": "http://127.0.0.1:%d/make-posts" % (s.port0 + 15)}, raw)
    code, raw = s.http("GET", "/home-url")
    case("and its home address", code == 200 and json.loads(raw) == {"url": "http://127.0.0.1:%d/home" % (s.port0 + 15)}, raw)
    case("asking changed nothing in the queue", (s.home / "queue.json").read_bytes() == before)
    f.write_text("http://127.0.0.1:%d/posting.html" % (s.port0 + 17), encoding="utf-8")      # an address nothing answers (after a restart)
    code, raw = s.http("GET", "/make-posts-url")
    got = json.loads(raw).get("url") or ""
    m = re.fullmatch(r"http://127\.0\.0\.1:(\d+)/make-posts", got)
    if m:
        s.started.append(int(m.group(1)))
    case("the page server is not running: it is started (the test's own port), and the address is the new one",
         code == 200 and m and s.port0 + 10 <= int(m.group(1)) < s.port0 + 15 and s.http_at(int(m.group(1)), "/home") == 200, raw)
    for p in s.started:
        stop_listener(p)
    f.write_text("http://127.0.0.1:%d/posting.html" % (s.port0 + 15), encoding="utf-8")

    code, st = s.post({"action": "store", "id": patio})
    rec = s.shoot("Patio session")
    case("store: Archived, out of Delivered, the record still \"finished\"", code == 200 and where(st, "Patio session") == ["stored"] and rec["status"] == "finished" and rec["stored"] is True and rec.get("stored_at"), (code, rec))
    stamp = rec.get("stored_at")
    before2 = (s.home / "queue.json").read_bytes()
    time.sleep(1.1)
    code, out = s.post({"action": "store", "id": patio})
    case("store twice (a double press on Yes, archive it): 200, the lists, the record byte for byte as it was",
         code == 200 and isinstance(out, dict) and where(out, "Patio session") == ["stored"] and (s.home / "queue.json").read_bytes() == before2 and s.shoot("Patio session").get("stored_at") == stamp, (code, str(out)[:200]))
    code, st = s.post({"action": "store", "id": lee})
    time.sleep(1.1)
    s.post({"action": "unstore", "id": patio})
    code, st = s.post({"action": "store", "id": patio})
    case("Archived: the one archived last is first", names(st["stored"]) == ["Patio session", "Lee family"], names(st["stored"]))
    code, st = s.post({"action": "unstore", "id": lee})
    rec = s.shoot("Lee family")
    case("unstore: back in Delivered, as it was (delivered date kept)", code == 200 and where(st, "Lee family") == ["delivered"] and "stored" not in rec and "stored_at" not in rec and rec.get("finished_at"), rec)
    code, st = s.post({"action": "requeue", "id": patio})
    rec = s.shoot("Patio session")
    case("requeue from Archived: in the queue, \"stored\" cleared, no due date", code == 200 and where(st, "Patio session") == ["waiting"] and not any(k in rec for k in ("stored", "stored_at", "finished_at")) and not rec.get("due"), rec)
    s.post({"action": "done", "id": patio})
    s.post({"action": "store", "id": patio})
    code, st = s.post({"action": "undo", "id": patio})
    rec = s.shoot("Patio session")
    case("undo from Archived: in the queue, \"stored\" cleared", code == 200 and where(st, "Patio session") == ["waiting"] and "stored" not in rec and "stored_at" not in rec, rec)
    s.post({"action": "due", "id": patio, "due": "2026-11-30"})
    code, st = s.post({"action": "unqueue", "id": patio})
    rec = s.shoot("Patio session")
    case("unqueue: in Uploaded shoots, no due date, nothing of a delivery", code == 200 and where(st, "Patio session") == ["archive"] and rec["status"] == "archived" and not any(rec.get(k) for k in ("due", "finished_at", "stored", "reminded")), rec)
    code, st = s.post({"action": "requeue", "id": patio})
    case("Add to my editing queue brings it back", code == 200 and where(st, "Patio session") == ["waiting"])
    code, st = s.post({"action": "done", "id": patio})
    rec = s.shoot("Patio session")
    case("done: Delivered, marked by the page", code == 200 and where(st, "Patio session") == ["delivered"] and rec["finished_by"] == "page", rec)
    case("the state names every list and where Make posts goes", set(st) >= {"today", "waiting", "archive", "delivered", "stored", "make_posts"}, sorted(st))
    case("nobody was lost: the same five shoots", len(s.queue()["shoots"]) == 5)
    code, raw = s.http("GET", "/queue.html")
    case("the served page has no \"Claude\" and no 8799", code == 200 and b"Claude" not in raw and b"8799" not in raw)


def toast(c, text, seconds=8):
    return c.wait_for("(() => { const t = document.querySelector('#toast'); return t.classList.contains('on') && t.textContent === %s })()" % json.dumps(text), seconds)


def shown(c, sel):
    """The names on the cards of a list that can be seen (a closed section's cards are not)."""
    return c.js("Array.from(document.querySelectorAll(%s)).filter(e => e.offsetParent !== null && e.getClientRects().length).map(e => e.querySelector('.name').textContent)" % json.dumps(sel))


def search(c, text):
    c.js("(() => { const q = document.querySelector('#q'); q.focus(); q.value = ''; q.dispatchEvent(new Event('input', {bubbles:true})) })()")
    c.click("#q")
    if text:
        c.type_text(text)
    c.wait_for("document.querySelector('#q').value === %s" % json.dumps(text), 5)


def check_page(c, s):
    """Before: the queue = Garcia (Nov 20), NASTY; Uploaded = Beach; Delivered = Patio, Lee."""
    c.open(s.url())
    c.wait_for("document.querySelectorAll('#list .card').length == 2", 10)
    case("Delivered and Archived start closed", c.js("!document.querySelector('#delivered').open && !document.querySelector('#stored').open"))
    case("their headings count them: Delivered (2), Archived (0)", c.text("#dtitle") == "Delivered (2)" and c.text("#stitle") == "Archived (0)", (c.text("#dtitle"), c.text("#stitle")))
    case("Uploaded shoots holds only the shoot that is not queued or delivered, with her count line",
         shown(c, "#alist .acard") == ["Beach day"] and c.text("#acount") == "1 shoot, newest first. Every shoot you back up lands here. When one is a client gallery you need to edit and deliver, add it to your editing queue.", (shown(c, "#alist .acard"), c.text("#acount")))
    case("the check mark says Mark as delivered (title and aria-label)",
         c.js("(() => { const b = document.querySelector('#list .card .check'); return b.title === 'Mark as delivered' && b.getAttribute('aria-label') === 'Mark Garcia wedding as delivered' })()"))
    case("each queue card has Take out of my queue", c.js("Array.from(document.querySelectorAll('#list .card')).every(x => x.querySelector('.unq') && x.querySelector('.unq').textContent === 'Take out of my queue')"))
    case("a name with <, & and a script is shown as text only", NASTY in shown(c, "#list .card") and c.js("window.__got === undefined && !document.querySelector('#list img[src=x]')"))
    case("the search line and its place: above Uploaded shoots, under the queue",
         c.text(".findsay") == "Looks through every shoot: your queue, uploaded, delivered and archived." and c.rect("#q")["y"] < c.rect("#archive")["y"] and c.rect("#q")["y"] > c.rect("#list")["bottom"] - 1)
    case("the Make posts link, on a delivered shoot, goes to the Assistant's own page server",
         c.js("Array.from(document.querySelectorAll('#dlist a.mk')).map(a => a.getAttribute('href') + '|' + a.textContent)") == ["http://127.0.0.1:%d/make-posts|Make posts from this shoot" % (s.port0 + 15)] * 2)

    # Make posts from this shoot: a press asks the queue server where that screen is, and goes there
    # (loaded while the page server's address is not known, so nothing but the press can find the way)
    known = s.home / "posting-url.txt"
    address = known.read_text(encoding="utf-8")
    known.unlink()
    c.reload()
    c.wait_for("document.querySelectorAll('#list .card').length == 2", 10)
    c.js("document.querySelector('#delivered').open = true")
    case("with no address known the link is still on every delivered shoot", c.js("Array.from(document.querySelectorAll('#dlist a.mk')).map(a => a.getAttribute('href') + '|' + a.textContent)") == ["#|Make posts from this shoot"] * 2)
    known.write_text(address, encoding="utf-8")
    c.click("#dlist a.mk")
    c.wait_for("location.pathname === '/make-posts'", 10)
    case("a press on Make posts from this shoot lands on the page server's /make-posts", c.js("location.href") == "http://127.0.0.1:%d/make-posts" % (s.port0 + 15), c.js("location.href"))
    c.open(s.url() + "#stored")
    c.wait_for("document.querySelector('#stored').open", 10)
    case("#stored opens Archived (\"show my archived shoots\"); Delivered stays closed", c.js("document.querySelector('#stored').open && !document.querySelector('#delivered').open"))
    c.js("location.hash = '#delivered'")       # only the part after # changes, so the page is loaded again by hand
    c.reload()
    c.wait_for("document.querySelector('#delivered').open", 10)
    case("#delivered opens Delivered", c.js("document.querySelector('#delivered').open && !document.querySelector('#stored').open"))
    c.js("history.replaceState(null, '', location.pathname)")
    c.reload()
    c.wait_for("document.querySelectorAll('#list .card').length == 2", 10)

    # one search for everything
    search(c, "patio")
    case("searching for a delivered shoot opens Delivered and shows it; the queue and Uploaded hide the rest",
         c.js("document.querySelector('#delivered').open") and shown(c, "#dlist .acard") == ["Patio session"] and shown(c, "#list .card") == [] and shown(c, "#alist .acard") == []
         and c.js("document.querySelector('#nomatch').hidden") and not c.js("document.querySelector('#stored').open"), (shown(c, "#dlist .acard"), shown(c, "#list .card")))
    case("its heading counts the matches", c.text("#dtitle") == "Delivered (1)")
    search(c, "GARCIA")
    case("the search filters the queue cards too, whatever the capitals", shown(c, "#list .card") == ["Garcia wedding"] and shown(c, "#dlist .acard") == [] and c.js("document.querySelector('#nomatch').hidden"))
    search(c, "beach")
    case("and Uploaded shoots", shown(c, "#alist .acard") == ["Beach day"] and shown(c, "#list .card") == [] and c.js("document.querySelector('#nomatch').hidden"))
    search(c, "zzz nobody")
    case("\"No shoot by that name.\" only when nothing matches anywhere", c.js("!document.querySelector('#nomatch').hidden") and c.text("#nomatch") == "No shoot by that name."
         and c.rect("#nomatch")["h"] > 0 and shown(c, "#list .card") + shown(c, "#alist .acard") + shown(c, "#dlist .acard") + shown(c, "#slist .acard") == [])
    search(c, "")
    case("an empty search shows everything again", len(shown(c, "#list .card")) == 2 and shown(c, "#alist .acard") == ["Beach day"] and c.js("document.querySelector('#nomatch').hidden"))

    # Archive, behind "Are you sure you want to archive this?"
    c.js("document.querySelector('#delivered').open = true")
    row = "#dlist .acard[data-id=%s]" % json.dumps(s.shoot("Patio session")["id"])
    case("a delivered shoot's buttons, in her order", c.js("Array.from(document.querySelectorAll(%s)).map(e => e.textContent.trim())" % json.dumps(row + " .acts > *")) == ["Make posts from this shoot", "Put back in my editing queue", "Archive"])
    c.click(row + " .store")
    c.wait_for("!!document.querySelector(%s)" % json.dumps(row + " .sure"), 5)
    case("Archive asks first, with her words and two buttons", c.text(row + " .sure b") == "Are you sure you want to archive this?" and c.text(row + " .sure .yes") == "Yes, archive it" and c.text(row + " .sure .no") == "Cancel")
    case("nothing is archived by the first press", "stored" not in s.shoot("Patio session"))
    c.click(row + " .store")
    case("a second press on Archive does not ask twice", c.count(row + " .sure") == 1)
    c.click(row + " .sure .no")
    case("Cancel takes the question away and archives nothing", c.count(row + " .sure") == 0 and "stored" not in s.shoot("Patio session"))
    c.click(row + " .store")
    c.wait_for("!!document.querySelector(%s)" % json.dumps(row + " .sure .yes"), 5)
    # a double press on Yes, archive it: both in one tick, as a double click sends them
    c.js("(() => { window.__toasts = []; const t = document.querySelector('#toast'); new MutationObserver(() => window.__toasts.push(t.textContent)).observe(t, {childList:true, characterData:true, subtree:true}); const b = document.querySelector(%s); b.click(); b.click() })()" % json.dumps(row + " .sure .yes"))
    toast(c, "Archived. You can bring it back any time.")
    time.sleep(0.6)
    case("a double press on Yes, archive it never says \"That did not save\"", c.js("window.__toasts.length > 0 && window.__toasts.every(t => t === 'Archived. You can bring it back any time.')"), c.js("window.__toasts"))
    case("Yes, archive it: saved, out of Delivered, into Archived", s.shoot("Patio session").get("stored") is True and c.text("#dtitle") == "Delivered (1)" and c.text("#stitle") == "Archived (1)")
    search(c, "pat")
    case("searching for an archived shoot opens Archived and shows it", c.js("document.querySelector('#stored').open") and shown(c, "#slist .acard") == ["Patio session"] and c.js("document.querySelector('#nomatch').hidden"))
    search(c, "")
    case("an archived shoot has only Bring it back (no Archive, no Make posts)", c.js("Array.from(document.querySelectorAll('#slist .acard .acts > *')).map(e => e.textContent.trim())") == ["Bring it back"])
    c.js("document.querySelector('#delivered').open = false")
    c.js("(() => { window.__toasts.length = 0; const b = document.querySelector('#slist .unstore'); b.click(); b.click() })()")
    toast(c, "Back in Delivered.")
    time.sleep(0.6)
    case("a double press on Bring it back: only \"Back in Delivered.\"", c.js("window.__toasts.length > 0 && window.__toasts.every(t => t === 'Back in Delivered.')"), c.js("window.__toasts"))
    case("Bring it back: in Delivered again, and Delivered is open", "stored" not in s.shoot("Patio session") and c.js("document.querySelector('#delivered').open") and "Patio session" in shown(c, "#dlist .acard") and c.text("#stitle") == "Archived (0)")
    case("an empty Archived says so", c.js("document.querySelector('#slist').textContent.trim()") == "Nothing archived.")

    # Take out of my queue
    card = "#list .card[data-id=%s]" % json.dumps(s.shoot("Garcia wedding")["id"])
    c.js("(() => { window.__toasts.length = 0; const b = document.querySelector(%s); b.click(); b.click() })()" % json.dumps(card + " .unq"))
    toast(c, "Garcia wedding is back in your uploaded shoots")
    time.sleep(0.6)
    case("a double press on Take out of my queue: only its own toast", c.js("window.__toasts.length > 0 && window.__toasts.every(t => t === 'Garcia wedding is back in your uploaded shoots')"), c.js("window.__toasts"))
    rec = s.shoot("Garcia wedding")
    case("Take out of my queue: saved, in Uploaded shoots with no date, with Add to my editing queue",
         rec["status"] == "archived" and not rec.get("due") and "Garcia wedding" in shown(c, "#alist .acard") and "Garcia wedding" not in shown(c, "#list .card")
         and c.js("Array.from(document.querySelectorAll('#alist .acard .requeue')).every(b => b.textContent === 'Add to my editing queue')"))
    c.click("#alist .acard[data-id=%s] .requeue" % json.dumps(rec["id"]))
    toast(c, "Added to your editing queue. No due date yet.")
    case("Add to my editing queue brings it back", s.shoot("Garcia wedding")["status"] == "waiting" and "Garcia wedding" in shown(c, "#list .card"))

    # the check mark, pressed twice in one tick
    c.js("(() => { window.__toasts.length = 0; const b = document.querySelector(%s); b.click(); b.click() })()" % json.dumps(card + " .check"))
    toast(c, "Garcia wedding: delivered, moved to Delivered below")
    stamp = s.shoot("Garcia wedding").get("finished_at")
    case("between the two presses the card keeps its delivered look", c.js("document.querySelector(%s).classList.contains('done')" % json.dumps(card)))
    c.wait_for("!document.querySelector(%s)" % json.dumps(card), 8)
    case("a double press on the check mark: the delivered toast only, one saved change",
         c.js("window.__toasts.length === 1 && window.__toasts[0] === 'Garcia wedding: delivered, moved to Delivered below'") and s.shoot("Garcia wedding").get("finished_at") == stamp, c.js("window.__toasts"))
    case("the check mark: saved as delivered, out of the queue, in Delivered, not in Uploaded shoots",
         s.shoot("Garcia wedding")["status"] == "finished" and c.text("#dtitle") == "Delivered (3)" and "Garcia wedding" not in shown(c, "#alist .acard"))
    case("a delivered card says Delivered and the day", c.js("document.querySelector('#dlist .acard .tag.edited').textContent.startsWith('Delivered ')"))
    c.click("#dlist .acard[data-id=%s] .requeue" % json.dumps(s.shoot("Garcia wedding")["id"]))
    toast(c, "Back in your editing queue. No due date yet.")
    case("Put back in my editing queue", s.shoot("Garcia wedding")["status"] == "waiting")

    # a page a step behind the chat: the chat takes the shoot out of the queue, then the page's check mark is pressed
    s.run("unqueue", "garcia")
    c.js("window.__toasts.length = 0")
    c.click(card + " .check")
    toast(c, "This shoot was changed somewhere else. Here's the newest.")
    case("a page a step behind the chat: it says so, shows the newest lists, never \"That did not save. Try again.\"",
         "Garcia wedding" not in shown(c, "#list .card") and "Garcia wedding" in shown(c, "#alist .acard") and s.shoot("Garcia wedding")["status"] == "archived"
         and not c.js("window.__toasts.some(t => t.includes('did not save'))"), c.js("window.__toasts"))
    s.run("undo", "garcia")

    # the last shoot out: the shorter empty line
    for n in ("Garcia wedding", NASTY):
        s.post({"action": "unqueue", "id": s.shoot(n)["id"]})
    c.reload()
    c.wait_for("!!document.querySelector('#list .empty')", 10)
    case("the empty queue says only her shorter line", c.text("#list .empty") .replace("\n", "") in ("Nothing waiting.Shoots land here when you add them after a backup.",) and c.text("#count") == "All caught up", c.text("#list .empty"))
    case("the nasty name in Uploaded shoots is text too", NASTY in shown(c, "#alist .acard") and c.js("window.__got === undefined"))
    case("nothing on the page says Claude", "claude" not in c.js("document.body.innerText").lower())
    c.phone(390, 844)
    c.reload()
    c.wait_for("!!document.querySelector('#alist .acard')", 10)
    c.js("document.querySelector('#delivered').open = true")
    case("at phone width nothing runs off the side", c.js("document.documentElement.scrollWidth <= window.innerWidth + 1"), c.js("document.documentElement.scrollWidth"))
    c.desktop()
    case("no errors on the page", not c.page_errors(), c.page_errors())
    case("the page asked for nothing outside this computer", not c.outside_requests(), c.outside_requests())
    # Back to home goes the same way: the queue server is asked where home is (and starts it if it is not up)
    known = s.home / "posting-url.txt"
    address = known.read_text(encoding="utf-8")
    known.write_text("http://127.0.0.1:%d/posting.html" % (s.port0 + 15) + "\n", encoding="utf-8")
    c.reload()
    c.wait_for("!!document.querySelector('.homelink')", 10)
    c.js("document.querySelector('.homelink').setAttribute('href', 'http://127.0.0.1:%d/nowhere')" % (s.port0 + 17))   # a stale address on the page
    c.click(".homelink")
    c.wait_for("location.pathname === '/home'", 10)
    case("Back to home asks the queue server for the address (a stale one on the page is not followed)", c.js("location.href") == "http://127.0.0.1:%d/home" % (s.port0 + 15), c.js("location.href"))
    known.write_text(address, encoding="utf-8")


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=8990)
    ap.add_argument("--no-chrome", action="store_true", help="the lists, the words and the routes only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792, 8799) for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="edit-queue-v26-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    s = Setup(work, a.port)
    try:
        eq = group("the lists and the chat's commands", check_lists, s)
        if eq:
            group("the words", check_words, eq)
            group("the Make posts link", check_link, eq, s)
        pretend = pretend_server(a.port + 15)      # stands in for the Assistant's own page server (/home, /make-posts)
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 20)
        group("the page server", check_server, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                group("the page", check_page, c, s)
    finally:
        s.stop()
        try:
            pretend.shutdown()
        except NameError:
            pass
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
