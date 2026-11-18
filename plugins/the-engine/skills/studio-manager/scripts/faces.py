#!/usr/bin/env python3
"""Where the faces are in a kit's photos, for the home page's hello (Nicole's v28, Nov 17: "you need to find the
face and then center the image around the face").

Hers is a small Swift tool (faces.swift). Ours asks the Mac's own Vision the way the sneak-peek check and the clip
stills already do (this_computer.mac_javascript): nothing to build, nothing shipped, nothing sent anywhere, and
Vision on a file on this computer asks no permission. What comes back is hers, field for field:

    {"w": px, "h": px, "faces": [[x, y, w, h], ...]}

each face a box from the TOP LEFT, 0 to 1, of the photo as it is looked at (a turn mark in the file is followed,
so a photo stored sideways gives its upright width, height and boxes), only faces Vision is more than 0.6 sure of
(CONFIDENCE, hers).

What is looked at is never the photo itself: only the small copy (520 px) the kit already makes for its pages
(arrange.py, .kit/previews). So it is fast (a dozen copies in well under a second on Dustin's Mac) and a 60 MB
original is never opened here.

Every copy that is not known yet goes through ONE run (starting the run is the slow part). The answers are kept in

    ~/.studio/faces.json      {"v": 1, "faces": {"<kit folder>/<small copy's file name>": {"w", "h", "faces"}}}

keyed by the kit and the small copy's own name, which already carries the photo's name, size and modified time
(arrange.preview_file): a photo exported again has a new copy, a new name, and is looked at again. Each photo is
looked at once, ever. It is a cache: losing it only means looking again.

A PC has no Vision, and a Mac where Vision fails gives nothing: every photo then simply has no faces, nothing is
kept, and the page centers the photo. (The named PC gap: on a PC the hello's photos are centered, not framed on
faces.)

Route (on the posting server, for the Assistant's own pages only; never a path in or out):
    GET /kit-faces?kit=<kit folder>&n=1,2,3      up to 24 numbers -> {"ok": true, "faces": {"1": {w, h, faces}, ...}}
A number with no small copy yet, or that Vision could not read, is simply not in the answer.

    python3 faces.py kit "<kit folder name>" 1 2 3      print what the route answers (looks, and keeps what it finds)

Python 3.9, standard library only.
"""
import json
import os
import re
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402
this_computer.utf8_output()

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
CACHE = HOME / "faces.json"
CONFIDENCE = 0.6            # hers: a face Vision is less sure of than this is left out
MOST = 24                   # hers: several at once, up to 24
KEEP = 6000                 # the list is trimmed to its newest 4000 past this (a cache, never a record)
GET_ROUTES = ("/kit-faces",)

# One run for every picture given. The turn mark is read from the file (CIImage's properties) and handed to
# Vision, so the boxes and the width and height are those of the picture standing upright. Vision's boxes start
# at the bottom left; hers (and the page's) start at the top left.
FACES_JS = r"""
ObjC.import('Vision'); ObjC.import('Foundation'); ObjC.import('AppKit'); ObjC.import('CoreImage');
function run(argv) {
  var least = parseFloat(argv[0]), all = [];
  for (var a = 1; a < argv.length; a++) {
    var out = {w: 0, h: 0, faces: [], ok: false};
    try {
      var url = $.NSURL.fileURLWithPath(argv[a]);
      var o = 1, w = 0, h = 0;
      var ci = $.CIImage.imageWithContentsOfURL(url);
      if (ci && !ci.isNil()) {
        var e = ci.extent; w = Math.round(e.size.width); h = Math.round(e.size.height);
        var p = ci.properties;
        if (p && !p.isNil()) { var v = p.objectForKey('Orientation'); if (v && !v.isNil()) o = v.intValue; }
      }
      if (!(o >= 1 && o <= 8)) o = 1;
      if (o >= 5) { var t = w; w = h; h = t; }
      out.w = w; out.h = h;
      if (w > 0 && h > 0) {
        var hd = $.VNImageRequestHandler.alloc.initWithURLOrientationOptions(url, o, $());
        var rc = $.VNDetectFaceRectanglesRequest.alloc.init;
        out.ok = !!hd.performRequestsError($([rc]), Ref());
        var r = rc.results;
        if (r && !r.isNil()) for (var i = 0; i < r.count; i++) {
          var f = r.objectAtIndex(i); if (!(f.confidence > least)) continue;
          var b = f.boundingBox;
          out.faces.push([b.origin.x, 1 - b.origin.y - b.size.height, b.size.width, b.size.height]);
        }
      }
    } catch (err) { out.ok = false; }
    all.push(out);
  }
  return JSON.stringify(all);
}
"""

