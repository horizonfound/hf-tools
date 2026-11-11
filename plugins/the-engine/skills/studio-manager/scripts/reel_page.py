#!/usr/bin/env python3
"""The reel page: Nicole's reel maker (handoff v19, pages/reel-maker.html), as the Assistant's own page.

    python3 reel_page.py open "beach"      get the page ready (the numbered list, the small copies) and print its address
    python3 reel_page.py show "beach"      what the page has saved: whose order, the order, the song and vibe picked
    python3 reel_page.py make "beach" [--capcut-song "<name>"] [--hook "..."] [--name "..."] [--no-song] [--dry-run]
                                           Claude's own Make my reel, for what the page doesn't do (a song from
                                           CapCut's music, words on the first photo, a second take under another
                                           name) or when the page said "Ask your assistant to make the reel instead":
                                           the page's order, song and vibe, made exactly as the page makes it
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

Routes, all on the posting server (posting_queue.py hands them here):
  GET  /reel.html?kit=<folder>   the page
  GET  /reel-state?kit=<folder>  everything the page draws from: the photos (numbers and sizes only), Claude's
                                 order, what was saved, the record's counter
  POST /reel-save                {kit, stamp, base, page, saved: {...}}: the page's choices, checked field by field
  GET  /reel-font?f=<name>       one of the plugin's own font files (FACES)
  GET  /reel-songs?kit=<folder>  step 3: the songs in the shoot's Music and Photos folders, {id, name, where, kind}
  POST /reel-open                {kit, what: "music"}: makes <kit>/Music if it isn't there and opens it (finder.py)
  POST /reel-make                {kit, stamp, picks, song, vibe, test}: Make my reel; answers with a job to ask after
  GET  /reel-job?kit=&id=        how that job is going: queued, running, done (her lines) or problem (her words)
  POST /reel-capcut              {kit, from?}: Open CapCut (capcut.py's own open), in her words (capcut.OPEN_WORDS);
                                 "from": "kit" is the post kit's Reel card (her "Open in CapCut" button)
Small copies of the photos are arrange.py's (/kit-photo, .kit/previews), the same the pickers use.

Records:
  <kit>/.kit/reel-page.json       {"v": 1, "rev": the counter (only this file moves it on, by one for every accepted
                                  save), "from": {page, base} of the last save, "stamp": the numbered list it was saved
                                  against, "names": {number: file name} for every number it mentions (so a re-made
                                  list finds the same photos again), "saved": {picks, mine, mine_picks, song, vibe,
                                  footage, style, sel, ask, feel, updated}, and, from the later stages, "moments",
                                  "claude_bts" and "made"; Claude's moments are written only by footage.py moments,
                                  which keeps those of an earlier look in "earlier_looks"}. Her record (BUILD.md section 8), minus her "claude", which
                                  is read from kit.json picks.reel every time.
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

The page is built so the steps still to come slot in where hers has them: SECTIONS keeps her order (1 footage,
2 the order, 3 the song, 4 the style, 5 the vibe), and an empty slot is simply left out; her renumbering counts
only the steps that show. The page's script is a small core (CORE_JS: the record, saving, following) with one
part per step (ORDER_JS is step 2); each later step adds its own part and its own fields to SAVE_FIELDS.

Python 3.9, standard library only. Nothing here is Mac-only: the small copies are arrange.py's (sips on a Mac,
pictures.py's Pillow on a PC), the lock is this_computer.try_lock, and the page's words name no Mac thing.
"""
import argparse
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
SHORT_SONG_FROM_TOP = 40  # decision 8: a song shorter than this (seconds) starts at the top (her code), not where it picks up
SOUND_BESIDE_OUTSIDE = False   # decision 4: a screen recording in a Photos folder outside Your Content (an export folder
                        # the kit only points to) has its sound made in <kit>/Music, never in their folder. True: beside it
PLAN_WORDS = "nicole"   # decision 5: the Plan line in the result box is hers ("Plan: 14 photos, 15.2 seconds, every cut on
                        # the beat at about 85 beats a minute, starting the song at the top."); "reel": reel.py's longer line
MAKE_LIMIT = 600        # hers: a reel may take ten minutes to make, then it is stopped and the page says so
JOB_GRACE = 30          # seconds past MAKE_LIMIT before a job is told as too long even while its lock is held
SONG_EVERY_MS = 3000    # hers: the song list is looked at again every 3 seconds
JOB_EVERY_MS = 700      # how often the page asks how Make my reel is going (ours: hers waited on one long request)
JOB_BOOT = 20.0         # seconds a job may take to start before "queued" means it never did

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
SOUND_NAME = re.compile(r"(.+) sound(?: ([2-9]))?")    # "<name> sound", or "<name> sound 2" beside a damaged one (ours)
SOUND_SPARES = 8        # "<name> sound 2" to "<name> sound 9": the most made beside sounds that couldn't be read
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
MOMENT_ID = re.compile(r"[mu][0-9]{1,4}-[0-9a-f]{6}")  # hers: m<k>-<6 hex> (Claude's), u<k>-<6 hex> (theirs)
# step 1, the footage (stage b2 and b3)
FOOTAGE = "Footage"                    # hers: <shoot>/Footage, the behind-the-scenes videos they drag in
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
ADD_MIN, ADD_MAX = 1.0, 8.0            # hers: Use this moment's length, 1 to 8 seconds
MAX_CLIPS = 12                         # hers: a style uses at most 12 clips (Moment first 1, Bookends 2)
STYLE_MAX = {"first": 1, "reveal": 12, "backforth": 12, "bookends": 2}     # hers: STYLE_PICK
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
             "/reel-strip", "/reel-moment-still")
POST_PATHS = ("/reel-save", "/reel-open", "/reel-make", "/reel-capcut", "/reel-moment")

