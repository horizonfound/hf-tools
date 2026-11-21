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
    python3 vault.py relist --sheets --only "12, 15, 20 to 24"
                                       sheets of those vault numbers only (a shortlist from `find`), 48 to a sheet
    python3 vault.py members           the post kits in it
    python3 vault.py add "<folder>"    + Add a shoot: copy that folder's finished photos into the vault's own Photos
                                       folder, each copy checked; the originals are only read. Twice copies nothing.
                                       Exit 0 done, 1 a copy stopped, did not match or a file could not be read,
                                       2 stop (also: another copy is running right now), 4 not a folder to add.
                                       A photo the vault already has from a shoot's post kit is not copied again.
    python3 vault.py find "<words>" [--photos | --clips]
                                       what matches in the vault, by the search rule below: photos by what is in
                                       them (photo_words.py) and their shoot's name, clips by their name and their
                                       shoot's name. Numbers and names only; reads only.

    python3 vault.py out [--photo N | --clip "<shoot's folder>:<id>"]
                                       Remove from my vault: take one photo (by its vault number) or one clip out.
                                       ONLY the vault's own vault.json is written (the version before kept); no
                                       photo, video or post kit is touched, and a photo's number stays its own.
                                       With nothing after it: what was taken out. Twice changes nothing.
    python3 vault.py back --photo N | --clip "<shoot's folder>:<id>"
                                       Put it back, with the number it had.

The search rule is hers and lives here, in one place (search_words, found): lower case, split on anything that is
not a letter or a number, everyday words dropped, and every word left must be in the item's text.
"""
import argparse
import hashlib
import json
import os
import re
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
EVERYTHING = True                   # "See everything in it" is drawn on the vault's page: its page is vault_page.py's /vault.html (stage 11)
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


CANT_READ_VAULT = ("I can't read your vault's own record right now, so nothing was made, copied or changed. "
                   "Try again in a moment. If it keeps happening, tell your assistant.")      # ours, a draft
CANT_READ_LIST = ("I can't read your vault's list of photo numbers right now, so nothing was changed. "
                  "Try again in a moment. If it keeps happening, tell your assistant.")       # ours, a draft


def _vault_unread(d):
    """A folder that is the vault by everything but its record: kit.json is there and can't be read (or isn't a
    record), and the vault's own vault.json or its marked list sits beside it. A plain post kit never has those."""
    d = Path(d)
    try:
        rec = json.loads((d / ".kit" / "kit.json").read_text(encoding="utf-8"))
        if isinstance(rec, dict):
            return False
    except FileNotFoundError:
        return False
    except (OSError, ValueError):
        pass
    try:
        if (d / ".kit" / "vault.json").is_file():
            return True
    except OSError:
        return True
    return _json(d / ".kit" / "sheet.json").get(MARK) is True


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
        for d in _kit_dirs(c):
            if _vault_unread(d):
                # the vault is there and its record can't be read this moment: never a second vault beside it
                raise Trouble(CANT_READ_VAULT)
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


def _state(vault_kit, d=None):
    """The vault's numbers and what was taken out, for a READER (a page, a count): a file that can't be read
    reads as empty. Anything that WRITES asks _state_to_write, which never takes "can't read" for "empty"."""
    if d is None:
        d = _json(Path(vault_kit) / ".kit" / "vault.json")
    numbers = {k: n for k, n in (d.get("numbers") or {}).items() if isinstance(k, str) and type(n) is int and n >= 1} \
        if isinstance(d.get("numbers"), dict) else {}
    nxt = d.get("next") if type(d.get("next")) is int and d["next"] >= 1 else 1
    nxt = max([nxt] + [n + 1 for n in numbers.values()])        # a number once given is never given again
    out_ = d.get("out") if isinstance(d.get("out"), dict) else {}
    out_ = {w: dict(v) for w, v in out_.items() if w in WHATS and isinstance(v, dict)}
    return {"numbers": numbers, "next": nxt, "out": out_, "from": d.get("from")}


def _keys_of_list(d):
    """{key: n} from a vault list (sheet.json): its rows and its retired rows both carry n, kit and src."""
    out = {}
    if not isinstance(d, dict):
        return out
    for part in ("photos", "retired"):
        for x in d.get(part) if isinstance(d.get(part), list) else []:
            if not isinstance(x, dict) or type(x.get("n")) is not int or x["n"] < 1 or not isinstance(x.get("kit"), str):
                continue
            if x["kit"] == OWN:
                name = Path(str(x.get("file") or "")).name
                if not name or name == "?":
                    continue
                k = _own_key(name)
            elif type(x.get("src")) is int:
                k = _key(x["kit"], x["src"])
            else:
                continue
            out.setdefault(k, x["n"])
    return out


def _state_to_write(vault_kit):
    """The vault's numbers for whoever is about to WRITE them (relist, Remove, Put it back), under the vault's
    lock: (state, recovered).

    vault.json there and readable: as it is. There and NOT readable this moment (a drive hiccup, a refusal, on a
    PC another program holding it): Trouble, and nothing is written; "can't read it" is never "it is empty", or
    every photo would get a new number and saved reels and designs would show other photos.
    Damaged, empty or gone: the numbers are put back from what is still on disk beside it (the list itself,
    sheet.json, whose rows and retired rows carry every number; then vault.prev.json and sheet.prev.json), what
    was taken out from vault.prev.json, and the damaged file is kept beside it under a dated name. Nothing is
    deleted. `recovered` is True then."""
    hid = Path(vault_kit) / ".kit"
    f = hid / "vault.json"
    raw = None
    try:
        raw = f.read_bytes()
    except FileNotFoundError:
        pass
    except OSError:
        raise Trouble(CANT_READ_LIST)
    if raw is not None:
        try:
            d = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            d = None
        if isinstance(d, dict) and isinstance(d.get("numbers"), dict):
            return _state(vault_kit, d), False
    lists = []
    for name in ("sheet.json", "sheet.prev.json"):
        try:
            lists.append(json.loads((hid / name).read_text(encoding="utf-8")))
        except FileNotFoundError:
            lists.append(None)
        except ValueError:
            lists.append(None)
        except OSError:
            if name == "sheet.json":
                raise Trouble(CANT_READ_LIST)       # the one place the numbers still are can't be read either: wait
            lists.append(None)
    before = _json(hid / "vault.prev.json")
    was = _state(vault_kit, before) if isinstance(before.get("numbers"), dict) else {"numbers": {}, "out": {}}
    numbers, used = {}, set()
    for src in (_keys_of_list(lists[0]), was["numbers"], _keys_of_list(lists[1])):
        for k, n in sorted(src.items(), key=lambda kv: kv[1]):
            if k not in numbers and n not in used:
                numbers[k] = n
                used.add(n)
    if raw is None and not numbers:
        return _state(vault_kit, {}), False         # a vault whose making was cut off before its numbers: a new one
    if raw is not None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{os.getpid()}"
        try:
            tmp = hid / f".vault.damaged-{stamp}.tmp"
            tmp.write_bytes(raw)
            for i in range(1, 100):                 # never over one already kept
                if this_computer.rename_new(tmp, hid / f"vault.damaged-{stamp}{'' if i == 1 else f'-{i}'}.json"):
                    break
            else:
                tmp.unlink()                        # our own scratch copy
        except OSError:
            pass
    st = _state(vault_kit, {"numbers": numbers, "out": was["out"], "from": None})
    return st, True


def _keep_prev(hid):
    """The vault.json before this write, kept beside it as vault.prev.json (only a file that reads as a record)."""
    try:
        was = (hid / "vault.json").read_bytes()
        if not isinstance(json.loads(was.decode("utf-8")), dict):
            return
        tmp = hid / f".vault.prev.json.{os.getpid()}.tmp"
        tmp.write_bytes(was)
        this_computer.replace(tmp, hid / "vault.prev.json")
    except (OSError, ValueError, UnicodeDecodeError):
        pass


