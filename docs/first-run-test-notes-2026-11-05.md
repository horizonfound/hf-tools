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
