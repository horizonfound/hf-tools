#!/usr/bin/env python3
"""The post kit and the posting queue with several reels, and captions optional (Nicole's v25, sections 6 and 7),
checked by request and on the real pages in a HIDDEN Chrome.

    python3 tests/kit_reels_queue_check.py [--port 9940] [--work <a folder to keep the run in>] [--no-chrome]
                                           [--only words|optional|reels|video|names|cover|chat|reminders|guard|page|posting]

What it does, on pretend Assistants it makes itself in a throwaway folder (the words page check's own: one kit, a
few tiny pictures; nothing of a client's, nothing of the real ~/.studio, no drive, never the real Calendar):
  * her words: every new line on the kit page and in the cover picker against her own v25 page and her own
    posting queue changes, when her handoff is on this computer (it is never in the repository; else SKIP);
  * captions are optional: Add to my queue works once the piece is made, caption or not; without a caption the
    button carries the mark that makes the page ask first; a piece that is not made is still refused;
  * a shoot with more than one reel: a preview of each reel by name on the Reel card (up to 7 photos, "In CapCut:
    <newest project>" or "Not made yet", "No photos picked yet."), each reel's place in the queue in step 3, in
    her words, and the reels Add to my queue may offer (made, not in the queue yet);
  * each reel its own piece: the first keeps the kit's existing reel piece (no id renamed, its date and place
    kept), every other gets one of its own under the kit's own collision-proof name; pieces carry which reel and
    its name; a reel renamed is shown by its new name; a shoot with ONE reel is in the queue with the very same
    fields as before;
  * the queue's names: "<shoot> reel · <reel name>" on the page, "<shoot> reel (<reel name>)" in the chat;
  * the reel cover picker's photos: that reel's own, in the order it plays, whichever reel is open;
  * the chat: ready "<piece>" --reel "<name>" (a reel that isn't made, or a name that fits none, changes
    nothing), and a reel found by its name;
  * reminders (a pretend calendar only): each reel's piece has its own event, and one with no caption says so in
    its notes;
  * who may press and what a press may say: a reel id that isn't one, another page's Origin, a field too many;
  * the kit page itself (when there is a Chrome): the caption question in a box on the page (never a browser
    pop-up), its two buttons, Escape and the x; "Which reel goes in your queue?" with a button per reel (a name
    with a tag in it shown as letters), skipped when one is left; a phone's width;
  * the posting page itself: "<shoot> reel · <name>" in the list and the panel's heading; "From your reel, in the
    order it plays" numbered, "+ Use a different photo" opening "Any other photo from the shoot" (open already
    when the cover is one of those); a carousel's panel as it was.

No folder is ever opened and CapCut is never started. The page servers and the hidden Chrome are this test's own
and are stopped at the end. Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9,
standard library only, a Mac or a PC.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import words_page_check as wpc  # noqa: E402  (its pretend Assistant: one kit, the page server, words.py from the chat)
import posting_panel_check as ppc  # noqa: E402  (the panel's own helpers)
import posting_reminders_page_check as rpc  # noqa: E402  (the pretend calendar's helpers)

KIT, SHORT, PROJECT, HOOKS = wpc.KIT, wpc.SHORT, wpc.PROJECT, wpc.HOOKS
KQ = quote(KIT, safe="")
PAGE = "/content/%s/Post%%20kit.html" % KQ
SECOND = "White <b>Backdrop"                 # a reel's name is theirs: a tag in it must only ever show as letters
# The same name where it is part of a FILE's name: a PC cannot make a file with < or > in its name, so there it is the
# name the reel page itself gives a saved video (those characters become a space); a Mac keeps the tag, to show as letters.
SECOND_FILE = "White b Backdrop" if wpc.WINDOWS else SECOND
THIRD = "Zoë's 🌊 third"
P1, P2, P3 = PROJECT, SHORT + " reel 4", SHORT + " reel 5"
LOCK_TAIL = " first. Then add it to your posting queue to see it in your feed and give it a date."
READY = "It's ready! Add it to your posting queue so you can see it in your feed and give it a date."
READY_NOCAP = "Add it to your posting queue so you can see it in your feed and give it a date. Its caption can come later, or not at all."
NOCAP_TITLE = "You haven't written a caption for your %s yet"
NOCAP_TEXT = "That's okay. Do you still want to add it to your posting queue, or write your caption first?"
WHICH_TITLE = "Which reel goes in your queue?"
WHICH_TEXT = "You have more than one reel from this shoot. Pick the one you're adding; each reel gets its own spot in your queue."
FROM_REEL = "From your reel, in the order it plays"
USE_OTHER = "+ Use a different photo"
HIDE_OTHER = "Hide the other photos"
ANY_OTHER = "Any other photo from the shoot"
NO_CAPTION_NOTE = "No caption yet. Write it on your words page in the post kit."
ONLY = None


def skip(line):
    print("SKIP  " + line, flush=True)


def want(name):
    return ONLY is None or ONLY == name


def her(*parts):
    """A file of her newest handoff from v25 on (v25 brought these pages; v27 changed only the bar and the Reels card), or
    None when it is not on this computer."""
    for base in (ROOT, Path("/Users/dustindamron/Projects/hf-tools")):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v2[5-9]-*"), reverse=True):
            f = h.joinpath("Carousel designer and reel picker", *parts)
            if f.is_file():
                return f
    return None


# ---------- a pretend Assistant, and its reels ----------

def fresh(work, name, port, backend="none"):
    s = wpc.Setup(work / name, port)
    s.env.update(STUDIO_NO_WINDOWS_FOR_TESTS="1", STUDIO_CARD_FOR_TESTS="none", REMINDERS_BACKEND=backend)
    s.make()
    return s


def rrec(s):
    f = s.kit / ".kit" / "reel-page.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}      # no record until the reel page is first opened


def wrec(s, rec):
    f = s.kit / ".kit" / "reel-page.json"
    tmp = f.with_name("reel-page.json.test")
    tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(f))


def new_reel(s, name):
    code, out = s.cmd("reel_page.py", "reels", KIT, "--new", "--name", name)
    if code != 0:
        raise RuntimeError("a new reel could not be started: " + out[-300:])


def fields(rec, vid):
    """One reel's own fields in the record, to change: the top of the record for the open reel, its "data" else."""
    if rec.get("current", "v1") == vid or not rec.get("versions"):
        return rec
    v = next(x for x in rec["versions"] if x["id"] == vid)
    return v.setdefault("data", {})


def set_picks(s, vid, ns):
    """Their own order for one reel ("I'll drag them in myself"), as the reel page saves it."""
    rec = rrec(s)
    f = fields(rec, vid)
    order = [{"n": n, "h": ""} for n in ns]
    saved = dict(f.get("saved") or {"song": None, "vibe": "beat", "footage": None, "style": "first", "ask": "", "feel": "", "sel": {}})
    saved.update(mine=True, picks=order, mine_picks=order, updated=time.time())
    f["saved"] = saved
    wrec(s, rec)


def set_made(s, vid, project):
    """A reel made on the reel page: its "made" entry, marked with which reel (as reel_page.py writes it)."""
    rec = rrec(s)
    rec.setdefault("made", []).append({"project": project, "picks": "1,2", "vibe": "beat", "footage": None, "version": vid, "when": time.time()})
    wrec(s, rec)


def set_video(s, vid, name):
    """A B-roll reel saved whole from the reel page (Save my video, Nicole's v27): its "made" entry carries the video's
    file name and no CapCut project (reel_page.py writes it so), and the file is in the shoot's Reels folder."""
    rec = rrec(s)
    rec.setdefault("made", []).append({"video": name, "picks": "", "vibe": "beat", "footage": "broll", "clips": ["u1-aaaaaa"],
                                       "song": "", "song_id": "", "version": vid, "when": time.time(), "variation": 0,
                                       "song_start": None, "seconds": 4.5})
    wrec(s, rec)
    (s.kit / "Reels").mkdir(exist_ok=True)
    (s.kit / "Reels" / name).write_bytes(b"\x00" * 2000)


