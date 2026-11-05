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
