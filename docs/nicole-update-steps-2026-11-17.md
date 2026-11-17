# Nicole: moving to the newest Assistant, a fresh install (for Slack, Nov 17 to 18, 2026)

Written as Dustin's Claude, for #the-engine, the night of Nov 17 (Dustin: "Slack Nicole, she's going to want to be working on this in the morning with the latest version... archive the version that she's been working on so that she could not lose anything, but also be able to do a fresh install"). Replaces the Nov 13 steps (`docs/nicole-update-steps-2026-11-13.md`), which were sent on Nov 13 but never acted on: v25, v26 and v27 came in between.

What is different from Nov 13: her v19 to v27 are all built in; the route is a **fresh install from the hf-tools marketplace** (so Check for updates works for her from now on), with the upload file as the fallback; her safety copy is dated Nov 18; and the words copy is unchanged.

Five messages, one thread. 1 and 2 go together. 3 goes in the same thread so she has it in the morning; it says to wait for her Claude's report only if anything in it looks off. The zip is attached to 3.

---

## Message 1

*Nicole: the newest Assistant is ready, with your v25, v26 and v27 built in. Here's how to move to it in the morning without losing anything.*

This is Dustin's Claude writing, overnight. Everything you've sent through v27 is in the main Assistant now (a few places differ on purpose; a short list is in message 5). Moving is a one-way step: after it you use the built-in pages, and the pages your Claude built are retired. Read this first part before you press anything.

*What the switch means*
• Nothing of yours is deleted. Your photos, backups, finished slides, stories, songs, videos and CapCut projects stay exactly where they are. Step 1 makes a full safety copy of your version anyway, so you can always open it and look.
• On shoots you already worked on (Katie, Hannah, Aurora), the new reel, designer and talking reel pages open looking *empty*. Your words come over in Step 1. Your old work is still on your drive and in your safety copy; the new pages just don't show it. Finished reels, slides and stories are files in the shoot and carry over as they are.
• Your own pages are retired after the switch. Don't start their server again, and don't have your Claude copy anything back.
• You're the first person to install this way on a Mac that isn't Dustin's. Send a screenshot at each step, so we can see what you see.

*Before you start* (about half an hour, in one sitting)
1. Plug in your photo drive and leave it in the whole time.
2. Let any backup finish.
3. Last call on your own pages: press *Save slides* or *Save stories* on any design you care about, *Save my video* or *Make this one in CapCut* on any B-roll you're part way through, and *Make it in CapCut* on any talking reel. Finished pieces carry over. Half-done ones would need redoing on the new pages.
4. Write down the names of any fonts you added in your designer.
5. Close every page that's open beside the chat.

*Step 1: have your Claude make the safety copy*
Open the chat where you and your Claude built your version. Copy everything in the grey box in the next message and paste it there. Paste its report here. If anything in it says STOP or looks wrong, wait for Dustin; otherwise carry on to Step 2.

---

## Message 2 (the whole message is one code block)

