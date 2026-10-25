"""Terminal output and input, matching what the Bash version shows.

Only the interfaces (this module, cli.py, launch/) print or prompt; the rest of the package returns values.
"""
import subprocess
import sys

# The 256-colour palette Torquio's screens use
WINE = "\033[38;5;125m"
BLUE = "\033[38;5;110m"
GREEN = "\033[38;5;108m"
YELLOW = "\033[38;5;179m"
RED = "\033[38;5;167m"
GRAY = "\033[38;5;244m"
DARK_GRAY = "\033[38;5;240m"
RESET = "\033[0m"

_IFS_WHITESPACE = " \t\n"


def clear():
    """The `clear` command (its output depends on the terminal, so it isn't imitated)."""
    sys.stdout.flush()
    subprocess.run(["clear"])


def read(prompt="", raw=False, stream=None):
    """Bash's `read [-r] -p PROMPT VAR`, with one variable and the default IFS. Returns (value, ok).

    The prompt goes to stderr, and only when input comes from a terminal. Leading and trailing (unescaped)
    spaces and tabs are removed. Without `raw`, a backslash makes the next character literal and a backslash
    at the end of a line continues onto the next line. At end of input `ok` is False and `value` is whatever
    came before it (usually ""), which is what `read VAR || true` leaves in VAR.
    """
    stream = stream or sys.stdin
    if prompt and stream.isatty():
        sys.stdout.flush()
        sys.stderr.write(prompt)
        sys.stderr.flush()
    chars = []  # (character, escaped)
    ok = False
    while True:
        line = stream.readline()
        if not line:
            break
        complete = line.endswith("\n")
        if complete:
            line = line[:-1]
        i, continued = 0, False
        while i < len(line):
            c = line[i]
            if c == "\\" and not raw:
                if i + 1 < len(line):
                    chars.append((line[i + 1], True))
                    i += 2
                    continue
                continued = complete  # backslash-newline: the line goes on
                break
            chars.append((c, False))
            i += 1
        if not complete:
            break
        if not continued:
            ok = True
            break
    while chars and not chars[0][1] and chars[0][0] in _IFS_WHITESPACE:
        chars.pop(0)
    while chars and not chars[-1][1] and chars[-1][0] in _IFS_WHITESPACE:
        chars.pop()
    return "".join(c for c, _ in chars), ok
