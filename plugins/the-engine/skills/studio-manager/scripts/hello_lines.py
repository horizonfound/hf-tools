#!/usr/bin/env python3
"""The hello at the top of the home page (Nicole's v30, Nov 21, section 3): it only lifts them up.

"The header should only be used to pump them up. It should be inspirational... nothing should ever be making
them feel pressure. Ever." So the hello is one greeting on top plus one line under it, made ONLY from her 150
approved lines (../hellos/approved-hellos-by-when.json, her file exactly as she sent it, curly apostrophes and
all). No reminders of any kind, no button, no "Another hello".

When each can show (her by-when groups):
  greeting  greet any time; morning (before noon), afternoon (noon to 5), evening (5 on) by this computer's own
            clock; greetday by the day: "Happy Monday" only on a Monday, "Happy Friday" only on a Friday,
            "Happy weekend" only on a Saturday or Sunday, "Happy {day}" any day.
  line      newest   their newest post kit (more often just after a new one comes in)
            top      the shoot most was made from this year (wrapped.py), when two or more shoots had something
                     made and that one had two things or more
            photos, shoots, reels, carousels, posted, hours   this year's numbers (wrapped.py); a group whose
                     number is under 2 is left out, so nothing ever reads "1 reels"
            week     two posts or more marked posted this week (Monday to now, posting.json posted_at)
            week1    any post this week; {kind} is what the newest one was (reel, carousel, post)
            monday, friday   only that day; weekend   Friday to Sunday (hers: "Hope your weekend is a good one")
            anyday   any day; morningline before noon; eveningline from 5
            warm     any day, for anyone
            first    only before any shoot (no post kit and no backup): then the line is always one of these
            away     only when the last visit was 14 days ago or more
            later    left out (her note allows it: they need counts we do not keep yet)
  {name}   their name from the Brand Homebase (what the home page's hello already uses, wrapped.gather "me");
           with no name, only lines without {name}. {shoot} a post kit's name without its date; {n} a number
           written 1,234; {day} the weekday; {kind} a kind of post. A line with a slot that can't be filled is
           never shown.

Ours, where her rules are silent (each a draft for Dustin and Nicole):
  * a greeting and a line never start with the same word or share two words in a row ("Happy Friday, Nicole!"
    then "Happy Friday. You earned it." never come together), and only one of the two says the name;
  * before any shoot, no greeting that says "back" or "again" (nobody has been here before);
  * never the same greeting or the same line twice running (and the last few are passed over while others fit).

The very first hello (Nicole, Nov 22: "when they first log in everyones should say this only Hi! I'm your
Assistant, and I'm so glad you're here."): before any shoot, and when the page has never greeted them (no visit kept
in home-hello.json), the page shows ONLY that one line of hers (FIRST_ONLY), with no greeting over it, whatever
their name; the answer says "only": true and its greeting is empty. It is kept for its 3 hours like any hello; after
that the hello works as before.

The same hello is kept for 3 hours (KEEP_HOURS) in ~/.studio/home-hello.json, written whole, the version before
kept as home-hello.prev.json, so reloading the page keeps it; it is chosen again sooner when a post kit that was
not there before comes in, or when the kept one stops being true (the morning is over, a shoot it named has
gone, a number changed it is refilled with the new number). The same file keeps the last visit, for "away".

For the page (stage B wires it): pick() answers {greeting, line, greeting_parts, line_parts, name, group,
greeting_group, kit, shoot, chosen_at, keep_until, kept, only}. *_parts are [{"text": ..., "name": true|false}], so the
page can colour the name with textContent alone (no HTML from here, ever). kit is a post kit's FOLDER NAME (never a
path), for the photos behind the hello.

    python3 hello_lines.py show               what is true for them now, the groups that can show, the kept hello
                                              (changes nothing)
    python3 hello_lines.py pick [--now 2026-11-21T09:30] [--seed N] [--fresh] [--dry-run]
                                              the hello the home page would show (and keeps it, unless --dry-run)

Python 3.9, standard library only; a Mac and a PC alike.
"""
import argparse
import json
import os
import random
import re
import sys
import threading
from datetime import datetime, date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
STATE = HOME / "home-hello.json"
STATE_PREV = HOME / "home-hello.prev.json"
DATA = HERE.parent / "hellos" / "approved-hellos-by-when.json"

