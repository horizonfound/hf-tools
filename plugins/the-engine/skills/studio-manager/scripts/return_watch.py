#!/usr/bin/env python3
"""Wait until the photographer has been away, then until they are back in the Claude app, then exit.

"You can walk away" means the report has to be on screen when they come back, and the Claude app's browser
pane can lose its page while they are gone (Dustin's first-run test, Nov 5: two hours away, a blank pane
with a play button). Claude cannot watch the app; it only runs when something wakes it. A background
command finishing does wake it, so this is that command: started when a backup's report has been shown, it
exits the moment they are back, and Claude then checks the pane and puts the report back.

Away means any of: the Claude app is not in front, the screen is locked, or the keyboard and mouse have
been still for --away seconds. Back means: the Claude app is in front, the screen is unlocked, and the
keyboard or mouse was used in the last few seconds. Reads only; needs no permission.

On a Mac: lsappinfo and ioreg, as tried on Dustin's Mac. On a PC: Windows' own answers (how long since the
keyboard or mouse was used, which program owns the window in front), written from Microsoft's documentation
and unproven on a real PC. Anywhere else, or if those cannot be asked, it says so and exits 4 so nothing
waits on it.

    python3 return_watch.py [--away 300] [--max-hours 12] [--log <file>]

Exit 0: they went away and came back (prints how long). Exit 3: gave up after --max-hours.
Exit 4: cannot tell on this computer.
"""
import argparse
import errno
import os
import plistlib
import re
import subprocess
import sys
import time
from datetime import datetime
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()

CLAUDE = "com.anthropic.claudefordesktop"


def say(msg, log=None):
    line = f"{datetime.now().strftime('%H:%M:%S')}  {msg}"
    try:
        print(line, flush=True)
    except BrokenPipeError:
        pass
    except OSError as e:
        # A PC only (as kit.py's say): Windows reports a reader that has gone away as "invalid argument" (EINVAL),
        # not as a broken pipe, and the work goes on, as it does on a Mac. A Mac raises anything else, as before.
        if not (this_computer.WINDOWS and e.errno == errno.EINVAL):   # unproven on a real PC
            raise
    if log:
        try:
            with open(log, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


# ---------------------------------------------------------------- a PC (unproven on a real PC)

_win = None


def _windows():
    """Windows' own functions, set up once with their exact argument and return types (64-bit handles as
    pointers, never as plain numbers). None if they cannot be had."""
    global _win
    if _win is not None:
        return _win or None
    try:
        import ctypes
        from ctypes import wintypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
        user32.GetLastInputInfo.restype = wintypes.BOOL
        user32.GetForegroundWindow.argtypes = []
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        kernel32.GetTickCount.argtypes = []
        kernel32.GetTickCount.restype = wintypes.DWORD
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                        ctypes.POINTER(wintypes.DWORD)]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        _win = {"ctypes": ctypes, "wintypes": wintypes, "LASTINPUTINFO": LASTINPUTINFO, "user32": user32, "kernel32": kernel32}
    except Exception:  # noqa: BLE001  (not Windows, or a Windows without these)
        _win = False
        return None
    return _win


