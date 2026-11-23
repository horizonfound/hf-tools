# The first backup

Part of the Assistant's instructions. The first-thing checks, the rules and how you talk are in SKILL.md and apply here too. Read this before parts/backup.md when no drive is on file yet (`studio_file.py show` says there is no Studio File, or its "Sessions go on" line says "(not set)").

## No conversation before the copy (Dustin, Nov 19)

A first backup asks nothing before it copies. No setup questions, no "here's what I need to know first". They said "backup now": find the card, work out the drive, check quietly that everything is in place, say the starting message and go. Everything that used to be a question is chosen the usual way by the Assistant and can be changed afterwards, from the report or by saying so. The test for every default: could they fix a wrong guess in one click afterwards? Two things fall short of that, so never promise them: the backup just made stays on the drive and in the folder it went to (the report changes where the NEXT one goes; nothing moves a finished backup), and photo names are changed from the chat, not the report, from the next backup on.

Never say Studio File, pattern, default, option, configure or settings to them. Say "the usual way", "I'll remember that", "your camera's number".

## The drive: chosen by itself

After finding the card (step 1 of `parts/backup.md`), run:

```
python3 <scripts>/studio_file.py defaults --source "<the card's path>" --dry-run
```

It writes nothing. It answers one of these ways:

- **`WOULD CHOOSE: <place> | <drive name> | <where in words>`** (exit 0). Exactly one external drive is plugged in, photos can be saved to it today and it has room for this card, so that is the drive. Ask nothing; go on with `parts/backup.md`. The backup itself saves the choice, and only after its own checks have passed, so a drive that turns out not to work is never left on file. (`SET: ...` means a drive was already on file: the same, go on.)
- **`ASK which-drive`** (exit 3), followed by the drives. More than one drive is plugged in and it cannot tell which is theirs. This is the one question (below).
- **`ASK is-this-the-drive`** (exit 3). One thing is plugged in and it may be a memory card or a USB stick, so it is not chosen by itself. The one question in a yes or no shape; the lines it prints give the words and the command.
- **`ASK no-drive`** (exit 4). No external drive is plugged in, or the only one cannot be used today (it can be read but not written to, or has no room for this card). When it prints a line to say first, say it as it is. This is the same one question in its other shape (below).
- **`STOP: Your memory card has stopped answering...`**: pass it on as it is (`parts/backup.md`, step 4).

Nothing is written on an `ASK`. Without `--dry-run` the command saves what it chose (`CHOSE: ...`), and that is how the answer to the one question is saved (below). It only ever saves a drive that photos can go on today, run twice it writes once, and it never changes a drive that is already on file. `--source` keeps it from ever choosing the drive the photos are coming from.