```
I'm about to switch to Dustin's newest version of The Assistant, which has our v19 to v27 handoffs built in. Before I do, I need a safety copy. The only things you may do are: stop your own page server, read, and make the copies listed below. Don't edit, move, rename or delete anything, don't edit the installed plugin, and don't start the server again afterwards. Do the steps in order. If you can't find something or aren't sure, stop and tell me instead of guessing.

1. If the page server from "Carousel designer and reel picker" (port 8799) is running, stop it, and only that one. Leave anything on 8790, 8770 or 8765 alone. Tell me the exact command you normally start it with, including its --content, --studio and --queue-home folders.

2. Tell me where each of these is on this Mac:
(a) the "Carousel designer and reel picker" folder, and the Handoffs folder beside it if there is one;
(b) every installed copy of The Assistant plugin: read ~/.studio/code-home.txt (the plugin folder is three folders up from the scripts folder it names, the one holding .claude-plugin and skills), and also search ~/Library/Application Support/Claude and ~/.claude for folders named studio-manager and go two folders up from each;
(c) the folder you save my work in (the --studio folder), and any "data" folder beside server.py.

3. Tell me how big each of these is: (a), each copy in (b), the ~/.studio folder, and (c) without its cache folder. If the total is over 2 GB, or this Mac has less than 10 GB free, stop and tell me. Otherwise make a new folder directly in my home folder called "Assistant-before-update-2026-11-18" (not in Documents or Desktop, not anywhere under Library, not inside the folder I open my chats in; if it already exists, add "-2"). Copy into it: (a) whole; each copy in (b) whole; ~/.studio whole; and from (c) only these if they exist: designs, story-designs, templates, story-templates, words, reel-pages, reels, talking, brand.json, brand-homebase.md, and a "data" folder beside server.py. Leave out cache, drop, and any folder named after a backup. Count the files in each copy against its original and give me both numbers. Then write a short README.txt in that folder saying what it is, the date, and that it is a frozen copy to look at, never to run or copy back.

4. Bring my words over. In the words folder inside (c), each file is named "<shoot folder name>.json". For each one (skip any file with .prev in its name): find the folder with exactly that name inside my Your Content folder (the --content folder). If that shoot folder has a hidden .kit folder with kit.json in it, and has no .kit/post-words.json yet, copy the file there as .kit/post-words.json (copy, never move, never write over anything), then compare the copy with the original. If the name doesn't match exactly, or there is no kit.json, or a post-words.json is already there, skip it. Tell me each one you copied and each one you skipped, with the reason.

5. List any file you've changed since the v27 handoff, in "Carousel designer and reel picker" or in the installed plugin. Say whether the installed posting_queue.py and home.py still contain your 8799 changes.

6. List every shoot folder in Your Content and say for each whether it has a hidden .kit/kit.json.

7. Tell me whether any folder in (a), (b) or (c) sits inside ~/Library/Application Support/Claude, and what my Studio File says about where backups go and how folders are named.

8. Give me one short report of all of the above that I can paste to Dustin.
```

---

## Message 3 (The-Assistant.zip attached; it is the fallback, not the first route)

*Step 2: the fresh install*
This time you install from the Assistant's own marketplace instead of uploading a file, so from now on a new version is one button (Check for updates). You're the first person outside Dustin's account to do it, so go slowly and screenshot each screen.

1. Open claude.ai in your web browser (not the desktop app for this part) and click *Plugins* in the left column.
2. Find the row called *The Assistant* that you uploaded on Nov 5. Open it and choose *Remove* (or *Uninstall*). Your safety copy from Step 1 has every file of it, so nothing is lost. Screenshot before and after.
3. At the top right click *+ Add*, then *Add marketplace*, then *Add from a repository*. Type exactly this and click *Sync*:
```
horizonfound/hf-tools
```
   If it says hf-tools is already added, that's fine: open *Manage marketplaces*, click the three dots beside hf-tools and *Check for updates*.
4. Search Plugins for "Assistant"; you should see *The Assistant* by Horizon Found, "From hf-tools". Click *Add* (or *Install*).
5. Check it shows as installed with no red line. Screenshot. Then quit the Claude desktop app completely and open it again.
6. If step 3 or 4 refuses, or *The Assistant* doesn't appear within a minute: stop, screenshot, and do the old route instead: *+ Add*, *Upload plugin*, and pick the attached *The-Assistant.zip* from Downloads (don't open the zip). If it asks about the one you already have, choose *Replace*.

*Step 3: tell your Claude the new rules*
In the chat where you built your version, paste everything in this grey box:
```
The Assistant now has everything from our handoffs through v27 built in: the reel page with its four kinds of reel, the footage editor, B-roll with Save my video, the carousel and stories designer, the words page, the posting queue with Posted on the post, the home base, the editing queue and the talking reel. From now on the Assistant's own pages and commands are the ones to use. Don't start the server in "Carousel designer and reel picker", don't edit files inside the installed plugin, and don't re-apply your earlier changes to it. The folder "Assistant-before-update-2026-11-18" is only for looking things up: never run anything from it and never copy anything from it back. Saved work now lives inside each shoot's own folder and in the Assistant's folder on this Mac, not all on the drive, and that is expected. Don't run any Assistant command in this chat from now on, not even to check; I'll use a new chat. If something I ask for is missing from the built-in version, tell me so I can tell Dustin; don't build it yourself. Please add this at the top of PREFERENCES.md in "Carousel designer and reel picker" and of any other notes or memory a new chat of ours reads, and tell me which files you saved it in.
```

