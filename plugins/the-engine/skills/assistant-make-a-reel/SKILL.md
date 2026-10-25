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
4. **CapCut can stay open.** If it is open, the script writes only the new project's folder and CapCut adds it to its projects by itself; if it is closed, the project is added to CapCut's list for next time. Never ask them to quit CapCut unless the new project doesn't show up.
5. **One look at the sheet, not photo by photo.** The contact sheet is how you see the shoot and the strip is how you check the order. Open a single photo larger only to settle a close call, and never more than a handful.
6. **Nothing posts, nothing sends.**

## Step 1: the edited photos

Usually you arrive here from the Studio Manager: they said "I'm done with the beach shoot," it found the export folder and they confirmed it. Use that folder. If they came straight here, ask which shoot; the Studio Manager's `find_exports.py` finds the folder (see its skill), or they tell you where it is. A folder of favorites or selects they made themselves is even better: use that.

Make the sheet:

```
python3 scripts/reel.py sheet --folder "<edited photos>" --shoot "<shoot name>"
```

It writes one numbered contact sheet (more if there are over 48 photos) and a list with which way each photo is (tall, wide, square), in the Studio's own folder; their photo folder is not changed. Read the sheet image(s).

## Step 2: curate the set (your main job)

Read `../../shared/curating.md` first, every time. The photos are already edited and each one already looks great on its own; your job is to make them look great **as a group**, flowing from one to the next in the most harmonious way possible. That comes before everything else here.

Pick 8 to 14 and order them by those rules: open on the scroll-stopper; move between wides, mediums, close-ups and details, never three of one distance in a row; change one thing at a time from photo to photo (light, color, distance, direction), so every cut feels like the natural next one; let color and light travel somewhere instead of bouncing; no near-twins side by side; close on a quiet, final frame. A great photo that fights the flow stays out. For a reel, add one more: **tall photos first**, since the screen is tall and a wide photo loses its sides (one or two wide ones are fine if the subject sits near the middle).

While you order them, mark how long each one deserves: a `+` after a number to linger on it (the emotional peak, a wide with a lot to take in, the closer), a `-` to pass quickly (a run of details, two or three frames of one laugh in a burst). Most photos get no mark. With the "a little of everything" pace these marks decide where the long and quick moments fall, so the rhythm follows the photos instead of a formula.

Then check your order as it will play:

```
python3 scripts/reel.py strip --folder "<edited photos>" --shoot "<shoot name>" --picks 7,2,11+,4,9-,1-,5,12+
```

Read the strip left to right. Fix any jolt (swap two neighbors, move a detail in as a breather, drop the one that fights) and draw it again if you changed anything.

Show the pick in one short message: the numbers in order and a few words on how it flows ("Opens wide on the beach, moves in to the two of them, then hands and the ring, ends on the walk away"), plus one line for any trade-off ("Left out 14, lovely but a twin of 9"). Then one question: "Go with these?" [Make it (recommended)] [Change the picks]. If they change it ("swap 3 for 5", "start with the couple"), do it their way; mention once if it now puts near-twins or three close-ups together.

## Step 3: the song

Run `python3 scripts/reel.py songs` first. It lists songs from CapCut's own music that are in their CapCut projects (C1, C2...), then song files on the computer (Downloads, Music, Desktop, newest first).

