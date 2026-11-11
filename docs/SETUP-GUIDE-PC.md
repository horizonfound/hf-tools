# Setting up The Assistant on a Windows PC

**Draft 2, Nov 7, 2026. Still nothing in this guide has been tried on a PC.** Draft 1 (Nov 6) was a script for the first PC walk-through. Draft 2 is the same script, now with a PDF beside it: **`docs/The Assistant - Setup Guide for PC.pdf`**, built by `docs/install-guide/build-pc.sh` from `docs/install-guide/install-guide-pc.html`, in the same look as the Mac PDF. Part 1 and Part 2 below are the PDF's words, line for line, with the marks the PDF leaves out. Steps the official sources confirm (Anthropic's Claude Code and Claude help pages, python.org, Microsoft's help, read Nov 7) no longer carry a mark; each is listed with its link in "What the official sources say" at the bottom.

Two kinds of marks, in this file only (the PDF has none, apart from the placeholders):

- **[check on a PC]**: written from the Mac's screens, from documentation, or from the scripts' Windows code, and not yet seen on a PC.
- **[Dustin and Nicole to decide]**: yours, with the most likely answer written in for now.

The rule from the Mac's first install (`docs/install-issues-2026-11-05.md`) holds: a step goes in the guide a student gets only after someone has seen it on a real screen. **So the PC PDF is for the first PC walk-through, not to send yet.** Its cover says it is the first Windows edition; its drawings are marked as drawings.

