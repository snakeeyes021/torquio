"""The setup assistant, shown until Torquio is installed: what it needs, a few choices, then the install."""
import json
import os
from gettext import gettext as _

from gi.repository import Adw, Gtk

from .. import host
from ..task import TaskView
from ..widgets import StatusRow, add, choose_file, clear, suffix_button

SDA_PAGE = "https://o.steinberg.net/index.php?id=steinberg_download_assistant&L=1"
MEDIABAY_PAGE = "https://o.steinberg.net/index.php?id=15368&L=1"
REPO_URL = "https://github.com/snakeeyes021/torquio.git"
INSTALLERS = [("sda", _("Steinberg Download Assistant"), True, SDA_PAGE,
               "Steinberg_Download_Assistant_*_Installer_win*.exe"),
              ("mediabay", _("Steinberg MediaBay"), True, MEDIABAY_PAGE, "MediaBay_Installer_win64*.zip"),
              ("noteperformer", _("NotePerformer"), False, "https://www.noteperformer.com/", "NotePerformer-Installer-*.exe"),
              ("cantai", _("Cantai"), False, "https://www.cantai.app/", "Cantai-Windows-*Installer-*.exe.zip")]


def open_uri(window, uri):
    Gtk.UriLauncher.new(uri).launch(window, None, None)


def page(title, child, tag):
    header = Adw.HeaderBar()
    toolbar = Adw.ToolbarView(content=child)
    toolbar.add_top_bar(header)
    return Adw.NavigationPage(title=title, child=toolbar, tag=tag)


def footer(*buttons):
    box = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER, margin_top=12, margin_bottom=24)
    for b in buttons:
        box.append(b)
    return box


def pill(label, callback, suggested=True):
    b = Gtk.Button(label=label, use_underline=True)
    b.add_css_class("pill")
    if suggested:
        b.add_css_class("suggested-action")
    b.connect("clicked", lambda *_: callback())
    return b


