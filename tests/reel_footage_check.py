#!/usr/bin/env python3
"""The reel page's step 1 (behind-the-scenes footage), the moment cards, the player and step 4 (the style),
checked on the server and on the real page in a HIDDEN Chrome, on small clips this test makes itself.

    python3 tests/guard.py 800 /usr/bin/python3 tests/reel_footage_check.py --work /private/tmp/somewhere [--port 9322]
        [--only server|order|make|page]

It touches video, so it is run under the 800 MB memory guard; it keeps itself small to fit: a 12-photo pretend
kit (tests/fake_kit.py), three clips of 6 seconds (640 x 360 H.264 with a tone, one stored sideways like a phone,
made with the Mac's own AVFoundation, as tests/video_check.py makes them), and the lightest hidden Chrome
(LIGHT below: one process, no Chrome extensions, no address-bar pages). Never a client's clip, never HEVC, 4K or
anything longer.

What it checks:
  * her words, word for word: every word of step 1 and step 4 on the page against her reel-maker.html (handoff v19,
    when it is on this computer; it is never in the repository);
  * Add my footage (makes <kit>/Footage, her words; no folder is really opened in a test); the list of videos,
    each by a key from its name, size and time, following a new file within her 4 s look; Good to know with her
    thresholds; the line to copy, with and without notes (copied with the page's own copy); Want to direct the
    reel? (600 characters) and How should it feel? (40), saved and read back;
  * the player: the original over Range (206) for a video that plays as it is; for one that doesn't (a fake facts
    entry, since AVFoundation here writes only H.264 4:2:0), the 540p copy, made once by the server's one preview
    worker, its state on disk; the sideways clip shown upright; the strip of stills, one every 2 s, jumping the
    player;
  * the moment cards: Use this moment adds a 4 s moment first and selected; − and + by half a second; Remove with
    a 10 s Undo; Select / ✓ Selected per style, her limits; all saved under the lock and back after a reload;
  * step 4: each style builds the clip order hers would (her server.py's footage_items, run here on a copy with
    stand-ins), Bookends with one clip puts it in twice as c1 and c2; a dry run through /reel-make (test) gives the
    same "Beats per piece" line as reel.py --clips straight from her order;
  * every refusal (a key or an id not its shape or not there, a path, another site, a Footage folder that is a
    link), nothing from the internet, no path in any answer, nothing of theirs changed or removed.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import reel_page_check as rpc  # noqa: E402

rpc.PHOTOS = PHOTOS = 12
KIT = rpc.KIT
KQ = KIT.replace(" ", "%20")
SHORT = "Fake beach"
# the lightest hidden Chrome that plays a video (measured Nov 7: about 600 MB by the guard's count, against 1 GB)
LIGHT = ("--single-process", "--disable-component-extensions-with-background-pages", "--enable-features=NetworkServiceInProcess2",
         "--disable-features=Translate,MediaRouter,OptimizationHints,DialMediaRouteProvider,SpareRendererForSitePerProcess,"
         "IsolateOrigins,site-per-process,WebUIOmniboxPopup,OmniboxWebUIPopup,WebUIOmniboxFullPopup,AimServerEligibility")

# Her words for step 1 and step 4, as her reel-maker.html shows them (handoff v19; since v27 the step's heading, the
# ask box's words and the line to copy's are her v27 page's, and the yes/no cards are gone: the chooser decides).
HERS1 = {
    "h2": "Choose your behind-the-scenes footage",
    "say2": "Press <b>Add my footage</b> and a Footage folder for this shoot opens in Finder. Drag your behind-the-scenes videos into it.",
    "add": "▶ Add my footage",
    "insight_b": "Good to know: longer footage takes longer",
    "insight": "Longer videos take me longer to look through and use more of your plan. A few minutes of footage takes a few minutes. A 20-minute video takes about 10 minutes or more.",
    "fix": "<b>Quick fix:</b> trim it first and keep just the parts you like. On your iPhone, open the video in Photos, tap Edit, and drag the ends of the timeline in. On a Mac, open it in QuickTime Player and choose Edit › Trim. A few short clips are quicker for me than one long video.",
    "paste_say": "Then, once your footage is in, copy this into the chat so I can look through it:",
    "copy": "Copy",
    "ask_b": "Is there anything specific you'd like your assistant to look for?",
    "ask": " Optional. Certain moments from the shoot, something funny you remember, or a special moment you'd love to have as a clip to choose from.",
    "ex1": "For example: “Find the first kiss.” or “Find the part where the baby grabs the camera strap.”",
    "ex2": "Another example: “Find the footage of me walking into the frame with my camera.”",
    "ask_ph": "Optional: the moments you'd like me to look for",
    "feel_b": "How should it feel?",
    "feels": ["Heartwarming", "Nostalgic", "Fun", "Dreamy", "Something else"],
    "feel_ph": "Your words, like joyful or cozy",
    "feel_small": "Optional. Pick one, or tap <b>Something else</b> and type your own. I'll pick the photos and moments that bring out that feeling. Tap it again to clear it.",
    "opened": "Your Footage folder is open in Finder. Drag your videos in, and they will show up here by themselves.",
}
HERS4 = {
    "h2": "What style of behind the scenes is this?",
    "say": "Pick a style. It uses the clips you selected in step 1. Style and vibe come last so you can try a few versions: change them and press Make my reel again. Every cut still lands on the beat. With a song, the footage plays muted so your song carries the reel; with No song, it keeps its own sound.",
    "cards": [["Moment first", "A few seconds of footage opens the reel, then your photos."],
              ["The reveal", "The moment the photo was taken, then the finished photo. A few times through."],
              ["Back and forth", "A clip, then a couple of photos, then the next clip, so it feels like being there."],
              ["Bookends", "Footage opens and closes the reel, with your photos in the middle. Works with any footage."]],
}
HERS_MAKE = {
    "clips_need": "<h3>One more thing: your clips</h3><p>Select the clip or clips to use under <b>Select your clips</b> in step 1, or choose <b>Just photos</b>.</p>",
    "not_looked": "<h3>I haven't looked through your footage yet</h3><p>Add your videos in step 1, then copy the line into the chat. The moments I find show up under <b>Select your clips</b> in step 1. Or choose <b>Just photos</b>.</p>",
}
# Her v27 (Nov 17): the footage editor replaced "Select your clips", the moment cards' − / + / Trim / Remove row and
# "Watch your footage and pick your own"; its words are reel_page.EDITOR_WORDS, held to her v27 page in check_editor_words


def rp():
    sys.path.insert(0, str(SCRIPTS))
    import reel_page
    return reel_page


# ---------- the clips (as tests/video_check.py makes them: AVFoundation, nothing installed) ----------

def make_clips(folder):
    import video_check as vc
    folder.mkdir(parents=True, exist_ok=True)
    cols = ";".join(",".join(map(str, c)) for c in vc.COLOURS)
    pic = folder / "picture.mov"
    vc.js("picture", str(pic), "640", "360", "6", "30", cols)
    wav = folder / "tone.wav"
    vc.tone_wav(wav)
    m4a = folder / "tone.m4a"
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(wav), str(m4a)], capture_output=True, check=True)
    out = {}
    for name, rot in (("clip.mov", 0), ("sideways.mov", 90)):
        vc.js("compose", str(pic), str(m4a), str(folder / name), str(rot), vc.RECORDED)
        out[name] = folder / name
    for p in (pic, wav, m4a):
        p.rename(folder.parent / ("made-" + p.name))      # kept, out of the way
    return out


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def no_path(obj):
    return not re.search(r"/private/|/Users/|/Volumes/|[A-Za-z]:\\\\|\.kit/", json.dumps(obj, ensure_ascii=False))


def foot(s):
    return s.http("GET", "/reel-footage?kit=" + KQ)


def wait_ready(s, seconds=60):
    end = time.time() + seconds
    j = None
    while time.time() < end:
        _, j, _ = foot(s)
        if j and j.get("videos") and all(v["preview"] in ("ready", "failed", "lowspace", "pc", "hevc_pc") for v in j["videos"]):
            return j
        time.sleep(0.5)
    return j


def record(s):
    return s.record() or {}


def moment(s, body):
    return s.http("POST", "/reel-moment", dict({"kit": KIT}, **body))


# ---------- 1. the server ----------

def check_server(s, clips):
    R = rp()
    code, j, _ = s.http("POST", "/reel-open", {"kit": KIT, "what": "footage"})
    case("Add my footage: makes the shoot's Footage folder and answers her words", code == 200 and j == {"ok": True, "words": HERS1["opened"]}
         and (s.kit / "Footage").is_dir(), (code, j))
    code, j, _ = foot(s)
    case("no videos yet: an empty list, the folder there", code == 200 and j["ok"] and j["videos"] == [] and j["folder"] is True and j["moments"] == [], j)
    shutil.copy(clips["clip.mov"], s.kit / "Footage" / "clip.mov")
    shutil.copy(clips["sideways.mov"], s.kit / "Footage" / "Sideways é.mov")
    (s.kit / "Footage" / ".hidden.mov").write_bytes(b"not listed")
    (s.kit / "Footage" / "notes.txt").write_text("not a video")
    j = wait_ready(s)
    vids = j["videos"] if j else []
    case("the videos in name order (hers), hidden files and non-videos left out", [v["name"] for v in vids] == ["Sideways é.mov", "clip.mov"], vids)
    sizes = {p.name: p.stat().st_size for p in (s.kit / "Footage").iterdir()}
    want = {v["name"]: R._video().key(s.kit / "Footage" / v["name"]) for v in vids}
    case("each video by a key from its name, size and time (12 letters and numbers), never a path",
         all(KEY_RE.fullmatch(v["key"]) and v["key"] == want[v["name"]] for v in vids) and no_path(j), [(v["name"], v["key"]) for v in vids])
    case("their length, the size shown (the sideways one upright, 360 x 640) and size in MB",
         [(v["length"], v["w"], v["h"], v["mb"]) for v in vids] == [(6.0, 360, 640, round(sizes["Sideways é.mov"] / 1e6)), (6.0, 640, 360, round(sizes["clip.mov"] / 1e6))], vids)
    case("both previews ready, a strip of stills one every 2 s (0, 2, 4)",
         all(v["preview"] == "ready" and v["strip"] == [{"n": 1, "t": 0.0}, {"n": 2, "t": 2.0}, {"n": 3, "t": 4.0}] for v in vids), vids)
    a = next(v for v in vids if v["name"] == "clip.mov")
    pr = json.loads((s.kit / ".kit" / "footage" / a["key"] / "preview.json").read_text())
    case("the preview's state is on disk (preview.json): ready, its strip folder; no copy for a video that plays as it is",
         pr["state"] == "ready" and pr["strip"] == "strip" and "copy" not in pr and not (s.kit / ".kit" / "footage" / a["key"] / "preview.mp4").exists(), pr)

    # the player: the original over Range
    orig = (s.kit / "Footage" / "clip.mov").read_bytes()
    base = "/reel-video?kit=%s&key=%s" % (KQ, a["key"])
    code, _, raw = s.http("GET", base, headers={"Range": "bytes=0-99"})
    h = s.last_headers
    case("the original, asked for a range: 206, its bytes exactly, Content-Range and Accept-Ranges", code == 206 and raw == orig[:100]
         and h.get("Content-Range") == "bytes 0-99/%d" % len(orig) and h.get("Accept-Ranges") == "bytes", (code, h))
    code, _, raw = s.http("GET", base, headers={"Range": "bytes=100-"})
    case("a range to the end: 206, the rest of it", code == 206 and raw == orig[100:], code)
    code, _, raw = s.http("GET", base, headers={"Range": "bytes=-50"})
    case("the last 50 bytes: 206", code == 206 and raw == orig[-50:], code)
    code, _, raw = s.http("GET", base)
    case("no range: 200 and the whole video, byte for byte", code == 200 and raw == orig, code)
    code, _, raw = s.http("GET", base, headers={"Range": "bytes=%d-" % len(orig)})
    case("a range past the end: 416", code == 416, code)
    code, _, raw = s.http("GET", "/reel-strip?kit=%s&key=%s&n=2" % (KQ, a["key"]))
    case("a still of the strip is a JPEG", code == 200 and raw[:3] == b"\xff\xd8\xff", code)

    # a video that doesn't play as it is: the small copy (a fake facts entry: AVFoundation writes only H.264 4:2:0 here)
    np_ = s.kit / "Footage" / "Not plain.mov"
    shutil.copy(clips["clip.mov"], np_)
    k = R._video().key(np_)
    fj = s.kit / ".kit" / "footage" / "facts.json"
    facts = json.loads(fj.read_text())
    fake = dict(facts[a["key"]], codec="hvc1", codec_name="hevc", chroma="4:2:0", bits=10, plays_as_is=False)
    facts[k] = fake
    fj.write_text(json.dumps(facts))
    j = wait_ready(s)
    v = next((x for x in (j or {}).get("videos", []) if x["name"] == "Not plain.mov"), None)
    copy = s.kit / ".kit" / "footage" / k / "preview.mp4"
    case("a video that doesn't play as it is gets the small copy, made once by the preview worker", v and v["preview"] == "ready" and copy.is_file(), v)
    pr = json.loads((s.kit / ".kit" / "footage" / k / "preview.json").read_text()) if copy.is_file() else {}
    case("its state on disk says so (copy: preview.mp4)", pr.get("state") == "ready" and pr.get("copy") == "preview.mp4", pr)
    code, _, raw = s.http("GET", "/reel-video?kit=%s&key=%s" % (KQ, k), headers={"Range": "bytes=0-"})
    case("the player is handed the copy (206), not the original", code == 206 and copy.is_file() and raw == copy.read_bytes() and raw != np_.read_bytes(), code)
    cf = R._video().facts(copy) if copy.is_file() else {}
    case("the copy is H.264 8-bit 4:2:0, never enlarged (640 x 360 stays)", cf.get("plays_as_is") and (cf.get("w"), cf.get("h")) == (640, 360), cf)
    t_before = pr.get("t")
    _, j2, _ = foot(s)
    case("asked again, nothing is made again", json.loads((s.kit / ".kit" / "footage" / k / "preview.json").read_text()).get("t") == t_before
         and sorted(os.listdir(s.kit / ".kit" / "footage" / k)) == ["preview.json", "preview.mp4", "strip"])

    # moments, through the server
    code, j, _ = moment(s, {"do": "add", "video": a["key"], "start": 1.0, "seconds": 4})
    m = (j or {}).get("moments", [{}])[0]
    case("Use this moment: a 4-second moment of theirs, first, labelled her way", code == 200 and m.get("by") == "you" and m.get("start") == 1.0
         and m.get("end") == 5.0 and m.get("label") == "Your pick at 0:01" and m.get("key") == a["key"] and m.get("name") == "clip.mov"
         and re.fullmatch(r"u1-[0-9a-f]{6}", m.get("id", "")), j)
    code, _, raw = s.http("GET", "/reel-moment-still?kit=%s&id=%s" % (KQ, m.get("id")))
    case("its card's still is made (a JPEG from its middle)", code == 200 and raw[:3] == b"\xff\xd8\xff"
         and (s.kit / ".kit" / "footage" / "moments" / m["id"]).is_dir(), code)
    rec = record(s)
    case("saved in the record under her name for it, the video by its file name only",
         [x["video"] for x in rec.get("moments", [])] == ["clip.mov"] and rec["moments"][0]["start"] == 1.0, rec.get("moments"))
    code, j, _ = moment(s, {"do": "update", "id": m["id"], "end": 5.5})
    case("+ : half a second longer", code == 200 and j["moments"][0]["end"] == 5.5 and j["moments"][0]["set"] is True, j)
    code, j, _ = moment(s, {"do": "update", "id": m["id"], "end": 9.0})
    case("never past the end of its video (6 s)", code == 200 and j["moments"][0]["end"] == 6.0, j)
    code, j, _ = moment(s, {"do": "update", "id": m["id"], "end": 1.2})
    case("never under a second (hers)", code == 200 and j["moments"][0]["end"] == 2.0, j)
    moment(s, {"do": "update", "id": m["id"], "end": 5.0})
    code, j, _ = moment(s, {"do": "remove", "id": m["id"]})
    rec = record(s)
    case("Remove: gone from the moments, kept in the record (nothing lost)", code == 200 and j["moments"] == []
         and [r["moment"]["id"] for r in rec.get("removed", [])] == [m["id"]], (j, rec.get("removed")))
    code, j, _ = moment(s, {"do": "restore", "id": m["id"], "at": 0})
    case("Undo: put back where it was, from what the Assistant kept (the page sends only its id)",
         code == 200 and [x["id"] for x in j["moments"]] == [m["id"]] and j["moments"][0]["end"] == 5.0 and not record(s).get("removed"), j)
    prev = s.kit / ".kit" / "reel-page.prev.json"
    case("the record is written whole with the version before kept beside it", prev.is_file() and json.loads(prev.read_text()).get("moments") == [], prev.exists())

    # refusals
    bad = [("an unknown video", {"do": "add", "video": "0" * 12, "start": 1}, 400, "That video isn't in this shoot's Footage folder."),
           ("a path for the video", {"do": "add", "video": "Footage/clip.mov", "start": 1}, 400, "That video isn't in this shoot's Footage folder."),
           ("a moment that isn't there", {"do": "update", "id": "u9-abcdef", "end": 3}, 400, "That moment isn't there anymore. Reload the page."),
           ("putting back one never removed", {"do": "restore", "id": "u9-abcdef"}, 400, "That moment can't be put back."),
           ("an id not her shape", {"do": "remove", "id": "../x"}, 400, None),
           ("a field it doesn't know", {"do": "add", "video": a["key"], "start": 1, "path": "/tmp/x.mov"}, 400, None),
           ("a do it doesn't know", {"do": "delete", "id": m["id"]}, 400, None),
           ("a start that is not a number", {"do": "add", "video": a["key"], "start": "1"}, 400, None)]
    for name, body, want_code, words in bad:
        code, j, _ = moment(s, body)
        case("refused: %s%s" % (name, ", in her words" if words else ""), code == want_code and j and j["ok"] is False
             and (words is None or j["words"] == words), (code, j))
    code, j, _ = s.http("POST", "/reel-moment", {"kit": KIT, "do": "remove", "id": m["id"]}, headers={"Origin": "http://evil.example"})
    case("refused: a moment change from another site's page (403), nothing changed", code == 403 and len(record(s)["moments"]) == 1, code)
    for path in ("/reel-footage?kit=" + KQ, "/reel-video?kit=%s&key=%s" % (KQ, a["key"])):
        code, _, _ = s.http("GET", path, headers={"Sec-Fetch-Site": "cross-site"})
        case("refused: %s asked for by another site (403)" % path.split("?")[0], code == 403, code)
        code, _, _ = s.http("GET", path, headers={"Host": "evil.example:%d" % s.port})
        case("refused: %s under another name (403)" % path.split("?")[0], code == 403, code)
    for name, path in (("a key not its shape", "/reel-video?kit=%s&key=..%%2Fx" % KQ), ("a key of no video", "/reel-video?kit=%s&key=%s" % (KQ, "f" * 12)),
                       ("a still past the strip", "/reel-strip?kit=%s&key=%s&n=99" % (KQ, a["key"])), ("a still by name", "/reel-strip?kit=%s&key=%s&n=..%%2F..%%2Fkit.json" % (KQ, a["key"])),
                       ("a moment still by path", "/reel-moment-still?kit=%s&id=..%%2Fx" % KQ), ("a kit outside Your Content", "/reel-footage?kit=..%2F..")):
        code, _, _ = s.http("GET", path)
        case("refused: %s (404)" % name, code == 404, code)

    # the editor's clip (v27): up to 15 s, a start and an end together, a name from the chat that a trim keeps
    # (a pretend 30-second video: a copy of the 6 s clip with its length faked in facts.json, since nothing longer is made here)
    lp = s.kit / "Footage" / "Long pretend.mov"
    shutil.copy(clips["clip.mov"], lp)
    kl = R._video().key(lp)
    facts = json.loads(fj.read_text())
    facts[kl] = dict(facts[a["key"]], length=30.0)
    fj.write_text(json.dumps(facts))
    j = wait_ready(s)
    code, j, _ = moment(s, {"do": "add", "video": kl, "start": 2.0, "seconds": 16})
    lm = next((x for x in (j or {}).get("moments", []) if x.get("key") == kl), {})
    case("Add clip asks for 16 s: cut to 15 (her v27 cap; v19's was 8)", code == 200 and lm.get("start") == 2.0 and lm.get("end") == 17.0 and R.ADD_MAX == 15.0, lm)
    code, j, _ = moment(s, {"do": "update", "id": lm.get("id", "u9-abcdef"), "start": 5.0, "end": 4.0})
    case("a trim with its start past its end is refused whole, in plain words", code == 400 and (j or {}).get("words") == R.OUR_WORDS["trim_length"], j)
    code, j, _ = moment(s, {"do": "update", "id": lm.get("id", "u9-abcdef"), "start": 3.0, "end": 19.0})
    case("a trim of 16 s is refused whole (the editor never sends one; hers would bend it quietly)", code == 400 and (j or {}).get("words") == R.OUR_WORDS["trim_length"], j)
    code, j, _ = moment(s, {"do": "update", "id": lm.get("id", "u9-abcdef"), "start": 3.0, "end": 18.0})
    lm2 = next((x for x in (j or {}).get("moments", []) if x.get("key") == kl), {})
    case("a trim moves both ends (3.0 to 18.0, 15 s), and her \"Your pick at\" label follows the start", code == 200 and lm2.get("start") == 3.0 and lm2.get("end") == 18.0
         and lm2.get("label") == "Your pick at 0:03", lm2)
    nf = s.work / "names-server.json"
    nf.write_text(json.dumps({"clips": {lm.get("id", "u9-abcdef"): {"label": "A long look round"}}}))
    code, out = s.cmd("footage.py", "describe", KIT, "--file", str(nf))
    code2, j, _ = moment(s, {"do": "update", "id": lm.get("id", "u9-abcdef"), "start": 4.0, "end": 9.0})
    lm3 = next((x for x in (j or {}).get("moments", []) if x.get("key") == kl), {})
    case("a name from the chat (footage.py describe) is kept by a later trim (her Nov 16 rule); the page is told it is named",
         code == 0 and code2 == 200 and lm3.get("label") == "A long look round" and lm3.get("named") is True and lm3.get("start") == 4.0, (out[-200:], lm3))
    moment(s, {"do": "remove", "id": lm.get("id", "u9-abcdef")})
    lp.rename(s.work / "set aside" / "Long pretend.mov") if (s.work / "set aside").is_dir() else lp.rename(s.work / "Long pretend.mov")
    case("(the pretend video taken out again: three videos)", wait_ready(s) and len(foot(s)[1]["videos"]) == 3)

    # a Footage folder that is a link: never listed, never opened
    real = s.kit / "Footage"
    real.rename(s.kit / "Footage-real")
    os.symlink(str(s.kit / "Footage-real"), str(real))
    try:
        code, j, _ = foot(s)
        case("a Footage folder that is a link: no videos listed from it", code == 200 and j["videos"] == [] and j["folder"] is False, j)
        code, j, _ = s.http("POST", "/reel-open", {"kit": KIT, "what": "footage"})
        case("and Add my footage won't open it, in her words", code == 200 and j == {"ok": False, "words": "Could not open the folder. Ask your assistant to open it."}, j)
    finally:
        real.rename(s.kit / "Footage link (test)")
        (s.kit / "Footage-real").rename(real)
    code, j, _ = foot(s)
    case("(the real folder back: three videos)", len(j["videos"]) == 3, j)


KEY_RE = re.compile(r"[0-9a-f]{12}")


# ---------- 2. her order for each style ----------

def her_footage_items():
    """Her server.py's footage_items, taken from her own file (never in the repository) and run here on a copy with
    stand-ins for her records. None when her handoff isn't on this computer."""
    f = rpc.her_folder()
    if not f:
        return None
    src = (f / "server.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "footage_items")
    mod = ast.Module(body=[fn], type_ignores=[])
    return compile(mod, "her server.py", "exec")


def run_hers(code, moments, style, clips, picks, photos, videos, tmp):
    """Her pieces, as (picks text with c1.., clips list) in reel.py's own words, from her footage_items."""
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "photos.json").write_text(json.dumps([{"n": n, "w": 1080, "h": 1350} for n in photos]))
    originals = {n: "/photo/%d.jpg" % n for n in photos}
    fake_fm = types.ModuleType("footage")
    fake_fm.probe = lambda p: dict(videos[Path(p).name])
    g = {"reel_rec": lambda name: {"moments": moments}, "shoot_dir": lambda name: "/shoot", "prepare": lambda name: (str(tmp), originals),
         "FOOTAGE_STYLES": ("first", "reveal", "backforth", "bookends"), "json": json, "os": os, "open": open}
    saved = sys.modules.get("footage")
    sys.modules["footage"] = fake_fm
    try:
        exec(code, g)
        try:
            items = g["footage_items"]("shoot", {"style": style, "clips": clips}, picks)
        except ValueError as e:
            return ("problem", str(e)), None
    finally:
        if saved is None:
            sys.modules.pop("footage", None)
        else:
            sys.modules["footage"] = saved
    back = {v: k for k, v in originals.items()}
    toks, entries = [], []
    for it in items:
        if it["kind"] == "clip":
            entries.append({"path": Path(it["path"]).name, "src": it["src"], "seconds": it["seconds"], "w": it["w"], "h": it["h"], "length": it["length"]})
            toks.append("c%d" % len(entries))
        else:
            toks.append("%d%s" % (back[it["path"]], it["mark"]))
    return ",".join(toks), entries


