#!/usr/bin/env python3
"""Several reels from one shoot (Nicole's handoff v25, section 2): the reel page's "Your reels" bar and the talking
reel page's "Your talking reels" bar, the records underneath, and the chat's commands.

    python3 tests/reels_check.py                 everything (the pages in a hidden Chrome)
    python3 tests/reels_check.py --no-chrome     the checks that need no browser
    python3 tests/guard.py 3000 python3 tests/reels_check.py     as it is run: under the memory guard

What it holds:
  the list itself   reels.py by itself: a record with no list is one reel and is not changed by looking; a new
                    reel, another opened, a rename; her default names; what is refused; a record changed by hand
  her words         every line of the two bars against her v25 pages and server (when her handoff is here)
  the reel page     by request: every reel fully separate (photos, order, Longer and Quicker, song, footage,
                    style, vibe, notes, clips and which are selected, the Assistant's picks), a new reel blank on
                    "I'll drag them in myself", nothing of one reel ever written into another (a page a step
                    behind), safe to press twice, the refusals, the chat's commands (kit.py picks, footage.py
                    moments, reel_page.py show / reels), a reel made noted as its reel's
  the talking reel  the same by request, and no new or other reel while a video is being turned into a script
  as before         a shoot with one reel: its records are byte for byte what the code before this stage wrote
                    (compared with that code out of git, when git has it)
  the pages         both bars in a hidden Chrome: her words, + Start a new reel, the drop-down, Rename with Save,
                    Cancel, Enter and Escape, a change saved first, names as text, a phone's width

Nothing here touches the real ~/.studio, a real kit, CapCut or a visible window: a scratch home, pretend kits,
the pretend transcriber, a pretend CapCut folder under the scratch home. Python 3.9, standard library only.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import talking_page_check as t  # noqa: E402   (its Setup: a scratch home, pretend kits, the page server)

SCRIPTS = t.SCRIPTS
PORT = 9860
KIT = "2026-09-23 Zoë & the 'boys' 🌊" if t.WINDOWS else "2026-09-23 Zoë <b>& the 'boys' 🌊"
TALK_KIT = "2026-09-24 Talk"
OLD_KIT = "2026-09-25 As before"
BEFORE = "b5af248"            # the commit before this stage: what a shoot with one reel is compared with
PAGE = "abcdefgh12"


def her_v25():
    for base in (ROOT, ROOT.parent / "hf-tools"):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v25-*")):
            f = h / "Carousel designer and reel picker"
            if (f / "pages" / "reel-maker.html").is_file():
                return f
    return None


def run(s, script, *args, env=None):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, encoding="utf-8",
                       errors="replace", env=dict(s.env, **(env or {})), timeout=240)
    return r.returncode, (r.stdout + r.stderr)


def reel_rec(s, kit):
    try:
        return json.loads((s.kit(kit) / ".kit" / "reel-page.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def reel_bytes(s, kit):
    try:
        return (s.kit(kit) / ".kit" / "reel-page.json").read_bytes()
    except OSError:
        return b""


def reel_state(s, kit):
    return s.http("GET", "/reel-state" + s.q(kit))[1]


def save(s, kit, saved, reel=None, base=None, page=PAGE):
    st = reel_state(s, kit)
    body = {"kit": kit, "stamp": st["stamp"], "base": st["rev"] if base is None else base, "page": page, "saved": saved}
    if reel:
        body["reel"] = reel
    return s.post("/reel-save", body)


def ver(s, kit, **ask):
    return s.post("/reel-version", dict(ask, kit=kit))


def tver(s, kit, **ask):
    return s.post("/talking-version", dict(ask, kit=kit))


def picks(*toks):
    return [{"n": int(re.match(r"\d+", x).group()), "h": x[-1] if x[-1] in "+-" else ""} for x in toks]


# ---------- the list by itself ----------

def run_list():
    sys.path.insert(0, str(SCRIPTS))
    import reels
    live = lambda rec: ("saved", "moments")      # noqa: E731
    fresh = lambda rec: {"saved": {"new": True}, "moments": []}      # noqa: E731
    rec = {"v": 1, "rev": 4, "saved": {"picks": [1]}, "made": [{"project": "x"}]}
    before = json.dumps(rec)
    case("a record with no list is one reel, by her first name", reels.info(rec, "Reel 1") == {"versions": [{"id": "v1", "name": "Reel 1"}], "current": "v1"})
    case("...and looking at it changes nothing in it", json.dumps(rec) == before and not reels.several(rec))
    case("opening the reel that is open changes nothing (no list is written)", reels.switch(rec, "v1", live, "Reel 1") is False and json.dumps(rec) == before)
    nid = reels.new(rec, live, fresh, "Reel 1", "Reel")
    case("a new reel is v2, \"Reel 2\" (hers), and is the one being worked on", nid == "v2" and reels.info(rec, "Reel 1") ==
         {"versions": [{"id": "v1", "name": "Reel 1"}, {"id": "v2", "name": "Reel 2"}], "current": "v2"}, rec)
    case("the reel they were on waits whole in its entry; the new one's fields are at the top (her shape)",
         rec["versions"][0]["data"] == {"saved": {"picks": [1]}} and rec["saved"] == {"new": True} and rec["moments"] == [] and "data" not in rec["versions"][1], rec)
    case("what is the shoot's stays at the top, untouched", rec["rev"] == 4 and rec["made"] == [{"project": "x"}])
    with reels.turned(rec, "v1", live, "Reel 1"):
        inside = (rec["current"], json.loads(json.dumps(rec["saved"])))
        rec["saved"]["picks"] = [1, 2]
    case("a command that names another reel reads it as if open, and leaves the open one open",
         inside == ("v1", {"picks": [1]}) and rec["current"] == "v2" and rec["saved"] == {"new": True} and rec["versions"][0]["data"]["saved"] == {"picks": [1, 2]}, rec)
    case("...and what it changed is kept in that reel", reels.data_of(rec, "v1", live, "Reel 1") == {"saved": {"picks": [1, 2]}})
    reels.switch(rec, "v1", live, "Reel 1")
    case("opening the first again brings its fields back to the top and puts the other away",
         rec["current"] == "v1" and rec["saved"] == {"picks": [1, 2]} and "moments" not in rec and rec["versions"][1]["data"] == {"saved": {"new": True}, "moments": []}, rec)
    reels.rename(rec, "v2", "Reel 3", "Reel 1")
    n3 = reels.new(rec, live, fresh, "Reel 1", "Reel")
    case("a new reel's name is the next number that is free (hers): Reel 3 is taken, so Reel 4",
         n3 == "v3" and reels.name_of(rec, "v3", "Reel 1") == "Reel 4", reels.listed(rec, "Reel 1"))

    def wrong(fn):
        snap = json.dumps(rec)
        try:
            fn()
        except reels.Wrong as e:
            return str(e), json.dumps(rec) == snap
        return None, json.dumps(rec) == snap
    case("a reel that isn't there: her line, nothing changed", wrong(lambda: reels.op(rec, {"op": "switch", "id": "v9"}, live, fresh, "Reel 1", "Reel")) == ("That reel isn't there anymore.", True))
    case("a rename with no name: her line, nothing changed", wrong(lambda: reels.op(rec, {"op": "rename", "id": "v1", "name": "   "}, live, fresh, "Reel 1", "Reel")) == ("Give the reel a name.", True))
    case("a name another reel has (whatever the capitals): ours, nothing changed",
         wrong(lambda: reels.op(rec, {"op": "rename", "id": "v1", "name": "reel 4"}, live, fresh, "Reel 1", "Reel")) == (reels.NAME_TAKEN, True))
    for bad in ({"op": "delete", "id": "v1"}, {"op": "new", "id": "v2"}, {"op": "switch", "id": "../x"}, {"op": "rename", "id": "v1", "name": 7},
                {"op": "switch", "id": "v1", "extra": 1}, {"op": "switch", "id": "v1", "name": "x"}, "new", {"op": "new", "name": ["x"]}):
        got = wrong(lambda b=bad: reels.op(rec, b, live, fresh, "Reel 1", "Reel"))
        if got != ("", True):
            case("an ask that is not one of hers is refused and changes nothing: %r" % (bad,), False, got)
            break
    else:
        case("an ask that is not one of hers (another op, an id with a new reel, a name that is not text...) is refused and changes nothing", True)
    case("a name is one line of plain text, 40 letters at the most (her box's length)",
         reels.clean_name("  Kitchen\n &\tcup​cakes  ") == "Kitchen & cup cakes" and len(reels.clean_name("x" * 90)) == 40 and reels.clean_name(None) == "")
    case("the same name again changes nothing", reels.rename(rec, "v1", "Reel 1", "Reel 1") is False)
    case("the chat finds a reel by its whole name, a part that fits one, or its id",
         [reels.find(rec, w, "Reel 1")[0] for w in ("reel 4", "REEL 1", "3", "v3")] == ["v3", "v1", "v2", "v3"], reels.listed(rec, "Reel 1"))
    case("words that fit more than one, or none, name nothing and list the reels",
         reels.find(rec, "reel", "Reel 1")[0] is None and "more than one reel" in reels.find(rec, "reel", "Reel 1")[1]
         and reels.find(rec, "kitchen", "Reel 1")[0] is None and '"Reel 1", "Reel 3", "Reel 4"' in reels.find(rec, "kitchen", "Reel 1")[1])
    odd = {"v": 1, "versions": [None, {"id": "v1", "name": "A"}, {"id": "x", "name": "B"}, {"id": "v1", "name": "twice"}, {"id": "v2", "name": ""}, 7], "current": "v7", "saved": {}}
    case("a list changed by hand is read for what makes sense, and the open reel is one that is there",
         reels.info(odd, "Reel 1") == {"versions": [{"id": "v1", "name": "A"}], "current": "v1"})
    sneaky = {"versions": [{"id": "v1", "name": "A"}, {"id": "v2", "name": "B", "data": {"saved": {"mine": True}, "rev": 999, "made": ["no"], "current": "v9"}}], "current": "v1", "rev": 3, "made": []}
    reels.switch(sneaky, "v2", live, "Reel 1")
    case("a reel's own fields only come up: a \"data\" changed by hand can't write over the shoot's counter or list",
         sneaky["rev"] == 3 and sneaky["made"] == [] and sneaky["current"] == "v2" and sneaky["saved"] == {"mine": True}, sneaky)
    many = {"saved": {}}
    for _k in range(reels.MOST - 1):
        reels.new(many, live, fresh, "Reel 1", "Reel")
    case("a shoot keeps at most %d reels (ours: nothing can be removed), said in plain words" % reels.MOST,
         len(reels.listed(many, "Reel 1")) == reels.MOST and wrong_many(reels, many, live, fresh) == reels.TOO_MANY)


def wrong_many(reels, rec, live, fresh):
    try:
        reels.new(rec, live, fresh, "Reel 1", "Reel")
    except reels.Wrong as e:
        return str(e)
    return None


# ---------- her words ----------

def run_words(s):
    import reel_page as rp
    tp = s.tp
    hers = her_v25()
    case("the reel page's bar has its own table of her words, the talking page's the same with its three lines",
         rp.REELS_WORDS["reels_label"] == "Your reels" and tp.REELS_WORDS["reels_label"] == "Your talking reels"
         and tp.REELS_WORDS["reels_save"] == rp.REELS_WORDS["reels_save"] == "Save")
    case("no page word says Claude, and none has a long dash",
         not [v for v in list(rp.REELS_WORDS.values()) + list(tp.REELS_WORDS.values()) + [rp.OUR_WORDS["reels_taken"], rp.OUR_WORDS["reels_most"], s.TR.STILL_MAKING]
              if "Claude" in v or "—" in v or "–" in v])
    if hers is None:
        t.skip("the two bars' words against her v25 pages: her handoff (reference-private) isn't on this computer")
        return
    page = (hers / "pages" / "reel-maker.html").read_text(encoding="utf-8")
    talk = (hers / "pages" / "talking-reel.html").read_text(encoding="utf-8")
    server = (hers / "server.py").read_text(encoding="utf-8")
    flat = lambda x: x.replace("\\'", "'")      # noqa: E731
    bad = [k for k, v in rp.REELS_WORDS.items() if v not in flat(page) and v not in server]
    case("every word of the reel page's bar (%d) is in her v25 reel page or server, word for word" % len(rp.REELS_WORDS), not bad, bad)
    case("the talking page's two it-didn't-go-through lines are that page's own (her talking page shows its own post's words)",
         "reels_reach" not in tp.REELS_WORDS and tp.page_words()["reels_reach"] == tp.page_words()["cant_reach"] and tp.page_words()["reels_failed"] == tp.page_words()["didnt_work"])
    bad = [k for k, v in tp.REELS_WORDS.items() if v not in flat(talk) and v not in server]
    case("every word of the talking page's bar (%d) is in her v25 talking page or server, word for word" % len(tp.REELS_WORDS), not bad, bad)
    # hers in ours: every piece of wording in her bar's markup and its script
    block = re.search(r'<div class="reels" id="reels">(.*?)</div>', page, re.S).group(1)
    her_bits = [x.strip() for x in re.findall(r">([^<>]+)<", block) if x.strip()] + re.findall(r'aria-label="([^"]+)"', block)
    her_bits += ["Saving this reel and starting a new one…", "Opening that reel…", "I can't reach the page right now. Check the photo drive is plugged in.",
                 "That didn't work.", "Give the reel a name.", "That reel isn't there anymore."]
    case("every line her reel page's bar can show is one of ours, whole", not [x for x in her_bits if x not in rp.REELS_WORDS.values()],
         [x for x in her_bits if x not in rp.REELS_WORDS.values()])
    tblock = re.search(r'<div class="reels" id="reels">(.*?)</div>', talk, re.S).group(1)
    t_bits = [x.strip() for x in re.findall(r">([^<>]+)<", tblock) if x.strip()] + re.findall(r'aria-label="([^"]+)"', tblock)
    t_bits += ["I'm still turning your video into a script. Give it a minute, then try again."]
    case("every line her talking page's bar can show is one of ours, whole", not [x for x in t_bits if x not in tp.REELS_WORDS.values()],
         [x for x in t_bits if x not in tp.REELS_WORDS.values()])
    case("her default names and her first names are hers (Reel 1, Reel 2...; Talking reel 1...)",
         'REEL_FIRST, TALK_FIRST = "Reel 1", "Talking reel 1"' in server and rp.REEL_FIRST == "Reel 1" and s.TR.TALK_FIRST == "Talking reel 1"
         and '"Reel")' in server and '"Talking reel")' in server and rp.REEL_WORD == "Reel" and s.TR.TALK_WORD == "Talking reel")
    her_css = [ln.strip() for ln in page.splitlines() if ln.strip().startswith(".reels")]
    ours = rp.REELS_CSS.replace(";max-width:100%}", "}")
    case("her style rules for the bar are ours, each as she wrote it (ours adds only that a box never runs off a phone)",
         len(her_css) == 10 and all(ln in ours for ln in her_css), [ln for ln in her_css if ln not in ours][:2])
    her_tcss = [ln.strip() for ln in talk.splitlines() if ln.strip().startswith(".reels")]
    import talking_css
    ours_t = talking_css.REELS_CSS.replace(";max-width:100%}", "}")
    case("...and the talking page's", len(her_tcss) == 10 and all(ln in ours_t for ln in her_tcss), [ln for ln in her_tcss if ln not in ours_t][:2])


# ---------- the reel page, by request ----------

def add_footage(s, kit):
    """Two header-only videos in the kit's Footage folder (tests/pc_video.py builds them byte by byte)."""
    import pc_video as pv
    fd = s.kit(kit) / "Footage"
    fd.mkdir(exist_ok=True)
    pv.write(fd, "one.mov", pv.FTYP, pv.box(b"mdat", pv.DATA), pv.moov(pv.vtrak(), pv.atrak()))
    pv.write(fd, "two.mov", pv.FTYP, pv.box(b"mdat", pv.DATA), pv.moov(pv.vtrak(), pv.atrak()))


