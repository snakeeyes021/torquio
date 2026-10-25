"""Internal commands the Bash scripts call while the port is under way (not for users; see docs/REFACTOR.md).

Bash runs these through torquio_py in scripts/common.sh (`torquio_py config-get KEY DEFAULT`). For
development, `PYTHONPATH=lib python3 -m torquio COMMAND ...` does the same.
"""
import sys

# Each command imports only what it needs: get_config_val runs many times per screen, so it has to
# start as fast as the one-liner it replaces.


def _config_get(key, default):
    from . import config
    print(config.get_text(key, default))


def _config_set(key, value):
    from . import config
    config.set_text(key, value)


def _steinberg_licenses(prefix):
    from . import licenses
    print(licenses.steinberg_state(prefix))


def _plugin_licenses(prefix):
    from . import licenses
    text = licenses.format_plugins(licenses.active_plugins(prefix))
    if text:
        print(text)


def _manifest():
    from . import manifest
    manifest.main()


def _export_logs(out_dir=None):
    from . import logs
    logs.main(out_dir)


# command: (function, number of required arguments, number of optional ones)
COMMANDS = {
    "config-get": (_config_get, 2, 0),
    "config-set": (_config_set, 2, 0),
    "steinberg-licenses": (_steinberg_licenses, 1, 0),
    "plugin-licenses": (_plugin_licenses, 1, 0),
    "manifest": (_manifest, 0, 0),
    "export-logs": (_export_logs, 0, 1),
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in COMMANDS:
        print(f"usage: torquio_py {{{','.join(COMMANDS)}}} ...", file=sys.stderr)
        return 2
    function, required, optional = COMMANDS[argv[0]]
    args = argv[1:]
    if not required <= len(args) <= required + optional:
        print(f"torquio_py {argv[0]}: wrong number of arguments", file=sys.stderr)
        return 2
    function(*args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
