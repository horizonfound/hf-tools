# Nicole's v25, v26 and v27: the build plan (Nov 17, 2026)

Branch `v27` (main is tagged `before-v27`), built in five lanes on worktrees `v27-a` to `v27-e`, merged back into `v27`. Her packs are in `reference-private/nicole-handoff-v25-2026-11-13/`, `...-v26-2026-11-13/` and `...-v27-2026-11-17/` beside the main checkout, plus her notes `reference-private/nicole-notes-v25-2026-11-13/`: data only, read, never run, never copied over ours, never in git. v27 says everything in v20 to v26 still stands except where v27 changes it, so v27 wins where they differ.

Standing rule (Dustin): identical for the photographer (every word on the page hers, same behaviour, built from her screenshots), our way underneath. Where hers and ours differ on words, posting, hooks or the calendar, Nicole's wins. Her faults are fixed, not copied, and listed. Where she says "still for you to decide", the build takes the default written below and the question goes in the note for Nicole.

Dustin, Nov 17 (going to bed, "you have the green light"): build it, ship it, and message Nicole with install steps that keep her current copy safe. Built overnight by Claude in lanes, each lane with a reviewer and a fix round, then a whole-build check.

Short names: `S` = `plugins/the-engine/skills/studio-manager/scripts`, `R` = `plugins/the-engine/skills/assistant-make-a-reel/scripts`, `P` = `plugins/the-engine/skills/studio-manager/parts`.

This plan was written from five planners' maps of her packs onto our code (each planner read the packs in full and grepped main). The full item lists, with her exact lines and our file-by-file changes, are what the lanes build from; this file is the readable form.

## Lane A: the reel page, several reels, songs, trim, the footage editor, B-roll, the paces

Nicole's v25 and v27 rebuild the reel page and change every reel's timing. The timing engine (ours: R/timing.py, hers: bts_reel.py) must (v25 §9) move the beat grid onto the song's audible hits and charge a cut where the song doesn't hit, and (v27 §9) give Calm, Build and A little of everything clearly different holds; her re-recorded 22 acceptance lines (v27) are the contract and none of them matches main today. The page gets a chooser of four kinds (Behind the scenes, Just photos, Talking to camera, B-roll), several named reels per shoot with everything per reel, a photo note and the "the photographer decides" rule, a footage editor laid out like a video editor (trim on the timeline, Your clips with YOUR PICK tags and short names from the chat), songs with Listen and Remove to the Trash, a short song starting after its glitchy opening, Lightroom-style multi-select, "Would you like to direct this edit?", "Watch your reel before you make it" (a dry-run plan played in the browser with Another part of this song, Try another mix, Undo and Redo), B-roll finished on the page with words on screen and Save my video (an MP4 with nothing installed: AVFoundation on a Mac, a named gap on a PC), and "Add this reel to my posting queue". Three new chat lines (Name my clips, Edit my reel and follow my direction, Pick my reel photos for <shoot>, <reel>, and follow my note) need parts and tests. Nothing of this is in main except the structure that makes it cheaper: reel.py already calls timing.py (so the chat reel maker gets the new paces for free), the record lock and counter, the moments routes, the small video copies and strips, and the job machinery for Make my reel.

**Estimate:** Roughly 10 to 12 days of focused work for Lane A: four L items (several reels, the footage editor, watch before you make, Save my video), eleven M items and three S, each built in the usual stages with two reviewers and a fix round and a check per fix. The timing (A1 and A2, about a day together) comes first and gates everything that previews or makes a reel; Save my video (A15) carries the one real unknown (Core Animation from JXA) and should be prototyped on a 6 s clip before its day is spent.

### Items

