#!/usr/bin/env python3
"""The product's name, in one place.

Dustin and Nicole are still deciding what to call it (Nov 5: "The Studio" or "The Assistant"), so no page or
message spells the name out itself; they all ask here. Change PRODUCT and every page, title and line follows.

A photographer can also give their helper a name of their own ("call yourself Sherman": photographers name
their first assistant), kept in the Studio File as "name". When they have, the pages and messages use that
name, and the product's name sits small beside it ("Sherman · The Studio by Horizon Found").

Folder names on their drive (the "The Studio" folder) and the tool tag inside XMP sidecars are not here on
purpose: renaming those would move their files or rewrite sidecars, which the Studio never does on a whim.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PRODUCT = "The Studio"          # the product's name (one line to change)
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
