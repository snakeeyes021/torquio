"""The setup assistant, shown until Torquio is installed: what it needs, a few choices, then the install."""
import json
import os
from gettext import gettext as _

from gi.repository import Adw, Gdk, Gtk, Pango

from .. import host
from ..task import TaskDialog, TaskView
from ..widgets import StatusRow, add, choose_file, clear, suffix_button

SDA_PAGE = "https://o.steinberg.net/index.php?id=steinberg_download_assistant&L=1"
INSTALLERS = [("sda", _("Steinberg Download Assistant"), True, SDA_PAGE,
               "Steinberg_Download_Assistant_*_Installer_win*.exe"),
              ("noteperformer", _("NotePerformer"), False, "https://www.noteperformer.com/", "NotePerformer-Installer-*.exe"),
              ("cantai", _("Cantai"), False, "https://www.cantai.app/", "Cantai-Windows-*Installer-*.exe.zip")]


def open_uri(window, uri):
    Gtk.UriLauncher.new(uri).launch(window, None, None)


def page(title, child, tag, show_title=True):
    header = Adw.HeaderBar(show_title=show_title)
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
    """Welcome → what's needed (installing what's missing) → choices → install → done."""

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.options = {"manage": True, "freetype": "40", "map_path": "", "map_type": "drive", "import_path": ""}
        self.nav = Adw.NavigationView()
        self.set_child(self.nav)
        self.nav.add(self._welcome())

    # ---- welcome --------------------------------------------------------------------------------------------

    def _welcome(self):
        status = Adw.StatusPage(icon_name=self.window.get_application().get_application_id(),
                                title=_("Welcome to Torquio"),
                                description=_("Steinberg's Dorico on Linux, set up for you. It takes about twenty "
                                              "minutes, mostly downloading."))
        status.add_css_class("hero")
        self.get_started = pill(_("_Get Started"), lambda: self.nav.push(self._requirements()))
        status.set_child(footer(self.get_started))
        return page(_("Welcome"), status, "welcome", show_title=False)

    # ---- requirements ---------------------------------------------------------------------------------------

    def _requirements(self):
        prefs = Adw.PreferencesPage(description=_("Download the installers into your Downloads folder; Torquio finds "
                                                  "them there. You don't need Dorico's own installer: the Download "
                                                  "Assistant gets it."))
        self.system_group = Adw.PreferencesGroup(title=_("This Computer"))
        self.missing_group = Adw.PreferencesGroup(title=_("Install What's Missing"), visible=False)
        self.installer_group = Adw.PreferencesGroup(title=_("Installers"))
        for g in (self.system_group, self.missing_group, self.installer_group):
            prefs.add(g)
        self.req_continue = pill(_("_Continue"), lambda: self.nav.push(self._choices()))
        self.req_continue.set_sensitive(False)
        group = Adw.PreferencesGroup()
        group.add(footer(pill(_("Check _Again"), self._check, suggested=False), self.req_continue))
        prefs.add(group)
        self.chosen = None  # the missing items ticked for installing (all, at first)
        self._check()
        return page(_("What Torquio Needs"), prefs, "requirements")

    def _check(self):
        def work():
            facts = host.facts()
            return facts, (host.api("prereqs") if facts.get("python") else None)
        host.in_background(work, self._show_requirements)

    ITEMS = (("python", "Python 3.9+", "application-x-executable-symbolic"),
             ("distrobox", "Distrobox", "drive-harddisk-symbolic"),
             ("podman", None, "drive-harddisk-symbolic"))

    def _show_requirements(self, result, error):
        for g in (self.system_group, self.missing_group, self.installer_group):
            clear(g)
        if error:
            add(self.system_group, StatusRow(_("This Computer"))).set_state(str(error), "error")
            return
        facts, data = result
        self.facts, self.prereqs = facts, data
        missing = facts["missing"]
        for key, title, icon in self.ITEMS:
            row = add(self.system_group, StatusRow(title or _("Podman or Docker"), icon))
            if key == "podman" and key not in missing:
                row.set_state("Podman" if facts.get("podman") else "Docker", "ok")
            else:
                row.set_state(_("Missing") if key in missing else _("Installed"),
                              "error" if key in missing else "ok")
        if self.chosen is None or not set(self.chosen) <= set(missing):
            self.chosen = list(missing)
        self._show_missing()
        ok = not missing
        if data:
            for key, title, required, url, pattern in INSTALLERS:
                path = data["installers"].get(key, "")
                row = add(self.installer_group, StatusRow(title + ("" if required else " " + _("(optional)"))))
                if path:
                    row.set_state(os.path.basename(path), "ok")
                else:
                    row.set_state(_("Not found in Downloads") if required else _("Not found; you can add it later"),
                                  "warn" if required else "off")
                    row.add_suffix(suffix_button(_("Open Download Page"), lambda u=url: open_uri(self.window, u),
                                                 "flat", tooltip=_("Opens it in your web browser")))
                    row.add_suffix(suffix_button(_("Choose…"), lambda p=pattern: self._choose_installer(p),
                                                 tooltip=_("An installer saved somewhere else")))
                ok &= bool(path) or not required
        self.installer_group.set_visible(bool(data))
        self.req_continue.set_sensitive(ok)

    # ---- installing what's missing --------------------------------------------------------------------------

    def _show_missing(self):
        from torquio import prereqs
        facts, missing = self.facts, self.facts["missing"]
        self.missing_group.set_visible(bool(missing))
        if not missing:
            return
        name = facts.get("name") or _("This system")
        plan = prereqs.install_plan(facts["family"], [k for k in missing if k in self.chosen])
        titles = {"python": "Python 3", "distrobox": "Distrobox", "podman": "Podman"}
        # what to install: a tick per missing item (only where there's a command that installs it)
        installable = prereqs.install_plan(facts["family"], missing)
        if installable["command"]:
            for key in missing:
                if key in installable["note_keys"]:
                    continue
                row = Adw.ActionRow(title=titles[key], use_markup=False, activatable=True)
                check = Gtk.CheckButton(active=key in self.chosen, valign=Gtk.Align.CENTER)
                check.connect("toggled", lambda c, k=key: self._toggle(k, c.get_active()))
                row.add_prefix(check)
                row.set_activatable_widget(check)
                add(self.missing_group, row)
        if plan["command"]:
            self.missing_group.set_description(
                (_("On {name}, Torquio would run this command as administrator (it asks for your password), "
                   "answering its questions with yes:") if plan["root"] else
                 _("On {name}, Torquio would run this command, for your user only (no password needed):"))
                .format(name=name))
            add(self.missing_group, self._command_row(plan["shown"]))
            buttons = Gtk.Box(spacing=12, halign=Gtk.Align.END, margin_top=6)
            buttons.append(self._button(_("_Copy Command"), lambda: self._copy(plan["shown"]), suggested=False))
            install = self._button(_("_Install"), lambda: self._install_missing(plan["command"], plan["root"]))
            if plan["root"] and not facts.get("pkexec"):
                install.set_sensitive(False)
                install.set_tooltip_text(_("This system can't ask for an administrator password here; run the "
                                           "command in a terminal instead"))
            buttons.append(install)
            add(self.missing_group, buttons)
        else:
            self.missing_group.set_description("")
        if plan["alternative"]:
            add(self.missing_group, Gtk.Label(
                label=_("Or install Distrobox for your user only, without the package manager:"),
                xalign=0, wrap=True, margin_top=12, css_classes=["dim-label"]))
            add(self.missing_group, self._command_row(plan["alternative"]))
            box = Gtk.Box(spacing=12, halign=Gtk.Align.END, margin_top=6)
            box.append(self._button(_("Copy"), lambda: self._copy(plan["alternative"]), suggested=False))
            box.append(self._button(_("Install for Me Only"), lambda: self._install_missing(plan["alternative"], False),
                                    suggested=False))
            add(self.missing_group, box)
        note = installable["note"]
        if note:
            add(self.missing_group, self._note(note, name, installable["note_keys"], installable["config"]))

    def _note(self, note, name, keys, config):
        """Why there's no button for some items, and what to do instead."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12)
        listed = " and ".join({"python": "Python 3", "distrobox": "Distrobox", "podman": "Podman"}[k] for k in keys)
        if note == "image":
            text = _("{name} is an image-based system, and Torquio never changes its system image. {items} is "
                     "normally part of it: use your system's own way to get an image that includes it (an update, "
                     "or a rebase to such an image), then check again.").format(name=name, items=listed)
        elif note == "nix":
            text = _("On NixOS, add these lines to your configuration, rebuild, then check again:")
        elif note == "builtin":
            text = _("{name} normally comes with Distrobox and Podman. If they're missing, update the system, then "
                     "check again.").format(name=name)
        else:
            text = _("Torquio needs Distrobox, which runs Torquio's Linux container, and Podman (or Docker), which "
                     "Distrobox uses. Install them the way your system installs software, then check again.")
        box.append(Gtk.Label(label=text, xalign=0, wrap=True))
        if note == "nix" and config:
            box.append(self._command_row(config))
            box.append(self._button(_("_Copy Lines"), lambda: self._copy(config), suggested=False,
                                    halign=Gtk.Align.END))
        if note == "unknown":
            links = Gtk.Box(spacing=12)
            links.append(Gtk.LinkButton(uri="https://distrobox.it/#installation", label=_("Installing Distrobox")))
            links.append(Gtk.LinkButton(uri="https://podman.io/docs/installation", label=_("Installing Podman")))
            box.append(links)
        return box

    def _command_row(self, text):
        label = Gtk.Label(label=text, xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, selectable=True,
                          margin_top=8, margin_bottom=8, margin_start=12, margin_end=12)
        label.add_css_class("monospace")
        frame = Gtk.Frame(child=label)
        frame.add_css_class("view")
        return frame

    def _button(self, label, callback, suggested=True, halign=None):
        b = Gtk.Button(label=label, use_underline=True)
        if suggested:
            b.add_css_class("suggested-action")
        if halign is not None:
            b.set_halign(halign)
        b.connect("clicked", lambda *_: callback())
        return b

    def _toggle(self, key, active):
        if active and key not in self.chosen:
            self.chosen.append(key)
        elif not active and key in self.chosen:
            self.chosen.remove(key)
        clear(self.missing_group)
        self._show_missing()

    def _copy(self, text):
        Gdk.Display.get_default().get_clipboard().set(text)
        self.window.toast(_("Copied"))

    def _install_missing(self, command, root):
        """Run the shown command (as administrator through pkexec when it needs root), with its output live, then
        check again."""
        argv = (["pkexec", "sh", "-c", command + " 2>&1"] if root else ["sh", "-c", command + " 2>&1"])
        TaskDialog(self.window, _("Install What's Missing"), _("Installing…"), _("Installed"), "prereqs",
                   argv=argv, on_done=lambda code, result: self._check()).present(self.window)

    def _choose_installer(self, pattern):
        def chosen(path):
            folder = self.prereqs["installers_dir"]
            self.window.toast(_("Copying the installer…"))

            def copied(code, error):
                if error or code != 0:
                    self.window.show_error(_("Couldn't Use That File"),
                                           _("It couldn't be copied to {}.").format(folder))
                self._check()
            # Installers can be gigabytes: copy off the main loop
            host.in_background(lambda: host.run(["sh", "-c", 'mkdir -p "$1" && cp -f "$2" "$1/"', "sh", folder, path],
                                                timeout=900)[0], copied)
        choose_file(self.window, _("Choose the Installer"), [pattern], chosen)

    # ---- choices ----------------------------------------------------------------------------------------------

    def _choices(self):
        prefs = Adw.PreferencesPage()
        display = Adw.PreferencesGroup(title=_("Display"))
        wayland = self.prereqs.get("session_type") != "x11"
        manage = Adw.SwitchRow(use_markup=False, title=_("Manage Scaling Automatically"), active=wayland, sensitive=wayland,
                               subtitle=_("Sizes Dorico for your screen each time it starts (adjusts your desktop's "
                                          "XWayland setting, which you can restore later)") if wayland else
                               _("For Wayland sessions; set Wine's DPI later in Display & Scaling"))
        manage.connect("notify::active", lambda r, *_: self.options.update(manage=r.get_active()))
        self.options["manage"] = wayland
        fonts = Adw.ComboRow(use_markup=False, title=_("Font Smoothing"), model=Gtk.StringList.new([_("Bolder"), _("Crisper")]),
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
        self.folder_row = Adw.ActionRow(title=_("A Folder for Your Scores"), use_markup=False,
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
        row = Adw.SwitchRow(title=_("Import Key Commands"), subtitle=os.path.basename(path), active=True,
                            use_markup=False)
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
            # The main window (and its Maintenance page) isn't there until Torquio is installed: collecting the
            # logs for a bug report is offered here
            maintenance = next(v for v in self.window.views if v.name == "maintenance")
            self.task_view.append(footer(pill(_("_Export Logs"), maintenance._logs, suggested=False)))
            return
        status = Adw.StatusPage(icon_name="object-select-symbolic", title=_("You're All Set"),
                                description=_("The Steinberg Download Assistant is opening: sign in and install "
                                              "Dorico. Then start it from here or from your app menu."))
        status.add_css_class("hero")
        status.set_child(footer(pill(_("_Continue"), self.window.refresh)))
        done = page(_("Done"), status, "done", show_title=False)
        done.set_can_pop(False)
        self.nav.push(done)
