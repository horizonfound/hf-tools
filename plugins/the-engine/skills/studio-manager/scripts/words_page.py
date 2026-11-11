#!/usr/bin/env python3
"""The words page: where the photographer tells the Assistant about a post, and where its caption and hooks show
up (Nicole's handoff v20, pages/words.html, rebuilt our way: stage 1 of the v21 build).

What the photographer sees is hers, word for word (WORDS below): the Reel and Carousel tabs, the strip of that
piece's photos, step 1 "Tell me about it" (the five questions, each with its line of teaching), step 2 "Your
words" (the caption, ten hooks with Pick and Copy for a reel, write your own), step 3 "Post it" (her numbered
steps, the posting queue step, the other piece's box). Underneath it is ours:

  * it is served by the one page server (posting_queue.py hands every request for it to handle_get / handle_post
    here), never a second server, and every POST goes through the pickers' guard (arrange.guard: this server's
    own name in Host, this server's own page in Origin, JSON, a length under the cap);
  * a kit is named by its folder's name in Your Content and nothing else (arrange.kit_by_name); no path is ever
    sent to the page or taken from it; every word of theirs reaches the page as text, never as HTML;
  * the words record is words.py's (<kit>/.kit/post-words.json): this file reads and saves only through it;
  * "Add to my queue" asks the posting queue in this same process, under its own lock (no command is run);
  * the look is look.py's (DM Sans from /look-font, nothing from the internet); where hers sets the lines to
    copy in a serif italic, ours are DM Sans, slanted (Dustin, Nov 7: no serif).

Routes, all on the posting server:
    GET  /words.html?kit=<kit folder>&piece=reel|carousel     the page
    GET  /words-state?kit=&piece=                             everything the page draws from; asked every 2.5 s
    POST /words-save   {kit, piece, answers?, own?, caption?, picked?}     saved by words.save_from_page
    POST /words-carry  {kit, piece}                           this piece's answers copied to the other (words.carry)
    POST /words-rhythm {text}                                 how often they post, asked once, from her five chips
    POST /words-queue  {kit, piece}                           the piece goes in the posting queue, ready to post
    POST /words-open   {kit}                                  opens the kit's Carousel folder (ours; see OUR_WORDS)

For stage 3 (the posting queue's grid photo picker): the page already shows her grid-photo lines when the
piece in the queue carries a "cover" (see queue_state): a reel's "Before you share, tap Edit cover...", with the
queue's own tile small beside it, and a carousel's "Your grid preview uses slide 3..." when the cover is
"Carousel/<a slide's file name>" and that slide isn't the first.

A Mac and a PC: nothing here is the computer's own way of doing anything; the few lines of hers that name
AirDrop or an Apple ID have a PC's line beside them (PC_WORDS).
"""
import html
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import parse_qs, quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402
import arrange  # noqa: E402
import kit as kit_mod  # noqa: E402
import brand  # noqa: E402
import look  # noqa: E402
import words as words_mod  # noqa: E402

GET_PATHS = ("/words.html", "/words-state")
POST_PATHS = ("/words-save", "/words-carry", "/words-rhythm", "/words-queue", "/words-open")
PIECES = words_mod.PIECES                # reel, carousel: no words for stories (Nicole, Nov 10)
OTHER = {"reel": "carousel", "carousel": "reel"}
SAVE_AFTER_MS = 600                      # hers: saved 600 ms after they stop typing
LOOK_EVERY_MS = 2500                     # hers: the page looks for answers given in the chat, and new drafts, every 2.5 s
TYPING_MS = 5000                         # hers: nothing is filled in within 5 s of their last key
STRIP_REEL, STRIP_SLIDES = 12, 10        # hers: the first 12 reel photos, the first 10 slides
RHYTHMS = ("Every day", "Every other day", "3 a week", "Twice a week", "Once a week")     # her five chips
POSTING_PAGE = "/posting.html"           # "See it in my feed": the posting queue, on this same server
SAVE_KEYS = {"kit", "piece", "answers", "own", "caption", "picked"}
ANSWER_KEYS = ("about", "who", "who_text", "where", "purpose", "purpose_text", "notes")

# Her words (pages/words.html, handoff v20), word for word. {short} is the shoot's short name, {piece} "reel" or
# "carousel", {other} the other of the two.
WORDS = {
    "back_kit": "Back to the post kit",
    "eyebrow": "Your words · ",
    "tab_reel": "Reel", "tab_carousel": "Carousel",
    "title": "{short} {piece} words",
    "doc_title": "{short} {piece} · your words",
    "lede": "Your captions and hooks should come from your heart. Tell me about this post in your own words, the way you'd tell a friend. I'll shape what you said like an editor would, and keep it true to your brand. Or write your own and I'll polish it.",
    # step 1
    "s1_h2": "Tell me about it",
    "s1_say": "Answer what you can. A sentence or two is plenty.",
    "talk_b": "Rather talk it out?",
    "talk": "Copy this into the chat and I'll ask you these questions one at a time. Press the microphone in the chat box and just talk. Your answers fill in here as you go.",
    "talk_line": "Ask me about the {short} {piece}",
    "copy": "Copy",
    "q_about": "Tell me about this shoot",
    "q_about_small": "Every caption needs a backstory. What was the shoot for: a family session, a milestone, a brand? Who was there, and what happened? What stood out to you that day that you'd want people to notice? Tell me the way you'd tell a friend. The real story is what makes people stop scrolling.",
    "about_ph": "Tell me about it…",
    "q_who": "Who are you trying to reach?",
    "q_who_small": "Every post you make is trying to reach someone. Who are you trying to reach with this one? The clearer you are about who it's for, the more it will speak to them.",
    "who_new": "New clients", "who_past": "Past clients", "who_followers": "Everyone who follows me", "who_photographers": "Other photographers",
    "who_ph": "Optional: tell me about them. Who are they, and what do they care about?",
    "q_where": "Where is this reel going?",
    "q_where_small": "A trial reel is shown to people who don't follow you yet, so its first second has to stop a stranger. A reel on your feed goes to your followers too.",
    "where_feed": "On my feed", "where_trial": "A trial reel",
    "q_purpose": "What is this post trying to do?",
    "q_purpose_small": "Every post should have a job. Do you want to share your work, book more sessions, or let people know about something coming up, like mini sessions?",
    "purpose_share": "Share my work", "purpose_book": "Book more sessions", "purpose_offer": "Something coming up", "purpose_other": "Something else",
    "purpose_ph": "Optional: tell me more",
    "purpose_ph_offer": "What's coming up? Mini sessions, a new offer… the dates, how to book, anything people should know.",
    "purpose_ph_book": "Optional: what kind of sessions? How should people book?",
    "q_notes": "Anything to include or leave out?",
    "q_notes_small": "Do you want their names in it? Something not to mention, how people should book or reach you…",
    "notes_ph": "Optional",
    "saved": "Saved ✓",
    "not_saved": "Not saved. Is the photo drive plugged in?",
    # step 2
    "s2_h2": "Your words",
    "copy_say_reel": "When you've told me about it, copy this into the chat. I'll edit what you said into a caption and 10 hooks (the line on the reel's first photo), and they'll show up right here.",
    "copy_say_carousel": "When you've told me about it, copy this into the chat. I'll edit what you said into a caption, and it'll show up right here.",
    "write_line": "Write my words for the {short} {piece}",
    "caption_h": "Caption",
    "copy_caption": "Copy caption",
    "caption_empty": "Your caption shows up here.",
    "hooks_h": "Hooks",
    "copy_picks": "Copy my picks",
    "hooks_say": "Pick the ones you love. Try a different one on each version of the reel.",
    "hooks_empty": "Your hooks show up here.",
    "pick": "Pick", "picked": "✓ Picked",
    "or": "or write your own",
    "own_say_a": "Rather write the caption yourself? Write it here. If you'd like, copy ",
    "polish_quoted": "“Polish my caption for the {short} {piece}”",
    "own_say_b": " into the chat and I'll tidy it, keeping your words.",
    "own_ph": "Your caption, in your words",
    "copy_own": "Copy my caption",
    "copy_polish": "Copy the polish line",
    # step 3
    "s3_h2": "Post it",
    "s3_say": "Nothing posts by itself. Here's your next step, one at a time.",
    "r1_h": "Put your hook on the reel",
    "r1": "Pick the hook you love above, copy it, and add it as text on the first second of your reel in CapCut{project}.",
    "copy_hook": "Copy my hook",
    "r2_h": "Export it and send it to your phone",
    "r2": "In CapCut, press Export. Then AirDrop the video to your phone, or save it wherever you post from.",
    "cap_h": "Copy your caption",
    "cap": "If your iPhone uses the same Apple ID as this computer, what you copy here pastes right on your phone. If not, text or email it to yourself.",
    "q_h": "Add it to your posting queue",
    "q_locked": "Once your {piece} is made and has its caption, add it here to see it in your feed and give it a date.",
    "q_ready": "Want to see it in your feed first? Add it to your queue and it gets a date, too.",
    "q_add": "Add to my queue",
    "q_how_often": "How often do you want to post?",
    "q_adding": "Adding it…",
    "q_added_a": "It's in your queue",
    "q_added_date": ", down for {day}",
    "q_added_b": ". See how it looks in your grid before you post.",
    "q_posted": "Posted ✓",
    "q_feed": "See it in my feed →",
    "r5_h": "Post it on Instagram",
    "r5": "Upload the reel, paste your caption, and share it.",
    "r5_trial": "Upload the reel, paste your caption, and turn on Trial reel before you share.",
    "r5_cover": " Before you share, tap Edit cover and choose this photo, the one you picked for your grid.",
    "cover_alt": "Your cover photo",
    "c1_h": "Send your slides to your phone",
    "c1": "Your {n} slides are in the {short} folder on your photo drive, in Carousel. AirDrop them to your phone in order.",
    "c4": "Pick all your slides in order, paste your caption, and share it.",
    "c4_cover": " Your grid preview uses slide {n}, but Instagram shows the first slide. Move slide {n} to the front in the carousel designer first so your feed matches.",
    # the other piece
    "o_ready_h": "Your {other} words are ready too",
    "o_ready_reel": "You already have a caption and {n} hooks for the {short} reel.",
    "o_ready_carousel": "You already have a caption for the {short} carousel.",
    "o_go": "Go to the {other} words →",
    "o_waiting_h": "Your {other} is waiting for its words",
    "o_waiting": "You've already told me about the {other}. Copy this into the chat and I'll write it, a version of these words made for a {other}.",
    "o_line": "Write my words for the {short} {other}",
    "o_make_h": "Make a version for your {other}?",
    "o_make": "You have a {other} from this shoot too. I'll carry over everything you told me, so you don't have to answer again, and write a version of these words made for a {other}.",
    "o_yes": "Yes, make the {other} version",
    # the small notes that come up at the bottom of the page
    "copied": "Copied ",
    "what_line": "the line. Paste it into the chat.",
    "what_caption": "your caption",
    "what_picks": "your picks",
    "what_one": "that one",
    "what_hook": "your hook",
    "copy_failed": "Select the words and copy them",
    "pick_first": "Pick one above first",
    "no_caption": "Your caption isn't written yet",
    "added": "Added to your posting queue",
    "cant_add": "I couldn't add it",
    "rhythm_not_saved": "Not saved",
    "carried": "Carried over to the {other}",
}

