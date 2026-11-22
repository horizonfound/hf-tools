# Building Nicole's v30 (Nov 21, 2026, overnight; branch `v30`, worktree `/Users/dustindamron/Projects/hf-tools-v30`)

Dustin, Nov 21, night: "slack with new version start building. going to bed". Nicole's pack: `reference-private/nicole-handoff-v30-2026-11-21/` in the MAIN checkout (`/Users/dustindamron/Projects/hf-tools/reference-private/...`; it is not in this worktree and is never committed). `UPDATE-v30.md` is the spec; `pages/home-new-look.html` is her mock-up (read it, never run it); `screenshots/` shows what she means; `hellos/` holds her 150 approved lines.

Same rule as every handoff: identical for the photographer (her words whole, the same behaviour), our way underneath (our routes, our records, nothing installed, never a path to a page, Python 3.9 and 3.12, standard library only in the plugin). Build fast, harden before beta: no per-stage reviewers for pages; a careful review only where files on a drive are touched (the "+ A new shoot" route).

## Choices made so nothing waited (Dustin's and Nicole's to turn round)

1. **The new look is on the home page and the Create dialog only.** Her pack is "mostly on the home page"; every other page keeps today's look (`look.py`, DM Sans, cream and coral) until Dustin says. The home page's look lives in its own block of tokens in `home.py` so it can be moved into `look.py` in one step. Dustin chose "Honey, palm and butter" for the sales page on Nov 14; Nicole's v30 colours are different; theirs to settle.
2. **Helvetica is the Mac's own** (`"Helvetica Neue", Helvetica, Arial, sans-serif`); nothing is downloaded. A PC gets Arial.
3. **The hello's choice is kept by the Assistant** (`~/.studio/home-hello.json`), not the browser, so a reload keeps it for 3 hours.
4. **`later` lines are left out** (her note allows it).
5. **Sample photos:** the mechanism is built with an empty `samples` folder; Nicole chooses the photos. Nothing shows until there are photos in it.

## Stages

- **A. The hello engine** (`hello_lines.py`, data and choosing; no page).
- **B. The home page in the new look** (`home.py`): top bar, one wide hello photo with faces centered from the 1600 px copies, Turn your shoots into posts and the four tiles, See all my post kits alone, the three cards side by side, the recap on tan; no Newest line, no hello button, no Another hello.
- **C. Create a reel: the four tiles ask which shoot** (the dialog, + A new shoot through the folder picker, My vault first, the list with search at 7+), landing on the page tapped.
- **D. The posting queue's grid at about 420 px.**
- **E. Sample photos for a brand-new Assistant** (mechanism only).
- **F. Instructions, notes for Nicole, CLAUDE.md, release.json version 7; the sweep.**

Each stage writes a "Built" note under its heading below.

## Built

### Stage A, the hello engine (built Nov 21, night)

- **What:** `studio-manager/scripts/hello_lines.py` and her 150 lines as data, `studio-manager/hellos/approved-hellos-by-when.json` (her file byte for byte, curly apostrophes kept). No page yet: `home.py` is untouched; stage B wires it. No route.
- **For the page:** `hello_lines.pick(now=None, rng=None, facts=None, fresh=False, write=True)` answers `{greeting, line, greeting_parts, line_parts, name, group, greeting_group, kit, shoot, chosen_at, keep_until, kept}`. The parts are `[{"text", "name": bool}]`, so the page colours the name with textContent only. `kit` is a post kit's folder name (for the photo behind the hello), never a path. `gather(now)` reads the facts from what the Assistant keeps: the name and the year's numbers through `wrapped.gather` / `wrapped.data` (the name the v28 hello already uses), the newest kit through `home_base.kits()`, posts this week from `posting_queue.load()`.
- **The rules as built:** greeting = greet + the part of the day by this computer's clock (before 12 morning, 12 to 5 afternoon, from 5 evening; hers) + greetday ("Happy Monday" Monday only, "Happy Friday" Friday only, "Happy weekend" Saturday and Sunday only, "Happy {day}" any day). Line from the groups true for them: newest (weight 4, 12 just after a new kit), top, photos / shoots / reels / carousels / posted / hours (this year, skipped under 2), week (2+ posts since Monday), week1 (any post since Monday; {kind} reel, carousel or post), monday, friday, weekend, anyday, morningline, eveningline, warm, first (only and always before any post kit or backup), away (last visit 14+ days ago). `later` left out. Weights are hers from her mock-up. A line with a slot it can't fill is never offered; with no name, nothing that needs one.
- **Kept:** `~/.studio/home-hello.json` (written whole, the version before in `home-hello.prev.json`): the chosen templates and slots, when, the kits seen, the last few said, the last visit. A reload within 3 hours keeps it; a post kit that wasn't there before brings a new one at once; a kept hello that stopped being true (a "Good morning" past noon, the day changed, its shoot gone or archived, the name gone) is chosen again; a number that moved is refilled in the same hello. Every page load writes the last visit.
- **CLI:** `hello_lines.py show` (changes nothing), `hello_lines.py pick [--now ISO] [--seed N] [--fresh] [--dry-run]`.
- **Test:** `tests/hello_lines_check.py`, 122 checks, pure Python, a scratch STUDIO_HOME, PASS on Python 3.12 and Apple's 3.9 (about 5 s). Every one of her 137 non-later lines is produced by some true set of facts; no later line ever is. Seven rules were taken out one at a time (the under-2 skip, the first-word clash, the Monday-only greeting, the 3-hour keep, first-only, the weekend days, the twice-running guard) and a check failed each time. Added to GitHub's check (Windows and Mac jobs), `tests/workflow_check.py` 14 of 14. `tools/check_pc.py` clean, `tools/check_plugin.py` CLEAN, `tests/skill_text_check.py` 776 of 776.
- **Choices, ours (for Dustin and Nicole):**
  1. A greeting and a line never start with the same word or share two words in a row, and only one of the two says the name (so no "Happy Friday, Nicole!" with "Happy Friday. You earned it.", no "Hi, Nicole. So glad you're here." with "So glad you're here.").
  2. Before any shoot, no greeting saying "back" or "again".
  3. "This week" is Monday to now by the computer's clock (home.py's posted_week is the last 7 days; hers read that). A Sunday post is not "this week" on a Monday.
  4. The weekend line ("Hope your weekend is a good one.") shows Friday to Sunday, as her mock-up has it; the "Happy weekend" greeting Saturday and Sunday only.
  5. top needs two or more shoots with something made this year, and that one with two things or more ("You keep coming back to {shoot}" must be true).
  6. Hours are the minutes saved rounded to whole hours (her estimate, wrapped.py), shown from 2.
  7. "{n} shoots this year. That's a lot of people with photos..." sits in her photos group; it is filled with the shoots number. "{n} shoots turned into posts" with the shoots something was made from.
  8. {kind}: a single post reads "post".
  9. Before any shoot with no name there is one first line only ("Hi! I'm your Assistant, and I'm so glad you're here."), so it is the same line every visit; the greeting still changes.
  10. Her clock: "Good morning" from midnight (hr < 12), as hers.
- **Not tried:** on the page (stage B), on a real Studio, on a PC (pure Python, should run as is), across midnight by hand; the weights' feel over weeks of real visits.
