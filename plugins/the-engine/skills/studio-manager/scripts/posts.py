#!/usr/bin/env python3
"""The home for social media content, and the drop box that feeds it.

The Studio makes one folder for them (asked once at setup, remembered in the Studio File):

    The Studio/
      Drop a shoot here/      empty, waiting. Drag any folder of finished photos in.
      Your Content/           one folder per shoot, dated and named, each a post kit

A drop can be anything: one tidy shoot, three shoots in one folder, a year of chaos.
`look` reads the photos' capture times (nothing is opened by Claude), splits them into
groups by day and by the gaps between photos, pulls a few previews per group and draws one
contact sheet, and prints what it sees in plain words with the one question to ask.
`sort` then copies the photos into Your Content under proper names: each group its own shoot,
or everything as one, or just one of them. Copied and checked (a hash of every file, like the
backup), never moved, never deleted: what they dropped stays in the drop box exactly as dropped, so a
folder moved in by accident (Finder moves within one drive) can be dragged straight back. Log first; safe to run twice; a cut-off sort is finished
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
6 a name clash (nothing copied).
"""
import argparse
import errno
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exif_read  # noqa: E402
import groups as groups_mod  # noqa: E402
import sheet  # noqa: E402
import brand  # noqa: E402
import studio_file  # noqa: E402
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
import pictures  # noqa: E402  (every small picture, on a Mac or a PC)
this_computer.utf8_output()

DROP_NAME = "Drop a shoot here"
CONTENT_NAME = "Your Content"   # capital C (Dustin, Nov 5)
# Earlier names; a folder still carrying one is renamed once, in place, the first time the Assistant looks
# ("Content" until Oct 30, "Your content" until Nov 5). Nothing is copied or deleted.
OLD_CONTENT_NAMES = ("Your content", "Content")
HOME_NAME = "The Assistant"  # Nov 5. A folder already made as "The Studio" stays as it is (its path is in the Studio File).
# Only finished photos are ever copied: JPEGs, and HEIC/PNG/WebP for phone photos and screenshots.
# Everything heavy or unfinished (RAW, TIFF, Photoshop, video) stays in the drop box and is named, never copied (Dustin, Oct 30).
PHOTO = {".jpg", ".jpeg", ".heic", ".png", ".webp"}
WORKING = {".tif": "TIFF", ".tiff": "TIFF", ".psd": "Photoshop file", ".psb": "Photoshop file", ".ai": "Illustrator file",
           ".lrcat": "Lightroom catalog", ".lrdata": "Lightroom catalog", ".xmp": "edit sidecar"}
RAW = {".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw"}
VIDEO = {".mp4", ".mov", ".m4v", ".avi"}
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
LIBRARY_SUFFIX = {".lrcat", ".lrdata", ".lrcat-data", ".photoslibrary", ".cocatalog", ".cocatalogdb"}


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass
    except OSError as e:
        # A PC only (as kit.py's say): Windows reports a reader that has gone away as "invalid argument" (EINVAL),
        # not as a broken pipe, and the work goes on, as it does on a Mac. A Mac raises anything else, as before.
        if not (this_computer.WINDOWS and e.errno == errno.EINVAL):   # unproven on a real PC
            raise


# ---------- the home ----------

def rename_exact(h, old, new):
    """Rename h/old to h/new when the two may differ only in capital letters. Most drives ignore case, so
    "is it there" means the exact name is in the folder's listing, never exists() (which says yes to either
    spelling; the same trap the shoot renamer fell into on Oct 28). A plain rename changes the case on a Mac's
    drives; if the listing still shows the old spelling, go through a spare name."""
    def names():
        return set(os.listdir(h))
    if new in names() or old not in names():
        return new in names()
    try:
        (h / old).rename(h / new)
    except OSError:
        pass
    if new not in names() and old in names():
        spare = h / (new + ".renaming")
        if spare.name not in names():
            (h / old).rename(spare)
            try:
                spare.rename(h / new)
            except OSError:
                spare.rename(h / old)       # never left under the spare name (a PC refuses while a window has it open)
                raise
    return new in names()


