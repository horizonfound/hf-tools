#!/usr/bin/env python3
"""The reel page's step 1 (behind-the-scenes footage), the moment cards, the player and step 4 (the style),
checked on the server and on the real page in a HIDDEN Chrome, on small clips this test makes itself.

    python3 guard.py 800 /usr/bin/python3 tests/reel_footage_check.py --work /private/tmp/somewhere [--port 9322]
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

# Her words for step 1 and step 4, as her reel-maker.html shows them (handoff v19).
HERS1 = {
    "h2": "Behind-the-scenes footage?",
    "say": "Do you want this reel to include behind-the-scenes video from the shoot, or just your photos?",
    "bts_b": "Add behind-the-scenes footage", "bts_s": "Clips from the shoot, mixed with your finished photos.",
    "photos_b": "Just photos", "photos_s": "Your finished photos, cut on the beat.",
    "say2": "Press <b>Add my footage</b> and a Footage folder for this shoot opens in Finder. Drag your behind-the-scenes videos into it.",
    "add": "▶ Add my footage",
    "insight_b": "Good to know: longer footage takes longer",
    "insight": "Longer videos take me longer to look through and use more of your plan. A few minutes of footage takes a few minutes. A 20-minute video takes about 10 minutes or more.",
    "fix": "<b>Quick fix:</b> trim it first and keep just the parts you like. On your iPhone, open the video in Photos, tap Edit, and drag the ends of the timeline in. On a Mac, open it in QuickTime Player and choose Edit › Trim. A few short clips are quicker for me than one long video.",
    "paste_say": "Once your footage is in, copy this into the chat so I can look through it:",
    "copy": "Copy",
    "ask_b": "Want to direct the reel?",
    "ask": " Optional. Tell me the moments you want and how you'd like the reel to go, and I'll follow it through your footage.",
    "ex1": "For example: “Find the first kiss. Start with getting ready in the morning, then the ceremony, and end with the sparkler exit.”",
    "ex2": "Another example: “Find the footage of me walking into the frame with my camera.”",
    "ask_ph": "Optional: the moments you want, and how you'd like it to go",
    "feel_b": "How should it feel?",
    "feels": ["Heartwarming", "Nostalgic", "Fun", "Dreamy", "Something else"],
    "feel_ph": "Your words, like joyful or cozy",
    "feel_small": "Optional. Pick one, or tap <b>Something else</b> and type your own. I'll pick the photos and moments that bring out that feeling. Tap it again to clear it.",
    "clips_h3": "Select your clips",
    "moments_first": "The moments I find will show up here.",
    "watch_h3": "Watch your footage and pick your own",
    "watch": "Play it here, or tap a still to jump there. When you see a part you love, press <b>Use this moment</b>. It shows up first in your clips, 4 seconds long and selected. Use <b>−</b> and <b>+</b> on its card to make it shorter or longer.",
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
    "foot_need": "<h3>One more thing: behind-the-scenes footage?</h3><p>Choose <b>Add behind-the-scenes footage</b> or <b>Just photos</b> in step 1.</p>",
    "clips_need": "<h3>One more thing: your clips</h3><p>Select the clip or clips to use under <b>Select your clips</b> in step 1, or choose <b>Just photos</b>.</p>",
    "not_looked": "<h3>I haven't looked through your footage yet</h3><p>Add your videos in step 1, then copy the line into the chat. The moments I find show up under <b>Select your clips</b> in step 1. Or choose <b>Just photos</b>.</p>",
}
TAIL = "Press ▶ to preview one, use − and + to make it shorter or longer, or Remove it."


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
      return {h2: h('step0'), say: document.querySelector('#step0 > p.say').textContent,
        bts_b: document.querySelector('#modeBts b').textContent, bts_s: document.querySelector('#modeBts span').textContent,
        photos_b: document.querySelector('#modePhotos b').textContent, photos_s: document.querySelector('#modePhotos span').textContent,
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
        clips_h3: document.querySelectorAll('#btsBox h3.mh')[0].textContent, watch_h3: document.querySelectorAll('#btsBox h3.mh')[1].textContent,
        watch: document.querySelectorAll('#btsBox > p.say')[2].innerHTML, moments_say: document.getElementById('momentsSay').textContent,
        h2s: h('stepStyle'), says: document.querySelector('#stepStyle > p.say').textContent,
        cards: Array.from(document.querySelectorAll('#styles .opt')).map(function(x){ return [x.querySelector('b').textContent, x.querySelector('span').textContent]; }),
        nums: Array.from(document.querySelectorAll('section.step')).filter(function(s){ return !s.hidden; }).map(function(s){ return s.id + '=' + s.querySelector('.num').textContent; }),
        bts_on: document.getElementById('modeBts').classList.contains('on'), photos_on: document.getElementById('modePhotos').classList.contains('on'),
        box_hidden: document.getElementById('btsBox').hidden, style_hidden: document.getElementById('stepStyle').hidden,
        rec_shown: !document.getElementById('claudeRec').hidden, done0: document.getElementById('step0').classList.contains('done'),
        waiting: document.getElementById('footWaiting').textContent, vlist: document.getElementById('vlist').innerText,
        sum: document.getElementById('sum').textContent, result: document.getElementById('result').innerHTML};
    })()""")


