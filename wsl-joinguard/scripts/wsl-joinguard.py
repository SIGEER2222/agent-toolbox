#!/usr/bin/python3
# wsl-joinguard — undoes WSL's argv->commandline->argv round trip that lets an
# outer shell expand $VAR/$(...)/$$ before the real command sees them
# (the root cause of '$'-eating in every devin exec command).
#
# Two interception points, selected by argv[0]:
#
#  A) installed AS /bin/bash  (real bash moved to /bin/bash.dist)
#     Catches `bash.exe` (C:\Windows\System32 stub -> BashMain), which sends:
#         argv = [/bin/bash, -c, '/bin/bash -c "CMD"']
#     The wrap is peeled off and CMD is exec'd verbatim by the real bash —
#     one expansion, at the correct layer.
#
#  B) installed as the login shell (passwd entry)
#     Catches `wsl.exe prog args` (no -e), which sends:
#         argv = [shell, -c, 'prog \"arg1\" \"arg2\"']
#     The join is un-quoted (no expansion) and the recovered argv is execvp'd.
#
# Everything else (scripts, interactive, -e calls, real `bash -c` commands)
# execs the real bash unchanged.
import os
import re
import shlex
import sys

REAL_BASH = "/bin/bash.dist"
LOG = "/tmp/joinguard-%d.log" % os.getuid()

# '<prog> [flags] -c "CMD" [positional...]' — the -c arg of the outer wrap.
# prog may be bash, sh, or anything; quote may be " or '; trailing whitespace
# and positional params are tolerated.
PROG_WRAP = re.compile(r'^(\S+)((?:\s+-[^\s]+)*)(\s+-[^\s]*c[^\s]*)\s+(["\'])(.*)\4(\s+.*)?\s*$', re.S)


def _log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _real(argv0, args):
    os.execv(REAL_BASH, [argv0] + args)


def _passthrough():
    argv0 = "-bash" if sys.argv[0].startswith("-") else "bash"
    _real(argv0, sys.argv[1:])


def _unquote_joined(s):
    # wsl.exe non-exec join wraps spacey args in \"..\"; turn that into a
    # normal quoted string and split WITHOUT expansion.
    return shlex.split(s.replace('\\"', '"'), posix=True)


def _exec_inner(inner):
    # exec the recovered argv; route bare 'bash' straight to the real binary
    if os.path.basename(inner[0]) in ("bash", "bash.exe"):
        os.execv(REAL_BASH, inner)
    os.execvp(inner[0], inner)


def _exec_wrap(prog, flags, cflag, cmd, tail):
    # recovered argv: prog [flags] <-c/-lc/...> CMD [positionals] — bash
    # resolves to the real binary, anything else execvp's via PATH
    inner = [prog]
    if flags:
        inner += flags.split()
    inner += [cflag.strip(), cmd]
    if tail:
        try:
            inner += shlex.split(tail, posix=True)
        except ValueError:
            inner += tail.split()
    _exec_inner(inner)


def _guard_c_arg(s):
    """Return exec target for a wrapped -c string, else None."""
    m = PROG_WRAP.match(s)
    if m:
        return ("wrap", m.group(1), m.group(2), m.group(3), m.group(5), m.group(6))
    if '\\"' in s:
        try:
            inner = _unquote_joined(s)
        except ValueError:
            inner = None
        if inner:
            return ("argv", inner)
    return None


def _as_bash():
    # Role A: we ARE /bin/bash. Only peel the stub wrap; pass all else through.
    if len(sys.argv) == 3 and re.match(r'^-[a-zA-Z]*c[a-zA-Z]*$', sys.argv[1]):
        hit = _guard_c_arg(sys.argv[2])
        _log("BASH_MODE argv=%r hit=%r" % (sys.argv, hit))
        if hit and hit[0] == "wrap":
            _exec_wrap(hit[1], hit[2], hit[3], hit[4], hit[5])
        if hit and hit[0] == "argv":
            try:
                _exec_inner(hit[1])
            except OSError:
                pass
    _passthrough()


def _as_shell():
    # Role B: we ARE the login shell; -c string is a joined command line.
    if len(sys.argv) == 3 and sys.argv[1] == "-c":
        joined = sys.argv[2]
        hit = _guard_c_arg(joined)
        inner = None
        if hit and hit[0] == "argv":
            inner = hit[1]
        else:
            try:
                inner = shlex.split(joined, posix=True)
            except ValueError:
                inner = None
        _log("SHELL_MODE joined=%r inner=%r" % (joined, inner))
        if inner:
            try:
                _exec_inner(inner)
            except OSError:
                pass
    _passthrough()


try:
    base = os.path.basename(sys.argv[0]).lstrip("-")
    if base == "bash":
        _as_bash()
    else:
        _as_shell()
except BaseException:
    _passthrough()

os._exit(127)
