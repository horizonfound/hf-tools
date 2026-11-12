#!/usr/bin/env python3
"""One report for a shoot on more than one card (Dustin, Nov 12: "card one is this, card two is this, and it'll
all have to be on the same page").

Each card is still its own backup with its own records (the card is a delivery, the shoot is the unit). This links
them and builds the shoot's page: the verdict for the whole shoot on top, the numbers added up, then one section
per card, which is that card's own report (report-card.html, the same page without its top bar and footer) in a
frame sized to its content, so every button on it keeps working. serve_report.py started on any of the cards
shows the shoot's page at /report.html and each card at /card/N/...

    python3 shoot_report.py link "<card 1's backup>" "<card 2's backup>" [...] [--shoot "Smith wedding"]
    python3 shoot_report.py build "<any card's backup>"
    python3 shoot_report.py show "<any card's backup>"

link: writes shoot.json into every card's records ({"shoot": name, "cards": [{"card": 1, "records": ..., "name":
...}]}), keeps cards already linked to the first one, and rebuilds the pages of the cards that have a report.
night.py --with "<card 1's backup>" does it for a card as it is backed up. Records only; no photo is read.
Exit codes: 0 done, 1 a problem, 2 nothing to do.
"""
import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from where import locate, same_place  # noqa: E402
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()

SHOOT = "shoot.json"
PAGE = "shoot-report.html"
CARD_PAGE = "report-card.html"


def say(msg):
    try:
        print(msg, flush=True)
    except (BrokenPipeError, OSError):
        pass


def records_of(spelled):
    """The records folder a card's recorded path names, before or after it settled (a records folder written down
    as <day folder>/_studio moves to <their place>/.studio/<night> when the night settles; where.locate finds it
    from the day folder). None when it cannot be found (the drive unplugged)."""
    p = Path(spelled)
    for cand in ([p, p.parent] if p.name == "_studio" else [p]):
        try:
            return locate(cand)[1]
        except SystemExit:
            continue
    return None


def read(studio, heal=True):
    """The shoot this card belongs to: shoot.json with every card's records found afresh, or None when the card is
    not part of a shoot. A recorded path that has moved (a settle) is written back in place when heal is on."""
    studio = Path(studio)
    f = studio / SHOOT
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        cards = data["cards"]
        assert isinstance(cards, list) and data.get("shoot")
    except (OSError, ValueError, KeyError, AssertionError, TypeError):
        return None
    moved = False
    for c in cards:
        # the path as written, then any earlier spelling of it (a settle moved it once; a drive came back)
        rec = None
        for spelled in [c.get("records", "")] + list(c.get("was") or []):
            rec = records_of(spelled)
            if rec:
                break
        c["found"] = str(rec) if rec else None
        if rec and not same_place(str(rec), c.get("records")):
            c["was"] = [w for w in [c.get("records")] + list(c.get("was") or []) if w and not same_place(w, str(rec))][:6]
            c["records"] = str(rec)
            moved = True
    if moved and heal:
        try:
            save(studio, data)
        except OSError:
            pass
    return data


