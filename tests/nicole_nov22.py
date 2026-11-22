"""Nicole, Nov 22: everything is the Assistant.

In anything a photographer sees, the helper is "the Assistant" (capital A), never
"your assistant" or "my assistant", in any case. This file holds the one set of
rules that turned our words over, so a test that compares our words with
Nicole's own earlier handoff (written before Nov 22, when hers still said
"your assistant") can turn hers over the same way and keep comparing both ways:

    import nicole_nov22
    hers = nicole_nov22.as_now(hers)

Left alone on purpose: "your Assistant folder" (the folder on their drive is
called The Assistant; "Open my Assistant folder" is its button), and the old
heading "Also in your Assistant", which tests quote only to say it is gone.
"""
import re

KEEP = (
    "Also in your Assistant",                                  # the old heading (gone since v30)
)
# Her self-introductions keep "your Assistant", the name with a capital A (her own Nov 22 line:
# "Hi! I'm your Assistant, and I'm so glad you're here."), and so do ours ("Hi, I'm Sherman, your Assistant.").
_KEEP_SELF = re.compile(r"\bI['\u2019]m (?:[A-Z]\w*, )?your Assistant\b")
_KEEP_FOLDER = re.compile(r"\b([Yy]our|[Mm]y) (Assistant(?:['’]s)? folder)")

# In order. The first two keep a sentence reading right where the page server ("the
# Assistant") and the chat ("your assistant") were told apart in one breath.
RULES = (
    (re.compile(r"Could not reach the Assistant\. Tell your assistant the name instead\."),
     "Could not reach the Assistant. Tell the Assistant the name in the chat instead."),
    (re.compile(r"Could not reach the Assistant\. Tell your assistant instead\."),
     "Could not reach the Assistant. Tell the Assistant in the chat instead."),
    (re.compile(r"\bYOUR ASSISTANT\b"), "THE ASSISTANT"),
    (re.compile(r"\bMY ASSISTANT\b"), "THE ASSISTANT"),
    (re.compile(r"\b(?:Your|My) [Aa]ssistant\b"), "The Assistant"),
    (re.compile(r"\b(?:your|my) [Aa]ssistant\b"), "the Assistant"),
)

_HOLD = "\x00HOLD%d\x00"


def as_now(text):
    """The text with every "your assistant" / "my assistant" said as "the Assistant"."""
    held = []

    def hold(s):
        held.append(s)
        return _HOLD % (len(held) - 1)

    for k in KEEP:
        text = text.replace(k, hold(k))
    text = _KEEP_FOLDER.sub(lambda m: hold(m.group(0)), text)
    text = _KEEP_SELF.sub(lambda m: hold(m.group(0)), text)
    for pat, new in RULES:
        text = pat.sub(new, text)
    for i, s in enumerate(held):
        text = text.replace(_HOLD % i, s)
    return text


OLD = re.compile(r"\b(?:your|my) assistant\b", re.I)


def old_words(text):
    """Every "your assistant" / "my assistant" still in the text, but for the ones kept on purpose."""
    t = text
    for k in KEEP:
        t = t.replace(k, "")
    t = _KEEP_FOLDER.sub("", t)
    t = _KEEP_SELF.sub("", t)
    return OLD.findall(t)


def read(path):
    """One of Nicole's handoff files, as it would say it now (her words before Nov 22 said "your assistant")."""
    return as_now(path.read_text(encoding="utf-8"))