def video_stem(s):
    """The name reel_page.py itself would give the open reel's saved video (without ".mp4"), asked of it in its own process."""
    ask = ("import sys; from pathlib import Path; sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, sys.argv[2]); "
           "import reel_page as rp; k = Path(sys.argv[1]); sys.stdout.write(rp.video_stem(k, rp.load(k)))")
    r = subprocess.run([sys.executable, "-c", ask, str(s.kit), str(SCRIPTS)], capture_output=True, text=True, encoding="utf-8", env=s.env, cwd=str(SCRIPTS))
    if r.returncode != 0:
        raise RuntimeError("reel_page.video_stem: " + (r.stdout + r.stderr)[-300:])
    return r.stdout


def two_reels(s, second_made=True):
    """Reel 1 (the kit's pick 1,2,3,4; made from the chat: P1) and a second reel with its own order 6,5 (made: P2)."""
    s.reel_made()
    new_reel(s, SECOND)
    set_picks(s, "v2", [6, 5])
    if second_made:
        set_made(s, "v2", P2)


def look(s):
    code, _, raw = s.http("GET", PAGE)
    return code, raw.decode("utf-8")


def box(t, name):
    """The text of one data-box of the kit page, tags taken out."""
    m = re.search(r"<div class='w q[^']*' data-box='%s'>(.*?)</div>(?=</div></a>|<div class='w|</div>\s*</a>)" % name, t, re.S)
    return m.group(1) if m else ""


def text_of(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "\x1f", fragment))


def add_button(t, piece="reel"):
    m = re.search(r"<button class='qbtn' type='button' data-add='%s'([^>]*)>" % piece, t)
    return m.group(1) if m else None


def reel_rows(t):
    m = re.search(r"<ul class='qreels'>(.*?)</ul>", t, re.S)
    return [html.unescape(re.sub(r"<[^>]+>", "", li)) for li in re.findall(r"<li[^>]*>(.*?)</li>", m.group(1), re.S)] if m else []


def previews(t):
    """[(the reel's name, how many photos its strip draws, its +N, its status line)] for each .onereel of the Reel card."""
    out = []
    for m in re.finditer(r"<div class='onereel' data-reel='(v\d+)'><div class='rn'>(.*?)</div>(.*?)(?=<div class='onereel'|<div class='status'><button|<p class='went'>)", t, re.S):
        body = m.group(3)
        more = re.search(r"<span class='more'>(\+\d+)</span>", body)
        st = re.search(r"<div class='status'>(.*?)</div>", body, re.S)
        out.append((m.group(1), html.unescape(m.group(2)), len(re.findall(r"<img ", body)), more.group(1) if more else "",
                    html.unescape(re.sub(r"<[^>]+>", "", st.group(1))) if st else "", "No photos picked yet." in body))
    return out


def reel_pieces(s):
    return {x["id"]: x for x in s.posting().get("pieces", []) if re.search(r"-reel(-v\d+)?$", x.get("id", ""))}


def add(s, piece="reel", **more):
    return s.http("POST", "/words-queue", dict({"kit": KIT, "piece": piece}, **more))[:2]


# ---------- 1. her words ----------

def check_words(s):
    os.environ["STUDIO_HOME"] = str(s.studio)
    sys.path.insert(0, str(SCRIPTS))
    import kit as k
    import posting_queue as pq
    K = k.KIT_WORDS
    case("the kit page's new lines are hers, word for word",
         K["ready_nocap"] == READY_NOCAP and K["nocap_title"] == NOCAP_TITLE.replace("%s", "{piece}") and K["nocap_text"] == NOCAP_TEXT
         and K["nocap_add"] == "Add it to my queue" and K["nocap_write"] == "Write my caption" and K["which_title"] == WHICH_TITLE
         and K["which_text"] == WHICH_TEXT and K["reel_empty"] == "No photos picked yet."
         and (K["r_posted"], K["r_down"], K["r_in"], K["r_made"], K["r_not"]) == ("posted ✓", "down for {day}", "in your posting queue", "made, not in your queue yet", "not made yet"))
    case("the two v24 lines that asked for a caption first are gone (captions are optional now)", "need_both" not in K and "need_caption" not in K
         and "write its caption" not in json.dumps(K).lower())
    case("no line of the page says Claude, and none has an em dash", not any("Claude" in v or "—" in v for v in K.values()))
    src = pq.SCRIPT
    for w in (FROM_REEL, USE_OTHER, HIDE_OTHER, ANY_OTHER, "Photo {n} in your reel"):
        case("the cover picker says her %r" % w, ("'" + w + "'") in src)
    case("the older 'More from the shoot' divider is gone from the picker", "More from the shoot" not in src)
    f = her("pages", "post-kit.html")
    if f is None:
        skip("her words against her own page (v25 or newer): her handoff (reference-private) isn't on this computer")
    else:
        t = html.unescape(f.read_text(encoding="utf-8")).replace("\\'", "'")
        new = ("ready_nocap", "nocap_title", "nocap_text", "nocap_add", "nocap_write", "which_title", "which_text", "reel_empty",
               "r_posted", "r_down", "r_in", "r_made", "r_not")
        bad = [(key, frag) for key in new for frag in re.split(r"\{\w+\}", K[key]) if frag.strip() and frag not in t]
        case("each of those %d lines is in her newest pages/post-kit.html (v25 or later)" % len(new), not bad, bad)
        raw = f.read_text(encoding="utf-8")
        rules = [ln for ln in k.REELS_STYLE.splitlines() if ln.strip()]
        missing = [ln for ln in rules if ln not in raw]
        case("her %d style lines for the reel previews, the list of reels and the question box are in our page as she wrote them" % len(rules),
             len(rules) >= 12 and not missing and k.REELS_STYLE in k.CSS, missing[:3])
        case("her box's markup: a dialog, labelled by its title, with a close button", "role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"nocapTitle\"" in raw
             and "role='dialog' aria-modal='true' aria-labelledby='nocapTitle'" in k.ASK_BOX and "aria-label='Close'" in k.ASK_BOX)
    d = her("plugin-changes", "posting_queue-since-v24.diff")
    if d is None:
        skip("her posting queue changes: her handoff (reference-private) isn't on this computer")
    else:
        t = d.read_text(encoding="utf-8")
        for w in (FROM_REEL, USE_OTHER, HIDE_OTHER, ANY_OTHER, "' in your reel'", "' · '+x.reel_name"):
            case("her posting queue has %r" % w, w in t)
        css = [ln[1:] for ln in t.splitlines() if ln.startswith("+.pick ")]
        case("her four style lines for the picker are in our posting page as she wrote them", len(css) == 4 and all(ln in pq.CSS for ln in css), css)
        case("her chat name for a reel's piece: '<shoot> reel (<reel name>)'", "(f\" ({p['reel_name']})\" if p.get(\"reel_name\") else \"\")" in t
             and pq.piece_name({"shoot_name": "Katie", "kind": "reel", "reel_name": "Fun Maternity"}) == "Katie reel (Fun Maternity)"
             and pq.piece_name({"shoot_name": "Katie", "kind": "reel"}) == "Katie reel"
             and pq.piece_name({"shoot_name": "Katie", "kind": "single", "n": 2}) == "Katie single 2")
    # which reel a piece is, from its name alone
    ids = {"kit:a-reel": "v1", "kit:a-reel-v2": "v2", "kit:a-reel-v12": "v12", "kit:smith-reel-v2-reel": "v1", "kit:a-reel-v0": "v1"}
    got = {i: pq.reel_version({"id": i}) for i in ids}
    case("which reel a piece is, is read from its name: '...-reel' the first, '...-reel-v2' the second", got == ids, got)
    roles = {i: pq.kit_role({"id": i, "kit": "/x/A"}) for i in ("kit:a-reel", "kit:a-reel-v2", "kit:a-carousel", "kit:a-single-3", "kit:a-reel-v0", "kit:a-reel-vx")}
    case("a reel's own piece is a reel; nothing else became one", roles == {"kit:a-reel": "reel", "kit:a-reel-v2": "reel", "kit:a-carousel": "carousel",
                                                                           "kit:a-single-3": "single", "kit:a-reel-v0": "", "kit:a-reel-vx": ""}, roles)


# ---------- 2. captions are optional ----------

