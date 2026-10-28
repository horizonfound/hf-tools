#!/usr/bin/env python3
"""The note to the client that goes with the sneak peeks.

Claude writes the note (that is voice work, not script work). This script keeps
everything around it: what the photographer told the Studio about how they
write, the facts Claude writes from, the finished draft, and the "Copy" card on
the report. Nothing is ever sent; the photographer pastes it into their own email.

    python3 client_note.py setup --sample-file <a note they sent before> [--tone warm|plain|playful] [--sign-off "Nicole"]
    python3 client_note.py setup --tone warm --sign-off "xo, Nicole"      (no sample: a tone instead)
    python3 client_note.py setup --off                                     (no notes, don't ask again)
    python3 client_note.py status                                          on / off / never asked

    python3 client_note.py facts --night "<backup>" --shoot s1    what Claude has to write from (JSON)
    python3 client_note.py save --night "<backup>" --shoot s1 --to "Sarah" --subject "..." --body-file draft.txt
    python3 client_note.py save --night "<backup>" --shoot s1 --to "Sarah"      (just the name, before the draft)
    python3 client_note.py show --night "<backup>" [--shoot s1]

Settings live in the Studio File (~/.studio/studio.json, "note"): on, sample, tone,
sign_off. A night's notes live in its records, notes/<shoot id>.json: to, subject,
body, written. `save` rebuilds the report so the note card is on it at once.
Exit codes: 0 done, 1 a problem, 2 nothing there.
"""
import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import studio_file  # noqa: E402
from where import locate  # noqa: E402

TONES = {"warm": "warm and personal", "plain": "short and plain", "playful": "playful"}


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


# ---- the Studio File side -------------------------------------------------------------

def settings():
    return studio_file.load().get("note", {})


def setup(sample=None, tone=None, sign_off=None, off=False):
    sf = studio_file.load()
    n = sf.setdefault("note", {})
    if off:
        n["on"] = False
    else:
        n["on"] = True
        if sample is not None:
            n["sample"] = sample.strip()
        if tone:
            n["tone"] = tone
        if sign_off is not None:
            n["sign_off"] = sign_off.strip()
    sf["note"] = n
    studio_file.save(sf)
    return n


def status():
    n = settings()
    if not n:
        return "never asked"
    return "on" if n.get("on") else "off"


# ---- a night's notes ------------------------------------------------------------------

def notes_dir(studio):
    return studio / "notes"


def load_note(studio, shoot_id):
    p = notes_dir(studio) / f"{shoot_id}.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except ValueError:
            pass
    return {}


def save_note(studio, shoot_id, note):
    d = notes_dir(studio)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{shoot_id}.json"
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(note, indent=1, ensure_ascii=False))
    os.replace(tmp, p)
    return p


def all_notes(studio):
    """{shoot id: note} for every note written for this night."""
    out = {}
    d = notes_dir(studio)
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            try:
                out[p.stem] = json.loads(p.read_text())
            except ValueError:
                pass
    return out


def shoot_names(studio):
    """{shoot id: the name the photographer gave it, or the Studio's}, from the records."""
    names = {}
    if not (studio / "shoots.json").exists():
        return names
    given = json.loads((studio / "names.json").read_text()) if (studio / "names.json").exists() else {}
    for sh in json.loads((studio / "shoots.json").read_text())["shoots"]:
        names[sh["id"]] = given.get(sh["id"]) or sh.get("name") or sh.get("suggested") or sh["id"]
    return names


def nice_day(iso):
    try:
        d = date.fromisoformat(iso[:10])
    except (ValueError, TypeError):
        return iso or ""
    return f"{d.strftime('%A')}, {d.strftime('%B')} {d.day}"


def time_of_day(start, end):
    """'in the evening', 'in the morning', 'around midday', 'in the afternoon', from the capture times."""
    try:
        h0 = int(start[11:13])
        h1 = int(end[11:13]) if end else h0
    except (ValueError, TypeError):
        return ""
    mid = (h0 + h1) / 2
    if mid < 11:
        return "in the morning"
    if mid < 14:
        return "around midday"
    if mid < 17:
        return "in the afternoon"
    return "in the evening"


def due_for(studio, shoot_id):
    """The due date from the editing queue, if the shoot is in it."""
    try:
        q = json.loads((studio_file.HOME / "queue.json").read_text())
    except (OSError, ValueError):
        return None
    for s in q.get("shoots", []):
        if s.get("studio") == str(studio) and s.get("shoot") == shoot_id:
            return s.get("due")
    return None


def due_words(iso):
    if not iso:
        return ""
    try:
        n = (date.fromisoformat(iso) - date.today()).days
    except ValueError:
        return ""
    if n <= 3:
        return "in the next few days"
    if n <= 10:
        return "in about a week"
    if n <= 17:
        return "in about two weeks"
    if n <= 24:
        return "in about three weeks"
    return "in about a month"


