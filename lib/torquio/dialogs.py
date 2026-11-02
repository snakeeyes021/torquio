"""Desktop dialogs for the launchers: zenity, else kdialog, else GTK (gtk_dialog.py, through PyGObject), else a
desktop notification. Stock Fedora Workstation has neither zenity nor kdialog, so without the GTK fallback
every question went unasked."""
import os
import sys

from . import run

GTK_DIALOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtk_dialog.py")


def _on_kde():
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    return "kde" in desktop or "plasma" in desktop


def _gtk(kind, title, text):
    """True/False as answered (False also when closed), None when GTK can't show a dialog."""
    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        return None
    code = run.interactive([sys.executable, "-I", GTK_DIALOG, kind, title, text],
                           stdin=run.DEVNULL, stdout=run.DEVNULL, stderr=run.DEVNULL)
    return None if code not in (0, 1) else code == 0


def question(text, title, width=None):
    """A yes/no question. True (yes), False (no, or closed), or None when there's no way to ask."""
    if run.have("zenity"):
        cmd = ["zenity", "--question", f"--title={title}", f"--text={text}"] + ([f"--width={width}"] if width else [])
        return run.interactive(cmd, stderr=run.DEVNULL if width else None) == 0
    if run.have("kdialog"):
        return run.interactive(["kdialog", "--yesno", text, "--title", title],
                               stderr=run.DEVNULL if width else None) == 0
    return _gtk("question", title, text)


def message(kind, text, title, width=400):
    """A warning or error ("warning"/"error") the user has to close; waits until they do. Falls back to a
    notification. Returns False if it couldn't be shown at all."""
    if _on_kde() and run.have("kdialog"):
        return run.interactive(["kdialog", "--sorry" if kind == "warning" else "--error", text, "--title", title],
                               stderr=run.DEVNULL) != 127
    if run.have("zenity"):
        return run.interactive(["zenity", f"--{kind}", f"--text={text}", f"--title={title}", f"--width={width}"],
                               stderr=run.DEVNULL) != 127
    if run.have("kdialog"):
        return run.interactive(["kdialog", "--sorry" if kind == "warning" else "--error", text, "--title", title],
                               stderr=run.DEVNULL) != 127
    if _gtk(kind, title, text) is not None:
        return True
    return notify(title, text, "dialog-error" if kind == "error" else "dialog-warning")


def notify(title, text, icon="dialog-information"):
    """A desktop notification (notify-send, else the notification service over D-Bus). False if neither works."""
    if run.succeeds(["notify-send", "--app-name=Torquio", f"--icon={icon}", title, text]):
        return True
    return run.succeeds(["gdbus", "call", "--session", "--dest", "org.freedesktop.Notifications",
                         "--object-path", "/org/freedesktop/Notifications",
                         "--method", "org.freedesktop.Notifications.Notify",
                         "Torquio", "0", icon, title, text, "[]", "{}", "-1"], timeout=5)
