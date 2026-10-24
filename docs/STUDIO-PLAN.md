# The Studio: what changed last night, what it means, and a plan to argue with

Written Oct 22, 1am, from Nicole's two briefs (v3 is the one that counts), the 42-minute recording of the two of you, the Slack thread, and everything built and tested on the Engine so far. Nothing here is decided until you two say so.

## 1. What changed, in one breath

The Engine stops being the product and becomes one employee. The product is **The Studio**: a staff that lives on the photographer's computer. The **Studio Manager** handles everything around the art from the moment a card goes in (backup, checks, review markers, sorting a mini-session day, sneak peeks, client note, calendar, gallery setup, export check, upload) and then hands her favorites to the **Assistant** (the Engine), which makes the reel, carousel, stories and captions. The **Concierge** (inbox, milestones, testimonials, gifts) is the first "new hire," sold later as an add-on. One install, one Studio File, one set of folders, one voice. One-time purchase, runs on her own Claude plan. Black Friday is off. Nicole wants January 1.

Three things in the recording that weren't in the briefs and matter for the build:

- **Dustin: the overnight jobs may belong on the Code side of Claude**, because long unattended work needs to run without a permission tap at every step. The plugin we built already runs in both the desktop app and Claude Code; the question is which one hosts which job.
- **Nicole on the reel: "it's not even trying to be a video editor."** Song first, cuts on the beat, no transitions, no cinematic effects, no decoration. Dustin: "the Ken Burns effect is the worst." That settles yesterday's argument in a direction I didn't expect, and it's the right one for photographers: the photos carry it. The complaint students actually have is landing on the beat, and that part works.
- **The mini-session day** is the one hard case Nicole named: eight families on one card, sorted by the timestamps against a screenshot of the booking calendar, with a note, sneak peeks and captions for each.

## 2. The Assistant: what survives, what's cut, what was wasted

What survives from the last six days, untouched: the interview and the Brand File (becomes part of the Studio File), the playbook and guardrails, hooks in her voice, captions on request, carousels and stories, trial reels, the contact sheet, beat detection, the grader, the no-install finding, the fonts, the warm voice.

What changes because of Nicole's call: the photo motion comes out (hard cuts, still photos), the "editorial / clean / label" text is kept but used sparingly, and the formats become her list: behind the scenes into photos, photos only, B-roll, a behind-the-scenes sneak peek, and the **DM testimonial with photos flashing behind it** (new; easy: a screenshot layered over fast photo cuts). Add **song preview**: she hears a few seconds of each candidate before picking. Add the **matching moment** later, not now.

What last night's CapCut test means now: the Assistant can hand back an **editable CapCut project** as well as a finished MP4, on a Mac, with nothing installed. With effects off the table, CapCut's value isn't transitions; it's that she can open the cut, swap one photo, retype the hook, and export. Keep both outputs, MP4 as the default, CapCut project as "open it in CapCut if you want to change anything." Windows and Intel Macs still untested, same as before.

Yesterday's work on smooth motion, text styling and the stricter grader is not wasted: the grader, the text engine and the audio mixing all carry over; the motion code just gets switched off by default.

## 3. The Studio Manager: an honest feasibility read, promise by promise

I checked what the Claude workspace on your Mac can actually do tonight. This is the build reality, not the marketing.

| Promise | Reality | Risk |
|---|---|---|
| Copy from the card to her drive, then to her cloud drive | Plain file copy, `rsync` is already there. The card and the drive just have to be connected folders in the desktop app once. | Low. Needs a test with a real card: does the card show up at the same path every time. |
| Never deletes anything | Better than a promise: the workspace **can't delete** inside a connected folder unless she explicitly grants it. The guarantee is enforced by Claude, not by our good intentions. | None. This is a sales-page line. |
| Every file checked, both copies identical | Hashes of every file, original vs each copy. Standard. | Low. |
| Marks blinks, missed focus, near-duplicates | Near-duplicates: easy (image fingerprints). Missed focus: rough but useful (sharpness score, flagged for review only). Blinks: OpenCV 5 is installed with a modern face detector; eyes-closed needs one small model file we bundle. RAW files: ImageMagick on the workspace reads CR2, CR3, ARW, NEF, DNG, RAF, ORF, so we can pull previews without her exporting anything. | Medium. The rule that makes it safe: all of this is done by local scripts, not by Claude looking at every photo. Claude looks at a shortlist. Otherwise a 2,000-image session would burn her plan. |
| Sorts a mini-session day into families | Timestamps from the files plus the booking screenshot. Doable. | Medium. Gaps between families are usually obvious; back-to-back with no gap needs her confirmation. |
| Suggests sneak peeks, drafts the client note | Shortlist by local scoring, then Claude picks three and writes the note in her voice from the Studio File. | Low. |
| Adds the delivery date to her calendar, drafts the email | Google Calendar and Gmail connectors exist; she connects her own Google account once. | Low. |
| Sets up the gallery, uploads, sets the cover, checks the count | **This is the hard one.** ShootProof has a real developer API. Pic-Time has an API for integrations. Pixieset has none, so it means driving the Pixieset website in her browser, which is slow and breaks when Pixieset changes its pages. | **High.** "All three on day one" is the single biggest schedule risk. See section 5. |
| Works overnight while she sleeps | The Claude desktop app has to be open and the Mac awake. A laptop with the lid half closed goes to sleep. She sets the Mac not to sleep on session nights (one setting; we teach it). Permission prompts: the desktop app writes into connected folders without asking, so a backup runs unattended today; anything beyond her folders (the gallery site, email) still taps her. | Medium. Dustin's instinct about the Code side is right for the long jobs; test both. |
| Learns from her edits | The Studio File updates when she rewrites a draft. Same mechanism as the Brand File. | Low. |
| Runs on her own Claude plan at no cost to us | True. Token cost per session is small if the heavy lifting stays in scripts (above). | Low, if we hold that rule. |

