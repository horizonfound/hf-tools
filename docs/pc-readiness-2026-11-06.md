# The Assistant on a Windows PC: what stands in the way

Nov 6, 2026. Written for Dustin. The top part is the plain-words read; the tables below it are for whoever does the work.

**How this was made.** All 42 scripts and all 26 instruction files in the plugin were searched line by line for things only a Mac has, and the parts of each script that touch the computer (drives, folders, pictures, sound, other programs) were read in full. Not every one of the 17,600 lines was read, so a stray Mac-only line could still be hiding; step 3 of the suggested order is what would catch it. Nothing was changed and nothing was run on a PC, because there is no PC here. So every line that says what a PC "would do" is a reading of the code and of the official documentation, not something seen. Nothing in this file is called working on Windows.

**Update, later on Nov 6: the build has started.** After this list was written Dustin said go. Done since, on every script except the five another session was changing (`arrange.py`, `arrange_page.py`, `kit.py`, `posting_queue.py`, `canva_kit.py`): rows A1 and A2 (instructions), B1 to B5, E1 to E5, E7, E8, E9, F1, G1, G7, G8, G11, H1, H2, H3 and part of J. Everything now goes through one file, `scripts/this_computer.py`; `tools/check_pc.py` stops new Mac-only lines; `tests/pc_smoke.py` is the test GitHub will run on a real Windows machine once this is pushed. A whole pretend backup gives the same result on the Mac before and after. **Still nothing has run on Windows.** Still to do: the five scripts, pictures (C), sound (D), CapCut (I), the rest of F, G and J. `CLAUDE.md`, "Black Friday is back on", has the running state.

