#!/usr/bin/env python3
"""The product's name, in one place.

Dustin and Nicole settled on "The Assistant" (Nov 5), no sub-names, after going back and forth; no page or
message spells the name out itself, they all ask here, so a change of heart is one line. Change PRODUCT and every page, title and line follows.

A photographer can also give their helper a name of their own ("call yourself Sherman": photographers name
their first assistant), kept in the Studio File as "name". When they have, the pages and messages use that
name, and the product's name sits small beside it ("Sherman · The Assistant by Horizon Found").

The folder on their drive follows posts.HOME_NAME (an existing "The Studio" folder is kept as it is, never
renamed, since moving their files on a whim is not something the Assistant does).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PRODUCT = "The Assistant"       # the product's name (one line to change). Decided Nov 5: The Assistant, no sub-names.
MAKER = "by Horizon Found"


def own_name():
    """The name the photographer gave their helper, or None."""
    try:
        import studio_file
        n = (studio_file.load().get("name") or "").strip()
        return n or None
    except Exception:
        return None


def name():
    """What to call the helper in a sentence: their own name for it, else the product's."""
    return own_name() or PRODUCT


def the_name():
    """The same, for mid-sentence use: "Sherman" or "the Studio" (lower-case 'the' when the product's name starts with it)."""
    n = own_name()
    if n:
        return n
    return ("the " + PRODUCT[4:]) if PRODUCT.lower().startswith("the ") else PRODUCT


def short():
    """The name without a leading "The", for "my Assistant folder": "Assistant", or their own name."""
    n = own_name()
    if n:
        return n
    return PRODUCT[4:] if PRODUCT.lower().startswith("the ") else PRODUCT


def title(page=None):
    """A page's <title>: 'Posting queue · The Studio' or 'Posting queue · Sherman'."""
    return f"{page} · {name()}" if page else name()


def bar():
    """The brand mark in every page's top bar."""
    import html
    n = own_name()
    if n:
        return f"<span class='brand'><b>{html.escape(n)}</b><small>{html.escape(PRODUCT)} {MAKER}</small></span>"
    return f"<span class='brand'><b>{html.escape(PRODUCT)}</b><small>{MAKER}</small></span>"


if __name__ == "__main__":
    print(name())
