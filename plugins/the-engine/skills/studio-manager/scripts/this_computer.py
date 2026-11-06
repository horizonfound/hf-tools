#!/usr/bin/env python3
"""Everything that is different between a Mac and a Windows PC, in one place.

The Assistant was built on a Mac. Wherever a script needs something the two computers do differently
(how much room a drive has, which drives are plugged in, hiding a folder, writing "October 4" without
a zero, keeping the computer awake, starting a page server that stays up), it asks here, and this file
knows both ways. A script should never call a Mac-only tool itself. docs/pc-readiness-2026-11-06.md
is the list this file works through.

Nothing here has run on a real PC yet (Nov 6, 2026). The Mac side is what the scripts did before,
moved here unchanged. Every Windows branch is written from Microsoft's and Python's documentation and
fails quietly to a safe answer: an empty list, None, False. Never a guess.

    python3 this_computer.py          prints what it can see: a quick health check for a new computer

Not called platform.py on purpose: that name would hide Python's own module from every script here.
"""
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

WINDOWS = os.name == "nt"
MAC = sys.platform == "darwin"

# Words a photographer sees.
COMPUTER = "PC" if WINDOWS else ("Mac" if MAC else "computer")
FILES_APP = "File Explorer" if WINDOWS else ("Finder" if MAC else "the file manager")
APP_BAR = "the taskbar" if WINDOWS else "the Dock"
COPY_KEY = "Ctrl" if WINDOWS else "Option"

if WINDOWS:
    # Scripts started by other scripts (the page servers, a rename from the report) read and write UTF-8
    # whatever this PC's own default is. Read by Python when a process starts, so it reaches children only.
    os.environ.setdefault("PYTHONUTF8", "1")


# ---------------------------------------------------------------- text