def _win_idle():
    """Seconds since the keyboard or mouse was last used (GetLastInputInfo), or None."""
    w = _windows()
    if not w:
        return None
    try:
        info = w["LASTINPUTINFO"]()
        info.cbSize = w["ctypes"].sizeof(info)
        if not w["user32"].GetLastInputInfo(w["ctypes"].byref(info)):
            return None
        # Both counts are milliseconds since Windows started, kept in 32 bits, so they wrap after 49.7 days:
        # the difference is taken the same way.
        return ((w["kernel32"].GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception:  # noqa: BLE001
        return None


def _win_front():
    """The file name of the program whose window is in front ("claude.exe"), "" when no window is in front
    (as when the screen is locked), or None when Windows cannot be asked."""
    w = _windows()
    if not w:
        return None
    ctypes, wintypes, user32, kernel32 = w["ctypes"], w["wintypes"], w["user32"], w["kernel32"]
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000      # enough to read a program's name, nothing more
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not h:
            return ""                                    # a program we may not look at (an administrator's)
        try:
            size = wintypes.DWORD(32768)
            buf = ctypes.create_unicode_buffer(size.value)
            if not kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return ""
            return os.path.basename(buf.value).lower()
        finally:
            kernel32.CloseHandle(h)
    except Exception:  # noqa: BLE001
        return None


def _win_is_claude(name):
    # The Claude app's program name on Windows has not been seen here (Nov 6, 2026); it is believed to be
    # "Claude.exe". Matched as any program name with "claude" in it, ignoring capital letters, and nothing
    # more specific until a real PC shows the name.
    return bool(name) and "claude" in name.lower()


def _win_locked(name):
    # Windows has no single "is the screen locked" answer a script can just ask. While it is locked, the
    # window in front belongs to the lock screen (LockApp.exe, LogonUI.exe) or there is none at all.
    return name == "" or name in ("lockapp.exe", "logonui.exe")


# ---------------------------------------------------------------- a Mac

def _mac_front():
    asn = run("lsappinfo", "front").strip()  # pc-ok: the Mac branch (front_app asks only on a Mac)
    m = re.search(r'bundleID="([^"]*)"', run("lsappinfo", "info", "-only", "bundleid", asn)) if asn else None  # pc-ok: the Mac branch
    return m.group(1) if m else ""


def _mac_idle():
    m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', run("ioreg", "-c", "IOHIDSystem"))  # pc-ok: the Mac branch
    return int(m.group(1)) / 1e9 if m else None


def _mac_locked():
    try:
        out = subprocess.run(["ioreg", "-n", "Root", "-d1", "-a"], capture_output=True, timeout=10).stdout  # pc-ok: the Mac branch
        users = plistlib.loads(out).get("IOConsoleUsers") or [{}]
        return bool(users[0].get("CGSSessionScreenIsLocked", False))
    except Exception:
        return False


# ---------------------------------------------------------------- either

def front_app():
    """What is in front: the Mac's bundle id ("com.anthropic.claudefordesktop"), or on a PC the program's
    file name ("claude.exe"); "" when nothing can be said."""
    if this_computer.WINDOWS:
        return _win_front() or ""
    if sys.platform == "darwin":
        return _mac_front()
    return ""


def idle_seconds():
    if this_computer.WINDOWS:
        return _win_idle()
    if sys.platform == "darwin":
        return _mac_idle()
    return None


def locked():
    if this_computer.WINDOWS:
        return _win_locked(_win_front())
    if sys.platform == "darwin":
        return _mac_locked()
    return False


def is_claude(front):
    if this_computer.WINDOWS:
        return _win_is_claude(front)
    return front == CLAUDE


def can_tell():
    """True when this computer can say who is at it: a Mac that answers lsappinfo and ioreg, or a PC whose own
    functions answer."""
    if this_computer.WINDOWS:
        return _win_idle() is not None and _win_front() is not None
    return sys.platform == "darwin" and idle_seconds() is not None and bool(front_app())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--away", type=float, default=300, help="seconds of being away before a return counts")
    ap.add_argument("--max-hours", type=float, default=12)
    ap.add_argument("--log")
    a = ap.parse_args()
    if not can_tell():
        say("Cannot tell on this computer whether anyone is at it.", a.log)
        return 4
    say(f"Watching. A return counts after {a.away:.0f} s away.", a.log)
    started = time.time()
    away_since = None      # when the app left the front or the screen locked
    was_away = None        # when they first counted as away
    why = ""
    while time.time() - started < a.max_hours * 3600:
        front, idle, lock = front_app(), idle_seconds() or 0, locked()
        elsewhere = not is_claude(front) or lock
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
        elif is_claude(front) and not lock and idle < 10:
            gone = time.time() - was_away
            say(f"BACK in the Claude app after {gone / 60:.1f} minutes away ({why}).", a.log)
            return 0
        time.sleep(2)
    say("Gave up waiting.", a.log)
    return 3


if __name__ == "__main__":
    sys.exit(main())