KEEP_HOURS = 3                  # hers: "the same hello for a whole visit. Keep it for about 3 hours"
AWAY_DAYS = 14                  # hers: "only when they come back after two weeks or more"
LEFT_OUT = ("later",)           # hers: "Leave them out until you have that count"
GREET_GROUPS = ("greet", "morning", "afternoon", "evening", "greetday")
RECENT = 4                      # the last few greetings and lines are passed over while others fit
NOON, EVENING = 12, 17          # hers (hr < 12 morning, < 17 afternoon, else evening)

# how often each group of lines comes up, against the others that are true (hers, from her mock-up's weights;
# a group's weight is shared among its lines). newest_new is the newest shoot just after it came in.
WEIGHTS = {"newest": 4, "newest_new": 12, "top": 1, "photos": 1.5, "shoots": 1, "reels": 1, "carousels": 0.7,
           "posted": 0.7, "hours": 0.8, "week": 2, "week1": 1.5, "warm": 3, "monday": 1, "friday": 1, "weekend": 0.6,
           "anyday": 0.4, "morningline": 0.5, "eveningline": 0.6, "away": 6, "first": 1}

# The one line the very first hello says, alone (Nicole, Nov 22): found among her "first" lines by these words, so
# the text shown is always hers exactly as she sent it (curly apostrophes and all).
FIRST_ONLY_HAS = "so glad you"

KIND_WORDS = {"reel": "reel", "carousel": "carousel", "single": "post", "story": "stories", "stories": "stories"}

_LOCK = threading.Lock()
_LINES = None


def say(msg):
    try:
        print(msg, flush=True)
    except (BrokenPipeError, OSError):
        pass


def lines():
    """Her groups, exactly as she sent them (read once)."""
    global _LINES
    if _LINES is None:
        d = json.loads(DATA.read_text(encoding="utf-8"))
        _LINES = {k: [t for t in v if isinstance(t, str)] for k, v in d.items() if isinstance(v, list)}
    return _LINES


# ---------- what is true for them ----------

def _empty_facts():
    return {"name": "", "kits": [], "kits_seen": [], "any_shoot": False,
            "year": {"photos": 0, "shoots": 0, "shared": 0, "reels": 0, "carousels": 0, "posted": 0, "hours": 0},
            "top": None, "posted_week": []}


def gather(now=None):
    """What the hello is made from, read from what the Assistant already keeps (wrapped.py's one read of the
    records, home_base.kits for the newest kit, the posting queue). Each part fails soft. Names and numbers only."""
    now = now or datetime.now()
    day = now.date()
    f = _empty_facts()
    got = None
    try:
        import wrapped
        got = wrapped.gather()
        f["name"] = str(got.get("me") or "").strip()
        f["any_shoot"] = bool([k for k in got.get("kits") or [] if not k.get("vault")] or got.get("backups"))
    except (Exception, SystemExit):  # noqa: BLE001
        got = None
    try:
        import home_base
        import look
        every = home_base.kits()                      # newest first; the vault is never one of them
        f["kits_seen"] = sorted(k["folder"] for k in every)
        f["kits"] = [{"folder": k["folder"], "short": look.short_name(k["folder"]) or k["folder"]}
                     for k in every if not k.get("archived")]
        if every:
            f["any_shoot"] = True
    except (Exception, SystemExit):  # noqa: BLE001
        pass
    if got:
        try:
            import wrapped
            y = wrapped.data(year=str(day.year), got=got, day=day)
            t = y["totals"]
            made = lambda s: s["reels"] + s["carousels"] + s["stories"]  # noqa: E731
            worked = [s for s in y["shoots"] if made(s)]
            f["year"] = {"photos": int(t.get("photos") or 0), "shoots": int(t.get("photo_shoots") or 0),
                         "shared": int(t.get("made_shoots", t.get("shared_shoots")) or 0),   # made from, as "{n} shoots turned into posts" says (the recap's "shared" is posted only since Nov 23)
                         "reels": int(t.get("reels") or 0),
                         "carousels": int(t.get("carousels") or 0), "posted": int(t.get("posted") or 0),
                         "hours": int(round((t.get("minutes_saved") or 0) / 60.0))}
            top = next((s for s in worked if s["name"] == y.get("top")), None)
            if top and len(worked) >= 2 and made(top) >= 2:
                f["top"] = {"folder": top["name"], "short": top["short"]}
        except (Exception, SystemExit):  # noqa: BLE001
            pass
    try:
        f["posted_week"] = posted_this_week(now)
    except (Exception, SystemExit):  # noqa: BLE001
        pass
    return f


