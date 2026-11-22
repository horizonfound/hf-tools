#!/usr/bin/env python3
"""The hello engine (Nicole's v30, section 3): hello_lines.py.

    python3 tests/hello_lines_check.py

What it holds, on facts given by hand and on a small pretend Assistant it builds in a scratch STUDIO_HOME (two
post kits as records only, no photos, no page server, no Chrome; nothing of the real ~/.studio, no /Volumes):
  * her 150 lines are in the plugin exactly as she sent them (byte for byte, when her pack is on this computer);
  * every one of her lines can be said, given facts that make it true, except the "later" ones, which never are;
  * when each can show: morning / afternoon / evening by the clock, Monday and Friday and weekend greetings and
    lines only on their days, morningline and eveningline by the clock, first only before any shoot (and then
    only first), away only after 14 days, week only with two posts this week, week1 with one, a number group
    never under 2, the shoots line in the photos group filled with the shoots number, {kind} as a word;
  * {name}: filled from the Brand Homebase name, the name marked in the parts; with no name no line or greeting
    that needs one; never a line with a slot left in it; only one of the two says the name;
  * nothing reads badly together, nothing is said twice running;
  * kept for 3 hours in home-hello.json (written whole, the version before in home-hello.prev.json), a new post
    kit brings a new one sooner and the newest shoot more often, a kept hello that stopped being true is chosen
    again, a number that moved is refilled; the same seed and clock give the same hello;
  * the CLI: show and pick --dry-run keep nothing, pick keeps it.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9 and 3.12, standard library only;
a Mac and a PC alike.
"""
import json
import os
import random
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
WORK = Path(tempfile.mkdtemp(prefix="hello-lines-"))
os.environ["STUDIO_HOME"] = str(WORK / "studio")
os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, str(SCRIPTS))
import hello_lines as H  # noqa: E402

FAILED = []


def case(what, ok, detail=None):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok or detail is None else "   " + repr(detail)[:400]), flush=True)
    if not ok:
        FAILED.append(what)


def skip(what):
    print("SKIP  " + what, flush=True)


L = H.lines()
ALL = [t for v in L.values() for t in v]
LATER = set(L["later"])
WANT = [t for g, v in L.items() if g != "later" for t in v]

# a Monday, a Wednesday, a Friday, a Saturday and a Sunday of the week of Nov 16, 2026
MON, WED, FRI, SAT, SUN = (datetime(2026, 11, 16, 9, 0), datetime(2026, 11, 18, 14, 0), datetime(2026, 11, 20, 18, 30),
                           datetime(2026, 11, 21, 10, 0), datetime(2026, 11, 22, 20, 0))


def facts(name="Nicole", kits=2, top=True, n=12, week=3, kind="reel", first=False):
    f = H._empty_facts()
    f["name"] = name
    if first:
        return f
    f["any_shoot"] = True
    f["kits"] = [{"folder": "2026-11-0%d Shoot %d" % (9 - i, i), "short": "Shoot %d" % i} for i in range(kits)]
    f["kits_seen"] = sorted(k["folder"] for k in f["kits"])
    f["year"] = {"photos": n * 100, "shoots": n, "shared": n - 1, "reels": n, "carousels": n, "posted": n, "hours": n}
    f["top"] = {"folder": f["kits"][-1]["folder"], "short": f["kits"][-1]["short"]} if top and kits else None
    f["posted_week"] = [{"kind": kind} for _ in range(week)]
    return f


def reset():
    for p in (H.STATE, H.STATE_PREV):
        try:
            p.unlink()
        except OSError:
            pass


def many(f, now, tries=1500, seed0=0, **kw):
    """(greeting templates, line templates, answers) over many fresh picks, keeping nothing."""
    gs, ls, outs = Counter(), Counter(), []
    for s in range(seed0, seed0 + tries):
        reset()
        rng = random.Random(s)
        c = H.choose(f, now, rng, **kw)
        gs[c["greeting_t"]] += 1
        ls[c["line_t"]] += 1
        outs.append((c, H._answer(c, f, now, False)))
    return gs, ls, outs


# ---------- the data ----------

