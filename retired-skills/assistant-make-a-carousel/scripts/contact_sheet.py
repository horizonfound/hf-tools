#!/usr/bin/env python3
"""The Assistant by Horizon Found: one numbered contact sheet of a session folder.

Looks at every photo in a folder (jpg, jpeg, png, heic, heif, tif, webp, top
level only), sorts them by filename, and writes one sheet of numbered
thumbnails so the whole session can be seen at once. Nothing in the folder is
touched; the sheet goes into <folder>/_assistant/. Also prints a numbered
list with each photo's orientation, size, brightness, warmth and detail.

    python3 contact_sheet.py <folder> [--out path] [--max 40]

Exit codes: 0 made the sheet, 1 something expected went wrong (empty folder,
missing folder), 2 something unexpected went wrong (run again with --debug).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat
except ImportError:  # Pillow is preinstalled in the Assistant's workspace; this is a safety net
    print("Problem: the Pillow image library is missing (python3 -m pip install pillow).")
    sys.exit(1)

try:  # HEIC straight through Pillow when the plugin exists; otherwise we try ImageMagick
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_IN_PILLOW = True
except ImportError:
    HEIF_IN_PILLOW = False

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".webp"}
HEIC_EXTS = {".heic", ".heif"}
WORK_DIR = "_assistant"            # the only place the Assistant ever writes inside a session folder
CONVERTED_DIR = ".converted"       # inside _assistant: HEIC files turned into JPEGs
FONTS_DIR = Path(__file__).resolve().parents[3] / "shared" / "fonts"
RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS


class Problem(Exception):
    """An expected problem with a friendly one-line message."""


# ---------------------------------------------------------------- folder listing
# carousel.py and stories.py use this same listing, so the numbers on the sheet
# mean the same thing everywhere. Keep the three copies identical.

def natural_key(path):
    """Sort like a person reads: IMG_2 before IMG_10, ignoring case."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def list_photos(folder):
    """Every photo file at the top level of the folder, sorted by filename."""
    photos = []
    for path in folder.iterdir():
        if not path.is_file() or path.name.startswith("."):   # skips hidden and Mac "._" files
            continue
        if path.suffix.lower() in IMAGE_EXTS:
            photos.append(path)
    photos.sort(key=natural_key)
    return photos


def subfolders_with_photos(folder):
    found = []
    for path in sorted(folder.iterdir(), key=natural_key):
        if path.is_dir() and not path.name.startswith(".") and path.name != WORK_DIR:
            try:
                count = len(list_photos(path))
            except OSError:
                continue
            if count:
                found.append((path.name, count))
    return found


# ---------------------------------------------------------------- opening photos

_MAGICK = None


def imagemagick():
    """Path to ImageMagick (magick, or an ImageMagick convert), or None."""
    global _MAGICK
    if _MAGICK is None:
        _MAGICK = ""
        for name in ("magick", "convert"):
            exe = shutil.which(name)
            if not exe:
                continue
            try:  # on Windows, "convert" is a disk tool, so check it is really ImageMagick
                out = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=20).stdout
            except (OSError, subprocess.SubprocessError):
                continue
            if "ImageMagick" in out:
                _MAGICK = exe
                break
    return _MAGICK or None


