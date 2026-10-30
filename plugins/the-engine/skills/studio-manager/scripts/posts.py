#!/usr/bin/env python3
"""The home for social media content, and the drop box that feeds it.

The Studio makes one folder for them (asked once at setup, remembered in the Studio File):

    The Studio/
      Drop a shoot here/      empty, waiting. Drag any folder of finished photos in.
      Content/                one folder per shoot, dated and named, each a post kit

A drop can be anything: one tidy shoot, three shoots in one folder, a year of chaos.
`look` reads the photos' capture times (nothing is opened by Claude), splits them into
groups by day and by the gaps between photos, pulls a few previews per group and draws one
contact sheet, and prints what it sees in plain words with the one question to ask.
`sort` then moves the photos into Content under proper names: each group its own shoot,
or everything as one, or just one of them. Moved, never copied, never deleted; the drop
box is empty again afterwards. Log first; safe to run twice; a cut-off sort is finished
by the next run. Anything that is not a finished photo (RAW files, videos, catalogs,
undated screenshots) is left in the drop box and named in the summary, unless told where
it goes.

    python3 posts.py places                         where the home could go, to pick from
    python3 posts.py setup --where "/Volumes/Big Kahuna"      makes The Studio there and remembers it
    python3 posts.py setup --home "/Users/me/Pictures/The Studio"   an exact spot instead
    python3 posts.py show                           where things are, what's waiting, what's in Content
    python3 posts.py look [--gap 120]               read the drop box; the summary, the question, the sheet
    python3 posts.py sort --separate [g01=Beach g02+g03=Wedding]    one shoot per group (merge with +);
                                                     groups not named get a date name
    python3 posts.py sort --one "Spring favorites"  everything as one shoot
    python3 posts.py sort --only g01=Beach           just that one; the rest stay in the drop box
         --undated g01 | own "<name>" | leave        where photos with no date go (default: leave)
         --dry-run                                   the plan only
    python3 posts.py list                           the shoots in Content, newest first

Records: <home>/.studio/drop/ (look.json, previews, sheet.png) and <home>/.studio/drop-log.json;
each shoot folder carries .kit/kit.json. Exit: 0 done, 1 problem, 2 nothing to do or no home,
6 a name clash (nothing moved).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exif_read  # noqa: E402
import groups as groups_mod  # noqa: E402
import sheet  # noqa: E402
import studio_file  # noqa: E402

DROP_NAME = "Drop a shoot here"
CONTENT_NAME = "Content"
HOME_NAME = "The Studio"
PHOTO = {".jpg", ".jpeg", ".heic", ".png", ".tif", ".tiff", ".webp"}
RAW = {".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw"}
VIDEO = {".mp4", ".mov", ".m4v", ".avi"}
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
LIBRARY_SUFFIX = {".lrcat", ".lrdata", ".lrcat-data", ".photoslibrary", ".cocatalog", ".cocatalogdb"}


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


# ---------- the home ----------

def home():
    """The Studio folder, from the Studio File. None if never set up."""
    p = studio_file.load().get("posts", {}).get("home")
    return Path(p) if p else None


def places():
    """Where the home could go: the session drive first, then other drives, then Pictures."""
    sf = studio_file.load()
    out, seen = [], set()
    sess = sf.get("drives", {}).get("session")
    if sess and Path(sess).is_dir():
        out.append({"path": sess, "name": Path(sess).name, "why": "the drive your photos are on", "recommended": True})
        seen.add(sess)
    for d in studio_file.drives():
        if d["path"] not in seen:
            out.append({"path": d["path"], "name": d["name"], "why": f"{d['free_gb']} GB free", "recommended": False})
            seen.add(d["path"])
    pics = Path.home() / "Pictures"
    if pics.is_dir():
        out.append({"path": str(pics), "name": "Pictures", "why": "on this Mac", "recommended": not out})
    if out and not any(o["recommended"] for o in out):
        out[0]["recommended"] = True
    return out


def hide(p):
    if sys.platform == "darwin":
        subprocess.run(["chflags", "hidden", str(p)], capture_output=True)


def setup(where=None, home_path=None):
    h = Path(home_path) if home_path else Path(where) / HOME_NAME
    if not h.parent.is_dir():
        raise SystemExit(f"STOP: {h.parent} isn't a folder I can see. Nothing made.")
    for sub in (h, h / DROP_NAME, h / CONTENT_NAME, h / ".studio"):
        sub.mkdir(parents=True, exist_ok=True)
    hide(h / ".studio")
    sf = studio_file.load()
    sf["posts"] = {"home": str(h), "made": datetime.now().isoformat(timespec="seconds")}
    studio_file.save(sf)
    return h


def need_home():
    h = home()
    if not h:
        say("STOP: the Studio folder isn't set up yet. Run setup first (needs setup).")
        sys.exit(2)
    if not h.is_dir():
        say(f"STOP: the Studio folder should be at {h} but it isn't there. Is the drive plugged in?")
        sys.exit(2)
    for sub in (h / DROP_NAME, h / CONTENT_NAME, h / ".studio"):
        sub.mkdir(parents=True, exist_ok=True)
    return h


# ---------- the look ----------

def walk(top):
    """Every file under the drop box, with its path relative to it. Hidden files and libraries skipped."""
    out = []
    for root, dirs, files in os.walk(top):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and Path(d).suffix.lower() not in LIBRARY_SUFFIX)
        for f in sorted(files):
            if f.startswith(".") or f in SKIP_NAMES:
                continue
            p = Path(root) / f
            out.append(p.relative_to(top).as_posix())
    return out


def kind(rel):
    ext = Path(rel).suffix.lower()
    if ext in PHOTO:
        return "photo"
    if ext in RAW:
        return "raw"
    if ext in VIDEO:
        return "video"
    return "other"


def preview(src, dst, size=700):
    if shutil.which("sips"):
        return groups_mod.make_preview(src, dst, size)
    try:
        from PIL import Image
        im = Image.open(src)
        im.thumbnail((size, size))
        im.convert("RGB").save(dst, quality=80)
        return True
    except Exception:
        return False


def thumb_rows(src, size, tmp):
    if shutil.which("sips"):
        return sheet.thumb(src, size, tmp)
    try:
        from PIL import Image
        im = Image.open(src).convert("RGB")
        im.thumbnail((size, size))
        w, h = im.size
        raw = im.tobytes()
        return w, h, [raw[y * w * 3:(y + 1) * w * 3] for y in range(h)]
    except Exception:
        return None


def draw_sheet(studio, groups, per_row=4, size=220):
    """One contact sheet: a row per group, its id at the left, previews across."""
    tmp = studio / ".tmp.bmp"
    pad, label_w, row_h = 8, 70, size
    W = label_w + per_row * (size + pad) + pad
    H = len(groups) * (row_h + pad) + pad
    cv = sheet.Canvas(W, H)
    for i, g in enumerate(groups):
        y = pad + i * (row_h + pad)
        cv.rect(pad, y, label_w - pad, row_h, (40, 40, 40))
        cv.text(pad + 6, y + 8, g["id"][1:].lstrip("0") or "0", scale=3, color=(240, 127, 90))
        for j, pv in enumerate(g.get("previews", [])[:per_row]):
            t = thumb_rows(studio / "previews" / pv, size, tmp)
            if not t:
                continue
            w, h, rws = t
            if h > row_h:
                rws = rws[(h - row_h) // 2:(h - row_h) // 2 + row_h]
                h = row_h
            x = label_w + j * (size + pad)
            cv.paste(x + max(0, (size - w) // 2), y + max(0, (row_h - h) // 2), w, h, rws)
    out = studio / "sheet.png"
    sheet.write_png(out, W, H, cv.rows)
    if tmp.exists():
        tmp.unlink()
    return out


def day_words(iso):
    d = datetime.fromisoformat(iso)
    return d.strftime("%B %-d, %Y")


def look(h, gap_minutes=120, previews_per=4):
    drop = h / DROP_NAME
    studio = h / ".studio" / "drop"
    studio.mkdir(parents=True, exist_ok=True)
    files = walk(drop)
    if not files:
        say("The drop box is empty. Drag a folder of finished photos into \"Drop a shoot here\" and say the word.")
        return None
    top = sorted({rel.split("/")[0] for rel in files if "/" in rel})
    photos, raws, videos, others = [], [], [], []
    for rel in files:
        k = kind(rel)
        if k == "photo":
            ex = exif_read.read(drop / rel) or {}
            photos.append({"file": rel, "taken": ex.get("taken"), "camera": ex.get("camera"), "serial": ex.get("serial"), "lens": ex.get("lens")})
        elif k == "raw":
            raws.append(rel)
        elif k == "video":
            videos.append(rel)
        else:
            others.append(rel)
    groups, undated = groups_mod.find_groups(photos, gap_minutes)
    pv_dir = studio / "previews"
    if pv_dir.exists():
        shutil.rmtree(pv_dir)
    pv_dir.mkdir()
    for g in groups:
        g["previews"] = []
        g["folders"] = sorted({f.split("/")[0] for f in g["files"] if "/" in f})
        for f in groups_mod.spread(g["files"], previews_per):
            dst = pv_dir / f"{g['id']}_{Path(f).stem}.jpg"
            if preview(drop / f, dst):
                g["previews"].append(dst.name)
    sheet_path = draw_sheet(studio, groups) if groups else None
    result = {"drop": str(drop), "looked": datetime.now().isoformat(timespec="seconds"), "gap_minutes": gap_minutes,
              "top_folders": top, "photos": len(photos), "groups": groups, "undated": undated,
              "raws": raws, "videos": videos, "others": others, "sheet": str(sheet_path) if sheet_path else None}
    (studio / "look.json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
    return result


def summary(r):
    """The look in plain words, with the question. Claude reads the sheet before asking, so it can say
    'a beach session' instead of 'group 1'."""
    lines = []
    n = r["photos"]
    what = f"{n:,} photo{'s' if n != 1 else ''}"
    if r["top_folders"]:
        what += " in " + (f"\"{r['top_folders'][0]}\"" if len(r["top_folders"]) == 1 else f"{len(r['top_folders'])} folders")
    lines.append(f"I looked through the {what} you dropped in.")
    gs = r["groups"]
    days = sorted({g["start"][:10] for g in gs})
    if len(gs) == 1:
        g = gs[0]
        lines.append(f"They're all from one day, {day_words(g['start'])}, {g['count']} photos over {g['minutes']} minutes. Looks like one shoot.")
    elif gs:
        lines.append(f"They're from {len(days)} different day{'s' if len(days) != 1 else ''}, in {len(gs)} groups:")
        for g in gs:
            gap = f", {g['gap_before_min']} min after the one before" if g.get("gap_before_min") else ""
            fold = f"  (from \"{g['folders'][0]}\")" if len(g.get("folders", [])) == 1 and len(r["top_folders"]) > 1 else ""
            lines.append(f"  {g['id']}  {day_words(g['start'])}  {groups_mod.clock(g['start'])} to {groups_mod.clock(g['end'])}  {g['count']:>4} photos{gap}{fold}")
    if r["undated"]:
        lines.append(f"{len(r['undated'])} photo{'s have' if len(r['undated']) != 1 else ' has'} no date on {'them' if len(r['undated']) != 1 else 'it'} (screenshots, or saved from somewhere): they can't be placed by time.")
    side = []
    if r["raws"]:
        side.append(plural(len(r["raws"]), "RAW file"))
    if r["videos"]:
        side.append(plural(len(r["videos"]), "video"))
    if r["others"]:
        side.append(plural(len(r["others"]), "other file"))
    if side:
        lines.append("Also in there, left where they are for now: " + ", ".join(side) + ".")
    if r["sheet"]:
        lines.append(f"Contact sheet, one row per group: {r['sheet']}")
    lines.append("")
    if len(gs) > 1:
        lines.append("The question to ask, with what each group is after reading the sheet:")
        lines.append("  What did you have in mind?  [Separate them into N shoots]  [One compilation from all of it]  [Just one of them]")
    elif gs:
        lines.append("One shoot: ask only what to call it (offer the folder name or the date), then sort.")
    else:
        lines.append("Nothing with a date in there. Ask what they'd like done with these, or leave them.")
    return "\n".join(lines)


# ---------- the sort ----------

def load_look(h):
    p = h / ".studio" / "drop" / "look.json"
    if not p.exists():
        say("STOP: look first (posts.py look), then sort.")
        sys.exit(2)
    return json.loads(p.read_text())


def parse_specs(specs):
    """['g01=Beach', 'g02+g03=Wedding'] -> [(['g01'], 'Beach'), (['g02','g03'], 'Wedding')]."""
    out = []
    for s in specs or []:
        if "=" in s:
            ids, name = s.split("=", 1)
        else:
            ids, name = s, ""
        out.append(([i.strip() for i in ids.split("+") if i.strip()], name.strip()))
    return out


def folder_name(name, when):
    naming = studio_file.load().get("naming", {})
    if not naming.get("folder_pattern"):
        naming = {"folder_pattern": "{date} {shoot}", "date_format": "%Y-%m-%d"}
    return studio_file.render(naming, name, when)


def date_name(g_list):
    """A plain name for a shoot nobody named: the folder it was dropped in as, if it had one of its own,
    else just "Shoot" (the folder pattern adds the date)."""
    folders = sorted({f for g in g_list for f in g.get("folders", [])})
    if len(folders) == 1:
        n = clean_name(re.sub(r"\b(final|export|exports|edited|edits|jpegs?|jpgs?|copy|new|v\d+|\d+)\b", " ", folders[0], flags=re.I))
        if n and not re.fullmatch(r"[\W\d_]*", n):
            return n[:1].upper() + n[1:]
    return "Shoot"


def plural(n, word):
    return f"{n} {word}{'s' if n != 1 else ''}"


def clean_name(s):
    s = re.sub(r"[\\/:*?\"<>|]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s


def plan(h, r, mode, specs, one_name, undated_to):
    gs = {g["id"]: g for g in r["groups"]}
    shoots = []
    if mode == "one":
        if not r["groups"] and not (r["undated"] and undated_to == "own"):
            say("STOP: nothing with a date to sort.")
            sys.exit(2)
        if r["groups"]:
            shoots.append({"name": clean_name(one_name) or date_name(r["groups"]), "groups": [g["id"] for g in r["groups"]]})
    else:
        named = parse_specs(specs)
        used = set()
        for ids, name in named:
            bad = [i for i in ids if i not in gs]
            if bad:
                say(f"STOP: no group called {', '.join(bad)} in the last look.")
                sys.exit(1)
            shoots.append({"name": clean_name(name) or date_name([gs[i] for i in ids]), "groups": ids})
            used.update(ids)
        if mode == "separate":
            for g in r["groups"]:
                if g["id"] not in used:
                    shoots.append({"name": date_name([g]), "groups": [g["id"]]})
        elif not named:
            say("STOP: say which group (posts.py sort --only g01=Beach).")
            sys.exit(1)
    moves = []
    for s in shoots:
        files = [f for gid in s["groups"] for f in gs[gid]["files"]]
        first = min(gs[gid]["start"] for gid in s["groups"])
        s["date"] = first[:10]
        s["folder"] = folder_name(s["name"], first)
        s["photos"] = len(files)
        s["source_folders"] = sorted({f.split("/")[0] for f in files if "/" in f})
        for f in files:
            moves.append({"src": f, "dst": f"{CONTENT_NAME}/{s['folder']}/Photos/{Path(f).name}", "shoot": s["folder"]})
    if r["undated"] and undated_to and undated_to != "leave":
        if undated_to == "own":
            name = clean_name(one_name or "Undated photos")
            s = {"name": name, "groups": [], "date": datetime.now().strftime("%Y-%m-%d"), "folder": folder_name(name, datetime.now()),
                 "photos": len(r["undated"]), "source_folders": []}
            shoots.append(s)
            target = s["folder"]
        else:
            target = next((s["folder"] for s in shoots if undated_to in s["groups"]), None)
            if not target:
                say(f"STOP: --undated names {undated_to}, which isn't in this sort.")
                sys.exit(1)
        for f in r["undated"]:
            moves.append({"src": f, "dst": f"{CONTENT_NAME}/{target}/Photos/{Path(f).name}", "shoot": target})
    # two files with the same name landing in one Photos folder: keep the subfolder name in front
    seen = Counter(m["dst"] for m in moves)
    for m in moves:
        if seen[m["dst"]] > 1 and "/" in m["src"]:
            sub = m["src"].rsplit("/", 1)[0].replace("/", "_")
            m["dst"] = m["dst"].rsplit("/", 1)[0] + f"/{sub}_{Path(m['src']).name}"
    return shoots, moves


def identity(p):
    st = p.stat()
    return [st.st_ino, st.st_size, int(st.st_mtime)]


def log_path(h):
    return h / ".studio" / "drop-log.json"


def read_log(h):
    p = log_path(h)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except ValueError:
            pass
    return {"runs": []}


def write_log(h, log):
    p = log_path(h)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(log, indent=1, ensure_ascii=False))
    os.replace(tmp, p)


def finish_unfinished(h):
    """A sort cut off mid-way: do the moves that still can be done, then mark the run done."""
    log = read_log(h)
    done_any = False
    for run in log["runs"]:
        if run.get("status") != "moving":
            continue
        problems = []
        for m in run["moves"]:
            if m.get("done"):
                continue
            src, dst = h / DROP_NAME / m["src"], h / m["dst"]
            if dst.exists() and not src.exists():
                m["done"] = True  # moved just before the cut
                continue
            if not src.exists():
                problems.append(f"{m['src']} is gone from the drop box and not at its new place")
                continue
            if dst.exists():
                problems.append(f"{m['dst']} already exists; left {m['src']} in the drop box")
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.rename(src, dst)
            m["done"] = identity(dst) == m["id"]
            if not m["done"]:
                problems.append(f"{m['dst']} is not the same file after the move")
        run["problems"] = problems
        run["status"] = "problems" if problems else "done"
        write_kits(h, run)
        done_any = True
    if done_any:
        write_log(h, log)
    return done_any


def write_kits(h, run):
    for s in run["shoots"]:
        kit = h / CONTENT_NAME / s["folder"]
        if not kit.exists():
            continue
        rec = kit / ".kit"
        rec.mkdir(exist_ok=True)
        hide(rec)
        photos = sorted(p.name for p in (kit / "Photos").iterdir() if p.is_file() and not p.name.startswith(".")) if (kit / "Photos").is_dir() else []
        (rec / "kit.json").write_text(json.dumps({
            "name": s["name"], "date": s["date"], "folder": s["folder"], "source": "drop",
            "dropped_as": s.get("source_folders", []), "photos": photos, "made": run["started"]}, indent=1, ensure_ascii=False))


def tidy_drop(h):
    """Empty folders left behind go; Finder's own files are set aside, not deleted."""
    drop = h / DROP_NAME
    aside = h / ".studio" / "drop" / "set-aside"
    for root, dirs, files in os.walk(drop, topdown=False):
        rp = Path(root)
        for f in files:
            if f in SKIP_NAMES or f.startswith("._"):
                aside.mkdir(parents=True, exist_ok=True)
                dst = aside / f"{rp.relative_to(drop).as_posix().replace('/', '_')}_{f}".lstrip("._")
                try:
                    os.rename(rp / f, dst)
                except OSError:
                    pass
        if rp != drop:
            try:
                rp.rmdir()
            except OSError:
                pass