class Setup(Adw.Bin):
    """Welcome → (get Torquio) → requirements → choices → install → done."""

    def __init__(self, window, torquio_missing=False):
        super().__init__()
        self.window = window
        self.options = {"manage": True, "freetype": "40", "map_path": "", "map_type": "drive", "import_path": ""}
        self.nav = Adw.NavigationView()
        self.set_child(self.nav)
        self.nav.add(self._welcome(torquio_missing))

    # ---- welcome --------------------------------------------------------------------------------------------

    def _welcome(self, torquio_missing):
        status = Adw.StatusPage(icon_name=self.window.get_application().get_application_id(),
                                title=_("Welcome to Torquio"),
                                description=_("Steinberg's Dorico on Linux, set up for you. It takes about twenty "
                                              "minutes, mostly downloading."))
        status.add_css_class("hero")
        self.get_started = pill(_("_Get Started"), lambda: self._get_torquio() if torquio_missing
                                else self.nav.push(self._requirements()))
        status.set_child(footer(self.get_started))
        return page(_("Welcome"), status, "welcome")

    def _get_torquio(self):
        """No Torquio on this computer yet: download it from GitHub (on the host, with git)."""
        target = host.APP_COPY
        self.get_started.set_sensitive(False)
        self.get_started.set_label(_("Downloading Torquio…"))

        def work():
            if host.run(["sh", "-c", "command -v git"])[0] != 0:
                raise host.HostError(_("Torquio needs git, which isn't installed on this computer. Install it from "
                                       "your distribution's software (on Fedora Atomic or Bazzite it's included)."))
            if host.run(["test", "-d", os.path.join(target, ".git")])[0] != 0:
                code, _out = host.run(["git", "clone", "--quiet", REPO_URL, target], timeout=600)
                if code != 0:
                    raise host.HostError(_("Couldn't download Torquio from GitHub. Check your internet connection."))
            return host.check_version()

        def done(result, error):
            self.get_started.set_sensitive(True)
            self.get_started.set_label(_("_Get Started"))
            if error:
                self.window.show_error(_("Couldn't Get Torquio"), error)
            else:
                self.window.version = result
                self.nav.push(self._requirements())
        host.in_background(work, done)

    # ---- requirements ---------------------------------------------------------------------------------------

    def _requirements(self):
        prefs = Adw.PreferencesPage(description=_("Download the installers into your Downloads folder; Torquio finds "
                                                  "them there. You don't need Dorico's own installer: the Download "
                                                  "Assistant gets it."))
        self.system_group = Adw.PreferencesGroup(title=_("This Computer"))
        self.installer_group = Adw.PreferencesGroup(title=_("Installers"))
        prefs.add(self.system_group)
        prefs.add(self.installer_group)
        self.req_continue = pill(_("_Continue"), lambda: self.nav.push(self._choices()))
        self.req_continue.set_sensitive(False)
        group = Adw.PreferencesGroup()
        group.add(footer(pill(_("Check _Again"), self._check, suggested=False), self.req_continue))
        prefs.add(group)
        self._check()
        return page(_("What Torquio Needs"), prefs, "requirements")

    def _check(self):
        host.in_background(lambda: host.api("prereqs"), self._show_requirements)

    def _show_requirements(self, data, error):
        clear(self.system_group)
        clear(self.installer_group)
        if error:
            add(self.system_group, StatusRow(_("Torquio"))).set_state(str(error), "error")
            return
        self.prereqs = data
        ok = True
        row = add(self.system_group, StatusRow("Distrobox", "drive-harddisk-symbolic"))
        row.set_state(_("Installed") if data["distrobox"] else _("Not installed: install it from your distribution's "
                                                                 "software"), "ok" if data["distrobox"] else "error")
        ok &= data["distrobox"]
        row = add(self.system_group, StatusRow(_("Podman or Docker"), "drive-harddisk-symbolic"))
        row.set_state(data["container_manager"].capitalize() if data["container_manager"] else
                      _("Neither is installed: Podman is the easier one"), "ok" if data["container_manager"] else "error")
        ok &= bool(data["container_manager"])
        for key, title, required, url, pattern in INSTALLERS:
            path = data["installers"].get(key, "")
            row = add(self.installer_group, StatusRow(title + ("" if required else " " + _("(optional)"))))
            if path:
                row.set_state(os.path.basename(path), "ok")
            else:
                row.set_state(_("Not found in Downloads") if required else _("Not found; you can add it later"),
                              "warn" if required else "off")
                row.add_suffix(suffix_button(_("Download"), lambda u=url: open_uri(self.window, u), "flat",
                                             tooltip=_("Open the download page")))
                row.add_suffix(suffix_button(_("Choose…"), lambda p=pattern: self._choose_installer(p),
                                             tooltip=_("An installer saved somewhere else")))
            ok &= bool(path) or not required
        self.req_continue.set_sensitive(ok)

    def _choose_installer(self, pattern):
        def chosen(path):
            folder = self.prereqs["installers_dir"]
            code, _out = host.run(["sh", "-c", 'mkdir -p "$1" && cp -f "$2" "$1/"', "sh", folder, path], timeout=120)
            if code != 0:
                self.window.show_error(_("Couldn't Use That File"), _("It couldn't be copied to {}.").format(folder))
            self._check()
        choose_file(self.window, _("Choose the Installer"), [pattern], chosen)

    # ---- choices ----------------------------------------------------------------------------------------------

    def _choices(self):
        prefs = Adw.PreferencesPage()
        display = Adw.PreferencesGroup(title=_("Display"))
        wayland = self.prereqs.get("session_type") != "x11"
        manage = Adw.SwitchRow(title=_("Manage Scaling Automatically"), active=wayland, sensitive=wayland,
                               subtitle=_("Sizes Dorico for your screen each time it starts (adjusts your desktop's "
                                          "XWayland setting, which you can restore later)") if wayland else
                               _("For Wayland sessions; set Wine's DPI later in Display & Scaling"))
        manage.connect("notify::active", lambda r, *_: self.options.update(manage=r.get_active()))
        self.options["manage"] = wayland
        fonts = Adw.ComboRow(title=_("Font Smoothing"), model=Gtk.StringList.new([_("Bolder"), _("Crisper")]),
                             subtitle=_("Bolder is FreeType v40, Crisper v35; easy to change later"))
        fonts.connect("notify::selected", lambda r, *_: self.options.update(freetype="40" if r.get_selected() == 0
                                                                            else "35"))
        display.add(manage)
        display.add(fonts)
        prefs.add(display)

        speed = Adw.PreferencesGroup(title=_("Speed"))
        nt = self.prereqs.get("ntsync")
        row = StatusRow(_("Kernel Fast Sync"), "power-profile-performance-symbolic")
        row.set_tooltip_text(_("NTsync makes big scores much faster to edit"))
        if nt == "dormant":
            row.set_state(_("Your kernel supports it; enabling it needs your password"), "warn")
            row.add_suffix(suffix_button(_("Enable"), lambda: self.window.enable_ntsync(
                on_done=lambda ok: row.set_state(_("Active"), "ok") if ok else None)))
        else:
            row.set_state(_("Active") if nt == "active" else _("Not supported by this kernel (6.14 or newer needed)"),
                          "ok" if nt == "active" else "off")
        speed.add(row)
        prefs.add(speed)

        extras = Adw.PreferencesGroup(title=_("Optional"))
        self.folder_row = Adw.ActionRow(title=_("A Folder for Your Scores"),
                                        subtitle=_("Shown as drive D: in Dorico's dialogs"))
        self.folder_row.add_prefix(Gtk.Image(icon_name="folder-music-symbolic"))
        self.folder_row.add_suffix(suffix_button(_("Choose…"), self._choose_folder))
        extras.add(self.folder_row)
        self.keys_group = extras
        prefs.add(extras)
        host.in_background(lambda: host.api("keycommands"), self._offer_keycommands)

        group = Adw.PreferencesGroup()
        group.add(footer(pill(_("_Install"), lambda: self.nav.push(self._install()))))
        prefs.add(group)
        return page(_("A Few Choices"), prefs, "choices")

    def _choose_folder(self):
        def chosen(path):
            self.options["map_path"] = path
            self.folder_row.set_subtitle(_("{} as drive D:").format(path))
        choose_file(self.window, _("Choose a Folder for Your Scores"), None, chosen, folder=True)

    def _offer_keycommands(self, data, error):
        if error or not data.get("backups"):
            return
        path = data["backups"][0]
        row = Adw.SwitchRow(title=_("Import Key Commands"), subtitle=os.path.basename(path), active=True)
        row.add_prefix(Gtk.Image(icon_name="input-keyboard-symbolic"))
        self.options["import_path"] = path
        row.connect("notify::active", lambda r, *_: self.options.update(import_path=path if r.get_active() else ""))
        self.keys_group.add(row)

    # ---- install and done -----------------------------------------------------------------------------------

    def _install(self):
        view = TaskView(_("Installing Torquio…"), on_done=self._installed)
        self.task_view = view
        clamp = Adw.Clamp(maximum_size=520, child=view, margin_top=24, margin_bottom=24, margin_start=18,
                          margin_end=18)
        p = page(_("Installing"), Gtk.ScrolledWindow(child=clamp, hscrollbar_policy=Gtk.PolicyType.NEVER), "install")
        p.set_can_pop(False)
        view.detail.set_label(_("You can keep using your computer; this window shows each step."))
        view.detail.set_visible(True)
        view.start("install", json.dumps(self.options))
        self.install_page = p
        return p

    def _installed(self, code):
        self.install_page.set_can_pop(True)
        if code != 0:
            return
        status = Adw.StatusPage(icon_name="object-select-symbolic", title=_("You're All Set"),
                                description=_("The Steinberg Download Assistant is opening: sign in and install "
                                              "Dorico. Then start it from here or from your app menu."))
        status.add_css_class("hero")
        status.set_child(footer(pill(_("_Continue"), self.window.refresh)))
        done = page(_("Done"), status, "done")
        done.set_can_pop(False)
        self.nav.push(done)
