# The reel, new shape: test on the Mac

Built Oct 25 on the `reel-capcut` branch. A folder of edited photos goes in, a CapCut project comes out: Claude's picks in Claude's order, hard cuts on the beat of the song, the song starting where it picks up, optional plain text on the first photo. No ffmpeg, nothing installed.

## What's in it

- `skills/assistant-make-a-reel/scripts/beats_lite.py`: finds the beat with nothing installed. The Mac's own `afconvert` turns the song into samples; six-band onset envelope, autocorrelation tempo, Ellis's beat tracker, all plain Python. About 1 to 2 seconds for a 2-minute song. On click tracks with known beats it lands within 2 ms of every kick (librosa, for comparison, landed on the off-beat hats). On seven real songs (librosa's example tracks: waltz, ragtime, orchestra, folk, Tchaikovsky, electronic, drum and bass) its tempo was within 3% of librosa's on six; the seventh is a syncopated track where librosa's own two methods disagree. Beat for beat (within 70 ms) it matched on four of the seven.
- `scripts/capcut.py`: writes the project. Built from pieces CapCut 9.6 wrote itself (`references/capcut/`, with device ids and paths blanked), borrows the CapCut version from their newest project, fills wide photos to the tall frame, never overwrites a folder, adds the project to CapCut's list after keeping a copy of the list (`root_meta_info.before-studio.json` the first time, `root_meta_info.studio-backup.json` every time). Stops with exit 8 if CapCut is open.
- `scripts/reel.py`: `sheet` (numbered contact sheet of the edited photos, into `~/.studio/reels/<shoot>/`), `songs` (song files on the Mac, newest first), `make` (beat, plan, project).
- The skill (`SKILL.md`) is rewritten for this shape; the ffmpeg version is parked. The Studio Manager's "I'm done with X" now offers the reel.

## Already done from the cloud session (Oct 25, about midnight)

A test project, **"Studio test reel"**, was written straight into Dustin's CapCut projects folder: the nine Kira photos plus one wide beach photo (from the backup's previews, as photo 4), the test song, the hook "Studio test: hard cuts on the beat". Beats were found in the cloud with ffmpeg, so `afconvert` has not run yet. CapCut was open at the time and added the project to its own list within two seconds of the files landing (it rewrote `root_meta_info.json` with our entry in it), so it recognizes the project; whether it opens and plays is Dustin's look.

**Dustin opened it (Oct 25, 1:50am): listed, opens, plays, every cut on the beat, the text layer on top.** Still to answer: photo 4, and an export. **The original questions:** is it listed, does it open, do the cuts land on the beat, and how does photo 4 look (should fill the screen, cropped at the sides; if it is hugely zoomed or small with black bars, the fill scale is wrong). Does the text show? Does it export?

## For the Code session on the Mac

Paste into Claude Code: **"Get the reel-capcut branch from GitHub, then run the test in docs/reel-capcut-test.md."**

1. `git fetch && git checkout reel-capcut`.
2. `python3 plugins/the-engine/skills/assistant-make-a-reel/scripts/capcut.py where` → should find the projects folder, CapCut 9.6.0, and say whether CapCut is open.
3. `python3 .../beats_lite.py "/Users/dustindamron/Horizon Found Dropbox/The Engine/_test/session/song.m4a"` → should say about 99 beats a minute, 23 beats, "(afconvert)". This proves the Mac reads the song with nothing installed.
4. `python3 .../reel.py sheet --folder "/Users/dustindamron/Horizon Found Dropbox/The Engine/_test/session" --shoot "Kira test"` → open the sheet it prints (sips path, no Pillow).
5. Quit CapCut. `python3 .../reel.py make --folder "<same>" --shoot "Kira test" --picks 9,8,7,1,2,3,5,6 --song "<same>/song.m4a" --rhythm build --hook "Second test"` → "Kira test reel" in CapCut.
6. Open CapCut, play both test projects, export one. Report what Dustin sees.
7. **For the next step (song from CapCut's library):** ask Dustin to make a new CapCut project, add any song from CapCut's own music, and quit CapCut. Then copy that project's `draft_info.json` to `docs/capcut-samples/library-song.json` (it holds no personal data; check for paths under /Users and blank them) and commit it, so the cloud session can see how CapCut stores a library song.
8. Nothing here writes outside `~/.studio/reels/` and CapCut's projects folder. The test projects can be deleted in CapCut like any project.

## Untested

CapCut versions other than 9.6; Windows (projects folder `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`, file `draft_content.json`; the song needs ffmpeg or a .wav there); HEIC photos (sips handles them on a Mac); songs from CapCut's library; whether CapCut's scale 1.0 is "fit" (assumed; photo 4 tells us).
