---
name: assistant-make-a-reel
description: The Assistant by Horizon Found, the reel. Turns a photographer's edited, exported photos into a CapCut project cut on the beat of their song, with Claude picking and ordering the photos, ready for them to style and export in CapCut. Use this whenever the person says make a reel, turn these into a reel, reel from the beach shoot, pick my reel photos for a shoot, look through my footage for a shoot, yes to "want a reel?", cut these to a song, or trial reels from this shoot, even if they do not name the Assistant.
---

# Make a reel

This is part of what the Assistant does, after the edit. The photographer has exported their edited photos; you pick the strongest ones and put them in an order that flows. **The reel page** beside the chat does the rest with them (Nicole's reel maker): they move the photos if they want, add their song, pick the vibe and press **Make my reel**, and the page lays the photos on the beat of the song as a new CapCut project. They open CapCut, add their look (a text style, a filter, a template), and export. You save them the hour of choosing and cutting. You never make the look, and nothing posts.

**The song and the vibe are asked on the page, never in the chat.** Your part is the pick (Step 2) and opening the page. Don't ask "which song?" or "how should it move?" in the chat; the page asks both, in Nicole's words, with the songs they dropped in and the four vibes as buttons.

Talk the way the Assistant talks: short, plain words, the result first, one question at a time with buttons (the likely answer first, marked recommended) and the Other box always there. The photographer is "you" or "they", never "she" or "he". No file names in code styling, no settings talk.

Paths here, written once so they work from any folder: `<reel scripts>` is the `scripts` folder beside this file (`${CLAUDE_SKILL_DIR}/scripts`), `<assistant scripts>` is the Assistant's scripts (`${CLAUDE_SKILL_DIR}/../studio-manager/scripts`), `<assistant>` is the Assistant's own folder (`${CLAUDE_SKILL_DIR}/../studio-manager`, where its `parts` are), and `<shared>` is the plugin's shared folder (`${CLAUDE_SKILL_DIR}/../../shared`). The working folder is the photographer's project, so a bare `scripts/reel.py` would not be found: always write the whole path. Nothing has to be installed on a Mac: the song is read with the Mac's own tools and everything else is plain Python. **On a Windows PC,** read the Assistant's `<assistant>/parts/on-a-pc.md` first (once per conversation; its section "The reel" is this skill's): reading a song and CapCut have never been tried on a PC, and it says what to say when they don't work yet.

## The rules

1. **Edited photos only.** A reel is made from the photos they exported after editing, never from the backup's raw files. If all you have is a backup, say "Whenever you're finished with your edits, let me know and I'll turn your favorites into a reel."
2. **Every frame is theirs.** Hard cuts on the beat. No transitions, no effects, no zooms or motion, no generated anything. Their look comes from CapCut.
3. **Always a new CapCut project.** Never open, change or overwrite one they made. The script will not.
4. **CapCut can stay open** (on a Mac). If it is open, the script writes only the new project's folder and CapCut adds it to its projects by itself; if it is closed, the project is added to CapCut's list for next time. Never ask them to quit CapCut unless the new project doesn't show up. **On a PC, a reel made while CapCut is open waits** to be added to CapCut's list. If the output ends with "NOTE: once CapCut is closed, `capcut.py open` adds the waiting reel...", ask them to close CapCut, then run `python3 <reel scripts>/capcut.py open`, which adds the reel to CapCut's list and starts CapCut. (The same line can appear on either computer when CapCut's list couldn't be saved; the answer is the same.) `python3 <reel scripts>/capcut.py open` also just starts CapCut, on either computer, whenever they want it open.
5. **One look at the sheet, not photo by photo.** The contact sheet is how you see the shoot and the strip is how you check the order. Open a single photo larger only to settle a close call, and never more than a handful.
6. **Nothing posts, nothing sends.**
7. **Nothing is ever left out to fit** (Nicole, Nov 6): not a photo, not a clip. A vibe bends to fit the song; the photos and clips don't. When even the quickest timing can't fit, nothing is made and the page says exactly why.

## Step 1: the edited photos, in a post kit

Usually you arrive here from the Assistant: they said "I'm done with the beach shoot," it found the export folder and they confirmed it. Use that folder. If they came straight here, ask which shoot; the Assistant's `find_exports.py` finds the folder (see its skill), or they tell you where it is. A folder of favorites or selects they made themselves is even better: use that.

**Every reel is made from a post kit,** because the reel page belongs to one. Find out whether the shoot has one: it has when you came here from one, or when `python3 <assistant scripts>/kit.py show "<shoot name>"` finds it (that prints STOP when there is none). **No post kit yet:** make one now. It is only a folder in Your Content that points at their photos; nothing is moved or copied:

```
python3 <assistant scripts>/kit.py start --folder "<edited photos>" --name "<shoot name>"
python3 <assistant scripts>/kit.py start --night "<backup>" --shoot s1          (a shoot the Assistant backed up)
```

If that stops because the Assistant folder isn't set up yet, set it up first (`<assistant>/parts/photos-in.md`, "set up my Assistant folder"), then start the kit. Don't write the kit's captions or make its other pieces here unless they asked for posts; a reel needs only the kit.

Then number the photos through the kit, so your numbers and the page's are the same:

```
python3 <assistant scripts>/kit.py sheet "<kit>"
```

It runs this skill's sheet on the kit's own photos and keeps the list with the kit. From here on `--folder` is the kit's photos (the folder `kit.py show` names on its Photos line, after "in") and `--shoot` is the kit's name as `kit.py show` prints it. Never run `reel.py sheet` on some other folder under the same shoot name: that numbers the photos differently, and numbers you picked would point at other photos on the page. Read the sheet image(s); their photo folder is not changed.

## Step 2: curate the set (your main job), and put it on the page

Read `<shared>/curating.md` first, every time, and choose the way it says. **What goes in is Nicole's rule (Nov 6): the best photos, on their own merit**: the most engaging, the ones that tell the best story, variety, emotion, and the ones that help tell the story the photographer is trying to tell. Similar photos are fine when together they tell a story; leave out the same expression a fraction of a second later. Find the stories in the shoot, shortlist the strongest frames for each, and settle the close calls side by side (the strip below, with just the group as its picks, `--picks 7,8,9`, draws them in a row; open a photo larger only when the strip can't settle it, a handful at most). If `reel_page.py show "<kit>"` prints their notes or how it should feel, those steer which of the best photos lead.

**The order is the Assistant's flow rules** (curating.md): open on the scroll-stopper; move between wides, mediums, close-ups and details, never three of one distance in a row; change one thing at a time from photo to photo (light, color, distance, direction), so every cut feels like the natural next one; let color and light travel somewhere instead of bouncing; let the emotion build, then come back down; no near-twins side by side, except a run kept because it tells a story; close on a quiet, final frame. For a reel, add one more: **tall photos first**, since the screen is tall and a wide photo loses its sides (one or two wide ones are fine if the subject sits near the middle). **About 8 to 14 photos is a guide, not a rule:** the shoot's best photos and its stories decide.

While you order them, mark how long each one deserves: a `+` after a number to linger on it (the emotional peaks, a wide with a lot to take in, the closer), a `-` to pass quickly (a detail in a run). Most photos get no mark. The marks count in every vibe, in the page's words: "Longer stays on screen about twice as long", "Quicker gets the shortest time, one beat". On the page they show as Longer and Quicker on each photo, and they can change them there.

Then check your order as it will play:

```
python3 <reel scripts>/reel.py strip --folder "<edited photos>" --shoot "<shoot name>" --picks 7,2,11+,4,9-,1-,5,12+
```

Read the strip left to right. Fix any jolt (swap two neighbors, move a detail in as a breather, drop the one that fights) and draw it again if you changed anything.

**Save the pick and open the page:**

```
python3 <assistant scripts>/kit.py picks "<kit>" --reel 7,2,11+,4,9-,1-,5,12+
python3 <assistant scripts>/reel_page.py open "<kit>"
```

The second prints the page's address on its last line. Load it in the Claude app's browser pane and bring the pane forward (`mcp__ccd_view__show_pane`, pane `preview`); never Chrome. Then say it short, in one or two lines: "My pick for the reel is on the page beside us: 12 photos, in the order they'll play. Opens wide on the beach, moves in to the two of them, ends on the walk away. Choose Just photos (or add your footage), move anything you like, add your song, and press Make my reel." Add one line for what was left out and why ("Left out 8 and 9, the same laugh a moment after 7"). There is no question to ask: the page asks the rest. Their own order is always kept on the page; yours never replaces it.

**"Pick my reel photos for the beach shoot"** is what the page tells them to say when you haven't picked yet (or they want a fresh pick). Do Steps 1 and 2 the same way and save it with `kit.py picks --reel`; a page that is already open shows the new pick by itself within a few seconds while "Let my assistant choose" is on (if it hasn't, load its address in the pane again). If they are on "I'll drag them in myself", their own order stays on the screen and yours is under "Let my assistant choose"; say so in a few words. Then the one line on how it flows, and nothing else.

