#!/usr/bin/env python3
"""The carousel designer's records, rules and routes: a page where the photographer lays out carousel slides.

Photos sit as frames on a strip of slides, with text boxes, brand colors, saved designs and templates, and
"Save slides" puts the finished slides in the kit's Carousel folder. The page itself is design_page.py; it is
served by the page server (posting_queue.py), which hands every request for it to handle_get / handle_post
here. This file holds no page code.

    python3 design.py open "beach" [--design <id>]     get the page ready and print its address
    python3 design.py show "beach"                     the shoot's designs and the sets of slides saved from them
    python3 design.py commit "<kit>" --design <id> --set <token> [--rev N]
                                                       put a staged set of slides into the Carousel folder (the
                                                       page's Save slides runs this, as a process of its own)
    python3 design.py took "beach"                     Claude has told them about the save: clear the waiting line
                                                       (the kit name exactly as the line gives it also works when the
                                                       folder has been renamed since)
    python3 design.py tidy "beach"                     clear the waiting slides of saves that were never finished
    every command takes --kind stories for the stories designer (below); without it, the carousel's

THE STORIES DESIGNER (?kind=stories on the page, --kind stories on a command; Nicole's v19). The same page and the
same rules for Instagram stories: each box is one 9:16 story (1080 by 1920), a set holds 1 to 40, a shoot has one
stories design (made empty on the first visit, white, and the page opens on "Add stories"), "+ Add stories" adds
after the last story and never replaces, her seven grid layouts, text with a look (Plain, Box, Neon), her story
fonts, and "Save stories" puts the set in the kit's Stories folder as "<short> stories - 01.jpg", then "<short>
stories (2) - 01.jpg" (decision 17). Every difference between the two kinds is in KINDS. A carousel's records,
names and slides are exactly as they were; a story's are kept apart from them in every folder below.

Rules this file keeps:
  * Everything the page knows is on disk, saved as they work, with a counter (rev). A reload, a server that
    starts over or a new port loses nothing. Nothing that matters is in the browser's storage.
  * A page names a shoot only by its kit folder NAME, a photo only by its NUMBER on the kit's numbered list,
    a design or template only by an id this file made. No route takes a path or a file name, and no answer
    contains one. The browser only ever gets JPEG copies the Assistant made (arrange.py's /kit-photo).
  * Nothing is deleted or written over. There is no way to delete a design or a template. The version of a
    design before the last save is kept beside it. Finished slides wait in the kit's hidden folder until every
    one has arrived, and go into the Carousel folder as a whole set, under a name chosen from what is in that
    folder and written down BEFORE the first file moves. A save that was cut off is finished under the same
    name by the next try. A second save makes a new set beside the first. The plain slides, Canva's slides
    and anything else in that folder are never touched. Once a slide of a set has been put in the Carousel
    folder, what happens to it there is the photographer's business: a slide they rename, move or change is
    left as it is, and no other slide is moved because of it. A set that could not be finished part way is
    put back to wait, and a slide that came back that way is never cleared (it is set aside, see below).
    The only files ever cleared are slides that never reached the Carousel folder, from saves nobody finished.
  * "Already saved" is said only when saving now would make the very same slides: the same layout, under the
    same name, from the same edit of every photo, with the same fonts, and every file still in the folder.
  * kit.json is written only by commands (this file's commit, run as a process of its own), never by a
    server thread.
  * Every POST goes through arrange.guard (Host, Origin, Content-Type, Content-Length) and is checked field
    by field. Unknown keys are dropped. A font name must match FONT before it is kept.
  * Nothing here exits the process outside main(): a server thread must never bring the server down.

Records (<kit> is the shoot's folder in Your Content; <studio> is STUDIO_HOME, ~/.studio unless set):
  <kit>/.kit/designs/<id>.json           one design: {v, id, name, updated, t, rev, stamp, names, state, from, dropped}
  <kit>/.kit/designs/<id>.prev.json      that design as it was before its last save
  <kit>/.kit/designs/earlier/<id> <YYYY-MM-DD>.json
                                         that design as it stood at the end of that day (kept when the first
                                         change of a later day comes in; one a day at most)
  <kit>/.kit/designs/sets/<id>-<token>.json
                                         one press of Save slides: the set's name, its files and their hashes, and
                                         the layout that made it. Written "moving" before the first file moves,
                                         "done" when the set is whole, "undone" when it had to be put back. "n"
                                         numbers the kit's saves in the order they were written down. "drawn" is
                                         what the slides were drawn from (each photo's mark, fonts that fell back
                                         to Georgia); "theirs" names slides the photographer changed by hand after
                                         they were put in; "back" names slides an undone set took back to staging.
  <kit>/.kit/design-staging/<id>-<token>/slide-NN.jpg
                                         slides that have arrived and are waiting for their set
  <kit>/.kit/design-slides-older/<when> <set name>/<the slide's name>
                                         slides of a set that could not be finished, which had already been in
                                         the Carousel folder: set aside here a day later, never cleared
  <kit>/.kit/design.lock                 held for every read-change-write of a design
  <kit>/.kit/slides.lock                 kit.py's own: held while files go into the Carousel folder
  <kit>/.kit/kit.json                    "carousel_set" (the newest laid-out set) and "laid_out" (every one)
  <studio>/design-templates/<id>.json    a template: a layout with empty frames, shared by every shoot
  <studio>/brand.json                    the brand colors, shared by every shoot
  <studio>/design-fonts.json             fonts they loaded by name ("Yours")
  <studio>/arrange-waiting.json          arrange.py's list: a line for Claude after a save (piece "design"; stories: "stories")
Stories keep the same records in their own places: <kit>/.kit/story-designs/ (with sets/ and earlier/ inside it),
<kit>/.kit/story-staging/, <kit>/.kit/story-slides-older/, <kit>/.kit/stories.lock (held while files go into the
Stories folder), kit.json "stories_set" and "stories_laid_out" (kit.stories_shown reads them), and
<studio>/story-templates/ (kept apart from a carousel's). The brand colors and "Yours" are shared by both.

On a PC (the PC pass of Nov 6; every line of it unproven on a real PC until GitHub's Windows machine runs
tests/pc_design.py). Everything the two computers do differently is asked of this_computer.py, or of the helpers in
arrange.py and kit.py that ask it; nothing here does a Mac-only thing itself:
  * text out (this_computer.utf8_output), records saved over a file that may be open (arrange.write_whole ->
    this_computer.replace), a slide given its name without ever taking one (kit.place -> this_computer.rename_new:
    a Mac's hard link, a look and a rename where the drive has no links, Windows' own refusing rename), the locks
    (arrange.locked and kit._held -> this_computer.try_lock), the commit started with no window
    (this_computer.popen_detached), this computer's own page asked for with no proxy (this_computer.open_local).
  * names: a saved slide's name is made by this_computer.safe_name (none of the characters Windows refuses, no
    dot or space at the end, never CON, AUX, NUL...), the same on both computers so a drive can move between them.
  * how long a path may be: a PC opens nothing past 260 characters. A slide whose full address in the Carousel
    folder would pass that (this_computer.path_too_long), or a kit too deep in folders for the designer's own
    hidden files where long paths are off (records_path_too_long), is refused in plain words BEFORE anything is
    staged or written (name_too_long, too_deep). A Mac has no such limit and measures nothing.
  * no record holds a path: a save's record names its files by name only, so there is no slash to get wrong.

Python 3.9, standard library only.
"""
import argparse
import errno
import hashlib
import json
import math
import os
import random
import re
import socket
import struct
import subprocess
import sys
import threading
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402
import arrange  # noqa: E402
import kit as kit_mod  # noqa: E402
import posts  # noqa: E402

HOME = arrange.HOME                     # STUDIO_HOME, as every other script resolves it
TEMPLATES = HOME / "design-templates"
BRAND = HOME / "brand.json"
FONTS_FILE = HOME / "design-fonts.json"
FONT_DIR = HERE.parent.parent.parent / "shared" / "fonts"      # the font files the plugin carries

# ---------- the decisions, each in one place ----------
W, H = 1080, 1350                       # one slide, the shape Instagram shows in the feed (4:5)
SLIDES_MIN, SLIDES_MAX = 1, 20         # decision 12 (Nicole, Nov 6): one slide on its own is a single post
MAX_BLOCKS = 80                         # photos and text boxes together, in one design
MAX_TEXTS = 40
TEXT_MAX = 2000                         # letters in one text box
TEXT_TOTAL = 20000                      # letters in all of a design's text boxes together
NAME_MAX = 80                           # letters in a design's or a template's name
FRAME_MIN = 60                          # the smallest a photo frame may be, each way
TEXT_W_MIN = 80                         # the narrowest a text box may be
TEXT_H_MAX = 13500                      # a text box's height is worked out by the page from its lines
ON_STRIP = 40                           # at least this much of every block stays on the strip
XY_MAX = 100000                         # nothing sane is further from the strip than this
ZOOM = (1, 3)
SIZE = (8, 600)                         # text size, in strip pixels
LS = (-20, 200)                         # letter spacing, in strip pixels
LH = (0.5, 3)                           # line height, as a multiple of the size
BORDER = (1, 200)                       # a frame's border, in strip pixels
ALIGN = ("left", "center", "right")
WEIGHTS = (400, 700)
BRAND_MAX = 16
YOURS_MAX = 60                          # fonts kept under "Yours"
DESIGNS_MAX = 200                       # designs in one shoot
TEMPLATES_MAX = 200
DEFAULT_SLIDES = 5                      # a blank design
SEED_MOST = 8                           # one photo per slide when the shoot has no carousel order yet
DEFAULT_TEXT = "Your words here"
DEFAULT_FONT = "Playfair Display"
FALLBACK_FONT = "Georgia"               # what text is drawn in when its font can't be loaded
GOOGLE_CSS = "https://fonts.googleapis.com/css2"
OPEN_NEW = "NEW: this shoot had no design, so one was made just now, with one photo on each slide."
OPEN_THEIRS = "THEIRS: this design was already here. It is as they left it."
SET_NAME = "{base} - slide {i:02d}.jpg"         # a saved slide's file name in the Carousel folder
SET_AGAIN = "{base} ({k})"                      # the same design saved again: "<name> (2)", "<name> (3)". In brackets,
                                                # because a design's own name often ends in a number
                                                # ("Beach carousel 1"), and "Beach carousel 1 2" reads like a mistake
# Stories (decision 17: the carousel's pattern): "<short> stories - 01.jpg", then "<short> stories (2) - 01.jpg"
STORY_SET_NAME = "{base} - {i:02d}.jpg"
STORY_SET_AGAIN = "{base} ({k})"
STORY_HANDLE_FALLBACK = "yourname"      # decision 18: the name in the stories preview when their handle isn't known
STORY_SAFE = (250, 340)                 # Instagram's name and buttons at the top of a story, its reply bar at the bottom
LOOKS = ("plain", "box", "neon")        # a story's text: plain, on a box behind each line, or neon (stories only)
POST_CAP = 262144                       # bytes in a JSON save
SMALL_CAP = 4096                        # bytes in the small JSON posts (a color, a font name, a commit)
SLIDE_CAP = 12 * 1024 * 1024            # bytes in one finished slide
SLIDE_MIN = 1000
STAGING_KEEP = 86400.0                  # seconds a set that never finished arriving is kept before it is cleared
STAGING_MOST = 60                       # unfinished sets waiting in one kit
STAGING_PRESSED = 3600.0                # when that many are waiting, ones left alone for an hour are cleared too
COMMIT_CAP = 16384                      # bytes in a commit (it says which photos and fonts the slides were drawn from)
COMMIT_WAIT = 60.0                      # seconds the page's Save slides waits for the set to be placed
# A PC only (too_deep): as long as the names made here and by the page get. An id is a letter, the time and four
# of chance (13 today, 14 from the year 2059); the page's name for a press is the same length.
LONGEST_ID = "d" + "0" * 13
LONGEST_TOKEN = "s" + "0" * 13

ID = re.compile(r"[a-z][a-z0-9]{5,23}")                 # a design or template id, made here
TOKEN = re.compile(r"[a-z0-9]{8,24}")                   # the name a page gives one press (a save, a new design)
COLOR = re.compile(r"#[0-9a-fA-F]{6}")
FONT = re.compile(r"[A-Za-z0-9]+(?: [A-Za-z0-9]+)*")    # a font family's name: letters, digits, single spaces
FONT_MAX = 50
STAGED = re.compile(r"slide-(\d\d)\.jpg")

