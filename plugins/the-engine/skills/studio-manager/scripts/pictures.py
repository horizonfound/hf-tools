#!/usr/bin/env python3
"""Small pictures from photos, on a Mac or a PC: previews, contact-sheet thumbnails, a photo's size.

Every preview, contact-sheet thumbnail, sneak peek and big preview the Assistant makes comes from here.

On a Mac this is the Mac's own `sips`, exactly as before: nothing installed, and it opens every RAW.
A PC has no such tool, so there the work is done in two steps:

  1. For a RAW file, pull out the JPEG the camera already stored inside it (every camera does: it is
     what the back of the camera shows). Plain Python, nothing installed. The RAW is only ever read.
  2. Resize it with Pillow, the one picture add-on a PC needs (`python -m pip install pillow`).

Finished photos (JPEG, PNG, TIFF, WebP) go straight to step 2. iPhone HEIC needs a second add-on
(`pillow-heif`); without it a HEIC is reported as unreadable in plain words (why_not), never guessed at.

    python3 pictures.py <photo> [<photo> ...]        says what it can read from each, and how
    python3 pictures.py --make <photo> <out.jpg> [size]

To try the PC route on a Mac, set ASSISTANT_NO_SIPS=1 (Pillow has to be there).

What is stored inside each RAW, and so how big a PC's previews can be (the Mac's sips decodes the RAW
itself, so a Mac is never limited by this):
  Canon CR3     a 1620 px preview and the full-size JPEG              proven (EOS R5, Nov 6)
  Canon CR2     the full-size JPEG                                   proven (5D Mark IV, Nov 6)
  DJI DNG       a 960 x 720 preview only                             proven (Mavic 3, Nov 6)
  Nikon NEF     the full-size JPEG (JpgFromRaw), in a sub-directory  from the layout, not tried
  Sony ARW      a 1616 px preview                                    from the layout, not tried
  Fuji RAF      a 1920 px (older: 1600 or 640) JPEG at a fixed spot  from the layout, not tried
  Panasonic RW2 the whole JPEG in one tag (JpgFromRaw)               from the layout, not tried
  Olympus ORF, Pentax PEF, anything else: the preview sits in the maker's own notes, so it is found by
                looking through the file for a complete JPEG         not tried on a real file
A file whose preview cannot be found or opened gives no picture and plain words (why_not), never a
crash and never a made-up picture. Nothing here has run on a real PC.
"""
import io
import mmap
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

import exif_read
import this_computer

RAW = {".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw", ".3fr", ".erf", ".iiq"}
HEIC = {".heic", ".heif"}
_heif_tried = False
_heif_ok = False
_sips_here = None


def use_sips():
    """True on a Mac: its own sips makes every small picture, as it always has."""
    global _sips_here
    if _sips_here is None:
        _sips_here = bool(shutil.which("sips"))
    return _sips_here and not os.environ.get("ASSISTANT_NO_SIPS")


def _pillow():
    """Pillow's Image module, with iPhone photos switched on if that add-on is here too. None if Pillow is not."""
    global _heif_tried, _heif_ok
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001  (not installed, or installed for another Python and broken here)
        return None
    if not _heif_tried:
        _heif_tried = True
        # Photographers' own files, opened small: a 100-megapixel medium-format photo is not an attack.
        Image.MAX_IMAGE_PIXELS = max(Image.MAX_IMAGE_PIXELS or 0, 250_000_000)
        warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
            _heif_ok = True
        except Exception:  # noqa: BLE001  (not installed, or too old for this Python)
            pass
    return Image


def ready():
    """(True, how) when small pictures can be made on this computer; (False, what is missing in plain words)."""
    if use_sips():
        return True, "the Mac's own picture tool"
    if _pillow():
        return True, "Pillow"
    # Ends in a full stop, with the command inside the brackets so the stop is never read as part of it:
    # callers add their own sentence after these words.
    if this_computer.MAC and not os.environ.get("ASSISTANT_NO_SIPS"):
        # A Mac whose own picture tool is missing: never seen (every Mac comes with sips). Its words say so, and
        # give the Mac's own name for Python (a Mac has no "python"). ASSISTANT_NO_SIPS, the PC way tried on a
        # Mac, keeps the PC's words below: showing those is what it is for.
        return False, ("This Mac's own picture tool (sips, which every Mac comes with) can't be found, so I can't "
                       "make previews of your photos. One free add-on can do the same job: Pillow (one command adds "
                       "it: python3 -m pip install pillow).")
    return False, (f"This {this_computer.COMPUTER} needs one free add-on before I can make previews of your photos. "
                   "It is called Pillow (one command adds it: python -m pip install pillow).")