def moments_file(s, name, ms):
    f = s.work / name
    f.write_text(json.dumps({"moments": ms}, ensure_ascii=False), encoding="utf-8")
    return str(f)


NO_AV = {"ASSISTANT_NO_AVFOUNDATION": "1"}       # no still is ever taken from a pretend video


def run_reel(s):
    import reel_page as rp
    k = s.kit(KIT)
    st = reel_state(s, KIT)
    case("a shoot with one reel: the page is told it has one, \"Reel 1\", and no record is written by looking",
         st["versions"] == [{"id": "v1", "name": "Reel 1", "kind": None}] and st["current"] == "v1" and reel_rec(s, KIT) is None, (st.get("versions"), reel_rec(s, KIT)))
    code, j = save(s, KIT, {"picks": picks("1", "2+", "3-"), "mine": True, "mine_picks": picks("1", "2+", "3-"), "vibe": "calm", "footage": False,
                            "style": "reveal", "ask": "the laughing ones", "feel": "fun"}, reel="v1")
    case("a save that says which reel it is for (the page's own) is taken", code == 200 and j["ok"], j)
    rec = reel_rec(s, KIT)
    case("...and a shoot with one reel still has no list in its record", "versions" not in rec and "current" not in rec, sorted(rec))
    # the footage look, while there is one reel
    add_footage(s, KIT)
    code, out = run(s, "footage.py", "moments", KIT, "--file", moments_file(s, "m1.json", [
        {"video": "one.mov", "start": 0.5, "end": 4.0, "label": "Laughing"}, {"video": "two.mov", "start": 1, "end": 4.5, "label": "Walking"}]), env=NO_AV)
    rec = reel_rec(s, KIT)
    found1 = [m["id"] for m in rec.get("moments_found") or []]
    case("footage.py moments saves the clips to the reel and keeps every clip found for the shoot (hers: moments_found)",
         code == 0 and [m["label"] for m in rec["moments"]] == ["Laughing", "Walking"] and found1 == [m["id"] for m in rec["moments"]]
         and "This shoot has" not in out, (code, out[-300:]))
    m_a, m_b = found1
    code, j = s.post("/reel-moment", {"kit": KIT, "do": "update", "id": m_a, "end": 5.0, "reel": "v1"})
    case("they make a clip longer in the first reel", code == 200 and [m for m in j["moments"] if m["id"] == m_a][0]["end"] == 5.0, j)
    code, j = save(s, KIT, {"sel": {"reveal": [m_b]}, "footage": True}, reel="v1")
    v1_saved = reel_rec(s, KIT)["saved"]
    v1_moments = reel_rec(s, KIT)["moments"]
    kit_before = (k / ".kit" / "kit.json").read_bytes()
    # ---- a new reel
    b0 = reel_bytes(s, KIT)
    code, j = ver(s, KIT, op="new", id="v2")
    case("an ask that is not hers (a new reel with an id) is refused in plain words and nothing is written",
         code == 400 and j == {"ok": False, "words": rp.NOT_UNDERSTOOD} and reel_bytes(s, KIT) == b0, j)
    rev0 = reel_rec(s, KIT)["rev"]
    code, j = ver(s, KIT, op="new")
    rec = reel_rec(s, KIT)
    case("+ Start a new reel: the answer names both reels and the new one is being worked on (hers)",
         code == 200 and j["ok"] and j["versions"] == [{"id": "v1", "name": "Reel 1"}, {"id": "v2", "name": "Reel 2"}] and j["current"] == "v2", j)
    case("the record is her shape: versions [{id, name, data}], current, the open reel's fields at the top",
         [v["id"] for v in rec["versions"]] == ["v1", "v2"] and rec["current"] == "v2" and "data" in rec["versions"][0] and "data" not in rec["versions"][1]
         and isinstance(rec.get("saved"), dict), sorted(rec))
    case("the reel they were on is kept exactly as it was (its choices, its clips and their lengths)",
         rec["versions"][0]["data"]["saved"] == v1_saved and rec["versions"][0]["data"]["moments"] == v1_moments)
    sv = rec["saved"]
    case("a new reel starts blank on \"I'll drag them in myself\": nothing in it, no song, footage not chosen (hers)",
         sv["picks"] == [] and sv["mine"] is True and sv["mine_picks"] == [] and sv["song"] is None and sv["footage"] is None
         and sv["vibe"] == "beat" and sv["style"] == "first" and sv["ask"] == "" and sv["feel"] == "" and sv["sel"] == {}, sv)
    case("...with every clip found for the shoot, all as found (the length they set in the other reel is that reel's)",
         [m["id"] for m in rec["moments"]] == found1 and all(m["keep"] is True and "set" not in m for m in rec["moments"])
         and [m["end"] for m in rec["moments"]] == [4.0, 4.5], rec["moments"])
    case("the record's counter moved on, so a page that has not seen this can't save into the new reel", rec["rev"] == rev0 + 1 and "from" not in rec)
    case("the version before is kept whole beside the record", (k / ".kit" / "reel-page.prev.json").read_bytes() == b0)
    st = reel_state(s, KIT)
    case("the page's state is the new reel: no pick of the assistant's, nothing saved in it, both reels listed",
         st["current"] == "v2" and st["claude"] == [] and st["saved"]["picks"] == [] and len(st["versions"]) == 2 and len(st["moments"]) == 2, (st["claude"], st["saved"]))
    case("the kit's own record was not written by starting a reel (the page server never writes kit.json)", (k / ".kit" / "kit.json").read_bytes() == kit_before)
    # ---- nothing of one reel is ever written into another
    b1 = reel_bytes(s, KIT)
    code, j = save(s, KIT, {"picks": picks("7", "8"), "vibe": "build"}, reel="v1")
    case("a page still showing Reel 1 can't save into Reel 2: told there is something newer, given it, nothing written",
         code == 409 and j.get("why") == "newer" and j["state"]["current"] == "v2" and reel_bytes(s, KIT) == b1, (code, j.get("why")))
    code, j = s.post("/reel-moment", {"kit": KIT, "do": "remove", "id": m_a, "reel": "v1"})
    case("...nor take a clip out of it", code == 409 and reel_bytes(s, KIT) == b1, (code, j))
    code, j = s.post("/reel-make", {"kit": KIT, "stamp": st["stamp"], "picks": picks("1", "2"), "song": "", "vibe": "beat", "test": True, "reel": "v1"})
    case("...nor make a reel from it as if it were the other", code == 409 and j.get("why") == "newer" and "job" not in j and reel_bytes(s, KIT) == b1, (code, j.get("why")))
    for bad in ("v0", "x", 2, "v12345", ""):
        code, j = save(s, KIT, {"vibe": "calm"}, reel=bad) if bad != "" else s.post("/reel-save", {"kit": KIT, "stamp": st["stamp"], "base": st["rev"], "page": PAGE, "saved": {"vibe": "calm"}, "reel": ""})
        if code != 400 or reel_bytes(s, KIT) != b1:
            case("a reel named in a way no page would is refused: %r" % (bad,), False, (code, j))
            break
    else:
        case("a reel named in a way no page would (not v<number>) is refused, nothing written", True)
    # ---- every reel fully separate
    code, j = save(s, KIT, {"picks": picks("5", "6+"), "mine": True, "vibe": "build", "footage": True, "style": "bookends", "ask": "only the kitchen", "sel": {"bookends": [m_a]}}, reel="v2")
    code2, j2 = s.post("/reel-moment", {"kit": KIT, "do": "remove", "id": m_b, "reel": "v2"})
    rec = reel_rec(s, KIT)
    case("changes in the new reel are the new reel's", code == 200 and code2 == 200 and rec["saved"]["vibe"] == "build" and [m["id"] for m in rec["moments"]] == [m_a], (j, j2))
    case("...and the first reel is as it was: its order, Longer and Quicker, vibe, style, notes, clips, which are selected",
         rec["versions"][0]["data"]["saved"] == v1_saved and rec["versions"][0]["data"]["moments"] == v1_moments)
    case("a clip taken out of one reel is still in every clip found for the shoot", [m["id"] for m in rec["moments_found"]] == found1)
    # ---- the assistant's picks, per reel
    code, out = run(s, "kit.py", "picks", KIT, "--reel", "4,3+,2-")
    rec = reel_rec(s, KIT)
    case("kit.py picks --reel goes to the reel being worked on (Reel 2), and says which reel",
         code == 0 and rec.get("claude") == picks("4", "3+", "2-") and 'for "Reel 2", one of this shoot\'s 2 reels' in out, out)
    case("...the first reel's pick in kit.json is untouched", (k / ".kit" / "kit.json").read_bytes() == kit_before)
    st = reel_state(s, KIT)
    case("the page's state has that reel's pick, and the record's counter moved so an open page takes it", st["claude"] == picks("4", "3+", "2-") and st["rev"] == rec["rev"])
    b2 = reel_bytes(s, KIT)
    code, out = run(s, "kit.py", "picks", KIT, "--reel", "4,3+,2-")
    case("the same pick again writes nothing", code == 0 and reel_bytes(s, KIT) == b2, out)
    code, out = run(s, "kit.py", "picks", KIT, "--reel", "4,3,99")
    case("a number that is not on the sheet stops it, nothing changed anywhere", code == 1 and "no photo numbered 99" in out and reel_bytes(s, KIT) == b2
         and (k / ".kit" / "kit.json").read_bytes() == kit_before, out)
    code, out = run(s, "kit.py", "picks", KIT, "--reel", "6,5", "--carousel", "1,2,3")
    rec = reel_rec(s, KIT)
    kj = json.loads((k / ".kit" / "kit.json").read_text(encoding="utf-8"))
    case("a new pick for Reel 2 keeps the one it replaces (the last 12, as the kit keeps reel_earlier); a carousel pick beside it goes to the kit",
         code == 0 and rec["claude"] == picks("6", "5") and rec["claude_earlier"] == ["4,3+,2-"] and kj["picks"]["carousel"] == [1, 2, 3]
         and kj["picks"].get("reel") == json.loads(kit_before)["picks"].get("reel"), (out, rec.get("claude_earlier")))
    code, out = run(s, "kit.py", "picks", KIT, "--reel", "1,2,3+", "--for-reel", "reel 1")
    kj = json.loads((k / ".kit" / "kit.json").read_text(encoding="utf-8"))
    case("--for-reel names another reel: the first reel's pick goes to kit.json, where it always was, and Reel 2's is untouched",
         code == 0 and kj["picks"]["reel"] == [1, 2, 3] and kj["reel_marks"] == {"3": "+"} and reel_rec(s, KIT)["claude"] == picks("6", "5")
         and 'for "Reel 1"' in out, out)
    code, out = run(s, "kit.py", "picks", KIT, "--reel", "1", "--for-reel", "nope")
    case("--for-reel with a name no reel has stops and lists the reels", code == 1 and 'no reel called "nope"' in out and '"Reel 1", "Reel 2"' in out, out)
    code, out = run(s, "kit.py", "picks", KIT, "--carousel", "1", "--for-reel", "Reel 2")
    case("--for-reel without --reel is refused", code == 1 and "goes with --reel" in out, out)
    st2 = reel_state(s, KIT)
    code, out = run(s, "reel_page.py", "show", KIT, "--reel", "Reel 1")
    case("reel_page.py show --reel reads another reel without opening it",
         code == 0 and "What follows is \"Reel 1\"" in out and "Claude's order: 1,2,3+" in out and "The order Make my reel uses: 1,2+,3-" in out
         and reel_state(s, KIT)["current"] == "v2" and reel_state(s, KIT)["rev"] == st2["rev"], out)
    code, out = run(s, "reel_page.py", "show", KIT)
    case("...and with no --reel shows the one being worked on, saying which", code == 0 and "What follows is \"Reel 2\"" in out and "Claude's order: 6,5" in out, out)
    # ---- the footage look goes to the reel being worked on
    code, out = run(s, "footage.py", "moments", KIT, "--file", moments_file(s, "m2.json", [{"video": "two.mov", "start": 2, "end": 5.5, "label": "A look back"}]), env=NO_AV)
    rec = reel_rec(s, KIT)
    case("footage.py moments goes to the reel being worked on, and says which reel", code == 0 and [m["label"] for m in rec["moments"]] == ["A look back"]
         and 'This is for "Reel 2", the one open on the reel page.' in out, out[-400:])
    case("...the other reel's clips are untouched", rec["versions"][0]["data"]["moments"] == v1_moments)
    case("...and every clip found for the shoot now has the new one too (hers: the earlier ones, then these)",
         [m["label"] for m in rec["moments_found"]] == ["Laughing", "Walking", "A look back"], [m["label"] for m in rec["moments_found"]])
    code, out = run(s, "footage.py", "moments", KIT, "--reel", "Reel 1", "--file", moments_file(s, "m3.json", [{"video": "one.mov", "start": 1.5, "end": 5.0, "label": "For the first"}]), env=NO_AV)
    rec = reel_rec(s, KIT)
    case("footage.py moments --reel saves to another reel and leaves the open one alone",
         code == 0 and [m["label"] for m in rec["versions"][0]["data"]["moments"]] == ["For the first"] and [m["label"] for m in rec["moments"]] == ["A look back"]
         and rec["current"] == "v2" and "not the one open on the reel page" in out, out[-300:])
    # ---- a third reel starts with every clip found
    code, j = ver(s, KIT, op="new", name="  Kitchen &\n<b>cupcakes</b>  ")
    rec = reel_rec(s, KIT)
    case("a new reel may be given a name (cleaned to one line of text)", code == 200 and j["versions"][2] == {"id": "v3", "name": "Kitchen & <b>cupcakes</b>"} and j["current"] == "v3", j)
    case("...and starts with every clip found for the shoot so far",
         [m["label"] for m in rec["moments"]] == ["Laughing", "Walking", "A look back", "For the first"] and rec.get("claude") is None and rec["saved"]["picks"] == [], rec["moments"])
    case("Reel 2 went into its entry with its own pick and the picks before it", rec["versions"][1]["data"]["claude"] == picks("6", "5") and rec["versions"][1]["data"]["claude_earlier"] == ["4,3+,2-"])
    # ---- switch, rename, twice
    code, j = ver(s, KIT, op="switch", id="v1")
    st = reel_state(s, KIT)
    case("opening Reel 1 again shows it exactly as it was left: the order with Longer and Quicker, the vibe, the notes",
         code == 200 and j["current"] == "v1" and st["saved"]["picks"] == picks("1", "2+", "3-") and st["saved"]["vibe"] == "calm" and st["saved"]["ask"] == "the laughing ones"
         and st["claude"] == picks("1", "2", "3+"), (j, st["saved"]))
    b3 = reel_bytes(s, KIT)
    code, j = ver(s, KIT, op="switch", id="v1")
    case("opening the reel that is already open writes nothing (safe to press twice)", code == 200 and j["current"] == "v1" and reel_bytes(s, KIT) == b3)
    code, j = ver(s, KIT, op="switch", id="v9")
    case("a reel that isn't there: her line, nothing written", code == 400 and j == {"ok": False, "words": "That reel isn't there anymore."} and reel_bytes(s, KIT) == b3, j)
    code, j = ver(s, KIT, op="rename", id="v2", name="   ")
    case("a rename with no name: her line, nothing written", code == 400 and j["words"] == "Give the reel a name." and reel_bytes(s, KIT) == b3, j)
    code, j = ver(s, KIT, op="rename", id="v2", name="reel 1")
    case("a name another reel of the shoot has: ours, nothing written", code == 400 and j["words"] == rp.OUR_WORDS["reels_taken"] and reel_bytes(s, KIT) == b3, j)
    code, j = ver(s, KIT, op="rename", id="v2", name="White backdrop")
    case("Rename: the answer has the new name; the reel being worked on does not change", code == 200 and j["versions"][1]["name"] == "White backdrop" and j["current"] == "v1", j)
    b4 = reel_bytes(s, KIT)
    code, j = ver(s, KIT, op="rename", id="v2", name="White backdrop")
    case("the same name again writes nothing", code == 200 and reel_bytes(s, KIT) == b4)
    # ---- refusals of the route itself
    for what, kw in (("another website (Origin)", {"headers": {"Origin": "https://example.com"}}),
                     ("a cross-site press", {"headers": {"Sec-Fetch-Site": "cross-site", "Origin": "http://127.0.0.1:%d" % s.port}}),
                     ("another host's name", {"headers": {"Host": "evil.example"}})):
        code, j = s.post("/reel-version", {"kit": KIT, "op": "new"}, **kw)
        if code != 403 or reel_bytes(s, KIT) != b4:
            case("the route is refused to " + what, False, (code, j))
            break
    else:
        case("the route is the page's own: another website, a cross-site press and another host's name are refused, nothing written", True)
    code, j = ver(s, "2026-01-01 Not here", op="new")
    case("a shoot that isn't in Your Content: the page's can't-find line", code == 404 and j["words"] == rp.CANT_FIND, j)
    code, j, raw, _h = s.http("POST", "/reel-version", raw_body=b"x" * 70000, headers={"Content-Type": "application/json"})
    case("a body far too big is refused", code in (400, 413) and reel_bytes(s, KIT) == b4, code)
    case("no answer of the route has a path in it", str(k) not in json.dumps(ver(s, KIT, op="switch", id="v1")) and "Your Content" not in json.dumps(reel_state(s, KIT)["versions"]))
    # ---- the chat's reels command (since v27 each reel's kind is named after it: left out here, tests/reel_v27_page_check.py has it)
    nokind = lambda o: re.sub(r" \((behind the scenes|just photos|B-roll)\)", "", o)   # noqa: E731
    code, out = run(s, "reel_page.py", "reels", KIT)
    case("reel_page.py reels lists the shoot's reels and marks the one open on the page", code == 0 and '3 reels: "Reel 1" (the one open on the page), "White backdrop", "Kitchen & <b>cupcakes</b>"' in nokind(out), out)
    code, out = run(s, "reel_page.py", "reels", KIT, "--open", "white")
    case("...--open works on another (a part of its name is enough)", code == 0 and reel_rec(s, KIT)["current"] == "v2" and '"White backdrop" (the one open on the page)' in nokind(out), out)
    code, out = run(s, "reel_page.py", "reels", KIT, "--rename", "kitchen", "--to", "Kitchen")
    case("...--rename --to renames one", code == 0 and reel_state(s, KIT)["versions"][2]["name"] == "Kitchen", out)
    code, out = run(s, "reel_page.py", "reels", KIT, "--open", "nope")
    case("...a name no reel has stops in plain words", code == 1 and 'no reel called "nope"' in out and reel_rec(s, KIT)["current"] == "v2", out)
    # ---- a re-made numbered list: every reel finds its photos again
    sheet = k / ".kit" / "sheet.json"
    rows = json.loads(sheet.read_text(encoding="utf-8"))
    n = len(rows["photos"])
    for x in rows["photos"]:
        x["n"] = n + 1 - x["n"]                  # the same photos, numbered the other way round
    rows["photos"].sort(key=lambda x: x["n"])
    sheet.write_text(json.dumps(rows), encoding="utf-8")
    st = reel_state(s, KIT)
    rec = reel_rec(s, KIT)
    flip = lambda lst: [{"n": n + 1 - x["n"], "h": x["h"]} for x in lst]      # noqa: E731
    case("the numbered list re-made: the open reel's pick and the put-away reels' orders all find the same photos again",
         st["claude"] == flip(picks("6", "5")) and rec["versions"][0]["data"]["saved"]["picks"] == flip(picks("1", "2+", "3-"))
         and rec["claude_earlier"] == ["%d,%d+,%d-" % (n - 3, n - 2, n - 1)], (st["claude"], rec["versions"][0]["data"]["saved"]["picks"], rec.get("claude_earlier")))


