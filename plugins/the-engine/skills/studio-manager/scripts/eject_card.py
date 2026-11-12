#!/usr/bin/env python3
"""Eject a memory card once its photos are safe (Dustin, Nov 11: with more than one card, "there should be like
an eject my card button so that they click that and then it ejects the card and then it's like, okay, now go ahead
and pop in your new one").

    python3 eject_card.py "<the card's path>"

Ejecting does not change the card: nothing on it is written, renamed or deleted (rule 1). It only tells the
computer to let go of it, so it is safe to pull out. Two things are checked first, and either one refuses:

  - it is a memory card (a drive of its own with a DCIM folder at the top), never the photo drive or a folder
  - this card's backup is finished: every file copied and checked (the card ledger knows it)

Every touch of the card has a time limit, so a card that has gone quiet gets plain words, not a silent wait.
Exit codes: 0 the card is out, 1 the computer would not let go of it, 2 refused (says why), 3 not on this computer yet.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cards  # noqa: E402
import this_computer  # noqa: E402
this_computer.utf8_output()

OUT = "Your card is out. Pull it from the reader, and put the next one in."
IN_USE = ("Something on this {computer} is still using the card (a {files} window, or a photo app looking at it). "
          "Close it and try again.")
QUIET = ("The card isn't answering, so I can't eject it. Nothing of mine is using it. "
         "Eject it yourself in {files}; if that won't work either, it is safe to pull it out once nothing is copying.")
NOT_A_CARD = "That isn't a memory card, so I won't eject it."
NOT_SAFE = ("This card isn't backed up yet, so I won't eject it on my own. Say \"backup now\" first, "
            "or eject it yourself in {files}.")
ON_A_PC = ("I can't eject a card on a PC yet. Click the small USB icon by the clock at the bottom right, "
           "then pick the card. When it says it is safe, pull it out and put the next one in.")


def words(text):
    return text.format(computer=this_computer.COMPUTER, files=this_computer.FILES_APP)


def is_card(path):
    """A drive of its own with a DCIM folder at the top (what a camera makes). Never a folder on another drive."""
    path = Path(path)
    try:
        return os.path.ismount(str(path)) and (path / "DCIM").is_dir()
    except OSError:
        return False


def backed_up(path):
    """True when the card ledger holds a finished backup of this very card (same files, same sizes): every file
    copied and checked, and no problems on record."""
    try:
        _, held = cards.check(path)
        if not held:
            return False
        m = json.loads((Path(held["studio"]) / "manifest.json").read_text(encoding="utf-8"))
        files = m.get("files", {})
        return bool(files) and not m.get("problems") and all(v.get("dest", {}).get("ok") for v in files.values())
    except (Exception, SystemExit):  # noqa: BLE001  (anything unreadable means "not known to be safe")
        return False


def let_go(path):
    """Ask the Mac to eject it. (ok, what it said)."""
    try:
        r = subprocess.run(["diskutil", "eject", str(path)], capture_output=True, encoding="utf-8", errors="replace", timeout=45)  # pc-ok: a Mac only (main returns before this on a PC)
        return r.returncode == 0, ((r.stdout or "") + (r.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        return False, "quiet"
    except OSError as e:
        return False, str(e)


def eject(path):
    """(exit code, the words to say)."""
    if this_computer.WINDOWS:
        return 3, words(ON_A_PC)   # unproven on a real PC
    if not cards.answers(path):
        return 1, words(QUIET)
    if not is_card(path):
        return 2, NOT_A_CARD
    if not backed_up(path):
        return 2, words(NOT_SAFE)
    ok, said = let_go(path)
    if ok:
        return 0, OUT
    return 1, words(QUIET if said == "quiet" else IN_USE)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('usage: eject_card.py "<the card\'s path>"')
    code, say = eject(sys.argv[1])
    print(say, flush=True)
    sys.exit(code)