If they would rather say a change than drag it ("swap 3 for 5", "start with the couple"), do it their way with `kit.py picks` again, and mention once if it now puts near-twins or three close-ups together. More about the page, and what to do when a line starting ARRANGED comes up, is in the Assistant's `<assistant>/parts/arrange.md`.

## Behind-the-scenes footage: "Look through my footage for <shoot>"

The reel page's step 1 ("Behind-the-scenes footage?") gives them a line with a Copy button once their videos are in the shoot's Footage folder: **"Look through my footage for <shoot>"**, with **" and follow my notes"** on the end when they wrote in "Want to direct the reel?" or picked how it should feel. When they paste it, you find the best moments in their videos and save them as cards on the page. They then select the clips each style uses and press Make my reel themselves.

**The rules (Nicole, Nov 6, from her SELECTS.md):**

1. **The photos are the point, with footage too.** The footage only adds behind-the-scenes moments between them. The photos are the reel's photo pick, the same with footage or without, chosen on their own merit by Step 2. **Never choose, leave out or move a photo because of a clip, and never limit the photos to the setting the footage shows** (her first behind-the-scenes order did that and lost the strongest photos). If the shoot has no reel pick yet, do Step 2 first.
2. **Find the best moments, up to 12, fewer is fine:** engaging (something is happening), interesting, real reactions (laughing, a client seeing the back of the camera and loving it), the photographer and the clients looking good on screen.
3. **Judge each moment on how it looks.** There are no banned kinds of moment. Nicole's notes on her first picks were about those particular clips, not rules: someone walking back to the camera looking bad, a dog running past that has nothing to do with the shoot. Ask every time: is this one of the best-looking, most engaging spots in this footage?
4. **Their notes come first.** Find what they described in "Want to direct the reel?" before anything else, keep those moments in the order they describe, and always include them. If one can't be found, say so plainly. Never invent one.
5. **The feel steers the moments, not the photos.** Tender moments for Heartwarming, the funny bits for Fun, their own words when they typed something else. Notes or a feel written after your photo pick don't mean redoing Step 2 for the footage look: the photos stay the reel's photo pick (rule 1). Only when they ask for a fresh pick ("pick my reel photos for <shoot>") does Step 2 run again, and it reads the feel then. How a feel turns into picks is your judgment, not Nicole's rule; when it's unclear, ask them.
6. **Matching a photo is never the goal.** Only The reveal uses a moment that shows a finished photo being taken. Give a moment a photo only when it is obvious (same pose, same setting, an angle that agrees with where the photographer stood; check with a close look and `--photo`). A wrong match is worse than none.
7. **Loudness is a hint for where to look,** never a reason to pick. A loud stretch is often a laugh or a cheer, and often not.
8. **Each moment is 3 to 4 seconds,** starting where the good part starts. The first one never under 3 seconds. They can make one longer or shorter on the page.
9. **The labels are what happens, in plain words** ("Showing them the back of the camera"). Never a name, an occasion or anything else the photographer didn't tell you.