def run_ours(moments, style, clips, picks, photos, videos):
    R = rp()
    vids = [{"name": n, "path": Path("/shoot/Footage") / n, "facts": dict(f, plays_as_is=True)} for n, f in videos.items()]
    order = [(int(x.rstrip("+-")), x[-1] if x[-1] in "+-" else "") for x in picks.split(",") if x]
    try:
        toks, entries = R.footage_order(Path("/shoot"), {"moments": moments}, style, clips, order, set(photos), vids)
    except R.NoFootage as e:
        return ("problem", str(e)), None
    return toks, [{"path": Path(e["path"]).name, "src": e["src"], "seconds": e["seconds"], "w": e["w"], "h": e["h"], "length": e["length"]} for e in entries]


def check_editor_words():
    """reel_page.EDITOR_WORDS against her v27 reel-maker.html, both ways: every word of ours is in her page, and
    every line her editor's markup shows or names is one of ours, whole; her style rules for the editor are in
    the page as she wrote them."""
    import html as _html
    R = rp()
    W = R.EDITOR_WORDS
    case("the editor's words are in their own table (reel_page.EDITOR_WORDS, %d lines), none says Claude, none has a long dash" % len(W),
         len(W) >= 50 and not [v for v in W.values() if "Claude" in v or "—" in v or "–" in v])
    case("the old players' words are not on the page any more: no Use this moment, no Watch your footage, no Trim on a card, no Select your clips",
         not any(x in R.page_html("x", "x", True, "bts").split("id='reelData'")[0] for x in ("Use this moment", "Watch your footage and pick your own", "&#9986; Trim", "Select your clips", "id='viewers'")))
    hers = rpc.her_v27_page()
    if hers is None:
        print("SKIP  her editor words against her v27 page: that handoff isn't on this computer", flush=True)
        return
    text = re.sub(r"\\u([0-9a-f]{4})", lambda m: chr(int(m.group(1), 16)), _html.unescape(hers).replace("\\'", "'"))   # her '\u2713 Added'
    bad = [(k, frag) for k, v in W.items() for frag in re.split(r"\{\w+\}", v) if len(frag.strip()) >= 2 and frag not in text]
    case("every word of ours for the editor is in her v27 reel page, word for word", not bad, bad)
    block = re.search(r"<!-- the footage editor \(Nicole, Nov 16.*?<div class=\"moments row\" id=\"moments\" hidden>", hers, re.S)
    case("her editor's markup is in her page where ours is: under the line to copy in step 1", block is not None)
    if block:
        b = block.group(0)
        her_bits = [_html.unescape(x).strip() for x in re.findall(r">([^<>]+)<", b) if x.strip()] + re.findall(r'(?:title|aria-label)="([^"]+)"', b)
        her_bits = [x for x in her_bits if x not in ("0:00.0", "Name my clips", "▶")]      # the time, a line the page fills in, her glyph-only ▶ (ours carries the same glyph)
        ours = [v.strip() for v in list(W.values()) + [R.WORDS["copy"]]]
        case("every line her editor's markup shows or names (%d) is one of ours, whole" % len(her_bits), len(her_bits) >= 16 and not [x for x in her_bits if x not in ours],
             [x for x in her_bits if x not in ours])
        her_ids = re.findall(r'id="(ed\w*|vpBtn|clist|descBox|descWords|descCopy|momentsSay)"', b)
        page = R.page_html("x", "x", True, "bts")
        case("every part of her editor is in ours, by her name (%d of them)" % len(her_ids), len(her_ids) >= 20 and all(("id='%s'" % i) in page for i in her_ids if i not in ("edR0", "edR1")),
             [i for i in her_ids if ("id='%s'" % i) not in page])
    for line in ("'That\\'s 15 seconds, the longest a clip can be. Drag its ends to change it, or press Add clip.'",
                 "'Added to your clips. <b>To make another</b>, drag the orange trim to a new moment (or drag its ends), then press <b>Add clip</b>. Or find a moment and press <b>Start here</b>.'",
                 "'The end has to be at least a second after the start.'", "'Make it at least a second long first.'", "'Adding your clip…'",
                 "'Show the whole video' : 'Zoom in'", "'Not named yet'", "'Name my clips for ' + short", "&#9654; Play this clip", "'Take it out of your reel' : 'Use it in your reel'",
                 "'No photo' : on ? '&#10003; In reel' : 'Use'", "title=\"Remove this clip\"", "Your clips show up here: the moments I find, and the ones you add.</p>'",
                 "Choose the clips you\\'d like in your B-roll reel. They play in the order shown, each cut on the beat."):
        case("her line is in her page as ours has it: %s" % line[:50], line in hers, line)
    case("her 15 s cap, her 4 px tap rule and her tenth-of-a-second rounding are ours",
         "Math.min(edT(), ED.inT + 15" in hers and "Math.abs(ev.clientX - d.sx) > 4" in hers and "Math.round(ED.inT * 10) / 10" in hers or "Math.round(edT() * 10) / 10" in hers
         and R.ADD_MAX == 15.0 and R.TAP_PX == 4)
    sty = re.search(r"<style>(.*?)</style>", hers, re.S).group(1)
    # left out: her first editor's tabs (.edtabs, .edmain, .edside, .edbin), the description she took out (.ci .about), her
    # serif on the Name my clips line, and her first .tcut rule (white and dashed), which her orange one further down replaces
    skip = (".edtabs", ".edmain", ".edside", ".edbin", ".ci .about", ".descline #descWords", ".edruler{", "@media (max-width:900px){.edmain",
            ".tcut{position:absolute;top:0;bottom:0;border:2px dashed #fff")
    her_css = [ln for ln in sty.splitlines() if ln.startswith((".ed", ".tm", ".tcut", "#edIn", ".vp", ".cl-head", ".clist", ".ci", ".descline", ".wl{", ".say.sm{", "@media (max-width:820px){.edgrid"))
               and not ln.startswith(skip)]
    missing = [ln[:70] for ln in her_css if ln not in R.EDITOR_CSS and (ln.split("}")[0] + "}") not in R.EDITOR_CSS]
    case("her style rules for the editor are in the page as she wrote them (%d of them; her first editor's tabs and the description she took out left out)" % len(her_css),
         len(her_css) >= 60 and not missing, missing)
    case("her .edruler rule is ours too (the one line her file has twice)", any(ln in R.EDITOR_CSS for ln in sty.splitlines() if ln.startswith(".edruler{")))
    case("the Name my clips line is DM Sans in ours (Dustin: no serif), where hers is Fraunces", ".descline #descWords{font:500 15.5px/1.3 var(--sans);color:var(--ink)}" in R.EDITOR_CSS
         and "var(--display)" not in R.EDITOR_CSS)


