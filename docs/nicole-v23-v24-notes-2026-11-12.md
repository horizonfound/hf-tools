# Nicole's v23 and v24, built into the Assistant: what differs from hers (Nov 12, 2026)

**First: Nicole, please don't press "Check for updates" until Dustin says this is in main.** If your v23 and v24 are edits on your own Mac, an update before then would replace them.

**A draft for Dustin to send or not. Not sent: nothing here has gone to Nicole or Slack (rule 10).** Same rule as v19 to v22: identical for the photographer, our way underneath. Built on branch `v24`, checked on pretend kits only, with a pretend transcriber. The plan it was built from is `docs/handoff-v24-build-2026-11-12.md`.

**The short version of what is not proven** (section 10 has it all): the small app that turns talking into words has been built and run once (Dustin's hand test, Nov 12: one Mac (Dustin's, macOS 27.2), two real videos (a handheld 25-second one, 60 words; a second, steady one), the Allow answer only), and three talking reels were made and opened in CapCut. The slow zoom looked smooth to Dustin's eye on a steady clip. Not tried: Don't Allow and the way back through System Settings, nobody answering, a Mac without Apple's tools, an older macOS, a Mac that can't do it by itself, a long video, a silent video on the real app, a second Mac, Windows.

## 1. Built as yours

- **The talking reel page:** the preview beside the script, a click on a word, the highlight bar in your order, the bars above the exact words, the photo menu and its four spots, both pickers, the preview's drags, one-word captions, the phone guides, the timeline docked at the bottom with Split, Delete, Speed, Zoom, its own zoom, Undo and Redo to 60 steps, and Make it in CapCut with your result box. 171 lines of yours are on it, whole; a test compares them with your `talking-reel.html`, `talking_core.py` and `server.py` both ways.
- **Your arithmetic,** number for number: the 0.45 s pause, 0.08 before and 0.14 after, the halfway meeting, the 0.05 s drop, the sentence rules, the caption times, `behind` read as `full` and `top` as `center`, v23's `moves` and `photos` still read. (We may not run your code, so every expected number in the test was worked by hand from it.)
- **Your two rule blocks for the assistant** (`RULES`, `PHOTO_RULES`), character for character, printed every time.
- **The chat's lines:** the three lines to paste, your STOP lines, "Saved: N cuts. The reel is now X seconds of talking. The page shows it in a few seconds." and the photo one.
- **The reel page's third card,** "Talking to camera", your two lines and your one style rule.
- **The post kit's design preview:** your two lines and your style line; sent after each good autosave and when a design opens; saved slides still win.
- **Everything you turned down stays out** (v24 section 3), each with a check: one photo panel under the preview, bars between the lines, a page that does not scroll, button rows per photo, plus tiles and hover "add", Behind you, Across the top.

## 2. Different underneath, on purpose

A photographer sees none of these.