def _follow_renames(vault_kit, mem, st, prev_rows):
    """A post kit whose folder was renamed in Finder keeps its photos' vault numbers and what was taken out.

    A kit's record keeps the folder name it was made under ("folder"); the vault never writes into a kit, so it
    follows the rename in its OWN record: when a kit's folder is no longer called that, no post kit is called
    that any more, exactly one kit says it was, and the vault holds numbers under the old name and none under
    the new, every key moves from the old name to the new (numbers, photos taken out, clips taken out, and the
    rows of the list before). Returns {old: new}; nothing is written here (relist writes vault.json after)."""
    names = {m["folder"] for m in mem}
    claims = {}
    for m in mem:
        old = _json(m["path"] / ".kit" / "kit.json").get("folder")
        if isinstance(old, str) and old and old != m["folder"] and old not in names and "/" not in old and "\\" not in old:
            claims.setdefault(old, []).append(m["folder"])
    moved = {}
    for old, news in claims.items():
        if len(news) != 1:
            continue                            # a copied kit folder: two say they were it, so neither is followed
        new = news[0]
        held = [k for k in st["numbers"] if not k.startswith("own:") and k.rpartition("#")[0] == old]
        if not held or any(not k.startswith("own:") and k.rpartition("#")[0] == new for k in st["numbers"]):
            continue
        moved[old] = new
    if not moved:
        return moved

    def photo_key(k):
        if k.startswith("own:"):
            return k
        member, _, src = k.rpartition("#")
        return _key(moved[member], src) if member in moved else k

    def clip_key(k):
        member, sep, cid = k.rpartition(":")
        return clip_out_key(moved[member], cid) if sep and member in moved else k

    st["numbers"] = {photo_key(k): n for k, n in st["numbers"].items()}
    if isinstance(st["out"].get("photos"), dict):
        st["out"]["photos"] = {photo_key(k): w for k, w in st["out"]["photos"].items()}
    if isinstance(st["out"].get("clips"), dict):
        st["out"]["clips"] = {clip_key(k): w for k, w in st["out"]["clips"].items()}
    for n, x in list(prev_rows.items()):
        if x.get("kit") in moved:
            prev_rows[n] = dict(x, kit=moved[x["kit"]])
    return moved


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
        st, recovered = _state_to_write(vault_kit)      # can't be read: Trouble, nothing written, no number moves
        sheet_file = hid / "sheet.json"
        prev = _json(sheet_file)
        had = sheet_file.is_file()
        prev_rows = {x["n"]: x for x in _rows(sheet_file)}
        mem = sorted(members(vault_kit), key=lambda m: (m["date"], m["folder"]))      # oldest first: numbers grow with time
        renamed = _follow_renames(vault_kit, mem, st, prev_rows)
        numbers, nxt = dict(st["numbers"]), st["next"]
        out_photos = st["out"].get("photos") or {}
        prev_retired = {x["n"]: x for x in (prev.get("retired") or []) if isinstance(x, dict) and type(x.get("n")) is int} \
            if isinstance(prev.get("retired"), list) else {}
        prev_of = {}                            # a member's rows on the list before, to keep when its own list can't be read now
        for x in prev_rows.values():
            prev_of.setdefault(x.get("kit"), []).append(x)

        found, waiting = [], []                 # (key, row without its number), in the order new numbers are given
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
               "waiting": waiting, "sheets": [], "recovered": recovered, "renamed": renamed}
        new_state = {"numbers": numbers, "next": nxt, "out": st["out"], "from": sig}
        kept = False
        if not same:
            if had:
                new_list.update(added=added, gone=gone, back=back)
            # the numbers first: one given here is never given to another photo, even if the list's write is cut off
            _keep_prev(hid)                     # the version before, kept beside it
            kept = True
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
            if not kept:
                _keep_prev(hid)
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


def _draw_sheets(vault_kit, photos, shortlist=False):
    """The numbered contact sheets of the vault's photos, drawn by the reel script's own make_sheets into the
    vault's hidden folder. A photo that can't be reached right now is an empty square with its number.
    `shortlist`: these rows only, into a folder of their own beside the whole vault's sheets (which stay as they
    are); 48 to a sheet, each photo under its own vault number."""
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
    if shortlist:
        wd = wd / "shortlist"
        wd.mkdir(exist_ok=True)
    rows = with_files(vault_kit, photos)
    return reel.make_sheets([Path(x["file"]) for x in rows], wd, labels=[x["n"] for x in rows])


ONLY_MOST = 480                     # a shortlist of more photos than this is not a shortlist: ten sheets at the most


def parse_numbers(text):
    """"12, 15, 20 to 24" or "12,15,20-24" as vault.py find prints them -> [12, 15, 20, 21, 22, 23, 24], in the
    order given, each once. Raises Trouble on anything else."""
    out = []
    for part in str(text or "").replace(" to ", "-").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        a, dash, b = part.partition("-")
        a, b = a.strip(), b.strip()
        if not a.isdigit() or (dash and not b.isdigit()):
            raise Trouble(f"\"{part}\" is not a photo's number. Give the numbers as vault.py find prints them: 12, 15, 20 to 24.")
        lo, hi = int(a), int(b) if dash else int(a)
        if hi < lo or hi - lo > 5000:
            raise Trouble(f"\"{part}\" is not a run of numbers.")
        for n in range(lo, hi + 1):
            if n not in out:
                out.append(n)
    if not out:
        raise Trouble("No numbers given. Give the photos' numbers as vault.py find prints them: 12, 15, 20 to 24.")
    return out


def shortlist_sheets(vault_kit, numbers):
    """Numbered contact sheets of these vault photos only (`vault.py relist --sheets --only`): the list is brought
    up to date first (quick), then the sheets are drawn, each photo under its own vault number, in number order.
    {"sheets": [paths], "drawn": [n], "unknown": [n not on the list]}. Nothing but the sheets is written."""
    res = relist(vault_kit, quick=True)
    by = {x["n"]: x for x in _rows(Path(vault_kit) / ".kit" / "sheet.json")}
    drawn = sorted(n for n in numbers if n in by)
    unknown = [n for n in numbers if n not in by]
    if len(drawn) > ONLY_MOST:
        raise Trouble(f"That is {len(drawn):,} photos, too many for a shortlist ({ONLY_MOST} at the most). Narrow the "
                      "search, or draw the whole vault's sheets with `vault.py relist --sheets`.")
    sheets = [str(p) for p in _draw_sheets(vault_kit, [by[n] for n in drawn], shortlist=True)] if drawn else []
    return {"sheets": sheets, "drawn": drawn, "unknown": unknown, "photos": res["photos"]}


def rows_by_group(vault_kit):
    """The vault's rows the way its pages fold them: the photos added to the vault itself first ("added"), then
    each post kit, newest first. [{"group": "added" | "kit", "kit", "name", "date", "rows"}]; a group with no
    rows is left out. Names and numbers only."""
    rows = _rows(Path(vault_kit) / ".kit" / "sheet.json")
    gone = (_state(vault_kit)["out"].get("photos") or {})          # taken out of the vault: left off at once (the
    by = {}                                                         # list itself follows on the next look)
    for x in rows:
        if gone and photo_out_key(x) in gone:
            continue
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