def check_order(run):
    code = her_footage_items()
    if code is None:
        print("SKIP  her clip order for each style: her handoff (reference-private) isn't on this computer", flush=True)
    videos = {"IMG_1.MOV": {"w": 1080, "h": 1920, "length": 30.5}, "IMG 2 é.mov": {"w": 1920, "h": 1080, "length": 12.0}}
    M = [{"id": "m1-aaaaaa", "video": "Footage/IMG_1.MOV", "start": 2.5, "end": 6.5, "label": "One", "photo": None, "keep": True},
         {"id": "m2-bbbbbb", "video": "Footage/IMG_1.MOV", "start": 10.0, "end": 13.2, "label": "Two", "photo": 4, "keep": True},
         {"id": "u1-cccccc", "video": "Footage/IMG 2 é.mov", "start": 1.0, "end": 5.0, "label": "Your pick at 0:01", "photo": None, "keep": True, "by": "you"},
         {"id": "m3-dddddd", "video": "Footage/IMG 2 é.mov", "start": 7.0, "end": 9.5, "label": "Three", "photo": 9, "keep": False}]
    photos = list(range(1, 13))
    picks = "3,1+,7,4,12-,9,2,5+"
    cases = []
    for style in ("first", "reveal", "backforth", "bookends"):
        for clips in (None, [], ["m1-aaaaaa"], ["u1-cccccc", "m2-bbbbbb"], ["m3-dddddd", "m1-aaaaaa", "m2-bbbbbb"], [m["id"] for m in M]):
            cases.append((style, clips, M))
    cases.append(("reveal", ["m1-aaaaaa", "u1-cccccc"], M))       # no matching photo among them
    cases.append(("first", None, []))                                # no moments at all
    cases.append(("bookends", ["u1-cccccc"], M))                     # one clip: in twice
    same, diff = 0, []
    for style, clips, ms in cases:
        ours = run_ours(ms, style, clips, picks, photos, videos)
        if code is not None:
            hers = run_hers(code, ms, style, clips, picks, photos, videos, run / "her-order")
            if ours == hers:
                same += 1
            else:
                diff.append((style, clips, ours, hers))
    if code is not None:
        case("every style builds the clip order hers would: %d cases (clips selected or not, none matching, no moments, one clip)" % len(cases),
             not diff and same == len(cases), diff[:2])
    toks, entries = run_ours(M, "bookends", ["u1-cccccc"], picks, photos, videos)
    case("Bookends with one clip puts it in twice, as c1 and c2 (each its own entry)", toks.startswith("c1,") and toks.endswith(",c2")
         and len(entries) == 2 and entries[0] == entries[1] and entries[0]["src"] == 1.0, (toks, entries))
    toks, entries = run_ours(M, "backforth", ["m1-aaaaaa", "m2-bbbbbb", "u1-cccccc"], picks, photos, videos)
    case("Back and forth: a clip, two photos, the next clip... then the rest (hers)", toks == "c1,3,1+,c2,7,4,c3,12-,9,2,5+", toks)
    toks, _ = run_ours(M, "reveal", ["m2-bbbbbb", "m3-dddddd"], picks, photos, videos)
    case("The reveal: each moment then its photo held longer, then the other photos without those two (hers)", toks == "c1,4+,c2,9+,3,1+,7,12-,2,5+", toks)
    case("Back and forth with nothing selected yet (the chat's make) takes the first two clips she would keep",
         run_ours(M, "backforth", None, picks, photos, videos)[0] == "c1,3,1+,c2,7,4,12-,9,2,5+")


# ---------- 3. Make my reel with footage: the server's order against reel.py straight from hers ----------

