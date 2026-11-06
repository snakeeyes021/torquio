"""Maintenance: Wine's own tools, repairs, the Wine engine, logs for bug reports, and uninstalling."""
import os
from gettext import gettext as _

from gi.repository import Adw, Gtk

from .. import host
from ..widgets import StatusRow, choose_file, confirm, nav_row, suffix_button
from . import Page

WINE_TOOLS = [("winecfg", _("Wine Configuration"), _("Libraries, audio and Windows version"), "preferences-system-symbolic"),
              ("regedit", _("Registry Editor"), None, "emblem-system-symbolic"),
              ("control", _("Control Panel"), None, "applications-utilities-symbolic"),
              ("explorer", _("File Manager"), _("Wine's own, inside the prefix"), "folder-open-symbolic"),
              ("cmd", _("Command Prompt"), None, "utilities-terminal-symbolic")]


class Maintenance(Page):
    name, title, icon = "maintenance", _("Maintenance"), "applications-system-symbolic"

    def __init__(self, window):
        super().__init__(window)
        tools = Adw.PreferencesGroup(title=_("Wine Tools"))
        for name, title, subtitle, icon in WINE_TOOLS:
            tools.add(nav_row(title, subtitle, icon, lambda n=name, t=title: self._wine(n, t), opens="window"))
        tools.add(nav_row(_("Run a Windows Program…"), _("An installer (.exe or .msi) or a program"),
                          "application-x-executable-symbolic", self._run_exe, opens="window"))
        tools.add(nav_row(_("Open Drive C:"), _("The Wine prefix in your file manager"), "drive-harddisk-symbolic",
                          lambda: host.open_folder(os.path.join(self.window.status["prefix"]["path"], "drive_c")),
                          opens="window"))
        self.widget.add(tools)

        wine = Adw.PreferencesGroup(title=_("Wine"))
        wine.add(nav_row(_("Restart Wine"), _("Restarts Wine's Windows session (wineboot)"), "view-refresh-symbolic",
                         lambda: self._stop_wine("reboot")))
        wine.add(nav_row(_("Close All Wine Programs"), _("Dorico, the Activation Manager and the Download Assistant "
                                                         "too"), "system-shutdown-symbolic",
                         lambda: self._stop_wine("shutdown")))
        self.widget.add(wine)

        repair = Adw.PreferencesGroup(title=_("Repair"))
        repair.add(nav_row(_("Fix Icons & Launchers"), _("Menu entries, file types and launchers"),
                           "emblem-system-symbolic", lambda: window.run_task(
                               _("Fix Icons & Launchers"), _("Refreshing icons and launchers…"),
                               _("Icons and launchers are refreshed"), "fix-icons")))
        self.engine = StatusRow(_("Wine Engine"), "applications-system-symbolic")
        self.engine.add_suffix(suffix_button(_("Rebuild…"), self._rebuild, tooltip=_("Compile it on this computer")))
        self.engine_update = suffix_button(_("Update"), lambda: window.run_task(
            _("Wine Engine"), _("Updating the Wine engine…"), _("The Wine engine is up to date"), "engine-update"),
            "suggested-action")
        self.engine.add_suffix(self.engine_update)
        repair.add(self.engine)
        self.ntsync = StatusRow(_("Kernel Fast Sync"), "power-profile-performance-symbolic")
        self.ntsync_enable = suffix_button(_("Enable"), window.enable_ntsync)
        self.ntsync.add_suffix(self.ntsync_enable)
        repair.add(self.ntsync)
        repair.add(nav_row(_("Export Logs"), _("A zip for bug reports, with personal details removed"),
                           "document-send-symbolic", self._logs))
        self.widget.add(repair)

        danger = Adw.PreferencesGroup()
        uninstall = Adw.ButtonRow(title=_("_Uninstall Torquio…"), use_underline=True)
        uninstall.add_css_class("destructive-action")
        uninstall.connect("activated", lambda *_: UninstallDialog(window).present(window))
        danger.add(uninstall)
        self.widget.add(danger)

    def refresh(self, status):
        e = status["engine"]
        source = {"prebuilt": _("Prebuilt"), "compiled": _("Compiled on this computer")}.get(e["source"], e["source"])
        self.engine.set_state(source + (" · " + _("update available") if e["update_available"] else ""),
                              "warn" if e["update_available"] else "ok")
        self.engine_update.set_visible(e["update_available"])
        nt = status["ntsync"]
        self.ntsync.set_state({"active": _("Active"), "dormant": _("Available, not enabled"),
                               "unavailable": _("Not supported by this kernel")}.get(nt, nt),
                              {"active": "ok", "dormant": "warn"}.get(nt, "off"))
        self.ntsync_enable.set_visible(nt == "dormant")

    def _wine(self, name, title):
        self.window.toast(_("Opening {}…").format(title))
        host.Task("wine", name, on_done=lambda code: self._wine_failed(title) if code not in (0, None) else None).start()

    def _wine_failed(self, title):
        self.window.show_error(_("{} Didn't Start").format(title),
                               _("Wine couldn't run it. Is Torquio's container working? Export Logs collects the "
                                 "details for a bug report."))

    def _run_exe(self):
        def chosen(path):
            self.window.toast(_("Running {}…").format(os.path.basename(path)))
            host.Task("wine", "exe", path, on_done=lambda code: self._wine_failed(os.path.basename(path))
                      if code != 0 else None).start()
        choose_file(self.window, _("Choose a Windows Program"), ["*.exe", "*.msi", "*.EXE", "*.MSI"], chosen)

    def _stop_wine(self, how):
        def go():
            self.window.toast(_("Restarting Wine…") if how == "reboot" else _("Closing Wine programs…"))
            host.Task("wine", how, on_done=lambda code: self.window.toast(
                (_("Wine restarted") if how == "reboot" else _("Wine programs closed")) if code == 0
                else _("Wine didn't respond; try again, or restart your computer"))).start()

        def check(data, error):
            if data and data.get("running"):
                confirm(self.window, _("Close Dorico?"),
                        _("Dorico or one of Steinberg's programs is open, and this closes it. Save your work first."),
                        _("_Close and Continue"), go, destructive=True)
            else:
                go()
        host.in_background(lambda: host.api("running"), check)

    def _rebuild(self):
        confirm(self.window, _("Compile the Wine Engine?"),
                _("Compiling Torquio's Wine engine on this computer takes 20 to 40 minutes and closes Dorico while it "
                  "runs. The prebuilt engine is the same; this is for testing changes to it."),
                _("_Compile"), lambda: self.window.run_task(_("Wine Engine"), _("Compiling the Wine engine…"),
                                                            _("The Wine engine is compiled"), "engine-rebuild"))

    def _logs(self):
        def done(code, result):
            if code == 0 and result and result.get("path"):
                toast = Adw.Toast(title=_("Logs saved to Downloads"), button_label=_("_Show"), timeout=8)
                toast.set_use_markup(False)
                toast.connect("button-clicked", lambda *_: host.show_in_files(result["path"]))
                self.window.toast_overlay.add_toast(toast)
        self.window.run_task(_("Export Logs"), _("Collecting logs…"),
                             _("Logs saved. Project names are still in them: have a look before posting them "
                               "publicly."), "logs", on_done=done)


