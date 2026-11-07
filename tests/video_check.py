#!/usr/bin/env python3
"""The reel's video helper (assistant-make-a-reel/scripts/video.py) on a Mac, on clips this test makes itself.

    python3 tests/video_check.py [--work <scratch folder>]

The clips (made here with the Mac's own AVFoundation, nothing installed; never a client's, never HEVC, never 4K,
never longer than 10 seconds or wider than 720 px):
  clip.mov              6 s, 640 x 360, H.264, 30 a second: one solid colour each second (red, green, blue, yellow,
                        purple, cyan) with a white block in its top-left corner as stored; a tone that is quiet for
                        3 s and then loud; the phone's own recording time (com.apple.quicktime.creationdate)
  sideways.mov          the same picture stored as it is but turned 90 degrees to be shown (like a phone filming
                        upright): shown 360 x 640
  Café shoot é.mp4      the same, as an MP4, with an accent and a space in its name
  square.mov            2 s, 720 x 720 (its short side over 540, so its copy is made smaller)
  moov-first.mov        clip.mov rearranged: the movie header first, the picture data last with "to the end" size
  big-box.mov           clip.mov with its picture data in a 64-bit box
and things that are not videos: a text file called .mov, an empty .mp4, a JPEG called .mov, a song (.m4a), and
clip.mov cut off half way.

Checks: the facts against AVFoundation's own (length, size shown, turn, kind, frames a second, sound, recording
time); stills checked by their colour at known times, upright, labelled with the time really returned, never
enlarged, every look in a new folder; the loud stretch found within one half second; the copy made once, never
over a file, never enlarged, upright, and read back by AVFoundation; the PC route (ASSISTANT_NO_AVFOUNDATION=1)
saying its plain words and making nothing; a non-video refused in plain words.

Run it under the memory guard (it touches video). Every line says PASS, FAIL or SKIP. Exit 1 only when something
FAILED; the scratch folder is kept then.
"""
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
sys.path.insert(0, str(REEL))
import video  # noqa: E402
import this_computer  # noqa: E402  (video.py put studio-manager/scripts on the path)
import pictures  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RESULTS = {"PASS": 0, "FAIL": 0, "SKIP": 0}


def check(what, ok, detail=""):
    RESULTS["PASS" if ok else "FAIL"] += 1
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:500]}]" if detail and not ok else ""), flush=True)
    return ok


def skip(what, why):
    RESULTS["SKIP"] += 1
    print(f"SKIP  {what}   [{why}]", flush=True)


COLOURS = [(230, 40, 40), (40, 190, 70), (40, 80, 230), (240, 210, 40), (160, 50, 190), (40, 200, 210)]
RECORDED = "2026-11-06T10:12:33-0800"