# ---------- + Add a shoot: a folder's finished photos, copied into the vault's own Photos folder ----------
#
# This is the one place the vault copies a photo, so it is built like posts.py bring (and the backup): only
# finished photos (posts.PHOTO; everything else is named and left where it is), each copied with
# posts.copy_checked (hashed while written to a partial file, given its name without ever replacing a file, read
# back and compared). The originals are only ever read. The plan is written to .kit/vault-adds.json BEFORE the
# first byte is copied (status "copying"; each file's name in its folder, size, time, hash and the name it gets),
# and after every few copies. A run cut off is finished by the next add; a second add of the same folder copies
# nothing. A name already in the vault's Photos: the same bytes means it is already there; different bytes means
# the copy gets a number after its name ("IMG_0001 (2).jpg"). Nothing is ever written over.

ADDS = "vault-adds.json"            # the log, in the vault's hidden folder
ADD_JOB = "vault-add-job.json"      # what the page follows while a copy runs (state, done, of, words)
ADD_NAMES_MOST = 500                # "IMG_0001 (500).jpg": past that, the file is a problem, not a copy
ADD_ASIDE = "copies-set-aside"      # in the vault's hidden folder: a copy that did not match its original, kept, never a photo
ADD_SAVE_EVERY = 10                 # the log is saved after this many copies (and at every stop)

# Ours, every one a draft for Dustin and Nicole. What the page shows is `words`; never a path.
ADD_WORDS = {
    "copied": "Copied {n} finished photo{s} into your vault. Your originals weren't moved.",
    "already_some": " {n} {were} already in your vault.",
    "already_all": "Those photos are already in your vault. Nothing was copied.",
    "left": " {n} file{s} left where {they}: not finished photos.",
    "none": "No finished photos (JPEGs) in that folder. Nothing was copied.",
    "from_kit": "That shoot is already in your vault, from its post kit.",
    "own": "That folder is your vault's own. Nothing was copied.",
    "inside": "That folder is part of your Assistant folder. Pick the folder your finished photos were exported to.",
    "no_folder": "I can't see that folder right now. Nothing was copied.",
    "busy": "Photos are being copied into your vault right now. Try again when that's done.",
    "held": "Something stopped the copy part way: {why}. {n} of {of} photos are in, each one checked. Nothing is lost and your originals weren't moved; add the same folder again to finish.",
    "mismatch": "{n} photo{s} did not match the original after copying, so {they} not in your vault. Your originals weren't moved. Tell your assistant.",
    "unread": "{n} file{s} in that folder could not be read, so {they} not in your vault. Nothing was changed there. Tell your assistant.",
    "working": "Copying {n} of {of}…",
    "starting": "Looking at the photos in that folder…",
    "stopped": "The copy stopped before it finished. Nothing is lost; add the same folder again to finish.",
}


def _s(n):
    return "" if n == 1 else "s"


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _adds(vault_kit):
    d = _json(Path(vault_kit) / ".kit" / ADDS)
    runs = d.get("adds") if isinstance(d.get("adds"), list) else []
    return {"adds": [r for r in runs if isinstance(r, dict) and isinstance(r.get("files"), list)]}


def _job_write(vault_kit, **facts):
    try:
        _write_whole(Path(vault_kit) / ".kit" / ADD_JOB, dict(facts, pid=os.getpid(), when=datetime.now().isoformat(timespec="seconds")))
    except OSError:
        pass                        # the page's progress line is a courtesy; the copy itself never waits on it


def _job_write_pid(vault_kit, pid):
    """The page server's own, right after it starts the job: the job's number, so a job that died before its
    first line is seen as stopped and never as working for ever."""
    f = Path(vault_kit) / ".kit" / ADD_JOB
    d = _json(f)
    if d.get("state") == "working" and d.get("of") in (0, None) and not d.get("done"):
        try:
            _write_whole(f, dict(d, pid=pid))
        except OSError:
            pass


def add_job(vault_kit):
    """What the page follows: {"state": "none" | "working" | "done" | "stopped", "words", "done", "of", "copied"}.
    A job whose process is gone while its record still says working is "stopped" (the next add finishes it)."""
    d = _json(Path(vault_kit) / ".kit" / ADD_JOB)
    state = d.get("state") if d.get("state") in ("working", "done", "stopped") else "none"
    if state == "working" and this_computer.still_running(d.get("pid")) is False:
        return {"state": "stopped", "words": ADD_WORDS["stopped"], "done": d.get("done") or 0, "of": d.get("of") or 0, "copied": 0}
    return {"state": state, "words": str(d.get("words") or ""), "done": d.get("done") or 0, "of": d.get("of") or 0,
            "copied": d.get("copied") or 0}


def _inside(child, parent):
    try:
        child, parent = Path(child).resolve(), Path(parent).resolve()
    except OSError:
        return False
    return child == parent or parent in child.parents


def add_refusal(vault_kit, folder):
    """Why this folder can't be added, as a key of ADD_WORDS, or None when it can. Checked before anything is
    read: a post kit's own photos (already in, by reference), the vault's own folders, anything else of the
    Assistant's."""
    vault_kit, src = Path(vault_kit), Path(folder)
    try:
        if not src.is_dir():
            return "no_folder"
    except OSError:
        return "no_folder"
    if _inside(src, vault_kit):
        return "own"
    c = vault_kit.parent
    for d in _kit_dirs(c):
        if d == vault_kit:
            continue
        photos = _member_photos(d)
        try:
            if _inside(src, d) or (photos is not None and src.resolve() == Path(photos).resolve()):
                return "from_kit"
        except OSError:
            continue
    try:
        h = posts.home()
    except (Exception, SystemExit):  # noqa: BLE001
        h = None
    if _inside(src, c) or _inside(c, src):
        return "inside"
    if h and _inside(src, h) and not _inside(src, Path(h) / posts.DROP_NAME):
        return "inside"
    return None


def _numbered_name(name, i):
    p = Path(name)
    return name if i == 1 else f"{p.stem} ({i}){p.suffix}"


def _taken(folder):
    """The names in a folder by its own listing, folded (most drives ignore capitals): {folded: exact name}."""
    try:
        return {_nfc(e).casefold(): e for e in os.listdir(folder)}
    except OSError:
        return {}


def _place_for(photos_dir, name, want, taken, seen):
    """The name a copy of these bytes gets in the vault's Photos folder: (name, "there") when a file by that
    name already holds the same bytes, (name, "new") for the first free name. `seen` keeps the hash of a file
    already there, so it is read once. None when 500 numbered names are all taken by other pictures."""
    for i in range(1, ADD_NAMES_MOST + 1):
        cand = _numbered_name(name, i)
        key = _nfc(cand).casefold()
        if key not in taken:
            return cand, "new"
        exact = taken[key]
        if exact.endswith(".studio-partial"):
            continue
        if exact not in seen:
            try:
                seen[exact] = _sha(photos_dir / exact)
            except OSError:
                seen[exact] = None
        if seen[exact] == want:
            return exact, "there"
    return None


def _add_words(res):
    w = ADD_WORDS
    if res.get("refused"):
        return w[res["refused"]]
    if res.get("held"):
        return w["held"].format(why=res["held"], n=res["copied"] + res["there"], of=res["photos"])
    left = sum(res["left"].values())
    tail = w["left"].format(n=left, s=_s(left), they="it is" if left == 1 else "they are") if left else ""
    if not res["photos"]:
        return w["none"] + tail
    unread = len(res.get("unread") or [])
    bad = len(res["problems"]) - unread
    out = ""
    if res["copied"]:
        out = w["copied"].format(n=res["copied"], s=_s(res["copied"]))
        if res["there"]:
            out += w["already_some"].format(n=res["there"], were="was" if res["there"] == 1 else "were")
    elif not bad and not unread:
        out = w["already_all"]
    if bad:
        out = (out + " " if out else "") + w["mismatch"].format(n=bad, s=_s(bad), they="it is" if bad == 1 else "they are")
    if unread:
        out = (out + " " if out else "") + w["unread"].format(n=unread, s=_s(unread), they="it is" if unread == 1 else "they are")
    return out + tail