**The steps.** The script is the Assistant's `footage.py` (in `<assistant scripts>`). Scripts take the stills and draw the sheets; you look only at the sheets, never at frames one by one (this skill's rule 5: one look at the sheet).

1. **Scan.** `python3 <assistant scripts>/footage.py scan "<kit>"`. It prints their notes and their feel first, then the rules, then each video: its key, its length and shape, when it was recorded, its contact sheets (a still every second for a video up to 2 minutes, every 2 seconds up to 10, more apart for longer ones; tall cells 7 across for a phone video), its loudest moments, and the finished photos taken while it was recording. Every look goes in a new folder of its own; nothing an earlier look made is changed. It stops with "there's no footage yet" when the Footage folder is empty: tell them to drag their videos in with Add my footage on the page, then paste the line again. Exit 3 means no sheets could be made on this computer (a PC): see `<assistant>/parts/on-a-pc.md`.
   **It can take minutes** (a 7-minute phone video is a few hundred stills): run it with a 10-minute limit on the command (a timeout of 600000 ms), or in the background and wait for it to finish; never read a look that was cut off. It prints a line as it starts each video. If it says it is waiting for another video to be got ready (a preview the reel page is making), let it wait. A video still being copied into the Footage folder is left out and named: tell them to paste the line again once the copy is done. If a video says "I ran out of time on this video from 2:40", the look of that video stops there: take the rest with close looks from that time (step 3), or run the scan again.