# ---------- the words: hers, word for word (reel-maker.html and server.py, handoff v19) ----------
# Each is shown exactly as written here. "_html" words carry her own <b>; {short}, {n}, {k}, {max} are filled in.
# The words for the steps still to come are here already, so every word on the page lives in this one table.
# The few lines that are ours, not hers, are in OUR_WORDS below, each with its reason.
WORDS = {
    # the top of the page
    "page_title": "Make my reel",
    "reel_of": "{short} reel",
    "back_kit": "Back to the post kit",
    "eyebrow": "Reel",
    "h1": "Your reel",
    "lede_html": "A few quick steps, then press <b>Make my reel</b> and it's cut on the beat in CapCut, ready for your look.",
    "reach": "I can't reach this shoot right now. Check that the photo drive is plugged in, then reload.",

    # step 1 (stage b): behind-the-scenes footage
    "foot_h2": "Behind-the-scenes footage?",
    "foot_say": "Do you want this reel to include behind-the-scenes video from the shoot, or just your photos?",
    "foot_bts_b": "Add behind-the-scenes footage",
    "foot_bts_s": "Clips from the shoot, mixed with your finished photos.",
    "foot_photos_b": "Just photos",
    "foot_photos_s": "Your finished photos, cut on the beat.",
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
    "paste_say": "Once your footage is in, copy this into the chat so I can look through it:",
    "paste_plain": "Look through my footage",
    "paste_for": "Look through my footage for {short}",
    "paste_notes": " and follow my notes",
    "copy": "Copy",
    "copied": "Copied",
    "ask_label_html": "<b>Want to direct the reel?</b> Optional. Tell me the moments you want and how you'd like the reel to go, and I'll follow it through your footage.",
    "ask_ex1": "For example: “Find the first kiss. Start with getting ready in the morning, then the ceremony, and end with the sparkler exit.”",
    "ask_ex2": "Another example: “Find the footage of me walking into the frame with my camera.”",
    "ask_placeholder": "Optional: the moments you want, and how you'd like it to go",
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
    "foot_need_h3": "One more thing: behind-the-scenes footage?",
    "foot_need_html": "Choose <b>Add behind-the-scenes footage</b> or <b>Just photos</b> in step 1.",
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
    "order_h2": "Put your photos in order",
    "order_say": "Your assistant can choose the order for you, or you can drag and drop them into the order you'd like. Whichever you pick, the other one is kept, so you can switch back and forth to compare.",
    "claude_b": "Let my assistant choose",
    "claude_rec": "Recommended for behind-the-scenes reels",
    "claude_words": "Your assistant picks the strongest photos and orders them so each one flows into the next.",
    "claude_words_bts": "Your assistant picks your strongest photos, the ones with the most feeling and the best story, and fits your behind-the-scenes moments in between.",
    "not_picked_html": "Your assistant hasn't picked for this shoot yet. In the chat, say <b>“pick my reel photos for {short}”</b> and they'll show up here.",
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
    "song_recording": "Screen recording · I'll use its sound",
    "song_song": "Song",
    "song_in_music": "in your Music folder",
    "song_in_photos": "in your Photos folder",
    "no_song_b": "No song",
    "no_song_s": "I'll add music in Instagram when I post",
    "got_it": "Got it: {name}.",
    "opening_music": "Opening your Music folder in Finder...",
    "music_open": "Your Music folder is open in Finder. Drag your song in, and it will show up here by itself.",
    "cant_open": "Could not open the folder. Ask your assistant to open it.",

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
    "vibe_mixed_s": "Some quick, some long, changing where the music turns over.",
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

# Lines that are ours, not hers, each with why (they go on the "Tell Nicole" list):
OUR_WORDS = {
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
    "coming_small": "still copying in",
    "coming": "{name} is still being copied into your Footage folder. It shows up here when it's done.",
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
    """Every photo number the record mentions: the saved orders, and (from the footage stage) Claude's footage
    order and the photos the moments are matched to."""
    out = set()
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
    if rec.get("stamp") and rec.get("stamp") != stamp and isinstance(rec.get("saved"), dict):
        # the list was re-made: find each photo again by its file name
        n_of = {}
        for x in rows:
            n_of.setdefault(arrange.photo_name(x), x["n"])
        old = rec.get("names") or {}
        s = rec["saved"]
        for key in ("picks", "mine_picks"):
            if isinstance(s.get(key), list):
                s[key] = _refind(s[key], old, n_of)
        if isinstance(rec.get("claude_bts"), list):
            rec["claude_bts"] = _refind(rec["claude_bts"], old, n_of)
        for m in rec.get("moments") or []:
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
    rec["names"] = _names(rec.get("saved") if isinstance(rec.get("saved"), dict) else {},
                          {x["n"]: arrange.photo_name(x) for x in rows}, rec)
    rec["stamp"] = stamp


def state(kit):
    """Everything the page draws from. No path and no file name is in it. None when the numbered list can't be
    read right now."""
    with arrange.locked(lock_path(kit)):
        rec, rows, stamp = sync(kit)
    if not rows:
        return None
    rec_kit = kit_mod.load_rec(kit)
    photos, made = arrange.page_photos(kit, rec_kit, rows)
    on_sheet = {x["n"] for x in rows}
    saved = rec.get("saved") if isinstance(rec.get("saved"), dict) else None
    return {
        "ok": True,
        "short": short_name(kit.name),
        # the kit page is built on every request from the kit's record (v19 stage d), so every kit has one
        "kit_page": kit_mod.rec_path(kit).is_file(),
        "stamp": stamp, "rev": int(rec.get("rev") or 0), "total": len(rows),
        "photos": photos, "previews": {"made": made, "of": len(rows)},
        "claude": claude_order(kit, rec_kit, on_sheet),
        "claude_earlier": earlier_orders(rec_kit, on_sheet),
        "saved": _for_page(saved, on_sheet),
        "max": MAX_PICKS,
        "songs": songs_for_page(kit, rec_kit),
        "music": music_dir(kit).is_dir() and music_ok(kit),
        "job": job_for_page(kit),
        # step 1: the moments (their videos by key) and Claude's footage order; the videos themselves come from
        # /reel-footage, which the page asks only once they chose footage (asking starts the previews)
        "moments": moments_for_page(kit, rec, on_sheet),
        "claude_bts": _bts_of(rec, on_sheet),
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


def current_picks(kit):
    """The order Make my reel uses when it is not handed one by the page, as reel.py reads it ("19,4,10+,14-"):
    their own when they chose "I'll drag them in myself", otherwise Claude's newest, with the Longer / Quicker
    they set on the same photos (her followClaude). "" when there is nothing yet."""
    st = state(kit)
    if st is None:
        return ""
    return ",".join(f"{x['n']}{x.get('h') or ''}" for x in _order_used(st["saved"], st["claude"], st.get("claude_earlier")))


def order_for_kit_page(kit, rows=None, rec_kit=None):
    """The reel's photos in the order Make my reel would use (_order_used), for the post kit's Reel card (her
    kit_summary's reel_order). Reads only: nothing is saved and no lock is taken, so showing the kit page never
    changes the record. A record saved against an earlier numbered list is read the way sync() would bring it in
    line (each photo found again by its file name), in memory only. [] when the numbered list can't be read."""
    rows = arrange.sheet_rows(kit) if rows is None else rows
    if not rows:
        return []
    rec = load(kit)
    saved = rec.get("saved") if isinstance(rec.get("saved"), dict) else None
    stamp = arrange.sheet_stamp(kit)
    if saved and rec.get("stamp") and stamp and rec.get("stamp") != stamp:
        n_of = {}
        for x in rows:
            n_of.setdefault(arrange.photo_name(x), x["n"])
        saved = dict(saved)
        for key in ("picks", "mine_picks"):
            if isinstance(saved.get(key), list):
                saved[key] = _refind(saved[key], rec.get("names") or {}, n_of)
    on_sheet = {x["n"] for x in rows}
    rec_kit = rec_kit if rec_kit is not None else kit_mod.load_rec(kit)
    return _order_used(_for_page(saved, on_sheet), claude_order(kit, rec_kit, on_sheet), earlier_orders(rec_kit, on_sheet))


def _when_of(iso):
    try:
        return datetime.fromisoformat(str(iso)).timestamp()
    except (TypeError, ValueError):
        return 0.0


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


def sound_for(kit, s, deadline=None):
    """The sound of a screen recording (hers: sound_of), made ONCE and never written over: "<name> sound.m4a"
    beside the recording (a PC with no ffmpeg makes "<name> sound.wav"), or, when the recording sits in a Photos
    folder outside Your Content (an export folder the kit only points to), in the kit's own Music folder
    (decision 4), since their folder is never written to. A sound already there is used when it can be read; one
    that can't (cut off part way) is left exactly as it is and a new one is made beside it, "<name> sound 2.m4a".
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
        good = next((h for h in have if _sound_ok(h)), None)
        if good is not None:
            return good, None
        if have:
            arrange.log(f"reel page: a sound beside a recording couldn't be read, so it is left as it is: {have[0].name}")
            continue
        out = folder / names[0]                    # the first name with nothing under it
        break
    if out is None:
        return None, WORDS["no_sound"]
    if this_computer.WINDOWS and this_computer.path_too_long(out):      # unproven on a real PC
        return None, WORDS["no_sound"]
    left = (deadline - time.time()) if deadline else MAKE_LIMIT
    if left <= 1:
        return None, WORDS["too_long"]
    try:
        got, how = _reel_module("sound").extract_audio(video, out, timeout=left)
    except Exception as e:  # noqa: BLE001
        arrange.log(f"reel page: the sound of a recording couldn't be taken: {e.__class__.__name__}: {str(e)[:200]}")
        return None, WORDS["no_sound"]
    if not got:
        arrange.log(f"reel page: the sound of a recording couldn't be taken: {str(how)[:200]}")
        return None, WORDS["too_long"] if "took too long" in str(how) else WORDS["no_sound"]
    return Path(got), None


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


def _facts(kit, p, key):
    """The video's facts (video.facts, from its header): from this process's memory, else the kit's facts.json,
    else read and kept there. {"refused": plain words} for a file that is not a video it can read."""
    with _FACTS_LOCK:
        if key in _FACTS:
            return _FACTS[key]
    f = foot_work(kit) / "facts.json"
    kept = _read(f) or {}
    got = kept.get(key) if isinstance(kept.get(key), dict) else None
    if got is None:
        v = _video()
        try:
            got = v.facts(p)
        except v.NotAVideo as e:
            got = {"refused": str(e)}
        except OSError:
            return {"refused": WORDS["video_not_here"]}
        if got.get("refused") and _just_changed(p):
            return got                     # maybe still coming in: asked again on the next look, never kept
        try:
            with arrange.locked(foot_work(kit) / "facts.lock"):
                kept = _read(f) or {}
                kept[key] = got
                arrange.write_whole(f, kept)
        except (OSError, arrange.Busy):
            pass
    with _FACTS_LOCK:
        _FACTS[key] = got
    return got


def _just_changed(p):
    try:
        return time.time() - Path(p).stat().st_mtime < COMING_RECENT
    except OSError:
        return False


def list_videos(kit, coming=None):
    """The videos in <kit>/Footage, in name order (hers): [{key, name, path, size, facts}]. Hidden files, links
    and anything not a .mov, .mp4 or .m4v are left out. The path never leaves this computer's own side.
    A video still being copied in (its boxes run past the end of the file, and it changed in the last
    COMING_RECENT seconds) is left out too, its facts never read and nothing made for it: it goes in `coming`
    (a list, when given) as {name, size}, and comes in whole on a later look (v19 review, Nov 7: a copy in
    progress left a record for every size it passed through)."""
    d = footage_dir(kit)
    if not footage_ok(kit) or not d.is_dir():
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
        fx = _facts(kit, p, key)
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
                    "by": "you" if m.get("by") == "you" else "", "set": bool(m.get("set"))})
    return out


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
    if allowed is None or set(body) - {"kit", "do"} - allowed:
        return _bad()
    if do != "add" and (not isinstance(body.get("id"), str) or not MOMENT_ID.fullmatch(body["id"])):
        return _bad()
    vids = list_videos(kit)
    still = None
    with arrange.locked(lock_path(kit)):
        rec, rows, stamp = sync(kit)
        if not rows:
            return _bad(NOT_READY, 404)
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
            start = max(0.0, min(start, length - 0.5))
            if s_in is not None and e_in is None and end - start < MOMENT_MIN:
                end = start + (float(m["end"]) - float(m["start"]))      # a new start keeps the length it had
            end = max(start + MOMENT_MIN, min(end, start + MOMENT_MAX, length))
            m.update(start=round(start, 2), end=round(end, 2), set=True)
            if m.get("by") == "you":
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


def footage_for_page(kit):
    """GET /reel-footage: hers (/footage with /reel's moments): the videos, the moments and Claude's footage order.
    Asking starts any preview not made yet, one at a time."""
    coming = []
    vids = list_videos(kit, coming)
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
    return [m["id"] for m in pool[:2]]           # Back and forth starts with 2 clips (Nicole, Nov 6)


def chosen_clips(saved, ms):
    """Hers (the page's chosen()): the clips selected for the saved style, in card order."""
    style = saved.get("style") if saved.get("style") in STYLES else "first"
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
    if style not in STYLES:
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
                        "moment": m["id"]})
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
        if k not in STYLES or not isinstance(ids, list) or len(ids) > 12:
            raise Refused("sel")
        if any(not isinstance(x, str) or not MOMENT_ID.fullmatch(x) for x in ids):
            raise Refused("sel")
        out[k] = list(ids)
    return out


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
    "style": lambda v, kit, ons: v if v in STYLES else _no("style"),
    "sel": lambda v, kit, ons: _sel(v),
    "ask": lambda v, kit, ons: _text(v, 600),
    "feel": lambda v, kit, ons: _feel(v),
}


def _no(what):
    raise Refused(what)


def _bad(words=NOT_UNDERSTOOD, code=400, **more):
    d = {"ok": False, "words": words}
    d.update(more)
    return code, d


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
    if set(body) - {"kit", "stamp", "base", "page", "saved"}:
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
        longest = len(claude_order(kit, None, on_sheet))
        for key in ("picks", "mine_picks"):
            if isinstance(clean.get(key), list) and len(clean[key]) > max(MAX_PICKS, longest, len(stored.get(key) or [])):
                return _bad(OUR_WORDS["too_many"], 400, why="many")
        rev = int(rec.get("rev") or 0)
        if all(stored.get(k) == v for k, v in clean.items()):
            return 200, {"ok": True, "rev": rev}      # what is stored already: nothing to write
        src = rec.get("from") if isinstance(rec.get("from"), dict) else {}
        own = src.get("page") == page and src.get("base") == base
        if not (REV_CHECK and base != rev and not own):
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
    if state in ("queued", "running"):
        began = float(j.get("t0") or 0)
        if began and time.time() - began > MAKE_LIMIT + JOB_GRACE:
            # past its time, whatever its lock says (v19 review: a hung job held its lock, and the page spun forever)
            state, problem = "problem", WORDS["too_long"]
        elif not job_running(kit) and (state == "running" or j.get("pid") or time.time() - float(j.get("t") or 0) > JOB_BOOT):
            state, problem = "problem", OUR_WORDS["interrupted"]
        if state == "problem":
            made = _made_by(kit, j["id"])
            if made:              # CapCut has it: never say nothing was made (rule 7)
                problem = OUR_WORDS["interrupted_made"].replace("{project}", made)
    words = [w for w in (j.get("words") or []) if isinstance(w, str)]
    out = {"id": j["id"], "state": state, "dry": bool(j.get("dry")), "project": j.get("project") if state == "done" else None,
           "words": words if state == "done" else [], "problem": problem if state == "problem" else None,
           "short_song": bool(j.get("short_song")) and state == "problem"}
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


def capcut_say(st):
    """The line under "It's in CapCut": hers when the reel is in CapCut's list (or a Mac's open CapCut adds it by
    itself); else ours, saying what to do (v19 review)."""
    if st.get("listed") or st.get("left_to_capcut") or ("listed" not in st and "waiting" not in st):
        return WORDS["open_capcut_say"]
    return _capcut_words("waiting" if st.get("waiting") else "not_listed")


def _picks_text(lst):
    return ",".join(f"{x['n']}{x['h']}" for x in lst)


def start_make(body):
    """POST /reel-make: {kit, stamp, picks: [{n, h}], song: an id, "" for No song, vibe, test}. Checked the way a
    save is; then the job is written down and its process started. (status, answer)."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    if set(body) - {"kit", "stamp", "picks", "song", "vibe", "test", "footage", "style", "clips"}:
        return _bad()
    rows = arrange.sheet_rows(kit)
    if not rows:
        return _bad(NOT_READY, 404)
    if body.get("stamp") != arrange.sheet_stamp(kit):
        return _bad(OUR_WORDS["photos_changed"], 409, why="photos")
    on_sheet = {x["n"] for x in rows}
    try:
        picks = _picks(body.get("picks"), on_sheet)
    except Refused:
        return _bad()
    if not picks:
        return _bad(WORDS["pick_photos"])
    if len(picks) > MAX_PICKS:
        return _bad(OUR_WORDS["too_many"], 400, why="many")
    vibe = body.get("vibe")
    if vibe not in VIBES:
        return _bad(WORDS["pick_vibe"])
    song = body.get("song")
    if song is None:
        return _bad(re.sub(r"<[^>]+>", "", WORDS["need_song_html"]), 400, why="song")
    if not isinstance(song, str) or (song and not SONG_ID.fullmatch(song)):
        return _bad()
    if song and song not in song_ids(kit):
        return _bad(WORDS["song_gone"], 400, why="song")
    test = body.get("test", False)
    if type(test) is not bool:
        return _bad()
    footage, style, clips = body.get("footage", False), body.get("style", "first"), body.get("clips")
    if type(footage) is not bool or style not in STYLES:
        return _bad()
    if clips is not None and (not isinstance(clips, list) or len(clips) > MAX_CLIPS
                              or any(not isinstance(x, str) or not MOMENT_ID.fullmatch(x) for x in clips)):
        return _bad()
    if footage:
        with arrange.locked(lock_path(kit)):
            ms = moments_of(load(kit))
        if not ms:
            return _bad(WORDS["no_moments"].replace("{_}", ""), 400, why="footage")
    with _JOB_ROUTE:
        j = read_job(kit) or {}
        if job_running(kit) or (j.get("state") == "queued" and not j.get("pid") and time.time() - float(j.get("t") or 0) < JOB_BOOT):
            return 409, {"ok": False, "words": OUR_WORDS["already_making"], "why": "making", "job": job_for_page(kit)}
        jid = os.urandom(6).hex()
        write_job(kit, {"id": jid, "state": "queued", "t": time.time(), "dry": test,
                        "ask": {"picks": _picks_text(picks), "song": song, "vibe": vibe, "dry": test,
                                "stamp": body.get("stamp"), "footage": style if footage else None,
                                "clips": list(clips) if footage and clips is not None else None}})
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


def _make(kit, ask, jid, t0):
    """The work of one job. Returns what goes in the job record: {state, words, project, problem, short_song}.
    Everything, from the recording's sound to reel.py, is held to one deadline: t0 + MAKE_LIMIT."""
    deadline = t0 + MAKE_LIMIT
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
    made = page_rec.get("made") or []
    style = ask.get("footage") if ask.get("footage") in STYLES else None
    # hers: the next reel of the same photos, vibe and footage style is the next mix
    variation = sum(1 for m in made if isinstance(m, dict) and m.get("picks") == picks and m.get("vibe") == ask["vibe"]
                    and m.get("footage") == style)
    # The numbers on the page are the kit's numbered list (.kit/sheet.json); reel.py is handed that same list in
    # its working folder, so a photo exported since can never shift a number to another photo.
    rows = arrange.sheet_rows(kit)
    if not rows or arrange.sheet_stamp(kit) != ask.get("stamp"):
        return {"state": "problem", "problem": OUR_WORDS["photos_changed"]}
    listing = [{"n": x["n"], "file": str(photos / arrange.photo_name(x)), "w": x.get("w") or 0, "h": x.get("h") or 0,
                "way": x.get("way") or ""} for x in rows]
    work = reel.kit_workdir(kit) or reel.workdir(rec_kit.get("name") or short, str(photos))
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
    status = kit / ".kit" / JOB_STATUS
    arrange.write_whole(status, {"for": jid, "pending": True})     # reel.py keeps "for" when it writes what happened
    cmd = [sys.executable, str(kit_mod.REEL_PY), "make", "--folder", str(photos), "--shoot", rec_kit.get("name") or short,
           "--kit", str(kit), "--picks", tokens, "--vibe", ask["vibe"],
           *(["--clips", str(work / "clips.json")] if clip_list else []),
           *(["--capcut-song", ask["capcut_song"]] if ask.get("capcut_song") else ["--song", str(song) if song else "none"]),
           "--variation", str(variation), "--name", ask.get("name") or reel.kit_reel_name(kit.name, short), "--status", str(status)]
    if ask.get("hook"):
        cmd += ["--hook", ask["hook"]]          # Claude's make only (decision 15): words on the first photo, when they ask
    if song:
        secs = capcut.song_length(str(song)) or 99
        if secs < SHORT_SONG_FROM_TOP:
            cmd += ["--song-start", "0"]            # decision 8: her code starts a short song at the top
    if ask.get("dry"):
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
    dry = bool(ask.get("dry"))
    words = _her_lines(r_out, dry, st.get("plan"), known)
    project = st.get("project")
    if not dry and project:
        with arrange.locked(lock_path(kit)):
            rec = load(kit)
            rec.setdefault("made", []).append({"project": project, "picks": picks, "vibe": ask["vibe"], "footage": style,
                                               "clips": [c["moment"] for c in clip_list] if clip_list else None,
                                               "song": song_name, "song_id": ask.get("song") or "", "when": time.time()})
            save(kit, rec)
        try:                     # the kit's own record of its reel, through its command (kit.json is only theirs to write)
            k = subprocess.run([sys.executable, str(HERE / "kit.py"), "reel-made", str(kit), "--project", project, "--picks", picks],
                               capture_output=True, encoding="utf-8", errors="replace", timeout=60)
            if k.returncode != 0:
                arrange.log(f"reel page: kit.py reel-made said: {(k.stdout + k.stderr).strip()[-300:]}")
        except (OSError, subprocess.SubprocessError) as e:
            arrange.log(f"reel page: kit.py reel-made could not run: {e}")
    return {"state": "done", "words": words, "project": project, "capcut_say": None if dry else capcut_say(st)}


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
            j.update(state="problem", problem=WORDS["too_long"], t=time.time())
            made = _made_by(kit, jid)
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
        threading.Thread(target=_watchdog, args=(kit, jid, t0 + MAKE_LIMIT, finished), daemon=True).start()
        g = _hold_make_lock(t0 + MAKE_LIMIT)
        if g is None:
            j.update(state="problem", problem=WORDS["too_long"], t=time.time())
            write_job(kit, j)
            return 1
        try:
            j.update(state="running", t=time.time())
            write_job(kit, j)
            try:
                res = _make(kit, ask, jid, t0)
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


def open_music(body):
    """POST /reel-open {kit, what: "music" | "footage"}: makes <kit>/Music (or <kit>/Footage) if it isn't there,
    and opens it (hers: /music/open and /footage/open)."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    if set(body) - {"kit", "what"} or body.get("what") not in ("music", "footage"):
        return _bad()
    if body["what"] == "footage":
        return open_footage(kit)
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
            return arrange._send_page(handler, arrange_page.plain_page(cant[1] + " Tell Claude and it'll sort it out."))
        arrange.start_previews(kit)
    arrange._send_page(handler, page_html(kit.name, st["short"], st["kit_page"]))


def _get_state(handler, q):
    if (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 403)
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_json(handler, {"ok": False, "words": CANT_FIND}, 404)
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
        return handler.send_error(404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        arrange.log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            if path in ("/reel-font", "/reel-video", "/reel-strip", "/reel-moment-still"):
                handler.send_error(404)
            elif path.endswith(".html"):
                import arrange_page
                arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
            else:
                arrange._send_json(handler, {"ok": False, "words": OUR_WORDS["cant_reach"]}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def _json_body(handler, path):
    """The body of a JSON POST as a dict, after arrange's guard (host, Origin, type, length). None when it was
    refused (and answered)."""
    try:
        handler.connection.settimeout(arrange.BODY_WAIT)
    except (OSError, AttributeError):
        pass
    bad = arrange.guard(handler, "application/json", POST_CAP, path)
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
        route = {"/reel-save": save_from_page, "/reel-make": start_make, "/reel-open": open_music,
                 "/reel-capcut": open_capcut_for_page, "/reel-moment": change_moments}.get(path)
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
.viewer .spin{border-color:rgba(0,0,0,.15);border-top-color:var(--coral-2);vertical-align:-2px}
.viewer{display:flex;gap:1.1rem;align-items:flex-start;border:1px solid var(--line);border-radius:16px;padding:1rem;margin:.8rem 0 0;background:var(--paper)}
.viewer video{width:250px;max-width:42vw;aspect-ratio:9/16;background:#111;border-radius:12px;display:block;flex:none;object-fit:contain}
.viewer video.wide{aspect-ratio:16/9;width:420px}
.vside{flex:1;min-width:0}
.vside h4{margin:0 0 .2rem;font:600 15px/1.3 var(--sans)}
.vside p{margin:0 0 .6rem;font-size:13.5px;color:var(--ink-2)}
.strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(54px,1fr));gap:5px;max-height:330px;overflow-y:auto;padding:2px;border-radius:10px}
.strip button{position:relative;border:0;padding:0;border-radius:6px;overflow:hidden;cursor:pointer;background:var(--sand-l);aspect-ratio:9/16;outline-offset:-2px}
.strip.wide button{aspect-ratio:16/9}
.strip img{width:100%;height:100%;object-fit:cover;display:block}
.strip span{position:absolute;left:0;right:0;bottom:0;font:600 9.5px/1.5 var(--sans);color:#fff;background:rgba(0,0,0,.45);text-align:center}
.strip button.now{outline:3px solid var(--coral)}
.strip button.inm::after{content:"";position:absolute;top:3px;right:3px;width:8px;height:8px;border-radius:50%;background:var(--coral-2);box-shadow:0 0 0 1.5px #fff}
.userow{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;margin-top:.8rem}
.userow .at{font-size:13.5px;color:var(--ink-2)}
.mom .play{position:absolute;left:8px;top:8px;width:34px;height:34px;border-radius:50%;background:rgba(0,0,0,.55);color:#fff;display:grid;place-items:center;font-size:13px;cursor:pointer}
.mom .play:hover{background:var(--coral-2)}
.mom .len{display:flex;align-items:center;gap:.35rem;margin-top:.45rem;font-size:13px}
.mom .len button{width:28px;height:26px;border-radius:8px;border:1px solid var(--line);background:#fff;font:600 15px/1 var(--sans);cursor:pointer;color:var(--ink)}
.mom .len button:hover{border-color:var(--coral)}
.mom .len b{min-width:3.6em;text-align:center;font-weight:600}
.mom.editing{border-color:var(--coral-2);box-shadow:0 0 0 1px var(--coral-2) inset}
.userow .btn.small[hidden]{display:none}
.mom .rm{position:absolute;right:8px;bottom:8px;font:600 12px/1 var(--sans);color:var(--ink-2);text-decoration:underline;cursor:pointer}
.mom .yours{display:inline-block;font:600 10px/1 var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--coral-2);background:var(--coral-l);border-radius:999px;padding:.3em .55em;margin-bottom:.3rem}
@media(max-width:620px){.viewer{flex-direction:column}.viewer video{width:100%;max-width:none}}
.vid{display:flex;align-items:center;gap:.7rem;border:1px solid var(--line);border-radius:12px;padding:.55rem .8rem;font-size:14.5px}
.vid .ic{width:30px;height:30px;border-radius:9px;background:var(--coral-l);color:var(--coral-2);display:grid;place-items:center;font-size:13px;flex:none}
.vid small{color:var(--ink-2);margin-left:auto;white-space:nowrap}
.insight{background:#FFF8EC;border:1px solid #F3E3C3;border-radius:14px;padding:.85rem 1rem;margin:1rem 0 0;font-size:14px}
.insight b{font-weight:600}.insight p{margin:.35rem 0 0}
.paste{margin:1rem 0 0;font-size:14.5px}.paste p{margin:0 0 .45rem}
.paste .line{display:flex;align-items:center;gap:.7rem;justify-content:space-between;border:1.5px dashed var(--coral);border-radius:14px;padding:.6rem .7rem .6rem 1rem;max-width:520px;background:var(--paper)}
.paste .line span{font:500 17px/1.35 var(--sans)}
.mh{font:600 16px/1.2 var(--sans);margin:1.3rem 0 .2rem}
.moments{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,190px));gap:.8rem}
.mom{position:relative;border:1.5px solid var(--line);border-radius:14px;overflow:hidden;background:var(--paper);cursor:default;text-align:left;padding:0;font:inherit;color:inherit}
.mom .th{display:flex;aspect-ratio:9/16;background:#111;position:relative}
.mom .th video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#111}
.mom .play{border:0;padding:0;z-index:2}
.mom .play.on{background:var(--coral-2)}
.mom .th{cursor:pointer}
.mom .len{display:flex;align-items:center;justify-content:space-between;gap:.4rem;margin-top:.55rem}
.mom .len > span{display:flex;align-items:center;gap:.3rem}
.mom .tx .len b{display:inline-block;min-width:3.4em;text-align:center;font-size:13.5px}
.mom .len button.rm{width:auto;height:auto;border:0;background:none;padding:.2rem 0;font:600 12.5px/1 var(--sans);color:var(--ink-2);text-decoration:underline;cursor:pointer}
.mom .len button.rm:hover{color:var(--coral-2)}
.mom .usebtn{display:block;width:100%;margin-top:.55rem;padding:.55rem .6rem;border-radius:10px;border:1.5px solid var(--line);background:#fff;font:600 13.5px/1.1 var(--sans);color:var(--ink);cursor:pointer}
.mom .usebtn:hover{border-color:var(--coral)}
.mom .usebtn[disabled]{cursor:default;color:var(--ink-2);background:var(--sand-l);border-color:transparent;font-weight:500}
.mom.sel{border-color:var(--coral-2);box-shadow:0 0 0 1.5px var(--coral-2) inset}
.mom.sel .usebtn{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.mom .badge{position:absolute;right:8px;top:8px;z-index:2;font:700 12px/1 var(--sans);background:var(--coral-2);color:#fff;border-radius:999px;padding:.45em .7em}
.undo-note{display:flex;gap:.7rem;align-items:center;font-size:14px;background:var(--ink);color:#fff;border-radius:12px;padding:.55rem .9rem;margin:.6rem 0 0;width:max-content;max-width:100%}
.undo-note button{background:none;border:0;color:#FFB59B;font:600 14px var(--sans);text-decoration:underline;cursor:pointer;padding:0}
.mom .th img{height:100%;object-fit:cover;flex:1 1 0;min-width:0}
.mom .th img.ph{flex:0 0 38%;border-left:3px solid #fff}
.mom .tx{padding:.55rem .7rem .65rem;font-size:13.5px;line-height:1.35}
.mom .tx b{display:block;font-weight:600;font-size:14px}
.mom .tx small{color:var(--ink-2)}
.mom .kp{position:absolute;top:8px;right:8px;font:600 11px/1 var(--sans);border-radius:999px;padding:.4em .7em;background:var(--long);color:#fff}
.mom.off{opacity:.45}.mom.off .kp{background:var(--ink-2)}
.mom.off .kp::after{content:""}
.lb{position:fixed;inset:0;background:rgba(20,22,30,.92);display:none;place-items:center;z-index:50;cursor:zoom-out;padding:16px}
.lb.on{display:grid}.lb img{max-width:92vw;max-height:92vh;border-radius:12px}
@media(max-width:560px){#reel{grid-template-columns:repeat(auto-fill,minmax(88px,1fr))}.opt{min-width:0;max-width:none}}
"""

FONT_CSS = "".join(
    "@font-face{font-family:'%s';src:url('/reel-font?f=%s') format('truetype');font-weight:%d;font-style:%s;font-display:swap}"
    % (fam, key, wt, st) for fam, wt, st, key in FACES)
# The page itself takes its font from look.py (/look-font, answered by the posting server). FONT_CSS (with Fraunces)
# is kept for kit pages saved before Nov 7 that still ask for it, and /reel-font answers exactly as before.

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

# Her steps, in her order (BUILD.md section 5: "This order is final"). Each is (her section's id, the
# function that writes it, or None while that step is not built yet). A step left out is simply not on the page.
def pc_footage():
    """True where the footage look and the stills can't run (a PC: video.py's named gap)."""
    try:
        return not _video().avfoundation_here()
    except Exception:  # noqa: BLE001
        return this_computer.WINDOWS


def _footage_section(w, num):
    """Her step 1, "Behind-the-scenes footage?" (reel-maker.html #step0), with everything under it: Add my
    footage, the videos, Good to know, the line to copy, Want to direct the reel?, How should it feel?, the moment
    cards, and the player with its strip. On a PC (pc_footage()), where Claude can't look through footage and
    there are no stills: Good to know (about how long the look takes) and the line to copy are left out, with
    this_computer.NO_LOOK_PC in place of the line (decision 26; v19 review, Nov 7). A Mac: exactly hers."""
    e = html.escape
    pc = pc_footage()
    feels = "".join("<button type='button' data-f='" + f + "'>" + e(w["feel_" + f]) + "</button>" for f in FEELS)
    return (
        "<section class='step' id='step0'>"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["foot_h2"]) + "</h2>"
        "<p class='say'>" + e(w["foot_say"]) + "</p>"
        "<div class='choice'>"
        "<button class='opt' id='modeBts' type='button'><b>" + e(w["foot_bts_b"]) + "</b><span>" + e(w["foot_bts_s"]) + "</span></button>"
        "<button class='opt' id='modePhotos' type='button'><b>" + e(w["foot_photos_b"]) + "</b><span>" + e(w["foot_photos_s"]) + "</span></button>"
        "</div>"
        "<div id='btsBox' hidden>"
        "<p class='say'>" + w["foot_say2_html"] + "</p>"
        "<button class='btn main' id='addFootage' type='button'>" + e(w["add_footage"]) + "</button>"
        "<p class='waiting' id='footWaiting'></p>"
        "<div class='vlist' id='vlist'></div>"
        "<div class='insight'" + (" hidden" if pc else "") + "><b>" + e(w["insight_b"]) + "</b><p id='insightWords'>" + e(w["insight_words"]) + "</p>"
        "<p>" + w["quick_fix_html"] + "</p></div>"
        "<div class='paste' id='pasteBox'><p id='pasteSay'>" + e(this_computer.NO_LOOK_PC if pc else w["paste_say"]) + "</p>"
        "<div class='line'" + (" hidden" if pc else "") + "><span id='pasteWords'>" + e(w["paste_plain"]) + "</span>"
        "<button class='btn' id='copyLine' type='button'>" + e(w["copy"]) + "</button></div>"
        "<div class='ask'><label for='askIn'>" + w["ask_label_html"]
        + "<span class='ex'>" + e(w["ask_ex1"]) + "</span><span class='ex'>" + e(w["ask_ex2"]) + "</span></label>"
        "<textarea id='askIn' rows='3' maxlength='600' placeholder='" + e(w["ask_placeholder"], quote=True) + "'></textarea>"
        "<div class='feel' id='feelRow'><b>" + e(w["feel_b"]) + "</b>" + feels
        + "<button type='button' data-f='own' id='feelOwnBtn'>" + e(w["feel_own"]) + "</button>"
        "<input id='feelOwn' maxlength='40' placeholder='" + e(w["feel_placeholder"], quote=True) + "' hidden>"
        "<small>" + w["feel_small_html"] + "</small></div></div></div>"
        "<h3 class='mh'>" + e(w["clips_h3"]) + "</h3>"
        "<p class='say' id='momentsSay'>" + e(w["moments_first"]) + "</p>"
        "<div class='moments' id='moments'></div>"
        "<div id='undoNote'></div>"
        "<h3 class='mh'>" + e(w["watch_h3"]) + "</h3>"
        "<p class='say'>" + (this_computer.WATCH_PC_HTML if pc else w["watch_say_html"]) + "</p>"
        "<div id='viewers'></div>"
        "</div></section>")


def _style_section(w, num):
    """Her step 4, "What style of behind the scenes is this?" (#stepStyle), shown only with footage."""
    e = html.escape
    cards = "".join("<button class='opt' type='button' data-style='" + st + "'><b>" + e(w["style_%s_b" % st]) + "</b>"
                    "<span>" + e(w["style_%s_s" % st]) + "</span></button>" for st in STYLES)
    return (
        "<section class='step' id='stepStyle' hidden>"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["style_h2"]) + "</h2>"
        "<p class='say'>" + e(w["style_say"]) + "</p>"
        "<div class='vibes' id='styles'>" + cards + "</div>"
        "</section>")


