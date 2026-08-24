#!/usr/bin/env python3
"""Test cases for block_heredoc_with_pipe_or_redirect hook.

Confirms the hook fires on a `<<` heredoc co-occurring with a pipe/redirect
on the heredoc's command line (the "Family 3" matcher prompt: "Contains
shell syntax (file_redirect/pipeline) that cannot be statically analyzed"
— see docs/active/chain-hook-maintenance/FINDINGS.md entry 2026-06-05) and
does NOT fire on plain heredocs or on heredoc bodies that merely contain
`|`/`>`/`<` characters.

Detection boundary (deliberate, see also the hook docstring):
The only place a pipe/redirect can bind to a heredoc *command* in valid
bash is the OPEN LINE (the line carrying `<<DELIM`) — before or after the
heredoc operator. A redirect/pipe sitting on a body line, or on a line
*after* the closing delimiter, belongs to the heredoc body or to a
separate command, neither of which is a confirmed Family-3 trigger.

DEVIATION FROM PLAN (02_block_heredoc_with_pipe_or_redirect.md, case #4):
the plan listed `python3 - <<'PY'\\nprint(1)\\nPY | grep x` as a DENY case
("pipe AFTER the close delimiter"). Empirically that shape is bash-MALFORMED:
`PY | grep x` is not a valid delimiter line, so bash treats it as heredoc
*body* and the heredoc runs to EOF (verified 2026-06-05 with a live `bash`
run: the command printed both `hi` and the literal `PY | grep h` line, with
no grep filtering). The plan's own architecture uses the strict close regex
`^\\s*DELIM\\s*$`, which cannot match `PY | grep x` either — so the plan was
internally inconsistent. We therefore treat that shape as ALLOW (it's a
plain-heredoc-body case) and instead add a bash-VALID redirect-before-heredoc
DENY case to keep coverage of the open-line space.
"""
import json
import subprocess
import sys

HOOK = (
    "/Users/dan/code/dotfiles/claude-hooks/"
    "block_heredoc_with_pipe_or_redirect.py"
)

# Each case: (command, should_block, description)
CASES = [
    # ---- DENY: heredoc + pipe/redirect on the open line (confirmed shapes) ----
    (
        "cat <<'PY' 2>&1\nbody\nPY",
        True,
        "P7: heredoc + 2>&1 on open line",
    ),
    (
        "cat <<'PY' | grep x\nbody\nPY",
        True,
        "P8: heredoc + pipe on open line",
    ),
    (
        "python3 - <<'PY' 2>&1 | grep x\nprint(1)\nPY",
        True,
        "P9: heredoc + redirect + pipe on open line",
    ),
    (
        "cat <<'PY' > /tmp/out\nbody\nPY",
        True,
        "heredoc + stdout-to-file redirect on open line",
    ),
    (
        "python3 - 2>&1 <<'PY'\nprint(1)\nPY",
        True,
        "heredoc + redirect BEFORE the heredoc operator (bash-valid)",
    ),
    (
        "uv run python - <<'PY' 2>&1 | grep -v VIRTUAL_ENV\nprint(1)\nPY",
        True,
        "real-world weirdo (INCOMING 2026-06-05): uv run python heredoc + 2>&1 | grep",
    ),
    (
        'cat <<EOF | wc -l\na\nb\nEOF',
        True,
        "unquoted delimiter heredoc + pipe on open line",
    ),

    # ---- ALLOW: plain heredocs and false-positive guards ----
    (
        "python3 <<'PY'\nprint(1)\nPY",
        False,
        "CRITICAL: plain heredoc, no pipe/redirect (Dan's preferred form)",
    ),
    (
        "python3 <<'PY'\nx = a | b\ny = (c > d)\nz = (1 << 2)\nprint(x, y, z)\nPY",
        False,
        "CRITICAL: heredoc BODY contains |, >, < (Python code) — must not fire",
    ),
    (
        "cat <<EOF\nhello\nEOF",
        False,
        "plain heredoc, unquoted delimiter, no pipe/redirect",
    ),
    (
        "echo x 2>&1 | grep x",
        False,
        "P5: no heredoc, redirect + pipe (analyzable, silent)",
    ),
    (
        "python3 - < /tmp/x.py | grep x",
        False,
        "P10: no heredoc, stdin-from-file + pipe (analyzable, silent)",
    ),
    (
        "python3 - <<<'print(1)' | grep x",
        False,
        "herestring (<<<) + pipe — out of scope, not a confirmed Family-3 trigger",
    ),
    (
        "python3 - <<'PY'\nprint(1)\nPY | grep x",
        False,
        "bash-MALFORMED 'pipe after delimiter line' — `| grep x` is body, not a pipe",
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
        {"tool_name": "Read", "tool_input": {"command": "cat <<'PY' | grep x\nb\nPY"}}
    )
    r = subprocess.run([HOOK], input=payload, capture_output=True, text=True)
    return '"deny"' not in r.stdout


def test_hook_behavior():
    """Pytest entry point: every case must match its expected block decision."""
    for cmd, should_block, desc in CASES:
        assert _blocked(cmd) == should_block, f"{desc!r}: expected block={should_block}"
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
