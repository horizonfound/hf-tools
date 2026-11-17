# Nicole's v27, the reel page (Lane A): what differs from hers, and the questions (Nov 17, 2026; a draft, not sent: rule 10)

Lane A built your v27 sections 2, 3, 4, 9, 10, 11 and 14 (the reel page) on branch `v27`. Every word of yours on the page is yours (the tests compare them with your page both ways); the behaviour is built from your screenshots; underneath it is ours. This is the list of where ours differs from yours, her faults we fixed rather than copied, the lines we had to write where you had none (all drafts for you to reword), and the questions. The other lanes add theirs to this file in the whole-build round.

## Different from yours, on purpose

- **Save my video draws the words with the Mac's own text engine, not Pillow,** and lays them over the video with the Mac's own video tools (nothing installed). The words match the page: the same font faces, 66 px times the size, wrapped at the same width, and **one box a line, as your screenshot 18**. The video is made by a job the page follows (yours waited on one request for up to 30 minutes), held to 15 minutes; the free name is chosen before rendering; a song shorter than the reel fades out where it ends (yours faded at the reel's end, in silence). Only a B-roll reel can be saved whole (yours answered any reel). The clips' own sound is kept with no song, left out with one (as yours).
- **The path at the top** is built on the server from the shoot's name (yours in crumbs.js from the address, with your home's address and port written in); every link is a path of the page's own server.
- **Photo numbers stay fixed when photos are added** (new ones at the end, a removed photo's number never reused), for the reel, the carousel picker, the designer and the stories alike (yours numbered the kept photos again from 1).
- **A reel remembers its kind,** and switching under Your reels reopens each reel as its kind (yours kept the address's kind and hid the wrong steps). A reel from before v27 opens as Behind the scenes when footage was on, Just photos when off, the chooser when nothing was chosen.
- **The footage editor:** one zoom threshold (60 s) for Start here and for a picked clip (yours 60 and 90); after a reload the trim is drawn dashed from their newest clip of that video (yours lost it); × on a card whose clip is in the editor clears the trim too; the video is swapped by key; the ruler's times are rounded; the Name my clips line is DM Sans (yours Fraunces, which Dustin took off every page). Your v25 Trim panel is off the page (its code kept behind one switch).
- **Naming clips:** labels only, up to 80 letters, "about" refused (you took the description out); each `picks` run goes in a fresh folder (yours wrote one clip's sheet over another's); `describe` writes the record itself (yours posted to your page server).
- **The watch step:** the preview runs in a folder of its own, one at a time per shoot and held to 30 seconds; photos by number and clips by key on the wire (yours sent paths); the watched start is sent back to the make every time and floored to the millisecond; a start past the song's end is refused in plain words.
- **Direct this edit:** `reel_page.py direct` sets the style, the clips and the order in one save (you named no command); the box saves only the changed field.
- **B-roll's words on screen** are saved as numbers in your bounds (yours kept them as text cut to 300 characters); your hidden Top/Middle/Bottom and "how long" selects are not drawn.
- **Remove this song** (Lane E) goes through one door, the computer's own Trash (the Recycle Bin on a PC, Windows' own call, not send2trash); a recording in the Photos folder stays.
- **The paces:** your 22 acceptance lines match line for line; our extra cases are re-recorded from our engine (we never run yours). A clip that is the whole of a short video plays a touch slower to fill its beat (in CapCut and in the saved video) rather than stopping the reel.

## Your faults we fixed rather than copied (the full list is in CLAUDE.md's v27 section)

Save my video: the `.part` file beside the output with no lock (two presses raced); `FileExistsError` after a full render; ffmpeg unbounded. The watch step: the preview leaked the song's path and each clip's src; `v.src.endsWith(u)`; no lock against Make my reel; the short-song rule and the preview's start could disagree. The editor: `ED.added` lost on a reload; the ids snapshot after the add's request; two zoom thresholds; × on a card not clearing the trim. The chooser: the title set in JS after load; a switch keeping the address's kind. Add photos: `prepare()` renumbering everything; a second poll of /photos.json. The queue button: `reelToQueue` re-entering itself; "already in your queue" by status green alone. B-roll: the sum written twice; onscreen's numbers stringified. Naming: "about" stored quietly; one clip's sheet over another's.

## Lines of ours where you had none (drafts for you to reword)

- A PC, Save my video: "Saving a finished video isn't on a PC yet: it needs a part only a Mac has today. Make this one in CapCut works here, and your words go with it."
- A PC, the editor: "On a PC the timeline has no pictures along it yet. The trim, its ends and the times work the same."
- A PC, naming: "I can't take stills from a video on this PC yet, so I can't see your clips to name them here."
- Save my video: "Your video is already being saved. One moment." / "Saving your video stopped before it finished. Nothing was saved. Press Save my video again." / "Saving your video took too long and was stopped. Nothing was saved. Try again, or press Make this one in CapCut." / "Save my video is for a B-roll reel. For this kind, press Make this one in CapCut." / "A file with that name appeared in the Reels folder just now, so the video was saved under the next number." / "Your Reels folder is open in Finder." / "I couldn't open the Reels folder. It's inside this shoot's post kit folder."
- The watch step: "That part of the song is past its end. Pick another part."
- The post kit's Reels card, for a B-roll reel saved with Save my video (your card says In CapCut for every made reel): "Saved as a video, in this shoot's Reels folder: Beach B-roll.mp4", and no Open in CapCut unless a project exists too.
- The chat, when a photo that had gone is back in the Photos folder: "Back since the last list: 1 photo (number 3), with the number it had before."
- Remove this song: "That one's in your Photos folder, so it stays. Take it out of that folder yourself if you'd like it off the list." / "Already in the Trash: {names}."

## Questions for you

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
