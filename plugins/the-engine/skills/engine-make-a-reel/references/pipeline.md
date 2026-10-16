# Reel pipeline (commands)

All work happens in `<session folder>/_engine/`. Never touch originals.

## 0. Check and setup

```
bash scripts/check-setup.sh      # prints OK/MISSING for ffmpeg, whisper, pycapcut, capcut draft folder, capcut version
bash scripts/setup.sh            # one-time install, several GB, 10–30 min
```

## 1. Listen (only if a clip has talking)

```
whisper "<clip>.mov" --model small --output_format srt --output_dir _engine/
```
Use `small` by default. On Apple silicon, `medium` is fine for short clips. On Intel Macs, warn that it may take several minutes per minute of footage.

## 2. Cut (silence and restarts)

```
ffmpeg -i "<clip>.mov" -af silencedetect=noise=-30dB:d=0.6 -f null - 2>&1 | grep silence_
```
Turn the output into a keep/kill list: each chunk of speech between silences, with the first few words from the transcript. Present it as a short numbered list. They answer with numbers to kill.

Apply the cuts by trimming inside the draft (pyCapCut segment source ranges), not by re-encoding, so every cut stays editable in CapCut.

## 3. Plan

Write the plan per `reel-plan.md`. Wait for approval.

## 4. Build the draft

Use pyCapCut (`pip install pycapcut`). Rough shape of the script you write and run:

```python
import pycapcut as cc
draft = cc.DraftFolder(DRAFT_ROOT).create_draft(NAME, 1080, 1920)
draft.add_track(cc.TrackType.video).add_track(cc.TrackType.text).add_track(cc.TrackType.audio)
t = 0
for beat in plan.beats:
    seg = cc.VideoSegment(cc.VideoMaterial(beat.file), cc.trange(t, beat.dur), source_timerange=cc.trange(beat.src_in, beat.dur))
    draft.add_segment(seg)
    t += beat.dur
# hook + captions as TextSegments, styled from the Brand File (font, color, position)
# music as AudioSegment with fade in/out if provided
draft.save()
```
Photos become video segments with a 3–5 second duration and a gentle scale keyframe (1.0 to 1.06) so they don't sit still.

Draft root:
- Mac: `~/Movies/CapCut/User Data/Projects/com.lveditor.draft/`
- Windows: read from CapCut settings → Draft location.

CapCut must be closed when the draft is written, or it may not pick it up. Tell them to close it first, then open it after.

## 5. Hands-off export (no CapCut)

If they want a finished video instead of a draft, build it with ffmpeg: concat trimmed segments, burn captions from the SRT with their font, overlay the hook text, mix music, output 1080x1920 H.264. This path is a fallback and loses editability; say so.

## Gotchas to remember

- Fonts in CapCut must be installed on the computer or be CapCut built-ins. Default looks use CapCut built-in free fonts only.
- HEIC photos: convert to JPG first with `sips -s format jpeg` (Mac) or ffmpeg.
- Vertical video only. Horizontal clips get a 9:16 crop centered on faces; say which crop you chose.
- If the CapCut version is newer than the library's validated list, warn before building and still try.
