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

The piece is reel or carousel. Stories have no words (Nicole, Nov 10). A few words find the kit, as for kit.py.

answer's file: any of about, who (a list of new, past, followers, photographers), who_text, where (feed or
trial; reels only), purpose (share, book, offer, other), purpose_text, notes.

The record is <kit>/.kit/post-words.json; the version before every save is kept beside it as
post-words.prev.json. Their own caption ("own") and their picked hooks are kept by a draft; picks are cleared
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


def piece_of(rec, piece):
    w = rec.setdefault("pieces", {}).get(piece)
    if not isinstance(w, dict):
        w = rec["pieces"][piece] = {}
    if not isinstance(w.get("answers"), dict):
        w["answers"] = {}
    return w


def change(kit, piece, how):
    """Read the record, change one piece (how(piece_record, whole_record)), and save it as one step no other
    command or page can get in the middle of. The version before is kept beside it. Returns the saved record."""
    kit = Path(kit)
    kitmod.hidden(kit)
    with kitmod._held(kit / ".kit" / "words.lock", 10.0):
        p = record_path(kit)
        rec = load(kit)
        how(piece_of(rec, piece), rec)
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


def save_answers(kit, piece, given):
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
    change(kit, piece, how)
    return done


def save_draft(kit, piece, given):
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
    change(kit, piece, how)
    return bool(cap), len(hooks)


def save_from_page(kit, piece, given):
    """What the words page sends: any of answers, caption, own, hooks, picked. Returns the saved piece."""
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
    rec = change(kit, piece, how)
    return rec["pieces"][piece]


def carry(kit, src, dst):
    """Copy one piece's answers to the other, so they never answer twice. "where" is a reel's own question."""
    a = dict(piece_of(load(kit), src)["answers"])
    a.pop("where", None)
    if not any(a.get(k) for k in ("about", "who", "who_text", "purpose", "purpose_text", "notes")):
        raise Stop(f"the {src} has no answers to carry over yet")
    return save_answers(kit, dst, a)


def status(kit):
    """For the post kit: {piece: {answered, caption, hooks, picked}}."""
    rec = load(kit)
    out = {}
    for p in PIECES:
        w = piece_of(rec, p)
        a = w["answers"]
        out[p] = {"answered": any(a.get(k) for k in ("about", "who", "who_text", "purpose", "purpose_text", "notes")),
                  "caption": bool((w.get("caption") or "").strip() or (w.get("own") or "").strip()),
                  "hooks": len(w.get("hooks") or []), "picked": len(w.get("picked") or [])}
    return out


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


def answered(ans):
    who = ", ".join(WHO.get(x, x) for x in ans.get("who") or [])
    return [("1. The shoot", ans.get("about")),
            ("2. Who they want to reach", " · ".join(x for x in (who, ans.get("who_text")) if x)),
            ("2c. Where it's going", WHERE.get(ans.get("where"), ans.get("where") or "")),
            ("3. What it's for", " · ".join(x for x in (PURPOSE.get(ans.get("purpose"), ans.get("purpose") or ""), ans.get("purpose_text")) if x)),
            ("4. Anything to include or leave out", ans.get("notes"))]


# ---------- the commands ----------

def cmd_show(kit, piece):
    rec = load(kit)
    w = piece_of(rec, piece)
    ans = w["answers"]
    say(RULES.format(task=f"{HOW_MANY[piece]} {WHAT[piece]}, and one caption" if HOW_MANY[piece]
                     else "one caption, and no cover lines (Nicole, Nov 10: they can figure that out themselves)"))
    hb = homebase()
    if hb:
        say(f"\nTheir Brand Homebase: {hb}  (read it in full before you write)")
    else:
        say("\nNo Brand Homebase found. Ask them where it is, or write from their answers and say it isn't on their brand yet.")
        v = kitmod.voice()
        if v.get("samples") or v.get("never"):
            say("  What they gave when asked how they write (kit.py voice), until there is a Homebase:")
            for s in (v.get("samples") or [])[:5]:
                say("    A caption they posted: " + s.replace("\n", " / "))
            for s in (v.get("never") or [])[:5]:
                say("    They'd never write: " + s.replace("\n", " / "))
    say("")
    say(f"{kit.name}, the {piece}: what they said")
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
    ow = piece_of(rec, other)
    if ow.get("caption"):
        say(f"\nThe {other}'s caption, already written (their answers carry over; the words must not repeat):")
        say("  " + ow["caption"].replace("\n", " / "))
        say(f"  The {piece} caption must be genuinely DIFFERENT from this one (Nicole, Nov 10: someone who sees both"
            f" shouldn't feel like they're reading a slightly different version). Same facts, same goal in the opening"
            f" lines, but a different way in: a different opening line and angle, a different part of their story up"
            f" front, a different shape and different sentences. Don't reuse its lines or reword them one by one."
            f" Use only their answers for facts; their answers are your source, this caption is only what to avoid."
            + (f" Then write new {WHAT[piece].split(' (')[0]}, different from the {other}'s too." if HOW_MANY[piece] else ""))
    if w.get("caption") or w.get("hooks"):
        say("\nAlready written (a new draft replaces it; the version before is kept):")
        if w.get("caption"):
            say("  Caption: " + w["caption"].replace("\n", " / "))
        for i, h in enumerate(w.get("hooks") or [], 1):
            say(f"  {i}. {h}")
    return 0


def cmd_ask(kit, piece):
    w = piece_of(load(kit), piece)
    what = WHAT[piece].split(" (")[0] if HOW_MANY[piece] else "caption"
    say(ASK.format(piece=piece, what=what).replace("the caption and caption are", "the caption is"))
    say("")
    say(f"{kit.name}, the {piece}: answered so far")
    for k, v in answered(w["answers"]):
        say(f"  {k}: {(v or '').strip() or '(not yet)'}")
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
    c = sub.add_parser("carry")
    c.add_argument("words"); c.add_argument("piece", choices=PIECES); c.add_argument("to", choices=PIECES)
    a = ap.parse_args(argv)
    fresh.announce()
    kit = kitmod.find_kit(a.words)
    try:
        if a.cmd == "show":
            return cmd_show(kit, a.piece)
        if a.cmd == "ask":
            return cmd_ask(kit, a.piece)
        if a.cmd == "answer":
            done = save_answers(kit, a.piece, read_json(a.file))
            say(f"Saved {', '.join(done)} for the {kit.name} {a.piece}. The page shows it in a few seconds.")
            return 0
        if a.cmd == "draft":
            cap, n = save_draft(kit, a.piece, read_json(a.file))
            say(f"Saved the {a.piece} words for {kit.name}: " + ("a caption" if cap else "") + (" and " if cap and n else "")
                + (f"{n} {WHAT[a.piece].split(' (')[0]}" if n else "") + ". The page shows them in a few seconds.")
            return 0
        if a.cmd == "carry":
            if a.piece == a.to:
                raise Stop("carry goes from one piece to the other")
            done = carry(kit, a.piece, a.to)
            say(f"Carried {', '.join(done)} from the {a.piece} to the {a.to}. They don't have to answer again.")
            return 0
    except Stop as e:
        say(f"STOP: {e}. Nothing was saved.")
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
