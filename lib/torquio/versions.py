"""Version ordering as GNU `sort -V` does it (gnulib's filevercmp, then byte order for ties)."""
import functools


def _isdigit(c):
    return "0" <= c <= "9"


def _isalpha(c):
    return ("a" <= c <= "z") or ("A" <= c <= "Z")


def _order(s, i):
    if i >= len(s):
        return 0
    c = s[i]
    if _isdigit(c):
        return 0
    if _isalpha(c):
        return ord(c)
    if c == "~":
        return -1
    return ord(c) + 256


def _verrevcmp(a, b):
    i = j = 0
    while i < len(a) or j < len(b):
        first_diff = 0
        while (i < len(a) and not _isdigit(a[i])) or (j < len(b) and not _isdigit(b[j])):
            ac, bc = _order(a, i), _order(b, j)
            if ac != bc:
                return ac - bc
            i += 1
            j += 1
        while i < len(a) and a[i] == "0":
            i += 1
        while j < len(b) and b[j] == "0":
            j += 1
        while i < len(a) and j < len(b) and _isdigit(a[i]) and _isdigit(b[j]):
            if not first_diff:
                first_diff = ord(a[i]) - ord(b[j])
            i += 1
            j += 1
        if i < len(a) and _isdigit(a[i]):
            return 1
        if j < len(b) and _isdigit(b[j]):
            return -1
        if first_diff:
            return first_diff
    return 0


def _prefixlen(s):
    """Length of `s` without its file suffix: the trailing run of (\\.[A-Za-z~][A-Za-z0-9~]*)*."""
    n, i, prefixlen = len(s), 0, 0
    while True:
        if i == n:
            return prefixlen
        i += 1
        prefixlen = i
        while i + 1 < n and s[i] == "." and (_isalpha(s[i + 1]) or s[i + 1] == "~"):
            i += 2
            while i < n and (_isalpha(s[i]) or _isdigit(s[i]) or s[i] == "~"):
                i += 1


def filevercmp(a, b):
    if a == b:
        return 0
    if not a:
        return -1
    if not b:
        return 1
    # Special files and hidden files
    for special in (".", ".."):
        if a == special:
            return -1
        if b == special:
            return 1
    if a[0] == "." and b[0] != ".":
        return -1
    if b[0] == "." and a[0] != ".":
        return 1
    if a[0] == "." and b[0] == ".":
        a, b = a[1:], b[1:]
    ap, bp = _prefixlen(a), _prefixlen(b)
    one_pass_only = ap == len(a) and bp == len(b)
    result = _verrevcmp(a[:ap], b[:bp])
    return result if result or one_pass_only else _verrevcmp(a, b)


def compare(a, b):
    """<0, 0 or >0, like strcmp, in `sort -V` order."""
    return filevercmp(a, b) or (a > b) - (a < b)


def sort(items):
    return sorted(items, key=functools.cmp_to_key(compare))