def heic_ok():
    """True when iPhone photos (HEIC) can be opened here: always on a Mac, on a PC only with pillow-heif."""
    if use_sips():
        return True
    return bool(_pillow()) and _heif_ok


def why_not(src):
    """Why a small picture of this photo could not be made here, in plain words, after make_jpeg or
    thumb_rows said no. None on a Mac: its own tool reads everything, and its rare failures keep the words
    they always had. The photo itself is only ever read, so nothing about it has changed; whether the file
    itself is whole is not known here, so that is never claimed."""
    if use_sips():
        return None
    ok, words = ready()
    if not ok:
        return words
    ext = Path(src).suffix.lower()
    if ext in HEIC and not heic_ok():
        # No install command here: whether a PC gets that add-on (pillow-heif) is Dustin and Nicole's call, still
        # open, and parts/on-a-pc.md has Claude suggest exported JPEGs meanwhile. These words say the same.
        return (f"iPhone photos (HEIC) can't be shown on a {this_computer.COMPUTER} yet: that takes one more add-on "
                "(pillow-heif), which isn't part of the Assistant yet. Exported as JPEGs, they can be. Nothing was changed.")
    if ext in RAW:
        gen = _raw_jpegs(src)
        try:
            found = next(gen, None) is not None
        finally:
            gen.close()
        if not found:
            return "I could not find the preview the camera keeps inside this RAW file, so I can't show it here. Nothing was changed."
        return "The preview inside this RAW file could not be opened here. Nothing was changed."
    return "This photo could not be opened here. Nothing was changed."


# ---------------------------------------------------------------- the JPEG inside a RAW file

def _jpeg_head(b, off, limit=None, strict=False):
    """(SOF marker, width, height, where the picture data starts) of a JPEG that begins at off, or None.
    Walks its markers up to the start of the picture data. Marker 0xC0-0xC2 is an ordinary JPEG; 0xC3 is
    the lossless kind cameras use for the RAW data itself, which is not a picture to show. strict (for a
    JPEG found by looking through a file, not one the file's own directory points to) also asks for the
    quantisation table and 8-bit samples every camera preview has, so a chance run of bytes in the RAW
    data is never taken for a picture."""
    n = len(b) if limit is None else min(len(b), limit)
    if off < 0 or off + 4 > n or b[off] != 0xFF or b[off + 1] != 0xD8:
        return None
    p, sof, dqt = off + 2, None, False
    for _ in range(400):
        if p + 4 > n or b[p] != 0xFF:
            return None
        m = b[p + 1]
        if m == 0xFF:                                   # a fill byte before the marker
            p += 1
            continue
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            p += 2
            continue
        if m == 0xD9:
            return None
        seg = struct.unpack_from(">H", b, p + 2)[0]
        if seg < 2:
            return None
        if m == 0xDB:
            dqt = True
        if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC) and sof is None:
            if p + 10 > n:
                return None
            bits, comps = b[p + 4], b[p + 9]
            h, w = struct.unpack_from(">HH", b, p + 5)
            if not w or not h:
                return None
            if strict and (bits != 8 or comps not in (1, 3) or w > 30000 or h > 30000 or min(w, h) < 64):
                return None
            sof = (m, w, h)
        if m == 0xDA:
            if not sof or (strict and not dqt):
                return None
            return sof + (p,)
        p += 2 + seg
    return None


def _jpeg_kind(b, off, limit=None):
    """(marker, width, height) of the JPEG that starts at off, or None."""
    head = _jpeg_head(b, off, limit)
    return head[:3] if head else None


