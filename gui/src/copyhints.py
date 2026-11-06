"""Developer tool for the app's copy (wording) review, not a feature: with TORQUIO_COPY_HINTS=1 every string the
app shows becomes "⟨ID short hint⟩" (the IDs of the copy list), and the app talks to a canned backend
(copyfake.py) instead of the computer's Torquio. Inert unless that variable is set."""
import gettext
import html
import json
import os
import re
import sys

ENABLED = os.environ.get("TORQUIO_COPY_HINTS") == "1"
TABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "copy-hints.json")
_labels = {}  # (context, text) -> label


def _load():
    if _labels:
        return
    with open(TABLE, encoding="utf-8") as f:
        for entry in json.load(f):
            _labels[(entry.get("context") or "", entry["text"])] = entry["label"]


def label(text, context=""):
    """The hint label for a string of the copy list; unlisted strings (the list has only the strings with voice)
    show their own text, and are logged."""
    if not ENABLED:
        return text
    _load()
    found = _labels.get((context or "", text))
    if found is None and context:
        found = _labels.get(("", text))
    if found is None:
        print(f"copyhints: not in the copy list: {text!r}", file=sys.stderr, flush=True)
        return text
    return found


def install():
    """Route gettext through the hint labels (before the app's modules bind `_`), and use the canned backend."""
    if not ENABLED:
        return
    _load()
    gettext.gettext = lambda text: label(text)
    gettext.pgettext = lambda context, text: label(text, context)
    from . import copyfake
    copyfake.install()


PARAGRAPH = re.compile(r"(<(p|li)>)(.*?)(</\2>)", re.S)


def markup(text):
    """Release notes and the like (<p> and <li> markup): each paragraph and item as its hint label."""
    if not ENABLED:
        return text
    return PARAGRAPH.sub(lambda m: m.group(1) + html.escape(label(" ".join(html.unescape(m.group(3)).split())),
                                                            quote=False) + m.group(4), text)


UI_STRING = re.compile(r'(<(property|attribute)\b([^>]*)\btranslatable="yes"([^>]*)>)([^<]*)(</\2>)')
CONTEXT = re.compile(r'\bcontext="([^"]*)"')


def _ui_text(resource_path):
    from gi.repository import Gio
    text = Gio.resources_lookup_data(resource_path, Gio.ResourceLookupFlags.NONE).get_data().decode("utf-8")

    def swap(m):
        context = CONTEXT.search(m.group(3) + m.group(4))
        new = label(html.unescape(m.group(5)), context.group(1) if context else "")
        return m.group(1) + html.escape(new, quote=False) + m.group(6)
    return UI_STRING.sub(swap, text)


def template(resource_path):
    """Gtk.Template's arguments for a .ui resource (with hint labels in hint mode)."""
    return {"string": _ui_text(resource_path)} if ENABLED else {"resource_path": resource_path}


def builder(resource_path):
    from gi.repository import Gtk
    return Gtk.Builder.new_from_string(_ui_text(resource_path), -1) if ENABLED else \
        Gtk.Builder.new_from_resource(resource_path)
