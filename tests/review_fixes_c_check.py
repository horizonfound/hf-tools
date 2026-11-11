#!/usr/bin/env python3
"""Check what the reviewers of v19's stories designer, post kit cards and skill text found (Nov 7), each with a
case that failed before its fix.

    python3 tests/review_fixes_c_check.py --work /private/tmp/somewhere --port 9760 [--only words|server|browser|text]

  words    a story's lines are turned into story words before they are filled in, so a shoot called "Slide Rock
           park" keeps its name (design.KW, the save lines, the commit command's lines)
  server   a visit to the stories designer (or the carousel's) writes an empty design, and the kit's cards and the
           shoot menu don't count it as theirs until it is changed or saved from; the kit page with odd records
           (a date that is a number, marks that are a list) is still built, and when it can't be built a saved
           copy from before her three cards is never sent as if it were current; kit.py show names the folder
           and counts like the sheet
  browser  the stories designer in a hidden Chrome: no "Saved" on a first visit nobody has touched (the carousel's
           first visit still says Saved, the Nov 6 default), and the page's story words never change a name put
           into a line
  text     the skill text: the reel page's line starts with step 1, the kit page server is started through
           home.py url, a single post says it takes the carousel's place, the reel skill's paths from one base,
           the footage look's feel line

It makes its pretend kits with tests/fake_kit.py in a new folder under /private/tmp (it refuses anywhere else),
points STUDIO_HOME there, runs the plugin under the Mac's own /usr/bin/python3 and starts its page server on
--port (up to --port + 20). It never touches the real ~/.studio. Run it with a Python that has Pillow.
Exit 0 when every case passes.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
PLUGIN = ROOT / "plugins" / "the-engine"
SCRIPTS = PLUGIN / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(TESTS))
import design_check as dc  # noqa: E402  (its helpers: case, Server, ask, post, get_json, run, make_kit)

case = dc.case
APPLE = dc.APPLE


def py(env, code):
    r = subprocess.run([APPLE, "-c", "import sys; sys.path.insert(0, %r)\n" % str(SCRIPTS) + code], capture_output=True, text=True, env=env, timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


# ---------- words: a story's line is filled in after it is turned into story words ----------

def check_words(work):
    env = dict(os.environ, STUDIO_HOME=str(work / "words-studio"))
    code, out = py(env, """
