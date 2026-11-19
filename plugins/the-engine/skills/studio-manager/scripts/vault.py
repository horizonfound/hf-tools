#!/usr/bin/env python3
"""
My vault: one post kit that draws from every shoot (Nicole's v29, section 1.3).

The vault is a real folder in Your Content, like any post kit, so every page that works on a post kit works on
it. What makes it the vault is the mark in its record ({"name": "My vault", "vault": true}); it is found by that
mark, never by its name (a shoot already called "My vault" leaves the vault as "My vault 2").

Its numbered list (.kit/sheet.json) is REFERENCES. Each row is the usual n, file, w, h, way, plus:
    kit   the folder name of the post kit the photo is in ("" for a photo in the vault's own Photos folder)
    src   that post kit's own number for the photo (for the vault's own photos: the same as n)
No photo is copied to be in the vault. THE VAULT ONLY READS OTHER POST KITS: nothing here writes into one.

Numbers never move. .kit/vault.json keeps
    {"numbers": {"<kit folder>#<src>": n, "own:<file name>": n}, "next": N, "out": {"photos": {key: when}, ...},
     "from": what the list was made from}
A photo keeps its vault number for good. A photo that is gone (its own post kit's list no longer has it, the kit
is gone, or it was taken out of the vault) keeps its number unused, under "retired", and comes back to it. A post
kit whose drive is unplugged keeps its rows: only what a kit's own list calls gone is gone.

This script is the one writer of the vault's list.

    python3 vault.py show              where the vault is, how many shoots and photos (never makes it)
    python3 vault.py ensure            make the vault if there is none (twice makes one), then list its photos
    python3 vault.py relist [--sheets] bring the list up to date; --sheets also draws the numbered contact sheets
    python3 vault.py members           the post kits in it
"""
import argparse
import hashlib
import json
import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import posts  # noqa: E402
import this_computer  # noqa: E402

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
NAME = "My vault"                   # the name in its record, and its folder's name when that is free
MARK = "vault"                      # the field in kit.json (and in sheet.json) that says "this is the vault"
OWN = ""                            # a row's "kit" for a photo in the vault's own Photos folder
FOLDERS = ("Photos", "Footage", "Music", "Talking", "Carousel", "Stories", "Reels")
WHATS = ("photos", "clips")         # what can be taken out of the vault (stage 11 uses it)
NAMES_MOST = 99                     # "My vault 99": past that something is badly wrong, and nothing is made


class Trouble(RuntimeError):
    """Plain words for whoever asked; nothing was changed."""


def say(msg):
    try:
        print(msg, flush=True)
    except (BrokenPipeError, OSError):
        pass


def _nfc(s):
    return unicodedata.normalize("NFC", str(s))


def _kit():
    import kit as kit_mod
    return kit_mod


def _json(p):
    try:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_whole(path, obj):
    """Whole or not at all: a scratch name of this process's own, then put in place."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
        this_computer.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()            # our own scratch copy, never the real file
        except OSError:
            pass
        raise


# ---------- which folder is the vault, and who is in it ----------

def content():
    """Your Content, or None when the Assistant's folder is not set up or not there right now."""
    try:
        h = posts.home()
    except (Exception, SystemExit):  # noqa: BLE001
        return None
    if not h:
        return None
    c = h / posts.CONTENT_NAME
    return c if c.is_dir() else None


def _kit_dirs(c):
    """Every real folder in Your Content that holds a kit record, by name. Never a link."""
    out = []
    try:
        names = sorted(os.listdir(c))
    except OSError:
        return out
    for name in names:
        if name.startswith("."):
            continue
        d = c / name
        try:
            if d.is_symlink() or not d.is_dir() or not (d / ".kit" / "kit.json").is_file():
                continue
        except OSError:
            continue
        out.append(d)
    return out


def is_vault(kit_or_rec):
    """Is this the vault? A kit's record (a dict) or its folder. Only the mark counts, never the name."""
    if isinstance(kit_or_rec, dict):
        return kit_or_rec.get(MARK) is True
    if kit_or_rec is None:
        return False
    return _json(Path(kit_or_rec) / ".kit" / "kit.json").get(MARK) is True


def find():
    """The vault's folder, or None. Found by the mark in its record; if two folders ever carry it, the first by
    name is the vault."""
    c = content()
    if c is None:
        return None
    for d in _kit_dirs(c):
        if is_vault(d):
            return d
    return None


