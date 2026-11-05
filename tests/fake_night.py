#!/usr/bin/env python3
"""Make a small fake backup (a settled-looking day folder with _studio records) for testing the report
and its buttons without a card. Two shoots of coloured JPEGs, index, groups, shoots, previews, the
peek pages and six sneak peeks per shoot picked by "Claude". Needs Pillow where sips is absent.

    python3 tests/fake_night.py /tmp/somewhere/night   (makes it; prints the path)
"""
import json, sys, subprocess, hashlib, random
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageDraw

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/the-engine/skills/studio-manager/scripts"


def photo(path, i, hue):
    im = Image.new("RGB", (900, 600), (hue, (hue * 3 + i * 40) % 255, (255 - hue + i * 13) % 255))
    d = ImageDraw.Draw(im)
    d.ellipse((300 + (i % 5) * 40, 150, 600 + (i % 5) * 40, 450), fill=(255, 255, 255))
    d.text((20, 20), f"photo {i}", fill=(0, 0, 0))
    im.save(path, quality=85)


def main(night):
    night = Path(night); studio = night / "_studio"
    (studio / "groups").mkdir(parents=True, exist_ok=True)
    random.seed(1)
    files, index, groups, shoots = {}, [], [], []
    t0 = datetime(2026, 6, 24, 9, 0)
    gi = 0
    for si, (name, n, hue) in enumerate([("Beach", 40, 60), ("Palm grove", 30, 180)], 1):
        folder = night / f"2026-06-24 {name}"; folder.mkdir(exist_ok=True)
        gids = []
        for gpart in range(2):
            gi += 1; gid = f"g{gi:02d}"; gfiles, previews = [], []
            for k in range(n // 2):
                i = gpart * (n // 2) + k
                rel = f"2026-06-24 {name}/{name.replace(' ', '-')}_{i+1:04d}_IMG_{si}{i:03d}.jpg"
                p = night / rel; photo(p, i, hue)
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                files[rel] = {"size": p.stat().st_size, "sha256": h, "dest": {"ok": True}}
                taken = (t0 + timedelta(hours=si * 2 + gpart, seconds=i * 5 if i % 4 else i * 5 + 400)).isoformat(timespec="seconds")
                index.append({"file": rel, "taken": taken, "camera": "Canon R5", "serial": "123", "lens": "35mm"})
                gfiles.append(rel)
                if k < 4:
                    pv = f"{gid}_IMG_{si}{i:03d}.jpg"
                    Image.open(p).resize((300, 200)).save(studio / "groups" / pv)
                    previews.append(pv)
            groups.append({"id": gid, "files": gfiles, "previews": previews, "start": index[-len(gfiles)]["taken"], "end": index[-1]["taken"],
                           "bodies": 1, "lenses": ["35mm"], "photos": len(gfiles)})
            gids.append(gid)
        shoots.append({"id": f"s{si}", "groups": gids, "name": name, "suggested": name, "photos": n, "folder": f"2026-06-24 {name}",
                       "recap": f"{n} frames at the {name.lower()}.", "why": "same people, same place"})
    (studio / "manifest.json").write_text(json.dumps({"session": "2026-06-24 fake card", "dest": str(night), "files": files,
                                                       "started": "2026-06-24T22:00:00", "finished": "2026-06-24T22:07:00", "work_seconds": 420,
                                                       "problems": [], "skipped_system_files": 0}, indent=1))
    (studio / "index.json").write_text(json.dumps({"photos": index}, indent=1))
    (studio / "groups.json").write_text(json.dumps({"groups": groups}, indent=1))
    (studio / "shoots.json").write_text(json.dumps({"shoots": shoots}, indent=1))
    run = lambda *a: subprocess.run([sys.executable, str(SCRIPTS / a[0]), *a[1:]], capture_output=True, text=True)
    r = run("peek_sheets.py", "make", str(night)); assert r.returncode == 0, r.stdout + r.stderr
    r = run("peek_sheets.py", "closer", str(night), "s1=1,2,3,4,5,6,7,8,9,10,11,12", "s2=1,2,3,4,5,6,7,8,9,10"); assert r.returncode == 0, r.stdout + r.stderr
    r = run("peek_sheets.py", "pick", str(night), "s1=3,1,5,7,9,11", "s2=2,4,6,8,10,1"); assert r.returncode == 0, r.stdout + r.stderr
    r = run("sneak_peeks.py", "--night", str(night)); assert r.returncode in (0, 2), r.stdout + r.stderr
    r = run("first_look.py", str(night)); assert r.returncode == 0, r.stdout + r.stderr
    r = run("report_page.py", str(night)); assert r.returncode == 0, r.stdout + r.stderr
    print(night)


if __name__ == "__main__":
    main(sys.argv[1])
