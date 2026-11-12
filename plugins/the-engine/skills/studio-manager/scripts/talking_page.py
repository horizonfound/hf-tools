#!/usr/bin/env python3
"""The talking reel page: Nicole's handoff v24 (pages/talking-reel.html), as the Assistant's own page.

    python3 talking_page.py open "<shoot>"        prints the page's address, to load in the pane

They record themselves talking about a shoot, drag the video into the shoot's Talking folder, and this page turns
it into a script they can cut, put photos and videos on, and send to CapCut. The photographer sees her page: her
words (WORDS, word for word from her talking-reel.html, talking_core.py and server.py), her layout, her steps.
Underneath it is ours: served by the posting server like the reel page and the words page, every request behind
the pickers' guard, the record kept by talking_rec.py (one writer at a time, a counter so a page can never wipe
what the chat just wrote), no path and no file's place ever sent to or taken from the page, every word of theirs
put on the page as text.

The page is built in sub-stages (the plan, Stage C). This file, talking_css.py, talking_js_core.py and
talking_js_step1.py are C1: the whole page's structure, every route, the state and its 3-second refresh, and
step 1 (Add my video, the videos, Edit my video, the status line, who places the photos, the lines to copy).
C2 is talking_js_script.py (the sentences, a click on a word, the highlight bar, the Move row, the bars above the
words, dragging a bar, a bar's menu) and talking_js_pick.py (the photo picker and the video picker).
C3 is talking_js_preview.py (playing the cut or the whole, a photo or a video where it will sit, themselves in
the corner, the zooms, the captions, dragging and sizing on the preview, the phone guides, step 3's chips).
The timeline is its own file, added to JS_PARTS when it is built; until then the timeline shows its frame and
nothing moves in it but its round play button.

Routes (GET: our host, never another website's page; POST: the pickers' guard, then one JSON object; the kit by
its folder name; everything wrapped so the server stays up):
    GET  /talking.html?kit=              the page
    GET  /talking-state?kit=[&rev=&mark=]   talking_rec.state_for_page: everything the page draws from; with the
                                         counter and the mark the page holds, only {ok, rev, mark, working, step,
                                         make} while neither has moved (a long talk's whole state is about half a
                                         megabyte, and the page asks every 3 seconds)
    GET  /talking-video?kit=             the small copy of their talking video, in pieces when asked (Range)
    POST /talking-open  {kit}            makes <kit>/Talking if it isn't there and opens it
    POST /talking-start {kit, video}     Edit my video: `video` is the key the state gave. A video whose script
                                         was made before comes back with its edit, nothing transcribed again;
                                         otherwise a job of its own turns it into words (talking_rec.start)
    POST /talking-save  {kit, base, page, saved}   talking_rec.save_from_page (up to SAVE_CAP bytes)
    POST /talking-make  {kit}            Make it in CapCut (talking_rec.start_make)
The video picker uses the reel page's own routes: /reel-footage?kit=&for=talking (the list only: no "not ready",
the reel page's record never rewritten; asked ONLY when the picker opens, since asking gets every Footage video
ready), /reel-video, /reel-strip, /reel-open {what: "footage"}. The photos are the pickers' small copies
(/kit-photo, by number); which photos there are rides on every whole state ("photos", see _to_draw).

A Mac and a PC: the page opens on both. On a PC Edit my video answers this_computer.NO_TALKING_PC at once (a named
gap); "Finder" reads File Explorer and the two Undo tooltips name Ctrl.
"""
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arrange          # noqa: E402
import brand            # noqa: E402
import look             # noqa: E402
import reel_page        # noqa: E402
import this_computer    # noqa: E402
import talking_rec as TR  # noqa: E402
import talking_css      # noqa: E402
import talking_js_core  # noqa: E402
import talking_js_step1  # noqa: E402
import talking_js_script  # noqa: E402
import talking_js_pick  # noqa: E402
import talking_js_preview  # noqa: E402

GET_PATHS = ("/talking.html", "/talking-state", "/talking-video")
POST_PATHS = ("/talking-open", "/talking-start", "/talking-save", "/talking-make")
SAVE_CAP = 200000            # hers: a save may be this big (2000 cuts and 500 stretches)
LOOK_EVERY_MS = 3000         # hers: the page looks for the assistant's cut, and a finished script, every 3 seconds
TOAST_MS = 2600              # hers
UNDO_STEPS = 60              # hers
REV = re.compile(r"[0-9]{1,12}")
MARK = re.compile(r"[0-9a-f]{12}")
# The page's script, in the order it runs. Each later sub-stage adds its own file here.
JS_PARTS = (talking_js_core.JS, talking_js_step1.JS, talking_js_script.JS, talking_js_pick.JS, talking_js_preview.JS)
FOOTAGE_EVERY_MS = 4000      # hers: while the video picker is open and a video is still being got ready
COPIES_EVERY_MS = 4000       # ours: while a photo the page shows has no small copy yet, look for it again
COPIES_TRIES = 90            # ...this many times with nothing new, then no more (a copy that never comes)
START_JS = "window.Talk.start();"

