"""The machine ID of the Torquio container (Wine turns it into the Windows system UUID, which some plug-ins,
e.g. Cantai, tie their license to)."""
import hashlib

from . import container


def derived_machine_id():
    """The ID Torquio gives new containers: the host's machine ID, hashed (empty if the host has none)."""
    try:
        with open("/etc/machine-id", "rb") as f:
            host = f.read()
    except OSError:
        return ""
    if not host:
        return ""
    host = host.rstrip(b"\n")  # as $(cat /etc/machine-id)
    return hashlib.sha256(b"torquio:" + host).hexdigest()[:32]


def container_machine_id():
    """The container's /var/lib/dbus/machine-id (hex digits only; empty if unreadable)."""
    return "".join(c for c in container.enter("cat", "/var/lib/dbus/machine-id") if c in "0123456789abcdef")