def who(name):
    """A piece's "who" for the vault, whole ("My vault reel is waiting", never "My's reel"); None for any other
    name, so the caller goes on with its own rule. The one helper every such line asks."""
    name = str(name or "").strip()
    return name if name == NAME else None


def _free_name(c):
    """"My vault", or "My vault 2"... when a folder is already called that (capitals and accents aside)."""
    try:
        taken = {_nfc(e).casefold() for e in os.listdir(c)}
    except OSError:
        taken = set()
    for i in range(1, NAMES_MOST + 1):
        name = NAME if i == 1 else f"{NAME} {i}"
        if _nfc(name).casefold() not in taken:
            return name
    raise Trouble("There are too many folders called My vault in Your Content. Nothing was made.")


def ensure():
    """The vault's folder, made if there is none: (folder, True when it was made just now). Under one lock, so two
    asks at once make one. Made only here (a command, or a guarded press), never because a page was loaded.
    Raises Trouble when the Assistant's folder is not set up or not there."""
    c = content()
    if c is None:
        raise Trouble("The Assistant's folder isn't set up yet, or its drive isn't plugged in. Nothing was made.")
    kit_mod = _kit()
    HOME.mkdir(parents=True, exist_ok=True)
    with kit_mod._held(HOME / "vault.lock", 30.0) as got:
        if got is False:
            raise Trouble("The vault is being made right now. Try again in a moment.")
        v = find()
        if v is not None:
            return v, False
        v = c / _free_name(c)
        v.mkdir()
        for sub in FOLDERS:
            (v / sub).mkdir(exist_ok=True)
        hid = kit_mod.hidden(v)
        _write_whole(hid / "sheet.json", {MARK: True, "folder": str(v / "Photos"), "photos": [], "retired": []})
        _write_whole(hid / "vault.json", {"numbers": {}, "next": 1, "out": {}, "from": None})
        # the record last: a folder without it is not the vault (and not a post kit), so a make cut off before
        # this line leaves a plain folder, and the next ask makes "My vault 2" beside it rather than half a vault
        kit_mod.save_rec(v, {"name": NAME, MARK: True, "folder": v.name, "source": "vault",
                             "made": datetime.now().isoformat(timespec="seconds")})
        return v, True


def members(vault_kit=None):
    """Every other post kit, newest first: {folder, name, date, photos, listed, path}. `photos` is the count on the
    kit's own numbered list; `listed` is False for a kit that has no list yet (its photos join the vault once it
    has one: the vault never writes a list into another kit). Archived kits are in it like any other."""
    c = content()
    if c is None:
        return []
    out = []
    for d in _kit_dirs(c):
        rec = _json(d / ".kit" / "kit.json")
        if rec.get(MARK) is True:
            continue                            # one level only: the vault is never in the vault
        sheet = d / ".kit" / "sheet.json"
        rows = _rows(sheet)
        day = rec.get("date") if isinstance(rec.get("date"), str) else ""
        out.append({"folder": d.name, "name": str(rec.get("name") or d.name), "date": day, "photos": len(rows),
                    "listed": sheet.is_file(), "path": d})
    out.sort(key=lambda m: (m["date"], m["folder"]), reverse=True)
    return out


def _rows(sheet_file):
    """A numbered list's rows, as arrange.sheet_rows reads them; [] when there is none or it can't be read."""
    try:
        d = json.loads(Path(sheet_file).read_text(encoding="utf-8"))
        return [x for x in d.get("photos", []) if isinstance(x, dict) and type(x.get("n")) is int and x["n"] >= 1
                and isinstance(x.get("file"), str) and x["file"]]
    except (OSError, ValueError, AttributeError, TypeError):
        return []


# ---------- where a row's photo is ----------

_REC = {}                           # a member's folder -> (its record's time and size, the photos folder or None)


def _member_photos(d):
    """The photos folder of a post kit beside the vault, read from that kit's own record (kept until the record
    changes). None when it is no kit, a link, or the vault itself."""
    rec_file = d / ".kit" / "kit.json"
    try:
        st = rec_file.stat()
    except OSError:
        return None
    key = (st.st_mtime_ns, st.st_size)
    hit = _REC.get(str(d))
    if hit and hit[0] == key:
        return hit[1]
    rec = _json(rec_file)
    folder = None
    try:
        if not d.is_symlink() and rec.get(MARK) is not True:
            folder = Path(rec["photos_dir"]) if isinstance(rec.get("photos_dir"), str) and rec["photos_dir"] else d / "Photos"
    except OSError:
        folder = None
    if len(_REC) > 500:
        _REC.clear()
    _REC[str(d)] = (key, folder)
    return folder