MAKE_JS = r"""
ObjC.import('AVFoundation'); ObjC.import('CoreVideo'); ObjC.import('CoreMedia'); ObjC.import('CoreGraphics'); ObjC.import('Foundation');
function C(n) { return $.NSClassFromString(n); }
function wait(flag) { var t0 = Date.now(); while (!flag() && Date.now() - t0 < 120000) $.NSRunLoop.currentRunLoop.runUntilDate($.NSDate.dateWithTimeIntervalSinceNow(0.02)); }
// picture <out.mov> <w> <h> <seconds> <fps> <colours as r,g,b;r,g,b...>: one solid colour a second, white block top-left
function picture(out, W, H, secs, fps, cols) {
  var err = Ref();
  var w = C('AVAssetWriter').assetWriterWithURLFileTypeError($.NSURL.fileURLWithPath(out), 'com.apple.quicktime-movie', err);
  var inp = C('AVAssetWriterInput').assetWriterInputWithMediaTypeOutputSettings('vide', $.NSDictionary.dictionaryWithDictionary({AVVideoCodecKey: 'avc1', AVVideoWidthKey: W, AVVideoHeightKey: H}));
  inp.expectsMediaDataInRealTime = false;
  var attrs = $.NSDictionary.dictionaryWithDictionary({PixelFormatType: 0x42475241, Width: W, Height: H});
  var ad = C('AVAssetWriterInputPixelBufferAdaptor').assetWriterInputPixelBufferAdaptorWithAssetWriterInputSourcePixelBufferAttributes(inp, attrs);
  w.addInput(inp); w.startWriting; w.startSessionAtSourceTime($.CMTimeMake(0, fps));
  var cs = $.CGColorSpaceCreateWithName($('kCGColorSpaceSRGB'));
  for (var i = 0; i < Math.round(secs * fps); i++) {
    while (!inp.readyForMoreMediaData) $.NSThread.sleepForTimeInterval(0.005);
    var r = Ref(); $.CVPixelBufferCreate(null, W, H, 0x42475241, attrs, r); var pb = r[0];
    $.CVPixelBufferLockBaseAddress(pb, 0);
    var ctx = $.CGBitmapContextCreate($.CVPixelBufferGetBaseAddress(pb), W, H, 8, $.CVPixelBufferGetBytesPerRow(pb), cs, 2 | 8192);
    var c = cols[Math.floor(i / fps) % cols.length];
    $.CGContextSetRGBFillColor(ctx, c[0] / 255, c[1] / 255, c[2] / 255, 1); $.CGContextFillRect(ctx, $.CGRectMake(0, 0, W, H));
    $.CGContextSetRGBFillColor(ctx, 1, 1, 1, 1); $.CGContextFillRect(ctx, $.CGRectMake(0, H - H / 4, W / 4, H / 4));
    $.CGContextRelease(ctx); $.CVPixelBufferUnlockBaseAddress(pb, 0);
    if (!ad.appendPixelBufferWithPresentationTime(pb, $.CMTimeMake(i, fps))) throw new Error('append ' + i);
    $.CVPixelBufferRelease(pb);
  }
  inp.markAsFinished; var done = false; w.finishWritingWithCompletionHandler(function () { done = true; }); wait(function () { return done; });
  if (Number(w.status) !== 2) throw new Error('writer ' + w.status);
  return 'ok';
}
// compose <picture.mov> <sound.m4a|-> <out> <turn 0|90> <recorded|->: picture and sound into one file, as a phone stores it
function compose(pic, snd, out, rot, when) {
  var vA = C('AVURLAsset').URLAssetWithURLOptions($.NSURL.fileURLWithPath(pic), $.NSDictionary.dictionary);
  var comp = C('AVMutableComposition').composition, e = Ref();
  var vt = vA.tracksWithMediaType('vide').objectAtIndex(0);
  var cv = comp.addMutableTrackWithMediaTypePreferredTrackID('vide', 0);
  if (!cv.insertTimeRangeOfTrackAtTimeError(vt.timeRange, vt, $.kCMTimeZero, e)) throw new Error('video insert');
  if (rot === 90) { var sz = vt.naturalSize; cv.preferredTransform = $.CGAffineTransformMake(0, 1, -1, 0, sz.height, 0); }
  if (snd !== '-') {
    var aA = C('AVURLAsset').URLAssetWithURLOptions($.NSURL.fileURLWithPath(snd), $.NSDictionary.dictionary);
    var at = aA.tracksWithMediaType('soun').objectAtIndex(0);
    var ca = comp.addMutableTrackWithMediaTypePreferredTrackID('soun', 0);
    if (!ca.insertTimeRangeOfTrackAtTimeError(vt.timeRange, at, $.kCMTimeZero, e)) throw new Error('sound insert');
  }
  var ex = C('AVAssetExportSession').alloc.initWithAssetPresetName(comp, 'AVAssetExportPresetPassthrough');
  ex.outputURL = $.NSURL.fileURLWithPath(out);
  ex.outputFileType = out.toLowerCase().endsWith('.mp4') ? 'public.mpeg-4' : 'com.apple.quicktime-movie';
  if (when !== '-') {
    var item = C('AVMutableMetadataItem').metadataItem;
    item.keySpace = 'mdta'; item.key = $('com.apple.quicktime.creationdate'); item.value = $(when);
    ex.metadata = $.NSArray.arrayWithObject(item);
  }
  var done = false; ex.exportAsynchronouslyWithCompletionHandler(function () { done = true; }); wait(function () { return done; });
  if (Number(ex.status) !== 3) throw new Error('export ' + ex.status + ' ' + (ex.error.isNil() ? '' : ex.error.localizedDescription.js));
  return 'ok';
}
// info <video>: AVFoundation's own facts, to check video.py's against
function info(p) {
  var a = C('AVURLAsset').URLAssetWithURLOptions($.NSURL.fileURLWithPath(p), $.NSDictionary.dictionaryWithDictionary({AVURLAssetPreferPreciseDurationAndTimingKey: true}));
  var vs = a.tracksWithMediaType('vide'), ss = a.tracksWithMediaType('soun');
  var out = {length: $.CMTimeGetSeconds(a.duration), has_audio: Number(ss.count) > 0, playable: !!a.isPlayable, readable: !!a.isReadable};
  if (Number(vs.count)) {
    var v = vs.objectAtIndex(0), n = v.naturalSize, t = v.preferredTransform;
    var r = $.CGRectApplyAffineTransform($.CGRectMake(0, 0, n.width, n.height), t);
    var fd = v.formatDescriptions.objectAtIndex(0), sub = $.CMFormatDescriptionGetMediaSubType(fd);
    out.stored_w = n.width; out.stored_h = n.height; out.w = Math.round(Math.abs(r.size.width)); out.h = Math.round(Math.abs(r.size.height));
    out.rotation = ((Math.round(Math.atan2(t.b, t.a) * 180 / Math.PI) % 360) + 360) % 360;
    out.codec = String.fromCharCode((sub >>> 24) & 255, (sub >>> 16) & 255, (sub >>> 8) & 255, sub & 255);
    out.fps = Number(v.nominalFrameRate);
  }
  var md = a.metadata, rec = '';
  for (var i = 0; i < Number(md.count); i++) {
    var it = md.objectAtIndex(i), k = it.identifier && !it.identifier.isNil() ? it.identifier.js : '';
    if (k.indexOf('com.apple.quicktime.creationdate') >= 0 && it.stringValue && !it.stringValue.isNil()) rec = it.stringValue.js;
  }
  out.recorded = rec;
  return out;
}
function run(argv) {
  try {
    var c = argv[0];
    if (c === 'picture') return picture(argv[1], parseInt(argv[2]), parseInt(argv[3]), parseFloat(argv[4]), parseInt(argv[5]),
                                        argv[6].split(';').map(function (x) { return x.split(',').map(Number); }));
    if (c === 'compose') return compose(argv[1], argv[2], argv[3], parseInt(argv[4]), argv[5]);
    if (c === 'info') return JSON.stringify(info(argv[1]));
  } catch (e) { return 'error: ' + e.message; }
  return 'error: no such command';
}
"""


