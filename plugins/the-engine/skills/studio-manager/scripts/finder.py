#!/usr/bin/env python3
"""Open a folder in Finder and bring Finder to the front.

A page's "Open photo folder" button asks a small
local server to open the folder. Plain `open` from that server does open it,
but the window lands behind the Claude app, so it looks as if nothing
happened. Here Finder is asked to come forward as well. Opens only; never
changes anything in the folder.
"""
import subprocess
import sys
import time

# Open the folder, bring its window out of the Dock if it was minimized, put it in front of Finder's other
# windows, and bring Finder in front of every app (asked two ways, since one can be refused when another app
# is full screen or has the keyboard).
_ACTIVATE = [
    "on run argv",
    "set f to POSIX file (item 1 of argv) as alias",
    'tell application "Finder"',
    "open f",
    "activate",
    "try",
    "set w to first Finder window whose target is f",
    "if collapsed of w then set collapsed of w to false",
    "set index of w to 1",
    "end try",
    "end tell",
    'tell application "System Events" to set frontmost of process "Finder" to true',
    "end run",
]


def finder_in_front():
    try:
        r = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
                           capture_output=True, text=True, timeout=10)
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
        cmd = ["osascript"]
        for line in _ACTIVATE:
            cmd += ["-e", line]
        try:
            r = subprocess.run(cmd + [path], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                for _ in range(2):  # it is open; is it in front? if not, ask once more
                    if finder_in_front():
                        return True, ""
                    time.sleep(0.4)
                    subprocess.run(["open", "-a", "Finder", path], capture_output=True, timeout=15)
                return True, "" if finder_in_front() else "behind"
        except (OSError, subprocess.TimeoutExpired):
            pass
        # Finder could not be asked (for example, permission to control it was declined): open it the plain way.
        try:
            r = subprocess.run(["open", path], capture_output=True, text=True, timeout=15)
            return r.returncode == 0, (r.stderr or "").strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, str(e)
    opener = {"win32": ["explorer"]}.get(sys.platform, ["xdg-open"])
    try:
        subprocess.run([*opener, path], check=False, timeout=15)
        return True, ""
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


if __name__ == "__main__":
    ok, why = open_folder(sys.argv[1])
    print(("opened, behind the app in front" if why == "behind" else "opened") if ok else f"could not open: {why}")
    sys.exit(0 if ok else 1)
