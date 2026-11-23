#!/usr/bin/env python3
"""The words for a post: what the photographer said about it, and the caption and hooks written from that
(Nicole's handoff v20, Nov 9 and 10, built our way).

A post isn't finished when the reel or the carousel is made: "It's obviously not complete until you have the
captions." The words are theirs. They say what the shoot was about, in the chat or on the words page, and
Claude shapes it the way an editor would. Nothing here writes a caption: Claude does, in the chat, and every
command prints the rules again so they are never skipped.

    python3 words.py ask    "hannah" reel               they pasted "Ask me about the <shoot> <piece>": how to ask the
                                                        questions in the chat, one at a time, and what's answered
    python3 words.py answer "hannah" reel --file a.json save what they said for one or more questions
    python3 words.py show   "hannah" reel               they pasted "Write my words for ..." or "Polish my caption
                                                        for ...": the rules, their Brand Homebase, their answers,
                                                        what's already written
    python3 words.py draft  "hannah" reel --file d.json save {"caption": "...", "hooks": ["...", ...]}
    python3 words.py carry  "hannah" reel carousel      copy one piece's answers to the other (never "where")
    python3 words.py carry-reel "hannah" --from "Reel 1" --reel "Reel 2"
                                                        a new reel starts from another reel's answers (answers only)

EACH REEL HAS ITS OWN WORDS (Nicole, Nov 23: "each reel gets its own caption"). A shoot (or My vault) with more
than one reel: every command that means a reel takes --reel "<its name>" (a part of the name, or its id), and with
several reels and no --reel it stops and lists the names. A shoot with one reel needs none, and its record is
byte for byte what it always was.

The piece is reel or carousel. Stories have no words (Nicole, Nov 10). A few words find the kit, as for kit.py.

answer's file: any of about, who (a list of new, past, followers, photographers), who_text, where (feed or
trial; reels only), purpose (share, book, offer, other), purpose_text, notes.

The record is <kit>/.kit/post-words.json; the version before every save is kept beside it as
post-words.prev.json. Her shape, kept: {"pieces": {"reel": {...}, "carousel": {...}}}. "reel" is the shoot's FIRST
reel (reels.FIRST_ID), as it always was; every reel started after it keeps its words under its own id beside it,
{"pieces": {"reels": {"v2": {...}, ...}}}, each in the very shape "reel" has. That map is not written until a
later reel has words of its own. Their own caption ("own") and their picked hooks are kept by a draft; picks are cleared
only when the hooks change.

Exit: 0 done, 1 a problem with the kit, 2 STOP (a purpose or place that isn't one of the buttons, an empty file).

A Mac and a PC: every file is read and written as UTF-8; saving goes through kit.py's whole-file write.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fresh           # noqa: E402
import kit as kitmod   # noqa: E402
import posts           # noqa: E402
import reels as reels_mod   # noqa: E402
import this_computer   # noqa: E402

PIECES = ("reel", "carousel")                     # no stories (Nicole, Nov 10)
HOW_MANY = {"reel": 10, "carousel": 0}            # carousels: a caption only, no cover lines (Nicole, Nov 10)
WHAT = {"reel": "hooks (the line on the reel's first photo)", "carousel": "cover lines (the words on the first slide)"}
WHO = {"new": "New clients", "past": "Past clients", "followers": "Everyone who follows me", "photographers": "Other photographers"}
WHERE = {"feed": "On their feed", "trial": "A trial reel (shown to people who don't follow them yet)"}
PURPOSE = {"share": "Share my work", "book": "Book more sessions", "offer": "Something coming up (an offer, like mini sessions)", "other": "Something else"}
FIELDS = {"about": 3000, "who_text": 600, "purpose_text": 1000, "notes": 1000}      # the most each answer may hold
CAPTION_MOST, HOOKS_MOST, HOOK_MOST = 4000, 20, 200
RECORD, BEFORE = "post-words.json", "post-words.prev.json"
HOMEBASE = "brand-homebase.md"
# Each reel its own words (Nicole, Nov 23). The shoot's first reel is "pieces.reel", as ever; a later reel's words
# are "pieces.reels.<its id>". A reel with no words of its own is EMPTY: it never reads another reel's.
FIRST_REEL = reels_mod.FIRST_ID
LATER = "reels"
ANSWERED = ("about", "who", "who_text", "purpose", "purpose_text", "notes")
# Ours (drafts for Nicole): what the chat is told when a reel has to be named, or can't be found.
NOT_A_REEL = "that isn't one of this shoot's reels"
WHICH_REEL = "this shoot has {n} reels, and each reel has its own words. Say which one with --reel: {names}"

# Nicole's rules, word for word (handoff v20, words.py). Rule 11 in CLAUDE.md says the same thing from our side:
# specifics come only from the photographer.
RULES = """How to write it (Nicole, Nov 9 and 10; the Assistant's own rules for words apply too):
  YOU'RE THE EDITOR (Nicole, Nov 10). They told you the shoot in their own words. Take exactly their words and
  make them better, the way an editor would: keep their story, their phrases and their feeling, and shape it
  so it sounds like them, only better. Cross-check every line against their Brand Homebase (read it in full,
  the path is below): how they sound, the words they use, the words they never want to see, their rules.
  You're not rewriting them and you never add a fact; you're polishing what they gave you.
  OPTIMIZE FOR THE GOAL. Use what you know about social media so the caption does its job. Whatever the post is
  for goes where people see it first, in the opening line or two before "more". If it's an offer like mini
  sessions, open with the offer (what, when, where), then the story, then exactly how to book. Even if they said
  it last, it goes first: reorder, never change what they said. Nicole: "if you hide it in there, then no one's
  going to see it."
  SPECIFICS COME ONLY FROM THEIR ANSWERS: names, what happened, the occasion, an offer's dates, price or details.
  If one is missing, leave it out or ask them in the chat. Never invent it, not even something probably true.
  If their playbook or Homebase expects something they didn't give (a price on a mini-session post), ask.
  HOOKS (Nicole, Nov 10: "Why are the hooks so bad?"). A hook is not a line about the shoot. It speaks to the
  person they're trying to reach and points at the post's purpose. Before writing, name the two things: who
  (e.g. new clients like Hannah, moms in that same season) and the purpose (e.g. book the mini sessions).
  Every hook must give that person a reason to stop and keep watching that leads toward the purpose: what they
  want, what they'd feel, why this is for them. They don't all have to say the offer outright (vary them: some
  name it, most make the person want it), but every one has to serve it.
  Never describe the shoot as a hook ("the kids were having so much fun", "the weather was perfect"): that's
  caption material and stops no one. Never retell the client's story as the hook either.
  Build them from their Brand Homebase (who their ideal client is, what that person wants, how they sound) and
  from this shoot's own details. Match their personality: if they're fun, give a few fun ones; if they're
  heartwarming and nurturing, give those; usually a mix. Never the generic lines everyone says ("this season
  goes so fast", "hurry, it's almost gone"): each one should only make sense coming from this photographer.
  Check every hook before saving: would the person they want to reach stop for it, and does it lead to the
  purpose? If not, cut it. One line each, readable in a second, each a different angle.
  If the purpose is an offer, the hooks and caption point to it exactly as they described it.
  If it's a trial reel, every hook has to stop someone who has never heard of them.
  Write {task}. Then tell them in the chat it's on the page, in one line."""

ASK = """Asking in the chat (Nicole, Nov 10: "typing all this stuff is so hard"). They talk with the microphone in the
chat box; you ask, listen, and save. The page fills in as you go.
  One question at a time, in this order, each with buttons where it has them. Skip any they've already answered
  (shown below) unless they want to change it. Keep each question short and warm, with its one line of why:
  1. Tell me about this shoot. Every caption needs a backstory: what was it for (a family session, a milestone,
     a brand)? Who was there, what happened, what stood out to you that day?  (no buttons; they just talk)
  1b. If people are in it: Do you want their names in it?  Buttons: Yes, use their names · No names
     If yes, ask for any names they haven't said, spelled the way they want. Save it in notes ("Names: ..." or "No names").
  2. Who are you trying to reach with this one? The clearer you are, the more it speaks to them.
     Buttons: New clients · Past clients · Everyone who follows me · Other photographers (more than one is fine)
  2b. Always follow up (Nicole, Nov 10: ask the optional parts too): Tell me a little about them. Who are they,
     and what do they care about?  Buttons: Skip this · (or they just talk). Save it as who_text.
  2c. Reels only: Is this going on your feed, or is it a trial reel? A trial reel is shown to people who don't
     follow you yet, so its first second has to stop a stranger.  Buttons: On my feed · A trial reel. Save as where.
  3. What is this post trying to do?  Buttons: Share my work · Book more sessions · Something coming up · Something else
  3b. Always follow up, in their words, saved as purpose_text:
     Something coming up: What is it (mini sessions, a new offer)? The dates, where, the price if they want it in,
     how to book, and anything people should know. Ask only what they haven't said; never fill a gap.
     Book more sessions: What kind of sessions, and how should people book?
     Share my work / Something else: Anything you want people to take away?  Buttons: Skip this
  4. Anything else to include or leave out? Something not to mention, how people should book.
     Buttons: Nothing else · Yes (then they say it)
  After each answer, save it right away with `answer` (their words as they said them; tidy only obvious
  dictation slips, never add to them). Then ask the next one. Never ask two at once.
  Keep anything already in notes (like names) when you save notes again. When all four are done, say in one line that it's all on the page, then write the words exactly as for
  "Write my words" (`show`, then `draft`), and tell them in one line the caption and {what} are on the page."""


def say(msg):
    kitmod.say(msg)


class Stop(Exception):
    """Something in what was handed over can't be saved; nothing was written."""


# ---------- the record ----------

def record_path(kit):
    return Path(kit) / ".kit" / RECORD


def load(kit):
    """The kit's words record, or an empty one. A file that can't be read as JSON counts as empty here; the save
    that follows keeps it as the version before, so nothing of theirs is lost."""
    try:
        rec = json.loads(record_path(kit).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"pieces": {}}
    if not isinstance(rec, dict) or not isinstance(rec.get("pieces"), dict):
        return {"pieces": {}}
    return rec


def later_reel(piece, reel):
    """Where a reel's words are kept: None for the carousel and for the shoot's first reel (they are
    "pieces.<piece>", as ever), else the reel's own id, the key under "pieces.reels". An id that is not a reel
    id's shape is refused (Stop) before anything is read or written, so nothing odd is ever made a key."""
    if piece != "reel" or reel is None or reel == FIRST_REEL:
        return None
    if not isinstance(reel, str) or not reels_mod.ID.fullmatch(reel):
        raise Stop(NOT_A_REEL)
    return reel


def piece_of(rec, piece, reel=None):
    """One piece's words in the record, to CHANGE: made (empty) when it isn't there yet. `reel`: which of the
    shoot's reels (a reel's id); none, or the first reel's, is "pieces.reel"."""
    later = later_reel(piece, reel)
    pieces = rec.setdefault("pieces", {})
    if later is None:
        w = pieces.get(piece)
        if not isinstance(w, dict):
            w = pieces[piece] = {}
    else:
        m = pieces.get(LATER)
        if not isinstance(m, dict):
            m = pieces[LATER] = {}
        w = m.get(later)
        if not isinstance(w, dict):
            w = m[later] = {}
    if not isinstance(w.get("answers"), dict):
        w["answers"] = {}
    return w


def read_of(rec, piece, reel=None):
    """One piece's words in the record, to READ: {} with empty answers when it has none. Nothing in the record is
    changed or added. A later reel reads only its own; never another reel's, never the first reel's."""
    later = later_reel(piece, reel)
    pieces = rec.get("pieces") if isinstance(rec, dict) and isinstance(rec.get("pieces"), dict) else {}
    if later is None:
        w = pieces.get(piece)
    else:
        m = pieces.get(LATER)
        w = m.get(later) if isinstance(m, dict) else None
    w = dict(w) if isinstance(w, dict) else {}
    if not isinstance(w.get("answers"), dict):
        w["answers"] = {}
    return w


def reels_with_words(rec):
    """The ids of the later reels that have a words entry of their own in this record."""
    pieces = rec.get("pieces") if isinstance(rec, dict) and isinstance(rec.get("pieces"), dict) else {}
    m = pieces.get(LATER)
    return [k for k, v in m.items() if isinstance(k, str) and reels_mod.ID.fullmatch(k) and isinstance(v, dict)] if isinstance(m, dict) else []


def change(kit, piece, how, reel=None):
    """Read the record, change one piece (how(piece_record, whole_record)), and save it as one step no other
    command or page can get in the middle of. The version before is kept beside it. Returns the saved record.
    `reel`: which reel's words (see piece_of); only that reel's entry is handed to `how`."""
    kit = Path(kit)
    later_reel(piece, reel)                     # an id that isn't one stops here, before the folder is touched
    kitmod.hidden(kit)
    with kitmod._held(kit / ".kit" / "words.lock", 10.0):
        p = record_path(kit)
        rec = load(kit)
        how(piece_of(rec, piece, reel), rec)
        if p.exists():
            try:
                kitmod._write_text_whole(p.with_name(BEFORE), p.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                pass                            # the earlier copy could not be read: the save still goes ahead
        kitmod._write_whole(p, rec)
        return rec


def _text(v, most):
    return str(v if v is not None else "").strip()[:most]


def take_answers(ans, given):
    """Put what was given into the answers, each in its own shape and within its limit. Returns the names saved.
    Raises Stop for a purpose or a place that isn't one of the buttons, before anything is changed."""
    if not isinstance(given, dict):
        raise Stop("the answers aren't a set of named answers")
    where, purpose = given.get("where"), given.get("purpose")
    if "where" in given and where and where not in WHERE:
        raise Stop(f"where must be one of {', '.join(WHERE)}")
    if "purpose" in given and purpose and purpose not in PURPOSE:
        raise Stop(f"purpose must be one of {', '.join(PURPOSE)}")
    if "who" in given and given["who"] is not None and not isinstance(given["who"], (list, tuple)):
        raise Stop("who must be a list of: " + ", ".join(WHO))
    done = []
    for k, most in FIELDS.items():
        if k in given:
            ans[k] = _text(given[k], most); done.append(k)
    if "who" in given:
        ans["who"] = [x for x in (given["who"] or []) if x in WHO]; done.append("who")
    if "where" in given:
        ans["where"] = where or ""; done.append("where")
    if "purpose" in given:
        ans["purpose"] = purpose or ""; done.append("purpose")
    return done


def save_answers(kit, piece, given, reel=None):
    done = []

    def how(w, rec):
        got = take_answers(w["answers"], given)
        if piece != "reel":
            w["answers"].pop("where", None)         # feed or trial is a reel's question only
            got = [k for k in got if k != "where"]
        if not got:
            raise Stop("the answer file has none of: about, who, who_text, where, purpose, purpose_text, notes")
        done.extend(got)
        w["updated"] = time.time()
    change(kit, piece, how, reel)
    return done


def save_draft(kit, piece, given, reel=None):
    """A caption and, for a reel, hooks. Returns (caption saved?, how many hooks saved)."""
    if not isinstance(given, dict):
        raise Stop("the draft isn't a caption and a list of hooks")
    cap = _text(given.get("caption"), CAPTION_MOST)
    hooks = given.get("hooks") or []
    if not isinstance(hooks, (list, tuple)):
        raise Stop("hooks must be a list of lines")
    hooks = [_text(h, HOOK_MOST) for h in hooks if _text(h, HOOK_MOST)][:HOOKS_MOST]
    if not HOW_MANY[piece]:
        hooks = []                                  # a carousel gets a caption only
    if not cap and not hooks:
        raise Stop("the draft has no caption and no hooks" if HOW_MANY[piece] else "the draft has no caption (a carousel gets a caption only)")

    def how(w, rec):
        if cap:
            w["caption"] = cap
        if hooks:
            if hooks != w.get("hooks"):
                w["picked"] = []
            w["hooks"] = hooks
        w["drafted"] = w["updated"] = time.time()
    change(kit, piece, how, reel)
    return bool(cap), len(hooks)


def save_from_page(kit, piece, given, reel=None):
    """What the words page sends: any of answers, caption, own, hooks, picked. Returns the saved piece.
    `reel`: which reel's words (the page says which; the first reel's when it says none)."""
    if piece not in PIECES:
        raise Stop("words are for a reel or a carousel")
    if not isinstance(given, dict):
        raise Stop("nothing to save")

    def how(w, rec):
        if "answers" in given:
            take_answers(w["answers"], given["answers"])
            if piece != "reel":
                w["answers"].pop("where", None)
        if "caption" in given:
            w["caption"] = _text(given["caption"], CAPTION_MOST)
        if "own" in given:
            w["own"] = _text(given["own"], CAPTION_MOST)
        if "hooks" in given and HOW_MANY[piece]:
            hs = given["hooks"] if isinstance(given["hooks"], (list, tuple)) else []
            hs = [_text(h, HOOK_MOST) for h in hs if _text(h, HOOK_MOST)][:HOOKS_MOST]
            if hs != w.get("hooks"):
                w["picked"] = []
            w["hooks"] = hs
        if "picked" in given:
            n = len(w.get("hooks") or [])
            ps = given["picked"] if isinstance(given["picked"], (list, tuple)) else []
            w["picked"] = [i for i in dict.fromkeys(ps) if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < n]
        w["updated"] = time.time()
    rec = change(kit, piece, how, reel)
    return read_of(rec, piece, reel)


def carry(kit, src, dst, reel=None):
    """Copy one piece's answers to the other, so they never answer twice. "where" is a reel's own question.
    `reel`: which reel is the reel end of it (from that reel to the carousel, or from the carousel to it)."""
    a = dict(read_of(load(kit), src, reel)["answers"])
    a.pop("where", None)
    if not any(a.get(k) for k in ANSWERED):
        raise Stop(f"the {src} has no answers to carry over yet")
    return save_answers(kit, dst, a, reel)


def carry_reel(kit, src, dst):
    """A reel that has no answers yet starts from another reel's (answers only: never its caption, its hooks or
    their own caption, which are each reel's own). Never over answers the reel already has. Returns the names."""
    if (later_reel("reel", src) or FIRST_REEL) == (later_reel("reel", dst) or FIRST_REEL):
        raise Stop("that is the same reel")
    rec = load(kit)
    a = dict(read_of(rec, "reel", src)["answers"])
    if not any(a.get(k) for k in ANSWERED):
        raise Stop("that reel has no answers to use yet")
    done = []

    def how(w, rec):
        if any(w["answers"].get(k) for k in ANSWERED):          # looked at under the lock: never over theirs
            raise Stop("this reel already has answers of its own")
        done.extend(take_answers(w["answers"], a))
        w["updated"] = time.time()
    change(kit, "reel", how, dst)
    return done


def _status(w):
    a = w["answers"]
    return {"answered": any(a.get(k) for k in ANSWERED),
            "caption": bool((w.get("caption") or "").strip() or (w.get("own") or "").strip()),
            "hooks": len(w.get("hooks") or []), "picked": len(w.get("picked") or [])}


def status(kit, reel=None):
    """For the post kit: {piece: {answered, caption, hooks, picked}}. `reel`: which reel "reel" means (the
    shoot's first when none)."""
    rec = load(kit)
    return {p: _status(read_of(rec, p, reel if p == "reel" else None)) for p in PIECES}


def reels_status(kit, ids):
    """{reel id: {answered, caption, hooks, picked}} for each of the shoot's reels named (an id that isn't one
    is left out), read from one look at the record."""
    rec = load(kit)
    out = {}
    for vid in ids:
        try:
            out[vid] = _status(read_of(rec, "reel", vid))
        except Stop:
            pass
    return out


def kit_reel_names(kit):
    """([{id, name}] for the shoot's reels, the id of the one being worked on). One reel, or a reel record that
    can't be read: ([], None), and then nothing anywhere asks which reel."""
    try:
        import reel_page
        names, cur = reel_page.reel_names(Path(kit))
    except (Exception, SystemExit):  # noqa: BLE001
        return [], None
    names = [v for v in names if isinstance(v, dict) and isinstance(v.get("id"), str) and isinstance(v.get("name"), str)]
    return (names, cur) if len(names) > 1 else ([], None)


def which_reel(kit, said):
    """For a command's --reel: (the reel's id or None, its name or ""). A shoot with one reel: (None, "") and
    --reel is not needed (given anyway, it must fit that reel). Several reels: the one `said` names (its name, a
    part of one name only, or its id); nothing said, or a name that fits none or more than one, is a Stop that
    lists the reels by name, so words are never saved to a reel nobody named."""
    names, _ = kit_reel_names(kit)
    if not names:
        if said:
            import reel_page
            try:
                vid, why = reel_page.which_reel(Path(kit), said)
            except (Exception, SystemExit):  # noqa: BLE001
                vid, why = FIRST_REEL, None
            if vid is None:
                raise Stop(why)
        return None, ""
    listed = ", ".join(f"\"{v['name']}\"" for v in names)
    if not said:
        raise Stop(WHICH_REEL.format(n=len(names), names=listed))
    import reel_page
    vid, why = reel_page.which_reel(Path(kit), said)
    if vid is None:
        raise Stop(why)
    return vid, next((v["name"] for v in names if v["id"] == vid), "")


# ---------- their brand ----------

def homebase():
    """Their Brand Homebase for their photography business: the brand interview they did when they started with
    the Assistant, saved as brand-homebase.md in the Assistant's folder on their drive. Only ever that one: a
    brand file of some other business of theirs is the wrong voice (Nicole's Horizon Found one is written for
    photographers, not moms), so when it isn't here the answer is to ask, never to look further afield."""
    spots = []
    try:
        h = posts.home()
    except Exception:
        h = None
    if h:
        spots += [Path(h) / HOMEBASE, Path(h) / ".studio" / HOMEBASE]
    spots.append(Path(os.environ.get("STUDIO_HOME") or Path.home() / ".studio") / HOMEBASE)
    for f in spots:
        try:
            if f.is_file():
                return f
        except OSError:
            pass
    return None


def homebase_spot():
    """Where a Brand Homebase would be read from when there is none yet: the Assistant's folder, by its exact
    name. Printed so nobody has to guess the folder or the name (a .txt or a PDF beside it is not found)."""
    try:
        h = posts.home()
    except Exception:
        h = None
    return (Path(h) if h else Path(os.environ.get("STUDIO_HOME") or Path.home() / ".studio")) / HOMEBASE


def answered(ans):
    who = ", ".join(WHO.get(x, x) for x in ans.get("who") or [])
    return [("1. The shoot", ans.get("about")),
            ("2. Who they want to reach", " · ".join(x for x in (who, ans.get("who_text")) if x)),
            ("2c. Where it's going", WHERE.get(ans.get("where"), ans.get("where") or "")),
            ("3. What it's for", " · ".join(x for x in (PURPOSE.get(ans.get("purpose"), ans.get("purpose") or ""), ans.get("purpose_text")) if x)),
            ("4. Anything to include or leave out", ans.get("notes"))]


# ---------- the commands ----------

def _the(piece, reel_name):
    """ "reel" or "carousel", with the reel's name when the shoot has several: reel "Reel 2". """
    return f"{piece} \"{reel_name}\"" if piece == "reel" and reel_name else piece


def _reel_flag(reel_name):
    return f" --reel \"{reel_name}\"" if reel_name else ""


def cmd_show(kit, piece, reel=None, reel_name=""):
    rec = load(kit)
    w = read_of(rec, piece, reel if piece == "reel" else None)
    ans = w["answers"]
    say(RULES.format(task=f"{HOW_MANY[piece]} {WHAT[piece]}, and one caption" if HOW_MANY[piece]
                     else "one caption, and no cover lines (Nicole, Nov 10: they can figure that out themselves)"))
    hb = homebase()
    if hb:
        say(f"\nTheir Brand Homebase: {hb}  (read it in full before you write)")
    else:
        say("\nNo Brand Homebase found. Ask them where it is, or write from their answers and say it isn't on their brand yet.")
        say(f"  It is read from exactly this file, and no other name or ending: {homebase_spot()}")
        v = kitmod.voice()
        if v.get("samples") or v.get("never"):
            say("  What they gave when asked how they write (kit.py voice), until there is a Homebase:")
            for s in (v.get("samples") or [])[:5]:
                say("    A caption they posted: " + s.replace("\n", " / "))
            for s in (v.get("never") or [])[:5]:
                say("    They'd never write: " + s.replace("\n", " / "))
    say("")
    say(f"{kit.name}, the {_the(piece, reel_name)}: what they said")
    if piece == "reel" and reel_name:
        say("  (Each reel of this shoot has its own answers, caption and hooks. These are this reel's only;"
            f" save with{_reel_flag(reel_name)}.)")
    rows = answered(ans)
    for k, v in rows:
        say(f"  {k}: {(v or '').strip() or '(nothing yet)'}")
    own = (w.get("own") or "").strip()
    if own:
        say(f"  Their own caption (polish it if they ask; never replace it): {own}")
    if not any((v or "").strip() for _, v in rows) and not own:
        said = kitmod.told_text(kit)
        if said:
            say("\n  They haven't answered the questions yet, but they said this when the kit was made (theirs, word for word):")
            say("    " + said.replace("\n", " / "))
            say("  Ask the questions it leaves open, one at a time, or point them to the page.")
        else:
            say("\n  They haven't answered yet. Ask them in the chat, one question at a time, or point them to the page.")
    other = [p for p in PIECES if p != piece][0]
    names, _ = kit_reel_names(kit)
    # the captions this one must not repeat: the other piece's, and, with several reels, every other reel's
    # (to READ only: nothing of another reel is ever saved here)
    others = []
    if piece == "reel":
        oc = read_of(rec, "carousel")
        if oc.get("caption"):
            others.append(("carousel", oc["caption"]))
        for v in names:
            if (later_reel("reel", v["id"]) or FIRST_REEL) != (later_reel("reel", reel) or FIRST_REEL):
                c = read_of(rec, "reel", v["id"]).get("caption")
                if c:
                    others.append((f"reel \"{v['name']}\"", c))
    else:
        for v in names or [{"id": FIRST_REEL, "name": ""}]:
            c = read_of(rec, "reel", v["id"]).get("caption")
            if c:
                others.append((_the("reel", v["name"]), c))
    for i, (what, text) in enumerate(others):
        named = '"' in what                 # a reel by its name: "the caption of the reel "Reel 2""
        if i:
            say(f"\nAnd the caption of the {what}, already written (this one must be genuinely different from it too):")
        elif named:
            say(f"\nThe caption of the {what}, already written (the words must not repeat):")
        else:
            say(f"\nThe {what}'s caption, already written (their answers carry over; the words must not repeat):")
        say("  " + text.replace("\n", " / "))
    if others:
        theirs = "those" if len(others) > 1 or '"' in others[0][0] else f"the {others[0][0]}'s"
        say(f"  The {piece} caption must be genuinely DIFFERENT from this one (Nicole, Nov 10: someone who sees both"
            f" shouldn't feel like they're reading a slightly different version). Same facts, same goal in the opening"
            f" lines, but a different way in: a different opening line and angle, a different part of their story up"
            f" front, a different shape and different sentences. Don't reuse its lines or reword them one by one."
            f" Use only their answers for facts; their answers are your source, this caption is only what to avoid."
            + (f" Then write new {WHAT[piece].split(' (')[0]}, different from {theirs} too." if HOW_MANY[piece] else ""))
    if w.get("caption") or w.get("hooks"):
        say("\nAlready written (a new draft replaces it; the version before is kept):")
        if w.get("caption"):
            say("  Caption: " + w["caption"].replace("\n", " / "))
        hooks = w.get("hooks") or []
        picked = {i for i in (w.get("picked") or []) if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(hooks)}
        for i, h in enumerate(hooks, 1):
            say(f"  {i}. {h}" + ("   <- picked" if (i - 1) in picked else ""))
        if hooks:
            # the picking is theirs, on the words page: never pick one for them (parts/words.md, parts/canva.md)
            say(f"  They picked {len(picked)} of the {len(hooks)} on the page (marked \"<- picked\")." if picked
                else "  None picked yet: they pick on the words page (Pick). Never choose one for them.")
    return 0


def cmd_ask(kit, piece, reel=None, reel_name=""):
    rec = load(kit)
    w = read_of(rec, piece, reel if piece == "reel" else None)
    what = WHAT[piece].split(" (")[0] if HOW_MANY[piece] else "caption"
    say(ASK.format(piece=piece, what=what).replace("the caption and caption are", "the caption is"))
    say("")
    say(f"{kit.name}, the {_the(piece, reel_name)}: answered so far")
    if piece == "reel" and reel_name:
        say(f"  (This reel's own answers. Save each with{_reel_flag(reel_name)}.)")
    for k, v in answered(w["answers"]):
        say(f"  {k}: {(v or '').strip() or '(not yet)'}")
    other = [p for p in PIECES if p != piece][0]
    names, _ = kit_reel_names(kit)
    if not _status(w)["answered"] and piece == "reel" and names:
        # a new reel starts empty; another reel of the shoot that is answered is offered first, with their yes
        mine = later_reel("reel", reel) or FIRST_REEL
        src = next((v for v in names if v["id"] != mine and _status(read_of(rec, "reel", v["id"]))["answered"]), None)
        if src is not None:
            say(f"\nNothing is answered for this reel yet, but \"{src['name']}\" is. Don't start again from question 1:"
                f" offer to start from what they said for that reel (buttons: Use what I said for {src['name']} · Ask me again)."
                f" On yes: words.py carry-reel \"<kit>\" --from \"{src['name']}\" --reel \"{reel_name}\", then ask what"
                " is different about this reel and save only that. The caption and the hooks are never copied: each"
                " reel gets its own.")
            return 0
    if piece == "carousel" and len(names) > 1 and not _status(w)["answered"]:
        src = next((v for v in names if _status(read_of(rec, "reel", v["id"]))["answered"]), None)
        if src is not None:
            say(f"\nNothing is answered for the carousel yet, but the reel \"{src['name']}\" is. Don't start again from"
                f" question 1: offer to use what they said for that reel (buttons: Use what I said for {src['name']} · Ask me again)."
                f" On yes: words.py carry \"<kit>\" reel carousel --reel \"{src['name']}\", then ask only what is still open.")
        return 0 if src is not None else _ask_told(kit, w)
    st = status(kit, reel)
    if not st[piece]["answered"] and st[other]["answered"]:
        # so they never answer twice (Nicole): offered, with their yes; "where" is the reel's own and never carries
        say(f"\nNothing is answered for the {piece} yet, but the {other} is. Don't start again from question 1: offer"
            f" to use what they said for the {other} (buttons: Use what I said for the {other} · Ask me again)."
            f" On yes: words.py carry \"<kit>\" {other} {piece}{_reel_flag(reel_name)}, then ask only what is still open"
            + (" (2c: feed or trial reel)." if piece == "reel" else "."))
        return 0
    return _ask_told(kit, w)


def _ask_told(kit, w):
    if not (w["answers"].get("about") or "").strip():
        # what they said when the kit was made is theirs, but it was said about the whole shoot, before this
        # piece existed: it is offered as question 1's answer, with their yes, never saved there unasked
        said = kitmod.told_text(kit)
        if said:
            say("\nQuestion 1 isn't answered, but they said this when the kit was made (theirs, word for word):")
            say("    " + said.replace("\n", " / "))
            say("  Don't ask question 1 cold: read it back in a line and ask whether to use it as it is or add to it"
                " (buttons: Use that · Let me add to it). Save it as about only once they say so, their words as said.")
    return 0


def read_json(path):
    try:
        return json.loads(kitmod.read_their_file(path))
    except OSError as e:
        raise Stop(f"the file can't be read ({e.__class__.__name__})")
    except ValueError as e:
        raise Stop(f"the file isn't JSON that can be read ({e})")


def main(argv=None):
    this_computer.utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, with_file in (("show", False), ("ask", False), ("answer", True), ("draft", True)):
        s = sub.add_parser(name)
        s.add_argument("words", help="a few words of the shoot's name")
        s.add_argument("piece", choices=PIECES)
        if with_file:
            s.add_argument("--file", required=True, help="a UTF-8 JSON file")
        s.add_argument("--reel", default="", help="which reel, by its name, when the shoot has more than one")
    c = sub.add_parser("carry")
    c.add_argument("words"); c.add_argument("piece", choices=PIECES); c.add_argument("to", choices=PIECES)
    c.add_argument("--reel", default="", help="which reel is the reel end of it, when the shoot has more than one")
    r = sub.add_parser("carry-reel")
    r.add_argument("words")
    r.add_argument("--from", dest="src", required=True, help="the reel whose answers to start from, by its name")
    r.add_argument("--reel", required=True, help="the reel that gets them, by its name")
    a = ap.parse_args(argv)
    fresh.announce()
    kit = kitmod.find_kit(a.words)
    try:
        if a.cmd == "carry-reel":
            src, src_name = which_reel(kit, a.src)
            dst, dst_name = which_reel(kit, a.reel)
            if not src_name or not dst_name:
                raise Stop("this shoot has one reel, so there is no other reel to start from")
            done = carry_reel(kit, src, dst)
            say(f"\"{dst_name}\" now starts from what they said for \"{src_name}\" ({', '.join(done)}). Only the answers:"
                " its caption and hooks are still to write, and are its own.")
            return 0
        # which reel: only where a reel is meant (a carousel's own commands never ask)
        reel, reel_name = which_reel(kit, a.reel) if (a.piece == "reel" or (a.cmd == "carry" and a.to == "reel")) else (None, "")
        if a.cmd == "show":
            return cmd_show(kit, a.piece, reel, reel_name)
        if a.cmd == "ask":
            return cmd_ask(kit, a.piece, reel, reel_name)
        if a.cmd == "answer":
            done = save_answers(kit, a.piece, read_json(a.file), reel)
            say(f"Saved {', '.join(done)} for the {kit.name} {_the(a.piece, reel_name)}. The page shows it in a few seconds.")
            return 0
        if a.cmd == "draft":
            cap, n = save_draft(kit, a.piece, read_json(a.file), reel)
            say(f"Saved the {_the(a.piece, reel_name)} words for {kit.name}: " + ("a caption" if cap else "") + (" and " if cap and n else "")
                + (f"{n} {WHAT[a.piece].split(' (')[0]}" if n else "") + ". The page shows them in a few seconds.")
            return 0
        if a.cmd == "carry":
            if a.piece == a.to:
                raise Stop("carry goes from one piece to the other")
            done = carry(kit, a.piece, a.to, reel)
            say(f"Carried {', '.join(done)} from the {_the(a.piece, reel_name)} to the {_the(a.to, reel_name)}. They don't have to answer again.")
            return 0
    except Stop as e:
        say(f"STOP: {e}. Nothing was saved.")
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
