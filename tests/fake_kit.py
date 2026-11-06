#!/usr/bin/env python3
"""Make a pretend Assistant with one post kit, for testing the picker pages without a real shoot.

    /usr/bin/python3 tests/fake_kit.py /private/tmp/hf-fake --photos 60
    /usr/bin/python3 tests/fake_kit.py /private/tmp/hf-fake-45 --photos 12 --megapixels 45
    /usr/bin/python3 tests/fake_kit.py /private/tmp/hf-real --photos-from "/Volumes/Big Kahuna/Final Exports/Beach"

It refuses any target that is not under /private/tmp, and it never deletes or replaces anything: a target
that already holds a kit of the same name stops it.

What it makes under <target>:
    studio/                                   use this as STUDIO_HOME (a Studio File with posts.home set)
    The Assistant/Drop a shoot here/
    The Assistant/Your Content/2026-11-01 Fake beach/
        Photos/                               N photos drawn in plain Python and converted by the Mac's own sips:
                                              tall, wide and square JPEGs, each a colour, a big number and a ruler
                                              along the top and left edges (a tick every 50 px, a long one every
                                              100) for pixel checks; plus one HEIC, one PNG, one TIFF, one with an
                                              upper-case name, one small 300x450, and one stored sideways
        .kit/kit.json, .kit/sheet.json        the kit record and the numbered list (kit.py sheet), with picks
    The Assistant/Your Content old/Sneaky/.kit/kit.json
                                              a look-alike beside Your Content, for the refusal tests

With --photos-from the kit's photos are a real folder, left exactly as it is (nothing is written there): the
kit record only points at it.

Python 3.9, standard library only. No Pillow.
"""
import argparse
import colorsys
import json
import os
import struct
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
SAFE = Path("/private/tmp")

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


def say(msg):
    print(msg, flush=True)


# ---------- drawing, in plain Python ----------