def _jpeg_end(b, sos):
    """Where a JPEG ends (just past its end marker), given where its picture data starts. None if it never does.
    Inside the picture data every 0xFF byte is followed by 0x00 or a restart marker, so the first FF D9 is the end."""
    try:
        q = sos + 2 + struct.unpack_from(">H", b, sos + 2)[0]
    except struct.error:
        return None
    e = b.find(b"\xff\xd9", q)
    return e + 2 if e >= 0 else None


def _tiff_candidates(b):
    """Every (offset, length) in a TIFF-shaped RAW that might be a JPEG: thumbnail pairs (Sony's preview,
    Nikon's JpgFromRaw in a sub-directory, every IFD1 thumbnail), single strips (Canon CR2's full-size JPEG,
    a DNG's previews), Panasonic's JpgFromRaw. Walks the main chain of directories and their sub-directories."""
    if b[:2] == b"II":
        e = "<"
    elif b[:2] == b"MM":
        e = ">"
    else:
        return []
    size = len(b)
    out, seen = [], set()
    sizes = {1: 1, 2: 1, 3: 2, 4: 4, 6: 1, 7: 1, 8: 2, 9: 4, 13: 4}

    def values(typ, cnt, p):
        width = sizes.get(typ)
        if not width or cnt < 1 or cnt > 64:
            return None
        vo = p + 8 if width * cnt <= 4 else struct.unpack_from(e + "I", b, p + 8)[0]
        if vo + width * cnt > size:
            return None
        fmt = {1: "B", 3: "H", 4: "I", 13: "I"}.get(typ)
        return list(struct.unpack_from(e + fmt * cnt, b, vo)) if fmt else None

    def walk(off, depth):
        hops = 0
        while off and off not in seen and off + 2 <= size and depth < 4 and hops < 12:
            seen.add(off)
            hops += 1
            n = struct.unpack_from(e + "H", b, off)[0]
            if n > 400 or off + 2 + n * 12 + 4 > size:
                return
            t = {}
            for k in range(n):
                p = off + 2 + k * 12
                tag, typ, cnt = struct.unpack_from(e + "HHI", b, p)
                if tag == 0x002E and typ == 7 and cnt > 4:      # Panasonic: the whole JPEG as one blob
                    out.append((struct.unpack_from(e + "I", b, p + 8)[0], cnt))
                elif tag in (0x0111, 0x0117, 0x0201, 0x0202, 0x014A):
                    t[tag] = values(typ, cnt, p)
            if t.get(0x0201) and t.get(0x0202):
                out.append((t[0x0201][0], t[0x0202][0]))
            if t.get(0x0111) and t.get(0x0117) and len(t[0x0111]) == 1:
                out.append((t[0x0111][0], t[0x0117][0]))
            for sub in t.get(0x014A) or []:
                walk(sub, depth + 1)
            off = struct.unpack_from(e + "I", b, off + 2 + n * 12)[0]

    try:
        walk(struct.unpack_from(e + "I", b, 4)[0], 0)
    except (struct.error, IndexError, ValueError):
        pass
    return out


def _cr3_candidates(b):
    """Canon CR3: the 1620-pixel preview (PRVW), the small thumbnail (THMB), and the full-size JPEG that is
    the file's first track (found from the track's own size and offset tables)."""
    out = []
    head = min(len(b), 4 * 1024 * 1024)
    for name in (b"PRVW", b"THMB"):
        i = b.find(name, 0, head)
        if i >= 4:
            end = i - 4 + struct.unpack_from(">I", b, i - 4)[0]
            j = b.find(b"\xff\xd8\xff", i, min(end, len(b)))
            if j > 0:
                out.append((j, end - j))
    try:
        for kind, s, e in exif_read._iter_boxes(b, 0, len(b)):
            if kind != b"moov":
                continue
            for k2, s2, e2 in exif_read._iter_boxes(b, s, e):
                if k2 != b"trak":
                    continue
                stsz = b.find(b"stsz", s2, e2)
                co64 = b.find(b"co64", s2, e2)
                stco = b.find(b"stco", s2, e2)
                if stsz > 0 and (co64 > 0 or stco > 0):
                    fixed, count = struct.unpack_from(">II", b, stsz + 8)
                    length = fixed or (struct.unpack_from(">I", b, stsz + 16)[0] if count else 0)
                    offset = struct.unpack_from(">Q", b, co64 + 12)[0] if co64 > 0 else struct.unpack_from(">I", b, stco + 12)[0]
                    if length and offset:
                        out.append((offset, length))
                break                                   # only the first track is a picture to show
    except (struct.error, ValueError, IndexError):
        pass
    return out