def check_make(s, run):
    R = rp()
    st = s.state()
    a = next(v for v in foot(s)[1]["videos"] if v["name"] == "clip.mov")
    b = next(v for v in foot(s)[1]["videos"] if v["name"] == "Sideways é.mov")
    # a moment of Claude's (as the footage look writes it, matched to photo 5), beside theirs
    rec = record(s)
    rec["moments"] = rec.get("moments", []) + [{"id": "m1-0a0b0c", "video": "Footage/Sideways é.mov", "start": 0.5, "end": 4.0,
                                                 "label": "Walking in", "photo": 5, "keep": True}]
    (s.kit / ".kit" / "reel-page.json").write_text(json.dumps(rec))
    music = s.kit / "Music"
    music.mkdir(exist_ok=True)
    shutil.copy(rpc.BEAT60, music / "Test beat.wav")
    sid = rpc.song_of(s, KIT, "Test beat")
    picks = "3,1+,7,4,12-,9,2,10+"
    page_picks = rpc.pk(picks)
    clips_all = [m["id"] for m in R.moments_of(record(s))]
    case("(set up: a moment of theirs and one of Claude's, the test beat in Music)", len(clips_all) == 2 and sid, clips_all)
    code = her_footage_items()
    for style, clips in (("first", clips_all[:1]), ("backforth", clips_all), ("reveal", clips_all), ("bookends", clips_all), ("bookends", clips_all[1:])):
        (_, _), job = make_with(s, page_picks, sid, "beat", style, clips)
        got = rpc.beats_of(job)
        if code is None:
            print("SKIP  reel.py straight from her order (%s): her handoff isn't on this computer" % style, flush=True)
            case("a dry run with footage (%s) through Make my reel makes a plan" % style, got and got.startswith("Beats per piece"), job)
            continue
        vids = {v["name"]: R._video().facts(s.kit / "Footage" / v["name"]) for v in (a, b)}
        hers, entries = run_hers(code, record(s)["moments"], style, clips, picks, list(range(1, PHOTOS + 1)), vids, run / "her-make")
        cf = run / ("clips-%s-%d.json" % (style, len(clips)))
        cf.write_text(json.dumps([dict(e, path=str(s.kit / "Footage" / e["path"])) for e in entries]))
        r = subprocess.run([sys.executable, str(REEL / "reel.py"), "make", "--dry-run", "--folder", str(s.kit / "Photos"), "--shoot", KIT,
                            "--kit", str(s.kit), "--picks", hers, "--vibe", "beat", "--song", str(music / "Test beat.wav"), "--variation", "0",
                            "--clips", str(cf)], capture_output=True, text=True, env=s.env, timeout=120)
        line = next((x for x in r.stdout.splitlines() if x.startswith(("Beats per piece", "STOP"))), r.stdout[-200:])
        case("%s (%d clip%s): Make my reel's dry run gives the same Beats per piece line as reel.py --clips straight from her order"
             % (style, len(clips), "s" if len(clips) != 1 else ""), got == line and got.startswith("Beats per piece"), "page: %s / hers: %s" % (got, line))
        if style == "first":
            case("and her Plan line, \"1 clip and 8 photos\", and the clip's line (hers: \" clip from \")",
                 job["words"][0].startswith("Plan: 1 clip and 8 photos, ") and any(" clip from clip.mov at 1.0 s" in w for w in job["words"]), job["words"][:3])
            case("no path in what the page is told", no_path(job), job)
            cl = json.loads((s.kit / ".kit" / "reels" / "clips.json").read_text())
            case("the clips were written to <kit>/.kit/reels/clips.json for --clips", [c["moment"] for c in cl["clips"]] == clips_all[:1], cl)
    (_, _), job = make_with(s, page_picks, sid, "beat", "reveal", [clips_all[0]])
    case("The reveal with no moment matched to a photo: her words", job and job["state"] == "problem" and job["problem"] ==
         "The reveal needs footage moments that match one of your final photos, and none of these do. Try Moment first or Back and forth.", job)
    (_, _), job = make_with(s, page_picks, sid, "beat", "backforth", [])
    case("no clip selected: her words", job and job["problem"] == "Select the clip or clips to use for this style.", job)
    code_, j, _ = s.http("POST", "/reel-make", {"kit": KIT, "stamp": st["stamp"], "picks": page_picks, "song": sid, "vibe": "beat", "test": True,
                                               "footage": True, "style": "first", "clips": ["../x"]})
    case("refused: a clip that is not a moment id", code_ == 400 and j["ok"] is False, (code_, j))
    code_, j, _ = s.http("POST", "/reel-make", {"kit": KIT, "stamp": st["stamp"], "picks": page_picks, "song": sid, "vibe": "beat", "test": True,
                                               "footage": True, "style": "sideways"})
    case("refused: a style she hasn't got", code_ == 400, (code_, j))
    # Claude's make from the chat follows the page: footage on, the style and clips selected there
    code_, j, _ = s.http("POST", "/reel-save", rpc.save_body(s.state(), {"picks": page_picks, "mine": True, "song": sid, "vibe": "beat", "footage": True,
                                                                          "style": "bookends", "sel": {"bookends": clips_all}}, page="makepage1"))
    rc, out = s.cmd("reel_page.py", "make", KIT, "--dry-run")
    case("Claude's make from the chat uses the page's footage, style and clips (Bookends here)", rc == 0 and "Plan: 2 clips and 8 photos" in out, out[-300:])
    rc, out = s.cmd("reel_page.py", "show", KIT)
    case("reel_page.py show says footage, the style, the clips and the videos", "Footage: yes, Bookends, 2 clips selected" in out
         and "In the Footage folder: 3 videos" in out, out)


def make_with(s, picks, song, vibe, style, clips):
    st = s.state()
    body = {"kit": KIT, "stamp": st["stamp"], "picks": picks, "song": song, "vibe": vibe, "test": True, "footage": True, "style": style, "clips": clips}
    code, j, _ = s.http("POST", "/reel-make", body)
    if code != 200 or not (j or {}).get("job"):
        return (code, j), None
    jid = j["job"]["id"]
    end = time.time() + 120
    while time.time() < end:
        _, j2, _ = s.http("GET", "/reel-job?kit=%s&id=%s" % (KQ, jid))
        job = (j2 or {}).get("job")
        if job and job["state"] in ("done", "problem"):
            return (code, j), job
        time.sleep(0.3)
    return (code, j), None


# ---------- 4. the page ----------

def texts1(c):
    return c.js("""(function(){
      function h(id){ var x = document.querySelector('#' + id + ' h2').cloneNode(true); x.querySelector('.num').remove(); return x.textContent; }
      var lab = document.querySelector('#btsBox label').cloneNode(true); lab.querySelectorAll('.ex').forEach(function(e){ e.remove(); });
      var b = lab.querySelector('b'); var bt = b.textContent; b.remove();
      return {h2: h('step0'), oldcards: document.querySelectorAll('#step0 .choice, #modeBts, #modePhotos, #modeTalk').length,
        say2: document.querySelector('#btsBox > p.say').innerHTML, add: document.getElementById('addFootage').textContent,
        insight_b: document.querySelector('.insight > b').textContent, insight: document.getElementById('insightWords').textContent,
        fix: document.querySelectorAll('.insight p')[1].innerHTML, paste_say: document.querySelector('#pasteBox > p').textContent,
        copy: document.getElementById('copyLine').textContent, paste: document.getElementById('pasteWords').textContent,
        ask_b: bt, ask: lab.textContent, ex1: document.querySelectorAll('#btsBox .ex')[0].textContent, ex2: document.querySelectorAll('#btsBox .ex')[1].textContent,
        ask_ph: document.getElementById('askIn').placeholder, ask_max: document.getElementById('askIn').maxLength,
        feel_b: document.querySelector('#feelRow > b').textContent,
        feels: Array.from(document.querySelectorAll('#feelRow button')).map(function(x){ return x.textContent; }),
        feel_ph: document.getElementById('feelOwn').placeholder, feel_max: document.getElementById('feelOwn').maxLength,
        feel_small: document.querySelector('#feelRow small').innerHTML,
        moments_say: document.getElementById('momentsSay').textContent,
        h2s: h('stepStyle'), says: document.querySelector('#stepStyle > p.say').textContent,
        cards: Array.from(document.querySelectorAll('#styles .opt')).map(function(x){ return [x.querySelector('b').textContent, x.querySelector('span').textContent]; }),
        nums: Array.from(document.querySelectorAll('section.step')).filter(function(s){ return !s.hidden; }).map(function(s){ return s.id + '=' + s.querySelector('.num').textContent; }),
        feel_hidden: document.getElementById('feelRow').hidden, ask_first: document.getElementById('askIn').getBoundingClientRect().top < document.getElementById('pasteWords').getBoundingClientRect().top,
        box_hidden: document.getElementById('btsBox').hidden, style_hidden: document.getElementById('stepStyle').hidden,
        rec_shown: !document.getElementById('claudeRec').hidden, done0: document.getElementById('step0').classList.contains('done'),
        waiting: document.getElementById('footWaiting').textContent, vlist: document.getElementById('vlist').textContent,
        vsum: (function(){ var su = document.querySelector('#vlist summary'); return su ? su.querySelector('b').textContent + ' ' + su.querySelector('small').textContent.replace(/\\s+/g, ' ').trim() : ''; })(),
        vcards: Array.from(document.querySelectorAll('#vlist .vcard')).map(function(v){ return v.querySelector('b').textContent + ' ' + v.querySelector('small').textContent.replace(/\\s+/g, ' ').trim(); }),
        sum: document.getElementById('sum').textContent, result: document.getElementById('result').innerHTML};
    })()""")


def on_disk(s, fn, seconds=6):
    try:
        chrome_drive.wait_until(lambda: fn(record(s)), seconds, what="the record")
        return True
    except Exception:  # noqa: BLE001
        return False


def wait(c, cond, seconds=8):
    try:
        c.wait_for(cond, seconds)
        return True
    except Exception:  # noqa: BLE001
        return False


def click_into(c, sel, seconds=30):
    """Press a box to type in, once the page has stopped moving, and be sure the keyboard is in it. Make my reel's
    answer glides into view by itself (the page's own smooth scroll, hers); on a slow computer that glide is still
    going when the next press is aimed, and carries the box out from under it, so what is typed goes nowhere
    (GitHub's slow Mac, Nov 17: nothing was saved because nothing was typed). A person presses what they see."""
    end = time.time() + seconds
    while True:
        y, still = c.js("window.scrollY"), time.time()
        while time.time() - still < 0.5 and time.time() < end:      # still for half a second: the glide is over
            time.sleep(0.05)
            now = c.js("window.scrollY")
            if now != y:
                y, still = now, time.time()
        c.click(sel)
        if c.js("document.activeElement === document.querySelector(%s)" % json.dumps(sel)) or time.time() >= end:
            return