def check_data():
    case("her lines: 150 in all, 25 groups, every one a string", len(ALL) == 150 and len(L) == 25, (len(ALL), len(L)))
    case("her lines: curly apostrophes kept (no straight one anywhere)", "’" in "".join(ALL) and "'" not in "".join(ALL))
    case("her lines: no em dash in any of them", "—" not in "".join(ALL))
    pack = None
    for r in (ROOT / "reference-private", ROOT.parent / "hf-tools" / "reference-private"):
        for p in sorted(r.glob("nicole-handoff-v30-*/hellos/approved-hellos-by-when.json")):
            pack = p
    if pack:
        case("her file is in the plugin byte for byte", pack.read_bytes() == H.DATA.read_bytes())
        app = json.loads((pack.parent / "approved-hellos.json").read_text(encoding="utf-8"))["approved"]
        case("... and the 150 are exactly her approved list", sorted(app) == sorted(ALL))
    else:
        skip("her pack is not on this computer (reference-private/ is never pushed)")
    bad = [t for t in ALL if re.search(r"\b(waiting|due|late|pressure|back up|still up|remind)\b", t, re.I)]
    case("no reminder words in any line", not bad, bad)


# ---------- every line can be said, but later ----------

def check_every_line():
    said = set()
    scenarios = [
        (facts(), MON), (facts(), WED), (facts(), FRI), (facts(), SAT), (facts(), SUN),
        (facts(kind="carousel"), datetime(2026, 11, 18, 12, 30)),
        (facts(first=True), MON), (facts(name="", first=True), FRI),
    ]
    for f, now in scenarios:
        gs, ls, _ = many(f, now, tries=1500)
        said |= set(gs) | set(ls)
    for f, now in ((facts(), MON), (facts(), SUN)):
        gs, ls, _ = many(f, now, tries=1500, seed0=5000, away=True)
        said |= set(gs) | set(ls)
    missing = [t for t in WANT if t not in said]
    case("every one of her lines can be said, given facts that make it true (%d of %d)" % (len(WANT) - len(missing), len(WANT)),
         not missing, missing)
    case("no 'later' line is ever said", not (said & LATER), sorted(said & LATER))


# ---------- when each can show ----------