def _order_section(w, num):
    e = html.escape
    return (
        "<section class='step' id='step1'>"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["order_h2"]) + "</h2>"
        "<p class='say'>" + e(w["order_say"]) + "</p>"
        "<div class='choice'>"
        "<button class='opt' id='useClaude' type='button'><b>" + e(w["claude_b"])
        + "<span class='rec' id='claudeRec' hidden>" + e(w["claude_rec"]) + "</span></b>"
        "<span id='claudeWords'>" + e(w["claude_words"]) + "</span></button>"
        "<button class='opt' id='useMine' type='button'><b>" + e(w["mine_b"]) + "</b><span>" + e(w["mine_words"]) + "</span></button>"
        "</div>"
        "<div class='tip'><div><p>" + w["tip_html"] + "</p>"
        "<div class='legend'><span><i style='background:var(--long)'></i>" + e(w["legend_long"]) + "</span>"
        "<span><i style='background:var(--quick)'></i>" + e(w["legend_quick"]) + "</span></div></div></div>"
        "<div class='tools'><button class='btn small' id='undoBtn' type='button' disabled>" + e(w["undo"]) + "</button>"
        "<span class='tools-say' id='undoSay'></span><span class='notice' id='notice'></span></div>"
        "<div class='reelwrap' id='reelwrap'><div id='reel'></div></div>"
        "<div class='count' id='count'></div>"
        "<div class='count warn limit' id='limit'>" + e(OUR_WORDS["too_many"]) + "</div>"
        "<details class='all' id='allBox'><summary>" + e(w["all_summary"]) + "</summary><div id='all'></div></details>"
        "</section>")


