"""The main window: the setup assistant until Torquio is installed, then a sidebar of pages."""
import os
from gettext import gettext as _

from gi.repository import Adw, Gio, GLib, Gtk

from . import copyhints, host
from .task import TaskDialog
from .views.display import Display
from .views.folders import Folders
from .views.keycommands import KeyCommands
from .views.maintenance import Maintenance
from .views.overview import Overview
from .views.plugins import Plugins
from .views.setup import Setup
from .widgets import confirm, error


@Gtk.Template(**copyhints.template('/tech/redfoxlabs/Torquio/window.ui'))
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
                                      ("launch", self._launch, GLib.VariantType.new("s"))):
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
        if self.stack.get_visible_child_name() == "setup" and host.Task.busy():
            return  # the setup assistant's install is running: keep showing its progress
        if self.stack.get_visible_child_name() != "main":
            self.stack.set_visible_child_name("loading")
        self.refresh_button.set_sensitive(False)
        host.in_background(self._prepare, self._show_status)

    def _prepare(self):
        """(On a worker thread.) The host's Torquio made the app's own (placed there when it differs), what the host
        has, and, when it can run Torquio, its version and status."""
        host.reach_host()
        placed = host.place_copy()
        facts = host.facts()
        if not facts.get("python"):
            return {"placed": placed, "facts": facts, "version": {}, "status": None}
        return {"placed": placed, "facts": facts, "version": host.api("version", timeout=30),
                "status": host.api("status")}

    def _message(self, title, description, icon="dialog-warning-symbolic"):
        self.message_page.set_title(title)
        self.message_page.set_description(description)
        self.message_page.set_icon_name(icon)
        self.stack.set_visible_child_name("message")

    def _show_status(self, result, err):
        self.refresh_button.set_sensitive(True)
        if err is not None:
            # Only a missing permission or a broken host gets here; what Torquio needs is the setup's job
            self._message(_("Couldn't Reach Torquio"), GLib.markup_escape_text(str(err)))
            return
        self.facts, self.version, self.status = result["facts"], result["version"], result["status"] or {}
        if result["placed"] and self.status.get("installed"):
            self._refresh_install()
        # TORQUIO_GUI_SETUP=1 shows the setup assistant on an installed system (for working on it)
        if result["status"] is None or not self.status.get("installed") or \
                os.environ.get("TORQUIO_GUI_SETUP") == "1":
            self._show_setup()
            return
        self.setup = None
        for view in self.views:
            view.refresh(self.status)
        self.stack.set_visible_child_name("main")

    def _refresh_install(self):
        """The app placed a new copy of Torquio (an update of the app, or its first run over an install from a
        checkout): point the launchers at it and refresh the prefix's settings, quietly."""
        def done(code):
            if code == 0:
                self.toast(_("Torquio's files are up to date"))
            else:
                self.toast(_("Refreshing Torquio's launchers didn't finish; Fix Icons & Launchers in Maintenance "
                             "repeats it"), timeout=6)
        host.Task("app-refresh", on_done=done).start()

    def _show_setup(self):
        if self.setup is None:
            self.setup = Setup(self)
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