def run_older(s):
    """A record from before "moments_found": a new reel starts with every clip any reel still has that is not theirs."""
    import reel_page as rp
    old = {"v": 1, "moments": [{"id": "u1-aaaaaa", "video": "a.mov", "start": 1.0, "end": 5.0, "by": "you", "keep": True},
                               {"id": "m1-bbbbbb", "video": "a.mov", "start": 2.0, "end": 6.5, "keep": False, "set": True, "label": "x"}],
           "versions": [{"id": "v1", "name": "Reel 1"}, {"id": "v2", "name": "Reel 2", "data": {"moments": [
               {"id": "m1-bbbbbb", "video": "a.mov", "start": 2.0, "end": 5.5, "keep": True}, {"id": "m2-cccccc", "video": "b.mov", "start": 0.0, "end": 3.5, "keep": True}]}}], "current": "v1"}
    fresh = rp.reel_fresh(old)
    case("an older record (no list of clips found): a new reel starts with every clip any reel still has that is not their own, each once",
         [m["id"] for m in fresh["moments"]] == ["m1-bbbbbb", "m2-cccccc"], fresh["moments"])
    case("...each selected and not marked as a length they set (that mark is the other reel's)", all(m["keep"] is True and "set" not in m for m in fresh["moments"]), fresh["moments"])
    case("...and what the new reel is handed is a copy: the other reels' clips are not changed by it", old["moments"][1]["keep"] is False and old["moments"][1].get("set") is True)


