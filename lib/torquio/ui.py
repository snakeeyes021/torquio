"""Terminal output and input, matching what the Bash version shows.

Only the interfaces (this module, cli.py, launch/) print or prompt; the rest of the package returns values.
"""
import os
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


_SIMPLE_ESCAPES = {"a": "\a", "b": "\b", "e": "\033", "E": "\033", "f": "\f", "n": "\n", "r": "\r", "t": "\t",
                   "v": "\v", "\\": "\\"}
_NUMERIC_ESCAPES = {"0": ("01234567", 3, 8), "x": ("0123456789abcdefABCDEF", 2, 16),
                    "u": ("0123456789abcdefABCDEF", 4, 16), "U": ("0123456789abcdefABCDEF", 8, 16)}


def echo_e(text):
    """`echo -e TEXT` as Bash prints it (most of Torquio's screens use it, so backslashes in paths and names
    are interpreted too). Returns the text including the newline, or without it after \\c."""
    out, i = [], 0
    while i < len(text):
        c = text[i]
        if c != "\\" or i + 1 >= len(text):
            out.append(c)
            i += 1
            continue
        e = text[i + 1]
        if e in _SIMPLE_ESCAPES:
            out.append(_SIMPLE_ESCAPES[e])
            i += 2
        elif e == "c":
            return "".join(out)
        elif e in _NUMERIC_ESCAPES:
            digits, most, base = _NUMERIC_ESCAPES[e]
            j = i + 2
            while j < len(text) and j - (i + 2) < most and text[j] in digits:
                j += 1
            if j == i + 2 and e != "0":
                out.append("\\" + e)  # \x, \u, \U without digits stay as they are
            else:
                value = int(text[i + 2:j] or "0", base)
                # \\0 and \\x give a byte, \\u and \\U a character (bytes >= 0x80 travel as surrogate escapes)
                out.append(chr(value) if e in "uU" or value < 0x80 else chr(0xDC00 + (value & 0xFF)))
            i = j
        else:
            out.append("\\" + e)
            i += 2
    return "".join(out) + "\n"


def echo(text=""):
    """Print like `echo -e TEXT`."""
    sys.stdout.flush()
    sys.stdout.buffer.write(echo_e(text).encode("utf-8", "surrogateescape"))
    sys.stdout.buffer.flush()


def clear():
    """The `clear` command (its output depends on the terminal, so it isn't imitated)."""
    sys.stdout.flush()
    subprocess.run(["clear"])


def _readline(stream):
    """One line, including its newline ("" at end of input). From the real stdin it's read a byte at a time,
    as Bash's read does: buffered reading would swallow input meant for whatever runs after Torquio's Python
    code (the Bash menus, when input comes from a pipe)."""
    if stream is not sys.stdin:
        return stream.readline()
    sys.stdout.flush()
    fd = sys.stdin.fileno()
    data = bytearray()
    while True:
        try:
            byte = os.read(fd, 1)
        except InterruptedError:
            continue
        if not byte:
            break
        data += byte
        if byte == b"\n":
            break
    return data.decode("utf-8", "surrogateescape")


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
        line = _readline(stream)
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


def ask(prompt="", strict=True, raw=False):
    """`read -p PROMPT VAR` as the Bash screens used it; returns the answer.

    At end of input, `strict` (Bash ran with set -e and no `|| true`) stops Torquio with exit code 1, as the
    Bash version did; otherwise whatever was typed before it is returned.
    """
    value, ok = read(prompt, raw)
    if not ok and strict:
        raise SystemExit(1)
    return value


def pause(prompt="Press [Enter] to continue...", strict=True):
    ask(prompt, strict)


def yes(answer):
    """[[ "$answer" =~ ^[Yy]$ ]]"""
    return answer in ("y", "Y")


def no(answer):
    """[[ "$answer" =~ ^[Nn]$ ]]"""
    return answer in ("n", "N")