def do_sort(h, mode, specs, one_name, undated_to, dry_run):
    if finish_unfinished(h):
        say("Finished a sort that was cut off earlier.")
    r = load_look(h)
    drop = h / DROP_NAME
    shoots, moves = plan(h, r, mode, specs, one_name, undated_to)
    # everything still there, nothing in the way
    gone = [m["src"] for m in moves if not (drop / m["src"]).exists()]
    if gone:
        say(f"STOP: {len(gone)} of the photos from the last look aren't in the drop box any more (first: {gone[0]}). Look again.")
        return 1
    clashes = sorted({m["shoot"] for m in moves if (h / CONTENT_NAME / m["shoot"]).exists()})
    if clashes:
        say("STOP: there's already a folder in Content called " + " and ".join(f"\"{c}\"" for c in clashes) + ". Give this one another name; nothing was moved.")
        return 6
    say("The plan:")
    for s in shoots:
        say(f"  {s['folder']}   {s['photos']} photos")
    left = len(r["undated"]) if undated_to in (None, "leave") else 0
    stay = left + len(r["raws"]) + len(r["videos"]) + len(r["others"])
    if stay:
        say(f"  Left in the drop box: " + ", ".join(x for x in [
            plural(left, "undated photo") if left else "", plural(len(r["raws"]), "RAW file") if r["raws"] else "",
            plural(len(r["videos"]), "video") if r["videos"] else "", plural(len(r["others"]), "other file") if r["others"] else ""] if x))
    if dry_run:
        say("Dry run: nothing moved.")
        return 0
    for m in moves:
        m["id"] = identity(drop / m["src"])
    log = read_log(h)
    run = {"started": datetime.now().isoformat(timespec="seconds"), "mode": mode, "status": "moving", "shoots": shoots, "moves": moves}
    log["runs"].append(run)
    write_log(h, log)
    problems = []
    for m in moves:
        src, dst = drop / m["src"], h / m["dst"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.rename(src, dst)
        m["done"] = identity(dst) == m["id"]
        if not m["done"]:
            problems.append(f"{m['dst']} is not the same file after the move")
    run["problems"] = problems
    run["status"] = "problems" if problems else "done"
    write_log(h, log)
    write_kits(h, run)
    tidy_drop(h)
    (h / ".studio" / "drop" / "look.json").rename(h / ".studio" / "drop" / f"look-{run['started'].replace(':', '-')}.json")
    if problems:
        say("STOP: " + problems[0] + (f" (and {len(problems) - 1} more)" if len(problems) > 1 else ""))
        return 1
    n = sum(s["photos"] for s in shoots)
    say(f"Done. Moved {n} photos into Content: " + "; ".join(f"\"{s['folder']}\" ({s['photos']})" for s in shoots)
        + ". Nothing copied, nothing changed, nothing deleted." + (" The drop box still has the files set aside above." if stay else " The drop box is empty again."))
    return 0


# ---------- what's there ----------

def kits(h):
    out = []
    c = h / CONTENT_NAME
    if not c.is_dir():
        return out
    for d in sorted(c.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        rec = d / ".kit" / "kit.json"
        info = {}
        if rec.exists():
            try:
                info = json.loads(rec.read_text())
            except ValueError:
                pass
        photos = len([p for p in (d / "Photos").iterdir() if p.is_file() and not p.name.startswith(".")]) if (d / "Photos").is_dir() else 0
        out.append({"folder": d.name, "path": str(d), "name": info.get("name", d.name), "date": info.get("date"), "photos": photos,
                    "kit": (d / "Post kit.html").exists()})
    out.sort(key=lambda k: (k["date"] or "", k["folder"]), reverse=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("places")
    st = sub.add_parser("setup"); st.add_argument("--where"); st.add_argument("--home")
    sub.add_parser("show"); sub.add_parser("list")
    lk = sub.add_parser("look"); lk.add_argument("--gap", type=float, default=120); lk.add_argument("--previews", type=int, default=4)
    so = sub.add_parser("sort")
    so.add_argument("--separate", action="store_true"); so.add_argument("--one"); so.add_argument("--only", action="store_true")
    so.add_argument("specs", nargs="*"); so.add_argument("--undated", default="leave"); so.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.cmd == "places":
        for p in places():
            say(f"{'* ' if p['recommended'] else '  '}{p['name']}: {p['path']}  ({p['why']})")
        return 0
    if a.cmd == "setup":
        if not (a.where or a.home):
            say("STOP: say where (--where <a drive or folder>, or --home <the exact folder>).")
            return 1
        h = setup(a.where, a.home)
        say(f"Made \"{HOME_NAME}\" at {h}, with \"{DROP_NAME}\" and \"{CONTENT_NAME}\" inside. Remembered.")
        return 0
    if a.cmd == "show":
        h = home()
        if not h:
            say("No Studio folder yet (needs setup).")
            return 2
        say(f"The Studio folder: {h}" + ("" if h.is_dir() else "  (not there right now; drive unplugged?)"))
        if h.is_dir():
            waiting = walk(h / DROP_NAME) if (h / DROP_NAME).is_dir() else []
            say(f"Drop a shoot here: {len(waiting)} file{'s' if len(waiting) != 1 else ''} waiting" if waiting else "Drop a shoot here: empty")
            ks = kits(h)
            say(f"Content: {len(ks)} shoot{'s' if len(ks) != 1 else ''}")
        return 0
    if a.cmd == "list":
        h = need_home()
        ks = kits(h)
        if not ks:
            say("Nothing in Content yet.")
            return 2
        for k in ks:
            say(f"  {k['folder']}   {k['photos']} photos" + ("   post kit made" if k["kit"] else ""))
        return 0
    if a.cmd == "look":
        h = need_home()
        if finish_unfinished(h):
            say("Finished a sort that was cut off earlier.")
        r = look(h, a.gap, a.previews)
        if r is None:
            return 2
        say(summary(r))
        return 0
    if a.cmd == "sort":
        h = need_home()
        mode = "one" if a.one is not None else "only" if a.only else "separate" if a.separate else None
        if not mode:
            say("STOP: say how: --separate, --one \"<name>\", or --only g01=<name>.")
            return 1
        return do_sort(h, mode, a.specs, a.one, a.undated, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
