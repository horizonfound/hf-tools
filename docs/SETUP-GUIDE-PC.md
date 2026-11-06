# Setting up The Assistant on a Windows PC

**Draft 1, Nov 6, 2026. Nothing in this guide has been tried on a PC.** It is the PC edition of the Mac guide (the PDF built from `docs/install-guide/`, walked through on Nicole's Mac on Nov 5), with the two things a PC needs that a Mac doesn't. Lines marked **[check on a PC]** are written from the Mac's screens or from the documentation and have not been seen on a PC. Lines marked **[Dustin and Nicole to decide]** are yours, with the most likely answer written in for now.

The rule from the Mac's first install (`docs/install-issues-2026-11-05.md`) holds here too: a step goes in the guide a student gets only after someone has seen it on a real screen. So this is the script for the first PC walk-through, not a guide to send yet.

> **For Dustin, before anyone uses this**
>
> - **The route is Upload plugin, the same as the Mac PDF.** The brief for this draft said Add marketplace, Add from a repository. The PDF moved off that route on Nov 5, because the marketplace copy on Claude's servers froze on Oct 16 and never refreshed (install-issues, item 4). Upload plugin is the one seen working.
> - **What a PC student installs [Dustin and Nicole to decide].** A Mac needs nothing (or Apple's one window). A PC needs at least two things: Python, from the Microsoft Store (the "Python Install Manager"; `winget install 9NQ7512CXL7T` is the same thing for someone at ease with a command line), and **Pillow**, the free add-on that makes the previews. This draft has the Assistant offer Pillow and add it itself on a yes, the first time it needs it. Songs may need a third: the reel is being taught to use Windows' own sound reader (`sound.py`, never run on a PC); if that fails, the fallback is ffmpeg, for example inside the `imageio-ffmpeg` add-on. "Nothing to install" is not true on a PC; "one free install from the Microsoft Store, and the Assistant adds one more piece itself" is the honest line if the Pillow route holds.
> - **Git for Windows: not asked for here [Dustin and Nicole to decide].** Anthropic's docs call it optional and recommend it, so Claude can use its Mac-like command line; without it Claude uses PowerShell. The instructions were written to work in either. The docs do not say which one the desktop app uses.
> - **iPhone photos (HEIC) [Dustin and Nicole to decide].** A PC needs a second add-on to read them. This draft says to export them as JPEGs.
> - **Drive letters.** Windows can hand the photo drive's letter to the memory card another day. Since late Nov 6 the Studio File keeps the drive's name and its own number beside the letter, and the backup stops before writing anything when that letter holds a different drive (written, never run on a PC). Older records (the backups, the queue, the report) still keep folders by letter only.
> - **One thing to know:** Claude Code has an extra safety wall it can run commands inside (the sandbox). Anthropic's docs say it runs on Mac, Linux and WSL2, and that on plain Windows commands run without it. The Assistant's own rules (never touch the card, never overwrite, never delete) are in its scripts and hold either way.
> - **What Anthropic's docs say about the Claude app on Windows** (checked Nov 6, `docs/pc-readiness-2026-11-06.md`, section K): the Code part of the app is on Windows, for ordinary PCs and the newer ARM ones; Auto mode is on Windows from a certain app version on; the browser pane exists there; the plugin screens and Remote Control have no Windows note at all. Everything else in this guide about the Windows app is a guess from the Mac's screens.

---

## Before you start

You need five things:

- **A Windows PC.** The Claude app runs on ordinary PCs and on the newer ARM ones. **[check on a PC: the oldest Windows the app supports]**
- **A Claude plan, Pro or higher.** The Assistant runs on your own Claude account. The free plan doesn't include the part of Claude it lives in.
- **An external hard drive for your shoots.** If your photos live on your computer for now, it still works, and the Assistant will talk to you about it once.
- **The Assistant file.** One file called **The-Assistant.zip**. Download it from **[PLACE: to decide]**. It lands in your Downloads folder. Leave it as it is: don't open it and don't choose Extract All.
- **About half an hour, once.** A little longer than on a Mac, because a PC needs one free piece from Microsoft first. **[check on a PC: how long it really takes]**

---

## Part 1: The one-time setup

### Step 1: Install Claude on your PC

1. Open your web browser and go to **claude.ai/download**.
2. Click the download for **Windows**. **[check on a PC: whether the page picks the right one for an ARM PC by itself]** Open the file when it has downloaded and follow what it shows. If Windows asks whether to let it make changes, click **Yes**. **[check on a PC]**
3. Open **Claude** from the Start menu and **sign in** with your Claude account.
4. Find the **Code** part of Claude. On a Mac it is a small **&lt;/&gt;** picture at the top left of the window. **[check on a PC: where it sits on a PC, and what it looks like]** You won't write any code.

You'll know it worked when there's a message box at the bottom with a few small choices under it.

If Claude says your plan doesn't include this part, you need Pro or higher.

### Step 2: Python, the one free piece from Microsoft

The Assistant runs on a small free piece of software called Python. A Mac comes with it (or offers it with one click). A PC doesn't, so you add it once.

1. Open the **Microsoft Store** (click Start and type **Store**).
2. Search for **Python Install Manager**. **[check on a PC: that this is its exact name in the Store, and that it comes from the Python Software Foundation]**
3. Click **Get** (or **Install**). When it says it's done, you're done with this step. There's nothing to open.

What you just added is Python's installer. Python itself finishes setting itself up the first time the Assistant uses it: a minute or two, and it needs the internet. The Assistant says "Getting Python ready" while it happens. **[check on a PC: how long it takes, and whether Python asks a question that first time]**

Use the Microsoft Store rather than a website: it's the simplest way, and it's the one this guide was written for.

If you skip this step, the Assistant notices the first time you say hi and tells you the same thing.

**[check on a PC: whether Claude has to be closed and opened again before it can see Python]**

### Step 3: Make a folder for the Assistant

Claude needs a small folder to start in. This one is only for the Assistant's own use. **Your photos never go in this folder.**

1. Under the message box, click the choice for the folder, then **Open folder…** A window opens showing your files. **[check on a PC: the exact words]**
2. Click in the address bar at the top of that window, type **%USERPROFILE%** and press **Enter**. That jumps to your home folder, the one with your name on it.
3. Click **New folder**, type **Assistant**, and press **Enter**.
4. With the new **Assistant** folder selected, click **Select Folder**. **[check on a PC]**

You'll know it worked when the folder choice under the message box says **Assistant**.

**Not in Documents, Desktop or Pictures.** On many PCs Windows keeps those three in OneDrive, which copies them to the cloud and can hold a file open while it does. Your home folder isn't synced. You'll come back to this same folder every time you open the Assistant. **[check on a PC: whether the window shows OneDrive this way]**

### Step 4: Add the Assistant to Claude

You add the Assistant from Claude's own **Settings**, using the file you downloaded. Nothing gets typed. **[check on a PC, all of this step: Anthropic's docs don't describe these screens for Windows; the words below are the ones seen on Nicole's Mac]**

**Installed "The Engine" from us before?** Message us at **[ADDRESS: to decide]** before you go on. Never had it? Carry on.

1. Open **Settings**. On a Mac it is the small gear at the bottom left, at the right end of the line with your name. **[check on a PC: where it is on a PC]**
2. In the Settings box, find **Customize** in its list on the left. Click it, then click **Plugins** at the top. (Landed on Connectors? Leave its buttons alone.)
3. Click the dark **+ Add** button at the top right, then **Upload plugin** (not Add marketplace).
4. Under **Plugin file**, choose **The-Assistant.zip** from your Downloads folder.
5. Check two things: **no line with a red !**, and the **Preview** says **the-engine**, "The Assistant by Horizon Found…" (the-engine is its behind-the-scenes name). The two grey notes on that screen are always there. They are not errors.
6. Click the black **Upload** button, then close Settings.

**A red ! that says "Plugin failed validation"?** Stop and send a screenshot to **[ADDRESS: to decide]**. That one is ours to fix.

### Step 5: Let it work while you're away

This step lets a backup finish while you're out of the room. Without it, Claude may stop and ask your permission before each thing it does.

1. Look under the message box, at the right. After the name of the Claude you're using, there is one word. If it says **Auto**, you're done with this step.
2. If it says anything else, click that word. In the list that opens, click **Auto**.

You'll know it worked when that word says **Auto**. Glance at it each time you start; if it has changed, set it back.

**Don't see Auto in the list?** Auto came to Windows in a newer version of the Claude app. Update the app **[check on a PC: where its update button is]**, then click the name just left of that word, pick the newest one in the list, and look again.

**Is this safe?** Auto means Claude does the backup's steps without asking each time. And the Assistant has one rule it never breaks, in any mode: **nothing on your memory card is ever deleted, moved or changed.**

### Step 6: Say hi

1. Click inside the message box, type **hi** and press **Enter**.
2. Give it up to a minute the first time. A few grey lines show in the chat: nothing to click. Then it introduces itself, and its home page opens beside the chat. **[check on a PC: that the page beside the chat opens on a PC]**
3. If you skipped Step 2, it tells you your PC needs Python first. Do Step 2, then tell it "done."
4. Claude may offer to copy your browser's sign-ins ("Stay signed in to your sites"). Click **Not now** or **Don't show again**. **[check on a PC]**

**The first time it needs to show you photos,** the Assistant says your PC needs one more free piece, called **Pillow**, and asks whether to add it. Click **Yes, add it**. It takes about a minute, and you never see it again. **[Dustin and Nicole to decide]** **[check on a PC]**

You're set up. Next time: open Claude, go to Code, start a new chat, check the folder under the message box says **Assistant**, type **hi**.

### Step 7 (optional): Claude on your phone

The Assistant can tap you on the phone when a backup is done, or when it's time to swap cards. **[check on a PC, all of this step: it was tested on Dustin's Mac on Oct 28; Anthropic's docs say nothing different for Windows, except that the computer has to stay on]**

1. **Install the Claude app on your phone** from the App Store or Google Play. Sign in with the **same** Claude account. When the phone asks whether Claude may send notifications, say **Allow**.
2. **Link your PC to your phone.** In Code, open the panel on the right side of the chat and flip **Remote Control** on. (Typing `/remote-control` in the message box does the same thing.) **[check on a PC: where the panel and the switch are]**
3. **Turn on the taps.** In the message box, paste each of these lines and press Enter after each:

```
/config agentPushNotifEnabled=true
```

```
/config inputNeededNotifEnabled=true
```

Each answers with "Set … to true". The first lets the Assistant tap you when a backup finishes; the second taps you when it's waiting on an answer.

**Good to know:** the PC has to be on and awake with Claude open. The Assistant asks the PC to stay awake during a backup, but closing a laptop's lid still puts it to sleep: leave it open, with the charger in. If you're sitting at the PC, the tap is skipped, since you can already see it on screen.

---

## Part 2: Your first posts, and your first backup

You don't need a memory card to begin. Talk to the Assistant in your own words.

### Photos you've already finished

1. On the home page, click **Make posts from a shoot**.
2. A box opens with a few words and a **Copy** button. Click Copy, click in the chat's message box, press **Ctrl + V**, then **Enter**. (The first time the words are **set up my Assistant folder**: that makes a second folder, on your photo drive, for your posts.)
3. Click **Select the folder with your finished photos** and pick your exports. If on your PC that button says to drag the folder in instead, **don't drag it.** Copy the folder's address instead: in File Explorer, click the address bar at the top of the folder's window and press **Ctrl + C**. Then in the chat type **make posts from**, press **Ctrl + V** to paste the address after it, and press **Enter**. **[check on a PC: what the button does on a PC]**
4. Type **make my posts** in the chat and press **Enter**. (Skip this if you pasted the folder's address in step 3.)

You get single posts, a carousel and stories sized for Instagram, and captions written from what you tell it. The Assistant works from its own copies; your originals aren't moved or changed.

**Why not drag?** In File Explorer, dragging a folder to another folder on the same drive moves it instead of copying it, so the folder you dragged from ends up empty. If that happens, press **Ctrl + Z** in that window right away and it comes back.

### A memory card with new photos

1. Put the card in and plug in your drive. Windows may show a box asking what to do with the card. Close it, or pick **Take no action**: the Assistant does the copying, and never from that box. **[check on a PC: the box's exact words]**
2. Type **backup now** in the chat and press **Enter**. (You can also press the **Windows key and H** and say it. Windows' voice typing needs the internet. **[check on a PC: that it types into Claude's message box]**)
3. The first time, the Assistant asks a few setup questions, one at a time, with buttons: which drive your shoots go on (each drive shows with its letter, like "Big Kahuna (E:)"), whether to put them right on it or inside a folder, whether you copy shoots to a second drive too, how you like a shoot folder named, how you write to clients, and how often you like to post. After that, it's one quick screen each time, and it names your drive with its letter ("Onto Big Kahuna (E:) like usual?").
4. When it says **You can walk away**, walk away. Leave the laptop open and plugged in.

**About drive letters.** Windows gives each drive and card a letter when it's plugged in, and a drive doesn't always get the same one. Before every backup the Assistant checks that your photo drive is still on its letter and that the card isn't. If the letters have moved, it tells you and asks before it copies anything. It never guesses.

When you're back, click **Show the report** in the chat. Every photo is copied and checked, sorted into named shoots, with six sneak peeks picked to edit first.

**In Lightroom,** the sneak peeks are one filter away: the keyword **sneak peek**. This works the same on a PC as on a Mac. Photos you had already brought into Lightroom Classic before the backup: select them, then **Metadata > Read Metadata from Files**.

---

## What doesn't work on a PC yet

> **Be straight with the PC tester about this box.**
>
> - **Nothing in this guide has been tried on a PC.** The first PC walk-through is the test of every step.
> - **Songs for a reel.** A song saved as a WAV file works on any computer. MP3 and M4A songs on a PC are being taught to use Windows' own sound reader, which has never been tried on a real PC. If the Assistant says it can't read your song, make the reel with no song and add the song in CapCut.
> - **The song from a screen recording.** May not work on a PC yet.
> - **CapCut.** Nobody has seen CapCut for Windows open a project the Assistant made. Some versions of CapCut may lock their project files. The first reel on a PC is a test. The kit page's **Open in CapCut** button may not find CapCut either: open it from the Start menu.
> - **The home page's folder button** (Select the folder with your finished photos) may not open a window on a PC yet. Paste the folder's address in the chat instead (Part 2).
> - **The pages where you move the reel's or the carousel's photos** may show no pictures on a PC yet. Say the change in the chat instead ("start with the couple").
> - **iPhone photos (HEIC).** Export them as JPEGs first. **[Dustin and Nicole to decide]**
> - **RAW files from Nikon, Sony, Fuji, Olympus, Panasonic and Pentax.** The previews are written for them but have never been tried on a real file. Canon (CR2 and CR3) and a DJI drone's DNG have been, on a Mac set up to work the way a PC does.
> - **Drive letters that change.** The Assistant remembers your photo drive by its letter, like E:. If Windows gives it a different letter another day, the Assistant checks before a backup and asks you first, but older shoots' **Open photo folder** buttons may not find their folders until the drive is back on its old letter. Unplugging the card and other drives, then plugging the photo drive back in, usually gives it its old letter. **[check on a PC]**
> - **Renaming a shoot while Lightroom has it open.** Windows can refuse to rename a folder while another program has one of its photos open. The Assistant says so; close Lightroom (and any File Explorer window showing that folder) and say **go**. Nothing is lost.
> - **Untried on a PC:** the phone taps, voice typing into Claude, the pages beside the chat staying up while you're away, and keeping the PC awake through a long backup.

---

## If something isn't right

- **The Assistant says your PC needs Python.** Do Step 2, then say **done**. If it still can't find it, close Claude, open it again, and say **hi**.
- **It asks to add Pillow.** That's the one more free piece it needs for your photos. Say yes.
- **The page beside the chat is blank, or shows a play button.** Don't press the play button. Type **show the Assistant** and the page comes back.
- **A button on the page says the Assistant isn't running.** Type **show the Assistant** in the chat.
- **Claude keeps stopping to ask permission.** Step 5 slipped back. Say yes to the one on screen, then set the word under the message box back to **Auto**.
- **A backup stopped.** The Assistant says why, first thing. Fix that (plug the drive in, clear space) and say **backup now** again. Nothing is copied twice.
- **"Windows wouldn't let me move the folder."** Another program has a photo in it open. Close Lightroom and any File Explorer window showing that shoot, then say **go**.
- **We tell you there's an update.** We'll send a new file and the steps with it.
- **You're not sure what to do next.** Say **hi**. It tells you where things stand and what you can say.

**Three promises:** nothing on your memory card is ever changed. Nothing is ever deleted. Nothing is ever posted or sent for you.

---

## For the first PC walk-through (Dustin)

Do it on a PC that has never had Claude or Python on it, ideally the PC student's own, with a screenshot at every step. Parallels on a Mac with an Apple chip runs the ARM kind of Windows, which most PCs aren't; it's fine for most of this list but weaker for CapCut and the add-ons (`docs/pc-readiness-2026-11-06.md`, "What needs a real PC").

What to look at, in order:

1. Step 1: where the Code part is in the Windows app, and what the window looks like.
2. Step 2: the Store's listing for Python Install Manager, how long Python's first run takes (it downloads Python itself), whether it asks anything then and whether it waits for an answer when Claude runs it, and whether Claude needs a restart to see it.
3. Step 3: the folder window's words, whether %USERPROFILE% works in it, and how OneDrive shows up.
4. Step 4: every click (the gear, Customize, Plugins, + Add, Upload plugin) and the Preview.
5. Step 5: Auto in the list; the app's version.
6. Step 6: hi, the home page beside the chat, the Pillow question, and whether the install runs in Auto without asking.
7. Step 7: the Remote Control switch, the two /config lines, a real tap with the tester away from the PC.
8. Part 2: a real card (the drive letter, the letters on a second day with the card put in before the drive, Windows' box when a card goes in, the setup questions, a full backup, the report, Show the report after an hour away); a real export folder for posts; one reel opened in CapCut for Windows (and, if it doesn't open, one CapCut project folder zipped and sent to us, so we can see the format).
9. How long each step took.
