"""Torquio's GUI: the application."""
import sys
from gettext import gettext as _

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from .window import TorquioWindow  # noqa: E402


class TorquioApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self, version, application_id):
        super().__init__(application_id=application_id, flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/tech/redfoxlabs/Torquio')
        self.version = version
        self.create_action('quit', lambda *_: self.quit(), ['<control>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('shortcuts', self.on_shortcuts_action, ['<control>question'])

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = TorquioWindow(application=self)
        win.present()

    def on_about_action(self, *args):
        about = Adw.AboutDialog(application_name='Torquio',
                                application_icon=self.get_application_id(),
                                developer_name='Matthew Samson (Red Fox Labs)',
                                version=self.version,
                                website='https://github.com/snakeeyes021/torquio',
                                issue_url='https://github.com/snakeeyes021/torquio/issues',
                                license_type=Gtk.License.GPL_3_0,
                                # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
                                translator_credits=_('translator-credits'),
                                developers=['Matthew Samson'],
                                copyright='© 2026 Matthew Samson')
        about.present(self.props.active_window)

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
