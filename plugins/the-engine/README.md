# The Assistant · by Horizon Found

The Assistant handles the busywork around a photographer's photos, on their own Mac, inside the Claude
desktop app. It never posts anything and never changes an original.

## What it does

| Say | What happens |
|---|---|
| **hi** | It says where things stand and opens its home page beside the chat. |
| **backup now** | Copies a memory card to your drive, checks every file, sorts and names the shoots, picks six sneak peeks, and leaves a report. |
| **make my posts** | Turns a folder of finished photos into a post kit: single posts, a carousel, stories, a reel cover, and captions written from what you tell it. |
| **make a reel** | Lays your picks on the beat of your song as a CapCut project for you to style and export. |
| **what's in my queue** | The shoots you still have to edit, and when each is due. |
| **show my posting queue** | What's ready to post and how your grid will look. |

## Installing

The setup guide is the one place for this: `docs/The Assistant - Setup Guide.pdf` in the hf-tools project.
In short: Claude desktop app, Settings, Customize, Plugins, + Add, Upload plugin, and the file
The-Assistant.zip. Use it from the Code tab with your Assistant folder selected.

Updates do not arrive on their own yet. We send a new file.

## How it's built

- `skills/studio-manager/` : the Assistant. `SKILL.md` is the short core; `parts/` holds the instructions for each kind of request; `scripts/` are the small Python programs that do the measured work.
- `skills/assistant-make-a-reel/` : the reel.
- `shared/` : how the Assistant talks, how it curates a set of photos, and fonts.
- Nothing to install: the scripts run on the Python a Mac already has.

Horizon Found LLC · The Assistant runs inside Claude. Separate companies, their own pricing.
