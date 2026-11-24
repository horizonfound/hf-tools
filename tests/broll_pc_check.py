#!/usr/bin/env python3
"""B-roll on a PC is said up front (Nicole, Nov 23: "thats ok. Make sure it states that so theyre aware if they
have a PC"). Save my video is a Mac's only (this_computer.NO_VIDEO_PC), so where no finished video can be made
(a PC; here the switch the reel tests use, ASSISTANT_NO_AVFOUNDATION=1) the photographer is told BEFORE any press:

  * the chooser's B-roll card carries one short line of ours;
  * the B-roll page's watch step says Make this one in CapCut where hers says Save my video, shows
    this_computer.NO_VIDEO_PC right under it, draws no Save my video button, and makes Make this one in CapCut
    the main button;
  * a Mac's pages are what they were: her sentence, Save my video the main button, no PC line anywhere;
  * the other kinds of reel are untouched on a PC;
  * the instructions' PC part says the same gap in the same words.

No browser, no page server, no kit: the pages are written by reel_page.py's own functions, in a process of its
own for each computer, with a scratch STUDIO_HOME. Runs on python3 and on Apple's /usr/bin/python3.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
PARTS = SCRIPTS.parent / "parts"
RESULTS = []

ASK = r"""
import json, re, sys
sys.path.insert(0, sys.argv[1])
import reel_page as R, this_computer as T
def watch(kind):
    page = R.page_html("Fake Beach_10-18-26", "Fake Beach", False, kind)
    m = re.search(r"<section class='step watch' id='watch'>.*?</section>", page, re.S)
    return m.group(0) if m else ""
print(json.dumps({"pc": R.pc_footage(), "chooser": R.chooser_html("Fake Beach_10-18-26", "Fake Beach"),
                  "broll": watch("broll"), "photos": watch("photos"), "bts": watch("bts"),
                  "hers": R.WATCH_WORDS["pv_say_broll_html"], "ours": R.OUR_WORDS["pv_say_broll_pc_html"],
                  "card": R.OUR_WORDS["broll_card_pc"], "gap": T.NO_VIDEO_PC, "save": R.ONSCREEN_WORDS["os_save"],
                  "make": R.WATCH_WORDS["pv_make"], "card_s": R.KIND_WORDS["kind_broll_s"]}))
