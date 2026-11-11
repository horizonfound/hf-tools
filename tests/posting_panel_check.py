#!/usr/bin/env python3
"""The posting queue's panel for an upcoming post (Nicole's v20 section 5 and v21 section 2, stage 3 of the v21
build): the photo a post shows in the grid, and its caption and hook to copy. Checked by request, in this
program, and on the real page in a HIDDEN Chrome.

    python3 tests/posting_panel_check.py [--port 8950] [--work <a folder to keep the run in>] [--no-chrome]

What it does, on a pretend Assistant with pretend kits it makes itself in a throwaway folder (a few tiny
pictures; nothing of a client's, nothing of the real ~/.studio, no drive, no calendar):
  * the names of a kit's pieces: an OLD posting.json (pieces from before the kit's folder was kept) still loads
    and its pieces are never renamed; two shoots whose folder names shorten to the same one can both be added and
    are kept apart; a reel's first tile is the reel's first photo; a tile they picked is never changed by an add;
  * every route and every refusal: GET /posting/panel (another host, another website's page, a post that isn't
    upcoming, no such post) and POST /posting {action: "cover"} (another Origin, another website, a body too big,
    a photo outside the kit, another kit's photo, "..", a backslash, a hidden file, the wrong folder for the
    piece, a piece that isn't upcoming); nothing is changed by a refused pick;
  * a pick: the cover saved on the piece, the tile under a new name with the earlier one kept, the reel's strip
    in reel order with the rest after, the carousel's slides numbered, the words page and the kit page showing it;
  * the words: the caption (or their own), the first picked hook, none picked, no caption;
  * the page itself (when there is a Chrome): her words, the panel right under the clicked post's row across all
    three columns, the outlined tile, a 5 px press opens it and a real drag moves the tile without opening it,
    the panel staying open through a redraw, Copy caption / Copy my hook and their toasts, the carousel's
    not-slide-1 warning, and a shoot's name or a caption with <, &, quotes and a script only ever shown as text.

The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only, a Mac or a PC.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import words_page_check as wpc  # noqa: E402  (its pretend Assistant: kits, the page server, words.py from the chat)

KIT, SHORT, LONG, LONG_SHORT, HOOKS, NASTY = wpc.KIT, wpc.SHORT, wpc.LONG, wpc.LONG_SHORT, wpc.HOOKS, wpc.NASTY
TWIN = KIT[:10] + "-" + KIT[11:]          # a dash where the space was: the same name once the queue shortens it
CAPTION = "MINI SESSIONS are coming to Laguna Beach on December 4th!!!\n\n" + NASTY
OWN = "Their own caption, typed by hand."

# her words, as v21 has them (UPDATE-v21.md section 2, UPDATE-v20.md section 5)
HINT = "Click on a post to change the photo it shows in your grid, or to copy its caption."
SENTENCE = ("Newest at the top, like Instagram. The outlined ones are your upcoming posts. Click one to pick the photo it shows. "
            "Drag one to a different spot to change the order; the dates update to match.")
TIP = "Click to change its photo or copy its caption · drag to move it"
REEL_LINE = "Pick the photo your reel shows in your grid. When you post it, tap Edit cover and choose the same photo so your feed matches."
CAR_LINE = "Instagram shows a carousel’s first slide in your grid, so pick the slide you want people to see first."
WARN = "This isn’t your first slide, so your real grid will show slide 1 instead. To match, move this one to the front in the carousel designer."
T_REEL = "Changed. Pick this one as the cover when you post."
T_CAR = "Changed. That’s its photo in your grid now."
T_CAPTION = "Copied your caption. Paste it into Instagram."
T_HOOK = "Copied your hook. Paste it into Instagram."
T_NO_HOOK = "Pick a hook on your words page first."
CANT = "I can’t find this post’s photos right now. Open its post kit once, then try again."


def skip(line):
    print("SKIP  " + line, flush=True)


def page_state(s):
    """What the posting page draws from, as the server hands it to the page."""
    code, _, raw = s.http("GET", "/posting.html")
    m = re.search(r"<script type='application/json' id='data'>(.*?)</script>", raw.decode("utf-8"), re.S)
    return json.loads(m.group(1).replace("<\\/", "</")) if code == 200 and m else {}


def green(s, pid):
    return next((x for x in page_state(s).get("greens", []) if x["id"] == pid), None)


def piece(s, pid):
    return next((x for x in s.posting().get("pieces", []) if x.get("id") == pid), None)


def of_kit(s, name, role):
    return next((x for x in s.posting().get("pieces", []) if x.get("id", "").endswith("-" + role)
                 and re.split(r"[\\/]", str(x.get("kit") or ""))[-1] == name), None)


def panel(s, pid, headers=None):
    return s.http("GET", "/posting/panel?id=" + quote(pid, safe=""), headers=headers)


def cover(s, pid, rel, headers=None):
    return s.http("POST", "/posting", {"action": "cover", "id": pid, "rel": rel}, headers=headers)


def make_twin(s):
    twin = s.content / TWIN
    if not twin.exists():
        shutil.copytree(str(s.kit), str(twin))
        sheet = twin / ".kit" / "sheet.json"
        d = json.loads(sheet.read_text(encoding="utf-8"))
        d["folder"] = str(twin / "Photos")
        for x in d["photos"]:
            x["file"] = str(twin / "Photos" / Path(x["file"]).name)
        sheet.write_text(json.dumps(d), encoding="utf-8")
    return twin


# ---------- 1. the names of a kit's pieces (in this program, on a queue that is never saved) ----------

def check_ids(s, pq):
    legacy_sid = "kit:" + pq.slug(KIT)
    old = {"pieces": [
        {"id": legacy_sid + "-reel", "shoot_id": legacy_sid, "shoot_name": SHORT, "kind": "reel", "status": "green", "slot": 1,
         "date": "2026-11-11", "thumb": None, "added": "2026-11-01T10:00:00"},
        {"id": legacy_sid + "-carousel", "shoot_id": legacy_sid, "shoot_name": SHORT, "kind": "carousel", "status": "yellow",
         "thumb": None, "added": "2026-11-01T10:00:00"},
        {"id": "s-0001-reel", "shoot_id": "s-0001", "shoot_name": "Garcia", "kind": "reel", "status": "red", "thumb": None, "added": "2026-11-01T10:00:00"}],
        "interval": 3.0, "reminded": {}}
    p = json.loads(json.dumps(old))
    pq.add_for_kit(p, s.kit)
    ids = [x["id"] for x in p["pieces"]]
    case("an older queue (pieces with no folder kept): adding the kit again makes no second piece and renames none",
         ids == [legacy_sid + "-reel", legacy_sid + "-carousel", "s-0001-reel"], ids)
    case("...its pieces now keep the folder they were made from, and the reel stays ready to post with its date",
         all(pq.kit_folder(x) == KIT for x in p["pieces"][:2]) and p["pieces"][0]["status"] == "green" and p["pieces"][0]["date"] == "2026-11-11",
         [(x.get("kit"), x["status"]) for x in p["pieces"][:2]])
    case("a piece made without a kit is nobody's kit piece", pq.kit_role(p["pieces"][2]) == "" and not pq.same_kit(p["pieces"][2], s.kit))

    twin = make_twin(s)
    case("the two folder names shorten to the same one", pq.slug(KIT) == pq.slug(TWIN) and KIT != TWIN, (pq.slug(KIT), pq.slug(TWIN)))
    before = json.dumps(p["pieces"][:2], sort_keys=True)
    pq.add_for_kit(p, twin)
    mine = [x for x in p["pieces"] if pq.same_kit(x, twin)]
    case("a second shoot whose name shortens alike can be added: two pieces of its own, under a name of their own",
         len(mine) == 2 and all(x["id"] not in ids for x in mine) and len({x["id"] for x in p["pieces"]}) == len(p["pieces"]),
         [x["id"] for x in mine])
    case("...the first shoot's pieces are exactly as they were", json.dumps(p["pieces"][:2], sort_keys=True) == before)
    case("...the new names are plain (letters, digits, dashes after 'kit:') and no longer than the old ones may be",
         all(re.fullmatch(r"kit:[a-z0-9-]{1,60}-(reel|carousel)", x["id"]) for x in mine), [x["id"] for x in mine])
    again = [x["id"] for x in p["pieces"]]
    pq.add_for_kit(p, twin)
    pq.add_for_kit(p, s.kit)
    case("adding either again changes no name and adds nothing", [x["id"] for x in p["pieces"]] == again)
    a, b = pq.kit_piece(p, s.kit, "reel"), pq.kit_piece(p, twin, "reel")
    case("each kit's reel is found by its own folder", a is p["pieces"][0] and b is not None and b is not a and pq.kit_folder(b) == TWIN)
    fresh = {"pieces": [], "interval": None, "reminded": {}}
    pq.add_for_kit(fresh, twin)
    case("alone in a queue, the second shoot takes the short name as ever (nothing changes for one kit)",
         [x["id"] for x in fresh["pieces"]] == [legacy_sid + "-reel", legacy_sid + "-carousel"], [x["id"] for x in fresh["pieces"]])

    # the reel's first tile
    import kit as kit_mod
    rec = kit_mod.load_rec(s.kit)
    photos = kit_mod.photo_files(kit_mod.photos_dir(s.kit, rec))
    f = pq.reel_first_photo(s.kit, rec, photos)
    case("a reel's tile is the reel's first photo (photo 3 of Claude's pick), not the kit's first photo",
         Path(str(f)).name == "beach-003.jpg" and Path(str(photos[0])).name == "beach-001.jpg", f)
    rp = s.kit / ".kit" / "reel-page.json"
    rp.write_text(json.dumps({"v": 1, "saved": {"mine": True, "picks": [{"n": 5, "h": ""}, {"n": 2, "h": ""}]}}), encoding="utf-8")
    try:
        f = pq.reel_first_photo(s.kit, rec, photos)
        case("...and when they dragged their own order in on the reel page, the first photo of that order (photo 5)", Path(str(f)).name == "beach-005.jpg", f)
    finally:
        rp.unlink()

    # a tile they picked stays theirs
    x = pq.kit_piece(p, s.kit, "reel")
    x["cover"], x["thumb"] = "Photos/beach-002.jpg", "posting-thumbs/theirs.jpg"
    pq.add_for_kit(p, s.kit)
    case("a tile they picked is not changed by adding the kit again", x["cover"] == "Photos/beach-002.jpg" and x["thumb"] == "posting-thumbs/theirs.jpg", x)
    x["cover"] = "Photos/gone.jpg"
    pq.add_for_kit(p, s.kit)
    case("a pick whose photo is gone is let go, and the tile is the usual one again", "cover" not in x and x["thumb"] != "posting-thumbs/theirs.jpg", x)

    # which photo a pick may name
    ok = pq.cover_file(s.kit, "reel", "Photos/beach-004.jpg")
    case("a pick names a photo by its folder word and its file name", ok is not None and ok.name == "beach-004.jpg")
    (s.kit / "Photos" / ".hidden.jpg").write_bytes(wpc.TINY)
    (s.kit / "Photos" / "not-on-the-list.jpg").write_bytes(wpc.TINY)
    bad = ["", "Photos", "Photos/", "/Photos/beach-001.jpg", "Photos/../Photos/beach-001.jpg", "Photos/..", "../" + KIT + "/Photos/beach-001.jpg",
           "Photos\\beach-001.jpg", "Photos/sub/beach-001.jpg", "Photos/.hidden.jpg", "Photos/not-on-the-list.jpg", ".kit/kit.json",
           "Carousel/Slide 01 (beach-001).jpg", "Singles/beach-001.jpg", str(s.kit / "Photos" / "beach-001.jpg"), "Photos/beach-001.jpg\x00", 7, None]
    got = [r for r in bad if pq.cover_file(s.kit, "reel", r) is not None]
    case("...and nothing else: no path, no '..', no backslash, no hidden file, no file off the numbered list, no other folder", not got, got)
    case("a carousel's pick is one of its slides only", pq.cover_file(s.kit, "carousel", "Carousel/Slide 02 (beach-002).jpg") is not None
         and pq.cover_file(s.kit, "carousel", "Photos/beach-001.jpg") is None and pq.cover_file(s.kit, "carousel", "Carousel/../Photos/beach-001.jpg") is None)
    (s.kit / "Photos" / "not-on-the-list.jpg").unlink()


# ---------- 2. the routes ----------

def check_routes(s):
    legacy_sid = "kit:" + re.sub(r"[^a-z0-9]+", "-", KIT.lower()).strip("-")[:40]
    rid, cid = legacy_sid + "-reel", legacy_sid + "-carousel"
    # an older posting.json, as a photographer's may be: the kit's reel with no folder kept
    s.write_posting({"pieces": [{"id": rid, "shoot_id": legacy_sid, "shoot_name": SHORT, "kind": "reel", "status": "yellow", "thumb": None,
                                 "added": "2026-11-01T10:00:00", "made_at": "2026-11-01T10:00:00"}], "interval": 3.0, "reminded": {}})
    code, _, raw = s.http("GET", "/posting.html")
    case("an older posting.json still loads: the posting page opens", code == 200 and b"id='pick'" in raw, code)
    code, j, _ = s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel"})
    code2, j2, _ = s.http("POST", "/words-queue", {"kit": KIT, "piece": "carousel"})
    x, y = piece(s, rid), piece(s, cid)
    case("Add to my queue on the older queue: the same piece, never renamed, now ready to post; the carousel beside it",
         code == 200 and code2 == 200 and x and y and x["status"] == "green" and y["status"] == "green" and len(s.posting()["pieces"]) == 2
         and x.get("date") == "2026-11-11" and y.get("date") == "2026-11-13", (code, j, code2, j2, s.posting()))
    first_thumb = x["thumb"]

    # the second shoot, by request
    make_twin(s)
    code, j, _ = s.http("POST", "/words-queue", {"kit": TWIN, "piece": "reel"})
    t = of_kit(s, TWIN, "reel")
    case("a second shoot whose name shortens to the same one is added too (it was refused before), under its own name",
         code == 200 and j and j.get("ok") and t and t["id"] != rid and t["status"] == "green" and piece(s, rid)["status"] == "green", (code, j, t))
    tid = t["id"] if t else ""
    code, j, _ = s.http("GET", "/words-state" + s.q("reel", TWIN))
    case("...each shoot's words page reads its own piece (the second one's date, not the first's)",
         j and j["queue"]["status"] == "green" and j["queue"]["date"] == (t or {}).get("date") != "2026-11-11" and s.state()["queue"]["date"] == "2026-11-11", j and j["queue"])

    # the state the page draws from
    g = green(s, rid) or {}
    raw_state = json.dumps(page_state(s))
    case("the page's state names a post's kit by its folder's name, says a click opens its panel, and holds no path",
         g.get("folder") == KIT and g.get("role") == "reel" and g.get("cover") is None and (green(s, tid) or {}).get("folder") == TWIN
         and str(s.work) not in raw_state and "Your Content" not in raw_state, g)

    # GET /posting/panel
    code, j, raw = panel(s, rid)
    rels = [c["rel"] for c in (j or {}).get("choices", [])]
    case("the reel's photos: its own first, in reel order (3, 1, 2, 4), then every other photo of the shoot",
         code == 200 and j["ok"] and rels == ["Photos/beach-%03d.jpg" % n for n in (3, 1, 2, 4, 5, 6)]
         and [c["in_reel"] for c in j["choices"]] == [True] * 4 + [False] * 2, (code, rels))
    case("...the one in use, with nothing picked, is the reel's first photo; no path in the answer",
         j["cover"] == "Photos/beach-003.jpg" and str(s.work) not in raw.decode("utf-8") and all(c["src"].startswith("/kit-photo?kit=") for c in j["choices"]), j.get("cover"))

    def pictures(choices):
        return [s.http("GET", c["src"])[0] for c in choices]
    try:
        chrome_drive.wait_until(lambda: set(pictures(j["choices"])) == {200}, 30, every=0.3, what="the small copies")
        made = True
    except Exception:  # noqa: BLE001
        made = False
    case("every photo in the strip is a small copy this server serves (made in the background the first time)", made, pictures(j["choices"]))
    code, jc, _ = panel(s, cid)
    case("the carousel's slides, in order, the first one marked",
         code == 200 and [c["rel"] for c in jc["choices"]] == ["Carousel/Slide %02d (beach-%03d).jpg" % (n, n) for n in (1, 2, 3, 4)]
         and [c["first"] for c in jc["choices"]] == [True, False, False, False] and jc["cover"] == jc["choices"][0]["rel"]
         and set(pictures(jc["choices"])) == {200}, jc)
    code, jt, _ = panel(s, tid)
    case("the second shoot's panel shows its own photos (its own folder in every address)",
         code == 200 and len(jt["choices"]) == 6 and all(("kit=" + quote(TWIN, safe="")) in c["src"] for c in jt["choices"]), jt)

    # a kit added from the chat, not ready yet: not an upcoming post
    s.make_long()
    code_l, out = s.cmd("posting_queue.py", "add", "--kit", str(s.content / LONG))
    lr = of_kit(s, LONG, "reel") or {}
    lid = lr.get("id", "")
    case("another kit added from the chat is in progress, under its own name", code_l == 0 and lr.get("status") == "yellow" and lid not in (rid, tid), (code_l, out[-200:], lr))
    port = s.port
    refusals = [
        ("another host", panel(s, rid, {"Host": "evil.example:%d" % port})[0], 403),
        ("another website's page", panel(s, rid, {"Sec-Fetch-Site": "cross-site"})[0], 403),
        ("a post that isn't upcoming (in progress)", panel(s, lid)[0], 404),
        ("no such post", panel(s, "kit:nobody-reel")[0], 404),
        ("no id", s.http("GET", "/posting/panel")[0], 404),
        ("an id that is a path", panel(s, "../../studio.json")[0], 404),
    ]
    case("GET /posting/panel refuses: " + ", ".join(n for n, _, _ in refusals), all(got == want for _, got, want in refusals), [(n, got) for n, got, _ in refusals])

    # POST /posting {action: "cover"}: the refusals
    (s.kit / "Photos" / ".hidden.jpg").write_bytes(wpc.TINY)
    before = (s.studio / "posting.json").read_bytes()
    thumbs_before = sorted(os.listdir(str(s.studio / "posting-thumbs")))
    own = "http://127.0.0.1:%d" % port
    tries = [
        ("another Origin", cover(s, rid, "Photos/beach-005.jpg", {"Origin": "http://evil.example"})[0], 403),
        ("another website's page", cover(s, rid, "Photos/beach-005.jpg", {"Origin": own, "Sec-Fetch-Site": "cross-site"})[0], 403),
        ("another host", cover(s, rid, "Photos/beach-005.jpg", {"Host": "evil.example:%d" % port})[0], 403),
        ("a body too big", s.http("POST", "/posting", {"action": "cover", "id": rid, "rel": "Photos/beach-005.jpg", "pad": "x" * 70000})[0], 413),
        ("'..'", cover(s, rid, "Photos/../.kit/kit.json")[0], 400),
        ("a way out of the kit", cover(s, rid, "../../studio/studio.json")[0], 400),
        ("a whole path", cover(s, rid, str(s.kit / "Photos" / "beach-005.jpg"))[0], 400),
        ("a backslash", cover(s, rid, "Photos\\beach-005.jpg")[0], 400),
        ("a hidden file", cover(s, rid, "Photos/.hidden.jpg")[0], 400),
        ("the kit's records", cover(s, rid, ".kit/kit.json")[0], 400),
        ("another kit's photo", cover(s, rid, "Photos/p1.jpg")[0], 400),
        ("another kit's slide for this carousel", cover(s, cid, "Carousel/Slide 01 (p1).jpg")[0], 400),
        ("a slide for the reel", cover(s, rid, "Carousel/Slide 01 (beach-001).jpg")[0], 400),
        ("a photo for the carousel", cover(s, cid, "Photos/beach-001.jpg")[0], 400),
        ("a photo that isn't text", cover(s, rid, ["Photos/beach-005.jpg"])[0], 400),
        ("a piece that isn't upcoming", cover(s, lid, "Photos/p1.jpg")[0], 400),
        ("no such piece", cover(s, "kit:nobody-reel", "Photos/beach-005.jpg")[0], 400),
        ("a body that isn't a press", s.http("POST", "/posting", ["cover"])[0], 400),
    ]
    case("a pick is refused: " + ", ".join(n for n, _, _ in tries), all(got == want for _, got, want in tries), [(n, got) for n, got, _ in tries if got != _])
    case("...and nothing was changed by any of them: the queue byte for byte, no new tile",
         (s.studio / "posting.json").read_bytes() == before and sorted(os.listdir(str(s.studio / "posting-thumbs"))) == thumbs_before)

    # a pick
    code, j, _ = cover(s, rid, "Photos/beach-005.jpg", {"Origin": own})
    x = piece(s, rid)
    g = next((z for z in (j or {}).get("greens", []) if z["id"] == rid), {})
    new_thumb = x.get("thumb") or ""
    case("a pick is saved at once: the cover on the piece, and the answer is the page's new state",
         code == 200 and x.get("cover") == "Photos/beach-005.jpg" and g.get("cover") == "Photos/beach-005.jpg" and g.get("thumb") == new_thumb, (code, x))
    case("the tile is a new file in the thumbnails folder under a new name, and the earlier tile is still there",
         new_thumb != first_thumb and new_thumb.startswith("posting-thumbs/") and (s.studio / new_thumb).is_file() and (s.studio / first_thumb).is_file()
         and s.http("GET", "/" + quote(new_thumb))[0] == 200, (first_thumb, new_thumb))
    n_thumbs = len(os.listdir(str(s.studio / "posting-thumbs")))
    cover(s, rid, "Photos/beach-006.jpg")
    cover(s, rid, "Photos/beach-005.jpg")
    case("picking the same photo again uses the tile already made", piece(s, rid)["thumb"] == new_thumb and len(os.listdir(str(s.studio / "posting-thumbs"))) == n_thumbs + 1)
    case("the panel now shows that photo as the one in use", panel(s, rid)[1]["cover"] == "Photos/beach-005.jpg")
    case("the other shoot's reel was not touched", "cover" not in (of_kit(s, TWIN, "reel") or {"cover": 1}))

    # decision 8: the kit follows it
    q = s.state()["queue"]
    kq = quote(KIT, safe="")
    page = s.http("GET", "/content/%s/Post%%20kit.html" % kq)[2].decode("utf-8")
    case("the words page's Post it step is handed the picked photo (the queue's own tile)", q["cover"] is True and q["thumb"] == "/" + quote(new_thumb, safe="/"), q)
    case("the kit page's queue step shows the picked photo", ("class='qpic' src='%s'" % html.escape("/" + quote(new_thumb, safe="/"))) in page, re.findall(r"<img class='qpic'[^>]*>", page))
    code, j, _ = cover(s, cid, "Carousel/Slide 03 (beach-003).jpg")
    q = s.http("GET", "/words-state" + s.q("carousel"))[1]["queue"]
    case("a carousel's pick is kept as 'Carousel/<the slide's file>', and the words page knows it is slide 3",
         code == 200 and piece(s, cid)["cover"] == "Carousel/Slide 03 (beach-003).jpg" and q["cover"] is True and q["cover_slide"] == 3, q)
    s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel"})
    case("adding the kit again leaves both picks and both tiles as they picked them",
         piece(s, rid)["thumb"] == new_thumb and piece(s, rid)["cover"] == "Photos/beach-005.jpg" and piece(s, cid)["cover"] == "Carousel/Slide 03 (beach-003).jpg")
    # the slides made again without the one they picked
    gone = s.kit / "Carousel" / "Slide 03 (beach-003).jpg"
    aside = s.work / "slide-3-aside.jpg"
    shutil.move(str(gone), str(aside))
    try:
        s.cmd("posting_queue.py", "add", "--kit", str(s.kit))
        y = piece(s, cid)
        case("when the slide they picked is no longer one of the carousel's, the pick is let go and the tile is the first slide again",
             "cover" not in y and y["thumb"] and piece(s, rid)["cover"] == "Photos/beach-005.jpg", y)
    finally:
        shutil.move(str(aside), str(gone))

    # the words, straight from the words record
    w = panel(s, rid)[1]["words"]
    case("the panel's words: the caption whole, and no hook while none is picked", w == {"piece": "reel", "caption": CAPTION.strip(), "hook": ""}, w)
    s.save("reel", picked=[2, 0])
    case("...the hook is the first one they picked", panel(s, rid)[1]["words"]["hook"] == HOOKS[2], panel(s, rid)[1]["words"])
    wc = panel(s, cid)[1]["words"]
    case("a carousel has its caption (their own typed one, when that is all there is) and never a hook", wc == {"piece": "carousel", "caption": OWN, "hook": ""}, wc)
    s.save("carousel", own="")
    case("no caption yet: the caption is empty", panel(s, cid)[1]["words"]["caption"] == "")
    s.save("carousel", own=OWN)
    return rid, cid, tid, lid


# ---------- 3. the page ----------

PANEL = "document.getElementById('pick')"
OPEN = "(function(){ var p = %s; return !!p && !p.hidden && !!p.parentNode && p.parentNode.id === 'grid'; })()" % PANEL
OPEN_ID = "(function(){ var p = %s; return p && !p.hidden ? (p.dataset.id || '') : ''; })()" % PANEL
TOAST = "(function(){ var t = document.getElementById('toast'); return t.classList.contains('on') ? t.textContent : ''; })()"
READY = "(function(){ var p = %s; return !!p && !p.hidden && !p.querySelector('.strip .empty') && p.querySelectorAll('.strip .c').length > 0; })()" % PANEL
WHERE = ("(function(){ var p = %s, g = document.getElementById('grid'), kids = Array.from(g.children), tiles = kids.filter(function(c){ return c !== p; });"
         " return {at: kids.indexOf(p), before: p.previousElementSibling ? tiles.indexOf(p.previousElementSibling) : -1, tiles: tiles.length,"
         " w: p.getBoundingClientRect().width, gw: g.getBoundingClientRect().width, picking: Array.from(g.querySelectorAll('.tile.picking')).map(function(t){ return t.dataset.id; })}; })()" % PANEL)
ORDER = "Array.from(document.querySelectorAll('#grid .tile.mine')).map(function(t){ return t.dataset.id; })"
STUB_COPY = ("window.__copied = []; document.execCommand = function(c){ var a = document.activeElement;"
             " window.__copied.push([c, a && a.value]); return true; };")


def tile(pid):
    return "#grid .tile.mine[data-id=%s]" % json.dumps(pid)


def press_small(c, selector, dx):
    """A press that moves dx pixels before it is let go (a hand is never perfectly still)."""
    x, y = c.point(selector)
    c.mouse_move(x, y)
    c.mouse_press()
    if dx:
        c.mouse_move(x + dx, y)
    c.mouse_release()


def open_panel(c, pid):
    if c.js(OPEN_ID) != pid:
        press_small(c, tile(pid), 0)
    c.wait_for("%s === %s && %s" % (OPEN_ID, json.dumps(pid), READY), 10)


def wait_toast(c, text):
    try:
        c.wait_for("%s === %s" % (TOAST, json.dumps(text)), 5)
        return True
    except Exception:  # noqa: BLE001
        return c.js(TOAST)


def check_page(c, s, ids):
    rid, cid, tid, lid = ids
    # five upcoming posts, so the grid has a second row: the long-named kit's two go ready as well
    lcar = (of_kit(s, LONG, "carousel") or {}).get("id", "")
    for pid in (lid, lcar):
        s.http("POST", "/posting", {"action": "ready", "id": pid})
    c.open(s.url("/posting.html"))
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 5", 10)
    order = c.js(ORDER)                      # newest first: the last in line is top-left
    case("the grid shows the five upcoming posts, the next one to post last", len(order) == 5 and order[-1] == rid, order)
    case("her note above the grid, in coral, with its pencil", c.text("#pickhint") == HINT and c.js("!document.getElementById('pickhint').hidden")
         and c.js("getComputedStyle(document.getElementById('pickhint'), ':before').content") in ('"✎"', "'✎'")
         and c.js("getComputedStyle(document.getElementById('pickhint')).color") == "rgb(212, 100, 63)",
         (c.text("#pickhint"), c.js("getComputedStyle(document.getElementById('pickhint')).color")))
    case("the section's sentence, hers", SENTENCE in c.js("document.body.textContent"))
    case("an upcoming tile's tooltip, hers", c.js("document.querySelector(%s).title" % json.dumps(tile(rid))) == TIP)
    case("nothing is open until a post is clicked", c.js(OPEN) is False and c.js("%s.hidden" % PANEL) is True)

    # a click: a press that moves less than 6 px
    row1, row2 = order[0], order[3]          # a post in the first row of three, and one in the second
    press_small(c, tile(row2), 5)
    c.wait_for("%s === %s && %s" % (OPEN_ID, json.dumps(row2), READY), 10)
    w = c.js(WHERE)
    case("a press that moves 5 px opens the post's panel, and the order is as it was", c.js(ORDER) == order, c.js(ORDER))
    case("the panel is right under that post's row (after the sixth tile, before the next row), across all three columns",
         w["before"] == 5 and w["at"] == 6 and abs(w["w"] - w["gw"]) <= 10, w)
    try:                                      # the outline eases in (the tile's own .35 s)
        c.wait_for("getComputedStyle(document.querySelector(%s)).boxShadow.indexOf(' 4px inset') >= 0" % json.dumps(tile(row2)), 10)
    except Exception:  # noqa: BLE001
        pass
    shadow = c.js("getComputedStyle(document.querySelector(%s)).boxShadow" % json.dumps(tile(row2)))
    case("the clicked tile is outlined 4 px in the dark coral, and only that one", w["picking"] == [row2] and "rgb(212, 100, 63)" in shadow and " 4px inset" in shadow, (w["picking"], shadow))
    press_small(c, tile(row2), 0)
    c.wait_for("%s === ''" % OPEN_ID, 5)
    case("clicking the same post again closes it, and the outline goes", c.js("%s.hidden" % PANEL) is True and c.count(".tile.picking") == 0)
    press_small(c, tile(row1), 2)
    c.wait_for("%s === %s && %s" % (OPEN_ID, json.dumps(row1), READY), 10)
    w = c.js(WHERE)
    case("a post in the first row: the panel sits after the third tile", w["before"] == 2 and w["at"] == 3 and w["picking"] == [row1], w)
    c.click("#pick .x")
    case("Done closes it", c.js("%s.hidden" % PANEL) is True and c.text("#pick .x") is None and c.count(".tile.picking") == 0)

    # a drag still moves the tile, and opens nothing
    a, b = order[0], order[1]
    c.drag(tile(a), tile(b), steps=14)
    c.wait_for("JSON.stringify(%s) !== %s" % (ORDER, json.dumps(json.dumps(order, separators=(",", ":")))), 10)
    moved = c.js(ORDER)
    case("a real drag moves the tile onto the other's place (the dates follow), and no panel opens",
         moved[:2] == [b, a] and moved[2:] == order[2:] and c.js("%s.hidden" % PANEL) is True and wait_toast(c, "Moved. The dates follow the order.") is True, moved)
    c.drag(tile(a), tile(b), steps=14)
    c.wait_for("JSON.stringify(%s) === %s" % (ORDER, json.dumps(json.dumps(order, separators=(",", ":")))), 10)

    # the reel's panel
    c.js(STUB_COPY)
    open_panel(c, rid)
    head = c.text("#pick .ph b")
    case("the heading is 'Your <shoot> reel', the shoot's name shown as text (a tag in it is never a tag)",
         head == "Your %s reel" % SHORT and c.count("#pick .ph b *") == 0, head)
    case("the line under it, hers", c.text("#pick .ph p") == REEL_LINE, c.text("#pick .ph p"))
    row = c.js("Array.from(document.querySelectorAll('#pick .pw > *')).filter(function(e){ return e.textContent; }).map(function(e){ return [e.tagName, e.textContent]; })")
    case("the button row: Copy caption (dark), Copy my hook, Set a reminder to post, Open my words →", row == [["BUTTON", "Copy caption"], ["BUTTON", "Copy my hook"], ["SPAN", "Set a reminder to post"], ["A", "Open my words →"]]
         and c.js("getComputedStyle(document.querySelector('#pick .pw [data-c=cap]')).backgroundColor") == c.js("getComputedStyle(document.querySelector('.homelink')).backgroundColor"), row)
    case("...it sits right under the heading and above the photos, with the reminder's place in it between the hook and the link",
         c.js("(function(){ var k = Array.from(%s.children).map(function(e){ return e.className; }); return k.join(' '); })()" % PANEL) == "ph pw pr pn strip warn"
         and c.js("Array.from(document.querySelectorAll('#pick .pw > *')).map(function(e){ return e.className; }).join('|')") == "btn|btn o|rslot|pwl"
         and c.js("document.querySelector('#pick .rslot').dataset.remindSlot") == rid)
    href = c.js("document.querySelector('#pick .pwl').getAttribute('href')")
    case("Open my words leads to this post's words page on this same server", href == "/words.html?kit=%s&piece=reel" % quote(KIT, safe="~()*!.'"), href)
    strip = c.js("Array.from(document.querySelectorAll('#pick .strip > *')).map(function(e){ return e.className === 'sep' ? 'SEP:' + e.textContent : e.dataset.rel + (e.classList.contains('on') ? ' ON' : ''); })")
    case("the strip: the reel's photos in reel order, 'More from the shoot', then the rest; the one in use marked",
         strip == ["Photos/beach-003.jpg", "Photos/beach-001.jpg", "Photos/beach-002.jpg", "Photos/beach-004.jpg", "SEP:More from the shoot", "Photos/beach-005.jpg ON", "Photos/beach-006.jpg"], strip)
    r = c.rect("#pick .c")
    case("each photo is 96 px wide and 4:5, the one in use has its ✓, and a reel's photos carry no numbers",
         abs(r["w"] - 96) < 0.6 and abs(r["h"] - 120) < 0.6 and c.js("getComputedStyle(document.querySelector('#pick .c.on'), '::after').content") in ('"✓"', "'✓'")
         and c.count("#pick .c .n") == 0, r)
    case("the strip scrolls sideways inside the panel, never the page", c.js("getComputedStyle(document.querySelector('#pick .strip')).overflowX") == "auto"
         and c.js("document.documentElement.scrollWidth <= window.innerWidth"))
    case("every photo in the strip loaded", c.js("Array.from(document.querySelectorAll('#pick .c img')).every(function(i){ return i.complete && i.naturalWidth > 0; })"))

    # a pick: saved at once, the tile changes, the panel stays
    src0 = c.js("document.querySelector(%s + ' img').getAttribute('src')" % json.dumps(tile(rid)))
    c.click("#pick .c[data-rel='Photos/beach-002.jpg']")
    said = wait_toast(c, T_REEL)
    c.wait_for("document.querySelector(\"#pick .c[data-rel='Photos/beach-002.jpg']\").classList.contains('on')", 10)
    src1 = c.js("document.querySelector(%s + ' img').getAttribute('src')" % json.dumps(tile(rid)))
    case("clicking a photo saves it at once: her toast, the grid tile shows the new picture", said is True and src1 != src0 and piece(s, rid)["cover"] == "Photos/beach-002.jpg", (said, src0, src1))
    w = c.js(WHERE)
    case("the panel stays open through the redraw, under the same post's row, the tile still outlined, one ✓",
         c.js(OPEN_ID) == rid and w["picking"] == [rid] and w["before"] == 5 and c.count("#pick .c.on") == 1, w)
    # a change somewhere else on the page: the panel survives and is put back
    c.click("#greens [data-a='unready'][data-id=%s]" % json.dumps(lcar))
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 4", 10)
    c.wait_for(READY, 10)
    w = c.js(WHERE)
    case("another post taken out of the line: the panel is still open, back under its own post's row",
         c.js(OPEN_ID) == rid and w["picking"] == [rid] and w["before"] == 5 and w["at"] == 6 and c.js(OPEN), w)

    # copy
    c.click("#pick .pw [data-c=cap]")
    said = wait_toast(c, T_CAPTION)
    copied = c.js("window.__copied")
    case("Copy caption: the whole caption is copied the old way (the Claude app's pane refuses the new one), with her toast",
         said is True and copied and copied[-1] == ["copy", CAPTION.strip()], (said, copied))
    c.click("#pick .pw [data-c=hook]")
    said = wait_toast(c, T_HOOK)
    case("Copy my hook: the first hook they picked, with her toast", said is True and c.js("window.__copied")[-1] == ["copy", HOOKS[2]], (said, c.js("window.__copied")[-1]))
    case("a caption with a tag, quotes and a script in it only ever reached the clipboard: nothing ran, nothing was drawn",
         c.js("window.pwned === undefined") and c.count("#pick img[src='x']") == 0 and NASTY not in c.js("%s.innerHTML" % PANEL))
    s.save("reel", picked=[])
    c.click("#pick .x")
    open_panel(c, rid)
    n = len(c.js("window.__copied"))
    tip = c.js("document.querySelector('#pick .pw [data-c=hook]').title")
    c.click("#pick .pw [data-c=hook]")
    said = wait_toast(c, T_NO_HOOK)
    case("Copy my hook with none picked: her line, and nothing is copied", said is True and len(c.js("window.__copied")) == n and tip == "Pick a hook on your words page first", (said, tip))
    s.save("reel", picked=[2, 0])

    # the carousel's panel
    press_small(c, tile(cid), 3)
    c.wait_for("%s === %s && %s" % (OPEN_ID, json.dumps(cid), READY), 10)
    case("another post clicked: the panel is that post's now, and only its tile is outlined", c.js(WHERE)["picking"] == [cid] and c.text("#pick .ph b") == "Your %s carousel" % SHORT)
    case("the carousel's line, hers", c.text("#pick .ph p") == CAR_LINE)
    nums = c.js("Array.from(document.querySelectorAll('#pick .c')).map(function(b){ return [b.querySelector('.n').textContent, b.title, b.classList.contains('on')]; })")
    case("the slides are numbered 1 to 4, the first in use, no divider", nums == [["1", "Slide 1", True], ["2", "Slide 2", False], ["3", "Slide 3", False], ["4", "Slide 4", False]]
         and c.count("#pick .sep") == 0, nums)
    case("on the first slide there is no warning", c.text("#pick .warn") == "" and c.js("getComputedStyle(document.querySelector('#pick .warn')).display") == "none")
    row = c.js("Array.from(document.querySelectorAll('#pick .pw > *')).filter(function(e){ return e.textContent; }).map(function(e){ return e.textContent; })")
    case("a carousel's row has no hook button", row == ["Copy caption", "Set a reminder to post", "Open my words →"]
         and c.js("document.querySelector('#pick .pwl').getAttribute('href')").endswith("&piece=carousel"), row)
    c.click("#pick .pw [data-c=cap]")
    case("Copy caption copies their own caption when that is all there is", wait_toast(c, T_CAPTION) is True and c.js("window.__copied")[-1] == ["copy", OWN])
    c.click("#pick .c", nth=2)
    said = wait_toast(c, T_CAR)
    c.wait_for("document.querySelectorAll('#pick .c')[2].classList.contains('on')", 10)
    case("picking slide 3: her toast, and the pale orange box says it isn't the first slide, in her words",
         said is True and c.text("#pick .warn") == WARN and c.js("getComputedStyle(document.querySelector('#pick .warn')).backgroundColor") == "rgb(255, 244, 236)"
         and piece(s, cid)["cover"] == "Carousel/Slide 03 (beach-003).jpg", (said, c.text("#pick .warn")))
    c.click("#pick .c", nth=0)
    c.wait_for("document.querySelectorAll('#pick .c')[0].classList.contains('on')", 10)
    case("back on slide 1 the warning goes", c.text("#pick .warn") == "")
    s.save("carousel", own="")
    c.click("#pick .x")
    open_panel(c, cid)
    row = c.js("Array.from(document.querySelectorAll('#pick .pw > *')).filter(function(e){ return e.textContent; }).map(function(e){ return [e.tagName, e.textContent]; })")
    case("no caption yet: the row reads 'No caption yet.' with Set a reminder to post and 'Write my words →', and there is nothing to copy",
         row == [["SPAN", "No caption yet."], ["SPAN", "Set a reminder to post"], ["A", "Write my words →"]] and c.count("#pick .pw button[data-c]") == 0, row)
    s.save("carousel", own=OWN)

    # the post itself leaves the line: its panel closes
    c.click("#greens [data-a='unready'][data-id=%s]" % json.dumps(cid))
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 3", 10)
    case("the open post marked 'Not ready yet': its panel closes with it", c.js("%s.hidden" % PANEL) is True and c.count(".tile.picking") == 0)

    # a kit that can't be reached: her line, and the page is fine
    away = s.content / (TWIN + " away")
    os.rename(str(s.content / TWIN), str(away))
    try:
        press_small(c, tile(tid), 0)
        c.wait_for("%s === %s && !!document.querySelector('#pick .strip .empty') && document.querySelector('#pick .strip .empty').textContent !== 'Finding the photos…'" % (OPEN_ID, json.dumps(tid)), 10)
        case("a post whose kit can't be reached right now: her line, and no row of buttons", c.text("#pick .strip .empty") == CANT and c.count("#pick .pw > *") == 0, c.text("#pick .strip .empty"))
    finally:
        os.rename(str(away), str(s.content / TWIN))
    c.click("#pick .x")

    # the keyboard, a phone, and a clean page
    c.js("document.querySelector(%s).focus()" % json.dumps(tile(rid)))
    c.key("Enter")
    c.wait_for("%s === %s" % (OPEN_ID, json.dumps(rid)), 5)
    case("Enter on a post's tile opens its panel too", c.js(OPEN_ID) == rid)
    c.phone()
    c.wait_for(READY, 10)
    case("at a phone's width the open panel never makes the page scroll sideways", c.js("document.documentElement.scrollWidth <= window.innerWidth"),
         c.js("[document.documentElement.scrollWidth, window.innerWidth]"))
    c.desktop()
    errs = [e for e in c.page_errors() if "favicon" not in e]
    case("the page ran clean (no error), asked nothing of the internet, and nothing of theirs ran as code",
         not errs and not c.outside_requests() and c.js("window.pwned === undefined"), (errs, c.outside_requests()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=8950)
    ap.add_argument("--no-chrome", action="store_true", help="the routes only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="posting-panel-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    s = wpc.Setup(work, a.port)
    s.env["REMINDERS_BACKEND"] = "file"       # never the real Calendar
    os.environ["REMINDERS_BACKEND"] = "file"
    s.make()
    rec = s.kit_rec()
    rec["picks"]["reel"] = [3, 1, 2, 4]       # the reel's first photo is not the kit's first
    s.write_kit(rec)
    s.reel_made()
    s.slides_made(4)
    s.words("draft", "reel", {"caption": CAPTION, "hooks": HOOKS})
    wpc.page_module(s)
    import posting_queue as pq
    try:
        s.start()
        s.save("carousel", own=OWN)
        s.stop()
        group("the names of a kit's pieces", check_ids, s, pq)
        for f in (s.studio / "posting.json",):
            if f.exists():
                f.unlink()
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 20)
        ids = group("the routes", check_routes, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        elif not ids:
            skip("the page in a browser: the routes did not run to their end")
        else:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                group("the page", check_page, c, s, ids)
    finally:
        s.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return wpc.summary()


if __name__ == "__main__":
    sys.exit(main())
