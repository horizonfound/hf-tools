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
