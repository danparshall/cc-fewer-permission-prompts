#!/usr/bin/env python3
"""Test cases for block_newline_hash_in_quoted_arg hook.

Confirms the hook fires on `\\n#` inside quoted regions (the pattern that
trips Claude Code's "Newline followed by # inside a quoted argument" anti-
obfuscation heuristic — see docs/active/chain-hook-maintenance/FINDINGS.md
entry dated 2026-06-01) and does not fire on benign quoted bodies.
"""
import json
import subprocess
import sys

HOOK = "/Users/dan/code/dotfiles/claude-hooks/block_newline_hash_in_quoted_arg.py"

# Each case: (command, should_block, description)
cases = [
    # POSITIVE: empirically confirmed Probe B from the 2026-06-01 session.
    (
        'python3 -c "print(\'a\')\n# comment"',
        True,
        "Probe B: double-quoted -c body with \\n# (Python comment)",
    ),
    # NEGATIVE: empirically confirmed Probe A — same shape minus the #.
    (
        'python3 -c "print(\'a\')\nprint(\'b\')"',
        False,
        "Probe A: double-quoted -c body with \\n but no # on line 2",
    ),
    # Single-quoted bodies also have the heuristic per Claude Code's reading.
    (
        "python3 -c 'print(1)\n# x'",
        True,
        "Single-quoted -c body with \\n#",
    ),
    # Bare # without a preceding newline inside quotes is fine (it's a string
    # literal char or shell-comment-after-redirect; not the heuristic shape).
    (
        'python3 -c "print(\'hash # in string\')"',
        False,
        "# inside quoted string without leading newline",
    ),
    # No quoted region at all → can't possibly match.
    (
        "ls -la /tmp",
        False,
        "Plain command, no quotes",
    ),
    # \\n# OUTSIDE any quoted region: this is a real bash comment at the
    # start of a new line, not the heuristic shape. Don't fire — bash
    # comments outside quoted args are legitimate (e.g., heredoc EOF lines).
    (
        "echo hi\n# regular bash comment",
        False,
        "\\n# outside any quoted region (real bash comment)",
    ),
    # Empty command — defensive.
    (
        "",
        False,
        "Empty command",
    ),
    # Brace-quote pattern from the SIBLING hook should not trigger this one
    # (separation of concerns; the other hook handles braces).
    (
        'python3 -c "d = {\'k\': \'v\'}"',
        False,
        "Brace+quote pattern (sibling hook's domain, not ours)",
    ),
    # Indented Python comment after a newline — common shape. Hook matches
    # `\\n` followed by optional whitespace then `#`.
    (
        'python3 -c "def f():\n    # indented comment\n    pass"',
        True,
        "Indented Python comment inside quoted body",
    ),
]

failures = 0
for cmd, should_block, desc in cases:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        [HOOK], input=payload, capture_output=True, text=True,
    )
    blocked = "permissionDecision" in r.stdout and '"deny"' in r.stdout
    status = "PASS" if blocked == should_block else "FAIL"
    if blocked != should_block:
        failures += 1
    print(f"{status}  blocked={blocked!s:5}  expected={should_block!s:5}  {desc}")

# Also confirm non-Bash tools are passthrough.
payload = json.dumps({"tool_name": "Edit", "tool_input": {"command": 'x = "a\n# b"'}})
r = subprocess.run([HOOK], input=payload, capture_output=True, text=True)
passthrough_ok = '"deny"' not in r.stdout
print(f"{'PASS' if passthrough_ok else 'FAIL'}  Non-Bash tool passthrough")
if not passthrough_ok:
    failures += 1

sys.exit(1 if failures else 0)
