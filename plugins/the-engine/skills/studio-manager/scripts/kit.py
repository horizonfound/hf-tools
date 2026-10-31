#!/usr/bin/env python3
"""The post kit: everything for one shoot's social posts, in one folder, made at once.

    Content/2026-06-24 Beach/
      Photos/                  the finished photos (moved in from the drop box, or left where
                               Lightroom exported them and pointed to; never changed)
      Singles/                 the single posts, sized for Instagram (fit within 1080 x 1350)
      Carousel/                the slides in order, all 1080 x 1350 (padded so they match)
      Stories/                 story frames, 1080 x 1920
      Reel.txt                 which CapCut project the reel is, and the photos in it
      Captions and hooks.txt   everything written, ready to paste
      Post kit.html            the page: every piece with a Copy button

Claude does the choosing and the writing; this does the files. Nothing posts.

    python3 kit.py start "beach"                       the kit for a shoot in Content (a few words find it)
    python3 kit.py start --night "<backup>" --shoot s1    a shoot the Studio backed up: finds their export folder,
                                                       makes the kit folder, points Photos at the exports
    python3 kit.py start --folder "<any folder of finished photos>" [--name "..."]
    python3 kit.py told "beach" --text "..."           what they said when asked about the shoot
    python3 kit.py sheet "beach"                       numbered contact sheets of the photos (reel.py's)
    python3 kit.py picks "beach" --singles 3,17,22 --stories 5,9,30,41 --carousel 1,4,8,12,15,19,23 --reel 2,6,... [--cover 2]
    python3 kit.py build "beach"                       Singles, Carousel, Stories from the picks (reel via reel.py)
    python3 kit.py facts "beach"                       what Claude writes the words from (JSON)
    python3 kit.py words "beach" --file words.json     save the hooks, caption, short caption, story lines
    python3 kit.py page "beach"                        rebuild Post kit.html
    python3 kit.py voice --sample-file posted.txt --never-file never.txt --audience both --hashtags "#..."
                                                       how they write for Instagram (asked once; in the Studio File)
    python3 kit.py show "beach"

Exit: 0 done, 1 problem, 2 nothing there, 7 the export folder could not be found (ask).
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exif_read  # noqa: E402
import posts  # noqa: E402
import studio_file  # noqa: E402

REEL_PY = HERE.parent.parent / "assistant-make-a-reel" / "scripts" / "reel.py"
PHOTO = posts.PHOTO
# Instagram's shapes, checked Oct 30, 2026 (Sked Social, posteverywhere.ai): feed posts 4:5 (1080x1350) are the
# safe default; 3:4 is in-app only; the profile grid shows a 3:4 tile cut from the middle of each post, so a 4:5
# post loses a sliver off each side there; every slide of a carousel takes the first slide's shape; stories and
# reels are 9:16 (1080x1920), with the grid showing the middle 3:4 of a reel's cover.
SINGLE = (1080, 1350)        # 4:5
CAROUSEL = (1080, 1350)      # 4:5, every slide the same
STORY = (1080, 1920)         # 9:16
COVER = (1080, 1920)         # the reel cover, 9:16; the grid shows its middle 3:4
GRID = (1080, 1440)          # 3:4, what the profile grid shows of a post
WIDEST = 1.91                # the widest Instagram keeps a feed photo; wider gets trimmed
PAD_DARK = "1A1A1C"
PAD_WHITE = "FFFFFF"
TOP_BIAS = 0.4               # when a tall photo is trimmed to 4:5, take 40% of the cut from the top, 60% from the bottom (faces sit high)
KINDS = ("reel", "carousel", "singles", "stories")
FONTS = "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&family=DM+Sans:wght@400;500;600&display=swap"


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


# ---------- finding a kit ----------

def rec_path(kit):
    return kit / ".kit" / "kit.json"


def load_rec(kit):
    p = rec_path(kit)
    return json.loads(p.read_text()) if p.exists() else {}


def save_rec(kit, rec):
    d = kit / ".kit"
    d.mkdir(exist_ok=True)
    posts.hide(d)
    tmp = d / "kit.json.tmp"
    tmp.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    os.replace(tmp, d / "kit.json")


def find_kit(words):
    """A kit folder in Content from a few words of its name (or the exact folder name, or a path)."""
    p = Path(words)
    if p.is_dir() and (p / ".kit").is_dir():
        return p
    h = posts.need_home()
    content = h / posts.CONTENT_NAME
    if (content / words).is_dir():
        return content / words
    w = [x for x in re.split(r"[^a-z0-9]+", words.lower()) if x]
    hits = [d for d in content.iterdir() if d.is_dir() and not d.name.startswith(".") and all(x in d.name.lower() for x in w)]
    exact = [d for d in hits if load_rec(d).get("name", "").lower() == words.strip().lower()]
    if len(exact) == 1:
        return exact[0]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        say(f"STOP: nothing in Content matches \"{words}\". (posts.py list shows what's there.)")
        sys.exit(2)
    say(f"STOP: \"{words}\" could mean more than one: " + ", ".join(d.name for d in sorted(hits)) + ". Say which.")
    sys.exit(1)


def photos_dir(kit, rec=None):
    rec = rec or load_rec(kit)
    if rec.get("photos_dir"):
        return Path(rec["photos_dir"])
    return kit / "Photos"


def photo_files(folder):
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in PHOTO and not p.name.startswith("."))


# ---------- start ----------

def start_from_folder(folder, name=None):
    folder = Path(folder)
    if not folder.is_dir():
        say(f"STOP: {folder} isn't a folder I can see.")
        sys.exit(2)
    files = photo_files(folder)
    if not files:
        say(f"STOP: no finished photos (JPEG, HEIC, PNG, TIFF) in {folder}.")
        sys.exit(2)
    h = posts.need_home()
    taken = sorted(t for t in ((exif_read.read(f) or {}).get("taken") for f in files[:200]) if t)
    when = taken[0] if taken else datetime.fromtimestamp(files[0].stat().st_mtime).isoformat()
    nm = posts.clean_name(name or posts.date_name([{"folders": [folder.name]}]))
    folder_name = posts.folder_name(nm, when)
    kit = h / posts.CONTENT_NAME / folder_name
    if kit.exists() and not (kit / ".kit").is_dir():
        say(f"STOP: there's already a folder in Content called \"{folder_name}\" that isn't a kit. Give this one another name.")
        sys.exit(6)
    kit.mkdir(parents=True, exist_ok=True)
    rec = load_rec(kit) or {"name": nm, "date": when[:10], "folder": folder_name, "source": "folder", "made": datetime.now().isoformat(timespec="seconds")}
    rec["photos_dir"] = str(folder)
    rec["photos"] = [f.name for f in files]
    save_rec(kit, rec)
    return kit


def start_from_night(night, shoot_id):
    """A shoot the Studio backed up: its edited exports become the kit's photos (left where they are)."""
    from where import locate
    import find_exports
    root, studio = locate(night)
    shoots = json.loads((studio / "shoots.json").read_text())["shoots"]
    s = next((x for x in shoots if x["id"] == shoot_id), None)
    if not s:
        say(f"STOP: no shoot {shoot_id} in that backup.")
        sys.exit(1)
    names = json.loads((studio / "names.json").read_text()) if (studio / "names.json").exists() else {}
    name = names.get(shoot_id) or s.get("name") or s.get("suggested") or shoot_id
    remembered = studio_file.load().get("exports")
    found = find_exports.find(root, studio, shoot_id, remembered)
    if not found or not found.get("folder"):
        say("STOP: I couldn't find the edited photos for this shoot. Where did you export them? (exit 7)")
        sys.exit(7)
    folder = Path(found["folder"])
    sh_folder = s.get("folder")
    folder_name = Path(sh_folder).name if sh_folder else posts.folder_name(name, s.get("start") or datetime.now().isoformat())
    h = posts.need_home()
    kit = h / posts.CONTENT_NAME / folder_name
    kit.mkdir(parents=True, exist_ok=True)
    rec = load_rec(kit) or {"name": name, "date": (s.get("start") or "")[:10], "folder": folder_name, "source": "backup",
                            "made": datetime.now().isoformat(timespec="seconds")}
    rec.update({"night": str(night), "shoot_id": shoot_id, "photos_dir": str(folder), "photos": [f.name for f in photo_files(folder)]})
    save_rec(kit, rec)
    return kit


