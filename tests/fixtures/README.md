# Test songs

Small songs for testing how the reel hears music (`plugins/the-engine/skills/assistant-make-a-reel/scripts/sound.py` and `beats_lite.py`) on a Mac and on a PC.

**Every sound here is synthetic.** `make_fixtures.py` builds them from sine waves and a fixed pseudo-random hiss. There is no recorded, downloaded or copyrighted audio in this folder, and none should ever be added.

## What they are

The same click track in every file: **100 beats a minute, 4 beats to a bar, 10 seconds, first beat at 0.25 s**.

- Beat 1 of each bar: a low kick plus a high click (1,600 Hz).
- Beat 3: a softer kick plus a click (1,000 Hz).
- Beats 2 and 4: a click.
- On the "and" of every beat: a short hiss.

So the right answers are known: about 99 to 100 beats a minute, 17 beats, 4 to a bar.

| File | What it is | Made with | What it tests |
|---|---|---|---|
| `click-100bpm.wav` | WAV, 16-bit, mono, 11,025 a second | Python's `wave` | The plain-Python route (no tools at all) |
| `click-100bpm.aiff` | AIFF, 16-bit big-endian, mono, 11,025 a second | Written by hand (Python 3.13 has no `aifc`) | Reading AIFF's own header and samples |
| `click-100bpm.m4a` | AAC in M4A, 48 kbit/s, mono, 44.1 kHz | The Mac's `afconvert` | Apple's gapless note (`iTunSMPB`); a mono M4A, which `afconvert` decodes into the "extensible" WAV that Python 3.9's `wave` refused |
| `click-100bpm-m4a-named.mp3` | A byte-for-byte copy of the M4A, with a `.mp3` name | `cp` | What CapCut's library songs look like: the kind is read from inside the file, never from its name |
| `click-100bpm-cbr.mp3` | MP3, constant 48 kbit/s, with an Info header | ffmpeg 9 with libmp3lame | Length from the header frame |
| `click-100bpm-vbr.mp3` | MP3, variable bit rate (`-q:a 6`), with a Xing header | ffmpeg with libmp3lame | Length from the header frame |
| `click-100bpm-cbr-noheader.mp3` | MP3, constant bit rate, no header frame (`-write_xing 0`) | ffmpeg with libmp3lame | Length from the bit rate and the file size |
| `click-100bpm-vbr-noheader.mp3` | MP3, variable bit rate, no header frame | ffmpeg with libmp3lame | Length by counting every frame |
| `click-100bpm-22k-vbr.mp3` | MP3 (MPEG-2), 22,050 a second, variable bit rate, with a Xing header | ffmpeg with libmp3lame (`-ar 22050`) | Frames of 576 samples, the same length as LAME's delay: the shape a review found Windows' trimming missed (added Nov 6) |

Each file is under 250 KB; all nine together are about 730 KB.

## The right lengths

These are the true lengths, worked out from what is inside each file, and what `sound.duration()` must give.

| File | Length |
|---|---|
| WAV, AIFF, M4A, M4A named `.mp3` | 10.000000 s |
| MP3s with a header, and the variable one without | 10.031020 s (384 frames of 1,152 samples) |
| The 22,050-a-second MP3 | 10.057143 s (385 frames of 576 samples) |
| Constant-rate MP3 without a header | 10.031 s (from its size and bit rate) |

The Mac's own `afinfo` agrees for seven of the nine. It gets two wrong, which is why `sound.py` reads lengths itself: for the M4A named `.mp3` it says 0.34 s (it goes by the name and reads the file as an MP3), and for the variable-rate MP3 without a header it says 11.7 s (it guesses from the first frames' bit rate). ffmpeg says 10.000 for the two MP3s with a header, because it also leaves out the encoder's padding at the ends. For the M4A it says 10.054, because it counts the AAC encoder's warm-up.

## Checking them

    python3 tests/fixtures/check_sound.py

Standard library only. On a Mac it tries the Mac's own route (`afconvert`) and the plain-Python route. On Windows it tries the plain-Python route and Windows' own Media Foundation, with ffmpeg switched off so Media Foundation really runs. A machine without Media Foundation says SKIP for those lines, not FAIL. Besides the beat (the beat finder works in steps of 11.6 ms), every decode's clicks are measured against the WAV's to a tenth of a millisecond (`clicks.py`) and must be within 2 ms. One known exception prints as NOTE, not PASS or FAIL: the Mac's own `afconvert` keeps LAME's 576 samples at the front of an MP3, so its clicks are 13.1 ms late (26.1 ms in the 22,050-a-second MP3: the same 576 samples at half the rate); whether to take those off on a Mac is Dustin's to decide.

    python3 tests/fixtures/decode_report.py

Information only: with both ffmpegs switched off, what this computer's own decoder (Windows' Media Foundation on a PC, `afconvert` on a Mac) makes of the seven MP3 and M4A songs: which way heard each, how many seconds came back against the true length, how loud, how long it took, how early or late its clicks are against the WAV's (to 0.1 ms), and on Windows what Media Foundation gave before `sound.py` took the encoder's warm-up off; or the plain words for why not. GitHub runs it on Windows as a step that may fail without failing the check. `tests/pc_smoke.py` also reads every song's length here and hears the WAV, AIFF, MP3 and M4A songs when the computer has a way to.

## Remaking them

    python3 tests/fixtures/make_fixtures.py

This needs a Mac (for `afconvert`) and ffmpeg with libmp3lame. The output differs slightly between encoder versions, so remake them only when a new kind of file is needed, then re-check the table above.