def check_optional(s):
    s.start()
    code, t = look(s)
    case("nothing made: 'Make your reel first. ...', locked, for the reel and the carousel", code == 200
         and ("Make your reel" + LOCK_TAIL) in text_of(t) and ("Make your carousel" + LOCK_TAIL) in text_of(t) and add_button(t) is None)
    code, j = add(s)
    case("a reel that isn't made is refused, and nothing is written", code == 409 and j["ok"] is False and not s.posting(), (code, j))
    s.reel_made()
    s.slides_made(3)
    code, t = look(s)
    case("made, no caption: her line 'Add it to your posting queue ... Its caption can come later, or not at all.'",
         text_of(box(t, "queue-reel")).count(READY_NOCAP) == 1 and READY not in text_of(t), text_of(box(t, "queue-reel")))
    case("...the button is live and marked so the page asks first", add_button(t) is not None and "data-nocap='1'" in add_button(t)
         and "data-nocap='1'" in add_button(t, "carousel") and "disabled" not in add_button(t))
    body = t.split("<script", 1)[0]                   # the page itself, before its words and its script
    case("the question box is on the page once, hidden, after the last card (nothing in a card is a link)",
         body.count("id='nocap'") == 1 and "<div class='nocap' id='nocap' hidden" in body and body.index("id='nocap'") > body.rindex("</a>")
         and text_of(body).count(NOCAP_TEXT) == 1, (body.count("id='nocap'"), text_of(body).count(NOCAP_TEXT)))
    case("the page never asks with a browser pop-up", not re.search(r"\b(alert|confirm|prompt)\s*\(", t))
    case("showing the page added nothing", not s.posting())
    code, j = add(s)
    x = s.queue_piece("reel") or {}
    case("Add to my queue with no caption: added, ready to post", code == 200 and j["ok"] and j["queue"]["status"] == "green" and x.get("status") == "green", (code, j))
    case("a shoot with one reel is in the queue with the same fields as ever: no version, no reel name",
         "version" not in x and "reel_name" not in x and x["id"] == "kit:" + re.sub(r"[^a-z0-9]+", "-", KIT.lower()).strip("-")[:40] + "-reel", sorted(x))
    code, j = add(s, "carousel")
    case("a carousel with no caption too", code == 200 and (s.queue_piece("carousel") or {}).get("status") == "green", (code, j))
    code, j = add(s)
    case("added twice: still one reel piece", code == 200 and len(reel_pieces(s)) == 1)
    st = ppc.page_state(s)
    g = next(x for x in st["greens"] if x["role"] == "reel")
    case("the posting page is told no reel name for a shoot with one reel", g.get("reel_name") is None, g)
    code, p, _ = ppc.panel(s, g["id"])
    case("its panel, with no caption: the words row has none to copy (the page says 'No caption yet.')",
         code == 200 and p["words"] == {"piece": "reel", "caption": "", "hook": ""}, p.get("words"))
    # with a caption the page says it's ready and asks nothing
    s2 = s
    s2.words("draft", "reel", {"caption": "MINI SESSIONS are coming to Laguna Beach on December 4th!!!", "hooks": HOOKS})
    p_ = s2.posting()
    for y in p_["pieces"]:
        if y["id"].endswith("-reel"):
            y["status"] = "yellow"
            y.pop("slot", None)
            y.pop("date", None)
    s2.write_posting(p_)
    code, t = look(s2)
    case("with a caption: 'It's ready! ...' and a button that asks nothing", READY in text_of(box(t, "queue-reel")) and add_button(t) is not None
         and "data-nocap" not in add_button(t), text_of(box(t, "queue-reel")))
    s.stop()


# ---------- 3. a shoot with more than one reel ----------

def check_reels(s):
    s.reel_made()
    s.start()
    add(s)                                           # in the queue while the shoot still has one reel
    was = dict(s.queue_piece("reel"))
    two_reels(s, second_made=False)
    code, t = look(s)
    pv = previews(t)
    case("the Reel card shows a preview of each reel by name", [(v, n) for v, n, *_ in pv] == [("v1", "Reel 1"), ("v2", SECOND)], pv)
    case("...the first: its 4 photos and 'In CapCut: <its project>'; the second: its 2 photos and 'Not made yet'",
         len(pv) == 2 and pv[0][2:5] == (4, "", "In CapCut: " + P1) and pv[1][2:5] == (2, "", "Not made yet"), pv)
    case("a reel's name with a tag in it is only ever letters", "<b>Backdrop" not in t and "White &lt;b&gt;Backdrop" in t)
    case("one Open in CapCut under the previews (a reel is made)", t.count("id='capcut'") == 1)
    rows = reel_rows(t)
    case("step 3 lists each reel's place, in her words: 'Reel 1: down for Wed... / in your posting queue', '<second>: not made yet'",
         rows == ["Reel 1: in your posting queue", SECOND + ": not made yet"], rows)
    case("nothing can be added: the button is the pale green '✓ Added to my queue', disabled, and 'See it in my feed' is there",
         add_button(t) is None and "<button class='qbtn done' type='button' disabled>✓ Added to my queue</button>" in t and "See it in my feed" in box(t, "queue-reel"))
    x = s.queue_piece("reel")
    case("the first reel kept the kit's existing piece: the same id, the same place in line", x["id"] == was["id"] and x.get("slot") == was.get("slot")
         and x["status"] == "green" and len(reel_pieces(s)) == 1, (x["id"], was["id"]))
    before = (s.studio / "posting.json").read_bytes()
    code, j = add(s, reel="v2")
    case("a reel that isn't made can't be added (her locked line), nothing written", code == 409 and j["ok"] is False
         and (s.studio / "posting.json").read_bytes() == before, (code, j))
    set_made(s, "v2", P2)
    code, out = s.cmd("posting_queue.py", "add", "--kit", KIT)
    case("the kit added again from the chat: a reel nobody asked to queue gets no piece (hers: only when it goes in)",
         code == 0 and sorted(reel_pieces(s)) == [was["id"]], sorted(reel_pieces(s)))
    code, t = look(s)
    case("the second reel made: 'In CapCut: <its own project>' under its own name, and 'made, not in your queue yet'",
         previews(t)[1][4] == "In CapCut: " + P2 and previews(t)[0][4] == "In CapCut: " + P1
         and reel_rows(t)[1] == SECOND + ": made, not in your queue yet", (previews(t), reel_rows(t)))
    btn = add_button(t) or ""
    offered = json.loads(html.unescape(re.search(r"data-reels='([^']*)'", btn).group(1))) if "data-reels" in btn else None
    case("Add to my queue offers the reels that are made and not in the queue yet: only the second", "data-multi='1'" in btn
         and offered == [{"id": "v2", "name": SECOND}], (btn, offered))
    code, j = add(s, reel="v2")
    pcs = reel_pieces(s)
    v2 = pcs.get(was["id"] + "-v2") or {}
    case("the second reel got a piece of its own, named after the kit's reel piece: '<it>-v2'", code == 200 and sorted(pcs) == [was["id"], was["id"] + "-v2"]
         and v2.get("status") == "green", sorted(pcs))
    case("the pieces carry which reel and its name", (v2.get("version"), v2.get("reel_name")) == ("v2", SECOND)
         and (pcs[was["id"]].get("version"), pcs[was["id"]].get("reel_name")) == ("v1", "Reel 1"), (v2.get("version"), v2.get("reel_name")))
    case("it is this kit's own: the same shoot, the folder it was made from, a reel", v2.get("shoot_id") == was["shoot_id"] and v2.get("kit") == was.get("kit")
         and v2.get("kind") == "reel" and v2.get("shoot_name") == was["shoot_name"])
    case("the first reel's piece was not renamed and kept its day", pcs[was["id"]].get("date") == "" or pcs[was["id"]].get("date") == was.get("date"))
    case("its tile is its own picture (the reel's own first photo), under its own name", isinstance(v2.get("thumb"), str) and v2["thumb"] != pcs[was["id"]].get("thumb")
         and (s.studio / v2["thumb"]).is_file(), v2.get("thumb"))
    code, t = look(s)
    case("both in: the list says so, the button is done", reel_rows(t) == ["Reel 1: in your posting queue", SECOND + ": in your posting queue"]
         and add_button(t) is None, reel_rows(t))
    code, j = add(s, reel="v2")
    case("added twice: still two reel pieces", code == 200 and len(reel_pieces(s)) == 2)
    # a rhythm: each gets a date, and the list says the day
    s.http("POST", "/words-rhythm", {"text": "3 a week"})
    code, t = look(s)
    case("with a rhythm the list says each reel's day: 'down for Wed, Nov 11' and 'down for Fri, Nov 13'",
         reel_rows(t) == ["Reel 1: down for Wed, Nov 11", SECOND + ": down for Fri, Nov 13"], reel_rows(t))
    p = s.posting()
    for y in p["pieces"]:
        if y["id"] == was["id"]:
            y["status"] = "posted"
            y.pop("slot", None)
    s.write_posting(p)
    code, t = look(s)
    case("a reel that went out: 'posted ✓'", reel_rows(t)[0] == "Reel 1: posted ✓", reel_rows(t))
    # a third reel: seven photos and more, and no photos
    new_reel(s, THIRD)
    code, t = look(s)
    case("a new reel with nothing in it: 'No photos picked yet.' and 'Not made yet'", previews(t)[2][1] == THIRD and previews(t)[2][5] is True
         and previews(t)[2][4] == "Not made yet", previews(t)[2:])
    set_picks(s, "v3", [1, 2, 3, 4, 5, 6, 1, 2, 3][:6] + [])
    code, t = look(s)
    case("its photos show once they are in", previews(t)[2][2] == 6 and previews(t)[2][5] is False, previews(t)[2])
    set_made(s, "v3", P3)
    code, t = look(s)
    btn = add_button(t) or ""
    offered = json.loads(html.unescape(re.search(r"data-reels='([^']*)'", btn).group(1)))
    case("the third reel made: it is the only one offered (the others are in the queue or posted)", offered == [{"id": "v3", "name": THIRD}], offered)
    # the open reel when none is named (hers)
    code, j = add(s)
    case("a press that names no reel adds the one being worked on (hers)", code == 200 and (was["id"] + "-v3") in reel_pieces(s)
         and reel_pieces(s)[was["id"] + "-v3"]["reel_name"] == THIRD, sorted(reel_pieces(s)))
    # a reel renamed is shown by its new name
    code, out = s.cmd("reel_page.py", "reels", KIT, "--rename", THIRD, "--to", "Golden hour")
    code2, out2 = s.cmd("posting_queue.py", "add", "--kit", KIT)
    case("a reel renamed: the queue's piece follows the new name the next time the kit is added",
         code == 0 and code2 == 0 and reel_pieces(s)[was["id"] + "-v3"]["reel_name"] == "Golden hour" and "reel (Golden hour): green" in out2, (out[-200:], out2[-300:]))
    case("...and no piece was made for a reel nobody asked to queue; none was renamed", sorted(reel_pieces(s)) == [was["id"], was["id"] + "-v2", was["id"] + "-v3"])
    s.stop()


