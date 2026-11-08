# Getting new versions to students from GitHub

For Dustin, Nov 7. Nothing has been changed in any app, account or setting. Every claim is sourced at the end.

## 1. Why GitHub didn't update anyone in November

When you add a marketplace in the Claude app (Settings, Customize, Plugins, Add marketplace), the app doesn't keep reading GitHub itself. Claude's servers make **their own copy** of hf-tools for your account, and the app downloads that copy every 10 minutes. Two things make the servers copy GitHub again:

- someone presses **Check for updates** on that marketplace, or
- **Sync automatically** is on *and* GitHub sends Claude a notice when we push.

Nobody pressed the button. For a personal marketplace, GitHub never sent a notice: people on Anthropic's bug list report that the switch shows "on" but no push notice gets set up, even with the Claude GitHub App installed (reports run up to Nov 5, with no reply from Anthropic). So your account's copy has sat at Oct 16 ever since. Having no version number in plugin.json was **not** the cause. The app tracks the commit the server last copied.

One more snag: in the desktop app, a marketplace can't be removed and added again ("already added"). So an old copy can only be fixed with Check for updates.

## 2. The route most likely to work: list The Assistant in Anthropic's plugin directory

**How it works:** you submit the hf-tools folder once. After that, Anthropic watches the branch, checks and scans each new commit, and serves it to everyone who added the plugin. "Nothing to accept." Students add it from **Plugins > Discover** with one click. They never see a repo address, a zip, or a GitHub account. The Code tab loads the new version at the next session. This is the only route Anthropic's docs promise is automatic, and it's the only one where we found nobody reporting it broken.

**Weak points, plainly:**
- **It's a public, free listing.** Anyone on a paid Claude plan could find it and add it. The repo is already public, so anyone can add it today by address, but a listing makes it findable. Whether that fits a product you sell is **your and Nicole's call**.
- **Review time isn't published.** A person reviews the first version. Later versions go live by themselves only if Anthropic turns on "auto-publish" for us. If it doesn't, each version waits for a reviewer, and Black Friday is 20 days away.
- **A LICENSE file is required.** We have none, and a missing LICENSE blocks the submission. Which license to use is your call. The docs don't say whether an "all rights reserved" license is accepted.
- **Every version gets a security scan.** The plugin runs local page servers and calls Canva, Instagram and Google Fonts with curl. The directory's policy asks that we "own or control" the addresses we connect to, so a version could be held for a reviewer. A held version blocks every later one until it's cleared.
- **Nobody here has tried it,** and we found no first-hand reports of how fast directory updates really land.

**A safety rule for any route:** have students follow a `stable` branch, not `main`. 85 commits touched the plugin in the last week. Every push to the branch they follow reaches everyone, so work in progress should stay off it.

**The cheaper route to rule in or out first:** keep the GitHub marketplace you already have and get Sync automatically working. If it works, it's simpler than the directory: no review and no public listing. Anthropic's own docs say it should work, but the bug reports and the app's code say it probably doesn't for a personal marketplace. The test below settles that in 15 minutes. It also proves the second half of the directory route (an account plugin reaching the Code tab by itself), because both routes share that half.

## 3. Test plan (about 15 to 20 minutes, your own account)

