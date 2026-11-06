#!/usr/bin/env python3
"""Drive a HIDDEN Chrome from a test: a real page, real pointer events, real canvas and fonts.

A test tool only. It is never shipped in the plugin and nothing in the plugin imports it.
Python 3.9, standard library only (it carries its own small websocket client).

HOW A TEST USES IT

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import chrome_drive

    if not chrome_drive.find_chrome():
        print("SKIP  no Chrome on this computer"); return
    with chrome_drive.Chrome(work=scratch_folder, size=(1280, 900)) as c:
        c.open("http://127.0.0.1:8931/design.html?kit=...")
        c.wait_for("document.querySelectorAll('.slide').length >= 2", 10)
        c.drag("#pool .pt[data-n='7']", "#row", steps=12)        # genuine pointerdown / move / up
        order = c.js("Array.from(document.querySelectorAll('#row .rt')).map(t => +t.dataset.n)")
        assert not c.page_errors(), c.page_errors()

    python3 tests/chrome_drive.py --selftest --port 8930 --work /private/tmp/somewhere
        proves the driver on the reel picker (PASS / FAIL lines, exit 1 on a failure, SKIP and exit 0
        with no Chrome). --work must be under /private/tmp; everything it makes goes in a new folder there.
        It uses --port for the Assistant's page server and --port + 8 for a small page of its own.

MEASURED (Nov 6 2026, Chrome 156 on an Apple-silicon Mac, Python 3.9 and 3.12)

    starting the hidden Chrome until it takes commands    0.3 to 0.4 s
    stopping it and removing its profile                  0.1 s
    opening the reel picker (18 photos) until it is ready 0.08 s
    one pointer event (a press, a move or a release)      17 ms: Chrome handles one per frame
    a drag in 12 steps (14 pointer events)                0.2 s;  in 30 steps 0.5 s;  in 2 steps 0.05 s
    80 drags in a row on the reel picker                  80 landed where they should

THE API (every x, y is in page pixels from the top left of what is showing, like clientX / clientY)

    find_chrome()                    the path of a Chrome (or Chromium / Edge), or None. CHROME_DRIVE_CHROME
                                     in the environment points at another one.
    Chrome(work, size=(1280, 900))   .start() / .stop(), or use it in a "with". Always headless, always a
                                     throwaway profile in a new folder under work, removed again on stop.
                                     Chrome picks a free debugging port itself (c.debug_port says which).
    c.open(url)                      go there and wait for the page's load event (CannotOpen if it can't be reached)
    c.reload()
    c.js(expr, await_promise=True)   run JavaScript, get its value back as JSON (a promise is waited for)
    c.wait_for(js_cond, seconds=10)  ask again and again, with real sleeps here in Python, until it is true;
                                     returns the value, or raises Timeout saying what it last saw
    wait_until(fn, seconds=10)       the same for a Python function (a file on disk, say)
    c.rect(selector, nth=0)          {x, y, w, h, cx, cy, right, bottom} from getBoundingClientRect, or None
    c.count(selector) / c.text(selector)   how many match; the text of one
    c.point(target, fx=.5, fy=.5)    a selector's point (brought to the middle of the window first when it is off
                                     screen or under something) or an (x, y) as given
    c.mouse_move(x, y) / c.mouse_press() / c.mouse_release()      the raw pieces; alt= shift= meta= ctrl=
    c.drag(a, b, steps=12, alt=False, shift=False, release=True)  press at a, move in steps, let go at b
    c.click(target) / c.double_click(target) / c.wheel(target, dy, dx=0)
    c.key("Escape") / c.key("Meta+Z") / c.key("Shift+ArrowLeft") / c.key("Mod+Z")   Mod = Cmd on a Mac, Ctrl on a PC
    c.key_down("Shift") ... c.key_up("Shift")
    c.type_text("Hello")             real key events a character at a time
    c.tap(target) / c.touch_drag(a, b)                             a finger instead of a mouse
    c.set_value(selector, value)     a colour box, a list or a slider given a value, with 'input' and 'change' sent
    c.screenshot(name_or_path)       a PNG, only ever inside the work folder; returns its path (full=True: whole page)
    c.pixel(x, y)                    the colour showing at a point, (r, g, b)
    c.page_errors()                  uncaught exceptions and console.error lines since the last clear_errors()
    c.console / c.requests / c.failed / c.dialogs / c.log          what the page logged, asked for (with each
                                     answer's status), failed to get, put up as a box; and Chrome's own log
                                     (a 404 is a line there, not a failure)
    c.outside_requests()             every address asked for that is not this computer
    c.set_offline(True)              no INTERNET: every address but this computer fails; 127.0.0.1 still answers
    c.set_offline(True, everything=True)   Chrome's own offline switch: 127.0.0.1 fails too, navigator.onLine false
    c.block_urls(["*fonts.googleapis.com*"])  those addresses fail; block_urls([]) lifts it
    c.phone(390, 844) / c.desktop()  a phone's width and back
    c.hold_timers()                  call BEFORE open(): the page's setTimeout / setInterval / requestAnimationFrame
                                     are kept waiting until c.run_timers(); c.free_timers() ends it from the
                                     next open(); see the gotchas

GOTCHAS (each one met while building this)

  * "--dump-dom --virtual-time-budget" returns before a page's fetches have finished. Nothing here uses it;
    everything goes through the remote-debugging websocket.
  * Chrome's own offline switch (Network.emulateNetworkConditions) cuts off 127.0.0.1 as well, so a page
    served by the Assistant could not even save. "No internet" for our pages is set_offline(True), which
    stops each request on its way out and fails the ones that are not for this computer.
  * A hidden Chrome treats its page as in front: timers run on time. The Claude app's pane does not promise
    that (a page that is not in front has its timers slowed to a second or more). To prove that nothing waits
    on a timer, use hold_timers(): the page then runs with every timer and animation frame kept back, and the
    test decides when they run. fetch() and events are not held. While they are held, do not wait in js()
    for a promise that needs a timer: it would never come.
  * Chrome answers a wheel command before the page has had the wheel event (a press, a move and a key are
    handled by the time their call returns). wheel() therefore watches for the event in the page and waits.
  * A hidden Chrome cannot open the colour box of <input type=color>, a file chooser, or a list's own menu.
    Use set_value() for the first and the last.
  * CHROME_DRIVE_CHROME pointing at something that is not there counts as "no Chrome" (it does not fall back).
  * A press is refused (Covered) when something else lies on top of the point. point() first brings a selector
    that is off screen, or under a bar fixed to the window's edge, to the middle of the window; only when it
    is still covered after that (a thing fixed in place under another) is the press refused. check=False
    presses anyway.
  * So a press on a selector can SCROLL THE PAGE. Measure anything else (rect()) after c.point(selector), not before.
  * A whole-page screenshot is as wide as the page's content, which is the window less its scrollbar (1265 for
    a 1280 window that scrolls). Taking one makes Chrome drop the scrollbar from the layout for good, so
    screenshot(full=True) sets the window's size afresh afterwards (the page may see a resize event).
  * At a phone's width, innerWidth is LARGER than asked when the page is wider than the screen (a phone
    zooms out to fit): innerWidth equal to the width asked means no sideways scroll.
  * An (x, y) is used as given and is not scrolled to. Take it from rect() AFTER any scrolling.
  * js() returns JSON: an element comes back as {}. Return numbers, strings, lists.
  * mouse_move with a button held needs buttons set or the page sees "the button was let go"; drag() does that.
  * Keys with Cmd / Ctrl / Alt held carry no text, as on a real keyboard. On a Mac the usual editing keys
    (Cmd+A, Z, Shift+Z, C, X, V) also carry Chrome's editing command, so a text box behaves as it does by hand.
  * Never give Chrome the person's own profile. This always makes a new one and removes only that.
  * If the test is killed outright (kill -9), a small watcher ends the hidden Chrome anyway (Mac and Linux).
    On Windows the hidden Chrome and every helper it starts are put in a job of Windows' own (_WinJob) that
    Windows ends when the test's process ends, however it ends. The throwaway profile folder is then left in
    the work folder.
  * On Windows (Nov 6; written from Microsoft's documentation, unproven until GitHub's Windows machine runs
    tests/pc_design_page.py): Chrome is found in Program Files (then Chromium, then Edge); stopping it ends the
    whole tree of helpers (the job, then "taskkill /T /F", then the process itself), because a helper that
    lives a moment longer still has files of the throwaway profile open and Windows will not remove a file
    that is open; the profile's removal is tried for up to 15 seconds there, and a profile that still cannot
    be removed is left in the work folder (c.profile_left says so) and never fails a test by itself.
"""
import argparse
import atexit
import base64
import fnmatch
import hashlib
import http.client
import json
import os
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import quote, urlsplit

ENV_CHROME = "CHROME_DRIVE_CHROME"
MAC = sys.platform == "darwin"
WINDOWS = os.name == "nt"


class NoChrome(Exception):
    """There is no Chrome on this computer: a test should SKIP, not fail."""


class ChromeGone(Exception):
    """The hidden Chrome stopped, or stopped answering."""


class CDPError(Exception):
    """Chrome refused a command."""


class JSError(Exception):
    """The JavaScript given to js() threw."""


class CannotOpen(Exception):
    """The address given to open() could not be reached."""


class Timeout(Exception):
    """wait_for / wait_until ran out of time."""


class Covered(Exception):
    """Something else is on top of the point a press was meant for."""


# ---------------------------------------------------------------- finding Chrome