class Picture:
    """Rows of BGR bytes (the order a BMP wants), top row first."""

    def __init__(self, w, h, rgb):
        self.w, self.h = w, h
        self.rows = [bytearray(bytes((rgb[2], rgb[1], rgb[0])) * w) for _ in range(h)]

    def rect(self, x0, y0, w, h, rgb):
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.w, x0 + w), min(self.h, y0 + h)
        if x1 <= x0 or y1 <= y0:
            return
        fill = bytes((rgb[2], rgb[1], rgb[0])) * (x1 - x0)
        for y in range(y0, y1):
            self.rows[y][x0 * 3:x1 * 3] = fill

    def number(self, s, rgb):
        scale = max(2, min(self.w // (6 * len(s) + 2), self.h // 12))
        x0 = (self.w - (6 * len(s) - 1) * scale) // 2
        y0 = (self.h - 7 * scale) // 2
        for ch in s:
            for gy, line in enumerate(DIGITS.get(ch, [])):
                for gx, bit in enumerate(line):
                    if bit == "1":
                        self.rect(x0 + gx * scale, y0 + gy * scale, scale, scale, rgb)
            x0 += 6 * scale

    def ruler(self):
        """A white band along the top and the left edge with black ticks: one every 50 px, long every 100."""
        band = max(16, min(self.w, self.h) // 40)
        self.rect(0, 0, self.w, band, (255, 255, 255))
        self.rect(0, 0, band, self.h, (255, 255, 255))
        for x in range(0, self.w, 50):
            self.rect(x, 0, 2, band if x % 100 == 0 else band // 2, (0, 0, 0))
        for y in range(0, self.h, 50):
            self.rect(0, y, band if y % 100 == 0 else band // 2, 2, (0, 0, 0))

    def turned_left(self):
        """The same picture turned a quarter turn to the left, as a camera held sideways stores it."""
        out = Picture.__new__(Picture)
        out.w, out.h = self.h, self.w
        out.rows = []
        for yy in range(self.w):
            c = (self.w - 1 - yy) * 3
            out.rows.append(bytearray(b"".join(bytes(r[c:c + 3]) for r in self.rows)))
        return out

    def write_bmp(self, path):
        pad = b"\x00" * ((4 - (self.w * 3) % 4) % 4)
        size = (self.w * 3 + len(pad)) * self.h
        with open(path, "wb") as f:
            f.write(b"BM" + struct.pack("<IHHI", 54 + size, 0, 0, 54))
            f.write(struct.pack("<IiiHHIIiiII", 40, self.w, self.h, 1, 24, 0, size, 2835, 2835, 0, 0))
            for row in reversed(self.rows):
                f.write(row)
                f.write(pad)


def draw(w, h, i, total):
    hue = (i * 0.618034) % 1.0
    r, g, b = (int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.45, 0.85))
    pic = Picture(w, h, (r, g, b))
    r2, g2, b2 = (int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.55, 0.55))
    pic.rect(0, h * 2 // 3, w, h - h * 2 // 3, (r2, g2, b2))          # a darker "ground", so up is plainly up
    pic.rect(w // 8, h // 8, max(8, w // 10), max(8, w // 10), (255, 244, 200))   # a "sun", top left
    pic.number(str(i), (255, 255, 255))
    pic.ruler()
    return pic


def sips(src, dst, fmt, quality=None):
    cmd = ["sips", "-s", "format", fmt]
    if quality:
        cmd += ["-s", "formatOptions", str(quality)]
    r = subprocess.run(cmd + [str(src), "--out", str(dst)], capture_output=True, text=True)
    return r.returncode == 0 and Path(dst).is_file()


def mark_sideways(jpg):
    """Write the camera's "this was shot turned" note (EXIF orientation 6) into a JPEG's header."""
    data = Path(jpg).read_bytes()
    if data[:2] != b"\xff\xd8":
        return False
    tiff = b"II*\x00" + struct.pack("<I", 8) + struct.pack("<H", 1) + struct.pack("<HHI", 0x0112, 3, 1) + struct.pack("<HH", 6, 0) + struct.pack("<I", 0)
    body = b"Exif\x00\x00" + tiff
    seg = b"\xff\xe1" + struct.pack(">H", len(body) + 2) + body
    # sips writes an Exif block of its own (with no turn in it); ours takes its place, so there is only one
    out, i, placed = [data[:2]], 2, False
    while i + 4 <= len(data) and data[i] == 0xFF and data[i + 1] != 0xDA:
        n = struct.unpack(">H", data[i + 2:i + 4])[0]
        piece = data[i:i + 2 + n]
        if data[i + 1] == 0xE1 and piece[4:10] == b"Exif\x00\x00":
            if not placed:
                out.append(seg)
                placed = True
        else:
            out.append(piece)
        i += 2 + n
    if not placed:
        out.insert(1, seg)
    out.append(data[i:])
    Path(jpg).write_bytes(b"".join(out))
    return True


def sizes(megapixels):
    """(tall, wide, square) sizes. The default is small enough to draw sixty in a few seconds."""
    if not megapixels:
        return (1200, 1800), (1800, 1200), (1400, 1400)
    px = megapixels * 1_000_000
    short = int((px / 1.5) ** 0.5) // 2 * 2
    long_ = int(short * 1.5) // 2 * 2
    sq = int(px ** 0.5) // 2 * 2
    return (short, long_), (long_, short), (sq, sq)


def make_photos(folder, n, megapixels):
    """N photos into the folder. Returns the names, and which one is which special case."""
    if n < 8:
        raise SystemExit("STOP: --photos needs at least 8 (six of them are the special cases).")
    tall, wide, square = sizes(megapixels)
    tmp = folder / ".drawing.bmp"
    special = {}
    names = []
    # where the special cases sit among the numbers (never 1 to 3, which the tests use as plain photos)
    spots = {4: "heic", 5: "png", 6: "tiff", 7: "upper", 8: "small", n: "sideways"}
    for i in range(1, n + 1):
        what = spots.get(i, "plain")
        w, h = (tall, wide, tall, square, wide, tall)[i % 6] if what == "plain" else tall
        if what == "small":
            w, h = 300, 450
        if what == "sideways":
            w, h = 800, 1200
        pic = draw(w, h, i, n)
        if what == "sideways":
            pic = pic.turned_left()
        pic.write_bmp(tmp)
        name = {"heic": f"beach-{i:03d}.heic", "png": f"beach-{i:03d}.png", "tiff": f"beach-{i:03d}.tif",
                "upper": f"BEACH-{i:03d}.JPG", "small": f"beach-{i:03d}-small.jpg",
                "sideways": f"beach-{i:03d}-sideways.jpg"}.get(what, f"beach-{i:03d}.jpg")
        fmt = {"heic": "heic", "png": "png", "tiff": "tiff"}.get(what, "jpeg")
        ok = sips(tmp, folder / name, fmt, 88 if fmt == "jpeg" else None)
        if not ok:
            raise SystemExit(f"STOP: sips could not write {name}.")
        if what == "sideways" and not mark_sideways(folder / name):
            raise SystemExit("STOP: could not mark the sideways photo.")
        if what != "plain":
            special[what] = name
        names.append(name)
    if tmp.exists():
        tmp.unlink()            # our own scratch bitmap, made a moment ago
    return names, special


def run(env, script, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, env=env)
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("target", help="a new folder under /private/tmp")
    ap.add_argument("--photos", type=int, default=60)
    ap.add_argument("--megapixels", type=float, default=0, help="draw the plain photos this large (45 for a big camera)")
    ap.add_argument("--photos-from", help="a real folder of finished photos to point the kit at (read only)")
    ap.add_argument("--name", default="Fake beach")
    a = ap.parse_args()

    target = Path(a.target).resolve()
    if SAFE not in target.parents:
        say(f"STOP: {target} is not under {SAFE}. This only ever writes there.")
        return 2
    if not Path("/usr/bin/sips").exists():
        say("STOP: this needs the Mac's own sips.")
        return 2

    studio = target / "studio"
    home = target / "The Assistant"
    folder_name = f"2026-11-01 {a.name}"
    kit = home / "Your Content" / folder_name
    if kit.exists():
        say(f"STOP: {kit} is already there. Pick a new target folder; nothing was changed.")
        return 1
    studio.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, STUDIO_HOME=str(studio))

    code, out = run(env, "posts.py", "setup", "--home", str(home))
    if code != 0:
        say(out)
        return 1
    (kit / ".kit").mkdir(parents=True)
    rec = {"name": a.name, "date": "2026-11-01", "folder": folder_name, "source": "drop", "dropped_as": [a.name],
           "made": datetime.now().isoformat(timespec="seconds")}
    special = {}
    if a.photos_from:
        src = Path(a.photos_from)
        if not src.is_dir():
            say(f"STOP: {src} isn't a folder I can see.")
            return 2
        rec["source"] = "folder"
        rec["photos_dir"] = str(src)
        rec["photos"] = sorted(p.name for p in src.iterdir() if p.is_file() and not p.name.startswith("."))
    else:
        (kit / "Photos").mkdir()
        t0 = datetime.now()
        names, special = make_photos(kit / "Photos", a.photos, a.megapixels)
        rec["photos"] = sorted(names)
        say(f"Drew {len(names)} photos in {(datetime.now() - t0).total_seconds():.1f} s.")
    (kit / ".kit" / "kit.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))

    # the look-alike beside Your Content, for the refusal tests
    sneaky = home / "Your Content old" / "Sneaky" / ".kit"
    sneaky.mkdir(parents=True, exist_ok=True)
    (sneaky / "kit.json").write_text(json.dumps({"name": "Sneaky", "folder": "Sneaky"}, indent=1))
    old = home / "Your Content old" / ".kit"
    old.mkdir(exist_ok=True)
    (old / "kit.json").write_text(json.dumps({"name": "Your Content old", "folder": "Your Content old"}, indent=1))

    code, out = run(env, "kit.py", "sheet", str(kit))
    say(out)
    if code != 0:
        return 1
    listing = json.loads((kit / ".kit" / "sheet.json").read_text())["photos"]
    total = len(listing)
    if total >= 2:
        step = max(1, total // 12)
        reel = [n for n in range(1, total + 1, step)][:12]
        car = [n for n in range(2, total + 1, max(1, total // 7))][:7]
        code, out = run(env, "kit.py", "picks", str(kit), "--reel", ",".join(map(str, reel)), "--carousel", ",".join(map(str, car)))
        say(out)
        if code != 0:
            return 1
    by_name = {Path(x["file"]).name: x for x in listing}
    for what, name in sorted(special.items()):
        x = by_name.get(name)
        say(f"  {what}: {name}" + (f" is photo {x['n']}, listed {x['way']} ({x['w']}x{x['h']})" if x else " (not on the numbered list)"))
    say("")
    say(f"Kit: {kit}")
    say(f"Use: export STUDIO_HOME=\"{studio}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
