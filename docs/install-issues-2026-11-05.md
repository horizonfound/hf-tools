# What went wrong when Nicole installed the Assistant (Nov 5, 2026)

Nicole was the first person to install the Assistant on a Mac that isn't Dustin's. She hit eight roadblocks
in about forty minutes, and a ninth surprise once she was in. Every one is written down here: what she saw, why, what fixed it, and what now
stops it from happening to the next person. She got through: at 8:31pm she typed hi and the Assistant
answered with its home page beside the chat.

The short version: **seven of the eight were our mistakes, and five of those were mistakes in the guide
Claude wrote from documentation without ever seeing the real screens.** The project already held the
right route (the October guide and the README). The lesson is at the bottom.

| # | What Nicole saw | Whose fault | Fixed |
|---|---|---|---|
| 1 | Pasting the install line opened Settings and installed nothing | The guide | Yes |
| 2 | "This marketplace is already added" | Her Claude still held October's copy | Worked around |
| 3 | "Find it in that list": there was no list | Claude's Slack message | Yes |
| 4 | Discover offered "The Engine", not "The Assistant" | Claude never went back to GitHub after Oct 16 | Worked around; cause found, fix not yet tried |
| 5 | Upload refused: "description... must be at most 1024 characters" | The plugin | Yes, and now checked automatically |
| 6 | A grey line, "The archive must contain...", looked like an error | Claude's screen; the guide didn't warn | Yes |
| 7 | "Couldn't access Documents" when she typed hi | The guide | Yes |
| 8 | A pop-up asking to import her browser's cookies | Claude's own browser; the guide didn't warn | Yes |
| 9 | Instagram's "Sign up / Log in" box over her grid | Instagram; the Assistant didn't warn | Yes |

---

## 1. The install line did nothing

**What she saw:** the PDF's Step 3 said to paste `/plugin marketplace add https://github.com/horizonfound/hf-tools`
into the message box. It installed nothing. It opened Settings on Customize, Plugins.

**Why:** that line is for Claude Code in a terminal. In the Claude desktop app, plugins are added from
Settings. Claude wrote the step from the Claude Code documentation and marked it "not clicked through yet,"
then shipped it anyway when Dustin asked for a PDF.

**Fix:** the guide's Step 3 is now the Settings route, as seen on her screen.

**Prevention:** the guide may only contain steps that have been seen on a real screen (see "The rule" below).

## 2. "This marketplace is already added"

**What she saw:** in Add marketplace she typed `horizonfound/hf-tools` and got a red line: "This marketplace
is already added."

**Why:** her Claude account added hf-tools in October, for the Engine. Removing the Engine plugin did not
remove the marketplace behind it.

**Fix that night:** skip the marketplace; upload the Assistant as a file (issue 5).

**Still open:** see issue 4.

## 3. "Find it in that list and click Sync"

**What she saw:** Claude's Slack message told her that if hf-tools was already added she should "find it in
that list and click Sync." She replied: "dont know what list its talking about."

**Why:** Claude had not seen that screen and described one it imagined.

**Prevention:** never describe a screen that hasn't been seen. Ask for a screenshot first, then answer.

## 4. Discover offered "The Engine"

**What she saw:** under Discover, one entry: "The Engine, by hf-tools... Your brand. Your voice. Just fa..."
That is the plugin as it was on October 16.

**Why (found by the investigation, Nov 5, 9pm):** Claude's servers copied hf-tools from GitHub once, on
October 16 at 2:03pm, and have not gone back since. Nothing was ever telling them to.
- **"Sync automatically" has nothing behind it.** It waits for GitHub to announce each change, and no such
  announcement is set up on our GitHub project. Claude's own help says "Nothing syncs on a schedule."
  Proof: a change pushed four minutes after that last sync, with the switch already on, never arrived.
  Neither did any of the hundreds since.
- **The Claude app's own check every 20 minutes can't help.** It only downloads what Claude's servers
  already hold. It never asks them to look at GitHub again.
- **Adding the marketplace again can't help either.** "This marketplace is already added" is the app
  turning you away before it contacts anything.
- **It was not the too-long description.** That fault (and three smaller header faults) sat in the plugin
  from October 24 until tonight, and would likely have blocked a refresh if anyone had tried one. But 54
  good versions from the week before it never arrived either, so it is not why the copy froze.

Checked by: Claude's own saved record of the marketplace on Dustin's Mac (last sync started Oct 16,
succeeded, no errors, nothing since), the app's logs, the app's own code, and GitHub. Five investigators,
then a skeptic tried to knock down each finding; all five held. Nicole's account could not be looked at.

**The fix that should work, not yet tried:** a button called **Check for updates**. In Settings, Customize,
Plugins: **+ Add**, **Manage marketplaces**, the **...** on the hf-tools row, **Check for updates**. Best
done at claude.ai in a web browser; other people report it failing from the Code tab's screen. A real
refresh answers "Updated to" and a short code. These labels were read out of the app's code; nobody has
clicked them yet.

**Fix that night:** upload the Assistant as a file.

**What this means for students:** "updates happen on their own" is not true today, and CLAUDE.md said it
was. Until automatic sync is made to work (it needs the Claude GitHub App given access to our GitHub
project, and other people report even that not working), every update means each photographer pressing
Check for updates, or being sent a new file.

## 5. The upload was refused

