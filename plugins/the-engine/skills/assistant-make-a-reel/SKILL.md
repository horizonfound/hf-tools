---
name: assistant-make-a-reel
description: The Assistant by Horizon Found, the reel. Turns a photographer's edited, exported photos into a CapCut project cut on the beat of their song, with Claude picking and ordering the photos, ready for them to style and export in CapCut. Use this whenever the person says make a reel, turn these into a reel, reel from the beach shoot, yes to "want a reel?", cut these to a song, or trial reels from this shoot, even if they do not name the Assistant.
---

# Make a reel

This is part of what the Assistant does, after the edit. The photographer has exported their edited photos; you pick the strongest ones, put them in an order that flows, and lay them on the beat of their song as a new CapCut project. They open CapCut, add their look (a text style, a filter, a template), and export. You save them the hour of choosing and cutting. You never make the look, and nothing posts.

Talk the way the Assistant talks: short, plain words, the result first, one question at a time with buttons (the likely answer first, marked recommended) and the Other box always there. The photographer is "you" or "they", never "she" or "he". No file names in code styling, no settings talk.

The scripts are in `scripts/` next to this file. Nothing has to be installed on a Mac: the song is read with the Mac's own tools and everything else is plain Python. **On a Windows PC,** read the Assistant's `../studio-manager/parts/on-a-pc.md` first (once per conversation; its section "The reel" is this skill's): reading a song and CapCut have never been tried on a PC, and it says what to say when they don't work yet.

## The rules

1. **Edited photos only.** A reel is made from the photos they exported after editing, never from the backup's raw files. If all you have is a backup, say "Whenever you're finished with your edits, let me know and I'll turn your favorites into a reel."
2. **Every frame is theirs.** Hard cuts on the beat. No transitions, no effects, no zooms or motion, no generated anything. Their look comes from CapCut.
3. **Always a new CapCut project.** Never open, change or overwrite one they made. The script will not.
4. **CapCut can stay open** (on a Mac). If it is open, the script writes only the new project's folder and CapCut adds it to its projects by itself; if it is closed, the project is added to CapCut's list for next time. Never ask them to quit CapCut unless the new project doesn't show up. **On a PC, a reel made while CapCut is open waits** to be added to CapCut's list. If the output ends with "NOTE: once CapCut is closed, `capcut.py open` adds the waiting reel...", ask them to close CapCut, then run `python3 scripts/capcut.py open`, which adds the reel to CapCut's list and starts CapCut. (The same line can appear on either computer when CapCut's list couldn't be saved; the answer is the same.) `python3 scripts/capcut.py open` also just starts CapCut, on either computer, whenever they want it open.
5. **One look at the sheet, not photo by photo.** The contact sheet is how you see the shoot and the strip is how you check the order. Open a single photo larger only to settle a close call, and never more than a handful.
6. **Nothing posts, nothing sends.**

## Step 1: the edited photos

Usually you arrive here from the Assistant: they said "I'm done with the beach shoot," it found the export folder and they confirmed it. Use that folder. If they came straight here, ask which shoot; the Assistant's `find_exports.py` finds the folder (see its skill), or they tell you where it is. A folder of favorites or selects they made themselves is even better: use that.

**First, find out whether this shoot has a post kit**, because that decides how the photos are numbered, and every number you pick from here on comes from that one numbering. It has a kit when you came here from one, or when `python3 ../studio-manager/scripts/kit.py show "<shoot name>"` finds it (that prints STOP when there is none).

**With a post kit,** number the photos through the kit, so your numbers and the page's (Step 2) are the same:

```
python3 ../studio-manager/scripts/kit.py sheet "<kit>"
```

It runs this skill's sheet on the kit's own photos and keeps the list with the kit. From here on, for every command in this skill, `--folder` is the kit's photos (the folder `kit.py show` prints after "Photos:", or the Photos folder inside the kit's own folder when it prints none) and `--shoot` is the kit's name as `kit.py show` prints it. Once a shoot has a kit, do not run `reel.py sheet` on some other folder under the same shoot name: that numbers the photos differently, and numbers you picked would point at other photos on the page.

**No post kit:** make the sheet yourself:

```
python3 scripts/reel.py sheet --folder "<edited photos>" --shoot "<shoot name>"
```

Either way it writes one numbered contact sheet (more if there are over 48 photos) and a list with which way each photo is (tall, wide, square), in the Assistant's own folder; their photo folder is not changed. Read the sheet image(s).

