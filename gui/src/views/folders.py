"""Folders: folders of this computer in Dorico's Open and Save dialogs, as drive letters or Desktop shortcuts."""
from gettext import gettext as _

from gi.repository import Adw, Gtk

from .. import host
from ..widgets import add, choose_file, clear, icon_button
from . import Page


class Folders(Page):
    name, title, icon = "folders", _("Folders"), "folder-symbolic"

    def __init__(self, window):
        super().__init__(window)
        self.widget.set_description(_("Make folders on this computer easy to reach from Dorico's Open and Save "
                                      "dialogs: as a drive (D:, E:…) or as a shortcut on Wine's Desktop."))
        actions = Adw.PreferencesGroup()
        add_row = Adw.ButtonRow(title=_("_Add Folder…"), use_underline=True, start_icon_name="list-add-symbolic")
        add_row.connect("activated", lambda *_: self._add())
        actions.add(add_row)
        self.widget.add(actions)
        self.drives = Adw.PreferencesGroup(title=_("Drives"))
        self.shortcuts = Adw.PreferencesGroup(title=_("Desktop Shortcuts"))
        self.empty = Adw.StatusPage(icon_name="folder-open-symbolic", title=_("No Folders Yet"),
                                    description=_("Dorico can still reach your home folder through Wine's Documents, "
                                                  "Music and Desktop folders."))
        self.empty.add_css_class("compact")
        empty_group = Adw.PreferencesGroup()
        empty_group.add(self.empty)
        self.empty_group = empty_group
        for g in (self.drives, self.shortcuts, empty_group):
            self.widget.add(g)
        self.note = Gtk.Label(label=_("New drives appear in Dorico's dialogs once Dorico and Steinberg's programs "
                                      "have been closed."), wrap=True, xalign=0, margin_top=6)
        self.note.add_css_class("dim-label")
        self.note.add_css_class("caption")
        self.drives.set_description(None)
        note_group = Adw.PreferencesGroup()
        note_group.add(self.note)
        self.widget.add(note_group)

    def refresh(self, status):
        host.in_background(lambda: host.api("folders"), self._show)

    def _show(self, data, error):
        clear(self.drives)
        clear(self.shortcuts)
        if error:
            self.window.show_error(_("Couldn't List the Folders"), error)
            return
        for d in data["drives"]:
            row = add(self.drives, Adw.ActionRow(title=d["letter"], subtitle=d["target"]))
            row.add_prefix(Gtk.Image(icon_name="drive-harddisk-symbolic"))
            row.add_suffix(icon_button("user-trash-symbolic", lambda d=d: self._remove("drive", d["letter"], d),
                                       _("Remove")))
        for s in data["shortcuts"]:
            row = add(self.shortcuts, Adw.ActionRow(title=s["name"], subtitle=s["target"]))
            row.add_prefix(Gtk.Image(icon_name="folder-symbolic"))
            row.add_suffix(icon_button("user-trash-symbolic", lambda s=s: self._remove("desktop", s["path"], s),
                                       _("Remove")))
        self.drives.set_visible(bool(data["drives"]))
        self.shortcuts.set_visible(bool(data["shortcuts"]))
        self.empty_group.set_visible(not data["drives"] and not data["shortcuts"])
        self.note.set_visible(bool(data["drives"]))

    def _add(self):
        def chosen(path):
            dialog = Adw.AlertDialog(heading=_("Add “{}”").format(path.rstrip("/").split("/")[-1] or path),
                                     body=_("How should it appear in Dorico?"))
            dialog.add_response("cancel", _("_Cancel"))
            dialog.add_response("desktop", _("On Wine's _Desktop"))
            dialog.add_response("drive", _("As a _Drive"))
            dialog.set_response_appearance("drive", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_close_response("cancel")
            dialog.connect("response", lambda d, r: self._map(path, r) if r != "cancel" else None)
            dialog.present(self.window)
        choose_file(self.window, _("Choose a Folder for Dorico"), None, chosen, folder=True)

    def _map(self, path, kind, quiet=False):
        def done(data, error):
            if error:
                self.window.show_error(_("Couldn't Add the Folder"), error)
            elif not quiet:
                self.window.toast(_("Folder added"))
            self._show(data, None) if data else None
        host.in_background(lambda: host.api("folders", "map", path, kind), done)

    def _remove(self, kind, value, entry):
        def done(data, error):
            if error:
                self.window.show_error(_("Couldn't Remove the Folder"), error)
                return
            self._show(data, None)
            # Easy to undo: put it back as it was
            toast = Adw.Toast(title=_("Removed {}").format(entry.get("letter") or entry.get("name")),
                              button_label=_("_Undo"))
            toast.connect("button-clicked", lambda *_: self._map(entry["target"], kind, quiet=True))
            self.window.toast_overlay.add_toast(toast)
        host.in_background(lambda: host.api("folders", "unmap", kind, value), done)