SAVED_VIDEO = "Saved as a video, in this shoot's Reels folder:"       # ours: her v27 card has no line for a saved video


def check_video(s):
    """A B-roll video saved from the reel page counts as made (the stage-1 contract; the review of Nov 17 found a shoot
    with ONE reel went by CapCut projects alone, so Add this reel to my posting queue showed and then failed)."""
    s.start()
    video = SHORT + " B-roll.mp4"
    set_video(s, "v1", video)
    code, t = look(s)
    r = box(t, "queue-reel")
    st = re.search(r"<div class='status'>(.*?)</div>", t.split("data-piece='carousel'", 1)[0], re.S)
    status = re.sub(r"\s+", " ", text_of(st.group(1))).replace("\x1f", "").strip() if st else ""
    case("one reel, a saved video, no CapCut project: the Reel card says our 'Saved as a video, in this shoot's Reels folder: <file>'",
         code == 200 and status == SAVED_VIDEO + " " + video, status)
    case("...never 'In CapCut' or 'Not made yet', and no Open in CapCut (there is no project to open)",
         "In CapCut" not in text_of(t.split("data-piece='carousel'", 1)[0]) and "Not made yet" not in status and "id='capcut'" not in t)
    case("...and her 'Create another reel' (the reel is made), with the queue step live: her no-caption line, the button marked to ask first",
         "Create another reel" in text_of(t) and READY_NOCAP in text_of(r) and add_button(t) is not None and "disabled" not in add_button(t), text_of(r)[:300])
    code, j = add(s)
    x = s.queue_piece("reel") or {}
    case("Add to my queue on that one reel: added, ready to post (hers refused it with the locked line)",
         code == 200 and j.get("ok") and j["queue"]["status"] == "green" and x.get("status") == "green", (code, j))
    case("a shoot with one reel keeps the queue's same fields as ever", "version" not in x and "reel_name" not in x, sorted(x))
    code, t = look(s)
    case("the page now says 'In your posting queue.' with her '✓ Added to my queue'", "In your posting queue." in text_of(box(t, "queue-reel"))
         and "✓ Added to my queue" in text_of(box(t, "queue-reel")), text_of(box(t, "queue-reel"))[:300])
    # a second reel, saved as a video too: each reel's own preview says so, and it can be added by its id
    new_reel(s, SECOND)
    set_picks(s, "v2", [6, 5])
    stem = video_stem(s)
    case("the name the reel page itself gives that reel's saved video is one a PC can make: none of  \\ / : * ? \" < > |  in it, the rest kept",
         not re.search(r'[\\/:*?"<>|]', stem) and stem.endswith(" B-roll - White b Backdrop") and "'boys' 🌊" in stem and "Zoë" in stem, stem)
    video2 = SHORT + " B-roll - " + SECOND_FILE + ".mp4"
    set_video(s, "v2", video2)
    code, t = look(s)
    pv = previews(t)
    case("two reels, both saved as videos: each preview says 'Saved as a video, ...: <its file>', no Open in CapCut under them",
         [(v, n, st) for v, n, _c, _m, st, _e in pv] == [("v1", "Reel 1", SAVED_VIDEO + " " + video), ("v2", SECOND, SAVED_VIDEO + " " + video2)]
         and "id='capcut'" not in t, pv)
    code, j = add(s, reel="v2")
    case("the second reel, saved as a video, goes in the queue by its id", code == 200 and j.get("ok") and len(reel_pieces(s)) == 2, (code, j))
    set_made(s, "v2", P2)
    code, t = look(s)
    pv = previews(t)
    case("a reel made in CapCut after its video: 'In CapCut: <project>' again, and one Open in CapCut under the previews",
         pv[1][4] == "In CapCut: " + P2 and t.count("id='capcut'") == 1, (pv, t.count("id='capcut'")))


def check_twin(s):
    """Two shoots whose names shorten alike, each with two reels: every piece is its own kit's."""
    two_reels(s)
    twin = ppc.make_twin(s)
    s.start()
    c1, _ = add(s, reel="v2")
    c2 = s.http("POST", "/words-queue", {"kit": ppc.TWIN, "piece": "reel", "reel": "v2"})[0]
    p = s.posting()["pieces"]
    mine = [x for x in p if re.split(r"[\\/]", x["kit"])[-1] == KIT and re.search(r"-reel(-v\d+)?$", x["id"])]
    theirs = [x for x in p if re.split(r"[\\/]", x["kit"])[-1] == ppc.TWIN and re.search(r"-reel(-v\d+)?$", x["id"])]
    ids = [x["id"] for x in p]
    case("two shoots whose names shorten alike, each with a second reel: four reel pieces, no id twice",
         c1 == 200 and c2 == 200 and len(mine) == 2 and len(theirs) == 2 and len(set(ids)) == len(ids), ids)
    case("...each second reel's piece is named after its own kit's reel piece", sorted(x["id"] for x in mine)[1] == sorted(x["id"] for x in mine)[0] + "-v2"
         and sorted(x["id"] for x in theirs)[1] == sorted(x["id"] for x in theirs)[0] + "-v2"
         and {x["status"] for x in mine if x["id"].endswith("-v2")} == {"green"} and {x["status"] for x in theirs if x["id"].endswith("-v2")} == {"green"})
    case("the twin folder is still there", twin.is_dir())
    s.stop()


# ---------- 4. the queue's names, and the cover picker's photos ----------

