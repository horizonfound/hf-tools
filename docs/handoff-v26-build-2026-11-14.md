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
2. With no `--design`, the chat's commands take the set they pressed Copy on, or changed, last (see the review round below) and list the others.
3. "+ New set of stories" opens the new empty set without throwing the Add stories window over it (hers); that window still opens by itself when a page opens on a shoot whose stories are empty.
4. The x is on stories' labels only (hers), and is not shown at one story. Its line is in the bar's first line, beside the Slides line (hers: the bottom line).
5. Redo is emptied by any new change of theirs, not by a text box's height being set right when its font arrives.
6. A template that is added lands on the set's own background (hers does the same: a template's cream background is only ever seen on its card in the window).
7. The card of My editing queue reads "1 story · 0 photos" (hers: "0 photo").
8. Copy uses the older copy call only, the one the Claude app's pane allows (the designer page has a rule against the newer one; hers falls back to it).
9. From 1024 to 1179 px wide the slider that sizes the slides loses its word "Size" and is a little shorter, so the slides' row stays one row with Redo in it and five brand colors saved. **This is in both designers, the carousel's too** (Redo is in both), so it is a second small change to the carousel's page beside Redo.
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
7. **The word "Size" is hidden between 1024 and 1179 px, in both designers, the carousel's included** (item 9 above).
8. **Client names on a public story.** My editing queue shows each shoot as it is named in their editing queue (hers, by her choice: the names question was "too much"). They can take a name off by hand.

**The review round (Nov 14).** Two reviewers; every should-fix was real and is fixed, each with a check that fails without it.
- **The assistant fills the set they asked about.** The line they paste names no set, so with two sets the chat took the one changed last, which could be a different one from the set open on the page. Now Copy tells the Assistant which set it was pressed on (`POST /design-asked`: only a time, `asked`, is noted in the set's record; its stories, counter, name, note and the version kept beside it are untouched), and `story-note` and `story-fill` with no `--design` take the set asked about, or changed, last, whichever is later.
- **`story-fill` is safe to run twice.** The very same command again answers `SAME:` and writes nothing, with or without frames to start from (before, a pick that left frames empty was put in a second time, and a set that had no frames answered with a refusal). A photo that is already in the set is refused rather than put in twice, unless `--replace`.
- **The pick never lands under their hands.** With the caret in a box (a story's words, the set's name, a size) the page waits and takes the pick when they leave the box. A note they are typing while the newest set arrives stays in its box and is saved with the set.
- **A page's lost save, sent again after the assistant's pick, never wipes the pick:** this already held; it now has a check.
- **`story-note` reads right:** a frame across several stories is "stories 1 to 3" (it said "story 2 (across 3 stories)"), and a frame of no particular shape "takes any photo".
- Smaller: one odd record in the editing queue no longer makes My editing queue say it can't reach the queue; a note that is not text at all is refused with the plain "couldn't understand" line, not "longer than fits"; a shoot's folder with a quote in its name is quoted in the command lines the commands print, so they run as pasted.
- **Left as they are, and theirs to settle:** (9) a set with several BLANK stories and nothing on them keeps those blank stories in front of the assistant's pick (our page's own Add stories has done the same since v19; in hers a set with nothing on it is simply replaced by what is added); (10) a new set is "<Shoot> stories" when that name is free (the first set was renamed), where hers would count the sets and say "<Shoot> stories 2"; (11) when a page's save is refused because the assistant's pick is newer, the line is the usual "This design was changed somewhere else. Here's the newest.", which reads oddly when the "somewhere else" is the assistant they just asked: the wording is theirs; (12) a photo already in the set is refused on a second pick without `--replace` (so the assistant never puts one photo in twice by accident; they can still do it by hand).
- Tests after the round: `design_v26_check.py` 238 with the page (165 without), `pc_design.py` 247 (246 on Apple's 3.9), `skill_text_check.py` 432. Twelve pieces of the round were each taken out in a scratch copy and a check failed each time (nine by request, three on the page).
- Not tried: the typing wait with the caret in a real story's text box by hand (the check uses the set's name box and a box made for the test); Copy's note of the set in the Claude app's pane.

**For later stages.**
- Stage K (the post kit): the Stories card counts "saved designs"; with sets, her v26 post kit may word it differently. The card's link opens the stories designer with no set named, so it opens the set changed last.
- Stage E: carry the eight items above into the note for Nicole; CLAUDE.md should say sets of stories replaced one design a shoot, and that Redo is in both designers.
- `design_js_designs.py`'s `makeDesign` now sends the kind (before, only a carousel ever made a new design from the page).
- The designer's routes gained `GET /design-queue` (`posting_queue.py` hands it to `design.handle_get`). `/home-data` still has no `queue`.
- A test that starts a page server for the designer should set `STUDIO_NO_WINDOWS_FOR_TESTS`, as the new one does.


## Stage D, built (Nov 14): the report after a backup

Nicole's notes, section 2 (and the intro from section 1). The naming question itself is untouched: it waits on the owners.

**What a photographer sees on the report.**
- **Why there are several folders,** above the shoots, when the card held more than one shoot and they are filed: her line, "Since these were two days, I put them in two separate folders. You can name them in the boxes below." It is used only when that is what happened (every shoot one day of its own). Any other split (two shoots in one day, three shoots over two days, a shoot across midnight) gets ours, which claims no days: "Since these looked like two different shoots, I put them in two separate folders. You can name them in the boxes below." The count is in words up to twelve.
- **Each shoot has its own "Open this folder"** under its name box, and what happened is said right under that button ("Opened 2026-06-24 Beach in Finder."). The where-box at the bottom stays.
- **"Does everything look right? If so, add it to your editing queue."** right above Add to my editing queue. It goes when the shoot is in the queue.
- **The sneak peeks explained:** "I picked six photos that could be great sneak peeks to send your client. They're marked 'sneak peek' in Lightroom, if you want to do a quick edit on them." then Dustin's "Not feeling them? Just say what you'd rather see." and the two buttons, Pick again and Show me more, as before. The first sentence is bold.
  - **JPEG shooters (and HEIC, DNG, TIFF, PNG) are never told their picks are marked in Lightroom,** since they are not: "They're the ones shown here. They aren't marked in Lightroom: to mark this kind of photo (a JPEG, for one) I'd have to write inside it, and I never change your photos." Some of each: "Four of them are marked 'sneak peek' in Lightroom... The others are a kind of photo I'd have to write inside to mark, and I never change your photos."
  - A shoot with three to five picks (an older backup) says its own number and has no buttons, as before.
- **The next step, once, under the shoots:** "Open your folder to start editing. When your edits are done, come back to your home base and click Make posts from a shoot." A card of only video clips gets only the first sentence. On a shoot's page for several cards it is said once for the whole shoot, not in every card's section.
- **The old line is gone everywhere:** "Whenever you're finished with your edits, let me know and I'll turn your favorites into a reel." was only ever said in the chat (the end of a backup, and the reel skill when all it had was a backup). Both now say the new next step.
- **The setup intro** (`parts/first-backup-setup.md`) has a third part, between what was found and the "few quick questions" line: "Here's what's about to happen. I'll copy every photo to your drive and check each one against the card. If the card has more than one shoot on it, each one goes in its own folder, and you can name them on the report afterwards. Then I'll pick a few sneak peeks from each shoot, and you'll get a report that shows all of it."
- **Video-clip-only shoots keep their own words** ("5 video clips", See all 5 video clips, Open video folder); they also get Open this folder and the look-right line.
- **The report's lines say "your assistant", never "Claude"** (thirteen lines on the page and three the report's server answers with).

