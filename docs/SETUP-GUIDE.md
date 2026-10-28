# Setting up The Studio

**Draft 1, Oct 28, 2026.** For the printable guide and the walkthrough video. Plain words, one thing per step, every step something to click or paste. Lines marked **[check]** come from the official Claude docs but have not been clicked through in the desktop app yet; confirm each on a fresh Mac before this goes out. Screenshots to add where marked **[shot]**.

---

## Before you start

You need three things:

- A Mac. (A Windows version is coming; see the end.)
- A Claude plan. The Studio runs on your own Claude account, and it needs the **Pro** plan or higher. The free plan does not include Claude Code, which is the part of Claude the Studio lives in. **[check: plan names on the current pricing page]**
- About twenty minutes, once. After this, every backup starts with two words.

---

## Part 1: The one-time setup

### Step 1: Install Claude on your Mac

1. Download the Claude desktop app for macOS from claude.ai/download. One download works for every Mac. **[shot]**
2. Open it from your Applications folder and sign in with your Claude account.
3. At the top of the sidebar, click **Code**. **[shot]**

If Code asks you to upgrade, your plan does not include it yet. If it asks you to sign in online, follow that link, then come back.

### Step 2: Pick where the Studio works

The first time you open Code, there is a row of choices under the message box: where to work, which folder, how much to ask you, which model.

1. Under **folder**, choose **Open folder…** and pick your Pictures folder, or make a new folder called **Studio** anywhere you like. This is only where the Studio keeps its own notes; your photos never go here. **[shot]**

### Step 3: Install The Studio

1. Click in the message box and paste this line, then press Return:

   ```
   /plugin marketplace add horizonfound/hf-tools
   ```

   It answers "Successfully added marketplace: hf-tools."

2. Paste this line and press Return:

   ```
   /plugin install the-engine@hf-tools
   ```

   If it asks who the plugin is for, choose **Install for you**. **[check: whether the desktop message box accepts these two lines, or whether the + button beside the message box and "Add plugins" is the way; the docs show both the lines and a plugin browser, and say the browser lists only the official marketplaces]**

### Step 4: Keep The Studio up to date

The Studio gets better every week. Turn on updates once and you never think about it again.

1. In the message box, type `/plugin` and press Return.
2. Open the **Marketplaces** tab, choose **hf-tools**, and turn on **Enable auto-update**. **[check: this is the documented path inside a session; confirm the desktop app shows the same tabs]**

Updates arrive on their own a few minutes after you start a session, and take effect the next time you open Code.

### Step 5: Let the Studio work while you're away

This is the step that makes "walk away" true. Without it, Claude stops every few seconds to ask "may I run this?", and a backup can't finish while you're out of the room.

1. In the row under the message box, find the choice that says **Manual**. Click it. (Or press **Cmd+Shift+M**.) **[shot]**
2. Choose **Auto**.

Auto means Claude runs the backup's steps without asking each time, with its own safety checks running in the background. It remembers this choice for your Studio folder. If **Auto** is not in the list, make sure Code is set to a current Claude model in the same row; Auto needs one. **[check: the model requirement wording]**

Nothing in The Studio ever deletes, moves or changes a photo on your memory card. That is a rule the Studio's own scripts enforce, in any mode.

### Step 6: Claude on your phone

The Studio can tap you on the phone when a backup is done, or when it's time to swap cards. Three short steps.

**6a. Install the Claude app on your phone.** From the App Store or Google Play. Sign in with the **same** Claude account you used on the Mac. When the phone asks whether Claude may send notifications, say **Allow**. **[shot]**

**6b. Link your Mac to your phone.** Back on the Mac, in the Code message box, type this and press Return:

```
/remote-control
```

Your session now shows in the Claude app on your phone, under **Code**, with a small computer icon and a green dot. **[shot]**

To have this happen on its own every time: open the Claude app's **Settings**, go to **Code**, and turn on **Connect new sessions to Remote Control**. **[check: exact label]**

**6c. Turn on the phone taps.** In the message box on the Mac, paste each of these lines and press Return after each:

```
/config agentPushNotifEnabled=true
```

```
/config inputNeededNotifEnabled=true
```

The first one lets the Studio tap you when a backup finishes. The second taps you when it's waiting on an answer. Each line answers with "Set … to true". (Tested Oct 28 on Dustin's Mac: both lines worked typed into the Code message box, and the taps arrived.)

**Good to know about the taps:**

- The Mac has to be awake with Claude open. The Studio keeps the Mac from dozing off during a backup, but a closed lid still sleeps, so leave it open.
- If you're sitting at the Mac, the tap is skipped: you can already see it on screen. It only goes to your phone when you've walked away.
- On an iPhone, a Focus mode or a notification summary can hold the tap back. Check Settings, Notifications, Claude.
- If a tap never comes and you've done all this, open the Claude app on your phone once; that refreshes the link.

That's the setup. You never do it again.

---

## Part 2: Your first backup

1. Put your memory card in.
2. In the Code message box, type **backup now** and press Return. (You can also press the microphone key on your keyboard and say it. **[check: which dictation to point to; Claude's own `/voice` is documented for the terminal only]**)
3. The first time, the Studio asks you five quick questions, one at a time, with buttons:
   - Which drive your shoots go on.
   - Right on that drive, or inside a folder.
   - Whether you copy shoots to a second drive too.
   - How you like a shoot folder named.
   - How you write to clients, so it can draft notes in your voice.
4. Then two questions it asks every time: how many cards for this shoot, and what's on the card. Say what's on it however you'd say it ("Smith family, beach session, Sarah's the mom, due in two weeks"), or skip.
5. Then it says:

   **You can walk away. I'll have the report ready when you're back.**

From then on, "backup now" asks only those two quick questions.

### When you come back

Your phone has tapped you, and the report is on the Mac's screen. Top to bottom: every photo backed up and checked, byte for byte, and the card is safe to format; what's on the card, one block per shoot, each with six sneak peeks picked to edit first; a note to your client, ready to copy; and a button that opens the folder your photos are in.

On each shoot:

- **Click any photo** to see it big.
- **The name box:** click in it, type a better name, press **Rename**. The folder and every photo in it are renamed to match.
- **Add to my editing queue:** click, pick a date on the calendar, Save. **Show my editing queue** opens your list of shoots to edit.
- **Copy the note** puts the client note on your clipboard, ready to paste into an email. Nothing is ever sent from the Studio.

In Lightroom, the sneak peeks are one filter away: the keyword **sneak peek**.

### Things to say to the Studio

- **show me the report** · **show my shoots** · **what's in my queue**
- **the first one is the Garcia family** (names a shoot)
- **I'm done with the beach shoot** (starts the reel and carousel)
- **backup now** (always)

---

## If something goes wrong

- **The backup stopped.** The report says why, first thing, in plain words. Fix that (plug the drive in, clear space) and say **backup now** again. It picks up where it left off; nothing is copied twice.
- **No phone tap came.** See "Good to know about the taps" in Step 6.
- **Claude keeps asking permission.** Step 5 wasn't done, or the mode slipped back to Manual. Check the row under the message box.
- **"This card is already safe."** The Studio recognized a card it has backed up before. Nothing to do.

---

## Windows

The Studio launches for Mac and PC together. The Windows guide is written separately once the PC version is tested. **[to do]**

---

## For the video

Record Part 1 start to finish on a Mac that has never had Claude on it, in one take, no cuts, so every pause and prompt is real. Then Part 2 with a real card. Twenty minutes is the target.