def _raf_candidates(b):
    """Fuji RAF: the header says where its JPEG is and how long, at bytes 84 to 91."""
    try:
        return [struct.unpack_from(">II", b, 84)]
    except struct.error:
        return []


def _scan_candidates(b, most=8):
    """For a RAW whose preview is not where its directories say (Olympus and Pentax keep theirs in the
    maker's own notes): look through the file for complete, ordinary JPEGs."""
    out, p = [], 0
    while len(out) < most:
        p = b.find(b"\xff\xd8\xff", p)
        if p < 0:
            break
        head = _jpeg_head(b, p, strict=True)
        if head and head[0] in (0xC0, 0xC1, 0xC2):
            end = _jpeg_end(b, head[3])
            if end:
                out.append((p, end - p))
                p = end
                continue
        p += 3
    return out


def _checked(b, cands, strict=False):
    """(long edge, offset, length) for each candidate that really is an ordinary JPEG; the rest dropped."""
    good, seen = [], set()
    for off, length in cands:
        if off in seen or off <= 0 or off >= len(b) or length <= 1024:
            continue
        seen.add(off)
        end = min(len(b), off + length)
        head = _jpeg_head(b, off, end, strict=strict)
        if head and head[0] in (0xC0, 0xC1, 0xC2):
            good.append((max(head[1], head[2]), off, end - off))
    return good


def _raw_candidates(b, ext, want):
    """The ordinary JPEGs stored inside a RAW, each (long edge, offset, length)."""
    if b[4:8] == b"ftyp":
        cands = _cr3_candidates(b)
    elif b[:8] == b"FUJIFILM":
        cands = _raf_candidates(b)
    elif b[:2] in (b"II", b"MM"):
        cands = _tiff_candidates(b)
    else:
        cands = []
    good = _checked(b, cands)
    # Only a thumbnail found (or nothing): the real preview is somewhere the directories do not point to.
    # Looking through the whole file costs one read of it, so it is done only then.
    if ext in RAW and (not good or max(g[0] for g in good) < min(want or 640, 1000)):
        known = {g[1] for g in good}
        good += [g for g in _checked(b, _scan_candidates(b), strict=True) if g[1] not in known]
    return good


def _ordered(good, want):
    """The order to try them in: the smallest at least `want` on its long edge first (quicker to open),
    then the bigger ones, then the smaller ones, biggest first."""
    big = sorted(g for g in good if want and g[0] >= want)
    rest = sorted((g for g in good if not (want and g[0] >= want)), reverse=True)
    return big + rest


def _raw_spots(path, want=0):
    """(long edge, offset, length) of each JPEG stored inside a RAW file, in the order to try them. Empty for a
    file that cannot be read or whose layout is not understood here."""
    try:
        with open(path, "rb") as fh:
            if os.fstat(fh.fileno()).st_size < 64:
                return []
            with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as b:
                return _ordered(_raw_candidates(b, Path(path).suffix.lower(), want), want)
    except Exception:  # noqa: BLE001  (an unreadable file, or a layout read wrong: no picture, never a crash)
        return []


def _raw_jpegs(path, want=0):
    """The bytes of each JPEG stored inside a RAW file, best first for a picture `want` pixels on its long
    edge. Yields nothing for a file that cannot be read or whose layout is not understood here. The file is
    only read, and only the one JPEG being tried; it is closed again before each is handed over (a file a
    program has open cannot be renamed on a PC)."""
    for edge, off, length in _raw_spots(path, want):
        try:
            with open(path, "rb") as fh:
                fh.seek(off)
                data = fh.read(length)
        except OSError:
            return
        if len(data) == length:                         # the file changed since it was looked at: skip that one
            yield data


def embedded_jpeg(path, want=0):
    """The bytes of a JPEG stored inside a RAW file, or None. `want` is the long edge the caller needs:
    the smallest stored JPEG at least that big is chosen (quicker to open), else the biggest there is."""
    gen = _raw_jpegs(path, want)
    try:
        return next(gen, None)
    finally:
        gen.close()


