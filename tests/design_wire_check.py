#!/usr/bin/env python3
"""The designer as part of the Assistant: the kit page, the posting queue, the picker's link, the chat.

Run through tests/design_check.py (python3 tests/design_check.py --only wire --port P; it uses P + 4):

  check_wire          by requests and commands, no browser. After Save slides the kit page shows only the
                      newest laid-out set, with a true line and the folder's button beside it; a new order from
                      the picker puts the plain slides back and leaves every laid-out file where it is; pressing
                      Save slides again on a design that is already saved shows its set again; a Canva carousel
                      fetched after a save is what shows; a set with a slide missing is not shown in pieces; the
                      posting queue's picture follows the first slide shown; home.py pending prints one line that
                      names the kit, the set and the slides, and design.py took clears it.
  check_wire_browser  the two "Lay out the slides" links pressed by a real pointer in a hidden Chrome (SKIP when
                      there is no Chrome): each opens the designer, and neither asks for a folder to be opened.

Nothing here opens Finder: the one request that would (GET /open) is answered inside the page in the browser
part and is never sent in the other. Needs Pillow (the slides it sends are drawn here). The plugin's own code
runs under the Mac's own /usr/bin/python3.
"""
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from html import unescape
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"

LAY_OUT = "Lay out the slides"
PLAIN_LINE = "The slides, in order, all the same size. They are in the Carousel folder."
CANVA_LINE = "Made in Canva from your template; the plain slides are there too."
ALSO_LINE = " The slides you laid out are in that folder too."

# Run in every page before its own scripts: a request to open a folder never leaves the page. It is written
# down where a later page of the same tab can still read it (a link that also asked for a folder would do so
# on the page that is then left), and answered as the Assistant would answer it.
NO_FINDER_KEPT_JS = r"""
(function(){
  var real = window.fetch;
  function note(u){ try { var a = JSON.parse(sessionStorage.getItem('__opens') || '[]'); a.push(u); sessionStorage.setItem('__opens', JSON.stringify(a)); } catch (e) {} }
  window.fetch = function(u, o){
    if (String(u).indexOf('/open') === 0) {
      note(String(u));
      return Promise.resolve(new Response(JSON.stringify({ok: true, words: 'Opened Carousel in Finder.'}), {status: 200, headers: {'Content-Type': 'application/json'}}));
    }
    return real.apply(this, arguments);
  };
})();
"""


def _carousel_section(page):
    """The Carousel section of a kit page: (its html, the picture addresses in it, the line under its heading)."""
    m = re.search(r"<section class='piece'><div><div class='top'><h2>Carousel<span.*?</section>", page, re.S)
    if not m:
        return "", [], ""
    sec = m.group(0)
    srcs = [unescape(x) for x in re.findall(r"<img src='([^']+)'", sec)]
    sub = re.search(r"<p class='sub'>(.*?)</p>", sec, re.S)
    return sec, srcs, unescape(sub.group(1)) if sub else ""


