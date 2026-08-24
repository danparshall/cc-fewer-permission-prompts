#!/usr/bin/env python3
"""Test cases for block_loop_with_pipe hook.

Confirms the hook fires on a bash loop whose body the matcher can't
statically analyze — a loop containing a pipe (`|`) OR a variable expansion
(`$i`, `${x}`). Both are Family-3 "cannot be statically analyzed" bails in
loop-body context (`pipeline` isolated 2026-06-05; `simple_expansion`
isolated 2026-06-06 via the headless marker-file probe). See
docs/active/chain-hook-maintenance/FINDINGS.md. The detector requires:

  loop keyword (for/while/until/select)  AND  `\\bdo\\b`
  AND  ( a lone `|`  OR  a `$var` expansion )

The `\\bdo\\b` conjunct is load-bearing and non-negotiable: without it the
detector hard-denies ordinary commands, because `for`/`while`/`until` are
common words in arguments AND `$var` is ubiquitous (`grep for x | head`,
`echo "cost $total"`). Real loops are always `for/while/until … do … done`;
`\\bdo\\b` is rare as a standalone word in normal commands and does NOT match
`sudo`, `done`, or `window`.

Two strip levels matter (a variable expands inside DOUBLE quotes but not
SINGLE quotes; a pipe/keyword is inert in BOTH):
  - loop/do/pipe checked on the BOTH-quotes-stripped string.
  - `$var` checked on the SINGLE-quote-only-stripped string, so `"row $i"`
    (expands, bails) fires but `'$i'` (literal, no bail) does not.
  - `$(` command substitution is EXCLUDED — the matcher can analyze a cmdsub
    (FINDINGS probe 03: loop+cmdsub runs silent), only a bare variable bails.

DENY cases prove the hook catches both bail shapes (incl. INTENDED
false-positives — pipe-after-loop, header cmdsub-pipe, and a variable outside
the loop body — documented as intended, not bugs; the regex-only detector
can't scope the pipe/var to the loop body).

ALLOW cases are the false-positive guards. The CRITICAL ones (loop-word +
pipe/var but no `do`; pipe/var + `do` but no loop-word; the static-body loop;
the single-quoted `$i`; and the command-substitution-not-variable case) prove
the hook is narrow enough not to tax normal commands AND that genuinely-static
loops still run silently.

Design note (deliberate deviation from plan 04's "lift strip_inert
verbatim"): this hook does NOT strip `$(...)`/backticks. Stripping `$(...)`
would (a) blank the pipe inside a header command substitution, turning the
`for f in $(ls | grep x); …` intended-FP DENY into an ALLOW, and (b) is
unnecessary because VAR_RE already excludes `$(`. Quote-stripping is split
into single-only (for `$var`) and both (for pipe/loop/do).
"""
import json
import subprocess
import sys

HOOK = "/Users/dan/code/dotfiles/claude-hooks/block_loop_with_pipe.py"

