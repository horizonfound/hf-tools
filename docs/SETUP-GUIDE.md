# Setting up The Assistant

> **Replaced on Nov 5, 2026 by the PDF guide (`docs/The Assistant - Setup Guide.pdf`, built from `docs/install-guide/`). Do not write install steps from this file.** Its Steps 3 and 4 describe routes that failed on Nicole's Mac; see `docs/install-issues-2026-11-05.md`. Kept for its notes on the phone taps and the first backup.

**Draft 2, Nov 5, 2026** (first draft Oct 28). For the printable guide and the walkthrough video. Plain words, one thing per step, every step something to click or paste. Lines marked **[check]** come from the official Claude docs but have not been clicked through in the desktop app yet; confirm each on a fresh Mac before this goes out. Screenshots to add where marked **[shot]**.

---

## Before you start

You need four things:

- A Mac. (There's a separate guide for a Windows PC; see the end.)
- **An external hard drive for your shoots.** If you already keep your photos on one, you're set. If your shoots live on your computer, this is the moment to change that: a computer can be dropped, die or get stolen, and the photos on it go with it, while a drive on the shelf is still fine. Raw files are also big, and a few shoots can fill a laptop and slow it down. Any external drive with room to spare works; the Assistant asks for it by name on the first backup. (It will still work onto the computer if you have to, and it will say its piece about it once.)
- A Claude plan. The Assistant runs on your own Claude account, and it needs the **Pro** plan or higher. The free plan does not include Claude Code, which is the part of Claude the Assistant lives in. **[check: plan names on the current pricing page]**
- About twenty minutes, once. After this, every backup starts with two words.

---

## Part 1: The one-time setup

### Step 1: Install Claude on your Mac

1. Download the Claude desktop app for macOS from claude.ai/download. One download works for every Mac. **[shot]**
2. Open it from your Applications folder and sign in with your Claude account.
3. At the top of the sidebar, click **Code**. **[shot]**

If Code asks you to upgrade, your plan does not include it yet. If it asks you to sign in online, follow that link, then come back.

### Step 2: Pick where the Assistant works

The first time you open Code, there is a row of choices under the message box: where to work, which folder, how much to ask you, which model.

1. Under the message box, click the folder choice, choose **Open folder…**, press **Command + Shift + H** to jump to your home folder, and make a new folder there called **Assistant**. This is only where the Assistant keeps its own notes; your photos never go here. **Not inside Documents, Desktop or Downloads:** the Mac guards those and blocked Claude on Nicole's first try ("Couldn't access Documents", Nov 5). **[shot]**

### Step 3: Add The Assistant to Claude

> **Superseded later on Nov 5: the PDF guide installs from a file instead** (+ Add, **Upload plugin**, The-Assistant.zip). The steps below use Add marketplace, and Claude's copy of hf-tools from that route has not refreshed since Oct 16 (`docs/install-issues-2026-11-05.md`, item 4). Kept as a record; follow the PDF.

**Corrected Nov 5, 8pm, from Nicole's first try.** Pasting a `/plugin` line into the desktop app's message box does not install anything: it opens Settings on Customize, Plugins. That Settings box is the way in (it is also how the Engine was installed in October).

1. Click the **gear** at the bottom left of the Claude window, next to your name. Settings opens.
2. In the list on the left, click **Customize**. Then click **Plugins** at the top.
3. Click **+ Add** at the top right. Choose **Add marketplace**, then **Add from a repository**. **[check: the exact words in the + Add menu; these are from the October install notes]**
4. Paste `horizonfound/hf-tools` and click **Sync**.
5. Click **Discover**, and type **Assistant** in the search box.
6. Click the **+** on **The Assistant**. Close Settings.

If it says hf-tools is already added, find it in the list and click **Sync**. If "The Engine" shows and "The Assistant" does not, the October copy is still there and has not synced.

### Step 4: Getting updates

**[check, all of it]** Installed this way, the Assistant lives on the Claude account, not in a folder Claude Code manages, so the `/plugin` auto-update switch from Draft 2 does not apply. The October notes say updates arrive on their own and that an **Update** button on the plugin's page (Settings, Customize, Plugins, Yours, The Assistant) forces one. But Dustin's account was still on the Oct 16 copy (0.2.4) on Nov 5, after 0.3.1 was pushed Oct 21, so "on their own" did not happen at least once. Until this is seen working: after we push a fix, the photographer opens that page and clicks **Sync** on hf-tools and **Update** on The Assistant.

### Step 5: Let the Assistant work while you're away

This is the step that makes "walk away" true. Without it, Claude stops every few seconds to ask "may I run this?", and a backup can't finish while you're out of the room.

1. In the row under the message box, find the choice that says **Manual**. Click it. (Or press **Cmd+Shift+M**.) **[shot]**
2. Choose **Auto**.

Auto means Claude runs the backup's steps without asking each time, with its own safety checks running in the background. It remembers this choice for your Assistant folder. If **Auto** is not in the list, make sure Code is set to a current Claude model in the same row; Auto needs one. **[check: the model requirement wording]**

Nothing in The Assistant ever deletes, moves or changes a photo on your memory card. That is a rule the Assistant's own scripts enforce, in any mode.

### Step 6: Claude on your phone

The Assistant can tap you on the phone when a backup is done, or when it's time to swap cards. Three short steps.

**6a. Install the Claude app on your phone.** From the App Store or Google Play. Sign in with the **same** Claude account you used on the Mac. When the phone asks whether Claude may send notifications, say **Allow**. **[shot]**

**6b. Link your Mac to your phone.** Back on the Mac, at the top right of the Code window, click the first of the small icons (the one that says **Show session rail** when you hover). A panel opens on the right. Under **Environment**, flip the **Remote Control** switch on. **[shot: the session rail with the switch on; Dustin's screenshot, Oct 28]**

Your session now shows in the Claude app on your phone, under **Code**, with a small computer icon and a green dot. **[shot]**

To have this happen on its own every time: open the Claude app's **Settings**, go to **Code**, and turn on **Connect new sessions to Remote Control**. **[check: exact label]** (Typing `/remote-control` in the message box does the same thing as the switch.)

**6c. Turn on the phone taps.** In the message box on the Mac, paste each of these lines and press Return after each:

```
/config agentPushNotifEnabled=true
```

```
/config inputNeededNotifEnabled=true
```

The first one lets the Assistant tap you when a backup finishes. The second taps you when it's waiting on an answer. Each line answers with "Set … to true". (Tested Oct 28 on Dustin's Mac: both lines worked typed into the Code message box, and the taps arrived.)

**Good to know about the taps:**

- The Mac has to be awake with Claude open. The Assistant keeps the Mac from dozing off during a backup, but a closed lid still sleeps, so leave it open.
- If you're sitting at the Mac, the tap is skipped: you can already see it on screen. It only goes to your phone when you've walked away.
- On an iPhone, a Focus mode or a notification summary can hold the tap back. Check Settings, Notifications, Claude.
- If a tap never comes and you've done all this, open the Claude app on your phone once; that refreshes the link.

That's the setup. You never do it again.

---

## Part 2: Opening the Assistant, and your first backup

**Opening the Assistant.** Click the Assistant in the left column, start a new chat, and just say **hi**. **[check: whether typing /assistant also works from an installed copy; the docs suggest it shows up as /the-engine:assistant, so "hi" is the one to teach]** The first time, the Assistant introduces itself and opens its home page beside the chat; once you've done a few things together it answers with the day instead (what's due, what's queued to post, whether it sees a card). You don't need a memory card to start: if you have photos you've already finished, you can begin with posts. The home page has a button for everything it can do, and your recent shoots. Click any button to see what it does; if it's something you do together, it tells you what to say. That's the whole interface. Say what you want, in your own words, the way you'd say it to a person.

**The very first time, on a newer Mac: one free piece from Apple.** The Assistant runs on a small piece of software that Apple supplies but doesn't put on every Mac ahead of time. If yours doesn't have it yet, a window from Apple pops up the first time you say hi, asking to install "command line developer tools." Click **Install**, then **Agree**. It takes five to ten minutes. When it says it's done, tell the Assistant "done" and it picks up where it left off. You never see this again. **[check on a Mac that has never had it: the window's exact words, and how long it takes]** **[shot]**

