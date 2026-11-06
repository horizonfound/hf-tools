# First-run test notes, Nov 5, 2026

Dustin is going through the Assistant as a brand-new photographer (saved setup set aside, nothing deleted).
His comments as the tester are kept here, apart from the walkthrough itself. Each note says whether it is fixed.

## 1. The first "hi" should be an introduction, not a status report

**What happened:** on a brand-new setup he said "hi" and the reply opened with "It's a clean slate today:
nothing due, nothing waiting, and no memory card in."

**Dustin:** "I'm kind of confused with how you started this session off... It should be more of like an intro."

**Why it happened:** the skill's "Opening the Assistant" section has one script for every hello: say the day
(what's due, what's queued, whether a card is in), then what they can say. That fits someone coming back.
It has no first-time version, so a new photographer gets a report on a day that has nothing in it.
The home page already gets this right ("Welcome to The Assistant... put a memory card in and we'll start
there"); the chat reply does not match it.

**Fixed the same day (Dustin: "there needs to be a first-time script... fix it now"):** `home.py hello --mark` picks the hello from what they've done: first (the introduction below), new (said hi before, nothing done yet: one warm line, no intro again), getting-started (one side done: the day if there's anything in it, plus an invitation to the other side), regular (the day's rundown). In the skill's "Opening the Assistant" section.

**The first-time words, as written into the skill:** when there is no setup on file, the hello is an introduction: who this is,
what it does in a sentence or two, what the page beside the chat is, and one first step. No "nothing due",
no "no card in". Something like:

> Hi, I'm your Assistant. I take care of the busywork around your photos: backing up your memory cards,
> sorting and naming your shoots, keeping track of what's left to edit, and turning finished photos into
> posts. The page beside this chat shows everything I can do; click anything to see how it works.
> The best place to start is your first backup: put a memory card in and say "backup now."
> No card handy? Click "Make posts from a shoot" and we'll start with photos you've already finished.

The day's rundown (due, queued, card in) starts once they've done things, not on a second hello.

## 2. Nothing should assume they have a memory card

**What happened:** the new first-time hello said "The best place to start is your first backup," and the
welcome screen said "When you're ready, put a memory card in and we'll start there."

**Dustin:** the Assistant was first built as if everybody always has a fresh shoot on a card. A lot of the
students don't shoot that often; they'll mostly use it for social media. A backup is still a fine place to
start, but someone with no card should feel just as welcome to explore and start with what they have.

**Fixed the same day:** the two ways in are offered side by side, finished photos first, and neither is
"the" place to start.

- The first hello now ends: "There are two good places to start, depending on what you have today. Got
  photos you've already finished? Click "Make posts from a shoot" on the page and I'll turn them into a
  reel, a carousel and captions. Just back from a shoot? Put the memory card in and say "backup now."
  Or just look around first."
- The second-hello line and the "nothing going on" line for regulars got the same treatment (the old one
  still mentioned dragging photos in, which is no longer the way).
- The welcome screen, for someone new: "Start with whatever you have today: photos you've already
  finished, or a memory card from a shoot." Its empty "Your shoots" line no longer says "after your first
  backup," and its Today section no longer says "Nothing due and nothing waiting" to someone who hasn't
  started; it says what will show up there.
- The setup guide's "Opening the Assistant" paragraph says you don't need a memory card to start.
- The rule is in the skill: never assume they have a memory card.

**Still worth a look (not changed):** the setup guide's Part 2 is titled "Opening the Assistant, and your
first backup" and goes straight into a backup; a "your first posts" walk-through beside it would match.

## 3. "Just back from a shoot?" isn't the right line

**Dustin:** "This is one line that I'm not in love with. Give me some options on other ways we could say it."

**Why it's off:** it describes something they did today, and most students haven't just come back from a
shoot. The line before it ("Got photos you've already finished?") describes what they have, which works
whenever they shot.

**Fixed: Dustin picked "Have a memory card with new photos on it? Put it in and say "backup now."**" It is in
the first hello, the second-hello line and the regulars' quiet-day line.

**The options he chose from:**
- "Photos still on a memory card? Put it in and say "backup now.""
- "Have a memory card with new photos on it? Put it in and say "backup now.""
- "Got a memory card to back up? Put it in and say "backup now.""
- "Shot something new? Put the memory card in and say "backup now.""

## 4. The welcome screen's cards jump around, and the explanation box won't close

**What happened (two screenshots):** clicking "Make posts from a shoot" left a hole where the third card
had been and pushed the other three cards under the dark explanation box; clicking "Back up a card" pushed
all four other cards under it, in a different arrangement. And the box only went away by clicking a
different card.

**Dustin:** "There should be some form of continuity there, so that it's not so random." A click outside
the selected card should unselect it, and so should a second click on the same card; click it again to
bring it back.

**Why it happened:** the box was placed right after the card that was clicked and stretched across the
whole row, so every card after it in that row was shoved below. Which cards moved depended on which one
you clicked. There was no way to close it at all.

**Fixed the same day:**
- The box now opens under the whole row its card sits in. No card ever changes place; only the rows below
  slide down to make room. On a phone, where the cards are one per row, it opens right under its card.
- It closes on a second click on the same card, a click anywhere outside the card and the box, or the
  Escape key. Clicking inside the box (the Copy button) keeps it open.
- Tried in the app's pane at desktop and phone width: Back up a card, Make posts, and the folder card each
  open under their row with every card where it was; all four ways of closing work; going straight from
  one card to another works.

## 5. No obvious way back to the welcome screen

**What happened:** he clicked "My editing queue" on the welcome screen, landed on the queue page, and saw
no clear way back.

**Dustin:** the pane has its own back arrow up top, "but it's not that obvious." There should be a
built-in back button so people don't get confused about how to get back to the welcome page.

**Why it happened:** every page did have a link home, but it was a small outlined "Home" pill at the far
right of the top bar, next to the date, where nobody looks for a way back.

**Fixed the same day:** on the editing queue, the posting queue, the post kit and the report, the link is
now a solid dark button at the top left, the first thing in the bar: "← Back to home" ("← Home" on a
phone, where there's less room). Looked at in the app's pane on a copy of the earlier setup: the queue page
and the posting page at desktop width, the queue page at phone width (nothing spills over), and a click on
it lands on the welcome screen. The post kit and the report use the same button but were not looked at,
since both pages are written when a kit or a backup is made; the next one made will have it.

## 6. "Your Content," with a capital C

**Dustin:** "For the Your content folder, capitalize the C, and update it everywhere it says that,
throughout all of your code."

**Fixed the same day:** the folder is "Your Content" in the code, in everything the Assistant says, and in
its instructions. A folder already made as "Your content" (or the older "Content") is renamed in place the
first time the Assistant looks: a rename on the same drive, nothing copied or deleted. Because most drives
ignore capital letters, the check reads the folder's exact listing rather than asking "does it exist,"
which would say yes to either spelling. Tried on pretend folders (lowercase, the oldest name, already
right, brand new, a fresh setup; a pretend photo inside came through unchanged), then on the real folder on
Big Kahuna, which now reads "Your Content." The old "The Studio" folder from before the test was left
alone; it gets the same rename if that setup is ever put back.

## 7. "The Assistant copies the photos in (JPEGs only). Nothing is moved."

**Dustin:** that line on the Make posts card could be said "a little bit more clearly and a little bit more
user-friendly. Give me some options."

**Fixed: he picked "Makes its own copies."** The line now reads: "The Assistant makes its own copies of the
JPEGs in that folder. Your originals aren't moved or changed." (The option as offered ended "Your originals
aren't touched"; "touched" is a word he ruled out on Oct 24, so it went in as "moved or changed.")

**The options he chose from:**
- "Your photos stay exactly where they are. The Assistant makes copies of the JPEGs to work from."
- "The Assistant works from copies of your JPEGs, so your originals are never moved or changed."
- "The Assistant makes its own copies of the JPEGs in that folder. Your originals aren't touched."
- "Your originals stay put. The Assistant copies the JPEGs to work from."

## 8. "Backup now" crashed before it started (found by the test, not by Dustin)

**What happened:** the check that runs before a backup stopped with a code error, before anything was
copied. Nothing was changed anywhere.

**Why it happened:** the Oct 30 change that added the "your computer's disk is getting full" nudge put a
second `import studio_file` inside the backup script's main routine. In Python that makes the name local to
the whole routine, so the very first line that reads the Studio File failed. That change was written in
the cloud and no backup had been run on the Mac since, so every "backup now" since Oct 30 would have
stopped right here.

**Fixed on the spot:** the stray import is gone. A scan of every script in the Assistant and the reel
maker for the same mistake found no others. The check now passes on the test folder.

**Worth doing:** a one-line smoke test (`night.py --check` on a pretend card) before any push that touches
the backup scripts, since a crash like this is invisible until someone says "backup now."

## 9. The first backup felt like a questionnaire

**What happened:** before the first backup started he answered eleven things: where the photos are, yes
that folder, which drive, where on it, a second copy, folder naming, how he writes to clients, how he
signs off, his name, how often he posts, and what's in the folder.

**Dustin:** understandable the first time, but "they're thinking, oh, this is going to make my life so much
easier, and then they're sitting there going through a whole questionnaire... they just want to back up
their photos." Warm them up: since we've never done this before I need to ask a few questions so I know
what to do, and I'll remember your preferences so it's quick and easy every time from now on. "And we'll
try and streamline this as much as possible."

**Fixed the same day, the warm-up:** the first-time opening now says, before any question: "Since we've
never done this together, I need to ask you a few quick questions first, so I know where your photos go
and how you like things named. It takes about a minute, and it's only this once: I'll remember your
answers, so from now on a backup is just "backup now" and you can walk away."

**Not changed yet, the streamlining (his and Nicole's call; these are what could go):**
- **How often you post** has nothing to do with a backup. It could wait for the first time they make
  posts. Saves one question.
- **How you write to clients** could wait until the first shoot that gets a note. Dustin moved it into
  setup on Oct 28 because asking at the end held the report up; asking it the first time they add a shoot
  to the editing queue would keep it out of both places. Saves up to three (tone, sign-off, name).
- **The sign-off took three steps** in this run (tone, "just my first name," then the name) because a
  button can't carry a typed name. One plain question, "How do you sign your notes?", does it in one.
- **Where on the drive** could be asked only when the drive has an obvious shoots folder; otherwise shoots
  go right on the drive and the Assistant says so. Saves one for most people.
- With all four, a first backup from a card is: drive, second copy, folder naming, how many cards, what's
  on the card. Five, down from nine or more.

## 10. Fourteen photos were left out of their shoot and hidden (found by the test, not by Dustin)

**What happened:** the test folder held 442 raw photos. 428 were sorted into two shoots. The other 14, with
their 13 edit sidecars, were reported as "27 files that are not photos" and moved into the backup's hidden
records folder. Nothing was lost: every one is on Big Kahuna, verified byte for byte, and the source folder
is untouched. But a photographer would open the shoot, find 14 photos missing, and have no idea where
they went. They were also the 14 that had been rated or edited in another program: the selects.

**Why it happened, two things:**
1. **The date reader only looked at the first megabyte of a raw file.** A program that saves ratings or
   edits back into a CR2 (Capture One, Canon's software, Photo Mechanic) can move the file's directory to
   the very end. Those 14 came back with no date, camera or lens.
2. **The sorter treats "no date" as "not a photo."** Anything it could not date is set aside with the
   camera's housekeeping files, out of sight, and the message says "not photos."

**Fixed the same day (1):** the reader now finds the directory wherever it sits in the file. All 14 read
correctly (Feb 5 2020, 6:01 to 6:26 am, the lookbook shoot), about half a second each; ordinary files are
as fast as before.

**Not fixed yet (2), and it matters beyond this case:** iPhone HEIC photos cannot be dated yet at all, so a
card of them would be hidden wholesale. What it should do, for Dustin and Nicole to confirm: a photo is a
photo by its file type, never by whether it has a date; photos with no readable date go in a visible folder
of their own next to the shoots ("No date, from this backup") with their sidecars; and the report says so
at the top in plain words ("14 photos had no date I could read. They're in ..."). Sidecars always travel
with their photo.

**This backup:** the 14 are still in the hidden records folder. Running the backup fresh with the fixed
reader would sort all 442; that needs the two shoot folders from this run set aside first.

## 11. The report talks about a memory card when the photos came from a folder (found by the test)

**What happened:** this backup's source was a folder on a drive, not a card. The report still says "checked
against the card," "your memory card is exactly as it was," "The card is safe to format when you're ready,"
and "What's on the card." The backup's day folder was also named "thursday card."

**Not fixed yet.** When the source is a folder, the report should say "the folder" (and name it), and there
is nothing to format, so that button and line should not appear. Same for the first-time questions: "How
many memory cards for this shoot?" does not apply to a folder and was skipped by hand in this run.

**Also on this report:** it says "2 shoots, 428 photos" and nothing about the 14 photos left out (note 10).
The top of the report is where that belongs.

## 12. The report wasn't on screen; the pane's play button showed a bare list of files

**What happened:** when the backup finished, the report was loaded in the pane and the pane was brought
forward. By the time Dustin looked, the pane was blank with a play button. He pressed it and got
"Directory listing for /": first-look.html, from-the-card, index.json, manifest.json and so on.

**Why it happened, as far as it can be traced:**
- The pane lost its page between the report being shown and Dustin looking. The session's instructions
  were re-read at that moment, which is what happens when the app reloads a session; a reloaded pane comes
  back empty. That part is the app's doing, and the Assistant cannot speak first to put the page back.
- The play button runs this project's own launch setting, a leftover from Oct 24 that pointed at the old
  "Night test" backup. Its port was busy with today's report, so it started a second server on the next
  port and opened that server's bare address, and the report server answered a bare address with a list of
  the backup's record files.

**Fixed the same day:**
- A report server's bare address now opens the report, and it never lists a folder's files.
- The home page server's bare address now opens the home page (it used to open the posting page).
- This Mac's launch setting now starts the Assistant's home page, so the play button lands on Home. (That
  file is Dustin's own, not part of what students get.)

**Still open:** a student whose pane comes back blank has no launch setting at all, so the play button will
do nothing useful for them. The honest fix is in the guide and the hello: "If the page beside the chat is
ever blank, say 'show me the report' or 'hi' and it comes back." Worth a line in the setup guide.

**Note 12, the timing, from the session's own log:** the report was put on screen at 12:58 pm. Dustin's
next message in this chat was at 3:14 pm, two hours and sixteen minutes later, and two other chats in this
project were in use in between. The report's server ran the whole time; only the pane's page was gone.
Whether it was the time away, switching to other chats, or the app reloading the chat cannot be told from
here. It does not matter for the fix: "you can walk away" means the report has to be reachable when they
come back hours later, whatever the pane did meanwhile.

**Dustin: "we need to solve that issue somehow." Proposed, not built yet:**
1. The closing chat message, which is always still there when they come back, ends with how to get the
   page back: "If the page beside this chat is blank, press the play button in it, or say 'show me the
   report.'"
2. Make the play button work for students: at setup the Assistant writes the launch setting into the
   folder they opened, so a blank pane's play button opens Home; and Home shows the latest backup at the
   top with a "See the report" button.
3. Whenever they say anything after a backup, the Assistant first checks that the pane is showing a page
   and puts the report back if it is not.
Ruled out earlier by Dustin (Oct 28): also opening the report in the Mac's regular browser, which would
survive, but put pages in two places.

## 13. Can the Assistant tell when they come back, and put the report back itself? (Dustin's idea)

**Dustin:** "Is there a way for you to tell if the Claude app goes inactive and becomes active again when
someone returns? Can that be a cue to reload the pane?"

**What's true:** Claude cannot watch the app; it only runs when something wakes it. But a script on the Mac
can read, with no permission prompt, which app is in front, how long the keyboard and mouse have been
still, and whether the screen is locked. And a background command finishing does wake Claude. So
`return_watch.py` (new, in the scripts folder, not wired into the backup yet) waits until they have been
away, then until they are back in the Claude app, then exits; Claude wakes, reloads the report, and brings
the pane forward.

**Two short tests on the Mac, Nov 5:**
- First, 60 seconds away: nothing happened. The watcher never saw a full minute away. Its log was too thin
  to say whether Dustin was back sooner or the switch was missed, so it now logs every time the Claude app
  leaves or returns to the front.
- Second, 20 seconds: **it worked.** The pane had been closed. The watcher counted him away (keyboard and
  mouse still), saw him back at 3:33:07, and the report was back on screen by 3:33:12, five seconds later,
  without a word typed. Note it was stillness that counted as away, not a switch to another app; the
  app-switch path has not been seen working yet.

**Not proven:** the case that matters, hours away with the app reloading the chat in between. If the app
drops the watcher or the wake-up when that happens, this fails exactly then. A long test is running
(counts a return after 30 minutes away). Until that passes, the closing chat line and the play button
stay as the safety net.

**To decide before wiring it in:** how long counts as away (5 minutes is the script's default; sitting
still reading counts too, which is harmless if the reload only happens when the pane has lost its page),
and that every wake-up is a small turn on their plan.

## 14. A "Show the report" button as the last thing in the chat (Dustin's fix for note 12)

**Dustin:** "Maybe the best thing is to just have the very bottom thing in the chat box, for when they
return after a card backup, be a button that says show the report. That way it's either up on the screen
or easy to launch if not."

**Done the same day, in the Assistant's instructions:** every backup now ends with the app's next-step box
under the closing message: a one-line recap, "Want to see the report?", and one button, Show the report.
A click sends "Show the report," and the Assistant loads the page fresh and brings the pane forward every
time, without checking whether it was still there. In a plain terminal, where there is no such box, the
closing message ends with "Say "show me the report" any time to see it."

**This replaces** the "press the play button" line proposed in note 12. The return watcher (note 13) stays
as an experiment; the button is the answer that does not depend on anything staying alive.

**To see for sure:** whether the box and its button are still under the last message after hours away and
an app reload. The first one was shown at the end of this change; Dustin's next long break is the test.

## 15. Speed: where the waiting is, and the instructions split into parts

**Dustin:** "Any way to speed some of these things up so there's less delay? Is it dependent on my
computer speed?"

**Measured from this chat's own log (Nov 5):** the Show the report button took 6 to 10 seconds from click
to page; a hello 9 to 19; copying and checking 16 GB took 87 seconds; working out the shoots about 40;
picking the sneak peeks one to two minutes; the whole backup about four and a half minutes. Only the copy
depends on the Mac and its drives. Everything else is Claude's thinking, which happens on Anthropic's
servers and depends on the model and on how much it has to read.

**Dustin runs Fable 5.1 on high;** most students will be on a lighter model and will likely see quicker
replies. This chat is also heavier than theirs: a day of conversation plus the whole project notes file,
which students never load.

**Done the same day (his call): the instructions are split.** The one 75 KB file every reply had to read
is now a 9 KB core (the first-thing checks, the rules, how to talk, showing a page, and a table of which
part to read) plus twelve parts in a `parts` folder: hello, first-backup-setup, backup, sneak-peeks,
client-note, after-the-report, editing-queue, post-kit, photos-in, canva, posting-queue,
where-things-live. The text was moved word for word; a line-by-line check found nothing lost and nothing
doubled. Sentences that pointed at "the section below" now name the part. A hello now reads about 15 KB
instead of 75; a backup after setup about 21.

**What this does and does not buy:** less to read means less of their plan used on every reply, and less
for the Assistant to wade through. How much faster replies get was not measured; a timed fresh chat
before and after would say. The cost is one extra step to read the part.

**Not done:** bundling the routine checks into one command; a link in the chat that opens the report with
no thinking at all (untested whether the app opens it in the pane or in Chrome); which lighter model is
good enough for the sneak peeks.

**Note 15, the cold read (same day):** a fresh helper that had never seen the instructions was given the
core only and twelve things a photographer might say (hi, backup now with and without setup, the backup
stopping for the picks, what's in my queue, I'm done with the beach shoot, make my posts, export the
carousel again, Show the report, the beach reel's ready, call the sunset one Kaia, a shorter note for
Sarah). It chose the right part every time and had to guess only once (Show the report needs no part).
Every script the parts name exists. It also found wording slips, most older than the split, now fixed:
"five questions" where there are six; "Last one" on question four; "two button questions" on a screen with
three; "rule 6" and "rule 11" for rules that are numbered differently; the first-backup trigger worded
three ways (it is "no drive set," since a posts folder can exist before any backup); which naming choice
is 1 and which is 2; where the curating notes and the reel script live; the folder button called two
names; the queue page told to open in the regular browser against the pane-only rule; the sneak-peek part
saying "run the same command again" without naming it; /assistant and /studio both named now.

**Left for whoever knows the Canva connector best:** the Canva part names editing tools
(`start-editing-transaction`, `perform-editing-operations`, `commit-editing-transaction`) that this Mac's
Canva connector does not have (it has one `edit-design` tool). The part now says the names differ by
version; the steps themselves want a check against the connector students will actually get.

## 16. A long shoot name was cut off mid-letter in the name box

**Dustin:** the name box on the report showed "Lookbook on the patterned" with the last word sliced off at
the edge. "It would be good to have like a ... or something that shows that it's longer than what is
shown there."

**Fixed the same day:** a name longer than the box now ends in "..." ("Lookbook on the patterne..."), and
hovering over the box shows the whole name. Clicking into the box to type still shows all of it. Seen on
the real report in the pane. Reports written before this keep the old look until they are rebuilt.

## 17. No way back to the report after leaving it

**Dustin:** "Once I exit the report, there's no way for me to get back to it." The report is where shoots
get renamed, so someone who leaves it by accident is stuck. He suggested the "Your recent shoots" area.

**Fixed the same day, on the home page:**
- Every recent shoot that came from a backup has a "See the report" button beside "Open photo folder." It
  opens the report of the backup that shoot came from, right in the pane, at the top. (It first jumped to
  that shoot's name box; Dustin: "it opens scrolled half way down the page." Changed within the hour.)
- Under Today, one line names the newest backup ("Your last backup, today: 2 shoots, 428 photos.") with
  its own "See the report" button.
- If that report's little server isn't running, the click starts it. If the drive is unplugged it says
  "Plug in Big Kahuna to see this report." A report server now says which backup it serves, so a click
  never lands on some other backup's report.
- Tried in the pane: a click on a shoot's button landed on the report at that shoot, and Back to home came
  back. Asking twice starts only one server.

**Also fixed while there:** after a first backup, Today said "Nothing ready to post. Time to get something
in the pipeline." and "Nothing ready to post yet." to someone who has never made a post. The running-low
nudge now waits until they have made at least one piece, and Today no longer lists an empty tank. And the
"Opened ... in Finder" line on a shoot card now sits under the buttons, not between them.

**Not done:** the same button on the editing queue's "Your shoots" list, which would give a way back from
there too.

**Note 13, the long watcher, stopped at 4:13 pm for a fresh run:** it ran 40 minutes and was never away
for the 30 it needed, so the hours-away case is still unproven. Its log does settle the other open point:
it saw every switch to Chrome and Finder and every screen lock, and every return, to the second. So the
app-switch path works; the first test's "nothing happened" was a return in under a minute.

**Fresh run 5 (4:13 pm):** the saved setup is set aside as `~/.studio-fresh-run-5-2026-11-05`. The last
run's folders on Big Kahuna (The Assistant folder, the two shoot folders, the backup's records) were
renamed into `The Engine Test/set aside 2026-11-05 first-run 5/`, with a note inside saying where each
came from. Nothing deleted or copied.

## 18. Fresh run 5: the source drive dropped out mid-copy, and the backup stopped the right way

**What happened:** on the second first-timer run the TETHER drive was plugged in at the "where are your
photos" question, the six setup questions were answered, and the copy began. On the very first photo the
drive disconnected ("Device not configured"). It had also gone missing once earlier in the afternoon,
between runs, so it looks like a loose cable, a hub, or the drive going to sleep.

**What the Assistant did, which is what it should:** stopped at once, copied nothing further, said so at
the top of its report, and left the one half-written file marked as partial. Nothing on TETHER was
changed. Running the same backup again picks up where it left off.

**Small things seen on this run:**
- The "Starting now... You can walk away" message came out after the backup had already stopped, because
  the backup was launched before the message was written. The message should go out first, or in the same
  breath as the launch.
- Keeping what they said about the shoots ("told") was refused for the first half minute because the
  backup's records did not exist yet; it had to be retried. It should wait for the records itself, or the
  backup should take the words as it starts.
- A drive with a lot on it: the quick count of every folder took under a second and the question offered
  the four likeliest folders. That worked well.
- For a stop like this, the useful button under the last message is "Backup now" (try again), not only
  "Show the report." Worth changing in the instructions.
- The warm-up before the questions and the one-step sign-off question both ran as written today.

## 19. Fresh run 5, second try: all 442 photos sorted

**What happened:** with TETHER plugged back in, "backup now" asked nothing (the answers were saved) and
picked up where it had stopped. 455 files copied and checked in 62 seconds; two shoots found; every one of
the 442 photos sorted, including the 14 that were hidden on the earlier run (note 10). Nothing was set
aside as "not a photo." Four photos re-read against the originals on TETHER, two of them from the 14: all
match. Nothing on TETHER was changed.

**What they said about the card did its job:** "the first shoot is a holiday lookbook for HAH... the second
is portraits of Nicole for Horizon Found" named both shoots: "2020-02-05 HAH holiday lookbook" and
"2020-04-14 Nicole portraits," in the date-first naming he picked.

**One of the Assistant's six picks for the lookbook was already a 5-star of the photographer's own.** That
photo came with its own rating sidecar from 2020, so the Assistant left it exactly as it was and did not
add its keyword. Worth saying on the report when it happens ("one of these was already a 5-star of yours").

**No notes written:** neither shoot has a due date yet, so neither is in the editing queue. The lookbook
is a client shoot; its note waits for "Add to my editing queue" on the report and for who it goes to.

**Still wrong on the report (note 11):** it says "memory card" and "safe to format" for a folder source.

## 20. "Show me more" opened already full, so clicking a photo did nothing

**Dustin:** pressing Show me more showed the current six numbered one to six. "Instinctively I want to click
on other unselected images to add more, and it won't let me unless I click one of the images to unselect
it... not the most intuitive." He suggested starting with none selected, and to "figure out a better way."

**Fixed the same day:**
- It opens with nothing chosen. The six that are on the report today carry a small tag, "on the report
  now," so they can be picked again or passed over.
- The line under the photos always says where things stand: "Nothing chosen yet. Click the six you want.",
  "3 of 6 chosen. 3 to go.", "6 of 6. Press Use these, or click one of your six to swap it out."
- At six, the photos not chosen fade back, and a click on one of them says why nothing happened: "You
  already have six. Click one of your six to take it out, then pick this one."
- A "Start over" button clears the choices. "Never mind" closes it and keeps the six on the report.
- Tried in the pane on the Nicole portraits: open, one, six, a seventh, swap, start over. Each step read
  right. "Use these" was not pressed, so the six on the report are unchanged.

**A slip of mine along the way:** the first version of this change had an apostrophe that broke the report
page's script for about two minutes, so no button on the report worked until it was fixed. Every script on
the rebuilt page was then checked with the Mac's own JavaScript engine. That check should run every time a
page is built (not done yet).

## 21. The photo-count tag covered a face

**Dustin:** "Slightly less overlap on the part where it says the 230 photos, because you can see where it
cuts off Nicole's head in that portrait."

**Fixed the same day:** the count tag on each shoot's photos sits higher, mostly above the top-left photo.
It now overlaps the photo by about half its height instead of most of it. Seen on both shoots in the pane;
the face is clear.

## 22. Choosing new sneak peeks put the report back to its older look

**Dustin:** after pressing Show me more and choosing new photos, "it looks like it reverted back to the old
way." His screenshot showed the count tag covering the face again (note 21), a change made minutes before.

**Why it happened:** when "Use these" (or Rename) finishes, the report's little server rebuilds the page.
It rebuilt it with the code it had loaded into memory when it started, not the code on disk. So anything
changed since that server started was silently undone on the next rebuild: the tag moved back down and the
picker went back to opening full. The photos he chose were saved correctly; only the page's look was old.

**Fixed the same day:** the server now rebuilds the report in a fresh process every time, which always uses
the current code. Checked by having the server itself re-save the same six: the rebuilt page kept the new
tag position and the new picker.

**The same weakness, still there in the other two page servers (home and posting, and the editing queue):**
they draw their pages from code loaded when they started. After the Assistant updates, they keep showing
the old pages until they are stopped and started again. That has needed a manual restart several times
today. A proper fix, not built: each server notes how new its code was when it started, and whoever asks
for its address (`home.py url` and the like) restarts it if the code on disk is newer. For students this
matters the day after an update lands while a page server is still running.

**Note 22, the rest of it, done the same day (Dustin: "Yes, fix those too"):** all three page servers (home
and posting, the editing queue, a backup's report) now notice when the Assistant's code on disk is newer
than what they loaded. On the next page request they answer with a one-line "One moment. The Assistant just
got an update" page that retries by itself, and start over with the new code on the same address. New
helper: `fresh.py`. An open home page reloads into the new version without a click.

Tested on all three, on the Mac:
- A change lands on disk: the next page load shows "One moment," and the real page is back about two
  seconds later, on the same address. Each server's log says "starting over with the new code."
- A half-written (broken) file lands in the folder: every server keeps serving its pages and logs that it
  is staying on what it has. An old page beats no page.
- The broken file goes away: no needless restart. A good update after that: restarts as it should.
- The small background questions a page asks do not restart anything; only a page request does.

One flaw found and fixed in the testing: a restarted server first took its "which code did I load" reading
at its first page request, not when it started, so it could miss a change that landed in between.

No more "stop and start the server after an update," for Dustin or for students.