def _song_section(w, num):
    e = html.escape
    return (
        "<section class='step' id='step3'>"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["song_h2"]) + "</h2>"
        "<p class='say'>" + e(w["song_say1"]) + "</p>"
        "<p class='say'>" + w["song_say2_html"] + "</p>"
        "<button class='btn main' id='addMusic' type='button'>" + e(w["add_music"]) + "</button>"
        "<p class='waiting' id='waiting'></p>"
        "<div class='songs' id='songs'></div>"
        "<p class='note'>" + w["licence_html"] + "</p>"
        "</section>")


def _vibe_section(w, num):
    e = html.escape
    rec = default_vibe()
    cards = "".join(
        "<button class='opt' type='button' data-vibe='" + v + "'><b>" + e(w["vibe_%s_b" % v])
        + ("<span class='rec'>" + e(w["vibe_rec"]) + "</span>" if v == rec else "") + "</b>"
        "<span>" + e(w["vibe_%s_s" % v]) + "</span></button>" for v in VIBES)
    return (
        "<section class='step' id='step4'>"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["vibe_h2"]) + "</h2>"
        "<p class='say'>" + e(w["vibe_say"]) + "</p>"
        "<div class='vibes' id='vibes'>" + cards + "</div>"
        "</section>")


SECTIONS = [
    ("step0", _footage_section),  # 1. Behind-the-scenes footage?
    ("step1", _order_section),    # 2. Put your photos in order
    ("step3", _song_section),     # 3. Add your song
    ("stepStyle", _style_section),  # 4. What style of behind the scenes is this? (shown only with footage)
    ("step4", _vibe_section),     # 5. Pick the vibe
]


