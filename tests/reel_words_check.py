#!/usr/bin/env python3
"""Each reel has its own words (Nicole, Nov 23: "each reel gets its own caption"), checked in the record, from
the chat, by request, and on the real words page in a HIDDEN Chrome.

    python3 tests/reel_words_check.py [--port 9965] [--work <a folder to keep the run in>] [--no-chrome]
                                      [--only record|chat|routes|kit|queue|reminders|page]

What it does, on pretend Assistants it makes itself in a throwaway folder (the words page check's own: one kit, a
few tiny pictures; nothing of a client's, nothing of the real ~/.studio, no drive, never the real Calendar):
  * the record: a shoot with ONE reel writes byte for byte the record it wrote before Nov 23 (a kept copy made
    by the code before: tests/fixtures/post-words-one-reel-before-nov23*.json); a later reel's words go under
    its own id and nowhere else; nothing new is written until a later reel has words; a reel id that isn't one
    is refused before anything is touched; reading never changes the record; the version before is kept;
  * one reel's words can never land in another's: every way of saving (answers, a draft, the page's save, a
    carry) is tried against a record that holds two other reels, and only the reel named changes;
  * the chat: with several reels a reel command without --reel stops and lists the names, and nothing is saved;
    --reel by name, by a part of one name, by id; a carousel's commands never ask; show and ask say whose words
    they are; a new reel is offered another reel's answers (carry-reel: answers only, never over its own);
  * the routes: a page's reel is the one its address names; a look or a save with none is the shoot's first
    reel's (never whichever reel is open now); a reel that isn't the shoot's is refused in her words, nothing
    written; a shoot with one reel is as it was;
  * the post kit: Your words lists each reel with its own state and its own link; "No caption: add it anyway?"
    looks at THAT reel's caption;
  * the posting queue's panel and a reminder's notes: each reel's own caption and hook;
  * the page itself (when there is a Chrome): which reel it says, the links to the others (a name with a tag in
    it shown as letters), the lines to copy naming the reel, typing saved to that reel only, a new reel starting
    empty with one press to start from another reel's answers.

No folder is ever opened and CapCut is never started. The page servers and the hidden Chrome are this test's own
and are stopped at the end. Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9,
standard library only, a Mac or a PC.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import words_page_check as wpc  # noqa: E402  (its pretend Assistant: one kit, the page server, words.py from the chat)
import kit_reels_queue_check as krq  # noqa: E402  (a shoot with several reels, made as the reel page makes them)
import posting_panel_check as ppc  # noqa: E402

KIT, SHORT, HOOKS = wpc.KIT, wpc.SHORT, wpc.HOOKS
KQ = quote(KIT, safe="")
KJ = quote(KIT, safe="!'()*~")                  # the kit's name as the page's own script spells it in an address
SECOND, THIRD = krq.SECOND, krq.THIRD            # "White <b>Backdrop" and "Zoë's 🌊 third": names are theirs
GONE = "That reel isn't there anymore."
ONLY = None
BEFORE = "post-words-one-reel-before-nov23.json"
BEFORE_PREV = "post-words-one-reel-before-nov23.prev.json"

# What a shoot with one reel does to its words, start to finish, with the clock held still, so the record can be
# compared byte for byte with the one the code before Nov 23 wrote (the two kept files were made by running this
# very text against that code). argv: the scripts folder, the kit, and optionally the reel to name on every reel
# save ("v1": the shoot's first reel, which must write the very same record).
SCENARIO = r"""
import sys, types
from pathlib import Path
sys.path.insert(0, sys.argv[1])
kit = Path(sys.argv[2])
reel = sys.argv[3] if len(sys.argv) > 3 else None
import words
t = [1700000000.0]
def tick():
    t[0] += 1.5
    return t[0]
words.time = types.SimpleNamespace(time=tick)
def r(piece):
    return {"reel": reel} if (reel and piece == "reel") else {}
words.save_answers(kit, "reel", {"about": "Zoë & the boys, a windy morning \U0001F30A", "who": ["new", "followers"], "who_text": "moms",
                                 "where": "trial", "purpose": "offer", "purpose_text": "Minis, Dec 4", "notes": "Names: Zoë"}, **r("reel"))