---

## Message 4

*Step 4: start fresh and test*
1. Close any page open beside the chat. Start a *new* chat in the same folder you always use for the Assistant and say hi. Don't carry on in an old chat.
2. *How to tell you're on the new version:* the home page says "Welcome to your home base." and the address at the top of the page ends in 8790. If it ends in *8799*, you're on your old version: stop and say "open the Assistant's own page".
3. First round, a shoot you haven't made posts from before: on the home base click *Make posts from a shoot*, pick the folder of finished photos, paste "make my posts". Then try, in any order: the reel page (the chooser of four kinds, a behind-the-scenes reel, B-roll with Save my video), the carousel designer, stories, the words page, the posting queue, a talking reel. Anything you add to the posting queue while testing lands in your real queue.
4. Keep Katie, Hannah and Aurora for a second round. Anything empty there, note it as "empty on an old shoot".

*When you report something:* say which shoot, and send a screenshot with the address at the top showing.

*Getting a newer version from now on:* when the Assistant says "a newer version of me is ready", say "show me how". The page beside the chat shows the one button (Plugins › Add › Manage marketplaces › the three dots beside hf-tools › Check for updates). After it says Synced, start a new chat. Claude may show "Executable files or settings may differ from the version you were using before this sync": that's the new version arriving.

---

## Message 5

*Things you'll notice, all expected*
• The first time you press *Edit my video* on a talking reel, your Mac will most likely ask about Speech Recognition, naming "Assistant Transcriber". Press Allow.
• Open your calendar and look at your posting reminders. There should be no doubles, and each should still have your caption in its notes. If one says "No caption yet", tell me which post.
• An old shoot might show its old sets as one long carousel until you save a set from the new designer, or might not be listed on the new pages at all. Tell me which; it's still on your drive.
• If a page says it can't reach a shoot, the drive is unplugged. Plug it in and reload.

*Where it differs from yours, on purpose* (the full list is in the notes Dustin has)
• Photo numbers stay fixed when you add photos to a shoot: new ones take the next numbers, a removed photo's number is never reused, so a pick or a design never points at the wrong photo. A shoot's list can have gaps.
• Save my video draws your words with the Mac's own text engine and nothing installed; on a PC it says plainly that it isn't there yet and offers Make this one in CapCut.
• The path at the top of every post kit page is built by the Assistant itself, so Home works whatever port the page is on.
• Remove this song goes to the Mac's Trash (the Recycle Bin on a PC) through one door; a drive with no Trash is refused in plain words, and a recording in the Photos folder stays.
• Open folder on the designer is one button in the bottom bar, there all the time, serving both of yours.
• Remove this slide is off with "It's your only slide, so it stays." when there is one slide; a dragged slide goes back on Escape.
• Fixing a word on the talking reel keeps what was heard underneath and lays your fix over it, so captions and CapCut always see your word; a video turned into a script again keeps its fixes with the earlier cuts.
• Open CapCut on the talking page starts CapCut the reel page's way, on a Mac or a PC, and says so when it takes a while.
• A clip that is the whole of a short video plays a touch slower to fill its beat instead of stopping the reel.

*Four rough edges we know about and haven't fixed yet* (all on the designer; say if any bites you)
• Pressing + Add photos while you have an unsaved change can refuse the save with "The photos in this shoot changed since this page opened" and ask you to reload; save first, then add.
• Remove this slide also takes a photo that stretches well across the slide's edge. Undo brings it back.
• Your Open folder tooltip ("Open the folder your saved slides go in") isn't on ours yet.
• Finishing a cut-off single-slide save from the chat can fail with an error instead of a sentence.

*Still waiting on you and Dustin* (asked on Nov 14, still open)
• The folder-naming question at setup: name then date (yours) or year first (Dustin's October call). Not changed until you two agree.
• The copy left in "Drop a shoot here": Trash it after the copy is checked, skip the drop box, or leave it. Not changed.
• Remove this song: built as your v27 has it, two taps and the recording goes to the Mac's Trash. Say if you'd rather it only left the list.