def check_when():
    by = {g: set(v) for g, v in L.items()}
    for now, part in ((datetime(2026, 11, 18, 7, 0), "morning"), (datetime(2026, 11, 18, 11, 59), "morning"),
                      (datetime(2026, 11, 18, 12, 0), "afternoon"), (datetime(2026, 11, 18, 16, 59), "afternoon"),
                      (datetime(2026, 11, 18, 17, 0), "evening"), (datetime(2026, 11, 18, 23, 30), "evening")):
        gs = {g for g, _ in H.greetings(facts(), now)}
        others = {"morning", "afternoon", "evening"} - {part}
        case("at %s only the %s greetings by the clock" % (now.strftime("%H:%M"), part), part in gs and not (gs & others), gs)
    for now, label in ((MON, "Monday"), (WED, "Wednesday"), (FRI, "Friday"), (SAT, "Saturday"), (SUN, "Sunday")):
        ts = {t for _, t in H.greetings(facts(), now)}
        case("%s: Happy Monday only on a Monday" % label, ("Happy Monday, {name}." in ts) == (label == "Monday"))
        case("%s: Happy Friday only on a Friday" % label, ("Happy Friday, {name}!" in ts) == (label == "Friday"))
        case("%s: Happy weekend only on a Saturday or Sunday" % label, ("Happy weekend, {name}." in ts) == (label in ("Saturday", "Sunday")))
        case("%s: Happy {day} any day" % label, "Happy {day}, {name}." in ts)
        groups = {g for _, g, _, _ in H.line_pool(facts(), now)}
        case("%s: the monday lines only on a Monday" % label, ("monday" in groups) == (label == "Monday"))
        case("%s: the friday line only on a Friday" % label, ("friday" in groups) == (label == "Friday"))
        case("%s: the weekend line Friday to Sunday" % label, ("weekend" in groups) == (label in ("Friday", "Saturday", "Sunday")))
        case("%s: anyday and warm any day" % label, {"anyday", "warm"} <= groups)
    for hr, mo, ev in ((9, True, False), (13, False, False), (19, False, True)):
        g = {x for _, x, _, _ in H.line_pool(facts(), datetime(2026, 11, 18, hr))}
        case("%d:00: morningline %s, eveningline %s" % (hr, mo, ev), ("morningline" in g) == mo and ("eveningline" in g) == ev, g)
    # first
    g = {x for _, x, _, _ in H.line_pool(facts(first=True), WED)}
    case("before any shoot, only the first lines", g == {"first"}, g)
    case("with a shoot, never a first line", "first" not in {x for _, x, _, _ in H.line_pool(facts(), WED)})
    gt = {t for _, t in H.greetings(facts(first=True), WED)}
    case("before any shoot, no greeting says back or again", not [t for t in gt if re.search(r"\b(back|again)\b", t)] and gt, gt)
    _, ls, _ = many(facts(first=True), WED, tries=300)
    case("before any shoot, the line said is always a first line", set(ls) <= by["first"], set(ls))
    # away
    case("away lines only when away", "away" not in {x for _, x, _, _ in H.line_pool(facts(), WED)}
         and "away" in {x for _, x, _, _ in H.line_pool(facts(), WED, away=True)})
    # newest, top
    case("no newest line without a post kit", "newest" not in {x for _, x, _, _ in H.line_pool(facts(kits=0), WED)})
    case("no top line without a most-loved shoot", "top" not in {x for _, x, _, _ in H.line_pool(facts(top=False), WED)})
    p = H.line_pool(facts(), WED)
    case("the newest line names the newest kit", {s.get("kit") for _, x, _, s in p if x == "newest"} == {"2026-11-09 Shoot 0"})
    # the numbers
    for n, there in ((0, False), (1, False), (2, True)):
        g = {x for _, x, _, _ in H.line_pool(facts(n=n, week=0), WED)}
        nums = {"photos", "shoots", "reels", "carousels", "posted", "hours"}
        if n == 0:
            case("numbers at 0: no number line", not (g & nums), g & nums)
        elif n == 1:
            f = facts(n=1, week=0)
            f["year"]["photos"] = 1
            g = {x for _, x, _, _ in H.line_pool(f, WED)}
            case("numbers at 1: no number line (never '1 reels')", not (g & nums), g & nums)
        else:
            f = facts(n=2, week=0)
            f["year"]["shared"] = 2
            g = {x for _, x, _, _ in H.line_pool(f, WED)}
            case("numbers at 2: every number group can show", nums <= g, nums - g)
    f = facts(n=5, week=0)
    f["year"].update(photos=1234, shoots=7, shared=3, hours=1)
    texts = {H.fill(t, f, WED, s)[0] for _, x, t, s in H.line_pool(f, WED)}
    case("photos: written 1,234", "You’ve finished 1,234 photos this year. Incredible." in texts)
    case("the shoots line in the photos group says the shoots number",
         "7 shoots this year. That’s a lot of people with photos they’ll keep forever." in texts)
    case("'turned into posts' says the shoots something was made from", "3 shoots turned into posts. That’s amazing." in texts)
    case("an hour saved is not '1 hours'", not any("hours this year" in t for t in texts))
    # this week
    g = lambda f: {x for _, x, _, _ in H.line_pool(f, WED)}  # noqa: E731
    case("no posts this week: no week or week1 line", not ({"week", "week1"} & g(facts(week=0))))
    case("one post this week: week1 but not week", "week1" in g(facts(week=1)) and "week" not in g(facts(week=1)))
    case("two posts this week: both", {"week", "week1"} <= g(facts(week=2)))
    for kind, word in (("reel", "reel"), ("carousel", "carousel"), ("post", "post")):
        f = facts(week=1, kind=word)
        t = [H.fill(t, f, WED, s)[0] for _, x, t, s in H.line_pool(f, WED) if "{kind}" in t]
        case("{kind}: 'You shared your %s this week.'" % word, t == ["You shared your %s this week. Love that for you." % word], t)


# ---------- names, slots and reading well ----------