**Our way underneath.**
- New words live in `first_look.WORDS` (hers) and `first_look.OUR_WORDS` (ours, drafts).
- **`GET open-shoot?shoot=<id>` on the report's server** (`serve_report.py`): the page sends a shoot's id and nothing else. The folder is the one the backup's records name for that shoot at that moment (so a rename or a settle is followed), and it must be inside the place the backup's photos are in; records changed by hand to point anywhere else open nothing. Another website's ask is refused (403). A folder that is gone gets the Back up a card screen's own line ("I can't find this folder anymore. If you moved or renamed it in Finder, tell your assistant where it went."; File Explorer on a PC). It works inside each card's section of a several-card page (`/card/N/open-shoot`).
- Whether a pick is "marked in Lightroom" is told from the kind of file (`sneak_peeks.NO_SIDECAR`), so it is right with the drive unplugged too.
- Two older faults the new test found, fixed: a press on the where-box's button also ran the Rename code and threw an error in the page (nothing was renamed; the handler was bound to every `.go`); and at a narrow phone width (336) the green "safe to format" pill made the report scroll sideways.

**Choices where her notes were silent.**
1. Her folders line takes the place of the older lede ("Each one is already in its own folder, named by date...") when it shows; one shoot keeps the older lede.
2. No folders line while shoots are not filed yet, and no Open this folder on a shoot with no folder.
3. Open this folder sits between the name box and the editing queue line.
4. "Not feeling them? Just say what you'd rather see." (Dustin, Nov 5) is kept after her sneak peeks line, since the two buttons need a lead-in.
5. The next step is one box under all the shoots, not a line per shoot.
6. A press on Open this folder answers under its own button, not in the page's bottom toast.
7. With six picks of mixed kinds, the count that are marked is said as a word ("Four of them").

