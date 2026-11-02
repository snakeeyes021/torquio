"""Preferences: the few things about Torquio itself (everything about Dorico's setup has its own page)."""
from gettext import gettext as _

from gi.repository import Adw

from . import host


class Preferences(Adw.PreferencesDialog):
    def __init__(self, window):
        super().__init__(title=_("Preferences"))
        self.window = window
        page = Adw.PreferencesPage(title=_("General"), icon_name="preferences-system-symbolic")
        updates = Adw.PreferencesGroup(title=_("Updates"))
        self.check = Adw.SwitchRow(title=_("Check for Updates"),
                                   subtitle=_("Looks on GitHub at most once a day and shows a banner when there's a "
                                              "new version"),
                                   active=window.status.get("settings", {}).get("check_for_updates", True))
        self.check.connect("notify::active", lambda *_: window.apply_setting(
            "check_for_updates", "true" if self.check.get_active() else "false",
            quiet_success=_("Saved")))
        updates.add(self.check)
        page.add(updates)
        about = Adw.PreferencesGroup(title=_("Torquio on This Computer"))
        v = window.version
        for title, value in ((_("Version"), v.get("torquio", "")), (_("Branch"), v.get("branch", "")),
                             (_("Folder"), v.get("repo", ""))):
            row = Adw.ActionRow(title=title, subtitle=value or "—")
            row.add_css_class("property")
            about.add(row)
        page.add(about)
        self.add(page)