2. **Read every sheet once** with the Read tool, in order. Each still is labelled with its time.
3. **A close look only at the promising stretches,** a handful at most: `python3 <assistant scripts>/footage.py close "<kit>" <key> <from> <to>` gives a still every half second (`--every 1` for a longer stretch; at most 48 stills a look). Give it the same 10-minute limit: it waits its turn behind any preview the reel page is making. Add `--photo N` to put finished photo N first, only to check a match for The reveal. For scale: Nicole's 7-minute video took 15 sheets and about 9 close looks; a few short clips take a sheet or two each and maybe two close looks.
4. **Choose the moments** by the rules above.
5. **Save them** with a small file you write in your own scratch folder (never in their folders):

   ```
   {"moments": [{"video": "<the key the scan printed>", "start": 42.0, "end": 46.0, "label": "Laughing at the wave", "photo": null}, ...]}
   python3 <assistant scripts>/footage.py moments "<kit>" --file <that file>
   ```

   Times are seconds or minutes and seconds ("0:42"). Leave "order" out: the page uses the reel's photo pick, which is right (the first footage rule above). It refuses, in plain words and writing nothing, more than 12 moments, a moment under 3 or over 4 seconds (a video shorter than 3 seconds may be used whole, never first), a moment past the end of its video, a video it doesn't know and a photo not on the list: fix the file and run it again. **Never write the moments into the reel page's records any other way.** Their own moments (from Use this moment) stay first, and a clip they had already selected for a style is carried over when you save the same moment again.
6. **The page shows the moments by itself** within a few seconds, under "Select your clips". Don't reload it. Tell them in plain words, with times, in a few lines: "I found 5 moments: lining up the shot at 0:12, the laugh when they saw the back of the camera at 1:40, ... They're on the page under Select your clips. Pick a style, select the clips you want, and press Make my reel." If something in their notes wasn't there, say so plainly ("I couldn't find the sparkler exit in these videos."). Nothing more: the page asks the rest.

What is said in the footage can't be heard yet (there is no speech-to-text here), so a moment chosen for what someone says is out of reach; say so if they ask for one.

## Step 3: the song (on the page)

The page asks it: "Add your song". **Add my music** makes a Music folder for this shoot and opens it; they drag a song in (or a screen recording of a song playing: the page takes the sound from it once and keeps it beside the recording, or in the Music folder when the recording is in a folder of theirs outside Your Content). The page sees a new file by itself and says "Got it: <name>." **No song** is there too, with Nicole's line for business accounts. You don't ask which song, and you don't pick one.

What you still do, only when they bring it up:

