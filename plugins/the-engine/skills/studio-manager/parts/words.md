# The words for a post: the caption, and a reel's hooks

Part of the Assistant's instructions. The first-thing checks, the rules and how you talk are in SKILL.md and apply here too.

A post isn't finished when the reel or the carousel is made; it is finished when it has its caption (Nicole, Nov 10). The words are theirs. They say what the shoot was about, in the chat or on the piece's words page, and you shape it the way an editor would: their story, their phrases, their feeling, only better, and never a fact they didn't give. This is the one way a caption or a hook is written (Dustin and Nicole, Nov 10). There is no other.

**Read this part in full when they paste or say any of these.** The words page hands out the first three with a Copy button, so they usually arrive pasted, word for word:

- **"Ask me about the <shoot> reel"** (or carousel): they'd rather talk than type. The interview, below.
- **"Write my words for the <shoot> reel"** (or carousel): write the caption (and a reel's hooks) from what they've said. "Writing", below.
- **"Polish my caption for the <shoot> reel"** (or carousel): they wrote their own. "Polishing", below.
- **The same in their own words:** "write a caption for the beach reel", "I need hooks", "redo the captions", "make the caption shorter", "change the opening". Work out which of the three it is ("In their own words", below).

## What gets words, and what doesn't

- **A reel:** one caption and ten hooks (a hook is the line on the reel's first photo).
- **A carousel:** one caption, and nothing else. No hooks, no cover lines, no lines for the slides: what a slide says they type themselves in the designer (`parts/arrange.md`).
- **A single post** is a one-slide carousel, and its words are the carousel's. Use `carousel`.
- **Stories get no words from you.** They type on a story themselves, in the stories designer. If they ask for story words, say so in one line and offer to open the designer (`parts/arrange.md`, "Making stories"). The only words that ever go on a story for them are a line they gave you for a Canva story template (`parts/canva.md`).
- **Never hashtags, and never a second, short caption** (Dustin, Nov 10). Don't add them, don't offer them. If they want hashtags they add their own to the caption on the page.

## The commands

`<kit>` is a few words of the shoot's name, in quotes: the `<shoot>` in the line they pasted is the kit's folder name without its date, and it finds the kit as it is. The piece is `reel` or `carousel`.

```
python3 <scripts>/words.py ask    "<kit>" reel                    how to ask, and what's answered so far
python3 <scripts>/words.py answer "<kit>" reel --file <a.json>    save what they said for one question (or more)
python3 <scripts>/words.py show   "<kit>" reel                    the rules, their Brand Homebase, everything they said, what's written
python3 <scripts>/words.py draft  "<kit>" reel --file <d.json>    save the caption, and a reel's ten hooks
python3 <scripts>/words.py carry  "<kit>" reel carousel           copy one piece's answers to the other
```

**Every command prints the rules for the moment it is for:** `ask` prints how to ask, `show` prints how to write, Nicole's own rules, word for word. Follow what it prints every time, even when you remember it; her hook rules stand as written, and where anything else you have read about hooks or captions differs, what the command prints wins. This part doesn't repeat them. It says what a command can't: when to run what, in what order, what to say afterwards, and the traps.

**Anything they said goes through a file, never the command line.** A caption has quotes, apostrophes, dollar signs, line breaks and emoji in it, and a command line, a PC's above all, can change every one of them. Write the file with the Write tool into your scratchpad (never into their folders), as UTF-8 JSON, then hand its path to `--file`. A fresh file for each save.

An answer file holds only the answers you are saving now; everything else stays as it was:

```
{"about": "what they said about the shoot, as they said it"}
{"who": ["new", "followers"]}
{"who_text": "what they said about who those people are"}
{"where": "feed"}
{"purpose": "offer"}
{"purpose_text": "what it is, the dates, where, how to book, as they said it"}
{"notes": "Names: use their first names. Don't mention the rain."}
```

`who` is a list of any of `new`, `past`, `followers`, `photographers`. `where` is `feed` or `trial` (a reel's question only). `purpose` is one of `share`, `book`, `offer`, `other`. Those are the page's buttons, and nothing else is accepted.

A draft file:

```
{"caption": "the caption, with its line breaks", "hooks": ["one line", "another line", "... ten in all"]}
```

Leave `hooks` out for a carousel, and for a reel whenever only the caption is changing.

**What the commands answer.** Exit 0: done, and a line saying what was saved. Exit 2, a line starting `STOP:` that ends "Nothing was saved.": the file had something that isn't one of the buttons, or nothing in it; mend the file and save again. Also exit 2: no kit matches those words (`posts.py list` names every kit). Exit 1: the words fit more than one kit, and it names them; ask which with buttons, then use that kit's whole folder name. If they didn't say which piece, ask: [The reel] [The carousel].

## "Ask me about the <shoot> reel": the interview

1. Run `words.py ask "<kit>" reel` once. It prints the questions, their order, the buttons each has, and what is already answered. **Skip what's answered** unless they want to change it.
2. **One question at a time, in the order it prints:** 1 the shoot; 1b whether to use the people's names; 2 who they're trying to reach; 2b tell me about them; 2c, reels only, feed or trial reel; 3 what the post is for; 3b the follow-up to that; 4 anything to include or leave out. Never two at once. Each short and warm, with its one line of why.
3. **Buttons wherever the page has them** (the who, more than one allowed; feed or trial; the purpose; Skip this; Nothing else). Question 1, and the follow-ups when they'd rather talk, are plain questions with no buttons: ask, and wait. They are talking into the microphone in the chat box, which is the whole reason they pasted this line.
4. **Save each answer the moment you have it,** with `answer`, before you ask the next one. The words page is open beside the chat and fills in within a few seconds, which is how they see it's working. Don't hold answers to save at the end.
5. **Their words, as they said them.** Tidy only an obvious dictation slip (a doubled word, a wrong homophone). Don't shorten, don't improve, don't add. The improving happens in the caption, never in their answer.
6. **1b, 2b and 3b are always asked** (Nicole caught them being skipped). 2b and the lighter 3b have a Skip this button; pressing it is their answer. 1b only if people are in the shoot.
   - **A skip saves nothing.** Skip this, and Nothing else on question 4, are not saved anywhere: there is no file to write, and never a made-up "skipped" or "Nothing else" in their answers, since the page would show it as theirs. In this conversation you remember it and don't ask again.
   - **On a later pass** (they paste the line again, or a new conversation) `ask` can't show a skip. How to read what it prints: in lines 2 and 3 a follow-up that was answered shows after a " · "; buttons with nothing after them mean 2b or 3b is still open, so offer it once more, lightly, with its Skip this ("Anything to add about who they are?"). Line 4 with "Names: ..." or "No names" in it means 1b is done. Line 4 saying "(not yet)" means ask 4 again; it is one press.
7. **Names.** If yes to names, ask for any they haven't said, spelled their way, and check a spelling you're not sure you heard right. Names live in notes: "Names: ..." or "No names".
8. **Saving notes replaces notes.** When question 4 adds something, write the notes file with what was already there (the names line) and the new line together.

**If question 1 isn't answered but they told you about the shoot when the kit was made,** `ask` prints what they said then. Don't ask question 1 cold: read it back in a line and ask "Is that what you'd say about it for this one, or do you want to add to it?" [Use that] [Let me add to it]. Save it as `about` only once they say so, with anything they add. Never save it there without asking: it is theirs, but they said it about the whole shoot before this piece existed, and the page would show it as their answer to a question they were never asked.

**If nothing is answered for this piece but the other one is,** `ask` says so ("Nothing is answered for the carousel yet, but the reel is"). Don't start again from question 1: ask once, "You told me about this shoot for the reel. Use that for the carousel too?" [Use what I said for the reel] [Ask me again]. On yes, `words.py carry "<kit>" reel carousel` (the piece that has answers first), run `ask` again, and ask only what is still open: for a reel that is 2c, which is the reel's own question and never carries. On Ask me again, the interview from question 1.

**Ask, don't guess.** When something they said sounds like a slip of the microphone ("fifteen dollar photos" when everything else says 15 photos each), check it with buttons before you save it. When something an offer needs is missing (the date, where, how to book), ask for it at 3b; the price only if they want it in. Never fill a gap, not even with something probably true.

**When the last one is saved,** say so in one line ("That's all on the page.") and go straight on to "Writing" below, without waiting to be asked.

## "Write my words for the <shoot> reel": writing

1. `words.py show "<kit>" reel`. It prints the rules, where their Brand Homebase is, everything they said, their own caption if they wrote one, the other piece's caption if it has one, and what is already written with the hooks they've picked marked.
2. **Nothing to write from yet?** If every answer says "(nothing yet)": for a carousel whose reel has answers, `words.py carry "<kit>" reel carousel` and `show` again (the other way round for a reel, and then ask 2c, which is the reel's own question and never carries). Otherwise say "Let me ask you a few things first, one at a time," and do the interview. If the shoot is answered but not what the post is for, ask question 3 and its follow-up before you write: the caption opens with it.
3. **Read their Brand Homebase in full,** with the Read tool, at the path `show` printed, every time, before you write a word. It is the brand interview for their photography business: how they sound, the words they use, the words they never want to see, their house rules, who their ideal client is. Check every line you write against it. If it expects something they didn't give (a price on a mini-session post), ask them for it.
   - **The mistake to avoid: never another brand's file.** A photographer may have a brand file for some other business of theirs on the same computer, written for a different audience; a client post in that voice is wrong from the first line. Use only the one `show` points to. Never search the computer for one, and never borrow one from somewhere else because it has the right name.
   - **If `show` says "No Brand Homebase found":** say so plainly, once in a conversation, and ask: "I don't have your Brand Homebase yet, the page or two that says how your photography business sounds. Do you have one?" [Yes, I'll put it in my Assistant folder] [No, write from what I told you]. On yes, they drag it into their Assistant folder: the folder Your Content sits in, and `show` prints the exact place under "No Brand Homebase found" (offer to open the folder for them). The file `show` finds is named exactly `brand-homebase.md`, in that folder; no other name or ending is found. So whatever they dragged in (a PDF, a Word file, a file with another name), read it and save a faithful text copy beside it as `brand-homebase.md` with the Write tool; theirs stays as it is. Run `show` again; go on only when it prints "Their Brand Homebase:", and read the copy in full. On no, write from their answers and from what `show` prints under it: the captions they've posted and the ones they'd never write, from the "how I write" question (`parts/post-kit.md`). That is the fallback until the brand interview is part of setup. Your closing line then says so: "It isn't checked against your brand yet."
4. **Write, by the rules `show` printed.** The order of a caption: **the goal first**, in the opening line or two, where people see it before "more" (for something coming up: what, when, where, and the price if they gave one); then their story; then exactly how to book or what to do. Reorder what they said; never change it. **How a caption closes is theirs:** a thank-you to the client by name, a sign-off, a favorite last line go in only when their Brand Homebase shows that habit or they said it; with neither, the caption ends on how to book. Even when they said the offer last, it opens the caption.
5. **Specifics come only from them:** names, what happened, the occasion, a feeling about the day, an offer's dates, price and details. A warm sentence you made up about how the day felt is an invented fact; if they didn't say it, it isn't there.
6. **A reel's ten hooks: her rules, as printed.** Before the first one, name to yourself who the post is reaching and what it is for; then check every hook against both, and cut any that describes the shoot, retells the client's story, talks about how the photographer works, or could have come from any photographer. One line each, each a different way in.
7. **If the other piece already has its caption,** `show` prints it as what to avoid. The second caption is genuinely different: same facts, the goal still first, but a different opening line, a different part of their story up front, a different shape. Never the first one with sentences swapped.
8. Save with `words.py draft "<kit>" reel --file <d.json>`. A new draft replaces the last one (the version before is kept beside it).
9. **One line, and stop:** "Your caption and ten hooks are on the page. Pick the hooks you love there." For a carousel: "Your caption is on the page." Don't paste the caption or the hooks into the chat; the page is where they read, pick, copy and change them. If the words page isn't open beside the chat (they asked in their own words rather than pasting its line), show it: `python3 <scripts>/home.py url` prints the home page's address; load `/words.html?kit=<the kit's folder name, URL-encoded>&piece=reel` on that same address in the Claude app's browser pane and bring the pane forward.
10. Once, when the words for a piece are first written: `python3 <scripts>/home.py did posts --note "wrote the words for the beach reel"`.

**The shape of a good one, with nothing of anyone's in it:** the offer, in their punctuation and their energy. Then the story of the day, in their own phrases, tightened. Then how to book, exactly as they said it. A closing line only if their Brand Homebase or their own words give one. Every fact in it is one they said; everything about how it sounds is from their Brand Homebase.

## "Polish my caption for the <shoot> reel": polishing

They wrote their own caption in the "or write your own" box on the page. `words.py show` prints it as "Their own caption". Read the Brand Homebase in full as above, then polish: fix what trips, tighten, put the goal first if it is buried, keep their words and their order of thought. **Never replace it and never add a fact.** Save the polished one with `draft` and a caption only (`{"caption": "..."}`): it lands in the Caption box on the page, their own stays untouched in its box, and the hooks and their picks stay as they are. One line: "Your polished caption is on the page, above your own." If `show` prints no caption of their own, ask them to type it in that box on the page and paste the line again; that way theirs is kept beside the polished one. If they'd rather say it here, take it as said, polish it the same way and save it with `draft`; nothing can put it in their own box from the chat, so close with "Your polished caption is on the page." and no word about their own.

## In their own words

- **"Write a caption for the beach reel", "I need hooks for the park reel":** the same as "Write my words". `show` first; with no answers yet, the interview first.
- **"I need hooks" for a carousel:** hooks are a reel's. Say so in one line and offer the caption.
- **"Redo the captions", "make it shorter", "change the opening", "less salesy":** if they haven't said what to change, ask one question ("What would you change?"). Then `show` again, always: they may have changed the caption on the page since you wrote it, and the one on the page is the one to start from. Draft again with the caption only, so the hooks and their picks stay.
- **"New hooks", "more hooks like number 4":** `show` marks the ones they picked. Keep the picked ones, word for word, in the new list of ten and replace the rest. **Saving any change to the hooks clears their picks on the page,** so tell them in the closing line: "Ten hooks are on the page. I kept the three you'd picked; press Pick on them again."
- **"Write me some hashtags", "give me a short version too", "what should my story say?", "what should the first slide say?":** none of these is written by you ("What gets words, and what doesn't", above). One line saying so and what they can do instead: their own hashtags go into the caption on the words page; "make the caption shorter" changes the one caption; a story or a slide they type themselves, and you offer to open the designer.
- **"Which hook should I use?":** the picking is theirs. You can say which two or three you'd reach for and why, in a line each; never pick one for them on the page or put one on a cover or a reel they didn't choose.
- **They change what they told you** ("actually it's December 5th"): save the corrected answer with `answer` first, then write again. The answers are the source; a caption is never mended by hand while the answer still says the old thing.

## The traps

- Writing before reading the Brand Homebase, or reading only its first page.
- Using a brand file `show` didn't point to.
- Describing the shoot as a hook. That is caption material.
- The offer at the bottom of the caption.
- A second caption that is the first one reworded.
- A sentence about how they felt that they never said.
- Lines for a carousel's cover or slides, words for a story, hashtags, a short caption.
- Asking two questions at once, skipping 1b, 2b or 3b, or saving the answers in one go at the end.
- Putting what they said on the command line instead of in a file.
- Pasting the caption into the chat instead of saying it's on the page.
