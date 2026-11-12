#!/usr/bin/env python3
"""The "get a tap on your phone" page (Dustin, Nov 11): when a shoot is on more than one memory card, the
photographer walks away and needs a tap on their phone to come back and put the next card in. That tap only
reaches the phone when Remote Control is on for the conversation, and it is off by default.

Most of the time nobody sees this page: the Assistant can see whether Remote Control is on and can switch it on
itself with their OK (see parts/backup.md). This page is the fallback, a picture of the two things to click, for
when the Assistant cannot do it.

    python3 phone_setup.py url     the page's address on the Assistant's page server (started if it isn't running)
    python3 phone_setup.py page    the page as HTML, to look at

The two pictures are made from screenshots of the Claude app by tools/make_phone_pictures.py.
"""
import base64
import html
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brand  # noqa: E402
import look  # noqa: E402  (the font, the colours and the rules every page shares)
import this_computer  # noqa: E402
this_computer.utf8_output()

PICTURES = HERE.parent / "pictures"
ROUTE = "/phone-setup"

STEPS = (
    ("phone-step-1.png", "Open the panel",
     "Near the top of the Claude window there is a short row of small buttons. Click the first one, the one with three lines."),
    ("phone-step-2.png", "Switch Remote Control on",
     "In the panel that opens, find Remote Control and click its switch. It turns blue when it is on."),
    (None, "Check your phone",
     "Open the Claude app on your phone, signed in with the same account you use here, and let it send you notifications."),
)

CSS = """
body{margin:0;background:var(--cream,#FAFAF6);color:var(--ink,#1F2430);font:400 16px/1.5 var(--sans,system-ui)}
.wrap{max-width:720px;margin:0 auto;padding:clamp(1.2rem,4vw,2.4rem) 16px 3rem}
.homelink{display:inline-flex;align-items:center;gap:.45em;font:600 13.5px/1 var(--sans);color:#fff;background:var(--ink,#1F2430);text-decoration:none;padding:10px 16px 10px 13px;border-radius:999px}
h1{font:600 clamp(26px,5vw,36px)/1.1 var(--sans);letter-spacing:-.02em;margin:1.4rem 0 .4rem}
.lede{color:#5b6070;margin:0 0 1.6rem}
.step{background:#fff;border-radius:18px;padding:1.1rem 1.2rem;margin:0 0 1rem;display:grid;gap:.6rem}
.step h2{font:600 18px/1.3 var(--sans);margin:0;display:flex;gap:.6rem;align-items:center}
.step .n{flex:none;width:28px;height:28px;border-radius:50%;background:var(--coral,#D4643F);color:#fff;display:grid;place-items:center;font:600 15px/1 var(--sans)}
.step p{margin:0}
.step img{max-width:100%;height:auto;border-radius:12px;display:block}
.done{font-weight:600;margin-top:1.4rem}
"""


def picture(name):
    """The picture as a data address, so the page is one piece. "" when the file is missing."""
    try:
        return "data:image/png;base64," + base64.b64encode((PICTURES / name).read_bytes()).decode("ascii")
    except OSError:
        return ""


def page_html(home="/home"):
    e = html.escape
    out = ["<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
           f"<title>Phone taps · {e(brand.name())}</title><style>{look.head_css()}{CSS}</style></head><body><div class='wrap'>",
           f"<a class='homelink' href='{e(home)}'><span aria-hidden='true'>&larr;</span> Back to home</a>",
           "<h1>Get a tap on your phone</h1>",
           "<p class='lede'>With more than one memory card, you'll want to know the moment a card is done so you can put the next one in. "
           "Three quick steps, once per backup.</p>"]
    for i, (pic, title, words) in enumerate(STEPS, 1):
        out.append(f"<section class='step'><h2><span class='n'>{i}</span>{e(title)}</h2><p>{e(words)}</p>")
        src = picture(pic) if pic else ""
        if src:
            out.append(f"<img src='{src}' alt='{e(title)}: where to click, circled'>")
        out.append("</section>")
    out.append("<p class='done'>That's it. Go back to the chat and say “go”.</p></div></body></html>")
    return "\n".join(out)


def url():
    import time
    import home
    u = home.url()
    if not u:
        return None
    mine = u.rsplit("/", 1)[0] + ROUTE
    # A page server that was started before this page existed starts over with the newer code when the home page
    # is asked for (home.url just did); give it a few seconds, and only hand the address over once it answers.
    for _ in range(40):
        try:
            if b"Get a tap on your phone" in this_computer.open_local(mine, timeout=2).read():
                return mine
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.25)
        home.url()
    return None


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "url":
        u = url()
        if not u:
            sys.exit("STOP: the page server would not start.")
        print(u)
    elif cmd == "page":
        print(page_html())
    else:
        sys.exit("usage: phone_setup.py url | page")
