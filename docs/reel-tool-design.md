# The Assistant · Reel tool design (0.3.1, Oct 21)

Status: built, running on Dustin's Mac with nothing installed. *Oct 21 evening: Nicole's call is hard cuts, no photo motion, no effects. The motion code stays in `make_reel.py` behind `--motion`, to be off by default. Everything else below carries over.*

## How it works, in plain words

The Claude workspace on the student's computer already has ffmpeg (video), Python, numpy and Pillow (pictures). The
reel tool is a set of small Python scripts that use those and nothing else. No Homebrew, no Terminal, no 10 GB, no
"set up the reel tool" lesson. The Assistant plans the reel with the student in chat, runs the script, grades the
result, and hands back an MP4 (and trial-reel versions), and can also write an editable CapCut draft. Nothing posts.

## What made the first one look like a slideshow, and what was fixed

Dustin watched the first one (0.3.0) and said: static in the sound, ugly text, jittery zoom. It proved the pipeline ran; the grader only checked the beat. The three things were real defects, each with a cause, each fixed and measured:

| What he saw | The cause | What it does now | Measured |
|---|---|---|---|
| Static in the sound | The clip's own sound was cut off mid-wave (a click), the song's volume ramped in 50 steps a second (zipper), and the audio was compressed three times over. | One audio pass from a WAV master: the song ducked under the voice with a smooth curve updated every millisecond, the voice high-passed, gently compressed, level-matched and faded, a limiter on the sum, encoded once at the end. | Old: a click at 2.93 s. New: no clicks, no clipping, peak −1.3 dBFS. |
| Ugly text | Thin Cormorant Light at 72 px, a smudgy blurred shadow, dropped across her face, a one-word orphan line. | `hooktext.py`: balanced line breaks, Cormorant Medium Italic at 96 px (drawn at 2x and downsampled), the quietest band of the frame that isn't a face or hands, cream or ink picked from what's behind, a soft gradient only on bright backgrounds, fade in with a small rise, fade out before the cut. Three looks: editorial (serif), clean (sans), label (Instagram's native pill). | Old: contrast 2.2:1. New: 6:1 to 10:1. |
| Jittery zoom | ffmpeg's zoompan filter rounds the crop to whole pixels every frame. | Every frame drawn in Pillow with a sub-pixel affine transform and piped to ffmpeg. (Now off by default per Nicole.) | Old: 0.7 px/frame wobble. New: 0.08. |

Also in 0.3.1: the song starts where it picks up (the loudest stretch that fits the reel, nudged toward an energy jump, on a beat), the dead air before the person starts talking is trimmed, and a "build" rhythm speeds the photos up toward the end and settles on the last one.

## The pipeline, one reel

1. Contact sheet so the Assistant can see every photo and refer to them by number.
2. Song: a file in the folder (works today), the CapCut music folder (untested), or none (even pace).
3. Beat grid from the song (onsets → tempo → phase-locked grid) and the best start point (`beats.py`).
4. Plan: opening clip ends on a beat; each photo holds N beats; `plan.json` saved.
5. Render: clips cut with ffmpeg; photos as stills (or drawn frame by frame when motion is on); pieces joined without re-encoding.
6. Audio master (WAV): song + voice as above.
7. Text PNGs decided from the actual frame they sit on.
8. One final encode: text overlaid with fades, sound added. Trial reels re-use the same base.
9. Grade (`grade_reel.py`): cuts within two frames of the song's beat grid, opening held, no clicks or clipping, motion smoothness under 0.25 px/frame, text contrast 3:1 or better. FAIL says why. Taste is not graded.

## The CapCut draft (proven Oct 21 on Mac, CapCut 9.6.0)

CapCut has no official way in, but every project is a folder of plain files. On Mac: `~/Movies/CapCut/User Data/Projects/com.lveditor.draft/<project>/draft_info.json` (Windows: `draft_content.json`), `draft_meta_info.json`, and the registry `root_meta_info.json` (`all_draft_store` entries with draft_id, draft_name, draft_fold_path, draft_json_file). Times are in microseconds. A draft written by script (copy of an app-created project, retimed, photo swapped, text added, registered in the root file) appears in CapCut, opens, and exports. CapCut must be closed while the draft is written (`.locked` marks an open project). No mouse needed in the product: the student opens CapCut and exports. Test script: `_test/capcut/capcut_fill.py` in Dropbox. Untested: Windows, Intel Mac, newer CapCut versions.

## Speed

Dustin's Mac (Apple silicon, 4 cores in the workspace): 15 s for a 14-second reel, about 10 s per trial reel.
A two-core machine takes three to four times that. The setup check measures it and says so.

## Untested, honestly

A real session with real photos; a clip of someone actually talking (the ducking has not been heard); iPhone HEIC;
Windows; Intel Mac; the CapCut music folder; Canva folders.

## Next, when the Studio plan reaches it

- Switch motion off by default, confirm hard cuts still grade PASS.
- The DM-testimonial format (a screenshot layered over fast photo cuts).
- Song preview before picking.
- Word-by-word captions on a talking clip need speech-to-text; nothing on the machine does it today.
