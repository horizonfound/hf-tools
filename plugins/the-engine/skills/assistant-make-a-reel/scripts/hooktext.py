#!/usr/bin/env python3
"""The Assistant by Horizon Found. Draws on-screen text for a reel the way a designer would, not a subtitle tool.

What it does differently from a plain text overlay:
  - balances the line breaks so no line is left hanging with one word
  - sizes the type to the frame and keeps it inside Instagram's safe zones
  - looks at the frame behind the text and picks the quietest spot (never across a face if there is a plainer area)
  - picks the text color for that spot, and adds a soft gradient scrim only when the background is bright
  - renders at 2x and downsamples, so the edges stay crisp after video compression
  - three styles: editorial (serif), clean (sans), label (sans on a dark pill, the Instagram-native look)

Needs Pillow and numpy. Nothing to install.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
SS = 2  # supersample

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent.parent.parent / "shared" / "fonts"
FONT_FILES = {
    "cormorant": "CormorantGaramond-Medium.ttf",
    "cormorant italic": "CormorantGaramond-MediumItalic.ttf",
    "cormorant light": "CormorantGaramond-Light.ttf",
    "cormorant light italic": "CormorantGaramond-LightItalic.ttf",
    "cormorant regular": "CormorantGaramond-Regular.ttf",
    "cormorant regular italic": "CormorantGaramond-Italic.ttf",
    "cormorant semibold": "CormorantGaramond-SemiBold.ttf",
    "cormorant semibold italic": "CormorantGaramond-SemiBoldItalic.ttf",
    "montserrat": "Montserrat-Regular.ttf",
    "montserrat semibold": "Montserrat-SemiBold.ttf",
    "dm sans": "DMSans-Regular.ttf",
    "dm sans semibold": "DMSans-SemiBold.ttf",
    "inter": "Inter-Regular.ttf",
    "inter bold": "Inter-Bold.ttf",
    "fraunces": "Fraunces-Regular.ttf",
    "fraunces italic": "Fraunces-Italic.ttf",
}

STYLES = {
    # headline font, size at 1080 wide, leading, letter spacing (em), kicker font
    "editorial": {"font": "cormorant italic", "size": 96, "min_size": 72, "leading": 1.08, "tracking": 0.0,
                  "kicker_font": "montserrat semibold", "kicker_size": 26, "kicker_tracking": 0.32, "maxw": 0.84},
    "clean": {"font": "montserrat semibold", "size": 58, "min_size": 44, "leading": 1.22, "tracking": 0.0,
              "kicker_font": "montserrat", "kicker_size": 22, "kicker_tracking": 0.28, "maxw": 0.82},
    "label": {"font": "inter bold", "size": 50, "min_size": 40, "leading": 1.5, "tracking": 0.0,
              "kicker_font": None, "kicker_size": 0, "kicker_tracking": 0, "maxw": 0.80},
}

INK = (43, 36, 32)
CREAM = (250, 248, 243)


def font_file(name, fallback="cormorant italic"):
    """Resolve a friendly font name (or a path) to a file. Never falls back to the ugly built-in bitmap font."""
    if not name:
        name = fallback
    p = Path(str(name)).expanduser()
    if p.suffix.lower() in (".ttf", ".otf") and p.exists():
        return p
    key = str(name).lower().strip()
    if key in FONT_FILES:
        return FONTS / FONT_FILES[key]
    # loose match: "Cormorant Garamond Italic" -> cormorant italic
    words = [w for w in key.replace("garamond", "").split() if w]
    best = None
    for k in FONT_FILES:
        if all(w in k.split() for w in words):
            if best is None or len(k) < len(best):
                best = k
    if best:
        return FONTS / FONT_FILES[best]
    raise ValueError(f"I don't have a font called {name}. Bundled: " + ", ".join(sorted(FONT_FILES)))


def hex_to_rgb(s):
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def _wrap(words, font, draw, limit, tracking_px):
    lines, cur = [], []
    for w in words:
        trial = cur + [w]
        if _width(" ".join(trial), font, draw, tracking_px) <= limit or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = [w]
    if cur:
        lines.append(cur)
    return [" ".join(l) for l in lines]


def _width(text, font, draw, tracking_px):
    return draw.textlength(text, font=font) + tracking_px * max(0, len(text) - 1)


def balance(text, font, draw, maxw, tracking_px=0.0):
    """Wrap like a designer: fewest lines that fit, then even them out so no line hangs with one short word."""
    out = []
    for para in text.replace(" / ", "\n").split("\n"):
        words = para.split()
        if not words:
            continue
        greedy = _wrap(words, font, draw, maxw, tracking_px)
        n = len(greedy)
        if n == 1:
            out.extend(greedy)
            continue
        # binary search the narrowest limit that still gives n lines -> balanced
        lo, hi = max(_width(w, font, draw, tracking_px) for w in words), maxw
        best = greedy
        for _ in range(18):
            mid = (lo + hi) / 2
            trial = _wrap(words, font, draw, mid, tracking_px)
            if len(trial) <= n:
                best, hi = trial, mid
            else:
                lo = mid
        out.extend(best)
    return out


def region_stats(frame, box):
    """Mean luminance, busyness (edge energy) and skin share of the frame inside box=(x0,y0,x1,y1) at 1080x1920.
    Skin share is a plain YCbCr skin-tone test: good enough to keep text off faces and hands without any ML."""
    if frame is None:
        return 0.5, 0.0, 0.0
    small = frame.convert("RGB").resize((W // 4, H // 4))
    g = np.asarray(small.convert("L"), dtype=np.float32) / 255.0
    ycc = np.asarray(small.convert("YCbCr"), dtype=np.float32)
    x0, y0, x1, y1 = [int(v / 4) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(g.shape[1], max(x0 + 1, x1)), min(g.shape[0], max(y0 + 1, y1))
    r = g[y0:y1, x0:x1]
    if r.size < 4:
        return 0.5, 0.0, 0.0
    gy = np.abs(np.diff(r, axis=0)).mean() if r.shape[0] > 1 else 0.0
    gx = np.abs(np.diff(r, axis=1)).mean() if r.shape[1] > 1 else 0.0
    cb = ycc[y0:y1, x0:x1, 1]
    cr = ycc[y0:y1, x0:x1, 2]
    skin = ((cb > 77) & (cb < 127) & (cr > 133) & (cr < 173)).mean()
    return float(r.mean()), float(gx + gy), float(skin)


def render(text, out, style="editorial", font=None, color="auto", position="auto", kicker=None, frame=None, size=None):
    """Draw the text to a transparent PNG at 1080x1920. Returns a dict describing what was decided."""
    st = STYLES.get(style, STYLES["editorial"])
    ff = font_file(font, st["font"])
    size = int(size or st["size"])
    min_size = st["min_size"]
    s = SS
    canvas = Image.new("RGBA", (W * s, H * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # the lower band sits beside Instagram's right-hand icon rail, so it gets a touch narrower
    def maxw_for(pos):
        return int(W * s * (st["maxw"] - (0.06 if pos == "lower" else 0.0)))

    # size the headline: start big, go down until it fits in 4 lines (3 for label style)
    max_lines = 3 if style == "label" else 4
    while True:
        fnt = ImageFont.truetype(str(ff), size * s)
        tracking = st["tracking"] * size * s
        lines = balance(text, fnt, draw, maxw_for("upper"), tracking)
        if len(lines) <= max_lines or size <= min_size:
            break
        size -= 4
    leading = int(size * s * st["leading"])
    ascent, descent = fnt.getmetrics()
    block_h = leading * (len(lines) - 1) + ascent + descent

    kick_font = kick_h = None
    if kicker and st["kicker_font"]:
        kick_font = ImageFont.truetype(str(font_file(st["kicker_font"])), st["kicker_size"] * s)
        kick_h = int(st["kicker_size"] * s * 1.0) + int(34 * s)  # kicker line plus the gap below it
        block_h += kick_h

    # candidate positions, in frame pixels (not supersampled), inside the safe zones
    top_safe, bottom_safe = 250, H - 300
    bh = block_h / s
    cands = {
        "upper": int(H * 0.165),
        "middle": int((H - bh) / 2),
        "lower": int(H * 0.79 - bh),
    }
    for k in cands:
        cands[k] = int(max(top_safe + 10, min(cands[k], bottom_safe - 10 - bh)))
    boxw = max(_width(l, fnt, draw, tracking) for l in lines) / s
    if position in cands:
        pos = position
    else:
        # the quietest band wins, and a band with a face or hands in it loses; upper is preferred when it is close
        scores = {}
        for k, y in cands.items():
            lum, busy, skin = region_stats(frame, ((W - boxw) / 2 - 40, y - 30, (W + boxw) / 2 + 40, y + bh + 30))
            scores[k] = busy + 0.45 * skin - (0.008 if k == "upper" else 0.0)
        pos = min(cands, key=lambda k: scores[k])
    y0 = cands[pos]
    lum, busy, skin = region_stats(frame, ((W - boxw) / 2 - 40, y0 - 30, (W + boxw) / 2 + 40, y0 + bh + 30))

    # color and scrim
    scrim = 0.0
    if style == "label":
        rgb = CREAM if color in ("auto", "", None) else hex_to_rgb(color)
    elif color in ("auto", "", None):
        if lum > 0.74 and busy < 0.05:
            rgb = INK          # bright, plain background (sky, sand, a wall): dark type looks expensive
        else:
            rgb = CREAM
            scrim = 0.0 if lum < 0.42 else min(0.38, 0.14 + (lum - 0.42) * 0.8)
    else:
        rgb = hex_to_rgb(color)
        if sum(rgb) / 3 > 140 and lum >= 0.42:
            scrim = min(0.38, 0.14 + (lum - 0.42) * 0.8)

    cy = (y0 + bh / 2) * s
    if scrim > 0:
        # a soft vertical gradient darkening, centered on the text, fading to nothing well above and below
        reach = int((bh / 2 + 340) * s)
        g = np.zeros((H * s, 1), dtype=np.float32)
        ys = np.arange(H * s, dtype=np.float32)
        d = np.abs(ys - cy)
        g[:, 0] = np.where(d < reach, 0.5 * (1 + np.cos(math.pi * d / reach)), 0.0)
        alpha = (g * 255 * scrim).astype(np.uint8)
        alpha = np.repeat(alpha, W * s, axis=1)
        layer = Image.new("RGBA", (W * s, H * s), (14, 12, 10, 0))
        layer.putalpha(Image.fromarray(alpha, "L"))
        canvas = Image.alpha_composite(canvas, layer)
        draw = ImageDraw.Draw(canvas)

    # text layer, drawn once, used for the shadow and the fill
    text_layer = Image.new("L", (W * s, H * s), 0)
    td = ImageDraw.Draw(text_layer)
    y = y0 * s
    if kick_font:
        kt = kicker.upper()
        ktrack = st["kicker_tracking"] * st["kicker_size"] * s
        kw = _width(kt, kick_font, td, ktrack)
        x = (W * s - kw) / 2
        for ch in kt:
            td.text((x, y), ch, font=kick_font, fill=255)
            x += td.textlength(ch, font=kick_font) + ktrack
        y += kick_h
    label_boxes = []
    for i, line in enumerate(lines):
        lw = _width(line, fnt, td, tracking)
        x = (W * s - lw) / 2
        if tracking:
            for ch in line:
                td.text((x, y + i * leading), ch, font=fnt, fill=255)
                x += td.textlength(ch, font=fnt) + tracking
        else:
            td.text((x, y + i * leading), line, font=fnt, fill=255)
        label_boxes.append((x, y + i * leading, x + lw, y + i * leading + ascent + descent))

    if style == "label":
        pad_x, pad_y, radius = int(26 * s), int(10 * s), int(16 * s)
        pill = Image.new("RGBA", (W * s, H * s), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pill)
        for (x0, by0, x1, by1) in label_boxes:
            pd.rounded_rectangle((x0 - pad_x, by0 - pad_y + int(descent * 0.35), x1 + pad_x, by1 + pad_y - int(descent * 0.2)),
                                 radius=radius, fill=(22, 19, 17, 196))
        canvas = Image.alpha_composite(canvas, pill)
    else:
        # one soft, wide shadow: reads as natural depth, never a smudge
        shadow = Image.new("RGBA", (W * s, H * s), (0, 0, 0, 0))
        sh_alpha = text_layer.filter(ImageFilter.GaussianBlur(14 * s))
        sh_alpha = sh_alpha.point(lambda v: int(v * (0.55 if rgb == CREAM else 0.22)))
        shadow.putalpha(sh_alpha)
        shadow = shadow.transform(shadow.size, Image.AFFINE, (1, 0, 0, 0, 1, -4 * s))
        canvas = Image.alpha_composite(canvas, shadow)

    fill = Image.new("RGBA", (W * s, H * s), rgb + (0,))
    fill.putalpha(text_layer)
    canvas = Image.alpha_composite(canvas, fill)
    canvas = canvas.resize((W, H), Image.LANCZOS)
    canvas.save(out)
    return {"lines": lines, "size": size, "position": pos, "color": "#%02x%02x%02x" % rgb, "scrim": round(scrim, 2),
            "band_luminance": round(lum, 2), "band_busy": round(busy, 3), "band_skin": round(skin, 2), "style": style, "font": ff.name,
            "block": [int((W - boxw) / 2), int(y0), int((W + boxw) / 2), int(y0 + bh)]}


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="Render reel text to a transparent 1080x1920 PNG.")
    ap.add_argument("text")
    ap.add_argument("--out", default="hook.png")
    ap.add_argument("--style", default="editorial", choices=sorted(STYLES))
    ap.add_argument("--font", default=None)
    ap.add_argument("--color", default="auto")
    ap.add_argument("--position", default="auto", choices=["auto", "upper", "middle", "lower"])
    ap.add_argument("--kicker", default=None)
    ap.add_argument("--frame", default=None, help="a still of the frame behind the text, for placement and color")
    a = ap.parse_args()
    frame = Image.open(a.frame).convert("RGB").resize((W, H)) if a.frame else None
    print(json.dumps(render(a.text, a.out, a.style, a.font, a.color, a.position, a.kicker, frame), indent=1))
