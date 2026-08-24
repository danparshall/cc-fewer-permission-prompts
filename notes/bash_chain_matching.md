# Bash chain matching is broken in general

> ⚠️ **PARTIALLY SUPERSEDED 2026-05-30.** The "matcher does whole-string
> prefix matching, never splits chains" claim below is no longer true.
> A HITL probe on 2026-05-30 found the matcher does *per-segment*
> checking: splits on `&&` / `|` (and probably `;`, `||`), checks each
> segment's leading verb against the allow list, allows the whole chain
> only if every segment matches. The "chain-prefix workaround" examples
> below — `Bash(cd /tmp *)` swallowing `&& <rest>` via glob — appear to
> work today because both segments are independently allowed, NOT
> because the cd-rule's glob is swallowing the chain tail.
>
> This note is kept for historical context and as a record of the
> matcher's previous behavior (or our previous understanding of it).
> Current active research line and durable findings live at:
> **`docs/active/chain-hook-maintenance/FINDINGS.md`**.
>
> The hook `claude-hooks/block_bash_chains.py` still implements the
> 2026-05-25 logic as of the supersession date — intentionally, to
> preserve the baseline Dan has been living with while we accumulate
> real-world weirdo reports.

**Status:** discovered 2026-05-25 during a session exploring why
`mkdir foo && ln -s ...` prompted despite both tools being individually
allowed. Generalizes the cd+git finding (`notes/cd_git_hardcoded.md`):
it isn't a special hardcoded heuristic, it's a general matcher
limitation.

## TL;DR

1. Claude Code's Bash permission matcher **prefix-matches the full
   command string** against allow/deny/ask rules. It does NOT split
   chains on `&&`/`||`/`;` and check each segment independently.
2. So `mkdir foo && touch bar` prompts even though `Bash(mkdir *)` and
   `Bash(touch *)` are both in ALLOW — the full string `mkdir foo && touch bar`
   doesn't prefix-match either rule.
3. The "chain prefix" patterns that **do** work — `Bash(cd /Users/dan/code *)`,
   `Bash(cd /tmp *)`, env-var prefixes like `Bash(PYTHONPATH=*)` — only
   work because their `*` glob literally swallows the `&& <rest-of-line>`
   as a single string match. It's not special chain handling, it's
   greedy glob.
4. **Implication:** you cannot make `Bash(mkdir *)` cover chains by
   moving it to a different block in `update_claude_permissions.py`.
   The rule already exists; the matcher's behavior is fixed in the
   harness. The only fix is a PreToolUse hook
   (`block_bash_chains.py`) that hard-fails chains so the habit
   actually breaks.

## Test transcript (2026-05-25)

All run on Dan's MacBook Air with the global allow list including
`Bash(mkdir *)`, `Bash(touch *)`, `Bash(ln *)`, `Bash(cp *)`,
`Bash(grep *)`, `Bash(ls *)`, etc.

| Command | Result |
|---|---|
| `mkdir /tmp/foo && ln -s /tmp/foo /tmp/bar` | **prompted** (tested twice) |
| `mkdir /tmp/foo && touch /tmp/foo/x` | **prompted** |
| `echo h > /tmp/x && mkdir /tmp/d && cp /tmp/x /tmp/d/` | **prompted** |
| `ls /tmp/*.log 2>/dev/null && touch /tmp/x` | **prompted** (contradicts old doc claim) |
| `grep -l finish /tmp/*.log; touch /tmp/x` | **prompted** (contradicts old doc claim) |

The old `~/.claude/CLAUDE.md` claimed `grep -q` and `ls path/*` worked
as chain prefixes. Empirically false — only `cd /Users/dan/code *`
and `cd /tmp *` (and env-var prefixes, untested today but believed)
actually pass through.

## The actual rule

Confirmed via [claude-code issue #29421](https://github.com/anthropics/claude-code/issues/29421)
(closed as duplicate, undocumented, not prioritized): the matcher
does full-string prefix matching with glob expansion. Chains work iff
a single allow rule's prefix+glob covers the entire command string.

`Bash(cd /tmp *)` covers `cd /tmp && <anything>` because the `*`
matches the `&& <anything>` tail as one string.
`Bash(mkdir *)` does NOT cover `mkdir foo && touch bar` because…
actually, it should by the same logic. Empirically it doesn't.
The most likely explanation is that `cd` gets special-cased somewhere
in the harness (cd is a shell builtin with no side effect on its own,
so checking the post-cd command separately is safe). That explanation
is speculative — the harness source isn't public. What is empirically
clear: only `cd <approved-path>` chains and env-var prefixes pass
through. All other chains prompt.

## What we did about it

Added `claude-hooks/block_bash_chains.py` — PreToolUse hook that
hard-fails any Bash command containing `&&`, `||`, or `;` at top
level (outside quotes/heredocs), with exemptions for:

- `cd /Users/dan/code` / `cd /tmp` prefixes (matcher accepts them)
- env-var prefixes (`FOO=bar baz ...`)
- flow control commands (`for`, `while`, `until`, `if`, `case`)
  whose semicolons are syntax, not chains
- heredocs (`<<DELIM`) whose body might contain semicolons as
  language syntax (Python, etc.)
- `cd <path> && git <subcmd>` — owned by `block_cd_git.py` for a
  more specific message

Same rationale as `block_cd_git.py`: settings rules can't deliver the
hard-fail, so a hook moves the friction from Dan (who currently
denies every prompt) to Claude (who gets a deny message and must
retry with separate Bash calls).

## See also

- `notes/cd_git_hardcoded.md` — the precedent. cd+git was originally
  framed as a "hardcoded heuristic"; this note generalizes the finding.
- `claude-hooks/block_bash_chains.py` — the hook itself.
- [claude-code issue #29421](https://github.com/anthropics/claude-code/issues/29421)
  — upstream tracking of the matcher limitation.
