# Changing the photos on a page

Part of the Assistant's instructions. The first-thing checks, the rules and how you talk are in SKILL.md and apply here too. The quoted lines below are the default wording; Dustin and Nicole may change any of them.

Choosing and ordering the photos is your job and stays so. This page is how the photographer moves things after you have picked: your pick is in a row at the top, in the order it plays, with every photo of the shoot below it. They drag to reorder, drag one up to add it, drag one down (or press its X) to take it out, and click any photo to see it big. Every change is saved to the kit as they make it, so nothing is lost if the page is closed.

**So far only the reel has this page.** The carousel's is coming; until then a carousel is changed by saying it ("swap the third slide for the one of the dog") and you run `kit.py picks` again.

## When to open it

- Whenever you show your reel pick for a shoot that has a post kit (the reel skill's Step 2 says how).
- Whenever they say "change the picks", "reorder the reel", "let me move those around", or anything that means the same.
- Not in the middle of a whole post kit being made: those steps carry on without stopping. They can change the reel afterwards.

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

The first part is the kit's folder name; use it as the kit in the commands.

- **You were waiting on that reel** (you had asked "Go with these?", or they just said "done"): run `arrange.py apply "<kit folder>" --piece reel`, take the picks it prints, and carry on with the reel skill from its song step. apply clears the line, and the page's own line under the button ("Saved. Go back to the chat...") goes with it.
- **It came out of the blue** (they opened the page themselves and rearranged a reel): one line and one question. "You put the beach reel in a new order: 12 photos. Want me to make it?" [Make it (recommended)] [Not now]. On yes, apply and make the reel from the song step. On "Not now", `arrange.py took "<kit folder>" --piece reel`; their order stays saved in the kit for whenever they want it.

They said "done" and there is no ARRANGED line: they didn't press the button, and that is fine. The page saves every change as it is made, so run apply and carry on.

## Two things to be straight about

**Longer and Quicker.** Under each photo in the row is a bar that reads Normal, Longer or Quicker. Those are the reel's `+` and `-` marks. They decide which photos linger and which pass quickly only when the reel moves as "A little of everything". The other ways of moving (calm, fast, build, one photo a beat) do not use them. The page says so; you say so too if they set some and then pick another way of moving: "One thing: the Longer and Quicker you set only count with \"A little of everything\". With this one they aren't used."

**A reel that is already in CapCut is never changed.** A new order makes a new CapCut project beside the first ("... reel 2"); the one they may already have styled stays exactly as it is. Say that in a few words when they rearrange a reel that was already made.

## If the page can't show a shoot

The page says "I can't find that shoot's posts. Is the drive plugged in?" when the kit's folder isn't there, and "This shoot isn't ready for this yet" when its photos have never been numbered. `arrange.py open` fixes the second by itself. A photo that can't be read right now (the photos are on a drive that is unplugged) still shows if its small copy was made earlier; if not, its tile says "Can't read this photo right now". Either way one line at the top of the page says why.
