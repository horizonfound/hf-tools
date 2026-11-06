#!/usr/bin/env python3
"""Pictures the PC way: made-up RAW files laid out the way six camera makers lay them out, plus junk and damaged
files. pictures.py must find the right JPEG inside each one, or say plainly that it can't, and never crash.
Runs the same on a Mac and on Windows; on a Mac it switches the Mac's own picture tool off (ASSISTANT_NO_SIPS=1),
so the PC route is what runs. GitHub runs it on a real Windows machine (.github/workflows/check-pc.yml).

    python3 tests/pc_pictures.py [<a folder of real RAW files>]      needs Pillow

The made-up files are drawn here (no real photos are kept in the project). With a folder of real CR2, CR3 or DNG
files (ASSISTANT_TEST_RAWS, or the first argument), each is also tried cut short and with its stored JPEGs
damaged. From the Nov 6 PC build (it was scratchpad/wf/pictures/tools/synth.py).
"""
import io, os, random, struct, sys, shutil, tempfile
from pathlib import Path
os.environ["ASSISTANT_NO_SIPS"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"))
import pictures  # noqa: E402
from PIL import Image  # noqa: E402
D = Path(tempfile.mkdtemp(prefix="assistant pc pictures "))
_raws = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ASSISTANT_TEST_RAWS") or "").strip()
RAWS = Path(_raws) if _raws else None
random.seed(7)
ran = 0
fails = 0
def check(what, ok):
    global fails, ran
    print(("PASS  " if ok else "FAIL  ") + what)
    fails += 0 if ok else 1
    ran += 1

def jpeg(w, h, color=(200, 40, 40), orient=None, nested_thumb=False):
    im = Image.new("RGB", (w, h), color)
    for x in range(0, w, max(1, w // 8)):           # a pattern, so the picture is not one flat colour
        im.paste((20, 20, 20), (x, 0, x + max(1, w // 40), h // 4))
    bio = io.BytesIO()
    kw = {"quality": 85}
    if orient:
        ex = Image.Exif(); ex[0x0112] = orient; kw["exif"] = ex.tobytes()
    im.save(bio, "JPEG", **kw)
    d = bio.getvalue()
    if nested_thumb:   # an APP1 Exif segment that carries a whole small JPEG inside it (as Fuji and others do)
        t = io.BytesIO(); Image.new("RGB", (160, 120), (0, 0, 255)).save(t, "JPEG"); t = t.getvalue()
        tiff = b"II*\x00" + struct.pack("<I", 8) + struct.pack("<H", 0) + struct.pack("<I", 0) + t
        app1 = b"\xff\xe1" + struct.pack(">H", 2 + 6 + len(tiff)) + b"Exif\x00\x00" + tiff
        d = d[:2] + app1 + d[2:]
    return d

def tiff(endian, magic, ifds, blobs, extra=b""):
    """ifds: list of lists of (tag, type, count, value-or-blob-name). Blobs are appended and their offsets filled in."""
    e = "<" if endian == "II" else ">"
    head = endian.encode() + magic
    out = bytearray(head + b"\0\0\0\0")
    blob_at = {}
    data = bytearray()
    # layout: header, then blobs, then IFDs
    base = len(out)
    for name, b in blobs.items():
        blob_at[name] = base + len(data); data += b
        if len(data) % 2: data += b"\0"
    out += data
    out += extra
    offs = []
    pos = len(out)
    sizes = []
    for entries in ifds:
        sizes.append(2 + 12 * len(entries) + 4)
    for s in sizes:
        offs.append(pos); pos += s
    for i, entries in enumerate(ifds):
        b = struct.pack(e + "H", len(entries))
        for tag, typ, cnt, val in entries:
            if isinstance(val, str) and val.startswith("ifd"):
                v = offs[int(val[3:])]
            elif isinstance(val, str):
                v = blob_at[val]
            elif isinstance(val, tuple):
                v = len(blobs[val[1]])
            else:
                v = val
            if typ == 3 and cnt == 1:
                b += struct.pack(e + "HHIHH", tag, typ, cnt, v, 0)
            else:
                b += struct.pack(e + "HHII", tag, typ, cnt, v)
        nxt = 0
        b += struct.pack(e + "I", nxt)
        out += b
    struct.pack_into(e + "I", out, 4, offs[0])
    return bytes(out)

def made(name, data, want_edge, orient_portrait=None):
    p = D / name; p.write_bytes(data)
    dst = D / (name + ".jpg")
    ok = pictures.make_jpeg(p, dst, 700, 82)
    if want_edge is None:
        check(f"{name}: no picture, and plain words: {pictures.why_not(p)!r}", not ok and pictures.why_not(p))
        return
    if not ok:
        check(f"{name}: made a preview", False); return
    im = Image.open(dst)
    good = max(im.size) == min(700, want_edge)
    if orient_portrait is not None:
        good = good and ((im.size[1] > im.size[0]) == orient_portrait)
    check(f"{name}: preview {im.size} from the {want_edge} px JPEG inside" + (" (upright portrait)" if orient_portrait else ""), good)

big, thumb = jpeg(4000, 2667), jpeg(160, 120, (0, 0, 255))
# Nikon NEF: big-endian, IFD0 with an uncompressed thumbnail strip and SubIFDs; SubIFD0 = JpgFromRaw; SubIFD1 = raw strip
raw_noise = bytes(random.getrandbits(8) for _ in range(300000))
nef = tiff("MM", b"\x00\x2a", [
    [(0x00FE, 4, 1, 1), (0x0111, 4, 1, "rgb"), (0x0117, 4, 1, ("len", "rgb")), (0x014A, 4, 2, 0), (0x0112, 3, 1, 1)],
], {"rgb": bytes(160 * 120 * 3), "jpg": big, "raw": raw_noise})
# patch: SubIFDs need two IFDs; build them as separate IFDs referenced by offset (rebuild with explicit IFD list)
nef = tiff("MM", b"\x00\x2a", [
    [(0x00FE, 4, 1, 1), (0x0111, 4, 1, "rgb"), (0x0117, 4, 1, ("len", "rgb")), (0x014A, 4, 1, "ifd1")],
    [(0x00FE, 4, 1, 1), (0x0201, 4, 1, "jpg"), (0x0202, 4, 1, ("len", "jpg"))],
], {"rgb": bytes(160 * 120 * 3), "jpg": big, "raw": raw_noise})
made("synthetic.NEF", nef, 4000)
# Sony ARW: IFD0 holds the 1616 px preview by 0x0201/0x0202, IFD1 a thumbnail (chained), a SubIFD the raw data
prev = jpeg(1616, 1080, (40, 160, 60))
arw = tiff("II", b"\x2a\x00", [
    [(0x0201, 4, 1, "prev"), (0x0202, 4, 1, ("len", "prev")), (0x014A, 4, 1, "ifd1")],
    [(0x0111, 4, 1, "raw"), (0x0117, 4, 1, ("len", "raw"))],
], {"prev": prev, "thumb": thumb, "raw": raw_noise})
made("synthetic.ARW", arw, 1616)
# Panasonic RW2: "IIU", the whole JPEG in tag 0x002E (type undefined), with its own Exif saying portrait
rjpg = jpeg(1920, 1280, (120, 120, 30), orient=6)
rw2 = tiff("II", b"\x55\x00", [[(0x002E, 7, len(rjpg), "j"), (0x0111, 4, 1, "raw"), (0x0117, 4, 1, ("len", "raw"))]], {"j": rjpg, "raw": raw_noise})
made("synthetic.RW2", rw2, 1920, orient_portrait=True)
# Fuji RAF: fixed header, JPEG offset and length at bytes 84..91; the JPEG carries a nested thumbnail in its Exif
fj = jpeg(1920, 1280, (30, 90, 200), nested_thumb=True)
hdr = bytearray(b"FUJIFILMCCD-RAW 0201FF383501" + b"\0" * 200)
struct.pack_into(">II", hdr, 84, len(hdr), len(fj))
made("synthetic.RAF", bytes(hdr) + fj + raw_noise, 1920)
# Olympus ORF: "IIRO", the raw strip in IFD0, a thumbnail chained in IFD1, and the real preview hidden in the
# maker's notes (not pointed to by any directory we read), with a nested thumbnail inside its own Exif
olymp_prev = jpeg(3200, 2400, (180, 120, 60), nested_thumb=True)
makernote = b"OLYMPUS\x00II\x03\x00" + b"\0" * 64 + olymp_prev + b"\0" * 32
orf = tiff("II", b"\x52\x4f", [
    [(0x0111, 4, 1, "raw"), (0x0117, 4, 1, ("len", "raw"))],
], {"mn": makernote, "thumb": thumb, "raw": raw_noise})
made("synthetic.ORF", orf, 3200)
# Pentax PEF, big-endian, only a 160 px thumbnail pointed to; the preview sits in the notes
pef = tiff("MM", b"\x00\x2a", [[(0x0201, 4, 1, "thumb"), (0x0202, 4, 1, ("len", "thumb"))]], {"thumb": thumb, "mn": b"AOC\0MM" + jpeg(1280, 853, (90, 30, 90))})
made("synthetic.PEF", pef, 1280)
# junk and damage
for ext in (".NEF", ".ORF", ".ARW", ".RW2", ".RAF", ".PEF", ".CR3", ".CR2", ".DNG", ".SRW", ".IIQ"):
    made("junk" + ext, bytes(random.getrandbits(8) for _ in range(200000)), None)
made("tiny.NEF", b"MM\x00\x2a\x00\x00\x00\x08", None)
made("empty.CR2", b"", None)
made("fake-header.RAF", b"FUJIFILMCCD-RAW " + b"\xff" * 200, None)
# a TIFF whose directory points far past the end of the file, and one that points at itself (a loop)
loop = bytearray(b"II*\x00\x08\x00\x00\x00" + struct.pack("<H", 1) + struct.pack("<HHII", 0x014A, 4, 1, 8) + struct.pack("<I", 8) + b"\0" * 2000)
made("loop.NEF", bytes(loop), None)
made("far.NEF", b"II*\x00" + struct.pack("<I", 0x7FFFFFF0) + b"\0" * 5000, None)
# real RAWs cut short, and with their stored JPEG damaged (only when a folder of them is given)
for f in sorted(RAWS.glob("*.*")) if RAWS and RAWS.is_dir() else []:
    if f.suffix.upper() not in (".CR2", ".CR3", ".DNG"): continue
    whole = f.read_bytes()
    for cut in (64, 4096, 65536, 1 << 20, 3 << 20):
        p = D / f"cut{cut}-{f.name}"; p.write_bytes(whole[:cut])
        ok = pictures.make_jpeg(p, D / (p.name + ".jpg"), 700)
        why = pictures.why_not(p) if not ok else None
        check(f"{f.name} cut to {cut} bytes: " + ("a preview from what is left" if ok else f"no preview, words: {why!r}"), ok or bool(why))
    # every stored JPEG damaged in its middle: still no crash; either a picture or plain words
    gen = pictures._raw_jpegs(f); 
    try: blobs = [bytes(x) for x in gen]
    finally: gen.close()
    dam = bytearray(whole)
    for jb in blobs:
        i = whole.find(jb[:64])
        if i > 0:
            mid = i + len(jb) // 2
            dam[mid:mid + 4096] = bytes(4096)
    p = D / f"damaged-{f.name}"; p.write_bytes(bytes(dam))
    ok = pictures.make_jpeg(p, D / (p.name + ".jpg"), 700)
    check(f"{f.name} with its stored JPEGs damaged: " + ("a picture (the damage is greyed, not a crash)" if ok else f"no picture, words: {pictures.why_not(p)!r}"), True)
# a HEIC with no add-on, a folder called .CR2, a file that cannot be opened
(D / "phone.HEIC").write_bytes(b"\0\0\0\x18ftypheic\0\0\0\0mif1heic" + b"\0" * 5000)
ok = pictures.make_jpeg(D / "phone.HEIC", D / "phone.jpg", 700)
w = pictures.why_not(D / "phone.HEIC")
check(f"HEIC with no add-on: no picture, words: {w!r}", not ok and w and "pillow-heif" in w)
(D / "folder.CR2").mkdir(exist_ok=True)
check("a folder named like a RAW: no picture, no crash", not pictures.make_jpeg(D / "folder.CR2", D / "folder.jpg", 700))
if os.name != "nt" and hasattr(os, "getuid") and os.getuid() != 0:   # Windows has no "unreadable to its owner"
    locked = D / "locked.NEF"; locked.write_bytes(nef); os.chmod(locked, 0)
    check("a RAW that cannot be read: no picture, no crash", not pictures.make_jpeg(locked, D / "locked.jpg", 700)); os.chmod(locked, 0o644)
check("a missing file: no picture, no crash", not pictures.make_jpeg(D / "nope.CR2", D / "nope.jpg", 700))
check("thumb_rows on junk: None", pictures.thumb_rows(D / "junk.NEF", 240) is None)
check("size_of on junk: None", pictures.size_of(D / "junk.NEF") is None)
print(f"\n{ran - fails} of {ran} passed." + ("" if not fails else f"  (scratch folder: {D})"))
if not fails:
    shutil.rmtree(D, ignore_errors=True)
sys.exit(1 if fails else 0)
