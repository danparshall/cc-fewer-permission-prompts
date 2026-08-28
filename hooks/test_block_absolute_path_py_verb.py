#!/usr/bin/env python3
"""Test cases for block_absolute_path_py_verb hook.

Confirms the hook fires when a Bash command's leading "verb" is an absolute
or relative path ending in `.py` (e.g. `/Users/.../test_X.py 2>&1 | tail -3`
or `./foo.py --flag`) and does NOT fire on:
  - the canonical fix shape `python3 <path>` (CRITICAL — the regression of
    this would break Claude's escape route from the hook)
  - `.py` paths in argument position (`cat /tmp/x.py`, `ls /tmp/*.py`,
    `head -n 5 /tmp/x.py`)
  - quoted `.py` strings inside arguments (`echo "/path/to/foo.py"`,
    `find . -name '*.py'`, `git commit -m "rename foo.py to bar.py"`)
  - bare-verb `foo.py` shapes (no slash; out of regex scope by design)
  - non-`.py` extensions (`path/to/foo.pyc`, `path/to/foo.pyx`,
    `./install.sh`, `/Users/.../install.sh`)
  - non-Bash tool payloads

Coverage rationale:
  - Cover the literal trigger from 2026-06-05 (three redundant smoke-checks
    of `/Users/dan/code/dotfiles/claude-hooks/test_X.py 2>&1 | tail -3`) so
    the hook catches the real-world shape that motivated it.
  - Cover variations on path-as-verb: absolute, relative (./ and bare
    subdir/), parent-dir, quoted (single/double), tilde-prefixed, with
    and without trailing args/redirects/backgrounding.
  - Cover EVERY false-positive shape we can think of, especially the
    canonical fix (`python3 <path>`) — if that ever denies, the hook
    becomes a trap with no escape route.
  - Cover the chain-interaction shape (`/abs/foo.py && other`) as DENY:
    our regex fires in isolation; in production block_bash_chains.py
    (registered earlier in PreToolUse) hard-denies first, but the test
    verifies our hook's behavior in isolation per Plan 03 §134.

Design boundary (Plan 03 §28-39): the hook MUST NOT fire on the canonical
fix or any `.py`-as-argument shape; these are the highest-priority test
cases. A false positive on `python3 <path>` would break Claude's escape
route from the hook.
"""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent / "block_absolute_path_py_verb.py"