def check_names(s):
    two_reels(s)
    s.start()
    s.http("POST", "/words-rhythm", {"text": "3 a week"})
    add(s, reel="v1")
    add(s, reel="v2")
    st = ppc.page_state(s)
    g = {x["id"]: x for x in st["greens"]}
    base = next(i for i in g if i.endswith("-reel"))
    case("the posting page is told each reel's name, as text", g[base]["reel_name"] == "Reel 1" and g[base + "-v2"]["reel_name"] == SECOND
         and g[base + "-v2"]["role"] == "reel" and g[base + "-v2"]["kind"] == "reel", [(i, x.get("reel_name")) for i, x in g.items()])
    code, _, raw = s.http("GET", "/posting.html")
    t = raw.decode("utf-8")
    case("the page draws '<shoot> reel · <reel name>' in the lists and the panel's heading, through its text-only way",
         "${x.reel_name?' · '+esc(x.reel_name):''}" in t and "+(x.reel_name?' · '+x.reel_name:'')" in t and "<b>Backdrop" not in t.split("id='data'")[0])
    case("no path in what the page is handed", str(s.kit) not in json.dumps(st) and str(s.work) not in json.dumps(st))

    # the cover picker: that reel's own photos, in the order it plays, whichever reel is open on the reel page
    c1, p1, _ = ppc.panel(s, base)
    c2, p2, _ = ppc.panel(s, base + "-v2")
    in1 = [c["rel"] for c in p1["choices"] if c.get("in_reel")]
    in2 = [c["rel"] for c in p2["choices"] if c.get("in_reel")]
    case("the first reel's picker: its own photos first, in play order (1,2,3,4)", c1 == 200
         and in1 == ["Photos/beach-%03d.jpg" % n for n in (1, 2, 3, 4)] and [c["rel"] for c in p1["choices"]][:4] == in1, in1)
    case("the second reel's picker: ITS photos, in ITS order (6,5), then the rest of the shoot", c2 == 200
         and in2 == ["Photos/beach-006.jpg", "Photos/beach-005.jpg"]
         and [c["rel"] for c in p2["choices"]] == in2 + ["Photos/beach-%03d.jpg" % n for n in (1, 2, 3, 4)], [c["rel"] for c in p2["choices"]])
    code, out = s.cmd("reel_page.py", "reels", KIT, "--open", "Reel 1")
    c2b, p2b, _ = ppc.panel(s, base + "-v2")
    c1b, p1b, _ = ppc.panel(s, base)
    case("...the same whichever reel is open on the reel page", code == 0 and [c["rel"] for c in p2b["choices"]] == [c["rel"] for c in p2["choices"]]
         and [c["rel"] for c in p1b["choices"]] == [c["rel"] for c in p1["choices"]], out[-200:])
    case("the cover in use is the reel's own first photo until they pick", p1["cover"] == "Photos/beach-001.jpg" and p2["cover"] == "Photos/beach-006.jpg", (p1["cover"], p2["cover"]))
    code, j, _ = ppc.cover(s, base + "-v2", "Photos/beach-003.jpg")
    x = ppc.piece(s, base + "-v2")
    case("any other photo from the shoot can be the cover: saved on that reel's piece only", code == 200 and x["cover"] == "Photos/beach-003.jpg"
         and "cover" not in ppc.piece(s, base) and ppc.panel(s, base + "-v2")[1]["cover"] == "Photos/beach-003.jpg", (code, x.get("cover")))
    code, _, _ = ppc.cover(s, base + "-v2", "Photos/../../kit.json")
    case("a cover that isn't a photo of the kit is refused", code == 400 and ppc.piece(s, base + "-v2")["cover"] == "Photos/beach-003.jpg", code)
    cc, pc, _ = ppc.panel(s, base.replace("-reel", "-carousel"))
    case("a carousel's panel is as it was (not an upcoming post here: no panel)", cc in (200, 404))
    s.stop()


# ---------- 5. the chat ----------

def check_chat(s):
    two_reels(s, second_made=False)
    code, out = s.cmd("posting_queue.py", "add", "--kit", KIT)
    base = next(i for i in reel_pieces(s))
    case("add --kit with several reels: the kit's reel piece is the first reel's, named, and no piece is made for the others",
         code == 0 and sorted(reel_pieces(s)) == [base] and reel_pieces(s)[base]["reel_name"] == "Reel 1" and reel_pieces(s)[base]["status"] == "yellow"
         and "reel (Reel 1): yellow" in out, out[-300:])
    before = (s.studio / "posting.json").read_bytes()
    code, out = s.cmd("posting_queue.py", "ready", "boys reel", "--reel", "white")
    case("ready --reel for a reel that isn't made: stops in plain words, nothing changed", code != 0 and "isn't made in CapCut yet" in out
         and "Nothing changed" in out and (s.studio / "posting.json").read_bytes() == before, out[-300:])
    code, out = s.cmd("posting_queue.py", "ready", "boys reel", "--reel", "sunset")
    case("ready --reel with a name that fits no reel: stops and lists the shoot's reels, nothing changed", code != 0 and "Reel 1" in out and "White <b>Backdrop" in out
         and (s.studio / "posting.json").read_bytes() == before, out[-300:])
    code, out = s.cmd("posting_queue.py", "ready", "no such shoot reel", "--reel", "white")
    case("ready --reel for a shoot that isn't in the queue: stops, nothing changed", code != 0 and "Nothing changed" in out
         and (s.studio / "posting.json").read_bytes() == before, out[-300:])
    set_made(s, "v2", P2)
    code, out = s.cmd("posting_queue.py", "ready", "boys reel", "--reel", "white")
    v2 = reel_pieces(s).get(base + "-v2") or {}
    case("ready --reel \"white\": that reel's own piece is made and marked ready; the first reel's is as it was",
         code == 0 and v2.get("status") == "green" and v2.get("reel_name") == SECOND and reel_pieces(s)[base]["status"] == "yellow"
         and "reel (%s): ready to post" % SECOND in out, out[-300:])
    code, out = s.cmd("posting_queue.py", "list")
    case("the list names each reel: '<shoot> reel (<reel name>)'", code == 0 and "reel (%s)" % SECOND in out and "reel (Reel 1)" in out, out[-400:])
    code, out = s.cmd("posting_queue.py", "posted", "boys reel")
    case("'the <shoot> reel' alone, with two reels in the queue, could mean more than one: it asks which, nothing changed",
         code != 0 and "could mean more than one" in out and "(Reel 1)" in out and "(%s)" % SECOND in out and reel_pieces(s)[base + "-v2"]["status"] == "green", out[-300:])
    code, out = s.cmd("posting_queue.py", "posted", "boys reel white backdrop")
    case("a reel is found by its name: posted \"<shoot> reel white backdrop\"", code == 0 and reel_pieces(s)[base + "-v2"]["status"] == "posted"
         and reel_pieces(s)[base]["status"] == "yellow", out[-300:])
    code, out = s.cmd("posting_queue.py", "ready", "boys reel", "--reel", "Reel 1")
    case("ready --reel \"Reel 1\": the kit's own reel piece, never a second one", code == 0 and reel_pieces(s)[base]["status"] == "green"
         and sorted(reel_pieces(s)) == [base, base + "-v2"], out[-300:])
    was = json.dumps(reel_pieces(s), sort_keys=True)
    code, out = s.cmd("posting_queue.py", "made", SHORT + " reel", "--where", "A newer project")
    case("the reel maker's 'made' for a shoot with several reels never puts a ready reel back to in progress",
         code == 0 and "more than one reel" in out and reel_pieces(s)[base]["status"] == "green" and reel_pieces(s)[base + "-v2"]["status"] == "posted"
         and json.dumps(reel_pieces(s), sort_keys=True) == was, out[-300:])
    code, out = s.cmd("posting_queue.py", "ready", "boys carousel")
    case("ready without --reel is as it always was", code == 0 and "carousel: ready to post" in out, out[-200:])


# ---------- 6. reminders: each reel's piece its own (a pretend calendar only) ----------

