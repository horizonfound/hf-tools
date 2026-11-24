#!/usr/bin/env python3
"""GitHub's workflow file is one GitHub will run: it parses, and every step's condition names a step its own job has.

    python3 tests/workflow_check.py

Why: after the merge of two lanes (Nov 17) the pull_request `paths:` list was closed twice, so the file was not YAML
at all, and GitHub refuses an invalid workflow file outright: none of the Windows or Mac jobs ran, and every test
"registered in the workflow" never ran. The same day a step in the `mac` job waited on `steps.py.outcome`, an id
only the Windows jobs have, so that step was skipped silently on every run. This check catches both before a push.

How the file is parsed: with PyYAML when this Python has it, else with the Mac's own ruby (both GitHub's runners and
every Mac carry ruby), else that part is SKIP and the rest still runs. Plain Python otherwise; nothing is written.
Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "check-pc.yml"

RESULTS = {"PASS": 0, "FAIL": 0, "SKIP": 0}


def check(name, ok, detail=""):
    RESULTS["PASS" if ok else "FAIL"] += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else "\n      " + str(detail)[:600]), flush=True)


def skip(name):
    RESULTS["SKIP"] += 1
    print("SKIP  " + name, flush=True)


def parse(path):
    """The file as GitHub would read it: (the document, or None, and how it was read or why not)."""
    try:
        import yaml  # noqa: F401
    except ImportError:
        yaml = None
    if yaml is not None:
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8")), "PyYAML"
        except yaml.YAMLError as e:
            return None, "PyYAML: " + str(e).replace("\n", " ")[:300]
    ruby = shutil.which("ruby")
    if not ruby:
        return None, "no YAML reader on this computer (neither PyYAML nor ruby)"
    r = subprocess.run([ruby, "-ryaml", "-rjson", "-e", "puts JSON.generate(YAML.load_file(ARGV[0]))", str(path)],
                       capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0:
        return None, "ruby: " + (r.stderr or r.stdout).strip().splitlines()[0][:300] if (r.stderr or r.stdout).strip() else "ruby: failed"
    try:
        return json.loads(r.stdout), "ruby"
    except ValueError as e:
        return None, "ruby gave something that isn't JSON: " + str(e)[:200]


def jobs_by_lines(text):
    """{job name: [(line number, line)]} read from the file's own lines, so the step-id check works even when the
    file doesn't parse (and says which line is wrong)."""
    out, job, in_jobs = {}, None, False
    for i, line in enumerate(text.splitlines(), 1):
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if m:
            job = m.group(1)
            out.setdefault(job, [])
            continue
        if job is not None:
            out[job].append((i, line))
    return out


def main():
    text = WORKFLOW.read_text(encoding="utf-8")
    print("-- the file parses (GitHub refuses a workflow file that doesn't, and then no job runs)")
    doc, how = parse(WORKFLOW)
    if doc is None and how.startswith("no YAML reader"):
        skip("the workflow file parses as YAML: " + how)
    else:
        check("the workflow file parses as YAML (read with %s)" % how.split(":")[0], isinstance(doc, dict), how)
    if isinstance(doc, dict):
        jobs = doc.get("jobs") if isinstance(doc.get("jobs"), dict) else {}
        # mac-page became four jobs on Nov 23: as one it ran past its 50 minutes on GitHub's Mac and was cut off
        check("it has its eight jobs: windows, windows-page, mac, mac-talking, and the four page jobs on the Mac",
              sorted(jobs) == ["mac", "mac-page", "mac-page-design", "mac-page-reel", "mac-page-vault", "mac-talking", "windows", "windows-page"], sorted(jobs))
        check("every page job on the Mac may fail without failing the check, and has a time limit of its own",
              all(isinstance(jobs.get(j), dict) and jobs[j].get("continue-on-error") is True and isinstance(jobs[j].get("timeout-minutes"), int)
                  for j in ("mac-page", "mac-page-design", "mac-page-reel", "mac-page-vault")))
        # YAML reads a bare `on` as the boolean true (ruby's JSON then spells it "true"); GitHub reads it as the word
        on = next((doc[k] for k in ("on", True, "true") if isinstance(doc.get(k), dict)), {})
        push_paths = (on.get("push") or {}).get("paths") if isinstance(on.get("push"), dict) else None
        pr_paths = (on.get("pull_request") or {}).get("paths") if isinstance(on.get("pull_request"), dict) else None
        check("push and pull_request each have one list of paths, and the two lists are the same",
              isinstance(push_paths, list) and isinstance(pr_paths, list) and push_paths == pr_paths and len(push_paths) > 20,
              (type(push_paths).__name__, type(pr_paths).__name__))
        for name, job in sorted(jobs.items()):
            steps = job.get("steps") if isinstance(job, dict) else None
            check("job %s: a list of steps, each a mapping with a name or a uses" % name,
                  isinstance(steps, list) and steps and all(isinstance(s, dict) and ("name" in s or "uses" in s) for s in steps),
                  str(steps)[:200] if not isinstance(steps, list) else [s for s in steps if not isinstance(s, dict)])

    print("\n-- every step's condition names a step its own job has (else the condition is false and the step is skipped silently)")
    for name, lines in jobs_by_lines(text).items():
        ids = {m.group(1) for _, ln in lines for m in [re.match(r"^\s+- id:\s*([A-Za-z0-9_-]+)\s*$", ln)] if m}
        wrong = []
        for i, ln in lines:
            for sid in re.findall(r"steps\.([A-Za-z0-9_-]+)\.(?:outcome|conclusion|outputs)", ln):
                if sid not in ids:
                    wrong.append((i, sid))
        check("job %s: every steps.<id> in a condition is an id of that job (%s)" % (name, ", ".join(sorted(ids)) or "no ids"),
              not wrong, "line %d names steps.%s, which this job doesn't have" % wrong[0] if wrong else "")
    check("the two closing lines of the paths lists appear once each (the merge of Nov 17 left one twice)",
          text.count('"tests/workflow_check.py", ".github/workflows/check-pc.yml"]') == 2,
          text.count('"tests/workflow_check.py", ".github/workflows/check-pc.yml"]'))

    print("\n%d passed, %d failed, %d skipped." % (RESULTS["PASS"], RESULTS["FAIL"], RESULTS["SKIP"]))
    return 1 if RESULTS["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