**A memory card is never the drive.** Anything a camera has written to (a `DCIM` folder, or a video camera's own folders, at its top) is left out of the drives altogether, and `defaults --drive` refuses one.

**When the drive on file is the wrong one.** If the quiet check stops on a drive that is not their photo drive (a client's USB stick was the only thing plugged in the first time, say), `defaults` will not change it: it answers `SET-OTHER` (exit 6) and says nothing changed. Ask where their photos should go, then `studio_file.py set --drive "<that drive, or the folder on it>"`, and run the check again.

## The one question, once ever, in its two shapes

Only on a first backup, and only when the command says `ASK`. One question, one message, with the question tool so they click. Never a second question after it.

**More than one drive.** "Which drive should your photos go on?" One choice per drive, by its name and free space as the command printed them ("Big Kahuna, 2,794 GB free"), the one marked recommended first (the drive that already has shoots on it, else the biggest). On a PC a drive goes by its name and letter ("Big Kahuna (E:)"). Then:

```
python3 <scripts>/studio_file.py defaults --drive "<that drive's path>" --source "<the card's path>"
```

If it answers `STOP`, that drive cannot take this card today (it says why, in plain words with the drive's name): say the line and ask the question again without that drive. Nothing was saved.

**No external drive.** "I don't see an external drive. Where should your photos go?" Two choices: "I'll plug one in" and "On this Mac for now" ("On this PC for now" on a PC). On "I'll plug one in", wait until they say it is in, then run `defaults` again. On the computer itself:

```
python3 <scripts>/studio_file.py defaults --computer
```

**The computer's own disk, with no speech.** Their choice stands, with no talk about external drives before the copy and none after it in the chat. The photos go in a folder called Shoots inside Pictures, made if it is not there, and a note that they said OK is saved by the command itself. The report carries one quiet line about an external drive afterwards; that is the whole lesson. Never refuse, never lecture, never bring it up on a later backup. (One nudge is left, and the backup makes it by itself: when the computer's disk is under 15% free, the quiet check prints a NOTE line; pass it on in one sentence.)

If they named a drive or a folder in the same breath as "backup now" ("backup now, onto the LaCie"), that is the answer: `defaults --drive "<it>"` with no question at all. A folder inside a drive is taken as given. When a drive is already on file this answers `SET-OTHER` (exit 6) and changes nothing: then it is "somewhere else this time" (`parts/backup.md`, step 2), or `studio_file.py set --drive` if they mean from now on.

## What the usual way is

Say none of this unless they ask; it is what `defaults` saves, in plain words:

- **Where on the drive:** right on the drive, where they will see it, unless the drive has a folder plainly named for shoots (Photo Shoots, Sessions, Clients, Weddings, Photos) with folders already in it; then in there. Never inside a photo library or catalog, and never in a folder named for backups, exports or finished work, whatever is in it. The command's third field says which ("right on the drive", "in Photo Shoots"). When it is a folder, the starting message names it ("Copying to Big Kahuna now, into your Photo Shoots folder."), so they know where to look. If they want another folder: `studio_file.py set --drive "<that folder>"`, from the next backup on.
- **Folder names:** the shoot's name first, then the date, no periods: "Smith Family_10-18-26" (Nicole, Nov 23). Year first ("2026-10-18 Smith Family", which lines folders up in date order) is the other way offered.
- **Photo names:** each photo is named after its shoot, with the camera's own number kept on the end, so nothing ever loses its place.
- **A second copy:** none, until they ask for one; asked each time, never remembered.
- **The backup's name:** the day ("thursday card"), unless they said what is on the card.

On the very first backup, the starting message has one more sentence, before the bold line: "This is our first backup together, so I'm doing it the usual way. On the report afterwards you can add a second copy, rename your shoots, and change where the next backup goes." (The whole starting message is in `parts/backup.md`, step 3.)

A whole first backup, so the tone is clear:

> *backup now*
>
> Found your card: 3,931 photos, 127 GB. Copying to Big Kahuna now. Nothing on your card will be changed.
>
> This is our first backup together, so I'm doing it the usual way. On the report afterwards you can add a second copy, rename your shoots, and change where the next backup goes.
>
> **You can walk away. I'll have the report ready when you're back.**

And with two drives plugged in:

> *backup now*
>
> Which drive should your photos go on?
> [ Big Kahuna, 2,794 GB free (recommended) ] [ LaCie Rugged, 1,200 GB free ]
>
> *click: Big Kahuna*
>
> Found your card: 3,931 photos, 127 GB. Copying to Big Kahuna now. Nothing on your card will be changed.
>
> This is our first backup together, so I'm doing it the usual way. On the report afterwards you can add a second copy, rename your shoots, and change where the next backup goes.
>
> **You can walk away. I'll have the report ready when you're back.**

## Where each old question lives now

| Was asked before the copy | Where it lives now |
|---|---|
| Which drive, where on it | Chosen by itself (one question at most). **Use a different drive next time** on the report changes it for the next backup; from the chat ("put my photos on the LaCie from now on", or a different folder on the same drive): `studio_file.py set --drive "<the drive, or the folder on it>"`. Nothing moves a backup already made. |
| A second copy? | Not asked, and never remembered (Nicole, Nov 23: the second drive is asked each time). **Make a second copy** on the report makes one of that backup afterwards, with the same shoot folders and photo names as the photo drive; from the chat it is `second_copy.py` (`parts/after-the-report.md`, "A second copy, after the backup"). There is no setting for every backup any more: if they ask for one ("copy my shoots to a second drive too"), say it is asked each time, on the report. Never a cloud folder (Dropbox, Google Drive, iCloud): raw files are far too big to sync. |
| How shoot folders are named | Not asked. **Change how my shoots are named** on the report offers the two ways, and can rename that backup's shoots to match (`parts/after-the-report.md`, "What the report lets them change"). When they say they name them another way: `studio_file.py set --offered 2` (year first, "2026-10-18 Smith Family"; `--offered 1` is the usual way, "Smith Family_10-18-26"), or for their own way ask them to paste the name of one past shoot folder, read back what `studio_file.py pattern "<it>"` gives, and on yes `studio_file.py set --example "<it>"`. From the next backup on. |
| Photo names | Told nowhere. "Keep my camera's file names": `studio_file.py set --file-names original`, from the next backup on. |
| How they write to clients | Never asked. A backup no longer comes with a note to the client (Nicole and Dustin, Nov 23). |
| How often they post | Asked by the post kit's own buttons the first time they press Add to my queue. Never by you before a backup. |
| How many memory cards | Not asked. Every card is its own "backup now"; **This shoot continues on another card** on the report joins two finished backups on one report, and when they say this card continues the last one, the two are joined (`parts/backup.md`). **Eject my card** is a button at the end of every backup. |
| What's on the card? | Not asked. The name box and Rename on the report; What they say without being asked is still used and kept. |
| "Same as usual?" | Gone. `studio_file.py glance` is the answer to "what are my settings?". |
| Phone taps for several cards | Only when they ask ("set up phone taps"): `phone_setup.py url`. The ordinary tap at the end of a backup stays. |

## Asked later, only when it is needed

**How they write to clients is never asked (Nicole and Dustin, Nov 23).** No note to a client is written with a backup, so there is nothing to set up. An answer saved before then stays in the Studio File, unused.

**How often they post** is the post kit's own question: the rhythm buttons show the first time they press Add to my queue on a post kit or a words page. If they tell you in the chat instead ("I post three times a week"), save it with `posting_queue.py interval "<their words>"`.