# Every line of hers a photographer can see on this page, word for word (pages/talking-reel.html, v24; the lines
# her server and her engine send are talking_rec.JOB_WORDS and MAKE_WORDS, joined in below). In a line, {b} and
# {eb} are where her bold starts and ends, {br} her line break, and any other {name} a blank the page fills in
# (always as text). tests/talking_page_check.py --only words compares these with her files, both ways.
WORDS = {
    "back_kit": "Back to the post kit",
    "eyebrow": "Talking reel",
    "title": "{short} talking reel",
    "doc_title": "{short} · talking reel",
    "lede": "Record your talking-to-camera reel, as messy as you like. Your assistant cuts the video for you; then you "
            "watch it, cut or bring back words, and add your photos or videos. Then it's made in CapCut.",
    # step 1
    "s1_h2": "Your video",
    "s1_say": "Press {b}Add my video{eb} and this shoot's Talking folder opens.{br}Drag your video in, pick it here, "
              "then press {b}Edit my video{eb}.",
    "add_video": "▶ Add my video",
    "edit_video": "Edit my video",
    "no_videos": "No videos in the Talking folder yet.",
    "talking_open": "Your Talking folder is open in Finder",
    "swap_ask": "{b}Edit {new} instead?{eb} Your edit of {old} is kept, but this page will show the new one. Press "
                "{b}Edit my video{eb} again to go ahead.",
    "working": "Working on it…",
    "status_working": "{b}{step}{eb} A minute of video takes about a minute.",
    "status_ready": "{b}{video}{eb}: {n} words, {dur} of video",
    "status_after": ", {b}{after}{eb} after the cuts.",
    "secs": "{t} s",
    "cut_say": "Copy this into the chat, and your assistant cuts the script like an editor: the warm-up, the restarts, "
               "the words said twice. Nothing you keep is changed.",
    "cut_line": "Cut my talking reel for {short}",
    "copy": "Copy",
    "copied": "Copied. Paste it into the chat.",
    "who_h": "Your photos and videos",
    "who_say": "Who puts them with what you say?",
    "who_me": "I'll add them",
    "who_me_say": "Highlight any words, then Add photos or Add video.",
    "who_me_toast": "Highlight any words, then Add photos or Add video",
    "who_asst": "My assistant places them",
    "who_asst_say": "A photo with each part. Swap any you like.",
    "place_say": "Copy this into the chat, and your assistant puts your photos with what you say:",
    "place_say_wait": "Once your script is ready, copy this into the chat and your assistant puts your photos with what "
                      "you say:",
    "place_line": "Place the photos in my talking reel for {short}",
    "cut_place_line": "Cut my talking reel and place the photos for {short}",
    "didnt_work": "That didn't work",
    # step 2: the script and the preview
    "s2_h2": "Watch it and make it yours",
    "s2_say": "Click any word to play from there; the spacebar plays and pauses. {b}Highlight words{eb} to add photos or "
              "a video there, cut them, bring them back, or add a punch in or a slow zoom. Each photo sits above the "
              "words it goes with: click it for where it goes, drag its ends to stretch or shrink it, or drag it to move "
              "it. On the preview, drag a photo, yourself in the corner or the caption to move it; the round handle "
              "makes it bigger or smaller.",
    "punch": "Punch in",
    "slow_zoom": "Slow zoom",
    "sped_up": "Sped up",
    "cut": "Cut",
    "screen_title": "Click to play or pause",
    "knob_photo": "Drag to make the photo bigger or smaller",
    "knob_me": "Drag to make yourself bigger or smaller",
    "knob_cap": "Drag to make the captions bigger or smaller",
    "g_reels": "Reels", "g_likes": "1,204", "g_comments": "36", "g_shares": "18", "g_user": "yourname",
    "g_follow": "Follow", "g_audio": "♫ Original audio",
    "guides": "Phone guides",
    "guides_title": "Shows what Instagram covers on a reel",
    "cut_mode": "Play the cut version",
    "move": "Move",
    "move_none": "None",
    "move_part": "on part of it",
    # the highlight bar
    "sel_photo": "+ Add photos",
    "sel_video": "+ Add video",
    "sel_back": "Bring back",
    "sel_nozoom": "No zoom",
    "zoom_punch_toast": "Punch in on those words",
    "zoom_slow_toast": "Slow zoom across those words",
    "zoom_none_toast": "No zoom on those words",
    # a photo's bar, its menu, the photo picker
    "spot_full": "Full screen",
    "spot_pip": "Full screen, you in the corner",
    "spot_center": "Center",
    "spot_corner": "Small corner",
    "spot_short_pip": "You in corner",
    "spot_short_corner": "Corner",
    "now_on": "Now on “{words}”",
    "change_video": "Change video",
    "change_photos": "Change photos",
    "change_photo": "Change photo",
    "remove_one": "Remove this one",
    "remove": "Remove",
    "remove_all": "Remove all {n}",
    "put_back": "Put it back",
    "removed": "Removed. Undo brings it back.",
    "removed_many": "Removed. Undo brings them back.",
    "pm_words": "“{words}”",
    "pick_head": "Pick photos",
    "pick_alt": "Photo {n}",
    "pick_for": "Photos for “{words}”",
    "close": "Close",
    "pick_say": "Pick one, or several to flash through those words one after another, in the order you click them.",
    "pick_use": "Use this photo",
    "pick_use_many": "Use these {n}",
    "pick_count": "{n} photos, flashing through in this order",
    # the video picker
    "vp_head": "Add a video",
    "vp_for": "A video for “{words}”",
    "vp_say": "Your videos come from this shoot's Footage folder. Pick one, find where it should start, and press "
              "{b}Use from here{eb}. It plays without its sound, under what you're saying.",
    "vp_use": "Use from here",
    "vp_at": "Starts at {t}",
    "vp_wait": "{length} · getting it ready",
    "vp_none": "No videos in this shoot's Footage folder yet. Press {b}Open my Footage folder{eb}, drag your videos in, "
               "then press {b}I added videos{eb}.",
    "vp_open": "Open my Footage folder",
    "vp_refresh": "I added videos",
    "footage_open": "Your Footage folder is open in Finder",
    # step 3
    "s3_h2": "Captions",
    "s3_say": "Your words on screen one at a time, as you say them. Drag the word on the preview to put your captions "
              "wherever you like, and drag its round handle to make them bigger or smaller. They come into CapCut as "
              "plain text so you can give them your own style there.",
    "cap_on": "Captions on",
    "cap_off": "No captions",
    "cap_reset": "Put the captions back to how they were",
    # the timeline
    "play": "Play",
    "pause": "Pause",
    "split": "Split",
    "split_title": "Split the clip where the line is",
    "delete": "🗑 Delete",
    "delete_title": "Delete the clip you picked (or press Delete)",
    "delete_clip": "🗑 Delete clip",
    "delete_photo": "🗑 Delete photo",
    "speed": "Speed",
    "zoom": "Zoom",
    "undo": "↶ Undo",
    "redo": "↷ Redo",
    "undo_title": "Undo (⌘Z)",
    "redo_title": "Redo (⇧⌘Z)",
    "zoom_out": "Zoom out",
    "zoom_tl": "Zoom the timeline",
    "zoom_in": "Zoom in",
    "tl_hint": "Drag to scrub · drag a clip's end to cut or bring back talking · a photo's ends only move the photo · "
               "spacebar plays · zoom in to see your words",
    "tl_hint_words": "Drag a clip's end to cut or bring back talking (sound and picture together) · a photo's ends only "
                     "change which words it covers · Split cuts between two words",
    "tl_photo_title": "Drag either end to change which words this covers",
    "tl_photo_x": "Delete this photo",
    "tl_clip_title": "{words} · drag an end to cut or bring back (sound and picture together)",
    "tl_clip_x": "Delete this clip",
    "tl_photos": "{n} photos · {spot}",
    "tl_video": "{name} · {spot}",
    "no_words_left": "That would leave the photo no words",
    "photo_now_on": "Photo now on “{words}”",
    "split_no_clip": "Move the line onto a clip to split it",
    "split_one_word": "That clip is one word, so it can't be split smaller",
    "split_before": "Split before “{word}”",
    "nothing_back": "Nothing cut there to bring back",
    "brought_back": "Brought back “{words}”",
    "cut_said": "Cut “{words}”, sound and picture",
    "cut_clip": "Cut. Undo brings it back, or find it crossed out in your script.",
    "photo_deleted": "Photo deleted. Undo brings it back.",
    "nothing_undo": "Nothing to undo",
    "undone": "Undone",
    "nothing_redo": "Nothing to redo",
    "redone": "Redone",
    # the make bar and the result box
    "sum": "{b}{t}{eb} of talking · {photos} · {zooms}",
    "sum_photo": "{n} photo", "sum_photos": "{n} photos",
    "sum_video": " · {n} video", "sum_videos": " · {n} videos",
    "sum_zoom": "{n} zoom", "sum_zooms": "{n} zooms",
    "sum_fast": " · {n} sped up",
    "sum_caps_on": " · captions on", "sum_caps_off": " · captions off",
    "sum_empty": "Add your video to start",
    "make": "Make it in CapCut",
    "making": "Making it…",
    "made_h2": "It's in CapCut",
    "made_say": "Open CapCut, give your captions your look, and export.",
}
WORDS.update({"job_" + k: v for k, v in TR.JOB_WORDS.items()})       # her engine's lines (talking_core.py)
WORDS.update({"make_" + k: v for k, v in TR.MAKE_WORDS.items()})     # her server's lines (server.py make_talking)

