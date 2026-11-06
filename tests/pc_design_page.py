#!/usr/bin/env python3
"""The carousel designer's REAL page on a PC: opened in a hidden Chrome, drawn, and saved. Written to run on
GitHub's Windows machine (which carries Chrome), and on a Mac.

    python tests/pc_design_page.py [--port 9330]
    ASSISTANT_PAGE_KEEP=<folder>     where a failed run leaves a picture of the page and the two logs

tests/design_check.py is the full test of the page (1,371 cases), but it cannot run on a PC yet: it stops without
the Mac's sips, makes its pretend shoots with tests/fake_kit.py (sips, and only under /private/tmp), and runs the
page's rule scripts under the Mac's own JavaScript engine (osascript). This is the short version that can: one
pretend shoot of six grey photos written in plain Python (tests/pc_plain_jpeg.py), the small copies made the way
this computer makes pictures (a Mac's sips; a PC's Pillow), the Assistant's own page server on a scratch port, and
the page in a hidden Chrome driven by tests/chrome_drive.py:
  * the page loads with no error of its own, shows one photo on each of six slides, and every photo is drawn;
  * the line about the key that turns snapping off names this computer's key (Alt on a PC);
  * Georgia, the font words fall back to, is on this computer; a font the plugin carries loads from the Assistant;
  * Save slides: six finished 1080 x 1350 JPEGs arrive in the Carousel folder, the line says so, the folder's
    button shows (it is NOT pressed: no window is ever opened), and, where Pillow is, slide 1 is the photo's grey;
  * the hidden Chrome is gone afterwards, every helper with it, and its throwaway profile removed.
Nothing is touched outside a scratch folder it makes itself. SKIP and exit 0 when there is no Chrome, or no way of
making pictures yet (a PC without Pillow). Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(os.environ.get("ASSISTANT_SCRIPTS") or ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts")
WINDOWS = os.name == "nt"
NEVER_PORTS = {8790, 8765, 8770, 8899}
PHOTOS = 6
results = []


def check(what, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:600]}]" if detail != "" and not ok else ""), flush=True)
    return bool(ok)


def skip(what, why):
    print(f"SKIP  {what}   [{why}]", flush=True)


sys.path.insert(0, str(Path(__file__).resolve().parent))
import chrome_drive  # noqa: E402
from pc_plain_jpeg import make_kit  # noqa: E402

PORT = None
if "--port" in sys.argv:
    PORT = int(sys.argv[sys.argv.index("--port") + 1])
    if any(p in NEVER_PORTS for p in range(PORT, PORT + 20)):
        sys.exit("STOP: that port range reaches one the real pages use.")

CHROME = chrome_drive.find_chrome()
if not CHROME:
    print("SKIP  the designer's real page   [no Chrome on this computer (set CHROME_DRIVE_CHROME to point at one): the page was not looked at]")
    sys.exit(0)

work = Path(tempfile.mkdtemp(prefix="assistant pc design page "))
STUDIO = work / "studio"
STUDIO.mkdir()
os.environ["STUDIO_HOME"] = str(STUDIO)           # before arrange is imported: it reads STUDIO_HOME then
ENV = dict(os.environ)
sys.path.insert(0, str(SCRIPTS))
import this_computer as tc  # noqa: E402
import pictures  # noqa: E402
import arrange  # noqa: E402
import design  # noqa: E402

tc.utf8_output()
try:
    from PIL import Image
    HAVE_PIL = True
except Exception:  # noqa: BLE001
    HAVE_PIL = False
print(f"This is a {tc.COMPUTER}, Python {sys.version.split()[0]}; small pictures made "
      f"{'the Mac way (sips)' if pictures.use_sips() else 'the PC way (Pillow)'}; Chrome at {CHROME}\n", flush=True)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def keep(c, srv_log):
    """A failed run: a picture of the page and the logs, where the person (or GitHub) can pick them up."""
    where = os.environ.get("ASSISTANT_PAGE_KEEP")
    try:
        shot = c.screenshot("the page when it failed.png") if c is not None and c.alive() else None
    except Exception:  # noqa: BLE001
        shot = None
    if not where:
        return
    try:
        dst = Path(where)
        dst.mkdir(parents=True, exist_ok=True)
        for f in [shot, srv_log, STUDIO / "arrange.log"] + list(work.glob("chrome/*.log")):
            if f and Path(f).is_file():
                shutil.copy2(str(f), str(dst / Path(f).name))
    except OSError:
        pass


GEORGIA = """(function(){
  var c = document.createElement('canvas').getContext('2d'), words = 'Wiiiii mmm Quartz 0123';
  c.font = '40px Georgia, monospace'; var a = c.measureText(words).width;
  c.font = '40px monospace'; var b = c.measureText(words).width;
  return Math.abs(a - b) > 1;
})()"""
OWN_FONT = """(function(f){
  return new FontFace('PcDesignPageTest', 'url("/design-font-file?f=' + f + '")').load().then(function(){ return 'ok'; }, function(e){ return 'failed: ' + e; });
})"""
READY = "window.Designer && Designer.saver && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total"
DRAWN = "Array.prototype.filter.call(document.querySelectorAll('#strip .blk img'), function(i){ return i.complete && i.naturalWidth > 0; }).length"


def main():
    HOME = work / "The Assistant"
    r = subprocess.run([sys.executable, str(SCRIPTS / "posts.py"), "setup", "--home", str(HOME)], capture_output=True,
                       encoding="utf-8", errors="replace", env=ENV)
    if not check("a pretend Assistant folder is set up (posts.py setup)", r.returncode == 0, (r.stdout + r.stderr)[-300:]):
        return
    content = HOME / "Your Content"
    content.mkdir(parents=True, exist_ok=True)
    kit = make_kit(content, "2026-11-01 Zoë’s beach 🌊", PHOTOS)
    can, words = pictures.ready()
    if not can:
        skip("the designer's real page", f"this computer can't make pictures yet ({words})")
        return
    got = arrange.make_previews(kit, retry=True)
    if not check(f"the small copies of the {PHOTOS} photos are made, this computer's way", got.get("made") == PHOTOS and not got.get("failed"), got):
        return
    port = PORT or free_port()
    url_file = STUDIO / "posting-url.txt"
    log_path = work / "posting server.log"
    log = open(log_path, "wb")
    srv = tc.popen_detached([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(port)],
                            stdout=log, stderr=subprocess.STDOUT, env=ENV)
    c = None
    seen = {}
    try:
        said, t0 = "", time.monotonic()
        while time.monotonic() - t0 < 40 and srv.poll() is None:
            try:
                said = url_file.read_text(encoding="utf-8").strip()
            except OSError:
                said = ""
            if said:
                break
            time.sleep(0.2)
        if not check("the page server starts and says its address", bool(said) and srv.poll() is None,
                     log_path.read_bytes().decode("utf-8", "replace")[-400:]):
            return
        base = said.rsplit("/", 1)[0]
        c = chrome_drive.Chrome(work=work / "chrome", size=(1280, 900))
        c.start()
        seen["pid"], seen["profile"] = c.proc.pid, c.profile
        print(f"      (a hidden {c.version}, started in {c.started_in:.1f} s)", flush=True)
        c.open(base + "/design.html?kit=" + quote(kit.name), seconds=60)
        try:
            c.wait_for(READY, 60, tell="document.body.innerText.slice(0, 300)")
            ready = True
        except chrome_drive.Timeout as e:
            ready = str(e)
        if not check("the designer opens on the shoot and is ready", ready is True, ready):
            return
        st = c.js("JSON.stringify({slides: Designer.st.slides, blocks: Designer.st.blocks.length, name: Designer.design.name, kit: Designer.KIT})")
        st = json.loads(st)
        check(f"one photo on each of {PHOTOS} slides, in the shoot named by its folder alone",
              st["slides"] == PHOTOS and st["blocks"] == PHOTOS and st["kit"] == kit.name, st)
        try:
            c.wait_for(DRAWN + " >= %d" % PHOTOS, 60, tell=DRAWN)
            drawn = True
        except chrome_drive.Timeout as e:
            drawn = str(e)
        check("every photo on the strip is drawn from a copy this computer made", drawn is True, drawn)
        title = c.js("document.querySelector('#g-snap label').title")
        want = "Hold Alt while you drag" if WINDOWS else "Hold Option (Alt on a PC) while you drag"
        check(f"the line about snapping names this computer's key ({'Alt' if WINDOWS else 'Option'})", want in title, title)
        check("Georgia, the font words fall back to, is on this computer", c.js(GEORGIA) is True)
        own = next((f for f in design.OWN_FILES if (design.FONT_DIR / f"{f}.ttf").is_file()), None)
        if own:
            got = c.js(OWN_FONT + "(%s)" % json.dumps(own))
            check(f"a font the plugin carries ({own}) loads from the Assistant itself", got == "ok", got)
        else:
            skip("a font the plugin carries loads from the Assistant itself", "this copy of the plugin carries no font files")
        check("no error of the page's own so far", not c.page_errors(), c.page_errors()[:3])
        # Save slides
        c.click("#save-slides")
        try:
            c.wait_for("!Designer.saver.busy() || Designer.saver.asking()", 180, tell="document.getElementById('save-line').textContent")
        except chrome_drive.Timeout:
            pass
        line = c.text("#save-line")
        check("Save slides: the line says the six slides are in the Carousel folder",
              line.startswith(f"Saved {PHOTOS} slides in your Carousel folder, named \""), line)
        car = kit / "Carousel"
        files = sorted(n for n in os.listdir(car)) if car.is_dir() else []
        whole = [n for n in files if design.slide_ok((car / n).read_bytes())]
        check(f"{PHOTOS} finished 1080 x 1350 JPEGs are in the Carousel folder, and nothing else", len(files) == PHOTOS and whole == files, files)
        check("no path anywhere on the page's lines", "\\" not in line and str(work) not in c.js("document.body.innerText"))
        check("the folder's button shows beside the line (it is not pressed here: no window is ever opened)",
              c.js("!document.getElementById('open-wrap').hidden") is True)
        if HAVE_PIL and files:
            with Image.open(car / files[0]) as im:
                px = im.convert("RGB").getpixel((540, 675))
            grey = 128 + 2 * 5                    # photo 1 is the grey of level 5 (tests/pc_plain_jpeg.py)
            check("slide 1 is the first photo's own grey, not a blank slide", all(abs(v - grey) <= 6 for v in px), px)
        else:
            skip("slide 1 is the first photo's own grey", "Pillow is not installed for this Python" if files else "no slide to read")
        check("no error of the page's own at the end", not c.page_errors(), c.page_errors()[:3])
    except Exception as e:  # noqa: BLE001
        import traceback
        check("the page ran to the end of the test", False, f"{e.__class__.__name__}: {e} | {traceback.format_exc()[-700:]}")
    finally:
        if results.count(False):
            keep(c, log_path)
        if c is not None:
            t0 = time.time()
            c.stop()
            gone = True
            if seen.get("pid"):
                alive = tc.still_running(seen["pid"])
                end = time.time() + 10
                while alive and time.time() < end:
                    time.sleep(0.2)
                    alive = tc.still_running(seen["pid"])
                gone = alive is not True
            check(f"the hidden Chrome is gone ({time.time() - t0:.1f} s to stop it)", gone)
            check("and its throwaway profile is removed", not c.profile_left and not Path(seen["profile"]).exists(), seen.get("profile"))
        srv.terminate()
        try:
            srv.wait(15)
        except subprocess.TimeoutExpired:
            srv.kill()
            srv.wait(15)
        log.close()
        check("the page server is stopped", srv.poll() is not None)


main()
failed = results.count(False)
print(f"\n{len(results)} checks, {sum(results)} passed, {failed} failed." + (f"  Scratch folder, kept to look at: {work}" if failed else ""))
if not failed:
    shutil.rmtree(work, ignore_errors=True)
sys.exit(1 if failed else 0)
