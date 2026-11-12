# Nicole's v23 and v24: notes for Nicole (draft, Nov 12, 2026)

**Not sent.** Nothing here goes to Nicole or Slack without Dustin's say-so (rule 10).

**This file is not the whole note yet.** It was started in the stage G fix round so that one list would not be lost: the small ways the talking reel page behaves differently from hers, which the builders and reviewers named along the way and which lived only in the build's scratch notes. Still to be added before it is handed over, from the build plan (`docs/handoff-v24-build-2026-11-12.md`): what differs underneath and why (the plan's 2a and 2c, the frame grid, 540, one material), the six CapCut points listed under stage D, the questions for the two of them (2b), which steps ask a Claude Code permission question outside Auto mode, and what only a person can prove (section 5).

Standing rule for all of it: identical for the photographer (her words, the same behaviour), our way underneath. Everything below is a place where a photographer could notice a difference. None is a fault found in the build; each is theirs to keep or turn round.

## Small behaviours that differ from yours

### Step 1: the video, Edit my video, who places the photos

1. **A long refusal from Edit my video stays in the status line, in red.** Yours shows it as a toast for 2.6 seconds.
2. **Choosing another video chip takes the swap question away,** and it is asked again the next time. Yours went ahead with the swap unasked.
3. **A job's stopped line shows in red whenever the record carries a problem,** even when an earlier script is still ready underneath.
4. **While the Mac asks about Speech Recognition the status is only that line,** without "A minute of video takes about a minute." beside it.
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