# Every line of ours on this page, each with why it is ours. (line, reason.) All drafts for Nicole to reword.
OUR_WORDS = {
    "coming": ("{name} is still being copied into your Talking folder. It shows up here when it's done.",
               "hers lists a video while it is still copying in, and Edit my video then reads half a file; ours "
               "waits for it, as the reel page does for Footage"),
    "copy_failed": ("Select the words and copy them",
                    "the app's pane can refuse a copy; hers then says nothing (the words page's own line)"),
    "cant_open": ("Could not open the folder. Ask your assistant to open it.",
                  "her talking page says its folder is open whether or not it opened; this is her reel maker's line"),
    "behind": (reel_page.OUR_WORDS["behind"],
               "the folder can open behind the Claude app; every folder button of the Assistant says so"),
    "cant_reach": ("I couldn't reach the Assistant just now. Try again in a moment.",
                   "hers shows the browser's own error words when her server is not there"),
    "not_understood": (arrange.NOT_UNDERSTOOD, "a request her page could never send is refused in plain words"),
    "newer": (TR.NEWER, "hers has no counter: a save from a page that had not seen the assistant's cut wipes it"),
    "busy": (TR.BUSY, "two saves at the same moment; hers has one process and no lock across programs"),
    "trouble": (TR.TROUBLE, "a record that would not be read just now; hers shows an empty edit"),
    "vp_cant": ("{length} · I couldn't get this one ready to use here",
                "a Footage video whose small copy could not be made: her picker opens an empty player for it; the "
                "reel page's own line for it says its moments and the reel still work, which is not so on this page"),
    "vp_lowspace": ("{length} · your photo drive is almost full, so I couldn't get this one ready",
                    "the same, when the reason is a nearly full drive (her own page says \"almost full\")"),
    "undo_title_pc": ("Undo (Ctrl+Z)", "a PC has no ⌘ key"),
    "redo_title_pc": ("Redo (Ctrl+Shift+Z)", "a PC has no ⌘ key"),
}
OUR_WORDS["not_ready"] = (
    "This shoot isn't ready for this yet. Tell your assistant: make posts from this shoot.",
    "the pickers' own line says \"to Claude\", which no line on this page may; the same page, reworded")
