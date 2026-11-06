# The look

Goal: two fonts that exist in both CapCut and Canva, five colors from their photos shown as swatches, one rule for where text sits, and "barely any text" as the default. Shown, never described. About eight minutes.

The old version of this part (mood words, rounds of font pairs mocked up on photos, three signature looks at the end) is gone. It was the slow, uncertain part, and the first tester did not like any of the results. Do not bring it back.

## What the look is for

Every other tool reads the Look section of the Brand File for one job: putting a line of text on a reel frame or a carousel cover, in the same fonts, in the same spot, every time. That is all. Most posts have no text at all. So the look is a headline font, a small-text font, where text sits, and colors that sit nicely against their photos. Nothing more.

The Assistant never designs a look from nothing. No improvised layouts, no inventing a brand. It matches what they have, or it picks from the library.

## Three ways in

1. **A library look.** Start from one of the looks below, on their own photo, and make it theirs. The default when they have nothing.
2. **Their existing branding.** Build from what they already have: website, screenshots, font names, a logo. The default when they have something.
3. **A Canva template they use.** They send a screenshot or the share link and the font names (click any text in Canva and the font name shows in the toolbar at the top). The Assistant reads the fonts and colors off it and builds around them.

## The procedure

### If they already have a brand identity (yes, or sort of)

1. Look at what they sent. Two lines: the fonts you see (name them if you can, otherwise your closest guess, and say it is a guess), the colors, the feel.
2. Name the two fonts: a headline font and a small-text font. If they only have one, pair it with a quiet small-text font from the list below.
3. Check both fonts exist in CapCut and Canva (the check is below). If one does not, find the closest free one that does and show the two side by side as text samples in an artifact: their font on top, the swap underneath, the same words in both. They pick. Say: "Instagram doesn't use your website fonts. This is the closest one that lives in both apps."
4. Their colors as swatches (artifact). If their brand colors are all neutrals, add one or two pulled from their photos.
5. Text placement: suggest the one their branding already uses. Ask.
6. Sample posts on their photos (below). Confirm. Record.

### If they do not (no)

1. Five photos. Two lines on what you see. Ask if it matches how they see their own work.
2. Five colors from the photos as swatches (artifact): the lightest one, the darkest one, and three that carry the mood. Plain names ("cream," "espresso," "ocean"). Say it in their direction: in a lot of cases colors don't matter much, this is photography focused, these are so text and backgrounds sit nicely with the photos.
3. The library on their photo (artifact): one tile per look, the same photo, the same short line from their spoken story, the look's name under each. They pick one, or none. "None" means: ask what they do like (a font they have seen, an account whose text they like, a Canva template they own) and go from there with the font list below.
4. Text placement: the look's default, changed if they want.
5. Sample posts. Confirm. Record.

## The library (starter version)

Built only from the fonts that ship with the Assistant, so the sample posts render in the real fonts and every look is a safe pick. Nicole's style pack replaces this list when it lands. Until then, these six:

| Look | Headline font | Small-text font | Text sits | Feels like |
|---|---|---|---|---|
| Quiet Campaign | Cormorant Garamond Light | Montserrat Regular, small spaced caps | upper third, centered, one short line | calm and expensive, like a lookbook |
| Clean and Simple | Inter Bold | Inter Regular | bottom left, small | tidy, modern, no fuss |
| Warm Modern | Fraunces Regular | DM Sans Regular | a quiet corner, small | friendly, a little editorial |
| Editorial Caps | DM Sans SemiBold, spaced caps | Cormorant Garamond Light Italic | upper third, or along the bottom edge | magazine, graphic |
| Soft Classic | Cormorant Garamond Regular | DM Sans Regular | centered, lower third | gentle, timeless |
| Bold and Loud | Montserrat SemiBold, caps, big | Inter Regular | centered, upper third | loud, confident, seniors and sports |

The text color is whichever of their five swatches reads best on their photos, usually the lightest one. Never pure white or pure black unless it is in their swatches.

## Fonts that live in both CapCut and Canva

**Bundled by the plugin at `../../shared/fonts`:** Montserrat (Regular, SemiBold), DM Sans (Regular, SemiBold), Inter (Regular, Bold), Cormorant Garamond (Light, Light Italic, Regular), Fraunces (Regular, Italic). These are free fonts, the sample posts render in them, and the files are there so they can be installed on the computer if CapCut does not already list one. These are the safe picks.

