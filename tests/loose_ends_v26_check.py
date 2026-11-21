#!/usr/bin/env python3
"""The smaller changes and loose ends of Nicole's v25 and v26 (stage L of the build).

    python3 tests/loose_ends_v26_check.py [--work <a folder to keep the run in>]

No browser, no server, no add-on: it runs on Apple's own Python and on a PC. What it checks:

  * no line a page shows tells them to talk to "Claude": every page says "your assistant" (Nicole, Nov 13:
    "Everywhere on the page says 'your assistant', never 'Claude'"); the name of the app ("the Claude app") is
    not what this is about
  * the Make posts screen lists every shoot in Your Content that has a kit record, also one whose page was
    never written (her v25, section 10: her newest shoot did not show until its page was made); a folder
    made by hand with no kit record is not listed, and one odd record does not hide the others
  * the instructions: the parts no longer describe the old home page, the old reel line or one stories design
    a shoot; a caption is optional before the queue, said where the words are written too; the slash commands
    send the hello through parts/hello.md; where-things-live names every record v25 and v26 added
  * "when the photos are much alike, keep the opener and the holds short" is in the choosing rules and the
    reel skill (instructions only, as her engine has no change for it)
  * both setup guides: the lines the new home base made untrue are gone, and the new screens are named
  * the reel page's own style narrows a wide video's player in a narrow window (her rule kept whole above it;
    the real page is measured in tests/reel_footage_check.py)

Nothing under ~/.studio is touched: STUDIO_HOME is a scratch folder, and the pretend Assistant folder is inside it.
"""
import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "the-engine"
SCRIPTS = PLUGIN / "skills" / "studio-manager" / "scripts"
REEL_SCRIPTS = PLUGIN / "skills" / "assistant-make-a-reel" / "scripts"
PARTS = PLUGIN / "skills" / "studio-manager" / "parts"

RESULTS = []