def utf8_output():
    """Whatever a script prints goes out as UTF-8, so a name with an accent or an emoji in a caption never
    stops it. A Mac already does this; a PC uses an older code page for output unless told."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001  (a stream that was replaced, or closed)
            pass


# ---------------------------------------------------------------- dates in words

def strftime(when, fmt):
    """when.strftime(fmt), where %-d, %-I, %-m, %-H, %-M, %-S, %-j and %-y (the number without a leading
    zero) work on every computer. Windows does not know the %- spelling, so the number is put in here."""
    def number(m):
        return str(int(when.strftime("%" + m.group(1))))
    return when.strftime(re.sub(r"(?<!%)%-([dmHIMSjy])", number, fmt))


# ---------------------------------------------------------------- room on a drive

def disk(path):
    """(total bytes, free bytes) for the drive a folder is on, or None if it cannot be asked."""
    try:
        u = shutil.disk_usage(str(path))
        return u.total, u.free
    except (OSError, ValueError):
        return None


def free_bytes(path):
    d = disk(path)
    return d[1] if d else None


# ---------------------------------------------------------------- hiding the Assistant's own folders

def hide(path):
    """Out of sight in Finder or File Explorer. The name does not change, so every script still finds it.
    On a Mac a name starting with a dot is hidden already; on a PC nothing is hidden unless marked."""
    try:
        if MAC:
            subprocess.run(["chflags", "hidden", str(path)], check=False, capture_output=True)
        elif WINDOWS:
            subprocess.run(["attrib", "+h", str(path)], check=False, capture_output=True)
    except OSError:
        pass


# ---------------------------------------------------------------- names Windows refuses

_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}


def not_reserved(name):
    """The older name for unreserved(), kept so nothing that calls it breaks. It used to put the underscore at
    the very end ("aux.jpg_", "Nul. Family_"), which Windows still reads as AUX and NUL; now it is the same as
    unreserved(): "aux_.jpg", "Nul_. Family"."""
    return unreserved(name)


def unreserved(name):
    """The name, with an underscore straight after a word Windows keeps for itself, before any dot: "CON" ->
    "CON_", "Nul. Family" -> "Nul_. Family", "aux.jpg" -> "aux_.jpg". Windows reads a reserved word followed by
    a dot and anything at all as that word ("NUL.txt" is NUL), so an underscore at the very end would not help
    a name with a dot in it. Every other name comes back exactly as it was. The same on both computers, so a
    drive can move between them."""
    name = str(name)
    head, dot, rest = name.partition(".")
    word = head.rstrip()
    if word.strip().upper() not in _RESERVED:
        return name
    return word + "_" + head[len(word):] + dot + rest


def drive_words(path):
    """How to say which drive a folder is on when it is not there ("Plug in Big Kahuna"), or None."""
    parts = Path(path).parts
    if len(parts) > 2 and parts[1] == "Volumes":
        return parts[2]
    drive = os.path.splitdrive(str(path))[0]
    if WINDOWS and re.fullmatch(r"[A-Za-z]:", drive):
        return f"the drive that was {drive.upper()}"
    return None


def safe_name(name, limit=80, fallback="Untitled"):
    """A folder or file name every Mac, PC and cloud drive accepts: none of  \\ / : * ? " < > |  or control
    characters, no dot or space at the end, not one of the few names Windows keeps for itself (CON, AUX,
    NUL, COM1...), and not too long. The same on both computers, so a drive can move between them."""
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", str(name))
    name = re.sub(r"\s+", " ", name).strip(" .")[:limit].strip(" .")
    if not name:
        return fallback
    return unreserved(name)


# ---------------------------------------------------------------- staying awake

def keep_awake():
    """Ask a PC not to doze off while this process is working (it stops asking when the process ends).
    Like the Mac's caffeinate, it cannot stop a closed lid. On a Mac the long steps run under caffeinate
    instead (awake_command). True if the PC was asked."""
    if not WINDOWS:
        return False
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        return bool(ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED))
    except Exception:  # noqa: BLE001
        return False


def awake_command(cmd):
    """The command to run for a long step so the computer stays awake through it."""
    if MAC and Path("/usr/bin/caffeinate").exists():
        return ["/usr/bin/caffeinate", "-i", *cmd]
    keep_awake()
    return list(cmd)


# ---------------------------------------------------------------- a server that outlives its starter

def popen_detached(cmd, **kw):
    """Start a process (a page's little server) that keeps running after the command that started it ends."""
    if WINDOWS:
        # unproven on a real PC. CREATE_NO_WINDOW gives the server a console of its own with no window, apart
        # from its starter's, so closing the starter's window does not end it; CREATE_NEW_PROCESS_GROUP keeps a
        # Ctrl+C there from reaching it. Not DETACHED_PROCESS (no console at all): then every helper the server
        # runs later (a rename from the report, the report rebuilt) would get a new console, which Windows shows
        # as a black window that flashes up, and closing that window would end the rename part way. Microsoft:
        # CREATE_NO_WINDOW "is ignored ... if used with ... DETACHED_PROCESS", so never the two together.
        CREATE_NO_WINDOW, CREATE_NEW_PROCESS_GROUP = 0x08000000, 0x00000200
        kw["creationflags"] = kw.get("creationflags", 0) | CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
        kw.setdefault("stdin", subprocess.DEVNULL)
        kw.setdefault("close_fds", True)
    else:
        kw.setdefault("start_new_session", True)
    return subprocess.Popen(cmd, **kw)


# ---------------------------------------------------------------- saving over a file someone is reading

def replace(src, dst, tries=25):
    """os.replace that waits a moment on a PC when another program has the file open right then (a page
    server reading a list while a command saves it; the virus checker reading a file just written). A Mac
    never refuses. After about three seconds the refusal is passed on, never swallowed."""
    for i in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if not WINDOWS or i == tries - 1:
                raise
            time.sleep(0.01 * (i + 1))


# ---------------------------------------------------------------- moving a file or folder on the same drive

class HeldOpen(PermissionError):
    """A PC would not move a file or a folder because another program has something in it open (Lightroom,
    a File Explorer window, the virus checker). Nothing moved in that one step. `words` is what to tell the
    photographer; str() keeps the details (which file, what Windows said) for the log and for Claude."""
    words = ("Something has a photo in this folder open (Lightroom, or a folder window). Close it and say go: "
             "nothing is lost, and running it again finishes the job.")

    def __init__(self, src, dst, cause):
        self.src, self.dst, self.cause = str(src), str(dst), cause
        self.winerror = getattr(cause, "winerror", None)
        super().__init__(13, f"another program has it open, so it could not be moved: {src} -> {dst} ({cause})")


def _patient(step, what, wait):
    """Run step(); on a PC, a refusal because something has the file open is tried again for `wait`
    seconds before it is passed on as HeldOpen. Any other error goes straight through, untouched."""
    # unproven on a real PC: written from Python's and Microsoft's documentation. A file or folder another
    # program holds open gives ERROR_SHARING_VIOLATION (32) or ERROR_ACCESS_DENIED (5), which Python raises
    # as PermissionError. "Already exists" is FileExistsError and "not there" FileNotFoundError: never retried.
    deadline = time.monotonic() + wait
    pause = 0.05
    while True:
        try:
            return step()
        except PermissionError as e:
            left = deadline - time.monotonic()
            if left <= 0:
                raise HeldOpen(what[0], what[1], e) from e
            time.sleep(min(pause, left))  # the last try comes right at the deadline
            pause = min(pause * 2, 0.5)


def rename(src, dst, wait=6.0):
    """Move a file or a folder to a new name on the same drive. On a Mac this is exactly os.rename.

    A PC refuses while another program has a file there open: Lightroom, a File Explorer window showing it,
    the virus checker reading a file just written. Most of those let go within a second, so the move is tried
    again for a few seconds; then HeldOpen (a PermissionError) is raised, which the callers turn into plain
    words. Every caller writes its log before it moves anything, so running it again finishes the job.

    It adds no "is something already there" check of its own: the callers check before they move, and a name
    that differs only in upper and lower case (a rename on a drive that ignores case) must go straight
    through. On a PC a name that is already there is refused by Windows itself (FileExistsError, passed on)."""
    if not WINDOWS:
        return os.rename(src, dst)
    return _patient(lambda: os.rename(src, dst), (src, dst), wait)


def rmdir(path, wait=6.0):
    """Take down an empty folder. On a Mac exactly os.rmdir. On a PC a folder window or a command window
    sitting in it can hold it for a moment, so that is tried again for a few seconds, then raised as HeldOpen.
    A folder with anything in it is refused on both, as before (OSError, never HeldOpen)."""
    if not WINDOWS:
        return os.rmdir(path)
    return _patient(lambda: os.rmdir(path), (path, path), wait)


def rename_new(src, dst, tries=25):
    """Give a finished file its real name, never taking a name that is already in use (one could appear between
    a check and the rename). True when it has the name; False when something else already had it: then nothing
    moved, and src is still under its own name for the caller to deal with.

    A Mac: a hard link (which never takes a name that is there) and then the old name is dropped; on a drive with
    no links (exFAT, FAT, some network drives) the name is checked and then renamed. A plain os.rename on a Mac
    would quietly replace a file that is there. (Moved here from posts.into_place, Nov 6; unchanged.)
    A PC: os.rename, which Windows refuses onto a name that is there (FileExistsError). A virus checker still
    reading the new file gets a few short waits (about three seconds in all) before its refusal is passed on."""
    if WINDOWS:
        # unproven on a real PC. os.rename there is MoveFileEx without "replace".
        for i in range(tries):
            try:
                os.rename(src, dst)
                return True
            except FileExistsError:
                return False
            except PermissionError:
                if i == tries - 1:
                    raise
                time.sleep(0.01 * (i + 1))
    try:
        os.link(src, dst)                        # a Mac: a link never takes a name that is already there
    except FileExistsError:
        return False
    except OSError:                              # a drive with no links (exFAT, FAT, some network drives)
        if os.path.lexists(dst):
            return False
        os.rename(src, dst)
        return True
    os.unlink(src)                               # the same file is under its real name now; only the old name goes
    return True


def try_lock(f, shared=False):
    """Try once, without waiting, to lock an open lock file so that no other program of the Assistant's can
    hold it at the same time. True: held. False: something else holds it right now. None: this computer or
    this drive has no such locks (carry on without one, as before). The computer lets go of the lock by itself
    if the holder dies.

    A Mac (and Linux): fcntl.flock, exclusive or shared, exactly the call the scripts made before Nov 6.
    A PC: msvcrt.locking on the file's first byte. Windows has no shared lock there, so a shared ask is an
    exclusive try; whoever asks only to look (is a job at work?) must let go at once with unlock(f)."""
    if WINDOWS:
        # unproven on a real PC. msvcrt.locking locks bytes from the file's current place, so go to the start;
        # locking past the end of an empty file is allowed. EACCES means another handle holds that byte.
        import errno
        import msvcrt
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError as e:
            if e.errno in (errno.EACCES, getattr(errno, "EDEADLOCK", errno.EDEADLK)):
                return False
            return None
    try:
        import fcntl
    except ImportError:
        return None
    try:
        fcntl.flock(f, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False
    except OSError:
        return None


def unlock(f):
    """Let go of a lock taken with try_lock. Never raises: closing the file lets go of it as well."""
    try:
        if WINDOWS:
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_UN)
    except (OSError, ImportError):
        pass


def still_running(pid):
    """Is the program with this number still running? True, False, or None when this computer can't say.
    A Mac: os.kill(pid, 0), which asks and changes nothing (a program it may not signal is still running).
    A PC: never os.kill there (signal 0 is Ctrl+C on Windows); the process is opened just to read whether it
    has ended (OpenProcess + GetExitCodeProcess, which is 259, STILL_ACTIVE, while it runs)."""
    if type(pid) is not int or pid <= 0:
        return False
    if WINDOWS:
        # unproven on a real PC.
        try:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.OpenProcess.restype = wintypes.HANDLE
            k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            k32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
            k32.CloseHandle.argtypes = (wintypes.HANDLE,)
            h = k32.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                err = ctypes.get_last_error()
                if err == 87:                                # ERROR_INVALID_PARAMETER: no such process
                    return False
                if err == 5:                                 # ERROR_ACCESS_DENIED: it exists, someone else's
                    return True
                return None
            try:
                code = wintypes.DWORD()
                if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
                    return None
                return code.value == 259
            finally:
                k32.CloseHandle(h)
        except Exception:
            return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None


_PC_HOUSEKEEPING ={"thumbs.db", "ehthumbs.db", "ehthumbs_vista.db", "desktop.ini"}


def housekeeping_file(name):
    """A file the computer itself leaves in folders, never a photo: Finder's .DS_Store and the other files
    whose names start with a dot; on a PC also File Explorer's Thumbs.db and desktop.ini."""
    name = str(name)
    if name.startswith("."):
        return True
    return WINDOWS and name.lower() in _PC_HOUSEKEEPING  # unproven on a real PC


# ---------------------------------------------------------------- how long a path may be

WINDOWS_FILE_LIMIT = 259    # MAX_PATH is 260, and Windows counts the closing character it adds
WINDOWS_FOLDER_LIMIT = 247  # a folder has to leave room for a short name inside it (MAX_PATH - 12, less the same one)
_LONG_PATHS = []


def long_paths_on():
    """True when this computer takes paths longer than 260 characters. A Mac always does. A PC does only when
    long paths have been switched on (an administrator's setting: LongPathsEnabled, Windows 10 and 11; Python
    itself has been ready for them since 3.6). Read once. Only the Assistant's own hidden files rely on it
    (records_path_too_long); photos and shoot folders are held to 260 whatever it says (path_too_long)."""
    if not WINDOWS:
        return True
    if not _LONG_PATHS:
        on = False
        try:  # unproven on a real PC
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem") as key:
                value, kind = winreg.QueryValueEx(key, "LongPathsEnabled")
            on = kind == winreg.REG_DWORD and bool(value)
        except (OSError, ImportError):
            on = False
        _LONG_PATHS.append(on)
    return _LONG_PATHS[0]


def _places(t):
    """How many places Windows counts in a path: it counts in UTF-16, where an emoji takes two."""
    return len(t.encode("utf-16-le", "surrogatepass")) // 2


def _too_long(path, folder, python_only):
    # unproven on a real PC
    s = str(path)
    long_form = s.startswith("\\\\?\\")
    if long_form:
        if python_only:
            return False  # a path written in Windows' long form is exempt from the limit, for Python
        s = s[4:]  # for File Explorer it is the same path, and just as long
    s = os.path.abspath(s)
    if any(_places(part) > 255 for part in re.split(r"[\\/]+", s) if part):
        return True  # one name longer than 255: too long on every drive Windows knows
    if python_only and long_paths_on():
        return False
    return _places(s) > (WINDOWS_FOLDER_LIMIT if folder else WINDOWS_FILE_LIMIT)


def path_too_long(path, folder=False):
    """True when, on a PC, a photo or folder at this path could not be opened, moved or deleted in File
    Explorer: longer than 260 characters for a file or 248 for a folder (counting the drive and every folder
    on the way), or any one name in it longer than 255. This holds even where long paths have been switched on
    (LongPathsEnabled, which Python's own installers offer to set): that setting helps only programs written
    for it, and File Explorer is not one of them (Lightroom is unproven). So it is used for everything a
    photographer will open: their shoot folders and photos. A Mac: never (as before)."""
    if not WINDOWS:
        return False
    return _too_long(path, folder, python_only=False)


def records_path_too_long(path, folder=False):
    """The same check for the Assistant's own hidden files (a backup's records, its previews), which only the
    Assistant's scripts open: there, long paths switched on is enough. A Mac: never."""
    if not WINDOWS:
        return False
    return _too_long(path, folder, python_only=True)


def same_place(a, b):
    """Two paths name the same place: on a PC upper and lower case and the kind of slash do not matter
    ("e:\\photos" and "E:/Photos"); on a Mac the text has to match, as before."""
    if WINDOWS:  # unproven on a real PC
        return os.path.normcase(os.path.normpath(str(a))) == os.path.normcase(os.path.normpath(str(b)))
    return str(a) == str(b)


# ---------------------------------------------------------------- drives and memory cards

def _mac_volumes():
    out = []
    root = Path("/Volumes")
    if not root.is_dir():
        return out
    try:
        boot = os.stat("/").st_dev
    except OSError:
        boot = None
    for v in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        d = disk(v)
        if not d:
            continue
        try:
            system = v.name in ("Macintosh HD", "Recovery") or os.stat(v).st_dev == boot
        except OSError:
            system = False
        out.append({"path": str(v), "name": v.name, "shown": v.name, "total": d[0], "free": d[1],
                    "system": system, "removable": None, "id": None})
    return out


def _windows_volumes():
    out = []
    try:
        import ctypes
        import string
        k = ctypes.windll.kernel32
        mask = k.GetLogicalDrives()
        sysdrive = (os.environ.get("SystemDrive") or "C:").upper()
        for i, letter in enumerate(string.ascii_uppercase):
            if not mask & (1 << i):
                continue
            root = f"{letter}:\\"
            kind = k.GetDriveTypeW(ctypes.c_wchar_p(root))      # 2 removable (card readers), 3 fixed
            if kind not in (2, 3):
                continue                                        # network drives, discs, anything odd
            label = ctypes.create_unicode_buffer(261)
            fs = ctypes.create_unicode_buffer(261)
            serial = ctypes.c_ulong(0)
            old = k.SetErrorMode(1)                             # no "insert a disk" window for an empty reader
            try:
                ok = k.GetVolumeInformationW(ctypes.c_wchar_p(root), label, 261, ctypes.byref(serial), None, None, fs, 261)
            finally:
                k.SetErrorMode(old)
            d = disk(root) if ok else None
            if not d:
                continue                                        # an empty card reader
            name = label.value.strip() or ("Card" if kind == 2 else "Drive")
            out.append({"path": root, "name": name, "shown": f"{name} ({letter}:)", "total": d[0], "free": d[1],
                        "system": f"{letter}:" == sysdrive, "removable": kind == 2,
                        "id": f"{serial.value:08X}", "format": fs.value})
    except Exception:  # noqa: BLE001  (never let a drive listing stop a script)
        pass
    return out


def volumes():
    """Every drive plugged in right now. Each: path (where its files start), name (what they called it),
    shown (how to say it to them: "Big Kahuna" on a Mac, "Big Kahuna (E:)" on a PC), total and free
    bytes, system (the computer's own disk), removable (True, False, or None when the Mac cannot say),
    id (the volume's own number on a PC, which changes when a card is formatted)."""
    if WINDOWS:
        return _windows_volumes()
    if MAC:
        return _mac_volumes()
    return []


def cards():
    """Memory cards in right now: a drive with a DCIM folder at the top. The same list on both computers."""
    out = []
    for v in volumes():
        try:
            if not v["system"] and (Path(v["path"]) / "DCIM").is_dir():
                out.append(v)
        except OSError:
            pass
    return out


def volume_by_name(name):
    """The drive they mean when they say its name ("Big Kahuna", "E:", "Big Kahuna (E:)"), or None."""
    want = str(name).strip().strip("/\\").lower()
    if not want:
        return None
    for v in volumes():
        letter = v["path"].rstrip("\\/").lower() if WINDOWS else None
        if want in (v["name"].lower(), v["shown"].lower()) or (letter and want in (letter, letter.rstrip(":"))):
            return v
    return None


def volume_id(path):
    """A PC's own number for the drive a folder is on, or None. (A Mac's comes from diskutil, in cards.py.)"""
    if not WINDOWS:
        return None
    drive = os.path.splitdrive(os.path.abspath(str(path)))[0].upper()
    for v in volumes():
        if v["path"].upper().startswith(drive):
            return v["id"]
    return None


def drive_root(letter_or_path):
    """"E:" means the top of drive E. Python reads a bare "E:" as "wherever I last was on E", which is
    never what a photographer means, so a bare letter gets its slash here."""
    s = str(letter_or_path)
    if WINDOWS and re.fullmatch(r"[A-Za-z]:", s.strip()):
        return Path(s.strip() + "\\")
    return Path(s)


# ---------------------------------------------------------------- Pictures, Desktop, Downloads, Music

_WINDOWS_FOLDERS = {"Pictures": "My Pictures", "Desktop": "Desktop", "Music": "My Music", "Documents": "Personal",
                    "Videos": "My Video", "Downloads": "{374DE290-123F-4565-9164-39C4925E467B}"}


def known_folder(name):
    """Where Pictures, Desktop, Downloads, Music or Documents really is. On a PC, Windows often moves
    these into OneDrive, so they are asked for rather than assumed to sit in the home folder."""
    if WINDOWS:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                value, _ = winreg.QueryValueEx(key, _WINDOWS_FOLDERS.get(name, name))
            p = Path(os.path.expandvars(value))
            if p.is_dir():
                return p
        except Exception:  # noqa: BLE001
            pass
    return Path.home() / name


# ---------------------------------------------------------------- the folder picker

def pick_folder(prompt):
    """The computer's own "choose a folder" window. (path, "") when they chose one, (None, "cancelled") when
    they closed it, (None, why) when the window could not be shown."""
    try:
        if MAC:
            script = ('tell application "System Events" to activate\n'
                      f'set f to choose folder with prompt "{prompt}"\n'
                      'POSIX path of f')
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=300)
            folder = r.stdout.strip()
            if r.returncode == 0 and folder:
                return folder, ""
            return None, "cancelled" if "-128" in (r.stderr or "") else "the folder window did not open"
        if WINDOWS:
            ps = ("Add-Type -AssemblyName System.Windows.Forms; "
                  "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                  "$d.Description = $env:ASSISTANT_PICK_PROMPT; $d.ShowNewFolderButton = $false; "
                  "$top = New-Object System.Windows.Forms.Form; $top.TopMost = $true; "
                  "[Console]::OutputEncoding = [Text.Encoding]::UTF8; "
                  "if ($d.ShowDialog($top) -eq 'OK') { Write-Output $d.SelectedPath } else { Write-Output '::cancelled::' }")
            env = dict(os.environ, ASSISTANT_PICK_PROMPT=prompt)
            r = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", ps], capture_output=True,
                               encoding="utf-8", errors="replace", timeout=300, env=env)
            folder = (r.stdout or "").strip()
            if folder == "::cancelled::":
                return None, "cancelled"
            if r.returncode == 0 and folder and Path(folder).is_dir():
                return folder, ""
            return None, "the folder window did not open"
    except (OSError, subprocess.SubprocessError):
        pass
    return None, "the folder window did not open"


