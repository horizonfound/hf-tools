#!/usr/bin/env python3
"""The carousel designer's page. A PLACEHOLDER: the next stage of the build replaces this file.

    page_html(kit_name)     the page (served live by posting_queue.py through design.handle_get)
    plain_page(words)       a small page with the Back to home button, for "can't find that shoot"

Only the kit's folder name goes into the page (html-escaped, as a data- attribute); the real page asks
/design-state for everything else. See design.py for the routes and the records.
"""
import html
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arrange_page  # noqa: E402
import brand  # noqa: E402

NOT_BUILT = "The carousel designer isn't ready yet."


def plain_page(words):
    """A small page for when there is nothing to design: the words, and the way back home."""
    return arrange_page.plain_page(words)


def page_html(kit_name):
    """The designer for one shoot. Until the page is built: a plain line, in the pickers' look."""
    attrs = " data-kit='" + html.escape(kit_name, quote=True) + "'"
    inner = "</div><div class='plain' id='designer'><p>" + html.escape(NOT_BUILT) + "</p></div></div>"
    return arrange_page._shell(brand.title("Carousel"), attrs, inner)
