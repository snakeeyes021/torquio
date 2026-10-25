# Contributing to Torquio

Welcome to Torquio! Thanks for your interest in helping make Steinberg software run beautifully on Linux. Whether you're fixing a bug, tweaking a script, or improving documentation, we appreciate the support.

Here is a quick guide to help you get up and running.

## The Standard Workflow

If you've contributed to open-source before, this will feel very familiar. 

1. **Fork:** Click the "Fork" button at the top right of this repository to create your own copy.
2. **Clone:** Clone your fork to your local machine:
    ```bash
    git clone https://github.com/<YOUR_GITHUB_USERNAME>/torquio.git
    cd torquio
    ```

3. **Branch:** Create a new branch for your feature or bug fix:
    ```bash
    git checkout -b feature/my-feature-or-fix
    ```

4. **Code:** Make your changes!
5. **Test:** See the testing section below.
6. **Push:** Push your branch up to your fork:
   ```bash
   git push origin feature/my-feature-or-fix
   ```

7. **PR:** Open a Pull Request from your fork back to our main repository. Give it a clear title and description.

## Development Guidelines

Torquio relies on containerizing Windows apps without messing up your host system (making it, hopefully, universally compatible, including on immutable distros like Bazzite and the rest of the Fedora Atomic family). Here are a few practical rules of thumb to keep in mind while you code:

* **Keep it in the box:** Torquio uses Distrobox to keep Wine completely contained. Avoid writing scripts that install Wine packages or Windows dependencies directly onto the user's host OS.
* **Use dynamic paths:** We have standard, XDG-compliant path variables defined in `scripts/common.sh` (like `TORQUIO_PREFIX_DIR`), and the same locations in Python in `lib/torquio/paths.py`. Use those so your code works on everyone's machine.
* **Python:** Torquio's host side is Python (`lib/torquio/`; Bash remains only inside the container and in two thin wrappers). It uses only the standard library and must run on Python 3.9. Modules outside `cli/` and `launch/` don't print or prompt; they return values, so a GUI can use them too.
* **Mind the host integration:** We intentionally disabled Wine's automatic desktop integration. This means if you need to add an icon or a `.desktop` file, you'll need to manually craft it in the `desktop_stubs/` directory and ensure the installer script copies it over.

## Testing Your Changes

Since Torquio interacts heavily with the GUI (icons, file associations, desktop launchers), you'll want to test your changes on a clean slate.

You can run `./scripts/cleanup.sh` to completely wipe your existing Torquio environment, and then run your modified `./install.sh` to see if everything works as expected.

Before that, two quick checks that don't touch your installation:

* `python3 -m unittest` runs the unit tests (GitHub runs them on every push too).
* `python3 tests/parity/run.py` compares what Torquio shows before and after your change (against `develop` by default) in an isolated scratch environment; see `tests/parity/README.md`.

## Using AI Assistants

If you are using an AI agent (like GitHub Copilot or a custom LLM) to help write code, please have the agent read `docs/AGENTS.md` at the start of your session. This helps the AI understand our containerization approach and prevents it from suggesting bad Wine hacks.

Thanks again for contributing!