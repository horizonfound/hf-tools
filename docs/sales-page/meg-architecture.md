# How Meg's sales page is built (The Reels Editing Engine, archived Oct 17 2026)

Studied for its ARCHITECTURE and the KINDS of moving parts only. Rule 9: study, never bootleg. None of her words,
pictures, names, fonts (Instrument Serif italic accent + Inter + a mono label face), colours (cream + brick red) or
layouts-as-drawn are to be reused. Ours is our own look and our own words. What transfers is the skeleton and the
idea of each interactive module.

Size: about 21,800 px tall, 3,400 words, 21 sections, 43 short looping videos, 65 small line drawings, 38 CSS
animations, scroll-triggered reveals, a countdown, a drag slider, tabs, toggles, a drifting row of phrases.
Price shown: $97 once (or 2 payments), "every update free", doors open for three days at a time, then a waitlist.

## Section order (the skeleton)
0. Thin top bar: a live countdown ("doors reopen in DD:HH:MM:SS") + one button.
1. HERO. Small label above; a 3-line headline where one phrase is struck through and replaced by a coloured word
   ("in hours" struck, "automatically"); two sentences; ONE button + a quiet "see how it works" link; a "Powered by
   Claude + CapCut" line with small logos. Right side: a phone-shaped frame playing a real result, with a small
   floating proof card overlapping its corner (three real numbers).
2. TICKER: one line of text sliding sideways forever on a coloured band ("from your camera roll to a finished reel").
3. "ONE INPUT, THREE OUTPUTS" DEMO: a framed window styled like the Claude app; inside, three phone frames
   (reel, carousel, stories) that animate in sequence as if being made; two "+ Make a ..." buttons and a REPLAY
   button; a hand-written aside under it; button.
4. BEFORE / AFTER TOGGLE: one phone frame, two pills (RAW CLIP / FINISHED REEL); tapping swaps what the frame
   shows. Headline: "Do not take my word for it. Watch ...".
5. THE LONG GUIDED DEMO (tallest section): "your style, your footage, minus the hours"; a sequence of sub-blocks
   each with a looping screen clip and a short caption: how done you want it, "thinking but what if...", why a
   free prompt can't do this.
6. "THIS IS FOR YOU": pains said in the reader's words ("sound familiar?"), two columns, then who it is for.
7. A language block (her course is in two languages) with a toggle.
8. "YOU JUST TELL IT WHAT YOU WANT": no menus, no settings. Two rows of quoted phrases in pill shapes drifting
   sideways in opposite directions: the real things a buyer would say to it.
9. FORMAT TABS: four tabs, one marked "works best", one marked "early access". Each tab swaps a phone frame and
   a short paragraph. Honest about which format is strongest.
10. STYLE PACKS: three named looks as cards + "build your own".
11. A DRAG SLIDER: "hands off, or hands on. Your call." Dragging the handle between two ends highlights one of
    two cards (finished file vs editable project).
12. "OPEN IT IN CAPCUT": the perk of an editable project, with a drawn timeline.
13. VALUE TABLE: left, "use one piece and it's paid for"; right, a receipt-like table listing each thing with
    what it would cost elsewhere, a total, then "you pay" in the accent colour, and a hand-written aside.
    Footnote with where the comparison prices come from.
14. GALLERY WALL: a grid of 26 short result videos. One line of text.
15. PRAISE WALL: real messages from buyers as cards, names removed and says why.
16. "OH, AND IT ALSO DOES ALL OF THIS": three groups, each a one-word promise on the left (Effortless. Beautiful.
    Yours.) and four small icon + two-line items on the right.
17. FOUNDER STORY: "I built it for myself first." photo, short first-person story.
18. PRICE / URGENCY: "every update free, yours forever", last round at this price.
19. OBJECTIONS AS FAQ: each question is written in quotes as the buyer's own doubt ("I'm not techy." "Is the
    price worth it?" "Will this work on my computer?"), open/close, with a plain honest answer. Headline:
    "Here's the honest answer."
20. Footer.

## What makes it feel alive (the mechanics, all plain CSS + a little script)
- Things rise and fade in as they scroll into view (IntersectionObserver adds a class once).
- A struck-through word in the headline, drawn with an animated line.
- Loops that run forever without interaction: the ticker, the drifting phrase rows, small floating cards,
  a pulsing dot on "live" labels.
- A self-playing "watch it being made" sequence with a Replay button (timed steps: dots, ticks, bars filling).
- Small controls that change one picture: pills (before/after), tabs (formats), a drag handle (two choices).
- Hand-written asides in a script face, with a drawn arrow, as the founder's voice in the margin.
- Every section opens with a tiny upper-case label, then a big headline with ONE coloured phrase.
- The same single button repeated every two or three sections. Never two competing buttons.
- Honest small print right where a claim is made (which format works best, where comparison prices come from).