def _json_for_script(obj):
    """JSON that is safe inside a <script> element (no "</script>", no "<!--")."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def page_html(kit_name, short, kit_page=False):
    e = html.escape
    w = {k: pc_words(v) for k, v in WORDS.items()}
    if this_computer.WINDOWS:          # decision 26: her trim tip's Mac sentence, a PC's way
        w["quick_fix_html"] = w["quick_fix_html"].replace(
            "On a Mac, open it in QuickTime Player and choose Edit › Trim.", OUR_WORDS["trim_pc"])
    if pc_footage():                   # decision 26 (v19 review, Nov 7): no footage look on a PC, so no "I find"
        w["moments_first"] = w["moments_none"] = this_computer.MOMENTS_PC
        w["not_looked_h3"] = w["clips_need_h3"]
        w["not_looked_html"] = this_computer.NOT_LOOKED_PC_HTML
    title = w["reel_of"].replace("{short}", short)
    data = {"words": dict(w, **OUR_WORDS), "max": MAX_PICKS, "dragOut": DRAG_OUT, "undoSteps": UNDO_STEPS,
            "saveAfter": SAVE_AFTER_MS, "followEvery": FOLLOW_MS, "defaultVibe": default_vibe(),
            "songEvery": SONG_EVERY_MS, "jobEvery": JOB_EVERY_MS, "footEvery": FOOT_EVERY_MS, "feels": list(FEELS),
            "styles": list(STYLES), "styleMax": STYLE_MAX, "useSeconds": USE_SECONDS, "step": MOMENT_STEP,
            "undoNote": UNDO_NOTE_MS, "stripEvery": STRIP_EVERY}
    # her numbers as written (step 1 to 5, step 4 hidden until footage is chosen); the page renumbers them (hers)
    steps = "".join(fn(w, i) for i, fn in enumerate((fn for _, fn in SECTIONS if fn), 1))
    back_href = ("/content/" + quote(kit_name) + "/Post%20kit.html") if kit_page else "/home"
    back_words = w["back_kit"] if kit_page else OUR_WORDS["back_home"]
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + e(title) + "</title><style>" + look.head_css() + STYLE + OUR_CSS + "</style></head>"
        "<body data-kit='" + e(kit_name, quote=True) + "'>"
        "<div class='wrap'>"
        "<div class='bar'><a class='homelink' id='back' href='" + e(back_href, quote=True) + "'><span aria-hidden='true'>&larr;</span> "
        "<span id='backWords'>" + e(back_words) + "</span></a>" + brand.bar() + "</div>"
        "<header class='head'><span class='eyebrow'>" + e(w["eyebrow"]) + "</span>"
        "<h1 id='title'>" + e(title) + "<em>.</em></h1>"
        "<p class='lede'>" + w["lede_html"] + "</p></header>"
        + steps +
        "<div class='result' id='result'></div>"
        "</div>"
        "<div class='make'><div class='in'><div class='sum' id='sum'></div>"
        "<button class='btn main' id='makeBtn' type='button'>" + e(w["make"]) + "</button></div></div>"
        "<div class='lb' id='lb'><img id='lbimg' alt=''></div>"
        "<script type='application/json' id='reelData'>" + _json_for_script(data) + "</script>"
        "<script>" + DRAG_JS + "</script><script>" + MODEL_JS + "</script><script>" + CORE_JS + "</script>"
        "<script>" + ORDER_JS + "</script><script>" + SONG_JS + "</script><script>" + VIBE_JS + "</script>"
        "<script>" + FOOTAGE_JS + "</script><script>" + MAKE_JS + "</script><script>" + START_JS + "</script>"
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
  root.ReelModel = {at: at, copy: copy, insertAt: insertAt, takeOut: takeOut, sameNums: sameNums, landing: landing};
})(typeof window !== 'undefined' ? window : this);
"""