def check_names_slots():
    _, _, outs = many(facts(), WED, tries=600)
    bad = [o for _, o in outs if "{" in o["greeting"] + o["line"] or "  " in o["greeting"] + o["line"]]
    case("never a slot left in a hello", not bad, bad[:2])
    ok = all("".join(p["text"] for p in o["greeting_parts"]) == o["greeting"] and "".join(p["text"] for p in o["line_parts"]) == o["line"]
             for _, o in outs)
    case("the parts put together are the words", ok)
    named = [o for _, o in outs if "{name}" in _["greeting_t"] or "{name}" in _["line_t"]]
    case("the name is filled and marked as the name", named and all(any(p["name"] and p["text"] == "Nicole" for p in o["greeting_parts"] + o["line_parts"]) for o in named))
    case("the name is never both in the greeting and the line", not [c for c, _ in outs if "{name}" in c["greeting_t"] and "{name}" in c["line_t"]])
    case("nothing else is marked as the name", all(p["text"] == "Nicole" for _, o in outs for p in o["greeting_parts"] + o["line_parts"] if p["name"]))
    _, _, outs = many(facts(name=""), WED, tries=600)
    case("with no name, no greeting or line that needs one", not [c for c, _ in outs if "{name}" in c["greeting_t"] + c["line_t"]])
    gs = {t for _, t in H.greetings(facts(name=""), WED)}
    case("with no name the greetings are hers without a name", gs == {t for t in L["greet"] if "{name}" not in t}, gs)
    _, _, outs = many(facts(), FRI, tries=900)
    clashing = [(c["greeting_t"], c["line_t"]) for c, _ in outs if H.clash(c["greeting_t"], c["line_t"])]
    case("nothing that reads badly together is said (900 hellos on a Friday evening)", not clashing, clashing[:3])
    case("'Happy Friday, Nicole!' never comes with 'Happy Friday. You earned it.'",
         not [c for c, _ in outs if c["greeting_t"].startswith("Happy") and c["line_t"].startswith("Happy")])
    case("'Hi, ... So glad you’re here.' never with the warm 'So glad you’re here.'",
         H.clash("Hi, {name}. So glad you’re here.", "So glad you’re here."))
    case("the day is the computer's own weekday",
         H.fill("Happy {day}, {name}.", facts(), WED, {})[0] == "Happy Wednesday, Nicole.")
    case("a slot with nothing to put in it is never filled", H.fill("{shoot} looks so beautiful.", facts(), WED, {}) is None
         and H.fill("{n} reels this year. Look at you go.", facts(), WED, {}) is None)


# ---------- kept for a visit ----------

