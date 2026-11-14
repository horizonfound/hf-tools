# Building Nicole's v26 into the Assistant (started Nov 14, branch `v26`)

Dustin, Nov 14: "grab all the latest stuff from Nicole... and let's start building that into the main."

## What came from Slack (#the-engine, Nov 13)

- `Carousel-designer-and-reel-picker-handoff-v26-updates-since-v25.zip` (unpacked in `reference-private/nicole-handoff-v26-2026-11-13/`, data only, never run, never pushed): `UPDATE-v26.md`, `NOTES-from-Nicole-Nov-13.md` (her notes, sections 1 to 14), a clickable demo of the home base, her test home pages, her stories designer page, and her changes to `edit_queue.py`.
- "Notes for v25": the same notes file, byte for byte.
- One screenshot: the first-backup question "how do you like a shoot folder named?" with her comment "i think client name then date is probably best rather than date first".
- **The v25 zip arrived Nov 14, 8:39am** (`reference-private/nicole-handoff-v25-2026-11-13/`): `UPDATE-v25.md`, her reel page, talking reel page, post kit, timing (`bts_reel.py`), `footage.py`, her posting queue changes, a re-recorded acceptance test, three screenshots.

## The rule, as before

Identical for the photographer (her words whole, the same behaviour), our way underneath. Her code is read, never run or copied. Her "test-only bits" (section 6 of her note: port 8799, `?home=test`) are not built: her home base becomes the real home page.

## Stages (one at a time, each with tests that fail without the change)

- **A. The editing queue** (`edit_queue.py`): the check mark is Mark as delivered; Take out of my queue; one Find a shoot over everything; Uploaded shoots; Delivered (opens and closes); Archived (behind "Are you sure you want to archive this?"; Bring it back); "your assistant", never "Claude". Actions `unqueue`, `store`, `unstore`. Nothing is deleted.
- **B. The home base** (`home.py`, the posting server): the welcome words, Today, four step cards in the order of the work, Open my Assistant folder; no recent-shoots list. Two screens of their own: **Back up a card** (every backup: 10 newest, Show older by month, search; card safe to format, second copy, something needs a look; each shoot with Open this folder and See the report; drive unplugged; folder moved; the cards of one shoot shown as one backup, wired to our linked backups) and **Make posts from a shoot** (post kits: 20 newest, Show older, search, Archive by hand and Bring it back). Kit archive list kept in `~/.studio/kit-archive.json` (where things are saved stays ours).
- **C. The stories designer** (`design*.py`): "Show Instagram's guides"; the stories stay in view while the photos scroll; Let my assistant choose (a note saved as `ask`, a line to copy into the chat, and the chat side of it); templates Gallery delivered (4), My editing queue (1, filled from the queue), The full story (10), Seamless swipe (6); Redo; sets of stories (replaces "one stories design per shoot"); x on each story's label.
- **D. The report's words** (her notes, section 2): why there are two folders; "Does everything look right?"; Open this folder on each shoot; the sneak peeks explained; the closing line changed.
- **E. Instructions, the notes for Nicole, CLAUDE.md, the full test sweep.**

## v25 stages (after A to D; the timing first, since her note says it matters most)

- **F. The timing on the song's real hits** (`timing.py`, and the chat reel maker): every vibe moves its beat grid onto hits you can hear and avoids cuts where the song doesn't hit; "No song" works; her 22 acceptance cases re-recorded.
- **G. Several reels per shoot** (reel page, talking reel page, records, `footage.py`): Your reels bar, Start a new reel, Rename, every reel fully separate.
- **H. The photographer picks:** nothing picked until they ask; the photo note and its copy line; "make my posts" only brings photos in and opens the post kit.
- **I. Trim a clip; select several photos like Lightroom.**
- **J. Songs:** a short song starts after a glitchy opening; a replaced recording's sound taken again; Remove (to the Trash, never deleted; a PC's Recycle Bin).
- **K. The post kit and posting queue:** captions optional (it asks); a preview of each reel; Which reel goes in your queue; each reel its own piece; the reel cover picker in play order.
- **L. Smaller:** the home page lists every shoot in Your Content; shorter holds when photos are alike.

## Waiting on Dustin and Nicole (not built until they say)