def row_file(vault_kit, row):
    """Where a row of the vault's list says its photo is (it may not be there right now), or None. A row from a
    post kit: that kit's photos folder as its own record names it today, and the row's file NAME. A row of the
    vault's own: its Photos folder. One level only: a member is never the vault."""
    try:
        name = Path(row["file"]).name
        member = row.get("kit")
        if not name or name.startswith(".") or not isinstance(member, str):
            return None
        vault_kit = Path(vault_kit)
        if member == OWN:
            return vault_kit / "Photos" / name
        if "/" in member or "\\" in member or "\x00" in member or member.startswith("."):
            return None
        folder = _member_photos(vault_kit.parent / member)
        return folder / name if folder is not None else None
    except (OSError, KeyError, TypeError, ValueError, AttributeError):
        return None


def with_files(vault_kit, rows):
    """The rows with `file` as where each photo is today (a member's export folder may have moved since the list
    was written). A row that can't be placed keeps the path the list holds."""
    out = []
    for x in rows:
        p = row_file(vault_kit, x)
        out.append(dict(x, file=str(p)) if p is not None else x)
    return out


def files(vault_kit):
    """The vault's photos that are there right now, in number order (for the few readers that want plain files:
    a tile, the facts)."""
    out = []
    for x in _rows(Path(vault_kit) / ".kit" / "sheet.json"):
        p = row_file(vault_kit, x)
        try:
            if p is not None and p.is_file():
                out.append(p)
        except OSError:
            pass
    return out


# ---------- the list ----------

def _key(member, src):
    return f"{member}#{src}"


def _own_key(name):
    return "own:" + _nfc(name)


def _state(vault_kit):
    d = _json(Path(vault_kit) / ".kit" / "vault.json")
    numbers = {k: n for k, n in (d.get("numbers") or {}).items() if isinstance(k, str) and type(n) is int and n >= 1} \
        if isinstance(d.get("numbers"), dict) else {}
    nxt = d.get("next") if type(d.get("next")) is int and d["next"] >= 1 else 1
    nxt = max([nxt] + [n + 1 for n in numbers.values()])        # a number once given is never given again
    out_ = d.get("out") if isinstance(d.get("out"), dict) else {}
    out_ = {w: dict(v) for w, v in out_.items() if w in WHATS and isinstance(v, dict)}
    return {"numbers": numbers, "next": nxt, "out": out_, "from": d.get("from")}


def _own_photos(vault_kit):
    """The finished photos in the vault's own Photos folder, by name. Links and hidden files are left out."""
    kit_mod = _kit()
    folder = Path(vault_kit) / "Photos"
    try:
        return [p for p in sorted(folder.iterdir(), key=lambda p: p.name.lower())
                if not p.name.startswith(".") and p.suffix.lower() in kit_mod.PHOTO and not p.is_symlink() and p.is_file()]
    except OSError:
        return []


def _signature(vault_kit):
    """What the list is made from, cheaply: each post kit's own list (its time and size) and the vault's own
    photos (name, time, size). When this is what the list was made from, nothing needs listing again."""
    c = Path(vault_kit).parent
    kits = {}
    for d in _kit_dirs(c):
        if d == Path(vault_kit):
            continue
        try:
            st = (d / ".kit" / "sheet.json").stat()
            kits[d.name] = [st.st_mtime_ns, st.st_size]
        except OSError:
            kits[d.name] = None
    own = []
    for p in _own_photos(vault_kit):
        try:
            st = p.stat()
            own.append([_nfc(p.name), st.st_mtime_ns, st.st_size])
        except OSError:
            pass
    return {"kits": kits, "own": own}


def changed(vault_kit):
    """Would a relist say something new? The post kits' lists and the vault's own Photos folder, compared with
    what the list was made from. Reads only. `settled` is False while a photo in the vault's own Photos folder
    was changed in the last two seconds (still being copied in): the caller waits."""
    import time
    sig = _signature(vault_kit)
    now = time.time_ns()
    settled = all(now - t >= 2_000_000_000 for _, t, _ in sig["own"])
    return {"changed": _state(vault_kit)["from"] != sig, "settled": settled}