# ---------- the sheet and the picks ----------

def sheet(kit):
    rec = load_rec(kit)
    folder = photos_dir(kit, rec)
    r = subprocess.run([sys.executable, str(REEL_PY), "sheet", "--folder", str(folder), "--shoot", rec.get("name", kit.name)],
                       capture_output=True, text=True)
    say(r.stdout.strip())
    if r.returncode != 0:
        say(r.stderr.strip())
        return 1
    m = re.search(r"List: (.+)", r.stdout)
    if m and Path(m.group(1).strip()).exists():
        listing = json.loads(Path(m.group(1).strip()).read_text())
        shutil.copyfile(m.group(1).strip(), kit / ".kit" / "sheet.json")
        rec["numbered"] = len(listing["photos"])
        save_rec(kit, rec)
    return 0


def numbered(kit):
    p = kit / ".kit" / "sheet.json"
    if not p.exists():
        say("STOP: make the sheet first (kit.py sheet), so the picks have numbers.")
        sys.exit(2)
    return {x["n"]: x for x in json.loads(p.read_text())["photos"]}


def parse_nums(s):
    return [int(x) for x in re.findall(r"\d+", s or "")]


def set_picks(kit, singles, stories, carousel, reel, cover=None):
    by_n = numbered(kit)
    rec = load_rec(kit)
    picks = rec.get("picks", {})
    for key, val in (("singles", singles), ("stories", stories), ("carousel", carousel), ("reel", reel), ("cover", cover)):
        if val is None:
            continue
        ns = parse_nums(val)
        if key == "cover":
            ns = ns[:1]
        bad = [n for n in ns if n not in by_n]
        if bad:
            say(f"STOP: no photo numbered {bad[0]} on the sheet.")
            sys.exit(1)
        picks[key] = ns
    rec["picks"] = picks
    save_rec(kit, rec)
    return picks