# The page's core: the record, saving (retried until it lands), following what changes elsewhere. Each step is
# a part: {fields(): what it saves, adopt(st, first): take a state, follow(st): a newer state arrived while idle}.
CORE_JS = r"""
(function(){
  'use strict';
  var DATA = JSON.parse(document.getElementById('reelData').textContent);
  var W = DATA.words, KIT = document.body.dataset.kit, Q = 'kit=' + encodeURIComponent(KIT);
  var $ = function(id){ return document.getElementById(id); };
  var esc = function(t){ return String(t).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
  var fill = function(t, o){ return String(t).replace(/\{(\w+)\}/g, function(m, k){ return o && o[k] != null ? o[k] : m; }); };
  // a name this page gives itself, new on every load and kept nowhere: it lets the Assistant tell this page's
  // own save (whose answer never arrived) from a save made in another window
  var PAGE = (Math.random().toString(36).slice(2, 12) + Date.now().toString(36)).replace(/[^a-z0-9]/g, '');
  var parts = [], S = null, rev = 0, stamp = '', blocked = false;
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
  function adopt(st, first){ S = st; rev = st.rev; stamp = st.stamp; parts.forEach(function(p){ if (p.adopt) p.adopt(st, first); }); }
  function save(){
    var out = $('result'); if (out && out.classList.contains('bad')) out.className = 'result';   // hers: they changed something, the old problem no longer applies
    if (blocked || !S) return;
    dirty = true;
    clearTimeout(timer);
    timer = setTimeout(send, DATA.saveAfter);
  }
  function body(){ return JSON.stringify({kit: KIT, stamp: stamp, base: rev, page: PAGE, saved: fields()}); }
  function send(){
    clearTimeout(timer); clearTimeout(retryT);
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
  function follow(){
    if (document.hidden || !idle()) return;
    var asked = rev;
    getState().then(function(st){
      if (!st || !st.ok || !idle() || rev !== asked) return;
      if (st.stamp !== stamp) { photosChanged(); return; }
      if (st.rev !== rev) { adopt(st, false); return; }          // saved in another window: shown as it is now
      S = st;
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
    // a POST of the page's own (arrange.guard checks it): {code, j}; a server that gave no answer throws
    post: function(url, obj){
      return fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(obj)})
        .then(function(r){ if (r.status >= 500) throw new Error('no answer'); return r.json().then(function(j){ return {code: r.status, j: j}; }); });
    },
    photoUrl: function(p, size){ return '/kit-photo?' + Q + '&n=' + p.n + '&size=' + size + '&v=' + encodeURIComponent(p.v || ''); },
    // her renumbering: only the steps that show are counted
    renumber: function(){ var k = 0; document.querySelectorAll('section.step').forEach(function(s){ if (!s.hidden) s.querySelector('.num').textContent = ++k; }); }};
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
  function notPicked(){ $('claudeWords').innerHTML = R.fill(W.not_picked_html, {short: esc(short)}); }
  function setMode(m){
    mine = m;
    $('useClaude').classList.toggle('on', !mine);
    $('useMine').classList.toggle('on', mine);
  }
  function limit(on){ $('limit').classList.toggle('on', !!on); }

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
      b.onclick = function(e){ if (e.detail === 0 && !(e.target.closest && e.target.closest('.zoom'))) toggle(p.n); };
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
  var target = null;
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
    var n = +t.dataset.n, at = M.at(reel, n), fromRow = t.classList.contains('tile');
    if (inside(wrapEl.getBoundingClientRect(), x, y)) {
      var tiles = Array.prototype.slice.call(reelEl.querySelectorAll('.tile'));
      var pos = M.landing(tiles.map(function(k){ return k.getBoundingClientRect(); }), x, y);
      if (at >= 0 && (pos === at || pos === at + 1)) return;          // where it already is
      if (at < 0 && reel.length >= MAX) { target = {kind: 'full'}; return; }
      target = {kind: 'in', pos: pos};
      showIns(pos, tiles, y);
      return;
    }
    if (R.data.dragOut && fromRow && inside(allEl.getBoundingClientRect(), x, y)) target = {kind: 'out'};
  }
  function drop(t){
    var n = +t.dataset.n, tg = target;
    target = null; clearIns();
    if (!tg) return;
    if (tg.kind === 'full') { limit(true); return; }
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
    cancel: function(){ target = null; clearIns(); },
    click: function(t){ if (t.classList.contains('pick')) toggle(+t.dataset.n); },
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
      return {picks: M.copy(reel), mine: mine, mine_picks: mineOrder ? M.copy(mineOrder) : null};
    },
    adopt: function(st, first){
      short = st.short;
      document.title = R.fill(W.reel_of, {short: short});
      $('title').innerHTML = esc(R.fill(W.reel_of, {short: short})) + '<em>.</em>';
      var back = $('back');
      if (st.kit_page) { back.href = '/content/' + encodeURIComponent(R.kit) + '/Post%20kit.html'; $('backWords').textContent = W.back_kit; }
      var rebuild = stampSeen !== st.stamp;
      stampSeen = st.stamp;
      photos = st.photos; byN = {}; photos.forEach(function(p){ byN[p.n] = p; });
      claude = known(st.claude);
      claudeBts = known(st.claude_bts);
      earlier = (st.claude_earlier || []).map(known);
      var saved = st.saved;
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

# Step 3, her "Add your song": the songs in the shoot's Music and Photos folders, by id; No song; a new file is
# picked by itself.
SONG_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc;
  var songs = [], seen = null, song = null;          // song: null (not picked yet), '' (No song), or a song's id
  R.song = function(){ return song; };
  R.songName = function(){ var s = songs.filter(function(x){ return x.id === song; })[0]; return s ? s.name : ''; };
  function renderSongs(){
    var box = $('songs');
    var list = songs.map(function(s){
      var on = song === s.id;
      var what = s.kind === 'video' ? W.song_recording : W.song_song;
      var where = s.where === 'Music' ? W.song_in_music : W.song_in_photos;
      return '<button class="song ' + (on ? 'on' : '') + '" type="button" data-id="' + esc(s.id) + '"><span class="ic">' +
        (s.kind === 'video' ? '&#9654;' : '&#9835;') + '</span><span><b>' + esc(s.name) + '</b><small>' + esc(what) + ', ' + esc(where) + '</small></span></button>';
    }).join('');
    box.innerHTML = list + '<button class="song none ' + (song === '' ? 'on' : '') + '" type="button" data-id=""><span class="ic">&ndash;</span><span><b>' +
      esc(W.no_song_b) + '</b><small>' + esc(W.no_song_s) + '</small></span></button>';
    box.querySelectorAll('.song').forEach(function(b){ b.onclick = function(){ song = b.dataset.id; renderSongs(); R.save(); if (R.changed) R.changed(); }; });
    $('step3').classList.toggle('done', song !== null);
  }
  // hers (loadSongs): a file that wasn't there on the last look is picked by itself
  function take(list){
    var fresh = seen ? list.filter(function(s){ return !seen[s.id]; }) : [];
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
    backforth: {max: D.styleMax.backforth, say: W.pick_backforth}, bookends: {max: D.styleMax.bookends, say: W.pick_bookends}};
  var STYLE_WORDS = {first: W.style_first_b, reveal: W.style_reveal_b, backforth: W.style_backforth_b, bookends: W.style_bookends_b};
  // hers: 0:04, 1:02.5
  function mmss(t){ t = Math.max(0, t); var m = Math.floor(t / 60), s = t - m * 60; return m + ':' + (s < 10 ? '0' : '') + (s % 1 ? s.toFixed(1) : Math.round(s)); }
  function videoUrl(key){ return '/reel-video?' + R.q + '&key=' + encodeURIComponent(key); }
  function stripUrl(key, n){ return '/reel-strip?' + R.q + '&key=' + encodeURIComponent(key) + '&n=' + n; }
  function stillUrl(id){ return '/reel-moment-still?' + R.q + '&id=' + encodeURIComponent(id); }
  function summary(){ if (R.changed) R.changed(); }
  R.footage = function(){ return footage; };

  // ---- the two cards (hers: setFootage) ----
  function setFootage(v){
    footage = v;
    $('modeBts').classList.toggle('on', v === true);
    $('modePhotos').classList.toggle('on', v === false);
    $('btsBox').hidden = v !== true;
    $('stepStyle').hidden = v !== true;
    $('step0').classList.toggle('done', v !== null);
    R.setFootage(v);                 // step 2: the recommended tag, its words, the assistant's footage order; renumbers
    renderStyles();
  }
  $('modeBts').onclick = function(){ setFootage(true); R.save(); summary(); loadFootage(); };
  $('modePhotos').onclick = function(){ setFootage(false); R.save(); summary(); };
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
  $('copyLine').onclick = function(){
    var t = $('pasteWords').textContent, ok = false;
    try {
      var r = document.createRange(); r.selectNodeContents($('pasteWords'));
      var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
      ok = document.execCommand('copy');
      s.removeAllRanges();
    } catch (e) { ok = false; }
    if (!ok && navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).catch(function(){});
    $('copyLine').textContent = W.copied; setTimeout(function(){ $('copyLine').textContent = W.copy; }, 1600);
  };

  // ---- the videos and Good to know (hers: renderVideos) ----
  function renderVideos(){
    $('vlist').innerHTML = vids.map(function(v){
      var small = v.preview === 'coming' ? W.coming_small + ' · ' + fill(W.mb, {n: v.mb}) : mmss(v.length) + ' · ' + fill(W.mb, {n: v.mb});
      return '<div class="vid"><span class="ic">&#9654;</span><span>' + esc(v.name) + '</span><small>' + esc(small) + '</small></div>';
    }).join('');
    renderViewers();
    var total = vids.reduce(function(a, v){ return a + v.length; }, 0);
    var w = W.insight_words;
    if (total > 0) {
      var est = total <= 180 ? W.est_1 : total <= 600 ? W.est_2 : total <= 1500 ? W.est_3 : W.est_4;
      w = fill(W.insight_added, {total: mmss(total), est: est}) + (total > 900 ? W.insight_trim : '');
    }
    $('insightWords').textContent = w;
  }

  // ---- watching the footage, and picking moments yourself (hers: renderViewers) ----
  function renderViewers(){
    var box = $('viewers'); if (!box) return;
    box.innerHTML = vids.map(function(v){
      var wide = v.w > v.h;
      if (v.preview !== 'ready') {
        var pc = v.preview === 'pc' || v.preview === 'hevc_pc';
        var stuck = v.preview === 'failed' || v.preview === 'lowspace' || pc;
        var msg = v.preview === 'lowspace' ? W.vid_lowspace : v.preview === 'failed' ? W.vid_failed
          : (pc || v.preview === 'coming') ? (v.words || W.vid_failed) : fill(W.vid_getting, {name: v.name});
        return '<div class="viewer" data-key="' + esc(v.key) + '"><p class="waiting" style="margin:0">' + (stuck ? '' : '<span class="spin"></span> ') + esc(msg) + '</p></div>';
      }
      return '<div class="viewer" data-key="' + esc(v.key) + '" data-ready="1">' +
        '<video class="' + (wide ? 'wide' : '') + '" src="' + esc(videoUrl(v.key)) + '" controls playsinline preload="metadata"></video>' +
        '<div class="vside"><h4>' + esc(v.name) + '</h4><p>' + esc(fill(W.vid_tap, {length: mmss(v.length)})) + '</p>' +
        '<div class="strip ' + (wide ? 'wide' : '') + '">' + (v.strip || []).map(function(s){
          return '<button type="button" data-t="' + s.t + '" title="' + esc(mmss(s.t)) + '"><img src="' + esc(stripUrl(v.key, s.n)) + '" alt="" loading="lazy"><span>' + esc(mmss(s.t)) + '</span></button>';
        }).join('') + '</div>' +
        '<div class="userow"><button class="btn main use" type="button">' + esc(W.use_moment) + '</button><span class="at"></span></div></div></div>';
    }).join('');
    box.querySelectorAll('.viewer[data-ready]').forEach(function(el){
      var vid = el.querySelector('video'), at = el.querySelector('.at'), key = el.dataset.key;
      var btns = Array.prototype.slice.call(el.querySelectorAll('.strip button'));
      var show = function(){
        at.textContent = fill(W.starts_at, {t: mmss(vid.currentTime)});
        var t = vid.currentTime;
        btns.forEach(function(b){ b.classList.toggle('now', +b.dataset.t <= t && t < +b.dataset.t + D.stripEvery); });
      };
      vid.addEventListener('timeupdate', show); vid.addEventListener('seeked', show); vid.addEventListener('loadedmetadata', show);
      btns.forEach(function(b){ b.onclick = function(){ vid.currentTime = +b.dataset.t; vid.play().catch(function(){}); }; });
      el.querySelector('.use').onclick = function(){
        var btn = el.querySelector('.use'), t = vid.currentTime; btn.disabled = true; vid.pause();
        R.post('/reel-moment', {kit: R.kit, do: 'add', video: key, start: Math.round(t * 10) / 10, seconds: D.useSeconds}).then(function(res){
          var r = res.j || {};
          if (r.ok) {
            var before = {}; moments.forEach(function(m){ before[m.id] = true; });
            takeMoments(r.moments);
            var added = moments.filter(function(m){ return !before[m.id]; })[0];
            if (added && style !== 'reveal') {
              var ids = chosen(), max = STYLE_PICK[style].max;
              sel[style] = max === 1 ? [added.id] : [added.id].concat(ids.filter(function(x){ return x !== added.id; })).slice(0, max);
              renderMoments(); R.save(); summary();
            }
            at.textContent = fill(W.added_at, {t: mmss(t)});
            $('moments').scrollIntoView({behavior: 'smooth', block: 'center'});
          } else at.textContent = r.words || W.didnt_work;
          btn.disabled = false;
        }).catch(function(){ at.textContent = W.no_server_short; btn.disabled = false; });
      };
    });
    markStrips();
  }
  function markStrips(){          // a dot on the stills that are inside a moment you're using (hers)
    var ids = chosen();
    document.querySelectorAll('.viewer[data-ready]').forEach(function(el){
      var ms = moments.filter(function(m){ return m.key === el.dataset.key && ids.indexOf(m.id) >= 0; });
      el.querySelectorAll('.strip button').forEach(function(b){ var t = +b.dataset.t; b.classList.toggle('inm', ms.some(function(m){ return t + D.stripEvery > m.start && t < m.end; })); });
    });
  }

  // ---- a moment's clip plays right on its card, from its start to its end (hers) ----
  var cardPlaying = null;
  function stopCard(){
    if (!cardPlaying) return;
    var v = cardPlaying.v, card = cardPlaying.card; cardPlaying = null;
    try { v.pause(); } catch (e) {}
    v.remove(); var pl = card.querySelector('.play'); if (pl) { pl.classList.remove('on'); pl.innerHTML = '&#9654;'; }
  }
  function previewCard(m){
    stopCard();
    document.querySelectorAll('.viewer video').forEach(function(v){ v.pause(); });
    var card = document.querySelector('.mom[data-id="' + CSS.escape(m.id) + '"]');
    var src = vids.filter(function(x){ return x.key === m.key; })[0];
    if (!card || !src || src.preview !== 'ready') return;
    var v = document.createElement('video');
    v.playsInline = true; v.preload = 'auto'; v.muted = false; v.src = videoUrl(src.key) + '#t=' + m.start;
    card.querySelector('.th').appendChild(v);
    var pl = card.querySelector('.play'); pl.classList.add('on'); pl.innerHTML = '&#9632;';
    cardPlaying = {v: v, card: card, id: m.id};
    v.addEventListener('loadedmetadata', function(){ v.currentTime = m.start; v.play().catch(function(){}); }, {once: true});
    v.addEventListener('timeupdate', function(){ if (v.currentTime >= m.end) stopCard(); });
    v.addEventListener('ended', stopCard);
  }
  R.cardPlaying = function(){ return cardPlaying ? cardPlaying.id : null; };
  var lenT = null;
  function changeMoment(m, change){
    var body = {kit: R.kit, do: 'update', id: m.id};
    for (var k in change) body[k] = change[k];
    R.post('/reel-moment', body).then(function(res){
      var r = res.j || {};
      if (!r.ok) return;
      stopCard(); takeMoments(r.moments);
      clearTimeout(lenT);              // let a few quick taps land, then play the new length (hers: 450 ms)
      lenT = setTimeout(function(){ var n = moments.filter(function(x){ return x.id === m.id; })[0]; if (n) previewCard(n); }, 450);
    }).catch(function(){});
  }
  var undoT = null;
  function removeMoment(m){
    var at = -1; moments.forEach(function(x, i){ if (x.id === m.id) at = i; });
    R.post('/reel-moment', {kit: R.kit, do: 'remove', id: m.id}).then(function(res){
      var r = res.j || {};
      if (!r.ok) return;
      stopCard(); takeMoments(r.moments);
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
  function sig(list){ return JSON.stringify((list || []).map(function(m){ return [m.id, m.key, m.start, m.end, m.label, m.photo]; })); }
  function fromServer(list){        // the moments as the Assistant has them now (Claude's look, or another window)
    if (!Array.isArray(list) || sig(list) === sig(moments)) return;
    moments = merge(list); renderMoments(); summary();
  }

  // ---- which clips each style uses: they select them on the cards (hers) ----
  function defaultSel(st){
    var ok = moments.filter(function(m){ return m.keep !== false; }), pool = ok.length ? ok : moments;
    if (st === 'first') return pool.slice(0, 1).map(function(m){ return m.id; });
    if (st === 'bookends') return (pool.length > 1 ? [pool[0], pool[pool.length - 1]] : pool.slice(0, 1)).map(function(m){ return m.id; });
    if (st === 'reveal') return moments.filter(function(m){ return m.photo; }).slice(0, 2).map(function(m){ return m.id; });
    return pool.slice(0, 2).map(function(m){ return m.id; });        // Back and forth starts with 2 clips (Nicole)
  }
  function chosen(){
    var ids = Array.isArray(sel[style]) ? sel[style] : defaultSel(style);
    return moments.filter(function(m){ return ids.indexOf(m.id) >= 0; }).map(function(m){ return m.id; });     // in card order
  }
  R.chosen = chosen;
  function toggleClip(m){
    var rule = STYLE_PICK[style], ids = chosen();
    if (ids.indexOf(m.id) >= 0) ids = ids.filter(function(x){ return x !== m.id; });
    else if (rule.max === 1) ids = [m.id];
    else if (ids.length >= rule.max) { $('momentsSay').textContent = fill(W.style_full, {max: rule.max}); return; }
    else ids = ids.concat(m.id);
    sel[style] = ids;
    renderMoments(); markStrips(); R.save(); summary();
  }
  function renderMoments(){
    var box = $('moments');
    markStrips();
    if (!moments.length) { box.innerHTML = ''; $('momentsSay').textContent = W.moments_none; return; }
    var yours = moments.filter(function(m){ return m.by === 'you'; }).length, found = moments.length - yours;
    var ids = chosen(), rule = STYLE_PICK[style] || STYLE_PICK.first;
    $('momentsSay').textContent = [found ? fill(W.n_found, {n: found}) : '', yours ? fill(W.n_yours, {n: yours}) : ''].filter(Boolean).join(W.n_and) +
      '. ' + rule.say + ' ' + W.moments_tail;
    box.innerHTML = moments.map(function(m){
      var on = ids.indexOf(m.id) >= 0, k = ids.indexOf(m.id), off = style === 'reveal' && !m.photo;
      var badge = !on ? '' : style === 'bookends' ? (k === 0 ? W.badge_opens : W.badge_closes) : style === 'first' ? W.badge_opens : fill(W.badge_clip, {k: k + 1});
      var pickW = off ? W.no_match : on ? W.selected : W.select;
      return '<div class="mom ' + (on ? 'sel' : '') + '" data-id="' + esc(m.id) + '">' + (badge ? '<span class="badge">' + esc(badge) + '</span>' : '') +
        '<span class="th"><img src="' + esc(stillUrl(m.id)) + '" alt=""></span>' +
        '<button class="play" type="button" title="' + esc(W.preview_moment) + '" aria-label="' + esc(W.preview_moment) + '">&#9654;</button>' +
        '<span class="tx">' + (m.by === 'you' ? '<span class="yours">' + esc(W.your_pick) + '</span>' : '') + '<b>' + esc(m.label || W.a_moment) + '</b>' +
        '<small>' + esc(m.name) + ' · ' + esc(fill(W.span, {a: mmss(m.start), b: mmss(m.end)})) + '</small>' +
        '<span class="len"><span><button class="ls" type="button" title="' + esc(W.shorter) + '" aria-label="' + esc(W.shorter_label) + '">&minus;</button><b>' + (m.end - m.start).toFixed(1) + ' s</b>' +
        '<button class="lg" type="button" title="' + esc(W.longer) + '" aria-label="' + esc(W.longer_label) + '">+</button></span><button class="rm" type="button">' + esc(W.remove) + '</button></span>' +
        '<button class="usebtn" type="button"' + (off ? ' disabled' : '') + '>' + esc(pickW) + '</button></span></div>';
    }).join('');
    box.querySelectorAll('.mom').forEach(function(b){
      var m = moments.filter(function(x){ return x.id === b.dataset.id; })[0];
      var img = b.querySelector('.th img'); img.onerror = function(){ img.remove(); };    // a PC: no still yet
      b.querySelector('.play').onclick = function(){ if (cardPlaying && cardPlaying.id === m.id) stopCard(); else previewCard(m); };
      b.querySelector('.th').onclick = function(){ previewCard(m); };
      b.querySelector('.ls').onclick = function(){ changeMoment(m, {end: Math.round((m.end - D.step) * 100) / 100}); };
      b.querySelector('.lg').onclick = function(){ changeMoment(m, {end: Math.round((m.end + D.step) * 100) / 100}); };
      b.querySelector('.rm').onclick = function(){ removeMoment(m); };
      b.querySelector('.usebtn').onclick = function(){ toggleClip(m); };
    });
  }

  // ---- looking at the Footage folder (hers: loadFootage, every 4 s) ----
  function loadFootage(){
    if (footage !== true) return;
    fetch('/reel-footage?' + R.q, {cache: 'no-store'}).then(function(r){ return r.json(); }).then(function(f){
      if (!f || !f.ok) return;
      vids = f.videos || [];
      var s = JSON.stringify(vids.map(function(v){ return [v.key, v.name, v.preview, (v.strip || []).length, v.words]; }));
      if (s !== vsig) { vsig = s; renderVideos(); }
      R.setClaudeBts(f.claude_bts || []);
      fromServer(f.moments);
    }).catch(function(){});
  }
  setInterval(function(){ if (!document.hidden && R.state()) loadFootage(); }, D.footEvery);

  // ---- step 4: the style (hers: renderStyles) ----
  function renderStyles(){
    document.querySelectorAll('#styles .opt').forEach(function(b){ b.classList.toggle('on', b.dataset.style === style); });
    $('stepStyle').classList.toggle('done', !!style);
    renderMoments();
  }
  document.querySelectorAll('#styles .opt').forEach(function(b){ b.onclick = function(){ style = b.dataset.style; renderStyles(); R.save(); summary(); }; });

  // ---- what the bar and Make my reel need from steps 1 and 4 ----
  R.sumExtra = function(){
    if (!footage) return '';
    var used = chosen().length;
    return esc(fill(W.sum_clip, {n: used, s: used === 1 ? '' : 's'})) + ' · ' + esc(STYLE_WORDS[style] || '');
  };
  R.beforeMake = function(){
    if (footage === null) return {h3: W.foot_need_h3, html: W.foot_need_html};
    if (footage && !chosen().length) return moments.length ? {h3: W.clips_need_h3, html: W.clips_need_html} : {h3: W.not_looked_h3, html: W.not_looked_html};
    return null;
  };
  R.makeExtra = function(){ return {footage: footage === true, style: style, clips: chosen()}; };

  R.part({
    fields: function(){ return {footage: footage, style: style, sel: sel, ask: ask, feel: feel}; },
    adopt: function(st, first){
      short = st.short;
      var sv = st.saved || {};
      footage = sv.footage === true ? true : sv.footage === false ? false : null;
      style = D.styles.indexOf(sv.style) >= 0 ? sv.style : 'first';
      sel = (sv.sel && typeof sv.sel === 'object' && !Array.isArray(sv.sel)) ? sv.sel : {};
      ask = typeof sv.ask === 'string' ? sv.ask : ''; feel = typeof sv.feel === 'string' ? sv.feel : '';
      if (first || document.activeElement !== $('askIn')) $('askIn').value = ask;
      if (first || document.activeElement !== $('feelOwn')) feelOwnOpen = false;
      moments = merge(st.moments);
      showFeel(); pasteLine();
      setFootage(footage); renderMoments();
      if (footage) loadFootage();
    },
    follow: function(st){ fromServer(st.moments); }
  });
})();
"""