def check_page(c, s, clips):
    sid = rpc.song_of(s, KIT, "Test beat")
    # start from a record with no footage choice yet: their 8 photos, the song picked
    rec = record(s)
    rec["saved"] = {"picks": rpc.pk("3,1+,7,4,12-,9,2,10+"), "mine": True, "song": sid, "vibe": "beat"}
    rec["rev"] = int(rec.get("rev") or 0) + 1
    rec.pop("from", None)
    (s.kit / ".kit" / "reel-page.json").write_text(json.dumps(rec))
    c.init_script("document.addEventListener('copy', function(){ window.__copied = String(window.getSelection()); }, true);")
    c.open(s.page_url("bts"))                 # v27: a behind-the-scenes page (the chooser decides the kind)
    c.wait_for("document.querySelectorAll('#reel .tile').length === 8 && document.querySelectorAll('#songSel option').length > 1", 20)
    t = texts1(c)
    case("a behind-the-scenes page (v27): no yes/no cards, the box and step 4 show at once, her renumbering 1 to 7, the recommended tag",
         t["oldcards"] == 0 and not t["box_hidden"] and not t["style_hidden"] and t["rec_shown"]
         and t["nums"] == ["step0=1", "step1=2", "step3=3", "stepDirect=4", "stepStyle=5", "step4=6", "watch=7"], {k: t[k] for k in ("oldcards", "box_hidden", "style_hidden", "rec_shown", "nums")})
    case("her words, step 1: h2 (v27)", t["h2"] == HERS1["h2"], (t["h2"], HERS1["h2"]))
    case("the ask box comes before the line to copy, and How should it feel? is hidden (hers, v27)", t["ask_first"] and t["feel_hidden"])
    # with no clips yet (the server part's moments set aside for a moment): her box
    rec = record(s)
    keep_m = rec.get("moments")
    rec["moments"] = []
    rec["rev"] = int(rec.get("rev") or 0) + 1
    (s.kit / ".kit" / "reel-page.json").write_text(json.dumps(rec))
    c.js("window.Reel.followNow()")
    wait(c, "document.querySelectorAll('#clist .ci').length === 0", 8)
    c.click("#makeBtn")
    case("Make my reel before any footage is in: her \"I haven't looked through your footage yet\" box", wait(c, "document.getElementById('result').innerHTML === %s" % json.dumps(HERS_MAKE["not_looked"]), 5),
         texts1(c)["result"])
    rec = record(s)
    rec["moments"] = keep_m
    rec["rev"] = int(rec.get("rev") or 0) + 1
    (s.kit / ".kit" / "reel-page.json").write_text(json.dumps(rec))
    c.js("window.Reel.followNow()")
    wait(c, "document.querySelectorAll('#clist .ci').length > 0", 8)
    click_into(c, "#askIn")
    c.type_text("x")
    c.key("Backspace")
    case("saved on the first change, with footage on and the kind (v27: nothing is written on a plain open)",
         on_disk(s, lambda r: (r.get("saved") or {}).get("footage") is True and (r.get("saved") or {}).get("kind") == "bts", 15),
         # what a slow computer left instead: the record's saved part, its rev, and what the page was saying
         (record(s).get("saved"), record(s).get("rev"), c.js("(document.getElementById('notice') || {}).textContent || ''"),
          c.js("document.querySelectorAll('#clist .ci').length")))
    for k in ("say2", "add", "insight_b", "fix", "paste_say", "copy", "ask_b", "ask", "ex1", "ex2", "ask_ph", "feel_b", "feels", "feel_ph",
              "feel_small"):
        case("her words, step 1: %s" % k, t[k] == HERS1[k], (t[k], HERS1[k]))
    case("her words, step 4: the heading, the line, the four styles in her order",
         t["h2s"] == HERS4["h2"] and t["says"] == HERS4["say"] and t["cards"] == HERS4["cards"], (t["h2s"], t["cards"]))
    case("her limits on the boxes: 600 and 40 characters", t["ask_max"] == 600 and t["feel_max"] == 40, (t["ask_max"], t["feel_max"]))
    case("Good to know with three 6-second videos: her line for up to 3 minutes", wait(c, "document.getElementById('insightWords').textContent === %s"
         % json.dumps("You've added 0:18 of footage. That takes me about a minute or two to look through, and longer footage uses more of your plan."), 8),
         texts1(c)["insight"])
    case("the videos fold into one drop-down (v27): '3 videos added', '0:18 of footage · all ready to watch below' once their previews are made",
         wait(c, "document.querySelectorAll('#vlist .vcard').length === 3 && (document.querySelector('#vlist summary') || {}).innerText.indexOf('all ready to watch below') > 0", 30)
         and texts1(c)["vsum"] == "3 videos added 0:18 of footage · all ready to watch below", texts1(c)["vsum"])
    case("...which opens to the cards, each with its length, size and that it is ready (hers)",
         texts1(c)["vcards"] == ["Not plain.mov 0:06 · 0 MB · ready to watch below", "Sideways é.mov 0:06 · 0 MB · ready to watch below", "clip.mov 0:06 · 0 MB · ready to watch below"], texts1(c)["vcards"])
    case("the drop-down is closed to begin with, and step 1 is done once videos are in", c.js("!document.querySelector('#vlist details').open") and texts1(c)["done0"])

    # Add my footage, and the list following a new file
    c.click("#addFootage")
    case("Add my footage: her words once the folder is open", wait(c, "document.getElementById('footWaiting').textContent === %s" % json.dumps(HERS1["opened"]), 6),
         texts1(c)["waiting"])
    shutil.copy(clips["clip.mov"], s.kit / "Footage" / "Dropped in.mov")
    case("a video dropped into the Footage folder shows up by itself (her 4 s look): '4 videos added', its card",
         wait(c, "Array.from(document.querySelectorAll('#vlist .vcard b')).some(function(x){ return x.textContent === 'Dropped in.mov'; }) && (document.querySelector('#vlist summary') || {}).innerText.indexOf('4 videos added') === 0", 8),
         texts1(c)["vsum"])
    case("and Good to know adds it up: 0:24", wait(c, "document.getElementById('insightWords').textContent.indexOf('0:24 of footage') > 0", 4), texts1(c)["insight"])
    # taken back out (kept beside the kit): the list follows that too, and the page plays three videos, not four
    aside = s.work / "set aside"
    aside.mkdir(exist_ok=True)
    (s.kit / "Footage" / "Dropped in.mov").rename(aside / "Dropped in.mov")
    case("a video taken out of the folder goes from the list",
         wait(c, "document.querySelectorAll('#vlist .vcard').length === 3 && document.getElementById('insightWords').textContent.indexOf('0:18 of footage') > 0", 8),
         texts1(c)["vlist"])

    # the line to copy, the notes and the feel
    case("the line to copy: \"Look through my footage for Fake beach\"", texts1(c)["paste"] == "Look through my footage for " + SHORT, texts1(c)["paste"])
    c.click("#copyLine")
    case("Copy: the line is copied with the page's own copy, and the button says Copied", c.js("window.__copied") == "Look through my footage for " + SHORT
         and texts1(c)["copy"] == "Copied", (c.js("window.__copied"), texts1(c)["copy"]))
    case("and back to Copy after a moment (hers: 1.6 s)", wait(c, "document.getElementById('copyLine').textContent === 'Copy'", 4))
    c.click("#askIn")
    c.type_text("Find the laugh")
    case("notes written: \" and follow my notes\" on the line", texts1(c)["paste"] == "Look through my footage for Fake beach and follow my notes", texts1(c)["paste"])
    case("saved: their notes (saved.ask)", on_disk(s, lambda r: (r.get("saved") or {}).get("ask") == "Find the laugh"))
    c.click("#copyLine")
    case("Copy with notes copies the longer line", c.js("window.__copied") == "Look through my footage for Fake beach and follow my notes", c.js("window.__copied"))
    c.set_value("#askIn", "")
    c.js("document.getElementById('askIn').dispatchEvent(new Event('input'))")
    case("notes cleared: the line goes back", texts1(c)["paste"] == "Look through my footage for " + SHORT and on_disk(s, lambda r: (r.get("saved") or {}).get("ask") == ""))
    # her v27 hides "How should it feel?": the row is written hidden, its buttons still work underneath (a feel
    # saved before v27 still counts, and the Assistant still reads it)
    c.js("document.getElementById('feelRow').hidden = false")
    c.click("#feelRow button[data-f='fun']")
    case("a feel (the row shown by hand): Fun marked, the line has the notes, saved as \"fun\"", c.js("document.querySelector(\"#feelRow button[data-f='fun']\").classList.contains('on')")
         and texts1(c)["paste"].endswith(" and follow my notes") and on_disk(s, lambda r: (r.get("saved") or {}).get("feel") == "fun"))
    c.click("#feelRow button[data-f='fun']")
    case("tapped again it clears (hers)", on_disk(s, lambda r: (r.get("saved") or {}).get("feel") == "") and texts1(c)["paste"] == "Look through my footage for " + SHORT)
    c.click("#feelOwnBtn")
    case("Something else: their own box opens", c.js("!document.getElementById('feelOwn').hidden && document.activeElement === document.getElementById('feelOwn')"))
    c.type_text("cozy and warm")
    case("their own words saved (saved.feel)", on_disk(s, lambda r: (r.get("saved") or {}).get("feel") == "cozy and warm"))
    st = s.state()
    for name, saved, ok in (("600 characters of notes", {"ask": "a" * 600}, True), ("601", {"ask": "a" * 601}, False),
                            ("a feel of 40 characters", {"feel": "b" * 40}, True), ("41", {"feel": "b" * 41}, False)):
        code, j, _ = s.http("POST", "/reel-save", rpc.save_body(st, saved, page="limits1"))
        if code == 200:
            st = s.state()
        case("the server takes %s" % name if ok else "the server refuses %s" % name, (code == 200) == ok, (code, j))
    s.http("POST", "/reel-save", rpc.save_body(s.state(), {"ask": "", "feel": "cozy and warm"}, page="limits2"))
    case("no errors on the page (steps 1 and 4)", not c.page_errors(), c.page_errors()[:3])



def cards(c):
    """Your clips, card by card (her .ci cards, v27)."""
    return c.js("""Array.from(document.querySelectorAll('#clist .ci')).map(function(m){
      var b = m.querySelector('b').cloneNode(true); var n = b.querySelector('.num'); var num = n ? n.textContent : ''; if (n) n.remove();
      return {id: m.dataset.mid, sel: m.classList.contains('sel'), edit: m.classList.contains('edit'), num: num, label: b.textContent,
        small: m.querySelector('small').textContent, use: m.querySelector('.cin').textContent, off: m.querySelector('.cin').disabled,
        use_title: m.querySelector('.cin').title, yours: (m.querySelector('.yours') || {}).textContent || '',
        img: !!(m.querySelector('img') && m.querySelector('img').getAttribute('src'))}; })""")


def ed(c):
    """The editor's state as numbers (window.Reel.editor), with what the page shows round it."""
    return c.js("""(function(){ var e = window.Reel.editor(); var cut = document.getElementById('edCut');
      e.say = document.getElementById('edSay').innerHTML; e.cutClass = cut ? cut.className : null; e.cutTag = cut ? cut.querySelector('b').textContent : null;
      e.addOff = document.getElementById('edAdd').disabled; e.addText = document.getElementById('edAdd').textContent;
      e.rec = document.getElementById('edIn').classList.contains('rec'); e.clearHidden = document.getElementById('edClear').hidden;
      e.win = document.getElementById('edWin').textContent; e.zoomText = document.getElementById('edZoom').textContent;
      e.time = document.getElementById('edTime').textContent; e.paused = document.getElementById('edVid').paused;
      e.marks = Array.from(document.querySelectorAll('#edMarks .tm')).map(function(t){ return [t.dataset.mid, t.className.trim(), (t.querySelector('i') || {}).textContent || '', !!t.querySelector('.hl')]; });
      e.sel = document.getElementById('edSel').hidden ? null : document.getElementById('edSel').innerText;
      e.desc = document.getElementById('descBox').hidden ? null : document.getElementById('descWords').textContent;
      e.vp = document.getElementById('vpBtn').innerText.replace(/\\s+/g, ' ').replace(/ ▾$/, '').trim(); return e; })()""")


def x_at(c, secs):
    """The window x of a second on the timeline, as it is zoomed now."""
    r = c.rect("#edTl")
    e = c.js("window.Reel.editor()")
    return r["x"] + (secs - e["w0"]) / (e["w1"] - e["w0"]) * r["w"]


def tl_y(c):
    return c.rect("#edTl")["cy"]


def near(a, b, by=0.16):
    return a is not None and b is not None and abs(float(a) - float(b)) <= by


