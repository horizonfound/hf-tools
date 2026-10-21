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
    # speed probe: one second of 1080x1920 the way the reel draws it (frame by frame in Pillow, encoded by ffmpeg)
    if shutil.which("ffmpeg"):
        try:
            from PIL import Image
            W, H = 1080, 1920
            im = Image.new("RGB", (int(W * 1.14), int(H * 1.14)), (200, 180, 150))
            bw, bh = im.size
            t0 = time.time()
            p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30",
                                  "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "15", "-pix_fmt", "yuv420p",
                                  "-f", "null", "-"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            for i in range(30):
                z = 1 + 0.07 * i / 29
                vw, vh = bw / z, bh / z
                fr = im.transform((W, H), Image.AFFINE, (vw / W, 0, (bw - vw) / 2, 0, vh / H, (bh - vh) * 0.4), resample=Image.BILINEAR)
                p.stdin.write(fr.tobytes())
            p.stdin.close(); p.wait()
            dt = time.time() - t0
            cores = os.cpu_count() or 2
            per_reel = int(dt * 15 / max(1, cores - 1) * 1.2) + 12
            if dt < 4:
                speed = f"fast: a 15-second reel takes about {per_reel} seconds"
            elif dt < 7:
                speed = f"okay: a 15-second reel takes about {per_reel} seconds; the slow push on photos stays on"
            else:
                speed = "slow: a 15-second reel would take a few minutes, so photos will hold still instead of moving (same cuts)"
            print(f"Speed    {dt:.1f} s to draw one second of video on {cores} cores · {speed}")
        except Exception as e:
            print(f"Speed    couldn't measure ({e.__class__.__name__})")
    print("Everything the reel tool needs is here. Nothing to install." if all_ok else
          "Something the reel tool needs is missing. Screenshot this and send it to support with Mac or PC in the subject.")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