def check_reminders(s):
    two_reels(s)
    rpc.cfg(s)
    s.start()
    s.http("POST", "/words-rhythm", {"text": "3 a week"})
    add(s, reel="v1")
    add(s, reel="v2")
    base = next(i for i in reel_pieces(s) if i.endswith("-reel"))
    v2 = base + "-v2"
    rpc.settle(s)
    rpc.press(s, {"action": "remind-calendar", "calendar": "Home"})
    rpc.press(s, {"action": "remind", "id": v2, "time": "09:00"})
    ok = rpc.until(lambda: len(rpc.events(s, v2)) == 1) and rpc.settle(s)
    ev = (rpc.events(s, v2) or [{}])[0]
    case("a reminder on the second reel's post: one event, on that reel's own day, for that piece only",
         ok and ev.get("date") == reel_pieces(s)[v2]["date"] and ev.get("time") == "09:00" and not rpc.events(s, base), ev)
    case("with no caption, the reminder's notes say so: 'No caption yet. Write it on your words page in the post kit.'",
         ok and NO_CAPTION_NOTE in ev.get("notes", ""), ev.get("notes"))
    rpc.press(s, {"action": "remind", "id": base, "time": "18:00"})
    ok = rpc.until(lambda: len(rpc.events(s, base)) == 1) and rpc.settle(s)
    case("...and the first reel's has its own event at its own time", ok and rpc.events(s, base)[0]["time"] == "18:00"
         and rpc.events(s, base)[0]["date"] != ev.get("date") and len(rpc.book(s)) == 2, rpc.book(s))
    s.words("draft", "reel", {"caption": "A caption written later.", "hooks": HOOKS})
    rpc.press(s, {"action": "remind-sync"})
    ok = rpc.until(lambda: "A caption written later." in (rpc.events(s, v2) or [{}])[0].get("notes", ""), 20) and rpc.settle(s)
    case("a caption written later reaches the reminder's notes", ok, (rpc.events(s, v2) or [{}])[0].get("notes"))
    rpc.press(s, {"action": "unready", "id": v2})
    ok = rpc.until(lambda: not rpc.events(s, v2)) and rpc.settle(s)
    case("that reel taken out of line: its event goes, the other reel's stays", ok and len(rpc.events(s, base)) == 1, rpc.book(s))
    s.stop()


# ---------- 7. who may press, and what a press may say ----------

def check_guard(s):
    two_reels(s)
    s.start()
    nothing = not s.posting()
    bad = [add(s, reel=r)[0] for r in ("v0", "v", "2", "../v2", "v2 ", 2, ["v2"], {"id": "v2"}, "")]
    case("a reel id that isn't one is refused (400 each), nothing written", bad == [400] * 9 and nothing and not s.posting(), bad)
    code, j = add(s, reel="v9")
    case("a reel that isn't in the shoot: refused in her words, nothing written", code == 409 and j["words"] == "That reel isn't there anymore." and not s.posting(), (code, j))
    code, j = add(s, "carousel", reel="v2")
    case("a reel named for a carousel is refused", code == 400 and not s.posting(), (code, j))
    code, j = add(s, reel="v2", extra=1)
    case("a field too many is refused", code == 400 and not s.posting(), (code, j))
    codes = [s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel", "reel": "v2"}, headers=h)[0]
             for h in ({"Origin": "http://evil.example"}, {"Sec-Fetch-Site": "cross-site"}, {"Host": "evil.example:80"})]
    case("another page's press, a cross-site press and another host are refused (403 each), nothing written", codes == [403] * 3 and not s.posting(), codes)
    code, _, _ = s.http("GET", "/words-queue?kit=%s&piece=reel&reel=v2" % KQ)
    case("a GET can't add", code in (404, 405, 501) and not s.posting(), code)
    code, j = add(s, reel="v2")
    case("(the same press from the page itself adds it)", code == 200 and len(reel_pieces(s)) == 2)
    # a one-reel shoot: a reel id is ignored, the kit's own piece (hers)
    s.stop()


# ---------- 8. the kit page in a hidden Chrome ----------

POPUPS = "window.__pop = []; ['alert','confirm','prompt'].forEach(function(k){ window[k] = function(){ window.__pop.push(k); return true; }; });"
BOX = "(function(){ var b = document.getElementById('nocap'); return !!b && !b.hidden && getComputedStyle(b).display !== 'none'; })()"
BOX_SAYS = ("(function(){ return [document.getElementById('nocapTitle').textContent, document.getElementById('nocapText').textContent,"
            " Array.from(document.querySelectorAll('#nocapRow button')).map(function(b){ return b.textContent; })]; })()")


