# Testing The Assistant 0.3 (0.3.1 pushed Oct 21, 4:30pm)

0.3.1 is live on the marketplace (horizonfound/hf-tools). Installed copies update on their own; the Update button on
the plugin's page (Settings → Plugins → The Assistant) forces it. A zip backup is in Dropbox → The Engine
(`the-assistant-plugin-0.3.1.zip`).

## What changed, in one breath
Three tools (make a reel, make a carousel, make stories), the rebuilt interview, the menu, and the playbook and
guardrails every tool reads first. Plan my week and the grid makeover are gone. Nothing to install for the reel tool:
the Claude workspace on a Mac already has what it needs (checked on Dustin's Mac, Apple silicon).

0.3.1 (same day): Dustin watched the first reel and called it: static in the sound, ugly text, jittery zoom. All three
were real defects, all three fixed and measured (`reel-tool-design.md` has the numbers). The grader now
checks those things too; it fails the old reel and passes the new ones.

## Already tested, by Claude, on Dustin's Mac
- `check my setup`: everything OK, "fast."
- 0.3.1 make a reel from the test session (9 photos, a 3-second clip, the song): 15 s to render plus two trial reels,
  graded PASS (cuts on the beat, no clicks, no clipping, motion smooth, text readable). A photos-only montage with the
  "build" rhythm and an end line: 19 s, PASS.
  Files: Dropbox → The Engine → _test → session → _assistant → reel-after-clip and reel-after-montage. The first
  version Dustin watched is still there (reel-kira-beach) for the before/after.
- Make a carousel (6 slides with a cover line) and make stories (3 frames): under 2 seconds each.
- CapCut draft route: a script-written draft listed, opened and exported in CapCut 9.6.0 on the Mac (Oct 21).
- Not tested: a real session with real photos and a real song; a clip of someone actually talking (the ducking and
  the dead-air trim are built, not heard yet); HEIC photos; a Windows PC; an Intel Mac; the Canva folder route;
  CapCut's music folder.

## Studio Manager (added Oct 23)
- `backup.py` on Dustin's R5 card (`/Volumes/EOS_DIGITAL`) to the RAID (`/Volumes/Big Kahuna/The Engine Test/2026-10-23 Card test R5/`): 5 files, 6.9 GB, every file verified by sha256 against the card; two files re-checked independently with `sha256sum`, matched. 128 seconds in the desktop workspace, run in chunks with `--budget 140` because that workspace stops a process when a step returns.
- Not tested: a second copy to a cloud folder (the report should flip to "safe in two places"); a card with RAW photos; a mini-session card with several shoots; a long run in Claude Code without chunking.

## Dustin, at the Mac (30 minutes)
1. Settings → Plugins → The Assistant → Update. Check the version says 0.3.1.
2. Connect a real session folder: finished photos, one behind-the-scenes or talking clip, and a song file
   at the top level. HEIC straight from an iPhone is fine; that's one of the tests. A clip of someone talking is the
   other one: it's what the sound mixing was built for and nobody has heard it yet.
3. "check my setup", then "make a reel from the <folder> session." Go through the hooks. Time it. Watch the reel on
   your phone, sound on.
4. "make a carousel from the same folder." Look at the order and the cover.
5. "stories from today's post."
6. Anything that broke or felt dumb: screenshot, Slack it, say Mac.

## Nicole (about an hour)
1. Update the plugin (same clicks). Start a fresh chat in your Project.
2. "start here" again, from the top. This is the rebuilt interview; it should feel like a conversation, ask for your
   voice first, never ask for captions, and never make you say why you're special. Say "note:" any time something
   feels off and it saves the note.
3. When the Brand File is done: make one reel, one carousel, one set of stories from a real session.
4. Read `shared/playbook.md`. Every line marked "[draft, Nicole to confirm]" is one Claude filled in. Correct anything
   that isn't you.

## What a good result looks like
- The reel: every cut on a beat, the song starting where it picks up, the hook readable on a phone and off the faces,
  in your fonts, the voice clear over the music. "Could post tonight." Watch for any click or crackle in the sound,
  text you have to squint at.
- The interview: you feel seen; the Brand File sounds like you; the look section was short.
- The carousel order: you'd keep most of it.
