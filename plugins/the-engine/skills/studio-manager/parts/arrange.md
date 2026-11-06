# Changing the photos on a page

Part of the Assistant's instructions. The first-thing checks, the rules and how you talk are in SKILL.md and apply here too. The quoted lines below are the default wording; Dustin and Nicole may change any of them.

Choosing and ordering the photos is your job and stays so. This page is how the photographer moves things after you have picked: your pick is in a row at the top, in order, with every photo of the shoot below it. They drag to reorder, drag one up to add it, drag one down (or press its X) to take it out, and click any photo to see it big. Every change is saved to the kit as they make it, so nothing is lost if the page is closed.

**The reel and the carousel each have this page** (`--piece reel`, `--piece carousel`). It is the same page with two differences. The reel's row is the order the photos play, and each photo has a Normal / Longer / Quicker bar; the carousel's row is the order people swipe, with no bar, and it stops at 20 photos. And the button at the end, "I'm happy with this order", does different things: for the reel it hands the order back to you for the song step; for the carousel the page makes the slides itself, there and then (see "The carousel's page" below). Singles and stories have no page; they are changed by saying it, and you run `kit.py picks` again.

## When to open it

- Whenever you show your reel pick for a shoot that has a post kit (the reel skill's Step 2 says how).
- Whenever they say "change the picks", "reorder the reel", "let me move those around", or anything that means the same.
- For the carousel, whenever they want to change which photos are in it or their order and would rather do it themselves: "change the carousel", "reorder the slides", "let me pick the carousel photos".
- Not in the middle of a whole post kit being made: those steps carry on without stopping. They can change the reel or the carousel afterwards.

They can also get there without you: the kit page has a "Change the photos" button in its Reel section and in its Carousel section, which opens the same page.

A shoot with no post kit has no page; its picks are changed in the chat, by number, as before.

## The two commands

```
python3 <scripts>/arrange.py open "<kit>" --piece reel
python3 <scripts>/arrange.py apply "<kit>" --piece reel
```

**open** gets the page ready (it numbers the photos if that hasn't been done, makes the small copies the page shows, and starts the page server if it isn't running) and prints the page's address on its last line. Load that address in the Claude app's browser pane and bring the pane forward (`mcp__ccd_view__show_pane`, pane `preview`). Never Chrome. The page shows whatever the kit's reel pick is, so save your pick first with `kit.py picks "<kit>" --reel ...`.

Then say, in place of a paragraph of numbers: "My pick for the reel is on the page beside us: 12 photos, in the order they'll play. Opens wide on the beach, moves in to the two of them, ends on the walk away. Move anything you like, or leave it as it is. Next I'll ask which song to cut it to." and ask "Go with these?" [Make it (recommended)] [Change the picks]. If they choose Change the picks: "It's on the page beside us. Drag the photos where you want them, then press \"I'm happy with this order\"." Then wait. The page tells them to come back to the chat and say "done".

**apply** takes the order from the page into the kit and prints it the way the reel script reads it: `Reel picks: 19,4,10+,14-`. Run it before the song question every time, whichever way they said yes (the button, "done", "looks good"), and use the picks it prints for everything after. If they moved nothing, it prints your pick. Running it twice changes nothing.

If they would rather say a change than drag it ("start with the couple"), do it their way: `kit.py picks "<kit>" --reel ...` again. A fresh pick from you replaces what is on the page, and an open page shows it by itself within a few seconds (if it hasn't, load its address in the pane again). The order it replaced is kept (`arrange.py earlier "<kit>" --piece reel` prints it), so nothing they arranged is ever thrown away. Number the photos through the kit before you pick (`kit.py sheet "<kit>"`, the reel skill's Step 1), so your numbers are the page's.

## A line that starts ARRANGED

`home.py pending` prints one after its list when they pressed "I'm happy with this order" on a page:

```
ARRANGED: 2026-06-24 Beach | reel | 12 photos
```

The first part is the kit's folder name; use it as the kit in the commands. The second part is the piece. What follows is for a reel; for a line that says `carousel`, see "The carousel's page" below.

- **You were waiting on that reel** (you had asked "Go with these?", or they just said "done"): run `arrange.py apply "<kit folder>" --piece reel`, take the picks it prints, and carry on with the reel skill from its song step. apply clears the line, and the page's own line under the button ("Saved. Go back to the chat...") goes with it.
- **It came out of the blue** (they opened the page themselves and rearranged a reel): one line and one question. "You put the beach reel in a new order: 12 photos. Want me to make it?" [Make it (recommended)] [Not now]. On yes, apply and make the reel from the song step. On "Not now", `arrange.py took "<kit folder>" --piece reel`; their order stays saved in the kit for whenever they want it.

They said "done" and there is no ARRANGED line: they didn't press the button, and that is fine. The page saves every change as it is made, so run apply and carry on.

## Two things to be straight about

**Longer and Quicker.** Under each photo in the row is a bar that reads Normal, Longer or Quicker. Those are the reel's `+` and `-` marks. They decide which photos linger and which pass quickly only when the reel moves as "A little of everything". The other ways of moving (calm, fast, build, one photo a beat) do not use them. The page says so; you say so too if they set some and then pick another way of moving: "One thing: the Longer and Quicker you set only count with \"A little of everything\". With this one they aren't used."

**A reel that is already in CapCut is never changed.** A new order makes a new CapCut project beside the first ("... reel 2"); the one they may already have styled stays exactly as it is. Say that in a few words when they rearrange a reel that was already made.

## The carousel's page

```
python3 <scripts>/arrange.py open "<kit>" --piece carousel
python3 <scripts>/arrange.py apply "<kit>" --piece carousel
```

**open** works as it does for the reel. Load the address it prints in the pane, bring the pane forward, and say: "My pick for the carousel is on the page beside us: 7 photos, in the order people will swipe. Move anything you like, then press \"I'm happy with this order\"." There is nothing to wait for and no question to ask: the page does the rest.

**What the button does.** The page says "Making your slides..." and, a few seconds later, "Done. 7 slides are in your Carousel folder." with an "Open the Carousel folder" button beside it. The plain slides in the kit's Carousel folder are then in their order: the new ones made from the photos, and the earlier plain slides moved into the kit's hidden folder (never deleted). Canva's slides, and any file in that folder that isn't named like one of this shoot's slides, are left where they are. A plain slide they have edited and saved under its own name counts as a slide: if its place in the order changes it is moved into the hidden folder with the others, kept exactly as they saved it, and you can fetch it back for them. The kit page and the posting queue's picture follow by themselves. If a photo can't be read (the drive is unplugged), the page says which one and that the Carousel folder was left as it was; nothing is half done.

**A line `ARRANGED: <kit folder> | carousel | 7 photos`** from `home.py pending` means they pressed that button. Run `arrange.py apply "<kit folder>" --piece carousel`. It makes sure the slides are in the order the button was pressed on (they almost always already are, and then it changes nothing), clears the line, and prints the order and what it did. Then one line: "Your slides are in the new order: 7, in the Carousel folder."

- **If it printed a line starting `Canva:`**, the kit's Canva slides were made from another order than the carousel has now, so ask: "Your Canva slides still show the old photos. Want me to fill your template again?" [Yes, redo them] [Leave them]. On yes, read `parts/canva.md` and fill the carousel template again from the new order (its last step, `canva_kit.py note`, is what tells the Assistant the Canva slides are up to date again; the line then goes from the page by itself). apply prints this line every time it is true, whether or not it changed anything itself. The page tells them the same thing in its own words: say "redo the Canva carousel" to Claude; that phrase means this.
- **If it printed a line starting `Page:`**, they pressed the button and then moved photos again without pressing it. The slides are the order they pressed on; what they moved afterwards is still on the page, not made (the page has told them to press the button again when it's right). Say so and ask: "Your slides are in the order you pressed the button on. You've moved a few photos since. Want the slides the way the page is now?" [Yes, as it is now] [Leave them]. On yes: `arrange.py apply "<kit folder>" --piece carousel --as-it-is`.

They rearranged the carousel but never pressed the button, and tell you so ("I changed the carousel"): run the same `apply`. With no press waiting, it takes the order as they left it and makes the slides.

**If they would rather say it than drag it** ("swap the third slide for the one of the dog"): `kit.py picks "<kit>" --carousel ...`, then `kit.py build "<kit>"`. build makes the new slides and sets the earlier ones aside the same careful way, and says how many. A fresh pick from you replaces what is on the page, and the order they had is kept (`arrange.py earlier "<kit>" --piece carousel`). A carousel holds at most 20 photos (Instagram's limit); `kit.py picks` refuses more.

**If apply or build stops**, it says why in one line, and nothing was lost:

- **"...were not finished: ... run this again to finish"**: something about the drive stopped it half way (the drive is full, a folder can't be written to, the drive was unplugged). The line says which. Once that is put right, run the same command again and it finishes from where it stopped.
- **"... has a name a new slide needs"**: a file of theirs in the Carousel folder has the same name as one of the new slides (their drive treats capital and small letters as the same). Nothing was moved; if a move had already begun, the earlier slides were put back and the line says so. The line names the file. Tell them, and ask them to rename it or move it out: "There's a file in your Carousel folder called \"<its name>\" that has the same name as one of the new slides. Could you rename it or move it somewhere else? Then I'll finish." Then run the same command again. The page says the same without the file's name and sends them to you.

## If the page can't show a shoot

The page says "I can't find that shoot's posts. Is the drive plugged in?" when the kit's folder isn't there, and "This shoot isn't ready for this yet" when its photos have never been numbered. `arrange.py open` fixes the second by itself. A photo that can't be read right now (the photos are on a drive that is unplugged) still shows if its small copy was made earlier; if not, its tile says "Can't read this photo right now". Either way one line at the top of the page says why.
