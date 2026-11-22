#!/usr/bin/env python3
"""Sample photos for a brand-new Assistant (Nicole's v30, section 6).

A few photos Nicole chooses ship in the plugin's `samples` folder (beside `scripts`). Until the photographer's
first post kit exists, the home page's hello and its four tiles show them, with the line "Sample photos. Yours
show up here after your first shoot." Once a first post kit exists they disappear on their own. They are never a
kit, so they count in nothing (the numbers, the recap, the hello's facts, the posting queue), and no other page
asks for them. With the folder empty (as it ships until Nicole chooses), the grey placeholders stay.

    GET /home-sample?name=<file name>   one sample photo, by its exact file name in the folder (never a path)
    GET /home-sample-faces              {ok, faces: {name: {w, h, faces}}} where the faces are in each sample

    python3 samples.py show             what is in the folder, and whether the home page would use it now

STUDIO_SAMPLES_FOR_TESTS (the tests' own): another folder to read the samples from.
"""
import json
import os
import stat as stat_mod
import struct
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FOLDER = HERE.parent / "samples"
KINDS = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
MOST = 12                   # photos read from the folder (hers: 8 to 10)
BIGGEST = 6_000_000         # a 1600 px sample is well under 1 MB; anything this big is not one
GET_ROUTES = ("/home-sample", "/home-sample-faces")
WIDE = 1.15                 # wider than tall by this much: a photo for the hello's wide strip
HELLO_MOST = 8
HELLO_FEW = 3
TILES = 4
TILE_CANDS = 6

# Hers (UPDATE-v30 section 6: "for example"), used whole.
WORDS = {"note": "Sample photos. Yours show up here after your first shoot."}

_LOCK = threading.Lock()
_DIMS = {}                  # (name, size, mtime) -> (w, h) or None, for as long as this program runs
_FACES = {}                 # (name, size, mtime) -> faces or None


def folder():
    d = os.environ.get("STUDIO_SAMPLES_FOR_TESTS")
    return Path(d) if d else FOLDER


def _key(st, name):
    return (name, st.st_size, st.st_mtime_ns)


def listed():
    """[(name, stat)] of the sample photos, in name order: plain files in the folder itself (no link, no hidden
    file, no folder), a photo's ending, not empty and not too big. Nothing in the folder, or no folder: []."""
    d = folder()
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return []
    out = []
    for n in names:
        if n.startswith(".") or "/" in n or "\\" in n or Path(n).suffix.lower() not in KINDS:
            continue
        try:
            st = os.lstat(d / n)
        except OSError:
            continue
        if not stat_mod.S_ISREG(st.st_mode) or st.st_size <= 0 or st.st_size > BIGGEST:
            continue
        out.append((n, st))
        if len(out) >= MOST:
            break
    return out


def _dims(path):
    """(width, height) from a JPEG's or PNG's own header, or None. Nothing installed, nothing decoded."""
    try:
        with open(path, "rb") as f:
            head = f.read(26)
            if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
                f.seek(16)
                return struct.unpack(">II", f.read(8))
            if head[:2] != b"\xff\xd8":
                return None
            f.seek(2)
            for _ in range(500):
                b = f.read(1)
                while b and b != b"\xff":
                    b = f.read(1)
                while b == b"\xff":
                    b = f.read(1)
                if not b:
                    return None
                m = b[0]
                if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                    continue
                ln = f.read(2)
                if len(ln) < 2:
                    return None
                size = struct.unpack(">H", ln)[0]
                if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    data = f.read(5)
                    h, w = struct.unpack(">HH", data[1:5])
                    return (w, h) if w and h else None
                f.seek(size - 2, 1)
    except (OSError, struct.error):
        return None
    return None


def no_kit_yet():
    """True when the photographer has no post kit at all (archived ones count as one; My vault does not)."""
    try:
        import home_base
        return not home_base.kits()
    except (Exception, SystemExit):  # noqa: BLE001  (can't tell: no samples, never a sample beside real photos)
        return False


