#!/usr/bin/env python3
"""The chat side after v19 (stage e): what Claude reads says what the new pages do.

    /usr/bin/python3 tests/skill_text_check.py

Reads text only; nothing is run, started or written. What it checks:
  * a scripted search over every instruction Claude reads (the two skills, every part, shared/, the commands)
    and the lines the scripts hand Claude: no step asks the song or the vibe in the chat, and nothing opens the
    old reel picker for a reel (arrange.py open ... --piece reel), or names it except as the older page;
  * the core table: a row for each thing the photographer says that the new pages answer ("make a reel",
    "pick my reel photos for <shoot>", "look through my footage for <shoot>", "lay out my stories" / "make my
    stories", "make a single post", "show my post kit"); every file a row names exists, and every section a row
    names by its title is in that file;
  * both skills' descriptions stay within 1,024 characters (Claude's own limit, tools/check_plugin.py);
  * shared/curating.md by decision 10: Nicole's rules decide what goes in (the best photos, stories in the shoot, a
    shortlist each, close calls side by side, similar photos when they tell a story, the same expression a moment
    later left out), the Assistant's flow rules decide the order (with the emotion building and coming back down),
    "8 to 14" is a guide, Claude's own judgment is labelled as Claude's, and the old lines that contradict hers
    are gone;
  * the reel skill: Nicole's choosing rules in Step 2, her footage rules 4 to 6, "nothing is ever left out to fit";
  * the hello, the home page, the kit and the Canva part: the reel page named where the old flow was, and the
    stories designer offered where only plain or Canva stories were;
  * nothing of a client's in the text this stage wrote.

Every line says PASS or FAIL; exit 1 only when something FAILED.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PLUGIN = ROOT / "plugins" / "the-engine"
SKILLS = PLUGIN / "skills"
SM = SKILLS / "studio-manager"
REEL = SKILLS / "assistant-make-a-reel"
SCRIPTS = SM / "scripts"

_results = []


def case(name, ok, detail=""):
    _results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ((" -> " + str(detail)[:400]) if (detail != "" and not ok) else ""), flush=True)
    return bool(ok)


def read(p):
    return Path(p).read_text(encoding="utf-8")


def instruction_files():
    """Every text Claude reads as instructions: the skills, their parts, shared/, the slash commands."""
    out = [p for p in SKILLS.rglob("*.md") if "references" not in p.parts]
    out += sorted((PLUGIN / "shared").glob("*.md")) + sorted((PLUGIN / "commands").glob("*.md"))
    return sorted(set(out))


def rel(p):
    return str(Path(p).relative_to(PLUGIN))


# ---------- 1. the scripted search: no song or vibe asked in the chat, no reel picker opened for a reel ----------

ASKS = [
    # a question put to them with buttons ('"...?" [') that is about the song or the vibe
    (r'"([^"\n]{3,200}\?)"\s*\[', lambda q: re.search(r"\b(song|songs|music|vibe|feel|pace|move)\b", q, re.I)),
    # 'Ask with buttons: "...' about the song or the vibe
    (r'Ask with buttons[^:\n]*:\s*"([^"\n]{3,200})', lambda q: re.search(r"\b(song|vibe|pace)\b", q, re.I)),
]
TELLS = [
    r"(?<!don't )(?<!never )(?<!Never )\b[Aa]sk (?:them )?(?:which|what) (?:song|vibe)",   # "ask which song" (not "don't ask which song")
    r"\bI(?:'|’)ll ask which song",                            # the old picker's line
    r'"Which song\?"', r'"How should it move\?"', r'"What vibe\?"',
    r"Always ask this question",
    r"\bthen ask (?:the|for the) (?:song|vibe)",
]


def check_search():
    files = instruction_files()
    case("the search covers the two skills, every part, shared/ and the commands (at least 20 files)", len(files) >= 20, len(files))
    for p in files:
        t = read(p)
        bad = []
        for pat, about in ASKS:
            bad += [m.group(1) for m in re.finditer(pat, t) if about(m.group(1))]
        for pat in TELLS:
            bad += [m.group(0) for m in re.finditer(pat, t)]
        case(f"{rel(p)}: no step asks the song or the vibe in the chat", not bad, bad[:3])
        opens = re.findall(r"arrange\.py open [^\n`]*--piece reel", t)
        case(f"{rel(p)}: nothing opens the old reel picker for a reel", not opens, opens[:2])
        named = [ln for ln in t.splitlines() if re.search(r"reel(?:'s)? picker", ln, re.I)]
        stale = [ln[:160] for ln in named if not re.search(r"older reel picker|old reel picker", ln, re.I)]
        case(f"{rel(p)}: the reel picker is named only as the older page", not stale, stale[:2])
    # the lines the scripts hand Claude or the photographer
    ap = read(SCRIPTS / "arrange_page.py")
    said = [ln for ln in ap.splitlines() if re.match(r"\s*done(?:Again)?: '", ln)]
    case("the old reel picker's saved lines send them to the reel page, not to a song question in the chat",
         len(said) >= 2 and not any("which song" in ln for ln in said)
         and sum("I’ll put this order on the reel page" in ln for ln in said) == 2, said)
    kit = read(SCRIPTS / "kit.py")
    m = re.search(r'REEL_LINE = \("(.*?)"\s*\n\s*"(.*?)"\)', kit, re.S)
    line = (m.group(1) + m.group(2)) if m else ""
    case("kit.py build's reel line says the reel is made on the reel page, not now",
         line.startswith("Reel: the pick is saved; the reel is made on the reel page") and "not here" in line
         and not re.search(r'say\("Reel: run reel\.py make', kit) and kit.count("say(REEL_LINE + ") == 2, line[:200])
    home = read(SCRIPTS / "home.py")
    case("the home page names no reel picker", not re.search(r"picker", home.split("# ---------- the page ----------", 1)[-1].split("CSS_EXTRA", 1)[0], re.I))


# ---------- 2. the core table ----------

def table_rows(core):
    return [ln for ln in core.splitlines() if ln.startswith("| ") and not ln.startswith("| When") and not ln.startswith("|---")]


def check_table():
    core = read(SM / "SKILL.md")
    rows = table_rows(core)
    case("the core table has its rows", len(rows) >= 15, len(rows))
    wanted = {
        '"make a reel"': ["../assistant-make-a-reel/SKILL.md", "parts/arrange.md"],
        '"pick my reel photos for <shoot>"': ["../assistant-make-a-reel/SKILL.md", "parts/arrange.md"],
        '"look through my footage for <shoot>" (and "... and follow my notes")': ["../assistant-make-a-reel/SKILL.md"],
        '"lay out my stories"': ["parts/arrange.md"],
        '"make my stories"': ["parts/arrange.md"],
        '"make a single post"': ["parts/arrange.md"],
        '"show my post kit"': ["parts/post-kit.md"],
        '"lay out my carousel"': ["parts/arrange.md"],
    }
    for phrase, files in wanted.items():
        hit = [r for r in rows if phrase in r.split(" | ")[0]]
        case(f"exactly one row answers {phrase}", len(hit) == 1, len(hit))
        if hit:
            named = re.findall(r"`([^`]+\.md)`", hit[0].split(" | ", 1)[1])
            case(f"... and it sends Claude to {', '.join(files)}", all(f in named for f in files), named)
    # every file a row names exists; every section it names by title is in that file
    missing, no_section = [], []
    for r in rows:
        right = r.split(" | ", 1)[1] if " | " in r else r
        for f in re.findall(r"`([^`]+\.md)`", right):
            p = (SM / f).resolve()
            if not p.is_file():
                missing.append(f)
        for f, title in re.findall(r"`([^`]+\.md)`[^|`]*?, \"([^\"]+)\"", right):
            p = (SM / f).resolve()
            if p.is_file() and title not in read(p):
                no_section.append((f, title))
    case("every file the core table names exists", not missing, missing)
    case("every section the core table names by its title is in that file", not no_section, no_section)
    for title, f in (("## The reel's page", "parts/arrange.md"), ("## Making stories: the stories designer", "parts/arrange.md"),
                     ('**A single post: "make a single post".**', "parts/arrange.md"), ('## "Show my post kit"', "parts/post-kit.md"),
                     ("## Behind-the-scenes footage", "../assistant-make-a-reel/SKILL.md")):
        case(f"{f} has the section {title!r}", title in read((SM / f).resolve()))


# ---------- 3. descriptions ----------

def check_descriptions():
    for skill in (SM, REEL):
        t = read(skill / "SKILL.md")
        d = re.search(r"^description: (.*)$", t, re.M)
        n = len(d.group(1)) if d else 0
        case(f"{skill.name}: the description is within 1,024 characters ({n})", d and n <= 1024, n)
    d = re.search(r"^description: (.*)$", read(SM / "SKILL.md"), re.M).group(1)
    case("studio-manager's description names the new phrases (show my post kit, make a single post, make my stories)",
         all(x in d for x in ("show my post kit", "make a single post", "make my stories", "lay out my carousel")))
    d = re.search(r"^description: (.*)$", read(REEL / "SKILL.md"), re.M).group(1)
    case("the reel skill's description names make a reel, pick my reel photos and look through my footage",
         all(x in d for x in ("make a reel", "pick my reel photos", "look through my footage")))


# ---------- 4. curating.md: decision 10 ----------

def check_curating():
    t = read(PLUGIN / "shared" / "curating.md")
    what = t.split("## What goes in", 1)[-1].split("\n## ", 1)[0]
    order = t.split("## The order", 1)[-1].split("\n## ", 1)[0]
    case("curating.md says whose each half is: what goes in is Nicole's, the order is the Assistant's (decision 10)",
         "## What goes in: the best photos (Nicole, Nov 6)" in t and "## The order: how the set flows (the Assistant's own, Dustin, Oct 25)" in t
         and "decision 10" in t)
    case("... what goes in: the photos are the point, the best photos on their own merit",
         "The photos are the point" in what and "Choose the best photos" in what and all(
             x in what for x in ("stop the scroll", "the best story", "variety", "emotion", "the story the photographer is trying to tell")))
    case("... similar photos are allowed when they tell a story; the same expression a fraction of a second later is out",
         "Similar photos are allowed when together they tell a story" in what and "the same expression a fraction of a second later" in what)
    case("... '8 to 14' is a guide, not a rule", "8 to 14" in t and "a guide, not a rule" in t and "Pick 8 to 14" not in t)
    steps = t.split("## How to choose, step by step", 1)[-1].split("\n## ", 1)[0]
    case("... her method: the whole shoot at once, the stories in it, a shortlist each, close calls side by side",
         all(x in steps for x in ("See the whole shoot at once", "Find the stories in the shoot", "Shortlist the strongest frames for each story",
                                  "Settle the close calls side by side", "Keep sequences that tell a story")))
    case("... the order: the emotion builds and comes back down, the scroll-stopper opens, a quiet frame closes",
         "Let the emotion build, then come back down" in order and "Open on the scroll-stopper" in order and "quiet, final frame" in order)
    case("... how a feel turns into picks is labelled Claude's judgment, not a rule",
         "**your judgment, not a rule**" in t and "Nicole named the idea but hasn't said how each feel should change the picks" in t)
    case("... never turn one of her comments into a rule she didn't say",
         "Never turn one of Nicole's comments about a particular photo or clip into a rule she didn't say" in t)
    case("... the old lines that contradict hers are gone (not to judge whether a photo is good; a great photo that breaks the flow stays out; three frames of one laugh)",
         not re.search(r"not to judge whether a photo is good|breaks the flow stays out|three frames of one laugh", t))
    case("... the flow decides the order, not what goes in: a best photo that jolts gets a better place, not left out",
         "The flow decides the order, not what goes in" in t and "rather than leaving it out" in t)
    case("... their own order is always kept on the page; yours never replaces it", "yours never replaces it" in t)
    case("... nothing of a client's: no name from her example shoot, no numbers from her example picks",
         not re.search(r"Hannah|\b(41|42|45|46|49|51)\b", t))
    them = [ln for ln in t.splitlines() if "Nicole" not in ln]           # Nicole is "she"; the photographer never is
    case("... the photographer is never 'she' or 'he'", not any(re.search(r"\b(she|he|his|hers?)\b", ln) for ln in them),
         [ln[:120] for ln in them if re.search(r"\b(she|he|his|hers?)\b", ln)][:3])


# ---------- 5. the reel skill ----------

def check_reel_skill():
    t = read(REEL / "SKILL.md")
    step2 = t.split("## Step 2", 1)[-1].split("\n## ", 1)[0]
    case("Step 2 reads curating.md and chooses by Nicole's rule: the best photos on their own merit",
         "<shared>/curating.md" in step2 and "What goes in is Nicole's rule (Nov 6): the best photos, on their own merit" in step2)
    case("... stories in the shoot, a shortlist each, close calls side by side with the strip, a handful of larger looks at most",
         all(x in step2 for x in ("Find the stories in the shoot", "shortlist the strongest frames for each", "settle the close calls side by side",
                                  "`--picks 7,8,9`, draws them in a row", "a handful at most")))
    case("... the order is the Assistant's flow rules, the emotion builds and comes back down, tall photos first",
         "The order is the Assistant's flow rules" in step2 and "let the emotion build, then come back down" in step2 and "tall photos first" in step2)
    case("... about 8 to 14 is a guide, not a rule", "About 8 to 14 photos is a guide, not a rule" in step2 and "Pick 8 to 14" not in t)
    case("... the '-' mark is for a detail in a run, not frames of one laugh", "a detail in a run" in step2 and "frames of one laugh" not in t)
    case("... their own order is kept on the page", "Their own order is always kept on the page; yours never replaces it." in step2)
    foot = t.split("## Behind-the-scenes footage", 1)[-1].split("\n## ", 1)[0]
    case("her footage rules 4 to 6: never a photo because of a clip, never limited to the footage's setting, the same picks with or without",
         "Never choose, leave out or move a photo because of a clip" in foot and "never limit the photos to the setting the footage shows" in foot
         and "the same with footage or without" in foot)
    case("the rules: nothing is ever left out to fit, not a photo, not a clip",
         "**Nothing is ever left out to fit** (Nicole, Nov 6): not a photo, not a clip." in t)


# ---------- 6. the hello, the home page, the kit and Canva ----------

def check_doors():
    hello = read(SM / "parts" / "hello.md")
    case("the hello's Make posts explanation names the reel page and the two designers",
         "the reel is made on its own page beside the chat" in hello and "the carousel and the stories each have a designer" in hello)
    kitp = read(SM / "parts" / "post-kit.md")
    case("post-kit.md: plain stories are the kit's, the stories designer is theirs from the Stories card",
         "plain stories (one photo each)" in kitp and "they make in the stories designer, from the kit page's Stories card" in kitp)
    case("post-kit.md: 'show my post kit' loads the kit page in the pane through home.py url", '## "Show my post kit"' in kitp and "home.py url" in kitp.split('## "Show my post kit"', 1)[1])
    case("post-kit.md: the kit's reel and carousel counts are guides", "about 8 to 14, a guide, not a rule" in kitp and "about 5 to 8, a guide" in kitp)
    photos = read(SM / "parts" / "photos-in.md")
    case("photos-in.md: 'make the reel for the park shoot' goes to the pick and the reel page", "then the reel page, where they add the song" in photos)
    canva = read(SM / "parts" / "canva.md")
    case("canva.md: with no story template, the stories designer is offered beside a Canva template",
         "offer both ways to finished stories" in canva and "stories designer" in canva.split("No story template set", 1)[-1][:600])
    arr = read(SM / "parts" / "arrange.md")
    single = arr.split('**A single post: "make a single post".**', 1)[-1].split("\n\n", 1)[0]
    case("arrange.md: a single post is one slide in the designer, with the page's own words for the buttons",
         "One slide on its own is a single post" in single and 'design.py open "<kit>"' in single and all(
             x in single for x in ("+ New design", "Blank", "Slides", "Save slides", "Singles folder")))
    page = read(SCRIPTS / "design_page.py") + read(SCRIPTS / "design_js_designs.py")
    case("... and those words are on the designer page", all(x in page for x in ("+ New design", "'Blank'", '"Slides"', "One slide on its own is a single post.")))
    readme = read(PLUGIN / "README.md")
    case("the plugin's README: make a reel opens the reel page; make my stories opens the stories designer",
         "opens the reel page beside the chat" in readme and "**make my stories** | Opens the stories designer" in readme)


def main():
    for fn in (check_search, check_table, check_descriptions, check_curating, check_reel_skill, check_doors):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            case(f"{fn.__name__} ran to its end", False, f"{type(e).__name__}: {e}")
    failed = _results.count(False)
    print(f"\n{len(_results) - failed} of {len(_results)} passed." + (f" {failed} FAILED." if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