def facts(night, shoot_id):
    root, studio = locate(night)
    shoots = json.loads((studio / "shoots.json").read_text())["shoots"]
    s = next((x for x in shoots if x["id"] == shoot_id), None)
    if not s:
        return None
    groups = {g["id"]: g for g in json.loads((studio / "groups.json").read_text())["groups"]} if (studio / "groups.json").exists() else {}
    gs = [groups[g] for g in s.get("groups", []) if g in groups]
    start = gs[0]["start"] if gs else ""
    end = gs[-1].get("end", "") if gs else ""
    peeks = []
    pj = studio / "sneak-peeks.json"
    if pj.exists():
        try:
            for pk in json.loads(pj.read_text()).get("picks", []):
                if pk.get("shoot", shoot_id) == shoot_id:
                    peeks.append({"file": Path(pk["file"]).name, "why": pk.get("why", ""),
                                  "preview": str(studio / "sneak-peeks" / (Path(pk["file"]).stem + ".jpg"))})
        except ValueError:
            pass
    due = due_for(studio, shoot_id)
    note = load_note(studio, shoot_id)
    return {
        "shoot": shoot_names(studio).get(shoot_id, shoot_id),
        "shoot_id": shoot_id,
        "day": nice_day(start),
        "time_of_day": time_of_day(start, end),
        "photos": s.get("photos"),
        "lenses": sorted({l for g in gs for l in g.get("lenses", [])}),
        "recap": s.get("recap", ""),
        "due": due,
        "due_words": due_words(due),
        "sneak_peeks": peeks,
        "to": note.get("to", ""),
        "existing_note": bool(note.get("body")),
        "how_they_write": settings(),
    }


def rebuild_report(night):
    try:
        import report_page
        report_page.write_page(night)
    except Exception as ex:  # the note is saved either way; the report is a convenience
        say(f"(The report could not be rebuilt: {ex})")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("setup")
    st.add_argument("--sample-file")
    st.add_argument("--sample")
    st.add_argument("--tone", choices=sorted(TONES))
    st.add_argument("--sign-off")
    st.add_argument("--off", action="store_true")
    sub.add_parser("status")
    f = sub.add_parser("facts"); f.add_argument("--night", required=True); f.add_argument("--shoot", required=True)
    sv = sub.add_parser("save"); sv.add_argument("--night", required=True); sv.add_argument("--shoot", required=True)
    sv.add_argument("--to"); sv.add_argument("--subject"); sv.add_argument("--body"); sv.add_argument("--body-file")
    sh = sub.add_parser("show"); sh.add_argument("--night", required=True); sh.add_argument("--shoot")
    a = ap.parse_args()

    if a.cmd == "setup":
        sample = None
        if a.sample_file:
            sample = Path(a.sample_file).read_text()
        elif a.sample:
            sample = a.sample
        n = setup(sample, a.tone, a.sign_off, a.off)
        if not n.get("on"):
            say("Client notes: off. The Studio won't ask again.")
        else:
            say("Client notes: on. "
                + ("Matching the note you pasted" if n.get("sample") else f"Tone: {TONES.get(n.get('tone', 'warm'), 'warm and personal')}")
                + (f". Signed: {n['sign_off']}" if n.get("sign_off") else ". Sign-off not set yet") + ".")
        return 0
    if a.cmd == "status":
        say(status())
        return 0
    if a.cmd == "facts":
        d = facts(a.night, a.shoot)
        if d is None:
            say(f"STOP: no shoot {a.shoot} in that night's records.")
            return 1
        say(json.dumps(d, indent=1, ensure_ascii=False))
        return 0
    if a.cmd == "save":
        root, studio = locate(a.night)
        if a.shoot not in shoot_names(studio):
            say(f"STOP: no shoot {a.shoot} in that night's records.")
            return 1
        note = load_note(studio, a.shoot)
        if a.to is not None:
            note["to"] = a.to.strip()
        if a.subject is not None:
            note["subject"] = a.subject.strip()
        body = Path(a.body_file).read_text() if a.body_file else a.body
        if body is not None:
            note["body"] = body.strip() + "\n"
            note["written"] = datetime.now().isoformat(timespec="seconds")
        if not note:
            say("Nothing to save.")
            return 2
        p = save_note(studio, a.shoot, note)
        rebuild_report(a.night)
        what = "draft" if body is not None else "name"
        say(f"Saved the {what} for {shoot_names(studio)[a.shoot]}" + (f" (to {note['to']})" if note.get("to") else "") + ". It's on the report with a Copy button.")
        return 0
    if a.cmd == "show":
        root, studio = locate(a.night)
        names = shoot_names(studio)
        notes = all_notes(studio)
        if a.shoot:
            notes = {k: v for k, v in notes.items() if k == a.shoot}
        if not notes:
            say("No notes written for this backup yet.")
            return 2
        for sid, n in notes.items():
            say(f"--- {names.get(sid, sid)}" + (f", to {n['to']}" if n.get("to") else ""))
            if n.get("subject"):
                say(f"Subject: {n['subject']}")
            say(n.get("body", "(no draft yet)"))
        return 0


if __name__ == "__main__":
    sys.exit(main())
