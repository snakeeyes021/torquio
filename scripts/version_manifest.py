#!/usr/bin/env python3
"""Version manifest: what this installation's Wine engine was built from and which Windows software is installed.

Prints the "Build Environment Artifacts" and "Verified Application Versions" sections of a docs/RELEASES.md
entry as Markdown. Problems that make the manifest unreliable for a release (e.g. a Wine engine built from
other patches than this copy of Torquio has) are printed to stderr as warnings.

Usage: version_manifest.py
"""
import glob
import hashlib
import os
import re
import struct
import subprocess
import sys

HOME = os.path.expanduser("~")
DATA_DIR = os.environ.get("TORQUIO_DATA_DIR") or os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.join(HOME, ".local/share"), "torquio")
PREFIX = os.environ.get("TORQUIO_PREFIX_DIR") or os.path.join(DATA_DIR, "prefix")
CONTAINER = os.environ.get("TORQUIO_CONTAINER_NAME") or "torquio-env"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Programs are listed under their Windows "Programs and Features" names, except Cantai, whose installer
# registers as its renderer but installs the plug-in too
LABELS = {"Cantai Local Render": "Cantai"}
# The Steinberg programs listed, in this order; components bundled with them (HALion Sonic, Groove Agent,
# Library Manager, ...) are left out. All third-party programs are listed.
STEINBERG = ["Steinberg Download Assistant", "Steinberg Activation Manager", "Steinberg MediaBay", "Steinberg Dorico"]
HIDDEN = re.compile(r"^(Microsoft |Wine ICU|Wine Mono|Wine Gecko)")


def read_reg(path):
    """String values of a Wine registry file: {key path: {value name: value}}."""
    keys, current = {}, None
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return keys
    for line in lines:
        if line.startswith("["):
            current = keys.setdefault(line[1:line.rindex("]")], {})
            continue
        m = re.match(r'^"((?:[^"\\]|\\.)*)"="((?:[^"\\]|\\.)*)"$', line)
        if current is not None and m:
            current[m.group(1)] = re.sub(r"\\(.)", r"\1", m.group(2))
    return keys


def installed_programs():
    """Entries of the prefix's Uninstall keys (machine-wide and per-user)."""
    programs = {}
    for reg in ("system.reg", "user.reg"):
        for key, values in read_reg(os.path.join(PREFIX, reg)).items():
            if "\\\\Uninstall\\\\" in key and values.get("DisplayName"):
                programs.setdefault(values["DisplayName"], values)
    return programs


def unix_path(win_path):
    """A C:\\ path inside the prefix, matched case-insensitively like Windows does; None if it doesn't exist."""
    m = re.match(r"(?i)^c:[\\/]+(.*)$", win_path.strip().strip('"'))
    if not m:
        return None
    path = os.path.join(PREFIX, "drive_c")
    for part in filter(None, re.split(r"[\\/]+", m.group(1))):
        try:
            match = next((e for e in os.listdir(path) if e.lower() == part.lower()), None)
        except OSError:
            return None
        if match is None:
            return None
        path = os.path.join(path, match)
    return path


def pe_file_version(path):
    """FileVersion from a Windows executable's version resource, as a tuple of 4 ints (None if absent).
    Reads only the headers and the resource itself (some installers embed hundreds of MB of data)."""
    try:
        with open(path, "rb") as f:
            def read(offset, size):
                f.seek(offset)
                data = f.read(size)
                if len(data) != size:
                    raise ValueError
                return data
            pe = struct.unpack("<I", read(0x3C, 4))[0]
            if read(pe, 4) != b"PE\0\0":
                return None
            sections, opt_size = struct.unpack("<H12xH", read(pe + 6, 16))
            opt = pe + 24
            dirs = opt + (112 if struct.unpack("<H", read(opt, 2))[0] == 0x20B else 96)
            rsrc_rva = struct.unpack("<I", read(dirs + 16, 4))[0]
            table = [struct.unpack("<8xIIII", read(opt + opt_size + 40 * i, 24)) for i in range(sections)]

            def offset_of(rva):
                for vsize, vaddr, rawsize, rawptr in table:
                    if vaddr <= rva < vaddr + max(vsize, rawsize):
                        return rva - vaddr + rawptr
                raise ValueError

            base = offset_of(rsrc_rva)
            entry, want = base, 16  # resource tree: type (RT_VERSION) > name > language
            for _ in range(3):
                named, ids = struct.unpack("<12xHH", read(entry, 16))
                entries = [struct.unpack("<II", read(entry + 16 + 8 * i, 8)) for i in range(named + ids)]
                pick = next((e for e in entries if want is None or e[0] == want), None)
                if pick is None:
                    return None
                entry, want = base + (pick[1] & 0x7FFFFFFF), None
            data_rva, size = struct.unpack("<II", read(entry, 8))
            data = read(offset_of(data_rva), min(size, 4096))
            i = data.find(b"\xbd\x04\xef\xfe")
            if i < 0:
                return None
            ms, ls = struct.unpack("<II", data[i + 8:i + 16])
            return (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)
    except (OSError, ValueError, struct.error):
        return None