def run_made(s):
    """A reel made is noted as its reel's; each reel's next mix is its own. A Mac only (the pretend CapCut folder)."""
    import reel_page as rp
    kit = "2026-09-26 Made"
    k = s.make_kit(kit, photos=8)
    store = s.home / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    store.mkdir(parents=True, exist_ok=True)

    def make(reel=None, toks=("1", "2", "3", "4")):
        st = reel_state(s, kit)
        body = {"kit": kit, "stamp": st["stamp"], "picks": picks(*toks), "song": "", "vibe": "beat", "test": False}
        if reel:
            body["reel"] = reel
        code, j = s.post("/reel-make", body)
        if code != 200:
            return code, j
        end = time.time() + 120
        while time.time() < end:
            job = s.http("GET", "/reel-job" + s.q(kit))[1].get("job") or {}
            if job.get("state") in ("done", "problem"):
                return 200, job
            time.sleep(0.3)
        return 200, job
    code, job = make()
    rec = reel_rec(s, kit)
    case("one reel: a reel is made, and its note in the record is exactly as before (no reel named in it)",
         code == 200 and job.get("state") == "done" and len(rec["made"]) == 1 and "version" not in rec["made"][0] and "versions" not in rec, (job, rec.get("made")))
    job_file = json.loads((k / ".kit" / "reel-job.json").read_text(encoding="utf-8"))
    case("...and the job is written as before (no reel named in it)", "reel" not in job_file["ask"], job_file["ask"])
    ver(s, kit, op="new")
    code, job = make("v2")
    rec = reel_rec(s, kit)
    case("several reels: the reel made from Reel 2 is noted as Reel 2's (hers: made entries carry the version)",
         code == 200 and job.get("state") == "done" and [m.get("version") for m in rec["made"]] == [None, "v2"] and rp.made_for(rec["made"][0]) == "v1", (job, rec.get("made")))
    names = sorted(p.name for p in store.iterdir() if p.is_dir())
    case("in CapCut the projects are named for the shoot, the second \"... reel 2\", whichever reel it came from",
         names == ["2026-09-26 Made reel", "2026-09-26 Made reel 2"], names)
    case("the job says which reel it is for, so the reel is made from that reel's clips also if they open another meanwhile",
         json.loads((k / ".kit" / "reel-job.json").read_text(encoding="utf-8"))["ask"].get("reel") == "v2")
    made = rec["made"]
    case("the same photos in another reel start at that reel's own first mix (the first reel's makes don't count for it); the same reel again is its next mix",
         rp.mix_number(made, "1,2,3,4", "beat", None, "v2") == 1 and rp.mix_number(made, "1,2,3,4", "beat", None, "v1") == 1
         and rp.mix_number(made[:1], "1,2,3,4", "beat", None, "v2") == 0 and rp.mix_number(made, "1,2,3,4", "calm", None, "v2") == 0, made)
    code, out = run(s, "reel_page.py", "show", kit, "--reel", "Reel 1")
    code2, out2 = run(s, "reel_page.py", "show", kit)
    case("reel_page.py show counts each reel's own makes", "the newest \"2026-09-26 Made reel\"" in out and "the newest \"2026-09-26 Made reel 2\"" in out2, (out[-200:], out2[-200:]))


