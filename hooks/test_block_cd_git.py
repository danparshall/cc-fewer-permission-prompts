#!/usr/bin/env python3
"""Quick test cases for block_cd_git hook regex."""
import json
import subprocess
import sys

HOOK = "/Users/dan/code/dotfiles/claude-hooks/block_cd_git.py"

# Constructed so this file itself never contains the literal sequence
# `cd <path> && git ...` outside of test strings — but the test strings
# are passed via JSON to a subprocess, not executed as bash.
CD = "cd"
AND = " && "
GIT = "git"

cases = [
    (f"{CD} /Users/dan/code/lobby_analysis{AND}{GIT} status", True),
    (f'grep -A 1 "{CD} <path>{AND}{GIT}" /tmp/x', False),
    (f"mkdir foo{AND}{CD} foo{AND}{GIT} init", True),
    (f"{GIT} -C /Users/dan/code/lobby_analysis status", False),
    ("ls && echo done", False),
    (f"echo hello{AND}{CD} /tmp{AND}{GIT} status", True),
    # 2026-06-01: cd then INTERVENING command then git — Claude Code's
    # hardcoded bare-repo heuristic catches this; the hook now does too.
    # Prior regex required `cd <path> && git` adjacency and missed this.
    (f"{CD} /Users/dan/code/foo{AND}pwd{AND}{GIT} status --short{AND}{GIT} log --oneline -10", True),
    (f"{CD} /Users/dan/code/foo{AND}ls -la{AND}{GIT} status", True),
    # cd then a non-git chain — must remain ALLOWED (this is the legitimate
    # use case for the chain hook's cd whitelist).
    (f"{CD} /Users/dan/code/foo{AND}python script.py{AND}echo done", False),
]

failures = 0
for cmd, should_block in cases:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        [HOOK], input=payload, capture_output=True, text=True,
    )
    blocked = "permissionDecision" in r.stdout
    status = "PASS" if blocked == should_block else "FAIL"
    if blocked != should_block:
        failures += 1
    print(f"{status}  blocked={blocked!s:5}  expected={should_block!s:5}  {cmd!r}")

sys.exit(1 if failures else 0)
