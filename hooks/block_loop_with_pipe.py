#!/usr/bin/env python3
r"""PreToolUse hook: hard-fail a bash loop whose body Claude Code's permission
matcher can't statically analyze — i.e. a loop containing a pipe (`|`) OR a
variable expansion (`$i`, `${x}`) — and redirect to a clean alternative.

(Filename is historical: this started as a pipe-only hook. It now also covers
the variable case, isolated 2026-06-06 — see below. The "pipe" in the name is
the canonical/first-found shape, not the only one.)

Background — the matcher body-analyzes a loop. The matcher parses commands
with a real shell grammar (tree-sitter-bash) and, for a loop, looks INSIDE
the body: if every effect is statically boundable, it auto-approves the loop
silently — even with no `Bash(for *)` allow rule. But if the body contains a
node whose effect it can't bound without running the shell, it BAILS with
"Contains shell syntax (<node>) that cannot be statically analyzed" and
prompts Dan. Two such loop-body nodes are known (both empirically isolated;
docs/active/chain-hook-maintenance/FINDINGS.md):

  - `pipeline`         — a pipe `|` in the body. A bare top-level pipe is fine
                         (leading-verb fast-path); nested in a loop body the
                         fast-path doesn't apply and it bails. (2026-06-05.)
  - `simple_expansion` — a bare variable `$i` / `$f` in the body. A variable
                         at top level is fine (`echo $HOME` runs constantly);
                         in a loop body the matcher can't bound the value and
                         bails. (2026-06-06, isolated via the headless
                         marker-file probe: `for i …; do touch /tmp/x_$i; done`
                         BLOCKED on "simple_expansion"; the variable-free
                         `… do touch /tmp/static; done` RAN.)

Critically, a COMMAND SUBSTITUTION `$(…)` in the loop body does NOT bail
(FINDINGS probe 03: `until true; do echo "$(date +%s)"; done` ran silent) —
the matcher can recurse into the substituted command and bound it, whereas a
bare variable is an unknowable value. So this hook fires on `$var` but NOT on
`$(`.

Why this exists — almost every USEFUL loop references its loop variable
(`$i`, `$f`, `$line`) or pipes, so in practice the matcher prompts on nearly
every real loop. A prompt is a tax on Dan's parallelism (the chain-hook
work-line thesis). This hook converts that soft, cryptic, per-loop prompt
into a hard-fail with a concrete redirect (Python / Monitor / a temp var /
separate Bash calls), moving the friction to Claude. Genuinely-static loops
(no pipe, no variable) still run silently — the matcher allows them and this
hook leaves them alone.

Detection — fire iff ALL THREE conjuncts hold:
  1. LOOP_RE — a loop keyword: for / while / until / select   (on full-strip)
  2. DO_RE   — `\bdo\b`                                        (on full-strip)
  3. (PIPE_RE on full-strip)  OR  (VAR_RE on single-quote-strip)

The `\bdo\b` conjunct is LOAD-BEARING and non-negotiable. Without it the
detector hard-denies ordinary commands, because `for`/`while`/`until` are
common words in arguments AND `$var` is ubiquitous (`grep for x | head`,
`echo "cost $total"`). Real loops are always `for/while/until … do … done`;
`\bdo\b` is rare as a standalone word in normal commands and does NOT match
`sudo`, `done`, or `window`. The three conjuncts together scope the over-fire
to actual loop-shaped commands — the false-positive class Dan signed off on
(FP cost = a Claude rewrite to Python/parallel calls; FN cost = a Dan prompt).

Two strip levels (a variable expands inside DOUBLE quotes but not SINGLE
quotes; a pipe and the loop keywords are inert inside BOTH):
  - LOOP_RE / DO_RE / PIPE_RE are checked on the BOTH-quotes-stripped string,
    so a loop word or pipe inside any quoted string (`echo "for x | y"`) is
    inert and a fake keyword can't trip the loop/do gate.
  - VAR_RE is checked on the SINGLE-quote-only-stripped string, so `$i` inside
    double quotes (`echo "row $i"` — which DOES expand and DOES bail) still
    fires, while `$i` inside single quotes (`echo '$i'` — literal, no bail)
    does not. `$(` command substitution is excluded by VAR_RE itself.

This is a DUMB-BUT-NOT-BLIND detector: regex-only, no nesting/AST analysis.
It does not verify the pipe/variable is literally between `do` and `done`, so
a bare loop alongside an unrelated pipe or variable (`x=$foo; for i …; do :;
done`, or `for …; done; ls | head`) over-fires. Accepted: cost is a cheap
rewrite.

Sibling of block_heredoc_with_pipe_or_redirect / block_brace_expansion —
same Family-3 matcher false-positive class, same Strategy-2 remediation.
Coexists with block_bash_chains.py: the chain hook short-circuits on
flow-control, so a loop passes it untouched and is caught here.
"""
import json
import re
import sys