# ---------- the talking reel, by request ----------

def run_talking(s):
    TR = s.TR
    k = s.kit(TALK_KIT)
    key1 = s.add_talk(k, t.V1)
    key2 = s.add_talk(k, t.V2)
    TR.put_words(k, t.V1, key1, t.WORDS1, info={"dur": 3.0, "w": 320, "h": 240})
    s.cut(TALK_KIT, [[0, 1]])
    st = s.state(TALK_KIT)
    case("a shoot with one talking reel: the page is told it has one, \"Talking reel 1\"", st["versions"] == [{"id": "v1", "name": "Talking reel 1"}] and st["current"] == "v1", st.get("versions"))
    rec = s.rec(TALK_KIT)
    case("...and its record has no list", "versions" not in rec and "current" not in rec, sorted(rec))
    b0 = s.rec_bytes(TALK_KIT)
    v1_before = {kk: vv for kk, vv in rec.items() if kk not in TR.TALK_KEEP}
    code, j = tver(s, TALK_KIT, op="new")
    rec = s.rec(TALK_KIT)
    case("+ Start a new talking reel: both are named and the new one is being worked on (hers)",
         code == 200 and j["ok"] and j["versions"] == [{"id": "v1", "name": "Talking reel 1"}, {"id": "v2", "name": "Talking reel 2"}] and j["current"] == "v2", j)
    case("the one they were on is kept exactly as it was: every key but the list and the counter is that reel's (hers)",
         rec["versions"][0]["data"] == v1_before and not [kk for kk in v1_before if kk in rec and kk not in ("captions", "photo_mode")], sorted(rec))
    case("the words of a video are never put away with a reel (they are the video's, kept beside)", not [x for x in TR.WORD_FIELDS if x in rec["versions"][0]["data"] or x in rec])
    case("a new talking reel starts at step 1: no video chosen, captions on (hers)", rec.get("captions") is True and rec.get("photo_mode") == "" and "video" not in rec and "cut" not in rec, rec)
    case("the counter moved on and the version before is kept beside", rec["rev"] == json.loads(b0)["rev"] + 1 and (k / ".kit" / "talking.prev.json").read_bytes() == b0)
    st = s.state(TALK_KIT)
    case("the page's state is the new reel: no script, nothing cut, both reels listed", st["current"] == "v2" and not st["rec"]["words"] and st["rec"]["cut"] == [] and len(st["versions"]) == 2, st["rec"].get("video"))
    # a page still on the first reel
    b_new = s.rec_bytes(TALK_KIT)
    code, j, raw, _h = s.http("POST", "/talking-save", {"kit": TALK_KIT, "base": json.loads(b0)["rev"], "page": PAGE, "saved": {"captions": False}})
    case("a page still showing the first reel can't save into the new one: told there is something newer, given it, nothing written",
         code == 409 and j and j.get("why") == "newer" and j["state"]["current"] == "v2" and s.rec_bytes(TALK_KIT) == b_new, (code, raw[:200]))
    code, j, raw, _h = s.http("POST", "/talking-save", {"kit": TALK_KIT, "base": json.loads(b0)["rev"], "page": PAGE, "saved": {"cut": [[2, 3]]}})
    case("...and its cuts (word numbers of the other reel's script) are refused outright", code in (400, 409) and s.rec_bytes(TALK_KIT) == b_new, (code, raw[:200]))
    # the chat's commands
    try:
        s.cut(TALK_KIT, [[2, 3]])
        got = None
    except TR.Stop as e:
        got = str(e)
    case("the chat's cut acts on the reel being worked on: the new one has no script yet, so it stops", got == TR.NO_SCRIPT, got)
    n, secs = TR.save_cut(k, {"cut": [[4, 5]], "why": ["a restart"]}, False, "v1")
    rec = s.rec(TALK_KIT)
    case("cut --reel acts on another reel and leaves the open one open and untouched",
         n == 1 and rec["versions"][0]["data"]["cut"] == [[4, 5]] and rec["current"] == "v2" and "cut" not in rec and "video" not in rec, rec["versions"][0]["data"].get("cut"))
    code, out = run(s, "talking_rec.py", "status", TALK_KIT, "--reel", "reel 1")
    case("talking_rec.py status --reel says which reel it is about, and reads that one",
         code == 0 and 'This is "Talking reel 1", not the one open on the page.' in out and "Video: " + t.V1 in out and "1 cuts (your cut)" in out, out)
    code, out = run(s, "talking_rec.py", "status", TALK_KIT)
    case("...and with no --reel, the one open on the page", code == 0 and 'This is "Talking reel 2", the one open on the page.' in out and "No video has been turned into a script yet" in out, out)
    code, out = run(s, "talking_rec.py", "show", TALK_KIT, "--reel", "nope")
    case("a name no talking reel has stops in plain words", code == 2 and 'no talking reel called "nope"' in out and '"Talking reel 1", "Talking reel 2"' in out, out)
    cuts = s.work / "cuts.json"
    cuts.write_text(json.dumps({"cut": [[0, 0]], "why": ["the warm-up"]}), encoding="utf-8")
    code, out = run(s, "talking_rec.py", "cut", TALK_KIT, "--file", str(cuts), "--reel", "Talking reel 1")
    case("talking_rec.py cut --reel from the command line: saved in that reel, and it says the page shows it when they open that reel",
         code == 0 and "Saved: 1 cuts." in out and "when they open that reel" in out and s.rec(TALK_KIT)["versions"][0]["data"]["cut"] == [[0, 0]], out)
    # the second reel takes the other video; both keep their own
    TR.put_words(k, t.V2, key2, t.WORDS2, info={"dur": 3.0, "w": 320, "h": 240})
    s.cut(TALK_KIT, [[1, 2]])
    code, j = tver(s, TALK_KIT, op="switch", id="v1")
    st = s.state(TALK_KIT)
    case("opening the first again: its own video, its own script and its own cuts",
         code == 200 and st["current"] == "v1" and st["rec"]["video"] == t.V1 and len(st["rec"]["words"]) == len(t.WORDS1) and st["rec"]["cut"] == [[0, 0]], (st["rec"]["video"], st["rec"]["cut"]))
    rec = s.rec(TALK_KIT)
    case("...and the second waits with its own", rec["versions"][1]["data"]["video"] == t.V2 and rec["versions"][1]["data"]["cut"] == [[1, 2]])
    b1 = s.rec_bytes(TALK_KIT)
    code, j = tver(s, TALK_KIT, op="switch", id="v1")
    case("opening the one that is open writes nothing", code == 200 and s.rec_bytes(TALK_KIT) == b1)
    for ask, words in (({"op": "switch", "id": "v9"}, "That reel isn't there anymore."), ({"op": "rename", "id": "v1", "name": ""}, "Give the reel a name."),
                       ({"op": "rename", "id": "v1", "name": "talking REEL 2"}, TR.reels.NAME_TAKEN), ({"op": "bogus"}, s.tp.NOT_UNDERSTOOD),
                       ({"op": "switch", "id": "v1", "x": 1}, s.tp.NOT_UNDERSTOOD)):
        code, j = tver(s, TALK_KIT, **ask)
        if code != 400 or j.get("words") != words or s.rec_bytes(TALK_KIT) != b1:
            case("refused in plain words, nothing written: %r" % (ask,), False, (code, j))
            break
    else:
        case("a reel that isn't there, no name, a name that is taken, an ask that is not hers: each refused in its words, nothing written", True)
    code, j = s.post("/talking-version", {"kit": TALK_KIT, "op": "new"}, headers={"Origin": "https://example.com"})
    case("the route is the page's own (another website is refused)", code == 403 and s.rec_bytes(TALK_KIT) == b1, code)
    # while a video is being turned into a script
    key3 = s.add_talk(k, "third.mp4")
    s.says(words=t.WORDS2, sleep=3.0)
    code, j = s.post("/talking-start", {"kit": TALK_KIT, "video": key3})
    case("Edit my video is pressed (the pretend transcriber takes three seconds)", code == 200 and j.get("ok"), j)
    code, j = tver(s, TALK_KIT, op="new")
    code2, j2 = tver(s, TALK_KIT, op="switch", id="v2")
    case("while a video is being turned into a script: no new talking reel and no other one, in her words",
         (code, j.get("words")) == (409, "I'm still turning your video into a script. Give it a minute, then try again.") and (code2, j2.get("words")) == (code, j.get("words"))
         and s.rec(TALK_KIT)["current"] == "v1" and len(s.rec(TALK_KIT)["versions"]) == 2, (j, j2))
    code, j = tver(s, TALK_KIT, op="rename", id="v1", name="Sit-down")
    case("...Rename still works meanwhile (hers)", code == 200 and j["versions"][0]["name"] == "Sit-down", j)
    st = s.settled(TALK_KIT, 60)
    rec = s.rec(TALK_KIT)
    case("the script lands in the reel it was started on, and the other reel is as it was",
         st and st["current"] == "v1" and st["rec"]["status"] == "ready" and st["rec"]["video"] == "third.mp4" and rec["versions"][1]["data"]["cut"] == [[1, 2]]
         and rec["versions"][1]["data"]["video"] == t.V2, st and (st["rec"].get("status"), st["rec"].get("video")))
    code, j = tver(s, TALK_KIT, op="switch", id="v2")
    case("once it is done, the other reel opens", code == 200 and j["current"] == "v2", j)
    s.says(words=t.WORDS2)


