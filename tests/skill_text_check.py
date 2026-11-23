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
    scripts' own names. (For this last part the talking scripts are imported, only to read their words.);
  * the photographer picks (Nicole's v25, stage H of the v26 build): nothing is picked until they ask; the pasted
    line "Pick my reel photos for <shoot>" is answered with reel_page.py note first, the note followed exactly,
    the pick saved for that reel only; "make my posts" and a new kit only number the photos and open the post
    kit (no pick, no build, no question); the page's own lines are quoted word for word;
  * Posted on the post itself, the Reels card and the path at the top (Nicole's v27, Lane D of the v27 build): the
    Not posted / Posted switch, the posted post in the feed and "that one didn't go out after all" (unposted) are
    in parts/posting-queue.md in the page's own words, the command exists and its printed line is quoted, the
    core's row sends the new lines there; the Reels card's name and its two buttons are quoted from kit.py and no
    part still says "Reel card"; the path (Home › Beach post kit, › Captions) is told in the kit part and the
    words part from look.py's and words_page.py's own words, and the posting queue page still keeps Back to home;
    "What's a post kit?" is answered with her Make posts paragraph, whole, when her pack is here to compare;
    where-things-live.md says what posted_at, feed.json and read_at decide; no new line says "Claude".

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
    case("the home page names no reel picker", not re.search(r"\bpicker", home.split("# ---------- the page ----------", 1)[-1].split("def _in_address", 1)[0], re.I)
         and not re.search(r"reel picker", read(SCRIPTS / "home_base.py"), re.I))


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
        '"Pick my story photos for <shoot>"': ["parts/arrange.md"],
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
    case("Step 4: every vibe lands on beats you can hear (her v25, Nov 13), the chat's reel maker the same, her dry-run line, "
         "and most cuts, never a promise of every one",
         "Every vibe lands on beats you can hear in their song (Nicole, Nov 13)" in step4
         and "for a reel made from the chat with `reel.py make` just the same" in step4
         and "Real hits: 13 of 14 cuts land on a hit you can hear." in step4
         and "**Most cuts, not a promise of every one:**" in step4 and "With no song there are no hits to find" in step4)
    case("the reel skill: a CapCut song's beats stay on CapCut's own marks, and the half second is 'about', never a promise "
         "(review, Nov 14)",
         "those beats are never moved (CapCut shows the marks in the project)" in t
         and "cuts still keep off the marks where the song doesn't hit" in t
         and "never promise the half second to the frame" in t)
    alike = "When the photos are much alike, keep it fast (Nicole, Nov 13)"
    case("photos that are much alike (her v25 pacing note): the opener plain, few Longers, more Quickers, in the reel skill's "
         "Step 2 and in curating.md's step 7, in her words",
         all(alike in x and "the first photo should not be so long" in x and "leave the opener plain" in x
             for x in (t.split("## Step 2", 1)[-1].split("\n## ", 1)[0], read(PLUGIN / "shared" / "curating.md"))))
    case("parts/arrange.md: whichever vibe, the cuts land on beats you can hear",
         "the cuts land on beats you can hear in their song" in read(PLUGIN / "skills" / "studio-manager" / "parts" / "arrange.md"))
    # The made reel does not always keep the plan (same in her engine: the song's hits and the bar can pull a plain
    # opener or a Longer photo to one beat), so the words say "aims" and never promise it (review, Nov 11).
    case("... and those lengths are aims, not promises: a Longer or the opener can land on one beat, one-beat photos can fall together",
         "**Those are aims, not promises.**" in step4 and "a Longer photo or a plain opener lands on one beat" in step4
         and "three or four one-beat photos fall together" in step4 and "never tell them it can't happen" in step4
         and "never three one-beat plain photos in a row" not in t and "(two to four, wherever the song hits)" not in t)
    case("... a reel pick is fully marked whenever it is saved (and \"make my posts\" is no longer where one is saved: v25)",
         "**This holds whenever a reel pick is saved** with `kit.py picks --reel`" in step2
         and "`--reel 7+,2,11-,4,9+`" in step2 and "is where most reel picks are first saved" not in t)
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
         "plain stories (one photo each" in kitp and "they make in the stories designer, from the kit page's Stories card" in kitp)
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
    case("ready to post normally comes from Add to my queue; the chat's ready does not check for a caption, so the assistant asks first",
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
    # (Nov 14: the home base's words are Nicole's v26, whole, in home_base.WORDS. Her Make posts card names
    # "reels, carousels, single photos, stories and captions"; a single post is made in the carousel designer.)
    # (Nov 17, her v28: the home page's own words moved to home.py; its step 3 says "reels, carousels, stories, and captions".)
    base = read(SCRIPTS / "home_base.py")
    cards = re.findall(r'"s3_p": "([^"]+)"', read(SCRIPTS / "home.py")) + re.findall(r'"m_lede": "([^"]+)"', base)
    case("the home base's Make posts card and screen promise no captions that 'sound like you' or are 'written the way you write'",
         len(cards) == 2 and not any(banned.search(c) for c in cards) and all("captions" in c for c in cards), cards)
    case("... and name what the kit makes, in her words (v26)",
         len(cards) == 2 and all(all(w in c for w in ("reels", "carousels", "stories")) for c in cards))
    # (Nov 17, Nicole's v27 section 8) the Make posts screen says what a post kit is, and its third step happens inside the kit
    wk = re.search(r'"m_what_h": "([^"]+)",\s*"m_what_p": "([^"]+)"', base)
    case("the Make posts screen says what a post kit is, in her v27 words, and has a third step inside the post kit",
         wk is not None and wk.group(1) == "What's a post kit?" and wk.group(2).startswith("It's one place for everything you'll post from a shoot.")
         and wk.group(2).endswith("Nothing is ever posted for you.") and '"m_s3": "<b>Make your posts inside your post kit.</b>"' in base
         and '"m_steps": "How to make a post kit from a shoot"' in base and "we'll build you a <b>post kit</b>" in base)
    hello_flat = re.sub(r"\s+", " ", read(SM / "parts" / "hello.md"))
    case("hello.md knows the screen's What's a post kit? box and its three steps, and answers \"what's a post kit?\" in her words",
         "What's a post kit?" in hello_flat and "It's one place for everything you'll post from a shoot." in hello_flat and "three steps" in hello_flat
         and "Make your posts inside your post kit" in hello_flat and "I'll bring your photos in and open your new post kit" in hello_flat)
    case("photos-in.md: after \"make my posts\" the assistant does what the screen's step 2 promised, nothing more",
         "I'll bring your photos in and open your new post kit." in re.sub(r"\s+", " ", read(SM / "parts" / "photos-in.md")))
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
    # (Nov 14, the home base's review round) the folder picker's button is on the Make posts screen, not the home page
    flat = lambda p: re.sub(r"\s+", " ", read(SM / "parts" / p))  # noqa: E731
    case("photos-in.md and on-a-pc.md send them to the Make posts screen for the Select the folder button, never to the home page",
         "the Make posts screen's \"Select the folder with your finished photos\" button opens it" in flat("photos-in.md")
         and "use the Select the folder button on the Make posts screen" in flat("on-a-pc.md")
         and not re.search(r"home page's \"Select the folder|Select the folder button on the home page", flat("photos-in.md") + flat("on-a-pc.md")))
    # a press on step 1 or 3 opens a screen that also lists backups and kits: it may be someone only looking
    case("hello.md: a press on See all my post kits may only be someone looking; what they asked is answered, then home.py seen (Back up a card never shows as a press since Nov 23)",
         "may only be someone looking" in flat("hello.md") and "answer what they asked, say nothing about the press, and run `home.py seen`" in flat("hello.md")
         and "may only be someone looking" in re.sub(r"\s+", " ", read(SM / "SKILL.md")))
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
         len(hit) == 1 and "parts/talking-reel.md" in hit[0] and "Tell the Assistant: set up talking reels." in talking_rec.line_for("no_tools"))
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
        ("several clips at once is theirs to press, and rule 3 stands",
         ("Holding Command (Ctrl on a PC) and clicking another adds it", "holding Shift and clicking picks every clip from the one clicked last to that one",
          "Slow zoom on clips that sit side by side becomes one long zoom across all of them", "one Undo takes that whole press back",
          "rule 3 stands, and you still have no command for a zoom or a speed", "tell them how to make them one",
          "nobody has yet pressed it by hand or opened a joined zoom in CapCut")),
        ("Speed and Zoom are a small menu each (Dustin, Nov 13), and no line still speaks of chips on the timeline",
         ("Speed and Zoom are a small menu each", "To take a zoom off a clip they pick the clip and choose None there", "Both are grey until a clip is picked")),
        ("How much and How fast (Dustin, Nov 13) are theirs to press too: the rows are said in the page's own words, no command sets them, and nobody has watched an eased zoom in CapCut",
         ("**How much** (Subtle, Medium, Strong)", "**How fast**", "Quick push", "Whole clip", "the menu stays open so they can set both",
          "these are theirs to press: you have no command for them (rule 3)", "nobody has watched an eased zoom in a real CapCut project yet")),
    ):
        miss = [w for w in words if w not in flat and w not in flat.lower()]
        case(f"the part: {what}", not miss, miss)
    case("the part: the word chip is nowhere in it (the timeline has menus now)", "chip" not in flat.lower(), [m.start() for m in re.finditer("chip", flat.lower())][:3])
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
    case("parts/arrange.md names the chooser's Talking to camera card (v27) in her words, as a link and not a choice",
         ('"' + reel_page.KIND_WORDS["kind_talk_b"] + '"') in arr and ('"' + reel_page.KIND_WORDS["kind_talk_s"] + '"') in arr
         and "is a link, not a choice" in arr and "changes nothing on the reel page" in arr and "`parts/talking-reel.md`" in arr)

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

    # Nicole's v27 (Nov 17, Lane C): Fix a word, Open CapCut and + Add more photos are the photographer's, on the page; the
    # part tells the assistant what they are, in the page's own words, and that it never presses or fixes for them
    case("the part tells Fix a word in the page's own words (double-click, Fix the words, Enter, Undo fix, the hover line) and that the assistant never fixes one (rule 3)",
         all(x in flat for x in ("A word the Mac misheard they fix themselves", "**" + W["sel_fix"] + "**", "double-click it", "type the right words, Enter",
                                 W["fix_back"] + " puts the heard word back", "You fixed this. It was heard as", "You never fix a word for them (rule 3)",
                                 "Double-click the word on the page and type the right one."))
         and W["sel_fix"] == "Fix the words" and W["fix_back"] == "Undo fix" and W["fixed_title"].startswith("You fixed this. It was heard as"))
    case("rule 3 still says the assistant never touches a caption word, and that the photographer can, on the page",
         "never touch a caption word" in flat and "never fix, tidy or reword one (they can, on the page" in flat)
    case("the part says the fixed word is simply the word to show and photos, and that status counts the fixes and never names them, as the script does",
         "`show` and `photos` print the fixed word as the word; `status` says how many they fixed, never which" in flat
         and "how many words they fixed on the page (never which: rule 3)" in flat and talking_rec.FIXED_COUNT.strip().startswith("Words fixed on the page:"))
    case("the part tells Open CapCut as the page has it (beside Make it in CapCut once made, and in the result box that names the project), with no command for it",
         ("**" + W["open_capcut"] + "**") in flat and "beside Make it in CapCut once this talking reel has been made, and in the result box" in flat
         and "You have no command for that either" in flat and "free from capcut.com" in flat and "free from capcut.com" in W["capcut_missing"]
         and ('"' + W["made_h2"] + '", which names the project to click') in flat and W["open_capcut"] == "Open CapCut")
    case("the part tells + Add more photos as the page has it (the photo pop-up's footer, the Photos folder, new photos at the end), and that every photo keeps its number",
         ("**" + W["add_photos"] + "**") in flat and "sits in the photo pop-up's footer" in flat and "opens the shoot's Photos folder" in flat
         and "show up in the grid at the end, with the next numbers" in flat and "**Every photo keeps its number**" in flat
         and "run the sheet command again before you place" in flat and W["add_photos"] == "+ Add more photos")
    case("...and the numbering the part promises is the one the code keeps (reel.py number_photos: the next after the highest ever given, a photo gone keeps its number unused)",
         "a photo that is gone keeps its number unused" in flat and "after the highest ever given" in flat
         and "nxt = max(before.values(), default=0) + 1" in read(REEL / "scripts" / "reel.py") and "def number_photos(photos, before):" in read(REEL / "scripts" / "reel.py"))
    v27 = [ln for ln in part.splitlines() if ln.startswith(("  - **A word the Mac misheard", "  - **+ Add more photos**", "**Open CapCut**"))]
    case("the three v27 paragraphs are there and say the Assistant, never Claude (the app's own name stays where the part names the Claude app's pane)",
         len(v27) == 3 and not any("Claude" in ln for ln in v27), [ln[:60] for ln in v27])


# ---------- Nicole's v26: sets of stories, and the assistant choosing a story's photos ----------

# ---------- Nicole's v27: the assistant choosing a carousel's photos (Lane B, stage 1) ----------

