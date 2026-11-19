# The v29 build: a backup with no questions, and Nicole's v29 (posts first, the vault)

Nov 19, 2026. Branch `v29`, worktree `/Users/dustindamron/Projects/hf-tools-v29`. Nothing here is pushed, posted or sent.

Two things are combined in one build, by Dustin's say (Nov 19):

1. **The backup asks nothing before it copies.** Dustin: "I really like the zero questions before copy thing. Let's make it simple, give them options after the fact in their report, and then they can customize it as they see fit... Everything else moves to after, yes... just give them options to make little adjustments after the fact, but we get everything on the card, and then they can choose whether they want to do a second backup or not." Nicole felt overwhelmed by the run of questions before her first backup; her test is "is it easier than dragging the photos into a folder by hand?"
2. **Nicole's v29** (her handoff: `/Users/dustindamron/Projects/hf-tools/reference-private/nicole-handoff-v29-2026-11-19/unpacked/Carousel designer and reel picker`, read only: `UPDATE-v29.md`, five mock-up pages in `pages/`, nine screenshots). Posts come first on the home page, and the vault is one post kit for everything. Same rule as every build: identical for the photographer (her words whole), our way underneath. Her mock-ups are data to study. Never run them, never copy her code, never commit them.

Her 2.1 (old reels did not come over) is already in main: `bring_older.py` (e16f046). It is not part of this build.

## How this build runs

