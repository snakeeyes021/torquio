#!/usr/bin/env python3
"""Meson install script: puts Torquio itself (the `torquio` command, lib/, scripts/, desktop_stubs/) inside the
app, at share/torquio/tree, with a stamp naming its version and a hash of its files. The app places this copy on
the host and runs everything from it (docs/GUI.md, "One app"). File modes are kept: the scripts must stay
executable, and the Wine engine's image tag is the git tree ID of scripts/1-build, which includes them.
Usage (from meson): bundle.py VERSION"""
import hashlib
import json
import os
import shutil
import stat
import sys

SOURCE = os.environ["MESON_SOURCE_ROOT"]
DEST = os.path.join(os.environ.get("DESTDIR", "") + os.environ["MESON_INSTALL_PREFIX"], "share", "torquio", "tree")
VERSION = sys.argv[1]
ITEMS = ["torquio", "lib", "scripts", "desktop_stubs", "LICENSE", "README.md"]
SKIP_DIRS = {"__pycache__", ".git"}
STAMP = ".torquio-app.json"  # read by lib/torquio/appinfo.py


def files():
    for item in ITEMS:
        top = os.path.join(SOURCE, item)
        if os.path.isfile(top):
            yield item
            continue
        for root, dirs, names in os.walk(top):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(names):
                if name.endswith(".pyc"):
                    continue
                yield os.path.relpath(os.path.join(root, name), SOURCE)


def main():
    if os.path.isdir(DEST):
        shutil.rmtree(DEST)
    digest = hashlib.sha256()
    count = 0
    for rel in files():
        src, dst = os.path.join(SOURCE, rel), os.path.join(DEST, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
            digest.update(b"L" + rel.encode() + b"\0" + os.readlink(src).encode() + b"\0")
        else:
            shutil.copy2(src, dst)
            mode = os.stat(src).st_mode
            with open(src, "rb") as f:
                data = f.read()
            digest.update(b"F" + rel.encode() + b"\0" + (b"x" if mode & stat.S_IXUSR else b"-")
                          + hashlib.sha256(data).digest())
        count += 1
    with open(os.path.join(DEST, STAMP), "w") as f:
        json.dump({"version": VERSION, "hash": digest.hexdigest()[:16]}, f)
        f.write("\n")
    print(f"Bundled Torquio {VERSION}: {count} files, {digest.hexdigest()[:16]}")


main()