def check_carousel_v27():
    arr = read(SM / "parts" / "arrange.md")
    part = arr.split("## Laying out the slides: the designer", 1)[1].split("\n## ", 1)[0]
    flat = " ".join(part.split())
    design = read(SCRIPTS / "design.py")
    page = read(SCRIPTS / "design_page.py")
    skill = read(SM / "SKILL.md")
    where = read(SM / "parts" / "where-things-live.md")
    case("carousel v27: SKILL.md has a row for the line pasted from the carousel designer, word for word, pointing at the designer's section",
         '| a line pasted from the carousel designer: "Pick my carousel photos for <shoot>" (and "..., and follow my note") | `parts/arrange.md`, "Laying out the slides: the designer" |' in skill)
    case("carousel v27: the two commands are in the designer's command block, as design.py has them",
         'design.py note "<kit>" [--design <id>]' in part and 'design.py fill "<kit>" --photos 3,8,12 [--design <id>] [--replace]' in part
         and 'sub.add_parser("note"' in design and 'sub.add_parser("fill"' in design and 'sub.add_parser("story-note"' in design)
    case("carousel v27: the page's line and its button are named as the page has them",
         '**"Pick my carousel photos for <shoot>"** (and "..., and follow my note")' in part and '**"Let the Assistant choose the photos"**' in part
         and 'ASK_LINE_CAROUSEL = "Pick my carousel photos"' in page and 'ASK_BUTTON = "Let the Assistant choose the photos"' in page)
    case("carousel v27: the five steps mirror the stories' (note, one look at the sheet with curating.md, the shape each frame wants, fill in the frames' order, the page shows it by itself)",
         "1. `design.py note \"<kit>\"`" in part and "2. `kit.py sheet \"<kit>\"`" in part and "shared/curating.md" in part and "3. Give each frame a photo of the shape it wants" in part
         and "4. `design.py fill \"<kit>\" --photos N,N,N --design <id>`" in part and "5. The open page shows your pick by itself within a few seconds" in part)
    case("carousel v27: choosing is the assistant's job, the note is theirs and comes first, an opener and a closer in an order that flows, never pretend",
         "Choosing and ordering the photos is your job (rule 11); the note is theirs and outranks your taste" in flat and "an opener that stops the scroll, variety, no near-twins side by side, a closer" in flat
         and "never pretend" in flat)
    case("carousel v27: with no empty frame the assistant adds no slides and names what to press; --replace only when they asked; the words are theirs",
         "**With no empty frame**" in part and "you add no slides and replace nothing by yourself" in flat and "Press Empty frame on a slide" in flat and "+ Add slides" in flat
         and "that is `--replace`" in flat and "`fill` changes photos only: it never adds, changes or removes a text box" in flat)
    case("carousel v27: a rerun is harmless and the design before is kept, as design.py has it",
         "Running the very same command again is harmless: it answers `SAME:`" in flat and "The design as it was before your pick is kept beside it; nothing is deleted." in flat and "def _pick_there(" in design)
    case("carousel v27: where-things-live names the three fields on a carousel design's record and the two commands",
         "A carousel design's record (`designs/<id>.json`) may hold the same three since Nicole's v27 (`ask`, `asked`, `filled_by`; read with `design.py note`, filled with `design.py fill`)." in where)
    case("carousel v27: the stories' section says its two commands are the same two with --kind stories",
         "(`story-note` and `story-fill` are `design.py note` and `design.py fill` with `--kind stories`" in arr)
    case("carousel v27: no leftover says the carousel's designer takes no note or has no such button",
         not re.search(r"carousel[^.]*\b(no|never)\b[^.]*\bnote\b[^.]*assistant", flat, re.I) and "a carousel's page has neither" not in read(SCRIPTS / "design_js_ask.py"))
    # Open folder (B15) and the three collages (B7c), as the part names them
    case("carousel v27: the designer's folder button is \"Open folder\" in both sections, with her not-yet line, and no leftover \"Open the Carousel folder\" said of the designer",
         'with an "Open folder" button on the same line' in part and "Press Save slides first and it's made for you." in part
         and 'with "Open folder" on the same line' in arr and "Press Save stories first and it's made for you." in arr
         and '"Open the Carousel folder" button on the same line' not in part and '"Open the Stories folder"' not in arr)
    case("carousel v27: the three story collages are named among the stories' templates", "**Playful mosaic**, **Mood board** and **Overlapping collage**" in arr)
    pc = read(SM / "parts" / "on-a-pc.md")
    case("carousel v27: the PC part says the button's new name and its answer on a PC", '"Open folder" opens File Explorer' in pc and "Your Carousel folder is open in File Explorer." in pc and "Open the Carousel folder" not in pc)
    # the page's v27 buttons (B8 to B17), named in the part as the page has them, so the assistant points at the button and does nothing from the chat
    core_js = read(SCRIPTS / "design_js_core.py")
    save_js = read(SCRIPTS / "design_js_save.py")
    crop_js = read(SCRIPTS / "design_js_crop.py")
    view_js = read(SCRIPTS / "design_js_view.py")
    sect = part.split("**The photo inside its frame, several photos at once, one slide on its own, and more photos (Nicole's v27).**", 1)
    case("carousel v27: the designer's section has the paragraph for her v27 page buttons, before Adding slides", len(sect) == 2 and "**Adding slides, and the templates" in sect[1])
    para = " ".join(sect[1].split("**Adding slides, and the templates", 1)[0].split()) if len(sect) == 2 else ""
    for words, src in (("Show the whole photo", "whole: 'Show the whole photo'"), ("Crop", "btn: 'Crop'"), ("Keep the frame's shape", "Keep the frame\\'s shape"), ("Done", "done: 'Done'"),
                       ("Even them out", "even: 'Even them out'"), ("Same size", "sameSize: 'Same size'"), ("Line up tops", "tops: 'Line up tops'"), ("Remove them", "removeThem: 'Remove them'"),
                       ("Use this photo", "viewUse: 'Use this photo'"), ("Put it in the selected frame", "viewPut: 'Put it in the selected frame'"),
                       ("Save just this slide", "saveOne: 'Save just this slide'"), ("Save just one slide", "saveOneAny: 'Save just one slide'")):
        case(f"carousel v27: the part names the page's button as the page has it: {words}", f"**{words}**" in para or f'"{words}"' in para, words)
        case(f"carousel v27: ... and the page has it: {words}", src in core_js + save_js + crop_js + view_js, src)
    case("carousel v27: the part says a single slide's name and that nothing else changes (not the kit page, the queue or the design), with no line to the assistant, as design.py has it",
         '"Beach carousel 1 - slide 03 updated.jpg"' in para and '"... updated 2.jpg"' in para and "not which set the kit page and the posting queue show, not the design, and no line comes to you from it" in para
         and 'ONE_NAME = "{base} - slide {i:02d} updated.jpg"' in design and "add_waiting" not in design.split("def _finish_one(")[1].split("def _one_words(")[0])
    case("carousel v27: the part tells the assistant what to say for \"I just want to save number 3\" (Nicole, Nov 15), naming the button",
         "then press Save just slide 3 beside Save slides" in para and "Slide 3 on its own" in para and "on its own:" in design)
    case("carousel v27: the part says + Add photos opens the Photos folder, new photos join the end with the next numbers, every number stays, a removal still asks for Reload, and kit.py sheet keeps the numbers",
         "**+ Add photos**" in para and "numbered after the last" in para and "every photo that was there keeps its number" in para and "still stops the page until Reload" in para
         and "`kit.py sheet \"<kit>\"` keeps every number" in para and "never number a shoot's photos any other way" in para and "--before" in read(SCRIPTS / "kit.py"))
    case("carousel v27: her line for photos that joined is quoted as the page says it", '"2 new photos in, at the end of your photos (#31\u201332)."' in para
         and "' new photo' + (k === 1 ? '' : 's') + ' in, at the end of your photos (#'" in read(SCRIPTS / "design_js_ask.py"))
    case("carousel v27: the stories' section carries the same in a story's words: Save just this story, the single story's name, + Add photos",
         "**Save just this story** / **Save just story N**" in arr and '"Beach stories - 03 updated.jpg"' in arr and "Story 3 on its own" in arr and 'STORY_ONE_NAME = "{base} - {i:02d} updated.jpg"' in design)
    case("carousel v27: where-things-live names the single slide's record (`one`, `again`), its file name beside the set, and that kit.json is untouched",
         "A press of Save just this slide (Nicole's v27) leaves a record of the same shape with `one`, the slide's number, and `again`" in where
         and "\"<the set's name> - slide 03 updated.jpg\"" in where and "nothing in `kit.json` changes for it" in where)
    case("carousel v27: the PC part says + Add photos' lines name File Explorer and that a single slide's name is held to the 260 characters",
         '"+ Add photos" opens the shoot\'s Photos folder in File Explorer too' in pc and "Your Photos folder is open in File Explorer. Drag your finished photos in, and they show up here at the end." in pc
         and 'A slide saved on its own ("Save just slide 3") is held to the same 260 characters' in pc)


def check_stories_v26():
    arr = read(SM / "parts" / "arrange.md")
    part = arr.split("## Making stories: the stories designer", 1)[1].split("\n## ", 1)[0]
    flat = " ".join(part.split())
    design = read(SCRIPTS / "design.py")
    page = read(SCRIPTS / "design_page.py")
    case("stories: a shoot's stories come in sets, and nothing says there is only one design any more",
         "**A shoot's stories come in sets**" in part and "My story sets" in part and "+ New set of stories" in part and "has **one** stories design" not in arr
         and "one stories design" not in read(SM / "parts" / "where-things-live.md"))
    case("stories: the two commands of the assistant's pick are in the part, as design.py has them",
         'design.py story-note "<kit>" [--design <id>]' in part and 'design.py story-fill "<kit>" --photos 3,8,12 [--design <id>] [--replace]' in part
         and 'sub.add_parser("story-note"' in design and 'sub.add_parser("story-fill"' in design and '"--replace"' in design)
    case("stories: the part says which set a command takes (Copy pressed, or changed, last), that a rerun is harmless, and the record's name for it; design.py has all three",
         "the set they pressed Copy on, or changed, last" in part and "Running the very same command again is harmless: it answers `SAME:`" in part
         and "a photo that is already in the set" in part and "`asked`, the time they last pressed Copy there" in read(SM / "parts" / "where-things-live.md")
         and "def _post_asked(" in design and "def _pick_there(" in design and '"/design-asked"' in design)
    case("stories: the page's line and its button are named as the page has them",
         '"Pick my story photos for <shoot>"' in part and '"..., and follow my note"' in part and '"Let the Assistant choose the photos"' in part
         and 'ASK_BUTTON = "Let the Assistant choose the photos"' in page and 'ASK_LINE = "Pick my story photos"' in page)
    case("stories: choosing is the assistant's job, the note is theirs and comes first, one look at the sheet",
         "Choosing and ordering the photos is your job (rule 11); the note is theirs and outranks your taste" in flat and "One look at the sheet, never photo by photo" in flat
         and "never pretend" in flat)
    case("stories: --replace only when they asked; a refusal changes nothing; the set before is kept",
         "use it only when they asked you to choose again" in flat and "changes nothing when it refuses" in flat and "The set as it was before your pick is kept beside it; nothing is deleted." in flat)
    case("stories: the assistant never touches the words (rule 11), also when the note asks for words",
         "**You never touch the words.**" in part and "it never adds, changes or removes a text box, and neither do you" in flat and "The words are yours" in flat
         and "**The words on a story are theirs.**" in part)
    case("stories: the template words are placeholders the assistant never fills in; My editing queue fills itself from their queue",
         "are placeholders for them to change: you never fill them in" in flat and "**My editing queue** fills its list by itself from their editing queue" in flat
         and "If your shoot is on here, your gallery is on its way." in flat and "I can't reach your editing queue right now." in flat
         and 'QUEUE_CLOSING = "If your shoot is on here, your gallery is on its way."' in design and 'QUEUE_CANT = "I can\'t reach your editing queue right now."' in design)
    case("stories: her four templates, the guides' new name, Redo and the x on a label are in the part; the old name of the tick is gone",
         all(x in flat for x in ("**Gallery delivered**", "**My editing queue**", "**The full story**", "**Seamless swipe**", "\"Show Instagram's guides\"", "**Redo** sits beside Undo",
                                 "has a small x that removes that story, even an empty one")) and "Show Instagram's buttons" not in arr)
    case("stories: Save stories names a set after the set, and the kit shows the set saved last",
         "named after the set" in flat and "shows the set that was saved last as the stories" in flat)
    case("stories: an open page takes the pick by itself; otherwise open that set by its id", "The open page shows your pick by itself within a few seconds" in flat
         and 'design.py open "<kit>" --kind stories --design <id>' in flat)
    case("where-things-live.md: the note and who filled a set are named, and a saved set is named after the set",
         "`ask`, the note they wrote for you" in read(SM / "parts" / "where-things-live.md") and "`filled_by`" in read(SM / "parts" / "where-things-live.md")
         and '"<the set\'s name> - 01.jpg"' in read(SM / "parts" / "where-things-live.md"))


def check_several_reels():
    """Several reels from one shoot (Nicole's v25, stage G of the v26 build): the instructions say what the scripts do."""
    arr = read(SM / "parts" / "arrange.md")
    part = arr.split("**Several reels from one shoot", 1)[1].split('**"Look through my footage for <shoot>"**', 1)[0]
    flat = " ".join(part.split())
    rp, kit, foot, tr = read(SCRIPTS / "reel_page.py"), read(SCRIPTS / "kit.py"), read(SCRIPTS / "footage.py"), read(SCRIPTS / "talking_rec.py")
    case("several reels: the bar is named as the page has it (Your reels, + Start a new reel, Rename), with her default names",
         "**Your reels**" in part and "**+ Start a new reel**" in part and "**Rename**" in part and '"Reel 1", "Reel 2"' in part
         and '"reels_label": "Your reels"' in rp and '"reels_new": "+ Start a new reel"' in rp and 'REEL_FIRST = "Reel 1"' in rp)
    case("several reels: a new reel is blank on \"I'll drag them in myself\", with every clip found; every reel fully separate; the folders are the shoot's",
         "\"I'll drag them in myself\" with nothing in it, no pick of yours, footage not chosen, no song, and every clip you have found for the shoot, as found" in flat
         and "**Every reel is fully separate:**" in part and "Nothing done in one reel changes another." in flat and "shared by all its reels" in flat)
    case("several reels: every command acts on the reel open on the page and says which; the part names each command's way to name another, as the scripts have them",
         "**Every command acts on the reel that is open on the page**" in part and "each of them says first which reel it is about" in flat
         and '--for-reel "Reel 2"' in part and 'footage.py scan "<kit>" --reel "Reel 2"' in part and 'footage.py moments "<kit>" --file <file> --reel "Reel 2"' in part
         and 'reel_page.py show "<kit>" --reel "Reel 2"' in part and 'reel_page.py make "<kit>" --reel "Reel 2"' in part
         and 'reel_page.py direct "<kit>" --reel "Reel 2"' in part
         and '"--for-reel"' in kit and 'x.add_argument("--reel"' in foot and rp.count('.add_argument("--reel"') == 4)
    case("several reels: the chat's reels command, as reel_page.py has it, in the part and in the part's command block",
         'reel_page.py reels "<kit>" --new [--name "Kitchen"]' in flat and '--rename "Reel 2" --to "Kitchen"' in flat and '--open "Reel 1"' in flat
         and 'python3 <scripts>/reel_page.py reels "<kit>" [--new [--name "<name>"] | --open "<reel\'s name>" | --rename "<reel\'s name>" --to "<name>"]' in arr
         and 'sub.add_parser("reels"' in rp and all(('rl.add_argument("%s"' % a) in rp for a in ("--new", "--name", "--open", "--rename", "--to")))
    case("several reels: a pasted line that names a reel is checked against the reel open on the page first",
         "run `reel_page.py note \"<kit>\" --reel \"Kitchen\"` first: it checks that the reel named is the one open on the page" in flat
         and "say which reel your pick went to" in flat and 'sub.add_parser("note"' in rp)
    case("several reels: a new reel has no pick until they ask, and a pick waits under Let the Assistant choose",
         "Pick for it only when they ask." in flat and 'your pick waits under "Let the Assistant choose": tell them to press it' in flat)
    case("several reels: a reel is never removed, said plainly; two reels never share a name (the scripts refuse it)",
         "**A reel can never be removed** (nothing is deleted)" in part and "Two reels of one shoot never share a name" in flat and "NAME_TAKEN" in read(SCRIPTS / "reels.py"))
    case("several reels: CapCut's projects are named for the shoot, not the reel; each reel's mixes are its own",
         'the first one made is "<shoot> reel", the next "<shoot> reel 2", whichever reel on the page it came from' in flat and "gives the next mix of that reel" in flat
         and "def mix_number(" in rp)
    reel = read(REEL / "SKILL.md")
    case("several reels: the reel skill says so in a paragraph and sends to the part",
         "**A shoot can have several reels (Nicole, Nov 12).**" in reel and '`--for-reel "<reel\'s name>"` saves it for another' in " ".join(reel.split())
         and '"Several reels from one shoot"' in reel)
    talk = " ".join(read(SM / "parts" / "talking-reel.md").split())
    case("several talking reels: the bar, a new one at step 1, each its own, --reel on the five commands, her refusal line word for word, never removed",
         "**Your talking reels**" in talk and "**+ Start a new talking reel**" in talk and "A new one starts at step 1 with no video chosen" in talk
         and '"Talking reel 1", "Talking reel 2"' in talk and "`status`, `show`, `cut`, `photos` and `place` act on the one open on the page" in talk
         and 'add `--reel "<its name>"`' in talk and "I'm still turning your video into a script. Give it a minute, then try again." in talk
         and 'STILL_SCRIPT = "I\'m still turning your video into a script. Give it a minute, then try again."' in tr and "Rename always works" in talk
         and "A talking reel can never be removed" in talk and 's.add_argument("--reel"' in tr)
    where = " ".join(read(SM / "parts" / "where-things-live.md").split())
    case("where-things-live.md names the list of reels in both records, every clip found, and where the first reel's pick stays",
         "the others wait in `versions`" in where and "`current` naming the open one" in where and "`moments_found` is every clip found for the shoot" in where
         and "the first reel's pick of yours stays in `kit.json`" in where and where.count("wait in `versions`") == 2
         and '"moments_found"' in foot and "REEL_KEYS" in rp)


