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
