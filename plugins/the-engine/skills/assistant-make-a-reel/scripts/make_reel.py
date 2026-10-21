#!/usr/bin/env python3
"""The Assistant by Horizon Found. Builds a reel from a session folder, cut to the beat.

  python3 make_reel.py --session "<folder>" [--recipe montage|hook-photos|bts|bts-photos]
                       [--song auto|none|<file>] [--clip <file>] [--photos 3,1,7 or names]
                       [--hook "text"] [--hook-font Cormorant] [--hook-color "#F5F4ED"]
                       [--hook-position upper|middle|lower] [--hook-hold 3] [--hook-persist]
                       [--beats-per-photo 2] [--max-seconds 20] [--zoom auto|on|off]
                       [--variants hooks.txt] [--name "kira-beach"] [--dry-run]

Recipes
  montage      photos only, one photo every N beats
  hook-photos  a short talking clip first (the hook), then photos on the beat     (default when a clip exists)
  bts          behind-the-scenes clips only, chopped on the beat
  bts-photos   behind-the-scenes clips on the beat, then photos on the beat

Writes only into <session>/_assistant/reel-<name>/. Never touches the originals.
Needs ffmpeg/ffprobe, Python 3, numpy and Pillow. Nothing to install.
"""
import argparse, json, math, os, re, shutil, subprocess, sys, time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import beats as beatlib  # noqa: E402

W, H, FPS = 1080, 1920, 30
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".webp"}
CLIP_EXT = {".mp4", ".mov", ".m4v"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".aiff", ".aif", ".flac", ".ogg"}
FONTS = HERE.parent.parent.parent / "shared" / "fonts"
FONT_NAMES = {
    "cormorant": "CormorantGaramond-Light.ttf", "cormorant italic": "CormorantGaramond-LightItalic.ttf",
    "cormorant regular": "CormorantGaramond-Regular.ttf", "montserrat": "Montserrat-Regular.ttf",
    "montserrat semibold": "Montserrat-SemiBold.ttf", "dm sans": "DMSans-Regular.ttf",
    "dm sans semibold": "DMSans-SemiBold.ttf", "inter": "Inter-Regular.ttf", "inter bold": "Inter-Bold.ttf",
    "fraunces": "Fraunces-Regular.ttf", "fraunces italic": "Fraunces-Italic.ttf",
}


def say(msg):
    print(msg, flush=True)


def fail(msg, code=1):
    say(msg)
    sys.exit(code)


