#!/usr/bin/env python3
"""PreToolUse hook: hard-fail `.venv/bin/python(3)` invocations.

Background: Dan's permission allowlist covers `Bash(python *)` and
`Bash(python3 *)`, plus `Bash(uv *)` — so `python ...` and
`uv run python ...` run without prompting. `.venv/bin/python ...`
doesn't match either prefix and forces a prompt every time. The Python
environment policy says to use `uv run python` anyway. Claude (me) kept
defaulting to `.venv/bin/python` out of habit and burning prompts. This
hook makes the lapse hard-fail so I notice immediately and retry with
the policy-blessed form.
"""
import json
import re
import sys

# Match `.venv/bin/python` or `.venv/bin/python3[.N]` in *command position*:
#   - start of command, or after a chain separator (`;`, `&&`, `|`)
#   - optionally preceded by env var assignments (FOO=bar BAZ=qux)
#   - optionally preceded by a path prefix (./, /abs/path/, etc.)
# Does NOT match when `.venv/bin/python` appears as an argument to another
# command (`ls .venv/bin/python`, `grep '.venv/bin/python' .`).
VENV_PYTHON_RE = re.compile(
    r'(?:^|[;&|]+\s*)'                 # start of command or chain separator
    r'(?:[A-Za-z_]\w*=\S+\s+)*'        # optional env var assignments
    r'\S*\.venv/bin/python\d*(?:\.\d+)?\b'  # optional path prefix, .venv/bin/python[3[.N]]
)

DENY_REASON = (
    "Blocked: `.venv/bin/python(3)`. The Python policy in your global "
    "CLAUDE.md says use `uv run python` — and the allowlist is shaped "
    "around that (`Bash(uv *)`, `Bash(python *)`, `Bash(python3 *)`). "
    "`.venv/bin/python` matches none of those, so it prompts Dan every "
    "single time. Rewrite as: `uv run python <args>` (or, if you're in "
    "the project root, bare `python <args>` also works). "
    "If this is the second time you've tripped this hook in one session, "
    "apologize — Dan put it in for a reason."
)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if not VENV_PYTHON_RE.search(command):
        sys.exit(0)

    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": DENY_REASON,
        }
    }
    print(json.dumps(response))
    sys.exit(0)


if __name__ == "__main__":
    main()
