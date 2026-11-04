"""A yes/no question or a message in a GTK dialog, for desktops without zenity or kdialog (stock Fedora
Workstation has neither; GNOME desktops have PyGObject). Run as a separate script, so a broken or missing GTK
can't take the launcher down with it:

    python3 -I gtk_dialog.py question|warning|error TITLE TEXT

Exit code 0: Yes or OK; 1: No, or the dialog was closed; 2: GTK isn't available (no PyGObject, no GTK, or no
display)."""
import sys
import warnings

UNAVAILABLE = 2


def load_gtk():
    try:
        import gi
    except ImportError:
        return None
    for version in ("4.0", "3.0"):
        try:
            gi.require_version("Gtk", version)
            from gi.repository import Gtk
            return Gtk
        except (ImportError, ValueError):
            continue
    return None


def main(argv):
    if len(argv) != 4 or argv[1] not in ("question", "warning", "error"):
        print(__doc__, file=sys.stderr)
        return UNAVAILABLE
    try:
        return show(*argv[1:])
    except Exception as e:  # e.g. no display: an uncaught exception's exit code (1) would read as "No"
        print(f"gtk_dialog: {e}", file=sys.stderr)
        return UNAVAILABLE


def show(kind, title, text):
    Gtk = load_gtk()
    if Gtk is None:
        return UNAVAILABLE
    # Gtk.MessageDialog is deprecated in GTK 4.10 (for AlertDialog, 4.10+ only) but works on every GTK 3 and 4
    warnings.simplefilter("ignore")
    message_type = {"question": Gtk.MessageType.QUESTION, "warning": Gtk.MessageType.WARNING,
                    "error": Gtk.MessageType.ERROR}[kind]
    buttons = Gtk.ButtonsType.YES_NO if kind == "question" else Gtk.ButtonsType.OK
    accepted = (Gtk.ResponseType.YES, Gtk.ResponseType.OK)

    if Gtk.get_major_version() >= 4:
        # PyGObject already tried to initialise GTK 4 on import; init_check() can be true even when that failed
        if not Gtk.init_check() or not Gtk.is_initialized():
            return UNAVAILABLE
        from gi.repository import GLib
        loop = GLib.MainLoop()
        result = [1]
        dialog = Gtk.MessageDialog(message_type=message_type, buttons=buttons, text=title, secondary_text=text)

        def on_response(d, response):
            result[0] = 0 if response in accepted else 1
            d.destroy()
            loop.quit()

        dialog.connect("response", on_response)
        # (no window title: GTK 4 shows it above the text, which already starts with it)
        dialog.present()
        loop.run()
        return result[0]

    if not Gtk.init_check(sys.argv)[0]:
        return UNAVAILABLE
    dialog = Gtk.MessageDialog(message_type=message_type, buttons=buttons, text=title)
    dialog.format_secondary_text(text)
    dialog.set_title(title)
    dialog.set_keep_above(True)
    response = dialog.run()
    dialog.destroy()
    return 0 if response in accepted else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