**Before you start (once, on GitHub; your call, because it gives Anthropic's app read access to hf-tools):**
1. Open **github.com/apps/claude/installations/new**.
2. Pick the **horizonfound** account.
3. Choose **Only select repositories**, pick **hf-tools**, then press **Install**.

**The test:**
1. **I push test 1.** One new file, `plugins/the-engine/update-test.txt`, saying "update test 1". Only that file goes in the commit. I'll tell you its short commit code (7 letters and numbers).
2. **claude.ai in a browser** (it's reported to work better there than in the desktop app): go to Settings > Customize (or Plugins) > Plugins, then **Manage marketplaces**.
   - If hf-tools is listed: open its **...** menu and press **Check for updates**.
   - If it isn't listed: + Add > Add marketplace > Add from a repository, type `horizonfound/hf-tools`, then install The Assistant.

   **Look for "Updated to <code>" matching test 1.** If you see "Failed" or "plugin sync failed", screenshot it and stop. That result is itself the answer: the manual button is unreliable too.
3. In the same **...** menu, turn on **Sync automatically**. If it says "Grant access", the GitHub App step didn't take.
4. **I push test 2** (the file now says "update test 2"). Wait **5 minutes** and don't press anything.
5. Press **Check for updates** once.
   - **"Already up to date."** means Sync automatically fired by itself. **The cheap route works.**
   - **"Updated to <test-2 code>"** means it didn't fire, but the manual button works.
6. **Desktop app:** click into the Claude app so its window is in front (that triggers its download). Start a **new** Code conversation in an empty folder, *not* hf-tools, because hf-tools has its own copy of the skill and would fool the test. Ask: *"Without changing anything, find the file update-test.txt inside the installed Assistant plugin and tell me what it says."*
   - "update test 2" means an account update reaches the Code tab by itself.
   - If it says "test 1" or finds nothing, wait 10 minutes, click away and back, start one more new conversation and ask again.
7. **Afterwards:** I remove the test file in one more commit. Leaving the GitHub App installed is up to you. You can remove it at github.com/settings/installations > Claude > Configure > Uninstall.

**What the results mean:**
- **Step 5 says "Already up to date" and step 6 says test 2:** use the existing marketplace with Sync automatically. Students add it once and switch Sync on. We still need to check that it works on a student's account, which isn't linked to our GitHub. Nicole's account is the next test.
- **Step 5 says "Updated to":** auto-sync is broken, as reported. Go to the directory. Step 6 still tells us whether the account-to-Code-tab half works.
- **Step 6 never shows test 2:** both account routes have a problem in the last mile. Go to the fallback.

**The directory itself can't be tested in 15 minutes.** Its proof comes after the listing is live: push a test commit and see whether it reaches your account without you pressing anything. To submit: add a LICENSE file, add a README section saying what the plugin runs and what it connects to, then submit at claude.ai/directory/manage.

## 4. Fallback if neither account route works

**F1. Claude Code's own updater on the student's computer.** This is roughly a 100-line script, a page of instructions in the skill, and a 20-minute test on your Mac first (with your OK, since it changes your Claude settings). The app's Plugins page has a separate **Code** tab for marketplaces kept on the computer. Its Check for updates fetches **straight from GitHub**, with no Claude server in between.

To make it automatic, the Assistant would ask the student once ("Want updates to arrive on their own?"), then add three things to their `~/.claude/settings.json`:
- hf-tools as a marketplace, by its https address, with auto-update on
- The Assistant turned on
- `FORCE_AUTOUPDATE_PLUGINS=1`

That last setting matters because the app deliberately starts Code sessions with plugin auto-update switched off. A copy installed this way outranks an uploaded copy of the same name.

Weak points:
- It leans on a setting the app turns off on purpose, so Anthropic could change it.
- It's undocumented for the desktop app.
- It needs git. Macs have it once Python is installed; whether a PC has it is unknown.
- It's a settings change the student has to say yes to.

**F2. Our own self-updater.** Around 500 to 800 lines plus tests on both computers. The Assistant downloads a signed release from our GitHub Releases page and switches over only after every file checks out, keeping the old copy as the way back. It works whatever Anthropic does, but it makes us responsible for shipping code safely: a signing key, plus the auto mode prompts that come with "downloading and running code". Only if F1 fails.

**Stopgap, always available:** one Check for updates per release per student, or a new zip per release. Both are the hoops you want gone, but they work today.

## 5. What to tell Nicole now

Don't wait. She keeps the uploaded zip for today's beta testing. Before she gets a newer build, I rebuild `dist/The-Assistant.zip` from current main with `tools/build_zip.sh`. She uploads it and chooses **Replace** (the Nov 5 desktop fix says older uploads should be re-uploaded that way). Once a GitHub route proves out, she switches once: add it from Discover (directory) or the marketplace, then remove the upload. Nothing is sent to her until you say so.

Suggested words: *"Keep the version you uploaded for now. I'll send one newer file to replace it this week. We're setting it up so updates come straight from GitHub after that, and you'll make one switch when it's ready."*

---

## Facts and sources

- Claude's servers keep the account's copy. The app polls every 10 min, on window focus, and downloads only when the server's `updatedAt` changes. It never calls GitHub. Source: Claude.app 4.23118.0, `app.asar` `.vite/build/index.chunk-C4tKAcde.js` (`ee=6e5`, focus handler, `r.updatedAt!==n.updatedAt`) and `index.chunk-D8rgQQPl.js` (`/plugins/list-plugins`, `/download`).
- "To pull the latest from a marketplace you added, select Check for updates." Source: https://claude.com/docs/plugins/overview
- Check for updates = `POST .../marketplaces/<id>/account-sync`. The result reads "Updated to {sha}." or "Already up to date." It is rate-limited ("You synced recently"). Source: app `ion-dist.asar` assets `c6a2a31c4-BaOiJLYb.js`, `c3bb81cd1-JoO2aIIY.js`, i18n `/2pxhGB8eZ`.
- Personal Sync automatically needs the GitHub App: "Auto-sync requires the Claude GitHub App to have access to this repository." The personal screens have no webhook setting. The org screens say: "Automatic sync previously worked through the GitHub App integration. It now requires a webhook". Source: app assets `caeab6b9d-BztD-z4V.js`, `cf400e6a4-BRgrvOfU.js`.
- App install address in the app's code: `https://github.com/apps/claude/installations/new`.
- "Nothing syncs on a schedule." Source: https://claude.com/docs/plugins/admin
- Personal auto-sync never fires, even with the App installed ("only the automatic trigger does not"). No hook is ever created ("a personal marketplace stays on manual clicks until that webhook gets created"). Pressing the button worked in about 20 s. No Anthropic reply. Sources: https://github.com/anthropics/claude-code/issues/93825, https://github.com/anthropics/claude-code/issues/95456
- The desktop app's Check for updates often fails with "plugin sync failed"; one reporter says "The same marketplace updates fine from the chat Customise screen". Source: https://github.com/anthropics/claude-code/issues/86818
- A marketplace can't be removed in the app: "There is no UI anywhere to remove a marketplace". Source: https://github.com/anthropics/claude-code/issues/91308. Re-adding is refused before any request ("This marketplace is already added."). Source: app asset `caeab6b9d-BztD-z4V.js`.
- Directory updates: "Merge to the tracked branch, and the directory picks up the commit, checks it, and publishes it." Later versions go live by themselves only under auto-publish. Source: https://claude.com/docs/plugins/submit. Users get updates: "Yes, after the version you push is published". Source: https://code.claude.com/docs/en/plugins/publish
- "Review time isn't fixed." Source: https://claude.com/docs/directory/publish
- Missing LICENSE blocks submission. Holds apply over 512 files or non-image files over 256 KiB. Source: https://claude.com/docs/plugins/pre-submission-checklist. Checked locally: no LICENSE in the repo (`ls LICENSE*`: no match); 110 tracked plugin files; only fonts exceed 256 KiB.
- Endpoints: "verify that they own or control any endpoint" (as summarized). Source: https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy
- A synced account plugin reaches Claude Code: "it downloads as a synced plugin the next time you start a session". Source: https://claude.com/docs/plugins/overview
- The app starts Code sessions with `DISABLE_AUTOUPDATER:"1"` (app `index.chunk-BBUaTQ8d.js`, function MIa; confirmed in this session's `env`). The bundled Claude Code skips plugin auto-update then unless `FORCE_AUTOUPDATE_PLUGINS` is set: "Plugin autoupdate: skipped (auto-updater disabled)". Source: `~/Library/Application Support/Claude/claude-code/2.1.317/.../claude`.
- The Code-tab marketplace's Check for updates runs `plugin marketplace update <name>` on the computer. Source: app `index.chunk-B0P0-Zco.js`.
- Auto-update can be set by `autoUpdate` on an `extraKnownMarketplaces` entry in settings. A marketplace copy outranks a synced copy of the same name ("reports the synced copy as not loaded"). Source: https://code.claude.com/docs/en/plugins/loading
- Re-upload: "Upload earlier ones again, choosing Replace if asked". Source: https://claude.com/docs/cowork/changelog (v4.23118.0, 2026-11-05)
- 85 commits touched `plugins/the-engine` since Oct 31 (`git log --since=2026-10-31 -- plugins/the-engine`). Latest main commit is d86cdaf (Nov 7).

**Still unknown:**
- whether Sync automatically fires for a *student's* account once the App is on our repo
- whether the server keeps one copy per account (the reports suggest yes)
- directory review time, and whether we'd get auto-publish
- whether the scan passes our curl calls
- whether an "all rights reserved" license is accepted
- whether `FORCE_AUTOUPDATE_PLUGINS` in settings works inside the desktop app
- whether a PC has git
- whether the Nov 9 rename of Customize to Plugins moves these buttons
