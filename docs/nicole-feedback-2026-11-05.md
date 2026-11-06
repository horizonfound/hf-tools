# Nicole's feedback, and what to talk about (started Nov 5, 2026)

Nicole is the first person to use the Assistant on a Mac that isn't Dustin's. This page keeps what she said,
in her words, sorted by what it needs: a decision from the two of you, a small fix, or nothing more.
Claude adds to it as she goes. The install roadblocks themselves are in `install-issues-2026-11-05.md`.

**Her own reason for sending all of it (8:51pm):** "just telling you things cause if i experience it like
this other people will too i think its good to give all the details as someone goes through so tehy know
whats happening."

---

## 1. To decide together

### 1a. Her photos ended up in three places

**Her words (8:42pm, 8:49pm):** "theyre already on my hard drive in another location. it wouldnt make sense
to duplicate it so would you want it to find the folder instead?" Then: "it created a folder called the
assistant and then two sub folders drop a shoot here and your content... i dropped the shoot in a drop a
shoot here folder... then it recreated that same folder in the your content folder... so now my hard drive
has my original folder... and it duplicated twice in drop a shoot and your content."

**What happens today:** exactly what she describes. The finished photos are copied into "Drop a shoot
here," and then copied again into "Your Content." With her original folder that is three copies of the same
52 photos on one drive. When the photographer uses the folder picker, the Assistant makes both of those
copies itself.

**Dustin told her (8:50pm):** "the drop folder gets cleared once everythign is organized after you rename
the shoot." **That is not what the Assistant does today.** It never clears the drop box. It says "clear it
out whenever you like" and leaves it, because the rule since Oct 30 has been that nothing is ever deleted.
So either she should be told that, or the Assistant should be changed to match what he said.

**Ways to go:**
- **Work from the photos where they are.** No copy of the originals at all; only the sized posts are made
  new. This already exists (`kit.py start --folder`) and is what she expected. It depends on the original
  folder staying put: if she moves or renames it later, the kit loses its photos.
- **Copy once, not twice.** Go from her folder straight into Your Content and skip the drop box when she
  points at a folder. One extra copy, the kit holds its own photos, nothing to clear.
- **Keep both copies but clear the drop box after.** What Dustin described. It means the Assistant deletes
  files, which it has never done; the rule would need an exception for copies it made and has just checked.

**Not decided.**

### 1b. Everything at once, or one piece at a time

**Her words (8:47pm):** "i feel like it should be one at a time this feels overwhelming to have it create
these for you and it makes it feel like its just gonna do it without any input... wether thats true or not
it feels like it is."

**What happens today:** one request makes the whole kit: reel, carousel, singles, stories, covers, captions
(Dustin, Oct 30: "as much done for you as possible").

**Worth talking about:** the two aims pull against each other. Her note is about feeling in control, which
is also rule 11 (the photographer is behind the wheel). A middle way exists: ask "What do you want to make
first?" with the whole kit as one of the choices.

**Not decided.**

### 1c. The caption question comes before she has seen anything

**Her words (8:48pm):** "like showing it the photos and then it asking for the caption already i feel like
you should make the reel or carousel or story first and then you would make the caption after you see the
final piece."

**Dustin answered her (8:48pm):** "no ... all you need to do is share stories and details about the shoot.
give a little background about what it was like."

**Two things in there:**
- **The wording** (a small fix, see 2a): the Assistant said "the captions come from you" and "anything you'd
  put in the caption," so she heard "write your caption now."
- **The order:** she would write about the shoot after seeing the pieces. Today the question comes first so
  the captions can be made in the same pass. **Not decided.**

### 1d. How students get the Assistant, and how they get updates

Not from Nicole, but tonight showed it needs deciding.
- **Tonight:** a file passed over Slack. Students need one place to download it (the course, or a link).
- **Updates do not arrive on their own.** Claude copied our GitHub project once, on October 16, and never
  went back, because nothing tells it to. There is a "Check for updates" button that should refresh it;
  nobody has pressed it yet. If it works, students could install from the marketplace with no file at all,
  and update with one click. **Try it on Dustin's account first.**

### 1e. The Start Here interview

Set aside on Nov 5 with three other October skills so the install has one helper. Whether the 40-minute
interview comes back is yours to say.

---

## 2. Small fixes Claude can make when you say go

### 2a. Reword the question before a post kit

Proposed, to match what Dustin told her:

> Great. I'll put your post kit together: the reel, the carousel, a few single posts and stories. You'll see
> every piece on one page when it's done, you can change any of it, and nothing gets posted. First, tell me a
> little about this shoot: who they are, what the day was like, a moment that stuck with you. You're not
> writing a caption, just talking. I'll write the captions from what you tell me.

### 2b. The same question asked twice

Before the photos came in, the Assistant explained the two ways to hand them over in a paragraph, then asked
the same thing again in a box with two buttons. One is enough.

### 2c. Say what is happening as it goes

Her 8:51pm note is a request for more narration: at each step, what the Assistant is doing and what she
will see next. The install guide now does this. The Assistant itself could do more of it at the moments
that surprised her: making folders, copying photos, opening Instagram.

### 2d. "Click Plugins first, then Yours"

She was on the Connectors tab, where Yours lists connectors. The guide should name the tab first. She also
found that the filter button on Plugins has a Source list with "My Uploads" in it.

---

## 3. Already fixed tonight

- The upload was refused over a description two characters too long. Fixed, and now checked automatically
  before any file can be built.
- "Couldn't access Documents": the guide now puts the Assistant's folder in the home folder.
- Instagram's sign-up box over her grid looked like the Assistant logging her in. The Assistant now says
  beforehand that the box may appear and that she doesn't need to log in.
- The guide's install steps, rewritten to the route that worked on her Mac.

---

## 4. Not known yet

- **"1 failed."** One of the Assistant's commands failed while it set up her folder; it carried on. Which
  one is not visible from here.
- **Whether "Check for updates" works** for our GitHub project, on either account.
- **What "installed" looks like** under Plugins, Yours on her Mac. A screenshot was asked for.
