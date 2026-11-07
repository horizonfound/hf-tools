#!/usr/bin/env python3
"""The reel page becomes the way in (v19 stage a5), and the chat only picks.

    /usr/bin/python3 tests/reel_door_check.py --work /private/tmp/somewhere [--port 9141]

What it checks, on a pretend kit it makes itself (tests/fake_kit.py; nothing of a client's):
  * the words Claude reads: the reel skill and the Assistant's parts have no step that still asks the song or
    the vibe in the chat; the reel picker is no longer what they open; post-kit.md no longer makes the reel in
    the same breath as the kit (decision 14); the core table sends "pick my reel photos" to parts/arrange.md;
    nothing anywhere still says Longer and Quicker count with one vibe only;
  * the kit page: its reel "Change the photos" goes to the reel page (kit.REEL_DOOR, decision 3), the carousel's
    still to the carousel's picker, and the old reel picker still answers when asked for by name;
  * in a HIDDEN Chrome: pressing the reel's "Change the photos" on the kit page opens the reel page, and a fresh
    pick from the chat (kit.py picks --reel) shows on that open page by itself;
  * reel_page.py show (the order, the song, the vibe) and reel_page.py make (Claude's own Make my reel): it stops
    when no song is picked on the page, a dry run makes nothing, a real one makes one CapCut project in a pretend
    CapCut folder under this run's own HOME, records it, and a CapCut song that isn't there stops in plain words.

Nothing outside --work is touched; CapCut is never started and no folder is ever opened (reel_page's two test
switches). Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED.
"""
import argparse
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PLUGIN = ROOT / "plugins" / "the-engine"
SM = PLUGIN / "skills" / "studio-manager"
REEL_SKILL = PLUGIN / "skills" / "assistant-make-a-reel" / "SKILL.md"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import reel_page_check as rpc  # noqa: E402

KIT = rpc.KIT
KQ = quote(KIT)
ORDER = rpc.ORDER


# ---------- 1. the words Claude reads ----------

def _asked(text):
    """Every question put to the photographer with buttons in a skill text: '"...?" [' (a quoted question
    followed by its buttons) and 'Ask with buttons: "...' lines."""
    out = [m.group(1) for m in re.finditer(r'"([^"\n]{3,200}\?)"\s*\[', text)]
    out += [m.group(1) for m in re.finditer(r'Ask with buttons[^:\n]*:\s*"([^"\n]{3,200})', text)]
    return out


def check_words():
    reel = REEL_SKILL.read_text(encoding="utf-8")
    arr = (SM / "parts" / "arrange.md").read_text(encoding="utf-8")
    kit_part = (SM / "parts" / "post-kit.md").read_text(encoding="utf-8")
    core = (SM / "SKILL.md").read_text(encoding="utf-8")
    texts = {"the reel skill": reel, "parts/arrange.md": arr, "parts/post-kit.md": kit_part}
    for name, t in texts.items():
        bad = [q for q in _asked(t) if re.search(r"\b(song|songs|music|vibe|move|feel|pace)\b", q, re.I)]
        case("%s puts no question about the song or the vibe to them with buttons" % name, not bad, bad)
        case("%s never runs the old reel picker as the way in (arrange.py open ... --piece reel)" % name,
             not re.search(r"arrange\.py open \"<kit>\" --piece reel", t), re.findall(r".{0,40}arrange\.py open \"<kit>\" --piece reel.{0,20}", t))
    case("the reel skill: no 'Which song?' and no 'How should it move?' asked in the chat",
         "Which song?" not in reel and 'Ask with buttons, in Nicole' not in reel and "Always ask this question" not in reel)
    case("the reel skill says the page asks the song and the vibe, never the chat",
         "The song and the vibe are asked on the page, never in the chat." in reel and "## Step 3: the song (on the page)" in reel
         and "## Step 4: the vibe (on the page)" in reel)
    case("the reel skill opens the reel page (reel_page.py open) and saves the pick with kit.py picks --reel",
         'reel_page.py open "<kit>"' in reel and 'kit.py picks "<kit>" --reel' in reel)
    case("the reel skill answers 'pick my reel photos for <shoot>' (her not-picked line) with a pick and one line",
         "Pick my reel photos for the beach shoot" in reel and "pick my reel photos for a shoot" in reel.split("---")[1])
    case("the reel skill: words on the first photo and trial reels only when they ask (decision 15)",
         "## Step 5: words on the first photo, and trial reels (only if they ask)" in reel and "Want words on the first photo?" not in reel)
    case("the reel skill: CapCut's own music only when they ask, with the licence note, made from the chat (decision 2)",
         "They ask for a song from CapCut's own music" in reel and "reel.py capcut-ok" in reel and "--capcut-song" in reel)
    case("parts/arrange.md: the reel's page is the reel page, with its three commands",
         "## The reel's page" in arr and all(('reel_page.py %s "<kit>"' % c) in arr for c in ("open", "show", "make")))
    case("parts/arrange.md: no reel step waits on 'Go with these?' before a song question", "Next I'll ask which song" not in arr and "Go with these?" not in arr)
    case("parts/post-kit.md: the reel is not made as part of the kit (decision 14)",
         "Then the reel through the reel skill" not in kit_part and "reel.py make" not in kit_part and "**The reel is not made here**" in kit_part)
    row = next((ln for ln in core.splitlines() if "`parts/arrange.md`" in ln and ln.startswith("|")), "")
    case("the core table sends 'pick my reel photos for <shoot>' to parts/arrange.md", '"pick my reel photos for <shoot>"' in row, row[:200])
    stale = []
    for p in PLUGIN.rglob("*"):
        if p.suffix in (".md", ".py") and p.is_file():
            t = p.read_text(encoding="utf-8", errors="replace")
            if re.search(r"only (count|when the reel moves)|count when the reel moves|aren't used", t):
                stale.append(p.name)
    case("nothing in the plugin still says Longer and Quicker count with one vibe only", not stale, stale)