# The bar at the bottom and Make my reel: hers, with the reel made by a job of its own that the page asks after.
# A later step adds to it through R.sumExtra() (words after the photo count, hers: " + 1 clip · Moment first"),
# R.beforeMake() (a reason not to make yet: {h3, html}) and R.makeExtra() (more for the request).
MAKE_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc;
  var TEST = new URLSearchParams(location.search).get('test') === '1';      // hers: plans the reel, makes nothing in CapCut
  var VIBE_WORDS = {beat: W.vibe_word_beat, mixed: W.vibe_word_mixed, calm: W.vibe_word_calm, build: W.vibe_word_build};
  var making = false, jobId = null, pollT = null, fails = 0;
  var btn = $('makeBtn'), out = $('result');
  if (TEST) btn.textContent = W.make_test;
  function summary(){
    if (!R.order || !R.song || !R.vibe) return;
    var n = R.order().length, s = R.song(), name = R.songName();
    var songW = s === null ? W.sum_no_song_yet : s === '' ? W.sum_no_song : (name ? esc(name) : W.sum_no_song_yet);
    var ft = R.sumExtra ? R.sumExtra() : '';
    $('sum').innerHTML = '<b>' + esc(R.fill(n === 1 ? W.one_photo : W.photos, {n: n})) + ft + '</b> · ' + songW + ' · ' + esc(VIBE_WORDS[R.vibe()] || '');
    if (!making) btn.disabled = !n;
  }
  R.changed = summary;
  function busy(on){
    making = on;
    if (on) { btn.disabled = true; btn.innerHTML = '<span class="spin"></span> ' + esc(W.making); }
    else { btn.textContent = TEST ? W.make_test : W.make; btn.disabled = !(R.order && R.order().length); }
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
        '</button><a class="btn" id="resultBack" href="' + esc(back.getAttribute('href')) + '">' + esc($('backWords').textContent) + '</a></div><p class="went" id="went"></p>';
      $('capcut').onclick = function(){
        R.post('/reel-capcut', {kit: R.kit}).then(function(res){ $('went').textContent = (res.j && res.j.words) || ''; }).catch(function(){});
      };
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
    var st = R.state() || {}, extra = R.makeExtra ? R.makeExtra() : {};
    var body = {kit: R.kit, stamp: st.stamp, picks: R.order(), song: R.song(), vibe: R.vibe(), test: TEST};
    for (var k in extra) body[k] = extra[k];
    R.post('/reel-make', body).then(function(res){
      var j = res.j || {};
      if (j.job) { follow(j.job); return; }             // started, or already being made: that one is followed
      busy(false); bad(W.didnt_work_h3, esc(j.words || W.went_wrong));
    }).catch(function(){ busy(false); bad(W.didnt_work_h3, esc(W.no_server)); });
  };
  R.part({
    adopt: function(st, first){
      var job = st.job;
      if (first && job && (job.state === 'queued' || job.state === 'running') && !making) follow(job);   // reloaded while one is at work
      summary();
    }
  });
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
    say(addr)
    return 0