Ask with buttons: "Which song?" [A song from CapCut's music] [A song file on this computer] [No song for now] (and Other). Put first whichever they used last time; a first-timer with CapCut songs listed gets CapCut's music first.

- **A song from CapCut's music:** offer the songs listed (C1, C2...) as buttons by name. If the one they want isn't there: "Pick it in CapCut: start a new project, add the song from CapCut's music, then quit CapCut and tell me." The first time they choose CapCut's music (the list says "License note: not shown yet"), tell them once, plainly, before making anything: "CapCut's own songs come with CapCut's license: its regular songs are for personal, non-commercial posts, and its commercial songs are cleared for businesses only on CapCut and TikTok, not Instagram. Your call." Buttons: [Use it anyway] [Pick a different song]. On "Use it anyway", run `python3 scripts/reel.py capcut-ok` so the note isn't repeated, and carry on. It is their decision; don't lecture, don't repeat the note on later reels. Then make it with `--capcut-song "<song name>"` instead of `--song`. The song goes into the new project exactly as CapCut saved it (still CapCut's library song, with CapCut's own beat markers), and our cuts land on the same beats CapCut shows.
- **A song file:** offer the top three or four files as buttons by name. Songs bought or streamed in Apple Music are locked and cannot be read; if that is the only copy, say so plainly and suggest a downloaded song. Licensed music services (Artlist, Epidemic Sound, Musicbed and the like) cover social posts; their downloads work here.
- **No song for now:** the cuts go at an even pace (100 beats a minute), so music can be added in CapCut or Instagram afterwards. Say that in one line.

The script starts the song where it picks up (the loudest stretch that fits, on a beat, nudged toward where the energy jumps) and says where. If they want a different moment, `--song-start 58` is seconds into the song, `--song-start 0` the very top.

## Step 4: how it moves

Ask with buttons: "How should it move?"
- **A little of everything (recommended):** some quick, some long, never a formula. The changes fall where the music turns over, more cuts where the song is busy and fewer where it's quiet, and your `+` and `-` marks decide which photos linger and which fly by.
- **Calm:** about two seconds a photo; room to look. Best with 6 to 9 photos.
- **Fast:** about half a second a photo; quick and punchy. Best with 12 to 20 photos.
- **Build:** starts calm, quickens toward the end, then lands on the last photo.

Every cut lands on the beat whichever they pick. If they pick Fast and you chose fewer than 12 photos, offer a few more from the sheet; if Calm and more than 9, offer to trim.

## Step 5: words on the first photo (optional)

Ask: "Want words on the first photo?" [No words (recommended)] [Yes, give me options]. If yes, write five short options in their voice (their Brand File's Voice section if they have one). Rules from Nicole: it speaks to their client about what the client feels and wants, never about how the photographer works; one short line, readable in a second; a real angle only this photographer would say; never invent a name, date, price or offer. They pick one. It goes in as plain white text over the first photo; they restyle it with one of CapCut's text styles.

## Step 6: make it

```
python3 scripts/reel.py make --folder "<edited photos>" --shoot "<shoot name>" \
  --picks 7,2,11+,4,9-,1-,5,12+ --song "<song file>"   (or --capcut-song "<name>", or --song none)
  --pace mixed|calm|fast|build   [--hook "the line they picked"] [--song-start 58] [--fit] [--variation 2]
```

- `--pace` is their answer from Step 4 (`mixed` is "a little of everything"). The first photo always holds long enough to read, and the last one lands.
- `--variation 2` (3, 4...) gives another mix of the same picks with the same pace, if they want to see it move differently.
- Wide photos fill the screen by default; `--fit` shows them whole with bars instead.
- `--dry-run` prints the plan and writes nothing.

If the script says CapCut was open, tell them it will appear in their CapCut projects in a moment, and only if it doesn't: "Quit CapCut and open it again." Exit 2 is a stop: say what it printed.

How the timing works, if they ask: the reel starts on the first beat of a bar, long holds land on the 1 of a bar (songs in 3, like a waltz, are counted in 3), and every cut sits on the video frame at or just before its beat, never after, so it never feels late. With a song from CapCut's music, the cuts follow CapCut's own beat marks.

## Step 7: hand it over

Two lines, their words: "It's in CapCut: Black-sand beach reel, 10 photos, 12.4 seconds, cut on the beat of Golden Hour. Open it, add your look, and export." If the script named wide photos, add: "Photo 4 is wide, so it's zoomed to fill the screen; slide it in CapCut if anything important is cut off."

Then one next step, as a question with buttons: a carousel from the same picks, or trial reels. **Trial reels** are the same cut with a different opening line: run `make` again with another `--hook` and `--name "<shoot> reel, take 2"`, one project each, in seconds. Remind them once that trial reels go out as trial reels, never to the feed.

## Untested, honestly

Proven on Dustin's Mac with CapCut 9.6: a project written this way opens and exports (Oct 21). The full flow here (sheet, pick, song, beat, project) has run on test photos only. Not yet tried: CapCut versions other than 9.6, Windows (the projects folder and the song reading are written for it, not run), HEIC photos. The first time on any of these, say "first time on this, tell me if anything looks off" and keep going.

## Parked

The earlier version rendered finished MP4s with ffmpeg (`make_reel.py`, `hooktext.py`, `grade_reel.py`, `beats.py`, `check_setup.py`). Next to CapCut's own looks it read as amateur, so it is parked: the code stays, nothing new is built on it, and you do not use it.