- **"Where do I get the song?"** A song file they bought or downloaded works (Artlist, Epidemic Sound, Musicbed and the like cover social posts). Songs bought or streamed in Apple Music are locked and cannot be read; say so plainly and suggest a downloaded song, a screen recording, or No song. **Never move, rename or tidy their recording or their song, and never save a song into Music, Downloads, Desktop or Documents yourself** (Nicole's first reel, Nov 5: CapCut showed "File not accessible"). The page's own Music folder is the place.
- **They ask for a song from CapCut's own music** (the page doesn't offer these; Nicole left them off). Run `python3 <reel scripts>/reel.py songs`: it lists the CapCut songs in their CapCut projects (C1, C2...). Offer those by name as buttons. If the one they want isn't there: "Pick it in CapCut: start a new project, add the song from CapCut's music, then quit CapCut and tell me." The first time (the list says "License note: not shown yet"), tell them once, plainly, before making anything: "CapCut's own songs come with CapCut's license: its regular songs are for personal, non-commercial posts, and its commercial songs are cleared for businesses only on CapCut and TikTok, not Instagram. Your call." [Use it anyway] [Pick a different song]. On "Use it anyway", `python3 <reel scripts>/reel.py capcut-ok`. Then make it from the chat (Step 6, with `--capcut-song "<song name>"`): the song goes into the new project exactly as CapCut saved it, with CapCut's own beat marks.

**The song travels inside the CapCut project.** The reel step puts its own checked copy of the song in the project's folder and points CapCut at that copy, so nothing done to the original later can break the reel. Never hand-edit a project's song path, and never move a song "to fix" a reel: make the reel again.

## Step 4: the vibe (on the page)

The page asks it too, in Nicole's words: "Pick the vibe", with **On every beat** (recommended), **A little of everything**, **Calm** and **Build**. You never ask it in the chat and never pick for them. How it works, if they ask:

- **Every cut on a whole beat, every photo at least one beat (Nicole, Nov 6).** No half-beat cuts, ever: Quicker is the shortest, one beat; no photo is on screen for less than about half a second (on a very fast song the shortest becomes two beats); the last photo always gets at least two beats. **Never write your own script to cut faster or on half beats.** Every cut comes from `reel.py make`, which the page runs.
- **The same choices again give another mix.** Pressing Make my reel again with the same photos and vibe makes a new version that moves a little differently ("... reel 2"); none of the vibes is a fixed template.
- **"Too slow", "faster", "more energy"** (Nicole's first reel, Nov 5): pick On every beat on the page and press Make my reel again; that is the one she said "Yes, that's it" to. If it is still too slow, the song is slow: say so and suggest a quicker song, or more photos.
- **Nothing is left out to fit a vibe.** On a short song the page keeps every photo, makes the vibe quicker and says so in its own box ("Your song is only 15 seconds, so I kept all 14 photos..."). When even one beat a photo can't fit, nothing is made and the page says exactly why, under "Your song is a little short for this". If they ask you about it, say it in those words, never as an error, and ask which they'd like: a longer song, or a few photos out.

## Step 5: words on the first photo, and trial reels (only if they ask)

The page has neither, and you don't offer them. If they ask for words on the first photo, write five short options in their voice (their Brand File's Voice section if they have one). Rules from Nicole: it speaks to their client about what the client feels and wants, never about how the photographer works; one short line, readable in a second; a real angle only this photographer would say; never invent a name, date, price or offer. They pick one; make it from the chat (Step 6) with `--hook "<the line they picked>"`. It goes in as plain white text over the first photo; they restyle it with one of CapCut's text styles.

**Trial reels**, if they ask, are the same cut with a different opening line: make it from the chat with another `--hook` and `--name "<the kit's folder name> reel, take 2"`, one CapCut project each. Remind them once that trial reels go out as trial reels, never to the feed.

## Step 6: make it

**They press Make my reel on the page.** The page makes it there and then (a few seconds), shows "It's in CapCut: <project>" with an **Open CapCut** button, the plan in a line, and anything to know (a wide photo, a short song). The reel is named after the kit's folder ("2026-06-24 Beach reel"); a second one is "... reel 2". Nothing waits on you.

**Making it from the chat**, only for what the page can't do (a song from CapCut's music, words on the first photo, a trial reel) or when the page says "Ask your assistant to make the reel instead" or can't reach its server:

```
python3 <assistant scripts>/reel_page.py show "<kit>"          the order, song and vibe on the page
python3 <assistant scripts>/reel_page.py make "<kit>" [--capcut-song "<name>"] [--hook "<line>"] [--name "<name>"] [--no-song] [--dry-run]
```