_LOCK = threading.Lock()        # the kept list: read, added to and saved by one thread at a time
_LOOK = threading.Lock()        # one look at a time: two pages opened together never start two runs for the same photos
_KEPT = {"at": None, "faces": {}}


def _clean(d):
    """One answer as the page gets it, or None when it is not one: whole numbers for the size, each face four
    numbers from 0 to 1 (three decimals, hers)."""
    try:
        w, h = int(d["w"]), int(d["h"])
        if w <= 0 or h <= 0 or w > 100000 or h > 100000:
            return None
        out = []
        for f in d["faces"]:
            if len(f) != 4:
                return None
            box = [round(min(1.0, max(0.0, float(x))), 3) for x in f]
            if box[2] > 0 and box[3] > 0:
                out.append(box)
        return {"w": w, "h": h, "faces": out[:40]}
    except (KeyError, TypeError, ValueError):
        return None


def find(paths):
    """Ask this computer where the faces are in these pictures, all in one run. A list as long as paths: for each,
    {"w", "h", "faces"} or None (not read). On a PC, or when the Mac's Vision does not answer, every one is None.
    FACES_PRETEND (the tests' own): a JSON file {"<file name>": {w, h, faces}}, or "none" for a computer that has
    no face finder; nothing is run then."""
    paths = [str(p) for p in paths]
    if not paths:
        return []
    pretend = os.environ.get("FACES_PRETEND")
    if pretend:
        try:
            table = {} if pretend == "none" else json.loads(Path(pretend).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            table = {}
        return [_clean(table[Path(p).name]) if isinstance(table.get(Path(p).name), dict) else None for p in paths]
    try:
        r = this_computer.mac_javascript(FACES_JS, [CONFIDENCE, *paths], timeout=20 + 3 * len(paths))
        if not r or r[0] != 0:                      # None: a PC. Not 0: the Mac's scripting said no.
            return [None] * len(paths)
        got = json.loads(r[1])
        if not isinstance(got, list) or len(got) != len(paths):
            return [None] * len(paths)
        return [_clean(d) if isinstance(d, dict) and d.get("ok") else None for d in got]
    except Exception:  # noqa: BLE001  (a run that took too long, an answer that is not JSON: no faces, never a crash)
        return [None] * len(paths)


def _kept():
    """The kept list, read again only when the file has changed. Call with _LOCK held."""
    try:
        st = CACHE.stat()
        at = (st.st_mtime_ns, st.st_size)
    except OSError:
        at = None
    if at != _KEPT["at"]:
        faces = {}
        if at is not None:
            try:
                d = json.loads(CACHE.read_text(encoding="utf-8"))
                if isinstance(d, dict) and isinstance(d.get("faces"), dict):
                    faces = {k: v for k, v in d["faces"].items() if isinstance(k, str) and isinstance(v, dict)}
            except (OSError, ValueError):
                faces = {}
        _KEPT["at"], _KEPT["faces"] = at, faces
    return _KEPT["faces"]


def _keep(new):
    """Add what was just found and save the list whole (a scratch file put in place). A list that can't be saved
    is no trouble: the photos are looked at again next time. Call with _LOCK held."""
    faces = dict(_kept())
    faces.update(new)
    if len(faces) > KEEP:
        faces = dict(list(faces.items())[-4000:])
    tmp = CACHE.with_name(f"{CACHE.name}.{os.getpid()}-{threading.get_ident()}.tmp")
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps({"v": 1, "faces": faces}, ensure_ascii=False), encoding="utf-8")
        this_computer.replace(tmp, CACHE)
        st = CACHE.stat()
        _KEPT["at"], _KEPT["faces"] = (st.st_mtime_ns, st.st_size), faces
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        _KEPT["faces"] = faces              # still known for as long as this program runs


