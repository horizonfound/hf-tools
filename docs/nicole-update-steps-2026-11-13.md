# Nicole: moving to the newest Assistant (for Slack, Nov 13, 2026)

Four messages for one Slack thread, written as Dustin. Not sent yet. Messages 1 and 2 go first. Message 3 (with `dist/The-Assistant.zip` attached) goes only after her Claude's report has been read. Message 4 goes once "hi" works on the new version. What this was written from, and what is untried, is in CLAUDE.md under "Moving Nicole to the newest version".

---

## Message 1

*Nicole: the newest Assistant is ready for you, and here's how to move to it safely*

Your v19 to v24 are built into it now (with a few differences on purpose), plus the newer backup work. Moving is a one-way step: after it you use the built-in pages, and the pages your Claude built are retired. Please read this first part before you press anything.

*What the switch means*
• Nothing of yours should be deleted. Your photos, backups, finished slides, stories, songs and CapCut projects stay where they are. We tried this on practice shoots shaped like yours, not on your Mac, which is why Step 1 makes a full copy first.
• On shoots you already worked on (Hannah, Aurora), the new reel, designer and talking reel pages will open looking *empty*. Your words should come over in Step 1. Your old work is still on your drive. The new pages just don't show it.
• Your own pages are retired after the switch. Their Make my reel will very likely stop working, and once you use the new talking reel, the old one can't turn a new video into words.
• Going back is possible but fiddly, and nobody has tried it. If you need it, tell me and we'll do it together. Please don't have your Claude copy anything back.
• Nobody has done this update before, on any Mac. Send me a screenshot at each step so I can see what you see.

*Before you start* (about half an hour, in one sitting)
1. Plug in your photo drive and leave it in the whole time.
2. Let any backup finish.
3. Last call on your own pages: press *Save slides* or *Save stories* on any design you care about, and *Make it in CapCut* on any talking reel you're part way through. Finished pieces carry over. Half-done ones would need redoing on the new pages.
4. Write down the names of any fonts you added in your designer. Those are kept only in the old page.
5. Close every page that's open beside the chat.

*Step 1: have your Claude make a safety copy*
Open the chat where you and your Claude built your version. Copy everything in the grey box in my next message and paste it there. Then paste its report here and wait for me. I'll read it and send the next steps. If you use your own pages again before I do, we run Step 1 again.

---

## Message 2 (the whole message is one code block)

```
I'm about to switch to Dustin's newest version of The Assistant, which has our v19 to v24 handoffs built in. Before I do, I need a safety copy. The only things you may do are: stop your own page server, read, and make the copies listed below. Don't edit, move, rename or delete anything, don't edit the installed plugin, and don't start the server again afterwards. Do the steps in order. If you can't find something or aren't sure, stop and tell me instead of guessing.

1. If the page server from "Carousel designer and reel picker" (port 8799) is running, stop it, and only that one. Leave anything on 8790, 8770 or 8765 alone. Tell me the exact command you normally start it with, including its --content, --studio and --queue-home folders.

2. Tell me where each of these is on this Mac:
(a) the "Carousel designer and reel picker" folder;
(b) every installed copy of The Assistant plugin: read ~/.studio/code-home.txt (the plugin folder is three folders up from the scripts folder it names, the one holding .claude-plugin and skills), and also search ~/Library/Application Support/Claude and ~/.claude for folders named studio-manager and go two folders up from each;
(c) the folder you save my work in (the --studio folder), and any "data" folder beside server.py.

3. Tell me how big each of these is: (a), each copy in (b), the ~/.studio folder, and (c) without its cache folder. If the total is over 2 GB, or this Mac has less than 10 GB free, stop and tell me. Otherwise make a new folder directly in my home folder called "Assistant-before-update-2026-11-13" (not in Documents or Desktop, not anywhere under Library, not inside the folder I open my chats in; if it already exists, add "-2"). Copy into it: (a) whole; each copy in (b) whole; ~/.studio whole; and from (c) only these if they exist: designs, story-designs, templates, story-templates, words, reel-pages, talking, brand.json, brand-homebase.md, and a "data" folder beside server.py. Leave out cache, drop, and any folder named after a backup. Count the files in each copy against its original and give me both numbers.

4. Bring my words over. In the words folder inside (c), each file is named "<shoot folder name>.json". For each one (skip any file with .prev in its name): find the folder with exactly that name inside my Your Content folder (the --content folder). If that shoot folder has a hidden .kit folder with kit.json in it, and has no .kit/post-words.json yet, copy the file there as .kit/post-words.json (copy, never move, never write over anything), then compare the copy with the original. If the name doesn't match exactly, or there is no kit.json, or a post-words.json is already there, skip it. Tell me each one you copied and each one you skipped, with the reason.

5. List any file you've changed since the v24 handoff, in "Carousel designer and reel picker" or in the installed plugin. Say whether the installed posting_queue.py and home.py still contain your 8799 changes.

6. List every shoot folder in Your Content and say for each whether it has a hidden .kit/kit.json.

7. Tell me whether any folder in (a), (b) or (c) sits inside ~/Library/Application Support/Claude, and what my Studio File says about where backups go and how folders are named.

8. Give me one short report of all of the above that I can paste to Dustin.
```