def cmd_show(kit):
    st = state(kit)
    if st is None:
        say("STOP: couldn't read this shoot's numbered list. Nothing was changed.")
        return 1
    saved = st["saved"] or {}
    say(f"{st['short']}  ({kit.name})")
    say(f"  Claude's order: {','.join(str(x['n']) + x['h'] for x in st['claude']) or '(none yet)'}")
    if saved:
        whose = "their own order" if saved.get("mine") else "the assistant's order"
        say(f"  On the page: {whose}")
    else:
        say("  On the page: nothing saved yet")
    say(f"  The order Make my reel uses: {current_picks(kit) or '(none yet)'}")
    sid = saved.get("song")
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
    rec = load(kit)
    ms = moments_of(rec)
    foot = saved.get("footage")
    if foot is True:
        style = saved.get("style") if saved.get("style") in STYLES else "first"
        clips = chosen_clips(saved, ms)
        say(f"  Footage: yes, {WORDS['style_' + style + '_b']}, {len(clips)} clip{'s' if len(clips) != 1 else ''} selected"
            + (f" ({', '.join(clips)})" if clips else ""))
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
    if saved.get("ask") or saved.get("feel"):
        say(f"  Their notes for the footage look: {saved.get('ask') or '(none)'}; the feel: {saved.get('feel') or '(none)'}")
    made = [m for m in (rec.get("made") or []) if isinstance(m, dict)]
    if made:
        say(f"  Reels made from the page: {len(made)}, the newest \"{made[-1].get('project')}\"")
    say(f"  Saved {st['rev']} time{'s' if st['rev'] != 1 else ''}")
    return 0


def cmd_make(kit, a):
    """Claude's own Make my reel (see the top of this file): what the page would hand reel.py, made the same way,
    one reel at a time on this computer. A song comes from the page, unless they asked for CapCut's own music."""
    st = state(kit)
    if st is None:
        say("STOP: couldn't read this shoot's numbered list. Nothing was made.")
        return 1
    saved = st["saved"] or {}
    picks = current_picks(kit)
    if not picks:
        say("STOP: there's no order for this reel yet: pick the photos first (kit.py picks --reel), or they put them in order on the page.")
        return 1
    if len([x for x in picks.split(",") if x]) > MAX_PICKS:
        say("STOP: " + OUR_WORDS["too_many"])
        return 1
    vibe = saved.get("vibe") if saved.get("vibe") in VIBES else default_vibe()
    ask = {"picks": picks, "vibe": vibe, "dry": bool(a.dry_run), "stamp": st["stamp"]}
    if saved.get("footage") is True:            # behind the scenes, as the page would make it: its style, its clips
        style = saved.get("style") if saved.get("style") in STYLES else "first"
        with arrange.locked(lock_path(kit)):
            ms = moments_of(load(kit))
        clips = chosen_clips(saved, ms)
        if not clips:
            say("STOP: footage is on for this reel, but no clips are selected on the page (Select your clips, in step 1). "
                "They select them there, or choose Just photos.")
            return 1
        ask.update(footage=style, clips=clips)
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("open").add_argument("words")
    sub.add_parser("show").add_argument("words")
    m = sub.add_parser("make", help="Claude's own Make my reel: the page's order, song and vibe")
    m.add_argument("words")
    m.add_argument("--capcut-song", help="a song from CapCut's music (only when they asked for it, after the licence note)")
    m.add_argument("--hook", help="words on the first photo, when they asked for them")
    m.add_argument("--name", help="another name for the CapCut project (a second take)")
    m.add_argument("--no-song", action="store_true", help="no song, whatever the page has")
    m.add_argument("--dry-run", action="store_true")
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
        return cmd_show(kit)
    except arrange.Busy:
        say("STOP: this shoot's reel page is being written by something else right now. Nothing was changed. Try again in a moment.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
