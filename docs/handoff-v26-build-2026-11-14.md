# Building Nicole's v26 into the Assistant (started Nov 14, branch `v26`)

Dustin, Nov 14: "grab all the latest stuff from Nicole... and let's start building that into the main."

## What came from Slack (#the-engine, Nov 13)

- `Carousel-designer-and-reel-picker-handoff-v26-updates-since-v25.zip` (unpacked in `reference-private/nicole-handoff-v26-2026-11-13/`, data only, never run, never pushed): `UPDATE-v26.md`, `NOTES-from-Nicole-Nov-13.md` (her notes, sections 1 to 14), a clickable demo of the home base, her test home pages, her stories designer page, and her changes to `edit_queue.py`.
- "Notes for v25": the same notes file, byte for byte.
- One screenshot: the first-backup question "how do you like a shoot folder named?" with her comment "i think client name then date is probably best rather than date first".
- **No v25 zip was ever posted.** v26 says "unzip v19, then v20 to v25, and this one on top", so v25 exists on her Mac. Until it is sent, anything v25 changed in files v26 does not carry is unknown to us.

## The rule, as before

Identical for the photographer (her words whole, the same behaviour), our way underneath. Her code is read, never run or copied. Her "test-only bits" (section 6 of her note: port 8799, `?home=test`) are not built: her home base becomes the real home page.

## Stages (one at a time, each with tests that fail without the change)

- **A. The editing queue** (`edit_queue.py`): the check mark is Mark as delivered; Take out of my queue; one Find a shoot over everything; Uploaded shoots; Delivered (opens and closes); Archived (behind "Are you sure you want to archive this?"; Bring it back); "your assistant", never "Claude". Actions `unqueue`, `store`, `unstore`. Nothing is deleted.
- **B. The home base** (`home.py`, the posting server): the welcome words, Today, four step cards in the order of the work, Open my Assistant folder; no recent-shoots list. Two screens of their own: **Back up a card** (every backup: 10 newest, Show older by month, search; card safe to format, second copy, something needs a look; each shoot with Open this folder and See the report; drive unplugged; folder moved; the cards of one shoot shown as one backup, wired to our linked backups) and **Make posts from a shoot** (post kits: 20 newest, Show older, search, Archive by hand and Bring it back). Kit archive list kept in `~/.studio/kit-archive.json` (where things are saved stays ours).
- **C. The stories designer** (`design*.py`): "Show Instagram's guides"; the stories stay in view while the photos scroll; Let my assistant choose (a note saved as `ask`, a line to copy into the chat, and the chat side of it); templates Gallery delivered (4), My editing queue (1, filled from the queue), The full story (10), Seamless swipe (6); Redo; sets of stories (replaces "one stories design per shoot"); x on each story's label.
- **D. The report's words** (her notes, section 2): why there are two folders; "Does everything look right?"; Open this folder on each shoot; the sneak peeks explained; the closing line changed.
- **E. Instructions, the notes for Nicole, CLAUDE.md, the full test sweep.**

## Waiting on Dustin and Nicole (not built until they say)

1. **The v25 zip.**
2. **The folder-naming question at setup.** Nicole: it reads as "name this folder"; ask "do you name your shoots a specific way?" with a box, and suggest name then date. Dustin, Oct 24: year first stays as the recommended one. They differ on which is suggested.
3. **The drop box keeps a second full copy** (about 5 GB for Nicole). Her suggestion: clear it to the Trash after a checked sort when the photos came through the folder picker, or copy straight into Your Content. Either changes "nothing is deleted" or the Oct 30 design.
4. Set aside by Nicole herself: a logo for queue screenshots, centering on faces, gallery upload.
