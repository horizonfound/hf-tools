#!/usr/bin/env python3
"""Stop new Mac-only lines getting into the Assistant's scripts.

The Assistant has to work on a Windows PC too (Dustin, Nov 6, 2026). Everything the two computers do
differently has a home of its own, and no other script may do a Mac-only thing itself:

    skills/studio-manager/scripts/this_computer.py     drives, hiding, staying awake, folders, moving files
    skills/studio-manager/scripts/pictures.py          small pictures (the Mac's sips; on a PC, Pillow)
    skills/assistant-make-a-reel/scripts/sound.py      a song's length and sound (afconvert, afinfo; on a PC,
                                                        plain Python and Windows' own Media Foundation)

    python3 tools/check_pc.py

Exit 0: clean. Exit 1: something to fix (STOP lines). NOTE lines are the known work still to do
(docs/pc-readiness-2026-11-06.md); they do not stop anything, they keep the list honest.

A line that calls a Mac-only tool from inside a branch that only a Mac reaches is marked "# pc-ok: why"; the
check then lets it be (the marker is the promise that a PC never runs it).

NOT_YET holds the scripts that have not been through the PC pass. Take a script off that list when it
has been done; the check then holds it to the rules for good. KNOWN holds the few lines in scripts that HAVE
been through the pass but that this check only learned to see later (Nov 6, second review): each is counted,
so one more of the same kind in that script still stops, and each says what to do.

How the check reads a script (Nov 6, second review): with Python's own tokenizer and syntax tree, never by
guessing from how lines start. The first version took the closing \"\"\" of any long text block (page styles,
a sidecar template) for the start of a docstring and skipped the real code after it: 276 lines in 9 scripts
were never read. Now only comments and real docstrings (the first statement of a module, class or function)
are left out; every other line is read, including the lines inside other strings, since commands are often
written in strings. The check tries itself on made-up scripts every time it runs (self_test), so a reader
that goes wrong again stops the check instead of quietly calling everything clean.
"""
import ast
import io
import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "plugins" / "the-engine" / "skills"

# Not through the PC pass yet, or parked since Oct 24. Empty since Nov 6: the last five (arrange.py,
# arrange_page.py, kit.py, posting_queue.py, canva_kit.py), held back while another session changed them, have
# been through it. A script added later that is not ready for a PC yet goes here, by name, with a note why.
NOT_YET = set()
PARKED = {"make_reel.py", "beats.py", "grade_reel.py", "find_music.py", "hooktext.py", "check_setup.py"}

# Where the Mac-only tools may be called from: their homes (paths under skills/).
HOMES = {"studio-manager/scripts/this_computer.py", "studio-manager/scripts/pictures.py",
         "assistant-make-a-reel/scripts/sound.py"}

# Mac-only tools no other script may call itself: (tool, what it is for, where calling it belongs).
# A tool whose name is also an everyday word ("say", "defaults", "ditto") only counts when it stands alone in
# quotes ("say", or "/usr/bin/say"), so a sentence that starts with the word is not taken for a command.
EVERYDAY_WORDS = {"say", "defaults", "ditto"}
MAC_TOOLS = [("sips", "pictures", "pictures.py (make_jpeg, thumb_rows, size_of)"),
             ("afconvert", "hearing a song", "sound.py (decode, extract_audio)"),
             ("afinfo", "a song's length", "sound.py (duration)"),
             ("avconvert", "pulling the sound out of a video", "sound.py (extract_audio)"),
             ("afplay", "playing a sound", "sound.py, or a Mac-only branch"),
             ("osascript", "Finder and the folder picker", "this_computer.py (pick_folder), or a Mac-only branch like finder.py's"),
             ("diskutil", "a drive's own number", "this_computer.py (volume_id)"),
             ("hdiutil", "disk images", "this_computer.py, or a Mac-only branch"),
             ("lsappinfo", "which app is in front", "this_computer.py, or a Mac-only branch like return_watch.py's"),
             ("ioreg", "how long the computer has been idle", "this_computer.py, or a Mac-only branch like return_watch.py's"),
             ("mdls", "Spotlight's notes on a file", "a Mac-only branch"),
             ("mdfind", "a Spotlight search", "a Mac-only branch"),
             ("pbcopy", "the clipboard", "a Mac-only branch (a PC has no such command)"),
             ("pbpaste", "the clipboard", "a Mac-only branch (a PC has no such command)"),
             ("xattr", "a file's extra Mac notes", "a Mac-only branch"),
             ("xcrun", "Apple's developer tools", "a Mac-only branch"),
             ("defaults", "the Mac's settings", "a Mac-only branch"),
             ("ditto", "a Mac copy", "a copy the backup's way (hash while copying), on both computers"),
             ("say", "the Mac speaking", "a Mac-only branch"),
             ("chflags", "hiding a folder", "this_computer.py (hide)"),
             ("caffeinate", "keeping the computer awake", "this_computer.py (keep_awake, awake_command)"),
             ("attrib", "hiding a folder on a PC", "this_computer.py (hide)"),
             # Nov 6, test review: these five were not on the list, and pgrep only printed a NOTE
             ("pgrep", "whether a program is running", "a Mac-only branch, like capcut.py's (a PC asks its own way)"),
             ("killall", "ending a program by its name", "a Mac-only branch (a PC has no such command)"),
             ("pkill", "ending a program by its name", "a Mac-only branch (a PC has no such command)"),
             ("lsof", "which program holds a file open", "this_computer.py, or a Mac-only branch"),
             ("launchctl", "the Mac's background jobs", "a Mac-only branch"),
             ("pmset", "the Mac's sleep settings", "this_computer.py (keep_awake), or a Mac-only branch")]
