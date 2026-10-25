# The reel, new shape: test on the Mac

Built Oct 25, now on main. A folder of edited photos goes in, a CapCut project comes out: Claude's picks in Claude's order, hard cuts on the beat of the song, the song starting where it picks up, optional plain text on the first photo. No ffmpeg, nothing installed.

## What's in it

- `skills/assistant-make-a-reel/scripts/beats_lite.py`: finds the beat with nothing installed. The Mac's own `afconvert` turns the song into samples; six-band onset envelope, autocorrelation tempo, Ellis's beat tracker, all plain Python. About 1 to 2 seconds for a 2-minute song. On click tracks with known beats it lands within 2 ms of every kick (librosa, for comparison, landed on the off-beat hats). On seven real songs (librosa's example tracks: waltz, ragtime, orchestra, folk, Tchaikovsky, electronic, drum and bass) its tempo was within 3% of librosa's on six; the seventh is a syncopated track where librosa's own two methods disagree. Beat for beat (within 70 ms) it matched on four of the seven.
- `scripts/capcut.py`: writes the project. Built from pieces CapCut 9.6 wrote itself (`references/capcut/`, with device ids and paths blanked), borrows the CapCut version from their newest project, fills wide photos to the tall frame, never overwrites a folder, adds the project to CapCut's list after keeping a copy of the list (`root_meta_info.before-studio.json` the first time, `root_meta_info.studio-backup.json` every time). Stops with exit 8 if CapCut is open.
- `scripts/reel.py`: `sheet` (numbered contact sheet of the edited photos, into `~/.studio/reels/<shoot>/`), `songs` (song files on the Mac, newest first), `make` (beat, plan, project).
- The skill (`SKILL.md`) is rewritten for this shape; the ffmpeg version is parked. The Studio Manager's "I'm done with X" now offers the reel.

## Already done from the cloud session (Oct 25, about midnight)

A test project, **"Studio test reel"**, was written straight into Dustin's CapCut projects folder: the nine Kira photos plus one wide beach photo (from the backup's previews, as photo 4), the test song, the hook "Studio test: hard cuts on the beat". Beats were found in the cloud with ffmpeg, so `afconvert` has not run yet. CapCut was open at the time and added the project to its own list within two seconds of the files landing (it rewrote `root_meta_info.json` with our entry in it), so it recognizes the project; whether it opens and plays is Dustin's look.

**Dustin opened it (Oct 25, 1:50am): listed, opens, plays, every cut on the beat, the text layer on top.** Still to answer: photo 4, and an export. **The original questions:** is it listed, does it open, do the cuts land on the beat, and how does photo 4 look (should fill the screen, cropped at the sides; if it is hugely zoomed or small with black bars, the fill scale is wrong). Does the text show? Does it export?

## For the Code session on the Mac

Paste into Claude Code: **"Get the latest from GitHub, then run the test in docs/reel-capcut-test.md."** (The older wording, "get the reel-capcut branch", works too.)