def run(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 and not quiet:
        say(r.stderr[-800:])
    return r


def ffprobe_json(path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {}


def has_audio(path):
    return any(s.get("codec_type") == "audio" for s in ffprobe_json(path).get("streams", []))


def natural_key(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def slug(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "reel"


def snap(t):
    """Snap a time to the frame grid."""
    return round(round(t * FPS) / FPS, 4)


# ---------- inventory ----------

def inventory(session):
    files = [p for p in session.iterdir() if p.is_file() and not p.name.startswith(".") and not p.name.startswith("_")]
    photos = sorted([p for p in files if p.suffix.lower() in PHOTO_EXT], key=natural_key)
    clips = sorted([p for p in files if p.suffix.lower() in CLIP_EXT], key=natural_key)
    audio = sorted([p for p in files if p.suffix.lower() in AUDIO_EXT], key=natural_key)
    return photos, clips, audio


def load_sheet_numbers(session):
    """If the contact sheet has been made, numbers map to filenames."""
    js = session / "_assistant" / "contact-sheet.json"
    if js.exists():
        try:
            data = json.loads(js.read_text())
            items = data.get("photos") or data.get("items") or data
            out = {}
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict) and "index" in it and "file" in it:
                        out[int(it["index"])] = it["file"]
            elif isinstance(items, dict):
                for k, v in items.items():
                    try:
                        out[int(k)] = v if isinstance(v, str) else v.get("file")
                    except (ValueError, AttributeError):
                        pass
            return out
        except Exception:
            return {}
    return {}


def pick_photos(session, photos, spec):
    if not spec:
        return photos
    numbers = load_sheet_numbers(session)
    byname = {p.name.lower(): p for p in photos}
    chosen = []
    for tok in [t.strip() for t in spec.split(",") if t.strip()]:
        if tok.isdigit():
            n = int(tok)
            name = numbers.get(n)
            if name and name.lower() in byname:
                chosen.append(byname[name.lower()])
            elif 1 <= n <= len(photos):
                chosen.append(photos[n - 1])
            else:
                fail(f"There is no photo number {n} (the folder has {len(photos)}). Run contact_sheet.py to see the numbers.")
        else:
            p = byname.get(tok.lower())
            if not p:
                fail(f"I can't find a photo called {tok} in the session folder.")
            chosen.append(p)
    return chosen


# ---------- photos ----------

def to_jpeg(src, workdir):
    """Make a plain JPEG copy ffmpeg can read (HEIC and friends), EXIF orientation applied. Returns path."""
    from PIL import Image, ImageOps
    out = workdir / (src.stem + ".jpg")
    try:
        im = Image.open(src)
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        im.save(out, quality=94)
        return out
    except Exception:
        conv = shutil.which("magick") or shutil.which("convert")
        if conv:
            r = run([conv, str(src), "-auto-orient", str(out)])
            if r.returncode == 0 and out.exists():
                return out
        return None


# ---------- hook text ----------

def font_path(name):
    if not name:
        name = "cormorant"
    p = Path(name)
    if p.suffix.lower() in (".ttf", ".otf") and p.exists():
        return p
    key = name.lower().strip()
    if key in FONT_NAMES:
        return FONTS / FONT_NAMES[key]
    for k, v in FONT_NAMES.items():
        if key in k:
            return FONTS / v
    fail(f"I don't have a font called {name}. Bundled: " + ", ".join(sorted(set(k for k in FONT_NAMES))))


def render_hook_png(text, out, font_name, color, position, size=None):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    fp = font_path(font_name)
    size = size or 72
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    maxw = int(W * 0.82)
    lines = []
    while True:
        font = ImageFont.truetype(str(fp), size)
        lines = []
        for para in text.replace(" / ", "\n").split("\n"):
            words = para.split()
            cur = ""
            for w in words:
                trial = (cur + " " + w).strip()
                if draw.textlength(trial, font=font) <= maxw:
                    cur = trial
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
        if len(lines) <= 3 or size <= 40:
            break
        size -= 4
    lh = int(size * 1.18)
    block = lh * len(lines)
    # safe zones: keep out of Instagram's top 250 and bottom 300 px
    if position == "upper":
        y0 = int(H * 0.22)
    elif position == "lower":
        y0 = int(H * 0.72) - block
    else:
        y0 = (H - block) // 2
    y0 = max(260, min(y0, H - 320 - block))
    # soft shadow for legibility on sunny photos, never a box
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for i, line in enumerate(lines):
        tw = draw.textlength(line, font=font)
        x = (W - tw) / 2
        sd.text((x + 2, y0 + i * lh + 3), line, font=font, fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    img = Image.alpha_composite(img, shadow)
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        tw = draw.textlength(line, font=font)
        draw.text(((W - tw) / 2, y0 + i * lh), line, font=font, fill=color)
    img.save(out)
    return lines, size


# ---------- rendering ----------

ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart"]


def photo_filter(dur, zoom):
    cover = f"scale=w='if(gt(a,{W}/{H}),-2,{W})':h='if(gt(a,{W}/{H}),{H},-2)',crop={W}:{H}:(iw-{W})/2:(ih-{H})*0.40"
    if zoom:
        # feed zoompan a 20% larger frame so the push-in never goes soft; top-biased so faces stay in
        bw, bh = int(W * 1.2), int(H * 1.2)
        big = (f"scale=w='if(gt(a,{W}/{H}),-2,{bw})':h='if(gt(a,{W}/{H}),{bh},-2)',crop={bw}:{bh}:(iw-{bw})/2:(ih-{bh})*0.40")
        frames = max(1, int(round(dur * FPS)))
        zp = (f"zoompan=z='min(1+0.10*on/{frames},1.10)':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*0.40'"
              f":d=1:s={W}x{H}:fps={FPS}")
        return f"{big},{zp},setsar=1"
    return f"{cover},setsar=1,fps={FPS}"


def render_photo(jpg, dur, out, zoom):
    cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.4f}", "-i", str(jpg),
           "-vf", photo_filter(dur, zoom), "-t", f"{dur:.4f}", "-an"] + ENC + [str(out)]
    r = run(cmd)
    if r.returncode != 0:
        fail("ffmpeg couldn't render a photo: " + (r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "unknown error"))


def clip_filter():
    return (f"scale=w='if(gt(a,{W}/{H}),-2,{W})':h='if(gt(a,{W}/{H}),{H},-2)',"
            f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*0.35,setsar=1,fps={FPS}")


def render_clip(src, start, dur, out, keep_audio):
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.4f}", "-i", str(src), "-t", f"{dur:.4f}", "-vf", clip_filter()]
    if keep_audio:
        cmd += ["-c:a", "aac", "-ar", "48000", "-ac", "2"]
    else:
        cmd += ["-an"]
    cmd += ENC + [str(out)]
    r = run(cmd)
    if r.returncode != 0:
        fail("ffmpeg couldn't cut a clip: " + (r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "unknown error"))


def concat(segments, out):
    lst = out.parent / "concat.txt"
    lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in segments))
    r = run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
    if r.returncode != 0:
        # fall back to re-encode if stream params differ
        r = run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-an"] + ENC + [str(out)])
        if r.returncode != 0:
            fail("Couldn't join the pieces: " + (r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "unknown error"))


