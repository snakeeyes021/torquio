# Steinberg Dorico on Linux

## The Mission
This project aims to bring Steinberg Dorico to Linux with near-native performance and stability. 

Steinberg software has historically been difficult to run on Linux due largely to installer compatibility, account logins and token handoffs, and a host of other related technical hurdles. That is to say, the software itself generally runs decently well... if you can get that far.

Our goal is to solve these technical challenges and create a **reproducible, automated, and user-friendly** deployment system.

## Philosophy & Architectural Aims
2. **Reproducibility:** The environment must be entirely scriptable. A developer should be able to run a single command to compile the engine, fetch dependencies, and generate the working state from scratch.
3. **The "Plug-and-Play" End Goal:** Whether through automated installers or a pre-configured image, the ultimate goal is a zero-friction experience for the end-user. 

## Current Architecture: The Container Method
We're currently using a **Containerized approach using Distrobox and Docker**.  

*   **The Engine:** We compile a custom branch of Wine (`zhiyi/wine`) that includes experimental `dcomp` stubs required by Dorico 6. In the future, we may attempt to merge some GE patches, which we believe do fix some issues with the current working state.
*   **The Environment:** Distrobox allows us to run an Ubuntu container that shares the host's display, DBus, audio, and home directory. Developing inside this container means we can set up whatever environment is necessary to get the software running without polluting the host system or having to deal with packaging during the development process.
*   **The Handoff:** We use custom `.desktop` URI handlers to seamlessly pass login tokens from the host's native Linux web browser directly into the containerized Steinberg Download Assistant and Steinberg Activation Manager. 

## Delivery Mechanisms & The Future
Currently, we are building the "recipe" inside a Docker container. Depending on licensing and legal constraints from Steinberg, this recipe can be distributed in several ways:

1. **The "Bring Your Own Installer" Bootstrapper (Most Likely):** If we cannot distribute pre-packaged Steinberg software, we will provide a single "one-click" terminal command (e.g., `curl -sL ... | bash`) in this README. This command will download our installation framework, verify the user has Distrobox installed, generate the container, and present a wizard that automatically processes the user's downloaded `.exe` installers.
2. **The "Template Prefix" Docker Image:** We can distribute a Docker image containing the compiled Wine engine and a pre-installed Dorico prefix. A first-run wrapper script copies this "Template Prefix" to the user's local home folder and updates the registry, providing a true one-click install without extra packaging layers.
3. **AppImage / Flatpak:** If legally permitted, the engine and binaries can be packed into a single, executable AppImage or Flatpak manifest.

## Repository Structure & Documentation
*   `dorico_linux_state.md`: The active, living blueprint, tracking our current environment, hashes, and Technical Debt / To-Do list.
*   `archive_bottles_flatpak_method.md`: A historical record of our previous attempts and roadblocks using Bottles.
*   `build/` & `setup/` scripts: The shell scripts used to bootstrap the Wine engine and prefix.