#!/usr/bin/env python3
"""Open a folder in Finder and bring Finder to the front.

A page's "Open photo folder" or "Take me to the photos" button asks a small
local server to open the folder. Plain `open` from that server does open it,
but the window lands behind the Claude app, so it looks as if nothing
happened. Here Finder is asked to come forward as well. Opens only; never
changes anything in the folder.
"""
import subprocess
import sys

_ACTIVATE = [
    "on run argv",
    'tell application "Finder"',
    "open (POSIX file (item 1 of argv) as alias)",
    "activate",
    "end tell",
    "end run",
]


def open_folder(path):
    """(ok, why) after showing the folder in Finder (Explorer, or the file manager elsewhere), in front."""
    path = str(path)
    if sys.platform == "darwin":
        cmd = ["osascript"]
        for line in _ACTIVATE:
            cmd += ["-e", line]
        try:
            r = subprocess.run(cmd + [path], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return True, ""
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
    print("opened" if ok else f"could not open: {why}")
    sys.exit(0 if ok else 1)