OUR_WORDS.update({"job_" + k: v for k, v in TR.OUR_JOB_WORDS.items()})
OUR_WORDS.update({"make_" + k: v for k, v in TR.OUR_MAKE_WORDS.items()})

CANT_FIND = arrange.CANT_FIND
NOT_READY = OUR_WORDS["not_ready"][0]   # the pickers' own "not ready" page (arrange.NOT_READY), without its "to Claude"
NOT_UNDERSTOOD = arrange.NOT_UNDERSTOOD


def say(msg):
    TR.say(msg)


def page_words():
    """Every word the page's script may show: hers, then ours (the line only). On a PC her "Finder" is this
    computer's word for it and the two Undo tooltips name Ctrl."""
    w = {k: reel_page.pc_words(v) for k, v in WORDS.items()}
    for k, (line, _why) in OUR_WORDS.items():
        w.setdefault(k, line)
    if this_computer.WINDOWS:
        w["undo_title"], w["redo_title"] = w["undo_title_pc"], w["redo_title_pc"]
    return w


# ---------- the routes ----------

def _bad(words=NOT_UNDERSTOOD, code=400, **more):
    d = {"ok": False, "words": words}
    d.update(more)
    return code, d


def _kit_only(body, keys=("kit",)):
    """The kit a POST names, or None with the answer to give: only the fields this route takes, the kit by its
    folder name in Your Content."""
    if set(body) - set(keys):
        return None, _bad()
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return None, _bad(CANT_FIND, 404)
    return kit, None


def open_talking(body):
    """POST /talking-open {kit}: makes <kit>/Talking if it isn't there and opens it (hers: /talking/open). Her
    toast, with this computer's word for Finder; ours when it could not be opened, or opened behind the window."""
    kit, bad = _kit_only(body)
    if bad:
        return bad
    w = page_words()
    if not TR.talking_ok(kit):                # a link, or not a folder: never opened, never written into
        arrange.log("talking page: the shoot's Talking folder is a link or not a folder, so it isn't opened")
        return 200, {"ok": False, "words": w["cant_open"]}
    d = TR.talking_dir(kit)
    try:
        d.mkdir(exist_ok=True)                # the kit's own folder is there (kit_by_name): only Talking is ever made
    except OSError:
        return 200, {"ok": False, "words": w["cant_open"]}
    ok, note = reel_page._open_folder(d)
    if not ok:
        arrange.log(f"talking page: the Talking folder couldn't be opened: {str(note)[:200]}")
        return 200, {"ok": False, "words": w["cant_open"]}
    return 200, {"ok": True, "words": w["talking_open"] + (w["behind"] if note == "behind" else "")}


def start_from_page(body):
    """POST /talking-start {kit, video}: Edit my video. `video` is the key the state gave for a video in the
    Talking folder (never a name, never a path).
      - the video the page is already on, its script ready and made from the file as it is now: nothing to do
        ({"ok": True, "already": True}); the page scrolls to the edit instead of asking;
      - another video whose script was made before: it comes back with its edit and NOTHING is transcribed
        again ({"ok": True, "back": True});
      - anything else: talking_rec.start, a job of its own."""
    kit, bad = _kit_only(body, ("kit", "video"))
    if bad:
        return bad
    key = body.get("video")
    if not isinstance(key, str) or not TR.KEY.fullmatch(key):
        return _bad()
    try:
        talks = TR.list_talks(kit)
        talk = TR.talk_by_key(kit, key, talks)
        if talk is None:
            return 404, {"ok": False, "why": "gone", "words": TR.JOB_WORDS["not_in_folder"]}
        if TR.job_running(kit) or TR._starting(TR.read_job(kit)):
            return 409, {"ok": False, "why": "working", "words": TR.JOB_WORDS["still_working"]}
        rec = TR.load(kit)
        on_it = rec.get("video") == talk["name"]
        if on_it and rec.get("words") and rec.get("status") == "ready" and TR.video_state(kit, rec, talks) == "here":
            return 200, {"ok": True, "already": True}
        if not on_it:                          # no transcriber is needed for this: it works on a PC too
            entry = TR.words_for(kit, talk["name"])
            if isinstance(entry, dict) and entry.get("words") and entry.get("key") == talk["key"]:
                TR.use_video(kit, talk["name"])
                return 200, {"ok": True, "back": True}
    except TR.Busy:
        return 503, {"ok": False, "why": "busy", "words": TR.BUSY}
    except (TR.Unreadable, OSError) as e:
        TR.log(f"{kit.name}: Edit my video could not look at the record ({e.__class__.__name__}: {e})")
        return 503, {"ok": False, "why": "trouble", "words": TR.TROUBLE}
    return TR.start(kit, key)


def save_from_page(body):
    """POST /talking-save {kit, base, page, saved}: talking_rec.save_from_page, which checks every field."""
    if not isinstance(body.get("kit"), str):
        return _bad()
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    code, out = TR.save_from_page(kit, body)
    if code == 200 and out.get("ok"):
        out = _with_make(kit, out)
    elif isinstance(out.get("state"), dict) and out["state"].get("ok"):
        out["state"] = _with_make(kit, out["state"])
    return code, out


