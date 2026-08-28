#!/usr/bin/env python3
"""Test cases for block_brace_quote_heredoc hook.

Confirms the hook fires when a heredoc BODY contains a brace/bracket
immediately followed by a quote character (`{"k":"v"}`, `['a','b']`,
`[ "x" ]`) — the shape that trips Claude Code's "Contains brace with
quote character (expansion obfuscation)" anti-obfuscation heuristic in
bash-unquoted contexts (verified 2026-05-30 HITL probe; see
docs/active/chain-hook-maintenance/FINDINGS.md) — and does NOT fire on:
  - the same pattern in a properly quoted argument (`python3 -c "…"`),
    which the matcher does not flag (that context is bash-quoted)
  - heredoc bodies with braces but no adjacent quote (`{1,2,3}`, `{}`)
  - brace+quote text on the heredoc OPEN line or AFTER the close
    delimiter (only the body is scanned)
  - here-strings (`<<<`), which are not heredocs
  - commands with no heredoc at all

Characterization suite written 2026-08-27 (corpus-spinoff Phase 3b): the
hook shipped 2026-05-30 without a test file. Cases pin the hook's
behavior as implemented; none required a hook change.
"""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent / "block_brace_quote_heredoc.py"

# Each case: (command, should_block, description)
CASES = [
    # ---- DENY: brace/bracket + quote inside a heredoc body ----
    (
        "python3 <<'PY'\nd = {\"k\": \"v\"}\nprint(d)\nPY",
        True,
        "dict literal with double-quoted keys in single-quoted-delimiter heredoc",
    ),
    (
        "python3 <<'PY'\nxs = ['a', 'b']\nPY",
        True,
        "list literal with single-quoted strings",
    ),
    (
        "python3 <<PY\nd = {'k': 1}\nPY",
        True,
        "unquoted delimiter",
    ),
    (
        'python3 <<"PY"\nd = {"k": 1}\nPY',
        True,
        "double-quoted delimiter",
    ),
    (
        "cat <<-EOF\n\t{ \"a\": 1 }\n\tEOF",
        True,
        "<<- variant, brace then whitespace then quote",
    ),
    (
        "jq -n '.' <<EOF\n[ \"x\", \"y\" ]\nEOF",
        True,
        "bracket then whitespace then quote (JSON array)",
    ),
    (
        "python3 <<'PY'\nd = {\"k\": 1}",
        True,
        "heredoc with no closing delimiter (body runs to end of command)",
    ),
    (
        "python3 <<'PY'\nx = 1\ny = {'a': 2}\nz = 3\nPY",
        True,
        "brace+quote on a later body line, not the first",
    ),
    (
        "echo start && python3 <<'PY'\nd = {\"k\": 1}\nPY",
        True,
        "heredoc as the second segment of a chain",
    ),

    # ---- ALLOW: not a heredoc-body brace+quote ----
    (
        "python3 -c \"d = {'k': 'v'}\"",
        False,
        "brace+quote inside a bash-quoted -c argument (no heredoc)",
    ),
    (
        "python3 <<'PY'\nprint('hello')\nPY",
        False,
        "heredoc body with no braces",
    ),
    (
        "python3 <<'PY'\ns = {1, 2, 3}\nPY",
        False,
        "heredoc body with braces but no adjacent quote",
    ),
    (
        "python3 <<'PY'\nd = {}\nxs = []\nPY",
        False,
        "empty braces / brackets in heredoc body",
    ),
    (
        "python3 <<'PY'\nd = dict(k='v')\nPY",
        False,
        "quotes in heredoc body without a preceding brace",
    ),
    (
        "jq '{\"a\":1}' <<EOF\nplain body\nEOF",
        False,
        "brace+quote on the heredoc OPEN line (bash-quoted), body is clean",
    ),
    (
        "cat <<EOF\nplain body\nEOF\necho '{\"x\": 1}'",
        False,
        "brace+quote AFTER the close delimiter (outside the body)",
    ),
    (
        "cat <<< '{\"a\": 1}'",
        False,
        "here-string, not a heredoc",
    ),
    (
        "ls -la /tmp",
        False,
        "plain command, no heredoc",
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
        {
            "tool_name": "Write",
            "tool_input": {"command": "python3 <<'PY'\nd = {\"k\": 1}\nPY"},
        }
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