def _way(w, h):
    return "tall" if h > w * 1.05 else "wide" if w > h * 1.05 else "square"


def relist(vault_kit, quick=False):
    """Bring the vault's list up to date, with every number where it was. Returns
        {"ok", "photos", "added": [n], "gone": [n], "back": [n], "same": bool, "waiting": [kits with no list yet],
         "sheets": [paths]}
    The list is written whole, the one before kept as sheet.prev.json; run again with nothing new, nothing is
    written. Not quick: the numbered contact sheets are drawn too, with the reel script's own make_sheets.
    Nothing is ever written into another post kit."""
    kit_mod = _kit()
    vault_kit = Path(vault_kit)
    hid = vault_kit / ".kit"
    if not is_vault(vault_kit):
        raise Trouble("That folder isn't the vault. Nothing was changed.")
    with kit_mod._held(hid / "vault.lock", 30.0) as got:
        if got is False:
            raise Trouble("The vault's list is being made right now. Try again in a moment.")
        sig = _signature(vault_kit)             # read BEFORE the lists, so a change made meanwhile is seen next time
        st = _state(vault_kit)
        numbers, nxt = dict(st["numbers"]), st["next"]
        out_photos = st["out"].get("photos") or {}
        sheet_file = hid / "sheet.json"
        prev = _json(sheet_file)
        had = sheet_file.is_file()
        prev_rows = {x["n"]: x for x in _rows(sheet_file)}
        prev_retired = {x["n"]: x for x in (prev.get("retired") or []) if isinstance(x, dict) and type(x.get("n")) is int} \
            if isinstance(prev.get("retired"), list) else {}
        prev_of = {}                            # a member's rows on the list before, to keep when its own list can't be read now
        for x in prev_rows.values():
            prev_of.setdefault(x.get("kit"), []).append(x)

        found, waiting = [], []                 # (key, row without its number), in the order new numbers are given
        mem = sorted(members(vault_kit), key=lambda m: (m["date"], m["folder"]))      # oldest first: numbers grow with time
        for m in mem:
            rows = _rows(m["path"] / ".kit" / "sheet.json")
            if not rows:
                if not m["listed"]:
                    waiting.append(m["folder"])
                # its own list can't be read right now (or is empty): what the vault had of it stays as it was
                for x in sorted(prev_of.get(m["folder"], []), key=lambda x: x["n"]):
                    found.append((_key(m["folder"], x.get("src")), {k: v for k, v in x.items() if k != "n"}))
                continue
            folder = _member_photos(m["path"])
            for x in sorted(rows, key=lambda x: x["n"]):
                name = Path(x["file"]).name
                if not name or name.startswith("."):
                    continue
                found.append((_key(m["folder"], x["n"]),
                              {"file": str(folder / name) if folder is not None else x["file"], "w": x.get("w") or 0,
                               "h": x.get("h") or 0, "way": x.get("way") or "", "kit": m["folder"], "src": x["n"]}))
        for p in _own_photos(vault_kit):
            k = _own_key(p.name)
            old = prev_rows.get(numbers.get(k)) if k in numbers else None
            if old and old.get("w") and old.get("h") and old.get("kit") == OWN and _nfc(Path(old["file"]).name) == _nfc(p.name):
                w, h = old["w"], old["h"]       # measured when it was first listed
            else:
                got_size = kit_mod.size_of(p)
                w, h = (got_size if got_size else (0, 0))
            found.append((k, {"file": str(p), "w": w, "h": h, "way": _way(w, h) if w and h else "", "kit": OWN, "src": None}))

        photos, here = [], set()
        for k, row in found:
            if k in here or k in out_photos:
                continue                        # taken out of the vault: its number stays unused until it is put back
            here.add(k)
            if k not in numbers:
                numbers[k] = nxt
                nxt += 1
            n = numbers[k]
            if row.get("kit") == OWN:
                row = dict(row, src=n)
            photos.append(dict({"n": n}, **row))
        photos.sort(key=lambda x: x["n"])
        now_ns = {x["n"] for x in photos}
        retired = []
        for k, n in sorted(numbers.items(), key=lambda kv: kv[1]):
            if n in now_ns:
                continue
            old = prev_rows.get(n) or prev_retired.get(n) or {}
            member, _, src = k.rpartition("#") if not k.startswith("own:") else (OWN, "", None)
            retired.append({"n": n, "file": Path(str(old.get("file") or (k[4:] if k.startswith("own:") else "?"))).name,
                            "kit": member, "src": int(src) if isinstance(src, str) and src.isdigit() else None})
        new_list = {MARK: True, "folder": str(vault_kit / "Photos"), "photos": photos, "retired": retired}
        added = sorted(now_ns - set(prev_rows) - set(prev_retired))
        gone = sorted(set(prev_rows) - now_ns)
        back = sorted(set(prev_retired) & now_ns)
        same = had and prev.get("photos") == photos and (prev.get("retired") or []) == retired and prev.get(MARK) is True
        res = {"ok": True, "photos": len(photos), "added": added, "gone": gone, "back": back, "same": bool(same),
               "waiting": waiting, "sheets": []}
        new_state = {"numbers": numbers, "next": nxt, "out": st["out"], "from": sig}
        if not same:
            if had:
                new_list.update(added=added, gone=gone, back=back)
            # the numbers first: one given here is never given to another photo, even if the list's write is cut off
            _write_whole(hid / "vault.json", dict(new_state, **{"from": st["from"]}))
            if had:
                try:
                    tmp = hid / f".sheet.prev.json.{os.getpid()}.tmp"
                    tmp.write_bytes(sheet_file.read_bytes())
                    this_computer.replace(tmp, hid / "sheet.prev.json")
                except OSError:
                    pass
            _write_whole(sheet_file, new_list)
        if _json(hid / "vault.json") != new_state:
            _write_whole(hid / "vault.json", new_state)
        if not same:
            count = len(photos)

            def note(r):
                r["numbered"] = count
            kit_mod.update_rec(vault_kit, note)     # the vault's own record, never another kit's
        if not quick and photos:
            try:
                res["sheets"] = [str(p) for p in _draw_sheets(vault_kit, photos)]
            except Exception as e:  # noqa: BLE001  (a sheet is a convenience; the numbered list still works)
                res["sheet_trouble"] = f"{e.__class__.__name__}: {str(e)[:160]}"
        return res