def case(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(("  ok    " if ok else "  FAIL  ") + name + ("" if ok else "\n          " + str(detail)[:600]), flush=True)


def group(name):
    print("\n" + name, flush=True)


def read(p):
    return Path(p).read_text(encoding="utf-8")


def flat(p):
    return re.sub(r"\s+", " ", read(p))


TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=")


# ---------------------------------------------------------------- "your assistant", never "Claude"

# What a line that sends them to "Claude" looks like. The app's own name is fine ("the Claude app", "the Claude
# window"): that is what the app is called on their screen.
TO_CLAUDE = re.compile(r"\b(?:Tell|tell|Ask|ask) Claude\b|\bto Claude\b|\bClaude(?:,)? and it'll\b|\bClaude will\b")
# The one line of talking_page.py that explains, in a reason nobody is shown, why its own line differs from the
# pickers' older one.
EXPLAINS = ("the pickers' own line said",)


def check_assistant():
    group("No page tells them to talk to Claude")
    hits = []
    for folder in (SCRIPTS, REEL_SCRIPTS):
        for f in sorted(folder.glob("*.py")):
            for n, line in enumerate(read(f).splitlines(), 1):
                line = re.split(r"\s{2,}#\s", line)[0]         # a note to ourselves at the end of a line is not a page's line
                if TO_CLAUDE.search(line) and not any(x in line for x in EXPLAINS):
                    hits.append("%s:%d %s" % (f.name, n, line.strip()[:110]))
    case("no script holds a line that says Tell Claude, Ask Claude or \"to Claude\"", not hits, hits[:6])
    sys.path.insert(0, str(SCRIPTS))
    import arrange
    import kit
    import reminders
    said = {"the pickers' not-ready page": arrange.NOT_READY, "the pickers' can't-reach line": arrange.CANT_REACH,
            "slides not finished": arrange.NOT_FINISHED, "a name in the way": arrange.IN_THE_WAY,
            "the kit page's can't-reach line": kit.OUR_KIT_WORDS["unreached"], "the kit's saved copy": kit.OUR_KIT_WORDS["saved_copy"],
            "the kit that can't be built": kit.OUR_KIT_WORDS["cant_build"], "a reminder stopped here": reminders.STOPPED_HERE}
    for what, line in said.items():
        case("%s says \"your assistant\"" % what, "your assistant" in line and "Claude" not in line, line)
    for name in ("arrange_page.py", "design_js_core.py", "design_js_save.py", "posting_queue.py"):
        t = read(SCRIPTS / name)
        case("%s: its lines for a page say \"your assistant\"" % name, "your assistant" in t and not TO_CLAUDE.search(t))
    parts = []
    for f in sorted(PARTS.glob("*.md")):
        for m in re.finditer(r"[^.]*\b(?:[Tt]ell|[Aa]sk) Claude\b[^.]*|[^.(]*\bto Claude;[^.]*", read(f)):
            parts.append("%s: %s" % (f.name, m.group(0).strip()[:120]))
    case("no part quotes a page as saying to tell Claude", not parts, parts[:4])


# ---------------------------------------------------------------- every shoot in Your Content is listed

def py(env, code):
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(SCRIPTS))
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def check_listed(work):
    group("Every shoot in Your Content shows on the Make posts screen (v25, section 10)")
    studio = work / "studio"
    spot = work / "drive"
    studio.mkdir(parents=True)
    spot.mkdir(parents=True)
    env = dict(os.environ, STUDIO_HOME=str(studio), HOME=str(work / "home"), USERPROFILE=str(work / "home"),
               STUDIO_NO_WINDOWS_FOR_TESTS="1", STUDIO_CARD_FOR_TESTS="none", PYTHONIOENCODING="utf-8")
    (work / "home").mkdir()
    r = subprocess.run([sys.executable, str(SCRIPTS / "posts.py"), "setup", "--where", str(spot)], capture_output=True, text=True,
                       encoding="utf-8", env=env)
    code, out, err = py(env, "import posts, json; print(json.dumps(str(posts.home())))")
    home = Path(json.loads(out)) if code == 0 and out else None
    case("a pretend Assistant folder, in a scratch place", r.returncode == 0 and home is not None and str(work) in str(home), (r.returncode, r.stdout[-200:], r.stderr[-200:], out, err[-200:]))
    if home is None:
        return
    content = home / "Your Content"

    def kit(folder, record=None, page=False, photos=2):
        d = content / folder
        (d / "Photos").mkdir(parents=True)
        for i in range(photos):
            (d / "Photos" / ("p%02d.jpg" % (i + 1))).write_bytes(TINY_JPEG)
        if record is not None:
            (d / ".kit").mkdir()
            (d / ".kit" / "kit.json").write_text(record if isinstance(record, str) else json.dumps(record), encoding="utf-8")
        if page:
            (d / ".kit" / "Post kit.html").write_text("<html>an older page</html>", encoding="utf-8")
        return d

    kit("2026-11-01 With a page", {"name": "With a page", "date": "2026-11-01"}, page=True)
    kit("2026-11-12 Newest, no page yet", {"name": "Newest, no page yet", "date": "2026-11-12"})
    kit("2026-10-03 An odd record", "[1, 2, 3]")
    kit("Made by hand", None)
    code, out, err = py(env, "import home_base, json; print(json.dumps(home_base.kits()))")
    kits = json.loads(out) if code == 0 and out else []
    names = [k.get("folder") for k in kits]
    case("a shoot whose page was never written is listed, newest first, with its photos counted",
         names[:1] == ["2026-11-12 Newest, no page yet"] and kits[0].get("photos") == 2 and kits[0].get("name") == "Newest, no page yet", (code, names, err[-300:]))
    case("...beside the one that has a page", "2026-11-01 With a page" in names, names)
    case("a record that is not a record hides nothing: its shoot is listed under its folder's name, and so are the others",
         "2026-10-03 An odd record" in names and len(names) == 3, names)
    case("a folder made by hand, with no kit record, is not listed (there is no page it could open)", "Made by hand" not in names, names)
    case("nothing listed is a path", not any("/" in json.dumps(k) or "\\\\" in json.dumps(k) for k in kits), kits[:1])
    made = [f for f in content.rglob("Post kit.html")]
    case("listing writes no page: the one page there is the one that was there", [p.parent.parent.name for p in made] == ["2026-11-01 With a page"], made)
    code, out, err = py(env, "import home, json; g = home.gather(); print(json.dumps([k['folder'] for k in g.get('kits', [])]))")
    seen = json.loads(out) if code == 0 and out else None
    case("what the hello reads (home.gather) counts the shoot with no page as a kit too",
         seen is not None and "2026-11-12 Newest, no page yet" in seen and "Made by hand" not in seen, (code, seen, err[-300:]))


# ---------------------------------------------------------------- the instructions