# Mac-only tools still called directly somewhere, without a home yet: listed so they cannot be forgotten.
# Empty since Nov 6: pgrep (is CapCut open) became a STOP like the others; capcut.py's one call is in its Mac
# branch, marked pc-ok.
STILL_DIRECT = []

# A line is let be only for a comment that is itself the marker, "# pc-ok: why" (a comment that only mentions
# the words, like "# not pc-ok yet", excuses nothing; Nov 6, test review).
PC_OK = re.compile(r"#\s*pc-ok:")


def tool_call(tool):
    """A quoted tool name, as in ["sips", ...], shutil.which("afinfo"), "/usr/bin/caffeinate" or
    "caffeinate -i ...". An everyday word only alone in quotes, or with a /usr/bin/ in front."""
    if tool in EVERYDAY_WORDS:     # ["say", ...], which("say"), "/usr/bin/say ..."; never className = 'say'
        return re.compile(rf"""[\[(]\s*["'](?:/usr/s?bin/)?{tool}["']|["']/usr/s?bin/{tool}["'\s]""")
    return re.compile(rf"""["'](?:[^"'\s]*/)?{tool}(?=["'\s])""")


# Things no script may do itself: (short name, what to look for, what to say). The short name is what KNOWN
# and the NOT_YET note count by. These look at each line as written (strings included, since a command or a
# "python -c" snippet is often written in one); the same kinds are also found in the syntax tree (WHY and
# tree_problems below), which sees a call split over lines, "import os, fcntl", os.kill(int(pid), 0) and a date
# format inside an f-string. A hit both ways on one line counts once.
WHY = {
    "%-d": "%-d and friends are not understood on Windows: use this_computer.strftime(when, fmt)",
    "Mac open": "the Mac's open command does not exist on a PC: finder.py opens folders on both, os.startfile opens a file on a PC",
    "fcntl": "fcntl does not exist on Windows: the lock belongs in this_computer.py (try_lock, unlock)",
    "Mac-only module": "that module does not exist on Windows: put the use behind this_computer.WINDOWS, or in this_computer.py",
    "os.kill(pid, 0)": "on Windows os.kill(pid, 0) does not ask whether a process is still running: signal 0 there is Ctrl+C, "
                       "sent to that process's group (or it ends it outright). Use this_computer.still_running(pid)",
}
MAC_MODULES = {"fcntl", "termios", "tty", "pty", "pwd", "grp", "resource", "posix"}
RULES = [
    ("statvfs", re.compile(r"os\.statvfs"), "os.statvfs does not exist on Windows: use this_computer.disk() or free_bytes()"),
    # Nov 6, the designer's join: also the spelling in a dict of options ({"start_new_session": True}), which is how
    # design.py started its commit before it was brought under these rules, and which this check did not see
    ("new session", re.compile(r"""start_new_session\s*=|["']start_new_session["']\s*:"""),
     "start_new_session does nothing on Windows: use this_computer.popen_detached()"),
    ("/Volumes", re.compile(r"""["']/Volumes(?:[/"']|\b)"""),
     "/Volumes is where a Mac puts drives: use this_computer.volumes(), cards() or volume_by_name()"),
    ("Mac open", re.compile(r"""\[\s*["'](?:/usr/bin/)?open["']|["']/usr/bin/open["'\s]"""), WHY["Mac open"]),
    ("fcntl", re.compile(r"\bimport\s+fcntl\b|\bfrom\s+fcntl\s+import\b"), WHY["fcntl"]),
    ("Mac-only module", re.compile(r"\b(?:import|from)\s+(?:termios|tty|pty|pwd|grp|resource|posix)\b"), WHY["Mac-only module"]),
    ("os.kill(pid, 0)", re.compile(r"os\.kill\([^,()]+,\s*0\s*\)"), WHY["os.kill(pid, 0)"]),
    ("WNOHANG", re.compile(r"os\.WNOHANG"), "os.WNOHANG does not exist on Windows: put it behind this_computer.WINDOWS"),
    ("preexec_fn", re.compile(r"\bpreexec_fn\s*="), "Windows refuses preexec_fn: use this_computer.popen_detached() or creationflags"),
    ("Mac-only signal", re.compile(r"signal\.SIG(?:KILL|HUP|USR1|USR2|ALRM|CHLD|QUIT|PIPE|STOP|CONT|TSTP|WINCH)\b"),
     "that signal does not exist on Windows (only SIGTERM, SIGINT and SIGBREAK do): put it behind this_computer.WINDOWS"),
    ("Mac-only signal call", re.compile(r"signal\.(?:alarm|pause|setitimer|siginterrupt)\("),
     "that signal call does not exist on Windows: put it behind this_computer.WINDOWS"),
    ("Mac-only os call", re.compile(r"\bos\.(?:killpg|setsid|getpgid|setpgrp|setpgid|fork|getuid|geteuid|getgid|chown|lchown|sync)\("),
     "that os call does not exist on Windows: put it behind this_computer.WINDOWS, or in this_computer.py"),
    ("st_flags", re.compile(r"\.st_flags\b"), "st_flags (the Mac's hidden flag) does not exist on Windows: use getattr(st, \"st_flags\", 0) or this_computer"),
    ("os.popen", re.compile(r"\bos\.popen\("), 'os.popen reads in the PC\'s own code page: use subprocess.run with encoding="utf-8"'),
    ("execv", re.compile(r"os\.exec[lv]p?e?\("), None),    # only fresh.py, which has its Windows branch beside it
    # Nov 6 follow-up: Python's own urlopen takes the computer's proxy (on a PC from Windows' own settings, where
    # "<local>" leaves 127.0.0.1 out), and a proxy can't see this computer's pages, so "is the page server up?"
    # said no and another server was started. Nothing here fetches from the internet with urllib either.
    ("urlopen", re.compile(r"\burlopen\("),
     "urllib's urlopen goes through a proxy set on the computer (on a PC, Windows' own settings): this computer's "
     "own pages through this_computer.open_local(url, timeout), the internet through curl (this_computer.run_curl)"),
]
# Texts written or read with no encoding: found in the syntax tree, never by guessing from the line.
ENCODING = "no encoding"
ENCODING_WORDS = {
    "open": "a file opened as text with no encoding (a PC uses its own code page): add encoding=\"utf-8\"",
    "open mode": "a file opened with a mode the check can't read, and no encoding: write the mode out (\"rb\" for "
                 "bytes), or pass encoding=\"utf-8\" when it is text",
    "read_text": "a text read with no encoding: add encoding=\"utf-8\"",
    "write_text": "a text written with no encoding (a PC writes its own code page, and an emoji stops it): add encoding=\"utf-8\"",
    "text": "text=True (or universal_newlines=True) with no encoding reads in the PC's own code page: add encoding=\"utf-8\", errors=\"replace\"",
}

