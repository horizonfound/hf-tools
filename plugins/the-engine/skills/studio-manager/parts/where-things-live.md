# Where the Assistant keeps things

Part of the Assistant's instructions. The first-thing checks, the rules and how you talk are in SKILL.md and apply here too.

## What lives where

What the Assistant knows about the photographer is in `~/.studio/`: `studio-file.md` (their drives and naming, readable) with `studio.json` beside it for the scripts, `cards.json`, the ledger of cards already backed up, and `queue.json` (the editing queue) with `queue-thumbs/` (small copies of three previews per queued shoot, so the queue page works with the drive unplugged). Everything about one backup is in its records folder: `<day folder>/_studio/` while the backup runs, then `<their place>/.studio/<day folder name>/` once it has settled (both hidden in Finder). Every script takes the old day folder, or the records folder, and finds the right place itself (`where.py`), so "rename the beach one" works the same before and after: `manifest.json` (every file and its hash), `index.json` (when each photo was taken, which camera), `groups.json`, `groups-sheet.png`, `shoots.json`, `names.json`, `sort-log.json`, `rename-log.json`, `report.html`, `first-look.html`, `previews/`, `groups/`, `from-the-card/` (camera housekeeping set aside, never deleted). They ask you for these; they do not go looking.