- **Where the record lives:** in the shoot's own hidden folder (`talking.json`, with the version before kept), not `<studio>/talking/<shoot>.json`. Your field names and shapes are kept. The words and their times sit in a file of their own, written once per video, so each save stays small.
- **Nothing installed:** no ffmpeg or ffprobe. The video's facts, the small copy and the sound come from the Mac's own parts.
- **Turning a video into words is a job of its own,** not a thread inside the page server, so the server starting over cannot kill it and a job that died reads as plain words, never a page stuck on "Getting your video ready…". It has stated time limits.
- **The small app is built on their Mac the first time,** from a short source inside the Assistant (yours is built by hand beforehand). It needs Apple's Command Line Tools. It is started only through the Mac's own `open`, so macOS asks its question in the app's own name. Its names are yours ("The Assistant", "Assistant Transcriber", your sentence in the permission box). **Seen on the real box, Nov 12:** macOS names the app "Assistant Transcriber" (not "The Assistant"), in the box and in System Settings, so our lines now name it that way. Changing the name the box shows means changing your `Info.plist`, which makes the Mac ask everyone again; we left it.
- **The CapCut project is written by a second builder inside our `capcut.py`,** not by patching the first. Photo reels are byte for byte what they were.
- **The chat commands find a shoot by a few words** and take a file, not `--studio` and `--content` paths.
- **The page never gets a path.** A shoot is its folder name, a photo its number, a video a key. The record still keeps your `v` and `video` as file names.
- **Words reach the page as text only;** our one look (DM Sans, no serif, nothing loaded from the internet).
- **Copying uses the older copy call first** (the Claude app's pane refuses the modern one).
- **A save is checked field by field** and one bad field refuses the whole save in plain words (yours drops the bad entry silently). Two things are done as yours because your own page can send them: more than 30 photos keeps the first 30, and an Undo naming a Footage video since taken away drops that one stretch.
- **A counter on the record,** so a page that has not seen the assistant's cut cannot wipe it.
- **Your dead code is not ported** (`sdrag`, `#phBack`, the `behind` and `top` branches, the old strip's styles).
- **The design preview** is kept beside its design in the shoot's hidden folder, written whole then swapped in, and drawn small from the small copies (yours draws full size then shrinks: the same picture, a fraction of the memory).

**Numbers that differ:** the small copy is 540 on its short side (yours 720 wide); 5 GB must stay free (yours 2); a talk over 30 minutes is refused (yours has no limit); a make's limit is ten minutes (yours five).

## 3. Faults in yours that ours fixes rather than copies

- "Your edit of <old> is kept" is only true in yours until the next save. Ours keeps each video's edit, resets every word-numbered field for the new video (yours leaves photos, zooms, splits and speeds on the wrong word numbers), and going back restores the edit with no new transcription.
- Dragging a video block's end on the timeline loses the video. Ours carries it.
- The spacebar plays the talking video behind the open video picker and behind the open photo menu, and takes the key from a button reached with the Tab key. Ours: nothing plays behind an open picker or menu, and a button reached with Tab is pressed by the spacebar.
- A Footage video shorter than the words it sits on flickers in your preview. Ours stays on its last frame.
- A video with no sound shows a Python error. Ours: your line "I couldn't hear any talking in that video." before anything is made.
- A preview keyed on the file name plays a stale copy after the video is exported again. Ours keys on name, size and time.
- A talking video exported again under the same name keeps its old script, with every word time now belonging to the old file. Ours says so on the page, offers Edit my video again, and refuses the make until then.
- `place` accepts a photo number that does not exist and a stretch with no kept word. Ours refuses both in plain words.
- A missing value in the record can crash your engine. Ours drops the bad entry.
- Captions: "you" followed by "'re" shows as "you 're". Ours closes up every word that begins with an apostrophe. Your other two caption rules are kept.
- Undo after the chat has changed things wipes the assistant's cut or placing in one press. Ours empties the Undo and Redo lists when the chat changes something.
- Choosing who places the photos adds an Undo step that holds nothing. Ours adds none.
- Your line "click Allow, then try again" is wrong once they have said no, because macOS never asks twice. Ours says where to switch it on.
- On some Macs yours sends the talk's sound to Apple without a word. Ours stops and says so.
- An emptied design still got a preview. Ours shows none.
- Kept as yours and only noted: "Remove this one" always removes the first photo of a flashing stretch; a photo or themselves-in-the-corner can be dragged wholly off the screen (only "Put it back" recovers it); the last caption stays up at the very end; Select All brings up the highlight bar for the whole script.

## 4. The CapCut project: where ours differs

Three of ours have been made and opened in CapCut (Dustin, Nov 12: they worked), and the slow zoom looked smooth to his eye on a steady clip (point 10). Nobody has looked at the other points one by one, so those are still on paper.

1. **Every time sits on a whole frame.** CapCut moves times onto its 30 fps grid when it opens a project; in October that put every cut a frame late. Ours puts each edge on a frame and takes the photo, corner and caption times from those same edges. Pieces differ from yours by at most half a frame.
2. **One material for the talking video,** not one per piece; no "photo, 5 s" note on a video.
3. **A talking video that is not 9:16 fills the frame,** so the project matches your preview (yours lays it in with bars). The small copy of them in the corner is written at your size (`me.w`), as yours: CapCut cannot crop, so it shows whole inside its box where the preview shows it cropped.
4. **A third "Made" line,** ours, for the one case where neither of yours would be true (the reel is made but could not be added to CapCut's list).
5. **Stretches that overlap are split by owner;** a video stretch's start and the last piece are held to the video's real length; with sentences moved, a photo stretch flashes its photos again in each run.
6. **More photos than frames on a stretch:** the ones with no frame are left out and counted in the log. Yours writes them all at under a frame each.
7. **A photo or Footage video that has gone stops the make** and says which kind is missing. Yours leaves that stretch out without a word (question 13).
8. **A record changed by hand** is held to the page's own limits before it reaches CapCut.
9. **A second talking reel of a shoot** is "<shoot> talking reel 2". Yours would clash on the name.
10. **The slow zoom's keyframes** are timed as in your file (the video's own clock). Other accounts of CapCut's files time them from the start of the clip. It is one switch in one place. **Seen Nov 12:** on a steady clip in CapCut the slow zoom was "really smooth... I didn't see any jittering" (Dustin), and a zoom across a closed pause carries on as one zoom. Two things he noticed, both as yours: two separate slow zooms side by side snap back to normal size at the cut and start growing again, which looks odd; and a short stretch makes the zoom look faster, since the 12% is fixed. Would you leave those, alternate them, or join two that touch?

## 5. Small behaviours that differ from yours

### Step 1: the video, Edit my video, who places the photos

1. **A long refusal from Edit my video stays in the status line, in red.** Yours shows it as a toast for 2.6 seconds.
2. **Choosing another video chip takes the swap question away,** and it is asked again the next time. Yours went ahead with the swap unasked.
3. **A job's stopped line shows in red whenever the record carries a problem,** even when an earlier script is still ready underneath.
4. **While the Mac asks about Speech Recognition the status is that line in bold, and under it one plain line about the box's "sent to Apple" sentence** (new Nov 12, after the real box was seen), without "A minute of video takes about a minute." beside it.
5. **Below 520 px wide the two "who places the photos" choices stack** instead of sitting side by side.
6. **The three lines to copy are slanted DM Sans,** not your serif (Dustin's no-serif rule, Nov 7).
7. **Lines of ours where yours had none** (all in `talking_page.OUR_WORDS`, each with its reason, all drafts for you to reword): a video still being copied in; "couldn't reach the Assistant"; "couldn't open the folder"; "select and copy" when the clipboard is refused; the PC's Undo and Redo tooltips; a Footage video that is not ready yet; and the video picker's two (`vp_cant`, `vp_lowspace`).

### The script, the bars and the pickers

8. **A Footage video that is not ready yet cannot be pressed in the video picker.** Yours can, and opens a player with nothing in it. Its card becomes pressable the moment it is ready.
9. **A photo whose file is missing (and has no older small copy) is left out of the photo picker's grid.** Yours shows every photo. A photo with no small copy yet shows no thumbnail on its bar; yours always draws the picture.
10. **"Remove all N" does nothing if the stretch has already gone.** Yours would still show its toast.
11. **A Control-click on a bar does nothing** (on a Mac that is a right click).
12. **"Open my Footage folder" failing shows our plain lines** (couldn't open, didn't work, couldn't reach) where yours shows the raw error.
13. **The Move chips, the picker's photos and the video cards are real buttons** (they can be reached by keyboard and say whether they are pressed); the round x says what it is to a screen reader, in your tooltip's words. Nothing looks different.
14. **The page re-reads the Footage list every 4 seconds until every video is ready or has failed.** Yours keeps asking while any is "not ready", so a failed one is asked about for ever.
15. **Every whole answer from the page server carries the photo list and the videos' first stills,** and (since the fix round) each video stretch carries its video's shape. Yours loads the Footage list as the page starts; ours asks for that list only when the video picker opens, so nothing is made for a Footage video while the page just sits open. A wide video on a stretch is drawn wide from the first frame, as yours.
16. **While a photo that is showing has no small copy yet, the page asks for a whole state every 4 seconds** until it has one.
17. **Two stretches can never share a word.** Your page can never send that either (everything it saves is trimmed around the new stretch); ours also refuses it if something other than the page sends it. Stretches are kept in order of their first word.

### The timeline and the keyboard

18. **Delete and Backspace are ignored while Cmd or Ctrl is held** (yours deletes), **Z and Y are ignored while Option (Alt) is held** (yours acts), **and a key pressed inside a drop-down is ignored.** Say if you want the keys exactly as yours; it is three small conditions.
19. **One line of page-wide style: anything scrolled into view stops above the docked timeline.** In yours a bar brought into view can sit under the timeline. We count this as a fault of yours fixed, not only a difference.

### Make it in CapCut

20. **An answer with no words falls back to "Something went wrong making it."** Yours falls back to "That didn't work".
21. **A refusal also scrolls the result box into view** (yours scrolls only when it worked), and the box is announced to a screen reader.

### In the chat

22. **"Saved: N cuts." counts the cuts after touching ones are joined.** The sentence is yours word for word; the number can differ (three cuts handed over that touch, "Saved: 2 cuts"). The same kind of difference as "seconds of talking".
23. **A fresh cut after they brought every word back on the page now stops and asks.** Yours saves. Why: bringing every word back is their own work.
24. **The assistant's own photo set sent a second time, unchanged, saves without `--replace`** (nothing changes, nothing is asked). Yours stops. Why: a run that was cut off or doubted should not end in a question about "their" photos.
25. **Words of ours in the chat's lines, for you to reword:** the [Keep my cuts] choice; "say yes in that box" (the assistant never clicks a system box for them, and never says "click Allow"); and "or place" in the note the assistant gets when the talking video was exported again.
26. **What the assistant is told about the photo stretches** (`talking_rec.py status`, never read out): "(placed by you)" only while the stretches are still the very set the assistant placed; after the photographer changes them on the page it reads "(changed on the page since you placed them: ask before replacing them)". Your `claude_shots` flag is kept as it is for the page.

### On the computer, not on the page

27. **The sound of their talk is never left behind.** The job that turns a video into words keeps the sound in a scratch folder on the computer's own disk while it works. It is removed when the job ends, when the job is stopped for taking too long, and, for a job cut off outright (a power cut, a force quit), the next time the Assistant sees the job is gone.

### The design preview on the post kit

28. **A photo whose small copy is not ready is tried again quietly** (every 3 seconds, up to 10 times) before the picture is sent; a photo that can never be read means no picture at all.
29. **The page sends its counter with the picture,** so an older picture can never replace a newer design's.
30. **An emptied design is no longer previewed** (section 3).
31. **Beside a preview of the assistant's own first design the button reads "Open my carousel →",** though that design is still not counted as "a saved design".
32. **The card can show a slightly older picture** when the designer is left within about 2 seconds of a change, or another design is opened within 1.5 seconds. The same as yours.

### A few more on the talking page

33. **The highlight bar follows the highlighted words when the page scrolls.** Yours stays where it first appeared.
34. **While a make runs, the page asks once a second how it stands.** If it cannot see the make five times in a row, the button comes back with a plain red line; when it can see it again it follows it and clears the line. The page never stays on "Making it…".
35. **Another shoot's talking video being worked on:** only one runs at a time on the computer, so a second shoot's Edit my video can wait, and if it waits too long it gets a line of ours rather than your "still working on the last one", which would not be true of that shoot.
36. **The timeline is tall in a small window,** as yours: about 290 px of an 800 px high window once the Speed and Zoom chips wrap. Worth a look in the Claude app's pane before deciding anything.

## 6. Every line of ours where yours had none

All drafts, all yours to reword. 40 on the page (`talking_page.OUR_WORDS`):

| Our line | Why it is there |
|---|---|
| {name} is still being copied into your Talking folder. It shows up here when it's done. | hers lists a video while it is still copying in, and Edit my video then reads half a file; ours waits for it, as the reel page does for Footage |
| Select the words and copy them | the app's pane can refuse a copy; hers then says nothing (the words page's own line) |
| Could not open the folder. Ask your assistant to open it. | her talking page says its folder is open whether or not it opened; this is her reel maker's line |
| , behind this window. Click Finder in the Dock to see it. | the folder can open behind the Claude app; every folder button of the Assistant says so |
| I couldn't reach the Assistant just now. Try again in a moment. | hers shows the browser's own error words when her server is not there |
| That didn't arrive the way it should have. Reload the page and try again. | a request her page could never send is refused in plain words |
| This was changed somewhere else. Here's the newest. | hers has no counter: a save from a page that had not seen the assistant's cut wipes it |
| Something else is saving this shoot's talking reel right now. Try again in a moment. | two saves at the same moment; hers has one process and no lock across programs |
| I couldn't get to this shoot's talking reel just now. Nothing was changed. Try again in a moment. | a record that would not be read just now; hers shows an empty edit |
| {length} · I couldn't get this one ready to use here | a Footage video whose small copy could not be made: her picker opens an empty player for it; the reel page's own line for it says its moments and the reel still work, which is not so on this page |
| {length} · your photo drive is almost full, so I couldn't get this one ready | the same, when the reason is a nearly full drive (her own page says "almost full") |
| Undo (Ctrl+Z) | a PC has no ⌘ key |
| Redo (Ctrl+Shift+Z) | a PC has no ⌘ key |
| Made "{project}" in CapCut. | talking_make.MADE_ONLY: the reel is made but could not be added to CapCut's list of projects, so neither of her two lines would be true |
| Made "{project}" in CapCut. {note} | the same, with capcut.py's own note after it on the same line (what to do so the reel shows up in CapCut), as the photo reel's page shows it |
| This shoot isn't ready for this yet. Tell your assistant: make posts from this shoot. | the pickers' own line says "to Claude", which no line on this page may; the same page, reworded |
| Setting up, just this once… | hers has the transcriber built by hand beforehand; ours builds it on their Mac the first time |
| Your Mac is asking if Assistant Transcriber may use Speech Recognition. Press Allow in that box and I'll carry on. (It may be behind this window.) | hers waits in silence while macOS asks |
| The box says speech data will be sent to Apple. Apple puts that sentence on every box like this. I only ask your Mac to do it by itself, and I stop if it can't. | shown under the line above while the box is up: the Mac's box carries Apple's fixed sentence about sending speech data to Apple, and a photographer reading it needs to hear what the Assistant asks for while they decide (new Nov 12) |
| Your Mac asked if Assistant Transcriber may use Speech Recognition, and nobody answered, so I stopped. Press Edit my video to try again, and press Allow when the box comes up. | hers would wait an hour |
| Speech Recognition is turned off for Assistant Transcriber, so I can't turn your talking into words yet. To turn it on: open System Settings, then Privacy & Security, then Speech Recognition, and switch on Assistant Transcriber. Then press Edit my video again. | hers says "click Allow, then try again", which is wrong once refused: macOS never asks twice |
| This Mac doesn't allow Speech Recognition (Screen Time or a work profile is holding it off), so I can't turn your talking into words on it. | hers shows the Mac's own error words |
| Your Mac's Dictation looks to be turned off, and I need it to turn your talking into words. To turn it on: open System Settings, then Keyboard, and switch on Dictation. Then press Edit my video again. | hers shows the Mac's own error words |
| This Mac can only turn talking into words by sending the sound to Apple, and I won't send your video's sound anywhere. So I can't make a script on this Mac yet. | hers sends the sound to Apple without a word (rules 7 and 8) |
| Talking reels need one more thing from Apple on this Mac before the first one. Tell your assistant: set up talking reels. | ours builds the transcriber on their Mac, which needs Apple's Command Line Tools |
| Apple's tools on this Mac are older than its macOS, so I couldn't finish setting up. Tell your assistant: set up talking reels. | after a macOS update the compiler and the SDK can disagree |
| Apple's tools on this Mac are waiting for their licence to be accepted, so I couldn't finish setting up. Tell your assistant: set up talking reels. | an Xcode whose licence was never accepted refuses to build |
| I couldn't finish setting up talking reels on this Mac. Tell your assistant: set up talking reels. | the build can fail in ways hers never meets |
| Talking reels need macOS 13 or newer, and this Mac is on an older one. | hers needs macOS 13 too and does not say so |
| This video has changed since its script was made. Press Edit my video to make its script again. | hers keeps the old script on a video exported again under the same name |
| That took too long, so I stopped. Nothing of yours was changed. Press Edit my video to try again. | hers has no limit: a hung step leaves the page on "Getting your video ready…" for good |
| That video is over 30 minutes, which is more than I can turn into a script. Try a shorter one. | hers has no limit |
| Another video was still being worked on, so I didn't get to yours. Press Edit my video to try again. | hers does one video at a time inside her server; ours can wait behind a backup's clips or another shoot's talk, and her "still working on the last one" would not be true of this shoot |
| I was stopped before the script was finished. Press Edit my video to try again. | hers stays on "Getting your video ready…" when her server stops part way |
| I couldn't turn the talking into words just now. Press Edit my video to try again. | hers shows the Mac's own error words in brackets; ours keeps those in the log |
| Talking reels aren't on a PC yet: turning your talking into words needs a part only a Mac has today. Your photo reel, carousel and stories all work here. | hers has no PC |
| A photo in your talking reel isn't in this shoot anymore. Take it off its words or put it back, then make it again. | hers leaves that stretch out of the reel without a word; ours stops before anything is written |
| A video in your talking reel isn't in the Footage folder anymore. Take it off its words or put it back, then make it again. | hers leaves that stretch out of the reel without a word; ours stops before anything is written |
| I can't find CapCut's projects folder. Is CapCut installed, and has it been opened once? | capcut.py's own stop, as the photo reel's page shows it: tells them what to do, where hers says only that something went wrong |
| I couldn't make the project's folder in CapCut's projects folder. Nothing was written. | capcut.py's own stop, as the photo reel's page shows it |
| I couldn't give the CapCut project its name. Nothing was added to CapCut. Try again. | capcut.py's own stop, as the photo reel's page shows it |

One more on the page, shared with every picker: "I can't find that shoot's posts. Is the drive plugged in?" (a shoot that is not in Your Content, or whose drive is unplugged).

**On the reel page:** nothing of ours; the third card is your two lines.

**On the post kit:** nothing of ours; the two preview lines are yours.

**What the assistant is told to say in the chat** (`parts/talking-reel.md`; ours, since yours has no instructions file for these):
- The setup talk when Apple's tools are missing ("click Install, five to ten minutes, tell me when it's done").
- The permission lines: "Press Allow in that box" (the real box's button, seen Nov 12; your "click Allow" had the button right), the app named as the box names it (Assistant Transcriber), what to say when they ask about the box's "sent to Apple" sentence, and where to switch Speech Recognition on once refused.
- Both "replace?" questions, with the [Keep my cuts] choice.
- The PC line, the same as the page's.
- It also answers to their own words ("open my talking reel", "is my script ready", "cut it tighter"), treats an empty cut as a cut, and never places photos before the script is cut unless they asked for the photos alone.
- It never adds a zoom, a speed or a caption word, never says the script is ready before `status` says so, and never clicks a box their Mac puts up.

## 7. Lines of yours that are left out, and why

| Your line | Why |
|---|---|
| "The Assistant" / "by Horizon Found" (the top bar) | ours is the bar every page of the Assistant wears |
| "Your talking reel", "Cut my talking reel", "Place the photos in my talking reel", and the first timeline hint | written over at once by your own script as the page loads; ours is right from the start |
| "Photo moved. Undo puts it back." | dead code (the photo strip you turned down) |
| "In CapCut: Remove background on your clip" and the "Behind you: in CapCut..." line | dead code (the "behind" spot you removed) |
| "Across top" | dead code (the spot you removed) |
| "The Assistant's transcriber isn't on this Mac yet." | a state ours cannot reach: ours builds it, and says so in its own lines |
| "I can't find the Assistant's reel maker on this Mac." | a state ours cannot reach |
| "If it asked about Speech Recognition, click Allow, then try again." | replaced by our permission lines (wrong once refused) |
| "Plan: ..." and "Dry run: nothing made in CapCut." | your maker's dry-run lines: neither your page nor ours ever asks for a dry run |
| The Mac's own error words in brackets | kept in the log only |

Two of yours changed by one word on a PC only: "Finder" and "Your Mac" take the PC's words, "quit and reopen" reads "close and reopen", and the Undo and Redo tooltips say Ctrl.

## 8. For Nicole and Dustin to settle

Each with what was built, so nothing waited.

1. **How talking becomes words.** Built: the Mac's own Speech Recognition in a small app built on their Mac the first time (needs Apple's Command Line Tools). Or ship one ready-built app inside the Assistant. Or Whisper later, as you suggested (works on a PC, no permission box, but a model download).
2. **A Mac that can only do it by sending the sound to Apple.** Built: stop and say so. Yours sends it.
3. **Punch in, Slow zoom and speed-ups against rule 4** ("no effects, no Ken Burns"). Built as yours; the assistant never adds one. The rule needs rewording to allow them; a wording is proposed in CLAUDE.md.
4. **Where things live.** Built: your Talking folder beside Photos, Footage and Music; everything else hidden in the shoot or on the computer's own disk.
5. **A PC.** Built: a named gap, with our line. Your wording?
6. **The lines of ours** in section 6. Your wording?
7. **The small numbers** in section 2 (540, 5 GB, 30 minutes, ten minutes), apostrophe words in captions, and "seconds of talking" in the chat being the reel's length (the number the page shows; yours prints the video's seconds, so chat and page disagree once a stretch is sped up).
8. **The assistant's own first design.** Built as yours: it gets a preview once it has been opened. Say if it should not count.
9. **Is a talking reel a piece in the posting queue, and does it show on the kit's Reel card?** Built as yours: neither.
10. **A second talking reel of a shoot:** "<shoot> talking reel 2"?
11. **Your two "Made ... in CapCut" lines** differ by a few words from the photo reel's. Built: yours on this page.
12. **Small copies are kept** (up to about 1.3 GB for a 30-minute talk, one more for each video exported again). May the Assistant clear one whose video is gone?
13. **A photo or Footage video gone at make time.** Built: stop and say so. Rather it skipped, as yours?
14. **A talking video that is not 9:16.** Built: fills the frame in CapCut. Right?
15. **English only,** as yours. Another language is a named gap.
16. **The app's names,** yours. macOS will show "The Assistant" in its box.
17. **Ten minutes of someone's time in CapCut:** a throwaway project made by hand (one clip at 1.5x with two scale keyframes, a clip on a second layer, a moved text) so we can read how CapCut itself writes its layers. (The slow zoom itself looked smooth to Dustin's eye on Nov 12.)
18. **The 36 small behaviours** in section 5: keep each, or turn it round.

## 9. When Claude Code asks a permission question (outside Auto mode)

- **Should never ask (not yet tried in the Claude app):** Edit my video and Make it in CapCut. The build, the sound, the app and the CapCut project all start inside the background job the page server starts.
- **May ask:** the assistant's chat commands (`talking_rec.py show`, `cut`, `photos`, `place`, `status`, `setup`, and `talking_page.py open`), and writing the cuts file or the stretches file. Those files go in the assistant's scratch folder, never in their folders and never on the command line.
- **Not Claude Code's question, the Mac's:** the first Edit my video on a Mac brings up macOS's own Speech Recognition box. That one is theirs to answer; the assistant never clicks it.

## 10. Not proven yet

- **The small app has been built and run once** (Dustin's hand test, Nov 12): one Mac (Dustin's, macOS 27.2), two real videos (a handheld 25-second one, 60 words; a second, steady one), the Allow answer only; the Mac did not ask again for the second video. Not tried: Don't Allow and the way back through System Settings, nobody answering, a Mac without Apple's tools, an older macOS, a Mac that can't do it by itself, a long video, a silent video on the real app, a second Mac, Windows.
- **The one-time setup on a Mac without Apple's tools** has never been walked through (Apple's install window, then picking up again).
- **Which Macs can do it without Apple's servers** is not known. The stop that says the sound won't be sent anywhere has only been reached with the pretend transcriber.
- **The Speech Recognition box has been seen once (Nov 12, macOS 27.2) and answered with Allow.** Title: Allow "Assistant Transcriber" to access what is said using speech recognition? Then Apple's own sentence, "Speech data from this app will be sent to Apple to process your requests. This will also help Apple improve its speech recognition technology.", then yours, "So your talking video turns into a script you can edit." Buttons: Don't Allow, Allow. Not seen: Don't Allow and the way back, nobody answering, whether it always comes to the front, whether a rebuild asks again. Two of our lines (Dictation off; no talking heard) rest on guesses about what Apple's error says.
- **Two real talking videos** (Nov 12: a handheld one, 25 seconds, 60 words; a second, steady one); otherwise only 3 and 6 second self-made clips. Not a phone video (HEVC, 4K, HDR, held sideways), not a long talk, not another language.
- **Three talking reels have been made and opened in CapCut** (Dustin, Nov 12: they worked), and the slow zoom looked smooth to his eye on a steady clip. Still to look at, one by one: a sped-up piece; a punch in; a photo in each spot, moved and resized; themselves in the corner, in step; a phone video stored turned; a video stretch, muted, from its start point; captions above a full-screen photo; cuts landing on the words.
- **One hand on the page** (Dustin, Nov 12, a practice shoot: Edit my video, the photo picker, Make it in CapCut); before that a hidden Chrome only. The same goes for the reel page's third card, "Talking to camera".
- **The design preview** in the pane by anyone's hand, with real large photos, or on a PC's Chrome. The card can show a slightly older picture when the designer is left within about 2 seconds of a change.
- **A fresh session** given the three pasted lines.
- **Windows:** nothing has run there, and GitHub's checks have not run on any of this yet.
