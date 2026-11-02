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
    repo = paths.repo_dir()
    code, changes = run.capture(["git", "-C", repo, "status", "--porcelain", "--", "scripts/1-build"])
    if changes:
        return ""
    code, tree = run.capture(["git", "-C", repo, "rev-parse", "HEAD:scripts/1-build"])
    if code != 0:
        return ""
    return f"{paths.image_repo()}:build-{tree.strip()[:12]}"


def is_prebuilt(image):
    return image.startswith(paths.image_repo() + ":")


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
    if is_prebuilt(image):
        expected = prebuilt_image()
        return bool(expected) and image != expected
    out = container.enter("cat", "/opt/wine-custom/share/torquio/build-info")
    record = "\n".join(l for l in out.splitlines() if re.match(r"(zhiyi_commit|patch)=", l))
    if not record:
        return True
    return record != wanted_build_record()