**What she saw:** on Upload a plugin, a red box: "Plugin failed validation with 1 error. Skill
'skills/studio-manager': field 'description' in SKILL.md must be at most 1024 characters."

**Why:** the Assistant's description of itself (the paragraph Claude reads to decide when to use it) was
1,026 characters. It had grown one phrase at a time over two weeks and nobody had ever counted.

**Fix:** shortened to 931. A second file, The-Assistant-plugin-2.zip, passed.

**Prevention, three layers:**
- `tools/check_plugin.py` checks every rule we know (this limit first) and says in plain words what is wrong.
- `tools/build_zip.sh` is now the only way the upload file gets made, and it refuses to make one that fails.
- GitHub runs the same check on every push that touches the plugin, so a session working elsewhere is told
  within a minute.

## 6. A grey line that looked like an error

**What she saw:** with the good file chosen, a grey line under it: "The archive must contain a
.claude-plugin/plugin.json manifest, or a top-level SKILL.md that declares the plugin's components." She
stopped and asked.

**Why:** it is a standing note on Claude's screen. It shows whether the file is good or bad. The real signal
is the Preview underneath: when it shows "the-engine" and the Assistant's description, the file was read.

**Fix:** the guide now says so, next to the step.

## 7. "Couldn't access Documents"

**What she saw:** she typed hi and got "Couldn't access Documents. macOS often blocks access only briefly...
allow access in System Settings, or use a folder outside Documents." In System Settings, Claude only had
switches for Desktop and Downloads, both already on.

**Why:** the guide told her to make the Assistant's folder inside Documents. The Mac guards Documents,
Desktop and Downloads, and had not given Claude Documents. Dustin's project folder is not in any of those,
so it never came up in testing.

**Fix:** the folder goes in the home folder (Command + Shift + H in the file window). She worked that out
herself before the reply reached her.

**Prevention:** the guide's Step 2 says home folder, and says why not Documents.

## 8. "Stay signed in to your sites"

**What she saw:** the moment the home page opened, a pop-up from Claude: "Import cookies from your browser."
She asked: "do i do these things?"

**Why:** Claude's built-in browser offers this the first time it opens. The Assistant's pages are on her own
Mac and need no sign-in.

**Fix:** the guide says Cancel, and Don't show again.

## 9. Instagram's sign-up box (after install, the first thing she tried)

**What she saw:** she said "read my Instagram grid," gave her handle, and the page beside the chat opened
her profile with a box over it: "See photos, videos and more from nicolelhill_ ... Sign up / Log in." She
wrote "tried to log me in," then "it did that but now its loaded my grid."

**Why:** Instagram shows that box to anyone who isn't signed in. The grid behind it can still be read, and
it was. But nothing told her that, so it looked like the Assistant wanted her password.

**Fix:** the Assistant now says, before it opens the page, that Instagram may show a sign-up box and that
she doesn't need to log in.

---

## Things she did not hit, but the next person might

- **A window from Apple asking to install "command line developer tools."** Only on a Mac that has never had
  them. In the guide; never seen for real.
- **"Claude would like to access files on a removable volume."** Expected the first time the Assistant reads
  a memory card or a photo drive. In the guide; not yet seen.
- **An old "The Engine" still installed.** Dustin removed hers by hand first. The guide now starts with that.
- **Where the file comes from.** That night it was passed over Slack, and Dustin had to ask how to get it out
  of Claude. Students need one place to download it. **Dustin and Nicole's call** (the course, or a link).

## What the guide still says that nobody has seen (from the four-reader review, Nov 5)

Four independent readers went through the rebuilt guide: one cold, as a photographer; one against Nicole's
real screenshots; one against this log; one checking every claim. Their corrections are in the guide now.
What is left cannot be fixed by rewording. Each needs someone to look at a real screen:

- **Step 1, installing Claude itself.** Both Macs already had it.
- **Step 2's clicks:** what the folder choice says before a folder is picked, the "Open folder…" line, and
  whether Claude's file window has a New Folder button.
- **Step 3:** the + Add menu opened (its exact lines), what to click under Plugin file, what the screen does
  after Upload, and how to remove an old "The Engine."
- **Step 4:** the list behind the word next to the model name. Nicole's already said Auto.
- **Step 5:** Apple's developer-tools window (likely the normal case on a photographer's Mac), and whether
  hi works in a chat that was open before the file was uploaded.
- **The Mac's question** about reading a memory card or drive.
- **Safari may unzip the file by itself** when it is downloaded, leaving a folder and no file to upload.
  Try the real download link in Safari before the guide goes out.
- **How long it takes.** The guide no longer claims a time.

**The cheapest way to clear most of these:** one walk-through on a Mac, or a new user account on a Mac,
that has never had Claude, taking a screenshot at every step.

**For Dustin and Nicole to decide (marked in yellow in the guide):** where the file is downloaded from, the
address for "send us a screenshot," whether to print how to get a Pro plan and its price, and what the
guide promises about updates.

## The rule this leaves behind

**A setup step goes in the guide only after it has been seen working on a real screen, and the guide says
which screen.** Documentation for a different product (Claude Code in a terminal) is not evidence about the
Claude desktop app. Before writing any install step, read what the project already knows: the October guide
had the right route, with screenshots, and the README had it in one line.

---

## After the install

What Nicole noticed once she was in and using it, and everything that needs a conversation, is kept in one
organized page: `docs/nicole-feedback-2026-11-05.md`.
