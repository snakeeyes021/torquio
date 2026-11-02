"""The Torquio container: which engine runs it, whether it exists, running commands inside it."""
import os

from . import paths, run


def manager():
    """The container engine distrobox uses (it prefers podman)."""
    if os.environ.get("DBX_CONTAINER_MANAGER"):
        return os.environ["DBX_CONTAINER_MANAGER"]
    return "podman" if run.have("podman") else "docker"


def distrobox_list():
    """`distrobox list` output (empty if distrobox fails)."""
    return run.capture(["distrobox", "list"])[1]


def exists(listing=None):
    """Whether the container shows up in `distrobox list`. Like the Bash version's grep, any mention of the
    name counts (so "torquio-env" also matches "torquio-env-old")."""
    return paths.container_name() in (distrobox_list() if listing is None else listing)


def status(listing=None):
    """The STATUS column of the matching rows of `distrobox list`, whitespace collapsed (what
    `grep NAME | awk -F'|' '{print $3}' | xargs` gives)."""
    listing = distrobox_list() if listing is None else listing
    name = paths.container_name()
    fields = []
    for line in listing.splitlines():
        if name in line:
            columns = line.split("|")
            fields.append(columns[2] if len(columns) > 2 else "")
    return " ".join(" ".join(fields).split())


def image():
    """The image the container was created from (empty if unknown)."""
    if manager() == "podman":
        cmd = ["podman", "container", "inspect", "--format", "{{.ImageName}}", paths.container_name()]
    else:
        cmd = ["docker", "container", "inspect", "--format", "{{.Config.Image}}", paths.container_name()]
    return run.capture(cmd)[1].rstrip("\n")


def enter(*cmd):
    """Run a command inside the container without input; returns its output ("" if it fails to start)."""
    return run.capture(["distrobox", "enter", paths.container_name(), "--", *cmd])[1]


def enter_bash(script):
    """Run a Bash script inside the container without input; returns its output."""
    return enter("bash", "-c", script)


def has_nvidia_host():
    return os.path.exists("/proc/driver/nvidia/version")


def has_nvidia_libraries():
    """Whether the container has the host's NVIDIA libraries (distrobox --nvidia)."""
    return run.interactive(["distrobox", "enter", paths.container_name(), "--", "test", "-e",
                            "/usr/lib/x86_64-linux-gnu/libGLX_nvidia.so.0"], stderr=run.DEVNULL) == 0


def vulkan_gpus():
    """["type|name"] for the GPUs Vulkan sees in the container, without CPU emulations."""
    out = run.capture(["distrobox", "enter", paths.container_name(), "--", "bash", "-c",
                       "vulkaninfo --summary 2>/dev/null"], stderr=None, stdin=None)[1]
    gpus, kind = [], ""
    for line in out.splitlines():
        fields = line.split(" = ")
        if "deviceType" in line:
            kind = fields[1] if len(fields) > 1 else ""
        if "deviceName" in line:
            gpus.append(f"{kind}|{fields[1] if len(fields) > 1 else ''}")
    return [g for g in gpus if not g.startswith("PHYSICAL_DEVICE_TYPE_CPU")]


def pull_image(image):
    """Download a prebuilt image unless it's already here; True if it's available."""
    mgr = manager()
    if run.succeeds([mgr, "image", "inspect", image]):
        return True
    return run.interactive([mgr, "pull", image]) == 0