# ---------- as before: one reel, byte for byte ----------

CHILD = r"""
import json, os, sys, time
time.time = lambda: 1794000000.0
time.strftime = lambda *a: "2026-11-14 10:00:00"
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[2])
import arrange, reel_page as rp, talking_rec as TR
kit = arrange.kit_by_name(sys.argv[3])
st = rp.state(kit)
P = lambda *ns: [{"n": n, "h": ""} for n in ns]
print(rp.save_from_page({"kit": kit.name, "stamp": st["stamp"], "base": 0, "page": "abcdefgh12", "saved": {"picks": P(1, 2, 3), "mine": True, "vibe": "calm", "footage": False, "ask": "x"}})[0])
print(rp.save_from_page({"kit": kit.name, "stamp": st["stamp"], "base": 1, "page": "abcdefgh12", "saved": {"picks": P(3, 2), "song": ""}})[0])
words = [{"w": w, "start": 0.1 + i * 0.2, "end": 0.25 + i * 0.2, "conf": 0.9} for i, w in enumerate("so um hello there this is my shoot".split())]
TR.put_words(kit, "talk.mp4", "0123456789ab", words, info={"dur": 3.0})
print(TR.save_cut(kit, {"cut": [[0, 1]], "why": ["warm-up"]})[0])
print(TR.save_from_page(kit, {"base": TR._rev(TR._slim(kit)), "page": "abcdefgh12", "saved": {"cut": [[0, 2]]}})[0])
"""