`make` uses exactly what the page would: the order on it (theirs or yours, with Longer and Quicker), the song they picked there and the vibe they picked there (On every beat if they haven't picked one), and makes the reel the same way, one at a time. It stops when no song is picked on the page yet (unless it is a CapCut song): the song is still theirs to pick on the page, so say "Add your song on the page beside us, or pick No song, then tell me." and make it once they have; pass `--no-song` only when they have said no song. Its last line is "Made: <the CapCut project>". Exit 1 or 2 is a stop: say what it printed, in its words.

**Behind-the-scenes footage is on the page** (step 1, "Behind-the-scenes footage?", and step 4, the style): they add their videos there, pick their own moments with Use this moment, select the clips for the style, and press Make my reel; the page puts the clips among the photos the way the style says. `reel_page.py make` from the chat does the same when footage is on there (the style and the clips selected on the page). The footage look ("Look through my footage for <shoot>") is the section "Behind-the-scenes footage" above. Only if they want clips in a reel and can't use the page, make it with this skill's `reel.py make`, using what `reel_page.py show` prints: `python3 <reel scripts>/reel.py make --folder "<the kit's photos>" --shoot "<kit name>" --kit "<kit folder>" --picks c1,7,2,c2,11-,4 --pace <the vibe show printed: beat for On every beat, mixed for A little of everything, calm, build> --song "<the song file show named, in the kit's Music or Photos folder>" (or --song none) --clips clips.json`. The clips file is a list of the moments, each `{"path": the video, "src": seconds into the video where the moment starts, "seconds": how long its card is, "w": the video's width, "h": its height, "length": the whole video's length in seconds}`, placed in `--picks` as `c1`, `c2`... by their place in the list. Each clip plays once, so the same moment twice is two entries. A clip runs whole beats, never longer than its card or past the end of its video; with a song the clips are muted, with no song they keep their own sound. If anything in the file is missing or can't be right, the script stops and says what in plain words: never guess a size or a length.

If the page or the script says CapCut was open, the reel appears in their CapCut projects in a moment; only if it doesn't: "Quit CapCut and open it again."

How the timing works, if they ask: the whole reel is worked out at once for its own song and photos, so every cut lands on a whole beat, on the song's stronger hits where there's room; long holds land on the 1 of a bar; every photo stays at least one beat; nothing is left out to fit. The reel starts on the first beat of a bar, and every cut sits on the video frame at or just before its beat, never after, so it never feels late. With a song from CapCut's music, the cuts follow CapCut's own beat marks.

## Step 7: after it's made

The page has already told them it's in CapCut and given them the Open CapCut button, so don't say it again. When they next come back to the chat (or when you made it from the chat), check with `reel_page.py show "<kit>"` (its "Reels made" line) and record it once: `python3 <assistant scripts>/home.py did reel --note "made the beach reel"`. If you made it from the chat, two lines in their words: "It's in CapCut: 2026-06-24 Beach reel, 10 photos, 12.4 seconds, cut on the beat of Golden Hour. Open it, add your look, and export." and, if the script named wide photos, "Photo 4 is wide, so it's zoomed to fill the screen; slide it in CapCut if anything important is cut off." (With clips the script counts by place in the reel, clips included: "The 5th one in the reel is wide...".) A reel already in CapCut is never changed: a new order or a new vibe always makes a new project beside it.

## Untested, honestly

Proven on Dustin's Mac with CapCut 9.6: a project written this way opens and exports (Oct 21). The full flow here (sheet, pick, song, beat, project) has run on test photos only. Not yet tried: CapCut versions other than 9.6, Windows (the place CapCut keeps its projects on a PC is written in but has never been tried; nobody has seen CapCut for Windows open a project written this way; reading an MP3 or M4A song on a PC is written, through Windows' own media parts, but has never run on a PC), HEIC photos. The first time on any of these, say "first time on this, tell me if anything looks off" and keep going.

## Parked

The earlier version rendered finished MP4s with ffmpeg (`make_reel.py`, `hooktext.py`, `grade_reel.py`, `beats.py`, `check_setup.py`). Next to CapCut's own looks it read as amateur, so it is parked: the code stays, nothing new is built on it, and you do not use it.