# The page is allowed to load one thing from the internet: Google's font stylesheets and font files, for
# the words on the slides. No script from anywhere, ever. The browser is told so, and keeps to it.
PAGE_CSP = ("default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; img-src 'self' blob: data:; connect-src 'self'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

# ---------- words a photographer can see (arrange.py's are used where they already say it) ----------
CANT_FIND = arrange.CANT_FIND
NOT_READY = arrange.NOT_READY
CANT_REACH = arrange.CANT_REACH
NOT_UNDERSTOOD = arrange.NOT_UNDERSTOOD
PHOTOS_CHANGED = arrange.PHOTOS_CHANGED
SAVED_WORD = "Saved"
NEWER = "This design was changed somewhere else. Here's the newest."
NO_DESIGN = "I can't find that design. Reload the page to see this shoot's designs."
TOO_MANY_DESIGNS = "This shoot already has 200 designs. Open one of them and change it instead."
ONE_STORIES = "This shoot already has its stories. Press + Add stories to add more."
TOO_MANY_BLOCKS = "A design holds up to 80 photos and text boxes. Remove one first."
TEXT_TOO_LONG = "That's more words than one text box holds. Shorten it, or add another text box."
FONT_BAD = "That doesn't look like a font's name. Use letters, numbers and spaces only."
NAME_BAD = "Give it a name, up to 80 letters."
TEMPLATE_EMPTY = "Add some photos or text first, then save it as a template."
TEMPLATE_SAVED = "Saved \"{name}\" to your templates. You'll find it under + New design, in any shoot."
TOO_MANY_TEMPLATES = "You have 200 templates, which is as many as fit."
BRAND_FULL = "You've saved 16 brand colors, which is as many as fit. Take one off first."
YOURS_FULL = "Your font list is full. The font still works in this design."
SLIDE_AGAIN = "Something went wrong while the slides were being sent. Nothing was added to your Carousel folder. Press Save slides again."
SLIDES_WAITING = "Too many unfinished saves are waiting. Tell Claude and it'll sort it out."
SAVED_SET = "Saved {n} slides in your Carousel folder, named \"{base}\". Nothing was replaced."
SAVED_ONE = "Saved 1 slide in your Carousel folder, named \"{base}\". Nothing was replaced."
ALREADY = "Already saved as \"{base}\". Change something to save a new set."
MISSING = "Not every slide arrived. Nothing was added to your Carousel folder. Press Save slides to try again."
CHANGED = "The design changed while its slides were being made. Nothing was added to your Carousel folder. Press Save slides again."
STILL = "Still saving your slides. One moment."
BUSY = "Your slides are being changed by something else right now. Try again in a moment."
TRY_AGAIN = "The Assistant is busy with this shoot right now. Try again in a moment."
NOT_FINISHED = "Couldn't finish saving your slides. Nothing was lost. Press Save slides again and it will finish."
IN_THE_WAY = "Couldn't save the slides: a file in your Carousel folder has a name one of them needs. Nothing was replaced. Press Save slides again."
DRIVE = "Couldn't save the slides: {why}. Nothing was lost. Press Save slides again once that is put right."
CANT_SAVE = "Your changes can't be saved right now: {why}. They'll be saved by themselves once that is put right."
CANT_KEEP = "That couldn't be saved: {why}."
PHOTO_NEWER = ("A photo on these slides was exported again since this page opened, so no slides were made. "
               "Nothing was added to your Carousel folder. Press Reload, then Save slides again.")
# A PC only (a Mac has no such limit and never says these). The limit is said in kit.py's own words (LONG_WORDS).
LONG_NAME = ("Couldn't save the slides: with this design's name, a slide's own name would be too long for this {pc} "
             "to open ({limit}). Nothing was added to your Carousel folder. Give the design a shorter name, then "
             "press Save slides again.")
LONG_FOLDER = ("Couldn't save the slides: this shoot's folder sits too deep in other folders for this {pc} to open "
               "a slide in it ({limit}). Nothing was added to your Carousel folder. Tell Claude and it'll sort it out.")
TOO_DEEP = ("This shoot's folder sits too deep in other folders for this {pc} to keep a design of its slides "
            "({limit}). Moving {where} nearer the top of the drive, or a shorter name for this shoot's folder, puts "
            "it right. Nothing was changed.")
WHY_WORDS = {"many": TOO_MANY_BLOCKS, "long": TEXT_TOO_LONG, "font": FONT_BAD, "name": NAME_BAD}

# ---------- the fonts ----------
# Nicole's list, in her three groups; the second item is the weights Google has for the family ("" = one
# weight only). Fraunces is added because the plugin carries it. A family the plugin carries as files is
# served by the Assistant itself (OWN_FACES), so it works with no internet and draws the same every time.
FONT_GROUPS = [
    ("Serif", [("Playfair Display", "400;700"), ("Cormorant Garamond", "400;700"), ("Libre Baskerville", "400;700"),
               ("DM Serif Display", ""), ("Bodoni Moda", "400;700"), ("Lora", "400;700"), ("EB Garamond", "400;700"),
               ("Cinzel", "400;700"), ("Italiana", ""), ("Old Standard TT", "400;700"), ("Abril Fatface", ""),
               ("Fraunces", "")]),
    ("Sans", [("Montserrat", "400;700"), ("Inter", "400;700"), ("Poppins", "400;700"), ("Raleway", "400;700"),
              ("Josefin Sans", "400;700"), ("Work Sans", "400;700"), ("DM Sans", "400;700"), ("Tenor Sans", ""),
              ("Syne", "400;700"), ("Space Grotesk", "400;700"), ("Bebas Neue", ""), ("Oswald", "400;700")]),
    ("Script", [("Great Vibes", ""), ("Allura", ""), ("Pinyon Script", ""), ("Dancing Script", "400;700"),
                ("Homemade Apple", ""), ("La Belle Aurore", ""), ("Caveat", "400;700")]),
]
# (family, the weight the page asks for, style, the file in shared/fonts without its .ttf). 700 is the
# heaviest file the plugin carries for that family (a SemiBold where there is no Bold).
OWN_FACES = [
    ("Cormorant Garamond", 400, "normal", "CormorantGaramond-Regular"),
    ("Cormorant Garamond", 400, "italic", "CormorantGaramond-Italic"),
    ("Cormorant Garamond", 700, "normal", "CormorantGaramond-SemiBold"),
    ("Cormorant Garamond", 700, "italic", "CormorantGaramond-SemiBoldItalic"),
    ("DM Sans", 400, "normal", "DMSans-Regular"),
    ("DM Sans", 700, "normal", "DMSans-SemiBold"),
    ("Fraunces", 400, "normal", "Fraunces-Regular"),
    ("Fraunces", 400, "italic", "Fraunces-Italic"),
    ("Inter", 400, "normal", "Inter-Regular"),
    ("Inter", 700, "normal", "Inter-Bold"),
    ("Montserrat", 400, "normal", "Montserrat-Regular"),
    ("Montserrat", 700, "normal", "Montserrat-SemiBold"),
]
OWN_FILES = tuple(f[3] for f in OWN_FACES)      # the only names /design-font-file answers to
# The stories designer's own fonts, first in its list: Google Fonts that feel like Instagram's story fonts (Nicole's
# list, v19), each with its Instagram style as a nickname ("Classic · Figtree"). Decision 19 was to carry Figtree in
# the plugin; no Figtree file was on this Mac or in the handoff when stories were built, so it comes from Google like
# the rest, and with no internet its words show in Georgia with the page's usual line. Adding its .ttf files to
# shared/fonts and two lines to OWN_FACES is all it takes.
STORY_FONTS = [("Figtree", "400;700", "Classic"), ("Archivo Narrow", "400;700", "Modern"), ("Yellowtail", "", "Neon"),
               ("Courier Prime", "400;700", "Typewriter"), ("Anton", "", "Strong"), ("DM Serif Display", "", "Editor"),
               ("Bebas Neue", "", "Poster"), ("Playfair Display", "400;700", "Elegant"), ("Fredoka", "400;700", "Bubble"),
               ("Caveat", "400;700", "Handwritten"), ("Lora", "400;700", "Literature")]
STORY_FONT_GROUP = "Story fonts"
# A new text box in a story: Classic, bold, size 72, line height 1.3, black on a white box (hers).
STORY_TEXT = {"font": "Figtree", "size": 72, "weight": 700, "color": "#111111", "look": "box", "boxColor": "#ffffff", "lh": 1.3}


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass
    except UnicodeEncodeError:          # an output that can't spell a name and could not be set to UTF-8: spell it out instead
        try:
            print(str(msg).encode("ascii", "backslashreplace").decode("ascii"), flush=True)
        except (OSError, ValueError):
            pass
    except OSError as e:
        # A PC only (as arrange.py's and kit.py's say): Windows reports a reader that has gone away as "invalid
        # argument" (EINVAL), not as a broken pipe. It happens here for real: the page server stops waiting for a
        # commit after a minute (COMMIT_WAIT) and the commit, still at work, then prints into a closed pipe. The
        # work goes on, as it does on a Mac. A Mac raises anything else, as before.
        if not (this_computer.WINDOWS and e.errno == errno.EINVAL):   # unproven on a real PC
            raise


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _test_stop(name):
    """For the tests only: stop dead at a named point, the way a power cut or a kill would.
    DESIGN_TEST_STOP names the point ("after-journal", "after-2" = two files placed, "after-record");
    DESIGN_TEST_STOP_ONCE (a file to make) limits it to one time."""
    if os.environ.get("DESIGN_TEST_STOP") != name:
        return
    once = os.environ.get("DESIGN_TEST_STOP_ONCE")
    if once:
        if os.path.exists(once):
            return
        Path(once).write_text(name, encoding="utf-8")
    os._exit(9)


def new_id(prefix):
    """An id made here, never by a page: a letter, the time, and four letters or digits of chance."""
    n, s = int(time.time() * 1000), ""
    while n:
        n, r = divmod(n, 36)
        s = "0123456789abcdefghijklmnopqrstuvwxyz"[r] + s
    return prefix + s + "".join(random.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(4))


# ---------- names ----------

TURNERS = set("\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u061c\ufeff")   # marks that turn the reading direction, and the byte-order mark


def _unseen(c):
    """A character nobody can see (a zero-width mark, a direction mark): Unicode's "format" kind."""
    return unicodedata.category(c) == "Cf"


def _writable(s):
    """Can this text be written to a file at all? Half of a two-part character (a lone surrogate, which only a
    made-up request can send: the page's own boxes never cut a letter in half) cannot be written as UTF-8."""
    try:
        s.encode("utf-8")
        return True
    except UnicodeEncodeError:
        return False


def clean_name(v):
    """A design's or a template's name as it is kept: one line, no control characters, 1 to 80 letters.
    Marks that turn the reading direction are dropped (they come along when a name is pasted, and can make a
    name read differently from what is stored), and so is anything unseen at either end. None when it is not
    a usable name (one that could never be written to a file among them)."""
    if not isinstance(v, str) or not _writable(v):
        return None
    s = unicodedata.normalize("NFC", v)
    s = "".join(" " if (ord(c) < 32 or ord(c) == 127) else c for c in s if c not in TURNERS)
    s = re.sub(r"\s+", " ", s).strip()
    while s and (_unseen(s[0]) or _unseen(s[-1])):
        s = (s[1:] if _unseen(s[0]) else s[:-1]).strip()
    return s if 1 <= len(s) <= NAME_MAX else None


def safe_base(name, kind="carousel"):
    """A design's name as the start of a file name that any drive, a Mac and a PC will take: no slash, colon,
    star, question mark, quote, angle bracket or bar; no dot or space at either end; not one of the names
    Windows keeps for itself; and never the words "(Canva)", which canva_kit.py takes for a Canva slide.
    No character nobody can see either: a drive like Big Kahuna leaves those out when it compares two names,
    so a name that differs from a saved set's only by one of them could never be given a file."""
    s = unicodedata.normalize("NFC", str(name))
    s = re.sub(r"\(canva\)", " ", s, flags=re.I)
    s = "".join(" " if ord(c) == 127 else c for c in s if not _unseen(c))
    # The rest is the one rule every script shares (this_computer.safe_name): the characters Windows refuses and
    # the control characters become a space, no dot or space at either end, at most 80 letters, and a word Windows
    # keeps for itself gets an underscore before any dot ("aux_.txt", "Con_"). The same on both computers.
    fallback = "Stories" if kind == "stories" else "Carousel"
    base = this_computer.safe_name(s, limit=NAME_MAX, fallback=fallback)
    if len(base) > NAME_MAX:
        # That underscore is added after the cut to 80, so "con." and 76 more letters came out 81 long, and the same
        # rule run over it again gave 80: a name that did not settle, and a save whose own record (_journal_ok) was
        # then not known as one. Cut one letter shorter, the underscore fits and the name stays what it is.
        base = this_computer.safe_name(s, limit=NAME_MAX - 1, fallback=fallback)
    return base


def kit_bg(rec):
    """The kit's slide background ('FFFFFF' in the kit record) the way a design keeps a color."""
    v = str(rec.get("slide_background") or kit_mod.PAD_WHITE).lstrip("#")
    return "#" + v.lower() if re.fullmatch(r"[0-9a-fA-F]{6}", v) else "#ffffff"


# ---------- checking a design's layout, field by field ----------

def _num(v, lo, hi, places=2):
    """A plain finite number within lo..hi, rounded; None for anything else (a word, true, NaN, too big)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    try:
        if not math.isfinite(v) or v < lo or v > hi:
            return None
        r = round(float(v), places)
    except (OverflowError, ValueError, TypeError):
        return None
    return int(r) if r == int(r) else r


def _clamped(v, lo, hi, places):
    """A plain finite number brought inside lo..hi; None if it is not a finite number at all."""
    n = _num(v, -1e9, 1e9, places)
    if n is None:
        return None
    n = max(lo, min(hi, n))
    return int(n) if n == int(n) else n


def _color(v):
    return v.lower() if isinstance(v, str) and COLOR.fullmatch(v) else None


def font_ok(v):
    return isinstance(v, str) and len(v) <= FONT_MAX and bool(FONT.fullmatch(v))


def _on_strip(x, y, w, h, slides, k=None):
    sw, sh = (k["w"], k["h"]) if k else (W, H)
    return x + w >= ON_STRIP and x <= slides * sw - ON_STRIP and y + h >= ON_STRIP and y <= sh - ON_STRIP


def _photo_block(b, slides, on_sheet, template, k=None):
    k = k or KINDS[CAROUSEL]
    out = {"id": b["id"]}
    n = b.get("n")
    if n is not None:
        if template or type(n) is not int or n < 1 or n > 999999 or (on_sheet is not None and n not in on_sheet):
            return None, "photo"
    out["n"] = n
    x, y = _num(b.get("x"), -XY_MAX, XY_MAX), _num(b.get("y"), -XY_MAX, XY_MAX)
    w, h = _num(b.get("w"), FRAME_MIN, slides * k["w"]), _num(b.get("h"), FRAME_MIN, k["h"])
    if None in (x, y, w, h) or not _on_strip(x, y, w, h, slides, k):
        return None, "frame"
    out.update(x=x, y=y, w=w, h=h)
    ox, oy = _clamped(b.get("ox", 0.5), 0, 1, 4), _clamped(b.get("oy", 0.5), 0, 1, 4)
    zoom = _clamped(b.get("zoom", 1), ZOOM[0], ZOOM[1], 3)
    if None in (ox, oy, zoom):
        return None, "crop"
    out.update(ox=ox, oy=oy, zoom=zoom)
    if b.get("border") is not None:
        bd = b["border"]
        if not isinstance(bd, dict):
            return None, "border"
        bw, bc = _num(bd.get("w"), BORDER[0], BORDER[1]), _color(bd.get("color"))
        if bw is None or bc is None:
            return None, "border"
        out["border"] = {"w": bw, "color": bc}
    if b.get("slot") is not None:
        if type(b["slot"]) is not int or not 1 <= b["slot"] <= 999:
            return None, "slot"
        out["slot"] = b["slot"]
    return out, None


def _text_block(b, slides, k=None):
    k = k or KINDS[CAROUSEL]
    text = b.get("text")
    if not isinstance(text, str):
        return None, "text"
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if any((ord(c) < 32 and c != "\n") or ord(c) == 127 for c in text) or not _writable(text):
        return None, "text"
    if len(text) > TEXT_MAX:
        return None, "long"
    if not font_ok(b.get("font")):
        return None, "font"
    size = _num(b.get("size"), SIZE[0], SIZE[1])
    ls, lh = _num(b.get("ls", 0), LS[0], LS[1]), _num(b.get("lh", 1.15), LH[0], LH[1], 3)
    color = _color(b.get("color"))
    weight, italic, upper, al = b.get("weight", 400), b.get("italic", False), b.get("upper", False), b.get("al", "center")
    if (None in (size, ls, lh, color) or type(weight) is not int or weight not in WEIGHTS or type(italic) is not bool
            or type(upper) is not bool or al not in ALIGN or not isinstance(al, str)):
        return None, "style"
    x, y = _num(b.get("x"), -XY_MAX, XY_MAX), _num(b.get("y"), -XY_MAX, XY_MAX)
    w, h = _num(b.get("w"), TEXT_W_MIN, slides * k["w"]), _num(b.get("h"), 1, TEXT_H_MAX)
    if None in (x, y, w, h) or not _on_strip(x, y, w, h, slides, k):
        return None, "frame"
    out = {"id": b["id"], "type": "text", "text": text, "font": b["font"], "size": size, "weight": weight,
           "italic": italic, "upper": upper, "al": al, "ls": ls, "lh": lh, "color": color,
           "x": x, "y": y, "w": w, "h": h}
    if k["looks"]:
        # A story's text may have a look (Plain, Box, Neon) and a box color. Only a story keeps them: on a
        # carousel these keys are dropped like any other unknown key, so its records and slides stay as they were.
        look, box = b.get("look"), b.get("boxColor")
        if look is not None:
            if not isinstance(look, str) or look not in LOOKS:
                return None, "style"
            out["look"] = look
        if box is not None:
            if _color(box) is None:
                return None, "style"
            out["boxColor"] = _color(box)
    return out, None


def validate_state(state, on_sheet=None, template=False, kind="carousel"):
    """A design's layout, checked field by field. Returns (the clean layout, None) or (None, a short reason).
    The clean layout holds only the keys this file knows; every number is finite, in range and rounded.
    on_sheet, when given, is the set of photo numbers on the kit's list: a photo must be one of them.
    template: every frame must be empty (a template holds no photo). kind: "carousel" (4:5 slides, 1 to 20) or
    "stories" (9:16 stories, 1 to 40; text may carry a look); anything else is refused."""
    k = KINDS.get(kind) if isinstance(kind, str) else None
    if k is None or not isinstance(state, dict):
        return None, "shape"
    slides = state.get("slides")
    if type(slides) is not int or not k["slides"][0] <= slides <= k["slides"][1]:
        return None, "slides"
    bg = _color(state.get("bg"))
    if bg is None:
        return None, "bg"
    blocks = state.get("blocks")
    if not isinstance(blocks, list):
        return None, "shape"
    if len(blocks) > MAX_BLOCKS:
        return None, "many"
    out, seen, texts, letters = [], set(), 0, 0
    for b in blocks:
        if not isinstance(b, dict):
            return None, "block"
        if type(b.get("id")) is not int or not 1 <= b["id"] <= 1000000 or b["id"] in seen:
            return None, "id"
        seen.add(b["id"])
        kind = b.get("type")
        if kind == "text":
            clean, why = _text_block(b, slides, k)
            if clean is not None:
                texts += 1
                letters += len(clean["text"])
                if texts > MAX_TEXTS:
                    return None, "many"
                if letters > TEXT_TOTAL:
                    return None, "long"
        elif kind is None or kind == "photo":
            clean, why = _photo_block(b, slides, on_sheet, template, k)
        else:
            return None, "block"
        if clean is None:
            return None, why
        out.append(clean)
    return {"slides": slides, "bg": bg, "blocks": out}, None


def to_template(state):
    """A layout with its photos taken out, for use with any shoot: every frame is empty and back to the
    middle of its crop, "slot" numbers the frames in reading order (left to right, then top to bottom),
    text boxes are kept as they are, the order (which is the stacking) is kept, ids are 1 to N."""
    frames = [b for b in state["blocks"] if b.get("type") != "text"]
    slot = {b["id"]: i for i, b in enumerate(sorted(frames, key=lambda b: (b["x"], b["y"])), 1)}
    blocks = []
    for i, b in enumerate(state["blocks"], 1):
        c = dict(b)
        if b.get("type") != "text":
            c.update(n=None, ox=0.5, oy=0.5, zoom=1, slot=slot[b["id"]])
        c["id"] = i
        blocks.append(c)
    return {"slides": state["slides"], "bg": state["bg"], "blocks": blocks}


# ---------- the two kinds of design: a carousel's slides, and stories ----------
# The stories designer (?kind=stories, Nicole's v19) is the same page and the same rules in a second shape. Every
# difference between the two is here, in one place; a function that cares takes kind ("carousel" or "stories").
CAROUSEL, STORIES = "carousel", "stories"
KINDS = {
    CAROUSEL: {"kind": CAROUSEL, "w": W, "h": H, "slides": (SLIDES_MIN, SLIDES_MAX), "folder": "Carousel",
               "designs": "designs", "staging": "design-staging", "older": "design-slides-older",
               "templates": TEMPLATES, "templates_lock": "design-templates.lock", "slides_lock": "slides.lock",
               "set_name": SET_NAME, "set_again": SET_AGAIN, "fallback": "Carousel", "word": "carousel",
               "piece": "design", "rec_set": "carousel_set", "rec_all": "laid_out", "one_design": False,
               "safe": None, "looks": False, "blank_slides": DEFAULT_SLIDES},
    STORIES: {"kind": STORIES, "w": 1080, "h": 1920, "slides": (1, 40), "folder": "Stories",
              "designs": "story-designs", "staging": "story-staging", "older": "story-slides-older",
              "templates": HOME / "story-templates", "templates_lock": "story-templates.lock", "slides_lock": "stories.lock",
              "set_name": STORY_SET_NAME, "set_again": STORY_SET_AGAIN, "fallback": "Stories", "word": "stories",
              "piece": "stories", "rec_set": "stories_set", "rec_all": "stories_laid_out", "one_design": True,
              "safe": STORY_SAFE, "looks": True, "blank_slides": 1},
}


def K(kind):
    """A kind's settings. Anything that is not a kind's name is the carousel (every caller has checked it first)."""
    return KINDS.get(kind) if isinstance(kind, str) and kind in KINDS else KINDS[CAROUSEL]


def kind_ok(v):
    """The kind a page or a command named: "" or None is the carousel; an unknown word is None (refused)."""
    if v in (None, ""):
        return CAROUSEL
    return v if isinstance(v, str) and v in KINDS else None


def story_words(s):
    """A carousel's line in a story's words (decision 20: "story" for her "slide", and the Stories folder)."""
    s = s.replace("+ New design", "+ Add stories").replace("Carousel folder", "Stories folder")
    s = re.sub(r"\bslides\b", "stories", s)
    s = re.sub(r"\bSlides\b", "Stories", s)
    s = re.sub(r"\bslide\b", "story", s)
    s = re.sub(r"\bSlide\b", "Story", s)
    return s


def KW(kind, s):
    """A line a photographer sees, in the words of the kind they are working on."""
    return story_words(s) if kind == STORIES else s


def _starters():
    """The eleven starter templates from Nicole's designer, as templates: frames in the order they are
    stacked and filled, no photo in any of them."""
    m, g = 70, 24

    def F(x, y, w, h):
        return {"x": x, "y": y, "w": w, "h": h}

    def T(x, y, w, **extra):
        t = {"type": "text", "text": DEFAULT_TEXT, "font": DEFAULT_FONT, "size": 96, "weight": 400, "italic": False,
             "upper": False, "al": "center", "ls": 0, "lh": 1.15, "color": "#2a2622", "x": x, "y": y, "w": w, "h": 110}
        t.update(extra)
        return t

    half_h, half_w = H / 2 - 1.5 * m, W / 2 - g / 2
    gw, gh = (W - 3 * g) / 2, (H - 3 * g) / 2
    raw = [
        ("st-story", "Story mix", 7, "#f4efe6",
         [F(0, 0, W, H), F(W, 0, 2 * W, H), F(3 * W + m, m, W - 2 * m, half_h), F(3 * W + m, H / 2 + m / 2, W - 2 * m, half_h),
          F(4 * W + 90, 120, 600, 900), F(4 * W + 750, 560, 660, 660), F(5 * W + 470, 170, 520, 780), F(6 * W, 0, W, H)], []),
        ("st-pano", "Panorama opener", 5, "#ffffff", [F(0, 0, W, H), F(W, 0, 2 * W, H), F(3 * W, 0, W, H), F(4 * W, 0, W, H)], []),
        ("st-stack", "Stacked horizontals", 4, "#ffffff",
         [F(0, 0, W, H), F(W + m, m, W - 2 * m, half_h), F(W + m, H / 2 + m / 2, W - 2 * m, half_h),
          F(2 * W + m, m, W - 2 * m, half_h), F(2 * W + m, H / 2 + m / 2, W - 2 * m, half_h), F(3 * W, 0, W, H)], []),
        ("st-peek", "Seam peek", 5, "#e9e1d6",
         [F(0, 0, W, H), F(W + 90, 200, 640, 960), F(2 * W - 300, 520, 600, 600), F(2 * W + 420, 150, 560, 840),
          F(3 * W, 0, W, H), F(4 * W, 0, W, H)], []),
        ("st-grid", "Four-photo grid", 3, "#ffffff",
         [F(0, 0, W, H), F(W + g, g, gw, gh), F(W + 2 * g + gw, g, gw, gh), F(W + g, 2 * g + gh, gw, gh),
          F(W + 2 * g + gw, 2 * g + gh, gw, gh), F(2 * W, 0, W, H)], []),
        ("st-title", "Title slide", 4, "#f4efe6", [F(140, 760, 800, 470), F(W, 0, W, H), F(2 * W, 0, W, H), F(3 * W, 0, W, H)],
         [T(90, 260, 900, text="Your title", size=150),
          T(140, 470, 800, text="a line of your own", font="Montserrat", size=34, upper=True, ls=8)]),
        ("st-film", "Film strip", 3, "#111111", [F(40, 275, 1000, 800), F(W + 40, 275, 1000, 800), F(2 * W + 40, 275, 1000, 800)], []),
        ("st-border", "Editorial borders", 5, "#ffffff", [F(k * W + 90, 110, 900, 1130) for k in range(5)], []),
        ("st-pairs", "Side by side", 4, "#ffffff",
         [F(0, 0, W, H), F(W, 0, half_w, H), F(W + W / 2 + g / 2, 0, half_w, H), F(2 * W, 0, half_w, H),
          F(2 * W + W / 2 + g / 2, 0, half_w, H), F(3 * W, 0, W, H)], []),
        ("st-bigsmall", "Big and small", 4, "#e9e1d6",
         [F(0, 0, W, H), F(W, 0, 640, H), F(W + 700, 420, 320, 440), F(2 * W + 60, 420, 320, 440),
          F(2 * W + 440, 0, 640, H), F(3 * W, 0, W, H)], []),
        ("st-wide3", "One wide across three", 3, "#ffffff", [F(0, 0, 3 * W, H)], []),
    ]
    out = []
    for sid, name, slides, bg, frames, texts in raw:
        blocks = []
        for i, f in enumerate(frames, 1):
            blocks.append(dict(f, id=len(blocks) + 1, n=None, ox=0.5, oy=0.5, zoom=1, slot=i))
        for t in texts:
            blocks.append(dict(t, id=len(blocks) + 1))
        clean, _ = validate_state({"slides": slides, "bg": bg, "blocks": blocks}, template=True)
        if clean is not None:
            out.append({"id": sid, "name": name, "template": clean})
    return out


STARTERS = _starters()


def _story_starters():
    """The stories designer's layouts (hers, v19): grids that cover the whole story, edge to edge, 12 px apart.
    Each one is one story; "+ Add stories" puts it after the last one."""
    w, h, g = KINDS[STORIES]["w"], KINDS[STORIES]["h"], 12
    out = []
    for sid, name, cols, rows in (("sg-1", "One photo", 1, 1), ("sg-2", "Two up", 1, 2), ("sg-3", "Three strips", 1, 3),
                                  ("sg-4", "Four", 2, 2), ("sg-6", "Six", 2, 3), ("sg-9", "Nine", 3, 3), ("sg-12", "Twelve", 3, 4)):
        cw, ch = (w - (cols - 1) * g) / cols, (h - (rows - 1) * g) / rows
        blocks = []
        for r in range(rows):
            for c in range(cols):
                blocks.append({"id": len(blocks) + 1, "n": None, "x": c * (cw + g), "y": r * (ch + g), "w": cw, "h": ch,
                               "ox": 0.5, "oy": 0.5, "zoom": 1, "slot": len(blocks) + 1})
        clean, _ = validate_state({"slides": 1, "bg": "#ffffff", "blocks": blocks}, template=True, kind=STORIES)
        if clean is not None:
            out.append({"id": sid, "name": name, "template": clean})
    return out


STORY_STARTERS = _story_starters()
KINDS[CAROUSEL]["starters"] = STARTERS
KINDS[STORIES]["starters"] = STORY_STARTERS


# ---------- where a kit's designs are ----------

def designs_dir(kit, kind=CAROUSEL):
    return kit / ".kit" / K(kind)["designs"]


def design_path(kit, did, kind=CAROUSEL):
    return designs_dir(kit, kind) / f"{did}.json"


def prev_path(kit, did, kind=CAROUSEL):
    return designs_dir(kit, kind) / f"{did}.prev.json"


def sets_dir(kit, kind=CAROUSEL):
    return designs_dir(kit, kind) / "sets"


def staging_dir(kit, kind=CAROUSEL):
    return kit / ".kit" / K(kind)["staging"]


def design_lock(kit):
    return kit / ".kit" / "design.lock"


# ---------- a PC only: how long a path may be ----------

def _scratch_of(path):
    """A record's scratch name, as long as arrange.write_whole's gets on a PC (a process's number of up to seven
    digits, a thread's of up to ten)."""
    return path.with_name(f".{path.name}.{'0' * 7}.{'0' * 10}.tmp")


def too_deep(kit, kind=CAROUSEL):
    """A PC with long paths off (Windows' own setting): plain words when this kit sits too deep in folders for the
    designer's own hidden files, else None. The longest of them are a slide waiting under its scratch name, a
    save's record and a day's earlier copy of a design while each is being written. Asked before a design is made
    or changed and before a slide is staged, so nothing is ever left half written. A Mac: None, nothing measured."""
    if not this_computer.WINDOWS:
        return None
    waiting = f"{LONGEST_ID}-{LONGEST_TOKEN}"          # unproven on a real PC
    own = [staging_dir(kit, kind) / waiting / f".part-{'0' * 7}-{'0' * 10}-slide-00.jpg",
           _scratch_of(sets_dir(kit, kind) / f"{waiting}.json"),
           _scratch_of(designs_dir(kit, kind) / "earlier" / f"{LONGEST_ID} 0000-00-00.json")]
    if not any(this_computer.records_path_too_long(f) for f in own):
        return None
    try:
        h = posts.home()
        where = f"your \"{h.name}\" folder" if h else "the folder your posts are kept in"
    except (Exception, SystemExit):  # noqa: BLE001
        where = "the folder your posts are kept in"
    return KW(kind, TOO_DEEP.format(pc=this_computer.COMPUTER, limit=kit_mod.LONG_WORDS, where=where))


def name_too_long(kit, name, base=None, kind=CAROUSEL):
    """A PC only: plain words when a slide saved from a design of this name could not be opened in File Explorer
    (its full address in the Carousel folder would pass 260 characters, long paths on or not), else None. base is
    the set's name when it has been chosen already; otherwise it is worked out as a save would (free_base). When
    even the shortest name would not fit, the words say it is the folder, not the name. A Mac: None."""
    if not this_computer.WINDOWS:
        return None
    k = K(kind)
    car = kit / k["folder"]                             # unproven on a real PC
    base = base if base is not None else free_base(kit, name, kind)
    if not this_computer.path_too_long(car / k["set_name"].format(base=base, i=1)):
        return None
    shortest = this_computer.path_too_long(car / k["set_name"].format(base="C", i=1))
    return KW(kind, (LONG_FOLDER if shortest else LONG_NAME).format(pc=this_computer.COMPUTER, limit=kit_mod.LONG_WORDS))


def cant_save(kit, name, base=None, kind=CAROUSEL):
    """(why, plain words) when a PC could not take this design's slides at all ("deep": the kit's own hidden
    files; "long": a slide's name in the Carousel folder), else None. A Mac: always None."""
    if not this_computer.WINDOWS:
        return None
    words = too_deep(kit, kind)
    if words:
        return "deep", words
    words = name_too_long(kit, name, base, kind)
    return ("long", words) if words else None


def _read_json(path):
    """A record as a dict, or None when it is not there or is not one. A PC only (unproven on a real PC): a record
    that is being saved over at this very instant (this_computer.replace, in another thread or by the commit) can
    refuse to be opened for a moment; it is asked for again a few times, a tenth of a second in all, before it
    counts as not there. A Mac reads once, as before."""
    tries = 5 if this_computer.WINDOWS else 1
    for i in range(tries):
        try:
            d = json.loads(Path(path).read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else None
        except PermissionError:
            if i == tries - 1:
                return None
            time.sleep(0.01 * (i + 1))
        except (OSError, ValueError, RecursionError):
            return None
    return None


def load_design(kit, did, kind=CAROUSEL):
    """One design, or None when it is not there or can't be trusted (its layout is checked on the way in,
    so nothing a hand or another program wrote into the file reaches a page unchecked)."""
    if not isinstance(did, str) or not ID.fullmatch(did):
        return None
    d = _read_json(design_path(kit, did, kind))
    if not d or d.get("id") != did or type(d.get("rev")) is not int or d["rev"] < 0:
        return None
    state, _ = validate_state(d.get("state"), kind=kind)
    name = clean_name(d.get("name"))
    if state is None or name is None:
        return None
    d["state"], d["name"] = state, name
    return d


def list_designs(kit, kind=CAROUSEL):
    """Every design of this shoot, newest first."""
    out = []
    for f in sorted(kit_mod._listing(designs_dir(kit, kind))):
        if f.endswith(".json") and ID.fullmatch(f[:-5]):
            d = load_design(kit, f[:-5], kind)
            if d:
                out.append(d)
    out.sort(key=lambda d: (float(d.get("t") or 0), d["id"]), reverse=True)
    return out


def count_designs(kit, kind=CAROUSEL):
    return sum(1 for f in kit_mod._listing(designs_dir(kit, kind)) if f.endswith(".json") and ID.fullmatch(f[:-5]))


def _names_for(state, rows):
    """File names for the photos a layout uses, so a re-made numbered list can find the same photos again.
    Kept in the design's record; never sent to a page."""
    name_of = {x["n"]: arrange.photo_name(x) for x in rows}
    used = sorted({b["n"] for b in state["blocks"] if b.get("type") != "text" and b.get("n") is not None})
    return {str(n): name_of[n] for n in used if n in name_of}


def _store(kit, d, old=None, kind=CAROUSEL):
    """Write a design whole (a temp file, then a rename). The version before goes beside it first, and the
    first change of a day also keeps that version under the day's date. With the design lock held."""
    if old is not None:
        arrange.write_whole(prev_path(kit, d["id"], kind), old)
        day = datetime.now().strftime("%Y-%m-%d")
        if str(old.get("updated") or "")[:10] != day:
            # the day goes into a file's name, and "updated" is read from a file a hand could have changed: only
            # its digits and dashes are used (a slash there would make folders, a colon stops a PC)
            was = re.sub(r"[^0-9-]", "", str(old.get("updated") or "")[:10]) or "undated"
            keep = designs_dir(kit, kind) / "earlier" / f"{d['id']} {was}.json"
            if not keep.exists():
                arrange.write_whole(keep, old)
    d["v"] = 1
    d["updated"], d["t"] = now_iso(), round(time.time(), 3)
    arrange.write_whole(design_path(kit, d["id"], kind), d)
    return d


def _sync(kit, d, rows, stamp, kind=CAROUSEL):
    """With the design lock held: bring a design in line with the kit's numbered list. When the list has
    been re-made since the design was saved, every photo is found again by its file name; a photo that is
    no longer in the shoot leaves an empty frame, and the design's "dropped" says how many."""
    if d.get("stamp") == stamp:
        return d
    if not d.get("stamp"):
        d["stamp"] = stamp
        return d
    old = json.loads(json.dumps(d))
    n_of = {}
    for x in rows:
        n_of.setdefault(arrange.photo_name(x), x["n"])
    was = d.get("names") if isinstance(d.get("names"), dict) else {}
    dropped = 0
    for b in d["state"]["blocks"]:
        if b.get("type") == "text" or b.get("n") is None:
            continue
        nm = was.get(str(b["n"]))
        new_n = n_of.get(nm) if nm else None
        if new_n is None:
            b.update(n=None, ox=0.5, oy=0.5, zoom=1)
            dropped += 1
        else:
            b["n"] = new_n
    d["stamp"], d["names"] = stamp, _names_for(d["state"], rows)
    d["rev"] = int(d["rev"]) + 1
    d["dropped"] = dropped
    d.pop("from", None)                 # no open page has seen this layout
    return _store(kit, d, old, kind)


def seed_state(rec, nums, rows):
    """One photo per slide, filling it, in the carousel's order (or the first few photos when the shoot has
    no carousel order yet), on the kit's slide background."""
    on_sheet = {x["n"] for x in rows}
    nums = [n for n in nums if n in on_sheet][:SLIDES_MAX]
    if not nums:
        nums = [x["n"] for x in rows[:SEED_MOST]]
    blocks = [{"id": i + 1, "n": n, "x": i * W, "y": 0, "w": W, "h": H, "ox": 0.5, "oy": 0.5, "zoom": 1, "slot": i + 1}
              for i, n in enumerate(nums)]
    return {"slides": max(SLIDES_MIN, min(SLIDES_MAX, len(nums))), "bg": kit_bg(rec), "blocks": blocks}


def next_name(shoot_name, designs, stem=None, kind=CAROUSEL):
    """"<Shoot name> carousel 1", then 2, 3: the first not taken. With stem ("<a design's name> copy"), that
    name, then "<stem> 2". Stories (one design a shoot): "<Shoot name> stories", then "<Shoot name> stories 2"."""
    taken = {kit_mod._fold(d["name"]) for d in designs}
    if stem is not None:
        stem = stem[:NAME_MAX - 4].rstrip()
        k, name = 1, stem
        while kit_mod._fold(name) in taken:
            k += 1
            name = f"{stem} {k}"
        return name
    word = K(kind)["word"]
    room = NAME_MAX - len(f" {word} 999")
    base = clean_name(str(shoot_name)[:NAME_MAX]) or "My"
    if len(base) > room:
        # a long shoot name is cut at the end of a word, not in the middle of one (the design's name becomes
        # the slides' file name)
        cut = base[:room + 1].rsplit(" ", 1)[0] if " " in base[:room + 1] else base[:room]
        base = (cut if len(cut) >= room // 2 else base[:room]).rstrip(" ,;:-") or base[:room].rstrip()
    if kind == STORIES:
        name, k = f"{base} {word}", 1
        while kit_mod._fold(name) in taken:
            k += 1
            name = f"{base} {word} {k}"
        return name
    k = 1
    while kit_mod._fold(f"{base} {word} {k}") in taken:
        k += 1
    return f"{base} {word} {k}"


def carousel_order(kit):
    """The carousel's order as it is now (the picker's, which follows the kit's own pick). [] if none."""
    _, p = arrange.sync(kit, "carousel")
    return list(p["now"]["nums"]) if p else []


def blank_story():
    """A shoot's stories before anything is added: one empty white story (hers: white by default)."""
    return {"slides": 1, "bg": "#ffffff", "blocks": []}


def new_design(kit, state=None, name=None, token=None, copy=None, kind=CAROUSEL):
    """Make a NEW design; it never takes the place of another. Returns (status, answer).
      state  a layout to start from (checked here); left out, it is one photo per slide (stories: one empty story)
      copy   the id of a design of this shoot to make a copy of, as it is stored
      token  the name the page gave this press: the same token again gives the same design back, so a press
             whose answer was lost does not leave two
    Stories are one design a shoot (Nicole): once a shoot has its stories, no second one is made."""
    rows, stamp = arrange.sheet_rows(kit), arrange.sheet_stamp(kit)
    if not rows or not stamp:
        return 404, {"ok": False, "words": NOT_READY}
    deep = too_deep(kit, kind)              # a PC only: nothing is written into a kit too deep for it
    if deep:
        return 409, {"ok": False, "why": "deep", "words": deep}
    with arrange.locked(design_lock(kit)):
        designs = list_designs(kit, kind)
        if token is not None:
            for d in designs:
                if d.get("made_by") == token:
                    return 200, {"ok": True, "design": _design_for_page(kit, d, kind), "designs": _design_list(kit, designs, d["id"], kind)}
        if K(kind)["one_design"] and (designs or count_designs(kit, kind)):
            return 409, {"ok": False, "why": "one", "words": ONE_STORIES}
        if len(designs) >= DESIGNS_MAX or count_designs(kit, kind) >= DESIGNS_MAX:
            return 409, {"ok": False, "why": "full", "words": TOO_MANY_DESIGNS}
        rec = kit_mod.load_rec(kit)
        shoot = rec.get("name") or kit.name
        stem = None
        if copy is not None:
            src = load_design(kit, copy, kind)
            if src is None:
                return 404, {"ok": False, "why": "design", "words": NO_DESIGN}
            src = _sync(kit, src, rows, stamp, kind)
            state, stem = src["state"], f"{src['name']} copy"
        elif state is None:
            state = blank_story() if kind == STORIES else seed_state(rec, carousel_order(kit), rows)
        clean, why = validate_state(state, {x["n"] for x in rows}, kind=kind)
        if clean is None:
            return 400, {"ok": False, "why": why, "words": WHY_WORDS.get(why, NOT_UNDERSTOOD)}
        if name is not None:
            name = clean_name(name)
            if name is None:
                return 400, {"ok": False, "why": "name", "words": NAME_BAD}
        else:
            name = next_name(shoot, designs, stem, kind)
        did = new_id("d")
        while design_path(kit, did, kind).exists():
            did = new_id("d")
        d = {"id": did, "name": name, "rev": 0, "stamp": stamp, "names": _names_for(clean, rows), "state": clean,
             "made": now_iso(), "made_by": token or "assistant"}
        _store(kit, d, kind=kind)
        designs = [d] + designs
        return 200, {"ok": True, "design": _design_for_page(kit, d, kind), "designs": _design_list(kit, designs, did, kind)}


def ensure_design(kit, kind=CAROUSEL):
    """The first visit to a shoot with no design makes one: one photo per slide from the carousel's order
    (stories: one empty white story, and the page opens on Add stories). Returns the newest design, or None
    when the shoot is not ready."""
    with arrange.locked(design_lock(kit)):
        designs = list_designs(kit, kind)
        if designs:
            return designs[0]
        code, out = new_design(kit, kind=kind)
        return load_design(kit, out["design"]["id"], kind) if code == 200 else None


def save_from_page(body):
    """One save from the designer page: the layout and the name of one design. Returns (status, answer).
    The counter is this file's alone: an accepted change makes it one higher. A page sends "base" (the
    counter it was last told) and "page" (the name it gave itself when it loaded). A change is taken only
    from a page that has seen the stored design: base is the stored counter, or the stored design is that
    same page's own last save from that same base (its answer never arrived). Anything else is told there
    is something newer, and given it. Sending exactly what is stored is always fine and writes nothing."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return 404, {"ok": False, "words": CANT_FIND}
    kind = kind_ok(body.get("kind"))
    if kind is None:
        return 400, {"ok": False, "why": "kind", "words": NOT_UNDERSTOOD}
    did, page, base = body.get("design"), body.get("page"), body.get("base")
    if not isinstance(did, str) or not ID.fullmatch(did):
        return 400, {"ok": False, "why": "design", "words": NOT_UNDERSTOOD}
    if not isinstance(page, str) or not arrange.PAGE_ID.fullmatch(page) or type(base) is not int or base < 0:
        return 400, {"ok": False, "why": "page", "words": NOT_UNDERSTOOD}
    rows, stamp = arrange.sheet_rows(kit), arrange.sheet_stamp(kit)
    if not rows or not stamp:
        return 404, {"ok": False, "words": NOT_READY}
    deep = too_deep(kit, kind)              # a PC only
    if deep:
        return 409, {"ok": False, "why": "deep", "words": deep}
    with arrange.locked(design_lock(kit)):
        d = load_design(kit, did, kind)
        if d is None:
            return 404, {"ok": False, "why": "design", "words": NO_DESIGN}
        d = _sync(kit, d, rows, stamp, kind)
        if body.get("stamp") != stamp:
            return 409, {"ok": False, "why": "photos", "words": PHOTOS_CHANGED, "design": _design_for_page(kit, d, kind)}
        name = d["name"]
        if "name" in body:
            name = clean_name(body.get("name"))
            if name is None:
                return 400, {"ok": False, "why": "name", "words": NAME_BAD}
        state, why = validate_state(body.get("state"), {x["n"] for x in rows}, kind=kind)
        if state is None:
            return 400, {"ok": False, "why": why, "words": WHY_WORDS.get(why, NOT_UNDERSTOOD)}
        same = state == d["state"] and name == d["name"]
        src = d.get("from") if isinstance(d.get("from"), dict) else {}
        own = src.get("page") == page and src.get("base") == base
        if not same and base != d["rev"] and not own:
            return 409, {"ok": False, "why": "newer", "words": NEWER, "design": _design_for_page(kit, d, kind)}
        if not same:
            old = json.loads(json.dumps(d))
            d.update(name=name, state=state, rev=d["rev"] + 1, stamp=stamp, names=_names_for(state, rows))
            d["from"] = {"page": page, "base": base}
            d.pop("dropped", None)
            _store(kit, d, old, kind)
        info = set_info(kit, d, kind)
        return 200, {"ok": True, "words": SAVED_WORD, "rev": d["rev"], "updated": d.get("updated"), "t": d.get("t"),
                     "set": info, "unfinished": _unfinished(kit, did, kind), "marks": photo_marks(kit, d["state"], rows)}


# ---------- templates, brand colors, fonts: shared by every shoot ----------

def _load_template(tid, kind=CAROUSEL):
    d = _read_json(K(kind)["templates"] / f"{tid}.json")
    if not d or d.get("id") != tid:
        return None
    tpl, _ = validate_state(d.get("template"), template=True, kind=kind)
    name = clean_name(d.get("name"))
    if tpl is None or name is None:
        return None
    return {"id": tid, "name": name, "from": clean_name(d.get("from")) or "", "made": str(d.get("made") or "")[:19],
            "made_by": d.get("made_by"), "template": tpl}


def list_templates(kind=CAROUSEL):
    """Their own templates, newest first. A story's templates are kept apart from a carousel's (hers)."""
    out = []
    for f in sorted(kit_mod._listing(K(kind)["templates"])):
        if f.endswith(".json") and ID.fullmatch(f[:-5]):
            t = _load_template(f[:-5], kind)
            if t:
                out.append(t)
    out.sort(key=lambda t: (t["made"], t["id"]), reverse=True)
    return out


def _templates_for_page(ts):
    return [{k: t[k] for k in ("id", "name", "from", "made", "template")} for t in ts]


def save_template(name, state, from_name="", token=None, kind=CAROUSEL):
    """"Save as template": the layout with its photos taken out, kept for every shoot. Returns (status, answer)."""
    name = clean_name(name)
    if name is None:
        return 400, {"ok": False, "why": "name", "words": NAME_BAD}
    clean, why = validate_state(state, kind=kind)
    if clean is None:
        return 400, {"ok": False, "why": why, "words": WHY_WORDS.get(why, NOT_UNDERSTOOD)}
    if not clean["blocks"]:
        return 400, {"ok": False, "why": "empty", "words": TEMPLATE_EMPTY}
    folder = K(kind)["templates"]
    with arrange.locked(HOME / K(kind)["templates_lock"]):
        ts = list_templates(kind)
        if token is not None:
            for t in ts:
                if t.get("made_by") == token:
                    return 200, {"ok": True, "words": KW(kind, TEMPLATE_SAVED.format(name=t["name"])), "template": _templates_for_page([t])[0],
                                 "templates": _templates_for_page(ts)}
        if len(ts) >= TEMPLATES_MAX:
            return 409, {"ok": False, "why": "full", "words": TOO_MANY_TEMPLATES}
        tid = new_id("t")
        while (folder / f"{tid}.json").exists():
            tid = new_id("t")
        t = {"v": 1, "id": tid, "name": name, "from": clean_name(from_name) or "", "made": now_iso(),
             "made_by": token or "assistant", "template": to_template(clean)}
        arrange.write_whole(folder / f"{tid}.json", t)
        ts = list_templates(kind)
        return 200, {"ok": True, "words": KW(kind, TEMPLATE_SAVED.format(name=name)), "template": _templates_for_page([_load_template(tid, kind)])[0],
                     "templates": _templates_for_page(ts)}


def load_brand():
    """The brand colors, in the order they were saved."""
    d = _read_json(BRAND) or {}
    out = []
    for c in d.get("colors") if isinstance(d.get("colors"), list) else []:
        c = _color(c)
        if c and c not in out:
            out.append(c)
    return out[:BRAND_MAX]


def change_brand(add=None, remove=None):
    """Save one brand color, or take one off the list (it is kept in the file under "removed", with the day).
    Returns (status, answer)."""
    color = _color(add if add is not None else remove)
    if color is None or (add is not None and remove is not None):
        return 400, {"ok": False, "why": "color", "words": NOT_UNDERSTOOD}
    with arrange.locked(HOME / "brand.lock"):
        d = _read_json(BRAND) or {}
        colors = load_brand()
        removed = [x for x in (d.get("removed") if isinstance(d.get("removed"), list) else []) if isinstance(x, dict)]
        if add is not None and color not in colors:
            if len(colors) >= BRAND_MAX:
                return 409, {"ok": False, "why": "full", "words": BRAND_FULL, "colors": colors}
            colors.append(color)
        elif remove is not None and color in colors:
            colors.remove(color)
            removed = (removed + [{"color": color, "at": now_iso()}])[-200:]
        else:
            return 200, {"ok": True, "colors": colors}
        d.update(v=1, colors=colors, removed=removed, updated=now_iso())
        arrange.write_whole(BRAND, d)
        return 200, {"ok": True, "colors": colors}


def load_yours():
    """Fonts they loaded by name, newest first."""
    d = _read_json(FONTS_FILE) or {}
    out = []
    for f in d.get("fonts") if isinstance(d.get("fonts"), list) else []:
        if font_ok(f) and f not in out:
            out.append(f)
    return out[:YOURS_MAX]


def add_font(name):
    """Keep a font they loaded by name under "Yours". Returns (status, answer)."""
    if not font_ok(name):
        return 400, {"ok": False, "why": "font", "words": FONT_BAD}
    curated = {f for _, fs in FONT_GROUPS for f, _ in fs} | {f[0] for f in STORY_FONTS}
    with arrange.locked(HOME / "design-fonts.lock"):
        yours = load_yours()
        if name in curated or name in yours:
            return 200, {"ok": True, "yours": yours}
        if len(yours) >= YOURS_MAX:
            return 409, {"ok": False, "why": "full", "words": YOURS_FULL, "yours": yours}
        yours = [name] + yours
        arrange.write_whole(FONTS_FILE, {"v": 1, "fonts": yours, "updated": now_iso()})
        return 200, {"ok": True, "yours": yours}


def fonts_for_page(kind=CAROUSEL):
    own = {f[0] for f in OWN_FACES if (FONT_DIR / f"{f[3]}.ttf").is_file()}
    groups = [{"name": g, "fonts": [{"name": n, "weights": w, "own": n in own} for n, w in fs]} for g, fs in FONT_GROUPS]
    if kind == STORIES:
        # her story fonts first, each with its Instagram style beside it ("Classic · Figtree"); then the rest
        groups = [{"name": STORY_FONT_GROUP, "fonts": [{"name": n, "weights": w, "own": n in own, "nick": nick}
                                                       for n, w, nick in STORY_FONTS]}] + groups
    return {
        "groups": groups,
        "yours": load_yours(),
        "faces": [{"family": fam, "weight": wt, "style": st, "file": key} for fam, wt, st, key in OWN_FACES if fam in own],
        "default": STORY_TEXT["font"] if kind == STORIES else DEFAULT_FONT, "fallback": FALLBACK_FONT, "google": GOOGLE_CSS,
        "pattern": "^" + FONT.pattern + "$", "max": FONT_MAX,
        "nicks": {n: nick for n, _, nick in STORY_FONTS} if kind == STORIES else {},
    }


# ---------- the sets of slides saved from a design ----------

def _journal_path(kit, did, token, kind=CAROUSEL):
    return sets_dir(kit, kind) / f"{did}-{token}.json"


def _journal_ok(j, kind=CAROUSEL):
    """Is this a record of a save that this file wrote, with names it can act on?"""
    k = K(kind)
    try:
        if not (ID.fullmatch(j["design"]) and TOKEN.fullmatch(j["token"]) and j["state"] in ("moving", "done", "undone")):
            return False
        base, files = j["base"], j["files"]
        if (not isinstance(base, str) or base != safe_base(base, kind) or not isinstance(files, list)
                or not k["slides"][0] <= len(files) <= k["slides"][1]):
            return False
        for i, f in enumerate(files, 1):
            if f["staged"] != f"slide-{i:02d}.jpg" or f["final"] != k["set_name"].format(base=base, i=i):
                return False
            if not re.fullmatch(r"[0-9a-f]{64}", f["sha256"]):
                return False
        return validate_state(j["layout"], kind=kind)[0] is not None
    except (KeyError, TypeError, AttributeError):
        return False


_checked = {}                           # a save's record -> its size and time when it was last found good


def _journal(kit, did, token, kind=CAROUSEL):
    """One save's record, or None when it is not there or is not one this file wrote. The check of a record
    is remembered for as long as the file is unchanged, so a shoot with many saved sets stays quick to save in."""
    p = _journal_path(kit, did, token, kind)
    try:
        st = p.stat()
    except OSError:
        return None
    sig = (st.st_size, st.st_mtime_ns)
    j = _read_json(p)
    if not j:
        return None
    if _checked.get(str(p)) != sig:
        if not _journal_ok(j, kind):
            return None
        if len(_checked) > 5000:
            _checked.clear()
        _checked[str(p)] = sig
    return j if j.get("design") == did and j.get("token") == token else None


def _journals(kit, kind=CAROUSEL):
    out = []
    for f in sorted(kit_mod._listing(sets_dir(kit, kind))):
        m = re.fullmatch(r"([a-z][a-z0-9]{5,23})-([a-z0-9]{8,24})\.json", f)
        if m:
            j = _journal(kit, m.group(1), m.group(2), kind)
            if j:
                out.append(j)
    return out


def _order(j):
    """Where a save stands among the kit's saves: each is numbered, one higher than the last, when it is
    written down (with the slides lock held), so "the newest" never rests on two clocks reading the same second."""
    return (j.get("n") if type(j.get("n")) is int else 0, str(j.get("finished") or j.get("at") or ""))


def last_done(kit, did, kind=CAROUSEL):
    """The newest whole set saved from this design, or None."""
    done = [j for j in _journals(kit, kind) if j["design"] == did and j["state"] == "done"]
    return max(done, key=_order) if done else None


def _set_there(kit, j, kind=CAROUSEL):
    """Is every slide of this set in the Carousel folder (a story's: the Stories folder): its name in the folder's
    own listing, and a file of the size written down (so another design's slides under the same names are not
    taken for this one's)?"""
    car = kit / K(kind)["folder"]
    have = kit_mod._names(car)
    for f in j["files"]:
        real = have.get(kit_mod._nf(f["final"]))
        if real is None:
            return False
        try:
            if type(f.get("size")) is int and os.path.getsize(car / real) != f["size"]:
                return False
        except OSError:
            return False
    return True


def photo_marks(kit, state, rows=None, rec=None):
    """{a photo's number, as text: the mark of that photo as it is on the drive now}, for the photos a layout
    uses. The mark is the one the page is given with each photo (arrange.state_for_page's "v"): it changes
    when the photo is exported again under the same name. It is how a save knows which edit of a photo its
    slides were drawn from."""
    used = sorted({b["n"] for b in state["blocks"] if b.get("type") != "text" and b.get("n") is not None})
    if not used:
        return {}
    rows = rows if rows is not None else arrange.sheet_rows(kit)
    rec = rec if rec is not None else kit_mod.load_rec(kit)
    by = {x["n"]: x for x in rows}
    try:
        names = set(os.listdir(arrange.previews_dir(kit)))
    except OSError:
        names = set()
    small, out = arrange.SIZES["s"], {}
    for n in used:
        row, name = by.get(n), ""
        if row is not None:
            src = arrange.photo_path(kit, rec, row)
            if src is not None:
                try:
                    name = arrange.preview_file(kit, row, small, src).name
                except OSError:
                    src = None
            if src is None:
                name = arrange._older_copy(names, row, small) or ""
        out[str(n)] = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8] if name else ""
    return out


def drawn_ok(v):
    """What a page says a set of slides was drawn from, checked: {"photos": {number: mark}, "fell": [fonts that
    could not be loaded, so their words were drawn in Georgia]}. None when it is not that."""
    if not isinstance(v, dict):
        return None
    photos, fell = v.get("photos"), v.get("fell", [])
    if not isinstance(photos, dict) or len(photos) > MAX_BLOCKS or not isinstance(fell, list) or len(fell) > MAX_TEXTS:
        return None
    for k, m in photos.items():
        if not (isinstance(k, str) and re.fullmatch(r"[0-9]{1,6}", k) and isinstance(m, str) and re.fullmatch(r"[0-9a-f]{0,8}", m)):
            return None
    if not all(font_ok(f) for f in fell):
        return None
    return {"photos": {k: photos[k] for k in sorted(photos)}, "fell": sorted(set(fell))}


def _fell(j):
    d = j.get("drawn") if isinstance(j.get("drawn"), dict) else {}
    return sorted(f for f in (d.get("fell") or []) if font_ok(f))


def _same_as(kit, d, j, drawn=None, kind=CAROUSEL):
    """Would saving this design now make the very slides of set j again? Only when the layout is the one that
    made them, the design still has the name they were saved under, every photo on them is the same edit of
    that photo (a photo exported again since is a change), the same fonts were missing then as now (when the
    page says which are, in drawn), and every one of the set's files is still in the Carousel folder."""
    if j["layout"] != d["state"]:
        return False
    if kit_mod._fold(safe_base(d["name"], kind)) != kit_mod._fold(safe_base(j.get("name") or "", kind)):
        return False
    was = j.get("drawn") if isinstance(j.get("drawn"), dict) else None
    if was is None or was.get("photos") != photo_marks(kit, d["state"]):
        return False
    if drawn is not None and sorted(drawn.get("fell") or []) != _fell(j):
        return False
    return _set_there(kit, j, kind)


def set_info(kit, d, kind=CAROUSEL):
    """What the page needs to know about the last set saved from a design: its name, how many slides, when,
    "same" (pressing Save slides would make nothing new: see _same_as) and "fell" (the fonts that could not
    be loaded when it was saved; the page knows which can't be loaded now, and a difference is a change)."""
    j = last_done(kit, d["id"], kind)
    if not j:
        return None
    same = _same_as(kit, d, j, kind=kind)
    return {"base": j["base"], "count": len(j["files"]), "at": j.get("finished") or j.get("at"), "same": same,
            "fell": _fell(j), "words": KW(kind, ALREADY.format(base=j["base"])) if same else ""}


def _unfinished(kit, did, kind=CAROUSEL):
    """Is a save of this design written down and not finished (it was cut off part way)?"""
    return any(j["design"] == did and j["state"] == "moving" for j in _journals(kit, kind))


def jpeg_size(data):
    """(width, height) from a JPEG's own header, or None."""
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        m = data[i + 1]
        if m == 0xFF:
            i += 1
            continue
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        n = struct.unpack(">H", data[i + 2:i + 4])[0]
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if i + 9 > len(data):
                return None
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        if m == 0xDA or n < 2:
            return None
        i += 2 + n
    return None


def slide_ok(data, kind=CAROUSEL):
    """Is this one finished slide: a whole JPEG whose own header says 1080 by 1350 (a story: 1080 by 1920)?"""
    k = K(kind)
    return (SLIDE_MIN <= len(data) <= SLIDE_CAP and data[:2] == b"\xff\xd8" and data[-2:] == b"\xff\xd9"
            and jpeg_size(data) == (k["w"], k["h"]))


def stage_slide(kit, did, token, i, of, data, kind=CAROUSEL):
    """One finished slide from the page, into the kit's hidden staging folder and nowhere else. Returns
    (status, answer). The same slide sent again (its answer was lost) is fine; a different picture for a
    slide that has already arrived is refused, and the page starts a new set."""
    if not slide_ok(data, kind):
        return 400, {"ok": False, "why": "slide", "words": NOT_UNDERSTOOD}
    d = load_design(kit, did, kind)
    if d is None:
        return 404, {"ok": False, "why": "design", "words": NO_DESIGN}
    if of != d["state"]["slides"]:
        return 409, {"ok": False, "why": "changed", "words": KW(kind, CHANGED)}
    cant = cant_save(kit, d["name"], kind=kind)     # a PC only: a slide that could never be opened is not taken in at all
    if cant:
        return 409, {"ok": False, "why": cant[0], "words": cant[1]}
    root = staging_dir(kit, kind)
    folder = root / f"{did}-{token}"
    if not kit_mod._has(root, folder.name) and len(waiting_sets(kit, kind)) >= STAGING_MOST:
        tidy(kit, STAGING_PRESSED, wait=2.0, kind=kind)     # unfinished saves nobody came back to are cleared first
        if len(waiting_sets(kit, kind)) >= STAGING_MOST:
            return 503, {"ok": False, "why": "waiting", "words": SLIDES_WAITING}
    j = _journal(kit, did, token, kind)
    if j and j["state"] in ("moving", "done"):
        return 409, {"ok": False, "why": "again", "words": KW(kind, SLIDE_AGAIN)}     # this set is already on its way in
    arrange.make_folder(folder)
    dst = folder / f"slide-{i:02d}.jpg"
    sha = hashlib.sha256(data).hexdigest()
    if not kit_mod._has(folder, dst.name):
        tmp = folder / f".part-{os.getpid()}-{threading.get_ident()}-{dst.name}"
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        if not kit_mod.place(tmp, dst):
            try:
                tmp.unlink()            # our own scratch file; the slide that is there stays
            except OSError:
                pass
    if kit_mod._sha(dst) != sha:
        return 409, {"ok": False, "why": "again", "words": KW(kind, SLIDE_AGAIN)}
    have = sum(1 for n in kit_mod._listing(folder) if STAGED.fullmatch(n))
    return 200, {"ok": True, "i": i, "of": of, "have": have}


def staged_ok(kit, did, token, count, kind=CAROUSEL):
    """Does staging hold exactly slide-01 to slide-<count> for this set, each a whole slide?"""
    folder = staging_dir(kit, kind) / f"{did}-{token}"
    have = sorted(n for n in kit_mod._listing(folder) if STAGED.fullmatch(n))
    if have != [f"slide-{i:02d}.jpg" for i in range(1, count + 1)]:
        return False
    for n in have:
        try:
            if not slide_ok((folder / n).read_bytes(), kind):
                return False
        except OSError:
            return False
    return True


def free_base(kit, name, kind=CAROUSEL):
    """The set's name: the design's name made safe for a file, or that name with (2), (3)... after it. The first
    for which the Carousel folder's own listing holds no file that starts "<name> - slide ", compared the way
    a drive that ignores capitals and keeps accents its own way would compare them. (A story's: the Stories
    folder, and "<name> - ".)"""
    kk = K(kind)
    base0 = safe_base(name, kind)
    taken = [kit_mod._fold(n) for n in kit_mod._listing(kit / kk["folder"])]
    k = 1
    while True:
        base = base0 if k == 1 else kk["set_again"].format(base=base0, k=k)
        prefix = kit_mod._fold(kk["set_name"].split("{i")[0].format(base=base))
        if not any(t.startswith(prefix) for t in taken):
            return base
        k += 1


SET_FOLDER = re.compile(r"([a-z][a-z0-9]{5,23})-([a-z0-9]{8,24})")


def waiting_sets(kit, kind=CAROUSEL):
    """The sets of slides waiting in the kit's hidden staging folder: only folders this file names."""
    root = staging_dir(kit, kind)
    return sorted(n for n in kit_mod._listing(root) if SET_FOLDER.fullmatch(n) and (root / n).is_dir() and not (root / n).is_symlink())


def kept_dir(kit, j, kind=CAROUSEL):
    """Where slides that had been in the Carousel folder, and were put back because their set could not be
    finished, are set aside for good: a folder named for when that happened and the name the set had."""
    last = ([x for x in (j.get("undone") or []) if isinstance(x, dict)] or [{}])[-1]
    when = re.sub(r"[^0-9T-]", "", str(last.get("at") or j.get("finished") or ""))[:17] or "undated"
    return kit / ".kit" / K(kind)["older"] / f"{when} {safe_base(last.get('base') or j['base'], kind)}"


def _sweep_staging(kit, keep=STAGING_KEEP, kind=CAROUSEL):
    """With the slides lock held: slides that arrived for a set that never finished arriving, and were never
    put into the Carousel folder, are the Assistant's own scratch. A day after the last one arrived they are
    cleared, so abandoned saves do not eat the drive. Only folders this file names, only files named like a
    staged slide or a scratch file, never a set that is written down as on its way in. A slide that HAD been
    in the Carousel folder (its set could not be finished, and it was put back) is never cleared: it is set
    aside in the kit's hidden design-slides-older folder, under the name it had. Returns how many sets went."""
    root = staging_dir(kit, kind)
    went = 0
    for name in waiting_sets(kit, kind):
        m = SET_FOLDER.fullmatch(name)
        folder = root / name
        j = _journal(kit, m.group(1), m.group(2), kind)
        if j and j["state"] == "moving":
            continue
        try:
            old = time.time() - folder.stat().st_mtime > keep
        except OSError:
            continue
        if not old and not (j and j["state"] == "done"):
            continue
        back = set(j.get("back") or []) if j and j["state"] == "undone" else set()
        final_of = {f["staged"]: f["final"] for f in j["files"]} if j else {}
        for f in sorted(kit_mod._listing(folder)):
            p = folder / f
            if not ((STAGED.fullmatch(f) or f.startswith(".part-")) and p.is_file() and not p.is_symlink()):
                continue
            try:
                if f in back and f in final_of:
                    dst = kept_dir(kit, j, kind)
                    arrange.make_folder(dst)
                    kit_mod._move_one(p, dst / final_of[f])     # never over another file; if it can't go, it stays here
                else:
                    p.unlink()
            except OSError:
                pass
        try:
            os.rmdir(folder)
            went += 1
        except OSError:
            pass
    return went


def tidy(kit, keep=STAGING_KEEP, wait=0.0, kind=CAROUSEL):
    """Clear the waiting slides of saves that were never finished (see _sweep_staging), if nothing else is
    changing this kit's slides right now. Returns how many sets were cleared, or None when it could not look."""
    if not waiting_sets(kit, kind):
        return 0
    try:
        lock_file = kit / ".kit" / K(kind)["slides_lock"]   # kit.py's own lock (stories: the designer's own); staging is beside it
        with kit_mod._held(lock_file, wait) as mine:
            return _sweep_staging(kit, keep, kind) if mine else None
    except (OSError, arrange.Busy):
        return None


def _saved_words(j, kind=CAROUSEL):
    """"Saved N slides ...": N is how many of the set are in the folder under their names (a slide the
    photographer has since renamed, moved or changed is theirs, and is not counted)."""
    n = len(j["files"]) - len(j.get("theirs") or [])
    return KW(kind, (SAVED_ONE if n == 1 else SAVED_SET).format(n=n, base=j["base"]))


def _result(state, j=None, why="", words="", **more):
    out = {"state": state, "base": j["base"] if j else "", "count": len(j["files"]) if j else 0, "why": why, "words": words}
    out.update(more)
    return out


def _undo(kit, j, why, blocked="", kind=CAROUSEL):
    """A set that cannot be finished under its name (a file turned up in the Carousel folder under a name
    one of its slides needs, or a staged slide is gone or is not the one written down) is put back: every
    slide of it already in the Carousel folder goes back to staging, known by its hash. Nothing is deleted,
    nothing is written over, and the record ends as "undone". The next try picks a name afresh. This is only
    ever done to a set that was still PART WAY in (see _finish): the slides it takes back are written down
    ("back"), and the day-old clearing of staging sets those aside instead of clearing them."""
    car = kit / K(kind)["folder"]
    stag = staging_dir(kit, kind) / f"{j['design']}-{j['token']}"
    arrange.make_folder(stag)
    back = set(j.get("back") or [])
    for f in j["files"]:
        if kit_mod._has(car, f["final"]) and not kit_mod._has(stag, f["staged"]) and kit_mod._sha(car / f["final"]) == f["sha256"]:
            back.add(f["staged"])       # written down in the record below: this slide has been in the Carousel folder
            j["back"] = sorted(back)
            arrange.write_whole(_journal_path(kit, j["design"], j["token"], kind), j)
            kit_mod._move_one(car / f["final"], stag / f["staged"])
    undone = list(j.get("undone") or []) + [{"base": j["base"], "why": why, "blocked_by": blocked, "at": now_iso()}]
    j.update(state="undone", undone=undone[-10:], finished=now_iso(), back=sorted(back))
    arrange.write_whole(_journal_path(kit, j["design"], j["token"], kind), j)
    arrange.log(f"design set {j['base']!r} for {kit.name} was put back ({why})")
    return _result("problem", j, why=why, words=KW(kind, IN_THE_WAY if why == "clash" else NOT_FINISHED))


def _finish(kit, j, kind=CAROUSEL):
    """Carry out (or finish) the save written down in a record: every staged slide to its name in the
    Carousel folder, never over another file, each checked by its hash; then the kit's record, the kit page,
    the posting queue's picture and the line for Claude. Safe to run any number of times. Trouble with the
    drive itself is raised (OSError) and leaves the record saying "moving", for the next run."""
    kk = K(kind)
    car = kit / kk["folder"]
    stag = staging_dir(kit, kind) / f"{j['design']}-{j['token']}"
    car.mkdir(exist_ok=True)
    seen = {}

    def placed_before(k):
        """Had slide k already been put in the Carousel folder by an earlier run of this same save? Slides go
        in in order and leave staging only by going in, so: its staged copy is not in staging, and either a
        later slide of the set is in the Carousel folder, or no slide of the set is left in staging at all and
        at least one is in the folder. Then whatever has happened to slide k since is the photographer's own
        doing in their own folder (renamed, moved, edited), and no other slide is moved because of it."""
        if "left" not in seen:
            seen["left"] = {kit_mod._nf(n) for n in kit_mod._listing(stag)}
            names = kit_mod._names(car)
            seen["there"] = set()
            for i, x in enumerate(j["files"], 1):
                real = names.get(kit_mod._nf(x["final"]))
                try:
                    if real is not None and kit_mod._sha(car / real) == x["sha256"]:
                        seen["there"].add(i)
                except OSError:
                    pass
        left = {x["staged"] for x in j["files"]} & seen["left"]
        if j["files"][k - 1]["staged"] in left:
            return False
        return any(i > k for i in seen["there"]) or (not left and bool(seen["there"]))

    theirs = list(j.get("theirs") or [])         # slides the photographer has since renamed, moved or changed
    for k, f in enumerate(j["files"], 1):
        got = kit_mod._move_one(stag / f["staged"], car / f["final"])
        if got == "there" and kit_mod._sha(car / f["final"]) != f["sha256"]:
            got = "different"           # a file has that name, and it is not the slide this save made
        elif got == "moved" and kit_mod._sha(car / f["final"]) != f["sha256"]:
            got = "clash"
        if got in ("gone", "different") and placed_before(k):
            if f["final"] not in theirs:
                theirs.append(f["final"])
            got = "theirs"
        if got in ("clash", "different"):
            return _undo(kit, j, "clash", f["final"], kind)
        if got == "gone":
            return _undo(kit, j, "redo", kind=kind)
        _test_stop(f"after-{k}")
    if theirs:
        j["theirs"] = theirs
    files = [f["final"] for f in j["files"]]
    entry = {"kind": "laid-out", "base": j["base"], "files": files, "saved": j["at"], "design": j["design"],
             "token": j["token"], "name": j.get("name") or j["base"]}

    all_key, set_key = kk["rec_all"], kk["rec_set"]      # "laid_out" and "carousel_set"; a story's: "stories_..."

    def note(rec):
        sets = [x for x in (rec.get(all_key) or []) if isinstance(x, dict)]
        if not any(x.get("design") == j["design"] and x.get("token") == j["token"] for x in sets):
            sets.append({k: entry[k] for k in ("base", "files", "saved", "design", "token")})
        rec[all_key] = sets
        rec[set_key] = entry

    rec = kit_mod.load_rec(kit)
    if rec.get(set_key) != entry or not any(isinstance(x, dict) and x.get("token") == j["token"] and x.get("design") == j["design"]
                                            for x in rec.get(all_key) or []):
        kit_mod.update_rec(kit, note)
    _test_stop("after-record")
    j.update(state="done", finished=j.get("finished") if j.get("state") == "done" else now_iso())
    arrange.write_whole(_journal_path(kit, j["design"], j["token"], kind), j)
    _test_stop("after-done")
    for nicety in (kit_mod.write_page, kit_mod._refresh_posting):
        try:
            nicety(kit)                 # the kit is already right; any trouble here is left for the next time
        except (Exception, SystemExit) as e:  # noqa: BLE001
            arrange.log(f"design set for {kit.name}: {nicety.__name__} failed: {e.__class__.__name__}: {str(e)[:160]}")
    try:
        arrange.add_waiting(kit.name, kit_mod.load_rec(kit).get("name") or kit.name, kk["piece"], len(files), base=j["base"])
    except (arrange.Busy, OSError) as e:
        arrange.log(f"design set for {kit.name}: the line for Claude could not be written ({e.__class__.__name__})")
    try:
        os.rmdir(stag)                  # our own staging folder, empty now (left alone if anything is still in it)
    except OSError:
        pass
    arrange.log(f"design set {j['base']!r} for {kit.name}: {len(files) - len(theirs)} slides are in the {kk['folder']} folder"
                + (f" ({len(theirs)} more were renamed, moved or changed by hand since they were put there; left as they are)" if theirs else ""))
    return _result("done", j, words=_saved_words(j, kind))


def _is_shown(kit, j, rec=None, kind=CAROUSEL):
    """Is this saved set the one the kit page and the posting queue show as the carousel now (a story's: as the
    stories)? Reads only."""
    rec = rec if rec is not None else kit_mod.load_rec(kit)
    key = K(kind)["rec_set"]
    cs = rec.get(key) if isinstance(rec.get(key), dict) else {}
    shown = kit_mod.stories_shown(kit, rec) if kind == STORIES else kit_mod.carousel_shown(kit, rec)
    return shown["kind"] == "laid-out" and cs.get("design") == j["design"] and cs.get("token") == j["token"]


def _show_again(kit, j, kind=CAROUSEL):
    """Save slides was pressed on a design whose slides are already saved, and the kit is showing other
    slides as its carousel (a new order from the picker put the plain ones back, another design was saved
    since, or a Canva carousel was fetched): this set is the one shown again. No file is made, moved or
    changed; only the kit's record says which set is shown, and the kit page and the posting queue's picture
    follow. Run by the commit command (a process of its own), with the slides lock held."""
    files = [f["final"] for f in j["files"]]
    entry = {"kind": "laid-out", "base": j["base"], "files": files, "saved": j["at"], "design": j["design"],
             "token": j["token"], "name": j.get("name") or j["base"]}
    if _is_shown(kit, j, kind=kind):
        return False                    # it is the set shown already: nothing is written

    def note(r):
        r[K(kind)["rec_set"]] = dict(entry, shown=now_iso())

    kit_mod.update_rec(kit, note)
    for nicety in (kit_mod.write_page, kit_mod._refresh_posting):
        try:
            nicety(kit)
        except (Exception, SystemExit) as e:  # noqa: BLE001
            arrange.log(f"design set for {kit.name}: {nicety.__name__} failed: {e.__class__.__name__}: {str(e)[:160]}")
    arrange.log(f"design set {j['base']!r} for {kit.name} is the carousel shown again")
    return True


def commit(kit, did, token, rev=None, drawn=None, kind=CAROUSEL):
    """Put a staged set of slides into the Carousel folder. One run at a time for a kit's Carousel folder,
    across processes (kit.py's slides lock, which the plain-slide maker holds too). Returns
    {"state": "done" | "already" | "problem", "base", "count", "why", "words"}. Never raises for trouble
    with the drive: that is a problem in plain words, and nothing is lost."""
    try:
        lock_file = kit_mod.hidden(kit) / K(kind)["slides_lock"]
    except OSError as e:
        return _result("problem", why="drive", words=KW(kind, DRIVE.format(why=kit_mod._plain_os(e))))
    with kit_mod._held(lock_file, kit_mod.SLIDES_WAIT) as mine:
        if not mine:
            return _result("problem", why="busy", words=KW(kind, BUSY))
        try:
            return _commit(kit, did, token, rev, drawn, kind)
        except arrange.Busy:
            return _result("problem", why="busy", words=KW(kind, BUSY))
        except OSError as e:
            arrange.log(f"design commit for {kit.name} stopped: {e.__class__.__name__}: {str(e)[:160]}")
            return _result("problem", why="drive", words=KW(kind, DRIVE.format(why=kit_mod._plain_os(e))))


def _commit(kit, did, token, rev, drawn=None, kind=CAROUSEL):
    """With the slides lock held. In order: finish any save an earlier run was cut off in (under the name it
    had written down); clear old scratch; if this very set is already in, say so again; refuse if the design
    has changed since the slides were drawn, or a photo on them was exported again since the page that drew
    them opened (drawn, when the page says what it drew from); if saving now would make the very slides of
    the design's last set again (_same_as), make nothing new; refuse unless every slide has arrived; choose
    the name from the folder's own listing; write everything down, with what the slides were drawn from;
    then move the files."""
    finished_now = []
    for j in _journals(kit, kind):
        if j["state"] == "moving":
            if _finish(kit, j, kind)["state"] == "done":
                finished_now.append((j["design"], j["token"]))
    _sweep_staging(kit, kind=kind)
    d = load_design(kit, did, kind)
    if d is None:
        return _result("problem", why="design", words=NO_DESIGN)
    mine = _journal(kit, did, token, kind)
    if mine and mine["state"] == "done":
        return _result("done", mine, words=_saved_words(mine, kind))
    if rev is not None and rev != d["rev"]:
        return _result("problem", why="changed", words=KW(kind, CHANGED))
    marks = photo_marks(kit, d["state"])
    if drawn is not None and drawn["photos"] != marks:
        return _result("problem", why="photos", words=KW(kind, PHOTO_NEWER))
    last = last_done(kit, did, kind)
    if last and _same_as(kit, d, last, drawn, kind):
        if (last["design"], last["token"]) in finished_now:
            return _result("done", last, words=_saved_words(last, kind))
        _show_again(kit, last, kind)
        return _result("already", last, words=KW(kind, ALREADY.format(base=last["base"])))
    count = d["state"]["slides"]
    if not staged_ok(kit, did, token, count, kind):
        return _result("problem", why="missing", words=KW(kind, MISSING))
    stag = staging_dir(kit, kind) / f"{did}-{token}"
    base = free_base(kit, d["name"], kind)
    cant = cant_save(kit, d["name"], base, kind)    # a PC only, before anything is written down or moved
    if cant:
        return _result("problem", why=cant[0], words=cant[1])
    files = []
    for i in range(1, count + 1):
        p = stag / f"slide-{i:02d}.jpg"
        files.append({"staged": p.name, "final": K(kind)["set_name"].format(base=base, i=i), "size": p.stat().st_size, "sha256": kit_mod._sha(p)})
    j = {"v": 1, "n": 1 + max([_order(x)[0] for x in _journals(kit, kind)] or [0]),
         "design": did, "token": token, "name": d["name"], "rev": d["rev"], "stamp": d.get("stamp"), "base": base,
         "state": "moving", "files": files, "layout": d["state"], "at": now_iso(),
         "drawn": {"photos": marks, "fell": sorted((drawn or {}).get("fell") or [])},
         "undone": list((mine or {}).get("undone") or [])}
    if kind == STORIES:
        j["kind"] = STORIES
    arrange.write_whole(_journal_path(kit, did, token, kind), j)    # written down BEFORE the first file moves
    _test_stop("after-journal")
    return _finish(kit, j, kind)


# ---------- what the page is given ----------

def _design_for_page(kit, d, kind=CAROUSEL):
    return {"id": d["id"], "name": d["name"], "rev": d["rev"], "updated": d.get("updated"), "t": d.get("t"),
            "state": d["state"], "dropped": int(d.get("dropped") or 0), "set": set_info(kit, d, kind),
            "unfinished": _unfinished(kit, d["id"], kind)}


def _design_list(kit, designs, open_id=None, kind=CAROUSEL):
    done = {}
    for j in _journals(kit, kind):
        if j["state"] == "done" and (j["design"] not in done or _order(j) > done[j["design"]][0]):
            done[j["design"]] = (_order(j), j["base"])
    return [{"id": d["id"], "name": d["name"], "slides": d["state"]["slides"], "updated": d.get("updated"), "t": d.get("t"),
             "rev": d["rev"], "open": d["id"] == open_id, "set": done.get(d["id"], (None, None))[1]} for d in designs]


def shoots_for_page(open_kit=None):
    """Every shoot that has a post kit, for the shoot menu: its folder name (which is how a page names it),
    the name they gave it, how many photos, how many designs."""
    out = []
    try:
        h = posts.home()
        names = sorted(os.listdir(h / posts.CONTENT_NAME)) if h else []
    except (Exception, SystemExit):  # noqa: BLE001
        names = []
    for name in names:
        k = arrange.kit_by_name(name)
        if k is None:
            continue
        try:
            rec = kit_mod.load_rec(k)
        except (OSError, ValueError):
            continue
        out.append({"kit": k.name, "name": rec.get("name") or k.name, "photos": len(arrange.sheet_rows(k)),
                    "designs": count_designs(k), "story_designs": count_designs(k, STORIES),
                    "open": open_kit is not None and k.name == open_kit.name})
    out.sort(key=lambda s: s["kit"], reverse=True)          # folders start with the date: newest first
    return out


LIMITS = {"slides": [SLIDES_MIN, SLIDES_MAX], "blocks": MAX_BLOCKS, "texts": MAX_TEXTS, "text": TEXT_MAX,
          "text_total": TEXT_TOTAL, "name": NAME_MAX, "frame_min": FRAME_MIN, "text_w_min": TEXT_W_MIN,
          "text_h_max": TEXT_H_MAX, "on_strip": ON_STRIP, "zoom": list(ZOOM), "size": list(SIZE), "ls": list(LS),
          "lh": list(LH), "border": list(BORDER), "brand": BRAND_MAX, "slide_bytes": SLIDE_CAP, "save_bytes": POST_CAP,
          "w": W, "h": H}


def limits_for(kind=CAROUSEL):
    """The numbers a page goes by, for one kind. The carousel's are LIMITS exactly as they always were; a story's
    are the same with its own size, how many stories a set may hold, where Instagram's own buttons sit, and its
    kind. The page is given these twice: written into it (design_page.py: the scripts read W and H from them
    before anything is drawn) and with every state."""
    out = dict(LIMITS)
    if kind == STORIES:
        k = KINDS[STORIES]
        out.update(slides=list(k["slides"]), w=k["w"], h=k["h"], kind=STORIES, safe=list(k["safe"]))
    return out


def story_handle():
    """The name the stories preview shows at the top: their Instagram handle from the grid they had read
    (~/.studio/feed.json, posting_queue.py), else "yourname" (decision 18). Never anyone else's."""
    f = _read_json(HOME / "feed.json") or {}
    h = str(f.get("handle") or "").lstrip("@")
    return h if re.fullmatch(r"[A-Za-z0-9._]{1,30}", h) else STORY_HANDLE_FALLBACK


def state_for_page(kit, want=None, kind=CAROUSEL):
    """Everything the designer page draws from, in one answer. No path and no file name is in it. None when
    the shoot's numbered list can't be read right now. The first visit to a shoot with no design makes one
    (stories: one empty white story; the shoot's one stories design, the newest, is the one always opened)."""
    st = arrange.state_for_page(kit, "carousel") if arrange.sheet_rows(kit) else None
    if st is None:
        return None
    rows, stamp = arrange.sheet_rows(kit), arrange.sheet_stamp(kit)
    if not rows or stamp != st["stamp"]:
        return None                     # the list was re-made between two looks: the page asks again
    with arrange.locked(design_lock(kit)):          # held only for the designs themselves
        if ensure_design(kit, kind) is None:
            return None
        designs = [_sync(kit, d, rows, stamp, kind) for d in list_designs(kit, kind)]
    designs.sort(key=lambda d: (float(d.get("t") or 0), d["id"]), reverse=True)
    if kind == STORIES:
        want = None                     # one stories design a shoot: the newest is the one opened
    d = next((x for x in designs if x["id"] == want), None)
    fell_back = want is not None and d is None
    d = d or designs[0]
    rec = kit_mod.load_rec(kit)
    story = kind == STORIES
    out = {
        "ok": True, "kit": kit.name, "name": st["name"], "stamp": stamp, "total": st["total"],
        "photos": st["photos"], "previews": st["previews"], "sizes": dict(arrange.SIZES),
        # the photos frames are filled from first: the carousel's picks; a story takes the photos in number order (hers)
        "carousel": [] if story else [n for n in st["now"]["nums"]], "slide_bg": "#ffffff" if story else kit_bg(rec),
        "design": _design_for_page(kit, d, kind), "fell_back": fell_back,
        "designs": _design_list(kit, designs, d["id"], kind),
        "templates": _templates_for_page(list_templates(kind)), "starters": K(kind)["starters"],
        "brand": {"colors": load_brand(), "max": BRAND_MAX},
        "fonts": fonts_for_page(kind), "shoots": shoots_for_page(kit), "limits": limits_for(kind),
        "blank": blank_story() if story else {"slides": DEFAULT_SLIDES, "bg": kit_bg(rec), "blocks": []},
        "text": dict(STORY_TEXT, text=DEFAULT_TEXT) if story else {"text": DEFAULT_TEXT, "font": DEFAULT_FONT},
        "kit_page": st["kit_page"],
    }
    if story:
        out["kind"] = STORIES
        out["handle"] = story_handle()
    return out


# ---------- the routes ----------

def _one(q, key):
    v = q.get(key, [""])
    return v[0] if v else ""


def _send_page(handler, text, csp=True):
    out = text.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    if csp:
        handler.send_header("Content-Security-Policy", PAGE_CSP)
    handler.send_header("Content-Length", str(len(out)))
    handler.end_headers()
    handler.wfile.write(out)


def _get_page(handler, q):
    import design_page
    kind = kind_ok(_one(q, "kind"))
    if kind is None:
        return _send_page(handler, design_page.plain_page(NOT_UNDERSTOOD))
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return _send_page(handler, design_page.plain_page(CANT_FIND))
    st = arrange.state_for_page(kit, "carousel") if arrange.sheet_rows(kit) else None
    if st is None:
        return _send_page(handler, design_page.plain_page(NOT_READY))
    to_make = any(not x["have"] and not x["missing"] for x in st["photos"])
    if to_make:
        # a PC without Pillow, or a kit too deep in folders for a PC: said so, as the pickers say it, rather than
        # "getting your photos ready" for ever. A Mac: never (arrange.cant_make).
        cant = arrange.cant_make(kit, arrange.sheet_rows(kit))
        if cant:
            return _send_page(handler, design_page.plain_page(cant[1] + " Tell Claude and it'll sort it out."))
    deep = too_deep(kit, kind)          # a PC only: the designer's own files would not fit either
    if deep:
        return _send_page(handler, design_page.plain_page(deep + " Tell Claude and it'll sort it out."))
    if st["previews"]["made"] < st["previews"]["of"] and to_make:
        arrange.start_previews(kit)
    tidy(kit, kind=kind)                # day-old slides of saves that were never finished (the Assistant's own scratch)
    _send_page(handler, design_page.page_html(kit.name, kind))


def _get_state(handler, q):
    kind = kind_ok(_one(q, "kind"))
    if kind is None:
        return arrange._send_json(handler, {"ok": False, "why": "kind", "words": NOT_UNDERSTOOD}, 400)
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_json(handler, {"ok": False, "words": CANT_FIND}, 404)
    want = _one(q, "design")
    deep = too_deep(kit, kind)          # a PC only: the first look would make a design, and it could not be written
    if deep:
        return arrange._send_json(handler, {"ok": False, "why": "deep", "words": deep}, 409)
    st = state_for_page(kit, want if ID.fullmatch(want) else None, kind)
    if st is None:
        return arrange._send_json(handler, {"ok": False, "words": NOT_READY}, 404)
    if want and not ID.fullmatch(want):
        st["fell_back"] = True
    arrange._send_json(handler, st)


def _get_font(handler, q):
    key = _one(q, "f")
    if key not in OWN_FILES:
        return handler.send_error(404)
    try:
        data = (FONT_DIR / f"{key}.ttf").read_bytes()
    except OSError:
        return handler.send_error(404)
    handler.send_response(200)
    handler.send_header("Content-Type", "font/ttf")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "private, max-age=604800")
    handler.end_headers()
    handler.wfile.write(data)


GET_PATHS = ("/design.html", "/design-state", "/design-font-file")
POST_PATHS = ("/design", "/design-new", "/design-template", "/design-brand", "/design-font", "/design-slide", "/design-commit")


def handle_get(handler, path, query):
    """Every GET for the designer. Whatever goes wrong, the server answers and stays up."""
    try:
        if not arrange.our_host(handler):
            return handler.send_error(403)
        q = parse_qs(query or "", keep_blank_values=True)
        if path == "/design.html":
            return _get_page(handler, q)
        if path == "/design-state":
            # The first look at a shoot makes its first design, so this is not a question another website
            # may put to the Assistant through someone's browser (the browser says where a request came from).
            if (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
                return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 403)
            return _get_state(handler, q)
        if path == "/design-font-file":
            return _get_font(handler, q)
        return handler.send_error(404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        arrange.log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            if path == "/design-font-file":
                handler.send_error(404)
            elif path.endswith(".html"):
                import design_page
                _send_page(handler, design_page.plain_page(CANT_FIND))
            else:
                arrange._send_json(handler, {"ok": False, "words": TRY_AGAIN if isinstance(e, arrange.Busy) else CANT_REACH}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def _json_body(handler, path, cap):
    """The body of a JSON POST as a dict, after the guard. None when it was refused (and answered)."""
    try:
        handler.connection.settimeout(arrange.BODY_WAIT)    # a body that never arrives must not hold a thread for ever
    except (OSError, AttributeError):
        pass
    bad = arrange.guard(handler, "application/json", cap, path)
    if bad:
        arrange._drain(handler)
        arrange._send_json(handler, {"ok": False, "words": bad[1]}, bad[0])
        return None
    raw = handler.rfile.read(int(handler.headers.get("Content-Length").strip()))
    try:
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, RecursionError):
        body = None
    if not isinstance(body, dict):
        arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 400)
        return None
    return body


def _token(body):
    """The name the page gave this press, or False when it sent one that is not a token."""
    t = body.get("token")
    if t is None:
        return None
    return t if isinstance(t, str) and TOKEN.fullmatch(t) else False


def _post_new(body):
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return 404, {"ok": False, "words": CANT_FIND}
    kind = kind_ok(body.get("kind"))
    if kind is None:
        return 400, {"ok": False, "why": "kind", "words": NOT_UNDERSTOOD}
    token = _token(body)
    copy = body.get("copy")
    if token is False or (copy is not None and (not isinstance(copy, str) or not ID.fullmatch(copy))):
        return 400, {"ok": False, "why": "token", "words": NOT_UNDERSTOOD}
    if copy is not None and "state" in body:
        return 400, {"ok": False, "why": "shape", "words": NOT_UNDERSTOOD}
    if "stamp" in body and body.get("stamp") != arrange.sheet_stamp(kit):
        return 409, {"ok": False, "why": "photos", "words": PHOTOS_CHANGED}
    return new_design(kit, state=body.get("state") if "state" in body else None,
                      name=body.get("name") if "name" in body else None, token=token, copy=copy, kind=kind)


def _post_template(body):
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return 404, {"ok": False, "words": CANT_FIND}
    kind = kind_ok(body.get("kind"))
    if kind is None:
        return 400, {"ok": False, "why": "kind", "words": NOT_UNDERSTOOD}
    token = _token(body)
    if token is False:
        return 400, {"ok": False, "why": "token", "words": NOT_UNDERSTOOD}
    try:
        shoot = kit_mod.load_rec(kit).get("name") or kit.name
    except (OSError, ValueError):
        shoot = kit.name
    return save_template(body.get("name"), body.get("state"), shoot, token, kind)


def _post_brand(body):
    if ("add" in body) == ("remove" in body):
        return 400, {"ok": False, "why": "color", "words": NOT_UNDERSTOOD}
    return change_brand(add=body.get("add") if "add" in body else None, remove=body.get("remove") if "remove" in body else None)


def _post_slide(handler, query):
    try:
        handler.connection.settimeout(arrange.BODY_WAIT)
    except (OSError, AttributeError):
        pass
    bad = arrange.guard(handler, "image/jpeg", SLIDE_CAP, "/design-slide")
    if bad:
        arrange._drain(handler)
        return arrange._send_json(handler, {"ok": False, "words": bad[1]}, bad[0])
    n = int(handler.headers.get("Content-Length").strip())
    data = handler.rfile.read(n)
    q = parse_qs(query or "", keep_blank_values=True)
    kind = kind_ok(_one(q, "kind"))
    if kind is None:
        return arrange._send_json(handler, {"ok": False, "why": "kind", "words": NOT_UNDERSTOOD}, 400)
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_json(handler, {"ok": False, "words": CANT_FIND}, 404)
    did, token, i_txt, of_txt = _one(q, "design"), _one(q, "set"), _one(q, "i"), _one(q, "of")
    if (len(data) != n or not ID.fullmatch(did) or not TOKEN.fullmatch(token)
            or not re.fullmatch(r"[0-9]{1,2}", i_txt) or not re.fullmatch(r"[0-9]{1,2}", of_txt)):
        return arrange._send_json(handler, {"ok": False, "why": "slide", "words": NOT_UNDERSTOOD}, 400)
    i, of = int(i_txt), int(of_txt)
    lo, hi = K(kind)["slides"]
    if not lo <= of <= hi or not 1 <= i <= of:
        return arrange._send_json(handler, {"ok": False, "why": "slide", "words": NOT_UNDERSTOOD}, 400)
    code, out = stage_slide(kit, did, token, i, of, data, kind)
    arrange._send_json(handler, out, code)


# by name, so a computer whose Python lacks one of these (EDQUOT is not everywhere) still starts
DRIVE_TROUBLE = tuple(getattr(errno, n) for n in ("ENOSPC", "EDQUOT", "EACCES", "EPERM", "EROFS", "ENOENT", "ENOTDIR", "EIO", "ENXIO")
                      if hasattr(errno, n))
HELD_OWN = ("something on this {pc} is holding one of the Assistant's own files for a moment (a sync or backup "
            "program, or the virus checker)")
HELD_OWN_MAYBE = ("something on this {pc} may be holding one of the Assistant's own files for a moment (a sync or "
                  "backup program, or the virus checker); if it stays this way, its folder can't be written to")


def _drive_words(path, e, kind=CAROUSEL):
    """What a page is told when the drive would not take what one of the designer's routes had to write.
    Slides (/design-slide, /design-commit) are pictures in the photographer's own folders: kit.py's words, as the
    slide maker says them. Every other route writes only the Assistant's own hidden records (a design, a
    template, the brand colors, the font list), so on a PC a record another program holds for longer than
    this_computer.replace waits is said as that: there is no picture, and nothing the photographer could close.
    A Mac never refuses that way, and gets kit.py's words for everything, as before."""
    slides = path in ("/design-slide", "/design-commit")
    winerror = getattr(e, "winerror", None) if this_computer.WINDOWS else None      # a Mac: always None
    if not slides and (isinstance(e, this_computer.HeldOpen) or winerror in (5, 32, 33)):   # unproven on a real PC
        why = (HELD_OWN_MAYBE if winerror == 5 else HELD_OWN).format(pc=this_computer.COMPUTER)
    else:
        why = kit_mod._plain_os(e)
    return KW(kind, (DRIVE if slides else CANT_SAVE if path == "/design" else CANT_KEEP).format(why=why))


_STATUS = {"changed": 409, "missing": 400, "busy": 503, "still": 503, "design": 404, "clash": 409, "redo": 409, "drive": 500,
           "photos": 409, "long": 409, "deep": 409}


def _answer_for(res, kind=CAROUSEL):
    if res["state"] in ("done", "already"):
        return 200, {"ok": True, "already": res["state"] == "already", "base": res["base"], "count": res["count"], "words": res["words"]}
    return _STATUS.get(res.get("why"), 500), {"ok": False, "why": res.get("why") or "problem", "words": res.get("words") or KW(kind, NOT_FINISHED)}


def _post_commit(body):
    """Save slides, the last step: every slide has arrived in staging; now the set goes into the Carousel
    folder. The quick answers are given here (this very set is already in; the design has changed; nothing
    new to make; a slide is missing). The moving itself is done by a process of its own (design.py commit),
    because it writes the kit's record, and this waits for it for up to a minute. Safe to send twice."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return 404, {"ok": False, "words": CANT_FIND}
    kind = kind_ok(body.get("kind"))
    if kind is None:
        return 400, {"ok": False, "why": "kind", "words": NOT_UNDERSTOOD}
    lo, hi = K(kind)["slides"]
    did, token, rev, count = body.get("design"), body.get("set"), body.get("rev"), body.get("count")
    if (not isinstance(did, str) or not ID.fullmatch(did) or not isinstance(token, str) or not TOKEN.fullmatch(token)
            or type(rev) is not int or rev < 0 or (count is not None and (type(count) is not int or not lo <= count <= hi))):
        return 400, {"ok": False, "why": "commit", "words": NOT_UNDERSTOOD}
    drawn = None
    if "drawn" in body:                 # what the page drew the slides from: each photo's mark, and fonts that fell back
        drawn = drawn_ok(body.get("drawn"))
        if drawn is None:
            return 400, {"ok": False, "why": "commit", "words": NOT_UNDERSTOOD}
    d = load_design(kit, did, kind)
    if d is None:
        return 404, {"ok": False, "why": "design", "words": NO_DESIGN}
    moving = any(j["state"] == "moving" for j in _journals(kit, kind))
    if not moving:
        mine = _journal(kit, did, token, kind)
        if mine and mine["state"] == "done":
            return _answer_for(_result("done", mine, words=_saved_words(mine, kind)), kind)
        if rev != d["rev"] or (count is not None and count != d["state"]["slides"]):
            return _answer_for(_result("problem", why="changed", words=KW(kind, CHANGED)), kind)
        if drawn is not None and drawn["photos"] != photo_marks(kit, d["state"]):
            return _answer_for(_result("problem", why="photos", words=KW(kind, PHOTO_NEWER)), kind)
        last = last_done(kit, did, kind)
        if last and _same_as(kit, d, last, drawn, kind):
            if _is_shown(kit, last, kind=kind):
                return _answer_for(_result("already", last, words=KW(kind, ALREADY.format(base=last["base"]))), kind)
            # already saved, but the kit is showing other slides as its carousel: the commit below makes
            # this set the one shown again (it writes the kit's record, so it is a process of its own)
        elif not staged_ok(kit, did, token, d["state"]["slides"], kind):
            return _answer_for(_result("problem", why="missing", words=KW(kind, MISSING)), kind)
        else:
            cant = cant_save(kit, d["name"], kind=kind)     # a PC only (the commit asks again, with the name it chooses)
            if cant:
                return _answer_for(_result("problem", why=cant[0], words=cant[1]), kind)
    cmd = [sys.executable, str(HERE / "design.py"), "commit", str(kit), "--design", did, "--set", token, "--rev", str(rev)]
    if kind != CAROUSEL:
        cmd += ["--kind", kind]
    if drawn is not None:
        cmd += ["--drawn", json.dumps(drawn)]       # plain ASCII, whatever the names in the design
    # Started the way arrange.py starts its slide job (this_computer.popen_detached). A Mac: start_new_session,
    # exactly as before. A PC: no window (the page server has none of its own, and a command started from it would
    # open a black one for a moment at every Save slides) and a process group of its own; unproven on a real PC.
    try:
        arrange.HOME.mkdir(parents=True, exist_ok=True)
        p = this_computer.popen_detached(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError as e:
        arrange.log(f"the design commit could not be started: {e}")
        return _answer_for(_result("problem", why="drive", words=KW(kind, NOT_FINISHED)), kind)
    try:
        out, _ = p.communicate(timeout=COMMIT_WAIT)
    except subprocess.TimeoutExpired:
        return _answer_for(_result("problem", why="still", words=KW(kind, STILL)), kind)     # it is left to finish; the page asks again
    res = None
    for line in reversed((out or b"").decode("utf-8", "replace").splitlines()):
        if line.startswith("RESULT: "):
            try:
                res = json.loads(line[8:])
            except ValueError:
                res = None
            break
    if not isinstance(res, dict) or res.get("state") not in ("done", "already", "problem"):
        arrange.log(f"design commit for {kit.name} gave no result (exit {p.returncode}): {(out or b'')[-300:]!r}")
        # The command stopped without saying how it went. The record on the drive is what is true: if it says
        # this very set is in, it is in, and saying "couldn't finish" would not be true.
        mine = _journal(kit, did, token, kind)
        if mine and mine["state"] == "done":
            res = _result("done", mine, words=_saved_words(mine, kind))
        else:
            res = _result("problem", why="drive", words=KW(kind, NOT_FINISHED))
    return _answer_for(res, kind)


def handle_post(handler, path, query):
    """Every POST for the designer. Whatever goes wrong, the server answers and stays up."""
    kind = CAROUSEL                     # whose words a drive's trouble is said in (a story's, once that is known)
    try:
        if path == "/design-slide":
            kind = kind_ok(_one(parse_qs(query or "", keep_blank_values=True), "kind")) or CAROUSEL
            return _post_slide(handler, query)
        if path not in POST_PATHS:
            return handler.send_error(404)
        body = _json_body(handler, path, POST_CAP if path in ("/design", "/design-new", "/design-template")
                          else COMMIT_CAP if path == "/design-commit" else SMALL_CAP)
        if body is None:
            return None
        kind = kind_ok(body.get("kind")) or CAROUSEL
        if path == "/design":
            code, out = save_from_page(body)
        elif path == "/design-new":
            code, out = _post_new(body)
        elif path == "/design-template":
            code, out = _post_template(body)
        elif path == "/design-brand":
            code, out = _post_brand(body)
        elif path == "/design-font":
            code, out = add_font(body.get("add"))
        else:
            code, out = _post_commit(body)
        arrange._send_json(handler, out, code)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        if isinstance(e, OSError) and e.errno in DRIVE_TROUBLE and not isinstance(e, (ConnectionError, socket.timeout)):
            # The Assistant was reached; it is the drive that would not take the change (full, locked, unplugged).
            # Said as what it is, with "why": "drive", so the page shows these words and not "trying again".
            arrange.log(f"POST {path} could not write: {e.__class__.__name__}: {str(e)[:200]}")
            words = _drive_words(path, e, kind)
            try:
                arrange._send_json(handler, {"ok": False, "why": "drive", "words": words}, 500)
            except (Exception, SystemExit):  # noqa: BLE001
                pass
            return
        arrange.log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            arrange._send_json(handler, {"ok": False, "words": TRY_AGAIN if isinstance(e, arrange.Busy) else CANT_REACH}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


# ---------- the commands (Claude's; these may stop with a message) ----------

def page_address(kit, did=None, kind=CAROUSEL):
    """The designer's address on the page server, which is started if it isn't running (as arrange.py does)."""
    import home
    u = home.url()
    if not u:
        return None
    base = u.rsplit("/", 1)[0]
    # Never through a proxy (this_computer.open_local, as arrange.page_address): a proxy can't see this computer's
    # own pages, so every try would fail. With no proxy set this is exactly what it was.
    for _ in range(40):                 # a server that is starting over is gone for a moment: wait for it
        try:
            if b"<title>One moment</title>" not in this_computer.open_local(base + "/home", timeout=3).read(700):
                break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.25)
    if kind == STORIES:                 # one stories design a shoot: the page always opens it
        return f"{base}/design.html?kit={quote(kit.name)}&kind={STORIES}"
    return f"{base}/design.html?kit={quote(kit.name)}" + (f"&design={did}" if did else "")


OPEN_NEW_STORIES = "NEW: this shoot had no stories yet. The page opens on Add stories, so they can pick how the first one starts."
OPEN_THEIRS_STORIES = "THEIRS: this shoot's stories were already here. They are as they left them."


def cmd_open(kit, did=None, kind=CAROUSEL):
    listed = arrange.kit_by_name(kit.name)
    if listed is None or listed.resolve() != kit.resolve():
        say(f"STOP: \"{kit.name}\" isn't in {posts.CONTENT_NAME}, so the page can't show it.")
        return 1
    if not arrange.sheet_rows(kit):
        if kit_mod.sheet(kit) != 0 or not arrange.sheet_rows(kit):
            say("STOP: couldn't number this shoot's photos. Are they where the kit says they are?")
            return 1
    got = arrange.make_previews(kit)
    # The four below are arrange.cmd_open's own, word for word, and only ever come from a PC (no Pillow yet, a kit
    # too deep in folders, copies the virus checker kept busy, a full drive). A Mac never gets them.
    if got.get("cant"):
        say(f"STOP: {got['cant']} " + ("Run this again once it is added." if got.get("cant_kind") == "addon"
                                       else "Run this again once that is done."))
        return 1
    deep = too_deep(kit, kind)
    if deep:
        say(f"STOP: {deep}")
        return 1
    if got["missing"] or got["failed"]:
        say(f"({got['missing'] + got['failed']} of {got['of']} photos couldn't be read right now; the page will say so.)")
        if got.get("why"):
            say(f"({got['why']})")
    if got.get("later") and got.get("full"):
        say(f"({got['later']} of {got['of']} photos weren't ready yet: the drive this post kit is on is full. Once "
            "there's some room on it, opening the page again makes them.)")
    elif got.get("later"):
        say(f"({got['later']} of {got['of']} photos weren't ready yet: something on this {this_computer.COMPUTER} kept "
            "their copies busy, most often the virus checker. The page makes them when it opens.)")
    if did is not None and load_design(kit, did, kind) is None:
        say(f"STOP: this shoot has no design with the id {did}. (design.py show lists them.)")
        return 1
    had = count_designs(kit, kind)
    d = load_design(kit, did, kind) if did else ensure_design(kit, kind)
    if d is None:
        say("STOP: couldn't read this shoot's numbered list. Nothing was changed.")
        return 1
    addr = page_address(kit, d["id"], kind)
    if not addr:
        say("STOP: couldn't start the page server.")
        return 2
    if kind == STORIES:
        n = len(d["state"]["blocks"])
        say(f"Opening this shoot's stories, \"{d['name']}\" ({d['state']['slides']} stor{'ies' if d['state']['slides'] != 1 else 'y'}, "
            f"{n} thing{'s' if n != 1 else ''} on them).")
        say(OPEN_NEW_STORIES if not d["state"]["blocks"] else OPEN_THEIRS_STORIES)
        say(addr)
        return 0
    n = count_designs(kit)
    say(f"{n} design{'s' if n != 1 else ''} for this shoot. Opening \"{d['name']}\" ({d['state']['slides']} slides).")
    # which of the two things to tell the photographer (parts/arrange.md): a design made this minute with one
    # photo on each slide, or one they have already worked on
    say(OPEN_NEW if had == 0 and n >= 1 else OPEN_THEIRS)
    say(addr)
    return 0


def cmd_show(kit, kind=CAROUSEL):
    kk = K(kind)
    rec = kit_mod.load_rec(kit)
    say(f"{rec.get('name') or kit.name}  ({kit.name})" + ("  stories" if kind == STORIES else ""))
    designs = list_designs(kit, kind)
    if not designs:
        say("  No designs yet. (design.py open makes the first one.)" if kind == CAROUSEL
            else "  No stories yet. (design.py open --kind stories makes them.)")
    for d in designs:
        frames = [b for b in d["state"]["blocks"] if b.get("type") != "text"]
        texts = len(d["state"]["blocks"]) - len(frames)
        say(f"  {d['id']}  \"{d['name']}\"  {d['state']['slides']} {KW(kind, 'slides')}, {len(frames)} photo frame{'s' if len(frames) != 1 else ''}"
            f" ({sum(1 for b in frames if b.get('n') is None)} empty), {texts} text box{'es' if texts != 1 else ''}; changed {d.get('updated')}, counter {d['rev']}")
    for j in sorted(_journals(kit, kind), key=lambda j: str(j.get("at") or "")):
        what = {"done": "saved", "moving": KW(kind, "NOT FINISHED (the next Save slides, or design.py commit, finishes it)"), "undone": "put back, not saved"}[j["state"]]
        say(f"  {KW(kind, 'Slides')}: \"{j['base']}\", {len(j['files'])} {KW(kind, 'slides')}, from design {j['design']}, {j.get('finished') or j.get('at')}: {what}")
    cs = rec.get(kk["rec_set"])
    if isinstance(cs, dict) and cs.get("kind") == "laid-out":
        say(KW(kind, f"  The newest laid-out set is \"{cs.get('base')}\" ({len(cs.get('files') or [])} slides), in the Carousel folder."))
    held = waiting_sets(kit, kind)
    if held:
        say(KW(kind, f"  {len(held)} unfinished save{'s' if len(held) != 1 else ''} left slides waiting (hidden, never put in the Carousel folder). "
                     f"They clear themselves a day later; design.py tidy clears the ones left alone for an hour now."))
    for w in arrange.waiting():
        if w["kit"] == kit.name and w["piece"] == kk["piece"]:
            say("  Waiting for Claude: " + arrange.waiting_line(w))
    return 0


def cmd_tidy(kit, kind=CAROUSEL):
    """Clear the waiting slides of saves that were never finished and have been left alone for an hour. None
    of them was ever in the Carousel folder; a set that is on its way in is never touched."""
    before = len(waiting_sets(kit, kind))
    got = tidy(kit, STAGING_PRESSED, wait=kit_mod.SLIDES_WAIT, kind=kind)
    if got is None:
        say(KW(kind, "STOP: this shoot's slides are being changed by something else right now. Nothing was cleared. Try again in a moment."))
        return 2
    left = len(waiting_sets(kit, kind))
    say(KW(kind, f"Cleared the waiting slides of {got} unfinished save{'s' if got != 1 else ''} (none had reached the Carousel folder; nothing in it was changed)."
           if got else "Nothing to clear." if not before else "Nothing was old enough to clear."))
    if left:
        say(KW(kind, f"{left} still waiting: started within the last hour, or on the way in. Save slides works again once fewer than {STAGING_MOST} are waiting."))
    return 0


def took_by_name(words, kind=CAROUSEL):
    """Clear the line for Claude by the kit name on the line itself, even when no folder has that name any
    more (the shoot's folder was renamed after its slides were saved). Returns how many were cleared."""
    return arrange.took(words, K(kind)["piece"])


def took_for(kit, kind=CAROUSEL):
    """Clear this kit's line, and any design line left under a name no folder has any more whose shoot is
    this one (the folder was renamed after the save)."""
    piece = K(kind)["piece"]
    n = arrange.took(kit.name, piece)
    try:
        shoot = kit_mod.load_rec(kit).get("name") or kit.name
    except (OSError, ValueError):
        shoot = kit.name
    for w in arrange.waiting():
        if w["piece"] == piece and w["kit"] != kit.name and w.get("name") == shoot and arrange.kit_by_name(w["kit"]) is None:
            n += arrange.took(w["kit"], piece)
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    kinds = dict(choices=list(KINDS), default=CAROUSEL, help="carousel (the default) or stories (the stories designer)")
    o = sub.add_parser("open"); o.add_argument("words"); o.add_argument("--design"); o.add_argument("--kind", **kinds)
    sh = sub.add_parser("show"); sh.add_argument("words"); sh.add_argument("--kind", **kinds)
    c = sub.add_parser("commit"); c.add_argument("words"); c.add_argument("--design", required=True); c.add_argument("--set", required=True)
    c.add_argument("--rev", type=int, help="the design's counter when the slides were drawn; a design changed since is refused")
    c.add_argument("--drawn", help="what the page drew the slides from, as it sent it (the page server passes this on)")
    c.add_argument("--kind", **kinds)
    tk = sub.add_parser("took"); tk.add_argument("words"); tk.add_argument("--kind", **kinds)
    td = sub.add_parser("tidy"); td.add_argument("words"); td.add_argument("--kind", **kinds)
    a = ap.parse_args()
    # A design's or a shoot's name, in any alphabet, never stops a report on a PC. Belt and braces: importing
    # arrange (and posts, fresh, home) has already done this, so taking this line out changes no output.
    this_computer.utf8_output()
    import fresh
    fresh.announce()                       # this folder is where the Assistant's code is now (see fresh.py)

    if a.cmd == "took" and took_by_name(a.words, a.kind):     # the name on the line, whether or not a folder still has it
        say("Cleared.")
        return 0
    kit = kit_mod.find_kit(a.words)
    try:
        if a.cmd == "open":
            return cmd_open(kit, a.design, a.kind)
        if a.cmd == "show":
            return cmd_show(kit, a.kind)
        if a.cmd == "tidy":
            return cmd_tidy(kit, a.kind)
        if a.cmd == "took":
            n = took_for(kit, a.kind)
            say("Cleared." if n else "Nothing was waiting for that one.")
            return 0
        if a.cmd == "commit":
            if not ID.fullmatch(a.design) or not TOKEN.fullmatch(a.set):
                say("STOP: --design and --set are the ids the page uses (design.py show lists the designs).")
                return 2
            drawn = None
            if a.drawn is not None:
                try:
                    drawn = drawn_ok(json.loads(a.drawn))
                except ValueError:
                    drawn = None
                if drawn is None:
                    say("STOP: --drawn is not what a page sends.")
                    return 2
            res = commit(kit, a.design, a.set, a.rev, drawn, a.kind)
            if res["state"] == "done":
                say(KW(a.kind, f"Slides: {res['count']} slides are in the Carousel folder, named \"{res['base']}\". Nothing was replaced."))
            elif res["state"] == "already":
                say(KW(a.kind, f"Slides: already saved as \"{res['base']}\". Nothing was changed."))
            else:
                say(KW(a.kind, f"STOP: the slides were not saved ({res.get('why')}). ") + str(res.get('words')))
            say("RESULT: " + json.dumps(res))
            return 0 if res["state"] != "problem" else 1
    except arrange.Busy:
        say("STOP: this shoot's designs are being written by something else right now. Nothing was changed. Try again in a moment.")
        return 2
    except OSError as e:
        say(f"STOP: {kit_mod._plain_os(e)}. Nothing was lost. Run this again once that is put right.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
