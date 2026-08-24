#!/usr/bin/env python3
"""PreToolUse hook: hard-fail heredoc bodies containing brace+quote
patterns that trip Claude Code's anti-obfuscation matcher heuristic.

Background: Claude Code's permission matcher has an anti-obfuscation
detector that flags brace immediately followed by a quote character
(e.g. `{"key":"val"}`, `['a','b']`) and prompts Dan with the diagnostic
"Contains brace with quote character (expansion obfuscation)" — even
when `Bash(python3 *)` / `Bash(uv *)` are individually allowed.

Empirically the heuristic fires on UNQUOTED-at-bash-level contexts only:
heredoc bodies trip it; properly single- or double-quoted strings do not
(verified 2026-05-30 HITL probe; see docs/active/chain-hook-maintenance/
FINDINGS.md and STRATEGIES.md).

Since no allow rule can override the heuristic (Strategy 1 fails — the
matcher checks command structure, not just the allow list), this hook
implements Strategy 2: detect the pattern in heredoc bodies and deny
with a useful message pointing Claude to the Write-then-run alternative.
"""
import json
import re
import sys

# Match heredoc open: <<DELIM / <<'DELIM' / <<"DELIM" / <<-DELIM variants.
# Group 1 = optional quote, Group 2 = delimiter word.
HEREDOC_OPEN_RE = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")

# Brace or bracket followed by (optional whitespace then) a quote character —
# the pattern Claude Code's matcher flags. Catches `{"...`, `['...`, `[ "..."`
# and similar dict/list-literal openings.
BRACE_QUOTE_RE = re.compile(r"[\{\[]\s*['\"]")

NASTYGRAM = (
    "Blocked: heredoc body contains a brace+quote pattern "
    "(e.g. `{\"key\":\"val\"}` or `['x','y']`) that trips Claude Code's "
    "anti-obfuscation matcher heuristic. The matcher will prompt Dan on "
    "this command even though `Bash(python3 *)` / `Bash(uv *)` are "
    "individually allowed — it's a heuristic separate from the allow list.\n\n"
    "Fix: Write the script to a file, then run it as a SEPARATE Bash call.\n"
    "  1. Write('/tmp/probe_<name>.py', <python source>)\n"
    "  2. Separate Bash call: python3 /tmp/probe_<name>.py\n\n"
    "The temp script keeps the brace+quote in a file, not the bash command "
    "string, so the heuristic doesn't fire. See "
    "docs/active/chain-hook-maintenance/STRATEGIES.md for the framework."
)


def find_heredoc_bodies(command: str):
    """Yield (delimiter, body) for each heredoc found in command.

    Body is the text between the heredoc-open line and the closing
    delimiter line (or end-of-command if no closing line is found).
    Naive: doesn't handle nested heredocs or heredocs inside command
    substitutions, but covers the common single-heredoc case.
    """
    for m in HEREDOC_OPEN_RE.finditer(command):
        delim = m.group(2)
        rest = command[m.end():]
        close_re = re.compile(
            r"^\s*" + re.escape(delim) + r"\s*$", re.MULTILINE
        )
        close_m = close_re.search(rest)
        if close_m:
            yield delim, rest[:close_m.start()]
        else:
            yield delim, rest


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    for _delim, body in find_heredoc_bodies(command):
        if BRACE_QUOTE_RE.search(body):
            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": NASTYGRAM,
                }
            }
            print(json.dumps(response))
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
