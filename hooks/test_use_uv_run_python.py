#!/usr/bin/env python3
"""Quick test cases for use_uv_run_python hook regex."""
import json
import subprocess
import sys

HOOK = "/Users/dan/code/dotfiles/claude-hooks/use_uv_run_python.py"

cases = [
    # --- positives: should block ---
    (".venv/bin/python tools/inspect.py", True),
    (".venv/bin/python tools/inspect.py 2>&1", True),
    (".venv/bin/python3 tools/inspect.py", True),
    ("./.venv/bin/python tools/inspect.py", True),
    ("/Users/dan/code/lobby_analysis/.venv/bin/python tools/inspect.py", True),
    ("PYTHONPATH=src .venv/bin/python -m foo", True),
    ("FOO=bar BAZ=qux .venv/bin/python script.py", True),
    ("echo hello && .venv/bin/python script.py", True),
    ("cd /tmp; .venv/bin/python script.py", True),

    # --- negatives: should pass through ---
    ("uv run python tools/inspect.py", False),
    ("uv run python3 tools/inspect.py", False),
    ("python tools/inspect.py", False),
    ("python3 tools/inspect.py", False),
    ("ls .venv/bin/python", False),               # argument, not invocation
    ("which .venv/bin/python", False),
    ("cat .venv/bin/python", False),
    ("echo .venv/bin/python", False),
    ("grep -r '.venv/bin/python' .", False),      # quoted in arg
    ("source .venv/bin/activate && python foo.py", False),
    ("ls && echo done", False),
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