def posted_this_week(now):
    """The posts marked posted since Monday of this week (by this computer's clock), newest first: [{"kind"}]."""
    import posting_queue
    p = posting_queue.load()
    monday = (now.date() - timedelta(days=now.weekday())).isoformat()
    upto = now.isoformat(timespec="seconds")
    out = []
    for x in p.get("pieces") or []:
        if not isinstance(x, dict) or x.get("status") != "posted":
            continue
        at = x.get("posted_at")
        if isinstance(at, str) and monday <= at[:10] and at[:19] <= upto:
            out.append((at, KIND_WORDS.get(x.get("kind"), "post")))
    out.sort(reverse=True)
    return [{"kind": k} for _, k in out]


# ---------- which greetings and lines are true right now ----------

def part_of_day(now):
    return "morning" if now.hour < NOON else "afternoon" if now.hour < EVENING else "evening"


def _count_for(group, template, facts):
    """The number a line is about. Two of her lines speak of a number other than their group's: "{n} shoots this
    year..." (in photos) is the shoots count, and "{n} shoots turned into posts" the shoots something was made from."""
    y = facts["year"]
    if "{n} shoots turned into posts" in template:
        return y["shared"]
    if "{n} shoots" in template:
        return y["shoots"]
    if group == "week":
        return len(facts["posted_week"])
    return y.get(group, 0)


def greetings(facts, now, away=False):
    """[(group, template)] for the greetings that are true now."""
    L = lines()
    wd = now.weekday()                      # Monday 0 .. Sunday 6
    out = [("greet", t) for t in L.get("greet", [])]
    out += [(part_of_day(now), t) for t in L.get(part_of_day(now), [])]
    for t in L.get("greetday", []):
        if "Monday" in t and wd != 0:
            continue
        if "Friday" in t and wd != 4:
            continue
        if "weekend" in t and wd not in (5, 6):
            continue
        out.append(("greetday", t))
    if not facts["any_shoot"]:              # ours: a first visit is nobody's "welcome back"
        out = [(g, t) for g, t in out if not re.search(r"\b(back|again)\b", t)]
    return [(g, t) for g, t in out if facts["name"] or "{name}" not in t]


