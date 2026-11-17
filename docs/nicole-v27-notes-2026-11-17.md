# Nicole's v27: what differs from hers, and the questions (Nov 17, 2026; a draft, not sent: rule 10)

We built your v27 on branch `v27`: the reel page, the carousel and stories designer, the talking reel, the post kit, the words page, the posting queue, the path at the top, Remove this song and the Make posts screen. Every word of yours on a page is yours (the tests compare them with your pages both ways); the behaviour is built from your screenshots; underneath it is ours. This is the list of where ours differs from yours, her faults we fixed rather than copied, the lines we had to write where you had none (all drafts for you to reword), the questions, and a short list of rough edges we know about and have not fixed.

## Different from yours, on purpose

**Reel page**

- **Save my video draws the words with the Mac's own text engine, not Pillow,** and lays them over the video with the Mac's own video tools (nothing installed). The words match the page: the same font faces, 66 px times the size, wrapped at the same width, and **one box a line, as your screenshot 18**. The video is made by a job the page follows (yours waited on one request for up to 30 minutes), held to 15 minutes; the free name is chosen before rendering; a song shorter than the reel fades out where it ends (yours faded at the reel's end, in silence). Only a B-roll reel can be saved whole (yours answered any reel). The clips' own sound is kept with no song, left out with one (as yours).
- **The path at the top** is built on the server from the shoot's name (yours in crumbs.js from the address, with your home's address and port written in); every link is a path of the page's own server.
- **Photo numbers stay fixed when photos are added** (new ones at the end, a removed photo's number never reused), for the reel, the carousel picker, the designer and the stories alike (yours numbered the kept photos again from 1).
- **A reel remembers its kind,** and switching under Your reels reopens each reel as its kind (yours kept the address's kind and hid the wrong steps). A reel from before v27 opens as Behind the scenes when footage was on, Just photos when off, the chooser when nothing was chosen.
- **The footage editor:** one zoom threshold (60 s) for Start here and for a picked clip (yours 60 and 90); after a reload the trim is drawn dashed from their newest clip of that video (yours lost it); × on a card whose clip is in the editor clears the trim too; the video is swapped by key; the ruler's times are rounded; the Name my clips line is DM Sans (yours Fraunces, which Dustin took off every page). Your v25 Trim panel is off the page (its code kept behind one switch).
- **Naming clips:** labels only, up to 80 letters, "about" refused (you took the description out); each `picks` run goes in a fresh folder (yours wrote one clip's sheet over another's); `describe` writes the record itself (yours posted to your page server).
- **The watch step:** the preview runs in a folder of its own, one at a time per shoot and held to 30 seconds; photos by number and clips by key on the wire (yours sent paths); the watched start is sent back to the make every time and floored to the millisecond; a start past the song's end is refused in plain words.
- **Direct this edit:** `reel_page.py direct` sets the style, the clips and the order in one save (you named no command); the box saves only the changed field.
- **B-roll's words on screen** are saved as numbers in your bounds (yours kept them as text cut to 300 characters); your hidden Top/Middle/Bottom and "how long" selects are not drawn.
- **The paces:** your 22 acceptance lines match line for line; our extra cases are re-recorded from our engine (we never run yours). A clip that is the whole of a short video plays a touch slower to fill its beat (in CapCut and in the saved video) rather than stopping the reel.

**Carousel and stories designer**

- **Remove this slide takes the photo with the slide either way:** yours takes a photo only when its middle is on the slide and otherwise leaves it lying there, so the slide that moves up lands under it (two photos on top of each other). Ours takes it when its middle is on the slide or when it stretches across either edge of it (see the rough edges at the end).
- **At one slide, Remove this slide is off** and says "It's your only slide, so it stays." (yours does nothing and says nothing; your stories have had the same line since v26). Your three slide tooltips say "story" in the stories designer (yours still say slide).
- **A drag can be cancelled:** Escape puts the slide back, and so does the window losing focus mid-drag (yours has no way out once started). The drop line and the dimmed piece are your coral; our centred lines stay blue.
- **The slide buttons keep their room.** With buttons showing for anything selected, our page holds the room under them so the slides do not jump (yours lets them jump). The slides start about 40 px lower on a wide window, and one row lower between 768 and 1023 px.
- **Where should it go? forgets the slide clicked last** when another design is opened, so a stale "slide 8" can't happen.
- **Pick my carousel photos:** the designer still makes its first design with one photo on every slide, so on a fresh shoot there is no empty frame to fill. The assistant says so and names what to press (Empty frame on a slide, or + Add slides with the fill tick off). Frames are listed to the assistant in the order the page fills them (slot, left to right, top to bottom), not "by y then x", so the chat and the page agree. The note is kept after the fill, and its box saves after a short pause rather than on every keystroke, so a note never makes a new set or an Undo step.
- **Open folder:** your permanent button sits in the top row beside Save just slide N; ours lives in the bottom bar beside Save slides and Save just slide N (always in sight, one button for both jobs). On a PC the answer says File Explorer; when the Mac keeps the browser in front we add a sentence of ours. The route still answers every other page's folder button in its old words; only the designer's two folders have your lines.
- **Show the whole photo and Done:** a frame that would come out under 60 px on a side is brought to 60 and a sliver of the photo is cut off (yours leaves a frame nobody can take hold of). A zoom past 25 is brought to 25. The Zoom slider still runs 100 to 300; after a Crop that zooms past 3x the slider sits at its end, and the wheel only winds a larger zoom down. The Crop window shows the Assistant's 1600 px copy, never taller than two thirds of the screen (yours swaps in the full photo). The two Crop hints in the stories designer end "on your story".
- **Several photos at once:** dragging a group stops where the first of them would leave the strip (40 px kept), and the group stays rigid (yours can be dragged off and lost). Same size uses the last photo you clicked as the reference, never a text box. Escape lets go of the several but keeps the last clicked; arrow keys and the selected-photo buttons act on the one with handles; Even them out lays everything on the slide of the first photo, even from different slides (all as yours).
- **See a photo big** shows the Assistant's 1600 px copy (window at most 1400 px wide), not the full file; the window closes if the design changes under it. A photo that can't be read (drive unplugged) has no big view and the arrows skip it. On a touch screen the small ⤢ is always showing, and a single tap still waits 230 ms.
- **Save just this slide** goes beside the design's newest whole set, named from the design itself ("... slide 03 updated.jpg" with no set yet). The page says "Saved slide 3 as ..." and tells the chat nothing (yours tells nobody).
- **+ Add photos:** only photos that were added join without a reload; one taken out or renamed still asks for a Reload. The assistant's contact sheets are not redrawn at that moment; the assistant draws them before it picks, keeping every number. A single click on a new photo's tile waits the usual 230 ms.
- **The path at the top of the designer** (Home › shoot post kit › Carousel) hides your Back to home pill too, since Home is its first step. A collage, the three story collages included, lands on the set's own background, not its cream or grey.
- **Your "Empty frame" button is still named "Take the photo out"** in ours (from before v27).

**Talking reel**

- **Fixed words are laid over the heard words when the record is read** (yours rewrites the word and keeps the heard one as w0). What the page receives is the same shape. A fix over 80 characters refuses the whole save in plain words (yours cuts it silently). Odd keys, other scripts' digits and a list typed as a fix are refused with nothing written.
- **Fixes survive a new script.** When a video is turned into words again, our fixes go with the earlier cuts and the edit starts afresh (yours loses them silently). Each video keeps its own fixes and gets them back when you switch to it.
- **The fix box** toasts "Fixed. Your captions use it now." only once the save got through (yours says Fixed over a refusal). It follows its word when the page scrolls and closes, saving nothing, when the word scrolls out of the window. On a phone the input gives way so the box stays on screen.
- **A word typed away** (fewer words typed than highlighted) still plays and only loses its caption, as yours. A fix on a cut word is allowed, as yours.
- **Open CapCut** goes the reel page's way: starts CapCut on a Mac or a PC, adds a reel still waiting for CapCut's list when CapCut is surely closed, and says it is taking a while when the Mac was slow. With nothing made it answers "I couldn't open CapCut." (yours opens CapCut anyway). On a PC the line says "this PC" and "the Start menu".
- **"Working on it"** shows the moment Edit my video is pressed, before the Assistant answers.
- **+ Add more photos** looks only while the photo pop-up is open (yours looks every 4 seconds for the life of the page). A photo still being copied waits until it has settled before it is numbered. We left out the dashed purple box your old rule puts around the button; it is a plain small button. The "new photos in" line counts what each look brought.
- **Project names:** still "shoot talking reel", "... 2", counted across the shoot, so Open CapCut on reel 1 may name "... 2".
- **The assistant never fixes a caption word for them;** asked to, it says "Double-click the word on the page and type the right one." Its status says how many words were fixed, never which. It has no command for Open CapCut and points to the button.

**Post kit, words page, posting queue, the path at the top**

- **The path** (Home › Hannah post kit › Captions) is built on our server, Home is this computer's own home page on any port, and the hover colour and font come from the page's own look. A step with no link is plain words, never a dead link; a long unbroken shoot name breaks inside its crumb on a phone. A saved copy of the kit page (no server behind it) shows the path as plain words. Your Back pills stay in the page, hidden, as yours do. Your test-only Home switch is not built, by your own note.
- **Switching a posted post back to Not posted** puts it at the end of the line on a new date (yours kept its old date, so it came back "down for" a day already gone), and its reminder comes back on that day (the same calendar event, moved). Pressing it twice changes nothing; a post still finishing can't be switched back.
- **The panel of a posted post** offers only the switch and Done (yours): no Copy caption, no Copy my hook, no reminder. The posted tile can be reached with the keyboard here and the switch has a focus ring (yours were mouse-only). A single post marked Posted gets a small ▢ mark in the grid.
- **The chat's unposted command** looks only among posted pieces, so "beach reel" means the posted one even with another reel still in line.
- **The grid's rows stay whole** once posted tiles are drawn (yours went ragged).
- **The carousel picker** keeps the carousel at the top without your 48vh cap: at 1280x800 with 20 photos it takes 38% of the window and its own row scrolls inside; only a window under about 535 px tall would give it more than yours.
- **"What's a post kit?" in the chat** is answered with your Make posts paragraph word for word. "Create another reel" shows once any reel of the shoot is made (your rule).

**Remove this song and the Make posts screen**

- **Remove this song goes to the Trash through Finder** (Put Back works), on a PC to the Recycle Bin through Windows' own call with nothing installed (yours is Mac-only; send2trash would be an install). Dustin's earlier thought, only take it off the list and leave the file, is not taken: your v27 is the newer answer and Put Back keeps it reversible.
- **It checks every file first, then moves,** and names which went if one could not (yours stops at the first failure with earlier files already gone and says nothing). It calls it done only when the Trash really has it. It takes the song's id, never a path, and refuses a press from another website.
- **A recording takes its sounds with it:** " sound", " sound 2" and any number after (yours stops at 9), and the sounds noted for it.
- **The reel that had the song picked** goes back to "no song picked yet" on the server too, so a page that never got the answer sees it on reload. Another reel of the shoot that picked the same song is left alone; opened, it says your "That song isn't there anymore" line when Make my reel is pressed (as yours).
- **A recording in the Photos folder stays** (yours would trash it from there).
- **The Make posts screen** has your What's a post kit? box, your new lede and the three steps, word for word. The fonts and colours are inline in our own look, nothing loaded from the internet. When someone types "what's a post kit?" the assistant answers with the box's words, and after it opens the kit it stops (your Nov 13 "I choose, not you" rule).
- **The page's version of the box wins:** your pack's section 8 words differ slightly from your page's ("Inside it you build reels..." against "Inside your post kit is where you make it all..."); we built the page's.

## Your faults we fixed rather than copied

**Reel page** (the full list is in CLAUDE.md's v27 section)

- Save my video: the `.part` file beside the output with no lock (two presses raced); `FileExistsError` after a full render; ffmpeg unbounded. The watch step: the preview leaked the song's path and each clip's src; `v.src.endsWith(u)`; no lock against Make my reel; the short-song rule and the preview's start could disagree. The editor: `ED.added` lost on a reload; the ids snapshot after the add's request; two zoom thresholds; × on a card not clearing the trim. The chooser: the title set in JS after load; a switch keeping the address's kind. Add photos: `prepare()` renumbering everything; a second poll of /photos.json. The queue button: `reelToQueue` re-entering itself; "already in your queue" by status green alone. B-roll: the sum written twice; onscreen's numbers stringified. Naming: "about" stored quietly; one clip's sheet over another's.

**Carousel and stories designer**

- Remove this slide left a stretched photo lying where it was and moved the next slide up under it (two photos overlapping); at one slide it did nothing silently. The stretch test was written out in three places, ours in one.
- A drag had no Escape. Your stale "slide 8" in New design can't happen here.
- Insert, remove, move and add slides each saved at once on every press; ours go through the one queued save and one Undo step like every change. A block past the last slide is brought to the last one so it travels with it.
- A very tall photo in a wide short frame could leave a frame under 60 px, a sliver nobody can take hold of; Done could leave a frame under 60 px or off the strip with Keep the frame's shape off; the wheel could keep zooming a cropped photo further.
- A group drag could leave the strip and be lost; Same size with a text box last clicked gave the photos the text's width; Even them out could try a column count whose cells were too small; the big window stayed open when the design changed under it.
- Save just this slide wrote straight into the Carousel folder with no staging, no record and no check; ours stages it, never moves it over another file, checks it arrived whole and refuses a slide the design hasn't got or a stale page. It guessed the set number from file names, which picks the wrong set after a hand rename; ours names from the design's own last finished set. A file of yours under the same name (capitals ignored on some drives) is never taken for the slide. A refusal showed the server's raw error text; ours says one plain clause.
- + Add photos listed the folder every few seconds for the life of the page, even unpressed, and renumbered the kept photos from 1; ours asks only while its line shows and keeps every number, so an open page keeps its Undo and its unsaved change.
- Open folder ran a Mac-only command and its button only changed its own label; ours works on both computers, shows the Assistant's full answer and never a path, and another website cannot press it. Your missing-folder line was built from the Save button's text; ours is the page's own line.
- The note box saved on every keystroke; Save just slide N's label was updated by a timer after every click, ours on the click and on every draw.

**Talking reel**

- Saving fixes took any number of keys, turned a list into the text "['a']" and ignored keys past the last word; ours refuses the whole save on any bad entry with nothing written. Digits of other scripts counted as a word number.
- Fixes were lost without a word when the video was turned into words again, and were not kept per video.
- The fix box was placed once and never moved on scroll; its "Fixed" toast came after the save whatever the answer, covering a refusal; a press on the highlight bar closed it.
- Open CapCut never added a reel waiting for CapCut's list and had no PC path; it opened CapCut with nothing made; a failed request showed a raw error message.
- + Add more photos polled forever, said "Is the photo drive plugged in?" for any failure (and could carry a path), and counted "new" by the list being longer, so one photo gone and one added in the same look counted as nothing new. The old dashed button rule landed on the footer's new line.
- Not her faults, though we expected them: Space, Delete and Escape typed in the fix box never reached the video or the timeline in yours either.

**Post kit, words page, posting queue, the path at the top**

- crumbs.js wrote http://127.0.0.1:8790/home into the path and its hover colour and font by hand. It built the path in the browser from the address, so a page with no shoot showed a bare "Post kit" with a dead link. On a phone a long unbroken shoot name pushed the page sideways (130 px over at 390 px).
- Switching a post back kept its old date; the posted tile had no keyboard access; the switch was built from text strings; a posted time that is not a string could break the sort (and our own scheduling crashed on one before this stage); the feed was filtered a second time on the page.

**Remove this song and the Make posts screen**

- Remove this song took any path the page sent, stopped at the first failure with earlier files already in the Trash and nothing said, never cleared the picked song on the server, would trash a recording from the Photos folder, took " sound" only up to 9, and was Mac-only. Hers never checked the item really went to the Trash.
- The Make posts page loaded CSS and Google Fonts from the internet, opened the kit page on your test port 8799 and Back to home on the test home page, and a long unbreakable word could widen a phone screen.

## Lines of ours where you had none (drafts for you to reword)

**Reel page**

- A PC, Save my video: "Saving a finished video isn't on a PC yet: it needs a part only a Mac has today. Make this one in CapCut works here, and your words go with it."
- A PC, the editor: "On a PC the timeline has no pictures along it yet. The trim, its ends and the times work the same."
- A PC, naming: "I can't take stills from a video on this PC yet, so I can't see your clips to name them here."
- Save my video: "Your video is already being saved. One moment." / "Saving your video stopped before it finished. Nothing was saved. Press Save my video again." / "Saving your video took too long and was stopped. Nothing was saved. Try again, or press Make this one in CapCut." / "Save my video is for a B-roll reel. For this kind, press Make this one in CapCut." / "A file with that name appeared in the Reels folder just now, so the video was saved under the next number." / "Your Reels folder is open in Finder." / "I couldn't open the Reels folder. It's inside this shoot's post kit folder."
- The watch step: "That part of the song is past its end. Pick another part."
- The post kit's Reels card, for a B-roll reel saved with Save my video (your card says In CapCut for every made reel): "Saved as a video, in this shoot's Reels folder: Beach B-roll.mp4", and no Open in CapCut unless a project exists too.
- The chat, when a photo that had gone is back in the Photos folder: "Back since the last list: 1 photo (number 3), with the number it had before."

**Carousel and stories designer**

- When the assistant's pick lands on an open carousel: "Your assistant's pick is in your slides."
- Beside Remove this slide at one slide: "It's your only slide, so it stays."
- The three stories tooltips: "Put a new blank story in front of the one this is on" / "Put a new blank story right after the one this is on" / "Take out the story this is on, and everything on it".
- The stories Crop hints' endings: "Only what's inside the box shows on your story." / "The frame on your story changes shape to match."
- Even them out in the stories designer: "Lay them out tidily on their story, every photo whole".
- Save only the story, the tooltips: "Save only the story this is on, as its own picture" / "Save only the story you clicked".
- When a single slide can't be saved, inside your "Stopped: ... Nothing was overwritten.", one clause each: "the design changed while the slide was being made, so press it again" / "the slide didn't arrive whole, so press it again" / "a photo on it was exported again since this page opened, so press Reload first" / "a file in your Carousel folder took the name it needed, so press it again" / "your slides are being changed by something else right now, so try again in a moment" / "it is still being saved, one moment" / "that design isn't here any more, so reload the page" / "that slide isn't in this design any more" / "too many unfinished saves are waiting, so tell your assistant and it'll sort it out" / "couldn't save it (the reason), and nothing was lost, so press it again once that is put right".
- Open folder when the Mac kept the browser in front, after your line: "It's behind this window: click Finder in the Dock to see it." (a PC: File Explorer, the taskbar).
- To the assistant, for "I just want to save number 3": "Click slide 3, then press Save just slide 3 beside Save slides. It goes in your Carousel folder beside the set, and nothing else changes." When every slide already has a photo: "Every slide already has a photo. Press Empty frame on a slide you'd like me to fill, or + Add slides with "Put this shoot's photos in the frames for me" unticked, then copy the line again."

**Talking reel**

- When a folder won't open and it isn't a missing folder: "Could not open the folder. Ask your assistant to open it." (yours says "Is the photo drive plugged in?" for everything). When the Assistant can't be reached: "I couldn't reach the Assistant just now. Try again in a moment."
- To the assistant only: "Words fixed on the page: {n}." (how many, never which).

**Post kit, words page, posting queue, the path at the top**

- The chat, when a post is switched back: "Beach reel: back in your queue, ready to post, down for Saturday." (your page's "Back in your queue, ready to post." with the day added).
- To the assistant, where the switch is: "Open your posting queue, click the post in your grid, and the switch is beside Done."
- To the assistant, getting back: "Press Home at the top of the page" / "Press Beach post kit at the top".
- The posted single post's mark: ▢, read aloud as "Single post". Trigger phrases we added for the chat: "it's in my feed now", "that one didn't go out after all".

**Remove this song and the Make posts screen**

- A recording in the Photos folder: "That one's in your Photos folder, so it stays. Take it out of that folder yourself if you'd like it off the list."
- When the recording went but a sound didn't: "Already in the Trash: {names}."
- The helper's refusals: "I couldn't move that to the Trash." (a PC: "...to the Recycle Bin.") / "That isn't where it was anymore." / "That's a link to somewhere else, so it stays where it is." / "That isn't in the folder it should be in, so it stays where it is." / "That drive has no Trash to put it in, so it stays where it is." / "That name is too long for Windows to move it to the Recycle Bin, so it stays where it is."
- A PC, getting it back: "open the Recycle Bin in File Explorer and choose Restore"; and your lines with "Move it to the Recycle Bin?" and "Moved to the Recycle Bin. To get it back, open the Recycle Bin in File Explorer and choose Restore."

## Questions for you

**Reel page**

1. Save my video on a PC: not possible with nothing installed. Built as a named gap (the line above). OK, or should a PC be asked to install something?
2. The words in the saved video are drawn by the Mac's own text engine: the same font, size, wrap and one box a line, as your screenshot 18. Does it look right to you on a real reel? (Nobody's hand has been on it yet.)
3. The B-roll words' dragged position carries into the saved video; CapCut's text layer sits at CapCut's default spot (your tip says change it there). Say so on the page, or leave the tip?
4. Your v25 ✂ Trim panel is unreachable in your v27 page; built: the editor only. Do you want the panel back anywhere?
5. A clip that is the whole of a short video (2.40 s on a 2.43 s beat) used to stop the reel; now it plays a touch slower to fill the beat. Held last frame, or a slightly slowed clip?
6. The orange trim zooms in on about 40 s for a video over 60 s (Start here) and over 90 s (clicking a clip) in your page; built with one threshold, 60 s. Fine?
7. Undo and Redo in the watch step also change the song, pace and style chosen in steps 3 and 5 (as yours). Fine?
8. The legend still says "Longer stays on screen about twice as long" while Calm's Longer is 6 beats to 4 and Build's one beat more. Reword, or leave?
9. Photo numbers now stay fixed when photos are added, so a shoot's list can have gaps. OK?
10. Adding a reel to the queue from the reel page needs no caption (your v25); the kit page still asks its caption question. Should the reel page ask it too?
11. Multi-select has no touch-screen way (no Shift or Cmd on a finger); not built, as yours. Fine for now?
12. Remove this song on a PC goes to the Recycle Bin through Windows' own call (you suggested send2trash, an install). OK?
13. Still open from v26, untouched by v27: the folder-naming question at setup, and the drop box's second copy.
14. A photo that leaves the Photos folder and comes back (dragged out by mistake, or a re-export that deletes and re-copies) now takes its old number again, so a pick or a design that named it points at it once more; yours gave it a new number. Keep it this way?
15. A B-roll video saved with Save my video counts as made on the post kit's Reels card and in the queue, with the card line above. OK, or would you rather it only count once it is made in CapCut?

**Carousel and stories designer**

16. A fresh shoot's carousel opens with one photo on every slide, so Pick my carousel photos has no empty frame to fill. Should a carousel open empty now, should the pasted line replace what is there, or should the assistant add slides itself?
17. Open folder: your permanent button is in the top row beside Save just slide N; ours is in the bottom bar. Which row?
18. Removing a slide under half of a photo that stretches across two slides: ours takes the photo with it. Would you rather it refused, or left the photo?
19. Your Empty frame button is still "Take the photo out" in ours. Which name?
20. Save just this slide tells the chat nothing, as yours does. Should the assistant be told, as it is for a whole set?
21. A slide saved on its own goes beside the newest whole set; with no set yet it is named "... slide 03 updated.jpg". Fine?
22. Escape with several photos selected lets the several go but keeps the last clicked (yours); the reel page lets everything go at once. Which should the designer do? And should the arrow keys move all of them, not just the one with handles?
23. The bar for several photos pushes the slide strip down while it shows (your screenshot 11). Fine, or should room be held for it?
24. The Zoom slider runs 100 to 300; should it reach 25x after a big Crop? Is the Assistant's 1600 px copy enough in the Crop and See a photo big windows?
25. After + Add photos, the contact sheets are redrawn by the assistant before it picks, not at that moment. Fine?
26. A collage lands on the set's own background, not its cream or grey (the v26 question still stands), and our centred drag lines stay blue (the Nov 11 "coral or plain" question still stands). Settle these?
27. The Back to home pill is hidden in the designer because Home is the first step of the path; the kit page keeps its Back to home beside its path. Fine?

**Talking reel**

28. When a video is turned into words again, our fixes are kept with the earlier cuts and the edit starts afresh (word numbers change). OK, or should fixes carry over by matching words?
29. A word typed away still plays and only loses its caption. Is that what you want, or should the box refuse a count that doesn't match?
30. A tap on a touch screen never shows the hover line (as yours). Your call on a tap?
31. Several talking reels: should Open CapCut name projects after the reel, rather than "... 2" counted across the shoot? And on a PC, do you want your own line instead of "this PC"?
32. Should "Working on it" show when a file lands in the Talking folder rather than when Edit my video is pressed? (That row already names a file still being copied in.)
33. + Add more photos looks only while the pop-up is open; a photo dropped in while it is closed shows the next time it opens. OK? And do you want the dashed purple box back around the button?

**Post kit, words page, posting queue, the path at the top**

34. The path says "Hannah post kit" (the folder name without its date, your short() rule). Keep that, or the kit's own name as the kit page's title shows it? Should the posting queue page get the path too (yours keeps Back to home there)?
35. When a post is switched back to Not posted, its reminder comes back on the new day. Or should switching back leave the reminder off? And it goes to the end of the line on a new date; would you rather it kept its old place?
36. A posted post's panel offers only the switch and Done. Keep it that way, or should Copy caption stay?
37. "Create another reel" shows once any reel of the shoot is made. Or only once every reel listed is made?
38. "What's a post kit?" in the chat is your Make posts paragraph word for word. Fine, or shorter?
39. Is the pane you use ever under about 535 px tall? (The carousel picker would then take more room than yours.)
40. The chat's unposted finds only posted pieces, so "beach reel" means the posted one. Right?

**Remove this song and the Make posts screen**

41. Remove this song: Dustin's thought was only to take it off the list and leave the file. Built your way, to the Trash. Say if you would rather it only left the list.
42. A recording in the Photos folder stays; the page says so. And another reel that picked the same song is left alone and says "That song isn't there anymore" when opened. OK on both?
43. A drive with no Trash (a memory card, some network drives) refuses with a line of ours, since Finder would ask in a box nobody sees. Or would you rather it did something else? (The PC way has not run on a real PC yet.)
44. The Make posts lede still says "single photos"; the post kit has no single-photo card (a one-slide carousel is a single post). Keep the words?
45. Your v27 adds "me" and "posting" to the home data for "Good morning, Nicole" (section 13). Not built until you've brainstormed the page; say when.
46. Still open from v26: a delivered shoot's pill reads Edited on Back up a card while the queue says Delivered; a press on step 1 or step 3 is still recorded (yours records nothing); Archive asks nothing first; no chat command archives a kit; searching for an archived kit reads "No post kit called ... yet" above the closed Archived list; and "Show the archive" in the chat still scrolls to Uploaded shoots. Should "the archive" now mean Archived? For you and Dustin: clearing the drop box's second copy to the Trash would go through the same door as Remove this song; Dustin's call.

## Known rough edges we have not fixed yet

- **From the chat, finishing a one-slide save with a whole set's token crashes.** If the assistant runs the save-finish command for one slide with a token that belongs to a finished whole set, it stops with an error instead of a plain refusal. The page is safe; only that chat command is.
- **Remove this slide also removes a photo that stretches across the slide's near edge,** even when its middle is on the slide before. Undo brings it back and nothing on disk is touched, but it is a loss you did not ask for, and the slide's tooltip does not promise it. Yours would keep the photo.
- **+ Add photos with an unsaved change can refuse the save.** If you press + Add photos, drop files in, and move something before the page next looks at the folder, the save can be refused with "The photos in this shoot changed since this page opened", and the page reloads and loses that move. A second page of the same shoot is blocked the same way.
- **Your Open folder tooltip is missing from ours.** Yours says "Open the folder your saved slides go in"; ours has no tooltip on that button.
