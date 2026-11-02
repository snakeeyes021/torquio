"""The main window: the setup assistant until Torquio is installed, then a sidebar of pages."""
import os
from gettext import gettext as _

from gi.repository import Adw, Gio, GLib, Gtk

from . import host
from .task import TaskDialog
from .views.display import Display
from .views.folders import Folders
from .views.keycommands import KeyCommands
from .views.maintenance import Maintenance
from .views.overview import Overview
from .views.plugins import Plugins
from .views.setup import Setup
from .widgets import confirm, error


@Gtk.Template(resource_path='/tech/redfoxlabs/Torquio/window.ui')
class TorquioWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'TorquioWindow'

    toast_overlay = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    message_page = Gtk.Template.Child()
    setup_bin = Gtk.Template.Child()
    split = Gtk.Template.Child()
    sidebar = Gtk.Template.Child()
    content_page = Gtk.Template.Child()
    pages = Gtk.Template.Child()
    update_banner = Gtk.Template.Child()
    refresh_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.status, self.version = {}, {}
        self.setup = None
        for name, callback, param in (("refresh", lambda *_: self.refresh(), None),
                                      ("launch", self._launch, GLib.VariantType.new("s")),
                                      ("update", lambda *_: self._show_update(), None)):
            action = Gio.SimpleAction.new(name, param)
            action.connect("activate", callback)
            self.add_action(action)

        self.views = [Overview(self), Display(self), Folders(self), KeyCommands(self), Plugins(self),
                      Maintenance(self)]
        for view in self.views:
            self.pages.add_named(view.widget, view.name)
            row = Gtk.ListBoxRow()
            box = Gtk.Box(spacing=12, margin_top=3, margin_bottom=3)
            box.append(Gtk.Image(icon_name=view.icon))
            box.append(Gtk.Label(label=view.title, xalign=0, hexpand=True))
            row.set_child(box)
            row._view = view
            self.sidebar.append(row)
        self.sidebar.connect("row-activated", self._select)
        self.sidebar.select_row(self.sidebar.get_row_at_index(0))
        self.refresh()

    # ---- navigation ---------------------------------------------------------------------------------------

    def _select(self, listbox, row):
        self.pages.set_visible_child_name(row._view.name)
        self.content_page.set_title(row._view.title)
        self.split.set_show_content(True)

    def show_page(self, name):
        for i, view in enumerate(self.views):
            if view.name == name:
                row = self.sidebar.get_row_at_index(i)
                self.sidebar.select_row(row)
                self._select(self.sidebar, row)

    # ---- state ----------------------------------------------------------------------------------------------

    def refresh(self):
        if self.stack.get_visible_child_name() != "main":
            self.stack.set_visible_child_name("loading")
        self.refresh_button.set_sensitive(False)
        host.in_background(lambda: (host.check_version(), host.api("status")), self._show_status)

    def _message(self, title, description, icon="dialog-warning-symbolic"):
        self.message_page.set_title(title)
        self.message_page.set_description(description)
        self.message_page.set_icon_name(icon)
        self.stack.set_visible_child_name("message")

    def _show_status(self, result, err):
        self.refresh_button.set_sensitive(True)
        if isinstance(err, host.NotInstalled):
            self._show_setup(torquio_missing=True)
            return
        if isinstance(err, host.TooOld):
            self._message(_("Torquio Needs Updating"),
                          _("The Torquio on this computer is older than this app. Update it with "
                            "<tt>torquio -u</tt> in a terminal, then try again."), "software-update-available-symbolic")
            return
        if err is not None:
            self._message(_("Couldn't Reach Torquio"), GLib.markup_escape_text(str(err)))
            return
        self.version, self.status = result
        # TORQUIO_GUI_SETUP=1 shows the setup assistant on an installed system (for working on it)
        if not self.status.get("installed") or os.environ.get("TORQUIO_GUI_SETUP") == "1":
            self._show_setup()
            return
        self.setup = None
        self.update_banner.set_revealed(self.status.get("updates_pending", 0) > 0)
        for view in self.views:
            view.refresh(self.status)
        self.stack.set_visible_child_name("main")

    def _show_setup(self, torquio_missing=False):
        if self.setup is None:
            self.setup = Setup(self, torquio_missing)
            self.setup_bin.set_child(self.setup)
        self.stack.set_visible_child_name("setup")

    # ---- shared actions ---------------------------------------------------------------------------------------

    def toast(self, text, timeout=3):
        self.toast_overlay.add_toast(Adw.Toast(title=text, timeout=timeout, use_markup=False))

    def show_error(self, heading, err):
        error(self, heading, err)

    def _launch(self, action, parameter):
        name = parameter.get_string()
        labels = {"torquio-dorico": _("Starting Dorico…"), "torquio-sam": _("Starting the Activation Manager…"),
                  "torquio-sda-handler": _("Starting the Download Assistant…")}
        try:
            host.spawn([host.launcher(name)])
            self.toast(labels.get(name, _("Starting…")))
        except OSError as e:
            self.show_error(_("Couldn't Start It"), e)

    def run_task(self, title, heading, done_heading, name, *args, on_done=None):
        def finished(code, result):
            self.refresh()
            if on_done:
                on_done(code, result)
        TaskDialog(self, title, heading, done_heading, name, *args, on_done=finished).present(self)

    def apply_setting(self, key, value, on_done=None, on_cancel=None, quiet_success=None):
        """Change a setting; graphics settings restart Wine, so ask first when Dorico is open."""
        restarts_wine = key in ("manage_graphics", "manual_dpi", "match_physical_dpi", "freetype_interpreter")

        def apply():
            def done(data, err):
                if err:
                    self.show_error(_("Couldn't Change the Setting"), err)
                    if on_cancel:
                        on_cancel()
                    return
                self.toast(quiet_success or _("Applied"))
                self.refresh()
                if on_done:
                    on_done()
            host.in_background(lambda: host.api("settings", "set", key, value), done)

        if not restarts_wine:
            apply()
            return

        def check(data, err):
            if data and data.get("running"):
                dialog = confirm(self, _("Restart Wine?"),
                                 _("Applying this restarts Wine, which closes Dorico and Steinberg's programs. Save "
                                   "your work first."), _("_Restart Wine"), apply, destructive=True)
                dialog.connect("response", lambda d, r: on_cancel() if r != "ok" and on_cancel else None)
            else:
                apply()
        host.in_background(lambda: host.api("running"), check)

    def enable_ntsync(self, on_done=None):
        def done(code):
            if code == 0:
                self.toast(_("Kernel fast sync is on"))
                self.refresh()
            else:
                self.toast(_("Kernel fast sync wasn't enabled"))
            if on_done:
                on_done(code == 0)
        host.Task("ntsync", on_done=done).start()

    def _show_update(self):
        dialog = Adw.AlertDialog(heading=_("Update Torquio"), body=_("Checking what's new…"))
        dialog.add_response("cancel", _("_Later"))
        dialog.add_response("update", _("_Update"))
        dialog.set_response_appearance("update", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_response_enabled("update", False)
        dialog.set_close_response("cancel")

        def listed(data, err):
            if err:
                dialog.set_body(str(err))
                return
            if data["local_changes"]:
                dialog.set_body(_("Torquio's files were changed on this computer, so it can't update itself. "
                                  "Run torquio -u in a terminal to see what changed."))
                return
            commits = data["commits"]
            if not commits:
                dialog.set_body(_("Torquio is up to date."))
                self.update_banner.set_revealed(False)
                return
            shown = "\n".join("• " + c for c in commits[:12])
            more = len(commits) - 12
            dialog.set_body(_("{} changes, including:").format(len(commits)) + "\n\n" + shown +
                            (("\n" + _("…and {} more").format(more)) if more > 0 else ""))
            dialog.set_response_enabled("update", True)
        dialog.connect("response", lambda d, r: self.run_task(
            _("Update Torquio"), _("Updating Torquio…"), _("Torquio is up to date"), "update") if r == "update"
            else None)
        dialog.present(self)
        host.in_background(lambda: host.api("updates", "check", timeout=60), listed)
