#!/usr/bin/env python3
r"""PreToolUse hook: hard-fail Bash commands containing a bash brace
expansion (`{a,b}`, `{1,2,3}`, `{1..5}`, etc.) in shell-argument position.

Background: Claude Code's permission matcher parses commands with a real
shell grammar (tree-sitter-bash). It silently allows commands whose full
effect it can statically bound, but BAILS — prompting Dan with "Contains
shell syntax (brace_expansion) that cannot be statically analyzed" — when
a bash brace expansion appears unquoted in argument position. The
expansion is shell-runtime: `mv /p/{a,b}.txt /dest/` becomes two distinct
`mv` invocations the matcher can't enumerate without running the shell.
This is true even when `Bash(mv *)` / `Bash(ls *)` / etc. are individually
allowed — it's a structural static-analysis bail, pre-allow-list, so no
allow rule can override it (same class as the heredoc+pipe/redirect bail
and the Family 1/2 built-in heuristics). See docs/active/chain-hook-
maintenance/FINDINGS.md (entry 2026-06-05, NEW Family-3 row, second after
heredoc+pipe/redirect; empirically isolated via the `ls /tmp/{a,b}` HITL
probe — minimal possible shape, allow-listed verb, single segment, no
chain, no quotes — and the prompt UI reported "Brace expansion" as the
heuristic name).

The matcher only soft-prompts, and an agent tends to click through it on
autopilot. This hook (Strategy 2 per STRATEGIES.md) converts the soft-
prompt into a hard-fail pointing at the enumerate-explicitly dodge —
which removes the shell-expansion construct entirely, restoring the
matcher's ability to statically bound effects.

Detection (regex BRACE_EXPANSION_RE):
  - `\{[^{}\s]*(?:,|\.\.)[^{}\s]*\}` — open brace, content with no
    whitespace and at least one `,` or `..`, close brace.
  - Negative lookbehind for `$` excludes parameter expansion `${VAR}`
    and `${VAR:-default,foo}`, which is a different construct.
  - The no-whitespace requirement is what bash itself enforces: `{a, b}`
    (with a space) is NOT expanded by bash and stays literal — so it's
    safe to ignore here too. This also excludes bash code blocks
    `{ cmd1; cmd2; }` (space after `{`) and function bodies.
  - Requiring `,` or `..` excludes `{}` (find -exec placeholder) and
    quoted JSON-shaped braces like `{"k":"v"}` without a comma (the
    sibling block_brace_quote_heredoc hook covers `{"...","..."}`).

Stripping (before scanning):
  1. Heredoc bodies are removed — Python set/dict literals
     (`data = {1, 2, 3}` or `{1,2,3}`) inside heredoc bodies must never
     false-positive. Bash brace expansion only happens in shell-argument
     positions, never inside heredoc body text (which is stdin).
  2. Single-quoted, double-quoted, $()-substituted, and backtick-
     substituted content is replaced with empty placeholders so braces
     inside those contexts (`echo "{a,b}"`, `echo '{a,b}'`) don't fire.

Sibling of block_brace_quote_heredoc.py / block_heredoc_with_pipe_or_redirect
/ block_newline_hash_in_quoted_arg.py — same family of matcher false
positives (Family 1 + Family 3), same Strategy-2 remediation. Coexists with
block_bash_chains.py (the chain hook deliberately lets all-blanket chains
through to the matcher per the Plan 01 redesign; this hook catches the
ones whose static-analysis bail would have otherwise hit Dan with a
permission prompt).
"""
import json
import re
import sys

# Match heredoc open: <<DELIM / <<'DELIM' / <<"DELIM" / <<-DELIM variants.
# Group 1 = optional quote, Group 2 = delimiter word. Same regex as the
# sibling block_brace_quote_heredoc / block_heredoc_with_pipe_or_redirect.
HEREDOC_OPEN_RE = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")

# Bash brace expansion in argument position: `{alt,alt,...}`, `{a..b}`,
# `{a..b..step}`, or any combination thereof.
#
# - `(?<!\$)` excludes parameter expansion `${...}` (which is a different
#   construct; the `$` cues the matcher to a parameter-expansion node,
#   and an unquoted comma inside `${...:-default,foo}` is a literal
#   default-value char, not an alternation).
# - `[^{}\s]*` requires no whitespace inside the braces — matching bash's
#   own rule (`{a, b}` with a space is not expanded, it stays literal).
#   This also rules out bash code blocks `{ cmd; cmd; }` (space after
#   the brace) and function-body braces.
# - `(?:,|\.\.)` requires at least one alternation operator inside. This
#   distinguishes brace expansion from `{}` (find -exec placeholder).
BRACE_EXPANSION_RE = re.compile(r"(?<!\$)\{[^{}\s]*(?:,|\.\.)[^{}\s]*\}")