def _draw_sheets(vault_kit, photos):
    """The numbered contact sheets of the vault's photos, drawn by the reel script's own make_sheets into the
    vault's hidden folder. A photo that can't be reached right now is an empty square with its number."""
    kit_mod = _kit()
    d = str(kit_mod.REEL_PY.parent)
    saved = list(sys.path)
    if d not in sys.path:
        sys.path.append(d)
    try:
        import reel
    finally:
        sys.path[:] = saved + [x for x in sys.path if x not in saved]
    wd = Path(vault_kit) / ".kit" / "reels"
    wd.mkdir(exist_ok=True)
    rows = with_files(vault_kit, photos)
    return reel.make_sheets([Path(x["file"]) for x in rows], wd, labels=[x["n"] for x in rows])


def rows_by_group(vault_kit):
    """The vault's rows the way its pages fold them: the photos added to the vault itself first ("added"), then
    each post kit, newest first. [{"group": "added" | "kit", "kit", "name", "date", "rows"}]; a group with no
    rows is left out. Names and numbers only."""
    rows = _rows(Path(vault_kit) / ".kit" / "sheet.json")
    by = {}
    for x in rows:
        by.setdefault(x.get("kit") if isinstance(x.get("kit"), str) else OWN, []).append(x)
    out = []
    if by.get(OWN):
        out.append({"group": "added", "kit": OWN, "name": "", "date": "", "rows": by.pop(OWN)})
    by.pop(OWN, None)
    for m in members(vault_kit):
        if m["folder"] in by:
            out.append({"group": "kit", "kit": m["folder"], "name": m["name"], "date": m["date"], "rows": by.pop(m["folder"])})
    for folder in sorted(by):                  # a kit that can't be seen right now: its rows are still the vault's
        out.append({"group": "kit", "kit": folder, "name": folder, "date": "", "rows": by[folder]})
    return out


# ---------- taken out of the vault (stage 11 uses these) ----------

def out(vault_kit):
    """What was taken out of the vault: {"photos": {key: when}, "clips": {key: when}}. A photo's key is the one
    its number is kept under ("<kit folder>#<its number there>", or "own:<file name>")."""
    o = _state(vault_kit)["out"]
    return {w: dict(o.get(w) or {}) for w in WHATS}