def check_page(c, s):
    s.reel_made()
    s.slides_made(3)
    s.start()
    c.init_script(POPUPS)
    url = s.url(PAGE)
    here = "location.pathname.indexOf('/content/') === 0"
    c.open(url)
    c.wait_for("document.body.classList.contains('live') && !!document.querySelector('[data-box=queue-reel] [data-add]')", 10)
    case("in a browser: made, no caption: her line and a live Add to my queue; the box is not showing",
         c.text("[data-box=queue-reel] .ws") == READY_NOCAP and c.js(BOX) is False)
    c.click("[data-box=queue-reel] [data-add]")
    c.wait_for(BOX, 5)
    said = c.js(BOX_SAYS)
    case("a press with no caption: her box, on the page: 'You haven't written a caption for your reel yet' / 'That's okay. ...'",
         said == [NOCAP_TITLE % "reel", NOCAP_TEXT, ["Add it to my queue", "Write my caption"]], said)
    case("...never a browser pop-up, nothing added yet, and the card's page was not opened", c.js("window.__pop") == [] and not s.posting() and c.js(here) is True)
    case("the first button is the dark one and has the keyboard", c.js("document.activeElement === document.querySelector('#nocapRow button') && document.activeElement.className === 'main'") is True)
    r = c.rect("#nocap .box")
    case("the box sits over the page in the middle, at most 420 wide", r["w"] <= 420.5 and abs(r["cx"] - 640) < 2 and c.js("getComputedStyle(document.getElementById('nocap')).position") == "fixed", r)
    c.key("Escape")
    time.sleep(0.3)
    case("Escape closes it with nothing done; the button it came from has the keyboard again", c.js(BOX) is False and not s.posting()
         and c.js("document.activeElement === document.querySelector('[data-box=queue-reel] [data-add]')") is True)
    c.click("[data-box=queue-reel] [data-add]")
    c.wait_for(BOX, 5)
    c.click("#nocapClose")
    time.sleep(0.3)
    case("the x closes it with nothing done", c.js(BOX) is False and not s.posting() and c.js(here) is True)
    c.click("[data-box=queue-carousel] [data-add]")
    c.wait_for(BOX, 5)
    case("the carousel asks the same, about the carousel", c.js(BOX_SAYS)[0] == NOCAP_TITLE % "carousel", c.js(BOX_SAYS))
    c.click("#nocapRow button", nth=1)
    c.wait_for("location.pathname === '/words.html'", 10)
    case("Write my caption opens that piece's words page, and nothing was added", c.js("decodeURIComponent(location.search)") == "?kit=%s&piece=carousel" % KIT
         and not s.posting(), c.js("location.href"))
    c.open(url)
    c.wait_for("document.body.classList.contains('live') && !!document.querySelector('[data-box=queue-reel] [data-add]')", 10)
    c.click("[data-box=queue-reel] [data-add]")
    c.wait_for(BOX, 5)
    c.click("#nocapRow button", nth=0)
    c.wait_for("document.querySelectorAll('[data-box=queue-reel] .qchips button').length === 5", 5)
    case("Add it to my queue: the box closes and the rhythm is asked the first time, nothing added yet", c.js(BOX) is False and not s.posting())
    c.click("[data-box=queue-reel] .qchips button:nth-child(3)")
    try:
        c.wait_for("!!document.querySelector('[data-box=queue-reel] .qbtn.done')", 10)
        done = True
    except chrome_drive.Timeout:
        done = False
    case("...then it is added with no caption: 'Down for Wed, Nov 11.' and '✓ Added to my queue'", done and (s.queue_piece("reel") or {}).get("status") == "green"
         and c.text("[data-box=queue-reel] .ws") == "Down for Wed, Nov 11." and c.js(here) is True, c.text("[data-box=queue-reel]"))
    # with a caption: no question
    s.words("draft", "carousel", {"caption": "Hannah's baby boy was just turning one..."})
    c.open(url)
    c.wait_for("document.body.classList.contains('live') && !!document.querySelector('[data-box=queue-carousel] [data-add]')", 10)
    c.click("[data-box=queue-carousel] [data-add]")
    try:
        c.wait_for("!!document.querySelector('[data-box=queue-carousel] .qbtn.done')", 10)
        done = True
    except chrome_drive.Timeout:
        done = False
    case("a piece with its caption is added at once: no box", done and c.js(BOX) is False and c.js("window.__pop") == [], c.text("[data-box=queue-carousel]"))

    # ---- several reels
    new_reel(s, SECOND)
    set_picks(s, "v2", [6, 5])
    set_made(s, "v2", P2)
    new_reel(s, THIRD)
    set_picks(s, "v3", [3])
    set_made(s, "v3", P3)
    c.open(url)
    c.wait_for("document.body.classList.contains('live') && document.querySelectorAll('.onereel').length === 3", 10)
    names = c.js("Array.from(document.querySelectorAll('.onereel .rn')).map(function(n){ return n.textContent; })")
    case("in a browser: a preview of each reel by name, the names only ever letters", names == ["Reel 1", SECOND, THIRD]
         and c.js("document.querySelectorAll('.onereel b').length") == 3 and c.count(".onereel .rn *") == 0 and c.js("window.pwned === undefined") is True, names)
    lines = c.js("Array.from(document.querySelectorAll('.qreels li')).map(function(n){ return n.textContent; })")
    case("step 3 lists each reel: the first is down for its day, the others are 'made, not in your queue yet'",
         lines == ["Reel 1: down for Wed, Nov 11", SECOND + ": made, not in your queue yet", THIRD + ": made, not in your queue yet"], lines)
    case("the card is whole: its previews and its steps inside one link, no link inside a link",
         c.js("document.querySelectorAll('#pieces > *').length === 3 && document.querySelectorAll('a a').length === 0"
              " && document.querySelector('a.piece[data-piece=reel]').contains(document.querySelector('.qreels'))") is True)
    before = len(reel_pieces(s))
    c.click("[data-box=queue-reel] [data-add]")
    c.wait_for(BOX, 5)
    said = c.js(BOX_SAYS)
    case("Add to my queue asks 'Which reel goes in your queue?' with a button for each reel that is made and not queued",
         said == [WHICH_TITLE, WHICH_TEXT, [SECOND, THIRD]] and c.count("#nocapRow button *") == 0, said)
    case("...nothing added yet, no pop-up", len(reel_pieces(s)) == before and c.js("window.__pop") == [])
    c.click("#nocapRow button", nth=1)
    c.wait_for("document.getElementById('nocapTitle').textContent === %s" % json.dumps(NOCAP_TITLE % "reel"), 5)
    case("the reel picked: then the caption question, since the reel has no caption", c.js(BOX) is True and c.js(BOX_SAYS)[2] == ["Add it to my queue", "Write my caption"])
    c.click("#nocapRow button", nth=0)
    c.wait_for("document.querySelectorAll('.qreels li')[2].textContent.indexOf('down for ') > 0", 10)
    pcs = reel_pieces(s)
    third = next((x for i, x in pcs.items() if i.endswith("-v3")), {})
    lines = c.js("Array.from(document.querySelectorAll('.qreels li')).map(function(n){ return n.textContent; })")
    case("the reel they picked is the one that went in: the third, by name, with its own spot",
         third.get("status") == "green" and third.get("reel_name") == THIRD and not any(i.endswith("-v2") for i in pcs)
         and lines[2].startswith(THIRD + ": down for ") and lines[1] == SECOND + ": made, not in your queue yet", (sorted(pcs), lines))
    case("the page was drawn again in place: still on the kit page, the box closed", c.js(here) is True and c.js(BOX) is False)
    c.click("[data-box=queue-reel] [data-add]")
    c.wait_for(BOX, 5)
    case("one reel left: the question is skipped, straight to the caption question", c.js(BOX_SAYS)[0] == NOCAP_TITLE % "reel", c.js(BOX_SAYS))
    c.click("#nocapRow button", nth=0)
    c.wait_for("!!document.querySelector('[data-box=queue-reel] .qbtn.done')", 10)
    case("...and that reel went in: all three have their own piece, the button is done", sorted(i[-3:] for i in reel_pieces(s) if re.search(r"-v\d$", i)) == ["-v2", "-v3"]
         and len(reel_pieces(s)) == 3 and c.text("[data-box=queue-reel] .qbtn") == "✓ Added to my queue", sorted(reel_pieces(s)))
    case("no error on the page, nothing asked of a browser pop-up", not c.page_errors() and c.js("window.__pop") == [], c.page_errors())

    # ---- a phone's width: the box fits
    p = s.posting()
    for y in p["pieces"]:
        if re.search(r"-reel-v\d$", y["id"]):
            y["status"] = "yellow"
            y.pop("slot", None)
            y.pop("date", None)
    s.write_posting(p)
    c.phone(375, 800)
    c.open(url)
    c.wait_for("document.body.classList.contains('live') && !!document.querySelector('[data-box=queue-reel] [data-add]')", 10)
    c.js("document.querySelector('[data-box=queue-reel] [data-add]').click()")
    c.wait_for(BOX, 5)
    r = c.rect("#nocap .box")
    btns = [c.rect("#nocapRow button", nth=i) for i in range(2)]
    case("at a phone's width the box and its buttons are inside the screen", r["x"] >= 0 and r["x"] + r["w"] <= 375.5
         and all(b["x"] >= r["x"] and b["x"] + b["w"] <= r["x"] + r["w"] + 0.5 for b in btns), (r, btns))
    case("...and the page is no wider than the phone", c.js("document.documentElement.scrollWidth") <= 375, c.js("document.documentElement.scrollWidth"))
    c.desktop()
    s.stop()


def check_page_rhythm(c, s):
    """The first add of all, on a shoot with two reels: which reel, the caption question, how often, and the reel
    they picked is still the one that goes in."""
    two_reels(s)
    s.start()
    c.open(s.url(PAGE))
    c.wait_for("document.body.classList.contains('live') && !!document.querySelector('[data-box=queue-reel] [data-add]')", 10)
    c.click("[data-box=queue-reel] [data-add]")
    c.wait_for(BOX, 5)
    case("two reels, nothing queued yet: both are offered, in the order they were started", c.js(BOX_SAYS)[2] == ["Reel 1", SECOND], c.js(BOX_SAYS))
    c.click("#nocapRow button", nth=0)                # Reel 1: NOT the reel open on the reel page (that is the second)
    c.wait_for("document.getElementById('nocapTitle').textContent === %s" % json.dumps(NOCAP_TITLE % "reel"), 5)
    c.click("#nocapRow button", nth=0)
    c.wait_for("document.querySelectorAll('[data-box=queue-reel] .qchips button').length === 5", 5)
    case("no rhythm yet: 'How often do you want to post?' comes last, and nothing is added before it is answered", not s.posting())
    c.click("[data-box=queue-reel] .qchips button:nth-child(3)")
    c.wait_for("document.querySelectorAll('.qreels li').length === 2 && document.querySelector('.qreels').textContent.indexOf('down for ') > 0", 10)
    pcs = reel_pieces(s)
    lines = c.js("Array.from(document.querySelectorAll('.qreels li')).map(function(n){ return n.textContent; })")
    case("after the rhythm, the reel they picked (the first, not the one open on the reel page) is the one in line; the other has no piece",
         {i[-3:]: x["status"] for i, x in pcs.items()} == {"eel": "green"} and s.posting().get("interval") == 3.0
         and lines == ["Reel 1: down for Wed, Nov 11", SECOND + ": made, not in your queue yet"], (sorted(pcs), lines))
    case("no error on the page", not c.page_errors(), c.page_errors())
    s.stop()


# ---------- 9. the posting page in a hidden Chrome ----------

