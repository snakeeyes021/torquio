"""What Torquio needs on the host (Python 3.9+, Distrobox, Podman or Docker) and how each kind of distribution
installs it. README.md's "Requirements" section is the source of truth: the commands shown here are the README's,
and the families it doesn't list follow the same idea; change both together. Pure functions of /etc/os-release's text and a few facts, so the app can use them before Torquio
itself can run (it needs Python), and tests can cover every family.

Families: dnf, apt, zypper, pacman (mutable: the package manager, as root); image-fedora (Fedora Atomic, Bazzite
and the other uBlue images) and image-suse (openSUSE Aeon, MicroOS): image-based, whose base image Torquio never
changes (the maintainer, 2026-11-06: no layering, ever), so only Distrobox's own user-level install into ~/.local,
and an explanation when the image lacks Podman or Python; builtin (SteamOS, Vanilla OS: they come with them);
nix (NixOS: configuration lines, no command); unknown."""
import shlex

# Package names per family (the same everywhere they're packaged)
PACKAGES = {"python": "python3", "distrobox": "distrobox", "podman": "podman"}

# Distrobox's documented install without root (into ~/.local, no package manager, no restart), exactly as the
# README gives it for the upstream Fedora Atomic family
DISTROBOX_USER_INSTALL = "curl https://raw.githubusercontent.com/89luca89/distrobox/main/install | sh -s -- -P ~/.local/"
# Image-based systems whose image may lack Distrobox: only the user-level install, never a change to the image
IMAGE_FAMILIES = ("image-fedora", "image-suse")
# Systems the README lists as including both (the Universal Blue images, SteamOS, openSUSE Aeon and Kalpa)
UBLUE_IDS = ("bazzite", "bluefin", "aurora", "ucore", "secureblue")


def parse_os_release(text):
    """KEY=value lines (values maybe quoted) to a dict."""
    info = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        try:
            value = shlex.split(value)[0] if value else ""
        except ValueError:
            value = value.strip("\"'")
        info[key.strip()] = value
    return info


def family(info, ostree=False, transactional=False, ublue=False):
    """The distribution's family from os-release (ID, ID_LIKE, VARIANT_ID), whether it boots an ostree image
    (/run/ostree-booted), whether it's a transactional openSUSE (Aeon, MicroOS) and whether it's a Universal Blue
    image (/usr/share/ublue-os)."""
    ids = [info.get("ID", "").lower()] + info.get("ID_LIKE", "").lower().split()
    variant = info.get("VARIANT_ID", "").lower()
    if "nixos" in ids:
        return "nix"
    if ids[0] in ("steamos", "vanilla", "vanillaos") or ids[0] in UBLUE_IDS or (ublue and ostree):
        return "builtin"
    if any(i.startswith("opensuse") or i == "suse" or i == "sles" for i in ids):
        if ids[0] in ("opensuse-aeon", "opensuse-kalpa") or variant in ("aeon", "kalpa"):
            return "builtin"
        if transactional or ids[0] == "opensuse-microos" or variant == "microos":
            return "image-suse"
        return "zypper"
    if ostree and any(i in ("fedora", "rhel", "centos") for i in ids):
        return "image-fedora"
    if any(i in ("fedora", "rhel", "centos", "rocky", "almalinux") for i in ids):
        return "dnf"
    if any(i in ("debian", "ubuntu") for i in ids):
        return "apt"
    if any(i in ("arch", "archlinux") for i in ids):
        return "pacman"
    return "unknown"


def missing(have_python, have_distrobox, have_podman, have_docker):
    """The keys of PACKAGES that aren't there (Docker stands in for Podman when it's installed)."""
    out = []
    if not have_python:
        out.append("python")
    if not have_distrobox:
        out.append("distrobox")
    if not (have_podman or have_docker):
        out.append("podman")
    return out


def install_plan(fam, keys):
    """How to install `keys` here. Returns {"command": a shell command ("" where there's no button), "root":
    whether it runs as root (with pkexec), "shown": the same as a user would type it, "alternative": another
    command for Distrobox alone (its user-level install, offered next to the package manager's), "config": NixOS
    configuration lines, "note": why there's no button for some of `keys` ("image", "nix", "builtin",
    "unknown"), "note_keys": which ones}."""
    plan = {"command": "", "root": False, "shown": "", "alternative": "", "config": "", "note": "",
            "note_keys": []}
    if not keys:
        return plan
    pkgs = [PACKAGES[k] for k in keys]
    names = " ".join(pkgs)
    if fam in IMAGE_FAMILIES:
        # The base image isn't changed: Distrobox for this user only; Podman or Python missing from the image is
        # explained (the system's own image or rebase is the way), not layered
        if "distrobox" in keys:
            plan["command"] = plan["shown"] = DISTROBOX_USER_INSTALL
        rest = [k for k in keys if k != "distrobox"]
        if rest:
            plan["note"], plan["note_keys"] = "image", rest
        return plan
    if fam in ("nix", "builtin", "unknown"):
        plan["note"], plan["note_keys"] = fam, list(keys)
        if fam == "nix":
            lines = []
            if "podman" in keys:
                lines.append("virtualisation.podman.enable = true;")
            extra = [p for p in pkgs if p != "podman"]
            if extra:
                lines.append("environment.systemPackages = with pkgs; [ " + " ".join(extra) + " ];")
            plan["config"] = "\n".join(lines)
        return plan
    plan["root"] = True
    if fam == "dnf":
        plan["shown"] = f"sudo dnf install {names}"
        plan["command"] = f"dnf install -y {names}"
    elif fam == "apt":
        plan["shown"] = f"sudo apt install {names}"
        plan["command"] = f"apt-get update && apt-get install -y {names}"
    elif fam == "zypper":
        plan["shown"] = f"sudo zypper install {names}"
        plan["command"] = f"zypper --non-interactive install {names}"
    elif fam == "pacman":
        plan["shown"] = f"sudo pacman -S {names}"
        plan["command"] = f"pacman -S --noconfirm {names}"
    if "distrobox" in keys:
        plan["alternative"] = DISTROBOX_USER_INSTALL
    return plan
