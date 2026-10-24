#!/usr/bin/env python3
"""Read the few camera facts the Studio needs (when it was taken, which camera,
which lens) straight out of the file, with nothing installed. Pure Python.

Handles: TIFF-based RAW (CR2, NEF, ARW, DNG, ORF, RW2, PEF), CR3 (Canon's
newer format), JPEG, RAF (Fuji, which carries a JPEG with EXIF inside), and
MP4/MOV clips (creation time only). HEIC is not read yet.

    python3 exif_read.py <file> [<file> ...]    prints what it finds
"""
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TAG_MAKE, TAG_MODEL, TAG_EXIF_IFD = 0x010F, 0x0110, 0x8769
TAG_DATETIME_ORIGINAL, TAG_DATETIME_DIGITIZED, TAG_DATETIME = 0x9003, 0x9004, 0x0132
TAG_SUBSEC_ORIGINAL, TAG_OFFSET_TIME_ORIGINAL = 0x9291, 0x9011
TAG_LENS_MODEL, TAG_BODY_SERIAL, TAG_IMAGE_WIDTH, TAG_IMAGE_HEIGHT = 0xA434, 0xA431, 0xA002, 0xA003
TAG_FOCAL, TAG_EXPOSURE, TAG_FNUMBER, TAG_ISO = 0x920A, 0x829A, 0x829D, 0x8827
TAG_ORIENTATION = 0x0112
TYPE_SIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 13: 4}
WANT = {TAG_MAKE, TAG_MODEL, TAG_EXIF_IFD, TAG_DATETIME_ORIGINAL, TAG_DATETIME_DIGITIZED, TAG_DATETIME, TAG_SUBSEC_ORIGINAL,
        TAG_OFFSET_TIME_ORIGINAL, TAG_LENS_MODEL, TAG_BODY_SERIAL, TAG_IMAGE_WIDTH, TAG_IMAGE_HEIGHT, TAG_FOCAL, TAG_EXPOSURE,
        TAG_FNUMBER, TAG_ISO, TAG_ORIENTATION}
TIFF_RAW = {".cr2", ".nef", ".arw", ".dng", ".orf", ".rw2", ".pef", ".tif", ".tiff", ".srw"}
CLIPS = {".mp4", ".mov", ".m4v"}


class _Tiff:
    """Just enough TIFF to walk IFD0 and the Exif IFD inside a byte blob."""

    def __init__(self, data, base=0):
        self.d = data
        self.base = base
        bo = data[base:base + 2]
        if bo == b"II":
            self.e = "<"
        elif bo == b"MM":
            self.e = ">"
        else:
            raise ValueError("not TIFF")
        self.first_ifd = struct.unpack_from(self.e + "I", data, base + 4)[0]

    def u16(self, off):
        return struct.unpack_from(self.e + "H", self.d, off)[0]

    def u32(self, off):
        return struct.unpack_from(self.e + "I", self.d, off)[0]

    def ifd(self, off, want, out):
        """Collect wanted tags from one IFD into out; return the next-IFD offset."""
        off += self.base
        if off + 2 > len(self.d):
            return 0
        n = self.u16(off)
        p = off + 2
        for _ in range(n):
            if p + 12 > len(self.d):
                break
            tag, typ, cnt = self.u16(p), self.u16(p + 2), self.u32(p + 4)
            if tag in want and typ in TYPE_SIZE:
                size = TYPE_SIZE[typ] * cnt
                voff = p + 8 if size <= 4 else self.base + self.u32(p + 8)
                out[tag] = self.value(typ, cnt, voff)
            p += 12
        return self.u32(p) if p + 4 <= len(self.d) else 0

    def value(self, typ, cnt, off):
        if off < 0 or off + TYPE_SIZE[typ] * cnt > len(self.d):
            return None
        if typ == 2:
            raw = self.d[off:off + cnt]
            return raw.split(b"\x00", 1)[0].decode("utf-8", "replace").strip()
        fmt = {1: "B", 3: "H", 4: "I", 6: "b", 8: "h", 9: "i", 7: "B"}.get(typ)
        if fmt:
            vals = struct.unpack_from(self.e + fmt * cnt, self.d, off)
            return vals[0] if cnt == 1 else list(vals)
        if typ in (5, 10):
            f = "I" if typ == 5 else "i"
            vals = struct.unpack_from(self.e + f * (2 * cnt), self.d, off)
            pairs = [(vals[i], vals[i + 1]) for i in range(0, len(vals), 2)]
            r = [a / b if b else None for a, b in pairs]
            return r[0] if cnt == 1 else r
        return None

    def read(self):
        out = {}
        nxt = self.ifd(self.first_ifd, WANT, out)
        if TAG_EXIF_IFD in out and isinstance(out[TAG_EXIF_IFD], int):
            self.ifd(out[TAG_EXIF_IFD], WANT, out)
        return out