# ---------------------------------------------------------------- colours: a camera set to Adobe RGB
#
# A camera set to Adobe RGB stores its preview JPEG in Adobe RGB colours with no colour profile attached; it only
# says so in the Exif ColorSpace tag (0xFFFF "uncalibrated", or 2 on some Sonys). Read as if it were ordinary sRGB,
# such a picture comes out dull, a green dress turning teal (seen on the 5D Mark IV CR2s, Nov 6). The Mac's sips
# reads the RAW itself and never has this problem. Here the pixels are turned into sRGB with Pillow's own colour
# module; if that module is missing, the preview keeps its colours and carries an Adobe RGB profile instead,
# which every browser honours.

def _s15(x):
    return struct.pack(">i", int(round(x * 65536)))


def _adobe_rgb_icc():
    """A small ICC colour profile matching Adobe RGB (1998): its published primaries, white point and 2.2 gamma
    (563/256), built here so nothing has to be downloaded or shipped."""
    def xyz(x, y, z):
        return b"XYZ " + b"\0" * 4 + _s15(x) + _s15(y) + _s15(z)

    def curve(gamma):
        return b"curv" + b"\0" * 4 + struct.pack(">IH", 1, int(round(gamma * 256))) + b"\0\0"

    name = b"Adobe RGB (1998) compatible\0"
    tags = [(b"desc", b"desc" + b"\0" * 4 + struct.pack(">I", len(name)) + name + struct.pack(">IIHB", 0, 0, 0, 0) + b"\0" * 67),
            (b"cprt", b"text" + b"\0" * 4 + b"No copyright, use freely\0"),
            (b"wtpt", xyz(0.95045, 1.0, 1.08905)),
            (b"rXYZ", xyz(0.60974, 0.31111, 0.01947)), (b"gXYZ", xyz(0.20528, 0.62567, 0.06087)), (b"bXYZ", xyz(0.14919, 0.06322, 0.74457)),
            (b"rTRC", curve(563 / 256)), (b"gTRC", curve(563 / 256)), (b"bTRC", curve(563 / 256))]
    table, body, start = struct.pack(">I", len(tags)), b"", 128 + 4 + 12 * len(tags)
    for sig, data in tags:
        data += b"\0" * (-len(data) % 4)
        table += sig + struct.pack(">II", start + len(body), len(data))
        body += data
    head = (struct.pack(">I", 128 + len(table) + len(body)) + b"\0" * 4 + struct.pack(">I", 0x02100000) + b"mntrRGB XYZ "
            + struct.pack(">6H", 2000, 1, 1, 0, 0, 0) + b"acsp" + b"\0" * 24 + struct.pack(">I", 0)
            + _s15(0.9642) + _s15(1.0) + _s15(0.8249) + b"\0" * 48)
    return head + table + body


_cms = {}


def _srgb_transform():
    """Pillow's Adobe RGB to sRGB transform, made once. None if Pillow's colour module is not there."""
    if "t" not in _cms:
        try:
            from PIL import ImageCms
            _cms["t"] = ImageCms.buildTransform(ImageCms.ImageCmsProfile(io.BytesIO(_adobe_rgb_icc())),
                                                ImageCms.createProfile("sRGB"), "RGB", "RGB")
        except Exception:  # noqa: BLE001
            _cms["t"] = None
    return _cms["t"]


def _adobe_says(color_space, interop):
    """True when an Exif ColorSpace and interop index mean Adobe RGB: 2 (some Sonys), or "uncalibrated" with
    the Adobe interop index R03 or none at all. "Uncalibrated" with R98 (the sRGB index) is unclear (Canon
    writes exactly that for Adobe RGB, see _raw_adobe), and unclear means the ordinary colours: never a guess."""
    return color_space == 2 or (color_space == 0xFFFF and interop in (None, "R03"))


def _entry(t, ifd_off, tag):
    """Where the value of one tag in a directory starts (its own offset, as the file says), or None."""
    off = ifd_off + t.base
    n = t.u16(off)
    for k in range(min(n, 400)):
        p = off + 2 + 12 * k
        if t.u16(p) == tag:
            return t.u32(p + 8)
    return None


