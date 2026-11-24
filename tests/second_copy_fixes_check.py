#!/usr/bin/env python3
"""The second copy's review fixes (Nov 23): what two reviewers broke on purpose, each held here by a check that
fails on the code before the fix.

  1. a follow cut off while photos are trading names (a ring after a join; one photo taking the name another had)
     is finished by the next follow, at every point it can be cut, and the report never says all is well meanwhile
  2. a copy killed in the moment between a photo landing on the second drive and the record hearing of it leaves
     no stray photo behind under an old name when a shoot is renamed before the copy is carried on
  3. sidecars of the same size: each stays under its own photo's name on the second drive when photos change names
  4. a rename made while this computer's one second-copy lock is held by something else is caught up afterwards
  5. while a copy is behind, the report's line never says it has the photo drive's folders and names
  6. the report server's second-copy GETs refuse another website, and never start the catch-up for one
  7. a copy that was behind because something was in the way is tried again by itself once that is gone

Everything is pretend, as in second_copy_check.py (whose helpers are used): a scratch STUDIO_HOME, pretend drives and
a pretend card in a temp folder, the report's server on a scratch port with STUDIO_NO_WINDOWS_FOR_TESTS. No browser.

    python3 tests/second_copy_fixes_check.py [ring chain copy sidecars busy line server problem]
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import second_copy_check as sc  # noqa: E402

t = sc.t
check = sc.check
MIRROR, SESSION = sc.MIRROR, sc.SESSION

# Runs second_copy.py and stops it dead at the Nth step, the way a crash or a pulled plug would:
#   before / after : just before, or just after, the Nth rename on the second drive or write of a record
#   copy           : just after the Nth file has landed on the second drive (its record not yet written)
KILLER = r'''
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
N, how = int(sys.argv[2]), sys.argv[3]
import backup, this_computer, second_copy
count = [0]
def wrap(fn, mine):
    def g(*a, **k):
        if mine:
            count[0] += 1
            if count[0] == N:
                if how != "before":
                    fn(*a, **k)
                sys.stderr.write("KILLED\n"); sys.stderr.flush(); os._exit(9)
        return fn(*a, **k)
    return g
moves = how in ("before", "after")
this_computer.rename = wrap(this_computer.rename, moves)
this_computer.rename_new = wrap(this_computer.rename_new, moves)
this_computer.rmdir = wrap(this_computer.rmdir, moves)
second_copy.write_whole = wrap(second_copy.write_whole, moves)
backup.copy_with_hash = wrap(backup.copy_with_hash, how == "copy")
sys.argv = ["second_copy.py"] + sys.argv[4:]
second_copy.main()
'''


def killed(b, n, how, *args):
    code, out = t.run_python([b["killer"], t.SCRIPTS, n, how, *args], env=b["env"])
    return "KILLED" in out, out


def snap(b, tag):
    d = b["base"].with_name(f"world.{tag}")
    if d.exists():
        shutil.rmtree(d)
    shutil.copytree(b["base"], d, symlinks=True)


def restore(b, tag):
    # A catch-up the part before started by itself (the report's own status check starts one in the background)
    # may be on its way out with its log still open; a PC won't take a file away while a program has it open.
    # That is this test clearing its own pretend world, nothing a photographer does: wait for the hold to go.
    end = time.time() + 60
    while True:
        try:
            shutil.rmtree(b["base"])
            break
        except PermissionError:
            if time.time() > end:
                raise
            time.sleep(0.5)
        except FileNotFoundError:
            break                       # an earlier try took the last of it
    shutil.copytree(b["base"].with_name(f"world.{tag}"), b["base"], symlinks=True)


def index_of(b):
    return json.loads((b["records"] / "index.json").read_text(encoding="utf-8"))


def in_shoot(b, index, n):
    folder = json.loads((b["records"] / "shoots.json").read_text(encoding="utf-8"))["shoots"][n]["folder"]
    return [p for p in index["photos"] if p.get("original") and p["file"].startswith(folder + "/")]


def save_index(b, index):
    (b["records"] / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")


def moving(to):
    return [x for x in sc.listing(to) if x.endswith(".studio-moving")]


def in_line(b, to):
    got, want = sc.mirror_tree(to), sc.expected(b["records"])
    return got == want, sorted(set(got) ^ set(want)) + [k for k in got if k in want and got[k] != want[k]]


# ---------------------------------------------------------------- 1. a follow cut off while names change hands

def a_ring(b):
    """Three photos (no sidecars) of the second shoot pass their names round on the photo drive."""
    index = index_of(b)
    x, y, z = in_shoot(b, index, 1)[:3]
    D = b["drive"]
    fx, fy, fz = x["file"], y["file"], z["file"]
    os.rename(D / fx, D / (fx + ".tmp"))
    os.rename(D / fy, D / fx)
    os.rename(D / fz, D / fy)
    os.rename(D / (fx + ".tmp"), D / fz)
    y["file"], z["file"], x["file"] = fx, fy, fz
    save_index(b, index)


def a_chain(b):
    """As a join that shifts the numbers does it: the last photo of the second shoot takes a new name, and each
    photo before it takes the name the next one had."""
    index = index_of(b)
    two = in_shoot(b, index, 1)
    D = b["drive"]
    names = [p["file"] for p in two]
    new_last = str(Path(names[-1]).with_name("Shifted_" + Path(names[-1]).name))
    targets = names[2:] + [new_last]            # photos 2.. each take the next one's name; the first stays
    for p, to in reversed(list(zip(two[1:], targets))):
        os.rename(D / p["file"], D / to)
        p["file"] = to
    save_index(b, index)


def cut_at_every_point(b, to, label, play):
    print(f"A follow cut off at every point it can be, {label}")
    restore(b, "copied")
    play(b)
    snap(b, "played")
    whole = sorted(sc.mirror_tree(to).values())
    for how in ("before", "after"):
        bad, unsaid, points = [], [], 0
        for n in range(1, 200):
            restore(b, "played")
            was_killed, out = killed(b, n, how, "follow", b["records"], "--json")
            if not was_killed:
                break
            points += 1
            ok0, _ = in_line(b, to)
            # (n == 1 is before the follow's first write, its log: nothing on the second drive has changed yet)
            if not ok0 and how == "before" and n > 1 and not sc.status_of(b).get("behind"):
                unsaid.append(n)
            code, got, out1 = sc.follow(b)
            ok, diff = in_line(b, to)
            code2, got2, _ = sc.follow(b)
            if not (ok and got.get("state") in ("followed", "same") and got2.get("state") == "same" and not moving(to)
                    and sorted(sc.mirror_tree(to).values()) == whole and not sc.status_of(b).get("behind")):
                bad.append((n, got.get("state"), got2.get("state"), diff[:3], moving(to)))
        check(f"cut {how} each of its {points} steps: the next follow finishes it (every photo under the name the photo "
              "drive has, nothing left under a hidden name, nothing lost), and one more changes nothing",
              points > 4 and not bad, str(bad)[:900])
        if how == "before":
            check("and between the cut and that next follow, the report never says all is well while names are wrong",
                  not unsaid, f"cut points with wrong names and no line: {unsaid}")


# ---------------------------------------------------------------- 2. a copy killed before the record heard of a file

def a_copy_killed(b, to):
    print("A copy killed in the moment a photo has landed and the record has not heard of it")
    bad, plain_bad, points = [], [], 0
    for n in range(1, 60):
        restore(b, "sorted")
        was_killed, out = killed(b, n, "copy", b["records"], "--to", to)
        if not was_killed:
            break
        points += 1
        if n % 3 == 1:          # (carried on with no rename in between: as before)
            code, out = sc.second(b, to)
            ok, diff = in_line(b, to)
            if code != 0 or not ok:
                plain_bad.append((n, code, diff[:3]))
            restore(b, "sorted")
            killed(b, n, "copy", b["records"], "--to", to)
        code, out = sc.rename(b, "s2", "Zoë évening")
        code, out = sc.second(b, to)
        ok, diff = in_line(b, to)
        if code != 0 or not ok:
            bad.append((n, code, diff[:4]))
    check(f"killed after each of its {points} files, a shoot renamed, the copy carried on: the second drive holds exactly "
          "what the photo drive holds (no photo left behind under its old name beside its copy)", points > 5 and not bad, str(bad)[:900])
    check("and carried on with no rename in between, it is finished as before", not plain_bad, str(plain_bad)[:400])
    restore(b, "sorted")
    killed(b, 3, "copy", b["records"], "--to", to)
    note = json.loads((b["records"] / "second-copy.going.json").read_text(encoding="utf-8")) if (b["records"] / "second-copy.going.json").is_file() else {}
    check("the note of the file being copied is written before its first byte: which file, and the name it goes under, never more",
          set(note) == {"key", "at", "place"} and (to / note["at"]).is_file() and not (sc.record(b).get("files", {}).get(note["key"]) or {}).get("ok"), str(note))
    if not note:
        return
    (to / note["at"]).write_bytes(b"not the photo: something else under that name")
    code, got, out = sc.follow(b)
    check("a file under that name that is NOT the photo (its hash differs) is never taken for it",
          not (sc.record(b).get("files", {}).get(note["key"]) or {}).get("ok")
          and (to / note["at"]).read_bytes() == b"not the photo: something else under that name", out)


# ---------------------------------------------------------------- 3. sidecars of one size

def swap_two_with_sidecars(b):
    index = index_of(b)
    one = in_shoot(b, index, 0)
    a_, b_ = one[0], one[1]
    D = b["drive"]
    for ext in (None, ".xmp"):
        fa = a_["file"] if ext is None else str(Path(a_["file"]).with_suffix(ext))
        fb = b_["file"] if ext is None else str(Path(b_["file"]).with_suffix(ext))
        os.rename(D / fa, D / (fa + ".tmp"))
        os.rename(D / fb, D / fa)
        os.rename(D / (fa + ".tmp"), D / fb)
    a_["file"], b_["file"] = b_["file"], a_["file"]
    save_index(b, index)
    return a_, b_


def sidecars(b, to):
    print("Sidecars of the same size: each stays under its own photo's name on the second drive")
    restore(b, "copied")
    a_, b_ = swap_two_with_sidecars(b)
    xa, xb = (str(Path(p["file"]).with_suffix(".xmp")) for p in (a_, b_))
    check("(the pretend swap: the two sidecars are the same size and not the same bytes)",
          (b["drive"] / xa).stat().st_size == (b["drive"] / xb).stat().st_size and sc.sha(b["drive"] / xa) != sc.sha(b["drive"] / xb))
    code, got, out = sc.follow(b)
    ok, diff = in_line(b, to)
    check("after two photos with sidecars swap names, follow leaves each sidecar under its own photo's name",
          got.get("state") == "followed" and ok and sc.sha(to / xa) == sc.sha(b["drive"] / xa) and sc.sha(to / xb) == sc.sha(b["drive"] / xb), f"{out[-300:]} {diff}")
    for card_in in (True, False):
        restore(b, "sorted")
        a_, b_ = swap_two_with_sidecars(b)
        if not card_in:
            sc.pull_card(b)
        code, out = sc.second(b, to)
        ok, diff = in_line(b, to)
        check(f"and a new second copy made after the swap ({'from the card' if card_in else 'the card out'}) puts each sidecar under its own photo's name",
              code == 0 and ok, f"{out[-300:]} {diff}")
        sc.push_card(b)


# ---------------------------------------------------------------- 4, 5. the lock held by something else; one true line

HOLDER = ("import sys, time\nsys.path.insert(0, sys.argv[1])\nimport this_computer\nf = open(sys.argv[2], 'a+', encoding='utf-8')\n"
          "print('held' if this_computer.try_lock(f) is not False else 'not', flush=True)\nsys.stdin.read()\n")


def hold_lock(b):
    b["home"].mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen([sys.executable, "-c", HOLDER, str(t.SCRIPTS), str(b["home"] / "second-copy.lock")], env=t.child_env(b["env"]),
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding="utf-8")
    return p, p.stdout.readline().strip() == "held"


def let_go(p):
    try:
        p.stdin.close()
        p.wait(timeout=20)
    except Exception:  # noqa: BLE001
        p.kill()


def lock_held_by_another(b, to):
    print("A rename while this computer's one second-copy lock is held by something else")
    restore(b, "copied")
    p, held = hold_lock(b)
    try:
        check("(the pretend other copy holds the lock)", held)
        rec_before = (b["records"] / "second-copy.json").read_bytes()
        code, out = sc.rename(b, "s2", "Busy rename")
        last = out.strip().splitlines()[-1] if out.strip() else ""
        check("the rename's last line does not say the copy 'takes the new names itself': it says this one catches up afterwards",
              code == 0 and "it takes the new names itself" not in out and "still has the folders and names from before" in last
              and "catches up as soon as that is done" in last and str(b["base"]) not in last, out[-400:])
        st = sc.status_of(b)
        check("it is on record as behind, and the report says so (not 'the same folders and photo names')",
              st.get("behind", "").startswith("Your second copy on LaCie still has the folders and names from before")
              and "same folders and photo names" not in st.get("line", "") and st.get("state") == "done", str(st))
        check("the record itself was not written by a command that did not hold the lock (the note is a file of its own)",
              (b["records"] / "second-copy.json").read_bytes() == rec_before
              and (b["records"] / "second-follow-later.json").is_file()
              and json.loads((b["records"] / "second-follow-later.json").read_text(encoding="utf-8")).get("state") == "waiting")
        page = (b["records"] / "report.html").read_text(encoding="utf-8") if (b["records"] / "report.html").is_file() else ""
        check("the report as a file says so too", not page or "catches up as soon as that is done" in page.replace("&#x27;", "'"), page[page.find("sc-behind") - 80:][:400])
    finally:
        let_go(p)
    check("with the lock free, the status offers to catch up", sc.status_of(b).get("catch") is True, str(sc.status_of(b)))
    code, out = t.run("second_copy.py", "follow", "--all", env=b["env"])
    ok, diff = in_line(b, to)
    st = sc.status_of(b)
    check("follow --all (as a backup runs it) brings it in line, and the line goes",
          code == 0 and "1 second copy brought in line." in out and ok and st.get("behind") == "" and "same folders and photo names" in st.get("line", ""),
          f"{out} {diff} {st}")

    restore(b, "copied")
    p, held = hold_lock(b)
    try:
        (b["home"] / "second-copy.running.json").write_text(json.dumps({"pid": p.pid, "studio": str(b["records"]), "card": None, "to_name": "LaCie"}), encoding="utf-8")
        code, got, out = sc.follow(b)
        check("when the copy that holds the lock is this backup's own, the answer is still busy: it takes the new names itself",
              got.get("state") == "busy" and "it takes the new names itself" in got.get("words", "")
              and not (b["records"] / "second-follow-later.json").exists(), out)
    finally:
        let_go(p)


def one_true_line(b, to):
    print("While a copy is behind, the report shows one true line, not two that disagree")
    restore(b, "copied")
    st = sc.status_of(b)
    check("(in line: the made line says it has the photo drive's folders and names)", "It has the same folders and photo names as Big Kahuna." in st.get("line", "") and st.get("behind") == "", str(st))
    away = to.with_name(to.name + " (unplugged)")
    os.rename(to, away)
    sc.rename(b, "s2", "While away")
    st = sc.status_of(b)
    check("with its drive out during a rename: the behind line shows, and the made line no longer says 'the same folders and photo names'",
          st.get("behind", "").startswith("Your second copy on LaCie still has") and st.get("line", "").startswith("Second copy made on LaCie")
          and "same folders and photo names" not in st.get("line", "") and st.get("line", "").rstrip().endswith("."), str(st))
    os.rename(away, to)
    snap(b, "waiting")
    sc.follow(b)
    st = sc.status_of(b)
    check("caught up, the made line says it again", "It has the same folders and photo names as Big Kahuna." in st.get("line", "") and st.get("behind") == "", str(st))


# ---------------------------------------------------------------- 6. the report server's GETs

def get(base, path, **headers):
    req = urllib.request.Request(base + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, ""


def the_server(b, to):
    print("The report server's second-copy GETs are for its own page only")
    restore(b, "waiting")               # behind, its drive back in: the next status check would start the catch-up
    old = sorted(k for k in sc.mirror_tree(to))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = subprocess.Popen([sys.executable, str(t.SCRIPTS / "serve_report.py"), str(b["records"]), "--port", str(port)],
                           env=t.child_env(b["env"]), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding="utf-8", errors="replace")
    try:
        srv.stdout.readline()
        base = f"http://127.0.0.1:{port}"
        evil = {"Origin": "http://evil.example", "Sec-Fetch-Site": "cross-site"}
        code, body = get(base, "/second-status", **evil)
        check("GET second-status from another website is refused (403)", code == 403 and not body, f"{code} {body[:200]}")
        code2, _ = get(base, "/second-status", Origin="http://evil.example")
        code3, _ = get(base, "/second-status", **{"Sec-Fetch-Site": "cross-site"})
        check("by its Origin alone, and by Sec-Fetch-Site alone", code2 == 403 and code3 == 403, f"{code2} {code3}")
        for path in ("/second-drives", "/other-backups", "/naming", "/next-drives"):
            code, body = get(base, path, **evil)
            check(f"GET {path[1:]} from another website is refused too", code == 403 and not body, f"{code} {body[:120]}")
        time.sleep(4)
        check("and none of those asks started the catch-up: nothing on the second drive moved",
              sorted(k for k in sc.mirror_tree(to)) == old and sc.status_of(b).get("behind"), str(sc.status_of(b)))
        code, body = get(base, "/second-drives", Origin=base, **{"Sec-Fetch-Site": "same-origin"})
        check("the page's own ask (its own Origin) is answered", code == 200 and "drives" in body, f"{code} {body[:120]}")
        st, end = {}, time.time() + 60
        while time.time() < end:
            code, body = get(base, "/second-status", **{"Sec-Fetch-Site": "same-origin"})
            st = json.loads(body) if code == 200 else {}
            if code != 200 or not st.get("behind"):
                break
            time.sleep(0.3)
        ok, diff = in_line(b, to)
        check("and its own status check still brings the copy in line by itself", code == 200 and st.get("behind") == "" and ok, f"{code} {st} {diff}")
    finally:
        srv.kill()
        srv.communicate()


# ---------------------------------------------------------------- 7. something in the way, then gone

def problem_tried_again(b, to):
    print("Behind because something was in the way: tried again by itself once that is gone")
    restore(b, "copied")
    away = to.with_name(to.name + " (unplugged)")
    os.rename(to, away)
    sc.rename(b, "s2", "Blocker")
    os.rename(away, to)
    new_folder = next(f for f in sc.shoot_folders(b["records"]) if f.startswith("Blocker"))
    (to / new_folder).mkdir()
    (to / new_folder / "notes.txt").write_bytes(b"their own folder")
    code, got, out = sc.follow(b)
    check("(a folder of theirs in the way: a problem, their folder untouched)", got.get("state") == "problem"
          and (to / new_folder / "notes.txt").read_bytes() == b"their own folder", out)
    st = sc.status_of(b)
    check("the status says so, offers another try, and does not say 'the same folders and photo names'",
          "isn't part of the copy" in st.get("behind", "") and st.get("catch") is True and "same folders and photo names" not in st.get("line", ""), str(st))
    held = {n: ((b["records"] / n).read_bytes() if (b["records"] / n).is_file() else None) for n in ("second-copy.json", "second-follow-log.json")}
    stamps = sc.stamps(to)
    code, got, out = sc.follow(b)
    code, out2 = t.run("second_copy.py", "follow", "--all", env=b["env"])
    check("a try that meets the same thing in the way moves nothing and writes nothing (the log does not grow)",
          got.get("state") == "problem" and "0 second copies brought in line." in out2 and sc.stamps(to) == stamps
          and held == {n: ((b["records"] / n).read_bytes() if (b["records"] / n).is_file() else None) for n in held}, out + out2)
    os.rename(to / new_folder, to / "Their own folder")        # (they move their folder out of the way)
    code, out = t.run("second_copy.py", "follow", "--all", env=b["env"])
    got_, want = sc.mirror_tree(to), {**sc.expected(b["records"]), "Their own folder/notes.txt": sc.sha(to / "Their own folder" / "notes.txt")}
    check("once it is gone, follow --all (as a backup runs it) brings the copy in line with nobody asking",
          code == 0 and "1 second copy brought in line." in out and got_ == want and sc.status_of(b).get("behind") == "", f"{out} {sorted(set(got_) ^ set(want))}")


def words():
    print("The words")
    import second_copy
    W = second_copy.OUR_WORDS
    for key in ("follow_later", "follow_part_way"):
        line = W.get(key, "")
        check(f"{key}: plain words, the drive by name, never a path or 'your assistant'",
              "{drive}" in line and "/" not in line and "your assistant" not in line.lower() and "Claude" not in line and "—" not in line)
    part = (t.SCRIPTS.parent / "parts" / "after-the-report.md").read_text(encoding="utf-8")
    check("the instructions say a copy with something in the way is tried again by itself, and how to do it now",
          "tried again by itself" in part and "second_copy.py follow" in part)


def main():
    os.environ.pop("STUDIO_DRIVES_FOR_TESTS", None)
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    want = lambda name: not only or name in only  # noqa: E731
    work = Path(tempfile.mkdtemp(prefix="second-copy-fixes-"))
    try:
        words()
        ok, how = t.pictures.ready()
        if not ok:
            sc.SKIPPED.append("everything that needs a whole backup")
            print(f"  SKIP  everything that needs a whole backup   [this computer cannot make the small pictures yet: {how}]", flush=True)
        else:
            print("One whole pretend backup, three photos with same-size sidecars, and a second drive")
            b = sc.a_finished_backup(work, sidecars=3)
            if b:
                b["killer"] = work / "killer.py"
                b["killer"].write_text(KILLER, encoding="utf-8")
                to = sc.new_drive(b, "LaCie")
                snap(b, "sorted")
                code, out = sc.second(b, to)
                ok_, diff = in_line(b, to)
                check("(a second copy, made and in line, for the cases below)", code == 0 and ok_, f"{out[-300:]} {diff}")
                snap(b, "copied")
                if want("ring"):
                    cut_at_every_point(b, to, "three photos passing their names round in a ring", a_ring)
                if want("chain"):
                    cut_at_every_point(b, to, "each photo taking the name the next one had", a_chain)
                if want("copy"):
                    a_copy_killed(b, to)
                if want("sidecars"):
                    sidecars(b, to)
                if want("busy"):
                    lock_held_by_another(b, to)
                if want("line") or want("server"):
                    one_true_line(b, to)
                if want("server"):
                    the_server(b, to)
                if want("problem"):
                    problem_tried_again(b, to)
                restore(b, "copied")
                check("after everything, the card is exactly as it was", t.card_snapshot(b["card"]) == b["card_before"])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL OK' if not sc.FAILED else str(len(sc.FAILED)) + ' FAILED'}" + (f" ({len(sc.SKIPPED)} skipped)" if sc.SKIPPED else ""))
    return 1 if sc.FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
