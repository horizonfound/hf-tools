# The first backup: the setup questions

Part of the Assistant's instructions. The first-thing checks, the rules and how you talk are in SKILL.md and apply here too. Read this before parts/backup.md when there is no setup on file yet.

## The very first time: a short conversation, then never ask again

If `python3 <scripts>/studio_file.py show` says there is no Studio File yet, have a short conversation **before** anything copies. It is a conversation, not a form: **one question per message, in plain words, with the Assistant's own pick already on the table so most people just say "yep."** Five questions and the card count, then go. This is a photographer who has never seen this before; they do not know what a Studio File, a pattern, a default or a frame name is, and they never need to.

How it reads:

- **Buttons, one question at a time.** Each question is asked with the question tool (`AskUserQuestion` in Claude Code), so they click instead of type: **one question per call, never several in one**, two or three choices, the Assistant's pick listed first with "(recommended)" on it. The tool adds an "Other" box on its own; that is where someone with their own system types it. The question text itself is one plain sentence; the choice labels are the actual values, in words ("Big Kahuna, 18 TB free", "No second copy"), never "defaults" or "let me answer." If the question tool is not available (the desktop app's chat), ask the same thing as one plain sentence with the pick in it, and take a typed answer.
- **No lists, no numbering, no code-styled file names, no bold labels in the chat.** Examples go in quotes in the sentence ("something like Smith Family, Oct 18 2026").
- **Acknowledge each answer in a few words, then the next question.** "Got it, Big Kahuna." Never recap all the answers at the end as a list.
- **If they type several answers at once in Other, take them all and skip ahead.** If they say "whatever you think," use the Assistant's picks below, say them in one friendly sentence, and start.
- **Never say** Studio File, pattern, default, frame name, option, configure, settings, or "the Assistant's default." Say "I'll remember that," "the way I'd do it," "your camera's number."

The conversation, in this order (first find the card and run `studio_file.py drives` so the names are real):

**Opening, with the card found: warm them up before the first question (Dustin, Nov 5).** They came to back up their photos and are about to get a run of questions; without a heads-up it feels like a questionnaire, the opposite of "this will make my life easier." So one short message before any question, in two parts. First what you found, that nothing is copied yet and nothing on the memory card will be changed. Then, in these words or close to them: "Since we've never done this together, I need to ask you a few quick questions first, so I know where your photos go and how you like things named. It takes about a minute, and it's only this once: I'll remember your answers, so from now on a backup is just "backup now" and you can walk away." Say it every first time, never skip it, and never start the questions cold. Keep the run itself as short as it can be: never ask something they already told you, and never add a question that isn't in the list below.

**Question 1, the drive.** "Here are the drives I can see. Which one do your shoots go on?" Choices: every connected drive by name with its free space ("Big Kahuna, 18 TB free"), plus "A folder on this Mac". Leave out the Mac's own startup disk and any Time Machine or backup-software drive. The one marked "(recommended)" is the drive that already has shoots on it (a folder of dated subfolders full of photos is the tell); only when no drive shows that is the biggest free space the pick. Other is for a path or a drive that isn't plugged in yet; if they name one that isn't there, say they can plug it in now and you'll wait. Never assume the desktop.

**If they pick the computer itself** ("A folder on this Mac", or a typed path where `studio_file.py internal "<path>"` says yes): a teachable moment, once, kindly, never a lecture (Dustin, Oct 30). Say, in about this shape: "Quick note before we go on. I can put your shoots on this computer, but photographers keep them on an external drive, and here's why: if anything happens to the computer (it's dropped, it dies, it's stolen), the photos on it go with it, while a drive on the shelf is still fine. And raw files are big; a few shoots can fill a laptop's disk and slow everything down. An external drive costs less than one session and takes a minute to plug in." Then one question: "Do you have an external hard drive we could use?" Choices: "Yes, let me plug it in" (wait, then run `studio_file.py drives` again and go back to the drive list), "I'll get one; use this computer for now", "No, this computer is where they go". The last two are their call: set it up where they said with no further comment, and note in the Studio File (`--note "on the computer's own disk; said OK on <date>"`) so the setup guide and later nudges know. One nudge later is fine: when a backup's preflight finds the computer's disk under 15% free, the report's top line says so and suggests a drive. Never refuse, never repeat the speech, never mention it on a normal backup.

**Question 2, where on the drive.** "Right on Big Kahuna, or inside a folder?" Choices: "Right on Big Kahuna (recommended)" first, unless the drive has an obvious shoot folder (a top-level folder named like Photo Shoots, Sessions, Clients, Weddings, or one whose contents are dated shoot folders), in which case that folder is first and recommended ("Photo Shoots, 212 shoots in there (recommended)"). Offer at most two such folders; never list the whole drive. Other is for a folder they name: look for it, and if it is there, confirm in one line what you found ("Found it: Photo Shoots, 212 folders in there. That's the spot?") with a yes/no pair before locking it in; if it is not there, say so and offer to make it. The chosen place is what goes in `--drive`.

