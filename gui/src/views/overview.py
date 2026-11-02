"""Overview: Dorico one click away, and how the installation is doing."""
from gettext import gettext as _

from gi.repository import Adw, GLib, Gtk

from .. import host
from ..widgets import StatusRow, suffix_button
from . import Page

ENGINE = {"prebuilt": _("Prebuilt"), "compiled": _("Compiled on this computer")}
NTSYNC = {"active": (_("Active"), "ok"), "dormant": (_("Available, not enabled"), "warn"),
          "unavailable": (_("Not supported by this kernel"), "off")}


class Overview(Page):
    name, title, icon = "overview", _("Overview"), "user-home-symbolic"

    def __init__(self, window):
        super().__init__(window)
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, halign=Gtk.Align.CENTER,
                       margin_top=12, margin_bottom=6)
        icon = Gtk.Image(icon_name=window.get_application().get_application_id(), pixel_size=128)
        icon.add_css_class("hero-icon")
        self.headline = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
        self.headline.add_css_class("title-1")
        self.subline = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
        self.subline.add_css_class("dim-label")
        self.start = Gtk.Button(label=_("_Start Dorico"), use_underline=True, halign=Gtk.Align.CENTER,
                                margin_top=18, action_name="win.launch", action_target=GLib.Variant("s", "torquio-dorico"))
        self.start.add_css_class("pill")
        self.start.add_css_class("suggested-action")
        self.get_dorico = Gtk.Button(label=_("Get Dorico"), halign=Gtk.Align.CENTER, margin_top=18, visible=False,
                                     action_name="win.launch", action_target=GLib.Variant("s", "torquio-sda-handler"),
                                     tooltip_text=_("Sign in to the Steinberg Download Assistant to install Dorico"))
        self.get_dorico.add_css_class("pill")
        self.get_dorico.add_css_class("suggested-action")
        tools = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER, margin_top=6)
        for label, target in ((_("_Activation Manager"), "torquio-sam"),
                              (_("_Download Assistant"), "torquio-sda-handler")):
            b = Gtk.Button(label=label, use_underline=True, action_name="win.launch",
                           action_target=GLib.Variant("s", target))
            b.add_css_class("flat")
            tools.append(b)
        for w in (icon, self.headline, self.subline, self.start, self.get_dorico, tools):
            hero.append(w)
        group = Adw.PreferencesGroup()
        group.add(hero)
        self.widget.add(group)

        env = Adw.PreferencesGroup(title=_("Environment"))
        self.engine = StatusRow(_("Wine Engine"), "applications-system-symbolic")
        self.engine_update = suffix_button(_("Update"), lambda: window.run_task(
            _("Wine Engine"), _("Updating the Wine engine…"), _("The Wine engine is up to date"), "engine-update"),
            "suggested-action")
        self.engine.add_suffix(self.engine_update)
        self.container = StatusRow(_("Container"), "drive-harddisk-symbolic")
        self.ntsync = StatusRow(_("Kernel Fast Sync"), "power-profile-performance-symbolic")
        self.ntsync.set_tooltip_text(_("NTsync speeds up big scores' selections and edits considerably"))
        self.ntsync_enable = suffix_button(_("Enable"), window.enable_ntsync)
        self.ntsync.add_suffix(self.ntsync_enable)
        self.playback = StatusRow(_("Playback"), "audio-x-generic-symbolic")
        for row in (self.engine, self.container, self.ntsync, self.playback):
            env.add(row)
        self.widget.add(env)

    def refresh(self, status):
        apps = status["apps"]
        version = self.window.version.get("torquio", "")
        branch = self.window.version.get("branch", "")
        if apps["dorico"]:
            self.headline.set_label(_("Ready When You Are"))
            self.subline.set_label(_("Dorico runs in Torquio's Wine environment, tuned for it."))
        else:
            self.headline.set_label(_("Almost There"))
            self.subline.set_label(_("Sign in to the Steinberg Download Assistant to download and install Dorico."))
        self.start.set_visible(apps["dorico"])
        self.get_dorico.set_visible(not apps["dorico"])

        engine = status["engine"]
        text = ENGINE.get(engine["source"], engine["source"] or _("Unknown"))
        self.engine.set_state(text + (" · " + _("update available") if engine["update_available"] else ""),
                              "warn" if engine["update_available"] else "ok")
        self.engine_update.set_visible(engine["update_available"])
        c = status["container"]
        self.container.set_state(f'{c["name"]} · {c["status"]}' if c["exists"] else _("Not created"),
                                 "ok" if c["exists"] else "error")
        label, state = NTSYNC.get(status["ntsync"], (status["ntsync"], "off"))
        self.ntsync.set_state(label, state)
        self.ntsync_enable.set_visible(status["ntsync"] == "dormant")
        plugins = [n for n, key in (("NotePerformer", "noteperformer"), ("Cantai", "cantai")) if apps.get(key)]
        self.playback.set_state(", ".join(plugins) if plugins else _("Dorico's own sounds"), "ok" if plugins else "off")
        self.version_text = f"{version} ({branch})" if branch and branch not in ("main", "HEAD") else version

