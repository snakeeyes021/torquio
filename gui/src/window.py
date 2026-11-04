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
        # The window's size is kept between runs (when the app's settings schema is installed)
        app_id = self.get_application().get_application_id()
        source = Gio.SettingsSchemaSource.get_default()
        if source and source.lookup(app_id, True):
            self.settings = Gio.Settings.new(app_id)
            for key, prop in (("window-width", "default-width"), ("window-height", "default-height"),
                              ("window-maximized", "maximized")):
                self.settings.bind(key, self, prop, Gio.SettingsBindFlags.DEFAULT)
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
        # The message page's buttons: Try Again (from window.ui), and Update Torquio when it's too old for us
        try_again = self.message_page.get_child()
        self.message_page.set_child(None)
        self.update_old = Gtk.Button(label=_("_Update Torquio"), use_underline=True, visible=False)
        self.update_old.add_css_class("pill")
        self.update_old.add_css_class("suggested-action")
        self.update_old.connect("clicked", self._update_old)
        buttons = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, halign=Gtk.Align.CENTER)
        buttons.append(self.update_old)
        buttons.append(try_again)
        self.message_page.set_child(buttons)

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
        if self.stack.get_visible_child_name() == "setup" and host.Task.busy():
            return  # the setup assistant's install is running: keep showing its progress
        if self.stack.get_visible_child_name() != "main":
            self.stack.set_visible_child_name("loading")
        self.refresh_button.set_sensitive(False)
        host.in_background(lambda: (host.check_version(), host.api("status")), self._show_status)

    def _message(self, title, description, icon="dialog-warning-symbolic"):
        self.message_page.set_title(title)
        self.message_page.set_description(description)
        self.message_page.set_icon_name(icon)
        self.update_old.set_visible(False)
        self.stack.set_visible_child_name("message")

    def _show_status(self, result, err):
        self.refresh_button.set_sensitive(True)
        if isinstance(err, host.NotInstalled):
            self._show_setup(torquio_missing=True)
            return
        if isinstance(err, host.TooOld):
            self._message(_("Torquio Needs Updating"),
                          _("The Torquio on this computer is older than this app. Updating it takes a minute and "
                            "keeps your settings, Dorico and its licenses."), "software-update-available-symbolic")
            self.update_old.set_visible(True)
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
        if not getattr(self, "_checked_updates", False):
            # Once per run: fetch from GitHub if the last check is a day old (as the terminal menu does), so the
            # banner can tell there's an update
            self._checked_updates = True
            host.in_background(lambda: host.api("updates", "daily", timeout=60), self._daily_checked)

    def _daily_checked(self, data, err):
        if data and data.get("commits") and not data.get("local_changes"):
            self.update_banner.set_revealed(True)

    def _update_old(self, *args):
        self.update_old.set_sensitive(False)
        self.update_old.set_label(_("Updating…"))

        def done(result, err):
            self.update_old.set_sensitive(True)
            self.update_old.set_label(_("_Update Torquio"))
            if err:
                self.show_error(_("Couldn't Update Torquio"), err)
            else:
                self.refresh()
        host.in_background(host.update_old_torquio, done)

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
        path = host.launcher(name)

        def checked(code, err):
            if err or code != 0:
                self.show_error(_("Couldn't Start It"), _("Its launcher ({}) is missing. Fix Icons & Launchers in "
                                                          "Maintenance puts it back.").format(path))
                return
            try:
                host.spawn([path])
                self.toast(labels.get(name, _("Starting…")))
            except OSError as e:
                self.show_error(_("Couldn't Start It"), e)
        host.in_background(lambda: host.run(["test", "-x", path], timeout=10)[0], checked)

    # Tasks that replace the container, which stops Wine and with it Dorico
    STOPS_WINE = ("engine-update", "engine-rebuild", "setup-gpu")

    def task_busy(self):
        """True (and says so) when a task that changes the installation is already running."""
        if host.Task.busy():
            self.toast(_("Another task is still running; try again when it has finished"))
            return True
        return False

    def run_task(self, title, heading, done_heading, name, *args, on_done=None):
        if self.task_busy():
            return

        def finished(code, result):
            self.refresh()
            if on_done:
                on_done(code, result)

        def start():
            if not self.task_busy():
                TaskDialog(self, title, heading, done_heading, name, *args, on_done=finished).present(self)
        if name in self.STOPS_WINE:
            self.when_wine_can_stop(start, _("This replaces Torquio's container, which closes Dorico and "
                                             "Steinberg's programs. Save your work first."), _("_Continue"))
        else:
            start()

    def when_wine_can_stop(self, callback, body, action_label, on_cancel=None):
        """callback() at once when Dorico and Steinberg's programs are closed, else after asking."""
        def check(data, err):
            if data and data.get("running"):
                dialog = confirm(self, _("Close Dorico?"), body, action_label, callback, destructive=True)
                dialog.connect("response", lambda d, r: on_cancel() if r != "ok" and on_cancel else None)
            else:
                callback()
        host.in_background(lambda: host.api("running"), check)

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
        self.when_wine_can_stop(apply, _("Applying this restarts Wine, which closes Dorico and Steinberg's "
                                         "programs. Save your work first."), _("_Restart Wine"), on_cancel=on_cancel)

    def enable_ntsync(self, on_done=None):
        def done(code):
            if code == 0:
                self.toast(_("Kernel fast sync is on"))
                self.refresh()
            else:
                self.toast(_("Kernel fast sync wasn't enabled"))
            if on_done:
                on_done(code == 0)
        if not self.task_busy():
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
