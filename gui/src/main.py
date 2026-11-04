"""Torquio's GUI: the application."""
import sys
from gettext import gettext as _

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from .window import TorquioWindow  # noqa: E402

RELEASE_NOTES = """<p>The first release of Torquio's app: everything the torquio menu does, in a window.</p>
<ul>
  <li>A setup assistant that checks what's needed, finds your installers and installs Torquio</li>
  <li>Dorico, the Activation Manager and the Download Assistant one click away</li>
  <li>Display scaling, folders, key commands and the GPU for AI plug-ins</li>
  <li>Wine's tools, repairs, engine updates, logs for bug reports, and uninstalling</li>
</ul>"""


class TorquioApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self, version, application_id):
        super().__init__(application_id=application_id, flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/tech/redfoxlabs/Torquio')
        self.version = version
        self.create_action('quit', lambda *_: self.quit(), ['<primary>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action, ['<primary>comma'])
        self.create_action('shortcuts', self.on_shortcuts_action, ['<primary>question'])
        self.set_accels_for_action('win.refresh', ['<primary>r', 'F5'])
        self.set_accels_for_action("win.launch('torquio-dorico')", ['<primary>Return'])

    def do_startup(self):
        Adw.Application.do_startup(self)
        css = Gtk.CssProvider()
        css.load_from_resource('/tech/redfoxlabs/Torquio/style.css')
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = TorquioWindow(application=self)
        win.present()

    def on_about_action(self, *args):
        win = self.props.active_window
        torquio = getattr(win, "version", {}).get("torquio", "")
        about = Adw.AboutDialog(application_name='Torquio',
                                application_icon=self.get_application_id(),
                                developer_name='Matthew Samson (Red Fox Labs)',
                                version=self.version,
                                comments=_("Steinberg's Dorico on Linux, set up for you"),
                                website='https://github.com/snakeeyes021/torquio',
                                issue_url='https://github.com/snakeeyes021/torquio/issues',
                                license_type=Gtk.License.GPL_3_0,
                                release_notes=RELEASE_NOTES,
                                release_notes_version=self.version,
                                debug_info=f"App {self.version}\nTorquio {torquio}\n",
                                # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
                                translator_credits=_('translator-credits'),
                                developers=['Matthew Samson'],
                                copyright='© 2026 Matthew Samson')
        about.add_acknowledgement_section(_("Built On"), [
            "Wine https://www.winehq.org/",
            "zhiyi/wine (DirectComposition) https://gitlab.winehq.org/zhiyi/wine",
            "vkd3d-proton https://github.com/HansKristian-Work/vkd3d-proton",
            "Distrobox https://distrobox.it/"])
        about.add_acknowledgement_section(_("With Thanks To"), [
            "vstenv https://github.com/dguedry/vstenv",
            "steinberg_fix https://github.com/chiarfe/steinberg_fix"])
        about.add_legal_section("Wine", "© the Wine project authors", Gtk.License.LGPL_2_1, None)
        about.present(win)

    def on_preferences_action(self, *args):
        from .preferences import Preferences
        Preferences(self.props.active_window).present(self.props.active_window)

    def on_shortcuts_action(self, *args):
        builder = Gtk.Builder.new_from_resource('/tech/redfoxlabs/Torquio/shortcuts-dialog.ui')
        builder.get_object('shortcuts_dialog').present(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version, application_id):
    """The application's entry point."""
    app = TorquioApplication(version, application_id)
    return app.run(sys.argv)