def _shoot_index(vault_kit):
    """Every photo the vault already has from a shoot's post kit, by (file name, size): {(name, size): [(kit
    folder, where it is)]}. Names and sizes only (one stat each); a file is read only when a photo being added
    has the same name and size. A kit whose photos can't be reached right now is not in it."""
    idx = {}
    for m in members(vault_kit):
        folder = _member_photos(m["path"])
        if folder is None:
            continue
        for x in _rows(m["path"] / ".kit" / "sheet.json"):
            name = Path(x["file"]).name
            f = folder / name
            try:
                size = f.stat().st_size
            except OSError:
                continue
            idx.setdefault((_nfc(name).casefold(), size), []).append((m["folder"], f))
    return idx


def _in_a_shoot(idx, name, size, want, seen):
    """The folder name of a post kit that already holds this very photo (same name, same size, same bytes), or
    None. Such a photo is in the vault already, from its shoot, and is not copied a second time."""
    for member, f in idx.get((_nfc(name).casefold(), size), ()):
        key = str(f)
        if key not in seen:
            try:
                seen[key] = _sha(f)
            except OSError:
                seen[key] = None
        if seen[key] == want:
            return member
    return None


def add(vault_kit, folder, progress=None):
    """Copy a folder's finished photos into the vault's own Photos folder. Returns
        {"ok", "refused": key | None, "photos", "copied", "there", "left": {kind: n}, "problems": [names],
         "held": why | None, "words"}
    Safe to run twice (the second copies nothing), safe to cut off (the next run finishes it: what is in is
    compared, never replaced). The originals are only read."""
    kit_mod = _kit()
    vault_kit = Path(vault_kit)
    if not is_vault(vault_kit):
        raise Trouble("That folder isn't the vault. Nothing was changed.")
    res = {"ok": False, "refused": None, "photos": 0, "copied": 0, "there": 0, "left": {}, "problems": [], "held": None,
           "unread": []}
    try:
        src = Path(folder).expanduser()
        src = src.resolve() if src.is_dir() else src
    except OSError:
        src = Path(folder)
    why = add_refusal(vault_kit, src)
    if why:
        res["refused"] = why
        res["words"] = _add_words(res)
        return res
    hid = vault_kit / ".kit"
    photos_dir = vault_kit / "Photos"
    with kit_mod._held(hid / "vault-add.lock", 2.0) as got:
        if got is False:
            res["refused"] = "busy"
            res["words"] = _add_words(res)
            return res
        photos_dir.mkdir(exist_ok=True)
        log = _adds(vault_kit)
        where = str(src)
        earlier = {}                # a file of this folder a run already put in: rel -> its log line
        for r in log["adds"]:
            if this_computer.same_place(r.get("from", ""), where):
                for f in r["files"]:
                    if isinstance(f, dict) and f.get("done") and isinstance(f.get("src"), str):
                        earlier[f["src"]] = f
        run = next((r for r in log["adds"] if r.get("status") == "copying" and this_computer.same_place(r.get("from", ""), where)), None)
        files, left = [], {}
        for rel in posts.walk(src):
            k = posts.kind(rel)
            if k != "photo":
                label = {"raw": "RAW file", "video": "video", "working": posts.WORKING.get(Path(rel).suffix.lower(), "working file")}.get(k, "other file")
                left[label] = left.get(label, 0) + 1
                continue
            files.append(rel)
        res["photos"], res["left"] = len(files), left
        taken, seen, plan = _taken(photos_dir), {}, []
        shoots, shoot_seen = _shoot_index(vault_kit), {}
        if progress:
            progress(0, len(files), False)
        for rel in files:
            p = src / rel
            try:
                st = p.stat()
                want = None
                was = earlier.get(rel)
                if not (was and was.get("size") == st.st_size and was.get("mtime") == int(st.st_mtime)
                        and isinstance(was.get("dst"), str) and _nfc(was["dst"]).casefold() in taken):
                    want = _sha(p)
            except OSError:
                # one file that can't be read (a broken alias, a locked file, one that has gone) is named and left;
                # it never stops the photos beside it
                plan.append({"src": rel, "size": None, "mtime": None, "sha256": None, "dst": None, "done": False,
                             "state": "could not read"})
                continue
            line = {"src": rel, "size": st.st_size, "mtime": int(st.st_mtime), "sha256": None, "dst": None, "done": False}
            if (was and was.get("size") == st.st_size and was.get("mtime") == int(st.st_mtime) and isinstance(was.get("dst"), str)
                    and _nfc(was["dst"]).casefold() in taken):
                # the same file as last time (name, size, time), and the copy made then is still there: already in
                line.update(sha256=was.get("sha256"), dst=taken[_nfc(was["dst"]).casefold()], done=True, state="there")
                plan.append(line)
                continue
            line["sha256"] = want
            member = _in_a_shoot(shoots, Path(rel).name, st.st_size, want, shoot_seen)
            if member is not None:
                # the very same photo is in the vault already, from that shoot's post kit: never a second copy
                line.update(done=True, state="there", **{"in": member})
                plan.append(line)
                continue
            spot = _place_for(photos_dir, Path(rel).name, want, taken, seen)
            if spot is None:
                line["state"] = "no name free"
                plan.append(line)
                continue
            line["dst"], state = spot
            if state == "there":
                line.update(done=True, state="there")
            else:
                line["state"] = "to copy"
                taken[_nfc(line["dst"]).casefold()] = line["dst"]
                seen[line["dst"]] = want          # two files of this folder with the same name and bytes: one copy
            plan.append(line)
        todo = [f for f in plan if f.get("state") == "to copy"]
        if not todo and run is None:
            # nothing to copy: nothing is logged for a look that changed nothing (a second add of the same folder)
            res["there"] = sum(1 for f in plan if f.get("state") == "there")
            res["unread"] = [f["src"] for f in plan if f.get("state") == "could not read"]
            res["problems"] = [f["src"] for f in plan if f.get("state") in ("no name free", "could not read")]
            res["ok"] = not res["problems"]
            res["words"] = _add_words(res)
            return res
        if run is None:
            run = {"id": datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{os.getpid()}", "from": where,
                   "started": datetime.now().isoformat(timespec="seconds")}
            log["adds"].append(run)
        run.update({"status": "copying", "files": plan, "left": left})
        _write_whole(hid / ADDS, log)           # the log first: not a byte is copied before the plan is on disk
        stop_after = int(os.environ.get("STUDIO_VAULT_ADD_STOP_FOR_TESTS") or 0)     # only a test sets it: a run cut off
        made = 0
        for f in todo:
            dst = photos_dir / f["dst"]
            try:
                got_hash = posts.copy_checked(src / f["src"], dst, aside=hid / ADD_ASIDE)
                tries = 0
                while got_hash is None and dst.exists() and tries < 5:
                    # the name was taken meanwhile by another picture: the next free name, never over it
                    tries += 1
                    spot = _place_for(photos_dir, Path(f["src"]).name, f["sha256"], _taken(photos_dir), {})
                    if spot is None:
                        break
                    f["dst"] = spot[0]
                    dst = photos_dir / f["dst"]
                    got_hash = f["sha256"] if spot[1] == "there" else posts.copy_checked(src / f["src"], dst, aside=hid / ADD_ASIDE)
            except OSError as ex:
                res["held"] = posts.could_not(ex)
                _write_whole(hid / ADDS, log)
                break
            if got_hash is not None:
                if got_hash != f["sha256"]:
                    # the photo was saved over between the first look and its copy (an export still running): the
                    # copy was checked against the file as it is now, so it IS in the vault; the log says which bytes
                    f["sha256"] = got_hash
                    try:
                        now = (src / f["src"]).stat()
                        f.update(size=now.st_size, mtime=int(now.st_mtime))
                    except OSError:
                        pass
                f.update(done=True, state="copied")
                res["copied"] += 1
            else:
                f["state"] = "did not match"
            made += 1
            if made % ADD_SAVE_EVERY == 0:
                _write_whole(hid / ADDS, log)
            if progress:
                progress(made, len(todo), False)
            if stop_after and made >= stop_after:
                _write_whole(hid / ADDS, log)
                os._exit(9)                     # the test's cut: no tidy-up, as if the power went
        res["there"] = sum(1 for f in plan if f.get("state") == "there")
        res["unread"] = [f["src"] for f in plan if f.get("state") == "could not read"]
        res["problems"] = [f["src"] for f in plan if f.get("state") in ("did not match", "no name free", "could not read")]
        if res["held"] is None:
            run["status"] = "problems" if res["problems"] else "done"
            run["finished"] = datetime.now().isoformat(timespec="seconds")
        run["copied"] = sum(1 for f in plan if f.get("state") == "copied")
        _write_whole(hid / ADDS, log)
    res["ok"] = res["held"] is None and not res["problems"]
    res["words"] = _add_words(res)
    if res["copied"]:
        try:
            relist(vault_kit, quick=True)       # the new photos get their numbers (the list is the vault's own)
        except Trouble:
            pass                                # the next look at the vault lists them
    return res


