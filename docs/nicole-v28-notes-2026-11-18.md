# Notes for Nicole on v28 (draft, not sent)

Nov 18, 2026. Your v28 is built into the Assistant on a branch called `v28`. It is not in the version you can install yet. Everything a photographer sees is meant to be yours: your words, your order, your timings. This note is only what is different, what is missing, and what nobody has tried.

**The honest state first:** it was built fast, with tests but with no second pair of eyes on any part, and nobody has watched any of it with their own eyes yet. Not Dustin, not you. It ran on pretend shoots in a hidden browser on Dustin's Mac. Nothing has run on a PC.

## What is built

- The home page: the hello framed on faces, "Another hello", your four steps in your exact words with their "right now" boxes, the monthly recap card with its two hide choices, and the Your year bar in its dates.
- Your year and the monthly recap as stories, with Save this one to share and Save all of them.
- The backup report: numbers count up while photos fall into the files box, and Play it again.
- Posted lifts the post into the grid, and `?try=posted`.
- The editing queue: cards deal in, Delivered flips the card, and `?try=delivered`.
- The post kit's photo fan, once per kit, `?fan=1` to replay.

## Different from yours, and why

**Underneath (a photographer never sees these)**
- **Finding faces.** No Swift tool. The Assistant asks the Mac's own Vision directly, so there is nothing to build or ship. It looks at the small copies of the photos, never the originals. A dozen photos take well under a second on Dustin's Mac.
- **Hiding the recap** is remembered by the Assistant, not the browser, as you asked for the real thing.
- **Saving a story.** The page sends the picture itself; the Assistant checks it really is a 1080x1920 picture and names the file itself. Same folder, Stories to share, never over a picture that is there.
- **The two previews can't save anything by accident.** In yours, a click during `?try=posted` could really un-post a post, and `?try=delivered` threw away real presses for about 7 seconds. Ours can't.
- **No animation can get stuck.** Each has a time limit, since a page that is not in front can leave one unfinished.

**Things a photographer could notice**
- **No serif.** Your italic accent words (the home page, the stories, "Delivered.") are in the plain font, in coral. That is Dustin's Nov 7 call for every page. On the story pictures one switch brings your italic back. The big numbers are a little lighter than yours (our font stops at semi-bold).
- **Step 4's "About N days of posts."** Yours multiplied the ready posts by the rhythm, so 3 posts at 3.5 a week said about 10 days. Ours says 6. With no rhythm set it says "No posting rhythm set yet".
- **"Every one checked"** under the last backup shows only when that backup really was all checked. A sample backup and one with a problem say so instead. A video clip is never called a photo.
- **Carousels and sets of stories** are counted once per design that slides were saved from. Yours counted design files by the date they were last touched, which changes when a file is edited again or copied.
- **A story with nothing in it is skipped,** so there can be fewer than nine. One of a thing is singular ("1 reel made").
- **A year counts only that year.**
- **The hours saved** story: your line, plus "It is an estimate." in the side note.
- **The backup report's animation** plays by itself only when the report is freshly opened, not each time the report reloads itself after a rename or a note. It never plays on a sample backup, or inside a shoot page that holds several cards.
- **The post kit's fan** is marked "seen" only when it really played. A kit with 1 or 2 photos still plays a small one. No photo shows twice.
- **The editing queue's deal** stops adding delay after the 8th card, so a long queue is all there in about a second and a half. The confetti starts from the green check.
- **Reduced motion:** nothing animates anywhere, the hello's photos don't change, and the row doesn't slide on Posted either.
- **Left out:** your test-only lines and links.
- **A few lines of ours where you had none:** "No posting rhythm set yet", "About 1 day of posts", "Open the folder", "Getting your photos ready…", "It is an estimate.", "That didn't work. Try again in a moment.", and the lines for when there is no Assistant folder to save into. All drafts for you to reword.

## Not built

- The samples page.
- The card-into-folders animation for the live backup (yours isn't built either).
- Face finding on a PC. There the hello's photos are centered.
- Canva carousels are not counted as carousels in the recap.

## Not tried

- Anyone's own eyes on any of it, in the Claude app.
- Real shoots, real photos, real backups. Years of kits (how long the home page takes to open).
- Faces on real client photos: groups, children, whether heads sit where you want them.
- A PC.
- The Your year bar in a real December.

## Questions for you

1. **Reels count every make,** as yours does: one reel made three times is "3 reels made", and the hours saved go up with it. Is that the number you want people sharing, or each reel once?
2. **"You shared N shoots with the world"** counts shoots something was made from, not posted. Is that the claim you want on a picture people share?
3. **Serif or no serif on the story pictures?** They are the one place it may be worth it.
4. **"Katie's reel"** comes from the first word of "Katie Austin Maternity". The same rule gives "Sunrise's reel" for "Sunrise palm grove". Keep, or only when it is clearly a person?
5. **"See your year" in the hello** opens the year's stories any day, while the bar is December only. Is that what you meant?
6. **When the next post in line is marked Posted** (the usual case, and always in the preview), its tile hops and lands in the same square, as in your screenshot 09. It only travels when a post further back is posted. Keep, or should the preview pick one that travels?
7. **Should the report's animation replay every time the report reloads itself?** Ours doesn't.
8. **With reduced motion on, should the green Delivered side still show, without movement?** Yours and ours show nothing.
9. **With no Brand Homebase the hello has no name** ("Welcome back."). Should it use a name from elsewhere?
10. **May a photographer ask for a recap in the chat** ("show my November recap")? We added that; say if it should only live on the home page.