def build_audio(song, total, hook_clip_seg, hook_dur, out):
    """Song trimmed to length with a fade-out; if the hook clip has sound, it plays over a ducked song."""
    fade_start = max(0.0, total - 1.0)
    if song is None and hook_clip_seg is None:
        return None
    if song is None:
        # just the clip's own sound, padded to the full length
        r = run(["ffmpeg", "-v", "error", "-y", "-i", str(hook_clip_seg), "-vn", "-af", f"apad,atrim=0:{total:.4f}",
                 "-c:a", "aac", "-b:a", "160k", str(out)])
        return out if r.returncode == 0 else None
    if hook_clip_seg is None:
        af = f"atrim=0:{total:.4f},afade=t=out:st={fade_start:.3f}:d=1"
        r = run(["ffmpeg", "-v", "error", "-y", "-i", str(song), "-vn", "-af", af, "-c:a", "aac", "-b:a", "160k", str(out)])
        return out if r.returncode == 0 else None
    # duck the song under the talking clip, then bring it up over half a second
    duck = (f"[0:a]atrim=0:{total:.4f},volume='if(lt(t,{hook_dur:.3f}),0.18,if(lt(t,{hook_dur + 0.5:.3f}),"
            f"0.18+0.82*(t-{hook_dur:.3f})/0.5,1))':eval=frame,afade=t=out:st={fade_start:.3f}:d=1[m];"
            f"[1:a]apad,atrim=0:{total:.4f}[v];[m][v]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
    r = run(["ffmpeg", "-v", "error", "-y", "-i", str(song), "-i", str(hook_clip_seg), "-filter_complex", duck,
             "-map", "[a]", "-c:a", "aac", "-b:a", "160k", str(out)])
    return out if r.returncode == 0 else None


def finish(base, audio, hook_png, hook_end, persist, out, total=None):
    inputs = ["-i", str(base)]
    fc = []
    vlabel = "0:v"
    idx = 1
    if hook_png:
        # loop the still so the fade has frames to work on (a one-frame input would fade to nothing and stay there)
        span = total if total else (hook_end + 1.0)
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{span:.3f}", "-i", str(hook_png)]
        enable = "" if persist else f":enable='lt(t,{hook_end:.3f})'"
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st=0:d=0.3:alpha=1[hk];[0:v][hk]overlay=0:0{enable}[v]")
        vlabel = "v"
        idx += 1
    cmd = ["ffmpeg", "-v", "error", "-y"] + inputs
    if audio:
        cmd += ["-i", str(audio)]
    if fc:
        cmd += ["-filter_complex", ";".join(fc), "-map", f"[{vlabel}]"]
    else:
        cmd += ["-map", "0:v"]
    if audio:
        cmd += ["-map", f"{idx}:a", "-c:a", "aac", "-b:a", "160k"]
    cmd += ["-shortest"] + ENC + [str(out)]
    r = run(cmd)
    if r.returncode != 0:
        fail("Couldn't finish the reel: " + (r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "unknown error"))


def probe_speed(workdir):
    """Encode half a second with the zoom filter and time it. Slow machines get still photos instead of the push-in."""
    from PIL import Image
    test = workdir / "_probe.jpg"
    Image.new("RGB", (1440, 2560), (200, 180, 150)).save(test, quality=80)
    out = workdir / "_probe.mp4"
    t0 = time.time()
    render_photo(test, 0.5, out, zoom=True)
    dt = time.time() - t0
    for p in (test, out):
        try:
            p.unlink()
        except OSError:
            pass
    return dt


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Build a reel from a session folder, cut to the beat.")
    ap.add_argument("--session", required=True)
    ap.add_argument("--recipe", default="auto", choices=["auto", "montage", "hook-photos", "bts", "bts-photos"])
    ap.add_argument("--song", default="auto", help="auto (first audio file in the folder), none, or a file")
    ap.add_argument("--clip", default=None, help="the talking / behind-the-scenes clip to open with")
    ap.add_argument("--photos", default="", help="order: contact-sheet numbers or filenames, comma separated")
    ap.add_argument("--hook", default="", help="on-screen text for the opening")
    ap.add_argument("--hook-font", default="Cormorant")
    ap.add_argument("--hook-color", default="#F5F4ED")
    ap.add_argument("--hook-position", default="upper", choices=["upper", "middle", "lower"])
    ap.add_argument("--hook-hold", type=float, default=3.0, help="seconds the opening clip and hook text hold")
    ap.add_argument("--hook-persist", action="store_true", help="keep the hook text on for the whole reel")
    ap.add_argument("--beats-per-photo", type=int, default=2)
    ap.add_argument("--max-seconds", type=float, default=20.0)
    ap.add_argument("--zoom", default="auto", choices=["auto", "on", "off"])
    ap.add_argument("--variants", default=None, help="a text file, one hook per line: extra reels for trial reels")
    ap.add_argument("--name", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-grade", action="store_true")
    a = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            fail(f"{tool} isn't available in this workspace, so I can't build video here. Run check_setup.py for details.")

    session = Path(a.session).expanduser().resolve()
    if not session.is_dir():
        fail(f"I can't find a folder at {session}")
    photos, clips, audio = inventory(session)
    if not photos and not clips:
        fail("That folder has no photos or clips in it (looking for jpg, png, heic, mp4, mov at the top level).")

    name = slug(a.name or session.name)
    outdir = session / "_assistant" / f"reel-{name}"
    work = outdir / "work"
    work.mkdir(parents=True, exist_ok=True)

    # song
    song = None
    if a.song == "none":
        song = None
    elif a.song == "auto":
        song = audio[0] if audio else None
    else:
        song = Path(a.song).expanduser()
        if not song.exists():
            song = session / a.song
        if not song.exists():
            fail(f"I can't find the song at {a.song}")

    # recipe
    recipe = a.recipe
    clip = Path(a.clip).expanduser() if a.clip else None
    if clip and not clip.exists():
        clip = session / a.clip
    if recipe == "auto":
        recipe = "hook-photos" if (clips and photos) else ("montage" if photos else "bts")
    if recipe in ("hook-photos", "bts", "bts-photos") and not clips and not clip:
        fail("That recipe needs a clip, and the folder has none. Try --recipe montage for photos only.")
    if recipe in ("hook-photos", "montage", "bts-photos") and not photos:
        fail("That recipe needs photos, and the folder has none.")
    if recipe in ("hook-photos",) and clip is None:
        clip = clips[0]

    chosen = pick_photos(session, photos, a.photos)

    # beats
    if song:
        info = beatlib.analyze(song)
        if not info["ok"]:
            fail("I couldn't find a steady beat in that song. Try another track, or --song none to cut at an even pace.")
        beat_times = info["beats"]
        period = info["period"]
        tempo = info["tempo"]
    else:
        period = 0.6
        tempo = 100.0
        beat_times = [round(i * period, 3) for i in range(int(a.max_seconds / period) + 60)]

    # plan
    plan = {"recipe": recipe, "song": str(song.name) if song else None, "tempo": tempo, "beats_per_photo": a.beats_per_photo,
            "segments": [], "hook_text": a.hook or None}
    t = 0.0
    segments = []  # (kind, src, start_in_src, dur)
    hook_end = 0.0
    if recipe in ("hook-photos",):
        # the clip holds for ~hook_hold, ending on a beat
        target = a.hook_hold
        end = min([b for b in beat_times if b >= target - 0.35] or [target])
        end = snap(end)
        segments.append(("clip", clip, 0.0, end))
        t = end
        hook_end = end
    if recipe in ("bts", "bts-photos"):
        srcs = [clip] if clip else clips
        # chop each clip into beat-length pieces, spread across the clip, until budget is used
        budget = a.max_seconds if recipe == "bts" else min(a.max_seconds * 0.5, 8.0)
        piece = period * a.beats_per_photo
        for src in srcs:
            d = beatlib.duration_of(src)
            n_pieces = max(1, int(min(budget, d) / piece))
            for i in range(n_pieces):
                if t + piece > budget + 0.01:
                    break
                start_in = (d / n_pieces) * i
                start_in = min(start_in, max(0.0, d - piece))
                segments.append(("clip", src, start_in, snap(piece)))
                t = snap(t + piece)
        hook_end = snap(min(a.hook_hold, t)) if a.hook else 0.0
    if recipe in ("hook-photos", "montage", "bts-photos"):
        # photos start on the first beat at or after t, each held beats_per_photo beats
        next_beats = [b for b in beat_times if b >= t - 0.02]
        if not next_beats:
            fail("The song is shorter than the opening clip.")
        if t > 0 and abs(next_beats[0] - t) > 0.02:
            # stretch the last segment to land on the beat
            kind, src, s0, d0 = segments[-1]
            segments[-1] = (kind, src, s0, snap(d0 + (next_beats[0] - t)))
            t = snap(next_beats[0])
        i = 0
        for p in chosen:
            if i + a.beats_per_photo >= len(next_beats):
                break
            start, end = next_beats[i], next_beats[i + a.beats_per_photo]
            if end > a.max_seconds + 0.01:
                break
            segments.append(("photo", p, 0.0, snap(end - start)))
            t = snap(end)
            i += a.beats_per_photo
        if recipe == "montage" and a.hook:
            hook_end = snap(min(a.hook_hold, t))
    total = snap(sum(s[3] for s in segments))
    if total < 2:
        fail("That would be a very short reel. Add more photos, a longer song, or more beats per photo.")
    for kind, src, s0, d in segments:
        plan["segments"].append({"kind": kind, "file": src.name, "start_in_source": round(s0, 3), "seconds": round(d, 3)})
    plan["total_seconds"] = total
    plan["hook_end"] = hook_end
    (outdir / "plan.json").write_text(json.dumps(plan, indent=2))

    nphotos = sum(1 for s in segments if s[0] == "photo")
    nclips = sum(1 for s in segments if s[0] == "clip")
    say(f"Plan: {recipe} · {total:.1f} s · {nclips} clip piece(s) + {nphotos} photos · ~{tempo:.0f} bpm, every {a.beats_per_photo} beats"
        + (f" · song: {song.name}" if song else " · no song (even pace; add audio in Instagram)"))
    if a.dry_run:
        for s in plan["segments"]:
            say(f"  {s['kind']:5} {s['file']:30} {s['seconds']:.2f}s")
        say(f"Plan saved to {outdir / 'plan.json'}. Nothing rendered.")
        return

    # speed check
    zoom = a.zoom == "on"
    if a.zoom == "auto":
        dt = probe_speed(work)
        zoom = dt < 4.0
        if not zoom:
            say(f"This computer is on the slower side ({dt:.1f} s for a half-second test), so the photos will hold still instead of the slow push-in. Same reel, same cuts.")

    # render pieces
    t0 = time.time()
    parts = []
    hook_clip_seg = None
    for n, (kind, src, s0, d) in enumerate(segments):
        out = work / f"seg_{n:03d}.mp4"
        if kind == "photo":
            jpg = to_jpeg(src, work)
            if jpg is None:
                fail(f"I couldn't open {src.name}. If it's an iPhone HEIC, exporting it as JPEG first will fix it.")
            render_photo(jpg, d, out, zoom)
        else:
            keep = (recipe == "hook-photos" and n == 0 and has_audio(src))
            render_clip(src, s0, d, out, keep_audio=False)
            if keep:
                hook_clip_seg = work / "hook_audio.mp4"
                render_clip(src, s0, d, hook_clip_seg, keep_audio=True)
        parts.append(out)
        say(f"  {n + 1}/{len(segments)} {kind} {src.name} ({d:.2f}s)")
    base = work / "base.mp4"
    concat(parts, base)

    audio_path = build_audio(song, total, hook_clip_seg, hook_end if hook_clip_seg else 0.0, work / "audio.m4a")

    hook_png = None
    if a.hook:
        hook_png = work / "hook.png"
        lines, size = render_hook_png(a.hook, hook_png, a.hook_font, a.hook_color, a.hook_position)
        say(f"  hook text: {len(lines)} line(s) at {size} px, {a.hook_position} third, holds {hook_end:.1f}s" + (" and stays on" if a.hook_persist else ""))
        if hook_end == 0:
            hook_end = snap(min(a.hook_hold, total))

    final = outdir / f"{name}.mp4"
    finish(base, audio_path, hook_png, hook_end, a.hook_persist, final, total)
    say(f"Rendered in {time.time() - t0:.0f} s: {final}")

    # variants for trial reels
    if a.variants:
        vfile = Path(a.variants).expanduser()
        if not vfile.exists():
            vfile = session / a.variants
        if vfile.exists():
            lines = [l.strip() for l in vfile.read_text(encoding="utf-8").splitlines() if l.strip()]
            for i, line in enumerate(lines, 1):
                png = work / f"hook_v{i}.png"
                render_hook_png(line, png, a.hook_font, a.hook_color, a.hook_position)
                vout = outdir / f"{name}-trial-{i}.mp4"
                finish(base, audio_path, png, hook_end or snap(min(a.hook_hold, total)), a.hook_persist, vout, total)
                say(f"  trial reel {i}: {vout.name}  \"{line}\"")
        else:
            say(f"  (couldn't find the variants file {a.variants}; skipped)")

    # grade
    if not a.no_grade and (HERE / "grade_reel.py").exists():
        r = subprocess.run([sys.executable, str(HERE / "grade_reel.py"), str(final)], capture_output=True, text=True)
        report = r.stdout.strip()
        (outdir / "report.txt").write_text(report + "\n")
        grade_line = [l for l in report.splitlines() if l.startswith("GRADE")]
        summary = [l for l in report.splitlines() if " cuts " in l or "cuts ·" in l]
        say("Check: " + (summary[0] if summary else "") + ("  " + grade_line[0] if grade_line else ""))

    # tidy
    for p in work.glob("seg_*.mp4"):
        try:
            p.unlink()
        except OSError:
            pass
    say("Nothing has been posted. The originals were not touched.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
