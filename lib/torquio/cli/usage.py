"""What `torquio` prints for an unknown flag."""

USAGE = [
    'Usage: ./torquio [flags]',
    'Flags:',
    '  -i, --install, --reinstall  Run clean container/prefix setup.',
    '  -r, --remove, --uninstall   Complete environment purge.',
    '  -f, --fix-icons             Refresh host desktop icons.',
    '  -g, --graphics              Interact with display scaling configs.',
    '  -s, --status                Display status dashboard.',
    '  -u, --update                Update Torquio to the latest version.',
    '  -d, --map_folder [p] [l]    Map folder positional/interactively.',
    '  -l, --export-logs           Zip up logs for a bug report (personal data removed).',
    '      --manifest              Print the installed versions (release notes Markdown).',
    '  -x, --export_key_commands   Export key commands to zip.',
    '  -m, --import_key_commands   Import key commands zip/json.',
    '  -w, --winecfg               Launch winecfg in the container prefix.',
    '  -k, --kill_wine             Shutdown all active Wine/Steinberg processes.',
    '  -b, --reboot                Simulate a Windows reboot inside the prefix.',
    '  -e, --execute, --run [file] Execute a custom .exe or .msi in the prefix.',
    '      --rebuild-wine          Recompile custom Wine engine inside container.',
    '      --setup-gpu             Give AI plug-ins (e.g. Cantai) access to the GPU.',
    '      --fix-identity          Give the container a machine ID derived from this computer.',
    '      --enable-ntsync         Activate and persist host kernel fast sync (ntsync).',
]


def unknown_argument(arg):
    """Print the error and the flag list (the caller exits with 1)."""
    print(f"Error: Unknown argument '{arg}'")
    for line in USAGE:
        print(line)