def check_photographer_picks():
    """The photographer picks (Nicole's v25, sections 3 and 10; stage H of the v26 build): nothing is picked until
    they ask, the photo note is read first and followed, and "make my posts" only brings the photos in and opens
    the post kit. The instructions say what the page and the scripts do, in the page's own words."""
    rp, kitsrc, foot = read(SCRIPTS / "reel_page.py"), read(SCRIPTS / "kit.py"), read(SCRIPTS / "footage.py")
    arr, kitp, photos = read(SM / "parts" / "arrange.md"), read(SM / "parts" / "post-kit.md"), read(SM / "parts" / "photos-in.md")
    reel, cur, core = read(REEL / "SKILL.md"), read(PLUGIN / "shared" / "curating.md"), read(SM / "SKILL.md")
    flat = lambda t: " ".join(t.split())  # noqa: E731
    words = dict(re.findall(r'^    "(not_picked|photo_ask_b|photo_for|photo_note)": "([^"]+)"', rp, re.M))
    case("the page's four lines are in reel_page.PICK_WORDS (the not-picked line, the box's title, the line to copy, its ending)", len(words) == 4, sorted(words))
    not_picked, box = words.get("not_picked", "?"), words.get("photo_ask_b", "?")
    case("arrange.md and post-kit.md quote the page's not-picked line word for word", ('"' + not_picked + '"') in flat(arr) and ('"' + not_picked + '"') in flat(kitp))
    case("arrange.md and the reel skill name the note box by its title on the page", box in flat(arr) and box in flat(reel) and box in flat(cur))
    case("arrange.md gives the line as the page builds it: the reel's name only with several reels, 'and follow my note' only with a note",
         '**"Pick my reel photos for <shoot>"**' in arr and '**", and follow my note"**' in arr and '"Pick my reel photos for Beach, Kitchen, and follow my note"' in arr
         and words.get("photo_for") == "Pick my reel photos for {short}" and words.get("photo_note") == ", and follow my note")
    para = arr.split('**"Pick my reel photos for <shoot>"** (and', 1)[-1].split("\n\n", 1)[0]
    case("arrange.md: the pasted line is answered in order: reel_page.py note first, the note decides, the pick saved for that reel only",
         para.index('reel_page.py note "<kit>"') < para.index("**The note decides what may go in.**") < para.index("**for that reel only**")
         and "It changes nothing." in para and '--for-reel "<name>"' in para and "A pick for one reel never changes another." in para)
    case("... pick only what the note allows, never widen it, never fill in; ask when nothing fits",
         "Pick only what it allows" in para and "never widen it" in para and "never fill in with photos it leaves out" in para and "ask one short question" in para)
    case("... it is the only time a reel's photos are picked, and the marking rule still holds then",
         "**It is the only time you pick a reel's photos**" in para and "about a third Longer, about a quarter Quicker" in para)
    case("the command the instructions name is the script's: reel_page.py note, with --reel, and it prints the note word for word",
         'sub.add_parser("note"' in rp and 'nt.add_argument("--reel"' in rp and "word for word" in rp.split("def cmd_note", 1)[1].split("\ndef ", 1)[0])
    case("kit.py picks says the note again after a reel pick is saved (and the instructions lean on it)",
         "_say_photo_note(kit, later)" in kitsrc and "prints their note again after" in flat(arr) and "prints their note again after it saves" in flat(reel))
    case("arrange.md opens with who chooses: the photographer, and the assistant only when asked (her words)",
         '**The photographer chooses; you pick only when they ask (Nicole, Nov 13: "I choose, not you.").**' in arr
         and "Choosing and ordering the photos is your job and stays so. These pages are how the photographer moves things after you have picked" not in arr)
    case("arrange.md: opening the reel page is not a reason to pick, and there is a line to say when nothing was picked",
         "**Opening the page is not a reason to pick:**" in arr and "**When you have not picked** (the usual case):" in arr
         and "put your photos in, add your song, and press Make my reel" in arr)
    case("arrange.md: the carousel is picked only when they ask", "**Pick the carousel only when they ask you to**" in arr)
    # the post kit: "make my posts" only brings the photos in and opens the post kit
    steps = kitp.split("**Then, in order, without stopping:**", 1)[-1].split("**Only when they ask", 1)[0]
    case("post-kit.md: making a kit only numbers the photos and opens the kit page: no pick, no build, no question",
         "**This step is only the numbering: don't read the sheets and don't pick.**" in steps and "2. **Nothing is picked here.** No `kit.py picks`" in steps
         and "no `kit.py build` as part of a kit" in steps and "**The reel is not made here**" in steps)
    case("... none of the kit's steps runs kit.py picks or kit.py build as a command to do",
         not re.search(r"^\d\. `kit\.py (picks|build)", steps, re.M))
    case("post-kit.md: no question when a kit starts, about the shoot or how they write; what they say unasked is still kept through a file",
         "**No question when a kit starts" in kitp and "Don't ask them to tell you about the shoot, and don't ask how they write." in kitp
         and "tell me about this shoot. Who they are, what the day was like" not in kitp and "**If they tell you about the shoot anyway, unasked, keep it word for word.**" in kitp
         and "kit.py told \"<kit>\" --text-file" in kitp)
    case("post-kit.md: the voice question waits for the first caption they ask for, never a kit", "**The voice, asked once, the first time they ask you for a caption** (never when a kit is made" in kitp)
    case("post-kit.md says it in her words, and what to say when the kit opens promises no pick",
         "\"You're not supposed to do any of that. I choose, not you.\"" in kitp and "Nothing is picked yet" in kitp
         and "Never add a pick, a caption or an offer to choose for them to that" in kitp)
    case("post-kit.md: the picks and the plain pieces are still there, only when they ask",
         "**Only when they ask: your pick for the carousel, and the plain singles, stories and cover.**" in kitp and "None of this is part of making a kit." in kitp
         and "`kit.py build \"<kit>\"`" in kitp)
    case("post-kit.md: \"I'm done with the shoot\" ends on the kit page too: nothing picked, no question",
         "**Nothing is picked or made in the chat, and there is no question about the shoot**" in kitp.split("## The post kit", 1)[0])
    case("photos-in.md: \"make my posts\" only brings the photos in and opens the post kit",
         '**"Make my posts" only brings the photos in and opens the post kit' in photos and "Don't read the photos to pick, don't ask about the shoot, don't write anything." in photos
         and "you pick them only if they ask" in photos)
    case("kit.py start's own next-step line no longer sends the assistant to a question or a pick",
         "Nothing is picked or made until they ask." in kitsrc and "Next: the question, then kit.py sheet." not in kitsrc)
    case("the reel skill: they choose; Step 2 runs only when they ask, their note first",
         '**They choose which photos go in (Nicole, Nov 13: "I choose, not you.")**' in reel and "## Step 2: when they ask for your pick, curate the set and put it on the page" in reel
         and "**Nothing is picked until they ask (Nicole, Nov 13).**" in reel and "**Their note first.**" in reel and "**Pick only what the note allows**" in reel
         and "**Stop here and open the page unless they asked for your pick:**" in reel and "(your main job)" not in reel)
    case("the reel skill: a footage look is not a reason to pick photos, and footage.py says the same",
         "don't pick photos because they asked for a footage look" in reel and "If the shoot has no reel pick yet, do Step 2 first." not in reel
         and "Pick the photos first, exactly as for a reel with no footage" not in foot and "Find the moments only" in foot)
    case("curating.md: you choose only when they ask; their photo note decides what may go in; the marking rule stays for when you do",
         "**You choose only when they ask (Nicole, Nov 13:" in cur and "**Their photo note decides what may go in (Nicole, Nov 13).**" in cur
         and "mark its rhythm: every reel, fully (Nicole, Nov 10)" in cur and "When the photos are much alike, keep it fast (Nicole, Nov 13)" in cur)
    case("the core's rule: choosing is the assistant's when it is asked of it; the sneak peeks always",
         "**Choosing and ordering photos is yours, when it is asked of you:**" in core and "**nothing is picked until they ask**" in core
         and "you pick its photos only when they ask" in core)
    case("hello.md's first-time explanation of Make posts no longer says the assistant picks the photos",
         "you pick the photos; each piece's caption" not in read(SM / "parts" / "hello.md") and "you pick only when they ask" in read(SM / "parts" / "hello.md"))
    case("canva.md: the Canva fill is never run by itself when a kit is made", "never by itself when a kit is made" in read(SM / "parts" / "canva.md"))
    case("where-things-live.md names the note in the reel page's record", "`photo_ask`" in read(SM / "parts" / "where-things-live.md") and '"photo_ask"' in rp)
    said = [ln[:140] for name, t in (("arrange", arr), ("post-kit", kitp), ("photos-in", photos), ("reel", reel))
            for ln in t.splitlines() if re.search(r"\bClaude\b", ln) and re.search(r"hasn't picked|which photos you'd like", ln)]
    case("the page's lines are quoted as the page has them: 'the Assistant', never 'Claude'", not said, said)


def check_trim_and_select():
    """Select several photos like Lightroom (Nicole's v25, section 8), and the footage editor that replaced her v25
    Trim panel (her v27, section 3; Lane A's stage 3). Both are the page's own: the instructions say what the page
    does, in the page's words, and that the assistant has no command for either; naming their clips is the
    assistant's (the reel skill's section "Name my clips")."""
    rp = read(SCRIPTS / "reel_page.py")
    arr, pc = " ".join(read(SM / "parts" / "arrange.md").split()), " ".join(read(SM / "parts" / "on-a-pc.md").split())
    reel, core = " ".join(read(REEL / "SKILL.md").split()), read(SM / "SKILL.md")
    words = dict(re.findall(r'^    "(sel_longer|sel_quicker|sel_neither|sel_out|sel_clear|sel_add|editor_no_stills_pc)": "([^"]+)"', rp, re.M))
    ed = dict(re.findall(r'^    "(ed_h3|ed_footage|ed_make|ed_in|ed_out|ed_add|ed_clear|ed_zoom|ed_whole|clips_wl|use|in_reel|play_clip|not_named|desc_say|desc_line)": "([^"]+)"', rp, re.M))
    case("the page's words for selecting several and for the editor are in reel_page.py (7 and 16 of them)", len(words) == 7 and len(ed) == 16, (sorted(words), sorted(ed)))
    case("the v25 Trim panel is off the page (TRIM_PANEL = False), its code kept behind the switch", "TRIM_PANEL = False" in rp and "if TRIM_PANEL:" in rp)
    case("arrange.md names the editor's parts as the page shows them: Your footage, Footage, Make a clip, Start here, End here, Add clip, Clear, Your clips, Zoom in, Show the whole video",
         all(("**" + ed[k] + "**") in arr for k in ("ed_h3", "ed_footage", "ed_make", "ed_zoom", "ed_whole", "clips_wl", "use", "in_reel"))
         and all(ed[k] in arr for k in ("ed_in", "ed_out", "ed_add", "ed_clear")) and "**Add clip**" in arr, [k for k in ed if ed[k] not in arr])
    case("arrange.md says how a clip is made (the orange stretch that grows, End here, the ends and the middle, 1 to 15 seconds, Add clip) and what happens after Add clip",
         all(x in arr for x in ("Start here turns orange and plays", "orange striped stretch grows", "End here makes it solid", "drag an end to trim it", "the middle to slide it",
                                "a clip is 1 to 15 seconds", "dashed with \"✓ Added\"", "the clip just added is never changed")))
    case("arrange.md: a click on a card opens the clip, a drag across a clip only scrubs, a trimmed clip keeps its name, the assistant has no command that trims, makes or removes a clip",
         all(x in arr for x in ("A click on a card opens that clip in the editor", ed["play_clip"], "Dragging across a clip on the timeline only scrubs; a plain click picks it",
                                "A trimmed clip keeps a name it was given", "You have no command that trims, makes or removes a clip", "Her v25 Trim panel")))
    case("arrange.md names YOUR PICK, Not named yet and the Name my clips line, and sends the naming to the reel skill",
         "**YOUR PICK**" in arr and ("**\"" + ed["not_named"] + "\"**") in arr and ("**\"" + ed["desc_say"] + "\"**") in arr and ("**\"" + ed["desc_line"].replace("{short}", "<shoot>") + "\"**") in arr
         and 'the reel skill\'s section "Name my clips"' in arr)
    case("the reel skill has the section Name my clips: picks, read each sheet once, a short plain name (never a name, a feeling), no about, describe, the page shows them",
         '## Name my clips: "Name my clips for <shoot>"' in reel and "footage.py picks" in reel and "Read each sheet once" in reel and "Never a person's name, a feeling, an occasion" in reel
         and 'refuses an "about"' in reel and "footage.py describe" in reel and "Never write a clip's name into the reel page's records any other way" in reel)
    case("the reel skill's footage look names any unnamed picks at its end, and sends the moments to Your clips (not Select your clips)",
         "Then name any clips of their own that aren't named yet" in reel and 'under "Your clips" in the footage editor' in reel and "Select your clips" not in reel)
    case("the core table sends Name my clips to the reel skill", '| "Name my clips for <shoot>"' in core and 'the reel skill\'s "Name my clips"' in core)
    case("arrange.md: selecting several, key by key (click, Shift-click, Cmd-click or Ctrl-click on a PC, Escape), and a drag moves the whole selection in order",
         all(x in arr for x in ("a click on a photo in the order selects it", "Shift-click selects everything between it and the last one clicked",
                                "Cmd-click (Ctrl-click on a PC) adds or drops one", "Escape lets them all go",
                                "Dragging any selected photo moves the whole selection to where it lands, in order", "a tag on it says how many photos are moving")))
    bar = "**%s, %s, %s, %s** and **%s**" % tuple(words.get(k, "?") for k in ("sel_longer", "sel_quicker", "sel_neither", "sel_out", "sel_clear"))
    case("arrange.md names the bar's five buttons as the page has them, and Add them to the end below", bar in arr and ("**" + words.get("sel_add", "?") + "**") in arr, bar)
    case("arrange.md: in All your photos a plain click still adds or takes out; one press of Undo takes a whole batch back; a selection is the page's own",
         "a plain click still adds a photo or takes it out" in arr and "one press of Undo takes the whole batch back" in arr and "you can't see it and nothing saves it" in arr)
    case("on-a-pc.md names the editor's gap honestly, in the page's own line (no pictures along the timeline), Start here and End here, and that clips can't be named on a PC",
         ('"' + words.get("editor_no_stills_pc", "?") + '"') in pc and "**Start here**, **End here** and **Add clip** work on it" in pc and "Use this moment" not in pc
         and "can't see your clips to name them" in pc and "Naming their clips" in pc)


def check_songs_v25():
    """Songs (Nicole's v25, section 5; stage J of the v26 build): a short song starts after a glitchy opening, a
    replaced recording gets its sound taken again, and Remove this song (her v27, built Nov 17, Lane E's E12):
    the instructions say the page's button moves a song, and a recording's sounds, to the computer's own Trash,
    never a delete, Put Back brings it back, a song in the Photos folder stays, and the assistant has no command
    for it and never moves a song itself."""
    rp = read(SCRIPTS / "reel_page.py")
    tc = read(SCRIPTS / "this_computer.py")
    arr, where = " ".join(read(SM / "parts" / "arrange.md").split()), " ".join(read(SM / "parts" / "where-things-live.md").split())
    reel = " ".join(read(REEL / "SKILL.md").split())
    gone = re.search(r'^    "song_gone": "([^"]+)"', rp, re.M)
    case("the short-song line is 40 seconds in reel_page.py, and the gap is hers (-50 dB, 0.3 s, the first 12 seconds) in sound.py",
         "SHORT_SONG_FROM_TOP = 40 " in rp and all(x in read(REEL / "scripts" / "sound.py") for x in ("LEAD_NOISE_DB = -50.0", "LEAD_GAP = 0.3 ", "LEAD_WITHIN = 12.0")))
    for name, t in (("arrange.md", arr), ("the reel skill", reel)):
        case(f"{name}: a song under 40 seconds starts after the last silent gap in its first 12 seconds, on the first 1 of a bar; no gap, the top",
             "For a song under 40 seconds" in t and "after the last silent gap in the song's first 12 seconds, on the first 1 of a bar after it" in t
             and ("with no gap it starts at the top" in t or "with no gap, at the top" in t) and '"starting the song 4 seconds in"' in t)
        case(f"{name}: a replaced recording's sound is taken again as \"<name> sound 2.m4a\", the first never written over, the recording listed once",
             '"<name> sound 2.m4a"' in t and "never written over" in t and "shows the recording once" in t)
        case(f"{name}: Remove this song is the page's button (two taps), to the computer's own Trash (the Recycle Bin on a PC), never a delete, and Put Back brings it back",
             "**Remove this song**" in t and '"Move it to the Trash?"' in t and "the computer's own Trash (the Recycle Bin on a PC)" in t
             and "never a delete" in t and "Put Back (Restore on a PC) brings it back" in t and "no button for that yet" not in t)
        case(f"{name}: a recording's sounds go with it, the reel that had it picked goes back to no song, and another reel that picked it says her line when opened",
             "every sound taken from a recording" in t and 'goes back to "no song picked yet"' in t and "another reel of the shoot that had it picked says" in t
             and ('"' + (gone.group(1) if gone else "?") + '"') in t)
        case(f"{name}: only a song in the shoot's own Music folder can go; one in the Photos folder stays and is theirs to take out",
             "Only a song in the shoot's own Music folder can go" in t and "a recording in the Photos folder stays" in t and "theirs to take out of that folder themselves" in t)
        case(f"{name}: the assistant has no command for it, never moves, renames or deletes a song itself, and points at the button",
             "You have no command for it" in t and "never move, rename or delete a song or a recording yourself" in t and "point at the button" in t)
    case("the route exists: POST /reel-song-remove in reel_page.py's list and remove_song goes through this_computer.trash_many, the one door",
         '"/reel-song-remove"' in rp and "def remove_song(body):" in rp and "this_computer.trash_many(paths, music_dir(kit))" in rp and "def trash_many(paths, inside):" in tc)
    case("her four page lines and her two server lines are in reel_page.WORDS, word for word",
         all(x in rp for x in ('"song_remove": "Remove this song"', '"song_sure": "Move it to the Trash?"', '"song_removing": "Removing…"',
                               '"song_trashed": "Moved to the Trash. To get it back, open the Trash in Finder and choose Put Back."',
                               '"song_not_here": "That song isn\'t in this shoot\'s folder anymore."',
                               '"song_cant_trash": "I couldn\'t move that song to the Trash. Drag it out of the shoot\'s Music folder in Finder instead."')))
    case("where-things-live.md says a removed song is in the computer's own Trash with its sounds, its lines in reel-sounds.json dropped, nothing else written down",
         "**Remove this song**" in where and "goes to the computer's own Trash with every sound taken from it" in where
         and "its lines in `reel-sounds.json` are dropped, the version before kept" in where and "nothing else is written down about it" in where)
    case("arrange.md gives the page's own line for a picked song that is gone", bool(gone) and ('"' + gone.group(1) + '"') in arr, gone and gone.group(1))
    case("where-things-live.md names the note of which recording each sound came from, and what is in it",
         "`reel-sounds.json`" in where and "`reel-sounds.prev.json`" in where and "`reel-sounds.lock`" in where and "a hash of its first megabyte, never a path" in where
         and 'SOUNDS = "reel-sounds.json"' in rp and 'SOUNDS_PREV = "reel-sounds.prev.json"' in rp and 'SOUNDS_LOCK = "reel-sounds.lock"' in rp)
    case("where-things-live.md: \"sound 2\" up to 99, none written over, and a sound with no line goes by the files' times",
         'up to 99' in where and "SOUND_SPARES = 98 " in rp and "goes by the files' times" in where)