def unfinished_adds(vault_kit):
    """The folders of adds that were cut off (status still "copying"), for the next add to finish first."""
    return [r["from"] for r in _adds(vault_kit)["adds"] if r.get("status") == "copying" and isinstance(r.get("from"), str)]


def add_and_finish(vault_kit, folder, progress=None):
    """What `vault.py add` and the page's job run: any add that was cut off is finished first (its folder is
    looked at again; what is in is compared, never replaced), then this one."""
    for old in unfinished_adds(vault_kit):
        if not this_computer.same_place(old, str(Path(folder).expanduser().resolve() if Path(folder).expanduser().is_dir() else folder)):
            try:
                if Path(old).is_dir():
                    add(vault_kit, old)
            except (OSError, Trouble):
                pass                            # it stays "copying" in the log, for the time its folder is back
    return add(vault_kit, folder, progress)


def clip_count(vault_kit):
    """How many videos the vault can draw from: the ones in its own Footage folder and in every post kit's.
    A plain count of video files by each folder's own listing (stage 9 lists them properly)."""
    n = 0
    vault_kit = Path(vault_kit)
    for d in [vault_kit] + [m["path"] for m in members(vault_kit)]:
        f = Path(d) / "Footage"
        try:
            if f.is_symlink() or not f.is_dir():
                continue
            for e in os.listdir(f):
                if not e.startswith(".") and e.lower().endswith((".mov", ".mp4", ".m4v")) and not (f / e).is_symlink() and (f / e).is_file():
                    n += 1
        except OSError:
            continue
    return n


# ---------- search (Nicole's v29, 1.4 and 1.5): the one rule, and what a page needs to search with ----------
#
# Hers, from her mock-up: lower case; split on anything that is not a letter or a number; everyday words are
# ignored (me, my, with, the, on...); every other word has to be found in the item's text ("laugh" finds
# "laughing"). A photo's text is what is in it (this computer's tags and your assistant's words, photo_words.py)
# plus its shoot's name, so "Hannah laughing" works. A clip's text is its name plus its shoot's name.
# Ours beside hers: accents are folded ("zoe" finds "Zoë"), and letters of any alphabet count as letters.

EVERYDAY = frozenset("me my on the a an of with at in and i to".split())
CLIP_EVERYDAY = EVERYDAY | frozenset("find every clip clips from any".split())     # "Find every clip of me at the beach"
SEARCH_WORDS = {"not_named": "Not named yet"}       # hers (the reel page's own words for a clip with no name)


def fold(text):
    """Text as search compares it: lower case, accents taken off, anything that is not a letter or a number a
    space."""
    t = unicodedata.normalize("NFKD", str(text or "")).casefold()
    return "".join(c if c.isalnum() else " " for c in t if not unicodedata.combining(c))


def search_words(query, clips=False):
    """The words of a search that must be found: her rule. An empty list finds everything."""
    drop = CLIP_EVERYDAY if clips else EVERYDAY
    out = []
    for w in fold(query).split():
        if w not in drop and w not in out:
            out.append(w)
    return out


def found(words, text):
    """Is every word in this item's text? (words: from search_words.)"""
    t = fold(text)
    return all(w in t for w in words)


def _clips_of(kit_dir):
    """Every clip in every reel of one post kit, each once, read from its reel record with the calls the footage
    look uses. Reads only; [] when there is no record."""
    import reel_page
    rec = reel_page.load(kit_dir)
    out, seen = [], set()
    first = reel_page.REEL_FIRST
    for _vid, data in reel_page.reels.each(rec, reel_page.REEL_LIVE, first):
        if not isinstance(data, dict):
            continue
        for m in reel_page.moments_of(data):
            if m["id"] in seen or isinstance(m.get("from"), dict):
                continue                        # (a clip a vault reel took from a shoot is that shoot's clip, listed there)
            seen.add(m["id"])
            label = " ".join(str(m.get("label") or "").split())
            named = bool(label) and not label.startswith(reel_page.PICK_AT)
            out.append({"id": m["id"], "label": label if named else SEARCH_WORDS["not_named"], "named": named,
                        "by": "you" if m.get("by") == "you" else "assistant",
                        "video": Path(str(m["video"]).replace("\\", "/")).name,
                        "start": round(float(m["start"]), 2), "end": round(float(m["end"]), 2)})
    return out