# Lines in scripts already through the PC pass that this check only learned to see on Nov 6 (second review).
# (script, short name): (how many there are today, what to do). One more of the same kind in that script stops
# the check; fewer gives a NOTE to lower the number.
KNOWN = {   # night.py's open_report line got its pc-ok marker on Nov 6; these two came with the urlopen rule (Nov 6 follow-up)
    ("night.py", "urlopen"): (1, "open_report's \"is the report server up?\": this_computer.open_local(old, timeout=1) "
                                 "(the change is written out in the follow-up's needs_from_others)"),
    ("serve_report.py", "urlopen"): (3, "report_url() and queue_url(): this_computer.open_local in place of each "
                                        "urllib.request.urlopen (the change is written out in the follow-up's needs_from_others)"),
}


# ---------------------------------------------------------------- reading a script

def _docstring_rows(tree):
    """The rows of every real docstring: the first statement of a module, class or function, when it is a
    plain string."""
    rows = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                rows.update(range(first.lineno, (getattr(first, "end_lineno", None) or first.lineno) + 1))
    return rows


def read_script(text):
    """(code lines, pc-ok rows, tree). Code lines: (line number, the line with its comments and any docstring
    blanked out) for every line that still holds something. Raises SyntaxError for text that is not Python."""
    tree = ast.parse(text)
    doc_rows = _docstring_rows(tree)
    lines = text.split("\n")
    masked = [list(line) for line in lines]
    ok_rows = set()

    def blank(start, end):
        (r0, c0), (r1, c1) = start, end
        for r in range(r0, r1 + 1):
            if r - 1 >= len(masked):
                break
            row = masked[r - 1]
            a = c0 if r == r0 else 0
            b = c1 if r == r1 else len(row)
            for c in range(a, min(b, len(row))):
                row[c] = " "

    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            if PC_OK.search(tok.string):
                ok_rows.add(tok.start[0])
            blank(tok.start, tok.end)
        elif tok.type == tokenize.STRING and tok.start[0] in doc_rows:
            blank(tok.start, tok.end)
    code = [(n, "".join(row)) for n, row in enumerate(masked, 1) if "".join(row).strip() and n not in ok_rows]
    return code, ok_rows, tree


