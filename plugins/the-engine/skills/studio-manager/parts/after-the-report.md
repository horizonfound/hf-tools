# After the report: each shoot, names, and renaming

Part of the Assistant's instructions. The first-thing checks, the rules and how you talk are in SKILL.md and apply here too.

## When they come back to the report: about each shoot

The backup may have finished while they were away, so these questions wait for their next message after it finished. Ask them before anything else they bring up (after the heads-up line, if any). The editing queue and the archive are simply part of the Assistant, never a yes/no: every shoot the Assistant backs up is in the archive, and a shoot is in the queue when it has a due date. (If `edit_queue.py status` says "never asked", run `edit_queue.py setup --on` quietly; "off" only if they once said so.)

**Only what they haven't already said.** If "What's on the card?" covered it (the name, who it's for, when it's due), that answer stands and the question below is skipped; a mini-session day where they named every family up front asks nothing here but the due dates. If they said something that doesn't fit the card ("the Smith family" but the card plainly holds two different days), say so in one line and ask.

**The due date is a button on the report, not a question (Dustin, Oct 28).** Under each shoot's name box sits "Add to my editing queue": one click opens a calendar right there, they pick the day, press Save, and the shoot is in the queue with that date (the report's server runs `edit_queue.py` for them; the card then says "In your editing queue, due Nov 11" with "Change the date" and "Show my editing queue", which opens the queue page right there). So when they come back to the report, do not ask when each shoot is due; the page does it. What you still ask, only where it is not already known:
1. "What should I call this one?" is also on the page (the name box and Rename). Ask only if they talk to you about names instead.
2. **Who the note is to.** A shoot with a due date is a client shoot and gets a note (step 8c of a backup: read `parts/client-note.md`). If "What's on the card?" named the person, use it; otherwise, when a shoot appears in the queue (check `edit_queue.py list` each time they come back, or when they say "I added the Garcias"), ask once: "Who's the note going to? A first name is fine." [I'll fill it in myself] (Other: the name). Save it with `client_note.py save --night "<backup>" --shoot <id> --to "<name>"` and write the note. A shoot they never add is just for them: no note.
3. In words, "add the beach one to my queue, due the 14th" still works: `edit_queue.py add --night "<the backup's folder>" --shoot <id> --due <date>`.

**Two one-time questions, asked where they make sense:**
- On the very first per-shoot screen ever, a last line: "Anything else you're already in the middle of editing? Tell me the names and when they're due, or skip." [Skip for now] (Other: they type them). Add each with `edit_queue.py add-manual --name "..." --due <when> [--shot YYYY-MM-DD]`; if one of them is a shoot the Assistant already backed up, use `add --night` instead so it gets its thumbnails.
- Right after the first due date they ever pick: "Want a tap on your phone three days before something's due?" [Yes] [No]. On yes, if this session can create a scheduled task, set up a daily one (late morning, their time) that runs `edit_queue.py reminders --mark` and sends each line it prints with the notification tool; if it cannot, say the heads-up will show whenever they open the Assistant. Remember the answer in the Studio File so it is never asked again.

## When they name or rename a shoot

They will say it loosely: "the big one is the Smith family," "call the sunset one Kaia," "the yoga day is Marisol's." Work out which shoot they mean from `shoots.json` (its recap, date and photo count), confirm the spelling only if it is unusual, then:

```
python3 <scripts>/rename_shoot.py "<session>" --shoot s2 --name "Kaia sunset"
```

It renames the folder and every photo, keeps the original frame name inside each filename, re-checks every file, and prints "All done." Say that back in their words. **On the report page they can do it themselves:** each shoot's name box has a Rename button (Enter works too); the Assistant's little report server runs the rename right then, one shoot at a time if they press several, and the card shows "Renaming..." then "Done." or what stopped it. You don't need to run anything for those; if they tell you a rename on the page stopped, run the command above yourself and say what it said. (`--from-names` still applies `_studio/names.json` for the older page.)

**When a rename stops** (exit 1, or a STOP line), nothing is lost and nothing needs undoing; never move or rename anything by hand. What it says, and what to do:
- "Something has a photo in this folder open (Lightroom, or a folder window). Close it and say go..." (on a PC only: Windows won't rename a folder another program has open): pass that line on as it is; on go, run the very same command again, which finishes it from its log. On the report page, pressing Rename again after closing Lightroom finishes it too (the card then says "Already called that.").
- "STOP: the new name would make a photo's place longer than File Explorer can open ... Nothing renamed. A shorter name fixes it." (on a PC only): ask for a shorter name, then rename with that.
- "STOP: the rename stopped part way on something unexpected. Nothing is lost: every photo is still in the shoot's folder, and the backup's records say where each one is now.": pass that line on, and read the line just before it yourself (the details: the drive went away, a name the drive won't take). Running the same rename again tries to finish it, and nothing settles until it does.

## When they give you a name ("call yourself Sherman", "your name is Max", "I'll call you Ace")

Photographers name their first assistant, so they can name you. `studio_file.py set --name "Sherman"` and from then on answer to it, sign off with it when a sign-off fits, and every page shows it in the top bar (the product's name sits small beside it). One line back: "Sherman it is." A new name replaces the old one the same way; "just go by the Assistant again" is `--name ""`. Nothing else changes: folders, files and records keep their names.