words.save_draft(kit, "reel", {"caption": "Line one\n\nLine two “quoted”", "hooks": ["hook %d" % i for i in range(10)]}, **r("reel"))
words.save_from_page(kit, "reel", {"picked": [2, 0], "own": "my own", "answers": {"notes": "No names"}}, **r("reel"))
words.carry(kit, "reel", "carousel", **r("reel"))
words.save_draft(kit, "carousel", {"caption": "A carousel caption"})
words.save_from_page(kit, "reel", {"caption": "edited by hand"}, **r("reel"))
"""


def skip(line):
    print("SKIP  " + line, flush=True)


def want(name):
    return ONLY is None or ONLY == name


def unix(b):
    return b.replace(b"\r\n", b"\n")


def run_scenario(s, scripts=SCRIPTS, reel=None):
    args = [sys.executable, "-c", SCENARIO, str(scripts), str(s.kit)] + ([reel] if reel else [])
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=s.env, cwd=str(scripts))
    if r.returncode != 0:
        raise RuntimeError("the one-reel scenario: " + (r.stdout + r.stderr)[-400:])


def prev_bytes(s):
    try:
        return (s.kit / ".kit" / "post-words.prev.json").read_bytes()
    except OSError:
        return b""


def words_module(s):
    """words.py, in this process, pointed at this pretend Assistant."""
    os.environ["STUDIO_HOME"] = str(s.studio)
    os.environ["HOME"] = str(s.home)
    os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    sys.path.insert(0, str(SCRIPTS))
    import importlib
    return importlib.import_module("words")


def pieces(s):
    return ((s.record() or {}).get("pieces") or {})


def later(s, vid):
    m = pieces(s).get("reels")
    return (m.get(vid) if isinstance(m, dict) else None) or {}


def chat(s, *args, given=None):
    """words.py from the chat: (exit code, what it printed). `given`: what goes in --file."""
    args = list(args)
    if given is not None:
        s.n += 1
        f = s.work / ("rw%d.json" % s.n)
        f.write_text(json.dumps(given, ensure_ascii=False), encoding="utf-8")
        args += ["--file", str(f)]
    return s.cmd("words.py", *args)


def three_reels(s):
    """Reel 1 (made), SECOND (its own order 6,5; made) and THIRD (not made)."""
    krq.two_reels(s)
    krq.new_reel(s, THIRD)


def state(s, piece="reel", reel=None):
    return s.http("GET", "/words-state?kit=" + KQ + ("&reel=" + quote(reel, safe="") if reel else "") + "&piece=" + piece)


def save(s, piece="reel", **given):
    return s.http("POST", "/words-save", dict({"kit": KIT, "piece": piece}, **given))[:2]


# ---------- 1. the record ----------

def check_record(work, port):
    s = krq.fresh(work, "one", port)
    f, fp = FIXTURES / BEFORE, FIXTURES / BEFORE_PREV
    run_scenario(s)
    case("a shoot with one reel: the record is byte for byte what the code before Nov 23 wrote",
         f.is_file() and unix(s.rec_bytes()) == unix(f.read_bytes()), s.rec_bytes()[:300])
    case("...and so is the version kept before the last save", fp.is_file() and unix(prev_bytes(s)) == unix(fp.read_bytes()))
    case("...with no map of reels in it", "reels" not in pieces(s) and sorted(pieces(s)) == ["carousel", "reel"], sorted(pieces(s)))

    s = krq.fresh(work, "first", port)
    three_reels(s)
    run_scenario(s, reel="v1")
    case("a shoot with three reels, every save naming its FIRST reel: the very same bytes (the first reel is 'pieces.reel', as ever)",
         unix(s.rec_bytes()) == unix(f.read_bytes()) and unix(prev_bytes(s)) == unix(fp.read_bytes()))
    case("nothing new is written until a later reel has words: still no map of reels", "reels" not in pieces(s))

    w = words_module(s)
    kit = s.kit
    before = s.rec_bytes()
    rec = w.load(kit)
    snap = json.dumps(rec, sort_keys=True)
    got = [w.read_of(rec, "reel", v) for v in ("v2", "v3", "v99")]
    case("reading a reel that has no words gives nothing, and changes neither the record in hand nor the file",
         all(g == {"answers": {}} for g in got) and json.dumps(rec, sort_keys=True) == snap and s.rec_bytes() == before, got)
    case("a new reel starts empty: nothing of the first reel's is read as its own",
         w.status(kit, "v2")["reel"] == {"answered": False, "caption": False, "hooks": 0, "picked": 0}
         and w.status(kit)["reel"]["caption"] and w.status(kit, "v1")["reel"] == w.status(kit)["reel"], w.status(kit, "v2"))
    bad = []
    for vid in ("v0", "v", "2", "../v2", "v2 ", "reels", "carousel", "V2", "v12345", 2, ["v2"], True, ""):
        for fn in (lambda v: w.save_answers(kit, "reel", {"about": "x"}, v), lambda v: w.save_draft(kit, "reel", {"caption": "x"}, v),
                   lambda v: w.save_from_page(kit, "reel", {"own": "x"}, v), lambda v: w.read_of(w.load(kit), "reel", v),
                   lambda v: w.carry(kit, "carousel", "reel", v)):
            try:
                fn(vid)
                bad.append(vid)
            except w.Stop:
                pass
    case("a reel id that isn't one is refused every way in, and nothing is written", not bad and s.rec_bytes() == before, bad)

    first = json.dumps(pieces(s)["reel"], sort_keys=True)
    car = json.dumps(pieces(s)["carousel"], sort_keys=True)
    w.save_answers(kit, "reel", {"about": "The white backdrop set", "where": "feed"}, "v2")
    case("an answer saved for the second reel is under its own id, in the shape 'reel' has",
         later(s, "v2").get("answers") == {"about": "The white backdrop set", "where": "feed"} and "updated" in later(s, "v2"), later(s, "v2"))
    case("...the first reel's words and the carousel's are exactly as they were",
         json.dumps(pieces(s)["reel"], sort_keys=True) == first and json.dumps(pieces(s)["carousel"], sort_keys=True) == car)
    case("...and the version before that save is kept beside it", unix(prev_bytes(s)) == unix(before))
    w.save_draft(kit, "reel", {"caption": "Second reel's caption", "hooks": HOOKS}, "v2")
    got = w.save_from_page(kit, "reel", {"picked": [1, 3], "own": "second's own"}, "v2")
    case("a draft and a page save for the second reel: its caption, its ten hooks, its picks, its own caption; the answer is that reel's",
         later(s, "v2").get("caption") == "Second reel's caption" and later(s, "v2").get("hooks") == HOOKS and later(s, "v2").get("picked") == [1, 3]
         and got.get("own") == "second's own" and got.get("caption") == "Second reel's caption", later(s, "v2"))
    w.save_draft(kit, "reel", {"caption": "Third reel's caption"}, "v3")
    second = json.dumps(later(s, "v2"), sort_keys=True)
    third = json.dumps(later(s, "v3"), sort_keys=True)
    # every way of saving, each against the other two reels
    w.save_answers(kit, "reel", {"about": "first again"})
    w.save_draft(kit, "reel", {"caption": "First again", "hooks": ["a", "b"]})
    w.save_from_page(kit, "reel", {"picked": [1], "own": "first's own", "caption": "First, by hand"})
    w.carry(kit, "carousel", "reel")
    case("every way of saving the FIRST reel's words leaves the second's and the third's exactly as they were",
         json.dumps(later(s, "v2"), sort_keys=True) == second and json.dumps(later(s, "v3"), sort_keys=True) == third)
    first = json.dumps(pieces(s)["reel"], sort_keys=True)
    w.save_answers(kit, "reel", {"notes": "No names"}, "v3")
    w.save_draft(kit, "reel", {"hooks": ["only", "three", "hooks"]}, "v3")
    w.save_from_page(kit, "reel", {"picked": [0]}, "v3")
    case("every way of saving the THIRD reel's leaves the first's and the second's exactly as they were",
         json.dumps(pieces(s)["reel"], sort_keys=True) == first and json.dumps(later(s, "v2"), sort_keys=True) == second
         and later(s, "v3").get("hooks") == ["only", "three", "hooks"] and later(s, "v3").get("picked") == [0])
    case("new hooks clear the picks of that reel only", later(s, "v2").get("picked") == [1, 3] and pieces(s)["reel"].get("picked") == [1])
    # carry: a reel to the carousel, the carousel to a reel
    w.carry(kit, "reel", "carousel", "v2")
    case("carry from the second reel to the carousel: the carousel has the second reel's answers (never 'where')",
         pieces(s)["carousel"]["answers"].get("about") == "The white backdrop set" and "where" not in pieces(s)["carousel"]["answers"], pieces(s)["carousel"]["answers"])
    w.save_answers(kit, "carousel", {"about": "For the carousel"})
    w.carry(kit, "carousel", "reel", "v3")
    case("carry from the carousel to the third reel lands in the third reel only",
         later(s, "v3")["answers"].get("about") == "For the carousel" and json.dumps(later(s, "v2"), sort_keys=True) == second
         and pieces(s)["reel"]["answers"].get("about") != "For the carousel")
    # a reel starting from another reel's answers
    krq.new_reel(s, "Fourth")
    done = w.carry_reel(kit, "v2", "v4")
    case("a new reel starts from another reel's answers: the answers only, never its caption, hooks, picks or own caption",
         later(s, "v4").get("answers") == later(s, "v2")["answers"] and not any(k in later(s, "v4") for k in ("caption", "hooks", "picked", "own"))
         and "about" in done, later(s, "v4"))
    stops = []
    for a, b in (("v2", "v4"), ("v2", "v2"), ("v1", "v1"), (None, "v1"), ("v9", "v3")):
        mark = s.rec_bytes()
        try:
            w.carry_reel(kit, a, b)
            stops.append((a, b))
        except w.Stop:
            if s.rec_bytes() != mark:
                stops.append((a, b, "written"))
    case("...never over answers the reel already has, never onto itself, never from a reel with none; nothing written", not stops, stops)
    st = w.reels_status(kit, ["v1", "v2", "v3", "v4", "bad id"])
    case("where each reel's words stand, read in one look: each its own",
         sorted(st) == ["v1", "v2", "v3", "v4"] and st["v2"]["hooks"] == 10 and st["v2"]["picked"] == 2 and st["v3"]["hooks"] == 3
         and st["v4"] == {"answered": True, "caption": False, "hooks": 0, "picked": 0} and st["v1"] == w.status(kit)["reel"], st)
    case("the reels that have words of their own are told from the record", sorted(w.reels_with_words(w.load(kit))) == ["v2", "v3", "v4"])
    # a record changed by hand
    rec = s.record()
    rec["pieces"]["reels"] = ["not", "a", "map"]
    s.rec.write_text(json.dumps(rec), encoding="utf-8")
    case("a map of reels that isn't one (changed by hand) reads as no words, and the page's piece is still answered",
         w.read_of(w.load(kit), "reel", "v2") == {"answers": {}} and w.status(kit, "v2")["reel"]["caption"] is False and w.status(kit)["reel"]["caption"])
    w.save_answers(kit, "reel", {"about": "after the mend"}, "v2")
    case("...and the next save for a reel makes it a map again, the first reel's words untouched",
         later(s, "v2").get("answers") == {"about": "after the mend"} and json.dumps(pieces(s)["reel"], sort_keys=True) == first)


# ---------- 2. the chat ----------

def check_chat(work, port):
    s = krq.fresh(work, "chat1", port)
    code, out = chat(s, "answer", KIT, "reel", given={"about": "One reel, no name needed"})
    case("a shoot with one reel: no --reel is needed, and the line says nothing about reels",
         code == 0 and s.piece("reel")["answers"]["about"] == "One reel, no name needed" and "Reel 1" not in out and "reels" not in pieces(s), out)
    code, out = chat(s, "answer", KIT, "reel", "--reel", "Reel 1", given={"notes": "No names"})
    case("...and --reel \"Reel 1\" given anyway is that one reel", code == 0 and s.piece("reel")["answers"]["notes"] == "No names" and "reels" not in pieces(s), out)
    mark = s.rec_bytes()
    code, out = chat(s, "answer", KIT, "reel", "--reel", "Reel 7", given={"notes": "x"})
    case("...a name that fits no reel stops, nothing saved", code == 2 and "STOP" in out and s.rec_bytes() == mark, out)
    code, out = chat(s, "show", KIT, "reel")
    case("show for one reel reads as it always did (no reel named)", code == 0 and ", the reel: what they said" in out and "--reel" not in out, out[-400:])

    s = krq.fresh(work, "chat3", port)
    three_reels(s)
    s.cmd("words.py", "answer", KIT, "reel", "--reel", "Reel 1", "--file", str(_file(s, {"about": "The first reel's story"})))
    mark = s.rec_bytes()
    for what, given in (("answer", {"about": "whose?"}), ("draft", {"caption": "whose?"})):
        code, out = chat(s, what, KIT, "reel", given=given)
        case("three reels, `%s reel` with no --reel: stops, lists every reel by name, saves nothing" % what,
             code == 2 and "STOP" in out and "Nothing was saved" in out and all(('"%s"' % n) in out for n in ("Reel 1", SECOND, THIRD))
             and "--reel" in out and s.rec_bytes() == mark, out)
    for what in ("show", "ask"):
        code, out = chat(s, what, KIT, "reel")
        case("...`%s reel` with no --reel stops the same way" % what, code == 2 and "--reel" in out and ('"%s"' % SECOND) in out, out[-300:])
    code, out = chat(s, "carry", KIT, "carousel", "reel")
    case("...and so does a carry that ends at a reel", code == 2 and "--reel" in out and s.rec_bytes() == mark, out[-300:])
    code, out = chat(s, "answer", KIT, "carousel", given={"about": "The carousel needs no reel"})
    case("a carousel's own commands never ask which reel", code == 0 and pieces(s)["carousel"]["answers"]["about"] == "The carousel needs no reel", out)
    code, out = chat(s, "answer", KIT, "reel", "--reel", SECOND, given={"about": "The second reel's story", "where": "trial"})
    case("--reel by its whole name: saved to that reel, and the line names it",
         code == 0 and later(s, "v2")["answers"] == {"about": "The second reel's story", "where": "trial"} and SECOND in out
         and s.piece("reel")["answers"]["about"] == "The first reel's story", out)
    code, out = chat(s, "draft", KIT, "reel", "--reel", "backdrop", given={"caption": "Second caption", "hooks": HOOKS})
    case("--reel by a part of one name", code == 0 and later(s, "v2").get("caption") == "Second caption" and "caption" not in s.piece("reel"), out)
    code, out = chat(s, "answer", KIT, "reel", "--reel", "v3", given={"notes": "Names: Zoë"})
    case("--reel by the reel's id", code == 0 and later(s, "v3")["answers"] == {"notes": "Names: Zoë"}, out)
    mark = s.rec_bytes()
    code, out = chat(s, "answer", KIT, "reel", "--reel", "nothing like it", given={"about": "x"})
    case("--reel with a name that fits none: stops, lists the reels, saves nothing", code == 2 and "Reel 1" in out and s.rec_bytes() == mark, out)
    code, out = chat(s, "answer", KIT, "reel", "--reel", "e", given={"about": "x"})
    case("--reel with a part that fits more than one: stops, saves nothing", code == 2 and "more than one" in out and s.rec_bytes() == mark, out)
    code, out = chat(s, "show", KIT, "reel", "--reel", SECOND)
    case("show --reel: that reel's answers and caption, said to be its own",
         code == 0 and ('the reel "%s": what they said' % SECOND) in out and "The second reel's story" in out and "Caption: Second caption" in out
         and "The first reel's story" not in out, out[-900:])
    s.cmd("words.py", "draft", KIT, "reel", "--reel", "Reel 1", "--file", str(_file(s, {"caption": "First caption", "hooks": HOOKS})))
    code, out = chat(s, "show", KIT, "reel", "--reel", SECOND)
    case("...and another reel's caption is printed only as what this one must differ from",
         code == 0 and 'The caption of the reel "Reel 1", already written' in out and "First caption" in out and "genuinely DIFFERENT" in out, out[-900:])
    code, out = chat(s, "show", KIT, "carousel")
    case("show carousel with several reels: every reel's caption is one to differ from",
         code == 0 and "First caption" in out and "Second caption" in out and "genuinely different from it too" in out, out[-900:])
    krq.new_reel(s, "Fourth")
    code, out = chat(s, "ask", KIT, "reel", "--reel", "Fourth")
    case("ask for a reel with nothing answered yet: offered another reel's answers, with the command",
         code == 0 and "carry-reel" in out and "--from \"Reel 1\"" in out and '--reel "Fourth"' in out and "never copied" in out, out[-700:])
    code, out = chat(s, "ask", KIT, "reel", "--reel", SECOND)
    case("...a reel that is answered is offered nothing of another reel's", code == 0 and "carry-reel" not in out, out[-400:])
    code, out = s.cmd("words.py", "carry-reel", KIT, "--from", "Reel 1", "--reel", "Fourth")
    case("carry-reel: the new reel has the first reel's answers and nothing else of it",
         code == 0 and later(s, "v4").get("answers") == s.piece("reel")["answers"] and "caption" not in later(s, "v4") and "hooks" not in later(s, "v4"), out)
    mark = s.rec_bytes()
    code, out = s.cmd("words.py", "carry-reel", KIT, "--from", SECOND, "--reel", "Fourth")
    case("...a second time it stops: never over answers the reel has", code == 2 and "STOP" in out and s.rec_bytes() == mark, out)
    code, out = chat(s, "carry", KIT, "reel", "carousel", "--reel", SECOND)
    case("carry reel carousel --reel: the carousel gets that reel's answers", code == 0 and pieces(s)["carousel"]["answers"]["about"] == "The second reel's story", out)
    code, out = s.cmd("kit.py", "show", KIT)
    case("the chat's own look at the kit says where each reel's words stand, by name",
         code == 0 and 'reel "Reel 1" caption written' in out and ('reel "%s" caption written' % SECOND) in out
         and ('reel "%s" told, not written' % THIRD) in out, out[-500:])


def _file(s, given):
    s.n += 1
    f = s.work / ("rwf%d.json" % s.n)
    f.write_text(json.dumps(given, ensure_ascii=False), encoding="utf-8")
    return f


# ---------- 3. the routes ----------

def page_data(s, piece="reel", reel=None):
    code, _, raw = s.http("GET", "/words.html?kit=" + KQ + ("&reel=" + quote(reel, safe="") if reel else "") + "&piece=" + piece)
    t = raw.decode("utf-8")
    m = re.search(r"<script type='application/json' id='wordsData'>(.*?)</script>", t, re.S)
    return code, (json.loads(m.group(1)) if m else {}), t


def check_routes(work, port):
    s = krq.fresh(work, "routes1", port)
    s.reel_made()
    s.start()
    try:
        code, j, _ = state(s)
        case("a shoot with one reel: the state names no reel and lists none", code == 200 and j["reel"] is None and j["reels"] == [] and j["from"] is None and j["reel_name"] == "", j)
        code, d, t = page_data(s)
        case("...its page keeps no reel, its tabs name none, and its lines to copy are hers",
             d.get("reel") is None and "&amp;reel=" not in t and ("Ask me about the %s reel" % html.escape(SHORT)) in t and "id='reelsBar' hidden" in t)
        code, j = save(s, answers={"about": "one reel"})
        code2, j2 = save(s, reel="v1", own="by its id too")
        case("...a save with no reel, or naming its one reel, is the shoot's words as ever",
             code == 200 and code2 == 200 and s.piece("reel")["answers"]["about"] == "one reel" and s.piece("reel")["own"] == "by its id too" and "reels" not in pieces(s))
        mark = s.rec_bytes()
        code, j = save(s, reel="v2", own="a reel that isn't")
        case("...a save naming a reel the shoot doesn't have is refused in her words, nothing written", code == 409 and j["words"] == GONE and s.rec_bytes() == mark, (code, j))
        code, j, _ = state(s, reel="v2")
        case("...and so is a look", code == 404 and j["ok"] is False and j["words"] == GONE, (code, j))
    finally:
        s.stop()

    s = krq.fresh(work, "routes3", port)
    three_reels(s)                                  # the reel being worked on is the third, the one started last
    s.slides_made(3)
    s.words_reel = lambda what, reel, given: chat(s, what, KIT, "reel", "--reel", reel, given=given)
    s.words_reel("answer", "Reel 1", {"about": "The first reel's story", "who": ["new"], "where": "feed"})
    s.words_reel("draft", "Reel 1", {"caption": "First caption", "hooks": HOOKS})
    s.start()
    try:
        code, d, t = page_data(s)
        case("three reels, an address with no reel: the page opens the reel being worked on, and keeps its id",
             code == 200 and d.get("reel") == "v3" and "&amp;reel=v3&amp;piece=carousel" in t, d.get("reel"))
        code, d, t = page_data(s, reel="v2")
        case("...an address naming a reel opens that one", d.get("reel") == "v2" and "&amp;reel=v2&amp;piece=reel" in t)
        code, d, t = page_data(s, reel="v9")
        code2, d2, _ = page_data(s, reel="<script>")
        case("...an address naming a reel that isn't (or isn't an id) opens the reel being worked on, and never puts what it was given in the page",
             d.get("reel") == "v3" and d2.get("reel") == "v3" and "v9" not in t, (d.get("reel"), d2.get("reel")))
        case("no reel's name is in the page's own markup (names arrive with the state, as text)", SECOND not in t and html.escape(SECOND) not in t and THIRD not in t)
        code, j, _ = state(s)
        case("a look with no reel (a page opened when the shoot had one reel): the FIRST reel's words, never the open one's",
             code == 200 and j["reel"] == "v1" and j["reel_name"] == "Reel 1" and j["w"]["caption"] == "First caption" and len(j["w"]["hooks"]) == 10
             and j["reels"] == [{"id": "v1", "name": "Reel 1"}, {"id": "v2", "name": SECOND}, {"id": "v3", "name": THIRD}], (j.get("reel"), j.get("reels")))
        code, j2, _ = state(s, reel="v2")
        case("a look at the second reel: its own (empty) words, its name, its own photos in the strip, its own CapCut project",
             code == 200 and j2["reel"] == "v2" and j2["reel_name"] == SECOND and j2["w"] == {"answers": {"about": "", "who": [], "who_text": "", "where": "", "purpose": "", "purpose_text": "", "notes": ""},
                                                                                         "caption": "", "hooks": [], "picked": [], "own": ""}
             and [re.search(r"&n=(\d+)", u).group(1) for u in j2["strip"]] == ["6", "5"] and j2["kit"]["reel"] == krq.P2 and j2["kit"]["made"] is True, j2)
        case("...and it is offered a start from the reel that is answered", j2["from"] == {"id": "v1", "name": "Reel 1"} and j["from"] is None, j2.get("from"))
        code, j3, _ = state(s, reel="v3")
        case("the third reel isn't made: its page says so, whatever the others are", j3["kit"]["made"] is False and j3["kit"]["reel"] == "", j3["kit"])
        bad = [state(s, reel=r)[0] for r in ("v0", "2", "../v2", "V2")]
        code, j9, _ = state(s, reel="v9")
        case("a look naming a reel that isn't one: refused (an id by its shape: 404; a reel the shoot lacks: her words)",
             bad == [404] * 4 and code == 404 and j9["words"] == GONE, (bad, code, j9))
        # saves
        first = json.dumps(s.piece("reel"), sort_keys=True)
        code, j = save(s, reel="v2", answers={"about": "Typed for the second reel", "where": "trial"}, own="second's own")
        case("a save naming the second reel: saved under it, answered with that reel's piece",
             code == 200 and j["piece"]["own"] == "second's own" and j["piece"]["answers"]["about"] == "Typed for the second reel"
             and later(s, "v2")["answers"] == {"about": "Typed for the second reel", "where": "trial"}, (code, j))
        case("...the first reel's words exactly as they were", json.dumps(s.piece("reel"), sort_keys=True) == first)
        code, j = save(s, own="no reel named")
        case("a save naming no reel (that older page): the FIRST reel's, though another reel is open",
             code == 200 and s.piece("reel")["own"] == "no reel named" and later(s, "v2")["own"] == "second's own" and "v3" not in (pieces(s).get("reels") or {}), (code, j))
        mark = s.rec_bytes()
        code, j = save(s, reel="v9", own="nobody's")
        case("a save naming a reel the shoot doesn't have: 409 in her words, nothing written", code == 409 and j["words"] == GONE and s.rec_bytes() == mark, (code, j))
        bad = [save(s, reel=r, own="x")[0] for r in ("v0", "v", "2", "../v2", "v2 ", 2, ["v2"], {"id": "v2"}, "", None)]
        case("a reel id that isn't one by its shape: 400 each, nothing written", bad == [400] * 10 and s.rec_bytes() == mark, bad)
        code, j = save(s, "carousel", reel="v2", own="the carousel's own")
        case("a carousel's save from a page that names a reel is the carousel's (its words are the shoot's)",
             code == 200 and pieces(s)["carousel"]["own"] == "the carousel's own" and later(s, "v2")["own"] == "second's own", (code, j))
        code, j = save(s, picked=[0, 1], reel="v2")
        case("picks sent for a reel with no hooks pick nothing (the first reel's ten are not its own)", code == 200 and j["piece"]["picked"] == [] and s.piece("reel").get("picked") in (None, []), j)
        # a start from another reel
        code, j = s.http("POST", "/words-carry", {"kit": KIT, "piece": "reel", "reel": "v3", "from": "v1"})[:2]
        case("one press: the third reel starts from the first reel's answers (answers only)",
             code == 200 and j["ok"] and later(s, "v3")["answers"] == s.piece("reel")["answers"] and "caption" not in later(s, "v3"), (code, j))
        mark = s.rec_bytes()
        got = [s.http("POST", "/words-carry", b)[:2] for b in (
            {"kit": KIT, "piece": "reel", "reel": "v3", "from": "v2"},       # v3 has answers now
            {"kit": KIT, "piece": "reel", "reel": "v2", "from": "v2"},       # onto itself
            {"kit": KIT, "piece": "reel", "reel": "v2", "from": "v9"},       # from a reel that isn't
            {"kit": KIT, "piece": "reel", "from": "v2"},                     # onto no reel named
            {"kit": KIT, "piece": "carousel", "reel": "v2", "from": "v1"},   # a carousel
            {"kit": KIT, "piece": "reel", "reel": "v2", "from": "../v1"})]
        case("...never over a reel's own answers, onto itself, from a reel that isn't, or for a carousel; nothing written",
             all(not (j or {}).get("ok") for _, j in got) and [c for c, _ in got] == [200, 409, 409, 400, 400, 400] and s.rec_bytes() == mark, got)
        code, j = s.http("POST", "/words-carry", {"kit": KIT, "piece": "carousel", "reel": "v2"})[:2]
        mark = s.rec_bytes()
        code2, j2 = s.http("POST", "/words-carry", {"kit": KIT, "piece": "reel", "reel": "v2"})[:2]
        case("the carousel's 'make the reel version' from a page that names the second reel carries to that reel; and back",
             code == 200 and code2 == 200 and j2["ok"] and pieces(s)["carousel"]["answers"].get("about") == "Typed for the second reel", (code, j, code2, j2))
        # the other piece's box, and the queue step
        code, jc, _ = state(s, "carousel", reel="v2")
        code, jc1, _ = state(s, "carousel", reel="v1")
        case("the carousel's page says how its reel's words stand for the reel its address names",
             jc["other"]["caption"] is True and jc["other"]["hooks"] == 0 and jc1["other"]["hooks"] == 10 and jc["reel_name"] == SECOND, (jc["other"], jc1["other"]))
        s.http("POST", "/words-rhythm", {"text": "3 a week"})
        code, j = s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel", "reel": "v2"})[:2]
        st1, st2 = state(s, reel="v1")[1], state(s, reel="v2")[1]
        case("Add to my queue from the second reel's page adds that reel; each page shows its own reel's place",
             code == 200 and st2["queue"]["status"] == "green" and st1["queue"]["status"] != "green"
             and [x["status"] for i, x in krq.reel_pieces(s).items() if i.endswith("-reel-v2")] == ["green"], (st1["queue"], st2["queue"]))
        code, j = s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel", "reel": "v3"})[:2]
        case("...a reel that isn't made is refused, as ever", code == 409, (code, j))
    finally:
        s.stop()


# ---------- 4. the post kit ----------

def words_rows(t):
    m = re.search(r"<div class='w' data-box='words-reel'>(.*?)</ul></div>", t, re.S)
    if not m:
        return []
    out = []
    for li in re.finditer(r"<li class='go-words' role='link' tabindex='0' data-reel='(v\d+)' data-href='([^']*)'>(.*?)</li>", m.group(1), re.S):
        out.append((li.group(1), html.unescape(li.group(2)), html.unescape(re.sub(r"<[^>]+>", "|", li.group(3)))))
    return out


def check_kit(work, port):
    s = krq.fresh(work, "kit1", port)
    s.reel_made()
    s.start()
    try:
        _, t = krq.look(s)
        case("a shoot with one reel: the Your words step is the one box it always was, with no reel in its link",
             ("data-box='words-reel' role='link' tabindex='0' data-href='/words.html?kit=%s&amp;piece=reel'" % KQ) in t and "wreels'" not in t.split("<style", 1)[0] + t.split("</style>", 1)[1])
    finally:
        s.stop()
    s = krq.fresh(work, "kit3", port)
    three_reels(s)
    krq.set_made(s, "v3", krq.P3)
    chat(s, "draft", KIT, "reel", "--reel", SECOND, given={"caption": "Second caption", "hooks": HOOKS})
    chat(s, "answer", KIT, "reel", "--reel", THIRD, given={"about": "told only"})
    s.start()
    try:
        save(s, reel="v2", picked=[0, 4])
        code, t = krq.look(s)
        rows = words_rows(t)
        case("three reels: Your words lists each reel by name with where ITS words stand",
             code == 200 and [(r[0], r[2].split("|")[1], r[2].split("|")[2]) for r in rows] == [
                 ("v1", "Reel 1", ": not written yet"), ("v2", SECOND, ": caption ready · 10 hooks, 2 picked"), ("v3", THIRD, ": told, not written yet")], rows)
        case("...each row is the way to that reel's own words page",
             [r[1] for r in rows] == ["/words.html?kit=%s&reel=%s&piece=reel" % (KQ, v) for v in ("v1", "v2", "v3")], [r[1] for r in rows])
        case("...and says Write my words or Open my words by that reel's own words",
             ["Open my words" in r[2] for r in rows] == [False, True, False] and ["Write my words" in r[2] for r in rows] == [True, False, True])
        case("a reel's name with a tag in it is only ever letters there", "<b>Backdrop" not in t.split("<script", 1)[0] and html.escape(SECOND) in t)
        btn = krq.add_button(t)
        can = json.loads(html.unescape(re.search(r"data-reels='([^']*)'", btn).group(1)))
        case("Add to my queue: the caption question is about THAT reel: only the reels with no caption carry the mark",
             can == [{"id": "v1", "name": "Reel 1", "nocap": True}, {"id": "v2", "name": SECOND}, {"id": "v3", "name": THIRD, "nocap": True}]
             and "data-nocap" not in btn, (can, btn))
        chat(s, "draft", KIT, "reel", "--reel", "Reel 1", given={"caption": "First caption"})
        s.http("POST", "/words-rhythm", {"text": "3 a week"})
        s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel", "reel": "v2"})
        s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel", "reel": "v1"})
        _, t = krq.look(s)
        btn = krq.add_button(t)
        can = json.loads(html.unescape(re.search(r"data-reels='([^']*)'", btn).group(1)))
        case("...with only a captionless reel left to add, the button itself carries the mark too",
             can == [{"id": "v3", "name": THIRD, "nocap": True}] and "data-nocap='1'" in btn, (can, btn))
        src = t.split("<script", 1)[1]
        case("the page's script asks about the reel they picked, and Write my caption goes to that reel's words",
             "then(r.id, !!r.nocap)" in src and "(reel ? '&reel=' + encodeURIComponent(reel) : '')" in src)
    finally:
        s.stop()
    # the box's makers, by hand (the older way of calling still means every reel alike)
    os.environ["STUDIO_HOME"] = str(s.studio)
    sys.path.insert(0, str(SCRIPTS))
    import kit as k
    rl = [{"id": "v1", "name": "A", "made": True}, {"id": "v2", "name": "B", "made": True}]
    old_yes, old_no = k.reels_queue_box(rl, True, {}), k.reels_queue_box(rl, False, {})
    case("reels_queue_box called the older way (one yes or no for every reel) still works",
         "nocap" not in old_yes and "data-nocap='1'" in old_no and old_no.count("&quot;nocap&quot;: true") == 2)
    case("the three new lines of ours on the kit page are in OUR_KIT_WORDS, not among hers",
         all(key in k.OUR_KIT_WORDS and key not in k.KIT_WORDS for key in ("w_ready", "w_told", "w_none")))


# ---------- 5. the posting queue's panel ----------

def check_queue(work, port):
    s = krq.fresh(work, "queue", port)
    three_reels(s)
    chat(s, "draft", KIT, "reel", "--reel", "Reel 1", given={"caption": "First caption", "hooks": HOOKS})
    chat(s, "draft", KIT, "reel", "--reel", SECOND, given={"caption": "Second caption", "hooks": list(reversed(HOOKS))})
    s.start()
    try:
        save(s, reel="v1", picked=[2])
        save(s, reel="v2", picked=[0])
        s.http("POST", "/words-rhythm", {"text": "3 a week"})
        krq.add(s, reel="v1")
        krq.add(s, reel="v2")
        base = next(i for i in krq.reel_pieces(s) if i.endswith("-reel"))
        code, p1, _ = ppc.panel(s, base)
        code2, p2, _ = ppc.panel(s, base + "-v2")
        case("the panel of the first reel's post: the first reel's caption and its picked hook",
             code == 200 and p1["words"] == {"piece": "reel", "reel": "v1", "caption": "First caption", "hook": HOOKS[2]}, p1.get("words"))
        case("the panel of the second reel's post: the second reel's own",
             code2 == 200 and p2["words"] == {"piece": "reel", "reel": "v2", "caption": "Second caption", "hook": HOOKS[-1]}, p2.get("words"))
        code, raw = s.http("GET", "/posting.html")[0::2]
        case("Open my words on a reel's post goes to that reel's own words page", "(W.reel?'&reel='+encodeURIComponent(W.reel):'')" in raw.decode("utf-8"))
        # a later reel with no words of its own has no caption: never the first reel's
        krq.set_made(s, "v3", krq.P3)
        krq.add(s, reel="v3")
        code, p3, _ = ppc.panel(s, base + "-v3")
        case("a reel with no words of its own has no caption in its panel: never another reel's",
             code == 200 and p3["words"] == {"piece": "reel", "reel": "v3", "caption": "", "hook": ""}, p3.get("words"))
        s.slides_made(3)
        s.words("draft", "carousel", {"caption": "Carousel caption"})
        krq.add(s, "carousel")
        cid = next(x["id"] for x in s.posting()["pieces"] if x["id"].endswith("-carousel"))
        code, pc, _ = ppc.panel(s, cid)
        case("a carousel's panel is as it was (no reel)", code == 200 and pc["words"] == {"piece": "carousel", "reel": None, "caption": "Carousel caption", "hook": ""}, pc.get("words"))
    finally:
        s.stop()


# ---------- 6. a reminder's notes ----------

def check_reminders(work, port):
    s = krq.fresh(work, "remind", port)
    three_reels(s)
    chat(s, "draft", KIT, "reel", "--reel", "Reel 1", given={"caption": "First caption", "hooks": HOOKS})
    chat(s, "draft", KIT, "reel", "--reel", SECOND, given={"caption": "Second caption", "hooks": list(reversed(HOOKS))})
    words_module(s)
    os.environ["REMINDERS_BACKEND"] = "none"
    import reminders as rm
    base = {"id": "kit:x-reel", "kind": "reel", "kit": str(s.kit)}
    v2, v3 = dict(base, id="kit:x-reel-v2"), dict(base, id="kit:x-reel-v3")
    car = {"id": "kit:x-carousel", "kind": "carousel", "kit": str(s.kit)}
    case("which reel's words a queue piece reads is told from its own name", [rm.words_reel(x) for x in (base, v2, v3, car, {"id": "kit:x-reel-v0", "kind": "reel"})] == [None, "v2", "v3", None, None])
    n1, n2, n3 = rm.notes(base, rm.words_for(base)), rm.notes(v2, rm.words_for(v2)), rm.notes(v3, rm.words_for(v3))
    case("a reminder's notes for the first reel's post hold the first reel's caption", n1.endswith("First caption") and "Second caption" not in n1, n1)
    case("...for the second reel's post, the second reel's", n2.endswith("Second caption") and "First caption" not in n2, n2)
    case("...and for a reel with no words yet, her 'No caption yet' line, never another reel's caption", n3.endswith(rm.NO_CAPTION) and "caption" not in n3.replace(rm.NO_CAPTION, "").replace("Your caption (copy everything below):", ""), n3)
    whole = s.record()
    case("the same from the whole record in hand", rm.notes(v2, whole) == n2 and rm.notes(base, whole) == n1 and rm.notes(v3, whole) == n3 and rm.notes(car, whole).endswith(rm.NO_CAPTION))


# ---------- 7. the page itself ----------

def open_words(c, s, piece="reel", reel=None):
    c.open(s.url("/words.html?kit=" + KQ + ("&reel=" + reel if reel else "") + "&piece=" + piece))
    c.wait_for("document.querySelectorAll('#todo > li').length > 0", 10)


def check_page(c, work, port):
    s = krq.fresh(work, "page1", port)
    s.reel_made()
    s.start()
    try:
        open_words(c, s)
        case("a shoot with one reel: no list of reels on the page, the eyebrow and the lines to copy are hers",
             c.js("document.getElementById('reelsBar').hidden && document.getElementById('fromReel').hidden") is True
             and c.js("document.getElementById('talkLine').textContent") == "Ask me about the %s reel" % SHORT
             and c.js("document.getElementById('copyLine').textContent") == "Write my words for the %s reel" % SHORT
             and c.js("document.getElementById('eyebrow').textContent") == "Your words · Reel")
        c.js("(function(){var t=document.getElementById('about'); t.value='typed with one reel'; t.dispatchEvent(new Event('input',{bubbles:true}));})()")
        chrome_drive.wait_until(lambda: s.piece("reel").get("answers", {}).get("about") == "typed with one reel", 8, what="the save")
        # a second reel is started while this page is open: the words it holds are still the first reel's
        krq.new_reel(s, SECOND)
        chrome_drive.wait_until(lambda: c.js("!document.getElementById('reelsBar').hidden"), 10, what="the reels to show")
        c.js("(function(){var t=document.getElementById('notes'); t.value='typed after a second reel was started'; t.dispatchEvent(new Event('input',{bubbles:true}));})()")
        chrome_drive.wait_until(lambda: s.piece("reel").get("answers", {}).get("notes") == "typed after a second reel was started", 8, what="the save")
        case("a second reel started while the page is open: the page says it is Reel 1's, and what is typed next is still saved to the first reel",
             "reels" not in pieces(s) and c.js("document.querySelector('#reelsNav a.on').textContent") == "Reel 1"
             and c.js("document.getElementById('about').value") == "typed with one reel")
    finally:
        s.stop()

    s = krq.fresh(work, "page3", port)
    three_reels(s)
    chat(s, "answer", KIT, "reel", "--reel", "Reel 1", given={"about": "The first reel's story", "who": ["new"], "where": "feed"})
    chat(s, "draft", KIT, "reel", "--reel", "Reel 1", given={"caption": "First caption", "hooks": HOOKS})
    s.start()
    try:
        open_words(c, s, reel="v2")
        chrome_drive.wait_until(lambda: c.js("!document.getElementById('reelsBar').hidden"), 10, what="the reels to show")
        names = c.js("Array.prototype.map.call(document.querySelectorAll('#reelsNav a'), function(a){ return [a.textContent, a.className, a.getAttribute('href')]; })")
        case("the second reel's page lists the shoot's reels by name, this one marked, each a link to its own words",
             names == [["Reel 1", "", "/words.html?kit=%s&reel=v1&piece=reel" % KJ], [SECOND, "on", "/words.html?kit=%s&reel=v2&piece=reel" % KJ],
                       [THIRD, "", "/words.html?kit=%s&reel=v3&piece=reel" % KJ]], names)
        case("a reel's name with a tag in it shows as letters (no element is made from it)", c.js("document.querySelectorAll('#reelsBar b, #reelsBar script, #talkLine b').length") == 0)
        case("the page says whose words these are, and the lines to copy name the reel",
             c.js("document.getElementById('reelsSay').textContent") == "Each reel has its own caption and hooks. These are for %s." % SECOND
             and c.js("document.getElementById('talkLine').textContent") == "Ask me about the %s reel, %s" % (SHORT, SECOND)
             and c.js("document.getElementById('copyLine').textContent") == "Write my words for the %s reel, %s" % (SHORT, SECOND)
             and c.js("document.getElementById('polishWords').textContent") == "“Polish my caption for the %s reel, %s”" % (SHORT, SECOND)
             and c.js("document.getElementById('eyebrow').textContent") == "Your words · Reel · " + SECOND)
        case("a new reel starts empty: none of the first reel's answers, caption or hooks",
             c.js("document.getElementById('about').value") == "" and c.js("!!document.getElementById('caption')") is False
             and c.js("document.querySelectorAll('#hooks .hook').length") == 0)
        case("...and offers one press to start from the first reel's answers",
             c.js("!document.getElementById('fromReel').hidden") is True and c.js("document.getElementById('fromBtn').textContent") == "Use my answers from Reel 1")
        case("the tabs keep the reel", c.js("document.querySelector('#pieces a[data-piece=carousel]').getAttribute('href')") == "/words.html?kit=%s&reel=v2&piece=carousel" % KJ)
        first = json.dumps(s.piece("reel"), sort_keys=True)
        c.js("document.getElementById('fromBtn').click()")
        chrome_drive.wait_until(lambda: c.js("document.getElementById('about').value") == "The first reel's story", 10, what="the answers to arrive")
        case("the press: the first reel's answers are in this reel's boxes, saved under this reel, and the offer is gone",
             later(s, "v2").get("answers") == s.piece("reel")["answers"] and "caption" not in later(s, "v2")
             and chrome_drive.wait_until(lambda: c.js("document.getElementById('fromReel').hidden"), 8, what="the offer to go") is True)
        time.sleep(5.2)          # the page fills nothing in within 5 s of a change; let that pass before typing
        c.js("(function(){var t=document.getElementById('about'); t.value='Different for the second reel'; t.dispatchEvent(new Event('input',{bubbles:true}));})()")
        chrome_drive.wait_until(lambda: later(s, "v2").get("answers", {}).get("about") == "Different for the second reel", 8, what="the save")
        case("typing on the second reel's page is saved to the second reel, and the first reel's words are exactly as they were",
             json.dumps(s.piece("reel"), sort_keys=True) == first)
        c.js("document.querySelector('#reelsNav a[data-reel=v1]').click()")
        c.wait_for("location.search.indexOf('reel=v1') > 0 && document.querySelectorAll('#todo > li').length > 0 && !!document.getElementById('caption')", 10)
        case("the link to Reel 1 opens the first reel's own words: its story, its caption, its ten hooks",
             c.js("document.getElementById('about').value") == "The first reel's story" and c.js("document.getElementById('caption').value") == "First caption"
             and c.js("document.querySelectorAll('#hooks .hook').length") == 10 and c.js("document.getElementById('fromReel').hidden") is True)
        open_words(c, s, "carousel", reel="v2")
        chrome_drive.wait_until(lambda: c.js("!document.getElementById('other').hidden") is not None, 5, what="the page")
        case("the carousel's page shows no list of reels (its words are the shoot's), and its way to the reel's words keeps the reel",
             c.js("document.getElementById('reelsBar').hidden") is True
             and c.js("document.querySelector('#pieces a[data-piece=reel]').getAttribute('href')") == "/words.html?kit=%s&reel=v2&piece=reel" % KJ)
        c.phone()
        try:
            open_words(c, s, reel="v2")
            chrome_drive.wait_until(lambda: c.js("!document.getElementById('reelsBar').hidden"), 10, what="the reels to show")
            wide = c.js("[document.documentElement.scrollWidth - document.documentElement.clientWidth, window.innerWidth]")
            case("at a phone's width the list of reels doesn't push the page sideways", wide[0] <= 0 and wide[1] == 390, wide)
        finally:
            c.desktop()
    finally:
        s.stop()


def main():
    global ONLY
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=9965)
    ap.add_argument("--no-chrome", action="store_true", help="everything but the page in a browser")
    ap.add_argument("--only", choices=("record", "chat", "routes", "kit", "queue", "reminders", "page"))
    a = ap.parse_args()
    ONLY = a.only
    if any(p in chrome_drive.NEVER_PORTS for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="reel-words-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    try:
        if want("record"):
            group("the record", check_record, work, a.port)
        if want("chat"):
            group("the chat", check_chat, work, a.port)
        if want("routes"):
            group("the routes", check_routes, work, a.port)
        if want("kit"):
            group("the post kit", check_kit, work, a.port)
        if want("queue"):
            group("the posting queue's panel", check_queue, work, a.port)
        if want("reminders"):
            group("a reminder's notes", check_reminders, work, a.port)
        if want("page"):
            if a.no_chrome or not chrome_drive.find_chrome():
                skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
            else:
                with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                    group("the page", check_page, c, work, a.port)
    finally:
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return wpc.summary()


if __name__ == "__main__":
    sys.exit(main())
