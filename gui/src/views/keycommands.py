"""Key Commands: back up Dorico's custom key commands, or bring a backup in."""
import os
from gettext import gettext as _

from gi.repository import Adw, Gtk

from .. import host
from ..widgets import StatusRow, add, choose_file, clear, suffix_button
from . import Page


class KeyCommands(Page):
    name, title, icon = "keycommands", _("Key Commands"), "input-keyboard-symbolic"

    def __init__(self, window):
        super().__init__(window)
        self.widget.set_description(_("Keep your Dorico shortcuts safe, or bring them over from another computer."))
        mine = Adw.PreferencesGroup(title=_("Dorico's Key Commands"))
        self.files = StatusRow(_("Custom Key Commands"), "input-keyboard-symbolic")
        mine.add(self.files)
        export = Adw.ButtonRow(title=_("_Export to Downloads"), use_underline=True,
                               start_icon_name="document-save-symbolic")
        export.connect("activated", lambda *_: self._export())
        self.export = export
        mine.add(export)
        self.widget.add(mine)

        self.backups = Adw.PreferencesGroup(title=_("Import"),
                                            description=_("Imported key commands take effect the next time Dorico "
                                                          "starts."))
        choose = Adw.ButtonRow(title=_("_Choose a Backup…"), use_underline=True,
                               start_icon_name="document-open-symbolic")
        choose.connect("activated", lambda *_: choose_file(self.window, _("Choose a Key Commands Backup"),
                                                           ["*.zip", "*.json"], self._import))
        self.choose = choose
        self.widget.add(self.backups)

    def refresh(self, status):
        host.in_background(lambda: host.api("keycommands"), self._show)

    def _show(self, data, error):
        clear(self.backups)
        if error:
            self.files.set_state(str(error), "warn")
            return
        files = data["dorico_files"]
        self.files.set_state(", ".join(files) if files else _("None yet: customize them in Dorico's Preferences"),
                             "ok" if files else "off")
        self.export.set_sensitive(bool(files))
        for path in data["backups"]:
            row = add(self.backups, Adw.ActionRow(title=os.path.basename(path), subtitle=_("In Downloads")))
            row.add_prefix(Gtk.Image(icon_name="x-office-document-symbolic"))
            row.add_suffix(suffix_button(_("Import"), lambda p=path: self._import(p)))
        add(self.backups, self.choose)

    def _export(self):
        def done(data, error):
            if error:
                self.window.show_error(_("Couldn't Export"), error)
                return
            toast = Adw.Toast(title=_("Saved {}").format(os.path.basename(data["exported"])),
                              button_label=_("_Show"))
            toast.connect("button-clicked", lambda *_: host.show_in_files(data["exported"]))
            self.window.toast_overlay.add_toast(toast)
            self.refresh(None)
        host.in_background(lambda: host.api("keycommands", "export"), done)

    def _import(self, path):
        def done(data, error):
            if error:
                self.window.show_error(_("Couldn't Import"), error)
            else:
                self.window.toast(_("Key commands will be imported when Dorico next starts"))
        host.in_background(lambda: host.api("keycommands", "import", path), done)