def check_editor(c, s):
    """Her footage editor (v27, screenshots 13 to 16) on the page, driven with real pointer drags: the player and
    the Footage drop-down, scrubbing, Start here and End here with the three states of the orange trim, Add clip
    and the card with YOUR PICK and Not named yet, the trim that stays and moves to make the next clip, a clip
    picked by a click and trimmed on the timeline, a name from the chat that a trim keeps, Zoom in, Use and
    In reel, Remove and Undo, two columns at a desk and one on a phone."""
    R = rp()
    W = R.EDITOR_WORDS
    code, j, _ = s.http("POST", "/reel-save", rpc.save_body(s.state(), {"style": "first", "footage": True, "kind": "bts"}, page="editor0"))
    case("(set up: a behind-the-scenes reel, Moment first)", code == 200 and (j or {}).get("ok"), j)
    c.open(s.page_url("bts"))
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.editor().key", 20)
    ok = wait(c, "document.getElementById('edVid').readyState >= 1 && document.querySelectorAll('#clist .ci').length === 2", 15)
    e = ed(c)
    case("the editor opens on the first video that is ready to play, Not plain.mov (name order), its length under the Footage label and the three videos counted",
         ok and e["vp"] == "Not plain.mov 0:06 · 3 videos" and e["win"] == "Not plain.mov · 0:06" and e["zoomText"] == W["ed_zoom"] and e["time"] == "0:00.0 / 0:06", e)
    t = c.js("""({h3: Array.from(document.querySelectorAll('#btsBox h3.mh')).map(function(h){ return h.textContent; }),
                 say: document.getElementById('edSayTop').textContent, wait_hidden: document.getElementById('edWait').hidden,
                 wls: Array.from(document.querySelectorAll('#ed .wl')).map(function(x){ return x.textContent; }),
                 btns: ['edIn', 'edOut', 'edAdd', 'edClear', 'edZoom', 'edBack', 'edFwd', 'descCopy'].map(function(i){ return document.getElementById(i).textContent; }),
                 titles: ['edBack', 'edFwd'].map(function(i){ return document.getElementById(i).title; }),
                 tip: document.querySelector('#ed .edtip:not(.pcnote)').textContent, find: document.getElementById('edSay').textContent,
                 bigPlay: document.getElementById('edBig').getAttribute('aria-label'), desc: document.querySelector('#descBox > span').textContent,
                 pcnote: !!document.querySelector('#ed .pcnote'), oldrow: document.querySelectorAll('#moments, #viewers, .mom, .viewer, .usebtn').length})""")
    case("her words: the heading, the line under it, the three labels, the buttons, the tip, the first line of Make a clip, no PC note on a Mac",
         t["h3"] == [W["ed_h3"]] and t["say"] == W["ed_say"] and t["wait_hidden"] and t["wls"] == [W["ed_footage"], W["ed_make"], W["clips_wl"]]
         and t["btns"] == [W["ed_in"], W["ed_out"], W["ed_add"], W["ed_clear"], W["ed_zoom"], W["ed_back_b"], W["ed_fwd_b"], "Copy"]
         and t["titles"] == [W["ed_back"], W["ed_fwd"]] and t["tip"] == W["ed_tip"] and t["find"] == W["ed_find"] and t["bigPlay"] == W["ed_play"]
         and t["desc"] == W["desc_say"] and not t["pcnote"], t)
    case("the old players, strips and moment cards are gone from the page (hers hides them; ours does not draw them)", t["oldrow"] == 0, t["oldrow"])
    cs = cards(c)
    case("Your clips: every clip at once, theirs first with her YOUR PICK tag and Not named yet, Claude's with its name; video, start to end and length under each; Use or In reel",
         [x["yours"] for x in cs] == ["Your pick", ""] and cs[0]["label"] == W["not_named"] and cs[1]["label"] == "Walking in"
         and cs[0]["small"] == "clip.mov · 0:01.0–0:05.0 · 4.0 s" and cs[1]["small"] == "Sideways é.mov · 0:00.5–0:04.0 · 3.5 s"
         and [x["use"] for x in cs] == [W["in_reel"], W["use"]] and cs[0]["num"] == "1" and cs[0]["use_title"] == W["out_title"] and cs[1]["use_title"] == W["use_title"], cs)
    case("her line over the cards is the style's ask only (Moment first)", c.js("document.getElementById('momentsSay').textContent") == R.WORDS["pick_first"])
    case("the YOUR PICK tag is her purple, in capitals (her style rule)", c.js("(function(y){ var st = getComputedStyle(y); return [st.textTransform, st.color]; })(document.querySelector('#clist .yours'))") == ["uppercase", "rgb(90, 79, 168)"])
    case("Name my clips: her box shows while a clip of theirs is unnamed, with the line for this shoot", e["desc"] == "Name my clips for " + SHORT, e["desc"])
    c.click("#descCopy")
    case("Copy on it copies the line", c.js("window.__copied") == "Name my clips for " + SHORT and wait(c, "document.getElementById('descCopy').textContent === 'Copy'", 4), c.js("window.__copied"))
    own = cs[0]["id"]

    # the Footage drop-down
    c.click("#vpBtn")
    menu = c.js("[!document.getElementById('edTabs').hidden, Array.from(document.querySelectorAll('#edTabs [data-ek]')).map(function(b){ return b.innerText.replace(/\\s+/g, ' ').trim(); })]")
    case("Footage opens to the three videos, each with its length and clip count", menu[0] and menu[1] == ["Not plain.mov 0:06", "Sideways é.mov 0:06 · 1 clip", "clip.mov 0:06 · 1 clip"], menu)
    c.click("#edTabs [data-ek]", nth=2)
    ok = wait(c, "window.Reel.editor().key && document.getElementById('vpBtn').innerText.indexOf('clip.mov') === 0 && document.getElementById('edVid').readyState >= 1", 10)
    e = ed(c)
    case("clip.mov chosen: the player and the timeline are its; the menu closes", ok and e["win"] == "clip.mov · 0:06" and c.js("document.getElementById('edTabs').hidden")
         and c.js("document.getElementById('edVid').src.indexOf('/reel-video?') > 0 && Math.round(document.getElementById('edVid').duration) === 6"), e)
    case("their newest clip of this video is drawn on the timeline (1, selected) and, after a load, as the dashed ✓ Added trim with Add clip off (ours: nothing is added twice after a reload)",
         e["marks"] == [[own, "tm sel", "1", False]] and e["added"] == own and e["cutClass"] == "tcut set added" and e["cutTag"] == W["ed_added"] and e["addOff"] and e["addText"] == W["ed_added"]
         and e["say"] == W["ed_added_html"] and near(e["inT"], 1.0) and near(e["outT"], 5.0), e)
    case("the strip of stills along the timeline, from the video's own strip", c.js("document.querySelectorAll('#edThumbs img').length") >= 6
         and wait(c, "Array.from(document.querySelectorAll('#edThumbs img')).every(function(i){ return i.complete && i.naturalWidth > 0; })", 10))
    case("the ruler: a mark every second for a 6 s video", c.js("Array.from(document.querySelectorAll('#edRuler span')).map(function(x){ return x.textContent; })") == ["0:00", "0:01", "0:02", "0:03", "0:04", "0:05"])
    c.click("#edClear")
    e = ed(c)
    case("Clear: the trim goes, her first line is back, Clear is hidden", e["inT"] is None and e["cutClass"] is None and e["say"] == W["ed_find"] and e["clearHidden"] and e["addOff"], e)

    # scrubbing: a drag along the timeline moves the video, nothing is saved
    rev0 = record(s).get("rev")
    y = tl_y(c)
    c.drag((x_at(c, 1.0), y), (x_at(c, 3.0), y), steps=8)
    e = ed(c)
    case("dragging along the timeline scrubs: the video follows the hand (3.0 s), paused, the time says so, and nothing is saved",
         near(e["t"], 3.0, 0.25) and e["paused"] and e["time"].startswith("0:0") and e["drag"] is None and record(s).get("rev") == rev0, (e["t"], e["time"], e["drag"]))

    # Start here, the stretch grows, End here
    c.js("document.getElementById('edVid').currentTime = 1.0")
    wait(c, "Math.abs(document.getElementById('edVid').currentTime - 1) < 0.05", 3)
    c.click("#edIn")
    ok = wait(c, "!document.getElementById('edVid').paused && window.Reel.editor().inT === 1 && (document.getElementById('edCut') || {}).className === 'tcut live'", 6)
    e = ed(c)
    case("Start here at 1.0 s: the button turns orange, the video plays, a striped orange stretch starts there (her 'orange highlighted thing')",
         ok and e["rec"] and e["cutClass"] == "tcut live" and e["outT"] is None and not e["clearHidden"], e)
    ok = wait(c, "parseFloat((document.getElementById('edCut').querySelector('b').textContent || '0')) >= 1.0", 6)
    e = ed(c)
    case("...and grows to the playhead as it plays, its length on it (\"1.x s\") and her 'so far' line", ok and bool(re.fullmatch(r"\d+\.\d s", e["cutTag"] or ""))
         and e["say"] == W["ed_sofar_html"].replace("{secs}", (e["cutTag"] or " ").split(" ")[0]), e)
    c.js("var v = document.getElementById('edVid'); v.pause(); v.currentTime = 3.0;")
    wait(c, "Math.abs(document.getElementById('edVid').currentTime - 3) < 0.05 && document.getElementById('edVid').paused", 3)
    c.click("#edOut")
    e = ed(c)
    case("End here at 3.0 s: the trim is solid with an orange handle each end, 2.0 s, her line with the times, Add clip on",
         e["cutClass"] == "tcut set" and near(e["inT"], 1.0) and near(e["outT"], 3.0) and e["cutTag"] == "2.0 s" and not e["rec"] and not e["addOff"]
         and e["say"] == "Your clip: 0:01.0 to 0:03.0, <b>2.0 s</b>. Drag its orange ends on the timeline to fine-tune it, then press <b>Add clip</b>."
         and c.js("[getComputedStyle(document.querySelector('#edCut .cl')).display, getComputedStyle(document.querySelector('#edCut .cr')).display]") == ["grid", "grid"], e)
    # the ends and the middle
    c.drag("#edCut .cr", (x_at(c, 4.5), y), steps=8)
    e = ed(c)
    case("dragging the end handle trims the end (to 4.5 s), the video jumps there, the start stays", near(e["outT"], 4.5) and near(e["inT"], 1.0) and near(e["t"], 4.5, 0.25) and e["cutTag"] == "3.5 s", e)
    c.drag("#edCut .cl", (x_at(c, 0.5), y), steps=8)
    e = ed(c)
    case("dragging the start handle trims the start (to 0.5 s), the video jumps there", near(e["inT"], 0.5) and near(e["outT"], 4.5) and near(e["t"], 0.5, 0.25), e)
    c.drag("#edCut .cr", (x_at(c, 0.2), y), steps=8)
    e = ed(c)
    case("an end dragged too close: a clip is never under a second (hers)", near(e["outT"], 1.5) and near(e["inT"], 0.5), e)
    c.drag("#edCut .cr", (x_at(c, 2.5), y), steps=8)
    c.drag((x_at(c, 1.5), y), (x_at(c, 2.5), y), steps=8)
    e = ed(c)
    case("dragging the middle slides the whole trim (by a second), its length kept", near(e["inT"], 1.5) and near(e["outT"], 3.5) and e["cutTag"] == "2.0 s", e)
    case("a clip is kept 1 to 15 seconds: her 15 s line and the cap are the page's (a 6 s clip can't reach it here)",
         c.js("window.Reel.data.addMax") == 15 and W["ed_fifteen"] == "That's 15 seconds, the longest a clip can be. Drag its ends to change it, or press Add clip.")

    # Add clip
    before = [x["id"] for x in cards(c)]
    c.click("#edAdd")
    ok = wait(c, "document.querySelectorAll('#clist .ci').length === 3 && typeof window.Reel.editor().added === 'string'", 12)
    cs = cards(c)
    new = [x for x in cs if x["id"] not in before]
    e = ed(c)
    case("Add clip: a new card of theirs after their first pick and before Claude's (hers: theirs first), YOUR PICK, Not named yet, 1.5 to 3.5, 2.0 s, selected to open",
         ok and len(new) == 1 and [x["id"] for x in cs].index(new[0]["id"]) == 1 and new[0]["yours"] == "Your pick" and new[0]["label"] == W["not_named"]
         and new[0]["small"] == "clip.mov · 0:01.5–0:03.5 · 2.0 s" and new[0]["sel"] and new[0]["num"] == "1" and new[0]["use"] == W["in_reel"], cs)
    nid = new[0]["id"] if new else ""
    case("(no error on the page after Add clip)", not c.page_errors(), c.page_errors()[:3])
    case("saved: a 2.0 s clip of theirs on clip.mov, her label with its start, selected for Moment first",
         on_disk(s, lambda r: any(m["id"] == nid and m["start"] == 1.5 and m["end"] == 3.5 and m["label"] == "Your pick at 0:01.5" and m.get("by") == "you" for m in r.get("moments") or [])
                 and (r.get("saved") or {}).get("sel", {}).get("first") == [nid]))
    case("the trim stays where it was, dashed, with ✓ Added on it; Add clip says ✓ Added and is off; her line about making another",
         e["cutClass"] == "tcut set added" and e["cutTag"] == W["ed_added"] and e["addOff"] and e["addText"] == W["ed_added"] and e["say"] == W["ed_added_html"]
         and e["added"] == nid and e["marks"] and [m[0] for m in e["marks"]] == [own, nid], e)
    case("the Footage drop-down counts it: clip.mov · 0:06 · 2 clips", ed(c)["vp"] == "clip.mov 0:06 · 2 clips · 3 videos", ed(c)["vp"])
    c.wait_for("document.querySelector('#clist .ci[data-mid=\"%s\"] img').complete" % nid, 8)
    case("its card shows its still (a JPEG from its middle)", c.js("document.querySelector('#clist .ci[data-mid=\"%s\"] img').naturalWidth" % nid) > 0)
    # moved after Add clip: a new clip, the one added untouched (the timeline moved down with the new card: y afresh)
    y = tl_y(c)
    c.drag((x_at(c, 2.5), y), (x_at(c, 3.5), y), steps=8)
    e = ed(c)
    case("the trim moved after Add clip (by a second): it is a new clip now, Add clip is back on, the stretch solid with its length (hers, Nov 17)",
         e["added"] is False and not e["addOff"] and e["addText"] == W["ed_add"] and e["cutClass"] == "tcut set" and near(e["inT"], 2.5) and near(e["outT"], 4.5), e)
    case("...and the clip just added is never changed by that", on_disk(s, lambda r: any(m["id"] == nid and m["start"] == 1.5 and m["end"] == 3.5 for m in r.get("moments") or []), 2))
    c.click("#edClear")

    # a drag across a clip only scrubs; a click picks it
    rev0 = record(s).get("rev")
    c.drag("#edMarks .tm[data-mid='%s']" % nid, (x_at(c, 5.5), y), steps=8, check=False)
    e = ed(c)
    case("a drag that starts on a clip only scrubs (her fix: it used to pick and slide the clip by accident); nothing picked, nothing saved",
         e["edit"] is None and near(e["t"], 5.5, 0.3) and record(s).get("rev") == rev0 and e["sel"] is None, (e["edit"], e["t"]))
    c.click("#edMarks .tm[data-mid='%s']" % nid, check=False)
    e = ed(c)
    cs = cards(c)
    case("a plain click on a clip picks it: its handles show on the timeline, its card is outlined, her box says Play this clip and the clip's times",
         e["edit"] == nid and [m for m in e["marks"] if m[0] == nid][0][3] is True and [x["edit"] for x in cs] == [False, True, False]
         and e["sel"] and W["play_clip"] in e["sel"] and "0:01.5 to 0:03.5 · 2.0 s. On the timeline, drag its ends to trim it or its middle to slide it." in e["sel"]
         and near(e["t"], 1.5, 0.25), (e["edit"], e["marks"], e["sel"]))
    c.click("#edPlayClip")
    case("Play this clip plays it from its start and stops by itself at its end (3.5 s)",
         wait(c, "!document.getElementById('edVid').paused", 5) and wait(c, "document.getElementById('edVid').paused && Math.abs(document.getElementById('edVid').currentTime - 3.5) < 0.6", 8),
         c.js("document.getElementById('edVid').currentTime"))
    # the picked clip's end trimmed on the timeline
    c.drag("#edMarks .tm[data-mid='%s'] .hr" % nid, (x_at(c, 4.0), y), steps=8, check=False)
    case("dragging the picked clip's right handle trims its end (to 4.0 s), saved through the Assistant; the card follows; her label keeps its start",
         on_disk(s, lambda r: any(m["id"] == nid and m["start"] == 1.5 and m["end"] == 4.0 and m["label"] == "Your pick at 0:01.5" for m in r.get("moments") or []))
         and wait(c, "document.querySelector('#clist .ci[data-mid=\"%s\"] small').textContent === 'clip.mov · 0:01.5–0:04.0 · 2.5 s'" % nid, 6), cards(c))
    # the picked clip's middle slides it
    c.drag("#edMarks .tm[data-mid='%s']" % nid, (x_at(c, 3.75), y), steps=8, check=False)
    case("dragging its middle slides it (to 2.5 to 5.0), saved; the label moves with the start (not named yet)",
         on_disk(s, lambda r: any(m["id"] == nid and near(m["start"], 2.5, 0.11) and near(m["end"], 5.0, 0.11) and m["label"].startswith("Your pick at 0:02.") for m in r.get("moments") or [])), record(s).get("moments"))

    # a name from the chat (footage.py describe), and a trim keeps it
    names = s.work / "names.json"
    names.write_text(json.dumps({"clips": {nid: {"label": "Walking down the kitchen to the stove"}, own: {"label": "Lining up the shot"}}}))
    code, out = s.cmd("footage.py", "describe", KIT, "--file", str(names))
    case("footage.py describe names their two clips (the chat's command, under the record's lock)", code == 0 and "Named 2 clips" in out, out[-300:])
    case("the page shows the name within a few seconds, by itself; the YOUR PICK tag stays; the Name my clips box goes (every pick of theirs is named)",
         wait(c, "((document.querySelector('#clist .ci[data-mid=\"%s\"] b') || {}).textContent || '').indexOf('Walking down the kitchen to the stove') >= 0" % nid, 8)
         and cards(c)[1]["yours"] == "Your pick" and c.js("document.getElementById('descBox').hidden"), cards(c))
    c.click("#edMarks .tm[data-mid='%s']" % nid, check=False)
    c.drag("#edMarks .tm[data-mid='%s'] .hl" % nid, (x_at(c, 2.0), y), steps=8, check=False)
    case("trimming a named clip keeps its name (her Nov 16 rule); its start moved to 2.0",
         on_disk(s, lambda r: any(m["id"] == nid and near(m["start"], 2.0, 0.11) and m["label"] == "Walking down the kitchen to the stove" and m.get("named") is True for m in r.get("moments") or [])),
         record(s).get("moments"))
    case("and her box over the clip says its name", "Walking down the kitchen to the stove" in (ed(c)["sel"] or ""), ed(c)["sel"])

    # Zoom in / Show the whole video (a 6 s video: the window is the whole video either way; the words switch)
    c.click("#edZoom")
    e = ed(c)
    case("Zoom in: her 'zoomed in on' line and Show the whole video", e["zoom"] and e["win"] == "clip.mov · zoomed in on 0:00 to 0:06" and e["zoomText"] == W["ed_whole"], e)
    c.click("#edZoom")
    e = ed(c)
    case("Show the whole video: back", not e["zoom"] and e["win"] == "clip.mov · 0:06" and e["zoomText"] == W["ed_zoom"], e)
    case("one zoom threshold, 60 s, for Start here and for a picked clip (hers: 60 and 90), a 40 s window",
         c.js("[window.Reel.data.zoomOver, window.Reel.data.zoomWindow]") == [60, 40] and R.ZOOM_OVER == 60.0 and R.ZOOM_WINDOW == 40.0)

    # Use / In reel, per style; Remove and Undo
    c.click("#styles .opt[data-style='backforth']")
    cs = cards(c)
    case("Back and forth: two clips In reel, numbered 1 and 2 on their cards and on the timeline; her ask over the cards",
         [x["use"] for x in cs] == [W["in_reel"], W["in_reel"], W["use"]] and [x["num"] for x in cs] == ["1", "2", ""]
         and c.js("document.getElementById('momentsSay').textContent") == R.WORDS["pick_backforth"], cs)
    c.click("#clist .ci[data-mid='m1-0a0b0c'] .cin")
    cs = cards(c)
    case("Use on Claude's clip: In reel, 3; saved for this style only", [x["num"] for x in cs] == ["1", "2", "3"]
         and on_disk(s, lambda r: r["saved"]["sel"].get("backforth") == [own, nid, "m1-0a0b0c"] and r["saved"]["sel"]["first"] == [nid]), cs)
    case("Use on a card does not open it in the editor (the card's click does)", ed(c)["edit"] == nid)
    c.click("#clist .ci[data-mid='m1-0a0b0c'] .cin")
    case("In reel pressed again takes it out", [x["use"] for x in cards(c)] == [W["in_reel"], W["in_reel"], W["use"]])
    c.click("#styles .opt[data-style='reveal']")
    cs = cards(c)
    case("The reveal: only a clip matched to a photo can go in; the rest say No photo", [(x["use"], x["off"]) for x in cs] == [(W["no_photo"], True), (W["no_photo"], True), (W["in_reel"], False)], cs)
    c.click("#styles .opt[data-style='first']")
    c.click("#clist .ci[data-mid='m1-0a0b0c']")
    e = ed(c)
    case("a click on a card opens that clip in the editor: its video (Sideways é.mov) loads, the clip picked, the player at its start",
         wait(c, "window.Reel.editor().key !== null && document.getElementById('vpBtn').innerText.indexOf('Sideways') === 0", 8) and ed(c)["edit"] == "m1-0a0b0c"
         and near(ed(c)["t"], 0.5, 0.3) and ed(c)["win"] == "Sideways é.mov · 0:06", ed(c))
    case("the sideways video plays upright in the player (360 x 640)", wait(c, "document.getElementById('edVid').videoWidth === 360 && document.getElementById('edVid').videoHeight === 640", 10))
    c.click("#clist .ci[data-mid='%s'] .cx" % nid)
    case("× on a card: Remove, with her Undo note", wait(c, "document.querySelectorAll('#clist .ci').length === 2 && !!document.querySelector('.undo-note')", 6)
         and c.js("document.querySelector('.undo-note').firstChild.textContent") == "Removed “Walking down the kitchen to the stove”."
         and on_disk(s, lambda r: nid not in [m["id"] for m in r["moments"]] and nid in [x["moment"]["id"] for x in r.get("removed", [])]))
    c.click(".undo-note button")
    case("Undo puts it back where it was, with its name", wait(c, "document.querySelectorAll('#clist .ci').length === 3", 6) and cards(c)[1]["id"] == nid
         and cards(c)[1]["label"] == "Walking down the kitchen to the stove", cards(c))
    c.click("#clist .ci[data-mid='%s']" % nid)
    c.wait_for("window.Reel.editor().edit === '%s'" % nid, 5)
    c.click("#clist .ci[data-mid='%s'] .cx" % nid)
    e = ed(c)
    case("× on the card whose clip is in the editor clears the editor's pick too (ours: hers left it)", wait(c, "document.querySelectorAll('#clist .ci').length === 2", 6) and ed(c)["edit"] is None and ed(c)["sel"] is None, ed(c))
    s.http("POST", "/reel-moment", {"kit": KIT, "do": "restore", "id": nid, "at": 1})
    c.wait_for("document.querySelectorAll('#clist .ci').length === 3", 8)

    # after a reload: the names and the selection as left; two columns at a desk, one on a phone
    c.reload()
    c.wait_for("window.Reel && window.Reel.state() && document.querySelectorAll('#clist .ci').length === 3", 15)
    cs = cards(c)
    case("after a reload: the three cards, their names and the selection as left", cs[1]["label"] == "Walking down the kitchen to the stove" and cs[1]["sel"] and [x["sel"] for x in cs] == [False, True, False], cs)
    c.desktop((1100, 900))
    cols = c.js("(function(){ var r = Array.from(document.querySelectorAll('#clist .ci')).map(function(x){ return Math.round(x.getBoundingClientRect().left); }); return [new Set(r).size, document.documentElement.scrollWidth <= window.innerWidth, getComputedStyle(document.querySelector('.edgrid')).gridTemplateColumns.split(' ').length]; })()")
    case("at a desk: Your clips in two columns (every clip at once, no scroll box), the player beside them", cols[0] == 2 and cols[1] and cols[2] == 2, cols)
    c.phone(375, 800)
    ph = c.js("(function(){ var r = Array.from(document.querySelectorAll('#clist .ci')).map(function(x){ return Math.round(x.getBoundingClientRect().left); }); return [new Set(r).size, document.documentElement.scrollWidth, window.innerWidth, Math.round(document.getElementById('edPlayer').getBoundingClientRect().right), Math.round(document.getElementById('edTl').getBoundingClientRect().right)]; })()")
    case("on a phone: one column, the player and the timeline fit, and the page does not scroll sideways", ph[0] == 1 and ph[1] <= ph[2] and ph[3] <= 375 and ph[4] <= 375, ph)
    c.desktop()
    case("no errors on the page (the editor)", not c.page_errors(), c.page_errors()[:3])
    case("nothing asked of the internet (the editor)", not c.outside_requests(), c.outside_requests()[:3])
    case("no path anywhere on the page", not re.search(r"/private/|/Users/|\.kit/", c.js("document.body.innerHTML")))

    # a B-roll page: the same editor, her B-roll line over the cards, four clips to start with
    code, j, _ = s.http("POST", "/reel-version", {"kit": KIT, "op": "new", "name": "B-roll try", "kind": "broll"})
    case("(a B-roll reel started beside the first)", code == 200 and (j or {}).get("ok") and (j or {}).get("kind") == "broll", j)
    c.open(s.page_url("broll"))
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.editor().key && document.getElementById('edVid').readyState >= 1", 20)
    cs = cards(c)
    case("a B-roll page (a new reel of that kind): the same editor; it starts with the clip the assistant found (hers: a new reel keeps those), In reel, and her B-roll line over the cards",
         [x["label"] for x in cs] == ["Walking in"] and cs[0]["use"] == W["in_reel"] and cs[0]["num"] == "1"
         and c.js("document.getElementById('momentsSay').textContent") == W["pick_broll"], (cs, c.js("document.getElementById('momentsSay').textContent")))
    c.js("document.getElementById('edVid').currentTime = 0.5")
    wait(c, "Math.abs(document.getElementById('edVid').currentTime - 0.5) < 0.05", 3)
    c.click("#edIn")
    wait(c, "window.Reel.editor().inT === 0.5", 5)
    c.js("var v = document.getElementById('edVid'); v.pause(); v.currentTime = 3.0;")
    wait(c, "Math.abs(document.getElementById('edVid').currentTime - 3) < 0.05 && document.getElementById('edVid').paused", 3)
    c.click("#edOut")
    c.click("#edAdd")
    ok = wait(c, "document.querySelectorAll('#clist .ci').length === 2 && typeof window.Reel.editor().added === 'string'", 12)
    cs = cards(c)
    case("a clip made on a B-roll page: first, In reel, numbered 1, the found clip 2", ok and len(cs) == 2 and cs[0]["yours"] == "Your pick" and cs[0]["use"] == W["in_reel"]
         and [x["num"] for x in cs] == ["1", "2"], cs)
    case("...saved for B-roll as its own style, in that reel only", on_disk(s, lambda r: (r.get("saved") or {}).get("style") == "broll" and (r.get("saved") or {}).get("kind") == "broll"
         and (r["saved"].get("sel") or {}).get("broll") == [cs[0]["id"], "m1-0a0b0c"] and r.get("current") == "v2" and len(r.get("moments") or []) == 2))
    code, out = s.cmd("reel_page.py", "reels", KIT, "--open", "Reel 1")
    case("(back to the first reel, behind the scenes, for the tests after this one)", code == 0 and on_disk(s, lambda r: r.get("current", "v1") == "v1" and len(r.get("moments") or []) == 3), out[-200:])