> **For Dustin, before anyone uses this**
>
> - **The PDF is ready to look at:** `docs/The Assistant - Setup Guide for PC.pdf`, 10 pages: a cover, six steps, an optional phone page, "Two good places to start", and "How a PC is different" (drive letters, what a PC can't do yet, if something isn't right). Rebuild it after any change with `sh docs/install-guide/build-pc.sh`. The Mac PDF and its page are untouched.
> - **Python is now Step 1, before Claude.** Draft 1 had Claude first. Python first means the Claude that opens in Step 2 is a fresh one and should find Python without a restart. Whether an already-open Claude needs a restart is not documented anywhere. Someone who already has Claude is told, in a box of its own above Step 1's numbered lines, to quit it first: right-click its icon by the clock and choose Quit, since on Windows the ✕ may only hide it (Claude Code GitHub issues #30267 and #15368 report that). If Python still isn't found after the reopen, the Step 6 table and the Assistant both say to restart the PC. [check on a PC: that the icon by the clock has Quit, and whether the ✕ alone quits Claude]
> - **The route is Upload plugin, the same as the Mac PDF** (the marketplace copy on Claude's servers froze on Oct 16; install-issues, item 4).
> - **What a PC student installs [Dustin and Nicole to decide].** Python, from the Microsoft Store ("Python Install Manager", free, from the Python Software Foundation; it puts in only Python's installer, and Python comes down by itself the first time it runs). And **Pillow**, the free add-on that makes the previews on a PC: the Assistant asks and adds it on a yes **at their very first hi**, right after Python's first run and before it introduces itself, so the setup is finished in one sitting with the guide open (`parts/on-a-pc.md`, "The first conversation on a PC"; PDF Step 6, line 2 and the table). Said Not now, it asks again the first time a backup or posts need pictures. Songs: the reel reads MP3 and M4A with Windows' own sound reader (passed on GitHub's Windows machines, never on a photographer's PC), so nothing is installed for a song that reader can read. But when a PC can't read a song, `sound.py`'s Windows message (`_PC_WAYS`) names a second add-on, imageio-ffmpeg, with a pip command, and that line reaches the reel page's result box. The Assistant is told not to run it or offer it; whether to take that sentence out of the code, or let a PC have that add-on, is yours [Dustin and Nicole to decide]. The honest line for a sales page: "one free install from the Microsoft Store, and the Assistant adds one more piece itself".
> - **Git for Windows: not asked for [Dustin and Nicole to decide].** Anthropic's docs call it optional. Without it, Claude runs its commands in PowerShell, and the Assistant's instructions are written for either.
> - **iPhone photos (HEIC) [Dustin and Nicole to decide].** A PC needs a second add-on (pillow-heif) to read them. The PDF says: export them as JPEGs.
> - **The firewall box.** The Assistant's page servers listen on 127.0.0.1 only (`fresh.Server`), never on the network. Whether that still brings up Windows' "allow access" box is not documented by Microsoft or Anthropic. The PDF has one conditional row for it in Step 6 ("Leave Private networks ticked and click Allow access. It's for the Assistant's own pages, which run on this PC only."). If the walk-through never shows the box, take the row out. [check on a PC, with an ordinary (non-admin) account too: Microsoft says a non-admin's answer makes block rules]
> - **"Customize" is becoming "Plugins".** Claude's help says the sidebar's Customize becomes Plugins (rolling out from Oct 29, for everyone on Nov 9). Step 4 says "Customize ... (newer copies of Claude may call it Plugins)". Once Nicole's or the tester's screen shows the new name, both PDFs should be updated to it.
> - **Footage on a PC (v19, Nov 7).** A PC lists videos on the reel page, plays the usual kind (H.264: most cameras, an iPhone set to Most Compatible) and makes clip reels from moments picked with Use this moment. It takes no stills, so "Look through my footage" and the strip of stills don't work there. The PDF says so in plain words under "Not on a PC yet".
> - **A note for whoever owns `parts/on-a-pc.md`** (from the Python research, Nov 7; done in the in-app instructions since, `parts/on-a-pc.md`): python.org says Python's automatic first-run install "should not generally be relied on" and suggests an explicit `py install default`; the source code shows the automatic install asks no questions (the PATH question comes only from the setup helper you get by clicking Open), and that it works offline from a bundled copy. And on a PC that already has an older Python, `python3 --version` installs nothing. Pillow 13 needs Python 3.11 or later, so an older Python gets an older Pillow.

---

## Before you start

You need four things:

- **A Windows PC.** Windows 10 or 11, with its updates done, and the internet on while you set up.
- **A Claude plan, Pro or higher.** The Assistant runs on your own Claude account. The free plan doesn't include the part of Claude it lives in.
- **An external hard drive.** Where your shoots are kept. If your photos live on your computer for now, it still works, and the Assistant will talk to you about it once.
- **The Assistant file.** One file called **The-Assistant.zip**, from **[PLACE: to decide]**. It lands in Downloads, maybe shown as **The-Assistant** with a zipper on its picture. Leave it as it is: don't open it or choose Extract All.

**Stuck at any point?** Send a screenshot of what you see to **[ADDRESS: to decide]**. (Windows key + Shift + S takes one.)

This is the first Windows edition, and you're among the first to use the Assistant on a PC. The pictures are drawings, so your screen will look a little different. If a word doesn't match, send us a screenshot.

**[check on a PC: how long the whole setup takes]**

---

## Part 1: The one-time setup

### Step 1: Add Python from the Store

The Assistant runs on a small free piece of software called Python. A PC doesn't come with it, so you add it once. **Do this before you open Claude, so Claude finds it right away.**

**Claude already open on this PC?** Quit it first: right-click its icon by the clock, bottom right (click the small **^** if you don't see it), and choose **Quit**. The ✕ on its window may leave it running. **[check on a PC: the icon's menu says Quit (or Exit)]**

1. Click **Start**, the Windows logo at the bottom of your screen, and type **Store**. Click **Microsoft Store**.
2. In the search box at the top of the Store, type **Python Install Manager** and press **Enter**.
3. Click the one called **Python Install Manager**, from the Python Software Foundation. Not the ones called Python with a number after it (like Python 3.13).
4. Click **Get** (it may say Install). Wait until it's finished. **Then you're done: don't click Open.** There's nothing to open. **[check on a PC: Get or Install for someone who never had it; the Store page's own code holds "Get", python.org says "Install"]**

*Drawings: Start with the Store found; the Store with Python Install Manager first and Python 3.13 and 3.12 faded below it.*

You'll know it worked when the button where Get was says **Open**. Leave it and close the Store. Python finishes setting itself up the first time the Assistant uses it. **[check on a PC: that the button says Open afterwards]**

**Clicked Open anyway?** A black window asks a few questions. Press **Enter** at each one. When it stops asking, close it with the **✕** at its top right. (Python's source code: Enter takes the default each time, No to everything but installing Python; a yes to the long-paths question would ask for admin rights and a restart, which is why we say Enter.) **[check on a PC: whether the window closes by itself]** (Not added: "if Windows asks to let it make changes, click Yes". Only a yes to the long-paths question brings that box, and Enter answers no.)

### Step 2: Install Claude on your PC

Claude is the app the Assistant lives inside. **Already have Claude on this PC and you're signed in? Open it from the Start menu and start at number 4 on this page.**

1. Open your web browser (Edge is fine) and go to **claude.ai/download**.
2. Click the download for **Windows**. When it has downloaded, open the file. If Windows asks whether to let this app make changes to your device, click **Yes**. **[check on a PC: whether this box comes up for an ordinary install, and whether SmartScreen warns first; the docs mention the box only for the MSIX package]**
3. Open **Claude** from the Start menu and **sign in** with your Claude account.
4. Look at the top left of the Claude window. There's a small box with two pictures in it: a speech bubble and **&lt;/&gt;**. Click **&lt;/&gt;**. (If you see the words Chat and Code instead, click Code.) That part of Claude is called **Code**. You won't write any code. **[check on a PC: where it sits and what it looks like on Windows; the docs say only "the Code tab at the top of the sidebar", with names showing on hover]**

*Drawing: the Windows window, with the </> picture at the top left and Windows' own –, □, ✕ at the top right.*

You'll know it worked when the top of the window says **New session** and there's a message box at the bottom with a few small choices under it. A small box in the middle about "Choose environment" or "Connect GitHub" can be ignored. You don't need GitHub. **[check on a PC: a "WSL" choice may also be offered under the message box; the Assistant needs the plain Local one, since plugins don't load in WSL]**

If Claude says your plan doesn't include this part, you need Pro or higher. If it asks you to sign in online, follow the link, then come back to the app. If the download page offers two Windows versions, take the plain one, unless your PC has an ARM chip (such as a Snapdragon): then take ARM64. Not sure? Click Start, type **About**, open **About your PC**, and look at **System type**. **[check on a PC: whether the download page picks the ARM one by itself]**

### Step 3: Make a folder for the Assistant

Claude needs a small folder to start in. This one is only for the Assistant's own use. **Your photos never go in this folder.**

1. Under the message box, click the choice with a small **folder** picture in front of it.
2. Click **Open folder…** A window opens showing your files.
3. Click in the long box at the very top of that window (the address bar). Type **%USERPROFILE%** and press **Enter**. That jumps to your **home folder**, the one with your name on it. **[check on a PC: that the folder window takes it]**
4. Click **New folder** near the top. Type **Assistant** and press **Enter**.
5. With the new **Assistant** folder selected, click **Select Folder**. **[check on a PC: the window's words, New folder and Select Folder, are Windows' usual folder window; not seen inside Claude]**

*Drawings: the folder choice under the message box; the Select Folder window at the home folder, with Downloads, OneDrive and the new Assistant folder.*

You'll know it worked when the folder choice under the message box now says **Assistant**.

**Not in Documents, Desktop, Pictures or OneDrive.** On many PCs Windows keeps the first three inside OneDrive, which copies everything to the cloud and can hold a file busy while it does. Your home folder isn't. (The file in Downloads is fine where it is.)

**The address bar won't take it?** Click **This PC** on the left, then **Local Disk (C:)**, **Users**, and the folder with your name. Carry on from number 4.

### Step 4: Add the Assistant to Claude

You add the Assistant from Claude's own **Settings**, using the file you downloaded. (Claude calls add-ons like the Assistant **plugins**.) **Nothing gets typed.** **[check on a PC, all of this step: the words are the ones seen on Nicole's Mac; Claude's help describes the Plugins page's + Add, Add marketplace and upload with no Windows note]**

**Installed "The Engine" from us before?** Message us at **[ADDRESS: to decide]** before you go on. Never had it? Carry on.

1. At the very bottom left, at the right end of the line with your name, click the small **gear**. A box called **Settings** opens. **[check on a PC]**
2. Click **Customize** in the Settings list on the left, near the bottom (on newer copies it's called **Plugins**). If you see a row of words at the top, click **Plugins** there. (Landed on Connectors? Leave its buttons alone.)
3. Click the dark **+ Add** button at the far top right, then **Upload plugin** (not Add marketplace).
4. Under **Plugin file**, click to choose a file. In the window that opens, click **Downloads** on the left, click **The-Assistant** (the one with a zipper on its picture), then **Open**. **[check on a PC: Windows hides ".zip" unless file extensions are switched on]**
5. Check two things: **no line with a red !**, and the **Preview** says **the-engine**, "The Assistant by Horizon Found…" (the-engine is its behind-the-scenes name.)
6. Click the black **Upload** button (grey means the file isn't right), then close Settings with its **X**. The real proof is Step 6.

*Drawings: Settings with Customize, Plugins and + Add marked; the Upload a plugin box with the file, the Preview and Upload marked. The same drawings as the Mac PDF.*

**A red ! that says "Plugin failed validation"?** Stop and send a screenshot to **[ADDRESS: to decide]**. That one is ours to fix. **"This marketplace is already added"?** Cancel, then + Add, Upload plugin. **"The Engine" with an Add button?** Leave it. It's an old copy.

### Step 5: Let it work while you're away

This step lets a backup finish while you're out of the room. Without it, Claude may stop and ask your permission before each thing it does.

1. Look under the message box, at the right. After the name of the Claude you're using (ours said Opus 5.5), there is one word. If it says **Auto**, you're done with this step.
2. If it says anything else, click that word. In the list that opens, click **Auto**.

You'll know it worked when that word says **Auto**. Glance at it each time you start; if it has changed, set it back.

**Is this safe?** Auto means Claude does the backup's steps without asking each time, with its own safety checks running. And the Assistant has one rule it never breaks, in any mode: **nothing on your memory card is ever deleted, moved or changed.**

**Don't see Auto in the list?** Click the name just left of that word (ours said Opus 5.5), pick the newest one in the list, then look again. Still not there? Your Claude may need its update: click the **three lines** at the top left of the Claude window, then **Help**, then **Check for Updates**. Let it restart, then look again. **[check on a PC: where the Help menu is in the Windows window; the docs give the menu path, Help > Check for Updates…, but not where the menu sits; the three lines are the drawing's guess]**

### Step 6: Say hi

That's the setup. Now meet your Assistant.

1. Click inside the message box, type **hi** and press **Enter**.
2. Give it a few minutes the first time: Python finishes setting itself up now. Grey lines show in the chat ("Ran 2 commands"): nothing to click. Then it asks to add one more free piece, called Pillow, for showing your photos: click **Yes, add it**. Then it introduces itself, and its home page opens beside the chat. **[check on a PC: how long Python's first run takes (a download of about 37 MB); that the page beside the chat opens on a PC]**
3. Claude may offer to copy your browser's sign-ins ("Stay signed in to your sites"). Click **Not now** or **Don't show again**. Clicked Import cookies by mistake? Click **Cancel** in the next box. **[check on a PC]**

*Drawing: the chat on the left, the home page on the right, the pop-up to dismiss, in a Windows window.*

**Things you might see:**

| What you see | What to do |
|---|---|
| "Your PC needs one free piece from Microsoft" | Python isn't on yet. Do Step 1, quit Claude (right-click its icon near the clock, Quit), open it again from the Start menu, say **hi**. Still says it? Restart your PC and say hi again. |
| "It's called Pillow, and I can add it now" | At your first hi. Click **Yes, add it**: about a minute, once. Said Not now? It asks again the first time you make posts or back up a card. **[check on a PC: how long, and whether Auto lets the install run without asking] [Dustin and Nicole to decide: the Assistant adds it, or the guide has them do it]** |
| A Windows Security box about Python and networks | Leave **Private networks** ticked and click **Allow access**. It's for the Assistant's own pages, which run on this PC only. **[check on a PC: whether the box comes up at all]** |
| You said hi and no page opened beside the chat | Click **+ New** (top of the left column), check the folder under the message box says **Assistant**, say hi again. Still nothing? Screenshot to **[ADDRESS: to decide]**. |

**You're set up.** Next time: open Claude from the Start menu, click **&lt;/&gt;**, click **+ New**, check the folder under the message box says **Assistant**, type **hi**.

### Optional, any time: a tap on your phone

The Assistant can tap you on your phone when a backup is done, or when it's waiting on an answer from you. Skip this page if you don't want that. You can come back to it later. **[check on a PC, all of this part: it was tested on Dustin's Mac on Oct 28; Anthropic's docs describe it with no Windows difference]**

1. **Put Claude on your phone.** Get the Claude app from the App Store or Google Play and sign in with the **same** Claude account. When the phone asks whether Claude may send notifications, say **Allow**.
2. **Link your PC to your phone.** On your PC, open Claude's **Settings** (the gear, as in Step 4), click **Code** in its list (it may say Claude Code), and turn on **Connect new sessions to Remote Control**. Close Settings, then click **+ New**.
3. **Turn on the taps.** Click in the message box, type the first line below exactly as it is and press **Enter**. Then the second line, the same way. Each one answers with a line saying it's set to true. **[check on a PC: that /config typed in the Code message box works there, as it did on the Mac]**

```
/config agentPushNotifEnabled=true
```

```
/config inputNeededNotifEnabled=true
```

What each one does: the first lets the Assistant tap you when a backup finishes. The second taps you when it's waiting on an answer from you.

**Good to know.** Your PC has to be on and awake, with Claude open. The Assistant asks the PC to stay awake during a backup, but closing a laptop's lid still puts it to sleep: leave it open, with the charger in. And if you're sitting at the PC, the tap is skipped, since you can already see it on screen.

(Draft 1 said to flip a Remote Control switch in a panel beside the chat. The PDF uses the Settings switch instead, which the docs name, and which covers every new chat, not one.)

---

## Part 2: Two good places to start

You don't need a memory card to begin. Talk to the Assistant in your own words.

### Photos you've already finished

Edited and exported, sitting in a folder.

1. On the home page, click **Make posts from a shoot**. **The first time only,** the box says **set up my Assistant folder**: click **Copy**, click in the chat's message box, press Ctrl + V, then Enter, and answer its one question about where to keep your posts. The box then changes (if not, click Make posts again). **[check on a PC: the home page reloads itself within seconds once the folder is made, as on the Mac (Oct 30); the "if not" covers a page that doesn't]**
2. Click **Select the folder with your finished photos**. A small window with a list of folders opens: click the little arrows to open **This PC** and your drive, click the folder with your exports, then **OK**. **[check on a PC: that the window opens in front of Claude; it is Windows' classic "Browse For Folder" window, from `this_computer.pick_folder`]**
3. Click **Copy** next to **make my posts**, paste it in the chat with Ctrl + V, and press Enter.

You get a carousel (or a single post) and stories sized for Instagram, and a reel page where you pick the song and the pace, then finish the reel in CapCut (you'll need the CapCut app). The Assistant works from its own copies; your originals aren't moved or changed. **Reels in CapCut are new on a PC:** if yours doesn't show up in CapCut, tell the Assistant.

What's behind that line since Nicole's v19 (Nov 7), for the walk-through: the post kit is three cards (Reel, Carousel, Stories); a carousel of one slide is a single post; the reel page has footage, photos ("Let my assistant choose" or drag), the song (a Music folder inside the shoot, or a screen recording's sound), the style and the vibe, then **Make my reel**, which writes a CapCut project; the stories designer saves 9:16 stories into the kit's Stories folder. **[check on a PC: all of it; CapCut for Windows has never opened a project the Assistant wrote]**

**Why not drag the folder in?** On a PC, dragging a folder into another folder on the same drive **moves** it rather than copying it, so the folder you dragged from ends up empty. Use the Select the folder button instead. Dragged one by mistake? Press **Ctrl + Z** in that File Explorer window right away and it comes back.

### A memory card with new photos

Straight out of the camera.

1. Put the card in and plug in your drive. If Windows pops up a note asking what to do with the card, ignore it, or pick **Take no action**. **[check on a PC: the note's words]**
2. Type **backup now** in the chat and press Enter.
3. The first time, the Assistant asks a few setup questions, one at a time, with buttons. Your drives show with their letters, like **Big Kahuna (E:)**. After that, it's one quick screen each time.
4. When it says **You can walk away**, walk away. On a laptop, leave the lid open and the charger in.

When you're back, click **Show the report** in the chat. Every photo is copied and checked, sorted into named shoots, with six sneak peeks picked to edit first.

**Rather say it than type it?** Click in the message box, press the **Windows key + H**, and talk. That's Windows' own voice typing, and it needs the internet. **[check on a PC: that it types into Claude's message box and its question boxes]**

(Not in the PDF, true on a PC as on a Mac: in Lightroom the sneak peeks are the keyword **sneak peek**; photos already in Lightroom Classic need Metadata > Read Metadata from Files.)

---

## How a PC is different

### Drive letters

Windows gives each drive and memory card a letter when it's plugged in, and a drive doesn't always get the same letter. Some days the card even gets the letter your photo drive had. So before every backup the Assistant checks that your photo drive is where it should be, and that the card isn't. **If the letters have moved, it tells you and asks before it copies anything.** **[check on a PC: the letters on a second day, with the card put in before the drive]**

*Drawing: File Explorer's This PC with Local Disk (C:), Big Kahuna (E:) and EOS_DIGITAL (F:), the card.*

### Not on a PC yet

- **Looking through your videos for moments.** The reel page lists your videos and plays the usual kind (most cameras, or an iPhone set to Most Compatible), and you can pick a moment yourself with **Use this moment**. The Assistant can't pick moments for you yet.
- **iPhone videos in High Efficiency.** They can't play on the reel page on a PC yet. For your next shoot, set the iPhone to Most Compatible (Settings, Camera, Formats).
- **iPhone photos (HEIC).** Export them as JPEGs first, and the Assistant can use those. **[Dustin and Nicole to decide]**
- **Posting-day reminders don't reach your calendar by themselves.** The Assistant makes a calendar file with your caption in it, and you add it to your calendar yourself, and again after any change. Check that it has an alert. **[New Nov 11: not in the PDF yet; wording is Dustin and Nicole's]**

> **Not in the PDF: what is new on a PC and untried. Be straight with the PC tester about this box.**
>
> - **Nothing in this guide has been tried on a PC.** The first PC walk-through is the test of every step.
> - **CapCut for Windows.** Nobody has seen it open a project the Assistant made; some versions may lock their project files. A reel made while CapCut is open waits, and is added when CapCut is closed and **Open CapCut** is pressed on the reel page.
> - **Songs.** MP3 and M4A are read with Windows' own sound reader: right to 0.1 ms on GitHub's Windows machines, never on a photographer's PC. A WAV works anywhere. The sound from a screen recording may not work on a PC yet.
> - **RAW from Nikon, Sony, Fuji, Olympus, Panasonic and Pentax.** The previews are written for them but never tried on a real file (Canon CR2 and CR3 and a DJI DNG have been, on a Mac set up to work the way a PC does).
> - **Older shoots after a drive's letter changes.** Their Open photo folder buttons may not find their folders until the drive is back on its old letter.
> - **Untried on a PC:** the phone taps, voice typing into Claude, the pages beside the chat staying up while you're away, keeping the PC awake through a long backup, the folder window coming up in front of Claude, the designer and the stories designer, reading the Instagram grid and Canva (both use Windows' own curl).

### If something isn't right

- **The page beside the chat is blank, or shows a play button.** Don't press the play button. Type **show the Assistant** and the page comes back.
- **A folder button seemed to do nothing.** The File Explorer window may be behind Claude. Click **File Explorer** on the taskbar at the bottom of your screen.
- **"Windows wouldn't let me move the folder."** A program has a photo in it open. Close Lightroom and any File Explorer window on that shoot, say **go**. Nothing is lost.
- **Claude keeps stopping to ask permission.** Step 5 slipped back. Say yes to the one on screen, then set the word under the message box back to **Auto**.
- **A backup stopped.** The Assistant says why, first thing. Fix that (plug the drive in, clear space) and say **backup now** again. Nothing is copied twice.
- **You're not sure what to do next.** Say **hi**. It tells you where things stand and what you can say. We'll tell you when there's an update, and send the steps with it.

**Three promises:** nothing on your memory card is ever changed. Nothing is ever deleted. Nothing is ever posted or sent for you.

---

## What the official sources say (read Nov 7, 2026)

The research behind Draft 2. Anthropic's pages were saved as read (scratch, not in the repo); re-read a page before quoting it anywhere. "Stated" means the page says it; "inferred" means it follows but isn't written.

**The Claude app on Windows**

- Windows 10 or later. Stated: [Install Claude Desktop](https://support.claude.com/en/articles/10065433-install-claude-desktop) ("Windows: Windows 10 or higher"). Claude Code itself lists Windows 10 1809 or later, 4 GB of memory, x64 or ARM64 ([setup](https://code.claude.com/docs/en/setup)).
- Install: download, open the file, launch Claude from the Start menu, sign in. Stated: [Install Claude Desktop](https://support.claude.com/en/articles/10065433-install-claude-desktop). A separate ARM64 installer exists ([desktop quickstart](https://code.claude.com/docs/en/desktop-quickstart)).
- A Windows permission box (UAC) while installing, and no admin needed except for Cowork. Stated for the packaged (MSIX) install: [Deploy Claude Desktop for Windows](https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows). Whether the ordinary download shows it: not stated.
- The Code tab includes Claude Code; nothing else to install; it needs Pro, Max, Ultra, Team or Enterprise. Stated: [desktop quickstart](https://code.claude.com/docs/en/desktop-quickstart). The Code tab is "at the top of the sidebar"; names show on hover. Where it sits on Windows: not stated.
- Folder: the environment control (pick the Local one), then the folder control, Open folder…. Stated: [desktop quickstart](https://code.claude.com/docs/en/desktop-quickstart). Plugins don't load in WSL sessions ([desktop](https://code.claude.com/docs/en/desktop)).
- Git for Windows is optional; without it Claude Code uses PowerShell, and PowerShell profiles are not loaded. Stated for Claude Code ([setup](https://code.claude.com/docs/en/setup), [tools reference](https://code.claude.com/docs/en/tools-reference)); that the desktop app's own copy does the same is inferred. The safety sandbox does not run on plain Windows.
- The desktop app doesn't read PowerShell profiles; a changed PATH needs Claude quit and reopened. Stated: [desktop](https://code.claude.com/docs/en/desktop). That a Python installed while Claude is open needs the same is inferred; hence Python first.
- Auto in the mode selector "appears when auto mode is available", with a supported model (Opus 4.6 or later, Sonnet 4.6 or later, Haiku 5.5, or a Fable model). Stated: [desktop](https://code.claude.com/docs/en/desktop). On native Windows, Auto becomes the *starting* mode from Claude Code v2.1.233; before that the default is Manual. That version number is about the default, not about whether Auto is offered. Stated: [permission modes](https://code.claude.com/docs/en/permission-modes). A mode is remembered per folder.
- Ctrl for Cmd; Ctrl+/ shows shortcuts; Ctrl+Shift+B opens the browser pane; "Show in Explorer". Stated: [desktop](https://code.claude.com/docs/en/desktop).
- Updates: Help > Check for Updates… on Windows; the app updates itself on launch and about every four hours. Stated: [desktop](https://code.claude.com/docs/en/desktop), [Deploy Claude Desktop for Windows](https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows).
- Remote Control: `/remote-control` in the message box, or Settings > Code (or Claude Code) > Connect new sessions to Remote Control. The push switches `agentPushNotifEnabled` and `inputNeededNotifEnabled` are off by default and work only while Remote Control is connected; pushes are skipped while you're at the session. Stated: [remote control](https://code.claude.com/docs/en/remote-control), [settings reference](https://code.claude.com/docs/en/settings-reference). No Windows difference stated.
- Plugins: the sidebar's Customize becomes Plugins (from Oct 29, for everyone Nov 9); Add > Add marketplace > Add from a repository is described; uploading a plugin file is one sentence with no steps. Stated: [one Plugins page](https://support.claude.com/en/articles/17740565-manage-plugins-skills-and-connectors-from-one-plugins-page), [Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude). The 200 MB, valid .zip limit is stated for organization uploads only ([Manage plugins for your organization](https://support.claude.com/en/articles/13837433-manage-plugins-for-your-organization)).
- Voice: Claude's own `/voice` is for the terminal, not the desktop Code tab ([voice dictation](https://code.claude.com/docs/en/voice-dictation)). Windows' voice typing is Windows key + H, in a text box, and needs the internet ([Microsoft Support](https://support.microsoft.com/en-us/windows/use-voice-typing-to-talk-instead-of-type-on-your-pc-fec94565-c4bd-329d-e59a-af033fa5689f)).
- Firewall: Windows asks to allow or block the first time a program with no rule listens; a non-admin's answer makes block rules ([Microsoft Learn, firewall rules](https://learn.microsoft.com/windows/security/operating-system-security/network-security/windows-firewall/rules)). Nothing official says whether a program listening on 127.0.0.1 only gets the box.
- Git: Claude Desktop on Windows before version 1.49585.0 asked for Git before any local session; the fix is to update the app ([desktop](https://code.claude.com/docs/en/desktop)). Not in the PDF until the walk-through shows whether today's download ever asks.
- Troubleshooting from Anthropic: "another installation in progress" means run the installer as Administrator; sign-in or 403 errors, sign out and in; crash logs in Event Viewer ([desktop](https://code.claude.com/docs/en/desktop)).

**Python on Windows**

- The Python Install Manager is the official route, from the Microsoft Store, "recommended for most users"; Store ID 9NQ7512CXL7T; the old full installer is deprecated. Stated: [python.org, Using Python on Windows](https://docs.python.org/3/using/windows.html), [Python install manager 26.4](https://www.python.org/downloads/release/pymanager-264/).
- The Store listing is "Python Install Manager", Python Software Foundation, free, needs Windows 10 version 19044 or later. A Store search for "python" also lists Python 3.12 and Python 3.13 from the same publisher. Stated: [Microsoft Store listing](https://apps.microsoft.com/detail/9NQ7512CXL7T), [Store search](https://apps.microsoft.com/search?query=python).
- The Store app puts in the manager only; with no Python yet, the first `python`, `py` or `python3` installs the newest one by itself (about 37 MB), for that user only, no admin. Stated: [python.org](https://docs.python.org/3/using/windows.html). That this automatic install asks no questions is read from the source code ([install_command.py](https://github.com/python/pymanager/blob/main/src/manage/install_command.py)); the PATH and four other questions come only from the setup helper you get by clicking Open ([firstrun.py](https://github.com/python/pymanager/blob/main/src/manage/firstrun.py)). With no internet it installs a bundled Python 3.15.0.
- A work PC can have automatic installs switched off by policy (from the manager's settings file).
- pip comes with it; `python -m pip install pillow` needs no admin. Pillow 13 (Oct 16, 2026) has ready-made Windows files for Python 3.15 on x64 and ARM64, so no compiler is needed. Stated: [Pillow installation](https://pillow.readthedocs.io/en/stable/installation/basic-installation.html), [Pillow on PyPI](https://pypi.org/project/pillow/).

**Still unknown, for the walk-through:** where the regular installer puts Claude and whether SmartScreen warns; where the Code tab, the gear and the Help menu sit on Windows; whether Settings says Customize or Plugins on the tester's copy; Upload plugin on Windows; how long Python's first run takes and whether an already-open Claude sees it; whether the Store button says Get or Install; whether the firewall box comes up for a server on 127.0.0.1; whether Auto lets the Pillow install run without asking; whether /config works in the message box on Windows; whether the ✕ quits Claude or leaves it running near the clock, and whether the icon by the clock has Quit; whether Claude asks for Git.

---

## For the first PC walk-through (Dustin)

Do it on a PC that has never had Claude or Python on it, ideally the PC student's own, with the PDF open beside it and a screenshot at every step. Parallels on a Mac with an Apple chip runs the ARM kind of Windows, which most PCs aren't; it's fine for most of this list but weaker for CapCut and the add-ons (`docs/pc-readiness-2026-11-06.md`, "What needs a real PC"). Try one run on an ordinary (non-admin) Windows account if you can.

What to look at, in order:

1. **Step 1:** the Store's listing (Get or Install, the button saying Open afterwards, which numbered Pythons sit beside it); what happens on Open, if you try it on a second PC; whether Claude's ✕ quits it, and what the icon by the clock offers (Quit or Exit).
2. **Step 2:** the Windows box while installing (and SmartScreen); where the Code part is and what the window looks like (this replaces the drawing); whether a WSL choice shows under the message box; **whether Claude asks you to install Git** before a session starts (if it does, add a row to the PDF: "You don't need Git. Update Claude: three lines at the top left, Help, Check for Updates").
3. **Step 3:** the folder window's words, whether %USERPROFILE% works in its address bar, and how OneDrive shows up.
4. **Step 4:** every click (the gear, Customize or Plugins, + Add, Upload plugin, the file window with .zip hidden) and the Preview.
5. **Step 5:** Auto in the list; the app's version (Help > About Claude); where the Help menu is (the PDF says the three lines at the top left).
6. **Step 6:** hi; how long Python's first run takes; the home page beside the chat; the cookie pop-up; whether a firewall box comes up; the Pillow question (right after Python, before the introduction), how long it takes and whether it runs in Auto without asking.
7. **The phone:** the Settings switch, the two /config lines, a real tap with the tester away from the PC.
8. **Part 2, posts:** a real export folder (the folder window from the home page and whether it comes up in front, a post kit built, the reel page with a song from the Music folder and Make my reel, the carousel and stories designers with real photos, one reel opened in CapCut for Windows (if it doesn't open, one CapCut project folder zipped and sent to us), a Canva carousel brought into a kit, reading the Instagram grid).
9. **Part 2, a card:** a real card (the drive letter, the letters on a second day with the card put in before the drive, Windows' note when a card goes in, the setup questions, a full backup, the report, Show the report after an hour away).
10. **Footage:** an H.264 video and an iPhone HEVC video on the reel page, Use this moment, a clip reel.
11. How long each step took, and the whole setup.

After the walk-through: replace the drawings that turned out wrong (or swap them for the tester's screenshots), take the marks out of this file, update both PDFs if Settings now says Plugins, and only then send the PDF to a student.