**Other free fonts usually in both apps' lists** (confirm before recording; both apps change their lists): Playfair Display, Lora, Libre Baskerville, EB Garamond, Poppins, Raleway, Lato, Open Sans, Josefin Sans, Oswald, Bebas Neue, Anton.

**Check, don't assume.** A font is confirmed only when it has been seen in both apps on their computer, or they tell you they saw it:
- Canva: open any design, click a text box, click the font name at the top left of the toolbar, type the font name in the search. If it shows up, it is there. Canva's free plan cannot add fonts, so a font missing in Canva means a swap.
- CapCut desktop: open any project, Text, Add text, open the font list, search the name. CapCut also lists fonts installed on the computer. If a bundled font is missing, hand them the file from `../../shared/fonts` (copy it to their Desktop if you can reach their files), have them double-click it and click Install Font, then restart CapCut and check again.
- If you cannot check on their computer, ask them to do the two checks (one minute) and tell you. Record what they saw.

Record "both confirmed in CapCut and Canva: yes" only when both checks passed. Otherwise record "not yet" with which app and which font, so the reel tool knows to check again before it builds anything.

**A font you cannot identify** from a screenshot: pick the closest from the lists above, say "closest I can tell," and let them confirm or type the real name (their website builder's settings show it).

## Showing things (artifacts, never words)

**Swatches.** A small HTML artifact: five squares in a row, each filled with the color, the plain name under each. No hex on screen. If a swatch is wrong, change that one and show it again.

**Library tiles.** One HTML artifact: one of their photos repeated as 4:5 tiles, one per look, the same short line from their spoken story set in that look's fonts and placement, the look's name under each tile.

**Sample posts.** One HTML artifact with two or three posts at real proportions, scaled to fit side by side:
- a carousel cover (4:5) with one line in their voice, in the headline font, in their placement
- a reel frame (9:16) with a hook in their placement (this is the first second of a reel)
- a single photo post (4:5) with no text, labeled "most of your posts"
A one-word label under each. Their photos as the backgrounds.

**Fonts in an artifact.** All the library fonts are on Google Fonts, so a `<link>` to fonts.googleapis.com by name works. If the fonts do not load (ask: "do you see the thin serif in the headline?"), embed the file from `../../shared/fonts` as a base64 `@font-face` instead.

**Their photos in an artifact.** An artifact cannot reach a photo that was dropped into the chat. The photo has to be inside the page. If the Assistant can read their files (a folder they have given it), make a small copy of each photo (long side about 1080 px, JPEG; on a Mac, `sips -Z 1080 in.jpg --out small.jpg`), base64 it, and put it in as a data URI. Keep the page under 16 MB; three photos at this size are well under. If the Assistant cannot read their files, say so in one line, build the posts on a soft block in their lightest swatch color with the text where it would sit, and offer to redo them on real photos the first time they make a reel or a carousel (those tools work from their photo folders). Never pretend a placeholder is their photo.

After each artifact: one question, then wait. Change one thing at a time. They are in the driver's seat: "I don't like any of these" is a useful answer, and "what do you like?" is the next question.

## Recording the look in the Brand File

Fill the Look section of `brand-file-template.md` with:
- Existing brand identity: yes / sort of / no, what they have, and what they sent.
- Way in: matched their branding, library look "[name]," or their Canva template.
- Headline font, with weight. Small-text font, with weight.
- Both confirmed in CapCut and Canva: yes, or not yet (which app, which font). If a swap was made: their font, the swap, and why, in one line.
- Colors: five, each as a plain name plus hex, the lightest and darkest marked. Hex is for the tools; they saw swatches.
- Text placement rule: where text sits when there is any, the text color, and what a second line looks like if there is one.
- Text amount: barely any, unless they asked for more. Text on a photo only for carousel covers, reel hooks, and announcements like minis.
- Their photos look like: the two lines you said to them, as they confirmed them.
- Sample posts they approved: what was shown and what they changed.

If they marked the look as "not sure yet," write that down too. The look is the version to beat, not a contract. "Update my look" changes it any time.
