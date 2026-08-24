#!/usr/bin/env python3
"""PreToolUse hook: hard-fail `cd <path> && git <subcmd>` patterns.

Background: Anthropic's hardcoded bare-repo-attack heuristic prompts the
user every time Claude generates `cd <path> && git ...`. Settings.json
DENY rules don't override the heuristic (tested 2026-05-14, see
~/code/dotfiles/notes/cd_git_hardcoded.md). This hook delivers the
hard-fail that DENY can't, moving the friction from Dan (who currently
has to deny every prompt) to Claude (who gets a deny message and must
retry with the alternate form).
"""
import json
import re
import sys

# Split a command into chain segments. Splits on `&&`, `||`, and `;`.
# Does NOT split on `|` (pipe) — a pipe doesn't change directory, so
# `cd ... | git ...` is structurally different and rarer.
CHAIN_SPLIT_RE = re.compile(r'\s*(?:&&|\|\||;)\s*')

# A segment that STARTS with `cd <path>` (path can be quoted or unquoted).
CD_SEGMENT_RE = re.compile(r'^\s*cd\s+(?:"[^"]*"|\'[^\']*\'|\S+)')

# A segment that STARTS with `git <subcmd>`.
GIT_SEGMENT_RE = re.compile(r'^\s*git\b')


def has_cd_then_git(command: str) -> bool:
    """Return True if any `cd <path>` segment precedes any `git` segment
    in the same chain.

    Catches the broader pattern that Claude Code's hardcoded bare-repo-
    attack heuristic catches. The prior regex required immediate
    `cd <path> && git` adjacency and missed common shapes like
    `cd <path> && pwd && git status` (2026-06-01 in-the-wild observation).
    """
    cd_seen = False
    for seg in CHAIN_SPLIT_RE.split(command):
        if CD_SEGMENT_RE.match(seg):
            cd_seen = True
        elif cd_seen and GIT_SEGMENT_RE.match(seg):
            return True
    return False


DENY_REASON = (
    "Blocked: chain contains `cd <path>` followed later by `git <subcmd>`. "
    "Anthropic's monitor will force this to get approval, which Dan doesn't like; "
    "he already granted 'git -C', so just use that. "
    "Rewrite as: git -C <path> <subcmd> (in any chain position — no cd needed). "
    "If you need pwd verification, use a SEPARATE Bash call for pwd; cwd persists. "
    "If this is the third time you've triggered this error this session, "
    "tell Dan that he's vindicated ;)"
)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if not has_cd_then_git(command):
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