def check_test_make(c, s):
    """A test make on the page with footage, and the page with footage but no moments (a fresh Chrome)."""
    c.open(s.page_url("bts") + "&test=1")
    c.wait_for("document.querySelectorAll('#clist .ci').length === 3", 15)
    c.click("#makeBtn")
    case("a test make with footage: her heading, her Plan line with the clip, the clip's line, the beats",
         wait(c, "document.getElementById('result').innerHTML.indexOf('Beats per piece') > 0", 60)
         and c.js("document.querySelector('#result h3').textContent") == "Test run: nothing was made"
         and c.js("document.querySelectorAll('#result p')[0].textContent").startswith("Plan: 1 clip and 8 photos, ")
         and " clip from " in c.js("document.getElementById('result').textContent"), c.js("document.getElementById('result').innerHTML")[:400])
    case("no path in the result", not re.search(r"/private/|/Users/|\.kit", c.js("document.getElementById('result').innerHTML")))
    # with footage and no moments at all: her line
    rec = record(s)
    keep_m = rec.get("moments")
    rec["moments"] = []
    (s.kit / ".kit" / "reel-page.json").write_text(json.dumps(rec))
    c.reload()
    c.wait_for("document.querySelectorAll('#songSel option').length > 1 && !document.getElementById('btsBox').hidden", 15)
    case("no clips yet: her line in the empty Your clips, and nothing over them", c.js("document.querySelector('#clist p').textContent") == rp().EDITOR_WORDS["clips_empty"]
         and texts1(c)["moments_say"] == "", c.js("document.getElementById('clist').textContent"))
    c.click("#makeBtn")
    case("Make my reel with footage and nothing looked at yet: her \"I haven't looked through your footage yet\"",
         wait(c, "document.getElementById('result').innerHTML === %s" % json.dumps(HERS_MAKE["not_looked"]), 5), texts1(c)["result"])
    rec = record(s)
    rec["moments"] = keep_m
    (s.kit / ".kit" / "reel-page.json").write_text(json.dumps(rec))
    errs = c.page_errors()
    case("no errors on the page", not errs, errs[:3])
    case("nothing asked of the internet", not c.outside_requests(), c.outside_requests()[:3])
    page = c.js("document.documentElement.outerHTML")
    case("no HTML5 drag on the page, and no path in it", "draggable=" not in page and "dragstart" not in page and not re.search(r"/private/|/Users/", page))