## Step 2: curate the set (your main job)

Read `../../shared/curating.md` first, every time. The photos are already edited and each one already looks great on its own; your job is to make them look great **as a group**, flowing from one to the next in the most harmonious way possible. That comes before everything else here.

Pick 8 to 14 and order them by those rules: open on the scroll-stopper; move between wides, mediums, close-ups and details, never three of one distance in a row; change one thing at a time from photo to photo (light, color, distance, direction), so every cut feels like the natural next one; let color and light travel somewhere instead of bouncing; no near-twins side by side; close on a quiet, final frame. A great photo that fights the flow stays out. For a reel, add one more: **tall photos first**, since the screen is tall and a wide photo loses its sides (one or two wide ones are fine if the subject sits near the middle).

While you order them, mark how long each one deserves: a `+` after a number to linger on it (the emotional peak, a wide with a lot to take in, the closer), a `-` to pass quickly (a run of details, two or three frames of one laugh in a burst). Most photos get no mark. The marks count in every vibe, in the page's words: "Longer stays on screen about twice as long", "Quicker gets the shortest time, one beat".

Then check your order as it will play:

```
python3 scripts/reel.py strip --folder "<edited photos>" --shoot "<shoot name>" --picks 7,2,11+,4,9-,1-,5,12+
```

Read the strip left to right. Fix any jolt (swap two neighbors, move a detail in as a breather, drop the one that fights) and draw it again if you changed anything.

**Show the pick.** How depends on whether this shoot has a post kit (you found that out in Step 1).

**With a post kit: on the page beside the chat.** The photographer sees your pick as a row of photos they can move, instead of a paragraph of numbers. Your numbers are the kit's own, since Step 1 numbered the photos through the kit. Save your pick, marks and all, and open the page:

```
python3 ../studio-manager/scripts/kit.py picks "<kit>" --reel 7,2,11+,4,9-,1-,5,12+
python3 ../studio-manager/scripts/arrange.py open "<kit>" --piece reel
```

