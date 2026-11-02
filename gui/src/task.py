"""Progress for long jobs on the host (installing, updating, the Wine engine...): each step as it happens, the
full log underneath for when something goes wrong."""
from gettext import gettext as _

from gi.repository import Adw, Gdk, GLib, Gtk

from . import host


class TaskView(Gtk.Box):
    """The steps of a running task, a spinner on the current one and a check on the finished ones, and its log
    in an expander. Used in TaskDialog and in the setup assistant."""

    def __init__(self, heading, on_done=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.on_done = on_done
        self.code = None
        self.current = None

        self.spinner = Adw.Spinner(width_request=48, height_request=48, halign=Gtk.Align.CENTER)
        self.result_icon = Gtk.Image(pixel_size=48, visible=False, halign=Gtk.Align.CENTER)
        self.heading = Gtk.Label(label=heading, wrap=True, justify=Gtk.Justification.CENTER)
        self.heading.add_css_class("title-2")
        self.detail = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER, visible=False)
        self.detail.add_css_class("dim-label")
        for widget in (self.spinner, self.result_icon, self.heading, self.detail):
            self.append(widget)

        self.steps = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, visible=False)
        self.steps.add_css_class("boxed-list")
        self.append(self.steps)

        self.buffer = Gtk.TextBuffer()
        self.log = Gtk.TextView(buffer=self.buffer, editable=False, cursor_visible=False, monospace=True,
                                wrap_mode=Gtk.WrapMode.WORD_CHAR, top_margin=12, bottom_margin=12, left_margin=12,
                                right_margin=12)
        self.log.add_css_class("task-log")
        scroller = Gtk.ScrolledWindow(child=self.log, min_content_height=220, vexpand=True)
        scroller.add_css_class("card")
        self.scroller = scroller
        self.expander = Gtk.Expander(label=_("Details"), child=scroller)
        self.append(self.expander)

    def start(self, name, *args):
        host.Task(name, *args, on_event=self._event, on_done=self._done).start()
        return self

    def _step(self, text):
        if self.current:
            self._finish_step(self.current, True)
        row = Adw.ActionRow(title=GLib.markup_escape_text(text))
        spinner = Adw.Spinner()
        row.add_prefix(spinner)
        row._spinner = spinner
        self.steps.append(row)
        self.steps.set_visible(True)
        self.current = row

    def _finish_step(self, row, ok):
        row.remove(row._spinner)
        icon = Gtk.Image(icon_name="object-select-symbolic" if ok else "dialog-error-symbolic")
        icon.add_css_class("success" if ok else "error")
        row.add_prefix(icon)

    def _event(self, event):
        kind = event.get("event")
        if kind == "phase":
            self._step(event.get("text", ""))
        elif kind == "log":
            end = self.buffer.get_end_iter()
            self.buffer.insert(end, event.get("text", "") + "\n")
            adj = self.scroller.get_vadjustment()
            GLib.idle_add(lambda: adj.set_value(adj.get_upper()) and False)
        elif kind == "result":
            self.result = event

    def _done(self, code):
        self.code = code
        if self.current:
            self._finish_step(self.current, code == 0)
        self.spinner.set_visible(False)
        self.result_icon.set_visible(True)
        if code == 0:
            self.result_icon.set_from_icon_name("object-select-symbolic")
            self.result_icon.add_css_class("success")
        else:
            self.result_icon.set_from_icon_name("dialog-error-symbolic")
            self.result_icon.add_css_class("error")
            self.heading.set_label(_("Something Went Wrong"))
            self.detail.set_label(_("The details below show where it stopped. Export Logs in Maintenance collects "
                                    "everything for a bug report."))
            self.detail.set_visible(True)
            self.expander.set_expanded(True)
        if self.on_done:
            self.on_done(code)

    def log_text(self):
        return self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter(), False)


class TaskDialog(Adw.Dialog):
    """A task in its own dialog. Closing it lets the task carry on; the window says when it's finished."""

    def __init__(self, window, title, heading, done_heading, name, *args, on_done=None):
        super().__init__(title=title, content_width=520, content_height=560)
        self.window, self.done_heading, self.callback = window, done_heading, on_done
        self.view = TaskView(heading, on_done=self._done)
        self.copy_button = Gtk.Button(icon_name="edit-copy-symbolic", tooltip_text=_("Copy Log"), visible=False)
        self.copy_button.connect("clicked", self._copy)
        header = Adw.HeaderBar()
        header.pack_start(self.copy_button)
        page = Adw.Clamp(maximum_size=480, child=self.view, margin_top=24, margin_bottom=24, margin_start=18,
                         margin_end=18)
        toolbar = Adw.ToolbarView(content=Gtk.ScrolledWindow(child=page, hscrollbar_policy=Gtk.PolicyType.NEVER))
        toolbar.add_top_bar(header)
        self.set_child(toolbar)
        self.closed_early = False
        self.connect("closed", lambda *_: setattr(self, "closed_early", self.view.code is None))
        self.view.start(name, *args)

    def _copy(self, *args):
        Gdk.Display.get_default().get_clipboard().set(self.view.log_text())
        self.window.toast(_("Log copied"))

    def _done(self, code):
        self.copy_button.set_visible(True)
        if code == 0:
            self.view.heading.set_label(self.done_heading)
        if self.closed_early:
            self.window.toast(self.done_heading if code == 0 else _("{} didn't finish").format(self.get_title()))
        if self.callback:
            self.callback(code, getattr(self.view, "result", None))