# Ours, where hers would say something that isn't true in our build, or has no line at all. Each is in the note
# for Nicole ("what differs from hers").
OUR_WORDS = {
    # hers always says "Your N slides are in ...", even with none made, and "1 slides"
    "c1_none": "Your slides aren't made yet. Once they are, they'll be in the {short} folder, in Carousel.",
    "c1_one": "Your slide is in the {short} folder on your photo drive, in Carousel. AirDrop it to your phone.",
    # the test for anything a photographer sees (Oct 30): a folder that is named has its button beside it
    "open_carousel": "Open the Carousel folder",
    "opened": "Opened Carousel in {app}.",
    "cant_open": "Could not open the folder. Ask your assistant to open it.",
    # "Yes, make the ... version" with nothing answered yet: hers shows "You've already told me about the carousel"
    "nothing_to_carry": "Tell me about it above first",
    "cant_reach": arrange.CANT_REACH,
    "queue_cant": "The posting queue couldn't be saved just now. Tell your assistant.",
}
ON_DRIVE = " on your photo drive"        # her words; left out when Your Content is on the computer's own disk

# A PC: the lines of hers that name AirDrop, an iPhone and an Apple ID (a Mac's way) say a PC's way instead.
PC_WORDS = {
    "r2": "In CapCut, press Export. Then send the video to your phone, or save it wherever you post from.",
    "cap": "Text or email it to yourself, so it's on your phone when you post.",
    "c1": "Your {n} slides are in the {short} folder on your photo drive, in Carousel. Send them to your phone in order.",
}
OUR_PC_WORDS = {
    "c1_one": "Your slide is in the {short} folder on your photo drive, in Carousel. Send it to your phone.",
}

CANT_FIND = arrange.CANT_FIND
NOT_UNDERSTOOD = arrange.NOT_UNDERSTOOD


def say(msg):
    arrange.say(msg)


def short_name(name):
    """Hers (server.py short_name): the folder name without a leading date."""
    return kit_mod.short_name(name)


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _pq():
    """The posting queue, as the page server itself loaded it. The server is posting_queue.py run as a program,
    so its own copy (with the one lock every press on the posting page takes) is the program's main module; a
    second copy brought in by name would have a lock of its own. Anywhere else (a test, a command), by name."""
    m = sys.modules.get("__main__")
    if m is not None and Path(getattr(m, "__file__", "") or "x").name == "posting_queue.py" and hasattr(m, "_POSTING_LOCK"):
        return m
    import posting_queue
    return posting_queue


# ---------- what the page draws from ----------

def piece_for_page(w):
    """One piece of the words record as the page reads it: every answer in its own shape, text only."""
    a = w.get("answers") if isinstance(w.get("answers"), dict) else {}
    who = [x for x in (a.get("who") or []) if x in words_mod.WHO] if isinstance(a.get("who"), (list, tuple)) else []
    hooks = [str(h) for h in (w.get("hooks") or []) if isinstance(h, str)] if isinstance(w.get("hooks"), (list, tuple)) else []
    picked = [i for i in (w.get("picked") or []) if type(i) is int and 0 <= i < len(hooks)] if isinstance(w.get("picked"), (list, tuple)) else []

    def text(v):
        return v if isinstance(v, str) else ""
    return {"answers": {"about": text(a.get("about")), "who": who, "who_text": text(a.get("who_text")),
                        "where": a.get("where") if a.get("where") in words_mod.WHERE else "",
                        "purpose": a.get("purpose") if a.get("purpose") in words_mod.PURPOSE else "",
                        "purpose_text": text(a.get("purpose_text")), "notes": text(a.get("notes"))},
            "caption": text(w.get("caption")), "hooks": hooks, "picked": sorted(set(picked)), "own": text(w.get("own"))}


def kit_facts(kit):
    """Is the reel made (its CapCut project's name), and the carousel's slides as the kit page shows them."""
    import reel_page
    try:
        rec = kit_mod.load_rec(kit)
    except (OSError, ValueError):
        rec = {}
    if not isinstance(rec, dict):
        rec = {}
    try:
        project = reel_page.newest_project(kit, rec) or ""
    except (OSError, ValueError, TypeError, AttributeError):
        project = ""
    try:
        slides = [p.name for p in kit_mod.carousel_shown(kit, rec)["files"]]
    except (OSError, ValueError, TypeError, AttributeError):
        slides = []
    return rec, project, slides


def on_photo_drive(kit):
    """Her carousel line says the slides are "on your photo drive". True unless Your Content is on the
    computer's own disk (then the page leaves those four words out, so the line stays true)."""
    try:
        import studio_file
        return not studio_file.on_internal_disk(kit)
    except (Exception, SystemExit):  # noqa: BLE001
        return True


def strip_for_page(kit, piece, rec, slides):
    """The addresses of the small pictures under the tabs, and whether a reel photo's small copy is still to be
    made. The reel: its photos in the order Make my reel would use, as the copies the pickers already make
    (/kit-photo, by number). The carousel: its slides, the pieces the Assistant made (/content). Never a photo
    itself, never a path."""
    kq = quote(kit.name, safe="")
    if piece == "carousel":
        return ["/content/%s/Carousel/%s" % (kq, quote(n, safe="")) for n in slides[:STRIP_SLIDES]], False
    import reel_page
    rows = arrange.sheet_rows(kit)
    if not rows:
        return [], False
    try:
        order = reel_page.order_for_kit_page(kit, rows, rec)
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        order = []
    by_n = {x["n"]: x for x in rows}
    shown = [by_n[x["n"]] for x in order if x.get("n") in by_n][:STRIP_REEL]
    if not shown:
        return [], False
    photos, _ = arrange.page_photos(kit, rec, shown)
    need = any(not p["have"] and not p["missing"] for p in photos)
    return ["/kit-photo?kit=%s&n=%d&size=s&v=%s" % (kq, p["n"], quote(p["v"] or "", safe="")) for p in photos if not p["missing"] or p["have"]], need