def _raw_adobe(path):
    """True when the RAW file says its camera was set to Adobe RGB (so the JPEG stored in it is in Adobe RGB).
    Canon says it plainly in its own notes (tag 0x00B4: 1 sRGB, 2 Adobe RGB; its Exif says "uncalibrated" with
    the sRGB interop index, seen on a 5D Mark IV and an R5); everyone else through Exif ColorSpace."""
    want = {0x8769, 0xA001, 0xA005, 0x00B4}
    try:
        with open(path, "rb") as fh:
            if os.fstat(fh.fileno()).st_size < 64:
                return False
            with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as b:
                out, canon, inter = {}, {}, None
                if b[4:8] == b"ftyp":                   # Canon CR3: Exif in the CMT2 box, Canon's own notes in CMT3
                    for kind, s, e in exif_read._iter_boxes(b, 0, len(b)):
                        if kind != b"moov":
                            continue
                        for k2, s2, e2 in exif_read._iter_boxes(b, s, e):
                            if k2 == b"uuid":
                                for k3, s3, e3 in exif_read._iter_boxes(b, s2 + 16, e2):
                                    if k3 in (b"CMT2", b"CMT3"):
                                        t = exif_read._Tiff(b, s3)
                                        t.ifd(t.first_ifd, want, out if k3 == b"CMT2" else canon)
                        break
                elif b[:2] in (b"II", b"MM"):
                    t = exif_read._Tiff(b, 0)
                    t.ifd(t.first_ifd, {0x8769}, out)
                    if isinstance(out.get(0x8769), int):
                        t.ifd(out[0x8769], want, out)
                        if isinstance(out.get(0xA005), int):
                            got = {}
                            t.ifd(out[0xA005], {0x0001}, got)
                            inter = got.get(0x0001)
                        if b[8:10] == b"CR":                # Canon CR2: its notes are a plain directory
                            mn = _entry(t, out[0x8769], 0x927C)
                            if mn:
                                t.ifd(mn, {0x00B4}, canon)
                else:
                    return False
                if canon.get(0x00B4) in (1, 2):
                    return canon[0x00B4] == 2
                return _adobe_says(out.get(0xA001), inter)
    except Exception:  # noqa: BLE001  (unreadable: assume the ordinary colours)
        return False


def _adobe_in(im):
    """True when a JPEG with no colour profile says in its own Exif that its colours are Adobe RGB. None when it
    does not say (a JPEG stored in a RAW often carries no Exif of its own)."""
    try:
        ex = im.getexif()
        cs = ex.get_ifd(0x8769).get(0xA001)
        if cs is None:
            return None
        return _adobe_says(cs, ex.get_ifd(0xA005).get(0x0001))
    except Exception:  # noqa: BLE001
        return None


def _in_srgb(im):
    """The picture in sRGB colours if it is in another space Pillow can say how to convert from; otherwise as is."""
    try:
        from PIL import ImageCms
    except Exception:  # noqa: BLE001
        return im
    icc = im.info.get("icc_profile")
    try:
        if icc:
            out = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(icc)), ImageCms.createProfile("sRGB"), outputMode="RGB")
            return out if out is not None else im
    except Exception:  # noqa: BLE001  (a profile littlecms cannot read: the colours stay as they are)
        pass
    return im


# ---------------------------------------------------------------- opening a photo with Pillow

_TURN = {2: "FLIP_LEFT_RIGHT", 3: "ROTATE_180", 4: "FLIP_TOP_BOTTOM", 5: "TRANSPOSE", 6: "ROTATE_270", 7: "TRANSVERSE", 8: "ROTATE_90"}


def _const(Image, group, name):
    """A Pillow constant under its newer name (Image.Transpose.ROTATE_90) or its older one (Image.ROTATE_90)."""
    return getattr(getattr(Image, group, Image), name)


