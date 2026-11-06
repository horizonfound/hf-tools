#!/usr/bin/env python3
"""Check the plugin the way Claude's own uploader does, BEFORE anyone is handed a file.

Why this exists (Nov 5, 2026): Nicole's first upload was refused with
"Skill 'skills/studio-manager': field 'description' in SKILL.md must be at most 1024 characters".
The description was 1,026. Nobody had ever checked. This script checks every rule we know of,
and build_zip.sh will not make the upload file unless it passes.

    python3 tools/check_plugin.py            check plugins/the-engine as it is on disk
    python3 tools/check_plugin.py <folder>   check another copy (an unpacked zip, say)

Exit 0: clean. Exit 1: something to fix (listed as STOP). NOTE lines are worth a look but do not
stop a build.

What is proven and what is caution: the 1,024 limit on a skill's description is PROVEN (it is Claude's
own error text). The other header rules (no angle brackets, no colon-then-space inside the text, name
matches its folder) come from Claude's published rules for skills or from how strict readers of these
headers behave; Claude's uploader did not complain about them on Nov 5, but they cost nothing to keep.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "plugins" / "the-engine"

DESC_MAX = 1024          # seen in Claude's own error message, Nov 5
DESC_COMFORT = 950       # leave room: a one-word edit should never tip it over
NAME_OK = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
BIG_FILE = 5 * 1024 * 1024
stops, notes = [], []


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        stops.append(f"{rel(path)}: no header block at the top (it must start with a line of ---, then name and description, then ---)")
        return None
    fields = {}
    for n, line in enumerate(m.group(1).split("\n"), 2):
        if not line.strip():
            continue
        if "\t" in line:
            stops.append(f"{rel(path)} line {n}: a tab in the header")
        key, sep, value = line.partition(":")
        if not sep or not re.match(r"^[A-Za-z_-]+$", key):
            stops.append(f"{rel(path)} line {n}: header line is not 'word: text' ({line[:50]!r})")
            continue
        value = value.strip()
        fields[key] = value
        if ": " in value or value.endswith(":"):
            stops.append(f"{rel(path)}: '{key}' has a colon followed by a space inside its text; a strict reader stops there. Reword without the colon.")
        if "<" in value or ">" in value:
            stops.append(f"{rel(path)}: '{key}' has an angle bracket (< or >); Claude's rules forbid them in a header. Write the words out.")
        if " #" in value:
            stops.append(f"{rel(path)}: '{key}' has ' #' in it; everything after it would be dropped as a comment")
        if value[:1] in "\"'[{>|*&!%@`":
            stops.append(f"{rel(path)}: '{key}' starts with {value[:1]!r}, which has a special meaning in a header")
    return fields


def rel(p):
    try:
        return str(Path(p).relative_to(PLUGIN))
    except ValueError:
        return str(p)


def main():
    if not PLUGIN.is_dir():
        print(f"STOP: no plugin folder at {PLUGIN}")
        return 1
    # the manifest
    man = PLUGIN / ".claude-plugin" / "plugin.json"
    if not man.is_file():
        stops.append(".claude-plugin/plugin.json is missing (Claude: 'The archive must contain a .claude-plugin/plugin.json manifest')")
    else:
        try:
            d = json.loads(man.read_text(encoding="utf-8"))
            if not NAME_OK.match(str(d.get("name", ""))):
                stops.append(f"plugin.json: name {d.get('name')!r} must be lowercase words joined by hyphens")
            if not d.get("description"):
                stops.append("plugin.json: no description")
            if "version" in d:
                notes.append(f"plugin.json has a fixed version ({d['version']}). An installed copy only updates when that text changes; it was taken out on Nov 5 on purpose.")
        except ValueError as e:
            stops.append(f"plugin.json is not valid JSON: {e}")
    # skills
    skills = sorted((PLUGIN / "skills").glob("*/SKILL.md")) if (PLUGIN / "skills").is_dir() else []
    if not skills:
        stops.append("no skills found (skills/<name>/SKILL.md)")
    for s in skills:
        f = frontmatter(s)
        if f is None:
            continue
        folder = s.parent.name
        name, desc = f.get("name", ""), f.get("description", "")
        if not name:
            stops.append(f"{rel(s)}: no name")
        elif name != folder:
            stops.append(f"{rel(s)}: name is {name!r} but its folder is {folder!r}; they must match")
        if name and (not NAME_OK.match(name) or len(name) > 64):
            stops.append(f"{rel(s)}: name {name!r} must be lowercase letters, numbers and hyphens, 64 at most")
        if re.search(r"claude|anthropic", name):
            stops.append(f"{rel(s)}: a skill name may not contain 'claude' or 'anthropic'")
        if not desc:
            stops.append(f"{rel(s)}: no description")
        n = max(len(desc), len(desc.encode("utf-8")))
        if n > DESC_MAX:
            stops.append(f"{rel(s)}: description is {n} characters; the limit is {DESC_MAX}. THIS is what refused Nicole's upload on Nov 5.")
        elif n > DESC_COMFORT:
            notes.append(f"{rel(s)}: description is {n} characters, close to the {DESC_MAX} limit")
    # commands
    for c in sorted((PLUGIN / "commands").glob("*.md")) if (PLUGIN / "commands").is_dir() else []:
        f = frontmatter(c)
        if f is not None and not f.get("description"):
            stops.append(f"{rel(c)}: no description")
    # files
    total = count = 0
    for p in sorted(PLUGIN.rglob("*")):
        if p.is_symlink():
            stops.append(f"{rel(p)}: a symbolic link; an upload cannot carry one")
            continue
        if not p.is_file() or "__pycache__" in p.parts or p.name == ".DS_Store":
            continue
        size = p.stat().st_size
        total += size
        count += 1
        if size > BIG_FILE:
            notes.append(f"{rel(p)}: {size / 1e6:.1f} MB, a large file to carry in a plugin")
        if p.suffix in (".zip", ".pdf", ".mp4", ".mov", ".mp3", ".wav", ".psd"):
            notes.append(f"{rel(p)}: a {p.suffix} file inside the plugin; does it need to ship to every photographer?")
    if (PLUGIN / "bin").exists():
        stops.append("a top-level bin/ folder; Claude rejects it. Scripts belong in a skill's scripts/ folder.")
    # every script must load under the Python a new Mac comes with (3.9), when this Mac has it
    old = Path("/usr/bin/python3")
    scripts = sorted(PLUGIN.rglob("*.py"))
    if old.exists() and scripts:
        code = ("import sys\nbad=[]\nfor f in sys.argv[1:]:\n    try: compile(open(f,encoding='utf-8').read(), f, 'exec')\n"
                "    except SyntaxError as e: bad.append(f'{f}: line {e.lineno}: {e.msg}')\nprint('\\n'.join(bad))")
        try:
            out = subprocess.run([str(old), "-c", code] + [str(s) for s in scripts], capture_output=True, text=True, timeout=120)
            ver = subprocess.run([str(old), "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
            for line in out.stdout.strip().split("\n"):
                if line.strip():
                    stops.append(f"does not load under the Mac's own {ver}: {line.replace(str(PLUGIN) + '/', '')}")
            if out.returncode != 0 and not out.stdout.strip():
                notes.append(f"could not run the old-Python check ({out.stderr.strip()[:120]})")
        except (OSError, subprocess.SubprocessError) as e:
            notes.append(f"could not run the old-Python check ({e})")
    for n in notes:
        print("NOTE:", n)
    for s in stops:
        print("STOP:", s)
    print(f"{len(skills)} skills, {count} files, {total / 1e6:.1f} MB.", "CLEAN: safe to build the upload file." if not stops else f"{len(stops)} thing(s) to fix first.")
    return 1 if stops else 0


if __name__ == "__main__":
    sys.exit(main())