def make_from_page(body):
    """POST /talking-make {kit}: Make it in CapCut, in a job of its own (talking_rec.start_make)."""
    kit, bad = _kit_only(body)
    if bad:
        return bad
    return TR.start_make(kit)


def _with_make(kit, st):
    """The state, with how the newest Make it in CapCut stands beside it (small: it rides on every answer). A
    WHOLE state (one with the record in it) also gets what the script and the pickers draw with (_to_draw)."""
    try:
        st["make"] = TR.make_for_page(kit)
    except (OSError, ValueError):
        st["make"] = None
    if isinstance(st.get("rec"), dict):
        _to_draw(kit, st)
    return st


def _to_draw(kit, st):
    """Beside a whole state: "photos", the shoot's photos as the pickers know them ({n, w, h, v, have, missing},
    numbered as the sheet; the page asks for each small copy by its number, /kit-photo), and "stills", for each
    Footage video on a stretch the number of its first still when one is made ({key: n}; the page asks for it by
    /reel-strip). Only read: nothing is made, started or written here, and no path or file name is in it."""
    photos, stills = [], {}
    try:
        got, _made = arrange.page_photos(kit, TR.kitmod.load_rec(kit), arrange.sheet_rows(kit))
        photos = [{"n": p["n"], "w": p["w"], "h": p["h"], "v": p["v"], "have": bool(p["have"]), "missing": bool(p["missing"])} for p in got]
    except (Exception, SystemExit) as e:  # noqa: BLE001  (the page still works: the pickers show nothing to pick)
        arrange.log(f"talking page: the photos couldn't be listed ({e.__class__.__name__})")
    for x in st.get("shots") or []:
        v = x.get("v") if isinstance(x, dict) else None
        if not isinstance(v, dict) or v.get("gone") or not isinstance(v.get("key"), str) or v["key"] in stills:
            continue
        try:
            strip = reel_page.strip_for_page(kit, v["key"])
        except (Exception, SystemExit):  # noqa: BLE001
            strip = []
        if strip:
            stills[v["key"]] = strip[0]["n"]
    st["photos"], st["stills"] = photos, stills


def state(kit, rev=None, mark=None):
    """What GET /talking-state answers (see the top of this file)."""
    return _with_make(kit, TR.state_for_page(kit, rev, mark))


def _one(q, key):
    v = q.get(key, [""])
    return v[0] if v else ""


def _cross_site(handler):
    return (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site"


def _get_page(handler, q):
    import arrange_page
    if _cross_site(handler):
        # a link from another website: the plain "can't find" page, and nothing is looked at or started
        return arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
    rows = arrange.sheet_rows(kit)
    if not rows:
        return arrange._send_page(handler, arrange_page.plain_page(NOT_READY))
    try:
        photos, _made = arrange.page_photos(kit, TR.kitmod.load_rec(kit), rows)
        if any(not x["have"] and not x["missing"] for x in photos) and not arrange.cant_make(kit, rows):
            arrange.start_previews(kit)          # the photos' small copies, made in the background, as the pickers do
    except (Exception, SystemExit) as e:  # noqa: BLE001  (the photos' small copies only; the page still opens)
        arrange.log(f"talking page: the small copies couldn't be started ({e.__class__.__name__})")
    arrange._send_page(handler, page_html(kit.name))


def _get_state(handler, q):
    if _cross_site(handler):
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 403)
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_json(handler, {"ok": False, "words": CANT_FIND}, 404)
    if not arrange.sheet_rows(kit):
        return arrange._send_json(handler, {"ok": False, "words": NOT_READY}, 404)
    rev, mark = _one(q, "rev"), _one(q, "mark")
    # the counter and the mark the page holds: only when both arrive whole is the short answer ever given
    held = REV.fullmatch(rev) and MARK.fullmatch(mark)
    arrange._send_json(handler, state(kit, int(rev), mark) if held else state(kit))


def _get_video(handler, q):
    """GET /talking-video?kit=: the small copy of the record's talking video (the Assistant's own file, made by
    the job), in pieces when the player asks. Never a path in or out; a `v` beside the kit only tells the browser
    it is a new video."""
    if _cross_site(handler) or set(q) - {"kit", "v"}:
        return handler.send_error(404)
    kit = arrange.kit_by_name(_one(q, "kit"))
    copy = TR.preview_for(kit) if kit is not None else None
    if copy is None:
        return handler.send_error(404)
    return reel_page.send_range(handler, copy, "video/mp4")