def js(*args, timeout=120):
    code, out, err = this_computer.mac_javascript(MAKE_JS, args, timeout=timeout)
    out = (out or "").strip()
    if code != 0 or out.startswith("error"):
        raise RuntimeError(out or err)
    return out


def av_info(p):
    return json.loads(js("info", str(p)))


def tone_wav(path, secs=6.0, loud_at=3.0, rate=48000):
    """A 440 Hz tone, quiet (-40 dBFS) until loud_at, loud (-6 dBFS) after: the stretch the loudness must find."""
    frames = bytearray()
    for i in range(int(secs * rate)):
        t = i / rate
        amp = 10 ** ((-6 if t >= loud_at else -40) / 20)
        frames += struct.pack("<h", int(32767 * amp * math.sin(2 * math.pi * 440 * t)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def top_boxes(b):
    out, pos = [], 0
    while pos + 8 <= len(b):
        size, kind = struct.unpack_from(">I4s", b, pos)
        head = 8
        if size == 1:
            size, head = struct.unpack_from(">Q", b, pos + 8)[0], 16
        elif size == 0:
            size = len(b) - pos
        out.append((kind, pos, head, size))
        pos += size
    return out


def shift_chunks(moov, by):
    """The movie header with every chunk offset (stco, co64) moved on by `by` bytes."""
    moov = bytearray(moov)

    def walk(s, e):
        pos = s
        while pos + 8 <= e:
            size, kind = struct.unpack_from(">I4s", moov, pos)
            if size < 8:
                return
            if kind in (b"trak", b"mdia", b"minf", b"stbl"):
                walk(pos + 8, pos + size)
            elif kind == b"stco":
                n = struct.unpack_from(">I", moov, pos + 12)[0]
                for i in range(n):
                    p = pos + 16 + 4 * i
                    struct.pack_into(">I", moov, p, struct.unpack_from(">I", moov, p)[0] + by)
            elif kind == b"co64":
                n = struct.unpack_from(">I", moov, pos + 12)[0]
                for i in range(n):
                    p = pos + 16 + 8 * i
                    struct.pack_into(">Q", moov, p, struct.unpack_from(">Q", moov, p)[0] + by)
            pos += size
    walk(8, len(moov))
    return bytes(moov)


def rebox(src, dst, how):
    """clip.mov rearranged, every chunk offset kept right so AVFoundation still plays it:
    "moov-first": ftyp, moov, then mdat with size 0 ("to the end of the file"); "big": mdat as a 64-bit box."""
    b = Path(src).read_bytes()
    boxes = top_boxes(b)
    get = {k: (p, h, s) for k, p, h, s in boxes}
    if b"moov" not in get or b"mdat" not in get:
        raise RuntimeError("no moov or mdat")
    mp, mh, ms = get[b"mdat"]
    vp, vh, vs = get[b"moov"]
    moov = b[vp:vp + vs]
    data = b[mp + mh:mp + ms]
    before = b"".join(b[p:p + s] for k, p, h, s in boxes if k not in (b"moov", b"mdat"))
    if how == "moov-first":
        new_data_at = len(before) + len(moov) + 8
        moov = shift_chunks(moov, new_data_at - (mp + mh))
        out = before + moov + struct.pack(">I4s", 0, b"mdat") + data
    else:
        new_data_at = len(before) + 16
        moov = shift_chunks(moov, new_data_at - (mp + mh))
        out = before + struct.pack(">I4sQ", 1, b"mdat", 16 + len(data)) + data + moov
    Path(dst).write_bytes(out)


def colour_at(jpg, x_frac, y_frac, work):
    """(r, g, b) of the pixel at that place in a JPEG (sips makes a BMP of it in the scratch folder)."""
    bmp = Path(work) / "pixel.bmp"
    if bmp.exists():
        bmp.unlink()
    subprocess.run(["sips", "-s", "format", "bmp", str(jpg), "--out", str(bmp)], capture_output=True, check=True)
    w, h, rows = pictures.bmp_pixels(bmp)
    x, y = min(w - 1, int(w * x_frac)), min(h - 1, int(h * y_frac))
    return tuple(rows[y][x * 3:x * 3 + 3]), (w, h)


WHITE = (255, 255, 255)


def near(c, want):
    """The colour seen is closest to the one wanted, of the six colours and white (a video's colour is a little
    off what was drawn: it is stored as brightness and colour difference, then turned back)."""
    def dist(x):
        return sum((a - b) ** 2 for a, b in zip(c, x))
    return min(COLOURS + [WHITE], key=dist) == tuple(want) and dist(want) < 60 ** 2


def tree(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(folder).rglob("*")) if p.is_file()}


def main():
    if not this_computer.MAC or not video.avfoundation_here():
        skip("everything", "this needs a Mac (AVFoundation); tests/pc_video.py is the PC part")
        return 0
    if "--work" in sys.argv:
        work = Path(sys.argv[sys.argv.index("--work") + 1]).resolve()
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
    else:
        work = Path(tempfile.mkdtemp(prefix="assistant video "))
    clips = work / "clips"
    clips.mkdir()
    cols = ";".join(",".join(map(str, c)) for c in COLOURS)

    # ---- the clips
    pic = work / "picture.mov"
    js("picture", str(pic), "640", "360", "6", "30", cols)
    wav = work / "tone.wav"
    tone_wav(wav)
    m4a = clips / "song.m4a"
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(wav), str(m4a)], capture_output=True, check=True)
    clip, side, acc = clips / "clip.mov", clips / "sideways.mov", clips / "Café shoot é.mp4"
    js("compose", str(pic), str(m4a), str(clip), "0", RECORDED)
    js("compose", str(pic), str(m4a), str(side), "90", RECORDED)
    js("compose", str(pic), str(m4a), str(acc), "0", RECORDED)
    sq_pic = work / "square-picture.mov"
    js("picture", str(sq_pic), "720", "720", "2", "30", cols)
    square = clips / "square.mov"
    js("compose", str(sq_pic), "-", str(square), "0", "-")
    first, big = clips / "moov-first.mov", clips / "big-box.mov"
    rebox(clip, first, "moov-first")
    rebox(clip, big, "big")
    for p in (clip, side, acc, square, first, big):
        check(f"made {p.name} ({p.stat().st_size} bytes)", p.stat().st_size > 1000)
    made = tree(clips)

    # ---- facts against AVFoundation's own
    for p in (clip, side, acc, square, first, big):
        f, a = video.facts(p), av_info(p)
        ok = (abs(f["length"] - a["length"]) < 0.002 and (f["w"], f["h"]) == (a["w"], a["h"])
              and (f["stored_w"], f["stored_h"]) == (round(a["stored_w"]), round(a["stored_h"]))
              and f["rotation"] == a["rotation"] and f["codec"] == a["codec"] and abs(f["fps"] - a["fps"]) < 0.01
              and f["has_audio"] == a["has_audio"]
              and (f["recorded"] if f["recorded_from"] == "phone" else "") == a["recorded"])
        check(f"{p.name}: facts match AVFoundation's (length {f['length']} s, shown {f['w']}x{f['h']}, turned "
              f"{f['rotation']}, {f['codec']}, {f['fps']} a second, sound {f['has_audio']}, recorded {f['recorded']!r})",
              ok, f"ours {f} / AVFoundation {a}")
    f = video.facts(clip)
    check("clip.mov: H.264 High, 8-bit 4:2:0, plays as it is", (f["codec_name"], f["profile"], f["chroma"], f["bits"],
          f["plays_as_is"]) == ("h264", 100, "4:2:0", 8, True), f)
    check("clip.mov: recorded by the phone (its own clock, with its time zone)", f["recorded_from"] == "phone", f)
    loc = video.recorded_local(f)
    from datetime import datetime, timezone
    want = datetime(2026, 11, 6, 18, 12, 33, tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
    check("its recording time as plain local time", loc == want, f"{loc} / {want}")
    check("sideways.mov: stored 640x360, shown 360x640, turned 90", (video.facts(side)["stored_w"], video.facts(side)["stored_h"],
          video.facts(side)["w"], video.facts(side)["h"], video.facts(side)["rotation"]) == (640, 360, 360, 640, 90))
    check("clip.mov has its header at the end, as a phone writes it; the MP4 has a 64-bit picture box (AVFoundation's own)",
          [k for k, *_ in top_boxes(clip.read_bytes())][-1] == b"moov"
          and any(k == b"mdat" and h == 16 for k, p, h, s in top_boxes(acc.read_bytes())))
    a_first, a_big = av_info(first), av_info(big)
    check("moov-first.mov and big-box.mov are real videos AVFoundation still reads", a_first["readable"] and a_big["readable"]
          and abs(a_first["length"] - 6) < 0.01 and abs(a_big["length"] - 6) < 0.01, (a_first, a_big))
    check("the rearranged files really are rearranged (header first + 'to the end' box; a 64-bit box)",
          [k for k, *_ in top_boxes(first.read_bytes())][-2:] == [b"moov", b"mdat"]
          and struct.unpack(">I", first.read_bytes()[top_boxes(first.read_bytes())[-1][1]:][:4])[0] == 0
          and any(k == b"mdat" and h == 16 for k, p, h, s in top_boxes(big.read_bytes())))

    # ---- not videos
    notes, empty, jpg, cut = clips / "notes.mov", clips / "empty.mp4", clips / "photo.mov", clips / "cut off.mov"
    notes.write_text("These are my notes for the shoot.\n", encoding="utf-8")
    empty.write_bytes(b"")
    jpg.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x00" * 200 + b"\xff\xd9")
    cut.write_bytes(clip.read_bytes()[:clip.stat().st_size // 2])
    for p in (notes, empty, jpg, m4a, cut, clips / "not there.mov"):
        try:
            video.facts(p)
            check(f"{p.name}: refused", False, "it was read as a video")
        except video.NotAVideo as e:
            words = str(e)
            check(f"{p.name}: refused in plain words ({words})", words and "/" not in words and "Traceback" not in words, words)
        except Exception as e:  # noqa: BLE001
            check(f"{p.name}: refused in plain words", False, f"{type(e).__name__}: {e}")
    r = video.stills(notes, [1], work / "looks")
    check("stills of a non-video: a plain answer, no folder made", not r["ok"] and r["state"] == "failed"
          and not (work / "looks").exists(), r)

    # ---- stills
    looks = work / "looks"
    times = [0.5 + i for i in range(6)]
    r = video.stills(clip, times, looks)
    check("stills: six made, in a new folder 'look'", r["ok"] and Path(r["folder"]).name == "look"
          and sum(1 for s in r["stills"] if "file" in s) == 6, r)
    ok_col, ok_at, detail = True, True, []
    for s, want in zip(r["stills"], COLOURS):
        c, size = colour_at(Path(r["folder"]) / s["file"], 0.7, 0.7, work)
        ok_col &= near(c, want)
        ok_at &= s["at"] <= s["asked"] + 1e-6 and s["asked"] - s["at"] < 1 / 30 + 1e-6
        detail.append((s["asked"], s["at"], c, want, size))
    check("stills: each the colour of its second (exact times, not the nearest keyframe)", ok_col, detail)
    check("stills: labelled with the time really returned, within one frame of the time asked", ok_at, detail)
    s0 = r["stills"][0]
    check("stills: no longer than 360 on the long side, the video's shape kept", (s0["w"], s0["h"]) == (360, 202), s0)
    before = tree(r["folder"])
    r2 = video.stills(clip, [2.25], looks)
    check("a second look goes in a new folder ('look 2'); the first is left exactly as it was",
          r2["ok"] and Path(r2["folder"]).name == "look 2" and tree(r["folder"]) == before, r2)
    c, _ = colour_at(Path(r2["folder"]) / r2["stills"][0]["file"], 0.7, 0.7, work)
    check("a still between two whole seconds is the colour of its second", near(c, COLOURS[2]), c)
    # upright: the white block is in the top-left of the picture as stored; turned 90 clockwise it shows top-right
    rs = video.stills(side, [1.5], looks, name="sideways")
    st = rs["stills"][0]
    tl, size = colour_at(Path(rs["folder"]) / st["file"], 0.05, 0.05, work)
    tr, _ = colour_at(Path(rs["folder"]) / st["file"], 0.95, 0.05, work)
    check("a sideways video's still comes out upright (shown 202x360, its stored top-left corner now top-right)",
          (st["w"], st["h"]) == (202, 360) and near(tr, (255, 255, 255)) and near(tl, COLOURS[1]), (st, tl, tr, size))
    ra = video.stills(acc, [4.5], looks, name="Café")
    c, _ = colour_at(Path(ra["folder"]) / ra["stills"][0]["file"], 0.7, 0.7, work)
    check("a video with an accent and a space in its name: its still is right", ra["ok"] and near(c, COLOURS[4]), (ra, c))
    rb = video.stills(clip, [1.5], looks, edge=1600)
    check("a still is never made bigger than the video (edge 1600 on a 640x360 video gives 640x360)",
          (rb["stills"][0]["w"], rb["stills"][0]["h"]) == (640, 360), rb)
    rl = video.stills(clip, [99, -3], looks, name="ends")
    check("a time past the end is the last picture; before the start, the first",
          rl["ok"] and rl["stills"][0]["at"] > 5.9 and rl["stills"][1]["at"] == 0, rl)
    saved = video.STILL_BATCH_BYTES
    video.STILL_BATCH_BYTES = 1                          # one still per AVFoundation program
    try:
        rbatch = video.stills(clip, times, looks, name="batches")
    finally:
        video.STILL_BATCH_BYTES = saved
    files = [s.get("file") for s in rbatch["stills"]]
    cols_ok = all(near(colour_at(Path(rbatch["folder"]) / s["file"], 0.7, 0.7, work)[0], want)
                  for s, want in zip(rbatch["stills"], COLOURS))
    check("stills in batches (each its own short program, so memory stays small): numbered 1 to 6 and right",
          files == [f"{i:06d}.jpg" for i in range(1, 7)] and cols_ok, rbatch)
    check("a batch size: 120 stills of 360 px at once, fewer when they are big",
          video._batch_size(video.facts(clip), 360) == 120 and video._batch_size({"w": 3840, "h": 2160}, 1600) < 20)

    # ---- loudness
    db, how = video.loudness(clip)
    check(f"loudness: a level every half second, 12 for 6 s ({how})", db is not None and len(db) == 12, (db, how))
    if db:
        quiet = db[0]
        jump = next((i for i, x in enumerate(db) if x > quiet + 15), None)
        check("the loud stretch found within one half second of 3 s (where the tone gets loud)",
              jump is not None and abs(jump * 0.5 - 3.0) <= 0.5, (jump, db))
        lm = video.loud_moments(db)
        check("her loud moments: one, at 3 s", len(lm) == 1 and abs(lm[0]["at"] - 3.0) <= 0.5, lm)
        check("the quiet part about -43 dB and the loud part about -9 dB (her measure: RMS of full scale)",
              abs(db[1] - (-43)) < 2.5 and abs(db[9] - (-9)) < 2.5, db)
        a, how2 = video._pcm_mac(clip)
        db2 = video.levels(a) if a is not None else None
        check("the same levels through AVFoundation's own reader (the Mac's second way), within 1 dB",
              db2 is not None and len(db2) == len(db) and max(abs(x - y) for x, y in zip(db, db2)) <= 1.0, (db, db2))
    db, how = video.loudness(square)
    check("a video with no sound: no levels, said plainly", db == [] and how == "no sound", (db, how))
    hop = 4000
    check("the last half second counts when it is at least 90% there, and not when it is less (ours, NEAR_FULL)",
          len(video.levels([1000] * (2 * hop + 3700))) == 3 and len(video.levels([1000] * (2 * hop + 3500))) == 2
          and len(video.levels([1000] * (2 * hop))) == 2)

    # ---- the small copy for playing
    pv = work / "previews" / "clip"
    out = pv / "preview.mp4"
    r = video.preview_copy(clip, out)
    check("the copy is made", r.get("ok") and r.get("made") and out.is_file(), r)
    check("no hidden half-copy left beside it", sorted(p.name for p in pv.iterdir()) == ["preview.mp4"], list(pv.iterdir()))
    h1 = hashlib.sha256(out.read_bytes()).hexdigest()
    r = video.preview_copy(clip, out)
    check("asked again, the copy already made is used as it is (made once, never over a file)",
          r == {"ok": True, "made": False} and hashlib.sha256(out.read_bytes()).hexdigest() == h1, r)
    cf, ca = video.facts(out), av_info(out)
    check("the copy is no bigger than the video (360 on its short side stays 360: never enlarged)",
          (cf["w"], cf["h"]) == (640, 360) and ca["readable"] and ca["playable"], (cf, ca))
    check("the copy is H.264 8-bit 4:2:0 with sound, the whole length, and plays as it is",
          cf["codec"] == "avc1" and cf["plays_as_is"] and cf["has_audio"] and abs(ca["length"] - 6) < 0.1, (cf, ca))
    rc = video.stills(out, [3.5], looks, name="from the copy")
    c, _ = colour_at(Path(rc["folder"]) / rc["stills"][0]["file"], 0.7, 0.7, work)
    check("AVFoundation reads the copy back: its still at 3.5 s is the fourth colour", rc["ok"] and near(c, COLOURS[3]), (rc, c))
    so = work / "previews" / "sideways" / "preview.mp4"
    r = video.preview_copy(side, so)
    sf = video.facts(so) if so.is_file() else {}
    rs = video.stills(so, [0.5], looks, name="sideways copy")
    tr, _ = colour_at(Path(rs["folder"]) / rs["stills"][0]["file"], 0.95, 0.05, work)
    check("a sideways video's copy plays upright (shown 360x640, still turned 90)",
          r.get("made") and (sf.get("w"), sf.get("h"), sf.get("rotation")) == (360, 640, 90) and near(tr, (255, 255, 255)),
          (r, sf, tr))
    sqo = work / "previews" / "square" / "preview.mp4"
    r = video.preview_copy(square, sqo)
    qf = video.facts(sqo) if sqo.is_file() else {}
    check("a video bigger than 540 on its short side is copied at 540 (720x720 becomes 540x540)",
          r.get("made") and (qf.get("w"), qf.get("h")) == (540, 540), (r, qf))
    taken = work / "previews" / "taken" / "preview.mp4"
    taken.parent.mkdir(parents=True)
    taken.write_bytes(b"something of theirs")
    r = video.preview_copy(clip, taken)
    check("a file already at the copy's place is never written over", r == {"ok": True, "made": False}
          and taken.read_bytes() == b"something of theirs", r)
    saved = video.SPACE_MARGIN
    video.SPACE_MARGIN = 1e18
    try:
        low = work / "previews" / "low" / "preview.mp4"
        r = video.preview_copy(clip, low)
    finally:
        video.SPACE_MARGIN = saved
    check("refused when the drive would keep less than 5 GB free: her words, nothing written",
          r.get("state") == "lowspace" and "nearly full" in r.get("words", "") and not low.exists()
          and not any(low.parent.iterdir()), r)
    broken = clips / "broken.mov"
    b = bytearray(clip.read_bytes())
    for k, p, h, n in top_boxes(bytes(b)):
        if k == b"mdat":
            b[p + h:p + n] = bytes(n - h)                # the header is whole; the picture data is all zeros
    broken.write_bytes(bytes(b))
    bo = work / "previews" / "broken" / "preview.mp4"
    r = video.preview_copy(broken, bo)
    left = sorted(x.name for x in bo.parent.iterdir()) if bo.parent.exists() else []
    check("a video whose pictures can't be read: no copy, her words, and no half-copy left behind",
          not r["ok"] and r["state"] == "failed" and "couldn't make a preview" in r["words"] and left == [], (r, left))
    r = video.preview_copy(notes, work / "previews" / "notes" / "preview.mp4")
    check("a copy of a non-video: plain words, nothing made", not r["ok"] and r["state"] == "failed", r)

    # ---- the PC's way, tried on this Mac
    os.environ[video.NO_AV] = "1"
    try:
        r = video.stills(clip, [1.5], work / "pc looks")
        check("the PC way: stills say this_computer.NO_PREVIEW, and no folder is made",
              r == {"ok": False, "state": "pc", "words": this_computer.NO_PREVIEW} and not (work / "pc looks").exists(), r)
        r = video.preview_copy(clip, work / "pc" / "preview.mp4")
        check("the PC way: the copy says the same, nothing made", r.get("state") == "pc" and not (work / "pc").exists(), r)
        check("the PC way: the facts and loudness still work", video.facts(clip)["w"] == 640
              and len(video.loudness(clip)[0] or []) == 12)
    finally:
        os.environ.pop(video.NO_AV, None)

    # ---- the video helper never changed a clip
    now = tree(clips)
    check("no clip was changed by any of this (each byte for byte what was made; only the test's own non-videos added)",
          all(now.get(k) == v for k, v in made.items()), [k for k, v in made.items() if now.get(k) != v])

    print(f"\n{RESULTS['PASS']} passed, {RESULTS['FAIL']} failed, {RESULTS['SKIP']} skipped.")
    if RESULTS["FAIL"]:
        print("Kept for a look:", work)
        return 1
    if "--work" not in sys.argv:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
