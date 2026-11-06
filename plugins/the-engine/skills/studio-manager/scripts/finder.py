#!/usr/bin/env python3
"""Open a folder in Finder and bring Finder to the front (on a PC: File Explorer, which Windows brings forward or not).

A page's "Open photo folder" button asks a small
local server to open the folder. Plain `open` from that server does open it,
but the window lands behind the Claude app, so it looks as if nothing
happened. Here Finder is asked to come forward as well, and every folder gets a
window of its own (an open window showing it is reused, never a different one).
Opens only; never changes anything in the folder.
"""
import subprocess
import sys
import time
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()

# Open the folder in a window of its own, so a folder already open in another window stays as it was
# (Dustin, Oct 30: several Finder windows at once, never one replacing the last). If a window already shows
# this exact folder, that one is brought forward instead of a twin. Then bring it out of the Dock if it was
# minimized, put it in front of Finder's other windows, and bring Finder in front of every app (asked two
# ways, since one can be refused when another app is full screen or has the keyboard).
_ACTIVATE = [
    "on run argv",
    "set f to POSIX file (item 1 of argv) as alias",
    'tell application "Finder"',
    "set w to missing value",
    "try",
    "set w to first Finder window whose target is f",
    "end try",
    "if w is missing value then set w to make new Finder window to f",
    "activate",
    "try",
    "if collapsed of w then set collapsed of w to false",
    "set index of w to 1",
    "end try",
    "end tell",
    'tell application "System Events" to set frontmost of process "Finder" to true',
    "end run",
]


def finder_in_front():
    try:
        r = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],  # pc-ok: only asked from the Mac branch below
                           capture_output=True, encoding="utf-8", errors="replace", timeout=10)
        return r.stdout.strip() == "Finder"
    except (OSError, subprocess.TimeoutExpired):
        return True  # cannot tell; assume the best


def open_folder(path):
    """(ok, note) after showing the folder in Finder (Explorer, or the file manager elsewhere).
    ok with note "" means it is in front; ok with note "behind" means the folder is open but macOS kept
    the app being used in front (it does that while someone is typing or clicking in another app, and
    nothing can force past it); not ok means it could not be opened, and note says why."""
    path = str(path)
    if sys.platform == "darwin":
        cmd = ["osascript"]  # pc-ok: the Mac branch
        for line in _ACTIVATE:
            cmd += ["-e", line]
        try:
            r = subprocess.run(cmd + [path], capture_output=True, encoding="utf-8", errors="replace", timeout=15)
            if r.returncode == 0:
                for _ in range(2):  # it is open; is it in front? if not, ask once more
                    if finder_in_front():
                        return True, ""
                    time.sleep(0.4)
                    subprocess.run(["osascript", "-e", 'tell application "Finder" to activate'], capture_output=True, timeout=15)  # pc-ok: the Mac branch
                return True, "" if finder_in_front() else "behind"
        except (OSError, subprocess.TimeoutExpired):
            pass
        # Finder could not be asked (for example, permission to control it was declined): open it the plain way.
        try:
            r = subprocess.run(["open", path], capture_output=True, encoding="utf-8", errors="replace", timeout=15)  # pc-ok: the Mac branch
            return r.returncode == 0, (r.stderr or "").strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, str(e)
    if sys.platform == "win32":
        # unproven on a real PC.
        # File Explorer wants the path its own way (backslashes), and handed one it cannot read it opens
        # Documents instead without a word, so the folder is checked first. Windows decides whether the
        # window comes to the front; nothing here can tell, so it is never reported as "behind".
        import os
        path = os.path.normpath(path)
        if not os.path.isdir(path):
            return False, "that folder is not there"
        try:
            os.startfile(path)
            return True, ""
        except OSError as e:
            return False, str(e)
    try:
        subprocess.run(["xdg-open", path], check=False, timeout=15)
        return True, ""
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


if __name__ == "__main__":
    ok, why = open_folder(sys.argv[1])
    print(("opened, behind the app in front" if why == "behind" else "opened") if ok else f"could not open: {why}")
    sys.exit(0 if ok else 1)