def check_queue_v25():
    """The post kit and the posting queue with several reels, captions optional (Nicole's v25, sections 6 and 7;
    stage K of the v26 build): the instructions say what the pages say, and name commands that exist."""
    sys.path.insert(0, str(SCRIPTS))
    import kit
    pq = read(SCRIPTS / "posting_queue.py")
    rem = read(SCRIPTS / "reminders.py")
    post = " ".join(read(SM / "parts" / "posting-queue.md").split())
    kitp = " ".join(read(SM / "parts" / "post-kit.md").split())
    arr, where = " ".join(read(SM / "parts" / "arrange.md").split()), " ".join(read(SM / "parts" / "where-things-live.md").split())
    K = kit.KIT_WORDS
    question = K["nocap_title"].format(piece="reel") + ". " + K["nocap_text"]
    for name, t in (("posting-queue.md", post), ("post-kit.md", kitp)):
        case(f"{name}: a caption is optional, and the page's question is given in the page's own words, with its two buttons",
             ('"' + question + '"') in t and f"**{K['nocap_add']}**" in t and f"**{K['nocap_write']}**" in t, question)
        case(f"{name} no longer says Add to my queue needs a caption", "only works once the piece is made and has its caption" not in t
             and "once it is made and has its caption" not in t and "write its caption first" not in t)
    case("posting-queue.md: with no caption the assistant asks her question, never marks it ready silently, never presses them to write one",
         "ask her question in her words" in post and "don't mark it ready silently" in post and "never press them to write one" in post)
    case("post-kit.md: step 3 is locked only until the piece is made, in the page's own words", "Make your reel first..." in kitp
         and '"Its caption can come later, or not at all."' in kitp and "Its caption can come later, or not at all." in K["ready_nocap"])
    case("the chat's ready can name which reel, and the command takes it", '`posting_queue.py ready "beach reel" --reel "White Backdrop"`' in post
         and 'sp.add_argument("--reel"' in pq and "def reel_piece_for(" in pq)
    case("posting-queue.md: a reel that isn't made is refused, a name that fits none lists the reels, and never pick one for them",
         "is refused with nothing changed" in post and "lists the shoot's reels" in post and "never pick one for them" in post
         and "isn't made in CapCut yet" in pq)
    case("posting-queue.md: the page's and the chat's name for a reel's post", '"<shoot> reel · <reel name>"' in post and '"<shoot> reel (<reel name>)"' in post
         and "' · '+esc(x.reel_name)" in pq and "({p['reel_name']})" in pq)
    case("posting-queue.md and post-kit.md: the kit page's question and each reel's place, in the page's own words",
         all(('"' + K["which_title"] + '"') in t for t in (post, kitp)) and all(K[k] in post for k in ("r_made", "r_not", "r_in", "r_posted", "reel_empty")))
    case("posting-queue.md: the reel cover picker in her words", all(x in post for x in ('"From your reel, in the order it plays"', "**+ Use a different photo**",
                                                                                         '"Any other photo from the shoot"', "**Hide the other photos**"))
         and all(("'" + x + "'") in pq for x in ("From your reel, in the order it plays", "+ Use a different photo", "Any other photo from the shoot", "Hide the other photos")))
    note = re.search(r'^NO_CAPTION = "([^"]+)"', rem, re.M)
    case("posting-queue.md says what a reminder's notes hold for a post with no caption, as reminders.py writes it",
         bool(note) and ('"' + note.group(1) + '"') in post and "still gets its reminder" in post, note and note.group(1))
    case("posting-queue.md: the first reel keeps its place, nothing is renamed; each reel has its own caption (Nov 23)",
         "nothing already in the queue is renamed or moved" in post and "one caption and one set of hooks for the shoot's reels" not in post
         and "**Each reel has its own words (Nicole, Nov 23" in post)
    case("arrange.md points a second reel at its own place in the queue", '`posting_queue.py ready "<shoot> reel" --reel "<name>"`' in arr)
    case("where-things-live.md names what a reel's piece carries", "`version`" in where and "`reel_name`" in where and "`...-reel-v2`" in where
         and 'x["version"], x["reel_name"] = ' in pq)


def check_trash_helper():
    """The Trash helper (Nicole's v27, Nov 17; Lane E's E11): parts/where-things-live.md says nothing of the
    photographer's is ever deleted, that the one door out is the computer's own Trash (the Recycle Bin on a PC)
    through this_computer.py, names the way back in Nicole's words, and gives the assistant no command for it."""
    where = " ".join(read(SM / "parts" / "where-things-live.md").split())
    tc = read(SCRIPTS / "this_computer.py")
    case("where-things-live.md says nothing of the photographer's is ever deleted, and the Assistant keeps no Trash of its own",
         "never delete a file or a folder of the photographer's" in where and "keeps no Trash of its own" in where)
    case("where-things-live.md names the computer's own Trash and the Recycle Bin as the one door out, through this_computer.py's trash",
         "Finder's Trash on a Mac, the Recycle Bin on a PC" in where and "`this_computer.py`'s `trash`" in where and "the only door" in where
         and "def trash(path, inside):" in tc)
    case("where-things-live.md says what the door refuses, in the helper's own terms (a link, a path outside the one folder, a drive with no Trash, never a delete)",
         "refuses a link, a path outside the one folder it is told to work in, and a drive with no Trash, and it is never a delete" in where)
    case("the way back is Nicole's line on a Mac (TRASH_BACK) and ours on a PC, in where-things-live.md word for word",
         "open the Trash in Finder and choose Put Back" in where and "open the Recycle Bin in File Explorer and choose Restore" in where
         and '"open the Trash in Finder and choose Put Back"' in tc and '"open the Recycle Bin in File Explorer and choose Restore"' in tc)
    case("the assistant has no chat command that moves anything to the Trash, and asked to delete says it never deletes",
         "You have no chat command that moves anything to the Trash" in where and "say you never delete" in where)
    case("this_computer.py's own words name no Claude and no path", "Claude" not in tc[tc.index("TRASH_WORD ="):tc.index("def trash_for_tests")])


def check_watch_direct_broll():
    """Nicole's v27, Lane A's stage 4: Watch your reel before you make it, Would you like to direct this edit? and
    B-roll on the page. The reel skill has the section "Edit my reel" (read the direction, arrange within it, set
    it up with reel_page.py direct, say what was arranged), the core table sends the line there, arrange.md says
    the two steps in the page's words and that the watch step is the page's (not the assistant's), the make takes
    --variation and --song-start, and where-things-live.md names direct, onscreen and the preview's folder."""
    rp = read(SCRIPTS / "reel_page.py")
    arr, where = " ".join(read(SM / "parts" / "arrange.md").split()), " ".join(read(SM / "parts" / "where-things-live.md").split())
    reel, core = " ".join(read(REEL / "SKILL.md").split()), read(SM / "SKILL.md")
    words = dict(re.findall(r'^    "(direct_h2|direct_b|direct_for|direct_note|watch_h2|pv_part|pv_mix|pv_undo|pv_redo|pv_make|os_wl|os_save|sum_broll)": "([^"]+)"', rp, re.M))
    case("the page's words for the direct step, the watch step and B-roll are in reel_page.py (13 of them)", len(words) == 13, sorted(words))
    case("the reel skill has the section Edit my reel: read the direction with note, follow it exactly, never widen it, the style that fits, a moment not on a card is a look for that moment only, reel_page.py direct, say what was arranged",
         '## Edit my reel: "Edit my reel for <shoot>[, <reel>], and follow my direction"' in reel and "reel_page.py note" in reel and "follow it exactly, never widen it" in reel
         and "a footage look for that moment only" in reel and "reel_page.py direct" in reel and "--style first|reveal|backforth|bookends --clips" in reel
         and "Never write the style, the clips or the order into the reel page's records any other way" in reel and "Say in two lines what you arranged" in reel)
    case("the reel skill says the watch step is the page's: press play on the page, Try another mix, Undo; never describe a cut you haven't seen the plan of",
         "Watch your reel before you make it (Nicole, Nov 16)" in reel and "press play on the page to watch it" in reel and "Try another mix" in reel
         and "never \"make it\"" in reel and "You never describe a cut you haven't seen the plan of" in reel)
    case("the reel skill's make takes --variation and --song-start, and says what they are", "[--variation N] [--song-start S]" in reel and "`--variation N` is which mix" in reel and "`--song-start S` where the song starts" in reel)
    case("the reel skill says what B-roll is (clips only, no photos, Words on screen, into CapCut as plain text) and what Save my video does (the finished MP4 in the shoot's Reels folder, never over the first, counts as made, no command of yours, the PC gap)",
         "B-roll (Nicole's v27, Nov 17) is a kind of reel with no photos" in reel and "Words on screen" in reel and "plain text over the whole reel" in reel
         and "**Save my video** (Nicole's v27) is the main button of a B-roll reel's watch step" in reel and "not built yet" not in reel and "isn't ready yet" not in reel
         and "Saving your video, with your song and words. This takes about a minute." in reel and "in this shoot's Reels folder. It's ready to post." in reel
         and "**Open the folder**" in reel and "never over the first" in reel and "A saved video counts as made" in reel and "You have no command for it" in reel
         and "saving a finished video isn't on a PC yet" in reel and "Videos saved from the page" in reel)
    case("the core table sends Edit my reel to the reel skill", '| "Edit my reel for <shoot>[, <reel>], and follow my direction"' in core and 'the reel skill\'s "Edit my reel"' in core)
    case("arrange.md: the direct step in the page's words, its line's shapes, sent to the reel skill's Edit my reel, and told apart from the footage box",
         ("**" + words["direct_h2"] + "**") in arr and ('"' + words["direct_b"] + '"') in arr and "**\"Edit my reel for <shoot>\"**" in arr and ", and follow my direction" in arr
         and 'the reel skill\'s section "Edit my reel"' in arr and "reel_page.py direct" in arr and "This is a different note from the footage box in step 1" in arr)
    case("arrange.md: the watch step in the page's words (Another part of this song, Try another mix, Undo and Redo, Make this one in CapCut), the last step, and the page's not the assistant's",
         ("**" + words["watch_h2"] + "**") in arr and all(("**" + words[k] + "**") in arr for k in ("pv_part", "pv_mix", "pv_make")) and "**Undo** and **Redo**" in arr and "the last step, on every kind" in arr
         and "Press play on the page beside us" in arr)
    case("arrange.md: B-roll is clips only with Words on screen, Save my video built (the Reels folder, never over the first, Open the folder, counts as made, the PC gap, no command); make takes --variation and --song-start",
         "A B-roll reel is clips only" in arr and ("**" + words["os_wl"] + "**") in arr and "**Save my video** (the finished MP4 made on the page, no CapCut needed) is the main button of its watch step" in arr
         and "in the shoot's Reels folder" in arr and "never over the first" in arr and "**Open the folder**" in arr and "a saved video counts as made" in arr
         and "saving a finished video isn't on a PC yet" in arr and "You have no command for it; asked for the file" in arr
         and "`--variation N` and `--song-start S`" in arr and "[--variation N] [--song-start S]" in arr and "isn't ready yet" not in arr and "still being built" not in arr)
    case("where-things-live.md names direct, onscreen, the made entries' variation and song_start, and the preview's own folder",
         "`direct`, Nov 17" in where and "`onscreen`: the words, the font, the style" in where and "`variation`, which mix it was, and `song_start`" in where and "`reel-preview/`" in where)
def check_instructions_v27_lane_a():
    """Nicole's v27, Lane A's A17: the instructions say the reel page as it is. The chooser is the way in (the door
    lines say "pick the kind"), the path at the top is the way back, the three chat lines of hers are in the reel
    skill and the core table, nothing still says Use this moment, Watch your footage and pick your own, the Trim
    panel as a thing on the page or "there's no Remove yet", the PC gaps (Save my video, the editor without stills,
    naming) are named in the PC part and the PC guide in this_computer's own words, and the core's description
    stays under 1,024 characters."""
    sys.path.insert(0, str(SCRIPTS))
    import this_computer
    reel = " ".join(read(REEL / "SKILL.md").split())
    core = read(SM / "SKILL.md")
    arr = " ".join(read(SM / "parts" / "arrange.md").split())
    pc = " ".join(read(SM / "parts" / "on-a-pc.md").split())
    where = " ".join(read(SM / "parts" / "where-things-live.md").split())
    guide = " ".join(read(ROOT / "docs" / "SETUP-GUIDE-PC.md").split())
    parts = {p.name: " ".join(read(p).split()) for p in sorted((SM / "parts").glob("*.md"))}
    case("the reel skill and arrange.md open the page on the chooser: the door line says pick the kind of reel (Just photos, Behind the scenes, Talking to camera or B-roll)",
         "Pick the kind of reel you want (Just photos, Behind the scenes, Talking to camera or B-roll)" in reel
         and arr.count("Pick the kind of reel you want (Just photos, Behind the scenes, Talking to camera or B-roll)") == 1 and "Pick Just photos (or Behind the scenes, with your footage)" in arr
         and "Choose Just photos (or add your footage)" not in reel + arr)
    case("arrange.md says the path at the top is the way back (Reels is the chooser), not the old link",
         "The path at the top of every reel page (Home › <shoot> post kit › Reels › B-roll) is the way back: Reels is the chooser" in arr and "goes back to the chooser" not in arr)
    for line in ('"Name my clips for <shoot>"', '"Edit my reel for <shoot>[, <reel>], and follow my direction"', '"Pick my reel photos for <shoot>"', '"Look through my footage for <shoot>"'):
        case("her line %s is in the reel skill and in the core's table (the core's rows say it in their own case)" % line, line in reel and line.lower() in core.lower())
    case("the core's table sends \"save my video\" and \"where did my B-roll video go\" to the reel skill",
         '"save my video", "where did my B-roll video go"' in core and "the reel skill, `../assistant-make-a-reel/SKILL.md`" in core.split('"save my video"')[1][:600])
    stale = ("Use this moment", "Watch your footage and pick your own", "there's no Remove", "Remove a song isn't built", "not built yet", "still being built", "isn't ready yet")
    found = [(name, w) for name, text in list(parts.items()) + [("reel SKILL.md", reel), ("core SKILL.md", " ".join(core.split()))] for w in stale if w in text]
    case("no part, the reel skill or the core still says Use this moment, Watch your footage and pick your own, there's no Remove, not built yet, still being built or isn't ready yet", not found, found)
    case("the Trim panel is only ever said to be gone from the page", "Trim panel" not in reel and arr.count("Trim panel") == 1 and "is gone from the page with v27" in arr
         and all("Trim panel" not in t for n, t in parts.items() if n != "arrange.md"))
    case("the PC part names Save my video's gap in this_computer.NO_VIDEO_PC's own words, with the clips' naming and the editor without stills",
         this_computer.NO_VIDEO_PC in pc and "Save my video (a B-roll reel's finished MP4, Nicole's v27) isn't on a PC yet either" in pc
         and "On a PC the timeline has no pictures along it yet. The trim, its ends and the times work the same." in pc
         and "Naming their clips (\"Name my clips for <shoot>\") can't run on a PC either" in pc and "Don't offer to install anything for it" in pc)
    case("the PC part's \"What can't you do on a PC?\" box and the PC guide's list both name it, in this_computer's words", ("> - Saving a B-roll reel as a finished video. " + this_computer.NO_VIDEO_PC) in read(SM / "parts" / "on-a-pc.md")
         and ("- **Saving a B-roll reel as a finished video.** " + this_computer.NO_VIDEO_PC) in read(ROOT / "docs" / "SETUP-GUIDE-PC.md"))
    case("the PC guide's footage lines say the editor's clips (Start here, End here, Add clip), not Use this moment, and the Save my video gap", "Use this moment" not in guide
         and "Start here, End here and Add clip" in guide and "Save my video (a B-roll reel's finished MP4) isn't on a PC yet" in guide)
    case("this_computer.NO_VIDEO_PC says what works instead (CapCut) and that the words go with it, no Finder or QuickTime",
         "Make this one in CapCut works here, and your words go with it." in this_computer.NO_VIDEO_PC and not any(w in this_computer.NO_VIDEO_PC for w in ("Finder", "QuickTime")))
    case("where-things-live.md: the Reels folder (theirs, beside Photos, Footage and Music, never written over), the made entry's video and seconds, reel-video/",
         "`Reels`, inside the kit's folder beside Photos, Footage and Music" in where and "Nothing in it is ever written over" in where
         and "with `video`, the file's name in the shoot's Reels folder, and `seconds`, and counts as made" in where and "`reel-video/` (Save my video's own" in where)
    desc = re.search(r"^description:\s*(.*)$", core, re.M)
    case("the core's description stays under 1,024 characters (the new lines live in the body)", desc and len(desc.group(1)) <= 1024, len(desc.group(1)) if desc else None)


