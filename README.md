# Steinberg Dorico on Linux

## The Mission
This project aims to bring Steinberg Dorico to Linux with near-native performance and stability. 

Steinberg software has historically been difficult to run on Linux due largely to installer compatibility, account logins and token handoffs, and a small handful of other related technical hurdles. That is to say, the software itself generally runs decently well... if you can get that far.

Our goal is to solve these technical challenges and create a **reproducible, automated, and user-friendly** deployment system.

## Prerequisites (End Users)
*(Note: The installer framework is currently under development. These are the planned requirements.)*
*   A Linux distribution running **Distrobox** (or Distroshelf).
*   A container engine (**Docker** or **Podman**).
*   Your own downloaded Steinberg Windows installers (`.exe` / `.zip`).

## Installation
*(Coming Soon)*
A single-command bootstrapper will be provided here to automatically build your isolated Steinberg environment.

---

## For Developers & Contributors
If you are looking to understand how this system works, contribute to the scripts, or read the historical design decisions, please refer to the `docs/` directory:

*   **[Architecture & Blueprint](docs/ARCHITECTURE.md):** The core technical design (Containers, Custom Wine, URI Handoffs).
*   **[Release Manifests](docs/RELEASES.md):** The verifiable combinations of Wine versions and Steinberg app versions.
*   **[Project Backlog](docs/backlog.md):** Current tasks and active sprint items.
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