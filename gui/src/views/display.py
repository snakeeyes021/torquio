"""Display & Scaling: Automated or Manual Mode, Wine's DPI, font smoothing, and what Torquio sees."""
from gettext import gettext as _

from gi.repository import Adw, Gtk

from .. import host
from ..widgets import StatusRow, add, clear, suffix_button
from . import Page

FONTS = [("40", _("Bolder"), _("FreeType v40: heavier text, the default")),
         ("35", _("Crisper"), _("FreeType v35: thinner, sharper text"))]


class Display(Page):
    name, title, icon = "display", _("Display & Scaling"), "preferences-desktop-display-symbolic"

    def __init__(self, window):
        super().__init__(window)
        self._updating = False
        self.widget.set_description(_("Torquio can size Dorico for your screen each time it starts, including when "
                                      "you move between a laptop screen and a monitor."))

        scaling = Adw.PreferencesGroup(title=_("Scaling"))
        self.manage = Adw.SwitchRow(title=_("Manage Scaling Automatically"),
                                    subtitle=_("Sets Wine's DPI and your desktop's XWayland setting for Dorico"))
        self.manage.connect("notify::active", self._manage_changed)
        self.match = Adw.SwitchRow(title=_("Match the Screen's Physical DPI"),
                                   subtitle=_("Size Dorico by the monitor's real pixel density instead of its scale"))
        self.match.connect("notify::active", lambda *_: self._set_bool("match_physical_dpi", self.match))
        self.dpi = Adw.SpinRow.new_with_range(48, 480, 1)
        self.dpi.set_title(_("Wine DPI"))
        self.dpi.set_subtitle(_("96 is 100 %, 120 is 125 %, 144 is 150 %, 192 is 200 %"))
        self.dpi_apply = suffix_button(_("Apply"), self._apply_dpi, "suggested-action")
        self.dpi_apply.set_visible(False)
        self.dpi.add_suffix(self.dpi_apply)
        self.dpi.connect("notify::value", self._dpi_changed)
        for row in (self.manage, self.match, self.dpi):
            scaling.add(row)
        self.widget.add(scaling)

        self.restore_group = Adw.PreferencesGroup()
        self.restore_row = Adw.ActionRow(title=_("Your Desktop's XWayland Setting Was Changed"))
        self.restore_row.add_prefix(Gtk.Image(icon_name="edit-undo-symbolic"))
        self.restore_row.add_suffix(suffix_button(_("Restore"), self._restore))
        self.restore_group.add(self.restore_row)
        self.restore_group.set_visible(False)
        self.widget.add(self.restore_group)

        text = Adw.PreferencesGroup(title=_("Text"))
        self.font = Adw.ComboRow(title=_("Font Smoothing"), model=Gtk.StringList.new([f[1] for f in FONTS]))
        self.font.connect("notify::selected", self._font_changed)
        text.add(self.font)
        self.widget.add(text)

        self.info = Adw.PreferencesGroup(title=_("This Display"))
        self.widget.add(self.info)

    def refresh(self, status):
        s = status["settings"]
        self._updating = True
        self.manage.set_active(s["manage_graphics"])
        self.match.set_active(s["match_physical_dpi"])
        self.match.set_visible(s["manage_graphics"])
        self.dpi.set_visible(not s["manage_graphics"])
        self.dpi.set_value(int(s["manual_dpi"]) if s["manual_dpi"].isdigit() else 96)
        self.dpi_apply.set_visible(False)
        self.font.set_selected(next((i for i, f in enumerate(FONTS) if f[0] == s["freetype_interpreter"]), 0))
        self.font.set_subtitle(FONTS[self.font.get_selected()][2])
        x11 = status["session_type"] == "x11"
        self.manage.set_sensitive(not x11)
        if x11:
            self.manage.set_subtitle(_("Automatic scaling is for Wayland sessions; set Wine's DPI by hand"))
        self._updating = False
        host.in_background(lambda: host.api("display"), self._show_display)

    def _show_display(self, data, error):
        clear(self.info)
        if error:
            add(self.info, StatusRow(_("Display"))).set_state(str(error), "warn")
            return
        g = data.get("graphics", {})
        rows = [(_("Desktop"), f'{g.get("de", "?")} · {data.get("session_type", "?").capitalize()}'),
                (_("Monitor"), f'{g.get("connector", "")} · {g.get("width", "?")} × {g.get("height", "?")}'),
                (_("Desktop Scale"), f'{round(float(g.get("scale", 1) or 1) * 100)} %'),
                (_("Physical DPI"), str(g.get("physical_dpi", "?"))),
                (_("Wine DPI Now"), str(data.get("wine_dpi", "?")))]
        if self.manage.get_active() and g.get("target_wine_dpi"):
            rows.append((_("Dorico Will Use"), _("{} DPI").format(g["target_wine_dpi"])))
        for title, value in rows:
            add(self.info, StatusRow(title)).set_state(value)
        restorable = data.get("restorable")
        self.restore_group.set_visible(bool(restorable) and not self.manage.get_active())
        if restorable:
            self.restore_row.set_subtitle(_("It's {current} now; it was {original} before Automated Mode").format(
                current=restorable["current"], original=restorable["original"]))

    # ---- changes --------------------------------------------------------------------------------------------

    def _manage_changed(self, *args):
        if self._updating:
            return
        if self.manage.get_active():
            dialog = Adw.AlertDialog(
                heading=_("Manage Scaling Automatically?"),
                body=_("Each time Dorico starts, Torquio sets Wine's DPI for the screen it's on and adjusts your "
                       "desktop's XWayland scaling setting, which other X11 apps share. Your current setting is kept "
                       "so you can restore it here."))
            dialog.add_response("cancel", _("_Cancel"))
            dialog.add_response("ok", _("_Manage Scaling"))
            dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_close_response("cancel")

            def answered(d, response):
                if response == "ok":
                    self.window.apply_setting("manage_graphics", "true")
                else:
                    self._revert()
            dialog.connect("response", answered)
            dialog.present(self.window)
        else:
            self.window.apply_setting("manage_graphics", "false", on_done=self._offer_restore,
                                      on_cancel=self._revert)

    def _revert(self):
        self.window.refresh()

    def _offer_restore(self):
        def check(data, error):
            if error or not data.get("restorable"):
                return
            r = data["restorable"]
            dialog = Adw.AlertDialog(
                heading=_("Restore Your Desktop's Setting?"),
                body=_("Automated Mode changed your desktop's XWayland scaling to {current}. Put it back to {original}?"
                       ).format(current=r["current"], original=r["original"]))
            dialog.add_response("keep", _("_Keep Current"))
            dialog.add_response("restore", _("_Restore"))
            dialog.set_response_appearance("restore", Adw.ResponseAppearance.SUGGESTED)
            dialog.connect("response", lambda d, resp: self._restore() if resp == "restore" else None)
            dialog.present(self.window)
        host.in_background(lambda: host.api("display"), check)

    def _restore(self):
        def done(data, error):
            if error:
                self.window.show_error(_("Couldn't Restore the Setting"), error)
            else:
                self.window.toast(_("Desktop scaling setting restored"))
                self.window.refresh()
        host.in_background(lambda: host.api("display", "restore"), done)

    def _set_bool(self, key, row):
        if not self._updating:
            self.window.apply_setting(key, "true" if row.get_active() else "false", on_cancel=self._revert)

    def _dpi_changed(self, *args):
        if not self._updating:
            current = self.window.status["settings"]["manual_dpi"]
            self.dpi_apply.set_visible(str(int(self.dpi.get_value())) != current)

    def _apply_dpi(self):
        self.window.apply_setting("manual_dpi", str(int(self.dpi.get_value())), on_cancel=self._revert)

    def _font_changed(self, *args):
        if self._updating:
            return
        self.font.set_subtitle(FONTS[self.font.get_selected()][2])
        self.window.apply_setting("freetype_interpreter", FONTS[self.font.get_selected()][0], on_cancel=self._revert)