NASTYGRAM = (
    "Blocked: this command contains a bash brace expansion "
    "(e.g. `{a,b}`, `{1,2,3}`, `{1..5}`). Claude Code's matcher can't "
    "statically enumerate what the braces will expand to at shell runtime "
    "and will prompt Dan (\"Contains shell syntax (brace_expansion) that "
    "cannot be statically analyzed\") — even when the leading verb "
    "(`mv`, `cp`, `ls`, `mkdir`, etc.) is in the allow list. This hook "
    "hard-fails the pattern so you don't click through the prompt on "
    "autopilot.\n\n"
    "Fix: enumerate the expanded paths as SEPARATE Bash tool calls (cwd "
    "persists across calls). For example, `mv /p/{a,b}.txt /dest/` becomes:\n"
    "  1. Separate Bash call: mv /p/a.txt /dest/\n"
    "  2. Separate Bash call: mv /p/b.txt /dest/\n\n"
    "A common-prefix glob works too if the targets share one — e.g. "
    "`mv /p/*.txt /dest/` — but only when the glob doesn't pull in files "
    "you didn't want. For complex multi-step file ops (cross-product "
    "brace expansions with no shared prefix), write a shell script with "
    "the Write tool and run it as one Bash call. See "
    "docs/active/chain-hook-maintenance/STRATEGIES.md."
)


def strip_inert(cmd: str) -> str:
    """Replace single-quoted, double-quoted, $(...), and `...` content with
    empty placeholders so brace patterns inside them don't match. Mirrors
    the helper of the same name in block_bash_chains.py. Naive: doesn't
    handle escaped quotes or nested substitutions, but covers the common
    cases (and false-negatives here are safe — the matcher generally
    doesn't fire on quoted braces either)."""
    cmd = re.sub(r"'[^']*'", "''", cmd)
    cmd = re.sub(r'"[^"]*"', '""', cmd)
    cmd = re.sub(r"\$\([^)]*\)", "$()", cmd)
    cmd = re.sub(r"`[^`]*`", "``", cmd)
    return cmd


def strip_heredoc_bodies(command: str) -> str:
    """Remove the body of every heredoc from `command`. Bash brace expansion
    does not happen inside heredoc bodies (which are stdin text passed to
    the command, never shell-expanded) — so Python set/dict literals like
    `{1, 2, 3}` or `{1,2,3}` in heredoc bodies must not false-positive.

    Naive: doesn't handle nested heredocs or heredocs inside command
    substitutions, but covers the common single-heredoc case (mirrors the
    body-finder in block_brace_quote_heredoc.py)."""
    out = []
    cursor = 0
    for m in HEREDOC_OPEN_RE.finditer(command):
        # Only process heredoc opens that lie in the still-uncovered tail.
        if m.start() < cursor:
            continue
        delim = m.group(2)
        nl_after = command.find("\n", m.end())
        if nl_after == -1:
            # Open with no newline after — malformed; keep tail as-is.
            break
        # Keep everything up to and including the open line's `\n`.
        out.append(command[cursor:nl_after + 1])
        # Find the closing delimiter line.
        close_re = re.compile(
            r"^\s*" + re.escape(delim) + r"\s*$", re.MULTILINE
        )
        rest_start = nl_after + 1
        close_m = close_re.search(command, rest_start)
        if close_m:
            # Skip the body, resume from the close-line start.
            cursor = close_m.start()
        else:
            # Unterminated heredoc — body runs to EOF. Drop everything after.
            cursor = len(command)
            break
    out.append(command[cursor:])
    return "".join(out)


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

    # Order matters: strip heredoc bodies first (the body itself may contain
    # quoted strings that strip_inert would otherwise corrupt; we want the
    # body gone entirely), then strip quoted/substituted regions.
    scan = strip_heredoc_bodies(command)
    scan = strip_inert(scan)

    if BRACE_EXPANSION_RE.search(scan):
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