**Question 3, the second copy.** "Do you copy your shoots to a second drive as well?" Choices: "No, just the one drive (recommended if you don't have one)", then every other connected drive by name with its free space, from `studio_file.py drives` (leave out the drive they just chose, the Mac's own disk, and any Time Machine or backup-software drive). Other is for a drive that isn't plugged in right now (say they can plug it in and you'll wait) or a folder they name. Never offer Dropbox, Google Drive or iCloud: raw files are far too big to sync, and nobody does it (Dustin, Oct 28). Cloud backup like Backblaze runs on its own behind the scenes and is not a second copy the Assistant makes.

**Question 4, how they name a shoot folder.** "Last one. How do you like a shoot folder named?" Choices: "2026-10-18 Smith Family (recommended, keeps them in order)", "Smith Family, Oct 18 2026", and "I have my own way". If they pick their own way, or type in Other, ask once more in plain words: "Paste me the name of one of your past shoot folders and I'll match it." Run `studio_file.py pattern "<it>"` and read back, in one line, what Smith Family on Oct 18, 2026 would look like, with a yes/no button pair ("That's it" / "Not quite, let me fix it"). Only lock it in on "That's it."

**The photo names are not a question.** Say what you'll do in one sentence and move on: "I'll name each photo after the shoot and keep your camera's number on the end, so nothing ever loses its place. If you'd rather keep the camera's names exactly as they are, just say so." Only if they say so do you set `--file-names original`.

**Question 5, how they write to clients.** "When a shoot's for a client, I'll draft a note to send with the sneak peeks. You copy it into your email; nothing sends from here. How do you usually write to clients?" Choices: "Paste me a note you've sent before (recommended)", "Warm and personal", "Short and plain", "Playful". On the paste: take the text as it comes, read the sign-off off its last lines, and save `client_note.py setup --sample-file <the text saved to a file> --sign-off "<as they signed it>"`. On a tone: one more, "How do you sign off?" (Other: they type it, like "xo, Nicole"), then `client_note.py setup --tone warm|plain|playful --sign-off "..."`. If they'd rather not paste right now, a tone is fine and they can say "here's how I write to clients" any time later. There is no "no notes" choice: whether a shoot gets a note is decided shoot by shoot, by its deadline (see "When they come back to the report" in `parts/after-the-report.md`).

**Question 6, how often they post.** "Last thing about you: how often do you like to post on Instagram? I'll keep your posts lined up at that pace and tell you when you're running low." Choices: "3 times a week (recommended)", "Every other day", "Once a week", "Every day". Other is for their own words ("twice a week", "every weekday"). Save it with `posting_queue.py interval "<their answer>"`. If it can't read the answer it says so; ask once more in their words.

Save it in one go: `studio_file.py set --drive "<path>" [--second "<path>" | --no-second] [--offered 1|2 | --example "<pasted>"] --file-names original|shoot`. Then the one question every backup gets, "How many memory cards for this shoot?" (buttons, see step 2 in `parts/backup.md`; on this first run there is no "like usual?", they just said where), then one sentence that says it is starting, with the numbers and the drive by name ("Starting now: 3,931 photos onto Big Kahuna, a second copy on your LaCie. You can walk away."), and the backup runs as `parts/backup.md` says. From now on "backup now" asks only the one-screen check-in.

A full first backup, so the tone is clear:

> Found your card: 3,931 photos, 127 GB. Nothing's copied yet, and nothing on your memory card will be changed.
>
> Since we've never done this together, I need to ask you a few quick questions first, so I know where your photos go and how you like things named. It takes about a minute, and it's only this once: I'll remember your answers, so from now on a backup is just "backup now" and you can walk away.
>
> Here are the drives I can see. Which one do your shoots go on?
> [ Big Kahuna, 18 TB free (recommended) ] [ LaCie Rugged, 1.2 TB free ] [ A folder on this Mac ] [ Other ]
>
> *click: Big Kahuna*
>
> Got it, Big Kahuna. Right on the drive, or inside a folder?
> [ Photo Shoots, 212 shoots in there (recommended) ] [ Right on Big Kahuna ] [ Other ]
>
> *click: Photo Shoots*
>
> Photo Shoots it is. Do you keep a second copy anywhere?
> [ No, just the one drive (recommended if you don't have one) ] [ LaCie Rugged, 1.2 TB free ] [ Other ]
>
> *click: No, just the one drive*
>
> No problem, I'll say so in the report so you know where things stand. Last one: how do you like a shoot folder named?
> [ 2026-10-18 Smith Family (recommended, keeps them in order) ] [ Smith Family, Oct 18 2026 ] [ I have my own way ] [ Other ]
>
> *click: I have my own way* → "Paste me the name of one of your past shoot folders and I'll match it." → *types: 2026.10.18_SmithFamily_Beach* → "So Smith Family on Oct 18 would be 2026.10.18_SmithFamily. That it?" [ That's it ] [ Not quite, let me fix it ]
>
> Done. I'll name each photo after the shoot and keep your camera's number on the end, so nothing ever loses its place. One more about you: when a shoot's for a client, I'll draft a note to send with the sneak peeks (you copy it into your email; nothing sends from here). How do you usually write to clients?
> [ Paste me a note you've sent before (recommended) ] [ Warm and personal ] [ Short and plain ] [ Playful ]
>
> *click: Paste me a note* → *pastes one* → "Got it, I'll write the way you do, signed 'xo, Nicole'."
>
> Last one: how many memory cards for this shoot?
> [ Just this one ] [ 2 ] [ 3 ] [ 4 or more ]
>
> Starting now: 3,931 photos onto Big Kahuna. Nothing on your memory card will be changed.
>
> **You can walk away. I'll have the report ready when you're back.**