def check_posted_and_path_v27():
    """Posted on the post itself, the Reels card and the path at the top (Nicole's v27, Lane D): the instructions
    say what the pages say, in the pages' own words, and name commands that exist."""
    import html as _html
    sys.path.insert(0, str(SCRIPTS))
    import kit
    import look
    import words_page
    pq = read(SCRIPTS / "posting_queue.py").replace("\u2019", "'")
    post = " ".join(read(SM / "parts" / "posting-queue.md").split()).replace("\u2019", "'")
    kitp = " ".join(read(SM / "parts" / "post-kit.md").split())
    wordsp = " ".join(read(SM / "parts" / "words.md").split())
    where = " ".join(read(SM / "parts" / "where-things-live.md").split())
    arr = " ".join(read(SM / "parts" / "arrange.md").split())
    rows = table_rows(read(SM / "SKILL.md"))
    # --- the switch and the posted post, in the page's own words ---
    said = {"Not posted": r"not_posted:'([^']+)'", "Posted": r"\bposted:'([^']+)'", "the posted post's line": r"in_feed:'([^']+)'",
            "the posted tile's tip": r"posted_tip:'([^']+)'", "Back in your queue": r"back_in_queue:'([^']+)'", "the Posted toast": r"posted_toast:'([^']+)'"}
    for what, pat in said.items():
        m = re.search(pat, pq)
        case(f"the posting page still says: {what}", bool(m))
        if m:
            case(f"... and posting-queue.md says it the same way: {m.group(1)[:50]}", m.group(1) in post, m.group(1))
    sect = re.search(r"\*\*Posted, on the post itself.*?(?=- \*\*|## )", post)
    case("posting-queue.md has the Posted-on-the-post section: the switch beside Done, no date and no posted-on label, read my Instagram grid, the switch only",
         bool(sect) and all(x in sect.group(0) for x in ("**Not posted** switch beside **Done**", 'no "posted on" label', '"read my Instagram grid"', "the switch and Done only", "no photo strip, no words and no reminder")))
    case("... and that section never says Claude (the pages say the Assistant)", bool(sect) and "Claude" not in sect.group(0))
    case("the page draws posted posts from the server's list, never filtering by read_at itself (so the part's rule is the server's)",
         "S.posted" in pq and "def posted_in_grid" in pq or ("S.posted" in pq and "POSTED_DAYS" in pq))
    # --- unposted: the command, its line, the row ---
    have = set(re.findall(r'add_parser\("([a-z-]+)"\)', pq))
    case("posting_queue.py has the unposted command and the part names it with its line", "unposted" in have
         and '`posting_queue.py unposted "beach reel"`' in post and "That one didn\'t go out after all" in post)
    case("the part quotes what unposted prints, as the script prints it", "back in your queue, ready to post" in post
         and 'back in your queue, ready to post" + (f", down for' in pq)
    case("the part says unposted looks only among the posted pieces (so the shoot's other reel in line is never taken)",
         "looks only among the posted pieces" in post and 'find(p, a.piece, statuses=("posted",))' in pq)
    case("the part says a reminder that was on comes back on the new date, the same event, never a second one",
         "the same event, moved; never a second one" in post and "the same event moved, never a second one" in post)
    hit = [r for r in rows if "\"that one didn't go out after all\"" in r.split(" | ")[0].replace("\u2019", "'")]
    case("the core's row for the posting queue takes \"that one didn't go out after all\" and \"it's in my feed now\" to parts/posting-queue.md",
         len(hit) == 1 and "`parts/posting-queue.md`" in hit[0] and "\"it's in my feed now\"" in hit[0].replace("\u2019", "'"), hit)
    # --- the Reels card: its name and its two buttons, from kit.py ---
    case("kit.py's card is Reels, and its buttons are Create my reels / Create another reel",
         kit.KIT_WORDS["reel"] == "Reels" and kit.REEL_CREATE == "Create my reels" and kit.REEL_AGAIN == "Create another reel")
    for name, t in (("post-kit.md", kitp), ("arrange.md", arr)):
        case(f"{name} names the Reels card and quotes both buttons with their arrow", "Reels card" in t
             and f'"{kit.REEL_CREATE} \u2192"' in t and f'"{kit.REEL_AGAIN} \u2192"' in t and "once any reel of the shoot is made" in t)
    stale = [f"{rel(q)}:{i}" for q in instruction_files() for i, ln in enumerate(read(q).splitlines(), 1) if re.search(r"\bReel card\b|\(Reel, Carousel", ln)]
    case("no instruction still calls it the Reel card", not stale, stale)
    # --- the path at the top: look.py's words, told in the kit part and the words part ---
    C = look.CRUMB_WORDS
    kitcrumb = C["post_kit"].format(shoot="Beach")
    path_kit = f"{C['home']} {C['sep']} {kitcrumb}"
    path_words = f"{path_kit} {C['sep']} {words_page.WORDS['crumb_captions']}"
    case("post-kit.md tells the path on the kit page and on the words page, in look.py's and words_page.py's own words",
         f"**{path_kit}** on the kit page" in kitp and f"**{path_words}** on the words page" in kitp and "Press Home at the top of the page" in kitp)
    case("post-kit.md says the kit's own crumb is not a link and Home is (as look.crumbs draws them)",
         "it is where they are, so it is not a link here" in kitp and "Home is a link to the home base" in kitp
         and "aria-current='page'" in read(SCRIPTS / "look.py") and look.HOME_PATH == "/home")
    case("words.md tells the words page's path and how to get back", f"**{path_words}**" in wordsp and "Press Beach post kit at the top of the page" in wordsp)
    case("the posting queue page still keeps Back to home, as the kit part says", "keeps its Back to home" in kitp and "Back to home</span>" in pq)
    case("the kit page's and the words page's bars are built by look.crumbs (else the parts' path is a story)",
         "trail if trail is not None else [(here, None)]" in read(SCRIPTS / "kit.py") and "look.crumbs(trail)" in read(SCRIPTS / "kit.py") and "look.crumbs(look.kit_trail(kit_name) + [(w[\"crumb_captions\"], None)])" in read(SCRIPTS / "words_page.py"))
    # --- "What's a post kit?": her Make posts paragraph, whole ---
    m = re.search(r'\*\*"What\'s a post kit\?"\*\* Answer in Nicole\'s words from the Make posts screen, whole: "([^"]+)"', kitp)
    case("post-kit.md answers \"What's a post kit?\" with one quoted paragraph", bool(m))
    hers = [f for base in (ROOT, Path("/Users/dustindamron/Projects/hf-tools"))     # a worktree looks beside the main checkout, as the kit tests do
            for f in sorted((base / "reference-private").glob("nicole-handoff-v2[7-9]-*/Carousel designer and reel picker/pages/make-posts.html"), reverse=True)]
    if m and hers:
        page = " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", read(hers[0]))).split())
        case(f"... and it is her paragraph, word for word ({hers[0].parent.parent.parent.name})", m.group(1) in page, m.group(1))
    else:
        case("... (her v27 pack is not on this computer, so the paragraph is not compared)", True)
    # --- where things live ---
    case("where-things-live.md says what posted_at, feed.json and read_at decide, with the script's 30 days",
         all(x in where for x in ("`posted_at`", "`feed.json`", "`read_at`", "last 30 days", "(`unposted`)")) and re.search(r"^POSTED_DAYS = 30\b", pq, re.M))


def check_second_copy():
    """Make a second copy, from the report, after the backup (Dustin, Nov 19): the instructions for it."""
    print("\nA second copy after the backup (Nov 19)")
    flat = lambda n: re.sub(r"\s+", " ", read(SM / "parts" / n))   # noqa: E731
    a, f, w, b = (flat(n) for n in ("after-the-report.md", "first-backup-setup.md", "where-things-live.md", "backup.md"))
    core = re.sub(r"\s+", " ", read(SM / "SKILL.md"))
    case("the core's table sends \"make a second copy\" to after-the-report.md",
         "\"make a second copy\"" in core and "A second copy, after the backup" in core)
    case("after-the-report.md: the section, the check first, then the copy in the background",
         "## A second copy, after the backup" in read(SM / "parts" / "after-the-report.md")
         and "second_copy.py \"<the backup's folder>\" --to \"<that drive>\" --check" in a
         and a.index("--to \"<that drive>\" --check") < a.index("# in the background") and "Run `--check` first, every time." in a)
    case("after-the-report.md: what the report's button and panel say, word for word",
         all(x in a for x in ("Anything you'd like to change?", "Your photos are safe either way. These are here if you want them.",
                              "**Make a second copy**", "Which drive should the second copy go on?", "**Look again**",
                              "**Do this after every backup**", "**Make the second copy**", "Keep your card in until this is done.")))
    case("after-the-report.md: it is the card's layout, never sorted, and the honest lines are said as they are",
         "never sorted or renamed" in a and "It was made from the copy on Big Kahuna, since the card wasn't in." in a
         and "5 video clips are the upright ones from your drive." in a and "never more than it says" in a)
    case("after-the-report.md: never called made before the last line says so; nothing deleted to make it pass; never a cloud folder",
         "Never say there is a second copy until the command's last line says it is made." in a
         and "never delete or move anything to make it pass" in a and "Never a cloud folder" in a)
    case("after-the-report.md: the four exit codes, the missed second drive, and the eject line",
         all(x in a for x in ("0 done", "2 refused before anything was written", "3 stopped part way", "1 problems"))
         and "Your second drive wasn't plugged in, so there's one copy for now. Plug it in and press Make a second copy." in a
         and "A second copy is still being made from this card. It won't be long." in a and "It won't be long." in b)
    case("first-backup-setup.md: the table's second-copy row points at the report's button and second_copy.py",
         "**Make a second copy** on the report" in f and "second_copy.py" in f)
    case("where-things-live.md names the new records",
         all(x in w for x in ("second-copy.json", "manifest.before-second-copy.json", "second-missed.json", "second-copy.lock")))


def check_backup_options():
    """The other options on the report (Dustin, Nov 19): another card, naming, the next drive, the note line."""
    print("\nWhat the report lets them change (Nov 19)")
    flat = lambda n: re.sub(r"\s+", " ", read(SM / "parts" / n))   # noqa: E731
    a, f = flat("after-the-report.md"), flat("first-backup-setup.md")
    core = re.sub(r"\s+", " ", read(SM / "SKILL.md"))
    case("the core's table has the three new asks and sends them to after-the-report.md",
         all(x in core for x in ("\"this shoot was on two cards\"", "\"change how my shoots are named\"", "\"use a different drive next time\"",
                                 "What the report lets them change")))
    case("after-the-report.md: the section, and that a press on the page needs nothing run",
         "## What the report lets them change" in read(SM / "parts" / "after-the-report.md")
         and "You never need to run anything for a press on the page." in a)
    case("after-the-report.md: another card, word for word, with the chat way and what it does not do",
         all(x in a for x in ("**This shoot continues on another card.**", "Which backup is the other card?", "**Put them on one report**",
                              "Done. Both cards are on one report now.", "Each card's photos stay in their own folders.",
                              "Back up the other card first: put it in and say backup now. Then come back here and pick it.",
                              "shoot_report.py link \"<card 1's backup>\" \"<card 2's backup>\"", "nothing can merge two cards' photos into one folder today")))
    case("after-the-report.md: naming, word for word, with the chat ways",
         all(x in a for x in ("**Change how my shoots are named.**", "How should a shoot folder be named?", "**Rename this backup's shoots to match**",
                              "Name them your own way? Copy this into the chat:", "studio_file.py set --example", "studio_file.py set --offered 1",
                              "--offered 2", "studio_file.py set --file-names original", "the photos keep their names")))
    case("after-the-report.md: the next drive, word for word, and that nothing is ever moved",
         all(x in a for x in ("**Use a different drive next time.**", "Where should your next backup go?",
                              "Saved. Your next backup goes to LaCie Rugged. The photos from this backup stay where they are.",
                              "studio_file.py set --drive", "no button and no command moves a finished backup to another drive")))
    case("after-the-report.md: no Write a note to my client button any more (Nov 23), and where to read if they ask outright",
         "There is no Write a note to my client button any more" in a and "Write a note for the <shoot's name> shoot" not in a
         and "Never offer one" in a and "parts/client-note.md" in a and "A first look at your shoot." in a)
    case("after-the-report.md: the own-disk line as the report says it, and never a speech",
         "Your photos are on this Mac's own disk. An external drive is safer: if anything happens to the computer, the photos on it go too. "
         "Plug one in and press Use a different drive next time." in a and "Never say it before a backup" in a)
    case("first-backup-setup.md: the table names each button",
         all(x in f for x in ("**Use a different drive next time** on the report", "**Change how my shoots are named** on the report",
                              "**This shoot continues on another card** on the report"))
         and "**Write a note to my client**" not in f)
    sys.path.insert(0, str(SM / "scripts"))
    try:
        import report_page
        import first_look
        W, F = report_page.OUR_WORDS, first_look.OUR_WORDS
        said = all(x in a for x in (W["oc_button"], W["oc_which"], W["oc_go"], W["oc_done"], W["oc_quiet"], W["oc_none"], W["nm_button"], W["nm_q"],
                                    W["nm_apply"], W["nm_own"], W["nd_button"], W["nd_q"], F["note_button"], F["note_how"],
                                    W["own_disk"].format(computer="Mac")))
    except Exception as ex:  # noqa: BLE001
        said = False
        print("        ", ex)
    case("and every line it quotes is the line the page itself says (read from the scripts)", said)


