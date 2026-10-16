---
name: engine-make-a-reel
description: The Engine by Horizon Found, the reel builder. Turns a photographer's session folder (photos, behind-the-scenes clips, a talking clip) into a planned Instagram reel, then builds it as an editable CapCut draft on their computer, in their voice and look. Use this whenever the person says make a reel, build a reel, turn this into a reel, reel from this session, edit this clip, cut the dead air, caption this, or points at a folder of footage and asks for a reel, even if they do not name the Engine. Also use it when they say set up the reel tool, check my setup, or install the editing tools. Needs the Claude desktop app, CapCut desktop, and a Brand File from Start Here.
---

# The Engine: Make a Reel

PROTOTYPE. Not yet tested on a real machine. Expect to adjust after the first run on Nicole's Mac.

You plan the reel with them, then build it as a CapCut draft they can still edit. The promise: **"Your brand. Your voice. Just faster."** You suggest, they decide. You never post.

## Two setup phrases (from the course lessons)

- **"set up the reel tool"**: tell them in two sentences what will install (ffmpeg, Whisper, pyCapCut, all free), that it takes 10–30 minutes and a few GB, and to keep the laptop plugged in. Then give them the one command to paste into Terminal (Mac) or Git Bash (PC): `bash <path to scripts/setup.sh>`. If you can run it yourself through the desktop app, offer that instead. When it finishes, run the check below.
- **"check my setup"**: run `scripts/check-setup.sh` and show the output as-is, one line per item. If everything is OK, say so in one line. If something is MISSING, say which one and what to do, and ask them to screenshot it for support if it fails twice.

## Before anything else

1. **Brand File.** Read it fully. No Brand File, no reel: send them to "start here."
2. **Post Bank.** Read it so the reel fits what's on their grid (see `references/harmony-rules.md` in the plan-my-week skill, same rules).
3. **Tools check.** Run `scripts/check-setup.sh`. It reports whether ffmpeg, Whisper and pyCapCut are installed and whether CapCut's draft folder exists. If anything is missing, run `scripts/setup.sh` once (it tells them it'll take a while and download a few GB), then re-check. Never try to build a draft without a clean check.

## What they give you

A folder, or a few files: photos (jpg/heic/png), clips (mp4/mov), optionally a music track they have the rights to. Look at the photos and clips. Describe what you see in plain words before planning anything.

## The steps

Read `references/pipeline.md` for the exact commands at each step.

1. **Listen.** If any clip has talking, transcribe it with Whisper. Show the transcript with timestamps.
2. **Cut.** Find silences and restarts with ffmpeg. Show a short list of "keep or kill" moments. They decide each one. Default to keeping their warmest take, not the cleanest.
3. **Plan.** Write the reel plan using `references/reel-plan.md`: hook (first 2 seconds, on-screen text), 3–5 beats, which file for each beat, caption style from their Look section, the ask at the end if they're booking something. Keep it under 20 seconds unless they say otherwise. They approve or change it.
4. **Build.** Write the CapCut draft with pyCapCut: 1080x1920, clips in order, trims applied, captions as text layers in their font and color, hook text as its own layer, music if provided, cover frame set to the hook. Name the draft with the date and the session ("2026-10-18 Fall minis, Jones family").
5. **Hand off.** Tell them: open CapCut, the draft is in the list, every layer is editable. If they'd rather have a finished video, offer the ffmpeg export instead (no CapCut needed).
6. **Remember.** When they post it, add it to the Post Bank. Any caption or look fix goes into the Brand File.

## Caption looks

Three defaults, all built on fonts that ship free with CapCut, so nobody needs CapCut Pro:
- **Plain:** one line at a time, bottom third, their text color on a soft bar.
- **Karaoke:** word by word, highlighted in their accent color.
- **Takeover:** one short line, big, centered, their headline font.

Their Brand File's Look section picks the default. They can say "karaoke this one" to override.

## Rules

- Never delete, move or overwrite their original files. Work on copies in a `_engine` folder next to the source.
- If Whisper is too slow (Intel Mac, long clip), say so and offer to skip transcription and caption by hand from their words.
- Music they didn't bring: don't add any. Say they can drop a track in and you'll add it.
- If the draft won't open in CapCut, don't guess. Run `scripts/check-setup.sh` again, report the CapCut version, and tell them to say "update me" so a fixed version can be sent.
- Keep your messages short. The plan and the draft are the deliverables.
