# Culling test: does it get "bad" right? (written Oct 24, late)

A look, not a build. **Write nothing to the photos, no sidecars, no stars.** All output goes in `~/.studio/tests/culling-<date>/`.

Shoot: the Black-sand beach shoot on Big Kahuna (find it from `edit_queue.py list --all` or the saturday card's records in `/Volumes/Big Kahuna/.studio/`).

## Why this test exists

Dustin wants the Studio to filter out "generally bad photos," gently at first, and **it must work on a PC too** (Mac extras are a bonus, never the foundation). So the test compares two layers on the same shoot:

- **Layer A, works on any computer:** pure Python on small previews, nothing installed.
  1. Near-duplicate groups: a small perceptual hash (e.g. 16x16 grayscale difference hash) on each preview, grouped with capture time (frames within a few seconds and a small hash distance are one moment). Inside each group the "best" is the sharpest, best-exposed frame.
  2. Sharpness: variance of a simple edge filter on a ~512 px grayscale preview (center-weighted; faces unknown in this layer).
  3. Exposure: share of near-black and near-white pixels.
- **Layer B, Mac only, the bonus:** Apple's Vision framework, reached with nothing installed if possible (JavaScript for Automation, `osascript -l JavaScript` with `ObjC.import('Vision')`; if that fails, a small Swift script if `swift` is present; say which worked).
  1. `VNCalculateImageAestheticsScoresRequest` (macOS 15+; check `sw_vers` first): `overallScore` (-1 to 1) and `isUtility`.
  2. Faces and eyes (`VNDetectFaceLandmarksRequest`) for a rough blink check, and `VNDetectFaceCaptureQualityRequest`.

Previews: use the ones the backup already made where they exist; otherwise pull small JPEGs with `sips` (Mac). Note for later: on a PC, previews must come from the RAW's embedded JPEG read in Python, since there is no `sips`.

## What to show Dustin

1. Contact sheet: the **40 lowest** by Layer A (a simple combined score), and the **40 highest**.
2. The same two sheets by Layer B's `overallScore`.
3. How many near-duplicate groups the shoot has, and how many frames would be marked "weaker frame" if only the best of each group kept a star.
4. How long each layer took for the whole shoot.
5. One plain paragraph: where A and B agree, where they disagree, and whether B adds enough that PC users would miss it.

Dustin judges with his own eye whether "lowest 40" looks like what he would throw out. That judgment is the barometer; nothing is built until he has seen it.