# ---------- 2. the kit page's link and the old picker ----------

def check_links(s):
    sys.path.insert(0, str(SM / "scripts"))
    import kit as kit_mod
    case("kit.REEL_DOOR is 'reel-page' (decision 3)", kit_mod.REEL_DOOR == "reel-page", kit_mod.REEL_DOOR)
    case("kit.reel_door names the reel page by the kit's folder name only", kit_mod.reel_door(KIT) == "/reel.html?kit=" + KQ, kit_mod.reel_door(KIT))
    code, out = s.cmd("kit.py", "page", str(s.kit))
    case("kit.py page writes the kit page", code == 0, out[-300:])
    code, _, raw = s.http("GET", "/content/%s/Post%%20kit.html" % KQ)
    page = raw.decode("utf-8", "replace")
    found = re.findall(r"<a class='arr' href='([^']+)'>(Change the photos|Create my reel →|Make a new version →)</a>", page)
    links = [h for h, _ in found]
    case("the kit page has the reel's link in the Reel section and 'Change the photos' in the Carousel section", code == 200 and len(links) == 2, (code, found))
    case("the reel's link says her words: 'Create my reel →' before a reel is made (v19 review: not 'Change the photos')",
         [w for _, w in found][:1] == ["Create my reel →"] and [w for _, w in found][1:] == ["Change the photos"], found)
    case("...and the line beside it points at that link, not at the chat",
         "Not made yet. Press Create my reel to pick your song and make it." in page and "Say “make the reel” to Claude" not in page)
    case("the Reel section's link goes to the reel page", links[:1] == ["/reel.html?kit=" + KQ], links)
    case("the Carousel section's link still goes to the carousel's picker", links[1:] == ["/arrange.html?kit=%s&amp;piece=carousel" % KQ], links)
    code, _, raw = s.http("GET", html.unescape(links[0])) if links else (0, None, b"")
    case("the reel page answers at that address with her step 2", code == 200 and "Put your photos in order" in raw.decode("utf-8", "replace"), code)
    code, _, raw = s.http("GET", "/arrange.html?kit=%s&piece=reel" % KQ)
    case("the old reel picker still works when asked for by name", code == 200 and b"data-piece='reel'" in raw, code)
    code, out = s.cmd("arrange.py", "open", KIT, "--piece", "reel")
    case("arrange.py open --piece reel still prints its address", code == 0 and out.strip().splitlines()[-1].endswith("/arrange.html?kit=%s&piece=reel" % KQ), out[-200:])
    code, out = s.cmd("reel_page.py", "open", KIT)
    case("reel_page.py open prints the reel page's address on its last line", code == 0 and out.strip().splitlines()[-1] == s.url("/reel.html?kit=" + KQ), out[-200:])


# ---------- 3. in a hidden Chrome: the link pressed, and a pick from the chat followed ----------

