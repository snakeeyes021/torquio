# Architectural Design & Blueprint

This document details the technical implementation and design philosophy of the Steinberg on Linux project. It is intended for developers, maintainers, and AI agents modifying the system.

## 1. Core Architecture: The Container Method

We use a **containerized approach using Distrobox and Docker** (or Podman) to isolate the complex dependencies of Steinberg software from the host Linux system.

*   **The Engine:** We compile a custom branch of Wine (`zhiyi/wine`) that includes experimental `dcomp` stubs required by Dorico 6. In the future, we may attempt to merge some GE patches, which we believe do fix some issues with the current working state.
*   **The Environment:** Distrobox allows us to run an Ubuntu container that shares the host's display, DBus, audio, and home directory. Developing inside this container prevents pollution of the host system and avoids complex flatpak/appimage packaging during the core development phase.
*   **The Handoff:** One of the most significant hurdles in running Steinberg software on Linux is the browser-based authentication. We use custom `.desktop` URI handlers on the host system to seamlessly catch `net-steinberg-sam://` and `net-steinberg-sda://` login tokens from the native Linux web browser and pass them directly into the containerized Windows binaries via Wine.

### Current Base Environment Details
*   **Container Host:** Distrobox (Ubuntu 24.04).
*   **Engine:** Docker.
*   **Custom Wine Build:** `zhiyi/wine` branch `bug-23698-react-native-20251217`.
    *   *Why:* Includes DirectComposition (`dcomp`) stubs required by Dorico 6.
    *   *Build Specifics:* Compiled with native `libicu-dev` support.
*   **Prefix Config:** Windows 10 (via Winetricks).
*   **Core Dependencies:** `d3dx9`, `msls31`, `allfonts`, `d3dcompiler_43`, `d3dcompiler_47`, `vcrun2019`, `dotnet48`, `wine-icu` (manual MSI).

## 2. Delivery Mechanisms & The Future

Currently, the "recipe" is executed manually via shell scripts (the exact manual baseline procedure is documented in `docs/PLAYBOOK.md`). Depending on licensing and legal constraints from Steinberg, the end-goal deployment strategy takes one of these forms:

1. **The "Bring Your Own Installer" Bootstrapper (Most Likely):** A single "one-click" terminal command (`curl -sL ... | bash`) that downloads our framework, verifies host dependencies (Distrobox), generates the container, and automatically processes the user's downloaded `.exe` installers.
2. **The "Template Prefix" Docker Image:** Distributing a Docker image containing the compiled Wine engine and a pre-installed prefix. A wrapper script copies this "Template Prefix" to the user's local home folder.
3. **AppImage / Flatpak:** If legally permitted, packing the engine and binaries into a single, executable AppImage or Flatpak manifest.

## 3. Execution Pipeline & Infrastructure

The project's scripting is organized chronologically to represent the build-to-runtime lifecycle:

*   **`1-build/`:** Scripts responsible for compiling the custom Wine engine and fetching its native Linux dependencies (e.g., `libicu-dev`).
*   **`2-install/`:** Scripts that bootstrap the Wine prefix (`winetricks`) and silently execute the Steinberg Windows installers within that prefix.
*   **`3-runtime_handlers/`:** The critical glue. These scripts (`dorico.sh`, `sam.sh`, `steinberg-sda-handler.sh`) live on the host or are called by the host's `.desktop` files. They set the correct environment variables and execute the Wine binaries *inside* the Distrobox container.
*   **`desktop_stubs/`:** Templates for the host OS integration, linking the user's application menu and web browser back to the `3-runtime_handlers`.