def line_pool(facts, now, away=False, new_kit=None):
    """[(weight, group, template, slots)] for the lines that are true now. slots: {"shoot", "kit", "n", "kind"}."""
    L = lines()
    wd, hr = now.weekday(), now.hour
    pool = []

    def add(key, slots=None, weight_key=None):
        ts = [t for t in L.get(key, []) if facts["name"] or "{name}" not in t]
        out = []
        for t in ts:
            s = dict(slots or {})
            if "{n}" in t:
                n = _count_for(key, t, facts)
                if n < 2:
                    continue
                s["n"] = n
            out.append((t, s))
        w = WEIGHTS[weight_key or key]
        for t, s in out:
            pool.append((w / len(out), key, t, s))

    if not facts["any_shoot"]:
        add("first")
        return pool
    if away:
        add("away")
    if facts["kits"]:
        k = facts["kits"][0]
        add("newest", {"shoot": k["short"], "kit": k["folder"]}, "newest_new" if new_kit == k["folder"] else "newest")
    if facts["top"]:
        add("top", {"shoot": facts["top"]["short"], "kit": facts["top"]["folder"]})
    for g in ("photos", "shoots", "reels", "carousels", "posted", "hours"):
        add(g)
    pw = facts["posted_week"]
    if len(pw) >= 2:
        add("week")
    if pw:
        add("week1", {"kind": pw[0]["kind"]})
    add("warm")
    if wd == 0:
        add("monday")
    if wd == 4:
        add("friday")
    if wd in (4, 5, 6):
        add("weekend")
    add("anyday")
    if hr < NOON:
        add("morningline")
    if hr >= EVENING:
        add("eveningline")
    return pool


# ---------- filling the slots ----------

def fill(template, facts, now, slots):
    """(text, parts) with every slot filled, or None when one can't be (never a line with a hole in it)."""
    vals = {"name": facts["name"], "day": now.strftime("%A"), "shoot": slots.get("shoot") or "",
            "kind": slots.get("kind") or "", "n": ("{:,}".format(slots["n"]) if isinstance(slots.get("n"), int) else "")}
    parts, text = [], ""
    for bit in re.split(r"(\{[a-z]+\})", template):
        if not bit:
            continue
        m = re.fullmatch(r"\{([a-z]+)\}", bit)
        if m:
            v = vals.get(m.group(1))
            if not v:
                return None
            parts.append({"text": v, "name": m.group(1) == "name"})
        elif parts and not parts[-1]["name"]:
            parts[-1]["text"] += bit
        else:
            parts.append({"text": bit, "name": False})
        text += v if m else bit
    # neighbouring plain bits are one part
    merged = []
    for p in parts:
        if merged and not merged[-1]["name"] and not p["name"]:
            merged[-1]["text"] += p["text"]
        else:
            merged.append(dict(p))
    return text, merged


def _words(t):
    return re.findall(r"[a-z]+", t.replace("{name}", " ").replace("’", "").replace("'", "").lower())


def clash(greeting_t, line_t):
    """Ours: the two would read badly together (the same first word, two words in a row shared, or both saying
    the name)."""
    if "{name}" in greeting_t and "{name}" in line_t:
        return True
    a, b = _words(greeting_t), _words(line_t)
    if a and b and a[0] == b[0]:
        return True
    pairs = lambda w: {(w[i], w[i + 1]) for i in range(len(w) - 1)}  # noqa: E731
    return bool(pairs(a) & pairs(b))


# ---------- the kept hello ----------

def _iso(dt):
    return dt.isoformat(timespec="seconds")


def _when(s):
    try:
        return datetime.fromisoformat(str(s)[:19])
    except (TypeError, ValueError):
        return None