def run_before(s):
    old = s.work / "before"
    old.mkdir()
    try:
        tar = subprocess.run(["git", "-C", str(ROOT), "archive", BEFORE, "plugins/the-engine/skills"], capture_output=True, timeout=120)
        ok = tar.returncode == 0 and tar.stdout
        if ok:
            ok = subprocess.run(["tar", "-x", "-C", str(old)], input=tar.stdout, capture_output=True, timeout=120).returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    if not ok:
        t.skip("a shoot with one reel, byte for byte against the code before this stage: git has no %s here" % BEFORE)
        return
    child = s.work / "child.py"
    child.write_text(CHILD, encoding="utf-8")
    got = {}
    name = OLD_KIT
    k = s.make_kit(name, photos=5)
    (k / "Talking").mkdir()
    (k / "Talking" / "talk.mp4").write_bytes(b"not a video, only a name")
    files = ("reel-page.json", "reel-page.prev.json", "talking.json", "talking.prev.json", "talking-words.json")
    for which, base in (("before", old / "plugins" / "the-engine" / "skills"), ("now", t.SKILLS)):
        r = subprocess.run([sys.executable, str(child), str(base / "studio-manager" / "scripts"), str(base / "assistant-make-a-reel" / "scripts"), name],
                           capture_output=True, encoding="utf-8", errors="replace", env=s.env, timeout=120)
        got[which] = (r.stdout.split(), {f: (k / ".kit" / f).read_bytes() if (k / ".kit" / f).is_file() else None for f in files}, r.stderr[-400:])
        aside = s.work / ("records of " + which)       # this test's own pretend records, set aside for the second run
        aside.mkdir()
        for f in list((k / ".kit").iterdir()):
            if f.name.startswith(("reel-page", "talking")):
                shutil.move(str(f), str(aside / f.name))
    case("the same saves ran on the code before this stage and on this code", got["before"][0] == got["now"][0] == ["200", "200", "1", "200"], (got["before"][0], got["now"][0], got["now"][2]))
    for f in files:
        case("a shoot with one reel: %s is byte for byte what the code before this stage wrote" % f,
             got["now"][1][f] is not None and got["now"][1][f] == got["before"][1][f])


# ---------- the pages ----------

def names_on(c):
    return c.js("Array.from(document.querySelectorAll('#verSel option')).map(function(o){ return o.textContent + (o.selected ? '*' : ''); })")


def run_reel_page(c, s):
    import reel_page as rp
    kit = "2026-09-27 Page <i>reel &amp; more" if not t.WINDOWS else "2026-09-27 Page reel"
    s.make_kit(kit, photos=8)
    c.open(s.url("/reel.html" + s.q(kit) + "&kind=photos"))     # v27: the bar is on a kind's page (the chooser has none)
    c.wait_for("window.Reel && window.Reel.state()", 20)
    bar = c.js("(function(){ var b = document.getElementById('reels'); var h = document.querySelector('header.head'); return {inHead: h.contains(b), afterLede: b.previousElementSibling.className, "
               "label: b.querySelector('label').textContent, forSel: b.querySelector('label').htmlFor, aria: document.getElementById('verSel').getAttribute('aria-label'), "
               "newB: document.getElementById('verNew').textContent, ren: document.getElementById('verRen').textContent, boxHidden: document.getElementById('verRenBox').hidden, "
               "max: document.getElementById('verName').maxLength, nameAria: document.getElementById('verName').getAttribute('aria-label'), "
               "save: document.getElementById('verSave').textContent, cancel: document.getElementById('verCancel').textContent}; })()")
    case("the reel page has her bar under the title: Your reels, a drop-down, + Start a new reel, Rename",
         bar == {"inHead": True, "afterLede": "lede", "label": "Your reels", "forSel": "verSel", "aria": "Which reel you're working on", "newB": "+ Start a new reel",
                 "ren": "Rename", "boxHidden": True, "max": 40, "nameAria": "The reel's name", "save": "Save", "cancel": "Cancel"}, bar)
    case("a shoot with one reel shows it as Reel 1", names_on(c) == ["Reel 1*"], names_on(c))
    # a change, then + Start a new reel at once: the change is saved first
    c.click("#all .pick")
    c.wait_for("document.querySelectorAll('#reel .tile').length === 1", 5)
    c.js("window.__sameLoad = true")
    c.click("#verNew")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v2'", 20)
    case("the page loads afresh on the new reel (hers: a reload, so nothing of the other reel is left on the screen)", c.js("window.__sameLoad === undefined"))
    rec = reel_rec(s, kit)
    case("+ Start a new reel saves the reel they were on exactly as it is first (a change made a moment before is in it)",
         len(rec["versions"][0]["data"]["saved"]["picks"]) == 1 and rec["current"] == "v2", rec["versions"][0].get("data"))
    case("the page reloads on the new reel: Reel 2 is picked in the drop-down, nothing in the reel, I'll drag them in myself",
         names_on(c) == ["Reel 1", "Reel 2*"] and c.count("#reel .tile") == 0 and c.js("window.Reel.state().saved.mine === true"), names_on(c))
    # Rename
    c.click("#verRen")
    state = c.js("[document.getElementById('verRenBox').hidden, document.getElementById('verRen').hidden, document.getElementById('verSel').hidden, "
                 "document.activeElement.id, document.getElementById('verName').value, document.getElementById('verNew').hidden]")
    case("Rename: the name turns into a box with Save and Cancel, the name in it and picked (hers)", state == [False, True, True, "verName", "Reel 2", False], state)
    c.key("Mod+A")
    c.type_text("Nope")
    c.key("Escape")
    case("Escape cancels: the box goes, the name is as it was, nothing saved",
         c.js("document.getElementById('verRenBox').hidden && !document.getElementById('verSel').hidden") and names_on(c) == ["Reel 1", "Reel 2*"]
         and reel_rec(s, kit)["versions"][1]["name"] == "Reel 2", names_on(c))
    c.click("#verRen")
    c.key("Mod+A")
    c.type_text("Reel 1")
    c.key("Enter")
    c.wait_for("document.getElementById('verMsg').textContent !== ''", 5)
    case("a name another reel has: the line says so and the box stays open for another try",
         c.text("#verMsg") == rp.OUR_WORDS["reels_taken"] and c.js("!document.getElementById('verRenBox').hidden") and reel_rec(s, kit)["versions"][1]["name"] == "Reel 2", c.text("#verMsg"))
    c.key("Mod+A")
    c.type_text("Kitchen <b>&</b> 'cupcakes' 🧁")
    c.key("Enter")
    c.wait_for("document.getElementById('verRenBox').hidden", 5)
    case("Enter saves: the drop-down shows the new name, as text (a tag in it is only letters)",
         names_on(c) == ["Reel 1", "Kitchen <b>&</b> 'cupcakes' 🧁*"] and c.count("#verSel b") == 0 and c.text("#verMsg") == ""
         and reel_rec(s, kit)["versions"][1]["name"] == "Kitchen <b>&</b> 'cupcakes' 🧁", names_on(c))
    c.click("#verRen")
    c.click("#verCancel")
    case("Cancel closes the box", c.js("document.getElementById('verRenBox').hidden && !document.getElementById('verRen').hidden"))
    c.click("#verRen")
    c.key("Mod+A")
    c.type_text("Second")
    c.click("#verSave")
    c.wait_for("document.getElementById('verRenBox').hidden", 5)
    case("Save saves", names_on(c) == ["Reel 1", "Second*"], names_on(c))
    # a save after a rename is not refused as stale
    c.click("#all .pick")
    c.wait_for("document.querySelectorAll('#reel .tile').length === 1", 5)
    chrome_drive.wait_until(lambda: len((reel_rec(s, kit).get("saved") or {}).get("picks") or []) == 1, 8, what="the save after a rename")
    case("after a rename the page's next change still saves, into the reel it shows", len(reel_rec(s, kit)["saved"]["picks"]) == 1 and c.text("#notice") == "", c.text("#notice"))
    # the drop-down
    c.js("window.__sameLoad = true")
    c.set_value("#verSel", "v1")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v1'", 20)
    case("...on a fresh load of the page (hers)", c.js("window.__sameLoad === undefined"))
    case("choosing another reel in the drop-down opens it: its own photo is there, the other reel's is not",
         names_on(c) == ["Reel 1*", "Second"] and c.count("#reel .tile") == 1 and reel_rec(s, kit)["current"] == "v1", names_on(c))
    # another window opened another reel: this page follows, and never saves into it
    ver(s, kit, op="switch", id="v2")
    c.js("window.Reel.followNow()")
    c.wait_for("window.Reel.state().current === 'v2'", 10)
    case("when another window opens another reel, this page shows that reel (the drop-down too)", names_on(c) == ["Reel 1", "Second*"], names_on(c))
    case("no fault on the page", not c.page_errors(), c.page_errors())
    c.phone(375, 800)
    c.reload()
    c.wait_for("window.Reel && window.Reel.state()", 20)
    wide = c.js("[document.documentElement.scrollWidth, document.getElementById('reels').getBoundingClientRect().right]")
    case("at a phone's width the bar wraps and nothing makes the page scroll sideways", wide[0] <= 375 and wide[1] <= 375, wide)
    c.click("#verRen")
    wide = c.js("[document.documentElement.scrollWidth, document.getElementById('verName').getBoundingClientRect().right, document.getElementById('verCancel').getBoundingClientRect().right]")
    case("...also with the Rename box open", wide[0] <= 375 and wide[1] <= 375 and wide[2] <= 375, wide)
    c.desktop()


