#!/usr/bin/env python3
"""PreToolUse hook: hard-fail commands containing `\\n#` (newline then `#`)
inside a quoted region — the pattern that trips Claude Code's
"Newline followed by # inside a quoted argument can hide arguments from
path validation" anti-obfuscation heuristic.

Background: Claude Code's permission matcher has a family of anti-
obfuscation lexers (see docs/active/chain-hook-maintenance/FINDINGS.md).
One of them, surfaced via the matcher's own diagnostic string, fires on
`\\n#` inside `"..."` or `'...'` quoted regions. The matcher's worry: an
obfuscator could put dangerous arguments after a fake bash-comment, and
a path-validation pass that stops at `#` would miss them.

This false-positives heavily on legitimate Python `python3 -c "..."`
bodies that contain comments — a very common shape. The matcher prompts
Dan with the diagnostic; rather than let Dan click-through on autopilot,
this hook converts the soft-prompt into a hard-fail and points the agent
at the documented Write-then-run alternative (or, for repeated use, a
git-tracked script).

Sibling of block_brace_quote_heredoc.py — same family of heuristics, same
Write-then-run remediation. See STRATEGIES.md for the framework.
"""
import json
import re
import sys


# Match `\n` optionally followed by whitespace, then `#`. Whitespace tolerated
# because indented Python comments (`def f():\n    # comment`) are equally
# common and equally caught by the matcher heuristic in practice.
NEWLINE_HASH_RE = re.compile(r"\n[ \t]*#")


def find_quoted_regions(command: str):
    """Yield (quote_char, body, start_idx) for each top-level quoted region.

    Quote-aware lexer that approximates bash's tokenization for the purpose
    of matching Claude Code's heuristic. Notes:

    - Single quotes are literal: no escape processing, ended only by `'`.
    - Double quotes allow `\\` to escape the following character.
    - Top-level only — we don't recurse into nested $() / ${} / backticks.
      The matcher likely doesn't either; if a future probe shows otherwise
      we can extend.
    """
    i = 0
    n = len(command)
    while i < n:
        ch = command[i]
        if ch == "'":
            j = command.find("'", i + 1)
            if j == -1:
                return
            yield "'", command[i + 1:j], i + 1
            i = j + 1
        elif ch == '"':
            j = i + 1
            while j < n:
                if command[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if command[j] == '"':
                    break
                j += 1
            if j >= n:
                return
            yield '"', command[i + 1:j], i + 1
            i = j + 1
        else:
            i += 1


NASTYGRAM = (
    "Blocked: command contains `\\n#` (newline followed by `#`) inside a "
    "quoted argument. Claude Code's matcher will prompt Dan with the "
    "anti-obfuscation diagnostic \"Newline followed by # inside a quoted "
    "argument can hide arguments from path validation\" — even when "
    "`Bash(python3 *)` / `Bash(uv *)` are individually allowed. This hook "
    "hard-fails the pattern so you don't click through the prompt on "
    "autopilot.\n\n"
    "Decide first: is this a one-shot, or will it happen again?\n\n"
    "ONE-SHOT — fine, just move the body to a file so the heuristic can't "
    "see the literal `\\n#`:\n"
    "  1. Write('/tmp/probe_<name>.py', <python source with the comments "
    "you wanted>)\n"
    "  2. Separate Bash call: python3 /tmp/probe_<name>.py\n\n"
    "REPEATED USE (you've solved a similar shape before, or expect to do "
    "this again) — make it a git-tracked script in the current repo so "
    "future-you and Dan can find it without re-typing:\n"
    "  1. Write('<repo>/scripts/<name>.py', <python source>)  (or wherever "
    "the project parks reusable scripts; check the repo's conventions)\n"
    "  2. Separate Bash call: python3 <repo>/scripts/<name>.py\n"
    "  3. Commit so the next session inherits the work.\n\n"
    "Either way, moving the body to a file means the newline+# never "
    "appears in the bash command string and the heuristic doesn't fire. "
    "See docs/active/chain-hook-maintenance/STRATEGIES.md for the "
    "framework — this is the same Write-then-run pattern as the brace+quote "
    "heredoc case."
)


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

    for _quote, body, _start in find_quoted_regions(command):
        if NEWLINE_HASH_RE.search(body):
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