| # | Pack | What | Size | In main today |
|---|---|---|---|---|
| A1 | v25 §9 (and v27 §9's acceptance file, which carries it) | Every vibe lands on the song's real hits: the hit finder, the snapped grid and W_EMPTY in timing.py | M | new |
| A2 | v27 §9 | The paces are now clearly different: Calm, Build and A little of everything in timing.py (ships with A1: one acceptance file) | M | new |
| A3 | v25 §9 last bullet; v27 §14 | The chat reel maker (R/reel.py) gets the same hits and paces | S | already-in-main |
| A4 | v25 §2; v27 §2 (Your reels under each kind's title) | Several reels from one shoot: the Your reels bar, the record's versions, everything per reel | L | new |
| A5 | v25 §3; v25 §10 third bullet; v27 §2 step 2 words | Picking photos: the photographer decides, the photo note, and the copy line with the reel's name | M | new |
| A6 | v27 §2 (the chooser); v27 §2 'Each kind is its own page' | Which reel do you want to create? The chooser of four kinds, KIND_WORDS, the steps per kind | M | new |
| A7 | v27 §2 step 1 and step 2 small changes | Step 1 and step 2 as rebuilt: the videos fold into one drop-down, the ask box moves up with new words, + Add photos with fixed numbering, the order sticks to the top | M | partly-in-main |
| A8 | v25 §5; v27 §2 step 3 | Songs: the drop-down with Listen and Remove this song (to the Trash), a short song starts after its glitchy opening, a replaced recording's sound taken again | M | partly-in-main |
| A9 | v25 §8 | Select several photos, like Lightroom: shift-click, Cmd/Ctrl-click, drag the whole selection, the selected bar, Add them to the end | M | new |
| A10 | v27 §2 'Watch your reel before you make it'; v27 §10 (/reel/preview, /reel/song, /reel/make) | Watch your reel before you make it: the plan from a dry run played in the browser, Another part of this song, Try another mix, Undo and Redo, Make this one in CapCut | L | new |
| A11 | v27 §3; v25 §4 (superseded, see decisions) | The footage editor: player, Footage drop-down, Make a clip with the orange trim that grows, the timeline of stills with Zoom in, Your clips in two columns | L | new |
| A12 | v27 §3 'The photographer's own clips'; v27 §11 | Naming the photographer's own clips from the chat: footage.py picks and describe, the 'Name my clips for <shoot>' line | M | new |
| A13 | v27 §2 step 4; v27 §11 | Would you like to direct this edit? The direct note, its copy line, and the assistant arranging clips, photos and style from it | M | new |
| A14 | v27 §4; v27 §10 (/reel/make: B-roll needs no photos) | B-roll on the page: clips only, each cut on the beat, words on screen dragged into place, carried into CapCut | M | new |
| A15 | v27 §4 'Save my video'; v27 §10 (/reel/video) | Save my video: the finished B-roll MP4 with the words on it, made with nothing installed | L | new |
| A16 | v27 §2 'Add it to my posting queue' | Add this reel to my posting queue, from the reel page (the bar under Your reels and the result box) | M | new |
| A17 | v27 §11; v25 §3; v25 §10 (third bullet); v27 §3 | The instructions: the new chat lines, several reels, the chooser, B-roll and the editor in the reel skill, parts/arrange.md, curating.md and the core table | M | new |
| A18 | v25 §11, v27 (its 'tested as your build' line), v27 §12 | The whole-build check for Lane A: her words compared both ways against v27's page and server, the PC jobs, and the note for Nicole | M | new |

### Build order

- A1 and A2 together: the timing (every preview, make and the chat reel depend on it; her 22 lines are the only hard proof in the pack and they fail on main today)
- A3: verify reel.py needs nothing (a check, minutes)
- A4: several reels (the record's shape that A5, A10, A12, A14, A15 and A16 all key on; Lane D's reels_of contract comes out of it)
- A6: the chooser and the kinds (the page's skeleton for every later step; the kit card's door)
- A5: the photo note and the not-picked rule (small, and it fixes the instructions' direction early)
- A7: step 1 and 2 changes with append-only numbering (shared with the other lanes: land it early so their tests settle)
- A8: songs (Listen is also the watch step's audio; the lead-in feeds the make and the preview)
- A11: the footage editor (the largest page piece; the trim and Your clips are what B-roll and the watch step show)
- A12: clip naming (needs A11's cards and A4's per-reel lists)
- A10: watch before you make (needs A8's audio, A11's clips, A1's timing)
- A14: B-roll on the page (needs A10's preview and A11)
- A15: Save my video (prototype the AVFoundation words layer first; needs A14)
- A9: multi-select (independent; anywhere after A6)
- A13: direct this edit (independent; needs A4 for the reel's name)
- A16: the queue button (after Lane D's per-version pieces; the page side can be built against a stub)
- A17: the instructions (as each piece lands, finished last)
- A18: the whole-build check, the PC jobs, the notes for Nicole

### Decisions (the default the build takes)

- **A1:** HIT is ranked from the unsnapped grid points' onset (her order of operations); keep it that way so the 22 match.
- **A1:** Fewer than 8 hits (a very short or quiet song): no snapping and no W_EMPTY, exactly as hers; the no-song even grid is untouched.
- **A1:** The extra test cases are re-recorded from our engine (never hers) once her 22 match.
- **A2:** Calm's odd-count cost (0.45) and its one-beat fallback (cost 3.0) are hers to the number; not tuned by us.
- **A2:** The legend line 'Longer stays on screen about twice as long' is left as hers although Calm's Longer is 1.5x and Build's is one beat more (already on the owners' list since v22).
- **A3:** No second code path: her request is met by the shared engine.
- **A4:** Where the assistant's pick for Reel 2 and later lives: built in the reel record per reel (kit.json keeps the first reel's, as always); kit.py picks --reel-name routes it there.
- **A4:** Default names 'Reel 1', 'Reel 2'… (hers); a typed name that another reel has is refused (ours).
- **A4:** A switch reloads the page (hers); the scroll position is not kept (as hers).
- **A5:** On 'make my posts' the reel's photos are not picked any more (hers); the Assistant picks when the page's line is pasted.
- **A5:** The note narrows the set; the Assistant still chooses and orders within it (rule 11).
- **A6:** A reel's kind is remembered per reel (ours) rather than only read from the address (hers).
- **A6:** The 'Recommended for behind-the-scenes reels' tag shows only on bts (as her BUILD.md meant; her CSS showed it everywhere, already on the Tell Nicole list).
- **A7:** Numbers are append-only from now on (hers); an older kit keeps its numbers as they are.
- **A7:** 'Show my new photos' reloads after a save (hers), rather than redrawing in place.
- **A8:** A PC uses the Recycle Bin through Windows' own call (hers suggests send2trash, which would be an install).
- **A8:** The lead-in replaces our decision 8 (a short song starts at the top) only when a silent gap is found; otherwise the top, as before.
- **A8:** −50 dB and 0.3 s are hers; the window is 10 ms RMS (ours; silencedetect's exact window isn't documented, so one acceptance clip with a known 1.2 s gap pins it).
- **A9:** A batch dragged from All your photos lands where it is dropped, in shoot order (hers).
- **A9:** Escape clears the selection (hers); the big view's Escape still closes the big view first.
- **A10:** The preview's photo frames come from the existing 1600 px copies (no new sizes).
- **A10:** A dry run is capped at 30 s; past it the page says her 'couldn't work out the cut' line.
- **A10:** Undo/Redo in the watch step also changes the saved song, pace and style (hers); it is the same record, one save per step.
- **A11:** The v25 ✂ Trim panel (quarter-second nudges, 'Play it again', Done/Cancel) is not built: in v27 the trim lives on the editor's timeline and her page leaves the panel unreachable. Open question for Nicole.
- **A11:** A clip picked by a click shows 'Play this clip' and her trim line under the list (her edSel box), as hers.
- **A11:** The Footage drop-down's picture is the strip's still nearest a third of the way in (no new video run).
- **A12:** describe writes the record directly under the lock (ours), not through the page server (hers).
- **A12:** Labels only (her 'the short name is enough'); 'about' is refused if present rather than stored.
- **A13:** The chat command sets style, clips and order in one save (ours; hers names no command: her assistant edited the record by hand).
- **A13:** A direction that names a moment not on the cards sends the Assistant to the footage look for that moment only.
- **A14:** onscreen is only saved as pos 'custom' with x, y (hers after Nov 17); the hidden selects are not built.
- **A14:** A B-roll reel is a 'made' entry like any other (version, footage 'broll', no picks).
- **A15:** Core Animation draws the words (not PIL): the box styles are one box behind the whole block rather than her per-line boxes; the note for Nicole shows both.
- **A15:** The render runs as a job (bounded, polled), not inside the request (hers blocks the request up to 30 minutes).
- **A15:** A PC gets a named gap and the PC line; no install asked for.
- **A16:** Adding from the reel page needs no caption (hers, v25 §6); the kit page's own rule is Lane D's.
- **A16:** The rhythm question uses the words page's existing route and chips (one copy).
- **A17:** The core table sends all three new lines to the reel skill, as today's rows do.

### Her faults we fix rather than copy

- **A1:** Her hits list is captured by monkey-patching beats_lite.onset_strength on its first call; ours reads keep_onset=True, which is the same numbers without the patch.
- **A1:** Her snapping mutates the cached grid in place so a second reel of the same song in one process snaps an already-snapped grid; ours snaps once when the Grid is built and caches the snapped Grid.
- **A2:** Her Calm on a short song said 'Your song is only…' with a wrong reason (she says so); the fallback length fixes it in hers and ours alike, and our STOP line still comes only when even one beat each can't fit.
- **A4:** ver_op 'new' lets two reels share a name; ours refuses the duplicate.
- **A4:** Her switch is a whole-page reload after an unchecked save; ours sends the save through /reel-save's counter first, so a second window's newer save is never written over.
- **A4:** Her REEL_LIVE loses 'removed' (our Undo-after-Remove store) on a switch; ours keeps 'removed' per reel too.
- **A5:** Her NOT_PICKED line shows for a new reel even while 'I'll drag them in myself' is on; ours shows it only under 'Let my assistant choose' with no pick for this reel.
- **A6:** Switching under 'Your reels' to a reel of another kind keeps the address's kind and hides the wrong steps; ours reopens the reel as its own kind.
- **A6:** Her chooser decides the title in JS after load; ours writes it on the server.
- **A7:** Her prepare() falls back to name order when photos.json is missing any file it lists, renumbering everything; ours never renumbers a photo the list already has.
- **A7:** Her page checks /photos.json every 4 s even when hidden only by the visibilitychange guard; ours asks /reel-state, which it already polls, so no second poll.
- **A8:** Her /music/remove runs osascript per file and stops at the first failure with some files already gone; ours checks every path first, then moves them, and says which moved if one fails.
- **A8:** Her seconds() uses afinfo (Mac only) to decide a short song; ours uses capcut.song_length / sound.duration (both systems).
- **A8:** Her sound_of overwrites nothing but picks 'sound 2' by mtime alone; a sound file touched by Spotlight would be taken as newer. Ours compares the recording's size and mtime recorded beside the sound (facts.json), not mtime alone.
- **A9:** Her Take them out on the selection leaves marks[n] for the removed photos; ours clears them so a re-added photo starts plain (as a single × does).
- **A10:** Her preview JSON leaks the song's relative path and each clip's src; ours sends ids and keys.
- **A10:** Her 'v.src.endsWith(u)' check reloads the clip when the address is encoded differently; ours compares keys.
- **A10:** Her preview runs bts_reel.py with no lock against Make my reel and shares last-plan.json by folder name; ours has its own folder per kit and a lock per kit.
- **A10:** Her short-song rule (afinfo < 40 s) and the preview's song_start disagree when the preview chose a start: ours sends the watched start to the make every time.
- **A11:** Her /moments/add makes the still with ffmpeg; ours uses the strip or video.stills under the one video turn, as today.
- **A11:** Her ED.added is lost on a reload, so a reload right after Add clip lets the same stretch be added twice; ours clears the trim after a successful add is seen in the record (the clip is on the list) and keeps the stretch drawn dashed from the record's newest 'you' clip.
- **A11:** Her edGo zooms to a 40 s window only for videos over 90 s and over 60 s for Start here (two different thresholds); ours uses one (60 s), noted for Nicole.
- **A11:** Her card click (edGo) and the × share one element; a × press on a card whose clip is in the editor clears ED.edit but not a trim in progress; ours clears both.
- **A12:** Her describe silently writes 'about' up to 400 chars though the feature was taken out; ours refuses the field.
- **A12:** Her picks sheet names the file by a hash of the video's base name, so two clips from the same video overwrite each other's close look between runs; ours writes each look in a fresh folder (as scan does).
- **A13:** Her page saves direct on every keystroke with the whole saved record; ours sends only the changed field (as every other box).
- **A14:** Her /reel save keeps onscreen's x, y and size only through the later keys loop (strings cut to 300 chars, numbers stringified); ours checks them as numbers in range.
- **A14:** Her summary() writes the sum twice (photos then B-roll); ours once.
- **A15:** Her render() checks for the output's existence twice but writes '.part.mp4' beside it with no lock, so two presses race; ours takes the kit's job lock and names the part file by the job id.
- **A15:** Her broll_video raises FileExistsError after a full render when the name appeared meanwhile; ours picks the free name under the lock before rendering.
- **A15:** Her ffmpeg run has no memory bound; ours runs under the video turn and the guard the tests use.
- **A16:** Her reelToQueue re-enters itself after the rhythm is set without checking the add didn't already happen; ours asks once and adds once.
- **A16:** Her 'already in your queue' check only looks for status green; a piece queued without a date reads as not queued and can be added twice; ours asks the queue by version.

### Touches other lanes

- Lane D (posting queue, v25 §6 and §7): the reel page's record is reel-page.json with 'versions' [{id: 'v1'…, name, data}] and 'current'; the open reel's fields stay top-level; 'made' entries carry 'version' (missing = v1) and, for a saved B-roll video, 'video' (file name in <kit>/Reels). Functions Lane D can call: reel_page.reels_of(kit) -> [{id, name, made, project, order: [{n, h}]}], reel_page.order_for_kit_page(kit, rows, rec, version=None), reel_page.newest_project(kit, rec_kit, version=None). Ids: the first reel keeps '<kit id>-reel', each other '<kit id>-reel-vN'; pieces carry version and reel_name; the queue shows '<shoot> reel · <reel name>'; the cover picker asks the order by version. The reel page will POST the add as {kit, piece: 'reel', version} to the words page's queue route and read GET /posting/reels?kit= -> {interval, reels: {vN: {status, date}}, url}: Lane D adds 'version' to /words-queue and /words-rhythm and that GET. Captions optional on add (v25 §6) is Lane D's kit change.
- Post-kit lane (kit.py): the Reel card becomes the Reels card with her words ('Create as many reels as you like from this shoot: behind the scenes, just photos, talking to camera, or B-roll. Each one is cut on the beat of your song and opens in CapCut, ready for your look.', 'Create my reels' / 'Create another reel') opening /reel.html?kit= (the chooser); per-reel preview strips and step 3's per-reel status (v25 §6) read reels_of; kit.py picks --reel gains --reel-name for a later reel (writes the reel record, not kit.json); parts/post-kit.md step 2: the reel is no longer picked while the kit is made (v25 §3 and §10); what 'make my posts' still makes without being asked is that lane's call and an open question.
- Lane B (talking reel): the chooser's 'Talking to camera' card links to /talking.html?kit=; 'Your talking reels' / '+ Start a new talking reel' (v25 §2) uses the same ver_op with TALK_LIVE (every key but versions and current) and refuses a switch while a video is being turned into words; v27's /capcut/open ('Open CapCut' on the talking page) is Lane B's; the reel page already has /reel-capcut.
- S/posting_queue.py: no new dispatch code expected: the reel page's new GET paths (/reel-song, /reel-preview is POST) and POST paths (/reel-version, /reel-preview, /reel-video, /reel-song-remove) go into reel_page.GET_PATHS / POST_PATHS, which posting_queue hands to reel_page.handle_get/handle_post; verify the dispatch there is by those tuples (lines ~1825 and ~2192) and not by a hard-coded list. /reel-song must stream with Range (reel_page.send_range exists).
- S/arrange.py and S/kit.py sheet: the numbered list becomes append-only (A7): the carousel picker, the designer and kit.py build share it; one change, their tests rerun (arrange_check, design_check, kit_steps_check).
- S/this_computer.py: a new trash(path) helper (Finder on a Mac, the Recycle Bin on a PC) and new PC lines (Save my video, the editor without stills, clip naming); other lanes may reuse trash() (v26 suggests clearing the drop box to the Trash).
- R/video.py: a new 'render' program (A15) under the same video turn lock every video job uses; tests must keep running one video test at a time under the guard.
- R/reel.py: --dry-run --status now writes 'pieces' (A10) and --hook-whole (A14); the talking reel's builder and capcut_even's eight kept projects must stay byte for byte.
- Parts and the core table: studio-manager/SKILL.md rows for 'Name my clips for <shoot>', 'Edit my reel for <shoot>[, <reel>], and follow my direction', 'Pick my reel photos for <shoot>, <reel>, and follow my note'; parts/on-a-pc.md and the PC guide: Save my video and clip naming not on a PC; parts/where-things-live.md: versions, moments_found, onscreen, the Reels folder.
- v27 §7 crumbs.js (Home › post kit › Reels › B-roll on every page) is page chrome across all pages: whichever lane owns look.py/brand.bar should build it once; the reel page will show '← All the reels you can make for this shoot' and the kit link in its bar until then.

### Not to build

- v26 in full (the home base and its screens, backups.html, the editing queue's Delivered/Archived/Find a shoot, the stories designer's templates and sets, home_data.py): other lanes; nothing in v26 touches the reel page ('Unchanged since v25: the reel page, talking reel, footage, timing').
- v25 §6 (the post kit: captions optional, per-reel previews, 'Which reel goes in your queue?') and §7 (the posting queue per reel, the reel cover picker): Lane D; only the contract above is Lane A's.
- v27 §5 (the talking reel: fix a word, Open CapCut, Add more photos) and the 'Your talking reels' bar: Lane B.
- v27 §6 (the carousel and stories designer's tools) and §8 (Posted in the posting queue, the Make posts screen): other lanes.
- v27 §7 crumbs.js: page chrome for every page (noted under cross-lane), not a reel-page piece.
- v26 §6 / v27 §14 test-only Home links (?home=test, sessionStorage assistantHome): hers for her test home; not built.
- Her HITGRID (cutting A little of everything from hit to hit): tried and set aside by her, left switched off; ours doesn't carry it.
- Her 'own' pace (v22: keep or drop): still out.
- The two-sentence clip description ('about'): taken out by her ('the short name is enough'); refused, not stored.
- Top/Middle/Bottom and 'how long it shows' for the B-roll words: taken out by her (hidden selects in her page); not drawn.
- Her v25 Trim panel (✂ Trim, quarter-second nudges): superseded by the v27 editor (open question 2).
- send2trash on a PC: an install; Windows' own Recycle Bin call instead.
- ffmpeg anywhere (her loudness, stills, moments, lead-in, broll_video): nothing installed; AVFoundation and plain Python as today.
- v27 §13 the friendlier home page: an idea, not to build.
- v27 §14 'working on it' on the talking reel: Lane B, and an idea.
- Whisper (v24's later idea): still parked.

### Open questions for Nicole

- v25 §3 says 'I choose, not you' and nothing is picked on 'make my posts'; the Assistant's rule 11 says choosing and ordering is its job. Built: the reel's photos are picked only when the page's line is pasted (yours), and the Assistant still chooses and orders within your note. Should the carousel, singles and stories also wait to be asked (the post-kit lane's call)?
- The v25 ✂ Trim panel (the quarter-second ◀ ▶ nudges, 'Play it again', Done/Cancel) is unreachable in your v27 page: the editor trims on the timeline instead. Built: the editor only. Do you want the panel back anywhere?
- 'Remove this song' on a PC: built with Windows' own Recycle Bin call (nothing installed; you suggested send2trash, which would be an install). OK?
- Save my video on a PC: not possible with nothing installed. Built as a named gap with a line saying Make this one in CapCut works there and the words go with it. OK, or should a PC be asked to install something?
- The words in the saved video are drawn by the Mac's own text engine, not Pillow: the same font, size and wrap width as the page, but 'White text on black' is one box behind the whole block rather than a box per line. Acceptable, or must it match your screenshot 18 per line?
- Your acceptance file's 22 lines are matched exactly; our extra timing cases (60 photos on the test beat, the clip cases) are re-recorded from our engine, since we never run yours. OK?
- The legend still says 'Longer stays on screen about twice as long' while Calm's Longer is 6 beats to 4 (1.5x) and Build's is one beat more. Reword, or leave?
- Where the Assistant's pick for Reel 2 and later lives: built in the reel page's record per reel (the first reel's stays in the kit's own file, as always). Any reason to keep them all in one place?
- Renaming a reel to a name another reel already has is refused in ours (yours allows it, which makes 'Pick my reel photos for <shoot>, <reel>' ambiguous). OK?
- A reel saved before v27 (no kind) opens as Behind the scenes when footage was on, Just photos when off, and the chooser when nothing was chosen. OK?
- Undo and Redo in the watch step also change the song, pace and style chosen in steps 3 and 5 (they are the same choices). As yours; say if you'd rather Undo there only covered the mix and the part of the song.
- The orange trim zooms in on about 40 s for a video over 60 s (Start here) and over 90 s (clicking a clip) in your page; built with one threshold, 60 s. Fine?
- Multi-select has no touch-screen way (no shift or Cmd on a finger); not built, as yours. Fine for now?
- The B-roll words' dragged position carries into the saved video; CapCut's text layer sits at CapCut's default spot (your tip says change it there). Say so on the page, or leave the tip as it is?

## Lane B: the carousel and stories designer

Nicole's v26 and v27 turn the designer from "lay photos on slides" into a working editor: Redo; sets of stories (the Nov 6 one-design rule is gone); the stage pinned at the top for carousels and stories; a note to the assistant with a copy line ("Pick my story photos for <shoot>, and follow my note" / "Pick my carousel photos for ...") that the assistant answers by filling the newest design's empty frames; slides added before/after/at the end, removed from their label, dragged by a grip; a real Crop window; Show the whole photo; several photos at once (Even them out, Same size, Line up tops, Remove them); a big view of any tray photo; Save just this slide; a permanent Open folder; + Add photos with numbers that stay fixed; seven new story templates (Gallery delivered, My editing queue filled from the editing queue, The full story, Seamless swipe, and the three collages); "Show Instagram's guides". Main has none of it except the sticky stage and the global [hidden] rule. Everything is built our way: nothing new installed, no path to the page, every POST field-checked, the single-slide save through staging and the no-overwrite commit, Finder/Explorer words from this_computer, records in .kit and ~/.studio. 20 items, about five days of focused work with tests; the chat-side fill command and parts/arrange.md changes touch the shared instruction files.

**Estimate:** About 5 to 6 days of focused work with tests: four L items (Crop, several photos at once, Save just this slide, + Add photos with fixed numbers), ten M (ask box, fill command, sets of stories, templates and the queue route, insert/remove slides, Where should it go, drag slides, See a photo big, the v27 test file, Redo-adjacent wiring), six S. The chat-side fill and the instruction edits are shared files; + Add photos waits on reel.py's sheet keeping numbers.

### Items

| # | Pack | What | Size | In main today |
|---|---|---|---|---|
| B1 | v26 §5, notes §14 | "Show Instagram's guides" (the bands' tick renamed) and the story lede's new last sentence | S | new |
| B2 | v26 §5, notes §14, v27 §6 | The slides stay in view: the stage sticks to the top of the window, stories and carousels alike | S | already-in-main |
| B3 | v26 §5, notes §14, v27 §6, v27 §11 | Let my assistant choose the photos: the note box, the `ask` field and the copy line, in stories and carousels | M | new |
| B4 | v26 §5, v27 §6, v27 §11, notes §14 | The assistant fills the frames from the chat: `design.py fill`, and the two chat lines in parts/arrange.md and SKILL.md | M | new |
| B5 | v26 §5, notes §14 | Redo beside Undo (Cmd+Shift+Z or Cmd+Y) | S | new |
| B6 | v26 §5, notes §14 | Sets of stories: the name box, "My story sets ▾" and "+ New set of stories" in the stories designer; the one-design rule retired | M | new |
| B7 | notes §12, v26 §5, notes §14, v27 §6 | Seven new story templates in Add stories: Gallery delivered, My editing queue (filled from the editing queue), The full story, Seamless swipe, Playful mosaic, Mood board, Overlapping collage | M | new |
| B8 | v27 §6 | Adding and removing slides: + and × on every label, Add a slide before / Add a slide after / Remove this slide in the selected-thing bar (stories say story) | M | partly-in-main |
| B9 | v27 §6, the [hidden] CSS lesson | Where should it go? in Add slides / Add stories, the changed adding line, and the over-limit refusal when a template is added | M | new |
| B10 | v27 §6 | Drag slides by the grip on their label; a coral line shows where it lands; slides sharing a stretched photo move together | M | new |
| B11 | v27 §6 | Crop: the whole photo with a box; corners keep the frame's shape; untick for eight handles and the frame takes the box's shape; Done maps to zoom and offset past the 300% slider | L | new |
| B12 | v27 §6 | Show the whole photo (in the selected-photo bar and inside the Crop window) | S | new |
| B13 | v27 §6 | Several photos at once: Shift/Cmd/Ctrl-click, drag any to move them all, the bar with Even them out, Same size, Line up tops, Remove them, Done | L | new |
| B14 | v27 §6 | See a photo big: double-click a tray photo or press its ⤢; ‹ › and the arrow keys browse; Use this photo / Put it in the selected frame; a single click waits 230 ms | M | new |
| B15 | v27 §6 | Saved, then Open folder: the saved line gets Open folder, and a permanent Open folder button beside Save slides / Save stories | S | partly-in-main |
| B16 | v27 §6, v27 §10 | + Add photos beside "Let my assistant choose": opens the Photos folder, and new photos join the tray at the end with numbers that stay fixed | L | new |
| B17 | v27 §6, v27 §10 | Save just this slide / Save just slide N: one slide saved beside the newest set as "... - slide 0N updated.jpg", never over anything | L | new |
| B18 | v26 §5, v27 §6, v27 §10 | Instructions: parts/arrange.md's designer sections brought up to v27 (sets of stories, the new buttons, Crop, several at once, Save just this slide, Open folder, + Add photos, the ask lines) and SKILL.md rows | S | new |
| B19 | v27 §6 (the [hidden] CSS lesson) | The [hidden] rule: a check that every element the designer hides with the hidden attribute really disappears | S | already-in-main |
| B20 | v27 §10, v27 §12 | Screens and words check: the whole v26/v27 designer compared with her pages and screenshots 09 to 12, in a new tests/design_v27_check.py part of design_check.py | M | new |

### Build order

- B1: a rename, lands first and settles the stories test words
- B5: Redo, small and every later item's Undo/Redo tests lean on it
- B8: insert/remove slides in the model, the labels' + and × and the sel-slides group (B9, B10, B17 put buttons in it)
- B9: Where should it go? and the new adding line (uses B8's insert)
- B10: drag slides by the grip (uses B8's seam rule)
- B12: Show the whole photo (one action; B11's window reuses it)
- B11: Crop (the ZOOM change and the model maths before the window)
- B13: several photos at once (its own model operations; after B11 so the selection outline code is settled)
- B14: See a photo big (changes the tray click timing; after B13's tray work)
- B6: sets of stories (flips a server rule; before B7 so new templates land on multi-set stories)
- B7: the seven story templates and /design-queue
- B3: the ask box and the `ask` field (server and page)
- B4: design.py fill and the chat lines (needs B3's field)
- B15: Open folder always, and in the saved line
- B17: Save just this slide (the commit path; after B15 for its Open folder button)
- B16: + Add photos and fixed numbers (the largest cross-lane piece: reel.py sheet order; last so the lane is usable without it)
- B18: parts/arrange.md and SKILL.md once the behaviour is fixed
- B19 and B20: the checks run throughout; B20's file is started with B1 and grows with each item
- B2: the sticky-stage check, any time

### Decisions (the default the build takes)

- **B3:** Should the note be cleared once the assistant has filled the frames? Default: kept (hers keeps it); the assistant may be asked again.
- **B3:** The textarea's maxlength is 600 (hers); the server's cap matches.
- **B4:** With no empty frames the assistant does not add slides by itself (default); it says what to press. Open question for Nicole.
- **B4:** The assistant fills empty frames only; it never replaces a photo the photographer placed (hers: the same, "fills the empty photo frames").
- **B6:** The first set keeps its old name ("<shoot> stories"); new sets count from 2. Hers names from 1. Open for Nicole.
- **B6:** Duplicate is not offered in stories (hers).
- **B7:** The card's sub line for the queue story is "1 story · 0 photos" (ours), where hers prints "1 story · 0 photo". Open for Nicole.
- **B7:** Queue rows use the names as the photographer gave them (hers, Nov 13), no due dates.
- **B8:** A photo whose middle sits on the removed slide goes with it even if it stretches into the next slide (hers).
- **B9:** The row is not shown on a one-slide design (hers).
- **B10:** The drop line and the dimmed piece are her coral; our centred lines stay blue (Nov 11's "coral or plain" question stays open).
- **B11:** ZOOM max 25 (her effective limit through MIN .04). Pillow-drawn previews and PC-made 4320 copies are unaffected (zoom is a page-side crop).
- **B13:** The bar sits inside the sticky stage above the labels (her screenshot 11), not in the held room of the selected-thing bar.
- **B13:** No snapping during a group drag (hers).
- **B14:** The 230 ms single-click delay is hers and is kept (it changes how fast a click fills a frame).
- **B15:** The permanent button stays in our bottom bar (our Nov 6 layout), labelled "Open folder"; hers sits in the top row. Open for Nicole.
- **B16:** Only additions are taken up without a reload; a removal or a rename still blocks the page until Reload (safer, and what ours does today).
- **B16:** The contact sheets for the chat are re-made with the new numbering at the same time (kit.py sheet does both), so the assistant's sheets and the page agree.
- **B17:** No ARRANGED line to the chat for a single slide (hers tells nobody); the page says it. Open for Nicole.
- **B17:** A single slide never changes which set the kit page shows.

### Her faults we fix rather than copy

- **B3:** Her box saves on every keystroke with no debounce (save() each input); ours goes through the autosave queue's 0.7 s pause.
- **B4:** Hers has no command at all: her Claude edited the design file by hand. Ours is one command under the lock.
- **B5:** Hers: Undo and Redo call save() at once on every press; ours queues the save as every change does.
- **B7:** Her askQueueNames names question and q-count role are leftovers of the busier version she rejected; not built.
- **B7:** Hers fetches /home-data (a route any page could read); ours is the designer's own guarded route.
- **B8:** Her "Remove this slide" at one slide does nothing and says nothing; ours keeps its line.
- **B8:** Her stretch test uses a 20 px tolerance; ours uses the model's seam rule (the same 20 px) in one place.
- **B9:** Her bug (stale "slide 8" in New design) cannot happen here because the row is rebuilt from lastSlide on every open and the global hidden rule wins.
- **B10:** Her drag has no Escape to cancel; ours cancels through finish(true) like every other drag.
- **B11:** Her Done can leave a frame narrower than our 60 px minimum or off the strip when unlocked; ours clamps.
- **B11:** Her modal reads P[b.n].src (the small copy) first and swaps to the full one; ours the same, but never a path.
- **B12:** A very tall photo in a very wide short frame could give a frame under 60 px wide in hers; ours clamps.
- **B13:** Her group drag ignores the strip's edges (a group can be dragged off); ours clamps like a single move.
- **B13:** Her Same size with a text box as the reference sets photos to the text's width: ours takes the last clicked photo as the reference and skips a text reference.
- **B15:** Hers runs `open` (Mac only); ours goes through finder.open_folder on both computers.
- **B16:** Her /photos.json poll every 4 s lists the folder and runs sips on every call for any new file, from the page server's request thread; ours throttles and runs the numbering as a command.
- **B16:** Her first-look numbering is by name, later ones append: ours does the same but writes the list whole (never half a list).
- **B17:** Her i is unchecked (0, 99) and the file is written straight into the Carousel folder from the request thread with no staging, journal or hash; ours uses the commit path.
- **B17:** Her set number K is guessed from the folder's prefixes ("<shoot> carousel K"), which can pick the wrong set when a set was renamed by hand; ours names from the design's own last finished set.

### Touches other lanes

- S/posting_queue.py do_GET/do_POST: Lane B adds GET /design-queue and POST /design-photos to the design lists in do_GET (line ~1815) and do_POST (line ~2181); no other route. GET /open?kit=&sub= already allows Photos, Carousel, Stories, Singles, Covers; v27 §10 also wants sub=Reels for the reel page (reel lane adds "Reels" to open_kit_folder's tuple); Lane B changes only the words for a missing Carousel/Stories folder there.
- R/reel.py cmd_sheet (reel lane): keeping photo numbers when photos are added (v27 footage.py / server.py rule: old order first, new files after) needs an option on reel.py sheet (an --order list or reading the kit's old sheet.json); kit.py sheet passes it. Until that lands, B16 blocks the page with "photos changed, reload" as today and designs follow by file name (design._sync).
- S/kit.py: sheet() (B16) and nothing else; the kit page's Stories card already shows the newest saved set from any design, so sets of stories need no kit change; kit_cards_check.py gets a two-set case.
- S/edit_queue.py: read only (edit_queue.load / waiting) by /design-queue for the "My editing queue" story; the home lane's queue changes (Delivered, Archived, Take out of my queue, notes §11 and §13) decide what "waiting" means; Lane B takes waiting() as it stands.
- parts/arrange.md (B18) and SKILL.md's table: Lane B edits the designer sections and adds two rows; the reel lane edits the reel sections of the same file (v27 §2 to §4, "Edit my reel ... follow my direction", "Name my clips"). Merge by section.
- parts/where-things-live.md: one line each for `ask` and the single-slide journal entry.
- .github/workflows/check-pc.yml: design_v27_check.py joins the mac-page job (hidden Chrome) and pc_design.py's new cases the Windows job.
- v25 §10's "make my posts should only bring the photos in and open the post kit" and "the home page lists a shoot from the drop box only once Post kit.html exists" are the post-kit/home lanes, not the designer.
- v25 §8 (select several photos like Lightroom) is the reel page's photo order, not the designer; its shift/cmd-click behaviour should match B13's for the photographer's hands.
- words_page.py's Copy button code is reused by B3; no change there.
- this_computer.FILES_APP / APP_BAR give the Finder vs File Explorer words for B15, B16 and B17's lines; her lines name Finder, ours name whichever computer it is.

### Not to build

- Her askQueueNames names question (Full names / First names / Initials / No names) and the q-count role: leftovers of the busier "My editing queue" she rejected (notes §12).
- The test-only Home links and `?home=test` (v26 §6, v27 §14).
- crumbs.js / the path at the top (v27 §7): the kit pages' lane, not the designer; the designer's Back to the post kit stays until that lane lands the crumbs on every page.
- v27 §13's friendlier home page idea.
- Hers opens folders with `open` and reads /home-data from the home server; ours uses finder.open_folder and its own guarded route.
- No Duplicate button in stories (hers hides it).
- Nothing on the designer from v25 (its §8 is the reel page's order list).

### Open questions for Nicole

- Open folder: her permanent button sits in the top row beside Save just slide N; ours lives in the bar at the bottom of the window with Save slides (our Nov 6 layout). Which?
- Save just this slide: should the chat be told (an ARRANGED line) as it is for a whole set, or is the page's own line enough (hers)?
- "Pick my carousel photos" when the design has no empty frame: the assistant says so and names what to press (default), or should it add slides itself?
- Sets of stories: a shoot's first set keeps its old name "<shoot> stories" and new ones count from 2 (so no saved file name changes); hers names every set "<shoot> stories N" from 1. Fine?
- Should the note to the assistant be cleared once the frames are filled, or kept for the next ask (default: kept, as hers)?
- The queue story's card reads "1 story · 0 photos" (ours) where hers reads "0 photo"; and the queue rows use the shoot names exactly as typed in the editing queue. Fine?
- + Add photos: only added photos join without a reload; a photo removed or renamed still asks for a Reload (today's rule). Fine? And should the assistant's contact sheets be re-made at the same moment (default yes)?
- The drop line and the several-photos bar are her coral; the centred lines and selection stay blue. The Nov 11 "coral or plain" question still stands.

## Lane C: the talking reel

v27 §5 adds four things to the talking reel page: Fix a word (double-click a word or highlight several and press Fix the words; a small box, Enter saves, Esc closes; the whole map of fixes saved, the heard word kept as w0, Undo/Redo include fixes, same-number-of-words rule, dotted coral underline with a hover saying what was heard; captions, preview and CapCut use the fixed words; a word typed away shows no caption), an Open CapCut button in the bottom bar once a reel has been made plus the "It's in CapCut" box naming the project to click, "+ Add more photos" moved into the photo pop-up's footer (the grid rebuilds as photos arrive), and the path at the top (Lane D's crumbs). v27 §10 gives the two routes (/capcut/open, /talking/save takes fixes); §14 suggests a "working on it" line right after a video is added. v25 §2 (not yet in main) adds the "Your talking reels" bar: several talking reels per shoot, each fully separate, with new / switch / rename, refused while a video is being turned into a script. None of these is in main: no "fixes", "w0", "Fix the words", "Open CapCut" on this page, "Add more photos", or "versions" in S/talking_*.py, R/talking*.py or P/talking-reel.md (grep done). Our way underneath: fixes live in the record as an edit field (per video, cleared and kept in "replaced" when a script is made again; the words file is never rewritten), checked field by field; Open CapCut goes through capcut.open_capcut like the reel page (PC path, waiting reels); versions keep the live reel at the top of talking.json as hers; the page never sees a path. Her talking_core.py v27 differs from v24 by one line only (captions skip an empty word); her rule blocks are unchanged.

**Estimate:** About three days of focused work: C10 M (2 h), C1 M (3 h), C2 L (6 h), C3 S (1 h), C4 M (3 h), C7 S (0.5 h), C6 L (7 h), C5 M (3 h, plus waiting on Lane B's numbering), C8 S (0.2 h), C9 S (1 h); then the whole-build rerun of the talking tests under the guard (talking_page_check whole, rec, engine, capcut, multi, menus, snap, pc_talking, skill_text, capcut_even, both Pythons: about 2 h).

### Items

| # | Pack | What | Size | In main today |
|---|---|---|---|---|
| C1 | v27 §5, §10 (/talking/save takes fixes), her talking_core.py (captions skip a word typed away) | Fix a word: the record, the save check and the engine | M | new |
| C2 | v27 §5 (Fix a word on the page), screenshots 20 and 21 | Fix a word: the page (double-click, Fix the words, the small box, Enter and Esc, the underline, Undo/Redo) | L | new |
| C3 | v27 §5 (the captions, the preview and CapCut use the fixed words) | The fixed words reach the preview's captions and the CapCut project | S | new |
| C4 | v27 §5 (Open CapCut) and §10 (POST /capcut/open), screenshot 22 | Open CapCut in the bottom bar, and "It's in CapCut" naming the project | M | new |
| C5 | v27 §5 (+ Add more photos in the photo pop-up's footer), her page's Add photos block (Nov 14/16) | + Add more photos in the photo pop-up's footer, with the grid rebuilding as photos arrive | M | new |
| C6 | v25 §2 (several reels from one shoot: the talking reel page has the same bar; the talking record; /talking/version; refused while a video is being turned into a script), screenshot 3 of v25 | Your talking reels: several talking reels per shoot (new, switch, rename) | L | new |
| C7 | v27 §14 ("The talking reel could say 'working on it' right after a video is added") | "Working on it" at once after a video is added (a sensible default) | S | partly-in-main |
| C8 | v27 §5 (the path at the top) and §7 (crumbs.js) | Where Lane D's crumbs go on the talking page | S | new |
| C9 | v27 §5, v25 §2 (the assistant's side), v27 §10 | parts/talking-reel.md and the assistant's words for fixes, several reels and Open CapCut | S | new |
| C10 | v27 (talking-reel.html, server.py, talking_core.py), v25 (talking-reel.html, server.py) | Her words compared both ways against v27 (and v25) instead of v24 | M | changed-since-v24 |

### Build order

- C10 first (point the words test at v27, so every later item is checked against the right files and her unbuilt lines are listed from day one)
- C1 (the record, the save check, the engine: everything else on fixes stands on _join laying fixes over the words)
- C2 (the page's Fix a word, on top of C1)
- C3 (proof that the fixed words reach the preview and CapCut: tests only, cheap once C1 is in)
- C4 (Open CapCut and the project in the result box: independent of fixes, touches posting_queue's route list once)
- C7 (the one-line 'working on it' default)
- C6 (several talking reels: the biggest change to the record; after fixes are in so the stash/restore covers the fixes field too)
- C5 last of the page items (waits on Lane B's 'new photos keep their numbers' mechanism; the button and words can go in earlier, the grid-rebuild check only once Lane B lands)
- C8 (a note for Lane D; nothing to build here)
- C9 (the part and the assistant's lines, once the behaviour is final)

### Decisions (the default the build takes)

- **C1:** Where fixes live: in the record, not the words file (hers rewrites the words). Default: record, as an edit field.
- **C1:** A fix equal to the heard word: dropped on save (hers does the same on the page and the server).
- **C1:** A value longer than 80 characters: the whole save refused (hers truncates silently). Default: refuse, as every other field.
- **C1:** Does a fix count as 'their own work' for cut --replace / place --replace? Default: no, fixes never touch cuts or stretches; status mentions the count only.
- **C1:** Does `show` mark a fixed word for the assistant? Default: no, the fixed word is simply the word (rule 3: the assistant never touches a caption word); status says how many were fixed.
- **C2:** Where the box sits when the word is near the top of the window: hers puts it at top 8 px; ours the same (her placement, both axes).
- **C2:** A double-click while words are highlighted: the browser selects the word anyway; openFix clears the selection, as hers.
- **C2:** Escape in the box: closes the box only (hers also reaches the timeline's Escape). Default: stop there.
- **C2:** A fix pressed while a save is on its way: queued through T.save's chain as every save.
- **C2:** Touch screens have no hover, so the heard word has no way to show there: left as hers; noted for Nicole.
- **C3:** The caption's time stays the heard word's start and end (hers): a fix never moves timing.
- **C4:** Which words when CapCut was already open: her sentence (newest project at the top) is kept; the maker's line before it (MADE_OPEN) already says to quit and reopen if it isn't there.
- **C4:** The bar's button after a page reload: shown when the record has any made entry (rec.made from state), as hers (REC.made.length).
- **C4:** Nothing made yet: the route refuses with her 'I couldn't open CapCut.' (hers would open CapCut anyway; the button is hidden then, so only a crafted request reaches it).
- **C5:** Polling: not a second timer; the page's existing look with the folder mark (ours), looking only while the pop-up is open.
- **C5:** The '+ Add photos' at the top of her v25/v26 page was never on ours (ours came from v24), so there is nothing to take out.
- **C5:** A photo dragged in while a stretch's pop-up is open: joins the grid at the end with its new number; nothing already picked moves (pickFresh keeps what is picked by number).
- **C6:** Project name with several reels: "<shoot> talking reel", "… 2" counted across the shoot (as today), not the reel's name. Open question for Nicole.
- **C6:** A duplicate reel name on rename: allowed, as hers (the id is what is switched; the drop-down shows both). Open question.
- **C6:** Switch refused while a make is at work (ours; hers only refuses during transcription).
- **C6:** The page reloads on new/switch as hers (simplest: every list, Undo and the video start fresh); the state answer alone could do it, not done.
- **C6:** A reel with no video and nothing in it left behind: kept, as hers; nothing is deleted.
- **C7:** Which moment she meant: the press of Edit my video (default) or the file landing in the folder (already covered by the 'coming' line). Open question.
- **C8:** The back link stays in the markup, hidden as hers, until Lane D's crumbs land (then hidden by Lane D's rule).
- **C9:** No new pasted line for 'which talking reel' (hers has none): the open reel is the one; the assistant asks only when they name another.
- **C10:** v25's talking-reel.html need not be read separately: v27's page carries the reels bar unchanged (the v25->v27 diff shows it untouched).

### Her faults we fix rather than copy

- **C1:** Her /talking/save accepts any number of keys, str()s a non-string value (a list becomes "['a']"), and silently ignores keys beyond the word count or non-digit keys: ours refuses the whole save on any bad entry.
- **C1:** Her fixes are lost without a word when the video is turned into words again (the words list is replaced): ours keeps them in "replaced" and starts the edit afresh, as every edit field.
- **C1:** Her fixes are not kept per video (her v24 record has no per-video edits): ours moves them with "earlier" when they change video and brings them back.
- **C2:** Her global keydown (her page line 951) does not stop Space/Delete/Backspace typed in the fix box from reaching the video and the timeline: ours guards them while the box is open.
- **C2:** Her Escape in the box does not stop propagation: with several clips picked, one Escape closes the box AND lets go of the clips. Ours closes the box only.
- **C2:** Her fix box is placed once and never moved on scroll (position:fixed): ours re-places it as the bar is, or closes it when the words scroll away.
- **C2:** Her mousedown-anywhere-closes handler fires for a press on the highlight bar too; harmless, but ours ignores presses inside #fixBox and the bar.
- **C4:** Her /capcut/open never adds a reel waiting for CapCut's list and has no PC path: ours goes through capcut.open_capcut as the reel page does.
- **C4:** Her 'Your newest project is at the top of the list' is said even when CapCut was already open and the project is not listed yet: kept as her words, but the maker's own line above it tells the truth about that case.
- **C5:** Her page polls /photos.json every 4 s for the life of the page, pop-up open or not: ours looks only while the pop-up is open, through the look it already makes.
- **C5:** Her 'Could not open the folder. Is the photo drive plugged in?' is said for any failure, a missing CapCut-style path included; ours says it only when the folder truly isn't there (posting_queue's own words otherwise).
- **C6:** Her verOp on new/switch does not wait for a save still on its way: a Cut pressed just before Start a new reel could land after the stash and go onto the wrong reel. Ours flushes the save chain first, and the server refuses a page save whose base is older (the counter).
- **C6:** Her ver_op is not under any lock across programs (her one-process server): ours runs inside change() under the record's lock.
- **C6:** Her new-reel default name search starts at len(vs)+1 and can produce 'Talking reel 3' after a rename took that name: ours picks the first free number the same way but also skips names taken; a reel the photographer deleted cannot exist (nothing is deleted) so numbers never repeat.

### Touches other lanes

- S/posting_queue.py do_POST, the list at ~line 2199 ('/talking-open', '/talking-start', '/talking-save', '/talking-make'): Lane C adds '/talking-capcut' and '/talking-version'. Lane B will add its own ('/reel-version', the preview, the song, moments/describe, capcut/open for the reel page) to the neighbouring reel_page list: one of us edits that block last, or both add to a tuple per page to avoid a clash. No change to do_GET for this lane (GET /open?kit=&sub=Photos already exists and is reused by C5).
- Lane B (the reel page, v27 §2 and §3): 'Photos keep their numbers when more are added: new ones go at the end' must be built in kit.py sheet / reel.py sheet (today the sheet is re-made from the folder's sorted names, which renumbers) and something must re-make the numbered list when files land in the Photos folder (hers: prepare() on every /photos.json). Lane C's '+ Add more photos' (C5) relies on both; the talking page then needs no new route (its state's mark already moves with the list). Contract: the numbered list keeps every existing n and appends new photos with the next numbers; the page learns of it through arrange.sheet_stamp / talking_rec.folder_mark.
- Lane B and Lane C both build a 'Your reels' / 'Your talking reels' bar (v25 §2): same CSS (.reels, hers), same JS shape (showVers, verOp, the rename box), separate records (reel-page.json vs talking.json) and routes (/reel-version vs /talking-version). Proposal: one JS module and one CSS block written once (S/versions_js.py; whichever lane is first writes it, the other imports), each page passing its own route and words. Her ver_op shape {versions: [{id, name, data}], current} is the same for both; keep the id form v<n> and the 40-character name cap identical.
- Lane D (crumbs, v27 §7): the talking page's bar is in S/talking_page.py page_html (<div class='bar'> with a#back and brand.bar()); her call for this page is [[post kit, kit page], ['Reels', reel chooser], ['Talking to camera', none]]. The existing test (tests/talking_page_script.py ~661) counts one .bar; a nav inside it is fine.
- R/capcut.py open_capcut / posting_queue.open_capcut are shared with the reel page and the kit page: Lane C only calls them with the talking page's words (ok_words, button) as reel_page.open_capcut_for_page does; no change to capcut.py itself. If Lane B changes posting_queue.open_capcut's signature for v27's reel-page Open CapCut, keep ok_words and button.
- P/talking-reel.md is Lane C's; tests/skill_text_check.py check_talking also reads the core's SKILL.md table: no new row (no new pasted line), so the core's table is untouched by this lane.
- Her talking_core.py v27 differs from v24 by the one captions line; talking.py's RULES / PHOTO_RULES are unchanged, so tests/talking_rec_check.py's rule compare can stay on v24 or move to v27 (identical).
- The design preview, kit cards and the posting queue are untouched by this lane; a talking reel still is not a queue piece and not on the Reel card (owners' question 9 stands; v25/v27 do not change it).

### Not to build

- v27 §13: the friendlier home page (Nicole: not yet; she wants to brainstorm).
- v27 §14's other two: the chat reel maker's paces (R/reel.py, Lane B) and the test-only Home links (v26 §6, to drop, not build).
- v26: nothing touches the talking reel ('Unchanged since v25: the reel page, talking reel'); the v26 notes don't mention it.
- v25 §3 (photo note), §4 (Trim), §5 (songs), §8 (batch select), §6/§7 (post kit reel previews, queue per reel): the reel page and the kit, Lanes A/B.
- The 'bring in photos from elsewhere on the computer' button (dropped Nov 12, branch add-photos-set-aside): NOT the same as v27's '+ Add more photos', which opens the shoot's own Photos folder; build the latter only.
- Anything on zooms (parked Nov 13: 'disregard zoom stuff for now'); v27 changes nothing there.
- A new pasted line naming the talking reel ('Cut my talking reel for <shoot>, <reel>'): her v27 page still writes the three lines without a reel name.
- Whisper, another language, a PC transcriber: named gaps, unchanged.
- Her two-sentence clip descriptions, Top/Middle/Bottom for words, the greyed 'posted' list: things she tried and took out elsewhere; nothing of the kind on this page.

### Open questions for Nicole

- A word typed away (fewer words typed than highlighted) still plays in the video and only loses its caption; the toast says 'To take a word out, use Cut.' Is that what you want, or should the box refuse a count that doesn't match?
- The hover line 'You fixed this. It was heard as …' never shows on a touch screen (no hover). Leave it, or add a tap?
- Several talking reels: should the CapCut project be named after the reel ('Aurora Family talking reel · Beach take') or stay '<shoot> talking reel', '… 2' as now (your server would clash on the name)?
- Rename: two talking reels may be given the same name (yours allows it). Refuse a taken name, or allow it?
- Switching reels is refused while a reel is being made in CapCut as well as while a video is being turned into a script (yours refuses only the second). OK?
- 'Working on it': do you mean the moment after pressing Edit my video (built: the status line says Working on it… at once), or the moment a file lands in the Talking folder (today the row names it as 'still being copied' until it is whole)?
- Open CapCut on a PC: your line names 'this Mac' ('CapCut doesn't seem to be on this Mac. It's free from capcut.com.'); on a PC ours says 'this PC' and 'the Start menu'. OK?
- May the assistant mention a word that looks misheard ('did you say Aurora?') and tell them how to fix it, or never (rule 3: the assistant never touches a caption word)? Built: never fixes, tells them how when asked.
- A fix is not counted as 'their own work' for the assistant's cut --replace / place --replace questions (fixes don't touch cuts or stretches). OK?

## Lane D: the post kit, the words page, the posting queue, the path at the top

Nothing of v25 to v27 in this lane is in main yet (grep: no reel_name, reel-label, unposted, crumbs, nor any of her new lines; only posted_at exists, written by set_status). The packs ask for: (1) the posting queue gives each reel of a shoot its own spot (reel-label, -reel-vN pieces, "<shoot> reel · <reel name>"); (2) the reel cover picker shows "From your reel, in the order it plays" numbered, then "+ Use a different photo"; (3) Posted on the post itself: a Not posted / Posted switch in the panel, the posted piece in the grid as a plain feed post with no date, switching back = unposted (clears posted_at), state() adds posted; (4) the post kit: captions optional with her on-page question box, and with more than one reel a preview per reel, step 3 listing each reel, and "Which reel goes in your queue?"; (5) the Reels card's v27 wording and CTAs; (6) a path at the top of every post kit page (Home › <shoot> post kit › Reels › B-roll; Captions; Carousel; Stories), old Back pills hidden; (7) the carousel picker's sticky carousel (already in main); (8) the parts (post-kit.md, posting-queue.md, words.md) and SKILL.md rows; (9) the v26 test-home links are test-only and are not built. Her v27 section 11 chat lines do not appear on the post kit or words page (checked), so nothing there for this lane. Two existing tests (kit_cards_check, kit_steps_check) compare KIT_WORDS against her newest post-kit.html and already fail against v27 (need_both, need_caption, reel_sub), so the word lists and tests move together. Depends on Lane A's reel record gaining versions (contract below).

**Estimate:** About three days of focused work: D9 S, D6 M, D1 M, D3 M, D4 M, D2 M, D5 L, D8 M, D7 S (a hand check). D2 and D5 wait on Lane A's reels_of / order_for_version and can be built against a stub record first.

### Items

| # | Pack | What | Size | In main today |
|---|---|---|---|---|
| D1 | v25 §7 (each reel has its own spot), v25 plugin-changes/posting_queue-since-v24.diff (label_reel, reel-label, piece_name, pub), v27 §8 (names in the panel) | Posting queue: one spot per reel (reel-label, -reel-vN pieces, reel_name everywhere a piece is named) | M | new |
| D2 | v25 §7 (the reel cover picker), v25 plugin-changes diff (the strip, .sub/.more/.others CSS) | Posting queue panel: the reel cover picker in reel order, numbered, then "+ Use a different photo" | M | new |
| D3 | v27 §8 "Posted, on the post itself", v27 plugin-changes/posting_queue-since-v26.diff, screenshots 23 to 25 | Posting queue: the Not posted / Posted switch on the post, the posted piece in the grid as a feed post, unposted | M | new |
| D4 | v25 §6 "Captions are optional", her v25/v27 pages/post-kit.html askBox/askNoCaption, screenshot 01 (the Carousel card's step 3 line) | Post kit: Add to my queue works once the piece is made, caption or not, with her on-page question | M | new |
| D5 | v25 §6 "With more than one reel" (kit_summary.reels, queue_state.reels), v27 §2 (the Reels card's wording), v27 §7, screenshot 01 and v25 screenshot 2 | Post kit: the Reels card (v27 wording), a preview per reel, step 3 per reel, "Which reel goes in your queue?" | L | new |
| D6 | v27 §7 (crumbs.js), pages/crumbs.js, her post-kit.html / words.html / reel-maker.html / talking-reel.html / carousel-designer.html bar lines, screenshots 01 and 07 | The path at the top of every post kit page (crumbs), built in look.py and used by the kit page and the words page | M | new |
| D7 | v27 §7 ("The carousel picker keeps the carousel at the top while the photos scroll"), her carousel-picker.html line 30 | Carousel picker: the carousel stays at the top while the photos scroll | S | already-in-main |
| D8 | v25 §6, §7, §10 ("make my posts" should only bring the photos in and open the post kit); v27 §2, §7, §8; v27 §14 | The instructions: post-kit.md, posting-queue.md, words.md and SKILL.md rows for everything above | M | new |
| D9 | tests (ours), prompted by her v25 and v27 post-kit.html now sitting in reference-private | The word checks against her newest page are red on main already; move them with the words | S | changed-since-v24 |

### Build order

- D9 first: the existing word checks are already red against her v27 page; fixing the glob and the retired-lines list makes every later run meaningful
- D6 (crumbs) next: small, self-contained, and the other lanes need look.crumbs() and the trail contract early so their pages can call it
- D1 (one spot per reel in the queue) before anything on the kit: D2, D3's pub() and D5 all read version/reel_name from it; it can be built and tested against a hand-made reel record while Lane A finishes versions
- D3 (Posted switch, unposted) next: independent of versions, all in posting_queue.py, and Nicole hit it on real shoots ("there's no refreshed feed there at all")
- D4 (captions optional) before D5: D5's which-reel flow ends in D4's question box
- D2 (the cover picker) once Lane A's order_for_version exists; its JS is independent of D5
- D5 (the Reels card, a preview per reel, which reel) last of the code: it needs Lane A's reels_of and D1, D4
- D8 (the parts) as each piece lands, D7 only a hand check

### Decisions (the default the build takes)

- **D1:** A reel's words: one words record per piece as hers (words.py unchanged since v24), so every reel of a shoot shares the reel caption and hooks; the panel's Copy caption reads the same words for v1 and v2. Default: as hers; asked below.
- **D1:** The reminder title with two reels: default "Post your Katie Austin Maternity reel · Fun Maternity today" (the name the page shows); hers would make two identical titles.
- **D1:** `find()` from the chat: a shoot word alone with two reels stops with both names ("could mean more than one: ... Say which."), as main does for twins.
- **D2:** The separator "More from the shoot" goes (hers replaced it with the two sections); it moves to the test's list of retired lines
- **D3:** Reminder on unposted: remind_on is left as it was, so a reminder that was on comes back with the post's new date (hers only pops posted_at; ours is the same, stated)
- **D3:** A posted piece's panel offers no photo, words or reminder (hers): the switch and Done only
- **D3:** Keyboard: posted tiles get tabIndex and Enter/Space like upcoming ones (ours; hers are mouse-only)
- **D4:** The words page's own queue step: left as hers (still asks for a caption there), so the kit page is where a caption-less add happens; CLAUDE.md already lists "whether the words page's queue step should also unlock" as theirs to settle
- **D4:** The chat's `posting_queue.py ready` keeps its instruction to look for a caption first and offer the words (posting-queue.md), since the page now allows it: the line changes from "don't mark it ready silently" to "say it has no caption yet, then do it if they say so"
- **D5:** The CTA says "Create another reel" once ANY reel is made (hers: kit.reel = the newest project)
- **D5:** "Open in CapCut" under several reels opens the newest project (hers); a per-reel Open is not built (not in her page)
- **D5:** The per-reel strip shows photos only when that reel has an order; "No photos picked yet." otherwise (hers)
- **D5:** The Reels card still opens /reel.html?kit= (reel_door unchanged); the chooser behind it is Lane A's
- **D6:** The shoot's short name in the crumb is the kit's name without its date (her short()), the same rule the kit title uses
- **D6:** On the saved copy (body:not(.live)) the crumb links are drawn as plain text, like the hidden homelink
- **D6:** The posting queue page keeps "Back to home" (hers)
- **D7:** Left as is unless the hand check shows the panel taller than her 48vh
- **D8:** v25 §10's "make my posts" change is written as instruction only (bring the photos in, show the kit; the assistant's picks and build still happen since the kit page's Reel card reads them); the full re-scope of the chat flow is Dustin's call
- **D8:** v27 §8's make-posts screen text belongs to the home lane; only its "What's a post kit?" paragraph is reused here as the chat's answer

### Her faults we fix rather than copy

- **D1:** label_reel finds the base piece by "kit:" + slug(kit_dir.name) + "-reel", ignoring kit_sid's collision-proof ids: a kit whose short name was taken gets "STOP: add the kit first."
- **D1:** label_reel copies the base piece's thumb, so reel 2 shows reel 1's grid photo until a cover is picked
- **D1:** label_reel calls sys.exit inside a library function (the page server would die on it); the name is cut to 40 characters silently
- **D1:** piece_name() uses "(name)" on the CLI while the page uses " · name": two forms for one thing
- **D1:** find() never looks at reel_name, so the chat cannot name the second reel
- **D2:** Her strip is rebuilt with innerHTML from server strings (main sets every name as text; keep ours)
- **D2:** Her aria-expanded is set as a boolean-ish string from !o.hidden; set "true"/"false" explicitly
- **D3:** Her JS filters S.posted by read_at a second time on the page (harmless, dropped: the server decides)
- **D3:** Her posted tile has no keyboard access and no focus ring
- **D3:** Her openPick builds the switch with innerHTML strings; ours with mkel/textContent
- **D4:** Her askBox builds buttons with innerHTML from labels; ours from textContent
- **D4:** Her dialog has no focus trap and Escape works only while open (fine) but Tab leaves it; add aria and keep focus inside
- **D5:** Her reelsQueueBox shows "✓ Added to my queue" disabled when no reel is left to add even if none was ever made and none is queued (reads oddly: ours shows the plain disabled "Add to my queue" then, as her own else-branch half does)
- **D5:** Her page decides "made" for v1 from kit_reel(...).project too; ours from reels_of only, one rule
- **D6:** Hard-coded http://127.0.0.1:8790/home (breaks the moment the port differs; ours is a relative path)
- **D6:** Hard-coded hover colour #D4643F and the font name 'DM Sans' (ours: the look's variables)
- **D6:** The test-home localStorage switch (v26 §6: test-only, never built)
- **D6:** Built in the browser from the URL's ?shoot=, so a page with no shoot shows a bare "Post kit" crumb with a dead link

### Touches other lanes

- Lane A (reel page / reel record): the contract Lane D builds against: <kit>/.kit/reel-page.json gains versions [{id, name, data}] and current (v25 §2), made[] entries carry version (old ones count as v1); two read-only helpers in S/reel_page.py: reels_of(kit, rows, rec_kit) -> [{id, name, made, project, order:[n...]}] (her server.py reels_of) and order_for_version(kit, rows, rec_kit, version) (her reel_order_of); until versions land both return the one reel from order_for_kit_page/newest_project. The reel page's make must pass its version to the queue: Lane D adds `posting_queue.py made <piece> --version vN` (labels first); today reel.py line 674 marks the base -reel piece.
- Lane A (reel page): v27 §2's "Add this reel to my posting queue" button on the reel page posts to Lane D's POST /words-queue {kit, piece:"reel", version} (same-page guard) and reads the reels map from /words-state; it asks the rhythm through /words-rhythm as the kit does. No new route is needed.
- Lane A / B / C (reel page, talking page, designer): call look.crumbs(look.kit_trail(kit) + ...) in their bars with her trails: reel page [('Reels', '/reel.html?kit=')] + [('Behind the scenes'|'Just photos'|'B-roll', None)] (the chooser with no kind: [('Reels', None)]); talking page [('Reels', '/reel.html?kit='), ('Talking to camera', None)]; designer [('Carousel'|'Stories', None)]; hide the old Back pill (display:none, kept). Lane D owns look.py and the CSS; nobody else edits look.BASE.
- Lane A (carousel picker, S/arrange_page.py): D7 is already sticky in main; Lane D touches nothing in arrange_page.py.
- Home lane (S/home.py, S/posts.py): v25 §10 says the home page should list every shoot in the content folder, not only those with .kit/Post kit.html (today home.gather filters posts.kits on k.get("kit"), which is exactly that file's existence). v27 §8's make-posts screen wording and v26's home/backups/edit_queue changes are that lane's. The v26 test-only ?home=test scripts in posting_queue.py, report_page.py and edit_queue.py are never built (v26 §6, v27 §14).
- S/posting_queue.py do_POST: Lane D adds only the action "unposted" inside the existing /posting branch, no new path; do_GET unchanged (/posting/panel answers as now; a posted piece's panel needs no fetch). New CLI commands: reel-label, unposted, made --version. Other lanes should not touch these functions: state(), set_status(), panel_choices(), add_for_kit(), kit_role(), kit_piece(), the page JS.
- S/words_page.py: /words-queue takes version; queue_state and state() return reels; the caption gate moves out of add_to_queue (made only). Lane A's reel page relies on this.
- S/reminders.py: words_piece() and title() learn reel pieces with a version/name (Lane D); nothing else in reminders changes.

### Not to build

- v26 §6 / v27 §14: the test-home Home links (?home=test, sessionStorage assistantHome, localStorage assistantHomeTest) in posting_queue.py, report_page.py, edit_queue.py and post-kit.html; and crumbs.js's home-test.html branch
- v25 plugin-changes: her label_reel as written (base lookup by slug, copied thumb, sys.exit); rebuilt our way in D1
- crumbs.js itself (a browser script with an absolute 8790 address and hard-coded colours): the path is built on the server by look.crumbs()
- A greyed-out "posted" list under Ready to post (v27 §8: tried and taken out)
- A "posted on <day>" label on the posted tile (Nicole: "that's not even true")
- Per-reel words pages or per-reel Open in CapCut buttons (not in her pages)
- v27 §13's friendlier home page (an idea, not yet); v27 §14's chat reel maker paces and the talking reel's "working on it" line (other lanes)
- v25 §10's pacing note (Lane A's timing) and the home page listing (home lane): noted under cross_lane_notes only

### Open questions for Nicole

- Several reels, one set of words: your words page and words.py are unchanged since v24, so every reel of a shoot shares the reel's caption and ten hooks, and the queue's Copy caption gives the same caption for Fun Maternity and White Backdrop. Is that what you want, or should each reel have its own words page tab?
- The words page's own "Add it to your posting queue" step still waits for a caption (your words.html), while the post kit now adds without one and asks. Keep the two different, or let the words page ask the same question?
- Two reels of one shoot get two calendar reminders with the same title ("Post your Katie Austin Maternity reel today") in your build. We add the reel name to the title ("... reel · Fun Maternity today"). Right?
- When a post is switched back to Not posted and it had a reminder, we bring the reminder back with its new date. Or should switching back leave the reminder off?
- The posted post stays in the grid with no date until the grid is read again (your rule). Should the panel of a posted post also offer Copy caption, or only the switch, as yours?
- "Create another reel" shows once any reel of the shoot is made (your kit.reel rule). Fine, or only once every reel listed is made?
- v25 §10: "make my posts" should only bring the photos in and open the post kit. Today the assistant still picks the reel and builds the slides, singles and stories as part of it (the words never). Drop those too, or keep the picks so the Reel card has an order waiting?
- The path at the top says "Hannah post kit" (the folder name without its date). Keep that, or the kit's own name as the kit page's title shows it?

## Lane E: the home base and its screens, the editing queue, the backup notes

Nicole's v26 turns the home page into "your home base": a two-paragraph welcome, Today, four numbered steps in the order of the work (Back up a card, My editing queue, Make posts from a shoot, My posting queue) and a small Open my Assistant folder card, with nothing else on it (the recent-shoots grid goes). Back up a card and Make posts from a shoot become screens of their own: a plain explanation, a light steps box with the paste line and Copy, then every backup (10 most recent, Show older by month, search, card-safe/second-copy pills, per-shoot state, Open this folder + See the report, unplugged and moved folders said in words, cards of one shoot grouped) and every post kit (20 most recent, Show older, search, Archive / Bring it back, never deleted). v27 §8 adds the "What's a post kit?" box and a third step to Make posts. The editing queue gets Mark as delivered, Take out of my queue, Uploaded shoots, Delivered (n) and Archived (n) folds with "Are you sure?", one Find a shoot across everything, "your assistant" never "Claude", and new actions unqueue/store/unstore. Her backup notes ask for the folder-name question reworded (people read it as "name this folder"), the report to explain two folders, the sneak peeks and "Does everything look right?", a per-shoot Open this folder, and the end-of-backup handoff reworded; and the drop box to stop keeping a second full copy after a picker bring. Nothing of this is in main yet (no delivered/stored/unqueue/kit-archive/home-data anywhere). Our side: home.py's /home rebuilt, two new page modules on the posting server with a /home-data JSON route and a /kit-archive POST, edit_queue.py's states and page, posts.py's drop box, first_look.py/report_page.py/serve_report.py for the report lines, six parts, and the tests. v27 §13 (friendlier "Good morning" home) is an idea only, noted, not built.

**Estimate:** About three and a half to four days of focused work: E5 L, E3 L, E1/E2/E4/E7/E8 M each, E6/E9 S, plus the test sweep and the two docs.

### Items

| # | Pack | What | Size | In main today |
|---|---|---|---|---|
| E1 | v26 §3 Home, notes §3 and §7, v27 §13 (note only) | The home page becomes the home base: her words, four steps in the order of the work, nothing else on it | M | changed-since-v24 |
| E2 | v26 §3 the server (home-data, kit-archive), notes §6, §9 | GET /home-data and POST /kit-archive on the posting server, read in-process, no path to the page | M | new |
| E3 | v26 §3 Back up a card (backups.html), notes §4 and §8, v26 §7 multi-card | Back up a card: its own screen with the explanation, the light steps box and every backup underneath | L | new |
| E4 | v26 §3 Make posts (make-posts.html), v27 §8 Make posts from a shoot (wins over v26), notes §5, §6, §9 | Make posts from a shoot: its own screen with What's a post kit, three steps, and every post kit with Archive | M | partly-in-main |
| E5 | v26 §4 the editing queue, notes §11 and §13, v26 §6 (the test-only bit on this page: drop) | The editing queue: Mark as delivered, Take out of my queue, Uploaded shoots, Delivered and Archived, one Find a shoot, 'your assistant' everywhere | L | new |
| E6 | notes §1, v26 §7 'First backup, the naming question' (a design ask on the backup flow: parts, not a page) | The first-time folder-name question, reworded so nobody reads it as 'name this folder', and the intro says what is about to happen | S | new |
| E7 | notes §2, v26 §7 'The report's words' (design asks on the report page and the backup's closing lines; shared with the backup lane) | The report after a backup: why two folders, 'Does everything look right?', Open this folder per shoot, the sneak peeks explained, and the handoff reworded | M | new |
| E8 | notes §10, v26 §7 'The drop box keeps a second full copy' | The drop box stops keeping a second full copy when the photos came in through the folder picker | M | new |
| E9 | v26 §3, §4 and §6 (test-only bits), notes §7 | The parts, the Back to home links and the test harness follow the new home | S | new |

### Build order

- E5 the editing queue first: its states (delivered, stored, unqueue) are what the Back up a card screen's per-shoot pills and the queue story template read, and the chat commands go with it
- E2 /home-data and /kit-archive next: the one data contract the three screens and the designer's 'My editing queue' story share
- E3 the Back up a card screen (the biggest page: grouping, pills, unplugged and moved folders)
- E4 the Make posts screen (v27 wording, archive)
- E1 the home page itself, last of the pages, so its four cards have screens to link to and pc_smoke's assertions move in one step
- E7 the report lines and the handoff (first_look, serve_report open?shoot, parts/backup.md)
- E6 the first-backup question (parts only)
- E8 the drop box clearing (posts.py), after Dustin's answer on the Trash or with set-aside as the only mode until then
- E9 parts, workflow, build doc and the note for Nicole, with the full test sweep

### Decisions (the default the build takes)

- **E1:** Her 'Welcome to your home base.' every time, instead of our Welcome back / Hi, I'm Sherman switch: her words win; the given name still shows in the top bar (brand.bar).
- **E1:** Her Make posts blurb says 'single photos' though the kit has no single-photo card since Nov 11: kept as hers, listed for Dustin and Nicole.
- **E1:** Her Today 'A card is in' line gets her Back it up button linking to the Back up a card screen (ours said 'Ready when you are').
- **E1:** Clicks on the two screen cards are still recorded in journey.json so home.py pending works as before.
- **E2:** Where the archive flag lives: ~/.studio/kit-archive.json (her shape plus a time), not kit.json, so Archived can sort newest-first and an unplugged drive still lists; open to Dustin.
- **E2:** A kit on an unplugged drive is not listed at all (posts.home() is None): the screen says the drive's name to plug in (E5).
- **E3:** Her STATUS word for a finished shoot on this screen is 'Edited' though the queue now says Delivered: kept as hers, listed for Nicole.
- **E3:** 'Just for you' for a backed-up shoot never queued: kept (her word), even though the queue page now calls that section Uploaded shoots.
- **E3:** Older backups with no shoot.json group by her ', card N' name pattern (the way the pre-shoot_report instructions named them), so Nicole's existing two-card test shows as one backup.
- **E4:** v27's header, step-2 note and third step replace v26's ('Your shoot's post kit opens, and it shows up below. Nothing is posted; you post it when you're ready.' is out).
- **E4:** Her 'single photos' stays in the header line (her words), listed for Nicole since a single post is a one-slide carousel.
- **E4:** A kit's date for 'Show older' months comes from kit.json's date, falling back to the folder's leading date as hers does.
- **E5:** 'Make posts from this shoot' opens the Make posts screen (as hers) rather than the shoot's kit directly; a direct jump when a kit with that name exists is a one-line extra, left for Dustin.
- **E5:** Section 6's ?home=test script on this page's Home link: not built.
- **E5:** Chat command names: unqueue / archive / unarchive (page words stay hers).
- **E6:** Which option is recommended: Nicole suggests 'the name of the shoot, then the date' (our --offered 2); Dustin's Nov 5 pick was date-first 'keeps them in order'. Default built: name-then-date recommended as Nicole says, both offered; open question.
- **E7:** Her sneak-peek sentence plus our one-line pointer to the buttons (Pick again / Show me more need 'say what you'd rather see'); open to Nicole whether to drop ours.
- **E7:** The bottom 'Where your photos are' card is kept beside the new per-shoot buttons.
- **E7:** The come-back line names both ways back (the chat line and the Make posts card), since the kit is made 'on request or at I'm done' (Dustin, Oct 30).
- **E8:** Trash versus 'nothing ever deleted' (Dustin's standing rule): built as Nicole asks, behind a re-check, with set-aside as the fallback; this is the first time the Assistant moves anything of the photographer's to the Trash, so it is open question #1 for Dustin.
- **E8:** Not built: copying straight from the chosen folder into Your Content (would change look/sort's contract that the drop box is the input).
- **E9:** Pages say 'your assistant' (Nicole); the chat keeps 'Claude' where rule 8 wants it.

### Her faults we fix rather than copy

- **E1:** Her page loads Google Fonts and her CSS from the internet: ours uses look.py's own DM Sans and inline CSS.
- **E1:** Her cards link to a second server (8799) and pass ?home=test: ours are same-server links, no flag.
- **E1:** Her failure line names 'the Assistant's records'; on a page ours says the same in brand words, never a path.
- **E2:** home_data.py re-reads every manifest.json on every call behind a 20 s cache and a 60 s subprocess timeout: ours reads in-process with per-part fail-soft and no cache (manifests are small; the page polls /home-state, not /home-data).
- **E2:** Her /kit-archive takes any JSON from any page: ours refuses another Origin, a cross-site press and a body over 2 KB, as /posting does.
- **E2:** Her shoot 'plugged' is a /Volumes regex (Mac only): ours uses this_computer.drive_words / volumes() on both computers.
- **E2:** Her backups list only knows shoots the queue knows: same as ours after edit_queue.py scan, which the instructions already run once; noted, not changed.
- **E3:** Her 'safe' is finished-and-no-problems only: a sample backup or one with unchecked files would read 'Card safe to format'. Ours uses the backup's own verdict (backup.py's ok rule and the report's all_good).
- **E3:** Her 'Second copy made' is true whenever manifest['second'] is a path, checked or not: ours counts the second copy's ok files.
- **E3:** Her month-heading rule (i >= RECENT || (q && shown.length > RECENT)) puts headings under a search only when more than ten match: ours shows month headings on every search result and after Show older, and never on the first ten.
- **E3:** Her drive and found checks are /Volumes-only and os.path.isdir on a path from the queue: ours goes through edit_queue.folder_of (follows renames and settling) and this_computer.
- **E3:** Her search filters shoots by name only, so a backup whose name matches but whose shoots don't vanishes: ours matches the shoot's name or the backup's session name.
- **E3:** Her 'See the report' on a backup opens the newest card's report: ours opens the shoot's own page (serve_report of the newest card) via /report-url, as parts/backup.md says.
- **E4:** Her kit list is her server's list_shoots() by Content folder names with /s/<name>/thumbs: ours is posts.kits() with the kit's own name and our home-thumbs, addresses through _in_address so a kit named 'Smith #2' keeps its pictures.
- **E4:** Her Open the post kit goes to her post-kit.html on 8799: ours to our kit page on the same server.
- **E4:** Her search lowercases name only: ours matches name and folder.
- **E5:** Her 'store' accepts any shoot id, so a waiting shoot could be archived off the page: ours refuses unless the shoot is delivered.
- **E5:** Her renderFolds opens a fold on a search hit and never closes it when the search is cleared: ours closes folds that were opened by the search when the box empties.
- **E5:** Her searchAll hides queue cards with display:none inside a draggable list, so drag-to-reorder over hidden cards saves an order with them in it: ours keeps the hidden cards out of the order sent on drop.
- **E5:** Her toast for unqueue names the shoot before the save answers: ours toasts after Q is updated.
- **E8:** Her note says 'copy straight from the chosen folder and skip the drop box' as an alternative: that would lose the stopped-bring resume and the 'already copied' pass; not taken.

### Touches other lanes

- S/posting_queue.py do_GET gains '/backups.html', '/make-posts.html', '/home-data'; do_POST gains '/kit-archive' (Origin-guarded). Other lanes adding routes to the same handler must not reuse these names; v27 §8's Posted/unposted work on /posting belongs to the posting lane.
- /home-data's JSON carries `queue: [{name, due}]` (the editing queue in order) for the stories designer's 'My editing queue' template (v26 §5 fillQueue): the designer lane reads it from the same server, no second route needed; `kits[].archived` is there too if the kit page wants it.
- The kit page's Back to home stays '/home'; if the crumbs lane (v27 §7, crumbs.js: Home › <shoot> post kit › ...) wants a 'Make posts' step it is '/make-posts.html' (and '#kits' scrolls to the list).
- S/edit_queue.py's status 'finished' now reads 'delivered' to the photographer; `edit_queue.py done` output changes ('Delivered: ...'); the post-kit lane's 'I'm done with the beach shoot' step and `offers --mark` keep working on status finished, nothing to change there but the words in parts/post-kit.md.
- S/first_look.py and S/serve_report.py (the report) are shared with the backup/report lane: E7 adds lines in shoots_section and a GET /open?shoot= route; coordinate so first_look.py is edited once.
- S/posts.py kits() gains 'archived'/'archived_at' from ~/.studio/kit-archive.json; home.kit_thumbs is used by the Make posts screen; any lane listing kits sees archived ones unless it filters.
- P/where-things-live.md gets kit-archive.json, stored/stored_at, brings.json and drop/cleared/: other lanes adding records should append to the same file in one commit.
- .github/workflows/check-pc.yml: two new tests on both jobs; the Mac page job gets the hidden-Chrome parts under guard.

### Not to build

- v26 §6 test-only bits: the ?home=test / sessionStorage assistantHome scripts on posting_queue.py, report_page.py and edit_queue.py's Home links, and post-kit.html's localStorage assistantHomeTest Back button (ours is the real home; v27 §14 also lists these as still to drop).
- Share my queue as a button on the editing queue (Nicole: 'a great idea, but it's hideous'; removed; it became a stories template, which is the designer lane).
- The fifth workflow step, uploading galleries to Pixieset/Dropbox (talked through and left out; the workflow ends at Instagram).
- Set aside for later (v26 §7): a custom logo or name on the queue for screenshots, centering photos on faces automatically, gallery upload.
- v27 §13: the friendlier 'Good morning' home page with a to-do list (an IDEA; she put the page back; brainstorm first).
- Her /hp/ proxy to the Assistant's server and her 20 s home-data cache (not needed on one server).
- Her home_data.py, server.py routes and pages as files: read as data, never run, never copied.
- Nicole's second drop-box option (copy straight from the chosen folder, skipping the drop box).
- v26 §5 (the stories designer: guides, sticky stage, Let my assistant choose, templates, Redo, sets, ×): the designer lane, not this one.

### Open questions for Nicole

- Back up a card screen: a delivered shoot's pill still reads 'Edited' (your STATUS map) while the queue says 'Delivered'. Keep 'Edited', or 'Delivered'?
- The home page's and Make posts screen's lines say 'single photos'; the post kit has no single-photo card since Nov 11 (a one-slide carousel is a single post). Keep the words as they are?
- The report's sneak-peek line: your sentence is in; we kept 'Not feeling them? Just say what you'd rather see.' after it so the Pick again / Show me more buttons have their cue. Keep ours, or just yours?
- First-backup question: you suggested name-then-date as the one suggested option; Dustin's earlier pick was date-first ('keeps them in order'). Built with yours recommended, both offered. Settle which is first.
- The end-of-backup handoff: built as 'Open your folder to start editing. When your editing's done, come back and say "I'm done with the <shoot>", or click Make posts from a shoot on the page, and we'll make your posts.' Reword as you like.
- 'Make posts from this shoot' on a delivered gallery opens the Make posts screen (as yours). Would you rather it opened that shoot's post kit straight away when one exists?
- For Dustin: clearing the drop-box copy to the Trash after a checked picker sort is the first time the Assistant moves anything of theirs to the Trash (standing rule: nothing deleted). Built behind a re-check with set-aside as the fallback; say yes, or keep set-aside only.
- For Dustin: the archive record lives in ~/.studio/kit-archive.json (central, as hers, with a time per kit) rather than in each kit's kit.json. Fine?
- v27 §13: the friendlier 'Good morning, Nicole' home page is noted, not built; brainstorm when you're ready.

## How the lanes meet

- Lane A builds the shared contracts first: the timing (A1, A2), photo numbers that stay fixed when photos are added (the append-only sheet, A7), the several-reels record with `reels_of` and `order_for_version` (A4), and one shared `versions` bar module for the reel and talking pages. Lanes B, C and D merge `v27-a` into their branch before the items that lean on these (B16, C5, C6, D2, D5).
- Lane D builds `look.crumbs()` (D6) first; the other lanes merge `v27-d` and call it in their page bars; whatever is still unwired at the end is wired in the whole-build round.
- In `S/posting_queue.py` each lane edits only its own page's route tuple in `do_GET` / `do_POST` (one line each); Lane D owns the rest of that file; Lane E adds its three page routes and `/kit-archive`.
- `parts/arrange.md` is edited by section (A: reels, B: designer); `SKILL.md`'s table and `parts/where-things-live.md` get one row or line per lane and are merged by hand.
- Tests: each lane runs its own area's tests in its worktree on every item, and the whole-build round runs the sweep, `tools/check_plugin.py`, `tools/check_pc.py` and `tests/skill_text_check.py`, then GitHub's Windows and Mac machines on the push.

## Lane A, stage 2, built (Nov 17): the chooser of four kinds, step 1 and 2, the song drop-down, the queue button

Built on branch `v27-a` after stage 1 (the paces, the fixed photo numbers, the short clip), with `v27-e` merged before A8 (the Trash helper and Lane E's `POST /reel-song-remove`). Items A6, A7 (its page half; the numbering was stage 1's), A8 (its page half; the route is Lane E's) and A16. Four commits: `b1454fc` the chooser and the kinds with step 1 and 2, `8fa6860` the merge, `d0d358c` the song drop-down, `7aea0aa` the queue button. The full account is in `CLAUDE.md`'s v27 section ("Lane A's stage 2").

**What a photographer sees.** The reel page opens on "Which reel do you want to create?" with her four cards; each kind is its own page with her title and only its steps, and comes back as its kind from Your reels. Step 1 has her new heading, the videos in one drop-down, the ask box first; step 2 is "Choose your photos", the order stuck to the top while All your photos scrolls, + Add photos, and "N new photos in. Show my new photos" when photos are dragged into the Photos folder, every other photo keeping its number. Step 3 is her drop-down with Listen and Remove this song (two taps, to the Trash). Add this reel to my posting queue sits under Your reels once the reel is made, and beside Open CapCut after a make.

**Choices where her spec was silent, or ours on purpose:** a reel remembers its kind and that wins over the address (hers: the address alone); nothing is saved by opening a page (hers saved footage and style on every load); a photo still being copied in holds the re-list until it has settled; on a phone the order does not stick; the link back to the chooser is a pill in the bar beside the kit's (hers hides it under the path at the top, crumbs.js, which is Lane D's); "How should it feel?" is written hidden (her v27 CSS hides it) and a feel saved before still counts; B-roll's chooser card is there before B-roll's own make (stage 4), and Make my reel on a B-roll page says the part isn't ready yet; a server without the remove route gets one line of ours.

**Her faults fixed, not copied:** her chooser set the title in JS after load (ours on the server); a switch to a reel of another kind kept the address's kind and hid the wrong steps; applyKind saved on every load; her page polled /photos.json every 4 s beside its other polls (ours asks the state it already polls); her reelToQueue re-entered itself after the rhythm was set, and its "already in your queue" went by status green alone (ours asks the queue by version, once).

**Not tried, said bluntly:** nobody's hand has been on the new page; the hidden Chrome did not play the song (Listen's address and the route are proven by request, the sound was not heard); the re-list ran on tiny pretend JPEGs, never on a real export of hundreds of photos (its cost on a big folder is `reel.py sheet`'s own read of every photo's header); no real song of anyone's went to the Trash from the page (the tests' own Trash folder only); the kit page's Reels card (Lane D's) still says "Reel" and "Create my reel →" and opens the chooser.

## Lane E, built (Nov 17): the Trash helper, Remove this song, the Make posts screen

Built on branch `v27-e` from `v27` (which already holds v25 and v26, merged Nov 17). The lane's plan, with her exact lines and the already-built list, is the planners' `home.json`; its items on v27 were E11 (the Trash helper), E10 (the Make posts screen's v27 words), E12 (Remove this song) and E14 (this section, CLAUDE.md, the workflow, the sweep). Everything else in the Lane E table above (E1 to E9) was already on `v27` from the v26 build and was not rebuilt. Four commits: `1ccb2e1` the trash helper, `a715e05` the Make posts screen, `478752e` the song remove route, and the one for this section.

**What a photographer sees.**
- **Remove this song** (her v27, section 2, step 3: "two taps, to the Trash"). Beside the song drop-down on the reel page: one tap turns the button into "Move it to the Trash?", a second tap moves the song, and every sound taken from a recording, to the computer's own Trash (the Recycle Bin on a PC), and the page says "Moved to the Trash. To get it back, open the Trash in Finder and choose Put Back." If that song was the open reel's pick, the reel goes back to "no song picked yet". Nothing is deleted: Put Back (Restore on a PC) brings it all back. The button itself and its two taps are Lane A's, inside the song drop-down it rebuilds (A8); this lane built the route, the words and the record change the button calls.
- **Make posts from a shoot** (her v27, section 8, screenshot 08): the lede now says a post kit is built for each shoot ("post kit" in bold), a box under it answers **What's a post kit?** in her words, the steps title reads "How to make a post kit from a shoot", step 2's small line is "I'll bring your photos in and open your new post kit. You'll find it below any time, too.", and a third step, **Make your posts inside your post kit**, has no button: it happens in the kit. The three v26 lines these replace are gone.
- **Nothing of theirs is ever deleted,** and the assistant has no command that moves anything to the Trash. Asked in the chat to remove a song, it points at the page's button (and at Put Back if they regret it); asked to delete anything, it says it never deletes.

**Our way underneath.**
- **One door out: `this_computer.trash(path, inside)`** (new section of `scripts/this_computer.py`, after `no_windows()`). On a Mac it is Finder's own delete through osascript, the path handed in as an argument (`on run argv`, never pasted into the script: the route `finder.py` already uses), called done only when Finder's answer names a `.Trash` / `.Trashes` place and the item is gone from where it was. On a PC it is Windows' own `SHFileOperationW` (`FO_DELETE` with `FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI`, the path double-NUL-terminated, through ctypes; nothing installed, so her `send2trash` suggestion is not taken). Never `os.remove`, `os.unlink` or `shutil.rmtree`, and a test greps the source to hold it so.
- **It looks before it moves** (`trash_check`): refused, with nothing moved, are a path that is not there, a link (never followed to its target), the folder `inside` itself or anything outside it by real place, a folder `inside` that is a link, a path with "." or ".." in it, a relative path, a trailing slash, on a PC a path too long, and a drive with no Trash (`~/.Trash` on the home disk, `<drive>/.Trashes` elsewhere; `$Recycle.Bin` on a PC), so Finder or Windows can never delete outright or put up a box nobody sees. `trash_many(paths, inside)` checks every path before the first move, moves in order, stops at the first failure and answers (ok, words, moved, left), a path given twice counted once.
- **No test ever reaches the real Trash.** The tests' switch `STUDIO_TRASH_FOR_TESTS=<folder>` sends items into that folder with `this_computer.rename` (a name already there gets " 2", " 3" before a file's extension), and a run that set `STUDIO_NO_WINDOWS_FOR_TESTS` but no trash folder is refused outright. The real routes are tried in the test with a stand-in in their place that records what it was asked.
- **The route: `POST /reel-song-remove {kit, song: id}`** (`reel_page.remove_song`; hers is `/music/remove {path}`). The id, never a path, is found on the server among the shoot's songs right now, behind the pickers' same-page guard and the cross-site check `/reel-version` has. Only a song in the shoot's own Music folder can go; a recording takes every sound made from it, found two ways and merged (the names noted for it in `.kit/reel-sounds.json`, and every "<name> sound N" beside it: hers takes " sound" to " sound 9", ours any number). Every path is checked first, then each goes through `trash_many`. If the song itself went, the open reel's pick is cleared under the record's lock with the counter one higher (so a page a step behind is told), other reels of the shoot are not touched (they say her "That song isn't there anymore. Press Add my music and drag it in again." when opened, as hers), and the sounds' notes are dropped with the version before kept. The answer is `{ok, words, songs, cleared}`; when one file could not be moved, her "I couldn't move that song to the Trash..." line comes with our "Already in the Trash: <names>." after it, so nothing already moved is hidden. One entry on the reel tuple of `posting_queue.py`'s `do_POST`; nothing else in that file.
- **Her words, whole:** `reel_page.WORDS` holds her four page lines (`song_remove`, `song_sure`, `song_removing`, `song_trashed`) and her two server lines (`song_not_here`, `song_cant_trash`); `trash_words()` turns the Trash, Finder and Put Back into the Recycle Bin, File Explorer and Restore on a PC. `this_computer.TRASH_WORD` and `TRASH_BACK` carry the same for every other caller.
- **The Make posts screen is words only:** `home_base.WORDS` (`m_lede` with its `<b>`, `m_what_h`, `m_what_p`, `m_steps`, `m_s2_small`, `m_s3`, `m_s3_small`), the `.whatkit` box and the third `.st` in `make_posts_html()`, her `.whatkit` rules in `look.py`'s tokens (the white card's paper, our line colour, DM Sans, max-width 52em as hers), nothing from the internet. Nothing the screen reads changes: kits, the archive, the small pictures, the picker route, `/clicked` and the `/home-state` reload all stay. `hello.md` knows the box and the three steps, so "what's a post kit?" in the chat is answered in her words and the assistant stops once the kit opens; `photos-in.md` and both setup guides say the same (the PDFs are not rebuilt, as before).
- **The instructions turned round:** `parts/arrange.md`, the reel skill's `SKILL.md` and `parts/where-things-live.md` ("Nothing of theirs is ever deleted (Nov 17)") replace "There is no Remove on a song" with the button, the Trash, Put Back, and no chat command. `CLAUDE.md`'s "Three things are NOT built" item 1 and "to settle" question 1 now say built, with the pointer to this section; the folder-naming question and the drop box's second copy still wait (her v27 says nothing new on either).

**Choices where her spec was silent (plainest behaviour):**
1. Only a song in the shoot's own Music folder can be removed from the page. A recording that sits in the Photos folder (their export folder, which the kit points to) stays, with a line of ours: "That one's in your Photos folder, so it stays. Take it out of that folder yourself if you'd like it off the list." Hers would send it to the Trash from wherever `list_songs` found it.
2. A recording's sounds go with it, however many ("sound 2" to "sound 47"), and the ones noted in `reel-sounds.json` too.
3. Other reels that had picked the song are not rewritten; they show her "isn't there anymore" line when opened (as hers).
4. When one of a recording's files cannot be moved, the ones already in the Trash are named after her line, rather than left unsaid.
5. The helper moves one item and refuses rather than guesses: a link, a path outside its folder, a drive with no Trash. Callers decide what goes together and check every path before the first move.
6. The PC's words: "the Recycle Bin", "open the Recycle Bin in File Explorer and choose Restore" (the Mac line is hers).
7. The Make posts screen keeps the Back to home pill, not the crumbs path: her `make-posts.html` keeps the bar, and `crumbs.js` is for post kit pages only (Lane D).
8. "Single photos" stays in her lede (the v26 question for Nicole stands).

**Hers left out, on purpose:** her per-row Remove of v25 (v27's one button in the drop-down wins); her `/music/remove` taking a path from the page; `send2trash` on a PC (an install); v27 section 13's friendlier "Good morning" home page and `/home-data`'s `me` and `posting` fields (section 10) that only it reads: she put the page back and asked to brainstorm first; v27 section 14's test-only Home links, which were never in ours.

**Her faults we fixed rather than copied:**
- Her remove runs one osascript per file and stops at the first failure with earlier files already gone, and never says which: ours checks every path first, then moves, and names what moved if one fails.
- Hers is Mac-only (osascript): ours has a PC branch through Windows' own call.
- Her route takes any path from the page and checks it only against `list_songs`' paths: ours takes an id, finds it on the server, and refuses another website's press.
- Hers never clears the song in the record on the server (the page does it on success): ours clears the open reel's pick under the lock, so a page that never gets the answer still sees it on reload.
- Hers would send a recording from the Photos folder (their export folder) to the Trash: ours refuses.
- Her Make posts page loads her CSS and Google Fonts from the internet and its Open the post kit goes to `post-kit.html` on port 8799: ours is inline in our tokens, and the kit page on the same server.

**Tests** (both Pythons: 3.12 with Pillow and Apple's 3.9 without; the real `~/.studio` unchanged before and after, by a hash of every file):
- `tests/trash_check.py` (new): 58 checks, no server, no browser. The words; a file and a folder of files move whole into the test's trash folder byte for byte; " 2" and " 3"; a quote, an accent and an emoji in a name; every refusal with nothing moved and a link's target untouched; `trash_many`'s check-first, order, twice-once and which-moved; the real routes with a stand-in (the no-windows refusal, osascript with the path as an argument, done only on Finder's `.Trash` answer and the item gone); the no-Trash drive; the grep for remove/unlink/rmtree. Seven behaviours were taken out one at a time and the test failed each time.
- `tests/songs_check.py`: 107 (73 before), its "Remove a song is not built" part turned into the remove part (37 checks through the route with a stand-in for the page server's handler): a recording with "sound" and "sound 2" beside it goes to the run's own Trash byte for byte; the open reel's pick cleared with the counter one higher and a second reel untouched; the same press again gets "isn't in this shoot's folder anymore"; a song in the Photos folder refused and left; another shoot's id, a cross-site Origin, a body over the cap and a kit that is not a kit refused with nothing moved; a Trash that fails on the second item names the one that moved; the route's source names no remove/unlink/rmtree.
- `tests/home_base_check.py`: 222 with the hidden Chrome, 134 without. Her v27 `make-posts.html` is read from the newest pack that has it and compared both ways; the box sits between the lede and the steps title; the steps are 1, 2, 3; step 3 has no button; the v26 lines are gone; the box fits a phone.
- `tests/reel_page_check.py`: 343; her six v27 lines both ways. `tests/skill_text_check.py`: 526 (507 before). `tests/loose_ends_v26_check.py`: 64. `tools/check_pc.py` clean, `tools/check_plugin.py` CLEAN (its standing note: the studio-manager description is 1,016 of 1,024 characters).
- The page tests around the lane, unchanged by it, run on their default ports one at a time under the guard: `edit_queue_v26_check` 145, `report_v26_check` 107 / 102, `reels_check` 150 (one SKIP: her v25 pages are looked for beside the main checkout, not this worktree), `home_base_check` 222 both, `reel_page_check` 343 both, and `pc_smoke` 230 / 183 (the 3.9 skips are Pillow's, as in the v26 sweep). Every run was green on both Pythons on the branch's head before this commit; the real `~/.studio` was unchanged (every file's hash the same before and after), and no page server of the sweep was left running. The lane's own port range (8850 to 8859) is refused by the tests themselves (`chrome_drive.NEVER_PORTS` holds 8850 to 8866 for the photographer's own page servers), which the whole-build round should know when it hands out ranges.
- GitHub's check (`.github/workflows/check-pc.yml`): `tests/trash_check.py` on both jobs and in both paths lists; the Songs steps' names say Remove this song is built. The first push is the PC branch's first real run.

**Not tried, said bluntly:**
- **Nobody's hand has been on it.** The Remove this song button is Lane A's (A8) and did not exist on this branch; the route was pressed only from the test's stand-in handler. No real song of anyone's has been moved by the route.
- **The PC branch has never run on a real PC** (`_recycle`, the `$Recycle.Bin` check, the held-open refusal, all marked `[check on a PC]`). GitHub's Windows machine on the first push is the first try.
- **A real external drive on a Mac** (Finder's delete to `<drive>/.Trashes`) was not tried: only the home disk's `~/.Trash`, once, by hand, on a scratch file of our own (`python3 this_computer.py trash <file>`; it landed in `~/.Trash` with Put Back).
- **No fresh chat session has followed the turned-round instructions** (pointing at the button, never deleting, answering "what's a post kit?" from the box).
- Nothing has run on GitHub; the branch is not pushed.

**Theirs to settle (for the note to Nicole, the whole-build round's):**
1. Remove this song is built as her v27: to the Trash (the Recycle Bin on a PC, nothing installed), a recording's sounds with it. Two choices of ours: only a song in the shoot's Music folder can go from the page (a recording in the Photos folder stays, with our line), and a second reel that had picked it is not rewritten, it says her line when opened. OK on both?
2. Our lines, all drafts: the Photos-folder line and "Already in the Trash: <names>." on the reel page; `this_computer`'s PC wording and its refusals ("That isn't where it was anymore.", "That's a link to somewhere else, so it stays where it is.", "That isn't in the folder it should be in, so it stays where it is.", "That drive has no Trash to put it in, so it stays where it is.", "That name is too long for Windows to move it to the Recycle Bin, so it stays where it is.", "I couldn't move that to the Trash.").
3. The Make posts screen's lede still says "single photos" (the post kit has no single-photo card; a one-slide carousel is a single post). Keep the words?
4. v27 section 13's friendlier home page, and `/home-data`'s `me` and `posting`: not built until she has brainstormed the page.
5. Still open from v26 on this lane: "Edited" on the Back up a card screen while the queue says Delivered; a press on step 1 or step 3 still recorded; an archived kit's search line; Archive asking nothing first; no chat command archives a kit; a moved folder's "tell your assistant where it went".
6. For Dustin, unchanged: the first-backup folder-name question, and the drop box's second full copy (now that a song can go to the Trash from the page, clearing the drop-box copy to the Trash after a checked picker sort would go through the same door, with set-aside as the fallback).
7. "Show the archive" still scrolls to Uploaded shoots (as hers); "show my archived shoots" opens Archived. Should "the archive" now mean Archived?

**For the whole-build round:** Lane A's A8 wires the button against `POST /reel-song-remove` and the words in `reel_page.WORDS` (the Chrome part of the test, the two taps and the 4 s timeout, is A8's); `parts/where-things-live.md`, the reel skill's `SKILL.md` and `CLAUDE.md` each got one paragraph or pointer from this lane, to be merged by hand with the other lanes'; the draft note for Nicole (`docs/nicole-v27-notes-<date>.md`) is not written by this lane, so the questions above are its material; `tests/edit_queue_v26_check.py` uses `--port` + 10 and + 15 for its stand-in servers, so a lane's ten-port range does not hold it.

## Lane A, stage 3, built (Nov 17): the footage editor, and naming the photographer's own clips from the chat

Built on branch `v27-a` after stage 2. Items A11 (the footage editor, her v27 section 3, screenshots 13 to 16) and A12 (Name my clips for <shoot>: `footage.py picks` and `describe`, her v27 sections 3 and 11). The v25 Trim panel is retired from the page (A11's decision 1). The full account is in `CLAUDE.md`'s v27 section ("Lane A's stage 3").

**What a photographer sees.** Under "Your footage" in step 1 the page is laid out like a video editor: the player on the left, the Footage drop-down, Make a clip and Your clips on the right, the timeline of stills along the bottom with Zoom in. Start here turns orange and an orange striped stretch grows as the video plays; End here makes it solid with a handle at each end, which they drag to trim it (the video jumps there) or slide by the middle; a clip is 1 to 15 seconds; Add clip puts it in Your clips with a purple YOUR PICK tag and "Not named yet", the trim staying dashed with "✓ Added" until they move it to make the next one. Every clip shows at once in two columns, with Use / ✓ In reel and ×; a click on a card or on its clip on the timeline picks it, and its ends and middle work on the timeline. The page then offers "Name my clips for <shoot>": pasted into the chat, the assistant looks at each clip of theirs and gives it a short plain name, which the card shows by itself; a later trim keeps the name.

**Choices where her spec was silent, or ours on purpose:** one zoom threshold (60 s) for Start here and for a picked clip (hers 60 and 90); after a reload the trim is drawn dashed from their newest clip of that video (hers lost it); the Trim panel of v25 is off the page, its code kept behind one switch; the Name my clips line is DM Sans (hers Fraunces); `describe` writes the record itself under the lock (hers posted to her page server); an "about" in the names file is refused (hers stored it quietly though the feature was taken out); each `picks` run goes in a fresh folder (hers wrote one clip's sheet over another's); on a PC the editor runs without stills and says so, and `picks` makes no sheet.

**Her faults fixed, not copied:** the ids snapshot before the add's request (her page's 4 s look could bring the new clip in before her response, and then nothing was selected); × on a card whose clip is in the editor clears the trim too; the video swapped by key (hers compared the address's spelling); the ruler's times rounded (hers drifted to "0:01.0" on a short video); her `/moments/add` made the still with ffmpeg (ours as before, through the one video turn).

**Not tried, said bluntly:** nobody's hand has been on the editor; the hidden Chrome drove the drags with synthetic pointer events on 6-second self-made clips (a 15-second stop and the zoom at 60 s are held by their numbers and the 30-second pretend length, never seen on a long real video); `picks` sheets were made for 3-second clips of a solid-colour test video and never read by a Claude naming anything; no real reel of Nicole's has been opened on the new page; the PC branch ran on a Mac with AVFoundation switched off, never on a PC.