# ---------------------------------------------------------------- a quick look, for a new computer

def _gb(n):
    return f"{n / 1e12:.1f} TB" if n >= 1e12 else f"{n / 1e9:.0f} GB"


def main():
    from datetime import datetime
    utf8_output()
    print(f"This is a {COMPUTER}. Python {sys.version.split()[0]}. Text goes out as {sys.stdout.encoding}.")
    print("A date in words:", strftime(datetime(2026, 11, 6, 9, 5), "%A, %B %-d, %Y at %-I:%M %p"))
    vols = volumes()
    print(f"Drives plugged in: {len(vols)}")
    for v in vols:
        kind = "this computer's own disk" if v["system"] else ("a card or removable drive" if v["removable"] else "a drive")
        print(f"  {v['shown']}: {_gb(v['total'])}, {_gb(v['free'])} free, {kind}")
    c = cards()
    print("Memory card in: " + (", ".join(v["shown"] for v in c) if c else "none"))
    print("Pictures folder:", known_folder("Pictures"))
    home = disk(Path.home())
    print("Room where your home folder is:", _gb(home[1]) + " free" if home else "could not ask")
    for tool, what in (("sips", "the Mac's picture tool"), ("afconvert", "the Mac's sound tool"), ("ffmpeg", "ffmpeg"),
                       ("curl", "curl"), ("powershell", "PowerShell")):
        print(f"  {what}: {'here' if shutil.which(tool) else 'not here'}")
    try:
        import PIL
        print("  Pillow (pictures on a PC):", PIL.__version__)
    except ImportError:
        print("  Pillow (pictures on a PC): not here")
    print("A name made safe:", safe_name('Card 10:30 / "aux". '), "|", safe_name("CON"))


if __name__ == "__main__":
    main()
