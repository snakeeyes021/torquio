"""Internal commands for the Bash wrappers scripts/install.sh and scripts/cleanup.sh, which keep their session log
setup and run torquio_py (scripts/common.sh) COMMAND. Not for users: run ./torquio.

For development, `PYTHONPATH=lib python3 -m torquio COMMAND ...` does the same.
"""
import sys


def _install(*args):
    from .cli import install
    return install.main(args)


def _uninstall():
    from .cli import uninstall
    return uninstall.main()


COMMANDS = {"install": _install, "uninstall": _uninstall}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in COMMANDS:
        print(f"usage: torquio_py {{{','.join(COMMANDS)}}} ...", file=sys.stderr)
        return 2
    if argv[0] == "uninstall":
        return _uninstall()
    return _install(*argv[1:])


def run_main():
    """main() with Ctrl+C handled like a Bash command: no traceback, and the process ends by SIGINT, so the
    Bash script that called it stops too."""
    try:
        code = main()
    except KeyboardInterrupt:
        import os
        import signal
        sys.stdout.flush()
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGINT)
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    run_main()
