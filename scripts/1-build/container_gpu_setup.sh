#!/bin/bash
# Setup inside the Torquio container (run inside it after it's created, and safe to re-run): computer
# identity and GPU access.
#  - vulkan-tools: the Dorico launcher uses vulkaninfo to list GPUs and pick one for AI plug-ins.
#  - NVIDIA: `distrobox create --nvidia` links the host's NVIDIA libraries into the container, but the
#    Vulkan driver descriptions it copies from the host name the library by the host's path
#    (e.g. Fedora's /usr/lib64/libGLX_nvidia.so.0), which doesn't exist in Ubuntu, so Vulkan silently
#    ignores the NVIDIA GPU. Add descriptions that name the library without a path.
set -e

# Computer identity: Wine derives the Windows system UUID (which e.g. Cantai's license is tied to) from
# /var/lib/dbus/machine-id, which every container gets its own random copy of. Give new containers one
# derived from the host's machine ID (hashed, as the raw one is meant to stay private), so the computer keeps
# its identity when the container is re-created. An existing ID is never changed (replace_container carries
# it over to the new container).
if [ ! -s /var/lib/dbus/machine-id ] && [ -s /etc/machine-id ]; then
    sudo mkdir -p /var/lib/dbus
    printf 'torquio:%s' "$(cat /etc/machine-id)" | sha256sum | cut -c1-32 | sudo tee /var/lib/dbus/machine-id >/dev/null
    echo "Computer identity set up."
fi

if ! command -v vulkaninfo >/dev/null 2>&1; then
    echo "Installing Vulkan tools..."
    sudo apt-get update -qq >/dev/null 2>&1 || true
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq vulkan-tools >/dev/null
fi

nvidia_icd() { # $1 = multiarch library dir, $2 = JSON name
    [ -e "$1/libGLX_nvidia.so.0" ] || return 0
    local api host_json
    host_json=$(ls /usr/share/vulkan/icd.d/nvidia_icd*.json /etc/vulkan/icd.d/nvidia_icd.json 2>/dev/null | head -n 1)
    api=$(grep -o '"api_version"[^,}]*' "$host_json" 2>/dev/null | grep -o '[0-9][0-9.]*' | head -n 1)
    sudo mkdir -p /etc/vulkan/icd.d
    printf '{\n    "file_format_version" : "1.0.1",\n    "ICD": {\n        "library_path": "libGLX_nvidia.so.0",\n        "api_version" : "%s"\n    }\n}\n' \
        "${api:-1.3.0}" | sudo tee "/etc/vulkan/icd.d/$2" >/dev/null
    echo "NVIDIA Vulkan driver registered ($2)."
}
nvidia_icd /usr/lib/x86_64-linux-gnu nvidia_icd.x86_64.json
nvidia_icd /usr/lib/i386-linux-gnu nvidia_icd.i686.json