class UninstallDialog(Adw.Dialog):
    """What uninstalling deletes, what it would lose (activated licenses, projects in the prefix), and a typed
    confirmation, as in the terminal."""

    WORD = "uninstall"

    def __init__(self, window):
        super().__init__(title=_("Uninstall Torquio"), content_width=520, content_height=620)
        self.window = window
        self.page = Adw.PreferencesPage()
        header = Adw.HeaderBar()
        toolbar = Adw.ToolbarView(content=self.page)
        toolbar.add_top_bar(header)
        self.set_child(toolbar)
        intro = Adw.PreferencesGroup(description=_(
            "This deletes Torquio's container, its Wine prefix (with Dorico, its settings and anything else installed "
            "in it), launchers, file types and icons. Your own files and projects outside the prefix stay."))
        self.page.add(intro)
        self.checks = Adw.PreferencesGroup(title=_("Checking…"))
        self.page.add(self.checks)
        self.confirm_group = Adw.PreferencesGroup(visible=False)
        self.restore = Adw.SwitchRow(use_markup=False, title=_("Restore My Desktop's Scaling Setting"), active=True, visible=False)
        self.entry = Adw.EntryRow(title=_("Type “{}” to confirm").format(self.WORD))
        self.entry.connect("changed", lambda *_: self._update())
        self.aware = Adw.SwitchRow(use_markup=False, title=_("I understand those licenses can't be deactivated afterwards"),
                                   visible=False)
        self.aware.connect("notify::active", lambda *_: self._update())
        # As in the terminal, every uninstall asks about licenses and projects, whatever the checks found
        self.deactivated = Adw.SwitchRow(use_markup=False, title=_("I've deactivated every license in this installation"),
                                         subtitle=_("Steinberg's products and any plug-ins such as Cantai"),
                                         visible=False)
        self.deactivated.connect("notify::active", lambda *_: self._update())
        self.saved = Adw.SwitchRow(use_markup=False, title=_("I've saved the projects I want to keep elsewhere"), visible=False)
        self.saved.connect("notify::active", lambda *_: self._update())
        # For someone removing the app as well: its copy of Torquio goes too (otherwise the app puts it back the
        # next time it starts). Not offered when the app runs a developer's checkout.
        self.remove_app = Adw.SwitchRow(use_markup=False, title=_("I'm Removing the App Too"),
                                        subtitle=_("Also deletes the app's own copy of Torquio's files"),
                                        visible=not host.DEV_REPO)
        for row in (self.restore, self.remove_app, self.aware, self.deactivated, self.saved, self.entry):
            self.confirm_group.add(row)
        self.page.add(self.confirm_group)
        self.button = Gtk.Button(label=_("_Uninstall"), use_underline=True, sensitive=False,
                                 halign=Gtk.Align.CENTER, margin_top=12)
        self.button.add_css_class("pill")
        self.button.add_css_class("destructive-action")
        self.button.connect("clicked", lambda *_: self._go())
        group = Adw.PreferencesGroup()
        group.add(self.button)
        self.page.add(group)
        host.in_background(lambda: host.api("guards", timeout=120), self._show)

    def _show(self, data, error):
        self.checks.set_title(_("Before You Go"))
        if error:
            row = StatusRow(_("Checks"))
            row.set_state(str(error), "warn")
            self.checks.add(row)
            return
        active = data["steinberg_active"] + [p["name"] for p in data["plugins"]]
        lic = StatusRow(_("Licenses"), "channel-secure-symbolic")
        if active:
            lic.set_state(_("Still activated: {}. Deactivate them first (Steinberg's in the Activation Manager, "
                            "Cantai in Cantai), or they can't be deactivated from this computer.").format(
                ", ".join(active)), "error")
            self.aware.set_visible(True)
        elif data["steinberg_unknown"]:
            lic.set_state(_("Couldn't tell whether Steinberg's licenses are deactivated. Check in the Activation "
                            "Manager that every product is deactivated."), "warn")
            self.deactivated.set_visible(True)
        else:
            lic.set_state(_("None activated"), "ok")
            self.deactivated.set_visible(True)
        self.checks.add(lic)
        projects = StatusRow(_("Projects in the Prefix"), "x-office-document-symbolic")
        if data["projects"]:
            names = ", ".join(os.path.basename(p) for p in data["projects"][:5])
            more = len(data["projects"]) - 5
            projects.set_state(_("Deleted with it: {}").format(names) + (f" (+{more})" if more > 0 else ""), "error")
        else:
            projects.set_state(_("None found"), "ok")
            self.saved.set_title(_("I've backed up any projects I kept in the prefix"))
        self.saved.set_visible(True)
        self.checks.add(projects)
        self.restore.set_visible(bool(data.get("restorable")))
        if data.get("restorable"):
            self.restore.set_subtitle(_("Back to {}").format(data["restorable"]["original"]))
        self.confirm_group.set_visible(True)
        self.entry.grab_focus()

    def _update(self):
        ok = self.entry.get_text().strip().lower() == self.WORD
        for row in (self.aware, self.deactivated, self.saved):
            if row.get_visible():
                ok = ok and row.get_active()
        self.button.set_sensitive(ok)

    def _go(self):
        restore = "true" if self.restore.get_visible() and self.restore.get_active() else "false"
        app = "remove" if self.remove_app.get_visible() and self.remove_app.get_active() else "keep"
        self.close()
        def done(code, result):
            if code == 0 and app == "remove":
                # No refresh: it would put the app's copy straight back
                self.window.removed()
            else:
                self.window.refresh()
        self.window.run_task(_("Uninstall Torquio"), _("Uninstalling…"), _("Torquio has been removed"),
                             "uninstall", restore, app, on_done=done)