def piece_id(pq, kit, piece, p=None):
    """The posting queue's own name for this kit's reel or carousel: the one its piece in the queue carries
    (posting_queue.kit_piece: found by the folder the piece was made from, never by the folder's name made
    short, which two shoots can share), or, when it isn't in the queue yet, the name it would be given."""
    if p is None:
        p = _queue_file(pq) or {"pieces": []}
    x = pq.kit_piece(p, kit, piece)
    return x["id"] if x is not None else "%s-%s" % (pq.kit_sid(p, kit), piece)


def _same_kit(x, kit):
    """Is this posting-queue piece this kit's own? The queue's one rule (posting_queue.same_kit): by the folder
    the piece was made from, so two shoots whose names shorten alike ("Fake beach" and "Fake-beach") are never
    shown or changed as one another."""
    return _pq().same_kit(x, kit)


def _queue_file(pq):
    """The posting queue as it is saved, for reading. An unreadable file reads as empty here (the queue's own
    load stops the program; a page server must answer)."""
    try:
        p = pq.load()
    except (Exception, SystemExit):  # noqa: BLE001  (a file that is JSON but not a queue, say a list, included)
        return None
    return p if isinstance(p, dict) and isinstance(p.get("pieces"), list) else None


def queue_state(kit, piece, slides):
    """This piece in the posting queue: {interval (is a rhythm set), status, date, cover, cover_slide, thumb}.
    "cover" is stage 3's (the photo they picked for the grid tile, kept on the piece): when a green piece
    carries one, a reel shows her "tap Edit cover" line with the queue's tile, and a carousel whose cover is
    "Carousel/<file>" says which slide it is when that isn't the first."""
    out = {"interval": False, "status": "", "date": "", "cover": False, "cover_slide": 0, "thumb": ""}
    pq = _pq()
    p = _queue_file(pq)
    if p is None:
        return out
    out["interval"] = bool(p.get("interval"))
    x = pq.kit_piece(p, kit, piece)          # this kit's own piece, by the folder it was made from
    if x is None:
        return out
    out["status"] = x.get("status") if isinstance(x.get("status"), str) else ""
    out["date"] = x.get("date") if isinstance(x.get("date"), str) else ""
    cover = x.get("cover")
    if out["status"] == "green" and isinstance(cover, str) and cover:
        out["cover"] = True
        if piece == "carousel":
            name = _nfc(cover[len("Carousel/"):] if cover.startswith("Carousel/") else cover)
            names = [_nfc(n) for n in slides]
            out["cover_slide"] = names.index(name) + 1 if name in names else 0
        thumb = x.get("thumb")
        if isinstance(thumb, str) and thumb and ".." not in thumb.split("/") and not thumb.startswith("/"):
            out["thumb"] = "/" + "/".join(quote(part, safe="") for part in thumb.split("/"))
    return out


def state(kit, piece, facts=None):
    """Everything the page draws from, for one piece. No path is in it."""
    rec_kit, project, slides = facts or kit_facts(kit)
    rec = words_mod.load(kit)
    w = piece_for_page(words_mod.piece_of(rec, piece))
    other = OTHER[piece]
    st = words_mod.status(kit)[other]
    strip, need = strip_for_page(kit, piece, rec_kit, slides)
    return {
        "ok": True, "piece": piece, "short": short_name(kit.name),
        "w": w,
        "kit": {"reel": project, "slides": len(slides), "made": bool(project) if piece == "reel" else bool(slides),
                "on_drive": on_photo_drive(kit)},
        "other": {"piece": other, "has": bool(project) if other == "reel" else bool(slides),
                  "answered": bool(st["answered"]), "caption": bool(st["caption"]), "hooks": int(st["hooks"])},
        "strip": strip, "strip_wait": need,
        "queue": queue_state(kit, piece, slides),
    }


# ---------- what the page sends ----------

def _bad(words=NOT_UNDERSTOOD, code=400, **more):
    d = {"ok": False, "words": words}
    d.update(more)
    return code, d


def _kit_and_piece(body, keys):
    """(kit, piece) for a POST's body, or (None, the answer to send). Only the fields the route takes."""
    if set(body) - set(keys):
        return None, _bad()
    piece = body.get("piece")
    if "piece" in keys and piece not in PIECES:      # stories, or anything else: words are for a reel or a carousel
        return None, _bad()
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return None, _bad(WORDS["not_saved"], 404)
    return (kit, piece), None


def save_from_page(body):
    """POST /words-save {kit, piece, answers?, own?, caption?, picked?}. Each part in its own shape, or nothing
    is saved; words.py holds every text to its limit. The hooks themselves are only ever written from the chat."""
    got, no = _kit_and_piece(body, SAVE_KEYS)
    if no:
        return no
    kit, piece = got
    given = {}
    if "answers" in body:
        a = body["answers"]
        if not isinstance(a, dict) or set(a) - set(ANSWER_KEYS):
            return _bad()
        for k, v in a.items():
            if k == "who":
                if not isinstance(v, list) or len(v) > 20 or not all(isinstance(x, str) for x in v):
                    return _bad()
            elif not isinstance(v, str):
                return _bad()
        given["answers"] = a
    for k in ("own", "caption"):
        if k in body:
            if not isinstance(body[k], str):
                return _bad()
            given[k] = body[k]
    if "picked" in body:
        ps = body["picked"]
        if not isinstance(ps, list) or len(ps) > words_mod.HOOKS_MOST or not all(type(i) is int for i in ps):
            return _bad()
        given["picked"] = ps
    if not given:
        return _bad()
    try:
        w = words_mod.save_from_page(kit, piece, given)
    except words_mod.Stop:
        return _bad()
    except OSError as e:
        arrange.log(f"words page: couldn't save the words of {kit.name!r} ({e.__class__.__name__}: {str(e)[:160]})")
        return _bad(WORDS["not_saved"], 503)
    return 200, {"ok": True, "piece": piece_for_page(w)}


def carry_from_page(body):
    """POST /words-carry {kit, piece}: this piece's answers are copied to the other one (never "where"), so
    they don't answer twice (words.carry)."""
    got, no = _kit_and_piece(body, {"kit", "piece"})
    if no:
        return no
    kit, piece = got
    try:
        words_mod.carry(kit, piece, OTHER[piece])
    except words_mod.Stop:
        return 200, {"ok": False, "words": OUR_WORDS["nothing_to_carry"]}
    except OSError as e:
        arrange.log(f"words page: couldn't carry the answers of {kit.name!r} ({e.__class__.__name__}: {str(e)[:160]})")
        return _bad(WORDS["not_saved"], 503)
    return 200, {"ok": True}


def set_rhythm(body):
    """POST /words-rhythm {text}: how often they post, from her five chips, asked the first time a piece is
    added. A rhythm that is already set is left as it is (the posting queue is where it changes)."""
    if set(body) - {"text"} or body.get("text") not in RHYTHMS:
        return _bad()
    pq = _pq()
    v = pq.parse_interval(body["text"])
    if not v:
        return _bad()
    try:
        with pq._POSTING_LOCK:
            p = pq.load()
            if not p.get("interval"):
                p["interval"] = v
                pq.schedule(p, reflow=True)
                pq.save(p)
                pq.write_page(p)
    except (OSError, SystemExit) as e:
        arrange.log(f"words page: couldn't save the posting rhythm ({e.__class__.__name__}: {str(e)[:160]})")
        return _bad(OUR_WORDS["queue_cant"], 503)
    return 200, {"ok": True}


