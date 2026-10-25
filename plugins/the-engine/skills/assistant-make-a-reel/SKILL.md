---
name: assistant-make-a-reel
description: The Studio by Horizon Found, the reel. Turns a photographer's edited, exported photos into a CapCut project cut on the beat of their song, with Claude picking and ordering the photos, ready for them to style and export in CapCut. Use this whenever the person says make a reel, turn these into a reel, reel from the beach shoot, yes to "want a reel?", cut these to a song, or trial reels from this shoot, even if they do not name the Studio.
---

# Make a reel

This is part of what the Studio Manager does, after the edit. The photographer has exported their edited photos; you pick the strongest ones, put them in an order that flows, and lay them on the beat of their song as a new CapCut project. They open CapCut, add their look (a text style, a filter, a template), and export. You save them the hour of choosing and cutting. You never make the look, and nothing posts.

Talk the way the Studio Manager talks: short, plain words, the result first, one question at a time with buttons (the likely answer first, marked recommended) and the Other box always there. The photographer is "you" or "they", never "she" or "he". No file names in code styling, no settings talk.

The scripts are in `scripts/` next to this file. Nothing has to be installed on a Mac: the song is read with the Mac's own tools and everything else is plain Python.

## The rules

1. **Edited photos only.** A reel is made from the photos they exported after editing, never from the backup's raw files. If all you have is a backup, say "Whenever you're finished with your edits, let me know and I'll turn your favorites into a reel."
2. **Every frame is theirs.** Hard cuts on the beat. No transitions, no effects, no zooms or motion, no generated anything. Their look comes from CapCut.
3. **Always a new CapCut project.** Never open, change or overwrite one they made. The script will not.
4. **CapCut closed while it writes.** The script checks. If CapCut is open it stops and you ask them to quit it for a moment.
5. **One look at the sheet, not photo by photo.** The contact sheet is how you see the shoot. Open a single photo larger only to settle a close call, and never more than a handful.
6. **Nothing posts, nothing sends.**

## Step 1: the edited photos

Usually you arrive here from the Studio Manager: they said "I'm done with the beach shoot," it found the export folder and they confirmed it. Use that folder. If they came straight here, ask which shoot; the Studio Manager's `find_exports.py` finds the folder (see its skill), or they tell you where it is. A folder of favorites or selects they made themselves is even better: use that.

Make the sheet:

```
python3 scripts/reel.py sheet --folder "<edited photos>" --shoot "<shoot name>"
```

It writes one numbered contact sheet (more if there are over 48 photos) and a list with which way each photo is (tall, wide, square), in the Studio's own folder; their photo folder is not changed. Read the sheet image(s).

## Step 2: pick and order

Pick 8 to 14 photos and put them in order. What makes a good reel of stills:

- **Open on the scroll-stopper**: the most striking, emotional frame, readable at a glance on a phone.
- **Vary it**: wide, then close, then a detail; posed, then candid. Never two near-identical frames back to back.
- **Let the color and light flow** from one photo to the next rather than jumping.
- **End on a closer**: a quiet, strong frame that feels like the last line.
- **Tall photos first choice.** A reel is a tall screen; a wide photo gets zoomed to fill it and loses its sides. One or two wide ones are fine if they are strong and the subject is near the middle.

Show the pick in one short message: the numbers in order, and a few words on the opener and the closer ("Opening on 7, the laugh in the wind; closing on 12, the walk away"). Then one question: "Go with these?" [Make it (recommended)] [Change the picks]. If they change it ("swap 3 for 5", "start with the couple"), just do it.

## Step 3: the song

Ask with buttons: "Which song?" [A song file on this computer] [No song for now] (and Other).

- **A song file:** run `python3 scripts/reel.py songs` (it looks in Downloads, Music and Desktop, newest first). Offer the top three or four as buttons by name. Songs bought or streamed in Apple Music are locked and cannot be read; if that is the only copy, say so plainly and suggest a downloaded song.
- **No song for now:** the cuts go at an even pace (100 beats a minute), so music can be added in CapCut or Instagram afterwards. Say that in one line.
- **A song from CapCut's own music library** is not supported yet; if they ask, say it's coming and offer the two options above.

The script starts the song where it picks up (the loudest stretch that fits, on a beat, nudged toward where the energy jumps) and says where. If they want a different moment, `--song-start 58` is seconds into the song, `--song-start 0` the very top.

## Step 4: words on the first photo (optional)

Ask: "Want words on the first photo?" [No words (recommended)] [Yes, give me options]. If yes, write five short options in their voice (their Brand File's Voice section if they have one). Rules from Nicole: it speaks to their client about what the client feels and wants, never about how the photographer works; one short line, readable in a second; a real angle only this photographer would say; never invent a name, date, price or offer. They pick one. It goes in as plain white text over the first photo; they restyle it with one of CapCut's text styles.

## Step 5: make it

```
python3 scripts/reel.py make --folder "<edited photos>" --shoot "<shoot name>" \
  --picks 7,2,11,4,9,1,5,12 --song "<song file>"        (or --song none)
  [--hook "the line they picked"] [--rhythm build] [--song-start 58] [--fit]
```

- Every photo holds the same number of beats, about a second each; the first and last hold twice as long. `--rhythm build` quickens the last third and settles on the last photo; offer it if they want more energy.
- Wide photos fill the screen by default; `--fit` shows them whole with bars instead.
- `--dry-run` prints the plan and writes nothing.

Exit 8 means CapCut is open: "CapCut is open. Quit it for a moment (CapCut menu, Quit CapCut) and tell me." Then run the same command again. Exit 2 is a stop: say what it printed.

## Step 6: hand it over

Two lines, their words: "It's in CapCut: Black-sand beach reel, 10 photos, 12.4 seconds, cut on the beat of Golden Hour. Open it, add your look, and export." If the script named wide photos, add: "Photo 4 is wide, so it's zoomed to fill the screen; slide it in CapCut if anything important is cut off."

Then one next step, as a question with buttons: a carousel from the same picks, or trial reels. **Trial reels** are the same cut with a different opening line: run `make` again with another `--hook` and `--name "<shoot> reel, take 2"`, one project each, in seconds. Remind them once that trial reels go out as trial reels, never to the feed.

## Untested, honestly

Proven on Dustin's Mac with CapCut 9.6: a project written this way opens and exports (Oct 21). The full flow here (sheet, pick, song, beat, project) has run on test photos only. Not yet tried: CapCut versions other than 9.6, Windows (the projects folder and the song reading are written for it, not run), HEIC photos, songs from CapCut's library. The first time on any of these, say "first time on this, tell me if anything looks off" and keep going.

## Parked

The earlier version rendered finished MP4s with ffmpeg (`make_reel.py`, `hooktext.py`, `grade_reel.py`, `beats.py`, `check_setup.py`). Next to CapCut's own looks it read as amateur, so it is parked: the code stays, nothing new is built on it, and you do not use it.