def check_backup_zero():
    """A backup asks nothing before it copies (Dustin, Nov 19): the instructions as rewritten for it."""
    print("\nNo questions before the copy (Nov 19)")
    flat = lambda n: re.sub(r"\s+", " ", read(SM / "parts" / n))   # noqa: E731
    b, f, a, h, pc, c = (flat(n) for n in ("backup.md", "first-backup-setup.md", "after-the-report.md", "hello.md",
                                            "on-a-pc.md", "client-note.md"))
    gone = [w for w in ("Same as usual?", "How many memory cards for this shoot?", "What's on the card?",
                        "Looks good (recommended)", "Change something", "one screen, every time") if w in b]
    case("backup.md: the screen of questions before the copy is gone (Same as usual?, the cards question, What's on the card?, Change something)",
         not gone, gone)
    case("backup.md: the new starting line, and the walk-away line last and in bold",
         "Found your card: 3,931 photos, 127 GB. Copying to Big Kahuna now. Nothing on your card will be changed." in b
         and "**You can walk away. I'll have the report ready when you're back.**" in b)
    case("backup.md: the one extra sentence on a first backup, word for word",
         "This is our first backup together, so I'm doing it the usual way. On the report afterwards you can add a second copy, rename your shoots, and change where the next backup goes." in b
         and "This is our first backup together, so I'm doing it the usual way. On the report afterwards you can add a second copy, rename your shoots, and change where the next backup goes." in f)
    case("backup.md: the quiet check comes before the starting message and speaks only on a STOP; every STOP's words are still there",
         b.index("night.py --source \"<the card's path>\" --check") < b.index("Copying to Big Kahuna now.")
         and "It speaks only on a STOP" in b
         and all(w in b for w in ("Your memory card has stopped answering", "already holds a backup made from a different memory card",
                                  "would go onto the memory card itself", "onto the same drive the photos are coming from",
                                  "Windows gave your drives different letters today", "the card is already safe")))
    case("backup.md: the drive is chosen by `studio_file.py defaults`, and exit 5 is the one question",
         "studio_file.py defaults --source" in b and "ONE QUESTION before the first backup" in b and "NEEDS SETUP" not in b)
    case("backup.md: every card is its own backup now; the closing box has Show the report and Eject my card; --with only when they say the card continues the last one",
         "every card is its own \"backup now\"" in b and "Never ask how many cards there are" in b
         and "**Show the report** first and **Eject my card** second" in b and "--with" in b and "never guess that two cards belong together" in b)
    case("backup.md: what they say unasked about the card is still used for the name and kept word for word",
         "without being asked" in b and "client_note.py told --night" in b and "Never ask what is on the card" in b)
    case("backup.md: the phone page only when they ask, and the pointer the PC part follows is really there",
         "Phone taps: only when they ask" in b and "**Somewhere else this time.**" in b and "\"Somewhere else this time\"" in pc)
    case("backup.md: the glance is only the answer to \"what are my settings?\"",
         "studio_file.py glance" in b and "never shown before a backup" in b)
    numbered = re.findall(r"\*\*Question \d", f)
    case("first-backup-setup.md: no numbered questions and no conversation before the copy", not numbered and "asks nothing before it copies" in f
         and "I need to ask you a few quick questions" not in f, numbered)
    case("first-backup-setup.md: the defaults command and its three answers, and the one question in its two shapes",
         all(w in f for w in ("studio_file.py defaults --source", "`CHOSE:", "`ASK which-drive`", "`ASK no-drive`",
                              "\"Which drive should your photos go on?\"", "\"I don't see an external drive. Where should your photos go?\"",
                              "\"I'll plug one in\"", "\"On this Mac for now\"", "\"On this PC for now\"",
                              "studio_file.py defaults --drive", "studio_file.py defaults --computer")))
    case("first-backup-setup.md: the computer's own disk is their call, with no speech",
         "with no speech" in f and "Never refuse, never lecture" in f and "Quick note before we go on" not in f)
    case("first-backup-setup.md: the table of where each old question lives now; how they write to clients is never asked (Nov 23)",
         "| Was asked before the copy | Where it lives now |" in f and "Asked later, only when it is needed" in f
         and "How they write to clients is never asked" in f and "How do you usually write to clients?" not in f
         and "posting_queue.py interval" in f)
    case("after-the-report.md: nothing is asked by itself when they come back",
         "Ask nothing by yourself" in a and "Two one-time questions" not in a and "Ask them before anything else" not in a
         and "Never ask whether there are any" in a and "Never offer it by yourself" in a)
    case("client-note.md: retired (Nov 23): never offered, never 'on the report', saved nowhere; what they say about a card is still kept",
         "A backup no longer comes with a note to the client." in c and "you never offer a note" in c and "save it nowhere" in c
         and "client_note.py told --night" in c and "client_note.py save" not in c and "Question 5" not in c)
    case("hello.md: a first backup is described with no questions first",
         "I'll ask a few quick questions first" not in h and "There's nothing to answer first" in h)
    case("on-a-pc.md: the drive-letter stops stay, and nothing points at the old check-in screen",
         "Drive letters move, so check them before every backup" in pc and "one-screen check-in" not in pc and "never guess which letter is which" in pc)
    # the Nov 19 review of the zero-questions backup: what the instructions must say, and must no longer say
    case("the first-backup sentence no longer promises that anything can be changed on the report (rule 7)",
         "You can change any of it on the report afterwards" not in b + f + h and "you can change anything on the report afterwards" not in h
         and "nothing moves a finished backup" in f and "photo names are changed from the chat, not the report" in f)
    case("first-backup-setup.md: the drive is worked out with --dry-run, and saved only by the backup once its checks pass",
         'studio_file.py defaults --source "<the card\'s path>" --dry-run' in f and "`WOULD CHOOSE:" in f
         and "only after its own checks have passed" in f and '--dry-run' in b)
    case("first-backup-setup.md: the new answers: a maybe-card is asked about, an unusable only drive is said, a card is never the drive",
         all(x in f for x in ("`ASK is-this-the-drive`", "cannot be used today", "**A memory card is never the drive.**")))
    case("first-backup-setup.md: a wrong drive on file has a way out (SET-OTHER, then set --drive)",
         "`SET-OTHER` (exit 6)" in f and "**When the drive on file is the wrong one.**" in f and "studio_file.py set --drive" in f)
    case("first-backup-setup.md: where on the drive is in plain sight unless a folder is plainly named for shoots, and the starting message names a folder",
         "right on the drive, where they will see it" in f and "Never inside a photo library or catalog" in f
         and "into your Photo Shoots folder" in f and "into your Photo Shoots folder" in b)
    case("backup.md: a second card of the day takes the next name by itself; only a name they gave stops",
         "With no name given this never stops" in b and "saturday card 2" in b and "the name THEY gave" in b)
    case("backup.md: the second copy is made after the backup and never holds it up",
         "it is made right after the backup itself and never holds it up" in b)
    case("hello.md: backup now pasted from the home page starts the backup, with no Want to dive in?",
         'never explain and never ask "Want to dive in?"' in h and "start the backup straight away" in h)
    a2 = re.sub(r"\s+", " ", read(SM / "parts" / "after-the-report.md"))
    src = read(SM / "scripts" / "shoot_report.py")
    case("after-the-report.md: a wrong card can be taken off a shoot's report, with a command shoot_report.py has",
         "shoot_report.py unlink" in a2 and 'add_parser("unlink"' in src and "no command that takes a card off" not in a2)
    case("after-the-report.md: a second copy refuses any memory card, and changed photos are never called lost",
         "It refuses a memory card (this backup's own or any other" in a2 and '"could not be found" when it says they were changed' in a2
         and "**The saved second drive had trouble during a backup**" in a2)
    import home_base
    case("the backups screen no longer says a question or two is asked (its steps box went with her v31: backing up starts in the box on the home page)",
         "b_s2_small" not in home_base.WORDS and "b_s2_small" not in home_base.OUR_WORDS
         and "quick question" not in " ".join(list(home_base.WORDS.values()) + list(home_base.OUR_WORDS.values())))


def check_vault_core():
    """The vault as a real post kit (Nicole's v29, 1.3; stage 6): where it lives, and the designer's blank first design."""
    print("\nThe vault's folder and records (Nov 19)")
    where = re.sub(r"\s+", " ", read(SM / "parts" / "where-things-live.md"))
    src = read(SM / "scripts" / "vault.py")
    for name in ("vault.json", "sheet.prev.json"):
        case(f"where-things-live names {name}, and vault.py still uses that name", f"`{name}`" in where or f"`.kit/{name}`" in where and f'"{name}"' in src)
    for key in ("numbers", "next", "out", "from"):
        case(f"where-things-live names vault.json's `{key}`, and vault.py still writes it", f"`{key}`" in where and f'"{key}"' in src)
    case("it says the vault is found by its mark, is made only by a command, and copies no photo",
         '"vault": true' in where and "never by its name" in where and "`vault.py ensure`" in where and "no photo is copied to be in it" in where)
    case("it says the vault only reads other post kits", "the vault only reads other post kits and never writes anything into one" in where)
    for cmd in ("show", "ensure", "relist", "members"):
        case(f"`vault.py {cmd}` is a command vault.py has", f"`vault.py {cmd}" in where and f'add_parser("{cmd}")' in src)
    arr = re.sub(r"\s+", " ", read(SM / "parts" / "arrange.md"))
    des = read(SM / "scripts" / "design.py")
    case("the designer's blank first design in the vault: the line design.py prints starts BLANK:, and arrange.md says what to say for it",
         'OPEN_NEW_BLANK = "BLANK:' in des and "If it starts `BLANK:`" in arr and "blank slides to start" in arr)


def check_vault_everything():
    """See everything in it (Nicole's v29, 1.6; stage 11): what the parts say, held to the code."""
    print("\nSee everything in it, Remove from my vault, Put it back (Nov 19)")
    kitp, core, where = read(SM / "parts" / "post-kit.md"), read(SM / "SKILL.md"), read(SM / "parts" / "where-things-live.md")
    src, page = read(SM / "scripts" / "vault.py"), read(SM / "scripts" / "vault_page.py")
    sec = kitp.split("## My vault: one post kit for every shoot", 1)[-1].split("\n## ", 1)[0]
    case("the switch is on, so the strip's link is drawn", "\nEVERYTHING = True" in src and "**See everything in it**" in sec)
    case("See everything in it: the page's address, a route vault_page.py answers", "`/vault.html`" in sec and '"/vault.html"' in page)
    case("her rule is there in her words, and Use it in a reel adds nothing", "**Nothing gets picked on this page; making happens in the post kit**" in sec
         and "it adds nothing to any reel" in sec and '"use": "Use it in a reel"' in page)
    case("take this out of my vault: `vault.py out`, a command vault.py has, by --photo or --clip", "`python3 <scripts>/vault.py out --photo <its vault number>`" in sec
         and '`python3 <scripts>/vault.py out --clip "<shoot\'s folder>:<id>"`' in sec and '("out", "take one photo or clip out' in src and '"--photo"' in src and '"--clip"' in src)
    case("it says nothing is deleted or moved, and to ask when more than one could be meant", "**Nothing is deleted and nothing is moved:**" in sec and "ask before taking anything out" in sec)
    case("the lines it tells the assistant to say are the ones vault.py says", "Taken out of your vault. The photo itself is still in its shoot, and nothing was deleted." in sec
         and '"photo_out": "Taken out of your vault. The photo itself is still in its shoot, and nothing was deleted."' in src
         and "\"Back in your vault.\"" in sec and '"back": "Back in your vault."' in src)
    case("put it back: `vault.py back`, a command vault.py has; the photo keeps its number and is not put back into a reel by itself",
         "`python3 <scripts>/vault.py back --photo <number>`" in sec and '("back", "put a photo or clip that was taken out back' in src
         and "comes back with the number it had" in sec and "not put back into a reel's order by itself" in sec)
    case("the page's own names for it are the ones on the page", "**Put it back**" in sec and "**Taken out of my vault**" in sec and '"put_back": "Put it back"' in page
         and '"out_fold": "Taken out of my vault ({n})"' in page and "**Remove from my vault**" in sec and '"remove": "Remove from my vault"' in page)
    case("the core's table sends see everything, take this out and put it back to that section",
         '| "see everything in it", "show me everything in my vault", "what\'s in my vault?", "take this out of my vault", "remove that clip from my vault", "put it back in my vault" | `parts/post-kit.md`, "My vault"' in core)
    case("where-things-live says what the out list holds, that only vault.json is written, and names vault.prev.json", "`vault.prev.json`" in where and '"vault.prev.json"' in src
         and "`<shoot's folder>:<the clip's id>`" in where and "writes only this file" in where and "`vault.py out`" in where and "`vault.py back`" in where)


def check_vault_search():
    """Photo descriptions and the search rule (Nicole's v29, 1.4 and 1.5; stage 8): what the parts say, held to the code."""
    print("\nDescribing photos so they can be found, and search (Nov 19)")
    kitp, where, core, pcp = read(SM / "parts" / "post-kit.md"), read(SM / "parts" / "where-things-live.md"), read(SM / "SKILL.md"), read(SM / "parts" / "on-a-pc.md")
    src, vsrc, tc = read(SM / "scripts" / "photo_words.py"), read(SM / "scripts" / "vault.py"), read(SM / "scripts" / "this_computer.py")
    guide = read(ROOT / "docs" / "SETUP-GUIDE-PC.md")
    case("post-kit.md has the section", "\n## Describing photos so they can be found\n" in kitp)
    sec = kitp.split("## Describing photos so they can be found", 1)[-1].split("\n## ", 1)[0]
    case("it says no photo is ever renamed or changed, in her words", "**No photo is ever renamed or changed for this**" in sec and "I don't want the assistant to rename the photos" in sec)
    case("her progress line is in the part and in the code, whole", "Getting your photos ready to search: 40 of 72." in sec and '"getting": "Getting your photos ready to search: {done} of {total}."' in src)
    case("the quiet line and the line to copy are the page's own", 'Want search to find more, like "laughing" or "a kiss"? Copy this into the chat:' in sec
         and '"more": "Want search to find more, like \\"laughing\\" or \\"a kiss\\"? Copy this into the chat:"' in src
         and "**Describe my photos for <shoot>**" in sec and '"line": "Describe my photos for {shoot}"' in src and '"line_vault": "Describe the photos in my vault"' in src)
    case("descriptions only when they ask, never because a kit was opened or made", "only when they ask" in sec and "Never describe photos because a kit was opened or made." in sec)
    for cmd in ("status", "sheets", "describe"):
        case(f"the part names `photo_words.py {cmd}`, a command the script has", f"python3 <scripts>/photo_words.py {cmd} " in sec and (f'"{cmd}"' in src))
    case("the limits the part names are the script's: 140 letters, 2,000 photos a file, about 300 before asking, 48 to a sheet",
         "up to 140 letters" in sec and "WORDS_MAX = 140" in src and "at most 2,000 photos a file" in sec and "FILE_MOST = 2000" in src
         and "More than about 300" in sec and "ASK_ABOVE = 300" in src and "48 photos to a sheet" in sec)
    case("from the sheets, never photo by photo (rule 6)", "Read the sheets, never photo by photo (rule 6)" in sec)
    case("what a description may say, and never a person's name unless the photographer said it",
         "**What a description may say.**" in sec and "**Never a person's name unless the photographer said it**" in sec and "never guess who someone is" in sec)
    case("descriptions are for finding photos only, never a fact in a caption, a hook, a note or story words (rule 11)",
         "**Descriptions are for finding photos only (rule 11).**" in sec and "as a fact in a caption, a hook, a note to a client or story words" in sec)
    case("the vault: described in the post kit each photo came from; the total said first", "**\"Describe the photos in my vault\".**" in sec
         and "described in the post kit each one came from" in sec and '`photo_words.py status "My vault"`' in sec and "Say the total first and ask before more than about 300" in sec)
    case("find in my vault: `vault.py find`, a command vault.py has, with --photos and --clips", '`python3 <scripts>/vault.py find "<their words>"`' in sec
         and 'add_parser("find"' in vsrc and '"--photos"' in vsrc and '"--clips"' in vsrc)
    case("the search rule the part tells is the code's: everyday words ignored, every other word must match, tags, descriptions and the shoot's name",
         "Everyday words (me, my, the, with, on...) are ignored and every other word has to match" in sec
         and 'EVERYDAY = frozenset("me my on the a an of with at in and i to".split())' in vsrc and 'frozenset("find every clip clips from any".split())' in vsrc)
    case("the core's table sends the two pasted lines and find in my vault to that section",
         '"Describe my photos for <shoot>" (pasted from a post kit), "Describe the photos in my vault"' in core and '"find ... in my vault"' in core
         and '| `parts/post-kit.md`, "Describing photos so they can be found" |' in core)
    case("where-things-live names the store, the version before, its lock, its fields and its one writer",
         all(x in where for x in ("`.kit/photo-words.json`", "`photo-words.prev.json`", "`photo-words.lock`", "`key`", "`tags`", "`words`", "`words_key`", "`unread`", "`photo_words.py` is its one writer"))
         and all(x in src for x in ('STORE = "photo-words.json"', 'PREV = "photo-words.prev.json"', 'LOCK = "photo-words.lock"', '"words_key"', '"unread"')))
    case("where-things-live says a shoot's photo keeps its words in the shoot's own file, and that the words are never a source for a caption",
         "under the shoot's own number" in where and "never a source for a caption, a note or a hook" in where)
    m = re.search(r'NO_TAGS_PC = \("([^"]+)"\s+"([^"]+)"\)', tc)
    pc_line = (m.group(1) + m.group(2)) if m else ""
    case("the PC line is in this_computer, and the PC part quotes it whole", pc_line == "On a PC, search finds your photos by shoot name and by anything the Assistant has described. To have them described, copy this into the chat:"
         and pc_line in pcp and "## Finding photos by what is in them" in pcp)
    first = "On a PC, search finds your photos by shoot name and by anything the Assistant has described."
    case("the PC gap is on the PC part's list and the PC guide's list, in the same words", ("> - Photo tags for search. " + first) in pcp and ("- **Photo tags for search.** " + first) in guide)