def home():
    """The Assistant's folder, from the Studio File. None if never set up. A content folder still carrying an
    earlier name ("Content", "Your content") is renamed to "Your Content" here, once: a rename on the same
    drive, nothing copied or deleted."""
    p = studio_file.load().get("posts", {}).get("home")
    if not p:
        return None
    h = Path(p)
    try:
        if h.is_dir() and CONTENT_NAME not in os.listdir(h):
            for old in OLD_CONTENT_NAMES:
                if old in os.listdir(h) and (h / old).is_dir():
                    rename_exact(h, old, CONTENT_NAME)
                    break
    except OSError:
        pass
    return h


def current_dst(dst):
    """A place written in an older log ("Your content/Beach/Photos/a.jpg"), under today's folder name."""
    for old in OLD_CONTENT_NAMES:
        if dst.startswith(old + "/"):
            return CONTENT_NAME + dst[len(old):]
    return dst


def places():
    """Where the home could go: the session drive first, then other drives, then Pictures."""
    sf = studio_file.load()
    out, seen = [], set()
    sess = sf.get("drives", {}).get("session")
    if sess and Path(sess).is_dir():
        out.append({"path": sess, "name": Path(sess).name or drive_shown(sess), "why": "the drive your photos are on",
                    "recommended": True})
        seen.add(sess)
    for d in studio_file.drives():
        if d["path"] not in seen:
            out.append({"path": d["path"], "name": d["name"], "why": f"{d['free_gb']} GB free", "recommended": False})
            seen.add(d["path"])
    pics = this_computer.known_folder("Pictures")
    if pics.is_dir():
        out.append({"path": str(pics), "name": "Pictures", "why": f"on this {this_computer.COMPUTER}", "recommended": not out})
    if out and not any(o["recommended"] for o in out):
        out[0]["recommended"] = True
    return out


def drive_shown(path):
    """How to name the top of a drive, which has no folder name of its own: on a PC "E:\\" is "Big Kahuna (E:)",
    as `studio_file.py drives` says it. (A Mac's drives always have a name in their path, so this is not asked
    there.) The path itself when no drive matches."""
    for v in this_computer.volumes():
        if this_computer.same_place(v["path"], path):
            return v["shown"]
    return str(path)


def hide(p):
    this_computer.hide(p)


def named_place(where):
    """A drive or place given by its NAME ("G PAPA", "Pictures") is the same as its path. `posts.py places`
    lists them by name, so a name has to work here too (Nicole's first run, Nov 5: --where "G PAPA" was
    refused because only /Volumes/G PAPA is a folder). A blank name is never a place: it stops, rather than
    making the folder wherever Claude happens to be working (an empty path is "here" to Python)."""
    if not str(where or "").strip():
        raise SystemExit(f"STOP: say which drive or folder \"{HOME_NAME}\" should go on. Nothing made.")
    p = this_computer.drive_root(where).expanduser()   # a bare "E:" means the top of drive E
    if p.is_dir():
        return p
    want = str(where).strip().strip("/\\" if this_computer.WINDOWS else "/").lower()
    for o in places():
        if o["name"].lower() == want:
            return Path(o["path"])
    if not this_computer.WINDOWS:
        # A Mac, exactly as before: a drive's name, or its name and then a folder on it ("Big Kahuna/Social").
        vol = Path("/Volumes") / str(where).strip().strip("/")  # pc-ok: never reached on a PC (the branch above)
        return vol if vol.is_dir() else p
    # Unproven on a real PC. A drive's name ("Big Kahuna", "E:", "Big Kahuna (E:)"), or its name and then a
    # folder on it ("Big Kahuna\Social", "Big Kahuna/Social"). Anything else is handed back as it was given,
    # and setup stops on it in plain words.
    vol = this_computer.volume_by_name(where)
    if vol:
        return Path(vol["path"])
    first, _, rest = str(where).strip().replace("/", "\\").partition("\\")
    vol = this_computer.volume_by_name(first) if rest.strip("\\") else None
    if vol:
        inside = Path(vol["path"]) / rest.strip("\\")
        if inside.is_dir():
            return inside
    return p