def check_browser(c, s):
    c.open(s.url("/content/%s/Post%%20kit.html" % KQ))
    c.wait_for("document.body.classList.contains('live')", 10)
    sel = "a.arr[href^='/reel.html']"
    case("in a browser: the Reel section's 'Create my reel' is showing", c.count(sel) == 1 and c.text(sel) == "Create my reel →"
         and c.js("(function(){var a=document.querySelector(\"%s\"); return a.closest('section').querySelector('h2').textContent.indexOf('Reel')===0 && a.getBoundingClientRect().width>40})()" % sel) is True)
    c.click(sel)
    try:
        c.wait_for("location.pathname === '/reel.html' && document.querySelector('h1') && document.querySelectorAll('#reel .tile').length > 0", 20)
        went = True
    except chrome_drive.Timeout:
        went = False
    case("pressing it opens the reel page, with the assistant's pick in the row", went and c.js("new URLSearchParams(location.search).get('kit')") == KIT
         and c.js(ORDER) == rpc.CLAUDE, (went, c.js("location.href")))
    case("...and the page is her reel page: her title and her step 2", "Fake beach reel" in c.text("h1") and "Put your photos in order" in c.js("document.body.innerText"), c.text("h1"))
    # the chat picks ("pick my reel photos for Fake beach"): the open page follows it by itself
    fresh = [7, 2, 11, 4, 9]
    code, out = s.cmd("kit.py", "picks", str(s.kit), "--reel", "7,2,11+,4,9-")
    case("the chat's pick is written through a command (kit.py picks --reel)", code == 0, out[-200:])
    st = s.state()
    case("the page's state shows the chat's pick, marks and all", [x["n"] for x in st["claude"]] == fresh and [x["h"] for x in st["claude"]] == ["", "", "+", "", "-"], st["claude"])
    try:
        c.wait_for("JSON.stringify(%s) === %s" % (ORDER, json.dumps(json.dumps(fresh, separators=(",", ":")))), 12)
        followed = True
    except chrome_drive.Timeout:
        followed = False
    case("the open page shows the chat's new pick by itself, within a few seconds", followed, c.js(ORDER))
    case("...with Longer and Quicker where the chat marked them", c.js(rpc.MARKS) == ["", "", "+", "", "-"], c.js(rpc.MARKS))
    case("the page threw no error", c.page_errors() == [], c.page_errors()[:3])


# ---------- 4. reel_page.py show and make (Claude's own Make my reel) ----------

def check_commands(s):
    rec_before = s.record() or {}
    code, out = s.cmd("reel_page.py", "show", KIT)
    case("show: the order Make my reel uses, and that no song or vibe is picked yet",
         code == 0 and "The order Make my reel uses: 7,2,11+,4,9-" in out and "Song: not picked on the page yet" in out
         and "Vibe: not picked on the page yet (Make my reel would use On every beat)" in out, out[-500:])
    code, out = s.cmd("reel_page.py", "make", KIT)
    case("make with no song picked on the page stops, says so, and makes nothing",
         code == 1 and "STOP: no song is picked on the page yet" in out and not list(s.store.iterdir()), out[-300:])
    code, out = s.cmd("reel_page.py", "make", KIT, "--no-song", "--dry-run")
    case("make --dry-run: her lines (Plan, Beats per piece), and nothing is made or recorded",
         code == 0 and out.startswith("Plan: 5 photos") and "Beats per piece" in out and "Made:" not in out and not list(s.store.iterdir())
         and len((s.record() or {}).get("made") or []) == len(rec_before.get("made") or []), out[-400:])
    case("make --dry-run: no path in what it says", not re.search(r"/private/|/Users/|\.jpg", out), out[-300:])
    code, out = s.cmd("reel_page.py", "make", KIT, "--capcut-song", "No such song anywhere")
    case("make --capcut-song with a song that isn't in their CapCut projects stops in plain words",
         code == 1 and "STOP: no song called" in out and not re.search(r"/private/|/Users/", out), out[-300:])
    code, out = s.cmd("reel_page.py", "make", KIT, "--no-song")
    projects = [p.name for p in s.store.iterdir() if p.is_dir()]
    case("make --no-song: one CapCut project, named after the kit's folder, in the pretend CapCut folder only",
         code == 0 and out.strip().splitlines()[-1] == "Made: %s reel" % KIT and projects == ["%s reel" % KIT], (out[-300:], projects))
    rec = s.record() or {}
    made = rec.get("made") or []
    case("make: the reel is recorded on the reel page's record, with the order and the vibe it was made from",
         len(made) == len(rec_before.get("made") or []) + 1 and made[-1].get("picks") == "7,2,11+,4,9-" and made[-1].get("vibe") == "beat"
         and made[-1].get("project") == "%s reel" % KIT, made[-1:] if made else rec)
    k = json.loads((s.kit / ".kit" / "kit.json").read_text(encoding="utf-8"))
    case("make: and in the kit's own record, through kit.py reel-made", (k.get("reel") or {}).get("project") == "%s reel" % KIT, k.get("reel"))
    code, out = s.cmd("reel_page.py", "show", KIT)
    case("show: says how many reels were made, and the newest", "Reels made from the page: 1, the newest \"%s reel\"" % KIT in out, out[-300:])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True)
    ap.add_argument("--port", type=int, default=9141)
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp")
        return 2
    group("the words Claude reads", check_words)
    s = rpc.Setup(work, a.port)
    s.make()
    run = work / "chrome"
    run.mkdir(parents=True, exist_ok=True)
    s.start()
    try:
        group("the kit page's link and the old picker", check_links, s)
        if chrome_drive.find_chrome():
            with chrome_drive.Chrome(work=str(run), size=(1280, 1100)) as c:
                group("in a hidden Chrome", check_browser, c, s)
        else:
            print("SKIP  the hidden-Chrome part: no Chrome on this computer", flush=True)
        time.sleep(0.2)
        group("reel_page.py show and make", check_commands, s)
    finally:
        s.stop()
    return rpc.summary()


if __name__ == "__main__":
    sys.exit(main())
