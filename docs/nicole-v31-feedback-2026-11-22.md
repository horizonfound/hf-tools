# v31 feedback for Nicole (sent Nov 22 to #the-engine, with Dustin's OK)

Nov 22, 2026. Two Slack messages for #the-engine, then the fuller notes for Dustin.
Written by four readers and a draft, then checked claim by claim against the code by a skeptic.

## Message 1

Hi Nicole, this is Dustin's Claude. These are honest notes on your v31 pack. The backup part isn't built yet. The two small fixes (faces on the tiles, the wider grid) are built on a test copy along with your Nov 22 answers, waiting for Dustin to look. (Part 1 of 2)

*Your question: what's the point if it's the same as a normal backup?* (added when sent) Dragging a card in Finder copies the files but never checks them. The Assistant reads every photo back and checks it matches the card exactly, never writes over a file, picks up where it left off, sorts and names the shoots, and only then says the card is safe to format.

*Love it, build as you have it*
• The Back up a card popup on the home page, with buttons and one question (where it goes). It should also get rid of a real snag: Claude asking for permission in the middle of a backup. We still need to test that.
• Your safety words at the top, and the card → drive pictures.
• Picking the drive and then the folder like Finder, + New folder, and Change clearing everything.
• Progress on the home card, and "No need to wait. Keep working."
• Your backups as just the list, with See the report as the main button.
• Faces above the words on the four tiles (about 30% from the top). Built on the test copy.
• Posting grid about 550 wide with 12 posts. Built on the test copy.
• "Shoot name", never "client name".

*Build it a bit differently (our suggestions)*
• *Checking happens while it copies.* Each photo is checked the moment it lands, so there's no separate checking step. The card would say "Copying and checking (128 of 181)", then "Sorting into shoots", then "Done". Showing a step that doesn't happen would be untrue.
• *The second copy right after the first,* not at the same time. Dustin set it up this way on Nov 19 so a problem with the second drive never stops the main backup. It's still one press, and it's checked the same way. Yours and Dustin's to turn round if you'd rather.
• *Sorting with nobody looking.* Today the Assistant looks at the photos and joins the pieces (your card started as 8 bits of time and became 3 shoots). A backup started from the page has nobody looking. One way: split wherever there's a 2-hour break, give each shoot a plain placeholder name, and you rename after. That fits your "name them after" idea. (Question 8.)
• *"Lets you know when it's done":* the card turns to Done by itself, and we can try a notification on the Mac. A tap on your phone only works when the backup is started from the chat.
• *Back up a folder instead:* this works for camera files and most downloads. But we can't read the date on iPhone photos yet, so a backup would set them aside out of sight instead of sorting them. That needs fixing first. And a folder that's already on your backup drive can't be backed up onto that same drive.
• *Shoot name box before the backup:* our suggestion is to use it only when the card holds one shoot. Otherwise it waits for naming after.
• *"Another card from the same day goes in with these":* today the cards are joined on one report, and each card's photos stay in their own folders. Putting them all in one folder is a bigger build that needs care.
• *Your backups page should ship at the same time as the popup,* because its top box is the only how-to there is today.

## Message 2

Part 2 of 2

