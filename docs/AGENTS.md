# AI Development Guide

Welcome! This document outlines the established engineering principles, architectural decisions, and documentation workflows for this repository. Please use this context to guide your suggestions and implementations.

## Architectural Principles

1. **Container-Native Isolation:** We utilize a Distrobox container (Ubuntu 24.04) which enables a universal solution for users running both mutable and immutable hosts. This provides the necessary isolation for Steinberg dependencies while maintaining direct integration with the host's audio (Pipewire) subsystem. Please focus all architectural solutions on this container-first approach.
2. **The Custom Wine Engine:** Dorico 6 requires DirectComposition (`dcomp`) stubs that are not yet available in upstream Wine. Therefore, our engine relies exclusively on the custom `zhiyi/wine` branch. Ensure all Wine-related modifications build strictly upon this custom compilation path.
3. **Environment-Agnostic Scripting:** To ensure maximum transportability for users, scripts should rely on dynamic XDG directories (e.g., `~/.local/share/wineprefixes/dorico`) and relative paths, avoiding hardcoded paths to specific developer directories.
4. **URI Handoff Architecture:** We solve Linux authentication by using `.desktop` handlers on the host OS to catch `net-steinberg-sam://` and `net-steinberg-sda://` login tokens, which are then passed into the containerized Windows binaries. This is our foundational solution for Steinberg licensing.

## Repository Context

When joining a session, please reference the following documents to understand the current state of the project:
*   **[ARCHITECTURE.md](ARCHITECTURE.md):** The core technical design and dependency structures.
*   **[PLAYBOOK.md](PLAYBOOK.md):** The manual Standard Operating Procedure (SOP) that serves as the logic blueprint for future automation.
*   **[BACKLOG.md](BACKLOG.md):** Active tasks, known issues, and planned epics.
*   **[RELEASES.md](RELEASES.md):** The verified manifest of Wine commits, dependencies, and Steinberg app versions known to work together.

## The "Document-As-You-Go" Workflow

To prevent context loss across sessions and handoffs, please operate as a proactive technical documenter. 

*   **Continuous Updates:** As we finalize architectural decisions, discover dependency quirks, or expand project scope, please suggest updates to `ARCHITECTURE.md` or `BACKLOG.md` immediately, rather than waiting for the end of a session.
*   **Preserving Intent:** When refactoring documentation files, prioritize preserving the exact technical constraints and historical rationale communicated by human developers. Focus edits on improving organization and readability while maintaining the factual integrity of the content.
*   **Session Wrap-up:** Before concluding a major thread, verify that relevant insights, new scripts, and roadmap items have been successfully persisted to the repository documentation.