def add_to_queue(body):
    """POST /words-queue {kit, piece}: the piece is finished, so it goes in the posting queue, ready to post
    (decision 7), and gets a date when a rhythm is set. Only a piece that is made and has its caption (hers);
    asked of the posting queue here in the server, under the lock every press on the posting page takes."""
    got, no = _kit_and_piece(body, {"kit", "piece"})
    if no:
        return no
    kit, piece = got
    facts = kit_facts(kit)
    _, project, slides = facts
    made = bool(project) if piece == "reel" else bool(slides)
    # the one rule both pages unlock on (words.status): a drafted caption, or one they typed themselves
    if not made or not words_mod.status(kit)[piece]["caption"]:
        return 409, {"ok": False, "words": WORDS["q_locked"].replace("{piece}", piece)}
    pq = _pq()
    try:
        with pq._POSTING_LOCK:
            p = pq.load()
            # another shoot whose name shortens to the same one keeps its own pieces: this kit's get a name of
            # their own (posting_queue.kit_sid), and each is found by the folder it was made from
            pq.add_for_kit(p, kit)
            x = pq.kit_piece(p, kit, piece)
            if x is None:
                return _bad(WORDS["cant_add"], 500)
            if x.get("status") not in ("green", "posted"):
                pq.set_status(p, x, "green", by="words page")
            pq.schedule(p)
            pq.save(p)
            pq.write_page(p)
    except (OSError, SystemExit, ValueError, KeyError, TypeError) as e:
        arrange.log(f"words page: couldn't add {kit.name!r} {piece} to the posting queue ({e.__class__.__name__}: {str(e)[:160]})")
        return _bad(OUR_WORDS["queue_cant"], 503)
    return 200, {"ok": True, "queue": queue_state(kit, piece, slides)}


def open_carousel(body):
    """POST /words-open {kit}: opens the kit's own Carousel folder (the one her line names), nothing else."""
    import reel_page
    if set(body) - {"kit"}:
        return _bad()
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    d = kit / "Carousel"
    try:
        ok_folder = d.is_dir() and not d.is_symlink()
    except OSError:
        ok_folder = False
    if not ok_folder:
        return 200, {"ok": False, "words": OUR_WORDS["cant_open"]}
    ok, note = reel_page._open_folder(d)
    if not ok:
        arrange.log(f"words page: the Carousel folder couldn't be opened: {str(note)[:200]}")
        return 200, {"ok": False, "words": OUR_WORDS["cant_open"]}
    said = OUR_WORDS["opened"].replace("{app}", this_computer.FILES_APP)
    if note == "behind":
        said = said[:-1] + reel_page.OUR_WORDS["behind"]
    return 200, {"ok": True, "words": said}


# ---------- the routes ----------

def _one(q, key):
    v = q.get(key, [""])
    return v[0] if v else ""


def _cross_site(handler):
    return (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site"


def _get_page(handler, q):
    import arrange_page
    if _cross_site(handler):
        # a link from another website: the plain "can't find" page, and nothing is looked at
        return arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
    kit = arrange.kit_by_name(_one(q, "kit"))
    piece = _one(q, "piece") or "reel"
    if kit is None or piece not in PIECES:
        return arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
    rec_kit, project, slides = kit_facts(kit)
    _, need = strip_for_page(kit, piece, rec_kit, slides)
    if need:
        try:
            if not arrange.cant_make(kit, arrange.sheet_rows(kit)):
                arrange.start_previews(kit)          # a reel photo in the strip has no small copy yet: made in the background
        except (Exception, SystemExit) as e:  # noqa: BLE001  (the strip only; the page still opens)
            arrange.log(f"words page: the small copies couldn't be started ({e.__class__.__name__})")
    arrange._send_page(handler, page_html(kit.name, piece))


def _get_state(handler, q):
    if _cross_site(handler):
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 403)
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_json(handler, {"ok": False, "words": CANT_FIND}, 404)
    piece = _one(q, "piece")
    if piece not in PIECES:
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 404)
    arrange._send_json(handler, state(kit, piece))


