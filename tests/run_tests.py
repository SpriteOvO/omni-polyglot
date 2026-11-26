#!/usr/bin/env python3
"""Run omni.ps1 under each interpreter and check that it took its own branch.

Usage:
    python3 tests/run_tests.py              # every case whose interpreter is installed
    python3 tests/run_tests.py bash fish    # exactly these cases; a missing one fails

Every case must exit 0, print nothing on stderr, and print exactly one line:
    lang=<name> version=<anything> argc=2 args=alpha beta gamma
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = "omni.ps1"
SCRIPT_ARGS = ["alpha", "beta gamma"]
EXPECTED_ARGC = "2"
EXPECTED_ARGS = "alpha beta gamma"
OUTPUT_RE = re.compile(r"^lang=(?P<lang>\S+) version=(?P<version>.+) argc=(?P<argc>\d+) args=(?P<args>.*)$")
TIMEOUT_SECONDS = 60

# name -> (command prefix, accepted "lang" values, regex the reported version must match)
CASES = {
    "bash": (["bash"], {"bash"}, None),
    # /bin/sh is dash on Debian/Ubuntu but bash on macOS, Git for Windows and MSYS2.
    "sh": (["sh"], {"sh", "bash"}, None),
    "dash": (["dash"], {"sh"}, None),
    "busybox": (["busybox", "sh"], {"sh"}, None),
    "zsh": (["zsh"], {"zsh"}, None),
    "ksh": (["ksh"], {"ksh"}, None),
    "mksh": (["mksh"], {"ksh"}, None),
    "tcsh": (["tcsh"], {"tcsh"}, None),
    "fish": (["fish"], {"fish"}, None),
    "pwsh": (["pwsh", "-NoLogo", "-NoProfile", "-NonInteractive", "-File"], {"powershell"}, r"^(?!5\.)\d+\."),
    "powershell": (["powershell", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"], {"powershell"}, r"^5\."),
    "python": ([sys.executable], {"python"}, None),
    "perl": (["perl", "-x"], {"perl"}, None),
    "ruby": (["ruby"], {"ruby"}, None),
    # Execute the file directly so the kernel follows the #!/bin/sh line.
    "shebang": ([], {"sh", "bash"}, None),
}


def build_command(name):
    """Return the full argv for a case, or None when its interpreter is unavailable."""
    prefix = CASES[name][0]
    if name == "shebang":
        if os.name != "posix" or not os.access(ROOT / SCRIPT, os.X_OK):
            return None
        return ["./" + SCRIPT] + SCRIPT_ARGS
    resolved = shutil.which(prefix[0])
    if resolved is None:
        return None
    return [resolved] + prefix[1:] + [SCRIPT] + SCRIPT_ARGS


def check(name, command):
    """Run one case; return (problems, first stdout line). No problems means it passed."""
    _, langs, version_re = CASES[name]
    try:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ["timed out after %ss" % TIMEOUT_SECONDS], ""
    stdout_lines = proc.stdout.splitlines()
    problems = []
    if proc.returncode != 0:
        problems.append("exit code %d" % proc.returncode)
    if proc.stderr.strip():
        problems.append("stderr: %r" % proc.stderr.strip())
    if len(stdout_lines) != 1:
        problems.append("expected 1 stdout line, got %d: %r" % (len(stdout_lines), proc.stdout))
        return problems, proc.stdout.strip()
    match = OUTPUT_RE.match(stdout_lines[0])
    if match is None:
        problems.append("unexpected output: %r" % stdout_lines[0])
        return problems, stdout_lines[0]
    if match["lang"] not in langs:
        problems.append("lang=%s, expected one of %s" % (match["lang"], sorted(langs)))
    if version_re and not re.search(version_re, match["version"]):
        problems.append("version %r does not match %r" % (match["version"], version_re))
    if match["argc"] != EXPECTED_ARGC or match["args"] != EXPECTED_ARGS:
        problems.append("argv not passed through: argc=%s args=%r" % (match["argc"], match["args"]))
    return problems, stdout_lines[0]


def main(argv):
    unknown = [name for name in argv if name not in CASES]
    if unknown:
        print("unknown case(s): %s; known: %s" % (", ".join(unknown), ", ".join(CASES)), file=sys.stderr)
        return 2
    required = bool(argv)
    names = argv or list(CASES)

    failures = 0
    for name in names:
        command = build_command(name)
        if command is None:
            if required:
                failures += 1
                print("FAIL  %-10s interpreter not found" % name)
            else:
                print("SKIP  %-10s interpreter not found" % name)
            continue
        problems, output = check(name, command)
        status = "FAIL" if problems else "PASS"
        failures += bool(problems)
        print("%s  %-10s %s" % (status, name, output))
        print("        via %s" % command[0])
        for problem in problems:
            print("        %s" % problem)

    print("%d case(s) failed" % failures if failures else "all cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
