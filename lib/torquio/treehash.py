"""Git's object ID for a directory's files, computed without git: what `git rev-parse HEAD:DIR` prints for a clean
checkout. The copy of Torquio inside the app (and placed on the host by it) has no .git, but still has to name
the prebuilt Wine engine image its build files match (`build-<tree id>`)."""
import hashlib
import os
import stat

# Not part of the tree: files a checkout ignores (Python's caches)
IGNORED = {"__pycache__"}


def _blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).digest()


def tree_id(path):
    """The tree object ID (hex) of the directory at `path`, as git computes it (symlinks, executable bits and
    git's ordering included; empty directories don't count, as git doesn't track them)."""
    digest = _tree(path)
    return digest.hex() if digest else ""


def _tree(path):
    entries = []
    for name in os.listdir(path):
        if name in IGNORED or name.endswith(".pyc"):
            continue
        full = os.path.join(path, name)
        st = os.lstat(full)
        if stat.S_ISLNK(st.st_mode):
            entries.append((name, b"120000", _blob(os.readlink(full).encode())))
        elif stat.S_ISDIR(st.st_mode):
            sub = _tree(full)
            if sub:
                entries.append((name + "/", b"40000", sub))
        elif stat.S_ISREG(st.st_mode):
            with open(full, "rb") as f:
                data = f.read()
            mode = b"100755" if st.st_mode & stat.S_IXUSR else b"100644"
            entries.append((name, mode, _blob(data)))
    if not entries:
        return b""
    # git sorts by name, with directories compared as if they ended in "/"
    entries.sort(key=lambda e: e[0].encode())
    body = b"".join(mode + b" " + name.rstrip("/").encode() + b"\0" + digest for name, mode, digest in entries)
    return hashlib.sha1(b"tree %d\0" % len(body) + body).digest()