def setup(where=None, home_path=None):
    h = Path(home_path) if home_path else named_place(where) / HOME_NAME
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
        say(f"STOP: the {HOME_NAME} folder isn't set up yet. Run setup first (needs setup).")
        sys.exit(2)
    if not h.is_dir():
        say(f"STOP: the {HOME_NAME} folder should be at {h} but it isn't there. Is the drive plugged in?")
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
            if f.startswith(".") or f in SKIP_NAMES or f.endswith(".studio-partial"):   # a copy of ours, not yet finished
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
    if ext in WORKING:
        return "working"
    return "other"


def preview(src, dst, size=700):
    """A small JPEG of a dropped photo: the Mac's own sips, or on a PC Pillow (pictures.py)."""
    return groups_mod.make_preview(src, dst, size)


def thumb_rows(src, size, tmp):
    """(w, h, rows) for the contact sheet: sips to BMP on a Mac, Pillow on a PC (both through sheet.thumb)."""
    return sheet.thumb(src, size, tmp)


def save_text(path, text):
    """Written whole under a scratch name, then given its name: a page reading it never sees half of it, and a
    PC that has it open for a moment is waited for (this_computer.replace)."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    this_computer.replace(tmp, path)


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
    return this_computer.strftime(d, "%B %-d, %Y")


def look(h, gap_minutes=120, previews_per=4):
    drop = h / DROP_NAME
    studio = h / ".studio" / "drop"
    studio.mkdir(parents=True, exist_ok=True)
    files = walk(drop)
    if not files:
        say("The drop box is empty. Drag a folder of finished photos into \"Drop a shoot here\" and say the word.")
        return None
    # Photos already copied into Your Content by an earlier sort (same drop path, same size, same file time)
    # are left out of the look, so a drop box nobody has cleared is not offered twice.
    already = {}
    for run in read_log(h).get("runs", []):
        if run.get("status") == "done":
            for m in run.get("moves", []):
                if m.get("done") and m.get("size") is not None:
                    already[m["src"]] = (m["size"], m.get("mtime"), m["dst"])
    done_before = []
    fresh = []
    for rel in files:
        a = already.get(rel)
        if a:
            try:
                st = (drop / rel).stat()
                if st.st_size == a[0] and int(st.st_mtime) == a[1] and (h / a[2]).exists():
                    done_before.append(rel)
                    continue
            except OSError:
                pass
        fresh.append(rel)
    files = fresh
    if not files:
        kits_named = sorted({already[r][2].split("/")[1] for r in done_before if "/" in already[r][2]})
        say(f"Everything in the drop box has already been copied into {CONTENT_NAME}" + (f" ({', '.join(kits_named)})" if kits_named else "") +
            ". Nothing new to sort. You can clear the drop box whenever you like.")
        return None
    top = sorted({rel.split("/")[0] for rel in files if "/" in rel})
    photos, raws, videos, working, others = [], [], [], [], []
    for rel in files:
        k = kind(rel)
        if k == "photo":
            ex = exif_read.read(drop / rel) or {}
            photos.append({"file": rel, "taken": ex.get("taken"), "camera": ex.get("camera"), "serial": ex.get("serial"), "lens": ex.get("lens")})
        elif k == "raw":
            raws.append(rel)
        elif k == "video":
            videos.append(rel)
        elif k == "working":
            working.append(rel)
        else:
            others.append(rel)
    groups, undated = groups_mod.find_groups(photos, gap_minutes)
    if groups:
        ok, words = pictures.ready()
        if not ok:
            say(f"STOP: {words} Nothing was copied or changed; once it is in, look again.")
            sys.exit(1)
    pv_dir = studio / "previews"
    if pv_dir.exists():
        try:
            shutil.rmtree(pv_dir)                    # our own previews from the last look, never a photo
        except OSError:                              # a PC with one of them open right now: clear what it can
            shutil.rmtree(pv_dir, ignore_errors=True)
    pv_dir.mkdir(exist_ok=True)
    unshown = {}
    for g in groups:
        g["previews"] = []
        g["folders"] = sorted({f.split("/")[0] for f in g["files"] if "/" in f})
        for f in groups_mod.spread(g["files"], previews_per):
            dst = pv_dir / f"{g['id']}_{Path(f).stem}.jpg"
            if preview(drop / f, dst):
                g["previews"].append(dst.name)
            else:
                why = pictures.why_not(drop / f)    # only ever words on a PC (an iPhone photo with no add-on)
                if why:
                    unshown[why] = unshown.get(why, 0) + 1
    sheet_path = draw_sheet(studio, groups) if groups else None
    result = {"drop": str(drop), "looked": datetime.now().isoformat(timespec="seconds"), "gap_minutes": gap_minutes,
              "top_folders": top, "photos": len(photos), "groups": groups, "undated": undated,
              "raws": raws, "videos": videos, "working": working, "others": others, "sheet": str(sheet_path) if sheet_path else None,
              "already_copied": len(done_before)}
    if unshown:
        result["not_shown"] = unshown
    save_text(studio / "look.json", json.dumps(result, indent=1, ensure_ascii=False))
    return result


def summary(r):
    """The look in plain words, with the question. Claude reads the sheet before asking, so it can say
    'a beach session' instead of 'group 1'."""
    lines = []
    n = r["photos"]
    what = f"{n:,} photo{'s' if n != 1 else ''}"
    if r["top_folders"]:
        what += " in " + (f"\"{r['top_folders'][0]}\"" if len(r["top_folders"]) == 1 else f"{len(r['top_folders'])} folders")
    lines.append(f"I looked through the {what} you dropped in." + (f" ({r['already_copied']} others in the drop box were copied into {CONTENT_NAME} earlier and are left out.)" if r.get("already_copied") else ""))
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
    by_kind = {}
    for f in r.get("working", []):
        by_kind[WORKING.get(Path(f).suffix.lower(), "working file")] = by_kind.get(WORKING.get(Path(f).suffix.lower(), "working file"), 0) + 1
    for name, n in sorted(by_kind.items()):
        side.append(plural(n, name))
    if r["videos"]:
        side.append(plural(len(r["videos"]), "video"))
    if r["others"]:
        side.append(plural(len(r["others"]), "other file"))
    if side:
        lines.append("Left where they are, not copied: " + ", ".join(side) + f". {brand.name()} only copies finished photos (JPEGs, and phone photos), so nothing big or unfinished comes along.")
    for why, n in sorted((r.get("not_shown") or {}).items()):
        lines.append(f"{plural(n, 'photo')} could not be shown on the contact sheet: {why}")
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
    return json.loads(p.read_text(encoding="utf-8"))


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


def into_place(part, dst):
    """Give a finished copy its real name, never over a file that is already there (one could appear between
    the check and the rename). True when it has the name; False when something else already had it (the copy
    is left under its partial name for the caller). On a PC a rename refuses an existing name by itself; on a
    Mac a link does (a plain rename would replace), and a drive with no links (exFAT, some network drives)
    is checked first. (The two ways live in this_computer.rename_new.)"""
    return this_computer.rename_new(part, dst)


def could_not(ex):
    """Why a copy could not be made right now, in plain words."""
    if isinstance(ex, PermissionError):
        if this_computer.WINDOWS:
            # Unproven on a real PC: a file another program holds open, or a folder that can't be written to.
            return ("another program has it open, or that folder can't be written to (close Lightroom or any "
                    f"{this_computer.FILES_APP} window showing it)")
        # A Mac never refuses because a program or a Finder window has a file open. Its usual reasons are its
        # privacy settings for the Claude app, or a locked or read-only file or drive; the Mac's own reason is kept.
        return (f"the {this_computer.COMPUTER} wouldn't let me read or write there ({ex.strerror or 'permission denied'}). "
                "If it's on the Desktop, in Documents or Downloads, or on an external drive, the Claude app may need "
                "permission in System Settings, Privacy & Security, Files & Folders")
    if getattr(ex, "errno", None) == errno.ENOSPC:
        return "the drive is full"
    return ex.strerror or str(ex)


class CopyHeld(Exception):
    """A copy that could not be made right now (a file held open, a folder that can't be written to, a full
    drive), as opposed to one that did not match. The sort stays "copying" in its log, so the next look or
    sort finishes it, as a cut-off sort always has been."""
    def __init__(self, what, ex):
        self.what, self.ex = what, ex
        super().__init__(f"{what} could not be copied: {could_not(ex)}")

    def words(self):
        return (f"STOP: {self.what} could not be copied: {could_not(self.ex)}. Nothing is lost: what's copied so far "
                "is checked, and once that's sorted, running it again finishes the job.")


def copy_move(m, src, dst, problems):
    """One copy of a sort, recorded on its move. A copy that did not match is a problem for the report; one
    that could not be made right now raises CopyHeld and the move stays not done."""
    try:
        got = copy_checked(src, dst)
    except OSError as ex:
        raise CopyHeld(m["dst"], ex)
    m["done"] = got is not None
    if m["done"]:
        m["sha256"] = got
    else:
        problems.append(f"{m['dst']} did not match the original after copying")


def copy_checked(src, dst):
    """Copy src to dst the way the backup does: hash while writing to a partial file, rename into place,
    read the copy back and compare. Returns the hash, or None if the copy did not match (the partial is removed).
    dst already there: compared, never replaced; returns its hash if it matches src, else None."""
    import hashlib
    def sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    want = sha(src)
    if dst.exists():
        return want if sha(dst) == want else None
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_name(dst.name + ".studio-partial")
    h = hashlib.sha256()
    try:
        with open(src, "rb") as f, open(part, "wb") as out:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
                out.write(chunk)
    except OSError:
        try:
            part.unlink()                        # our own half-made copy (a full drive); the original is untouched
        except OSError:
            pass
        raise
    if h.hexdigest() != want:
        part.unlink(missing_ok=True)
        return None
    shutil.copystat(src, part)
    try:
        placed = into_place(part, dst)
    except OSError:
        try:
            part.unlink()                        # our own copy under its partial name; the next run makes it again
        except OSError:
            pass
        raise
    if not placed:                               # something took the name meanwhile: compared, never replaced
        part.unlink(missing_ok=True)
        return want if sha(dst) == want else None
    if sha(dst) != want:
        return None
    return want


def log_path(h):
    return h / ".studio" / "drop-log.json"


def read_log(h):
    p = log_path(h)
    if p.exists():
        try:
            log = json.loads(p.read_text(encoding="utf-8"))
            for run in log.get("runs", []):          # older logs name the content folder as it was called then
                for m in run.get("moves", []):
                    if isinstance(m.get("dst"), str):
                        m["dst"] = current_dst(m["dst"])
            return log
        except ValueError:
            pass
    return {"runs": []}


def write_log(h, log):
    p = log_path(h)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    this_computer.replace(tmp, p)


def finish_unfinished(h):
    """A sort cut off mid-way: do the copies that still can be done, then mark the run done. Returns the runs
    it finished (empty when there were none). A copy that still can't be made right now raises CopyHeld,
    with what did get done saved and the run still "copying" for the next time."""
    log = read_log(h)
    finished = []
    for run in log["runs"]:
        if run.get("status") != "copying":
            continue
        problems = []
        try:
            for m in run["moves"]:
                if m.get("done"):
                    continue
                src, dst = h / DROP_NAME / m["src"], h / m["dst"]
                if not src.exists():
                    if dst.exists():
                        m["done"] = True  # copied just before the cut; the drop box has been tidied since
                    else:
                        problems.append(f"{m['src']} is gone from the drop box and was never copied")
                    continue
                copy_move(m, src, dst, problems)
        except CopyHeld:
            write_log(h, log)
            raise
        run["problems"] = problems
        run["status"] = "problems" if problems else "done"
        write_kits(h, run)
        finished.append(run)
    if finished:
        write_log(h, log)
    return finished


def stopped_brings(h):
    """Brings that stopped part way because a copy couldn't be made right then (written only when that
    happens): (the record's path, its list)."""
    p = h / ".studio" / "drop" / "bring-stopped.json"
    try:
        return p, json.loads(p.read_text(encoding="utf-8")).get("brings", [])
    except (OSError, ValueError, AttributeError):
        return p, []


def bring(h, folder):
    """Copy the finished photos (and only those) from a folder they chose into the drop box, under the
    folder's own name, checked file by file. The originals are never moved. Returns (copied, skipped_by_kind, dest).
    A bring of the same folder that stopped part way (a file held open, a full drive) carries on into the same
    folder in the drop box: what's already there is compared, never replaced, so nothing is copied twice."""
    src = Path(folder).expanduser()
    if not src.is_dir():
        say(f"STOP: {src} isn't a folder I can see.")
        return None
    drop = h / DROP_NAME
    name = src.name or "Photos"
    where_from = str(src.resolve())
    rec, stopped = stopped_brings(h)
    again = next((b for b in stopped if b.get("status") == "stopped" and b.get("into")
                  and this_computer.same_place(b.get("from", ""), where_from) and (drop / b["into"]).is_dir()), None)
    if again:
        dest = drop / again["into"]
    else:
        dest = drop / name
        n = 2
        while dest.exists() and any(dest.iterdir()):
            dest = drop / f"{name} {n}"
            n += 1

    def note(entry):
        if entry not in stopped:
            stopped.append(entry)
        rec.parent.mkdir(parents=True, exist_ok=True)
        save_text(rec, json.dumps({"brings": stopped}, indent=1, ensure_ascii=False))

    files = walk(src)
    total = sum(1 for rel in files if kind(rel) == "photo")
    copied, skipped = 0, {}
    for rel in files:
        k = kind(rel)
        if k != "photo":
            label = {"raw": "RAW file", "video": "video", "working": WORKING.get(Path(rel).suffix.lower(), "working file")}.get(k, "other file")
            skipped[label] = skipped.get(label, 0) + 1
            continue
        try:
            got = copy_checked(src / rel, dest / rel)
        except OSError as ex:
            entry = again or {"from": where_from, "into": dest.name}
            entry.update({"status": "stopped", "when": datetime.now().isoformat(timespec="seconds"),
                          "copied": copied, "of": total})
            note(entry)
            say(f"STOP: {rel} could not be copied: {could_not(ex)}. {copied} of {total} photos copied so far, each one "
                "checked; once that's sorted, running it again copies the rest into the same folder (nothing is copied "
                "twice). Your originals weren't moved.")
            return None
        if got is None:
            if again:                            # this folder can't be finished as it is: the next bring starts a fresh one
                again["status"] = "did not match"
                note(again)
            say(f"STOP: {rel} did not match the original after copying. Nothing else was changed.")
            return None
        copied += 1
    if again:
        again.update({"status": "finished", "finished": datetime.now().isoformat(timespec="seconds"), "copied": copied})
        note(again)
    return copied, skipped, dest


def write_kits(h, run):
    for s in run["shoots"]:
        kit = h / CONTENT_NAME / s["folder"]
        if not kit.exists():
            continue
        rec = kit / ".kit"
        rec.mkdir(exist_ok=True)
        hide(rec)
        photos = sorted(p.name for p in (kit / "Photos").iterdir() if p.is_file() and not p.name.startswith(".")
                        and not p.name.endswith(".studio-partial")) if (kit / "Photos").is_dir() else []
        save_text(rec / "kit.json", json.dumps({
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
                name = f"{rp.relative_to(drop).as_posix().replace('/', '_')}_{f}".lstrip("._")
                dst, n = aside / name, 2
                while os.path.lexists(dst):              # one set aside earlier under that name: keep both
                    dst, n = aside / f"{n}_{name}", n + 1
                try:
                    into_place(rp / f, dst)
                except OSError:
                    pass
        if rp != drop:
            try:
                rp.rmdir()
            except OSError:
                pass


def put_look_away(h, run):
    """The look a finished sort came from is kept beside it under the sort's time, as every sort does."""
    this_computer.replace(h / ".studio" / "drop" / "look.json", h / ".studio" / "drop" / f"look-{run['started'].replace(':', '-')}.json")


def sorted_words(run):
    """The end of a sort in plain words, and its exit: 0 done, 1 a copy that did not match."""
    problems, shoots = run.get("problems") or [], run["shoots"]
    if problems:
        say("STOP: " + problems[0] + (f" (and {len(problems) - 1} more)" if len(problems) > 1 else ""))
        return 1
    n = sum(s["photos"] for s in shoots)
    say(f"Done. Copied {n} photos into {CONTENT_NAME}: " + "; ".join(f"\"{s['folder']}\" ({s['photos']})" for s in shoots)
        + ". Every copy was checked against the original. What you dropped is still in the drop box, exactly as you dropped it:"
        " put it back where it came from if you moved it in by accident, or clear it out whenever you like.")
    return 0


def do_sort(h, mode, specs, one_name, undated_to, dry_run):
    try:
        finished = finish_unfinished(h)
    except CopyHeld as held:
        say(held.words())
        return 1
    if finished:
        say("Finished a sort that was cut off earlier.")
    r = load_look(h)
    drop = h / DROP_NAME
    shoots, moves = plan(h, r, mode, specs, one_name, undated_to)
    # The very sort that was just finished (it stopped part way, and they ran it again): it is done now, so
    # say how it went rather than stopping on its own folders as a name clash.
    want = [(m["src"], m["dst"]) for m in moves]
    same = next((run for run in finished if [(m.get("src"), m.get("dst")) for m in run.get("moves", [])] == want), None)
    if same is not None and not dry_run:
        put_look_away(h, same)
        return sorted_words(same)
    # everything still there, nothing in the way
    gone = [m["src"] for m in moves if not (drop / m["src"]).exists()]
    if gone:
        say(f"STOP: {len(gone)} of the photos from the last look aren't in the drop box any more (first: {gone[0]}). Look again.")
        return 1
    clashes = sorted({m["shoot"] for m in moves if (h / CONTENT_NAME / m["shoot"]).exists()})
    if clashes:
        say(f"STOP: there's already a folder in {CONTENT_NAME} called " + " and ".join(f"\"{c}\"" for c in clashes) + ". Give this one another name; nothing was copied.")
        return 6
    say("The plan:")
    for s in shoots:
        say(f"  {s['folder']}   {s['photos']} photos")
    left = len(r["undated"]) if undated_to in (None, "leave") else 0
    stay = left + len(r["raws"]) + len(r["videos"]) + len(r.get("working", [])) + len(r["others"])
    if stay:
        say(f"  Left in the drop box: " + ", ".join(x for x in [
            plural(left, "undated photo") if left else "", plural(len(r["raws"]), "RAW file") if r["raws"] else "",
            plural(len(r.get("working", [])), "working file (TIFF, Photoshop, catalogs)") if r.get("working") else "",
            plural(len(r["videos"]), "video") if r["videos"] else "", plural(len(r["others"]), "other file") if r["others"] else ""] if x))
    if dry_run:
        say("Dry run: nothing copied.")
        return 0
    for m in moves:
        try:
            st = (drop / m["src"]).stat()
            m["size"], m["mtime"] = st.st_size, int(st.st_mtime)
        except OSError:
            pass
    log = read_log(h)
    run = {"started": datetime.now().isoformat(timespec="seconds"), "mode": mode, "status": "copying", "shoots": shoots, "moves": moves}
    log["runs"].append(run)
    write_log(h, log)
    problems = []
    try:
        for m in moves:
            copy_move(m, drop / m["src"], h / m["dst"], problems)
    except CopyHeld as held:
        write_log(h, log)        # still "copying", with what's done marked: the next look or sort finishes the rest
        say(held.words())
        return 1
    run["problems"] = problems
    run["status"] = "problems" if problems else "done"
    write_log(h, log)
    write_kits(h, run)
    put_look_away(h, run)
    return sorted_words(run)


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
                info = json.loads(rec.read_text(encoding="utf-8"))
            except ValueError:
                pass
        photos = len([p for p in (d / "Photos").iterdir() if p.is_file() and not p.name.startswith(".")]) if (d / "Photos").is_dir() else 0
        out.append({"folder": d.name, "path": str(d), "name": info.get("name", d.name), "date": info.get("date"), "photos": photos,
                    "kit": (d / ".kit" / "Post kit.html").exists() or (d / "Post kit.html").exists()})
    out.sort(key=lambda k: (k["date"] or "", k["folder"]), reverse=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("places")
    st = sub.add_parser("setup"); st.add_argument("--where"); st.add_argument("--home")
    sub.add_parser("show"); sub.add_parser("list")
    lk = sub.add_parser("look"); lk.add_argument("--gap", type=float, default=120); lk.add_argument("--previews", type=int, default=4)
    br = sub.add_parser("bring", help="copy the finished photos from a folder into the drop box (originals untouched)")
    br.add_argument("folder")
    so = sub.add_parser("sort")
    so.add_argument("--separate", action="store_true"); so.add_argument("--one"); so.add_argument("--only", action="store_true")
    so.add_argument("specs", nargs="*"); so.add_argument("--undated", default="leave"); so.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.cmd == "bring":
        h = need_home()
        got = bring(h, a.folder)
        if not got:
            return 1
        copied, skipped, dest = got
        left = ", ".join(plural(n, k) for k, n in sorted(skipped.items()))
        say(f"Copied {copied} finished photo{'s' if copied != 1 else ''} from \"{Path(a.folder).name}\" into the drop box, every one checked. Your originals weren't moved."
            + (f" Left behind, not copied: {left}." if left else ""))
        say(json.dumps({"copied": copied, "skipped": skipped, "dest": str(dest)}))   # through say() like every line: a closed output can't end a finished copy in an error
        return 0 if copied else 3
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
            say(f"No {HOME_NAME} folder yet (needs setup).")
            return 2
        say(f"{HOME_NAME} folder: {h}" + ("" if h.is_dir() else "  (not there right now; drive unplugged?)"))
        if h.is_dir():
            waiting = walk(h / DROP_NAME) if (h / DROP_NAME).is_dir() else []
            say(f"Drop a shoot here: {len(waiting)} file{'s' if len(waiting) != 1 else ''} waiting" if waiting else "Drop a shoot here: empty")
            ks = kits(h)
            say(f"{CONTENT_NAME}: {len(ks)} shoot{'s' if len(ks) != 1 else ''}")
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
        try:
            if finish_unfinished(h):
                say("Finished a sort that was cut off earlier.")
        except CopyHeld as held:
            say(held.words())
            return 1
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
