#!/usr/bin/env python3
"""Checks on words.py (the caption and hooks record), from Nicole's 18 acceptance checks in handoff v20,
plus ours. Runs in a throwaway folder with its own pretend Assistant; touches nothing else.

    python3 tests/words_check.py

Every line must say PASS. Python 3.9, standard library only, a Mac or a PC.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
WORDS = SCRIPTS / "words.py"
SHOOT = "2026-09-23 Hannah"
fails = 0

TMP = Path(tempfile.mkdtemp(prefix="words-check-")).resolve()
STUDIO = TMP / "studio"
HOME = TMP / "The Assistant"
KIT = HOME / "Your Content" / SHOOT
REC = KIT / ".kit" / "post-words.json"
ENV = dict(os.environ, STUDIO_HOME=str(STUDIO), PYTHONIOENCODING="utf-8")


def run(*args, ok=True):
    r = subprocess.run([sys.executable, str(WORDS), *args], capture_output=True, text=True, encoding="utf-8", env=ENV)
    if ok and r.returncode != 0:
        raise SystemExit(f"words.py {' '.join(args)} failed:\n{r.stdout}{r.stderr}")
    return r


def check(name, cond):
    global fails
    print(("PASS  " if cond else "FAIL  ") + name)
    fails += 0 if cond else 1


N = [0]


def jfile(d, bom=False):
    N[0] += 1
    f = TMP / f"in{N[0]}.json"
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8-sig" if bom else "utf-8")
    return str(f)


def rec():
    return json.loads(REC.read_text(encoding="utf-8"))


try:
    STUDIO.mkdir(parents=True)
    (KIT / ".kit").mkdir(parents=True)
    (KIT / "Photos").mkdir()
    (STUDIO / "studio.json").write_text(json.dumps({"posts": {"home": str(HOME)}}), encoding="utf-8")
    (KIT / ".kit" / "kit.json").write_text(json.dumps({"name": "Hannah"}), encoding="utf-8")
    old_words = {"hooks": ["An older hook"], "caption": "An older caption", "stories": [], "short": "", "hashtags": []}
    (KIT / ".kit" / "words.json").write_text(json.dumps(old_words), encoding="utf-8")

    (KIT / ".kit" / "told.json").write_text(json.dumps({"text": "A windy morning with Zoë."}, ensure_ascii=False), encoding="utf-8")
    early = run("ask", "hannah", "reel").stdout
    check("ask: what they said when the kit was made is offered for question 1, with their yes",
          "they said this when the kit was made" in early and "A windy morning with Zoë." in early and "Use that" in early)
    # no Homebase yet: it says so and asks, never looks further afield
    first = run("show", "hannah", "reel").stdout
    check("no Brand Homebase: says so and says to ask", "No Brand Homebase found. Ask them where it is" in first)
    check("... and names the exact file it would read", str(HOME / "brand-homebase.md") in first and "no other name or ending" in first)
    (HOME / "brand-homebase.txt").write_text("not this one", encoding="utf-8")
    check("... a file with another ending is not taken for it", "No Brand Homebase found" in run("show", "hannah", "reel").stdout)
    (HOME / "brand-homebase.txt").unlink()
    (HOME / "brand-homebase.md").write_text("# Brand Homebase\nWarm, plain, never salesy. Zoë says so.\n", encoding="utf-8")

    # the interview: one answer at a time
    run("answer", "hannah", "reel", "--file", jfile({"about": "This was a mommy and me shoot in Laguna. Zoë laughed 😊"}, bom=True))
    run("answer", "hannah", "reel", "--file", jfile({"notes": 'Names: say "Hannah and her two boys" (no names for the boys).'}))
    run("answer", "hannah", "reel", "--file", jfile({"who": ["new", "followers", "nonsense"], "who_text": "Moms like Hannah"}))
    run("answer", "hannah", "reel", "--file", jfile({"where": "feed", "purpose": "offer",
                                                    "purpose_text": "Mini sessions on December 4th in Laguna Beach, 12 to 4. $400, 20 photos."}))
    before = REC.read_bytes()
    bad = run("answer", "hannah", "reel", "--file", jfile({"purpose": "sell", "about": "should not land"}), ok=False)
    check("a purpose that isn't a button is refused", bad.returncode == 2 and "STOP" in bad.stdout)
    check("a refused answer changes nothing", REC.read_bytes() == before)
    a = rec()["pieces"]["reel"]["answers"]
    check("answers kept one at a time", a["about"].startswith("This was") and a["notes"].startswith("Names:") and a["where"] == "feed")
    check("an accent and an emoji come through a file with a byte-order mark", a["about"].endswith("Zoë laughed 😊"))
    check("only real 'who' buttons are kept", a["who"] == ["new", "followers"])
    empty = run("answer", "hannah", "reel", "--file", jfile({"something": "else"}), ok=False)
    check("an answer file with no answers is refused", empty.returncode == 2)

    show = run("show", "hannah", "reel").stdout
    check("show: the editor rule", "YOU'RE THE EDITOR" in show)
    check("show: the goal goes first", "OPTIMIZE FOR THE GOAL" in show)
    check("show: hooks point at who and the purpose, never describe the shoot", "Never describe the shoot as a hook" in show)
    check("show: points at the Brand Homebase", "Their Brand Homebase: " + str(HOME / "brand-homebase.md") in show)
    check("show: 10 hooks for a reel", "Write 10 hooks" in show)
    check("show: trial reel / feed shown", "Where it's going: On their feed" in show)

    cask = run("ask", "hannah", "carousel").stdout
    check("ask: a carousel with nothing answered offers the reel's answers, and does not offer the kit-start words",
          "Nothing is answered for the carousel yet, but the reel is" in cask and "words.py carry" in cask
          and "Use what I said for the reel" in cask and "when the kit was made" not in cask)
    ask = run("ask", "hannah", "reel").stdout
    check("ask: the reel, answered, is not offered the other piece's answers", "Nothing is answered for the reel yet" not in ask)
    check("ask: once question 1 is answered, the kit-start words are not offered again", "when the kit was made" not in ask)
    check("ask: names question and the follow-ups", "Do you want their names in it?" in ask and "Always follow up" in ask)
    check("ask: feed or trial reel, reels only", "Reels only: Is this going on your feed, or is it a trial reel?" in ask)

    hooks = [f"Hook {i}" for i in range(1, 11)]
    run("draft", "hannah", "reel", "--file", jfile({"caption": "MINI SESSIONS first.", "hooks": hooks}))
    sys.path.insert(0, str(SCRIPTS))
    os.environ["STUDIO_HOME"] = str(STUDIO)
    import words as W
    W.save_from_page(KIT, "reel", {"picked": [5, 5, 99, True], "own": "My own caption"})
    check("the page's picks: only real hooks, each once", rec()["pieces"]["reel"]["picked"] == [5])
    marked = [ln for ln in run("show", "hannah", "reel").stdout.splitlines() if "<- picked" in ln and ln.strip()[:1].isdigit()]
    check("show marks the hook they picked on the page, and only that one", len(marked) == 1 and marked[0].strip().startswith("6. Hook 6"))
    run("draft", "hannah", "reel", "--file", jfile({"caption": "MINI SESSIONS first, edited."}))
    r = rec()["pieces"]["reel"]
    check("draft: picks kept when only the caption changes", r["picked"] == [5])
    check("draft: their own caption is kept", r["own"] == "My own caption")
    check("draft: the version before is kept", (KIT / ".kit" / "post-words.prev.json").exists()
          and json.loads((KIT / ".kit" / "post-words.prev.json").read_text(encoding="utf-8"))["pieces"]["reel"]["caption"] == "MINI SESSIONS first.")
    run("draft", "hannah", "reel", "--file", jfile({"hooks": hooks[::-1]}))
    check("draft: picks cleared when the hooks change", rec()["pieces"]["reel"]["picked"] == [])
    check("show: with nothing picked, it says they pick on the page and never to choose for them",
          "None picked yet" in run("show", "hannah", "reel").stdout and "<- picked" not in run("show", "hannah", "reel").stdout)
    nothing = run("draft", "hannah", "reel", "--file", jfile({"caption": "  ", "hooks": []}), ok=False)
    check("an empty draft is refused", nothing.returncode == 2)

    # the carousel: their answers carried over, a caption only, and a different caption from the reel's
    out = run("carry", "hannah", "reel", "carousel").stdout
    ca = rec()["pieces"]["carousel"]["answers"]
    check("carry: the answers go to the carousel, without feed or trial", ca["about"].startswith("This was") and "where" not in ca and "Carried" in out)
    cshow = run("show", "hannah", "carousel").stdout
    check("carousel: a caption only, no cover lines", "Write one caption, and no cover lines" in cshow)
    check("carousel: told the reel's caption is there and must be different", "genuinely DIFFERENT" in cshow and "MINI SESSIONS first, edited." in cshow)
    task = run("ask", "hannah", "carousel").stdout
    check("carousel ask: ends with 'the caption is on the page'", "the caption is on the page." in task)
    run("draft", "hannah", "carousel", "--file", jfile({"caption": "A carousel caption.", "hooks": ["a cover line"]}))
    check("carousel: hooks handed in are not kept", not rec()["pieces"]["carousel"].get("hooks"))

    st = run("show", "hannah", "stories", ok=False)
    check("stories are not a piece any more", st.returncode != 0)
    s = W.status(KIT)
    check("status for the post kit", s["reel"]["caption"] and s["reel"]["hooks"] == 10 and s["carousel"]["caption"] and s["carousel"]["hooks"] == 0)
    check("the kit's older words file is left exactly as it was", json.loads((KIT / ".kit" / "words.json").read_text(encoding="utf-8")) == old_words)
    REC.write_text("{ not json", encoding="utf-8")
    run("answer", "hannah", "reel", "--file", jfile({"about": "After a damaged file."}))
    check("a damaged record is kept as the version before, and saving goes on",
          (KIT / ".kit" / "post-words.prev.json").read_text(encoding="utf-8") == "{ not json" and rec()["pieces"]["reel"]["answers"]["about"] == "After a damaged file.")
    left = [p.name for p in (KIT / ".kit").iterdir() if ".part" in p.name or p.name.endswith(".tmp")]
    check("no scratch files left behind", not left)
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("\nAll passed." if not fails else f"\n{fails} failed.")
sys.exit(1 if fails else 0)
