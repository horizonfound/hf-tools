#!/usr/bin/env python3
"""The Assistant by Horizon Found: exports a carousel, in order, ready to post.

Takes the photos you chose (by their contact-sheet numbers or filenames), in
the order you want, and writes them as 1080x1350 (4:5) JPEGs named 01.jpg,
02.jpg ... into <folder>/_assistant/carousel/. The crop is centered with a
little extra room at the top, because faces usually sit high. With
--cover-text, the first photo becomes the cover: the line is set in the font
and color you give, two lines at most, in the quietest third of the frame,
with a soft shadow so it reads. Originals are never touched.

    python3 carousel.py --folder <folder> --order 3,1,7,2
        [--cover-text "..."] [--sub-text "..."] [--font Cormorant] [--small-font Montserrat]
        [--text-color "#F5F4ED"] [--text-position auto|upper|middle|lower]
        [--fit crop|pad] [--bg "#F5F4ED"] [--out _assistant/carousel]

Exit codes: 0 wrote the carousel, 1 something expected went wrong (bad order,
missing photo, text too long), 2 something unexpected (run again with --debug).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat
except ImportError:
    print("Problem: the Pillow image library is missing (python3 -m pip install pillow).")
    sys.exit(1)

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_IN_PILLOW = True
except ImportError:
    HEIF_IN_PILLOW = False

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".webp"}
HEIC_EXTS = {".heic", ".heif"}
WORK_DIR = "_assistant"
CONVERTED_DIR = ".converted"
FONTS_DIR = Path(__file__).resolve().parents[3] / "shared" / "fonts"
RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS

FRAME_W, FRAME_H = 1080, 1350      # Instagram 4:5
TOP_BIAS = 0.40                    # 0.5 would be dead center; a little less keeps heads in
JPEG_QUALITY = 92
MAX_SLIDES = 20                    # Instagram's limit


class Problem(Exception):
    """An expected problem with a friendly one-line message."""


# ---------------------------------------------------------------- folder listing (same as contact_sheet.py)

def natural_key(path):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def list_photos(folder):
    photos = []
    for path in folder.iterdir():
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() in IMAGE_EXTS:
            photos.append(path)
    photos.sort(key=natural_key)
    return photos


# ---------------------------------------------------------------- opening photos (same as contact_sheet.py)

_MAGICK = None


def imagemagick():
    global _MAGICK
    if _MAGICK is None:
        _MAGICK = ""
        for name in ("magick", "convert"):
            exe = shutil.which(name)
            if not exe:
                continue
            try:
                out = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=20).stdout
            except (OSError, subprocess.SubprocessError):
                continue
            if "ImageMagick" in out:
                _MAGICK = exe
                break
    return _MAGICK or None


def convert_heic(path, work_dir):
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


def photo_source(path, work_dir):
    """The file to actually decode: the photo itself, or its converted JPEG for a HEIC."""
    if path.suffix.lower() in HEIC_EXTS and not HEIF_IN_PILLOW:
        source = convert_heic(path, work_dir)
        if source is None:
            raise Problem(f"Problem: {path.name} is a HEIC and I could not convert it here. "
                          "Export it as a JPEG and try again.")
        return source
    return path


def check_photo(path, work_dir):
    """Make sure a photo can be opened before anything gets written (cheap: header only)."""
    source = photo_source(path, work_dir)
    try:
        with Image.open(source) as im:
            return im.size
    except (OSError, ValueError, SyntaxError):
        raise Problem(f"Problem: I could not open {path.name}. Is it a finished photo (jpg, png, heic)?")


def open_photo(path, work_dir):
    """Open a photo at full size, the right way up, as RGB. Raises Problem if it cannot."""
    source = photo_source(path, work_dir)
    try:
        im = Image.open(source)
        im = ImageOps.exif_transpose(im)
        icc = im.info.get("icc_profile")
        if im.mode != "RGB":
            im = im.convert("RGB")
        if icc:
            im.info["icc_profile"] = icc
        return im
    except (OSError, ValueError, SyntaxError):
        raise Problem(f"Problem: I could not open {path.name}. Is it a finished photo (jpg, png, heic)?")


# ---------------------------------------------------------------- picking the photos

def resolve_order(folder, order_text, work_dir):
    """Turn '3,1,7' or 'kira-03.jpg,kira-01.jpg' into photo paths, using the contact sheet's numbers."""
    tokens = [t.strip() for t in re.split(r"[,\s]+", order_text) if t.strip()]
    if not tokens:
        raise Problem("Problem: --order is empty. Give me the photo numbers in the order you want, like 3,1,7,2.")
    listing = list_photos(folder)
    numbered = {}
    sheet = work_dir / "contact-sheet.json"
    if sheet.exists():
        try:
            with open(sheet, encoding="utf-8") as fh:
                for entry in json.load(fh).get("photos", []):
                    numbered[int(entry["index"])] = folder / entry["file"]
        except (OSError, ValueError, KeyError, TypeError):
            numbered = {}
    if not numbered:
        numbered = {i: p for i, p in enumerate(listing, start=1)}
    by_name = {p.name.lower(): p for p in listing}

    chosen = []
    for token in tokens:
        if token.isdigit():
            path = numbered.get(int(token))
            if path is None or not path.exists():
                raise Problem(f"Problem: there is no photo number {token} on the contact sheet "
                              f"(it has {len(numbered)}). Run contact_sheet.py again if the folder changed.")
        else:
            path = by_name.get(token.lower()) or (Path(token).expanduser() if Path(token).expanduser().is_file() else None)
            if path is None:
                raise Problem(f"Problem: I could not find a photo called {token} in {folder}.")
        chosen.append(path)
    if len(chosen) > MAX_SLIDES:
        raise Problem(f"Problem: that is {len(chosen)} photos; Instagram allows {MAX_SLIDES} in a carousel. Pick fewer.")
    return chosen


