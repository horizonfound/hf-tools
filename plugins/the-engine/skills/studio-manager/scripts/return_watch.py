#!/usr/bin/env python3
"""Wait until the photographer has been away, then until they are back in the Claude app, then exit.

"You can walk away" means the report has to be on screen when they come back, and the Claude app's browser
pane can lose its page while they are gone (Dustin's first-run test, Nov 5: two hours away, a blank pane
with a play button). Claude cannot watch the app; it only runs when something wakes it. A background
command finishing does wake it, so this is that command: started when a backup's report has been shown, it
exits the moment they are back, and Claude then checks the pane and puts the report back.

Away means any of: the Claude app is not in front, the screen is locked, or the keyboard and mouse have
been still for --away seconds. Back means: the Claude app is in front, the screen is unlocked, and the
keyboard or mouse was used in the last few seconds. Reads only; needs no permission. Mac only for now
(lsappinfo, ioreg); on anything else it says so and exits 4 so nothing waits on it.

    python3 return_watch.py [--away 300] [--max-hours 12] [--log <file>]

Exit 0: they went away and came back (prints how long). Exit 3: gave up after --max-hours.
Exit 4: cannot tell on this computer.
"""
import argparse
import plistlib
import re
import subprocess
import sys
import time
from datetime import datetime

CLAUDE = "com.anthropic.claudefordesktop"


def say(msg, log=None):
    line = f"{datetime.now().strftime('%H:%M:%S')}  {msg}"
    try:
        print(line, flush=True)
    except BrokenPipeError:
        pass
    if log:
        try:
            with open(log, "a") as f:
                f.write(line + "\n")
        except OSError:
            pass


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def front_app():
    asn = run("lsappinfo", "front").strip()
    m = re.search(r'bundleID="([^"]*)"', run("lsappinfo", "info", "-only", "bundleid", asn)) if asn else None
    return m.group(1) if m else ""


def idle_seconds():
    m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', run("ioreg", "-c", "IOHIDSystem"))
    return int(m.group(1)) / 1e9 if m else None


def locked():
    try:
        out = subprocess.run(["ioreg", "-n", "Root", "-d1", "-a"], capture_output=True, timeout=10).stdout
        users = plistlib.loads(out).get("IOConsoleUsers") or [{}]
        return bool(users[0].get("CGSSessionScreenIsLocked", False))
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--away", type=float, default=300, help="seconds of being away before a return counts")
    ap.add_argument("--max-hours", type=float, default=12)
    ap.add_argument("--log")
    a = ap.parse_args()
    if sys.platform != "darwin" or idle_seconds() is None or not front_app():
        say("Cannot tell on this computer whether anyone is at it.", a.log)
        return 4
    say(f"Watching. A return counts after {a.away:.0f} s away.", a.log)
    started = time.time()
    away_since = None      # when the app left the front or the screen locked
    was_away = None        # when they first counted as away
    why = ""
    while time.time() - started < a.max_hours * 3600:
        front, idle, lock = front_app(), idle_seconds() or 0, locked()
        elsewhere = front != CLAUDE or lock
        if was_away is None:
            if elsewhere:
                if away_since is None:
                    say(f"Left the Claude app: {'screen locked' if lock else (front or 'unknown')} is in front.", a.log)
                away_since = away_since or time.time()
                if time.time() - away_since >= a.away:
                    was_away, why = away_since, ("screen locked" if lock else f"in another app ({front or 'unknown'})")
            else:
                if away_since is not None:
                    say(f"Claude in front again after {time.time() - away_since:.0f} s, not long enough to count.", a.log)
                away_since = None
                if idle >= a.away:
                    was_away, why = time.time() - idle, "keyboard and mouse still"
            if was_away is not None:
                say(f"Away: {why}.", a.log)
        elif front == CLAUDE and not lock and idle < 10:
            gone = time.time() - was_away
            say(f"BACK in the Claude app after {gone / 60:.1f} minutes away ({why}).", a.log)
            return 0
        time.sleep(2)
    say("Gave up waiting.", a.log)
    return 3


if __name__ == "__main__":
    sys.exit(main())