def handle_get(handler, path, query):
    """Every GET for the talking reel page. Whatever goes wrong, the server answers and stays up."""
    try:
        if not arrange.our_host(handler):
            return handler.send_error(403)
        q = parse_qs(query or "", keep_blank_values=True)
        if path == "/talking.html":
            return _get_page(handler, q)
        if path == "/talking-state":
            return _get_state(handler, q)
        if path == "/talking-video":
            return _get_video(handler, q)
        return handler.send_error(404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        arrange.log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            if path == "/talking-video":
                handler.send_error(404)
            elif path.endswith(".html"):
                import arrange_page
                arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
            else:
                arrange._send_json(handler, {"ok": False, "words": OUR_WORDS["cant_reach"][0]}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


ROUTES = {"/talking-open": open_talking, "/talking-start": start_from_page, "/talking-save": save_from_page,
          "/talking-make": make_from_page}


def handle_post(handler, path, query):
    """Every POST for the talking reel page, after the pickers' guard (reel_page._json_body: arrange.guard, then
    the body as one JSON object; a save may be SAVE_CAP bytes, everything else the usual small cap). Whatever goes
    wrong, the server answers and stays up."""
    try:
        route = ROUTES.get(path)
        body = reel_page._json_body(handler, path, SAVE_CAP if path == "/talking-save" else reel_page.POST_CAP)
        if body is None:
            return
        if route is None:
            return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 404)
        code, out = route(body)
        return arrange._send_json(handler, out, code)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        arrange.log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            arrange._send_json(handler, {"ok": False, "words": OUR_WORDS["cant_reach"][0]}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


# ---------- the page ----------

def _json_for_script(obj):
    """JSON that is safe inside a <script> element (no "</script>", no "<!--")."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def rich(line, **blanks):
    """One of the lines above as HTML: everything escaped, then {b}, {eb} and {br} as her bold and her line
    break. A blank is filled with text (escaped)."""
    s = html.escape(line, quote=False)
    for k, v in blanks.items():
        s = s.replace("{" + k + "}", html.escape(str(v), quote=False))
    return s.replace("{b}", "<b>").replace("{eb}", "</b>").replace("{br}", "<br>")


# Her little pictures on the phone guides (what Instagram draws over a reel): shapes, no words.
_SVG = "<svg viewBox='0 0 24 24' fill='none' stroke='#fff' stroke-width='2' stroke-linejoin='round'>%s</svg>"
_G_CAMERA = _SVG % "<rect x='3' y='7' width='18' height='13' rx='3'/><circle cx='12' cy='13.5' r='3.5'/><path d='M8.5 7l1.5-2.5h4L15.5 7'/>"
_G_HEART = _SVG % "<path d='M12 20s-7-4.4-9-8.6A4.8 4.8 0 0 1 12 6.6a4.8 4.8 0 0 1 9 4.8C19 15.6 12 20 12 20z'/>"
_G_TALK = _SVG % "<path d='M4 12a8 8 0 1 1 3.6 6.7L3.5 20l1.3-4A8 8 0 0 1 4 12z'/>"
_G_SEND = _SVG % "<path d='M21 3 3 10.5l7 2.5 2.5 7z M10 13l11-10'/>"
_G_DOTS = "<svg viewBox='0 0 24 24' fill='#fff'><circle cx='5' cy='12' r='1.8'/><circle cx='12' cy='12' r='1.8'/><circle cx='19' cy='12' r='1.8'/></svg>"


def _step1(w, short):
    e = html.escape
    return (
        "<section class='step s1step' id='step1'><div class='s1'><div>"
        "<h2><span class='num'>1</span>" + e(w["s1_h2"]) + "</h2>"
        "<p class='say sm'>" + rich(w["s1_say"]) + "</p>"
        "<div class='s1-row'><button class='btn main' id='addVideo' type='button'>" + e(w["add_video"]) + "</button>"
        "<div class='vids' id='vids'></div>"
        "<button class='btn' id='startBtn' type='button' disabled>" + e(w["edit_video"]) + "</button></div>"
        "<p class='coming' id='coming' hidden></p>"
        "<p class='status' id='status' role='status'></p>"
        "<div id='askCut' hidden><p class='say sm' style='margin:.7rem 0 .2rem'>" + e(w["cut_say"]) + "</p>"
        "<div class='line'><span id='cutLine'>" + e(w["cut_line"].replace("{short}", short)) + "</span>"
        "<button class='btn main' id='copyCut' type='button'>" + e(w["copy"]) + "</button></div></div>"
        "</div><div class='who'><b class='who-h'>" + e(w["who_h"]) + "</b>"
        "<p class='say sm' style='margin:.15rem 0 .1rem'>" + e(w["who_say"]) + "</p>"
        "<div class='who-row'>"
        "<button class='opt' id='whoMe' type='button' aria-pressed='false'><b>" + e(w["who_me"]) + "</b><span>" + e(w["who_me_say"]) + "</span></button>"
        "<button class='opt' id='whoAsst' type='button' aria-pressed='false'><b>" + e(w["who_asst"]) + "</b><span>" + e(w["who_asst_say"]) + "</span></button>"
        "</div><div id='placeAsk' hidden><p class='say sm' style='margin:.6rem 0 .2rem' id='placeSay'>" + e(w["place_say"]) + "</p>"
        "<div class='line'><span id='placeLine'>" + e(w["place_line"].replace("{short}", short)) + "</span>"
        "<button class='btn main' id='copyPlace' type='button'>" + e(w["copy"]) + "</button></div></div>"
        "</div></div></section>")


def _step2(w):
    e = html.escape
    q = lambda s: e(s, quote=True)  # noqa: E731
    guides = (
        "<div class='guides' id='guides' hidden aria-hidden='true'>"
        "<div class='g-top'><b>" + e(w["g_reels"]) + "</b>" + _G_CAMERA + "</div>"
        "<div class='g-side'><span>" + _G_HEART + "<i>" + e(w["g_likes"]) + "</i></span>"
        "<span>" + _G_TALK + "<i>" + e(w["g_comments"]) + "</i></span>"
        "<span>" + _G_SEND + "<i>" + e(w["g_shares"]) + "</i></span>"
        "<span>" + _G_DOTS + "</span><span class='g-sq'></span></div>"
        "<div class='g-bottom'><div class='g-user'><i class='g-av'></i><b>" + e(w["g_user"]) + "</b><em>" + e(w["g_follow"]) + "</em></div>"
        "<div class='g-cap'></div><div class='g-cap s'></div><div class='g-audio'>" + e(w["g_audio"]) + "</div></div>"
        "<div class='g-nav'></div></div>")
    return (
        "<section class='step' id='editStep' hidden><h2><span class='num'>2</span>" + e(w["s2_h2"]) + "</h2>"
        "<p class='say'>" + rich(w["s2_say"]) + "</p>"
        "<div class='legend'><span class='z-punch'>" + e(w["punch"]) + "</span><span class='z-zoom'>" + e(w["slow_zoom"]) + "</span>"
        "<span class='fast'>" + e(w["sped_up"]) + "</span>"
        "<span style='text-decoration:line-through;color:#a7a2a0;text-decoration-color:#d4643f'>" + e(w["cut"]) + "</span></div>"
        "<div class='edit'><div class='phone'>"
        "<div class='screen' id='screen' title='" + q(w["screen_title"]) + "'>"
        "<video id='vid' playsinline preload='auto'></video>"
        "<div class='phw' id='phFront'><img alt=''><video id='bvid' muted playsinline preload='auto'></video></div>"
        "<i class='knob' id='phKnob' title='" + q(w["knob_photo"]) + "'></i>"
        "<i class='knob' id='meKnob' title='" + q(w["knob_me"]) + "'></i>"
        "<i class='knob' id='capKnob' title='" + q(w["knob_cap"]) + "'></i>"
        "<div class='cap' id='cap'></div>" + guides + "</div>"
        # nothing but these two checkboxes ever sits under the preview (her v24, section 3). autocomplete off: a
        # browser must not put back, on a reload, a tick it remembers ("Play the cut version" is remembered nowhere,
        # and the guides only under the key the page itself keeps)
        "<div class='controls'><label title='" + q(w["guides_title"]) + "'><input type='checkbox' id='guidesOn' autocomplete='off'> " + e(w["guides"]) + "</label>"
        "<label><input type='checkbox' id='cutMode' checked autocomplete='off'> " + e(w["cut_mode"]) + "</label></div>"
        "</div><div class='script' id='script'></div></div></section>")


def _step3(w):
    e = html.escape
    return (
        "<section class='step' id='capStep' hidden><h2><span class='num'>3</span>" + e(w["s3_h2"]) + "</h2>"
        "<p class='say'>" + e(w["s3_say"]) + "</p>"
        "<button class='chip on' id='capOn' type='button'>" + e(w["cap_on"]) + "</button> "
        "<button class='chip' id='capOff' type='button'>" + e(w["cap_off"]) + "</button> "
        "<button class='chip' id='capReset' type='button' hidden>" + e(w["cap_reset"]) + "</button></section>")


def _floating(w):
    """The highlight bar, the photo picker, the video picker, the photo menu and the toast: all hidden until a
    later sub-stage's script opens them."""
    e = html.escape
    head = "<div style='display:flex;justify-content:space-between;align-items:center;gap:1rem'>"
    return (
        "<div class='sel' id='selBar'><button id='selPhoto' type='button'>" + e(w["sel_photo"]) + "</button>"
        "<button id='selVideo' type='button'>" + e(w["sel_video"]) + "</button><i></i>"
        "<button id='selCut' type='button'>" + e(w["cut"]) + "</button><button id='selBack' type='button'>" + e(w["sel_back"]) + "</button><i></i>"
        "<button id='selPunch' type='button'>" + e(w["punch"]) + "</button><button id='selZoom' type='button'>" + e(w["slow_zoom"]) + "</button>"
        "<button id='selNoZoom' type='button'>" + e(w["sel_nozoom"]) + "</button></div>"
        "<div class='modal' id='pick'><div class='sheet'>" + head +
        "<b id='pickHead'>" + e(w["pick_head"]) + "</b><button class='btn small' id='pickClose' type='button'>" + e(w["close"]) + "</button></div>"
        "<p class='say' style='margin:.3rem 0 0'>" + e(w["pick_say"]) + "</p><div class='grid' id='pickGrid'></div>"
        "<div class='pickfoot'><span class='hintsm' id='pickCount'></span>"
        "<button class='btn main' id='pickUse' type='button' disabled>" + e(w["pick_use"]) + "</button></div></div></div>"
        "<div class='modal' id='vpick'><div class='sheet'>" + head +
        "<b id='vpHead'>" + e(w["vp_head"]) + "</b><button class='btn small' id='vpClose' type='button'>" + e(w["close"]) + "</button></div>"
        "<p class='say sm' style='margin-top:.3rem'>" + rich(w["vp_say"]) + "</p><div class='vlist' id='vpList'></div>"
        "<div class='vplayer' id='vpPlayer' hidden><video id='vpVid' controls playsinline muted></video>"
        "<div class='pickfoot'><span class='hintsm' id='vpAt'></span>"
        "<button class='btn main' id='vpUse' type='button'>" + e(w["vp_use"]) + "</button></div></div>"
        "<div class='s1-row' style='margin-top:.7rem'><button class='btn small' id='vpOpen' type='button'>" + e(w["vp_open"]) + "</button>"
        "<button class='btn small' id='vpRefresh' type='button'>" + e(w["vp_refresh"]) + "</button></div></div></div>"
        "<div class='pmenu' id='pmenu'></div><div class='toast' id='toast' role='status'></div>")


def _dock(w):
    """The timeline, then the make bar, fixed across the bottom. The timeline is hidden until there is a script;
    Make it in CapCut stays off until the sub-stage that makes it work."""
    e = html.escape
    q = lambda s: e(s, quote=True)  # noqa: E731
    return (
        "<div class='dock' id='dock'><div class='tl' id='tl' hidden><div class='tl-in'><div class='tl-row'>"
        "<button class='tl-play' id='tlPlay' type='button' aria-label='" + q(w["play"]) + "'>&#9654;</button>"
        "<span class='tl-time' id='tlTime'>0:00.0 / 0:00.0</span><span class='tl-sep'></span>"
        "<button class='btn small' id='tlSplit' type='button' title='" + q(w["split_title"]) + "'>" + e(w["split"]) + "</button>"
        "<button class='btn small' id='tlCut' type='button' disabled title='" + q(w["delete_title"]) + "'>" + e(w["delete_clip"]) + "</button>"
        "<span class='tl-group' id='tlSpeed'><span class='lbl'>" + e(w["speed"]) + "</span></span>"
        "<span class='tl-group' id='tlZoom'><span class='lbl'>" + e(w["zoom"]) + "</span></span>"
        "<button class='btn small' id='tlUndo' type='button' disabled title='" + q(w["undo_title"]) + "'>" + e(w["undo"]) + "</button>"
        "<button class='btn small' id='tlRedo' type='button' disabled title='" + q(w["redo_title"]) + "'>" + e(w["redo"]) + "</button>"
        "<span class='tl-scale'><button id='tlOut' type='button' aria-label='" + q(w["zoom_out"]) + "'>&minus;</button>"
        "<input type='range' id='tlScale' min='0' max='100' value='0' aria-label='" + q(w["zoom_tl"]) + "'>"
        "<button id='tlIn' type='button' aria-label='" + q(w["zoom_in"]) + "'>+</button></span></div>"
        "<div class='tl-track' id='tlTrack'><div class='tl-inner' id='tlInner'><div class='tl-ruler' id='tlRuler'></div>"
        "<div class='tl-photos' id='tlPhotos'></div><div class='tl-clips' id='tlClips'></div>"
        "<div class='tl-words off' id='tlWords'></div><div class='tl-head' id='tlHead'></div></div></div>"
        "<div class='tl-hint' id='tlHint'>" + e(w["tl_hint"]) + "</div></div></div>"
        "<div class='make'><div class='in'><span class='sum' id='sum'>" + e(w["sum_empty"]) + "</span>"
        "<button class='btn main' id='makeBtn' type='button' disabled>" + e(w["make"]) + "</button></div></div></div>")


def page_html(kit_name):
    """The talking reel page for one kit. Everything that changes arrives by /talking-state."""
    e = html.escape
    w = page_words()
    short = reel_page.short_name(kit_name)
    kq = quote(kit_name, safe="")
    data = {"kit": kit_name, "short": short, "words": w, "lookEvery": LOOK_EVERY_MS, "toastMs": TOAST_MS,
            "undoSteps": UNDO_STEPS, "pc": bool(this_computer.WINDOWS), "footageEvery": FOOTAGE_EVERY_MS,
            "copiesEvery": COPIES_EVERY_MS, "copiesTries": COPIES_TRIES,
            "previewDone": list(reel_page.DONE_STATES)}
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + e(w["doc_title"].replace("{short}", short)) + "</title>"
        "<style>" + look.head_css() + talking_css.css() + "</style></head>"
        "<body data-kit='" + e(kit_name, quote=True) + "'>"
        "<div class='wrap'>"
        "<div class='bar'><a class='homelink' id='back' href='/content/" + kq + "/Post%20kit.html'><span aria-hidden='true'>&larr;</span> "
        + e(w["back_kit"]) + "</a>" + brand.bar() + "</div>"
        "<header class='head'><span class='eyebrow'>" + e(w["eyebrow"]) + "</span>"
        "<h1 id='title'>" + e(w["title"].replace("{short}", short)) + "<em>.</em></h1>"
        "<p class='lede'>" + e(w["lede"]) + "</p></header>"
        + _step1(w, short) + _step2(w) + _step3(w) +
        "<div class='result' id='result'></div></div>"
        + _floating(w) + _dock(w) +
        "<script type='application/json' id='talkData'>" + _json_for_script(data) + "</script>"
        "<script>" + "\n".join(JS_PARTS) + "\n" + START_JS + "</script></body></html>")


# ---------- the chat's side ----------

def page_address(kit):
    base = arrange.server_base()
    return f"{base}/talking.html?kit={quote(kit.name)}" if base else None


def cmd_open(kit):
    """`talking_page.py open "<shoot>"`: the page's address, once the shoot's photos are numbered and their small
    copies made (the reel page's own way)."""
    listed = arrange.kit_by_name(kit.name)
    if listed is None or listed.resolve() != kit.resolve():
        say(f"STOP: \"{kit.name}\" isn't in Your Content, so the page can't show it.")
        return 1
    if not arrange.sheet_rows(kit):
        if TR.kitmod.sheet(kit) != 0 or not arrange.sheet_rows(kit):
            say("STOP: couldn't number this shoot's photos. Are they where the kit says they are?")
            return 1
    got = arrange.make_previews(kit)
    lost = 0 if got.get("cant") else int(got.get("missing") or 0) + int(got.get("failed") or 0)
    if lost:
        say(f"({lost} of {got.get('of')} photos couldn't be read right now.)")
    addr = page_address(kit)
    if not addr:
        say("STOP: couldn't start the page server.")
        return 2
    say(addr)
    return 0


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("open", help="print the page's address").add_argument("words")
    a = ap.parse_args(argv)
    import fresh
    fresh.announce()
    kit = TR.find(a.words)
    return cmd_open(kit)


if __name__ == "__main__":
    sys.exit(main())
