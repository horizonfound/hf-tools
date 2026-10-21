# The Assistant · by Horizon Found

Version 0.3.1 (working title; the plugin's internal name is still `the-engine` so updates keep flowing).

You decide what to post. The Assistant makes it, in your voice and your look, from your own photos and clips. It never posts anything and never touches your originals. It runs inside the Claude desktop app, and we say so.

## What's in it

| Say | What happens |
|---|---|
| **start here** | A forty-minute conversation that learns your business, your voice (you talk, it listens) and your look, then writes your Brand File. Once. |
| **make a reel** | A session folder (photos, behind-the-scenes clips, a talking clip, a song) becomes a reel cut to the beat: the song starts where it picks up, the photos move slow and smooth, the text is set like a designer would, the voice sits over the ducked song. Ten to twenty hook options in your voice, extra versions for trial reels in seconds, and it grades its own result before handing over. |
| **make a carousel** | Every photo from a session on one numbered sheet; the Assistant picks and orders them so people keep swiping, with a cover line or none. Exports slides ready to post. |
| **make stories** | Three to five story frames spun off today's reel or carousel. |
| **check my setup** | What this computer can do and how fast. Nothing to install. |
| **what are we doing today?** | The menu. |

Everything it makes lands in an `_assistant` folder inside your session folder. Your photos and clips are never moved or changed.

## Install (once, in the Claude desktop app)

Settings → Plugins → Add marketplace → Add from a repository → paste `horizonfound/hf-tools` → Sync → Discover → The Assistant → Add. Updates arrive on their own.

Connect the folder your sessions live in (the Add folder button in the desktop app). That is how the Assistant sees your photos without you uploading anything.

## How it's built

- `skills/` : one folder per tool. `SKILL.md` is what Claude follows; `references/` are the rules it reads; `scripts/` are the small Python programs that do the measured work (beats, cuts, crops, text).
- `shared/playbook.md` : Nicole's thinking about posting, written down. Every tool reads it first. `shared/guardrails.md` : the hard-yes, hard-no list every piece is checked against. `shared/voice-of-the-assistant.md` : how it talks to you.
- `shared/fonts/` : free fonts for on-screen text (Cormorant Garamond, Montserrat, DM Sans, Inter, Fraunces).
- Scripts need only ffmpeg, Python 3, numpy and Pillow, all already inside the Claude workspace on Mac and PC.

## Requirements

A Mac or a Windows computer with the Claude desktop app on a paid Claude plan. Tested on Apple silicon. Intel Mac and Windows: the setup check reports what it finds; tell us.

Horizon Found LLC · The Assistant runs inside Claude. Separate companies, their own pricing.
