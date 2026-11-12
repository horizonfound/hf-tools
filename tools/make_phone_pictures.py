#!/usr/bin/env python3
"""Make the two marked-up pictures for the "get a tap on your phone" page from Dustin's screenshots of the Claude
app (docs/phone-setup/): the bar with the button that opens the panel, and the Remote Control switch, each with a
coral ring and a number. Needs Pillow. Run again if the app's look changes and new screenshots are saved there.

    python3 tools/make_phone_pictures.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "phone-setup"
OUT = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "pictures"
CORAL = (212, 100, 63)


def mark(src, out, centre, radius, number, scale=2, pad=26):
    im = Image.open(src).convert("RGB")
    im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
    bg = im.getpixel((2, 2))
    canvas = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), bg)
    canvas.paste(im, (pad, pad))
    d = ImageDraw.Draw(canvas)
    cx, cy, r = centre[0] * scale + pad, centre[1] * scale + pad, radius * scale
    for k in range(5):   # a thick ring
        d.ellipse((cx - r - k, cy - r - k, cx + r + k, cy + r + k), outline=CORAL)
    # the number, in a filled dot on the ring's shoulder
    bx, by, br = cx + int(r * 0.78), cy - int(r * 0.78), 17
    d.ellipse((bx - br, by - br, bx + br, by + br), fill=CORAL)
    try:
        font = ImageFont.load_default(size=24)
    except TypeError:
        font = ImageFont.load_default()
    box = d.textbbox((0, 0), str(number), font=font)
    d.text((bx - (box[2] - box[0]) / 2 - box[0], by - (box[3] - box[1]) / 2 - box[1]), str(number), fill="white", font=font)
    canvas.save(out, optimize=True)
    print(out, canvas.size)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    mark(SRC / "top-bar.jpg", OUT / "phone-step-1.png", (66, 44), 30, 1)
    mark(SRC / "remote-control-row.jpg", OUT / "phone-step-2.png", (579, 33), 34, 2)