import json, design
S = design.STORIES
print(json.dumps({
  "saved": design._saved_words({"files": [1, 2, 3], "base": "Slide Rock park stories"}, S),
  "one": design._saved_words({"files": [1], "base": "Slide Rock park stories"}, S),
  "already": design.KW(S, design.ALREADY, base="Slide Rock park stories (2)"),
  "carousel": design._saved_words({"files": [1, 2], "base": "Slide Rock park carousel 1"}, design.CAROUSEL),
  "plain": design.KW(S, "Save slides"),
  "old_way": design.story_words(design.SAVED_SET.format(n=3, base="Slide Rock park stories")),
}))""")
    if not case("words: the save lines can be made under the Mac's own Python", code == 0, out[-400:]):
        return
    w = json.loads(out.splitlines()[-1])
    case("words: the old way (fill in, then swap the words) renamed the shoot: this is what the fix stops",
         'named "Story Rock park stories"' in w["old_way"], w["old_way"])
    case("words: a story's save line keeps the shoot's name exactly as the files on disk have it",
         w["saved"] == 'Saved 3 stories in your Stories folder, named "Slide Rock park stories". Nothing was replaced.', w["saved"])
    case("words: the one-story line too", '"Slide Rock park stories"' in w["one"] and "1 story in your Stories folder" in w["one"], w["one"])
    case("words: \"Already saved as\" keeps the name", w["already"].startswith('Already saved as "Slide Rock park stories (2)".'), w["already"])
    case("words: a carousel's line is as it was", w["carousel"] == 'Saved 2 slides in your Carousel folder, named "Slide Rock park carousel 1". Nothing was replaced.', w["carousel"])
    case("words: a line with nothing to fill in is still turned into a story's words", w["plain"] == "Save stories", w["plain"])
    src = (SCRIPTS / "design.py").read_text(encoding="utf-8")
    left = re.findall(r"KW\([^()]*?(?:\([^()]*\))?[^()]*?\.format\(", src)
    case("words: no line in design.py is filled in before it goes through KW", not left, left[:3])
    left_f = [ln.strip() for ln in src.splitlines() if re.search(r"KW\([^,]+, f\".*\{(?:res|j|cs|d)\[?['\"]?(?:base|name)", ln)]
    case("words: no f-string puts a set's or a design's name inside KW", not left_f, left_f[:3])


# ---------- server: the empty design a visit makes, the kit page with odd records, kit.py show ----------

def card(page, piece):
    m = re.search(r"<a class='piece' data-piece='" + piece + r"'.*?</a>", page, re.S)
    return re.sub(r"<[^>]+>", " ", m.group(0)) if m else ""


def check_server(work, port):
    target = work / "server"
    ok, out = dc.make_kit(target, "Slide Rock park", 10)
    if not case("server: a pretend kit called \"Slide Rock park\" was made (tests/fake_kit.py)", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Slide Rock park"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    rec_file, words_file, saved_page = kit / ".kit" / "kit.json", kit / ".kit" / "words.json", kit / ".kit" / "Post kit.html"
    srv = dc.Server(env, port)
    try:
        P = srv.start()

        def kit_page():
            code, h, data = dc.ask(P, "GET", f"/content/{KQ}/Post%20kit.html")
            return code, html.unescape(data.decode("utf-8", "replace"))

        code, page = kit_page()
        case("kit page: before anything, Stories says Make my stories and Not made yet",
             code == 200 and "Make my stories" in card(page, "stories") and "Not made yet" in card(page, "stories"), card(page, "stories")[:300])
        case("kit page: before anything, Carousel says Design my carousel and Not made yet",
             "Design my carousel" in card(page, "carousel") and "Not made yet" in card(page, "carousel"), card(page, "carousel")[:300])

        # a look at the stories designer and the carousel designer, and nothing done there
        code, st = dc.get_json(P, f"/design-state?kit={KQ}&kind=stories")
        if not case("visit: the stories designer answers on its first visit", code == 200 and st and st.get("ok"), (code, st and st.get("words"))):
            return
        sdesign = st["design"]
        code, cst = dc.get_json(P, f"/design-state?kit={KQ}")
        case("visit: the first visits wrote a design each (the page needs a record to save into), marked as nobody's work yet",
             (kit / ".kit" / "story-designs" / f"{sdesign['id']}.json").is_file() and sdesign.get("untouched") is True
             and cst and cst["design"].get("untouched") is True, (sdesign.get("untouched"), cst and cst["design"].get("untouched")))
        code, page = kit_page()
        case("kit page after only looking: Stories still says Make my stories and Not made yet, not \"1 saved design\" (hers writes nothing until a change)",
             "Make my stories" in card(page, "stories") and "Not made yet" in card(page, "stories") and "saved design" not in card(page, "stories"), card(page, "stories")[:300])
        case("kit page after only looking: Carousel still says Design my carousel and Not made yet",
             "Design my carousel" in card(page, "carousel") and "Not made yet" in card(page, "carousel") and "saved design" not in card(page, "carousel"), card(page, "carousel")[:300])
        case("shoot menu after only looking: no designs counted", any(x["kit"] == kit_name and x["designs"] == 0 and x["story_designs"] == 0 for x in st["shoots"]), st["shoots"])

        # one change on the stories page
        state = {"slides": 2, "bg": "#ffffff", "blocks": []}
        code, out = dc.post(P, "/design", {"kit": kit_name, "kind": "stories", "design": sdesign["id"], "stamp": st["stamp"], "base": 0,
                                           "page": "fixcpage01", "state": state})
        case("change: a second story added on the page is saved", code == 200 and out.get("ok") and out.get("rev") == 1, (code, out))
        code, page = kit_page()
        case("kit page after a change: Stories says Open my stories and 1 saved design, no stories saved yet",
             "Open my stories" in card(page, "stories") and "1 saved design, no stories saved yet" in card(page, "stories"), card(page, "stories")[:300])
        case("kit page after a change: the carousel nobody touched is still not counted", "Not made yet" in card(page, "carousel"), card(page, "carousel")[:300])
        code, st2 = dc.get_json(P, f"/design-state?kit={KQ}&kind=stories")
        case("after a change: the stories design is no longer marked untouched, and the shoot menu counts it",
             st2["design"].get("untouched") is False and any(x["kit"] == kit_name and x["story_designs"] == 1 for x in st2["shoots"]), st2["design"].get("untouched"))

        # kit.py show: the folder named on the Photos line, the count the sheet gives
        code, out = dc.run(env, "kit.py", "show", kit_name)
        n_sheet = len(json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"])
        m = re.search(r"Photos: (\d+) in (.+)", out)
        case("kit.py show: the Photos line names the folder after \"in\" and counts what the sheet numbers",
             code == 0 and m and int(m.group(1)) == n_sheet and Path(m.group(2).strip()) == kit / "Photos", out)

        # odd records, changed by hand: the page is still built from them
        rec = json.loads(rec_file.read_text(encoding="utf-8"))
        good = json.dumps(rec, ensure_ascii=False, indent=2)
        try:
            rec_file.write_text(json.dumps(dict(rec, date=20261101), ensure_ascii=False), encoding="utf-8")
            code, page = kit_page()
            case("odd record: a date that is a number: the page is still built (her three cards), not an old saved copy",
                 code == 200 and "data-piece='stories'" in page and "assistant-page" in page, (code, page[:200]))
            rec_file.write_text(json.dumps(dict(rec, reel_marks=["+"], picks=dict(rec.get("picks") or {}, reel=[1, 2, 3])), ensure_ascii=False), encoding="utf-8")
            code, page = kit_page()
            case("odd record: reel marks saved as a list: the page is still built", code == 200 and "data-piece='reel'" in page, (code, page[:200]))
            rec_file.write_text(json.dumps(dict(rec, picks=["not", "a", "dict"]), ensure_ascii=False), encoding="utf-8")
            code, page = kit_page()
            case("odd record: picks saved as a list: the page is still built", code == 200 and "data-piece='reel'" in page, (code, page[:200]))
        finally:
            rec_file.write_text(good, encoding="utf-8")

        # the page can't be built at all (the shoot's name saved as a number; before Nov 10 this was a words file that
        # was not JSON, which the page no longer reads): a saved copy from before her cards is never sent
        bad = json.dumps(dict(json.loads(good), name=7), ensure_ascii=False)
        rec_file.write_text(bad, encoding="utf-8")
        try:
            saved_page.write_text("<!doctype html><html><head><link href='https://fonts.googleapis.com/css2?family=Fraunces'></head>"
                                  "<body>OLD PAGE: Change the photos</body></html>", encoding="utf-8")
            code, page = kit_page()
            case("can't build, old saved copy: the old page is not sent; one line says something couldn't be read and to tell Claude",
                 code == 500 and "OLD PAGE" not in page and "couldn't be read" in page and "Tell Claude" in page and "googleapis" not in page, (code, page[-300:]))
            rec_file.write_text(good, encoding="utf-8")
            c2, out2 = dc.run(env, "kit.py", "page", kit_name)
            rec_file.write_text(bad, encoding="utf-8")
            code, page = kit_page()
            case("can't build, saved copy of today's page: that copy is sent (it carries the page's mark)",
                 c2 == 0 and code == 200 and "data-piece='stories'" in page and "assistant-page" in page, (c2, out2[-200:], code))
        finally:
            rec_file.write_text(good, encoding="utf-8")
        code, page = kit_page()
        case("records put right: the page is built again", code == 200 and "data-piece='stories'" in page)
        words_file.write_text("{not json", encoding="utf-8")
        try:
            code, page = kit_page()
            case("an older kit's words.json that can't be read never stops the page (the page no longer reads it), and is left as it is",
                 code == 200 and "data-piece='stories'" in page and words_file.read_text(encoding="utf-8") == "{not json", code)
        finally:
            words_file.unlink()
    finally:
        srv.stop()


# ---------- browser: the stories page on a first visit, and its words ----------

def check_browser(work, port):
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  the stories page in a hidden Chrome: no Chrome on this computer", flush=True)
        return
    target = work / "browser"
    ok, out = dc.make_kit(target, "Slide Rock park", 8)
    if not case("browser: a pretend kit was made", ok, out):
        return
    env = dict(os.environ, STUDIO_HOME=str(target / "studio"))
    kit_name = "2026-11-01 Slide Rock park"
    KQ = quote(kit_name)
    srv = dc.Server(env, port)
    try:
        P = srv.start()
        base = f"http://127.0.0.1:{P}"
        with cd.Chrome(work=work / "chrome", size=(1280, 900)) as c:
            c.init_script("window.__noFinder = true;")
            c.open(f"{base}/design.html?kit={KQ}&kind=stories")
            c.wait_for("window.Designer && Designer.st && Designer.S", 20)
            c.js("void 0")
            status = c.js("document.getElementById('d-status').textContent")
            case("stories, first visit nobody touched: no \"Saved\" beside it (hers says nothing until the first change)", status == "", status)
            got = c.js("Designer.storyWords({a: function(x, k){ return 'Saved ' + k + ' slides as \"' + x + '\" in your Carousel folder'; }}).a('Slide Rock park slide show', 3)")
            case("stories page: a words line keeps a name put into it, and its own words become a story's",
                 got == 'Saved 3 stories as "Slide Rock park slide show" in your Stories folder', got)
            got = c.js("Designer.WORDS.nameText('Slide two here', 2)")
            case("stories page: the page's own lines too (a text box's name on a story)", got == "Text on story 2: Slide two here", got)
            got = c.js("Designer.storyWords({a: function(names){ return names.length + ' fonts: ' + names.join(', ') + ' on a slide'; }}).a(['Slide Sans', 'Inter'])")
            case("stories page: a list of names keeps every name, and its length", got == "2 fonts: Slide Sans, Inter on a story", got)
            got = c.js("Designer.storyWords({a: function(w){ return 'Text on slide 1' + (w ? ': ' + w : ''); }}).a('')")
            case("stories page: an empty text stays empty", got == "Text on story 1", got)
            c.open(f"{base}/design.html?kit={KQ}")
            c.wait_for("window.Designer && Designer.st && Designer.S", 20)
            c.wait_for("document.getElementById('d-status').textContent !== ''", 10)
            status = c.js("document.getElementById('d-status').textContent")
            case("carousel, first visit: still says Saved (the Nov 6 default, unchanged)", status == "Saved", status)
            case("browser: no page error", c.page_errors() == [], c.page_errors()[:3])
    finally:
        srv.stop()


# ---------- text: the skill's words ----------

def check_text():
    skills = PLUGIN / "skills"
    arrange = (skills / "studio-manager" / "parts" / "arrange.md").read_text(encoding="utf-8")
    postkit = (skills / "studio-manager" / "parts" / "post-kit.md").read_text(encoding="utf-8")
    reel = (skills / "assistant-make-a-reel" / "SKILL.md").read_text(encoding="utf-8")
    footage = (SCRIPTS / "footage.py").read_text(encoding="utf-8")
    line = "Choose Just photos (or add your footage), move anything you like, add your song, and press Make my reel."
    case("text: the reel page's line starts with step 1 (Make my reel waits for it), the same in both places",
         line in arrange and line in reel and "add your song, pick the vibe, and press Make my reel" not in arrange + reel)
    step6 = next((ln for ln in postkit.splitlines() if ln.startswith("6. Show the kit page")), "")
    case("text: the kit's step 6 starts the page server through home.py url, never a foreground posting_queue.py serve",
         "home.py url" in step6 and "posting_queue.py serve" not in step6, step6[:200])
    single = arrange[arrange.find("**A single post"):][:2500]
    case("text: a single post says it takes the carousel's place on the kit page and in the posting queue, and that saving the carousel brings it back",
         "in place of your carousel" in single and "saving the carousel again brings it back" in single and "Dustin and Nicole" in single, single[:200])
    case("text: \"Singles have no page\" now says which singles", "The plain singles `kit.py build` makes" in arrange)
    bare = [ln[:100] for ln in reel.splitlines() if re.search(r"python3 scripts/|`\.\./|\(\.\./|\"\.\./", ln)]
    case("text: the reel skill writes every path from one base (no bare scripts/ or ../)", not bare and "${CLAUDE_SKILL_DIR}/scripts" in reel and "<assistant scripts>/kit.py" in reel, bare[:3])
    case("text: arrange.md counts the reel skill's path from the skill's folder, like the core", "../../assistant-make-a-reel" not in arrange and "`../assistant-make-a-reel/SKILL.md`" in arrange)
    case("text: the reel skill's Step 1 reads the folder from the Photos line's \"in\"", 'names on its Photos line, after "in"' in reel)
    case("text: the footage look's feel line asks for the moments only, and the photos stay the pick",
         "Choose the photos and the moments" not in footage and "the photos stay the reel's photo pick" in footage
         and "The feel steers the moments, not the photos." in reel)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True)
    ap.add_argument("--port", type=int, default=9760)
    ap.add_argument("--only", choices=["words", "server", "browser", "text"])
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if dc.SAFE not in work.parents:
        print(f"STOP: {work} is not under {dc.SAFE}.")
        return 2
    work.mkdir(parents=True, exist_ok=True)
    if any((work / n).exists() for n in ("server", "browser")):
        print(f"STOP: {work} already holds a pretend kit from an earlier run. Give a new --work folder.")
        return 2
    os.environ["STUDIO_HOME"] = str(work / "no-studio")
    if a.only in (None, "words"):
        check_words(work)
    if a.only in (None, "server"):
        check_server(work, a.port)
    if a.only in (None, "browser"):
        check_browser(work, a.port + 10)
    if a.only in (None, "text"):
        check_text()
    bad = [n for n, ok in dc.results if not ok]
    print(f"\n{len(dc.results)} cases, {len(dc.results) - len(bad)} passed, {len(bad)} failed.  Work folder: {work}")
    for n in bad:
        print("  FAILED:", n)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
