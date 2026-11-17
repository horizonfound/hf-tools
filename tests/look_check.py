#!/usr/bin/env python3
"""The pages' shared look (look.py), checked: the font route refuses everything but its three files, the shared
styles have no serif and nothing from the internet, the report and the editing queue are built on it, and the path
at the top of every post kit page (Nicole's v27 crumbs.js, built here on the server) says her words, links only to
paths of this server, and matches her rules line for line when her v27 handoff is on this computer.

    python3 tests/look_check.py

Python 3.9, standard library only, a Mac or a PC. In scratch folders it makes itself; the two page servers it
starts (the report's and the editing queue's) are on ports 9830 and up (LOOK_TEST_PORT moves them) and are
stopped at the end.
"""
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
FONTS = ROOT / "plugins" / "the-engine" / "shared" / "fonts"
BASE = int(os.environ.get("LOOK_TEST_PORT", "9830"))
WINDOWS = os.name == "nt"
SERIF = re.compile(r"Fraunces|Cormorant|Georgia|Iowan|Palatino|serif(?!-)|var\(--display\)|--display|googleapis|gstatic", re.I)
results = []


def case(what, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:300]}]" if detail and not ok else ""), flush=True)


class FakeHandler:
    """Just enough of a request handler to see what look.serve_font answers."""
    def __init__(self):
        self.code, self.headers, self.wfile = None, {}, io.BytesIO()

    def send_error(self, code, *a):
        self.code = code

    def send_response(self, code):
        self.code = code

    def send_header(self, k, v):
        self.headers[k] = v

    def end_headers(self):
        pass


def sans_only(css):
    """The CSS with the 'sans-serif' fallback word taken out, so a search for serif finds only a real one."""
    return css.replace("sans-serif", "")


