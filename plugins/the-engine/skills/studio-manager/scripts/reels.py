#!/usr/bin/env python3
"""Several reels from one shoot (Nicole's handoff v25, Nov 12: "I don't want to deselect everything and lose it.
I just want to start a new one.").

One record holds a list of reels. Her shape (server.py ver_op, ver_info), kept as it is:

    "versions": [{"id": "v1", "name": "Reel 1"}, {"id": "v2", "name": "Reel 2", "data": {...}}, ...]
    "current":  the id of the reel being worked on

The reel being worked on has its fields at the TOP of the record, exactly where they were before there were
several reels, so everything that reads the record still reads the open reel. Every other reel waits in its own
"data". Nothing is ever dropped: there is no way to remove a reel.

A record with no "versions" is one reel (its `first` name: "Reel 1", "Talking reel 1"), and stays byte for byte
what it was until a second reel is started or the first is renamed.

Used by the reel page's record (reel_page.py: .kit/reel-page.json) and the talking reel's (talking_rec.py:
.kit/talking.json). Each tells this file which of its keys belong to one reel (`live`: a function of the record)
and what a new reel starts with (`fresh`: a function of the record). This file reads and changes a record in
memory only; the caller holds the record's lock and saves it whole, the version before kept, as it always did.

Ours, where hers is silent:
  * a name is plain text of at most 40 letters on one line (her page's box stops at 40; her server cut it there),
    and two reels of one shoot never share a name (the chat tells reels apart by name);
  * a record changed by hand is read for what makes sense: an entry that is not {id, name} is left out of what
    the page is shown, and never thrown away from the file;
  * MOST reels a shoot (hers has no end; nothing can be removed, so there is one here).

Python 3.9, standard library only. Nothing here is Mac-only.
"""
import re
import unicodedata

ID = re.compile(r"v[1-9][0-9]{0,3}")
FIRST_ID = "v1"
NAME_MAX = 40            # hers: the box's maxlength, and her server's cut
MOST = 99                # ours: the most reels one shoot keeps (nothing is ever removed)

# Hers, word for word (server.py ver_op):
NO_NAME = "Give the reel a name."
GONE = "That reel isn't there anymore."
# Ours (hers has no such state), drafts for Nicole:
NAME_TAKEN = "Another reel of this shoot already has that name. Give this one a different name."
TOO_MANY = f"A shoot keeps up to {MOST} reels. Rename one you're done with and use it again."


class Wrong(Exception):
    """An ask that can't be done; str(e) is the line for the page (plain words, no path)."""


