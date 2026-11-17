# Nicole's v25, v26 and v27: the build plan (Nov 17, 2026)

Branch `v27` (main is tagged `before-v27`), built in five lanes on worktrees `v27-a` to `v27-e`, merged back into `v27`. Her packs are in `reference-private/nicole-handoff-v25-2026-11-13/`, `...-v26-2026-11-13/` and `...-v27-2026-11-17/` beside the main checkout, plus her notes `reference-private/nicole-notes-v25-2026-11-13/`: data only, read, never run, never copied over ours, never in git. v27 says everything in v20 to v26 still stands except where v27 changes it, so v27 wins where they differ.

Standing rule (Dustin): identical for the photographer (every word on the page hers, same behaviour, built from her screenshots), our way underneath. Where hers and ours differ on words, posting, hooks or the calendar, Nicole's wins. Her faults are fixed, not copied, and listed. Where she says "still for you to decide", the build takes the default written below and the question goes in the note for Nicole.

Dustin, Nov 17 (going to bed, "you have the green light"): build it, ship it, and message Nicole with install steps that keep her current copy safe. Built overnight by Claude in lanes, each lane with a reviewer and a fix round, then a whole-build check.

Short names: `S` = `plugins/the-engine/skills/studio-manager/scripts`, `R` = `plugins/the-engine/skills/assistant-make-a-reel/scripts`, `P` = `plugins/the-engine/skills/studio-manager/parts`.

This plan was written from five planners' maps of her packs onto our code (each planner read the packs in full and grepped main). The full item lists, with her exact lines and our file-by-file changes, are what the lanes build from; this file is the readable form.

## What changed after the first plan (Nov 17, 4:30am)

