#!/usr/bin/env python3
"""The four tiles are shortcuts (Nicole's v30, section 4; screenshots 02 and 03): what the home page's "Create a reel:
which shoot?" box asks the page server.

    GET  /make-list            {ok, kits: [{folder, name, date, photos, thumb, go}], vault: {thumbs} | null}
                               every post kit the post kits screen lists and has not archived, newest first (never
                               My vault, which comes first on its own row); `go` the four pages each lands on
    GET  /make-new-status      what "+ A new shoot" is doing: {state, words, done, of, go} (new_shoot.job)
    POST /make-new   {}        "+ A new shoot": the computer's own folder picker, then new_shoot.py make --job,
                               detached; a cancelled picker changes nothing
    POST /make-vault {"make"}  My vault: made if there is none (vault.ensure, the guarded way its own card makes it),
                               then the page it lands on (new_shoot.vault_go)

Every POST is checked the way arrange.py checks its own (this server's Host, its own Origin when sent, JSON, a short
body, never another website's). Never a path on the page: a kit is its folder's name, a picture a /kit-thumb address.
"""
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import new_shoot  # noqa: E402
import this_computer  # noqa: E402

GET_ROUTES = ("/make-list", "/make-new-status")
POST_ROUTES = ("/make-new", "/make-vault")
POST_CAP = 200
VAULT_THUMBS = 4

# Ours, every one a draft for Dustin and Nicole.
OUR_WORDS = {
    "no_folder": "No folder chosen.",
    "no_window_mac": "The folder window didn't open. Tell your assistant which folder your finished photos are in, and it'll make the shoot for you.",
    "no_window_pc": ("The folder window didn't open. Tell your assistant which folder your finished photos are in (you can copy its "
                     "address from the top of its File Explorer window), and it'll make the shoot for you."),
    "cant_start": "Couldn't start the copy. Try again in a moment.",
    "didnt_work": "That didn't work. Try again in a moment.",
}


def _log(msg):
    try:
        print("make: " + msg, flush=True)
    except (BrokenPipeError, OSError, ValueError):
        pass


def _send(handler, obj, code=200):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    try:
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        pass


def _cross_site(handler):
    return (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site"


def thumb(kit_folder, i=1):
    return f"/kit-thumb?kit={quote(kit_folder, safe='')}&i={i}"


def listing():
    """What the box lists: the post kits (home_base.kits: the ones the post kits screen shows, newest first), not
    archived, and My vault's little mosaic (up to four shoots' pictures) when there are any."""
    import home_base
    kits = []
    for k in home_base.kits():
        if k.get("archived"):
            continue
        kits.append({"folder": k["folder"], "name": k["name"], "date": k.get("date") or "", "photos": k.get("photos") or 0,
                     "thumb": thumb(k["folder"]), "go": new_shoot.go(k["folder"])})
    vault = None
    if kits:
        with_photos = [k["folder"] for k in kits if k["photos"]][:VAULT_THUMBS]
        vault = {"thumbs": [thumb(f, 2) for f in with_photos]}
    return {"ok": True, "kits": kits, "vault": vault}


def handle_get(handler, path, query):
    import arrange
    try:
        if not arrange.our_host(handler) or _cross_site(handler):
            return _send(handler, {"ok": False}, 403)
        if path == "/make-list":
            return _send(handler, listing())
        if path == "/make-new-status":
            return _send(handler, dict(new_shoot.job(), ok=True))
        return _send(handler, {"ok": False}, 404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        return _send(handler, {"ok": False, "words": OUR_WORDS["didnt_work"]}, 500)


def _start(folder):
    """`new_shoot.py make "<folder>" --job`, detached so it outlives this request (and the page server)."""
    new_shoot.job_write(state="working", words=new_shoot.WORDS["starting"], done=0, of=0)
    logs = new_shoot.HOME / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    with open(logs / "new-shoot.log", "ab") as out:
        p = this_computer.popen_detached([sys.executable, str(HERE / "new_shoot.py"), "make", str(folder), "--job"],
                                         stdin=subprocess.DEVNULL, stdout=out, stderr=out)
    new_shoot.job_write_pid(p.pid)
    return p


def handle_post(handler, path, query):
    import arrange
    try:
        refused = arrange.guard(handler, "application/json", POST_CAP, path)
        if refused is None and _cross_site(handler):
            refused = (403, arrange.NOT_UNDERSTOOD)
        if refused:
            arrange._drain(handler)
            return _send(handler, {"ok": False, "words": refused[1]}, refused[0])
        n = int(handler.headers.get("Content-Length"))
        try:
            body = json.loads(handler.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return _send(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 400)

        if path == "/make-vault":
            if not isinstance(body, dict) or set(body) != {"make"} or body["make"] not in new_shoot.MAKES:
                return _send(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 400)
            import vault
            try:
                v, made = vault.ensure()
                try:
                    vault.relist(v, quick=True)
                except vault.Trouble:
                    pass                            # another look is listing it right now: the page opens all the same
            except vault.Trouble as t:
                return _send(handler, {"ok": False, "words": str(t)})
            if made:
                _log(f"made the vault ({v.name})")
            return _send(handler, {"ok": True, "url": new_shoot.vault_go(v.name)[body["make"]]})

        if path == "/make-new":
            if body != {}:
                return _send(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 400)
            if new_shoot.job()["state"] == "working":
                return _send(handler, {"ok": True, "state": "working", "words": new_shoot.WORDS["busy"]})
            folder, why = this_computer.pick_folder("Pick the folder with your finished photos. The Assistant copies the photos; nothing is moved.")
            if not folder:
                if why == "cancelled":
                    return _send(handler, {"ok": False, "cancelled": True, "words": OUR_WORDS["no_folder"]})
                return _send(handler, {"ok": False, "words": OUR_WORDS["no_window_pc" if this_computer.WINDOWS else "no_window_mac"]})
            try:
                _start(folder)
            except OSError as e:
                _log(f"couldn't start the copy ({e.__class__.__name__})")
                new_shoot.job_write(state="stopped", words=OUR_WORDS["cant_start"], done=0, of=0)
                return _send(handler, {"ok": False, "words": OUR_WORDS["cant_start"]})
            return _send(handler, {"ok": True, "state": "working", "words": new_shoot.WORDS["starting"]})

        return _send(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        return _send(handler, {"ok": False, "words": OUR_WORDS["didnt_work"]}, 500)