Eleven stages, one builder each, one after another in the same worktree. Each stage leaves the project working if the build stops after it. The order puts the small sure things first, then the backup (Dustin's decision of today, and the part that touches photos on a drive), then the vault, which is the biggest and the least certain.

| # | Key | What | Touches photos on a drive |
|---|---|---|---|
| 1 | `recap` | The recap counts each reel once (her 2.2) | no |
| 2 | `home` | The home page, posts first (her 1.2) | no |
| 3 | `backup-zero` | "backup now" with no questions before the copy | yes (the backup's start) |
| 4 | `backup-second-copy` | Make a second copy, from the report, after the fact | yes |
| 5 | `backup-options` | The other options on the report: another card, naming, next drive, the note | yes (renames) |
| 6 | `vault-core` | The vault as a real post kit whose photo list is references | no |
| 7 | `vault-page` | My vault first on the post kits list, and the vault's own post kit page | yes (+ Add a shoot copies) |
| 8 | `vault-search` | Photo descriptions beside each kit, and the search rule | no |
| 9 | `vault-reel-clips` | The vault's reel page: the four kinds, clips from every shoot, clip search | no |
| 10 | `vault-reel-photos` | The vault's reel page: photos folded by shoot, photo search, the two chat lines | no |
| 11 | `vault-everything` | See everything in it: tap to play, Use it in a reel, Remove from my vault | no |

**Every stage ends with:** a new or extended test in `tests/` that fails without the change; the test added to `.github/workflows/check-pc.yml` (then `python3 tests/workflow_check.py`); `python3 tools/check_pc.py` and `python3 tools/check_plugin.py` clean; `python3 tests/skill_text_check.py` passing when instructions changed (bring its expectations along where an instruction changed on purpose, and say which); a short **"Built"** note appended to this file under the stage's heading (what was built, counts tested, what is NOT tried, every choice for Dustin and Nicole); and ONE commit with a plain-words message ending `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.

**Rules every builder holds to** (from CLAUDE.md; the ones that bite here):
- Python standard library only, Python 3.9 and 3.12, no Mac-only call outside `this_computer.py`.
- A page never sends or shows a path. A shoot is its folder name, a photo its number, a drive its name. Every POST behind the pickers' same-page-only guard (`arrange.guard`). Text reaches a page as text.
- Her words whole in a `WORDS` table; ours in `OUR_WORDS`, each a draft. No em dashes in page copy, no serif, "your assistant" never "Claude", "you"/"they" never she/he.
- Tests: a scratch `STUDIO_HOME`, pretend kits and backups (`tests/fake_kit.py`, `tests/fake_night.py`), `STUDIO_NO_WINDOWS_FOR_TESTS` in any test that starts a page server, never the real `~/.studio`, `/Volumes`, CapCut, Calendar, or ports 8790 to 8792 and 8799. Hidden-Chrome tests one at a time: `python3 tests/guard.py 3000 python3 tests/<test>.py`; video tests under `guard.py 800`.
- When her handoff is on this computer a test compares her words with her own page, both ways, the way `tests/home_v28_check.py` and `tests/reel_page_check.py` find it (`reference-private/` beside the main checkout); it skips with a SKIP line where the handoff is not there (GitHub).
- Behaviour changes go in the part (`skills/studio-manager/parts/`), not the core. A new kind of request gets a row in the core's table. The skill's description is 1,016 characters and must stay under 1,024: do not touch it.

Shorthand below: `S/` is `plugins/the-engine/skills/studio-manager/scripts/`, `R/` is `plugins/the-engine/skills/assistant-make-a-reel/scripts/`, `P/` is `plugins/the-engine/skills/studio-manager/parts/`. Line numbers are as of e16f046 and are pointers, not promises.

---

## Stage 1. `recap`: each reel counted once

Her 2.2: the recap said 79 reels for November because every make counted. "Counting each reel once would be closer to the brag Nicole wants: what she actually made." This also answers question 1 of the v28 notes.

- `S/wrapped.py:85`: `COUNT_EACH_MAKE = False`. The once-per-reel branch is already written (about line 216). The hours saved follow by themselves (same counts). No word changes.
- Update the comment on the switch (who decided, when), and `P/hello.md` / `P/where-things-live.md` only if they say every make counts.
- Test: `tests/wrapped_check.py` already tries both ways; make the default expectation "once", and add one case that fails if the switch is turned back (three makes of one reel in one month read "1 reel made", singular).
- Also check the home page's recap chips (`wrapped.chips()`) follow.

## Stage 2. `home`: the home page, posts first

Her 1.2, screenshot `01-home-posts-first.png`, page `pages/home-preview.html`. Server-drawn as now, in `S/home.py`.

Top to bottom:
1. **The hello**, as it is.
2. **Turn your shoots into posts**, big, the first thing under the hello: one wide white card. Title "Turn your shoots <em>into posts</em>" (`s3_n`, already hers). Under it, exactly: "Turn your shoot into reels, carousels, stories, and captions." (`s3_p`, already hers). A dark button that is a plain link to `/make-posts`: **"Create your post kits →"** when there are no post kits, **"See all my post kits →"** once there are some. Beside it the "what's going on now" box as today: "Newest: {short}" with "{n} post kit(s)" under it; none: "No post kits yet" / "Start with any finished shoot". **No list of post kits on the home page.**
3. **My posting queue**, a full-width card: "My posting <em>queue</em>", "Your posts ready to go, and how your grid will look.", "Open my posting queue →", with its now-box as today.
4. A small caps heading **"Also in your Assistant"**, then two smaller cards side by side: "Back up <em>a card</em>" / "Copies your card to your drive, checks every photo, and sorts it into shoots." and "My editing <em>queue</em>" / "The shoots you need to edit and when they're due.", each with the same now-box as today (a card that is in, the last backup; shoots waiting, the next due). In her screenshot these two have no button label; the whole card is the press.
5. **The monthly recap card** and the Your year bar, unchanged.

What goes: the step numbers 1 to 4, the heading "Your workflow" (`wf_h`), the line "Start wherever you are…" (`wf_say`), and the `s1_go`, `s2_go`, `s3_go` labels. `STEPS` and the `.flow4` layout in `page_html` (about lines 1048 to 1122, CSS near 706) become: one big section, one wide card, the "also" row. `now_boxes` stays. Clicks are still recorded with the same `data-item` names (`posts`, `posting`, `backup`, `queue`), so `home.py pending` and the hello's buttons keep working. New `WORDS` keys: the two button labels and "Also in your Assistant". Take every line from her page; her page wins if this list and her page differ.

Also in this stage:
- With the steps no longer numbered, the eyebrows "Step 1 of your workflow" (`home_base.WORDS["b_eyebrow"]`) and any other "Step N of your workflow" on the Back up a card, editing queue and posting queue screens are stale: grep for "of your workflow" and take each out (leave `m_eyebrow` on the Make posts screen for stage 7, which reworks that screen). List what was removed.
- `tests/home_v28_check.py` holds the four-step layout: bring it along, and write `tests/home_v29_check.py` (hidden Chrome, pretend kits): the order of the sections; the button reads Create with no kits and See all with some; no kit names listed on the page beyond the one Newest box; the two small cards open what they opened before; her words both ways when her handoff is there; phone width has no sideways scroll.
- `P/hello.md`: the description of the home page, and what a press on each card means (unchanged in substance).

Left as hers says: "the home page still needs work and she'll keep tweaking it", so this is the direction, not final pixels.

---

## The backup with no questions (stages 3, 4, 5)

### What a photographer sees

**"backup now" with a card in.** No setup conversation, no "Same as usual?", no "How many memory cards", no "What's on the card?", no folder naming, no client-note voice, no second-copy question, no posting rhythm, no phone-tap page. The assistant finds the card, knows or picks the drive, checks quietly that everything is in place, says:

> Found your card: 3,931 photos, 127 GB. Copying to Big Kahuna now. Nothing on your card will be changed.
>
> **You can walk away. I'll have the report ready when you're back.**

and goes. On the very first backup one sentence is added before the bold line: "This is our first backup together, so I'm doing it the usual way. You can change any of it on the report afterwards."

**The one question that may be asked, once ever: which drive.** Only on a first backup (no drive on file), and only when the assistant cannot tell:
- **Exactly one external drive plugged in:** no question. That drive is it.
- **More than one:** "Which drive should your photos go on?" with each drive by name and free space, the recommended one first (the one that already has shoots on it, else the biggest), as `studio_file.py drives` lists them.
- **None:** "I don't see an external drive. Where should your photos go?" [I'll plug one in] [On this Mac for now] ("On this PC for now" on a PC). No speech before the copy (the Oct 30 teachable moment moves): if they choose the computer, the report carries one quiet line afterwards (stage 5) and the note goes in the Studio File as before.

**The defaults, written to the Studio File by the Assistant itself the first time** so every later backup is the same:
- **Where on the drive:** the folder the old setup would have recommended first: the drive's one obvious shoot folder when it has one (`studio_file.shoot_folders`, its top hit), else right on the drive. On the computer itself: a folder called `Shoots` inside Pictures (`this_computer.known_folder`), made if it is not there.
- **Folder names:** year first, "2026-10-18 Smith Family" (`OFFERED[0]`; Dustin, Oct 24).
- **Photo names:** named for the shoot with the camera's number kept (`file_names: shoot`), as today.
- **Second copy:** none.
- **The backup's name:** the weekday ("thursday card"), as today, unless they said what is on the card without being asked ("backup now, it's the Smith family"), which is still used for the name and kept word for word (`client_note.py told`).

**The preflight still runs, silently** (`night.py --check`), and speaks only when something is wrong: the card stopped answering, the drive is missing or full, the card is already safe (the ledger), the name is taken by another card, the copy would land on the card itself, and the PC's drive-letter checks. Every one of those stops and its words stay exactly as they are.

**Everything that was a question is an option afterwards, on the report**, each a button with its result shown right beside it (the Oct 30 test). The test for a default: could they fix a wrong guess in one click afterwards?

| Was asked before the copy | Where it lives now |
|---|---|
| Which drive, where on it | Chosen by itself (one question at most). **Use a different drive next time** on the report. |
| A second copy? | **Make a second copy** on the report (stage 4), with "after every backup" as a tick box. |
| How shoot folders are named | **Change how my shoots are named** on the report (stage 5). |
| Photo names | Told nowhere, changed in the chat ("keep my camera's file names"), from the next backup on. |
| How they write to clients | Asked the first time they ask for a note (`P/client-note.md` already has that path). |
| How often they post | Asked by the post kit's own chips on the first Add to my queue (already there). |
| How many memory cards | **This shoot continues on another card** on the report (stage 5); **Eject my card** as a second button at the end of every backup. |
| What's on the card? | The name box and Rename on the report; the note when they ask for one. What they say unasked is still kept. |
| "Same as usual?" | Gone. `studio_file.py glance` stays as the answer to "what are my settings?". |
| Phone taps for several cards | On ask ("set up phone taps": `phone_setup.py url`). The ordinary tap at the end of a backup stays. |

When they come back to the report the assistant asks nothing by itself either: no "who's the note going to", no "anything else you're editing", no "want a tap three days before". Each is a button or something they say.

Kept exactly: nothing starts without "backup now"; stop loudly; the card is never touched; the already-safe message; the walk-away line last and in bold; sneak peeks picked by themselves; the Show the report button at the end; the tap at the end.

### Stage 3. `backup-zero`

**Scripts.**
- `S/this_computer.py`: a tests' switch for the drives, since tests may never look at `/Volumes`: `STUDIO_DRIVES_FOR_TESTS` names a JSON file with a list of pretend volumes in the shape `volumes()` returns (path, name, shown, total, free, system, removable, id). When set, `volumes()` returns that list and nothing else. Only a test sets it.
- `S/studio_file.py`: a new function `choose_defaults(drive=None, computer=False, write=True)` and command `studio_file.py defaults [--drive "<path>"] [--computer] [--dry-run]`.
  - A drive already on file: prints `SET: <place> | <drive name>` and changes nothing.
  - None on file: reads `drives()`. Exactly one: chooses it. `--drive` given (after the one question): uses it. `--computer`: `<Pictures>/Shoots`.
  - The place on a chosen drive: its top shoot folder from `shoot_folders()` when there is one, else the top of the drive. (A `--drive` that is already a folder inside a drive is taken as given.)
  - Writes `drives.session` (through the same code path as `set --drive`, so a PC's drive facts are kept), `naming` = `OFFERED[0]` with `file_names: "shoot"` only when no naming is on file, leaves `drives.second` alone, and adds a note ("chosen by itself on <date>", or "on the computer's own disk; said OK on <date>" for `--computer`). Prints `CHOSE: <place> | <drive name> | <where in words: "in Photo Shoots" or "right on the drive">`.
  - More than one drive and no `--drive`: prints `ASK which-drive`, then the drives as `drives` prints them, exit 3, nothing written. No drive: prints `ASK no-drive`, exit 4, nothing written.
  - Run twice it writes nothing the second time. It never changes a drive that is already on file.
- `S/night.py` (about lines 338 to 349): with `--source` and no drive on file, call `studio_file.choose_defaults()` instead of stopping. Chosen: carry on, and say one line ("First backup: your photos go to Big Kahuna, in Photo Shoots."). With `--check`, choose with `write=False` and say what would be chosen. Only when it cannot choose does it still exit 5, with new words that name the one question (which drive, or no drive) and the `studio_file.py defaults --drive` command. Exit 5 keeps its number and now means "one question: which drive". Nothing else in `night.py` changes in this stage.
- `S/backup.py:379`: the help text for `--second` says "a second drive", not a cloud folder (Oct 28).

**Instructions.**
- `P/first-backup-setup.md`: rewritten short. Title: the first backup. What it now holds: no conversation before the copy; `studio_file.py defaults` and its three answers; the one question and its two shapes; the computer's-own-disk choice with no speech (the note is saved, the report says the quiet line); the defaults in plain words; the table above ("where each old question lives now"); and a short "Asked later, only when it is needed" section that keeps the exact wording of the client-voice question (old Question 5) for `P/client-note.md` to use and says the posting rhythm is the post kit's chips. The long sample conversation is replaced with the new, short one.
- `P/backup.md`, "When they say backup now": step 1 find the card (as is: two cards, no card, a mixed drive still ask, since those are "cannot tell" cases); step 2 becomes "the drive": `studio_file.py defaults`, the one question only on `ASK`; the three-question screen, the glance, Change something, the cards question, "What's on the card?" and the phone-tap page all go. The preflight (step 4) runs before the starting message and is silent unless it stops. The starting message is the new one above. The many-cards block becomes: each card is its own "backup now"; after any backup the closing box has **Show the report** and **Eject my card**; "Card 2 is in" still works when they say it; cards are joined on the report afterwards (stage 5), and `--with` stays for when they say up front that this card continues the last one. Steps 6 to 9 stay. Step 8c (the note) is written only when they said who it is for, or ask.
- `P/after-the-report.md`: the section "When they come back to the report" asks nothing by itself; it lists what the report offers and what they can say. The two one-time questions and "Who's the note going to?" become things asked only when they ask for the thing (a note needs a name: one question then).
- `P/hello.md`: the first hello with a card in loses "I'll ask a few quick questions first"; it says the backup starts and they can walk away. The "Want to dive in?" explanation of a first backup says no questions.
- `S/home_base.py`: `WORDS["b_s2_small"]` ("Your assistant asks a quick question or two, then you can walk away…") is Nicole's and is no longer true. It moves to a line of ours in `OUR_WORDS` (draft): "Your assistant finds your card and starts copying. There's nothing to answer first, so you can walk away. The report is ready when you're back, and it shows up below." Listed for Nicole.
- `P/on-a-pc.md`: the drive-letter stops stay (they are "something is wrong"); fix the pointer at line 102 that names a heading that does not exist; the old "Onto Big Kahuna (E:), like usual?" stays only for a Studio File with no drive name on a PC.
- `SKILL.md`: the table's backup row still sends a first backup through `P/first-backup-setup.md`; reword only if it speaks of setup questions. Do not touch the description.

**Test: `tests/backup_zero_check.py`** (no browser; both Pythons; scratch `STUDIO_HOME`, pretend drives through the new switch, a pretend card folder with a `DCIM` made in a temp folder).
- No Studio File, one pretend drive: `defaults` chooses it, writes year-first naming and shoot photo names, no second copy; `night.py --source <card> --check` says ready and writes nothing; `night.py --source <card>` copies (run it to its first stop, exit 4, the look) into the chosen place. With the change taken out it exits 5.
- A pretend drive with an obvious shoot folder: the place is that folder.
- Two pretend drives: `defaults` and `night.py` exit with the which-drive words and nothing is written; then `defaults --drive` writes and the backup runs.
- No drive: the no-drive words; `--computer` chooses `<a pretend Pictures>/Shoots` (point `known_folder` at a temp folder by its own test seam, or pass the place in).
- A Studio File already set: nothing changes, byte for byte.
- `defaults` twice writes once.
- The instructions: `backup.md` no longer holds "Same as usual?", "How many memory cards for this shoot?" or "What's on the card?"; `first-backup-setup.md` holds no numbered questions before the copy; the starting line and the bold walk-away line are there (extend `tests/skill_text_check.py`).
- `tests/glance_check.py` and `tests/backup_safety.py` still pass (the glance command and the copy are untouched).

### Stage 4. `backup-second-copy`

A second copy made after the fact, from a button on the report. This stage copies photos to a drive: it is built with the care of `backup.py` and gets reviewers.

**What it is.** `S/second_copy.py "<backup>" --to "<a drive or folder>"`: makes a second copy of THIS card's backup on another drive. One layout always, the card's own: `<to>/<the backup's folder name, "2026-11-19 thursday card">/<each file at its path on the card>`, with a copy of the records' manifest in a hidden `_studio` there, exactly what `backup.py --second` leaves (Dustin, Oct 28: the second copy stays as the card wrote it). It is never sorted, settled or renamed.

**Where each file is read from, decided per file:**
- **The card, when it is still in and unchanged.** `cards.check(<card>)` must say the ledger holds this card for this very backup's records. Then each file is read from the card at its card path.
- **Otherwise the verified copy on their drive.** The file's place now is found the way the settle does it (`settle.backup_hashes`, the index's `original` → `file`, and the set-aside leftovers), wherever the sort, a rename or the settle has put it.
- The same run may use both (the card pulled half way: the rest comes from the drive), and a later run finishes a run that stopped.

**What is checked. "Verified" means a hash matched.** Each file is copied the way `backup.copy_with_hash` does it (hash while writing to a `.studio-partial` file, rename into place, read the copy back). Three hashes must agree: what was read, what was read back, and what the backup's manifest recorded for that file. For a video clip the backup turned upright, the manifest holds two: the card's own (`card_sha256`) is the one to match when reading the card, the turned one (`sha256`) when reading the drive. A file whose source no longer matches the backup's record is a problem (the card or the drive's copy has changed): it is not counted, the run says which, and nothing is written over.

**Never overwrite, never delete.** A file already at the destination is compared, never replaced: identical means "already there"; different is a problem that stays on the report (`backup.py`'s `DIFFERS` rule). Only this run's own failed partial copy may be written again (`ours_to_redo`, with its `left` identity). Reuse `backup.py`'s functions (`copy_with_hash`, `sha256_of`, `identity`, `ours_to_redo`, `onto_itself`, the room check) by import; do not copy them.

**Refused before a byte is written** (`--check` runs only this): the place is the card, the same drive the photos are on, or inside the backup (`backup.onto_itself`); not enough room (the manifest's sizes plus a margin, per physical drive as `night.py` checks it); the backup is not finished, has problems, or was a sample; the records cannot be found (`where.locate`); a second copy of this backup is already complete (it says so and where); another second copy is running (its own lock, `this_computer.try_lock`, on `~/.studio/second-copy.lock`).

**Records, log first.** Progress lives in its own file in the backup's records, `second-copy.json`, written whole (temp file then `this_computer.replace`) before the first byte and after every file: `{to, to_name, started, state: "copying"|"done"|"stopped", done, total, bytes, from_card, from_drive, files: {<card path>: {ok, from: "card"|"drive", note, left}}, problems: [...], line}`. **The backup's `manifest.json` is touched once, at the very end, only when every file is copied and checked:** `manifest["second"] = <folder>` and each file's `second: {"ok": true}` in one whole write, with the manifest before kept beside it once as `manifest.before-second-copy.json`. Until that moment the manifest says there is no second copy, so a copy in progress or one that stopped can never switch off "Card safe to format" (`home_base.backup_status` ties safe to `second.ok` whenever `manifest["second"]` is set). Then the manifest copy goes to `<second>/_studio/manifest.json`, the folder is hidden, and `first_look.py` / `report_page.py` are rebuilt.

**Safe to run twice; safe to cut off.** Every file already recorded ok and still there at its size is skipped. A run with nothing to do says so. It runs under the keep-awake helper (`this_computer.awake_command` / `awake_while`). Exit codes: 0 done, 1 problems, 2 refused before anything was written, 3 stopped part way (run again).

**Honest words.** When any file came from the drive, the done line says so: "Second copy made on LaCie Rugged: 3,931 files, every one checked. It was made from the copy on Big Kahuna, since the card wasn't in." When turned clips came from the drive: "5 video clips are the upright ones from your drive." It never says more than was checked.

**The report's button** (`S/serve_report.py`, `S/report_page.py` or `S/first_look.py`; all words ours, in `OUR_WORDS`, drafts):
- A section under the shoots, heading **"Anything you'd like to change?"**, line: "Your photos are safe either way. These are here if you want them." (Stage 5 adds the other options to this section.)
- **Make a second copy** → a panel right there: "Which drive should the second copy go on?" then each drive that is plugged in by name and free space ("LaCie Rugged, 1.2 TB free"), leaving out the drive the photos are on, the card, the computer's own disk and Time Machine; **Look again**; a tick box "Do this after every backup"; **Make the second copy**. No other drive: "I can't see another drive. Plug one in, then press Look again."
- Running, beside the button: "Copying to LaCie Rugged: 240 of 3,931." and, while files are read from the card, "Keep your card in until this is done." Done: the honest line above. Stopped: the problem in plain words and "Nothing was removed. Press Make a second copy to carry on." (no paths, no Python words).
- A backup that already has a second copy shows "Second copy made on LaCie Rugged." in place of the button.
- Routes, all relative so they work inside `/card/N/`: `GET second-drives` (names, free space, an index; never a path), `POST second-copy {drive: <index>, name: <its name>, always: bool}` behind the same-page-only guard (the server lists the drives again and the name must match the index), `GET second-status` (reads `second-copy.json` and whether the job is alive; the page polls it and picks a running job up again after a reload).
- The job is started detached (`this_computer.popen_detached`) so it outlives a page server that starts over; one at a time on this computer.
- "Do this after every backup": on success runs `studio_file.py set --second "<place>"`.
- `S/night.py`: when the second copy on file comes from the Studio File (not `--second` typed for this run) and that drive is not plugged in, the backup no longer stops: it carries on with one copy and the report's top says "Your second drive wasn't plugged in, so there's one copy for now. Plug it in and press Make a second copy." A `--second` given for this run still stops, as today.
- `S/eject_card.py`: refuses while a second copy is reading that card, with one plain line: "A second copy is still being made from this card. It won't be long." It promises nothing else. (If the card is pulled anyway the copy stops in plain words, and the next press of Make a second copy finishes it from the drive.)
- From the chat: "make a second copy of the beach backup onto LaCie" → `second_copy.py "<backup>" --check --to …`, then run it in the background; a row in the core's table and a section in `P/after-the-report.md`.

**Test: `tests/second_copy_check.py`** (no browser for the script; one small server part with `STUDIO_NO_WINDOWS_FOR_TESTS`; a pretend finished backup from `tests/fake_night.py`, a pretend card folder, temp folders for the drives; both Pythons). At least:
- from the card: every file lands at its card path, hashes match the manifest, the manifest is changed only at the end, the report says second copy made;
- from the drive after a settle and a rename: the same layout, the same hashes, the done line says it came from the drive;
- a turned clip: matched against `card_sha256` from the card and `sha256` from the drive;
- cut off after N files (kill the process), run again: finishes, nothing copied twice, no partial files left;
- the card pulled half way (the pretend card folder removed): stops in plain words; the next run finishes from the drive;
- a file already at the destination and different: never written over, a problem, the manifest not changed, "safe to format" of the backup unchanged (`home_base.backup_status` before and after);
- a source file changed since the backup: a problem, not counted;
- refused: onto the same drive, onto the card, inside the backup, not enough room (a faked free-space answer), a sample backup, an unfinished backup, a second run while one holds the lock;
- run twice: the second writes nothing;
- the page: the POST is refused from another Origin; a drive index whose name does not match is refused; the status line never carries a path.
- Each guard taken out in a scratch copy, and the test seen to fail, for at least: the three-hash check, never-overwrite, the manifest-only-at-the-end rule, the lock.

### Stage 5. `backup-options`

The rest of "Anything you'd like to change?" on the report, and the same-page-only guard for the whole report server. Words ours, drafts, in `OUR_WORDS`. Button labels echo their question.

1. **This shoot continues on another card.** Panel: when other finished backups exist (from the card ledger, newest first, the last 30 days, at most 8, not ones already on this report): "Which backup is the other card?" with each as a button ("tuesday card · Nov 17 · 1,840 photos"), then **Put them on one report**. None: "Back up the other card first: put it in and say backup now. Then come back here and pick it." Route `GET other-backups` (name, day, count and an index; never a path) and `POST link-card {backup: <index>, name}`: the server runs `shoot_report.link([older, this])` (the existing machinery), re-reads the link (move the block in `serve_report.main()` that fills `Handler.cards` into a function and call it again), and the page reloads into the shoot's page. Result beside the button: "Done. Both cards are on one report now." Linking joins reports only; each card's shoots stay in their own folders (say so in one quiet line: "Each card's photos stay in their own folders.").
2. **Change how my shoots are named.** Panel: "How should a shoot folder be named?" with the two offered ways shown with one of this backup's own shoot names and its date ("2026-11-19 Black-sand beach", "Black-sand beach, Nov 19 2026"), the current one marked; a tick box "Rename this backup's shoots to match" (ticked); **Save**. Under it: "Name them your own way? Copy this into the chat:" with "Change how my shoots are named" and Copy. `POST naming {offered: 1|2, apply: bool}` → `studio_file.py set --offered N`, then, when ticked, each of this backup's shoots goes through the report's existing rename queue (`Renames`, one at a time, `rename_shoot.py --shoot <id> --name "<its name now>"`), which re-reads the pattern. **A rule for this builder:** first prove on a pretend backup that `rename_shoot.py` renames a shoot whose name is the same and whose pattern changed. If it answers "already called that", do NOT change the mover's planning today (it has four near-misses on record): the option then changes the naming from the next backup on, the tick box is not drawn, and the page says "Your next backup's shoots will be named like 2026-11-19 Smith Family." Report which happened.
3. **Use a different drive next time.** Panel: "Where should your next backup go?" with the plugged-in drives by name and free space (not the card, not Time Machine; the computer itself is offered last as "This Mac" / "This PC"), **Save**. `POST next-drive {drive: <index>, name}` → `studio_file.choose_defaults(drive=…)`'s place rule, written with `set --drive`. Result: "Saved. Your next backup goes to LaCie Rugged. The photos from this backup stay where they are." Nothing is moved.
4. **A note to the client, per shoot.** In each shoot's block (near Add to my editing queue): **Write a note to my client** shows, right there, "Copy this into the chat:" with "Write a note for the <shoot's name> shoot" and Copy. No form. The assistant asks who it is for and (the first time ever) how they write to clients, as `P/client-note.md` already says.
5. **The quiet line when photos are on the computer's own disk** (`studio_file.on_internal_disk` of the backup's place), once, under the where-card: "Your photos are on this Mac's own disk. An external drive is safer: if anything happens to the computer, the photos on it go too. Plug one in and press Use a different drive next time." Never before a copy, never a second time on the same report.
6. **The guard.** Every POST of the report server (`/rename`, `/queue`, `/peeks-again`, `/peeks-choose`, `/names` and the new ones) goes through the pickers' same-page-only check (`arrange.guard`, or the same test of Origin and Sec-Fetch-Site), and stays working inside `/card/N/` frames. A check that a POST naming another Origin gets 403 and changes nothing.

Instructions: `P/after-the-report.md` gets "What the report lets them change" (each option, what it does, the chat way to do the same: `shoot_report.py link`, `studio_file.py set --offered/--example/--file-names/--drive`, `second_copy.py`), and the core's table gets rows for "this shoot was on two cards", "change how my shoots are named", "use a different drive", "make a second copy". `P/where-things-live.md`: `second-copy.json`, `manifest.before-second-copy.json`.

**Test: `tests/report_options_check.py`** (a pretend backup or two from `fake_night.py`, the report server on a scratch port with the no-windows switch, pretend drives through `STUDIO_DRIVES_FOR_TESTS`; a hidden-Chrome part for the panels under `guard.py 3000`): each option's route does what it says and shows its line beside its button; linking two pretend backups gives one report with both cards and survives a reload; the naming option either renames (folders and records follow, checked by `rename_shoot`'s own proof) or says "next backup" (whichever was built); next-drive changes only the Studio File; the note line carries the shoot's name as text (a name with `<b>` and quotes stays text); every POST is refused from another Origin; no response body or page line holds a path. `tests/report_v26_check.py` and `tests/shoot_report_check.py` still pass.

Not in these stages (said under "Not built" below): moving a finished backup's shoots to another drive or folder; merging two cards' photos into one shoot folder; a phone-tap option on the report; the where-card's old habit of printing a folder's path.

---

## The vault (stages 6 to 11)

### What it is, in her words

"The vault is **one post kit for all your footage and photos**. It's not a separate tool, and **it's not a picker you start from.**" In the post kits list My vault is always the first card, set apart. Inside, it is the same post kit page as any shoot: the same Reels, Carousel and Stories cards, the same reel page, designer, words page and Add to my queue. "The only difference is that it draws from everything in the vault instead of one shoot." A strip at the top shows what is in it, with **+ Add a shoot**, **+ Add clips** and **See everything in it**. Searching is what makes it worth having ("I need me on the computer… a dream"), and the search lives where the reel is made.

### The design: a real kit folder whose photo list is references

Every page finds a kit only through `arrange.kit_by_name` (a real folder in Your Content holding `.kit/kit.json`). So the vault is a real folder and everything that works on a kit works on it with no new routing.

- **The folder:** `Your Content/My vault/`, with `.kit/kit.json` `{"name": "My vault", "vault": true}`, its own `Photos`, `Footage`, `Music`, `Talking`, `Carousel`, `Stories`, `Reels` folders like any kit. It is made only by a command or the first guarded press of Open the post kit, never on a page load. If a shoot folder is already called "My vault", the vault takes "My vault 2" (and so on); which folder is the vault is found by the `vault: true` mark, never by the name.
- **Who is in it:** every post kit, by itself, archived or not (archiving only tidies the list; it must never change a reel). Photos and videos put into the vault's own `Photos` and `Footage` folders are "Added to my vault". **The vault only ever reads another kit. It writes nothing into one.**
- **Its numbered list is references.** A new `S/vault.py` is the one writer of the vault's `.kit/sheet.json`. A row is the usual `n, file, w, h, way` plus `kit` (the member kit's folder name, or `""` for the vault's own Photos) and `src` (that kit's own number for the photo). No photo is copied to be in the vault.
- **Numbers never move** (the v27 promise). `.kit/vault.json` keeps `{"numbers": {"<member folder>#<src>": n, "own:<file name>": n}, "next": N, "out": {...}}`. A photo keeps its vault number for good; a photo that is gone (its kit's photo gone, or removed from the vault) keeps its number unused and comes back to it. The list carries `added`, `gone`, `back` and `retired` the way `reel.py sheet` writes them, so every reader behaves as with a kit.
- **Three small branches make the rest work:**
  1. `arrange.photo_path(kit, rec, row)`: a row with a `kit` field resolves through the member kit (its `photos_dir` and the row's file name). One level only: a member is never the vault. A row without the field is exactly as before.
  2. `reel.kit_numbers(kit, folder)` (`R/reel.py`): for a list marked `vault`, each row's path is its own (the member's photos folder is read from the sibling kit's record), instead of joining every name to one folder.
  3. `kit.sheet(kit)` and `reel_page.relist_if_changed(kit)`: for the vault they call `vault.relist(kit, quick)` / `vault.changed(kit)` (the members' list stamps and the vault's own Photos listing compared with what the list was made from).
  Plus the places that read one photos folder directly: `kit.carousel_plan` (about 913), `kit.facts` (1642), the counts in `home_base.kits` (657) and `kit_thumb` (775), `wrapped.py` (277), `posting_queue.py` (581), `reel_page._make` (3265) and `open_photos` (3757). Each either goes through the rows (`arrange.sheet_rows` + `photo_path`) for a vault or is left out for a vault with a reason.
- **The vault is left out of every list of shoots:** `posts.kits(h)` skips a kit whose record says `vault` unless asked (`posts.kits(h, vault=True)`), so the Make posts list, the home page's Newest and count, and the recap's shoots and top shoot never show it. Its reels, carousels and stories still count in the recap.
- **Small copies:** the vault makes its own (`<vault>/.kit/previews/`, by vault number) the first time a page asks. About half a minute and 15 MB for 300 photos. Sharing the members' copies is a later saving.
- **Clips** stay where they are too (stage 9): the vault lists every member kit's videos beside its own and keeps its own stills and small copies of them under its own `.kit`.

Why not the other ways: a folder of links (the reel page and `list_videos` skip links on purpose, and a PC needs special rights to make them); hard links (many photo drives are exFAT, which has none, and a re-export leaves the link on the old picture); full copies (doubles every finished photo, the very thing Nicole flagged about the drop box); a virtual kit (every record writer wants a folder to hold `reel-page.json`, designs, words and the queue id).

### Stage 6. `vault-core`

Build `S/vault.py` and the branches above. No page changes in this stage beyond what the branches need; photos only.

- `vault.py` functions: `find()` (the vault's folder or None, by the mark), `ensure()` (make it: the folder, its record and empty list, under a lock; twice makes one), `is_vault(kit_or_rec)`, `members()` (every other kit with a record, newest first: folder, name, date, photo count from its own list), `relist(kit, quick=False)` (rebuild the reference list with fixed numbers; runs `kit.py sheet --quick` logic for a member that has photos and no list yet by calling `kit.sheet(member, quick=True)`; writes whole, old list kept as `sheet.prev.json`; not quick also draws the numbered contact sheets with the reel script's own `make_sheets` and prints their paths), `changed(kit)`, `out(kit)` / `set_out(kit, what, key, on)` (the removed list; stage 11 uses it), `rows_by_group(kit)` (for the pages: `"added"` first, then each member).
- Commands: `vault.py show` (where it is, how many shoots, photos; never made by `show`), `vault.py ensure`, `vault.py relist [--sheets]`, `vault.py members`.
- A name clash inside the list: two members may both hold `IMG_0001.jpg`; rows are told apart by `kit` + `src`, never by name. Check every reader that keys on a file name (`reel._photo_key`, `arrange._older_copy`, the page's own maps) and make the vault safe there or name what is left.
- A member whose drive or export folder is not there: its rows stay on the list (the pages already show a photo they cannot reach as missing and use an older small copy); nothing is retired because a drive is unplugged. Only a photo its own kit's list calls gone is gone.
- The first design in a vault's carousel designer is blank (the designer otherwise makes "one photo a slide" from a pick; in the vault nothing is picked until they ask). The kit's fan animation and the hello may use the vault like any kit or skip it; say which.
- Wherever a piece's "who" is made from the kit's name (the home page's lines, the hello's "{who}'s reel", a reminder's title, the queue's piece names), the vault reads "My vault" whole ("My vault reel is waiting", "Post your My vault reel today"), never "My's reel". One helper, used by each.
- `P/where-things-live.md`: the vault's folder and records.

**Test: `tests/vault_core_check.py`** (pretend kits from `fake_kit.py`, two of them holding a photo with the same file name; scratch home; both Pythons; the server parts with the no-windows switch): `ensure` twice makes one vault; the list references both kits, same-named photos are two rows with two numbers; numbers stay when a kit gains a photo, loses one, gets one back, and when a third kit is made; a member kit's files and records are byte for byte unchanged after every vault command (hash the member folders before and after); `/kit-photo?kit=My vault&n=` serves the right photo for each of the two same-named ones; the arrange page state and the carousel designer's state list the vault's photos; a Just photos reel dry run (`reel.py make --dry-run` through the reel page's own make with pretend CapCut, as `tests/reel_page_check.py` does it) gets each picked photo's own path; `kit.py build`/Save slides in the vault writes slides into the vault's own Carousel folder from member photos; the vault is absent from `posts.kits`, `home_base.kits`, the home page's Newest and the recap's shoots; a plain kit's pages and records are byte for byte what they were (run `tests/arrange_check.py`, `tests/kit_cards_check.py`, `tests/sheet_numbers_check.py`, `tests/reel_page_check.py` after).

### Stage 7. `vault-page`

Her 1.3, screenshots 02 and 03, pages `make-posts-preview.html` and `vault-kit-preview.html`. Take every line from her pages; this list is a guide.

**The post kits list (`S/home_base.py`, the `/make-posts` screen).**
- My vault is always the first card, dark, alone on its own row above the shoots: "My vault", "All your shoots in one post kit · {n} photos", "Open the post kit". No Archive on it. "Find a post kit by shoot name" does not filter it.
- The press on Open the post kit is a guarded POST (`POST /vault-open`) that runs `vault.ensure()` and `vault.relist(quick)` and answers the vault's kit page address; with no post kits at all the card still shows (0 photos) and opens.
- The screen's title becomes hers, "Turn your shoots <em>into posts.</em>", and the eyebrow "Step 3 of your workflow" goes. The "What's a post kit?" box (her own v27 ask) stays, since her mock ran on her old server.

**The vault's post kit page (`S/kit.py build_page`, a vault branch).**
- Eyebrow "Post kit"; title "My vault."; "The post kit for all your shoots at once. Make reels and carousels that mix shoots: your favorites from the year, a few weddings in one, or behind the scenes you haven't used yet."
- The strip: one chip per shoot (its small picture and name), "{n} photos · {n} clips", **+ Add a shoot**, **+ Add clips**, **See everything in it →** (drawn only once stage 11's page exists: a constant `vault.EVERYTHING` that stage 11 turns on).
- Reels card: "The same reel maker as every post kit: your assistant picks, orders and cuts on the beat of your song, and it opens in CapCut. The only difference is it picks from every shoot in your vault." and the box "Tell your assistant what this reel is" with her three examples: "My favorite maternity photos this year" · "Behind the scenes at the beach" · "Moms laughing, from any shoot". (The note itself is the reel page's own `photo_ask`; the box here is her words and the door, not a second place to type.)
- Carousel card: "The same carousel designer, with photos from any shoot: a year of favorites, or three families in one post."
- Stories card: "Stories from any shoot: a throwback, a this-or-that, or behind the scenes from a few sessions."
- Everything else is the kit page's own (Make it, Create my reels →, Design my carousel →, Make my stories →, Not made yet, Your words, Add to my queue). The path at the top (`look.crumbs`) reads back to My post kits.
- Leave out her test-only words: every coral "Preview…" banner, "Trying ideas: animation samples", and every "In the real version, …" line.

**+ Add a shoot** (this copies photos, so it is built like `posts.py bring`).
- The computer's own choose-folder window (`GET /pick-folder`, as the Make posts screen uses), then `vault.py add "<folder>"` as a background job the page follows: the folder's finished photos only (JPEG, HEIC, PNG, WebP; `posts.py`'s own rule for what is a finished photo and what is "left where it is, not copied") are copied into the vault's own `Photos` folder with `posts.copy_checked` (hash while writing to a partial file, rename into place, read back and compare). The originals are never moved, renamed or changed.
- Log first: `.kit/vault-adds.json` (`status: copying`, each file's source name, size, time and hash); a run cut off is finished by the next; a second add of the same folder copies nothing ("already in your vault").
- A name already in the vault's Photos: same bytes means already there; different bytes means the copy is named with a number after its name ("IMG_0001 (2).jpg"); nothing is ever written over, and the original is never renamed.
- A folder that is one of their post kits' own photos folders is not copied: "That shoot is already in your vault, from its post kit."
- The line beside the button: "Copied 48 finished photos into your vault. Your originals weren't moved." (ours), and what was left ("3 files left where they are: not finished photos").
- From the chat: "add this folder to my vault" → `vault.py add`.

**+ Add clips** opens the vault's own Footage folder in a window (the way every post kit's footage gets in today; no video is copied by the Assistant), with a line of ours right there: "Put your videos in the folder that just opened. They show up in your vault's reel page, where you make clips from them."

Instructions: `P/post-kit.md` gets "My vault" (what it is, that it is opened like any post kit, the add commands, that nothing is picked until they ask); the core's table: "show my vault", "open my vault", "add this folder to my vault". `P/hello.md` if it describes the Make posts screen.

**Test: `tests/vault_page_check.py`** (hidden Chrome under `guard.py 3000`; pretend kits): the vault card is first, alone on its row, with no Archive, and stays when the search box filters everything else out; Open the post kit makes the vault once and lands on its page; her words both ways on the two pages when her handoff is there (her test-only lines on a named `HERS_NOT_OURS` list); the strip's chips and counts; the three cards open the reel page, the designer and the stories designer for the vault; `vault.py add` on a pretend folder: copies hash-identical, originals untouched (hashed before and after), heavy files named and left, twice copies nothing, a clash gets its own name and the first file is byte for byte what it was, cut off and finished; the page's add route refuses another Origin; no path on the page. `tests/home_base_check.py` and `tests/kit_cards_check.py` brought along.

### Stage 8. `vault-search`

Her 1.4 and the photo descriptions of 1.5. "Photo search has to find what's in the photo, not just the shoot name… **Never rename the photos.**"

**The store: `<kit>/.kit/photo-words.json`,** one per post kit (the vault's own Photos included), the version before kept as `photo-words.prev.json`, written whole under the kit's lock. Per photo number: `key` (the photo's size-and-time key, as `arrange._key` builds it, so a re-exported photo is looked at again), `tags` (from the Mac), `words` (from your assistant), and who wrote each and when. No photo file is touched or renamed.

**`S/photo_words.py` (new).**
- **The Mac's own tags, by themselves.** Apple's image classifier (Vision's `VNClassifyImageRequest`) asked through `this_computer.mac_javascript`, exactly the pattern of `faces.find` and `FACES_JS` (`S/faces.py`): on the 520 px small copies only, a dozen a run, the labels above a confidence line (`TAG_MIN`, a named constant; start at 0.3), at most 12 a photo, underscores turned to spaces; plus "one person" / "people" from the face count `faces.py` already gets. Nothing leaves the computer. **Prototype this route first on this Mac with a made-up picture** (it has never been tried; the faces route is proof only that Vision answers through the Mac's scripting). If the classifier does not answer this way, tags stay empty, the progress line is never shown as done falsely, and the stage says so plainly.
- **A background job per kit,** started when a post kit's page is opened or a kit is made and photos are without tags (the way `arrange.start_previews` runs; one kit at a time on this computer; it makes the small copies first if they are missing). `GET /photo-words-state?kit=` answers `{done, total, running}`. The post kit page shows her line while it runs, "Getting your photos ready to search: 40 of 72.", and takes it away when done. Everything else on the page keeps working.
- **A tests' switch** `PHOTO_WORDS_PRETEND` (a JSON file of file name → tags, or "none" for a computer with no classifier), like `FACES_PRETEND`. No test asks the real Vision except one small check that may SKIP.
- **Fuller descriptions from your assistant, only when asked** (rule 6: from numbered contact sheets, never photo by photo): `photo_words.py sheets "<kit words>"` prints the kit's numbered sheets (48 photos to a sheet, drawn by `kit.py sheet`) and which numbers have no words yet; `photo_words.py describe "<kit words>" --file words.json` checks the whole file first (`{"photos": {"12": {"words": "…"}}}`: a number on the list, one plain line up to 140 letters, no other field, at most 2,000) and writes under the lock; twice writes nothing. Modelled on `footage.py picks` / `describe`.
- **What a description may say** (in `P/post-kit.md`, new section "Describing photos so they can be found"): who is in it in plain terms (a mom, two kids, a couple; never a person's name unless the photographer said it), what they are doing, the setting and the colours ("Mom laughing with the kids at the water", "Close-up of the ring", "a green backdrop"). **Descriptions are for finding photos only.** They are never used as facts in a caption, a note or a hook (rule 11).
- The lines to copy (ours, drafts): on a post kit once the tags are done, a quiet line "Want search to find more, like "laughing" or "a kiss"? Copy this into the chat:" with "Describe my photos for <shoot>". The chat line for the vault: "Describe the photos in my vault" (every member kit without words; the assistant says how many photos first and asks before more than about 300).

**The search rule, hers, in one place (`vault.py`):** lower-case, split on anything that is not a letter or a number, drop everyday words (me, my, on, the, a, an, of, with, at, in, and, i, to; in the reel page's clip search also: find, every, clip, clips, from, any), and every word left must be found in the item's text. A photo's text is its tags + its words + its shoot's name ("Hannah laughing" works). A clip's text is its label + its shoot's name.
- `vault.catalog(kit)` builds what a page needs, once: the shoots (folder, name, date, counts, a small picture), every photo (vault number, group, its text), every clip (see stage 9: where its labels are read). The page filters in the page, so results "show up right away".
- `vault.py find "<words>" [--clips | --photos]` prints the matches for the chat (numbers and names, never asking the model to look).
- Clip labels live in each kit's `.kit/reel-page.json`, on each moment (`label`, `named`, `by`), in the open reel and in every other reel under `versions`: read them with the calls `footage.their_clips` uses (`reels.each`, `reel_page.moments_of`), each clip once. An unnamed clip ("Your pick at 1:09.6") has no words to find; it is listed under its shoot as "Not named yet".

**A PC:** no Vision, so no tags. A named gap with a line of ours on the post kit ("On a PC, search finds your photos by shoot name and by anything your assistant has described. To have them described, copy this into the chat: …"), in `this_computer` beside the other PC lines, in `P/on-a-pc.md` and the PC guide's list.

Instructions: the section above in `P/post-kit.md`; rows in the core's table for "Describe my photos for <shoot>", "Describe the photos in my vault", "find … in my vault"; `P/where-things-live.md`.

**Test: `tests/photo_words_check.py`** (pretend kits, the pretend classifier; both Pythons; a small hidden-Chrome part for the progress line): the store is written whole with the version before kept, keyed so a changed photo is done again; the job fills it in batches, the state counts up, the line shows and goes; a kit's photos are byte for byte unchanged and none renamed; `describe` refuses a bad file whole (a number not on the list, two lines, a path, an extra field) and twice writes nothing; the search rule: her everyday words are ignored, every other word must match, tags and words and shoot name together, case and accents; `vault.catalog` has no path in it; on a pretend PC (no classifier) search still finds by shoot name and by written words, and the PC line is on the page. One real-Vision check on a Mac that may SKIP.

### Stage 9. `vault-reel-clips`

Her 1.5, screenshots 05, 06 and 08, page `vault-reel-preview.html`. The Reels card in the vault's post kit opens our reel page for the vault. This stage: the top and the four kinds, and "Your clips".

**Words, hers (take them from her page; her page wins):**
- Eyebrow "My vault · Reel"; title "Make my <em>reel.</em>"; "From your vault: any clips and photos, from any of your shoots."
- "Which reel do you want to create?" / "The same four reels as every post kit. In your vault, each one can use clips and photos from any of your shoots."
- Behind the scenes: "Video clips from your vault, mixed with your finished photos." Just photos: "Your finished photos from any shoot, cut on the beat." Talking to camera: "You talk about your work, and photos from your vault go with what you say." B-roll: "Only video clips from your vault, cut on the beat. No photos."
- Your clips: "Your clips"; "Search your clips"; "Type what you're looking for. Results show up right away."; placeholder "me with my camera, laughing, kitchen, beach"; "Or tell your assistant what to look for"; "For example: “Find me editing on the computer.” or “Every clip of me shooting at the beach.”"; placeholder "Optional: what you'd like your assistant to find"; the line to copy "Find my clips in my vault" with "Copy" / "Copied"; "Added to my vault" / "Clips you add to your vault show up here, open and ready." / "+ Add clips"; per shoot "From its post kit · {n} clips", while searching "{n} found"; on a tile "+ Add" / "✓ Added"; "Your clips for this reel" / "{n} added" / "Add clips from your search above."; "Nothing matches that yet. Try other words, or tell your assistant what to look for."
- Each kind shows only its own steps, numbered in order (already how our kinds work): Behind the scenes: clips, photos, song, vibe, watch. Just photos: photos, song, vibe, watch. Talking to camera: the talking page. B-roll: clips, song, vibe, watch (no photos).
- Not ours to copy: "The same as every reel." under song, vibe and watch (her placeholders for our real steps), "A moment you picked" / "A clip" (ours says "Not named yet"), every "In the real version…" line.

**Underneath, our way (`S/reel_page.py`, a vault branch in few places):**
- **Videos across kits.** `list_videos(kit)` for the vault returns its own Footage videos and then each member kit's Footage videos (the member's own folder checked the same way), each member video named `<member folder>/<file name>` (a slash can never be in a file name, so two shoots' `IMG_1234.MOV` stay apart). A moment keeps naming its video by name (`"Footage/<member folder>/<file>"`), so `video_by_name` and everything after it work unchanged. The vault keeps its own facts, stills and small copies of those videos under its own `.kit` (made on first ask; nothing is written into a member kit).
- **+ Add from the search.** `POST /reel-moment` gains `do: "add-from"` with `{from_kit, from_id}`: the Assistant reads that member's moment itself (never the page's text), checks it, and adds a moment to the open vault reel with the member's start, end and label, `by: "you"`, `named` as the member's, and `from: {kit, id}` so the tile can say "✓ Added". The reel's own clip cards (ours "Your clips", headed "Your clips for this reel" in the vault) take it out with their own ×. Every existing rule holds: which reel the page shows, the two-window rule, the clip limits per kind.
- **The panel** above the footage editor on a vault's clips step: the search box (filters `vault.catalog`'s clips in the page with her rule and the clip list of everyday words), the ask box and line to copy, "Added to my vault" open on top (the clips made from the vault's own Footage videos), then each shoot folded shut with its small picture, name and count; a search opens only the shoots with a match and says "{n} found"; a clip tile shows a still (`/reel-moment-still` or the strip's still, by the vault's key), its length and its label.
- **The editor stays below it,** for making clips from the vault's own videos and from any shoot's video (its Footage drop-down lists the vault's own first). One line of ours joins them: "Videos you add show up in Your footage below. Make clips from them there, or ask your assistant to look through them."
- **Talking to camera** opens the talking page for the vault (its photo picker lists the vault's photos through the stage 6 branch). Try it on a pretend kit; name what does not work.
- **The chat line "Find my clips in my vault"** (and what they typed in the ask box, saved with the reel like the footage ask): `vault.py clips [--reel "<name>"]` prints the note and every clip (shoot, id, label, length; unnamed ones listed apart); the assistant chooses by the labels and the note (words only, never watching video), offers "Name my clips for <shoot>" for a shoot whose clips are unnamed, and adds its choices with `vault.py use-clips --reel "<name>" --clips "<member folder>:<id>,…"` (the same add as the page's). A section in the reel skill and `P/arrange.md`, a row in the core's table.
- **B-roll in the vault** is the kind Nicole most wants ("You don't want someone to have to upload a post kit to create like a simple B-roll clip"): search, + Add, song, Save my video. Make sure the made entry, Save my video and the queue work with member videos.

**Test: `tests/vault_reel_check.py`, part `clips`** (hidden Chrome under `guard.py 3000`, video parts under `guard.py 800` with tiny self-made clips; two pretend kits each with a video of the same file name and named moments): the chooser's words; each kind's steps; the vault lists both same-named videos apart; search "laughing" opens only the shoots with a match with "1 found" and leaves the rest shut, "Added to my vault" stays open; + Add puts the member's clip in the reel with its label and the tile says ✓ Added; × takes it out; a reload keeps it; `add-from` refuses a kit that is not a member, an id that is not a clip, another Origin; the member kits' records and folders are byte for byte unchanged; a B-roll dry run gets each clip's own video path; her words both ways. `tests/reel_page_check.py`, `tests/reel_footage_check.py`, `tests/reel_v27_page_check.py` still pass on a plain kit.

### Stage 10. `vault-reel-photos`

Her 1.5, screenshot 07. The photos step of the vault's reel page, and the two chat lines.

**Words, hers:** "Choose your photos"; "Your assistant can choose the photos and their order for you, or you can drag them in yourself."; "Let my assistant choose" / "Your assistant picks the strongest photos from your vault and orders them so each one flows into the next."; "I'll drag them in myself" / "Search or browse all your photos below, and tap to add."; "Tell your assistant which photos you'd like in this reel" + " Optional, and only for this reel."; "For example: “My favorite maternity photos from this year.” or “Moms laughing, from any shoot.”"; placeholder "Optional: which photos to use, or leave out"; "Then copy this into the chat, and your assistant picks the photos for this reel:"; the line to copy "Pick my reel photos from my vault"; "Your photos for this reel" / "Your assistant will pick these, or tap photos below to add your own."; "All your photos, from every shoot in your vault"; "Added to my vault" / "Photos you add to your vault show up here, open and ready." / "+ Add photos"; per shoot "From its post kit · {n} photos". For talking: "Your talking video" / "Record yourself talking to the camera, the same as a talking reel in any post kit. Your assistant places photos from your vault with what you say, from any shoot."
- Her photo-search placeholder "Search by shoot: maternity, Hannah, Christmas" is the mock's limit, not her wish (she says photo search must find what is in the photo). Ours (draft): "laughing, a kiss, green backdrop, Hannah".

**Build (`S/reel_page.py`):**
- The photos grid of a vault reel is grouped: "Added to my vault" open on top, then each shoot folded shut with its small picture, name and "From its post kit · {n} photos"; tap to open. A search box over it filters with her rule over each photo's text from `vault.catalog` (tags + words + shoot name); a search opens only the shoots with a match, with "{n} found" on each, and leaves the rest shut. Everything else on the step is the page's own: the order row, drag, Longer and Quicker, select several, the note (`photo_ask`), the line to copy with ", and follow my note" when there is one and the reel's name when there are several.
- "+ Add photos" in the vault opens the vault's own Photos folder (the existing `open_photos` door); the list picks new photos up by itself (stage 6's `vault.changed`).
- While a shoot's photos are still getting their tags, the step shows her progress line for that shoot so nobody searches too early and thinks it is broken.
- **The chat line "Pick my reel photos from my vault[, <reel>][, and follow my note]":** `reel_page.py note "My vault" [--reel]` prints the note and the save command (as for any kit). The assistant narrows first with `vault.py find "<the note's own words>" --photos` when the note names something findable, then looks at numbered sheets of the shortlist only (`vault.py relist --sheets --only <numbers>`: 48 to a sheet; with no note, the sheets of the whole vault, and it says how many photos first), picks and orders by `shared/curating.md`, and saves with `kit.py picks --reel … --for-reel`. The note decides what may go in (rule 11 as amended Nov 14). Instructions in the reel skill's Step 2 and `P/arrange.md`; a row in the core's table for both pasted lines.

**Test: `tests/vault_reel_check.py`, part `photos`** (hidden Chrome; three pretend kits with pretend tags and words): the folds, the counts, "Added to my vault" on top; "laugh" opens only the shoots with a match and says how many; "hannah laughing" finds across name and words; a tap adds a photo to the order with its vault number and the made reel's dry run gets that photo's own path; a note changes the line to copy; her words both ways; a plain kit's photos step is unchanged (the kept page tests pass).

### Stage 11. `vault-everything`

Her 1.6, screenshot 09, page `vault-preview.html`. "Nothing gets picked on this page. Making happens in the post kit."

**Words, hers:** title "What's in <em>my vault.</em>"; "Your clips and photos from every shoot. Add more, or look up a clip you remember."; tabs "Clips {n}" and "Photos {n}"; "+ Add clips or photos"; the search placeholder "Search: me with my camera, laughing, beach, kitchen" (aria "Search your vault"); chips "Every shoot" then each shoot's name; group heading "{shoot} · {date}"; "Nothing matches that yet."; in the viewer: the clip's label as the heading, "{shoot} · {date} · {n} seconds", **Use it in a reel**, **Remove from my vault**, close ×. The way back is the path at the top (hers: "← My vault post kit").
- Not hers to copy: "Photo {id}" as a photo's heading (ours: the shoot's name and the photo's own description when it has one), the dead tray code and "Used" badge, "In the real version…".

**Build: `S/vault_page.py` (new), `/vault.html` on the posting server** (one line each in `posting_queue.py`'s GET and POST lists, as every page's routes are added).
- The grid of clips (tall tiles with a still, the length badge "▶ 0:03", the label, the shoot) and photos, grouped by shoot, filtered by the search and the shoot chips, from `vault.catalog`.
- **Tapping a clip plays it** right there, looped between its start and end, from the existing `/reel-video` route (the vault and the video's key), with what it is, the shoot, the date and how long it is. A photo opens big from `/kit-photo`.
- **Use it in a reel** is a link to the vault's reel page (the chooser). It picks nothing.
- **Remove from my vault** (`POST /vault-remove {what: "photo"|"clip", id, on: false}`, guarded): writes one entry to the "out" list in the vault's `.kit/vault.json`, the version before kept. **No file is touched: not the photo, not the video, not the shoot's own post kit.** The photo's vault number stays retired; a clip is left out of the vault's lists. Twice changes nothing. The line right there (ours): "Taken out of your vault. The photo itself is still in its shoot, and nothing was deleted." with **Put it back** beside it; a quiet fold at the bottom, "Taken out of my vault ({n})", lists what was removed, each with Put it back (`on: true`).
- A reel that already used a removed photo shows it the way a gone photo shows today.
- **+ Add clips or photos** offers the two adds of stage 7 (the folder picker for photos, the Footage folder for videos).
- Turn on `vault.EVERYTHING` so the strip's "See everything in it →" appears on the vault's post kit.

Instructions: `P/post-kit.md` ("See everything in it", "take this out of my vault", "put it back": `vault.py out` / `vault.py back`), a row in the core's table.

**Test: `tests/vault_everything_check.py`** (hidden Chrome; a tiny self-made clip under `guard.py 800` for the play part): the tabs and counts; "me with my camera" finds the named clips; a tap opens the viewer with the label, shoot, date and seconds and a video element pointed at the vault's route; Remove writes only `vault.json` (every member folder and the vault's own Photos and Footage hashed before and after), the tile goes, Put it back brings it back with the same number; another Origin is refused; her words both ways; no path on the page.

---

## Decisions made here, for Dustin and Nicole to confirm

**The backup**
1. **The one question.** One external drive: no question at all. More than one, or none: one question, once ever. (As Dustin said it.)
2. **Where on the drive.** The drive's obvious shoot folder when it has one, else right on the drive. The other choice would be a folder of the Assistant's own on the drive. Nothing can move a finished backup afterwards, so this default cannot be fixed in one click for a backup already made; "Use a different drive next time" fixes the next one.
3. **No external drive.** One question, no speech; on "this Mac for now" photos go to a new folder `Shoots` in Pictures, and the report carries one quiet line about an external drive. The folder's name is a draft.
4. **Nothing is asked when they come back either.** "Who's the note going to?", "anything else you're editing?" and "a tap three days before it's due?" are asked only when they ask for that thing.
5. **A client note is no longer written during the backup** unless they said who it is for without being asked. The button gives a line to copy.
6. **The cards question is gone;** cards are joined on the report afterwards, and the end-of-backup box gets a second button, **Eject my card**. The phone-tap page is shown only when they ask.
7. **A later second copy is always in the card's layout,** whether read from the card or from the drive, and the report says which. Read from the drive, a clip the backup turned upright is the upright one (36 bytes different from the card).
8. **"Card safe to format" is not changed by a second copy that is running or stopped.** The backup's own record says "second copy" only once every file is checked.
9. **A saved second drive that is not plugged in no longer stops a backup:** one copy is made and the report says so with the button. (A second drive typed for that one backup still stops.)
10. **Folder naming on the report offers the two ways** (year first, name first) and a line to copy for their own way. Photo names are changed in the chat only.
11. **Her line on the Back up a card screen,** "Your assistant asks a quick question or two…", is replaced with one of ours, since it is no longer true.
12. **All of the report's option words are ours:** the section heading, every button, every result line.

**The home page and recap**
13. **Each reel is counted once** in the recap (her ask). Hours saved drop with it.
14. **The "Step N of your workflow" eyebrows go** from the screens, since the home page no longer numbers steps.
15. The Make posts screen takes her title, "Turn your shoots into posts.", and keeps the "What's a post kit?" box.

**The vault**
16. **A real folder, "My vault", in Your Content,** whose photo list points at the shoots' own photos. No photo is copied to be in it. It makes its own small copies for the pages.
17. **Every post kit is in the vault by itself, archived ones too.** Her card says "All your shoots in one post kit"; her mock left archived kits out. Ours keeps them so archiving a kit never changes a reel.
18. **+ Add a shoot copies a folder's finished photos into the vault's own Photos folder** (checked, originals untouched), shown under "Added to my vault". It does not quietly make a new post kit. A shoot that is already a post kit is already in.
19. **+ Add clips opens the vault's Footage folder;** the Assistant copies no video. A video dragged from the same drive is moved by Finder, as with every post kit's footage today.
20. **A clip from another shoot stays in that shoot.** The vault lists it and keeps its own stills and small copy of the video.
21. **Photo descriptions:** the Mac's own tags by themselves when a kit is opened (nothing leaves the computer); your assistant's fuller descriptions only when asked, from a line to copy. Apple's tags are things and places; "laughing" or "a kiss" needs the assistant's descriptions.
22. **Descriptions are for finding photos only,** never used as facts in a caption or a note, and never a person's name.
23. **Remove from my vault can be undone** (Put it back, and a fold of what was taken out). Hers has no way back.
24. **The vault in the posting queue and the hello** reads "My vault reel · {reel name}", "My vault reel is waiting". Needs a word from Nicole.
25. **The first carousel design in the vault is blank,** and both designers show every vault photo in one tray (her folds and search are for the reel page).
26. **Renaming a shoot's post kit folder by hand** gives its photos new numbers in the vault (kits have no id of their own).
27. **One caption for all of a shoot's reels** (already so) fits the vault badly, since each vault reel is about something else. Captions are optional; left as it is.
28. **Our draft words** where hers has none: the photo-search placeholder, the "Describe my photos" lines, the PC line, the add and remove result lines, "Taken out of my vault", the line joining the clip search and the editor.

## Deliberately not built

- **Her 1.7,** the one sentence that says what it is: she is still deciding. Nothing on a page changes for it.
- **Moving a finished backup** to another drive or folder; **merging two cards' photos into one shoot folder** (the Oct 23 master-folder plan); unlinking cards or changing their order.
- **A second copy that mirrors the sorted shoot folders,** and bringing a second drive up to date with edits (banked Oct 28).
- **A phone-tap option on the report;** photo-name choice on the report.
- **The report's where-card still prints the folder's path** and sends it to open the folder (older than the "never a path" rule). The new options never do.
- **The vault's folds and search in the two designers;** sharing the shoots' small copies with the vault; a kit id that survives a folder rename.
- **Fuller photo descriptions made by themselves** (they cost the photographer's plan; only on ask).
- **Photo tags on a PC** (no Vision there); the vault's footage stills on a PC (as every kit).
- **A caption per reel.**
- **Her test-only words and wiring:** the "Preview" banners, the samples link, "In the real version…", `?home=test`, her server's addresses.
- **The brand interview (stage 6 of v21), Remove-a-song follow-ups, the folder-naming question's wording, the drop box's second copy:** unchanged by this build. (The folder-naming question itself is no longer asked before a backup.)

## After the stages

For whoever closes the build: a sweep of every test, one at a time under the guard; `release.json` to version 6 with plain lines of what is new; a section in `CLAUDE.md` (what was built, what is NOT tried, what is theirs to settle); the draft note for Nicole, `docs/nicole-v29-notes-2026-11-19.md` (not sent; rule 10); the setup guides' first-backup walk-through, which still describes the questions. Nothing is pushed, merged, posted or sent without Dustin's say.

## Built

(Each stage's builder adds its note here, under its own heading.)

### Stage 1, `recap`, built (Nov 19)

**What changed.**
- `wrapped.py`: `COUNT_EACH_MAKE = False`. The recap and Your year count each reel once, on the day it was first made, however many times Make was pressed on it. The comment on the switch says who decided and why (Nicole, v29 2.2: 79 reels for November was every make counted). The notes at the top of the file say the same. No words on any page changed.
- The hours saved, the recap card's chips on the home page, each shoot's own count, the top shoot and "shoots shared" all follow by themselves; they read the same count.
- `parts/hello.md`: one sentence added where the assistant is told what a number counts ("A reel counts once, however many times they pressed Make on it, in the month it was first made."). `parts/where-things-live.md` never said every make counts; unchanged.
- `tests/wrapped_check.py`: "once" is the expected way throughout, and a new group, "each reel once": three makes of one reel in a month with nothing else in it read 1 reel, 45 minutes saved, "1 reel" in the chips and on the recap card, and the same month with the switch turned back would read 3 reels and 135 minutes. The test now puts the switch back to what the file ships with after trying the other way (before, it forced a value, which would have hidden a switch turned back).
- `tests/home_v28_check.py`: its pretend kit had the same reel made in October and again in November, which is now one October reel; the two makes are now two different reels of the shoot, so November still has something to recap. Test data only.

**Checked,** this Mac, pretend kits, a scratch home, both Pythons (3.12 and Apple's 3.9), same counts on both: `wrapped_check.py` 132 of 132 (it was 121), `home_v28_check.py` 175 of 175, `skill_text_check.py` 640 of 640, `workflow_check.py` 14, `tools/check_pc.py` and `tools/check_plugin.py` clean. With the switch turned back by hand, `wrapped_check.py` fails 13 cases, the new ones among them. `wrapped_check.py` was already in `check-pc.yml`; no change there.

**Not tried.** Nicole's real November (whether 79 becomes the number she expects is not known: her records are not here). Nobody has looked at the recap page or the card by eye since the change. Windows and GitHub: nothing pushed.

**Choices for Dustin and Nicole.**
1. **A reel made again in a later month stays in the month it was first made.** A reel first made in October and reworked in November counts for October only, so November's recap does not show it. The other way (count it once in every month it was made in) would let a year's months add up to more than the year.
2. **"One reel" means one reel on the reel page's Your reels list** (or one talking reel on its list). Starting a new reel with + Start a new reel counts as another; Try another mix and Make again on the same reel do not. A reel made from the chat the older way counts as the shoot's first reel.
3. **Reels made before v26 (no list of reels) all count as that shoot's first reel,** so an older shoot with several separately made reels reads as one.

### Stage 2, `home`, built (Nov 19)

**What changed.**
- `home.py`, server-drawn as before. Top to bottom: the hello (unchanged); one big white card, **Turn your shoots into posts**, with her line, one dark button that is a plain link to `/make-posts` ("Create your post kits →" with no post kits, "See all my post kits →" with some) and the same now-box beside it; **My posting queue**, full width, with its words, its box and "Open my posting queue →"; a small caps heading, **Also in your Assistant**, over two smaller outlined cards side by side, **Back up a card** and **My editing queue**, same words and boxes, no button label (the card is the press); then the recap card and the Your year bar, unchanged. No list of post kits anywhere on the page.
- Gone from the page and from `WORDS`: the step numbers, "Your workflow" (`wf_h`), "Start wherever you are…" (`wf_say`), `s1_go`, `s2_go`, `s3_go`; `STEPS` and the `.flow4` styles. New `WORDS` keys, hers word for word from `pages/home-preview.html`: `s3_create`, `s3_see`, `also_h`.
- The ids and press names are the ones the four steps had (`s1` backup, `s2` queue, `s3` posts, `s4` posting; `n1` to `n4`), so `home.py pending`, the hello's buttons and `now_boxes()` are untouched. One difference: `data-item='posts'` is on the big card's button (`#kitsBtn`), since the card itself is not a press (as hers).
- **The stale eyebrow removed:** "Step 1 of your workflow" (`home_base.WORDS["b_eyebrow"]`) and its `<span class='eyebrow'>` on the Back up a card screen. That was the only one besides `m_eyebrow` ("Step 3 of your workflow", Make posts screen, left for stage 7): the editing queue's and the posting queue's eyebrows read "Editing queue" and "Posting queue" and never said a step.
- `parts/hello.md`: the home page's description (the four cards, posts first, the button's two readings, no list of kits, never send them to "step 3") and one sentence on what each press is recorded as. `docs/SETUP-GUIDE.md`: its one sentence describing the home page (the PDF is not rebuilt; the PC guide had no such sentence).
- Tests brought along: `home_v28_check.py` (the new order; her five v28 lines that v29 took out are a named list), `home_base_check.py` (posts first, the button instead of the card, "Step 1 of your workflow" named as left out on purpose), `loose_ends_v26_check.py` (what hello.md must say), `pc_smoke.py` (one line it looked for on the page). New: `tests/home_v29_check.py`, in `check-pc.yml` on the Mac job (`--no-chrome`) and the Mac page job (under the guard).

**Checked,** this Mac, pretend kits, a scratch home, no windows: `home_v29_check.py` 47 of 47 on Python 3.12 and on Apple's 3.9 (27 without a browser, on both); with the old `home.py` put back it fails 5 of its first 8. `home_v28_check.py` 173 (3.12; 127 without a browser on 3.9), `home_base_check.py` 218, `skill_text_check.py` 640, `loose_ends_v26_check.py` 64, `pc_smoke.py` 230, `workflow_check.py` 14, `tools/check_pc.py` and `tools/check_plugin.py` clean. Looked at by eye: one picture of the page at desktop width and one at phone width in a hidden Chrome, pretend photos, beside her screenshot 01.

**Not tried.** Nobody's hand, the Claude app's pane, real kits or photos, 20 or 30 post kits, Windows, GitHub (nothing pushed). The home page's "no post kits" state was tried by moving the pretend kits aside, not on a brand-new Assistant with no folder at all in a browser.

**Found, not fixed (older, not this stage's):** the posting queue's own page (`/posting.html`) drops the connection when `posting.json` holds a piece that is not a record (a bare word in the list; `posting_queue.greens`). The home page survives the same record. Only a hand-broken file could do it; worth a line in the hardening pass.

**Choices for Dustin and Nicole.**
1. **The big card itself is not a press;** only its button is (as her page). The other three cards are a press anywhere on them.
2. **"Some post kits" means kits that are not archived:** with every kit archived the button reads "Create your post kits" and the box "No post kits yet" (her page does the same).
3. **Her accent words stay DM Sans in coral** (no serif, Dustin Nov 7), as on the v28 page.
4. **The Back up a card screen now has no small line over its heading** (it had "Step 1 of your workflow"). Nothing of ours was put in its place.
5. **The Make posts screen still says "Step 3 of your workflow"** until stage 7 reworks it.
6. **`release.json`'s version 5 line still says "your four steps";** left for whoever closes the build and writes version 6.
7. Her page shows a small label on the posting queue card only ("Open my posting queue →"); kept as hers, so three cards have a visible way in and two do not.

### Stage 3, `backup-zero`, built (Nov 19)

**Nothing here has run with a real card or a real drive.** Every check ran on this Mac, on pretend drives (temp folders handed over through a tests' switch), a pretend card folder and a scratch Studio home. No fresh chat session has followed the rewritten instructions.

**What was built.**
- `S/this_computer.py`: the tests' switch `STUDIO_DRIVES_FOR_TESTS` (a JSON list of pretend drives; with it set `volumes()` gives that list and nothing else; a list that cannot be read is no drives, never the real ones), and a second switch, `STUDIO_FOLDERS_FOR_TESTS`, so a test's Pictures folder is a temp folder.
- `S/studio_file.py`: `choose_defaults(drive, computer, write, source)`, the command `studio_file.py defaults [--drive] [--computer] [--source] [--dry-run]`, `set_drive()` (the one way a drive is saved, used by `set --drive`, `set --second` and the new choice, so a PC's drive facts are kept), `ask_words()` (the one question's two shapes, as the assistant is told them) and `drive_lines()`. Answers: `SET:` (a drive is on file, nothing changes), `CHOSE:` / `WOULD CHOOSE:`, `ASK which-drive` (exit 3), `ASK no-drive` (exit 4); a named folder that is not there is a STOP.
- `S/night.py`: with `--source` and no drive on file it chooses instead of stopping, says "First backup: your photos go to Big Kahuna, in Photo Shoots.", and carries on; with `--check` it chooses without writing ("would go"). Exit 5 is now "ONE QUESTION before the first backup: which drive", with the question and the command that saves the answer. Nothing else in the backup changed.
- `S/backup.py`: only the `--second` help text and usage line (a second drive, never a cloud folder).
- `S/home_base.py`: `b_s2_small` moved from `WORDS` to `OUR_WORDS` with the plan's draft; her line is on the "left out on purpose" list in `tests/home_base_check.py`.
- Instructions: `P/first-backup-setup.md` rewritten short (no conversation, the defaults command, the one question in two shapes, the computer's own disk with no speech, the usual way in plain words, the table, "Asked later, only when it is needed" with the client-voice question word for word); `P/backup.md` steps 1 to 5 rewritten (the quiet check before the starting message, the new starting message, every card its own backup, Eject my card as the closing box's second button, phone taps only on ask, a "Somewhere else this time" paragraph, a short "What are my settings?" section); `P/after-the-report.md` asks nothing by itself; `P/client-note.md` opening (a note only when they said who it is for, or ask); `P/hello.md` (no "few quick questions"); `P/on-a-pc.md` (the drive-letter stops kept; the dead pointer now points at a paragraph that exists); the core's backup row (one clause and "what are my settings?"; the description untouched).

**Tested** (both Pythons, 3.12 and Apple's 3.9, same counts unless said): `tests/backup_zero_check.py` 43 (new; with the old `night.py` put back 7 of them fail); `tests/skill_text_check.py` 658 (18 new, `check_backup_zero`); `tests/backup_safety.py` 32; `tests/glance_check.py`, `tests/eject_check.py`, `tests/phone_setup_check.py` all OK; `tests/report_v26_check.py` 107; `tests/home_base_check.py` 218 (under the guard); `tests/pc_smoke.py` 230 (183 on 3.9); `tests/shoot_report_check.py` 42; `tests/home_v29_check.py --no-chrome`, `tests/peek_check.py`, `tests/clips_check.py` pass; `tests/workflow_check.py`, `tools/check_pc.py`, `tools/check_plugin.py` clean. The new test is in `check-pc.yml` on the Windows and Mac jobs; it has not run on GitHub.

**Expectations of older tests changed on purpose:** `report_v26_check.py` (its two first-backup cases held the old opening speech and the folder-naming question; they now hold that both are gone and that naming is changed on ask); `phone_setup_check.py` ("Never for one card" is now "Phone taps: only when they ask"); `home_base_check.py` (her "quick question or two" line is left out on purpose).

**NOT tried.** A real card, a real external drive, two real drives, a Mac with none; a PC (drive letters with the new choice, `--computer` where Pictures is in OneDrive); a fresh session following the new parts ("backup now" with nothing asked, the one question, the first-backup sentence); the closing box with two buttons in the Claude app; a first backup whose only drive is nearly full (the quiet check stops it, as before, but the drive is already saved by then when `defaults` was run first).

**Choices for Dustin and Nicole.**
1. **A drive that holds the thing being backed up is never chosen** (`--source`): backing up a folder from the only external drive gives the no-drive question rather than a copy onto the same drive. Ours; the plan did not name it.
2. **The drive is saved before the quiet check runs,** so a first backup that then stops (card went quiet, drive full) leaves the drive on file. It is the drive they would have got anyway; say if it should be saved only once the copy starts.
3. **"backup now, onto the LaCie" on a first backup** is taken as the answer to the one question (`defaults --drive`), with nothing asked.
4. **Changing a default after the fact, until stages 4 and 5 put buttons on the report,** is by saying so in the chat; the table in `first-backup-setup.md` gives the assistant the command for each (a second copy, name-first folders, their own pattern, camera names, another drive from now on). The first-backup sentence already says "on the report", which is only fully true once stage 5 is built.
5. **When they say up front that a shoot is on several cards,** the "Ready to swap cards?" and "Is card 2 in?" boxes still follow each card. For someone who said nothing, each backup just ends with Show the report and Eject my card.
6. **The suggested name for a second unnamed card the same day ("saturday card 2") is now used without asking** (it was "offer"), since asking would be a question before the copy.
7. **Eject my card is left off the closing box** when the source was a folder rather than a card, or the backup stopped with a problem.
8. **Nicole's Nov 13 "here's what's about to happen" paragraph is gone** with the opening speech. Why there are several folders is still said on the report and in the closing lines.
9. **Draft words of ours:** the Back up a card screen's line (`home_base.OUR_WORDS["b_s2_small"]`), the two notes written into the Studio File ("Photos go onto Big Kahuna, in Photo Shoots: chosen by itself on the first backup." and the own-disk one), the folder name `Shoots`, the hello's "There's nothing to answer first, so you can walk away.", and the first-backup explanation in `hello.md`.
10. **A PC with an older Studio File that has no drive name beside its letter** is still asked "Onto Big Kahuna (E:), like usual?" once, as the plan says. That is the only "like usual" left.
11. **Not touched:** the setup guides' first-backup walk-through (still describes the questions; left for the close of the build, as the plan says), and CLAUDE.md.

### Stage 4, `backup-second-copy`, built (Nov 19)

**Nothing here has run on a real card or a real drive.** Every check ran on this Mac, on one whole pretend backup made by `night.py` itself (a pretend card folder, temp folders handed over as drives through `STUDIO_DRIVES_FOR_TESTS`, a scratch Studio home). No stage reviewer has read it yet; the plan says this stage gets reviewers.

**What was built.**
- **`S/second_copy.py`** (new): `second_copy.py "<backup>" --to "<drive or folder>" [--check] [--json] [--always]`. One layout always, the card's own: `<to>/<the backup's folder name>/<each file at its card path>` and a copy of the manifest in a hidden `_studio` there. Records found with `where.locate` (before or after the settle, and found again if the backup settles while the copy runs). Per file: the card when it is in, answers, and `cards.check` says the ledger holds it for this very backup's records; otherwise the copy on their drive, found through the index's `original` → `file`, the sort and rename logs (for a sidecar that came off the card), the set-aside leftovers in the records, and the card path itself. Copied with `backup.copy_with_hash`; three hashes must agree (read, read back, the manifest's: `card_sha256` from the card and `sha256` from the drive for a clip the backup turned). `backup.py`'s `copy_with_hash`, `sha256_of`, `identity`, `ours_to_redo`, `onto_itself`, `DIFFERS`, `hide`, `human` are imported, never copied (a check holds that).
- **Refused before a byte, and with `--check`:** onto the card, inside the backup (its records, its day folder, a shoot's own folder), onto the drive the photos are on, not enough room (what is still to copy × 1.05 plus 2 GB), a backup that is unfinished, has problems or was a sample, records not found, a folder of that name on the second drive holding a different backup, a second copy already complete elsewhere, another one running (`~/.studio/second-copy.lock` through `this_computer.try_lock`, with `second-copy.running.json` beside it saying which). A second copy already complete at the same place is exit 0, "Nothing to do."
- **Records:** `second-copy.json` in the backup's records, written whole before the first byte and after every file. The backup's `manifest.json` is written once, at the very end, only when every file is checked (`second`, each file's `second.ok`, and `second.turned` for an upright clip), with `manifest.before-second-copy.json` kept once; then the manifest copy on the second drive, then `first_look.py` and `report_page.py`, then the record says done. Runs under `this_computer.awake_while`. Exit 0 done, 1 problems, 2 refused, 3 stopped part way.
- **The report** (`S/report_page.py`: `OUR_WORDS`, `options_section`, `OPTIONS_SCRIPT`): the section "Anything you'd like to change?" under the shoots, the Make a second copy panel, the progress and keep-your-card-in lines beside the button, the made line in place of the button, and the missed-drive line under the hero's pill. Only on a backup that finished clean and was not a sample. **`S/serve_report.py`:** `GET second-drives` (name, free space, an index; never a path), `GET second-status`, `POST second-copy` behind `arrange.guard` plus the cross-site refusal; the server lists the drives again and the name must match; `second_copy.py --check --json` runs first in a fresh process, then the job is started with `this_computer.popen_detached`, its output in `~/.studio/logs/second copy.log`.
- **`S/night.py`:** a second drive from the Studio File that is not plugged in no longer stops the backup: one copy is made, `second-missed.json` goes in the records, and `--check` prints a NOTE for the assistant. A `--second` typed for that run still stops. **`S/eject_card.py`:** refuses with "A second copy is still being made from this card. It won't be long." while one is reading that card.
- **Instructions:** a section "A second copy, after the backup" in `P/after-the-report.md`, a row in the core's table (description untouched), the table row in `P/first-backup-setup.md`, the eject line in `P/backup.md`, the new records in `P/where-things-live.md`.

**Tested** (both Pythons, 3.12 and Apple's 3.9, same counts): `tests/second_copy_check.py` **116** (new; **126** with `--chrome`, which presses the button in a hidden Chrome under the guard, 3.12 only run): from the card; from the drive after a settle and a rename, with a sidecar and a camera file; a turned clip both ways; killed part way then finished with the same files (same file number and time) and no partial left; the card pulled half way; a different file already there, twice; its own failed copy redone and somebody else's file not; a changed photo on the drive; eleven refusals each with and without `--check`; run twice; the routes, the POST from another Origin and a cross-site one refused, a wrong name refused, no path in any answer or page line; the missed second drive. **Each guard was taken out in a scratch copy and the test failed each time:** the three-hash check (5 failures), never-overwrite (10), manifest-only-at-the-end (9), the lock (6). Also run after: `backup_safety.py` 32, `eject_check.py`, `backup_zero_check.py`, `glance_check.py`, `clips_check.py` OK, `shoot_report_check.py` 42, `report_v26_check.py` 107, `home_base_check.py` 218, `report_fall_check.py` 55, `pc_smoke.py` 230 (183 on 3.9), `skill_text_check.py` 666 (8 new, `check_second_copy`); `workflow_check.py`, `tools/check_pc.py`, `tools/check_plugin.py` clean. The test is in `check-pc.yml` on the Windows and Mac jobs and, with `--chrome`, on the Mac's page job; none of it has run on GitHub.

**NOT tried.** A real card, a real second drive, a real card pulled out mid-copy (the test renames a folder), a drive really filling up or really unplugged (those two stop lines have no test at all), a card that goes quiet, thousands of large files (the record is rewritten whole after every file, as the backup's manifest is), a real video clip turned by `clips.py rotate` (the test plays it by changing 36 bytes), a backup that settles while the copy runs, a shoot on several cards and the button inside a `/card/N/` frame, the panel by anyone's hand or in the Claude app's pane, a page server that starts over mid-copy, a PC (the lock, the detached job, drive letters), a fresh session following the new instructions.

**Choices for Dustin and Nicole.**
1. **The card pulled half way does not stop the copy:** the same run carries on from their drive and says how many came from each. (The plan's Test list said "stops in plain words; the next run finishes from the drive"; its design paragraph said one run may use both. Built as the design paragraph.)
2. **A copy that fails its check is never left under the photo's name on the second drive:** it is put back under the unfinished name it was written as (`.studio-partial`), which the next try writes afresh. Ours; `backup.py` leaves its own failed copy under the real name.
3. **A file on the card that no longer matches the backup gets one more try from their drive** in the same run, with a note in the record, not a problem. Only when the drive's copy does not match either is it a problem.
4. **`--to` must be a folder that is there;** the copy never makes a new folder on a drive except the backup's own.
5. **One second copy per backup.** A second one on another drive is refused once one is complete. A stopped copy to drive A followed by a copy to drive B keeps A's record as `second-copy.older-<date>.json` and leaves A's files where they are.
6. **Onto the computer's own disk is allowed** from the chat when the photos are on an external drive (it is a second place); the report's panel never offers it.
7. **Room is counted as 5% plus 2 GB over the files,** as the backup counts it.
8. **Exit 0 with "Nothing to do." when the same second copy is already complete** (the brief listed it among the refusals).
9. **The options section is not drawn on a backup with problems, an unfinished one or a sample,** and the missed-drive line sits under the "safe to format" pill only.
10. **The tick box saves the drive itself as the usual second copy** (`drives.second`), exactly as `studio_file.py set --second` does; it is saved only when the copy finished.
11. **Eject is refused only while the copy is reading the card.** Once the card is no longer being read (or the copy stopped), eject works as before.
12. **Every word is ours and a draft:** `report_page.OUR_WORDS` (14 lines) and `second_copy.OUR_WORDS` (32 lines): the refusals, "Ready: …", the three stopped lines ("LaCie Rugged stopped answering part way, at 240 of 3,931. Is it still plugged in?"), "1 file already on LaCie Rugged is different from your backup, so I left it alone.", "1 photo on your drive no longer matches what the backup recorded, so it was not copied.", and the "some of them came from the copy on Big Kahuna" line.
13. **A tests-only wait** (`STUDIO_SECOND_COPY_PAUSE_FOR_TESTS`) lets a copy of small pretend photos be cut off part way; nothing sets it but the test.
14. **Left for stage 5 or the close:** the report server's other POSTs still have no same-page guard (stage 5's item 6); the report's hero still says "checked against the card" of a second copy read from the drive (true by the chain of hashes, not by a fresh read of the card); the setup guides say nothing of the button.
