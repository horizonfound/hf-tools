#!/usr/bin/env python3
"""The Assistant by Horizon Found. Builds a reel from a session folder, cut to the beat.

  python3 make_reel.py --session "<folder>" [--recipe montage|hook-photos|bts|bts-photos]
                       [--song auto|none|<file>] [--song-start 12.5] [--clip <file>] [--clip-sound keep|mute]
                       [--photos 3,1,7 or names] [--beats-per-photo 2] [--max-seconds 20]
                       [--hook "text"] [--hook-kicker "Kira + James"] [--hook-style editorial|clean|label]
                       [--hook-font "cormorant italic"] [--hook-color auto|#hex] [--hook-position auto|upper|middle|lower]
                       [--hook-hold 3] [--hook-persist] [--motion auto|on|off]
                       [--variants hooks.txt] [--name "kira-beach"] [--dry-run] [--no-grade]

Recipes
  montage      photos only, one photo every N beats
  hook-photos  a short talking clip first (the hook), then photos on the beat     (default when a clip exists)
  bts          behind-the-scenes clips only, chopped on the beat
  bts-photos   behind-the-scenes clips on the beat, then photos on the beat

How it gets a professional result, not a slideshow
  - every cut lands on a beat of the song; the opening clip ends on one too
  - photos move with a slow, sub-pixel-smooth push, pull or drift (rendered frame by frame, never jittery)
  - the song is ducked under the talking clip with a smooth curve, the voice is cleaned up, nothing clicks or clips
  - on-screen text is set like a designer would: balanced lines, kept off faces, color and scrim chosen from the frame
  - audio is encoded once, at the end, not three times

Writes only into <session>/_assistant/reel-<name>/. Never touches the originals.
Needs ffmpeg/ffprobe, Python 3, numpy and Pillow. Nothing to install.
"""
import argparse, json, math, os, re, shutil, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import beats as beatlib  # noqa: E402
import hooktext  # noqa: E402

W, H, FPS = 1080, 1920, 30
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".webp"}
CLIP_EXT = {".mp4", ".mov", ".m4v"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".aiff", ".aif", ".flac", ".ogg"}

OVER = 1.14          # photos are prepared this much larger than the frame so motion never shows an edge
PUSH = 0.07          # how far a push-in or pull-out travels over one hold (7%)
ANCHOR_Y = 0.40      # motion and crops hold this point of the photo in place: faces live in the upper middle
SEG_ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "15", "-pix_fmt", "yuv420p", "-r", str(FPS)]
FINAL_ENC = ["-c:v", "libx264", "-preset", "faster", "-crf", "19", "-profile:v", "high", "-pix_fmt", "yuv420p",
             "-r", str(FPS), "-movflags", "+faststart"]


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


def last_err(r):
    s = r.stderr.strip()
    return s.splitlines()[-1] if s else "unknown error"


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

