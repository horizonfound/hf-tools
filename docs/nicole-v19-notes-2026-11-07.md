# Nicole's handoff v19, built into the Assistant (Nov 6 to 7, 2026)

Dustin, Nov 6: "unpack it and get started"; "yes that is A OK, proceed" to the plan "identical for the photographer, our way underneath". Built on branch `v19` overnight, one helper at a time after the Mac ran out of memory once. Her handoff is in `reference-private/` (never pushed). The plan with all 28 defaults: kept in the session's scratch as PLAN.md; the defaults that matter are below.

**Nothing here has been sent to Nicole (rule 10).** Part 2 is a draft for Dustin to send or not.

## 1. For Dustin and Nicole to decide (each has a default, in one place in the code)

1. **Every reel now follows her timing**, photo-only chat reels too. Calm is about half as long as before; "On every beat" is the recommended vibe instead of "A little of everything"; "Fast" is gone; some short songs that used to be refused now fit. Default: hers (`timing.DEFAULT_PACE`).
2. **A single post replaces the carousel on the kit.** A kit holds one laid-out set, so a saved one-slide design takes the carousel's place on the kit page and in the posting queue. Default: as built, and the Assistant says so. Keeping both is a small follow-up if wanted.
3. **Where things are kept.** Her rule: everything on the photo drive. Ours: anything about one shoot is in that shoot's hidden `.kit` on the drive; the Studio File, ledger, queues and templates stay on the computer (they must work with the drive unplugged).
4. **The licence line on the song step** is her Nov 6 wording ("pick No song... add a song from Instagram's own music"). Check the "can get your reel muted" claim before it goes in any sales copy (rule 7).
5. **Reel names**: ours ("2026-11-01 Beach reel", then "reel 2"), not hers ("Hannah reel 30"). `reel.REEL_NAME`.
6. **Figtree**, her default story font, is not carried: no copy was on this Mac. It loads from Google; offline the text shows in Georgia with a line saying so. Two OFL font files dropped into `shared/fonts` finish it (needs an OK to download them).
7. **Footage on a PC** is a gap: a PC lists the videos, plays H.264 and makes clip reels, but takes no stills, so "Look through my footage" and the moment strip are Mac only for now. The page says so in plain words.
8. **Half-made leftovers.** A reel make that is stopped part way leaves a hidden `.<name>.making-...` folder (no project in it) and a hidden `.part-` sound. Nothing deletes them. Clear them on a later run, or leave them?

## 2. Draft note for Nicole: where ours works differently from hers

Fixed in ours (hers has the bug):
- Footage moments never save in hers (`save_json` is handed `REEL_PAGES` itself). Ours save, as BUILD.md describes.
- The short-song heading never shows in hers ("only 15.4 seconds" doesn't match `\d+ seconds`). Ours uses a flag.
- Footage reels with No song stop in hers (a name used before it is set). Ours make them with the footage's own sound, as step 4 says.
- The "Recommended for behind-the-scenes reels" tag shows on photos-only reels in hers.
- Her page and her sheet number photos differently when names mix capitals or include PNG/HEIC. Ours uses one numbered list.
- For one mix her engine calls the 60 s test beat "too short" with 50 s to spare. Ours doesn't (timing identical).

Built our way on purpose (same for the photographer):
- No SortableJS, no Google Fonts for the pages, no ffmpeg or Pillow on a Mac: the Mac's own AVFoundation makes stills and the player copy. A small copy is never bigger than the original.
- Songs, videos and moments are named to the page by ids, never paths. Records live in each shoot's hidden `.kit`, not `<studio>/reel-pages`.
- Every footage look goes in a new folder; nothing is deleted (hers emptied the stills folder).
- Make my reel runs as a job the page checks on, so reloading mid-make picks it up again.
- Two windows on one page: one extra line, "This order was changed somewhere else. Here's the newest." Past 40 photos: "A reel holds up to 40 photos. Take one out first."
- The reel page follows a fresh pick from Claude within 4 s while "Let my assistant choose" is on.
- Saved text sits where the screen shows it (hers draws 4 to 6 px higher in the saved file).
- A video still being copied into Footage shows as "still copying in" until it's whole.

Words that differ (her call to reword):
- Stories mode says "story" where her page says "slide" (Fill story, Story 1...), and "+ Add stories" where she wrote "+ New design".
- Saved stories: "<short> stories - 01.jpg", then "(2)"; "1 slide saved" / "1 story saved" for her "1 slides".
- The stories preview shows the student's own handle, or "yourname", never hers.
- Remove this story is greyed at one story with "It's your only story, so it stays."; past 40: "A set holds up to 40 stories."
- The post kit's words column splits Hooks and Story lines into one box each with its own Copy, adds Short caption and a "Written from" line, and one quiet line under the cards for single photos, the reel cover and the kit folder.
- Some stories-mode words come from our Nov 6 carousel designer ("Snap into line", the tray line, "All N photos").
- PC lines, drafts: the trim tip ("open it in the Photos app and choose Trim"), and the no-preview and HEVC lines.

Her own wording that reads oddly (left as hers, suggestions):
- The reveal: "Added and selected" when the new card is not selected. Suggest "Added: 0:01.5. The reveal only uses moments matched to a photo."
- "starting the song 1 seconds in". Suggest "1 second", or "at the top" under 2 s.
- Empty step 1 says "any you pick yourself below" and "Play it here, or tap a still" with nothing below yet.
- Her page says a Use this moment pick "shows up first", but her server puts it after earlier picks (ours follows her server).

Questions for her:
- A still every second up to 2 minutes (her code) or every 2 seconds up to 10 minutes (her SELECTS.md)? Ours follows the code.
- Is a photos-only reel meant to have no "How should it feel?" box?
- Songs under 40 s start at the top (her code); her docs say "where it picks up". Ours follows the code.