def check_parts():
    group("The instructions no longer describe what v25 and v26 replaced")
    texts = {f.name: flat(f) for f in sorted(PARTS.glob("*.md"))}
    texts["SKILL.md"] = flat(PARTS.parent / "SKILL.md")
    texts["reel SKILL.md"] = flat(PLUGIN / "skills" / "assistant-make-a-reel" / "SKILL.md")
    for f in sorted((PLUGIN / "commands").glob("*.md")):
        texts["commands/" + f.name] = flat(f)
    everything = "\n".join(texts.values())
    gone = {
        "the home page's recent-shoots list": r"[Yy]our recent shoots",
        "the home page's five buttons": r"\bfive buttons\b",
        "the badges on the old home page's buttons": r"New to you|Done 3 times",
        "the old reel line at the end of a backup": r"turn your favorites into a reel",
        "one stories design a shoot, as a rule that stands": r"one stories design (?:per|a) shoot(?! rule)",
        "a caption needed before the queue on the post kit": r"Add to my queue (?:unlocks|stays locked) (?:when|until) [^.]*caption",
    }
    for what, pat in gone.items():
        where = [n for n, t in texts.items() if re.search(pat, t)]
        case("no instruction still describes %s" % what, not where, where)
    q = texts["editing-queue.md"]
    case("the editing queue's part names its sections in the page's own words, and says never \"finished\" or \"your shoots\"",
         all(w in q for w in ("**Uploaded shoots**", "**Delivered (n)**", "**Archived (n)**", "Mark as delivered", "never \"finished\" or \"your shoots\"")))
    h = texts["hello.md"]
    # (posts first since her v29, Nov 19: the cards are no longer numbered, and the post kits are not listed)
    case("the hello part describes the home base: the four cards, posts first and not numbered, and the two screens",
         "**1 Back up a card**" not in h and "Your workflow" not in h.replace('says "Your workflow"', "") and
         all(w in h for w in ("home base", "**Back up a card**", "**My editing queue**", "**Turn your shoots into posts**", "**Make posts from a shoot**", "**My posting queue**",
                              "**Also in your Assistant**", "**Create your post kits**", "**See all my post kits**", "never listed on the home page",
                              "Your backups", "Your post kits", "/backups", "/make-posts")))
    a = texts["arrange.md"]
    case("the stories part speaks of sets of stories", "set of stories" in a or "sets of stories" in a)
    case("\"make my posts\" only brings the photos in and opens the post kit, in both parts that start a kit",
         "only brings the photos in and opens the post kit" in texts["photos-in.md"] and "only brings the photos in and opens the post kit" in texts["post-kit.md"])
    w = texts["words.md"]
    case("where the words are written, it also says a caption is optional before the queue (ask, don't block)",
         "A caption is optional" in w and "Add to my queue works once the piece is made, caption or not" in w and "never tell them a reel or a carousel can't go in their posting queue" in w)
    case("...and the two other parts that speak of the queue say the same",
         "caption or not" in texts["post-kit.md"] and "caption or not" in texts["posting-queue.md"])
    bodies = [read(f).split("---")[-1].strip() for f in sorted((PLUGIN / "commands").glob("*.md"))]
    case("both slash commands send the hello through parts/hello.md and home.py hello --mark, in the same words",
         len(bodies) == 2 and bodies[0] == bodies[1] and "parts/hello.md" in bodies[0] and "home.py hello --mark" in bodies[0]
         and "Never list what is empty" in bodies[0] and "home base" in bodies[0], bodies[:1])
    case("...and neither tells every hello to be a rundown of the day", "then answer in two or three lines" not in everything)

    group("Where things live names every record v25 and v26 added")
    live = texts["where-things-live.md"]
    records = {
        "the kit archive and the list before it": ("`~/.studio/kit-archive.json`", "`kit-archive.prev.json`"),
        "the small pictures of the Make posts screen": ("`~/.studio/home-thumbs/`",),
        "a shoot's several reels": ("`versions`", "`current`", "`moments_found`"),
        "the note for a reel's photos": ("`photo_ask`",),
        "the note for a set of stories, and who filled it": ("`ask`", "`asked`", "`filled_by`"),
        "a delivered and an archived shoot in the editing queue": ("`finished_at`", "`stored`", "`stored_at`"),
        "which recording a sound came from": ("`reel-sounds.json`", "`reel-sounds.prev.json`"),
        "each reel's own piece in the posting queue": ("`version`", "`reel_name`", "`...-reel-v2`"),
        "the cards of one shoot": ("`shoot.json`",),
        "sets of stories": ("`story-designs/<id>.json`",),
        "several talking reels": ("several talking reels",),
    }
    for what, names in records.items():
        missing = [n for n in names if n not in live]
        case("it names %s" % what, not missing, missing)

    group("Photos that are much alike: a short opener and few long holds (v25, section 10)")
    cur = flat(PLUGIN / "shared" / "curating.md")
    reel = texts["reel SKILL.md"]
    case("the choosing rules say it", bool(re.search(r"(?i)alike", cur)) and bool(re.search(r"(?i)opener[^.]*(?:plain|short)", cur)), "")
    case("the reel skill says it where the assistant marks a pick", bool(re.search(r"(?i)alike", reel)) and "Quicker" in reel, "")


