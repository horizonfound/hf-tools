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