def _decode(Image, ImageOps, fp, want, raw=None, raw_adobe=None):
    """A Pillow picture, the right way up, in plain colour, fully read; None if it cannot be read here.
    raw: the RAW file this JPEG came out of, which says which way is up when the JPEG does not.
    raw_adobe: the RAW says its camera was set to Adobe RGB (used when the JPEG itself does not say)."""
    try:
        im = Image.open(fp)
        icc = im.info.get("icc_profile") if im.mode in ("RGB", "RGBA") else None
        adobe = False
        if not icc and im.mode == "RGB":
            said = _adobe_in(im)
            adobe = said if said is not None else bool(raw_adobe)
        if want and im.format == "JPEG":
            im.draft("RGB", (want, want))           # a big JPEG is opened small: many times quicker
        turn = im.getexif().get(0x0112)
        im = ImageOps.exif_transpose(im)
        if raw is not None and (not turn or turn == 1):  # the stored JPEG does not say which way is up: the RAW does
            o = exif_read.read(raw).get("orientation")
            if o in _TURN:
                im = im.transpose(_const(Image, "Transpose", _TURN[o]))
        if im.mode != "RGB":
            if im.mode in ("RGBA", "LA", "P", "PA"):
                im = im.convert("RGBA")
                flat = Image.new("RGB", im.size, (255, 255, 255))
                flat.paste(im, mask=im.split()[-1])
                im = flat
            else:
                im = im.convert("RGB")
        im.load()
        im.info.pop("icc_profile", None)
        if adobe:
            t = _srgb_transform()
            if t is not None:
                from PIL import ImageCms
                im = ImageCms.applyTransform(im, t)     # Adobe RGB numbers turned into sRGB ones
                im.info.pop("icc_profile", None)         # sRGB is what a picture with no profile means
            else:
                im.info["icc_profile"] = _adobe_rgb_icc()   # no colour module: the colours stay, labelled
        elif icc:
            im.info["icc_profile"] = icc
        return im
    except Exception:  # noqa: BLE001  (a file Pillow cannot read, a truncated JPEG: say no, never guess)
        return None


def _open(src, want=0):
    """A Pillow picture of the photo, the right way up, in plain colour. None if it cannot be read here."""
    Image = _pillow()
    if Image is None:
        return None
    try:
        from PIL import ImageOps
    except Exception:  # noqa: BLE001
        return None
    src = Path(src)
    if src.suffix.lower() not in RAW:
        return _decode(Image, ImageOps, src, want)
    adobe = None
    gen = _raw_jpegs(src, want)
    try:
        for data in gen:                                # a preview that will not open: try the next one
            if adobe is None:
                adobe = _raw_adobe(src)
            im = _decode(Image, ImageOps, io.BytesIO(data), want, raw=src, raw_adobe=adobe)
            if im is not None:
                return im
    finally:
        gen.close()
    return None


# ---------------------------------------------------------------- what the scripts ask for

def make_jpeg(src, dst, size, quality=82):
    """A JPEG copy of the photo, its long edge `size` pixels, at dst. True if it is there afterwards.
    The photo itself is only read. On a Mac: sips, exactly as always. Elsewhere: the stored JPEG and Pillow
    (a photo, or a RAW's stored preview, smaller than `size` is kept at its own size rather than blown up)."""
    src, dst = Path(src), Path(dst)
    if use_sips():
        try:
            r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(quality), "-Z", str(size), str(src), "--out", str(dst)],
                               capture_output=True, encoding="utf-8", errors="replace")
            return r.returncode == 0 and dst.exists()
        except OSError:
            return False
    im = _open(src, size)
    if im is None:
        return False
    tmp = dst.with_name(dst.name + ".part")
    try:
        if max(im.size) > size:
            im.thumbnail((size, size))
        kw = {"quality": int(quality)}
        if im.info.get("icc_profile"):
            kw["icc_profile"] = im.info["icc_profile"]  # the photo's own colours, as the Mac keeps them
        im.save(tmp, "JPEG", **kw)
        this_computer.replace(tmp, dst)
        return dst.exists()
    except Exception:  # noqa: BLE001  (a full drive, a picture Pillow could not write)
        try:
            tmp.unlink()                                # our own half-written preview, never a photo
        except OSError:
            pass
        return False


def bmp_pixels(path):
    """(width, height, rows of RGB bytes) from a 24- or 32-bit uncompressed BMP (what the Mac's sips writes)."""
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