def handle_get(handler, path, query):
    """Every GET for the words page. Whatever goes wrong, the server answers and stays up."""
    try:
        if not arrange.our_host(handler):
            return handler.send_error(403)
        q = parse_qs(query or "", keep_blank_values=True)
        if path == "/words.html":
            return _get_page(handler, q)
        if path == "/words-state":
            return _get_state(handler, q)
        return handler.send_error(404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        arrange.log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            if path.endswith(".html"):
                import arrange_page
                arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
            else:
                arrange._send_json(handler, {"ok": False, "words": OUR_WORDS["cant_reach"]}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def handle_post(handler, path, query):
    """Every POST for the words page, after the pickers' guard (reel_page._json_body: arrange.guard, then the
    body as one JSON object). Whatever goes wrong, the server answers and stays up."""
    try:
        import reel_page
        body = reel_page._json_body(handler, path)
        if body is None:
            return
        route = {"/words-save": save_from_page, "/words-carry": carry_from_page, "/words-rhythm": set_rhythm,
                 "/words-queue": add_to_queue, "/words-open": open_carousel}.get(path)
        if route is None:
            return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 404)
        code, out = route(body)
        return arrange._send_json(handler, out, code)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        arrange.log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            arrange._send_json(handler, {"ok": False, "words": OUR_WORDS["cant_reach"]}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


# ---------- the page ----------
# Her stylesheet (pages/words.html, v20) as she wrote it, with these changes. The Google Fonts link is gone and her
# colour names and the rules every page shares come from look.py. No serif (Dustin, Nov 7): her Fraunces italic
# touches (the coral full stop after the title, the lines to copy, the "shows up here" lines) are DM Sans, the
# lines to copy still slanted. OUR_CSS adds what ours needs and hers lacks.
STYLE = r"""
.wrap{max-width:900px;margin:0 auto;padding:0 clamp(16px,4vw,40px) 6rem}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand b{font:600 16px/1 var(--sans)}.brand small{display:block;margin-top:4px;font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.head{padding:clamp(1.8rem,4vw,3rem) 0 .6rem;display:grid;gap:.5rem}
h1{margin:0;font:600 clamp(30px,4.4vw,48px)/1.03 var(--sans);letter-spacing:-.035em}
.lede{margin:0;color:var(--ink-2);font-size:clamp(15.5px,1.3vw,17.5px);max-width:40em}
.lede b{color:var(--ink)}
.pieces{display:flex;gap:.4rem;margin:1rem 0 0;flex-wrap:wrap}
.pieces a{font:600 14px/1 var(--sans);text-decoration:none;color:var(--ink);border:1.5px solid var(--line);border-radius:999px;padding:.55rem 1rem;background:var(--paper)}
.pieces a.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.strip{display:flex;gap:6px;overflow:hidden;margin:.9rem 0 0}
.strip img{height:96px;width:64px;flex:none;border-radius:9px;object-fit:cover;background:var(--sand-l);box-shadow:0 0 0 1px var(--line)}
.strip.wide img{width:77px}
.step{background:var(--paper);border-radius:22px;padding:1.3rem;margin-top:1.1rem;box-shadow:0 1px 0 var(--line)}
.step h2{display:flex;align-items:center;gap:.6rem;margin:0 0 .3rem;font:600 21px/1.2 var(--sans);letter-spacing:-.02em}
.num{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--ink);color:#fff;font:600 13px/1 var(--sans);flex:none}
.say{margin:.2rem 0 .9rem;color:var(--ink-2);font-size:15px;max-width:44em}
.say b{color:var(--ink);font-weight:600}
.q{border-top:1px solid var(--line);padding:1rem 0 .4rem}
.q:first-of-type{border-top:0;padding-top:.3rem}
.q > b{display:block;font-weight:600;font-size:16.5px}
.q > small{display:block;color:var(--ink-2);font-size:14px;margin:.1rem 0 .55rem}
.box{position:relative}
textarea{width:100%;font:16px/1.5 var(--sans);color:var(--ink);background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:.75rem .9rem;min-height:5.2em;resize:vertical}
textarea:focus{outline:2px solid var(--coral);outline-offset:0;border-color:transparent}
textarea.big{min-height:8em}
.chips{display:flex;gap:.45rem;flex-wrap:wrap;margin:0 0 .6rem}
.chips button{font:500 14px/1 var(--sans);padding:.6em 1em;border-radius:999px;border:1.5px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
.chips button:hover{border-color:var(--coral)}
.chips button.on{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.tip{font-size:13.5px;color:var(--ink-2);margin:.6rem 0 0}
.saved{font-size:13px;color:var(--long);min-height:1.2em;margin:.3rem 0 0}
.line{display:flex;align-items:center;gap:.8rem;flex-wrap:wrap;background:#FFF6F2;border:1.5px solid var(--coral-l);border-radius:14px;padding:.75rem .95rem;margin:.4rem 0 .2rem}
.todo{margin:.6rem 0 0;padding:0;list-style:none;counter-reset:t}
.todo li{counter-increment:t;position:relative;padding:.75rem 0 .8rem 2.6rem;border-top:1px solid var(--line)}
.todo li:first-child{border-top:0}
.todo li::before{content:counter(t);position:absolute;left:0;top:.7rem;width:1.8rem;height:1.8rem;border-radius:50%;background:#FFF6F2;border:1.5px solid var(--coral-l);display:grid;place-items:center;font:600 14px/1 var(--sans);color:var(--coral-2)}
.todo b{display:block;font-weight:600;margin-bottom:.15rem}
.todo p{margin:0 0 .45rem;color:var(--ink-2);font-size:14.5px;max-width:44em}
.coverpic{display:block;width:72px;aspect-ratio:4/5;object-fit:cover;border-radius:8px;box-shadow:0 0 0 1px var(--line);margin:.3rem 0 .2rem}
.other{margin-top:1.1rem;background:#FFF6F2;border:1.5px solid var(--coral-l);border-radius:16px;padding:1rem 1.1rem}
.other b{display:block;font:600 17px/1.3 var(--sans);margin-bottom:.25rem}
.other p{margin:0 0 .6rem;color:var(--ink-2);font-size:14.5px;max-width:44em}
.other .line{background:#fff}
.talk{margin:.2rem 0 1.1rem}
.talk p{margin:0 0 .35rem;color:var(--ink-2);font-size:15px;max-width:44em}
.talk p b{color:var(--ink);font-weight:600}
.line span{font:italic 400 18px/1.35 var(--sans);flex:1 1 260px}
.btn{display:inline-flex;align-items:center;gap:.45rem;border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:999px;padding:.55rem 1rem;font:600 14px/1 var(--sans);cursor:pointer;transition:all .2s var(--ease)}
.btn:hover{border-color:var(--coral);color:var(--coral-2)}
.btn.main{background:var(--ink);color:#fff;border-color:var(--ink)}.btn.main:hover{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.btn.small{padding:.38rem .8rem;font-size:13px}
h3{font:600 16.5px/1.2 var(--sans);margin:1.2rem 0 .45rem;display:flex;align-items:center;justify-content:space-between;gap:.6rem;flex-wrap:wrap}
.empty{font:italic 400 16px/1.35 var(--sans);color:var(--ink-2);margin:0;padding:.7rem .9rem;border:1px dashed var(--line);border-radius:14px}
.hooks{display:grid;gap:.45rem}
.hook{display:flex;align-items:center;gap:.7rem;border:1.5px solid var(--line);border-radius:12px;padding:.6rem .7rem .6rem .8rem;background:#fff}
.hook.on{border-color:var(--coral-2);background:#FFF6F2}
.hook .n{font:600 12px/1 var(--sans);color:var(--ink-2);width:1.4em;flex:none}
.hook .t{flex:1;font-size:15.5px}
.hook .pk{font:600 12.5px/1 var(--sans);border-radius:999px;padding:.45em .8em;border:1.5px solid var(--line);background:#fff;cursor:pointer;white-space:nowrap}
.hook.on .pk{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.or{display:flex;align-items:center;gap:.8rem;color:var(--ink-2);font-size:13px;margin:1.4rem 0 .2rem;text-transform:uppercase;letter-spacing:.12em;font-weight:600}
.or::before,.or::after{content:"";flex:1;height:1px;background:var(--line)}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:var(--ink);color:#fff;font:600 14px/1 var(--sans);padding:.8rem 1.1rem;border-radius:999px;opacity:0;transition:opacity .2s;pointer-events:none}
.toast.on{opacity:1}
"""

OUR_CSS = r"""
[hidden]{display:none!important}
.btn:disabled{opacity:.4;cursor:default}
.btn:disabled:hover{border-color:var(--line);color:var(--ink)}
.btn.main:disabled:hover{background:var(--ink);border-color:var(--ink);color:#fff}
.hook .t{min-width:0;overflow-wrap:anywhere}
.line span{min-width:0;overflow-wrap:anywhere}
h1,.say,.say b,.todo b,.todo p,.other b,.other p,.talk p,.q > b,.q > small,.went,.eyebrow{overflow-wrap:anywhere}
.todo li,.other,.step{min-width:0}
.toast{max-width:calc(100vw - 32px);line-height:1.3;text-align:center}
.qhow{display:block;margin:.2rem 0 .4rem}
.went{display:block;font-size:13.5px;color:var(--ink-2);margin:.35rem 0 0;min-height:0}
.otherlink{margin:.5rem 0 0}
.strip img.wait{visibility:hidden}
@media (max-width:520px){.hook{flex-wrap:wrap}.hook .t{flex-basis:100%}}
"""


def _json_for_script(obj):
    """JSON that is safe inside a <script> element (no "</script>", no "<!--")."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def page_words():
    """Every word the page shows: hers, with a PC's lines where hers name a Mac's way, and the few of ours."""
    w = dict(WORDS)
    ours = dict(OUR_WORDS)
    if this_computer.WINDOWS:
        w.update(PC_WORDS)
        ours.update(OUR_PC_WORDS)
    w.update({k: v for k, v in ours.items() if k not in w})
    w["on_drive"] = ON_DRIVE
    return w


def page_html(kit_name, piece):
    """The words page for one piece of one kit. Everything that changes arrives by /words-state."""
    e = html.escape
    w = page_words()
    short = short_name(kit_name)

    def f(key, **more):
        s = w[key].replace("{short}", short).replace("{piece}", piece).replace("{other}", OTHER[piece])
        for k, v in more.items():
            s = s.replace("{" + k + "}", v)
        return s
    kq = quote(kit_name, safe="")
    data = {"kit": kit_name, "piece": piece, "short": short, "words": w, "rhythms": list(RHYTHMS),
            "saveAfter": SAVE_AFTER_MS, "lookEvery": LOOK_EVERY_MS, "typing": TYPING_MS, "posting": POSTING_PAGE}
    tabs = "".join(
        "<a href='/words.html?kit=%s&amp;piece=%s' data-piece='%s'%s>%s</a>" % (kq, p, p, " class='on'" if p == piece else "", e(w["tab_" + p]))
        for p in PIECES)

    def chips(group, keys):
        return ("<div class='chips' id='" + group + "'>"
                + "".join("<button type='button' data-v='%s'>%s</button>" % (k, e(w[group + "_" + k])) for k in keys) + "</div>")

    def box(ident, most, ph, big=False):
        return ("<div class='box'><textarea id='%s'%s maxlength='%d' placeholder='%s'></textarea></div>"
                % (ident, " class='big'" if big else "", most, e(ph, quote=True)))
    lim = words_mod.FIELDS
    step1 = (
        "<section class='step'><h2><span class='num'>1</span>" + e(w["s1_h2"]) + "</h2>"
        "<p class='say'>" + e(w["s1_say"]) + "</p>"
        "<div class='talk'><p><b>" + e(w["talk_b"]) + "</b> " + e(w["talk"]) + "</p>"
        "<div class='line'><span id='talkLine'>" + e(f("talk_line")) + "</span>"
        "<button class='btn main' id='talkBtn' type='button'>" + e(w["copy"]) + "</button></div></div>"
        "<div class='q'><b id='qAbout'>" + e(w["q_about"]) + "</b><small>" + e(w["q_about_small"]) + "</small>"
        + box("about", lim["about"], w["about_ph"], big=True) + "</div>"
        "<div class='q'><b>" + e(w["q_who"]) + "</b><small>" + e(w["q_who_small"]) + "</small>"
        + chips("who", ("new", "past", "followers", "photographers")) + box("who_text", lim["who_text"], w["who_ph"]) + "</div>"
        "<div class='q' id='qWhere'" + ("" if piece == "reel" else " hidden") + "><b>" + e(w["q_where"]) + "</b><small>" + e(w["q_where_small"]) + "</small>"
        + chips("where", ("feed", "trial")) + "</div>"
        "<div class='q'><b>" + e(w["q_purpose"]) + "</b><small>" + e(w["q_purpose_small"]) + "</small>"
        + chips("purpose", ("share", "book", "offer", "other")) + box("purpose_text", lim["purpose_text"], w["purpose_ph"]) + "</div>"
        "<div class='q'><b>" + e(w["q_notes"]) + "</b><small>" + e(w["q_notes_small"]) + "</small>"
        + box("notes", lim["notes"], w["notes_ph"]) + "</div>"
        "<p class='saved' id='saved' role='status'></p></section>")
    step2 = (
        "<section class='step'><h2><span class='num'>2</span>" + e(w["s2_h2"]) + "</h2>"
        "<p class='say' id='copySay'>" + e(w["copy_say_" + piece]) + "</p>"
        "<div class='line'><span id='copyLine'>" + e(f("write_line")) + "</span>"
        "<button class='btn main' id='copyBtn' type='button'>" + e(w["copy"]) + "</button></div>"
        "<h3>" + e(w["caption_h"]) + " <span><button class='btn small' id='copyCap' type='button' disabled>" + e(w["copy_caption"]) + "</button></span></h3>"
        "<div id='capBox'><p class='empty'>" + e(w["caption_empty"]) + "</p></div>"
        "<div id='hooksPart'" + ("" if piece == "reel" else " hidden") + ">"
        "<h3><span id='hooksHead'>" + e(w["hooks_h"]) + "</span> <span><button class='btn small' id='copyPicks' type='button' disabled>" + e(w["copy_picks"]) + "</button></span></h3>"
        "<p class='say' id='hooksSay' style='margin:0 0 .5rem'>" + e(w["hooks_say"]) + "</p>"
        "<div class='hooks' id='hooks'><p class='empty'>" + e(w["hooks_empty"]) + "</p></div></div>"
        "<div class='or'>" + e(w["or"]) + "</div>"
        "<p class='say'>" + e(w["own_say_a"]) + "<b id='polishWords'>" + e(f("polish_quoted")) + "</b>" + e(w["own_say_b"]) + "</p>"
        + box("own", words_mod.CAPTION_MOST, w["own_ph"], big=True) +
        "<p style='margin:.5rem 0 0'><button class='btn small' id='copyOwn' type='button' disabled>" + e(w["copy_own"]) + "</button> "
        "<button class='btn small' id='copyPolish' type='button'>" + e(w["copy_polish"]) + "</button></p></section>")
    step3 = (
        "<section class='step' id='nextStep'><h2><span class='num'>3</span>" + e(w["s3_h2"]) + "</h2>"
        "<p class='say'>" + e(w["s3_say"]) + "</p><ol class='todo' id='todo'></ol>"
        "<div class='other' id='other' hidden><b id='otherHead'></b><p id='otherSay'></p><div id='otherDo'></div></div></section>")
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + e(f("doc_title")) + "</title><style>" + look.head_css() + STYLE + OUR_CSS + "</style></head>"
        "<body data-kit='" + e(kit_name, quote=True) + "' data-piece='" + piece + "'>"
        "<div class='wrap'>"
        "<div class='bar'><a class='homelink' id='back' href='/content/" + kq + "/Post%20kit.html'><span aria-hidden='true'>&larr;</span> "
        + e(w["back_kit"]) + "</a>" + brand.bar() + "</div>"
        "<header class='head'><span class='eyebrow' id='eyebrow'>" + e(w["eyebrow"] + w["tab_" + piece]) + "</span>"
        "<h1 id='title'>" + e(f("title")) + "<em>.</em></h1>"
        "<p class='lede'>" + e(w["lede"]) + "</p>"
        "<nav class='pieces' id='pieces'>" + tabs + "</nav>"
        "<div class='strip" + (" wide" if piece == "carousel" else "") + "' id='strip'></div></header>"
        + step1 + step2 + step3 +
        "</div><div class='toast' id='toast' role='status'></div>"
        "<script type='application/json' id='wordsData'>" + _json_for_script(data) + "</script>"
        "<script>" + SCRIPT + "</script></body></html>")


# The page's own script. Every word of theirs (an answer, a caption, a hook, the shoot's name) is put on the page
# as text (textContent, a box's value), never as HTML.
SCRIPT = r"""
(function(){
'use strict';
var D = JSON.parse(document.getElementById('wordsData').textContent);
var W = D.words, KIT = D.kit, PIECE = D.piece, SHORT = D.short, OTHER = PIECE === 'reel' ? 'carousel' : 'reel';
var $ = function(id){ return document.getElementById(id); };
var Q = '?kit=' + encodeURIComponent(KIT) + '&piece=';
function fill(s, o){ o = o || {}; return s.replace(/\{(\w+)\}/g, function(m, k){
  if (k in o) return o[k];
  return k === 'short' ? SHORT : k === 'piece' ? PIECE : k === 'other' ? OTHER : m; }); }
function el(tag, cls, text){ var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
function btn(cls, text){ var b = el('button', cls, text); b.type = 'button'; return b; }

var w = {answers: {}, caption: '', hooks: [], picked: [], own: ''};
var who = [], purpose = '', where = '';
var lastEdit = 0, lastCapEdit = 0, lastPickEdit = 0, lastServerAns = null, lastRest = null;
var saveT = null, capT = null, S = null, carried = false, adding = false, stripKey = null;
// Only what they touched is ever sent: "dirty" names the answers (and 'own', 'caption') changed on this page since
// the last save went out, so an answer given in the chat that this page hasn't shown yet is never written over.
var dirty = {}, inflight = 0, loaded = false, ownTouched = false, shownWhere = null, wentText = '';

function toast(t){ var e = $('toast'); e.textContent = t; e.classList.add('on'); clearTimeout(toast.t); toast.t = setTimeout(function(){ e.classList.remove('on'); }, 1600); }

// Copy: the page's own copy first (the Claude app's pane allows it from a press and refuses the newer way), the
// newer way only if that failed.
function copyText(t){
  var ok = false, was = document.activeElement;
  try {
    var ta = document.createElement('textarea');
    ta.value = t; ta.setAttribute('readonly', ''); ta.setAttribute('aria-hidden', 'true');
    ta.style.cssText = 'position:fixed;left:-9999px;top:0;width:1px;height:1px;min-height:0;opacity:0';
    document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, t.length);
    ok = !!t && document.execCommand('copy');
    document.body.removeChild(ta);
    if (was && was.focus && was !== document.body) was.focus();
  } catch (e) { ok = false; }
  if (ok) return Promise.resolve(true);
  if (t && navigator.clipboard && navigator.clipboard.writeText)
    return navigator.clipboard.writeText(t).then(function(){ return true; }, function(){ return false; });
  return Promise.resolve(false);
}
function copy(t, what){ window.wordsLastCopied = t; return copyText(t).then(function(ok){ toast(ok ? W.copied + what : W.copy_failed); return ok; }); }

function ask(path){ return fetch(path, {cache: 'no-store'}).then(function(r){ return r.json(); }); }
function post(path, body, leaving){
  var o = {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)};
  if (leaving) o.keepalive = true;          // the page is being left: the browser still delivers it
  return fetch(path, o).then(function(r){ return r.json(); });
}

/* ---------- answers: saved as they type ---------- */
function answers(){ return {about: $('about').value, who: who.slice(), who_text: $('who_text').value, purpose: purpose,
                            purpose_text: $('purpose_text').value, notes: $('notes').value, where: PIECE === 'reel' ? where : ''}; }
function waiting(){ var k; for (k in dirty) return true; return false; }
// What is waiting to be saved: only the answers they touched, their own caption if they typed in it, the
// caption if they edited it. Null when nothing is.
function changes(){
  var all = answers(), a = {}, body = {}, n = 0, k;
  for (k in dirty) {
    if (k === 'own') body.own = $('own').value;
    else if (k === 'caption') { if ($('caption')) body.caption = $('caption').value; }
    else { a[k] = all[k]; n++; }
  }
  if (n) body.answers = a;
  for (k in body) return body;
  return null;
}
function send(extra, leaving){
  var body = changes() || {}, sent = dirty, k, any = false;
  for (k in (extra || {})) body[k] = extra[k];
  for (k in body) any = true;
  if (!any) return Promise.resolve(true);
  dirty = {};
  body.kit = KIT; body.piece = PIECE;
  inflight++;
  function failed(){
    inflight--;
    for (var k in sent) dirty[k] = 1;      // still theirs to save: the next save carries it again
    $('saved').textContent = W.not_saved; return false;
  }
  return post('/words-save', body, leaving).then(function(r){
    if (!r || !r.ok) return failed();
    inflight--;
    var p = r.piece;
    // only what was sent is taken from the answer; anything else the record holds (an answer or a draft from
    // the chat) is the next look's to show, by its own rules
    if ('own' in body) w.own = p.own;
    if ('caption' in body && !dirty.caption) w.caption = p.caption;
    $('saved').textContent = W.saved;
    return true;
  }, failed);
}
function save(extra){
  lastEdit = Date.now();
  clearTimeout(saveT); saveT = null; $('saved').textContent = '';
  if (extra) return send(extra);
  saveT = setTimeout(function(){ saveT = null; send(); }, D.saveAfter);
  return null;
}
// Everything still waiting (an answer, an edit to the caption) goes now.
function flush(leaving){
  clearTimeout(saveT); saveT = null; clearTimeout(capT); capT = null;
  return waiting() ? send(null, leaving) : Promise.resolve(true);
}
['about', 'who_text', 'purpose_text', 'notes', 'own'].forEach(function(id){ $(id).addEventListener('input', function(){
  dirty[id] = 1;
  if (id === 'own') { ownTouched = true; $('copyOwn').disabled = !$('own').value; }
  save(); }); });
// Leaving the page (a tab, the way back, the pane closed) inside the 600 ms: what they typed is sent as they go.
window.addEventListener('pagehide', function(){ flush(true); });
document.addEventListener('visibilitychange', function(){
  if (document.hidden) flush(true);
  else if (loaded) load();                 // back in view: catch up at once, not at the next look
});
function chips(id){
  Array.prototype.forEach.call(document.querySelectorAll('#' + id + ' button'), function(b){ b.onclick = function(){
    var v = b.dataset.v;
    if (id === 'who') who = who.indexOf(v) >= 0 ? who.filter(function(x){ return x !== v; }) : who.concat(v);
    else if (id === 'where') where = where === v ? '' : v;
    else purpose = purpose === v ? '' : v;
    dirty[id] = 1;
    showChips(); save();
    if (id === 'where') showNext();
  }; });
}
function showChips(){
  Array.prototype.forEach.call(document.querySelectorAll('#who button'), function(b){ b.classList.toggle('on', who.indexOf(b.dataset.v) >= 0); b.setAttribute('aria-pressed', who.indexOf(b.dataset.v) >= 0); });
  Array.prototype.forEach.call(document.querySelectorAll('#purpose button'), function(b){ b.classList.toggle('on', purpose === b.dataset.v); b.setAttribute('aria-pressed', purpose === b.dataset.v); });
  Array.prototype.forEach.call(document.querySelectorAll('#where button'), function(b){ b.classList.toggle('on', where === b.dataset.v); b.setAttribute('aria-pressed', where === b.dataset.v); });
  $('purpose_text').placeholder = purpose === 'offer' ? W.purpose_ph_offer : purpose === 'book' ? W.purpose_ph_book : W.purpose_ph;
}
chips('who'); chips('purpose'); chips('where');

/* ---------- the drafts: caption and hooks ---------- */
function showDrafts(){
  var capEl = $('capBox');
  if (w.caption) {
    var t = $('caption');
    if (!t) {
      capEl.textContent = '';
      t = document.createElement('textarea'); t.id = 'caption'; t.className = 'big'; t.maxLength = 4000;
      t.setAttribute('aria-label', W.caption_h);
      capEl.appendChild(t);
      t.oninput = function(){
        lastCapEdit = Date.now(); dirty.caption = 1; $('saved').textContent = '';
        clearTimeout(capT); capT = setTimeout(function(){ capT = null; send(); }, D.saveAfter);
      };
      t.value = w.caption;
    }
    // a new draft from the chat goes in whether or not the cursor was left in the box, but never over an edit
    // of theirs: not while one is waiting or on its way, nor within 5 s of their last key in it
    if (t.value !== w.caption && !dirty.caption && !capT && !inflight && Date.now() - lastCapEdit > D.typing) {
      var here = document.activeElement === t, a0 = t.selectionStart, a1 = t.selectionEnd;
      t.value = w.caption;
      if (here) { try { t.setSelectionRange(Math.min(a0, t.value.length), Math.min(a1, t.value.length)); } catch (e) {} }
    }
  } else if (!$('caption') || document.activeElement !== $('caption')) {
    capEl.textContent = ''; capEl.appendChild(el('p', 'empty', W.caption_empty));
  }
  var hs = w.hooks || [], picked = w.picked || [], box = $('hooks');
  // the rows are made again: the keyboard's place among them (a Pick or a Copy button) is kept
  var foc = document.activeElement, focRow = foc && foc.closest && box.contains(foc) ? foc.closest('.hook') : null;
  var focAt = focRow ? [focRow.dataset.i, foc.classList.contains('pk') ? '.pk' : '.cp'] : null;
  box.textContent = '';
  if (!hs.length) box.appendChild(el('p', 'empty', W.hooks_empty));
  hs.forEach(function(h, i){
    var on = picked.indexOf(i) >= 0, row = el('div', 'hook' + (on ? ' on' : ''));
    row.dataset.i = i;
    row.appendChild(el('span', 'n', String(i + 1)));
    row.appendChild(el('span', 't', h));
    var pk = btn('pk', on ? W.picked : W.pick); pk.setAttribute('aria-pressed', on);
    pk.onclick = function(){
      var p = (w.picked || []).slice(), at = p.indexOf(i);
      if (at >= 0) p.splice(at, 1); else p.push(i);
      w.picked = p.sort(function(a, b){ return a - b; });
      lastPickEdit = Date.now();
      // this row only, in place: the button they pressed stays where the keyboard is, and says what it now is
      var now = at < 0;
      row.classList.toggle('on', now); pk.textContent = now ? W.picked : W.pick; pk.setAttribute('aria-pressed', now);
      $('copyPicks').disabled = !w.picked.length;
      save({picked: w.picked});
    };
    var cp = btn('btn small cp', W.copy);
    cp.onclick = function(){ copy(h, W.what_one); };
    row.appendChild(pk); row.appendChild(cp);
    box.appendChild(row);
  });
  if (focAt) { var back = box.querySelector('.hook[data-i="' + focAt[0] + '"] ' + focAt[1]); if (back) back.focus(); }
  $('copyCap').disabled = !w.caption; $('copyPicks').disabled = !picked.length;
}
function captionNow(){ var t = $('caption'); return (t && t.value) || w.caption || ''; }
$('talkBtn').onclick = function(){ copy($('talkLine').textContent, W.what_line); };
$('copyBtn').onclick = function(){ copy($('copyLine').textContent, W.what_line); };
$('copyCap').onclick = function(){ copy(captionNow(), W.what_caption); };
$('copyPicks').onclick = function(){ copy((w.picked || []).map(function(i){ return w.hooks[i]; }).join('\n'), W.what_picks); };
$('copyOwn').onclick = function(){ copy($('own').value, W.what_caption); };
$('copyPolish').onclick = function(){ copy($('polishWords').textContent.replace(/[“”]/g, ''), W.what_line); };

/* ---------- step 3: post it, and the other piece ---------- */
function firstHook(){ var p = w.picked || []; return p.length ? w.hooks[p[0]] : ''; }
function niceDay(iso){ try { return new Date(iso + 'T12:00:00').toLocaleDateString('en-US', {weekday: 'short', month: 'short', day: 'numeric'}); } catch (e) { return iso; } }
function step(head, text){ var li = el('li'); li.appendChild(el('b', '', head)); li.appendChild(el('p', '', text)); return li; }
function coverNote(){
  var q = S.queue;
  if (!q.cover) return '';
  if (PIECE === 'reel') return W.r5_cover;
  return q.cover_slide > 1 ? fill(W.c4_cover, {n: q.cover_slide}) : '';
}
function coverPic(li){
  var q = S.queue;
  if (!q.cover || !q.thumb) return;
  var i = el('img', 'coverpic'); i.alt = W.cover_alt; i.src = q.thumb; li.appendChild(i);
}
function queueStep(){
  var q = S.queue, li;
  if (q.status === 'green' || q.status === 'posted') {
    li = step(W.q_h, q.status === 'posted' ? W.q_posted : W.q_added_a + (q.date ? fill(W.q_added_date, {day: niceDay(q.date)}) : '') + W.q_added_b);
    var a = el('a', 'btn small', W.q_feed); a.href = D.posting; a.id = 'seeFeed';
    li.appendChild(a);
    return li;
  }
  if (!S.kit.made || !w.caption) {
    li = step(W.q_h, fill(W.q_locked));
    var b = btn('btn small', W.q_add); b.disabled = true; b.id = 'addQueue';
    li.appendChild(b);
    return li;
  }
  li = step(W.q_h, W.q_ready);
  var area = el('span'); area.id = 'qArea';
  var add = btn('btn small main', W.q_add); add.id = 'addQueue'; add.onclick = addToQueue;
  area.appendChild(add); li.appendChild(area);
  return li;
}
function addToQueue(){
  var area = $('qArea');
  if (!area || adding) return;
  if (!S.queue.interval) {
    area.textContent = '';
    area.appendChild(el('b', 'qhow', W.q_how_often));
    D.rhythms.forEach(function(t, i){
      if (i) area.appendChild(document.createTextNode(' '));
      var b = btn('btn small', t); b.dataset.iv = t;
      b.onclick = function(){
        post('/words-rhythm', {text: t}).then(function(r){
          if (!r || !r.ok) { toast((r && r.words) || W.rhythm_not_saved); return; }
          S.queue.interval = true; area.textContent = ''; addToQueue();
        }, function(){ toast(W.rhythm_not_saved); });
      };
      area.appendChild(b);
    });
    return;
  }
  adding = true;
  area.textContent = W.q_adding;
  flush().then(function(){ return post('/words-queue', {kit: KIT, piece: PIECE}); }).then(function(r){
    adding = false;
    if (!r || !r.ok) { toast((r && r.words) || W.cant_add); showNext(); return; }
    S.queue = r.queue; lastRest = null; showNext(); toast(W.added);
  }, function(){ adding = false; toast(W.cant_add); showNext(); });
}
function showNext(){
  if (!S) return;
  var todo = $('todo'), li, b;
  var foc = document.activeElement, focId = foc && foc.id && $('nextStep').contains(foc) ? foc.id : '';
  shownWhere = where;
  todo.textContent = '';
  if (PIECE === 'reel') {
    li = step(W.r1_h, fill(W.r1, {project: S.kit.reel ? ' (' + S.kit.reel + ')' : ''}));
    b = btn('btn small', W.copy_hook); b.id = 'copyHook';
    b.onclick = function(){ if (firstHook()) copy(firstHook(), W.what_hook); else toast(W.pick_first); };
    li.appendChild(b); todo.appendChild(li);
    todo.appendChild(step(W.r2_h, W.r2));
  } else {
    var n = S.kit.slides, line = n === 0 ? W.c1_none : n === 1 ? W.c1_one : fill(W.c1, {n: n});
    if (!S.kit.on_drive) line = line.replace(W.on_drive, '');
    li = step(W.c1_h, fill(line));
    if (n > 0) {
      b = btn('btn small', W.open_carousel); b.id = 'openCarousel';
      var went = el('span', 'went', wentText); went.id = 'openWent'; went.setAttribute('role', 'status');
      b.onclick = function(){
        function tell(t){ wentText = t; var e = $('openWent'); if (e) e.textContent = t; }
        post('/words-open', {kit: KIT}).then(function(r){ tell((r && r.words) || W.cant_open); },
                                             function(){ tell(W.cant_reach); });
      };
      li.appendChild(b); li.appendChild(went);
    }
    todo.appendChild(li);
  }
  li = step(W.cap_h, W.cap);
  b = btn('btn small', W.copy_caption); b.id = 'copyCap2';
  b.onclick = function(){ if (captionNow()) copy(captionNow(), W.what_caption); else toast(W.no_caption); };
  li.appendChild(b); todo.appendChild(li);
  todo.appendChild(queueStep());
  li = step(W.r5_h, (PIECE === 'reel' ? (where === 'trial' ? W.r5_trial : W.r5) : W.c4) + coverNote());
  coverPic(li); todo.appendChild(li);

  var o = S.other, box = $('other');
  box.hidden = !o.has;
  if (o.has) showOther(o);
  if (focId && $(focId) && document.activeElement !== $(focId) && !$(focId).disabled) $(focId).focus();
}
function showOther(o){
  var b;
  var doIt = $('otherDo'), url = '/words.html' + Q + OTHER;
  doIt.textContent = '';
  function go(cls){ var a = el('a', cls, fill(W.o_go)); a.href = url; a.id = 'otherGo'; return a; }
  if (o.caption) {
    $('otherHead').textContent = fill(W.o_ready_h);
    $('otherSay').textContent = OTHER === 'reel' ? fill(W.o_ready_reel, {n: o.hooks || 0}) : fill(W.o_ready_carousel);
    doIt.appendChild(go('btn main'));
  } else if (o.answered || carried) {
    $('otherHead').textContent = fill(W.o_waiting_h);
    $('otherSay').textContent = fill(W.o_waiting);
    var ln = el('div', 'line'), sp = el('span', '', fill(W.o_line)); sp.id = 'otherLine';
    b = btn('btn main', W.copy); b.id = 'otherCopy';
    b.onclick = function(){ copy(fill(W.o_line), W.what_line); };
    ln.appendChild(sp); ln.appendChild(b); doIt.appendChild(ln);
    var p = el('p', 'otherlink'); p.appendChild(go('')); doIt.appendChild(p);
  } else {
    $('otherHead').textContent = fill(W.o_make_h);
    $('otherSay').textContent = fill(W.o_make);
    b = btn('btn main', fill(W.o_yes)); b.id = 'otherYes';
    b.onclick = function(){
      b.disabled = true;
      flush().then(function(){ return post('/words-carry', {kit: KIT, piece: PIECE}); }).then(function(r){
        if (r && r.ok) { carried = true; S.other.answered = true; showNext(); toast(fill(W.carried)); return; }
        b.disabled = false;
        toast((r && r.words) || W.not_saved);
      }, function(){ b.disabled = false; toast(W.not_saved); });
    };
    doIt.appendChild(b);
  }
}

/* ---------- the strip of this piece's photos ---------- */
function showStrip(urls){
  var key = JSON.stringify(urls);
  if (key === stripKey) return;
  stripKey = key;
  var s = $('strip'); s.textContent = '';
  urls.forEach(function(u){
    var i = el('img'), tries = 0; i.alt = '';
    i.onerror = function(){   // a small copy still being made: asked for again, a few times
      i.classList.add('wait');
      if (tries++ < 20) setTimeout(function(){ i.src = u + (u.indexOf('?') >= 0 ? '&' : '?') + 'again=' + tries; }, 1500);
    };
    i.onload = function(){ i.classList.remove('wait'); };
    i.src = u; s.appendChild(i);
  });
}

/* ---------- start, and pick up answers and drafts as they arrive ---------- */
function load(){
  return ask('/words-state' + Q + PIECE).then(function(st){
    if (!st || !st.ok) return;
    var first = !loaded;                   // no look has come back yet (the very first one may have failed)
    var p = st.w, a = p.answers, aj = JSON.stringify(a);
    // the first look, or answers given in the chat; never while they are typing (within 5 s of their last key),
    // never while a save of theirs is waiting or on its way, and never over a box they have touched since
    var quiet = !saveT && !inflight && Date.now() - lastEdit > D.typing;
    if ((first && !lastEdit) || (aj !== lastServerAns && quiet)) {
      ['about', 'who_text', 'purpose_text', 'notes'].forEach(function(k){
        if (!dirty[k] && $(k).value.trim() !== (a[k] || '')) $(k).value = a[k] || ''; });
      if (!dirty.who) who = a.who || [];
      if (!dirty.purpose) purpose = a.purpose || '';
      if (!dirty.where) where = a.where || '';
      showChips();
      lastServerAns = aj; w.answers = a;
    }
    // their own caption: put in its box once, by the first look that comes back, and never over their typing
    if (first && !ownTouched) { $('own').value = p.own || ''; $('copyOwn').disabled = !$('own').value; }
    var capOk = !capT && !dirty.caption && !inflight && Date.now() - lastCapEdit > D.typing, pickOk = Date.now() - lastPickEdit > 3000;
    var cap = capOk ? p.caption : w.caption, picked = pickOk ? p.picked : w.picked;
    var changed = JSON.stringify([cap, p.hooks]) !== JSON.stringify([w.caption, w.hooks]);
    var pickChanged = JSON.stringify(picked) !== JSON.stringify(w.picked);
    w.caption = cap; w.hooks = p.hooks; w.picked = picked;
    if (first || changed || pickChanged) showDrafts();
    showStrip(st.strip || []);
    // the steps: when a draft arrived, the kit or the queue changed, or the chat said where the reel is going;
    // never while the rhythm chips are showing
    var rest = JSON.stringify([st.kit, st.queue, st.other]);
    var busy = adding || !!document.querySelector('[data-iv]');
    if (first || !busy) {
      S = st;
      if (first || changed || rest !== lastRest || where !== shownWhere) { lastRest = rest; showNext(); }
    }
    loaded = true;
  }, function(){});
}
window.wordsPage = {load: load};
load().then(function(){
  setInterval(function(){ if (!document.hidden) load(); }, D.lookEvery);
});
})();
"""