def run_talking_page(c, s):
    kit = "2026-09-28 Page talk"
    k = s.make_kit(kit, photos=6)
    key = s.add_talk(k, t.V2)
    s.TR.put_words(k, t.V2, key, t.WORDS2, info={"dur": 3.0, "w": 320, "h": 240})
    t.open_page(c, s, kit)
    bar = c.js("(function(){ var b = document.getElementById('reels'); return {inHead: document.querySelector('header.head').contains(b), label: b.querySelector('label').textContent, "
               "aria: document.getElementById('verSel').getAttribute('aria-label'), newB: document.getElementById('verNew').textContent, ren: document.getElementById('verRen').textContent}; })()")
    case("the talking reel page has the same bar, in her words: Your talking reels, + Start a new talking reel, Rename",
         bar == {"inHead": True, "label": "Your talking reels", "aria": "Which talking reel you're working on", "newB": "+ Start a new talking reel", "ren": "Rename"}, bar)
    case("one talking reel shows as Talking reel 1", names_on(c) == ["Talking reel 1*"], names_on(c))
    seen = c.js(t.ALL_TEXT) if hasattr(t, "ALL_TEXT") else None
    c.click("#verNew")
    c.wait_for("window.Talk && window.Talk.loaded && window.Talk.ST.current === 'v2'", 20)
    case("+ Start a new talking reel: the page reloads on it, at step 1 with no script (hers)",
         names_on(c) == ["Talking reel 1", "Talking reel 2*"] and c.js("!window.Talk.ready() && document.getElementById('editStep').hidden"), names_on(c))
    # typing a name never plays the video or deletes a clip: the box keeps its keys
    c.click("#verRen")
    c.key("Mod+A")
    c.type_text("B roll talk")
    c.key("Enter")
    c.wait_for("document.getElementById('verRenBox').hidden", 5)
    case("Rename with Enter", names_on(c) == ["Talking reel 1", "B roll talk*"] and s.rec(kit)["versions"][1]["name"] == "B roll talk", names_on(c))
    c.set_value("#verSel", "v1")
    c.wait_for("window.Talk && window.Talk.loaded && window.Talk.ST.current === 'v1'", 20)
    case("the drop-down opens the first again, with its script", c.js("window.Talk.ready()") and names_on(c) == ["Talking reel 1*", "B roll talk"], names_on(c))
    c.click("#verRen")
    c.type_text(" ")
    c.key("Backspace")
    c.key("Escape")
    case("a space or Backspace typed in the name box is the box's own (the video does not play, no clip is cut), and Escape cancels",
         c.js("document.getElementById('vid').paused && document.getElementById('verRenBox').hidden") and s.rec(kit).get("cut") in (None, []), s.rec(kit).get("cut"))
    # refused while a script is being made: her line shows in the bar
    key3 = s.add_talk(k, "third.mp4")
    s.says(words=t.WORDS2, sleep=3.0)
    code, j = s.post("/talking-start", {"kit": kit, "video": key3})
    c.click("#verNew")
    c.wait_for("document.getElementById('verMsg').textContent.indexOf('still turning') > 0", 8)
    case("while a video is being turned into a script, + Start a new talking reel says her line and nothing changes",
         c.text("#verMsg") == "I'm still turning your video into a script. Give it a minute, then try again." and len(s.rec(kit)["versions"]) == 2 and names_on(c)[0].endswith("*"), c.text("#verMsg"))
    s.settled(kit, 60)
    s.says(words=t.WORDS2)
    case("no fault on the page", not [e for e in c.page_errors() if "favicon" not in e], c.page_errors())
    c.phone(375, 800)
    c.reload()
    c.wait_for("window.Talk && window.Talk.loaded", 20)
    wide = c.js("[document.documentElement.scrollWidth, document.getElementById('reels').getBoundingClientRect().right]")
    case("at a phone's width the talking page's bar wraps inside the page", wide[1] <= 375, wide)
    c.desktop()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-chrome", action="store_true", help="the checks that need no browser only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792, 8799) for p in range(a.port, a.port + 10)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    real_before = t.real_listing()
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else None
    if base:
        base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="reels-check-", dir=str(base) if base else ("/private/tmp" if t.MAC else None))).resolve()
    s = t.Setup(work, a.port)
    s.env["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"       # no folder window, no picker, no CapCut, whatever a test presses
    s.env["STUDIO_CARD_FOR_TESTS"] = "none"
    os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    s.make()
    try:
        group("the list of reels, by itself (reels.py)", run_list)
        s.make_kit(KIT, photos=9)
        kj = s.kit(KIT) / ".kit" / "kit.json"
        d = json.loads(kj.read_text(encoding="utf-8"))
        d["picks"] = {"reel": [1, 2, 3]}
        kj.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        s.make_kit(TALK_KIT, photos=6)
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
        group("her words, both bars", run_words, s)
        group("the reel page by request: every reel fully separate", run_reel, s)
        group("an older record's clips for a new reel", run_older, s)
        if t.MAC:
            group("a reel made is its reel's (a pretend CapCut folder)", run_made, s)
        else:
            t.skip("a reel made is its reel's: the pretend CapCut folder is a Mac's")
        group("the talking reel by request", run_talking, s)
        group("a shoot with one reel is as before, byte for byte", run_before, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            t.skip("the two bars on the pages: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work / "chrome"), size=(1280, 1000)) as c:
                group("the reel page's bar", run_reel_page, c, s)
                group("the talking reel page's bar", run_talking_page, c, s)
    finally:
        s.stop()
        chrome_drive.stop_all()
        case("the real Assistant folder on this computer is exactly as it was", t.real_listing() == real_before)
        if not keep and not [1 for _n, ok in chrome_drive._results if not ok]:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return t.summary()


if __name__ == "__main__":
    sys.exit(main())