# A loop keyword in word position. `select` is included for completeness
# (rare, interactive); it shares the `do…done` structure.
LOOP_RE = re.compile(r"\b(for|while|until|select)\b")

# The loop's `do` keyword. `\bdo\b` does NOT match `sudo` (no boundary
# before), `done` (no boundary after), or `window` (no `do` substring).
DO_RE = re.compile(r"\bdo\b")

# A lone pipe: a single `|` that is not part of a `||`. The lookarounds
# exclude both halves of `||` (the common `a || b` loop-body fallback idiom
# is logical-OR, not a pipeline, so it must not fire).
PIPE_RE = re.compile(r"(?<!\|)\|(?!\|)")

# A variable expansion: `$` followed by an optional `{` then a name/positional/
# special-parameter char. Matches `$i`, `$foo`, `$1`, `${x}`, `${x:-d}`, `$@`,
# `$?`, `$*`, `$#`, `$!`, `$-`. Deliberately does NOT match `$(` (command
# substitution) or `$((` (arithmetic) — the matcher can analyze a command
# substitution (FINDINGS probe 03: loop+cmdsub runs silent), only a bare
# variable bails. A trailing literal `$` (followed by space/end) also doesn't
# match (no class char after).
VAR_RE = re.compile(r"\$\{?[\w@*?#!-]")

NASTYGRAM = (
    "Blocked: this command is a loop whose body Claude Code's matcher can't "
    "statically analyze — it contains a pipe (`|`) and/or a variable "
    "expansion (`$i`, `${x}`) inside the loop. The matcher body-analyzes a "
    "loop and auto-approves it ONLY when every effect is statically "
    "boundable; a pipe or a bare variable in the body makes it bail "
    "(\"Contains shell syntax (pipeline / simple_expansion) that cannot be "
    "statically analyzed\") and prompt Dan — even though bare pipes and bare "
    "variables are both fine outside a loop. This hook hard-fails the pattern "
    "so you don't click through the prompt on autopilot.\n\n"
    "Fix — replace the loop with something the matcher (or no matcher) can "
    "handle:\n"
    "  - Do the work in Python: Write a script, then `uv run python "
    "<script>` (one Bash call, no loop, no per-item prompt).\n"
    "  - Unroll to SEPARATE Bash tool calls, one per item (cwd persists "
    "across calls) — good for a handful of known items.\n"
    "  - For a wait-until-condition monitor loop, use the Monitor tool.\n"
    "  - A genuinely static loop with NO pipe and NO variable in the body "
    "(e.g. `for i in 1 2 3; do echo hi; done`) is allowed and runs silently — "
    "but that's rarely what you want.\n\n"
    "See docs/active/chain-hook-maintenance/STRATEGIES.md."
)


def strip_all_quotes(cmd: str) -> str:
    """Blank single- AND double-quoted content. Used for the loop/do/pipe
    conjuncts: a loop keyword or pipe inside any quoted string is inert."""
    cmd = re.sub(r"'[^']*'", "''", cmd)
    cmd = re.sub(r'"[^"]*"', '""', cmd)
    return cmd


def strip_single_quotes(cmd: str) -> str:
    """Blank single-quoted content only. Used for the variable conjunct: a
    `$var` inside SINGLE quotes is literal (no expansion, no matcher bail), but
    a `$var` inside DOUBLE quotes DOES expand and DOES bail — so double-quoted
    content must be kept when scanning for variables."""
    return re.sub(r"'[^']*'", "''", cmd)


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

    full = strip_all_quotes(command)
    var_scan = strip_single_quotes(command)

    has_loop = LOOP_RE.search(full)
    has_do = DO_RE.search(full)
    has_pipe = PIPE_RE.search(full)
    has_var = VAR_RE.search(var_scan)

    if has_loop and has_do and (has_pipe or has_var):
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