The second prints the page's address on its last line. Load it in the Claude app's browser pane and bring the pane forward; never Chrome. Then say it short: "My pick for the reel is on the page beside us: 12 photos, in the order they'll play. Opens wide on the beach, moves in to the two of them, ends on the walk away. Move anything you like, or leave it as it is. Next I'll ask which song to cut it to." (add one line for any trade-off), and ask the same question: "Go with these?" [Make it (recommended)] [Change the picks]. On Change the picks: "It's on the page beside us. Drag the photos where you want them, then press \"I'm happy with this order\"." and wait; the page tells them to come back and say "done". If they would rather say the change ("swap 3 for 5", "start with the couple"), do it their way with `kit.py picks` again; the page beside the chat shows the new pick by itself within a few seconds (if it hasn't, load its address in the pane again); mention once if it now puts near-twins or three close-ups together.

**Whichever way they said yes** (the button, "done", "looks good"), run this before the song step and use the picks it prints for everything after:

```
python3 ../studio-manager/scripts/arrange.py apply "<kit>" --piece reel        prints: Reel picks: 7,2,11+,4,9-,1-,5,12+
```

It is their order if they moved anything and yours if they didn't, with Longer as `+` and Quicker as `-`. More on the page, and on a line starting ARRANGED, is in the Assistant's `parts/arrange.md` (`../studio-manager/parts/arrange.md`). When a whole post kit is being made, its steps carry on without stopping, so the pick is not shown first there; they can change it afterwards.

**No post kit: in the chat.** Show the pick in one short message: the numbers in order and a few words on how it flows ("Opens wide on the beach, moves in to the two of them, then hands and the ring, ends on the walk away"), plus one line for any trade-off ("Left out 14, lovely but a twin of 9"). Then one question: "Go with these?" [Make it (recommended)] [Change the picks]. If they change it ("swap 3 for 5", "start with the couple"), do it their way; mention once if it now puts near-twins or three close-ups together.

## Step 3: the song

Run `python3 scripts/reel.py songs` first. It lists songs from CapCut's own music that are in their CapCut projects (C1, C2...), then song files on the computer (Downloads, Music, Desktop, newest first).

Ask with buttons: "Which song?" [A song from CapCut's music] [A song file on this computer] [No song for now] (and Other). Put first whichever they used last time; a first-timer with CapCut songs listed gets CapCut's music first.

- **A song from CapCut's music:** offer the songs listed (C1, C2...) as buttons by name. If the one they want isn't there: "Pick it in CapCut: start a new project, add the song from CapCut's music, then quit CapCut and tell me." The first time they choose CapCut's music (the list says "License note: not shown yet"), tell them once, plainly, before making anything: "CapCut's own songs come with CapCut's license: its regular songs are for personal, non-commercial posts, and its commercial songs are cleared for businesses only on CapCut and TikTok, not Instagram. Your call." Buttons: [Use it anyway] [Pick a different song]. On "Use it anyway", run `python3 scripts/reel.py capcut-ok` so the note isn't repeated, and carry on. It is their decision; don't lecture, don't repeat the note on later reels. Then make it with `--capcut-song "<song name>"` instead of `--song`. The song goes into the new project exactly as CapCut saved it (still CapCut's library song, with CapCut's own beat markers), and our cuts land on the same beats CapCut shows.
- **A song file:** offer the top three or four files as buttons by name. Songs bought or streamed in Apple Music are locked and cannot be read; if that is the only copy, say so plainly and suggest a downloaded song. Licensed music services (Artlist, Epidemic Sound, Musicbed and the like) cover social posts; their downloads work here.
- **A video or a screen recording with the sound they want** (they screen-recorded a post, or dropped a clip in with the photos): `python3 scripts/reel.py sound --from "<the video>" --shoot "<shoot name>"` pulls the sound out (on a Mac with its own tools; on a PC with ffmpeg if it is there, otherwise Windows' own media parts, which give a .wav file) and prints where the song file is; pass that to `--song`. (On a PC this has never been tried; if it stops, say so plainly.) **Never move, rename or tidy their recording, and never save the song into Music, Downloads, Desktop or Documents** (Nicole's first reel, Nov 5: the song was put in her Music folder, CapCut showed "File not accessible", and she had to link it by hand). A sound recorded off Instagram is fine as a guide to cut to; say once that the clean way to post is to add the same sound in Instagram.
- **No song for now:** the cuts go at an even pace (100 beats a minute), so music can be added in CapCut or Instagram afterwards. Say that in one line.

**The song travels inside the CapCut project.** `reel.py make` puts its own checked copy of a song file in the project's folder and points CapCut at that copy, so CapCut can always open it and nothing done to the original later can break the reel. So never hand-edit a project's song path, and never move a song "to fix" a reel: make the reel again.

**Say the song question is coming (Nicole, Nov 5).** When you ask "Go with these?" in Step 2, add one line: "Next I'll ask which song to cut it to."

The script starts the song where it picks up (the loudest stretch that fits, on a beat, nudged toward where the energy jumps) and says where. If they want a different moment, `--song-start 58` is seconds into the song, `--song-start 0` the very top.

## Step 4: the vibe

Ask with buttons, in Nicole's words from her reel page: "How should it move? Every cut lands on the beat, whichever you pick. None of these is a fixed template: the timing is worked out for your song, your photos and your clips, so every reel comes out its own way."
- **On every beat (recommended):** Quick and punchy, a new photo on the beat, with a longer hold where the song hits. (`--pace beat`)
- **A little of everything:** Some quick, some long, changing where the music turns over. (`--pace mixed`)
- **Calm:** Longer looks, room to breathe. Best with fewer photos or a longer song. (`--pace calm`)
- **Build:** Starts calm, speeds up toward the end, then lands on the last photo. (`--pace build`)

**Always ask this question; never skip it and never pick for them.** The Longer and Quicker marks count with every one of the four. If they want to see the same choices move differently, make it again with `--variation 2` (3, 4...): every reel comes out its own way.

**Every cut on a whole beat, every photo at least one beat (Nicole, Nov 6).** No half-beat cuts, ever: Quicker is the shortest, one beat; no photo is on screen for less than about half a second (on a very fast song the shortest becomes two beats); the last photo always gets at least two beats. Quick half-beat pairs are gone: on one of her test reels they were 0.3 s a photo, "so fast it like disappears before you even see anything... they don't even hit the beat." **Never write your own script to cut faster or on half beats.** Every cut the Assistant makes comes from `reel.py make`.

**"Too slow", "faster", "more energy" (Nicole's first reel, Nov 5).** Make it again with On every beat (`--pace beat`): that is the one she said "Yes, that's it" to. If it is still too slow, the song is slow: say so and offer a quicker song, or more photos. (The old names still work: `--pace fast` is On every beat, `--pace steady` is Calm.)

**Nothing is left out to fit a vibe** ("you shouldn't be removing" photos or footage). When the song is short, the vibe bends: the script keeps every photo, makes the vibe quicker and says so in a line like "Your song is only 15 seconds, so I kept all 14 photos and made Calm quicker to fit. A longer song, or fewer photos, gives it more room." Pass that line on as it is. When even one beat a photo can't fit, nothing is made and it says exactly why ("Your song is only 15 seconds, and 14 photos need at least 15 seconds, even with every photo at one beat. Take a few photos out, or use a longer song."): tell them in those words, as "Your song is a little short for this", never as an error, and ask which they'd like.

## Step 5: words on the first photo (optional)

Ask: "Want words on the first photo?" [No words (recommended)] [Yes, give me options]. If yes, write five short options in their voice (their Brand File's Voice section if they have one). Rules from Nicole: it speaks to their client about what the client feels and wants, never about how the photographer works; one short line, readable in a second; a real angle only this photographer would say; never invent a name, date, price or offer. They pick one. It goes in as plain white text over the first photo; they restyle it with one of CapCut's text styles.

## Step 6: make it

```
python3 scripts/reel.py make --folder "<edited photos>" --shoot "<shoot name>" \
  --picks 7,2,11+,4,9-,1-,5,12+ --song "<song file>"   (or --capcut-song "<name>", or --song none)
  --pace beat|mixed|calm|build   [--night "<backup>" --shoot-id s1]
  [--hook "the line they picked"] [--song-start 58] [--fit] [--variation 2]
```

- **The reel is named after its shoot.** When you came from the Assistant, pass the backup and shoot id it gave you (`--night`, `--shoot-id`): the CapCut project is then called exactly like the shoot's folder plus "reel" ("2022-06-24 Black-sand beach reel"), and so is the video CapCut exports. Without those, the shoot name goes through their own folder pattern, dated by the first photo. A second reel of the same shoot gets "reel 2". Only use `--name` if they ask for a different name.
- `--pace` is their answer from Step 4 (`beat` is On every beat, `mixed` is A little of everything). The last photo always lands, at least two beats.
- `--variation 2` (3, 4...) gives another mix of the same picks with the same vibe, if they want to see it move differently.
- Wide photos fill the screen by default; `--fit` shows them whole with bars instead.
- `--dry-run` prints the plan and writes nothing.

If the script says CapCut was open, tell them it will appear in their CapCut projects in a moment, and only if it doesn't: "Quit CapCut and open it again." Exit 2 is a stop: say what it printed.

How the timing works, if they ask: the whole reel is worked out at once for its own song and photos, so every cut lands on a whole beat, on the song's stronger hits where there's room; long holds land on the 1 of a bar; every photo stays at least one beat; nothing is left out to fit. The reel starts on the first beat of a bar, and every cut sits on the video frame at or just before its beat, never after, so it never feels late. With a song from CapCut's music, the cuts follow CapCut's own beat marks.

## Step 7: hand it over

Two lines, their words: "It's in CapCut: 2022-06-24 Black-sand beach reel, 10 photos, 12.4 seconds, cut on the beat of Golden Hour. Open it, add your look, and export." If the script named wide photos, add: "Photo 4 is wide, so it's zoomed to fill the screen; slide it in CapCut if anything important is cut off."

Then one next step, as a question with buttons: a carousel from the same picks, or trial reels. **Trial reels** are the same cut with a different opening line: run `make` again with another `--hook` and `--name "<shoot> reel, take 2"`, one project each, in seconds. Remind them once that trial reels go out as trial reels, never to the feed.

## Untested, honestly

Proven on Dustin's Mac with CapCut 9.6: a project written this way opens and exports (Oct 21). The full flow here (sheet, pick, song, beat, project) has run on test photos only. Not yet tried: CapCut versions other than 9.6, Windows (the place CapCut keeps its projects on a PC is written in but has never been tried; nobody has seen CapCut for Windows open a project written this way; reading an MP3 or M4A song on a PC is written, through Windows' own media parts, but has never run on a PC), HEIC photos. The first time on any of these, say "first time on this, tell me if anything looks off" and keep going.

## Parked

The earlier version rendered finished MP4s with ffmpeg (`make_reel.py`, `hooktext.py`, `grade_reel.py`, `beats.py`, `check_setup.py`). Next to CapCut's own looks it read as amateur, so it is parked: the code stays, nothing new is built on it, and you do not use it.