def clean_name(v):
    """A reel's name as it is kept: text on one line, no control characters, at most NAME_MAX letters. "" when
    there is nothing left (hers: "Give the reel a name.")."""
    if not isinstance(v, str):
        return ""
    v = unicodedata.normalize("NFC", v)
    v = "".join(" " if unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") else c for c in v)
    return re.sub(r"\s+", " ", v).strip()[:NAME_MAX].strip()


def _entries(rec):
    """The record's own list entries that make sense: dicts with an id of hers' shape and a name, none twice."""
    out, seen = [], set()
    got = rec.get("versions") if isinstance(rec, dict) else None
    for v in got if isinstance(got, list) else []:
        if not isinstance(v, dict) or not isinstance(v.get("id"), str) or not ID.fullmatch(v["id"]) or v["id"] in seen:
            continue
        if not clean_name(v.get("name")):
            continue
        seen.add(v["id"])
        out.append(v)
    return out


def several(rec):
    """Does this record keep a list of reels at all? (One that never did is one reel, untouched.)"""
    return bool(_entries(rec))


def listed(rec, first):
    """[{id, name}] for the page and the chat, in the order they were started."""
    got = _entries(rec)
    if not got:
        return [{"id": FIRST_ID, "name": first}]
    return [{"id": v["id"], "name": clean_name(v["name"])} for v in got]


def current(rec, first=""):
    """The id of the reel being worked on."""
    got = _entries(rec)
    if not got:
        return FIRST_ID
    cur = rec.get("current")
    return cur if isinstance(cur, str) and any(v["id"] == cur for v in got) else got[0]["id"]


def info(rec, first):
    """Hers (ver_info): what the page is told."""
    return {"versions": listed(rec, first), "current": current(rec, first)}


def name_of(rec, vid, first):
    return next((v["name"] for v in listed(rec, first) if v["id"] == vid), "")


def find(rec, words, first, what="reel"):
    """Which reel a few words from the chat mean: its id ("v2"), its whole name whatever the capitals, or a part
    of one name only. (id, None), or (None, why) with `why` plain words that list the reels."""
    vs = listed(rec, first)
    w = clean_name(words).casefold()
    names = ", ".join(f"\"{v['name']}\"" for v in vs)
    if not w:
        return None, f"which {what}? This shoot has: {names}."
    for v in vs:
        if v["id"] == w or v["name"].casefold() == w:
            return v["id"], None
    hits = [v for v in vs if w in v["name"].casefold()]
    if len(hits) == 1:
        return hits[0]["id"], None
    if hits:
        return None, f"\"{clean_name(words)}\" fits more than one {what}. This shoot has: {names}."
    return None, f"there's no {what} called \"{clean_name(words)}\" for this shoot. It has: {names}."


def _begin(rec, first):
    """The list written into the record, for the first change that needs one."""
    if not several(rec):
        keep = rec.get("versions") if isinstance(rec.get("versions"), list) else []
        rec["versions"] = [{"id": FIRST_ID, "name": first}] + [v for v in keep if v is not None]
        rec["current"] = FIRST_ID
    rec["current"] = current(rec, first)
    return {v["id"]: v for v in _entries(rec)}


def _stash(rec, by, live):
    """The open reel's own fields, moved from the top of the record into its entry."""
    cur = rec["current"]
    by[cur]["data"] = {k: rec.pop(k) for k in list(live(rec)) if k in rec}


def _bring(rec, by, to, live):
    """Another reel's fields, moved from its entry to the top of the record. Only its own keys (`live`) come up:
    a "data" changed by hand can never write over the record's shared fields."""
    data = by[to].pop("data", None)
    data = data if isinstance(data, dict) else {}
    allowed = set(live(data)) if callable(live) else set(data)
    for k, v in data.items():
        if k in allowed:
            rec[k] = v
    rec["current"] = to


def switch(rec, to, live, first):
    """Work on another reel. The one being worked on is kept exactly as it is. True when the record changed."""
    if not isinstance(to, str) or to not in {v["id"] for v in listed(rec, first)}:
        raise Wrong(GONE)
    if to == current(rec, first):
        return False
    by = _begin(rec, first)
    _stash(rec, by, live)
    _bring(rec, by, to, live)
    return True


def new(rec, live, fresh, first, word, name="", as_id=None):
    """Start a new reel: the one being worked on is kept exactly as it is, and a blank one opens. Returns its id.
    Its name is `name`, or hers: "<word> <how many reels there are now>", the next number that is free.
    `as_id` (bring_older.py only: a reel brought from the older pages keeps the id it had there, so a post
    already in the queue for "...-reel-v2" still means that reel): the id to give it, which must be free."""
    by = _begin(rec, first)
    vs = _entries(rec)
    if len(vs) >= MOST:
        raise Wrong(TOO_MANY)
    taken = {clean_name(v["name"]).casefold() for v in vs}
    name = clean_name(name)
    if name and name.casefold() in taken:
        raise Wrong(NAME_TAKEN)
    k = len(vs) + 1
    while not name and f"{word} {k}".casefold() in taken:
        k += 1
    nid = "v%d" % (1 + max(int(v["id"][1:]) for v in vs))
    if as_id is not None:
        if not isinstance(as_id, str) or not ID.fullmatch(as_id) or any(v["id"] == as_id for v in vs):
            raise Wrong(GONE)
        nid = as_id
    if not ID.fullmatch(nid):
        raise Wrong(TOO_MANY)
    start = fresh(rec)                      # read before the open reel is put away (it may look at every reel)
    _stash(rec, by, live)
    rec["versions"].append({"id": nid, "name": name or f"{word} {k}"})
    rec.update(start)
    rec["current"] = nid
    return nid


def rename(rec, vid, name, first):
    """Give a reel another name. True when the record changed."""
    name = clean_name(name)
    if not isinstance(vid, str) or vid not in {v["id"] for v in listed(rec, first)} or not name:
        raise Wrong(NO_NAME)
    if name == name_of(rec, vid, first):
        return False
    if any(v["id"] != vid and v["name"].casefold() == name.casefold() for v in listed(rec, first)):
        raise Wrong(NAME_TAKEN)
    by = _begin(rec, first)
    by[vid]["name"] = name
    return True


def op(rec, ask, live, fresh, first, word):
    """Hers (ver_op): {op: new | switch | rename, id, name} from the page, every field checked. Changes `rec` in
    memory. Returns True when it changed. Wrong(words) when it can't be done; nothing is changed then."""
    if not isinstance(ask, dict) or set(ask) - {"op", "id", "name"}:
        raise Wrong("")
    what = ask.get("op")
    if "name" in ask and not isinstance(ask["name"], str):
        raise Wrong("")
    if "id" in ask and not (isinstance(ask["id"], str) and ID.fullmatch(ask["id"])):
        raise Wrong("")
    if what == "new":
        if "id" in ask:
            raise Wrong("")
        new(rec, live, fresh, first, word, ask.get("name") or "")
        return True
    if what == "switch":
        if "name" in ask:
            raise Wrong("")
        return switch(rec, ask.get("id"), live, first)
    if what == "rename":
        return rename(rec, ask.get("id"), ask.get("name"), first)
    raise Wrong("")


def data_of(rec, vid, live, first):
    """One reel's own fields, whichever reel is open (hers: reel_version_data): a dict to READ. For the open reel
    it is the record's own top fields; for another, its "data"."""
    if vid == current(rec, first):
        return {k: rec[k] for k in live(rec) if k in rec}
    v = next((v for v in _entries(rec) if v["id"] == vid), None)
    d = v.get("data") if v else None
    return d if isinstance(d, dict) else {}


def each(rec, live, first):
    """(id, that reel's own fields as a dict that can be CHANGED in place) for every reel: the record itself for
    the open one, the entry's "data" for the others."""
    cur = current(rec, first)
    yield cur, rec
    for v in _entries(rec):
        if v["id"] != cur and isinstance(v.get("data"), dict):
            yield v["id"], v["data"]


class turned:
    """For a command that names a reel other than the one being worked on: inside the `with`, the record reads as
    if that reel were open (its fields at the top); afterwards the record is as it was, with whatever was changed
    kept in that reel. The reel being worked on is not changed, and neither is which one that is.

        with reels.turned(rec, "v2", LIVE, FIRST):
            rec["saved"] = ...
    """

    def __init__(self, rec, vid, live, first):
        self.rec, self.vid, self.live, self.first = rec, vid, live, first
        self.back = None

    def __enter__(self):
        cur = current(self.rec, self.first)
        if self.vid != cur:
            if self.vid not in {v["id"] for v in listed(self.rec, self.first)}:
                raise Wrong(GONE)
            self.back = cur
            switch(self.rec, self.vid, self.live, self.first)
        return self.rec

    def __exit__(self, *exc):
        if self.back is not None:
            switch(self.rec, self.back, self.live, self.first)
        return False