def load_state():
    try:
        d = json.loads(STATE.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(d):
    """Whole or not at all, the version before kept beside it."""
    HOME.mkdir(parents=True, exist_ok=True)
    mark = f"{os.getpid()}-{threading.get_ident()}"
    if STATE.is_file():
        tmp = STATE_PREV.with_name(f"{STATE_PREV.name}.{mark}.tmp")
        try:
            tmp.write_bytes(STATE.read_bytes())
            this_computer.replace(tmp, STATE_PREV)
        except OSError:
            try:
                tmp.unlink()
            except OSError:
                pass
    tmp = STATE.with_name(f"{STATE.name}.{mark}.tmp")
    try:
        tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
        this_computer.replace(tmp, STATE)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _answer(chosen, facts, now, kept):
    """What the page gets, filled from today's facts (a number that moved is refilled), or None if it can't be."""
    g = ("", []) if chosen.get("only") else fill(chosen["greeting_t"], facts, now, {})
    ln = fill(chosen["line_t"], facts, now, chosen.get("slots") or {})
    if not g or not ln:
        return None
    at = _when(chosen.get("at")) or now
    slots = chosen.get("slots") or {}
    return {"greeting": g[0], "line": ln[0], "greeting_parts": g[1], "line_parts": ln[1], "name": facts["name"],
            "group": chosen["group"], "greeting_group": chosen["greeting_group"], "kit": slots.get("kit") or "",
            "shoot": slots.get("shoot") or "", "chosen_at": _iso(at), "keep_until": _iso(at + timedelta(hours=KEEP_HOURS)),
            "kept": kept, "only": bool(chosen.get("only"))}


def first_only_line():
    """Her one line for the very first hello, exactly as she sent it (no {name} in it), or None."""
    for t in lines().get("first", []):
        if FIRST_ONLY_HAS in t and "{" not in t:
            return t
    return None


def first_ever(facts, st):
    """The very first hello: no shoot yet, and the page has never greeted them (no visit kept)."""
    return not facts.get("any_shoot") and not st.get("last_visit") and not st.get("chosen")


def _still_true(chosen, facts, now):
    """The kept hello's greeting and line are still among what can be said now (with the same shoot)."""
    away = bool(chosen.get("away"))
    if chosen.get("only"):                 # the very first hello: true for its 3 hours while there is no shoot yet
        return not facts.get("any_shoot") and chosen.get("line_t") == first_only_line()
    if (chosen.get("greeting_group"), chosen.get("greeting_t")) not in greetings(facts, now, away):
        return False
    slots = chosen.get("slots") or {}
    for _, grp, t, s in line_pool(facts, now, away):
        if grp == chosen.get("group") and t == chosen.get("line_t") and s.get("kit", "") == slots.get("kit", "") \
                and s.get("kind", "") == slots.get("kind", ""):
            chosen["slots"] = s            # the same line; its number may have moved
            return True
    return False


def choose(facts, now, rng, away=False, new_kit=None, recent=None):
    """A new hello: one greeting and one line that are true now and read well together, never the last ones
    said. Returns the record kept in home-hello.json (templates and slots), or None (it can't happen with her
    lines: "warm" is always true, and "first" always has a line)."""
    recent = recent or {}
    last_g, last_l = list(recent.get("greetings") or []), list(recent.get("lines") or [])
    gs = greetings(facts, now, away)
    pool = [x for x in line_pool(facts, now, away, new_kit) if fill(x[2], facts, now, x[3])]
    if not gs or not pool:
        return None

    def narrowed(items, key, last):
        for avoid in (last[-RECENT:], last[-1:], []):
            got = [x for x in items if key(x) not in avoid]
            if got:
                return got
        return items
    gs = narrowed(gs, lambda x: x[1], last_g)
    pool = narrowed(pool, lambda x: x[2], last_l)
    for _ in range(3):
        total = sum(w for w, *_ in pool)
        r = rng.random() * total
        pick = pool[-1]
        for x in pool:
            r -= x[0]
            if r <= 0:
                pick = x
                break
        _, grp, lt, slots = pick
        ok = [g for g in gs if not clash(g[1], lt) and fill(g[1], facts, now, {})]
        if ok:
            gg, gt = ok[int(rng.random() * len(ok)) % len(ok)]
            return {"greeting_group": gg, "greeting_t": gt, "group": grp, "line_t": lt, "slots": slots,
                    "away": away, "at": _iso(now)}
    # every greeting clashed with the lines drawn: take any pair that does not
    for _, grp, lt, slots in pool:
        for gg, gt in gs:
            if not clash(gt, lt) and fill(gt, facts, now, {}):
                return {"greeting_group": gg, "greeting_t": gt, "group": grp, "line_t": lt, "slots": slots,
                        "away": away, "at": _iso(now)}
    return None


def pick(now=None, rng=None, facts=None, fresh=False, write=True):
    """The hello the home page shows now. now and rng can be given (tests); facts too. Keeps it for 3 hours."""
    now = now or datetime.now()
    rng = rng or random.Random()
    facts = facts if facts is not None else gather(now)
    with _LOCK:
        st = load_state()
        last_visit = _when(st.get("last_visit"))
        seen = set(st.get("kits_seen") or [])
        new_kits = [k for k in facts.get("kits_seen") or [] if k not in seen] if st.get("kits_seen") is not None else []
        chosen = st.get("chosen") if isinstance(st.get("chosen"), dict) else None
        out = None
        if chosen and not fresh and not new_kits:
            at = _when(chosen.get("at"))
            if at and timedelta(0) <= now - at < timedelta(hours=KEEP_HOURS) and _still_true(chosen, facts, now):
                out = _answer(chosen, facts, now, kept=True)
        if out is None:
            away = bool(last_visit) and now - last_visit >= timedelta(days=AWAY_DAYS)
            newest = facts["kits"][0]["folder"] if facts["kits"] else None
            new_kit = newest if newest and newest in new_kits else None
            recent = st.get("recent") if isinstance(st.get("recent"), dict) else {}
            only = first_only_line() if first_ever(facts, st) else None
            if only:
                chosen = {"only": True, "greeting_group": "", "greeting_t": "", "group": "first", "line_t": only,
                          "slots": {}, "away": False, "at": _iso(now)}
            else:
                chosen = choose(facts, now, rng, away=away, new_kit=new_kit, recent=recent)
            if chosen is None:
                return None
            out = _answer(chosen, facts, now, kept=False)
            recent = {"greetings": (list(recent.get("greetings") or []) + ([chosen["greeting_t"]] if chosen["greeting_t"] else []))[-RECENT:],
                      "lines": (list(recent.get("lines") or []) + [chosen["line_t"]])[-RECENT:]}
            st["recent"] = recent
            st["kits_seen"] = list(facts.get("kits_seen") or [])
        st["chosen"] = chosen
        st["last_visit"] = _iso(now)
        if write:
            save_state(st)
        return out


def show(now=None):
    """What is true for them now, the groups that can show, the kept hello. Changes nothing."""
    now = now or datetime.now()
    facts = gather(now)
    st = load_state()
    last_visit = _when(st.get("last_visit"))
    away = bool(last_visit) and now - last_visit >= timedelta(days=AWAY_DAYS)
    pool = line_pool(facts, now, away)
    groups = {}
    for _, g, t, s in pool:
        if fill(t, facts, now, s):
            groups[g] = groups.get(g, 0) + 1
    return {"now": _iso(now), "facts": facts, "away": away, "greetings": len(greetings(facts, now, away)),
            "line_groups": groups, "kept": st.get("chosen"), "last_visit": st.get("last_visit")}


def main():
    ap = argparse.ArgumentParser(description="The home page's hello, from Nicole's approved lines.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    p = sub.add_parser("pick")
    p.add_argument("--now", help="pretend it is this time on this computer, 2026-11-21T09:30")
    p.add_argument("--seed", type=int)
    p.add_argument("--fresh", action="store_true", help="a new hello even when one is kept")
    p.add_argument("--dry-run", action="store_true", help="keep nothing")
    a = ap.parse_args()
    if a.cmd == "show":
        say(json.dumps(show(), indent=1, ensure_ascii=False))
        return 0
    now = None
    if a.now:
        now = _when(a.now)
        if now is None:
            say("--now wants a time like 2026-11-21T09:30")
            return 2
    rng = random.Random(a.seed) if a.seed is not None else None
    say(json.dumps(pick(now=now, rng=rng, fresh=a.fresh, write=not a.dry_run), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