# Each case: (command, should_block, description)
CASES = [
    # ---- DENY: .py path as leading verb ----
    (
        "/Users/dan/code/dotfiles/claude-hooks/test_block_brace_expansion.py 2>&1 | tail -3",
        True,
        "literal 2026-06-05 trigger: absolute .py path + 2>&1 | tail tail",
    ),
    (
        "/Users/dan/code/dotfiles/claude-hooks/test_block_cd_git.py",
        True,
        "absolute .py path, no tail (bare invocation)",
    ),
    (
        "./foo.py",
        True,
        "minimal relative `./foo.py`",
    ),
    (
        "./foo.py --flag value",
        True,
        "relative with flag args",
    ),
    (
        "bin/script.py arg",
        True,
        "relative subdir without leading `./`",
    ),
    (
        "../parent/script.py",
        True,
        "parent-dir relative `../...`",
    ),
    (
        '"/Users/dan/foo.py" arg',
        True,
        "double-quoted absolute path as verb",
    ),
    (
        "'/Users/dan/foo.py'",
        True,
        "single-quoted absolute path as verb",
    ),
    (
        "/abs/path/foo.py &",
        True,
        "backgrounded (single `&`, not `&&` — chain hook ignores)",
    ),
    (
        "/abs/path/foo.py > out.txt",
        True,
        "with stdout redirect",
    ),
    (
        "/abs/path/foo.py 2>/dev/null",
        True,
        "with stderr-to-null redirect",
    ),
    (
        "~/scripts/foo.py",
        True,
        "tilde-prefixed path (matcher doesn't expand `~`, but `~` is \\S so regex catches)",
    ),
    (
        "/Users/dan/foo.py && echo done",
        True,
        "chained: our regex fires in isolation; chain hook owns first in prod",
    ),

    # ---- ALLOW: canonical fix and other false-positive guards ----
    (
        "python3 /Users/dan/foo.py",
        False,
        "CRITICAL: canonical fix — if this denies, hook is broken",
    ),
    (
        "python3 /Users/dan/foo.py 2>&1 | tail -3",
        False,
        "CRITICAL: canonical fix with the same 2>&1 | tail tail",
    ),
    (
        "python /Users/dan/foo.py",
        False,
        "python2-form interpreter",
    ),
    (
        "python3 -m mymodule",
        False,
        "interpreter with `-m`, no path argument",
    ),
    (
        "uv run python /Users/dan/foo.py",
        False,
        "uv-wrapped invocation; leading verb is `uv`",
    ),
    (
        "cat /Users/dan/foo.py",
        False,
        ".py path as argument to allow-listed verb",
    ),
    (
        "ls /Users/dan/foo.py",
        False,
        ".py path as argument to `ls`",
    ),
    (
        "ls /tmp/*.py",
        False,
        ".py glob argument, not literal path",
    ),
    (
        "cp foo.py bar.py",
        False,
        "no `/` in either token; out of regex scope",
    ),
    (
        "head -n 5 /tmp/x.py",
        False,
        ".py as argument to `head`",
    ),
    (
        "bash /Users/dan/code/dotfiles/install.sh",
        False,
        "different extension (.sh); out of scope",
    ),
    (
        "./install.sh",
        False,
        "different extension (.sh) relative",
    ),
    (
        "/Users/dan/code/dotfiles/install.sh",
        False,
        "different extension (.sh) absolute",
    ),
    (
        'echo "/path/to/foo.py"',
        False,
        ".py inside double-quoted argument (leading verb `echo` has no /)",
    ),
    (
        "echo '/path/to/foo.py'",
        False,
        ".py inside single-quoted argument",
    ),
    (
        "find . -name '*.py'",
        False,
        ".py inside quoted glob pattern",
    ),
    (
        'git commit -m "rename foo.py to bar.py"',
        False,
        ".py inside quoted commit message",
    ),
    (
        "path/to/foo.pyc",
        False,
        "different extension (.pyc)",
    ),
    (
        "path/to/foo.pyx",
        False,
        "different extension (.pyx Cython)",
    ),
    (
        "foo.py",
        False,
        "bare verb, no `/`; out of regex scope (normal allow-rule miss not our concern)",
    ),
    (
        "path/to/foo.py.bak",
        False,
        "`.py` followed by `.bak` — boundary check `(?:\\s|$)` rejects",
    ),
    (
        "FOO=bar /Users/dan/foo.py",
        False,
        "env-prefix on path-as-verb: leading token `FOO=bar` has no `/`; regex anchored",
    ),
    (
        "",
        False,
        "empty command",
    ),
]


def _blocked(cmd: str) -> bool:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run([HOOK], input=payload, capture_output=True, text=True)
    return "permissionDecision" in r.stdout and '"deny"' in r.stdout


def _non_bash_passthrough() -> bool:
    payload = json.dumps(
        {"tool_name": "Read", "tool_input": {"command": "/abs/foo.py"}}
    )
    r = subprocess.run([HOOK], input=payload, capture_output=True, text=True)
    return '"deny"' not in r.stdout


def test_hook_behavior():
    """Pytest entry point: every case must match its expected block decision."""
    for cmd, should_block, desc in CASES:
        assert _blocked(cmd) == should_block, (
            f"{desc!r}: expected block={should_block}, got block={_blocked(cmd)}"
        )
    assert _non_bash_passthrough(), "Non-Bash tool payload must pass through (no deny)"


def _main() -> int:
    failures = 0
    for cmd, should_block, desc in CASES:
        blocked = _blocked(cmd)
        status = "PASS" if blocked == should_block else "FAIL"
        if blocked != should_block:
            failures += 1
        print(f"{status}  blocked={blocked!s:5}  expected={should_block!s:5}  {desc}")

    passthrough_ok = _non_bash_passthrough()
    print(f"{'PASS' if passthrough_ok else 'FAIL'}  Non-Bash tool passthrough")
    if not passthrough_ok:
        failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