---

## Message 3 (attach The-Assistant.zip to this one; send only after her report is read)

*Step 2: put in the new version* (nobody has clicked this exact path as an update, so go slowly)
1. Download the file attached to this message (The-Assistant.zip). Leave it as it is. Don't open it.
2. In Claude, click the small gear at the bottom left, by your name. In the list on the left click *Customize* (it may be called *Plugins* now). If there's a row of words at the top, click *Plugins* there.
3. Send me a screenshot of that screen and wait for my OK. Don't press Check for updates. It isn't the route for your copy.
4. Click *+ Add* at the top right, then *Upload plugin* (not Add marketplace). Choose The-Assistant.zip from Downloads.
5. Check two things: no line with a red !, and the preview says "The Assistant by Horizon Found". A grey line starting "The archive must contain" is not an error. Then click *Upload*.
6. If it asks at any point about the one you already have, choose *Replace*. We don't know when it asks, or if it does. If you end up with two rows called The Assistant, stop and send me a screenshot. Don't remove one yourself.
7. Send me a screenshot of the Plugins screen afterwards. Then quit Claude completely and open it again.

*Step 3: tell your Claude the new rules*
In the chat where you built your version, paste everything in this grey box:
```
The Assistant now has the reel page, the carousel and stories designer, the words page, the posting queue panel, reminders and the talking reel built in. From now on the Assistant's own pages and commands are the ones to use. Don't start the server in "Carousel designer and reel picker", don't edit files inside the installed plugin, and don't re-apply your earlier changes to it. The folder "Assistant-before-update-2026-11-13" is only for looking things up: never run anything from it and never copy anything from it back. Don't put the old Assistant Transcriber app back in ~/.studio/talking. Saved work now lives inside each shoot's own folder and in the Assistant's folder on this Mac, not all on the drive, and that is expected. Don't run any Assistant command in this chat from now on, not even to check; I'll use a new chat. If something I ask for is missing from the built-in version, tell me so I can tell Dustin; don't build it yourself. Please add this at the top of PREFERENCES.md in "Carousel designer and reel picker" and of any other notes or memory a new chat of ours reads, and tell me which files you saved it in.
```

*Step 4: start fresh and test*
1. Close any page open beside the chat. Start a *new* chat in the same folder you always use for the Assistant, and say hi. Don't carry on in an old chat.
2. *How to tell you're on the new version:* look at the address at the top of the page. If it ends in *8799* you're on your old version. Any other number is the new one (usually 8790 for home and the posts pages, 8765 for a backup report, 8770 for the editing queue). If you ever see 8799, stop and say "open the Assistant's own page".
3. First round, use a shoot you haven't made posts from before: say "make my posts" and pick a folder of finished photos. Then try, in any order and as far as you have time for: reel, carousel, stories, words, the posting queue, a talking reel. Anything you add to the posting queue while testing lands in your real queue.
4. Keep Hannah and Aurora for a second round. Anything empty there, note it as "empty on an old shoot".

*When you report something:* say which shoot, and send a screenshot with the address at the top showing.

---

## Message 4 (send once "hi" works on the new version)

*Things you'll notice, all expected*
• The first time you press *Edit my video* on a talking reel, your Mac will most likely ask about Speech Recognition again, naming "Assistant Transcriber". Press Allow. From then on your old talking page can't turn a new video into words. Your old transcriber is kept, not deleted, but please don't put it back. (We haven't seen this exact moment on a Mac that already had your version.)
• Open your calendar and look at your posting reminders. There should be no doubles, and each should still have your caption in its notes. On a practice calendar that held; yours is the first real one. If one says "No caption yet", tell me which post. It can be put back. If your Mac asks to let "claude" use Calendar, press Allow.
• On an old shoot, the carousel card may show several of your old sets as one long carousel until you save a set from the new designer. A grid photo you picked for an old post may go back to the usual one.
• An old shoot might not be listed on the new pages at all. Tell me which, and it's still on your drive.
• If a page says it can't reach a shoot, the drive is unplugged. Plug it in and reload.

*New since your version, worth a try*
• Talking reel: pick several clips at once (Cmd-click or Shift-click). Two small menus, Speed and Zoom. A line that shows when the caption is centered. Zooms have *How much* and *How fast*, and now ease in and out. We haven't watched the new zooms in CapCut yet, so look closely at those, and at whether cuts and captions land on the words.
• Backups: a quick "Same as usual?" before each backup after your first. A shoot with both photos and video gets a Photos folder and a Videos folder. Sideways clips are stood upright in the backup copy, never on the card. Faces get a stricter check before sneak peeks are picked. The two folders and the face check haven't run on a real card of yours yet, so tell me what you see.
• You wanted folders named client first, then date: with a memory card in, say "backup now", press *Change something*, then *How folders are named*. It applies from then on. Shoots already backed up keep their names. Nobody has pressed Change something for real yet, so send a screenshot if it goes differently.
