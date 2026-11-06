"""The Wine engine: which prebuilt image matches this copy of Torquio, and whether the installed one is current."""
import glob
import hashlib
import os
import re

from . import config, container, paths, run


def prebuilt_image():
    """The prebuilt image built from exactly this copy's Wine build files (scripts/1-build), or "" when Wine
    has to be compiled locally: not a git checkout, local changes to those files, or build_from_source set."""
    if config.get_text("build_from_source", "false") == "true":
        return ""
    tree = build_tree()
    return f"{paths.image_repo()}:build-{tree[:12]}" if tree else ""


def build_tree():
    """The git tree ID of this copy's Wine build files (scripts/1-build), which names their prebuilt image; ""
    when a checkout has local changes to them. Without git (the copy inside the app, and the one it places on
    the host) the same ID is computed from the files."""
    repo = paths.repo_dir()
    if os.path.isdir(os.path.join(repo, ".git")) or os.path.isfile(os.path.join(repo, ".git")):
        code, changes = run.capture(["git", "-C", repo, "status", "--porcelain", "--", "scripts/1-build"])
        if changes:
            return ""
        code, tree = run.capture(["git", "-C", repo, "rev-parse", "HEAD:scripts/1-build"])
        return tree.strip() if code == 0 else ""
    from . import treehash
    return treehash.tree_id(os.path.join(repo, "scripts", "1-build"))


def is_prebuilt(image):
    return image.startswith(paths.image_repo() + ":")


# Left by `torquio --rebuild-wine` in a container from a prebuilt image: the engine in it was compiled here since.
# A container from an image doesn't have it, so swapping the container (engine updates) takes it away again.
COMPILED_MARKER = "/opt/wine-custom/share/torquio/compiled-locally"


def compiled_locally():
    """Whether the engine in this prebuilt-image container was recompiled here (`torquio --rebuild-wine`)."""
    return run.succeeds(["distrobox", "enter", paths.container_name(), "--", "test", "-e", COMPILED_MARKER])


def from_image(image):
    """Whether the engine is the prebuilt image's own (not compiled locally, nor recompiled in its container)."""
    return is_prebuilt(image) and not compiled_locally()


def wanted_build_record():
    """The build record (zhiyi/wine commit and patches) an engine compiled from this copy would have."""
    repo = paths.repo_dir()
    with open(os.path.join(repo, "scripts/1-build/build_wine.sh")) as f:
        commits = re.findall(r'^TARGET_COMMIT="(.*)"$', f.read(), re.M)
    lines = ["zhiyi_commit=" + "\n".join(commits)]
    for patch in sorted(glob.glob(os.path.join(repo, "scripts/1-build/patches/*.patch"))):
        with open(patch, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()[:12]
        lines.append(f"patch={digest} {os.path.basename(patch)[:-len('.patch')]}")
    return "\n".join(lines)


def outdated(image=None):
    """Whether the engine in the container isn't the one this copy builds: a prebuilt image other than the
    matching one, or a locally compiled engine whose build record differs (or that has none)."""
    image = container.image() if image is None else image
    if from_image(image):
        expected = prebuilt_image()
        return bool(expected) and image != expected
    out = container.enter("cat", "/opt/wine-custom/share/torquio/build-info")
    record = "\n".join(l for l in out.splitlines() if re.match(r"(zhiyi_commit|patch)=", l))
    if not record:
        return True
    return record != wanted_build_record()