# Each case: (command, should_block, description)
CASES = [
    # ---- DENY: loop keyword + `do` + lone pipe ----
    (
        'for i in 1 2 3; do echo "$i" | cat; done',
        True,
        "classic loop+pipe (the choke shape)",
    ),
    (
        'while read l; do echo "$l" | grep x; done < f',
        True,
        "while-read loop with pipe in body",
    ),
    (
        "until grep -q done log; do tail log | head -1; sleep 5; done",
        True,
        "the wild monitor-loop shape that started this work-line",
    ),
    (
        'for f in *.txt; do cat "$f" | wc -l; done',
        True,
        "for-glob loop with pipe in body",
    ),
    (
        "select x in a b; do echo \"$x\" | tr a-z A-Z; done",
        True,
        "select loop with pipe in body",
    ),
    (
        "for i in 1 2 3; do echo hi; done | sort",
        True,
        "INTENDED FP: pipe AFTER the loop (pipes the loop's stdout); "
        "matcher behavior untested, block conservatively",
    ),
    (
        'for f in $(ls | grep x); do echo "$f"; done',
        True,
        "INTENDED FP: pipe inside a header command substitution (also has "
        "$f); blocks (conservative; matcher behavior untested)",
    ),

    # ---- DENY: loop keyword + `do` + a `$var` in the body (no pipe) ----
    (
        "for i in 1 2 3; do echo $i; done",
        True,
        "the key new case (2026-06-06): bare variable in loop body, no pipe; "
        "headless probe confirmed the matcher bails on simple_expansion",
    ),
    (
        'for i in 1 2 3; do echo "row $i"; done',
        True,
        "CRITICAL: variable inside DOUBLE quotes — DOES expand and DOES bail, "
        "so must fire (single-quote-only strip keeps it visible)",
    ),
    (
        "for f in a b c; do mv $f /dest/; done",
        True,
        "common file-loop: variable in body, no pipe",
    ),
    (
        "while read line; do echo $line; done < f",
        True,
        "while-read loop with a variable in body, no pipe",
    ),
    (
        "until [ -f $f ]; do sleep 1; done",
        True,
        "until loop referencing a variable, no pipe",
    ),
    (
        "x=$foo; for i in 1 2 3; do echo hi; done",
        True,
        "INTENDED FP: variable is OUTSIDE the loop body (the loop is static), "
        "but the regex-only detector sees loop+do+$var co-present and can't "
        "scope them. Block conservatively; cost = a cheap rewrite.",
    ),

    # ---- ALLOW: false-positive guards (CRITICAL ones marked) ----
    (
        "grep for /var/log/syslog | head",
        False,
        "CRITICAL: `for` + pipe but NO `do` — ordinary piping must not be taxed",
    ),
    (
        'echo "waiting for it" | tee log',
        False,
        "CRITICAL: `for` inside a quoted string + pipe, no `do`",
    ),
    (
        "history | grep while",
        False,
        "CRITICAL: `while` + pipe but no `do`",
    ),
    (
        "ls | grep do",
        False,
        "CRITICAL: pipe + `do` (as an argument) but no loop keyword",
    ),
    (
        "for i in 1 2 3; do echo hi; done",
        False,
        "CRITICAL: static-body loop (no pipe, no variable) → MUST run silently "
        "(headless probe command D confirmed the matcher allows it)",
    ),
    (
        "for i in 1 2 3; do echo '$i'; done",
        False,
        "CRITICAL: `$i` in SINGLE quotes is literal (no expansion, no matcher "
        "bail) → must NOT fire (single-quote strip removes it)",
    ),
    (
        'until true; do echo "M03 $(date +%s)"; done',
        False,
        "CRITICAL: command substitution `$(…)` is NOT a variable — matcher can "
        "analyze it (FINDINGS probe 03 ran silent); VAR_RE excludes `$(`",
    ),
    (
        "for i in 1 2 3; do echo $(date); done",
        False,
        "command substitution in body, no bare variable → allowed",
    ),
    (
        "echo $HOME",
        False,
        "variable but no loop keyword — top-level vars never bail",
    ),
    (
        "grep $pattern file | head",
        False,
        "CRITICAL: variable + pipe but no loop keyword and no `do` — ordinary "
        "command must not be taxed",
    ),
    (
        "ls $dir | grep do",
        False,
        "variable + pipe + `do` (as an argument) but no loop keyword",
    ),
    (
        "while false; do echo hi; done",
        False,
        "bare while loop, no pipe",
    ),
    (
        "until true; do echo hi; done",
        False,
        "bare until loop, no pipe",
    ),
    (
        "for i in 1 2 3; do a && b || c; done",
        False,
        "loop + `do` but only `||`/`&&`, no lone pipe (the `||` carve-out)",
    ),
    (
        "echo hi | cat",
        False,
        "pipe, no loop keyword",
    ),
    (
        "sudo tee /etc/x | logger",
        False,
        "`sudo` contains 'do' but `\\bdo\\b` doesn't match it; no loop keyword",
    ),
    (
        "git log --oneline | head",
        False,
        "`log` contains no loop word; pipe but no `do` — ordinary piping",
    ),
    (
        "for i in 1 2 3; do echo hi; done; ls | head",
        True,
        "INTENDED FP: bare loop then a SEPARATE pipe after `done`. The pipe "
        "is NOT in the loop body, but the regex-only detector sees all three "
        "conjuncts (loop, `do`, lone pipe) co-present and can't scope them. "
        "Block conservatively; cost = a cheap rewrite to two Bash calls.",
    ),
    (
        "echo hello",
        False,
        "plain command, no loop, no pipe",
    ),
    (
        "",
        False,
        "empty command",
    ),
]


def _blocked(cmd: str) -> bool:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run([HOOK], input=payload, capture_output=True, text=True)
    return "permissionDecision" in r.stdout and '"deny"' in r.stdout


def _non_bash_passthrough() -> bool:
    payload = json.dumps(
        {
            "tool_name": "Read",
            "tool_input": {"command": "for i in 1 2 3; do echo hi | cat; done"},
        }
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