def convert_heic(path, work_dir):
    """Turn a HEIC into a JPEG inside _assistant/.converted. Returns the JPEG path or None."""
    out_dir = work_dir / CONVERTED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (path.stem + ".jpg")
    if out.exists() and out.stat().st_mtime >= path.stat().st_mtime:
        return out
    exe = imagemagick()
    if not exe:
        return None
    try:
        result = subprocess.run([exe, str(path), "-auto-orient", "-quality", "95", str(out)],
                                capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not out.exists():
        return None
    return out


def open_photo(path, work_dir, preview_size=None):
    """Open a photo the right way up. Returns (image, note, full_size).

    image is None (with the reason in note) if it could not be opened. full_size is the
    photo's real pixel size the right way up, even when preview_size asked JPEG decoding
    for a smaller image (much faster for a sheet of big files).
    """
    source = path
    if path.suffix.lower() in HEIC_EXTS and not HEIF_IN_PILLOW:
        source = convert_heic(path, work_dir)
        if source is None:
            how = "ImageMagick is not available" if not imagemagick() else "ImageMagick could not convert it"
            return None, "HEIC skipped (" + how + "; export it as JPEG and try again)", (0, 0)
    try:
        im = Image.open(source)
        full_w, full_h = im.size
        try:
            orientation = im.getexif().get(274, 1)
        except Exception:  # noqa: BLE001 - broken EXIF is not worth failing over
            orientation = 1
        if orientation in (5, 6, 7, 8):
            full_w, full_h = full_h, full_w
        if preview_size and im.format in ("JPEG", "MPO"):
            im.draft("RGB", (preview_size, preview_size))
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
    except (OSError, ValueError, SyntaxError) as e:
        reason = "not a readable image" if "cannot identify" in str(e) else str(e).strip()[:60]
        return None, "could not open (" + reason + ")", (0, 0)
    note = "converted from HEIC" if source is not path else ""
    return im, note, (full_w, full_h)


# ---------------------------------------------------------------- numbers for Claude

def measure(im):
    """Rough brightness (0-100), warmth (-100..100), detail (0-100) from a small copy."""
    small = im.convert("RGB")
    small.thumbnail((160, 160))
    r, g, b = ImageStat.Stat(small).mean
    gray = small.convert("L")
    luma = ImageStat.Stat(gray).mean[0]
    blur = gray.filter(ImageFilter.GaussianBlur(2))
    detail = ImageStat.Stat(ImageChops.difference(gray, blur)).mean[0]
    return {
        "brightness": int(round(luma / 255 * 100)),
        "warmth": int(round((r - b) / 255 * 100)),
        "detail": min(100, int(round(detail * 4))),
    }


def brightness_word(v):
    return "dark" if v < 35 else "bright" if v > 65 else "mid"


def warmth_word(v):
    return "cool" if v < -4 else "warm" if v > 6 else "neutral"


def detail_word(v):
    return "calm" if v < 30 else "busy" if v > 50 else "medium"


def orientation_word(w, h):
    if abs(w - h) <= max(w, h) * 0.04:
        return "square"
    return "portrait" if h > w else "landscape"


# ---------------------------------------------------------------- drawing the sheet

def load_font(name, size):
    """A font from the shared fonts folder, or Pillow's default if it is missing."""
    path = FONTS_DIR / name
    if path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # older Pillow: default font has one size
        return ImageFont.load_default()


def text_width(font, text):
    try:
        return font.getlength(text)
    except AttributeError:  # older Pillow
        return font.getbbox(text)[2]


def shorten(font, text, max_width):
    if text_width(font, text) <= max_width:
        return text
    stem, dot, ext = text.rpartition(".")
    base = stem if dot else text
    while base and text_width(font, base + "..." + (dot + ext if dot else "")) > max_width:
        base = base[:-1]
    return base + "..." + (dot + ext if dot else "")


def plan_cells(entries, long_side):
    """Pick a thumbnail box that matches most of the set (portrait sets get tall cells)."""
    ratios = sorted(e["width"] / e["height"] for e in entries if e.get("width"))
    median = ratios[len(ratios) // 2] if ratios else 0.8
    median = max(0.5625, min(1.7778, median))
    if median >= 1:
        return long_side, int(round(long_side / median))
    return int(round(long_side * median)), long_side


def draw_sheet(entries, thumbs, title, out_path, long_side=380):
    pad, label_h, header_h, margin = 18, 46, 64, 24
    box_w, box_h = plan_cells(entries, long_side)
    cell_w, cell_h = box_w + pad, box_h + label_h + pad
    n = len(entries)
    cols = max(2, min(10, int(round((n * cell_h / cell_w) ** 0.5))))
    cols = min(cols, n)
    if n % cols and cols > 2 and n % (cols - 1) == 0:   # 9 photos: a 3x3, not 4+4+1
        cols -= 1
    rows = (n + cols - 1) // cols
    sheet_w = margin * 2 + cols * cell_w - pad
    sheet_h = header_h + margin + rows * cell_h
    sheet = Image.new("RGB", (sheet_w, sheet_h), (205, 205, 205))
    draw = ImageDraw.Draw(sheet)

    number_font = load_font("Inter-Bold.ttf", max(26, int(min(box_w, box_h) * 0.16)))
    label_font = load_font("Inter-Regular.ttf", 20)
    header_font = load_font("Inter-Regular.ttf", 26)
    draw.text((margin, 20), title, font=header_font, fill=(40, 40, 40))

    for i, (entry, thumb) in enumerate(zip(entries, thumbs)):
        col, row = i % cols, i // cols
        x0 = margin + col * cell_w
        y0 = header_h + margin + row * cell_h
        if thumb is None:
            draw.rectangle((x0, y0, x0 + box_w, y0 + box_h), fill=(170, 170, 170))
            draw.text((x0 + 12, y0 + box_h // 2 - 10), "could not open", font=label_font, fill=(60, 60, 60))
        else:
            tw, th = thumb.size
            tx = x0 + (box_w - tw) // 2
            ty = y0 + (box_h - th) // 2
            sheet.paste(thumb, (tx, ty))
        number = str(entry["index"])
        nw = text_width(number_font, number)
        nh = number_font.size if hasattr(number_font, "size") else 24
        badge = (x0, y0, x0 + int(nw) + 22, y0 + nh + 14)
        draw.rounded_rectangle(badge, radius=6, fill=(20, 20, 20))
        draw.text((x0 + 11, y0 + 4), number, font=number_font, fill=(255, 255, 255))
        label = shorten(label_font, entry["file"], box_w)
        lw = text_width(label_font, label)
        draw.text((x0 + (box_w - lw) / 2, y0 + box_h + 10), label, font=label_font, fill=(35, 35, 35))

    sheet.save(out_path, "JPEG", quality=86, optimize=True)
    return sheet.size


# ---------------------------------------------------------------- main

def build(folder, out, per_sheet):
    photos = list_photos(folder)
    if not photos:
        msg = "Problem: no photos found in " + str(folder) + " (looked for jpg, png, heic, tif, webp at the top level)."
        subs = subfolders_with_photos(folder)
        if subs:
            msg += " Photos are in these subfolders: " + ", ".join(f"{name} ({count})" for name, count in subs)
            msg += ". Point me at one of those."
        raise Problem(msg)

    work_dir = folder / WORK_DIR
    work_dir.mkdir(exist_ok=True)
    if out is None:
        out_base = work_dir / "contact-sheet"
    else:
        out = Path(out)
        if not out.is_absolute():
            out = folder / out
        if out.is_dir() or out.suffix == "":
            out.mkdir(parents=True, exist_ok=True)
            out_base = out / "contact-sheet"
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            out_base = out.with_suffix("")

    entries, thumbs = [], []
    long_side = 380
    for i, path in enumerate(photos, start=1):
        im, note, (w, h) = open_photo(path, work_dir, preview_size=long_side * 2)
        entry = {"index": i, "file": path.name, "note": note}
        if im is None:
            entry.update({"width": 0, "height": 0, "orientation": "?", "brightness": None, "warmth": None, "detail": None})
            thumbs.append(None)
        else:
            entry.update({"width": w, "height": h, "orientation": orientation_word(w, h)})
            entry.update(measure(im))
            thumb = im.convert("RGB")
            thumb.thumbnail((long_side, long_side), RESAMPLE)
            thumbs.append(thumb)
            im.close()
        entries.append(entry)

    pages = [entries[i:i + per_sheet] for i in range(0, len(entries), per_sheet)]
    sheet_paths = []
    for p, page in enumerate(pages, start=1):
        if len(pages) == 1:
            out_path = out_base.with_name(out_base.name + ".jpg")
            title = f"{folder.name}: {len(entries)} photos"
        else:
            out_path = out_base.with_name(f"{out_base.name}-{p}.jpg")
            title = f"{folder.name}: {len(entries)} photos, sheet {p} of {len(pages)} (photos {page[0]['index']} to {page[-1]['index']})"
        page_thumbs = thumbs[(p - 1) * per_sheet: (p - 1) * per_sheet + len(page)]
        size = draw_sheet(page, page_thumbs, title, out_path, long_side)
        sheet_paths.append((out_path, size, page[0]["index"], page[-1]["index"]))

    info = {
        "folder": str(folder), "made": datetime.now().isoformat(timespec="seconds"),
        "sheets": [str(s[0]) for s in sheet_paths], "photos": entries,
    }
    with open(work_dir / "contact-sheet.json", "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2)
    return entries, sheet_paths, work_dir


def report(entries, sheet_paths, work_dir, folder):
    for path, size, first, last in sheet_paths:
        span = f" (photos {first} to {last})" if len(sheet_paths) > 1 else ""
        print(f"Wrote {path} ({size[0]}x{size[1]}){span}")
    print(f"Wrote {work_dir / 'contact-sheet.json'} (the numbers below, for carousel.py and stories.py)")
    print()
    opened = [e for e in entries if e["width"]]
    print(f"{len(entries)} photos in {folder}")
    print(f"{'#':>3}  {'file':<34} {'shape':<10} {'pixels':<11} {'brightness':<14} {'warmth':<13} detail")
    for e in entries:
        if not e["width"]:
            print(f"{e['index']:>3}  {e['file']:<34} {e['note']}")
            continue
        b, w, d = e["brightness"], e["warmth"], e["detail"]
        line = (f"{e['index']:>3}  {e['file']:<34} {e['orientation']:<10} {e['width']}x{e['height']:<6} "
                f"{b:>3} {brightness_word(b):<10} {w:>+4} {warmth_word(w):<8} {d:>3} {detail_word(d)}")
        if e["note"]:
            line += "   " + e["note"]
        print(line)
    print()
    print("brightness 0-100: dark under 35, bright over 65. warmth: minus is cool (blue), plus is warm (gold). "
          "detail: calm under 30, busy over 50 (rough; film grain reads as detail).")
    if opened:
        shapes = {}
        for e in opened:
            shapes[e["orientation"]] = shapes.get(e["orientation"], 0) + 1
        bright = sum(1 for e in opened if e["brightness"] > 65)
        dark = sum(1 for e in opened if e["brightness"] < 35)
        warm = sum(1 for e in opened if e["warmth"] > 6)
        cool = sum(1 for e in opened if e["warmth"] < -4)
        busy = sum(1 for e in opened if e["detail"] > 50)
        calm = sum(1 for e in opened if e["detail"] < 30)
        print("Set at a glance: " + ", ".join(f"{v} {k}" for k, v in shapes.items())
              + f"; {bright} bright, {dark} dark; {warm} warm, {cool} cool; {busy} busy, {calm} calm.")
    subs = subfolders_with_photos(folder)
    if subs:
        print("Also found photos in subfolders (not on this sheet): "
              + ", ".join(f"{name} ({count})" for name, count in subs))
    skipped = [e for e in entries if not e["width"]]
    if skipped:
        print(f"{len(skipped)} file(s) could not be opened; they keep their numbers so nothing shifts.")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 epilog="Example: python3 contact_sheet.py \"/Users/nicole/Sessions/Kira beach\"")
    ap.add_argument("folder", help="the session folder with the photos in it")
    ap.add_argument("--out", help="where to write the sheet (default: <folder>/_assistant/contact-sheet.jpg)")
    ap.add_argument("--max", type=int, default=40, help="photos per sheet before it splits into pages (default 40)")
    ap.add_argument("--debug", action="store_true", help="show full details if something unexpected goes wrong")
    args = ap.parse_args()

    try:
        folder = Path(args.folder).expanduser()
        if not folder.exists():
            raise Problem(f"Problem: there is no folder at {folder}. Check the path (and that the folder is connected).")
        if not folder.is_dir():
            raise Problem(f"Problem: {folder} is a file, not a folder. Give me the folder the photos are in.")
        if args.max < 1:
            raise Problem("Problem: --max needs to be 1 or more.")
        entries, sheet_paths, work_dir = build(folder.resolve(), args.out, args.max)
        report(entries, sheet_paths, work_dir, folder.resolve())
        return 0
    except Problem as e:
        print(str(e))
        return 1
    except Exception as e:  # noqa: BLE001 - anything else: one line, details on request
        if args.debug:
            traceback.print_exc()
        print(f"Unexpected problem: {type(e).__name__}: {e}. Run again with --debug for details.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