def photo_out_key(row):
    """The key a row of the vault's list is taken out and put back by."""
    if row.get("kit") == OWN:
        return _own_key(Path(row["file"]).name)
    return _key(row.get("kit"), row.get("src"))


def set_out(vault_kit, what, key, on=True):
    """Take one thing out of the vault (on) or put it back. Only the vault's own vault.json is written; the
    photo, its post kit and its number are untouched, and the next relist leaves it off the list (or puts it
    back at its old number). True when something changed."""
    kit_mod = _kit()
    if what not in WHATS or not isinstance(key, str) or not 1 <= len(key) <= 600:
        raise Trouble("That isn't something the vault can take out. Nothing was changed.")
    hid = Path(vault_kit) / ".kit"
    with kit_mod._held(hid / "vault.lock", 30.0) as got:
        if got is False:
            raise Trouble("The vault's list is being made right now. Try again in a moment.")
        st = _state(vault_kit)
        had = key in (st["out"].get(what) or {})
        if bool(on) == had:
            return False
        if on:
            st["out"].setdefault(what, {})[key] = datetime.now().isoformat(timespec="seconds")
        else:
            st["out"][what].pop(key, None)
        st["from"] = None                       # so the next look lists again
        _write_whole(hid / "vault.json", st)
        return True


# ---------- the commands ----------

def _count_words(n, one, many):
    return f"{n:,} {one if n == 1 else many}"


def _say_relist(res):
    say(_count_words(res["photos"], "photo", "photos") + " in the vault.")
    if res["same"]:
        say("The same photos as the last list, with the same numbers. Nothing was written.")
    else:
        for key, words in (("added", "New since the last list"), ("gone", "Gone since the last list"), ("back", "Back since the last list")):
            ns = res[key]
            if ns:
                say(f"{words}: {_count_words(len(ns), 'photo', 'photos')} (number{'s' if len(ns) != 1 else ''} "
                    + (f"{ns[0]} to {ns[-1]}" if len(ns) > 3 and ns == list(range(ns[0], ns[-1] + 1)) else ", ".join(map(str, ns)))
                    + "). Every other photo keeps its number.")
    if res["waiting"]:
        say("Not in yet (no numbered list of their own; kit.py sheet makes one, and so does opening the post kit): "
            + ", ".join(res["waiting"]) + ".")
    for s in res["sheets"]:
        say(f"Sheet: {s}")
    if res.get("sheet_trouble"):
        say(f"(could not draw the sheet: {res['sheet_trouble']})")


def main():
    this_computer.utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    sub.add_parser("ensure")
    rl = sub.add_parser("relist")
    rl.add_argument("--sheets", action="store_true", help="also draw the numbered contact sheets")
    sub.add_parser("members")
    a = ap.parse_args()
    try:
        import fresh
        fresh.announce()
    except Exception:  # noqa: BLE001
        pass
    try:
        if a.cmd == "ensure":
            v, made = ensure()
            say(f"{'Made the vault' if made else 'The vault is already there'}: \"{v.name}\" in {posts.CONTENT_NAME}.")
            _say_relist(relist(v, quick=True))
            return 0
        v = find()
        if v is None:
            say("NO VAULT: there is no vault yet. `vault.py ensure` makes it (an empty folder and its list; no photo is copied).")
            return 3 if a.cmd != "members" else 0
        if a.cmd == "show":
            mem = members(v)
            rows = _rows(v / ".kit" / "sheet.json")
            own = sum(1 for x in rows if x.get("kit") == OWN)
            say(f"The vault: \"{v.name}\" in {posts.CONTENT_NAME}.")
            say(f"{_count_words(len(mem), 'shoot', 'shoots')} in it, {_count_words(len(rows), 'photo', 'photos')} on its list"
                + (f" ({own} added to the vault itself)" if own else "") + ".")
            ch = changed(v)
            if ch["changed"]:
                say("Its list is behind (photos were added or taken away since): `vault.py relist` brings it up to date.")
            return 0
        if a.cmd == "members":
            for m in members(v):
                say(f"{m['folder']} | {m['name']} | {m['date'] or 'no date'} | "
                    + (_count_words(m["photos"], "photo", "photos") if m["listed"] else "no numbered list yet"))
            return 0
        if a.cmd == "relist":
            _say_relist(relist(v, quick=not a.sheets))
            return 0
    except Trouble as e:
        say(f"STOP: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
