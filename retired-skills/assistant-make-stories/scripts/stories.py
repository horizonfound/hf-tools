#!/usr/bin/env python3
"""The Assistant by Horizon Found: renders Instagram story frames from a session folder.

Reads a small JSON list of frames (which photo, one line of text, which style)
and writes them as 1080x1920 PNGs named 01.png, 02.png ... into
<folder>/_assistant/stories/. Text always stays out of the top 250 px and the
bottom 300 px, where Instagram's own buttons sit. Originals are never touched,
and nothing is posted; the photographer posts the frames by hand.

    python3 stories.py --folder <folder> --frames spec.json
        [--font Cormorant] [--small-font Montserrat] [--text-color "#F5F4ED"]
        [--bg "#F5F4ED"] [--ink "#4E3624"] [--out _assistant/stories]

spec.json is a list like:
    [
      {"photo": "kira-07.jpg", "line": "We just played for two hours", "style": "photo-full"},
      {"photo": 3, "line": "the detail I keep coming back to", "style": "quiet"},
      {"photo": "kira-09.jpg", "line": "Two spots left this month", "style": "cream"}
    ]
photo: a filename in the folder, or its number from the contact sheet.
line: one short line in the photographer's voice (may be empty for a wordless frame).
style: photo-full (full-bleed photo, line in the safe zone), cream (photo as a rounded
card on the brand's cream, line under it), quiet (photo with a tiny line in a corner).
Optional per frame: "position": upper | middle | lower (photo-full), or
"corner": bottom-left | bottom-right | top-left | top-right (quiet).

Exit codes: 0 wrote the frames, 1 something expected went wrong (bad spec,
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

FRAME_W, FRAME_H = 1080, 1920
TOP_UI, BOTTOM_UI = 250, 300       # Instagram's own interface covers these bands
SAFE_PAD = 40                      # extra breathing room inside the safe zone
TOP_BIAS = 0.40
STYLES = ("photo-full", "cream", "quiet")
POSITIONS = ("auto", "upper", "middle", "lower")
CORNERS = ("auto", "bottom-left", "bottom-right", "top-left", "top-right")
MAX_FRAMES = 10


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


# ---------------------------------------------------------------- opening photos (same as carousel.py)

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
    if path.suffix.lower() in HEIC_EXTS and not HEIF_IN_PILLOW:
        source = convert_heic(path, work_dir)
        if source is None:
            raise Problem(f"Problem: {path.name} is a HEIC and I could not convert it here. "
                          "Export it as a JPEG and try again.")
        return source
    return path


def check_photo(path, work_dir):
    source = photo_source(path, work_dir)
    try:
        with Image.open(source) as im:
            return im.size
    except (OSError, ValueError, SyntaxError):
        raise Problem(f"Problem: I could not open {path.name}. Is it a finished photo (jpg, png, heic)?")


def open_photo(path, work_dir):
    source = photo_source(path, work_dir)
    try:
        im = Image.open(source)
        im = ImageOps.exif_transpose(im)
        if im.mode != "RGB":
            im = im.convert("RGB")
        return im
    except (OSError, ValueError, SyntaxError):
        raise Problem(f"Problem: I could not open {path.name}. Is it a finished photo (jpg, png, heic)?")


def resolve_photo(folder, token, work_dir):
    """A filename, a contact-sheet number, or a path, to a photo path in the folder."""
    token = str(token).strip()
    listing = list_photos(folder)
    if token.isdigit():
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
        path = numbered.get(int(token))
        if path is None or not path.exists():
            raise Problem(f"Problem: there is no photo number {token} on the contact sheet (it has {len(numbered)}).")
        return path
    by_name = {p.name.lower(): p for p in listing}
    path = by_name.get(token.lower())
    if path is None:
        candidate = Path(token).expanduser()
        if candidate.is_file():
            return candidate
        raise Problem(f"Problem: I could not find a photo called {token} in {folder}.")
    return path


# ---------------------------------------------------------------- text in the look (same as carousel.py)

def parse_hex(value, what):
    s = str(value).strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6 or any(c not in "0123456789abcdefABCDEF" for c in s):
        raise Problem(f"Problem: {what} should be a hex color like #F5F4ED, not '{value}'.")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def font_file(name):
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


def quiet_box(im, block_w, block_h, zone, text_rgb, position="auto", x_choices=None):
    """Where to put a text block so it reads and stays off the person (see carousel.py)."""
    scale = 4
    gray = im.convert("L")
    gray = gray.resize((max(1, gray.width // scale), max(1, gray.height // scale)), RESAMPLE)
    detail = ImageChops.difference(gray, gray.filter(ImageFilter.GaussianBlur(2)))
    shapes = ImageChops.difference(gray, gray.filter(ImageFilter.GaussianBlur(10)))
    text_luma = 0.299 * text_rgb[0] + 0.587 * text_rgb[1] + 0.114 * text_rgb[2]
    if x_choices is None:
        x_choices = [(im.width - block_w) // 2]
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
            for x in x_choices:
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
                same_tone = max(0.0, 0.3 - separation) / 0.3
                centered = 1 - abs((y + block_h / 2) - im.height / 2) / (im.height / 2)
                score = (busy * 8 + busiest * 3 + shape * 4 + (1 - separation) * 1.0 + same_tone * 2.5
                         + centered * 0.6 + spread * 1.0)
                if best is None or score < best[0]:
                    best = (score, x, y, name, separation)
    if best is None:
        return x_choices[0], top, "upper", 0.5
    return best[1], best[2], best[3], best[4]


def draw_tracked(draw, x_left, y, text, font, fill, tracking):
    x = x_left
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += text_width(font, ch) + tracking


def tracked_width(font, text, tracking):
    return sum(text_width(font, ch) for ch in text) + tracking * max(0, len(text) - 1)


def with_shadow(frame, draw_calls, size, separation):
    """Run draw_calls(draw, dx, dy, fill) twice: a blurred dark pass, then the real one."""
    alpha = int(min(215, 140 + (1 - separation) * 75))
    shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw_calls(ImageDraw.Draw(shadow), 1, 2, (0, 0, 0, alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(2, size / 9)))
    out = Image.alpha_composite(frame.convert("RGBA"), shadow)
    draw_calls(ImageDraw.Draw(out), 0, 0, None)
    return out.convert("RGB")


# ---------------------------------------------------------------- the three styles

def fill_frame(im, w, h):
    """Crop a photo to fill w x h, centered, keeping more of the top."""
    pw, ph = im.size
    target = w / h
    if pw / ph > target:
        new_w = round(ph * target)
        x0 = (pw - new_w) // 2
        crop = im.crop((x0, 0, x0 + new_w, ph))
    else:
        new_h = round(pw / target)
        y0 = round((ph - new_h) * TOP_BIAS)
        crop = im.crop((0, y0, pw, y0 + new_h))
    return crop.resize((w, h), RESAMPLE)


def style_photo_full(im, line, look, position):
    frame = fill_frame(im, FRAME_W, FRAME_H)
    if not line:
        return frame, "no text"
    max_width = int(FRAME_W * 0.78)
    font, lines, size = fit_text(line, look["font"], max_width, 3, int(FRAME_W * 0.068), int(FRAME_W * 0.042))
    leading = int(size * 1.15)
    block_w = int(max(text_width(font, l) for l in lines))
    block_h = leading * len(lines)
    zone = (TOP_UI + SAFE_PAD, FRAME_H - BOTTOM_UI - SAFE_PAD)
    x, y, where, separation = quiet_box(frame, max(block_w, FRAME_W // 2), block_h, zone, look["text"], position)
    cx = FRAME_W / 2

    def calls(draw, dx, dy, fill):
        yy = y
        for l in lines:
            draw.text((cx - text_width(font, l) / 2 + dx, yy + dy), l, font=font, fill=fill or look["text"] + (255,))
            yy += leading
    return with_shadow(frame, calls, size, separation), f"line in the {where} part, {len(lines)} line(s) at {size} px"


def style_cream(im, line, look):
    frame = Image.new("RGB", (FRAME_W, FRAME_H), look["bg"])
    zone_top, zone_bottom = TOP_UI + SAFE_PAD, FRAME_H - BOTTOM_UI - SAFE_PAD
    max_width = int(FRAME_W * 0.78)
    font, lines, size, block_h, gap = None, [], 0, 0, 0
    if line:
        font, lines, size = fit_text(line, look["font"], max_width, 3, int(FRAME_W * 0.05), int(FRAME_W * 0.036))
        leading = int(size * 1.2)
        block_h = leading * len(lines)
        gap = int(size * 1.1)
    card_max_w = FRAME_W - 2 * 90
    card_max_h = (zone_bottom - zone_top) - block_h - gap
    pw, ph = im.size
    scale = min(card_max_w / pw, card_max_h / ph)
    cw, ch = max(1, round(pw * scale)), max(1, round(ph * scale))
    card = im.resize((cw, ch), RESAMPLE)
    radius = 28
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=radius, fill=255)
    total_h = ch + gap + block_h
    top = zone_top + ((zone_bottom - zone_top) - total_h) // 2
    left = (FRAME_W - cw) // 2

    # a faint shadow so the card sits on the page instead of floating
    shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((left, top + 10, left + cw, top + ch + 10), radius=radius, fill=(0, 0, 0, 40))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    out = Image.alpha_composite(frame.convert("RGBA"), shadow).convert("RGB")
    out.paste(card, (left, top), mask)
    if lines:
        draw = ImageDraw.Draw(out)
        yy = top + ch + gap
        for l in lines:
            draw.text((FRAME_W / 2 - text_width(font, l) / 2, yy), l, font=font, fill=look["ink"])
            yy += int(size * 1.2)
        return out, f"card {cw}x{ch}, {len(lines)} line(s) at {size} px under it"
    return out, f"card {cw}x{ch}, no text"


def style_quiet(im, line, look, corner):
    frame = fill_frame(im, FRAME_W, FRAME_H)
    if not line:
        return frame, "no text"
    side = 72
    max_width = int(FRAME_W * 0.6)
    size = 26
    small = ImageFont.truetype(str(look["small_font"]), size)
    text = line.upper()
    tracking = max(2, int(size * 0.2))
    lines = wrap_lines(text, small, max_width)
    if len(lines) > 2 or any(tracked_width(small, l, tracking) > max_width for l in lines):
        raise Problem("Problem: a 'quiet' frame takes a tiny line, two short lines at most. Try something shorter.")
    leading = int(size * 1.7)
    block_w = int(max(tracked_width(small, l, tracking) for l in lines))
    block_h = leading * len(lines)
    zone_top, zone_bottom = TOP_UI + SAFE_PAD, FRAME_H - BOTTOM_UI - SAFE_PAD
    spots = {
        "bottom-left": (side, zone_bottom - block_h),
        "bottom-right": (FRAME_W - side - block_w, zone_bottom - block_h),
        "top-left": (side, zone_top),
        "top-right": (FRAME_W - side - block_w, zone_top),
    }
    if corner != "auto":
        x, y = spots[corner]
        where = corner
        separation = 0.5
    else:
        best = None
        for name, (x, y) in spots.items():
            score, sep = score_spot(frame, x, y, block_w, block_h, look["text"])
            if best is None or score < best[0]:
                best = (score, name, x, y, sep)
        _, where, x, y, separation = best

    def calls(draw, dx, dy, fill):
        yy = y
        for l in lines:
            xx = x if "left" in where else x + block_w - tracked_width(small, l, tracking)
            draw_tracked(draw, xx + dx, yy + dy, l, small, fill or look["text"] + (255,), tracking)
            yy += leading
    return with_shadow(frame, calls, size, separation), f"tiny line {where}"


def score_spot(frame, x, y, w, h, text_rgb):
    """Same scoring as quiet_box for one fixed box (used to compare corners)."""
    scale = 4
    gray = frame.convert("L").resize((frame.width // scale, frame.height // scale), RESAMPLE)
    detail = ImageChops.difference(gray, gray.filter(ImageFilter.GaussianBlur(2)))
    shapes = ImageChops.difference(gray, gray.filter(ImageFilter.GaussianBlur(10)))
    text_luma = 0.299 * text_rgb[0] + 0.587 * text_rgb[1] + 0.114 * text_rgb[2]
    box = (x // scale, y // scale, (x + w) // scale, (y + h) // scale)
    region = gray.crop(box)
    busy = ImageStat.Stat(detail.crop(box)).mean[0] / 255
    shape = ImageStat.Stat(shapes.crop(box)).mean[0] / 255
    spread = ImageStat.Stat(region).stddev[0] / 255
    separation = abs(ImageStat.Stat(region).mean[0] - text_luma) / 255
    same_tone = max(0.0, 0.3 - separation) / 0.3
    return busy * 8 + shape * 4 + (1 - separation) * 1.0 + same_tone * 2.5 + spread * 1.0, separation


# ---------------------------------------------------------------- spec

def load_spec(path):
    if not path.is_file():
        raise Problem(f"Problem: there is no frames file at {path}.")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as e:
        raise Problem(f"Problem: {path.name} is not valid JSON ({str(e)[:60]}).")
    if isinstance(data, dict):
        data = data.get("frames", data)
    if not isinstance(data, list) or not data:
        raise Problem("Problem: the frames file should be a list of frames, like "
                      '[{"photo": "kira-07.jpg", "line": "...", "style": "photo-full"}].')
    if len(data) > MAX_FRAMES:
        raise Problem(f"Problem: {len(data)} frames is a lot for one day; keep it to {MAX_FRAMES} or fewer.")
    frames = []
    for n, item in enumerate(data, start=1):
        if not isinstance(item, dict) or "photo" not in item:
            raise Problem(f"Problem: frame {n} needs a \"photo\" (a filename or its contact-sheet number).")
        style = str(item.get("style", "photo-full")).strip().lower()
        if style not in STYLES:
            raise Problem(f"Problem: frame {n} has style '{style}'; use photo-full, cream or quiet.")
        position = str(item.get("position", "auto")).strip().lower()
        if position not in POSITIONS:
            raise Problem(f"Problem: frame {n} has position '{position}'; use upper, middle or lower.")
        corner = str(item.get("corner", "auto")).strip().lower()
        if corner not in CORNERS:
            raise Problem(f"Problem: frame {n} has corner '{corner}'; use bottom-left, bottom-right, top-left or top-right.")
        frames.append({"photo": item["photo"], "line": str(item.get("line", "") or "").strip(),
                       "style": style, "position": position, "corner": corner})
    return frames


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
    spec_path = Path(args.frames).expanduser()
    if not spec_path.is_absolute() and not spec_path.exists():
        spec_path = folder / spec_path
    frames = load_spec(spec_path)
    look = {
        "font": font_file(args.font), "small_font": font_file(args.small_font),
        "text": parse_hex(args.text_color, "--text-color"), "bg": parse_hex(args.bg, "--bg"),
        "ink": parse_hex(args.ink, "--ink"),
    }
    for frame in frames:                       # check everything before writing anything
        frame["path"] = resolve_photo(folder, frame["photo"], work_dir)
        check_photo(frame["path"], work_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    stale = [p for p in out_dir.iterdir() if re.fullmatch(r"\d\d\.png", p.name)]
    for p in stale:
        p.unlink()
    written = []
    for n, frame in enumerate(frames, start=1):
        im = open_photo(frame["path"], work_dir)
        if frame["style"] == "photo-full":
            image, note = style_photo_full(im, frame["line"], look, frame["position"])
        elif frame["style"] == "cream":
            image, note = style_cream(im, frame["line"], look)
        else:
            image, note = style_quiet(im, frame["line"], look, frame["corner"])
        im.close()
        out_path = out_dir / f"{n:02d}.png"
        image.save(out_path, "PNG", optimize=False, compress_level=6)
        written.append((out_path, frame["style"], frame["path"].name, note))
    return out_dir, written, stale


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 epilog='Example: python3 stories.py --folder "/Users/nicole/Sessions/Kira" '
                                        "--frames _assistant/stories-spec.json")
    ap.add_argument("--folder", required=True, help="the session folder the photos are in")
    ap.add_argument("--frames", required=True, help="the JSON list of frames (see --help text above)")
    ap.add_argument("--font", default="Cormorant", help="headline font by name from shared/fonts (default Cormorant)")
    ap.add_argument("--small-font", default="Montserrat", help="font for the tiny 'quiet' line (default Montserrat)")
    ap.add_argument("--text-color", default="#F5F4ED", help="hex color for text on photos (default cream #F5F4ED)")
    ap.add_argument("--bg", default="#F5F4ED", help="hex background for 'cream' frames (default #F5F4ED)")
    ap.add_argument("--ink", default="#4E3624", help="hex color for text on 'cream' frames (default espresso #4E3624)")
    ap.add_argument("--out", default=str(Path(WORK_DIR) / "stories"),
                    help="where the frames go, inside the session folder (default _assistant/stories)")
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
    for out_path, style, source, note in written:
        print(f"Wrote {out_path.name}  {style:<10} from {source}  ({note})")
    print(f"{len(written)} frame{'s' if len(written) != 1 else ''} at {FRAME_W}x{FRAME_H} in {out_dir}")
    print("Post them by hand, in number order. Nothing has been posted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
