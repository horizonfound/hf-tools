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
  * nothing of a client's in the text this stage wrote;
  * the words (Nicole's v20, stage 5 of the v21 build): each of the three lines the words page hands out, and a
    caption or hooks asked for in their own words, leads through the core's table to parts/words.md; that part
    has the interview order, answers through a file, the Brand Homebase read in full and never another brand's
    file, the goal first, a carousel a caption only, no words for stories, no hashtags and no short caption; and
    no instruction still describes the old way of writing a caption or a hook.
;
  * the talking reel (Nicole's v23 and v24, stage E of the v24 build): each of the three lines the talking reel
    page hands out, and "set up talking reels", has one row in the core's table, to parts/talking-reel.md; that
    part exists and holds her two rule blocks word for word, every command it names, --replace only after asking,
    the place step sent to shared/curating.md, never a zoom, a speed or a caption word, never "ready" before
    status says so, the setup talk and Apple's window only with their yes, files in the scratchpad, never a click
    on a system box, and what is not proven; both descriptions stay within 1,024 characters with the new trigger
    words in the reel skill's only; the reel skill no longer says "no zooms" without saying it is about a photo
    reel; the reel page's third card is named in parts/arrange.md; the PC gap is in parts/on-a-pc.md and the PC
    guide in the same words; and parts/where-things-live.md names every file the talking reel keeps, by the
    scripts' own names. (For this last part the talking scripts are imported, only to read their words.)

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
    case("... step 7, for a reel: mark its rhythm fully (Nicole, Nov 10): a third Longer, a quarter Quicker, the rest plain, "
         "never three of a kind in a row, a Longer after a few quick ones; the photographer's own marks win",
         all(x in steps for x in ("mark its rhythm: every reel, fully (Nicole, Nov 10)", "about a third of the photos", "about a quarter",
                                  "**The rest plain.**", "never three Longers or three Quickers in a row",
                                  "a Longer comes after a few quick ones", "and theirs win", "A carousel has no marks"))
         and "Aurora" not in t)
    case("... step 7: On every beat's lengths are aims; the song's hits still decide (review, Nov 11)",
         "a Longer photo aims for about three beats" in steps and "those are aims, and the song's hits still decide" in steps
         and "a Longer photo holds about three beats" not in t)
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
    case("... every reel is marked fully (Nicole, Nov 10): about a third Longer, about a quarter Quicker, the rest plain",
         "Mark every reel's rhythm, fully (Nicole, Nov 10)" in step2 and "on about a third of the photos" in step2
         and "on about a quarter" in step2 and "**The rest plain.**" in step2 and "Most photos get no mark" not in t)
    case("... what gets Longer and what gets Quicker, in her words; never three of a kind in a row; not frames of one laugh",
         all(x in step2 for x in ("the scroll-stopper you open on", "the emotional peaks", "a wide frame with a lot to take in", "and the closer",
                                  "details (shoes, hands)", "quick fun bursts", "the middle of a fast run",
                                  "never three Longers or three Quickers in a row", "a Longer comes after a few quick ones"))
         and "frames of one laugh" not in t)
    step4 = t.split("## Step 4", 1)[-1].split("\n## ", 1)[0]
    case("Step 4: On every beat has rhythm (her v22): Longer about three beats, Quicker one, plain one or two, never one beat each",
         "On every beat has rhythm (Nicole, Nov 10)" in step4 and "about three beats" in step4 and "never one beat each" in step4
         and "planned so that three one-beat plain photos don't come in a row" in step4)
    # The made reel does not always keep the plan (same in her engine: the song's hits and the bar can pull a plain
    # opener or a Longer photo to one beat), so the words say "aims" and never promise it (review, Nov 11).
    case("... and those lengths are aims, not promises: a Longer or the opener can land on one beat, one-beat photos can fall together",
         "**Those are aims, not promises.**" in step4 and "a Longer photo or a plain opener lands on one beat" in step4
         and "three or four one-beat photos fall together" in step4 and "never tell them it can't happen" in step4
         and "never three one-beat plain photos in a row" not in t and "(two to four, wherever the song hits)" not in t)
    case("... a reel pick is fully marked wherever it is saved, the post kit's kit.py picks --reel included",
         "**This holds wherever a reel pick is saved**, the post kit's `kit.py picks --reel` included" in step2
         and "`--reel 7+,2,11-,4,9+`" in step2)
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
    arr = read(SM / "parts" / "arrange.md")
    case("arrange.md: a reel pick goes to the page fully marked (Nicole, Nov 10), and the page keeps the marks that are on it",
         "about a third Longer, about a quarter Quicker, the rest plain, never three Longers or three Quickers in a row" in arr
         and "**Your marks and theirs.**" in arr and "the page keeps what is on it, marks and all" in arr)
    case("arrange.md: fresh marks show on an order they never changed, and never over marks they set (the whole-build fix round)",
         "**An order they never changed takes your new marks**" in arr and "**An order they marked themselves keeps theirs**" in arr
         and "reel_earlier" in read(SCRIPTS / "kit.py") and "claude_earlier" in read(SCRIPTS / "reel_page.py"))
    case("arrange.md: On every beat's lengths are aims, not promises (the song's hits still decide)",
         "a Longer photo aims for about three beats" in arr and "Those are aims, not promises" in arr
         and "never that it can't happen" in arr and "a Longer photo holds about three beats" not in arr)
    kitp = read(SM / "parts" / "post-kit.md")
    case("post-kit.md: plain stories are the kit's, the stories designer is theirs from the Stories card",
         "plain stories (one photo each)" in kitp and "they make in the stories designer, from the kit page's Stories card" in kitp)
    case("post-kit.md: 'show my post kit' loads the kit page in the pane through home.py url", '## "Show my post kit"' in kitp and "home.py url" in kitp.split('## "Show my post kit"', 1)[1])
    case("post-kit.md: the kit's reel and carousel counts are guides", "about 8 to 14, a guide, not a rule" in kitp and "about 5 to 8, a guide" in kitp)
    # the design preview on the kit's cards (Nicole's v24, section 7; the stage G fix round): the assistant is told
    # what the picture is, in the kit page's own two lines
    kitsrc = read(SCRIPTS / "kit.py")
    flatk, flata = re.sub(r"\s+", " ", kitp), re.sub(r"\s+", " ", arr)
    pv = tuple(re.search(r'"%s": "([^"]+)"' % k, kitsrc).group(1).replace("{name}", "<name>") for k in ("preview_of", "preview_stories"))
    case("post-kit.md says what the small picture on a card is before anything is saved, in the kit page's own two lines, and that Add to my queue stays locked",
         all(('"' + x + '"') in flatk for x in pv) and "Add to my queue stays locked, until they press Save slides (Save stories)" in flatk, pv)
    case("arrange.md says the same where it says which slides count as the carousel", all(('"' + x + '"') in flata for x in pv) and "nothing to queue until Save slides" in flata)
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


# ---------- 7. the words: one way to write a caption and hooks (Nicole's v20) ----------

OLD_WAY = [
    # (what it is, a pattern that must not be in any instruction)
    ("captions written as part of making a kit", r"kit\.py words \"<kit>\" --file"),
    ("a captions file handed to the photographer", r"Captions and hooks\.txt"),
    ("hooks written five at a time, in the reel skill", r"write five short options"),
    ("hooks written from what is seen in the photos", r"hook options for the on-screen text, based on what it sees"),
    ("ten to twenty hooks", r"offers ten to twenty hook"),
    ("three hooks of different kinds", r"three hooks|hooks \(three"),
    ("a hashtags question or hashtags in a draft", r"(?i)\b(?:ask|add|write|their) (?:for )?(?:their )?hashtags\b(?! question)"),
    ("a short caption being written", r"(?i)\b(?:and|write|with) a short caption\b"),
    ("story lines written by the Assistant", r"(?i)\bwrite (?:the )?story lines\b"),
    ("the caption written from the photos", r"(?i)captions? (?:written )?from (?:what is in )?the photos"),
]


def check_words():
    core = read(SM / "SKILL.md")
    rows = table_rows(core)
    part_path = SM / "parts" / "words.md"
    case("parts/words.md exists", part_path.is_file())
    part = read(part_path) if part_path.is_file() else ""
    flat = re.sub(r"\s+", " ", part)
    # the page's own lines, read from the page, so a change there is caught here
    page = read(SCRIPTS / "words_page.py")
    lines = {k: re.search(r'"%s": "([^"]+)"' % k, page) for k in ("talk_line", "write_line", "polish_quoted")}
    case("the words page still hands out its three lines", all(lines.values()), [k for k, v in lines.items() if not v])
    for k, m in lines.items():
        if not m:
            continue
        line = m.group(1).strip("“”").replace("{short}", "<shoot>")
        for piece in ("reel", "carousel"):
            said = line.replace("{piece}", piece)
            lead = said.rsplit(" ", 1)[0]                     # e.g. 'Ask me about the <shoot>'
            hit = [r for r in rows if ('"' + said + '"') in r.split(" | ")[0]
                   or (('"' + lead + ' reel"') in r.split(" | ")[0] and "(or carousel)" in r.split(" | ")[0])]
            case(f'exactly one row answers "{said}"', len(hit) == 1, len(hit))
            if hit:
                named = re.findall(r"`([^`]+\.md)`", hit[0].split(" | ", 1)[1])
                case("... and it sends Claude to parts/words.md and nowhere else", named == ["parts/words.md"], named)
        case(f'parts/words.md names the line "{line.replace("{piece}", "reel")}"', ('"' + line.replace("{piece}", "reel") + '"') in part)
    for phrase in ('"write a caption for the beach reel"', '"I need hooks"', '"redo the captions"'):
        hit = [r for r in rows if phrase in r.split(" | ")[0]]
        case(f"exactly one row answers {phrase}, and it is the words part",
             len(hit) == 1 and re.findall(r"`([^`]+\.md)`", hit[0].split(" | ", 1)[1]) == ["parts/words.md"], len(hit))
    case("no other row of the core's table still takes captions", not [r for r in rows if re.search(r"\bcaptions?\b", r.split(" | ")[0]) and "parts/words.md" not in r])
    d = re.search(r"^description: (.*)$", core, re.M).group(1)
    case("studio-manager's description names write my words", "write my words" in d)

    # the commands, as words.py has them
    for cmd in ("ask", "answer", "show", "draft", "carry"):
        case(f"words.md names words.py {cmd}", re.search(r"words\.py %s\b" % cmd, part))
    wpy = read(SCRIPTS / "words.py")
    case("... and words.py has each of them", all(('"%s"' % c) in wpy for c in ("ask", "answer", "show", "draft", "carry")))
    case("words.md: what they said goes through a file, never the command line",
         "**Anything they said goes through a file, never the command line.**" in part and "--file" in part and "--text " not in part)
    keys = re.findall(r'^\{"(\w+)":', part, re.M)
    case("words.md's example files use only the names words.py takes",
         set(keys) <= {"about", "who", "who_text", "where", "purpose", "purpose_text", "notes", "caption"}
         and {"about", "who", "who_text", "where", "purpose", "purpose_text", "notes", "caption"} <= set(keys), keys)
    for name, group in (("who", "WHO"), ("where", "WHERE"), ("purpose", "PURPOSE")):
        m = re.search(r"^%s = \{(.*)\}" % group, wpy, re.M)
        buttons = re.findall(r'"(\w+)":', m.group(1)) if m else []
        case(f"words.md names every button words.py takes for {name} ({', '.join(buttons)})",
             buttons and all(("`%s`" % b) in part for b in buttons), buttons)

    # the interview
    order = ["1 the shoot", "1b whether to use the people's names", "2 who they're trying to reach", "2b tell me about them",
             "2c, reels only, feed or trial reel", "3 what the post is for", "3b the follow-up to that", "4 anything to include or leave out"]
    at = [flat.find(x) for x in order]
    case("words.md: the interview order, with 1b, 2b, 2c and 3b", all(a >= 0 for a in at) and at == sorted(at), at)
    case("... which is the order words.py ask prints", all(x in wpy for x in ("\n  1. Tell me about this shoot", "\n  1b. ", "\n  2. Who are you trying", "\n  2b. ", "\n  2c. ", "\n  3. What is this post", "\n  3b. ", "\n  4. Anything else")))
    case("words.md: one question at a time, each answer saved at once, their words as said",
         "Never two at once" in part and "**Save each answer the moment you have it,**" in part and "**Their words, as they said them.**" in part)
    case("words.md: the follow-ups are always asked; saving notes keeps what was there",
         "**1b, 2b and 3b are always asked**" in part and "**Saving notes replaces notes.**" in part)
    case("words.md: ask, don't guess (a slip of the microphone, a missing detail)", "**Ask, don't guess.**" in part and "Never fill a gap" in part)
    case("words.md: what they said when the kit was made is offered for question 1, saved only on their yes",
         "[Use that] [Let me add to it]" in part and "Never save it there without asking" in part)

    # the writing
    case("words.md: read the Brand Homebase in full, every time, before writing", "**Read their Brand Homebase in full,**" in part and "every time, before you write a word" in part)
    case("words.md: never another brand's file", "**The mistake to avoid: never another brand's file.**" in part and "Never search the computer for one" in part)
    case("words.md: no Homebase found: say so and ask; the fallback until the brand interview is in setup",
         'If `show` says "No Brand Homebase found"' in part and "No Brand Homebase found" in wpy
         and "That is the fallback until the brand interview is part of setup" in part and "It isn't checked against your brand yet." in part)
    case("words.md: the goal first", "**the goal first**" in part and "Even when they said the offer last, it opens the caption" in part)
    case("words.md: specifics only from them; an invented feeling is an invented fact", "**Specifics come only from them:**" in part and "is an invented fact" in part)
    case("words.md: her hook rules as printed, not pasted again", "her hook rules stand as written" in part and "what the command prints wins" in part
         and "YOU'RE THE EDITOR" not in part and "OPTIMIZE FOR THE GOAL" not in part)
    case("... and words.py still prints them (hers, word for word)", "YOU'RE THE EDITOR (Nicole, Nov 10)" in wpy and "Never describe the shoot as a hook" in wpy)
    case("words.md: a second caption is genuinely different", "The second caption is genuinely different" in part)
    case("words.md: a carousel gets a caption only", "**A carousel:** one caption, and nothing else. No hooks, no cover lines" in part)
    case("words.md: a one-slide carousel is a single post, and its words are the carousel's", "**A single post** is a one-slide carousel, and its words are the carousel's" in part)
    case("words.md: no words for stories", "**Stories get no words from you.**" in part)
    case("words.md: no hashtags, no short caption", "**Never hashtags, and never a second, short caption**" in part)
    case("words.md: polishing never replaces their caption", "**Never replace it and never add a fact.**" in part and '{"caption": "..."}' in part)
    case("words.md: each ends with one line that it is on the page", all(x in part for x in (
        '"That\'s all on the page."', '"Your caption and ten hooks are on the page. Pick the hooks you love there."',
        '"Your caption is on the page."', '"Your polished caption is on the page, above your own."')))
    case("words.md: new hooks clear their picks, and it says so", "**Saving any change to the hooks clears their picks on the page,**" in part)
    case("words.py show marks the hooks they picked (canva.md and the reel skill lean on it)", "<- picked" in wpy
         and "<- picked" in read(SM / "parts" / "canva.md") and "<- picked" in read(REEL / "SKILL.md"))
    case("words.md has nothing of a client's in it", not re.search(r"Hannah|Laguna|Nicole Hill|mommy|\$400|December 4", part), re.findall(r"Hannah|Laguna|Nicole Hill|mommy|\$400|December 4", part))

    # the fix round (Nov 11): things a cold read got wrong
    row2 = [r for r in rows if '"I need hooks"' in r.split(" | ")[0]]
    case("the words row also takes hashtags, a short caption and what a story should say",
         row2 and all(x in row2[0].split(" | ")[0] for x in ("hashtags", "a short caption", '"what should my story say"')))
    case("words.md: hashtags, a short version, story and slide words asked for in their own words", '"Write me some hashtags"' in part and '"what should my story say?"' in part)
    case("words.md: the Brand Homebase file is named exactly, as words.py names it",
         "named exactly `brand-homebase.md`" in part and 'HOMEBASE = "brand-homebase.md"' in wpy and "text file called brand-homebase," not in part)
    case("... and words.py show prints where it would be read from", "no other name or ending" in wpy)
    case("words.md: a skip saves nothing, and a later pass offers the open follow-up once more",
         "**A skip saves nothing.**" in part and "**On a later pass**" in part and 'offer it once more, lightly' in part)
    case("words.md: the other piece's answers are offered before the interview starts again",
         "**If nothing is answered for this piece but the other one is,**" in part and "[Use what I said for the reel] [Ask me again]" in part
         and "Nothing is answered for the {piece} yet, but the {other} is" in wpy)
    case("words.md: a closing thank-you is not a rule for every caption",
         "**How a caption closes is theirs:**" in part and "when names are in, a thank-you" not in part and "Then thanks to the client by name" not in part)
    case("words.md: polishing a caption said in the chat doesn't claim their own box", "and no word about their own" in part and "or to say it here." not in part)
    arr = read(SM / "parts" / "arrange.md")
    case("arrange.md no longer points to hooks or story lines on the kit page",
         "story lines on the kit page" not in arr and "hooks and caption for this shoot are on the kit page" not in arr
         and arr.count("(`parts/words.md`)") >= 2)
    told = [f"{rel(p)}:{i}" for p in instruction_files() for i, ln in enumerate(read(p).splitlines(), 1)
            if re.search(r"kit\.py told\b(?!.*--text-file)", ln) or re.search(r'kit\.py told [^`]*--text "', ln)]
    case("what they said about a shoot always goes through a file (kit.py told --text-file)", not told, told)

    # the neighbours
    kitp = read(SM / "parts" / "post-kit.md")
    step4 = kitp.split("4. **The words are not written here.**", 1)[-1].split("\n5. ", 1)[0]
    case("post-kit.md step 4 is a short pointer to the words part", "read `parts/words.md` in full" in step4 and len(step4) < 1200 and "words.py answer" not in step4, len(step4))
    case("post-kit.md: the voice question is a stand-in until the brand interview is in setup", "stays only until the brand interview is part of setup" in kitp)
    case("post-kit.md: what they said at the kit's start is never copied into a words page by itself", "never copied into a words page by itself" in kitp)
    case("canva.md: the cover's hook is one they picked, never one Claude chose", "a hook they chose, never one you chose" in read(SM / "parts" / "canva.md"))
    case("the reel skill: a hook comes from the words page, never written in the reel step",
         "Never write hooks here, from the photos, or five at a time" in read(REEL / "SKILL.md") and "parts/words.md" in read(REEL / "SKILL.md"))
    case("hello.md and photos-in.md send captions to the words part", "parts/words.md" in read(SM / "parts" / "hello.md") and "parts/words.md" in read(SM / "parts" / "photos-in.md"))
    for what, pat in OLD_WAY:
        hits = []
        for p in instruction_files():
            for i, ln in enumerate(read(p).splitlines(), 1):
                if re.search(pat, ln):
                    hits.append(f"{rel(p)}:{i}")
        case(f"no instruction still has the old way: {what}", not hits, hits)
    # whoever tells Claude how to write a caption or hooks points at the words part (or is it)
    stray = []
    for p in instruction_files():
        if p.name in ("words.md", "playbook.md", "guardrails.md", "voice-of-the-assistant.md"):
            continue
        for i, ln in enumerate(read(p).splitlines(), 1):
            if re.search(r"words\.py (?:ask|answer|draft|carry)\b", ln):
                stray.append(f"{rel(p)}:{i}")
    case("the words commands that save are told in one place, parts/words.md", not stray, stray)
    case("the playbook's hooks and captions sections give way to the words part", "they win.**" in read(PLUGIN / "shared" / "playbook.md") and "`parts/words.md`" in read(PLUGIN / "shared" / "playbook.md"))


# ---------- 8. the posting queue's part: the panel, the grid photo, posting-day reminders ----------

def check_posting():
    part_path = SM / "parts" / "posting-queue.md"
    part = read(part_path)
    flat = re.sub(r"\s+", " ", part).replace("’", "'")
    page = read(SCRIPTS / "posting_queue.py").replace("’", "'")
    rem = read(SCRIPTS / "reminders.py")
    rows = table_rows(read(SM / "SKILL.md"))
    for phrase in ('"remind me to post the beach reel"', '"is my reminder set"', '"show my posting queue"', "\"the beach reel's ready\""):
        hit = [r for r in rows if phrase in r.split(" | ")[0]]
        case(f"exactly one row answers {phrase}", len(hit) == 1, len(hit))
        if hit:
            case("... and it sends Claude to parts/posting-queue.md", "`parts/posting-queue.md`" in hit[0].split(" | ", 1)[1])
    case("the part no longer says the calendar dates are not built", "Not built yet" not in part and "posting dates on their calendar" not in part)
    # the page's own words, read from the page, so a change there is caught here
    said = {
        "the reel's cover line": r"reel_line:'([^']+)'", "the carousel's first-slide line": r"carousel_line:'([^']+)'",
        "Copy caption": r"copy_caption:'([^']+)'", "Copy my hook": r"copy_hook:'([^']+)'", "Open my words": r"open_words:'([^']+)'",
        "Write my words": r"write_words:'([^']+)'", "No caption yet.": r"no_caption:'([^']+)'", "the no-hook line": r"no_hook:'([^']+)'",
        "the can't-find-the-photos line": r"\bcant:'(I can't find[^']+)'",
        "Set a reminder to post": r"RW=\{set:'([^']+)'", "Remind me": r"yes:'([^']+)'", "I'll post it myself": r'no:"([^"]+)"',
        "Which calendar does your phone show?": r"which:'([^']+)'", "What time?": r"what:'([^']+)'",
        "the Mac's say-yes line": r"slow:' ([^']+)'", "I can't reach your Calendar right now.": r"cant:'(I can't reach[^']+)'",
        "Try again": r"again:'([^']+)'", "the trouble line": r"trouble:'([^']+)'", "Change time": r"change:'([^']+)'", "Turn off": r"off:'([^']+)'",
        "Add to my calendar": r"pc_add:'([^']+)'", "Add it again": r"pc_add_again:'([^']+)'", "Take it off my calendar": r"pc_take:'([^']+)'",
    }
    for what, pat in said.items():
        m = re.search(pat, page)
        case(f"the posting page still says: {what}", bool(m))
        if m:
            case(f"... and the part says it the same way: {m.group(1)[:60]}", m.group(1) in flat, m.group(1))
    # every command the part names is one the scripts have
    have = {"posting_queue.py": set(re.findall(r'add_parser\("([a-z-]+)"\)', page)) | {"ready", "unready", "posted", "skip"},
            "reminders.py": set(re.findall(r'add_parser\("([a-z-]+)"\)', rem))}
    named = re.findall(r"`(?:python3 <scripts>/)?(posting_queue\.py|reminders\.py) ([a-z-]+)", part)
    bad = [f"{f} {c}" for f, c in named if c not in have[f]]
    case("every posting_queue.py and reminders.py command the part names exists", named and not bad, bad)
    for c in ("status", "calendars", "sync", "open", "calendar"):
        case(f"the part names reminders.py {c}", ("reminders.py", c) in named)
    # the chat cannot set a reminder: there is no such command, and the part says so (if one is ever added, say it here).
    # Choosing the calendar again is the one thing the chat can do (reminders.py calendar <name>, Nov 11).
    setter = [c for c in have["posting_queue.py"] | have["reminders.py"] if c in ("remind", "set", "on", "off", "time")]
    case("there is still no command that sets a reminder, its time, or turns it off", not setter, setter)
    case("reminders.py has the command that changes the calendar, and the part tells it: the names, their choice, then the command",
         "calendar" in have["reminders.py"] and "**Changing the calendar**" in flat and 'reminders.py calendar "<the name, exactly as listed>"' in flat
         and "never choose for them" in flat and "Changing the calendar afterwards is not built" not in flat and "I can't change which calendar yet" not in flat)
    case("the part says the chat cannot set one, and where the button is", "The chat cannot set one." in flat and "Click the beach reel in your grid" in flat and "Set a reminder to post" in flat)
    case("reminders are offered, never assumed, each post its own time", "Offered, never assumed." in flat and "each post gets its own" in flat)
    case("never say a reminder is set before status says so", "Don't say a reminder is set until `reminders.py status` says so." in flat)
    case("the Mac's permission question: say yes, and where to turn it back on",
         "Press Allow on both" in flat and "System Settings, Privacy & Security, Automation" in flat
         and "System Settings, Privacy & Security, " in re.sub(r'"\s+"', "", rem) and "Automation" in rem)
    case("the part says what was proven on the real Calendar and what was not", "What is proven (Dustin's Mac, Nov 11" in flat and "Not tried: saying Don't Allow" in flat)
    case("a calendar that is gone sends them to choosing another, not to a dead end", "they choose another" in flat and "there is no way to choose another yet" not in flat)
    case("the page still never offers the calendar question once one is chosen (else the part's line is wrong)",
         "mode==='cal'||(mode==='time'&&!pc&&!R.calendar)" in page and page.count("'cal')") == 0)
    case('"reminders not updated": the queue is right, do not run the command again, then status and sync',
         "(reminders not updated: ...)" in flat and "Don't run the queue command again" in flat and "reminders.py sync" in flat
         and "(reminders not updated: " in page and "(reminders not updated: " in rem)
    case("a PC: a calendar file they add themselves, and never 'your reminder is set'",
         "a calendar file" in flat and 'Never tell a PC photographer "your reminder is set"' in flat and "None of it has been tried on a real PC yet." in flat)
    case("a PC: the alert may not come through, said plainly", "The alert may not come through." in flat and "Google Calendar" in flat)
    case("a PC: the file lines the commands print are in the part as printed",
         "waiting to be opened in your calendar app. Nothing changes on your calendar until then." in flat
         and "waiting to be opened in your calendar app. Nothing changes on your calendar until then." in page
         and "Nothing is waiting to be opened." in flat and "Nothing is waiting to be opened." in rem)
    case("ready to post normally comes from Add to my queue, which needs its caption; offer the words",
         "Add to my queue" in flat and "does not check for a caption" in flat and "don't mark it ready silently" in flat and "`parts/words.md`" in flat)
    case("the panel's words come from the words page; changes go through parts/words.md",
         "nothing is written or changed in the posting queue" in flat and "that is `parts/words.md`, every time" in flat)
    case("two shoots with nearly the same name: both can be in the queue, never guess",
         "Both can be in the posting queue" in flat and "Never guess which of the two" in flat
         and "could mean more than one" in flat and "could mean more than one" in page and "def kit_sid" in page)
    case("the old refusal line is nowhere in the scripts (else the part must say what to do about it)",
         not any("nearly the same name" in read(f) for f in SCRIPTS.glob("*.py")))
    stray = []
    for q in instruction_files():
        if q.name == "posting-queue.md":
            continue
        for i, ln in enumerate(read(q).splitlines(), 1):
            if re.search(r"reminders\.py (?:status|sync|calendars|calendar|open)\b", ln):
                stray.append(f"{rel(q)}:{i}")
    case("the calendar reminder commands are told in one place, parts/posting-queue.md", not stray, stray)


def check_whole_build():
    """The whole-build fix round (Nov 11): three promises Nicole ruled out, the PC's honest list, where things live."""
    import json
    # Nicole, v20: never say on a page that the words "sound like you". The Assistant shapes what they said like an editor would.
    banned = re.compile(r"sounds? like you|in your voice|the way you write", re.I)
    home = read(SCRIPTS / "home.py")
    card = re.search(r'\("posts", "Make posts from a shoot",\s*"([^"]+)"', home)
    case("the home page's Make posts card promises no captions that 'sound like you' or are 'written the way you write'",
         bool(card) and not banned.search(card.group(1)) and "captions" in card.group(1), card.group(1) if card else "card not found")
    case("... and names the kit's three pieces (no 'single photos': a single post is a one-slide carousel)",
         bool(card) and "single photos" not in card.group(1) and all(w in card.group(1) for w in ("a reel", "a carousel", "stories")))
    plug = json.loads(read(PLUGIN / ".claude-plugin" / "plugin.json"))["description"]
    market = json.loads(read(ROOT / ".claude-plugin" / "marketplace.json"))["plugins"][0]["description"]
    case("the plugin's one-line description promises no captions 'in your voice'", not banned.search(plug), plug)
    case("... and the marketplace's description is the same line, word for word", plug == market)
    kit_part = read(SM / "parts" / "post-kit.md")
    said = [m for m in re.findall(r'"([^"\n]+)"', kit_part) if banned.search(m)]
    case("no line the Assistant says in parts/post-kit.md promises words that 'sound like you' (only the rule itself names the phrase)",
         said == ["sound like you"], said)
    pages = [f.name for f in sorted(SCRIPTS.glob("*.py")) if re.search(r"captions? (?:that )?sounds? like you|captions in your voice|captions written the way you write", read(f))]
    case("no page script promises captions that sound like them", not pages, pages)
    # the PC's "what can't you do" list names reminders, and the PC part points at the reminder section
    pc = re.sub(r"\s+", " ", read(SM / "parts" / "on-a-pc.md"))
    lst = pc.split('## "What can\'t you do on a PC?"', 1)[-1].split("## ", 1)[0]
    case("on a PC, 'what can't you do' names posting-day reminders: a calendar file added by hand, again after any change, check the alert",
         "Posting-day reminders" in lst and "calendar file" in lst and "again after any change" in lst and "alert" in lst)
    case("the PC part points at the reminder section and never names a reminders command itself",
         "On a PC: a calendar file they add themselves" in pc and "`parts/posting-queue.md`" in pc and "`parts/words.md`" in pc)
    guide = re.sub(r"\s+", " ", read(ROOT / "docs" / "SETUP-GUIDE-PC.md")) if (ROOT / "docs" / "SETUP-GUIDE-PC.md").is_file() else None
    if guide is not None:        # the guide is not part of the installed plugin; checked where the project is
        case("the PC setup guide's 'Not on a PC yet' list names reminders too",
             "Posting-day reminders" in guide.split("### Not on a PC yet", 1)[-1][:2500])
    # where things live: the new records
    where = re.sub(r"\s+", " ", read(SM / "parts" / "where-things-live.md"))
    words_py, rem_py = read(SCRIPTS / "words.py"), read(SCRIPTS / "reminders.py")
    for name, src in (("post-words.json", words_py), ("post-words.prev.json", words_py), ("brand-homebase.md", words_py),
                      ("made.json", rem_py), ("state.json", rem_py), ("event_uid", rem_py), ("event_sig", rem_py), ("event_cal", rem_py)):
        case(f"where-things-live names {name}, and the script still uses that name", f"`{name}`" in where and f'"{name}"' in src)
    case("where-things-live names the reminders' folder, posting.json's reminder fields and the log",
         all(w in where for w in ("`reminders/`", "`posting.json`", "`remind_on`", "`remind_time`", "`logs/reminders.log`", "`last.json`")))


# ---------- the talking reel (Nicole's v23 and v24, stage E of the v24 build) ----------

def check_talking():
    # The scripts are only imported, to read their own words and names (nothing of theirs is run). The Assistant's
    # own folder is pointed at a scratch folder first, so nothing can land in the real one.
    import os
    import tempfile
    import atexit
    import shutil
    scratch = tempfile.mkdtemp(prefix="skill-text-check-")
    atexit.register(shutil.rmtree, scratch, True)
    os.environ["STUDIO_HOME"] = scratch
    os.environ["TALKING_TRANSCRIBER"] = "none"
    os.environ["TALKING_NO_REAL"] = "1"
    sys.path.insert(0, str(SCRIPTS))
    sys.path.insert(0, str(REEL / "scripts"))
    import talking            # her two rule blocks, word for word (tests/talking_rec_check.py holds them to her file)
    import talking_page
    import talking_rec
    import this_computer
    import reel_page
    core = read(SM / "SKILL.md")
    rows = table_rows(core)
    part_path = SM / "parts" / "talking-reel.md"
    case("parts/talking-reel.md exists", part_path.is_file())
    part = read(part_path) if part_path.is_file() else ""
    flat = re.sub(r"\s+", " ", part)
    quoted = re.sub(r"\s+", " ", re.sub(r"(?m)^> ?", "", part))       # with the quote marks of a quoted block taken off

    # the three lines the page hands out, read from the page, so a change there is caught here
    W = talking_page.WORDS
    for k in ("cut_line", "place_line", "cut_place_line"):
        said = W[k].replace("{short}", "<shoot>")
        hit = [r for r in rows if ('"' + said + '"') in r.split(" | ")[0]]
        case(f'exactly one row answers the page\'s line "{said}"', len(hit) == 1, len(hit))
        if hit:
            named = re.findall(r"`([^`]+\.md)`", hit[0].split(" | ", 1)[1])
            case("... and it sends Claude to parts/talking-reel.md and nowhere else", named == ["parts/talking-reel.md"], named)
        case(f'the part names the line "{said}"', ('"' + said + '"') in part)
    hit = [r for r in rows if '"set up talking reels"' in r.split(" | ")[0]]
    case('the line the page tells them to say when the Mac needs setting up ("set up talking reels") has its row too',
         len(hit) == 1 and "parts/talking-reel.md" in hit[0] and "Tell your assistant: set up talking reels." in talking_rec.line_for("no_tools"))
    case("the three lines lead nowhere else: no other row of the table takes a talking reel",
         not [r for r in rows if "talking" in r.split(" | ")[0].lower() and "parts/talking-reel.md" not in r])

    # the descriptions: no new trigger words in the core's (it has no room), they are in the reel skill's
    d_core = re.search(r"^description: (.*)$", core, re.M).group(1)
    reel = read(REEL / "SKILL.md")
    d_reel = re.search(r"^description: (.*)$", reel, re.M).group(1)
    case("the core's description is as it was (no talking words squeezed into its last 8 characters)", "talking" not in d_core.lower() and len(d_core) <= 1024, len(d_core))
    case("the reel skill's description has the talking reel's trigger words, within 1,024 characters (%d)" % len(d_reel),
         len(d_reel) <= 1024 and all(x in d_reel for x in ("cut my talking reel", "place the photos in my talking reel", "set up talking reels", "make a talking reel")))
    case("...and nothing in it a strict reader stops on (a colon followed by a space, an angle bracket)", ": " not in d_reel and "<" not in d_reel and ">" not in d_reel)
    case("the reel skill points to the part near Steps 1 and 2, before Step 1",
         "<assistant>/parts/talking-reel.md" in reel and 0 < reel.find("## A talking reel is its own thing") < reel.find("## Step 1:")
         and all(('"' + W[k].replace("{short}", "<shoot>") + '"') in reel for k in ("cut_line", "place_line", "cut_place_line")))

    # rule 2 of the reel skill (decision 2b.3): "no zooms" only with its scope
    m = re.search(r"(?m)^2\. \*\*Every frame is theirs\.\*\*.*$", reel)
    rule2 = m.group(0) if m else ""
    case("the reel skill's rule 2 says no zooms or motion \"in a photo reel\", and names the talking reel's three moves as the photographer's own",
         "**In a photo reel**" in rule2 and "no zooms or motion" in rule2.split("**In a photo reel**")[-1].split("**A talking reel**")[0]
         and all(x in rule2 for x in ("Punch in", "Slow zoom", "a faster speed", "the photographer presses", "You never add one")), rule2[:300])
    bare = [ln[:140] for f in instruction_files() for ln in read(f).splitlines()
            if re.search(r"\bno zooms?\b", ln, re.I) and "photo reel" not in ln.lower()]
    case("nothing Claude reads says \"no zooms\" without saying it is about a photo reel", not bare, bare)
    case("rule 2 still keeps what nothing changes: every frame theirs, hard cuts, no transitions, no effects, nothing generated",
         all(x in rule2 for x in ("Every frame is theirs", "Hard cuts", "no transitions", "no effects", "no generated anything")))

    # her two rule blocks are the rules, word for word
    for name, block in (("cutting", talking.RULES), ("photo", talking.PHOTO_RULES)):
        want = re.sub(r"\s+", " ", block).strip()
        case(f"Nicole's {name} rules are in the part word for word, as the engine prints them", want in quoted, want[:80])
    case("the part says the commands print the rules every time, and to follow what they print",
         "every time" in flat and "`show` prints Nicole's cutting rules and `photos` prints her photo rules" in flat and talking_rec.cmd_show and talking_rec.cmd_photos)

    # each command the part names is one the script takes
    src = read(SCRIPTS / "talking_rec.py")
    cmds = re.findall(r"python3 <scripts>/talking_rec\.py (\w+)", part)
    case("every talking_rec.py command the part names is a command (show, cut, photos, place, status, setup)",
         set(cmds) == {"show", "cut", "photos", "place", "status", "setup"} and all(('"%s"' % c) in src for c in set(cmds)), sorted(set(cmds)))
    case("the part opens the page with talking_page.py open, in the pane, never Chrome",
         'python3 <scripts>/talking_page.py open' in part and hasattr(talking_page, "cmd_open") and "Never Chrome" in part and "mcp__ccd_view__show_pane" in part)
    # talking_page.py open finds the shoot as every other command does (talking_rec.find -> kit.find_kit), so two
    # shoots matching is its exit 1 too; the part once said never to read open's 1 that way
    import inspect
    import kit as kit_for_find
    case("the part says talking_page.py open answers 'more than one shoot' as the other commands do, as the code does",
         "TR.find(a.words)" in inspect.getsource(talking_page.main)
         and "kitmod.find_kit(words)" in inspect.getsource(talking_rec.find)
         and "could mean more than one" in inspect.getsource(kit_for_find.find_kit)
         and "`talking_page.py open` finds the shoot the same way as the others, so it too answers 1 with the line that says the words fit more than one shoot" in flat
         and "`open` answers 1 with a STOP when the shoot isn't in Your Content or its photos couldn't be numbered. Never read those" not in flat
         and 'For `open`, an exit 1 means "more than one shoot" only when its line says so.' in flat)
    case("the part's Saved lines are the commands' own",
         "Saved: 4 cuts. The reel is now 28.4 seconds of talking. The page shows it in a few seconds." in flat
         and 'say(f"Saved: {n} cuts. The reel is now {secs:.1f} seconds of talking. The page shows it in a few seconds.")' in src
         and "Saved: 12 photo stretches, 21 photos. The page shows them in a few seconds." in flat
         and 'say(f"Saved: {n} photo stretches, {m} photos. The page shows them in a few seconds.")' in src)
    case("the part's two STOP lines are the commands' own", ("`STOP: " + talking_rec.THEIR_CUTS.split(". ")[0] + ".`") in part
         and ("`STOP: " + talking_rec.THEIR_PHOTOS.split(". ")[0] + ".`") in part and talking_rec.PHOTOS_PLACED in flat)
    spots = re.search(r"The spots, as the page names them: (.*?)Stretches go in order", flat)
    case("the four spots, in the script's order, each with the page's own name for it",
         bool(spots) and re.findall(r"`(\w+)` is \"([^\"]+)\"", spots.group(1))
         == [(s, W["spot_" + s]) for s in talking_rec.PLACE_SPOTS], spots and spots.group(1)[:200])

    # the things the assistant never does
    for what, words in (
        ("--replace only after asking, every time", ("`--replace` goes on a command only after they have said yes", "Only on Replace them, run the same command again with `--replace`",
                                                     "Only on Replace them all, run again with `--replace`", "ask every time")),
        ("the place step goes to shared/curating.md first", ("Read `curating.md` in the plugin's `shared` folder first, every time", "${CLAUDE_SKILL_DIR}/../../shared/curating.md")),
        ("never a zoom, a speed or a caption word", ("You never add a zoom, never change a speed, and never touch a caption word", "you have no command for them")),
        ("never \"the script is ready\" before status says so", ("Never say the script is ready, or that anything is on the page, before a command says so", "answered from `status`")),
        ("the setup talk: through talking_rec.py setup, Apple's window in the core's own words", ("`talking_rec.py setup --check`", "click Install, then Agree. It takes five to ten minutes. Tell me when it says it's done.")),
        ("xcode-select --install never without their yes", ("**Never run `xcode-select --install` without their yes:**",)),
        ("cuts and stretches through a file in the scratchpad", ("go through a file in your scratchpad", "never on the command line and never in their folders")),
        ("the assistant never clicks a system box", ("You never click it, and you never use computer control on any system box or on System Settings", "The Mac never asks twice".lower())),
        ("an empty cut is a cut", ('{"cut": [], "why": []}',)),
        ("cut first, then place", ("Cut first, all the way through to its Saved line, then place", "Do the whole cut first")),
        ("what is not proven yet", ("## Not proven yet, honestly", "has run on one Mac only", "Three talking reels have been made and opened in CapCut", "Slow zoom looked smooth to Dustin's eye on a steady clip", "Any language but English")),
        ("Make it in CapCut is theirs, on the page", ("You have no command to press it for them", "A project already in CapCut is never changed")),
    ):
        miss = [w for w in words if w not in flat and w not in flat.lower()]
        case(f"the part: {what}", not miss, miss)
    case("(the core's own words for Apple's window are still the ones the part borrows)", "click Install, then Agree. It takes five to ten minutes." in core)
    case("where the Mac's switch is, the part says as the page does", "Privacy & Security, then Speech Recognition" in flat and "Privacy & Security, then Speech Recognition" in talking_rec.line_for("refused")
         and "then Keyboard, and switch on Dictation" in flat and "then Keyboard, and switch on Dictation" in talking_rec.line_for("dictation_off"))
    case("the part reads a stop of the setup from the script's own lines", "Not possible here" in src and "Not possible here" in flat and "Nothing to set up: it is ready." in src
         and "Nothing to set up: it is ready." in flat and "STOP: a talking video is being turned into a script right now" in flat
         and "a talking video is being turned into a script right now" in src)
    case("the part reads status from the script's own lines", all(x in src and x in flat for x in ("No script yet", "No video has been turned into a script yet", "exported again since its script was made")))
    case("the photographer has no gender in the part, and nothing of a client's", not re.search(r"\b(she|he|her|his|him)\b", re.sub(r"Nicole's|her photo rules|\"Her .*?baby\"|her older kids[^\"]*", "", quoted.replace(re.sub(r"\s+", " ", talking.RULES).strip(), "")), re.I)
         , re.findall(r".{30}\b(?:she|he|her|his|him)\b.{30}", re.sub(r"Nicole's|her photo rules", "", quoted.replace(re.sub(r"\s+", " ", talking.RULES).strip(), "")), re.I)[:3])

    # stage E's review: each of these was a finding, and each check fails with its fix taken out
    # the hand test (Nov 12, macOS 27.2): the Mac's box names "Assistant Transcriber" and its buttons are Don't Allow
    # and Allow, so the part and the page name that app and that button, and nothing says the box is unseen
    case("the part names what the Mac's real box names: Assistant Transcriber, and its button, Allow (never \"The Assistant\" as the app the Mac asks about)",
         "Assistant Transcriber may use Speech Recognition" in flat and "The Assistant may use" not in flat and "switch on The Assistant" not in flat
         and "switch on Assistant Transcriber" in flat and "Press Allow in that box" in flat and "Press Allow in that box" in talking_rec.OUR_JOB_WORDS["asking"][0]
         and "press Allow when the Mac asks" in flat and "ay yes in that box" not in flat,
         re.findall(r".{20}(?:The Assistant may use|switch on The Assistant|ay yes in that box).{20}", flat))
    case("the part no longer says nobody has seen the Mac's box, or that turning talking into words has never run",
         "Nobody has seen the Mac's real box" not in flat and "has never run" not in flat and "Nobody has opened a talking reel" not in flat
         and "seen Nov 12 on macOS 27.2" in flat and "Not tried: Don't Allow and the way back" in flat)
    case("the box's \"sent to Apple\" sentence: the part answers as the page does (what the Assistant asks for), and neither says nothing leaves the computer",
         "Speech data from this app will be sent to Apple to process your requests." in flat and "only asks your Mac to do it by itself" in flat
         and "I only ask your Mac to do it by itself" in talking_rec.APPLE_NOTE and "Never say nothing is sent" in flat
         and "nothing leaves" not in flat and not re.search(r"nothing leaves|never sent|is not sent|isn't sent", talking_rec.APPLE_NOTE),
         re.findall(r".{20}nothing leaves.{20}", flat))
    case("the replace-my-cuts question never uses \"mine\" for two people: [Keep my cuts], not [Keep mine]", "[Keep my cuts] [Replace them]" in flat and "[Keep mine]" not in flat)
    case("the part goes by the line, not the exit number, and names setup's and open's own exits as the scripts give them",
         "Go by the line, not the exit number" in flat and "`setup` has exits of its own: 3 with its STOP" in flat and "1 with \"Not possible here\" on a PC" in flat
         and "it also answers 1 with a STOP when the shoot isn't in Your Content" in flat and "never read that 1 as \"more than one shoot\"" in flat
         and re.search(r"being turned into a script right now.*?return 3", src, re.S) and re.search(r"Not possible here.*?\n\s+return 1", src)
         and "Exit 1: the words fit more than one shoot" not in flat)
    case("a second run of the same file asks them nothing, and the part says so (place too)",
         "changes nothing and asks nothing" in flat and "sent again, is the one thing that doesn't stop" in flat and "before you ask them anything" in flat)
    case("a full bring-back is their own work, in the part as in the script", "Bringing back every word you cut is their own work too" in flat)
    case("show and photos both end with the exported-again note, and both flows in the part stop on it",
         flat.count("If it ends with a line starting `NOTE: their talking video was exported again`, stop here") == 2
         and talking_rec.EXPORTED_AGAIN.startswith("NOTE: their talking video was exported again")
         and src.count("EXPORTED_AGAIN +") == 2)
    case("the part quotes the who-places-them question as the page has it: a heading, then the question",
         ('the heading "' + W["who_h"] + '", and under it "' + W["who_say"] + '"') in flat)
    case("arriving from the reel skill, the part's <scripts> and its core are named on both sides",
         "where it writes `<scripts>`, that is `<assistant scripts>` here" in reel and "`<assistant>/SKILL.md`, which you read first if you haven't this conversation" in reel
         and "`<scripts>` is what it calls `<assistant scripts>`" in flat and "read `<assistant>/SKILL.md` first" in flat
         and "../../shared/curating.md`" not in part.replace("${CLAUDE_SKILL_DIR}/../../shared/curating.md`", ""))

    # the door, in what Claude reads
    arr = re.sub(r"\s+", " ", read(SM / "parts" / "arrange.md"))
    case("parts/arrange.md names the reel page's third card in her words, as a link and not a choice",
         ('"' + reel_page.WORDS["foot_talk_b"] + '"') in arr and ('"' + reel_page.WORDS["foot_talk_s"] + '"') in arr
         and "it is a link, not a choice" in arr and "never gets the tick" in arr and "`parts/talking-reel.md`" in arr)

    # the PC: a named gap, in the same words everywhere
    pc = read(SM / "parts" / "on-a-pc.md")
    pcflat = re.sub(r"\s+", " ", pc)
    guide = read(ROOT / "docs" / "SETUP-GUIDE-PC.md")
    case("the PC line is this_computer's own, in the PC part and in the talking part", this_computer.NO_TALKING_PC in pcflat and this_computer.NO_TALKING_PC in flat)
    cant = pc[pc.index('## "What can\'t you do on a PC?"'):pc.index("## The words page and posting-day reminders")]
    case("\"What can't you do on a PC?\" lists talking reels, with the page's PC line whole (plan 2b.5)",
         ("\n> - Talking reels. " + this_computer.NO_TALKING_PC + "\n") in cant + "\n", [ln for ln in cant.splitlines() if "Talking reels" in ln])
    not_yet = guide[guide.index("### Not on a PC yet"):]
    not_yet = not_yet[:not_yet.index("\n> ")]
    case("the PC guide's \"Not on a PC yet\" lists talking reels, marked as wording still theirs", ("- **Talking reels.** " + this_computer.NO_TALKING_PC + " **[") in not_yet
         and "wording is Dustin and Nicole's" in not_yet.split("**Talking reels.**")[1])
    said = re.findall(r"(?m)^> - ([^.]+)\.", cant)
    listed = re.findall(r"(?m)^- \*\*([^*]+?)\.?\*\*", not_yet)
    case("the two lists name the same gaps, in the same order", [re.sub(r"\W+", " ", x).lower().strip()[:18] for x in said] == [re.sub(r"\W+", " ", x).lower().strip()[:18] for x in listed], (said, listed))

    # where things live: every name there is one the scripts use
    live = read(SM / "parts" / "where-things-live.md")
    import talking_make
    import transcribe
    names = {"Talking": talking_rec.TALKING, "talking-job.json": talking_rec.JOB, "talking-job.lock": talking_rec.JOB_LOCK,
             "talking-make-job.json": talking_rec.MAKE_JOB, "talking-make-job.lock": talking_rec.MAKE_JOB_LOCK,
             "talking-make-status.json": talking_rec.MAKE_STATUS, "talking-make.json": talking_make.PLAN_FILE,
             "talking-make.lock": talking_make.MAKE_LOCK, "turn.lock": talking_rec.TALK_TURN, "built.json": transcribe.BUILT,
             "permission.json": transcribe.PERMISSION, "Assistant Transcriber.app": transcribe.APP_NAME}
    case("where-things-live names every talking file, and each name is the script's own (%d)" % len(names),
         not [k for k, v in names.items() if k != v or ("`" + k + "`") not in live], [k for k, v in names.items() if k != v or ("`" + k + "`") not in live])
    for n in ("talking.json", "talking.prev.json", "talking.lock", "talking-words.json", "talking/<video key>/preview.mp4", "talking/facts.json",
              "talking.damaged-<date>-<time>.json", "~/.studio/talking/", "older/", "work/<job>/", "~/.studio/logs/talking.log"):
        case(f"where-things-live names {n}", ("`" + n + "`") in live)
    case("...and the scripts still keep them there", all(x in src for x in ('"talking.json"', "talking.prev.json", "talking.lock", "talking-words.json", "preview.mp4", "facts.json", "talking.damaged-"))
         and str(talking_rec.LOG).replace("\\", "/").endswith("logs/talking.log") and talking_rec.TALK_HOME.name == "talking" and talking_rec.WORK.name == "work")
    case("the part says what status says once they have changed the photos the assistant placed, in status's own words (stage G)",
         "changed on the page since you placed them: ask before replacing them" in flat and "(changed on the page since you placed them: ask before replacing them)" in src)
    # the stage G fix round: the files the first pass left unnamed, and the honest line about a job cut off
    more = {"talking-words.prev.json": talking_rec.WORDS_PREV, "made-again": talking_rec.MADE_AGAIN}
    case("where-things-live names the words as they were before, and the made-again mark, by the script's own names",
         not [k for k, v in more.items() if k != v or ("`" + k + "`") not in live], more)
    for n, has in (("talking-words.lock", '"talking-words.lock"'), ("talking/facts.lock", '"facts.lock"'),
                   ("talking/<video key>/preview.unusable-<date>-<time>.mp4", "preview.unusable-")):
        case(f"where-things-live names {n}, and the scripts still use that name", ("`" + n + "`") in live and has in src + read(SCRIPTS / "reel_page.py"))
    case("where-things-live says the unusable small copy is kept and counts toward the room on the drive", "kept, never deleted; it counts toward the same room on the drive" in live)
    flat_live = re.sub(r"\s+", " ", live)
    case("where-things-live no longer says a job's sound is always removed when the job ends: a job cut off leaves it until the Assistant next sees the job is gone",
         "removed when the job ends. Nothing of the photographer's is kept there" not in flat_live
         and "A job cut off outright (a power cut, a force quit) can't tidy up" in flat_live and "clear_stale_work()" in src.split("def settle(", 1)[1].split("\ndef ", 1)[0]
         and "shutil.rmtree(WORK / jid" in src.split("def _watchdog(", 1)[1].split("\ndef ", 1)[0])
    case("where-things-live says the small copies are kept, and how big they can get", "kept on purpose" in live and "1.3 GB" in live)
    case("where-things-live says the earlier edits and what a --replace replaced are kept", "`earlier`" in live and "`replaced`" in live and "the last 12" in live)


def main():
    for fn in (check_search, check_table, check_descriptions, check_curating, check_reel_skill, check_doors, check_words, check_posting, check_whole_build, check_talking):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            case(f"{fn.__name__} ran to its end", False, f"{type(e).__name__}: {e}")
    failed = _results.count(False)
    print(f"\n{len(_results) - failed} of {len(_results)} passed." + (f" {failed} FAILED." if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
