#!/usr/bin/env python3
"""The Assistant by Horizon Found. Checks what this computer's Claude workspace can do, and how fast.

  python3 check_setup.py

Prints one line per item, OK or MISSING, then a speed note. Nothing is installed or changed.
"""
import os, platform, shutil, subprocess, sys, tempfile, time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def line(label, ok, note=""):
    print(f"{'OK     ' if ok else 'MISSING'}  {label}" + (f"  ({note})" if note else ""))


def ver(cmd, flag="-version"):
    try:
        out = subprocess.run([cmd, flag], capture_output=True, text=True, timeout=20).stdout.splitlines()
        return out[0].strip()[:60] if out else ""
    except Exception:
        return ""


def main():
    mach = platform.machine().lower()
    osname = platform.system()
    chip = ("Apple silicon or other ARM" if mach in ("arm64", "aarch64") else "Intel/AMD" if mach in ("x86_64", "amd64") else mach)
    print(f"Workspace: {osname} {platform.release()} · {chip} · {os.cpu_count() or '?'} cores · Python {platform.python_version()}")
    host = "Mac" if osname == "Darwin" else ("Windows" if osname == "Windows" else "a Linux workspace (the Claude app runs the tools in here; your own computer is a Mac or a PC)")
    print(f"Running on: {host}")
    all_ok = True
    for tool in ("ffmpeg", "ffprobe"):
        p = shutil.which(tool)
        line(tool, bool(p), ver(tool) if p else "video can't be built without it")
        all_ok &= bool(p)
    for mod, why in (("numpy", "finds the beats"), ("PIL", "renders the hook text and photos")):
        try:
            m = __import__(mod)
            line(mod, True, getattr(m, "__version__", ""))
        except Exception:
            line(mod, False, why)
            all_ok = False
    # extras: nice, never required
    for mod, why in (("pillow_heif", "iPhone HEIC photos open directly; without it ImageMagick is tried, then the photo is skipped"),
                     ("cv2", "face check in the grader")):
        try:
            __import__(mod)
            line(mod + " (extra)", True)
        except Exception:
            print(f"-        {mod} (extra, not needed)  {why}")
    conv = shutil.which("magick") or shutil.which("convert")
    print(f"{'OK     ' if conv else '-      '}  ImageMagick (extra, for HEIC)" + ("" if conv else "  not found; HEIC photos would be skipped"))
    # disk
    try:
        free = shutil.disk_usage(tempfile.gettempdir()).free / 1e9
        line("free space", free > 1.0, f"{free:.1f} GB in the workspace; a reel needs well under 1 GB")
    except Exception:
        pass
    # speed probe: one second of 1080x1920 with the push-in, same filter the reel uses
    if shutil.which("ffmpeg"):
        try:
            from PIL import Image
            tmp = tempfile.mkdtemp()
            jpg = os.path.join(tmp, "p.jpg"); out = os.path.join(tmp, "p.mp4")
            Image.new("RGB", (1440, 2560), (200, 180, 150)).save(jpg, quality=80)
            vf = ("scale=1296:2304,zoompan=z='min(1+0.10*on/30,1.10)':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*0.40':d=1:s=1080x1920:fps=30,setsar=1")
            t0 = time.time()
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", "30", "-t", "1", "-i", jpg, "-vf", vf, "-t", "1",
                            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out], capture_output=True, timeout=180)
            dt = time.time() - t0
            shutil.rmtree(tmp, ignore_errors=True)
            if dt < 4:
                speed = f"fast: a 15-second reel takes about {int(dt * 15 * 1.3) + 10} seconds"
            elif dt < 10:
                speed = f"okay: a 15-second reel takes about {int(dt * 15 * 1.3) + 10} seconds; the push-in effect stays on"
            else:
                speed = f"slow: a 15-second reel would take several minutes, so photos will hold still instead of pushing in (same cuts)"
            print(f"Speed    {dt:.1f} s to render one second of video · {speed}")
        except Exception as e:
            print(f"Speed    couldn't measure ({e.__class__.__name__})")
    print("Everything the reel tool needs is here. Nothing to install." if all_ok else
          "Something the reel tool needs is missing. Screenshot this and send it to support with Mac or PC in the subject.")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
