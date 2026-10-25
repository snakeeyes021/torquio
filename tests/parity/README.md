# Parity harness

Checks that a change doesn't alter what Torquio shows or writes, by running the same flows in two copies of
the repo and comparing them byte for byte (colours included):

```
python3 tests/parity/run.py                  # every scenario, against develop
python3 tests/parity/run.py --base main      # against another branch, tag or commit
python3 tests/parity/run.py status menu-exit # only these scenarios
python3 tests/parity/run.py --show status    # also print the output
```

"Before" is a clean copy of the base ref; "after" is a copy of the current working tree, uncommitted and
untracked changes included. It prints `ok` or `DIFF` per scenario, with a diff for each difference, and exits
non-zero if anything differs.

## What's isolated

Each run happens in a scratch `$HOME` and its own copy of the repo, in a pseudo-terminal (so prompts appear
as on a real terminal) with typed input not echoed. Programs that reach outside `$HOME` (`sudo`, `distrobox`,
`podman`, `gsettings`, `kwriteconfig6`, `modprobe`, `pkill`, ...) are replaced by fakes, there's no session
bus or display, and the network is cut off with `unshare`. So it never touches your installation, container
or desktop settings. With no network, the clock check in the header always shows its "could not be
verified" warning.

Masked before comparing: dates and timestamps, the scratch paths and the repo path.

## Scenarios

`scenarios.py` lists them (the format is described at the top). For now they all run with nothing installed
(the fake `distrobox` reports no container). Stages of the Python port add scenarios for the screens they move,
including ones with an installed-looking prefix.

## When something differs

A difference is either a regression to fix or a deliberate change (e.g. a bug fix). The Python port keeps
deliberate changes in separate, clearly labelled commits, so a parity run on the port commits alone stays
clean.
