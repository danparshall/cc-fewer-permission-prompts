#!/usr/bin/env python3
"""PreToolUse hook: hard-fail Bash commands whose leading "verb" is an
absolute or relative path ending in `.py` (e.g. `/Users/dan/code/dotfiles/
claude-hooks/test_X.py 2>&1 | tail -3`, `./foo.py`, `bin/script.py arg`).

Background: this is NOT a matcher static-analysis bail (Family 1/2/3) — it's
a plain allow-rule miss. The matcher tokenizes the command and checks the
leading word against the allow list. `Bash(python *)` / `Bash(python3 *)`
cover the interpreter when it's the verb; `Bash(/Users/dan/code/dotfiles/
*.sh *)` covers `.sh` paths under the dotfiles tree. But NO rule covers
`.py` paths in verb position, so invoking a `.py` script directly via its
absolute or relative path puts an unrecognized "verb" at command start →
matcher soft-prompts Dan. The agent's training-data instinct is "if the
file is `chmod +x`'d with a Python shebang, just run it" — which the
matcher rejects because it checks the leading token against allow rules
and that token is the path itself, not `python3`.

Dan chose Strategy 2 (hard-fail hook) over Strategy 1 (add a
`Bash(/Users/.../*.py *)` allow rule) to train the canonical interpreter-
leading form rather than expand the allow surface — same training-pressure
rationale as the chain hook. See docs/active/chain-hook-maintenance/
STRATEGIES.md item #6.

Detection (PATH_PY_VERB_RE, anchored at command start):
  - `^\\s*['"]?` — optional leading whitespace + optional opening quote.
  - `\\S*/\\S*` — at least one slash inside the leading non-whitespace
    token; this is what distinguishes a path (`./foo.py`, `/abs/foo.py`,
    `subdir/foo.py`) from a bare-verb `foo.py` (which is out of scope —
    no slash, would prompt via normal allow-rule miss without our
    intervention).
  - `\\.py` — literal `.py` extension.
  - `['"]?(?:\\s|$)` — optional closing quote + whitespace or end-of-
    command boundary. The boundary is what prevents `path.py.bak` from
    matching as `path.py` + `.bak` — the next char after `.py` must be
    whitespace, EOF, or a closing quote followed by one of those.

Stripping (none):
  - `strip_inert` is deliberately NOT used here. The `^\\s*` anchor +
    boundary `(?:\\s|$)` already prevent matches at non-leading positions
    (`cat "/path/to/foo.py"` — leading verb is `cat`, no `/`, no match;
    `$(/path/to/foo.py)` — `)` after `.py` fails the boundary). Stripping
    would BREAK the leading-quote DENY cases — `"/Users/dan/foo.py" arg`
    becomes `"" arg` after strip, no `/`, no match. Trading correctness
    on the spec'd DENY cases for redundant defensiveness is a bad trade.
  - Heredoc-body stripping is also not needed — a heredoc body never sits
    in leading-verb position, and the `^\\s*` anchor enforces that.

Hook ordering (registered after block_bash_chains.py in PreToolUse):
  - For chained commands (`/abs/foo.py && other`), block_bash_chains.py
    hard-denies first (mixed-chain → non-blanket leading verb), so our
    hook never runs in that case. We test our regex's behavior in
    isolation though — it WILL fire on the chain shape if reached.

Sibling of block_brace_expansion.py / block_heredoc_with_pipe_or_redirect.py
/ block_brace_quote_heredoc.py — same Strategy-2 architecture, but
epistemically distinct: those three close matcher heuristics (Family 1/3
static-analysis bails) that allow rules CANNOT override; this one closes
an allow-rule MISS that Strategy 1 could in principle have closed. Dan
chose Strategy 2 deliberately to train interpreter-leading form. See
STRATEGIES.md item #6.
"""
import json
import re
import sys

# Bash command with .py-extension path as its leading verb.
#
# - `^\s*` anchors at command start (after optional leading whitespace).
# - `['"]?` optionally consumes a leading single/double quote (bash
#   tokenizes `"/path/foo.py"` as one token; the matcher sees the path).
# - `\S*/\S*` requires at least one `/` inside the leading non-whitespace
#   token. This is the key discriminator: a bare-verb `foo.py` has no `/`
#   and is out of scope (would prompt via normal allow-rule miss anyway,
#   without our intervention).
# - `\.py` literal — the extension we scope to.
# - `['"]?(?:\s|$)` optional closing quote + whitespace/EOF boundary.
#   This prevents `path.py.bak` from matching as `path.py` + `.bak`.
PATH_PY_VERB_RE = re.compile(
    r"""
    ^\s*                # leading whitespace
    ['"]?               # optional opening quote
    \S*                 # any non-whitespace prefix (slashes, dots, alphanumerics)
    /                   # require at least one slash — distinguishes path from bare verb
    \S*                 # rest of the path
    \.py                # must end in .py
    ['"]?               # optional closing quote
    (?:\s|$)            # must be followed by whitespace or end-of-command
    """,
    re.VERBOSE,
)

NASTYGRAM = (
    "Blocked: this command's leading verb is a path ending in `.py` "
    "(e.g. `/Users/.../foo.py` or `./foo.py`). Claude Code's matcher "
    "checks the leading token against allow rules — `Bash(python *)` / "
    "`Bash(python3 *)` cover the interpreter when IT is the verb, but no "
    "`Bash(/Users/.../*.py *)` allow rule exists, so the matcher prompts "
    "Dan on the unknown verb. This hook hard-fails the pattern so you "
    "don't click through the prompt on autopilot.\n\n"
    "Fix: invoke via the interpreter — prepend `python3 ` to make "
    "`Bash(python3 *)` cover it. The rest of the command (including any "
    "`2>&1 | tail -3` or other tail) can be preserved verbatim — only "
    "the leading word changes:\n\n"
    "  # before: prompts\n"
    "  /Users/dan/code/dotfiles/claude-hooks/test_X.py 2>&1 | tail -3\n"
    "  # after:  silent\n"
    "  python3 /Users/dan/code/dotfiles/claude-hooks/test_X.py 2>&1 | tail -3\n\n"
    "See docs/active/chain-hook-maintenance/STRATEGIES.md item #6."
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

    if PATH_PY_VERB_RE.match(command):
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