def get(url, host=None):
    req = urllib.request.Request(url, headers={"Host": host} if host else {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, b"", {}


def wait(url):
    for _ in range(100):
        try:
            urllib.request.urlopen(url, timeout=2).read()
            return True
        except Exception:  # noqa: BLE001
            time.sleep(0.2)
    return False


def main():
    work = Path(tempfile.mkdtemp(prefix="look check "))
    studio_home = work / "studio"
    studio_home.mkdir()
    env = dict(os.environ, STUDIO_HOME=str(studio_home), PYTHONIOENCODING="utf-8")
    os.environ["STUDIO_HOME"] = str(studio_home)
    sys.path.insert(0, str(SCRIPTS))
    import look

    # ---- 1. the font route, without a server
    semi = (FONTS / "DMSans-SemiBold.ttf").read_bytes()
    h = FakeHandler()
    look.serve_font(h, "f=DMSans-SemiBold")
    case("serve_font: DMSans-SemiBold comes back byte for byte as a font", h.code == 200 and h.wfile.getvalue() == semi
         and h.headers.get("Content-Type") == "font/ttf" and h.headers.get("Content-Length") == str(len(semi)), h.code)
    for q in ("f=../DMSans-SemiBold", "f=..%2FDMSans-SemiBold", "f=Fraunces-Italic", "f=", "", "f=DMSans-Regular&f=DMSans-Medium",
              "f=DMSans-Regular.ttf", "f=/etc/passwd", "f=DMSans-Regular&x=1", "x=DMSans-Regular", "f=dmsans-regular",
              "f=CormorantGaramond-Italic", "f=DMSans-Regular%00"):
        h = FakeHandler()
        look.serve_font(h, q)
        case("serve_font refuses %r" % q, h.code == 404 and h.wfile.getvalue() == b"", h.code)
    for key, _ in look.FACES:
        h = FakeHandler()
        look.serve_font(h, "f=" + key)
        case("serve_font serves %s" % key, h.code == 200 and h.wfile.getvalue() == (FONTS / (key + ".ttf")).read_bytes())

    # ---- 2. the shared styles
    head = look.head_css()
    case("head_css: no serif, no --display, nothing from the internet", not SERIF.search(sans_only(head)), SERIF.findall(sans_only(head)))
    case("head_css: the only addresses are the pages' own font route",
         re.findall(r"url\('([^']*)'\)", head) == ["/look-font?f=" + k for k, _ in look.FACES])
    case("head_css: the font is the plugin's DM Sans under the pages' own name, first in the font list",
         "font-family:'Assistant Sans'" in head and look.SANS.startswith("'Assistant Sans',") and "DM Sans" not in look.SANS
         and "--sans:" + look.SANS in head)
    case("head_css: no backslash (it goes into raw strings and pages as it is)", "\\" not in head)
    for name, val in (("cream", "#FAFAF6"), ("ink", "#1F2430"), ("coral-2", "#D4643F"), ("line", "rgba(31,36,48,.12)")):
        case("ROOT has --%s %s (the reel page's)" % (name, val), "--%s:%s;" % (name, val) in look.ROOT)

    # ---- 3. the pages built on it
    import report_page
    import first_look
    import edit_queue
    import reel_page
    for label, css in (("report_page.CSS", report_page.CSS), ("first_look.CSS", first_look.CSS), ("edit_queue.CSS", edit_queue.CSS),
                       ("reel_page.STYLE", reel_page.STYLE), ("reel_page.OUR_CSS", reel_page.OUR_CSS)):
        case(label + ": no serif, no --display, nothing from the internet", not SERIF.search(sans_only(css)), SERIF.findall(sans_only(css)))
        case(label + ": no italic left on a heading or a quiet line (DM Sans has no italic of its own)",
             not re.search(r"font:\s*italic", css), re.findall(r"[^}]*font:\s*italic[^}]*", css)[:2])
    case("report_page and edit_queue no longer name Google Fonts", not hasattr(report_page, "FONTS") and not hasattr(edit_queue, "FONTS"))
    # the posts side (group B): the posting page, the home page, the post kit
    import posting_queue
    import home
    import kit
    for label, css in (("posting_queue.CSS", posting_queue.CSS), ("home.CSS_EXTRA", home.CSS_EXTRA), ("kit.CSS", kit.CSS)):
        case(label + ": no serif, no --display, nothing from the internet", not SERIF.search(sans_only(css)), SERIF.findall(sans_only(css)))
        case(label + ": no italic left on a heading or a quiet line (DM Sans has no italic of its own)",
             not re.search(r"font:\s*italic", css), re.findall(r"[^}]*font:\s*italic[^}]*", css)[:2])
    case("posting_queue no longer names Google Fonts, and the reel page has no /reel-font fallback in its page",
         not hasattr(posting_queue, "FONTS") and not hasattr(reel_page, "SANS_FALLBACK_CSS"))
    case("the kit page's head is the shared look (no /reel-font, no Fraunces)", kit._font_css() == look.head_css())
    # the pickers and the designer (group C): their own colour names, valued from look.py; the page's fonts added
    # by the page (never in the styles); the designer's slide fonts are the photographer's and not checked here
    import arrange_page
    import design_page
    chrome = arrange_page.CSS + design_page.DESIGN_CSS + design_page.PART_CSS
    # (the preview's stand-in profile picture, a small warm circle, is a picture of Instagram, not the page's look)
    chrome = re.sub(r"\.pv-igtop i\{[^}]*\}", "", chrome)
    case("the pickers' and the designer's own styles: no serif, nothing from the internet, no @font-face",
         not SERIF.search(sans_only(chrome)) and "@font-face" not in chrome and "url(" not in chrome, SERIF.findall(sans_only(chrome)))
    case("the pickers' colours and font list are look.py's (cream, paper, ink, coral, the shared font list)",
         all("--%s:%s;" % kv in arrange_page.CSS for kv in (("bg", look.COLOR["cream"]), ("panel", look.COLOR["paper"]), ("ink", look.COLOR["ink"]),
                                                          ("soft", look.COLOR["ink-2"]), ("line", look.COLOR["line"]), ("accent", look.COLOR["coral-2"])))
         and "--sans:" + look.SANS + ";" in arrange_page.CSS
         and not re.search(r"#f6f3ee|#fffdf9|#2a2622|#c4683f|#efe9e0|-apple-system", chrome.replace(look.SANS, ""), re.I),
         re.findall(r"#f6f3ee|#fffdf9|#2a2622|#c4683f|#efe9e0|-apple-system", chrome.replace(look.SANS, ""), re.I)[:3])
    # the reviewers' fixes (Nov 7)
    case("the font list sends the few symbols DM Sans lacks to the Mac's own font, not Lucida Grande or PingFang",
         look.SANS.startswith("'Assistant Sans',-apple-system,BlinkMacSystemFont,") and "'Segoe UI'" in look.SANS)
    case("no slanted DM Sans left on the report or the queue ('Not written yet', 'Next up: <name>')",
         "font-style:italic" not in report_page.CSS + edit_queue.CSS and "#next em{font-style:normal" in edit_queue.CSS)
    case("the report's footer wordmark fills its band again (11.2vw, up to 144px)",
         ".wordmark{font:600 clamp(40px,11.2vw,144px)/.78 var(--sans)" in report_page.CSS)
    case("the pickers' top bar: the coral BY HORIZON FOUND and pill buttons of every other page, the old by-line on a phone so nothing wraps",
         "text-transform:uppercase;color:var(--accent)}" in arrange_page.CSS and "border-radius:10px" not in
         re.search(r"\.bar \.homelink\{[^}]*\}", arrange_page.CSS).group(0) + re.search(r"\.bar \.kitlink\{[^}]*\}", arrange_page.CSS).group(0)
         and ".brand small{margin-top:2px;font:400 11.5px/1.1 var(--sans);letter-spacing:0;text-transform:none;color:var(--soft-s)}}" in arrange_page.CSS)
    pick, plain = arrange_page.page_html("A kit", "reel"), arrange_page.plain_page("Nothing here.")
    des = design_page.page_html("A kit"); story = design_page.page_html("A kit", "stories")
    case("the pickers, their plain page and both designers start their styles with the page server's own fonts",
         all(pg.count("<style>" + look.font_css()) == 1 and "googleapis" not in pg.split("<script")[0] for pg in (pick, plain, des, story)))

    # a small backup's report, written for real
    session = work / "2026-11-07 look test"
    st = session / "_studio"
    st.mkdir(parents=True)
    (st / "manifest.json").write_text(json.dumps({"session": "2026-11-07 look test", "source": str(work / "card"), "dest": str(session),
                                                 "files": {}, "problems": [], "started": "2026-11-07T10:00:00", "finished": "2026-11-07T10:05:00"}),
                                      encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "report_page.py"), str(session)], env=env, capture_output=True, encoding="utf-8")
    page = (st / "report.html").read_text(encoding="utf-8") if (st / "report.html").exists() else ""
    case("the report is written", r.returncode == 0 and page, (r.stdout + r.stderr)[-300:])
    case("the report: no link to the internet, the shared look first in its styles",
         "<link" not in page and not re.search(r"https?://", page) and "<style>" + look.head_css() in page)
    case("the report: no serif anywhere in it", not SERIF.search(sans_only(page)), SERIF.findall(sans_only(page)))
    q = edit_queue.page_html(edit_queue.load())
    case("the editing queue page: no link to the internet, the shared look first, no serif",
         "<link" not in q and "fonts.googleapis" not in q and "<style>" + look.head_css() in q and not SERIF.search(sans_only(q)),
         SERIF.findall(sans_only(q)))

    # ---- 3b. the path at the top (Nicole's v27 crumbs.js, built on the server: look.crumbs, look.kit_trail)
    beach = look.kit_trail("2026-06-24 Beach")
    case("kit_trail: the kit's crumb is the folder name without its date, linked to the kit page by its folder name",
         beach == [("Beach post kit", "/content/2026-06-24%20Beach/Post%20kit.html")], beach)
    case("kit_trail: a name with no date, and one with an apostrophe and spaces, each quoted for the address only",
         look.kit_trail("Beach") == [("Beach post kit", "/content/Beach/Post%20kit.html")]
         and look.kit_trail("Mom's beach day") == [("Mom's beach day post kit", "/content/Mom%27s%20beach%20day/Post%20kit.html")])
    case("look.short_name is kit.short_name's rule (look never imports the post kit)",
         all(look.short_name(n) == kit.short_name(n) for n in ("2026-06-24 Beach", "Beach", "2026-06-24", "2026-06-24  Two spaces", "20260624 Nope", ""))
         and "import kit" not in (SCRIPTS / "look.py").read_text(encoding="utf-8"))
    nav = look.crumbs(beach + [("Captions", None)])
    case("crumbs: Home › Beach post kit › Captions, Home and the kit as links, Captions as where you are",
         nav == "<nav class='crumbs' aria-label='Where you are'><a href='/home'>Home</a><span class='sep' aria-hidden='true'>›</span>"
                "<a href='/content/2026-06-24%20Beach/Post%20kit.html'>Beach post kit</a><span class='sep' aria-hidden='true'>›</span>"
                "<span class='here' aria-current='page'>Captions</span></nav>", nav)
    case("crumbs: a kit page's own crumb with no link (where you are), and the unreachable page's plain 'Post kit'",
         look.crumbs([("Beach post kit", None)]).endswith("<span class='here' aria-current='page'>Beach post kit</span></nav>")
         and look.crumbs([("Post kit", None)]).count("<a ") == 1)
    nav = look.crumbs([("A <b>&\"x'", "/x?a=1&b=2"), ("Reels", None), ("B-roll", "/reel.html?kit=x")])
    case("crumbs: a label with <, & and quotes is escaped; a link's & too", "<b>" not in nav and "&lt;b&gt;&amp;&quot;x&#x27;" in nav
         and "href='/x?a=1&amp;b=2'" in nav, nav)
    case("crumbs: the last step is never a link, even when given one; aria-current sits on it alone",
         nav.count("<a ") == 2 and "/reel.html" not in nav and nav.count("aria-current='page'") == 1
         and nav.endswith("<span class='here' aria-current='page'>B-roll</span></nav>"), nav)
    case("crumbs: a step with no link before the last is plain words, never a dead link, and not where you are",
         "<span class='sep' aria-hidden='true'>›</span><span class='here'>Reels</span><span class='sep'" in nav, nav)
    case("crumbs: one separator between each pair, Home first, nothing to the internet",
         nav.count("class='sep'") == 3 and nav.startswith("<nav class='crumbs' aria-label='Where you are'><a href='/home'>Home</a>")
         and "http" not in nav and "://" not in nav)
    refused = []
    for bad in ("http://127.0.0.1:8790/home", "//evil.example/home", "home", "/x\n", "/x\r", 5, b"/home"):
        try:
            look.crumbs([("Reels", bad), ("B-roll", None)])
            refused.append((bad, "accepted"))
        except ValueError:
            pass
    case("crumbs refuses a link that is not a path of this server (her http://127.0.0.1:8790/home, //host, no slash, a line break, not a string)",
         not refused, refused)
    refused = []
    for bad in ((None, None), ("", None), ("  ", "/x"), (5, None), ("a", "/x", "b"), "Reels", ("a",)):
        try:
            look.crumbs([bad, ("B-roll", None)])
            refused.append((bad, "accepted"))
        except (ValueError, TypeError):
            pass
    case("crumbs refuses a step that is not (a few words, a link)", not refused, refused)
    case("crumbs on an empty trail is Home alone, where you are", look.crumbs([]) == "<nav class='crumbs' aria-label='Where you are'><span class='here' aria-current='page'>Home</span></nav>")
    # her rules, with the look's own names where she wrote the colour and the font
    case("the path's rules are in every page's shared look (BASE, head_css)", look.CRUMBS in look.BASE and look.CRUMBS in look.head_css())
    case("the path's rules name the look's own colour and font, never #D4643F or 'DM Sans' by name, no serif",
         "var(--coral-2)" in look.CRUMBS and "font:600 13.5px/1.3 var(--sans)" in look.CRUMBS and "#D4643F" not in look.CRUMBS.upper()
         and "DM Sans" not in look.CRUMBS and "Helvetica" not in look.CRUMBS and not SERIF.search(sans_only(look.CRUMBS)))
    case("a saved copy of a page (no .live) draws the path as plain words: no link to press; the rule is the kit page's own, not in every page's look",
         look.CRUMBS_SAVED.startswith("body:not(.live) .crumbs a{pointer-events:none") and look.CRUMBS_SAVED not in look.BASE and look.CRUMBS_SAVED not in look.head_css()
         and "not(.live)" not in look.CRUMBS and "look.CRUMBS_SAVED" in (SCRIPTS / "kit.py").read_text(encoding="utf-8"))
    case("a shoot named in one long unbroken piece may break inside its crumb (ours, so a phone never scrolls sideways)",
         ".crumbs a,.crumbs .here{overflow-wrap:anywhere}" in look.CRUMBS)
    src = (SCRIPTS / "look.py").read_text(encoding="utf-8")
    case("look.py has none of her test-only wiring: no localStorage, no assistantHomeTest, no home-test.html, no 8790",
         not re.search(r"localStorage|assistantHomeTest|home-test|8790/", src))
    hers = None
    for base in (ROOT, Path("/Users/dustindamron/Projects/hf-tools")):
        for f in sorted((base / "reference-private").glob("nicole-handoff-v2[7-9]-*/Carousel designer and reel picker/pages/crumbs.js"), reverse=True):
            hers = f.read_text(encoding="utf-8")
            break
        if hers:
            break
    if hers is None:
        print("SKIP  her crumbs.js against ours: her handoff v27 is not on this computer", flush=True)
    else:
        her_css = re.search(r"css\.textContent = `(.*?)`", hers, re.S).group(1)
        swap = lambda t: t.replace("'DM Sans','Helvetica Neue',Arial,sans-serif", "var(--sans)").replace("#D4643F", "var(--coral-2)")
        her_rules = [swap(x.strip()) for x in her_css.strip().splitlines()]
        our_rules = [x.strip() for x in look.CRUMBS.strip().splitlines()]
        case("her five rules are ours, line for line (her colour and font by the look's names)", all(r in our_rules for r in her_rules), [r for r in her_rules if r not in our_rules])
        case("ours are her five and one of our own (long names break)", our_rules[:5] == her_rules and len(our_rules) == 6 and our_rules[5].startswith(".crumbs a,.crumbs .here{overflow-wrap"), our_rules)
        words = {k: v.replace("{shoot}", "") for k, v in look.CRUMB_WORDS.items()}
        case("her words on the path are ours: Home, ' post kit', 'Post kit', 'Where you are' (from her post-kit.html's nav), ›",
             all(w in hers for k, w in words.items() if k != "where") and "<span class=\"sep\" aria-hidden=\"true\">›</span>" in hers
             and look.CRUMB_WORDS["where"] in next(f.read_text(encoding="utf-8") for base in (ROOT, Path("/Users/dustindamron/Projects/hf-tools"))
                                                   for f in sorted((base / "reference-private").glob("nicole-handoff-v2[7-9]-*/Carousel designer and reel picker/pages/post-kit.html"), reverse=True)),
             words)
        case("and hers are ours: every word her script puts on the path is in CRUMB_WORDS",
             all(w in words.values() for w in ("Home", " post kit", "Post kit", "›")) and "aria-current=\"page\"" in hers and "aria-hidden=\"true\"" in hers)
        case("her hard-coded address is not copied: ours is the path /home", "http://127.0.0.1:8790/home" in hers and look.HOME_PATH == "/home")

    # ---- 4. the font from the two servers this part of the look puts it on
    procs = []
    try:
        def start(*a):
            kw = {"creationflags": 0x00000200} if WINDOWS else {"start_new_session": True}
            p = subprocess.Popen([sys.executable, *map(str, a)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
            procs.append(p)
        start(SCRIPTS / "serve_report.py", session, "--port", str(BASE))
        start(SCRIPTS / "edit_queue.py", "serve", "--port", str(BASE + 5))
        def port_in(f, fallback):
            # each server writes the address it took (the asked-for port may be taken)
            for _ in range(100):
                try:
                    return f.read_text(encoding="utf-8").strip().split(":")[2].split("/")[0]
                except (OSError, IndexError):
                    time.sleep(0.2)
            return str(fallback)
        rport = port_in(st / "report-url.txt", BASE)
        qport = port_in(studio_home / "queue-url.txt", BASE + 5)
        start(SCRIPTS / "posting_queue.py", "serve", "--port", str(BASE + 10))
        pport = port_in(studio_home / "posting-url.txt", BASE + 10)
        case("all three servers came up", wait(f"http://127.0.0.1:{rport}/report.html") and wait(f"http://127.0.0.1:{qport}/queue.html")
             and wait(f"http://127.0.0.1:{pport}/home"))
        for label, port in (("report server", rport), ("editing queue server", qport), ("posting server", pport)):
            code, body, hd = get(f"http://127.0.0.1:{port}/look-font?f=DMSans-SemiBold")
            case(label + ": /look-font gives DMSans-SemiBold byte for byte", code == 200 and body == semi and hd.get("Content-Type") == "font/ttf", code)
            for bad in ("../DMSans-SemiBold", "Fraunces-Italic", ""):
                code, body, _ = get(f"http://127.0.0.1:{port}/look-font?f={bad}")
                case(label + ": /look-font refuses %r" % bad, code == 404 and not body, code)
            code, body, _ = get(f"http://127.0.0.1:{port}/look-font?f=DMSans-Regular", host="example.com")
            case(label + ": a request naming another host gets no font", code == 403 and not body, code)
        code, body, _ = get(f"http://127.0.0.1:{rport}/report.html")
        case("report server: the report it serves asks for no outside address", code == 200 and b"googleapis" not in body and b"/look-font?f=" in body)
        code, body, _ = get(f"http://127.0.0.1:{qport}/queue.html")
        case("editing queue server: its page asks for no outside address", code == 200 and b"googleapis" not in body and b"/look-font?f=" in body)
        for path in ("/home", "/posting.html"):
            code, body, _ = get(f"http://127.0.0.1:{pport}{path}")
            case("posting server: %s asks for no outside address, takes the shared look, no serif" % path,
                 code == 200 and b"googleapis" not in body and b"<link" not in body and ("<style>" + look.head_css()).encode() in body
                 and not SERIF.search(sans_only(body.decode("utf-8"))), (code, SERIF.findall(sans_only(body.decode("utf-8", "replace")))[:3]))
    finally:
        for p in procs:
            try:
                if WINDOWS:
                    p.terminate()
                else:
                    os.killpg(p.pid, signal.SIGTERM)
            except Exception:  # noqa: BLE001
                pass
        for p in procs:
            try:
                p.wait(5)
            except Exception:  # noqa: BLE001
                p.kill()
        shutil.rmtree(work, ignore_errors=True)

    print(f"\n{sum(results)} of {len(results)} passed.")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