def check_vault_page():
    """My vault on the pages (Nicole's v29, 1.3; stage 7): what the parts say, held to the code."""
    print("\nMy vault: the card, its page and adding a folder (Nov 19)")
    kitp, hello, where, core = read(SM / "parts" / "post-kit.md"), read(SM / "parts" / "hello.md"), read(SM / "parts" / "where-things-live.md"), read(SM / "SKILL.md")
    src, page = read(SM / "scripts" / "vault.py"), read(SM / "scripts" / "vault_page.py")
    case("post-kit.md has a My vault section", "\n## My vault: one post kit for every shoot\n" in kitp)
    sec = kitp.split("## My vault: one post kit for every shoot", 1)[-1].split("\n## ", 1)[0]
    case("it says what the vault is in her words: a post kit like any other, not a place to pick photos first, no photo copied to be in it",
         "a post kit like any other" in sec and "not a place to pick photos first" in sec and "no photo is copied to be in it" in sec)
    case("show my vault: `vault.py ensure`, then shown like any post kit", "`python3 <scripts>/vault.py ensure`" in sec and "Post kit.html" in sec and 'add_parser("ensure")' in src)
    case("nothing is picked until they ask", "**Nothing is picked until they ask**" in sec and "Never pick, order or make anything in the vault because it was opened" in sec)
    for line in ("My favorite maternity photos this year", "Behind the scenes at the beach", "Moms laughing, from any shoot"):
        case(f"her example is in the part and on the page, whole: {line}", line in sec and line in page)
    case("add this folder to my vault: `vault.py add`, a command vault.py has", '`python3 <scripts>/vault.py add "<the folder>"`' in sec and 'add_parser("add"' in src)
    case("it says only finished photos are copied, each checked, and the originals are never moved, renamed or changed",
         "finished photos (JPEG, HEIC, PNG, WebP)" in sec and "every copy checked against its original" in sec and "**the originals are never moved, renamed or changed.**" in sec)
    case("it says twice copies nothing, a cut-off copy is finished by the next, and nothing is written over",
         "the second time copies nothing" in sec and "finished by the next one" in sec and "nothing is written over" in sec and "IMG_0001 (2).jpg" in sec)
    case("the lines it tells the assistant to say are the ones vault.py prints", "Copied 48 finished photos into your vault. Your originals weren't moved." in sec
         and "Copied {n} finished photo{s} into your vault. Your originals weren't moved." in src and "That shoot is already in your vault, from its post kit." in sec
         and '"from_kit": "That shoot is already in your vault, from its post kit."' in src)
    case("the exit codes the part names are the ones vault.py gives (4 not a folder to add, 1 a copy stopped or did not match)",
         "Exit 4 means" in sec and "Exit 1 means" in sec and "return 4" in src and "return 0 if res[\"ok\"] else 1" in src)
    case("+ Add clips: no video is copied, and the line is the page's own", "The Assistant copies no video." in sec
         and "Put your videos in the folder that just opened. They show up in your vault's reel page, where you make clips from them." in sec
         and "Put your videos in the folder that just opened. They show up in your vault's reel page, where you make clips from them." in page)
    case("the core's table sends show my vault, open my vault and add this folder to my vault to that section",
         '| "show my vault", "open my vault", "what\'s my vault?", "add this folder to my vault", "put these photos in my vault" | `parts/post-kit.md`, "My vault" |' in core)
    case("hello.md says My vault is first on the post kits list, with no Archive, and names the screen by its new title",
         "**My vault** first, a dark card on a row of its own" in hello and "it has no Archive and the search never hides it" in hello and "**Turn your shoots into posts**; **Make posts from a shoot** before Nov 19" in hello)
    hb = read(SM / "scripts" / "home_base.py")
    case("... and the screen's title in the code is that one", '"m_h1": "Turn your shoots <em>into posts.</em>"' in hb and "m_eyebrow" not in hb.replace('"m_eyebrow" not', ""))
    case("where-things-live names the add log and what the page follows, as vault.py names them",
         "`.kit/vault-adds.json`" in where and 'ADDS = "vault-adds.json"' in src and "`.kit/vault-add-job.json`" in where and 'ADD_JOB = "vault-add-job.json"' in src)
    for key in ("status", "size", "mtime", "sha256"):
        case(f"where-things-live names the log's `{key}`, and vault.py writes it", f"`{key}`" in where and f'"{key}"' in src)
    case("it says what makes the vault: ensure, add, or the card's press, never a page being opened",
         "or `vault.py add`, or the press of Open the post kit on My vault's card" in where and "never because a page was opened" in where)


def check_vault_reel_clips():
    """The vault's reel page and "Find my clips in my vault" (Nicole's v29, 1.5; stage 9): the instructions, held to the code."""
    print("\nThe vault's reel page: clips from every shoot, and Find my clips in my vault (Nov 19)")
    core, reel, arr, where = read(SM / "SKILL.md"), read(REEL / "SKILL.md"), read(SM / "parts" / "arrange.md"), read(SM / "parts" / "where-things-live.md")
    src, page = read(SM / "scripts" / "vault.py"), read(SM / "scripts" / "reel_page.py")
    case("the reel skill has a Find my clips in my vault section", '\n## Find my clips in my vault: "Find my clips in my vault"\n' in reel)
    sec = reel.split('## Find my clips in my vault: "Find my clips in my vault"', 1)[-1].split("\n## ", 1)[0]
    case("the line it names is the one the page hands out", '"vc_line": "Find my clips in my vault"' in page and '**"Find my clips in my vault"**' in sec)
    case("`vault.py clips` and `vault.py use-clips`, commands vault.py has, with --reel and --clips as the part writes them",
         '`python3 <assistant scripts>/vault.py clips [--reel "<the vault reel\'s name>"]`' in sec and 'add_parser("clips"' in src
         and '`python3 <assistant scripts>/vault.py use-clips [--reel "<name>"] --clips "<shoot\'s folder>:<id>,<shoot\'s folder>:<id>"`' in sec and 'add_parser("use-clips"' in src)
    case("choose by the words, never by watching a video; what they typed is the whole brief; nothing typed, ask", "**Choose by the words, never by watching.**" in sec
         and "never open a video to choose" in sec and "is the whole brief (rule 11)" in sec and "ask what the reel is about, one short question" in sec)
    case("unnamed clips: offer Name my clips for <shoot>, never guess", '"Name my clips for <shoot>"' in sec and "Never guess what an unnamed clip shows." in sec and 'Offer: \\"Name my clips for' in src)
    case("the same add as the page's, checked whole, twice changes nothing, never any other way and never a copied video", "the same add as the page's + Add" in sec
         and "running it twice changes nothing" in sec and "**Never write a clip into the vault's records any other way,**" in sec and "never copy a video into the vault to use it" in sec
         and "reel_page.add_from(" in src)
    case("it says what is different in the vault: the look is of the vault's own videos, a photo is needed, the talking page's videos",
         '**"Look through my footage for My vault" looks only through videos they added to the vault itself**' in sec and "needs at least one photo somewhere in the vault" in sec
         and "the videos it can lay over the talk are the vault's own" in sec and "members=False" in read(SM / "scripts" / "footage.py"))
    case("arrange.md has The vault's reel page", "\n## The vault's reel page\n" in arr)
    sec = arr.split("## The vault's reel page", 1)[-1].split("\n## ", 1)[0]
    case("its words are the page's: the top, Your clips, Added to my vault, From its post kit, + Add and ✓ Added, Your clips for this reel",
         all(x in sec for x in ('"My vault · Reel"', '"Make my reel."', "From your vault: any clips and photos, from any of your shoots.", '**Step 1 is "Your clips".**', "**Added to my vault**",
                                '"From its post kit · 10 clips"', "**+ Add**", "**✓ Added**", "**Your clips for this reel**", '"1 found"'))
         and all(x in page for x in ('"My vault · Reel"', '"title_vault": "Make my reel"', '"vc_added": "Added to my vault"', '"vc_from": "From its post kit · {n} clips"', '"vc_add": "+ Add"',
                                     '"vc_added_tile": "✓ Added"', '"clips_wl": "Your clips for this reel"', '"vc_found": "{n} found"')))
    case("no video is copied, nothing is written into the shoot's post kit, and what is not there yet is said", "No video is copied and nothing is written into the shoot's post kit." in sec
         and "**Not there yet, say so plainly if asked:**" in sec and "does not open while the vault has no photo at all" not in sec
         and "**A vault with video clips and no photo at all** still opens its reel page" in sec and "No photos in the vault yet" in sec)
    case("the core's table sends the pasted line to the reel skill's section and to arrange.md's",
         '| "Find my clips in my vault" (the line on the vault\'s reel page), "find me editing on the computer", "every clip of me at the beach", "make a B-roll from my vault" | '
         'the reel skill\'s "Find my clips in my vault" (`../assistant-make-a-reel/SKILL.md`), and `parts/arrange.md`, "The vault\'s reel page" |' in core)
    case("where-things-live says where the vault's clips live: nothing copied, from {kit, id}, the vault's own .kit/footage, vault_ask",
         "**The vault's clips (Nov 19).**" in where and "`Footage/<shoot's folder>/<file name>`" in where and "`from: {kit: <shoot's folder>, id: <that clip's id>}`" in where
         and "`<vault>/.kit/footage/`" in where and "`vault_ask`" in where and '"vault_ask"' in page and '"from": {"kit": fk, "id": fid}' in page)


def check_vault_reel_photos():
    """The vault's photos step and "Pick my reel photos from my vault" (Nicole's v29, 1.5; stage 10): the instructions, held to the code."""
    print("\nThe vault's reel page: photos folded by shoot, photo search, Pick my reel photos from my vault (Nov 19)")
    core, reel, arr, where = read(SM / "SKILL.md"), read(REEL / "SKILL.md"), read(SM / "parts" / "arrange.md"), read(SM / "parts" / "where-things-live.md")
    src, page = read(SM / "scripts" / "vault.py"), read(SM / "scripts" / "reel_page.py")
    step2 = reel.split("## Step 2: when they ask for your pick", 1)[-1].split("\n## ", 1)[0]
    case("the reel skill's Step 2 has the vault's line, the one the page hands out", '**In My vault the line is "Pick my reel photos from my vault"**' in step2
         and '"photo_for": "Pick my reel photos from my vault"' in page and '"photo_plain": "Pick my reel photos from my vault"' in page)
    case("the note first, with the command as it is", '`python3 <assistant scripts>/reel_page.py note "My vault" [--reel "<the reel\'s name>"]`' in step2 and "This is the vault:" in page)
    case("narrow before looking: vault.py find with the note's own words, then sheets of the shortlist only, commands vault.py has",
         '`python3 <assistant scripts>/vault.py find "<the note\'s own words>" --photos`' in step2 and '`python3 <assistant scripts>/vault.py relist --sheets --only "<the numbers find printed>"`' in step2
         and '"--only"' in src and "def shortlist_sheets(" in src and "never search for something the note did not say" in step2 and "it is a shortlist, not the answer" in step2)
    case("48 to a sheet is the reel script's own number", "48 to a sheet" in step2 and "PER_SHEET = 48" in read(REEL / "scripts" / "reel.py"))
    case("with no note: say how many photos first, then the whole vault's sheets", "**With no note, the whole vault:** say how many photos you are about to look through first" in step2
         and "`python3 <assistant scripts>/vault.py relist --sheets` draws every photo" in step2)
    case("saved with kit.py picks under the vault's numbers, for that reel; the note decides what may go in",
         '`python3 <assistant scripts>/kit.py picks "My vault" --reel <vault numbers, in play order, marked> [--for-reel "<reel\'s name>"]`' in step2
         and "**The note decides what may go in**" in step2 and "never widen it" in step2)
    case("the strip in the vault names the vault as --kit and its own Photos folder", '`reel.py strip --kit "<the vault\'s folder>" --folder "<the vault\'s own Photos folder>" --picks ...`' in step2)
    sec = arr.split("## The vault's reel page", 1)[-1].split("\n## ", 1)[0]
    case("arrange.md's words for the photos step are the page's: the grid's heading, Added to my vault, + Add photos, From its post kit, found, her progress line",
         all(x in sec for x in ('**"Choose your photos" in the vault**', "**All your photos, from every shoot in your vault**", "**Added to my vault** open on top", "**+ Add photos**",
                                '"From its post kit · 72 photos"', '"3 found"', '"Getting your photos ready to search: 40 of 72."'))
         and all(x in page for x in ('"all_summary": "All your photos, from every shoot in your vault"', '"vp_added": "Added to my vault"', '"vp_add_photos": "+ Add photos"',
                                     '"vp_from": "From its post kit · {n} photos"'))
         and '"getting": "Getting your photos ready to search: {done} of {total}."' in read(SM / "scripts" / "photo_words.py"))
    case("it says search finds what is in a photo, and what to say while a shoot is still being looked at", "**The search finds what is in a photo**" in sec
         and "tell them to give it a moment rather than that nothing matches" in sec and '"Describe the photos in my vault"' in sec)
    case("it points the pasted line at the reel skill's Step 2 with the same commands", '**The line to copy there is "Pick my reel photos from my vault"**' in sec
         and '`vault.py find "<the note\'s own words>" --photos`' in sec and '`vault.py relist --sheets --only "<those numbers>"`' in sec and "The note decides what may go in." in sec)
    case("the stage 9 line that the photos step is the plain one is gone", "the photos step in the vault is still the plain one" not in arr)
    case("the core's table has a row for the pasted line (the description is not touched)",
         '| "Pick my reel photos from my vault" (the line on the vault\'s reel page; the reel\'s name and ", and follow my note" may follow), "pick photos from my vault for a reel", "moms laughing, from any shoot" | '
         'the reel skill\'s Step 2, "In My vault the line is..." (`../assistant-make-a-reel/SKILL.md`), and `parts/arrange.md`, "The vault\'s reel page" |' in core)
    case("where-things-live says where the shortlist's sheets go", "**The vault's sheets (Nov 19).**" in where and "`.kit/reels/shortlist/`" in where and 'wd / "shortlist"' in src)
    case("our search placeholder is in OUR words, a draft, and her mock-up's is nowhere", '"vp_search_ph": "laughing, a kiss, green backdrop, Hannah"' in page and "Search by shoot: maternity" not in page.split("VAULT_PICK_OUR_WORDS = {", 1)[1].split("}", 1)[0])


def check_create_tiles():
    """The home page's four tiles ask which shoot (Nicole's v30, section 4; stage C): what the parts say, held to the code."""
    print("\nThe four tiles: Create a reel, which shoot? (Nov 21)")
    hello, photos, where = read(SM / "parts" / "hello.md"), read(SM / "parts" / "photos-in.md"), read(SM / "parts" / "where-things-live.md")
    home, ns, cd = read(SCRIPTS / "home.py"), read(SCRIPTS / "new_shoot.py"), read(SCRIPTS / "create_dialog.py")
    for line in ("Which shoot do you want to make it from?", "Pick the folder with your finished photos", "Mix photos and clips from all your shoots",
                 "Start with a shoot: pick the folder with your finished photos.", "Search your shoots"):
        case(f"hello.md says her line, and the home page has it: {line}", line in hello and line in home)
    case("hello.md says where each tile lands", all(t in hello for t in ("Reels to the reel page", "Carousels to the carousel designer",
                                                                         "Stories to the stories designer", "Captions to the words page")))
    case("hello.md and photos-in.md say + A new shoot copies, never moves, and lands on the page they tapped",
         "copied and checked, never moved" in hello and "not on the post kit" in hello and "the folder they picked is only read" in photos)
    case("photos-in.md's by-hand line is a command new_shoot.py has", '`python3 <scripts>/new_shoot.py make "<folder>"`' in photos and 'add_parser("make"' in ns)
    case("hello.md's status line is a command new_shoot.py has", "`python3 <scripts>/new_shoot.py status`" in hello and 'add_parser("status"' in ns)
    case("where-things-live names the log and the job record new_shoot.py writes", ".studio/new-shoots.json" in where and "new-shoot-job.json" in where
         and 'LOG_NAME = "new-shoots.json"' in ns and '"new-shoot-job.json"' in ns)
    case("the routes the page asks are create_dialog.py's", all(r in cd for r in ('"/make-list"', '"/make-new-status"', '"/make-new"', '"/make-vault"')))



def check_v30_finish():
    """Stage F of v30 (Nov 22): the core sends + A new shoot to its part, a PC hears about the tiles, the parts count
    the home page's files right, and nothing tells them to click a Make posts from a shoot button the home page no
    longer has."""
    print("\nv30's loose ends: + A new shoot in the core, on a PC, and the come-back line (Nov 22)")
    skill, photos, pc = read(SM / "SKILL.md"), read(SM / "parts" / "photos-in.md"), read(SM / "parts" / "on-a-pc.md")
    where, hello = read(SM / "parts" / "where-things-live.md"), read(SM / "parts" / "hello.md")
    rows = [ln for ln in skill.splitlines() if ln.startswith("|") and "+ A new shoot" in ln]
    case("the core's table has a row for + A new shoot, sending it to photos-in.md's own section",
         len(rows) == 1 and "`parts/photos-in.md`, \"+ A new shoot, from the home page's tiles\"" in rows[0]
         and "**+ A new shoot, from the home page's tiles" in photos, rows)
    case("photos-in.md says new_shoot.py status answers what happened", "`python3 <scripts>/new_shoot.py status`" in photos)
    case("on-a-pc.md says how the tiles and + A new shoot work on a PC, and the chat's way when the window can't open",
         "+ A new shoot" in pc and "no face finder" in pc and '`python3 <scripts>/new_shoot.py make "<folder>"`' in pc)
    case("where-things-live counts three small files of the home page's own (the hello's is the third)",
         "keeps three small files of its own" in where and "two small files" not in where and "home-hello.json" in where)
    case("hello.md no longer says the three cards sit side by side", "three light cards side by side" not in hello and "stacked on the right" in hello)
    told = {n: read(SM / "parts" / n) for n in ("backup.md", "after-the-report.md")}
    told["the reel skill"] = read(SKILLS / "assistant-make-a-reel" / "SKILL.md")
    told["first_look.py"] = read(SCRIPTS / "first_look.py")
    stale = [n for n, x in told.items() if "click Make posts from a shoot" in x]
    case("nothing tells them to click Make posts from a shoot (the home page has no such button since v30)", not stale, stale)