1. `git pull` on main (or `git checkout reel-capcut`; both hold the same reel).
2. `python3 plugins/the-engine/skills/assistant-make-a-reel/scripts/capcut.py where` → should find the projects folder, CapCut 9.6.0, and say whether CapCut is open.
3. `python3 .../beats_lite.py "/Users/dustindamron/Horizon Found Dropbox/The Engine/_test/session/song.m4a"` → should say about 99 beats a minute, 23 beats, "(afconvert)". This proves the Mac reads the song with nothing installed.
4. `python3 .../reel.py sheet --folder "/Users/dustindamron/Horizon Found Dropbox/The Engine/_test/session" --shoot "Kira test"` → open the sheet it prints (sips path, no Pillow).
5. Quit CapCut. `python3 .../reel.py make --folder "<same>" --shoot "Kira test" --picks 9,8,7,1,2,3,5,6 --song "<same>/song.m4a" --pace build --hook "Second test"` → "Kira test reel" in CapCut.
6. Open CapCut, play both test projects, export one. Report what Dustin sees.
7. **For the next step (song from CapCut's library):** ask Dustin to make a new CapCut project, add any song from CapCut's own music, and quit CapCut. Then copy that project's `draft_info.json` to `docs/capcut-samples/library-song.json` (it holds no personal data; check for paths under /Users and blank them) and commit it, so the cloud session can see how CapCut stores a library song.
8. Nothing here writes outside `~/.studio/reels/` and CapCut's projects folder. The test projects can be deleted in CapCut like any project.

## Ran on the Mac (Oct 25, about 2:40am, Claude Code)

- **`capcut.py where`:** projects folder found, CapCut 9.6.0, 5 projects, open/closed read correctly.
- **`beats_lite.py` on the test song:** 13.7 s, about 99 beats a minute, 23 beats, "(afconvert)", in 0.1 s. Matches.
- **`reel.py sheet`:** 9 tall photos, sheet made through sips in 0.4 s.
- **`reel.py make`:** with CapCut open it planned, then stopped with exit 8 and wrote nothing (CapCut's list unchanged by hash). The brief's `--rhythm` is now `--pace` (fixed above). After Dustin quit CapCut: "Kira test reel" written, 8 photos, 9.6 s, beats per photo 2,2,2,2,2,1,1,4, song from 2.93 s, every cut within 8 ms of a beat, at the top of CapCut's list, all photo and song paths present, list backed up first.
- **Photo 4 (Dustin's screenshot):** the wide 1000x666 preview fills the 1080x1920 frame, cropped at the sides, no bars, no extra zoom. Scale 2.669 is right, so CapCut's scale 1.0 is "fit". It looks soft only because the test used a 1000-pixel preview.
- **Dustin (Oct 25, about 2:45am): the Kira test reel plays on the beat, and the export worked.** Every question in this brief is now answered. (It was written before the slower build start landed, so it shows the old build pace.)

### How CapCut stores a library song (sample: `docs/capcut-samples/library-song.json`)

Dustin made a project ("1025 (1)") with a song from CapCut's library ("Woman's Glow", category "Funny", 194.5 s). The song is a material of `"type": "music"` with `music_id`, `category_id`, `request_id` and a `path` into **CapCut's own cache: `~/Movies/CapCut/User Data/Cache/music/<hash>.mp3`**. The project also points at a `<hash>.beat` file there: CapCut's own beat list, JSON `{"time": [ms, ...]}`. `downLoadcfg` in that folder lists what was downloaded.

- **The cached ".mp3" is really M4A (AAC).** afconvert goes by the file name and refused it ("Couldn't open input file"). Fixed in `beats_lite.py`: it now reads the first bytes, and when the name is wrong it hands afconvert a link with the right name in a temporary folder (the song is never touched). All seven songs in Dustin's CapCut cache now read with afconvert; the test song and an mp3 still work.
- **Our beats match CapCut's own.** On "Woman's Glow": ours 139.7 beats a minute, 454 beats; CapCut's .beat file 451 beats. Every one of CapCut's beats has one of ours within 70 ms; 426 within 30 ms; median 9 ms.
- **What this opens up:** the photographer can pick a song in CapCut's library, and the Studio can find it in the cache (newest `.mp3` there, or the `path` of the music material in their newest project), find its beats (ours, or CapCut's .beat as a check), and cut on them. Copyright: library songs are licensed for use inside CapCut; whether a project we write may reference one is for the next step to check.

## Untested

CapCut versions other than 9.6; Windows (projects folder `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`, file `draft_content.json`; the song needs ffmpeg or a .wav there); HEIC photos (sips handles them on a Mac); songs from CapCut's library inside a project we write (stored and readable, see above; not yet written by us).

## CapCut library songs and the license (Oct 25)

CapCut's Materials License Agreement (capcut.com/clause/material-license-agreement): standard Sounds only for "personal entertainment and non-commercial purposes" and not to promote a brand or business; Commercial Sounds are for businesses but only on CapCut, TikTok and TikTok for Business, and use anywhere else needs the rights holders' permission; library materials may be edited "only on the Platform." A photographer's business reel on Instagram fits neither. The reading and beat-matching work, but writing projects with library songs is on hold until Dustin and Nicole decide (skip it, or personal and TikTok use only, with a plain warning). Not legal advice; their call.