1. **Remove a song (v25) is NOT built: a question for Nicole (Dustin, Nov 14: "flag that as a note that she needs to address, I'm not sure what she had in mind").** Hers moves the recording and its sound files from the shoot's Music folder to the Mac's Trash. Dustin's first thought: only take it off the list and leave the file where it is. Ask her which she meant, in the note for her. Until then the reel page has no Remove on a song.
2. **The folder-naming question at setup.** Nicole: it reads as "name this folder"; ask "do you name your shoots a specific way?" with a box, and suggest name then date. Dustin, Oct 24: year first stays as the recommended one. They differ on which is suggested.
3. **The drop box keeps a second full copy** (about 5 GB for Nicole). Her suggestion: clear it to the Trash after a checked sort when the photos came through the folder picker, or copy straight into Your Content. Either changes "nothing is deleted" or the Oct 30 design.
4. Set aside by Nicole herself: a logo for queue screenshots, centering on faces, gallery upload.

## Stage F, built (Nov 14): every vibe lands on the song's real hits

- **What changed:** `timing.py` has her three steps for every vibe: `audible_hits` (a jump in the sound 0.8 standard deviations above the music 1.5 s either side, never two within 0.2 s), `onto_hits` (each tick onto the hit nearest it, within a sixth of a beat and 0.09 s at the most; `Grid.ON` marks ticks with no hit), and `W_EMPTY` 0.9 in the one search. The onsets are our own plain-Python listening (`beats_lite`), nothing installed. The chat's `reel.py make` already went through `timing.py`, so it has the same three steps; its dry run now prints her line "Real hits: 13 of 14 cuts land on a hit you can hear." The reel page's line under A little of everything is hers: "Some quick, some longer, and every change lands on a beat you can hear in your song."
- **Her 22 acceptance lines match her re-recorded ones, line for line.** Ten changed, all on her two real songs: song2 first 14 (On every beat, A little of everything, Build), song2 first 20 (all four vibes), song1 photos 10 (On every beat, A little of everything, Calm). The nine on the steady test beat, her STOP line and two real-song lines are as before.
- **"No song" already worked in ours** (her crash was in her own file); it is now checked in every vibe.
- **CapCut times are still whole frames:** a cut sits on the frame at or just before its (moved) beat. `tests/capcut_even.py` is unchanged and still the same, since its kept projects are built from fixed plans, not through the timing.
- **Left out, as hers:** her hit-to-hit cutting (`HITGRID`), which she tried and left switched off.
- **The pacing note (her section 10)** is in the instructions only (`shared/curating.md` step 7, the reel skill's Step 2): when the photos are much alike, the opener stays plain, few Longers, more Quickers. Her engine has no change for it, so ours has none. Stage L need not build it again unless Dustin and Nicole want the engine itself to shorten holds.
- **Tests:** `tests/reel_hits_check.py` (new, 39 checks at first, 45 after the review round below, each step taken out in a scratch copy and seen to fail), `tests/reel_timing_check.py` (96, her 22 among them).
- **Not tried:** a real reel watched in CapCut with the new timing; her own counts on her songs (minea, november, Aurora, Hannah: those songs are not here); a song with CapCut's own beat list; Windows (the first push runs it).
- **Theirs to settle:** the "Real hits" line is only in a dry run (as hers); the page never shows how many cuts landed on a hit. A song with fewer than eight hits keeps its plain grid with nothing said (as hers).

### Stage F, the review round (Nov 14)

Two reviewers read the timing beside hers and found no fidelity fault. One thing was fixed and four are written down for the note to Nicole (stage E).

- **Fixed: a song from CapCut's own music keeps its beats on CapCut's beat marks.** Nicole's has no CapCut songs, so her spec is silent; ours offers them from the chat (`reel.py make --capcut-song`) and carries CapCut's beat marks into the project (Oct 25: "the cuts match the beat marks CapCut shows"). As first built, step 2 moved those beats too: on a made-up even CapCut list over the test's loose song, 38 of 48 beats moved off CapCut's marks, by up to 0.05 s (0.09 s is the most it could be). Now, for a CapCut song, step 1 (find the hits) and step 3 (a cut on a mark with no hit costs 0.9) apply, and step 2 only marks: no beat moves. One switch, `timing.ON_CAPCUT_MARKS`. Checked in `tests/reel_hits_check.py` (now 45 checks); not tried on a real CapCut song.
- **Also added:** a check that pins the edge of "the music 1.5 s either side" (the far end is not counted, as hers), which before only her two real songs held, and those never run on GitHub.
- **Words:** the reel skill says a CapCut song's beats are never moved, and that "about half a second" is about, never a promise to the frame. The headers of `timing.py`, `reel.py` and `beats_lite.analyze` say the same.

**For the note to Nicole (stage E), and theirs to settle:**
1. **A one-beat photo can now be on screen for about a third of a second.** Her half-second floor is worked out on the even beat, before any tick moves; two ticks that move toward each other (0.09 s each at the most) can leave a one-beat photo at about two thirds of a beat, as little as 0.30 s on a song of about 111 to 133 beats a minute. Her engine does exactly the same, so ours is left as hers. On her two acceptance songs it does not show (shortest 0.53 s and 0.67 s). It is the length she sent back on Hannah reel 26, so she should say: leave it, or size the shortest hold from the moved times.
2. **Her page line promises more than the engine gives.** "Every change lands on a beat you can hear in your song" is hers and is kept whole; on her own acceptance songs 12 of 14 and 17 of 20 cuts land on a hit in some vibes. Our instructions tell the assistant "most cuts, not a promise of every one" (ours, a draft).
3. **A CapCut song's beats stay on CapCut's marks** (above). Say if they should move onto the hits like any other song.
4. **A reel of one piece prints no "Real hits" line** in a dry run (hers: "0 of 0").
5. **Remove a song** is still not built and is hers to answer (the waiting list, item 1).

**For the builder of stage I (trim a clip), an older fault, not this stage's:** a clip whose card is the whole video can stop the reel with "... is only 2.40 seconds of video, and nothing in a reel stays on screen for less than one beat (2.43 s here)" when its whole-beat length comes out a frame or two over the video's own length (22 of 480 tries on the loose test song, 23 before stage F). Hers has no such stop. When the overshoot is under about 0.2 s, take a beat off or let the clip end a few frames short, and reword the line.

## Stage A, the review round (Nov 14): the editing queue

Two reviewers drove the queue page beside Nicole's. Her words, order and states matched; the faults were underneath. Fixed, each with a check that fails without it (`tests/edit_queue_v26_check.py`, 145 checks with the page in a hidden Chrome, on both Pythons; sixteen fixes were each taken out in a scratch copy and the test failed each time):

- **A second press is harmless again, as hers.** A double click on the check mark, Take out of my queue, Yes, archive it, Bring it back or Add to my editing queue said "That did not save. Try again." although it had saved. Now a press that finds the shoot already where it would put it changes nothing (no date rewritten, nothing saved) and answers with the lists as they are. The check mark also takes one press at a time.
- **A page a step behind the chat redraws.** A press that does not fit where the shoot is now (Archive on a shoot the chat put back in the queue) changes nothing and is answered with the newest lists (409); the page shows them and says "This shoot was changed somewhere else. Here's the newest." (ours, a draft; modelled on the pickers' line). A due date can only be set on a shoot in the queue.
- **Another website can no longer press the queue's buttons.** `POST /queue` now has the posting page's same-page-only rule (another Origin or a cross-site press is 403), a 64 KB limit, and a refused negative length; `GET /open` (it opens a folder window) and the two new address routes refuse a cross-site ask. A shoot's name from the page must be text of at most 80 letters. This gap was older than v26.
- **"Make posts from this shoot" is on every delivered shoot and is never a dead link.** A press asks the queue server (`GET /make-posts-url`), which checks that the Assistant's page server answers and starts it if it does not (after a restart of the computer), then goes to its `/make-posts`. "Back to home" goes the same way (`GET /home-url`). **Stage B must serve exactly `GET /make-posts` on the posting server**; until then the link lands on a page that says not found. `STUDIO_POSTING_PORT` is the tests' switch for which port a server started this way begins at.
- **"I'm done editing" no longer marks a shoot as delivered** (`parts/post-kit.md` step 2, `parts/editing-queue.md`). It contradicted the queue part ("not the same moment") and Nicole's page ("the client shoots you need to edit and deliver"). The shoot stays in the queue until they say the gallery is delivered or press the check mark. `edit_queue.py where "<shoot>"` (new, changes nothing) gives the next step the backup and the shoot.
- **From the chat, a repeat or a wrong-place command names the shoot and where it is** ("Patio session is already archived.", "Patio session isn't in the editing queue: it is in Archived."), never "no shoot matches" about a shoot that exists.
- **Smaller:** the page opens Delivered or Archived for `#delivered` / `#stored`; a record with no pictures list no longer stops the page; the chat's lines say "Uploaded shoots", not "your shoots".

**Not done, on purpose:** the home page's recent-shoots labels ("edited", "just for you") go with stage B; the small tap sizes of the new text buttons at phone width (13 to 16 px high) are as hers; a burst of 60 presses at once can still have a few connections reset by Python's own server.

**Theirs to settle (for the note to Nicole, stage E):**
1. **Is finished editing the same moment as delivered?** Built: no. "I'm done editing the beach shoot" starts the post kit and leaves the shoot in the queue; only "the gallery is delivered" or the check mark moves it to Delivered. One consequence: a shoot they finished and made posts from stays in the queue (and can still show as late) until they mark it delivered.
2. **"Show the archive."** Built: it still scrolls to Uploaded shoots (as hers, where `#archive` is that line); "show my archived shoots" opens Archived. Say if "the archive" should now mean Archived.
3. **Our line for a page that is a step behind:** "This shoot was changed somewhere else. Here's the newest." And two more of ours where hers has none: "I couldn't open that just now. Tell your assistant: make my posts" and, on a saved copy, "Open the queue through your assistant to make posts from here".
4. **Take out of my queue asks nothing first and drops the due date for good** (as hers).
5. **Only a delivered shoot can be archived; Mark as delivered clears an old archive mark; a delivered shoot archived before the next chat is not offered a reel until it is brought back** (the first builder's choices where hers is silent).
6. **Make posts from this shoot opens the Make posts screen, not that shoot's own kit** (as hers; the link carries no shoot).


## Stage B, built (Nov 14): the home base and its two screens

**What a photographer sees.** The home page is Nicole's home base: "Welcome to your home base.", her two paragraphs, Today, then "Your workflow, step by step" with four cards in the order of the work (1 Back up a card, 2 My editing queue, 3 Make posts from a shoot, 4 My posting queue) and Open my Assistant folder as a small card. No recent-shoots list, no drop-down steps. Steps 1 and 3 open screens of their own:

- **Back up a card** (`/backups`): her two paragraphs, the light steps box (whether a card is in; "backup now" with Copy), and **Your backups**: the 10 newest, "Show 9 older backups" with month headings, a search by shoot name. Each backup: Card safe to format, Second copy made / No second copy, Something needs a look: see the report. Each shoot: To edit with its due date / Edited / Just for you, then Open this folder with See the report under it. A drive that isn't plugged in and a folder that was moved each have her line in place of a dead button.
- **Make posts from a shoot** (`/make-posts`): the steps box (Select the folder with your finished photos, then "make my posts" with Copy), and **Your post kits**: the 20 newest, Show older by month, a search that includes archived kits, Archive and Bring it back.

**Our way underneath.**
- New file `scripts/home_base.py`: her words whole in `WORDS` (ours, four lines, in `OUR_WORDS`), the look (her layout in `look.py`'s colours and font, no serif, nothing from the internet), both screens, what they read, the kit archive. `home.py` draws the home page from it. Routes on the posting server: `GET /backups`, `/make-posts`, `/home-data`, `/kit-thumb`, `POST /kit-archive`.
- **The cards of one shoot are one backup ("2 cards") from our own link** (`shoot.json`, written by `night.py --with` or `shoot_report.py link`), never from the backups' names. Two backups that only look alike by name ("Smith day", "Smith day, card 2") stay two.
- **A sample backup never says safe to format.** It says "Keep the card: this was a sample" (the report's own words). "Card safe to format" needs: finished, no problems, every file's copy checked, the second copy too when there is one.
- **Read live, nothing new stored.** Every backup's records are found where they are now (settled or not, `where.locate`), its manifest read once per change. See the report now finds a settled backup's records too (before, a queue record that still named the day folder said "Plug in the drive").
- **The kit archive is one small list,** `~/.studio/kit-archive.json`, with the list before kept beside it. A second press writes nothing. No kit is ever moved. A press is checked field by field behind the pickers' guard; a name that is not a kit in Your Content right now is refused in her words ("That shoot isn't in your content folder.").
- **Every shoot folder in Your Content that holds a kit record is listed,** also one whose page was never written (v25 section 10); its page is built when it is opened.
- **The page never sees a path.** A shoot is its id, a kit its folder name, a drive its name.
- **Another website cannot press the buttons.** The routes that open a folder window, the folder picker, a report or the queue (`/open-home`, `/open-drop`, `/open-shoot`, `/report-url`, `/pick-folder`, `/queue-url`) and `/home-data` now refuse a cross-site ask. Older than v26.
- **The pages follow what changes:** a backup that lands, a kit that is made, a shoot marked as delivered in the chat show on an open screen within a few seconds, without a reload.
- **Pressing a card no longer reloads the home page.** Before, recording a press changed the page's stamp, so the page reloaded and wiped the line a press had just put under its button.
- Every "Back to home" already went to `/home`; the editing queue's "Make posts from this shoot" now lands on a real screen. No port 8799 anywhere.
- The lines these buttons answer with say "your assistant", never "Claude".

**Choices where her spec was silent (plainest behaviour):**
1. A search inside a two-card shoot shows only the shoots that match; when only one card's shoot matches, it shows without "2 cards" (exactly what her page does).
2. A backup still running shows "Something needs a look: see the report" (hers: anything not finished is not safe).
3. A second copy counts as made only when every file's second copy was checked (hers: whenever a second place was named).
4. A shoot with video clips reads "20 photos and 4 video clips" (hers would say photos).
5. The kit search looks at the kit's name and its folder name (hers: the short name).
6. A kit's three small pictures are made the first time they are shown, one at a time, and kept.
7. A folder in Your Content with no kit record (made by hand) is not listed: there is no page it could open.
8. Today's last-backup line reads "Nov 13, 2026" (hers), not "yesterday".
9. With no Assistant folder yet, the folder card and the folder button say "There's no The Assistant folder yet. Ask your assistant to set one up." in place (the old drop-down with "set up my Assistant folder" to paste is gone with the drop-downs).
10. Post kit pages keep "Back to home" going to the home page (hers sent it to the Make posts screen only on her test copy).

**Hers left out, on purpose:** her three test-copy lines, `?home=test`, port 8799, the `/hp/` pass-through (one server here), the 20-second cache (ours reads each manifest once per change instead), grouping cards by name.

**Tests:** `tests/home_base_check.py` (new): 182 checks with the pages in a hidden Chrome, 103 without, on both Pythons. Her words are compared with her three pages both ways (ours in hers, hers in ours; her three test-copy lines are the named list left out). 28 behaviours were each taken out in a scratch copy and the test failed each time. In GitHub's check: without Chrome on Windows, with Chrome on the Mac's page job.

**Not tried:** Dustin's or Nicole's own hand; the Claude app's pane; a real backup, a real two-card shoot, a real drive unplugged (the tests use records and empty folders, and a drive name that is on no computer); hundreds of real backups (how long the first read takes); real photos in a kit's small pictures; Open this folder, the folder picker and See the report pressed for real from these screens (the test answers them inside the page so no Finder window or report server opens; the routes themselves are older and unchanged but for where a report's records are looked for); Windows (first push); a touch screen.

**Theirs to settle (for the note to Nicole, stage E):**
1. **"Single photos" is back on the Make posts card** (hers: "reels, carousels, single photos, stories and captions"). The Nov 11 fix round had taken "single photos" out, since the kit has no Singles card (a single post is a one-slide carousel). Built: hers, whole.
2. **"It also picks six photos from each shoot... and marks them "sneak peek" in Lightroom"** is on the Back up a card screen for everyone. True on a Mac for RAW shoots; a shoot of only video clips gets no sneak peeks, and JPEG shooters get no Lightroom mark. Built: hers, whole.
3. **Someone brand new sees "Nothing due and nothing waiting." under Today** (hers). Ours used to say "Once you've backed up a shoot or made some posts, what's due and what's ready to post shows up here." for a first-timer (Dustin, Nov 5: never list what is empty). Built: hers.
4. **The heading is always "Welcome to your home base."** "Welcome back." and "Hi, I'm Sherman." are gone from the page (the hello in the chat still follows how well they know it).
5. **"Edited" on a backup's shoot means marked as delivered** in the editing queue (her word here; the queue itself says Delivered). A delivered shoot that was then archived in the queue also reads Edited.
6. **Our lines:** "Keep the card: this was a sample"; "video clip(s)" in a count; the saved copy's "This is a saved copy. Ask your assistant to “show the Assistant” for the live one."
7. **A moved folder:** her line says "tell your assistant where it went", and the assistant has no way to re-point a backup's records. The instructions say to say so plainly and that moving it back makes the button work. A real re-point command is its own job.
8. **Archive asks nothing first** on a post kit (hers; the editing queue's Archive asks "Are you sure?").
9. **No chat command archives a kit** (the button only).

**For later stages:**
- Stage K (the post kit) and stage H ("make my posts" only brings photos in and opens the post kit): the Make posts screen's step 2 already says "Your shoot's post kit opens, and it shows up below."
- Stage C's "My editing queue" story fills from the queue: hers read `/home-data`'s `queue`; ours has no `queue` in `/home-data` yet. Add it there (names in queue order) or read `edit_queue` directly.
- `tests/kit_steps_check.py` has one check failing before and after this stage (her v26 post-kit.html no longer has two of our kit lines): stage K's.
- `home.card_in()` has a tests' switch, `STUDIO_CARD_FOR_TESTS` ("none" or "NAME:files"), so a test never looks at a real drive for a card.
- `home.fingerprint()` no longer moves when a press is recorded; it now moves when `kit-archive.json` changes.

## Stage B, the review round (Nov 14): the home base and its two screens

Two reviewers read stage B. Five should-fix findings and a handful of notes; all real, all fixed but the ones named at the end, each fix with a check that fails without it.

**Fixed.**
- **One backup is one backup, however the queue spells it.** A backup whose queue records named its records folder two ways (the day folder it settled out of, and where it settled to) showed as "2 cards", both labelled "card 1", with "Cards safe to format". Now each spelling is looked up first and shoots are grouped by where the records really are, so "N cards" comes only from our link (`shoot.json`). The same shoot of one backup listed twice in the queue shows once (the one still to edit, else the delivered one, else the first).
- **One odd record never blanks a list.** A queue record with a due date that is not a day, no id, or a records folder that is not text is left out (a bad due date: the shoot still shows, with no date); a kit record that is a list, or has a number for a date, no longer hides every other kit (`posts.kits`). When the Assistant cannot read the backups or the kits at all (an unreadable `queue.json`), the screen keeps the list it had, or says her "can't reach" line; it never says "Nothing backed up yet" or "No post kits yet". The post kits still show when only the queue is broken, and the home page still comes (before, `/home` dropped the connection).
- **A test can no longer put a window on anyone's screen.** New tests' switch `STUDIO_NO_WINDOWS_FOR_TESTS`: with it set, a folder window, a video player, the folder picker, CapCut, and the report and queue page servers all answer without opening or starting anything (`this_computer.no_windows()`, honoured in `finder.py`, `this_computer.pick_folder`, `serve_report.py`, `posting_queue.open_capcut`). `tests/home_base_check.py` and `tests/edit_queue_v26_check.py` run their servers with it; the home base test asks its server for the picker only after proving in the program that the switch holds. Use it in any test that starts a page server.
- **A long name with no place to break no longer makes a phone scroll sideways** (the Today lines on the home page, the "A card is in" line on the Back up a card screen).
- **A shoot's small picture reaches the page only as the queue's own** (`queue-thumbs/...`), never an absolute path or one with ".." from a queue file changed by hand.
- **The kit folder button's route (`/open`) also refuses another website's ask,** like the six listed before.
- **A damaged kit archive list is set aside whole** (`kit-archive.unreadable-<date>-<n>.json`), never copied over the last good list before; a list of the wrong shape is read as no list, never as names.
- **A kit's photo count is its pictures only** (a text file in its Photos folder is not a photo), as hers.
- **Instructions:** `parts/photos-in.md` and `parts/on-a-pc.md` now send people to the Make posts screen for the Select the folder button (they said the home page). `parts/hello.md` and `SKILL.md`: a press on Back up a card or Make posts from a shoot may only be someone looking at their backups or post kits, so it is answered first only when what they typed is about it or is nothing in particular; otherwise the assistant answers what they asked and marks the press seen.
- Small: the unused `home.kit_thumbs` is gone; a page left while its pictures load no longer writes a line in the server's log.

**Not changed, on purpose.**
- A kit's three small pictures are kept by folder name for good: a kit whose photos change keeps its old small pictures (the old home page did the same). Remaking them when the photos change is its own small job.
- A search for a kit that is archived says "No post kit called ... yet." above a closed "Archived (1)" that holds the match. That is exactly what her page does: hers to change (for the note to Nicole).
- `home.gather()` still collects recent shoots and kits the page no longer shows (the hello uses the kits).

**Theirs to settle, added to the nine above:**
10. **A press on step 1 or step 3 is still recorded,** and the instructions now treat it as possibly "just looking". Say if a press on those two cards should not be recorded at all (hers records nothing), or only the Copy press on "backup now" and the folder picker.
11. **The same shoot twice in the queue shows once** on the Back up a card screen (our choice; the editing queue itself still lists both).
12. **Searching for an archived kit** reads as "no such kit" above the closed Archived list (hers).

**Tests** (this Mac, pretend data, one at a time): `tests/home_base_check.py` is 213 checks with the hidden Chrome and 128 without (182 and 103 before). 23 behaviours of this round were each taken out in a scratch copy and the test failed each time. `tests/skill_text_check.py` holds the three instruction lines.

**A thing to know.** During this round's take-it-out runs, one run (the test's server started without the switch) opened a real folder picker on this Mac; it was closed straight away and the test now cannot do that. An older picker from the first build (process 20477, started 10:16 on Nov 14, "Pick the folder your finished photos are in...") may still be open: press Cancel on it. Nothing is behind it; whatever is chosen there goes nowhere.


## Stage C, built (Nov 14): the stories designer

**What a photographer sees** (all of it in the stories designer; the carousel's designer changes in one thing only, Redo).

- **"Show Instagram's guides"** is the tick's name, and her intro ends "Untick Show Instagram's guides to hide them."
- **The stories stay in view while the photos scroll under them.** Ours already did this (the stage has stuck to the top of the window since Nov 6, in both designers); it is now checked on the stories page with 40 photos.
- **"Let my assistant choose the photos"**, a button beside the photos' heading. It opens her box: "Tell your assistant what you want" (optional, 600 letters), her example, and the line to copy, "Pick my story photos for <shoot>", which ends ", and follow my note" only while there is a note. Copy says Copied for a moment.
- **The chat's side of it.** `design.py story-note "<kit>"` prints their note word for word and the set's frames in the order they are filled (which story, tall or wide, which are empty). `design.py story-fill "<kit>" --photos 3,8,12` puts the assistant's pick in. An open page shows the pick by itself within a few seconds (it looks for ten minutes after Copy is pressed) and says "Your assistant's pick is in your stories." The instructions are in `parts/arrange.md`, under "Making stories": choosing photos is the assistant's job, the note is theirs and comes first, and the words on a story are never touched (rule 11).
- **Her four templates, first among the layouts, in her order, with her placeholder words:** Gallery delivered (4 stories), My editing queue (1, no photo), The full story (10), Seamless swipe (6, one wide photo across the first three). Then her seven grids, as before.
- **My editing queue fills itself when it is added:** the shoots still to edit, in the queue's own order, each as they named it ("1   Garcia wedding"), twelve at the most and then "+ 2 more", with "If your shoot is on here, your gallery is on its way." under it. An empty queue says "Nothing in your editing queue right now". It is ordinary text from then on: they restyle it and can Save as template.
- **Redo** beside Undo (Cmd+Shift+Z or Cmd+Y; Ctrl on a PC), in both designers. A new change empties it.
- **Sets of stories.** The name box, "My story sets ▾" and "+ New set of stories" show in stories, like a carousel's designs. Duplicate is not shown (hers). This replaces "one stories design a shoot".
- **A small x on each story's label** removes that story, even an empty one; the stories after it move up; the line says "Removed story 6. Undo brings it back."

**Our way underneath.**
- **A shoot's one stories design from before is its first set:** the same file in `story-designs/`, opened as it was, nothing written by opening it. A new set is a new file beside it ("<Shoot> stories 2"). There is still no way to delete a set.
- **Which set the kit shows:** the set **saved** last (`kit.json` `stories_set`, as before), whichever set it came from; while no stories are saved, the card's small picture is of the set **changed** last. Exactly what a carousel's designs do, with no new code in `kit.py`. Save stories names the files after the set ("Beach stories 2 - 01.jpg").
- **The note is kept with the set, never in its layout** (`ask` in the set's record; hers keeps it inside the layout). So a note changes no story, no Undo step and no "Already saved": a set saved, then given a new note, still says "Already saved as ...". It is checked like a name (text, 600 letters, no control characters) and reaches the page only as text. A carousel's design takes no note.
- **The assistant's pick is written like any change:** under the design's lock, checked like a layout from the page, the set as it was kept beside it, the counter one higher, so a page that has not seen it is told there is something newer and never saves an older layout over it. The same pick again writes nothing. It refuses more photos than there are frames, a number that is not on the kit's sheet, and a photo given twice, and changes nothing when it refuses. It never adds, changes or removes a text box.
- **The queue's names come from a route of the designer's own,** `GET /design-queue` (names and a count, nothing else; refused to another website and to another host's name), read from `edit_queue` the moment the template is added. Not from `/home-data`, which has no queue in ours. A queue that can't be read gives her line, "I can't reach your editing queue right now.", in the Add stories window, which stays open, and nothing is added.
- **The page opens the set its address names,** so a reload stays on the same set (hers opens the newest on every load). With no set named it opens the one changed last.
- **Saved stories and slides are byte for byte what they were.** Nothing that draws them changed (`design_js_paint.py`, `design_js_save.py`, `design_js_type.py`, `design_js_text.py` and `design_js_model.py` are untouched), and it was tried once by hand: two pretend shoots with the very same photos, one served by the code as it was before this stage and one by the code as it is, the same presses on each page (five stories with a text box in Figtree, Save stories; the carousel's first design, Save slides). All five stories and all seven slides came out byte-identical.
- New file `scripts/design_js_ask.py` (the button, the box, the follow). The page's words for it are in `design_page.py` (`ASK_*`), hers whole.

**Choices where her spec was silent (plainest behaviour).**
1. `story-fill` fills the **empty** frames, in the page's own filling order. `--replace` puts the pick into every frame; the instructions allow it only when they asked to choose again. A set with no frame at all gets one story for each photo, each filling its story.
2. With no `--design`, the chat's commands take the set changed last (the one they were just typing the note into) and list the others.
3. "+ New set of stories" opens the new empty set without throwing the Add stories window over it (hers); that window still opens by itself when a page opens on a shoot whose stories are empty.
4. The x is on stories' labels only (hers), and is not shown at one story. Its line is in the bar's first line, beside the Slides line (hers: the bottom line).
5. Redo is emptied by any new change of theirs, not by a text box's height being set right when its font arrives.
6. A template that is added lands on the set's own background (hers does the same: a template's cream background is only ever seen on its card in the window).
7. The card of My editing queue reads "1 story · 0 photos" (hers: "0 photo").
8. Copy uses the older copy call only, the one the Claude app's pane allows (the designer page has a rule against the newer one; hers falls back to it).
9. From 1024 to 1179 px wide the slider that sizes the slides loses its word "Size" and is a little shorter, so the slides' row stays one row with Redo in it and five brand colors saved.
10. A shoot's name in the queue story is one line, 80 letters at the most (as a design's name is cleaned).

**Hers left out, on purpose.** Her `askQueueNames` box ("How should your clients show?": full names, first names, initials, no names) and the due dates and counts beside it: they are in her file but nothing calls them (her note: "a busier first version was too much"). Her browser-storage memory of which set was open (ours is the address). Her idea for later, offering a Gallery delivered set when a shoot is marked delivered.

**Tests.** `tests/design_v26_check.py` (new; `design_check.py --only v26`, or by itself with `--work`): 205 checks with the real page in a hidden Chrome (her words looked for in her page when her folder is beside the project, her four templates number for number, the rules by themselves, every route and refusal, the two commands, and the page driven with a real mouse and keys). Thirty pieces of the new behaviour were each taken out in a scratch copy and the test failed each time (seventeen by request, thirteen on the real page). `tests/pc_design.py` has a part 15 for a PC (sets, the note, the pick, the queue's names; no page). `tests/skill_text_check.py` holds the instructions. The older stories, v22, save and layout checks were brought up to date where they said "one stories design", "seven layouts" or "Show Instagram's buttons". In GitHub's check: the new file in the Mac's page job, part 15 on Windows.

**Not tried.** Dustin's or Nicole's own hand; the Claude app's pane (Copy was pressed in a hidden Chrome, where the copy call was stood in for; the pane's own clipboard was proved for the home page on Oct 30, not for this box); a fresh session following the new instructions from the pasted line; a real shoot's photos and a real editing queue; the assistant actually choosing photos from a sheet for stories; a wide photo across three stories saved and looked at on a phone; her templates' words in Figtree with no internet (Figtree comes from Google; without it they show in Georgia, as any story text does); a second window open on the same set while the pick arrives; a real PC (the first push runs part 15 there); a touch screen (the x is 17 px drawn, with a larger area that takes the press).

**Theirs to settle (for the note to Nicole, stage E).**
1. **A template lands on the set's background, not its own.** Gallery delivered, My editing queue and The full story are cream in the window and white on the stories unless they change Background (hers does the same). Say if a template added to an EMPTY set should bring its background.
2. **Our lines where hers has none:** "Your assistant's pick is in your stories."; the name box's and the menu's names for a screen reader; the tooltip of + New set of stories; "That set of stories isn't here, so this is your newest one."; the two lines when a new set can't be made; "That note is longer than fits. Keep it under 600 letters." (never seen from the page: the box stops at 600).
3. **The assistant fills empty frames only, unless asked to redo.** Say if "Pick my story photos" pasted a second time should replace the photos already there.
4. **No command puts the earlier photos back** after a pick they don't like. The set as it was is kept on the drive, and the page's Undo does not reach across the pick. The instructions say: pick again, or they move photos themselves. A "put it back" command is its own small job.
5. **The page follows the assistant's pick for ten minutes after Copy.** After that a reload, or "show my stories", shows it.
6. **Duplicate is not offered for a set of stories** (hers).
7. **The word "Size" is hidden between 1024 and 1179 px** (item 9 above).
8. **Client names on a public story.** My editing queue shows each shoot as it is named in their editing queue (hers, by her choice: the names question was "too much"). They can take a name off by hand.

**For later stages.**
- Stage K (the post kit): the Stories card counts "saved designs"; with sets, her v26 post kit may word it differently. The card's link opens the stories designer with no set named, so it opens the set changed last.
- Stage E: carry the eight items above into the note for Nicole; CLAUDE.md should say sets of stories replaced one design a shoot, and that Redo is in both designers.
- `design_js_designs.py`'s `makeDesign` now sends the kind (before, only a carousel ever made a new design from the page).
- The designer's routes gained `GET /design-queue` (`posting_queue.py` hands it to `design.handle_get`). `/home-data` still has no `queue`.
- A test that starts a page server for the designer should set `STUDIO_NO_WINDOWS_FOR_TESTS`, as the new one does.