Two more things to decide early because they shape everything:

- **Where the files live.** Nicole said it on the recording: nobody has room on their laptop. So the Studio File asks for the session drive (external or a folder) and the cloud drive (Dropbox or Google Drive folder on the Mac, which syncs on its own). The Studio Manager never assumes the desktop.
- **Card formatting stays hers**, after the report says "safe in two places." That line is already in the brief and it's right.

## 4. The product structure, confirmed against how you sell

One product, one install, add-ons for new hires: it matches Kajabi upsells and order bumps, and it gives a launch moment per hire. The one risk is the first one: a photographer who only wants reels now has to buy "a studio." Keep the Engine (Assistant alone) as the cheaper door, as the brief says, and make the upgrade path real: the same install, flip on the Studio Manager.

Pricing isn't decided. One number to settle before anything else: what she already pays Claude. The Studio is sold on top of a Claude plan she buys herself; the sales page has to say that plainly, and the price has to make sense next to it.

## 5. A January 1 plan that's actually buildable

Ten weeks, two holidays in the middle. The full Version 1 in the brief is bigger than ten weeks if "all three galleries on day one" is literal. My recommendation:

**Weeks 1 to 2 (to Nov 5): the safety core.** Card in → copy → cloud copy → every file checked → review markers → the morning report. Run on one of Nicole's old, already-backed-up sessions. Nothing else gets built until this passes with every file checked by hand. This is also the moment the Studio File interview gets written (Nicole's Claude is drafting it; it needs the setup questions: drives, naming, promises, apps, voice).

**Weeks 3 to 4 (to Nov 19): the rest of the night.** Mini-session sorting, sneak peeks, client note, calendar, and the handoff: "the gallery is delivered, pass the favorites to your Assistant?" Assistant reel scope simplified to Nicole's list, with the song preview and the DM-testimonial format. First live session with every step waiting for approval.

**Weeks 5 to 6 (to Dec 3): galleries.** ShootProof and Pic-Time through their APIs first, because they'll be reliable. Pixieset through the browser last, because it's the fragile one, and it's probably the one most of your students use, so it can't be skipped. Export check and count.

**Weeks 7 to 8 (to Dec 17): beta.** Five photographers, different computers (one Intel Mac, one PC), different galleries, past sessions first, then live. Nicole records the walkthrough videos on her own machine during this; they double as launch content.

**Weeks 9 to 10: fix what beta found, sales page, Kajabi, launch.** January 1 is a Thursday and a holiday; January 6 is the first day people are back at their desks. Your call.

What gets pushed to Version 2 to make this fit: the Concierge (already planned), learning from edits, the Sunday recap, invoices, and any gallery platform beyond the three.

## 6. Code side or desktop side

The plugin as built installs in both. Here's how I'd split it, to test rather than assume:

- **Studio Manager overnight jobs on the Code side**, because it can run a long job to the end without tapping her, and it has scheduled tasks ("check the card drive at 9pm," "Sunday recap"). Nicole's walkthrough covers the install once.
- **The Assistant and the morning report in the desktop app**, where she talks to it like a person and taps approve.

If the desktop app alone turns out to run the overnight job unattended (it already writes into her folders without asking), we don't need the split. Test in week 1 on the safety core and decide from what happens, not from what we think.

*(Oct 23 update: tested. The desktop workspace stops any process the moment a step returns, 180 s max per step, so the first 6.9 GB backup died silently at 1.1 GB. Made the script resumable with a `--budget`, and it finished in chunks. That works, but it is the wrong shape for an overnight job. Development moves to Claude Code; the overnight jobs run there.)*

## 7. Open decisions for the two of you

1. Reel look: hard cuts only, photos still (Nicole), or the smooth motion stays as an option (Dustin yesterday). My read: Nicole's call for launch, motion as a switch that's off.
2. January 1 or January 6.
3. Galleries on day one: all three, or ShootProof + Pic-Time at launch and Pixieset the week after if it isn't solid. I'd rather launch with two that never fail than three where one breaks on a Tuesday.
4. The Engine alone: still sold as its own door, at what price.
5. The name. "The Studio" is working, and you both lit up at it. Check the trademark and the handle before you fall in love.
6. Who tests: which five photographers, and which old session of Nicole's is the first one through.

## 8. What I'd start on tonight, if you say go

The safety core, exactly as the brief orders it: a script that copies a session from a card (or any folder) to the drive she names and to her cloud folder, checks every file both ways, marks duplicates and soft-focus for review, writes the morning report, and stops loudly on any problem. Run on one of Nicole's backed-up sessions, with the results checked by hand, on your Mac, before anyone sees a sales page.

*(Oct 23: the copy-and-verify half of this is built and proven on Dustin's R5 card to his RAID. Markers, sorting and the report's richer sections are next.)*

Sources for the gallery claims: [ShootProof developer API](https://developer.shootproof.com/) · [Pic-Time API listing](https://jentic.com/apis/pic-time)
