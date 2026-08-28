#!/usr/bin/env python3
"""Test cases for block_cd_git hook.

Confirms the hook fires on `cd <path> && git ...` chains — including the
2026-06-01 shape with intervening commands between the `cd` and the
`git` (`cd foo && pwd && git status`), which Claude Code's hardcoded
bare-repo heuristic also catches — and does NOT fire on `git -C <path>`
(the clean alternative), on the trigger text inside a quoted argument,
or on cd-then-non-git chains (the chain hook's legitimate cd whitelist).
"""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent / "block_cd_git.py"

# Constructed so this file itself never contains the literal sequence
# `cd <path> && git ...` outside of test strings — but the test strings
# are passed via JSON to a subprocess, not executed as bash.
CD = "cd"
AND = " && "
GIT = "git"

# Each case: (command, should_block, description)
CASES = [
    (
        f"{CD} /Users/dan/code/lobby_analysis{AND}{GIT} status",
        True,
        "canonical cd-then-git chain",
    ),
    (
        f'grep -A 1 "{CD} <path>{AND}{GIT}" /tmp/x',
        False,
        "trigger text inside a double-quoted argument",
    ),
    (
        f"mkdir foo{AND}{CD} foo{AND}{GIT} init",
        True,
        "cd-then-git as later segments of a chain",
    ),
    (
        f"{GIT} -C /Users/dan/code/lobby_analysis status",
        False,
        "clean alternative: git -C <path>",
    ),
    (
        "ls && echo done",
        False,
        "unrelated chain, no cd, no git",
    ),
    (
        f"echo hello{AND}{CD} /tmp{AND}{GIT} status",
        True,
        "cd /tmp then git, after a leading echo",
    ),
    # 2026-06-01: cd then INTERVENING command then git — Claude Code's
    # hardcoded bare-repo heuristic catches this; the hook now does too.
    # Prior regex required `cd <path> && git` adjacency and missed this.
    (
        f"{CD} /Users/dan/code/foo{AND}pwd{AND}{GIT} status --short{AND}{GIT} log --oneline -10",
        True,
        "cd, intervening pwd, then git (2026-06-01 bare-repo heuristic shape)",
    ),
    (
        f"{CD} /Users/dan/code/foo{AND}ls -la{AND}{GIT} status",
        True,
        "cd, intervening ls, then git",
    ),
    # cd then a non-git chain — must remain ALLOWED (this is the legitimate
    # use case for the chain hook's cd whitelist).
    (
        f"{CD} /Users/dan/code/foo{AND}python script.py{AND}echo done",
        False,
        "cd then non-git chain (chain hook's cd whitelist territory)",
    ),
]


def _blocked(cmd: str) -> bool:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run([HOOK], input=payload, capture_output=True, text=True)
    return "permissionDecision" in r.stdout and '"deny"' in r.stdout


def _non_bash_passthrough() -> bool:
    payload = json.dumps(
        {"tool_name": "Read", "tool_input": {"command": f"{CD} /tmp{AND}{GIT} status"}}
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
