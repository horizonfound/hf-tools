# First-run test notes, Nov 11, 2026

Dustin's comments while running a first backup from scratch ("backup now", no setup on file). Kept apart from the walk-through itself.

## 1. The "how do you write to clients" question had a button that went nowhere

**What he saw:** the first choice was "Paste me a note you've sent before (Recommended)", and under it "Paste it in the Other box." So he clicked it, then had to click Other as well to get a box to paste into. His words: "a redundant step that didn't work as well as intended."

**Why:** the question box has one place to type or paste, and that is Other. A choice cannot open a box of its own.

**Fixed the same day** in `plugins/the-engine/skills/studio-manager/parts/first-backup-setup.md` (Question 5): the paste choice is gone. The question itself now says "Best is a note you've sent before: click Other and paste it right there. Or pick a tone." and the buttons are only the three tones. One click instead of two.

**Worth a look elsewhere:** any other question whose button tells them to go use Other (the folder-naming question's "I have my own way" asks a follow-up instead, which is fine).

## 2. Seen along the way, not a comment of his

The card in the reader held only video (17 clips, 162 GB, no photos). The instructions' opening line says "photos"; the walk-through said "17 video clips" instead.

## 3. From the second backup on: one glance, one click (Dustin's idea)

**What he said:** the first time is a setup (their voice, where things go, how folders are named). After that those answers almost never change; a backup just makes a new folder in the same place. So the second time they say "backup now", show a short list of the settings to glance at (where it's going, how it's named, and so on) with two buttons: "Looks good" or "Change something". Click the usual and move on, without walking through the questions again.

**Where it stands today:** the instructions already skip the setup questions from the second backup on. They ask "Onto Big Kahuna like usual?", "How many memory cards?" and "What's on the card?". What is missing is his glance list: the settings are not shown, only the drive's name.

**Not built yet.** To settle when building: what is on the list (drive and folder, second copy, folder naming, photo naming, note style?), and whether the cards and "what's on the card" questions stay on that same screen.

## 4. More than one card: get the phone set up before they walk away (Dustin)

**What he said:** when they pick 2 or more cards, they need the phone tap that says "card 1 is safe, pop in card 2". That only works if Claude on their phone is set up and the **Remote Control** switch is on, and it is off by default (it sits in the panel that shows This computer, the folder, main, Remote Control). So at that moment the Assistant should show a quick picture of what to switch on, so the tap can reach them.

**Where it stands today:** the setup guide (Step 6) covers the phone, Remote Control and the two notification settings, but nothing in the backup itself checks or prompts for it. Picking "2" today asks nothing more.

**Not built yet.** To settle when building: ask only the first time they pick more than one card, or every time Remote Control is off; whether the Assistant can tell the switch is off by itself; and the picture (a marked-up screenshot of that panel with the switch circled, plus the phone steps).

## 5. Found along the way: a card that stops answering hangs the walk-away check

The card listed its files fine, then stopped giving up any data: reading the first piece of the first clip never came back (tried by hand too, outside the Assistant). The walk-away check (`night.py --check`) sat on that read for 15 minutes and said nothing, when it should stop and say so.

**To fix:** give the check's read of the card a time limit, and say in plain words: "Your card stopped answering. Take it out, put it back in, and say backup now again. Nothing on it was changed."

Also: this card holds only video (17 clips, 162 GB). A video-only card has never been through a backup; the look, the sorting and the sneak peeks were all built around photos.

## 6. What a video-only card did (17 clips, 162 GB)

The copy and check worked: all files copied and verified in about 5 minutes, and one clip hashed by hand matched the card. Sorting and settling worked: two folders by day, clips renamed with the camera's number kept. The rough edges:

- The contact sheet for the look was blank (five empty rows), since no preview is made for a video. The shoots were split by day alone and both got the stand-in name "Video clips".
- The backup's lines call clips "photos" ("2 photos", "0 photos, 0 moments").
- The sneak-peek step stopped and asked for picks with nothing to pick from; it had to be skipped by hand (`--no-peeks`). It should skip itself when a shoot has no photos.
- The reel side can already make stills from video on a Mac (`video.py`); the backup's look could use the same to show one frame per clip.

## 7. Video and photos on the same card (Dustin, looking at the report)

**What he said:** he had never thought about a card with both. Photographers often shoot behind-the-scenes clips, so it needs thinking through. On the report this card's clips show as "17 photos", "6 photos", "11 photos", with an empty space where the previews go.

**What this run showed:** a clip is treated exactly like a photo. It is counted as a photo, grouped by its time, renamed and filed into the shoot's folder. No preview is made for it, so the picture spot is blank. Not yet tried: a card with both, where clips would land among the photos of the shoot they were taken during.

**To decide (Dustin and Nicole):**
- Words: "17 clips", and "212 photos and 6 clips" on a mixed shoot.
- Where clips go: in the shoot's folder beside the photos, or in a "Video" folder inside it.
- What the report shows for a clip: one still frame with a small play mark (the reel side can already pull stills from video on a Mac; not on a PC yet).
- Sneak peeks stay photos only; a shoot with no photos skips them.
- The handoff: clips filed with a shoot are the natural source for "Look through my footage" on the reel page.

## 8. Decided and built: video clips get their own folder (Dustin, Nov 11, evening)

Dustin's call after note 7: "definitely want a video folder to keep them separate. In instances where there's photo and video, 2 folders, 1 'photos' and 1 'videos'. Everything else you suggested sounds good."

Built the same evening:

- **Folders.** A shoot with photos and clips gets a Photos folder and a Videos folder inside its own. Each is numbered from 0001 in shooting order, so a clip never takes a photo's number. A photo's sidecar stays beside its photo.
- **One kind only stays flat (Dustin confirmed, Nov 11: "No, keep it flat").** A shoot of only photos is one folder with the photos right in it, as before. A shoot of only clips is also one folder, with no Videos folder inside.
- **Words.** A clip is never called a photo. The report, the rows the backup prints, the editing queue and "your shoots" all say "212 photos and 6 clips".
- **Pictures.** A shoot of only clips shows one still from each of three clips, with a play mark. Made on a Mac with nothing installed. On a PC there are no stills yet, so it shows a plain line instead.
- **Sneak peeks.** Photos only. A shoot of only clips is skipped, and a card of only clips no longer stops to ask for picks.
- **Renaming** carries both folders, and so does the last step that moves the shoots into place.

Checked:

- `tests/clips_check.py`: 33 checks on two pretend cards (photos with clips, and clips only), on both Pythons. Whole backup, rename there and back, a rename cut off part way, the settle, the card untouched, every file byte for byte.
- The older tests still pass: `pc_smoke.py`, `backup_safety.py`, `look_check.py`, `skill_text_check.py`.
- Today's real report was rebuilt: it says "17 clips" and shows stills from the real clips.

Not tried:

- A real card with photos and clips together. Only pretend cards so far.
- Any of it on a PC.

Found along the way, not fixed:

- **A clip whose date cannot be read is set aside in the hidden records folder**, like any undated file. The date reader only looks at the first part of a file, and some cameras and all phones can write a clip's date at the end. The clip is safe and the report counts it as set aside, but the photographer would not find it in the shoot. Worth fixing before beta.
- **The hand-off to "Look through my footage"** is not wired: a post kit does not yet know about the Videos folder from the backup.
- **The second copy** is untouched by this, as decided Oct 28: it stays as the card wrote it.

## 9. Stills stand upright (Dustin, Nov 11, late)

Dustin: "they need to be upright for sure because the previews that I'm looking at, they are sideways... analyze the clip. If there's a person, you're going to be able to identify it and then rotate it accordingly."

Built. Only the still is turned, the Assistant's own small picture. The clip file is never changed.

- **How it decides.** The Mac's own face and body finder looks at the still, with nothing installed. A face tipped a quarter turn means the camera was on its side, so the still is turned to match.
- **Nobody in the middle of the clip.** It looks at two other moments in the same clip for a person.
- **Still nobody.** It takes the turn of the nearest clip in the same stretch of shooting where a person was found. If there is none, the still is left as it is, never turned on a guess.
- **On today's real clips:** 8 of 11 stills needed a turn. 6 were decided by the person in them, 2 by the clip beside them (an empty chair, and a back to the camera). All 11 are upright on the report now.
- **Not done:** nothing on a PC (no stills there at all yet). A clip with no people anywhere near it, like a landscape filmed sideways, stays sideways.
- **Open, for Dustin and Nicole:** the reel page's own footage stills and the CapCut project do not use this yet, so a sideways clip is still sideways there. Whether a reel should turn such a clip is a bigger question, since that changes how the video plays.

Small things seen on the video-only report, not fixed: the box under the shoots still says "Where your photos are" and "Open photo folder", and the camera line says "unknown".

## 10. Clips named for what happens in them (Dustin, Nov 11, late)

Dustin: "be a little bit smarter than that. Look at a frame in the beginning, the middle, and the end, and try to figure out what's going on, and then use that information to name what the clip is. Depending on how labor intensive that ends up being."

Built. Not labor intensive: 22 seconds for all 17 real clips, and two pages for Claude to read.

- **The clip pages.** For every group of only clips, the backup takes three frames from each clip (near the start, the middle, near the end), turns them upright, and lays them out a dozen clips to a page. Claude reads the pages at the same moment it reads the contact sheet, and names each shoot of clips for what is going on and where.
- **What it showed on the real card.** One still per clip said "a person talking outdoors" and "a person talking indoors". Three frames said: Sep 13 is a lighting demo outdoors, with a white umbrella and a reflector. Oct 29 is sit-down talking takes in a green chair in front of shelves, in five outfits, each clip starting and ending on the empty chair.
- **Limits.** It names the shoot of clips, not each clip one by one. It goes by what is on screen, never the sound, so it cannot know the topic. Never a person's name unless the photographer said it. At most 96 clips are shown per card, spread evenly. A Mac only for now.
- **My reading of "name what the clip is":** the folder and the name every clip in it carries. If each clip should get its own name, that is a different job; say so.
- **Checked:** `tests/clips_check.py` now also checks the page is made and offered at the look.
- **Words (Dustin):** "talking takes" is a weird way to say it. A person talking to the lens is "direct to camera" or a "talking head". In the instructions now.
- **More words (Dustin):** a third-person view of someone doing something, like a clip of Nicole photographing a family, is "behind the scenes" or "B-roll", as opposed to direct to camera. In the instructions now.

## 11. The preview is a good moment, not just the middle (Dustin, Nov 11, late)

Dustin: the big preview on shoot 2 was "literally a shot of Nicole holding a red cup, staring down. It's not flattering at all. The clip should at least look semi-decent... even if you have to pick a different clip that's somewhere else in the timeline where they're not blinking or looking unflattering."

Built.

- **Nine moments, not one.** For each clip that gets a preview, nine moments across the clip are looked at small. The one where the face makes the best picture is kept. The score is the Mac's own face score, with nothing installed: eyes shut, looking down or a hidden face score low.
- **Nobody in any of them:** the middle of the clip, as before.
- **The report leads with the best.** Of a shoot's clip previews, the three best faces are shown, the best one biggest.
- **On the real clips:** the red-cup clip's preview moved from the middle to 24 seconds in, where the face is to the camera. All 10 clips with a person now show an open-eyed face. The eleventh is an empty chair from start to end.
- **Cost:** about 2 seconds a clip. 24 seconds to redo all 11 real previews.
- **Limits:** it is a score for a clear, open-eyed, camera-facing face, not taste. It cannot tell a nice expression from an odd one that is sharp and facing the lens. A Mac only. The clip pages Claude reads for naming are unchanged: those show the start, middle and end on purpose.

## 12. "Video clips", a click that plays, and a way to every clip (Dustin, Nov 11, late)

Dustin said yes to all four:

- **"Video clips", not "clips".** His ear: "video clips sounds better than clips by itself." Every count now reads "212 photos and 6 video clips". One line in `clips.py`. The folder is still called Videos.
- **A click plays the clip.** A preview with a play mark now plays that clip in the computer's own video player (QuickTime on a Mac). Before, it only showed a bigger picture. The line under the pictures says what happened.
- **"See all 11 video clips"** under the pictures opens the folder the clips are in: the Videos folder for a shoot with both, the shoot's folder otherwise.
- **Button words.** On a card of only clips the box says "Where your video clips are" and "Open video folder". With both, "Where your photos and video clips are".

Safety: the page never sends a place on the drive. A clip must be one the backup's records list, and the folder is worked out from the records. Anything else is refused.

Checked: `tests/clips_check.py` (50 checks, both Pythons; the player and the folder window are swapped for a recorder, so nothing opens during a test). By hand in the pane on the real report: a click on a preview played the real clip in QuickTime. Not tried: a PC; the See all link by hand.

## 13. Two fixes from the list (Dustin: "Yes, both", Nov 11, late)

**A card that stops answering (note 5).** The first read of the card is now made by a small program of its own with a 30 second limit. If the card does not answer, the backup stops before copying anything and says: "Your memory card has stopped answering. Nothing was copied and nothing on it was changed. Take the card out, put it back in, and say go." Before, the check waited in silence with no end.

- Covers the check they wait for, and the start of the backup itself.
- **Not covered:** a card that goes quiet in the middle of a long copy, after they have walked away. That still waits. It needs its own care, since it sits inside the copy-and-check step.
- The same could happen while the card is first being found (`studio_file.py cards`). Not covered either.

**Video clips with no readable date (found in note 8).** I had the cause slightly wrong there. The quick date reader does look at the end of a file, but it cannot make sense of a header that starts before the last part it reads, which is what a long phone clip has. Now a clip with no date gets one from the video reader, which finds the header wherever it is. If the header holds no date at all, the clip takes the file's own time, which the camera set and the backup kept. Either way the clip is sorted into its shoot instead of being set aside out of sight. The record says where the date came from.

- Photos with no date are unchanged: still set aside, as before.

Checked: `tests/clips_check.py`, now 58 checks, both Pythons. A stand-in card reader that never answers is given up on in 2 seconds in the test; a real quiet card has not been seen since. Two made-up clips, one with its header at the end of a big file and one with no date, both get a date.

## 14. The glance screen, built (note 3; Dustin: "just keep going and do it", Nov 11, late)

From the second backup on, the every-backup screen opens with the usual, right there to glance at.

- **In the chat, before the question:** "Here's how I'll do it, same as last time:" and a few short lines. On Dustin's Mac they read: Photos go onto Big Kahuna. No second copy. Folders named like "Smith Family, Oct 18 2026". Photos named after the shoot, with the camera's number kept. Client notes written the way you write, signed "Dustin / Horizon Found". Posts lined up at 3 a week.
- **The question:** "Same as usual?" with the same settings in one line, so they are in view even when only the question is on screen. Buttons: "Looks good" and "Change something".
- **Change something:** one question, "What would you like to change?", then just that one setup question again. Never the whole setup. A different drive asks "just this time, or from now on?"
- It replaces "Onto Big Kahuna like usual?". The other two questions on that screen are unchanged: how many cards, and what's on the card.
- The lines come from `studio_file.py glance`.

Checked: `tests/glance_check.py`, 6 checks on a pretend setup, both Pythons. **Not tried:** a real second backup with it, which is the real test of how it reads.

Also done in the same go: the two real video shoots are renamed "Garden lighting demo" and "Green chair, direct to camera" (17 clips, every one checked as the same file), and the day's work was committed.

Still open from this test: phone setup when there is more than one card (note 4), a card going quiet mid-copy (note 13), the reel page picking up the Videos folder, and anything on a PC.