def write_whole(path, text):
    """Written whole, then given its name, so a page server never reads half a file (as peek_sheets.save_json)."""
    import os
    import threading
    tmp = path.with_name(f"{path.name}.{os.getpid()}-{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    this_computer.replace(tmp, path)


def save(studio, data):
    out = {"shoot": data["shoot"], "cards": [{"card": c["card"], "records": c["records"], "name": c.get("name", ""), **({"was": c["was"]} if c.get("was") else {})} for c in data["cards"]]}
    write_whole(Path(studio) / SHOOT, json.dumps(out, indent=1, ensure_ascii=False))


def card_of(studio):
    """{"n": 2, "of": 3, "shoot": name} for a card of a shoot, else None (report_page.py asks)."""
    data = read(studio)
    if not data:
        return None
    try:
        here = str(Path(studio).resolve())
    except OSError:
        here = str(Path(studio))
    me = next((c for c in data["cards"] if c.get("found") and same_place(c["found"], here)), None)
    if not me:
        return None
    return {"n": me["card"], "of": len(data["cards"]), "shoot": data["shoot"]}


def shoot_name(session):
    """"2026-11-11 Smith wedding, card 2" -> "Smith wedding"."""
    name = session.split(" ", 1)[1] if session[:10].count("-") == 2 and " " in session else session
    return re.sub(r"[,\s]*\bcard\s*\d+\s*$", "", name, flags=re.I).strip() or name


def link(backups, shoot=None):
    found = []
    for b in backups:
        rec = records_of(b)
        if not rec:
            say(f"STOP: no backup records found for {b}")
            return 1
        found.append(rec)
    if len({str(r) for r in found}) < len(found):
        say("STOP: the same backup is named twice.")
        return 1
    first = read(found[0], heal=False) or {"shoot": None, "cards": []}
    cards = [c for c in first["cards"] if c.get("found")]
    for rec in found:
        if not any(same_place(c["found"], str(rec)) for c in cards):
            m = json.loads((rec / "manifest.json").read_text(encoding="utf-8"))
            cards.append({"card": len(cards) + 1, "records": str(rec), "found": str(rec), "name": m.get("session", rec.name)})
    if len(cards) < 2:
        say("Nothing to do: a shoot needs two or more cards to link.")
        return 2
    name = shoot or first.get("shoot") or shoot_name(cards[0]["name"])
    data = {"shoot": name, "cards": cards}
    for c in cards:
        save(Path(c["found"]), data)
    say(f"{name}: {len(cards)} cards linked")
    for c in cards:
        say(f"   card {c['card']}: {c['name']}")
    # the pages, for every card whose report already exists (a card still being backed up gets its pages at step 6)
    import report_page
    for c in cards:
        if (Path(c["found"]) / "report.html").exists():
            report_page.write_page(c["found"])
    return 0


# ---------------------------------------------------------------- the page
def facts(rec):
    """What the shoot's page says about one card, from its manifest: the same sums report_page.py makes."""
    import clips
    import report_page as rp
    m = json.loads((rec / "manifest.json").read_text(encoding="utf-8"))
    files = m.get("files", {})
    total = len(files)
    kinds = Counter(Path(k).suffix.lower().lstrip(".") or "other" for k in files)
    media = sum(n for k, n in kinds.items() if f".{k}" in rp.MEDIA)
    n_clips = sum(n for k, n in kinds.items() if f".{k}" in clips.VIDEO)
    second = m.get("second")
    ok_dest = sum(1 for e in files.values() if e.get("dest", {}).get("ok"))
    ok_second = sum(1 for e in files.values() if e.get("second", {}).get("ok")) if second else None
    problems = m.get("problems") or []
    work = m.get("work_seconds")
    return {"total": total, "bytes": sum(e.get("size", 0) for e in files.values() if e.get("size", 0) > 0),
            "ok": ok_dest, "problems": problems, "sample": m.get("sample"), "finished": m.get("finished"),
            "seconds": work if work else None, "started": m.get("started"),
            "all_good": not problems and ok_dest == total and (ok_second == total if second else True),
            "words": clips.words(media - n_clips, n_clips), "name": m.get("session", rec.name)}


def build(data):
    import brand
    import look
    import report_page as rp
    e = html.escape
    shoot = data["shoot"]
    cards = data["cards"]
    rows = []
    for c in cards:
        rec = Path(c["found"]) if c.get("found") else None
        if rec and (rec / "manifest.json").exists():
            rows.append((c, facts(rec)))
        else:
            rows.append((c, None))
    n = len(cards)
    total = sum(f["total"] for _, f in rows if f)
    ok = sum(f["ok"] for _, f in rows if f)
    size = sum(f["bytes"] for _, f in rows if f)
    missing = [c for c, f in rows if not f]
    bad = [(c, f) for c, f in rows if f and f["problems"]]
    unfinished = [(c, f) for c, f in rows if f and not f["problems"] and not f["all_good"]]
    samples = [(c, f) for c, f in rows if f and f["all_good"] and f["sample"]]
    finished = max((f["finished"] for _, f in rows if f and f["finished"]), default=None)
    both = "both" if n == 2 else f"all {n}"
    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
           f"<title>{e(brand.title(shoot))}</title><style>{look.head_css()}{rp.CSS}{CSS}</style></head><body>",
           f"<div class='wrap'><div class='bar'>{rp.home_link()}{brand.bar()}",
           f"<span class='when'>{e(rp.nice_time(finished)) if finished else 'Still running'}</span></div></div>",
           "<section class='wrap hero'>", f"<span class='eyebrow'>Backup report · {e(shoot)} · {n} cards</span>"]
    if missing:
        which = ", ".join(f"card {c['card']}" for c in missing)
        out.append(f"<h1 class='h1 bad'>I can't see {e(which)} right <span class='swap'>now.</span></h1>")
        out.append("<p class='lede'>Its records aren't where they were. Is the drive plugged in? The other cards are below.</p>")
        out.append("<span class='pill wait'><span class='dot'>…</span>Keep the cards for now</span>")
    elif bad:
        which = ", ".join(f"card {c['card']}" for c, _ in bad)
        out.append(f"<h1 class='h1 bad'>{e(which.capitalize())} needs you before this is <span class='swap'>safe.</span></h1>")
        out.append(f"<p class='lede'>{ok:,} of {total:,} files across the cards are copied and checked. Nothing on any memory card has been changed; "
                   "what stopped it is in that card's section below.</p>")
        out.append("<span class='pill bad'><span class='dot'>!</span>Not finished</span>")
    elif unfinished:
        which = ", ".join(f"card {c['card']}" for c, _ in unfinished)
        out.append(f"<h1 class='h1'>{e(which.capitalize())} isn't finished <span class='swap'>yet.</span></h1>")
        out.append(f"<p class='lede'>{ok:,} of {total:,} files across the cards are copied and checked so far.</p>")
        out.append("<span class='pill wait'><span class='dot'>…</span>Keep the cards for now</span>")
    elif samples:
        which = ", ".join(f"card {c['card']}" for c, _ in samples)
        out.append(f"<h1 class='h1'>A sample: part of {e(which)} was copied and <span class='swap'>verified.</span></h1>")
        out.append("<p class='lede'>This was a test run on part of a card, so that card is not backed up and is not safe to format. "
                   "Nothing on any memory card has been changed.</p>")
        out.append("<span class='pill wait'><span class='dot'>…</span>Keep the cards: this was a sample</span>")
    else:
        out.append(f"<h1 class='h1'>All {total:,} files on {both} cards, safely backed up and <span class='swap'>verified.</span></h1>")
        out.append("<p class='lede'>Every file was copied to your drive and checked against its card, byte for byte. "
                   "Your memory cards are exactly as they were: nothing on them was changed, renamed or deleted.</p>")
        out.append("<span class='pill'><span class='dot'>&#10003;</span>The cards are safe to format when you're ready</span>")
    out.append("</section>")
    out.append("<div class='wrap'><div class='stats'>"
               f"<div class='stat'><b>{n}</b><span class='eyebrow'>cards</span></div>"
               f"<div class='stat'><b>{total:,}</b><span class='eyebrow'>files</span></div>"
               f"<div class='stat'><b>{e(rp.human(size))}</b><span class='eyebrow'>copied</span></div>"
               f"<div class='stat'><b>{ok:,}</b><span class='eyebrow'>checked byte for byte</span></div>"
               "</div></div>")   # how long each card took is on its own section; four numbers fit one row
    # a list of the cards, then one section per card: its own report in a frame
    out.append("<div class='wrap'><nav class='cards-nav'>" + "".join(
        f"<a href='#card-{int(c['card'])}'>Card {int(c['card'])}<small>{e(f['words']) if f else 'not found'}</small></a>" for c, f in rows) + "</nav></div>")
    for c, f in rows:
        k = int(c["card"])
        if f:
            verdict = ("Needs you" if f["problems"] else "Not finished" if not f["all_good"] else "A sample, not a backup" if f["sample"] else "Safe and verified")
            cls = "bad" if f["problems"] else "wait" if (not f["all_good"] or f["sample"]) else ""
            out.append(f"<section class='wrap card-block' id='card-{k}'><div class='card-strip'><span class='eyebrow'>Card {k} of {n}</span>"
                       f"<h2>{e(f['words'])}</h2><span class='pill small {cls}'>{e(verdict)}</span></div>"
                       f"<iframe class='card-frame' src='card/{k}/{CARD_PAGE}' title='Card {k}' scrolling='no'></iframe></section>")
        else:
            out.append(f"<section class='wrap card-block' id='card-{k}'><div class='card-strip'><span class='eyebrow'>Card {k} of {n}</span>"
                       f"<h2>{e(c.get('name') or 'This card')}</h2><span class='pill small wait'>Not found right now</span></div>"
                       "<p class='also'>Its records aren't where they were. Is the drive plugged in?</p></section>")
    out.append("<footer class='foot'><div class='wrap'>Your memory cards are exactly as they were.</div>"
               f"<div class='wordmark'>{e(brand.name())}</div></footer>")
    out.append(FRAMES_SCRIPT + rp.REFRESH_SCRIPT + "</body></html>")
    return "\n".join(out)


