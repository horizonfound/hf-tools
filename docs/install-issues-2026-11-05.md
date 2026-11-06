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
| 4 | Discover offered "The Engine", not "The Assistant" | The October copy never refreshed | Worked around, cause being investigated |
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

**Why:** her account's copy of hf-tools has not refreshed since October 16, although the October guide said
"Leave Sync automatically on" and "updates happen on their own." Dustin's account was frozen on the same
copy. What is known: Dustin's Claude app log shows the last refresh request on Oct 16 at 2:03pm, and its
own check every 20 minutes since then found nothing new to download. **Why the refresh stopped is being
investigated; the finding goes here when it is in.**

**Fix that night:** upload the Assistant as a file.

**What this means for students:** until a refresh is seen to work, "updates happen on their own" is not a
claim we can make. Each update is a new file.

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

## The rule this leaves behind

**A setup step goes in the guide only after it has been seen working on a real screen, and the guide says
which screen.** Documentation for a different product (Claude Code in a terminal) is not evidence about the
Claude desktop app. Before writing any install step, read what the project already knows: the October guide
had the right route, with screenshots, and the README had it in one line.

---

## After the install: what Nicole noticed while using it (same evening)

These are not install roadblocks. They are a first-time user's notes, kept here so nothing she said is lost.

### A. "Yours" was hard to find

**What she said:** "there is no yours," then "yes i know yours is there but it doesnt have the assistant in
it," then "ohhh ok nevermind i see it now."

**What happened:** Settings, Customize has three tabs (Connectors, Skills, Plugins), and each has its own
Yours and Discover. She was on Connectors, so Yours listed her connectors, not the Assistant. She also found
a second way in: the filter button on Plugins has a Source list with **My Uploads** in it.

**For the guide:** say "click Plugins first, then Yours," not just "click Yours."

### B. Should making posts copy her photos? (a decision for Dustin and Nicole)

**What she said:** "it made a folder and is asking where it can locate the photos i want to use for the
post. theyre already on my hard drive in another location. it wouldnt make sense to duplicate it so would
you want it to find the folder instead? or you tell it where it is."

**What it does today:** it copies only the finished JPEGs into its own folder (Dustin's call, Oct 30: copies,
never moves, finished photos only), so a post kit sits in one place and the originals can't be touched.

**Her point:** when the photos are already on the same drive, a second copy looks like waste, and "find
them where they are" is what she expected. The Assistant already does this for a shoot it backed up itself
(it points at the export folder instead of copying), so working in place is possible.

**Not decided. Claude told her it is logged for the two of them.**

**Found afterwards:** the Assistant can already do what she asked. `kit.py start --folder "<their folder>"`
makes a kit from photos left where they are. On her run the Assistant went down the copy route (the folder
picker and the drop box) and never offered it. So the decision is which one the Assistant reaches for first,
not whether to build something.

### C. The same question asked twice

On that screen the Assistant explained the two ways to hand over photos in a paragraph, and then asked the
same thing again in a box with two buttons. One or the other is enough. Not changed yet.

### D. "1 failed"

The line above its reply said "Ran 3 commands, opened a page, 1 failed." What failed is not known; it
carried on and the folder was made. Worth a look at her session if it repeats.

### E. Making posts felt like too much at once, and the caption came too early (a decision for Dustin and Nicole)

**What she said (8:47pm):** "i feel like it should be one at a time this feels overwhelming to have it
create these for you and it makes it feel like its just gonna do it without any input... wether thats true
or not it feels like it is." And: "like showing it the photos and then it asking for the caption already i
feel like you should make the reel or carousel or story first and then you would make the caption after you
see the final piece."

**What was on her screen:** "Next I'll make your post kit: the reel, the carousel, a few single posts,
stories, and the captions to go with them. The captions come from you, and I just put them on paper. So tell
me about this shoot and what you want to say about it. Who they are, what the day was like, anything you'd
put in the caption."

**What Dustin answered her (8:48pm):** "no ... all you need to do is share stories and details about the
shoot. give a little background about what it was like."

**Two different things in there:**
- **The wording.** The Assistant said "the captions come from you" and "anything you'd put in the caption,"
  so she heard "write your caption now." Dustin's meaning is "just tell me about the shoot." The words on
  screen don't say that clearly. A reworded question is proposed to Dustin; not changed yet.
- **The order and the amount.** She would rather make one piece at a time and write the caption after seeing
  it. The kit makes everything in one go, by design (Dustin, Oct 30). **Their call; nothing changed.**