def check_kept():
    reset()
    f = facts()
    t0 = datetime(2026, 11, 18, 14, 0)
    a = H.pick(now=t0, rng=random.Random(1), facts=f)
    case("a hello is kept in home-hello.json", H.STATE.is_file() and json.loads(H.STATE.read_text(encoding="utf-8"))["chosen"]["line_t"])
    b = H.pick(now=t0 + timedelta(hours=1), rng=random.Random(99), facts=f)
    case("an hour later (a reload) the same hello", b["greeting"] == a["greeting"] and b["line"] == a["line"] and b["kept"] and not a["kept"])
    case("... and the version before is kept beside it", H.STATE_PREV.is_file()
         and json.loads(H.STATE_PREV.read_text(encoding="utf-8"))["chosen"]["line_t"] == json.loads(H.STATE.read_text(encoding="utf-8"))["chosen"]["line_t"])
    c = H.pick(now=t0 + timedelta(hours=2, minutes=59), rng=random.Random(98), facts=f)
    case("2 hours 59 later still the same", c["line"] == a["line"] and c["kept"])
    d = H.pick(now=t0 + timedelta(hours=3, minutes=1), rng=random.Random(97), facts=f)
    case("3 hours later a new one, not the same greeting or line", not d["kept"] and d["greeting"] != a["greeting"] and d["line"] != a["line"], (a, d))
    # never twice running, over many visits
    reset()
    prev, twice = None, []
    for i in range(200):
        o = H.pick(now=t0 + timedelta(hours=4 * i), rng=random.Random(i), facts=f)
        if prev and (o["greeting"] == prev["greeting"] or o["line"] == prev["line"]):
            twice.append((prev, o))
        prev = o
    case("200 visits, never the same greeting or line twice running", not twice, twice[:1])
    # a new post kit
    reset()
    f = facts(kits=2)
    a = H.pick(now=t0, rng=random.Random(5), facts=f)
    g = facts(kits=3)
    g["kits"] = [{"folder": "2026-11-20 Brand new", "short": "Brand new"}] + f["kits"]
    g["kits_seen"] = sorted(k["folder"] for k in g["kits"])
    b = H.pick(now=t0 + timedelta(minutes=20), rng=random.Random(6), facts=g)
    case("a new post kit coming in brings a new hello before 3 hours", not b["kept"])
    c = H.pick(now=t0 + timedelta(minutes=40), rng=random.Random(7), facts=g)
    case("... which is then kept", c["kept"] and c["line"] == b["line"])
    boosted = plain = 0
    for s in range(600):
        boosted += H.choose(g, t0, random.Random(s), new_kit="2026-11-20 Brand new")["group"] == "newest"
        plain += H.choose(g, t0, random.Random(s))["group"] == "newest"
    case("just after a new kit, the newest shoot comes up more often (%d against %d of 600)" % (boosted, plain), boosted > plain * 1.5)
    # stops being true
    reset()
    f = facts()
    mornings = None
    for s in range(400):
        reset()
        o = H.pick(now=datetime(2026, 11, 18, 11, 30), rng=random.Random(s), facts=f)
        if o["greeting_group"] == "morning":
            mornings = o
            break
    if mornings:
        n = H.pick(now=datetime(2026, 11, 18, 12, 10), rng=random.Random(1), facts=f)
        case("a 'Good morning' kept past noon is chosen again", not n["kept"] and n["greeting_group"] != "morning", n)
    else:
        case("a morning greeting was found to test with", False)
    reset()
    shoot = None
    for s in range(400):
        reset()
        o = H.pick(now=t0, rng=random.Random(s), facts=f)
        if o["group"] == "newest":
            shoot = o
            break
    g = facts()
    g["kits"] = g["kits"][1:]
    n = H.pick(now=t0 + timedelta(minutes=5), rng=random.Random(2), facts=g)
    case("a hello about a shoot that has gone (archived) is chosen again", shoot and not n["kept"] and n["shoot"] != shoot["shoot"], n)
    reset()
    reels = None
    for s in range(800):
        reset()
        o = H.pick(now=t0, rng=random.Random(s), facts=f)
        if o["group"] == "reels":
            reels = o
            break
    g = facts()
    g["year"]["reels"] = 40
    n = H.pick(now=t0 + timedelta(minutes=5), rng=random.Random(2), facts=g)
    case("a kept number line is refilled with the new number, the same hello", reels and n["kept"] and "40" in n["line"] and n["greeting"] == reels["greeting"], (reels, n))
    # away
    reset()
    H.save_state({"last_visit": H._iso(t0 - timedelta(days=15))})
    pool_away = H.line_pool(f, t0, away=True)
    hits = 0
    for s in range(60):
        reset()
        H.save_state({"last_visit": H._iso(t0 - timedelta(days=15))})
        hits += H.pick(now=t0, rng=random.Random(s), facts=f)["group"] == "away"
    case("15 days since the last visit: the away lines come up (%d of 60)" % hits, hits > 5 and pool_away)
    none = 0
    for s in range(200):
        reset()
        H.save_state({"last_visit": H._iso(t0 - timedelta(days=13))})
        none += H.pick(now=t0, rng=random.Random(s), facts=f)["group"] == "away"
    case("13 days: never an away line", none == 0)
    reset()
    H.pick(now=t0, rng=random.Random(1), facts=f)
    st = json.loads(H.STATE.read_text(encoding="utf-8"))
    case("the last visit is kept", st["last_visit"] == H._iso(t0))
    # the same seed and clock, the same hello
    reset()
    a = H.pick(now=t0, rng=random.Random(42), facts=f, write=False)
    reset()
    b = H.pick(now=t0, rng=random.Random(42), facts=f, write=False)
    case("the same seed and clock give the same hello", a == b)
    case("write=False keeps nothing", not H.STATE.exists())
    # a broken record is not the end of the hello
    H.HOME.mkdir(parents=True, exist_ok=True)
    H.STATE.write_text("{not json", encoding="utf-8")
    o = H.pick(now=t0, rng=random.Random(3), facts=f)
    case("an unreadable home-hello.json: a hello still comes, and the file is whole again",
         o and json.loads(H.STATE.read_text(encoding="utf-8")).get("chosen"))
    reset()


# ---------- the facts, from a pretend Assistant ----------