def chrome_candidates():
    out = []
    if MAC:
        for base in ("/Applications", str(Path.home() / "Applications")):
            out += [base + "/Google Chrome.app/Contents/MacOS/Google Chrome",
                    base + "/Chromium.app/Contents/MacOS/Chromium",
                    base + "/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
                    base + "/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    elif WINDOWS:
        roots = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        for r in [x for x in roots if x]:
            out.append(os.path.join(r, "Google", "Chrome", "Application", "chrome.exe"))
        for r in [x for x in roots if x]:
            out.append(os.path.join(r, "Chromium", "Application", "chrome.exe"))
        for r in [x for x in roots if x]:
            out.append(os.path.join(r, "Microsoft", "Edge", "Application", "msedge.exe"))
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
            p = shutil.which(name)
            if p:
                out.append(p)
        out += ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium"]
    return out


def find_chrome():
    """The path of a Chrome to run hidden, or None when there is none (so a test can SKIP)."""
    named = os.environ.get(ENV_CHROME)
    if named:
        return named if os.path.isfile(named) else None
    for p in chrome_candidates():
        if os.path.isfile(p):
            return p
    return None


# ---------------------------------------------------------------- a small websocket client

class WebSocketError(Exception):
    pass


class WebSocketClosed(WebSocketError):
    pass


WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _mask(data, key):
    n = len(data)
    if not n:
        return b""
    k = (key * (n // 4 + 1))[:n]
    return (int.from_bytes(data, "big") ^ int.from_bytes(k, "big")).to_bytes(n, "big")


class WebSocket:
    """A websocket client, enough for the DevTools protocol: the handshake, masked frames out, frames of any
    length in, a message sent in several pieces put back together, ping answered with pong, close answered."""

    def __init__(self, host, port, path, timeout=10):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._in = bytearray()
        self._send_lock = threading.Lock()
        self.closed = False
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        # No Origin header: Chrome turns away a debugging connection that names one.
        ask = ("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n") % (path, host, port, key)
        self.sock.sendall(ask.encode("ascii"))
        while b"\r\n\r\n" not in self._in:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise WebSocketError("the connection closed during the handshake")
            self._in += chunk
            if len(self._in) > 65536:
                raise WebSocketError("the handshake answer is too long")
        head, rest = bytes(self._in).split(b"\r\n\r\n", 1)
        self._in = bytearray(rest)
        lines = head.decode("latin-1").split("\r\n")
        if not re.match(r"HTTP/1\.1 101\b", lines[0]):
            raise WebSocketError("not a websocket: " + lines[0])
        got = {}
        for ln in lines[1:]:
            if ":" in ln:
                a, b = ln.split(":", 1)
                got[a.strip().lower()] = b.strip()
        want = base64.b64encode(hashlib.sha1((key + WS_GUID).encode("ascii")).digest()).decode("ascii")
        if got.get("sec-websocket-accept") != want:
            raise WebSocketError("the handshake answer does not match the key sent")
        self.sock.settimeout(None)
        self.pongs = 0

    def _frame(self, opcode, payload, fin=True):
        n = len(payload)
        head = bytes([(0x80 if fin else 0) | opcode])
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        key = os.urandom(4)
        return head + key + _mask(payload, key)

    def send(self, text, pieces=1):
        """Send one text message (always masked, as a client must). pieces > 1 sends it in that many frames."""
        data = text.encode("utf-8")
        if pieces <= 1 or len(data) < pieces:
            out = self._frame(1, data)
        else:
            step = -(-len(data) // pieces)
            parts = [data[i:i + step] for i in range(0, len(data), step)]
            out = b"".join(self._frame(1 if i == 0 else 0, p, fin=(i == len(parts) - 1)) for i, p in enumerate(parts))
        with self._send_lock:
            self.sock.sendall(out)

    def _control(self, opcode, payload=b""):
        with self._send_lock:
            self.sock.sendall(self._frame(opcode, payload[:125]))

    def ping(self, payload=b""):
        self._control(9, payload)

    def _read(self, n):
        while len(self._in) < n:
            chunk = self.sock.recv(max(65536, n - len(self._in)))
            if not chunk:
                raise WebSocketClosed("the connection closed")
            self._in += chunk
        out = bytes(self._in[:n])
        del self._in[:n]
        return out

    def recv(self):
        """The next whole message as text (or bytes for a binary one). Raises WebSocketClosed at the end."""
        kind, parts = None, []
        while True:
            b0, b1 = self._read(2)
            fin, opcode, n = bool(b0 & 0x80), b0 & 0x0F, b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            key = self._read(4) if b1 & 0x80 else None
            data = self._read(n)
            if key:
                data = _mask(data, key)
            if opcode == 9:                                 # ping: answer, carry on
                self._control(10, data)
                continue
            if opcode == 10:                                # pong
                self.pongs += 1
                continue
            if opcode == 8:                                 # close
                self.closed = True
                try:
                    self._control(8, data[:2])
                except OSError:
                    pass
                raise WebSocketClosed("the other side closed the connection")
            if opcode in (1, 2):
                if kind is not None:
                    raise WebSocketError("a new message began inside another")
                kind = opcode
            elif opcode == 0:
                if kind is None:
                    raise WebSocketError("a continuation with nothing to continue")
            else:
                raise WebSocketError("unknown frame type %d" % opcode)
            parts.append(data)
            if fin:
                whole = b"".join(parts)
                return whole.decode("utf-8") if kind == 1 else whole

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self._control(8, struct.pack(">H", 1000))
            except OSError:
                pass
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


# ---------------------------------------------------------------- keys

MODS = {"alt": 1, "option": 1, "ctrl": 2, "control": 2, "meta": 4, "cmd": 4, "command": 4, "shift": 8}
MOD_KEYS = {1: ("Alt", "AltLeft", 18), 2: ("Control", "ControlLeft", 17), 4: ("Meta", "MetaLeft", 91), 8: ("Shift", "ShiftLeft", 16)}
NAMED_KEYS = {
    "Enter": ("Enter", 13, "\r"), "Tab": ("Tab", 9, ""), "Escape": ("Escape", 27, ""), "Backspace": ("Backspace", 8, ""),
    "Delete": ("Delete", 46, ""), "ArrowLeft": ("ArrowLeft", 37, ""), "ArrowUp": ("ArrowUp", 38, ""),
    "ArrowRight": ("ArrowRight", 39, ""), "ArrowDown": ("ArrowDown", 40, ""), "Home": ("Home", 36, ""),
    "End": ("End", 35, ""), "PageUp": ("PageUp", 33, ""), "PageDown": ("PageDown", 34, ""), "Space": ("Space", 32, " "),
    "Shift": ("ShiftLeft", 16, ""), "Control": ("ControlLeft", 17, ""), "Alt": ("AltLeft", 18, ""), "Meta": ("MetaLeft", 91, ""),
}
ALIASES = {"esc": "Escape", "return": "Enter", "del": "Delete", "left": "ArrowLeft", "right": "ArrowRight", "up": "ArrowUp",
           "down": "ArrowDown", " ": "Space", "spacebar": "Space"}
PUNCT = {"-": ("Minus", 189), "=": ("Equal", 187), "[": ("BracketLeft", 219), "]": ("BracketRight", 221), "\\": ("Backslash", 220),
         ";": ("Semicolon", 186), "'": ("Quote", 222), ",": ("Comma", 188), ".": ("Period", 190), "/": ("Slash", 191), "`": ("Backquote", 192)}
SHIFTED = {"_": "-", "+": "=", "{": "[", "}": "]", "|": "\\", ":": ";", '"': "'", "<": ",", ">": ".", "?": "/", "~": "`",
           "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6", "&": "7", "*": "8", "(": "9", ")": "0"}
MAC_COMMANDS = {(4, "a"): "selectAll", (4, "z"): "undo", (12, "z"): "redo", (4, "c"): "copy", (4, "x"): "cut", (4, "v"): "paste"}


def key_parts(name, mods=0):
    """(key, code, windows key number, text) for one key name or one character."""
    name = ALIASES.get(name.lower(), name) if len(name) != 1 or name == " " else name
    for k in NAMED_KEYS:
        if k.lower() == name.lower():
            code, vk, text = NAMED_KEYS[k]
            return (" " if k == "Space" else k), code, vk, text
    m = re.match(r"^[Ff](\d{1,2})$", name)
    if m and 1 <= int(m.group(1)) <= 12:
        return "F" + m.group(1), "F" + m.group(1), 111 + int(m.group(1)), ""
    if len(name) == 1:
        ch = name
        if ch.isalpha() and ch.isascii():
            up = bool(mods & 8) or ch.isupper()
            return (ch.upper() if up else ch.lower()), "Key" + ch.upper(), ord(ch.upper()), (ch.upper() if up else ch.lower())
        if ch.isdigit():
            return ch, "Digit" + ch, ord(ch), ch
        if ch in PUNCT:
            return ch, PUNCT[ch][0], PUNCT[ch][1], ch
        if ch in SHIFTED:
            base = SHIFTED[ch]
            code, vk = (("Digit" + base, ord(base)) if base.isdigit() else PUNCT[base])
            return ch, code, vk, ch
        return ch, "", 0, ch
    raise ValueError("not a key this driver knows: %r" % name)


def parse_combo(combo):
    """'Meta+Z' -> (modifier bits, 'Z'). 'Mod' is Cmd on a Mac and Ctrl elsewhere. A lone '+' is the plus key."""
    if combo == "+":
        parts = ["+"]
    elif combo.endswith("++"):
        parts = combo[:-2].split("+") + ["+"]
    else:
        parts = combo.split("+")
    mods = 0
    for p in parts[:-1]:
        low = p.strip().lower()
        if low == "mod":
            mods |= 4 if MAC else 2
        elif low in MODS:
            mods |= MODS[low]
        else:
            raise ValueError("not a modifier key: %r in %r" % (p, combo))
    name = parts[-1] if parts[-1] == " " else parts[-1].strip()
    if len(name) == 1 and name.isalpha() and mods:
        name = name.upper() if mods & 8 else name.lower()       # Cmd+Z is "z" to a page, as from a real keyboard
    return mods, name


# ---------------------------------------------------------------- page scripts the driver brings

HOLD_TIMERS_JS = r"""
(function(){
  // The page's timers and animation frames, kept back until the test says go. Put in before any page script.
  if (window.__held) return;
  var q = [], id = 1000000;
  var H = window.__held = {holding: true, ran: 0};
  var real = {st: window.setTimeout, si: window.setInterval, raf: window.requestAnimationFrame,
              ct: window.clearTimeout, ci: window.clearInterval, caf: window.cancelAnimationFrame};
  function add(kind, fn, ms, args){ id += 1; q.push({id: id, kind: kind, fn: fn, ms: +ms || 0, args: args}); return id; }
  function drop(i){ q = q.filter(function(t){ return t.id !== i; }); }
  window.setTimeout = function(fn, ms){ return add('t', fn, ms, Array.prototype.slice.call(arguments, 2)); };
  window.setInterval = function(fn, ms){ return add('i', fn, ms, Array.prototype.slice.call(arguments, 2)); };
  window.requestAnimationFrame = function(fn){ return add('f', fn, 0, []); };
  window.clearTimeout = function(i){ drop(i); real.ct.call(window, i); };
  window.clearInterval = function(i){ drop(i); real.ci.call(window, i); };
  window.cancelAnimationFrame = function(i){ drop(i); real.caf.call(window, i); };
  H.waiting = function(){ return q.length; };
  // Run what is waiting now, once each (an interval stays for the next go). Returns how many ran.
  H.run = function(kinds){
    var due = q.filter(function(t){ return !kinds || kinds.indexOf(t.kind) >= 0; }), n = 0;
    q = q.filter(function(t){ return due.indexOf(t) < 0 || t.kind === 'i'; });
    due.forEach(function(t){
      n += 1; H.ran += 1;
      if (typeof t.fn === 'function') t.fn.apply(window, t.kind === 'f' ? [performance.now()] : t.args);
    });
    return n;
  };
})();
"""

POINT_JS = r"""
(function(sel, nth, fx, fy, scroll){
  var e = document.querySelectorAll(sel)[nth];
  if (!e) return null;
  var r, x, y, top, ok;
  function look(){
    r = e.getBoundingClientRect(); x = r.left + r.width * fx; y = r.top + r.height * fy;
    top = document.elementFromPoint(x, y); ok = !!top && (top === e || e.contains(top));
  }
  look();
  // off screen, or under something (a bar fixed to the window's edge): bring it to the middle and look again
  if (scroll && !ok) { e.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'}); look(); }
  var says = top ? top.tagName.toLowerCase() + (top.id ? '#' + top.id : '') + (typeof top.className === 'string' && top.className ? '.' + top.className.trim().split(/\s+/).join('.') : '') : 'nothing (off the page)';
  return {x: x, y: y, ok: ok, top: says, w: r.width, h: r.height};
})
"""

RECT_JS = r"""
(function(sel, nth){
  var e = document.querySelectorAll(sel)[nth];
  if (!e) return null;
  var r = e.getBoundingClientRect();
  return {x: r.left, y: r.top, w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2, right: r.right, bottom: r.bottom};
})
"""


def wait_until(fn, seconds=10, every=0.03, what=""):
    """Call fn again and again (real sleeps) until it returns something true; return that. Raises Timeout."""
    end = time.time() + seconds
    last = None
    while True:
        try:
            last = fn()
        except (OSError, ValueError, KeyError) as e:        # a file half written, not there yet
            last = repr(e)
        else:
            if last:
                return last
        if time.time() >= end:
            raise Timeout("waited %.1f s for %s; last saw %r" % (seconds, what or getattr(fn, "__name__", "it"), last))
        time.sleep(every)


class _WinJob:
    """Windows only: a job of Windows' own that holds the hidden Chrome and every helper it starts from then on.
    end() ends them all at once. The job is set to end its processes when its last handle closes, and this test's
    process holds the only one, so a test that is killed outright takes its Chrome with it. Every step fails
    quietly (no job: stop() still has taskkill and the process itself). Unproven on a real PC."""

    def __init__(self, proc):
        self.handle = self._k32 = None
        if not WINDOWS:
            return
        try:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.CreateJobObjectW.restype = wintypes.HANDLE
            k32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
            k32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD)
            k32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
            k32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
            k32.CloseHandle.argtypes = (wintypes.HANDLE,)

            class Basic(ctypes.Structure):
                _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                            ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                            ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                            ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

            class Counters(ctypes.Structure):
                _fields_ = [(n, ctypes.c_uint64) for n in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                                                           "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

            class Extended(ctypes.Structure):
                _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", Counters), ("ProcessMemoryLimit", ctypes.c_size_t),
                            ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                            ("PeakJobMemoryUsed", ctypes.c_size_t)]

            h = k32.CreateJobObjectW(None, None)
            if not h:
                return
            info = Extended()
            info.BasicLimitInformation.LimitFlags = 0x00002000         # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            ok = (k32.SetInformationJobObject(h, 9, ctypes.byref(info), ctypes.sizeof(info))      # 9: the extended limits
                  and k32.AssignProcessToJobObject(h, wintypes.HANDLE(int(proc._handle))))
            if not ok:
                k32.CloseHandle(h)
                return
            self.handle, self._k32 = h, k32
        except Exception:
            self.handle = None

    def end(self):
        """End every process in the job (the hidden Chrome and its helpers). True when Windows took the order."""
        if self.handle:
            try:
                return bool(self._k32.TerminateJobObject(self.handle, 1))
            except Exception:
                pass
        return False

    def close(self):
        if self.handle:
            try:
                self._k32.CloseHandle(self.handle)
            except Exception:
                pass
            self.handle = None


_LIVE = set()
_LIVE_LOCK = threading.Lock()
_HOOKED = False


def stop_all():
    """Stop every hidden Chrome this process started. Runs by itself when Python exits."""
    with _LIVE_LOCK:
        live = list(_LIVE)
    for c in live:
        try:
            c.stop()
        except Exception:
            pass


def _hook_exit():
    global _HOOKED
    if _HOOKED:
        return
    _HOOKED = True
    atexit.register(stop_all)
    if threading.current_thread() is not threading.main_thread():
        return
    for name in ("SIGTERM", "SIGHUP"):
        num = getattr(signal, name, None)
        if num is None:
            continue
        try:
            if signal.getsignal(num) is signal.SIG_DFL:     # only when the test has no handler of its own
                signal.signal(num, lambda n, f: sys.exit(128 + n))      # an exit runs "finally" and atexit
        except (ValueError, OSError):
            pass


class Chrome:
    """One hidden Chrome with one page. See the top of this file."""

    def __init__(self, work, size=(1280, 900), chrome=None, debug_port=0, scale=1, keep_profile=False, extra_args=()):
        self.work = Path(work).resolve()
        self.size = (int(size[0]), int(size[1]))
        self.scale = scale
        self.path = chrome
        self.debug_port = int(debug_port)
        self.keep_profile = keep_profile
        self.extra_args = list(extra_args)
        self.proc = self.ws = self.profile = self._watch = self._job = None
        self._made_profile = False
        self.profile_left = False           # True when stop() could not remove the throwaway profile (Windows: a file still open)
        self._lock = threading.Lock()
        self._waiting = {}
        self._next = 0
        self._dead = None
        self._loaded = threading.Event()
        self._offline = False
        self._fetch_on = False
        self._blocked = []
        self.blocked_how = None
        self._all_off = False
        self._hold = None
        self._metrics = None
        self._init_scripts = {}
        self._mods_down = 0
        self.mouse = (0.0, 0.0)
        self.buttons = 0
        self.console, self.errors, self.log, self.requests, self.failed, self.dialogs = [], [], [], [], [], []
        self._req = {}
        self.started_in = None
        self.version = ""

    # ---- starting and stopping ----

    def __enter__(self):
        return self.start()

    def __exit__(self, *a):
        self.stop()

    def start(self):
        t0 = time.time()
        path = self.path or find_chrome()
        if not path or not os.path.isfile(path):
            raise NoChrome("No Chrome found. Set %s to point at one." % ENV_CHROME)
        self.path = path
        self.work.mkdir(parents=True, exist_ok=True)
        self.profile = Path(tempfile.mkdtemp(prefix="chrome-profile-", dir=str(self.work)))    # new and empty: never a real profile
        self._made_profile = True
        (self.profile / "made-by-chrome_drive.txt").write_text("A throwaway Chrome profile made by tests/chrome_drive.py. Safe to remove.\n", encoding="utf-8")
        args = [path, "--headless=new", "--user-data-dir=" + str(self.profile),
                "--remote-debugging-port=%d" % self.debug_port, "--remote-debugging-address=127.0.0.1",
                "--no-first-run", "--no-default-browser-check", "--window-size=%d,%d" % self.size,
                "--disable-extensions", "--disable-component-update", "--disable-background-networking", "--disable-sync",
                "--disable-default-apps", "--disable-search-engine-choice-screen", "--mute-audio",
                "--use-mock-keychain", "--password-store=basic",       # never ask the Mac's keychain for anything
                "--disable-features=Translate,MediaRouter,OptimizationHints,DialMediaRouteProvider",
                "--force-device-scale-factor=%s" % self.scale]
        if not WINDOWS and hasattr(os, "geteuid") and os.geteuid() == 0:
            args.append("--no-sandbox")                               # a test machine running as root (some Linux checks)
        if os.environ.get("CHROME_DRIVE_NO_SANDBOX") == "1":
            args.append("--no-sandbox")
        args += self.extra_args + ["about:blank"]
        self._logfile = open(self.work / (self.profile.name + ".log"), "wb")
        kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": self._logfile}
        if WINDOWS:
            kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            kw["start_new_session"] = True                            # its own group, so the whole of it can be ended
        _hook_exit()
        self.proc = subprocess.Popen(args, **kw)
        self._job = _WinJob(self.proc) if WINDOWS else None           # Windows: the whole tree in one job, from the start
        with _LIVE_LOCK:
            _LIVE.add(self)
        try:
            self._start_watcher()
            port = self._find_port()
            self.debug_port = port
            target = self._page_target(port)
            u = urlsplit(target["webSocketDebuggerUrl"])
            self.ws = WebSocket("127.0.0.1", port, u.path)
            self._thread = threading.Thread(target=self._reader, name="chrome_drive reader", daemon=True)
            self._thread.start()
            for domain in ("Page", "Runtime", "Log", "Network"):
                self.cdp(domain + ".enable")
            self.desktop()
            self.cdp("Emulation.setFocusEmulationEnabled", {"enabled": True})
        except BaseException:
            self.stop()
            raise
        self.started_in = time.time() - t0
        return self

    def _start_watcher(self):
        # If this Python is killed outright, its end of the pipe closes, "cat" ends, and the hidden Chrome's
        # whole group is ended. A normal stop() ends the watcher first, so it never fires at a stranger.
        if WINDOWS or not os.path.exists("/bin/sh"):
            return
        g = self.proc.pid
        script = "cat >/dev/null; kill -TERM -- -%d 2>/dev/null; sleep 2; kill -KILL -- -%d 2>/dev/null" % (g, g)
        try:
            self._watch = subprocess.Popen(["/bin/sh", "-c", script], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            self._watch = None

    def _find_port(self):
        f = self.profile / "DevToolsActivePort"
        end = time.time() + 40
        while time.time() < end:
            if self.proc.poll() is not None:
                raise ChromeGone("Chrome stopped as it started (exit %s). Its own words are in %s" % (self.proc.returncode, self._logfile.name))
            try:
                first = f.read_text(encoding="utf-8").split("\n")[0].strip()
                if first.isdigit():
                    return int(first)
            except OSError:
                pass
            time.sleep(0.01)
        raise ChromeGone("Chrome did not open its debugging port in 40 s. Its own words are in %s" % self._logfile.name)

    def _page_target(self, port):
        end = time.time() + 20
        last = None
        while time.time() < end:
            try:
                c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                c.request("GET", "/json/list")
                r = c.getresponse()
                pages = [t for t in json.loads(r.read().decode("utf-8")) if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
                c.request("GET", "/json/version")
                self.version = json.loads(c.getresponse().read().decode("utf-8")).get("Browser", "")
                c.close()
                if pages:
                    return pages[0]
            except (OSError, ValueError, http.client.HTTPException) as e:
                last = e
            time.sleep(0.02)
        raise ChromeGone("Chrome gave no page to drive (%r)" % (last,))

    def stop(self):
        """End the hidden Chrome and remove its throwaway profile. Safe to call twice."""
        with _LIVE_LOCK:
            _LIVE.discard(self)
        proc, self.proc = self.proc, None
        watch, self._watch = self._watch, None
        if watch is not None:
            try:
                watch.kill()
                watch.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                watch.stdin.close()
            except OSError:
                pass
        if proc is not None:
            if proc.poll() is None and self.ws is not None and self._dead is None:
                try:
                    self._send("Browser.close", {})                   # the polite way first
                    proc.wait(timeout=4)
                except (OSError, WebSocketError, subprocess.TimeoutExpired, ChromeGone):
                    pass
            if proc.poll() is None:
                self._end_group(proc, signal.SIGTERM)
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    self._end_group(proc, getattr(signal, "SIGKILL", signal.SIGTERM))
                    try:
                        proc.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        pass
            elif not WINDOWS:
                self._end_group(proc, signal.SIGTERM)                 # helpers that outlived the main process
            elif self._job is not None:
                self._job.end()                                       # Windows: the same, through the job
        job, self._job = self._job, None
        if job is not None:
            job.close()
        if self.ws is not None:
            self.ws.close()
            self.ws = None
        self._dead = self._dead or ChromeGone("this Chrome was stopped")
        self._wake_all()
        lf = getattr(self, "_logfile", None)
        if lf is not None and not lf.closed:
            lf.close()
        if self.profile is not None and self._made_profile and not self.keep_profile:
            self._remove_profile()

    def _end_group(self, proc, sig):
        try:
            if WINDOWS:
                # The whole tree, not only the first process: the job when there is one, then Windows' own
                # "taskkill /T /F" (the first process and every process started from it), then the process itself.
                # Windows has no polite signal for a hidden program, so both "signals" end it outright.
                if self._job is not None:
                    self._job.end()
                try:
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                except (OSError, subprocess.SubprocessError):
                    pass
                if proc.poll() is None:
                    proc.kill()
            else:
                os.killpg(proc.pid, sig)
        except (OSError, ProcessLookupError):
            pass

    def _remove_profile(self):
        p = self.profile
        # only ever the folder this object made, inside its work folder, still carrying its own note
        ok = (p.parent == self.work and p.name.startswith("chrome-profile-") and (p / "made-by-chrome_drive.txt").is_file())
        if not ok:
            return
        # helpers may still be letting go of files: two seconds on a Mac, as before; fifteen on Windows, where a
        # file that anything still has open (a helper on its way out, the virus checker) cannot be removed at all
        for _ in range(300 if WINDOWS else 40):
            shutil.rmtree(str(p), ignore_errors=True)
            if not p.exists():
                break
            time.sleep(0.05)
        self.profile_left = p.exists()                                # left in the work folder; never a failure by itself
        self._made_profile = False

    def alive(self):
        return self.proc is not None and self.proc.poll() is None and self._dead is None

    # ---- the protocol ----

    def _reader(self):
        try:
            while True:
                msg = json.loads(self.ws.recv())
                if "id" in msg:
                    with self._lock:
                        slot = self._waiting.pop(msg["id"], None)
                    if slot is not None:
                        slot["msg"] = msg
                        slot["ev"].set()
                else:
                    try:
                        self._event(msg.get("method", ""), msg.get("params") or {})
                    except Exception as e:                            # a fault in here must not end the reader
                        self.log.append({"level": "driver", "text": "event handler: %r" % (e,)})
        except Exception as e:
            self._dead = self._dead or ChromeGone("the connection to Chrome ended (%s)" % (e,))
            self._wake_all()

    def _wake_all(self):
        with self._lock:
            slots = list(self._waiting.values())
            self._waiting.clear()
        for s in slots:
            s["ev"].set()

    def _send(self, method, params=None, slot=None):
        if self._dead is not None or self.ws is None:
            raise self._dead or ChromeGone("Chrome is not running")
        with self._lock:
            self._next += 1
            i = self._next
            if slot is not None:
                self._waiting[i] = slot
        self.ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
        return i

    def cdp(self, method, params=None, timeout=30):
        """One DevTools command; its result. Raises CDPError when Chrome refuses it."""
        slot = {"ev": threading.Event(), "msg": None}
        i = self._send(method, params, slot)
        if not slot["ev"].wait(timeout):
            with self._lock:
                self._waiting.pop(i, None)
            raise ChromeGone("Chrome did not answer %s in %s s" % (method, timeout))
        msg = slot["msg"]
        if msg is None:
            raise self._dead or ChromeGone("Chrome stopped before answering %s" % method)
        if "error" in msg:
            raise CDPError("%s: %s" % (method, msg["error"].get("message", msg["error"])))
        return msg.get("result") or {}

    def _event(self, method, p):
        if method == "Runtime.consoleAPICalled":
            text = " ".join(self._show(a) for a in p.get("args", []))
            rec = {"type": p.get("type"), "text": text}
            self.console.append(rec)
            if p.get("type") in ("error", "assert"):
                self.errors.append({"kind": "console.error", "text": text})
        elif method == "Runtime.exceptionThrown":
            d = p.get("exceptionDetails", {})
            ex = d.get("exception", {})
            text = ex.get("description") or (ex.get("value") if isinstance(ex.get("value"), str) else None) or d.get("text", "")
            self.errors.append({"kind": "exception", "text": text, "where": "%s:%s" % (d.get("url", ""), d.get("lineNumber", ""))})
        elif method == "Log.entryAdded":
            e = p.get("entry", {})
            self.log.append({"level": e.get("level"), "source": e.get("source"), "text": e.get("text"), "url": e.get("url")})
        elif method == "Page.loadEventFired":
            self._loaded.set()
        elif method == "Page.javascriptDialogOpening":
            self.dialogs.append({"type": p.get("type"), "text": p.get("message")})
            self._send("Page.handleJavaScriptDialog", {"accept": True})    # never leave the page stuck behind a box
        elif method == "Network.requestWillBeSent":
            r = p.get("request", {})
            rec = {"url": r.get("url", ""), "method": r.get("method"), "type": p.get("type"), "status": None}
            self._req[p.get("requestId")] = rec
            if not rec["url"].startswith("data:"):
                self.requests.append(rec)
        elif method == "Network.responseReceived":
            rec = self._req.get(p.get("requestId"))
            if rec is not None:
                rec["status"] = p.get("response", {}).get("status")
        elif method == "Network.loadingFailed":
            rec = self._req.get(p.get("requestId")) or {}
            self.failed.append({"url": rec.get("url", ""), "blocked": p.get("blockedReason"),
                                "error": p.get("errorText") or ("blocked (%s)" % p.get("blockedReason") if p.get("blockedReason") else "")})
        elif method == "Fetch.requestPaused":
            url = p.get("request", {}).get("url", "")
            if self._offline and not is_this_computer(url):
                self._send("Fetch.failRequest", {"requestId": p["requestId"], "errorReason": "InternetDisconnected"})
            elif any(fnmatch.fnmatchcase(url, pat) for pat in self._blocked):
                self._send("Fetch.failRequest", {"requestId": p["requestId"], "errorReason": "BlockedByClient"})
            else:
                self._send("Fetch.continueRequest", {"requestId": p["requestId"]})
        elif method == "Inspector.targetCrashed":
            self._dead = ChromeGone("the page crashed")
            self._wake_all()

    @staticmethod
    def _show(a):
        if "value" in a:
            v = a["value"]
            return v if isinstance(v, str) else json.dumps(v)
        return a.get("description") or a.get("unserializableValue") or a.get("type", "")

    # ---- pages and JavaScript ----

    def open(self, url, seconds=30):
        """Go to url and wait for its load event. Raises CannotOpen when the page cannot be reached."""
        self._loaded.clear()
        r = self.cdp("Page.navigate", {"url": url}, timeout=seconds)
        if r.get("errorText"):
            raise CannotOpen("could not open %s: %s" % (url, r["errorText"]))
        if not self._loaded.wait(seconds):
            raise Timeout("%s did not finish loading in %s s" % (url, seconds))
        self.mouse, self.buttons = (0.0, 0.0), 0
        return self

    def reload(self, seconds=30):
        self._loaded.clear()
        self.cdp("Page.reload", {"ignoreCache": True})
        if not self._loaded.wait(seconds):
            raise Timeout("the page did not finish loading again in %s s" % seconds)
        return self

    def js(self, expression, await_promise=True, timeout=30):
        """Run JavaScript in the page; its value, as JSON. A promise is waited for unless await_promise=False."""
        r = self.cdp("Runtime.evaluate", {"expression": expression, "awaitPromise": bool(await_promise),
                                          "returnByValue": True, "userGesture": True}, timeout=timeout)
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            ex = d.get("exception", {})
            raise JSError(ex.get("description") or str(ex.get("value", "")) or d.get("text", "the script threw"))
        res = r.get("result", {})
        if "unserializableValue" in res:
            return {"NaN": float("nan"), "Infinity": float("inf"), "-Infinity": float("-inf"), "-0": -0.0}.get(res["unserializableValue"], res["unserializableValue"])
        return res.get("value")

    def call(self, function_source, *args):
        """Run a JavaScript function (its source) with JSON arguments."""
        return self.js("(%s)(%s)" % (function_source.strip(), ", ".join(json.dumps(a) for a in args)))

    def wait_for(self, js_condition, seconds=10, every=0.03, tell=None):
        """Ask the page again and again (sleeping here, not in the page) until js_condition is true.
        Returns its value. On running out of time raises Timeout with what it last saw (and tell, if given:
        a second expression worth reading in the failure)."""
        end = time.time() + seconds
        last = None
        while True:
            try:
                last = self.js(js_condition)
                if last:
                    return last
            except (JSError, CDPError) as e:                          # between two pages there is nothing to ask
                last = "(%s)" % e
            if time.time() >= end:
                extra = ""
                if tell:
                    try:
                        extra = "; %s = %r" % (tell, self.js(tell))
                    except Exception as e:
                        extra = "; %s threw %s" % (tell, e)
                raise Timeout("waited %.1f s for: %s; last saw %r%s" % (seconds, js_condition, last, extra))
            time.sleep(every)

    def init_script(self, source):
        """JavaScript to run in every page opened from now on, before the page's own scripts. Returns a handle."""
        ident = self.cdp("Page.addScriptToEvaluateOnNewDocument", {"source": source})["identifier"]
        self._init_scripts[ident] = source
        return ident

    def drop_init_script(self, ident):
        self.cdp("Page.removeScriptToEvaluateOnNewDocument", {"identifier": ident})
        self._init_scripts.pop(ident, None)

    def hold_timers(self):
        """From the next open(): the page's setTimeout, setInterval and requestAnimationFrame wait for run_timers()."""
        if self._hold is None:
            self._hold = self.init_script(HOLD_TIMERS_JS)
        return self

    def free_timers(self):
        """Stop holding timers, from the next open()."""
        if self._hold is not None:
            self.drop_init_script(self._hold)
            self._hold = None
        return self

    def run_timers(self, rounds=1, kinds=None):
        """Run what the held page has waiting (kinds: 't' timeouts, 'i' intervals, 'f' frames; all by default).
        Returns how many ran. A timer set by a timer waits for the next round."""
        n = 0
        for _ in range(rounds):
            n += self.js("window.__held ? window.__held.run(%s) : 0" % json.dumps(kinds)) or 0
        return n

    def timers_waiting(self):
        return self.js("window.__held ? window.__held.waiting() : null")

    # ---- where things are ----

    def rect(self, selector, nth=0):
        """getBoundingClientRect of the nth match: {x, y, w, h, cx, cy, right, bottom}, or None if there is none."""
        return self.call(RECT_JS, selector, nth)

    def count(self, selector):
        return self.js("document.querySelectorAll(%s).length" % json.dumps(selector))

    def text(self, selector, nth=0):
        return self.js("(function(e){ return e ? e.textContent : null; })(document.querySelectorAll(%s)[%d])" % (json.dumps(selector), nth))

    def point(self, target, fx=0.5, fy=0.5, nth=0, check=True, scroll=True):
        """(x, y) for a press. target is a selector (its middle, or the fraction fx, fy of its box; brought to
        the middle of the window first when it is off screen or under something) or an (x, y) used as it is."""
        if not isinstance(target, str):
            return float(target[0]), float(target[1])
        p = self.call(POINT_JS, target, nth, fx, fy, scroll)
        if p is None:
            raise LookupError("nothing on the page matches %r" % target)
        if check and not p["ok"]:
            raise Covered("%r is not what a press at (%.0f, %.0f) would reach: %s is there" % (target, p["x"], p["y"], p["top"]))
        return p["x"], p["y"]

    # ---- the mouse ----

    @staticmethod
    def _bits(alt=False, ctrl=False, meta=False, shift=False):
        return (1 if alt else 0) | (2 if ctrl else 0) | (4 if meta else 0) | (8 if shift else 0)

    def _mouse(self, kind, x, y, button="none", count=0, mods=0, **more):
        p = {"type": kind, "x": x, "y": y, "button": button, "buttons": self.buttons, "clickCount": count,
             "modifiers": mods | self._mods_down, "pointerType": "mouse"}
        p.update(more)
        self.cdp("Input.dispatchMouseEvent", p)

    def mouse_move(self, x, y, **mods):
        """Move the pointer. While a button is held (mouse_press), the page sees that button held."""
        self.mouse = (float(x), float(y))
        self._mouse("mouseMoved", self.mouse[0], self.mouse[1], "left" if self.buttons & 1 else "none", 0, self._bits(**mods))

    def mouse_press(self, x=None, y=None, count=1, **mods):
        """Press the main button, at the pointer or at (x, y)."""
        if x is not None:
            self.mouse_move(x, y, **mods)
        self.buttons |= 1
        self._mouse("mousePressed", self.mouse[0], self.mouse[1], "left", count, self._bits(**mods))

    def mouse_release(self, x=None, y=None, count=1, **mods):
        """Let the main button go, at the pointer or at (x, y)."""
        if x is not None:
            self.mouse_move(x, y, **mods)
        self.buttons &= ~1
        self._mouse("mouseReleased", self.mouse[0], self.mouse[1], "left", count, self._bits(**mods))

    def drag(self, start, end, steps=12, alt=False, shift=False, meta=False, ctrl=False, release=True, check=True):
        """A drag as a hand does it: move to start, press, move to end in steps, let go. start and end are
        selectors or (x, y). release=False leaves the button held (look at the page, then mouse_release()).
        Returns the seconds it took."""
        t0 = time.time()
        m = {"alt": alt, "shift": shift, "meta": meta, "ctrl": ctrl}
        x0, y0 = self.point(start, check=check)
        if isinstance(end, str):
            x1, y1 = self.point(end, check=False, scroll=False)       # never scroll the page between the press and the drop
        else:
            x1, y1 = float(end[0]), float(end[1])
        self.mouse_move(x0, y0, **m)
        self.mouse_press(**m)
        steps = max(1, int(steps))
        for i in range(1, steps + 1):
            self.mouse_move(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps, **m)
        if release:
            self.mouse_release(**m)
        return time.time() - t0

    def click(self, target, count=1, nth=0, fx=0.5, fy=0.5, check=True, **mods):
        x, y = self.point(target, fx, fy, nth=nth, check=check)
        self.mouse_move(x, y, **mods)
        self.mouse_press(count=count, **mods)
        self.mouse_release(count=count, **mods)
        return x, y

    def double_click(self, target, nth=0, check=True, **mods):
        x, y = self.click(target, 1, nth=nth, check=check, **mods)
        self.mouse_press(count=2, **mods)
        self.mouse_release(count=2, **mods)
        return x, y

    def wheel(self, target, dy, dx=0, check=False, **mods):
        """Turn the wheel over a selector or an (x, y). dy > 0 scrolls down."""
        x, y = self.point(target, check=check)
        self.mouse = (x, y)
        # Chrome answers a wheel before the page has had it, so: watch for it in the page and wait for that.
        self.js("window.__wheelSeen = 0; window.addEventListener('wheel', function(){ window.__wheelSeen = 1; }, {capture: true, once: true, passive: true});")
        self._mouse("mouseWheel", x, y, "none", 0, self._bits(**mods), deltaX=dx, deltaY=dy)
        self.wait_for("window.__wheelSeen === 1", 5)

    # ---- a finger ----

    def _touch(self, kind, pts):
        self.cdp("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y, "id": 1} for x, y in pts], "modifiers": self._mods_down})

    def tap(self, target, nth=0, check=True):
        x, y = self.point(target, nth=nth, check=check)
        self._touch("touchStart", [(x, y)])
        self._touch("touchEnd", [])
        return x, y

    def touch_drag(self, start, end, steps=12, check=True):
        x0, y0 = self.point(start, check=check)
        x1, y1 = self.point(end, check=False, scroll=False) if isinstance(end, str) else (float(end[0]), float(end[1]))
        self._touch("touchStart", [(x0, y0)])
        for i in range(1, max(1, steps) + 1):
            self._touch("touchMove", [(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)])
        self._touch("touchEnd", [])

    # ---- the keyboard ----

    def _key(self, kind, key, code, vk, text, mods, commands=None):
        p = {"type": kind, "key": key, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk, "modifiers": mods}
        if kind != "keyUp" and text:
            p["text"] = text
            p["unmodifiedText"] = text
        if commands and kind != "keyUp":
            p["commands"] = commands
        self.cdp("Input.dispatchKeyEvent", p)

    def key_down(self, name):
        """Hold a key (a modifier stays held for the mouse and the keys that follow, until key_up)."""
        mods = self._mods_down
        key, code, vk, text = key_parts(name, mods)
        bit = {"Alt": 1, "Control": 2, "Meta": 4, "Shift": 8}.get(key, 0)
        self._mods_down |= bit
        plain = bool(text) and not (self._mods_down & 7)
        self._key("keyDown" if plain else "rawKeyDown", key, code, vk, text if plain else "", self._mods_down)

    def key_up(self, name):
        key, code, vk, text = key_parts(name, self._mods_down)
        bit = {"Alt": 1, "Control": 2, "Meta": 4, "Shift": 8}.get(key, 0)
        self._mods_down &= ~bit
        self._key("keyUp", key, code, vk, "", self._mods_down)

    def key(self, combo, times=1):
        """Press and let go: "Escape", "Delete", "ArrowLeft", "a", "Meta+Z", "Shift+ArrowRight", "Mod+Shift+Z"."""
        mods, name = parse_combo(combo)
        for _ in range(times):
            held = self._mods_down
            order = [b for b in (2, 1, 8, 4) if mods & b and not held & b]
            for b in order:
                self.key_down(MOD_KEYS[b][0])
            all_mods = self._mods_down
            key, code, vk, text = key_parts(name, all_mods)
            plain = bool(text) and not (all_mods & 7)
            cmd = MAC_COMMANDS.get((all_mods, key.lower())) if MAC else None
            self._key("keyDown" if plain else "rawKeyDown", key, code, vk, text if plain else "", all_mods, [cmd] if cmd else None)
            self._key("keyUp", key, code, vk, "", all_mods)
            for b in reversed(order):
                self.key_up(MOD_KEYS[b][0])

    def type_text(self, text):
        """Type into whatever has the keyboard: a key down and up per character (a new line is Enter).
        A character no key makes (an accent, an emoji) is put in whole, as a paste would."""
        for ch in text:
            if ch == "\n":
                self.key("Enter")
            elif ch == "\t":
                self.key("Tab")
            elif ord(ch) < 127:
                key, code, vk, t = key_parts(ch, 0)
                m = self._mods_down | (8 if (ch.isupper() or ch in SHIFTED) else 0)
                self._key("keyDown", key, code, vk, ch, m)
                self._key("keyUp", key, code, vk, "", m)
            else:
                self.cdp("Input.insertText", {"text": ch})

    # ---- pictures of the page ----

    def screenshot(self, name="page.png", full=False):
        """A PNG of what is showing (full=True: the whole page), written inside the work folder only."""
        p = Path(name)
        p = (p if p.is_absolute() else self.work / p).resolve()
        if self.work != p and self.work not in p.parents:
            raise ValueError("a screenshot goes inside the work folder %s, not %s" % (self.work, p))
        params = {"format": "png"}
        if full:
            m = self.cdp("Page.getLayoutMetrics")["cssContentSize"]
            params.update({"captureBeyondViewport": True, "clip": {"x": 0, "y": 0, "width": m["width"], "height": m["height"], "scale": 1}})
        data = base64.b64decode(self.cdp("Page.captureScreenshot", params, timeout=60)["data"])
        if full and self._metrics:
            # A whole-page picture leaves Chrome laying the page out with no scrollbar (15 px wider) from then
            # on. Setting the window's size afresh puts it back as it was; the scroll position is kept.
            self.cdp("Emulation.clearDeviceMetricsOverride")
            self.cdp("Emulation.setDeviceMetricsOverride", self._metrics)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def pixel(self, x, y):
        """The colour showing at a point of the window, as (r, g, b): what a person would see there."""
        off = self.js("[window.scrollX, window.scrollY]")
        clip = {"x": float(x) + off[0], "y": float(y) + off[1], "width": 1, "height": 1, "scale": 1 / float(self._metrics["deviceScaleFactor"] if self._metrics else 1)}
        data = base64.b64decode(self.cdp("Page.captureScreenshot", {"format": "png", "clip": clip})["data"])
        return one_pixel(data)

    def set_value(self, selector, value, nth=0):
        """Give a form control a value the way a choice in its own box would (a colour box, a list, a slider,
        which a hidden Chrome cannot open): sets it and sends the page 'input' and 'change'."""
        ok = self.call("""function(sel, nth, v){
            var e = document.querySelectorAll(sel)[nth]; if (!e) return false;
            var proto = e.tagName === 'SELECT' ? HTMLSelectElement.prototype : e.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
            Object.getOwnPropertyDescriptor(proto, 'value').set.call(e, v);
            e.dispatchEvent(new Event('input', {bubbles: true})); e.dispatchEvent(new Event('change', {bubbles: true}));
            return true; }""", selector, nth, value)
        if not ok:
            raise LookupError("nothing on the page matches %r" % selector)

    # ---- what the page said and asked for ----

    def page_errors(self):
        """Uncaught exceptions and console.error lines, as short strings. Empty when the page is clean."""
        return ["%s: %s" % (e["kind"], e["text"]) for e in list(self.errors)]

    def clear_errors(self):
        del self.errors[:], self.console[:], self.log[:], self.failed[:], self.requests[:], self.dialogs[:]

    def outside_requests(self):
        """Every address the page asked for that is not this computer."""
        return [r["url"] for r in list(self.requests) if not is_this_computer(r["url"])]

    # ---- the network ----

    def _fetch_gate(self):
        want = self._offline or bool(self._blocked)
        if want and not self._fetch_on:
            self.cdp("Fetch.enable", {"patterns": [{"urlPattern": "*"}]})
            self._fetch_on = True
        elif not want and self._fetch_on:
            self.cdp("Fetch.disable")
            self._fetch_on = False

    def set_offline(self, on=True, everything=False):
        """on: no internet. Addresses on this computer (127.0.0.1, localhost) still answer, as they do for a
        photographer whose wifi is down. everything=True uses Chrome's own switch instead, which cuts off this
        computer's own addresses too and makes navigator.onLine false."""
        if everything:
            self.cdp("Network.emulateNetworkConditions", {"offline": bool(on), "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1})
            self._all_off = bool(on)
            return self
        if self._all_off and not on:
            self.cdp("Network.emulateNetworkConditions", {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1})
            self._all_off = False
        self._offline = bool(on)
        self._fetch_gate()
        self.cdp("Network.setCacheDisabled", {"cacheDisabled": bool(on) or bool(self._blocked)})    # no answer from memory while "offline"
        return self

    def block_urls(self, patterns):
        """Make these addresses fail ("*" stands for anything): block_urls(["*fonts.googleapis.com*"]).
        An empty list lifts it."""
        patterns = [patterns] if isinstance(patterns, str) else list(patterns)
        self._blocked, self.blocked_how = [], None
        for how, params in (("Network.setBlockedURLs urls", {"urls": patterns}),
                            ("Network.setBlockedURLs urlPatterns", {"urlPatterns": [{"urlPattern": x, "block": True} for x in patterns]})):
            try:
                self.cdp("Network.setBlockedURLs", params)
                self.blocked_how = how
                break
            except CDPError:
                continue
        if self.blocked_how is None:                # a Chrome with neither form: fail them at the gate instead
            self._blocked, self.blocked_how = patterns, "Fetch"
        self._fetch_gate()
        self.cdp("Network.setCacheDisabled", {"cacheDisabled": bool(patterns) or self._offline})
        return self

    # ---- the window ----

    def phone(self, width=390, height=844, scale=2, touch=True):
        """A phone's screen: the page lays itself out at this width."""
        self._metrics = {"width": int(width), "height": int(height), "deviceScaleFactor": scale, "mobile": True}
        self.cdp("Emulation.setDeviceMetricsOverride", self._metrics)
        self.cdp("Emulation.setTouchEmulationEnabled", {"enabled": bool(touch), "maxTouchPoints": 5})
        return self

    def desktop(self, size=None):
        """Back to the window size this Chrome was started with (or another)."""
        w, h = size or self.size
        self._metrics = {"width": int(w), "height": int(h), "deviceScaleFactor": self.scale, "mobile": False}
        self.cdp("Emulation.setDeviceMetricsOverride", self._metrics)
        self.cdp("Emulation.setTouchEmulationEnabled", {"enabled": False})
        return self


def one_pixel(png):
    """(r, g, b) of a PNG that is one pixel large."""
    import zlib
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    at, idat, kind = 8, b"", None
    while at < len(png):
        n, name = struct.unpack(">I", png[at:at + 4])[0], png[at + 4:at + 8]
        body = png[at + 8:at + 8 + n]
        if name == b"IHDR":
            w, h, depth, kind = struct.unpack(">IIBB", body[:10])
            if (w, h, depth) != (1, 1, 8) or kind not in (2, 6):
                raise ValueError("not a one-pixel colour PNG: %r" % ((w, h, depth, kind),))
        elif name == b"IDAT":
            idat += body
        at += 12 + n
    raw = zlib.decompress(idat)             # one filter byte, then the pixel; with no neighbours every filter leaves it as it is
    return raw[1], raw[2], raw[3]


def is_this_computer(url):
    try:
        u = urlsplit(url)
    except ValueError:
        return False
    if u.scheme in ("data", "blob", "about", "chrome", "devtools", "chrome-error", "javascript"):
        return True
    host = (u.hostname or "").lower()
    return host in ("127.0.0.1", "localhost", "::1") or host.endswith(".localhost")


# ================================================================ the self-test
#
#   python3 tests/chrome_drive.py --selftest --port 8930 --work /private/tmp/somewhere
#
# 1. the websocket client against a small websocket server made here (pieces, long messages, ping, close)
# 2. the driver on a small page served here: pointer, keys, typing, wheel, timers held, no internet, phone
# 3. the driver on the real reel picker, served by the Assistant's own page server on a pretend kit:
#    every result checked on the page AND in the kit's .kit/arrange.json
# 4. the hidden Chrome is really gone afterwards, also when its test is killed outright
#
# It uses --port for the Assistant's page server and --port + 8 for the small page; everything it makes goes
# in a new folder under --work; the real ~/.studio is never read or written (STUDIO_HOME points into --work).

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
NEVER_PORTS = set([8790, 8765, 8770, 8899]) | set(range(8850, 8867))
OUTSIDE = "https://fonts.googleapis.com/css2?family=Inter"        # the one outside address the designer will ever ask for
_results = []
_times = []


def case(name, ok, detail=""):
    _results.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + ((" -> " + str(detail)[:400]) if (detail != "" and not ok) else ""), flush=True)
    return bool(ok)


def took(name, seconds):
    _times.append((name, seconds))
    print("TIME  %s: %.3f s" % (name, seconds), flush=True)


def group(name, fn, *a):
    """Run one group of cases; an exception in it is one FAIL, and the groups after it still run."""
    try:
        return fn(*a)
    except Exception as e:
        case("%s ran to its end" % name, False, "%s: %s" % (type(e).__name__, e))
        return None


# ---- 1. the websocket client ----

def _ws_server(script, box):
    """A websocket server for one connection, on a port of its own. script(conn, read_frame, send_frame) drives it."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    srv.settimeout(10)

    def run():
        try:
            conn, _ = srv.accept()
            conn.settimeout(10)
            buf = b""
            while b"\r\n\r\n" not in buf:
                buf += conn.recv(4096)
            key = re.search(rb"Sec-WebSocket-Key: (\S+)", buf).group(1).decode()
            box["origin"] = b"\r\nOrigin:" in buf
            acc = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
            if box.get("lie"):
                acc = base64.b64encode(b"not the right answer").decode()
            conn.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n" % acc).encode())
            pend = bytearray(buf.split(b"\r\n\r\n", 1)[1])

            def read(n):
                while len(pend) < n:
                    chunk = conn.recv(65536)
                    if not chunk:
                        raise OSError("closed")
                    pend.extend(chunk)
                out = bytes(pend[:n])
                del pend[:n]
                return out

            def read_frame():
                b0, b1 = read(2)
                n = b1 & 0x7F
                if n == 126:
                    n = struct.unpack(">H", read(2))[0]
                elif n == 127:
                    n = struct.unpack(">Q", read(8))[0]
                masked = bool(b1 & 0x80)
                key = read(4) if masked else None
                data = read(n)
                return {"fin": bool(b0 & 0x80), "op": b0 & 0x0F, "masked": masked, "data": _mask(data, key) if masked else data, "raw_differs": masked and n > 0 and data != _mask(data, key)}

            def send_frame(op, data, fin=True):
                n = len(data)
                head = bytes([(0x80 if fin else 0) | op])
                head += bytes([n]) if n < 126 else (bytes([126]) + struct.pack(">H", n) if n < 65536 else bytes([127]) + struct.pack(">Q", n))
                conn.sendall(head + data)

            script(conn, read_frame, send_frame, box)
            conn.close()
        except Exception as e:
            box["server_error"] = repr(e)
        finally:
            srv.close()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return srv.getsockname()[1], t


def check_websocket():
    long_in = "é" * 40000                    # 80,000 bytes: needs the 8-byte length
    long_out = "ü" * 45000

    def script(conn, read_frame, send_frame, box):
        box["hello"] = read_frame()
        send_frame(1, b"small")
        send_frame(1, b"in ", fin=False)
        send_frame(9, b"are you there")                       # a ping in the middle of a message
        send_frame(0, b"three ", fin=False)
        send_frame(0, b"pieces", fin=True)
        send_frame(1, b"m" * 300)                            # the 2-byte length
        send_frame(1, long_in.encode("utf-8"))
        box["pong"] = read_frame()
        box["long"] = read_frame()
        box["parts"] = [read_frame(), read_frame(), read_frame()]
        send_frame(8, struct.pack(">H", 1000))
        box["close"] = read_frame()

    box = {}
    port, t = _ws_server(script, box)
    ws = WebSocket("127.0.0.1", port, "/devtools/page/x")
    ws.send("hello")
    got = [ws.recv() for _ in range(4)]
    case("websocket: a short message arrives", got[0] == "small", got[0])
    case("websocket: a message sent in three pieces, with a ping in the middle, arrives whole", got[1] == "in three pieces", got[1])
    case("websocket: a 300-byte and an 80,000-byte message arrive whole", got[2] == "m" * 300 and got[3] == long_in, (len(got[2]), len(got[3])))
    ws.send(long_out)
    ws.send("one two three four", pieces=3)
    closed = False
    try:
        ws.recv()
    except WebSocketClosed:
        closed = True
    t.join(10)
    case("websocket: the server's close ends recv() with WebSocketClosed", closed)
    case("websocket: no fault on the server's side", "server_error" not in box, box.get("server_error"))
    h = box.get("hello") or {}
    case("websocket: what the client sends is masked, and reads back right", h.get("masked") and h.get("data") == b"hello" and h.get("raw_differs"), h)
    case("websocket: the handshake names no Origin (Chrome turns one away)", box.get("origin") is False)
    p = box.get("pong") or {}
    case("websocket: the ping was answered with a masked pong carrying the same words", p.get("op") == 10 and p.get("masked") and p.get("data") == b"are you there", p)
    lg = box.get("long") or {}
    case("websocket: a 90,000-byte message goes out whole", lg.get("op") == 1 and lg.get("fin") and lg.get("data") == long_out.encode("utf-8"), len(lg.get("data", b"")))
    parts = box.get("parts") or []
    case("websocket: a message sent in three pieces goes out as text, continuation, continuation-and-end",
         [(x["op"], x["fin"]) for x in parts] == [(1, False), (0, False), (0, True)] and b"".join(x["data"] for x in parts) == b"one two three four", parts)
    c = box.get("close") or {}
    case("websocket: the close was answered with a close", c.get("op") == 8, c)
    ws.close()

    box2 = {"lie": True}
    port, t = _ws_server(lambda *a: None, box2)
    refused = False
    try:
        WebSocket("127.0.0.1", port, "/x")
    except WebSocketError:
        refused = True
    t.join(10)
    case("websocket: a server whose handshake answer is wrong is refused", refused)

    case("keys: Meta+Z is Cmd held and a small z; Shift+ArrowLeft; Mod+Shift+Z; a lone +",
         parse_combo("Meta+Z") == (4, "z") and parse_combo("Shift+ArrowLeft") == (8, "ArrowLeft")
         and parse_combo("Mod+Shift+Z") == ((4 if MAC else 2) | 8, "Z") and parse_combo("+") == (0, "+") and parse_combo("Ctrl++") == (2, "+"),
         (parse_combo("Meta+Z"), parse_combo("Mod+Shift+Z"), parse_combo("Ctrl++")))
    case("keys: names, letters, digits and signs have their key numbers",
         key_parts("Escape")[:3] == ("Escape", "Escape", 27) and key_parts("delete")[2] == 46 and key_parts("a") == ("a", "KeyA", 65, "a")
         and key_parts("7")[1:3] == ("Digit7", 55) and key_parts("?")[1:3] == ("Slash", 191) and key_parts("F5")[2] == 116 and key_parts("space")[0] == " ")


# ---- 2. the driver on a small page of its own ----

SMALL_PAGE = r"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>chrome_drive small page</title><style>
body{margin:0;font:15px sans-serif} #box{position:absolute;left:100px;top:120px;width:200px;height:160px;background:#c4683f}
#far{position:absolute;left:40px;top:2600px;width:120px;height:60px;background:#2f7cf6}
#lid{position:fixed;left:0;right:0;bottom:0;height:80px;background:#222}
#under{position:fixed;left:20px;bottom:20px;width:60px;height:40px;background:#3d7a5a}
#scroller{position:absolute;left:400px;top:120px;width:200px;height:160px;overflow:auto;background:#efe9e0}
#name{position:absolute;left:100px;top:40px;width:200px} #ink{position:absolute;left:340px;top:40px}
@media (max-width:500px){ #scroller{left:100px;top:300px} }
</style></head><body><input id='name'><input id='ink' type='color' value='#000000'><div id='box'></div><div id='scroller'><div style='height:2000px'>tall</div></div>
<div id='far'></div><div id='under'></div><div id='lid'></div><div style='height:3200px'></div>
<script>
window.EV = [];
['pointerdown','pointermove','pointerup','click','dblclick','keydown','keyup','wheel'].forEach(function(n){
  document.addEventListener(n, function(e){
    EV.push({t: n, x: e.clientX, y: e.clientY, buttons: e.buttons, alt: !!e.altKey, shift: !!e.shiftKey, meta: !!e.metaKey, ctrl: !!e.ctrlKey,
             key: e.key, code: e.code, pt: e.pointerType, detail: e.detail, dy: e.deltaY, on: e.target && e.target.id});
  }, true);
});
window.T = [];
setTimeout(function(){ T.push('timeout'); setTimeout(function(){ T.push('second'); }, 0); }, 0);
setInterval(function(){ T.push('interval'); }, 30);
requestAnimationFrame(function(){ T.push('frame'); });
document.getElementById('ink').addEventListener('input', function(e){ document.getElementById('box').style.background = e.target.value; window.INK = (window.INK || 0) + 1; });
if (location.hash === '#loud') { console.error('said by the page', 7); setTimeout(function(){ throw new Error('thrown by the page'); }, 0); Promise.reject(new Error('rejected by the page')); alert('a box from the page'); }
</script></body></html>"""


class _Small:
    """The small page, served from this process on 127.0.0.1."""
    def __init__(self, port):
        import http.server
        seen = self.seen = []

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                seen.append(self.path)
                page = self.path.startswith("/small")
                body = SMALL_PAGE.encode("utf-8") if page else b"here"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8" if page else "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()


FETCH = "(function(u){ var c = new AbortController(); var t = setTimeout(function(){ c.abort(); }, 8000); return fetch(u, {cache: 'no-store', signal: c.signal}).then(function(r){ clearTimeout(t); return r.status; }).catch(function(e){ clearTimeout(t); return 'failed: ' + e; }); })"
LINK = "(function(u){ return new Promise(function(done){ var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = u; l.onload = function(){ done('loaded'); }; l.onerror = function(){ done('error'); }; document.head.appendChild(l); }); })"


def png_size(path):
    b = Path(path).read_bytes()
    return struct.unpack(">II", b[16:24]) if b[:8] == b"\x89PNG\r\n\x1a\n" else None


def check_small(c, base, run):
    url = base + "/small"
    t0 = time.time()
    c.open(url)
    took("opening a small page", time.time() - t0)
    v = c.js("[innerWidth, innerHeight, devicePixelRatio, document.hasFocus(), document.visibilityState]")
    case("the window is the size asked for, in front as far as the page can tell", v == [1280, 900, 1, True, "visible"], v)
    case("js(): numbers, strings, lists, null, a promise's value, and a thrown error",
         c.js("1 + 1") == 2 and c.js("'a' + 'b'") == "ab" and c.js("[1, {a: null}]") == [1, {"a": None}] and c.js("undefined") is None
         and c.js("new Promise(function(ok){ setTimeout(function(){ ok('later'); }, 20); })") == "later")
    threw = ""
    try:
        c.js("nothing.here")
    except JSError as e:
        threw = str(e)
    case("js(): a script that throws raises JSError with the page's words", "nothing is not defined" in threw, threw)
    r = c.rect("#box")
    case("rect(): the box where its styles put it", r and (r["x"], r["y"], r["w"], r["h"], r["cx"], r["cy"]) == (100, 120, 200, 160, 200, 200), r)
    case("rect(): nothing there gives None", c.rect("#nobody") is None)

    # a drag: press, moves with the button held, release
    c.js("EV.length = 0")
    d = c.drag("#box", (500, 400), steps=5, alt=True)
    ev = c.js("EV")
    kinds = [e["t"] for e in ev]
    moves = [e for e in ev if e["t"] == "pointermove"]
    case("drag(): one pointerdown, then moves, then one pointerup, already handled when drag() returns",
         kinds.count("pointerdown") == 1 and kinds.count("pointerup") == 1 and kinds.index("pointerdown") == 1 and [k for k in kinds if k.startswith("pointer")][-1] == "pointerup" and len(moves) == 6, kinds)
    case("drag(): the press is on the box, every move after it has the button held, the release has not",
         ev[1]["on"] == "box" and ev[0]["buttons"] == 0 and all(m["buttons"] == 1 for m in moves[1:]) and [e["buttons"] for e in ev if e["t"] == "pointerup"] == [0], [(e["t"], e["buttons"]) for e in ev])
    case("drag(): it ends where asked, in even steps, a mouse, with Alt held all the way",
         [(e["x"], e["y"]) for e in ev if e["t"] == "pointerup"] == [(500, 400)] and [m["x"] for m in moves] == [200, 260, 320, 380, 440, 500] and all(e["pt"] == "mouse" and e["alt"] and not e["shift"] for e in ev if e["t"].startswith("pointer")), ev[-1])
    took("a 5-step drag on the small page", d)

    c.js("EV.length = 0")
    c.click("#box", shift=True)
    c.double_click("#box")
    ev = c.js("EV")
    clicks = [e for e in ev if e["t"] == "click"]
    case("click() and double_click(): three clicks counted 1, 1, 2 and one dblclick; Shift only on the first",
         [e["detail"] for e in clicks] == [1, 1, 2] and [e["t"] for e in ev].count("dblclick") == 1 and [e["shift"] for e in clicks] == [True, False, False], [(e["t"], e["detail"]) for e in ev])

    # keys
    c.js("EV.length = 0")
    for k in ("Escape", "Delete", "Shift+ArrowLeft", "Meta+Z", "Meta+Shift+Z", "ArrowDown"):
        c.key(k)
    downs = [(e["key"], e["code"], e["meta"], e["shift"]) for e in c.js("EV") if e["t"] == "keydown"]
    want = [("Escape", "Escape", False, False), ("Delete", "Delete", False, False), ("Shift", "ShiftLeft", False, True), ("ArrowLeft", "ArrowLeft", False, True),
            ("Meta", "MetaLeft", True, False), ("z", "KeyZ", True, False), ("Shift", "ShiftLeft", False, True), ("Meta", "MetaLeft", True, True), ("Z", "KeyZ", True, True),
            ("ArrowDown", "ArrowDown", False, False)]
    case("key(): Escape, Delete, Shift+ArrowLeft, Meta+Z, Meta+Shift+Z, ArrowDown reach the page as a keyboard sends them", [list(x) for x in downs] == [list(x) for x in want], downs)
    ups = [e["key"] for e in c.js("EV") if e["t"] == "keyup"]
    case("key(): every key that went down came up", len(ups) == len(downs), ups)

    c.click("#name")
    c.type_text("Héllo, World! 100% (ok?) 😀")
    val = c.js("document.getElementById('name').value")
    case("type_text(): capitals, signs, an accent and an emoji all arrive", val == "Héllo, World! 100% (ok?) 😀", val)
    if MAC:
        c.key("Meta+A")
        sel = c.js("[document.getElementById('name').selectionStart, document.getElementById('name').selectionEnd]")
        c.key("Backspace")
        gone = c.js("document.getElementById('name').value")
        c.key("Meta+Z")
        back = c.js("document.getElementById('name').value")
        case("key(): on a Mac, Cmd+A selects, Backspace clears and Cmd+Z brings it back, as by hand", sel == [0, len(val) + 1] and gone == "" and back == val, (sel, gone, back))
    c.key_down("Shift")
    c.js("EV.length = 0")
    c.click("#box")
    held = [e["shift"] for e in c.js("EV") if e["t"] == "click"]
    c.key_up("Shift")
    c.js("EV.length = 0")
    c.click("#box")
    after = [e["shift"] for e in c.js("EV") if e["t"] == "click"]
    case("key_down('Shift') holds Shift for the mouse until key_up", held == [True] and after == [False], (held, after))

    # the wheel
    c.js("EV.length = 0")
    c.wheel("#scroller", 120)
    w = [e for e in c.js("EV") if e["t"] == "wheel"]
    case("wheel(): the page has had the wheel event, and the box under it has scrolled, when wheel() returns",
         len(w) == 1 and w[0]["dy"] == 120 and c.js("document.getElementById('scroller').scrollTop") == 120, w)

    # points, scrolling and things in the way
    p = c.point("#far")
    case("point(): something far down the page is brought to the middle of the window first", 300 < p[1] < 600 and c.js("scrollY") > 1500, (p, c.js("scrollY")))
    covered = ""
    try:
        c.click("#under")
    except Covered as e:
        covered = str(e)
    case("click(): a press on something lying under a bar is refused, naming what is on top", "div#lid" in covered, covered)
    c.js("EV.length = 0")
    c.click("#under", check=False)
    case("click(check=False) presses anyway, and the bar gets it", [e["on"] for e in c.js("EV") if e["t"] == "click"] == ["lid"])
    missing = False
    try:
        c.click("#nobody")
    except LookupError:
        missing = True
    case("click(): a selector that matches nothing raises LookupError", missing)
    c.js("scrollTo(0, 0)")

    # waiting
    c.js("setTimeout(function(){ window.LATE = 'here'; }, 150)")
    case("wait_for(): returns the value once it is true", c.wait_for("window.LATE", 5) == "here")
    late = ""
    t0 = time.time()
    try:
        c.wait_for("window.NEVER", 0.3, tell="document.title")
    except Timeout as e:
        late = str(e)
    case("wait_for(): gives up after the time given, saying what it last saw", 0.3 <= time.time() - t0 < 2 and "window.NEVER" in late and "small page" in late, late)

    # what the page says
    c.clear_errors()
    c.open(url + "?again=1#loud")
    try:
        wait_until(lambda: len(c.errors) >= 3 and c.dialogs, 5, what="the page's three errors and its box")
    except Timeout:
        pass
    errs = c.page_errors()
    case("page_errors(): a console.error, an uncaught exception and a promise nobody caught are all collected",
         any("said by the page 7" in e for e in errs) and any("thrown by the page" in e for e in errs) and any("rejected by the page" in e for e in errs), errs)
    case("a box the page puts up (alert) is answered, so the page is never stuck behind it", [d["text"] for d in c.dialogs] == ["a box from the page"], c.dialogs)
    c.clear_errors()
    c.open(url)
    c.wait_for("T.indexOf('second') >= 0 && T.indexOf('frame') >= 0 && T.indexOf('interval') >= 0", 5)
    case("a clean page has no errors, and asked for nothing outside this computer", c.page_errors() == [] and c.outside_requests() == [], (c.page_errors(), c.outside_requests()))

    # timers held
    c.hold_timers()
    c.open(url)
    c.js("EV.length = 0")
    c.click("#box")
    seen_click = len([e for e in c.js("EV") if e["t"] == "click"])
    fetched = c.js(FETCH + "(%s)" % json.dumps(base + "/plain"))
    case("hold_timers(): no timeout, interval or frame has run, yet a click and a fetch go through",
         c.js("T") == [] and c.timers_waiting() == 3 and seen_click == 1 and fetched == 200, (c.js("T"), c.timers_waiting(), seen_click, fetched))
    n1 = c.run_timers()
    t1 = c.js("T.slice()")
    n2 = c.run_timers()
    t2 = c.js("T.slice()")
    case("run_timers(): what was waiting runs once; a timer set by a timer waits for the next go",
         n1 == 3 and sorted(t1) == ["frame", "interval", "timeout"] and n2 == 2 and sorted(t2) == ["frame", "interval", "interval", "second", "timeout"], (n1, t1, n2, t2))
    c.free_timers()
    c.open(url)
    case("free_timers(): the next page's timers run by themselves again", c.wait_for("T.indexOf('second') >= 0 && T.indexOf('frame') >= 0", 5) is True)

    # no internet
    here = json.dumps(base + "/plain")
    out = json.dumps(OUTSIDE)
    online = c.js(FETCH + "(%s)" % out)
    has_net = online == 200
    if not has_net:
        print("NOTE  this computer cannot reach %s right now (%s): the 'works again' halves below cannot be shown" % (OUTSIDE, online), flush=True)
    c.set_offline(True)
    a, b = c.js(FETCH + "(%s)" % out), c.js(FETCH + "(%s)" % here)
    lk = c.js(LINK + "(%s)" % out)
    case("set_offline(True): an outside address fails, a stylesheet link's onerror fires, and 127.0.0.1 still answers",
         str(a).startswith("failed") and lk == "error" and b == 200, (a, lk, b))
    c.open(url + "?offline=1")
    case("set_offline(True): a page on this computer still opens", c.js("document.title") == "chrome_drive small page")
    refused = ""
    try:
        c.open("https://fonts.googleapis.com/")
    except CannotOpen as e:
        refused = str(e)
    case("set_offline(True): a page on the internet does not open (CannotOpen)", "INTERNET_DISCONNECTED" in refused, refused)
    c.open(url)
    case("set_offline(True): the failure is the one a computer with no internet gives", any("INTERNET_DISCONNECTED" in f["error"] and "fonts.googleapis.com" in f["url"] for f in c.failed), c.failed[-3:])
    c.set_offline(False)
    a, b = c.js(FETCH + "(%s)" % out), c.js(FETCH + "(%s)" % here)
    if has_net:
        case("set_offline(False): the outside address answers again", a == 200 and b == 200, (a, b))
    c.set_offline(True, everything=True)
    a, b, on = c.js(FETCH + "(%s)" % out), c.js(FETCH + "(%s)" % here), c.js("navigator.onLine")
    case("set_offline(True, everything=True): Chrome's own switch cuts off 127.0.0.1 too, and navigator.onLine is false",
         str(a).startswith("failed") and str(b).startswith("failed") and on is False, (a, b, on))
    c.set_offline(False, everything=True)
    b, on = c.js(FETCH + "(%s)" % here), c.js("navigator.onLine")
    case("set_offline(False, everything=True): 127.0.0.1 answers again", b == 200 and on is True, (b, on))
    c.block_urls(["*fonts.googleapis.com*"])
    c.clear_errors()
    a, lk, b = c.js(FETCH + "(%s)" % out), c.js(LINK + "(%s)" % out), c.js(FETCH + "(%s)" % here)
    case("block_urls(): the named address fails (fetch and stylesheet link), 127.0.0.1 still answers [%s]" % c.blocked_how,
         str(a).startswith("failed") and lk == "error" and b == 200 and any("fonts.googleapis.com" in f["url"] and "blocked" in f["error"].lower() for f in c.failed), (a, lk, b, c.failed[-2:]))
    c.block_urls([])
    if has_net:
        a, lk = c.js(FETCH + "(%s)" % out), c.js(LINK + "(%s)" % out)
        case("block_urls([]): lifted, the address answers and the stylesheet loads", a == 200 and lk == "loaded", (a, lk))
    case("outside_requests(): the outside addresses asked for are listed", any("fonts.googleapis.com" in u for u in c.outside_requests()) and not any("127.0.0.1" in u for u in c.outside_requests()))

    # a phone
    c.phone(390, 844)
    c.open(url)
    c.js("EV.length = 0")
    c.tap("#box")
    ev = c.js("EV")
    case("phone(): the page is 390 wide, and tap() is a finger (pointerType touch) that ends in a click",
         c.js("innerWidth") == 390 and [e["pt"] for e in ev if e["t"] == "pointerdown"] == ["touch"] and [e["t"] for e in ev].count("click") == 1, (c.js("innerWidth"), [(e["t"], e["pt"]) for e in ev]))
    c.desktop()
    c.open(url)
    case("desktop(): back to the size it started with", c.js("[innerWidth, innerHeight]") == [1280, 900])

    # pictures
    LAY = "[document.documentElement.scrollWidth, document.documentElement.scrollHeight, document.documentElement.clientWidth, scrollY]"
    c.js("scrollTo(0, 700)")
    lay = c.js(LAY)
    shot = c.screenshot("small.png")
    whole = c.screenshot("small-whole.png", full=True)
    case("screenshot(): a PNG the size of the window, and one of the whole page, inside the work folder",
         png_size(shot) == (1280, 900) and png_size(whole) == (lay[0], lay[1]) and lay[1] > 3000 and shot.parent == run and whole.parent == run, (png_size(shot), png_size(whole), lay))
    case("screenshot(full=True): the page is laid out and scrolled afterwards exactly as before", c.js(LAY) == lay, (lay, c.js(LAY)))
    c.js("scrollTo(0, 0)")
    outside = False
    try:
        c.screenshot(str(run.parent / "not-in-work.png"))
    except ValueError:
        outside = True
    case("screenshot(): a path outside the work folder is refused, and nothing is written there", outside and not (run.parent / "not-in-work.png").exists())

    px = [c.pixel(200, 200), c.pixel(50, 110)]
    c.set_value("#ink", "#2f7cf6")
    after = [c.pixel(200, 200), c.js("[document.getElementById('ink').value, window.INK]")]
    c.js("scrollTo(0, 60)")
    scrolled = c.pixel(200, 140)
    c.js("scrollTo(0, 0)")
    case("pixel(): the box shows its terracotta and the page beside it white; set_value() on the colour box turns it blue (also read after scrolling)",
         px == [(196, 104, 63), (255, 255, 255)] and after == [(47, 124, 246), ["#2f7cf6", 1]] and scrolled == (47, 124, 246) and c.js(LAY)[:3] == lay[:3], (px, after, scrolled, c.js(LAY), lay))

    big = "x" * 400000
    t0 = time.time()
    ok = c.js("(%s).length" % json.dumps(big)) == 400000 and len(c.js("'y'.repeat(3000000)")) == 3000000
    case("a 400,000-character script goes in and a 3,000,000-character answer comes back (in %.2f s)" % (time.time() - t0), ok)


# ---- 3. the driver on the real reel picker ----

class _PageServer:
    """The Assistant's own page server from this working copy, on a scratch STUDIO_HOME."""
    def __init__(self, env, port):
        self.env, self.want, self.port, self.proc = env, port, None, None

    def start(self):
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.want)],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=self.env, encoding="utf-8", errors="replace")
        line = self.proc.stdout.readline()
        m = re.search(r"127\.0\.0\.1:(\d+)/", line)
        if not m:
            raise RuntimeError("the page server did not start (%r)" % line.strip())
        self.port = int(m.group(1))
        if self.port in NEVER_PORTS:
            raise RuntimeError("the page server took port %d, which is not this test's to use" % self.port)

        def up():
            socket.create_connection(("127.0.0.1", self.port), timeout=0.5).close()
            return True
        wait_until(up, 10, what="the page server to answer")
        threading.Thread(target=self._drain, daemon=True).start()
        return self.port

    def _drain(self):
        try:
            for _ in self.proc.stdout:
                pass
        except (OSError, ValueError):
            pass

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.proc = None


ROW = "Array.from(document.querySelectorAll('#row .rt')).map(function(t){ return +t.dataset.n; })"
BARS = "Array.from(document.querySelectorAll('#row .rt .mk')).map(function(b){ return b.textContent; })"
PHOTOS = 18          # 18 photos give a reel pick of 9, so there are photos below that are not yet in the row
READY = "document.getElementById('status').textContent === 'Saved' && document.querySelectorAll('#row .rt').length > 0 && Array.from(document.querySelectorAll('#row img')).every(function(i){ return i.complete && i.naturalWidth > 0; })"


def check_picker(c, run, port):
    if not shutil.which("sips"):
        print("SKIP  the reel picker part: the pretend kit is drawn with the Mac's sips, which this computer does not have", flush=True)
        return
    target = run / "fake"
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "fake_kit.py"), str(target), "--photos", str(PHOTOS)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    if not case("the pretend kit was made (tests/fake_kit.py, %d photos)" % PHOTOS + "", r.returncode == 0, (r.stdout + r.stderr)[-400:]):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    kit_name = "2026-11-01 Fake beach"
    kit = target / "The Assistant" / "Your Content" / kit_name
    arr = kit / ".kit" / "arrange.json"
    r = subprocess.run([sys.executable, str(SCRIPTS / "arrange.py"), "previews", "Fake beach"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=600)
    if not case("the small copies of its photos were made (arrange.py previews)", r.returncode == 0 and r.stdout.startswith("made %d" % PHOTOS), (r.stdout + r.stderr)[-400:]):
        return
    srv = _PageServer(env, port)
    P = None
    try:
        P = srv.start()
        print("      (the Assistant's page server on port %d, STUDIO_HOME=%s)" % (P, studio), flush=True)
        url = "http://127.0.0.1:%d/arrange.html?kit=%s&piece=reel" % (P, quote(kit_name))

        def disk():
            now = json.loads(arr.read_text(encoding="utf-8"))["reel"]["now"]
            return {"nums": now["nums"], "marks": now["marks"], "rev": now["rev"]}

        def on_disk(nums, marks=None):
            def look():
                d = disk()
                return d if d["nums"] == nums and (marks is None or d["marks"] == marks) else None
            look.__name__ = "arrange.json to hold %s %s" % (nums, marks or "")
            return wait_until(look, 10)

        c.clear_errors()
        t0 = time.time()
        c.open(url)
        c.wait_for(READY, 20, tell="document.body.innerText.slice(0, 300)")
        took("opening the reel picker until it says Saved and its row's pictures are in", time.time() - t0)
        row = c.js(ROW)
        d0 = disk()
        picks = [int(re.sub(r"\D", "", str(x))) for x in json.loads((kit / ".kit" / "kit.json").read_text(encoding="utf-8"))["picks"]["reel"]]
        case("the row read from the page is the kit's reel pick, and the order in arrange.json", 3 <= len(row) < PHOTOS and row == d0["nums"] == picks, (row, d0, picks))
        case("the page shows the shoot's name and every photo below", "Fake beach" in c.text("#title") and c.count("#pool .pt") == PHOTOS, (c.text("#title"), c.count("#pool .pt")))

        # -- drag a photo from the grid into the row, to second place --
        n_new = c.js("(function(){ var t = document.querySelector('#pool .pt:not(.in)'); return t ? +t.dataset.n : null; })()")
        src = "#pool .pt[data-n='%d']" % n_new
        c.point(src)                                         # scrolls it into view if need be, BEFORE the row is measured
        r1 = c.rect("#row .rt", 1)
        c.drag(src, (r1["x"] + r1["w"] * 0.25, r1["cy"]), steps=12, release=False)
        mid = c.js("[document.querySelectorAll('.arr-lift').length, document.body.classList.contains('arr-dragging'), document.querySelectorAll('.ins.on').length, %s]" % ROW)
        case("drag from the grid: with the button still held, the photo is lifted and the bar shows where it would land; nothing has moved yet",
             mid == [1, True, 1, row], mid)
        t0 = time.time()
        c.mouse_release()
        want = row[:1] + [n_new] + row[1:]
        now_page = c.js("[%s, document.querySelectorAll('.arr-lift').length, document.querySelector(%s).classList.contains('in')]" % (ROW, json.dumps(src)))
        case("drag from the grid: on release the photo is second in the row at once (no waiting), and marked as in the row below",
             now_page == [want, 0, True], now_page)
        d1 = on_disk(want)
        case("drag from the grid: arrange.json holds the new order, one save on", d1["rev"] == d0["rev"] + 1 and d1["marks"] == [""] * len(want), d1)
        took("a drop, until the new order is in arrange.json (the page waits 0.4 s before saving)", time.time() - t0)
        c.wait_for("document.getElementById('status').textContent === 'Saved'", 10)
        row = want

        # -- drag to reorder: the last photo to the front --
        last = row[-1]
        r0 = c.rect("#row .rt", 0)
        dsec = c.drag("#row .rt[data-n='%d'] .ph" % last, (r0["x"] + r0["w"] * 0.25, r0["cy"]), steps=12)
        took("a 12-step drag on the reel picker (14 pointer events)", dsec)
        want = [last] + row[:-1]
        case("drag to reorder: the last photo is first on the page at once", c.js(ROW) == want, c.js(ROW))
        d2 = on_disk(want)
        case("drag to reorder: arrange.json holds it", d2["rev"] == d1["rev"] + 1, d2)
        row = want

        # -- the X on one --
        gone = row[2]
        c.click("#row .rt[data-n='%d'] button.x" % gone)
        want = [n for n in row if n != gone]
        case("the X: that photo is out of the row on the page, and no longer marked below",
             c.js(ROW) == want and c.js("document.querySelector(\"#pool .pt[data-n='%d']\").classList.contains('in')" % gone) is False, c.js(ROW))
        d3 = on_disk(want)
        case("the X: arrange.json holds the shorter row", d3["rev"] == d2["rev"] + 1, d3)
        row = want

        # -- a timing bar --
        who = row[1]
        bar = "#row .rt[data-n='%d'] button.mk" % who
        c.click(bar)
        bars = c.js(BARS)
        case("a timing bar: one press and that photo's bar says Longer, the others Normal", bars == ["Normal", "Longer"] + ["Normal"] * (len(row) - 2), bars)
        marks = ["", "+"] + [""] * (len(row) - 2)
        d4 = on_disk(row, marks)
        case("a timing bar: arrange.json holds '+' for that photo", d4["rev"] == d3["rev"] + 1, d4)
        c.click(bar)
        marks[1] = "-"
        case("a timing bar: a second press says Quicker, on the page and in arrange.json", c.js(BARS)[1] == "Quicker" and on_disk(row, marks)["rev"] == d4["rev"] + 1, c.js(BARS))
        c.wait_for("document.getElementById('status').textContent === 'Saved'", 10)

        # -- the big view, and Escape --
        before = disk()
        other = c.js("(function(){ var t = document.querySelector('#pool .pt:not(.in)'); return +t.dataset.n; })()")
        c.click("#pool .pt[data-n='%d']" % other)
        opened = c.js("[document.getElementById('big').classList.contains('on'), document.querySelector('#big .where').textContent, document.querySelectorAll('#big .bacts button').length]")
        case("a click on a photo (no drag) opens it big, saying it is not in the reel, with its one button", opened[0] is True and "Not in your reel" in opened[1] and opened[2] == 1, opened)
        c.key("ArrowRight")
        stepped = c.js("document.getElementById('big').classList.contains('on')")
        c.key("Escape")
        closed = c.js("document.getElementById('big').classList.contains('on')")
        case("Escape in the big view closes it; the row and arrange.json are as they were", stepped is True and closed is False and c.js(ROW) == row and disk() == before, (stepped, closed, disk()))

        # -- nothing may wait on a timer: an X pressed straight after a drop, with every timer held --
        c.hold_timers()
        c.open(url)
        c.wait_for("document.getElementById('status').textContent === 'Saved' && document.querySelectorAll('#row .rt').length === %d" % len(row), 20)
        before = disk()
        n2 = c.js("(function(){ var t = document.querySelector('#pool .pt:not(.in)'); return +t.dataset.n; })()")
        src = "#pool .pt[data-n='%d']" % n2
        c.point(src)
        rl = c.rect("#row .rt", len(row) - 1)
        c.drag(src, (rl["x"] + rl["w"] * 0.75, rl["cy"]), steps=8)
        c.click("#row .rt[data-n='%d'] button.x" % row[0])
        want = row[1:] + [n2]
        held = [c.js(ROW), c.text("#status"), c.timers_waiting() > 0, disk() == before]
        case("with every timer held: a drop to the end and an X pressed straight after both show on the page; it says Saving... and nothing is on disk yet",
             held == [want, "Saving...", True, True], held)
        c.run_timers()
        d5 = on_disk(want)
        case("with every timer held: let the timers run once and the save lands in arrange.json", d5["rev"] == before["rev"] + 1, d5)
        c.free_timers()
        row = want

        # -- a phone's width, a finger --
        c.phone(390, 844)
        c.open(url)
        c.wait_for(READY, 20)
        wide = c.js("[innerWidth, document.documentElement.scrollWidth]")
        c.tap("#pool .pt[data-n='%d']" % other)
        big = c.js("document.getElementById('big').classList.contains('on')")
        c.key("Escape")
        case("at a phone's width the picker does not scroll sideways, and a finger's tap on a photo opens it big",
             wide[0] == 390 and wide[1] <= 390 and big is True and c.js(ROW) == row, (wide, big))
        shot = c.screenshot("picker-phone.png")
        c.desktop()
        c.open(url)
        c.wait_for(READY, 20)
        shot2 = c.screenshot("picker.png")
        case("screenshots of the picker (phone and desktop) are in the work folder", png_size(shot) == (780, 1688) and png_size(shot2) == (1280, 900), (png_size(shot), png_size(shot2)))

        case("the picker page: no errors, no exception", c.page_errors() == [], c.page_errors())
        case("the picker page asked for nothing outside this computer", c.outside_requests() == [], c.outside_requests())
        asked = [r["url"] for r in c.requests]
        case("the test never pressed anything that opens a window (no /open request)", not any("/open" in urlsplit(u).path for u in asked) and len(asked) > 10, [u for u in asked if "/open" in u])
        case("a fresh load of the page shows the same row (it is on disk, not in the browser)", c.js(ROW) == row == disk()["nums"], (c.js(ROW), disk()))
    finally:
        srv.stop()
    gone = P is None
    try:
        socket.create_connection(("127.0.0.1", P or 1), timeout=0.5).close()
    except OSError:
        gone = True
    case("the Assistant's page server was stopped", gone)


# ---- 4. gone means gone ----

def _pids_with(text):
    if WINDOWS:
        return []
    r = subprocess.run(["pgrep", "-f", text], capture_output=True, text=True)
    return [int(x) for x in r.stdout.split() if x.isdigit() and int(x) != os.getpid()]


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


KILLED_CHILD = r"""
import sys, time
sys.path.insert(0, sys.argv[1])
import chrome_drive
c = chrome_drive.Chrome(sys.argv[2]).start()
print(c.proc.pid, c.profile, flush=True)
time.sleep(120)
"""


def check_gone(run, first):
    pid, profile, port = first
    case("after stop(): the hidden Chrome's process is gone, with every helper it started", not _pid_alive(pid) and _pids_with(str(profile)) == [], (pid, _pids_with(str(profile))))
    shut = False
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
    except OSError:
        shut = True
    case("after stop(): its debugging port no longer answers", shut)
    left = [p.name for p in run.iterdir() if p.is_dir() and p.name.startswith("chrome-profile-")]
    case("after stop(): its throwaway profile folder is removed, and only that", not profile.exists() and left == [] and (run / "small.png").exists(), left)

    # an exception inside "with" still stops it
    seen = {}
    try:
        with Chrome(run) as c2:
            seen = {"pid": c2.proc.pid, "profile": c2.profile}
            raise RuntimeError("a test that blew up")
    except RuntimeError:
        pass
    case("a test that raises inside 'with' still leaves no Chrome and no profile behind",
         seen and not _pid_alive(seen["pid"]) and not seen["profile"].exists() and _pids_with(str(seen["profile"])) == [], seen)

    no = False
    old = os.environ.get(ENV_CHROME)
    os.environ[ENV_CHROME] = str(run / "no-such-chrome")
    try:
        none_found = find_chrome() is None
        try:
            Chrome(run).start()
        except NoChrome:
            no = True
    finally:
        if old is None:
            del os.environ[ENV_CHROME]
        else:
            os.environ[ENV_CHROME] = old
    case("with no Chrome to be found, find_chrome() is None and start() raises NoChrome (a test can SKIP)", none_found and no)

    if WINDOWS:
        print("SKIP  a test killed outright: the watcher that ends Chrome then is Mac and Linux only", flush=True)
        return
    child = subprocess.Popen([sys.executable, "-c", KILLED_CHILD, str(Path(__file__).resolve().parent), str(run)], stdout=subprocess.PIPE, text=True)
    line = child.stdout.readline().split(None, 1)
    cpid, cprofile = int(line[0]), line[1].strip()
    was_up = _pid_alive(cpid)
    t0 = time.time()
    child.kill()                                             # kill -9: no "finally", no atexit
    child.wait(timeout=5)
    try:
        wait_until(lambda: not _pid_alive(cpid) and _pids_with(cprofile) == [], 10, what="the orphaned Chrome to end")
        ended = True
    except Timeout:
        ended = False
        for p in [cpid] + _pids_with(cprofile):              # never leave one behind, whatever the result
            try:
                os.kill(p, signal.SIGKILL)
            except OSError:
                pass
    case("a test killed outright (kill -9): its hidden Chrome was running, and is ended within seconds anyway (%.1f s)" % (time.time() - t0), was_up and ended)
    if os.path.isdir(cprofile) and Path(cprofile).parent == run and (Path(cprofile) / "made-by-chrome_drive.txt").is_file():
        shutil.rmtree(cprofile, ignore_errors=True)          # this test's own leftover; a real kill leaves it for a person


def selftest(port, work):
    if any(p in NEVER_PORTS for p in range(port, port + 10)):
        print("STOP: ports %d to %d reach one the real pages use. Give another --port." % (port, port + 9))
        return 2
    if work:
        work = Path(work).resolve()
        work.mkdir(parents=True, exist_ok=True)
    else:
        work = Path(tempfile.mkdtemp(prefix="chrome-drive-", dir="/private/tmp" if os.path.isdir("/private/tmp") else None)).resolve()
    run = Path(tempfile.mkdtemp(prefix="selftest-%s-" % time.strftime("%Y%m%d-%H%M%S"), dir=str(work))).resolve()
    print("      (everything this run makes is in %s)" % run, flush=True)
    t_all = time.time()

    group("the websocket client", check_websocket)

    path = find_chrome()
    if not path:
        bad = [n for n, ok in _results if not ok]
        print("SKIP  no Chrome on this computer (set %s to point at one): the page tests were not run" % ENV_CHROME)
        return 1 if bad else 0
    first = None
    small = None
    c = Chrome(run)
    try:
        c.start()
        took("starting the hidden Chrome (%s) until it takes commands" % c.version, c.started_in)
        first = (c.proc.pid, c.profile, c.debug_port)
        if MAC:
            listing = subprocess.run(["lsappinfo", "list"], capture_output=True, text=True).stdout
            m = re.search(r'pid = %d [^\n]*type="(\w+)"' % c.proc.pid, listing)
            kind = m.group(1) if m else "not listed"
            case("the hidden Chrome is no app in the Dock and has no window (the Mac lists it as %s)" % kind, kind in ("BackgroundOnly", "not listed"), kind)
        case("it runs on a throwaway profile inside the work folder, never the person's own",
             c.profile.parent == run and "--user-data-dir=" + str(c.profile) in " ".join(c.proc.args) and "--headless=new" in c.proc.args, c.proc.args)
        small = _Small(port + 8)
        group("the driver on a small page", check_small, c, "http://127.0.0.1:%d" % small.port, run)
        group("the driver on the reel picker", check_picker, c, run, port)
    except Exception as e:
        case("the hidden Chrome ran to the end of the test", False, "%s: %s" % (type(e).__name__, e))
    finally:
        t0 = time.time()
        c.stop()
        took("stopping the hidden Chrome and removing its profile", time.time() - t0)
        if small is not None:
            small.stop()
    if first:
        group("gone means gone", check_gone, run, first)

    bad = [n for n, ok in _results if not ok]
    print("\n%d cases, %d passed, %d failed, in %.1f s" % (len(_results), len(_results) - len(bad), len(bad), time.time() - t_all))
    for n in bad:
        print("  failed: " + n)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description="Drive a hidden Chrome from a test. See the top of this file.")
    ap.add_argument("--selftest", action="store_true", help="prove the driver on the reel picker")
    ap.add_argument("--port", type=int, default=8930, help="the Assistant's page server goes here; the small page on this + 8")
    ap.add_argument("--work", help="a folder under /private/tmp; a new folder is made inside it for this run")
    ap.add_argument("--where", action="store_true", help="print the Chrome this would use")
    a = ap.parse_args()
    if a.where:
        print(find_chrome() or "no Chrome found")
        return 0
    if a.selftest:
        return selftest(a.port, a.work)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