def open_photo(src):
    """Open any photo as RGB with EXIF orientation applied (HEIC through Pillow if it can, else ImageMagick)."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(src)
        im = ImageOps.exif_transpose(im)
        return im.convert("RGB")
    except Exception:
        conv = shutil.which("magick") or shutil.which("convert")
        if conv:
            tmp = Path(str(src) + ".assistant-tmp.jpg")
            r = run([conv, str(src), "-auto-orient", str(tmp)])
            if r.returncode == 0 and tmp.exists():
                try:
                    im = Image.open(tmp).convert("RGB")
                    im.load()
                    return im
                finally:
                    try:
                        tmp.unlink()
                    except OSError:
                        pass
        return None


def prepare_photo(src, over=OVER):
    """Cover-crop the photo to the frame, `over` times larger, anchored so faces stay in. Returns a PIL image and
    whether the source was wide (landscape), which gets a drift instead of a push."""
    from PIL import Image
    im = open_photo(src)
    if im is None:
        return None, False
    bw, bh = int(W * over), int(H * over)
    sw, sh = im.size
    wide = sw / sh > 1.05
    s = max(bw / sw, bh / sh)
    im = im.resize((max(bw, round(sw * s)), max(bh, round(sh * s))), Image.LANCZOS)
    sw, sh = im.size
    x0 = (sw - bw) // 2
    y0 = int((sh - bh) * ANCHOR_Y)
    return im.crop((x0, y0, x0 + bw, y0 + bh)), wide


def motion_for(index, wide):
    """Which move this photo gets. Wide photos drift sideways (there is more picture to show); portraits alternate
    between a push-in and a pull-out so the reel breathes instead of pumping."""
    if wide:
        return "drift"
    return "push" if index % 2 == 0 else "pull"


def view_box(move, f, bw, bh):
    """The part of the prepared photo shown at progress f (0..1): (x, y, w, h) in float pixels."""
    if move == "push":
        z = 1.0 + PUSH * f
    elif move == "pull":
        z = 1.0 + PUSH * (1.0 - f)
    elif move == "drift":
        z = 1.05 + 0.02 * f
    else:
        z = 1.0
    vw, vh = bw / z, bh / z
    if move == "drift":
        x = (bw - vw) * f
    else:
        x = (bw - vw) / 2
    y = (bh - vh) * ANCHOR_Y
    return x, y, vw, vh


def render_photo_job(args):
    """Render one photo hold to an mp4: frames are computed one by one with sub-pixel accuracy (that is what keeps
    the motion smooth) and piped straight into ffmpeg. Runs in a worker process."""
    src, dur, out, move = args
    from PIL import Image
    im, wide = prepare_photo(Path(src))
    if im is None:
        return (out, f"I couldn't open {Path(src).name}. If it's an iPhone HEIC, exporting it as JPEG first will fix it.")
    if move == "auto":
        move = "drift" if wide else "push"
    bw, bh = im.size
    n = max(1, int(round(dur * FPS)))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-an", "-threads", "2"] + SEG_ENC + [str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(n):
            f = i / max(1, n - 1)
            if move == "still":
                x, y, vw, vh = (bw - W) / 2, (bh - H) * ANCHOR_Y, W, H
            else:
                x, y, vw, vh = view_box(move, f, bw, bh)
            fr = im.transform((W, H), Image.AFFINE, (vw / W, 0, x, 0, vh / H, y), resample=Image.BILINEAR)
            p.stdin.write(fr.tobytes())
        p.stdin.close()
        err = p.stderr.read().decode(errors="ignore")
        p.wait()
    except BrokenPipeError:
        err = p.stderr.read().decode(errors="ignore")
        p.wait()
    if p.returncode != 0:
        return (out, "ffmpeg couldn't render a photo: " + (err.strip().splitlines()[-1] if err.strip() else "unknown error"))
    return (out, None)


def probe_motion_speed():
    """Time a few frames of the photo motion. Slow machines get still photos instead (same reel, same cuts)."""
    from PIL import Image
    im = Image.new("RGB", (int(W * OVER), int(H * OVER)), (200, 180, 150))
    t0 = time.time()
    for i in range(6):
        x, y, vw, vh = view_box("push", i / 5, *im.size)
        im.transform((W, H), Image.AFFINE, (vw / W, 0, x, 0, vh / H, y), resample=Image.BILINEAR).tobytes()
    return (time.time() - t0) / 6


# ---------- clips ----------

def clip_filter():
    return (f"scale=w='if(gt(a,{W}/{H}),-2,{W})':h='if(gt(a,{W}/{H}),{H},-2)',"
            f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*0.35,setsar=1,fps={FPS}")


def render_clip(src, start, dur, out):
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.4f}", "-i", str(src), "-t", f"{dur:.4f}", "-vf", clip_filter(),
           "-an"] + SEG_ENC + [str(out)]
    r = run(cmd)
    if r.returncode != 0:
        fail("ffmpeg couldn't cut a clip: " + last_err(r))


def extract_voice(src, start, dur, out_wav):
    """The talking clip's own sound, as a clean WAV, trimmed to the piece we use."""
    r = run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.4f}", "-i", str(src), "-t", f"{dur:.4f}", "-vn",
             "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(out_wav)])
    return out_wav if r.returncode == 0 and out_wav.exists() else None