def put(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")


def check_gather():
    home = H.HOME
    assistant = WORK / "The Assistant"
    content = assistant / "Your Content"
    put(home / "studio.json", {"posts": {"home": str(assistant)}})
    (assistant / "brand-homebase.md").parent.mkdir(parents=True, exist_ok=True)
    (assistant / "brand-homebase.md").write_text("# Brand Homebase\n\n- Name / business: Nicole Hill Photography\n", encoding="utf-8")
    ts = lambda s: datetime.fromisoformat(s).timestamp()  # noqa: E731
    for folder, date_, made in (("2026-10-14 Aurora", "2026-10-14", 3), ("2026-11-09 Hannah", "2026-11-09", 1)):
        d = content / folder
        (d / "Photos").mkdir(parents=True, exist_ok=True)
        put(d / ".kit" / "kit.json", {"name": folder, "date": date_})
        put(d / ".kit" / "reel-page.json", {"v": 1, "made": [{"project": "%s reel %d" % (folder, i), "when": ts("2026-11-0%dT10:00:00" % (i + 1)),
                                                              "version": "v%d" % (i + 1)} for i in range(made)]})
    put(home / "posting.json", {"interval": 3, "pieces": [
        {"id": "p1", "shoot_name": "Hannah", "kind": "reel", "status": "posted", "posted_at": "2026-11-17T18:00:00"},
        {"id": "p2", "shoot_name": "Aurora", "kind": "single", "status": "posted", "posted_at": "2026-11-18T09:00:00"},
        {"id": "p3", "shoot_name": "Aurora", "kind": "carousel", "status": "posted", "posted_at": "2026-11-15T09:00:00"},
        {"id": "p4", "shoot_name": "Aurora", "kind": "carousel", "status": "green", "date": "2026-11-25"}]})
    f = H.gather(datetime(2026, 11, 18, 14, 0))
    case("gather: the name from the Brand Homebase", f["name"] == "Nicole", f["name"])
    case("gather: the post kits, newest first, named without their dates",
         [k["short"] for k in f["kits"]] == ["Hannah", "Aurora"], f["kits"])
    case("gather: there is a shoot", f["any_shoot"])
    case("gather: this year's reels (each reel once)", f["year"]["reels"] == 4, f["year"])
    case("gather: the most-loved shoot is the one most was made from", (f["top"] or {}).get("short") == "Aurora", f["top"])
    case("gather: posted this week is Monday on, newest first, a single post read as 'post'",
         [x["kind"] for x in f["posted_week"]] == ["post", "reel"], f["posted_week"])
    case("gather: a post from last Sunday is not this week", len(f["posted_week"]) == 2)
    reset()
    o = H.pick(now=datetime(2026, 11, 18, 14, 0), rng=random.Random(1))
    case("pick on the pretend Assistant gives a hello", o and o["greeting"] and o["line"], o)
    # the CLI
    reset()
    env = dict(os.environ)
    r = subprocess.run([sys.executable, str(SCRIPTS / "hello_lines.py"), "show"], capture_output=True, text=True, env=env, encoding="utf-8", timeout=60)
    case("CLI show answers and keeps nothing", r.returncode == 0 and json.loads(r.stdout)["facts"]["name"] == "Nicole" and not H.STATE.exists(), r.stderr[-300:])
    r = subprocess.run([sys.executable, str(SCRIPTS / "hello_lines.py"), "pick", "--now", "2026-11-18T14:00", "--seed", "3", "--dry-run"],
                       capture_output=True, text=True, env=env, encoding="utf-8", timeout=60)
    case("CLI pick --dry-run answers and keeps nothing", r.returncode == 0 and json.loads(r.stdout)["line"] and not H.STATE.exists(), r.stderr[-300:])
    r = subprocess.run([sys.executable, str(SCRIPTS / "hello_lines.py"), "pick", "--now", "2026-11-18T14:00", "--seed", "3"],
                       capture_output=True, text=True, env=env, encoding="utf-8", timeout=60)
    case("CLI pick keeps it", r.returncode == 0 and H.STATE.is_file())
    r = subprocess.run([sys.executable, str(SCRIPTS / "hello_lines.py"), "pick", "--now", "tomorrow"], capture_output=True, text=True, env=env, encoding="utf-8", timeout=60)
    case("CLI pick with a time it can't read says so", r.returncode == 2 and "--now" in r.stdout)
    path_bits = [str(WORK), str(content), "/Users/", "\\"]
    out = json.dumps(H.pick(now=datetime(2026, 11, 18, 15, 0), rng=random.Random(4), fresh=True))
    case("no path in what the page gets", not any(b in out for b in path_bits), out[:200])
    reset()


def main():
    try:
        check_data()
        check_every_line()
        check_when()
        check_names_slots()
        check_kept()
        check_gather()
    finally:
        real = Path.home() / ".studio"
        case("the real ~/.studio was never the home here", Path(os.environ["STUDIO_HOME"]) != real and H.HOME != real)
    print("%s: %d failed" % ("FAILED" if FAILED else "OK", len(FAILED)), flush=True)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