def _tidy(tags):
    """Turn raw tags into the record the index keeps."""
    rec = {}
    dt = tags.get(TAG_DATETIME_ORIGINAL) or tags.get(TAG_DATETIME_DIGITIZED) or tags.get(TAG_DATETIME)
    if dt and len(dt) >= 19 and dt[:4].isdigit() and dt[:4] != "0000":
        try:
            t = datetime.strptime(dt[:19], "%Y:%m:%d %H:%M:%S")
            sub = str(tags.get(TAG_SUBSEC_ORIGINAL) or "").strip()
            if sub.isdigit():
                t = t.replace(microsecond=int((sub + "000000")[:6]))
            rec["taken"] = t.isoformat(timespec="milliseconds" if sub.isdigit() else "seconds")
        except ValueError:
            pass
    tz = tags.get(TAG_OFFSET_TIME_ORIGINAL)
    if tz:
        rec["tz"] = tz
    make, model = (tags.get(TAG_MAKE) or "").strip(), (tags.get(TAG_MODEL) or "").strip()
    if model:
        rec["camera"] = model if not make or model.lower().startswith(make.split()[0].lower()) else f"{make.split()[0]} {model}"
    if tags.get(TAG_BODY_SERIAL):
        rec["serial"] = str(tags[TAG_BODY_SERIAL]).strip()
    if tags.get(TAG_LENS_MODEL):
        rec["lens"] = str(tags[TAG_LENS_MODEL]).strip()
    if tags.get(TAG_IMAGE_WIDTH) and tags.get(TAG_IMAGE_HEIGHT):
        rec["width"], rec["height"] = int(tags[TAG_IMAGE_WIDTH]), int(tags[TAG_IMAGE_HEIGHT])
    if tags.get(TAG_ORIENTATION):
        rec["orientation"] = int(tags[TAG_ORIENTATION])
    if tags.get(TAG_FOCAL):
        rec["focal_mm"] = round(tags[TAG_FOCAL], 1)
    if tags.get(TAG_FNUMBER):
        rec["f"] = round(tags[TAG_FNUMBER], 1)
    if tags.get(TAG_EXPOSURE):
        ex = tags[TAG_EXPOSURE]
        rec["shutter"] = f"1/{round(1 / ex)}" if ex and ex < 1 else f"{ex:g}s"
    if tags.get(TAG_ISO):
        iso = tags[TAG_ISO]
        rec["iso"] = int(iso[0] if isinstance(iso, list) else iso)
    return rec


def _read_tiff_blob(data, base=0):
    try:
        return _tidy(_Tiff(data, base).read())
    except (ValueError, struct.error):
        return {}


def _jpeg_exif(data):
    """Find the Exif APP1 segment in a JPEG and read its TIFF."""
    if data[:2] != b"\xff\xd8":
        return {}
    p = 2
    while p + 4 <= len(data):
        if data[p] != 0xFF:
            p += 1
            continue
        marker = data[p + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            p += 2
            continue
        if marker == 0xDA:
            break
        seglen = struct.unpack_from(">H", data, p + 2)[0]
        if marker == 0xE1 and data[p + 4:p + 10] == b"Exif\x00\x00":
            return _read_tiff_blob(data, p + 10)
        p += 2 + seglen
    return {}


def _iter_boxes(data, start, end):
    p = start
    while p + 8 <= end:
        size, kind = struct.unpack_from(">I4s", data, p)
        hdr = 8
        if size == 1:
            size = struct.unpack_from(">Q", data, p + 8)[0]
            hdr = 16
        elif size == 0:
            size = end - p
        if size < hdr:
            break
        yield kind, p + hdr, p + size
        p += size


def _cr3_exif(data):
    """CR3: moov > uuid(85c0b687...) > CMT1 (IFD0) and CMT2 (Exif IFD), each its own little TIFF."""
    out = {}
    for kind, s, e in _iter_boxes(data, 0, len(data)):
        if kind != b"moov":
            continue
        for k2, s2, e2 in _iter_boxes(data, s, e):
            if k2 == b"uuid":
                for k3, s3, e3 in _iter_boxes(data, s2 + 16, e2):
                    if k3 in (b"CMT1", b"CMT2"):
                        try:
                            t = _Tiff(data, s3)
                            t.ifd(t.first_ifd, WANT, out)
                        except (ValueError, struct.error):
                            pass
    return _tidy(out)


def _mp4_time(data):
    """Clip creation time from the mvhd box (seconds since 1904, UTC)."""
    for kind, s, e in _iter_boxes(data, 0, len(data)):
        if kind == b"moov":
            for k2, s2, e2 in _iter_boxes(data, s, e):
                if k2 == b"mvhd":
                    ver = data[s2]
                    secs = struct.unpack_from(">Q" if ver == 1 else ">I", data, s2 + 4)[0]
                    if secs:
                        utc = datetime(1904, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=secs)
                        local = utc.astimezone().replace(tzinfo=None)  # this Mac's clock, same as the photos' camera time
                        return {"taken": local.isoformat(timespec="seconds"), "clip": True}
    return {}


def read(path, head_bytes=1024 * 1024):
    """Camera facts for one file. Reads only the first few MB, which is where
    every format keeps them (CR3 and MP4 keep moov at the front on cameras)."""
    path = Path(path)
    ext = path.suffix.lower()
    try:
        with open(path, "rb") as f:
            data = f.read(head_bytes)
    except OSError:
        return {}
    if not data:
        return {}
    if ext == ".cr3" or data[4:8] == b"ftyp" and data[8:12] in (b"crx ",):
        return _cr3_exif(data)
    if ext in CLIPS or data[4:8] == b"ftyp":
        rec = _mp4_time(data)
        if not rec and len(data) == head_bytes:  # moov at the end: read the tail
            try:
                with open(path, "rb") as f:
                    f.seek(max(0, path.stat().st_size - head_bytes))
                    rec = _mp4_time(f.read(head_bytes))
            except OSError:
                pass
        return rec
    if ext == ".raf" or data[:8] == b"FUJIFILM":
        j = data.find(b"\xff\xd8\xff")
        return _jpeg_exif(data[j:]) if j >= 0 else {}
    if data[:2] == b"\xff\xd8":
        return _jpeg_exif(data)
    if data[:2] in (b"II", b"MM"):
        return _read_tiff_blob(data)
    return {}


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(Path(arg).name, read(arg))
