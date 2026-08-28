#!/usr/bin/env python3
"""Test cases for use_uv_run_python hook.

Confirms the hook fires when a venv interpreter is invoked directly
(`.venv/bin/python …`, absolute or relative, with or without env-var
prefixes or a preceding chain segment) and does NOT fire on the clean
alternative (`uv run python …`), on bare `python`/`python3`, or on the
venv path appearing in argument position (`ls .venv/bin/python`).
"""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent / "use_uv_run_python.py"

# Each case: (command, should_block, description)
CASES = [
    # ---- DENY: direct venv interpreter invocation ----
    (".venv/bin/python tools/inspect.py", True, "relative .venv/bin/python"),
    (".venv/bin/python tools/inspect.py 2>&1", True, "with stderr redirect"),
    (".venv/bin/python3 tools/inspect.py", True, ".venv/bin/python3 variant"),
    ("./.venv/bin/python tools/inspect.py", True, "./ prefixed"),
    (
        "/Users/dan/code/lobby_analysis/.venv/bin/python tools/inspect.py",
        True,
        "absolute path to venv interpreter",
    ),
    ("PYTHONPATH=src .venv/bin/python -m foo", True, "single env-var prefix"),
    ("FOO=bar BAZ=qux .venv/bin/python script.py", True, "multiple env-var prefixes"),
    ("echo hello && .venv/bin/python script.py", True, "as second segment of && chain"),
    ("cd /tmp; .venv/bin/python script.py", True, "as second segment of ; chain"),

    # ---- ALLOW: clean alternatives and argument-position mentions ----
    ("uv run python tools/inspect.py", False, "clean alternative: uv run python"),
    ("uv run python3 tools/inspect.py", False, "clean alternative: uv run python3"),
    ("python tools/inspect.py", False, "bare python"),
    ("python3 tools/inspect.py", False, "bare python3"),
    ("ls .venv/bin/python", False, "venv path as ls argument"),
    ("which .venv/bin/python", False, "venv path as which argument"),
    ("cat .venv/bin/python", False, "venv path as cat argument"),
    ("echo .venv/bin/python", False, "venv path as echo argument"),
    ("grep -r '.venv/bin/python' .", False, "venv path quoted inside grep pattern"),
    (
        "source .venv/bin/activate && python foo.py",
        False,
        "activate-then-python (not a direct interpreter invocation)",
    ),
    ("ls && echo done", False, "unrelated chain"),
]


def _blocked(cmd: str) -> bool:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run([HOOK], input=payload, capture_output=True, text=True)
    return "permissionDecision" in r.stdout and '"deny"' in r.stdout


def _non_bash_passthrough() -> bool:
    payload = json.dumps(
        {"tool_name": "Read", "tool_input": {"command": ".venv/bin/python x.py"}}
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
