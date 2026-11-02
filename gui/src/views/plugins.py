"""AI Plug-ins: which GPU Cantai and other AI plug-ins render on."""
from gettext import gettext as _

from gi.repository import Adw, Gtk

from .. import host
from ..widgets import StatusRow, suffix_button
from . import Page


class Plugins(Page):
    name, title, icon = "plugins", _("AI Plug-ins"), "applications-science-symbolic"

    def __init__(self, window):
        super().__init__(window)
        self._updating = False
        self._choices = []
        self.widget.set_description(_("AI plug-ins such as Cantai run their models on a GPU when they can, which "
                                      "makes rendering much faster."))
        group = Adw.PreferencesGroup(title=_("GPU"))
        self.gpu = Adw.ComboRow(title=_("Render On"), model=Gtk.StringList.new([]))
        self.gpu.connect("notify::selected", self._gpu_changed)
        group.add(self.gpu)
        self.nvidia = StatusRow(_("NVIDIA Access"), "video-display-symbolic")
        self.nvidia_setup = suffix_button(_("Set Up"), lambda: window.run_task(
            _("NVIDIA Access"), _("Setting up NVIDIA access…"), _("NVIDIA access is set up"), "setup-gpu"),
            "suggested-action")
        self.nvidia.add_suffix(self.nvidia_setup)
        self.support = StatusRow(_("Wine Engine GPU Support"), "applications-system-symbolic")
        self.vkd3d = StatusRow(_("Direct3D 12 (vkd3d-proton)"), "emblem-system-symbolic")
        for row in (self.nvidia, self.support, self.vkd3d):
            group.add(row)
        self.widget.add(group)

        cantai = Adw.PreferencesGroup(title=_("Cantai"))
        self.cantai = StatusRow(_("Cantai"), "audio-x-generic-symbolic")
        cantai.add(self.cantai)
        self.widget.add(cantai)

    def refresh(self, status):
        host.in_background(lambda: host.api("gpus", timeout=60), self._show)

    def _show(self, data, error):
        if error:
            self.cantai.set_state(str(error), "warn")
            return
        self._updating = True
        auto = _("Automatic") + (f" ({data['automatic']})" if data["automatic"] else "")
        self._choices = [("auto", auto)] + [(g["name"], g["name"]) for g in data["gpus"]] + \
                        [("off", _("Off (the CPU)"))]
        self.gpu.set_model(Gtk.StringList.new([label for _value, label in self._choices]))
        self.gpu.set_selected(next((i for i, c in enumerate(self._choices) if c[0] == data["setting"]), 0))
        self.gpu.set_subtitle(_("Takes effect the next time Dorico starts"))
        self._updating = False

        self.nvidia.set_visible(data["nvidia"]["host"])
        self.nvidia.set_state(_("Enabled") if data["nvidia"]["enabled"] else _("Not set up"),
                              "ok" if data["nvidia"]["enabled"] else "warn")
        self.nvidia_setup.set_visible(data["nvidia"]["host"] and not data["nvidia"]["enabled"])
        self.support.set_state(_("Yes") if data["engine_support"] else _("Needs an engine update"),
                               "ok" if data["engine_support"] else "warn")
        self.vkd3d.set_state(data["vkd3d"] or _("Not downloaded yet"), "ok" if data["vkd3d"] else "off")
        on_gpu = data["setting"] != "off" and data["gpus"] and data["engine_support"] and data["vkd3d"]
        if not data["cantai"]:
            self.cantai.set_state(_("Not installed"), "off")
        else:
            self.cantai.set_state(_("Renders on the GPU") if on_gpu else _("Renders on the CPU"),
                                  "ok" if on_gpu else "warn")

    def _gpu_changed(self, *args):
        if self._updating or not self._choices:
            return
        value = self._choices[self.gpu.get_selected()][0]
        self.window.apply_setting("ai_gpu", value, quiet_success=_("Dorico will use it from its next start"))