# ---------- building the pieces ----------

def size_of(p):
    if shutil.which("sips"):
        r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(p)], capture_output=True, text=True)
        w = re.search(r"pixelWidth: (\d+)", r.stdout)
        h = re.search(r"pixelHeight: (\d+)", r.stdout)
        if w and h:
            return int(w.group(1)), int(h.group(1))
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.size
    except Exception:
        return None


def _pad_rgb(hexs):
    return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


def shape(src, dst, box, how, pad=PAD_DARK, bias=TOP_BIAS):
    """Make the photo fit Instagram's box (w, h) one of three ways, never stretching:
      "fit"   the whole photo inside the box, its own shape, no padding (a tall photo comes out narrower than the box)
      "pad"   the whole photo inside the box, padded to the box with a plain color
      "crop"  the box filled, the extra trimmed (tall photos lose a little top and bottom, more from the bottom)
    The Mac's own sips does all of it with nothing installed; Pillow elsewhere."""
    W, H = box
    size = size_of(src)
    if not size:
        return False
    w, h = size
    if how == "crop":
        scale = max(W / w, H / h)
    else:
        scale = min(W / w, H / h, 1.0)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    cut_y = max(0, nh - H) if how == "crop" else 0
    cut_x = max(0, nw - W) if how == "crop" else 0
    off_y, off_x = round(cut_y * bias), cut_x // 2
    if shutil.which("sips"):
        cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", "--resampleHeightWidth", str(nh), str(nw)]
        if how == "crop" and (cut_y or cut_x):
            cmd += ["--cropOffset", str(off_y), str(off_x), "--cropToHeightWidth", str(H), str(W)]
        elif how == "pad":
            cmd += ["--padToHeightWidth", str(H), str(W), "--padColor", pad]
        cmd += [str(src), "--out", str(dst)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode == 0 and dst.exists()
    try:
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        im = im.resize((nw, nh), Image.LANCZOS)
        if how == "crop" and (cut_y or cut_x):
            im = im.crop((off_x, off_y, off_x + W, off_y + H))
        elif how == "pad":
            bg = Image.new("RGB", (W, H), _pad_rgb(pad))
            bg.paste(im, ((W - nw) // 2, (H - nh) // 2))
            im = bg
        im.save(dst, "JPEG", quality=92)
        return True
    except Exception:
        return False


def fit(src, dst, box, pad=None):
    """Kept for the posting queue's thumbnails: fit, padded if a color is given."""
    return shape(src, dst, box, "pad" if pad else "fit", pad or PAD_DARK)


def single(src, dst):
    """A single post: tall photos become 4:5 (a little trimmed, more from the bottom); square stays square;
    wide photos keep their shape, trimmed only if wider than Instagram allows."""
    size = size_of(src)
    if not size:
        return False
    w, h = size
    if h > w * 1.05:
        return shape(src, dst, SINGLE, "crop")
    if w > h * WIDEST:
        return shape(src, dst, (1080, round(1080 / WIDEST)), "crop")
    return shape(src, dst, (1080, 1080), "fit")


def slide(src, dst, pad=PAD_WHITE):
    """A carousel slide: every slide 4:5. Tall photos are trimmed to it; square and wide ones sit on a plain
    background (white by default) so the whole photo shows."""
    size = size_of(src)
    if not size:
        return False
    w, h = size
    if h > w * 1.05:
        return shape(src, dst, CAROUSEL, "crop")
    return shape(src, dst, CAROUSEL, "pad", pad)


def build(kit):
    rec = load_rec(kit)
    picks = rec.get("picks", {})
    if not picks:
        say("STOP: no picks yet (kit.py picks).")
        return 2
    by_n = numbered(kit)
    made = {}
    pad = rec.get("slide_background", PAD_WHITE)
    makers = {"singles": (lambda a, b: single(a, b), "Single"),
              "carousel": (lambda a, b: slide(a, b, pad), "Slide"),
              "stories": (lambda a, b: shape(a, b, STORY, "pad", PAD_DARK), "Story")}
    for key, (maker, prefix) in makers.items():
        ns = picks.get(key) or []
        if not ns:
            continue
        out = kit / key.capitalize()
        out.mkdir(exist_ok=True)
        files = []
        for i, n in enumerate(ns, 1):
            src = Path(by_n[n]["file"])
            dst = out / f"{prefix} {i:02d} ({src.stem}).jpg"
            if dst.exists() or maker(src, dst):
                files.append(dst.name)
            else:
                say(f"(could not size {src.name} for {key})")
        made[key] = files
    # the reel cover: 9:16 from the cover pick (or the first reel pick), plus what the grid will show of it
    cover_n = picks.get("cover") or (picks.get("reel") or [None])[:1]
    cover_n = cover_n[0] if isinstance(cover_n, list) else cover_n
    if cover_n:
        out = kit / "Covers"
        out.mkdir(exist_ok=True)
        src = Path(by_n[cover_n]["file"])
        full, grid = out / "Reel cover.jpg", out / "Reel cover, as the grid shows it.jpg"
        ok = (full.exists() or shape(src, full, COVER, "crop")) and (grid.exists() or shape(full, grid, GRID, "crop", bias=0.5))
        made["covers"] = [full.name, grid.name] if ok else []
    rec["made_pieces"] = {**rec.get("made_pieces", {}), **made}
    rec["built"] = datetime.now().isoformat(timespec="seconds")
    save_rec(kit, rec)
    for k, fs in made.items():
        say(f"{k.capitalize()}: {len(fs)} made.")
    if picks.get("reel"):
        say("Reel: run reel.py make with these picks: " + ",".join(str(n) for n in picks["reel"]) + f" --folder \"{photos_dir(kit, rec)}\" --shoot \"{rec.get('name')}\""
            + (f" --night \"{rec['night']}\" --shoot-id {rec['shoot_id']}" if rec.get("night") else ""))
    write_page(kit)
    return 0


def note_reel(kit, project_name, picks=None):
    rec = load_rec(kit)
    rec["reel"] = {"project": project_name, "picks": picks or rec.get("picks", {}).get("reel", []), "made": datetime.now().isoformat(timespec="seconds")}
    save_rec(kit, rec)
    (kit / "Reel.txt").write_text(f"The reel for this shoot is the CapCut project \"{project_name}\".\nOpen CapCut, style it the way you like, and export it from there.\n"
                                  + ("Photos in it, in order: " + ", ".join(str(n) for n in rec["reel"]["picks"]) + "\n" if rec["reel"]["picks"] else ""))
    write_page(kit)


# ---------- the words ----------

def voice():
    return studio_file.load().get("voice", {})


def set_voice(sample=None, never=None, audience=None, hashtags=None):
    sf = studio_file.load()
    v = sf.setdefault("voice", {})
    if sample is not None:
        v["samples"] = [s.strip() for s in re.split(r"\n\s*\n", sample.strip()) if s.strip()]
    if never is not None:
        v["never"] = [s.strip() for s in re.split(r"\n\s*\n", never.strip()) if s.strip()]
    if audience:
        v["audience"] = audience
    if hashtags is not None:
        v["hashtags"] = hashtags.strip()
    sf["voice"] = v
    studio_file.save(sf)
    return v


def told(kit, text):
    p = kit / ".kit" / "told.json"
    old = json.loads(p.read_text()).get("text", "") if p.exists() else ""
    t = (old + "\n" + text.strip()).strip() if old else text.strip()
    p.write_text(json.dumps({"text": t, "at": datetime.now().isoformat(timespec="seconds")}, indent=1, ensure_ascii=False))


def time_words(times):
    if not times:
        return ""
    hs = [int(t[11:13]) for t in times]
    mid = sum(hs) / len(hs)
    return "in the morning" if mid < 11 else "around midday" if mid < 14 else "in the afternoon" if mid < 17 else "in the evening"


def facts(kit):
    rec = load_rec(kit)
    folder = photos_dir(kit, rec)
    files = photo_files(folder)
    exifs = [exif_read.read(f) or {} for f in files[:120]]
    times = sorted(e["taken"] for e in exifs if e.get("taken"))
    lenses = sorted({e["lens"] for e in exifs if e.get("lens")})
    cams = sorted({e["camera"] for e in exifs if e.get("camera")})
    told_p = kit / ".kit" / "told.json"
    out = {
        "name": rec.get("name"), "folder": kit.name, "date": rec.get("date"), "photos": len(files),
        "day": datetime.fromisoformat(times[0]).strftime("%A, %B %-d, %Y") if times else "",
        "time_of_day": time_words(times), "span_minutes": round((datetime.fromisoformat(times[-1]) - datetime.fromisoformat(times[0])).total_seconds() / 60) if len(times) > 1 else 0,
        "lenses": lenses, "cameras": cams,
        "they_said": json.loads(told_p.read_text()).get("text", "") if told_p.exists() else "",
        "picks": rec.get("picks", {}), "numbered_list": str(kit / ".kit" / "sheet.json"),
        "voice": voice(), "client_note_voice": studio_file.load().get("note", {}),
        "existing_words": bool((kit / ".kit" / "words.json").exists()),
    }
    if rec.get("night") and rec.get("shoot_id"):
        try:
            import client_note
            cf = client_note.facts(rec["night"], rec["shoot_id"]) or {}
            out["from_the_backup"] = {k: cf.get(k) for k in ("recap", "they_said", "sneak_peeks", "to", "due_words")}
        except Exception as e:  # the backup's records may be on an unplugged drive
            out["from_the_backup"] = f"(not readable: {e})"
    return out


def save_words(kit, words):
    for k in ("hooks", "caption", "short", "stories"):
        words.setdefault(k, [] if k in ("hooks", "stories") else "")
    words["written"] = datetime.now().isoformat(timespec="seconds")
    (kit / ".kit" / "words.json").write_text(json.dumps(words, indent=1, ensure_ascii=False))
    lines = ["HOOKS (pick one, or write your own)", ""]
    lines += [f"{i}. {h}" for i, h in enumerate(words["hooks"], 1)]
    lines += ["", "CAPTION", "", words["caption"].strip(), ""]
    if words.get("short"):
        lines += ["SHORT CAPTION", "", words["short"].strip(), ""]
    if words.get("stories"):
        lines += ["STORY LINES", ""] + [f"- {s}" for s in words["stories"]] + [""]
    if words.get("hashtags"):
        lines += ["HASHTAGS", "", words["hashtags"].strip(), ""]
    if words.get("leaned_on"):
        lines += ["", f"Written from: {words['leaned_on']}"]
    (kit / "Captions and hooks.txt").write_text("\n".join(lines) + "\n")
    write_page(kit)


# ---------- the page ----------

CSS = """
:root{--cream:#FAFAF6;--paper:#FFFFFF;--ink:#1F2430;--ink-2:#646B78;--coral:#F07F5A;--coral-2:#D4643F;--coral-l:#FCE6DD;--sand-l:#ECEAF6;--line:rgba(31,36,48,.12);
--display:'Fraunces',Georgia,serif;--sans:'DM Sans','Helvetica Neue',Arial,sans-serif;--ease:cubic-bezier(.2,.7,.2,1)}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:400 16px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:0 clamp(16px,4vw,40px) 4rem}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand b{font:600 16px/1 var(--sans)}.brand small{display:block;margin-top:4px;font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.bar .when{margin-left:auto;font:500 13px/1 var(--sans);color:var(--ink-2)}
.bar .homelink{margin-left:auto;font:600 13px/1 var(--sans);color:var(--coral-2);text-decoration:none;padding:8px 12px;border-radius:999px;border:1.5px solid var(--coral-l)}.bar .homelink+.when{margin-left:0}
body:not(.live) .homelink{display:none}
.head{padding:clamp(2rem,5vw,3.4rem) 0 1rem;display:grid;gap:.6rem}
.eyebrow{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
h1{margin:0;font:600 clamp(32px,4.6vw,54px)/1.03 var(--sans);letter-spacing:-.035em;text-wrap:balance}
h1 em{font:italic 400 1.1em/1 var(--display);color:var(--coral-2);letter-spacing:0}
.lede{margin:0;color:var(--ink-2);font-size:clamp(16px,1.4vw,18px);max-width:40em}
.piece{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:1.4rem;align-items:start;background:var(--paper);border-radius:22px;padding:1.3rem;margin-top:1.2rem;box-shadow:0 1px 0 var(--line)}
.piece h2{margin:0 0 .2rem;font:600 24px/1.1 var(--sans);letter-spacing:-.02em}
.piece .sub{color:var(--ink-2);font-size:14px;margin:0 0 .8rem}
.strip{display:flex;gap:6px;flex-wrap:wrap}.strip img{height:150px;width:auto;border-radius:10px;object-fit:cover;background:var(--sand-l);box-shadow:0 0 0 1px var(--line);cursor:zoom-in;transition:transform .3s var(--ease)}.strip img:hover{transform:translateY(-2px)}
.strip.tall img{height:210px}
.words{display:grid;gap:.8rem}
.w{border:1px solid var(--line);border-radius:14px;padding:.8rem .95rem;position:relative}
.w .k{font:600 10px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--coral-2);margin-bottom:.4rem}
.w p{margin:0;white-space:pre-wrap;font-size:15px}
.w.hook p{font:italic 400 19px/1.3 var(--display)}
.copy{position:absolute;top:.6rem;right:.6rem;border:0;border-radius:999px;padding:.4rem .8rem;font:600 12px/1 var(--sans);background:var(--ink);color:#fff;cursor:pointer;transition:transform .2s var(--ease)}
.copy:hover{transform:scale(1.04)}.copy.done{background:var(--coral)}
.empty{font:italic 400 16px/1.3 var(--display);color:var(--ink-2)}
.lean{font-size:13px;color:var(--ink-2);margin-top:1rem}
.folder{font-size:13px;color:var(--ink-2)}
.go{display:inline-flex;align-items:center;gap:.4rem;border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:999px;padding:.5rem .95rem;font:600 13.5px/1 var(--sans);cursor:pointer;transition:all .2s var(--ease)}
.go:hover{border-color:var(--coral);color:var(--coral-2);transform:translateY(-1px)}
a.go{text-decoration:none}
.go.main{background:var(--ink);color:#fff;border-color:var(--ink)}.go.main:hover{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.went{font-size:13px;color:var(--ink-2);min-height:1.2em;margin:.4rem 0 0}
.piece .top{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin-bottom:.5rem}
.piece .top h2{margin:0}
.ratio{font:600 10px/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--ink-2);border:1px solid var(--line);border-radius:999px;padding:.3em .6em;margin-left:.5rem;vertical-align:middle}
.big{position:fixed;inset:0;background:rgba(20,22,30,.92);display:none;place-items:center;z-index:50;cursor:zoom-out}.big.on{display:grid}.big img{max-width:92vw;max-height:92vh;border-radius:12px}
@media(max-width:760px){.piece{grid-template-columns:1fr}}
"""

SCRIPT = """
document.querySelectorAll('.copy').forEach(b=>b.onclick=async()=>{const t=b.parentElement.querySelector('p').textContent;
 try{await navigator.clipboard.writeText(t)}catch(e){const r=document.createRange();r.selectNodeContents(b.parentElement.querySelector('p'));const s=getSelection();s.removeAllRanges();s.addRange(r);document.execCommand('copy')}
 b.textContent='Copied';b.classList.add('done');setTimeout(()=>{b.textContent='Copy';b.classList.remove('done')},1600)});
const live=location.protocol.startsWith('http');if(live)document.body.classList.add('live');const KIT=document.body.dataset.kit;
document.querySelectorAll('.go').forEach(b=>b.onclick=async()=>{const line=b.closest('.piece,header').querySelector('.went');
 if(!live){line.textContent='This is a saved copy. Say “show the '+document.body.dataset.name+' kit” to Claude and the buttons work.';return}
 line.textContent='Opening...';
 try{const r=await fetch('/open?kit='+encodeURIComponent(KIT)+'&sub='+encodeURIComponent(b.dataset.sub||''));const j=await r.json();line.textContent=j.words}
 catch(e){line.textContent='Could not reach the Studio. Tell Claude instead.'}});
const big=document.getElementById('big');document.querySelectorAll('.strip img').forEach(i=>i.onclick=()=>{big.querySelector('img').src=i.src;big.classList.add('on')});big.onclick=()=>big.classList.remove('on');
"""


def rel(kit, p):
    return html.escape(Path(p).relative_to(kit).as_posix()) if str(p).startswith(str(kit)) else html.escape(str(p))


def write_page(kit):
    rec = load_rec(kit)
    words = json.loads((kit / ".kit" / "words.json").read_text()) if (kit / ".kit" / "words.json").exists() else {}
    name = rec.get("name", kit.name)
    when = rec.get("date") or ""
    try:
        when_words = date.fromisoformat(when).strftime("%B %-d, %Y")
    except ValueError:
        when_words = when
    made = rec.get("made_pieces", {})

    def strip(folder_name, tall=False):
        d = kit / folder_name
        if not d.is_dir():
            return "<p class='empty'>Not made yet.</p>"
        fs = sorted((p for p in d.iterdir() if p.suffix.lower() == ".jpg"), key=lambda p: ("(Canva)" not in p.name, p.name))
        if not fs:
            return "<p class='empty'>Not made yet.</p>"
        return f"<div class='strip{' tall' if tall else ''}'>" + "".join(f"<img src='{html.escape(folder_name)}/{html.escape(f.name)}' alt=''>" for f in fs) + "</div>"

    def wbox(k, text, cls=""):
        return f"<div class='w {cls}'><div class='k'>{html.escape(k)}</div><p>{html.escape(text)}</p><button class='copy'>Copy</button></div>"

    hooks = "".join(wbox(f"Hook {i}", h, "hook") for i, h in enumerate(words.get("hooks", []), 1)) or "<p class='empty'>Not written yet.</p>"
    caption = wbox("Caption", words["caption"]) if words.get("caption") else ""
    short = wbox("Short caption", words["short"]) if words.get("short") else ""
    tags = wbox("Hashtags", words["hashtags"]) if words.get("hashtags") else ""
    story_lines = "".join(wbox(f"Story {i}", s) for i, s in enumerate(words.get("stories", []), 1))
    reel = rec.get("reel")
    reel_html = (f"<p>In CapCut as <b>{html.escape(reel['project'])}</b>. Open it there, style it, export it.</p>"
                 + (f"<p class='sub'>Photos in it, in order: {', '.join(str(n) for n in reel.get('picks', []))}</p>" if reel.get("picks") else "")) if reel else "<p class='empty'>Not made yet. Say “make the reel” to Claude.</p>"
    lean = f"<p class='lean'>Written from: {html.escape(words['leaned_on'])}</p>" if words.get("leaned_on") else ""

    canva = rec.get("canva", {})

    def sec(title, sub, ratio, body, wrds, folder, piece=None):
        has = (kit / folder).is_dir()
        btn = f"<button class='go' data-sub='{html.escape(folder)}'>Open the {html.escape(folder)} folder</button>" if has else ""
        cv = canva.get(piece) if piece else None
        if cv and cv.get("edit_url"):
            btn = f"<a class='go' href='{html.escape(cv['edit_url'])}' target='_blank' rel='noopener'>Open in Canva</a> " + btn
        return (f"<section class='piece'><div><div class='top'><h2>{html.escape(title)}<span class='ratio'>{ratio}</span></h2><span>{btn}</span></div>"
                f"<p class='sub'>{html.escape(sub)}</p>{body}<p class='went'></p></div><div class='words'>{wrds}</div></section>")

    page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(name)} · Post kit · The Studio</title><link rel='stylesheet' href='{FONTS}'><style>{CSS}</style></head><body data-kit='{html.escape(kit.name)}' data-name='{html.escape(name)}'>"
            "<div class='wrap'><div class='bar'><span class='brand'><b>The Studio</b><small>by Horizon Found</small></span>"
            f"<a class='homelink' href='/home'>Home</a><span class='when'>{html.escape(when_words)}</span></div>"
            f"<header class='head'><span class='eyebrow'>Post kit</span><h1>{html.escape(name)}<em>.</em></h1>"
            f"<p class='lede'>Everything you need to post this shoot, in one place. Copy the captions, grab the photos from the folders, and post when you're ready. Nothing gets posted for you.</p>"
            f"<p class='folder'>In your Studio folder: {html.escape(posts.CONTENT_NAME)} › {html.escape(kit.name)}</p>"
            f"<p><button class='go main' data-sub=''>Open the kit folder</button> <button class='go' data-sub='Photos'>Open the Photos folder</button></p><p class='went'></p></header>"
            + sec("Reel", ("Cut on the beat, in CapCut. The cover was made in Canva from your template." if canva.get("cover") else "Cut on the beat, in CapCut. The cover is in the Covers folder."), "9:16", reel_html + strip("Covers", tall=True), hooks, "Covers", "cover")
            + sec("Carousel", ("Made in Canva from your template; the plain slides are there too." if canva.get("carousel") else "The slides, in order, all the same size. They are in the Carousel folder."), "4:5", strip("Carousel"), caption + tags, "Carousel", "carousel")
            + sec("Single posts", "Single photos sized for Instagram, in the Singles folder. On your profile grid Instagram shows only the middle of each one, so keep faces near the middle.", "4:5", strip("Singles"), short or caption or "", "Singles")
            + sec("Stories", "Photos sized for stories, in the Stories folder. Instagram puts its own buttons over the top and bottom, so the photo sits in the middle.", "9:16", strip("Stories", tall=True), story_lines or "<p class=empty>Not written yet.</p>", "Stories")
            + f"{lean}</div><div class='big' id='big'><img alt=''></div>"
            f"<script>{SCRIPT}</script></body></html>")
    (kit / "Post kit.html").write_text(page)
    return kit / "Post kit.html"


def show(kit):
    rec = load_rec(kit)
    say(f"{rec.get('name', kit.name)}  ({kit})")
    say(f"  Photos: {len(photo_files(photos_dir(kit, rec)))}" + (f" at {rec['photos_dir']}" if rec.get("photos_dir") else ""))
    p = rec.get("picks", {})
    if p:
        say("  Picks: " + ", ".join(f"{k} {len(v)}" for k, v in p.items() if v))
    for k, v in rec.get("made_pieces", {}).items():
        say(f"  {k.capitalize()}: {len(v)} made")
    if rec.get("reel"):
        say(f"  Reel: CapCut project \"{rec['reel']['project']}\"")
    say("  Words: " + ("written" if (kit / ".kit" / "words.json").exists() else "not yet"))
    say(f"  Page: {kit / 'Post kit.html'}" if (kit / "Post kit.html").exists() else "  Page: not yet")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("start"); st.add_argument("words", nargs="?"); st.add_argument("--night"); st.add_argument("--shoot"); st.add_argument("--folder"); st.add_argument("--name")
    t = sub.add_parser("told"); t.add_argument("words"); t.add_argument("--text", required=True)
    sub.add_parser("sheet").add_argument("words")
    pk = sub.add_parser("picks"); pk.add_argument("words")
    for k in ("singles", "stories", "carousel", "reel", "cover"):
        pk.add_argument(f"--{k}")
    sub.add_parser("build").add_argument("words")
    rl = sub.add_parser("reel-made"); rl.add_argument("words"); rl.add_argument("--project", required=True)
    sub.add_parser("facts").add_argument("words")
    w = sub.add_parser("words"); w.add_argument("words"); w.add_argument("--file", required=True)
    sub.add_parser("page").add_argument("words")
    sub.add_parser("show").add_argument("words")
    v = sub.add_parser("voice"); v.add_argument("--sample-file"); v.add_argument("--never-file"); v.add_argument("--audience", choices=["clients", "photographers", "both"]); v.add_argument("--hashtags")
    a = ap.parse_args()

    if a.cmd == "voice":
        sample = Path(a.sample_file).read_text() if a.sample_file else None
        never = Path(a.never_file).read_text() if a.never_file else None
        vv = set_voice(sample, never, a.audience, a.hashtags)
        say(f"Voice: {len(vv.get('samples', []))} captions of theirs, {len(vv.get('never', []))} they'd never write, for {vv.get('audience', 'both')}"
            + (f", hashtags kept" if vv.get("hashtags") else "") + ".")
        return 0
    if a.cmd == "start":
        if a.night:
            if not a.shoot:
                say("STOP: --night needs --shoot s1.")
                return 1
            kit = start_from_night(a.night, a.shoot)
        elif a.folder:
            kit = start_from_folder(a.folder, a.name)
        elif a.words:
            kit = find_kit(a.words)
            rec = load_rec(kit)
            if not rec.get("photos"):
                rec["photos"] = [f.name for f in photo_files(photos_dir(kit, rec))]
                save_rec(kit, rec)
        else:
            say("STOP: say which shoot (a few words, --night/--shoot, or --folder).")
            return 1
        rec = load_rec(kit)
        say(f"Kit: {kit}")
        say(f"{len(rec.get('photos', []))} photos" + (f" at {rec['photos_dir']}" if rec.get("photos_dir") else "") + ". Next: the question, then kit.py sheet.")
        return 0
    kit = find_kit(a.words)
    if a.cmd == "told":
        told(kit, a.text); say("Kept. It'll shape the captions."); return 0
    if a.cmd == "sheet":
        return sheet(kit)
    if a.cmd == "picks":
        p = set_picks(kit, a.singles, a.stories, a.carousel, a.reel, a.cover)
        say("Picks: " + ", ".join(f"{k} {len(v)}" for k, v in p.items() if v)); return 0
    if a.cmd == "build":
        return build(kit)
    if a.cmd == "reel-made":
        note_reel(kit, a.project); say("Noted. The reel is on the kit page."); return 0
    if a.cmd == "facts":
        say(json.dumps(facts(kit), indent=1, ensure_ascii=False)); return 0
    if a.cmd == "words":
        save_words(kit, json.loads(Path(a.file).read_text())); say(f"Saved. Captions and hooks.txt and the kit page are updated: {kit / 'Post kit.html'}"); return 0
    if a.cmd == "page":
        say(str(write_page(kit))); return 0
    if a.cmd == "show":
        show(kit); return 0


if __name__ == "__main__":
    sys.exit(main())