"""


def case(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else "   " + str(detail)[:600]))


def pages(home, pc):
    env = dict(os.environ, STUDIO_HOME=str(home), PYTHONIOENCODING="utf-8", STUDIO_NO_WINDOWS_FOR_TESTS="1")
    env.pop("ASSISTANT_NO_AVFOUNDATION", None)
    if pc:
        env["ASSISTANT_NO_AVFOUNDATION"] = "1"
    r = subprocess.run([sys.executable, "-c", ASK, str(SCRIPTS)], env=env, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def button(html_, bid):
    i = html_.find("id='" + bid + "'")
    if i < 0:
        return None
    a = html_.rfind("<button", 0, i)
    return html_[a:html_.find(">", i) + 1]


def main():
    work = Path(tempfile.mkdtemp(prefix="broll-pc-"))
    home = work / "studio"
    home.mkdir()
    real = Path.home() / ".studio"
    case("the home here is a scratch one, never the real ~/.studio", home.resolve() != real.resolve())
    pc, mac = pages(home, True), pages(home, False)

    # --- a PC
    case("the switch makes this a computer with no finished video (a PC's way)", pc["pc"] is True)
    ch = pc["chooser"]
    case("a PC: the chooser's B-roll card carries our one short line, inside the card, after her line",
         "id='kBrollPc'" in ch and pc["card"] in ch.replace("&#x27;", "'") and ch.find(pc["card_s"]) < ch.find("id='kBrollPc'") < ch.find("</a>", ch.find("id='kBroll'")), ch[-900:])
    case("... on the B-roll card only (once on the page)", ch.count("class='pcnote'") == 1)
    case("... and it says CapCut and that the finished video is a Mac's, in under 100 letters",
         "CapCut" in pc["card"] and "Mac only" in pc["card"] and len(pc["card"]) < 100 and "Claude" not in pc["card"] and "your assistant" not in pc["card"].lower(), pc["card"])
    b = pc["broll"]
    case("a PC: the B-roll watch step is drawn", bool(b))
    case("a PC: its first line is ours: Make this one in CapCut, never Save my video or 'no CapCut needed'",
         "<p class='say' id='pvSayBroll'>" + pc["ours"] + "</p>" in b and pc["hers"] not in b and "Save my video" not in pc["ours"] and "no CapCut needed" not in pc["ours"], b[:700])
    case("... our line is her sentence with only the button changed",
         pc["ours"] == pc["hers"].replace("<b>Save my video</b>: it's finished and ready to post, no CapCut needed.", "<b>Make this one in CapCut</b>."), (pc["ours"], pc["hers"]))
    gap = pc["gap"].replace("'", "&#x27;")
    case("a PC: this_computer.NO_VIDEO_PC is on the page up front, right under that line and above the player",
         ("</p><p class='say sm pcnote' id='pvPcNote'>" + gap + "</p>") in b and b.find("id='pvPcNote'") < b.find("id='pvPhone'"), b[:900])
    sv, mk = button(b, "pvSaveVid"), button(b, "pvMake")
    case("a PC: Save my video is not shown (hidden; the page's script still finds it)", sv is not None and " hidden" in sv, sv)
    case("a PC: Make this one in CapCut is the main button", mk is not None and "class='btn main'" in mk and (">" + pc["make"] + "<") in b, mk)
    case("a PC: exactly one main button in the watch step that can be seen",
         b.count("class='btn main'") == 2 and " hidden" in sv, b.count("class='btn main'"))
    for kind in ("photos", "bts"):
        case("a PC: the %s reel's watch step has no PC line and no Save my video (it never had one)" % kind,
             "pvPcNote" not in pc[kind] and "pvSaveVid" not in pc[kind] and "class='btn main' id='pvMake'" in pc[kind])
        case("a PC and a Mac: the %s reel's watch step is the same" % kind, pc[kind] == mac[kind])

    # --- a Mac: as it was. Only a Mac can be a Mac: with the switch off, a real PC is still a computer with no
    # finished video, so there the four Mac cases cannot exist. On a PC we check instead that the real thing (no
    # switch) gives the very pages the switch gave above, so everything checked above holds for a real PC too.
    import platform
    if platform.system() != "Darwin":
        print("SKIP  the four 'a Mac' cases: this computer is not a Mac (they run on a Mac)")
        case("a real PC (no switch) is a computer with no finished video", mac["pc"] is True)
        case("a real PC (no switch): the chooser and the three watch steps are exactly what the switch gives",
             all(mac[k] == pc[k] for k in ("chooser", "broll", "photos", "bts")), [k for k in ("chooser", "broll", "photos", "bts") if mac[k] != pc[k]])
    else:
        case("a Mac (no switch): finished videos can be made", mac["pc"] is False)
        case("a Mac: the chooser has no PC line", "class='pcnote'" not in mac["chooser"] and "kBrollPc" not in mac["chooser"] and mac["card"] not in mac["chooser"])
        m = mac["broll"]
        case("a Mac: her sentence, whole (Save my video, no CapCut needed)", "<p class='say' id='pvSayBroll'>" + mac["hers"] + "</p>" in m and "pvPcNote" not in m)
        sv, mk = button(m, "pvSaveVid"), button(m, "pvMake")
        case("a Mac: Save my video is the main button and shown; Make this one in CapCut the plain one",
             sv == "<button class='btn main' id='pvSaveVid' type='button'>" and mk == "<button class='btn' id='pvMake' type='button'>", (sv, mk))


    # --- the instructions say the same gap
    part = (PARTS / "on-a-pc.md").read_text(encoding="utf-8")
    case("parts/on-a-pc.md names the gap in the page's own words", pc["gap"] in part)
    case("parts/on-a-pc.md says the page tells them up front (the card's line and the watch step)",
         pc["card"] in part and "Make this one in CapCut is the main button" in part, "")
    reel = (ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "SKILL.md").read_text(encoding="utf-8")
    arr = (PARTS / "arrange.md").read_text(encoding="utf-8")
    told = "On a PC the page says so before they press anything (Nicole, Nov 23)"
    case("the reel skill and parts/arrange.md say the page tells a PC before any press, and no longer 'the button says'",
         told in reel and told in arr and "On a PC the button says" not in reel + arr)
    new = (PARTS / "photos-in.md").read_text(encoding="utf-8")
    case("parts/photos-in.md: a taken name is asked for in the box, --name from the chat, and the name is theirs to choose",
         "**A name that is already taken (Nicole, Nov 23).**" in new and "--name \"<their name>\"" in new and "**Use this name**" in new
         and "Never pick the new name for them" in new and "kit.py start --folder ... --name" not in new)
    print()
    n = len(RESULTS)
    print("%d of %d passed." % (sum(RESULTS), n))
    try:
        import shutil
        shutil.rmtree(str(work), ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