*Clashes with something decided before*
• *Month-first folder dates* (11.22.26_Aurora). On Oct 24 Dustin chose year first as the standard, because it's the only way folder names line up by date in Finder. Month first puts every November from every year together. Anyone who wants month first can already ask for it. A middle way is your layout with the year in front: 2026-11-22_Aurora.
• *"Your photos keep their own names."* Today we rename each photo for its shoot (Aurora_0001_IMG_4471). That was on purpose (Oct 24). Keeping the camera's names is already a setting, so the switch is easy. But if two cameras or a second shooter both write IMG_4471, the backup stops before sorting, so we need a rule for that first.
• *Second copy "in the same folders."* On Oct 28 Dustin decided the second copy stays exactly as the card wrote it, in its own dated folder. Your line is easy to reword.
• *"3 shoots are in your editing queue."* Today a backup never puts shoots in your editing queue. They show in your backups and under Uploaded shoots. Oct 28: a shoot that's just for them never goes in the queue, and a trip to Yosemite sitting in a to-deliver queue would feel odd. Each shoot on the report already has an Add to my editing queue button, which asks for a due date. Our suggestion: "Your 3 shoots are backed up", and that button stays.
• *No sneak peeks and no client notes.* Both were Dustin's ideas (Oct 25 and Oct 28). They're easy to take out once he says yes. The "sneak peek" word Lightroom shows on photos already backed up (only on yours and Dustin's drives) can stay; nothing gets deleted.

*Questions for you and Dustin*
1. Folder dates as the standard: month first or year first?
2. Photos keep their camera names on new backups? Yes / No
3. Two cameras' names clash: keep each camera's photos in their own folder inside the shoot, or rename that shoot's photos?
4. Change it for your and Dustin's Assistants too, not just new ones? Yes / No
5. Second copy: as the card wrote it, or the same folders?
6. Second drive: remember it, or ask every time?
7. New shoots go to: Your backups, or the editing queue?
8. With nobody looking, split shoots wherever there's a 2-hour break? Yes / Other
9. "Keep them in one folder" after sorting: needed for launch? Yes / Later
10. Name the shoots after the backup instead of before (your section 6)? Yes / Later
11. Sneak peeks and client notes gone for good? Yes / No
12. A notification on the Mac when it's done? It may show up as coming from an app called Script Editor. Yes / No
13. Tiles: when no photo's face fits above the word, the test copy uses a photo whose face sits behind the word before one with no face. Keep that, or the other way round?

---

# v31 feedback, the fuller version for Dustin

Four readers went through Nicole's v31 pack (`reference-private/nicole-handoff-v31-2026-11-22/`) and compared it with main (version 7). Nothing is built. Every claim below comes from what those readers found, checked again against main by a fifth. The Slack draft above follows rule 10: it's yours to send or change.

## 1. Starting the backup from the page (her sections 1 to 3)

**Can be done; medium effort.** Today only Claude starts `night.py`, from the chat (`parts/backup.md:30`). We already have the pattern for long work that a page starts and that outlives the page:
- `this_computer.popen_detached` (`this_computer.py:191`): `start_new_session` on a Mac; on a PC, no window and its own group.
- It's used by the reel make (`reel_page.py:3578`), the slide job (`arrange.py:1155`), the talking job (`talking_rec.py:1213`) and + A new shoot (`create_dialog.py:115`, job file and lock at `new_shoot.py:49-50`).
- `arrange._pid_alive` (`arrange.py:1074`) tells whether a job is still running.
- A page server that restarts for new code uses exec on a Mac (`fresh.py:389`); on a PC it starts a new server beside it (`fresh.py:314`). Before either, it stops only its own JavaScript helpers (`this_computer.stop_scripts`, `fresh.py:380`, `this_computer.py:1226`), never detached jobs.

**Recommendation:** a new detached job, for example `backup_job.py`.
- A POST on the home page's server starts it through `popen_detached`.
- It just runs `night.py` with the chosen card, drive and folder. No new copy logic.
- It writes `~/.studio/backup-job.json`: the state, the step, the counts, the pid, and the exact command so a stopped run can be started again the same way.
- It keeps the computer awake for its whole life with `this_computer.awake_while` (`this_computer.py:172`, as `second_copy.py:883` does).
- The home card polls a small GET route for that file.
- **Never a thread inside the page server:** a restart for new code would kill it mid-copy. Every line the card shows must come from that file, so closing the pane, reloading or a server restart loses nothing.

**Unproven:**
- Whether quitting the Claude app ends a detached job. Nobody has quit the app in the middle of a backup.
- `night.py` runs each step from its own folder (`night.py:151`). If an update lands in a new plugin folder and the old one is removed, the next step fails and needs a rerun.

### What needs Claude today, and what the page route does instead
`night.py` has three points where it stops and waits for Claude:
- **Exit 5, which drive** (`night.py:472`). Goes away, because the popup asks for the drive and folder.
- **Exit 4, the look** (`night.py:719-728`). Claude reads `groups-sheet.png` and, for clip-only groups, the clip pages (`night.py:704-705`). It merges the over-split 15-minute groups and writes `shoots.json` (`parts/backup.md:46-47`).
- **Exit 7, sneak peeks** (`night.py:748-780`). `--no-peeks` already exists (`night.py:413`).

Exit 4 is the real gap. `check_shoots` (`night.py:381-397`) only needs every group given to one shoot with a name, so a script can write `shoots.json`. But `groups.py` splits on 15 quiet minutes on purpose (`night.py:408`), and on Nicole's card that gave 8 groups for 3 shoots. **Without a fix, a backup started from the page sits at exit 4: copied and checked, never sorted or settled, and the card never reaches Done.**

**Recommendation:**
- Run with `--no-peeks`, `--gap 120` (the switch already exists, `night.py:408`, passed to `groups.py` at `:683`; 120 is the drop box's gap, `posts.py:317`), and a new switch (say `--by-time`) that writes `shoots.json` itself, one shoot per group, with no recap.
- **Not date-only names.** The folder pattern adds the date itself (`{date} {shoot}`), so a name that is only a date gives the date twice (the Oct 24 lesson c). Two shoots on one day would also get the same folder: their photos would number from 0001 into it, and `sort.py` stops on the first two files with the same name (`sort.py:194-196`). Each shoot needs a placeholder name that differs from the others. The wording is yours and Nicole's.
- Renaming stays on the report: `rename_shoot.py` already renames per shoot.
- Claude's look stays available when asked ("look at my shoots and name them").
- The other way is to wake Claude for the look. That's a choice for you and Nicole.

### Progress
`backup.py` checks each file as it copies it: `copy_with_hash` reads the copy back (`backup.py:56-75`). It prints `dest: N/total` every 25 files and saves the manifest after every file (`backup.py:216-220`). **There is no separate checking step**, so her "Checking every photo" as its own step would be a claim the code doesn't make (rule 7).

The home page already polls `/home-state` every 4 s (`home.py:1222`, `posting_queue.py:2084`; today it only reloads the page when something changed) and knows whether a card is in (`home.py:213`). Suggested card lines: "Copying and checking (128 of 181)", then "Sorting into shoots", then "Done". The bar moves only during the copy; the later steps have no counts of their own.

### "It lets you know when it's done"
- The phone tap is the PushNotification tool, sent by Claude (`parts/backup.md:54`). A job started from the page has no Claude turn, so it can't send one.
- `return_watch.py` is an experiment and isn't wired in.
- A Mac notification through osascript `display notification` needs nothing installed. On recent macOS it may show as coming from Script Editor and stay silent until it's allowed in System Settings. Untested.
- A PC would need a PowerShell toast, also untested.
- **Recommendation:** the card turns to Done by itself; try one Mac notification on your Mac before promising it; the chat's first-thing check reads the job file. Say in the popup that the phone tap needs the chat.

### Permission prompts: a likely gain
A job started from the page should avoid Claude Code's permission prompts, the Oct 24 snag. Page servers already run things outside Claude Code: renames, `report_options.py`, + A new shoot. macOS's own questions (for example about access to a removable volume) can still appear; untested for a detached job. Test once on a fresh Mac user.

### Two backups at once: needs a lock before this ships
`night.py` and `backup.py` take no lock.
- Two runs on the same card would write the same `.studio-partial` files and save the same manifest over each other.
- Two cards on the same day could race for "the next free" folder name (`night.py:299`).
- **Recommendation:** one computer-wide backup lock inside `night.py`, so the chat and the page share it. Copy `second_copy.py`'s `try_lock` pattern (`second_copy.py:55-56, 867-889`). A second start answers "A backup is already running". Eject should also refuse while a backup is reading the card.

### Card pulled or drive unplugged mid-copy
- A read or write error stops the copy with exit 1 (`backup.py:205-208`). Everything before it is in the manifest, and rerunning carries on.
- A card that goes quiet is only caught at the first read (`cards.answers`, `cards.py:160`; `night.py:426-429`).
- The chat route depends on Claude rerunning after exit 3 (`parts/backup.md:35`), so the job must rerun once by itself on any stop other than 1 or 2, using the **same** `--name`.
- Add a watchdog: no new file for a few minutes means the page says the card or drive stopped answering.

### PC
`popen_detached`, keep-awake, drive letters and the folder window all have Windows ways (`this_computer.py:150-205, 978`). Not done on a PC yet:
- No Vision, so no clips turned upright and no clip pages.
- Previews need Pillow, and the preflight stops without it.
- A folder held open in File Explorer stops the settle with "close it and say go", which the page needs as a Try again button.
- No notification route.
- Whether the Windows Claude app ends detached children is unknown.

## 2. Drive, folder, second copy (her section 2)

### The folder browser inside the page: build it, with guards
No page lists folders on a drive today. Folders are only picked through the computer's own folder window (`this_computer.pick_folder`, `this_computer.py:978`).

Safe shape:
- The page sends a drive by its number in the list plus its name, checked again on the server (as `serve_report.py:536-587` and `report_options.py:243-252` do), and a list of folder names from the top of the drive. Never a path.
- The server rebuilds the path, resolves it, and checks it's inside the drive and is a plain folder.
- Each name must match an exact entry in the folder's listing: not `.` or `..`, no slash, not hidden, not a link, not a package. Don't use case-blind `exists()` checks.
- Listing GETs need the Create box's checks: our own Host, and requests from other websites refused (`create_dialog.py:97`, `posting_queue.py:2180`). Folder names are often client names.
- Cap the list at a few hundred entries and add a time limit.
- Hide `.studio`, `_studio`, Backups.backupdb, `$RECYCLE.BIN`, System Volume Information and packages.

Snags in the code that saves the folder:
- `use_next` takes whole drives only: it cuts any pick down to the top of its drive (`studio_file.py:501, 514-517`).
- Picking the top of a drive runs `place_on`, which quietly swaps in the drive's "sure" shoot folder (`:485, :494`).
- Picking any folder on the drive backups already go to reads as "same" and saves nothing (`:518-520`).

So the popup needs a writer that saves exactly the folder picked, through `set_drive` (`:378`), after `cannot_use` (`:243`), `card_above` (`:198`) and `onto_itself` (`backup.py:339`), and only when Start is pressed. Keep the computer's own folder window as the fallback.

### The drive list
Feed it from `studio_file.drives()` (`studio_file.py:263`):
- It already leaves out the computer's own disk, memory cards and Time Machine, and marks the recommended drive.
- On a PC, drives show as "Big Kahuna (E:)" (`this_computer.py:613`).
- A second internal disk on a PC (a D: data drive) would be listed like an external drive.
- A Mac can't tell a card reader that doesn't name itself from a drive (`this_computer.py:629-657`).
- Her mock-up has no line for "no external drive". Keep the existing [I'll plug one in] [On this Mac for now] (`studio_file.py:425-440`).

### Second copy
- Keep the v29 design: made after the main copy, in the card's own layout in a dated folder (`night.py:659-661`, `second_copy.py:1-34`). Your Oct 28 decision.
- Her "in the same folders" isn't true and needs rewording.
- `offered_drives` takes a finished backup's records (`second_copy.py:259`), so a version that works before Start is needed.
- The old `--second` path copies during the backup and stops it on trouble (`night.py:247, 405, 636`), so add a way to pass a second drive for one backup into the after-the-copy path.
- The progress needs a "Making your second copy" step, and Done waits for it.

### + New folder
The pieces exist: `safe_name` (`this_computer.py:112-147`, CON becomes CON_), `can_write` (`studio_file.py:218`), the PC length limit (`this_computer.py:455, 500`). Rules for the route:
- It goes through `arrange.guard`.
- The parent folder is rebuilt from the drive number plus folder names.
- No leading dot in the name.
- A taken name is checked case-blind against the exact listing, and if it's taken we open the folder that's there; never overwrite.
- Plain `mkdir`, never `exist_ok`.
- Say so when the name was cleaned up.

### Back up a folder instead
The engine already takes any `--source`. Snags:
- `backup.py` refuses a folder on the same external drive as the backups (`backup.py:339-372`).
- HEIC dates aren't read (`exif_read.py:7`). iPhone photos come out undated, are left out of the groups (`groups.py:131`), and are set aside in the backup's hidden `_studio/from-the-card` (`sort.py:345-391`). The line there calls them "not photos" (`sort.py:391`). Phone JPEGs are fine.
- Eject my card doesn't apply.

## 3. Sneak peeks and client notes out (her section 5)

**Easy, with two traps:**
- **Don't delete `sneak_peeks.py` outright.** `rename_shoot.py:30` imports its `TOOL` to recognise and carry the Studio's own sidecars (`:74-80, :181-189`), and `first_look.py:642` imports from it too. Move `TOOL`/`OLD_TOOLS` into a tiny module, or keep the file unused.
- To turn peeks off: make "no peeks" the only path in `night.py` (no exit 7, `night.py:745-785`), and drop:
  - the report's peek buttons and routes (`serve_report.py:190, 221, 442, 829-866`; `first_look.py:33-51, 516, 637, 711`)
  - the first-thing check in `SKILL.md:23`
  - `parts/sneak-peeks.md`
  - the promise in `home_base.py:75`
- Without picks, the report already falls back to three previews per shoot (`first_look.py:711-720`).
- Several tests and two GitHub steps (`peek_check.py`, `check-pc.yml:450-452, 681-683`) need moving out. At least 6 test files import these scripts directly.
- **`client_note.py` also holds `told`:** what they say unasked is saved word for word (`parts/backup.md:25`) and read by `kit.py:1708-1713`. Deleting the file would make `kit.py` report the backup as unreadable. Move `told`/`facts` into a small module first. `first_look.py:685` and `report_page.py:759` import from it too.
- Then remove the note button, card, setup question (`parts/first-backup-setup.md:109`), the Studio File section (`studio_file.py:101-115`) and `parts/client-note.md`.
- Sidecars already on drives (on Big Kahuna and Nicole's drive; not counted): leave them. Rule 1 says never delete; Lightroom has already read the keyword anyway.
- Rule 11 in CLAUDE.md still says sneak peeks are always picked. That wording is yours to update.

## 4. Never rename the photos (her background list and section 6)

**Clashes with rule 1 and Oct 24.** The setting exists: `naming.file_names` is `shoot` (default) or `original` (`sort.py:164, 186`; `rename_shoot.py:129, 158-161`). First-backup defaults set `shoot` (`studio_file.py:622-625`).

Snags if the default flips:
- **Name clashes:** with camera names, `sort.py` puts a whole shoot in one folder and **stops the whole sort** if two files would get the same name (`sort.py:194-196`), then `night.py` exits 1. Common cases: two bodies or a second shooter both writing IMG_xxxx, the counter rolling past 9999, two DCIM folders. Any "-2" fix is itself a rename. Options: keep the card's subfolder (100CANON) only when names clash, or keep that one shoot shoot-named and say so on the report. Test on a two-body card before beta.
- **Old shoots:** `rename_shoot.py` follows today's global setting, not how that shoot was sorted. After the flip, renaming old "Smith" to "Jones" leaves Smith_0001_... files in a Jones folder. Flipping back would stop with "not in the sorter's naming" (`:163-164`). Fix: record the photo-name style per shoot in `shoots.json`.
- **find_exports:** it matches by name first (`find_exports.py:76-87, 163-170`). With bare camera names, an older shoot's exports that share frame numbers can match and skip the time check. Check a few files by capture time when only camera names matched.
- Existing Studio Files (yours, Nicole's) say `shoot` explicitly and keep it unless changed with your OK.
- Lightroom: keeping camera names is Lightroom's default; no code change. Drop the sneak-peek keyword screenshot from the guide.

## 5. Naming after the backup (her section 6, "an idea")

- **Her two patterns clash with year first (Oct 24).** `OFFERED` (`studio_file.py:38-41`) would be easy to swap. `learn_pattern` (`:632`) already reads mm.dd.yy (`:53`), so anyone can already have month first by asking. But 11.22.26_Aurora sorts by month, and Shoot name_Date sorts by name. Middle way: 2026-11-22_Aurora. Also, `glance`'s example still says "Smith Family" (`studio_file.py:704`).
- **Name box before the backup:** use it only when the card holds one shoot. With several, keep it as what they said (`told.json`) and ask at Name your shoots, because giving one name to one of three shoots is a guess.
- **Name your shoots screen:** easy. Build it on the existing per-shoot rename queue (`serve_report.py /rename`) and `render()` (`report_options.py:158-188`). Do it later leaves the placeholder names, which are already on the drive. The spelling check for unusual names still applies.
- **"Keep them in one folder" (merge after the sort): hard.** No tool exists. `rename_shoot.py` stops when the folder already exists (`:136-137`). Merging needs the full safety design (log first, same drive, exact-listing clash check, identity proof, finish a cut-off run) plus updates to `shoots.json`, the index, groups, names, queue records and post kits. Joining a photos-only shoot with one that has clips turns it into Photos/ and Videos/. It needs a reviewer. Alternative: hold the sort until Save or Do it later, which is safer but leaves the drive in card layout and goes against "nothing waits on her". With a 120-minute gap, same-day mini sessions will mostly land together already, so **splitting** may be the more common need, and that isn't built either.
- **"Back up another card, it goes in with these": hard.** Today it's a link on the report (`shoot_report.py:133`; `report_options` link `:112`), with each card's photos in their own folders. Real shared folders: `settle.py` exits 6 on a same-name folder (`settle.py:179-181`), `rename_shoot` would update only one backup's records (`:257-261`), and camera-name clashes between cards. For now, say "goes on the same report".

## 6. Your backups page (her section 4)

Easy, in `backups_html` (`home_base.py:466-476`):
- Drop the header, ledes and steps box.
- Use her h1 "Your *backups*." with the list line under it, and drop the duplicate h2.
- Delete the `cardStatus` line (`home_base.py:340`), **or the page throws and the list never draws**.
- Swap the buttons at `:296` so See the report is `btn solid` (the `.acts.stack` style already stacks them).
- Tests to update: `home_base_check.py:935-942, 1146, 1150, 1164` (add her old lines to `HERS_NOT_OURS` at `:66`), `home_v29_check.py:169-171`, `skill_text_check.py:1672`. Also update `parts/hello.md:9`.
- Ship it with the popup, since that box is the only how-to today.

## 7. "3 shoots are in your editing queue"

**Untrue on main, and a clash.** `register_night` adds shoots as `archived`, which the queue page shows under Uploaded shoots (`edit_queue.py:437-450`, called at `night.py:519, 800`). Only Add to my editing queue on the report (`first_look.py:808` → `serve_report.py:800-814`) or the chat puts a shoot in the queue. Both need a date: `--due` is required (`edit_queue.py:1308`) and the report's route refuses a POST without `due` (`serve_report.py:805-807`).

Queuing every shoot automatically goes against "just for me means archive only" (Oct 28), the queue page's own line (`edit_queue.py:1077`), and "any photographer, any photos".

If you two want it anyway:
- `register_night` writes `waiting` with no date, but keep `scan` as `archived`, or years of old shoots flood the queue.
- `first_look.py:689-694, 805-808` must treat an undated waiting shoot as queued.
- Reword `:1077`.

Suggested line instead: "Your 3 shoots are backed up". The report's Add to my editing queue button per shoot already exists.

## 8. Tiles: faces above the words (her section 7)

Easy. `aim()` (`home.py:1002-1014`) is shared with the hello.
- Add an `at = .5` parameter and use it in the `py` line (`:1008`). `transformOrigin` (`:1011`) already follows `py`.
- Add `TILE_AT = .3` beside `ZOOM` (`:991`).
- `put` passes `at` through (`:1038`); `startTiles` uses it at `:1086` and `:1091`.
- Add a `fits()` test: the face's middle after the clamp is at most about .36 from the top. Optionally, its lower edge after the 1.22x zoom stays above about .42.
- A face higher than 30% is fine; don't demand exactly 30% or good photos get rejected (the sample "04 baby.jpg").
- A wide photo in a wide tile can't move.
- The check can run before load, from the `faces.py` w/h.
- Consider raising `TILE_CANDS` (`home.py:598`) from 6 to about 10.
- Leave `.tl b` (`:892`) alone.
- `home_v30_check.py:264` is the test that would catch a tile with no face.
- Nicole's call: when no face fits, does a photo with no face come before a face that sits behind the word? Her rule suggests yes.

## 9. Posting grid (her section 8)

Easy.
- `posting_queue.py:1372`: max-width 420px → 550px, gap stays 3px.
- `:1534`: `>=15` → `>=12`, comment "four rows at most".
- Keep `FEED_MAX` at 15 (`:115`) and the 9 empty tiles before a read (`:1536`). Upcoming posts are added before the cap, so they still all show.
- Update `tests/posting_lift_check.py:119-134`: width about 530 to 570, tile about 170 to 185; drop or reword the 720 px height case (four rows are now about 905).
- Update the comment at `posting_reminders_page_check.py:735` and `parts/posting-queue.md:15, 17`.
- The "Your last N posts" note (`:1537`) counts posts read (up to 15) while 12 show. Say the number shown, or "Your latest posts".
- A fixed 550px is simplest; matching the line live would mean measuring it while it's hidden (`:1520`).

## Order, if you two say go
1. The backup lock in `night.py` (needed by both routes).
2. `--by-time` with `--no-peeks` and `--gap 120`, with placeholder names that differ per shoot.
3. The detached job and the popup, with the folder browser.
4. Your backups trimmed.
5. Sneak peeks and notes out (keeping `TOOL` and `told`).
6. Tiles and grid, any time; they're independent and small.

Hold the photo-name flip, month-first dates, the merge after sorting, shared folders across cards, and backing up folders of iPhone photos (HEIC dates) until you and Nicole answer.