def code_lines(path):
    """(line number, line) for the lines of a script that are code (comments and docstrings left out)."""
    code, _, _ = read_script(path.read_text(encoding="utf-8"))
    return code


_TEXT_MODE = re.compile(r"^[rwax+tU]+$")


def _const_str(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def encoding_problems(tree):
    """(line number, kind) for each text opened, read or written with no encoding."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        kws = {k.arg: k.value for k in node.keywords if k.arg}
        if any(k.arg is None for k in node.keywords):      # **options: cannot tell
            continue
        f, args = node.func, node.args
        name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
        has_enc = "encoding" in kws
        kind = None
        if name in ("open", "fdopen") and (isinstance(f, ast.Name) or (isinstance(f.value, ast.Name)
                                                                   and f.value.id in ("io", "codecs", "os"))):
            # open(file, mode="r", buffering, encoding): mode is the second thing, encoding the fourth
            given = args[1] if len(args) > 1 else kws.get("mode")
            mode = "r" if given is None else _const_str(given)
            if mode is not None and "b" not in mode and not has_enc and len(args) < 4:
                kind = "open"
            elif (mode is None and given is not None and not isinstance(given, ast.Constant) and not has_enc
                  and len(args) < 4 and (isinstance(f, ast.Name) or f.value.id == "io")):
                # open(p, mode) with the mode in a name: it may be text (Nov 6, test review). Only the built-in
                # open and io.open; os.open takes numbers and never reads text.
                kind = "open mode"
        elif name == "open" and isinstance(f, ast.Attribute):
            # Path.open(mode="r", buffering, encoding): only when the mode is plainly a file mode (so
            # webbrowser.open(url), Image.open(path) and wave.open(path, "rb") are never taken for it).
            # Path(x).open() with nothing in the brackets reads text (Nov 6, test review: it was let through).
            if args:
                mode = _const_str(args[0])
                mode = mode if mode is not None and _TEXT_MODE.match(mode) else None
            elif "mode" in kws:
                mode = _const_str(kws["mode"])
            elif set(kws) <= {"buffering", "errors", "newline"}:     # never tarfile.open(fileobj=...) and the like
                mode = "r"
            else:
                mode = None
            if mode is not None and "b" not in mode and not has_enc and len(args) < 3:
                kind = "open"
        elif name == "read_text" and isinstance(f, ast.Attribute):
            if not has_enc and not args:
                kind = "read_text"
        elif name == "write_text" and isinstance(f, ast.Attribute):
            if not has_enc and len(args) < 2:
                kind = "write_text"
        elif name in ("NamedTemporaryFile", "TemporaryFile", "SpooledTemporaryFile"):
            mode = _const_str(args[0]) if args else (_const_str(kws["mode"]) if "mode" in kws else "w+b")
            if mode is not None and "b" not in mode and not has_enc:
                kind = "open"
        if kind is None:
            for flag in ("text", "universal_newlines"):
                v = kws.get(flag)
                if isinstance(v, ast.Constant) and v.value is True and not has_enc:
                    kind = "text"
        if kind:
            found.append((node.lineno, kind))
    return sorted(set(found))


_PCT_DASH = re.compile(r"%-[A-Za-z]")
_FORMAT_FIELD_DASH = re.compile(r"\{[^{}]*:[^{}]*%-[A-Za-z]")       # "{:%-d}" or "{0:%B %-d}", for str.format
_RUNS_A_COMMAND = {"run", "call", "check_call", "check_output", "Popen", "getoutput", "getstatusoutput"}


def _texts(node):
    """Every plain text inside an expression: a format split over lines or joined with +, an f-string's pieces."""
    for n in ast.walk(node):
        s = _const_str(n)
        if s is not None:
            yield s


def _leading_text(node):
    """The text an expression starts with, when it is written out: "open -a X", or f"open {p}" -> "open "."""
    s = _const_str(node)
    if s is None and isinstance(node, ast.JoinedStr) and node.values:
        s = _const_str(node.values[0])
    return s


def _is_open_word(node):
    return _const_str(node) in ("open", "/usr/bin/open")


def _span(node):
    return range(node.lineno, (getattr(node, "end_lineno", None) or node.lineno) + 1)


def tree_problems(tree):
    """(node, short name) for the kinds the line rules miss when a call is split over lines or written another way
    (Nov 6, test review): "import os, fcntl"; os.kill(int(pid), 0); the Mac's open command as ["open", ...] over
    two lines, as a tuple, or in a shell string; %-d in an f-string's format, in "{:%-d}".format(d), or in a
    strftime whose format sits on the next line. A date format kept as data and handed to this_computer.strftime
    later (studio_file.py's "%b %-d %Y") is never a hit: only a format that reaches Python's own strftime or
    format is."""
    helper_mods, helper_funcs, os_kill, run_funcs = {"this_computer"}, set(), set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name == "this_computer":
                    helper_mods.add(a.asname or a.name)
        elif isinstance(n, ast.ImportFrom) and n.level == 0:
            for a in n.names:
                if n.module == "this_computer" and a.name == "strftime":
                    helper_funcs.add(a.asname or a.name)
                elif n.module == "os" and a.name == "kill":
                    os_kill.add(a.asname or a.name)
                elif n.module == "subprocess" and a.name in _RUNS_A_COMMAND:
                    run_funcs.add(a.asname or a.name)
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                base = a.name.split(".")[0]
                if base in MAC_MODULES:
                    hits.append((n, "fcntl" if base == "fcntl" else "Mac-only module"))
        elif isinstance(n, ast.ImportFrom):
            base = (n.module or "").split(".")[0]
            if n.level == 0 and base in MAC_MODULES:
                hits.append((n, "fcntl" if base == "fcntl" else "Mac-only module"))
        elif isinstance(n, ast.List):
            if n.elts and _is_open_word(n.elts[0]):
                hits.append((n, "Mac open"))
        elif isinstance(n, ast.FormattedValue) and n.format_spec is not None:
            if any(_PCT_DASH.search(s) for s in _texts(n.format_spec)):
                hits.append((n, "%-d"))
        elif isinstance(n, (ast.Assign, ast.AnnAssign)) and isinstance(n.value, ast.Tuple):
            # cmd = ("open", "-a", "CapCut") or ("open", path); never STATES = ("open", "closed")
            e = n.value.elts
            if len(e) > 1 and _is_open_word(e[0]) and (_const_str(e[1]) is None or _const_str(e[1]).startswith("-")):
                hits.append((n, "Mac open"))
        elif isinstance(n, ast.Call):
            f, args = n.func, n.args
            fname = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            on = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else None
            first = args[0] if args else None
            # __import__("fcntl"), importlib.import_module("fcntl")
            if fname in ("__import__", "import_module") and first is not None:
                base = (_const_str(first) or "").split(".")[0]
                if base in MAC_MODULES:
                    hits.append((n, "fcntl" if base == "fcntl" else "Mac-only module"))
            # Python's own strftime with %- in its format (this_computer.strftime, however it was imported, is the cure)
            if fname == "strftime":
                helper = (on in helper_mods) if isinstance(f, ast.Attribute) else (fname in helper_funcs)
                if not helper and any(_PCT_DASH.search(s) for a in args for s in _texts(a)):
                    hits.append((n, "%-d"))
            elif fname == "format" and isinstance(f, ast.Name) and len(args) > 1:          # format(d, "%-d")
                if any(_PCT_DASH.search(s) for s in _texts(args[1])):
                    hits.append((n, "%-d"))
            elif fname == "__format__" and first is not None:
                if any(_PCT_DASH.search(s) for s in _texts(first)):
                    hits.append((n, "%-d"))
            elif fname == "format" and isinstance(f, ast.Attribute) and _const_str(f.value) is not None:
                if _FORMAT_FIELD_DASH.search(_const_str(f.value)):                         # "{:%-d}".format(d)
                    hits.append((n, "%-d"))
            # os.kill(anything, 0)
            if (fname == "kill" and ((on == "os") or (isinstance(f, ast.Name) and f.id in os_kill))
                    and len(args) > 1 and isinstance(args[1], ast.Constant) and args[1].value == 0
                    and not isinstance(args[1].value, bool)):
                hits.append((n, "os.kill(pid, 0)"))
            # the Mac's open command as a tuple, or in a command line handed to a shell
            if isinstance(first, ast.Tuple) and first.elts and _is_open_word(first.elts[0]):
                hits.append((n, "Mac open"))
            runs = (on == "os" and fname in ("system", "popen")) or (on == "subprocess" and fname in _RUNS_A_COMMAND) \
                or (isinstance(f, ast.Name) and fname in run_funcs)
            if runs and first is not None:
                lead = (_leading_text(first) or "").lstrip()
                if lead == "open" or lead.startswith(("open ", "/usr/bin/open")):
                    hits.append((n, "Mac open"))
    return hits


def problems(text, rel="", name=""):
    """Every hit in one script: [(line number, short name, what to say)]. rel: its path under skills/."""
    code, ok_rows, tree = read_script(text)
    out = {}
    mac_tools = [(tool_call(t), t, what, home) for t, what, home in MAC_TOOLS]
    for n, line in code:
        for short, rx, why in RULES:
            if rx.search(line):
                if why is None:
                    if name != "fresh.py":
                        out[(n, short)] = "os.execv behaves differently on Windows; see fresh.py for how to restart there"
                    continue
                out[(n, short)] = why
        if rel not in HOMES:
            for rx, tool, what, home in mac_tools:
                if rx.search(line):
                    out[(n, tool)] = (f"{tool} ({what}) only exists on a Mac: it belongs in {home}. "
                                      "A line inside a branch only a Mac reaches is marked '# pc-ok: why'")
    for node, short in tree_problems(tree):
        # a pc-ok marker on any line of the call (or import, or list) lets it be, as it does a one-line call
        if not any(r in ok_rows for r in _span(node)):
            out.setdefault((node.lineno, short), WHY[short])
    for n, kind in encoding_problems(tree):
        if n not in ok_rows:
            out[(n, ENCODING)] = ENCODING_WORDS[kind]
    return sorted((n, short, why) for (n, short), why in out.items())


def still_direct(text):
    code, _, _ = read_script(text)
    rx = [(tool_call(t), t, what) for t, what in STILL_DIRECT]
    return {(t, what) for _, line in code for r, t, what in rx if r.search(line)}


# ---------------------------------------------------------------- the check tries itself first

_CSS_THEN_CODE = '''"""A module docstring that says sips, osascript and /Volumes: never a hit."""
import subprocess
CSS = """
body { color: red; }
"""
subprocess.run(["sips", "-Z", "100", "a.jpg"])
x = 1


def f():
    """A function docstring; caffeinate here is only words."""
    return 2
'''
SELF_TESTS = [   # (made-up script, the short names it must give, in any order; an empty set means clean)
    (_CSS_THEN_CODE, {"sips"}),
    ('T = """\n<svg></svg>\n"""\nimport subprocess\nsubprocess.run(["osascript", "-e", "x"])\n', {"osascript"}),
    ("x = 1  # sips is only mentioned in a comment\n# subprocess.run(['sips'])\n", set()),
    ('import subprocess\nsubprocess.run(["sips", "a"])  # pc-ok: only a Mac gets here\n', set()),
    ('import subprocess\ns = "a  #b"; subprocess.run(["sips", "a"])\n', {"sips"}),
    ('import subprocess\nsubprocess.run(["/usr/bin/caffeinate", "-i", "x"])\n', {"caffeinate"}),
    ('cmd = "caffeinate -i python3 night.py"\n', {"caffeinate"}),
    ('import os\nname = "x"\np = f"/Volumes/{name}"\nq = os.listdir("/Volumes")\n', {"/Volumes"}),
    ('from pathlib import Path\np = Path("/Volumes/EOS_DIGITAL")\nok = str(p).startswith("/Volumes")\n', {"/Volumes"}),
    ('import subprocess\nsubprocess.run(["open", "-a", "CapCut"])\n', {"Mac open"}),
    ('import os\nos.kill(1234, 0)\nos.waitpid(1, os.WNOHANG)\n', {"os.kill(pid, 0)", "WNOHANG"}),
    ('import subprocess, signal\nsubprocess.Popen(["x"], preexec_fn=None)\nsignal.SIGKILL\n', {"preexec_fn", "Mac-only signal"}),
    ("import termios\nfrom pwd import getpwuid\n", {"Mac-only module"}),
    ('import os\nos.killpg(1, 15)\n', {"Mac-only os call"}),
    ('s = "Say it however you\'d say it, then say go."\nt = "defaults to the drive"\n', set()),
    ('import subprocess\nsubprocess.run(["say", "done"])\n', {"say"}),
    ("JS = \"note.className = 'say'; el.dataset.mode = 'defaults';\"\n", set()),
    ('from pathlib import Path\nPath("a").read_text()\nPath("a").read_text(errors="replace")\n', {ENCODING}),
    ('from pathlib import Path\nPath("a").write_text("x")\n', {ENCODING}),
    ('open("a", "w").write("x")\nopen("b", "a")\nopen("c")\n', {ENCODING}),
    ('import subprocess\nsubprocess.run(["x"], capture_output=True, universal_newlines=True)\n', {ENCODING}),
    ('import subprocess\nsubprocess.run(["x"], capture_output=True, text=True, encoding="utf-8")\n'
     'from pathlib import Path\nPath("a").read_text(encoding="utf-8")\nPath("a").write_text("x", encoding="utf-8")\n'
     'open("a", "rb")\nopen("a", "w", encoding="utf-8")\nPath("a").open("rb")\nPath("a").open("w", encoding="utf-8")\n'
     'import webbrowser, wave\nwebbrowser.open("http://x")\nwave.open("a.wav", "rb")\n', set()),
    ('from pathlib import Path\nwith Path("a").open("w") as fh:\n    pass\n', {ENCODING}),
    # Nov 6, test review: each of these got through before (or, the last ones, was stopped when it shouldn't be)
    ("import os, fcntl\n", {"fcntl"}),
    ("import sys\nfrom fcntl import flock as f\nimport importlib\nm = importlib.import_module('termios')\n",
     {"fcntl", "Mac-only module"}),
    ('import os\npid = "12"\nos.kill(int(pid), 0)\n', {"os.kill(pid, 0)"}),
    ('import subprocess\nsubprocess.run([\n    "open", "-a", "CapCut"])\n', {"Mac open"}),
    ('import subprocess\nsubprocess.run(("open", "-R", "x"))\n', {"Mac open"}),
    ('import os\nos.system("open -a CapCut")\n', {"Mac open"}),
    ('import subprocess\np = "x"\nsubprocess.run(f"open {p}", shell=True)\ncmd = ("open", p)\n', {"Mac open"}),
    ('import subprocess\nsubprocess.run([\n    "open", "x"])  # pc-ok: only a Mac gets here\n', set()),
    ('from datetime import date\nd = date.today()\nx = f"{d:%B %-d}"\n', {"%-d"}),
    ('from datetime import date\nx = "{:%-d}".format(date.today())\n', {"%-d"}),
    ('from datetime import date\nx = date.today().strftime(\n    "%B %-d")\n', {"%-d"}),
    ('import time\nx = time.strftime("%b " + "%-d")\n', {"%-d"}),
    ('import this_computer as tc\nfrom datetime import date\nx = tc.strftime(date.today(), "%-d")\n'
     'from this_computer import strftime\ny = strftime(date.today(), "%B %-d")\n', set()),
    ('FMT = "%b %-d %Y"\nOFFERED = [{"date_format": "%B %-d, %Y"}]\n', set()),       # data, as studio_file.py keeps it
    ('from pathlib import Path\nwith Path("a").open() as fh:\n    pass\n', {ENCODING}),
    ('m = "w"\nwith open("a", m) as fh:\n    pass\n', {ENCODING}),
    ('import os, tarfile\nfd = os.open("a", os.O_RDONLY)\nt = tarfile.open(fileobj=None)\n', set()),
    ('import subprocess\nsubprocess.run(["killall", "CapCut"])\nsubprocess.run(["pkill", "-x", "x"])\n'
     'subprocess.run(["lsof", "x"])\nsubprocess.run(["launchctl", "list"])\nsubprocess.run(["pmset", "-g"])\n',
     {"killall", "pkill", "lsof", "launchctl", "pmset"}),
    ('import subprocess\nsubprocess.run(["pgrep", "-x", "CapCut"])\n', {"pgrep"}),
    ('import subprocess\nsubprocess.run(["sips", "a"])  # not pc-ok yet\n', {"sips"}),
    ('STATES = ("open", "closed")\ns = "x"\nok = s in ("open", "done")\nd = {"open": 1}\n', set()),
    # Nov 6 follow-up: a page of this computer's own asked for through urllib's own opener, which takes a proxy
    ('import urllib.request\nurllib.request.urlopen("http://127.0.0.1:8790/home", timeout=1).read(1)\n', {"urlopen"}),
    ('import urllib.request\nr = urllib.request.urlopen(\n    "http://127.0.0.1/", timeout=1)\nfrom urllib.request import urlopen\n'
     'y = urlopen("http://127.0.0.1/")\n', {"urlopen"}),
    ('import this_computer\nthis_computer.open_local("http://127.0.0.1:8790/home", timeout=1).read(1)\n'
     '# urllib.request.urlopen(u) is only mentioned here\n', set()),
    # Nov 6, the designer's join: a child's own session asked for through a dict of options
    ('import os, subprocess\nown = {"creationflags": 0x08000000} if os.name == "nt" else {"start_new_session": True}\n'
     'subprocess.Popen(["x"], **own)\n', {"new session"}),
    ('import this_computer\nthis_computer.popen_detached(["x"])  # a Mac: start_new_session, as before\n', set()),
]


def self_test():
    """Plain words for each made-up script the check reads wrong; empty when it reads them all right."""
    wrong = []
    for i, (text, want) in enumerate(SELF_TESTS, 1):
        try:
            got = {short for _, short, _ in problems(text, rel="studio-manager/scripts/made_up.py", name="made_up.py")}
        except SyntaxError as e:
            wrong.append(f"made-up script {i} could not be read ({e})")
            continue
        if got != want:
            wrong.append(f"made-up script {i}: found {sorted(got) or 'nothing'}, should have found {sorted(want) or 'nothing'}")
    return wrong


# ---------------------------------------------------------------- the check

def main():
    stops, notes, waiting, known_seen = [], {}, {}, {}
    for w in self_test():
        stops.append("the check itself reads scripts wrong, so it cannot be trusted: " + w)
    for f in sorted(SKILLS.glob("*/scripts/*.py")):
        rel = f.relative_to(SKILLS).as_posix()
        if f.name == "this_computer.py" or f.name in PARKED:
            continue
        text = f.read_text(encoding="utf-8")
        try:
            found = problems(text, rel, f.name)
            direct = still_direct(text)
        except (SyntaxError, tokenize.TokenError) as e:
            stops.append(f"{f.name}: could not be read as Python ({e})")
            continue
        if f.name in NOT_YET:
            counts = {}
            for _, short, _ in found:
                counts[short] = counts.get(short, 0) + 1
            for t, _ in direct:
                counts[t] = counts.get(t, 0) + 1
            waiting[f.name] = counts
            continue
        for n, short, why in found:
            if (f.name, short) in KNOWN:
                known_seen.setdefault((f.name, short), []).append(n)
                continue
            stops.append(f"{f.name}:{n}: {why}")
        for tool, what in direct:
            notes.setdefault((tool, what), set()).add(f.name)
    for (name, short), (allowed, todo) in sorted(KNOWN.items()):
        lines = known_seen.get((name, short), [])
        at = ", ".join(map(str, lines))
        if len(lines) > allowed:
            stops.append(f"{name}: {len(lines)} lines of the kind '{short}' where {allowed} are known "
                         f"(lines {at}): fix the new one")
        elif len(lines) < allowed:
            print(f"NOTE: {name} has {len(lines)} '{short}' line(s) now and KNOWN says {allowed}: lower the number "
                  "(or take the entry out)")
        else:
            print(f"NOTE: known, still to fix: {name}:{at}: {todo}")
    for (tool, what), files in sorted(notes.items()):
        print(f"NOTE: {tool} ({what}) is still called directly in: {', '.join(sorted(files))}")
    if waiting:
        def said(counts):
            if not counts:
                return ""
            return " (" + "; ".join(f"{k} x{v}" if v > 1 else k for k, v in sorted(counts.items())) + ")"
        print("NOTE: not through the PC pass yet: " + ", ".join(name + said(c) for name, c in sorted(waiting.items())))
    for s in stops:
        print("STOP: " + s)
    print("PC check: " + ("clean." if not stops else f"{len(stops)} to fix."))
    return 1 if stops else 0


if __name__ == "__main__":
    sys.exit(main())