def catalog(kit, photos=True, clips=True, with_out=False):
    """What a page needs to search a post kit, built once, with no place on this computer in it (`photos` False:
    the clips and the shoots only, for the reel page's clips panel, which asks often):

        {"vault": bool,
         "shoots": [{"kit": folder name ("" for what was added to the vault itself), "group": "added" | "kit",
                     "name", "date", "photos": count, "clips": count, "thumb": a photo's number or None}],
         "photos": [{"n": its number on this kit's list, "kit": its shoot's folder, "text": tags + words + shoot name}],
         "clips":  [{"id", "kit", "label" ("Not named yet" when it has none), "named", "by", "video": the video's
                     file name, "start", "end", "text": its name + its shoot's name}]}

    For the vault: every shoot in it, what was added to the vault first. For any other post kit: that one shoot.
    A page fetches a picture by number (/kit-photo?kit=<this kit>&n=<thumb>) and filters in the page with the
    same rule. Reads only. `clips` False (the reel page's photos step): the photos and the shoots only, no reel
    record read. With photos, each shoot also says "tagged": how many of its photos have been looked at for
    search (so a page can say her "Getting your photos ready to search: 40 of 72." for that shoot).
    A photo also carries "words": your assistant's own description of it ("" when it has none). A clip taken out
    of the vault (Remove from my vault) is left out; `with_out` True lists it all the same, marked "out": True
    (the page's "Taken out of my vault" fold)."""
    import photo_words
    kit = Path(kit)
    rec = _json(kit / ".kit" / "kit.json")
    is_v = rec.get(MARK) is True
    want_clips = clips
    shoots, photo_list, clips = [], [], []
    groups = rows_by_group(kit) if is_v else [{"group": "kit", "kit": kit.name, "name": str(rec.get("name") or kit.name),
                                               "date": rec.get("date") if isinstance(rec.get("date"), str) else "",
                                               "rows": _rows(kit / ".kit" / "sheet.json")}]
    seen = {}
    for g in groups:
        own = g["group"] == "added" or not is_v
        home = kit if own else kit.parent / g["kit"]
        words = photo_words.read(home) if photos else {}
        name = g["name"]
        tagged = 0
        for x in g["rows"] if photos else ():
            num = str(x["n"] if own else x.get("src"))
            tagged += 1 if (words.get(num) or {}).get("tags_at") else 0
            text = " ".join(t for t in (photo_words.text_of(words.get(num)), name) if t)
            photo_list.append({"n": x["n"], "kit": g["kit"], "text": text, "words": str((words.get(num) or {}).get("words") or "")})
        seen[g["kit"]] = {"kit": g["kit"], "group": g["group"], "name": name, "date": g["date"], "photos": len(g["rows"]),
                          "clips": 0, "thumb": g["rows"][0]["n"] if g["rows"] else None}
        if photos:
            seen[g["kit"]]["tagged"] = tagged
    # the clips: the kit's own reels, and for the vault every shoot's reels too (a shoot with clips and no photos
    # on the list is still a shoot here)
    homes = [(OWN if is_v else kit.name, "added" if is_v else "kit", kit, "" if is_v else str(rec.get("name") or kit.name), "")]
    clips_out = (_state(kit)["out"].get("clips") or {}) if is_v else {}
    if is_v:
        homes += [(m["folder"], "kit", m["path"], m["name"], m["date"]) for m in members(kit)]
    for folder, group, path, name, day in homes if want_clips else ():
        try:
            got = _clips_of(path)
        except (Exception, SystemExit):  # noqa: BLE001  (a reel record that can't be read: that shoot has no clips to show)
            got = []
        gone = clips_out if is_v else {}
        kept = [c for c in got if clip_out_key(folder, c["id"]) not in gone]
        if not kept and not (with_out and got):
            continue
        if folder not in seen:
            seen[folder] = {"kit": folder, "group": group, "name": name, "date": day, "photos": 0, "clips": 0, "thumb": None}
        seen[folder]["clips"] = len(kept)
        for c in got if with_out else kept:
            one = dict(c, kit=folder, text=" ".join(t for t in (c["label"] if c["named"] else "", name) if t))
            if clip_out_key(folder, c["id"]) in gone:
                one["out"] = True
            clips.append(one)
    order = [g["kit"] for g in groups] + [h[0] for h in homes]
    for folder in order:
        if folder in seen and seen[folder] not in shoots:
            shoots.append(seen[folder])
    return {"vault": is_v, "shoots": shoots, "photos": photo_list, "clips": clips}


def find_in(kit, query, photos=True, clips=True):
    """What matches a search in this kit's catalog: {"words", "photos": [...], "clips": [...], "shoots": {folder:
    name}}. Each kind is searched with its own everyday words."""
    cat = catalog(kit)
    pw, cw = search_words(query), search_words(query, clips=True)
    return {"words": pw, "clip_words": cw,
            "photos": [p for p in cat["photos"] if found(pw, p["text"])] if photos else [],
            "clips": [c for c in cat["clips"] if found(cw, c["text"])] if clips else [],
            "shoots": {s["kit"]: s["name"] for s in cat["shoots"]}}


def _numbers(ns):
    ns, out, i = sorted(set(ns)), [], 0
    while i < len(ns):
        j = i
        while j + 1 < len(ns) and ns[j + 1] == ns[j] + 1:
            j += 1
        out.append(str(ns[i]) if j == i else f"{ns[i]} to {ns[j]}" if j > i + 1 else f"{ns[i]}, {ns[j]}")
        i = j + 1
    return ", ".join(out)


def _say_find(v, query, photos, clips):
    res = find_in(v, query, photos, clips)
    added = "Added to my vault"
    if photos:
        if not res["words"]:
            say("Photos: no word to search by (everyday words like \"me\" and \"the\" are ignored). Say what should be in the photo.")
        else:
            say(f"Photos matching \"{' '.join(res['words'])}\": {len(res['photos']):,} (the vault's own numbers).")
            by = {}
            for p in res["photos"]:
                by.setdefault(p["kit"], []).append(p["n"])
            for folder, ns in by.items():
                say(f"  {res['shoots'].get(folder) or folder or added}: {_numbers(ns)}")
            if not res["photos"]:
                say("  None. Photos are found by what this computer saw in them, by your assistant's descriptions "
                    "(photo_words.py status shows which shoots have none), and by the shoot's name.")
    if clips:
        if not res["clip_words"]:
            say("Clips: no word to search by. Say what should be happening in the clip.")
        else:
            say(f"Clips matching \"{' '.join(res['clip_words'])}\": {len(res['clips']):,}.")
            for c in res["clips"]:
                say(f"  {c['id']} | {res['shoots'].get(c['kit']) or c['kit'] or added} | {c['label']} | {c['video']} "
                    f"{c['start']:g} to {c['end']:g} s")
    return 0


# ---------- "Find my clips in my vault" (stage 9): every clip, for the assistant to choose from by its words ----------

