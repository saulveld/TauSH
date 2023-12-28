import sys
import os
import shutil
import re

_environ_ = {"modules": []}


def ls(*a):
    return os.listdir(*a)


def cd(*a):
    return os.chdir(*a)


def pwd(*a):
    return os.getcwd(*a)


def cmd(*a):
    return os.system(*a)


def mkdir(*a):
    return os.mkdir(*a)


def rm(*a):
    return os.remove(*a)


def rmdir(*a):
    return os.rmdir(*a)


def mv(*a):
    return os.rename(*a)


def cp(*a):
    return shutil.copy(*a)


def exp(*a):
    return os.system(f"explorer {''.join(a)}")


def where(input, pattern):
    rtns = []
    if isinstance(input, list):
        for i in input:
            if re.search(pattern, i) is not None:
                rtns.append(i)
    else:
        if re.search(pattern, input) is not None:
            rtns.append(input)
    return rtns


def interpolate(s):
    prefix = s.split("{")[0]
    code = s.split("{")[1].split("}")[0]
    suffix = s.split("}")[1]
    return f"{prefix}{eval(code)}{suffix}"


def lines(items):
    return '\n'.join(items)


def get_command(*a):
    for m in _environ_["modules"]:
        if hasattr(m, a[0]):
            return getattr(m, a[0])
    return None


def shell_line(raw):
    if "|" in raw:
        parts = raw.split("|")
        r = shell_line(parts[0])
        for part in parts[1:]:
            subparts = part.split()
            r = get_command(subparts[0])(r, *subparts[1:])
        return r
    if "{" in raw and "}" in raw:
        raw = interpolate(raw)
    wrds = raw.split()
    command = get_command(wrds[0])
    if command is not None:
        r = command(*wrds[1:])
        return r
    else:
        return cmd(raw)


def repl():
    raw = input(f"|{pwd()}|>")
    while raw.lower() != "quit":
        out = shell_line(raw)
        if out is not None:
            print(out)
        raw = input(f"|{pwd()}|>")


def echo(*a):
    return ' '.join(a)


def set(*a):
    return os.environ.__setitem__(*a)


def load(*a):
    # load a module into modules
    _environ_["modules"].append(__import__(*a))


def extend(*a):
    sys.modules[__name__].__dict__[a[0]] = eval(' '.join(a[1:]))


_environ_["modules"] = [sys.modules[__name__]]

if __name__ == "__main__":
    repl()
