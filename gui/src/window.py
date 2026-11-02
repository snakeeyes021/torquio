"""The main window: an overview of the Torquio installation on this computer (`torquio api status`), with
buttons to start Dorico and Steinberg's tools. More pages follow docs/GUI.md."""
import threading
from gettext import gettext as _

from gi.repository import Adw, Gio, GLib, Gtk

from . import host

ENGINE_SOURCES = {"prebuilt": _("Prebuilt"), "compiled": _("Compiled on this computer")}
NTSYNC = {"active": _("Active"), "dormant": _("Supported, not enabled"), "unavailable": _("Not supported by this kernel")}


def in_background(work, done):
    """Run work() in a thread (host commands take a while), then done(result, error) on the main loop."""
    def thread():
        try:
            result, error = work(), None
        except Exception as e:  # shown to the user, not raised
            result, error = None, e
        GLib.idle_add(lambda: done(result, error) and False)
    threading.Thread(target=thread, daemon=True).start()


@Gtk.Template(resource_path='/tech/redfoxlabs/Torquio/window.ui')
class TorquioWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'TorquioWindow'

    stack = Gtk.Template.Child()
    message_page = Gtk.Template.Child()
    update_banner = Gtk.Template.Child()
    environment_group = Gtk.Template.Child()
    settings_group = Gtk.Template.Child()
    refresh_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rows = []
        refresh = Gio.SimpleAction.new("refresh", None)
        refresh.connect("activate", lambda *_: self.refresh())
        self.add_action(refresh)
        launch = Gio.SimpleAction.new("launch", GLib.VariantType.new("s"))
        launch.connect("activate", self.on_launch)
        self.add_action(launch)
        self.refresh()

    def refresh(self):
        self.stack.set_visible_child_name("loading")
        self.refresh_button.set_sensitive(False)
        in_background(lambda: (host.check_version(), host.api("status")), self.show_status)

    def show_message(self, title, description):
        self.message_page.set_title(title)
        self.message_page.set_description(description)
        self.stack.set_visible_child_name("message")

    def show_status(self, result, error):
        self.refresh_button.set_sensitive(True)
        if isinstance(error, host.NotInstalled):
            self.show_message(_("Torquio Isn't Installed"),
                              _("Torquio wasn't found on this computer. Setting it up from here is coming; for now, "
                                "install it as described at github.com/snakeeyes021/torquio."))
            return
        if isinstance(error, host.TooOld):
            self.show_message(_("Torquio Needs Updating"),
                              _("The Torquio on this computer is too old for this app. Update it with "
                                "<tt>torquio -u</tt> in a terminal, then refresh."))
            return
        if error is not None:
            self.show_message(_("Couldn't Check Torquio"), GLib.markup_escape_text(str(error)))
            return
        version, status = result
        if not status.get("installed"):
            self.show_message(_("Torquio Isn't Set Up Yet"),
                              _("Torquio is on this computer, but its environment isn't installed. Run "
                                "<tt>torquio -i</tt> in a terminal; the setup assistant is coming."))
            return
        self.fill_overview(version, status)
        self.update_banner.set_revealed(status.get("updates_pending", 0) > 0)
        self.stack.set_visible_child_name("overview")

    def _row(self, group, title, subtitle):
        row = Adw.ActionRow(title=title, subtitle=GLib.markup_escape_text(subtitle or "—"))
        row.add_css_class("property")
        group.add(row)
        self._rows.append((group, row))

    def fill_overview(self, version, status):
        for group, row in self._rows:
            group.remove(row)
        self._rows = []
        engine = status["engine"]
        engine_text = ENGINE_SOURCES.get(engine["source"], engine["source"])
        if engine["update_available"]:
            engine_text += " · " + _("update available")
        self._row(self.environment_group, _("Torquio"), version.get("torquio", ""))
        self._row(self.environment_group, _("Container"),
                  f'{status["container"]["name"]} ({status["container"]["status"]})')
        self._row(self.environment_group, _("Wine Engine"), engine_text)
        self._row(self.environment_group, _("Wine Prefix"), status["prefix"]["path"])
        self._row(self.environment_group, _("Kernel Fast Sync"), NTSYNC.get(status["ntsync"], status["ntsync"]))
        settings = status["settings"]
        self._row(self.settings_group, _("Display Scaling"),
                  _("Managed by Torquio") if settings["manage_graphics"] else _("Manual"))
        self._row(self.settings_group, _("GPU for AI Plug-ins"),
                  {"auto": _("Automatic"), "off": _("Off (CPU)")}.get(settings["ai_gpu"], settings["ai_gpu"]))
        self._row(self.settings_group, _("Font Smoothing"), f'FreeType v{settings["freetype_interpreter"]}')

    def on_launch(self, action, parameter):
        name = parameter.get_string()
        try:
            host.spawn([host.launcher(name)])
        except OSError as e:
            self.add_toast_message(str(e))

    def add_toast_message(self, text):
        dialog = Adw.AlertDialog(heading=_("Couldn't Start It"), body=text)
        dialog.add_response("close", _("_Close"))
        dialog.present(self)
