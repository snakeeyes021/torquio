# Valerio 
A unified installer for Dorico on Linux

## The Mission
This project aims to bring Steinberg's Dorico to Linux via WINE.

Steinberg software has historically been difficult to run on Linux due largely to installer compatibility, account logins and token handoffs, and a small handful of other related technical hurdles. That is to say, the software itself generally runs decently well... if you can get that far.

Our goal is to solve these technical challenges and create a **reproducible, automated, and user-friendly** deployment system.

## Prerequisites (End Users)
*(Note: The installer framework is currently under development. These are the planned requirements.)*
*   A Linux distribution running **Distrobox** (and/or Distroshelf).
*   A container engine (**Docker** or **Podman**).
*   Your own downloaded Steinberg Windows installers (`.exe` / `.zip`). 
    *   **Note:** Currently, all that is necessary is the Steinberg Download Assistant and Steinberg MediaBay; the Download Assistant installs the rest. (optional: Noteperformer)

## Installation

A single-command automated bootstrapper is currently in development. 

In the meantime, the intrepid among us can follow the **[Manual Deployment Playbook](docs/PLAYBOOK.md)** for a step-by-step guide to building the environment.

---

## For Developers & Contributors
If you are looking to understand how this system works, contribute to the scripts, or read the historical design decisions, please refer to the `docs/` directory:

*   **[Manual Playbook](docs/PLAYBOOK.md):** The step-by-step procedure to build the environment by hand.
*   **[Architecture & Blueprint](docs/ARCHITECTURE.md):** The core technical design (Containers, Custom Wine, URI Handoffs).
*   **[Release Manifests](docs/RELEASES.md):** The verifiable combinations of Wine versions and Steinberg app versions.
*   **[Project Backlog](docs/BACKLOG.md):** Current tasks and active sprint items.
*   **[AI Agent Guide](docs/AGENTS.md):** Rules and constraints for LLMs assisting with this repository.

### Repository Structure
```text
steinberg-on-linux/
├── README.md                 
├── desktop_stubs/            # URI handlers and .desktop templates for the host
├── docs/                     # Architectural, task, and release documentation
└── scripts/
    ├── 1-build/              # Compiles the custom Wine engine
    ├── 2-install/            # Bootstraps the prefix and installs software
    └── 3-runtime_handlers/   # Wrappers to launch the apps and handle web-logins
```
