#!/usr/bin/env python3
"""One contact sheet for Claude's one look: a row per time-gap group, a few
previews each, the group number drawn in the corner. Written as
_studio/groups-sheet.png with nothing installed on a Mac: `sips` (on every Mac)
turns each preview into a small uncompressed BMP, and this file lays them out and
writes the PNG with Python's own zlib. On a PC the small copies come from
pictures.py (Pillow); the layout and the PNG are the same.

    python3 sheet.py "<session folder>" [--thumb 220] [--per-row 4]

Rule 6 in practice: 4,000 photos become one image for the model to read.
Every contact sheet the Assistant draws (this one, the sneak-peek pages, the reel's
sheet, the drop box's sheet) gets its small copies from thumb() below.
Exit codes: 0 done, 1 this computer cannot make the small copies yet (it says why).
"""
import argparse
import json
import struct
import sys
import zlib
from pathlib import Path
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
import pictures  # noqa: E402  (every small picture, on a Mac or a PC)
this_computer.utf8_output()

# a tiny 5x7 font, just digits, for the row numbers
DIGITS = {
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
}

# Capital letters and a few marks in the same 5x7 font, so a page can carry a few words beside a number (the
# close-look pages say what the Mac saw in each face). Lowercase is drawn as capitals; anything else is a space.
LETTERS = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "10001", "11001", "10101", "10011", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ",": ["00000", "00000", "00000", "00000", "01100", "00100", "01000"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "?": ["01110", "10001", "00001", "00010", "00100", "00000", "00100"],
    "'": ["00100", "00100", "01000", "00000", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
    "\u00b7": ["00000", "00000", "00000", "01100", "01100", "00000", "00000"],
}


# Kept under its old name: the BMP reader lives in pictures.py now, beside the Mac's sips call that makes the BMP.
bmp_pixels = pictures.bmp_pixels


def thumb(src, size, tmp):
    """(width, height, rows of RGB bytes) for a small copy of the photo, its long edge `size`, or None.
    On a Mac: sips to a small BMP at tmp, read back, exactly as before. On a PC: Pillow (pictures.py)."""
    return pictures.thumb_rows(src, size, tmp)


def write_png(path, w, h, rows):
    raw = b"".join(b"\x00" + r for r in rows)
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    Path(path).write_bytes(png)


class Canvas:
    def __init__(self, w, h, bg=(24, 24, 24)):
        self.w, self.h = w, h
        self.rows = [bytearray(bytes(bg) * w) for _ in range(h)]

    def paste(self, x0, y0, w, h, rows):
        for y in range(h):
            if 0 <= y0 + y < self.h:
                x1 = min(w, self.w - x0)
                if x1 > 0:
                    self.rows[y0 + y][x0 * 3:(x0 + x1) * 3] = rows[y][:x1 * 3]

    def rect(self, x0, y0, w, h, color):
        for y in range(y0, min(y0 + h, self.h)):
            self.rows[y][x0 * 3:(x0 + w) * 3] = bytes(color) * min(w, self.w - x0)

    def text(self, x0, y0, s, scale=3, color=(255, 255, 255)):
        for ch in s:
            glyph = DIGITS.get(ch) or LETTERS.get(ch.upper())
            if glyph:
                for gy, line in enumerate(glyph):
                    for gx, bit in enumerate(line):
                        if bit == "1":
                            self.rect(x0 + gx * scale, y0 + gy * scale, scale, scale, color)
            x0 += 6 * scale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--thumb", type=int, default=220, help="longest edge of each preview on the sheet")
    ap.add_argument("--per-row", type=int, default=4)
    a = ap.parse_args()
    ok, words = pictures.ready()
    if not ok:
        print(f"STOP: {words}", flush=True)
        return 1
    studio = Path(a.session) / "_studio"
    groups = json.loads((studio / "groups.json").read_text(encoding="utf-8"))["groups"]
    tmp = studio / "groups" / ".sheet-tmp.bmp"

    cell_w, cell_h, label_w, gap = a.thumb, int(a.thumb * 0.68), 70, 6
    W = label_w + a.per_row * (cell_w + gap) + gap
    H = len(groups) * (cell_h + gap) + gap
    cv = Canvas(W, H)
    for i, g in enumerate(groups):
        y = gap + i * (cell_h + gap)
        cv.rect(0, y, label_w, cell_h, (40, 40, 40))
        cv.text(10, y + 12, f"{i + 1:02d}", scale=4, color=(240, 127, 90))
        for j, name in enumerate(g.get("previews", [])[:a.per_row]):
            t = thumb(studio / "groups" / name, a.thumb, tmp)
            if not t:
                continue
            w, h, rows = t
            x = label_w + gap + j * (cell_w + gap)
            # centre the thumb in its cell, cropping if taller than the cell
            dy = max(0, (cell_h - h) // 2)
            if h > cell_h:
                rows = rows[(h - cell_h) // 2:(h - cell_h) // 2 + cell_h]
                h = cell_h
            cv.paste(x + max(0, (cell_w - w) // 2), y + dy, w, h, rows)
    if tmp.exists():
        tmp.unlink()
    out = studio / "groups-sheet.png"
    write_png(out, W, H, cv.rows)
    print(f"{out}  ({W}x{H}, {len(groups)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
