"""Small pieces every page uses: rows that show a state, confirmations, file choosers."""
from gettext import gettext as _

from gi.repository import Adw, Gio, GLib, Gtk

from . import host

STATE_ICONS = {"ok": ("object-select-symbolic", "success"), "warn": ("dialog-warning-symbolic", "warning"),
               "error": ("dialog-error-symbolic", "error"), "off": ("", "")}


class StatusRow(Adw.ActionRow):
    """A row whose subtitle says how something is, with a small state icon at the end."""

    def __init__(self, title, icon_name=None, **kwargs):
        # Plain text: titles and values (paths, folder names) may contain "&" or "<"
        super().__init__(title=title, use_markup=False, **kwargs)
        if icon_name:
            self.add_prefix(Gtk.Image(icon_name=icon_name))
        self.state_icon = Gtk.Image(visible=False)
        self.add_suffix(self.state_icon)
        self.add_css_class("property")

    def set_state(self, text, state="off"):
        self.set_subtitle(text or "—")
        icon, css = STATE_ICONS.get(state, ("", ""))
        for c in ("success", "warning", "error"):
            self.state_icon.remove_css_class(c)
        self.state_icon.set_visible(bool(icon))
        if icon:
            self.state_icon.set_from_icon_name(icon)
            self.state_icon.add_css_class(css)


def suffix_button(label, callback, style=None, tooltip=None):
    button = Gtk.Button(label=label, valign=Gtk.Align.CENTER, tooltip_text=tooltip)
    if style:
        button.add_css_class(style)
    button.connect("clicked", lambda *_: callback())
    return button


def icon_button(icon, callback, tooltip):
    button = Gtk.Button(icon_name=icon, valign=Gtk.Align.CENTER, tooltip_text=tooltip)
    button.add_css_class("flat")
    button.connect("clicked", lambda *_: callback())
    return button


def nav_row(title, subtitle, icon, callback, opens=None):
    """A row that does something when activated. `opens`: "window" (another program's: the external-link icon),
    "page" (a page of ours: the chevron), or None (an action right here)."""
    row = Adw.ActionRow(title=title, subtitle=subtitle or "", activatable=True, use_markup=False)
    if icon:
        row.add_prefix(Gtk.Image(icon_name=icon))
    if opens:
        row.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic" if opens == "window" else "go-next-symbolic"))
    row.connect("activated", lambda *_: callback())
    return row


def confirm(parent, heading, body, action_label, callback, destructive=False, cancel_label=None):
    """An alert with Cancel and one action; callback() runs when the action is chosen."""
    dialog = Adw.AlertDialog(heading=heading, body=body)
    dialog.add_response("cancel", cancel_label or _("_Cancel"))
    dialog.add_response("ok", action_label)
    dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE if destructive
                                   else Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("cancel" if destructive else "ok")
    dialog.set_close_response("cancel")
    dialog.connect("response", lambda d, r: callback() if r == "ok" else None)
    dialog.present(parent)
    return dialog


def error(parent, heading, error_or_text):
    dialog = Adw.AlertDialog(heading=heading, body=str(error_or_text))
    dialog.add_response("close", _("_Close"))
    dialog.present(parent)


def choose_file(parent, title, patterns, callback, folder=False):
    """A file (or folder) chooser through the portal; callback(host path)."""
    dialog = Gtk.FileDialog(title=title, modal=True)
    if patterns:
        file_filter = Gtk.FileFilter()
        for p in patterns:
            file_filter.add_pattern(p)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(file_filter)
        dialog.set_filters(filters)
        dialog.set_default_filter(file_filter)

    def done(d, res):
        try:
            gfile = d.select_folder_finish(res) if folder else d.open_finish(res)
        except GLib.Error:
            return  # cancelled
        if gfile and gfile.get_path():
            callback(host.host_path(gfile.get_path()))

    (dialog.select_folder if folder else dialog.open)(parent, None, done)


def clear(container):
    """Remove every child a PreferencesGroup or ListBox got from us (they're tracked on the widget)."""
    for child in getattr(container, "_torquio_rows", []):
        container.remove(child)
    container._torquio_rows = []


def add(container, child):
    container.add(child)
    container._torquio_rows = getattr(container, "_torquio_rows", []) + [child]
    return child