def for_home():
    """What the home page uses: None when it shows no samples (a post kit exists, or the folder has no photos),
    else {"hello": [names], "tiles": [[names] x 4], "note": words}. Names only, never a path."""
    got = listed()
    if not got or not no_kit_yet():
        return None
    d = folder()
    wide, other = [], []
    for n, st in got:
        k = _key(st, n)
        with _LOCK:
            if k not in _DIMS:
                _DIMS[k] = _dims(d / n)
            wh = _DIMS[k]
        (wide if wh and wh[0] >= wh[1] * WIDE else other).append(n)
    hello = wide[:HELLO_MOST]
    if len(hello) < HELLO_FEW:
        hello += other[:HELLO_MOST - len(hello)]
    first = hello[:1]
    rest = [n for n in other + wide if n not in first] or [n for n, _ in got]
    tiles = []
    for i in range(TILES):
        cands = rest[i::TILES][:TILE_CANDS] or [rest[i % len(rest)]]
        tiles.append(cands)
    return {"hello": hello, "tiles": tiles, "note": WORDS["note"]}


def faces():
    """{name: {w, h, faces}} for the samples the Mac's own face finder could read (faces.find); remembered for as
    long as this program runs, and written nowhere. A PC, or no faces: {} (the page centres the photos)."""
    got = listed()
    d = folder()
    with _LOCK:
        new = [(n, st) for n, st in got if _key(st, n) not in _FACES]
    if new:
        import faces as faces_mod
        found = faces_mod.find([d / n for n, _ in new])
        with _LOCK:
            for (n, st), fc in zip(new, found):
                _FACES[_key(st, n)] = fc
    out = {}
    with _LOCK:
        for n, st in got:
            fc = _FACES.get(_key(st, n))
            if fc:
                out[n] = fc
    return out


# ---------- the routes ----------

def _send(handler, code, body, kind, cache="no-store"):
    try:
        handler.send_response(code)
        handler.send_header("Content-Type", kind)
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", cache)
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        pass


def _json(handler, obj, code=200):
    _send(handler, code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")


def handle_get(handler, path, query):
    """Only this server's own page (its own Host, never another website), only a name that is one of listed()
    exactly, and only while the home page would show samples. Anything else: 404 with nothing in it."""
    import arrange
    try:
        if not arrange.our_host(handler) or (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
            return _json(handler, {"ok": False}, 403)
        if not no_kit_yet():
            return _json(handler, {"ok": False}, 404)
        if path == "/home-sample-faces":
            return _json(handler, {"ok": True, "faces": faces()})
        if path != "/home-sample":
            return _json(handler, {"ok": False}, 404)
        try:
            names = parse_qs(query or "", strict_parsing=False).get("name") or []
        except ValueError:
            names = []
        name = names[0] if len(names) == 1 else None
        hit = next(((n, st) for n, st in listed() if n == name), None) if name else None
        if not hit:
            return _json(handler, {"ok": False}, 404)
        p = folder() / hit[0]
        with open(p, "rb") as f:
            body = f.read(BIGGEST + 1)
        if len(body) > BIGGEST:
            return _json(handler, {"ok": False}, 404)
        return _send(handler, 200, body, KINDS[Path(hit[0]).suffix.lower()], cache="private, max-age=300")
    except (Exception, SystemExit):  # noqa: BLE001
        try:
            _json(handler, {"ok": False}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def main():
    args = sys.argv[1:]
    if args[:1] != ["show"]:
        print(__doc__.strip())
        return 0
    got = listed()
    print(f"{len(got)} sample photo{'' if len(got) == 1 else 's'} in the plugin's samples folder.")
    for n, st in got:
        print(f"  {n}  ({st.st_size // 1024} KB)")
    print("The home page shows them now." if for_home() else
          "The home page shows them only until the first post kit exists." if got else
          "With none, the home page keeps its grey placeholders.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