**Second update, end of Nov 6: the second pass is done, on the Mac.** Five more pieces of work, each then reviewed on a Mac and on the PC route (the Mac's own picture tool switched off), and the asks between them applied. **Still nothing has run on Windows**, so every row below marked done is "done on the Mac, unproven on a PC".

- **Pictures (C): C1 to C4 and C6 to C8 done**, plus C10. `scripts/pictures.py` makes every preview, contact sheet and sneak peek: on a Mac with `sips`, exactly as before; on a PC from the JPEG every camera stores inside its RAW (plain Python), resized with Pillow. Proven on real Canon CR2 and CR3 and a DJI DNG with `sips` switched off, and on made-up RAW files laid out the way Nikon, Sony, Panasonic, Fuji, Olympus and Pentax lay them out (`tests/pc_pictures.py`). C5 and C9 (`arrange.py`, `kit.py`) wait for the other session. Found on the way: previews of Adobe RGB photos came out dull on the PC route (fixed: turned into sRGB); a DJI DNG holds at most a 960x720 picture, so that is the biggest preview a PC can make of it; the Mac's `sips` previews are tagged Display P3 (left as they are, since the Mac must not change); a backslash bug in `sneak_peeks.py` (fixed).
- **Saves (G3, G4):** `posts.py`, `sneak_peeks.py` and `peek_sheets.py` save the safe way on both computers; a `posts.py sort` or `bring` that stops because a copy can't be made right then (a file held open, a full drive, no permission) is finished by the next run, as a cut-off sort always was. The Mac's own permission words are kept apart from the PC's. `this_computer.rename_new()` is the one "give a finished file its name, never over another" (it was `posts.into_place`).
- **Sound (D): D1 to D4 done.** `assistant-make-a-reel/scripts/sound.py` reads a song's length and sound: the Mac's `afconvert` as before; ffmpeg if it is there; on a PC with neither, Windows' own Media Foundation (written from Microsoft's documentation, never run). `reel.py sound` stops with plain words when it can't. `tests/fixtures/` holds eight synthetic click tracks and `check_sound.py`. Four older Mac faults fixed: Python 3.9 couldn't find the beat of a mono M4A or AAC (so a mono `reel.py sound` result failed); `afinfo` said 0.34 s for an M4A named .mp3 (what CapCut's library songs are); a raw .aac failed without ffmpeg; `afinfo` got the length of a raw .aac and of a header-less variable-rate MP3 wrong. Damaged or empty song files now give plain words (an empty one used to crash `beats_lite`). **Open for Dustin:** the Mac's `afconvert` route puts an MP3's beats about 12 ms late (the MP3 decoder's delay; ffmpeg and a PC are exact); left alone because the Mac must not change.
- **CapCut (I):** I2, I5 and I6 written, unproven; I1 commented; I3, I4 and I7 need one CapCut project folder from a PC. On a PC a reel made while CapCut is open waits (in `root_meta_info.studio-waiting.json`) and is added by the next reel or by `capcut.py open`, which also starts CapCut on either computer. The hook's font on a PC is CapCut's own `en.ttf` if found. CapCut's own songs keep only their played length.
- **Moving files (G2, G9, G10, E9) for sort, rename and settle: done.** On a PC, a folder another program holds open is tried again for a few seconds, then the step stops with "Something has a photo in this folder open (Lightroom, or a folder window). Close it and say go: nothing is lost, and running it again finishes the job." Running it again finishes it from its log. Two decisions made in this pass, both by design: **(1) on a Mac too**, a shoot folder named with a word Windows keeps for itself gets an underscore right after that word ("Con_", "Nul_. Family"), and the 80-character cut never leaves a space or a dot at the end; **(2) on a PC, photo and shoot-folder paths are held to 260 characters even where long paths are switched on**, because File Explorer can't open longer ones; only the Assistant's own hidden records may go past it.
- **Servers (G3 for their files, G10, H3, H4, H6 for their files, F4, F5, J1 for their files): done.** Server logs now live in `~/.studio/logs/`, never inside a backup's records (on a PC an open log would stop the settle). **New finding:** Python's own web server lets two servers share one port on Windows; `fresh.Server` stops that for the report and queue servers (`posting_queue.py` still needs it). Page servers on a PC are started with no window of their own so they outlive their starter (`CREATE_NO_WINDOW`, never with `DETACHED_PROCESS`, which would have flashed a black window for every rename). Simulated only: whether the Windows Claude app ends a command's children when the command finishes is not known, and GitHub's check of it may only say SKIP.
- **The backup's review fixes (on both computers):** a second run never writes over a file that was already at the destination, nor over a checked copy changed since; a folder holding another card's backup is refused, with a plain request for the card's own name; a backup cut off part way now carries on and copies the rest (before, the rest of the card was never copied and the backup was called finished); a finished backup plus new photos on the card asks for its own name; the backup refuses to go onto the card itself, onto the same external drive, or inside the folder being copied, checked before even the preflight's test file; the export finder never opens OneDrive's online-only photos.
- **Glue (the asks between the units):** a settle cut off just after it moved the records no longer makes the next "backup now" copy the whole card again and stop on a missing index (reproduced on the Mac with the morning's scripts, fixed in `night.py`); on a PC the Studio File keeps the drive's name and own number beside its letter, and `night.py` stops before writing anything when that letter holds a different drive today (so the card-took-the-drive's-letter check is in the scripts now, not only in the instructions); `posts.py` names a drive's top folder by the drive ("Big Kahuna (E:)") and refuses a blank place; `client_note.py told --text-file`, so what the photographer said for a client note never passes through a PC's command line (`kit.py told` still does; it is one of the held scripts).
- **Instructions and words (J3 to J7):** `parts/on-a-pc.md`, read once per conversation on a PC; `docs/SETUP-GUIDE-PC.md` is Draft 1 of the PC guide (the Upload plugin route, untried on a PC).
- **The Windows check on GitHub** now runs five tests on a real Windows machine and on a Mac: `tests/pc_smoke.py` (now with a whole backup start to finish, a rename, a capital-letters-only rename, and on Windows a settle and a rename while a photo is held open), `tests/pc_pictures.py`, `tests/backup_safety.py`, `tests/pc_servers.py` and `tests/fixtures/check_sound.py`. None has run on Windows yet: nothing is pushed. On this Mac all five pass (pc_smoke 99 of 99 with Pillow, 72 of 72 on Apple's own Python 3.9 with its 2 PC-way groups skipped; pc_pictures and backup_safety need Pillow, so they run only on a Python that has it).
- **Still open:** `posting_queue.py` and `kit.py` (the other session's): `fresh.Server`, 'Segoe UI' in their fonts, the PC folder picker (F2), "Open in CapCut" through `capcut.open_capcut()` (F3), `kit.py told --text-file`, their saves (G3), the lock (G5), C5 and C9. Every record keeps folders by drive letter, so a drive that comes back under a new letter is "the drive that was E:" until it gets its old letter back; keeping each drive's own number beside the paths (backup records, the card ledger, the queue, the report and home pages) is a design job of its own. What a PC student is asked to install (Python, Pillow) is still yours to decide. Two of the held scripts stop a PC student early: `posting_queue.py` runs at the start of every conversation and serves the home page, and writes its page with no encoding named (it crashed in an old code page on the Mac; on a US PC the page's punctuation would show garbled); `kit.py facts` uses `%-d`, which Windows refuses, so a post kit stops on a PC, and `kit.py told` with an emoji left `told.json` empty in an old code page. The upload file `dist/The-Assistant.zip` (Nov 6, 1:31am) holds none of the PC pieces; it needs rebuilding with `tools/build_zip.sh` before the PC guide's Upload route can be tried.
- **A change on the Mac to know about:** the backup now refuses to copy a folder onto the same drive it is on ("back up the Jones folder on the orange drive" stops when the orange drive is also where shoots go), since a copy there is not a second place. Before, it was copied. Yours to keep or not.

*(The short answer below is the read from before the build started; the two updates above say where it stands now.)*

---

## The short answer

**Today it would not get through a first backup on a PC.** It would stop in the first minute. That is not one big problem; it is about seventy small and medium ones and three large ones. The good news is that the safety core (copy, check every file, never overwrite) is plain Python that Windows also runs, and I found nothing that would change a memory card or write over a photo on a PC. The failures are all of the "it stopped" kind, which is the rule the product is built on.

### What already has a Windows way written (never run)

Somebody thought ahead in these places. Each has code for a PC; none has ever been tried:

- Hiding the backup's records folder (`backup.py`, `settle.py`).
- Telling the computer's own disk from an external drive (the "teachable moment").
- Where CapCut keeps its projects on a PC, the name of its project file there, and checking whether CapCut is open.
- Opening a folder window, and opening CapCut from the kit page.
- Folder and file names: the characters Windows refuses (`: ? * " < > |`) are already cleaned out of shoot names, and names are kept short.
- Six scripts already fall back to a second picture tool (Pillow) when the Mac's own is missing.
- Renaming a shoot when only capital letters change (the Oct 28 near-miss) is handled in a way that should hold on a PC's drives too.
- The reading of camera facts (date, camera, lens), the sorting into shoots, the pacing of a reel, the queues and every page's design are plain Python and HTML with nothing Mac-only in them.

### What is missing

Three large pieces:

1. **Pictures.** Every preview, every contact sheet Claude looks at, every sneak peek, every sized post and every picker thumbnail is made by a tool only Macs have (`sips`). Eleven scripts use it. Five of them have no second way at all, and the second way in the other six cannot open a RAW file. A PC needs a new piece that pulls out the small JPEG the camera already tucked inside each RAW, plus Pillow to resize.
2. **Sound.** Finding the beat of a song and pulling the sound out of a screen recording both use tools only Macs have. Windows has nothing built in that a script can simply call to open an MP3 or M4A. Something has to be installed, or a harder Windows-only route has to be proved on a real PC.
3. **Drives and cards.** Finding the memory card, listing the drives to choose from and spotting a card on the home page all look in the one place a Mac puts drives. On a PC they would find nothing. Windows uses drive letters (E:, F:) and the code has to learn them.

And one thing before any of that: **a PC has no Python.** A Mac offers to install it with one click. On a PC the photographer has to install it, and "Nothing to install" stops being true. That is a wording decision for the two of you (see "Yours to decide").

### What would stop it in the first minute, in order

1. No Python on the PC, and the instructions call it by a name (`python3`) that only some ways of installing it provide.
2. The check for free room on the drive uses a call Windows does not have. The backup would stop with an error before copying.
3. Dates written like "October 24" use a spelling of the date code that Microsoft's version does not have. The report, the index and the folder names would stop.
4. Anything outside plain English letters (an emoji in a caption, an accent in a name, even the little dot between words on the pages) can stop a save or show up as garbage, because Windows uses a different default way of storing text than a Mac. About 210 places.
5. Every preview fails (see Pictures above), so Claude has nothing to look at.

### What is risky even once those are fixed

These are the ones that only a real PC can settle, and they are the ones I would worry about:

- **Other programs holding files.** On Windows, a folder cannot be renamed while Lightroom, an Explorer window or the virus checker has a file in it open. Renaming a shoot and moving shoots into place both rename whole folders. On a Mac this never fails; on a PC it can stop half way. The logs already make that recoverable, but it has never been tested, and the message would be a raw error.
- **Drives formatted for both Mac and PC (exFAT).** The fast "is this the very same file" check after a move relies on something Windows does not promise on those drives. Sorting and renaming fall back to reading the file in full (slower, still safe). The last step, moving shoots into place, has no fallback and could report every photo as "not the same file" when nothing is wrong.
- **The little page servers.** They are started in a way that keeps them alive on a Mac after Claude's command ends. That switch does nothing on Windows. Whether the pages stay up inside the Claude app on a PC is not known.
- **Updates.** The trick that restarts a page after an update behaves differently on Windows and is known to trip on a space in a folder name (and Windows user folders often have one: "Jane Doe").
- **CapCut on Windows.** The project format there may be locked in some versions. Reports on the internet disagree. Nobody here has seen a PC project.
- **How Claude runs commands on a PC.** Without an extra program (Git) Claude uses Windows' own command line, which reads some of our commands differently. The official docs do not say exactly how the desktop app behaves.

### Yours to decide (Dustin and Nicole)

- **"Nothing to install."** On a PC the honest line is "one install" (Python) and probably one more line for pictures and sound. What a PC student is asked to do in setup is a product call. The smallest version I can see: install Python from the Microsoft Store, then Claude runs one line itself.
- **iPhone photos (HEIC) on a PC.** They need one more add-on, or the PC version says plainly that it wants JPEGs. Finished exports from Lightroom are JPEGs, so this only touches phone photos dropped in for posts.
- **Which PC to test on.** Parallels on a newer Mac runs a different kind of Windows than most PCs have (see "What needs a real PC"). The PC student in the beta is the real test.

### Suggested order

1. **One "which computer am I on" file.** Today the Mac-only calls are scattered through 25 scripts. Put every one of them behind a single helper (free room, hide a folder, keep awake, list drives, find a card, open a folder, pick a folder, lock, start a page server, save text, write a date). Each script then asks the helper. Nothing changes on the Mac; it only makes the next steps one-file jobs. Note: another session is editing `arrange.py`, `kit.py` and `posting_queue.py` right now, so this waits for that.
2. **The first-minute stops** (free room, dates, text, names). All provable on the Mac.
3. **A Windows check on GitHub.** The project already has a check that runs on every push. GitHub can run the pretend backup on a real Windows machine the same way. No screen, no card, no CapCut, no Claude app, but real Windows, every push. This catches most of the list without owning a PC. (Free for a public project as far as I know; worth confirming for this one.)
4. **Pictures.** The embedded-JPEG piece plus Pillow, used everywhere `sips` is. Provable on the Mac by hiding `sips` and running the pretend backup.
5. **Drives, cards, folder windows, the folder picker.** Written on the Mac, proved on a PC.
6. **CapCut.** Before writing anything: ask the PC student to send one CapCut project folder. Five minutes of their time tells us whether the format is readable.
7. **Sound.** Decide the route (below), prove it on a PC.
8. **Words.** One pass so pages and instructions say "File Explorer" and "PC" on a PC.
9. **The full rehearsal on a PC,** from the install guide on, the way the Mac one was done.

### What needs a real PC or Parallels to prove

A real PC (or Parallels) is the only way to prove: the install from scratch in the Claude app; a card going in and being found; drive letters and names; folder windows coming to the front; the folder picker; the pages staying up; the PC staying awake through a long copy; Lightroom holding files during a rename; an exFAT drive; CapCut opening a project we wrote; reading a song; the phone tap; dictation.

About Parallels: on a Mac with an Apple chip it runs the "ARM" kind of Windows 11, while most PCs are the other kind. It is good for most of the list above. It is weaker for two things: CapCut (may behave differently or not have an ARM version) and installing the add-ons. I have not checked which chip Dustin's Mac has or what CapCut offers for ARM; treat both as not known. A real PC tester is still needed before anything is claimed.

---

# The full list

**How to read it.**
- *Where*: file and function. Line numbers are as of the morning of Nov 6; `arrange.py`, `kit.py` and `posting_queue.py` are being edited by another session, so theirs may have moved.
- *On a PC today*: read from the code and docs, not seen.
- *Size*: small (an hour or two, one place), medium (a day, several places), large (several days or a new piece).
- *Prove on*: **Mac** = can be proved without a PC. **GitHub** = real Windows through GitHub's check, no screen. **PC** = needs a real PC or Parallels.

## A. Before anything runs

| # | Where | What it is for | On a PC today | The Windows way | Size | Prove on |
|---|---|---|---|---|---|---|
| A1 | `studio-manager/SKILL.md` line 14; `README.md` line 30 ("Nothing to install: the scripts run on the Python a Mac already has") | The scripts need Python. A Mac offers to install it. | No Python. Typing `python` or `python3` with a script after it returns an error from a Microsoft Store shortcut [P1]. The paragraph that tells Claude what to say only knows Apple's window. | Install step: the Python Install Manager, from the Microsoft Store or `winget install 9NQ7512CXL7T` [P1]. Add a PC paragraph beside the Mac one: when the output says Python was not found, tell them the one step. | Small (words), plus the guide | PC |
| A2 | 30 command lines in 9 instruction files (`SKILL.md`, reel `SKILL.md`, `parts/arrange.md`, `backup.md`, `hello.md`, `post-kit.md`, `sneak-peeks.md`, `after-the-report.md`, `first-backup-setup.md`); `night.py` lines 320, 323 print `python3 ...` for Claude to run | The name Claude calls Python by | `python3` exists after the Install Manager or the old Store package. The older python.org installer gives `python` and `py`, and may not add either to the path [P1]. | Have the guide use the Install Manager so `python3` exists; tell Claude in the core instructions to use `py` or `python` if `python3` is not found. | Small | PC |
| A3 | No file yet | Pictures and sound need add-ons on a PC (see C and D) | Nothing there | One line Claude can run after Python is in: `python -m pip install pillow` (and whichever sound piece is chosen). Whether the Install Manager's Python includes pip was not confirmed [P1]. | Small | PC |
| A4 | All scripts | The scripts were written for Python 3.9 (the Mac's) and run on 3.12 (Dustin's) | A PC gets the newest Python (3.14 today). Never run on it. From 3.15, text handling changes for the better (see B3) [P3]. | Run the tests on the newest Python. | Small | Mac, GitHub |
| A5 | Every command in the instruction files | How Claude runs our commands | With Git for Windows installed, Claude uses a Mac-like command line. Without it, Claude uses PowerShell [C2]. PowerShell reads some things differently: a list written `s1=14,3,27,9` (the sneak-peek pick) may be split apart, and `&&` between commands fails on the older PowerShell every PC has. Which one the desktop app uses for its commands is not stated in the docs [C2]. | Put quotes around every argument with a comma; one command per line; test both ways. Or make Git for Windows part of setup (one more install). | Medium | PC |

## B. Stops on first use

| # | Where | What it is for | On a PC today | The Windows way | Size | Prove on |
|---|---|---|---|---|---|---|
| B1 | `backup.py` `free_bytes()` line 85; `night.py` `preflight()` line 101 and `main()` line 214; `studio_file.py` `drives()` line 168 | "Is there room on the drive?" before a byte is copied | `os.statvfs` does not exist on Windows [P4]. `backup.py` and `preflight` would stop with an error (the code only expects a different kind of error). The low-disk note in `--check` is quietly skipped. | `shutil.disk_usage(path)`, which works on both [P4]. | Small | Mac, GitHub |
| B2 | `index.py` 69; `groups.py` 70, 104; `report_page.py` 144, 188, 191; `first_look.py` 328; `kit.py` 1201, 1311; `posts.py` 283; `studio_file.py` 36, 51–55, 241 (and the `date_format` saved in each photographer's Studio File) | Dates in words: "Saturday, October 24", "9:05 am", and the second offered folder pattern "Smith Family, Oct 18 2026" | The code `%-d` (day without a leading zero) is not something Microsoft's formatter has; its spelling is `%#d` [P9]. Python's docs do not say what happens; it is widely reported to stop with "Invalid format string". Not run. | Build the number in Python (`d.day`, `d.hour`) in one shared date helper. `studio_file.render()` translates a saved `%-d` when it uses it, so a Studio File made on a Mac still works on a PC. | Small to medium (17 places, 7 files) | Mac, GitHub |
| B3 | About 210 text reads and writes with no encoding named, in 30 scripts (only 24 places name one; `capcut.py` is the tidy one). Every `say()` and `print()`. Three reel scripts already set the output to UTF-8 (`make_reel.py` 33, `find_music.py` 14, `check_setup.py` 11). | Saving and reading every record, every page, every caption | On Python 3.9 to 3.14 Windows stores text in an older code page unless told otherwise, and output sent to Claude uses it too [P3]. An emoji in a caption, or the "↗" used on a page, cannot be written that way: the save stops. Characters that can be written (é, ·, curly quotes) are stored in a form the pages (which say they are UTF-8) show as garbage. | `encoding="utf-8"` on every text read and write (or one shared read/write helper); `sys.stdout.reconfigure(encoding="utf-8")` at the start of every script; set `PYTHONUTF8=1` for the page servers started by other scripts [P3]. | Medium (mechanical, nearly every file) | Mac (Python's own `-X warn_default_encoding` lists every missed spot), then GitHub |
| B4 | `backup.py` `main()` (folder = date + name, about line 205); `night.py` `main()` (about line 197) | The backup's day folder, named from what Claude passes | The name is used as given. A colon or question mark in it ("Card 10:30") is refused by Windows [W14]; it would arrive as a raw error. | Run the name through `sort.safe_folder()` first. | Small | Mac |
| B5 | `sort.py` `safe_folder()` 43; `studio_file.py` `render()` 238; `capcut.py` `folder_name()` 442; `posts.py` kit folders | Folder names from what the photographer said | Characters are cleaned, trailing dots and spaces are trimmed. Not handled: the handful of names Windows keeps for itself (CON, PRN, AUX, NUL, COM1–9, LPT1–9), even with an ending [W14]. A shoot called "Con" or "Aux" would fail. | Add the reserved names to the one name-cleaning helper (put an underscore after them). | Small | Mac |

## C. Pictures (`sips`)

One shared picture helper would replace all of these. On a PC it needs two things: **(1) a new piece that pulls out the JPEG the camera stored inside each RAW file** (pure Python, beside `exif_read.py`, which already walks the same files: CR2, NEF, ARW, DNG, ORF, RW2, PEF, CR3, RAF), and **(2) Pillow** to resize, pad, crop and turn photos the right way up. Pillow has Windows versions and reads JPEG, PNG, TIFF, WebP; it does not read camera RAW, and reads iPhone HEIC only with a second add-on, `pillow-heif` [K25]. Windows' own picture tools read JPEG, PNG, TIFF and BMP but not HEIC or RAW unless extra pieces from the Microsoft Store are present, which varies by PC [W23].

| # | Where | What it is for | On a PC today | Size | Prove on |
|---|---|---|---|---|---|
| C1 | `previews.py` `make_preview()` 33 | The first small pictures from a backup | No second way. Fails. | Part of the large piece | Mac (hide `sips`), then PC |
| C2 | `groups.py` `make_preview()` 63 | Four previews per group, for the one look that sorts a card into shoots | No second way. Fails; Claude has nothing to look at. | Same | Same |
| C3 | `sheet.py` `thumb()` 62 | The contact sheet itself | No second way. Fails. | Same | Same |
| C4 | `first_look.py` about 334–349 | The big version of a preview on the report (click to enlarge) | No second way. Falls back to the small one or none. | Same | Same |
| C5 | `arrange.py` `_sips_copy()` 374, used by `make_one()` | The reel picker's small copies of each photo | No second way. The picker shows no photos. (Being edited by another session.) | Same | Same |
| C6 | `peek_sheets.py` 50–75 | The sneak-peek pages Claude picks from | Has a Pillow stand-in, but Pillow cannot open a RAW, so on a real card it fails. | Same | Same |
| C7 | `sneak_peeks.py` 172–190 | The six sneak peeks shown on the report | Same as C6. | Same | Same |
| C8 | `posts.py` `preview()` 226, `thumb_rows()` 239 | Looking at finished photos brought in for posts | Pillow stand-in written; works for JPEG, PNG, WebP if Pillow is installed; HEIC no. Sideways photos may show sideways (the stand-in does not turn them). | Small once the helper exists | Mac |
| C9 | `kit.py` `size_of()` 323, `shape()` 376 | Sizing singles, carousel slides and stories to Instagram's shapes | Pillow stand-in written, including the turn. HEIC no. | Small | Mac |
| C10 | `reel.py` `_thumb()` 93; `capcut.py` `photo_size()` 218, cover at 526 | The reel's contact sheet; a photo's size so it fills the frame; the project's cover picture | Sheet: Pillow stand-in. Size: read in plain Python for JPEG and PNG; HEIC and TIFF come back as "unknown" and would not fill the frame. Cover: copied only if the first photo is a small JPEG. | Small | Mac |

Overall size for C: **large** (the embedded-JPEG piece is new work; the rest is swapping calls). Most of it can be proved on the Mac by running the pretend backup with `sips` hidden and comparing with what `sips` makes. A PC is needed for the Pillow install and for speed (the Mac takes about half a second per RAW; a PC's time is unknown).

## D. Sound

| # | Where | What it is for | On a PC today | Size | Prove on |
|---|---|---|---|---|---|
| D1 | `beats_lite.py` `decode()` 89–115 | Hearing the song so the photos cut on the beat | Uses the Mac's `afconvert`; then `ffmpeg` if it happens to be installed; otherwise only a `.wav` file works. An MP3 or M4A gets "this computer has no way to read that kind of song file". | See below | PC |
| D2 | `reel.py` `cmd_sound()` 462–490 | Pulling the song out of a screen recording | `afconvert` only. Stops with a message that names the Mac. | See below | PC |
| D3 | `capcut.py` `song_length()` 237–256 | How long the song is | Mac's `afinfo`, else `ffprobe`, else `.wav` only. An MP3 on a PC comes back as zero seconds. | Small (an M4A's length can be read in plain Python; an MP3's with a little more) | Mac |
| D4 | `beats_lite.py` line 103 (`os.symlink`) | Giving a mis-named CapCut song its right ending for the Mac tool | Only inside the Mac branch. Windows needs special permission to make such links [P11], so the replacement must not use one. | Goes away with D1 | n/a |

**What reads an MP3 or M4A on Windows with nothing installed?** No built-in command was found [W22]. The choices:

1. **Windows' own media engine, called through PowerShell** (the "MediaTranscoder", which can write a WAV) [W22]. Nothing to install. But calling it from PowerShell needs a workaround that only community posts describe, and the "N" editions of Windows sold in Europe do not include the MP3 and AAC readers until the owner adds them [W22]. Unproven; needs a PC.
2. **ffmpeg, installed with the same line as Pillow:** `pip install imageio-ffmpeg` carries its own copy (about 39 MB on Windows) [K26]. The code already knows how to use ffmpeg. Simplest to build. It is one more thing installed.
3. **ffmpeg installed by itself** (`winget install Gyan.FFmpeg`, a community-kept package) [K26].
4. CapCut for Windows appears to carry its own `ffmpeg.exe` (seen only in an uninstaller's file listing, not confirmed) [K28]. Not recommended: it is another company's file and could move with any update.

My recommendation: try 1 on a real PC first because it keeps "one install"; fall back to 2. Size: **medium** with route 2, **large** with route 1.

## E. Drives and cards

| # | Where | What it is for | On a PC today | The Windows way | Size | Prove on |
|---|---|---|---|---|---|---|
| E1 | `studio_file.py` `drives()` 160–185 | The list of drives offered in setup ("Big Kahuna, 18 TB free") | Looks only in `/Volumes`. Returns an empty list. Its rules for what to leave out are Mac ones (Macintosh HD, Time Machine). | List drive letters with their names, kind (removable or fixed) and free room: `GetLogicalDriveStringsW`, `GetVolumeInformationW`, `GetDriveTypeW` through Python's built-in `ctypes`, or PowerShell's `Get-Volume` [W21]. Leave out the system drive and any recovery volume. | Medium | PC |
| E2 | `home.py` `card_in()` 159–172 | "A card is in right now" on the home page | `/Volumes` only. Never sees a card. | Same list as E1: a removable drive with a `DCIM` folder. | Small once E1 exists | PC |
| E3 | `parts/backup.md` lines 7, 20, 26 | Tells Claude to find the card in `/Volumes` and shows `/Volumes/EOS_DIGITAL` | Claude would look in a folder that does not exist, then improvise. | Have a script find the card (`studio_file.py cards` or similar) and have the instructions call that on both systems. | Small | PC |
| E4 | `posts.py` `named_place()` 157–169, `places()` 132–149 | "Where should your content live?" by drive name | Tries `/Volumes/<name>`. A drive given as `E:` (no slash) joins wrongly in Python: `E:` + `The Assistant` means "the current folder on E", not the top of E. "Pictures, on this Mac" wording. | Match by drive name from E1; always add the slash after a drive letter. | Small | Mac for the join, PC for the rest |
| E5 | `cards.py` `volume_uuid()` 32–37 | One of the facts that recognises a card already backed up | Uses the Mac's `diskutil`; quietly returns nothing elsewhere. The card is still recognised by its files (count, size, a sample), so this is a nice-to-have. | The volume's serial number from `GetVolumeInformationW`. It changes when the card is formatted, which is what we want [W21]. | Small | PC |
| E6 | `studio_file.py` `on_internal_disk()` 187–204 | The teachable moment: is this the computer's own disk? | A Windows way is written (the system drive letter). Never run. A second built-in disk (D:) would count as external; arguably fine. | As written; decide about D:. | Small | PC |
| E7 | `backup.py` `SKIP_DIRS` line 20; `cards.py` `SKIP_DIRS` line 29 | Leaving the system's own housekeeping folders out of a backup | "System Volume Information" is skipped. `$RECYCLE.BIN` (Windows' recycle folder on hard drives) is not, so backing up a folder on a drive could copy deleted files. `studio_file.py` line 149 already knows the name. | Add `$RECYCLE.BIN` to both lists. | Small | Mac |
| E8 | `find_exports.py` `candidate_folders()` 89; `posts.py` `places()` 144; `reel.py` songs line 230 | Looking in Pictures, Desktop, Downloads, Music for exports and songs | Assumes they sit under the home folder. On many PCs Windows moves Pictures, Desktop and Documents into OneDrive, so these folders may be empty or elsewhere. | Ask Windows where each really is (`SHGetKnownFolderPath` through `ctypes`). | Small to medium | PC |
| E9 | `sort.py` 207, 264; `rename_shoot.py` 183, 209; `settle.py` `identity()` 68 and `finish()` 160; `posts.py` `identity()` 516 | The instant proof that a moved file is the very same file (Oct 24: "less re-reading") | On NTFS (Windows' own format) the file's number stays put. On FAT drives Microsoft says it can change, for example on a rename to a longer name; exFAT is not mentioned either way [W15, P10]. `sort.py` and `rename_shoot.py` then read the file in full (slower, safe). **`settle.py` has no such fallback** and would report "not the same file after the move". | Give `settle.py` the same fallback (read and compare with the backup's hash). Test on an exFAT drive. | Small to write | PC with an exFAT drive |

## F. Folder windows, pickers, other apps

| # | Where | What it is for | On a PC today | The Windows way | Size | Prove on |
|---|---|---|---|---|---|---|
| F1 | `finder.py` `open_folder()` 49–80 (used by `serve_report.py`, `edit_queue.py`, `posting_queue.py`) | Every "Open photo folder" button | A Windows branch exists: it runs `explorer <folder>` and always reports success without checking. Explorer handed a path with forward slashes opens Documents instead (from experience, not confirmed in Microsoft's docs). No "came to the front or stayed behind" check, no reuse of a window already showing the folder. The words say "Finder" and "Dock". | `os.startfile(folder)` with the path in Windows form; check the folder exists first; look for an open window through `Shell.Application` if twins turn out to be a nuisance. | Small to medium | PC |
| F2 | `posting_queue.py` `pick_folder()` 891–917 | "Select the folder with your finished photos" (the safe way in, since dragging can move files) | Refuses on anything but a Mac and tells them to drag instead, which is the risky way; the hint says "hold the Option key". Explorer has the same rule as Finder: a drag within one drive moves. | Windows' own folder window through PowerShell (`System.Windows.Forms.FolderBrowserDialog`) or Python's `tkinter` if it is present [W20]. On Windows the key that forces a copy is Ctrl. | Medium | PC |
| F3 | `posting_queue.py` `open_capcut()` 725–742 | "Open in CapCut" on the kit page | Windows branch written: `os.startfile("CapCut")`. That only works if CapCut registered that short name with Windows; not known. | Find `CapCut.exe` under `%LOCALAPPDATA%\CapCut\Apps\` or its Start-menu shortcut and start that. | Small | PC with CapCut |
| F4 | `night.py` `open_report()` 383 | Showing a report from a plain terminal (not the app) | Windows branch written (`cmd /c start`). Never run. | As written. | Small | PC |
| F5 | `return_watch.py` (whole file) | The experiment that notices they are back and puts the report up again | Mac only by design; says so and exits. Not wired into the backup. | `GetLastInputInfo` and `GetForegroundWindow` through `ctypes`, if the experiment is kept. | Medium; not needed for launch | PC |
| F6 | `home.py` copy buttons; every page | The Copy button and pages in the Claude app's pane | The pane on Windows is not described as the same or different in the docs [C4]. The Mac pane refused the modern clipboard call and allowed the older one; the PC pane's behaviour is not known. | Test. | Unknown | PC |

## G. Files: hiding, moving, locking, names

| # | Where | What it is for | On a PC today | The Windows way | Size | Prove on |
|---|---|---|---|---|---|---|
| G1 | `posts.py` `hide()` 152 (Mac only); every folder or file hidden by a leading dot: `.kit` in each post kit, `.studio` in The Assistant folder, `.part-…` scratch files, `.thumb.bmp`, `.studio-write-test`, `~/.studio` | Keeping the Assistant's own files out of the photographer's sight (Oct 30: "the photographer sees only the photo folders") | A leading dot hides nothing on Windows. They would see `.kit` in every kit. `backup.py` `hide()` and `settle.py` line 132 do have the Windows way (`attrib +h`) [W19]. | One shared `hide()` used wherever a dot folder is made. | Small | GitHub (the mark is set), PC (how it looks) |
| G2 | `rename_shoot.py` 187 (whole folder), 195, 343; `settle.py` 136 (records), 218 (whole shoot folder); `sort.py` 208 | Renaming a shoot; moving shoots into place | Windows refuses to rename a folder while any program has a file inside it open: Lightroom, an Explorer preview, the virus checker reading a new file. On a Mac this cannot happen. The run would stop part way with a raw error. The logs are written first, so a second run should finish it, but that has never been tried on Windows. | Catch the "in use" error, wait and try again for a few seconds, then say plainly "Close Lightroom (or the folder window) and say go". | Medium | PC with Lightroom open |
| G3 | Every "written whole, never half" save: `edit_queue.py` 94, `posting_queue.py` 115, 442, `kit.py` 144, 257, 528, `home.py` 71, `client_note.py` 102, 284, `posts.py` 574, `arrange.py` 234, `sneak_peeks.py` 253, `fresh.py` 48, `capcut.py` 455 | Saving a list while a page may be reading it | On Windows the swap can fail if another process has the file open at that instant (a page server reading the queue while a command saves it). Rare and random. | One save helper that tries again a few times on "in use". | Small to medium | GitHub (a stress test), PC |
| G4 | `kit.py` 135, 354; `canva_kit.py` 98, 126; `posts.py` 94–101, 545, 663, 724; `rename_shoot.py` 69 | Giving a finished file its real name | `os.rename` onto a name that exists replaces it on a Mac and is an error on Windows [P8]. For "never write over anything" that error is the safe result, but it arrives as a raw error, not plain words. Each place needs a look. | Check first and say why, or use the helper from G3. | Small | GitHub |
| G5 | `kit.py` `_held()` 532–571; `arrange.py` 73, 153–179, 800–810, 1320–1346 | Making sure two things never save the same kit at once | The lock call (`fcntl`) does not exist on Windows [P5]. Both scripts notice and carry on with no lock between processes. Two saves at the same moment could lose one. | `msvcrt.locking` on the first byte of the lock file [P5]. (Being edited by another session.) | Small to medium | GitHub |
| G6 | `kit.py` `_pid_gone()` 587–596; `arrange.py` 777–790 | "Has that earlier run ended?" before sweeping its scratch files | Guarded correctly: on Windows the Mac's way of asking would end the other process [P6], and the code never does it there. Scratch files wait a day instead. | Fine as it is. Could ask properly with `OpenProcess` later. | None needed | GitHub |
| G7 | `backup.py` line 141 (`key = str(rel)`), 282; `sneak_peeks.py` 304. Compare `cards.py` 49, `posts.py` `walk()`, `sort.py` (forward slashes always) | The path of each photo inside the backup's records | On Windows `backup.py` would write `DCIM\100CANON\IMG_1.CR3` while other scripts write and expect `/`. `posts.py` 317–343 and 509–511 split on `/`. A drive used on both a Mac and a PC would carry records in two spellings. | Always write records with forward slashes (`as_posix()`); read either. | Small to medium | Mac, GitHub |
| G8 | `serve_report.py` line 73 | "No file paths on the page" when a rename fails | Looks for `/` only; a Windows path (`E:\...`) would slip through onto the page. | Check for `\` and a drive letter too. | Small | Mac |
| G9 | Kit folders, picker previews, CapCut project folders | Long paths | Windows stops at 260 characters unless an administrator has switched long paths on [P13]. Names are already capped (80 and 40 characters), so this bites only where the home folder is long, typically inside OneDrive ("C:\Users\First Last\OneDrive - Company\Pictures\The Assistant\Your Content\…"). | Keep the Assistant's own file names short; check the length before writing and say so plainly. | Small | PC |
| G10 | `where.py` line 52; `fresh.py` `announce()` 41 | Comparing two folder paths as text | `e:\photos` and `E:\Photos` are the same folder on Windows but different text. | Compare with `os.path.normcase()`. | Small | GitHub |
| G11 | `backup.py` line 303 | The report line "N hidden Mac system files left behind" | Wrong word on a PC. | "hidden system files". | Small | Mac |

Case of letters: Windows' drives ignore capital letters the same way a Mac's do [W16], and the Oct 28 fix (look at the folder's exact listing) is the right approach for both. Unproven on Windows.

## H. Staying awake, page servers, the internet

| # | Where | What it is for | On a PC today | The Windows way | Size | Prove on |
|---|---|---|---|---|---|---|
| H1 | `night.py` `run()` 46–52 | Keeping the computer awake through a long copy ("You can walk away") | Mac only (`caffeinate`). On a PC nothing stops it sleeping mid-backup; the backup would pause and need running again. | `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)` through `ctypes` inside the long-running script, cleared at the end. Like the Mac, it cannot stop a closed lid [W18]. Whether the Claude app on Windows has its own keep-awake is not in the docs [C10]. | Small | PC (start a long copy and leave it) |
| H2 | `night.py` 369; `home.py` 498; `serve_report.py` 118, 145; `arrange.py` 489, 843 | Starting a page's little server so it outlives the command that started it | The switch used (`start_new_session`) is for Mac and Linux only [P7]; Windows ignores it. Whether the server survives when Claude's command ends is not known. | `creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` (and `CREATE_NO_WINDOW` so no black window flashes) [P7]. | Small | PC, inside the Claude app |
| H3 | `fresh.py` `restart()` 131–171 (line 168, `os.execv`) | A page restarting itself after the Assistant updates | On a Mac the process replaces itself. On Windows a new one starts while the old one exits (per Python's bug tracker, not its docs) [P12], and from memory the same call mishandles a space in a path, which Windows user folders often have. The page could fail to come back after an update. | Start the new server as in H2, then exit. | Medium | GitHub, then PC |
| H4 | `night.py` 366; `serve_report.py` 116, 143; `home.py` 497 | Each server's log file | A server keeps its log open inside the records folder; on Windows that alone can block the folder from being moved later (see G2). | Keep server logs in `~/.studio`, not in a folder that moves. | Small | PC |
| H5 | `canva_kit.py` `curl()` 58, 71, 115; `posting_queue.py` `fetch_tile()` 458 | Sending a photo to Canva, fetching Canva's export, fetching Instagram grid pictures | Windows 10 and 11 include `curl` [W17]. Never run there. The messages say "the Mac's own curl". | As written; fix the words. | Small | PC |
| H6 | `fresh.py` `WAIT_PAGE` 107; `arrange_page.py` | The typeface of the "one moment" page and the picker | The font list starts with Apple's and never names Windows' own (Segoe UI); a PC falls through to Arial. Looks only. | Add `"Segoe UI"` or `system-ui`. | Small | PC (looks) |

## I. CapCut on Windows

Nothing here has been seen on a PC. CapCut publishes nothing official about its project files; everything below is from community sources and is marked that way in the sources.

| # | Where | What it is for | On a PC today | Size | Prove on |
|---|---|---|---|---|---|
| I1 | `capcut.py` `default_store()` 64–71 | Where CapCut keeps projects | Windows guess written: `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`. Community sources agree [K27]. | None if right | PC with CapCut |
| I2 | `capcut.py` `draft_file_name()` 87 | The name of the project file | Writes `draft_content.json` on Windows. One source says CapCut keeps both that and an older `draft_info.json` side by side [K27]. Whether a project with only one of them opens is not known. | Small | PC with CapCut |
| I3 | `capcut.py` `write()`, `their_platform()` 91–110 | Writing a project CapCut will open | **Sources conflict on whether recent versions lock (encrypt) the project file** [K27]. If CapCut for Windows locks it, the reel route does not work on a PC as built. `their_platform()` already treats an unreadable project as "use our own values". | Unknown until seen | PC with CapCut |
| I4 | `references/capcut/` (three template files) | The pieces our projects are built from | Taken from CapCut 9.6 on a Mac. They carry Mac-side values. A PC may want its own set. | Medium if needed | PC with CapCut |
| I5 | `capcut.py` `build()` 305–326, 379, 407 versus `native()` 467 | The address of each photo inside the project | The song and the project folders are written with forward slashes for Windows; the photos' own paths are written as given (backslashes on a PC). Which form CapCut for Windows expects is not known. | Small | PC with CapCut |
| I6 | `capcut.py` `capcut_open()` 74–84 | "Is CapCut open?" | Windows way written (`tasklist`, looking for `CapCut.exe`). Never run; the program's name there is a guess. | Small | PC with CapCut |
| I7 | `capcut.py` write of `root_meta_info.json` 540–550; `capcut_songs()` 126 | CapCut's own project list; songs from CapCut's library | Whether the list file has the same name and shape on Windows, and where library songs are cached, were not confirmed [K27]. | Small to medium | PC with CapCut |

Overall size for I: **medium to large**, entirely unknown until a PC project is in hand. Cheapest first step: the PC student zips one CapCut project folder and sends it.

## J. Words a photographer sees, and the instructions Claude follows

| # | Where | What it says | The Windows way | Size |
|---|---|---|---|---|
| J1 | `serve_report.py` 291, 294; `edit_queue.py` 313–316; `posting_queue.py` 845, 958; `report_page.py` 472, 493 | "Opened X in Finder", "Click Finder in the Dock to see it", "Open this folder in Finder" | A switch like `brand.py`'s: "Finder" or "File Explorer", "the Dock" or "the taskbar". | Small |
| J2 | `posting_queue.py` 735, 906, 909; `posts.py` 146; `reel.py` 472 | "on this Mac", "hold the Option key so it copies", "the Mac's own afconvert is missing" | "this computer" everywhere; Ctrl on a PC. | Small |
| J3 | `parts/first-backup-setup.md` 21, 23, 27, 46; `parts/photos-in.md` 7, 14; `parts/hello.md` 24; `parts/backup.md` 28, 36, 40; `parts/posting-queue.md` 15; `parts/editing-queue.md` 8; `parts/where-things-live.md` 7; reel `SKILL.md` 12, 90, 146; `README.md` 3, 30 | "A folder on this Mac", "Leave out the Mac's own startup disk and any Time Machine drive", "It keeps the Mac from dozing off", "Finder moves a folder dragged within the same drive", "hidden in Finder", "Nothing has to be installed on a Mac" | One pass: "this computer", and where the two differ, a line for each. | Medium (one careful pass) |
| J4 | `parts/backup.md` line 11 | "press the mic key on your keyboard" (Mac dictation) | On Windows: the Windows key and H; needs the internet and the cursor in a text box [W24]. | Small |
| J5 | `parts/backup.md` line 15 | Sending an iMessage from the Mac's Messages app when a card finishes | Mac only, and already dropped on Oct 28 (CLAUDE.md, "The phone tap"). The line is still there. Remove it for both. | Small |
| J6 | `studio-manager/SKILL.md` 57; `parts/backup.md` 32; `parts/arrange.md` 27 | Bringing the page forward with the app's show-pane tool; "`open` the address" outside the app | Whether the same tool exists in the Windows app is not known. `open` is a Mac command (`start` on Windows). | Small |
| J7 | `docs/SETUP-GUIDE.md` and the PDF in `docs/install-guide/` | The install guide and its drawings | Mac only (Apple's developer-tools window, the gear by the name, Cmd keys). A PC edition is its own job. | Medium |

## K. The Claude app on Windows (from Anthropic's documentation)

These were checked against the official docs on Nov 6. The quotes were read through a summarising tool, so the facts are paraphrased here; re-read the page before quoting it anywhere.

| # | Question | What the docs say | Status |
|---|---|---|---|
| K1 | Is the Code tab in the desktop app on Windows? | Yes; the download page offers it for ordinary (x64) PCs and for ARM ones [C1]. | Confirmed in docs |
| K2 | Does it need Git for Windows? | Optional. Recommended so Claude can use its Mac-like command line; without it Claude uses PowerShell [C2]. | Confirmed for the command-line Claude; the desktop app's own behaviour is not stated |
| K3 | The browser pane and our pages | The pane exists on Windows (it has a Windows shortcut). Nothing says it behaves identically [C4]. | Not known |
| K4 | Installing a plugin | The docs describe the + button and "Add plugins" with no Windows note. The Settings, Customize, Plugins route that worked for Nicole is not in these docs at all [C5]. | Not known |
| K5 | Updates | Auto-update is off by default for a marketplace like ours, same as on a Mac. A plugin with no version number counts each new commit as a new version [C5]. Everything in `docs/install-issues-2026-11-05.md` about the app not refreshing applies equally. | Confirmed in docs |
| K6 | Auto mode (so a backup runs unattended) | Available on Windows from a certain app version on [C6]. | Confirmed in docs |
| K7 | The safety sandbox | Runs on Mac, Linux and WSL2. On plain Windows commands run without it [C6]. Nothing we need changes; worth knowing. | Confirmed in docs |
| K8 | Phone taps and Remote Control | No Windows difference stated. The computer has to stay on [C7]. | Not known beyond that |
| K9 | The Canva connector | Connectors from claude.ai are available automatically when signed in. Nothing Windows-specific is stated [C12]. | Not known |
| K10 | Where plugins live on disk | Under `.claude/plugins` in the home folder; no Windows path is given [C5]. `fresh.py` reads the place from its own note, so it does not depend on this. | Not stated |

## L. Not counted: the parked reel route

`make_reel.py`, `beats.py`, `grade_reel.py`, `find_music.py`, `hooktext.py` and `check_setup.py` (the October route that renders video itself) need ffmpeg, numpy and Pillow on any computer, Mac included. They were parked on Oct 24 and nothing in the current flow calls them. Nothing new for Windows here; if they are ever revived they have the same needs on both.

---

## Counts

- 42 scripts and 26 instruction files searched; about 70 rows in the tables above.
- Mac-only calls with no Windows way at all: `sips` in 5 scripts (and in 6 more with a partial stand-in), `afconvert` in 2, `afinfo` in 1, `osascript` in 2 (one has a Windows branch beside it), `caffeinate` in 1, `/Volumes` in 3 scripts and 1 instruction file, `diskutil` in 1, `os.statvfs` in 3, `fcntl` in 2, `start_new_session` in 4, `os.execv` in 1, `lsappinfo`/`ioreg` in 1 (an experiment), `%-d` dates in 7.
- Text saved or read with no encoding named: about 210 places in 30 scripts.
- Places a Windows way is already written and unproven: about a dozen.
- By size: 3 large (pictures, sound if route 1, CapCut if the format differs), about 12 medium, the rest small.
- By where they can be proved: roughly a third on the Mac alone, a third on GitHub's Windows check, a third only on a real PC.

## Sources

Checked Nov 6, 2026. "Official" pages are Python's, Microsoft's, PyPI's and Anthropic's own. Where a page was read only through a search summary, or the source is a community one, it says so. Paraphrased throughout.

**Anthropic (Claude) docs**
- [C1] Desktop quickstart and setup: https://code.claude.com/docs/en/desktop-quickstart.md , https://code.claude.com/docs/en/setup.md
- [C2] Setup (Git for Windows, PowerShell), tools reference, environment variables: https://code.claude.com/docs/en/setup.md , https://code.claude.com/docs/en/tools-reference.md , https://code.claude.com/docs/en/env-vars.md
- [C4] Desktop app: https://code.claude.com/docs/en/desktop.md
- [C5] Plugins: https://code.claude.com/docs/en/plugins/install.md , https://code.claude.com/docs/en/plugins/loading.md , https://code.claude.com/docs/en/plugins/components.md
- [C6] Permission modes and sandboxing: https://code.claude.com/docs/en/permission-modes.md , https://code.claude.com/docs/en/sandboxing.md
- [C7] Remote Control: https://code.claude.com/docs/en/remote-control.md
- [C10] No keep-awake setting for the desktop app is described in the pages above.
- [C12] Connectors: https://code.claude.com/docs/en/mcp.md

**Python docs**
- [P1] Using Python on Windows: https://docs.python.org/3/using/windows.html (and Microsoft's https://learn.microsoft.com/en-us/windows/dev-environment/python )
- [P3] Text encoding: https://docs.python.org/3.9/library/functions.html , https://docs.python.org/3/library/sys.html , https://peps.python.org/pep-0686/
- [P4] `os.statvfs`, `shutil.disk_usage`: https://docs.python.org/3/library/os.html , https://docs.python.org/3/library/shutil.html
- [P5] `fcntl`, `msvcrt.locking`: https://docs.python.org/3/library/fcntl.html , https://docs.python.org/3/library/msvcrt.html
- [P6] `os.kill` on Windows; [P8] `os.rename` and `os.replace`; [P10] `st_ino`; [P11] `os.symlink`: https://docs.python.org/3/library/os.html
- [P7] `start_new_session` and the Windows start flags: https://docs.python.org/3/library/subprocess.html
- [P9] Dates: https://docs.python.org/3/library/datetime.html and Microsoft's formatter: https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strftime-wcsftime-strftime-l-wcsftime-l (read through a summary). What Python does with `%-d` on Windows is not in either; the "Invalid format string" report is from memory.
- [P12] `os.execv` on Windows: not in Python's docs; from its bug tracker, https://bugs.python.org/issue19124 . The trouble with spaces is from memory, not confirmed.
- [P13] 260-character paths: https://docs.python.org/3/using/windows.html

**Microsoft docs**
- [W14] File names: https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file
- [W15] File numbers on FAT: https://learn.microsoft.com/en-us/windows/win32/api/fileapi/ns-fileapi-by_handle_file_information (exFAT is not mentioned)
- [W16] Capital letters, and what each drive format can do: https://learn.microsoft.com/en-us/windows/win32/fileio/filesystem-functionality-comparison
- [W17] curl in Windows: https://techcommunity.microsoft.com/t5/containers/-/ba-p/382409 (a Microsoft blog)
- [W18] Staying awake: https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate
- [W19] Hiding: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/attrib . Explorer's command-line behaviour has no official page; community sources only.
- [W20] Folder windows: https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.folderbrowserdialog , https://docs.python.org/3/library/tkinter.html (whether the Install Manager's Python includes tkinter: not confirmed)
- [W21] Drives: https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdrivetypew , https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumeinformationw , https://learn.microsoft.com/en-us/powershell/module/storage/get-volume
- [W22] Sound: https://learn.microsoft.com/en-us/windows/win32/medfound/supported-media-formats-in-media-foundation , https://learn.microsoft.com/en-us/uwp/api/windows.media.transcoding.mediatranscoder , "N" editions: https://support.microsoft.com/en-us/windows/experience/platform-variants/media-feature-pack-for-windows-n . The PowerShell workaround is community-only: https://fleexlab.blogspot.com/2018/02/using-winrts-iasyncoperation-in.html
- [W23] Pictures: https://learn.microsoft.com/en-us/dotnet/api/system.drawing.image.fromfile , https://learn.microsoft.com/en-us/windows/win32/wic/native-wic-codecs . Whether the HEIC and RAW add-ons come pre-installed: not confirmed.
- [W24] Voice typing: https://support.microsoft.com/en-us/accessibility/windows/use-voice-typing-to-talk-instead-of-type-on-your-pc

**Packages**
- [K25] Pillow: https://pypi.org/project/pillow/ , https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html ; `pillow-heif`: https://pypi.org/project/pillow-heif/
- [K26] imageio-ffmpeg: https://pypi.org/project/imageio-ffmpeg/ ; `Gyan.FFmpeg` on winget (community listing): https://winget.run/pkg/Gyan

**CapCut (all community sources; nothing official exists)**
- [K27] Folders: https://blog.usro.net/2025/08/capcut-folders-cache-mac-and-pc-paths/ ; file names: https://cdn.jsdelivr.net/npm/capcut-cli-david@1.14.1/docs/draft-schema/00-overview.md ; locking, two views: https://github.com/emosheeep/capcut-export and https://gist.github.com/renezander030/521e6c6e8590a2a6e917009d9313bc55
- [K28] CapCut's own ffmpeg: https://www.advanceduninstaller.com/CapCut-5d98a9820d9063c670a49a2d861af94b-application.htm

## Not known, in one place

- How the desktop app on Windows runs commands when Git is not installed, and how it treats our comma lists and quotes.
- Whether the pages stay up after the command that started them ends, and whether the pane, the Copy button and the show-pane step behave as on the Mac.
- Whether the plugin installs by the same clicks on Windows.
- Whether CapCut for Windows will open a project we write (format, locking, which file names, which slashes).
- Whether Windows' own media engine can be reached from a script reliably enough to read a song with nothing installed.
- Whether file numbers stay put on exFAT under Windows.
- Whether the Install Manager's Python comes with pip and tkinter.
- What Python does with `%-d` on Windows (believed: an error).
- How long previews take on a PC.
- Which chip Dustin's Mac has, and so which kind of Windows Parallels would run.
