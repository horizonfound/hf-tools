#!/usr/bin/env python3
"""Eject my card (Dustin, Nov 11): the step behind the button that waits in the chat when a card is done and the
next one is due. Nothing is ever really ejected here: the Mac's own eject is swapped for a recorder.

    python3 tests/eject_check.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pc_smoke as t  # noqa: E402

SCRIPTS = t.SCRIPTS
FAILED = []


def check(what, ok, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {detail}"), flush=True)
    if not ok:
        FAILED.append(what)


def main():
    work = Path(tempfile.mkdtemp(prefix="eject-check-"))
    try:
        sys.path.insert(0, str(SCRIPTS))
        home = work / "home"
        home.mkdir()
        with t.environ(STUDIO_HOME=str(home)):
            import eject_card as ej
            asked = []
            real = (ej.is_card, ej.backed_up, ej.let_go, ej.cards.answers)

            def fake(card=True, safe=True, answers=True, result=(True, "Disk ejected")):
                ej.is_card = lambda p: card
                ej.backed_up = lambda p: safe
                ej.cards.answers = lambda p, *a, **k: answers
                ej.let_go = lambda p: asked.append(str(p)) or result
            try:
                card = work / "CARD"
                t.make_card(card, groups=(2,))
                code, said = real[0](card), None
                check("a folder that is not a drive of its own is not a card, even with a DCIM folder in it", code is False)
                check("a card with no backup on record is not known to be safe", real[1](card) is False)
                if not ej.this_computer.WINDOWS:
                    fake()
                    code, said = ej.eject(card)
                    check("a backed-up card is ejected, and the line says to put the next one in",
                          code == 0 and asked == [str(card)] and "put the next one in" in said, f"{code} {said}")
                    fake(card=False)
                    code, said = ej.eject(card)
                    check("anything that is not a memory card is refused, and nothing is ejected", code == 2 and len(asked) == 1 and "isn't a memory card" in said, said)
                    fake(safe=False)
                    code, said = ej.eject(card)
                    check("a card that is not backed up yet is refused in plain words", code == 2 and len(asked) == 1 and "isn't backed up yet" in said, said)
                    fake(answers=False)
                    code, said = ej.eject(card)
                    check("a card that has gone quiet gets plain words, and is not waited for", code == 1 and len(asked) == 1 and "isn't answering" in said, said)
                    fake(result=(False, "Volume failed to eject: in use"))
                    code, said = ej.eject(card)
                    check("when the computer will not let go of it, it says something is still using it", code == 1 and "still using the card" in said, said)
                    check("no line names a file path, a command or an error code", all("/" not in w and "diskutil" not in w for w in (ej.OUT, ej.NOT_A_CARD, ej.words(ej.NOT_SAFE), ej.words(ej.IN_USE), ej.words(ej.QUIET))))
            finally:
                ej.is_card, ej.backed_up, ej.let_go, ej.cards.answers = real
        text = (SCRIPTS.parent / "parts" / "backup.md").read_text(encoding="utf-8")
        check("the backup instructions carry the swap: the tap, Eject my card, then Card 2 is in",
              all(x in text for x in ("**Eject my card**", "eject_card.py", "**Card 2 is in**", "Ready to swap cards?")))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
