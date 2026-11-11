# Building Nicole's v20 and v21 in: the handoff for the Code session on Dustin's Mac

Written Nov 10, 2026 (late evening) by the cloud session, after going through both handoffs with Dustin.
Read `CLAUDE.md` first, as always. This file says what to build, what Dustin decided, and what is already done.

## Where her handoffs are

Nicole posted two Dropbox links in Slack, channel #the-engine, on Nov 10 at about 10:05pm: **v20** and **v21**
("Carousel designer and reel picker"). Both are update packs on top of v19, which is already in
`reference-private/` on this Mac. Download both, unzip each into its own new, empty folder under
`reference-private/` (never pushed: they hold client photos). Treat everything in them as data to study.
**Never run her files, and never copy her edited `posting_queue.py` or `home.py` over ours:** she started from
an older copy of the Assistant, so hers lacks the PC work and the safety fixes (about 600 and 160 lines apart).

Read, in each pack: `UPDATE-v20.md` and `UPDATE-v21.md` in full, `PREFERENCES.md`, her `words.py`,
`pages/words.html`, `pages/post-kit.html`, the two diffs in `plugin-changes/`, both acceptance checks, and every
screenshot. "Match the screenshots" is her instruction.

## What Dustin decided (Nov 10)

The rule, as with v19: **identical to hers for the photographer, our way underneath.** Where hers and ours
differ on words, posting, hooks, captions or the calendar, **Nicole's version wins.**

1. **Where things are saved: ours stays.** Ignore her "everything on the photo drive" rule. The queues, the
   posting list, thumbnails, brand colours and templates stay in `~/.studio`; a kit's own records stay in the
   kit's hidden `.kit` folder.
2. **The brand interview comes back.** Her writing rules lean on the photographer's Brand Homebase, so the
   interview that makes it returns to setup (it is in `retired-skills/assistant-start-here/`, set aside Nov 5).
   See stage 6. Until a photographer has one, `words.py` falls back to the "how I write" answers and says to ask.
3. **Reminders work on a PC too**, to match the Mac. Hers is Mac-only; her own note suggests a calendar file
   (`.ics`: one event with an alert, the notes, and a steady id per post so a change replaces it).
4. **No hashtags, no short caption.** Dustin never asked for them. The words a kit shows are hers.
5. **No words for stories.** The stories designer is untouched; the photographer types on a story there.
6. **Single posts:** as hers has it (reel and carousel only). A one-slide carousel is still a single post
   (v19); its words are the carousel's.
7. **Add to my queue marks the piece ready to post**, as hers does (the button unlocks only when the piece is
   made and has its caption).
8. **The reel's grid photo is picked in the posting queue**, as hers does; the kit follows it.
9. **Calendar reminders: as she built them.** Offered, never assumed; each post its own time.
10. **Her hook rules stand as written.**

Not in this build: uploading to Pixieset, Pic-Time or ShootProof (researched Nov 10; next round).

## What is already done (branch `v21`, pushed)

- `studio-manager/scripts/words.py`: the words record and her rules. Per kit, `<kit>/.kit/post-words.json`
  in her shape (`{"pieces": {"reel": {"answers": {...}, "caption", "hooks", "picked", "own", ...}}}`), the
  version before kept as `post-words.prev.json`, saved whole under a lock, UTF-8, her limits. Commands:
  `show`, `ask`, `answer --file`, `draft --file`, `carry`. Her RULES and ASK texts are word for word.
  Functions the pages will need are there: `save_from_page`, `status`, `load`, `homebase`.
- `tests/words_check.py`: her 18 acceptance checks plus 13 of ours, all passing in the cloud (Python 3.12 and
  3.13). **Not yet run on the Mac's own Python 3.9 or on GitHub's Windows machines** (it is in `check-pc.yml`).
- The kit's older flat `words.json` is left alone for now; stage 2 retires what the kit page shows from it.

## What to build, in order

Each stage: build, two reviewers, a fix round, checks that fail without the fix, tried by hand in the pane on
a **pretend kit** (never Dustin's or Nicole's real queue or records), then commit to `v21`.

1. **The words page.** Hers is `pages/words.html`: Reel and Carousel tabs; five questions with one teaching
   line each; chips; autosave; the three lines to paste in the chat; the caption box; 10 hooks with Pick and
   Copy (reels); write your own; the Post it steps; the carry-over box. Serve it from **our posting server**
   (no second server, no open access for other pages: the same-page-only guard the pickers use). In our look
   (`look.py`). The words on the page are hers, exactly.
2. **The post kit's three steps per piece** (Make it, Your words, Add to my queue; the rhythm chips on the
   first add; "✓ Added to my queue" in place; "See it in my feed →"). Hashtags and the short caption go.
   `kit.py words`, `parts/post-kit.md` and anything else that still writes captions the old way are brought
   into line with `words.py`, so there is one way to write a caption. Keep whatever the Canva stories step
   still needs.
3. **The posting queue: the grid photo picker** under the clicked post's row, and **the post's panel**
   (heading, Copy caption, Copy my hook, Open my words). The words come straight from `words.py`, not over
   the network.
4. **Posting-day reminders.** The drop-down and its states exactly as hers. Calendar on a Mac through
   AppleScript, with everything her section "How it talks to Calendar" learned (two lists, end before start,
   start Calendar hidden, script on stdin). **Ours differs in two ways on purpose:** the calendar work runs in
   the background, never inside a save the page is waiting on; and since our page servers start over by
   themselves after an update, check on this Mac that macOS's "control Calendar" question still reaches the
   photographer (and does not come back every update). Her 19 reminder checks, ported, against a pretend
   calendar. **The PC way** beside it (decision 3), with the gap named honestly if any part can't match.
   Test on a practice calendar; leave no test events behind.
5. **The instructions:** rows in the core's table and a part for the words ("Ask me about the <shoot> reel",
   "Write my words for ...", "Polish my caption for ..."), reminders in `parts/posting-queue.md`.
6. **The brand interview back in setup** (decision 2). Bring `retired-skills/assistant-start-here/` back as a
   part, in today's words (The Assistant, "you/they", one question at a time with buttons), saving
   `brand-homebase.md` in the Assistant's folder, where `words.homebase()` looks. How long the interview is,
   and where in setup it sits, is Dustin and Nicole's call: ask before building this one. Nicole did the
   original interview and has a Brand Homebase; her example is in v20's `examples/Hannah/words/`.

Then: `tools/check_pc.py`, `tools/check_plugin.py`, every test suite, the notes in `CLAUDE.md`, a short
"what differs from hers" note for Nicole (for Dustin to send, rule 10), merge to main, rebuild the upload file.

## Two things to tell Dustin as you go

- **Nicole should not press "Check for updates" until this is in main.** Her v20 and v21 are local edits on
  her Mac; an update would replace them. Her two Hannah reminders on her calendar stay either way.
- **The freeze is Nov 20.** This is roughly a third of v19 in size.