The five planners above mapped the packs against main, where none of v25 to v27 was. Then Slack showed that **v25 and v26 were already built on branch `v26`** (Nov 14, twelve stages, eleven tests, `docs/handoff-v26-build-2026-11-14.md`), never merged. `v26` is now merged into `v27` (four small conflicts: the update page's routes beside v26's pages). The lanes were re-planned against the merged code; the sections below are the re-plan and supersede the first item lists. Three things the first plan left for Nicole are settled by her v27: Remove this song is built (two taps, the recording to the computer's own Trash through a shared `this_computer.trash()` helper, Lane E; the button in the song drop-down, Lane A). The folder-naming question and the drop box's second copy still wait on Dustin and Nicole; nothing is built on them.

## Lane A: the reel page, several reels, songs, trim, the footage editor, B-roll, the paces, the chat reel maker (v25 §2, 3, 4, 5, 8, 9, 10, 11; v27 §2, 3, 4, 9, 10, 11, 14), re-planned on branch v27 after the v26 merge

**Estimate:** Roughly 8 to 10 days of focused work for what Lane A still has to build: three L items (the footage editor, watch before you make, Save my video), nine M (the paces, the chooser, step 1 and 2 with the numbering, songs with Remove, clip naming, direct this edit, B-roll on the page, the instructions, the whole-build check) and two S (the queue button on stage K's routes, the whole-video clip), each built in the usual stages with two reviewers and a fix round for the L items and a check per fix. About a third of the earlier plan's 10 to 12 days is already on v27 (the hits, several reels, the photographer picks, the song lead-in and replaced recordings, select several, the v25 Trim, the queue's per-reel pieces). Stage 1 (the contracts and the timing) is about a day and gates every lane; Save my video carries the one real unknown (Core Animation from JXA) and is prototyped on a 6 s clip before its day is spent.

### Already on the branch from v26

- A1 (every vibe lands on the song's real hits): timing.audible_hits, timing.onto_hits, timing.W_EMPTY (0.9), Grid.ON, timing.real_hits_line, timing.ON_CAPCUT_MARKS; reel_page.WORDS vibe_mixed_s is her new sentence; proven by tests/reel_hits_check.py (45) and tests/reel_timing_check.py (96; EXPECTED holds her v25 22 lines verbatim). What A1 does NOT cover: v27 re-recorded 15 of those 22 lines (every mixed, calm and build case on song1, song2 and beat60), which is A2's.
- A3 (the chat reel maker gets the same hits and paces): reel.py plan_reel calls timing.song_grid and timing.plan (no pace table of its own; pace.py retired); its dry run prints 'Real hits: N of M cuts land on a hit you can hear.'; tests/reel_timing_check.py EXTRA runs her cases through reel.py make --dry-run. v27 §14's 'give it section 9's paces' is met by the shared engine once A2 lands in timing.py.
- A4 (several reels from one shoot): scripts/reels.py (op new|switch|rename, listed, current, each, data_of, turned, NAME_TAKEN, MOST = 99), reel_page.version_from_page / POST /reel-version, reels_bar + REELS_JS + REELS_WORDS, reel_fresh, found_moments, as_reel, reels_for_kit, made_for ('made' entries carry version), newest_project, cmd_reels (--new/--open/--rename --to), --reel on show/make; footage.note_found writes moments_found and moments --reel; kit.py picks --reel --for-reel through reel_page.set_assistant_pick (later reels' picks in the reel record, the first reel's in kit.json); proven by tests/reels_check.py (158).
- A5 (the photographer decides, the photo note, the copy line with the reel's name): reel_page.PICK_WORDS (her words verbatim), SAVE_FIELDS['photo_ask'] (_text, PHOTO_ASK_MAX 600), photo_note, cmd_note '<kit>' [--reel], the not-picked line under Let my assistant choose, R.photoLine() (', <reel name>' only with several reels, ', and follow my note' only with a note); 'make my posts' stops at the kit (parts/post-kit.md, photos-in.md, arrange.md, the reel skill Step 2, shared/curating.md); proven by tests/picks_ask_check.py (76) and tests/skill_text_check.py.
- A8, two of its three parts (a short song starts after its glitchy opening; a replaced recording's sound taken again): sound.silences / sound.lead_in (LEAD_NOISE_DB -50, LEAD_GAP 0.3, LEAD_WITHIN 12, LEAD_LISTEN 14), reel_page.short_song_start, sound_for with <kit>/.kit/reel-sounds.json (same_recording by size, time and a 1 MB hash; SOUND_SPARES 98; SOUND_NAME hides any number); proven by tests/songs_check.py (73). NOT built: Remove this song, the song drop-down and Listen (songs_check holds that Remove is absent; that check turns round in A8).
- A9 (select several photos like Lightroom): reel_page.SELECT_WORDS, SELECT_CSS, ReelModel.many, the #reelSel and #allSel bars (Longer, Quicker, Neither, Take them out, Clear; Add them to the end), one save and one Undo step per batch, our own pointer drag with the '3 photos' tag; proven by tests/reel_trim_select_check.py --only select (153 with trim).
- v25 §4 Trim (not an item of the earlier plan, superseded by v27's editor): reel_page.TRIM_WORDS, TRIM_CSS, trim_panel, TRIM_JS, change_moments 'update' with start AND end, MOMENT_MIN/MOMENT_MAX 1 to 15 s refused whole outside; proven by tests/reel_trim_select_check.py --only trim. v27 leaves this panel unreachable (the trim lives on the editor's timeline): A11 decides what becomes of it.
- A16's Lane D half (each reel its own piece): posting_queue.reel_version, pieces with version and reel_name, words_page.add_to_queue takes {kit, piece, reel?} (POST /words-queue), words_page.queue_state(kit, piece, slides, version=), POST /words-rhythm, posting_queue.py ready --reel; proven by tests/kit_reels_queue_check.py (140). The reel page's own 'Add this reel to my posting queue' button is still A16's.
- A17 in part: the instructions for several reels, the photo note, Trim and selecting several, the songs' two changes and 'Remove a song isn't built' (parts/arrange.md, the reel skill, curating.md, on-a-pc.md, where-things-live.md); tests/skill_text_check.py (507). The v27 lines (Name my clips, Edit my reel, the chooser, the editor, B-roll, Save my video, the watch step) are nowhere in the parts yet.

### Items still to build

| # | Pack | What | Size |
|---|---|---|---|
| A2 | v27 §9 (and its acceptance/expected.json, which re-records 15 of the 22 lines) | The paces are now clearly different: Calm, Build and A little of everything in timing.py, with her v27 acceptance file | M |
| A6 | v27 §2 (the chooser; 'Each kind is its own page') | Which reel do you want to create? The chooser of four kinds, KIND_WORDS, the steps per kind, the kind kept per reel | M |
| A7 | v27 §2 step 1 and step 2 | Step 1 and step 2 as rebuilt: the videos fold into one drop-down, the ask box moves up with new words, 'Choose your photos', + Add photos with numbers that stay fixed, the order sticks to the top | M |
| A8 | v25 §5 (Remove); v27 §2 step 3 (the drop-down, Listen, Remove this song: settled by the v27 pack, to the Trash) | Songs: the drop-down with Listen and Remove this song (two taps, to the Trash through this_computer.trash()), the chat's words for it | M |
| A10 | v27 §2 'Watch your reel before you make it'; v27 §10 (/reel/preview, /reel/song, /reel/make with variation and song_start) | Watch your reel before you make it: the plan from a dry run played in the browser, Another part of this song, Try another mix, Undo and Redo, Make this one in CapCut | L |
| A11 | v27 §3 (replaces v25 §4's Trim panel, built Nov 14) | The footage editor: player, Footage drop-down, Make a clip with the orange trim that grows, the timeline of stills with Zoom in, Your clips in two columns | L |
| A12 | v27 §3 'The photographer's own clips'; v27 §11 | Naming the photographer's own clips from the chat: footage.py picks and describe, the 'Name my clips for <shoot>' line | M |
| A13 | v27 §2 step 4; v27 §11 | Would you like to direct this edit? The direct note, its copy line, and the assistant arranging clips, photos and style from it | M |
| A14 | v27 §4; v27 §10 (/reel/make: B-roll needs no photos) | B-roll on the page: clips only, each cut on the beat, words on screen dragged into place, carried into CapCut | M |
| A15 | v27 §4 'Save my video'; v27 §10 (/reel/video) | Save my video: the finished B-roll MP4 with the words on it, made with nothing installed | L |
| A16 | v27 §2 'Add it to my posting queue' | Add this reel to my posting queue, from the reel page (the bar under Your reels and the result box), on the queue routes stage K built | S |
| A17 | v27 §11; v27 §2, §3, §4; v25 §10 | The instructions: the new chat lines, the chooser, the editor, B-roll, Save my video and the watch step in the reel skill, parts/arrange.md, the core table, the PC parts, where things live | M |
| A18 | v27 (its 'tested as your build' line), v27 §12 screenshots, v25 §11 | The whole-build check for Lane A: her words compared both ways against v27's page and server, the PC jobs, the notes for Nicole | M |
| A20 | v27 §4 ('long clips work'); stage F's note for stage I (older, never fixed) | A clip whose card is the whole video no longer stops the reel with a misleading line | S |

### Stages

1. **A2, A7, A8, A20.** Stage 1, the contracts and the timing (about half a day each, in this order). First the record and numbering contracts the other lanes key on, written down in CLAUDE.md before any page work: (a) photo numbers append-only, in reel.py cmd_sheet with kit.py sheet handing it the list before (A7's underneath half; Lane C/D rerun arrange_check, design_check, kit_steps_check); (b) the reel record gains saved.kind (bts|photos|broll), saved.direct, saved.onscreen, moments[].named, and 'made' entries may carry video (a saved B-roll file in <kit>/Reels); reels_for_kit and reels.listed carry kind, and a made entry with video counts as made (Lane D reads these; nothing else in the record moves); (c) the new paths named in GET_PATHS (/reel-song) and POST_PATHS (/reel-song-remove, /reel-preview, /reel-video), dispatched by reel_page.handle_get/handle_post as today (posting_queue.py lines 1974 and 2353 hand every reel path there, so nothing changes in posting_queue); (d) this_computer.trash() (A8's helper, shared with any lane that clears to the Trash); (e) for Lane D: look.crumbs(items) -> the path at the top of every post kit page (Home › <shoot> post kit › Reels › B-roll), which the reel page will call once it exists and until then shows its back link. Then A2 (the paces and her v27 acceptance file: every preview and make after this is timed by it) and A20.
2. **A6, A7, A8, A16.** Stage 2, the page's new skeleton: the chooser and the kinds (A6), step 1 and 2 as rebuilt with + Add photos and Show my new photos on the stage-1 numbering (A7's page half), the song drop-down with Listen and Remove this song (A8's page half; GET /reel-song is also the watch step's audio), and the queue button on stage K's routes (A16). Each is one afternoon; the doors (kit card, parts) land on the chooser at the end of it.
3. **A11, A12.** Stage 3, the footage editor (the largest page piece; the trim and Your clips are what B-roll and the watch step show) and clip naming on its cards. Built from screenshots 13 to 16 in parts: the player and the Footage drop-down; the timeline, Zoom in and scrubbing; Start here / End here / Add clip with the three states of the orange trim; Your clips in two columns with YOUR PICK and Not named yet; then footage.py picks and describe. The hidden-Chrome test drives real pointer drags (the talking tests show how).
4. **A10, A13, A14.** Stage 4, watch before you make and B-roll on the page: reel.py's dry run writes pieces; /reel-preview and the 9:16 player with Another part of this song, Try another mix, Undo and Redo; Make this one in CapCut with variation and song_start; the direct note and reel_page.py direct; B-roll as a style with no photos, the words block dragged on the preview, the words into CapCut as a whole-reel hook. A14 needs A10's preview and A11's clips.
5. **A15, A17, A18.** Stage 5, Save my video (prototype AVVideoCompositionCoreAnimationTool from JXA on a 6 s clip under the memory guard before the day is spent; the render as a job), then the instructions finished (A17) and the whole-build check (A18): her words both ways against v27's page, the PC jobs on GitHub's Windows and Mac machines, two reviewers and a fix round per L item, the handoff doc, the note for Nicole (not sent) and the CLAUDE.md section.

### Decisions (the default the build takes)

- **A2:** Calm's odd-count cost (0.45) and its one-beat fallback (cost 3.0) are hers to the number; not tuned by us.
- **A2:** The extra test cases (60 photos on the test beat, the clip cases, the song started 30 s in) are re-recorded from our engine, never hers, once her 22 match, and each is held to the rules (every cut on a beat, nothing left out, the last photo two beats at least).
- **A2:** The legend line 'Longer stays on screen about twice as long' is left as hers although Calm's Longer is 1.5x and Build's is one beat more (on the owners' list since v22).
- **A6:** A reel's kind is remembered per reel (ours) rather than only read from the address (hers).
- **A6:** The 'Recommended for behind-the-scenes reels' tag shows only on bts (as her BUILD.md meant; her CSS showed it everywhere, already on the Tell Nicole list).
- **A6:** The chooser's title and lede are written on the server (hers decides them in JS after load).
- **A7:** Numbers are append-only from now on (hers); an older kit keeps its numbers as they are; a number is never reused for another photo.
- **A7:** 'Show my new photos' reloads after a save (hers), rather than redrawing in place.
- **A7:** The order's sticky top (.reelstick) is hers; on a phone it is not sticky (the order would cover the page).
- **A8:** Built as v27 says (two taps, to the Trash), which settles the v26 waiting-list question 1; Dustin's 'only off the list' is not built.
- **A8:** A PC uses the Recycle Bin through Windows' own call (hers suggests send2trash, which would be an install).
- **A8:** A removed recording takes its sound files with it (hers); its note in reel-sounds.json goes too so a recording put back is taken afresh.
- **A10:** The preview's photo frames come from the existing 1600 px copies (no new sizes).
- **A10:** A dry run is capped at 30 s; past it the page says her 'couldn't work out the cut' line.
- **A10:** Undo/Redo in the watch step also changes the saved song, pace and style (hers); it is the same record, one save per step.
- **A11:** The v25 ✂ Trim panel (built Nov 14: quarter-second nudges, 'Play it again', Done/Cancel) is not reachable from the v27 cards: v27 wins, the trim lives on the editor's timeline, and her page leaves the panel unreachable too. The panel's code stays until Nicole answers (question for her); tests/reel_trim_select_check.py --only trim points at the editor's drags or is retired.
- **A11:** A clip picked by a click shows 'Play this clip' and her trim line under the list (her edSel box), as hers.
- **A11:** The Footage drop-down's picture is the strip's still nearest a third of the way in (no new video run).
- **A11:** One zoom threshold (60 s) for Start here and for clicking a clip (hers: 60 and 90).
- **A12:** describe writes the record directly under the lock (ours), not through the page server (hers).
- **A12:** Labels only (her 'the short name is enough'); 'about' is refused if present rather than stored.
- **A12:** A name reaches the page as text only (a tag in a label shows as letters).
- **A13:** The chat command sets style, clips and order in one save (ours; hers names no command: her assistant edited the record by hand).
- **A13:** A direction that names a moment not on the cards sends the Assistant to the footage look for that moment only.
- **A14:** onscreen is only saved as pos 'custom' with x, y (hers after Nov 17); the hidden selects are not built.
- **A14:** A B-roll reel is a 'made' entry like any other (version, footage 'broll', no picks).
- **A15:** Core Animation draws the words (not PIL): the box styles are one box behind the whole block rather than her per-line boxes; the note for Nicole shows both.
- **A15:** The render runs as a job (bounded, polled), not inside the request (hers blocks the request up to 30 minutes).
- **A15:** A PC gets a named gap and the PC line; no install asked for.
- **A15:** The saved video is never written over: '<short> B-roll 2.mp4' and on.
- **A16:** Adding from the reel page needs no caption (hers, v25 §6; stage K's box is the kit page's, not drawn here).
- **A16:** The rhythm question uses the words page's existing route and chips (one copy).
- **A16:** A second press on a queued reel says her 'already' line and writes nothing.
- **A17:** The core table sends all three new lines to the reel skill, as today's rows do.
- **A17:** The skill's description stays under 1,024 characters (it is 1,016 today): the new lines go in the body, not the description.
- **A20:** The overshoot threshold (about 0.2 s, two to six frames) is ours; Nicole's call on whether a held last frame or a slightly slowed clip is right.

### Her faults we fix rather than copy

- **A2:** Her Calm on a short song said 'Your song is only…' with a wrong reason (she says so); the fallback length fixes it in hers and ours alike, and our STOP line still comes only when even one beat each can't fit.
- **A6:** Switching under 'Your reels' to a reel of another kind keeps the address's kind and hides the wrong steps; ours reopens the reel as its own kind.
- **A6:** Her applyKind() saves footage and style on every load (a save per visit); ours writes nothing on a plain open.
- **A7:** Her prepare() falls back to name order when photos.json is missing any file it lists, renumbering everything; ours never renumbers a photo the list already has.
- **A7:** Her page checks /photos.json every 4 s; ours asks /reel-state, which it already polls, so no second poll.
- **A8:** Her /music/remove runs osascript per file and stops at the first failure with some files already gone; ours checks every path first, then moves them, and says which moved if one fails.
- **A8:** Her remove takes a relative path from the page; ours takes the song's id (never a path on the wire).
- **A8:** Hers only removes 'sound 2' to 'sound 9'; ours removes every number SOUND_NAME hides.
- **A10:** Her preview JSON leaks the song's relative path and each clip's src path; ours sends ids and keys.
- **A10:** Her 'v.src.endsWith(u)' check reloads the clip when the address is encoded differently; ours compares keys.
- **A10:** Her preview runs bts_reel.py with no lock against Make my reel and shares last-plan.json by folder name; ours has its own folder per kit and a lock per kit.
- **A10:** Her short-song rule and the preview's song_start disagree when the preview chose a start; ours sends the watched start to the make every time.
- **A11:** Her /moments/add makes the still with ffmpeg; ours uses the strip or video.stills under the one video turn, as today.
- **A11:** Her ED.added is lost on a reload, so a reload right after Add clip lets the same stretch be added twice; ours clears the trim after a successful add is seen in the record and keeps the stretch drawn dashed from the record's newest 'you' clip.
- **A11:** Her edGo zooms to a 40 s window only for videos over 90 s and over 60 s for Start here; ours uses one threshold.
- **A11:** Her card click (edGo) and the × share one element; a × press on a card whose clip is in the editor clears ED.edit but not a trim in progress; ours clears both.
- **A12:** Her describe silently writes 'about' up to 400 chars though the feature was taken out; ours refuses the field.
- **A12:** Her picks sheet names the file by a hash of the video's base name, so two clips from the same video overwrite each other's close look between runs; ours writes each look in a fresh folder.
- **A13:** Her page saves direct on every keystroke with the whole saved record; ours sends only the changed field (as every other box, after SAVE_AFTER_MS).
- **A14:** Her /reel save keeps onscreen's x, y and size only through the later keys loop (strings cut to 300 chars, numbers stringified); ours checks them as numbers in range.
- **A14:** Her summary() writes the sum twice (photos then B-roll); ours once.
- **A15:** Her render() checks for the output's existence twice but writes '.part.mp4' beside it with no lock, so two presses race; ours takes the kit's job lock and names the part file by the job id.
- **A15:** Her broll_video raises FileExistsError after a full render when the name appeared meanwhile; ours picks the free name under the lock before rendering.
- **A15:** Her ffmpeg run has no memory bound; ours runs under the video turn and the guard the tests use.
- **A16:** Her reelToQueue re-enters itself after the rhythm is set without checking the add didn't already happen; ours asks once and adds once.
- **A16:** Her 'already in your queue' check only looks for status green; a piece queued without a date reads as not queued and can be added twice; ours asks the queue by version.

### Touches other lanes

- Lane D (posting queue, post kit): stage K's per-reel pieces, ready --reel, queue_state(version=) and add_to_queue(reel=) are built and are what the reel page's queue button (A16) drives in-process; no new Lane D route is needed. New for Lane D: a 'made' entry may carry 'video' (a saved B-roll MP4 in <kit>/Reels, no CapCut project) and 'footage': 'broll'; reels_for_kit gains kind and video; the Reels card and the queue should show a saved video as made, and its cover picker has clips and no photos (a plain row of the shoot's photos, as a reel with no pick has today). And look.crumbs(): v27 §7's path at the top of every post kit page (Home › <shoot> post kit › Reels › B-roll) is page chrome across all pages; whichever lane owns look.py/brand.bar builds it once (it is not in look.py today); the reel page shows '← All the reels you can make for this shoot' and the kit link in its bar until then and calls look.crumbs() after.
- Post-kit lane (kit.py): the Reel card becomes the Reels card with her v27 words ('Create as many reels as you like from this shoot: behind the scenes, just photos, talking to camera, or B-roll. Each one is cut on the beat of your song and opens in CapCut, ready for your look.'; REEL_CREATE 'Create my reels', REEL_AGAIN 'Create another reel') opening /reel.html?kit= (the chooser, A6); reel_door() unchanged in shape; the per-reel previews and step 3's per-reel status (stage K) read reels_for_kit and show a B-roll reel's clips count; tests/kit_cards_check.py holds the words.
- Lane C (the carousel and stories designer) and Lane D and the post-kit lane all read the kit's numbered list: A7 makes it append-only in reel.py cmd_sheet (the one writer; kit.py sheet copies it), new photos take the next number, a photo gone keeps its number unused; their '+ Add photos' (v27 §6) and 'Pick my carousel photos' sit on the same list; rerun arrange_check, design_check, design_v26_check, kit_steps_check after stage 1.
- Lane B (talking reel): the chooser's 'Talking to camera' card links to /talking.html?kit= (talk_card today); 'Your talking reels' is built (stage G, same reels.py); v27 §5 (fix a word, Open CapCut, + Add more photos in the pop-up) and the crumbs on the talking page are Lane B's; the reel page's /reel-capcut already opens CapCut.
- this_computer.py: trash(path) (A8) is a shared helper: Finder's Trash on a Mac, the Recycle Bin on a PC, refuses paths outside the kit, every path checked before any moves; other lanes may reuse it (v26's drop-box question, if Dustin and Nicole say so). New PC lines (Save my video, the editor without stills, clip naming) are drafts for Nicole.
- R/video.py: a new 'render' command (A15) under the same video turn lock every video job uses; tests keep running one video test at a time under the guard. R/reel.py: --dry-run --status gains 'pieces' (A10) and --hook-whole (A14); the talking reel's builder and capcut_even's eight kept projects stay byte for byte. R/timing.py: A2 changes every Calm, Build and mixed reel's holds (Nicole's real reels change again, by her choice) and A20 the whole-video clip rule; the talking engine does not use timing.py.
- v27 §10's GET /home-data 'me' and 'posting' fields: only her home-page idea (v27 §13, not to build) uses them; nothing in Lane A or the home base needs them. v27 §8 (Posted on the post itself) and §6 (the designer's tools) are other lanes'. v27 §14's test-only Home links: not built, as before.
- The v26 waiting list after this plan: item 1 (Remove a song) is settled by v27 and built in A8; items 2 (folder naming) and 3 (the drop box's second copy) still wait on Dustin and Nicole, nothing built; v27 says nothing new on them.
- tests: tests/reel_page_check.py moves its word comparison to her v27 page (A18) with TRIM_WORDS in HERS_NOT_OURS; tests/reel_trim_select_check.py --only trim is retired or pointed at the editor's timeline (A11); tests/songs_check.py's 'Remove is absent' check turns round (A8); every stage sets STUDIO_NO_WINDOWS_FOR_TESTS, TEST_OPEN and TEST_CAPCUT so no window, Finder Trash or CapCut is touched by a test.

### Open questions for Nicole

- Remove this song is built as your v27 says: two taps, the recording and its sound files go to the Trash (Put Back brings them back). On a PC it goes to the Recycle Bin through Windows' own call (nothing installed; you suggested send2trash, which would be an install). OK?
- Your v25 ✂ Trim panel (the quarter-second ◀ ▶ nudges, 'Play it again', Done/Cancel) was built on Nov 14; in your v27 page it is unreachable and the trim lives on the editor's timeline. Built: the editor only, the panel not opened from the cards. Do you want the panel back anywhere?
- Your 22 acceptance lines (v27) are matched exactly; our extra timing cases (60 photos on the test beat, the clip cases, the song started 30 s in) are re-recorded from our engine, since we never run yours. OK? And every Calm, Build and A little of everything reel you have made changes its holds (your choice): say when you have heard one.
- The legend still says 'Longer stays on screen about twice as long' while Calm's Longer is 6 beats to 4 (1.5x) and Build's is one beat more. Reword, or leave?
- A reel saved before v27 (no kind) opens as Behind the scenes when footage was on, Just photos when off, and the chooser when nothing was chosen; a reel's kind is remembered per reel, so switching under Your reels reopens each as its kind. OK?
- Photo numbers now stay fixed when photos are added (new ones at the end, a removed photo's number is never reused), for the reel, the carousel picker, the designer and the stories alike. OK that a shoot's list can have gaps?
- Undo and Redo in the watch step also change the song, pace and style chosen in steps 3 and 5 (they are the same choices). As yours; say if you'd rather Undo there only covered the mix and the part of the song.
- The browser's audio clock and the plan can drift by a frame or two over a 30 s reel; the cut times shown are the plan's, so the CapCut project is right even if the preview wobbles. OK to say nothing on the page about it?
- The orange trim zooms in on about 40 s for a video over 60 s (Start here) and over 90 s (clicking a clip) in your page; built with one threshold, 60 s. Fine?
- A clip that is the whole of a short video (2.40 s on a 2.43 s beat) used to stop the reel; built: under about 0.2 s short, the clip's last frame is held to the beat. Held last frame, or a slightly slowed clip?
- Clip names from the chat: labels only, up to 80 letters, 'about' refused (you took the description out). The assistant also names unnamed picks at the end of 'Look through my footage'. OK?
- Save my video on a PC: not possible with nothing installed. Built as a named gap with a line saying Make this one in CapCut works there and the words go with it. OK, or should a PC be asked to install something?
- The words in the saved video are drawn by the Mac's own text engine, not Pillow: the same font, size and wrap width as the page, but 'White text on black' is one box behind the whole block rather than a box per line. Acceptable, or must it match your screenshot 18 per line?
- The B-roll words' dragged position carries into the saved video; CapCut's text layer sits at CapCut's default spot (your tip says change it there). Say so on the page, or leave the tip as it is?
- Adding a reel to the queue from the reel page needs no caption (your v25); the kit page still asks its caption question. Should the reel page ask it too?
- Multi-select has no touch-screen way (no shift or Cmd on a finger); not built, as yours. Fine for now?
- Still open from v26 and untouched by v27: the folder-naming question at setup, and the drop box's second copy. Nothing is built on either until you and Dustin say.

## Lane B: the carousel and stories designer (v26 §5 and v27 §6 as they stand on branch v27 after the v26 merge; v27 §10's /open and /save?one=1&i=N; v27 §11's "Pick my carousel photos" line)

**Estimate:** About 5 days of focused work with tests, down from the earlier 5 to 6: v26's stories work (B1, B2, B5, B6, the stories half of B3/B4, four of B7's templates, the stories' × and the queue route) is merged and reviewed. Left: four L items (Crop, several photos at once, Save just this slide, + Add photos without the numbering, which is Lane A's), seven M (the carousel fill command, insert/remove slides, Where should it go, drag slides, See a photo big, the v27 check file; B20 grows throughout), and six S (the carousel ask box, the three collages, Show the whole photo, Open folder, the crumbs call, the instructions). Two items wait on other lanes (B16 on A-numbers, B21 on D-crumbs) and are placed last so the lane is usable without them.

### Already on the branch from v26

- B1 "Show Instagram's guides" and the lede's last sentence: S/design_page.py STORY_BANDS = "Show Instagram's guides" (line 295) and STORY_LEDE ends "Untick Show Instagram's guides to hide them."; proved by tests/design_v26_check.py HERS["bands"] / HERS["lede_end"] (browser part, ~line 775-777) and the older stories/v22 checks brought up to date in stage C.
- B2 the stage sticks to the top, both kinds: S/design_page.py DESIGN_CSS line 151 .stage{position:sticky;top:0;z-index:20} with no body.story qualifier; proved on the stories page with 40 photos by tests/design_v26_check.py ~line 1009 (view["pos"] == "sticky", top within 1 px while the tray is scrolled) and on the carousel by tests/design_layout_check.py lines 204-236 (the stage's top unchanged across four scroll states).
- B3, the STORIES half only: the button, the box, the `ask` field and the copy line. S/design_page.py ASK_BUTTON/ASK_HEAD/ASK_SUB/ASK_EXAMPLE/ASK_PLACE/ASK_THEN/ASK_LINE/ASK_COPY (lines 298-306; the button is rendered only `if story`, line 391); S/design_js_ask.py (DESIGN_ASK_JS: the box, the line with ", and follow my note", Copy/Copied, POST /design-asked); S/design.py clean_ask (418), ASK_MAX = 600 (201), save_from_page keeps `ask` on the SET'S RECORD, not the layout, for kind == STORIES only (1280-1301), load_design (1016-1021), _design_for_page sends it as text (2194), _post_asked (2505); proved by tests/design_v26_check.py browser part (the box's words, open/close, the line changing with a note, the note stored after the autosave) and tests/pc_design.py part 15. The carousel half is NOT built (see B3c).
- B4, the STORIES half only: the chat side. S/design.py cmd_story_note (2877) prints THEIR NOTE and the frames in filling order; story_fill / cmd_story_fill (2926, 3011) with --design and --replace, under the design lock, refuses a number not on the sheet, a photo already in, more photos than frames, SAME: when run twice, keeps the version before, bumps rev; P/arrange.md "Making stories" lines 141-157 (the two commands, the four steps, rule 11); SKILL.md row 46 ("Pick my story photos for <shoot>" and "..., and follow my note"); proved by tests/design_v26_check.py server part (the two commands, every refusal) and tests/skill_text_check.py. The carousel line and command are NOT built (see B4c).
- B5 Redo: S/design_js_core.py `fut` (157), D.redo (202), D.canRedo (215), cleared on every fresh change (177) and on design load (381); S/design_page.py the #redo button after Undo (374), in both kinds; Cmd/Ctrl+Shift+Z and Cmd/Ctrl+Y in S/design_js_edit.py keydown; proved by tests/design_v26_check.py (words["redo"] == "Redo" and the browser part's undo-then-redo).
- B6 sets of stories: S/design.py KINDS[STORIES]["one_design"] = False (648), next_name for STORIES gives "<shoot> stories", then "<shoot> stories 2" (1136-1160), new_design/blank_story take a kind (1173-1227), DESIGNS_MAX applies; S/design_js_designs.py DW.myDesigns 'My story sets', designsHead '<shoot> story sets', newSet '+ New set of stories' (109-115, 351-356, 428-433), Duplicate hidden in stories; the page opens the set its address names; proved by tests/design_v26_check.py (a second set made, named, listed, opened, saved as "Lake day stories 2 - 01.jpg", the kit shows the newest saved set) and tests/pc_design.py part 15.
- B7, FOUR of the seven templates and the queue route: S/design.py _story_templates (793-840) has sg-delivered (4 stories, #f6f1e7), sg-queue (1, fill "queue", list id), sg-full (10), sg-seamless (6, one frame 3*W wide) with her placeholder words, before the seven grids (_story_starters 869); queue_names() (842) reads edit_queue.load/waiting; GET /design-queue in design.handle_get (2436, cross-site refused) and S/posting_queue.py do_GET line 1962; S/design_js_plan.py fillQueue (159) writes "1   Garcia wedding" rows, 12 then "+ n more", "Nothing in your editing queue right now"; S/design_js_designs.py fetches /design-queue on Add (690) and says her "I can't reach your editing queue right now." (design.QUEUE_CANT); proved by tests/design_v26_check.py (her four templates number for number against her page, the queue of 3 / 14 / 0, the 503 line). The three story collages (Playful mosaic, Mood board, Overlapping collage) are NOT built for stories (see B7c); the carousel's cs-mosaic/cs-mood/cs-overlap exist in _starters (758-764).
- B8, the stories part only: S/design_js_model.py removeStory(st, k) (323; takes the story and everything whose middle is on it, shifts the rest by W); S/design_js_edit.py label() puts the × (class labx) on every story label when STORY (255-262) and the sel-story group's "Remove this story" (310-311, off at one story with a line); proved by tests/design_stories_check.py (the osascript part, lines 105-114) and design_v26_check ("Removed story 6. Undo brings it back."). The carousel's × and +, insertSlide, Add a slide before/after and Remove this slide are NOT built (see B8).
- B19 the [hidden] rule itself: S/arrange_page.py CSS line 60 `[hidden]{display:none!important}` is global and wins over any display:flex class on the designer (hers needed `.where[hidden]`); the static+computed-display CHECK is not written yet and folds into B20.
- Not an item of the earlier plan but worth knowing: the "Size" word hidden between 1024 and 1179 px in both designers (so Redo fits) is in, and GET /design-queue is wired in posting_queue.do_GET, so B7's route work is done.

### Items still to build

| # | Pack | What | Size |
|---|---|---|---|
| B3c | v27 §6, v27 §11 (her page: askKindWords, askLineText; screenshot 09) | Let my assistant choose the photos on CAROUSELS too: the button, the box worded for slides, the `ask` field on a carousel design, and the copy line "Pick my carousel photos for <shoot>[, and follow my note]" | S |
| B4c | v27 §6, v27 §11 | The assistant fills a carousel's empty frames from the chat: `design.py note` / `design.py fill` for carousels (story-note / story-fill kept as the stories' spelling), the arrange.md section and the SKILL.md row for "Pick my carousel photos for <shoot>, and follow my note" | M |
| B7c | v27 §6 (her page lines 585-587; screenshot 12) | The three story collages in Add stories: Playful mosaic, Mood board, Overlapping collage, scaled from the carousel collages, after Seamless swipe and before the grids | S |
| B8 | v27 §6 (her page insertSlide 955-968, removeStory 1121-1131; screenshot 09) | Adding and removing slides in BOTH kinds: + and × on every label, Add a slide before / Add a slide after / Remove this slide in the selected-thing bar (stories say story); the stories' × and Remove this story stay as they are | M |
| B9 | v27 §6 (her page tplWhere 370, addStories 1645-1665), the [hidden] CSS lesson | Where should it go? in Add slides / Add stories (Before slide N / After slide N / At the end), the changed adding lines, the fall-back when a photo stretches across the spot, and the over-limit refusal when a template is added | M |
| B10 | v27 §6 (her page slideGroups/moveGroup 969-1020) | Drag slides by the grip on their label; a coral line shows where it lands; slides sharing a stretched photo move together; Escape cancels | M |
| B12 | v27 §6 (her page wholeBtn 306; screenshot 09) | Show the whole photo, first in the selected-photo bar and later inside the Crop window | S |
| B11 | v27 §6 (her page openCrop..cropDone 1133-1212; screenshot 10) | Crop: the whole photo with a box; corners keep the frame's shape; untick for eight handles and the frame takes the box's shape; Done maps to zoom and offset past the 300% slider | L |
| B13 | v27 §6 (her page multibar 343, evenOut 1031-1065; screenshot 11) | Several photos at once: Shift/Cmd/Ctrl-click, drag any to move them all, the bar inside the stage with Even them out, Same size, Line up tops, Remove them, Done | L |
| B14 | v27 §6 (her page openView..buildTray 1750-1790) | See a photo big: double-click a tray photo or press its ⤢; ‹ › and the arrow keys browse; Use this photo / Put it in the selected frame; a single click waits 230 ms | M |
| B15 | v27 §6 (her page openSavedBtn 1066-1074, saveOne's Open folder 1113) | Saved, then Open folder: the saved line gets an Open folder button, and a permanent Open folder button beside Save slides / Save stories (no longer hidden until a save); her missing-folder line | S |
| B17 | v27 §6, v27 §10 (her server /save?one=1 1600-1618; her page saveOne 1104-1124) | Save just this slide / Save just slide N: one slide saved beside the design's newest set as "<base> - slide 0N updated.jpg" (stories "<base> - 0N updated.jpg"), never over anything, through staging and the commit | L |
| B16 | v27 §6, v27 §10 (her server prepare() 1023-1058; her page Add photos 1075-1102) | + Add photos beside "Let my assistant choose": opens the Photos folder; new photos join the tray at the end with numbers that stay fixed, without a reload (the numbering itself is Lane A's) | L |
| B21 | v27 §7 (crumbs.js; her carousel-designer.html bar; screenshots 09-12) | The path at the top of the designer: the bar calls look.crumbs() with Home › <shoot> post kit › Carousel | Stories once Lane D lands it; the old Back pill hidden | S |
| B18 | v27 §6, v27 §10, v27 §11 | Instructions: parts/arrange.md's designer sections brought to v27 (the new buttons the page does by itself, Crop, several at once, Save just this slide, Open folder, + Add photos with fixed numbers, the carousel ask line), SKILL.md's carousel row, where-things-live.md | S |
| B20 | v27 §10, v27 §12 (screenshots 09 to 12) | Screens and words check: tests/design_v27_check.py (page under osascript, server by request, browser in the hidden Chrome) as a part of design_check.py (--only v27), with her words both ways against her v27 page, the [hidden] check (B19), the carousel sticky-stage check, and the PC jobs | M |

### Stages

1. **B3c, B4c, B7c, B15, B20.** Contracts first, and the small server-side pieces that touch shared files. Lane B states what it NEEDS: from Lane A, kit.py sheet / reel.py sheet keeping every existing n and appending new photos with the next numbers, written whole (her prepare() rule), plus a way for a caller to learn 'added k, first n, last m, kept' (a printed line or a return value); from Lane D, look.crumbs(trail) and look.kit_trail(kit) with the Back-pill-hidden rule. What Lane B GIVES: POST /design-photos (B16) as the designer's poll target, GET /design-queue (already there), the carousel chat line for SKILL.md, and the open_kit_folder missing-folder words (B15) in posting_queue.py, which Lane A also edits for 'Reels'. B20's file is started here. About half a day.
2. **B8, B9, B10.** Slides as things: insert/remove in both kinds and the sel-slides group (B9's where-row and B10's grip build on insertSlide and the seam rule). Model maths under osascript first, buttons after. About a day.
3. **B12, B11.** The photo inside its frame: Show the whole photo (one action), then Crop (ZOOM to 25, the model maths, the modal). About a day.
4. **B13, B14.** Several photos at once (its own model operations and the bar inside the sticky stage), then See a photo big (changes the tray tile and click timing; one tile function that B16 reuses). About a day.
5. **B17, B16, B21, B18, B20.** The saves and the folder: Save just this slide through the commit path (after B8's group and B15's button), + Add photos and the /design-photos poll (needs A-numbers; usable without it as the reload path), the crumbs call once D-crumbs is in, the instructions, and the v27 check finished and put in check-pc.yml. About a day and a half.

### Decisions (the default the build takes)

- **B3c:** The note is kept after the fill (hers keeps it); nothing clears it.
- **B3c:** The box's maxlength stays 600 (hers); the server's cap matches.
- **B4c:** With no empty frame the assistant does not add slides by itself; it says what to press (open for Nicole). Note that the carousel's first design is made with one photo a slide (ensure_design / seed_state), so on a fresh kit "Pick my carousel photos" finds no empty frame unless they emptied some or added slides: see the question for Nicole.
- **B4c:** The assistant fills empty frames only unless --replace, which the instructions allow only when they asked to choose again (the stories' rule, Nov 14 review).
- **B7c:** A collage lands on the set's own background, like every template (the v26 question 1 to Nicole still stands).
- **B8:** A photo whose middle sits on the removed slide goes with it even if it stretches into the next slide (hers).
- **B8:** At one slide × is not shown and Remove this slide is off with our line (hers does nothing and says nothing).
- **B9:** The row is not shown on a one-slide design (hers).
- **B9:** A template that would pass 20/40 is refused whole with her line (hers); nothing is trimmed.
- **B10:** The drop line and the dimmed piece are her coral; our centred lines stay blue (Nov 11's question still open).
- **B11:** ZOOM max 25 (her effective limit through MIN .04); Pillow previews and PC 4320 copies are unaffected (zoom is a page-side crop, kept in the layout).
- **B13:** The bar sits inside the sticky stage above the labels (her screenshot 11).
- **B13:** No snapping during a group drag (hers).
- **B13:** The selected-thing bar shows the last clicked block's buttons while several are selected; those act on one block (hers).
- **B14:** The 230 ms single-click delay is hers and is kept.
- **B15:** The permanent button stays in our bottom bar labelled "Open folder"; hers sits in the top row (open for Nicole).
- **B17:** No ARRANGED line to the chat for a single slide (hers tells nobody); the page says it (open for Nicole).
- **B17:** Fonts fallen back ask the same Save anyway / Go back question as a set.
- **B16:** Only additions are taken up without a reload; a removal or a rename still blocks until Reload (safer, today's rule).
- **B16:** The chat's contact sheets are re-made with the new numbering at the same moment (kit.py sheet does both).

### Her faults we fix rather than copy

- **B3c:** Her box saves on every keystroke (save() each input) and keeps `ask` inside the layout; ours goes through the autosave pause and keeps it beside the layout, as the stories do.
- **B4c:** Hers has no command: her Claude edited the design file by hand. Ours is one command under the lock, safe to run twice.
- **B8:** Her "Remove this slide" at one slide does nothing silently; ours keeps its line.
- **B8:** Her 20 px stretch test is repeated in three places; ours is the model's seam rule in one.
- **B9:** Her stale "slide 8" bug: impossible here (rebuilt on open, global hidden rule).
- **B10:** Her drag has no Escape; ours cancels like every other drag.
- **B12:** A very tall photo in a very wide short frame could leave hers under 60 px; ours clamps.
- **B11:** Her Done can leave a frame under our 60 px or off the strip when unlocked; ours clamps.
- **B11:** Her modal reads P[b.n].src then the full copy; ours the same through D.photoUrl, never a path.
- **B13:** Her group drag can go off the strip; ours clamps like a single move.
- **B13:** Her Same size with a text box as the reference sets photos to the text's width; ours takes the last clicked photo and skips a text reference.
- **B15:** Hers runs `open` (Mac only); ours goes through finder.open_folder on both computers.
- **B17:** Her i is unchecked and the file is written straight into the folder from the request thread with no staging, journal or hash; ours uses the commit path.
- **B17:** Her set number K is guessed from the folder's prefixes and can pick the wrong set after a hand rename; ours names from the design's own last finished set.
- **B16:** Her /photos.json poll lists the folder and runs sips on every call from the request thread; ours throttles and runs the numbering as a command.
- **B16:** Her list is written in place; ours whole or not at all (kit.py sheet's tmp + replace).
- **B21:** Her crumbs.js is a browser script with an absolute 8790 address and hard-coded colours; the path is built on the server (Lane D).

### Touches other lanes

- Remove this song (v25 §5, settled by v27 §2's 'Remove this song, two taps, to the Trash') is the REEL PAGE's: Lane A builds it through a new this_computer.trash(path) (Finder's Trash on a Mac, the Recycle Bin on a PC, never a delete), a route and a test; tests/songs_check.py lines 524-526 currently assert it is ABSENT and must flip in Lane A. Lane B has no use of trash(); nothing in the designer deletes or moves a file.
- Lane A owns photo numbers that stay fixed (S/kit.py sheet, R/reel.py cmd_sheet, which numbers by name today, lines 190-210). Lane B's B16 and Lane C's '+ Add more photos' both depend on it; the contract Lane B needs is in stage 1's note. design._sync (design.py 1092) already re-maps designs by file name, so designs are safe either way; only the page's no-reload path needs kept numbers.
- S/posting_queue.py: Lane B adds POST /design-photos to do_POST's design list (line 2340) and nothing to do_GET (GET /design-queue is already at 1962); Lane A adds 'Reels' to open_kit_folder's tuple (2202) and Lane B changes only that function's missing-folder words for Carousel/Stories/Photos. Edit that function last, or one lane does both.
- Lane D owns look.py (look.crumbs, look.kit_trail) and the hide-the-Back-pill rule; Lane B's B21 is one call in design_page.py's bar and waits for it. The designer's trail: Home › <shoot> post kit › Carousel | Stories.
- parts/arrange.md and SKILL.md's table: Lane B edits the designer sections and adds one row (the carousel line); Lane A edits the reel sections of the same files ('Edit my reel ... follow my direction', 'Name my clips'). Merge by section. parts/where-things-live.md: one line each for `ask` on a carousel and the single-slide journal entry.
- S/edit_queue.py: read only by design.queue_names (edit_queue.load / waiting) for the My editing queue story; Lane B takes waiting() as it stands.
- .github/workflows/check-pc.yml: design_v27_check.py joins the mac-page job's lists (lines 189 and 193); tests/pc_design.py's new cases run in the Windows job as part 15 does.
- The carousel picker's shift/cmd-click (v25 §8, Lane A, built in stage I on the reel page) and B13's selection should feel the same under the photographer's hands: Shift adds or takes out, Cmd/Ctrl adds or drops one, Escape clears; Lane B follows reel_page.SELECT_WORDS's keys.
- v27 §14's chat reel maker paces and the talking reel's 'working on it' are Lanes A and C; v27 §13's friendlier home page and v26 §6's test-only Home links are not built by anyone.
- The folder-naming question and the drop box's second copy still wait on Dustin and Nicole; v27 says nothing new; no lane builds them.

### Open questions for Nicole

- "Pick my carousel photos": the carousel designer still makes its first design by itself with one photo on every slide, so on a fresh shoot there is no empty frame to fill. Should a carousel open empty now (so the assistant's pick is the first layout), or should the pasted line replace the photos that are there?
- With no empty frame in the design, should the assistant add slides itself, or say so and name what to press (built: it says what to press)?
- Save just this slide: is the page's own line enough (hers), or should the chat be told as it is for a whole set?
- Open folder: her permanent button sits in the top row beside Save just slide N; ours lives in the bottom bar with Save slides. Which?
- + Add photos: only added photos join without a reload; a photo removed or renamed still asks for a Reload. Fine? And the assistant's contact sheets are re-made at the same moment (built: yes).
- Sets of stories: a shoot's first set keeps its old name "<shoot> stories" and new ones count from 2 (no saved file name changes); hers names every set from 1. Fine?
- A template (the collages included) lands on the set's own background, not its cream or grey; should a template added to an EMPTY set bring its background?
- The drop line, the dimmed piece and the several-photos bar are her coral; the centred lines and the selection stay blue. The Nov 11 "coral or plain" question still stands.
- The queue story's card reads "1 story · 0 photos" where hers reads "0 photo", and the rows use the shoot names exactly as typed in the editing queue (client names on a public story). Fine?

## Lane C: the talking reel (v27 §5, §10 talking routes, §14 "working on it", her talking_core.py one-line change; v25 §2's "Your talking reels" bar is now built on v27; plus the one v25 piece the merge left out that v27 settles, Remove this song). Paths: S/ = plugins/the-engine/skills/studio-manager/scripts, R/ = plugins/the-engine/skills/assistant-make-a-reel/scripts, P/ = plugins/the-engine/skills/studio-manager/parts, all under /Users/dustindamron/Projects/hf-tools (branch v27).

**Estimate:** About two and a half days of focused work, C6 (several talking reels, 7 h in the earlier estimate) being already built on v27: C10 M (2 h), C1 M (3 h, the talking.clean change included), C2 L (6 h), C3 S (1 h), C4 M (3 h), C7 S (0.5 h), C8 S (0.5 h), C5 M (3 h, plus waiting on Lane A's numbering refresh), C9 S (1 h), then the whole-build rerun of the talking tests under the guard on both Pythons (about 2 h). Plus C11 M (3 h) only if Remove this song is built in this lane rather than as Lane A's A8.

### Already on the branch from v26

- C6 (several talking reels: new, switch, rename; refused while a video is being turned into a script): S/reels.py (op, new, switch, rename, info, listed, current, find; ID v<n>, NAME_MAX 40, MOST 99), S/talking_rec.py TALK_KEEP / TALK_LIVE / talk_fresh / version_op (refuses with STILL_SCRIPT while job_running, and with STILL_MAKING, ours, while a make is at work; rename never refused) / reel_info / which_reel / reel_line, state_for_page returns versions and current, S/talking_page.py version_from_page and "/talking-version" in POST_PATHS and ROUTES (cross-site refused), S/posting_queue.py do_POST line 2358 lists /talking-version, the bar itself is reel_page.reels_bar(w) + reel_page.REELS_JS used by page_html with talking_page.REELS_WORDS ("Your talking reels", "+ Start a new talking reel", "Which talking reel you're working on", Talking reel 1), S/talking_js_core.py T.reelsBar (flushes the save chain before new/switch, then location.reload), tests/reels_check.py (158 checks: both bars in a hidden Chrome, her words both ways against her v25 page and server, a one-reel shoot byte for byte against commit b5af248). The v25->v27 diff of her talking-reel.html touches nothing in the reels block, so reels_check staying on v25 is right.
- C9, the several-reels half: P/talking-reel.md line 41 ("Several talking reels from one shoot": the bar, --reel on status/show/cut/photos/place, refused while transcribing and while making, never removed, CapCut names stay the shoot's) and tests/skill_text_check.py's stage G section; cmd_status names the reel through reel_line when there are several.
- C9's "no new pasted line" decision: her v27 page still writes the three lines without a reel name (talking_page.WORDS cut_line / place_line / cut_place_line unchanged; skill_text_check check_talking holds them to the core's table).
- C7's half that was already in main: W["working"] ("Working on it…") exists and is the step line's fallback (talking_js_step1.py line 66, talking_page.WORDS status_working); the "still being copied" row line (OUR_WORDS["coming"]) covers a file landing in the Talking folder.
- The pieces of v27 §5 that need no code: "A single click still plays from that word" (talking_js_script.py jumpToWord), the words shown as text nodes (renderScript), the highlight bar placed by placeBar, T.pickerOpen() guarding the timeline's and preview's key handlers (talking_js_timeline.py 799, talking_js_preview.py 339), quiet() waiting while a picker or the menu is open (talking_js_core.py 306), the pop-up's grid rebuilt when the photo set differs (talking_js_pick.py pickFresh on T.emit('photos')), the state's mark moving with arrange.sheet_stamp (talking_rec.folder_mark), GET /open?kit=&sub=Photos (posting_queue.open_kit_folder, cross-site refused, PC-ready).
- Her v27 talking_core.py differs from v24 by the one captions line (diffed: `if text:` before out.append); talking.py's RULES / PHOTO_RULES unchanged, so tests/talking_rec_check.py's rule compare on v24 stays right.

### Items still to build

| # | Pack | What | Size |
|---|---|---|---|
| C10 | v27 (talking-reel.html, server.py's talking part, talking_core.py), v25 (reels bar, already compared by reels_check) | Her words compared both ways against v27 instead of v24 | M |
| C1 | v27 §5, §10 (/talking/save takes fixes), her talking_core.py v27 (captions skip a word typed away) | Fix a word: the record, the save check and the engine | M |
| C2 | v27 §5 (Fix a word on the page), screenshots 20 and 21, her page lines 170-179 (CSS), 299, 345-346, 504-526, 730-731, 750-791 | Fix a word: the page (double-click, Fix the words, the small box, Enter and Esc, the underline, Undo/Redo) | L |
| C3 | v27 §5 (the captions, the preview and CapCut use the fixed words) | The fixed words reach the preview's captions and the CapCut project | S |
| C4 | v27 §5 (Open CapCut) and §10 (POST /capcut/open), screenshot 22, her page lines 381, 1229-1245, her server lines 1360-1364 | Open CapCut in the bottom bar, and "It's in CapCut" naming the project | M |
| C5 | v27 §5 (+ Add more photos in the photo pop-up's footer), §2 step 2 (photos keep their numbers; new ones go at the end), her page lines 191, 246, 351, 834-837, 1315-1344 | + Add more photos in the photo pop-up's footer, with the grid rebuilding as photos arrive | M |
| C7 | v27 §14 ("The talking reel could say 'working on it' right after a video is added") | "Working on it" at once after Edit my video is pressed (a sensible default) | S |
| C8 | v27 §5 (the path at the top) and §7 (crumbs.js), her page line 252 | Lane D's crumbs on the talking page, the back pill hidden | S |
| C9 | v27 §5, §10 | parts/talking-reel.md and the assistant's words for fixes and Open CapCut | S |
| C11 | v25 §5 (Remove a song: to the Trash through Finder, Put Back brings it back, a PC's Recycle Bin, the picked song goes back to none) as settled by v27 §2 step 3 (Remove this song, two taps, to the Trash) and her v27 reel-maker.html lines 568, 1217-1228 and 1848-1865, her server.py /music/remove (lines 1532-1545) | Remove this song (the one v25 piece the merge left out that v27 still asks for): this_computer.trash(), a route and a test | M |

### Stages

1. **C10, C1.** First, half a day. Opens with the contracts other lanes need, written into the code's docstrings and the test names before anything else: Lane A (A-numbers): the numbered list keeps every existing n and appends new photos with the next numbers (reel.py cmd_sheet line 190 renumbers from the sorted folder today; kit.py sheet line 357 copies it whole), plus one callable refresh (proposed arrange.refresh_sheet(kit) -> bool changed, cheap when nothing landed) that talking_rec.state_for_page calls only with photos=1 in the query; the talking record is its own file (talking.json), so Lane A's reel record changes (versions, made[].version, B-roll's video) touch nothing here, and only reels.py is shared (no change). Lane D (D-crumbs): look.crumbs(trail) and look.kit_trail(kit) as named in the v27 plan, the nav living inside each page's .bar, the CSS in look.py. this_computer.trash(path) -> (ok, why) honouring no_windows(), shared with Lane A's A8 and Lane E's drop box. posting_queue.do_POST: Lane C adds '/talking-capcut' to the talking tuple (line 2358) and, if C11 is this lane's, '/reel-song-remove' to the reel tuple (line 2350). Then C10 (the words test on v27) and C1 (the record, the save check, the engine): everything on fixes stands on _join laying fixes over the words and on talking.clean keeping an empty fixed word.
2. **C2, C3.** A day. The page's Fix a word on top of C1, then the proof that the fixed words reach the preview and CapCut (tests only). Run talking_page_check --only words at the end of each so her new lines move from 'hers, not ours' to found.
3. **C4, C7, C8.** Half a day. Open CapCut through posting_queue.open_capcut as the reel page does (TEST_CAPCUT, no real CapCut from a test), the one-line 'working on it', and the crumbs call once Lane D's look.crumbs exists (build C8 against a stub that draws the nav if D is not there yet; the test allows the nav inside .bar either way).
4. **C5, C11.** Half a day each. C5's button and words can go in now; its grid-rebuild check runs only once Lane A's A-numbers refresh exists (skip with a named reason until then; never ship the look-while-open without it, or a photo added mid-list would renumber every stretch onto the wrong photos). C11 (Remove this song) is built here only if the orchestrator leaves it to Lane C rather than Lane A's A8; whichever lane builds this_computer.trash() first, the other imports it.
5. **C9.** An hour for the part and the assistant's lines once the behaviour is final; then the whole-build rerun of the talking tests under the guard (talking_page_check whole, rec, engine, capcut, multi, menus, snap, pc_talking, reels_check, songs_check, skill_text, capcut_even, both Pythons: about 2 hours).

### Decisions (the default the build takes)

- **C10:** v25's talking-reel.html need not be read by this test: v27's page carries the reels bar unchanged, and reels_check already holds it to v25.
- **C10:** Her two /capcut/open lines are read from server.py's handler so the words test sees them; the regexp that finds them today only reads ValueError(...) and "step"/"problem" strings, so the handler's "problem": "..." literal is covered by the existing pattern (check).
- **C1:** Where fixes live: in the record, not the words file (hers rewrites the words). Default: record, as an edit field.
- **C1:** A fix equal to the heard word: dropped on save (hers does the same on the page and the server).
- **C1:** A value longer than 80 characters: the whole save refused (hers truncates silently). Default: refuse, as every other field.
- **C1:** A fix is not 'their own work' for cut --replace / place --replace (fixes never touch cuts or stretches); status mentions the count only.
- **C1:** `show` does not mark a fixed word for the assistant: the fixed word is simply the word (rule 3); status says how many were fixed.
- **C1:** A fix on a word that is cut: allowed and kept (hers allows it; the word shows crossed out and fixed).
- **C2:** Where the box sits when the word is near the top of the window: hers puts it at top 8 px; ours the same (her placement, both axes).
- **C2:** A double-click while words are highlighted: the browser selects the word anyway; openFix clears the selection, as hers.
- **C2:** Escape in the box: closes the box only (hers also reaches the timeline's Escape). Default: stop there.
- **C2:** A fix pressed while a save is on its way: queued through T.save's chain as every save.
- **C2:** Touch screens have no hover, so the heard word has no way to show there: left as hers; noted for Nicole.
- **C2:** The box is re-placed on scroll like the bar (hers stays where it was).
- **C3:** The caption's time stays the heard word's start and end (hers): a fix never moves timing.
- **C4:** Which words when CapCut was already open: her sentence (newest project at the top) is kept; the maker's line before it (MADE_OPEN) already says to quit and reopen if it isn't there.
- **C4:** The bar's button after a page reload: shown when the open reel's record has any made entry (rec.made from state), as hers (REC.made.length).
- **C4:** Nothing made yet: the route refuses with her 'I couldn't open CapCut.' (hers would open CapCut anyway; the button is hidden then, so only a crafted request reaches it).
- **C4:** With several talking reels, the project named is the open reel's newest make, not the shoot's.
- **C5:** Polling: not a second timer; the page's existing look with the folder mark, asking for the refresh only while the pop-up is open.
- **C5:** The '+ Add photos' at the top of her v25/v26 page was never on ours (ours came from v24), so there is nothing to take out.
- **C5:** A photo dragged in while a stretch's pop-up is open: joins the grid at the end with its new number; nothing already picked moves (pickFresh keeps what is picked by number).
- **C5:** Her 'Could not open the folder. Is the photo drive plugged in?' is said only when the folder truly isn't there (posting_queue's own words otherwise).
- **C7:** Which moment she meant: the press of Edit my video (default) or the file landing in the folder (already covered by the 'coming' line). Open question.
- **C8:** The back link stays in the markup, hidden as hers.
- **C8:** 'Reels' links to the reel page's address with no kind, which Lane A turns into the chooser.
- **C9:** No new pasted line for 'which talking reel' (hers has none): the open reel is the one; the assistant asks only when they name another (built in stage G).
- **C11:** The Trash, as hers and v27 (not 'only off the list'); the file is never deleted and never renamed into a hidden place.
- **C11:** A PC: Windows' own Recycle Bin call, nothing installed (hers suggests send2trash); the removed line says Recycle Bin / File Explorer / Restore (ours).
- **C11:** A song picked by ANOTHER reel of the shoot is not cleared there (nothing of one reel is written into another); that reel's Make my reel already says song_gone ('That song isn't there anymore...').
- **C11:** A recording's sounds go with it (hers: 'sound.m4a' and 'sound 2..9'); ours takes every number sound_for could have made (SOUND_SPARES).

### Her faults we fix rather than copy

- **C1:** Her /talking/save accepts any number of keys, str()s a non-string value (a list becomes "['a']"), and silently ignores keys beyond the word count or non-digit keys: ours refuses the whole save on any bad entry.
- **C1:** Her fixes are lost without a word when the video is turned into words again (the words list is replaced): ours keeps them in "replaced" and starts the edit afresh, as every edit field.
- **C1:** Her fixes are not kept per video (her record has no per-video edits): ours moves them with "earlier" when they change video and brings them back.
- **C2:** Her global keydown does not stop Space/Delete/Backspace typed in the fix box from reaching the video and the timeline: ours guards them while the box is open (through T.pickerOpen).
- **C2:** Her Escape in the box does not stop propagation: with several clips picked, one Escape closes the box AND lets go of the clips. Ours closes the box only.
- **C2:** Her fix box is placed once and never moved on scroll (position:fixed): ours re-places it as the bar is, or closes it when the words scroll away.
- **C2:** Her mousedown-anywhere-closes handler fires for a press on the highlight bar too; ours ignores presses inside #fixBox and the bar.
- **C2:** Her renderScript writes the title attribute by string with esc(): ours sets it with setAttribute, so a heard word with a quote can never break the markup.
- **C4:** Her /capcut/open never adds a reel waiting for CapCut's list and has no PC path: ours goes through capcut.open_capcut as the reel page does.
- **C4:** Her 'Your newest project is at the top of the list' is said even when CapCut was already open and the project is not listed yet: kept as her words, but the maker's own line above it tells the truth about that case.
- **C5:** Her page polls /photos.json every 4 s for the life of the page, pop-up open or not: ours looks only while the pop-up is open, through the look it already makes.
- **C5:** Her 'Could not open the folder' is said for any failure; ours only when the folder isn't there.
- **C11:** Her route takes a path from the page and only checks it is one of the shoot's listed songs: ours takes an id and finds the file itself.
- **C11:** Hers clears the picked song only on the page (song = null; save()): ours clears it in the record as part of the same locked step, so a second window and the chat agree.
- **C11:** Hers has no PC path (osascript only) and suggests an install: ours uses Windows' own call.

### Touches other lanes

- S/posting_queue.py do_POST: the talking tuple at line 2358 ('/talking-open', '/talking-start', '/talking-save', '/talking-make', '/talking-version') gains '/talking-capcut' (Lane C); the reel tuple at line 2350 gains Lane A's routes and, for Remove this song, '/reel-song-remove' (whichever lane builds C11/A8). One lane edits each tuple; no change to do_GET for this lane (GET /open?kit=&sub=Photos exists and is reused by C5).
- Lane A (A-numbers, v27 §2 step 2): 'Photos keep their numbers when more are added: new ones go at the end' must be built in reel.py cmd_sheet (line 190, today enumerate over the folder's sorted names) and kit.py sheet (line 357), keeping every existing n and appending new files with the next numbers, with one callable refresh that writes sheet.json whole (the atomic replace kit.py sheet already does). Lane C calls it from talking_rec.state_for_page only while the photo pop-up is open (photos=1 in the query); the page learns of the change through the existing mark (folder_mark includes arrange.sheet_stamp) and T.emit('photos') -> pickFresh. C5 must not ship its look-while-open before this lands.
- Lane A's reel record changes (versions, made[].version, B-roll video, direct/onscreen) do not touch talking.json; the one shared module is S/reels.py, which Lane C does not change. Lane A's chooser makes /reel.html?kit= the 'Which reel' page: the talking page's crumbs 'Reels' step links there (C8), and the chooser's 'Talking to camera' card links to /talking.html?kit= (talking_page.page_address).
- Remove this song (C11) is on the reel page: the v27 plan's Lane A item A8 carries the song drop-down with Listen and Remove this song and names this_computer.trash() among A's touches. It is listed here because the merge left it out and the orchestrator says it is settled; one lane builds it (proposal: Lane A, since A8 rebuilds the song section; Lane C only if A8 is not in this round). this_computer.trash(path) is the shared helper (Lane E's drop-box clearing may reuse it); it must honour no_windows() so no test ever moves a real file.
- Lane D (D-crumbs, v27 §7): the talking page's bar is S/talking_page.py page_html line 827 (<div class='bar'> with a#back and brand.bar()); her trail for this page is [[post kit, kit page], ['Reels', reel chooser], ['Talking to camera', none]]; Lane C calls look.crumbs(look.kit_trail(kit) + [('Reels', '/reel.html?kit='), ('Talking to camera', None)]) and hides #back (display:none, kept). Lane D owns look.py and the CSS; nobody else edits look.BASE. tests/talking_page_script.py line 661 counts one .bar; a nav inside it is fine.
- R/capcut.py open_capcut / posting_queue.open_capcut are shared with the reel page and the kit page: Lane C only calls them with the talking page's words (ok_words, button) as reel_page.open_capcut_for_page (line 2845) does, reusing reel_page.TEST_CAPCUT; no change to capcut.py. If Lane A changes posting_queue.open_capcut's signature for v27's reel-page Open CapCut, keep ok_words and button, and the missing-CapCut words must stay readable (capcut.launch.missing) so the talking page can say her 'CapCut doesn't seem to be on this Mac' line.
- The 'Your reels' / 'Your talking reels' bar is one module already (reel_page.reels_bar, REELS_JS, the CSS in reel_page) used by both pages: Lane A's reel-page rebuild must keep reels_bar's signature (w, label, which, new) and the ReelsBar({words, flush, post, reload, renamed}) contract talking_js_core.py line 323 relies on.
- P/talking-reel.md is Lane C's; tests/skill_text_check.py check_talking also reads the core's SKILL.md table: no new row (no new pasted line), so the core's table is untouched by this lane. Lane A's new rows (Name my clips, Edit my reel and follow my direction) go in the same table: merge by row.
- Her talking_core.py v27 differs from v24 by the one captions line; talking.py's RULES / PHOTO_RULES are unchanged, so tests/talking_rec_check.py's rule compare stays on v24 (identical text). tests/reels_check.py stays on her v25 pages (the reels block is unchanged in v27, diffed).
- The design preview, kit cards and the posting queue are untouched by this lane; a talking reel still is not a queue piece and not on the Reel card (owners' question 9 stands; v25/v27 do not change it; Lane D's per-reel queue pieces are photo reels only).

### Open questions for Nicole

- A word typed away (fewer words typed than highlighted) still plays in the video and only loses its caption; the toast says 'To take a word out, use Cut.' Is that what you want, or should the box refuse a count that doesn't match?
- The hover line 'You fixed this. It was heard as …' never shows on a touch screen (no hover). Leave it, or add a tap?
- When a video is turned into a script again (Edit my video again, or the file exported again), yours loses the fixes without a word; ours keeps them with the earlier cuts in 'replaced' and starts the edit afresh (the word numbers change). OK, or should fixes be carried over by matching words?
- 'Working on it': do you mean the moment after pressing Edit my video (built: the status line says Working on it… at once), or the moment a file lands in the Talking folder (today the row names it as 'still being copied' until it is whole)?
- Open CapCut on a PC: your line names 'this Mac' ('CapCut doesn't seem to be on this Mac. It's free from capcut.com.'); on a PC ours says 'this PC' and 'the Start menu'. OK?
- With several talking reels, Open CapCut names the open reel's newest project in the box (not the shoot's newest). OK?
- May the assistant mention a word that looks misheard ('did you say Aurora?') and tell them how to fix it, or never (rule 3: the assistant never touches a caption word)? Built: never fixes, tells them how when asked.
- A fix is not counted as 'their own work' for the assistant's cut --replace / place --replace questions (fixes don't touch cuts or stretches). OK?
- Remove this song on a PC: your note suggests send2trash (an install); ours uses Windows' own Recycle Bin call, and the line reads 'open the Recycle Bin in File Explorer and choose Restore' (ours). OK?
- Remove this song when another reel of the same shoot had picked it: ours leaves that reel's pick alone (it says 'That song isn't there anymore' when they make it); yours never had two reels pick one song in the same breath. Clear it everywhere instead?
- + Add more photos: ours looks for new photos only while the pop-up is open (yours looks every 4 seconds for the life of the page). A photo dropped in while the pop-up is closed shows the next time it opens. OK?

## Lane D: the post kit, the words page, the posting queue and its panel, the path at the top (crumbs), her plugin-changes diffs (re-planned against branch v27, which holds the v26 merge)

**Estimate:** About a day and a half of focused work: D6-crumbs S (2 h), D5-reels-words S (1 h), D6-crumbs-pages M (3 h), D3-posted M (4 h), D8-parts M (3 h), D7-sticky-check S (a hand check, 20 min); then the lane's full test run on both Pythons (1 h). Nothing in the lane waits on Lane A now (reels_for_kit and order_for_kit_page are built); the only cross-lane timing is that look.crumbs() goes first so the other lanes' bars can call it.

### Already on the branch from v26

- D1 (one spot per reel in the queue): built by stage K (ed5aaf1), our way. posting_queue.reel_version(x) reads which reel from the piece's id (REEL_LATER = -reel-(vN)); kit_piece(p, kit_dir, role, n=None, version=None) and kit_reel_pieces(); add_for_kit(p, kit_dir, reel=None) makes or updates '<base>-reel-vN' with version and reel_name (line ~603, kept up to date on every add, a rename followed); find() matches the words of reel_name (line 444) and several_reels_kit() stops with both names; piece_name() says '(name)' on the CLI and the page says ' · name' (mk() line 1440, openPick line 1507, textContent); state().pub() carries reel_name (line 1693); the chat is `posting_queue.py ready "<shoot> reel" --reel "<name>"` (line 2592, reel_piece_for) instead of her reel-label, by choice 11 of stage K; `posting_queue.py made` brings every reel's piece up to date (line 2686) and never un-readies another reel; reminders go by the piece's id, words_piece() by kind == 'reel'. Proof: tests/kit_reels_queue_check.py (140 checks: two reels each its own piece, no id renamed, two shoots whose names shorten alike, the chat, reminders on a pretend calendar), tests/posting_panel_check.py (88), tests/posting_reminders_page_check.py (116). NOT taken from the earlier plan: the reel name in the reminder's title (reminders.title() is still 'Post your <shoot> reel today' for both reels: an owners' question, CLAUDE.md item 13), and the `reel-label` command (hers; `ready --reel` does both).
- D2 (the reel cover picker in play order): built by stage K. posting_queue.panel_choices() reads the reel from the piece (line 983: reel_page.order_for_kit_page(kit, rows, rec, reel=reel_version(x))); the page JS has PW.from_reel 'From your reel, in the order it plays', use_other '+ Use a different photo', hide_other 'Hide the other photos', any_other 'Any other photo from the shoot', photo_n 'Photo {n} in your reel' (lines 1481-1484); drawPick() draws the numbered strip, the .more button with aria-expanded 'true'/'false' and the hidden .others block with mkel/textContent (lines 1543-1548); MORE remembers whether they opened the others while the panel stays open (stage K choice 6, her fault mended). Proof: tests/posting_panel_check.py (the two rows, + Use a different photo, open already, a carousel as it was) and tests/kit_reels_queue_check.py (each reel's own cover photos).
- D4 (captions optional on the kit, her on-page question): built by stage K. kit.KIT_WORDS has ready_nocap, nocap_title, nocap_text, nocap_add, nocap_write, close (lines 1731-1736); need_both and need_caption are gone; queue_box(piece, made, has_caption, q) locks only on 'made' and carries data-nocap (line 2234); ASK_BOX is an on-page role=dialog aria-modal box (line 2134) built with textContent (askBox, askNoCaption lines 1978-2005, Escape and the x close it, focus returns to the button); words_page.add_to_queue() gates on 'made' only (line 532) and the words page's own Post it step still waits for a caption (hers). Proof: tests/kit_reels_queue_check.py (the box, its two buttons, Escape, the x, a reel with no caption added), tests/kit_steps_check.py (100), tests/words_page_check.py (195: the route adds a made reel with no caption; the page's step still waits); parts/posting-queue.md line 9 and parts/words.md line 7 say it.
- D5 (a preview per reel, step 3 per reel, Which reel goes in your queue): built by stage K with her v25 words; only the v27 wording of the Reels card is missing (item D5-reels-words below). kit.KIT_WORDS reel_empty, which_title, which_text, r_posted, r_down, r_in, r_made, r_not (lines 1739-1746), REELS_STYLE (.onereel, .qreels, .nocap), reels_queue_box(reel_list, has_caption, queues) (line 2241, data-add='reel' data-multi='1', the list of reels written into the button by the server as text), card_facts() + reel_page.reels_for_kit(), askWhichReel through the same box, add(piece, reel) posting {kit, piece, reel} to /words-queue, words_page.queue_state(kit, piece, slides, version=) and state() carrying the open reel's queue. Proof: tests/kit_reels_queue_check.py lines 187 and 327 (two .onereel previews by name, 7 photos then +N, each reel's place, the question skipped with one left, the very first add with two reels, a name with a tag as letters).
- D7 (the carousel picker's sticky carousel): already in main before v26: arrange_page.py line 79 .panel{position:sticky;top:0;z-index:20...}; tests/arrange_check.py proves position:sticky. Only the hand check on a 13-inch screen remains (item D7-sticky-check).
- D9 (the word checks against her newest page), half: the kit tests' her_page() glob already picks the newest pack (nicole-handoff-v2[0-9]-*, reverse), need_both/need_caption are gone from KIT_WORDS, and tests/kit_steps_check.py and tests/kit_cards_check.py were green against v26's page on Nov 14 (100 and 127). Since the v27 pack landed they are red again on the Reels card's words only (checked read-only with a script: of KIT_WORDS, reel_sub is the one line absent from v27's post-kit.html that was present in v25's; and kit_cards_check line 116 insists her page has 'Make a new version' and 'Create my reel', which v27 replaced). That red is fixed by D5-reels-words, not by a separate test item. tests/words_page_check.py her_page() still globs nicole-handoff-v20-* (v27's words.html differs from v20's only in the bar line, which D6-crumbs-pages changes).
- D8 (the parts), in part: parts/posting-queue.md already has `ready --reel`, the caption question in the chat ('say it has no caption yet, then do it if they say so' is there in substance: 'don't mark it ready silently; ask her question'), the reel previews and 'Which reel goes in your queue?' (line 21), a reel found by its name (line 23); parts/words.md says a caption is optional (line 7); parts/where-things-live.md has version, reel_name and the -reel-v2 ids (line 17); parts/post-kit.md step 6 has the box and the several-reels card. What is still missing is in item D8-parts.

### Items still to build

| # | Pack | What | Size |
|---|---|---|---|
| D3-posted | v27 §8 "Posted, on the post itself", plugin-changes/posting_queue-since-v26.diff, screenshots 23 to 25 | Posting queue: the Not posted / Posted switch on the post's panel, the posted piece in the grid as a feed post with no date, and unposted (page, chat and state) | M |
| D5-reels-words | v27 §2 (the post kit's Reels card), her v27 pages/post-kit.html lines 310-311, screenshot 01 | Post kit: the Reels card's v27 words (Reels, her new line, Create my reels / Create another reel), and the tests that are red on them now | S |
| D6-crumbs | v27 §7 (crumbs.js), pages/crumbs.js, screenshots 01 and 07 | look.crumbs() and look.kit_trail(): the path at the top, built on the server in look.py (the contract every lane's page calls) | S |
| D6-crumbs-pages | v27 §7, her v27 pages/post-kit.html line 91 and pages/words.html line 85, screenshots 01 and 07 | The path at the top of the kit page (Home › <shoot> post kit) and the words page (Home › <shoot> post kit › Captions); the old Back pills hidden; the words test moved to her newest page | M |
| D7-sticky-check | v27 §7 (the carousel picker keeps the carousel at the top), her carousel-picker.html line 30 | Carousel picker: a hand check that the sticky panel never grows past a 13-inch window | S |
| D8-parts | v27 §2, §7, §8, §14; v25 §6, §7, §10 | The instructions: post-kit.md, posting-queue.md, words.md, where-things-live.md, arrange.md and the SKILL.md row for the Posted switch, unposted, the Reels card's words and the path at the top | M |

### Stages

1. **D6-crumbs, D5-reels-words.** The contracts and the red tests, first (about three hours). look.crumbs(trail) and look.kit_trail(kit_name) in look.py with look_check, so Lanes A, B and C can call them in their bars from the start (reel page: kit_trail + [('Reels','/reel.html?kit=<kq>'), ('Behind the scenes'|'Just photos'|'B-roll', None)], the chooser kit_trail + [('Reels', None)]; talking page kit_trail + [('Reels','/reel.html?kit=<kq>'), ('Talking to camera', None)]; designer kit_trail + [('Carousel'|'Stories', None)]). Then the Reels card's v27 words, which turns tests/kit_cards_check.py and tests/kit_steps_check.py green against her newest page so every later run in the lane is meaningful.
2. **D6-crumbs-pages.** The path on the kit page and the words page, the old pills hidden, the words test moved to her newest page (about three hours, a hidden Chrome under guard.py). Independent of Lane A; needs only stage 1's look.py.
3. **D3-posted.** The Posted switch, the posted tile in the grid and unposted, all in posting_queue.py (about four hours): state(), the /posting action, the CLI, the page JS and CSS, the new tests/posting_posted_check.py and one case in posting_reminders_page_check.py. Independent of versions and of every other lane; Nicole hit it on real shoots ('there's no refreshed feed there at all').
4. **D8-parts, D7-sticky-check.** The parts, SKILL.md and skill_text_check as the pieces above land (about three hours), and the picker's hand check. Then the lane's full run: kit_cards_check, kit_steps_check, kit_reels_queue_check, reel_door_check, words_page_check, posting_panel_check, posting_posted_check, posting_reminders_page_check, reminders_check, look_check, skill_text_check, pc_smoke, both tool checks; both Pythons.

### Decisions (the default the build takes)

- **D3-posted:** Reminder on unposted: remind_on is left as it was, so a reminder that was on comes back on the post's new date (hers only pops posted_at; ours is the same, stated; asked below)
- **D3-posted:** A posted piece's panel offers no photo, words or reminder (hers): the switch and Done only (asked below)
- **D3-posted:** Keyboard: posted tiles get tabIndex and Enter/Space like upcoming ones (ours; hers are mouse-only)
- **D3-posted:** A single post (kind 'single') posted gets ▢ as its .rk icon, since our grid has singles and hers does not
- **D3-posted:** The CLI line is ours: '<piece>: back in your queue, ready to post, down for <day>.'
- **D5-reels-words:** 'Create another reel' shows once any reel of the shoot is made (hers)
- **D5-reels-words:** The Reels card still opens /reel.html?kit= with no kind; the 'Which reel do you want to create?' chooser behind it is Lane A's (v27 §2)
- **D6-crumbs:** The shoot's short name in the crumb is the kit's folder name without its date (her short()), the same rule the kit title uses (asked below)
- **D6-crumbs:** The test-home localStorage switch and home-test.html branch of crumbs.js are never built (v26 §6, v27 §14)
- **D6-crumbs:** Nobody but Lane D edits look.BASE; other lanes only call crumbs()/kit_trail()
- **D6-crumbs-pages:** On the saved copy (body:not(.live)) the crumb links are drawn as plain text, like the hidden homelink
- **D6-crumbs-pages:** The posting queue page keeps 'Back to home' (hers; it is not a post kit page)
- **D6-crumbs-pages:** The kit page's crumb is 'Hannah post kit' with no link (where you are); her words page links it to the kit
- **D7-sticky-check:** Left as is unless the hand check shows the panel taller than her 48vh
- **D8-parts:** The chat's answer to 'what's a post kit?' reuses her Make posts paragraph (v27 §8) word for word
- **D8-parts:** No chat command draws the posted tile; 'I posted it' and 'that one didn't go out' are the two commands

### Her faults we fix rather than copy

- **D3-posted:** Her JS filters S.posted by read_at a second time on the page (dropped: the server decides)
- **D3-posted:** Her posted tile has no keyboard access and no focus ring
- **D3-posted:** Her openPick builds the switch with innerHTML strings (ours with mkel/textContent); her aria-checked is a JS boolean stringified (set 'true'/'false' explicitly)
- **D3-posted:** Her state() sorts by posted_at with no guard for a piece whose posted_at is not a string
- **D6-crumbs:** Hard-coded http://127.0.0.1:8790/home (breaks the moment the port differs; ours is a relative path)
- **D6-crumbs:** Hard-coded hover colour #D4643F and the font name 'DM Sans' (ours: the look's variables)
- **D6-crumbs:** Built in the browser from the URL's ?shoot=, so a page with no shoot shows a bare 'Post kit' crumb with a dead link (ours is built from the kit the server already resolved)
- **D6-crumbs-pages:** Her v27 post-kit.html keeps the v26 test-home scripts on homeBack and the .qlink/queueLink hrefs (lines 109, 203, 258-259): test-only, not built

### Touches other lanes

- Lane A (reel page, S/reel_page.py and S/reels.py): the contract Lane D builds against is already there from stage K and needs no change: reel_page.reels_for_kit(kit, rows, rec_kit) -> [{id, name, made, project, order}] and reel_page.order_for_kit_page(kit, rows, rec_kit, reel=<id>) (lines 1082 and 1141), read by kit.card_facts() and posting_queue.panel_choices(). Lane A's photo-numbers-stay-fixed change (v27 §2: new photos go at the end of the sheet) must keep sheet.json's existing numbers: every queue cover ('Photos/<file>', found by name through arrange.sheet_rows) and every kit strip reads by number and by file name, so a renumbering would move every reel's cover and preview; Lane D changes nothing for it but adds nothing either until Lane A says the rule.
- Lane A (reel page): v27 §2's 'Add this reel to my posting queue' button (not in reel_page.py yet: no toQueue, no /words-queue call) posts to Lane D's existing POST /words-queue {kit, piece:'reel', reel:<id>} on the same server (words_page.add_to_queue, line 513: the reel must be one of the shoot's, made, else 409/400; refused when Sec-Fetch-Site is cross-site), reads the open reel's queue through GET /words-state?kit=&piece=reel (state() line 383 carries queue.status and queue.date for the reel open on the page: 'says so if it's already queued (with its date)'), and asks the rhythm through POST /words-rhythm as the kit page does. No new route; Lane D adds one case in words_page_check that a press whose Referer is /reel.html is accepted, and asks Lane A to say the queue's words in the kit's own (KIT_WORDS down_for, in_queue, how_often).
- Lane A (reel page, songs): v27 §2's 'Remove this song (two taps, to the Trash)' is settled to be built, through a shared helper this_computer.trash(path) -> the Trash on a Mac (Finder's, via the Finder/osascript route finder.py already uses, never rm), the Recycle Bin on a PC (the shell's recycle through PowerShell/VB, never Remove-Item), refusing anything outside the shoot's own Music folder, with a route (POST /reel-song-remove, same-page guard, the song named by file name only) and a test (tests/songs_check.py, with STUDIO_NO_WINDOWS_FOR_TESTS making the helper answer without moving anything, and one real move into a scratch folder's own trash on the Mac job). S/this_computer.py has no trash() today (grep: nothing). The recording's sounds ('<name> sound.m4a', 'sound 2'...) go with it, and reel-sounds.json's line for them is kept (names only). Lane D's posting queue never deletes and never calls it; it is named here so the helper is one helper, not two. CLAUDE.md's 'Three things NOT built' item 1 and parts' 'no button for that yet' lines change with it (Lane A, with Lane D's skill_text_check case retired).
- Lane A / B / C (reel page, talking page, designer, pickers): call look.crumbs(look.kit_trail(kit.name) + ...) in their bars with the trails in stage 1's note; hide the old Back pill (display:none, kept, as her pages do); the designer's nav takes her style='margin:0 0 12px' and shows only when the page has a kit. Lane D owns look.py and look.BASE; nobody else edits it. A trail step's href must be a path of this server (crumbs() refuses '://').
- Lane A (carousel picker, S/arrange_page.py): D7 is already sticky in main; Lane D touches nothing in arrange_page.py beyond, at most, one max-height line after the hand check, and says so to Lane A first.
- Home lane (S/home_base.py, S/home.py): v27 §8's Make posts screen words ('When your editing is done, start here...', 'What's a post kit?', 'How to make a post kit from a shoot' 1-2-3) are that lane's (home_base.WORDS m_lede, line 136, still has the v26 line). v27 §10's /home-data 'me' and 'posting' fields serve only v27 §13's home page idea ('not to build yet'): not built. The v26 test-only ?home=test scripts in posting_queue.py, report_page.py, edit_queue.py and post-kit.html are never built (v26 §6, v27 §14).
- S/posting_queue.py: Lane D adds only the action 'unposted' inside the existing /posting branch, no new path; do_GET unchanged (a posted piece's panel needs no fetch). New CLI command: unposted. Other lanes should not touch state(), set_status(), panel_choices(), add_for_kit(), kit_role(), kit_piece(), reel_version(), the page JS or CSS.
- S/reminders.py: nothing changes for v27. A posted piece keeps its event_uid (line 408), so unposted brings the reminder back on the new date by an update, not a second event; posting_reminders_page_check pins it.
- Lane D's v27 chat lines: her v27 §11 table names none on the post kit, the words page or the queue (checked); 'that one didn't go out after all' is Lane D's own addition to SKILL.md row 50.

### Open questions for Nicole

- Several reels, one set of words: your words page and words.py are unchanged since v24, so every reel of a shoot shares the reel's caption and ten hooks, and the queue's Copy caption gives the same caption for Fun Maternity and White Backdrop. Is that what you want, or should each reel have its own words page tab? (Built as yours.)
- The words page's own 'Add it to your posting queue' step still waits for a caption (your words.html), while the post kit adds without one and asks. Keep the two different, or let the words page ask the same question?
- Two reels of one shoot get two calendar reminders with the same title ('Post your Katie Austin Maternity reel today'). We can add the reel name ('... reel · Fun Maternity today'). Want that?
- When a post is switched back to Not posted and it had a reminder, we bring the reminder back on its new date. Or should switching back leave the reminder off?
- A posted post stays in the grid with no date until the grid is read again (your rule). Should the panel of a posted post also offer Copy caption and Copy my hook, or only the switch, as yours?
- 'Create another reel' shows once any reel of the shoot is made (your kit.reel rule). Fine, or only once every reel listed is made?
- The path at the top says 'Hannah post kit' (the folder name without its date). Keep that, or the kit's own name as the kit page's title shows it? And should the posting queue page get the path too (yours keeps Back to home there)?
- On the chat side we have no reel-label command: 'ready "<shoot> reel" --reel "<name>"' gives a reel its own spot and marks it ready in one go, and your page's press does the same through one route. Anything you needed reel-label on its own for?
- Remove this song: v27 settles it as two taps, to the Trash (Finder's Trash on a Mac, the Recycle Bin on a PC), the recording and its sound files together. Confirm that a song added from the chat (--capcut-song) is not removable this way, since it is CapCut's, not in the shoot's Music folder.

## E: the home base and its screens, the editing queue, the report, the first-backup question, the drop box (re-planned on branch v27 after the v26 merge)

**Estimate:** About one to one and a half days of focused work for Lane E on v27: E11 S (2 to 3 hours, the PC branch unproven until the first push), E10 S (about 2 hours), E12 M (about 4 hours, plus A8's wiring on Lane A's side), E14 S (about 2 hours), then the lane's own test sweep on both Pythons. The big v26 work (the home base, both screens, the editing queue, the report) is already merged and proven by home_base_check, edit_queue_v26_check and report_v26_check; the drop box and the naming question stay out by decision.

### Already on the branch from v26

- E1 the home base: home.page_html() draws from home_base.WORDS (her welcome, Today, four numbered cards, the folder card; no recent grid, no drop-downs); GET /home on the posting server (posting_queue.py do_GET line 1953); home.gather()['waiting'] and last_backup; proven by tests/home_base_check.py (213 with the hidden Chrome / 128 without: 'the home base: the four steps in the order of the work', 'nothing else: no recent-shoots list', 'the welcome words are hers') and tests/pc_smoke.py's /home checks
- E2 GET /home-data and POST /kit-archive: home_base.data() (today, card, groups, kits, stamp; each part fails soft, ids never paths), home_base.handle_get/handle_post with _cross_site guard, set_archived() writing ~/.studio/kit-archive.json with kit-archive.prev.json beside it, home.fingerprint() moving on it; proven by tests/home_base_check.py (the data part, the 403s, the 'That shoot isn't in your content folder.' refusal) and tests/pc_smoke.py line 1598 (GET /home-data)
- E3 Back up a card: home_base.backups_html(), backups(), backup_status(), records_of(), drive_here() (one backup from shoot.json's link, never from names; a sample never safe; second copy only when every file checked; unplugged and moved lines); GET /backups; proven by tests/home_base_check.py (the backups part, 'backups: her heading, her two paragraphs, her steps box') and pc_smoke line 1604
- E4 (the v26 half only): home_base.make_posts_html(), kits(), kit_thumb(), the archive <details>, Show older by month, the search over archived kits; GET /make-posts and /kit-thumb; proven by tests/home_base_check.py line 976 ('make posts: her heading, her paragraph, her steps box') and pc_smoke line 1603. The v27 words (What's a post kit?, the third step) are NOT in: home_base.WORDS still carries v26's m_lede, m_steps and m_s2_small
- E5 the editing queue: edit_queue.py actions unqueue/store/unstore (do_POST line 1157; store refuses a shoot that is not delivered), state() with stored_at, stored(), where(), the page's folds, Find a shoot, 'your assistant'; GET /make-posts-url and /home-url (line 1119); CLI unqueue/store/unstore/where (line 1248); proven by tests/edit_queue_v26_check.py (145) and the stage A review round in docs/handoff-v26-build-2026-11-14.md
- E6 (the intro only): parts/first-backup-setup.md has the 'Here's what's about to happen' paragraph before the questions (stage D); the Question 4 rewording is NOT built by decision (it still reads 'How do you like a shoot folder named?' with year-first recommended) and v27 says nothing new, so it stays out
- E7 the report: first_look.WORDS/OUR_WORDS, shoots_section(closing=True), closing_html(), the per-shoot Open this folder, the look-right line, her sneak-peek sentence (JPEG shooters told the truth), the 'two separate folders' line; serve_report.py GET open-shoot?shoot=<id> (403 cross-site, id never a path); parts/backup.md's new closing line; proven by tests/report_v26_check.py (107 / 102) and tests/shoot_report_check.py
- E9 the parts, links and harness: every Back to home is /home; 'your assistant' on every page (stage L, tests/loose_ends_v26_check.py 64); parts/hello.md, editing-queue.md, photos-in.md, after-the-report.md, where-things-live.md updated; .github/workflows/check-pc.yml runs edit_queue_v26_check, home_base_check, report_v26_check, loose_ends_v26_check on both jobs; CLAUDE.md's 'Nicole's v25 and v26' section and docs/nicole-v25-v26-notes-2026-11-14.md written (stage E)
- E8 the drop box: NOT built, by decision (posts.py bring still keeps the full copy in Drop a shoot here; bring-stopped.json only); v27 says nothing new, so it stays out of this lane's items

### Items still to build

| # | Pack | What | Size |
|---|---|---|---|
| E10 | v27 §8 Make posts from a shoot (make-posts.html, screenshot 08); wins over v26 §3 | The Make posts screen says what a post kit is: her new lede, the What's a post kit? box, 'How to make a post kit from a shoot' and a third step | S |
| E11 | v27 §2 step 3 'Remove this song (two taps, to the Trash)' settles the question of Nov 14; v26 notes §10 (the drop box) would use the same helper later; v27 plan Lane A note 'S/this_computer.py: a new trash(path) helper' | this_computer.trash(path): the computer's own Trash (Finder's on a Mac, the Recycle Bin on a PC), never a delete, with a tests' switch so no test touches the real Trash | S |
| E12 | v25 §5 and v27 §2 step 3: 'Remove this song (two taps, to the Trash)' and her /music/remove; settles item 1 of 'Waiting on Dustin and Nicole' in docs/handoff-v26-build-2026-11-14.md | Remove this song: the route that moves a song (and a recording's sounds) to the Trash, the record's song cleared, the instructions turned round, the test that held it absent turned into the test that it works | M |
| E14 | v27 (whole), v27 §13 and §14, the v26 plan's stage E | Lane E's build doc section, the note for Nicole, CLAUDE.md's 'not built' lines, the workflow and the test sweep | S |

### Stages

1. **E11.** The contract first: this_computer.trash(path) with its tests' switch and tests/trash_check.py, so Lane A's A8 (the song drop-down's Remove this song) and, when Dustin says yes, the drop box's clearing both call one helper. Lane E needs nothing from the other lanes before this: Lane A's fixed photo numbers do not change home_base.kits() or kit_thumb() (new photos go at the end, the first three stay the first three), and Lane D's look.crumbs() is for post kit pages, not these screens. About two to three hours.
2. **E10.** The Make posts screen's v27 words: WORDS, the What's a post kit? box, the third step, the CSS, home_base_check reading her v27 make-posts.html, hello.md and the guides. About two hours.
3. **E12.** Remove this song: the route, the record change, her words in reel_page.WORDS, the instructions turned round, songs_check's no_remove part turned into the remove part. The button itself is wired by Lane A in A8 against this route (merge v27-e before A8, or A8 wires it on the current list and the drop-down inherits it). About four hours.
4. **E14.** Lane E's section of the v27 build doc, the note for Nicole, CLAUDE.md's three 'not built' lines, the workflow, the lane's test sweep on both Pythons. About two hours.

### Decisions (the default the build takes)

- **E10:** v27's lede, steps title, step-2 line and third step replace v26's whole; 'single photos' stays in her lede (the v26 question for Nicole stands).
- **E10:** The screen keeps the Back to home pill, not the crumbs path: her make-posts.html keeps the bar, and crumbs.js is for post kit pages only (Lane D).
- **E11:** The Trash is the computer's own (Finder, the Recycle Bin), never a hidden folder of ours: Nicole's v27 does exactly this and Dustin's rule is kept because Put Back works.
- **E11:** The helper moves one item; callers decide what goes together and check every path before the first move.
- **E11:** A PC uses Windows' own Recycle Bin call (nothing installed), as the v27 plan's Lane A question 'send2trash would be an install' already proposes.
- **E12:** Built as her v27, to the Trash (Dustin's 'only take it off the list' is not taken: v27 is her newer answer and Put Back keeps it reversible).
- **E12:** Only songs in the shoot's Music folder can be removed from the page; a recording in the Photos folder is theirs (an export folder) and stays, with a line of ours (hers would trash it from wherever list_songs found it).
- **E12:** A recording's sounds go with it (hers: ' sound' and ' sound 2..9'; ours: any number, and the ones noted in reel-sounds.json).
- **E12:** No chat command removes a song (hers has none); the assistant points at the button.
- **E12:** Other reels that picked the song are not rewritten; they show her song_gone line when opened (as hers).
- **E14:** v27 §13's friendlier home page and /home-data's `me` and `posting` fields (v27 §10) are not built: she put the page back and asked to brainstorm first.

### Her faults we fix rather than copy

- **E10:** Her page loads her CSS and Google Fonts from the internet and the .whatkit colours from her home-test.css: ours are inline in home_base.CSS in look.py's tokens, nothing from the internet (as stage B).
- **E10:** Her Open the post kit still goes to post-kit.html on 8799: ours stays the kit page on the same server (as stage B).
- **E11:** Her osascript builds the AppleScript with the path handed in as an argument (fine) but stops at the first failure with earlier files already gone: the loop moves to the caller, which checks first.
- **E11:** Hers is Mac-only (osascript): ours has a PC branch.
- **E12:** Her route takes any path from the page and checks it only against list_songs' paths: ours takes an id and resolves it server-side, refusing another website's press.
- **E12:** Hers moves files one at a time and stops at the first failure with some already gone: ours checks every path first, then moves, and names which moved if one fails.
- **E12:** Hers never clears the song in the record on the server (the page does it on success): ours clears the open reel's pick under the lock, so a page that never gets the answer still sees it on reload.
- **E12:** Hers would send a recording from the Photos folder (their export folder) to the Trash: ours refuses.

### Touches other lanes

- Lane A (A8, songs): the 'Remove this song' button and its two taps live in A8's song drop-down (v27 wins over v25's per-row Remove); it calls Lane E's POST /reel-song-remove {kit, song: id} and uses the words in reel_page.WORDS (song_remove, song_sure, song_removing, song_trashed) and this_computer.TRASH_WORD/TRASH_BACK for a PC; do not write a second trash or a second route. The Chrome part of the test (the two taps, the 4 s timeout, the line under the button, the song list redrawn) is A8's; the by-request part is in songs_check.
- Lane A (A7, fixed photo numbers): nothing in home_base changes; kits() counts kit_mod.photo_files and kit_thumb() serves the first three, which stay the first three when photos are appended. The kept small pictures per kit (stage B's choice) are unchanged.
- Lane D (D6, look.crumbs()): the Home step is '/home' (home.py on the posting server; no 8790/8799 address, no localStorage test flag); her crumbs.js has no 'Make posts' step, so none is added; the two home screens, the editing queue and the report keep the Back to home pill (her make-posts.html keeps the bar). The editing queue's 'Make posts from this shoot' already lands on GET /make-posts (via /make-posts-url) and '#kits' scrolls to the list.
- Lane D (v27 §8 Posted/unposted on /posting): the posting lane's, as the v27 plan says; /home-data's `me` and `posting` (v27 §10) are not built (only the §13 idea reads them), so Lane D need not expose anything for them.
- S/posting_queue.py: Lane E adds no new route tuple this round; '/reel-song-remove' is one entry in the reel POST tuple at line 2350 (Lane A's line in Lane D's file): one-line edit, named here so nobody adds it twice. GET /backups, /make-posts, /home-data, /kit-thumb and POST /kit-archive are already there from stage B.
- Lanes B and C: /home-data still carries no `queue`; the stories designer's My editing queue template reads GET /design-queue (stage C), which stays.
- The drop box (v26 notes §10, old E8): still waits on Dustin and Nicole; when they say yes it clears through this_computer.trash() with the set-aside fallback the earlier plan drew, nothing else new. The folder-naming question (old E6) likewise waits; v27 says nothing on either.
- P/where-things-live.md and CLAUDE.md: Lane E adds one line each (nothing deleted, the Trash is the computer's own; Remove a song now built); other lanes append their rows in the same files and the whole-build round merges by hand.
- .github/workflows/check-pc.yml: tests/trash_check.py on both jobs; no other new test file from Lane E (songs_check and home_base_check are already there).

### Open questions for Nicole

- Remove this song is built as your v27: to the Trash (the Recycle Bin on a PC, with nothing installed), and a recording's sounds go with it. Two choices of ours: only a song in the shoot's Music folder can be removed from the page (a recording sitting in the Photos folder, your export folder, stays, with a line saying to take it out there), and a second reel of the shoot that had that song picked is not rewritten, it just says 'That song isn't there anymore' when opened, as yours does. OK on both?
- The Make posts screen now has your What's a post kit? box and three steps. Its lede still says 'single photos'; the post kit has no single-photo card (a one-slide carousel is a single post). Keep the words?
- Your v27 /home-data adds `me` and `posting` for the friendlier 'Good morning, Nicole' home (§13). Not built until you've brainstormed the page; say when.
- Still open from v26 on this lane: a delivered shoot's pill reads 'Edited' on the Back up a card screen while the queue says Delivered; a press on step 1 or step 3 is still recorded (yours records nothing); searching for an archived kit reads 'No post kit called ... yet' above the closed Archived list (yours does the same); Archive on a post kit asks nothing first; no chat command archives a kit (the button only); a moved folder's line says 'tell your assistant where it went' and the assistant has no way to re-point a backup's records (it says so, and that moving it back fixes the button).
- For you and Dustin, unchanged: the first-backup folder-name question (name then date, or year first, as the suggested one, and your rewording) and the drop box's second full copy (now that a song can go to the Trash from the page, is clearing the drop-box copy to the Trash after a checked picker sort the same kind of thing? Dustin's call).
- The chat's 'show the archive' still scrolls to Uploaded shoots (as yours, #archive); 'show my archived shoots' opens Archived. Should 'the archive' now mean Archived?

## How the lanes meet

- Lane A commits photo numbers that stay fixed first (message contains "numbers stay fixed"); Lanes B and C merge `v27-a` for it. Lane D commits `look.crumbs()` first ("crumbs"); every page lane merges `v27-d` for it. Lane E commits the Trash helper ("trash helper") and the song-remove route ("song remove route"); Lane A merges `v27-e` before the song drop-down.
- In `S/posting_queue.py` each lane edits only its own page's route tuple; Lane D owns the rest. `parts/arrange.md` by section; `SKILL.md`'s table and `parts/where-things-live.md` get one row per lane.
- Each lane ends with an adversarial reviewer and a fix round; then the lanes merge into `v27`, the whole-build round runs the sweep, `tools/check_plugin.py`, `tools/check_pc.py` and `tests/skill_text_check.py`, and GitHub's Windows and Mac machines run on the push.