def check_posting(c, s):
    two_reels(s)
    s.slides_made(3)
    s.start()
    s.http("POST", "/words-rhythm", {"text": "3 a week"})
    add(s, reel="v1")
    add(s, reel="v2")
    add(s, "carousel")
    base = next(i for i in reel_pieces(s) if i.endswith("-reel"))
    v2 = base + "-v2"
    cid = base[:-5] + "-carousel"
    c.open(s.url("/posting.html"))
    c.wait_for("document.querySelectorAll('#greens .row').length === 3", 10)
    rows = c.js("Array.from(document.querySelectorAll('#greens .row .name')).map(function(n){ return n.textContent; })")
    case("the list shows '<shoot> reel · <reel name>' for each reel, and the carousel as ever",
         rows == [SHORT + " reel · Reel 1", SHORT + " reel · " + SECOND, SHORT + " carousel"] and c.count("#greens .row .name *") == 0
         and c.js("window.pwned === undefined") is True, rows)
    ppc.open_panel(c, v2)
    c.wait_for(ppc.READY, 10)
    case("the panel's heading: 'Your <shoot> reel · <reel name>', as text", c.text("#pick .ph b") == "Your %s reel · %s" % (SHORT, SECOND) and c.count("#pick .ph b *") == 0, c.text("#pick .ph b"))
    subs = c.js("Array.from(document.querySelectorAll('#pick .sub')).map(function(n){ return [n.textContent, n.offsetParent !== null]; })")
    first = c.js("Array.from(document.querySelectorAll('#pick .ps > .strip .c')).map(function(b){ return [b.dataset.rel, b.querySelector('.n') ? b.querySelector('.n').textContent : '', b.title, b.classList.contains('on')]; })")
    case("'From your reel, in the order it plays' first: this reel's own photos, numbered in play order, the one in use marked",
         subs[0] == [FROM_REEL, True] and first == [["Photos/beach-006.jpg", "1", "Photo 1 in your reel", True], ["Photos/beach-005.jpg", "2", "Photo 2 in your reel", False]], (subs, first))
    more = c.js("(function(){ var b = document.querySelector('#pick .more'), o = document.querySelector('#pick .others'); return [b.textContent, b.getAttribute('aria-expanded'), o.hidden, getComputedStyle(o).display]; })()")
    case("'+ Use a different photo' under it, and 'Any other photo from the shoot' closed", more == [USE_OTHER, "false", True, "none"], more)
    c.click("#pick .more")
    time.sleep(0.4)
    more = c.js("(function(){ var b = document.querySelector('#pick .more'), o = document.querySelector('#pick .others'); return [b.textContent, b.getAttribute('aria-expanded'), o.hidden, o.querySelector('.sub').textContent]; })()")
    others = c.js("Array.from(document.querySelectorAll('#pick .others .c')).map(function(b){ return [b.dataset.rel, !!b.querySelector('.n')]; })")
    case("a press opens it: 'Any other photo from the shoot', the rest of the shoot, not numbered; the button says 'Hide the other photos'",
         more == [HIDE_OTHER, "true", False, ANY_OTHER] and others == [["Photos/beach-%03d.jpg" % n, False] for n in (1, 2, 3, 4)], (more, others))
    c.click("#pick .others .c[data-rel='Photos/beach-003.jpg']")
    c.wait_for("!!document.querySelector(\"#pick .others .c[data-rel='Photos/beach-003.jpg'].on\")", 10)
    case("one of those picked: saved as that reel's cover, and the other photos are still open after the page drew again",
         ppc.piece(s, v2).get("cover") == "Photos/beach-003.jpg" and c.js("document.querySelector('#pick .others').hidden") is False
         and c.count("#pick .c.on") == 1 and "cover" not in ppc.piece(s, base), ppc.piece(s, v2).get("cover"))
    c.click("#pick .ps > .strip .c[data-rel='Photos/beach-005.jpg']")
    c.wait_for("!!document.querySelector(\"#pick .ps > .strip .c[data-rel='Photos/beach-005.jpg'].on\")", 10)
    case("a photo of the reel picked while the others are open: they stay open, as they left them", c.js("document.querySelector('#pick .others').hidden") is False
         and c.text("#pick .more") == HIDE_OTHER and ppc.piece(s, v2).get("cover") == "Photos/beach-005.jpg")
    c.click("#pick .others .c[data-rel='Photos/beach-003.jpg']")
    c.wait_for("!!document.querySelector(\"#pick .others .c[data-rel='Photos/beach-003.jpg'].on\")", 10)
    c.click("#pick .more")
    time.sleep(0.3)
    case("a press hides them again", c.js("document.querySelector('#pick .others').hidden") is True and c.text("#pick .more") == USE_OTHER)
    c.click("#pick .x")
    time.sleep(0.3)
    ppc.open_panel(c, v2)
    c.wait_for(ppc.READY, 10)
    c.wait_for("!!document.querySelector('#pick .others')", 5)
    case("opened again: the cover is one of the other photos, so they are open already (hers)", c.js("document.querySelector('#pick .others').hidden") is False
         and c.text("#pick .more") == HIDE_OTHER and c.js("!!document.querySelector(\"#pick .others .c[data-rel='Photos/beach-003.jpg'].on\")") is True)
    c.click("#pick .x")
    time.sleep(0.3)
    ppc.open_panel(c, base)
    c.wait_for(ppc.READY, 10)
    first = c.js("Array.from(document.querySelectorAll('#pick .ps > .strip .c')).map(function(b){ return b.dataset.rel; })")
    case("the first reel's panel shows ITS photos in ITS order, and its other photos closed", first == ["Photos/beach-%03d.jpg" % n for n in (1, 2, 3, 4)]
         and c.js("document.querySelector('#pick .others').hidden") is True and c.text("#pick .ph b") == "Your %s reel · Reel 1" % SHORT, first)
    c.click("#pick .x")
    time.sleep(0.3)
    ppc.open_panel(c, cid)
    c.wait_for(ppc.READY, 10)
    nums = c.js("Array.from(document.querySelectorAll('#pick .c')).map(function(b){ return [b.querySelector('.n').textContent, b.title]; })")
    case("a carousel's panel is as it was: its slides numbered, no headings, no 'Use a different photo'", nums == [["1", "Slide 1"], ["2", "Slide 2"], ["3", "Slide 3"]]
         and c.count("#pick .sub") == 0 and c.count("#pick .more") == 0 and c.text("#pick .ph b") == "Your %s carousel" % SHORT, nums)
    case("no error on the page", not c.page_errors(), c.page_errors())
    c.phone(375, 800)
    c.open(s.url("/posting.html"))
    c.wait_for("document.querySelectorAll('#greens .row').length === 3", 10)
    c.js("document.querySelector('.tile.mine[data-id=%s]').dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}))" % json.dumps(v2))
    c.wait_for(ppc.READY, 10)
    case("at a phone's width the page is no wider than the phone with a reel's panel open", c.js("document.documentElement.scrollWidth") <= 375, c.js("document.documentElement.scrollWidth"))
    c.desktop()
    s.stop()


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    global ONLY
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=9940)
    ap.add_argument("--no-chrome", action="store_true", help="the routes only")
    ap.add_argument("--only", choices=("words", "optional", "reels", "video", "names", "cover", "chat", "reminders", "guard", "page", "posting"))
    a = ap.parse_args()
    ONLY = a.only
    if any(p in chrome_drive.NEVER_PORTS for p in range(a.port, a.port + 30)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="kit-reels-queue-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    os.environ["REMINDERS_BACKEND"] = "none"          # this program itself never asks a calendar
    made = []

    def one(name, backend="none"):
        s = fresh(work, name, a.port + 2 * len(made), backend)
        made.append(s)
        return s
    try:
        if want("words"):
            group("her words", check_words, one("words"))
        if want("optional"):
            group("captions are optional", check_optional, one("optional"))
        if want("reels"):
            group("a shoot with more than one reel", check_reels, one("reels"))
            group("two shoots whose names shorten alike", check_twin, one("twin"))
        if want("video"):
            group("a B-roll video saved from the reel page counts as made (v27)", check_video, one("video"))
        if want("names") or want("cover"):
            group("the queue's names and the cover picker's photos", check_names, one("names"))
        if want("chat"):
            group("the chat", check_chat, one("chat"))
        if want("reminders"):
            group("reminders, on a pretend calendar", check_reminders, one("reminders", "pretend"))
        if want("guard"):
            group("who may press", check_guard, one("guard"))
        if (want("page") or want("posting")) and (a.no_chrome or not chrome_drive.find_chrome()):
            skip("the pages in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        elif want("page") or want("posting"):
            with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                if want("page"):
                    group("the kit page", check_page, c, one("page"))
                    group("the kit page: the first add of all, with two reels", check_page_rhythm, c, one("rhythm"))
                if want("posting"):
                    group("the posting page", check_posting, c, one("posting"))
    finally:
        for s in made:
            s.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