def for_kit(kit, numbers):
    """{number: {"w", "h", "faces"}} for these numbered photos of a kit (a folder arrange.kit_by_name found), from
    the kept list, and one look for every small copy not known yet. A number that is not on the kit's list, has
    no small copy yet, or could not be read is left out."""
    import arrange
    import kit as kit_mod
    rows = {r["n"]: r for r in arrange.sheet_rows(kit)}
    rec = kit_mod.load_rec(kit)
    copies = {}
    for n in numbers:
        if n in rows and n not in copies:
            f = arrange.copy_to_serve(kit, rec, rows[n], arrange.SIZES["s"])
            if f is not None:
                copies[n] = f
    out = {}
    with _LOOK:
        with _LOCK:
            kept = _kept()
            for n, f in copies.items():
                d = kept.get(f"{kit.name}/{f.name}")
                d = _clean(d) if d else None
                if d:
                    out[n] = d
        new = [n for n in copies if n not in out]
        if new:
            found = find([copies[n] for n in new])
            add = {}
            for n, d in zip(new, found):
                if d:
                    out[n] = d
                    add[f"{kit.name}/{copies[n].name}"] = d
            if add:
                with _LOCK:
                    _keep(add)
    return out


# ---------- the route ----------

def _answer(handler, obj, code=200):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    try:
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        pass


def numbers_of(text):
    """ "1,2,3" as [1, 2, 3]: 1 to MOST whole numbers, each once. None for anything else."""
    if not isinstance(text, str) or not re.fullmatch(r"[0-9]{1,6}(,[0-9]{1,6}){0,%d}" % (MOST - 1), text):
        return None
    out = []
    for x in text.split(","):
        n = int(x)
        if n >= 1 and n not in out:
            out.append(n)
    return out or None


def handle_get(handler, path, query):
    """GET /kit-faces: only for this server's own pages (its own name in Host, never another website's ask), a kit
    found by its exact folder name in Your Content, numbers only. Whatever goes wrong, the server answers."""
    try:
        import arrange
        if not arrange.our_host(handler) or (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
            return _answer(handler, {"ok": False}, 403)
        try:
            q = parse_qs(query or "", keep_blank_values=True)
        except ValueError:
            return _answer(handler, {"ok": False}, 404)
        names, ns = q.get("kit") or [], q.get("n") or []
        numbers = numbers_of(ns[0]) if len(ns) == 1 else None
        kit = arrange.kit_by_name(names[0]) if len(names) == 1 else None
        if path != "/kit-faces" or kit is None or numbers is None or set(q) - {"kit", "n"}:
            return _answer(handler, {"ok": False}, 404)
        got = for_kit(kit, numbers)
        return _answer(handler, {"ok": True, "faces": {str(n): got[n] for n in numbers if n in got}})
    except (Exception, SystemExit) as e:  # noqa: BLE001
        try:
            print(f"faces: GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}", flush=True)
        except (BrokenPipeError, OSError):
            pass
        try:
            _answer(handler, {"ok": False}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "kit" and all(a.isdigit() for a in sys.argv[3:]):
        import arrange
        kit = arrange.kit_by_name(sys.argv[2])
        if kit is None:
            print("STOP: no post kit by that exact folder name in Your Content.")
            return 2
        got = for_kit(kit, [int(a) for a in sys.argv[3:]][:MOST])
        print(json.dumps({"ok": True, "faces": {str(n): d for n, d in got.items()}}, indent=1))
        return 0
    print(__doc__.split("\n\n")[0])
    return 2


if __name__ == "__main__":
    sys.exit(main())