**Your first posts (no memory card needed).**

1. On the home page, click **Make posts from a shoot**. A box opens under it that tells you what to do.
2. The first time, it asks you to paste **set up my Assistant folder** into the chat. The Assistant asks where your posts should be kept (your photo drive is the usual answer) and makes one folder there, called The Assistant, with Your Content inside it.
3. Back on the home page, click **Make posts from a shoot** again, then **Select the folder with your finished photos**. Pick the folder you exported from Lightroom. The Assistant makes its own copies of the JPEGs in it; your originals aren't moved or changed.
4. Paste **make my posts** into the chat. The Assistant looks through what you brought, asks what to call the shoot, and asks one open question: anything you'd want to say about it. Say as much or as little as you like. The words in your captions come from what you tell it.
5. It makes a post kit: single posts, a carousel, stories and a reel cover, all sized for Instagram, plus hooks and a caption, on one page with a Copy button on each. The reel is a project waiting in CapCut, cut to the beat, for you to style and export. **[check: on a Mac other than Dustin's, with that Mac's CapCut]**

Nothing is ever posted for you. The kit is yours to post from.

**Your first backup.**

1. Put your memory card in.
2. In the Code message box, type **backup now** and press Return. (You can also press the microphone key on your keyboard and say it. **[check: which dictation to point to; Claude's own `/voice` is documented for the terminal only]**)
3. The first time, the Assistant tells you it has a few quick questions, only this once, and asks them one at a time, with buttons:
   - Which drive your shoots go on.
   - Right on that drive, or inside a folder.
   - Whether you copy shoots to a second drive too.
   - How you like a shoot folder named.
   - How you write to clients, so it can draft notes in your voice.
   - How often you like to post.
4. Then two questions it asks every time: how many cards for this shoot, and what's on the card. Say what's on it however you'd say it ("Smith family, beach session, Sarah's the mom, due in two weeks"), or skip.
5. Then it says:

   **You can walk away. I'll have the report ready when you're back.**

From then on, "backup now" asks only those two quick questions.

### When you come back

Your phone has tapped you, and the last thing in the chat is a button: **Show the report**. Click it. (If you were away a long while, the page beside the chat may have gone blank. That's normal; the button brings the report back.) Top to bottom: every photo backed up and checked, byte for byte, and the card is safe to format; what's on the card, one block per shoot, each with six sneak peeks picked to edit first; a note to your client, ready to copy; and a button that opens the folder your photos are in.

On each shoot:

- **Click any photo** to see it big.
- **The name box:** click in it, type a better name, press **Rename**. The folder and every photo in it are renamed to match.
- **The six sneak peeks** are a first pass, to get you rolling. **Pick again** lets you say what you'd rather see. **Show me more** lets you choose your own: drag a photo onto one of the six numbered spots, or click any photo to see it big and place it from there.
- **Add to my editing queue:** click, pick a date on the calendar, Save. **Show my editing queue** opens your list of shoots to edit.
- **Copy the note** puts the client note on your clipboard, ready to paste into an email. Nothing is ever sent from the Assistant.

In Lightroom, the sneak peeks are one filter away: the keyword **sneak peek**.

**Getting around.** Every page has a **Back to home** button at the top left. On the home page, your recent shoots each have **See the report**, so you can always get back to a report to rename a shoot or change its sneak peeks.

### Things to say to the Assistant

- **show me the report** · **show my shoots** · **what's in my queue**
- **the first one is the Garcia family** (names a shoot)
- **I'm done with the beach shoot** (starts the reel and carousel)
- **backup now** (always)

---

## If something goes wrong

- **The page beside the chat is blank, or shows a play button.** Don't press the play button. Say **show the Assistant** (or **show me the report**) and the page comes back.
- **A window from Apple asks to install "command line developer tools."** That's the one free piece the Assistant runs on. Click Install. See "The very first time" in Part 2.
- **The backup stopped.** The report says why, first thing, in plain words. Fix that (plug the drive in, clear space) and say **backup now** again. It picks up where it left off; nothing is copied twice.
- **No phone tap came.** See "Good to know about the taps" in Step 6.
- **Claude keeps asking permission.** Step 5 wasn't done, or the mode slipped back to Manual. Check the row under the message box.
- **"This card is already safe."** The Assistant recognized a card it has backed up before. Nothing to do.

---

## Windows

The Assistant launches for Mac and PC together. Setting it up on a Windows PC has its own guide, with the two extra things a PC needs.

> **For Dustin:** the PC edition is `docs/SETUP-GUIDE-PC.md` (Draft 1, Nov 6, 2026). It installs the way the PDF does (Upload plugin, not the Add marketplace steps above), adds Python from the Microsoft Store and the Pillow add-on for pictures, and has a box of what doesn't work on a PC yet. Nothing in it has been tried on a PC; it is the script for the first PC walk-through, not a guide to send.

---

## For the video

Record Part 1 start to finish on a Mac that has never had Claude on it, in one take, no cuts, so every pause and prompt is real. Then Part 2 with a real card. Twenty minutes is the target.
