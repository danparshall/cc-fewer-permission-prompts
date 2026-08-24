#!/usr/bin/env python3
"""PreToolUse hook: hard-fail Bash commands where a `<<` heredoc co-occurs
with a pipe/redirect on the heredoc's command line — the "Family 3" matcher
prompt.

Background: Claude Code's permission matcher parses commands with a real
shell grammar (tree-sitter-bash). It silently allows commands whose full
effect it can statically bound, but BAILS — prompting Dan with "Contains
shell syntax (file_redirect) that cannot be statically analyzed" or
"...(pipeline)..." — when a heredoc co-occurs with a pipeline or an extra
redirect. Heredoc alone is analyzable (silent); a pipe/redirect *without*
a heredoc is analyzable (silent); the combination is what trips it. This
is true even when `Bash(python3 *)` / `Bash(uv *)` are individually allowed
— it's a structural static-analysis bail, pre-allow-list, so no allow rule
can override it (same class as the Family 1/2 built-in heuristics). See
docs/active/chain-hook-maintenance/FINDINGS.md (entry 2026-06-05, 12-cell
probe matrix P0–P11) for the empirical basis.

The matcher only soft-prompts, and an agent tends to click through it on
autopilot. This hook (Strategy 2 per STRATEGIES.md) converts the soft-prompt
into a hard-fail pointing at the Write-then-run dodge — which removes the
heredoc entirely, so the file-based replacement may KEEP its `2>&1 | grep`
tail freely.

Detection boundary (this is what keeps Dan's plain heredocs working):
The only place a pipe/redirect can bind to a heredoc *command* in valid
bash is the OPEN LINE — the physical line carrying `<<DELIM`, before or
after the operator (`python3 - <<'PY' 2>&1 | grep`, or `python3 - 2>&1
<<'PY'`). So we scan ONLY the open line, with the heredoc operator(s)
themselves removed, and we deliberately do NOT scan:
  - the heredoc BODY (Python `a | b`, `c > d`, `1 << 2` must never fire), or
  - text after the closing delimiter (that belongs to separate commands;
    a pipe there is not a confirmed Family-3 trigger).
A redirect/pipe on a line *after* the body is therefore left alone, and a
trailing `... PY | grep x` on the delimiter line is bash-malformed (the
`| grep x` is body, not a pipe) so it correctly does not fire.

Sibling of block_brace_quote_heredoc.py and block_newline_hash_in_quoted_arg.py
— same family of matcher false positives, same Write-then-run remediation.
Coexists with block_bash_chains.py (a single `|` is not a chain op, so a
heredoc+pipe passes that hook and is caught here).

Known limitation: a quoted operator on the open line that is an argument
rather than an operator (e.g. `grep ">" <<'PY'`) would false-positive. Not
observed in practice, and the deny→Write-then-run remedy is still safe; if
it ever over-fires the regex is the single point to adjust (see
docs/active/chain-hook-maintenance/STRATEGIES.md).
"""
import json
import re
import sys

# Match heredoc open: <<DELIM / <<'DELIM' / <<"DELIM" / <<-DELIM variants.
# Group 1 = optional quote, Group 2 = delimiter word. Lifted from the sibling
# block_brace_quote_heredoc.py. Note `<<<` herestrings do NOT match (the third
# `<` is neither a quote nor a \w), so they are out of scope by construction.
HEREDOC_OPEN_RE = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")

# A pipe or any redirect operator. After the heredoc operator(s) are stripped
# from the open line, any remaining `|`, `<`, or `>` is a pipe/redirect (the
# open line is bash code; these chars are operators there).
REDIR_OR_PIPE_RE = re.compile(r"[|<>]")

NASTYGRAM = (
    "Blocked: this command combines a heredoc (`<<`) with a pipe/redirect "
    "on the same command line. Claude Code's matcher can't statically "
    "analyze that and will prompt Dan (\"Contains shell syntax "
    "(file_redirect/pipeline) that cannot be statically analyzed\") — even "
    "when `Bash(python3 *)` / `Bash(uv *)` are individually allowed. This "
    "hook hard-fails the pattern so you don't click through the prompt on "
    "autopilot.\n\n"
    "Fix: Write the body to a file and run it as a SEPARATE Bash call — the "
    "file-based command may KEEP its `2>&1 | grep ...` tail (removing the "
    "heredoc is what makes it statically analyzable again):\n"
    "  1. Write('/tmp/<name>.py', <source>)\n"
    "  2. Separate Bash call: python3 /tmp/<name>.py 2>&1 | grep ...\n\n"
    "A plain heredoc with NO pipe/redirect is fine — only the combination "
    "trips this. See docs/active/chain-hook-maintenance/STRATEGIES.md."
)


def heredoc_open_lines(command: str):
    """Yield the open line of each heredoc with all heredoc operators removed.

    The "open line" is the physical line containing the `<<DELIM` operator
    (from the preceding newline to the following newline). All `<<DELIM`
    tokens on that line are stripped so the heredoc's own `<<` (and any
    second heredoc on the same line) never registers as a redirect. The
    heredoc body and any post-close text are excluded entirely.
    """
    seen_line_starts = set()
    for m in HEREDOC_OPEN_RE.finditer(command):
        line_start = command.rfind("\n", 0, m.start()) + 1
        if line_start in seen_line_starts:
            continue
        seen_line_starts.add(line_start)
        nl_after = command.find("\n", m.end())
        line_end = nl_after if nl_after != -1 else len(command)
        open_line = command[line_start:line_end]
        # Strip every heredoc operator on this line (handles multi-heredoc
        # lines and avoids counting the heredoc's own `<<` as a redirect).
        yield HEREDOC_OPEN_RE.sub("", open_line)


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

    for open_line in heredoc_open_lines(command):
        if REDIR_OR_PIPE_RE.search(open_line):
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