def _mmss(t):
    t = max(0.0, float(t))
    return "%d:%02d" % (int(t // 60), int(round(t - int(t // 60) * 60)) % 60)


def _reel_for(v, words):
    """(the vault reel's id, its name, a line saying which reel when there are several) for --reel, or (None, why)."""
    import reel_page
    vid, why = reel_page.which_reel(v, words)
    if vid is None:
        return None, None, why
    vs, cur = reel_page.reel_names(v)
    name = next((x["name"] for x in vs if x["id"] == vid), reel_page.REEL_FIRST)
    line = ""
    if len(vs) > 1:
        line = (f"Your vault has {len(vs)} reels ({reel_page.reels_line(vs, cur)}). This is for \"{name}\""
                + (", the one open on the reel page." if vid == cur else ", not the one open on the reel page.")
                + " Name another with --reel \"<its name>\".")
    return vid, name, line


def _say_clips(v, reel_words):
    """vault.py clips: what they asked for, and every clip in the vault with the words to choose by."""
    import reel_page
    vid, name, line = _reel_for(v, reel_words)
    if vid is None:
        say("STOP: " + line + " Nothing was changed.")
        return 2
    if line:
        say(line)
    saved = reel_page.as_reel(reel_page.load(v), vid).get("saved")
    saved = saved if isinstance(saved, dict) else {}
    note = " ".join(str(saved.get("vault_ask") or "").split())
    say("What they'd like you to find (their words, from the box on the reel page): " + (f"\"{note}\"" if note else "nothing typed. Ask them what the reel is about before choosing."))
    kind = reel_page.reel_kind(saved)
    most = reel_page.STYLE_MAX.get(reel_page.style_of(saved) if kind != "broll" else reel_page.BROLL_STYLE, reel_page.MAX_CLIPS)
    say("This reel is " + (reel_page.KIND_NAMES.get(kind) or "not started yet (no kind chosen on the page)") + f"; it plays up to {most} clip{'s' if most != 1 else ''}.")
    cat = catalog(v, photos=False)
    names = {s["kit"]: s["name"] for s in cat["shoots"]}
    have = set()
    for m in reel_page.moments_of(reel_page.as_reel(reel_page.load(v), vid)):
        f = m.get("from")
        have.add((f.get("kit"), f.get("id")) if isinstance(f, dict) else (OWN, m["id"]))
    if not cat["clips"]:
        say("No clips in the vault yet. A clip is made on a reel page: in a shoot's post kit (the footage look, or their own "
            "with Start here and End here), or in the vault from a video they added with + Add clips.")
        return 0
    named = [c for c in cat["clips"] if c["named"]]
    unnamed = [c for c in cat["clips"] if not c["named"]]
    say(f"{len(cat['clips'])} clip{'s' if len(cat['clips']) != 1 else ''} in the vault. Choose by these words only; never watch a video to choose.")
    say("shoot's folder:id | shoot | what it is | length")
    for c in named:
        say(f"  {c['kit']}:{c['id']} | {names.get(c['kit']) or 'Added to my vault'} | {c['label']} | {_mmss(c['end'] - c['start'])}"
            + ("   (in this reel already)" if (c["kit"], c["id"]) in have else ""))
    if unnamed:
        say(f"Not named yet ({len(unnamed)}): these can only be told apart by their shoot. Offer to name them first.")
        by = {}
        for c in unnamed:
            by.setdefault(c["kit"], []).append(c)
        for folder, cs in by.items():
            who_ = names.get(folder) or "Added to my vault"
            say(f"  {who_}: " + ", ".join(f"{c['kit']}:{c['id']} ({_mmss(c['end'] - c['start'])})" for c in cs)
                + (f"   Offer: \"Name my clips for {who_}\"" if folder else "   Offer: \"Name my clips for My vault\""))
    say("To add your choices to this reel, in play order:")
    say(f"  python3 {Path(__file__).name} use-clips" + (f" --reel \"{name}\"" if line else "") + " --clips \"<shoot's folder>:<id>,<shoot's folder>:<id>\"")
    return 0


def _use_clips(v, reel_words, text):
    """vault.py use-clips: the same add as the page's + Add (reel_page.add_from), for the clips the assistant chose."""
    import reel_page
    vid, name, line = _reel_for(v, reel_words)
    if vid is None:
        say("STOP: " + line + " Nothing was changed.")
        return 2
    pairs = []
    for part in [p.strip() for p in str(text or "").split(",") if p.strip()]:
        folder, sep, cid = part.rpartition(":")
        if not sep or not cid.strip():
            say(f"STOP: \"{part}\" is not <shoot's folder>:<clip id> (as `vault.py clips` prints them). Nothing was changed.")
            return 2
        pairs.append((folder.strip(), cid.strip()))
    if not pairs:
        say("STOP: no clips named. --clips \"<shoot's folder>:<id>,...\" as `vault.py clips` prints them. Nothing was changed.")
        return 2
    if len(set(pairs)) != len(pairs):
        say("STOP: the same clip is named twice. Nothing was changed.")
        return 2
    code, res = reel_page.add_from(v, pairs, reel=vid)
    if code != 200 or not res.get("ok"):
        say("STOP: " + str(res.get("words") or "that could not be added.") + " Nothing was changed.")
        return 2
    n, had = len(res.get("added") or []), int(res.get("already") or 0)
    if line:
        say(line)
    say(f"Added {n} clip{'s' if n != 1 else ''} to {name!r}." if n else f"Nothing to add to {name!r}.")
    if had:
        say(f"{had} {'was' if had == 1 else 'were'} in that reel already and left as {'it is' if had == 1 else 'they are'}.")
    if n:
        say("They show under Your clips for this reel on the vault's reel page within a few seconds; the page is where "
            "they choose which ones play, and in what order.")
    return 0


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
        st, _recovered = _state_to_write(vault_kit)     # can't be read: Trouble, and nothing is written
        had = key in (st["out"].get(what) or {})
        if bool(on) == had:
            return False
        if on:
            st["out"].setdefault(what, {})[key] = datetime.now().isoformat(timespec="seconds")
        else:
            st["out"][what].pop(key, None)
        st["from"] = None                       # so the next look lists again
        _keep_prev(hid)                         # the version before, kept beside it
        _write_whole(hid / "vault.json", st)
        return True


CLIP_ID = re.compile(r"[mu][0-9]{1,4}-[0-9a-f]{6}")     # a clip's id, as the reel page gives them
OUT_WORDS = {                           # ours, drafts: what the page and the commands say (Nicole's has no way back)
    "photo_out": "Taken out of your vault. The photo itself is still in its shoot, and nothing was deleted.",
    "clip_out": "Taken out of your vault. The clip itself is still in its shoot, and nothing was deleted.",
    "own_photo_out": "Taken out of your vault. The photo itself is still in your vault's Photos folder, and nothing was deleted.",
    "own_clip_out": "Taken out of your vault. The clip is still in the reel it was made in, and nothing was deleted.",
    "back": "Back in your vault.",
    "already_out": "That was already taken out of your vault. Nothing changed.",
    "already_in": "That is already in your vault. Nothing changed.",
    "no_photo": "That photo isn't in your vault.",
    "no_clip": "That clip isn't in your vault.",
    "a_photo": "A photo",
    "added": "Added to my vault",       # hers, from the vault's reel page (reel_page.VAULT_CLIP_WORDS)
}


def clip_out_key(member, clip_id):
    """The key a clip is taken out and put back by: "<its shoot's folder>:<its id>" (":<id>" for a clip made in
    the vault itself). The same pair `vault.py clips` prints and `vault.py use-clips` takes."""
    return f"{member}:{clip_id}"


def _photo_key_of(vault_kit, n):
    """The key of the photo with this vault number (on the list or taken out), or None."""
    return next((k for k, num in _state(vault_kit)["numbers"].items() if num == n), None)


def in_or_out(vault_kit, what, ident, on):
    """Remove from my vault (on False) and Put it back (on True): the page's press and `vault.py out` / `back` are
    this one function. `what` "photo": ident is its vault number. `what` "clip": ident is "<shoot's folder>:<id>".
    ONLY the vault's own vault.json is written (set_out; the version before kept as vault.prev.json): no photo, no
    video, no shoot's post kit. A photo's number stays its own and is unused until it is put back. Twice changes
    nothing. Returns {"changed", "words", "own"}; raises Trouble (plain words) for something that is not in the
    vault."""
    cur = out(vault_kit)
    if what == "photo":
        if type(ident) is not int or not 1 <= ident <= 999999:
            raise Trouble(OUT_WORDS["no_photo"])
        key = _photo_key_of(vault_kit, ident)
        if key is None:
            raise Trouble(OUT_WORDS["no_photo"])
        kind, own = "photos", key.startswith("own:")
    elif what == "clip":
        member, sep, cid = ident.rpartition(":") if isinstance(ident, str) else ("", "", "")
        if not sep or not CLIP_ID.fullmatch(cid) or len(ident) > 400:
            raise Trouble(OUT_WORDS["no_clip"])
        key, kind, own = clip_out_key(member, cid), "clips", member == OWN
        if key not in cur["clips"]:                 # it must be a clip the vault lists today
            if not any(c["kit"] == member and c["id"] == cid for c in catalog(vault_kit, photos=False)["clips"]):
                raise Trouble(OUT_WORDS["no_clip"])
    else:
        raise Trouble("That isn't something the vault can take out. Nothing was changed.")
    is_out = key in cur[kind]
    if on:
        if not is_out:
            return {"changed": False, "words": OUT_WORDS["already_in"], "own": own}
        set_out(vault_kit, kind, key, on=False)
        return {"changed": True, "words": OUT_WORDS["back"], "own": own}
    if is_out:
        return {"changed": False, "words": OUT_WORDS["already_out"], "own": own}
    set_out(vault_kit, kind, key, on=True)
    return {"changed": True, "words": OUT_WORDS[("own_" if own else "") + what + "_out"], "own": own}


def out_list(vault_kit):
    """What was taken out of the vault, newest first, for the page's fold and `vault.py out`: [{"what": "photo" |
    "clip", "id": the photo's vault number or the clip's "<shoot's folder>:<id>", "kit", "shoot": its shoot's
    name ("" for what was added to the vault itself), "label": a clip's name or a photo's description ("" when it
    has none), "when"}]. Names and numbers only."""
    import photo_words
    vault_kit = Path(vault_kit)
    st = _state(vault_kit)
    names = {m["folder"]: m for m in members(vault_kit)}
    got = []
    words_of = {}
    for key, when in (st["out"].get("photos") or {}).items():
        n = st["numbers"].get(key)
        if n is None:
            continue
        if key.startswith("own:"):
            member, num = OWN, str(n)
        else:
            member, _, num = key.rpartition("#")
        home = vault_kit if member == OWN else (names.get(member) or {}).get("path")
        if home is not None and member not in words_of:
            words_of[member] = photo_words.read(home)
        label = str(((words_of.get(member) or {}).get(num) or {}).get("words") or "")
        got.append({"what": "photo", "id": n, "kit": member, "shoot": (names.get(member) or {}).get("name") or member, "label": label, "when": str(when)})
    outs = st["out"].get("clips") or {}
    if outs:
        for c in catalog(vault_kit, photos=False, with_out=True)["clips"]:
            if c.get("out"):
                got.append({"what": "clip", "id": clip_out_key(c["kit"], c["id"]), "kit": c["kit"],
                            "shoot": (names.get(c["kit"]) or {}).get("name") or c["kit"], "label": c["label"],
                            "when": str(outs.get(clip_out_key(c["kit"], c["id"])) or "")})
    got.sort(key=lambda x: x["when"], reverse=True)
    return got


def _say_out(v, a, on):
    if a.photo is None and a.clip is None:
        if on:
            say("STOP: say which one: --photo <its vault number> or --clip \"<shoot's folder>:<id>\" (`vault.py out` with nothing after it lists what was taken out).")
            return 2
        lst = out_list(v)
        say(f"Taken out of the vault: {len(lst):,}." + ("" if lst else " Nothing has been taken out."))
        for x in lst:
            where = x["shoot"] or OUT_WORDS["added"]
            if x["what"] == "photo":
                say(f"  photo {x['id']} | {where}" + (f" | {x['label']}" if x["label"] else "") + f" | put back: vault.py back --photo {x['id']}")
            else:
                say(f"  clip {x['id']} | {where} | {x['label']} | put back: vault.py back --clip \"{x['id']}\"")
        return 0
    res = in_or_out(v, "photo" if a.photo is not None else "clip", a.photo if a.photo is not None else a.clip, on)
    say(res["words"])
    if res["changed"]:
        say("Only the vault's own list of what was taken out was written. No photo, video or post kit was touched; "
            + ("its number in the vault is the one it had." if on else "`vault.py back` puts it back, with the number it had."))
    return 0


# ---------- the commands ----------

def _count_words(n, one, many):
    return f"{n:,} {one if n == 1 else many}"


def _say_relist(res):
    say(_count_words(res["photos"], "photo", "photos") + " in the vault.")
    if res.get("recovered"):
        say("The vault's own record of its numbers was damaged or missing, so the numbers were put back from its list. "
            "The damaged file is kept beside it, and no photo was touched. If something was taken out of the vault just "
            "before, check `vault.py out`: the last one may need taking out again.")
    for old, new in sorted((res.get("renamed") or {}).items()):
        say(f"The post kit \"{old}\" is now called \"{new}\": its photos keep their vault numbers.")
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
    rl.add_argument("--only", default=None, help="with --sheets: sheets of these vault numbers only (\"12, 15, 20 to 24\"), 48 to a sheet")
    sub.add_parser("members")
    ad = sub.add_parser("add", help="copy a folder's finished photos into the vault's own Photos folder")
    ad.add_argument("folder")
    ad.add_argument("--job", action="store_true", help=argparse.SUPPRESS)      # the page's own: progress in a file
    fi = sub.add_parser("find", help="what matches these words in the vault (photos and clips)")
    fi.add_argument("words")
    only = fi.add_mutually_exclusive_group()
    only.add_argument("--photos", action="store_true", help="photos only")
    only.add_argument("--clips", action="store_true", help="clips only")
    cl = sub.add_parser("clips", help="every clip in the vault, and what they asked for (Find my clips in my vault)")
    cl.add_argument("--reel", default=None, help="which of the vault's reels (default: the one open on the reel page)")
    uc = sub.add_parser("use-clips", help="add the clips you chose to a vault reel")
    uc.add_argument("--reel", default=None)
    uc.add_argument("--clips", required=True, help="\"<shoot's folder>:<id>,...\" as `vault.py clips` prints them")
    for name, hlp in (("out", "take one photo or clip out of the vault (nothing is deleted); with nothing after it, list what was taken out"),
                      ("back", "put a photo or clip that was taken out back in the vault")):
        ob = sub.add_parser(name, help=hlp)
        which = ob.add_mutually_exclusive_group()
        which.add_argument("--photo", type=int, default=None, help="the photo's vault number")
        which.add_argument("--clip", default=None, help="\"<shoot's folder>:<id>\" as `vault.py clips` prints it")
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
        if a.cmd == "add":
            v, made = ensure()
            if made:
                say(f"Made the vault: \"{v.name}\" in {posts.CONTENT_NAME}.")
            prog = None
            if a.job:
                _job_write(v, state="working", words=ADD_WORDS["starting"], done=0, of=0)

                def prog(done, of, _end):
                    _job_write(v, state="working", words=ADD_WORDS["working"].format(n=done, of=of) if of else ADD_WORDS["starting"], done=done, of=of)
            try:
                res = add_and_finish(v, a.folder, prog)
            except BaseException as e:  # noqa: BLE001
                if a.job:
                    _job_write(v, state="stopped", words=ADD_WORDS["stopped"])
                if isinstance(e, Trouble):
                    raise
                say(f"STOP: the copy stopped ({e.__class__.__name__}: {str(e)[:160]}). Nothing is lost and no original was "
                    "changed; running the same command again finishes it.")
                return 2
            if a.job:
                _job_write(v, state="done" if res["ok"] or res["refused"] else "stopped", words=res["words"], copied=res["copied"])
            say(("" if res["ok"] else "STOP: " if (res["held"] or res["problems"]) else "") + res["words"])
            for label, n in sorted(res["left"].items()):
                say(f"Left where it is, not copied: {n} {label}{'' if n == 1 else 's'}.")
            for name in res["problems"]:
                say(f"Not in the vault: {name}")
            if res["refused"] == "busy":
                return 2                        # another copy is running: a stop to try again, not "not a folder to add"
            if res["refused"]:
                return 4
            return 0 if res["ok"] else 1
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
        if a.cmd == "find":
            return _say_find(v, a.words, not a.clips, not a.photos)
        if a.cmd == "clips":
            return _say_clips(v, a.reel)
        if a.cmd == "use-clips":
            return _use_clips(v, a.reel, a.clips)
        if a.cmd in ("out", "back"):
            return _say_out(v, a, a.cmd == "back")
        if a.cmd == "members":
            for m in members(v):
                say(f"{m['folder']} | {m['name']} | {m['date'] or 'no date'} | "
                    + (_count_words(m["photos"], "photo", "photos") if m["listed"] else "no numbered list yet"))
            return 0
        if a.cmd == "relist":
            if a.only is not None:
                if not a.sheets:
                    say("STOP: --only goes with --sheets (sheets of a shortlist). Nothing was changed.")
                    return 2
                got = shortlist_sheets(v, parse_numbers(a.only))
                say(f"{_count_words(got['photos'], 'photo', 'photos')} in the vault; "
                    f"{_count_words(len(got['drawn']), 'photo', 'photos')} on this shortlist"
                    + (f", on {_count_words(len(got['sheets']), 'sheet', 'sheets')}" if got["sheets"] else "")
                    + ". Each photo is under its own vault number: pick by those numbers.")
                if got["unknown"]:
                    say("Not on the vault's list (left off the sheets): " + _numbers(got["unknown"]) + ".")
                for s in got["sheets"]:
                    say(f"Sheet: {s}")
                if not got["drawn"]:
                    say("STOP: none of those numbers is a photo in the vault. `vault.py find \"<words>\" --photos` prints the numbers.")
                    return 2
                return 0
            _say_relist(relist(v, quick=not a.sheets))
            return 0
    except Trouble as e:
        say(f"STOP: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