CSS = """
.cards-nav{display:flex;gap:.6rem;flex-wrap:wrap;margin:1.2rem 0 .4rem}
.cards-nav a{display:flex;flex-direction:column;gap:.1rem;padding:.55rem .9rem;border:1px solid var(--line);border-radius:12px;text-decoration:none;color:var(--ink);font-weight:600;background:var(--panel,#fff)}
.cards-nav a small{font-weight:400;color:var(--soft,#6b7280);font-size:.82rem}
.card-block{margin-top:2.2rem;padding-top:1.4rem;border-top:1px solid var(--line)}
.card-strip{display:flex;align-items:center;gap:1rem;flex-wrap:wrap;margin-bottom:.4rem}
.card-strip h2{margin:0;font:600 1.25rem/1.2 var(--sans)}
.pill.small{font-size:.8rem;padding:.3rem .7rem}
.card-frame{display:block;width:100%;border:0;height:60vh;background:transparent}
"""

# Each card's frame is sized to the page inside it (same origin, so its height can be read), and again whenever
# that page changes (a calendar opens, a photo is enlarged, the page reloads itself).
FRAMES_SCRIPT = """
<script>
(function(){
  var frames=document.querySelectorAll('iframe.card-frame');
  function fit(fr){try{var d=fr.contentDocument;if(!d||!d.documentElement)return;var h=d.documentElement.scrollHeight;if(h>80&&Math.abs(h-fr.offsetHeight)>2)fr.style.height=h+'px';}catch(e){}}
  frames.forEach(function(fr){fr.addEventListener('load',function(){fit(fr);setTimeout(function(){fit(fr)},300);});});
  setInterval(function(){frames.forEach(fit)},500);
})();
</script>
"""


def write_pages(studio):
    """The shoot's page, written into every card's records that can be found (so the server of any card serves it).
    Returns the pages written, [] when this card is not part of a shoot."""
    data = read(studio)
    if not data:
        return []
    page = build(data)
    written = []
    for c in data["cards"]:
        if c.get("found"):
            try:
                write_whole(Path(c["found"]) / PAGE, page)
                written.append(Path(c["found"]) / PAGE)
            except OSError:
                pass
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    lk = sub.add_parser("link"); lk.add_argument("backups", nargs="+"); lk.add_argument("--shoot", default=None)
    sub.add_parser("build").add_argument("backup")
    sub.add_parser("show").add_argument("backup")
    a = ap.parse_args()
    if a.cmd == "link":
        return link(a.backups, a.shoot)
    rec = records_of(a.backup)
    if not rec:
        say(f"STOP: no backup records found for {a.backup}")
        return 1
    if a.cmd == "show":
        data = read(rec)
        say(json.dumps(data, indent=1, ensure_ascii=False) if data else "Not part of a shoot of several cards.")
        return 0 if data else 2
    pages = write_pages(rec)
    if not pages:
        say("Nothing to do: this backup is not one card of a shoot (link it first).")
        return 2
    for p in pages:
        say(str(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