# ---------------------------------------------------------------- frames

def crop_to_frame(im, fit, bg):
    """Return (frame, note): the photo as 1080x1350, cropped (top-biased) or padded on a color."""
    w, h = im.size
    if fit == "pad":
        scale = min(FRAME_W / w, FRAME_H / h)
        new = (max(1, round(w * scale)), max(1, round(h * scale)))
        frame = Image.new("RGB", (FRAME_W, FRAME_H), bg)
        frame.paste(im.resize(new, RESAMPLE), ((FRAME_W - new[0]) // 2, (FRAME_H - new[1]) // 2))
        note = "padded" + (" and upscaled" if scale > 1 else "")
        return frame, note
    target = FRAME_W / FRAME_H
    if w / h > target:                       # too wide: trim the sides evenly
        new_w = round(h * target)
        x0 = (w - new_w) // 2
        box = (x0, 0, x0 + new_w, h)
        how = f"trimmed {w - new_w} px off the sides"
    else:                                    # too tall: trim top and bottom, keeping more of the top
        new_h = round(w / target)
        y0 = round((h - new_h) * TOP_BIAS)
        box = (0, y0, w, y0 + new_h)
        how = f"trimmed {y0} px off the top and {h - new_h - y0} px off the bottom"
    crop = im.crop(box)
    note = how
    if crop.size[0] < FRAME_W:
        note += f", upscaled from {crop.size[0]}x{crop.size[1]}"
    if crop.size[0] < 700:
        note += " (small original; it may look soft)"
    return crop.resize((FRAME_W, FRAME_H), RESAMPLE), note


# ---------------------------------------------------------------- text in the look

def parse_hex(value, what):
    s = value.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6 or any(c not in "0123456789abcdefABCDEF" for c in s):
        raise Problem(f"Problem: {what} should be a hex color like #F5F4ED, not '{value}'.")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def font_file(name):
    """Find a font in the shared fonts folder by a friendly name ('Cormorant', 'Montserrat SemiBold')."""
    given = Path(name).expanduser()
    if given.suffix.lower() in (".ttf", ".otf") and given.is_file():
        return given
    if not FONTS_DIR.is_dir():
        raise Problem(f"Problem: the shared fonts folder is missing at {FONTS_DIR}.")
    files = sorted(list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf")))
    tokens = [t for t in re.split(r"[\s_\-]+", name.lower()) if t]
    matches = [f for f in files if all(t in f.stem.lower() for t in tokens)]
    if not matches:
        names = ", ".join(f.stem for f in files) or "none"
        raise Problem(f"Problem: no font called '{name}' in the shared fonts. Fonts there: {names}.")

    def rank(f):
        stem = f.stem.lower()
        if "italic" in stem and "italic" not in tokens:
            return 3
        return 0 if "light" in stem else 1 if "regular" in stem else 2
    matches.sort(key=lambda f: (rank(f), f.name))
    return matches[0]


def text_width(font, text):
    try:
        return font.getlength(text)
    except AttributeError:
        return font.getbbox(text)[2]


def wrap_words(words, font, max_width):
    lines, current = [], words[0]
    for word in words[1:]:
        trial = current + " " + word
        if text_width(font, trial) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def wrap_lines(text, font, max_width):
    """Word wrap with balanced lines (no one-word last line). A real newline, a typed
    backslash-n, or ' / ' forces a line break."""
    lines = []
    for para in text.replace("\\n", "\n").replace(" / ", "\n").split("\n"):
        words = para.split()
        if not words:
            continue
        best = wrap_words(words, font, max_width)
        if len(best) >= 2:
            widths = [text_width(font, line) for line in best]
            best_gap = max(widths) - min(widths)
            width = max_width
            while width > max_width * 0.55:
                width -= max_width * 0.04
                trial = wrap_words(words, font, width)
                if len(trial) != len(best):
                    break
                widths = [text_width(font, line) for line in trial]
                if max(widths) - min(widths) < best_gap:
                    best, best_gap = trial, max(widths) - min(widths)
        lines.extend(best)
    return lines


def fit_text(text, path, max_width, max_lines, start_size, min_size):
    """Largest size from start_size down at which the text fits in max_lines. Raises Problem if it never does."""
    size = start_size
    while True:
        font = ImageFont.truetype(str(path), size)
        lines = wrap_lines(text, font, max_width)
        fits = len(lines) <= max_lines and all(text_width(font, line) <= max_width for line in lines)
        if fits:
            return font, lines, size
        if size <= min_size:
            raise Problem(f"Problem: that line is too long to fit in {max_lines} lines at a readable size. "
                          "Try something shorter.")
        size = max(min_size, size - 4)


def quiet_box(im, block_w, block_h, zone, text_rgb, position="auto"):
    """Where to put a text block so it reads and stays off the person.

    zone is (top, bottom) in pixels the block must stay inside. position is 'auto' or one of
    'upper', 'middle', 'lower' to force a third. Returns (x, y, where). Scored on a quarter-size
    copy: fine detail (faces, lettering, leaves), the busiest patch inside the block, bigger
    shapes (a body against the background), how far the tone sits from the text color, and a
    nudge away from the center of the frame, where the person usually is.
    """
    scale = 4
    gray = im.convert("L")
    gray = gray.resize((max(1, gray.width // scale), max(1, gray.height // scale)), RESAMPLE)
    detail = ImageChops.difference(gray, gray.filter(ImageFilter.GaussianBlur(2)))
    shapes = ImageChops.difference(gray, gray.filter(ImageFilter.GaussianBlur(10)))
    text_luma = 0.299 * text_rgb[0] + 0.587 * text_rgb[1] + 0.114 * text_rgb[2]
    x = (im.width - block_w) // 2
    top, bottom = zone
    span = bottom - top
    names = ["upper", "middle", "lower"]
    best = None
    for i, name in enumerate(names):
        if position != "auto" and name != position:
            continue
        third_top = top + span * i / 3
        third_bottom = top + span * (i + 1) / 3
        for k in (0.0, 0.5, 1.0):
            y = third_top + k * (third_bottom - third_top - block_h)
            y = int(max(top, min(bottom - block_h, y)))
            box = (x // scale, y // scale, (x + block_w) // scale, (y + block_h) // scale)
            if box[3] <= box[1] or box[2] <= box[0]:
                continue
            region = gray.crop(box)
            fine = detail.crop(box)
            busy = ImageStat.Stat(fine).mean[0] / 255
            patch_w, patch_h = max(1, (box[2] - box[0]) // 6), max(1, (box[3] - box[1]) // 2)
            busiest = 0.0
            for a in range(6):
                for b in range(2):
                    patch = fine.crop((a * patch_w, b * patch_h, (a + 1) * patch_w, (b + 1) * patch_h))
                    busiest = max(busiest, ImageStat.Stat(patch).mean[0] / 255)
            shape = ImageStat.Stat(shapes.crop(box)).mean[0] / 255
            spread = ImageStat.Stat(region).stddev[0] / 255
            separation = abs(ImageStat.Stat(region).mean[0] - text_luma) / 255
            same_tone = max(0.0, 0.3 - separation) / 0.3          # text nearly the color of the background
            centered = 1 - abs((y + block_h / 2) - im.height / 2) / (im.height / 2)
            score = (busy * 8 + busiest * 3 + shape * 4 + (1 - separation) * 1.0 + same_tone * 2.5
                     + centered * 0.6 + spread * 1.0)
            if best is None or score < best[0]:
                best = (score, x, y, name, separation)
    if best is None:
        return x, top, "upper", 0.5
    return best[1], best[2], best[3], best[4]


def draw_tracked(draw, x_center, y, text, font, fill, tracking):
    """Draw text centered on x_center with extra space between letters (for small spaced caps)."""
    widths = [text_width(font, ch) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = x_center - total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking


def cover_sizes(width):
    """(max text width, largest size, smallest size) for a cover line on a frame this wide."""
    return int(width * 0.80), int(width * 0.085), int(width * 0.041)


def add_cover_text(frame, text, sub_text, font_path, small_font_path, color, zone=None, position="auto"):
    """Set the cover line (two lines max) and an optional small spaced-caps line under it."""
    max_width, biggest, smallest = cover_sizes(frame.width)
    font, lines, size = fit_text(text, font_path, max_width, 2, biggest, smallest)
    leading = int(size * 1.12)
    block_h = leading * len(lines)
    block_w = int(max(text_width(font, line) for line in lines))
    sub_font, sub_lines = None, []
    if sub_text:
        sub_size = max(20, int(size * 0.30))
        sub_font = ImageFont.truetype(str(small_font_path), sub_size)
        sub_lines = [line.upper() for line in wrap_lines(sub_text, sub_font, max_width)][:2]
        block_h += int(size * 0.45) + len(sub_lines) * int(sub_size * 1.5)
    if zone is None:
        margin = int(frame.height * 0.07)
        zone = (margin, frame.height - margin)
    x, y, where, separation = quiet_box(frame, max(block_w, int(frame.width * 0.5)), block_h, zone, color, position)

    # soft shadow under the letters (a little stronger when the background is close to the text
    # color), then the letters in the brand color. Never a box over the photo.
    alpha = int(min(215, 140 + (1 - separation) * 75))
    shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    cx = frame.width / 2
    yy = y
    for line in lines:
        sd.text((cx - text_width(font, line) / 2 + 1, yy + 2), line, font=font, fill=(0, 0, 0, alpha))
        yy += leading
    if sub_lines:
        yy += int(size * 0.45)
        tracking = max(2, int(sub_font.size * 0.18))
        for line in sub_lines:
            draw_tracked(sd, cx + 1, yy + 2, line, sub_font, (0, 0, 0, alpha), tracking)
            yy += int(sub_font.size * 1.5)
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(2, size / 9)))
    out = Image.alpha_composite(frame.convert("RGBA"), shadow)
    d = ImageDraw.Draw(out)
    yy = y
    for line in lines:
        d.text((cx - text_width(font, line) / 2, yy), line, font=font, fill=color + (255,))
        yy += leading
    if sub_lines:
        yy += int(size * 0.45)
        tracking = max(2, int(sub_font.size * 0.18))
        for line in sub_lines:
            draw_tracked(d, cx, yy, line, sub_font, color + (255,), tracking)
            yy += int(sub_font.size * 1.5)
    result = out.convert("RGB")
    if frame.info.get("icc_profile"):
        result.info["icc_profile"] = frame.info["icc_profile"]
    return result, where, len(lines), size


# ---------------------------------------------------------------- main

def build(args):
    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        raise Problem(f"Problem: there is no folder at {folder}. Check the path (and that the folder is connected).")
    folder = folder.resolve()
    work_dir = folder / WORK_DIR
    work_dir.mkdir(exist_ok=True)
    out_dir = Path(args.out).expanduser()
    if not out_dir.is_absolute():
        out_dir = folder / out_dir
    if out_dir.resolve() == folder or out_dir.resolve() in folder.parents:
        raise Problem("Problem: the output folder would sit on top of the originals. Use a folder inside _assistant.")
    text_color = parse_hex(args.text_color, "--text-color")
    bg = parse_hex(args.bg, "--bg")
    font_path = font_file(args.font) if args.cover_text else None
    small_font_path = font_file(args.small_font) if args.sub_text else None
    if args.sub_text and not args.cover_text:
        raise Problem("Problem: --sub-text only goes under a --cover-text line.")

    chosen = resolve_order(folder, args.order, work_dir)
    for path in chosen:                      # check everything first, so a problem never leaves a half export
        check_photo(path, work_dir)
    if args.cover_text:
        max_width, biggest, smallest = cover_sizes(FRAME_W)
        fit_text(args.cover_text, font_path, max_width, 2, biggest, smallest)

    out_dir.mkdir(parents=True, exist_ok=True)
    stale = [p for p in out_dir.iterdir() if re.fullmatch(r"\d\d\.jpg", p.name)]
    for p in stale:
        p.unlink()

    written = []
    for n, path in enumerate(chosen, start=1):
        im = open_photo(path, work_dir)
        frame, note = crop_to_frame(im, args.fit, bg)
        im.close()
        extra = ""
        if n == 1 and args.cover_text:
            frame, where, line_count, size = add_cover_text(frame, args.cover_text, args.sub_text,
                                                            font_path, small_font_path, text_color,
                                                            position=args.text_position)
            extra = f"; cover text in the {where} third, {line_count} line{'s' if line_count != 1 else ''} at {size} px"
        out_path = out_dir / f"{n:02d}.jpg"
        save_kwargs = {"quality": JPEG_QUALITY, "optimize": True}
        if frame.info.get("icc_profile"):
            save_kwargs["icc_profile"] = frame.info["icc_profile"]
        frame.save(out_path, "JPEG", **save_kwargs)
        written.append((out_path, path.name, note + extra))
    return out_dir, written, stale


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 epilog='Example: python3 carousel.py --folder "/Users/nicole/Sessions/Kira" '
                                        '--order 7,3,9,1,5 --cover-text "This time you\'re in it"')
    ap.add_argument("--folder", required=True, help="the session folder (the one contact_sheet.py looked at)")
    ap.add_argument("--order", required=True,
                    help="contact-sheet numbers (or filenames) in posting order, like 3,1,7,2; first one is the cover")
    ap.add_argument("--cover-text", default="", help="a line for the cover (two lines max; ' / ' forces a line break)")
    ap.add_argument("--sub-text", default="", help="a small spaced-caps line under the cover text")
    ap.add_argument("--font", default="Cormorant", help="headline font by name from shared/fonts (default Cormorant)")
    ap.add_argument("--small-font", default="Montserrat", help="font for --sub-text (default Montserrat)")
    ap.add_argument("--text-color", default="#F5F4ED", help="hex color for the text (default cream #F5F4ED)")
    ap.add_argument("--text-position", choices=("auto", "upper", "middle", "lower"), default="auto",
                    help="which third the cover text sits in (default auto picks the quietest)")
    ap.add_argument("--fit", choices=("crop", "pad"), default="crop",
                    help="crop fills the 4:5 frame (default); pad keeps the whole photo on a --bg color")
    ap.add_argument("--bg", default="#F5F4ED", help="background color for --fit pad (default cream)")
    ap.add_argument("--out", default=str(Path(WORK_DIR) / "carousel"),
                    help="where the frames go, inside the session folder (default _assistant/carousel)")
    ap.add_argument("--debug", action="store_true", help="show full details if something unexpected goes wrong")
    args = ap.parse_args()

    try:
        out_dir, written, stale = build(args)
    except Problem as e:
        print(str(e))
        return 1
    except Exception as e:  # noqa: BLE001
        if args.debug:
            traceback.print_exc()
        print(f"Unexpected problem: {type(e).__name__}: {e}. Run again with --debug for details.")
        return 2

    if stale:
        print(f"Cleared {len(stale)} frame(s) from an earlier export in {out_dir}")
    for out_path, source, note in written:
        print(f"Wrote {out_path.name}  from {source}  ({note})")
    print(f"{len(written)} frame{'s' if len(written) != 1 else ''} at {FRAME_W}x{FRAME_H} in {out_dir}")
    if len(written) == 1:
        print("Note: a carousel needs at least 2 photos; this is a single post as it stands.")
    elif len(written) > 10:
        print("Note: more than 10 slides; Instagram allows it, but most people stop swiping well before the end.")
    print("Upload them in number order. Nothing has been posted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