def cards(c):
    return c.js("""Array.from(document.querySelectorAll('#moments .mom')).map(function(m){ return {id: m.dataset.id, sel: m.classList.contains('sel'),
      badge: (m.querySelector('.badge') || {}).textContent || '', label: m.querySelector('.tx b').textContent, small: m.querySelector('.tx small').textContent,
      len: m.querySelector('.len b').textContent, use: m.querySelector('.usebtn').textContent, off: m.querySelector('.usebtn').disabled,
      yours: !!m.querySelector('.yours'), img: !!m.querySelector('.th img')}; })""")


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


def check_page(c, s, clips):
    sid = rpc.song_of(s, KIT, "Test beat")
    # start from a record with no footage choice yet: their 8 photos, the song picked
    rec = record(s)
    rec["saved"] = {"picks": rpc.pk("3,1+,7,4,12-,9,2,10+"), "mine": True, "song": sid, "vibe": "beat"}
    rec["rev"] = int(rec.get("rev") or 0) + 1
    rec.pop("from", None)
    (s.kit / ".kit" / "reel-page.json").write_text(json.dumps(rec))
    c.init_script("document.addEventListener('copy', function(){ window.__copied = String(window.getSelection()); }, true);")
    c.open(s.page_url())
    c.wait_for("document.querySelectorAll('#reel .tile').length === 8 && document.querySelectorAll('#songs .song').length > 1", 20)
    t = texts1(c)
    case("footage not chosen yet: both cards off, the box and step 4 hidden, steps 1 to 4 (hers)", not t["bts_on"] and not t["photos_on"]
         and t["box_hidden"] and t["style_hidden"] and t["nums"] == ["step0=1", "step1=2", "step3=3", "step4=4"], t["nums"])
    for k in ("h2", "say", "bts_b", "bts_s", "photos_b", "photos_s"):
        case("her words, step 1: %s" % k, t[k] == HERS1[k], (t[k], HERS1[k]))
    c.click("#makeBtn")
    case("Make my reel before footage is chosen: her \"One more thing\" box", wait(c, "document.getElementById('result').innerHTML === %s" % json.dumps(HERS_MAKE["foot_need"]), 5),
         texts1(c)["result"])
    c.click("#modePhotos")
    t = texts1(c)
    case("Just photos: marked, step 1 done, the box and step 4 stay hidden", t["photos_on"] and t["done0"] and t["box_hidden"] and t["style_hidden"]
         and t["nums"] == ["step0=1", "step1=2", "step3=3", "step4=4"], t)
    case("saved: footage false", on_disk(s, lambda r: (r.get("saved") or {}).get("footage") is False))
    c.click("#modeBts")
    t = texts1(c)
    case("Add behind-the-scenes footage: the box and step 4 show, her renumbering 1 to 5, the recommended tag",
         t["bts_on"] and not t["box_hidden"] and not t["style_hidden"] and t["rec_shown"]
         and t["nums"] == ["step0=1", "step1=2", "step3=3", "stepStyle=4", "step4=5"], t)
    case("saved: footage true", on_disk(s, lambda r: (r.get("saved") or {}).get("footage") is True))
    for k in ("say2", "add", "insight_b", "fix", "paste_say", "copy", "ask_b", "ask", "ex1", "ex2", "ask_ph", "feel_b", "feels", "feel_ph",
              "feel_small", "clips_h3", "watch_h3", "watch"):
        case("her words, step 1: %s" % k, t[k] == HERS1[k], (t[k], HERS1[k]))
    case("her words, step 4: the heading, the line, the four styles in her order",
         t["h2s"] == HERS4["h2"] and t["says"] == HERS4["say"] and t["cards"] == HERS4["cards"], (t["h2s"], t["cards"]))
    case("her limits on the boxes: 600 and 40 characters", t["ask_max"] == 600 and t["feel_max"] == 40, (t["ask_max"], t["feel_max"]))
    case("Good to know with three 6-second videos: her line for up to 3 minutes", wait(c, "document.getElementById('insightWords').textContent === %s"
         % json.dumps("You've added 0:18 of footage. That takes me about a minute or two to look through, and longer footage uses more of your plan."), 8),
         texts1(c)["insight"])
    case("the videos listed with their length and size (hers)", wait(c, "document.querySelectorAll('#vlist .vid').length === 3", 6)
         and c.js("Array.from(document.querySelectorAll('#vlist .vid')).map(function(v){ return v.innerText.replace(/\\s+/g, ' '); })")
         == ["▶ Not plain.mov 0:06 · 0 MB", "▶ Sideways é.mov 0:06 · 0 MB", "▶ clip.mov 0:06 · 0 MB"], c.js("document.getElementById('vlist').innerText"))

    # Add my footage, and the list following a new file
    c.click("#addFootage")
    case("Add my footage: her words once the folder is open", wait(c, "document.getElementById('footWaiting').textContent === %s" % json.dumps(HERS1["opened"]), 6),
         texts1(c)["waiting"])
    shutil.copy(clips["clip.mov"], s.kit / "Footage" / "Dropped in.mov")
    case("a video dropped into the Footage folder shows up by itself (her 4 s look)",
         wait(c, "Array.from(document.querySelectorAll('#vlist .vid span:not(.ic)')).some(function(x){ return x.textContent === 'Dropped in.mov'; })", 8),
         texts1(c)["vlist"])
    case("and Good to know adds it up: 0:24", wait(c, "document.getElementById('insightWords').textContent.indexOf('0:24 of footage') > 0", 4), texts1(c)["insight"])
    # taken back out (kept beside the kit): the list follows that too, and the page plays three videos, not four
    aside = s.work / "set aside"
    aside.mkdir(exist_ok=True)
    (s.kit / "Footage" / "Dropped in.mov").rename(aside / "Dropped in.mov")
    case("a video taken out of the folder goes from the list",
         wait(c, "document.querySelectorAll('#vlist .vid').length === 3 && document.getElementById('insightWords').textContent.indexOf('0:18 of footage') > 0", 8),
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
    c.click("#feelRow button[data-f='fun']")
    case("a feel: Fun marked, the line has the notes, saved as \"fun\"", c.js("document.querySelector(\"#feelRow button[data-f='fun']\").classList.contains('on')")
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



def check_player(c, s):
    """The player, the strip, Use this moment, the cards and the styles (a fresh Chrome: it fits the memory guard)."""
    c.open(s.page_url())
    c.wait_for("document.querySelectorAll('.viewer[data-ready]').length === 3", 20)
    t = texts1(c)
    case("after a reload: footage on, their feel in its own box, the notes empty", t["bts_on"] and c.js("document.getElementById('feelOwn').value") == "cozy and warm"
         and c.js("document.getElementById('askIn').value") == "", t)
    ok = wait(c, "Array.from(document.querySelectorAll('.viewer video')).every(function(v){ return v.readyState >= 1; })", 15)
    dims = c.js("Array.from(document.querySelectorAll('.viewer')).map(function(e){ var v = e.querySelector('video'); return [e.querySelector('h4').textContent, v.videoWidth, v.videoHeight, Math.round(v.duration)]; })")
    case("every video plays on the page (the one that doesn't play as it is, from its copy); the sideways one upright (360 x 640)",
         ok and dims == [["Not plain.mov", 640, 360, 6], ["Sideways é.mov", 360, 640, 6], ["clip.mov", 640, 360, 6]], dims)
    got = [(r["url"].split("key=")[-1], r["status"]) for r in c.requests if "/reel-video" in r["url"]]
    case("the player asked for its video in pieces, answered 206", got and all(st_ == 206 for _, st_ in got), got)
    strip = c.js("Array.from(document.querySelectorAll('.viewer')[2].querySelectorAll('.strip button')).map(function(b){ return [b.dataset.t, b.querySelector('span').textContent, b.querySelector('img').naturalWidth > 0]; })")
    case("a strip of stills one every 2 s under the player", [x[:2] for x in strip] == [["0", "0:00"], ["2", "0:02"], ["4", "0:04"]], strip)
    case("her line beside the player", c.js("document.querySelectorAll('.viewer')[2].querySelector('.vside p').textContent") == "0:06 · tap a still to jump there")
    c.js("document.querySelectorAll('.viewer')[2].scrollIntoView({block: 'center'})")
    c.click(".viewer[data-key] .strip button[data-t='2']", nth=2)
    case("a still jumps the player there", wait(c, "Math.abs(document.querySelectorAll('.viewer video')[2].currentTime - 2) < 0.6", 5),
         c.js("document.querySelectorAll('.viewer video')[2].currentTime"))
    c.js("var v = document.querySelectorAll('.viewer video')[2]; v.pause(); v.currentTime = 0.5;")
    case("her line under it: where it starts, 4 seconds", wait(c, "document.querySelectorAll('.viewer .at')[2].textContent === 'Starts at 0:00.5 · 4 seconds'", 5),
         c.js("document.querySelectorAll('.viewer .at')[2].textContent"))

    # Use this moment, − and +, Remove and Undo
    before = cards(c)
    c.click(".viewer .use", nth=2)
    case("Use this moment: her line beside it", wait(c, "document.querySelectorAll('.viewer .at')[2].textContent === 'Added and selected: 0:00.5. Use − and + on its card above to change the length.'", 8),
         c.js("document.querySelectorAll('.viewer .at')[2].textContent"))
    now = cards(c)
    theirs = sum(1 for x in before if x["yours"])
    new = now[theirs] if len(now) > theirs else {}
    case("a new card: after their earlier picks and before the ones found (her server: theirs first, in the order they add them), "
         "4 seconds, \"Your pick\", selected to open (Moment first)", len(now) == len(before) + 1 and new.get("yours") and theirs == 1
         and [x["id"] for x in now if x["id"] != new.get("id")] == [x["id"] for x in before]
         and new.get("label") == "Your pick at 0:00.5" and new.get("len") == "4.0 s" and new.get("sel") and new.get("badge") == "Opens" and new.get("use") == "✓ Selected", now)
    mid = new.get("id")
    at = lambda r: next((m for m in r.get("moments") or [] if m["id"] == mid), {})     # noqa: E731
    case("saved: the moment in that place, and selected for Moment first (saved.sel)", on_disk(s, lambda r: [m["id"] for m in r.get("moments") or []][theirs:theirs + 1] == [mid]
         and (r.get("saved") or {}).get("sel", {}).get("first") == [mid]))
    c.wait_for("document.querySelector('.mom .th img') && document.querySelector('.mom .th img').complete", 5)
    case("its card shows its still", c.js("document.querySelector('.mom .th img').naturalWidth") > 0)
    c.click(".mom[data-id='%s'] .lg" % mid)
    case("+ : half a second longer, on the card and saved", wait(c, "document.querySelector(\".mom[data-id='%s'] .len b\").textContent === '4.5 s'" % mid, 5)
         and on_disk(s, lambda r: at(r).get("end") == 5.0))
    case("then it replays at its new length on the card (hers: after 450 ms)", wait(c, "!!document.querySelector(\".mom[data-id='%s'] .th video\")" % mid, 3))
    c.click(".mom[data-id='%s'] .ls" % mid)
    wait(c, "document.querySelector(\".mom[data-id='%s'] .len b\").textContent === '4.0 s'" % mid, 5)
    c.click(".mom[data-id='%s'] .ls" % mid)
    case("− twice (each after the last has landed, as hers needs): 3.5 s", wait(c, "document.querySelector(\".mom[data-id='%s'] .len b\").textContent === '3.5 s'" % mid, 5)
         and on_disk(s, lambda r: at(r).get("end") == 4.0))
    c.click(".mom[data-id='%s'] .rm" % mid)
    case("Remove: the card goes, her Undo note shows", wait(c, "!document.querySelector(\".mom[data-id='%s']\") && !!document.querySelector('.undo-note')" % mid, 5)
         and c.js("document.querySelector('.undo-note').firstChild.textContent") == "Removed “Your pick at 0:00.5”."
         and c.js("document.querySelector('.undo-note button').textContent") == "Undo")
    case("and the moment is gone from the record (kept as removed)", on_disk(s, lambda r: mid not in [m["id"] for m in r["moments"]]
         and mid in [x["moment"]["id"] for x in r.get("removed", [])]))
    c.click(".undo-note button")
    case("Undo puts it back where it was, 3.5 s", wait(c, "document.querySelectorAll('#moments .mom')[%d].dataset.id === '%s'" % (theirs, mid), 5)
         and cards(c)[theirs]["len"] == "3.5 s" and on_disk(s, lambda r: [m["id"] for m in r["moments"]][theirs] == mid))
    c.click(".mom[data-id='%s'] .rm" % mid)
    c.wait_for("!!document.querySelector('.undo-note')", 5)
    t0 = time.time()
    gone = wait(c, "!document.querySelector('.undo-note')", 13)
    case("the Undo note goes by itself after 10 s (hers)", gone and 9 <= time.time() - t0 <= 12.5, time.time() - t0)
    s.http("POST", "/reel-moment", {"kit": KIT, "do": "restore", "id": mid, "at": theirs})
    case("(put back for the rest)", wait(c, "document.querySelectorAll('#moments .mom').length === 3", 8), len(cards(c)))

    # Select / Selected, per style
    ids = [x["id"] for x in cards(c)]
    t = texts1(c)
    case("her line over the cards: who found them, the style's ask, her tail",
         t["moments_say"] == "1 I found and 2 you picked. Select the clip that opens your reel. " + TAIL, t["moments_say"])
    case("(the cards: their two, then Claude's)", [x["yours"] for x in cards(c)] == [True, True, False] and ids[1] == mid, cards(c))
    c.click(".mom[data-id='%s'] .usebtn" % ids[0])
    cs = cards(c)
    case("Moment first takes one: selecting another moves the selection (Opens)", [x["sel"] for x in cs] == [True, False, False] and cs[0]["badge"] == "Opens"
         and on_disk(s, lambda r: r["saved"]["sel"]["first"] == [ids[0]]), cs)
    c.click("#styles .opt[data-style='backforth']")
    cs = cards(c)
    case("Back and forth starts with 2 clips selected (hers), badged Clip 1 and Clip 2", [x["sel"] for x in cs] == [True, True, False]
         and [x["badge"] for x in cs] == ["Clip 1", "Clip 2", ""], cs)
    c.click(".mom[data-id='%s'] .usebtn" % ids[2])
    case("and takes more: a third, Clip 3, saved for this style only", [x["badge"] for x in cards(c)] == ["Clip 1", "Clip 2", "Clip 3"]
         and on_disk(s, lambda r: r["saved"]["sel"].get("backforth") == ids and r["saved"]["sel"]["first"] == [ids[0]] and r["saved"]["style"] == "backforth"))
    case("the bar: her summary with the clips and the style", texts1(c)["sum"] == "8 photos + 3 clips · Back and forth · Test beat · on every beat", texts1(c)["sum"])
    c.click("#styles .opt[data-style='bookends']")
    cs = cards(c)
    case("Bookends: the first and last selected, Opens and Closes", [x["badge"] for x in cs] == ["Opens", "", "Closes"], cs)
    c.click(".mom[data-id='%s'] .usebtn" % ids[1])
    case("a third for Bookends: her line, nothing changed", texts1(c)["moments_say"] == "This style uses 2 clips. Unselect one first, then select the one you want."
         and [x["badge"] for x in cards(c)] == ["Opens", "", "Closes"], texts1(c)["moments_say"])
    c.click("#styles .opt[data-style='reveal']")
    cs = cards(c)
    case("The reveal: only a moment matched to a photo can be selected; the rest say \"No matching photo\"",
         [(x["use"], x["off"]) for x in cs if x["id"] != "m1-0a0b0c"] == [("No matching photo", True)] * 2
         and [x["sel"] for x in cs if x["id"] == "m1-0a0b0c"] == [True], cs)
    c.click("#styles .opt[data-style='backforth']")
    for i in ids:
        c.click(".mom[data-id='%s'] .usebtn" % i)
    case("Back and forth with every clip unselected", [x["sel"] for x in cards(c)] == [False, False, False])
    c.click("#makeBtn")
    case("Make my reel with no clip selected: her \"One more thing: your clips\"", wait(c, "document.getElementById('result').innerHTML === %s" % json.dumps(HERS_MAKE["clips_need"]), 5),
         texts1(c)["result"])
    c.reload()
    c.wait_for("document.querySelectorAll('#moments .mom').length === 3", 15)
    case("after a reload: the style and every style's selection as left", c.js("document.querySelector('#styles .opt.on').dataset.style") == "backforth"
         and [x["sel"] for x in cards(c)] == [False, False, False], cards(c))
    c.click("#styles .opt[data-style='first']")
    case("Moment first's own selection is still there", [x["sel"] for x in cards(c)] == [True, False, False], cards(c))

    # a moment's clip on its card
    c.js("document.querySelector('.mom[data-id=\"%s\"]').scrollIntoView({block: 'center'})" % ids[1])
    c.click(".mom[data-id='%s'] .play" % ids[1])
    case("▶ plays the moment on its card", wait(c, "(function(){ var v = document.querySelector(\".mom[data-id='%s'] .th video\"); return v && !v.paused && v.currentTime > 0; })()" % ids[1], 6))
    case("and stops by itself at its end", wait(c, "!document.querySelector(\".mom[data-id='%s'] .th video\")" % ids[1], 10))
    case("no errors on the page (the player and the cards)", not c.page_errors(), c.page_errors()[:3])
    case("nothing asked of the internet (the player and the cards)", not c.outside_requests(), c.outside_requests()[:3])



def check_test_make(c, s):
    """A test make on the page with footage, and the page with footage but no moments (a fresh Chrome)."""
    c.open(s.page_url() + "&test=1")
    c.wait_for("document.querySelectorAll('#moments .mom').length === 3", 15)
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
    c.wait_for("document.querySelectorAll('#songs .song').length > 1 && !document.getElementById('btsBox').hidden", 15)
    case("no moments yet: her line over the empty cards", texts1(c)["moments_say"] == "The moments I find, and any you pick yourself below, show up here.", texts1(c)["moments_say"])
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
    ap.add_argument("--only", choices=("server", "order", "make", "page"))
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp")
        return 2
    run = work / time.strftime("footage-%H%M%S")
    run.mkdir(parents=True)
    group("her clip order, style by style", check_order, run)
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
            with chrome_drive.Chrome(work=str(run), size=(820, 900), extra_args=LIGHT) as c:
                group("steps 1 and 4 on the page", check_page, c, s, clips)
            with chrome_drive.Chrome(work=str(run), size=(820, 900), extra_args=LIGHT) as c:
                group("the player, the moment cards and the styles", check_player, c, s)
            with chrome_drive.Chrome(work=str(run), size=(820, 900), extra_args=LIGHT) as c:
                group("a test make with footage on the page", check_test_make, c, s)
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
