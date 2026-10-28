#!/usr/bin/env python3
"""Turn a session's _studio/manifest.json into a page the photographer can look at:
_studio/report.html. One file, no account; opens in the Claude desktop app or
any browser. Problems first, then the good news, then a few teasers from the
shoot itself (from _studio/previews/, picked in _studio/teasers.json).

The look follows the Studio sales-page mock-up ("Fresh": cream desk, coral
accent, Fraunces + DM Sans, rounded cards, a few things tilted). Fonts load
from Google when there is internet and fall back to Georgia / the system font
when there is not; the page works either way.

Run on its own:  python3 report_page.py "<session folder>"
backup.py calls write_page() at the end of every run.
"""
import html
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

MEDIA = {".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf", ".rw2", ".jpg", ".jpeg", ".heic", ".png", ".tif", ".tiff",
         ".mov", ".mp4", ".mxf", ".avi"}

FONTS = ("https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600"
         "&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;1,9..144,300;1,9..144,400&display=swap")

CSS = """
:root{--cream:#FAFAF6;--paper:#FFFFFF;--ink:#1F2430;--ink-2:#646B78;--ink-deep:#2F6F6B;
--coral:#F07F5A;--coral-2:#D4643F;--ocean:#5EB5A9;--ocean-l:#DCEFEA;--sun:#F2CF72;--sun-l:#FBF2D6;--sand-l:#ECEAF6;--lime:#CDE9D6;
--line:rgba(31,36,48,.12);--shadow:0 30px 60px -30px rgba(31,36,48,.35);
--display:'Fraunces',Georgia,serif;--sans:'DM Sans','Helvetica Neue',Arial,sans-serif;--r:30px;--ease:cubic-bezier(.2,.7,.2,1);
color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:var(--cream);color:var(--ink);font:400 16px/1.6 var(--sans);-webkit-font-smoothing:antialiased}
img{max-width:100%;display:block}h1,h2,h3,p{margin:0}
.wrap{max-width:1100px;margin:0 auto;padding:0 clamp(16px,3vw,32px)}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:baseline;gap:.6rem;white-space:nowrap}
.brand b{font:600 16px/1 var(--sans);letter-spacing:-.01em}
.brand small{font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.bar .when{margin-left:auto;font:500 13px/1 var(--sans);color:var(--ink-2);white-space:nowrap}
.bar .nav{display:inline-flex;align-items:center;gap:.8rem;font:600 16px/1 var(--sans);color:#fff;text-decoration:none;padding:.5rem .5rem .5rem 1.3rem;border-radius:999px;background:var(--coral);border:1.5px solid var(--coral);white-space:nowrap;box-shadow:0 14px 28px -18px rgba(240,127,90,.9);transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
.bar .nav .arr{width:34px;height:34px;border-radius:50%;background:var(--paper);color:var(--coral);display:grid;place-items:center;font-size:15px;transition:transform .35s var(--ease)}
.bar .nav:hover{transform:translateY(-2px);box-shadow:var(--shadow)}.bar .nav:hover .arr{transform:translate(2px,-2px)}
@media(max-width:600px){.bar .nav{font-size:14px;padding-left:1rem}}
.eyebrow{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.h1{font:600 clamp(36px,5.4vw,64px)/1.02 var(--sans);letter-spacing:-.035em;text-wrap:balance;max-width:14em}
.h1.bad{max-width:16em}
.swap{font:italic 400 1.14em/1 var(--display);color:var(--ink);text-decoration:underline wavy var(--coral);text-decoration-thickness:.06em;text-underline-offset:.1em;letter-spacing:0}
.lede{font-size:clamp(16px,1.4vw,19px);color:var(--ink-2);max-width:36em;text-wrap:pretty}
.hero{display:grid;gap:1.2rem;padding:clamp(2.2rem,5vw,4rem) 0 clamp(1.6rem,3vw,2.4rem)}
.pill{display:inline-flex;align-items:center;gap:.7rem;padding:.4rem .4rem .4rem 1.1rem;border-radius:999px;font:500 14px/1 var(--sans);background:var(--paper);border:1.5px solid var(--ink);white-space:nowrap;width:max-content}
.pill .dot{width:30px;height:30px;border-radius:50%;background:var(--lime);display:grid;place-items:center;flex:none;color:var(--ink)}
.pill.bad{background:var(--coral);border-color:var(--coral);color:#fff}.pill.bad .dot{background:var(--paper);color:var(--coral)}
.pill.wait{background:var(--sun-l);border-color:var(--sun)}.pill.wait .dot{background:var(--sun)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.stat{padding:1.5rem 1.2rem;border-left:1px solid var(--line)}.stat:first-child{border-left:0}
.stat b{display:block;font:600 clamp(34px,4.2vw,54px)/1 var(--sans);letter-spacing:-.04em;font-variant-numeric:tabular-nums}
.stat span{display:block;margin-top:.6rem}
.problems{background:var(--coral);color:#fff;border-radius:var(--r);padding:clamp(1.4rem,3vw,2.2rem);display:grid;gap:.8rem;margin-top:1.4rem}
.problems .eyebrow{color:#fff;opacity:.85}.problems h2{font:600 clamp(22px,2.4vw,30px)/1.15 var(--sans);letter-spacing:-.02em}
.problems ul{margin:0;padding-left:1.2rem;display:grid;gap:.4rem;font-size:16px}.problems p{opacity:.92}
.teasers{position:relative;display:grid;grid-template-columns:repeat(6,1fr);gap:clamp(.6rem,1.6vw,1.2rem);padding:clamp(2.4rem,5vw,3.6rem) 0 clamp(1.8rem,3vw,2.6rem);align-items:end}
.teasers .ph{border-radius:22px;overflow:hidden;aspect-ratio:4/5;background:var(--sand-l);transform:rotate(var(--rot,0deg));transition:transform .6s var(--ease),box-shadow .6s var(--ease)}
.teasers .ph:hover{transform:rotate(0) translateY(-8px);box-shadow:var(--shadow)}
.teasers .ph img{width:100%;height:100%;object-fit:cover}
.teasers .ph:nth-child(2n){margin-bottom:1.6rem}
.chip{position:absolute;padding:.55rem 1rem;border-radius:999px;font:500 13px/1 var(--sans);color:var(--ink);border:3px solid var(--paper);box-shadow:0 12px 26px -12px rgba(31,36,48,.4);transform:rotate(var(--rot,0deg));z-index:2}
.f-sun{background:var(--sun-l)}.f-ocean{background:var(--ocean-l)}.f-lime{background:var(--lime)}.f-sand{background:var(--sand-l)}.f-paper{background:var(--paper)}
.teaser-note{font-size:13px;color:var(--ink-2);margin-top:-.6rem}
.peeks{padding:clamp(1.6rem,3vw,2.4rem) 0 .4rem}
.peeks .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:clamp(.6rem,1.6vw,1.1rem);margin-top:1rem;align-items:end}
.peeks .ph{border-radius:18px;overflow:hidden;aspect-ratio:4/5;background:var(--sand-l);transform:rotate(var(--rot,0deg));transition:transform .6s var(--ease),box-shadow .6s var(--ease);position:relative}
.peeks .ph:hover{transform:rotate(0) translateY(-6px);box-shadow:var(--shadow)}
.peeks .ph img{width:100%;height:100%;object-fit:cover;display:block}
.peeks .ph small{position:absolute;left:.6rem;bottom:.5rem;font-size:11px;color:#fff;background:rgba(0,0,0,.42);padding:.15rem .5rem;border-radius:999px;backdrop-filter:blur(4px)}
.peeks .lede{margin-top:.4rem}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:1.25rem;padding:1rem 0 clamp(2.5rem,5vw,4rem)}
.where-card{justify-content:center}
.where-card .path{font:400 14px/1.45 var(--sans);color:var(--ink-2);word-break:break-all;background:var(--paper);border-radius:14px;padding:.75rem .9rem}
a.go{display:inline-flex;align-items:center;gap:.9rem;align-self:flex-start;padding:.5rem .5rem .5rem 1.4rem;border-radius:999px;background:var(--coral);color:#fff;font:500 17px/1 var(--sans);text-decoration:none;border:1.5px solid var(--coral);transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
a.go:hover{transform:translateY(-2px);box-shadow:var(--shadow)}
a.go .arr{width:38px;height:38px;border-radius:50%;background:var(--paper);color:var(--coral);display:grid;place-items:center;font-size:17px;transition:transform .35s var(--ease)}
a.go:hover .arr{transform:translate(2px,-2px)}
.where-card .also{font-size:13px;color:var(--ink-2);word-break:break-all}
.card{border-radius:var(--r);padding:1.6rem;background:var(--paper);display:flex;flex-direction:column;gap:.8rem;min-height:220px}
.card h3{font:600 20px/1.25 var(--sans);letter-spacing:-.015em}
.card p{color:var(--ink-2);font-size:15px}.card p b{color:var(--ink);font-weight:600}
.bar-k{display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--sand-l)}.bar-k span{display:block;height:100%}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--ink-2);font-size:13.5px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.row{display:grid;gap:.15rem;padding:.7rem 0;border-top:1px solid var(--line)}.row:first-of-type{border-top:0;padding-top:0}
.row b{font-size:13px;font-weight:600}.row span{color:var(--ink-2);font-size:14px;word-break:break-all}
.card.f-lime p,.card.f-sun p{color:var(--ink)}
.big-ok{font:400 clamp(26px,2.6vw,34px)/1.1 var(--display);text-wrap:balance}
.foot{background:var(--ink);color:var(--cream);overflow:hidden;margin-top:1rem}
.foot .wrap{padding-top:2rem;font-size:14px;text-align:center;opacity:.9}
.wordmark{font:400 clamp(44px,11vw,160px)/.78 var(--display);letter-spacing:-.03em;white-space:nowrap;text-transform:uppercase;text-align:center;margin:1.2rem 0 -.22em;color:var(--coral)}
@media(max-width:900px){.stats{grid-template-columns:1fr 1fr}.stat:nth-child(3){border-left:0}.stat:nth-child(n+3){border-top:1px solid var(--line)}
.teasers{grid-template-columns:repeat(3,1fr)}.cards{grid-template-columns:1fr}}
@media(max-width:600px){.teasers{grid-template-columns:repeat(2,1fr)}.bar .when{display:none}}
"""