def thumb_rows(src, size, tmp=None):
    """(width, height, rows) for a small copy of the photo, its long edge `size` pixels, each row a run of
    R,G,B bytes: what the contact sheets are drawn from. None if the photo cannot be read here.
    On a Mac: sips writes a small BMP at tmp (a scratch file, overwritten each time) and it is read back,
    exactly as the contact sheets always were. Elsewhere: Pillow, the right way up; like sips, a small
    photo is brought up to `size` so every sheet looks the same."""
    if use_sips():
        own = tmp is None
        if own:
            fd, name = tempfile.mkstemp(suffix=".bmp")
            os.close(fd)
            tmp = name
        tmp = Path(tmp)
        try:
            r = subprocess.run(["sips", "-s", "format", "bmp", "-Z", str(size), str(src), "--out", str(tmp)], capture_output=True)
            if r.returncode != 0 or not tmp.exists():
                return None
            try:
                return bmp_pixels(tmp)
            except ValueError:
                return None
        finally:
            if own:
                try:
                    tmp.unlink()
                except OSError:
                    pass
    im = _open(src, size)
    if im is None:
        return None
    try:
        w, h = im.size
        if max(w, h) > size:
            im.thumbnail((size, size))
        elif max(w, h) < size:
            s = size / max(w, h)
            im = im.resize((max(1, round(w * s)), max(1, round(h * s))), _const(_pillow(), "Resampling", "BICUBIC"))
        im = _in_srgb(im)                       # a sheet is a plain PNG with no profile: its pixels have to be sRGB
        w, h = im.size
        raw = im.tobytes()
        return w, h, [raw[y * w * 3:(y + 1) * w * 3] for y in range(h)]
    except Exception:  # noqa: BLE001
        return None


def size_of(src):
    """(width, height) of the photo, or None. On a Mac: sips's own two numbers, exactly as capcut.py always read
    them (not turned for the photo's orientation, as before). On a PC: the right way up; a RAW gives the size of
    the biggest JPEG stored inside it (for most cameras the photo's own size; a DJI drone's DNG keeps 960 x 720)."""
    src = Path(src)
    if use_sips():
        try:
            r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(src)],
                               capture_output=True, encoding="utf-8", errors="replace")
            import re
            w, h = re.search(r"pixelWidth:\s*(\d+)", r.stdout), re.search(r"pixelHeight:\s*(\d+)", r.stdout)
            if w and h:
                return int(w.group(1)), int(h.group(1))
        except OSError:
            pass
        return None
    Image = _pillow()
    if Image is None:
        return None
    try:
        if src.suffix.lower() in RAW:
            data = embedded_jpeg(src)
            if not data:
                return None
            with Image.open(io.BytesIO(data)) as im:   # only the header is read, nothing decoded
                w, h = im.size
                turn = im.getexif().get(0x0112)
            if not turn or turn == 1:
                turn = exif_read.read(src).get("orientation")
        else:
            with Image.open(src) as im:
                w, h = im.size
                turn = im.getexif().get(0x0112)
        return (h, w) if turn in (5, 6, 7, 8) else (w, h)
    except Exception:  # noqa: BLE001
        return None


def main():
    this_computer.utf8_output()
    args = sys.argv[1:]
    ok, how = ready()
    print(("Small pictures are made with: " + how) if ok else how)
    if args and args[0] == "--make":
        size = int(args[3]) if len(args) > 3 else 1000
        made = make_jpeg(args[1], args[2], size)
        print("made" if made else (why_not(args[1]) or "could not read that photo"), args[2])
        return 0 if made else 1
    for a in args:
        p = Path(a)
        if p.suffix.lower() in RAW:
            gen = _raw_jpegs(p)
            try:
                inside = [_jpeg_kind(d, 0) for d in gen]
            finally:
                gen.close()
            inside = [k for k in inside if k]
            print(f"{p.name}: " + ("JPEGs inside: " + ", ".join(f"{k[1]} x {k[2]}" for k in inside) if inside else "no JPEG found inside"))
        else:
            s = size_of(p)
            print(f"{p.name}: " + (f"{s[0]} x {s[1]}" if s else (why_not(p) or "could not be read here")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
