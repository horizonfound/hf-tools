#!/usr/bin/env python3
"""One contact sheet for Claude's one look: a row per time-gap group, a few
previews each, the group number drawn in the corner. Written as
_studio/groups-sheet.png with nothing installed: `sips` (on every Mac) turns
each preview into a small uncompressed BMP, and this file lays them out and
writes the PNG with Python's own zlib.

    python3 sheet.py "<session folder>" [--thumb 220] [--per-row 4]

Rule 6 in practice: 4,000 photos become one image for the model to read.
"""
import argparse
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

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


def bmp_pixels(path):
    """(width, height, rows of RGB bytes) from a 24- or 32-bit uncompressed BMP."""
    d = Path(path).read_bytes()
    if d[:2] != b"BM":
        raise ValueError("not a BMP")
    off = struct.unpack_from("<I", d, 10)[0]
    w, h = struct.unpack_from("<ii", d, 18)
    bpp = struct.unpack_from("<H", d, 28)[0]
    if bpp not in (24, 32) or struct.unpack_from("<I", d, 30)[0] != 0:
        raise ValueError("unexpected BMP layout")
    top_down = h < 0
    h = abs(h)
    step = bpp // 8
    stride = (w * step + 3) & ~3
    rows = []
    for y in range(h):
        src = off + y * stride
        row = bytearray(w * 3)
        for x in range(w):
            b, g, r = d[src + x * step], d[src + x * step + 1], d[src + x * step + 2]
            row[x * 3:x * 3 + 3] = bytes((r, g, b))
        rows.append(bytes(row))
    if not top_down:
        rows.reverse()
    return w, h, rows


def thumb(src, size, tmp):
    """A small BMP of the preview, via sips."""
    r = subprocess.run(["sips", "-s", "format", "bmp", "-Z", str(size), str(src), "--out", str(tmp)], capture_output=True)
    if r.returncode != 0 or not tmp.exists():
        return None
    try:
        return bmp_pixels(tmp)
    except ValueError:
        return None


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
            glyph = DIGITS.get(ch)
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
    studio = Path(a.session) / "_studio"
    groups = json.loads((studio / "groups.json").read_text())["groups"]
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


if __name__ == "__main__":
    main()