def _mean(data, box=None):
    """The average color of a JPEG (the middle of it, or a box), as (r, g, b)."""
    from PIL import Image, ImageStat
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    im = im.crop(box or (w // 4, h * 3 // 5, w * 3 // 4, h * 4 // 5))
    return tuple(ImageStat.Stat(im).mean)


def _far(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def flat(color, w=1080, h=1350, mark=0):
    """A 1080 x 1350 JPEG of one flat color (with a thin line that differs per slide), drawn here."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), color)
    ImageDraw.Draw(im).rectangle([40, 40 + mark * 30, 400, 60 + mark * 30], fill=(255 - color[0], 255 - color[1], 255 - color[2]))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def check_wire(case, work, port, make_kit, Server, post, get_json, ask, run, tree_print, sha):
    target = work / "wire"
    ok, out = make_kit(target, "Fake beach", 14)
    if not case("wire: the pretend kit was made (tests/fake_kit.py)", ok, out):
        return
    ok, out = make_kit(target, "Never laid out", 8)
    case("wire: a second pretend kit, which never gets a laid-out set", ok, out)
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    content = target / "The Assistant" / "Your Content"
    kit_name, kit2_name = "2026-11-01 Fake beach", "2026-11-01 Never laid out"
    kit, kit2 = content / kit_name, content / kit2_name
    KQ, K2 = quote(kit_name), quote(kit2_name)
    car = kit / "Carousel"
    rec_file = kit / ".kit" / "kit.json"
    APPLE = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else sys.executable

    def rec():
        return json.loads(rec_file.read_text(encoding="utf-8"))

    def plain_names(k=None):
        return list((json.loads(((k or kit) / ".kit" / "kit.json").read_text(encoding="utf-8")).get("made_pieces") or {}).get("carousel") or [])

    for name in (kit_name, kit2_name):
        code, out = run(env, "kit.py", "build", name)
        case(f"wire: kit.py build made the plain slides of {name}", code == 0 and len(plain_names(content / name)) >= 3, out[-300:])
    (car / "my own picture.jpg").write_bytes(flat((20, 200, 220)))          # a file of the photographer's own, never to be touched
    code, out = run(env, "kit.py", "page", kit_name)
    code, out = run(env, "posting_queue.py", "add", "--kit", kit_name)
    case("wire: the kit is in the posting queue", code == 0, out[-200:])
    pid = next(x["id"] for x in json.loads((studio / "posting.json").read_text(encoding="utf-8"))["pieces"] if x["kind"] == "carousel")
    thumb_file = studio / "posting-thumbs" / f"{pid}.jpg"
    kept = {}                   # every file ever seen in the Carousel folder -> its hash when first seen

    def nothing_changed():
        now = tree_print(car)
        lost = [n for n, h in kept.items() if now.get(n) != h]
        for n, h in now.items():
            kept.setdefault(n, h)
        return lost

    nothing_changed()
    srv = Server(env, port)
    try:
        P = srv.start()
        print(f"      (wire: page server on port {P}, STUDIO_HOME={studio})", flush=True)

        def kit_page(q=KQ):
            code, h, data = ask(P, "GET", f"/content/{q}/Post%20kit.html")
            return code, data.decode("utf-8", "replace")

        def shown(q=KQ):
            """(the picture names the kit page's Carousel section shows, the line under its heading, the section)"""
            code, page = kit_page(q)
            sec, srcs, sub = _carousel_section(page)
            return [unquote(s.split("/", 1)[1]) for s in srcs if s.startswith("Carousel/")], sub, sec

        def pictures_load(q=KQ):
            """Every picture address in the Carousel section, asked for as a browser would ask (an address
            ends at a # or a ?, and a % is sent as it is written): the bytes it gets, by the name it asked for."""
            code, page = kit_page(q)
            got = {}
            for s in _carousel_section(page)[1]:
                path = s.split("#")[0].split("?")[0]
                c, h, data = ask(P, "GET", f"/content/{q}/" + quote(path, safe="/%"))
                got[unquote(path.split("/", 1)[1])] = data if c == 200 else None
            return got

        def thumb():
            """The carousel's picture as the posting page shows it: the address from the page, then its bytes."""
            code, h, data = ask(P, "GET", "/posting.html")
            m = re.search(r"posting-thumbs/" + re.escape(quote(pid, safe="")).replace("%3A", "(?:%3A|:)") + r"\.jpg[^'\")\s]*", data.decode("utf-8", "replace"))
            m = m or re.search(r"posting-thumbs/[^'\")\s]*carousel\.jpg[^'\")\s]*", data.decode("utf-8", "replace"))
            if not m:
                return None
            c, h, pic = ask(P, "GET", "/" + unescape(m.group(0)))
            return pic if c == 200 else None

        def thumb_is(slide_bytes):
            """Is the posting page's picture of the carousel a small copy of this slide? (average color, the whole of each)"""
            t = thumb()
            if not t:
                return False, "no picture"
            from PIL import Image
            w, h = Image.open(io.BytesIO(t)).size
            a = _mean(t, (w // 3, h // 3, w * 2 // 3, h * 2 // 3))
            b = _mean(slide_bytes, (360, 450, 720, 900))
            return _far(a, b) < 12, (tuple(round(x) for x in a), tuple(round(x) for x in b))

        # ---------- before any design: the kit page as it was, plus the link ----------
        names0 = plain_names()
        got, sub, sec = shown()
        case("before any laid-out set: the kit page shows the plain slides and the photographer's own picture", sorted(got) == sorted(names0 + ["my own picture.jpg"]), got)
        case("before any laid-out set: the line is the one it always was", sub == PLAIN_LINE, sub)
        links = re.findall(r"<a class='arr' href='([^']+)'[^>]*>" + LAY_OUT + "</a>", sec)
        code, page = kit_page()
        case("the kit page has 'Lay out the slides' once, in the Carousel section", len(links) == 1 and page.count(">" + LAY_OUT + "</a>") == 1 and links[0] == f"/design.html?kit={KQ}", links)
        order = [m.group(1) for m in re.finditer(r">(Change the photos|Lay out the slides|Open the Carousel folder)<", sec)]
        case("...beside 'Change the photos', before the folder's button", order == ["Change the photos", "Lay out the slides", "Open the Carousel folder"], order)
        tag = (re.findall(r"<a [^>]*>" + LAY_OUT + "</a>", page) or [""])[0]
        case("...a plain link of class 'arr', never 'go', with nothing that asks for a folder", "class='arr'" in tag and "class='go" not in tag and "data-sub" not in tag and "body:not(.live) .arr{display:none}" in page, tag)
        code, h, data = ask(P, "GET", unescape(links[0])) if links else (0, {}, b"")
        case("...and its address is the designer for this shoot", code == 200 and b"class='designer'" in data and f"data-kit='{kit_name}'".encode() in data, code)
        code, h, data = ask(P, "GET", "/posting.html")
        case("the posting page shows the carousel's picture", thumb() is not None)
        ok, why = thumb_is((car / names0[0]).read_bytes())
        case("before any laid-out set: the posting queue's picture is the first plain slide", ok, why)
        got2, sub2, sec2 = shown(K2)
        case("a kit that never gets a laid-out set has the link too", sec2.count(">" + LAY_OUT + "</a>") == 1 and f"/design.html?kit={K2}" in sec2 and sub2 == PLAIN_LINE, sub2)

        # ---------- a save from the designer ----------
        code, st = get_json(P, f"/design-state?kit={KQ}")
        if not case("wire: the designer's first design for this shoot", code == 200 and st and st.get("design"), code):
            return
        D = st["design"]
        DID, STAMP, N = D["id"], st["stamp"], D["state"]["slides"]
        box = {"rev": D["rev"], "state": copy.deepcopy(D["state"]), "tok": 0}
        COLORS = [(200, 30, 30), (30, 160, 60), (40, 60, 200), (220, 200, 40), (160, 40, 180), (30, 180, 190)]

        def save(change=True, name=None, color=0, expect_new=True):
            """Change the design a little (or not), send its slides, commit. (answer, the slides sent)"""
            if change:
                s = copy.deepcopy(box["state"])
                s["blocks"][0]["x"] = round(s["blocks"][0]["x"] + 5, 2)
                b = {"kit": kit_name, "design": DID, "stamp": STAMP, "base": box["rev"], "page": "wirepage01", "state": s}
                if name:
                    b["name"] = name
                c, o = post(P, "/design", b)
                if c != 200:
                    return (c, o), []
                box["rev"], box["state"] = o["rev"], s
            box["tok"] += 1
            tok = f"wiretoken{box['tok']:02d}"
            slides = [flat(COLORS[color % len(COLORS)], mark=i) for i in range(N)]
            if expect_new:
                for i, data in enumerate(slides, 1):
                    ask(P, "POST", f"/design-slide?kit={KQ}&design={DID}&set={tok}&i={i}&of={N}", body=data, headers={"Content-Type": "image/jpeg"})
            c, o = post(P, "/design-commit", {"kit": kit_name, "design": DID, "set": tok, "rev": box["rev"], "count": N})
            return (c, o), slides

        (code, out), S1 = save(change=False, color=0)
        BASE1 = "Fake beach carousel 1"
        set1 = [f"{BASE1} - slide {i:02d}.jpg" for i in range(1, N + 1)]
        case("Save slides: the first set is saved under the design's name", code == 200 and out.get("ok") and out.get("base") == BASE1 and out.get("count") == N, (code, out))
        got, sub, sec = shown()
        case("after a save the kit page's Carousel section shows only the laid-out set, in order", got == set1, got)
        case("...with a true line naming the set shown", sub == f"The slides you laid out, saved as “{BASE1}”. They are in the Carousel folder, and the other slides in that folder are all still there.", sub)
        case("...and the folder's button is in that same section, beside the line about the folder", "data-sub='Carousel'>Open the Carousel folder</button>" in sec and "<p class='went'></p>" in sec)
        loaded = pictures_load()
        case("...and every picture the page shows loads, and is byte for byte the slide that was saved", [loaded.get(n) for n in set1] == S1, [n for n in set1 if loaded.get(n) != S1[set1.index(n)]])
        case("...while the plain slides and the photographer's own picture are all still in the folder, unchanged", nothing_changed() == [] and all((car / n).is_file() for n in names0 + ["my own picture.jpg"]), nothing_changed())
        ok, why = thumb_is(S1[0])
        case("after a save the posting queue's picture of the carousel is the set's first slide", ok, why)
        ok2, _ = thumb_is((car / names0[0]).read_bytes())
        case("...and is no longer the first plain slide", not ok2)
        code, out = run(env, "home.py", "pending")
        line1 = f"ARRANGED: {kit_name} | design | {N} slides | {BASE1}"
        lines = [ln for ln in out.splitlines() if ln.startswith("ARRANGED:")]
        case("home.py pending prints one line: the kit, 'design', how many slides, and the set's name", code == 0 and lines == [line1], lines)
        code, out = run(env, "home.py", "pending")
        case("...and prints it the same, once, the next time too (it waits until Claude has said so)", [ln for ln in out.splitlines() if ln.startswith("ARRANGED:")] == [line1], out[-200:])
        code, out = run(env, "design.py", "show", kit_name)
        case("design.py show names the set and the line that is waiting", code == 0 and f"\"{BASE1}\"" in out and "Waiting for Claude: " + line1 in out, out[-400:])

        # a second, changed save, under a name with the characters that cut an address short
        NAME2 = "Tom & Ana's #1 100% beach"
        (code, out), S2 = save(change=True, name=NAME2, color=1)
        set2 = [f"{NAME2} - slide {i:02d}.jpg" for i in range(1, N + 1)]
        case("a second save, after a change and a new name, makes a new set beside the first", code == 200 and out.get("base") == NAME2 and all((car / n).is_file() for n in set1 + set2), (code, out))
        got, sub, sec = shown()
        case("the kit page now shows only the newest set (a name with &, ', # and % in it)", got == set2 and f"saved as “{NAME2}”" in sub, (got, sub))
        loaded = pictures_load()
        case("...and its pictures load from the page's own addresses, byte for byte", [loaded.get(n) for n in set2] == S2, [n for n in set2 if loaded.get(n) is None])
        ok, why = thumb_is(S2[0])
        case("...and the posting queue's picture follows the newest set's first slide", ok, why)
        code, out = run(env, "home.py", "pending")
        line2 = f"ARRANGED: {kit_name} | design | {N} slides | {NAME2}"
        case("home.py pending still prints one line for this shoot's slides, now naming the newest set", [ln for ln in out.splitlines() if ln.startswith("ARRANGED:")] == [line2], out[-200:])
        code, o = run(env, "design.py", "took", kit_name)
        code2, o2 = run(env, "home.py", "pending")
        case("design.py took clears it: home.py pending prints no ARRANGED line", code == 0 and "Cleared." in o and "ARRANGED" not in o2, (o, o2[-200:]))
        code, o = run(env, "design.py", "took", kit_name)
        case("design.py took a second time says nothing was waiting", code == 0 and "Nothing was waiting" in o, o)
        case("nothing that was in the Carousel folder has changed or gone", nothing_changed() == [], nothing_changed())

        # ---------- a new order from the picker: the plain slides are the carousel again ----------
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=carousel")
        ast = json.loads(data)
        nums = ast["now"]["nums"]
        new_order = [nums[1], nums[0]] + nums[2:]
        code, j = post(P, "/arrange", {"kit": kit_name, "piece": "carousel", "stamp": ast["stamp"], "page": "wirepicker1", "base": ast["rev"], "nums": new_order, "done": True})
        case("the picker's 'I'm happy with this order' on a new order starts its slide job", code == 200 and j.get("job") is True, (code, j))
        end, job = time.time() + 90, None
        while time.time() < end:
            code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=carousel")
            job = json.loads(data).get("job")
            if job and job.get("rev") == j.get("rev") and job.get("state") in ("done", "same", "problem"):
                break
            time.sleep(0.25)
        names1 = plain_names()
        case("...and the job ends done, with new plain slides", bool(job) and job.get("state") == "done" and names1 != names0 and len(names1) == len(new_order), job)
        got, sub, sec = shown()
        case("after the new order the kit page shows the plain slides again (and their own picture), and no laid-out slide", sorted(got) == sorted(names1 + ["my own picture.jpg"]) and not [n for n in got if n in set1 + set2], got)
        case("...and its line says, truly, that the laid-out slides are still in the folder", sub == PLAIN_LINE + ALSO_LINE, sub)
        now = tree_print(car)
        case("...and every laid-out file is still in the Carousel folder, byte for byte", [now.get(n) for n in set1 + set2] == [sha(x) for x in S1 + S2], [n for n in set1 + set2 if n not in now])
        aside = [n for n in names0 if n not in names1]
        older = kit / ".kit" / "slides-older"
        moved = {p.name for p in older.rglob("*.jpg")} if older.is_dir() else set()
        case("...and the earlier plain slides were set aside as plain slides always are; no laid-out slide went with them", all(n in moved for n in aside) and not [n for n in moved if " - slide " in n], sorted(moved)[:6])
        r = rec()
        case("the kit's record: the plain slides are the set shown, and both laid-out sets are still listed", r.get("carousel_set", {}).get("kind") == "plain" and [x["base"] for x in r.get("laid_out", [])] == [BASE1, NAME2], (r.get("carousel_set"), [x.get("base") for x in r.get("laid_out", [])]))
        ok, why = thumb_is((car / names1[0]).read_bytes())
        case("...and the posting queue's picture is the first plain slide of the new order", ok, why)
        for n in set1 + set2:
            kept[n] = sha((car / n).read_bytes())
        kept.update({n: h for n, h in tree_print(car).items() if n not in kept})
        for n in aside:
            kept.pop(n, None)       # moved to the kit's hidden folder by the picker's own job (checked just above)
        run(env, "arrange.py", "took", kit_name, "--piece", "carousel")

        # ---------- Save slides pressed again with nothing changed: that set is the one shown again ----------
        files_before = sorted(os.listdir(car))
        (code, out), _ = save(change=False, expect_new=False)
        case("Save slides with nothing changed, while the plain slides are shown: 'Already saved as ...', and no new file", code == 200 and out.get("already") is True and out.get("base") == NAME2
             and out.get("words") == f"Already saved as \"{NAME2}\". Change something to save a new set." and sorted(os.listdir(car)) == files_before, (code, out))
        got, sub, sec = shown()
        case("...and the kit page shows that set again, with its line", got == set2 and f"saved as “{NAME2}”" in sub, (got, sub))
        ok, why = thumb_is(S2[0])
        case("...and the posting queue's picture is that set's first slide again", ok, why)
        rec_now = rec_file.read_bytes()
        (code, out), _ = save(change=False, expect_new=False)
        case("pressed once more: the same answer, and the kit's record is not written again", code == 200 and out.get("already") is True and rec_file.read_bytes() == rec_now, (code, out))
        code, o2 = run(env, "home.py", "pending")
        case("an 'already saved' press puts no new line in front of Claude", "ARRANGED" not in o2, o2[-200:])

        # ---------- a Canva carousel fetched after a laid-out save ----------
        # (what canva_kit.py fetch does, without Canva: its files in the folder, its record, the page, the queue)
        canva_pics = [flat((240, 120, 20), mark=i) for i in range(2)]
        canva_names = [f"Slide {i:02d} (Canva).jpg" for i in (1, 2)]
        for n, data in zip(canva_names, canva_pics):
            (car / n).write_bytes(data)
        time.sleep(1.1)             # the record's times are whole seconds: the fetch is truly after the save
        script = ("import sys, json\nfrom datetime import datetime\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\nimport kit as kit_mod, canva_kit\n"
                  "k = Path(sys.argv[2])\n"
                  "def note(rec):\n"
                  "    c = rec.setdefault('canva', {})\n"
                  "    c.setdefault('files', {})['Carousel'] = json.loads(sys.argv[3])\n"
                  "    c.setdefault('fetched', {})['Carousel'] = datetime.now().isoformat(timespec='seconds')\n"
                  "    c['carousel'] = {'design_id': 'DAFtest', 'edit_url': '', 'template': 'T', 'made': c['fetched']['Carousel'], 'picks': list((rec.get('picks') or {}).get('carousel') or [])}\n"
                  "kit_mod.update_rec(k, note)\nkit_mod.write_page(k)\ncanva_kit.refresh_posting(k)\nprint('ok')\n")
        r = subprocess.run([APPLE, "-c", script, str(SCRIPTS), str(kit), json.dumps(canva_names)], capture_output=True, text=True, env=env, timeout=120)
        case("wire: a Canva carousel was put in as canva_kit.py fetch records one", r.returncode == 0 and "ok" in r.stdout, (r.stdout + r.stderr)[-300:])
        got, sub, sec = shown()
        case("a Canva carousel fetched after a laid-out save: the kit page shows the Canva slides first, then the plain ones, and no laid-out slide",
             got[:2] == canva_names and sorted(got[2:]) == sorted(names1 + ["my own picture.jpg"]), got)
        case("...and its line says so, and that the laid-out slides are in the folder too", sub == CANVA_LINE + ALSO_LINE, sub)
        ok, why = thumb_is(canva_pics[0])
        case("...and the posting queue's picture is the first Canva slide", ok, why)
        case("...and every laid-out file is still there, unchanged", nothing_changed() == [], nothing_changed())
        time.sleep(1.1)
        (code, out), S3 = save(change=True, color=2)
        BASE3 = f"{NAME2} (2)"
        set3 = [f"{BASE3} - slide {i:02d}.jpg" for i in range(1, N + 1)]
        got, sub, sec = shown()
        case("a laid-out set saved after that Canva carousel is the one shown", code == 200 and out.get("base") == BASE3 and got == set3 and f"saved as “{BASE3}”" in sub, (code, out, got))
        ok, why = thumb_is(S3[0])
        case("...in the posting queue too", ok, why)

        # ---------- a set with a slide missing is never shown in pieces ----------
        out_of_the_way = work / "wire-moved-out"
        out_of_the_way.mkdir(exist_ok=True)
        shutil.move(str(car / set3[1]), str(out_of_the_way / set3[1]))      # the photographer drags one slide out of the folder
        code, out = run(env, "kit.py", "page", kit_name)
        got, sub, sec = shown()
        case("a laid-out set with a slide gone from the folder is not shown, and none of its other slides shows as a loose slide",
             got[:2] == canva_names and not [n for n in got if " - slide " in n] and sub == CANVA_LINE + ALSO_LINE, (got, sub))
        shutil.move(str(out_of_the_way / set3[1]), str(car / set3[1]))      # and puts it back
        code, out = run(env, "kit.py", "page", kit_name)
        got, sub, sec = shown()
        case("put back, the set is shown whole again", got == set3, got)
        case("at the end nothing that was ever in the Carousel folder has changed or gone", nothing_changed() == [], nothing_changed())
        run(env, "design.py", "took", kit_name)

        # ---------- the walk a fresh reader takes: "lay out my carousel" -> SKILL.md -> the part -> the command ----------
        skill_dir = SCRIPTS.parent
        skill = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        rows = [ln for ln in skill.splitlines() if ln.startswith("|") and '"lay out my carousel"' in ln]
        sent_to = re.findall(r"`(parts/[\w-]+\.md)`", rows[0]) if len(rows) == 1 else []
        case("the walk: exactly one row of SKILL.md's table has \"lay out my carousel\", and it names one part to read", sent_to == ["parts/arrange.md"], (len(rows), sent_to))
        desc = re.search(r"^description: (.*)$", skill, re.M)
        case("the walk: the skill's own description names the phrase (so the skill is picked up at all), and is still within 1,024 characters",
             bool(desc) and "lay out my carousel" in desc.group(1) and len(desc.group(1)) <= 1024, len(desc.group(1)) if desc else 0)
        part = (skill_dir / (sent_to[0] if sent_to else "parts/arrange.md")).read_text(encoding="utf-8")
        first = part.find('"lay out my carousel"')
        pointer = re.search(r'"Laying out the slides: the designer"', part[first:first + 400]) if first >= 0 else None
        heading = "## Laying out the slides: the designer"
        case("the walk: the part's first mention of that phrase points to a section by its heading, and that heading is there",
             first >= 0 and bool(pointer) and part.count("\n" + heading + "\n") == 1 and first < part.index(heading))
        section = part[part.index(heading):].split("\n## ", 1)[0] if heading in part else ""
        block = re.search(r"```\n(.*?)```", section, re.S)
        cmds = block.group(1).strip().splitlines() if block else []
        case("the walk: that section's first command is the one that opens the designer", bool(cmds) and cmds[0] == 'python3 <scripts>/design.py open "<kit>"', cmds[:1])
        # run it exactly as written, with <scripts> and <kit> filled in the way a reader would ("beach")
        argv = cmds[0].replace("<scripts>", str(SCRIPTS)).replace('"<kit>"', "beach").split(" ")[1:] if cmds else []
        r = subprocess.run([APPLE] + argv, capture_output=True, text=True, env=env, timeout=120) if argv else None
        last = (r.stdout.strip().splitlines() or [""])[-1] if r else ""
        case("the walk: run as written, it prints the designer's address for that shoot on its last line", bool(r) and r.returncode == 0 and last.startswith(f"http://127.0.0.1:{P}/design.html?kit={KQ}&design="), (r.stdout + r.stderr)[-300:] if r else "")
        code, h, data = ask(P, "GET", last[len(f"http://127.0.0.1:{P}"):]) if last.startswith("http://127.0.0.1") else (0, {}, b"")
        case("the walk: and that address is the designer page", code == 200 and b"class='designer'" in data, code)
        took_cmd = next((c for c in cmds if "design.py took" in c), "")
        case("the walk: the section also gives the command that clears the line after Save slides", took_cmd == 'python3 <scripts>/design.py took "<kit folder>"', cmds)

        # ---------- a kit with no laid-out set is exactly as it was ----------
        rec2_file = kit2 / ".kit" / "kit.json"
        nums2 = json.loads(rec2_file.read_text(encoding="utf-8"))["picks"]["carousel"]
        code, out = run(env, "kit.py", "picks", kit2_name, "--carousel", ",".join(str(n) for n in reversed(nums2)))
        code, out = run(env, "kit.py", "build", kit2_name)
        r2 = json.loads(rec2_file.read_text(encoding="utf-8"))
        got2, sub2, sec2 = shown(K2)
        case("a kit with no laid-out set: a new order writes no carousel_set into its record, and its page reads as before",
             code == 0 and "carousel_set" not in r2 and "laid_out" not in r2 and sub2 == PLAIN_LINE and sorted(got2) == sorted(plain_names(kit2)), (sorted(r2), sub2))
    finally:
        srv.stop()

    # ---------- the instructions lead a fresh reader to the right command ----------
    skill = (SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8")
    part = (SCRIPTS.parent / "parts" / "arrange.md").read_text(encoding="utf-8")
    row = next((ln for ln in skill.splitlines() if ln.startswith("|") and "parts/arrange.md" in ln), "")
    case("SKILL.md's table sends 'lay out my carousel', 'design my carousel' and 'add text to my slides' to parts/arrange.md",
         all(p in row for p in ('"lay out my carousel"', '"design my carousel"', '"add text to my slides"')), row[:200])
    case("parts/arrange.md gives the command that opens the designer, and the one that clears its line",
         'design.py open "<kit>"' in part and 'design.py took "<kit folder>"' in part and "| design |" in part)
    case("parts/arrange.md says the words on a slide are the photographer's and nothing made earlier is replaced",
         "never invent" in part.lower() and "nothing made earlier is replaced" in part.lower())
    for name, needle in (("where-things-live.md", "design-templates"), ("canva.md", "laid out"), ("post-kit.md", LAY_OUT)):
        text = (SCRIPTS.parent / "parts" / name).read_text(encoding="utf-8")
        case(f"parts/{name} mentions the designer's side of things ({needle!r})", needle in text)


def check_wire_browser(case, work, port, make_kit, Server, run, ask, post, get_json):
    sys.path.insert(0, str(ROOT / "tests"))
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  the real-browser checks of the 'Lay out the slides' links: no Chrome on this computer", flush=True)
        return
    target = work / "wire-browser"
    ok, out = make_kit(target, "Fake beach", 10)
    if not case("wire browser: the pretend kit was made", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Fake beach"
    KQ = quote(kit_name)
    code, out = run(env, "kit.py", "build", kit_name)
    code, out = run(env, "arrange.py", "previews", kit_name)
    srv = Server(env, port)
    P = srv.start()
    base = f"http://127.0.0.1:{P}"
    try:
        # a set of laid-out slides saved by requests, under a name with the characters that cut an address short
        NAME = "Ana & Tom's #1 100% beach"
        code, st = get_json(P, f"/design-state?kit={KQ}")
        D = st["design"]
        N = D["state"]["slides"]
        code, o = post(P, "/design", {"kit": kit_name, "design": D["id"], "stamp": st["stamp"], "base": D["rev"], "page": "wirebrowser1", "name": NAME, "state": D["state"]})
        for i in range(1, N + 1):
            ask(P, "POST", f"/design-slide?kit={KQ}&design={D['id']}&set=wirebrowser01&i={i}&of={N}", body=flat((30, 120, 200), mark=i), headers={"Content-Type": "image/jpeg"})
        code2, o2 = post(P, "/design-commit", {"kit": kit_name, "design": D["id"], "set": "wirebrowser01", "rev": (o or {}).get("rev"), "count": N})
        case("wire browser: a set of slides was saved under a name with &, ', # and % in it", code == 200 and code2 == 200 and (o2 or {}).get("base") == NAME, (code, o, code2, o2))
        with cd.Chrome(work=work / "chrome-wire", size=(1280, 900)) as c:
            c.init_script(NO_FINDER_KEPT_JS)

            def opens():
                return json.loads(c.js("sessionStorage.getItem('__opens') || '[]'"))

            def asked_open():
                return [r for r in c.requests if "/open" in str(r)]

            # ---- the kit page ----
            c.open(f"{base}/content/{KQ}/Post%20kit.html")
            c.wait_for("document.body.classList.contains('live')", 10)
            car_imgs = ("Array.from(document.querySelectorAll('section.piece')).filter(function(s){return s.querySelector('h2').textContent.indexOf('Carousel')===0})[0]"
                        ".querySelectorAll('.strip img')")
            try:
                c.wait_for(f"Array.from({car_imgs}).every(function(i){{return i.complete}})", 15)
            except cd.Timeout:
                pass
            sizes = json.loads(c.js(f"JSON.stringify(Array.from({car_imgs}).map(function(i){{return [i.naturalWidth, i.naturalHeight]}}))"))
            case("kit page, in a browser: the Carousel section shows the saved set and every one of its pictures really loads (1080 by 1350)",
                 len(sizes) == N and all(x == [1080, 1350] for x in sizes), sizes)
            sub = c.js("Array.from(document.querySelectorAll('section.piece')).filter(function(s){return s.querySelector('h2').textContent.indexOf('Carousel')===0})[0].querySelector('.sub').textContent")
            case("kit page, in a browser: the line names the set exactly as it was saved", f"saved as \u201c{NAME}\u201d" in sub, sub)
            # the Stories section has a link of its own to the stories designer (v19 stage c2); this one is the carousel's
            sel = "a.arr[href^='/design.html']:not([href*='kind=stories'])"
            case("kit page, in a browser: the Stories section links to the stories designer (her \"Make my stories →\")",
                 c.js("(function(){var a=document.querySelector(\"a.arr[href*='kind=stories']\"); return !!a && a.closest('section').querySelector('h2').textContent.indexOf('Stories')===0 && a.textContent})()") == "Make my stories \u2192")
            case("kit page, in a browser: 'Lay out the slides' is showing in the Carousel section, beside 'Change the photos'",
                 c.count(sel) == 1 and c.text(sel) == LAY_OUT and c.js(f"(function(){{var a=document.querySelector(\"{sel}\"), s=a.closest('section'); return s.querySelector('h2').textContent.indexOf('Carousel')===0 && !!a.previousElementSibling && a.previousElementSibling.textContent==='Change the photos' && a.getBoundingClientRect().width>40}})()") is True)
            c.click(sel)
            c.wait_for("location.pathname === '/design.html' && window.Designer && Designer.st && Designer.S", 20, tell="location.href")
            case("kit page: pressing it opens the designer for that shoot", c.js("location.pathname + location.search").startswith(f"/design.html?kit={KQ}") and c.js("Designer.KIT") == kit_name, c.js("location.href"))
            case("kit page: pressing it asked for no folder to be opened (not in the page, not of the Assistant)", opens() == [] and asked_open() == [], (opens(), asked_open()))
            case("kit page: the designer drew this shoot's slides", c.count("#strip .blk") >= 2 and not c.page_errors(), c.page_errors())
            # the same press does trip this check when a folder IS asked for: the folder's own button, on the kit page
            c.open(f"{base}/content/{KQ}/Post%20kit.html")
            c.wait_for("document.body.classList.contains('live')", 10)
            c.click("button.go[data-sub='Carousel']")
            c.wait_for("JSON.parse(sessionStorage.getItem('__opens') || '[]').length === 1", 5)
            case("(the check does see a request to open a folder: the folder's own button makes exactly one, and it never leaves the page)",
                 opens() == [f"/open?kit={KQ}&sub=Carousel"] and asked_open() == [], (opens(), asked_open()))
            c.js("sessionStorage.removeItem('__opens')")

            # ---- the carousel picker's Done line ----
            c.open(f"{base}/arrange.html?kit={KQ}&piece=carousel")
            c.wait_for("document.querySelectorAll('#row .rt').length >= 2 && !document.getElementById('happy').disabled", 20)
            case("picker: before the button is pressed there is no 'Lay out the slides'", c.js("document.getElementById('layout').hidden") is True and c.rect("#layout")["w"] == 0)
            c.click("#happy")
            c.wait_for("!document.getElementById('openfolder').hidden", 60, tell="document.getElementById('doneline').textContent")
            line = c.text("#doneline")
            case("picker: with the slides made, the line has 'Open the Carousel folder' and 'Lay out the slides' beside it", "slides" in line and c.js("document.getElementById('layout').hidden") is False and c.text("#layout") == LAY_OUT, line)
            a, b, d = c.rect("#openfolder"), c.rect("#layout"), c.rect("#doneline")
            case("picker: the two sit on one line, the link after the folder's button, and neither is cut off by the window",
                 abs(a["cy"] - b["cy"]) < 4 and b["x"] >= a["right"] and b["right"] <= 1280 and b["w"] > 60 and b["h"] >= 28, (a, b, d))
            c.click("#layout")
            c.wait_for("location.pathname === '/design.html' && window.Designer && Designer.st && Designer.S", 20, tell="location.href")
            case("picker: pressing 'Lay out the slides' opens the designer for that shoot", c.js("location.pathname + location.search").startswith(f"/design.html?kit={KQ}") and c.js("Designer.KIT") == kit_name, c.js("location.href"))
            case("picker: pressing it asked for no folder to be opened", opens() == [] and asked_open() == [], (opens(), asked_open()))
            case("picker: nothing on any of these pages threw an error", not c.page_errors(), c.page_errors())
            # ---- Save slides pressed, in the real page, on a design whose slides are already saved ----
            rec_file = target / "The Assistant" / "Your Content" / kit_name / ".kit" / "kit.json"
            car_dir = rec_file.parent.parent / "Carousel"
            nums = json.loads(rec_file.read_text(encoding="utf-8"))["picks"]["carousel"]
            run(env, "kit.py", "picks", kit_name, "--carousel", ",".join(str(n) for n in reversed(nums)))
            code, out = run(env, "kit.py", "build", kit_name)
            kind = (json.loads(rec_file.read_text(encoding="utf-8")).get("carousel_set") or {}).get("kind")
            case("designer page: (a new order of the plain slides was made from the chat, so the plain slides are the carousel shown)", code == 0 and kind == "plain", (out[-200:], kind))
            files_before = sorted(os.listdir(car_dir))
            c.reload()
            c.wait_for("window.Designer && Designer.st && Designer.S && Designer.design && Designer.design.set && !document.getElementById('save-slides').disabled", 20, tell="document.body.innerText.slice(0, 200)")
            sent = lambda what: sum(1 for r_ in list(c.requests) if what in r_["url"])      # noqa: E731
            slides_before, commits_before = sent("/design-slide"), sent("/design-commit")
            c.click("#save-slides")
            c.wait_for("document.getElementById('save-line').textContent.indexOf('Already saved as') === 0", 20, tell="document.getElementById('save-line').textContent")
            line = c.text("#save-line")
            case("designer page: Save slides on the unchanged design says 'Already saved as ...' at once, and draws and sends no slide",
                 line == f"Already saved as \"{NAME}\". Change something to save a new set." and sent("/design-slide") == slides_before, line)
            try:
                cd.wait_until(lambda: (json.loads(rec_file.read_text(encoding="utf-8")).get("carousel_set") or {}).get("kind") == "laid-out", 20)
            except cd.Timeout:
                pass
            cs = json.loads(rec_file.read_text(encoding="utf-8")).get("carousel_set") or {}
            case("designer page: ...and that press made its set the carousel shown again (one request to the Assistant, no new file in the folder)",
                 cs.get("kind") == "laid-out" and cs.get("base") == NAME and sent("/design-commit") == commits_before + 1 and sorted(os.listdir(car_dir)) == files_before,
                 (cs.get("kind"), cs.get("base"), sent("/design-commit") - commits_before))
            code, h, data = ask(P, "GET", f"/content/{KQ}/Post%20kit.html")
            sec, srcs, sub = _carousel_section(data.decode("utf-8", "replace"))
            case("designer page: ...and the kit page shows that set again and says so", len(srcs) == N and f"saved as \u201c{NAME}\u201d" in sub, sub)
            case("designer page: nothing on the page threw an error", not c.page_errors(), c.page_errors())
            # at a phone's width the Done line still fits
            c.phone(390, 844)
            c.open(f"{base}/arrange.html?kit={KQ}&piece=carousel")
            c.wait_for("document.querySelectorAll('#row .rt').length >= 2 && !document.getElementById('happy').disabled", 20)
            c.tap("#happy")         # the order is the new one from the chat, so the button is pressed afresh, with a finger
            c.wait_for("!document.getElementById('openfolder').hidden", 60, tell="document.getElementById('doneline').textContent")
            b = c.rect("#layout")
            case("picker, at a phone's width: the link is showing, inside the window, and the page does not scroll sideways",
                 b["w"] > 60 and b["x"] >= 0 and b["right"] <= 390 and c.js("document.documentElement.scrollWidth <= window.innerWidth") is True, b)
            c.desktop()
    finally:
        srv.stop()