# ---------------------------------------------------------------- the setup guides

def check_guides():
    group("The setup guides say what the home base shows now")
    mac, pc = flat(ROOT / "docs" / "SETUP-GUIDE.md"), flat(ROOT / "docs" / "SETUP-GUIDE-PC.md")
    stale = {
        "a list of recent shoots on the home page": r"your recent shoots",
        "a box that opens under the Make posts button": r"A box opens under it|the box says \*\*set up my Assistant folder\*\*|The box then changes",
        "an open question asked when a kit is made": r"asks one open question",
        "a kit made all at once, with hooks and a caption": r"single posts, a carousel, stories and a reel cover",
        "\"I'm done\" starting the reel and the carousel by itself": r"\(starts the reel and carousel\)",
        "one button at the bottom as the only way to the photos": r"and a button that opens the folder your photos are in\.",
    }
    for what, pat in stale.items():
        where = [n for n, t in (("the Mac guide", mac), ("the PC guide", pc)) if re.search(pat, t)]
        case("neither guide still describes %s" % what, not where, where)
    case("the Mac guide names the home base's four steps and the two screens of their own",
         all(w in mac for w in ("**Back up a card**", "**My editing queue**", "**Make posts from a shoot**", "**My posting queue**", "screen of their own")))
    case("the Mac guide's first posts: the Make posts screen, the folder picker, make my posts, then the post kit and nothing picked until they ask",
         all(w in mac for w in ("It opens a screen of its own", "**Select the folder with your finished photos**", "**make my posts**",
                                "opens the shoot's post kit beside the chat", "it doesn't pick photos or write anything until you ask",
                                "**Reel**, **Carousel** and **Stories**", "it's optional: **Add to my queue** works once a piece is made")))
    case("the Mac guide: each shoot on the report has Open this folder, and See the report is on the Back up a card screen",
         "its own **Open this folder** button" in mac and "**Back up a card** opens a screen that lists every backup" in mac and "**See the report** under it" in mac)
    case("the Mac guide tells delivered apart from done editing", "**the beach gallery is delivered**" in mac and "opens that shoot's post kit" in mac)
    case("the PC guide: Make posts is a screen of its own, the assistant stops at the post kit, and the report has Open this folder",
         all(w in pc for w in ("It opens a screen of its own", "and stops there", "it picks only when you ask", "its own **Open this folder** button",
                               "**Back up a card** screen lists every backup")))
    for name, t in (("the Mac guide", mac), ("the PC guide", pc)):
        case("%s: no long dash in the lines changed" % name, not re.search(r"screen of (?:its|their) own[^.]*—", t))


# ---------------------------------------------------------------- the reel page's player at a phone's width

def check_player_css():
    group("A wide video's player in a narrow window")
    t = read(SCRIPTS / "reel_page.py")
    # since Nicole's v27 (Nov 17) the per-video players are gone: one player in the footage editor, 9:16, at most
    # the window's width (her rule), so there is no wide player to narrow any more
    case("the per-video players and their rules are gone (v27: the footage editor's one player)", ".viewer video.wide" not in t and "id='viewers'" not in t)
    case("the editor's player is hers: 9:16, never wider than the window", ".edplayer{position:relative;background:#111;border-radius:14px;overflow:hidden;height:min(520px,70vh);aspect-ratio:9/16;max-width:100%;display:grid;place-items:center}" in t)


# ---------------------------------------------------------------- run

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", help="a folder to keep the run in (made here; must not exist or must be empty)")
    a = ap.parse_args()
    if a.work:
        work = Path(a.work)
        work.mkdir(parents=True, exist_ok=True)
        if any(work.iterdir()):
            print("STOP: %s is not empty." % work)
            return 2
        keep = True
    else:
        work = Path(tempfile.mkdtemp(prefix="loose-ends-v26-"))
        keep = False
    work = work.resolve()
    try:
        check_assistant()
        check_listed(work)
        check_parts()
        check_guides()
        check_player_css()
    finally:
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
    bad = RESULTS.count(False)
    print("\n%d checks, %d failed" % (len(RESULTS), bad), flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