def check_chat_no_reminders():
    """Nicole, Nov 22: "i dont think the chat needs the reminders. either." The chat never leads with what is due or
    late, in any conversation or hello: the first-thing checks no longer run the two reminders commands or say
    "Heads up: ...", and the chat's hello stages say no due or late items. The page check-offs, updates and
    home.py pending stay; asked "what's due?", the chat answers; calendar reminders and a phone tap they asked for
    are untouched. (Before this, SKILL.md opened every conversation with those lines on purpose.)"""
    print("\nThe chat never opens with reminders (Nicole, Nov 22)")
    skill = read(SM / "SKILL.md")
    first = skill.split("## First thing, every time", 1)[-1].split("## Read the part before you act", 1)[0]
    case("the first-thing checks no longer run edit_queue.py reminders or posting_queue.py reminders",
         "## First thing, every time" in skill and not re.search(r"`python3 <scripts>/(?:edit|posting)_queue\.py reminders", first), first[:300])
    case("...and say the chat never opens with reminders, naming where they live and that a question is answered",
         "**The chat never opens with reminders" in first and "Don't run `edit_queue.py reminders` or `posting_queue.py reminders`" in first
         and "My editing queue and My posting queue cards" in first and "answer as before" in first)
    case("...while the page check-offs, the update check, home.py pending and Pick again still run first",
         "`python3 <scripts>/edit_queue.py offers --mark`" in first and "updates.py check" in first
         and "home.py pending" in first and "peek_sheets.py asks" in first)
    case("...and calendar reminders and a phone tap they asked for are kept", "Posting-day reminders on their calendar" in first and "phone tap" in first)
    stale = [rel(f) for f in instruction_files() if "Heads up: the Garcia" in read(f) or "Anything they print goes first" in read(f)]
    case("no instruction still opens a conversation with \"Heads up: ...\" lines", not stale, stale)
    named = []
    for f in instruction_files():
        for ln in read(f).splitlines():
            if re.search(r"(?:edit|posting)_queue\.py reminders", ln) and "Don't run" not in ln and "scheduled task" not in ln:
                named.append((rel(f), ln[:120]))
    case("the reminders commands are named only for a phone tap they asked for (a scheduled task), never to say in the chat", not named, named)
    hello = read(SM / "parts" / "hello.md")
    stages = {k: next((ln for ln in hello.splitlines() if ln.lstrip().startswith(f'- **"{k}"')), "") for k in ("getting-started", "regular")}
    case("the chat's hello: getting-started and regular no longer say what is due or late",
         all(stages.values()) and not any(re.search(r"due or late[,)]|anything due or late", v) for v in stages.values()), stages)
    case("...and every stage is told never to open with what is due or late", "never open with what is due or late (Nicole, Nov 22)" in hello)
    pq, pc, after = read(SM / "parts" / "posting-queue.md"), read(SM / "parts" / "on-a-pc.md"), read(SM / "parts" / "after-the-report.md")
    case("posting-queue.md no longer says the start-of-conversation lines are said in the chat",
         "Those are said in the chat" not in pq and "The chat never opens with what is due to post" in pq)
    case("on-a-pc.md's first conversation no longer lists the reminders as a first-thing check", "(the reminders, `home.py pending`)" not in pc)
    case("after-the-report.md no longer promises the heads-up whenever they open the Assistant",
         "will show whenever they open the Assistant" not in after and "My editing queue card" in after)
    # The final check of v31-prep (Nov 22): home.py's hello words are what `home.py hello` hands Claude, so they say the same.
    hw = read(SM / "scripts" / "home.py").split("HELLO_WORDS = {", 1)[-1].split("}", 1)[0]
    case("home.py's hello words for getting-started and regular no longer ask for the day's rundown, and say never what is due",
         "The day in" not in hw and hw.count("never what is due") + hw.count("Never what is due") == 2, hw)
    case("the core no longer counts a tile press among presses that may only be someone looking (tiles never reach pending)",
         "See all my post kits or a tile may only be" not in skill and "a press on See all my post kits may only be someone looking" in skill
         and "Back up a card or See all my post kits may only be someone looking" not in skill)
    case("posting-queue.md says the grid shows up to 12 posts in four rows (not 12 to 15, not five rows)",
         "12 to 15 posts" not in pq and "up to five rows" not in pq and "up to 12 posts show at once, four rows" in pq
         and "up to four rows (12 posts)" in pq)
    q = read(SM / "parts" / "editing-queue.md")
    case("asked, the chat still answers: \"what's due\" is in the core's table and opens the queue in editing-queue.md",
         any("\"what's due\"" in r and "parts/editing-queue.md" in r for r in table_rows(skill)) and "\"what's due?\"" in q)


def check_reel_words():
    """Nicole, Nov 23: "each reel gets its own caption". The instructions say so wherever a reel's words are
    written, read or queued, name the command's --reel and carry-reel as words.py has them, never tell the chat
    to guess a reel, and no longer say a shoot's reels share one caption."""
    print("\nEach reel has its own words (Nicole, Nov 23)")
    skill = read(SM / "SKILL.md")
    part, post, kitp, where = (read(SM / "parts" / n) for n in ("words.md", "posting-queue.md", "post-kit.md", "where-things-live.md"))
    w, wp = read(SM / "scripts" / "words.py"), read(SM / "scripts" / "words_page.py")
    case("words.md has the section, in her words", '## Each reel has its own words (Nicole, Nov 23: "each reel gets its own caption")' in part
         and "**Every reel has its own answers, its own caption, its own ten hooks and its own picked hook.**" in part)
    case("...the lines the page hands out name the reel after a comma, as the page writes them",
         '"Ask me about the Beach reel, White Backdrop"' in part and '"talk_line_reel": "Ask me about the {short} reel, {reel}"' in wp
         and '"write_line_reel": "Write my words for the {short} reel, {reel}"' in wp)
    case("...every reel command takes --reel, and words.py has it on each of them",
         'add `--reel "<reel name>"` to `ask`, `answer`, `show`, `draft`' in part and w.count('add_argument("--reel"') >= 3)
    case("...never guess which reel: the command stops and lists the names, and the chat asks",
         "**Never guess which reel.**" in part and "the command stops, saves nothing, and lists the reels by name" in part
         and "each reel has its own words. Say which one with --reel" in w and '"this shoot has 2 reels, and each reel has its own words"' in part)
    case("...a shoot with one reel needs none of it", "**A shoot with one reel needs none of this.**" in part)
    case("...carry-reel is named as words.py has it, answers only, never over a reel's own",
         '`words.py carry-reel "<kit>" --from "Reel 1" --reel "<this reel>"`' in part and 'sub.add_parser("carry-reel")' in w
         and "The caption and the hooks are never copied" in part and "It never writes over answers a reel already has." in part)
    case("...the page's own button for it is named as the page writes it", '"Use my answers from Reel 1"' in part and '"from_yes": "Use my answers from {from}"' in wp)
    case("...no command copies a caption between reels, and the chat says so", "there is no command that copies a caption from one reel to another" in part)
    case("...reels made before this: the one caption is the first reel's, the others have none", "that caption and those hooks are the shoot's first reel's now" in part)
    case("...the commands block has carry-reel and says --reel is needed with several reels",
         'words.py carry-reel "<kit>" --from "<a reel\'s name>" --reel "<another reel\'s name>"' in part
         and '`words.py draft "<kit>" reel --reel "White Backdrop" --file <d.json>`' in part)
    case("...and the traps name both mistakes", "Writing one reel's words without `--reel` when the shoot has several" in part
         and "Giving two reels of one shoot the same caption." in part)
    case("posting-queue.md: the caption question, the panel, the reminder and Open my words are that reel's own",
         "when THAT reel has no caption" in post and "shows that reel's own caption and its own picked hook" in post
         and "never borrows another reel's" in post and "a reel's post reads that reel's own words" in post
         and '`--reel "<reel name>"`, since each reel has its own caption' in post)
    case("...and it names the kit page's list of reels in Your words as the page writes it",
         all(('"' + x + '"') in read(SM / "scripts" / "kit.py") for x in ("caption ready", "told, not written yet", "not written yet"))
         and '"caption ready · 10 hooks, 2 picked", "told, not written yet", "not written yet"' in post)
    case("post-kit.md points a shoot with several reels at each reel's own words", "**A shoot with several reels: each reel has its own caption and hooks**" in kitp)
    case("where-things-live.md says where a later reel's words are kept, as words.py keeps them",
         "`pieces.reels.<the reel's id>`" in where and 'LATER = "reels"' in w and "a shoot with one reel has no such part" in where)
    case("the core's table sends a line with a reel's name after a comma to words.md",
         any("with a reel's name after a comma" in r and "parts/words.md" in r for r in table_rows(skill)))
    stale = [rel(f) for f in instruction_files() if re.search(r"one caption (and one set of hooks )?for (all of )?(the|a) shoot's reels|words page has one Reel tab", read(f))]
    case("no instruction still says a shoot's reels share one caption", not stale, stale)
def check_nov23_engine():
    """Nicole's Nov 23 answers, the backup's engine: the six photos are a first look (no keyword, no client note),
    and a backup started from the home page can be read and carried on from the chat."""
    print("\nNov 23: a first look, no client note, and a backup started from the home page")
    part = lambda n: read(SM / "parts" / n)   # noqa: E731
    skill, b, s, c, a, w = read(SM / "SKILL.md"), part("backup.md"), part("sneak-peeks.md"), part("client-note.md"), part("after-the-report.md"), part("where-things-live.md")
    case("sneak-peeks.md is the first look now: the page's line, six per shoot, the close look and the checked lines kept",
         "A first look at your shoot." in s and "six per shoot, always" in s and "peek_sheets.py closer" in s and "--checked" in s
         and "peek_sheets.py taste" in s)
    case("... and it never says the six are for a client, are sneak peeks to send, or are marked in Lightroom",
         "send your client" not in s and "marks each pick in Lightroom" not in s and "to send the client" not in s
         and "Never say a photo is marked, tagged or findable in Lightroom" in s)
    case("... an older backup's 'sneak peek' sidecars are left where they are, and it says what to answer",
         "They are left exactly where they are" in s and "New backups don't." in s)
    case("... a backup started from the home page picks its own six, with nobody looking",
         "A backup started from the home page picks its own six" in s and "night.py --by-time" in s)
    case("backup.md: step 8b is the first look, step 8c says no note is written or offered",
         "8b. **The first look (exit code 7).**" in b and "8c. **No note to the client (Nicole and Dustin, Nov 23).**" in b
         and "the sneak peeks are in it" not in b and "the notes (8c)" not in b)
    case("no instruction still tells the Assistant to save a client note onto the report",
         not [n for n in ("backup.md", "after-the-report.md", "first-backup-setup.md", "client-note.md", "hello.md", "sneak-peeks.md")
              if "client_note.py save" in part(n) or "client_note.py setup" in part(n) or "client_note.py facts" in part(n)])
    case("what they say about a card is still kept (client_note.py told), in backup.md and in the retired part",
         "client_note.py told --night" in b and "client_note.py told --night" in c)
    rows = [ln for ln in skill.splitlines() if ln.startswith("|") and "A backup started from the home page" in ln]
    case("the core's table sends 'is my backup done?' and 'A backup is already running.' to backup.md's own section",
         len(rows) == 1 and "is my backup done?" in rows[0] and "A backup is already running." in rows[0]
         and "## A backup started from the home page (Nov 23)" in b, rows)
    case("the core's first-thing check and table call the six first-look photos, never sneak peeks",
         "six first-look photos" in skill and "sneak peek" not in skill.lower())
    sec = b[b.find("## A backup started from the home page"):b.find('## "What are my settings?"')]
    case("backup.md: how a page-started backup went is read with backup_job.py status --words, and never a path read out",
         "backup_job.py status --words" in sec and "Never read a path from it out loud" in sec and "serve_report.py" in sec)
    case("... split by time at four quiet hours, placeholder names, the six chosen by a script",
         "quiet for four hours" in sec and "\"Shoot 1\", \"Shoot 2\"" in sec and "chosen by a script" in sec and "past midnight stays one shoot" in sec)
    case("... a problem is carried on with Try again or backup_job.py start, under the same name",
         "**Try again**" in sec and "backup_job.py start --source" in sec and "picks up under the same name" in sec)
    case("... one backup at a time, and eject's own line while a backup runs from the card",
         "A backup is already running." in sec and "start nothing" in sec and "A backup is still running from this card. It won't be long." in sec)
    case("... a folder instead: a HEIC by the file's own time, an undated file kept and said, never hidden",
         "by the file's own time" in sec and "kept with the backup's records" in sec)
    sys.path.insert(0, str(SM / "scripts"))
    try:
        import backup_lock
        import backup_job
        case("the lines the instructions quote are the ones the scripts say",
             backup_lock.BUSY in sec and backup_lock.BUSY_CARD in sec and backup_job.OUR_WORDS["busy"] == backup_lock.BUSY)
    except Exception as e:  # noqa: BLE001
        case("the lines the instructions quote are the ones the scripts say", False, repr(e))
    case("where-things-live.md names the job's record, the two locks, the log, and the by-time marks in a backup's records",
         all(x in w for x in ("backup-job.json", "backup-job.lock", "backup.lock", "backup.running.json", "logs/backup-job.log",
                              "\"placeholder\": true", "the backup, by time", "the file's own time")))
    case("after-the-report.md offers no note and names the first look",
         "Never offer one" in a and "A first look at your shoot." in a)
def check_backup_box_nov23():
    """Back up a card is a box on the home page that starts the backup itself (Nicole's v31; built Nov 23)."""
    hello, backup, skill, where = (re.sub(r"\s+", " ", read(SM / "parts" / n)) for n in ("hello.md", "backup.md", "../SKILL.md", "where-things-live.md"))
    sys.path.insert(0, str(SM / "scripts"))
    import backup_popup as bp
    case("hello.md: Back up a card opens a box on the home page; See all my backups opens Your backups, only the list, See the report first",
         "**Back up a card opens a box on the home page itself" in hello and "opens **Your backups**, which is only the list" in hello
         and "each shoot with **See the report** first" in hello and 'has the two steps (card in, paste "backup now")' not in hello)
    case("hello.md says the box's words as the page has them", bp.W("safe") in hello and bp.W("safety") in hello and bp.W("only_once").split(" After")[0] in hello
         and "Copying and checking (128 of 181)" in hello and bp.W("sorting") in hello and bp.OUR_WORDS["second_step"] in hello and bp.W("done_head") in hello
         and bp.W("no_wait") in hello and bp.W("second_add") in hello and bp.W("who_label") in hello)
    case("hello.md: a press on Back up a card never reaches the chat; nothing promises a notification",
         "`home.py pending` leaves it out, as it leaves out a tile" in hello and "never promise a tap or a notification for a backup started there" in hello)
    case("hello.md: asked how a backup works, the answer is the box, and the one thing it asks the first time",
         "The first time it asks one thing, where your backups should go" in hello and "I see we haven't backed up a card together yet" not in hello)
    case("backup.md: two ways to start; backup now in the chat still works; a running backup from the page is never doubled",
         "## Two ways to start a backup (since Nov 23)" in read(SM / "parts" / "backup.md") and '**"backup now" in the chat still works**' in backup
         and "never start another backup" in backup and "`python3 <scripts>/backup_job.py status`" in backup
         and "Never promise a notification or a phone tap for a backup started from the page" in backup
         and "asked every time and never remembered" in backup and "never at the same moment" in backup)
    case("the core: a press on Back up a card never shows in pending, and \"how's my backup going?\" goes to backup.md",
         "a press on Back up a card never shows here" in skill and "\"how's my backup going?\"" in skill)
    case("where-things-live.md names what the box keeps: the exact folder, never the second drive, and its one small note",
         "exactly the folder picked in the box" in where and "the second drive picked there is never saved" in where and "`~/.studio/backup-popup-start.json`" in where)
    case("hello.md no longer speaks of a Back up a card screen: the list is the Your backups screen",
         "Back up a card screen" not in hello and "**What the Your backups screen says about a backup" in hello)


def main():
    for fn in (check_reel_words, check_search, check_table, check_descriptions, check_curating, check_reel_skill, check_doors, check_words, check_posting, check_whole_build, check_talking,
               check_stories_v26, check_carousel_v27, check_several_reels, check_photographer_picks, check_trim_and_select, check_songs_v25, check_queue_v25, check_trash_helper,
               check_watch_direct_broll, check_instructions_v27_lane_a, check_posted_and_path_v27, check_backup_zero, check_second_copy, check_backup_options, check_vault_core, check_vault_page, check_vault_search, check_vault_reel_clips, check_vault_reel_photos, check_vault_everything, check_create_tiles, check_v30_finish, check_chat_no_reminders, check_nov23_engine, check_backup_box_nov23):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            case(f"{fn.__name__} ran to its end", False, f"{type(e).__name__}: {e}")
    failed = _results.count(False)
    print(f"\n{len(_results) - failed} of {len(_results)} passed." + (f" {failed} FAILED." if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
