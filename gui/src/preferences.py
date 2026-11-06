"""Preferences: about the Torquio the app runs (everything about Dorico's setup has its own page). Torquio comes
with the app and updates with it, so there's nothing to set here yet."""
from gettext import gettext as _

from gi.repository import Adw

from . import host


class Preferences(Adw.PreferencesDialog):
    def __init__(self, window):
        super().__init__(title=_("Preferences"))
        self.window = window
        page = Adw.PreferencesPage(title=_("General"), icon_name="preferences-system-symbolic")
        about = Adw.PreferencesGroup(title=_("Torquio on This Computer"),
                                     description=_("Torquio comes with this app and is updated with it."))
        v = window.version
        rows = [(_("Version"), v.get("torquio", "")), (_("Folder"), v.get("repo", "") or host.copy_dir())]
        if v.get("branch"):  # a developer's checkout (TORQUIO_HOST_REPO)
            rows.insert(1, (_("Branch"), v["branch"]))
        for title, value in rows:
            row = Adw.ActionRow(title=title, subtitle=value or "—", use_markup=False)
            row.add_css_class("property")
            about.add(row)
        page.add(about)
        self.add(page)