sys.path.insert(0, str(Path(__file__).resolve().parent))
from first_look import CSS as SHOOTS_CSS, shoots_section  # noqa: E402

PALETTE = ["#F07F5A", "#5EB5A9", "#F2CF72", "#9C8BD6", "#2F6F6B", "#CDE9D6"]
ROTS = [-3, 2, -1.5, 2.5, -2, 1.5]


def human(n):
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024


def nice_time(iso):
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%A, %B %-d · %-I:%M %p").replace("AM", "am").replace("PM", "pm")
    except (TypeError, ValueError):
        return ""


def seconds_text(s):
    if s < 90:
        return f"{s:.0f} sec"
    if s < 5400:
        return f"{s / 60:.0f} min"
    return f"{s / 3600:.1f} hrs"


def duration(start, end):
    try:
        return seconds_text((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds())
    except (TypeError, ValueError):
        return ""


def sort_aside(studio):
    """Files the sorter set aside in _studio/from-the-card (camera housekeeping, undated files)."""
    p = studio / "sort-log.json"
    if not p.exists():
        return []
    try:
        return [a["from"] for a in json.loads(p.read_text()).get("set_aside", [])]
    except (ValueError, OSError):
        return []


def index_facts(studio):
    """When it was taken and on what, from index.json, in plain words."""
    p = studio / "index.json"
    if not p.exists():
        return None
    try:
        ix = json.loads(p.read_text())
    except (ValueError, OSError):
        return None
    if not ix.get("first"):
        return None

    def day(iso):
        return datetime.fromisoformat(iso).strftime("%b %-d, %Y")

    def clock(iso):
        return datetime.fromisoformat(iso).strftime("%-I:%M %p").replace("AM", "am").replace("PM", "pm")

    first, last = ix["first"], ix["last"]
    if first[:10] == last[:10]:
        span = f"{day(first)}, {clock(first)} to {clock(last)}"
    else:
        span = f"{day(first)} to {day(last)}"
    ndays = len(ix.get("days", {}))
    days = f" · {ndays} days of shooting" if ndays > 1 else ""
    cams = ix.get("cameras", {})
    bodies = ix.get("bodies", 0)
    cam_text = ", ".join(f"{c} ({n:,})" for c, n in cams.items()) if len(cams) > 1 else next(iter(cams), "")
    if bodies > 1:
        cam_text += f" · {bodies} camera bodies"
    return {"span": span, "days": days, "cameras": cam_text}


def teasers(studio):
    """Up to six previews: the ones picked in teasers.json if it exists, else an even spread."""
    folder = studio / "previews"
    if not folder.is_dir():
        return [], ""
    picks, note = [], ""
    tj = studio / "teasers.json"
    if tj.exists():
        try:
            d = json.loads(tj.read_text())
            picks = [folder / f for f in d.get("files", []) if (folder / f).exists()]
            note = d.get("picked_by", "")
        except (ValueError, OSError):
            picks = []
    if not picks:
        allp = sorted(p for p in folder.glob("*.jpg"))
        if len(allp) > 6:
            step = (len(allp) - 1) / 5
            allp = [allp[round(i * step)] for i in range(6)]
        picks, note = allp, "evenly across the shoot; the good ones get chosen later"
    return picks[:6], note


def sneak_peeks(studio):
    """The sneak peeks for the top of the report: [(preview path, shoot name or '')], and who picked them."""
    folder = studio / "sneak-peeks"
    pj = studio / "sneak-peeks.json"
    if not pj.exists() and (studio / "picks.json").exists():
        pj = studio / "picks.json"
    if not pj.exists() or not folder.is_dir():
        return [], ""
    try:
        d = json.loads(pj.read_text())
    except (ValueError, OSError):
        return [], ""
    names = {}
    try:
        if (studio / "shoots.json").exists():
            given = json.loads((studio / "names.json").read_text()) if (studio / "names.json").exists() else {}
            for sh in json.loads((studio / "shoots.json").read_text())["shoots"]:
                names[sh["id"]] = given.get(sh["id"]) or sh.get("name") or sh.get("suggested", "")
    except (ValueError, OSError, KeyError):
        pass
    out = []
    for pk in d.get("picks", []):
        pv = folder / (Path(pk["file"]).stem + ".jpg")
        if pv.exists():
            out.append((pv, names.get(pk.get("shoot", ""), "")))
    return out, d.get("picked_by", "")


def build(manifest, studio):
    files = manifest.get("files", {})
    total = len(files)
    total_bytes = sum(e.get("size", 0) for e in files.values() if e.get("size", 0) > 0)
    ok_dest = sum(1 for e in files.values() if e.get("dest", {}).get("ok"))
    second = manifest.get("second")
    ok_second = sum(1 for e in files.values() if e.get("second", {}).get("ok")) if second else None
    problems = manifest.get("problems") or []
    kinds = Counter(Path(k).suffix.lower().lstrip(".") or "other" for k in files)
    media = sum(n for k, n in kinds.items() if f".{k}" in MEDIA)
    skipped = manifest.get("skipped_system_files", 0)
    session = manifest.get("session", "Session")
    name = session.split(" ", 1)[1] if session[:10].count("-") == 2 and " " in session else session
    finished = manifest.get("finished")
    work = manifest.get("work_seconds")
    took = seconds_text(work) if work else duration(manifest.get("started"), finished)
    all_good = not problems and ok_dest == total and (ok_second == total if second else True)
    pics, pick_note = teasers(studio)
    peeks, _ = sneak_peeks(studio)
    e = html.escape

    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
           f"<title>{e(name)} · The Studio</title><link rel='stylesheet' href='{FONTS}'><style>{CSS}{SHOOTS_CSS}</style></head><body>",
           "<div class='wrap'><div class='bar'><span class='brand'><b>The Studio</b><small>by Horizon Found</small></span>",
           f"<span class='when'>{e(nice_time(finished)) if finished else 'Still running'}</span>"
           + "</div></div>"]

    # hero: the one line they need
    out.append("<section class='wrap hero'>")
    out.append(f"<span class='eyebrow'>Backup report · {e(name)}</span>")
    if problems:
        out.append(f"<h1 class='h1 bad'>Something needs you before this is <span class='swap'>safe.</span></h1>")
        out.append(f"<p class='lede'>{ok_dest:,} of {total:,} files are copied and checked. Nothing on the memory card has been changed; "
                   "fix what's below, run it again, and it picks up where it left off.</p>")
        out.append("<span class='pill bad'><span class='dot'>!</span>Not finished</span>")
        out.append("<div class='problems'><span class='eyebrow'>Needs you first</span><h2>What stopped it</h2><ul>"
                   + "".join(f"<li>{e(p)}</li>" for p in problems) + "</ul></div>")
    elif all_good:
        where = "your drive and your second copy" if second else "your drive"
        out.append(f"<h1 class='h1'>All {total:,} files, safely backed up and <span class='swap'>verified.</span></h1>")
        out.append(f"<p class='lede'>Every one was checked against the card, byte for byte. They're on {where}. "
                   "Nothing deleted, nothing moved, nothing posted.</p>")
        out.append("<span class='pill'><span class='dot'>&#10003;</span>The card is safe to format when you're ready</span>")
    else:
        out.append(f"<h1 class='h1'>Not finished <span class='swap'>yet.</span></h1>")
        out.append(f"<p class='lede'>{ok_dest:,} of {total:,} files are copied and checked so far. Run it again to continue.</p>")
        out.append("<span class='pill wait'><span class='dot'>…</span>Keep the card for now</span>")
    out.append("</section>")

    # the numbers
    out.append("<div class='wrap'><div class='stats'>"
               f"<div class='stat'><b>{total:,}</b><span class='eyebrow'>files</span></div>"
               f"<div class='stat'><b>{e(human(total_bytes))}</b><span class='eyebrow'>copied</span></div>"
               f"<div class='stat'><b>{ok_dest:,}</b><span class='eyebrow'>checked byte for byte</span></div>"
               f"<div class='stat'><b>{e(took) or '—'}</b><span class='eyebrow'>to finish</span></div>"
               "</div></div>")

    # the sneak peeks: the first thing worth looking at, picked for variety and flow
    if peeks:
        many_shoots = len({sh for _, sh in peeks if sh}) > 1
        out.append("<section class='wrap peeks'><span class='eyebrow'>Sneak peeks</span>"
                   f"<h2 class='h2'>{len(peeks)} to edit <span class='swap'>first.</span></h2>"
                   "<p class='lede'>Picked for variety and flow, so they look good together. In Lightroom they're one filter away: "
                   "the keyword “sneak peek”, or one star. Edit these, send a few to your client with a note, and the rest can wait.</p>"
                   "<div class='grid'>")
        for i, (pv, sh) in enumerate(peeks):
            out.append(f"<div class='ph' style='--rot:{ROTS[i % len(ROTS)]}deg'><img src='sneak-peeks/{e(pv.name)}' alt=''>"
                       + (f"<small>{e(sh)}</small>" if sh and many_shoots else "") + "</div>")
        out.append("</div></section>")

    # the shoots, with their previews, recaps and name boxes (one page, not two)
    shoots_html, shoots_script = (shoots_section(studio) or (None, ""))
    if shoots_html:
        out.append(shoots_html)
    # with no shoots decided yet (and no sneak peeks), a few teasers from the card instead
    elif pics and not peeks:
        out.append("<div class='wrap'><div class='teasers'>")
        for i, p in enumerate(pics):
            out.append(f"<div class='ph' style='--rot:{ROTS[i % len(ROTS)]}deg'><img src='previews/{e(p.name)}' alt=''></div>")
        chips = [("f-sun", "-6deg", "top:1.2rem;left:-.4rem", f"{media:,} photos"),
                 ("f-ocean", "5deg", "top:.6rem;right:-.2rem", "a few from the shoot"),
                 ("f-lime", "-4deg", "bottom:.8rem;right:12%", "safe to format" if all_good else "keep the card")]
        for cls, rot, pos, text in chips:
            out.append(f"<span class='chip {cls}' style='--rot:{rot};{pos}'>{e(text)}</span>")
        out.append("</div>")
        if pick_note:
            out.append(f"<p class='teaser-note'>Teasers picked {e(pick_note)}.</p>")
        out.append("</div>")

    # the details
    out.append("<div class='wrap'><div class='cards'>")
    out.append("<div class='card'><span class='eyebrow'>What's on it</span>"
               f"<h3>{media:,} photos or clips</h3>")
    if total:
        parts = kinds.most_common()
        out.append("<div class='bar-k'>" + "".join(
            f"<span style='width:{100 * n / total:.2f}%;background:{PALETTE[i % len(PALETTE)]}' title='{e(k)}: {n:,}'></span>"
            for i, (k, n) in enumerate(parts)) + "</div>")
        out.append("<div class='legend'>" + "".join(
            f"<span><i style='background:{PALETTE[i % len(PALETTE)]}'></i>{n:,} .{e(k)}</span>" for i, (k, n) in enumerate(parts)) + "</div>")
    ix = index_facts(studio)
    if ix:
        out.append(f"<p>Taken: <b>{e(ix['span'])}</b>{e(ix['days'])}</p>")
        out.append(f"<p>{e(ix['cameras'])}</p>")
    else:
        out.append("<p>Taken: dates will show here once the index is built.</p>")
    if skipped:
        out.append(f"<p>{skipped} hidden Mac system file{'s' if skipped != 1 else ''} left behind, as they should be.</p>")
    aside = sort_aside(studio)
    if aside:
        out.append(f"<p>{len(aside)} file{'s' if len(aside) != 1 else ''} that aren't photos "
                   f"({', '.join(sorted({Path(a).suffix.lower().lstrip('.') for a in aside}))}) set aside, not deleted.</p>")
    out.append("</div>")

    def photos_folder(root):
        """The folder the photos actually sit in (e.g. .../DCIM/100EOSR5), not the top of the drive."""
        if not root:
            return root
        # after the sorter has run, index.json carries the new paths; before it, the manifest's card layout
        paths = list(files)
        ixp = studio / "index.json"
        if ixp.exists():
            try:
                paths = [p["file"] for p in json.loads(ixp.read_text()).get("photos", [])] or paths
            except (ValueError, OSError):
                pass
        parents = {Path(k).parent for k in paths if Path(k).suffix.lower() in MEDIA}
        if not parents:
            return root
        common = Path(*os.path.commonprefix([list(p.parts) for p in parents])) if len(parents) > 1 else parents.pop()
        return str(Path(root) / common) if str(common) not in (".", "") else root

    # one card, one button: where the photos ended up, and a way to go there.
    # Opens the folder in Finder: from Safari on its own, or via serve_report.py inside the app.
    where = photos_folder(manifest.get("dest", ""))
    url = Path(where).as_uri() + "/" if where else ""
    out.append("<div class='card f-sand where-card'><span class='eyebrow'>Where your photos are</span>")
    out.append(f"<p class='path'>{e(where)}</p>")
    if url:
        out.append(f"<a class='go where' href='{e(url)}' title='Open this folder in Finder'>Take me to the photos"
                   "<span class='arr'>&#8599;</span></a>")
    if second:
        tail = "" if ok_second == total else f" ({ok_second:,} of {total:,} checked)"
        out.append(f"<p class='also'>Second copy{e(tail)}: {e(photos_folder(second))}</p>")
    if not all_good:
        out.append("<p class='also'>Nothing on the memory card was changed. Keep it until this report says every file is checked.</p>")
    out.append("</div>")
    out.append("</div></div>")

    out.append("<footer class='foot'><div class='wrap'>Nothing deleted, nothing moved, nothing posted.</div>"
               "<div class='wordmark'>The Studio</div></footer>")
    # Served from localhost (inside the Claude app), a page may not open file:// links itself,
    # so ask serve_report.py to open the folder in Finder. Opened as a file in Safari, the links work as they are.
    out.append("<script>if(location.protocol.startsWith('http')){let last=0;for(const a of document.querySelectorAll('a.where')){"
               "a.addEventListener('click',ev=>{ev.preventDefault();ev.stopPropagation();const now=Date.now();if(now-last<800)return;last=now;"
               "const p=decodeURIComponent(a.getAttribute('href').replace(/^file:\\/\\//,'').replace(/\\/$/,''));"
               "fetch('/open?path='+encodeURIComponent(p)).catch(()=>{});});}}</script>")
    out.append(shoots_script + "</body></html>")
    return "\n".join(out)


def write_page(session_dir):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from where import locate
    _, studio = locate(session_dir)
    manifest = json.loads((studio / "manifest.json").read_text())
    page = studio / "report.html"
    page.write_text(build(manifest, studio))
    return page


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: report_page.py <session folder>")
    print(write_page(sys.argv[1]))
