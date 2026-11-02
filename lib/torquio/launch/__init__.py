"""The launchers Torquio installs in ~/.local/bin (torquio-dorico, torquio-sam, torquio-sda-handler).

The installed files are small stubs that run main() from this copy of Torquio. Each one writes a session
log, applies Automated Mode's display settings, writes a runner script into ~/.local/share/torquio and runs
it inside the container. The Bash launchers ran with set -e, so a failing step stops the launcher with its
exit code here too (run.check).
"""
import sys

KINDS = {"dorico": ("dorico", "Dorico"), "sam": ("sam", "SAM"), "sda": ("sda", "SDA")}


def main(kind, argv):
    """Run the launcher `kind` with its command-line arguments (argv[0] is the launcher's path)."""
    import os
    from .. import session_log
    os.environ["DBUS_SYSTEM_BUS_ADDRESS"] = "unix:path=/run/host/run/dbus/system_bus_socket"
    log_kind, label = KINDS[kind]
    session_log.start(log_kind, label, argv[0])
    arg = argv[1] if len(argv) > 1 else ""
    try:
        if kind == "dorico":
            from . import dorico
            return dorico.launch(arg)
        if kind == "sam":
            from . import sam
            return sam.launch(arg)
        from . import sda
        return sda.launch(arg)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    except KeyboardInterrupt:
        return 130
    finally:
        sys.stdout.flush()
