"""The main window's pages. Each has a name, a title, an icon and a widget, and refresh(status) fills it from
`torquio api status` (and whatever else it asks the host for)."""
from gi.repository import Adw


class Page:
    name = title = icon = ""

    def __init__(self, window):
        self.window = window
        self.widget = Adw.PreferencesPage()

    def refresh(self, status):
        pass