def check_pc_page(c, s, clips):
    """The PC's way on the real page (v19 review, Nov 7: on a PC no video could be played, so no moment could ever be
    made, while the page said the moments still worked; v27: the editor). The page server runs with
    ASSISTANT_NO_AVFOUNDATION=1, the PC's route on a Mac: a video that plays as it is plays in the editor, with no
    stills along the timeline and our line saying so; Start here, End here and Add clip make a clip (no still on
    its card); the line to copy for a footage look and Good to know are left out, the PC's own lines in their
    place; a video still being copied in is listed by name with our line."""
    import this_computer
    shutil.copy(clips["clip.mov"], s.kit / "Footage" / "PC plays.mov")
    whole = clips["clip.mov"].read_bytes()
    (s.kit / "Footage" / "Still copying.mov").write_bytes(whole[: len(whole) // 2])
    c.open(s.page_url("bts"))
    c.wait_for("window.Reel && window.Reel.state() && document.querySelectorAll('#vlist .vcard').length >= 4", 20)
    c.wait_for("document.querySelectorAll('#edTabs [data-ek]').length >= 4", 10)
    c.wait_for("Array.from(document.querySelectorAll('#edTabs [data-ek]')).some(function(b){ return b.innerText.indexOf('PC plays.mov') === 0 && b.innerText.indexOf('getting ready') < 0; })", 30)
    c.click("#vpBtn")
    c.js("Array.from(document.querySelectorAll('#edTabs [data-ek]')).filter(function(b){ return b.innerText.indexOf('PC plays.mov') === 0; })[0].click()")
    ok = wait(c, "document.getElementById('vpBtn').innerText.indexOf('PC plays.mov') === 0 && document.getElementById('edWait').hidden && document.getElementById('edVid').readyState >= 1 && Math.round(document.getElementById('edVid').duration) === 6", 20)
    got = c.js("""(function(){ var v = document.getElementById('edVid'); return {thumbs: document.querySelectorAll('#edThumbs img').length, w: v.videoWidth, d: Math.round(v.duration),
      vpimg: !!document.querySelector('#vpBtn img[src]'), note: (document.querySelector('#ed .pcnote') || {}).textContent, say: document.getElementById('edSayTop').innerHTML,
      inOff: document.getElementById('edIn').disabled, wait: document.getElementById('edWait').hidden}; })()""")
    case("on a PC a video that plays as it is plays in the editor, with no stills along the timeline and no picture in the Footage drop-down, our note under the timeline, and our line under Your footage",
         ok and got["thumbs"] == 0 and got["w"] == 640 and got["d"] == 6 and not got["vpimg"] and got["note"] == R().OUR_WORDS["editor_no_stills_pc"]
         and got["say"] == this_computer.WATCH_PC_HTML and not got["inOff"] and got["wait"], got)
    t = c.js("""({paste: document.getElementById('pasteSay').textContent, line: document.querySelector('#pasteBox .line').hidden,
                 insight: document.querySelector('.insight').hidden, vlist: document.getElementById('vlist').textContent})""")
    case("its lines on a PC: no copy line and no Good to know (Claude can't look there), the PC's own words in their place",
         t["paste"] == this_computer.NO_LOOK_PC and t["line"] and t["insight"], t)
    case("a video still being copied in: listed by name as still copying in",
         "Still copying.mov" in t["vlist"] and "still copying in" in t["vlist"], t)
    before = len(cards(c))
    c.js("document.getElementById('edVid').currentTime = 1.0;")
    wait(c, "Math.abs(document.getElementById('edVid').currentTime - 1) < 0.2", 5)
    c.click("#edIn")
    wait(c, "window.Reel.editor().inT === 1", 5)
    c.js("var v = document.getElementById('edVid'); v.pause(); v.currentTime = 3.5;")
    wait(c, "Math.abs(document.getElementById('edVid').currentTime - 3.5) < 0.1", 5)
    c.click("#edOut")
    e = ed(c)
    case("Start here and End here work off the video alone on a PC: a 2.5 s trim, solid, with its handles", e["cutClass"] == "tcut set" and e["cutTag"] == "2.5 s" and near(e["inT"], 1.0) and near(e["outT"], 3.5), e)
    c.click("#edAdd")
    ok = wait(c, "document.querySelectorAll('#clist .ci').length === %d" % (before + 1), 8)
    now = cards(c)
    new = next((x for x in now if x["small"].startswith("PC plays.mov")), {})
    case("Add clip on a PC adds a card of theirs, 2.5 s, YOUR PICK and Not named yet, with no still on it (none on a PC yet), and the trim stays dashed with ✓ Added",
         ok and new.get("yours") == "Your pick" and new.get("label") == "Not named yet" and new.get("small") == "PC plays.mov · 0:01.0–0:03.5 · 2.5 s"
         and wait(c, "!document.querySelector('#clist .ci[data-mid=\"%s\"] img[src]')" % new.get("id", "x"), 5) and ed(c)["cutClass"] == "tcut set added"
         and on_disk(s, lambda r: any(m.get("id") == new.get("id") and m.get("video") == "PC plays.mov" and m["end"] == 3.5 for m in r.get("moments") or [])), now)
    case("Name my clips: her box shows on a PC too (the naming itself needs stills: footage.py picks says so there)", ed(c)["desc"] == "Name my clips for " + SHORT)
    (s.kit / "Footage" / "Still copying.mov").write_bytes(whole)
    case("once the copy is done it comes in by itself (the page looks every 4 s)",
         wait(c, "Array.from(document.querySelectorAll('#edTabs [data-ek]')).some(function(b){ return b.innerText.indexOf('Still copying.mov') === 0; })", 12))


def R():
    return rp()


def check_untouched(s, before):
    now = {p.name: sha(p) for p in (s.kit / "Footage").iterdir() if p.is_file()}
    case("every video in their Footage folder is byte for byte as it was dropped in (only ever read)", all(now.get(k) == v for k, v in before.items()), now)
    case("the Photos folder is as it was", sorted(os.listdir(s.kit / "Photos")) == sorted(os.listdir(s.kit / "Photos")))


def mem_log(path):
    """FOOTAGE_MEM_LOG=<file>: every second, this run's memory by program, to read after the guard has stopped it."""
    import threading

    def run():
        while True:
            out = subprocess.run(["ps", "-axo", "pid=,ppid=,rss=,comm="], capture_output=True, text=True).stdout.splitlines()
            kids, rss, name = {}, {}, {}
            for ln in out:
                p = ln.split(None, 3)
                if len(p) >= 3:
                    kids.setdefault(int(p[1]), []).append(int(p[0]))
                    rss[int(p[0])], name[int(p[0])] = int(p[2]), (p[3] if len(p) > 3 else "")[-30:]
            todo, rows = [os.getpid()], []
            while todo:
                x = todo.pop()
                rows.append((rss.get(x, 0) // 1024, name.get(x, "")))
                todo += kids.get(x, [])
            with open(path, "a") as f:
                f.write("%s %d %s\n" % (time.strftime("%H:%M:%S"), sum(r[0] for r in rows), sorted(rows, reverse=True)[:6]))
            time.sleep(1)
    threading.Thread(target=run, daemon=True).start()


def main():
    if os.environ.get("FOOTAGE_MEM_LOG"):
        mem_log(os.environ["FOOTAGE_MEM_LOG"])
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=9322)
    ap.add_argument("--only", choices=("server", "order", "make", "page", "editor", "pc"))
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp")
        return 2
    run = work / time.strftime("footage-%H%M%S")
    run.mkdir(parents=True)
    group("her clip order, style by style", check_order, run)
    group("her words for the footage editor, both ways", check_editor_words)
    if a.only == "order":
        return rpc.summary()
    if not Path("/usr/bin/sips").exists():
        print("SKIP  the rest: the pretend kit and the clips are made with the Mac's own tools", flush=True)
        return rpc.summary()
    clips = make_clips(run / "clips")
    s = rpc.Setup(run, a.port)
    s.make()
    _orig_http = s.http

    def http(method, path, body=None, headers=None):          # the answer's headers too, for the Range checks
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=15)
        h = {"Host": "127.0.0.1:%d" % s.port}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        s.last_headers = dict(r.getheaders())
        c.close()
        try:
            j = json.loads(raw.decode())
        except (ValueError, UnicodeDecodeError):
            j = None
        return r.status, j, raw
    s.http = http
    s.start()
    try:
        case("the page server is on a port of this test's own (%d)" % s.port, a.port <= s.port < a.port + 10)
        code, out = s.cmd("reel_page.py", "open", str(s.kit))
        case("(set up: the page's small copies made first)", code == 0, out[-200:])
        group("the footage on the server", check_server, s, clips)
        before = {p.name: sha(p) for p in (s.kit / "Footage").iterdir() if p.is_file()}
        if a.only == "server":
            return rpc.summary()
        group("Make my reel with footage", check_make, s, run)
        if a.only == "make":
            return rpc.summary()
        if not chrome_drive.find_chrome():
            print("SKIP  the page in a browser: no Chrome on this computer", flush=True)
        else:
            # one hidden Chrome after another, each new, so the memory a long run builds up never adds up
            if a.only != "pc":
                if a.only != "editor":
                    with chrome_drive.Chrome(work=str(run), size=(820, 900), extra_args=LIGHT) as c:
                        group("steps 1 and 4 on the page", check_page, c, s, clips)
                with chrome_drive.Chrome(work=str(run), size=(820, 900), extra_args=LIGHT) as c:
                    c.init_script("document.addEventListener('copy', function(){ window.__copied = String(window.getSelection()); }, true);")
                    group("the footage editor on the page: the player, the timeline, the trim, Your clips", check_editor, c, s)
                if a.only == "editor":
                    return rpc.summary()
                with chrome_drive.Chrome(work=str(run), size=(820, 900), extra_args=LIGHT) as c:
                    group("a test make with footage on the page", check_test_make, c, s)
            if a.only in (None, "pc"):
                s.stop()
                s.start(ASSISTANT_NO_AVFOUNDATION="1")
                with chrome_drive.Chrome(work=str(run), size=(820, 900), extra_args=LIGHT) as c:
                    group("the PC's way on the page (ASSISTANT_NO_AVFOUNDATION=1)", check_pc_page, c, s, clips)
                (run / "set aside").mkdir(exist_ok=True)
                for n in ("PC plays.mov", "Still copying.mov"):
                    shutil.move(str(s.kit / "Footage" / n), str(run / "set aside" / n))
                s.stop()
                s.start()
                if a.only == "pc":
                    return rpc.summary()
        case("(the video the page test took back out is byte for byte what was dropped in)", sha(run / "set aside" / "Dropped in.mov") == sha(clips["clip.mov"]))
        group("nothing of theirs changed", check_untouched, s, before)
        s.stop()
        s.start()
        _, j, _ = foot(s)
        case("a new page server reads the previews' states from disk: nothing made again",
             j and all(v["preview"] == "ready" for v in j["videos"]) and sorted(os.listdir(s.kit / ".kit" / "footage" / j["videos"][-1]["key"])) == ["preview.json", "strip"], j)
    finally:
        s.stop()
    return rpc.summary()


if __name__ == "__main__":
    sys.exit(main())