**Hers left as it is, and theirs to settle (for the note to Nicole, stage E).**
1. **"to send your client" is said for every shoot,** also one that is just for them (hers, whole).
2. **Our line when the split was not days** ("Since these looked like two different shoots...").
3. **Our JPEG lines** for the sneak peeks, and "{Four} of them are marked...".
4. **Our come-back line** ("When your edits are done, come back to your home base and click Make posts from a shoot."), and that a card of only video clips is not told to make posts.
5. **Her line for a moved folder promises something the assistant cannot do** (same as stage B's item 7).
6. **The setup intro's words** are ours (she asked for the intro, gave no words).
7. A photo that already had a sidecar of the photographer's own (rated in Lightroom before) is counted as marked by its kind, though the Assistant left that sidecar alone. Rare; not handled.

**Not built, on purpose:** the folder-naming question and its choices (waiting); anything in `night.py` (it prints no closing words; the chat's closing words are in `parts/backup.md`).

**Tests:** `tests/report_v26_check.py` (new): 103 checks with the page in a hidden Chrome and Pillow, 98 on Apple's Python (no Pillow: Show me more on the pretend backup with pictures is skipped), 77 without Chrome. Its pretend backups are made with no add-on, so every part but that one runs on both Pythons. 23 behaviours were each taken out in a scratch copy and the test failed each time. In GitHub's check: without Chrome on Windows, with Chrome on the Mac's page job. Also run after the change, both Pythons: `shoot_report_check.py` (42; needs Pillow), `clips_check.py`, `peek_check.py`, `look_check.py` (75), `skill_text_check.py` (432), `pc_smoke.py` (230 / 183), `home_base_check.py --no-chrome` (128); both tool checks clean.

**Not tried:** Dustin's or Nicole's own hand; the Claude app's pane; a real backup's report; a real Finder window from Open this folder (the tests run with the no-windows switch); Rename followed by Open this folder on a real sorted backup (the route is checked against changed records; the pretend backups cannot be renamed for real); a shoot renamed while its page is open; a PC (first push); a touch screen.

**For later stages.**
- Stage E: carry the seven items above into the note for Nicole. CLAUDE.md: the Oct 24 "handoff line" is retired; the report has Open this folder per shoot and `GET open-shoot`; the report's lines say "your assistant".
- Many other pages still say "Tell Claude" (the pickers, the designer, the posting page, the kit, reminders): not this stage's. Their tests hold those words, so changing them means changing both.
- `first_look.shoots_section(studio, closing=True)` has a new argument; `first_look.closing_html(photos, wrap)` and `first_look.NEXT_CSS` are what the shoot's page uses.
- The older tests' pretend backups (`tests/fake_night.py`) cannot be renamed for real ("no sorted photos found"); a test that needs a real rename needs `original` records.


## Stage G, built (Nov 14): several reels from one shoot

Nicole's v25, section 2: "There's other photos from this shoot that I want to make as its own separate reel. And I don't want to deselect everything and lose it. I just want to start a new one."

**What a photographer sees.**
- **On the reel page, a bar under the title: "Your reels".** A drop-down of the shoot's reels, **+ Start a new reel**, and **Rename** (the name turns into a box with Save and Cancel; Enter saves, Escape cancels). Her words, her layout, her styles.
- **+ Start a new reel** saves the reel they were on exactly as it is, then opens a blank one: "I'll drag them in myself" with nothing in it, no pick of the assistant's, footage not chosen, no song, and every clip found for the shoot, as found. The page reloads on it (hers).
- **Choosing another reel in the drop-down** saves first, then reloads on that reel, exactly as they left it.
- **Names** are "Reel 1", "Reel 2" and so on until renamed (the next number that is free, as hers).
- **Every reel is fully separate:** photos, order, Longer and Quicker, the song picked, footage or just photos, the style, the vibe, the clips with their lengths and which are selected, their notes and feel, and the assistant's picks. The songs in the Music folder and the videos in the Footage folder are the shoot's.
- **On the talking reel page, the same bar: "Your talking reels"** and **+ Start a new talking reel**. A new one starts at step 1 with no video chosen. Each has its own video, script edit, cuts, photos, zooms and captions; two may use the same video and cut it differently. Names are "Talking reel 1", "Talking reel 2".
- **While a video is being turned into a script,** the page will not start or open another talking reel: "I'm still turning your video into a script. Give it a minute, then try again." (hers). Rename still works.
- **In CapCut** nothing changes: projects are named for the shoot, "<shoot> reel", then "<shoot> reel 2", whichever reel on the page they came from (hers does the same). Talking reels: "<shoot> talking reel", then "... talking reel 2".

**Our way underneath.**
- **One new file, `scripts/reels.py`,** holds the list for both records. Her record shape is kept: `versions` is a list of `{id, name, data}`, `current` is the open reel's id, the open reel's fields stay at the top of the record, the others wait in their `data`. Nothing is ever dropped; there is no way to remove a reel.
- **A shoot with one reel is byte for byte as before.** No list is written until a second reel is started (or the first is renamed). Checked against the code before this stage, out of git: the same saves give the same bytes in `reel-page.json`, its `.prev`, `talking.json`, its `.prev` and `talking-words.json`. One exception, on purpose and hers: a **new footage look** (`footage.py moments`) now also writes `moments_found`, every clip found for the shoot, which is what a new reel starts with.
- **Where hers and ours differ in the record, and why.** In hers the assistant's pick (`claude`) is always in the reel record. In ours the pick has always lived in the kit's own record (`kit.json`, `picks.reel` with `reel_marks` and `reel_earlier`), which the post kit, the posting queue and every older kit read, and which the page server never writes. So: **the shoot's first reel keeps its pick in `kit.json`, exactly as before; every reel started after it keeps its own in the reel record** (`claude`, with `claude_earlier`, the last 12 picks it replaced, and `claude_at`). A pick for one reel never changes another's.
- **Nothing of one reel can be written into another.** Every save, every clip change and every Make my reel from the page says which reel the page is showing. When another window has started or opened a different reel, that ask is refused, nothing is written, and the page is given the newest and shows it. Starting, opening or renaming a reel also moves the record's counter, so a page a step behind is told there is something newer (the rule the page already had).
- **Saved whole, the version before kept,** under the record's own lock, as every change to these records is. Opening the reel that is already open, the same name again, and the same pick again each write nothing.
- **A reel being made knows which reel it is.** The job is written down with the reel it was started on, so the reel is made from that reel's clips and noted as that reel's, also when they open another reel while it is being made. `made` entries carry `version` once a shoot has several reels; an entry without one is the first reel's (hers).
- **The next mix is each reel's own.** Making a reel again with the same photos, vibe and style gives the next mix of that reel; another reel with the same photos starts at its own first mix. (Hers counts every make of the shoot together.)
- **The chat's commands act on the reel being worked on, and can name another:** `kit.py picks --reel ... [--for-reel "<name>"]`, `footage.py scan` and `moments [--reel "<name>"]`, `reel_page.py show` and `make [--reel "<name>"]`, `talking_rec.py status / show / cut / photos / place [--reel "<name>"]`. When a shoot has more than one, each says first which reel it is about. A few words of a name are enough when they fit only one reel; a name that fits none stops and lists the reels. Naming another reel changes that reel only: the one open on the page stays open and untouched.
- **New, for the chat:** `reel_page.py reels "<kit>"` lists the reels; `--new [--name]`, `--open "<name>"` and `--rename "<name>" --to "<name>"` are the page's three moves from the chat, through the same checks.
- **The talking record:** every key but the list, the open reel's id and the record's own counter (`v`, `rev`, `updated`, `from`) belongs to the reel being worked on (hers: every key but `versions` and `current`). The words of a video are never put away with a reel: they are the video's, kept beside (`talking-words.json`). A reel that comes back up on words that were made again since has its edit started afresh, what was there kept, as a video's edit always was.
- **A numbered list that is re-made** (a photo exported again) finds every reel's photos again by file name, the put-away reels too.
- **The routes** are `POST /reel-version` and `POST /talking-version` on the Assistant's one page server, behind the pickers' same-page-only guard, every field checked; another website's press, another host's name and a cross-site press are refused. A reel's name reaches the page as text only. The page never sees a path.
- **One bar, two pages:** the bar's markup and script are the reel page's (`reel_page.reels_bar`, `REELS_JS`), used by both.

**Choices where her spec was silent (plainest behaviour).**
1. **Two reels of one shoot can't share a name** (ours; hers allows it). The chat tells reels apart by name. The line is ours: "Another reel of this shoot already has that name. Give this one a different name."
2. **A refused name leaves the Rename box open** with the line that says why (hers closes the box and shows the line).
3. A name is one line of plain text, 40 letters at the most (her box's length); a name that is only spaces is "Give the reel a name." (hers).
4. **A shoot keeps at most 99 reels** (hers has no end; nothing can be removed, so there is one). Ours: "A shoot keeps up to 99 reels. Rename one you're done with and use it again."
5. **The talking page also refuses a new or other talking reel while a reel is being made in CapCut** (ours: "I'm still making this reel in CapCut. Give it a minute, then try again."). Hers makes a reel inside one request, so the question never comes up there.
6. A new reel's clips come without the mark of a length they set in another reel. For a record from before `moments_found`, a new reel starts with every clip any reel still has that is not their own (hers).
7. `kit.py picks --for-reel` with no `--reel` is refused; a pick for a later reel is checked before anything is written (a wrong number changes nothing anywhere).
8. After the assistant picks for a reel that is on "I'll drag them in myself" (every new reel is), the pick waits under "Let my assistant choose", as it does today for the first reel. Stage H's line ("Your assistant hasn't picked for this reel yet...") goes here.
9. The post kit's Reel card and the posting queue's cover photos show **the reel being worked on** (hers did the same before her per-reel previews). Stage K gives each reel its own.
10. The older reel picker (`arrange.py`, opened by name, linked from nowhere) still writes the first reel's pick.
11. The talking page's bar says that page's own "can't reach" and "didn't work" lines when a press does not go through (her talking page shows its own post's words there).
12. Rename moves the record's counter too, so another open window shows the new name within a few seconds.

**Hers left out, on purpose.** Nothing a photographer sees. Her `photoLine()` (the copy line with the reel's name) is stage H's.

**Tests.** `tests/reels_check.py` (new): the list by itself, her words both ways against her v25 pages and server, the reel page and the talking reel by request, a shoot with one reel byte for byte against the code before the stage, a reel made into a pretend CapCut folder, and both bars in a hidden Chrome (her words, + Start a new reel with a change saved first, the drop-down, Rename with Save, Cancel, Enter and Escape, a name with a tag in it shown as letters, a phone's width). 158 checks with the pages (131 without), the same on both Pythons. 46 pieces of the stage were each taken out in a scratch copy and a check failed each time (34 by request, 12 on the real pages). `tests/skill_text_check.py` holds the new instruction lines to the scripts (443 checks). In GitHub's check: by request on Windows, with the pages on the Mac's page job.

Also run after the change, one at a time, both Pythons, all passing: `reel_page_check.py` 343, `reel_fixes_check.py` 41, `reel_door_check.py` 47, `reel_footage_check.py` 183, `footage_look_check.py` 88, `posting_panel_check.py` 88, `arrange_check.py` 660, `talking_page_check.py` 573, `talking_multi_check.py` 92, `talking_menus_check.py` 108, `talking_snap_check.py` 48, `talking_rec_check.py`, `talking_engine_check.py`, `talking_capcut_check.py`, `pc_reel_page.py` 49, `pc_talking.py`, `pc_smoke.py` 230 (183 on Apple's 3.9), `look_check.py` 75; `tools/check_pc.py` and `tools/check_plugin.py` clean. `kit_steps_check.py` (98 of 99) and `kit_cards_check.py` (125 or 126 of 127) fail only on what they failed on before this stage (see "For later stages").

**Not tried.** Dustin's or Nicole's own hand; the Claude app's pane; a real shoot; a real reel made from a second reel and opened in CapCut; a talking reel made from a second talking reel; two real windows by hand (the checks send what a second window would); a fresh session following the new instructions; Windows (the first push runs it); a touch screen; a screen reader reading the bar.

**Theirs to settle (for the note to Nicole, stage E).**
1. **Two reels can't share a name**, and a refused name keeps the box open (choices 1 and 2).
2. **At most 99 reels a shoot**, and no way to remove one. Say if a reel should be removable (it would go nowhere: kept in the record, only hidden).
3. **Our three lines:** the name-taken line, the 99 line, and "I'm still making this reel in CapCut. Give it a minute, then try again."
4. **CapCut's projects are named for the shoot, not the reel** (hers too). With two reels called "Kitchen" and "White backdrop", CapCut shows "<shoot> reel" and "<shoot> reel 2". Say if the reel's name should be in the project's name.
5. **The next mix is each reel's own** (hers counts the shoot's makes together).
6. **The first reel's pick lives in the kit's record, later reels' in the reel record.** Nothing they can see; said so it is known.
7. **Remove a song** is still not built and is hers to answer (the waiting list, item 1).

**For later stages.**
- Stage H (the photo note): `photo_ask` belongs in `saved`, so it is per reel by itself; add it to `reel_page.SAVE_FIELDS` and to `reel_fresh`. The copy line's reel name is `window.Reel.reels.name()` (the name, or "" when the shoot has one reel). "Checks the record's current reel matches the name" is `reel_page.py reels "<kit>"`, and `kit.py picks --for-reel`.
- Stage I (trim): clips are per reel (`moments` at the top of the record is the open reel's); `reel_fresh` drops the "set" mark for a new reel.
- Stage J (songs): the Music folder is the shoot's; which song is picked is `saved.song`, per reel already.
- Stage K (post kit, posting queue): one reel's own fields are `reel_page.as_reel(rec, id)` (a copy to read); its pick is `reel_page.assistant_pick`; whose a `made` entry is, `reel_page.made_for`; the list, `reels.listed(rec, reel_page.REEL_FIRST)`. `kit.json`'s `reel` is the newest reel made, of any reel. `order_for_kit_page` is the open reel.
- The bar's words are in their own tables (`reel_page.REELS_WORDS`, `talking_page.REELS_WORDS`), checked against her v25 pages by `tests/reels_check.py`; `reel_page.WORDS` is still compared with her v19/v23 page by `tests/reel_page_check.py`.
- `tests/kit_cards_check.py` has two failures that are older than this stage (shown on the code as committed before it): `need_both` / `need_caption` (stage K's), and "nothing was asked of the internet by the kit page" (it asks Google for Figtree; it came with the stories designer).

## Stage H, built (Nov 14): the photographer picks

Nicole's v25, section 3: "You're not supposed to do any of that. I choose, not you." And section 10: "make my posts" should only bring the photos in and open the post kit.

**What a photographer sees.**
- **"Make my posts" brings the photos in and opens the post kit, and stops.** Nothing is picked, nothing is made, nothing is written, and nothing is asked about the shoot. The same after "I'm done with the beach shoot".
- **On the reel page, a reel with no pick says her line** under Let my assistant choose: "Your assistant hasn't picked for this reel yet. Tell it which photos you'd like below, then copy the line into the chat." (The older line, "...for this shoot yet. In the chat, say...", is gone.)
- **Under the two choices in "Put your photos in order", her note box:** "Tell your assistant which photos you'd like in this reel", "Optional, and only for this reel.", her two examples, and the line to copy with a Copy button. The line is "Pick my reel photos for <shoot>", with the reel's name after the shoot only when the shoot has more than one reel, and ", and follow my note" only when there is a note.
- **The note is each reel's own** and is saved by itself as they type.
- **When they paste the line,** the assistant reads the note first, picks only what it allows, saves the pick for that reel only, and says in a line how it read the note. The pick waits under Let my assistant choose, as before.

**Our way underneath.**
- The note is `photo_ask` in the reel's `saved` (her name), checked like every field the page saves: text, her 600 letters at the most, the whole save refused if it is wrong. Because it sits in `saved` it is per reel by itself (stage G).
- **New, for the chat: `reel_page.py note "<kit>" [--reel "<the reel the line names>"]`.** It changes nothing. It prints which reel the pick is for, whether that is the reel open on the page, the note word for word, and the command that saves the pick for that reel only. A name that fits no reel stops and lists the reels. `reel_page.py show` prints the note too, and `kit.py picks --reel` says the note again after it saves.
- The words are in their own table, `reel_page.PICK_WORDS` (hers, word for word), and the box's styles in `PICK_CSS` (her three rules, two of ours).
- `kit.py start` now ends "Next: kit.py sheet (it numbers the photos for the pages), then show the post kit. Nothing is picked or made until they ask."
- **The instructions:** `parts/post-kit.md` (a kit only numbers the photos and opens the kit page; no question; the picks and the plain pieces moved to "Only when they ask"; the voice question waits for the first caption they ask for), `parts/photos-in.md`, `parts/arrange.md` (who chooses; the note box; the pasted line in five steps; the carousel picked only when asked), the reel skill (Step 2 runs only when they ask, their note first), `shared/curating.md` (you choose only when they ask; the note decides what may go in; the marking rule and the alike-photos rule stay for when it does pick), the core's rule on choosing, `parts/hello.md`, `parts/canva.md`, `parts/where-things-live.md`, and one line `footage.py scan` prints.

**Choices where her spec was silent (plainest behaviour).**
1. **The line names a reel that is not the one open on the page:** the pick goes to the reel the line names (`--for-reel`), the page stays where it is, and the assistant says which reel the pick went to. Hers says only "checks the record's current reel matches the name".
2. **The line says "and follow my note" but the note has been cleared since:** pick from the whole shoot and say there was no note.
3. **Nothing in the shoot fits the note, or the sheet can't show which photos it means:** the assistant says so and asks one short question. It never fills in with photos the note leaves out.
4. **The note is kept as typed** (her page trims the spaces round it; ours sends it trimmed too) and a note that is not text, or is over 600 letters, refuses the save (hers cuts it at 600 without a word; her box cannot hold more either way).
5. **A note written in another window** shows in the box when the box is not under their hand; it is never changed while they are typing in it.
6. **A footage look ("Look through my footage") is not a reason to pick photos.** Before, the instructions and `footage.py scan` told the assistant to pick the reel's photos first when there was no pick. Now they say: find the moments only.
7. **"Make a reel" from the chat** makes the kit if there is none, numbers the photos and opens the reel page, with a line of ours to say ("Your reel page is open beside us. ... If you'd rather I pick the photos, tell me which ones you'd like in the box under Put your photos in order and copy the line there into the chat."). It picks only when they also ask for a pick.
8. **`kit.py sheet` still runs when a kit is made** (the pages need the numbered list), but the assistant is told not to read the sheets. `posting_queue.py add --kit` still runs: the reel and the carousel go in as not started.
9. **What they say about the shoot unasked is still kept** (`kit.py told`), for the words step.
10. **The carousel and the plain singles, stories and cover** are picked and made only when they ask in the chat; the commands are unchanged.

**Hers left out, on purpose.** Nothing of section 3. (Section 10's "the home page lists a shoot without Post kit.html" is stage L's.)

**Tests.** `tests/picks_ask_check.py` (new): her words both ways against her v25 reel page; the note by request (saved, refused, each reel its own, another website refused); `reel_page.py note`, `show` and `kit.py picks`; a new kit that picks and makes nothing; and the box on the real page in a hidden Chrome (her words, where it sits, the line with and without the reel's name and the note's ending, saved as they type, Copy, a second reel, Rename, a pick arriving, a phone's width). 76 checks with the page (51 without), the same on both Pythons. 21 pieces were each taken out in a scratch copy and a check failed each time. `tests/skill_text_check.py` has a new section for this stage (472 checks). In GitHub's check: by request on Windows, with the page on the Mac's page job.

Also run after the change, one at a time, both Pythons, all passing: `reel_page_check.py` 343, `reels_check.py` 158, `reel_door_check.py` 47, `reel_fixes_check.py` 41, `reel_footage_check.py` 183, `footage_look_check.py` 88, `pc_reel_page.py` 49, `edit_queue_v26_check.py` 145, `review_fixes_c_check.py` 45, `posting_panel_check.py` 88, `home_base_check.py` 213, `arrange_check.py` 660, `pc_smoke.py` 230 (183 on Apple's 3.9), `words_check.py`, `look_check.py` 75, `design_check.py --only wire` 108 (3.12 only); `tools/check_pc.py` and `tools/check_plugin.py` clean. `kit_cards_check.py` (126 of 127) and `kit_steps_check.py` (98 of 99) fail only on `need_both` / `need_caption`, as before this stage (stage K's).

**Not tried.** Dustin's or Nicole's own hand; the Claude app's pane; a real shoot; **a fresh session following the new instructions** ("make my posts" stopping at the kit page, and the pasted line with a real note read against real photos: whether the assistant can tell "in front of the white backdrop" from a contact sheet is not known); the real clipboard (the test stands in for it); Windows (the first push runs it); a touch screen; a screen reader on the box.

**Theirs to settle (for the note to Nicole, stage E).**
1. **The carousel designer still makes a first design by itself** the first time it is opened for a shoot: one photo on each slide, the first eight photos when nothing was picked. That is a pick of a kind. Left as it is (her v25 says nothing of the carousel designer); say if it should open empty.
2. **The Oct 30 question at the start of a kit is gone** ("tell me about this shoot"), and the "how I write" question moved to the first caption they ask for. Hers wins on posting (Dustin, Nov 10); said so it is known.
3. **Rule 11 in CLAUDE.md** says choosing and ordering photos "is the Assistant's job and stays so". It now reads, in the instructions: the sneak peeks always; for a reel, a carousel or stories only when they ask. CLAUDE.md's wording is stage E's to bring in line, with Dustin's say.
4. **A footage look no longer makes the assistant pick photos** (choice 6). With no pick and nothing dragged in, a reel with footage has clips and no photos until they choose some.
5. **Our lines:** the one the assistant says when it opens a reel page it has not picked for, and "Nothing is picked yet: the reel, the carousel and the stories are each one press away, and you choose what goes in." Both drafts.
6. **The post kit's Reel card** still says "Your assistant hasn't picked the reel photos yet. Click to pick them yourself." (her v20 line; stage K rebuilds the card from her v25 post kit).
7. **Remove a song** is still not built and is hers to answer (the waiting list, item 1).

**For later stages.**
- Stage I (trim, select several): the note box sits between `.choice` and `.tip` in step 2 (`reel_page._order_section`); `R.photoLine()` redraws the line.
- Stage K: `reel_page.photo_note(saved)` is a reel's note as text. The kit's Reel card line is still v20's.
- Stage E: carry the seven items above; CLAUDE.md should say "make my posts" only brings photos in, name `reel_page.py note`, `photo_ask`, `PICK_WORDS`, and that rule 11's last sentence changed.
- `tests/reel_page_check.py` still compares `reel_page.WORDS` with her v19/v23 page; `PICK_WORDS` and `REELS_WORDS` are compared with her v25 page by their own tests. The not-picked line moved out of `WORDS`.

## Stage I, built (Nov 14): trim a clip, and select several photos like Lightroom

Nicole's v25, section 4: "I can't trim it from a specific end." And section 8: "It should work like programs for photography work. If I click on number one and I hold down shift and I click on 7, it should select all of them, so I can just drag a whole batch." Both are on the reel page only; the chat has no part in either.

**What a photographer sees.**
- **Each clip card has "✂ Trim"** after − and +, which still work as quick length buttons. The line over the cards is her v25 one ("...use − and + to make it shorter or longer, Trim to pick exactly where it starts and ends, or Remove it.").
- **Trim opens her panel over the page:** the clip on a loop with its sound; a strip of the video's own stills, about 8 seconds either side of the clip; the part they are keeping outlined in coral, the rest dimmed; a start handle and an end handle; dragging the middle slides the whole clip and keeps its length; ◀ ▶ beside Start and End move an end a quarter second; "▶ Play it again"; and her readout, "Starts 0:31.6 · ends 0:34.0 · 2.4 s".
- **A clip is 1 to 15 seconds and never runs past the ends of its video.** The handles stop there.
- **Done saves. Cancel, the ×, Escape and a click outside the panel close it and change nothing.** After Done the card shows the new length and plays it, as it does after − or +.
- **In the photo order:** a click on a photo selects it (her outline and check mark); Shift-click selects everything between it and the last one clicked; Cmd-click or Ctrl-click adds or drops one; Escape lets them all go. **Dragging any selected photo moves the whole selection** to where it lands, in the order it had: the others fade while it moves and a tag on the one being carried says "3 photos".
- **With two or more selected, a bar:** "N selected. Drag any of them and they all move together." with **Longer, Quicker, Neither, Take them out, Clear**.
- **In All your photos** a plain click still adds a photo or takes it out. Shift-click and Cmd-click select there; then they drag any of them up into the order, or press **Add them to the end** (the bar there: "N selected. Drag any of them up into your order, or" Add them to the end, Clear). They land in the shoot's order; one that was already in the reel moves there and keeps its mark.
- **One action on a selection is one save and one press of Undo.**

**Our way underneath.**
- **Nothing new is saved and no new route.** Done is the clip card's own change, `POST /reel-moment` with `do: "update"`, now with the start AND the end together. It goes through the same guard, lock and whole-record save (the version before kept) as − and +, is marked as a length they set, and is per reel like every clip (stage G).
- **The Assistant checks a trim itself.** A start and an end together must be 1 to 15 seconds from 0 on, both numbers: anything else is refused whole and nothing is written ("A clip is 1 to 15 seconds long.", ours). Hers bends whatever arrives into shape without a word. A trim that reaches past the video's end (the page knows the length to a tenth of a second) is slid back inside it, its length kept.
- **A fault of hers mended on the way:** with − and + (or a new start alone) a clip whose start sat right at the end of its video could be saved ending up to half a second past the video. Now it ends at the end.
- **What is selected is the page's own.** It is never saved, never sent, and gone after a reload. The record's fields are exactly what they were.
- **Our own drag, not hers.** Hers moves photos with a library from the internet (SortableJS); ours is the page's own pointer drag, as before, so a selection is carried by it: the tag sits on the lifted copy (her style rule, word for word, supplies " photos"), the bar that shows where a photo will land shows where the selection will land, and Escape in the middle of a drag puts everything back with the selection kept.
- **Her words are in two tables of their own,** `reel_page.TRIM_WORDS` and `reel_page.SELECT_WORDS`, and her 39 style rules for the panel, the Trim button, a selected photo, the tag and the bars are in `TRIM_CSS` and `SELECT_CSS`, each as she wrote it. The panel's markup is written above the page's scripts (`reel_page.trim_panel`), as her note asks. The rule for several photos going to one place is `ReelModel.many` in the page's model.
- **A PC.** A PC takes no stills from a video yet (the gap `video.py` already names), so the timeline in its Trim panel has no pictures. The panel says so, in a line of ours: "On a PC the timeline has no pictures along it yet. The handles, the arrows and the times work the same." A video that plays on the page plays in the panel. Selecting several needs nothing a PC lacks; Ctrl-click is the PC's Cmd-click.
- **The instructions:** `parts/arrange.md` (what Trim is and what the panel has, so the assistant can point to it; selecting several, key by key; that it has no command for either and can't see a selection) and `parts/on-a-pc.md` (the gap, in the page's own two lines).

**Choices where her spec was silent (plainest behaviour).**
1. **A trim outside 1 to 15 seconds is refused, not bent** (above). Her page can never send one, so nobody sees the difference.
2. **More photos than a reel holds.** Add them to the end, or a drag up, that would take the reel past 40 photos adds none of them, shows the line already under the reel ("A reel holds up to 40 photos. Take one out first.") and keeps them selected so one can be let go. Hers has no limit on the page (her server keeps the first 40 without a word).
3. **A video that will never have a preview** (the copy failed, no room, a PC that can't play it): the panel says "This video can't be played here. You can still trim it with the timeline." (ours). Her one line there says the preview "is still being made", which would never come true. While a preview really is being made, her line shows.
4. **Trim pressed in the first second, before the page has its list of videos:** the panel opens as soon as the list is there. Hers does nothing on that press.
5. **Escape** follows hers exactly, which means one press does two things when both apply: it closes the Trim panel (or the big photo) and also lets go of whatever is selected.
6. **A finger:** a tap on a photo in the order selects it (hers: a click). There is no Shift or Cmd on a phone, so several can't be selected there (hers the same).
7. **Only a press on the photo itself selects** (hers: `.ph`); the thin frame round the Longer and Quicker buttons does nothing.
8. **The assistant's order.** Moving or taking out a selection makes the order theirs ("I'll drag them in myself"), as moving one photo does; Longer, Quicker and Neither on a selection keep whose order it is, as the buttons under one photo do (hers).
9. **The arrows' names for a screen reader** are her words joined: "Start: A quarter second earlier". Hers gives the arrows a tooltip only.
10. **A click outside the panel closes it** (hers does too; it is not in her written list of ways out).

**Hers left out, on purpose.** Nothing a photographer sees. SortableJS (ours never loads anything from the internet). Her `/strip` and `/preview` addresses are our `/reel-strip` and `/reel-video`, which were there already.

**Tests.** `tests/reel_trim_select_check.py` (new): her words both ways against her v25 reel page and her style rules each as she wrote it; a trim by request on the 3-second clip in `tests/fixtures` (saved, refused, slid back inside, another website and another reel refused); and the real page in a hidden Chrome with the real Shift, Cmd and Ctrl keys and real drags: selecting, the two bars, a drag of the whole selection from the order and from All your photos, more than a reel holds, a phone's width; then the trim panel on a 40-second clip the test makes with the Mac's own tools (the loop with sound, the filmstrip, both handles, the middle, the arrows, 1 to 15 seconds, the video's ends, the four ways out, Done), and the panel as a PC has it. 153 checks with the page (43 without), the same on both Pythons. 54 pieces of the stage were each taken out in a scratch copy and a check failed each time (9 by request, 23 of selecting, 22 of the panel). `tests/skill_text_check.py` has a new section for this stage (480 checks). In GitHub's check: by request on Windows, with the page on the Mac's page job. `--only select | trim | pc` runs one part of the page.

Also run after the change, one at a time, both Pythons, all passing: `reel_page_check.py` 343, `reel_fixes_check.py` 41, `reel_door_check.py` 47, `reel_footage_check.py` 183 (its line over the clip cards is now her v25 one), `footage_look_check.py` 88, `reels_check.py` 158, `picks_ask_check.py` 76, `talking_page_check.py` 573, `pc_reel_page.py` 49, `pc_smoke.py` 230 (183 on Apple's 3.9), `look_check.py` 75; `tools/check_pc.py` and `tools/check_plugin.py` clean. Not run: `kit_cards_check.py` and `kit_steps_check.py` (nothing they read changed; their one older failure each is stage K's).

**Not tried.** Dustin's or Nicole's own hand; the Claude app's pane; a real shoot's footage (a phone's 4K HEVC video trims through its small copy: how smoothly the panel's player seeks on one is not known); a clip trimmed on the page and then made into a real CapCut reel (the make reads the same start and end it always did); a real PC (the PC's way was run on this Mac with the stills switched off); a touch screen's drag of a handle (a tap and a mouse were tried; the handles are 18 px wide); a screen reader on the panel (it is marked as a dialog, as hers, and the keyboard is not kept inside it, as hers); a shoot of hundreds of photos with a big selection dragged while the row scrolls.

**Found on the way, not this stage's, not fixed.** With footage on, a wide video's player under "Watch your footage" is 420 px wide (her rule, since v19), so at a phone's width the whole reel page scrolls sideways. The Trim panel sits inside the window all the same.

**Theirs to settle (for the note to Nicole, stage E).**
1. **Our three lines:** "This video can't be played here. You can still trim it with the timeline."; the PC line under the timeline; and "A clip is 1 to 15 seconds long." (which only a faulty page could ever be told).
2. **Past 40 photos:** the whole batch is refused and stays selected (choice 2). Say if it should add as many as fit instead.
3. **Escape doing two things at once** (choice 5), as hers. Say if Escape should only close what is on top.
4. **The wide video's player at a phone's width** (above): hers, and worth a look by whoever next touches step 1's styles.
5. **Remove a song** is still not built and is hers to answer (the waiting list, item 1).

**For later stages.**
- Stage J (songs): nothing here touches the song step.
- Stage K (post kit, posting queue): a trimmed clip is just a moment with a new start and end and `set: true`; nothing new to read.
- Stage E (note for Nicole, CLAUDE.md): carry the five items above. CLAUDE.md should say the reel page has Trim on each clip card and selecting several photos, name `TRIM_WORDS`, `SELECT_WORDS`, `trim_panel` and `ReelModel.many`, and say a trim is checked by the Assistant (1 to 15 seconds, refused outside).
- `reel_page.WORDS["moments_tail"]` is still her v19 line (held to her v19 page by `reel_page_check.py`); the page shows `TRIM_WORDS["moments_tail"]`, her v25 one. A stage that moves the whole comparison to her v25 page can drop the older one.
- New styles go in their own blocks (`SELECT_CSS`, `TRIM_CSS`), never inside `STYLE`.
- On the page: `window.Reel.clips` (a clip's video, the addresses, `change`, `fresh`), `window.Reel.openTrim(m)`, `window.Reel.trim()` (what the panel holds, for tests).

## Stage J, built (Nov 14): songs

Nicole's v25, section 5: "Screen recordings often open with a glitch and a moment of silence." Two of her three song changes are built. **Remove a song is not built, in any form** (no button, no route, nothing hidden from the list): it is still a question for Nicole (the waiting list, item 1).

**What a photographer sees.** Nothing new on the page: no new button and no new words.
- **A short song that opens with a glitch starts after it.** For a song under 40 seconds, Make my reel starts the reel after the last silent gap in the song's first 12 seconds, on the first 1 of a bar after it, on a whole frame. With no gap it starts at the top, as before. A song of 40 seconds or more starts where it picks up, as before. The Plan line in the result box already says where ("starting the song 4 seconds in"; under one second it says "at the top", hers).
- **A recording they replaced gets its sound taken again.** A new recording put in under the same name as an earlier one: the next Make my reel takes its sound as "<name> sound 2.m4a" beside the first (then "sound 3"...). The first sound is never written over. The song list still shows the recording once and none of its sounds. The reel keeps the song picked, since the name is the same.

**Our way underneath.**
- **The silence is measured with nothing installed.** Hers asks ffmpeg (`silencedetect`, -50 dB, 0.3 s, the first 14 seconds) and takes the last silence that ends in the first 12 seconds. Ours measures the same thing in plain Python, `sound.silences` and `sound.lead_in` in `assistant-make-a-reel/scripts/sound.py`: a sample is silent when it is quieter than -50 dB of full scale; 0.3 seconds or more of them in a row is a gap; the gap ends at the first sample that is not silent. It listens to the very samples the beat is found on (`sound.decode`: the Mac's afconvert, a WAV read in plain Python, Windows' own decoder on a PC), so the start and the beats share one clock. Her four numbers are in one place each (`LEAD_NOISE_DB`, `LEAD_GAP`, `LEAD_WITHIN`, `LEAD_LISTEN`). `sound.py --lead-in <song>` prints it.
- **Where it is wired:** `reel_page.short_song_start(song, seconds)`, called by Make my reel's job, which hands `reel.py make` `--song-start <seconds>`. From there it is the timing's own rule, untouched: the first 1 of a bar at or after that moment (her `downbeat_at_or_after`), on a whole frame. `SHORT_SONG_FROM_TOP = 40` is still the one line for "short".
- **How a replaced recording is told from the one before: its size, its time, and a hash of its first megabyte.** Hers goes by the files' times alone (a sound older than its recording is stale). Ours writes down, the moment a sound is taken, which recording it came from, in the kit's hidden folder: `.kit/reel-sounds.json` (the sound's folder and file name, the recording's file name, its size, its time, the hash; never a path), saved whole with the version before kept (`reel-sounds.prev.json`), one writer at a time (`reel-sounds.lock`). At the next make: same size and same time, it is the same recording (nothing is hashed). Same size and the same first megabyte, it is the same recording with its time moved (copied to another drive, say): its new time is noted and nothing is taken again. Anything else is a different recording: that sound is left exactly as it is and the next name is looked at; the first name with nothing under it is made.
- **A sound with no note** (made before today, or the note could not be written) goes by her rule: a sound at least as new as its recording is that recording's, and it is noted then. A note that can't be written never stops a make.
- **Better than hers in one case:** put the first recording back and its own first sound is used again; hers would take a third.
- **Nothing is written over, ever:** the sound is still made under a hidden name and only takes its real name when whole, and a name that is taken is never used. Up to "sound 99" for one recording's name (`SOUND_SPARES`; hers has no end); the list hides any number, as hers (`SOUND_NAME`; before, 2 to 9).
- **A PC:** nothing here is Mac-only. The measure reads a WAV in plain Python and anything else through Windows' own decoder; the note is plain files.
- **The instructions:** `parts/arrange.md` and the reel skill (what the page does with a short song and with a replaced recording; that there is no Remove on a song, the assistant has no command for one and never moves, renames or deletes a song; what to say if they ask), `parts/where-things-live.md` (the new record).

**Choices where her spec was silent (plainest behaviour).**
1. **A silence still going when the listening stops has no end, so it is not a gap.** ffmpeg (newer ones) ends a silence at the end of the file, so on a song under 12 seconds that trails off into silence hers would start the reel at the song's very end and then fall back. Ours starts at the top.
2. **Stereo.** ffmpeg listens to each channel by itself; ours to the two mixed to one. A gap in one ear alone is not a gap here.
3. **Only the page's Make my reel does this,** as hers (her server, not her timing). A reel made from the chat with `reel.py make` and no `--song-start` starts where the song picks up, short or not, as before.
4. **A song that can't be heard for the measure starts at the top** (hers: the top when there is no ffmpeg).
5. **The start is handed over to a hundredth of a second** (hers rounds the same way).
6. **A recording swapped while its sound was being read:** the note is of the recording as it was before the read, so the next make sees a different recording and takes the sound again.
7. **Past "sound 99"** the page says her "I couldn't take the sound out of that recording..." line. Nobody will get there.
8. **A song file of their own that happens to be called "<name> sound 12.m4a" beside a recording called "<name>" is hidden from the list,** as hers (before today only 2 to 9 were).

**Hers left out, on purpose.** Remove a song, whole: the button, "Move to Trash?", `POST /music/remove`, and "the reel goes back to no song picked yet". ffmpeg itself.

**Tests.** `tests/songs_check.py` (new; no server, no browser, no port, no ffmpeg; the same file on a Mac and a PC): what a silence is, sample by sample; `lead_in` on ten sounds made in the test (a glitch then silence then the test beat; no gap; two gaps; a gap ending after 12 seconds; a hum just above and just below -50 dB; a quarter-second pause; a song silent to its end); the same song as an M4A through the Mac's afconvert; when the computer happens to have ffmpeg, ours beside its `silencedetect` on every one (they agree to a hundredth on this Mac; SKIP elsewhere); `short_song_start`; a replaced recording with the taking of the sound stood in for (so the deciding is tried on every computer): "sound 2", the first untouched, the note and its version before, safe to run twice, the same size told apart by the start, a longer file with the same start told apart by size, only the time moved, the first one put back, no note and newer, no note and older, a sound that can't be read, the list, a note that can't be written; then through Make my reel's own job for real: a short song with a 4.3-second glitchy opening starts after it, on a 1 of a bar and a whole frame, her Plan line saying where, and a real recording replaced gets a real "sound 2"; and Remove a song is not on the page and has no route. 73 checks, the same on both Pythons. 25 pieces of the stage were each taken out in a scratch copy and a check failed each time. `tests/skill_text_check.py` has a section for this stage (492 checks). In GitHub's check on Windows and on the Mac.

Also run after the change, one at a time, both Pythons, all passing: `tests/fixtures/check_sound.py` 32, `pc_reel_page.py` 49, `reel_timing_check.py` 96, `reel_hits_check.py` 45, `reel_page_check.py` 343, `reel_fixes_check.py` 41, `reel_footage_check.py` 183, `reels_check.py` 158, `picks_ask_check.py` 76, `reel_trim_select_check.py` 153, `reel_door_check.py` 47, `pc_smoke.py` 230 (183 on Apple's 3.9), `look_check.py` 75; `tools/check_pc.py` and `tools/check_plugin.py` clean. Not run: `kit_cards_check.py` and `kit_steps_check.py` (nothing they read changed; their older failures are stage K's), the talking reel's tests and the designer's (nothing they read changed).

**Not tried.** A real screen recording of a song (every sound here was made by the test; a real recording's "silence" may carry a faint hiss above -50 dB, in which case there is no gap and the reel starts at the top, as hers would); a real make into CapCut with a short glitchy song, listened to; Dustin's or Nicole's own hand; a real PC (Windows' own decoder gives the samples there: untried for this); a stereo song with a gap in one ear; a shoot's kit copied to a new drive (the files' times may all move: sounds with a note are still known by size and start, sounds without one may be taken once more as "sound 2", which costs a small file and nothing else).

**Found on the way, worth knowing.** A song under 40 seconds that has a true silence of 0.3 seconds or more anywhere in its first 12 seconds (a dramatic stop, a count-in of clicks) starts after the last such silence, not at the top. That is her rule exactly, and ours the same; it is how the test beat (clicks with silence between) first read as "starts 11 seconds in".

**Theirs to settle (for the note to Nicole, stage E).**
1. **Remove a song** is still not built and is hers to answer: to the Trash (hers), or only off the list with the file left where it is (Dustin's first thought)?
2. **A real pause early in a short song** moves the start past it (above). Say if only a gap near the very start should count (the first 3 seconds, say).
3. **A chat-made reel** does not get the glitch rule (choice 3). Say if it should.
4. **The words the assistant says when asked to remove a song** are ours ("there's no button for that yet"; the list shows what is in the Music folder), until Nicole answers item 1.

**For later stages.**
- Stage K (post kit, posting queue): nothing here changes a made reel's record. The song picked is still `saved.song`, an id made from the recording's folder and file name, so a replaced recording keeps its pick.
- Stage E (note for Nicole, CLAUDE.md): carry the four items above. CLAUDE.md should name `sound.lead_in`, `reel_page.short_song_start`, `.kit/reel-sounds.json`, and say Remove a song is not built.
- `reel_page_check.py` still gives "Old rec sound.m4a" a time one second OLDER than "Old rec.mov"; by her v25 rule that sound is an earlier recording's, so that test's make now also leaves an "Old rec sound 2.m4a" in its scratch kit. Its checks still hold (the old sound is used by nobody and never written over).

## Stage K, built (Nov 14): the post kit and the posting queue with several reels; captions optional

Nicole's v25, sections 6 and 7: "It should know that it's Katie Austin's Fun Maternity, because I pressed add to my queue."

**What a photographer sees.**
- **Captions are optional.** On the post kit, **Add to my queue** works once the piece is made, caption or not. With no caption the box says "Add it to your posting queue so you can see it in your feed and give it a date. Its caption can come later, or not at all." and a press opens her small box on the page: "You haven't written a caption for your reel yet. That's okay. Do you still want to add it to your posting queue, or write your caption first?" with **Add it to my queue** and **Write my caption** (the words page). It is a box on the page, never a browser pop-up; Escape and the x close it with nothing done. The same for a carousel. The two lines that asked for a caption first ("Make your reel and write its caption", "Write its caption") are gone.
- **With more than one reel, the Reel card shows a preview of each reel by name:** up to 7 photos (then "+N"), then "In CapCut: <that reel's newest project>" or "Not made yet"; a reel with nothing in it says "No photos picked yet." One **Open in CapCut** under them when any is made.
- **Step 3 lists each reel's place,** in her words: "Fun Maternity: down for Sun, Nov 15", "White Backdrop: made, not in your queue yet", "not made yet", "in your posting queue", "posted ✓".
- **Add to my queue asks "Which reel goes in your queue?"** with a button for each reel that is made and not in the queue yet. With one left it does not ask. Then the caption question when there is no caption, then (the very first time) how often they post.
- **In the posting queue each reel is its own post:** its own date, its own grid photo, its own reminder. The lists and the panel's heading say "<shoot> reel · <reel name>".
- **The reel cover picker:** "From your reel, in the order it plays" first, that reel's own photos numbered in play order; then **+ Use a different photo**, which opens "Any other photo from the shoot" (**Hide the other photos** closes it). It is open already when the photo in use is one of those. A carousel's panel is as it was.
- **A shoot with one reel sees one change only:** the caption is optional. Its card, its queue box, its piece in the queue and its panel's photos are what they were (the panel's photos are now in her two rows).

**Our way underneath.**
- **Each reel has its own piece; no id is renamed.** The shoot's first reel keeps the kit's own reel piece, the one every kit always had, with its date and its place in line. Every reel started after it gets that piece's name with the reel's id after it ("...-reel-v2"). The kit's name in the queue is already one no other kit has (`kit_sid`), so two shoots whose names shorten alike never share a reel piece (checked with two such shoots, two reels each). Which reel a piece is, is read from its name (`posting_queue.reel_version`), never from a field a page could send. Pieces also carry `version` and `reel_name` (hers), kept up to date whenever the kit is added: a reel renamed is shown by its new name.
- **A shoot with one reel is in the queue with the same fields as ever** (no `version`, no `reel_name`).
- **No second server and no command run by the page.** Hers runs `posting_queue.py reel-label` and then `ready` from her page server. Ours is one press on the route the kit page already used, `POST /words-queue {kit, piece, reel?}`, in the page server, under the queue's own lock: `posting_queue.add_for_kit(p, kit, reel=<id>)` makes or updates that reel's piece, then it is marked ready. `reel` must look like a reel id and be one of the shoot's reels, and that reel must be made; anything else is refused with nothing written. Another website's page, another host, and now also a press the browser itself marks cross-site, are refused.
- **The kit page asks nothing of a second place for its reels:** the list of reels a press may offer is written into the button by the server (ids and names, as text), and the page is still built whole on every request. After an add only the boxes that changed are swapped, as before.
- **The words in the box are set as text.** A reel's name with a tag in it shows as letters, on the kit page, in the box's buttons, in the posting page's lists and in the panel's heading.
- **Which reel is made, and its newest project:** `reel_page.reels_for_kit` reads the reel page's record ("made" entries carry which reel; one without a mark is the first reel's, hers). A reel made from the chat the older way (only in `kit.json`) counts as the first reel's.
- **The kit's own reel piece follows the first reel** once a shoot has several: its light is the first reel's (hers lights it from the newest reel of any).
- **The cover picker's photos are that reel's own, whichever reel is open on the reel page:** `GET /posting/panel` reads which reel from the piece (`reel_page.order_for_kit_page(..., reel=)`). Hers asks her second server with `&version=vN`.
- **The reel maker's "made" can no longer un-ready another reel's post.** `reel.py make` tells the queue "<shoot> reel is made" without saying which reel. For a shoot with several reels, `posting_queue.py made` now brings each reel's piece up to date from the reel page's record and changes nobody's light downwards.
- **Reminders follow each reel's piece by themselves** (they always went by the piece's id). A post with no caption still gets its reminder; its notes say "No caption yet. Write it on your words page in the post kit." and fill in when a caption is written.
- **The chat:** `posting_queue.py ready "<shoot> reel" --reel "<reel name>"` gives that reel its own piece and marks it ready; a reel that is not made, or a name that fits none, stops with nothing changed and says why. A reel's piece is found by its name too ("beach reel white backdrop"); "<shoot> reel" alone with two in the queue asks which. The chat's name for a piece is hers: "<shoot> reel (<reel name>)". With no caption the assistant asks her question in her words before marking anything ready.
- **Files:** `kit.py` (the page), `words_page.py` (the route, its state), `posting_queue.py` (the pieces, the panel, the page, the commands), `reel_page.py` (`reels_for_kit`, a reel's own order), four parts of the instructions, `tests/kit_reels_queue_check.py` (new), five older tests brought up to v25, the GitHub check.

**Choices where her spec was silent (plainest behaviour).**
1. **A press that names no reel adds the reel being worked on** (hers). A reel id that is not one of the shoot's is refused (hers falls back to the reel being worked on).
2. **A reel that is not made is refused by the Assistant too,** not only hidden by the page (hers has no check on her server).
3. **A reel after the first gets its piece only when it goes in** (Add to my queue, or the chat's `ready --reel`), as hers. So "Still finishing" on the posting page shows the shoot's reel piece, not one row per made reel.
4. **The kit's reel piece is named for the first reel as soon as the shoot has several** and the kit is added (hers names it only when the first reel itself is added).
5. **The words page's own Add to my queue still waits for a caption** (her words page did not change in v25). With several reels it is about the reel being worked on: that reel's "is it made", that reel's place in the queue (hers adds that reel but shows the first reel's place).
6. **The cover picker remembers whether they opened or hid "Any other photo from the shoot"** while the panel stays open (hers works it out again on every redraw, so picking one of the reel's own photos would close it under their hand).
7. **A reel with no photos picked yet** has a plain row of every photo of the shoot, not numbered, with no headings (hers).
8. **The box:** the button that opened it gets the keyboard back when it closes; a long reel name wraps inside its button (ours, two style lines). Tab can still leave the box: it is hers, with no focus trap.
9. **`ready --reel` refuses a reel that is not made;** plain `ready` still marks whatever it is told (as before).
10. **A shoot with one reel that was renamed** (a list of one) is one reel: nothing new is asked and its piece carries no name (hers: more than one).
11. **There is no `reel-label` command** (hers is her own server's plumbing); `ready --reel` does both.
12. The older "More from the shoot" divider is gone from the picker; its one style line is left, unused.

**Hers left out, on purpose.** Her v26 post kit's test-home links (`?home=test`, the plan's rule). Her second server's `/choices` route and its open access (ours never had one). Nothing a photographer sees.

**Tests.** `tests/kit_reels_queue_check.py` (new): her words and style lines against her v25 page and her posting queue changes; captions optional; a shoot with several reels by request (previews, each reel's place, what may be offered, each reel its own piece, no id renamed, a rename followed); two shoots whose names shorten alike; the queue's names and each reel's own cover photos; the chat; reminders on a pretend calendar; every refusal; and in a hidden Chrome the kit page (the box, its two buttons, Escape, the x, "Which reel goes in your queue?", the question skipped with one left, a name with a tag as letters, the very first add with two reels, a phone's width) and the posting page (the names, the two rows, + Use a different photo, open already, a carousel as it was, a phone's width). 51 pieces of the stage were each taken out in a scratch copy and a check failed each time (30 by request, 21 on the real pages). `tests/skill_text_check.py` holds the new instruction lines to the scripts. In GitHub's check: by request on Windows, with the pages on the Mac's page job. Counts are in the build's report.

Older tests brought up to v25, each only where her behaviour changed: `kit_steps_check.py` and `kit_cards_check.py` (the caption is not asked for; their one long-standing failure, the two v24 lines, is gone with those lines), `words_page_check.py` (the route adds a made reel with no caption; the page's own step still waits), `posting_panel_check.py` and `posting_reminders_page_check.py` (the picker's two rows).

**Not tried.** Dustin's or Nicole's own hand; the Claude app's pane; a real shoot with two real reels made in CapCut; the real Calendar (a pretend one only); a fresh session following the new instructions; Windows (the first push runs it); a touch screen; a screen reader on the box; a shoot with ten reels on the card (how long the page takes with many previews).

**Theirs to settle (for the note to Nicole, stage E).**
1. **One caption for all of a shoot's reels.** The words page has one Reel tab, so two reels of one shoot go out with the same caption and hooks unless they change them between posts, and the caption question is about the shoot's reel words, not that reel's. Hers is the same. Say if each reel should have its own words.
2. **Two reels' reminders have the same title** ("Post your <shoot> reel today"), on different days. Say if the reel's name should be in it.
3. **The words page still waits for a caption before its own Add to my queue;** the post kit does not. Say if the words page should follow.
4. **"Still finishing" shows one row for the shoot's reels until a second reel goes in** (choice 3). Say if every made reel should have a row there.
5. **Our lines in the chat** when `ready --reel` stops (a reel not made, a name that fits none), and the line `made` prints for a shoot with several reels.
6. **In CapCut the projects are named for the shoot, not the reel** (stage G's question): the Reel card now shows them side by side, "White Backdrop ... In CapCut: Katie reel 4".
7. **Remove a song** is still not built and is hers to answer (the waiting list, item 1).

**For later stages.**
- Stage L: nothing here lists shoots on the home page. Stage E (CLAUDE.md): say a caption is optional on the post kit; each reel is its own piece ("...-reel-v2", `version`, `reel_name`); `ready --reel`; the cover picker's two rows; `reel_page.reels_for_kit`; and that the long-standing `need_both` / `need_caption` failures of the two kit tests are gone.
- `posting_queue.kit_piece(p, kit, "reel")` is the FIRST reel's piece; pass `version=` for another. `kit_reels(kit)` is [] for a shoot with one reel.
- The panel's photos now sit in `#pick .ps` (one or two `.strip` rows inside it), not in a single `#pick > .strip`.
- `tests/kit_cards_check.py`'s other older failure (the kit page asking Google for Figtree) still shows on some runs; it came with the stories designer.