def mean_volume_db(path):
    r = run(["ffmpeg", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"])
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def concat(segments, out):
    lst = out.parent / "concat.txt"
    lst.write_text("".join("file '" + s.as_posix().replace("'", "'\\''") + "'\n" for s in segments))
    r = run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
    if r.returncode != 0:
        r = run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-an"] + SEG_ENC + [str(out)])
        if r.returncode != 0:
            fail("Couldn't join the pieces: " + last_err(r))


# ---------- audio ----------

def build_audio(song, song_start, total, voice_wav, voice_dur, out_wav):
    """One pass, no clicks, no clipping, encoded once at the very end:
    the song is trimmed from song_start, faded in and out, ducked under the voice with a smooth curve (per
    millisecond, not per frame); the voice gets a high-pass, a gentle compressor, a level match and tiny fades so it
    never cuts off with a pop; a limiter catches the sum. Returns the WAV path or None when there is no sound."""
    if song is None and voice_wav is None:
        return None
    fade_out = min(1.2, max(0.4, total * 0.08))
    st_out = max(0.0, total - fade_out)
    graph, inputs, n = [], [], 0
    fmt = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    labels = []
    if song is not None:
        inputs += ["-i", str(song)]
        duck = "1"
        if voice_wav is not None:
            h, ramp = voice_dur, 0.6
            duck = (f"if(lt(t,{h:.3f}),0.16,if(lt(t,{h + ramp:.3f}),"
                    f"0.16+0.84*(0.5-0.5*cos(PI*(t-{h:.3f})/{ramp})),1))")
        graph.append(f"[{n}:a]atrim={song_start:.3f}:{song_start + total:.3f},asetpts=PTS-STARTPTS,{fmt},"
                     f"asetnsamples=n=48:p=0,volume='{duck}':eval=frame,"
                     f"afade=t=in:st=0:d=0.05,afade=t=out:st={st_out:.3f}:d={fade_out:.3f},apad,atrim=0:{total:.3f}[m]")
        labels.append("[m]")
        n += 1
    if voice_wav is not None:
        inputs += ["-i", str(voice_wav)]
        gain = 0.0
        mv = mean_volume_db(voice_wav)
        if mv is not None:
            gain = max(-6.0, min(12.0, -19.0 - mv))   # bring speech to about -19 dB mean, never more than +12
        vend = max(0.1, voice_dur - 0.12)
        graph.append(f"[{n}:a]{fmt},highpass=f=90,acompressor=threshold=-21dB:ratio=2.5:attack=8:release=120,"
                     f"volume={gain:.1f}dB,afade=t=in:st=0:d=0.04,afade=t=out:st={vend:.3f}:d=0.12,"
                     f"apad,atrim=0:{total:.3f}[v]")
        labels.append("[v]")
        n += 1
    if len(labels) == 2:
        graph.append(f"{labels[0]}{labels[1]}amix=inputs=2:duration=first:normalize=0[mix]")
        last = "[mix]"
    else:
        last = labels[0]
    graph.append(f"{last}alimiter=limit=0.94:attack=4:release=60:level=0[a]")
    r = run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(graph), "-map", "[a]",
             "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(out_wav)])
    if r.returncode != 0:
        say("  (audio mix fell back to the plain song: " + last_err(r) + ")")
        if song is None:
            return None
        r = run(["ffmpeg", "-v", "error", "-y", "-i", str(song), "-af",
                 f"atrim={song_start:.3f}:{song_start + total:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={st_out:.3f}:d={fade_out:.3f}",
                 "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(out_wav)])
        return out_wav if r.returncode == 0 else None
    return out_wav


# ---------- finish ----------

def frame_at(video, t, out_png):
    r = run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(video), "-frames:v", "1", str(out_png)])
    return out_png if r.returncode == 0 and out_png.exists() else None


def finish(base, audio_wav, hook_png, hook_end, persist, out, total, quick=False, end_png=None, end_start=None):
    """Lay the text over the picture with a fade and a small rise, add the sound, encode once."""
    inputs = ["-i", str(base)]
    fc = []
    vlabel = "0:v"
    idx = 1
    if hook_png:
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}", "-i", str(hook_png)]
        fades = "fade=t=in:st=0:d=0.30:alpha=1"
        enable = ""
        if not persist:
            fo = max(0.0, hook_end - 0.25)
            fades += f",fade=t=out:st={fo:.3f}:d=0.25:alpha=1"
            enable = f":enable='lt(t,{hook_end:.3f})'"
        rise = "y='-22*pow(1-min(t/0.45,1),3)'"
        fc.append(f"[{idx}:v]format=rgba,{fades}[hk];[{vlabel}][hk]overlay=x=0:{rise}:shortest=1{enable}[v]")
        vlabel = "v"
        idx += 1
    if end_png and end_start is not None and end_start < total:
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}", "-i", str(end_png)]
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={end_start:.3f}:d=0.4:alpha=1[et];"
                  f"[{vlabel}][et]overlay=x=0:y=0:shortest=1:enable='gte(t,{end_start:.3f})'[ve]")
        vlabel = "ve"
        idx += 1
    cmd = ["ffmpeg", "-v", "error", "-y"] + inputs
    if audio_wav:
        cmd += ["-i", str(audio_wav)]
    if fc:
        cmd += ["-filter_complex", ";".join(fc), "-map", f"[{vlabel}]"]
    else:
        cmd += ["-map", "0:v"]
    if audio_wav:
        cmd += ["-map", f"{idx}:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    enc = [("veryfast" if quick and v == "faster" else v) for v in FINAL_ENC]
    cmd += ["-t", f"{total:.3f}"] + enc + [str(out)]
    r = run(cmd)
    if r.returncode != 0:
        fail("Couldn't finish the reel: " + last_err(r))


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Build a reel from a session folder, cut to the beat.")
    ap.add_argument("--session", required=True)
    ap.add_argument("--recipe", default="auto", choices=["auto", "montage", "hook-photos", "bts", "bts-photos"])
    ap.add_argument("--song", default="auto", help="auto (first audio file in the folder), none, or a file")
    ap.add_argument("--song-start", default="auto", help="auto finds the chorus / the drop; or seconds into the song; 0 for the top")
    ap.add_argument("--clip", default=None, help="the talking / behind-the-scenes clip to open with")
    ap.add_argument("--clip-start", default="auto", help="auto trims the dead air before they start talking; or seconds into the clip")
    ap.add_argument("--rhythm", default="steady", choices=["steady", "build"], help="steady: every photo the same; build: it speeds up toward the end")
    ap.add_argument("--end-text", default=None, help="a small line on the last photo, like their handle or studio name")
    ap.add_argument("--clip-sound", default="keep", choices=["keep", "mute"], help="keep the opening clip's own sound (talking) or mute it")
    ap.add_argument("--photos", default="", help="order: contact-sheet numbers or filenames, comma separated")
    ap.add_argument("--hook", default="", help="on-screen text for the opening")
    ap.add_argument("--hook-kicker", default=None, help="a small line above the hook, like the couple's names or the place")
    ap.add_argument("--hook-style", default="editorial", choices=sorted(hooktext.STYLES))
    ap.add_argument("--hook-font", default=None, help="a bundled font name, or a .ttf path (default: the style's font)")
    ap.add_argument("--hook-color", default="auto", help="auto picks cream or ink from the frame; or a hex color")
    ap.add_argument("--hook-position", default="auto", choices=["auto", "upper", "middle", "lower"])
    ap.add_argument("--hook-hold", type=float, default=3.0, help="seconds the opening clip and hook text hold")
    ap.add_argument("--hook-persist", action="store_true", help="keep the hook text on for the whole reel")
    ap.add_argument("--beats-per-photo", type=int, default=2)
    ap.add_argument("--max-seconds", type=float, default=20.0)
    ap.add_argument("--motion", default="auto", choices=["auto", "on", "off"], help="the slow push/pull/drift on photos")
    ap.add_argument("--zoom", default=None, choices=["auto", "on", "off"], help=argparse.SUPPRESS)  # old name
    ap.add_argument("--variants", default=None, help="a text file, one hook per line: extra reels for trial reels")
    ap.add_argument("--name", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-grade", action="store_true")
    a = ap.parse_args()
    if a.zoom:
        a.motion = a.zoom

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

    # the opening clip: where it starts (trim the dead air) and how long it holds
    clip_start = 0.0
    if clip is not None and recipe == "hook-photos":
        if a.clip_start == "auto":
            if has_audio(clip):
                clip_start = beatlib.first_sound(clip)
                if clip_start > 0.05:
                    say(f"  trimming {clip_start:.1f} s of dead air from the start of {clip.name}")
        else:
            try:
                clip_start = max(0.0, float(a.clip_start))
            except ValueError:
                fail("--clip-start wants auto or a number of seconds.")

    # beats
    song_start = 0.0
    if song:
        info = beatlib.analyze(song)
        if not info["ok"]:
            fail("I couldn't find a steady beat in that song. Try another track, or --song none to cut at an even pace.")
        if a.song_start == "auto":
            need = min(a.max_seconds, (a.hook_hold if recipe == "hook-photos" else 0) + len(chosen) * a.beats_per_photo * info["period"] + 1.0)
            song_start = beatlib.best_start(info, need)
            if song_start > 0:
                say(f"  starting the song at {song_start:.1f} s, where it picks up")
        else:
            try:
                song_start = max(0.0, float(a.song_start))
            except ValueError:
                fail("--song-start wants auto or a number of seconds.")
        if song_start >= info["duration"] - 3:
            fail(f"--song-start {song_start:.1f} is past the end of the song ({info['duration']:.1f} s).")
        beat_times = [round(b - song_start, 3) for b in info["beats"] if b - song_start >= -0.001]
        period = info["period"]
        tempo = info["tempo"]
    else:
        period = 0.6
        tempo = 100.0
        beat_times = [round(i * period, 3) for i in range(int(a.max_seconds / period) + 60)]

    # plan
    plan = {"recipe": recipe, "song": str(song.name) if song else None, "song_start": song_start, "tempo": tempo,
            "beats_per_photo": a.beats_per_photo, "rhythm": a.rhythm, "segments": [], "hook_text": a.hook or None,
            "hook_kicker": a.hook_kicker, "hook_style": a.hook_style, "end_text": a.end_text}
    t = 0.0
    segments = []  # (kind, src, start_in_src, dur, move)
    hook_end = 0.0
    if recipe in ("hook-photos",):
        target = a.hook_hold
        end = min([b for b in beat_times if b >= target - 0.35] or [target])
        end = snap(end)
        segments.append(("clip", clip, clip_start, end, None))
        t = end
        hook_end = end
    if recipe in ("bts", "bts-photos"):
        srcs = [clip] if clip else clips
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
                segments.append(("clip", src, start_in, snap(piece), None))
                t = snap(t + piece)
        hook_end = snap(min(a.hook_hold, t)) if a.hook else 0.0
    if recipe in ("hook-photos", "montage", "bts-photos"):
        next_beats = [b for b in beat_times if b >= t - 0.02]
        if not next_beats:
            fail("The song is shorter than the opening clip.")
        if t > 0 and abs(next_beats[0] - t) > 0.02:
            kind, src, s0, d0, mv = segments[-1]
            segments[-1] = (kind, src, s0, snap(d0 + (next_beats[0] - t)), mv)
            t = snap(next_beats[0])
        i = 0
        # a montage with text opens on one photo held long enough to read it (about hook_hold, on the beat)
        first_beats = a.beats_per_photo
        if recipe == "montage" and (a.hook or a.variants) and period > 0:
            first_beats = max(a.beats_per_photo, int(round(a.hook_hold / period)))
        # "build": the same opening, then the photos come faster toward the end, and the last one settles
        pattern = None
        if a.rhythm == "build" and len(chosen) >= 4:
            bp = a.beats_per_photo
            quick = max(1, bp // 2)
            rest = len(chosen) - 1
            pattern = [bp] * max(1, rest // 2) + [quick] * max(0, rest - rest // 2 - 1) + [bp]
        for k, p in enumerate(chosen):
            nb = first_beats if k == 0 else (pattern[k - 1] if pattern and k - 1 < len(pattern) else a.beats_per_photo)
            if i + nb >= len(next_beats):
                break
            start, end = next_beats[i], next_beats[i + nb]
            if end > a.max_seconds + 0.01:
                break
            segments.append(("photo", p, 0.0, snap(end - start), "push" if k % 2 == 0 else "pull"))
            t = snap(end)
            i += nb
        if recipe == "montage" and (a.hook or a.variants) and segments:
            hook_end = segments[0][3]
    total = snap(sum(s[3] for s in segments))
    if total < 2:
        fail("That would be a very short reel. Add more photos, a longer song, or more beats per photo.")
    for kind, src, s0, d, mv in segments:
        plan["segments"].append({"kind": kind, "file": src.name, "start_in_source": round(s0, 3), "seconds": round(d, 3),
                                 "motion": mv})
    plan["total_seconds"] = total
    plan["hook_end"] = hook_end
    (outdir / "plan.json").write_text(json.dumps(plan, indent=2))

    nphotos = sum(1 for s in segments if s[0] == "photo")
    nclips = sum(1 for s in segments if s[0] == "clip")
    say(f"Plan: {recipe} · {total:.1f} s · {nclips} clip piece(s) + {nphotos} photos · ~{tempo:.0f} bpm, every {a.beats_per_photo} beats"
        + (f" · song: {song.name}" + (f" from {song_start:.1f}s" if song_start else "") if song else " · no song (even pace; add audio in Instagram)"))
    if a.dry_run:
        for s in plan["segments"]:
            say(f"  {s['kind']:5} {s['file']:30} {s['seconds']:.2f}s  {s['motion'] or ''}")
        say(f"Plan saved to {outdir / 'plan.json'}. Nothing rendered.")
        return

    # motion speed check
    motion = a.motion == "on"
    if a.motion == "auto":
        per_frame = probe_motion_speed()
        motion = per_frame < 0.22
        if not motion:
            say(f"This computer is on the slower side ({per_frame * 1000:.0f} ms a frame), so the photos will hold still instead of the slow push. Same reel, same cuts.")

    # render pieces: clips one by one, photos in parallel
    t0 = time.time()
    parts = [None] * len(segments)
    voice_wav = None
    jobs = []
    for n, (kind, src, s0, d, mv) in enumerate(segments):
        out = work / f"seg_{n:03d}.mp4"
        parts[n] = out
        if kind == "photo":
            jobs.append((str(src), d, str(out), (mv or "push") if motion else "still"))
        else:
            render_clip(src, s0, d, out)
            if recipe == "hook-photos" and n == 0 and a.clip_sound == "keep" and has_audio(src):
                voice_wav = extract_voice(src, s0, d, work / "voice.wav")
            say(f"  {n + 1}/{len(segments)} clip {src.name} ({d:.2f}s)")
    if jobs:
        workers = max(1, min(len(jobs), (os.cpu_count() or 2) - 1))
        say(f"  rendering {len(jobs)} photos with {'motion' if motion else 'no motion'} ({workers} at a time)...")
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for out, err in ex.map(render_photo_job, jobs):
                if err:
                    fail(err)
        say(f"  photos done ({time.time() - t0:.0f} s so far)")
    base = work / "base.mp4"
    concat(parts, base)

    audio_wav = build_audio(song, song_start, total, voice_wav, hook_end if voice_wav else 0.0, work / "audio.wav")

    # on-screen text: decided from the actual frame it will sit on
    hook_png = None
    behind = None
    if a.hook or a.variants:
        mid = (hook_end / 2) if hook_end else min(a.hook_hold, total) / 2
        png = frame_at(base, max(0.1, mid), work / "behind.png")
        if png:
            from PIL import Image
            behind = Image.open(png).convert("RGB")
    if a.hook:
        hook_png = work / "hook.png"
        d = hooktext.render(a.hook, hook_png, a.hook_style, a.hook_font, a.hook_color, a.hook_position, a.hook_kicker, behind)
        (work / "hook.json").write_text(json.dumps(d, indent=2))
        say(f"  hook text: {len(d['lines'])} line(s), {d['style']} {d['size']}px, {d['position']} third, {d['color']}"
            + (f", soft scrim {d['scrim']}" if d['scrim'] else "") + f", holds {hook_end:.1f}s" + (" and stays on" if a.hook_persist else ""))
        if hook_end == 0:
            hook_end = snap(min(a.hook_hold, total))

    end_png = end_start = None
    if a.end_text and len(segments) >= 2:
        end_start = snap(total - segments[-1][3])
        last_png = frame_at(base, end_start + segments[-1][3] / 2, work / "behind_end.png")
        from PIL import Image
        end_png = work / "end.png"
        hooktext.render(a.end_text, end_png, "clean", None, a.hook_color, "lower", None,
                        Image.open(last_png).convert("RGB") if last_png else None, size=34)

    final = outdir / f"{name}.mp4"
    finish(base, audio_wav, hook_png, hook_end, a.hook_persist, final, total, end_png=end_png, end_start=end_start)
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
                hooktext.render(line, png, a.hook_style, a.hook_font, a.hook_color, a.hook_position, a.hook_kicker, behind)
                vout = outdir / f"{name}-trial-{i}.mp4"
                finish(base, audio_wav, png, hook_end or snap(min(a.hook_hold, total)), a.hook_persist, vout, total, quick=True,
                       end_png=end_png, end_start=end_start)
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
        for l in report.splitlines():
            if l.startswith("  - "):
                say(l)

    # tidy
    for p in list(work.glob("seg_*.mp4")) + [work / "voice.wav"]:
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