def program_version(values):
    """The registry's DisplayVersion, extended to the program's full file version (e.g. 6.2.30 -> 6.2.30.6245)
    when one of its executables carries a longer version that starts with it."""
    version = values.get("DisplayVersion", "")
    try:
        base = tuple(int(p) for p in version.split("."))
    except ValueError:
        return version
    candidates = []
    icon = values.get("DisplayIcon", "").split(",")[0]
    if icon.lower().endswith(".exe"):
        candidates.append(unix_path(icon))
    folder = unix_path(values.get("InstallLocation", ""))
    if folder and os.path.isdir(folder):
        candidates += sorted(glob.glob(os.path.join(folder, "*.exe")) + glob.glob(os.path.join(folder, "*.EXE")))
    for exe in filter(None, candidates):
        full = pe_file_version(exe)
        if full and full[:len(base)] == base:
            full = list(full)
            while len(full) > len(base) and full[-1] == 0:
                full.pop()
            if len(full) > len(base):
                return ".".join(map(str, full))
    return version


def container_info():
    """Wine, winetricks, OS and Mesa versions plus the engine's build record, read inside the container."""
    script = r"""
echo "wine=$(/opt/wine-custom/bin/wine --version 2>/dev/null)"
echo "winetricks=$(winetricks --version 2>/dev/null | cut -d' ' -f1)"
. /etc/os-release; echo "os=$PRETTY_NAME"
echo "mesa=$(dpkg-query -W -f='${Version}\n' mesa-vulkan-drivers:amd64 2>/dev/null | head -n 1)"
[ -f /opt/wine-custom/share/torquio/build-info ] && sed 's/^/build./' /opt/wine-custom/share/torquio/build-info
true
"""
    info = {"build.patch": []}
    try:
        # distrobox enter offers to create a missing container and treats no answer as yes
        names = [row.split("|")[1].strip() for row in subprocess.run(["distrobox", "list", "--no-color"], capture_output=True,
                 text=True, timeout=60).stdout.splitlines()[1:] if row.count("|") >= 2]
        if CONTAINER not in names:
            return info
        out = subprocess.run(["distrobox", "enter", CONTAINER, "--", "bash", "-c", script],
                             capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return info
    for line in out.splitlines():
        key, sep, value = line.partition("=")
        if sep and re.fullmatch(r"wine|winetricks|os|mesa|build\.\w+", key):
            if key == "build.patch":
                info[key].append(value.split(" ", 1))
            else:
                info[key] = value.strip()
    return info


def repo_build():
    """The zhiyi/wine commit and patches (short sha256, name) this copy of Torquio builds."""
    commit = re.search(r'^TARGET_COMMIT="([0-9a-f]+)"', open(os.path.join(REPO, "scripts/1-build/build_wine.sh")).read(), re.M)
    patches = [[hashlib.sha256(open(p, "rb").read()).hexdigest()[:12], os.path.basename(p)[:-len(".patch")]]
               for p in sorted(glob.glob(os.path.join(REPO, "scripts/1-build/patches/*.patch")))]
    return (commit.group(1) if commit else "?"), patches


def pinned(script, variable):
    m = re.search(rf'^{variable}="([^"]+)"', open(os.path.join(REPO, "scripts", script)).read(), re.M)
    return m.group(1) if m else None


def versions_in(folder):
    return sorted((os.path.basename(d.rstrip("/")) for d in glob.glob(os.path.join(folder, "*/"))),
                  key=lambda v: [int(p) if p.isdigit() else p for p in re.split(r"[.-]", v)])


def manifest():
    """(Markdown lines, warnings)"""
    warnings = []
    c = container_info()
    commit, patches = repo_build()
    if not c.get("wine"):
        warnings.append(f"Couldn't read the Wine engine in the '{CONTAINER}' container; build details are this copy of Torquio's.")
    elif c.get("build.zhiyi_commit"):
        if c["build.zhiyi_commit"] != commit or c["build.patch"] != patches:
            warnings.append("The installed Wine engine was built from a different zhiyi/wine commit or patches than this copy of "
                            "Torquio has. Rebuild it (Wine Tools > Recompile / Rebuild Wine Engine) and re-test before a release.")
        if c.get("build.torquio_commit", "").endswith("-dirty"):
            warnings.append(f"The installed Wine engine was built from uncommitted changes ({c['build.torquio_commit']}).")
        commit, patches = c["build.zhiyi_commit"], c["build.patch"]
    else:
        warnings.append("The installed Wine engine predates build records, so the patches listed are this copy of Torquio's, "
                        "not necessarily the ones it was built with. Rebuilding the engine records them.")
        short = re.search(r"-g([0-9a-f]+)$", c["wine"])
        if short and not commit.startswith(short.group(1)):
            warnings.append(f"The installed Wine engine ({c['wine']}) isn't built from this copy's zhiyi/wine commit {commit}.")

    wine = f" (`{c['wine']}`)" if c.get("wine") else ""
    lines = ["**Build Environment Artifacts:**",
             f"*   **Custom Wine Source (`zhiyi/wine`):** Commit `{commit}`{wine}",
             "*   **Torquio Wine Patches:** " + (", ".join(f"`{name}`" for _, name in patches) or "none")]
    if c.get("os"):
        lines.append(f"*   **Container:** `{c['os']}`" + (f", Mesa `{c['mesa']}`" if c.get("mesa") else ""))
    vkd3d = versions_in(os.path.join(DATA_DIR, "vkd3d-proton"))
    if vkd3d:
        lines.append(f"*   **vkd3d-proton:** " + ", ".join(f"`{v}`" for v in vkd3d))
        want = pinned("2-install/install_vkd3d_proton.sh", "VKD3D_PROTON_VERSION")
        if want and want not in vkd3d:
            warnings.append(f"vkd3d-proton {want} (this copy's pinned version) isn't installed; re-run the Cantai installer to provision it.")
    webview2 = versions_in(os.path.join(PREFIX, "drive_c/Program Files/Torquio/WebView2"))
    if webview2:
        lines.append("*   **WebView2 Runtime:** " + ", ".join(f"`{v}`" for v in webview2) + " (fetched at install time)")
    if c.get("winetricks"):
        lines.append(f"*   **Winetricks Version:** `{c['winetricks']}`")

    programs = installed_programs()
    icu = programs.get("Wine ICU (x86_64)") or programs.get("Wine ICU (x86)")
    if icu:
        lines.append(f"*   **Wine-ICU MSI Version:** `{icu.get('DisplayVersion', '?')}`")

    def third_party(name):
        return "steinberg" not in programs[name].get("Publisher", name).lower()

    def order(name):
        return (third_party(name), next((i for i, f in enumerate(STEINBERG) if name.startswith(f)), len(STEINBERG)), name.lower())

    lines += ["", "**Verified Application Versions:**"]
    shown = sorted((n for n in programs if not HIDDEN.match(n) and order(n)[:2] != (False, len(STEINBERG))), key=order)
    for name in shown:
        label = LABELS.get(name, name) + (" (3rd Party)" if third_party(name) else "")
        lines.append(f"*   **{label}:** `{program_version(programs[name])}`")
    if not shown:
        lines.append("*   (no Windows software found in the Wine prefix)")
        warnings.append(f"No installed programs found in {PREFIX}.")
    return lines, warnings


def main():
    lines, warnings = manifest()
    print("\n".join(lines), flush=True)
    if warnings:
        print(file=sys.stderr)
    for w in warnings:
        print(f"Warning: {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
