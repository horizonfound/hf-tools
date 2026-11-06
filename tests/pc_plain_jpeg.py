#!/usr/bin/env python3
"""Real JPEGs written in plain Python, and a pretend post kit made of them. A helper, not a test:
tests/pc_design.py and tests/pc_design_page.py use it, so the designer can be tried on a computer with no way of
making pictures at all (a Mac's own Python 3.9, a PC before Pillow is put in).

    jpeg(w, h, level=0, note="")       the bytes of a JPEG of one flat grey
    make_kit(content, name, photos=6)  a kit folder in Your Content holding that many small grey photos, with
                                       kit.json and sheet.json written by hand in the shapes kit.py writes

    python tests/pc_plain_jpeg.py out.jpg [width height]     writes one, to look at

Python 3.9, standard library only.
"""
import json
import struct
import sys
from pathlib import Path

_DC = {0: "00", 1: "010", 2: "011", 3: "100", 4: "101", 5: "110", 6: "1110"}     # the standard table's first codes


def jpeg(w, h, level=0, note=""):
    """A real JPEG of one flat grey, w by h, with nothing but Python: one channel, the standard table for the
    first number of each 8 x 8 block, and a two-word table for the rest (every block ends at once). level (0 to
    63) sets the grey; note goes in as a comment, so two pictures of one grey still differ."""
    def seg(marker, data):
        return b"\xff" + bytes([marker]) + struct.pack(">H", len(data) + 2) + data
    out = b"\xff\xd8" + seg(0xE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
    if note:
        out += seg(0xFE, note.encode("ascii", "replace"))
    out += seg(0xDB, b"\x00" + bytes([16] * 64))
    out += seg(0xC0, b"\x08" + struct.pack(">HH", h, w) + b"\x01\x01\x11\x00")
    out += seg(0xC4, b"\x00" + bytes([0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]) + bytes(range(12)))
    out += seg(0xC4, b"\x10" + bytes([0, 2] + [0] * 14) + b"\x00\xf0")
    out += seg(0xDA, b"\x01\x01\x00\x00\x3f\x00")
    blocks = ((w + 7) // 8) * ((h + 7) // 8)
    level = max(0, min(63, int(level)))
    bits = _DC[level.bit_length()] + (format(level, "b") if level else "") + "00" + "0000" * (blocks - 1)
    bits += "1" * (-len(bits) % 8)
    data = int(bits, 2).to_bytes(len(bits) // 8, "big")
    return out + data.replace(b"\xff", b"\xff\x00") + b"\xff\xd9"


def make_kit(content, name, photos=6):
    """A kit folder in Your Content with a few real (small, grey) JPEG photos, tall and wide by turns."""
    kit = Path(content) / name
    (kit / ".kit").mkdir(parents=True)
    pdir = kit / "Photos"
    pdir.mkdir()
    rows = []
    for i in range(1, photos + 1):
        w, h = (600, 900) if i % 2 else (900, 600)
        f = pdir / f"p-{i:03d}.jpg"
        f.write_bytes(jpeg(w, h, level=i * 5, note=f"photo {i}"))
        rows.append({"n": i, "file": f.as_posix(), "w": w, "h": h, "way": "tall" if h > w else "wide"})
    rec = {"name": name, "date": "2026-11-01", "folder": name, "source": "drop", "photos": sorted(p.name for p in pdir.iterdir())}
    (kit / ".kit" / "kit.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    (kit / ".kit" / "sheet.json").write_text(json.dumps({"folder": pdir.as_posix(), "photos": rows}, indent=1, ensure_ascii=False),
                                             encoding="utf-8")
    return kit


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    size = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1080, 1350)
    Path(sys.argv[1]).write_bytes(jpeg(size[0], size[1], level=20, note="tests/pc_plain_jpeg.py"))
    print(f"wrote {sys.argv[1]} ({size[0]} x {size[1]})")
