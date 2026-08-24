#!/usr/bin/env python3
"""Test cases for block_brace_expansion hook.

Confirms the hook fires on bash brace-expansion patterns in shell-argument
position (the new Family-3 static-analysis bail, second row after
heredoc+pipe/redirect — see docs/active/chain-hook-maintenance/FINDINGS.md
entry 2026-06-05 and the `ls /tmp/{a,b}` HITL probe that isolated it) and
does NOT fire on:
  - bash code blocks `{ cmd; cmd; }` (space after `{`)
  - parameter expansion `${VAR}`, `${VAR:-default,foo}`
  - find -exec placeholders `{}`
  - quoted braces `'{a,b}'`, `"{a,b}"` (bash leaves them literal)
  - Python set/dict literals inside heredoc bodies (`{1, 2, 3}`)
  - plain commands with no braces at all

Coverage rationale:
  - Cover the minimal probe shape (`ls /tmp/{a,b}`) that empirically
    isolated the matcher's brace-expansion bail.
  - Cover the wild-prompt's full shape (multi-group cross-product with
    hyphens/dots) so we know the hook catches the real-world case that
    motivated it.
  - Cover the range form (`{1..5}`) since bash supports it and the
    matcher likely treats it identically.
  - Cover every false-positive shape we can think of, so future
    refactors don't silently re-introduce one.
"""
import json
import subprocess
import sys

HOOK = "/Users/dan/code/dotfiles/claude-hooks/block_brace_expansion.py"

# Each case: (command, should_block, description)
CASES = [
    # ---- DENY: bash brace expansion in shell-argument position ----
    (
        "ls /tmp/{a,b}",
        True,
        "minimal probe shape (HITL-isolated 2026-06-05): brace expansion in ls argument",
    ),
    (
        "mv /tmp/{a,b}/file /dest/",
        True,
        "brace expansion in mv argument (destructive verb)",
    ),
    (
        "cp /tmp/{1,2,3}.txt /dest/",
        True,
        "three numeric alternatives",
    ),
    (
        "ls /tmp/{1..5}.txt",
        True,
        "range form `{1..5}`",
    ),
    (
        "ls /tmp/{a..z}",
        True,
        "alphabetic range form `{a..z}`",
    ),
    (
        "ls /tmp/{1..10..2}",
        True,
        "range form with step `{1..10..2}`",
    ),
    (
        "mv /tmp/{a,b}__run{1,2,3}.json /dest/",
        True,
        "multi-group cross-product (2×3 expansion, wild-prompt 2026-06-05 shape)",
    ),
    (
        "mv /tmp/{claude-opus-4-7,gpt-5.2-2025-12-11}__x.json /dest/",
        True,
        "hyphens/dots in alternatives (wild-prompt 2026-06-05 exact shape)",
    ),
    (
        "mkdir -p /tmp/{x,y,z}",
        True,
        "brace expansion with mkdir (blanket verb but matcher still bails)",
    ),
    (
        "echo {hello,world}",
        True,
        "brace expansion with echo (blanket verb, no path involved)",
    ),
    (
        "ls /tmp/{,foo}",
        True,
        "empty first alternative `{,foo}` (valid bash brace expansion)",
    ),
    (
        "mkdir /tmp/x && mv /tmp/{a,b} /tmp/x/ && ls /tmp/x/",
        True,
        "wild-prompt 2026-06-05: all-blanket chain with brace expansion mid-segment",
    ),

    # ---- ALLOW: not brace expansion (false-positive guards) ----
    (
        "ls /tmp/",
        False,
        "no braces at all",
    ),
    (
        "ls *.txt",
        False,
        "glob, no braces",
    ),
    (
        "find . -exec rm {} \\;",
        False,
        "find -exec placeholder `{}` (no comma, no range)",
    ),
    (
        "find . -name '*.txt' -exec mv {} /dest/ +",
        False,
        "find -exec multi-arg placeholder `{}` (no comma)",
    ),
    (
        "{ echo a; echo b; }",
        False,
        "bash code block `{ ... }` (space after `{`)",
    ),
    (
        "foo() { echo hi; }",
        False,
        "bash function body `{ ... }` (space after `{`)",
    ),
    (
        "echo \"{a,b}\"",
        False,
        "double-quoted brace (bash leaves it literal)",
    ),
    (
        "echo '{a,b}'",
        False,
        "single-quoted brace (bash leaves it literal)",
    ),
    (
        "echo ${VAR}",
        False,
        "parameter expansion `${VAR}` (no `,` or `..` inside anyway)",
    ),
    (
        "echo ${VAR:-default,foo}",
        False,
        "parameter expansion with comma in default value (NOT brace expansion)",
    ),
    (
        "ls $(echo /tmp)",
        False,
        "command substitution, no braces",
    ),
    (
        "echo {a, b}",
        False,
        "brace with space — bash does NOT expand this, stays literal",
    ),
    (
        "echo { 1, 2, 3 }",
        False,
        "spaced braces — bash does NOT expand, stays literal",
    ),
    (
        "python3 <<'PY'\ndata = {1, 2, 3}\nprint(data)\nPY",
        False,
        "Python set literal in heredoc body (spaces — wouldn't expand anyway, but body should be stripped)",
    ),
    (
        "python3 <<'PY'\ndata = {1,2,3}\nprint(data)\nPY",
        False,
        "CRITICAL: Python set literal in heredoc body with no spaces — body must be stripped before scan",
    ),
    (
        "python3 <<'PY'\nd = {'k': 'v', 'k2': 'v2'}\nPY",
        False,
        "Python dict literal in heredoc body (brace+quote covered by sibling hook, not this one)",
    ),
    (
        "git commit -m 'fix {a,b} thing'",
        False,
        "single-quoted argument containing brace-shaped text",
    ),
    (
        "ls /tmp/{}",
        False,
        "empty braces `{}` (no comma, no range)",
    ),
    (
        "echo hello",
        False,
        "plain command, no braces",
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
        {"tool_name": "Read", "tool_input": {"command": "ls /tmp/{a,b}"}}
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
