#!/usr/bin/env python3
"""The reel page: Nicole's reel maker (handoff v19, pages/reel-maker.html), as the Assistant's own page.

    python3 reel_page.py open "beach"      get the page ready (the numbered list, the small copies) and print its address
    python3 reel_page.py show "beach"      what the page has saved: whose order, the order, the song and vibe picked
    python3 reel_page.py make "beach" [--capcut-song "<name>"] [--hook "..."] [--name "..."] [--no-song] [--dry-run]
                                      [--variation N] [--song-start S]
                                           Claude's own Make my reel, for what the page doesn't do (a song from
                                           CapCut's music, words on the first photo, a second take under another
                                           name) or when the page said "Ask your assistant to make the reel instead":
                                           the page's order, song and vibe, made exactly as the page makes it
                                           (--variation and --song-start: the mix and the part of the song, as the
                                           watch step names them; without them, the next mix and the song's own start)
    python3 reel_page.py direct "beach" [--reel "<reel>"] [--style first|reveal|backforth|bookends] [--clips <ids...>]
                                        [--order "7+,2,11-,4"]
                                           "Edit my reel for <shoot>, and follow my direction" (her v27): after reading
                                           their direction (show prints it), set the style, the clips in play order
                                           and the photos' order for that reel in one go; the page follows by itself
    python3 reel_page.py reels "beach" [--new [--name N] | --open "<reel>" | --rename "<reel>" --to "<name>"]
                                           the shoot's reels (her v25: several reels from one shoot), and the page's
                                           own three moves from the chat; show and make take --reel "<reel>"
    python3 reel_page.py note "beach" [--reel "<reel>"]
                                           before picking a reel's photos (her v25: nothing is picked until they
                                           ask): which reel the pick is for, and their note for it, word for word
    python3 reel_page.py job "<kit>" --id <id>   (the page server's own) make the reel a page asked for

The photographer sees her page: her words (WORDS below, word for word from her reel-maker.html and server.py),
her steps in her order, her buttons and what they do. Underneath it is built the Assistant's way:

  * The page names a kit only by its folder name and a photo only by its number on the kit's numbered list
    (.kit/sheet.json, reel.py's own numbering). No route takes a path or a file name, and no answer has one.
  * Nothing is loaded from the internet: the fonts are the plugin's own (shared/fonts, through /look-font, look.py), the
    drag is our own pointer drag (arrange_page.DRAG_JS; no SortableJS, no browser drag-and-drop).
  * Nothing is kept in the browser: every choice is saved to the kit by POST /reel-save, retried until it lands.
  * kit.json is only ever read here (Claude's order is picks.reel there, with reel_marks); commands write it.
  * Nothing is deleted or written over: the record is written whole, with the version before kept beside it.
  * Which reel do you want to create? (her v27, Nov 16): with no kind in its address the page is a chooser of
    four kinds (KIND_WORDS, chooser_html), and each kind is its own page (page_html with the kind): behind the
    scenes (bts), just photos (photos), B-roll (broll), their titles, ledes and steps written on the server. The
    Talking to camera card is a plain link to the talking reel's own page for the same shoot (talk_card;
    talking_page.py): it saves nothing. A reel remembers its kind (saved.kind), so it reopens as its kind
    whatever the address says; a reel from before v27 goes by its footage setting (reel_kind).

Routes, all on the posting server (posting_queue.py hands them here):
  GET  /reel.html?kit=<folder>   the page
  GET  /reel-state?kit=<folder>  everything the page draws from: the photos (numbers and sizes only), Claude's
                                 order, what was saved, the record's counter
  POST /reel-save                {kit, stamp, base, page, saved: {...}}: the page's choices, checked field by field
  GET  /reel-font?f=<name>       one of the plugin's own font files (FACES)
  GET  /reel-songs?kit=<folder>  step 3: the songs in the shoot's Music and Photos folders, {id, name, where, kind}
  POST /reel-open                {kit, what: "music" | "footage" | "photos" | "reels"}: makes <kit>/Music (or Footage) if it isn't
                                 there and opens it (finder.py); "photos" (her v27 + Add photos) opens the shoot's Photos
                                 folder as it is. New photos there are numbered on the page's own poll (relist_if_changed)
  GET  /reel-song?kit=&id=       her v27 Listen: the song to play, by id (a recording's sound, made once), in pieces
  POST /reel-make                {kit, stamp, picks, song, vibe, test}: Make my reel; answers with a job to ask after
  GET  /reel-job?kit=&id=        how that job is going: queued, running, done (her lines) or problem (her words)
  POST /reel-version             {kit, op: new | switch | rename, id, name}: her "Your reels" bar (v25): start a new
                                 reel, work on another, rename one. /reel-save, /reel-make and /reel-moment may
                                 carry "reel", the reel the page is showing: when that is no longer the one being
                                 worked on, nothing is written and the page is given the newest
  POST /reel-capcut              {kit, from?}: Open CapCut (capcut.py's own open), in her words (capcut.OPEN_WORDS);
                                 "from": "kit" is the post kit's Reel card (her "Open in CapCut" button)
  POST /reel-song-remove         {kit, song: id}: her Remove this song (v27, two taps): the song, and every sound
                                 taken from a recording, go to the computer's own Trash (this_computer.trash_many;
                                 the Recycle Bin on a PC), never a delete; the open reel's pick is cleared. Only a
                                 song in the shoot's own Music folder can go (remove_song)
  POST /reel-preview             the watch step (her v27): a dry run's pieces, nothing made (preview_from_page)
  POST /reel-video               {kit, stamp, song, clips, variation, song_start, onscreen, reel}: her v27 Save my video
                                 (B-roll only): a job, followed on /reel-job, that renders the finished MP4 with the
                                 song and the words through video.render_broll into <shoot>/Reels under a free name,
                                 never over a file ("<short> B-roll.mp4", " - <reel name>" with several reels, " 2"
                                 and on); the made entry carries the file's name (save_video_from_page, _make_video).
                                 /reel-open what "reels" is her Open the folder. A PC answers this_computer.NO_VIDEO_PC
Small copies of the photos are arrange.py's (/kit-photo, .kit/previews), the same the pickers use.

Records:
  <kit>/.kit/reel-page.json       {"v": 1, "rev": the counter (only this file moves it on, by one for every accepted
                                  save), "from": {page, base} of the last save, "stamp": the numbered list it was saved
                                  against, "names": {number: file name} for every number it mentions (so a re-made
                                  list finds the same photos again), "saved": {picks, mine, mine_picks, song, vibe,
                                  footage, style, sel, ask, feel, photo_ask, updated}, and, from the later stages, "moments",
                                  "claude_bts" and "made"; Claude's moments are written only by footage.py moments,
                                  which keeps those of an earlier look in "earlier_looks"}. Her record (BUILD.md section 8), minus her "claude", which
                                  is read from kit.json picks.reel every time.
                                  Several reels (her v25, reels.py): her shape. "versions": [{id, name, data}] and
                                  "current"; the reel being worked on keeps its fields at the top (REEL_KEYS: saved,
                                  moments, claude_bts, and for a reel after the first its own "claude"), the others
                                  wait in their "data"; "made" entries carry "version"; "moments_found" is every clip
                                  found for the shoot. A record with no "versions" is one reel and is written byte
                                  for byte as before. One difference from hers, on purpose: the FIRST reel's pick of
                                  the Assistant's stays in kit.json (picks.reel), where the post kit, the posting
                                  queue and every older kit read it, and which the page server never writes; only a
                                  reel started after it keeps its "claude" here (assistant_pick, set_assistant_pick).
  <kit>/.kit/reel-page.prev.json  the version before, kept whole
  <kit>/.kit/reel-page.lock       held by every writer (this_computer.try_lock, through arrange.locked), never removed
  <kit>/.kit/reel-job.json        Make my reel's newest job: {id, state, ask: {picks, song id, vibe, dry, stamp}, pid,
                                  words, project, problem, short_song}; reel-job.lock is held by its process while it
                                  lives; reel-job-status.json is what reel.py make --status said; .kit/reels holds the
                                  reel's working files (reel.REEL_WORK_IN_KIT)
  "made" in the record            one entry per reel made: {project, picks, vibe, footage, song (its file name),
                                  song_id, when}; the next reel of the same choices is the next mix (her variation)

The defaults Dustin and Nicole may change sit in one place each (PLAN section 2): MAX_PICKS and its line (23),
DRAG_OUT (22), REV_CHECK (21), the WORDS table (9, and every word on the page), STYLE (16), SHORT_SONG_FROM_TOP (8),
SOUND_BESIDE_OUTSIDE (4), PLAN_WORDS (5). Elsewhere: reel.REEL_NAME (6), reel.REEL_WORK_IN_KIT (1),
timing.DEFAULT_PACE (7), capcut.OPEN_WORDS (24), finder.BEHIND_WORDS (25).

Songs and the sound of a screen recording (hers: server.py list_songs, sound_of): a song is named to the page by
an id made from where it is and its file name. A recording's sound is made once with sound.py (afconvert on a Mac,
Media Foundation on a PC) as "<name> sound.m4a" (".wav" on a PC) beside it, or in <kit>/Music when the recording
sits in an export folder outside Your Content; a sound already there is used as it is, never written over.

Her v25, section 5 (Nov 12; stage J of the v26 build). Remove a song, which waited on Nicole, is built from her
v27 (Nov 17, Lane E's E12): POST /reel-song-remove, remove_song below.
  * A short song starts after a glitchy opening (short_song_start): for a song under 40 seconds the reel starts
    after the last silent gap that ends in its first 12 seconds, else at the top. Hers asks ffmpeg's silencedetect
    (-50 dB, 0.3 s); ours measures the same in plain Python on the samples the beat is found on (sound.lead_in).
    The start then lands as every start does: reel.py --song-start, the first 1 of a bar at or after it, on a
    whole frame.
  * A replaced recording gets its sound taken again (sound_for): "<name> sound 2.m4a" beside the first, which is
    never written over; the song list hides them all. Hers goes by the files' times alone (a sound older than its
    recording is stale). Ours keeps, in <kit>/.kit/reel-sounds.json (the version before beside it), which
    recording each sound was taken from: its size, its time and a hash of its first megabyte. Same size and time:
    the same recording. Same size and the same start: the same recording, its time noted afresh. Anything else: a
    different recording, so the next name is looked at, and the first free one is made. A sound with no note
    (made before this, or the note couldn't be written) goes by her rule.

The page is built so the steps still to come slot in where hers has them: SECTIONS keeps her order (1 footage,
2 the order, 3 the song, 4 the style, 5 the vibe), and an empty slot is simply left out; her renumbering counts
only the steps that show. The page's script is a small core (CORE_JS: the record, saving, following) with one
part per step (ORDER_JS is step 2); each later step adds its own part and its own fields to SAVE_FIELDS.

Her v25, sections 4 and 8 (Nov 13; stage I of the v26 build), both on the page only:
  * Trim a clip: each clip card has Trim, which opens her panel (trim_panel(), written above the scripts; TRIM_JS):
    the clip on a loop with its sound, a strip of the video's stills about 8 seconds either side, the kept part
    outlined, a start handle, an end handle, the middle to slide it, arrows of a quarter second, her readout.
    Done is the card's own change (POST /reel-moment, do: update) with the start AND the end: 1 to 15 seconds,
    anything else refused whole, never past the video's ends. Cancel, the x, Escape and a click outside save
    nothing. A PC takes no stills from a video yet, so its timeline has no pictures and one line of ours says so.
  * Select several photos, like Lightroom (ORDER_JS): click, Shift-click, Cmd- or Ctrl-click, Escape; a drag of
    any selected photo moves them all (ReelModel.many); two bars, "N selected", with what can be done to all of
    them. What is selected is the page's own and is never saved; one action on a selection is one save and one
    step of Undo.

Python 3.9, standard library only. Nothing here is Mac-only: the small copies are arrange.py's (sips on a Mac,
pictures.py's Pillow on a PC), the lock is this_computer.try_lock, and the page's words name no Mac thing.
"""
import argparse
import copy
import hashlib
import html
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402
import arrange  # noqa: E402
import kit as kit_mod  # noqa: E402
import reels  # noqa: E402
import brand  # noqa: E402
import look  # noqa: E402

this_computer.utf8_output()

# ---------- the defaults, each in one place (PLAN section 2) ----------
KIT_OPEN_CAPCUT = "Open in CapCut"   # her post kit's button (pages/post-kit.html); the reel page's is WORDS["open_capcut"]
MAX_PICKS = 40          # decision 23: her server keeps 40 (and quietly drops the rest); ours says so
DRAG_OUT = False        # decision 22: hers. Only the x or a tap below takes a photo out, never a drag down
REV_CHECK = True        # decision 21: two windows on one reel page: a save from a page that hadn't seen the newest is refused
UNDO_STEPS = 60         # hers
SAVE_AFTER_MS = 500     # hers: a change is saved half a second after the last one
FOLLOW_MS = 4000        # how often an open page asks for a fresh pick from Claude (hers looks every 4 s)
SHORT_SONG_FROM_TOP = 40  # decision 8: a song shorter than this (seconds) starts at the top (her code), not where it picks up;
                          # since her v25: after the last silent gap in its first 12 seconds, when it has one (short_song_start)
SOUND_BESIDE_OUTSIDE = False   # decision 4: a screen recording in a Photos folder outside Your Content (an export folder
                        # the kit only points to) has its sound made in <kit>/Music, never in their folder. True: beside it
PLAN_WORDS = "nicole"   # decision 5: the Plan line in the result box is hers ("Plan: 14 photos, 15.2 seconds, every cut on
                        # the beat at about 85 beats a minute, starting the song at the top."); "reel": reel.py's longer line
MAKE_LIMIT = 600        # hers: a reel may take ten minutes to make, then it is stopped and the page says so
JOB_GRACE = 30          # seconds past MAKE_LIMIT before a job is told as too long even while its lock is held
SONG_EVERY_MS = 3000    # hers: the song list is looked at again every 3 seconds
JOB_EVERY_MS = 700      # how often the page asks how Make my reel is going (ours: hers waited on one long request)
JOB_BOOT = 20.0         # seconds a job may take to start before "queued" means it never did

# Several reels from one shoot (Nicole's v25, Nov 12; reels.py). Hers: REEL_FIRST, REEL_LIVE.
REEL_FIRST = "Reel 1"                  # hers: a record with no list of reels is this one reel
REEL_WORD = "Reel"                     # hers: a new one is "Reel 2", "Reel 3"...
# What belongs to ONE reel (hers: saved, moments, claude, claude_bts, claude_at; ours beside them: when the moments
# were last changed, the moments Remove took out (Undo's), and the Assistant's earlier picks for that reel).
# Everything else in the record is the shoot's: the counter, the numbered list's stamp and names, "made" (each
# entry says which reel), "moments_found", "earlier_looks".
REEL_KEYS = ("saved", "moments", "moments_at", "claude_bts", "removed", "claude", "claude_earlier", "claude_at")
REEL_LIVE = lambda rec: REEL_KEYS      # noqa: E731
CLAUDE_EARLIER_KEPT = 12               # as kit.py's REEL_EARLIER_KEPT
RECORD = "reel-page.json"
PREV = "reel-page.prev.json"
LOCK = "reel-page.lock"
JOB = "reel-job.json"                 # Make my reel's job: its state, its words, what it was asked (ids and numbers only)
JOB_LOCK = "reel-job.lock"            # held by the job's own process for as long as it lives
JOB_STATUS = "reel-job-status.json"   # what reel.py make says happened (reel.py --status)
MAKE_LOCK = arrange.HOME / "reel-make.lock"   # one reel made at a time on this computer (her MAKE_LOCK)
SONG_EXTS = (".m4a", ".mp3", ".wav", ".aif", ".aiff", ".aac")   # hers
VIDEO_EXTS = (".mov", ".mp4", ".m4v")                           # hers: a screen recording, whose sound is used
SOUND = " sound"                      # hers: the sound of "<name>.mov" is kept as "<name> sound.m4a" (".wav" on a PC)
SOUND_NAME = re.compile(r"(.+) sound(?: (\d{1,2}))?")  # "<name> sound", or "<name> sound 2"... (hers hides any number)
SOUND_SPARES = 98       # "<name> sound 2" to "<name> sound 99": the most made for one recording's name, each beside the
                        # ones before it: after a recording was replaced by a new one of the same name (her v25), or
                        # beside a sound that couldn't be read (ours)
SOUNDS = "reel-sounds.json"           # which recording each sound was taken from (sound_for): names, sizes, times, a hash
SOUNDS_PREV = "reel-sounds.prev.json"
SOUNDS_LOCK = "reel-sounds.lock"
SOUND_HEAD = 1 << 20                  # how much of a recording's start is hashed to tell it from another (1 MB)
SONG_ID = re.compile(r"[0-9a-f]{12}")
JOB_ID = re.compile(r"[0-9a-f]{12}")
HER_KINDS = ("Plan:", "Made", "Wide", "Dry run", "Beats per piece", "Your song is only", "I left out")   # her server.py
SHOWN_MADE = ("Plan", "Your song is only", "I left out")     # her page, after a reel is made (hers lists "Wide" too, but
                                                              # her engine never prints one: see NOT_SHOWN)
NOT_SHOWN = ("Wide",)   # reel.py's "Wide photos zoomed to fill..." line counts by photo NUMBER, which the page never shows
                        # (it shows places in the reel), and her bts_reel.py prints no such line: hers never shows it
LEFT_OUT = ("Your song is only", "I left out")                       # her page shows these in their own box
TEST_OPEN = "ASSISTANT_TEST_OPEN"     # tests only: "front", "behind" or "fail"; no folder is opened, the answer is as if
TEST_CAPCUT = "ASSISTANT_TEST_CAPCUT"  # tests only: set, CapCut is never started and the answer is as if it opened
TEST_LIMIT = "ASSISTANT_TEST_MAKE_LIMIT"   # tests only: a few seconds in place of MAKE_LIMIT (and 2 s of JOB_GRACE)
try:
    if float(os.environ.get(TEST_LIMIT) or 0) > 0:
        MAKE_LIMIT, JOB_GRACE = float(os.environ[TEST_LIMIT]), 2
except ValueError:
    pass
POST_CAP = 65536
VIBES = ("beat", "mixed", "calm", "build")           # hers
STYLES = ("first", "reveal", "backforth", "bookends")  # hers
BROLL_STYLE = "broll"                                  # hers (v27): a B-roll reel's one style, clips only, no photos
MOMENT_ID = re.compile(r"[mu][0-9]{1,4}-[0-9a-f]{6}")  # hers: m<k>-<6 hex> (Claude's), u<k>-<6 hex> (theirs)
# step 1, the footage (stage b2 and b3)
FOOTAGE = "Footage"                    # hers: <shoot>/Footage, the behind-the-scenes videos they drag in
NOT_IN_TALKING = "That video isn't in this shoot's Talking folder."    # hers (talking_core.start), v23
FOOT_WORK = "footage"                  # ours: <kit>/.kit/footage holds the stills, the small copies and their states
FOOT_EVERY_MS = 4000                   # hers: the page looks at the Footage folder every 4 seconds
STRIP_EVERY = 2.0                      # hers: a still every 2 seconds under the player
USE_SECONDS = 4.0                      # hers: Use this moment adds a 4-second moment
PREVIEW_WAIT = 3600                    # ours: seconds the preview worker waits for this computer's one video turn
MOMENT_WAIT = 2                        # ours: a Use this moment press waits this long for it, then leaves the
                                       # card's still to the preview worker (the press never waits on a long copy)
COMING_RECENT = 120                    # ours: a video cut off at its end and changed this recently is still being
                                       # copied into Footage: left alone until it is whole (v19 review, Nov 7)
MOMENT_STEP = 0.5                      # hers: − and + change the end by half a second
MOMENT_MIN, MOMENT_MAX = 1.0, 15.0     # hers: a moment's length is kept 1 to 15 seconds and inside its video
ADD_MIN, ADD_MAX = 1.0, 15.0           # hers (v27): a clip made on the editor's timeline is 1 to 15 seconds (v19: 1 to 8)
# The footage editor (her v27, section 3): one player, one timeline, the trim on it. Ours, where hers had two:
ZOOM_OVER = 60.0                       # a video longer than this zooms the timeline in on Start here and on a picked clip
ZOOM_WINDOW = 40.0                     # ...to about 40 seconds (hers: 40 s on Start here for a video over 60 s, and on a
                                       # picked clip only over 90 s: one threshold here, for Nicole)
TAP_PX = 4                             # hers: under 4 px of travel a press on a clip is a click (picks it); more only scrubs
TRIM_PANEL = False                     # her v25 Trim panel (TRIM_WORDS, trim_panel, TRIM_JS): since her v27 the trim lives on
                                       # the editor's timeline and nothing on her page opens the panel. True puts it back as
                                       # a Trim button in a picked clip's box (a question for Nicole)
MAX_CLIPS = 12                         # hers: a style uses at most 12 clips (Moment first 1, Bookends 2)
# Watch your reel before you make it (her v27): the plan from a dry run of reel.py, played on the page
PREVIEW_LIMIT = 30                     # ours: a dry run for the preview is held to this many seconds, then her "couldn't" line
PREVIEW_WORK = "reel-preview"          # ours: <kit>/.kit/reel-preview, the preview's own working folder, never Make my reel's
PREVIEW_AFTER_MS = 700                 # hers: every change on the page refreshes the preview after 700 ms
VIDEO_WORK = "reel-video"              # hers (where="reel-video"): the video job's own working folder, <kit>/.kit/reel-video,
                                       # never the preview's and never Make my reel's
VIDEO_LIMIT = 900                      # ours: Save my video may take 15 minutes, then it is stopped and the page says so
                                       # (hers waited on one request for up to 30)
REELS = "Reels"                        # hers: <shoot>/Reels, where the finished video goes
VIDEO_NAME_SPARES = 998                # "<short> B-roll 2" to "... 999": the most a shoot's Reels folder takes before it says so
PV_UNDO = 40                           # hers: Undo and Redo in the watch step keep 40 steps
PART_MIN = 8.0                         # hers: Another part of this song moves on by max(8 s, 0.6 of the reel's length)...
PART_SHARE = 0.6
PART_END = 1.0                         # ...and goes back to the top once the reel would run past the song's end, less this
MIX_MOST = 999                         # ours: Try another mix counts up to here
DIRECT_MAX = 800                       # hers: "Would you like to direct this edit?", the box's length
ONSCREEN_TEXT_MAX = 300                # hers: B-roll's words on screen
OS_FONTS = ("avenir", "helvetica", "georgia")             # hers: the fonts the words may use
OS_STYLES = ("white", "black", "whitebox", "blackbox")    # hers: White text, Black text, White text on black, Black text on white
OS_X = (0.12, 0.88)                    # hers: where the middle of the words may sit, as a share of the screen...
OS_Y = (0.05, 0.95)
OS_SIZE = (0.5, 2.6)                   # ...and how big, as a share of her 66 px on a 1080 px reel
STYLE_MAX = {"first": 1, "reveal": 12, "backforth": 12, "bookends": 2, "broll": 12}     # hers: STYLE_PICK (broll since v27)
FEELS = ("heartwarming", "nostalgic", "fun", "dreamy")                     # hers: FEEL_WORDS
UNDO_NOTE_MS = 10000                   # hers: the Undo after Remove shows for 10 seconds
KEY = re.compile(r"[0-9a-f]{12}")      # a video's key (video.key: from its name, size and time, never its place)
PAGE_ID = arrange.PAGE_ID
FONT_DIR = HERE.parent.parent.parent / "shared" / "fonts"
# (family, weight, style, the file in shared/fonts without its .ttf): her page asks Google for DM Sans 400, 500
# and 600 and for Fraunces; these are the plugin's own, so the page works with no internet (decision 16).
FACES = [
    ("DM Sans", 400, "normal", "DMSans-Regular"),
    ("DM Sans", 500, "normal", "DMSans-Medium"),
    ("DM Sans", 600, "normal", "DMSans-SemiBold"),
    ("Fraunces", 400, "normal", "Fraunces-Regular"),
    ("Fraunces", 400, "italic", "Fraunces-Italic"),
]
FACE_FILES = tuple(f[3] for f in FACES)       # the only names /reel-font answers to

GET_PATHS = ("/reel.html", "/reel-state", "/reel-font", "/reel-job", "/reel-songs", "/reel-footage", "/reel-video",
             "/reel-strip", "/reel-moment-still", "/reel-song")
POST_PATHS = ("/reel-save", "/reel-open", "/reel-make", "/reel-capcut", "/reel-moment", "/reel-version", "/reel-song-remove",
              "/reel-preview", "/reel-video")

# ---------- the words: hers, word for word (reel-maker.html and server.py, handoff v19) ----------
# Each is shown exactly as written here. "_html" words carry her own <b>; {short}, {n}, {k}, {max} are filled in.
# The words for the steps still to come are here already, so every word on the page lives in this one table.
# The few lines that are ours, not hers, are in OUR_WORDS below, each with its reason.
WORDS = {
    # the top of the page
    "page_title": "Make my reel",
    "back_kit": "Back to the post kit",
    "eyebrow": "Reel",
    "h1": "Your reel",
    "lede_html": "A few quick steps, then press <b>Make my reel</b> and it's cut on the beat in CapCut, ready for your look.",
    "reach": "I can't reach this shoot right now. Check that the photo drive is plugged in, then reload.",

    # step 1 (stage b): behind-the-scenes footage. Since her v27 (Nov 17) the kind of reel is chosen on the chooser
    # (KIND_WORDS), so her old "Behind-the-scenes footage?" yes/no and its three cards are gone; the step's heading
    # is her v27 one
    "foot_h2": "Choose your behind-the-scenes footage",
    "foot_say2_html": "Press <b>Add my footage</b> and a Footage folder for this shoot opens in Finder. Drag your behind-the-scenes videos into it.",
    "add_footage": "▶ Add my footage",
    "opening_footage": "Opening your Footage folder in Finder...",
    "footage_open": "Your Footage folder is open in Finder. Drag your videos in, and they will show up here by themselves.",
    "insight_b": "Good to know: longer footage takes longer",
    "insight_words": "Longer videos take me longer to look through and use more of your plan. A few minutes of footage takes a few minutes. A 20-minute video takes about 10 minutes or more.",
    "insight_added": "You've added {total} of footage. That takes me {est} to look through, and longer footage uses more of your plan.",
    "insight_trim": " Trimming it first will make it quicker.",
    "est_1": "about a minute or two",             # her thresholds: up to 3 minutes of footage
    "est_2": "about 3 to 5 minutes",             # up to 10
    "est_3": "about 8 to 12 minutes",            # up to 25
    "est_4": "about 15 minutes or more",         # longer (and past 15 minutes, the trim line too)
    "quick_fix_html": "<b>Quick fix:</b> trim it first and keep just the parts you like. On your iPhone, open the video in Photos, tap Edit, and drag the ends of the timeline in. On a Mac, open it in QuickTime Player and choose Edit › Trim. A few short clips are quicker for me than one long video.",
    "paste_say": "Then, once your footage is in, copy this into the chat so I can look through it:",
    "paste_plain": "Look through my footage",
    "paste_for": "Look through my footage for {short}",
    "paste_notes": " and follow my notes",
    "copy": "Copy",
    "copied": "Copied",
    # her v27 (Nov 17): the box asks for moments to look for (how the reel should go is step 4's, "Would you like to
    # direct this edit?"), and sits before the line to copy
    "ask_label_html": "<b>Is there anything specific you'd like your assistant to look for?</b> Optional. Certain moments from the shoot, something funny you remember, or a special moment you'd love to have as a clip to choose from.",
    "ask_ex1": "For example: “Find the first kiss.” or “Find the part where the baby grabs the camera strap.”",
    "ask_ex2": "Another example: “Find the footage of me walking into the frame with my camera.”",
    "ask_placeholder": "Optional: the moments you'd like me to look for",
    "feel_b": "How should it feel?",
    "feel_heartwarming": "Heartwarming",
    "feel_nostalgic": "Nostalgic",
    "feel_fun": "Fun",
    "feel_dreamy": "Dreamy",
    "feel_own": "Something else",
    "feel_placeholder": "Your words, like joyful or cozy",
    "feel_small_html": "Optional. Pick one, or tap <b>Something else</b> and type your own. I'll pick the photos and moments that bring out that feeling. Tap it again to clear it.",
    "clips_h3": "Select your clips",
    "moments_first": "The moments I find will show up here.",
    "moments_none": "The moments I find, and any you pick yourself below, show up here.",
    "n_found": "{n} I found",
    "n_yours": "{n} you picked",
    "n_and": " and ",
    "moments_tail": "Press ▶ to preview one, use − and + to make it shorter or longer, or Remove it.",
    "pick_first": "Select the clip that opens your reel.",
    "pick_reveal": "Select the moments where you took one of your photos; each one is followed by that photo.",
    "pick_backforth": "Select the clips to go between your photos, a couple of photos after each. Two is usually plenty. They play in the order shown.",
    "pick_bookends": "Select two clips: the first one shown opens your reel and the second closes it.",
    "style_full": "This style uses {max} clips. Unselect one first, then select the one you want.",
    "badge_opens": "Opens",
    "badge_closes": "Closes",
    "badge_clip": "Clip {k}",
    "no_match": "No matching photo",
    "selected": "✓ Selected",
    "select": "Select",
    "preview_moment": "Preview this moment",
    "your_pick": "Your pick",
    "a_moment": "A moment",
    "span": "{a} to {b}",
    "shorter": "Shorter",
    "shorter_label": "Make it shorter",
    "longer_label": "Make it longer",
    "remove": "Remove",
    "removed": "Removed “{label}”.",
    "that_moment": "that moment",
    "undo_b": "Undo",
    "watch_h3": "Watch your footage and pick your own",
    "watch_say_html": "Play it here, or tap a still to jump there. When you see a part you love, press <b>Use this moment</b>. It shows up first in your clips, 4 seconds long and selected. Use <b>−</b> and <b>+</b> on its card to make it shorter or longer.",
    # her v27 (Nov 17): the videos fold into one drop-down, which opens to the cards
    "vids_one": "1 video added",
    "vids_n": "{n} videos added",
    "vids_total": "{total} of footage",
    "vids_ready": " · all ready to watch below",
    "vids_getting": " · getting {n} ready",
    "vid_ready": "ready to watch below",
    "vid_added": "added",
    "vid_getting_it": "getting it ready",
    "vid_lowspace": "Your photo drive is nearly full, so I didn't make a preview of this one. The moments and your reel still work; you just can't watch it here.",
    "vid_failed": "I couldn't make a preview of this one. The moments and your reel still work; you just can't watch it here.",
    "vid_getting": "Getting {name} ready so you can watch it here. This happens once.",
    "vid_tap": "{length} · tap a still to jump there",
    "mb": "{n} MB",
    "use_moment": "+ Use this moment",
    "starts_at": "Starts at {t} · 4 seconds",
    "added_at": "Added and selected: {t}. Use − and + on its card above to change the length.",
    "didnt_work": "That didn't work.",
    "no_server_short": "I couldn't reach the page server.",
    "sum_clip": " + {n} clip{s}",
    "clips_need_h3": "One more thing: your clips",
    "clips_need_html": "Select the clip or clips to use under <b>Select your clips</b> in step 1, or choose <b>Just photos</b>.",
    "not_looked_h3": "I haven't looked through your footage yet",
    "not_looked_html": "Add your videos in step 1, then copy the line into the chat. The moments I find show up under <b>Select your clips</b> in step 1. Or choose <b>Just photos</b>.",
    # her server.py, for the moments ({_} is only where her own line breaks in two in her server.py: it adds nothing)
    "your_pick_at": "Your pick at {t}",
    "moment_gone": "That moment isn't there anymore. Reload the page.",
    "video_not_here": "That video isn't in this shoot's Footage folder.",
    "cant_put_back": "That moment can't be put back.",
    "no_moments": "There are no footage moments to use yet. Add your footage, copy the line into the chat, {_}and the moments your assistant finds will show up here. Or choose Just photos.",
    "select_clips": "Select the clip or clips to use for this style.",
    "pick_style": "Pick how the footage goes in.",
    "reveal_none": "The reveal needs footage moments that match one of your final photos, and none of these do. {_}Try Moment first or Back and forth.",
    "photo_not_here": "Photo {n} isn't in this shoot.",

    # step 2: put your photos in order
    "order_h2": "Choose your photos",                      # her v27 (Nov 17; v19: "Put your photos in order")
    "order_say": "What order would you like your photos in? Your assistant can choose them and their order for you, or you can drag them in yourself. Whichever you pick, the other one is kept, so you can switch back and forth to compare.",
    # her v27: + Add photos opens the shoot's Photos folder; the page notices new photos and offers to show them
    "add_photos": "+ Add photos",
    "add_photos_say": "Opens this shoot's Photos folder in Finder. Drag in more finished photos and they show up here.",
    "new_photo": "{k} new photo in.",
    "new_photos": "{k} new photos in.",
    "show_new": "Show my new photos",
    "opening_photos": "Opening your Photos folder in Finder...",
    "photos_open": "Your Photos folder is open in Finder. Drag your finished photos in, and I'll show them here.",
    "cant_open_photos": "Could not open the folder. Is the photo drive plugged in?",
    "claude_b": "Let my assistant choose",
    "claude_rec": "Recommended for behind-the-scenes reels",
    "claude_words": "Your assistant picks the strongest photos and orders them so each one flows into the next.",
    "claude_words_bts": "Your assistant picks your strongest photos, the ones with the most feeling and the best story, and fits your behind-the-scenes moments in between.",
    "mine_b": "I'll drag them in myself",
    "mine_words": "Drag any photo to move it, or drag one up from all your photos below. Tap × to take one out.",
    "tip_html": "If there's a photo you really want on screen a little longer, tap <b>Longer</b> under it. If there are ones you'd like to flash by quicker, tap <b>Quicker</b>. Leave the rest alone.",
    "legend_long": "Longer stays on screen about twice as long",
    "legend_quick": "Quicker gets the shortest time, one beat",
    "undo": "↶ Undo",
    "undone": "Undone.",
    "empty": "Your reel is empty. Tap photos below to add them.",       # her CSS shows it in an empty row
    "take_out": "Take it out",
    "take_out_label": "Take photo {n} out",
    "photo_alt": "Photo {n}",
    "longer": "Longer",
    "quicker": "Quicker",
    "one_photo": "{n} photo",
    "photos": "{n} photos",
    "n_longer": " · {k} longer",
    "n_quicker": " · {k} quicker",
    "few": " · 6 or more works best",
    "lots": " · that's a lot for one reel",
    "all_summary": "All your photos (drag one up into your order, or tap to add it and tap again to take it out)",
    "zoom": "See it bigger",

    # step 3 (stage a3): the song
    "song_h2": "Add your song",
    "song_say1": "The music you choose shapes how your reel feels, so pick a song that helps tell your story.",
    "song_say2_html": "Press <b>Add my music</b> and a Music folder for this shoot opens. Drag your song into it. A screen recording of the song playing works fine: I'll take the sound from it and keep it right beside the recording.",
    "add_music": "♫ Add my music",
    "licence_html": "Posting from a business account? Music you didn't license can get your reel muted. The always-safe way: pick <b>No song</b>, make the reel, and add a song from Instagram's own music when you post.",
    # her v27 (Nov 16: "so it doesn't take up so much space"): one drop-down in place of the rows, Listen, and
    # Remove this song (two taps, to the Trash: her v25 section 5, settled by v27; its four page lines and two
    # server lines are below, with the Music folder's, since Lane E's route POST /reel-song-remove says them)
    "song_choose": "Choose a song…",
    "song_rec_tag": " (screen recording)",
    "song_none": "No song, I'll add music in Instagram",
    "song_aria": "Your song",
    "listen": "▶ Listen",
    "stop": "❚❚ Stop",
    "song_off_list": "Take this song off the list",
    "got_it": "Got it: {name}.",
    "opening_music": "Opening your Music folder in Finder...",
    "music_open": "Your Music folder is open in Finder. Drag your song in, and it will show up here by itself.",
    "cant_open": "Could not open the folder. Ask your assistant to open it.",
    # Remove this song (her v27, section 2, step 3: "two taps, to the Trash"; reel-maker.html songRm, built Nov 17,
    # Lane E's E12). The button sits in the song drop-down (Lane A's A8): one tap turns it into song_sure for 4 s,
    # the second sends POST /reel-song-remove; the page then says song_trashed. A PC reads these through
    # trash_words (the Recycle Bin, File Explorer, Restore).
    "song_remove": "Remove this song",
    "song_sure": "Move it to the Trash?",
    "song_removing": "Removing…",
    "song_trashed": "Moved to the Trash. To get it back, open the Trash in Finder and choose Put Back.",
    # her server.py (/music/remove), when it can't
    "song_not_here": "That song isn't in this shoot's folder anymore.",
    "song_cant_trash": "I couldn't move that song to the Trash. Drag it out of the shoot's Music folder in Finder instead.",

    # step 4 (stage b2): the style
    "style_h2": "What style of behind the scenes is this?",
    "style_say": "Pick a style. It uses the clips you selected in step 1. Style and vibe come last so you can try a few versions: change them and press Make my reel again. Every cut still lands on the beat. With a song, the footage plays muted so your song carries the reel; with No song, it keeps its own sound.",
    "style_first_b": "Moment first",
    "style_first_s": "A few seconds of footage opens the reel, then your photos.",
    "style_reveal_b": "The reveal",
    "style_reveal_s": "The moment the photo was taken, then the finished photo. A few times through.",
    "style_backforth_b": "Back and forth",
    "style_backforth_s": "A clip, then a couple of photos, then the next clip, so it feels like being there.",
    "style_bookends_b": "Bookends",
    "style_bookends_s": "Footage opens and closes the reel, with your photos in the middle. Works with any footage.",

    # step 5 (stage a4): the vibe
    "vibe_h2": "Pick the vibe",
    "vibe_say": "How should it move? Every cut lands on the beat, whichever you pick. None of these is a fixed template: the timing is worked out for your song, your photos and your clips, so every reel comes out its own way.",
    "vibe_beat_b": "On every beat",
    "vibe_rec": "Recommended",
    "vibe_beat_s": "Quick and punchy, a new photo on the beat, with a longer hold where the song hits.",
    "vibe_mixed_b": "A little of everything",
    # hers since v25 (Nov 13), when every vibe moved onto the song's real hits (timing.py)
    "vibe_mixed_s": "Some quick, some longer, and every change lands on a beat you can hear in your song.",
    "vibe_calm_b": "Calm",
    "vibe_calm_s": "Longer looks, room to breathe. Best with fewer photos or a longer song.",
    "vibe_build_b": "Build",
    "vibe_build_s": "Starts calm, speeds up toward the end, then lands on the last photo.",

    # the bar at the bottom and the result (stage a4)
    "make": "Make my reel",
    "make_test": "Make my reel (test: nothing is made)",
    "making": "Making your reel...",
    "finding_beat": "Finding the beat and cutting your photos to it. This takes a few seconds.",
    "sum_no_song_yet": "no song picked yet",
    "sum_no_song": "no song",
    "vibe_word_beat": "on every beat",
    "vibe_word_mixed": "a little of everything",
    "vibe_word_calm": "calm",
    "vibe_word_build": "build",
    "need_song_h3": "One more thing: your song",
    "need_song_html": "Add your song under <b>Add your song</b>, or pick <b>No song</b> if you'll add music in Instagram.",
    "short_h3": "Your song is a little short for this",
    "short_more_html": "Add a longer version of the song under <b>Add your song</b>, or take a few photos out.",
    "didnt_work_h3": "That didn't work yet",
    "went_wrong": "Something went wrong.",
    "test_h3": "Test run: nothing was made",
    "in_capcut_h3": "It's in CapCut: {project}",
    "new_reel": "your new reel",
    "open_capcut_say": "Open CapCut, click it at the top of your projects, add your look, and export.",
    "open_capcut": "Open CapCut",
    "no_server": "I couldn't reach the page server. Ask your assistant to make the reel instead.",
    "capcut_opening": "CapCut is opening. Your newest reel is at the top of your projects.",

    # her server.py, when Make my reel can't go ahead
    "pick_photos": "Pick a few photos for the reel first.",
    "pick_vibe": "Pick a vibe first.",
    "song_gone": "That song isn't there anymore. Press Add my music and drag it in again.",
    "no_sound": "I couldn't take the sound out of that recording. Try saving the song as an audio file.",
    "went_wrong_make": "Something went wrong making the reel. Ask your assistant to make it instead.",
    "too_long": "That took too long. Ask your assistant to make the reel instead.",

    # her v27 (Nov 14): straight into the posting queue from here, under Your reels once the reel is made, and in
    # the box after Make my reel. The rhythm is asked once, with her five chips (words_page.RHYTHMS, one copy)
    "toq_btn": "Add this reel to my posting queue",
    "toq_result": "Add it to my posting queue",
    "q_adding": "Adding it…",
    "q_how": "How often do you want to post?",
    "q_how_b": " I'll give each post a date.",
    "q_in": "It's in your posting queue: {label}{going}. Write its caption in your post kit whenever you're ready.",
    "q_going": ", going out {day}",
    "q_already": "It's already in your posting queue{set}.",
    "q_set": ", set for {day}",
    "q_open": "Open my posting queue",
    "q_done": "In your posting queue ✓",
    "q_cant": "I couldn't add it. Try again in a moment.",
    "q_label": "{short} · {name}",                     # hers: the shoot and the reel's name with several reels...
    "q_label_one": "{short} reel",                     # ...the shoot's reel with one

    # her Plan line (bts_reel.py), decision 5: "Plan: 1 clip and 14 photos, 15.2 seconds, every cut on the beat at
    # about 85 beats a minute, starting the song at the top."
    "plan_start": "Plan: ",
    "plan_clip": "{n} clip",
    "plan_clips": "{n} clips",
    "plan_and": " and ",
    "plan_body": ", {secs} seconds, every cut on the beat",
    "plan_tempo": " at about {bpm} beats a minute",
    "plan_top": ", starting the song at the top",
    "plan_in": ", starting the song {s} seconds in",
    "plan_no_song": ", no song",
    "plan_own_sound": " (the footage keeps its own sound).",
}

# Which reel do you want to create? (her v27, Nov 16): with no kind in the address the reel page is a chooser of four
# kinds, and each kind is its own page with its own title and words (her KIND_WORDS). Hers, word for word
# (pages/reel-maker.html, handoff v27); tests/reel_v27_page_check.py compares them with her page both ways.
KINDS = ("bts", "photos", "broll")          # hers: &kind=bts | photos | broll; Talking to camera is its own page
KIND_WORDS = {
    "chooser_h2": "Which reel do you want to create?",
    "chooser_say": "This is where you create the reels for this shoot's post kit. You can make as many as you like, of any kind. Each one is cut on the beat of your song and made in CapCut, ready for your look.",
    "kind_bts_b": "Behind the scenes",
    "kind_bts_s": "Video clips from the shoot, mixed with your finished photos.",
    "kind_photos_b": "Just photos",
    "kind_photos_s": "Your finished photos, cut on the beat.",
    "kind_talk_b": "Talking to camera",
    "kind_talk_s": "You talk about the shoot, and your photos go with what you say.",
    "kind_broll_b": "B-roll",
    "kind_broll_s": "Only video clips from the shoot, cut on the beat. No photos.",
    "chooser_lede": "Pick the kind of reel you want to make. You can come back here and make another one any time.",
    "title_chooser": "{short} reels",
    "title_bts": "{short} behind the scenes",
    "title_photos": "{short} reel",
    "title_broll": "{short} B-roll",
    "lede_bts": "Video clips from your shoot, mixed with your finished photos. Choose your footage and the clips you want, put your photos in order, pick your song, then watch it and make it in CapCut. You can make several: each one keeps its own name under Your reels.",
    "lede_photos": "Your finished photos, cut on the beat of your song. Put your photos in order, pick your song and the pace, then watch it and make it in CapCut. You can make several: each one keeps its own name under Your reels.",
    "lede_broll": "Only video clips from your shoot, cut on the beat of your song, with no photos. Choose your footage and the clips you want, pick your song, then watch it and make it in CapCut. You can make several: each one keeps its own name under Your reels.",
    "all_reels": "← All the reels you can make for this shoot",
}

# Several reels from one shoot (her v25, Nov 12): the "Your reels" bar under the title. Hers, word for word
# (pages/reel-maker.html and server.py ver_op, handoff v25); tests/reels_check.py compares them with her page.
REELS_WORDS = {
    "reels_first": REEL_FIRST,
    "reels_label": "Your reels",
    "reels_which": "Which reel you're working on",
    "reels_new": "+ Start a new reel",
    "reels_rename": "Rename",
    "reels_name": "The reel's name",
    "reels_save": "Save",
    "reels_cancel": "Cancel",
    "reels_starting": "Saving this reel and starting a new one…",
    "reels_opening": "Opening that reel…",
    "reels_reach": "I can't reach the page right now. Check the photo drive is plugged in.",
    "reels_failed": "That didn't work.",
    "reels_no_name": reels.NO_NAME,
    "reels_gone": reels.GONE,
}

# The photographer picks (her v25, section 3: "I choose, not you."): nothing is picked until they ask. A reel with
# no pick of the Assistant's says so; under the two choices is a note box, optional and this reel's own
# (saved.photo_ask), and the line to copy into the chat. Hers, word for word (pages/reel-maker.html, handoff v25);
# tests/picks_ask_check.py compares them with her page.
PICK_WORDS = {
    "not_picked": "Your assistant hasn't picked for this reel yet. Tell it which photos you'd like below, then copy the line into the chat.",
    "photo_ask_b": "Tell your assistant which photos you'd like in this reel",
    "photo_ask_opt": " Optional, and only for this reel.",
    "photo_ask_ex": "For example: “Only the ones in front of the white backdrop.” or “Just the kitchen and the cupcakes.”",
    "photo_ask_placeholder": "Optional: which photos to use, or leave out",
    "photo_then": "Then copy this into the chat, and your assistant picks the photos for this reel:",
    "photo_plain": "Pick my reel photos",
    "photo_for": "Pick my reel photos for {short}",
    "photo_reel": ", {name}",                      # only when the shoot has more than one reel
    "photo_note": ", and follow my note",          # only when there is a note
}
PHOTO_ASK_MAX = 600                                # her box's length, and what her server keeps

# Would you like to direct this edit? (her v27, section 2 step 4): a note on how the reel should go, saved as
# "direct", and the line to copy ("Edit my reel for <shoot>[, <reel name>][, and follow my direction]"). Hers, word
# for word (pages/reel-maker.html, handoff v27); not on a B-roll page.
DIRECT_WORDS = {
    "direct_h2": "Would you like to direct this edit?",
    "direct_say": "Optional. Tell your assistant how you'd like the reel to go, and it puts your clips and photos together that way.",
    "direct_b": "How should this reel go?",
    "direct_ex": "For example: “Start with the video of me shooting the first kiss, then the photos of the first kiss, then into the party after the ceremony.”",
    "direct_placeholder": "Optional: how you'd like the reel to go",
    "direct_then": "Then copy this into the chat, and your assistant edits it your way:",
    "direct_plain": "Edit my reel and follow my direction",   # hers, before the page knows the shoot's name
    "direct_for": "Edit my reel for {short}",
    "direct_reel": ", {name}",                     # only when the shoot has more than one reel
    "direct_note": ", and follow my direction",    # only when there is a note
}

# Watch your reel before you make it (her v27, section 2): a 9:16 player that plays the reel exactly as Make my
# reel will make it, with the song, the pace, the style, Another part of this song, Try another mix, Undo and
# Redo, and Make this one in CapCut. Hers, word for word (pages/reel-maker.html, handoff v27).
WATCH_WORDS = {
    "watch_h2": "Watch your reel before you make it",
    "pv_say_reel_html": "Press play to see it cut on your song, exactly the way <b>Make my reel</b> will make it. Change the song, the pace or the mix here, and it updates. Your look and filters come later, in CapCut.",
    "pv_say_broll_html": "Press play to see it cut on your song. Add your words if you'd like, then press <b>Save my video</b>: it's finished and ready to post, no CapCut needed. Changed something you didn't mean to? <b>Undo</b> takes you back a step.",
    "pv_empty": "Pick your photos below, and your reel shows up here.",
    "pv_working": "Working out the cut…",
    "pv_play": "Play the reel",
    "pv_song": "Song",
    "pv_part": "Another part of this song",
    "pv_pace": "Pace",
    "pv_style": "Behind the scenes",
    "pv_mix": "Try another mix",
    "pv_undo": "↶ Undo",
    "pv_redo": "Redo ↷",
    "pv_undo_title": "Go back to what you had",
    "pv_mix_n": "Mix {n}",
    "pv_pick_song": "Pick a song first.",
    "pv_one_part": "Your song is only {len} seconds and this reel is {n}, so there's only one part of it that fits. A longer song gives you more parts to try.",
    "pv_words_b": "{pace}: {secs} seconds{was}",                               # her line's bold part...
    "pv_words_tail": ", photos about {avg} s each.",                            # ...and the rest
    "pv_was": " ({pace}: {secs} s)",                                           # what the pace before gave
    "pv_marks_quick": "{k} of your {n} photos are set to Quicker",
    "pv_marks_long": "{j} to Longer",
    "pv_marks_and": " and ",
    "pv_marks_tail": ", and those stay that way in every pace, so the paces feel closer together. Clear some of them in step 2 to let the pace decide.",
    "pv_broll_words": "B-roll: {secs} seconds, {n} clip{s}, each cut on the beat.",
    "pv_couldnt": "I couldn't work out the cut just now. Try again in a moment.",
    "pv_cant": "This one can't be cut yet.",
    "pv_make": "Make this one in CapCut",
}

# B-roll: words on screen (her v27, section 4): one line of words over the whole reel, dragged into place on the
# preview, the dot in their corner for the size, a font and a style; and Save my video (A15, its words here as
# she wrote them). Hers, word for word.
ONSCREEN_WORDS = {
    "os_wl": "Words on screen",
    "os_placeholder": "Optional: the words on your reel",
    "os_hint_html": "Your words stay on the whole reel. Drag them on the video to put them anywhere, and drag the dot in their corner to make them bigger or smaller. Want a different font or look? Press <b>Make this one in CapCut</b> and change it there: your words go with it.",
    "os_font": "Font",
    "os_style": "Text style",
    "os_avenir": "Avenir",
    "os_helvetica": "Helvetica",
    "os_georgia": "Georgia",
    "os_white": "White text",
    "os_black": "Black text",
    "os_whitebox": "White text on black",
    "os_blackbox": "Black text on white",
    "os_move": "Drag to move your words",
    "os_size": "Drag to make your words bigger or smaller",
    "os_clips_first": "Choose a clip or two first.",
    "os_save": "Save my video",
    "os_saving": "Saving your video, with your song and words. This takes about a minute.",
    "os_saved": "Saved \"{file}\" ({secs} seconds) in this shoot's Reels folder. It's ready to post.",
    "os_open_folder": "Open the folder",
    "sum_broll": "{n} clip{s} · B-roll",
}

# Save my video, the server's side (her v27 server.py broll_video and broll_video.py): the video's name in the
# shoot's Reels folder, and the one refusal. Hers, word for word; compared with her two files by the test.
VIDEO_WORDS = {
    "file": "{short} B-roll",                  # "<short> B-roll.mp4"
    "file_reel": "{short} B-roll - {reel}",    # "... - <reel name>.mp4" when the shoot has several reels
    "no_clips": "There are no clips in this reel yet.",
}

# Trim a clip (her v25, section 4: "I can't trim it from a specific end."): each clip card has Trim, which opens a
# panel with the clip on a loop, a filmstrip, a start handle and an end handle. Hers, word for word
# (pages/reel-maker.html, handoff v25); tests/reel_trim_select_check.py compares them with her page.
TRIM_WORDS = {
    "trim_btn": "✂ Trim",
    "trim_btn_title": "Trim the start and the end",
    "trim_title": "Your clip",
    "trim_close": "Close",
    "trim_hint": "Drag the left handle to choose where it starts and the right handle to choose where it ends. Drag the middle to slide the whole clip. It plays on a loop as you go.",
    "trim_novid": "The preview of this video is still being made. You can still trim it with the timeline.",
    "trim_start_title": "Where it starts",
    "trim_end_title": "Where it ends",
    "trim_start": "Start",
    "trim_end": "End",
    "trim_earlier": "A quarter second earlier",
    "trim_later": "A quarter second later",
    "trim_play": "▶ Play it again",
    "trim_cancel": "Cancel",
    "trim_done": "Done",
    "trim_say_html": "Starts <b>{a}</b> · ends <b>{b}</b> · <b>{len} s</b>",
    # the line over the clip cards, as her v25 has it (her v19 line had no Trim in it; WORDS keeps that one)
    "moments_tail": "Press ▶ to preview one, use − and + to make it shorter or longer, Trim to pick exactly where it starts and ends, or Remove it.",
}
# The footage editor (her v27, section 3, screenshots 13 to 16: "laid out like a video editor"): one player, the
# Footage drop-down, Make a clip (Start here, End here, + Add clip, Clear), Your clips in two columns, and the
# timeline of stills with the orange trim on it. Hers, word for word (pages/reel-maker.html, handoff v27);
# tests/reel_footage_check.py compares them with her page both ways. The old per-video players, "+ Use this moment",
# the − / + / ✂ Trim / Remove row and "Select your clips" are gone from her page, so they are gone from ours.
EDITOR_WORDS = {
    "ed_h3": "Your footage",
    "ed_say": "Play your footage, or drag along the timeline to find a moment. Then choose the clip or clips you'd like in your reel: use the ones your assistant found, or make your own with Start here and End here.",
    "ed_wait": "Your footage shows up here once it's added.",
    "ed_play": "Play",
    "ed_back": "Back 1 second",
    "ed_back_b": "↶ 1s",
    "ed_fwd": "Forward 1 second",
    "ed_fwd_b": "1s ↷",
    "ed_footage": "Footage",
    "ed_none_b": "No footage yet",
    "ed_none_s": "Press Add my footage above",
    "ed_clip": " · {n} clip",
    "ed_clips": " · {n} clips",
    "ed_videos": " · {n} videos",
    "ed_getting_ready": " · getting ready",
    "ed_make": "Make a clip",
    "ed_in": "⟦ Start here",
    "ed_out": "End here ⟧",
    "ed_add": "+ Add clip",
    "ed_clear": "Clear",
    "ed_find": "Drag along the timeline to find a moment, then press Start here.",
    "ed_started_html": "Your clip starts here. Press play (or drag along the timeline), and press <b>End here</b> where you want it to stop.",
    "ed_sofar_html": "Your clip: <b>{secs} s</b> so far. Press <b>End here</b> where you want it to stop.",
    "ed_set_html": "Your clip: {a} to {b}, <b>{secs} s</b>. Drag its orange ends on the timeline to fine-tune it, then press <b>Add clip</b>.",
    "ed_fifteen": "That's 15 seconds, the longest a clip can be. Drag its ends to change it, or press Add clip.",
    "ed_added": "✓ Added",
    "ed_added_html": "Added to your clips. <b>To make another</b>, drag the orange trim to a new moment (or drag its ends), then press <b>Add clip</b>. Or find a moment and press <b>Start here</b>.",
    "ed_end_after": "The end has to be at least a second after the start.",
    "ed_second": "Make it at least a second long first.",
    "ed_adding": "Adding your clip…",
    "ed_drag": "{a} to {b}, {secs} s",
    "ed_zoom": "Zoom in",
    "ed_whole": "Show the whole video",
    "ed_win": "{video} · {length}",
    "ed_zoomed": "{video} · zoomed in on {a} to {b}",
    "ed_tip": "Drag along the timeline to scrub. Click a clip to pick it, drag its ends to trim it, or drag the middle to slide it.",
    "clips_wl": "Your clips",
    "clips_empty": "Your clips show up here: the moments I find, and the ones you add.",
    "pick_broll": "Choose the clips you'd like in your B-roll reel. They play in the order shown, each cut on the beat.",
    "use": "Use",
    "in_reel": "✓ In reel",
    "use_title": "Use it in your reel",
    "out_title": "Take it out of your reel",
    "no_photo": "No photo",
    "remove_clip": "Remove this clip",
    "play_clip": "▶ Play this clip",
    "edsel": "{a} to {b} · {secs} s. On the timeline, drag its ends to trim it or its middle to slide it.",
    # the photographer's own clips (her v27: a purple YOUR PICK tag and a short name from the chat, A12)
    "not_named": "Not named yet",
    "desc_say": "Want me to name the clips you made? Copy this into the chat:",
    "desc_line": "Name my clips for {short}",
}
TRIM_WINDOW = 16.0      # hers: the filmstrip shows about 8 seconds either side of the clip...
TRIM_SPAN_MIN = 20.0    # ...and never less than 20 seconds of the video (or all of a shorter one)
TRIM_NUDGE = 0.25       # hers: the arrow buttons move an end a quarter second
TRIM_GRID = 0.05        # hers: a handle moves in twentieths of a second

# Select several photos, like Lightroom (her v25, section 8): click, Shift-click, Cmd/Ctrl-click, Escape; a drag of
# any selected photo moves them all; a bar with what can be done to all of them at once. Hers, word for word.
# (The tag on the photos being dragged, "N photos", is in her style rule: SELECT_CSS.)
SELECT_WORDS = {
    "sel_n": "{n} selected.",
    "sel_reel_say": " Drag any of them and they all move together. ",
    "sel_longer": "Longer",
    "sel_quicker": "Quicker",
    "sel_neither": "Neither",
    "sel_out": "Take them out",
    "sel_clear": "Clear",
    "sel_all_say": " Drag any of them up into your order, or ",
    "sel_add": "Add them to the end",
}

# Lines that are ours, not hers, each with why (they go on the "Tell Nicole" list):
OUR_WORDS = {
    # several reels (v25): hers lets two reels share a name; the chat tells them apart by name, so ours does not.
    # And nothing can ever be removed, so there is an end to how many a shoot keeps (hers has none).
    "reels_taken": reels.NAME_TAKEN,
    "reels_most": reels.TOO_MANY,
    # decision 23: her server keeps the first 40 without a word
    "too_many": f"A reel holds up to {MAX_PICKS} photos. Take one out first.",
    # decision 21: only when a second window saved first
    "newer": arrange.NEWER,
    # her page has no Back to home: a kit with no kit page yet gets ours, from every other page
    "back_home": "Back to home",
    # her saves are sent once and forgotten; ours are tried again until they land, and say so only when one didn't
    "retry": "Not saved yet. Trying again...",
    "cant_reach": arrange.CANT_REACH,
    # our numbered list can be re-made under an open page (hers has no such list)
    "photos_changed": arrange.PHOTOS_CHANGED,
    "reload": "Reload",
    # our small copies are made in the background the first time, where hers were made before the page showed
    "getting_ready": "Getting this photo ready...",
    "cant_read": "Can't read this photo right now",
    # decision 25: her "is open in Finder" line, when the folder opened behind the Claude app (finder.BEHIND_WORDS)
    "behind": "",                                  # filled in below, from finder.behind_words()
    # Make my reel runs on its own now, so the page can be told about a second press or a job that was stopped
    "already_making": "Your reel is already being made. One moment.",
    "interrupted": "Making your reel stopped before it finished. Nothing was made. Press Make my reel again.",
    # a job stopped after CapCut had the project but before this page noted it (v19 review): never "nothing was made"
    "interrupted_made": "Making your reel stopped right at the end. It's in CapCut as {project}, but I didn't get to note it here. Open CapCut to see it.",
    # her "at the top of your projects" line is only true when the reel is in CapCut's list (v19 review): on a PC with
    # CapCut open, or when CapCut's list couldn't be saved, it waits until CapCut is closed (capcut.write.waiting)
    "waiting": "CapCut was open, so your reel is waiting to go into its list. {Quit} CapCut, then press Open CapCut and it will be added at the top of your projects.",
    # CapCut's list couldn't be read or saved, and nothing is waiting: what to do if it isn't there
    "not_listed": "Open CapCut. If your reel isn't at the top of your projects, {quit} CapCut and open it again.",
    # decision 26: her trim tip names QuickTime Player, which a PC hasn't got (a draft, for Nicole)
    "trim_pc": "On a PC, open it in the Photos app and choose Trim.",
    # (a PC can't show stills or play a video that needs the small copy yet, video.py's named gap, decision 11:
    # this_computer.NO_PREVIEW and HEVC_HELP come with the video from the server, in place of her "Getting ready";
    # a video that plays as it is plays there, with no strip of stills. The PC's own lines for step 1 are
    # this_computer's NO_LOOK_PC, WATCH_PC_HTML, NOT_LOOKED_PC_HTML and MOMENTS_PC: decision 26, drafts for Nicole)
    # v19 review: a video still being copied into the Footage folder is listed, and waited for, until it is whole
    # (hers read it part way and said it couldn't make a preview)
    # Trim (v25): her one line under the player is for a preview "still being made"; a video whose preview will never
    # come (a failed copy, no room, a PC that can't play it) gets ours, so the panel never promises one
    "trim_stuck": "This video can't be played here. You can still trim it with the timeline.",
    # a PC takes no stills from a video yet (video.py's named gap), so the timeline in the Trim panel has no pictures
    "trim_no_stills_pc": "On a PC the timeline has no pictures along it yet. The handles, the arrows and the times work the same.",
    # the Assistant's own check of a trim (her page can't send one outside 1 to 15 seconds; hers would quietly bend it)
    "trim_length": "A clip is 1 to 15 seconds long.",
    # the footage editor on a PC (v27): no stills are taken from a video there yet (video.py's named gap), so the
    # timeline draws without pictures; the trim, its ends and the times work the same (a draft, for Nicole)
    "editor_no_stills_pc": "On a PC the timeline has no pictures along it yet. The trim, its ends and the times work the same.",
    "coming_small": "still copying in",
    # Remove this song posts to /reel-song-remove (Lane E's route); a page served by an older server that has no
    # such route is told so in plain words, and nothing is moved
    "song_remove_soon": "Remove this song isn't finished yet, so nothing was moved. For now, drag the song out of the shoot's Music folder in Finder yourself.",
    "coming": "{name} is still being copied into your Footage folder. It shows up here when it's done.",
    # Remove this song (v27): hers would send a recording to the Trash from wherever list_songs found it; a
    # recording in the Photos folder is in a folder of theirs (an export folder the kit only points to), so
    # ours leaves it where it is (a draft, for Nicole)
    "song_in_photos_stays": "That one's in your Photos folder, so it stays. Take it out of that folder yourself if you'd like it off the list.",
    # hers stops at the first file that can't be moved, with the ones before it already gone and nothing said;
    # ours says which went, after her line (a draft, for Nicole)
    "song_part_moved": "Already in the Trash: {names}.",
    # Watch your reel (v27): hers took any number as the part of the song to start at; ours refuses one past its end
    "song_start_past": "That part of the song is past its end. Pick another part.",
    # Save my video (B-roll, her v27 section 4): hers makes the video inside one request and the page waits on it;
    # ours runs it as a job the page follows, so a second press and a job that was stopped can be told apart
    "video_making": "Your video is already being saved. One moment.",
    "video_interrupted": "Saving your video stopped before it finished. Nothing was saved. Press Save my video again.",
    "video_too_long": "Saving your video took too long and was stopped. Nothing was saved. Try again, or press Make this one in CapCut.",
    # hers answers any reel; only a B-roll reel is clips only, so only it can be saved whole
    "video_broll_only": "Save my video is for a B-roll reel. For this kind, press Make this one in CapCut.",
    # a file with the chosen name appeared in the Reels folder while the video was being made (never written over)
    "video_name_taken": "A file with that name appeared in the Reels folder just now, so the video was saved under the next number.",
    "video_many": "This shoot's Reels folder already holds {n} B-roll videos. Tidy it, then save again.",
    # her page opens the Reels folder after a save and says nothing; ours says what happened, as every folder button does
    "reels_open": "Your Reels folder is open in Finder.",
    "cant_open_reels": "I couldn't open the Reels folder. It's inside this shoot's post kit folder.",
}

def _behind():
    try:
        import finder
        return finder.behind_words()
    except Exception:  # noqa: BLE001  (the words only)
        return f", behind this window. Click {this_computer.FILES_APP} in {this_computer.APP_BAR} to see it."


OUR_WORDS["behind"] = _behind()


def _capcut_words(key):
    """OUR_WORDS["waiting"] or ["not_listed"] with what you do to make CapCut stop on this computer (quit on a Mac,
    close on a PC: capcut.QUIT)."""
    try:
        quit_ = _reel_module("capcut").QUIT
    except Exception:  # noqa: BLE001  (the words only)
        quit_ = "close" if this_computer.WINDOWS else "quit"
    return OUR_WORDS[key].replace("{Quit}", quit_.capitalize()).replace("{quit}", quit_)


def pc_words(s):
    """Her words name Finder; a PC says File Explorer (decision 26). A Mac: exactly hers."""
    return s.replace("Finder", this_computer.FILES_APP) if this_computer.WINDOWS else s


def trash_words(s):
    """Her Remove this song lines name the Trash and Put Back; a PC says the Recycle Bin and Restore
    (this_computer.TRASH_WORD, TRASH_BACK), and File Explorer for Finder (pc_words). A Mac: exactly hers."""
    if not this_computer.WINDOWS:
        return s
    s = s.replace("open the Trash in Finder and choose Put Back", this_computer.TRASH_BACK)
    return pc_words(s.replace("the Trash", this_computer.TRASH_WORD))


CANT_FIND = WORDS["reach"]
NOT_READY = arrange.NOT_READY
NOT_YET = "This part isn't ready yet."            # the later stages' routes, until they are built
NOT_UNDERSTOOD = arrange.NOT_UNDERSTOOD

_LOCK = threading.RLock()


def say(msg):
    arrange.say(msg)


def short_name(name):
    """Hers (server.py short_name): the folder name without a leading date."""
    return re.sub(r"^\d{4}-\d{2}-\d{2}\s+", "", name) or name


# ---------- the record ----------

def record_path(kit):
    return kit / ".kit" / RECORD


def prev_path(kit):
    return kit / ".kit" / PREV


def lock_path(kit):
    return kit / ".kit" / LOCK


def load(kit):
    try:
        d = json.loads(record_path(kit).read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return d
    except (OSError, ValueError):
        pass
    return {"v": 1}


def _write_bytes_whole(path, data):
    """Bytes written whole or not at all (a scratch name, then a rename), as arrange.write_whole does."""
    arrange.make_folder(path.parent)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_bytes(data)
        this_computer.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def save(kit, rec):
    """Write the record whole, keeping the version before it whole beside it. The caller holds the lock."""
    rec["v"] = 1
    p = record_path(kit)
    try:
        before = p.read_bytes()
    except OSError:
        before = None
    if before is not None:
        _write_bytes_whole(prev_path(kit), before)
    arrange.write_whole(p, rec)


def claude_order(kit, rec_kit=None, on_sheet=None):
    """Claude's photo-only order: kit.json picks.reel with its marks, as her record's "claude": [{n, h}].
    Only numbers on the numbered list."""
    rec_kit = rec_kit if rec_kit is not None else kit_mod.load_rec(kit)
    nums, marks = arrange.kit_pick(rec_kit, "reel")
    out = []
    for n, m in zip(nums, marks):
        if on_sheet is None or n in on_sheet:
            out.append({"n": n, "h": m})
    return out


def _clean_order(lst, on_sheet=None):
    """A list of {n, h} from a record, read for what makes sense: whole numbers, none twice, marks + - or none."""
    out, seen = [], set()
    for x in lst if isinstance(lst, list) else []:
        if isinstance(x, dict) and type(x.get("n")) is int and x["n"] not in seen and (on_sheet is None or x["n"] in on_sheet):
            seen.add(x["n"])
            out.append({"n": x["n"], "h": x.get("h") if x.get("h") in ("+", "-") else ""})
    return out


def _lines_as_orders(got, on_sheet=None):
    out = []
    for text in got if isinstance(got, list) else []:
        if not isinstance(text, str):
            continue
        one = [{"n": int(n), "h": m} for n, m in re.findall(r"(\d+)([+-]?)", text)]
        if on_sheet is not None:
            one = [x for x in one if x["n"] in on_sheet]
        if one:
            out.append(one)
    return out


def assistant_pick(kit, rec, rec_kit=None, on_sheet=None):
    """The Assistant's photo pick for the reel being worked on, as her record's "claude": [{n, h}].
    The shoot's first reel (and a shoot with only one) keeps its pick where it always was, in kit.json
    (claude_order): the post kit, the posting queue and every older kit read it there. Every reel started after
    it keeps its own in this record ("claude", written by kit.py picks --reel through set_assistant_pick), so a
    pick for one reel never changes another's."""
    if reels.current(rec, REEL_FIRST) == reels.FIRST_ID:
        return claude_order(kit, rec_kit, on_sheet)
    return _clean_order(rec.get("claude"), on_sheet)


def assistant_earlier(rec, rec_kit, on_sheet=None):
    """The Assistant's earlier picks for the reel being worked on (earlier_orders, per reel)."""
    if reels.current(rec, REEL_FIRST) == reels.FIRST_ID:
        return earlier_orders(rec_kit, on_sheet)
    return _lines_as_orders(rec.get("claude_earlier"), on_sheet)


def _order_text(lst):
    return ",".join(f"{x['n']}{x.get('h') or ''}" for x in lst or [])


def set_assistant_pick(kit, vid, text):
    """kit.py picks --reel, for a reel that is not the shoot's first: the pick ("19,4,10+,14-") goes into that
    reel only, in this record, under its lock, the version before kept. The pick it replaces is kept
    ("claude_earlier", the last 12, none twice), as kit.json keeps reel_earlier. The same pick again writes
    nothing. Returns (how many photos, the reel's name). Raises ValueError(words) and writes nothing when a
    number is not on the numbered list, the reel is not there, or the pick is the first reel's (kit.json's)."""
    nums, marks = kit_mod.parse_reel(text)
    with arrange.locked(lock_path(kit)):
        rec, rows, stamp = sync(kit)
        if not rows:
            raise ValueError("couldn't read this shoot's numbered list")
        on_sheet = {x["n"] for x in rows}
        bad = [n for n in nums if n not in on_sheet]
        if bad:
            raise ValueError(f"no photo numbered {bad[0]} on the sheet.")
        if len(set(nums)) != len(nums):
            raise ValueError("a photo is in that pick twice.")
        if len(nums) > MAX_PICKS:
            raise ValueError(OUR_WORDS["too_many"])
        if vid == reels.FIRST_ID or vid not in {v["id"] for v in reels.listed(rec, REEL_FIRST)}:
            raise ValueError(reels.GONE)
        name = reels.name_of(rec, vid, REEL_FIRST)
        new = [{"n": n, "h": marks.get(str(n), "")} for n in nums]
        try:
            with reels.turned(rec, vid, REEL_LIVE, REEL_FIRST):
                old = _clean_order(rec.get("claude"))
                if old == new:
                    return len(new), name
                if old:
                    line = _order_text(old)
                    kept = [t for t in (rec.get("claude_earlier") if isinstance(rec.get("claude_earlier"), list) else [])
                            if isinstance(t, str) and t != line]
                    rec["claude_earlier"] = (kept + [line])[-CLAUDE_EARLIER_KEPT:]
                rec["claude"] = new
                rec["claude_at"] = time.time()
        except reels.Wrong as e:
            raise ValueError(str(e))
        rec["rev"] = int(rec.get("rev") or 0) + 1      # an open page on that reel takes the new pick
        rec.pop("from", None)
        _stamp_names(rec, rows, stamp)
        save(kit, rec)
        return len(new), name


def earlier_orders(rec_kit, on_sheet=None):
    """The Assistant's earlier picks for this reel (kit.json "reel_earlier", written by kit.py picks when a new
    pick replaces one), each as [{n, h}], only photos on the numbered list. An order the page shows that is
    still exactly one of these was never touched by the photographer."""
    out = []
    got = (rec_kit or {}).get("reel_earlier")
    for text in got if isinstance(got, list) else []:
        if not isinstance(text, str):
            continue
        one = [{"n": int(n), "h": m} for n, m in re.findall(r"(\d+)([+-]?)", text)]
        if on_sheet is not None:
            one = [x for x in one if x["n"] in on_sheet]
        if one:
            out.append(one)
    return out


def _numbers_in(saved, rec=None):
    """Every photo number ONE reel mentions: the saved orders, and (from the footage stage) Claude's footage
    order and the photos the moments are matched to; for a reel after the first, the Assistant's pick too."""
    out = set()
    for key in ("claude",):
        for x in (rec or {}).get(key) or []:
            if isinstance(x, dict) and type(x.get("n")) is int:
                out.add(x["n"])
    for text in (rec or {}).get("claude_earlier") or []:
        if isinstance(text, str):
            out.update(int(n) for n in re.findall(r"(\d+)[+-]?", text))
    for key in ("picks", "mine_picks"):
        for x in (saved or {}).get(key) or []:
            if isinstance(x, dict) and type(x.get("n")) is int:
                out.add(x["n"])
    for x in (rec or {}).get("claude_bts") or []:
        if isinstance(x, dict) and type(x.get("n")) is int:
            out.add(x["n"])
    for m in (rec or {}).get("moments") or []:
        if isinstance(m, dict) and type(m.get("photo")) is int:
            out.add(m["photo"])
    return out


def _refind(lst, old_names, n_of):
    """A list of {n, h} on a re-made numbered list: every photo found again by its file name. Gone ones drop out."""
    if not isinstance(lst, list):
        return lst
    out, seen = [], set()
    for x in lst:
        if not isinstance(x, dict):
            continue
        nm = old_names.get(str(x.get("n")))
        n = n_of.get(nm) if nm else None
        if n is None or n in seen:
            continue
        seen.add(n)
        out.append({"n": n, "h": x.get("h") if x.get("h") in ("+", "-") else ""})
    return out


def sync(kit):
    """The record, brought in line with the numbered list. Returns (record, rows, stamp); rows is [] when the
    list can't be read right now, and then NOTHING is changed. The caller holds the lock."""
    rec = load(kit)
    rows = arrange.sheet_rows(kit)
    stamp = arrange.sheet_stamp(kit)
    if not rows or not stamp:
        return rec, [], ""
    if rec.get("stamp") and rec.get("stamp") != stamp and (isinstance(rec.get("saved"), dict) or reels.several(rec)):
        # the list was re-made: find each photo again by its file name
        n_of = {}
        for x in rows:
            n_of.setdefault(arrange.photo_name(x), x["n"])
        old = rec.get("names") or {}
        for _vid, d in reels.each(rec, REEL_LIVE, REEL_FIRST):      # every reel of the shoot, the open one first
            s = d.get("saved")
            for key in ("picks", "mine_picks"):
                if isinstance(s, dict) and isinstance(s.get(key), list):
                    s[key] = _refind(s[key], old, n_of)
            for key in ("claude_bts", "claude"):
                if isinstance(d.get(key), list):
                    d[key] = _refind(d[key], old, n_of)
            if isinstance(d.get("claude_earlier"), list):
                d["claude_earlier"] = [t for t in (_order_text(_refind(one, old, n_of)) for one in _lines_as_orders(d["claude_earlier"])) if t]
            for m in d.get("moments") or []:
                if isinstance(m, dict) and type(m.get("photo")) is int:
                    nm = old.get(str(m["photo"]))
                    m["photo"] = n_of.get(nm) if nm else None
        _stamp_names(rec, rows, stamp)
        rec["rev"] = int(rec.get("rev") or 0) + 1
        rec.pop("from", None)
        save(kit, rec)
    return rec, rows, stamp


def _names(saved, name_of, rec=None):
    return {str(n): name_of[n] for n in sorted(_numbers_in(saved, rec)) if n in name_of}


def _stamp_names(rec, rows, stamp):
    """The record's file name for every number it mentions, and the numbered list it is in line with."""
    name_of = {x["n"]: arrange.photo_name(x) for x in rows}
    names = {}
    for _vid, d in reels.each(rec, REEL_LIVE, REEL_FIRST):          # every reel of the shoot
        names.update(_names(d.get("saved") if isinstance(d.get("saved"), dict) else {}, name_of, d))
    rec["names"] = {k: names[k] for k in sorted(names, key=int)}
    rec["stamp"] = stamp


def reel_kind(saved):
    """Which kind of reel a saved record is (her v27: bts | photos | broll), or None when it was never chosen. A
    reel from before v27 (no kind) is bts when footage was on, photos when it was off (the page's own rule)."""
    saved = saved if isinstance(saved, dict) else {}
    k = saved.get("kind")
    if k in KINDS:
        return k
    if saved.get("footage") is True:
        return "bts"
    if saved.get("footage") is False:
        return "photos"
    return None


def kinds_of(rec):
    """{reel id: its kind or None} for every reel of the shoot."""
    return {vid: reel_kind(d.get("saved")) for vid, d in reels.each(rec, REEL_LIVE, REEL_FIRST)}


def as_reel(rec, vid):
    """The record as it would read with reel `vid` open: a copy, to READ (nothing is saved, and which reel is
    being worked on does not change). The record itself when that reel is the open one, or `vid` is None."""
    if vid is None or vid == reels.current(rec, REEL_FIRST):
        return rec
    rec = copy.deepcopy(rec)
    reels.switch(rec, vid, REEL_LIVE, REEL_FIRST)
    return rec


def which_reel(kit, words):
    """For a chat command's --reel: (the reel's id, None), or (None, plain words listing the shoot's reels).
    No words: the reel being worked on."""
    rec = load(kit)
    if not words:
        return reels.current(rec, REEL_FIRST), None
    return reels.find(rec, words, REEL_FIRST)


def reel_names(kit):
    """(the shoot's reels as [{id, name}], the id of the one being worked on)."""
    rec = load(kit)
    return reels.listed(rec, REEL_FIRST), reels.current(rec, REEL_FIRST)


def found_moments(rec):
    """Hers (found_moments): the clips the Assistant found for the shoot, untouched; a new reel starts with all
    of them. "moments_found" is kept by footage.py moments; a record from before it (or with none) gives every
    clip any reel still has that is not the photographer's own, the first one of each id."""
    got = rec.get("moments_found")
    if isinstance(got, list) and got:
        return [m for m in got if isinstance(m, dict)]
    seen, out = set(), []
    for _vid, d in reels.each(rec, REEL_LIVE, REEL_FIRST):
        for m in moments_of(d):
            if m.get("by") != "you" and m["id"] not in seen:
                seen.add(m["id"])
                out.append(m)
    return out


def reel_fresh(rec):
    """Hers (reel_fresh): what a new reel starts with. "I'll drag them in myself" with nothing in it, no
    assistant picks, footage not chosen, no song, every clip found for the shoot, all as found."""
    ms = []
    for m in copy.deepcopy(found_moments(rec)):
        m["keep"] = True
        m.pop("set", None)                    # a length they set in another reel is that reel's
        ms.append(m)
    return {"moments": ms,
            "saved": {"picks": [], "mine": True, "mine_picks": [], "song": None, "vibe": "beat", "footage": None,
                      "style": "first", "ask": "", "feel": "", "sel": {}, "updated": time.time()}}


def start_as(saved, kind):
    """What a reel of this kind starts with (her v27 applyKind, once, when the reel is started: ours never on a
    plain open): its kind, footage on for behind the scenes and B-roll and off for just photos, and B-roll's one
    style."""
    saved["kind"] = kind
    saved["footage"] = kind != "photos"
    if kind == "broll":
        saved["style"] = BROLL_STYLE
    elif saved.get("style") == BROLL_STYLE:
        saved["style"] = "first"


def version_from_page(body):
    """POST /reel-version {kit, op: new | switch | rename, id, name, kind?}: hers (/reel/version). Start a new
    reel, work on another, or rename one. Under the record's lock, written whole with the version before kept;
    the counter moves on, so a page that has not seen it can never save one reel's choices into another.
    `kind` (ours, v27), with "new" only: the new reel is of that kind from the start (the kind of the page it was
    started from). (status, {ok, versions, current, rev, kind} or {ok: False, words}); `kind` is the reel now
    being worked on's, so the page reopens it as its own kind (hers kept the address's)."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    ask = {k: v for k, v in body.items() if k != "kit"}
    kind = ask.pop("kind", None)
    if kind is not None and (kind not in KINDS or ask.get("op") != "new"):
        return _bad()
    with arrange.locked(lock_path(kit)):
        rec, rows, stamp = sync(kit)
        if not rows:
            return _bad(NOT_READY, 404)
        try:
            changed = reels.op(rec, ask, REEL_LIVE, reel_fresh, REEL_FIRST, REEL_WORD)
        except reels.Wrong as e:
            return _bad(str(e) or NOT_UNDERSTOOD)
        if changed and kind and isinstance(rec.get("saved"), dict):
            start_as(rec["saved"], kind)
        if changed:
            rec["rev"] = int(rec.get("rev") or 0) + 1
            rec.pop("from", None)
            _stamp_names(rec, rows, stamp)
            save(kit, rec)
        out = {"ok": True, "rev": int(rec.get("rev") or 0), "kind": reel_kind(rec.get("saved"))}
        out.update(reels.info(rec, REEL_FIRST))
    return 200, out


def state(kit, reel=None):
    """Everything the page draws from. No path and no file name is in it. None when the numbered list can't be
    read right now. `reel` (a chat command naming another reel): that reel's choices, read only."""
    with arrange.locked(lock_path(kit)):
        rec, rows, stamp = sync(kit)
    if not rows:
        return None
    open_reel = reels.current(rec, REEL_FIRST)
    whole = rec
    rec = as_reel(rec, reel)
    rec_kit = kit_mod.load_rec(kit)
    photos, made = arrange.page_photos(kit, rec_kit, rows)
    on_sheet = {x["n"] for x in rows}
    saved = rec.get("saved") if isinstance(rec.get("saved"), dict) else None
    kinds = kinds_of(rec)
    return {
        "ok": True,
        "short": short_name(kit.name),
        # the kit page is built on every request from the kit's record (v19 stage d), so every kit has one
        "kit_page": kit_mod.rec_path(kit).is_file(),
        "stamp": stamp, "rev": int(rec.get("rev") or 0), "total": len(rows),
        "photos": photos, "previews": {"made": made, "of": len(rows)},
        "claude": assistant_pick(kit, rec, rec_kit, on_sheet),
        "claude_earlier": assistant_earlier(rec, rec_kit, on_sheet),
        "saved": _for_page(saved, on_sheet),
        "max": MAX_PICKS,
        "songs": songs_for_page(kit, rec_kit),
        "music": music_dir(kit).is_dir() and music_ok(kit),
        "job": job_for_page(kit),
        # step 1: the moments (their videos by key) and Claude's footage order; the videos themselves come from
        # /reel-footage, which the page asks only once they chose footage (asking starts the previews)
        "moments": moments_for_page(kit, rec, on_sheet),
        "claude_bts": _bts_of(rec, on_sheet),
        # hers (GET /reel): the shoot's reels and which one is being worked on ("on_page": the one the page has,
        # also when a chat command reads another); since v27 each reel's kind too (the page reopens a reel as its
        # own kind), and the open reel's
        "versions": [dict(v, kind=kinds.get(v["id"])) for v in reels.listed(rec, REEL_FIRST)],
        "current": reels.current(rec, REEL_FIRST), "on_page": open_reel,
        "kind": reel_kind(saved),
        # her v27: Add this reel to my posting queue, once the reel is made; the queue's answer for each reel
        "made": {k: bool(v) for k, v in made_projects(whole, rec_kit).items()},
        "queue": queue_for_page(kit, whole),
    }


def _for_page(saved, on_sheet):
    """What was saved, as the page reads it back: her fields only, photos only if they are on the list."""
    if not saved:
        return None
    out = {k: saved.get(k) for k in SAVE_FIELDS if k in saved}
    for key in ("picks", "mine_picks"):
        if isinstance(out.get(key), list):
            out[key] = [x for x in out[key] if x.get("n") in on_sheet]
    return out


def _marked(order):
    return [(x.get("n"), x.get("h") or "") for x in order or []]


def _order_used(saved, claude, earlier=()):
    """The order Make my reel uses, as [{n, h}]: their own when they chose "I'll drag them in myself", otherwise
    Claude's newest, with the Longer / Quicker they set on the same photos (her followClaude). One case more
    (Nov 11): when what is saved is still exactly an earlier pick of the Assistant's, marks and all (`earlier`:
    earlier_orders), the photographer changed nothing, so the newest pick's marks are used. Nicole's own v22 did
    this by hand for her Aurora shoot; without it a kit picked before the fuller marks could never get them."""
    saved = saved or {}
    if saved.get("mine") or (not claude and saved.get("picks")):
        return list(saved.get("picks") or [])
    if isinstance(saved.get("picks"), list) and [x["n"] for x in saved["picks"]] == [x["n"] for x in claude]:
        if _marked(saved["picks"]) != _marked(claude) and any(_marked(saved["picks"]) == _marked(e) for e in earlier or ()):
            return list(claude)
        return list(saved["picks"])
    return list(claude)


def current_picks(kit, reel=None):
    """The order Make my reel uses when it is not handed one by the page, as reel.py reads it ("19,4,10+,14-"):
    their own when they chose "I'll drag them in myself", otherwise Claude's newest, with the Longer / Quicker
    they set on the same photos (her followClaude). "" when there is nothing yet. The reel being worked on,
    or the one named."""
    st = state(kit, reel)
    if st is None:
        return ""
    return ",".join(f"{x['n']}{x.get('h') or ''}" for x in _order_used(st["saved"], st["claude"], st.get("claude_earlier")))


def order_for_kit_page(kit, rows=None, rec_kit=None, reel=None, rec=None):
    """The reel's photos in the order Make my reel would use (_order_used), for the post kit's Reel card (her
    kit_summary's reel_order). Reads only: nothing is saved and no lock is taken, so showing the kit page never
    changes the record. A record saved against an earlier numbered list is read the way sync() would bring it in
    line (each photo found again by its file name), in memory only. [] when the numbered list can't be read.
    `reel` (v25: a shoot with several reels): that reel's own order, whichever reel is open on the page; None is
    the reel being worked on. `rec`: the reel page's record, when the caller has read it already."""
    rows = arrange.sheet_rows(kit) if rows is None else rows
    if not rows:
        return []
    rec = load(kit) if rec is None else rec
    if reel is not None:
        if reel not in {v["id"] for v in reels.listed(rec, REEL_FIRST)}:
            return []
        rec = as_reel(rec, reel)
    saved = rec.get("saved") if isinstance(rec.get("saved"), dict) else None
    stamp = arrange.sheet_stamp(kit)
    if rec.get("stamp") and stamp and rec.get("stamp") != stamp:
        n_of = {}
        for x in rows:
            n_of.setdefault(arrange.photo_name(x), x["n"])
        if saved:
            saved = dict(saved)
            for key in ("picks", "mine_picks"):
                if isinstance(saved.get(key), list):
                    saved[key] = _refind(saved[key], rec.get("names") or {}, n_of)
        if isinstance(rec.get("claude"), list):          # a reel after the first keeps its pick here
            rec = dict(rec, claude=_refind(rec["claude"], rec.get("names") or {}, n_of), claude_earlier=[])
    on_sheet = {x["n"] for x in rows}
    rec_kit = rec_kit if rec_kit is not None else kit_mod.load_rec(kit)
    return _order_used(_for_page(saved, on_sheet), assistant_pick(kit, rec, rec_kit, on_sheet), assistant_earlier(rec, rec_kit, on_sheet))


def _when_of(iso):
    try:
        return datetime.fromisoformat(str(iso)).timestamp()
    except (TypeError, ValueError):
        return 0.0


def made_projects(rec, rec_kit):
    """{reel id: the newest CapCut project made of it, or None} for every reel of the shoot (the rule
    reels_for_kit uses: a "made" entry says whose it is, made_for; a reel made from the chat the older way, in
    kit.json with no entry here, is the first reel's). A made entry that carries a saved video (B-roll, Save my
    video) counts as made too: its project is the video's file name."""
    rec_kit = rec_kit if isinstance(rec_kit, dict) else {}
    last, known = {}, set()
    for m in rec.get("made") or []:
        if not isinstance(m, dict):
            continue
        name = m.get("project") if isinstance(m.get("project"), str) and m.get("project") else None
        name = name or (m.get("video") if isinstance(m.get("video"), str) and m.get("video") else None)
        if name:
            last[made_for(m)] = m
            if m.get("project"):
                known.add(m["project"])
    chat = rec_kit.get("reel") if isinstance(rec_kit.get("reel"), dict) else {}
    chat_project = chat.get("project") if isinstance(chat.get("project"), str) and chat.get("project") else None
    out = {}
    for v in reels.listed(rec, REEL_FIRST):
        m = last.get(v["id"])
        project = (m.get("project") or m.get("video")) if m else None
        if v["id"] == reels.FIRST_ID and chat_project and chat_project not in known:
            try:
                page_when = float(m.get("when") or 0) if m else 0.0
            except (TypeError, ValueError):
                page_when = 0.0
            if not m or _when_of(chat.get("made")) > page_when + 1:
                project = chat_project
        out[v["id"]] = project
    return out


def queue_for_page(kit, rec):
    """Her v27 /queue, read in process (words_page.queue_state, one copy of the queue's rules): whether a
    posting rhythm is set, and each reel's place in the posting queue, {interval, reels: {id: {status, date}},
    url}. Whatever can't be read reads as not in the queue."""
    out = {"interval": False, "reels": {}, "url": "/posting.html"}
    try:
        import words_page
        for v in reels.listed(rec, REEL_FIRST):
            q = words_page.queue_state(kit, "reel", [], version=v["id"])
            out["interval"] = out["interval"] or bool(q.get("interval"))
            out["reels"][v["id"]] = {"status": q.get("status") or "", "date": q.get("date") or ""}
    except Exception as e:  # noqa: BLE001  (the queue's file, not the page's)
        arrange.log(f"reel page: the posting queue couldn't be read for the page: {e.__class__.__name__}: {str(e)[:160]}")
    return out


def newest_project(kit, rec_kit=None):
    """The CapCut project of the newest reel of this kit, or None: the newest made from the reel page (its record's
    "made") or from the chat (kit.json "reel", which the page's own makes write too), whichever was made later.
    Hers (server.py kit_summary) takes the page's first; the chat's is newer only when it was made after it."""
    rec_kit = rec_kit if rec_kit is not None else kit_mod.load_rec(kit)
    made = [m for m in (load(kit).get("made") or []) if isinstance(m, dict) and isinstance(m.get("project"), str) and m["project"]]
    page = made[-1] if made else None
    chat = rec_kit.get("reel") if isinstance(rec_kit.get("reel"), dict) else {}
    if not (isinstance(chat.get("project"), str) and chat["project"]):
        return page["project"] if page else None
    if not page:
        return chat["project"]
    try:
        page_when = float(page.get("when") or 0)
    except (TypeError, ValueError):
        page_when = 0.0
    return chat["project"] if _when_of(chat.get("made")) > page_when + 1 else page["project"]


def reels_for_kit(kit, rows=None, rec_kit=None):
    """Every reel of the shoot, for the post kit and the posting queue (hers: reels_of, v25): [{id, name, made,
    project, kind, video, order}] in the order they were started. `kind` (v27): bts, photos, broll, or None. `made`: a reel of it is in CapCut; `project`: the newest
    one's name; `order`: its photos in the order Make my reel would use, as [{n, h}] (at most 40, hers).
    Whose a made reel is: its "made" entry says (made_for; one without a mark is the first reel's, hers). A reel
    made from the chat the older way (kit.json "reel", with no entry in this record) is the first reel's too.
    Reads only; a record that can't be read gives the one reel it always was."""
    rows = arrange.sheet_rows(kit) if rows is None else rows
    rec = load(kit)
    try:
        rec_kit = rec_kit if rec_kit is not None else kit_mod.load_rec(kit)
    except (OSError, ValueError):
        rec_kit = {}
    if not isinstance(rec_kit, dict):
        rec_kit = {}
    projects = made_projects(rec, rec_kit)
    videos = made_videos(rec)
    kinds = kinds_of(rec)
    out = []
    for v in reels.listed(rec, REEL_FIRST):
        project = projects.get(v["id"])
        try:
            order = order_for_kit_page(kit, rows, rec_kit, reel=v["id"], rec=rec) if rows else []
        except (OSError, ValueError, TypeError, AttributeError, KeyError):
            order = []
        out.append({"id": v["id"], "name": v["name"], "made": bool(project), "project": project,
                    "kind": kinds.get(v["id"]),
                    # her v27 (Save my video): the newest video saved of this reel, its file name in <shoot>/Reels
                    "video": videos.get(v["id"]),
                    "order": [{"n": x["n"], "h": x.get("h") or ""} for x in order][:40]})
    return out


# ---------- checking what a page sends ----------

class Refused(Exception):
    pass


def _picks(v, on_sheet):
    """A list of {n, h}: each n a photo on the list, once; h '' (Normal), '+' (Longer) or '-' (Quicker)."""
    if not isinstance(v, list):
        raise Refused("picks")
    out, seen = [], set()
    for x in v:
        if not isinstance(x, dict) or set(x) - {"n", "h"}:
            raise Refused("picks")
        n, h = x.get("n"), x.get("h", "")
        if type(n) is not int or n not in on_sheet or n in seen or h not in ("", "+", "-") or not isinstance(h, str):
            raise Refused("picks")
        seen.add(n)
        out.append({"n": n, "h": h})
    return out


def _text(v, cap):
    if not isinstance(v, str) or len(v) > cap or "\x00" in v:
        raise Refused("text")
    return v


def _song(v, kit):
    """None (not picked yet), "" (No song), or the id of a song in this shoot right now."""
    if v is None or v == "":
        return v
    if isinstance(v, str) and SONG_ID.fullmatch(v) and v in song_ids(kit):
        return v
    raise Refused("song")


# ---------- step 3: the songs (hers: server.py list_songs and sound_of) ----------

def _reel_module(name):
    """One of the reel scripts (beside these, in assistant-make-a-reel/scripts), loaded without letting them stay at
    the front of Python's search list (posting_queue._capcut's way)."""
    d = str(kit_mod.REEL_PY.parent)
    if d not in sys.path:
        sys.path.append(d)
    saved = list(sys.path)
    try:
        return __import__(name)
    finally:
        sys.path[:] = saved + [x for x in sys.path if x not in saved]


def default_vibe():
    try:
        v = _reel_module("timing").DEFAULT_PACE
        return v if v in VIBES else "beat"
    except Exception:  # noqa: BLE001
        return "beat"


def music_dir(kit):
    return kit / "Music"


def music_ok(kit):
    """Is the shoot's Music folder (if it is there at all) a real folder of the kit's own? A Music folder that is a
    link (or that leads anywhere but inside the kit) is never listed, written into or opened (v19 review: songs
    were listed from wherever it pointed, and a recording's sound was written there, outside Your Content)."""
    d = music_dir(kit)
    try:
        if not os.path.lexists(d):
            return True
        if d.is_symlink() or not d.is_dir():
            return False
        return Path(os.path.realpath(d)).parent == Path(os.path.realpath(kit))
    except OSError:
        return False


def _inside_content(path):
    """Is this file or folder inside Your Content? (Then a sound may be kept beside it, decision 4.)"""
    try:
        import posts
        h = posts.home()
        if not h:
            return False
        content = Path(os.path.realpath(h / posts.CONTENT_NAME))
        return content in Path(os.path.realpath(path)).parents
    except Exception:  # noqa: BLE001
        return False


def song_id(where, name):
    """A song's id: from where it is (Music or Photos) and its file name, never a path, the same on every look."""
    return hashlib.sha1(("%s\0%s" % (where, arrange._nfc(name))).encode("utf-8")).hexdigest()[:12]


def _listing(folder):
    try:
        return [e for e in os.listdir(folder)]
    except OSError:
        return []


def list_songs(kit, rec=None):
    """The songs they put in the shoot's Music folder or its Photos folder, Music first, each folder newest first
    (hers): audio files, and screen recordings whose sound is used. The sound made from a recording is not listed
    on its own (the recording is shown once): beside it, or, for a recording in a Photos folder outside Your
    Content, in the Music folder (decision 4). Links are left out. Each: {id, name, where, kind, path}; the path
    never leaves this computer's own side."""
    rec = rec if rec is not None else kit_mod.load_rec(kit)
    folders = [("Music", music_dir(kit) if music_ok(kit) else None), ("Photos", kit_mod.photos_dir(kit, rec))]
    folders = [(w, d) for w, d in folders if d is not None]
    videos = {}
    for where, d in folders:
        videos[where] = {Path(f).stem.casefold() for f in _listing(d) if f.lower().endswith(VIDEO_EXTS) and not f.startswith(".")}
    outside = not _inside_content(folders[-1][1])
    videos.setdefault("Music", set())
    out = []
    for where, d in folders:
        made_here = set(videos[where])
        if where == "Music" and outside and not SOUND_BESIDE_OUTSIDE:
            made_here |= videos.get("Photos", set())
        found = []
        for f in _listing(d):
            low = f.lower()
            if f.startswith(".") or not low.endswith(SONG_EXTS + VIDEO_EXTS):
                continue
            stem = Path(f).stem
            m = SOUND_NAME.fullmatch(stem)
            if low.endswith((".m4a", ".wav")) and m and m.group(1).casefold() in made_here:
                continue                       # the sound taken from a recording: the recording is shown once
            p = d / f
            try:
                if p.is_symlink() or not p.is_file():
                    continue
                when = p.stat().st_mtime
            except OSError:
                continue
            found.append((-when, f, {"id": song_id(where, f), "name": stem, "where": where,
                                     "kind": "video" if low.endswith(VIDEO_EXTS) else "audio", "path": p}))
        out += [x[2] for x in sorted(found, key=lambda x: (x[0], x[1]))]
    return out


def songs_for_page(kit, rec=None):
    return [{k: s[k] for k in ("id", "name", "where", "kind")} for s in list_songs(kit, rec)]


def song_ids(kit):
    return {s["id"] for s in list_songs(kit)}


def song_by_id(kit, sid, rec=None):
    return next((s for s in list_songs(kit, rec) if s["id"] == sid), None)


def _named(folder, name):
    """The file in folder whose name is this one (capitals aside, as the drive sees it), or None."""
    want = arrange._nfc(name).casefold()
    hit = [e for e in _listing(folder) if arrange._nfc(e).casefold() == want]
    return folder / hit[0] if hit else None


def _sound_ok(p):
    """A sound beside a recording that can be used: a real file, not tiny, whose length can be read and is at least
    half a second (sound.duration reads the file itself). A sound cut off while it was made (by a make from before
    sounds were written under a hidden name first) fails this, and is never used (v19 review)."""
    try:
        if p.is_symlink() or not p.is_file() or p.stat().st_size < 2000:
            return False
        d = _reel_module("sound").duration(p)
        return bool(d) and d >= 0.5
    except Exception:  # noqa: BLE001  (a sound nobody can read is a sound not to use)
        return False


def short_song_start(song, seconds):
    """Where a song starts when it is short (hers: song_lead_in for a song under 40 seconds, v25): after the last
    silent gap that ends in its first 12 seconds, or 0.0, the top. None for a song that is not short (reel.py then
    starts it where it picks up) or whose length nobody could read (hers: 99)."""
    if not seconds or seconds >= SHORT_SONG_FROM_TOP:
        return None
    try:
        t = float(_reel_module("sound").lead_in(song))
    except Exception:  # noqa: BLE001  (a start nobody can measure is the top)
        return 0.0
    return t if 0 < t <= 12 else 0.0


# Which recording a sound was taken from (her v25: a replaced recording gets its sound taken again).

def sounds_path(kit):
    return kit / ".kit" / SOUNDS


def _sounds(kit):
    d = _read_json(sounds_path(kit))
    return d if isinstance(d, dict) and isinstance(d.get("sounds"), dict) else {"v": 1, "sounds": {}}


def _read_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def recording_print(video, head=True):
    """What tells one recording from another of the same name: its size, its time, and (head=True) a hash of its
    first megabyte. The recording is only read. None when it can't be."""
    try:
        st = Path(video).stat()
        out = {"size": st.st_size, "time": st.st_mtime}
        if head:
            with open(video, "rb") as f:
                out["head"] = hashlib.sha256(f.read(SOUND_HEAD)).hexdigest()
        return out
    except OSError:
        return None


def same_recording(note, video):
    """Is this the recording a sound's note was written for? (yes or no, the note to keep: the same one, or the
    same with the recording's new time.) By size, then time, then the hash of its start: read only when the size
    matches and the time does not."""
    if not isinstance(note, dict):
        return False, None
    now = recording_print(video, head=False)
    if now is None or note.get("size") != now["size"]:
        return False, None
    if note.get("time") == now["time"]:
        return True, note
    full = recording_print(video)
    if full is None or not note.get("head") or note.get("head") != full["head"]:
        return False, None
    return True, dict(note, time=full["time"])


def _sound_key(kit, sound):
    """A sound's name in the notes: the folder it is in (Music or Photos, never a path) and its file name."""
    try:
        where = "Music" if Path(os.path.realpath(sound.parent)) == Path(os.path.realpath(music_dir(kit))) else "Photos"
    except OSError:
        where = "Photos"
    return where + "/" + arrange._nfc(sound.name)


def _note_sound(kit, sound, video, how, note=None):
    """Write down which recording this sound was taken from. Saved whole, the version before kept beside it, one
    writer at a time. A note that can't be written (a drive that can't be written to) is logged and the make goes
    on: the next look then goes by the files' times, as hers."""
    try:
        note = note or recording_print(video)
        if note is None:
            return
        with arrange.locked(kit / ".kit" / SOUNDS_LOCK):
            d = _sounds(kit)
            key = _sound_key(kit, sound)
            want = dict(note, of=arrange._nfc(Path(video).name), how=how)
            have = d["sounds"].get(key)
            if isinstance(have, dict) and {k: have.get(k) for k in want} == want:
                return                             # nothing to change: nothing written (safe to run twice)
            want["when"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            d["v"] = 1
            d["sounds"][key] = want
            p = sounds_path(kit)
            try:
                before = p.read_bytes()
            except OSError:
                before = None
            if before is not None:
                _write_bytes_whole(kit / ".kit" / SOUNDS_PREV, before)
            arrange.write_whole(p, d)
    except Exception as e:  # noqa: BLE001
        arrange.log(f"reel page: couldn't note which recording a sound came from: {e.__class__.__name__}: {str(e)[:200]}")


def _sound_is_of(kit, sound, video):
    """Was this sound (one that can be read) taken from the recording that is there now? With a note: by the
    recording's size, time and start (same_recording). With none: her rule, a sound at least as new as its
    recording is that recording's, and it is noted so the next look need not go by times."""
    key = _sound_key(kit, sound)
    note = _sounds(kit)["sounds"].get(key)
    if isinstance(note, dict):
        same, keep = same_recording(note, video)
        if same and keep is not note:
            _note_sound(kit, sound, video, note.get("how") or "made", {k: keep[k] for k in ("size", "time", "head")})
        return same
    try:
        mine = sound.stat().st_mtime >= Path(video).stat().st_mtime
    except OSError:
        return False
    if mine:
        _note_sound(kit, sound, video, "found")
    return mine


def sound_for(kit, s, deadline=None):
    """The sound of a screen recording (hers: sound_of), made ONCE and never written over: "<name> sound.m4a"
    beside the recording (a PC with no ffmpeg makes "<name> sound.wav"), or, when the recording sits in a Photos
    folder outside Your Content (an export folder the kit only points to), in the kit's own Music folder
    (decision 4), since their folder is never written to. A sound already there is used when it can be read AND it
    was taken from the recording that is there now (_sound_is_of). One that can't be read (cut off part way), or
    that came from an earlier recording of the same name (her v25: they replaced the recording), is left exactly
    as it is and the next name is looked at: "<name> sound 2.m4a", "sound 3"...; the first name with nothing
    under it is made.
    deadline: the job's own (time.time() it must be done by). Returns (path, None) or (None, her plain words)."""
    video = s["path"]
    if s["where"] == "Photos" and not SOUND_BESIDE_OUTSIDE and not _inside_content(video):
        if not music_ok(kit):
            return None, WORDS["no_sound"]
        folder = music_dir(kit)
        try:
            folder.mkdir(exist_ok=True)
        except OSError:
            return None, WORDS["no_sound"]
    else:
        folder = video.parent
        if s["where"] == "Music" and not music_ok(kit):
            return None, WORDS["no_sound"]
    out = None
    for extra in [""] + [f" {n}" for n in range(2, SOUND_SPARES + 2)]:
        names = [video.stem + SOUND + extra + ext for ext in (".m4a", ".wav")]
        have = [h for h in (_named(folder, n) for n in names) if h is not None]
        good = [h for h in have if _sound_ok(h)]
        mine = next((h for h in good if _sound_is_of(kit, h, video)), None)
        if mine is not None:
            return mine, None
        if have:
            if not good:
                arrange.log(f"reel page: a sound beside a recording couldn't be read, so it is left as it is: {have[0].name}")
            continue                               # unreadable, or an earlier recording's: left as it is
        out = folder / names[0]                    # the first name with nothing under it
        break
    if out is None:
        return None, WORDS["no_sound"]
    if this_computer.WINDOWS and this_computer.path_too_long(out):      # unproven on a real PC
        return None, WORDS["no_sound"]
    left = (deadline - time.time()) if deadline else MAKE_LIMIT
    if left <= 1:
        return None, WORDS["too_long"]
    before = recording_print(video)                # the recording as it is BEFORE its sound is read
    try:
        got, how = _reel_module("sound").extract_audio(video, out, timeout=left)
    except Exception as e:  # noqa: BLE001
        arrange.log(f"reel page: the sound of a recording couldn't be taken: {e.__class__.__name__}: {str(e)[:200]}")
        return None, WORDS["no_sound"]
    if not got:
        arrange.log(f"reel page: the sound of a recording couldn't be taken: {str(how)[:200]}")
        return None, WORDS["too_long"] if "took too long" in str(how) else WORDS["no_sound"]
    if before is not None:
        _note_sound(kit, Path(got), video, "made", before)   # a recording swapped while it was read won't match this
    return Path(got), None                                   # note, so its sound is taken again next time


# ---------- Remove this song (her v27, section 2, step 3: "two taps, to the Trash"; her v25 /music/remove) ----------
# Built Nov 17 (Lane E's E12); the button in the song drop-down is Lane A's (A8). Hers takes a path from the page
# and runs one osascript per file, stopping at the first failure with the earlier files already gone. Ours takes
# the song's id (never a path, as every reel route does) and finds it here; only a song in the shoot's own Music
# folder can go (a recording in the Photos folder is in a folder of theirs); a recording takes every sound made
# from it with it; every path is checked before the first move (this_computer.trash_many), each goes to the
# computer's own Trash (the Recycle Bin on a PC; Put Back and Restore bring it back), and nothing is ever deleted;
# then the open reel's pick is cleared under the record's lock with the counter one higher, so a page that
# never got the answer, or a page a step behind, is told. Other reels of the shoot that picked the song are not
# rewritten: opened, they say her song_gone line (as hers).

def sounds_of_recording(kit, s):
    """Every sound taken from this recording that sits beside it in the Music folder, found two ways and merged:
    the sounds noted for it in reel-sounds.json, and every "<name> sound", "<name> sound 2"... (SOUND_NAME, any
    number; hers takes " sound" and " sound 2" to " sound 9") with that recording's name. Real files only, each
    once: a link is left where it is (list_songs leaves it out too), and nothing is followed."""
    music = music_dir(kit)
    stem = arrange._nfc(s["path"].stem).casefold()
    of = arrange._nfc(s["path"].name)
    names = []
    for key, note in _sounds(kit)["sounds"].items():
        if isinstance(note, dict) and key.startswith("Music/") and arrange._nfc(str(note.get("of") or "")) == of:
            names.append(key[len("Music/"):])
    for f in _listing(music):
        m = SOUND_NAME.fullmatch(Path(f).stem)
        if f.lower().endswith((".m4a", ".wav")) and m and arrange._nfc(m.group(1)).casefold() == stem:
            names.append(f)
    out, seen = [], set()
    for n in names:
        p = _named(music, n)
        if p is None or p == s["path"]:
            continue
        try:
            if p.is_symlink() or not p.is_file():
                continue
        except OSError:
            continue
        k = arrange._nfc(p.name).casefold()
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def _drop_sound_notes(kit, sounds):
    """The moved sounds' lines come out of reel-sounds.json (the version before kept beside it, one writer at a
    time, written only when there is one to drop). A note that can't be written is logged and that is all: a
    line for a sound that is gone does no harm (sound_for looks for the file first)."""
    keys = {"Music/" + arrange._nfc(p.name) for p in sounds}
    try:
        with arrange.locked(kit / ".kit" / SOUNDS_LOCK):
            d = _sounds(kit)
            if not any(k in d["sounds"] for k in keys):
                return
            d["v"] = 1
            d["sounds"] = {k: v for k, v in d["sounds"].items() if k not in keys}
            p = sounds_path(kit)
            try:
                before = p.read_bytes()
            except OSError:
                before = None
            if before is not None:
                _write_bytes_whole(kit / ".kit" / SOUNDS_PREV, before)
            arrange.write_whole(p, d)
    except Exception as e:  # noqa: BLE001
        arrange.log(f"reel page: a removed sound's note couldn't be dropped: {e.__class__.__name__}: {str(e)[:200]}")


def _clear_song(kit, sid):
    """Under the record's lock: when the open reel's picked song is this one it goes back to "no song picked yet"
    (saved.song None; hers: the page does it on success, ours the server too, so a page that never gets the
    answer sees it on reload), the counter moves on and the record is saved whole with the version before kept.
    Other reels of the shoot are not touched. True when it was cleared."""
    try:
        with arrange.locked(lock_path(kit)):
            rec, rows, stamp = sync(kit)
            saved = rec.get("saved") if isinstance(rec.get("saved"), dict) else None
            if not saved or saved.get("song") != sid:
                return False
            saved["song"] = None
            saved["updated"] = time.time()
            rec["rev"] = int(rec.get("rev") or 0) + 1
            rec.pop("from", None)
            if rows:
                _stamp_names(rec, rows, stamp)
            save(kit, rec)
            return True
    except Exception as e:  # noqa: BLE001  (the song is in the Trash either way, and the page's next look drops it)
        arrange.log(f"reel page: a removed song couldn't be cleared from the record: {e.__class__.__name__}: {str(e)[:200]}")
        return False


def remove_song(body):
    """POST /reel-song-remove {kit, song: id} (hers: /music/remove {path}). (status, answer): on success
    {ok, words (her song_trashed line), songs (the list without it), cleared (the open reel's pick was this song
    and is now "not picked yet")}. Refused with her song_not_here line when the id is not one of this shoot's
    songs right now, with ours when the song is in the Photos folder, and with her song_cant_trash line when
    the computer's Trash would not take it (then "why" carries this_computer's plain reason, and, when some of
    a recording's files had already gone, the names of those after her line). Nothing is deleted anywhere."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    if set(body) - {"kit", "song"}:
        return _bad()
    sid = body.get("song")
    if not isinstance(sid, str) or not SONG_ID.fullmatch(sid):
        return _bad()
    rec_kit = kit_mod.load_rec(kit)
    s = song_by_id(kit, sid, rec_kit)
    if s is None:
        return _bad(WORDS["song_not_here"], 400, why="song", songs=songs_for_page(kit, rec_kit))
    if s["where"] != "Music":
        return _bad(OUR_WORDS["song_in_photos_stays"], 400, why="photos", songs=songs_for_page(kit, rec_kit))
    paths = [s["path"]] + (sounds_of_recording(kit, s) if s["kind"] == "video" else [])
    ok, why, moved, _left = this_computer.trash_many(paths, music_dir(kit))
    moved = [Path(p) for p in moved]
    cleared = False
    if moved:
        sounds = [p for p in moved if p != s["path"]]
        if sounds:
            _drop_sound_notes(kit, sounds)
        if moved[0] == s["path"]:                      # the song itself is gone from the list
            cleared = _clear_song(kit, sid)
    songs = songs_for_page(kit, rec_kit)
    if not ok:
        arrange.log(f"reel page: Remove this song couldn't finish: {why} ({len(moved)} moved, {len(paths) - len(moved)} left)")
        words = pc_words(trash_words(WORDS["song_cant_trash"]))
        if moved:
            words += " " + trash_words(OUR_WORDS["song_part_moved"]).replace("{names}", ", ".join(p.name for p in moved))
        return _bad(words, 400, why=why, songs=songs, cleared=cleared)
    return 200, {"ok": True, "words": pc_words(trash_words(WORDS["song_trashed"])), "songs": songs, "cleared": cleared}


# ---------- step 1: the footage (hers: server.py footage_list, previews, moments) ----------
# The videos are only ever read. A video is named to the page by its key (video.key: from its name, size and
# time), a moment by its id; no path ever reaches the page. Everything the page needs made from a video (the
# strip of stills, the small copy to play, a moment's still) goes in <kit>/.kit/footage, each look in a folder of
# its own (video.fresh_folder), never over anything, nothing deleted:
#   .kit/footage/facts.json             {key: the video's facts} (read once from its header, video.facts)
#   .kit/footage/<key>/preview.json     its preview's state: waiting, making, ready, failed, lowspace, pc, hevc_pc,
#                                       with the strip's folder and stills and whether a copy was made
#   .kit/footage/<key>/strip/           a still every 2 s (or "strip 2"... when a look was cut off and made again)
#   .kit/footage/<key>/preview.mp4      the 540p copy, only for a video that doesn't play as it is
#   .kit/footage/moments/<id>/          the still on a moment's card
# One preview worker per page server makes them, one video at a time (hers: _preview_worker).

def _own_folder(kit, name):
    """Is <kit>/<name> (if it is there at all) a real folder of the kit's own? A link, or anything leading out of
    the kit, is never listed, written into or opened (music_ok's rule, for the Footage folder too)."""
    d = kit / name
    try:
        if not os.path.lexists(d):
            return True
        if d.is_symlink() or not d.is_dir():
            return False
        return Path(os.path.realpath(d)).parent == Path(os.path.realpath(kit))
    except OSError:
        return False


def footage_dir(kit):
    return kit / FOOTAGE


def footage_ok(kit):
    return _own_folder(kit, FOOTAGE)


def foot_work(kit):
    return kit / ".kit" / FOOT_WORK


def _video():
    return _reel_module("video")


def _read(p):
    try:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


_FACTS = {}                  # key -> facts, read once in this process (and kept in .kit/footage/facts.json)
_FACTS_LOCK = threading.Lock()


def _folder_work(kit, folder):
    """Where the Assistant keeps what it made for the videos of one of the kit's folders: Footage's in
    .kit/footage, as always; any other folder's (v24: Talking) in a hidden folder of its own, .kit/talking."""
    return foot_work(kit) if folder == FOOTAGE else kit / ".kit" / folder.lower()


def _facts(kit, p, key, folder=FOOTAGE):
    """The video's facts (video.facts, from its header): from this process's memory, else the kit's facts.json,
    else read and kept there. {"refused": plain words} for a file that is not a video it can read. Each folder
    has a facts file of its own (Footage's is .kit/footage/facts.json, as always)."""
    work = _folder_work(kit, folder)
    key_mem = key if folder == FOOTAGE else (folder, key)
    with _FACTS_LOCK:
        if key_mem in _FACTS:
            return _FACTS[key_mem]
    f = work / "facts.json"
    kept = _read(f) or {}
    got = kept.get(key) if isinstance(kept.get(key), dict) else None
    if got is None:
        v = _video()
        try:
            got = v.facts(p)
        except v.NotAVideo as e:
            got = {"refused": str(e)}
        except OSError:
            return {"refused": WORDS["video_not_here"] if folder == FOOTAGE else NOT_IN_TALKING}
        if got.get("refused") and _just_changed(p):
            return got                     # maybe still coming in: asked again on the next look, never kept
        try:
            with arrange.locked(work / "facts.lock"):
                kept = _read(f) or {}
                kept[key] = got
                arrange.write_whole(f, kept)
        except (OSError, arrange.Busy):
            pass
    with _FACTS_LOCK:
        _FACTS[key_mem] = got
    return got


def _just_changed(p):
    try:
        return time.time() - Path(p).stat().st_mtime < COMING_RECENT
    except OSError:
        return False


def list_videos(kit, coming=None, folder=FOOTAGE):
    """The videos in <kit>/Footage, in name order (hers): [{key, name, path, size, facts}]. Hidden files, links
    and anything not a .mov, .mp4 or .m4v are left out. The path never leaves this computer's own side.
    A video still being copied in (its boxes run past the end of the file, and it changed in the last
    COMING_RECENT seconds) is left out too, its facts never read and nothing made for it: it goes in `coming`
    (a list, when given) as {name, size}, and comes in whole on a later look (v19 review, Nov 7: a copy in
    progress left a record for every size it passed through).
    `folder` is another folder of the kit's own to list the same way (v24: "Talking"), with the same "is it the
    kit's own folder" check and a facts file of its own; Footage, the default, is exactly as before."""
    d = kit / folder
    if not _own_folder(kit, folder) or not d.is_dir():
        return []
    out = []
    vm = _video()
    for f in sorted(_listing(d)):
        if f.startswith(".") or not f.lower().endswith(VIDEO_EXTS):
            continue
        p = d / f
        try:
            if p.is_symlink() or not p.is_file():
                continue
            size = p.stat().st_size
            if vm.still_coming(p) and _just_changed(p):
                if coming is not None:
                    coming.append({"name": f, "size": size})
                continue
            key = vm.key(p)
        except OSError:
            continue
        fx = _facts(kit, p, key, folder)
        if fx.get("refused") and _just_changed(p):
            if coming is not None:            # its header isn't in yet (a phone writes it last): still coming in
                coming.append({"name": f, "size": size})
            continue
        out.append({"key": key, "name": f, "path": p, "size": size, "facts": fx})
    return out


def video_by_key(kit, key):
    if not isinstance(key, str) or not KEY.fullmatch(key):
        return None
    return next((v for v in list_videos(kit) if v["key"] == key), None)


def video_by_name(kit, name, vids=None):
    """A moment names its video by its file name (hers: "Footage/<name>"): that video now, or None."""
    name = re.sub(r"^Footage/", "", str(name or ""))
    want = arrange._nfc(name).casefold()
    return next((v for v in (vids if vids is not None else list_videos(kit)) if arrange._nfc(v["name"]).casefold() == want), None)


# ---- the previews: the strip of stills and, for a video that doesn't play as it is, the small copy ----

_PREV_Q = None
_PREV_LOCK = threading.Lock()
_PREV_TRIED = set()          # (kit, key) asked for in this process: made, or tried once and kept as it came out
DONE_STATES = ("ready", "failed", "lowspace", "pc", "hevc_pc")


def _prev_dir(kit, key):
    return foot_work(kit) / key


def _prev_rec(kit, key):
    return _read(_prev_dir(kit, key) / "preview.json") or {}


def _prev_write(kit, key, rec):
    arrange.write_whole(_prev_dir(kit, key) / "preview.json", rec)


def _prev_ready(kit, key, rec, f):
    """Is the preview as preview.json says, on disk: the strip's stills there, and the copy when one is needed?"""
    if rec.get("state") != "ready":
        return False
    if rec.get("no_strip"):            # a PC: it plays as it is, with no strip of stills (video.py's named gap)
        return not _video().avfoundation_here() and bool((f or {}).get("plays_as_is"))
    strip = _prev_dir(kit, key) / str(rec.get("strip") or "")
    if not rec.get("strip") or not strip.is_dir() or not rec.get("stills"):
        return False
    if not (f or {}).get("plays_as_is") and not (_prev_dir(kit, key) / "preview.mp4").is_file():
        return False
    return True


def _make_preview(kit, v):
    """Hers (_make_preview): reads the video and writes a strip of stills, and, only for a video that doesn't play
    as it is, the small copy; never touches the video. The state goes in preview.json as it goes. All of it in
    this computer's one video turn (video.turn), so no other page server, no footage look and no Use this moment
    can make the same thing beside it (v19 review, Nov 7); the record is read again once the turn is held."""
    vm = _video()
    with vm.turn(PREVIEW_WAIT) as ok:
        if not ok:                     # its turn didn't come: asked for again on the next look
            with _PREV_LOCK:
                _PREV_TRIED.discard((str(kit), v["key"]))
            return
        _make_preview_now(kit, v)


def _make_preview_now(kit, v):
    vm = _video()
    key, f = v["key"], v["facts"]
    d = _prev_dir(kit, key)
    rec = _prev_rec(kit, key)
    if f.get("refused"):
        _prev_write(kit, key, {"state": "failed", "words": WORDS["vid_failed"]})
        return
    if _prev_ready(kit, key, rec, f):
        return                         # made meanwhile, by another server in its turn
    if not vm.avfoundation_here() and f.get("plays_as_is"):
        # a PC: no stills yet (video.py's named gap, decision 11), but the page plays the original as it is, so it
        # is ready with no strip under the player, and Use this moment works on it (v19 review, Nov 7)
        _prev_write(kit, key, {"state": "ready", "strip": "", "stills": [], "no_strip": True, "t": time.time()})
        return
    rec.pop("no_strip", None)
    rec.update(state="making", t=time.time())
    _prev_write(kit, key, rec)
    if not (rec.get("strip") and (d / rec["strip"]).is_dir() and rec.get("stills")):
        if vm.avfoundation_here() and not vm.space_ok(d, 50e6):
            _prev_write(kit, key, {"state": "lowspace", "words": WORDS["vid_lowspace"]})
            return
        n = max(1, int(math.ceil(float(f.get("length") or 0) / STRIP_EVERY - 1e-6)))
        times = [round(i * STRIP_EVERY, 1) for i in range(n)]
        r = vm.stills(v["path"], times, d, name="strip", f=f, deadline=time.time() + 60 + 2 * n)
        if not r.get("ok"):
            st = r.get("state") if r.get("state") in ("pc", "hevc_pc") else "failed"
            _prev_write(kit, key, {"state": st, "words": r.get("words") if st != "failed" else WORDS["vid_failed"]})
            return
        rec["strip"] = Path(r["folder"]).name
        rec["stills"] = [{"n": i + 1, "t": times[i], "file": s["file"]} for i, s in enumerate(r["stills"])
                         if i < len(times) and s.get("file")]
    if not f.get("plays_as_is"):
        r = vm.preview_copy(v["path"], d / "preview.mp4", f=f)
        if not r.get("ok"):
            st = r.get("state") if r.get("state") in ("lowspace", "pc", "hevc_pc") else "failed"
            _prev_write(kit, key, {"state": st, "words": r.get("words") if st in ("pc", "hevc_pc") else
                                   WORDS["vid_lowspace" if st == "lowspace" else "vid_failed"]})
            return
        rec["copy"] = "preview.mp4"
    rec.update(state="ready", t=time.time())
    _prev_write(kit, key, rec)


def _queue(job):
    """Hand a job to this server's one preview worker (started the first time)."""
    global _PREV_Q
    with _PREV_LOCK:
        if _PREV_Q is None:
            import queue
            _PREV_Q = queue.Queue()
            threading.Thread(target=_preview_worker, name="reel previews", daemon=True).start()
        _PREV_Q.put(job)


def _preview_worker():
    while True:
        job = _PREV_Q.get()
        if job[0] == "still":              # a moment's card still, left here by a press that couldn't wait
            try:
                _moment_still(*job[1:], wait=PREVIEW_WAIT)
            except Exception as e:  # noqa: BLE001
                arrange.log(f"reel page: a moment's still couldn't be made: {e.__class__.__name__}: {str(e)[:200]}")
            continue
        kit, v = job[1], job[2]
        try:
            _make_preview(kit, v)
        except Exception as e:  # noqa: BLE001  (a preview is a nice-to-have; the reel never depends on it, hers)
            arrange.log(f"reel page: a preview couldn't be made: {e.__class__.__name__}: {str(e)[:200]}")
            try:
                _prev_write(kit, v["key"], {"state": "failed", "words": WORDS["vid_failed"]})
            except OSError:
                pass


def preview_state(kit, v):
    """(state, words) of a video's preview. A preview not made yet (or left part way by a server that stopped)
    is handed to this server's one worker, once."""
    key = v["key"]
    rec = _prev_rec(kit, key)
    if _prev_ready(kit, key, rec, v["facts"]):
        return "ready", None
    tag = (str(kit), key)
    with _PREV_LOCK:
        if tag in _PREV_TRIED:
            st = rec.get("state")
            if st in DONE_STATES and st != "ready":
                return st, rec.get("words")
            return ("making" if st == "making" else "waiting"), None
        _PREV_TRIED.add(tag)
    _queue(("preview", kit, v))
    return "waiting", None


def strip_for_page(kit, key):
    rec = _prev_rec(kit, key)
    return [{"n": s["n"], "t": s["t"]} for s in rec.get("stills") or [] if isinstance(s, dict) and "n" in s and "t" in s]


def videos_for_page(kit, vids=None, coming=None):
    """Hers (footage_list): each video as the page draws it. No path. Ours: a video still being copied in is
    listed by its name with preview "coming" and nothing else (no key, nothing made for it yet)."""
    out = []
    if vids is None:
        coming = []
        vids = list_videos(kit, coming)
    for c in coming or []:
        out.append({"key": "", "name": c["name"], "length": 0, "w": 0, "h": 0, "mb": int(round(c["size"] / 1e6)),
                    "preview": "coming", "words": OUR_WORDS["coming"].replace("{name}", c["name"]), "strip": []})
    for v in vids:
        f = v["facts"]
        st, words = preview_state(kit, v)
        out.append({"key": v["key"], "name": v["name"], "length": round(float(f.get("length") or 0), 1),
                    "w": int(f.get("w") or 0), "h": int(f.get("h") or 0), "mb": int(round(v["size"] / 1e6)),
                    "preview": st, "words": words, "strip": strip_for_page(kit, v["key"]) if st == "ready" else []})
    out.sort(key=lambda x: x["name"])
    return out


# ---- the moments (hers: rec["moments"]; BUILD.md section 8) ----

def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x)) else None


def moments_of(rec):
    """The record's moments, each checked (Claude's look writes them too): only those with an id of hers' shape,
    a video's name, and a start before an end. Card order."""
    out, seen = [], set()
    for m in rec.get("moments") or []:
        if not isinstance(m, dict) or not isinstance(m.get("id"), str) or not MOMENT_ID.fullmatch(m["id"]) or m["id"] in seen:
            continue
        s, e = _num(m.get("start")), _num(m.get("end"))
        if s is None or e is None or e <= s or s < 0 or not isinstance(m.get("video"), str):
            continue
        seen.add(m["id"])
        out.append(m)
    return out


def moments_for_page(kit, rec, on_sheet, vids=None):
    """The moments as the page draws them: the video by its key (and its name as text), never a path."""
    vids = vids if vids is not None else list_videos(kit)
    out = []
    for m in moments_of(rec):
        v = video_by_name(kit, m["video"], vids)
        photo = m.get("photo") if type(m.get("photo")) is int and m.get("photo") in on_sheet else None
        out.append({"id": m["id"], "key": v["key"] if v else "", "name": re.sub(r"^Footage/", "", m["video"]),
                    "start": round(float(m["start"]), 2), "end": round(float(m["end"]), 2),
                    "label": str(m.get("label") or "")[:200], "photo": photo, "keep": m.get("keep") is not False,
                    "by": "you" if m.get("by") == "you" else "", "set": bool(m.get("set")), "named": m.get("named") is True})
    return out


PICK_AT = WORDS["your_pick_at"].split("{t}")[0]        # "Your pick at ": her label for a clip of theirs not named yet


def unnamed_picks(ms):
    """Their own clips that have no name from the chat yet (her v27: a label that is empty or her "Your pick at
    1:09.6"), in card order."""
    return [m for m in ms if m.get("by") == "you" and (not str(m.get("label") or "").strip() or str(m.get("label")).startswith(PICK_AT))]


def _bts_of(rec, on_sheet):
    """Claude's order with footage (her claude_bts), only photos on the numbered list."""
    out = []
    for x in rec.get("claude_bts") or []:
        if isinstance(x, dict) and type(x.get("n")) is int and x["n"] in on_sheet and x["n"] not in [y["n"] for y in out]:
            out.append({"n": x["n"], "h": x.get("h") if x.get("h") in ("+", "-") else ""})
    return out


def mmss(t):
    """Hers (the page's mmss, and server.py's label): 0:04, 1:02.5."""
    t = max(0.0, float(t))
    m, s = int(t // 60), t - int(t // 60) * 60
    return "%d:%04.1f" % (m, s) if round(s, 6) % 1 else "%d:%02d" % (m, round(s))


def _moment_still(kit, mid, v, at, wait=MOMENT_WAIT):
    """The still on a moment's card (hers: one frame from its middle, 360 px), in a folder of its own. A PC has
    none yet (the card shows the strip's still nearest it, or none). It waits up to `wait` seconds for this
    computer's one video turn; when that isn't long enough (a long copy is being made), the still is left to the
    preview worker, which makes it in its turn, and the card shows the strip's nearest still meanwhile."""
    try:
        vm = _video()
        if not vm.avfoundation_here():
            return
        d = foot_work(kit) / "moments" / mid
        if d.is_dir() and any(x.lower().endswith(".jpg") for x in _listing(d)):
            return                         # made already
        r = vm.stills(v["path"], [at], foot_work(kit) / "moments", name=mid, f=v["facts"],
                      deadline=time.time() + 30 + wait, wait=wait)
        if r.get("state") == "busy" and wait < PREVIEW_WAIT:
            _queue(("still", kit, mid, v, at))
    except Exception as e:  # noqa: BLE001  (a card without its still still works)
        arrange.log(f"reel page: a moment's still couldn't be made: {e.__class__.__name__}: {str(e)[:200]}")


def moment_still_file(kit, mid):
    """The still to show on a moment's card: its own, else the strip still nearest its middle, else None."""
    d = foot_work(kit) / "moments" / mid
    if d.is_dir():
        hit = sorted(f for f in _listing(d) if f.lower().endswith(".jpg") and not f.startswith("."))
        if hit:
            return d / hit[0]
    with arrange.locked(lock_path(kit)):
        rec = load(kit)
    m = next((x for x in moments_of(rec) if x["id"] == mid), None)
    v = video_by_name(kit, m["video"]) if m else None
    if not v:
        return None
    pr = _prev_rec(kit, v["key"])
    stills = [s for s in pr.get("stills") or [] if isinstance(s, dict) and s.get("file")]
    if not stills or not pr.get("strip"):
        return None
    mid_t = (float(m["start"]) + float(m["end"])) / 2
    s = min(stills, key=lambda s: abs(float(s["t"]) - mid_t))
    p = _prev_dir(kit, v["key"]) / pr["strip"] / s["file"]
    return p if p.is_file() else None


def change_moments(body):
    """POST /reel-moment {kit, do, ...}: her four moments routes, as one (hers: /moments/add, /update, /remove,
    /restore). Under the record's lock, written whole with the version before kept; a removed moment is kept in
    the record ("removed"), so Undo needs only its id and nothing is ever lost (hers had the page send the
    moment back). (status, {ok, moments} or {ok: False, words})."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    do = body.get("do")
    allowed = {"add": {"video", "start", "seconds"}, "update": {"id", "start", "end"}, "remove": {"id"},
               "restore": {"id", "at"}}.get(do)
    if allowed is None or set(body) - {"kit", "do", "reel"} - allowed:
        return _bad()
    if "reel" in body and not (isinstance(body["reel"], str) and reels.ID.fullmatch(body["reel"])):
        return _bad()
    if do != "add" and (not isinstance(body.get("id"), str) or not MOMENT_ID.fullmatch(body["id"])):
        return _bad()
    vids = list_videos(kit)
    still = None
    with arrange.locked(lock_path(kit)):
        rec, rows, stamp = sync(kit)
        if not rows:
            return _bad(NOT_READY, 404)
        if _other_reel(body, rec):
            return _bad(OUR_WORDS["newer"], 409, why="newer")
        on_sheet = {x["n"] for x in rows}
        ms = moments_of(rec)
        if do == "add":
            v = next((x for x in vids if x["key"] == body.get("video")), None) if isinstance(body.get("video"), str) else None
            start, secs = _num(body.get("start")), _num(body.get("seconds", USE_SECONDS))
            if v is None:
                return _bad(WORDS["video_not_here"])
            if start is None or secs is None:
                return _bad()
            length = float(v["facts"].get("length") or 0)
            start = max(0.0, min(start, max(0.0, length - 1)))
            end = min(length, start + max(ADD_MIN, min(ADD_MAX, secs)))
            if end - start < 0.5:
                return _bad(WORDS["video_not_here"])
            mine_n = sum(1 for m in ms if m.get("by") == "you") + 1
            mid = "u%d-%s" % (mine_n % 10000, hashlib.sha1(("%s|%s|%s" % (v["name"], start, time.time())).encode("utf-8")).hexdigest()[:6])
            while any(m["id"] == mid for m in ms):
                mid = "u%d-%s" % (mine_n % 10000, os.urandom(3).hex())
            m = {"id": mid, "video": v["name"], "start": round(start, 2), "end": round(end, 2),
                 "label": WORDS["your_pick_at"].replace("{t}", mmss(start)), "photo": None, "keep": True, "by": "you"}
            ms.insert(sum(1 for x in ms if x.get("by") == "you"), m)   # their picks first, in the order they add them
            still = (mid, v, (start + end) / 2)
        elif do == "remove":                      # any moment, theirs or Claude's (hers)
            at = next((i for i, x in enumerate(ms) if x["id"] == body["id"]), None)
            if at is None:
                return _bad(WORDS["moment_gone"])
            gone = ms.pop(at)
            rec.setdefault("removed", []).append({"moment": gone, "at": at, "when": time.time()})
        elif do == "restore":                     # Undo right after a Remove: put it back where it was (hers)
            if any(x["id"] == body["id"] for x in ms):
                pass                              # already back
            else:
                gone = [r for r in rec.get("removed") or [] if isinstance(r, dict) and isinstance(r.get("moment"), dict)
                        and r["moment"].get("id") == body["id"]]
                if not gone:
                    return _bad(WORDS["cant_put_back"])
                at = body.get("at", gone[-1].get("at", 0))
                at = int(at) if type(at) is int else int(gone[-1].get("at") or 0)
                ms.insert(max(0, min(at, len(ms))), gone[-1]["moment"])
                rec["removed"] = [r for r in rec["removed"] if r is not gone[-1]]
        else:                                     # update: a longer or shorter clip, or a new start / end (hers)
            m = next((x for x in ms if x["id"] == body["id"]), None)
            if m is None:
                return _bad(WORDS["moment_gone"])
            s_in, e_in = body.get("start"), body.get("end")
            if (s_in is not None and _num(s_in) is None) or (e_in is not None and _num(e_in) is None) or (s_in is None and e_in is None):
                return _bad()
            v = video_by_name(kit, m["video"], vids)
            length = float(v["facts"].get("length") or 0) if v else 0.0
            length = length or float(m["end"])
            start = _num(s_in) if s_in is not None else float(m["start"])
            end = _num(e_in) if e_in is not None else float(m["end"])
            if s_in is not None and e_in is not None:
                # Trim's Done (her v25): where it starts AND where it ends. Her page only ever sends 1 to 15
                # seconds from 0 on; anything else is refused whole, never bent into shape without a word (ours)
                if start < 0 or not (MOMENT_MIN - 0.011 <= end - start <= MOMENT_MAX + 0.011):
                    return _bad(OUR_WORDS["trim_length"])
                if end > length:                       # the page knows the length to a tenth: slide it back inside
                    start, end = max(0.0, start - (end - length)), length
            else:
                start = max(0.0, min(start, length - 0.5))
                if s_in is not None and e_in is None and end - start < MOMENT_MIN:
                    end = start + (float(m["end"]) - float(m["start"]))      # a new start keeps the length it had
                end = max(start + MOMENT_MIN, min(end, start + MOMENT_MAX, length))
                if end > length:                       # never past the video's end (hers could leave it half a
                    end = length                       # second past, when the start sat right at the end)
                    start = max(0.0, min(start, end - MOMENT_MIN))
            m.update(start=round(start, 2), end=round(end, 2), set=True)
            # her v27 (Nov 16): trimming a clip keeps a name it was given; only a "Your pick at 1:09.6" label moves
            if m.get("by") == "you" and m.get("named") is not True and (not str(m.get("label") or "").strip() or str(m.get("label")).startswith(PICK_AT)):
                m["label"] = WORDS["your_pick_at"].replace("{t}", mmss(start))
        rec["moments"] = ms
        rec["moments_at"] = time.time()
        _stamp_names(rec, rows, stamp)
        save(kit, rec)
        out = moments_for_page(kit, rec, on_sheet, vids)
    if still:
        _moment_still(kit, *still)
    return 200, {"ok": True, "moments": out}


def open_footage(kit):
    """Makes <kit>/Footage if it isn't there and opens it (hers: /footage/open)."""
    if not footage_ok(kit):
        arrange.log("reel page: the shoot's Footage folder is a link or not a folder, so it isn't opened")
        return 200, {"ok": False, "words": WORDS["cant_open"]}
    d = footage_dir(kit)
    try:
        d.mkdir(exist_ok=True)
    except OSError:
        return 200, {"ok": False, "words": WORDS["cant_open"]}
    ok, note = _open_folder(d)
    if not ok:
        arrange.log(f"reel page: the Footage folder couldn't be opened: {str(note)[:200]}")
        return 200, {"ok": False, "words": WORDS["cant_open"]}
    w = pc_words(WORDS["footage_open"])
    if note == "behind":
        first, rest = w.split(". ", 1)
        w = first + OUR_WORDS["behind"] + " " + rest
    return 200, {"ok": True, "words": w}


def footage_for_page(kit, read_only=False):
    """GET /reel-footage: hers (/footage with /reel's moments): the videos, the moments and Claude's footage order.
    Asking starts any preview not made yet, one at a time.
    `read_only` (GET /reel-footage?kit=&for=talking, the talking reel page's video picker): the videos only. The
    reel page's own record is neither brought in line with the numbered list nor written, and no moments are
    read; the previews are still asked for, or a video never opened on the reel page would never be ready."""
    coming = []
    vids = list_videos(kit, coming)
    if read_only:
        return {"ok": True, "folder": footage_dir(kit).is_dir() and footage_ok(kit), "videos": videos_for_page(kit, vids, coming),
                "moments": [], "claude_bts": []}
    with arrange.locked(lock_path(kit)):
        rec, rows, stamp = sync(kit)
    on_sheet = {x["n"] for x in rows}
    return {"ok": True, "folder": footage_dir(kit).is_dir() and footage_ok(kit), "videos": videos_for_page(kit, vids, coming),
            "moments": moments_for_page(kit, rec, on_sheet, vids), "claude_bts": _bts_of(rec, on_sheet)}


# ---- Make my reel with footage: her order for each style (hers: footage_items) ----

def default_sel(style, ms):
    """Hers (the page's defaultSel): the clips a style uses before they select any."""
    ok = [m for m in ms if m.get("keep") is not False]
    pool = ok or ms
    if style == "first":
        return [m["id"] for m in pool[:1]]
    if style == "bookends":
        return [m["id"] for m in ([pool[0], pool[-1]] if len(pool) > 1 else pool[:1])]
    if style == "reveal":
        return [m["id"] for m in ms if m.get("photo")][:2]
    if style == BROLL_STYLE:
        return [m["id"] for m in pool[:4]]       # B-roll starts with 4 clips (hers, v27)
    return [m["id"] for m in pool[:2]]           # Back and forth starts with 2 clips (Nicole, Nov 6)


def style_of(saved):
    """The footage style saved for a reel: one of hers, B-roll's own (v27), else Moment first."""
    st = (saved or {}).get("style")
    return st if st in STYLES or st == BROLL_STYLE else "first"


def chosen_clips(saved, ms):
    """Hers (the page's chosen()): the clips selected for the saved style, in card order."""
    style = style_of(saved)
    sel = saved.get("sel") if isinstance(saved.get("sel"), dict) else {}
    ids = sel.get(style) if isinstance(sel.get(style), list) else default_sel(style, ms)
    return [m["id"] for m in ms if m["id"] in ids]


class NoFootage(Exception):
    """Her ValueError from footage_items: str() is her plain words."""


def footage_order(kit, rec, style, clips, order, on_sheet, vids=None):
    """Her footage_items, our way: the reel's pieces as reel.py's --picks ("c1,7+,2,c2,11-,4") and --clips (one
    entry per clip as it plays, so Bookends with one clip has it twice, c1 and c2). order: the photos [(n, mark)].
    Raises NoFootage with her words."""
    ms = moments_of(rec)
    if not ms:
        raise NoFootage(WORDS["no_moments"].replace("{_}", ""))
    if isinstance(clips, list):              # the clips they selected for this style, in the order shown (hers)
        want = set(clips)
        kept = [m for m in ms if m["id"] in want]
    else:
        kept = [m for m in ms if m.get("keep", True) is not False] or ms
        if style in ("backforth", "reveal"):
            kept = kept[:2]
    if not kept:
        raise NoFootage(WORDS["select_clips"])
    if style not in STYLES and style != BROLL_STYLE:
        raise NoFootage(WORDS["pick_style"])
    vids = vids if vids is not None else list_videos(kit)
    entries, tokens = [], []

    def clip(m):
        v = video_by_name(kit, m["video"], vids)
        if v is None or v["facts"].get("refused"):
            raise NoFootage(WORDS["video_not_here"])
        f = v["facts"]
        dur = max(0.5, float(m["end"]) - float(m["start"]))   # exactly the length on the card (hers)
        entries.append({"path": str(v["path"]), "src": round(float(m["start"]), 2), "seconds": round(dur, 2),
                        "w": int(f.get("w") or 0), "h": int(f.get("h") or 0), "length": float(f.get("length") or 0),
                        "moment": m["id"], "key": v.get("key")})     # the key: the watch step plays the clip by it
        tokens.append("c%d" % len(entries))

    def photo(n, mark=""):
        if n not in on_sheet:
            raise NoFootage(WORDS["photo_not_here"].replace("{n}", str(n)))
        tokens.append("%d%s" % (n, mark))

    if style == "first":
        clip(kept[0])
        for n, h in order:
            photo(n, h)
    elif style == "reveal":
        pairs = [m for m in kept if m.get("photo")]
        if not pairs:
            raise NoFootage(WORDS["reveal_none"].replace("{_}", ""))
        used = set()
        for m in pairs:
            clip(m)
            photo(int(m["photo"]), "+")
            used.add(int(m["photo"]))
        for n, h in order:
            if n not in used:
                photo(n, h)
    elif style == BROLL_STYLE:              # B-roll (her v27): only the clips they chose, in order, no photos
        for m in kept:
            clip(m)
    elif style == "backforth":               # a clip, then a couple of photos, then the next clip (hers)
        rest = list(order)
        for m in kept:
            clip(m)
            for _ in range(2):
                if rest:
                    photo(*rest.pop(0))
        for n, h in rest:
            photo(n, h)
    else:                                    # bookends: one opens, one closes (the same one twice when there is one)
        clip(kept[0])
        for n, h in order:
            photo(n, h)
        clip(kept[-1] if len(kept) > 1 else kept[0])
    return ",".join(tokens), entries


def _sel(v):
    if not isinstance(v, dict):
        raise Refused("sel")
    out = {}
    for k, ids in v.items():
        if (k not in STYLES and k != BROLL_STYLE) or not isinstance(ids, list) or len(ids) > 12:
            raise Refused("sel")
        if any(not isinstance(x, str) or not MOMENT_ID.fullmatch(x) for x in ids):
            raise Refused("sel")
        out[k] = list(ids)
    return out


def _onscreen(v):
    """B-roll's words on screen (her v27 "onscreen"), checked field by field: the words, a font and a style of hers,
    the place (only ever "custom": the middle of the words as a share of the screen, inside her bounds) and the
    size, numbers as numbers (hers kept x, y and size as whatever came, cut to 300 characters as text)."""
    if not isinstance(v, dict) or set(v) - {"text", "font", "style", "pos", "x", "y", "size", "hold"}:
        raise Refused("onscreen")
    text = _text(v.get("text", ""), ONSCREEN_TEXT_MAX)
    font, style = v.get("font", OS_FONTS[0]), v.get("style", OS_STYLES[0])
    if font not in OS_FONTS or style not in OS_STYLES or v.get("pos", "custom") != "custom" or v.get("hold", "all") != "all":
        raise Refused("onscreen")

    def num(key, lo, hi, default):
        x = v.get(key, default)
        if type(x) not in (int, float) or x != x or not lo <= x <= hi:
            raise Refused("onscreen")
        return round(float(x), 3)
    return {"text": text, "font": font, "style": style, "pos": "custom", "x": num("x", OS_X[0], OS_X[1], 0.5),
            "y": num("y", OS_Y[0], OS_Y[1], 0.24), "size": num("size", OS_SIZE[0], OS_SIZE[1], 1.0), "hold": "all"}


def _feel(v):
    v = re.sub(r"\s+", " ", _text(v, 200)).strip()
    if len(v) > 40:
        raise Refused("feel")
    return v


# Every field the page may save, with its check (her record's "saved", BUILD.md section 8). A field the page
# does not send is kept as it is. A later step adds its own field here.
SAVE_FIELDS = {
    "picks": lambda v, kit, ons: _picks(v, ons),
    "mine": lambda v, kit, ons: v if type(v) is bool else _no("mine"),
    "mine_picks": lambda v, kit, ons: None if v is None else _picks(v, ons),
    "song": lambda v, kit, ons: _song(v, kit),
    "vibe": lambda v, kit, ons: v if v in VIBES else _no("vibe"),
    "footage": lambda v, kit, ons: v if v is None or type(v) is bool else _no("footage"),
    "style": lambda v, kit, ons: v if v in STYLES or v == BROLL_STYLE else _no("style"),
    "sel": lambda v, kit, ons: _sel(v),
    "ask": lambda v, kit, ons: _text(v, 600),
    "feel": lambda v, kit, ons: _feel(v),
    # her v25 photo note: which photos they'd like in this reel, for the Assistant's pick (this reel's own)
    "photo_ask": lambda v, kit, ons: _text(v, PHOTO_ASK_MAX),
    # her v27: which kind of reel this is (bts | photos | broll), remembered per reel (ours; hers reads the address)
    "kind": lambda v, kit, ons: v if v in KINDS else _no("kind"),
    # her v27: how they'd like the edit to go ("Would you like to direct this edit?"), for the Assistant
    "direct": lambda v, kit, ons: _text(v, DIRECT_MAX),
    # her v27: B-roll's words on screen, where they were dragged and how big
    "onscreen": lambda v, kit, ons: _onscreen(v),
}


def _no(what):
    raise Refused(what)


def _bad(words=NOT_UNDERSTOOD, code=400, **more):
    d = {"ok": False, "words": words}
    d.update(more)
    return code, d


def _other_reel(body, rec):
    """A page says which reel it has open ("reel"). True when that is no longer the reel being worked on (another
    window started or opened another): nothing of that page's may be written into this reel. A page that does
    not say is taken as before."""
    got = body.get("reel")
    return got is not None and got != reels.current(rec, REEL_FIRST)


def save_from_page(body):
    """One save from the page. Returns (status, answer). Checks, in order: the kit, the numbered list's stamp,
    the counter the page had last seen, then every field it sent (the whole save is refused if any one is
    wrong, and nothing is written).

    The counter is this file's alone; an accepted save moves it on by one and the answer carries it. A save is
    taken only from a page that has seen the stored record: its "base" is the stored counter, or the stored
    record is that same page's own last save from that same base (its answer never arrived). Anything else is
    told there is something newer, and given it (REV_CHECK; with it off, the last save wins, as hers does).
    Sending exactly what is stored writes nothing."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    if set(body) - {"kit", "stamp", "base", "page", "saved", "reel"}:
        return _bad()
    if "reel" in body and not (isinstance(body["reel"], str) and reels.ID.fullmatch(body["reel"])):
        return _bad()
    base, page, sent = body.get("base"), body.get("page"), body.get("saved")
    if type(base) is not int or base < 0 or not isinstance(page, str) or not PAGE_ID.fullmatch(page):
        return _bad()
    if not isinstance(sent, dict) or not sent or set(sent) - set(SAVE_FIELDS):
        return _bad()
    with arrange.locked(lock_path(kit)):
        rec, rows, stamp = sync(kit)
        if not rows:
            return _bad(NOT_READY, 404)
        if body.get("stamp") != stamp:
            return _bad(OUR_WORDS["photos_changed"], 409, why="photos")
        other = _other_reel(body, rec)
        on_sheet = {x["n"] for x in rows}
        stored = rec.get("saved") if isinstance(rec.get("saved"), dict) else {}
        try:
            clean = {}
            for k, v in sent.items():
                if k == "song" and isinstance(v, str) and v and v == stored.get("song"):
                    clean[k] = v           # the song saved before stays as it is, even if its file went a moment ago
                else:
                    clean[k] = SAVE_FIELDS[k](v, kit, on_sheet)
        except Refused:
            return _bad()
        # More than a reel holds is refused, with one way through: an order that is ALREADY that long (an
        # older pick of Claude's) may be re-ordered and made shorter here, never longer.
        longest = len(assistant_pick(kit, rec, None, on_sheet))
        for key in ("picks", "mine_picks"):
            if isinstance(clean.get(key), list) and len(clean[key]) > max(MAX_PICKS, longest, len(stored.get(key) or [])):
                return _bad(OUR_WORDS["too_many"], 400, why="many")
        rev = int(rec.get("rev") or 0)
        if not other and all(stored.get(k) == v for k, v in clean.items()):
            return 200, {"ok": True, "rev": rev}      # what is stored already: nothing to write
        src = rec.get("from") if isinstance(rec.get("from"), dict) else {}
        own = src.get("page") == page and src.get("base") == base
        if not other and not (REV_CHECK and base != rev and not own):
            new = dict(stored)
            new.update(clean)
            new["updated"] = time.time()
            rec["saved"] = new
            rec["rev"] = rev + 1
            rec["from"] = {"page": page, "base": base}
            _stamp_names(rec, rows, stamp)
            save(kit, rec)
            return 200, {"ok": True, "rev": rev + 1}
    st = state(kit)
    return _bad(OUR_WORDS["newer"], 409, why="newer", state=st)


# ---------- Make my reel: a job of its own (hers: one long request to bts_reel.py) ----------
# The page asks for a reel (POST /reel-make) and is given a job; a process of its own makes it (reel_page.py job),
# writing how it is going to <kit>/.kit/reel-job.json, which the page reads (GET /reel-job) until it is done. One
# job per shoot at a time; one reel made at a time on this computer (the job waits its turn for MAKE_LOCK, as hers
# waited for her MAKE_LOCK); at most MAKE_LIMIT seconds. Only her kinds of lines reach the page, never a path.

_JOB_ROUTE = threading.Lock()


def job_path(kit):
    return kit / ".kit" / JOB


def job_lock_path(kit):
    return kit / ".kit" / JOB_LOCK


def read_job(kit):
    try:
        j = json.loads(job_path(kit).read_text(encoding="utf-8"))
        return j if isinstance(j, dict) else None
    except (OSError, ValueError):
        return None


def write_job(kit, j):
    arrange.write_whole(job_path(kit), j)


def job_running(kit):
    """Is a job's process at work on this shoot right now? It holds .kit/reel-job.lock for as long as it lives;
    asking tries to share that lock for an instant (arrange.job_running's way). Where a drive has no locks, the
    job's own process number is asked after instead, for at most MAKE_LIMIT and a minute."""
    try:
        arrange.make_folder(job_lock_path(kit).parent)
        with open(job_lock_path(kit), "a", encoding="utf-8") as f:       # never written to: only looked at
            got = this_computer.try_lock(f, shared=True)
            if got is False:
                return True
            if got:
                this_computer.unlock(f)
                return False
    except OSError:
        pass
    j = read_job(kit) or {}
    if j.get("state") not in ("queued", "running"):
        return False
    return time.time() - float(j.get("t0") or j.get("t") or 0) < MAKE_LIMIT + 60 and arrange._pid_alive(j.get("pid"))


def job_for_page(kit):
    """The newest job as the page sees it: {id, state (queued, running, done, problem), dry, project, words,
    problem, short_song}. A job that says it is at work but is not (stopped, or the computer was turned off) is a
    problem, in plain words. No path, no file name, no process number."""
    j = read_job(kit)
    if not j or not isinstance(j.get("id"), str) or j.get("state") not in ("queued", "running", "done", "problem"):
        return None
    state, problem = j["state"], j.get("problem")
    video = bool(j.get("video"))             # Save my video's job (her v27): its own words, and the file it made
    if state in ("queued", "running"):
        began = float(j.get("t0") or 0)
        if began and time.time() - began > (VIDEO_LIMIT if video else MAKE_LIMIT) + JOB_GRACE:
            # past its time, whatever its lock says (v19 review: a hung job held its lock, and the page spun forever)
            state, problem = "problem", (OUR_WORDS["video_too_long"] if video else WORDS["too_long"])
        elif not job_running(kit) and (state == "running" or j.get("pid") or time.time() - float(j.get("t") or 0) > JOB_BOOT):
            state, problem = "problem", (OUR_WORDS["video_interrupted"] if video else OUR_WORDS["interrupted"])
        if state == "problem" and not video:
            made = _made_by(kit, j["id"])
            if made:              # CapCut has it: never say nothing was made (rule 7)
                problem = OUR_WORDS["interrupted_made"].replace("{project}", made)
    words = [w for w in (j.get("words") or []) if isinstance(w, str)]
    out = {"id": j["id"], "state": state, "dry": bool(j.get("dry")), "project": j.get("project") if state == "done" else None,
           "words": words if state == "done" else [], "problem": problem if state == "problem" else None,
           "short_song": bool(j.get("short_song")) and state == "problem"}
    if video:
        out["kind"] = "video"
        if state == "done":
            out["video"] = j.get("video") if isinstance(j.get("video"), str) else None
            out["seconds"] = j.get("seconds")
    if state == "done" and not j.get("dry") and j.get("capcut_say"):
        out["capcut_say"] = j["capcut_say"]
    return out


def _made_by(kit, jid):
    """The CapCut project a job made, when reel.py had finished it (its --status says so for this job) though the
    job was stopped before writing it down; else None. A name only, never a path."""
    try:
        st = json.loads((kit / ".kit" / JOB_STATUS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(st, dict) and st.get("for") == jid and st.get("ok") and not st.get("dry") and isinstance(st.get("project"), str):
        return st["project"]
    return None


def made_for(m):
    """Which reel a "made" entry belongs to (hers: old entries count as v1)."""
    v = m.get("version") if isinstance(m, dict) else None
    return v if isinstance(v, str) and reels.ID.fullmatch(v) else reels.FIRST_ID


def mix_number(made, picks, vibe, style, which):
    """Hers (her "variation"): how many reels of the same photos, vibe and footage style were made before, so the
    next is the next mix. Of the same reel (ours): two reels of one shoot that hold the same photos each start
    at their own first mix."""
    return sum(1 for m in made or [] if isinstance(m, dict) and m.get("picks") == picks and m.get("vibe") == vibe
               and m.get("footage") == style and made_for(m) == which)


def capcut_say(st):
    """The line under "It's in CapCut": hers when the reel is in CapCut's list (or a Mac's open CapCut adds it by
    itself); else ours, saying what to do (v19 review)."""
    if st.get("listed") or st.get("left_to_capcut") or ("listed" not in st and "waiting" not in st):
        return WORDS["open_capcut_say"]
    return _capcut_words("waiting" if st.get("waiting") else "not_listed")


def _picks_text(lst):
    return ",".join(f"{x['n']}{x['h']}" for x in lst)


def _mix(v):
    """Try another mix's number (her "variation"), or None when the page sent none."""
    if v is None:
        return None
    if type(v) is not int or not 0 <= v <= MIX_MOST:
        raise Refused("variation")
    return v


def _song_start(v):
    """Where the song starts (her "song_start", from Another part of this song), or None for the Assistant's own
    choice. A number of seconds, not past anything a song could be; the song's own length is checked at the make."""
    if v is None:
        return None
    if type(v) not in (int, float) or v != v or not 0 <= v <= 36000:
        raise Refused("song_start")
    return float(v)


def _ask_from_page(body, kit, allowed):
    """What Make my reel and the watch step's preview share (her /reel/make and /reel/preview take the same body):
    every field checked, as a save is. Returns (ask, page_rec) or (status, answer) when refused."""
    if set(body) - allowed:
        return _bad()
    if "reel" in body and not (isinstance(body["reel"], str) and reels.ID.fullmatch(body["reel"])):
        return _bad()
    rows = arrange.sheet_rows(kit)
    if not rows:
        return _bad(NOT_READY, 404)
    if body.get("stamp") != arrange.sheet_stamp(kit):
        return _bad(OUR_WORDS["photos_changed"], 409, why="photos")
    on_sheet = {x["n"] for x in rows}
    footage, style, clips = body.get("footage", False), body.get("style", "first"), body.get("clips")
    if type(footage) is not bool or (style not in STYLES and style != BROLL_STYLE):
        return _bad()
    broll = footage and style == BROLL_STYLE
    try:
        picks = _picks(body.get("picks"), on_sheet)
        variation, start = _mix(body.get("variation")), _song_start(body.get("song_start"))
    except Refused:
        return _bad()
    if not picks and not broll:                  # her v27: B-roll needs no photos
        return _bad(WORDS["pick_photos"])
    if len(picks) > MAX_PICKS:
        return _bad(OUR_WORDS["too_many"], 400, why="many")
    vibe = body.get("vibe")
    if vibe not in VIBES:
        return _bad(WORDS["pick_vibe"])
    song = body.get("song")
    if song is not None and (not isinstance(song, str) or (song and not SONG_ID.fullmatch(song))):
        return _bad()
    if song and song not in song_ids(kit):
        return _bad(WORDS["song_gone"], 400, why="song")
    if clips is not None and (not isinstance(clips, list) or len(clips) > MAX_CLIPS
                              or any(not isinstance(x, str) or not MOMENT_ID.fullmatch(x) for x in clips)):
        return _bad()
    with arrange.locked(lock_path(kit)):
        page_rec = load(kit)
    if _other_reel(body, page_rec):
        return _bad(OUR_WORDS["newer"], 409, why="newer", state=state(kit))
    if footage and not moments_of(page_rec):
        return _bad(WORDS["no_moments"].replace("{_}", ""), 400, why="footage")
    # which reel this is, written down with the job: the reel is made from that reel's clips and noted as that
    # reel's, also when they open another while it is being made. Only once the shoot has more than one.
    which = {"reel": reels.current(page_rec, REEL_FIRST)} if reels.several(page_rec) else {}
    ask = {"picks": _picks_text(picks), "song": song, "vibe": vibe, "stamp": body.get("stamp"),
           "footage": style if footage else None, "clips": list(clips) if footage and clips is not None else None, **which}
    if variation is not None:
        ask["variation"] = variation
    if start is not None:
        ask["song_start"] = start
    return ask, page_rec


def start_make(body):
    """POST /reel-make: {kit, stamp, picks: [{n, h}], song: an id, "" for No song, vibe, test, footage, style,
    clips, variation, song_start}. Checked the way a save is; then the job is written down and its process
    started. (status, answer). Since her v27 the watch step's "Make this one in CapCut" sends the mix that was
    watched (variation) and where the song starts (song_start), so CapCut gets exactly what played."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    got = _ask_from_page(body, kit, {"kit", "stamp", "picks", "song", "vibe", "test", "footage", "style", "clips", "reel",
                                     "variation", "song_start"})
    if not isinstance(got[0], dict):
        return got
    ask, page_rec = got
    if ask.get("song") is None:
        return _bad(re.sub(r"<[^>]+>", "", WORDS["need_song_html"]), 400, why="song")
    test = body.get("test", False)
    if type(test) is not bool:
        return _bad()
    ask["dry"] = test
    with _JOB_ROUTE:
        j = read_job(kit) or {}
        if job_running(kit) or (j.get("state") == "queued" and not j.get("pid") and time.time() - float(j.get("t") or 0) < JOB_BOOT):
            return 409, {"ok": False, "words": OUR_WORDS["already_making"], "why": "making", "job": job_for_page(kit)}
        jid = os.urandom(6).hex()
        write_job(kit, {"id": jid, "state": "queued", "t": time.time(), "dry": test, "ask": ask})
        try:
            arrange.HOME.mkdir(parents=True, exist_ok=True)
            with open(arrange.LOG, "a", encoding="utf-8") as out:
                # a Mac: start_new_session; a PC: no window, a process group of its own (as the slide job)
                this_computer.popen_detached([sys.executable, str(HERE / "reel_page.py"), "job", str(kit), "--id", jid],
                                             stdout=out, stderr=subprocess.STDOUT, **arrange._child_env())
        except OSError as e:
            arrange.log(f"reel page: the reel's job could not be started: {e}")
            write_job(kit, {"id": jid, "state": "problem", "t": time.time(), "dry": test, "problem": WORDS["went_wrong_make"]})
        return 200, {"ok": True, "job": job_for_page(kit)}


def her_plan_line(p):
    """Her Plan line (bts_reel.py), from the plan's own numbers (decision 5)."""
    w = WORDS
    fill = lambda text, **kw: re.sub(r"\{(\w+)\}", lambda m: str(kw.get(m.group(1), m.group(0))), text)   # noqa: E731
    clips, photos = int(p.get("clips") or 0), int(p.get("photos") or 0)
    what = (fill(w["plan_clip" if clips == 1 else "plan_clips"], n=clips) + w["plan_and"] if clips else "")
    what += fill(w["one_photo" if photos == 1 else "photos"], n=photos)
    line = w["plan_start"] + what + fill(w["plan_body"], secs=f"{float(p.get('length') or 0):.1f}")
    if p.get("song"):
        f = float(p.get("song_from") or 0)
        line += fill(w["plan_tempo"], bpm=round(float(p.get("tempo") or 0)))
        line += (w["plan_top"] if f < 1 else fill(w["plan_in"], s=f"{f:.0f}")) + "."
    else:
        line += w["plan_no_song"] + (w["plan_own_sound"] if clips else ".")
    return line


_PATHISH = re.compile(r"(/[^\s/]+){2,}|~/|[A-Za-z]:[\\/]|\\\\")    # two parts of a path, a home, a drive, a network share


def _no_path(line, known):
    """A line as the page may see it: any path we know of taken back to its last name; a path left after that, and
    the line is not for the page (None)."""
    for k in sorted({str(x) for x in known if x}, key=len, reverse=True):
        if k and k in line:
            line = line.replace(k, Path(k).name)
    line = re.sub(r"\s*\([^()]*[/\\][^()]*\)", "", line)        # "(<a folder>)" said in passing
    return None if _PATHISH.search(line) else line


def _her_lines(out, dry, plan, known):
    """The lines her page shows, from reel.py's words: her server's kinds, then her page's filter."""
    lines = [ln.strip() for ln in (out or "").splitlines() if ln.strip()]
    keep = [w for w in lines if (w.startswith(HER_KINDS) or " clip from " in w) and not w.startswith(NOT_SHOWN)]
    if dry:
        keep = [w for w in keep if not w.startswith(("Dry run", "Made"))]
    else:
        keep = [w for w in keep if w.startswith(SHOWN_MADE)]
    if PLAN_WORDS == "nicole" and plan:
        keep = [her_plan_line(plan) if w.startswith("Plan:") else w for w in keep]
    return [x for x in (_no_path(w, known) for w in keep) if x]


def _problem(out, known):
    """What stopped reel.py, in its own plain words (hers: the STOP line, or the last plain line)."""
    lines = [w.strip() for w in (out or "").splitlines() if w.strip()]
    stop = next((w for w in lines if w.startswith("STOP")), None) or (lines[-1] if lines else "")
    stop = re.sub(r"^STOP:\s*", "", stop)
    return (_no_path(stop, known) if stop else None) or WORDS["went_wrong_make"]


def _hold_make_lock(deadline):
    """MAKE_LOCK, waited for until deadline: the open file holding it, "none" where locks can't be had (the work
    goes on), or None when the wait ran out."""
    try:
        arrange.HOME.mkdir(parents=True, exist_ok=True)
        f = open(MAKE_LOCK, "a", encoding="utf-8")
    except OSError:
        return "none"
    while True:
        got = this_computer.try_lock(f)
        if got:
            return f
        if got is None:
            f.close()
            return "none"
        if time.time() > deadline:
            f.close()
            return None
        time.sleep(0.25)


_CHILD = []          # the reel.py at work for this job's process right now (the watchdog stops it with the job)


def _run_bounded(cmd, timeout, **kw):
    """subprocess.run with a hard limit on the program AND everything it starts: it runs as its own group
    (this_computer.popen_detached), and past its time the whole group is stopped (this_computer.stop_tree), not
    only reel.py (v19 review). (returncode, stdout, stderr); raises subprocess.TimeoutExpired."""
    p = this_computer.popen_detached(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace", **kw)
    _CHILD.append(p)
    try:
        out, err = p.communicate(timeout=max(1.0, timeout))
    except subprocess.TimeoutExpired:
        this_computer.stop_tree(p.pid)
        try:
            p.communicate(timeout=10)
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass
        raise
    finally:
        if p in _CHILD:
            _CHILD.remove(p)
    return p.returncode, out, err


def _make(kit, ask, jid, t0, preview=False, work=None, limit=None):
    """The work of one job. Returns what goes in the job record: {state, words, project, problem, short_song}.
    Everything, from the recording's sound to reel.py, is held to one deadline: t0 + MAKE_LIMIT.

    preview (her v27, Watch your reel before you make it): the same run as a dry one, in the preview's own
    working folder (PREVIEW_WORK) and held to PREVIEW_LIMIT, answering the pieces as the page plays them (a
    photo by its number, a clip by its video's key and where it starts) and where the song starts; nothing is
    written to the record. `work` and `limit`: a preview run in another folder of the kit's hidden one and held
    to another number of seconds (Save my video's plan, VIDEO_WORK and VIDEO_LIMIT)."""
    deadline = t0 + (limit if limit else (PREVIEW_LIMIT if preview else MAKE_LIMIT))
    rec_kit = kit_mod.load_rec(kit)
    photos = kit_mod.photos_dir(kit, rec_kit)
    short = short_name(kit.name)
    known = [kit, photos]          # paths whose last name means something to them; anything else is never shown
    song, song_name = None, ""
    if ask.get("capcut_song"):
        song_name = ask["capcut_song"]          # Claude's make only (decision 2): CapCut's own music is never on the page
    elif ask.get("song"):
        s = song_by_id(kit, ask["song"], rec_kit)
        if s is None:
            return {"state": "problem", "problem": WORDS["song_gone"]}
        song_name = s["path"].name
        if s["kind"] == "video":
            got, why = sound_for(kit, s, deadline)
            if not got:
                return {"state": "problem", "problem": why}
            song = got
        else:
            song = s["path"]
        known += [song]
    reel = _reel_module("reel")
    capcut = _reel_module("capcut")
    picks = ask["picks"]
    with arrange.locked(lock_path(kit)):
        page_rec = load(kit)
    # the reel this make is for (several reels, v25): the one the job was started on, else the one being worked on
    which = ask.get("reel") if isinstance(ask.get("reel"), str) else reels.current(page_rec, REEL_FIRST)
    try:
        page_rec = as_reel(page_rec, which)
    except reels.Wrong:
        return {"state": "problem", "problem": reels.GONE}
    made = page_rec.get("made") or []
    style = ask.get("footage") if ask.get("footage") in STYLES or ask.get("footage") == BROLL_STYLE else None
    # hers: the next reel of the same photos, vibe and footage style is the next mix (of the same reel, ours:
    # two reels of one shoot that happen to hold the same photos each start at their first mix); since her v27
    # the watch step says which mix it played, and that one is made
    variation = ask["variation"] if isinstance(ask.get("variation"), int) else mix_number(made, picks, ask["vibe"], style, which)
    # The numbers on the page are the kit's numbered list (.kit/sheet.json); reel.py is handed that same list in
    # its working folder, so a photo exported since can never shift a number to another photo.
    rows = arrange.sheet_rows(kit)
    if not rows or arrange.sheet_stamp(kit) != ask.get("stamp"):
        return {"state": "problem", "problem": OUR_WORDS["photos_changed"]}
    listing = [{"n": x["n"], "file": str(photos / arrange.photo_name(x)), "w": x.get("w") or 0, "h": x.get("h") or 0,
                "way": x.get("way") or ""} for x in rows]
    work = (kit / ".kit" / (work or PREVIEW_WORK)) if preview else (reel.kit_workdir(kit) or reel.workdir(rec_kit.get("name") or short, str(photos)))
    work.mkdir(parents=True, exist_ok=True)
    arrange.write_whole(work / "photos.json", {"folder": str(photos), "photos": listing})
    tokens, clip_list = picks, None
    if style:                                     # behind the scenes: her order for the style, clips among the photos
        order = [(int(x.rstrip("+-")), x[-1] if x[-1] in "+-" else "") for x in picks.split(",") if x]
        try:
            tokens, clip_list = footage_order(kit, page_rec, style, ask.get("clips"), order, {x["n"] for x in rows})
        except NoFootage as e:
            return {"state": "problem", "problem": str(e)}
        arrange.write_whole(work / "clips.json", {"clips": clip_list})
        known += [footage_dir(kit)]
    status = (work if preview else kit / ".kit") / JOB_STATUS
    arrange.write_whole(status, {"for": jid, "pending": True})     # reel.py keeps "for" when it writes what happened
    cmd = [sys.executable, str(kit_mod.REEL_PY), "make", "--folder", str(photos), "--shoot", rec_kit.get("name") or short,
           "--kit", str(kit), "--picks", tokens, "--vibe", ask["vibe"],
           *(["--clips", str(work / "clips.json")] if clip_list else []),
           *(["--capcut-song", ask["capcut_song"]] if ask.get("capcut_song") else ["--song", str(song) if song else "none"]),
           "--variation", str(variation), "--name", ask.get("name") or reel.kit_reel_name(kit.name, short), "--status", str(status)]
    if preview:
        cmd += ["--work", str(work)]
    if ask.get("hook"):
        cmd += ["--hook", ask["hook"]]          # Claude's make only (decision 15): words on the first photo, when they ask
    elif style == BROLL_STYLE and not preview:
        # her v27: B-roll's words on screen go into the CapCut project too, over the whole reel, as plain text
        ons = (page_rec.get("saved") or {}).get("onscreen") if isinstance(page_rec.get("saved"), dict) else None
        text = " ".join(str(ons.get("text") or "").split()) if isinstance(ons, dict) else ""
        if text:
            cmd += ["--hook", text, "--hook-whole"]
    start = None
    if song:
        length = capcut.song_length(str(song))
        if ask.get("song_start") is not None:         # her v27: the part of the song they watched, exactly
            start = float(ask["song_start"])
            if length and start > max(0.0, length - PART_END):
                return {"state": "problem", "problem": OUR_WORDS["song_start_past"]}
            cmd += ["--song-start", "%.3f" % (math.floor(start * 1000) / 1000)]   # never a hair past the beat it names
        else:
            start = short_song_start(song, length)
            if start is not None:
                cmd += ["--song-start", "%.2f" % start]   # decision 8 and her v25: a short song starts at the top, or
                                                          # after the silence a screen recording opens with
    if ask.get("dry") or preview:
        cmd.append("--dry-run")
    left = deadline - time.time()
    if left <= 1:
        return {"state": "problem", "problem": WORDS["too_long"]}
    try:
        rc, r_out, r_err = _run_bounded(cmd, left, cwd=str(kit_mod.REEL_PY.parent))
    except subprocess.TimeoutExpired:
        return {"state": "problem", "problem": WORDS["too_long"]}
    try:
        st = json.loads(status.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    if st.get("pending") or not isinstance(st, dict):
        st = {}
    out = (r_out or "") + "\n" + (r_err or "")
    if rc != 0 or not st.get("ok"):
        arrange.log(f"reel page: reel.py stopped ({rc}): {out.strip()[-400:]}")
        return {"state": "problem", "problem": _problem(r_out or out, known), "short_song": bool(st.get("short_song"))}
    dry = bool(ask.get("dry")) or preview
    words = _her_lines(r_out, dry, st.get("plan"), known)
    if preview:
        return {"state": "done", "words": words, "pieces": _preview_pieces(st.get("pieces"), clip_list),
                "length": (st.get("plan") or {}).get("length"), "variation": variation,
                "song": ({"id": ask.get("song") or "", "from": st["song"].get("from"), "length": st["song"].get("length")}
                         if isinstance(st.get("song"), dict) else None),
                # Save my video's render needs the clips themselves and the song's file: never sent to a page
                "clip_list": clip_list, "song_file": song, "song_name": song_name}
    project = st.get("project")
    if not dry and project:
        with arrange.locked(lock_path(kit)):
            rec = load(kit)
            entry = {"project": project, "picks": picks, "vibe": ask["vibe"], "footage": style,
                     "clips": [c["moment"] for c in clip_list] if clip_list else None,
                     "song": song_name, "song_id": ask.get("song") or "", "when": time.time(),
                     # her v27: which mix it was and where the song started, as the watch step played it
                     "variation": variation, "song_start": (st.get("song") or {}).get("from") if isinstance(st.get("song"), dict) else None}
            if reels.several(rec):
                entry["version"] = which        # hers: which reel it was; an entry without one is the first reel's
            rec.setdefault("made", []).append(entry)
            save(kit, rec)
        try:                     # the kit's own record of its reel, through its command (kit.json is only theirs to write)
            k = subprocess.run([sys.executable, str(HERE / "kit.py"), "reel-made", str(kit), "--project", project, "--picks", picks],
                               capture_output=True, encoding="utf-8", errors="replace", timeout=60)
            if k.returncode != 0:
                arrange.log(f"reel page: kit.py reel-made said: {(k.stdout + k.stderr).strip()[-300:]}")
        except (OSError, subprocess.SubprocessError) as e:
            arrange.log(f"reel page: kit.py reel-made could not run: {e}")
    return {"state": "done", "words": words, "project": project, "capcut_say": None if dry else capcut_say(st)}


def _preview_pieces(pieces, clip_list):
    """reel.py's pieces as the page plays them: a photo by its number, a clip by its video's key, its id and where
    it starts in its video; never a path."""
    out = []
    for p in pieces if isinstance(pieces, list) else []:
        one = {"kind": p.get("kind"), "start": p.get("start"), "dur": p.get("dur"), "fill": bool(p.get("fill", True))}
        if p.get("kind") == "clip":
            c = (clip_list or [])[int(p.get("c") or 0) - 1] if clip_list and 1 <= int(p.get("c") or 0) <= len(clip_list) else {}
            one.update(key=c.get("key"), id=c.get("moment"), src=p.get("src"))
        else:
            one["n"] = p.get("n")
        out.append(one)
    return out


# ---------- Save my video (her v27, B-roll): the finished MP4 with the words on it, as a job ----------

def reels_dir(kit):
    """Her <shoot>/Reels, where a saved video goes (made when the first is saved; never a link)."""
    return kit / REELS


def reels_ok(kit):
    d = reels_dir(kit)
    return not d.is_symlink() and (d.is_dir() or not d.exists())


def video_stem(kit, rec):
    """Hers (server.py broll_video): "<short> B-roll", with " - <reel name>" when the shoot has several reels;
    anything a file name can't carry becomes a space."""
    short = short_name(kit.name)
    if reels.several(rec):
        stem = VIDEO_WORDS["file_reel"].replace("{short}", short).replace("{reel}", reels.name_of(rec, reels.current(rec, REEL_FIRST), REEL_FIRST))
    else:
        stem = VIDEO_WORDS["file"].replace("{short}", short)
    return " ".join(re.sub(r'[/\\:*?"<>|]+', " ", stem).split())


def free_video_name(kit, stem, after=0):
    """Hers: never over an earlier one. "<stem>.mp4", then "<stem> 2.mp4", "<stem> 3.mp4"...; `after`: the number
    to start past (a name that was taken while the video was being made). A name is taken whatever its case (a
    Mac's drive keeps one of "B-roll.mp4" and "b-roll.mp4"). (name, number), or (None, number) when the folder
    holds too many."""
    d = reels_dir(kit)
    try:
        there = {p.name.lower() for p in d.iterdir()} if d.is_dir() else set()
    except OSError:
        there = set()
    k = max(2, after + 1) if after else 1
    while k <= VIDEO_NAME_SPARES + 1:
        name = f"{stem}.mp4" if k == 1 else f"{stem} {k}.mp4"
        if name.lower() not in there and not (d / name).exists():
            return name, k
        k += 1
    return None, k


def made_videos(rec):
    """{reel id: the newest video saved of it (its file name)} for every reel of the shoot with one."""
    out = {}
    for m in rec.get("made") or []:
        if isinstance(m, dict) and isinstance(m.get("video"), str) and m["video"]:
            out[made_for(m)] = m["video"]
    return out


def save_video_from_page(body):
    """POST /reel-video (her v27, Save my video): {kit, stamp, song, clips, variation, song_start, onscreen, reel}.
    Checked the way Make my reel is (the same body, through _ask_from_page); only a B-roll reel (clips only) can be
    saved whole; the words come with the press (checked field by field, as a save is) or from the record. On a PC
    the plain words of the gap (this_computer.NO_VIDEO_PC) and nothing is started. Otherwise the job is written
    down and its process started, and the page follows it on /reel-job. (status, answer)."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    ons = body.get("onscreen")
    if ons is not None:
        try:
            ons = _onscreen(ons)
        except Refused:
            return _bad()
    body = {k: v for k, v in body.items() if k != "onscreen"}
    # hers sends the song, the clips, the mix, the song's start and the words: B-roll has no photos and no pace
    # chips, so the pick is empty and the pace is the reel's saved one (the cut the watch step played)
    with arrange.locked(lock_path(kit)):
        rec0 = load(kit)
    try:
        saved0 = as_reel(rec0, body.get("reel") if isinstance(body.get("reel"), str) else None).get("saved")
    except reels.Wrong:
        saved0 = None
    saved0 = saved0 if isinstance(saved0, dict) else {}
    body.setdefault("picks", [])
    if "vibe" not in body:
        body["vibe"] = saved0.get("vibe") if saved0.get("vibe") in VIBES else default_vibe()
    got = _ask_from_page(dict(body, footage=True, style=BROLL_STYLE), kit,
                         {"kit", "stamp", "picks", "song", "vibe", "footage", "style", "clips", "reel", "variation", "song_start"})
    if not isinstance(got[0], dict):
        return got
    ask, page_rec = got
    saved = page_rec.get("saved") if isinstance(page_rec.get("saved"), dict) else {}
    if reel_kind(saved) != BROLL_STYLE or (body.get("style") not in (None, BROLL_STYLE)) or body.get("footage") is False:
        return _bad(OUR_WORDS["video_broll_only"], 400, why="kind")
    if not ask.get("clips"):
        return _bad(VIDEO_WORDS["no_clips"], 400, why="clips")
    if not _video().avfoundation_here():
        return 200, {"ok": False, "pc": True, "words": this_computer.NO_VIDEO_PC}
    if not reels_ok(kit):
        return _bad(OUR_WORDS["cant_open_reels"], 400, why="reels")
    if ask.get("song") is None:
        ask["song"] = ""                       # hers: no song picked plays the clips' own sound
    ask["dry"] = True
    ask["video"] = True
    if ons is not None:
        ask["onscreen"] = ons
    with _JOB_ROUTE:
        j = read_job(kit) or {}
        if job_running(kit) or (j.get("state") == "queued" and not j.get("pid") and time.time() - float(j.get("t") or 0) < JOB_BOOT):
            words = OUR_WORDS["video_making"] if j.get("video") else OUR_WORDS["already_making"]
            return 409, {"ok": False, "words": words, "why": "making", "job": job_for_page(kit)}
        jid = os.urandom(6).hex()
        write_job(kit, {"id": jid, "state": "queued", "t": time.time(), "dry": True, "video": True, "ask": ask})
        try:
            arrange.HOME.mkdir(parents=True, exist_ok=True)
            with open(arrange.LOG, "a", encoding="utf-8") as out:
                this_computer.popen_detached([sys.executable, str(HERE / "reel_page.py"), "job", str(kit), "--id", jid],
                                             stdout=out, stderr=subprocess.STDOUT, **arrange._child_env())
        except OSError as e:
            arrange.log(f"reel page: the video's job could not be started: {e}")
            write_job(kit, {"id": jid, "state": "problem", "t": time.time(), "dry": True, "video": True, "problem": WORDS["went_wrong_make"]})
        return 200, {"ok": True, "job": job_for_page(kit)}


def _make_video(kit, ask, jid, t0):
    """The work of a Save my video job: the reel's plan from a dry run of reel.py (the very cut the watch step
    played: the mix and the part of the song), then video.render_broll into <shoot>/Reels under a free name
    chosen first and never written over; the made entry carries the video's file name (Lane D's contract). What
    goes in the job record: {state, video, seconds, words} or {state: problem, problem}."""
    deadline = t0 + VIDEO_LIMIT
    plan_ask = {k: v for k, v in ask.items() if k not in ("video", "onscreen")}
    res = _make(kit, plan_ask, jid, t0, preview=True, work=VIDEO_WORK, limit=VIDEO_LIMIT)
    if res.get("state") != "done":
        return {"state": "problem", "problem": res.get("problem") or WATCH_WORDS["pv_cant"], "short_song": bool(res.get("short_song"))}
    clip_list = res.get("clip_list") or []
    pieces = [p for p in res.get("pieces") or [] if p.get("kind") == "clip"]
    if not clip_list or len(pieces) != len(clip_list):
        return {"state": "problem", "problem": VIDEO_WORDS["no_clips"]}
    clips = [{"path": c["path"], "src": p.get("src") if p.get("src") is not None else c.get("src", 0), "dur": p["dur"]}
             for c, p in zip(clip_list, pieces)]
    song_file, song_from = res.get("song_file"), (res.get("song") or {}).get("from") or 0
    with arrange.locked(lock_path(kit)):
        rec = load(kit)
    try:
        page_rec = as_reel(rec, ask.get("reel") if isinstance(ask.get("reel"), str) else reels.current(rec, REEL_FIRST))
    except reels.Wrong:
        return {"state": "problem", "problem": reels.GONE}
    saved = page_rec.get("saved") if isinstance(page_rec.get("saved"), dict) else {}
    words = ask.get("onscreen") if isinstance(ask.get("onscreen"), dict) else (saved.get("onscreen") if isinstance(saved.get("onscreen"), dict) else None)
    d = reels_dir(kit)
    if not reels_ok(kit):
        return {"state": "problem", "problem": OUR_WORDS["cant_open_reels"]}
    try:
        d.mkdir(exist_ok=True)
    except OSError:
        return {"state": "problem", "problem": OUR_WORDS["cant_open_reels"]}
    stem = video_stem(kit, rec)
    name, k = free_video_name(kit, stem)
    if name is None:
        return {"state": "problem", "problem": OUR_WORDS["video_many"].replace("{n}", str(VIDEO_NAME_SPARES + 1))}
    note = ""
    for _try in range(2):                   # the name was chosen first; if it was taken while rendering, the next one (once)
        left = deadline - time.time()
        if left <= 1:
            return {"state": "problem", "problem": OUR_WORDS["video_too_long"]}
        r = _video().render_broll(clips, d / name, song_file, song_from, words, timeout=left, work=kit / ".kit" / VIDEO_WORK)
        if not r.get("ok"):
            if r.get("state") == "exists":
                name, k = free_video_name(kit, stem, after=k)
                if name is None:
                    return {"state": "problem", "problem": OUR_WORDS["video_many"].replace("{n}", str(VIDEO_NAME_SPARES + 1))}
                continue
            arrange.log(f"reel page: the video could not be made: {r.get('state')} {str(r.get('detail') or '')[:300]}")
            return {"state": "problem", "problem": OUR_WORDS["video_too_long"] if r.get("state") == "busy" else r.get("words") or WORDS["went_wrong_make"]}
        if r.get("placed"):
            break
        note = OUR_WORDS["video_name_taken"]
        name, k = free_video_name(kit, stem, after=k)
        if name is None:
            return {"state": "problem", "problem": OUR_WORDS["video_many"].replace("{n}", str(VIDEO_NAME_SPARES + 1))}
    else:
        return {"state": "problem", "problem": WORDS["went_wrong_make"]}
    which = ask.get("reel") if isinstance(ask.get("reel"), str) else None
    with arrange.locked(lock_path(kit)):
        rec = load(kit)
        entry = {"video": name, "picks": "", "vibe": ask.get("vibe"), "footage": BROLL_STYLE,
                 "clips": [c["moment"] for c in clip_list], "song": res.get("song_name") or "", "song_id": ask.get("song") or "",
                 "when": time.time(), "variation": res.get("variation"), "song_start": song_from if song_file else None,
                 "seconds": r.get("seconds")}
        if reels.several(rec):
            entry["version"] = which or reels.current(rec, REEL_FIRST)
        rec.setdefault("made", []).append(entry)
        save(kit, rec)
    out = {"state": "done", "video": name, "seconds": r.get("seconds"), "words": list(res.get("words") or [])}
    if note:
        out["words"].append(note)
    return out


_PREVIEWS = {}                 # kit -> the lock that keeps its previews one at a time
_PREVIEWS_LOCK = threading.Lock()


def _preview_lock(kit):
    with _PREVIEWS_LOCK:
        return _PREVIEWS.setdefault(str(kit), threading.Lock())


def preview_from_page(body):
    """POST /reel-preview (her v27, Watch your reel before you make it): the same body Make my reel takes, with the
    mix (variation) and where the song starts (song_start); a dry run of reel.py in the preview's own folder,
    one at a time for a shoot and held to PREVIEW_LIMIT seconds; nothing is made and nothing is written to the
    record. Answers {ok, pieces, length, song: {id, from, length}, words, variation}, no path in it; a reel that
    can't be cut answers her problem line (ok false, problem). (status, answer)."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    got = _ask_from_page(body, kit, {"kit", "stamp", "picks", "song", "vibe", "footage", "style", "clips", "reel",
                                     "variation", "song_start"})
    if not isinstance(got[0], dict):
        return got
    ask, _page_rec = got
    if ask.get("song") is None:
        ask["song"] = ""                       # hers: not picked yet plays with no song; Make my reel still asks for one
    t0 = time.time()
    lock = _preview_lock(kit)
    if not lock.acquire(timeout=PREVIEW_LIMIT):
        return 200, {"ok": False, "problem": WATCH_WORDS["pv_couldnt"]}
    try:
        res = _make(kit, ask, "preview", t0, preview=True)
    finally:
        lock.release()
    if res.get("state") != "done":
        return 200, {"ok": False, "problem": res.get("problem") or WATCH_WORDS["pv_cant"], "short_song": bool(res.get("short_song"))}
    return 200, {"ok": True, "pieces": res["pieces"], "length": res["length"], "song": res["song"], "words": res["words"],
                 "variation": res["variation"]}


_JOB_WRITE = threading.Lock()


def _watchdog(kit, jid, deadline, finished):
    """The job's hard limit (v19 review): at deadline and JOB_GRACE, if the job is still at work (a song file that
    won't read, a step that hangs), it is written down as too long, and this process, the reel.py it started and
    everything they started are stopped. The page then says so, and the next Make my reel can go ahead."""
    left = deadline + JOB_GRACE - time.time()
    if finished.wait(max(0.0, left)):
        return
    with _JOB_WRITE:
        if finished.is_set():
            return
        j = read_job(kit) or {}
        if j.get("id") == jid and j.get("state") in ("queued", "running"):
            j.update(state="problem", problem=(OUR_WORDS["video_too_long"] if j.get("video") else WORDS["too_long"]), t=time.time())
            made = None if j.get("video") else _made_by(kit, jid)
            if made:
                j["problem"] = OUR_WORDS["interrupted_made"].replace("{project}", made)
            try:
                write_job(kit, j)
            except OSError:
                pass
        arrange.log(f"reel page: a reel's job ran past {MAKE_LIMIT + JOB_GRACE} s and was stopped")
        for p in list(_CHILD):
            this_computer.stop_tree(p.pid)
        this_computer.stop_tree(os.getpid())     # a Mac: its whole group when it leads one (popen_detached); a PC: its tree
        os._exit(1)


def cmd_job(kit, jid):
    """The job's own process (started by the page server). Holds the job's lock for as long as it lives."""
    t0 = time.time()
    arrange._own_output()
    try:
        arrange.make_folder(job_lock_path(kit).parent)
        f = open(job_lock_path(kit), "a", encoding="utf-8")
    except OSError:
        f = None
    got = None
    if f is not None:
        end = time.time() + 3.0                     # a page asking "is it running?" holds it for an instant: wait that out
        while True:
            got = this_computer.try_lock(f)
            if got is not False or time.time() > end:
                break
            time.sleep(0.05)
    if got is False:
        f.close()
        return 0                                    # another job's process has it
    try:
        j = read_job(kit) or {}
        if j.get("id") != jid or j.get("state") != "queued":
            return 0
        ask = j.get("ask") or {}
        j.update(pid=os.getpid(), t0=t0, t=time.time())
        write_job(kit, j)
        finished = threading.Event()
        limit = VIDEO_LIMIT if ask.get("video") else MAKE_LIMIT
        threading.Thread(target=_watchdog, args=(kit, jid, t0 + limit, finished), daemon=True).start()
        g = _hold_make_lock(t0 + limit)
        if g is None:
            j.update(state="problem", problem=WORDS["too_long"], t=time.time())
            write_job(kit, j)
            return 1
        try:
            j.update(state="running", t=time.time())
            write_job(kit, j)
            try:
                res = _make_video(kit, ask, jid, t0) if ask.get("video") else _make(kit, ask, jid, t0)
            except Exception as e:  # noqa: BLE001  (whatever happens, the page is told in plain words)
                arrange.log(f"reel page: the reel's job failed: {e.__class__.__name__}: {str(e)[:300]}")
                res = {"state": "problem", "problem": WORDS["went_wrong_make"]}
            with _JOB_WRITE:
                finished.set()
                j.update(res, t=time.time())
                write_job(kit, j)
        finally:
            if g != "none":
                this_computer.unlock(g)
                g.close()
        return 0 if j.get("state") == "done" else 1
    finally:
        if f is not None:
            if got:
                this_computer.unlock(f)
            f.close()


# ---------- the folder buttons and Open CapCut ----------

def _open_folder(path):
    """finder.open_folder, or, in a test (TEST_OPEN), nothing opened and the answer as if it had been."""
    t = os.environ.get(TEST_OPEN)
    if t:
        arrange.log(f"reel page (test): would open {Path(path).name}")
        return (t != "fail"), ("behind" if t == "behind" else "" if t != "fail" else "test")
    import finder
    return finder.open_folder(path)


def open_photos(kit):
    """Her v27 + Add photos: opens the shoot's Photos folder (the one the kit's record names; read only, never
    made here) and says her line. The page then notices the new photos by itself (relist_if_changed)."""
    try:
        folder = kit_mod.photos_dir(kit, kit_mod.load_rec(kit))
        ok_folder = folder.is_dir() and not folder.is_symlink()
    except (OSError, ValueError, TypeError, AttributeError):
        ok_folder = False
    if not ok_folder:
        return 200, {"ok": False, "words": pc_words(WORDS["cant_open_photos"])}
    ok, note = _open_folder(folder)
    if not ok:
        arrange.log(f"reel page: the Photos folder couldn't be opened: {str(note)[:200]}")
        return 200, {"ok": False, "words": pc_words(WORDS["cant_open_photos"])}
    w = pc_words(WORDS["photos_open"])
    if note == "behind":
        first, rest = w.split(". ", 1)
        w = first + OUR_WORDS["behind"] + " " + rest
    return 200, {"ok": True, "words": w}


def open_reels(kit):
    """Her v27 Open the folder, after Save my video: opens the shoot's Reels folder (only once a video has been
    saved into it; never made here, never a link) and says so in our words (hers says nothing)."""
    d = reels_dir(kit)
    if not (d.is_dir() and not d.is_symlink()):
        return 200, {"ok": False, "words": pc_words(OUR_WORDS["cant_open_reels"])}
    ok, note = _open_folder(d)
    if not ok:
        arrange.log(f"reel page: the Reels folder couldn't be opened: {str(note)[:200]}")
        return 200, {"ok": False, "words": pc_words(OUR_WORDS["cant_open_reels"])}
    w = pc_words(OUR_WORDS["reels_open"])
    if note == "behind":
        w = w.rstrip(".") + OUR_WORDS["behind"]
    return 200, {"ok": True, "words": w}


def open_music(body):
    """POST /reel-open {kit, what: "music" | "footage" | "photos" | "reels"}: makes <kit>/Music (or <kit>/Footage) if it
    isn't there, and opens it (hers: /music/open and /footage/open); "photos" (her v27) opens the shoot's Photos
    folder as it is; "reels" (her v27, Open the folder after Save my video) the shoot's Reels folder as it is."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    if set(body) - {"kit", "what"} or body.get("what") not in ("music", "footage", "photos", "reels"):
        return _bad()
    if body["what"] == "footage":
        return open_footage(kit)
    if body["what"] == "photos":
        return open_photos(kit)
    if body["what"] == "reels":
        return open_reels(kit)
    d = music_dir(kit)
    if not music_ok(kit):                    # a link, or not a folder: never opened, never written into (v19 review)
        arrange.log("reel page: the shoot's Music folder is a link or not a folder, so it isn't opened")
        return 200, {"ok": False, "words": WORDS["cant_open"]}
    try:
        d.mkdir(exist_ok=True)               # the kit's own folder is there (kit_by_name): only Music is ever made
    except OSError:
        return 200, {"ok": False, "words": WORDS["cant_open"]}
    ok, note = _open_folder(d)
    if not ok:
        arrange.log(f"reel page: the Music folder couldn't be opened: {str(note)[:200]}")
        return 200, {"ok": False, "words": WORDS["cant_open"]}
    w = pc_words(WORDS["music_open"])
    if note == "behind":
        first, rest = w.split(". ", 1)
        w = first + OUR_WORDS["behind"] + " " + rest
    return 200, {"ok": True, "words": w}


def open_capcut_for_page(body):
    """POST /reel-capcut {kit, from?}: starts CapCut (posting_queue.open_capcut, through capcut.py's own open) and says
    her words (decision 24, capcut.OPEN_WORDS)."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    if set(body) - {"kit", "from"} or body.get("from", "reel") not in ("reel", "kit"):
        return _bad()
    # "from": "kit" is the post kit's Reel card, whose button is her "Open in CapCut" (the reel page's is "Open CapCut")
    button = KIT_OPEN_CAPCUT if body.get("from") == "kit" else WORDS["open_capcut"]
    with arrange.locked(lock_path(kit)):
        project = newest_project(kit)
    words = _reel_module("capcut").OPEN_WORDS
    if os.environ.get(TEST_CAPCUT):
        arrange.log("reel page (test): would open CapCut")
        return 200, {"ok": True, "words": words}
    import posting_queue
    ok, said = posting_queue.open_capcut({"reel": {"project": project}} if project else {}, ok_words=words,
                                         button=button)
    return 200, {"ok": bool(ok), "words": said}


# ---------- the routes ----------

def _one(q, key):
    v = q.get(key, [""])
    return v[0] if v else ""


def _get_page(handler, q):
    import arrange_page
    if (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
        # a link from another website: the plain "can't find" page, and nothing is looked at or written (v19 review:
        # the page's look starts small copies and can re-write the reel page's record)
        return arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
    rows = arrange.sheet_rows(kit)
    if not rows:
        return arrange._send_page(handler, arrange_page.plain_page(NOT_READY))
    st = state(kit)
    if st is None:
        return arrange._send_page(handler, arrange_page.plain_page(NOT_READY))
    if any(not x["have"] and not x["missing"] for x in st["photos"]):
        # a PC without Pillow, or a kit too deep in folders for a PC: say so. A Mac: never.
        cant = arrange.cant_make(kit, rows)
        if cant:
            return arrange._send_page(handler, arrange_page.plain_page(cant[1] + " Tell your assistant and it'll sort it out."))
        arrange.start_previews(kit)
    # her v27: no kind in the address is the chooser; with one, the reel's own kind wins over the address (a saved
    # bts reel opened from a photos address shows as bts), and a reel never chosen takes the address's
    asked = _one(q, "kind")
    if asked not in KINDS:
        return arrange._send_page(handler, chooser_html(kit.name, st["short"], st["kit_page"]))
    arrange._send_page(handler, page_html(kit.name, st["short"], st["kit_page"], st.get("kind") or asked))


_RELIST = {}                      # kit -> when its Photos folder was last compared with the numbered list
_RELIST_LOCK = threading.Lock()
RELIST_EVERY = 4.0                # hers: the page looks every 4 seconds; the folder is compared at most that often
RELIST_SETTLE = 2.0               # a photo still being copied in (changed this recently) holds the list until it has settled


def relist_if_changed(kit):
    """Her v27: photos dragged into the shoot's Photos folder show up on an open page by themselves. The folder is
    compared with the numbered list on the page's own poll (GET /reel-state; hers asked /photos.json every 4 s as
    well): a photo there that the list hasn't got, or one on the list that is gone, and the list is made again
    through `kit.py sheet`, the one writer, so every photo keeps its number (the stamp changes, and the page sees
    it). Nothing is drawn (no contact sheet: quick=True) and nothing else is written. True when the list was
    re-made. Whatever goes wrong, nothing is re-made and the page goes on with the list it has."""
    now = time.time()
    with _RELIST_LOCK:
        if now - _RELIST.get(str(kit), 0.0) < RELIST_EVERY:
            return False
        _RELIST[str(kit)] = now
    try:
        rows = arrange.sheet_rows(kit)
        if not rows:
            return False
        rec = kit_mod.load_rec(kit)
        folder = kit_mod.photos_dir(kit, rec)
        reel = _reel_module("reel")
        listed = {reel._photo_key(arrange.photo_name(x)) for x in rows}
        there, settled = set(), set()
        for f in folder.iterdir():
            if f.name.startswith(".") or f.suffix.lower() not in reel.PHOTOS or f.is_symlink() or not f.is_file():
                continue
            k = reel._photo_key(f.name)
            there.add(k)
            if now - f.stat().st_mtime >= RELIST_SETTLE:
                settled.add(k)
        new = there - listed
        if not new and not (listed - there):
            return False
        if new - settled:
            return False                      # a photo still being copied in: the list waits until every new one has settled
        if kit_mod.sheet(kit, quick=True) != 0:
            return False
        arrange.start_previews(kit)
        return True
    except (OSError, ValueError, TypeError, AttributeError, ImportError) as e:
        arrange.log(f"reel page: the Photos folder couldn't be compared with the list: {e.__class__.__name__}: {str(e)[:160]}")
        return False


def _get_state(handler, q):
    if (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 403)
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_json(handler, {"ok": False, "words": CANT_FIND}, 404)
    relist_if_changed(kit)
    st = state(kit) if arrange.sheet_rows(kit) else None
    if st is None:
        return arrange._send_json(handler, {"ok": False, "words": NOT_READY}, 404)
    arrange._send_json(handler, st)


def _get_job_or_songs(handler, path, q):
    """GET /reel-songs?kit=: the shoot's songs (ids and names only); GET /reel-job?kit=&id=: how Make my reel is going."""
    if (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 403)
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_json(handler, {"ok": False, "words": CANT_FIND}, 404)
    if path == "/reel-songs":
        return arrange._send_json(handler, {"ok": True, "music": music_dir(kit).is_dir() and music_ok(kit), "songs": songs_for_page(kit)})
    jid = _one(q, "id")
    if jid and not JOB_ID.fullmatch(jid):
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 400)
    job = job_for_page(kit)
    if job is None or (jid and job["id"] != jid):
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD, "job": job}, 404)
    arrange._send_json(handler, {"ok": True, "job": job})


def _cross_site(handler):
    return (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site"


def _get_footage(handler, path, q):
    """GET /reel-footage?kit=: the videos, moments and Claude's footage order. GET /reel-video?kit=&key=: the video
    to play (the original when it plays as it is, else its small copy), in pieces when asked (Range, 206).
    GET /reel-strip?kit=&key=&n=: one still of the strip under the player. GET /reel-moment-still?kit=&id=: the
    still on a moment's card. Never a path, in or out; only files the Assistant itself listed or made."""
    if _cross_site(handler):
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 403)
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_json(handler, {"ok": False, "words": CANT_FIND}, 404)
    if path == "/reel-footage":
        if _one(q, "for") == "talking":          # the talking reel page's video picker: the list, and nothing written
            return arrange._send_json(handler, footage_for_page(kit, read_only=True))
        if not arrange.sheet_rows(kit):
            return arrange._send_json(handler, {"ok": False, "words": NOT_READY}, 404)
        return arrange._send_json(handler, footage_for_page(kit))
    if path == "/reel-moment-still":
        mid = _one(q, "id")
        f = moment_still_file(kit, mid) if MOMENT_ID.fullmatch(mid) else None
        return _send_small(handler, f, "image/jpeg") if f else handler.send_error(404)
    v = video_by_key(kit, _one(q, "key"))
    if v is None:
        return handler.send_error(404)
    if path == "/reel-strip":
        n = _one(q, "n")
        pr = _prev_rec(kit, v["key"])
        s = next((x for x in pr.get("stills") or [] if isinstance(x, dict) and str(x.get("n")) == n and x.get("file")), None) \
            if re.fullmatch(r"[0-9]{1,5}", n) else None
        f = (_prev_dir(kit, v["key"]) / str(pr.get("strip") or "") / s["file"]) if s and pr.get("strip") else None
        if f is None or Path(s["file"]).name != s["file"] or not f.is_file():
            return handler.send_error(404)
        return _send_small(handler, f, "image/jpeg")
    if v["facts"].get("plays_as_is"):
        return send_range(handler, v["path"], "video/mp4")          # the original, only read (hers)
    copy = _prev_dir(kit, v["key"]) / "preview.mp4"
    if copy.is_file():
        return send_range(handler, copy, "video/mp4")
    return handler.send_error(404)


def _send_small(handler, path, ctype):
    try:
        data = Path(path).read_bytes()
    except OSError:
        return handler.send_error(404)
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "private, max-age=3600")
    handler.end_headers()
    handler.wfile.write(data)


RANGE = re.compile(r"bytes=([0-9]*)-([0-9]*)")


def send_range(handler, path, ctype):
    """A big file, in pieces when the browser asks for a range (hers: _send_file; video players ask, to skip
    around): 206 with the piece, 416 for a range past the end, 200 with the whole file when no range is asked."""
    try:
        f = open(path, "rb")
    except OSError:
        return handler.send_error(404)
    with f:
        size = os.fstat(f.fileno()).st_size
        m = RANGE.fullmatch((handler.headers.get("Range") or "").strip())
        a, b = 0, size - 1
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                a = int(m.group(1))
                b = int(m.group(2)) if m.group(2) else size - 1
            else:
                a = max(0, size - int(m.group(2)))
            b = min(b, size - 1)
            if a >= size or a > b:
                handler.send_response(416)
                handler.send_header("Content-Range", "bytes */%d" % size)
                handler.send_header("Content-Length", "0")
                handler.end_headers()
                return
            handler.send_response(206)
            handler.send_header("Content-Range", "bytes %d-%d/%d" % (a, b, size))
        else:
            handler.send_response(200)
        handler.send_header("Content-Type", ctype)
        handler.send_header("Accept-Ranges", "bytes")
        handler.send_header("Content-Length", str(b - a + 1))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        f.seek(a)
        left = b - a + 1
        try:
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                handler.wfile.write(chunk)
                left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass                                  # the player moved on; that's normal (hers)


SONG_TYPES = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".aif": "audio/aiff", ".aiff": "audio/aiff", ".aac": "audio/aac"}   # else audio/mp4 (hers)


def _get_song(handler, q):
    """GET /reel-song?kit=&id=: the song to play on the page (her v27 Listen, and the watch step's sound later):
    an audio file as it is, a screen recording's sound (made once, beside it: sound_for). By id, never a path;
    in pieces when the player asks (send_range). 404 for an id that isn't one of the shoot's songs."""
    if _cross_site(handler):
        return handler.send_error(403)
    kit = arrange.kit_by_name(_one(q, "kit"))
    sid = _one(q, "id")
    if kit is None or not SONG_ID.fullmatch(sid):
        return handler.send_error(404)
    s = song_by_id(kit, sid)
    if s is None:
        return handler.send_error(404)
    path = s["path"]
    if s["kind"] == "video":
        path, _why = sound_for(kit, s)
        if path is None:
            return handler.send_error(404)
    return send_range(handler, path, SONG_TYPES.get(Path(path).suffix.lower(), "audio/mp4"))


def _get_font(handler, q):
    key = _one(q, "f")
    if key not in FACE_FILES:
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


def handle_get(handler, path, query):
    """Every GET for the reel page. Whatever goes wrong, the server answers and stays up."""
    try:
        if not arrange.our_host(handler):
            return handler.send_error(403)
        q = parse_qs(query or "", keep_blank_values=True)
        if path == "/reel.html":
            return _get_page(handler, q)
        if path == "/reel-state":
            return _get_state(handler, q)
        if path == "/reel-font":
            return _get_font(handler, q)
        if path in ("/reel-job", "/reel-songs"):
            return _get_job_or_songs(handler, path, q)
        if path in ("/reel-footage", "/reel-video", "/reel-strip", "/reel-moment-still"):
            return _get_footage(handler, path, q)
        if path == "/reel-song":
            return _get_song(handler, q)
        return handler.send_error(404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        arrange.log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            if path in ("/reel-font", "/reel-video", "/reel-strip", "/reel-moment-still", "/reel-song"):
                handler.send_error(404)
            elif path.endswith(".html"):
                import arrange_page
                arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
            else:
                arrange._send_json(handler, {"ok": False, "words": OUR_WORDS["cant_reach"]}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def _json_body(handler, path, cap=None):
    """The body of a JSON POST as a dict, after arrange's guard (host, Origin, type, length). None when it was
    refused (and answered). `cap` is the most bytes the route takes (POST_CAP unless the route says otherwise:
    the talking reel page's save may be larger)."""
    try:
        handler.connection.settimeout(arrange.BODY_WAIT)
    except (OSError, AttributeError):
        pass
    bad = arrange.guard(handler, "application/json", POST_CAP if cap is None else cap, path)
    if bad:
        arrange._drain(handler)
        arrange._send_json(handler, {"ok": False, "words": bad[1]}, bad[0])
        return None
    raw = handler.rfile.read(int(handler.headers.get("Content-Length").strip()))
    try:
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        body = None
    if not isinstance(body, dict):
        arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 400)
        return None
    return body


def handle_post(handler, path, query):
    """Every POST for the reel page. Whatever goes wrong, the server answers and stays up."""
    try:
        body = _json_body(handler, path)
        if body is None:
            return
        if path in ("/reel-version", "/reel-song-remove") and _cross_site(handler):   # a press from another website's page
            return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 403)
        route = {"/reel-save": save_from_page, "/reel-make": start_make, "/reel-open": open_music,
                 "/reel-capcut": open_capcut_for_page, "/reel-moment": change_moments,
                 "/reel-version": version_from_page, "/reel-song-remove": remove_song,
                 "/reel-preview": preview_from_page, "/reel-video": save_video_from_page}.get(path)
        if route is None:
            return arrange._send_json(handler, {"ok": False, "words": NOT_YET}, 404)
        code, out = route(body)
        return arrange._send_json(handler, out, code)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        arrange.log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            arrange._send_json(handler, {"ok": False, "words": OUR_WORDS["cant_reach"]}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


# ---------- the page ----------
# Her stylesheet (reel-maker.html, v19), as she wrote it, with three changes. The Google Fonts link is gone: DM Sans
# is served by the Assistant itself. Her colour names and the rules every page shares now live in look.py (Dustin,
# Nov 7: every page takes this page's look), so they are not repeated here. And no serif (Dustin, Nov 7: "get rid of
# that serif font"): her three Fraunces italic touches (the coral full stop after the title, the empty-reel line, the
# paste line) are DM Sans now, the full stop still coral. OUR_CSS adds what our own drag draws, and one rule
# hers lacks: anything marked hidden stays hidden. In hers ".opt .rec{display:inline-block}" wins over hidden, so
# "Recommended for behind-the-scenes reels" shows on a photos-only reel too; BUILD.md says it is for footage
# only (for the "Tell Nicole" list).
STYLE = r"""
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:400 16px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:0 clamp(16px,4vw,40px) 9rem}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand b{font:600 16px/1 var(--sans)}.brand small{display:block;margin-top:4px;font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.homelink{display:inline-flex;align-items:center;gap:.45em;font:600 13.5px/1 var(--sans);color:#fff;background:var(--ink);text-decoration:none;padding:10px 16px 10px 13px;border-radius:999px;white-space:nowrap;transition:background .2s}.homelink:hover{background:var(--coral-2)}
.head{padding:clamp(1.8rem,4vw,3rem) 0 .6rem;display:grid;gap:.5rem}
.eyebrow{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
h1{margin:0;font:600 clamp(30px,4.4vw,50px)/1.03 var(--sans);letter-spacing:-.035em}
.lede{margin:0;color:var(--ink-2);font-size:clamp(15.5px,1.3vw,17.5px);max-width:42em}

.step{background:var(--paper);border-radius:22px;padding:1.3rem;margin-top:1.1rem;box-shadow:0 1px 0 var(--line)}
.step h2{display:flex;align-items:center;gap:.6rem;margin:0 0 .3rem;font:600 21px/1.2 var(--sans);letter-spacing:-.02em}
.num{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--ink);color:#fff;font:600 13px/1 var(--sans);flex:none}
.step.done .num{background:var(--long)}
.say{margin:.2rem 0 .9rem;color:var(--ink-2);font-size:15px;max-width:44em}
.say b{color:var(--ink);font-weight:600}

.choice{display:flex;gap:.6rem;flex-wrap:wrap;margin:.2rem 0 1rem}
.opt{border:1.5px solid var(--line);background:var(--paper);border-radius:14px;padding:.75rem 1rem;text-align:left;cursor:pointer;font:inherit;color:inherit;min-width:220px;flex:1 1 220px;max-width:340px;transition:border-color .2s,box-shadow .2s}
.opt b{display:block;font-weight:600;font-size:15px}
.opt span{display:block;color:var(--ink-2);font-size:13.5px;line-height:1.35;margin-top:.15rem}
.opt:hover{border-color:var(--coral)}
.opt{position:relative}
a.opt{text-decoration:none;display:block}
.opt.on{border-color:var(--coral-2);background:#FFF6F2;box-shadow:0 0 0 1px var(--coral-2) inset}
.opt.on::after{content:"✓";position:absolute;top:.6rem;right:.75rem;width:22px;height:22px;border-radius:50%;background:var(--coral-2);color:#fff;font:700 12px/22px var(--sans);text-align:center}
.opt.on b{padding-right:1.6rem}
.tools{display:flex;gap:.7rem;align-items:center;margin:0 0 .6rem;min-height:34px}
.btn.small{padding:.35rem .9rem;font-size:14px}
.btn:disabled{opacity:.4;cursor:default}
.tools-say{font-size:13.5px;color:var(--ink-2,#6b625a)}
.ask{margin-top:.8rem}.ask label{display:block;font-size:14px;margin-bottom:.5rem}
.ask .ex{display:block;color:var(--ink-2);margin-top:.25rem;padding-left:.8rem;border-left:2px solid var(--coral-l)}
.ask textarea{width:100%;box-sizing:border-box;font:15px/1.45 var(--sans);padding:.6rem .8rem;border:1px solid var(--line);border-radius:10px;background:#fff;resize:vertical;min-height:4.6em}
.feel{display:flex;flex-wrap:wrap;align-items:center;gap:.45rem;margin-top:.75rem;font-size:14px}
.feel > b{font-weight:600;margin-right:.2rem}
.feel button{font:500 14px/1 var(--sans);padding:.55em .95em;border-radius:999px;border:1.5px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
.feel button:hover{border-color:var(--coral)}
.feel button.on{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.feel small{color:var(--ink-2);flex-basis:100%}
.feel input{font:15px/1.2 var(--sans);padding:.5em .8em;border:1.5px solid var(--coral-2);border-radius:999px;min-width:0;width:15em;max-width:100%;background:#fff;color:var(--ink)}
.feel input:focus{outline:2px solid var(--coral);outline-offset:0}
.ask textarea:focus{outline:2px solid var(--coral);outline-offset:0;border-color:transparent}
.result .leftout{background:#FFF8EC;border:1px solid #F3E3C3;border-radius:10px;padding:.6rem .8rem}
#reel .pick{aspect-ratio:auto;min-height:120px}
.tip{display:flex;gap:.8rem;align-items:flex-start;background:var(--cream);border-radius:14px;padding:.8rem 1rem;margin:0 0 1rem;font-size:14.5px}
.tip p{margin:0}
.tip .legend{margin:.35rem 0 0}
.opt .rec{display:inline-block;font:600 10px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--coral-2);background:var(--coral-l);border-radius:999px;padding:.3em .55em;margin-left:.35rem;vertical-align:2px}

#reel{display:grid;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:10px;min-height:120px}
#reel:empty::before{content:"Your reel is empty. Tap photos below to add them.";color:var(--ink-2);grid-column:1/-1;align-self:center;text-align:center;font:400 16px/1.3 var(--sans)}
.tile{position:relative;border-radius:12px;overflow:hidden;background:var(--sand-l);cursor:grab;user-select:none;-webkit-user-select:none;box-shadow:0 0 0 1px var(--line)}
.tile .ph{aspect-ratio:9/16;position:relative}
.tile img{width:100%;height:100%;object-fit:cover;display:block;pointer-events:none}
.pos{position:absolute;top:6px;left:6px;background:rgba(20,22,30,.72);color:#fff;font:600 12px/1 var(--sans);border-radius:999px;padding:.35em .6em}
.x{position:absolute;top:5px;right:5px;width:26px;height:26px;border-radius:50%;border:0;background:rgba(20,22,30,.65);color:#fff;font-size:16px;line-height:26px;cursor:pointer;padding:0}
.tile.long{box-shadow:0 0 0 3px var(--long)}
.tile.quick{box-shadow:0 0 0 3px var(--quick)}
.hold{display:grid;grid-template-columns:1fr 1fr;gap:4px;padding:5px;background:var(--paper)}
.hold button{border:1px solid var(--line);background:var(--paper);color:var(--ink-2);border-radius:8px;font:600 11.5px/1 var(--sans);padding:.45rem 0;cursor:pointer}
.hold button.lng.on{background:var(--long);border-color:var(--long);color:#fff}
.hold button.qk.on{background:var(--quick);border-color:var(--quick);color:#fff}
.ghost{opacity:.35}.chosen{outline:3px solid var(--coral);outline-offset:-3px}
.count{font-size:13.5px;color:var(--ink-2);margin-top:.7rem}
.count.warn{color:var(--coral-2)}
.legend{display:flex;gap:1rem;flex-wrap:wrap;font-size:13px;color:var(--ink-2);margin:.2rem 0 .9rem}
.legend i{display:inline-block;width:12px;height:12px;border-radius:4px;margin-right:.35rem;vertical-align:-1px}

details.all{margin-top:1rem;border-top:1px solid var(--line);padding-top:.8rem}
details.all summary{cursor:pointer;font-weight:600;font-size:15px}
#all{display:grid;grid-template-columns:repeat(auto-fill,minmax(86px,1fr));gap:8px;margin-top:.8rem}
.pick{position:relative;border-radius:10px;overflow:hidden;background:var(--sand-l);aspect-ratio:2/3;cursor:pointer;border:0;padding:0}
.pick img{width:100%;height:100%;object-fit:cover;display:block;transition:opacity .15s}
.pick .badge{position:absolute;right:5px;bottom:5px;background:var(--coral-2);color:#fff;font:700 12px/24px var(--sans);border-radius:999px;min-width:24px;height:24px;text-align:center;padding:0 6px;display:none}
.pick.in .badge{display:block}.pick.in img{opacity:.45}
.zoom{position:absolute;top:4px;right:4px;width:24px;height:24px;border-radius:50%;border:0;background:rgba(20,22,30,.55);color:#fff;font-size:12px;cursor:pointer;padding:0}

.btn{display:inline-flex;align-items:center;gap:.45rem;border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:999px;padding:.62rem 1.1rem;font:600 14px/1 var(--sans);cursor:pointer;transition:all .2s var(--ease)}
.btn:hover{border-color:var(--coral);color:var(--coral-2)}
.btn.main{background:var(--ink);color:#fff;border-color:var(--ink)}.btn.main:hover{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.btn:disabled{opacity:.45;cursor:default}
.songs{display:grid;gap:.5rem;margin-top:.9rem}
.song{display:flex;align-items:center;gap:.75rem;border:1.5px solid var(--line);border-radius:14px;padding:.7rem .9rem;cursor:pointer;background:var(--paper);text-align:left;font:inherit;color:inherit;width:100%}
.song:hover{border-color:var(--coral)}
.song.on{border-color:var(--coral-2);background:#FFF6F2;box-shadow:0 0 0 1px var(--coral-2) inset}
.song .ic{width:34px;height:34px;border-radius:10px;background:var(--coral-l);color:var(--coral-2);display:grid;place-items:center;font-size:16px;flex:none}
.song b{display:block;font-weight:600;font-size:15px}
.song small{color:var(--ink-2);font-size:13px}
.song.none .ic{background:var(--sand-l);color:var(--ink-2)}
.waiting{font-size:14px;color:var(--ink-2);margin:.7rem 0 0}
.note{font-size:13px;color:var(--ink-2);margin:.9rem 0 0;max-width:46em}
.vibes{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:.6rem}
.vibes .opt{max-width:none}

.make{position:fixed;left:0;right:0;bottom:0;background:rgba(255,255,255,.96);backdrop-filter:blur(8px);border-top:1px solid var(--line);padding:.8rem 16px;z-index:5}
.make .in{max-width:1040px;margin:0 auto;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}
.make .sum{flex:1 1 260px;font-size:14px;color:var(--ink-2)}
.make .sum b{color:var(--ink)}
#makeBtn{padding:.8rem 1.4rem;font-size:15px}
.result{display:none;margin-top:1.1rem;border-radius:22px;padding:1.2rem 1.3rem;background:var(--long-l)}
.result.on{display:block}
.result.bad{background:var(--coral-l)}
.result h3{margin:0 0 .3rem;font:600 19px/1.25 var(--sans)}
.result p{margin:.2rem 0;font-size:14.5px}
.result .acts{margin-top:.7rem;display:flex;gap:.5rem;flex-wrap:wrap}
.spin{display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.vlist{display:grid;gap:.4rem;margin:.8rem 0 0}
.vid{display:flex;align-items:center;gap:.7rem;border:1px solid var(--line);border-radius:12px;padding:.55rem .8rem;font-size:14.5px}
.vid .ic{width:30px;height:30px;border-radius:9px;background:var(--coral-l);color:var(--coral-2);display:grid;place-items:center;font-size:13px;flex:none}
.vid small{color:var(--ink-2);margin-left:auto;white-space:nowrap}
.insight{background:#FFF8EC;border:1px solid #F3E3C3;border-radius:14px;padding:.85rem 1rem;margin:1rem 0 0;font-size:14px}
.insight b{font-weight:600}.insight p{margin:.35rem 0 0}
.paste{margin:1rem 0 0;font-size:14.5px}.paste p{margin:0 0 .45rem}
.paste .line{display:flex;align-items:center;gap:.7rem;justify-content:space-between;border:1.5px dashed var(--coral);border-radius:14px;padding:.6rem .7rem .6rem 1rem;max-width:520px;background:var(--paper)}
.paste .line span{font:500 17px/1.35 var(--sans)}
.mh{font:600 16px/1.2 var(--sans);margin:1.3rem 0 .2rem}
.undo-note{display:flex;gap:.7rem;align-items:center;font-size:14px;background:var(--ink);color:#fff;border-radius:12px;padding:.55rem .9rem;margin:.6rem 0 0;width:max-content;max-width:100%}
.undo-note button{background:none;border:0;color:#FFB59B;font:600 14px var(--sans);text-decoration:underline;cursor:pointer;padding:0}
.lb{position:fixed;inset:0;background:rgba(20,22,30,.92);display:none;place-items:center;z-index:50;cursor:zoom-out;padding:16px}
.lb.on{display:grid}.lb img{max-width:92vw;max-height:92vh;border-radius:12px}
@media(max-width:560px){#reel{grid-template-columns:repeat(auto-fill,minmax(88px,1fr))}.opt{min-width:0;max-width:none}}
"""

FONT_CSS = "".join(
    "@font-face{font-family:'%s';src:url('/reel-font?f=%s') format('truetype');font-weight:%d;font-style:%s;font-display:swap}"
    % (fam, key, wt, st) for fam, wt, st, key in FACES)
# The page itself takes its font from look.py (/look-font, answered by the posting server). FONT_CSS (with Fraunces)
# is kept for kit pages saved before Nov 7 that still ask for it, and /reel-font answers exactly as before.

# Her rules for the "Your reels" bar (v25), as she wrote them, in look.py's names.
REELS_CSS = r"""
.reels{display:flex;flex-wrap:wrap;align-items:center;gap:.6rem;margin-top:1.2rem;padding:.75rem .9rem;background:var(--paper);border:1px solid var(--line);border-radius:16px;max-width:42em}
.reels label{font:600 13px/1 var(--sans);color:var(--ink-2);letter-spacing:.02em}
.reels select,.reels input{font:600 14px/1.2 var(--sans);color:var(--ink);background:var(--cream);border:1px solid var(--line);border-radius:999px;padding:.55rem 2rem .55rem .9rem;min-width:11em;max-width:100%}
.reels select{appearance:none;-webkit-appearance:none;cursor:pointer;background-image:linear-gradient(45deg,transparent 50%,var(--ink-2) 50%),linear-gradient(135deg,var(--ink-2) 50%,transparent 50%);background-position:calc(100% - 16px) 52%,calc(100% - 11px) 52%;background-size:5px 5px;background-repeat:no-repeat}
.reels input{padding-right:.9rem}
.reels .btn{padding:.55rem .95rem;font-size:13.5px}
.reels .btn.new{background:var(--ink);color:#fff;border-color:var(--ink)}
.reels .msg{font-size:13px;color:var(--ink-2);flex-basis:100%}
.reels .msg:empty{display:none}
.reels [hidden]{display:none!important}
.reels #verRenBox{display:inline-flex;flex-wrap:wrap;align-items:center;gap:.6rem}
"""


def reels_bar(w, label="reels_label", which="reels_which", new="reels_new"):
    """Her "Your reels" bar (v25), as she wrote it: a drop-down of the shoot's reels, + Start a new reel, Rename
    (the name turns into a box with Save and Cancel). The talking reel page draws the same bar with its own
    three lines. Every name is put in by the page's script as text."""
    e = html.escape
    return ("<div class='reels' id='reels'>"
            "<label for='verSel'>" + e(w[label]) + "</label>"
            "<select id='verSel' aria-label='" + e(w[which], quote=True) + "'></select>"
            "<button class='btn new' id='verNew' type='button'>" + e(w[new]) + "</button>"
            "<button class='btn' id='verRen' type='button'>" + e(w["reels_rename"]) + "</button>"
            "<span id='verRenBox' hidden><input id='verName' maxlength='" + str(reels.NAME_MAX) + "' aria-label='"
            + e(w["reels_name"], quote=True) + "'> <button class='btn' id='verSave' type='button'>" + e(w["reels_save"])
            + "</button> <button class='btn' id='verCancel' type='button'>" + e(w["reels_cancel"]) + "</button></span>"
            "<span class='msg' id='verMsg' role='status'></span>"
            "</div>")


# The bar's script, one for both pages (the reel page and the talking reel page): hers (verOp and its buttons),
# with ours underneath. `host` is what the page hands it: post(body) -> a promise of {code, j}; flush() -> a
# promise that this reel is saved exactly as it is (hers: "this reel is saved exactly as it is first"); reload(j)
# after a new reel or a switch, given the route's answer (the reel page reopens the reel as its own kind, v27;
# the talking page reloads); words.
REELS_JS = r"""
(function(){
  'use strict';
  window.ReelsBar = function(host){
    var $ = function(id){ return document.getElementById(id); };
    var W = host.words, VERS = [], CUR = 'v1', busy = false;
    function msg(t){ $('verMsg').textContent = t || ''; }
    function show(){
      var sel = $('verSel');
      if (document.activeElement === sel && sel.options.length === VERS.length) return;   // never under their hand
      sel.textContent = '';
      VERS.forEach(function(v){
        var o = document.createElement('option');
        o.value = v.id; o.textContent = v.name; o.selected = v.id === CUR;
        sel.appendChild(o);
      });
      sel.value = CUR;
    }
    function set(vers, cur){
      if (!Array.isArray(vers) || !vers.length) return;
      VERS = vers; CUR = cur || vers[0].id;
      if (!busy) show();
    }
    function op(body){
      if (busy) return Promise.resolve(null);
      busy = true;
      msg(body.op === 'new' ? W.reels_starting : body.op === 'switch' ? W.reels_opening : '');
      return Promise.resolve(host.flush()).then(function(saved){
        if (saved === false) throw new Error('not saved');
        return host.post(body);
      }).then(function(res){
        busy = false;
        var j = (res && res.j) || {};
        if (!res || res.code !== 200 || !j.ok) { msg(j.words || W.reels_failed); show(); return null; }
        return j;
      }).catch(function(){ busy = false; msg(W.reels_reach); show(); return null; });
    }
    function renDone(){ $('verRenBox').hidden = true; $('verRen').hidden = false; $('verSel').hidden = false; }
    $('verSel').onchange = function(){
      var to = $('verSel').value;
      if (to === CUR) return;
      op({op: 'switch', id: to}).then(function(j){ if (j) host.reload(j); });    // the answer goes along (v27: the reel's own kind)
    };
    $('verNew').onclick = function(){ op({op: 'new'}).then(function(j){ if (j) host.reload(j); }); };
    $('verRen').onclick = function(){
      var v = VERS.filter(function(x){ return x.id === CUR; })[0] || {};
      $('verName').value = v.name || '';
      $('verRenBox').hidden = false; $('verRen').hidden = true; $('verSel').hidden = true;
      msg('');
      $('verName').focus(); $('verName').select();
    };
    $('verCancel').onclick = function(){ renDone(); $('verRen').focus(); };
    $('verSave').onclick = function(){
      var name = $('verName').value.trim();
      if (!name) return;
      op({op: 'rename', id: CUR, name: name}).then(function(j){
        if (!j) return;                              // the box stays open with the line that says why
        set(j.versions, j.current); msg(''); renDone(); show();
        if (host.renamed) host.renamed(j);
        $('verRen').focus();
      });
    };
    $('verName').onkeydown = function(e){
      if (e.key === 'Enter') { e.preventDefault(); $('verSave').click(); }
      if (e.key === 'Escape') { e.preventDefault(); $('verCancel').click(); }
      e.stopPropagation();
    };
    return {set: set, current: function(){ return CUR; }, list: function(){ return VERS.slice(); },
            name: function(){ var v = VERS.filter(function(x){ return x.id === CUR; })[0]; return VERS.length > 1 && v ? v.name : ''; }};
  };
})();
"""

# The photo note under "Put your photos in order" (her v25): her three rules as she wrote them, then two of ours
# (her box is two rows, where our other note box's smallest height is three; a long name wraps in the line to copy).
PICK_CSS = r"""
.photoask{margin:1rem 0 .4rem;padding:.9rem 1rem;border:1px solid var(--line);border-radius:14px;background:var(--cream)}
.photoask label{display:block;font-size:14.5px;margin-bottom:.5rem}.photoask .ex{display:block;color:var(--ink-2);font-size:13.5px;margin-top:.25rem}
.photoask p{margin:.7rem 0 .45rem}
.photoask textarea{min-height:3.4em}
.photoask .line span{overflow-wrap:anywhere;min-width:0}
"""

# Her v25 style rules for selecting several photos, each as she wrote it (the tag on the photos being dragged gets
# its words, " photos", from her rule; ours sits on the lifted copy our own drag draws, by the same rule).
SELECT_CSS = r"""
.tile.picked .ph{outline:3px solid var(--coral-2);outline-offset:2px;border-radius:12px}
.tile.picked .ph::after,.pick.picked::after{content:'\2713';position:absolute;bottom:6px;left:6px;width:20px;height:20px;border-radius:50%;background:var(--coral-2);color:#fff;display:grid;place-items:center;font:700 11px/1 var(--sans);z-index:2}
.pick.picked{outline:3px solid var(--coral-2);outline-offset:1px}
.tile.riding{opacity:.3}
[data-count]::before{content:attr(data-count) ' photos';position:absolute;z-index:5;top:-10px;right:-10px;background:var(--ink);color:#fff;font:600 11px/1 var(--sans);padding:5px 8px;border-radius:999px;white-space:nowrap}
.tile[data-count],.pick[data-count]{position:relative}
.selbar{margin:.2rem 0 .7rem;font-size:13.5px;color:var(--ink-2);display:flex;flex-wrap:wrap;align-items:center;gap:.35rem}
.selbar b{color:var(--ink)}
.selbar button{border:1px solid var(--line);background:var(--paper);border-radius:999px;padding:.35rem .7rem;font:600 12.5px/1 var(--sans);cursor:pointer;color:var(--ink)}
.selbar button:hover{border-color:var(--coral)}
"""

# Her v25 style rules for the Trim button on a clip card and for the trim panel, each as she wrote it. Ours, after
# them: the line a PC shows under the timeline.
TRIM_CSS = r"""
.trim{position:fixed;inset:0;z-index:60;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(31,36,48,.45)}
.trim[hidden]{display:none}
.trim .box{background:var(--paper);border-radius:20px;width:min(720px,100%);max-height:calc(100vh - 32px);overflow:auto;padding:1.2rem 1.2rem 1rem;box-shadow:0 20px 60px rgba(31,36,48,.3)}
.trim h3{margin:0 0 .2rem;font:600 18px/1.25 var(--sans)}
.trim .hint{margin:0 0 .8rem;color:var(--ink-2);font-size:13.5px}
.trim .x{float:right;border:0;background:none;font-size:22px;line-height:1;color:var(--ink-2);cursor:pointer}
.trim .vwrap{display:flex;justify-content:center;background:#111;border-radius:12px;overflow:hidden}
.trim video{max-height:min(42vh,380px);max-width:100%;display:block}
.trim .novid{color:#ddd;font-size:13px;padding:2rem 1rem}
.trim .bar{position:relative;height:74px;margin:1.1rem 0 0;border-radius:10px;background:var(--sand-l);overflow:visible;touch-action:none;cursor:pointer;user-select:none}
.trim .film{position:absolute;inset:0;border-radius:10px;overflow:hidden}
.trim .film img{position:absolute;top:0;height:100%;object-fit:cover}
.trim .dim{position:absolute;top:0;bottom:0;background:rgba(31,36,48,.55);pointer-events:none}
.trim .dim.l{left:0;border-radius:10px 0 0 10px}.trim .dim.r{right:0;border-radius:0 10px 10px 0}
.trim .sel{position:absolute;top:-3px;bottom:-3px;border:3px solid var(--coral);border-radius:8px;box-sizing:border-box;cursor:grab}
.trim .h{position:absolute;top:-3px;bottom:-3px;width:18px;background:var(--coral);cursor:ew-resize;display:flex;align-items:center;justify-content:center}
.trim .h::after{content:'';width:3px;height:22px;border-radius:2px;background:#fff}
.trim .h.a{left:-12px;border-radius:8px 0 0 8px}.trim .h.b{right:-12px;border-radius:0 8px 8px 0}
.trim .head{position:absolute;top:-6px;bottom:-6px;width:2px;background:#fff;box-shadow:0 0 0 1px rgba(0,0,0,.4);pointer-events:none}
.trim .ticks{position:relative;height:18px;margin-top:.35rem;font-size:11px;color:var(--ink-2)}
.trim .ticks span{position:absolute;transform:translateX(-50%)}.trim .ticks span:first-child{transform:none}.trim .ticks span:last-child{transform:translateX(-100%)}
.trim .say{margin:.5rem 0 .2rem;font-size:14.5px;text-align:center}
.trim .nudges{display:flex;justify-content:space-between;gap:.6rem;flex-wrap:wrap;margin:.5rem 0 .2rem;font-size:13px;color:var(--ink-2)}
.trim .nudges > span{display:flex;align-items:center;gap:.3rem}
.trim .nudges button,.trim .acts button{border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:999px;padding:.45rem .75rem;font:600 13px/1 var(--sans);cursor:pointer}
.trim .acts{display:flex;justify-content:flex-end;gap:.5rem;margin-top:.9rem}
.trim .acts .main{background:var(--ink);color:#fff;border-color:var(--ink)}
.trim .acts .main:hover{background:var(--coral-2);border-color:var(--coral-2)}
.trim .pcnote{margin:.5rem 0 0;font-size:13px;color:var(--ink-2);text-align:center}
"""

OUR_CSS = r"""
[hidden]{display:none!important}
.reelwrap{position:relative}
.ins{position:absolute;width:4px;border-radius:3px;background:var(--coral-2);pointer-events:none;display:none;box-shadow:0 0 0 2px rgba(212,100,63,.22);z-index:3}
.ins.on{display:block}
#reel .tile{touch-action:none}
#all .pick{touch-action:pan-y}
#reel img,#all img{pointer-events:none;-webkit-user-drag:none;user-select:none}
.tile.dragging,.pick.dragging{opacity:.35}
.tile .ph .wait,.pick .wait{position:absolute;inset:0;display:grid;place-items:center;text-align:center;padding:8px;font-size:12px;line-height:1.3;color:var(--ink-2)}
.notice{font-size:13.5px;color:var(--coral-2)}
.notice button{margin-left:.5rem}
.limit{display:none}.limit.on{display:block}
body.arr-dragging,body.arr-dragging *{cursor:grabbing!important;user-select:none!important;-webkit-user-select:none!important}
.arr-lift{position:fixed;left:0;top:0;z-index:9999;pointer-events:none;will-change:transform;transform-origin:0 0}
.arr-lift .pic{width:100%;height:100%;border-radius:12px;overflow:hidden;background:var(--sand-l);box-shadow:0 0 0 3px #fff,0 18px 36px -12px rgba(0,0,0,.5)}
.arr-lift .pic img{display:block;width:100%;height:100%;object-fit:cover}
.arr-lift .say{position:absolute;left:50%;top:100%;transform:translateX(-50%);margin-top:8px;white-space:nowrap;background:var(--ink);color:#fff;font:600 12.5px/1 var(--sans);padding:6px 10px;border-radius:8px;display:none}
.arr-lift .say.on{display:block}
"""

# Her v27 style rules (reel-maker.html, handoff v27), each as she wrote it: the chooser and the kinds of reel, the
# videos' drop-down, the order that sticks to the top, + Add photos, the even spacing under the step headings
# ("Press Add my footage..." on one line), and the song drop-down with its link-like Remove. Then three of ours:
# on a phone the order does not stick (it would cover the page), a kind's hidden steps stay hidden, and the link
# back to the chooser sits in the bar with the kit's link (hers hides it under the path at the top, crumbs.js).
V27_CSS = r"""
.kinds{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:1rem}
.kind{display:grid;gap:.35rem;padding:1.1rem 1.2rem;border:1.5px solid var(--line);border-radius:16px;background:var(--paper);text-decoration:none;color:var(--ink);cursor:pointer;transition:border-color .2s,box-shadow .2s}
.kind:hover{border-color:var(--coral-2);box-shadow:0 0 0 1px var(--coral-2)}
.kind b{font:600 17px/1.2 var(--sans)}.kind span{color:var(--ink-2);font-size:14px}
.chooser h2{margin-bottom:.3rem}
.vdrop{border:1.5px solid var(--line);border-radius:14px;background:var(--paper);padding:0}
.vdrop summary{list-style:none;display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:12px;align-items:center;padding:8px 12px 8px 8px;cursor:pointer}
.vdrop summary::-webkit-details-marker{display:none}
.vdrop .vthumbs{display:flex}.vdrop .vthumbs img{width:34px;height:46px;object-fit:cover;border-radius:6px;border:2px solid var(--paper);margin-left:-10px;background:#222}.vdrop .vthumbs img:first-child{margin-left:0}
.vdrop summary b{font:600 14px/1.2 var(--sans)}.vdrop summary small{display:block;color:var(--ink-2);font-size:12.5px;margin-top:2px}
.vdrop .car{color:var(--ink-2);transition:transform .2s}.vdrop[open] .car{transform:rotate(180deg)}
.vdrop .vcard{margin:0 8px 8px;border-radius:10px}
.vid.vcard{display:grid;grid-template-columns:44px minmax(0,1fr);gap:10px;padding:6px 10px 6px 6px;background:var(--paper)}.vid.vcard img{width:44px;height:58px;object-fit:cover;border-radius:7px;background:#222;display:block}.vid.vcard b{font:600 13.5px/1.25 var(--sans)}.vid.vcard small{display:block;color:var(--ink-2);font-size:12px;margin-top:2px}
.vid.vcard small{margin-left:0;white-space:normal}
.vdrop .spin{border-color:rgba(0,0,0,.15);border-top-color:var(--coral-2);vertical-align:-2px}
.reelstick{position:sticky;top:0;z-index:20;background:var(--paper);margin:0 -1.3rem;padding:.7rem 1.3rem .8rem;max-height:46vh;overflow-y:auto;border-radius:0 0 16px 16px}
.reelstick.stuck{box-shadow:0 12px 24px -10px rgba(31,36,48,.28);border-bottom:1px solid var(--line)}
.addph{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap;margin-top:1rem}
.step h2{margin:0 0 .55rem}
.say{max-width:64em;margin:.3rem 0 1rem;line-height:1.55}
.linkbtn{border:0;background:none;padding:.3rem .2rem;font:600 13px/1 var(--sans);color:var(--ink-2);text-decoration:underline;cursor:pointer}
.songpick{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;margin:.6rem 0}
.songpick select{font:500 15px/1.2 var(--sans);padding:.65rem .8rem;border-radius:12px;border:1.5px solid var(--line);background:var(--paper);color:var(--ink);min-width:min(320px,100%);max-width:100%}
.linkbtn.sure{color:#fff;background:var(--coral-2);text-decoration:none;border-radius:999px;padding:.45rem .75rem}
.toq{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap;margin-top:.6rem}.toq #qAsk2{flex-basis:100%}
.toq .went,.result .went{font-size:14px;color:var(--ink-2);margin:0}
.toq[hidden],.linkbtn[hidden],.edwait[hidden]{display:none!important}
@media(max-width:620px){.reelstick{position:static;max-height:none;overflow:visible;margin:0;padding:0;border-radius:0}}
[data-kind-hidden]{display:none!important}
.bar .homelink+.homelink{margin-left:-.4rem}
.make{z-index:25}
@media(max-width:620px){.bar{flex-wrap:wrap;padding:.6rem 0}.bar .homelink{white-space:normal}.bar .homelink+.homelink{margin-left:0}}
"""

# Her watch step's style rules (reel-maker.html, handoff v27: "watch it before you make it" and "B-roll words on
# screen"), each as she wrote it: the grid, the 9:16 phone, its play button and bar, the controls' column, the
# chips, the words block and the dot in its corner, the words box.
WATCH_CSS = r"""
.watch .wgrid{display:grid;grid-template-columns:auto minmax(0,1fr);gap:1.4rem;align-items:start;margin-top:.9rem}
@media (max-width:720px){.watch .wgrid{grid-template-columns:1fr}}
.pvphone{position:relative;width:270px;aspect-ratio:9/16;border-radius:22px;overflow:hidden;background:#111;box-shadow:0 10px 30px rgba(31,36,48,.18)}
.pvphone img,.pvphone video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.pvphone img.fit,.pvphone video.fit{object-fit:contain}
.pvphone video[hidden],.pvphone img[hidden],.pvempty[hidden]{display:none!important}
.pvempty{position:absolute;inset:0;display:grid;place-items:center;text-align:center;padding:1.4rem;color:#ddd;font-size:14px;line-height:1.4}
.pvplay{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:64px;height:64px;border-radius:50%;border:0;background:rgba(255,255,255,.88);color:#1F2430;font-size:24px;cursor:pointer;box-shadow:0 4px 18px rgba(0,0,0,.25)}
.pvplay.playing{opacity:0}.pvphone:hover .pvplay.playing{opacity:.85}
.pvbar{position:absolute;left:10px;right:10px;top:10px;height:3px;border-radius:2px;background:rgba(255,255,255,.35)}.pvbar i{display:block;height:100%;width:0;background:#fff;border-radius:2px}
.wctl{display:grid;gap:.55rem;align-content:start;min-width:0}
.wl{font:600 12px/1.2 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--ink-2);margin-top:.35rem}
.wrow{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap}
.wrow select{font:500 14px/1.2 var(--sans);padding:.55rem .7rem;border-radius:12px;border:1.5px solid var(--line);background:var(--paper);color:var(--ink);max-width:100%}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chips button{border:1.5px solid var(--line);background:var(--paper);border-radius:999px;padding:.5rem .9rem;font:600 13px/1 var(--sans);cursor:pointer;color:var(--ink)}
.chips button.on{border-color:var(--coral-2);background:var(--coral-l);color:var(--coral-2)}
.say.sm{font-size:13px}
#pvSaved .spin{border-color:rgba(0,0,0,.15);border-top-color:var(--coral-2);vertical-align:-2px;margin-right:.3rem}
.pvphone{container-type:inline-size}
.pvtext{position:absolute;transform:translateY(-50%);text-align:center;font-weight:700;font-size:6.1cqw;line-height:1.25;z-index:4;cursor:move;touch-action:none;user-select:none;outline:1.5px dashed transparent;outline-offset:3px;border-radius:4px}
.pvphone:hover .pvtext{outline-color:rgba(255,255,255,.85)}
.pvknob{position:absolute;width:16px;height:16px;margin:-8px 0 0 -8px;border-radius:50%;background:#fff;border:2.5px solid var(--coral-2);z-index:6;cursor:nwse-resize;touch-action:none;box-shadow:0 1px 4px rgba(0,0,0,.4)}
.pvknob[hidden]{display:none!important}
.oshint{margin:-.1rem 0 .1rem!important}
.pvtext[hidden],#osBox[hidden],#pvSaveVid[hidden]{display:none!important}
.pvtext span{box-decoration-break:clone;-webkit-box-decoration-break:clone;padding:.05em .3em}
#osBox{display:grid;gap:.45rem}
#osText{font:500 15px/1.4 var(--sans);padding:.6rem .75rem;border-radius:12px;border:1.5px solid var(--line);background:var(--paper);color:var(--ink);resize:vertical;width:100%}
.wrow.os select{font:500 13.5px/1.2 var(--sans);padding:.5rem .6rem;border-radius:10px;border:1.5px solid var(--line);background:var(--paper);color:var(--ink)}
#pvSaved:empty{display:none}
"""

# Her footage editor's style rules (reel-maker.html, handoff v27: the editor, "editor v2" and "see every clip at
# once"), each as she wrote it: the player and its buttons, the Footage drop-down, Make a clip, Your clips in two
# columns (one at a phone's width: her auto-fill), the picked clip's box, the ruler, the strip, the clips on it
# and the orange trim (striped while it grows, solid with a handle each end after End here, dashed after Add
# clip), the purple YOUR PICK tag and the Name my clips box. Her ".about" (the description she took out) and her
# first editor's tabs (.edtabs, .edmain, .edside) are left out. Two of ours at the end: the Name my clips line in
# DM Sans (Dustin: no serif), and the PC's note under the timeline.
EDITOR_CSS = r"""
.wl{font:600 12px/1.2 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--ink-2);margin-top:.35rem}
.ed{margin:.6rem 0 1.2rem;padding:1rem;border-radius:18px;background:var(--cream);border:1px solid var(--line)}
.say.sm{font-size:13px}
.edplayer{position:relative;background:#111;border-radius:14px;overflow:hidden;height:min(520px,70vh);aspect-ratio:9/16;max-width:100%;display:grid;place-items:center}
.edplayer video{width:100%;height:100%;object-fit:contain;display:block}
.edwait{position:absolute;inset:0;display:grid;place-items:center;padding:1rem;text-align:center;color:#ccc;font-size:14px}
.edwait[hidden],.edsel[hidden],.linkbtn[hidden],.songs[hidden]{display:none!important}
.edrow{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}
.edtime{font:600 14px/1 var(--sans);font-variant-numeric:tabular-nums;color:var(--ink-2);margin-left:.3rem}
.edsel{background:var(--paper);border:1.5px solid var(--coral-2);border-radius:14px;padding:.75rem .9rem;display:grid;gap:.45rem}
.edsel b{font-size:15px}.edsel small{color:var(--ink-2);font-size:13px}
.edtlbar{display:flex;justify-content:space-between;align-items:center;margin:.9rem 0 .35rem}
.edtl{position:relative;height:74px;border-radius:10px;overflow:hidden;background:#222;cursor:ew-resize;touch-action:none;user-select:none;-webkit-user-select:none}
.edthumbs{position:absolute;inset:0}.edthumbs img{position:absolute;top:0;height:100%;object-fit:cover;opacity:.9;pointer-events:none}
.edmarks{position:absolute;inset:0}
.tm{position:absolute;top:0;bottom:0;background:rgba(255,255,255,.18);border:2px solid rgba(255,255,255,.75);border-radius:6px;cursor:pointer}
.tm.sel{background:rgba(240,127,90,.35);border-color:#F07F5A}
.tm.edit{border-color:#fff;box-shadow:0 0 0 2px #D4643F}
.tm i{position:absolute;left:4px;top:3px;font:700 10px/1 var(--sans);color:#fff;font-style:normal;text-shadow:0 1px 2px rgba(0,0,0,.6)}
.tm .hl,.tm .hr{position:absolute;top:-2px;bottom:-2px;width:12px;background:#fff;border-radius:4px;cursor:ew-resize}.tm .hl{left:-7px}.tm .hr{right:-7px}
.edph{position:absolute;top:0;bottom:0;width:2px;background:#F07F5A;box-shadow:0 0 0 1px rgba(0,0,0,.3);pointer-events:none}
.edruler{position:relative;height:20px;margin-bottom:3px;font:500 11.5px/1 var(--sans);color:var(--ink-2);font-variant-numeric:tabular-nums;border-bottom:1px solid var(--line)}
.edruler span{position:absolute;bottom:0;padding:0 0 5px 4px;border-left:1px solid var(--ink-2)}
.edruler i{position:absolute;bottom:0;height:5px;border-left:1px solid var(--line)}
.edgrid{display:grid;grid-template-columns:auto minmax(0,1fr);gap:1.2rem;align-items:stretch}
@media (max-width:820px){.edgrid{grid-template-columns:1fr}}
.edleft{display:grid;gap:.5rem;justify-items:center;align-content:start}
.edplayer{cursor:pointer}
.edbig{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:64px;height:64px;border-radius:50%;border:0;background:rgba(255,255,255,.88);color:#1F2430;font-size:24px;cursor:pointer;box-shadow:0 4px 18px rgba(0,0,0,.3);z-index:2}
.edbig[hidden],.moments[hidden],.vpmenu[hidden]{display:none!important}
.edunder{display:flex;align-items:center;gap:.4rem}
.edunder .ic{border:1.5px solid var(--line);background:var(--paper);border-radius:999px;height:36px;min-width:36px;padding:0 .7rem;font:600 13px/1 var(--sans);cursor:pointer;color:var(--ink)}
.edunder .ic.play{background:var(--ink);color:#fff;border-color:var(--ink);min-width:46px;font-size:15px}
.edright{display:flex;flex-direction:column;gap:.5rem;min-width:0;max-height:min(600px,calc(70vh + 50px))}
.vpick{position:relative}
.vpbtn{width:100%;display:grid;grid-template-columns:44px minmax(0,1fr) auto;gap:10px;align-items:center;text-align:left;border:1.5px solid var(--line);background:var(--paper);border-radius:12px;padding:6px 10px 6px 6px;cursor:pointer;font:inherit;color:var(--ink)}
.vpbtn img,.vpmenu img{width:44px;height:58px;object-fit:cover;border-radius:7px;background:#222;display:block}
.vpbtn b,.vpmenu b{font:600 13.5px/1.25 var(--sans);overflow-wrap:anywhere}.vpbtn small,.vpmenu small{display:block;color:var(--ink-2);font-size:12px;margin-top:2px}
.vpbtn .car{color:var(--ink-2);font-size:13px}
.vpmenu{position:absolute;z-index:30;left:0;right:0;top:calc(100% + 6px);background:var(--paper);border:1px solid var(--line);border-radius:14px;box-shadow:0 12px 32px rgba(31,36,48,.18);padding:6px;display:grid;gap:4px;max-height:340px;overflow:auto}
.vpmenu button{display:grid;grid-template-columns:44px minmax(0,1fr);gap:10px;align-items:center;text-align:left;border:0;background:none;border-radius:10px;padding:5px;cursor:pointer;font:inherit;color:var(--ink)}
.vpmenu button:hover,.vpmenu button.on{background:var(--coral-l)}
.cl-head{display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap;margin-top:.3rem}
.clist{display:grid;gap:6px;overflow:auto;min-height:120px;flex:1 1 auto;padding-right:2px}
.ci{display:grid;grid-template-columns:40px minmax(0,1fr) auto auto;gap:9px;align-items:center;border:1.5px solid var(--line);background:var(--paper);border-radius:12px;padding:5px 8px 5px 5px;cursor:pointer}
.ci img{width:40px;height:56px;object-fit:cover;border-radius:6px;background:#222;display:block}
.ci b{font:600 13px/1.25 var(--sans);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.ci small{color:var(--ink-2);font-size:11.5px;font-variant-numeric:tabular-nums}
.ci.edit{border-color:var(--coral-2);box-shadow:0 0 0 1px var(--coral-2)}
.ci .cin{border:1.5px solid var(--line);background:var(--paper);border-radius:999px;padding:.35rem .65rem;font:600 12px/1 var(--sans);cursor:pointer;color:var(--ink);white-space:nowrap}
.ci.sel .cin{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.ci .cx{border:0;background:none;color:var(--ink-2);font-size:18px;line-height:1;cursor:pointer;padding:2px 4px;border-radius:6px}.ci .cx:hover{background:#F8E1DC;color:#C2412D}
.ci .num{width:20px;height:20px;font-size:11px}
.edsel{flex:none}
.edtip{margin:.45rem 0 0}
.tm{cursor:grab}.tm.edit .hl,.tm.edit .hr{display:block}
.tcut{position:absolute;top:0;bottom:0;border:3px solid #F07F5A;background:rgba(240,127,90,.42);border-radius:6px;pointer-events:none;z-index:3;box-shadow:0 0 0 1px rgba(0,0,0,.25)}
.tcut.live{background:repeating-linear-gradient(135deg,rgba(240,127,90,.5) 0 10px,rgba(240,127,90,.32) 10px 20px)}
.tcut .cl,.tcut .cr{position:absolute;top:-3px;bottom:-3px;width:14px;background:#F07F5A;pointer-events:auto;cursor:ew-resize;display:grid;place-items:center}
.tcut .cl{left:-10px;border-radius:6px 0 0 6px}.tcut .cr{right:-10px;border-radius:0 6px 6px 0}
.tcut .cl::after,.tcut .cr::after{content:'';width:2px;height:22px;border-radius:2px;background:#fff}
.tcut.live .cr{display:none}
.tcut.set{pointer-events:auto;cursor:grab}.tcut.added{background:rgba(240,127,90,.22);border-style:dashed}.tcut.set:active{cursor:grabbing}
.tcut b{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font:700 12px/1 var(--sans);color:#fff;background:#D4643F;padding:4px 7px;border-radius:999px;white-space:nowrap}
.tcut.tiny b{left:calc(100% + 14px);transform:translateY(-50%)}
#edIn.rec{background:#F07F5A;border-color:#F07F5A;color:#fff}
.edright{max-height:none}
.clist{overflow:visible;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));align-content:start}
.clist .ci{grid-template-columns:40px minmax(0,1fr) auto auto;gap:7px}.clist .ci small{display:block;white-space:normal;line-height:1.3}.clist .ci b{white-space:normal;line-height:1.25}.clist .ci .cin{padding:.32rem .55rem}
.ci .yours{display:inline-block;font:700 10px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:#5A4FA8;background:#ECE8FB;padding:3px 7px;border-radius:999px;margin-bottom:3px}
.clist{align-items:start}.clist .ci.wide{grid-column:1/-1}
.descline{display:grid;gap:.35rem;background:var(--paper);border:1.5px dashed rgba(212,100,63,.45);border-radius:12px;padding:.6rem .75rem;font-size:13.5px;color:var(--ink-2)}
.descline[hidden]{display:none!important}
.descline .line{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap}
.descline #descWords{font:500 15.5px/1.3 var(--sans);color:var(--ink)}
.edtip.pcnote{color:var(--coral-2)}
"""

# Her steps, in her order (BUILD.md section 5: "This order is final"). Each is (her section's id, the
# function that writes it, or None while that step is not built yet). A step left out is simply not on the page.
def pc_footage():
    """True where the footage look and the stills can't run (a PC: video.py's named gap)."""
    try:
        return not _video().avfoundation_here()
    except Exception:  # noqa: BLE001
        return this_computer.WINDOWS


def _hidden(kind, shown):
    """The hidden mark on a step a kind of reel does not use (her v27: just photos hides the footage step, B-roll
    hides the photos, the style and the vibe); the page keeps it hidden whatever else would show it."""
    return "" if kind in shown else " hidden data-kind-hidden='1'"


def _footage_section(w, num, kind="bts"):
    """Her step 1, "Choose your behind-the-scenes footage" (reel-maker.html #step0, v27), with everything under
    it: Add my footage, the videos (folded into one drop-down), Good to know, the ask box, the line to copy, the
    moment cards, and the player with its strip. Since her v27 the kind of reel is chosen on the chooser, so the
    old yes/no cards are gone and the step is hidden on a just-photos page. Her v27 hides "How should it feel?"
    (its row is written, hidden: a feel saved before still counts). On a PC (pc_footage()), where Claude can't
    look through footage and there are no stills: Good to know (about how long the look takes) and the line to
    copy are left out, with this_computer.NO_LOOK_PC in place of the line (decision 26; v19 review, Nov 7)."""
    e = html.escape
    pc = pc_footage()
    feels = "".join("<button type='button' data-f='" + f + "'>" + e(w["feel_" + f]) + "</button>" for f in FEELS)
    return (
        "<section class='step' id='step0'" + _hidden(kind, ("bts", "broll")) + ">"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["foot_h2"]) + "</h2>"
        "<div id='btsBox' hidden>"
        "<p class='say'>" + w["foot_say2_html"] + "</p>"
        "<button class='btn main' id='addFootage' type='button'>" + e(w["add_footage"]) + "</button>"
        "<p class='waiting' id='footWaiting'></p>"
        "<div class='vlist' id='vlist'></div>"
        "<div class='insight'" + (" hidden" if pc else "") + "><b>" + e(w["insight_b"]) + "</b><p id='insightWords'>" + e(w["insight_words"]) + "</p>"
        "<p>" + w["quick_fix_html"] + "</p></div>"
        "<div class='paste' id='pasteBox'>"
        "<div class='ask'><label for='askIn'>" + w["ask_label_html"]
        + "<span class='ex'>" + e(w["ask_ex1"]) + "</span><span class='ex'>" + e(w["ask_ex2"]) + "</span></label>"
        "<textarea id='askIn' rows='3' maxlength='600' placeholder='" + e(w["ask_placeholder"], quote=True) + "'></textarea>"
        "<div class='feel' id='feelRow' hidden><b>" + e(w["feel_b"]) + "</b>" + feels
        + "<button type='button' data-f='own' id='feelOwnBtn'>" + e(w["feel_own"]) + "</button>"
        "<input id='feelOwn' maxlength='40' placeholder='" + e(w["feel_placeholder"], quote=True) + "' hidden>"
        "<small>" + w["feel_small_html"] + "</small></div></div>"
        "<p id='pasteSay'>" + e(this_computer.NO_LOOK_PC if pc else w["paste_say"]) + "</p>"
        "<div class='line'" + (" hidden" if pc else "") + "><span id='pasteWords'>" + e(w["paste_plain"]) + "</span>"
        "<button class='btn' id='copyLine' type='button'>" + e(w["copy"]) + "</button></div></div>"
        + editor_html(w, pc) +
        "<div id='undoNote'></div>"
        "</div></section>")


def editor_html(w, pc=False):
    """Her footage editor (reel-maker.html, "the footage editor", v27; screenshots 13 to 16), under the line to
    copy in step 1: the player on the left (a big ▶ when paused; ↶ 1s, ▶, 1s ↷ and the time under it), on the
    right the Footage drop-down, Make a clip, Your clips and a picked clip's box, and below the ruler, the strip
    of stills with the clips and the trim on it, Zoom in / Show the whole video and her tip. On a PC (no stills
    from a video yet) the line under the heading is ours and says so. The scripts fill it on load."""
    e = html.escape
    return (
        "<h3 class='mh'>" + e(w["ed_h3"]) + "</h3>"
        "<p class='say' id='edSayTop'>" + (this_computer.WATCH_PC_HTML if pc else e(w["ed_say"])) + "</p>"
        "<div class='ed' id='ed'>"
        "<div class='edgrid'>"
        "<div class='edleft'>"
        "<div class='edplayer' id='edPlayer'><video id='edVid' playsinline preload='auto'></video>"
        "<button class='edbig' id='edBig' type='button' aria-label='" + e(w["ed_play"], quote=True) + "'>&#9654;</button>"
        "<div class='edwait' id='edWait'>" + e(w["ed_wait"]) + "</div></div>"
        "<div class='edunder'><button class='ic' id='edBack' type='button' title='" + e(w["ed_back"], quote=True) + "' aria-label='" + e(w["ed_back"], quote=True) + "'>" + e(w["ed_back_b"]) + "</button>"
        "<button class='ic play' id='edPlay' type='button' aria-label='" + e(w["ed_play"], quote=True) + "'>&#9654;</button>"
        "<button class='ic' id='edFwd' type='button' title='" + e(w["ed_fwd"], quote=True) + "' aria-label='" + e(w["ed_fwd"], quote=True) + "'>" + e(w["ed_fwd_b"]) + "</button>"
        "<span class='edtime' id='edTime'>0:00.0</span></div>"
        "</div>"
        "<div class='edright'>"
        "<span class='wl'>" + e(w["ed_footage"]) + "</span>"
        "<div class='vpick'><button class='vpbtn' id='vpBtn' type='button' aria-haspopup='listbox' aria-expanded='false'></button>"
        "<div class='vpmenu' id='edTabs' role='listbox' hidden></div></div>"
        "<span class='wl'>" + e(w["ed_make"]) + "</span>"
        "<div class='edrow'><button class='btn small' id='edIn' type='button'>" + e(w["ed_in"]) + "</button>"
        "<button class='btn small' id='edOut' type='button'>" + e(w["ed_out"]) + "</button>"
        "<button class='btn main small' id='edAdd' type='button' disabled>" + e(w["ed_add"]) + "</button>"
        "<button class='linkbtn' id='edClear' type='button' hidden>" + e(w["ed_clear"]) + "</button></div>"
        "<p class='say sm' id='edSay'>" + e(w["ed_find"]) + "</p>"
        "<div class='cl-head'><span class='wl'>" + e(w["clips_wl"]) + "</span><span class='say sm' id='momentsSay'></span></div>"
        "<div class='descline' id='descBox' hidden><span>" + e(w["desc_say"]) + "</span>"
        "<div class='line'><span id='descWords'></span><button class='btn small' id='descCopy' type='button'>" + e(w["copy"]) + "</button></div></div>"
        "<div class='clist' id='clist'></div>"
        "<div class='edsel' id='edSel' hidden></div>"
        "</div></div>"
        "<div class='edtlbar'><span class='say sm' id='edWin'></span><button class='linkbtn' id='edZoom' type='button'>" + e(w["ed_zoom"]) + "</button></div>"
        "<div class='edruler' id='edRuler'></div>"
        "<div class='edtl' id='edTl'><div class='edthumbs' id='edThumbs'></div><div class='edmarks' id='edMarks'></div><div class='edph' id='edPh'></div></div>"
        + ("<p class='say sm edtip pcnote'>" + e(OUR_WORDS["editor_no_stills_pc"]) + "</p>" if pc else "") +
        "<p class='say sm edtip'>" + e(w["ed_tip"]) + "</p>"
        "</div>")


def _style_section(w, num, kind="bts"):
    """Her step 4, "What style of behind the scenes is this?" (#stepStyle), shown only with footage (and since
    her v27 only on a behind-the-scenes page: B-roll has its one style)."""
    e = html.escape
    cards = "".join("<button class='opt' type='button' data-style='" + st + "'><b>" + e(w["style_%s_b" % st]) + "</b>"
                    "<span>" + e(w["style_%s_s" % st]) + "</span></button>" for st in STYLES)
    return (
        "<section class='step' id='stepStyle' hidden" + ("" if kind == "bts" else " data-kind-hidden='1'") + ">"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["style_h2"]) + "</h2>"
        "<p class='say'>" + e(w["style_say"]) + "</p>"
        "<div class='vibes' id='styles'>" + cards + "</div>"
        "</section>")


def _order_section(w, num, kind="photos"):
    e = html.escape
    return (
        "<section class='step' id='step1'" + _hidden(kind, ("bts", "photos")) + ">"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["order_h2"]) + "</h2>"
        "<p class='say'>" + e(w["order_say"]) + "</p>"
        "<div class='choice'>"
        "<button class='opt' id='useClaude' type='button'><b>" + e(w["claude_b"])
        + "<span class='rec' id='claudeRec' hidden>" + e(w["claude_rec"]) + "</span></b>"
        "<span id='claudeWords'>" + e(w["claude_words"]) + "</span></button>"
        "<button class='opt' id='useMine' type='button'><b>" + e(w["mine_b"]) + "</b><span>" + e(w["mine_words"]) + "</span></button>"
        "</div>"
        # her v25 note box: which photos they'd like in this reel, and the line to copy into the chat
        "<div class='paste ask photoask' id='photoAskBox'>"
        "<label for='photoAskIn'><b>" + e(w["photo_ask_b"]) + "</b>" + e(w["photo_ask_opt"])
        + "<span class='ex'>" + e(w["photo_ask_ex"]) + "</span></label>"
        "<textarea id='photoAskIn' rows='2' maxlength='" + str(PHOTO_ASK_MAX) + "' placeholder='"
        + e(w["photo_ask_placeholder"], quote=True) + "'></textarea>"
        "<p>" + e(w["photo_then"]) + "</p>"
        "<div class='line'><span id='photoPaste'>" + e(w["photo_plain"]) + "</span>"
        "<button class='btn' id='copyPhoto' type='button'>" + e(w["copy"]) + "</button></div>"
        "</div>"
        "<div class='tip'><div><p>" + w["tip_html"] + "</p>"
        "<div class='legend'><span><i style='background:var(--long)'></i>" + e(w["legend_long"]) + "</span>"
        "<span><i style='background:var(--quick)'></i>" + e(w["legend_quick"]) + "</span></div></div></div>"
        "<div class='tools'><button class='btn small' id='undoBtn' type='button' disabled>" + e(w["undo"]) + "</button>"
        "<span class='tools-say' id='undoSay'></span><span class='notice' id='notice'></span></div>"
        "<p class='selbar' id='reelSel' hidden></p>"
        # her v27: the order sticks to the top while All your photos scrolls under it (.reelstick)
        "<div class='reelstick' id='reelStick'><div class='reelwrap' id='reelwrap'><div id='reel'></div></div>"
        "<div class='count' id='count'></div>"
        "<div class='count warn limit' id='limit'>" + e(OUR_WORDS["too_many"]) + "</div></div>"
        # her v27: + Add photos opens the shoot's Photos folder; new photos keep every other photo's number
        "<div class='addph'><button class='btn small' id='addPhotos' type='button'>" + e(w["add_photos"]) + "</button>"
        "<span class='tools-say' id='addPhotosSay'>" + e(w["add_photos_say"]) + "</span></div>"
        "<details class='all' id='allBox'><summary>" + e(w["all_summary"]) + "</summary>"
        "<p class='selbar' id='allSel' hidden></p><div id='all'></div></details>"
        "</section>")


def _song_section(w, num, kind="photos"):
    e = html.escape
    return (
        "<section class='step' id='step3'>"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["song_h2"]) + "</h2>"
        "<p class='say'>" + e(w["song_say1"]) + "</p>"
        "<p class='say'>" + w["song_say2_html"] + "</p>"
        "<button class='btn main' id='addMusic' type='button'>" + e(w["add_music"]) + "</button>"
        "<p class='waiting' id='waiting'></p>"
        # her v27: one drop-down, Listen, Remove this song (the old rows are gone)
        "<div class='songpick' id='songPick'><select id='songSel' aria-label='" + e(w["song_aria"], quote=True) + "'></select>"
        "<button class='btn small' id='songPlay' type='button' hidden>" + e(w["listen"]) + "</button>"
        "<button class='linkbtn' id='songRm' type='button' hidden title='" + e(w["song_off_list"], quote=True) + "'>" + e(w["song_remove"]) + "</button>"
        "<audio id='songAudio' preload='none'></audio></div>"
        "<p class='note'>" + w["licence_html"] + "</p>"
        "</section>")


def _vibe_section(w, num, kind="photos"):
    e = html.escape
    rec = default_vibe()
    cards = "".join(
        "<button class='opt' type='button' data-vibe='" + v + "'><b>" + e(w["vibe_%s_b" % v])
        + ("<span class='rec'>" + e(w["vibe_rec"]) + "</span>" if v == rec else "") + "</b>"
        "<span>" + e(w["vibe_%s_s" % v]) + "</span></button>" for v in VIBES)
    return (
        "<section class='step' id='step4'" + _hidden(kind, ("bts", "photos")) + ">"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["vibe_h2"]) + "</h2>"
        "<p class='say'>" + e(w["vibe_say"]) + "</p>"
        "<div class='vibes' id='vibes'>" + cards + "</div>"
        "</section>")


def _direct_section(w, num, kind="bts"):
    """Her step 4, "Would you like to direct this edit?" (reel-maker.html #stepDirect, v27): a note on how the reel
    should go, and the line to copy into the chat. Not on a B-roll page (hers)."""
    e = html.escape
    return (
        "<section class='step' id='stepDirect'" + _hidden(kind, ("bts", "photos")) + ">"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["direct_h2"]) + "</h2>"
        "<p class='say'>" + e(w["direct_say"]) + "</p>"
        "<div class='paste ask photoask'>"
        "<label for='directIn'><b>" + e(w["direct_b"]) + "</b><span class='ex'>" + e(w["direct_ex"]) + "</span></label>"
        "<textarea id='directIn' rows='3' maxlength='" + str(DIRECT_MAX) + "' placeholder='" + e(w["direct_placeholder"], quote=True) + "'></textarea>"
        "<p>" + e(w["direct_then"]) + "</p>"
        "<div class='line'><span id='directPaste'>" + e(w["direct_plain"]) + "</span>"
        "<button class='btn' id='copyDirect' type='button'>" + e(w["copy"]) + "</button></div>"
        "</div></section>")


def _watch_section(w, num, kind="photos"):
    """Her last step, "Watch your reel before you make it" (reel-maker.html #watch, v27): the 9:16 player, the song,
    the pace chips (not on B-roll), the style chips (behind the scenes only), Try another mix, Undo and Redo, her
    line under it, B-roll's words on screen, and Make this one in CapCut. What a kind never shows is left out
    here on the server (hers hid it after load). Save my video (B-roll, A15) is the main button there: the
    finished MP4 with the song and the words, saved into the shoot's Reels folder (save_video_from_page)."""
    e = html.escape
    broll = kind == BROLL_STYLE
    chips = lambda attr, keys, word: "".join("<button type='button' data-" + attr + "='" + k + "'>" + e(w[word % k]) + "</button>" for k in keys)  # noqa: E731
    pace = ("" if broll else
            "<span class='wl'>" + e(w["pv_pace"]) + "</span>"
            "<div class='chips' id='pvPace'>" + chips("pv-vibe", VIBES, "vibe_%s_b") + "</div>")
    styles = ("<div id='pvStyleBox'><span class='wl'>" + e(w["pv_style"]) + "</span>"
              "<div class='chips' id='pvStyle'>" + chips("pv-style", STYLES, "style_%s_b") + "</div></div>" if kind == "bts" else "")
    os_box = ""
    if broll:
        opts = lambda keys, word: "".join("<option value='" + k + "'>" + e(w[word % k]) + "</option>" for k in keys)  # noqa: E731
        os_box = ("<div id='osBox'><span class='wl'>" + e(w["os_wl"]) + "</span>"
                  "<textarea id='osText' rows='2' maxlength='" + str(ONSCREEN_TEXT_MAX) + "' placeholder='" + e(w["os_placeholder"], quote=True) + "'></textarea>"
                  "<p class='say sm oshint'>" + w["os_hint_html"] + "</p>"
                  "<div class='wrow os'><select id='osFont' aria-label='" + e(w["os_font"], quote=True) + "'>" + opts(OS_FONTS, "os_%s") + "</select>"
                  "<select id='osStyle' aria-label='" + e(w["os_style"], quote=True) + "'>" + opts(OS_STYLES, "os_%s") + "</select></div></div>")
    return (
        "<section class='step watch' id='watch'>"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["watch_h2"]) + "</h2>"
        "<p class='say' id='" + ("pvSayBroll" if broll else "pvSayReel") + "'>" + w["pv_say_broll_html" if broll else "pv_say_reel_html"] + "</p>"
        "<div class='wgrid'>"
        "<div class='pvphone' id='pvPhone'>"
        "<img id='pvImg' alt=''><video id='pvVid' playsinline muted preload='auto'></video>"
        "<div class='pvtext' id='pvText' hidden title='" + e(w["os_move"], quote=True) + "'></div>"
        "<i class='pvknob' id='pvKnob' hidden title='" + e(w["os_size"], quote=True) + "'></i>"
        "<div class='pvempty' id='pvEmpty'>" + e(w["pv_empty"]) + "</div>"
        "<button class='pvplay' id='pvPlay' type='button' aria-label='" + e(w["pv_play"], quote=True) + "'>&#9654;</button>"
        "<div class='pvbar'><i id='pvProg'></i></div>"
        "</div>"
        "<div class='wctl'>"
        "<label class='wl' for='pvSong'>" + e(w["pv_song"]) + "</label>"
        "<div class='wrow'><select id='pvSong' aria-label='" + e(w["pv_song"], quote=True) + "'></select>"
        "<button class='btn small' id='pvPart' type='button'>" + e(w["pv_part"]) + "</button></div>"
        + pace + styles +
        "<div class='wrow'><button class='btn small' id='pvMix' type='button'>" + e(w["pv_mix"]) + "</button>"
        "<button class='btn small' id='pvUndo' type='button' disabled title='" + e(w["pv_undo_title"], quote=True) + "'>" + e(w["pv_undo"]) + "</button>"
        "<button class='btn small' id='pvRedo' type='button' disabled>" + e(w["pv_redo"]) + "</button>"
        "<span class='say sm' id='pvMixSay'></span></div>"
        "<p class='say sm' id='pvWords'></p>"
        + os_box +
        "<div class='wrow'>" + ("<button class='btn main' id='pvSaveVid' type='button'>" + e(w["os_save"]) + "</button>" if broll else "")
        + "<button class='btn" + ("" if broll else " main") + "' id='pvMake' type='button'>" + e(w["pv_make"]) + "</button></div>"
        "<p class='say sm' id='pvSaved' role='status'></p>"
        "</div></div>"
        "<audio id='pvAudio' preload='auto'></audio>"
        "</section>")


def trim_panel(w):
    """Her trim panel (reel-maker.html #trim, handoff v25), written above the page's scripts, which wire it up on
    load. Hidden until Trim is pressed on a clip card. On a PC, where no stills are taken from a video yet, one
    line of ours under the timeline says why it has no pictures."""
    e = html.escape

    def nudge(which, word):
        return ("<span>" + e(word) + " <button type='button' data-n='" + which + ":-" + str(TRIM_NUDGE) + "' title='" + e(w["trim_earlier"], quote=True)
                + "' aria-label='" + e(word + ": " + w["trim_earlier"], quote=True) + "'>&#9664;</button>"
                "<button type='button' data-n='" + which + ":" + str(TRIM_NUDGE) + "' title='" + e(w["trim_later"], quote=True)
                + "' aria-label='" + e(word + ": " + w["trim_later"], quote=True) + "'>&#9654;</button></span>")
    return (
        "<div class='trim' id='trim' hidden role='dialog' aria-modal='true' aria-labelledby='trimName'><div class='box'>"
        "<button class='x' id='trimX' type='button' aria-label='" + e(w["trim_close"], quote=True) + "'>&times;</button>"
        "<h3 id='trimName'>" + e(w["trim_title"]) + "</h3>"
        "<p class='hint'>" + e(w["trim_hint"]) + "</p>"
        "<div class='vwrap'><video id='trimVid' playsinline></video><p class='novid' id='trimNoVid' hidden>" + e(w["trim_novid"]) + "</p></div>"
        "<div class='bar' id='trimBar'><div class='film' id='trimFilm'></div>"
        "<div class='dim l' id='trimDimL'></div><div class='dim r' id='trimDimR'></div>"
        "<div class='sel' id='trimSel'><span class='h a' data-h='a' title='" + e(w["trim_start_title"], quote=True) + "'></span>"
        "<span class='h b' data-h='b' title='" + e(w["trim_end_title"], quote=True) + "'></span></div>"
        "<div class='head' id='trimHead'></div></div>"
        "<div class='ticks' id='trimTicks'></div>"
        + ("<p class='pcnote' id='trimPcNote'>" + e(OUR_WORDS["trim_no_stills_pc"]) + "</p>" if pc_footage() else "") +
        "<p class='say' id='trimSay'></p>"
        "<div class='nudges'>" + nudge("a", w["trim_start"])
        + "<button type='button' id='trimPlay'>" + e(w["trim_play"]) + "</button>" + nudge("b", w["trim_end"]) + "</div>"
        "<div class='acts'><button type='button' id='trimCancel'>" + e(w["trim_cancel"]) + "</button>"
        "<button type='button' class='main' id='trimDone'>" + e(w["trim_done"]) + "</button></div>"
        "</div></div>")


def kind_address(kit_name, kind=None):
    """The reel page's address for a shoot: the chooser, or one kind's page. The shoot goes in it by its folder
    name (never a path), as every page's does."""
    return "/reel.html?kit=" + quote(kit_name) + ("&kind=" + kind if kind in KINDS else "")


def talk_card(w, kit_name):
    """The chooser's Talking to camera card (her v27 reel-maker.html: <a class="kind" id="kTalk">; her v23 had it as
    step 1's third card): a plain link to the talking reel's page for the same shoot, written here on the server
    so it works before any script runs. It is a link and nothing more: it saves nothing and leaves this page's
    record as it was. A PC gets the same card: the talking page opens there and says in its own words what a PC
    can't do yet (this_computer.NO_TALKING_PC)."""
    e = html.escape
    return ("<a class='kind' id='kTalk' href='" + e("/talking.html?kit=" + quote(kit_name), quote=True) + "'><b>"
            + e(w["kind_talk_b"]) + "</b><span>" + e(w["kind_talk_s"]) + "</span></a>")


def chooser_section(w, kit_name):
    """Her chooser (v27, #chooser): the four kinds, each a plain link written on the server (hers decided the
    links and the title in its script after the page loaded)."""
    e = html.escape

    def card(kid, kind):
        return ("<a class='kind' id='" + kid + "' href='" + e(kind_address(kit_name, kind), quote=True) + "'><b>"
                + e(w["kind_%s_b" % kind]) + "</b><span>" + e(w["kind_%s_s" % kind]) + "</span></a>")
    return ("<section class='step chooser' id='chooser'>"
            "<h2>" + e(w["chooser_h2"]) + "</h2>"
            "<p class='say'>" + e(w["chooser_say"]) + "</p>"
            "<div class='kinds'>" + card("kBts", "bts") + card("kPhotos", "photos") + talk_card(w, kit_name) + card("kBroll", "broll") + "</div>"
            "</section>")


SECTIONS = [
    ("step0", _footage_section),  # 1. Choose your behind-the-scenes footage (not on a just-photos page)
    ("step1", _order_section),    # 2. Choose your photos (not on a B-roll page)
    ("step3", _song_section),     # 3. Add your song
    ("stepDirect", _direct_section),  # 4. Would you like to direct this edit? (not on a B-roll page)
    ("stepStyle", _style_section),  # 5. What style of behind the scenes is this? (behind the scenes only)
    ("step4", _vibe_section),     # 6. Pick the vibe (not on a B-roll page)
    ("watch", _watch_section),    # 7. Watch your reel before you make it (always the last step, hers)
]


def _rhythms():
    """Her five chips for how often they post (words_page.RHYTHMS: one copy)."""
    try:
        import words_page
        return words_page.RHYTHMS
    except Exception:  # noqa: BLE001
        return ("Every day", "Every other day", "3 a week", "Twice a week", "Once a week")


def _json_for_script(obj):
    """JSON that is safe inside a <script> element (no "</script>", no "<!--")."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _head(w, title, lede_html, back_href, back_words, kit_name, css, all_reels=None):
    """The top of both pages: the bar, the eyebrow, the title and the lede. `all_reels`: the link back to the
    chooser (a kind's page; the chooser has none)."""
    e = html.escape
    links = ("<a class='homelink' id='allReels' href='" + e(kind_address(kit_name), quote=True) + "'>"
             + e(all_reels) + "</a>" if all_reels else "")
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + e(title) + "</title><style>" + css + "</style></head>"
        "<body data-kit='" + e(kit_name, quote=True) + "'>"
        "<div class='wrap'>"
        "<div class='bar'>" + links + "<a class='homelink' id='back' href='" + e(back_href, quote=True) + "'><span aria-hidden='true'>&larr;</span> "
        "<span id='backWords'>" + e(back_words) + "</span></a>" + brand.bar() + "</div>"
        "<header class='head'><span class='eyebrow'>" + e(w["eyebrow"]) + "</span>"
        "<h1 id='title'>" + e(title) + "<em>.</em></h1>"
        "<p class='lede'>" + lede_html + "</p>")


def _back(kit_name, kit_page, w):
    back_href = ("/content/" + quote(kit_name) + "/Post%20kit.html") if kit_page else "/home"
    return back_href, (w["back_kit"] if kit_page else OUR_WORDS["back_home"])


def chooser_html(kit_name, short, kit_page=False):
    """Which reel do you want to create? (her v27): the page with no kind in its address. Her title and lede are
    written here on the server; no script runs and nothing is saved by looking at it."""
    e = html.escape
    w = dict(WORDS)
    w.update(KIND_WORDS)
    title = w["title_chooser"].replace("{short}", short)
    back_href, back_words = _back(kit_name, kit_page, w)
    return (_head(w, title, e(w["chooser_lede"]), back_href, back_words, kit_name, look.head_css() + STYLE + V27_CSS)
            + "</header>" + chooser_section(w, kit_name) + "</div></body></html>")


def page_html(kit_name, short, kit_page=False, kind="photos"):
    """One kind of reel's page (her v27: bts | photos | broll). Its title, its lede, which steps show and the
    step-1 heading are written here on the server (hers decided them in applyKind() after the page loaded)."""
    e = html.escape
    kind = kind if kind in KINDS else "photos"
    w = {k: pc_words(trash_words(v)) for k, v in WORDS.items()}
    w.update({k: pc_words(v) for k, v in KIND_WORDS.items()})
    if this_computer.WINDOWS:          # decision 26: her trim tip's Mac sentence, a PC's way
        w["quick_fix_html"] = w["quick_fix_html"].replace(
            "On a Mac, open it in QuickTime Player and choose Edit › Trim.", OUR_WORDS["trim_pc"])
    w.update(REELS_WORDS)
    w.update(PICK_WORDS)
    w.update(TRIM_WORDS)
    w.update(SELECT_WORDS)
    w.update(EDITOR_WORDS)
    w.update(DIRECT_WORDS)
    w.update(WATCH_WORDS)
    w.update(ONSCREEN_WORDS)
    if pc_footage():                   # decision 26 (v19 review, Nov 7): no footage look on a PC, so no "I find"
        w["clips_empty"] = this_computer.MOMENTS_PC
        w["not_looked_h3"] = w["clips_need_h3"]
        w["not_looked_html"] = this_computer.NOT_LOOKED_PC_HTML
    title = w["title_" + kind].replace("{short}", short)
    data = {"words": dict(w, **OUR_WORDS), "kind": kind, "max": MAX_PICKS, "dragOut": DRAG_OUT, "undoSteps": UNDO_STEPS,
            "saveAfter": SAVE_AFTER_MS, "followEvery": FOLLOW_MS, "defaultVibe": default_vibe(),
            "songEvery": SONG_EVERY_MS, "jobEvery": JOB_EVERY_MS, "footEvery": FOOT_EVERY_MS, "feels": list(FEELS),
            "styles": list(STYLES), "styleMax": STYLE_MAX, "useSeconds": USE_SECONDS, "step": MOMENT_STEP,
            "undoNote": UNDO_NOTE_MS, "stripEvery": STRIP_EVERY,
            "trimMin": MOMENT_MIN, "trimMax": MOMENT_MAX, "trimWindow": TRIM_WINDOW, "trimSpanMin": TRIM_SPAN_MIN,
            "trimNudge": TRIM_NUDGE, "trimGrid": TRIM_GRID, "trimPanel": TRIM_PANEL, "rhythms": list(_rhythms()),
            # the footage editor (v27): a clip up to 15 s, the zoom (one threshold, ours), her 4 px tap rule
            "addMax": ADD_MAX, "zoomOver": ZOOM_OVER, "zoomWindow": ZOOM_WINDOW, "tapPx": TAP_PX,
            # the watch step (v27): her 700 ms, 40 steps of Undo, Another part's step; the words' bounds
            "previewAfter": PREVIEW_AFTER_MS, "pvUndo": PV_UNDO, "partMin": PART_MIN, "partShare": PART_SHARE, "partEnd": PART_END,
            "osX": list(OS_X), "osY": list(OS_Y), "osSize": list(OS_SIZE), "vibes": list(VIBES)}
    # her numbers as written (step 1 to 5; the steps a kind doesn't use are hidden); the page renumbers them (hers)
    steps = "".join(fn(w, i, kind) for i, fn in enumerate((fn for _, fn in SECTIONS if fn), 1))
    back_href, back_words = _back(kit_name, kit_page, w)
    css = look.head_css() + STYLE + REELS_CSS + PICK_CSS + SELECT_CSS + (TRIM_CSS if TRIM_PANEL else "") + OUR_CSS + V27_CSS + EDITOR_CSS + WATCH_CSS
    head = _head(w, title, e(w["lede_" + kind]), back_href, back_words, kit_name, css, w["all_reels"])
    if TRIM_PANEL:                     # her v25 panel sits above the page's scripts (hers), before the wrap: the head is split round it
        head = head.replace("<div class='wrap'>", trim_panel(w) + "<div class='wrap'>", 1)
    toq = ("<div class='toq' id='toqBar' hidden><button class='btn' id='toQueue2' type='button'>" + e(w["toq_btn"]) + "</button>"
           "<span class='went' id='went2' role='status'></span><div id='qAsk2'></div></div>")
    return (
        head + reels_bar(w) + toq + "</header>"
        + steps +
        "<div class='result' id='result'></div>"
        "</div>"
        "<div class='make'><div class='in'><div class='sum' id='sum'></div>"
        "<button class='btn main' id='makeBtn' type='button'>" + e(w["make"]) + "</button></div></div>"
        "<div class='lb' id='lb'><img id='lbimg' alt=''></div>"
        "<script type='application/json' id='reelData'>" + _json_for_script(data) + "</script>"
        "<script>" + DRAG_JS + "</script><script>" + MODEL_JS + "</script><script>" + REELS_JS + "</script><script>" + CORE_JS + "</script>"
        "<script>" + ORDER_JS + "</script><script>" + PHOTOS_JS + "</script><script>" + SONG_JS + "</script><script>" + VIBE_JS + "</script>"
        "<script>" + FOOTAGE_JS + "</script>" + ("<script>" + TRIM_JS + "</script>" if TRIM_PANEL else "")
        + "<script>" + DIRECT_JS + "</script><script>" + MAKE_JS + "</script><script>" + WATCH_JS + "</script><script>" + QUEUE_JS + "</script><script>" + START_JS + "</script>"
        "</body></html>")


def _drag_js():
    import arrange_page
    return arrange_page.DRAG_JS


DRAG_JS = _drag_js()

# The order as a list of {n, h} (her shape: h '' Normal, '+' Longer, '-' Quicker). No page in it.
MODEL_JS = r"""
(function(root){
  'use strict';
  function at(list, n){ for (var i = 0; i < list.length; i++) { if (list[i].n === n) return i; } return -1; }
  function copy(list){ return (list || []).map(function(r){ return {n: r.n, h: r.h || ''}; }); }
  function clampPos(pos, len){ pos = Math.floor(Number(pos)); if (!(pos >= 0)) pos = 0; return pos > len ? len : pos; }
  // Put photo n into the gap before the photo now at pos (pos = length: the end). Already in: it moves there and
  // keeps its mark. Not in and the list full: null.
  function insertAt(list, n, pos, max){
    var from = at(list, n), out = list.slice();
    pos = clampPos(pos, list.length);
    if (from >= 0) {
      if (pos === from || pos === from + 1) return list;
      var it = out.splice(from, 1)[0];
      if (pos > from) pos -= 1;
      out.splice(pos, 0, it);
      return out;
    }
    if (list.length >= max) return null;
    out.splice(pos, 0, {n: n, h: ''});
    return out;
  }
  function takeOut(list, n){ var i = at(list, n); if (i < 0) return list; var out = list.slice(); out.splice(i, 1); return out; }
  function sameNums(a, b){ if (a.length !== b.length) return false; for (var i = 0; i < a.length; i++) { if (a[i].n !== b[i].n) return false; } return true; }
  // where a drop lands among the row's tiles: the first one the pointer is above the bottom of and left of the
  // middle of, or above altogether; none: the end (arrange_page's rule)
  function landing(rects, x, y){
    for (var i = 0; i < rects.length; i++) {
      var r = rects[i];
      if ((y < r.bottom && x < (r.left + r.right) / 2) || y < r.top) return i;
    }
    return rects.length;
  }
  // Several photos to one place (her v25: select several, like Lightroom). ns: their numbers, in the order they
  // are to sit. They land together in the gap before the photo now at pos; one already in the list moves there
  // and keeps its mark, one that is not comes in with the mark they last gave it (marks), or none. Everything
  // else keeps its order. The same order as before: the list itself.
  function many(list, ns, pos, marks){
    var set = {}, by = {}, i;
    ns.forEach(function(n){ set[n] = true; });
    list.forEach(function(r){ by[r.n] = r; });
    pos = clampPos(pos, list.length);
    var keep = function(r){ return !set[r.n]; };
    var out = list.slice(0, pos).filter(keep).concat(
      ns.map(function(n){ return by[n] || {n: n, h: (marks && marks[n]) || ''}; }), list.slice(pos).filter(keep));
    if (out.length === list.length) { for (i = 0; i < out.length; i++) { if (out[i] !== list[i]) return out; } return list; }
    return out;
  }
  root.ReelModel = {at: at, copy: copy, insertAt: insertAt, takeOut: takeOut, sameNums: sameNums, landing: landing, many: many};
})(typeof window !== 'undefined' ? window : this);
"""

# The page's core: the record, saving (retried until it lands), following what changes elsewhere. Each step is
# a part: {fields(): what it saves, adopt(st, first): take a state, follow(st): a newer state arrived while idle}.
CORE_JS = r"""
(function(){
  'use strict';
  var DATA = JSON.parse(document.getElementById('reelData').textContent);
  var W = DATA.words, KIT = document.body.dataset.kit, Q = 'kit=' + encodeURIComponent(KIT), KIND = DATA.kind || '';
  var $ = function(id){ return document.getElementById(id); };
  var esc = function(t){ return String(t).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
  var fill = function(t, o){ return String(t).replace(/\{(\w+)\}/g, function(m, k){ return o && o[k] != null ? o[k] : m; }); };
  // a name this page gives itself, new on every load and kept nowhere: it lets the Assistant tell this page's
  // own save (whose answer never arrived) from a save made in another window
  var PAGE = (Math.random().toString(36).slice(2, 12) + Date.now().toString(36)).replace(/[^a-z0-9]/g, '');
  var parts = [], S = null, rev = 0, stamp = '', blocked = false, REEL = null;
  var saving = false, dirty = false, timer = null, retryT = null, followT = null;

  function notice(text, reload){
    var n = $('notice'); if (!n) return;
    n.textContent = text || '';
    if (reload) { var b = document.createElement('button'); b.className = 'btn small'; b.type = 'button'; b.textContent = W.reload; b.onclick = function(){ location.reload(); }; n.appendChild(b); }
  }
  function photosChanged(){
    blocked = true; dirty = false; clearTimeout(timer); clearTimeout(retryT);
    notice(W.photos_changed, true);
  }
  function fields(){ var out = {}; parts.forEach(function(p){ if (p.fields) { var f = p.fields(); for (var k in f) out[k] = f[k]; } }); return out; }
  function goKind(k){ var u = new URL(location.href); u.searchParams.set('kind', k); location.href = u.toString(); }
  function adopt(st, first){
    // v27: the reel being worked on is of another kind (started or opened in another window, or from the chat):
    // this page reopens it as its own kind rather than showing it in the wrong steps
    if (!first && KIND && st.kind && st.kind !== KIND) { blocked = true; goKind(st.kind); return; }
    S = st; rev = st.rev; stamp = st.stamp;
    REEL = st.current || null;                       // which of the shoot's reels this page is showing (v25)
    if (BAR) BAR.set(st.versions, st.current);
    parts.forEach(function(p){ if (p.adopt) p.adopt(st, first); });
  }
  function withReel(o){ if (REEL) o.reel = REEL; return o; }
  // "This reel is saved exactly as it is first" (hers, before a new reel is started or another opened): true
  // once nothing of this page is waiting to be saved, false when it would not save in a few seconds
  function flush(){
    return new Promise(function(done){
      var t0 = Date.now();
      (function wait(){
        if (blocked || !S) return done(true);
        if (!dirty && !saving) return done(true);
        if (Date.now() - t0 > 6000) return done(false);
        if (dirty && !saving && !retryT) send();
        setTimeout(wait, 50);
      })();
    });
  }
  var BAR = !window.ReelsBar || !$('reels') ? null : window.ReelsBar({
    words: W, flush: flush,
    // a new reel started from this page is this page's kind (v27); the Assistant notes it with the new reel
    post: function(b){ b.kit = KIT; if (b.op === 'new' && KIND) b.kind = KIND; return R_post('/reel-version', b); },
    // v27: the reel now being worked on opens as its own kind (hers kept this page's kind, so a B-roll reel opened
    // from a photos page hid the wrong steps); a reel never chosen opens as this page's kind
    reload: function(j){
      var k = j && j.kind;
      if (k && k !== KIND) { goKind(k); return; }
      location.reload();
    },
    renamed: function(j){ if (typeof j.rev === 'number') rev = j.rev; if (S) { S.versions = j.versions; S.current = j.current; S.rev = rev; } if (R.photoLine) R.photoLine(); if (R.directLine) R.directLine(); }
  });
  function R_post(url, obj){
    return fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(obj)})
      .then(function(r){ if (r.status >= 500) throw new Error('no answer'); return r.json().then(function(j){ return {code: r.status, j: j}; }); });
  }
  function save(){
    var out = $('result'); if (out && out.classList.contains('bad')) out.className = 'result';   // hers: they changed something, the old problem no longer applies
    if (blocked || !S) return;
    dirty = true;
    clearTimeout(timer);
    timer = setTimeout(send, DATA.saveAfter);
  }
  function body(){ return JSON.stringify(withReel({kit: KIT, stamp: stamp, base: rev, page: PAGE, saved: fields()})); }
  function send(){
    clearTimeout(timer); clearTimeout(retryT); retryT = null;
    if (saving || blocked || !dirty || !S) return;
    saving = true; dirty = false;
    fetch('/reel-save', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: body()})
      .then(function(r){
        if (r.status >= 500) throw new Error('no answer');
        return r.json().then(function(j){ return {code: r.status, j: j}; });
      })
      .then(function(res){
        saving = false;
        var j = res.j || {};
        if (res.code === 200 && j.ok) {
          if (typeof j.rev === 'number') rev = j.rev;
          if ($('notice') && $('notice').textContent === W.retry) notice('');
          if (dirty) send();
          return;
        }
        if (res.code === 409 && j.why === 'photos') { photosChanged(); return; }
        if (res.code === 409 && j.why === 'newer' && j.state && j.state.ok) {
          dirty = false;
          adopt(j.state, false);
          notice(W.newer);
          return;
        }
        if (res.code === 404) { dirty = true; notice(j.words || W.cant_reach); retryT = setTimeout(send, 2000); return; }
        notice(j.words || W.cant_reach, true);       // refused in a way trying again will not fix
      })
      .catch(function(){ saving = false; dirty = true; notice(W.retry); retryT = setTimeout(send, 2000); });
  }
  // a change still waiting when the page goes away is sent on its way
  window.addEventListener('pagehide', function(){
    if (!dirty || blocked || !S || saving) return;
    try { fetch('/reel-save', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: body(), keepalive: true}); } catch (e) {}
  });
  function getState(){ return fetch('/reel-state?' + Q, {cache: 'no-store'}).then(function(r){ return r.json(); }); }
  function idle(){ return !!S && !blocked && !saving && !dirty && !(R.busy && R.busy()); }
  // v27: the numbered list grew (photos added) and every photo this page knows kept its number: the page goes on
  // against the new list and offers "Show my new photos" (hers reloads on that press); anything else that changed
  // the list (a photo gone) still stops the page with the reload line
  function onlyGrew(st){
    if (!S || !Array.isArray(st.photos) || !Array.isArray(S.photos) || st.photos.length <= S.photos.length) return false;
    var have = {}; st.photos.forEach(function(p){ have[p.n] = true; });
    return S.photos.every(function(p){ return have[p.n]; });
  }
  function follow(){
    if (document.hidden || !idle()) return;
    var asked = rev;
    getState().then(function(st){
      if (!st || !st.ok || !idle() || rev !== asked) return;
      if (st.stamp !== stamp) {
        if (!onlyGrew(st)) { photosChanged(); return; }
        var k = st.photos.length - S.photos.length;
        stamp = st.stamp;
        if (R.newPhotos) R.newPhotos(k);
      }
      if (st.rev !== rev) { adopt(st, false); return; }          // saved in another window: shown as it is now
      S = st;
      if (BAR) BAR.set(st.versions, st.current);
      parts.forEach(function(p){ if (p.follow) p.follow(st); });
    }).catch(function(){});
  }
  function start(){
    getState().then(function(st){
      if (!st || !st.ok) throw new Error('not ready');
      notice('');
      adopt(st, true);
      if (!followT) followT = setInterval(follow, DATA.followEvery);
    }).catch(function(){
      parts.forEach(function(p){ if (p.unreachable) p.unreachable(); });
      setTimeout(start, 2000);
    });
  }
  var R = window.Reel = {data: DATA, words: W, kit: KIT, q: Q, $: $, esc: esc, fill: fill, part: function(p){ parts.push(p); },
    save: save, notice: notice, start: start, state: function(){ return S; }, busy: null, followNow: follow,
    // several reels (v25): which reel this page shows goes with every ask, so nothing of one reel is ever
    // written into another when a second window has opened a different one
    withReel: withReel, reels: BAR, flush: flush,
    // v27: which kind of reel this page is, and the steps that kind never shows
    kind: KIND, kindHides: function(id){ var el = $(id); return !!(el && el.hasAttribute('data-kind-hidden')); },
    fresh: getState, newPhotos: null,
    // a POST of the page's own (arrange.guard checks it): {code, j}; a server that gave no answer throws
    post: function(url, obj){
      if (url === '/reel-moment' || url === '/reel-make') withReel(obj);
      return fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(obj)})
        .then(function(r){ if (r.status >= 500) throw new Error('no answer'); return r.json().then(function(j){ return {code: r.status, j: j}; }); });
    },
    photoUrl: function(p, size){ return '/kit-photo?' + Q + '&n=' + p.n + '&size=' + size + '&v=' + encodeURIComponent(p.v || ''); },
    // her renumbering: only the steps that show are counted (and a kind's hidden steps stay hidden, v27)
    renumber: function(){ var k = 0; document.querySelectorAll('section.step').forEach(function(s){ if (s.hasAttribute('data-kind-hidden')) s.hidden = true; var n = s.querySelector('.num'); if (!s.hidden && n) n.textContent = ++k; }); }};
  // v27: the kind goes with every save, so a reel reopens as its kind (nothing is written on a plain open)
  if (KIND) R.part({fields: function(){ return {kind: KIND}; }});
})();
"""

# Step 2, her "Put your photos in order", with our drag.
ORDER_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc, M = window.ReelModel, MAX = R.data.max;
  var photos = [], byN = {}, claude = [], claudeBts = [], reel = [], mine = false, mineOrder = null;
  var footage = null;            // step 1 sets this (R.setFootage); until then, no footage
  var marks = {};                // only the Longer / Quicker they set themselves, carried over to the assistant's next order
  var earlier = [];              // the assistant's earlier picks (state.claude_earlier): an order still exactly one of these was never touched
  function marked(list){ return JSON.stringify((list || []).map(function(r){ return [r.n, r.h || '']; })); }
  function untouched(list){ var m = marked(list); return earlier.some(function(e){ return marked(e) === m; }); }
  var undoStack = [], lastSnap = null, undoT = null, pollT = null, stampSeen = null;
  var short = '';
  var reelEl = $('reel'), allEl = $('all'), wrapEl = $('reelwrap'), insEl = document.createElement('div');
  insEl.className = 'ins'; wrapEl.appendChild(insEl);

  var claudeOrder = function(){ return (footage && claudeBts.length) ? claudeBts : claude; };
  function notPicked(){ $('claudeWords').textContent = W.not_picked; }
  // her v25 photo note: which photos they'd like in this reel, and the line to copy into the chat. The reel's
  // name is in the line only when the shoot has more than one reel, "and follow my note" only with a note.
  var photoAsk = '';
  function photoLine(){
    var nm = R.reels ? R.reels.name() : '';
    $('photoPaste').textContent = R.fill(W.photo_for, {short: short}) + (nm ? R.fill(W.photo_reel, {name: nm}) : '') + (photoAsk ? W.photo_note : '');
  }
  R.photoLine = photoLine;
  $('photoAskIn').oninput = function(){ photoAsk = $('photoAskIn').value.trim(); photoLine(); R.save(); };
  // Copy: the page's own copy first (the Claude app's pane allows it from a press), the newer way only if that failed
  $('copyPhoto').onclick = function(){
    var t = $('photoPaste').textContent, ok = false;
    try {
      var r = document.createRange(); r.selectNodeContents($('photoPaste'));
      var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
      ok = document.execCommand('copy');
      s.removeAllRanges();
    } catch (e) { ok = false; }
    if (!ok && navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).catch(function(){});
    $('copyPhoto').textContent = W.copied; setTimeout(function(){ $('copyPhoto').textContent = W.copy; }, 1600);
  };
  function setMode(m){
    mine = m;
    $('useClaude').classList.toggle('on', !mine);
    $('useMine').classList.toggle('on', mine);
  }
  function limit(on){ $('limit').classList.toggle('on', !!on); }

  // ---- select several photos and move them together, like Lightroom (her v25): click one, Shift-click another
  // for everything between, Cmd- or Ctrl-click to add or drop one, Escape to let go. Drag any selected photo and
  // they all go. SEL: the photos selected in the order; ALLSEL: in All your photos. Never saved: it is the
  // page's own, and one action on a selection is one save and one step of Undo. ----
  var SEL = {}, ANCHOR = null, ALLSEL = {}, ALLANCHOR = null;
  var press = {shift: false, add: false, on: null};      // the keys held at the last press, and what it was on
  function size(set){ return Object.keys(set).length; }
  function setOf(list){ var o = {}; list.forEach(function(n){ o[n] = true; }); return o; }
  function selNums(){ return reel.map(function(r){ return r.n; }).filter(function(n){ return SEL[n]; }); }        // as they play
  function allBatch(){ return photos.map(function(p){ return p.n; }).filter(function(n){ return ALLSEL[n]; }); }  // as the shoot has them
  function selectTile(n, m){
    var order = reel.map(function(r){ return r.n; });
    if (m.shift && ANCHOR !== null && order.indexOf(ANCHOR) >= 0) {
      var a = order.indexOf(ANCHOR), b = order.indexOf(n);
      var range = order.slice(Math.min(a, b), Math.max(a, b) + 1);
      SEL = setOf(m.add ? Object.keys(SEL).map(Number).concat(range) : range);
    } else if (m.add) {
      if (SEL[n]) delete SEL[n]; else SEL[n] = true;
      ANCHOR = n;
    } else {
      SEL = (size(SEL) === 1 && SEL[n]) ? {} : setOf([n]);
      ANCHOR = n;
    }
    paintSel();
  }
  // a press on a photo in All your photos: true when it selected (Shift or Cmd/Ctrl), false for a plain click,
  // which adds the photo or takes it out as it always did
  function selectPick(n, m){
    var order = photos.map(function(p){ return p.n; });
    if (m.shift && ALLANCHOR !== null && order.indexOf(ALLANCHOR) >= 0) {
      var a = order.indexOf(ALLANCHOR), z = order.indexOf(n);
      ALLSEL = setOf(order.slice(Math.min(a, z), Math.max(a, z) + 1)); paintSel(); return true;
    }
    if (m.add) { if (ALLSEL[n]) delete ALLSEL[n]; else ALLSEL[n] = true; ALLANCHOR = n; paintSel(); return true; }
    ALLANCHOR = n;
    if (size(ALLSEL)) { ALLSEL = {}; paintSel(); }
    return false;
  }
  function selBar(el, n, say, buttons, attr){
    el.innerHTML = '';
    if (n < 2) { el.hidden = true; return; }
    el.hidden = false;
    var b = document.createElement('b'); b.textContent = R.fill(W.sel_n, {n: n});
    el.appendChild(b); el.appendChild(document.createTextNode(say));
    buttons.forEach(function(x){
      var k = document.createElement('button'); k.type = 'button'; k.setAttribute(attr, x[0]); k.textContent = x[1];
      k.onclick = function(e){ e.preventDefault(); x[2](); };
      el.appendChild(k);
    });
  }
  function markAll(h){
    reel = reel.map(function(r){ if (!SEL[r.n]) return r; marks[r.n] = h; return {n: r.n, h: h}; });
    refresh();
  }
  function paintSel(){
    var inReel = setOf(reel.map(function(r){ return r.n; }));
    Object.keys(SEL).forEach(function(n){ if (!inReel[n]) delete SEL[n]; });        // a photo taken out is let go
    reelEl.querySelectorAll('.tile').forEach(function(t){ t.classList.toggle('picked', !!SEL[+t.dataset.n]); });
    allEl.querySelectorAll('.pick').forEach(function(t){ t.classList.toggle('picked', !!ALLSEL[+t.dataset.n]); });
    selBar($('reelSel'), size(SEL), W.sel_reel_say, [
      ['long', W.sel_longer, function(){ markAll('+'); }], ['quick', W.sel_quicker, function(){ markAll('-'); }],
      ['plain', W.sel_neither, function(){ markAll(''); }],
      ['out', W.sel_out, function(){ reel = reel.filter(function(r){ return !SEL[r.n]; }); SEL = {}; setMode(true); refresh(); }],
      ['clear', W.sel_clear, function(){ SEL = {}; paintSel(); }]], 'data-s');
    selBar($('allSel'), size(ALLSEL), W.sel_all_say, [
      ['add', W.sel_add, function(){ if (addBatch(allBatch(), reel.length)) { ALLSEL = {}; paintSel(); } }],
      ['clear', W.sel_clear, function(){ ALLSEL = {}; paintSel(); }]], 'data-a');
  }
  // photos from All your photos, in the shoot's order, to a place in the reel (hers). More than a reel holds:
  // nothing is added and the line under the reel says so (ours, as for one photo).
  function addBatch(ns, at){
    var next = M.many(reel, ns, at, marks);
    if (next.length > MAX) { limit(true); return false; }
    reel = next; setMode(true); refresh();
    return true;
  }
  document.addEventListener('pointerdown', function(e){ press.on = e.target; }, true);
  document.addEventListener('pointerup', function(e){ press.shift = !!e.shiftKey; press.add = !!(e.metaKey || e.ctrlKey); }, true);
  document.addEventListener('keydown', function(e){
    if (e.target && e.target.closest && e.target.closest('input,textarea')) return;
    if (e.key === 'Escape' && (size(SEL) || size(ALLSEL))) { SEL = {}; ALLSEL = {}; paintSel(); }
  });

  // ---- drawing ----
  function picture(holder, p, size){
    var wait = holder.querySelector('.wait');
    if (p && p.have) {
      var img = holder.querySelector('img');
      if (!img) {
        img = document.createElement('img'); img.alt = R.fill(W.photo_alt, {n: p.n}); img.decoding = 'async';
        if (holder.classList.contains('pick')) img.loading = 'lazy';
        holder.insertBefore(img, holder.firstChild);
      }
      var u = R.photoUrl(p, size);
      if (img.getAttribute('src') !== u) img.setAttribute('src', u);
      if (wait) wait.remove();
    } else if (!wait) {
      wait = document.createElement('span'); wait.className = 'wait';
      holder.insertBefore(wait, holder.firstChild);
    }
    if (wait) wait.textContent = p && p.missing ? W.cant_read : W.getting_ready;
  }
  function renderReel(){
    reelEl.innerHTML = '';
    reel.forEach(function(r, i){
      var p = byN[r.n]; if (!p) return;
      var t = document.createElement('div');
      t.className = 'tile' + (r.h === '+' ? ' long' : r.h === '-' ? ' quick' : '');
      t.dataset.n = r.n;
      t.innerHTML = '<div class="ph"><span class="pos">' + (i + 1) + '</span>' +
        '<button class="x" type="button" title="' + esc(W.take_out) + '" aria-label="' + esc(R.fill(W.take_out_label, {n: i + 1})) + '">&times;</button></div>' +
        '<div class="hold"><button class="lng ' + (r.h === '+' ? 'on' : '') + '" type="button">' + esc(W.longer) + '</button>' +
        '<button class="qk ' + (r.h === '-' ? 'on' : '') + '" type="button">' + esc(W.quicker) + '</button></div>';
      picture(t.querySelector('.ph'), p, 's');
      reelEl.appendChild(t);
    });
    var n = reel.length, c = $('count');
    var longs = reel.filter(function(r){ return r.h === '+'; }).length, quicks = reel.filter(function(r){ return r.h === '-'; }).length;
    c.textContent = R.fill(n === 1 ? W.one_photo : W.photos, {n: n}) + (longs ? R.fill(W.n_longer, {k: longs}) : '') +
      (quicks ? R.fill(W.n_quicker, {k: quicks}) : '') + (n && n < 6 ? W.few : n > 20 ? W.lots : '');
    c.className = 'count' + ((n && n < 6) || n > 20 ? ' warn' : '');
    $('step1').classList.toggle('done', n >= 1);
    paintSel();
    if (R.changed) R.changed();                 // the bar at the bottom (hers: summary())
  }
  function buildAll(){
    allEl.innerHTML = '';
    photos.forEach(function(p){
      var b = document.createElement('div');
      b.className = 'pick'; b.dataset.n = p.n; b.setAttribute('role', 'button'); b.tabIndex = 0;
      b.innerHTML = '<button class="zoom" type="button" title="' + esc(W.zoom) + '" aria-label="' + esc(W.zoom) + '">&#10530;</button><span class="badge"></span>';
      picture(b, p, 's');
      b.onkeydown = function(e){ if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(p.n); } };
      // a click that came with no press of a pointer before it (detail 0: VoiceOver's VO-Space, Switch Control, a
      // script) adds or takes out the photo as hers does; a real press is the drag code's (its click callback)
      b.onclick = function(e){
        if (e.detail !== 0 || (e.target.closest && e.target.closest('.zoom'))) return;
        if (!selectPick(p.n, {shift: !!e.shiftKey, add: !!(e.metaKey || e.ctrlKey)})) toggle(p.n);
      };
      b.querySelector('.zoom').onclick = function(e){ e.stopPropagation(); openBig(p.n); };
      allEl.appendChild(b);
    });
  }
  function renderAll(){
    var pos = {}; reel.forEach(function(r, i){ pos[r.n] = i + 1; });
    allEl.querySelectorAll('.pick').forEach(function(el){
      var p = pos[+el.dataset.n];
      el.classList.toggle('in', !!p);
      el.querySelector('.badge').textContent = p || '';
      el.classList.toggle('picked', !!ALLSEL[+el.dataset.n]);
    });
  }
  function refreshPictures(){
    reelEl.querySelectorAll('.tile').forEach(function(t){ picture(t.querySelector('.ph'), byN[+t.dataset.n], 's'); });
    allEl.querySelectorAll('.pick').forEach(function(b){ picture(b, byN[+b.dataset.n], 's'); });
  }
  function track(){
    var s = JSON.stringify({reel: reel, mine: mine});
    if (lastSnap !== null && s !== lastSnap) { undoStack.push(lastSnap); if (undoStack.length > R.data.undoSteps) undoStack.shift(); }
    lastSnap = s;
    $('undoBtn').disabled = !undoStack.length;
  }
  function refresh(){ limit(false); renderReel(); renderAll(); R.save(); track(); }

  // ---- the two orders ----
  function followClaude(){        // on "Let my assistant choose", always show the assistant's latest order
    if (mine) return;
    var c = claudeOrder();
    if (!c.length) return;
    if (M.sameNums(c, reel)) {                // same photos: keep their Longer / Quicker marks...
      if (marked(c) !== marked(reel) && untouched(reel)) {      // ...unless they never set any: still an earlier pick of the assistant's, so its newest marks show
        reel = M.copy(c); renderReel(); renderAll(); track();
      }
      return;
    }
    reel = c.map(function(r){ return {n: r.n, h: marks[r.n] !== undefined ? marks[r.n] : (r.h || '')}; });
    renderReel(); renderAll(); track();
  }
  function setFootage(v){
    footage = v;
    $('claudeRec').hidden = v !== true;
    $('claudeWords').textContent = v === true ? W.claude_words_bts : W.claude_words;
    if (!claudeOrder().length) notPicked();
    R.renumber(); followClaude();
  }
  R.setFootage = setFootage;
  // Claude's order with footage (her claude_bts), from the footage look: followed like a fresh pick (hers)
  R.setClaudeBts = function(list){
    var b = known(list);
    if (JSON.stringify(b) === JSON.stringify(claudeBts)) return;
    claudeBts = b;
    $('claudeWords').textContent = footage === true ? W.claude_words_bts : W.claude_words;
    if (!claudeOrder().length) notPicked();
    followClaude();
  };
  R.order = function(){ return M.copy(reel); };
  $('useClaude').onclick = function(){
    var c = claudeOrder();
    if (!c.length) { notPicked(); return; }
    if (mine) mineOrder = M.copy(reel);         // keep theirs before showing the assistant's
    reel = M.copy(c);
    setMode(false); refresh();
  };
  $('useMine').onclick = function(){
    if (!mine && mineOrder && mineOrder.length) reel = M.copy(mineOrder);   // their own order, as they left it
    setMode(true); $('allBox').open = true; refresh();
  };
  function toggle(n){
    var i = M.at(reel, n);
    if (i >= 0) reel.splice(i, 1);
    else { if (reel.length >= MAX) { limit(true); return; } reel.push({n: n, h: ''}); }
    setMode(true); refresh();
  }
  reelEl.addEventListener('click', function(e){
    if (drag.justDragged) return;
    var b = e.target.closest('button'); if (!b) return;
    var t = b.closest('.tile'); if (!t) return;
    var n = +t.dataset.n, i = M.at(reel, n); if (i < 0) return;
    e.stopPropagation();
    if (b.classList.contains('x')) { reel.splice(i, 1); setMode(true); refresh(); }
    else if (b.classList.contains('lng')) { reel[i] = {n: n, h: reel[i].h === '+' ? '' : '+'}; marks[n] = reel[i].h; refresh(); }
    else if (b.classList.contains('qk')) { reel[i] = {n: n, h: reel[i].h === '-' ? '' : '-'}; marks[n] = reel[i].h; refresh(); }
  });
  $('undoBtn').onclick = function(){
    if (!undoStack.length) return;
    var s = JSON.parse(undoStack.pop());
    reel = s.reel; setMode(s.mine);
    lastSnap = JSON.stringify({reel: reel, mine: mine});
    limit(false); renderReel(); renderAll(); R.save();
    $('undoBtn').disabled = !undoStack.length;
    $('undoSay').textContent = W.undone; clearTimeout(undoT); undoT = setTimeout(function(){ $('undoSay').textContent = ''; }, 1500);
  };

  // ---- the big view (hers: tap anywhere to close; Escape too) ----
  var lb = $('lb'), lbimg = $('lbimg');
  function openBig(n){ var p = byN[n]; if (!p || !p.have) return; lbimg.src = R.photoUrl(p, 'l'); lbimg.alt = R.fill(W.photo_alt, {n: n}); lb.classList.add('on'); }
  lb.onclick = function(){ lb.classList.remove('on'); };
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape' && lb.classList.contains('on')) lb.classList.remove('on'); });

  // ---- dragging (ours: a photo is lifted and a bar shows where it will land) ----
  var target = null, riding = null;      // riding: the selection being dragged, {from: 'row' | 'all', ns}, or false
  function ride(t){                      // once a drag: is this photo one of several selected? Then they all go
    var n = +t.dataset.n, row = t.classList.contains('tile');
    riding = false;
    if (row && SEL[n] && size(SEL) > 1) riding = {from: 'row', ns: selNums()};
    else if (!row && ALLSEL[n] && size(ALLSEL) > 1) riding = {from: 'all', ns: allBatch()};
    if (!riding) return;
    if (row) reelEl.querySelectorAll('.tile.picked').forEach(function(k){ if (k !== t) k.classList.add('riding'); });
    var lift = document.querySelector('.arr-lift');
    if (lift) lift.dataset.count = riding.ns.length;          // her tag: "3 photos"
  }
  function rideOver(){
    reelEl.querySelectorAll('.riding').forEach(function(k){ k.classList.remove('riding'); });
    var r = riding; riding = null;
    return r;
  }
  function inside(r, x, y){ return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom; }
  function clearIns(){ insEl.classList.remove('on'); }
  function showIns(pos, tiles, y){
    var wr = wrapEl.getBoundingClientRect(), left, top, h;
    if (!tiles.length) { left = 6; top = 8; h = Math.max(60, reelEl.clientHeight - 16); }
    else {
      var a = pos < tiles.length ? tiles[pos] : null, before = pos > 0 ? tiles[pos - 1] : null, useBefore = !a, r;
      if (a && before) { var ar = a.getBoundingClientRect(), br = before.getBoundingClientRect(); if (ar.top > br.top + 4 && y < ar.top) useBefore = true; }
      if (useBefore) { r = before.getBoundingClientRect(); left = r.right - wr.left + 3; }
      else { r = a.getBoundingClientRect(); left = r.left - wr.left - 7; }
      top = r.top - wr.top; h = r.height;
    }
    insEl.style.left = left + 'px'; insEl.style.top = top + 'px'; insEl.style.height = h + 'px';
    insEl.classList.add('on');
  }
  function over(x, y, t){
    clearIns(); target = null;
    if (riding === null) ride(t);
    var n = +t.dataset.n, at = M.at(reel, n), fromRow = t.classList.contains('tile');
    if (inside(wrapEl.getBoundingClientRect(), x, y)) {
      var tiles = Array.prototype.slice.call(reelEl.querySelectorAll('.tile'));
      var pos = M.landing(tiles.map(function(k){ return k.getBoundingClientRect(); }), x, y);
      if (riding) {                                           // the whole selection lands here, in its order
        var next = M.many(reel, riding.ns, pos, marks);
        if (next === reel) return;                            // where they already are
        if (next.length > MAX) { target = {kind: 'full'}; return; }
        target = {kind: 'many', pos: pos};
        showIns(pos, tiles, y);
        return;
      }
      if (at >= 0 && (pos === at || pos === at + 1)) return;          // where it already is
      if (at < 0 && reel.length >= MAX) { target = {kind: 'full'}; return; }
      target = {kind: 'in', pos: pos};
      showIns(pos, tiles, y);
      return;
    }
    if (R.data.dragOut && fromRow && inside(allEl.getBoundingClientRect(), x, y)) target = {kind: 'out'};
  }
  function drop(t){
    var n = +t.dataset.n, tg = target, went = rideOver();
    target = null; clearIns();
    if (!tg) return;
    if (tg.kind === 'full') { limit(true); return; }
    if (tg.kind === 'many') {
      if (!went) return;
      if (went.from === 'all') { if (addBatch(went.ns, tg.pos)) { ALLSEL = {}; paintSel(); } return; }
      var moved = M.many(reel, went.ns, tg.pos, marks);
      if (moved === reel) return;
      reel = moved; setMode(true); refresh();
      return;
    }
    if (tg.kind === 'out') { reel = M.takeOut(reel, n); setMode(true); refresh(); return; }
    var next = M.insertAt(reel, n, tg.pos, MAX);
    if (next == null) { limit(true); return; }
    if (next === reel) return;
    reel = next; setMode(true); refresh();
  }
  var drag = window.arrangeDrag({
    tileOf: function(el){
      var t = el && el.closest ? el.closest('.tile, .pick') : null;
      return t && (reelEl.contains(t) || allEl.contains(t)) ? t : null;
    },
    canDrag: function(t, e){ return !!R.state() && !(e.pointerType === 'touch' && t.classList.contains('pick')); },
    picture: function(t){ return t.classList.contains('tile') ? t.querySelector('.ph') : t; },
    over: over, drop: drop,
    cancel: function(){ target = null; clearIns(); rideOver(); },
    // a press with no drag. Below: a plain click adds the photo or takes it out, as before; with Shift or
    // Cmd/Ctrl it selects. In the order: a click on the photo itself selects it (hers).
    click: function(t){
      var n = +t.dataset.n;
      if (t.classList.contains('pick')) { if (!selectPick(n, press)) toggle(n); return; }
      if (press.on && press.on.closest && press.on.closest('.ph')) selectTile(n, press);
    },
    scrollBox: null
  });
  R.busy = function(){ return drag.busy(); };

  // ---- the state from the Assistant ----
  function known(list){ return (list || []).filter(function(r){ return !!byN[r.n]; }).map(function(r){ return {n: r.n, h: r.h || ''}; }); }
  function stillMaking(){ return photos.some(function(p){ return !p.have && !p.missing; }); }
  function pollPictures(){
    if (pollT || !stillMaking()) return;
    pollT = setInterval(function(){
      fetch('/reel-state?' + R.q, {cache: 'no-store'}).then(function(r){ return r.json(); }).then(function(st){
        if (!st || !st.ok || st.stamp !== stampSeen) return;
        photos = st.photos; photos.forEach(function(p){ byN[p.n] = p; });
        refreshPictures();
        if (!stillMaking()) { clearInterval(pollT); pollT = null; }
      }).catch(function(){});
    }, 1500);
  }
  R.part({
    fields: function(){
      if (mine) mineOrder = M.copy(reel);
      return {picks: M.copy(reel), mine: mine, mine_picks: mineOrder ? M.copy(mineOrder) : null, photo_ask: photoAsk};
    },
    adopt: function(st, first){
      short = st.short;                // the title is the server's now (v27: it says the reel's kind)
      var back = $('back');
      if (st.kit_page) { back.href = '/content/' + encodeURIComponent(R.kit) + '/Post%20kit.html'; $('backWords').textContent = W.back_kit; }
      var rebuild = stampSeen !== st.stamp;
      stampSeen = st.stamp;
      photos = st.photos; byN = {}; photos.forEach(function(p){ byN[p.n] = p; });
      claude = known(st.claude);
      claudeBts = known(st.claude_bts);
      earlier = (st.claude_earlier || []).map(known);
      var saved = st.saved;
      // their note for this reel's photos: never changed under their hand
      if (first || document.activeElement !== $('photoAskIn')) {
        photoAsk = saved && typeof saved.photo_ask === 'string' ? saved.photo_ask.trim() : '';
        $('photoAskIn').value = saved && typeof saved.photo_ask === 'string' ? saved.photo_ask : '';
      }
      photoLine();
      if (saved && Array.isArray(saved.picks)) {
        reel = known(saved.picks);
        mine = !!saved.mine;
        // saved before the assistant picked again, and never touched by them: the newest pick's marks show
        if (!mine && M.sameNums(claude, reel) && marked(claude) !== marked(reel) && untouched(reel)) reel = M.copy(claude);
        mineOrder = Array.isArray(saved.mine_picks) ? known(saved.mine_picks) : (mine ? M.copy(reel) : null);
        if (saved.footage === true || saved.footage === false) footage = saved.footage;
      } else {
        reel = M.copy(claude);
        mine = !claude.length;
      }
      if (rebuild) buildAll();
      setMode(mine); renderReel(); renderAll();
      if (first) {
        setFootage(footage);
        if (!reel.length) $('allBox').open = true;
      } else {
        $('claudeWords').textContent = footage === true ? W.claude_words_bts : W.claude_words;
        if (!claudeOrder().length) notPicked();
      }
      track();
      pollPictures();
    },
    follow: function(st){
      var c = known(st.claude);
      if (JSON.stringify(c) !== JSON.stringify(claude)) {          // a fresh pick from the assistant
        claude = c;
        earlier = (st.claude_earlier || []).map(known);
        $('claudeWords').textContent = footage === true ? W.claude_words_bts : W.claude_words;
        if (!claudeOrder().length) notPicked();
        followClaude();
      }
      R.setClaudeBts(st.claude_bts);
    },
    unreachable: function(){
      var r = $('reel');
      if (r && !$('reachLine')) { var p = document.createElement('p'); p.className = 'say'; p.id = 'reachLine'; p.textContent = W.reach; wrapEl.parentNode.insertBefore(p, wrapEl); }
    }
  });
  R.part({adopt: function(){ var l = $('reachLine'); if (l) l.remove(); }});
})();
"""

# Her v27, in step 2: + Add photos opens the shoot's Photos folder, the page notices new photos by itself (the
# core's follow: the list grew and every photo kept its number) and offers "Show my new photos", which saves
# what is waiting and reloads (hers). And her shadow under the order once it is stuck at the top.
PHOTOS_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc;
  var say = $('addPhotosSay'), btn = $('addPhotos');
  if (!say || !btn) return;
  var k0 = 0;
  R.newPhotos = function(k){
    k0 += k;
    say.innerHTML = esc(R.fill(k0 === 1 ? W.new_photo : W.new_photos, {k: k0})) + ' <button class="btn small main" id="showNew" type="button">' + esc(W.show_new) + '</button>';
    $('showNew').onclick = function(){ $('showNew').disabled = true; R.flush().then(function(){ location.reload(); }); };
  };
  btn.onclick = function(){
    say.textContent = W.opening_photos;
    R.post('/reel-open', {kit: R.kit, what: 'photos'}).then(function(res){
      say.textContent = (res.j && res.j.words) || W.cant_open_photos;
    }).catch(function(){ say.textContent = W.cant_open_photos; });
  };
  var stick = $('reelStick');
  function shadow(){ if (stick) stick.classList.toggle('stuck', stick.getBoundingClientRect().top <= 1 && $('allBox').open); }
  window.addEventListener('scroll', shadow, {passive: true}); window.addEventListener('resize', shadow);
})();
"""

# Step 3, her "Add your song": the songs in the shoot's Music and Photos folders, by id; No song; a new file is
# picked by itself.
SONG_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc;
  var songs = [], seen = null, song = null;          // song: null (not picked yet), '' (No song), or a song's id
  var sel = $('songSel'), play = $('songPlay'), rm = $('songRm'), audio = $('songAudio');
  R.song = function(){ return song; };
  R.songName = function(){ var s = songs.filter(function(x){ return x.id === song; })[0]; return s ? s.name : ''; };
  R.songs = function(){ return songs.slice(); };
  // the watch step's song drop-down (v27) picks the song as step 3's does
  R.setSong = function(id){ song = id; stopSong(); renderSongs(); R.save(); if (R.changed) R.changed(); };
  // hers (renderSongPick): "Choose a song…" until one is picked, each song (a recording says so), then No song
  function renderSongs(){
    var keep = sel.value;
    sel.innerHTML = (song === null ? '<option value="__" selected disabled>' + esc(W.song_choose) + '</option>' : '') +
      songs.map(function(s){ return '<option value="' + esc(s.id) + '">' + esc(s.name) + (s.kind === 'video' ? esc(W.song_rec_tag) : '') + '</option>'; }).join('') +
      '<option value="">' + esc(W.song_none) + '</option>';
    if (song !== null) sel.value = song; else if (keep === '__' || !keep) sel.value = '__';
    play.hidden = !song; rm.hidden = !song;
    if (!song) stopSong();
    $('step3').classList.toggle('done', song !== null);
  }
  function stopSong(){ try { audio.pause(); } catch (e) {} play.textContent = W.listen; }
  sel.onchange = function(){
    if (sel.value === '__') return;
    song = sel.value; stopSong(); renderSongs(); R.save(); if (R.changed) R.changed();
  };
  // Listen: the song as it is, or a recording's sound, by its id (hers: /reel/song)
  play.onclick = function(){
    if (!song) return;
    if (!audio.paused) { stopSong(); return; }
    var u = '/reel-song?' + R.q + '&id=' + encodeURIComponent(song);
    if (audio.getAttribute('src') !== u) audio.setAttribute('src', u);
    audio.play().then(function(){ play.textContent = W.stop; }).catch(function(){});
  };
  audio.addEventListener('ended', function(){ play.textContent = W.listen; });
  audio.addEventListener('pause', function(){ play.textContent = W.listen; });
  // Remove this song: two taps (hers), then the Assistant moves it to the Trash and the reel goes back to no song
  var sureT = null;
  function unsure(){ clearTimeout(sureT); sureT = null; rm.classList.remove('sure'); rm.textContent = W.song_remove; }
  rm.onclick = function(){
    if (!song) return;
    if (!rm.classList.contains('sure')) {
      rm.classList.add('sure'); rm.textContent = W.song_sure;
      clearTimeout(sureT); sureT = setTimeout(unsure, 4000);
      return;
    }
    clearTimeout(sureT); sureT = null;
    rm.classList.remove('sure'); rm.textContent = W.song_removing; rm.disabled = true;
    var sid = song;
    stopSong();
    R.post('/reel-song-remove', {kit: R.kit, song: sid}).then(function(res){
      var j = res.j || {};
      rm.disabled = false; rm.textContent = W.song_remove;
      if (res.code === 404 && !j.songs) { $('waiting').textContent = W.song_remove_soon; return; }
      $('waiting').textContent = j.words || (j.ok ? W.song_trashed : W.didnt_work);
      if (Array.isArray(j.songs)) take(j.songs, true);
      if (j.ok && song === sid) song = null;      // the Assistant cleared the pick itself; its record is adopted on the next look
      renderSongs(); if (R.changed) R.changed();
      if (j.ok) R.followNow();
    }).catch(function(){ rm.disabled = false; rm.textContent = W.song_remove; $('waiting').textContent = W.no_server_short; });
  };
  // hers (loadSongs): a file that wasn't there on the last look is picked by itself
  function take(list, quiet){
    var fresh = seen && !quiet ? list.filter(function(s){ return !seen[s.id]; }) : [];
    songs = list; seen = {}; list.forEach(function(s){ seen[s.id] = true; });
    if (fresh.length) { song = fresh[0].id; R.save(); $('waiting').textContent = R.fill(W.got_it, {name: fresh[0].name}); }
    if (song && !songs.some(function(s){ return s.id === song; })) song = null;
    renderSongs(); if (R.changed) R.changed();
  }
  function loadSongs(){
    return fetch('/reel-songs?' + R.q, {cache: 'no-store'}).then(function(r){ return r.json(); })
      .then(function(j){ if (j && j.ok && Array.isArray(j.songs)) take(j.songs); }).catch(function(){});
  }
  $('addMusic').onclick = function(){
    $('waiting').textContent = W.opening_music;
    R.post('/reel-open', {kit: R.kit, what: 'music'}).then(function(res){
      $('waiting').textContent = (res.j && res.j.words) || W.cant_open;
      loadSongs();
    }).catch(function(){ $('waiting').textContent = W.cant_open; });
  };
  setInterval(function(){ if (!document.hidden && R.state()) loadSongs(); }, R.data.songEvery);
  R.part({
    fields: function(){ return {song: song}; },
    adopt: function(st, first){
      var sv = st.saved || {};
      song = (sv.song === undefined || sv.song === null) ? null : sv.song;
      if (first) seen = null;
      take(st.songs || []);
    }
  });
})();
"""

# Step 5, her "Pick the vibe".
VIBE_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, $ = R.$, vibe = R.data.defaultVibe;
  var cards = document.querySelectorAll('#vibes .opt');
  R.vibe = function(){ return vibe; };
  function renderVibes(){
    cards.forEach(function(b){ b.classList.toggle('on', b.dataset.vibe === vibe); });
    $('step4').classList.add('done');
  }
  cards.forEach(function(b){ b.onclick = function(){ vibe = b.dataset.vibe; renderVibes(); R.save(); if (R.changed) R.changed(); }; });
  R.setVibe = function(v){ if (R.data.vibes.indexOf(v) < 0) return; vibe = v; renderVibes(); R.save(); if (R.changed) R.changed(); };   // the watch step's chips (v27)
  R.part({
    fields: function(){ return {vibe: vibe}; },
    adopt: function(st){ var sv = st.saved || {}; vibe = sv.vibe || R.data.defaultVibe; renderVibes(); }
  });
  renderVibes();
})();
"""

# Step 1, her "Behind-the-scenes footage?", and step 4, her "What style of behind the scenes is this?": the two
# cards, Add my footage, the videos, Good to know, the line to copy, the notes and the feel, the moment cards, the
# player and its strip, and the four styles. Videos by their key, moments by their id; the server keeps the moments.
FOOTAGE_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc, fill = R.fill, D = R.data;
  var footage = null, style = 'first', sel = {}, ask = '', feel = '', moments = [], vids = [], short = '', vsig = null;
  var STYLE_PICK = {first: {max: D.styleMax.first, say: W.pick_first}, reveal: {max: D.styleMax.reveal, say: W.pick_reveal},
    backforth: {max: D.styleMax.backforth, say: W.pick_backforth}, bookends: {max: D.styleMax.bookends, say: W.pick_bookends},
    broll: {max: D.styleMax.broll, say: W.pick_broll}};
  var STYLE_WORDS = {first: W.style_first_b, reveal: W.style_reveal_b, backforth: W.style_backforth_b, bookends: W.style_bookends_b, broll: W.kind_broll_b};
  var PICK_AT = /^Your pick at /;           // her label for a clip of theirs that has no name from the chat yet
  // hers: 0:04, 1:02.5; and fmt2, always with the tenth: 0:31.6
  function mmss(t){ t = Math.max(0, t); var m = Math.floor(t / 60), s = t - m * 60; return m + ':' + (s < 10 ? '0' : '') + (s % 1 ? s.toFixed(1) : Math.round(s)); }
  function fmt2(t){ t = Math.max(0, t); var m = Math.floor(t / 60), s = t - m * 60; return m + ':' + (s < 10 ? '0' : '') + s.toFixed(1); }
  function tenth(t){ return Math.round(t * 10) / 10; }
  function videoUrl(key){ return '/reel-video?' + R.q + '&key=' + encodeURIComponent(key); }
  function stripUrl(key, n){ return '/reel-strip?' + R.q + '&key=' + encodeURIComponent(key) + '&n=' + n; }
  function stillUrl(id){ return '/reel-moment-still?' + R.q + '&id=' + encodeURIComponent(id); }
  function summary(){ if (R.changed) R.changed(); }
  R.footage = function(){ return footage; };

  // ---- footage on or off is the kind's (v27: the chooser decides; her setFootage, with no cards) ----
  function setFootage(v){
    footage = v;
    $('btsBox').hidden = v !== true;
    $('stepStyle').hidden = v !== true || R.kindHides('stepStyle');
    $('step0').classList.toggle('done', v === true && vids.length > 0);
    R.setFootage(v);                 // step 2: the recommended tag, its words, the assistant's footage order; renumbers
    renderStyles();
  }
  $('addFootage').onclick = function(){
    $('footWaiting').textContent = W.opening_footage;
    R.post('/reel-open', {kit: R.kit, what: 'footage'}).then(function(res){
      $('footWaiting').textContent = (res.j && res.j.words) || W.cant_open;
      loadFootage();
    }).catch(function(){ $('footWaiting').textContent = W.cant_open; });
  };

  // ---- the line to copy, the notes and the feel (hers) ----
  function pasteLine(){ $('pasteWords').textContent = fill(W.paste_for, {short: short}) + (ask || feel ? W.paste_notes : ''); }
  $('askIn').oninput = function(){ ask = $('askIn').value.trim(); pasteLine(); R.save(); };
  var feelOwnOpen = false;           // "Something else": their own word for how it should feel
  function showFeel(){
    var own = feelOwnOpen || (feel && D.feels.indexOf(feel) < 0);
    document.querySelectorAll('#feelRow button').forEach(function(b){ b.classList.toggle('on', b.dataset.f === 'own' ? !!own : b.dataset.f === feel); });
    $('feelOwn').hidden = !own;
    if (own && D.feels.indexOf(feel) < 0 && document.activeElement !== $('feelOwn')) $('feelOwn').value = feel;
  }
  document.querySelectorAll('#feelRow button').forEach(function(b){ b.onclick = function(){
    if (b.dataset.f === 'own') {
      feelOwnOpen = !(feelOwnOpen || (feel && D.feels.indexOf(feel) < 0));
      feel = feelOwnOpen ? $('feelOwn').value.trim() : '';
      showFeel(); if (feelOwnOpen) $('feelOwn').focus();
    } else { feelOwnOpen = false; feel = feel === b.dataset.f ? '' : b.dataset.f; showFeel(); }
    pasteLine(); R.save();
  }; });
  $('feelOwn').oninput = function(){ feel = $('feelOwn').value.trim(); pasteLine(); R.save(); };
  // Copy: the page's own copy first (the Claude app's pane allows it from a press), the newer way only if that failed
  function copyOf(span, btn){
    var t = span.textContent, ok = false;
    try {
      var r = document.createRange(); r.selectNodeContents(span);
      var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
      ok = document.execCommand('copy');
      s.removeAllRanges();
    } catch (e) { ok = false; }
    if (!ok && navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).catch(function(){});
    btn.textContent = W.copied; setTimeout(function(){ btn.textContent = W.copy; }, 1600);
  }
  $('copyLine').onclick = function(){ copyOf($('pasteWords'), $('copyLine')); };
  $('descCopy').onclick = function(){ copyOf($('descWords'), $('descCopy')); };

  // ---- the videos and Good to know (hers: renderVideos; since v27 one drop-down that opens to the cards) ----
  var SETTLED = {ready: 1, failed: 1, lowspace: 1, pc: 1, hevc_pc: 1};
  function pic(v){ var st = v.strip || []; return st.length ? '<img src="' + esc(stripUrl(v.key, st[Math.floor(st.length / 3)].n)) + '" alt="">' : '<img alt="">'; }
  function vidState(v){
    if (v.preview === 'coming') return esc(W.coming_small);
    if (v.preview === 'ready') return esc(W.vid_ready);
    if (SETTLED[v.preview]) return esc(W.vid_added);
    return '<span class="spin"></span> ' + esc(W.vid_getting_it);
  }
  function renderVideos(){
    var box = $('vlist'), was = box.querySelector('details');
    var busy = vids.filter(function(v){ return !SETTLED[v.preview]; }).length;
    var tot = vids.reduce(function(a, v){ return a + (v.length || 0); }, 0);
    box.innerHTML = !vids.length ? '' : '<details class="vdrop"' + (was && was.open ? ' open' : '') + '><summary><span class="vthumbs">' + vids.slice(0, 4).map(pic).join('') +
      '</span><span><b>' + esc(fill(vids.length === 1 ? W.vids_one : W.vids_n, {n: vids.length})) + '</b><small>' + esc(fill(W.vids_total, {total: mmss(tot)})) +
      (busy ? esc(fill(W.vids_getting, {n: busy})).replace(' · ', ' · <span class="spin"></span> ') : esc(W.vids_ready)) + '</small></span><span class="car">&#9662;</span></summary>' +
      vids.map(function(v){
        return '<div class="vid vcard">' + pic(v) + '<span><b>' + esc(v.name) + '</b><small>' + esc(mmss(v.length) + ' · ' + fill(W.mb, {n: v.mb})) + ' · ' + vidState(v) + '</small></span></div>';
      }).join('') + '</details>';
    $('step0').classList.toggle('done', footage === true && vids.length > 0);
    var total = vids.reduce(function(a, v){ return a + v.length; }, 0);
    var w = W.insight_words;
    if (total > 0) {
      var est = total <= 180 ? W.est_1 : total <= 600 ? W.est_2 : total <= 1500 ? W.est_3 : W.est_4;
      w = fill(W.insight_added, {total: mmss(total), est: est}) + (total > 900 ? W.insight_trim : '');
    }
    $('insightWords').textContent = w;
    edTabs();
  }

  // ---- the moments: changed only through the Assistant (hers: /moments/add, update, remove, restore) ----
  var undoT = null;
  function changeMoment(m, change){
    var body = {kit: R.kit, do: 'update', id: m.id};
    for (var k in change) body[k] = change[k];
    return R.post('/reel-moment', body).then(function(res){
      var r = res.j || {};
      if (!r.ok) { if (r.words) $('edSay').textContent = r.words; edRender(); return; }
      takeMoments(r.moments);
    }).catch(function(){ edRender(); });
  }
  function removeMoment(m){
    var at = -1; moments.forEach(function(x, i){ if (x.id === m.id) at = i; });
    R.post('/reel-moment', {kit: R.kit, do: 'remove', id: m.id}).then(function(res){
      var r = res.j || {};
      if (!r.ok) return;
      takeMoments(r.moments);
      var box = $('undoNote');
      box.innerHTML = '<div class="undo-note">' + esc(fill(W.removed, {label: m.label || W.that_moment})) + '<button type="button">' + esc(W.undo_b) + '</button></div>';
      box.querySelector('button').onclick = function(){
        R.post('/reel-moment', {kit: R.kit, do: 'restore', id: m.id, at: Math.max(0, at)}).then(function(r2){
          if (r2.j && r2.j.ok) takeMoments(r2.j.moments);
        }).catch(function(){});
        box.innerHTML = '';
      };
      clearTimeout(undoT); undoT = setTimeout(function(){ box.innerHTML = ''; }, D.undoNote);
    }).catch(function(){});
  }
  function merge(list){
    var keep = {}; moments.forEach(function(m){ keep[m.id] = m.keep; });
    return (list || []).map(function(m){ var c = {}; for (var k in m) c[k] = m[k]; if (keep[m.id] !== undefined) c.keep = keep[m.id]; return c; });
  }
  function takeMoments(list){ moments = merge(list); renderMoments(); summary(); R.save(); }
  function sig(list){ return JSON.stringify((list || []).map(function(m){ return [m.id, m.key, m.start, m.end, m.label, m.photo, m.named]; })); }
  function fromServer(list){        // the moments as the Assistant has them now (Claude's look, a name from the chat, or another window)
    if (!Array.isArray(list) || sig(list) === sig(moments)) return;
    moments = merge(list); renderMoments(); summary();
  }

  // ---- which clips each style uses: they pick them on the cards (hers) ----
  function defaultSel(st){
    var ok = moments.filter(function(m){ return m.keep !== false; }), pool = ok.length ? ok : moments;
    if (st === 'first') return pool.slice(0, 1).map(function(m){ return m.id; });
    if (st === 'bookends') return (pool.length > 1 ? [pool[0], pool[pool.length - 1]] : pool.slice(0, 1)).map(function(m){ return m.id; });
    if (st === 'reveal') return moments.filter(function(m){ return m.photo; }).slice(0, 2).map(function(m){ return m.id; });
    if (st === 'broll') return pool.slice(0, 4).map(function(m){ return m.id; });
    return pool.slice(0, 2).map(function(m){ return m.id; });        // Back and forth starts with 2 clips (Nicole)
  }
  function chosen(){
    var ids = Array.isArray(sel[style]) ? sel[style] : defaultSel(style);
    return moments.filter(function(m){ return ids.indexOf(m.id) >= 0; }).map(function(m){ return m.id; });     // in card order
  }
  R.chosen = chosen;
  function toggleClip(m){
    var rule = STYLE_PICK[style] || STYLE_PICK.first, ids = chosen();
    if (ids.indexOf(m.id) >= 0) ids = ids.filter(function(x){ return x !== m.id; });
    else if (rule.max === 1) ids = [m.id];
    else if (ids.length >= rule.max) { $('momentsSay').textContent = fill(W.style_full, {max: rule.max}); return; }
    else ids = ids.concat(m.id);
    sel[style] = ids;
    renderMoments(); R.save(); summary();
  }
  function renderMoments(){ edTabs(); }          // edTabs draws the clip counts and ends with edRender(), which draws the cards

  /* ---------- the footage editor (hers, Nov 16 and 17: one player, one timeline, the trim on it) ----------
     ED: the video in the player (v), the window shown (w0 to w1), the trim in hand (inT, outT; added once Add clip
     took it, as the clip's id), the clip picked by a click (edit), the drag under way, where a played clip stops. */
  var ED = {v: null, w0: 0, w1: 1, inT: null, outT: null, added: false, edit: null, drag: null, stopAt: null, zoom: false, srcKey: null};
  var MAXC = D.addMax, ZOOM_OVER = D.zoomOver, ZOOM_W = D.zoomWindow, TAP = D.tapPx;
  function edT(){ return $('edVid').currentTime || 0; }
  function vidLen(){ return ED.v ? (ED.v.length || 0) : 0; }
  function edPic(v){ return pic(v); }            // a frame a third of the way in, so you can tell what it is (the strip's)
  function clipsOf(v){ return moments.filter(function(m){ return v && m.key === v.key; }); }
  function edInfo(v){
    var n = clipsOf(v).length;
    return mmss(v.length) + (v.preview === 'ready' ? (n ? fill(n === 1 ? W.ed_clip : W.ed_clips, {n: n}) : '') : W.ed_getting_ready);
  }
  function edTabs(){
    var ready = vids.filter(function(v){ return v.preview === 'ready'; }), menu = $('edTabs');
    menu.innerHTML = vids.map(function(v){
      return '<button type="button" role="option" data-ek="' + esc(v.key) + '" class="' + (ED.v && ED.v.key === v.key ? 'on' : '') + '">' + edPic(v) +
        '<span><b>' + esc(v.name) + '</b><small>' + esc(edInfo(v)) + '</small></span></button>';
    }).join('');
    menu.querySelectorAll('[data-ek]').forEach(function(b){ b.onclick = function(){
      var v = vids.filter(function(x){ return x.key === b.dataset.ek; })[0];
      menu.hidden = true; $('vpBtn').setAttribute('aria-expanded', 'false');
      if (v) edLoad(v);
    }; });
    if (!ED.v || !vids.some(function(v){ return v.key === ED.v.key; })) {
      if (ready[0]) { edLoad(ready[0]); return; }
      ED.v = vids[0] || null; edWaiting();
    } else {
      var fresh = vids.filter(function(v){ return v.key === ED.v.key; })[0];
      if (fresh && fresh.preview === 'ready' && ED.v.preview !== 'ready') { edLoad(fresh); return; }
      ED.v = fresh;
    }
    var v = ED.v;
    $('vpBtn').innerHTML = v ? edPic(v) + '<span><b>' + esc(v.name) + '</b><small>' + esc(edInfo(v) + (vids.length > 1 ? fill(W.ed_videos, {n: vids.length}) : '')) + '</small></span><span class="car">' + (vids.length > 1 ? '&#9662;' : '') + '</span>'
      : '<span></span><span><b>' + esc(W.ed_none_b) + '</b><small>' + esc(W.ed_none_s) + '</small></span><span></span>';
    edRender();
  }
  $('vpBtn').onclick = function(){ if (vids.length < 2) return; var m = $('edTabs'); m.hidden = !m.hidden; $('vpBtn').setAttribute('aria-expanded', String(!m.hidden)); };
  document.addEventListener('click', function(e){ if (!e.target.closest('.vpick')) { $('edTabs').hidden = true; $('vpBtn').setAttribute('aria-expanded', 'false'); } });
  function edWaiting(){
    var w = $('edWait'), v = ED.v || vids[0]; w.hidden = false;
    w.textContent = !v ? W.ed_wait : (v.words && (v.preview === 'pc' || v.preview === 'hevc_pc' || v.preview === 'coming')) ? v.words
      : v.preview === 'lowspace' ? W.vid_lowspace : v.preview === 'failed' ? W.vid_failed : fill(W.vid_getting, {name: v.name});
  }
  function newestOwn(v){            // their newest clip of this video (ours: after a reload the trim is drawn from it, dashed)
    var own = clipsOf(v).filter(function(m){ return m.by === 'you'; });
    return own.length ? own[own.length - 1] : null;
  }
  function edLoad(v){
    ED.v = v; ED.inT = ED.outT = null; ED.added = false; ED.zoom = false; ED.w0 = 0; ED.w1 = Math.max(1, v.length || 1); ED.stopAt = null;
    var vid = $('edVid');
    if (v.preview !== 'ready') { edWaiting(); edTabs(); return; }
    $('edWait').hidden = true;
    if (ED.srcKey !== v.key) { ED.srcKey = v.key; vid.src = videoUrl(v.key); }       // by key, never by the address's spelling
    var last = newestOwn(v);
    if (last) { ED.inT = last.start; ED.outT = last.end; ED.added = last.id; }
    edTabs();
  }
  function edThumbs(){
    var box = $('edThumbs'), v = ED.v; if (!v || !v.strip || !v.strip.length) { box.innerHTML = ''; return; }
    var w = $('edTl').clientWidth || 800, n = Math.max(6, Math.floor(w / 46)), span = ED.w1 - ED.w0, h = '';
    for (var i = 0; i < n; i++) {
      var t = ED.w0 + (i + .5) * span / n, best = v.strip[0];
      v.strip.forEach(function(s){ if (Math.abs(s.t - t) < Math.abs(best.t - t)) best = s; });
      h += '<img src="' + esc(stripUrl(v.key, best.n)) + '" style="left:' + (i * 100 / n) + '%;width:' + (100 / n + .2) + '%" alt="">';
    }
    box.innerHTML = h;
  }
  function edX(t){ return (t - ED.w0) / (ED.w1 - ED.w0) * 100; }
  function edRender(){
    var v = ED.v; edThumbs();
    var marks = $('edMarks');
    if (!v) { marks.innerHTML = ''; $('edRuler').innerHTML = ''; $('edWin').textContent = ''; edCutUi(); edSelUi(); edClips(); return; }
    if (ED.added && ED.added !== true && !moments.some(function(m){ return m.id === ED.added; })) { ED.inT = ED.outT = null; ED.added = false; }   // the clip went
    var ids = chosen();
    marks.innerHTML = clipsOf(v).filter(function(m){ return m.end > ED.w0 && m.start < ED.w1; }).map(function(m){
      var k = ids.indexOf(m.id), edit = ED.edit === m.id;
      return '<div class="tm ' + (k >= 0 ? 'sel' : '') + ' ' + (edit ? 'edit' : '') + '" data-mid="' + esc(m.id) + '" style="left:' + edX(m.start) + '%;width:' + Math.max(.6, edX(m.end) - edX(m.start)) + '%">' +
        (k >= 0 ? '<i>' + (k + 1) + '</i>' : '') + (edit ? '<span class="hl"></span><span class="hr"></span>' : '') + '</div>';
    }).join('') + (ED.inT != null ? '<div class="tcut ' + (ED.outT != null ? 'set' : 'live') + '" id="edCut"><span class="cl"></span><span class="cr"></span><b></b></div>' : '');
    var span = ED.w1 - ED.w0, steps = [1, 2, 5, 10, 15, 30, 60, 120, 300], step = steps.filter(function(x){ return span / x <= 9; })[0] || 600, minor = step / 5, h = '';
    for (var t = Math.ceil(ED.w0 / minor) * minor; t <= ED.w1 + 1e-6; t = Math.round((t + minor) * 1000) / 1000) {   // (rounded: hers drifted to "0:01.0" on a short video)
      var major = Math.abs(t / step - Math.round(t / step)) < 1e-6, x = edX(t);
      if (x > 97) continue;
      h += major ? '<span style="left:' + x + '%">' + esc(mmss(t)) + '</span>' : '<i style="left:' + x + '%"></i>';
    }
    $('edRuler').innerHTML = h;
    $('edWin').textContent = ED.zoom ? fill(W.ed_zoomed, {video: v.name, a: mmss(ED.w0), b: mmss(ED.w1)}) : fill(W.ed_win, {video: v.name, length: mmss(v.length)});
    $('edZoom').textContent = ED.zoom ? W.ed_whole : W.ed_zoom;
    edHead(); edCutUi(); edSelUi(); edClips();
  }
  function edHead(){
    $('edPh').style.left = Math.max(0, Math.min(100, edX(edT()))) + '%';
    $('edTime').textContent = fmt2(edT()) + (ED.v ? ' / ' + mmss(ED.v.length) : '');
    edCutDraw();
  }
  // Nicole, Nov 17: "Start here should create an orange highlighted thing so that it drags across". Until End here, the
  // clip runs from the start to wherever the video is (playing or dragged), up to 15 seconds; then its ends can be dragged.
  function edCutEnd(){ return ED.outT != null ? ED.outT : Math.max(ED.inT, Math.min(edT(), ED.inT + MAXC, vidLen() || 1e9)); }
  function edCutDraw(){
    var el = $('edCut'); if (!el || ED.inT == null) return;
    if (ED.outT == null && edT() >= ED.inT + MAXC) { ED.outT = ED.inT + MAXC; $('edVid').pause(); edRender(); $('edSay').textContent = W.ed_fifteen; return; }
    var a = ED.inT, b = edCutEnd();
    el.style.left = edX(a) + '%'; el.style.width = Math.max(0, edX(b) - edX(a)) + '%';
    el.querySelector('b').textContent = ED.added ? W.ed_added : (b - a).toFixed(1) + ' s'; el.classList.toggle('added', !!ED.added);
    el.classList.toggle('tiny', edX(b) - edX(a) < 4); $('edAdd').disabled = !!ED.added || b - a < 1;
    if (ED.outT == null) $('edSay').innerHTML = b - a < 0.05 ? W.ed_started_html : fill(W.ed_sofar_html, {secs: (b - a).toFixed(1)});
  }
  function edCutUi(){
    var can = !!ED.v && ED.v.preview === 'ready';
    $('edIn').disabled = $('edOut').disabled = !can;
    $('edAdd').disabled = ED.inT == null || (ED.outT == null && edCutEnd() - ED.inT < 1); $('edClear').hidden = ED.inT == null;
    $('edIn').classList.toggle('rec', ED.inT != null && ED.outT == null);
    $('edAdd').textContent = ED.added ? W.ed_added : W.ed_add;
    if (ED.added && ED.inT != null) { $('edAdd').disabled = true; $('edSay').innerHTML = W.ed_added_html; edCutDraw(); return; }
    if (ED.inT != null && ED.outT == null) { edCutDraw(); return; }
    if (ED.inT != null) { $('edSay').innerHTML = fill(W.ed_set_html, {a: fmt2(ED.inT), b: fmt2(ED.outT), secs: (ED.outT - ED.inT).toFixed(1)}); edCutDraw(); return; }
    $('edSay').textContent = W.ed_find;
  }
  function edSelUi(){
    var box = $('edSel'), m = moments.filter(function(x){ return x.id === ED.edit; })[0];
    if (!m) { box.hidden = true; return; }
    box.hidden = false;
    box.innerHTML = '<b>' + esc(m.label || W.a_moment) + '</b><small>' + esc(fill(W.edsel, {a: fmt2(m.start), b: fmt2(m.end), secs: (m.end - m.start).toFixed(1)})) + '</small>' +
      '<div class="edrow"><button class="btn small" id="edPlayClip" type="button">' + esc(W.play_clip) + '</button>' +
      (D.trimPanel && R.openTrim ? '<button class="btn small" id="edTrimClip" type="button" title="' + esc(W.trim_btn_title) + '">' + esc(W.trim_btn) + '</button>' : '') + '</div>';
    $('edPlayClip').onclick = function(){ var vid = $('edVid'); vid.currentTime = m.start; ED.stopAt = m.end; vid.play().catch(function(){}); };
    if ($('edTrimClip')) $('edTrimClip').onclick = function(){ R.openTrim(m); };
  }
  function edClips(){
    var box = $('clist'), ids = chosen(), rule = STYLE_PICK[style] || STYLE_PICK.first;
    $('momentsSay').textContent = moments.length ? rule.say : '';           // e.g. Select the clip that opens your reel.
    if (!moments.length) box.innerHTML = '<p class="say sm" style="margin:.2rem 0">' + esc(W.clips_empty) + '</p>';
    else box.innerHTML = moments.map(function(m){
      var k = ids.indexOf(m.id), on = k >= 0, off = style === 'reveal' && !m.photo;
      var name = PICK_AT.test(m.label || '') ? W.not_named : (m.label || W.a_moment);
      return '<div class="ci ' + (on ? 'sel' : '') + ' ' + (ED.edit === m.id ? 'edit' : '') + '" data-mid="' + esc(m.id) + '"><img src="' + esc(stillUrl(m.id)) + '" alt="">' +
        '<span>' + (m.by === 'you' ? '<span class="yours">' + esc(W.your_pick) + '</span>' : '') + '<b>' + (on ? '<span class="num" style="display:inline-grid;margin-right:5px;background:var(--coral-2)">' + (k + 1) + '</span>' : '') +
        esc(name) + '</b><small>' + esc(m.name + ' · ' + fmt2(m.start) + '–' + fmt2(m.end) + ' · ' + (m.end - m.start).toFixed(1) + ' s') + '</small></span>' +
        '<button class="cin" type="button"' + (off ? ' disabled' : '') + ' title="' + esc(on ? W.out_title : W.use_title) + '">' + esc(off ? W.no_photo : on ? W.in_reel : W.use) + '</button>' +
        '<button class="cx" type="button" title="' + esc(W.remove_clip) + '" aria-label="' + esc(W.remove_clip) + '">&times;</button></div>';
    }).join('');
    box.querySelectorAll('.ci').forEach(function(el){
      var m = moments.filter(function(x){ return x.id === el.dataset.mid; })[0];
      var img = el.querySelector('img'); img.onerror = function(){ img.removeAttribute('src'); };     // a PC: no still yet
      el.onclick = function(){ edGo(m); };
      el.querySelector('.cin').onclick = function(e){ e.stopPropagation(); toggleClip(m); };
      el.querySelector('.cx').onclick = function(e){
        e.stopPropagation();
        if (ED.edit === m.id) { ED.edit = null; ED.inT = ED.outT = null; ED.added = false; }      // ours: the trim in hand goes with it
        if (ED.added === m.id) { ED.inT = ED.outT = null; ED.added = false; }
        removeMoment(m);
      };
    });
    // their own clips: the Assistant gives them a short name from the chat (Nov 17)
    var unnamed = moments.some(function(m){ return m.by === 'you' && (!m.label || PICK_AT.test(m.label)); });
    $('descBox').hidden = !unnamed; $('descWords').textContent = fill(W.desc_line, {short: short});
  }
  function edGo(m){
    var v = vids.filter(function(x){ return x.key === m.key; })[0]; if (!v) return;
    if (!ED.v || ED.v.key !== v.key) edLoad(v);
    ED.edit = m.id;
    if (vidLen() > ZOOM_OVER) { ED.zoom = true; ED.w0 = Math.max(0, m.start - ZOOM_W / 2); ED.w1 = Math.min(vidLen(), m.end + ZOOM_W / 2); }
    try { $('edVid').currentTime = m.start; } catch (e) {}
    edRender();
  }
  function edAt(ev){ var r = $('edTl').getBoundingClientRect(); return ED.w0 + Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)) * (ED.w1 - ED.w0); }
  var tl = $('edTl');
  tl.addEventListener('pointerdown', function(ev){
    if (!ED.v || ED.v.preview !== 'ready') return;
    ev.preventDefault(); try { tl.setPointerCapture(ev.pointerId); } catch (e) {}
    var vid = $('edVid'), ce = ev.target.closest('#edCut .cl, #edCut .cr');
    if (ce) { vid.pause(); if (ED.outT == null) ED.outT = edCutEnd(); ED.drag = {mode: ce.classList.contains('cl') ? 'ia' : 'ib'}; return; }
    if (ev.target.closest('#edCut') && ED.outT != null) { vid.pause(); var t0 = edAt(ev); ED.drag = {mode: 'imove', off: t0 - ED.inT, len: ED.outT - ED.inT, a0: ED.inT}; return; }   // slide the whole trim
    var h = ev.target.closest('.hl,.hr'), tm = ev.target.closest('.tm');
    if (h && tm) { var mh = moments.filter(function(x){ return x.id === tm.dataset.mid; })[0]; ED.drag = {mode: h.classList.contains('hl') ? 'a' : 'b', m: mh, a: mh.start, b: mh.end}; return; }
    if (tm) {
      var m = moments.filter(function(x){ return x.id === tm.dataset.mid; })[0];
      if (ED.edit === m.id) { var t1 = edAt(ev); ED.drag = {mode: 'move', m: m, a: m.start, b: m.end, off: t1 - m.start}; return; }   // drag the middle: slide it
      ED.drag = {mode: 'scrub', tap: m, sx: ev.clientX}; vid.pause(); vid.currentTime = edAt(ev); edHead(); return;   // a click picks it; a drag just scrubs (Nicole, Nov 17)
    }
    ED.drag = {mode: 'scrub'}; vid.pause(); vid.currentTime = edAt(ev); edHead();
  });
  tl.addEventListener('pointermove', function(ev){
    var d = ED.drag; if (!d) return;
    var t = edAt(ev), vid = $('edVid'), len = vidLen();
    if (d.mode === 'scrub') { if (d.tap && Math.abs(ev.clientX - d.sx) > TAP) d.tap = null; vid.currentTime = t; edHead(); return; }
    if (d.mode === 'imove') {
      var a = tenth(Math.max(0, Math.min(len - d.len, t - d.off)));
      if (Math.abs(a - d.a0) >= 0.1) ED.added = false;              // moved after Add clip: it's a new clip now (the one added is never changed)
      ED.inT = a; ED.outT = tenth(a + d.len); vid.currentTime = ED.inT; edHead(); edCutUi(); return;
    }
    if (d.mode === 'ia' || d.mode === 'ib') {
      ED.added = false;
      if (d.mode === 'ia') ED.inT = tenth(Math.max(0, Math.max(ED.outT - MAXC, Math.min(t, ED.outT - 1))));
      else ED.outT = tenth(Math.min(len, Math.min(ED.inT + MAXC, Math.max(t, ED.inT + 1))));
      vid.currentTime = d.mode === 'ia' ? ED.inT : ED.outT; edHead(); edCutUi(); return;
    }
    if (d.mode === 'move') { var l = d.m.end - d.m.start; d.a = Math.max(0, Math.min(len - l, t - d.off)); d.b = d.a + l; }
    else if (d.mode === 'a') d.a = Math.max(0, Math.min(t, d.b - 1)); else d.b = Math.min(len, Math.max(t, d.a + 1));
    if (d.b - d.a > MAXC) { if (d.mode === 'a') d.a = d.b - MAXC; else d.b = d.a + MAXC; }
    var el = $('edMarks').querySelector('.tm[data-mid="' + CSS.escape(d.m.id) + '"]');
    if (el) { el.style.left = edX(d.a) + '%'; el.style.width = (edX(d.b) - edX(d.a)) + '%'; }
    vid.currentTime = d.mode === 'b' ? d.b : d.a; edHead();
    $('edSay').textContent = fill(W.ed_drag, {a: fmt2(d.a), b: fmt2(d.b), secs: (d.b - d.a).toFixed(1)});
  });
  function edUp(){
    var d = ED.drag; ED.drag = null;
    if (!d) return;
    if (d.mode === 'scrub' && d.tap) { ED.edit = d.tap.id; ED.inT = ED.outT = null; ED.added = false; $('edVid').currentTime = d.tap.start; edRender(); return; }
    if (d.mode === 'scrub' || d.mode === 'ia' || d.mode === 'ib' || d.mode === 'imove') return;
    if (d.mode === 'move' && Math.abs(d.a - d.m.start) < 0.05) { edRender(); return; }      // a click on the picked clip, not a slide
    changeMoment(d.m, {start: tenth(d.a), end: tenth(d.b)});
  }
  tl.addEventListener('pointerup', edUp); tl.addEventListener('pointercancel', edUp);
  var vidEl = $('edVid');
  vidEl.addEventListener('timeupdate', function(){ if (ED.stopAt != null && edT() >= ED.stopAt) { vidEl.pause(); ED.stopAt = null; } edHead(); });
  vidEl.addEventListener('play', function(){ $('edPlay').innerHTML = '&#10074;&#10074;'; $('edBig').hidden = true; (function tick(){ if (vidEl.paused) return; edHead(); requestAnimationFrame(tick); })(); });
  vidEl.addEventListener('pause', function(){ $('edPlay').innerHTML = '&#9654;'; $('edBig').hidden = false; });
  function edToggle(){ if (!ED.v || ED.v.preview !== 'ready') return; ED.stopAt = null; if (vidEl.paused) vidEl.play().catch(function(){}); else vidEl.pause(); }
  $('edPlay').onclick = edToggle; $('edBig').onclick = function(e){ e.stopPropagation(); edToggle(); };
  $('edPlayer').addEventListener('click', edToggle);
  $('edBack').onclick = function(){ vidEl.currentTime = Math.max(0, edT() - 1); edHead(); };
  $('edFwd').onclick = function(){ vidEl.currentTime = Math.min(vidLen(), edT() + 1); edHead(); };
  $('edIn').onclick = function(){
    if (!ED.v || ED.v.preview !== 'ready') return;
    ED.inT = tenth(edT()); ED.outT = null; ED.edit = null; ED.stopAt = null; ED.added = false;
    if (vidLen() > ZOOM_OVER) { ED.zoom = true; ED.w0 = Math.max(0, ED.inT - 5); ED.w1 = Math.min(vidLen(), ED.w0 + ZOOM_W); }   // close enough to see it grow
    edRender(); vidEl.play().catch(function(){});
  };
  $('edOut').onclick = function(){
    if (!ED.v || ED.v.preview !== 'ready') return;
    var t = tenth(edT());
    if (ED.inT == null) ED.inT = Math.max(0, t - 4);
    if (t <= ED.inT + 0.9) { $('edSay').textContent = W.ed_end_after; return; }
    ED.outT = Math.min(t, ED.inT + MAXC); ED.added = false; ED.edit = null; vidEl.pause(); edRender();
  };
  $('edClear').onclick = function(){ ED.inT = ED.outT = null; ED.added = false; edRender(); };
  $('edZoom').onclick = function(){
    if (!ED.v) return;
    if (ED.zoom) { ED.zoom = false; ED.w0 = 0; ED.w1 = vidLen(); }
    else { ED.zoom = true; var c = edT(), half = Math.min(ZOOM_W / 2, vidLen() / 2); ED.w0 = Math.max(0, c - half); ED.w1 = Math.min(vidLen(), ED.w0 + 2 * half); }
    edRender();
  };
  $('edAdd').onclick = function(){
    if (!ED.v || ED.inT == null || ED.added) return;
    var end = edCutEnd(), a = ED.inT; vidEl.pause();
    if (end - a < 1) { $('edSay').textContent = W.ed_second; return; }
    $('edAdd').disabled = true; $('edSay').textContent = W.ed_adding;
    var before = {}; moments.forEach(function(m){ before[m.id] = true; });     // before the ask: the page's 4 s look may bring the new clip in first
    R.post('/reel-moment', {kit: R.kit, do: 'add', video: ED.v.key, start: a, seconds: tenth(end - a)}).then(function(res){
      var r = res.j || {};
      if (!r.ok) { $('edSay').textContent = r.words || W.didnt_work; $('edAdd').disabled = false; return; }
      moments = merge(r.moments);
      var added = moments.filter(function(m){ return !before[m.id]; })[0];
      if (added && style !== 'reveal') {
        var ids = chosen(), max = (STYLE_PICK[style] || STYLE_PICK.first).max;
        sel[style] = max === 1 ? [added.id] : [added.id].concat(ids.filter(function(x){ return x !== added.id; })).slice(0, max);
      }
      ED.inT = a; ED.outT = end; ED.added = added ? added.id : true; ED.edit = null;     // the trim stays; moving it makes the next clip (Nicole, Nov 17)
      renderMoments(); summary(); R.save();
    }).catch(function(){ $('edSay').textContent = W.no_server_short; $('edAdd').disabled = false; });
  };
  window.addEventListener('resize', edThumbs);
  // what the Trim panel needs from here, when it is on the page (TRIM_PANEL): a clip's video as the page knows it,
  // the addresses, and the one way a clip is changed
  R.clips = {video: function(key){ return vids.filter(function(x){ return x.key === key; })[0] || null; },
    videoUrl: videoUrl, stripUrl: stripUrl, mmss: mmss, stop: function(){ vidEl.pause(); },
    change: function(m, change){ changeMoment(m, change); },
    fresh: function(fn){ waiting.push(fn); loadFootage(); }};
  // for the tests: the editor's state as numbers (no words, no path)
  R.editor = function(){ return {key: ED.v ? ED.v.key : null, w0: ED.w0, w1: ED.w1, inT: ED.inT, outT: ED.outT, added: ED.added, edit: ED.edit, zoom: ED.zoom, drag: ED.drag ? ED.drag.mode : null, t: edT()}; };

  // ---- looking at the Footage folder (hers: loadFootage, every 4 s) ----
  var waiting = [];
  function loadFootage(){
    if (footage !== true) return;
    fetch('/reel-footage?' + R.q, {cache: 'no-store'}).then(function(r){ return r.json(); }).then(function(f){
      if (!f || !f.ok) { waiting = []; return; }
      vids = f.videos || [];
      var s = JSON.stringify(vids.map(function(v){ return [v.key, v.name, v.preview, (v.strip || []).length, v.words]; }));
      if (s !== vsig) { vsig = s; renderVideos(); }
      R.setClaudeBts(f.claude_bts || []);
      fromServer(f.moments);
      var w = waiting; waiting = []; w.forEach(function(fn){ fn(); });
    }).catch(function(){ waiting = []; });
  }
  setInterval(function(){ if (!document.hidden && R.state()) loadFootage(); }, D.footEvery);

  // ---- step 4: the style (hers: renderStyles) ----
  function renderStyles(){
    document.querySelectorAll('#styles .opt').forEach(function(b){ b.classList.toggle('on', b.dataset.style === style); });
    $('stepStyle').classList.toggle('done', !!style);
    renderMoments();
  }
  document.querySelectorAll('#styles .opt').forEach(function(b){ b.onclick = function(){ style = b.dataset.style; renderStyles(); R.save(); summary(); }; });
  R.style = function(){ return style; };
  R.setStyle = function(st){ if (D.styles.indexOf(st) < 0) return; style = st; renderStyles(); R.save(); summary(); };   // the watch step's chips (v27)

  // ---- what the bar and Make my reel need from steps 1 and 4 ----
  R.sumExtra = function(){
    if (!footage) return '';
    var used = chosen().length;
    return esc(fill(W.sum_clip, {n: used, s: used === 1 ? '' : 's'})) + ' · ' + esc(STYLE_WORDS[style] || '');
  };
  R.beforeMake = function(){
    if (footage && !chosen().length) return moments.length ? {h3: W.clips_need_h3, html: W.clips_need_html} : {h3: W.not_looked_h3, html: W.not_looked_html};
    return null;
  };
  R.makeExtra = function(){ return {footage: footage === true, style: style, clips: chosen()}; };

  R.part({
    fields: function(){ return {footage: footage, style: style, sel: sel, ask: ask, feel: feel}; },
    adopt: function(st, first){
      short = st.short;
      var sv = st.saved || {};
      // v27: footage on or off, and B-roll's one style, are the kind's, whatever an older record says
      footage = R.kind === 'photos' ? false : true;
      style = R.kind === 'broll' ? 'broll' : D.styles.indexOf(sv.style) >= 0 ? sv.style : 'first';
      sel = (sv.sel && typeof sv.sel === 'object' && !Array.isArray(sv.sel)) ? sv.sel : {};
      ask = typeof sv.ask === 'string' ? sv.ask : ''; feel = typeof sv.feel === 'string' ? sv.feel : '';
      if (first || document.activeElement !== $('askIn')) $('askIn').value = ask;
      if (first || document.activeElement !== $('feelOwn')) feelOwnOpen = false;
      moments = merge(st.moments);
      showFeel(); pasteLine();
      setFootage(footage);
      if (footage) loadFootage();
    },
    follow: function(st){ fromServer(st.moments); }
  });
})();
"""


# Trim (her v25, section 4): where a clip starts and where it ends. Her panel and what it does, wired on load to
# the markup trim_panel() wrote above the scripts. Nothing is saved until Done; Cancel, the x, a click outside
# and Escape close it and change nothing. Done is the card's own change (POST /reel-moment, do: update, with
# the start and the end), so the Assistant checks it like any other.
TRIM_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, fill = R.fill, D = R.data, C = R.clips;
  var MIN = D.trimMin, MAX = D.trimMax, GRID = 1 / D.trimGrid;
  var TR = {m: null, v: null, a: 0, b: 0, w0: 0, w1: 0, len: 0, drag: null, grab: 0};
  // hers: 0:31.6, always with the tenth
  function fmt2(t){ t = Math.max(0, t); var m = Math.floor(t / 60), s = t - m * 60; return m + ':' + (s < 10 ? '0' : '') + s.toFixed(1); }
  function cents(t){ return Math.round(t * 100) / 100; }
  function open(m, again){
    C.stop(); document.querySelectorAll('.viewer video').forEach(function(v){ v.pause(); });
    var src = C.video(m.key);
    // pressed before the page had its list of videos: get the list, then open (hers does nothing here)
    if (!src) { if (again !== true) C.fresh(function(){ open(m, true); }); return; }
    var len = src.length || m.end + 10;
    TR.m = m; TR.a = m.start; TR.b = m.end; TR.len = len; TR.drag = null;
    var span = Math.max(D.trimSpanMin, (m.end - m.start) + D.trimWindow);          // about 8 seconds either side of the clip
    TR.w0 = Math.max(0, (m.start + m.end) / 2 - span / 2); TR.w1 = Math.min(len, TR.w0 + span); TR.w0 = Math.max(0, TR.w1 - span);
    $('trimName').textContent = m.label || W.trim_title;
    var film = $('trimFilm'), wide = TR.w1 - TR.w0;
    film.innerHTML = '';
    (src.strip || []).filter(function(x){ return x.t >= TR.w0 - D.stripEvery && x.t <= TR.w1; }).forEach(function(x){
      var img = document.createElement('img'); img.alt = '';
      img.src = C.stripUrl(src.key, x.n);
      img.style.left = ((x.t - TR.w0) / wide * 100) + '%'; img.style.width = (D.stripEvery / wide * 100) + '%';
      film.appendChild(img);
    });
    var v = $('trimVid'), no = $('trimNoVid');
    if (src.preview === 'ready') { v.src = C.videoUrl(src.key); v.hidden = false; no.hidden = true; }
    else {
      v.removeAttribute('src'); v.hidden = true; no.hidden = false;
      no.textContent = (src.preview === 'failed' || src.preview === 'lowspace' || src.preview === 'pc' || src.preview === 'hevc_pc') ? W.trim_stuck : W.trim_novid;
    }
    TR.v = v;
    v.onloadedmetadata = function(){ v.currentTime = TR.a; v.play().catch(function(){}); };
    v.ontimeupdate = function(){ if (!TR.drag && (v.currentTime >= TR.b || v.currentTime < TR.a - 0.3)) v.currentTime = TR.a; head(); };
    $('trim').hidden = false; draw();
  }
  function close(){
    $('trim').hidden = true;
    if (TR.v) { TR.v.pause(); TR.v.onloadedmetadata = TR.v.ontimeupdate = null; }
    TR.m = null; TR.drag = null;
  }
  function draw(){
    var wide = TR.w1 - TR.w0, L = (TR.a - TR.w0) / wide * 100, Rt = (TR.b - TR.w0) / wide * 100;
    $('trimSel').style.left = L + '%'; $('trimSel').style.width = (Rt - L) + '%';
    $('trimDimL').style.width = L + '%'; $('trimDimR').style.left = Rt + '%';
    $('trimSay').innerHTML = fill(W.trim_say_html, {a: fmt2(TR.a), b: fmt2(TR.b), len: (TR.b - TR.a).toFixed(1)});     // numbers only
    var ticks = $('trimTicks'); ticks.innerHTML = '';
    [0, 0.25, 0.5, 0.75, 1].forEach(function(f){
      var sp = document.createElement('span'); sp.style.left = (f * 100) + '%';
      sp.textContent = C.mmss(Math.round((TR.w0 + f * wide) * 2) / 2); ticks.appendChild(sp);
    });
  }
  function head(){ if (!TR.v || !TR.m) return; $('trimHead').style.left = ((TR.v.currentTime - TR.w0) / (TR.w1 - TR.w0) * 100) + '%'; }
  // hers: an end moves in twentieths of a second, the clip stays 1 to 15 seconds and inside the video; the middle
  // slides the whole clip and keeps its length
  function set(a, b, which){
    a = Math.round(a * GRID) / GRID; b = Math.round(b * GRID) / GRID;
    if (which === 'a') { a = Math.max(0, Math.min(a, b - MIN, TR.len - MIN)); a = Math.max(a, b - MAX); }
    else if (which === 'b') { b = Math.min(TR.len, Math.max(b, a + MIN)); b = Math.min(b, a + MAX); }
    else { var d = b - a; a = Math.max(0, Math.min(a, TR.len - d)); b = a + d; }
    TR.a = a; TR.b = b; draw();
    if (TR.v && TR.v.readyState) TR.v.currentTime = which === 'b' ? Math.max(a, b - 0.05) : a;
  }
  function at(ev){ var r = $('trimBar').getBoundingClientRect(); return TR.w0 + Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)) * (TR.w1 - TR.w0); }
  var bar = $('trimBar');
  bar.addEventListener('pointerdown', function(ev){
    if (!TR.m) return;
    var t = at(ev), h = ev.target.closest ? ev.target.closest('[data-h]') : null;
    TR.drag = h ? h.dataset.h : (t > TR.a && t < TR.b ? 'move' : (Math.abs(t - TR.a) < Math.abs(t - TR.b) ? 'a' : 'b'));
    TR.grab = t - TR.a;
    if (!h && TR.drag !== 'move') set(TR.drag === 'a' ? t : TR.a, TR.drag === 'b' ? t : TR.b, TR.drag);
    if (TR.v) TR.v.pause();
    try { bar.setPointerCapture(ev.pointerId); } catch (e) {}
    ev.preventDefault();
  });
  bar.addEventListener('pointermove', function(ev){
    if (!TR.drag) return;
    var t = at(ev);
    if (TR.drag === 'a') set(t, TR.b, 'a');
    else if (TR.drag === 'b') set(TR.a, t, 'b');
    else set(t - TR.grab, t - TR.grab + (TR.b - TR.a), 'move');
  });
  function up(){ if (!TR.drag) return; TR.drag = null; if (TR.v && TR.v.readyState) { TR.v.currentTime = TR.a; TR.v.play().catch(function(){}); } }
  bar.addEventListener('pointerup', up); bar.addEventListener('pointercancel', up);
  document.querySelectorAll('#trim [data-n]').forEach(function(b){ b.onclick = function(){
    if (!TR.m) return;
    var p = b.dataset.n.split(':'), d = +p[1];
    if (p[0] === 'a') set(TR.a + d, TR.b, 'a'); else set(TR.a, TR.b + d, 'b');
    if (TR.v && TR.v.readyState && TR.v.paused) TR.v.play().catch(function(){});
  }; });
  $('trimPlay').onclick = function(){ if (!TR.v || TR.v.hidden) return; TR.v.currentTime = TR.a; TR.v.play().catch(function(){}); };
  $('trimCancel').onclick = close; $('trimX').onclick = close;
  $('trim').addEventListener('click', function(ev){ if (ev.target === $('trim')) close(); });
  document.addEventListener('keydown', function(ev){ if (ev.key === 'Escape' && !$('trim').hidden) close(); });
  $('trimDone').onclick = function(){
    var m = TR.m; if (!m) return;
    var a = cents(TR.a), b = cents(TR.b); close();
    C.change(m, {start: a, end: b});
  };
  R.openTrim = open;
  R.trim = function(){ return TR.m ? {id: TR.m.id, a: TR.a, b: TR.b, w0: TR.w0, w1: TR.w1, len: TR.len} : null; };
})();
"""


# The bar at the bottom and Make my reel: hers, with the reel made by a job of its own that the page asks after.
# A later step adds to it through R.sumExtra() (words after the photo count, hers: " + 1 clip · Moment first"),
# R.beforeMake() (a reason not to make yet: {h3, html}) and R.makeExtra() (more for the request).
# Her v27, "Would you like to direct this edit?": the note is saved as "direct" (only the changed field, after
# SAVE_AFTER_MS, as every box; hers saved the whole record on every keystroke) and the line to copy follows it and
# the reel's name. Not on a B-roll page: there the section is hidden and nothing of it is sent.
DIRECT_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$;
  if (!$('stepDirect') || R.kindHides('stepDirect')) return;
  var direct = '', short = '';
  function line(){
    var nm = R.reels ? R.reels.name() : '';
    $('directPaste').textContent = R.fill(W.direct_for, {short: short}) + (nm ? R.fill(W.direct_reel, {name: nm}) : '') + (direct ? W.direct_note : '');
  }
  R.directLine = line;
  $('directIn').oninput = function(){ direct = $('directIn').value.trim(); line(); R.save(); };
  $('copyDirect').onclick = function(){
    var t = $('directPaste').textContent, ok = false;
    try {
      var r = document.createRange(); r.selectNodeContents($('directPaste'));
      var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
      ok = document.execCommand('copy');
      sel.removeAllRanges();
    } catch (e) { ok = false; }
    if (!ok && navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).catch(function(){});
    $('copyDirect').textContent = W.copied; setTimeout(function(){ $('copyDirect').textContent = W.copy; }, 1600);
  };
  R.part({
    fields: function(){ return {direct: direct}; },
    adopt: function(st, first){
      short = st.short;
      var sv = st.saved || {};
      direct = typeof sv.direct === 'string' ? sv.direct.trim() : '';
      if (first || document.activeElement !== $('directIn')) $('directIn').value = direct;
      line();
    }
  });
})();
"""

# Her v27, "Watch your reel before you make it" (her PV state machine, ours underneath): the page asks for the
# same plan Make my reel builds from (POST /reel-preview: a dry run of reel.py, nothing goes to CapCut) and plays
# it here. The song is the clock (GET /reel-song, by id), each photo shows for exactly its beats (the picker's own
# copies, by number), and a clip plays from its own start (its small copy or the original, by key: hers compared
# the address's spelling). Every change on the page refreshes it after 700 ms; a newer ask drops an older answer.
# Another part of this song, Try another mix, Undo and Redo (40 steps of the mix, the part of the song, the song,
# the pace and the style). Make this one in CapCut sends the mix and the start that were watched. B-roll: the words
# on screen, dragged into place on the phone, the dot in their corner for the size, saved as "onscreen" without
# rebuilding the preview (the words don't change the cut).
WATCH_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc, fill = R.fill, D = R.data, KIND = R.kind, BROLL = KIND === 'broll';
  if (!$('watch')) return;
  var NAMES = {}; D.vibes.forEach(function(v){ NAMES[v] = W['vibe_' + v + '_b']; });
  var PV = {plan: null, variation: 0, songStart: null, seen: false, t: null, playing: false, raf: 0, cur: -1, clock: null, ask: 0, lastLen: null, lastVibe: null};
  var byN = {}, _save = R.save;
  function photoSrc(n){ var p = byN[n]; return p ? R.photoUrl(p, 'l') : ''; }
  function videoUrl(key){ return '/reel-video?' + R.q + '&key=' + encodeURIComponent(key); }
  function songUrl(id){ return '/reel-song?' + R.q + '&id=' + encodeURIComponent(id); }
  function songOptions(){
    var sel = $('pvSong'), songs = R.songs ? R.songs() : [], song = R.song();
    sel.innerHTML = songs.map(function(s){ return '<option value="' + esc(s.id) + '">' + esc(s.name) + (s.kind === 'video' ? esc(W.song_rec_tag) : '') + '</option>'; }).join('') +
      '<option value="">' + esc(W.song_none) + '</option>';
    sel.value = song || '';
  }
  function chips(){
    var vibe = R.vibe(), style = R.style ? R.style() : '';
    document.querySelectorAll('[data-pv-vibe]').forEach(function(b){ b.classList.toggle('on', b.dataset.pvVibe === vibe); });
    document.querySelectorAll('[data-pv-style]').forEach(function(b){ b.classList.toggle('on', b.dataset.pvStyle === style); });
  }
  function empty(text){ $('pvEmpty').hidden = false; $('pvEmpty').textContent = text; $('pvVid').hidden = true; $('pvImg').hidden = true; }
  function pvSoon(){ clearTimeout(PV.t); PV.t = setTimeout(pvLoad, D.previewAfter); }
  R.save = function(){ _save.apply(this, arguments); pvSoon(); };      // every change on the page refreshes the preview a moment later (hers)
  function pvLoad(){
    clearTimeout(PV.t); PV.t = null;
    chips(); songOptions();
    var st = R.state(); if (!st) return;
    var picks = R.order ? R.order() : [], clips = R.chosen ? R.chosen() : [];
    if (BROLL ? !clips.length : !picks.length) { pvStop(); PV.plan = null; empty(BROLL ? W.os_clips_first : W.pv_empty); $('pvWords').textContent = ''; return; }
    var ask = ++PV.ask;
    $('pvWords').textContent = W.pv_working;
    var body = {kit: R.kit, stamp: st.stamp, picks: picks, song: R.song(), vibe: R.vibe(), variation: PV.variation};
    var extra = R.makeExtra ? R.makeExtra() : {};
    for (var k in extra) body[k] = extra[k];
    if (PV.songStart != null) body.song_start = PV.songStart;
    R.post('/reel-preview', R.withReel(body)).then(function(res){
      if (ask !== PV.ask) return;                        // a newer change already asked again
      var j = res.j || {};
      if (!j.ok) { pvStop(); PV.plan = null; empty(j.problem || j.words || W.pv_cant); $('pvWords').textContent = ''; return; }
      var wasPlaying = PV.playing; pvStop();
      PV.plan = j; PV.seen = true; $('pvEmpty').hidden = true;
      words(j);
      j.pieces.forEach(function(p){ if (p.kind === 'photo' && byN[p.n]) { var im = new Image(); im.src = photoSrc(p.n); } });
      var first = j.pieces.filter(function(p){ return p.kind === 'clip' && p.key; })[0];
      if (first) setClip(first.key);
      pvShow(0, true);
      if (wasPlaying) pvPlay();
    }).catch(function(){ if (ask === PV.ask) $('pvWords').textContent = W.pv_couldnt; });
  }
  // say plainly what this pace did, and what it was before, so a change is easy to see (hers)
  function words(j){
    var vibe = R.vibe(), len = (j.length || 0).toFixed(1), out = $('pvWords');
    if (BROLL) {
      var nc = j.pieces.length, t = fill(W.pv_broll_words, {secs: len, n: nc, s: nc === 1 ? '' : 's'}), i = t.indexOf(', ');
      out.innerHTML = '<b>' + esc(t.slice(0, i)) + '</b>' + esc(t.slice(i));
    } else {
      var ph = j.pieces.filter(function(p){ return p.kind === 'photo'; });
      var avg = ph.length ? ph.reduce(function(t2, p){ return t2 + p.dur; }, 0) / ph.length : 0;
      var was = PV.lastLen != null && PV.lastVibe !== vibe ? fill(W.pv_was, {pace: NAMES[PV.lastVibe] || PV.lastVibe, secs: PV.lastLen.toFixed(1)}) : '';
      var order = R.order(), quick = order.filter(function(r){ return r.h === '-'; }).length, long = order.filter(function(r){ return r.h === '+'; }).length;
      var marks = (quick + long) >= Math.max(3, order.length / 3)
        ? ' ' + (quick ? fill(W.pv_marks_quick, {k: quick, n: order.length}) : '') + (quick && long ? W.pv_marks_and : '') + (long ? fill(W.pv_marks_long, {j: long}) : '') + W.pv_marks_tail : '';
      out.innerHTML = '<b>' + esc(fill(W.pv_words_b, {pace: NAMES[vibe] || vibe, secs: len, was: was})) + '</b>' + esc(fill(W.pv_words_tail, {avg: avg.toFixed(1)}) + marks);
    }
    PV.lastLen = j.length; PV.lastVibe = vibe;
  }
  function setClip(key){ var v = $('pvVid'); if (v.dataset.key !== key) { v.dataset.key = key; v.src = videoUrl(key); } }
  function pvPiece(t){ var ps = PV.plan.pieces; for (var i = ps.length - 1; i >= 0; i--) if (t >= ps[i].start - 0.001) return i; return 0; }
  function pvShow(i, force){
    var p = PV.plan.pieces[i]; if (!p) return;
    var img = $('pvImg'), v = $('pvVid');
    if (i === PV.cur && !force) return;
    PV.cur = i;
    if (p.kind === 'clip' && p.key) {
      setClip(p.key);
      v.muted = !!R.song(); v.classList.toggle('fit', p.fill === false);
      try { v.currentTime = p.src || 0; } catch (e) {}
      if (PV.playing) v.play().catch(function(){});
      v.hidden = false; img.hidden = true;
    } else {
      v.pause(); v.hidden = true;
      img.src = photoSrc(p.n); img.classList.toggle('fit', p.fill === false); img.hidden = false;
    }
  }
  function pvTick(){
    if (!PV.playing || !PV.plan) return;
    var t = PV.clock(), L = PV.plan.length || 0;
    if (t >= L) { pvStop(); pvShow(0, true); $('pvProg').style.width = '0'; return; }
    pvShow(pvPiece(t));
    $('pvProg').style.width = Math.min(100, t / L * 100) + '%';
    PV.raf = requestAnimationFrame(pvTick);
  }
  function pvPlay(){
    if (!PV.plan) return;
    var a = $('pvAudio'), pl = PV.plan, song = R.song();
    PV.playing = true; PV.cur = -1; $('pvPlay').classList.add('playing'); $('pvPlay').innerHTML = '&#10074;&#10074;';
    $('pvKnob').hidden = true;
    var go = function(){
      a.currentTime = pl.song.from; a.volume = 1;
      a.play().catch(function(){});
      PV.clock = function(){ return a.currentTime - pl.song.from; };
      PV.raf = requestAnimationFrame(pvTick);
    };
    if (song && pl.song && pl.song.id) {
      var u = songUrl(pl.song.id);
      if (a.getAttribute('src') !== u) {
        a.setAttribute('src', u);
        var done = false, once = function(){ if (!done) { done = true; go(); } };
        a.addEventListener('loadedmetadata', once, {once: true}); setTimeout(once, 4000);
      } else go();
    } else {
      var t0 = performance.now(); PV.clock = function(){ return (performance.now() - t0) / 1000; };
      PV.raf = requestAnimationFrame(pvTick);
    }
  }
  function pvStop(){
    PV.playing = false; cancelAnimationFrame(PV.raf);
    try { $('pvAudio').pause(); } catch (e) {}
    $('pvVid').pause();
    $('pvPlay').classList.remove('playing'); $('pvPlay').innerHTML = '&#9654;';
    try { osDraw(); } catch (e) {}
  }
  $('pvPlay').onclick = function(){ if (PV.playing) pvStop(); else pvPlay(); };
  // Undo and Redo for what you try while watching: the mix, the part of the song, the song, the pace, the style (hers)
  var PVH = {back: [], fwd: []};
  function now(){ return {variation: PV.variation, songStart: PV.songStart, vibe: R.vibe(), style: R.style ? R.style() : null, song: R.song()}; }
  function record(){ PVH.back.push(now()); if (PVH.back.length > D.pvUndo) PVH.back.shift(); PVH.fwd = []; histUi(); }
  function histUi(){ $('pvUndo').disabled = !PVH.back.length; $('pvRedo').disabled = !PVH.fwd.length; }
  function mixSay(){ $('pvMixSay').textContent = PV.variation ? fill(W.pv_mix_n, {n: PV.variation + 1}) : ''; }
  function apply(st){
    PV.variation = st.variation; PV.songStart = st.songStart; mixSay();
    if (st.vibe !== R.vibe() && R.setVibe) R.setVibe(st.vibe);
    if (R.style && st.style && st.style !== R.style() && R.setStyle) R.setStyle(st.style);
    if (st.song !== R.song() && R.setSong) R.setSong(st.song);
    pvLoad();
  }
  $('pvUndo').onclick = function(){ if (!PVH.back.length) return; PVH.fwd.push(now()); apply(PVH.back.pop()); histUi(); };
  $('pvRedo').onclick = function(){ if (!PVH.fwd.length) return; PVH.back.push(now()); apply(PVH.fwd.pop()); histUi(); };
  $('pvSong').onchange = function(){ record(); PV.songStart = null; if (R.setSong) R.setSong($('pvSong').value); };
  document.querySelectorAll('[data-pv-vibe]').forEach(function(b){ b.onclick = function(){ record(); if (R.setVibe) R.setVibe(b.dataset.pvVibe); }; });
  document.querySelectorAll('[data-pv-style]').forEach(function(b){ b.onclick = function(){ record(); if (R.setStyle) R.setStyle(b.dataset.pvStyle); }; });
  $('pvPart').onclick = function(){
    var pl = PV.plan;
    if (!pl || !pl.song || !R.song()) { $('pvWords').textContent = W.pv_pick_song; return; }
    record();
    var len = pl.song.length || 0, step = Math.max(D.partMin, (pl.length || 10) * D.partShare);
    var next = pl.song.from + step;
    if (next + (pl.length || 0) > len - D.partEnd) next = 0;             // back to the top once the song runs out
    if (next === 0 && pl.song.from < 2) { $('pvWords').textContent = fill(W.pv_one_part, {len: Math.round(len), n: Math.round(pl.length || 0)}); return; }
    PV.songStart = Math.round(next * 100) / 100; pvLoad();
  };
  $('pvMix').onclick = function(){ record(); PV.variation += 1; mixSay(); pvLoad(); };
  $('pvMake').onclick = function(){ pvStop(); $('makeBtn').click(); };
  // her v27: Make this one in CapCut (and Make my reel) carry the mix and the start of the song that were watched
  R.watchExtra = function(){
    var o = {};
    if (PV.seen) o.variation = PV.variation;
    if (PV.plan && PV.plan.song && typeof PV.plan.song.from === 'number' && R.song()) o.song_start = PV.plan.song.from;
    return o;
  };

  // ---- B-roll: words on screen (hers: osDraw, osKnob, osDown; saved as "onscreen", only ever at a custom place) ----
  var onscreen = {text: '', font: 'avenir', style: 'white', pos: 'custom', x: 0.5, y: 0.24, size: 1, hold: 'all'};
  var OS_FONT = {avenir: "'Avenir Next', Avenir, 'Helvetica Neue', sans-serif", helvetica: "'Helvetica Neue', Helvetica, Arial, sans-serif", georgia: "Georgia, 'Times New Roman', serif"};
  function osWrap(x){ return Math.max(0.3, Math.min(0.8, 2 * Math.min(x, 1 - x) - 0.04)); }   // the words wrap inside the screen wherever they sit
  function cl(v, a, b){ return Math.min(b, Math.max(a, v)); }
  function osDraw(){
    var el = $('pvText'), txt = (onscreen.text || '').trim();
    if (!BROLL || !txt) { el.hidden = true; $('pvKnob').hidden = true; return; }
    var st = onscreen.style || 'white', box = /box$/.test(st), dark = st === 'black' || st === 'blackbox';
    var x = +onscreen.x || 0.5, y = +onscreen.y || 0.24, w = osWrap(x);
    el.style.left = (x - w / 2) * 100 + '%'; el.style.width = w * 100 + '%'; el.style.top = y * 100 + '%'; el.style.fontSize = 6.1 * (+onscreen.size || 1) + 'cqw';
    el.style.fontFamily = OS_FONT[onscreen.font] || OS_FONT.avenir;
    el.style.color = dark ? '#141414' : '#fff';
    el.innerHTML = '<span style="' + (box ? 'background:' + (st === 'whitebox' ? '#000' : '#fff') : '') + '">' + esc(txt) + '</span>';
    el.hidden = false; osKnob();
  }
  function osKnob(){   // the size dot sits on the words' bottom right corner
    var el = $('pvText'), k = $('pvKnob'); if (el.hidden || PV.playing) { k.hidden = true; return; }
    var sp = el.querySelector('span'), ph = $('pvPhone').getBoundingClientRect(); if (!sp || !ph.width) { k.hidden = true; return; }
    var rs = Array.prototype.slice.call(sp.getClientRects()), r = rs[rs.length - 1] || sp.getBoundingClientRect();
    var right = Math.max.apply(null, rs.map(function(q){ return q.right; }));
    k.style.left = (right - ph.left) / ph.width * 100 + '%'; k.style.top = (r.bottom - ph.top) / ph.height * 100 + '%'; k.hidden = false;
  }
  function osSave(){ _save(); }              // saves without rebuilding the preview: the words don't change the cut (hers)
  if (BROLL && $('osBox')) {
    ['osText', 'osFont', 'osStyle'].forEach(function(id){ $(id).addEventListener(id === 'osText' ? 'input' : 'change', function(){
      onscreen.text = $('osText').value; onscreen.font = $('osFont').value; onscreen.style = $('osStyle').value;
      osDraw(); osSave();
    }); });
    var OSD = null;
    function osDown(e, kind){
      e.preventDefault(); e.stopPropagation(); pvStop();
      var ph = $('pvPhone').getBoundingClientRect();
      OSD = {kind: kind, sx: e.clientX, sy: e.clientY, w: ph.width, h: ph.height, x: +onscreen.x || 0.5, y: +onscreen.y || 0.24, size: +onscreen.size || 1, moved: false};
      try { e.currentTarget.setPointerCapture(e.pointerId); } catch (er) {}
    }
    function osMove(e){
      var d = OSD; if (!d) return;
      var dx = (e.clientX - d.sx) / d.w, dy = (e.clientY - d.sy) / d.h;
      if (Math.abs(e.clientX - d.sx) + Math.abs(e.clientY - d.sy) > 2) d.moved = true;
      if (d.kind === 'move') { onscreen.x = Math.round(cl(d.x + dx, D.osX[0], D.osX[1]) * 1000) / 1000; onscreen.y = Math.round(cl(d.y + dy, D.osY[0], D.osY[1]) * 1000) / 1000; }
      else onscreen.size = Math.round(cl(d.size * (1 + (dx + dy) * 2.2), D.osSize[0], D.osSize[1]) * 100) / 100;   // right or down: bigger
      osDraw();
    }
    function osUp(){ var d = OSD; OSD = null; if (d && d.moved) osSave(); }
    $('pvText').addEventListener('pointerdown', function(e){ osDown(e, 'move'); });
    $('pvKnob').addEventListener('pointerdown', function(e){ osDown(e, 'size'); });
    ['pvText', 'pvKnob'].forEach(function(id){ $(id).addEventListener('pointermove', osMove); $(id).addEventListener('pointerup', osUp); $(id).addEventListener('click', function(e){ e.stopPropagation(); }); });
    window.addEventListener('resize', function(){ try { osKnob(); } catch (e) {} });
    // Save my video (hers): the reel's plan, then the finished MP4 with the song and the words, into the shoot's Reels
    // folder. Ours underneath: a job the page follows on /reel-job (hers waited on one request), so a reload while it
    // is being saved picks it up again, and a job that was stopped says so.
    var VID = {id: null, t: null, fails: 0};
    function vidSay(html){ $('pvSaved').innerHTML = html; }
    function vidDone(job){
      clearTimeout(VID.t); VID.t = null; VID.id = null; $('pvSaveVid').disabled = false;
      if (job.state === 'problem') { $('pvSaved').textContent = job.problem || W.went_wrong; return; }
      var secs = (typeof job.seconds === 'number' ? job.seconds : 0).toFixed(1);
      vidSay(esc(fill(W.os_saved, {file: job.video || '', secs: secs})) + ' <button class="btn small" id="openReels" type="button">' + esc(W.os_open_folder) + '</button><span class="say sm" id="reelsWent"></span>');
      $('openReels').onclick = function(){
        R.post('/reel-open', {kit: R.kit, what: 'reels'}).then(function(res){ $('reelsWent').textContent = (res.j && res.j.words) || ''; }).catch(function(){});
      };
      if (R.queue) R.queue.made();            // the reel counts as made now: Add this reel to my posting queue shows
      if (R.refresh) R.refresh();
    }
    function vidPoll(){
      VID.t = null;
      if (!VID.id) return;
      fetch('/reel-job?' + R.q + '&id=' + encodeURIComponent(VID.id), {cache: 'no-store'})
        .then(function(r){ return r.json(); })
        .then(function(j){
          VID.fails = 0;
          var job = j && j.job;
          if (!job || job.id !== VID.id) { vidDone({state: 'problem', problem: W.video_interrupted}); return; }
          if (job.state === 'done' || job.state === 'problem') { vidDone(job); return; }
          VID.t = setTimeout(vidPoll, D.jobEvery);
        })
        .catch(function(){
          if (++VID.fails > 40) { vidDone({state: 'problem', problem: W.no_server}); return; }
          VID.t = setTimeout(vidPoll, D.jobEvery * 2);
        });
    }
    function vidFollow(job){
      if (job.state === 'done' || job.state === 'problem') { vidDone(job); return; }
      VID.id = job.id; $('pvSaveVid').disabled = true;
      vidSay('<span class="spin"></span> ' + esc(W.os_saving));
      clearTimeout(VID.t); VID.t = setTimeout(vidPoll, D.jobEvery);
    }
    R.videoJob = function(job){ if (job && job.kind === 'video' && !VID.id) vidFollow(job); };
    if ($('pvSaveVid')) $('pvSaveVid').onclick = function(){
      if (VID.id) return;
      if (!(R.chosen && R.chosen().length)) { $('pvSaved').textContent = W.os_clips_first; return; }
      var st = R.state() || {};
      $('pvSaveVid').disabled = true; pvStop();
      vidSay('<span class="spin"></span> ' + esc(W.os_saving));
      var body = {kit: R.kit, stamp: st.stamp, song: R.song(), clips: R.chosen(), variation: PV.variation, onscreen: onscreen};
      if (PV.songStart != null) body.song_start = PV.songStart;
      R.flush().then(function(){ return R.post('/reel-video', R.withReel(body)); }).then(function(res){
        var j = res.j || {};
        if (j.job) { vidFollow(j.job); return; }
        $('pvSaveVid').disabled = false;
        $('pvSaved').textContent = j.words || W.went_wrong;      // a PC's line, no clips, another kind: in plain words
      }).catch(function(){ $('pvSaveVid').disabled = false; $('pvSaved').textContent = W.no_server; });
    };
  }
  R.part({
    fields: function(){ return BROLL ? {onscreen: onscreen} : {}; },
    adopt: function(st, first){
      byN = {}; (st.photos || []).forEach(function(p){ byN[p.n] = p; });
      if (BROLL && first && R.videoJob && st.job && st.job.kind === 'video' && (st.job.state === 'queued' || st.job.state === 'running')) R.videoJob(st.job);   // reloaded while a video was being saved
      if (BROLL) {
        var o = (st.saved || {}).onscreen;
        if (o && typeof o === 'object') ['text', 'font', 'style', 'x', 'y', 'size'].forEach(function(k){ if (o[k] !== undefined && o[k] !== null) onscreen[k] = o[k]; });
        if ($('osBox')) {
          if (first || document.activeElement !== $('osText')) $('osText').value = onscreen.text || '';
          $('osFont').value = onscreen.font; $('osStyle').value = onscreen.style;
        }
        osDraw();
      }
      chips(); songOptions();
      if (first) setTimeout(pvLoad, 300); else pvSoon();     // the preview, once everything has loaded (hers)
    },
    follow: function(st){ byN = {}; (st.photos || []).forEach(function(p){ byN[p.n] = p; }); }
  });
})();
"""

MAKE_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc;
  var TEST = new URLSearchParams(location.search).get('test') === '1';      // hers: plans the reel, makes nothing in CapCut
  var VIBE_WORDS = {beat: W.vibe_word_beat, mixed: W.vibe_word_mixed, calm: W.vibe_word_calm, build: W.vibe_word_build};
  var making = false, jobId = null, pollT = null, fails = 0;
  var btn = $('makeBtn'), out = $('result');
  if (TEST) btn.textContent = W.make_test;
  var BROLL = R.kind === 'broll';
  function enough(){ return BROLL ? !!(R.chosen && R.chosen().length) : !!(R.order && R.order().length); }   // her v27: B-roll needs clips, not photos
  function summary(){
    if (!R.order || !R.song || !R.vibe) return;
    var n = R.order().length, s = R.song(), name = R.songName();
    var songW = s === null ? W.sum_no_song_yet : s === '' ? W.sum_no_song : (name ? esc(name) : W.sum_no_song_yet);
    if (BROLL) {                                   // hers: "4 clips · B-roll · <song>" (written once; hers wrote the sum twice)
      var used = R.chosen ? R.chosen().length : 0;
      $('sum').innerHTML = '<b>' + esc(R.fill(W.sum_broll, {n: used, s: used === 1 ? '' : 's'})) + '</b> · ' + songW;
    } else {
      var ft = R.sumExtra ? R.sumExtra() : '';
      $('sum').innerHTML = '<b>' + esc(R.fill(n === 1 ? W.one_photo : W.photos, {n: n})) + ft + '</b> · ' + songW + ' · ' + esc(VIBE_WORDS[R.vibe()] || '');
    }
    if (!making) btn.disabled = !enough();
  }
  R.changed = summary;
  function busy(on){
    making = on;
    if (on) { btn.disabled = true; btn.innerHTML = '<span class="spin"></span> ' + esc(W.making); }
    else { btn.textContent = TEST ? W.make_test : W.make; btn.disabled = !enough(); }
  }
  function into_view(){ out.scrollIntoView({behavior: 'smooth', block: 'center'}); }
  function bad(h3, html){ out.className = 'result on bad'; out.innerHTML = '<h3>' + esc(h3) + '</h3><p>' + html + '</p>'; into_view(); }
  function lines(words){
    return (words || []).map(function(w){ return '<p' + (/^(Your song is only|I left out)/.test(w) ? ' class="leftout"' : '') + '>' + esc(w) + '</p>'; }).join('');
  }
  function show(job){
    clearTimeout(pollT); pollT = null; jobId = null; busy(false);
    if (job.state === 'problem') {
      var p = job.problem || W.went_wrong;
      out.className = 'result on bad';
      out.innerHTML = job.short_song
        ? '<h3>' + esc(W.short_h3) + '</h3><p>' + esc(p) + '</p>' + (/longer song/.test(p) ? '' : '<p>' + W.short_more_html + '</p>')
        : '<h3>' + esc(W.didnt_work_h3) + '</h3><p>' + esc(p) + '</p>';
    } else if (job.dry) {
      out.className = 'result on';
      out.innerHTML = '<h3>' + esc(W.test_h3) + '</h3>' + lines(job.words);
    } else {
      var back = $('back');
      out.className = 'result on';
      out.innerHTML = '<h3>' + esc(R.fill(W.in_capcut_h3, {project: job.project || W.new_reel})) + '</h3>' + lines(job.words) +
        '<p>' + esc(job.capcut_say || W.open_capcut_say) + '</p><div class="acts"><button class="btn main" id="capcut" type="button">' + esc(W.open_capcut) +
        '</button><button class="btn" id="toQueue" type="button">' + esc(W.toq_result) + '</button>' +
        '<a class="btn" id="resultBack" href="' + esc(back.getAttribute('href')) + '">' + esc($('backWords').textContent) + '</a></div><p class="went" id="went"></p><div id="qAsk"></div>';
      $('capcut').onclick = function(){
        R.post('/reel-capcut', {kit: R.kit}).then(function(res){ $('went').textContent = (res.j && res.j.words) || ''; }).catch(function(){});
      };
      // her v27: straight into the posting queue from here (the reel is made now, so the bar under Your reels shows too)
      if (R.queue) { R.queue.made(); $('toQueue').onclick = function(){ R.queue.add($('toQueue'), $('went'), $('qAsk')); }; }
    }
    into_view();
  }
  function poll(){
    pollT = null;
    if (!jobId) return;
    fetch('/reel-job?' + R.q + '&id=' + encodeURIComponent(jobId), {cache: 'no-store'})
      .then(function(r){ return r.json(); })
      .then(function(j){
        fails = 0;
        var job = j && j.job;
        if (!job || job.id !== jobId) { show({state: 'problem', problem: W.interrupted}); return; }
        if (job.state === 'done' || job.state === 'problem') { show(job); return; }
        pollT = setTimeout(poll, R.data.jobEvery);
      })
      .catch(function(){
        if (++fails > 40) { show({state: 'problem', problem: W.no_server}); return; }
        pollT = setTimeout(poll, R.data.jobEvery * 2);
      });
  }
  function follow(job){
    if (job.state === 'done' || job.state === 'problem') { show(job); return; }
    jobId = job.id; busy(true);
    out.className = 'result on'; out.innerHTML = '<p>' + esc(W.finding_beat) + '</p>';
    clearTimeout(pollT); pollT = setTimeout(poll, R.data.jobEvery);
  }
  btn.onclick = function(){
    if (making) return;
    if (R.song() === null) { bad(W.need_song_h3, W.need_song_html); return; }
    var stop = R.beforeMake ? R.beforeMake() : null;
    if (stop) { bad(stop.h3, stop.html); return; }
    busy(true);
    out.className = 'result on'; out.innerHTML = '<p>' + esc(W.finding_beat) + '</p>';
    var st = R.state() || {}, extra = R.makeExtra ? R.makeExtra() : {}, watched = R.watchExtra ? R.watchExtra() : {};
    var body = {kit: R.kit, stamp: st.stamp, picks: R.order(), song: R.song(), vibe: R.vibe(), test: TEST};
    for (var k in extra) body[k] = extra[k];
    for (var k2 in watched) body[k2] = watched[k2];     // her v27: the mix and the part of the song they watched
    // what is still waiting to be saved (B-roll's words, say) lands first: the make reads the record for them
    R.flush().then(function(){ return R.post('/reel-make', body); }).then(function(res){
      var j = res.j || {};
      if (j.job) { follow(j.job); return; }             // started, or already being made: that one is followed
      busy(false); bad(W.didnt_work_h3, esc(j.words || W.went_wrong));
    }).catch(function(){ busy(false); bad(W.didnt_work_h3, esc(W.no_server)); });
  };
  R.part({
    adopt: function(st, first){
      var job = st.job;
      // reloaded while one is at work (a Save my video job is the watch step's own, not Make my reel's)
      if (first && job && job.kind !== 'video' && (job.state === 'queued' || job.state === 'running') && !making) follow(job);
      summary();
    }
  });
})();
"""

# Her v27: Add this reel to my posting queue (reelToQueue), from the bar under Your reels once the open reel is
# made and from the box after Make my reel: the rhythm asked once with her five chips (POST /words-rhythm), then
# the add (POST /words-queue {kit, piece: 'reel', reel}), on the routes the post kit's page uses. Ours underneath:
# the queue is asked afresh at the press (its answer by version, so a piece queued without a date still reads as
# queued), it is asked once and added once (hers re-entered itself after the rhythm was set).
QUEUE_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc, D = R.data;
  var bar = $('toqBar'), adding = false;
  function niceDate(d){ try { return new Date(d + 'T12:00:00').toLocaleDateString('en-US', {weekday: 'long', month: 'short', day: 'numeric'}); } catch (e) { return d; } }
  function cur(){ return R.reels ? R.reels.current() : 'v1'; }
  function label(st){
    var vs = (st && st.versions) || [], me = vs.filter(function(v){ return v.id === cur(); })[0];
    return vs.length > 1 && me ? R.fill(W.q_label, {short: st.short, name: me.name}) : R.fill(W.q_label_one, {short: st ? st.short : ''});
  }
  function queued(q){ var m = q && q.reels && q.reels[cur()]; return m && (m.status === 'green' || m.status === 'posted') ? m : null; }
  function link(q){ return q && q.url ? ' <a href="' + esc(q.url) + '">' + esc(W.q_open) + '</a>' : ''; }
  function done(btn){ btn.textContent = W.q_done; btn.disabled = false; }
  function add(btn, went, ask){
    if (adding) return;
    adding = true; went.textContent = W.q_adding; ask.innerHTML = ''; btn.disabled = true;
    R.fresh().then(function(st){
      var q = (st && st.queue) || {};
      var mine = queued(q);
      if (mine) {                                        // hers: already in the queue, with its date
        adding = false;
        went.innerHTML = esc(R.fill(W.q_already, {set: mine.date ? R.fill(W.q_set, {day: niceDate(mine.date)}) : ''})) + link(q);
        done(btn); return;
      }
      if (!q.interval) {                                 // the queue asks once how often they post
        adding = false; went.textContent = '';
        ask.innerHTML = '<p class="say" style="margin:.4rem 0 .3rem"><b>' + esc(W.q_how) + '</b>' + esc(W.q_how_b) + '</p><div class="acts">' +
          D.rhythms.map(function(t){ return '<button class="btn small" type="button" data-iv="' + esc(t) + '">' + esc(t) + '</button>'; }).join('') + '</div>';
        ask.querySelectorAll('[data-iv]').forEach(function(b){ b.onclick = function(){
          ask.querySelectorAll('[data-iv]').forEach(function(x){ x.disabled = true; });
          R.post('/words-rhythm', {text: b.dataset.iv}).then(function(res){
            if (!res.j || !res.j.ok) { went.textContent = (res.j && res.j.words) || W.q_cant; ask.querySelectorAll('[data-iv]').forEach(function(x){ x.disabled = false; }); return; }
            ask.innerHTML = ''; add(btn, went, ask);     // once: the rhythm is set now, so this goes straight to the add
          }).catch(function(){ went.textContent = W.q_cant; ask.querySelectorAll('[data-iv]').forEach(function(x){ x.disabled = false; }); });
        }; });
        btn.disabled = false; return;
      }
      return R.flush().then(function(){ return R.post('/words-queue', {kit: R.kit, piece: 'reel', reel: cur()}); }).then(function(res){
        adding = false;
        var j = res.j || {};
        if (!j.ok) { went.textContent = j.words || W.q_cant; btn.disabled = false; return; }
        var got = j.queue || {};
        went.innerHTML = esc(R.fill(W.q_in, {label: label(st), going: got.date ? R.fill(W.q_going, {day: niceDate(got.date)}) : ''})) + link(q);
        done(btn);
      });
    }).catch(function(){ adding = false; went.textContent = W.q_cant; btn.disabled = false; });
  }
  function show(st){
    if (!bar) return;
    var made = st && st.made && st.made[cur()];
    bar.hidden = !made;
    var q = st && st.queue, mine = queued(q);
    if (made && mine && !$('went2').textContent) $('toQueue2').textContent = W.q_done; else if (made && !mine && $('toQueue2').textContent === W.q_done) $('toQueue2').textContent = W.toq_btn;
  }
  if (bar) $('toQueue2').onclick = function(){ add($('toQueue2'), $('went2'), $('qAsk2')); };
  R.queue = {add: add, made: function(){ if (bar) bar.hidden = false; }};
  R.part({adopt: show, follow: show});
})();
"""

START_JS = r"""window.Reel.start();"""


# ---------- the commands (Claude's) ----------

def page_address(kit):
    base = arrange.server_base()
    return f"{base}/reel.html?kit={quote(kit.name)}" if base else None


def cmd_open(kit):
    listed = arrange.kit_by_name(kit.name)
    if listed is None or listed.resolve() != kit.resolve():
        say(f"STOP: \"{kit.name}\" isn't in Your Content, so the page can't show it.")
        return 1
    if not arrange.sheet_rows(kit):
        if kit_mod.sheet(kit) != 0 or not arrange.sheet_rows(kit):
            say("STOP: couldn't number this shoot's photos. Are they where the kit says they are?")
            return 1
    got = arrange.make_previews(kit)
    if got.get("cant"):
        say(f"STOP: {got['cant']}")
        return 1
    if got["missing"] or got["failed"]:
        say(f"({got['missing'] + got['failed']} of {got['of']} photos couldn't be read right now; the page will say so.)")
    addr = page_address(kit)
    if not addr:
        say("STOP: couldn't start the page server.")
        return 2
    say(f"{got['of']} photos in the shoot.")
    kind = reel_kind((as_reel(load(kit), None).get("saved")))
    if kind:
        vs, cur = reel_names(kit)
        say(f"The reel being worked on, \"{reels.name_of({'versions': vs}, cur, REEL_FIRST)}\", is a {KIND_NAMES[kind]} reel: "
            f"{addr}&kind={kind} (the address below is the chooser of the four kinds).")
    say(addr)
    return 0


def _reel_or_stop(kit, words):
    """A chat command's --reel: the reel's id, or None after saying why not (nothing was changed)."""
    vid, why = which_reel(kit, words)
    if vid is None:
        say(f"STOP: {why} Nothing was changed.")
    return vid


def reels_line(vs, cur, shown=None, kinds=None):
    """One line naming the shoot's reels, the one being worked on marked (and the one a command is about), each
    with its kind when it has one (v27)."""
    kinds = kinds or {}
    return ", ".join(f"\"{v['name']}\"" + (f" ({KIND_NAMES[kinds[v['id']]]})" if kinds.get(v["id"]) in KIND_NAMES else "")
                     + (" (the one open on the page)" if v["id"] == cur else "")
                     + (" (this one)" if shown and v["id"] == shown and shown != cur else "") for v in vs)


KIND_NAMES = {"bts": "behind the scenes", "photos": "just photos", "broll": "B-roll"}    # the chat's words for a kind


def cmd_reels(kit, a):
    """reel_page.py reels "<kit>" [--new [--name N] [--kind bts|photos|broll] | --open "<reel>" | --rename "<reel>" --to "<name>"]:
    the shoot's reels, and the page's own three moves from the chat (the same checks, the same record)."""
    ask = None
    if a.new:
        ask = {"op": "new", **({"name": a.name} if a.name else {}), **({"kind": a.kind} if getattr(a, "kind", None) else {})}
    elif a.open or a.rename:
        vid = _reel_or_stop(kit, a.open or a.rename)
        if vid is None:
            return 1
        if a.rename and not a.to:
            say("STOP: --rename needs --to \"<the new name>\". Nothing was changed.")
            return 1
        ask = {"op": "switch", "id": vid} if a.open else {"op": "rename", "id": vid, "name": a.to}
    if ask is not None:
        code, out = version_from_page(dict(ask, kit=kit.name))
        if code != 200:
            say(f"STOP: {out.get('words')} Nothing was changed.")
            return 1
    vs, cur = reel_names(kit)
    kinds = kinds_of(load(kit))
    say(f"{short_name(kit.name)}: {len(vs)} reel{'s' if len(vs) != 1 else ''}: {reels_line(vs, cur, kinds=kinds)}.")
    if ask is not None and ask["op"] != "rename":
        say("The page shows it after a reload (or \"show my reel page\").")
    return 0


def photo_note(saved):
    """Their note for this reel's photos (her v25 saved.photo_ask), as one piece of text; "" when there is none."""
    v = (saved or {}).get("photo_ask")
    return v.strip() if isinstance(v, str) else ""


def direct_note(saved):
    """How they'd like this reel to go (her v27 saved.direct, "Would you like to direct this edit?"); "" when none."""
    v = (saved or {}).get("direct")
    return v.strip() if isinstance(v, str) else ""


def cmd_note(kit, reel=None):
    """reel_page.py note "<kit>" [--reel "<the reel the pasted line names>"]: what the Assistant reads before it
    picks a reel's photos (her v25, "Pick my reel photos for <shoot>, <reel name>, and follow my note"): which reel
    the pick is for, whether that is the reel open on the page, and their note for that reel's photos, word for
    word. It changes nothing."""
    vid = None
    if reel:
        vid = _reel_or_stop(kit, reel)
        if vid is None:
            return 1
    st = state(kit, vid)
    if st is None:
        say("STOP: couldn't read this shoot's numbered list (kit.py sheet makes it). Nothing was changed.")
        return 1
    several = len(st["versions"]) > 1
    name = reels.name_of({"versions": st["versions"]}, st["current"], REEL_FIRST)
    say(f"{st['short']}  ({kit.name})")
    for_reel = ""
    if not several:
        say("  This shoot has one reel. The pick is for it.")
    elif st["current"] == st["on_page"]:
        say(f"  The pick is for \"{name}\", the reel open on the page ({len(st['versions'])} reels: {reels_line(st['versions'], st['on_page'])}).")
    else:
        on = reels.name_of({"versions": st["versions"]}, st["on_page"], REEL_FIRST)
        say(f"  NOTE: the line names \"{name}\", but the reel open on the page is \"{on}\". The pick is for \"{name}\" only: "
            f"save it with --for-reel, and tell them it shows when they open \"{name}\" in Your reels. "
            f"Nothing of \"{on}\" changes.")
        for_reel = f' --for-reel "{name}"'
    if several and not reel:
        say("  (If the line they pasted names another reel, run this again with --reel \"<that name>\".)")
    note = photo_note(st["saved"])
    if note:
        say("  Their note for this reel's photos, word for word:")
        for ln in note.splitlines():
            say("    " + ln)
        say("  Pick only what the note allows. It is theirs: follow it exactly, never widen it. If no photo in the "
            "shoot fits it, or you can't tell which photos it means, say so and ask; don't fill in with photos it leaves out.")
    else:
        say("  No note for this reel's photos: choose from the whole shoot, the way curating.md says.")
    if direct_note(st["saved"]):
        say("  Their direction for how this reel should go (\"Edit my reel ... and follow my direction\" is reel_page.py direct):")
        for ln in direct_note(st["saved"]).splitlines():
            say("    " + ln)
    have = ",".join(str(x["n"]) + x["h"] for x in st["claude"])
    say(f"  Your pick for this reel so far: {have or '(none yet)'}")
    say(f"  Save the pick, for this reel only: kit.py picks \"{kit.name}\" --reel <numbers, in play order, marked>{for_reel}")
    return 0


def cmd_show(kit, reel=None):
    vid = None
    if reel:
        vid = _reel_or_stop(kit, reel)
        if vid is None:
            return 1
    st = state(kit, vid)
    if st is None:
        say("STOP: couldn't read this shoot's numbered list. Nothing was changed.")
        return 1
    saved = st["saved"] or {}
    say(f"{st['short']}  ({kit.name})")
    kind = st.get("kind")
    say(f"  Kind: {KIND_NAMES[kind] if kind else 'not chosen yet (the page opens on the chooser of the four kinds)'}")
    if len(st["versions"]) > 1:
        say(f"  This shoot's reels: {reels_line(st['versions'], st['on_page'], st['current'], kinds={v['id']: v.get('kind') for v in st['versions']})}. "
            f"What follows is \"{reels.name_of({'versions': st['versions']}, st['current'], REEL_FIRST)}\"."
            + ("" if st["current"] != st["on_page"] else " Name another with --reel \"<its name>\"."))
    say(f"  Claude's order: {','.join(str(x['n']) + x['h'] for x in st['claude']) or '(none yet)'}")
    if saved:
        whose = "their own order" if saved.get("mine") else "the assistant's order"
        say(f"  On the page: {whose}")
    else:
        say("  On the page: nothing saved yet")
    say(f"  The order Make my reel uses: {current_picks(kit, vid) or '(none yet)'}")
    sid = saved.get("song")
    songs = list_songs(kit)
    if songs:
        say("  Songs in the shoot: " + "; ".join(f"{x['name']} ({'a screen recording' if x['kind'] == 'video' else 'a song'}, {x['where']}, id {x['id']})"
                                                + (" <- picked" if x["id"] == sid else "") for x in songs))
    if sid is None:
        say("  Song: not picked on the page yet")
    elif sid == "":
        say("  Song: No song (they'll add music in Instagram)")
    else:
        s = song_by_id(kit, sid)
        say(f"  Song: {s['path'].name} ({'a screen recording, its sound' if s['kind'] == 'video' else 'a song'}, in the {s['where']} folder)"
            if s else "  Song: the one they picked is not there anymore")
    vibe = saved.get("vibe")
    say(f"  Vibe: {WORDS['vibe_' + vibe + '_b'] if vibe in VIBES else 'not picked on the page yet'}"
        + ("" if vibe in VIBES else f" (Make my reel would use {WORDS['vibe_' + default_vibe() + '_b']})"))
    rec = as_reel(load(kit), vid)
    ms = moments_of(rec)
    foot = saved.get("footage")
    if foot is True:
        style = style_of(saved)
        clips = chosen_clips(saved, ms)
        say(f"  Footage: yes, {KIND_WORDS['kind_broll_b'] + ' (clips only, no photos)' if style == BROLL_STYLE else WORDS['style_' + style + '_b']}, "
            f"{len(clips)} clip{'s' if len(clips) != 1 else ''} selected" + (f" ({', '.join(clips)})" if clips else ""))
    else:
        say("  Footage: " + ("Just photos" if foot is False else "not chosen on the page yet"))
    vids = list_videos(kit)
    if vids or ms:
        say(f"  In the Footage folder: {len(vids)} video{'s' if len(vids) != 1 else ''}"
            + (f" ({', '.join(v['name'] for v in vids)})" if vids else "") + f"; moments: {len(ms)}"
            + (f", {sum(1 for m in ms if m.get('by') == 'you')} of them theirs" if ms else ""))
    looks = foot_work(kit) / "looks"
    n_looks = sum(1 for x in _listing(looks) if re.fullmatch(r"look(?: \d+)?", x)) if looks.is_dir() else 0
    if n_looks:
        mine = sum(1 for m in ms if m.get("by") != "you")
        say(f"  Footage looks (footage.py scan): {n_looks}; Claude's moments on the page: {mine}")
    if photo_note(saved):
        say(f"  Their note for this reel's photos (reel_page.py note): {' / '.join(photo_note(saved).splitlines())}")
    if saved.get("ask") or saved.get("feel"):
        say(f"  Their notes for the footage look: {saved.get('ask') or '(none)'}; the feel: {saved.get('feel') or '(none)'}")
    if direct_note(saved):
        say(f"  Their direction for how this reel should go (reel_page.py direct sets it up): {' / '.join(direct_note(saved).splitlines())}")
    ons = saved.get("onscreen") if isinstance(saved.get("onscreen"), dict) else None
    if ons and str(ons.get("text") or "").strip():
        say(f"  Words on screen (B-roll): \"{' '.join(str(ons['text']).split())}\", {ONSCREEN_WORDS.get('os_' + str(ons.get('font')), ons.get('font'))}, "
            f"{ONSCREEN_WORDS.get('os_' + str(ons.get('style')), ons.get('style'))}, at {ons.get('x')}, {ons.get('y')} of the screen, size {ons.get('size')}")
    made = [m for m in (rec.get("made") or []) if isinstance(m, dict)]
    if len(st["versions"]) > 1:
        made = [m for m in made if made_for(m) == st["current"]]
    projects = [m for m in made if m.get("project")]
    videos = [m for m in made if isinstance(m.get("video"), str) and m["video"]]
    if projects:
        last = projects[-1]
        mix = (f" (mix {int(last['variation']) + 1}" + (f", the song from {float(last['song_start']):.1f} s" if isinstance(last.get("song_start"), (int, float)) else "") + ")"
               if isinstance(last.get("variation"), int) else "")
        say(f"  Reels made from the page: {len(projects)}, the newest \"{last.get('project')}\"{mix}")
    if videos:                   # her v27, Save my video (B-roll): the finished file in the shoot's Reels folder
        say(f"  Videos saved from the page (Save my video, in this shoot's Reels folder): {len(videos)}, the newest \"{videos[-1]['video']}\""
            + (f" ({float(videos[-1]['seconds']):.1f} seconds)" if isinstance(videos[-1].get("seconds"), (int, float)) else ""))
    q = st.get("queue") or {}
    inq = [v["name"] for v in st["versions"] if (q.get("reels") or {}).get(v["id"], {}).get("status") in ("green", "posted")]
    if inq:
        say("  In the posting queue: " + ", ".join(f'"{n}"' for n in inq))
    say(f"  Saved {st['rev']} time{'s' if st['rev'] != 1 else ''}")
    return 0


def cmd_make(kit, a):
    """Claude's own Make my reel (see the top of this file): what the page would hand reel.py, made the same way,
    one reel at a time on this computer. A song comes from the page, unless they asked for CapCut's own music."""
    vid = None
    if getattr(a, "reel", None):
        vid = _reel_or_stop(kit, a.reel)
        if vid is None:
            return 1
    st = state(kit, vid)
    if st is None:
        say("STOP: couldn't read this shoot's numbered list. Nothing was made.")
        return 1
    saved = st["saved"] or {}
    picks = current_picks(kit, vid)
    broll = saved.get("footage") is True and style_of(saved) == BROLL_STYLE
    if not picks and not broll:
        say("STOP: there's no order for this reel yet: pick the photos first (kit.py picks --reel), or they put them in order on the page.")
        return 1
    if len([x for x in picks.split(",") if x]) > MAX_PICKS:
        say("STOP: " + OUR_WORDS["too_many"])
        return 1
    vibe = saved.get("vibe") if saved.get("vibe") in VIBES else default_vibe()
    ask = {"picks": picks, "vibe": vibe, "dry": bool(a.dry_run), "stamp": st["stamp"]}
    if len(st["versions"]) > 1:
        ask["reel"] = st["current"]             # this reel's clips, and noted as this reel's
        say(f"(Making \"{reels.name_of({'versions': st['versions']}, st['current'], REEL_FIRST)}\", one of this shoot's {len(st['versions'])} reels.)")
    if saved.get("footage") is True:            # behind the scenes, as the page would make it: its style, its clips
        style = style_of(saved)
        with arrange.locked(lock_path(kit)):
            ms = moments_of(as_reel(load(kit), vid))
        clips = chosen_clips(saved, ms)
        if not clips:
            say("STOP: footage is on for this reel, but no clips are selected on the page (Use, under Your clips in step 1). "
                "They select them there, or choose Just photos.")
            return 1
        ask.update(footage=style, clips=clips)
    if getattr(a, "variation", None) is not None:
        if a.variation < 0 or a.variation > MIX_MOST:
            say(f"STOP: --variation is a mix number from 0 to {MIX_MOST}. Nothing was made.")
            return 1
        ask["variation"] = int(a.variation)
    if getattr(a, "song_start", None) is not None:
        if not 0 <= a.song_start <= 36000:
            say("STOP: --song-start is where the song starts, in seconds. Nothing was made.")
            return 1
        ask["song_start"] = float(a.song_start)
    if a.capcut_song:
        ask["capcut_song"] = a.capcut_song
    elif a.no_song or saved.get("song") == "":
        ask["song"] = ""
    elif saved.get("song"):
        if song_by_id(kit, saved["song"]) is None:
            say("STOP: " + WORDS["song_gone"])
            return 1
        ask["song"] = saved["song"]
    else:
        say("STOP: no song is picked on the page yet. The song is theirs to pick there (Add my music, or No song); pass --no-song only when they have said no song.")
        return 1
    if a.hook:
        ask["hook"] = a.hook
    if a.name:
        ask["name"] = a.name
    t0 = time.time()
    g = _hold_make_lock(t0 + MAKE_LIMIT)
    if g is None:
        say("STOP: another reel is still being made on this computer. Try again in a moment.")
        return 2
    try:
        res = _make(kit, ask, "chat" + os.urandom(4).hex(), t0)
    finally:
        if g != "none":
            this_computer.unlock(g)
            g.close()
    if res.get("state") != "done":
        say("STOP: " + str(res.get("problem") or WORDS["went_wrong_make"]))
        return 1
    for w in res.get("words") or []:
        say(w)
    if not a.dry_run and res.get("project"):
        say(f"Made: {res['project']}")
        if res.get("capcut_say") and res["capcut_say"] != WORDS["open_capcut_say"]:
            say(res["capcut_say"])          # not in CapCut's list yet: what to tell them
    return 0


def cmd_direct(kit, a):
    """reel_page.py direct "<kit>" [--reel] [--style] [--clips ids...] [--order "7+,2,11-,4"]: "Edit my reel for
    <shoot>, and follow my direction" (her v27). After reading their direction (cmd_show / cmd_note print it), the
    Assistant sets up that reel the way the direction says, in one go: the style, the clips it uses in play order,
    and the photos' order. Everything is checked first (a style of hers, clip ids that are this reel's, no more
    than the style takes, photos on the numbered list, none twice) and nothing is written when anything is wrong.
    The style and the clips go into the reel's saved choices under the record's lock, the rev moved on so an open
    page redraws; the order is the Assistant's pick for that reel (kit.py picks, the one writer of picks) and the
    page is set to follow it (saved.mine off). Run twice, it writes nothing. Not for a B-roll reel (her v27: no
    direction there)."""
    vid = None
    if getattr(a, "reel", None):
        vid = _reel_or_stop(kit, a.reel)
        if vid is None:
            return 1
    if a.style is None and a.clips is None and a.order is None:
        say("STOP: say what to set up: --style, --clips and/or --order. Nothing was changed.")
        return 1
    st = state(kit, vid)
    if st is None:
        say("STOP: couldn't read this shoot's numbered list. Nothing was changed.")
        return 1
    which = vid or st["current"]
    saved = st["saved"] or {}
    if style_of(saved) == BROLL_STYLE or st.get("kind") == BROLL_STYLE:
        say("STOP: this is a B-roll reel, which has no direction (its clips are chosen under Your clips). Nothing was changed.")
        return 1
    if a.style is not None and a.style not in STYLES:
        say(f"STOP: no style called \"{a.style}\". Pick one of: {', '.join(STYLES)}. Nothing was changed.")
        return 1
    style = a.style if a.style is not None else style_of(saved)
    with arrange.locked(lock_path(kit)):
        rec_now = as_reel(load(kit), vid)
    ms = moments_of(rec_now)
    ids = {m["id"] for m in ms}
    clips = None
    if a.clips is not None:
        clips = [str(x).strip() for x in a.clips if str(x).strip()]
        bad = [c for c in clips if c not in ids]
        if bad:
            say(f"STOP: no clip \"{bad[0]}\" in this reel (its clips: {', '.join(sorted(ids)) or 'none yet'}). Nothing was changed.")
            return 1
        if len(set(clips)) != len(clips):
            say("STOP: a clip is named twice. Each clip plays once. Nothing was changed.")
            return 1
        most = STYLE_MAX.get(style, MAX_CLIPS)
        if len(clips) > most:
            say(f"STOP: {WORDS['style_' + style + '_b']} uses at most {most} clip{'s' if most != 1 else ''}, and {len(clips)} were named. Nothing was changed.")
            return 1
        if not clips:
            say("STOP: --clips names no clip. Nothing was changed.")
            return 1
    order_text = None
    if a.order is not None:
        nums, marks = kit_mod.parse_reel(a.order)
        if not nums:
            say("STOP: --order is the photo numbers in play order, like 7+,2,11-,4. Nothing was changed.")
            return 1
        on_sheet = {p["n"] for p in st["photos"]}
        bad = [n for n in nums if n not in on_sheet]
        if bad:
            say(f"STOP: no photo numbered {bad[0]} on the sheet. Nothing was changed.")
            return 1
        if len(set(nums)) != len(nums):
            say("STOP: a photo is in that order twice. Nothing was changed.")
            return 1
        if len(nums) > MAX_PICKS:
            say("STOP: " + OUR_WORDS["too_many"] + " Nothing was changed.")
            return 1
        order_text = ",".join(f"{n}{marks.get(str(n), '')}" for n in nums)
    # the order: the Assistant's pick for this reel, through kit.py picks (nothing is written when it is that already)
    have = ",".join(str(x["n"]) + x["h"] for x in st["claude"])
    if order_text is not None and order_text != have:
        cmd = [sys.executable, str(HERE / "kit.py"), "picks", kit.name, "--reel", order_text]
        if which != reels.FIRST_ID:
            cmd += ["--for-reel", reels.name_of({"versions": st["versions"]}, which, REEL_FIRST)]
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=120)
        if r.returncode != 0:
            say("STOP: the order could not be saved: " + (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "STOP: the order could not be saved.")
            return 1
    # the style, the clips and "follow the assistant's order", in one save under the lock
    with arrange.locked(lock_path(kit)):
        rec, rows, stamp = sync(kit)
        if not rows:
            say("STOP: couldn't read this shoot's numbered list. The style and clips were not changed.")
            return 1
        with reels.turned(rec, which, REEL_LIVE, REEL_FIRST):
            sv = dict(rec.get("saved") if isinstance(rec.get("saved"), dict) else {})
            new = dict(sv)
            new["style"] = style
            new["footage"] = True
            if clips is not None:
                sel = dict(sv.get("sel") if isinstance(sv.get("sel"), dict) else {})
                sel[style] = list(clips)
                new["sel"] = sel
            if order_text is not None:
                new["mine"] = False
            changed = new != sv
            if changed:
                new["updated"] = time.time()
                rec["saved"] = new
        if changed:
            rec["rev"] = int(rec.get("rev") or 0) + 1
            rec.pop("from", None)
            _stamp_names(rec, rows, stamp)
            save(kit, rec)
    name = reels.name_of({"versions": st["versions"]}, which, REEL_FIRST)
    used = clips if clips is not None else chosen_clips(dict(saved, style=style), ms)
    say(f"Set up \"{name}\": {WORDS['style_' + style + '_b']}, {len(used)} clip{'s' if len(used) != 1 else ''}"
        + (f" ({', '.join(used)})" if used else "") + (f", the photos {order_text}" if order_text is not None else "")
        + ("" if changed or (order_text is not None and order_text != have) else " (as it was already; nothing written)")
        + ". The page shows it by itself.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("open").add_argument("words")
    sh = sub.add_parser("show")
    sh.add_argument("words")
    sh.add_argument("--reel", help="another of the shoot's reels, by name (without it: the one being worked on)")
    rl = sub.add_parser("reels", help="the shoot's reels; start a new one, open another, or rename one")
    rl.add_argument("words")
    rl.add_argument("--new", action="store_true", help="start a new reel (the one being worked on is kept as it is)")
    rl.add_argument("--name", help="with --new: its name (without it: Reel 2, Reel 3...)")
    rl.add_argument("--kind", choices=KINDS, help="with --new: which kind of reel it is (bts: behind the scenes, photos, broll); without it, the page's chooser asks")
    rl.add_argument("--open", help="work on this reel (its name)")
    rl.add_argument("--rename", help="rename this reel (its name now)")
    rl.add_argument("--to", help="with --rename: the new name")
    nt = sub.add_parser("note", help="before picking a reel's photos: which reel the pick is for, and their note for it")
    nt.add_argument("words")
    nt.add_argument("--reel", help="the reel the line they pasted names (without it: the one being worked on)")
    m = sub.add_parser("make", help="Claude's own Make my reel: the page's order, song and vibe")
    m.add_argument("words")
    m.add_argument("--reel", help="another of the shoot's reels, by name (without it: the one being worked on)")
    m.add_argument("--capcut-song", help="a song from CapCut's music (only when they asked for it, after the licence note)")
    m.add_argument("--hook", help="words on the first photo, when they asked for them")
    m.add_argument("--name", help="another name for the CapCut project (a second take)")
    m.add_argument("--no-song", action="store_true", help="no song, whatever the page has")
    m.add_argument("--dry-run", action="store_true")
    m.add_argument("--variation", type=int, help="which mix (0 is the first; the watch step's \"Mix 2\" is 1); without it, the next one")
    m.add_argument("--song-start", type=float, help="where the song starts, in seconds (the watch step's Another part of this song)")
    dr = sub.add_parser("direct", help="Edit my reel ... and follow my direction: the style, the clips and the order for a reel, in one go")
    dr.add_argument("words")
    dr.add_argument("--reel", help="the reel the line they pasted names (without it: the one being worked on)")
    dr.add_argument("--style", help="first (Moment first), reveal (The reveal), backforth (Back and forth) or bookends")
    dr.add_argument("--clips", nargs="*", help="the clips' ids, in the order they play (reel_page.py show lists them)")
    dr.add_argument("--order", help="the photos in play order, like 7+,2,11-,4 (+ Longer, - Quicker)")
    j = sub.add_parser("job", help="(the page server's own) make the reel a page asked for")
    j.add_argument("kit")
    j.add_argument("--id", required=True)
    a = ap.parse_args()
    if a.cmd == "job":
        kit = Path(a.kit)
        if not (kit / ".kit" / "kit.json").is_file() or not JOB_ID.fullmatch(a.id):
            return 2
        return cmd_job(kit, a.id)
    import fresh
    fresh.announce()
    kit = kit_mod.find_kit(a.words)
    try:
        if a.cmd == "open":
            return cmd_open(kit)
        if a.cmd == "make":
            return cmd_make(kit, a)
        if a.cmd == "reels":
            return cmd_reels(kit, a)
        if a.cmd == "note":
            return cmd_note(kit, a.reel)
        if a.cmd == "direct":
            return cmd_direct(kit, a)
        return cmd_show(kit, a.reel)
    except arrange.Busy:
        say("STOP: this shoot's reel page is being written by something else right now. Nothing was changed. Try again in a moment.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
