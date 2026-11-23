#!/usr/bin/env python3
"""Nicole, Nov 22: everything is the Assistant.

In anything a photographer sees, the helper is "the Assistant" (capital A), never "your assistant" or
"my assistant", in any case. This check reads every file of the plugin and the two setup guides
(docs/SETUP-GUIDE.md, docs/SETUP-GUIDE-PC.md) and fails on any "your assistant" / "my assistant" left in:

  * the words of every script (page words, the chat lines a command prints, the JavaScript in a page),
    with comments and docstrings left out (those are notes for us, never shown);
  * every instruction part, SKILL.md, the shared notes, the hello lines (hellos/*.json) and the guides.

Kept on purpose, and allowed (tests/nicole_nov22.py): "your Assistant folder" / "my Assistant folder"
(the folder on their drive is called The Assistant), and "Also in your Assistant", the old heading that the
hello instructions name only to say it is gone.

    python3 tests/the_assistant_check.py [--root <a copy of the project>]
"""
import io
import sys
import tokenize
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nicole_nov22  # noqa: E402

TEXT = {".md", ".json", ".txt", ".html", ".js", ".css"}
fails = []
count = 0


def case(name, ok, detail=""):
    global count
    count += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else "\n      " + str(detail)[:8000]))
    if not ok:
        fails.append(name)


def shown_part_of_python(src):
    """The script with its comments and docstrings taken out: what can reach a page or the chat."""
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    sig = [t for t in toks if t.type not in (tokenize.NL, tokenize.COMMENT)]
    out = []
    for i, t in enumerate(sig):
        if t.type == tokenize.STRING:
            prev = sig[i - 1].type if i else tokenize.NEWLINE
            nxt = sig[i + 1].type if i + 1 < len(sig) else tokenize.NEWLINE
            if prev in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING) \
                    and nxt in (tokenize.NEWLINE, tokenize.ENDMARKER):
                continue
        out.append(t.string)
    # a sentence split over two string pieces ("Tell your " "assistant: ...") still counts
    return " ".join(out).replace('" "', "").replace("' '", "")


def main():
    root = HERE.parent
    if "--root" in sys.argv:
        root = Path(sys.argv[sys.argv.index("--root") + 1]).resolve()
    files = sorted(p for p in (root / "plugins" / "the-engine").rglob("*")
                   if p.is_file() and (p.suffix == ".py" or p.suffix in TEXT) and "__pycache__" not in p.parts)
    files += [root / "docs" / "SETUP-GUIDE.md", root / "docs" / "SETUP-GUIDE-PC.md"]
    left = []
    for p in files:
        if not p.is_file():
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        shown = shown_part_of_python(src) if p.suffix == ".py" else src
        found = nicole_nov22.old_words(shown)
        if found:
            left.append("%s: %d (%s)" % (p.relative_to(root), len(found), ", ".join(sorted(set(found)))))
    case("files read: the plugin and the two setup guides", len(files) > 100, len(files))
    case("nothing a photographer sees says \"your assistant\" or \"my assistant\" (Nicole, Nov 22)", not left,
         "\n      ".join(left))

    # the rules themselves, so a comparison with her earlier handoffs turns hers over the way ours were
    A = nicole_nov22.as_now
    case("rules: Tell your assistant -> Tell the Assistant", A("Tell your assistant instead.") == "Tell the Assistant instead.")
    case("rules: Let my assistant choose -> Let the Assistant choose", A("Let my assistant choose") == "Let the Assistant choose")
    case("rules: Your year with your assistant -> Your year with the Assistant",
         A("Your year with your assistant, story by story.") == "Your year with the Assistant, story by story.")
    case("rules: Your assistant’s pick -> The Assistant’s pick",
         A("Your assistant’s pick is in your slides.") == "The Assistant’s pick is in your slides.")
    case("rules: where the page server and the chat were told apart, the chat is named",
         A("Could not reach the Assistant. Tell your assistant instead.")
         == "Could not reach the Assistant. Tell the Assistant in the chat instead.")
    case("rules: the folder and the old heading are kept",
         A("Open my Assistant folder, in your Assistant folder. Also in your Assistant")
         == "Open my Assistant folder, in your Assistant folder. Also in your Assistant")
    print()
    print(("OK: %d checks, 0 failed" % count) if not fails else ("FAILED: %d of %d failed" % (len(fails), count)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
