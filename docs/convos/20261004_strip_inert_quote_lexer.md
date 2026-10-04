# 20261004_strip_inert_quote_lexer

**Date:** 2026-10-04
**Branch:** main (main-direct work-line)
**Surface:** claude-code
**Machine:** Dans-MacBook-Air
**Session:** Dan (air, dotfiles, 20261004T1751, opus-5.5) · ~/.claude/projects/-Users-dan-code-dotfiles/d27b929c-6d58-4a25-a0c5-d6185bbf1d98.jsonl · —

## Summary

The session started from a handoff: fix `block_bash_chains.py`'s `strip_inert()` so quoted spans are blanked in one left-to-right pass that tracks shell quote state, using INCOMING entries 2026-07-24, 2026-09-22 and 2026-10-04. The old code ran separate regex passes, single quotes first and then double quotes. So an apostrophe inside a double-quoted commit message could pair with a later single quote, eat the message's closing `"`, and leak a quoted `;` or `&&` into the chain split. That produced phantom segments and a DENY.

`strip_inert` is now a small lexer: whichever quote opens first owns the span; `\"` inside `"…"` doesn't close it; `$(…)` nested in `"…"` gets its own quote tracking (the per-commit codename template depends on this); backticks are handled; `\;` outside quotes is literal; and an unterminated quote is left unblanked, so it can't hide a real chain. Commit `10f100d`.

At Dan's request, the same session also ported the fix to `block_loop_with_pipe.py`. Both of its strip levels (both-quotes and single-only) had the same flaw. Commit `bcaa061`.

## Topics Explored
- Probed the old `strip_inert` against candidate commands before writing tests, to find out which shapes actually leak.
- Wrote TDD cases for both hooks through the real subprocess hook contract.
- Checked the handoff's claimed precedent, `block_loop_with_pipe.py`. It had the same flaw, so it was a precedent for the two strip levels, not for the lexer.

## Provisional Findings
- **The old code didn't leak on a lone apostrophe.** `git commit -m "it's fixed; done"` passed. The leak needed a `'` *after* the message's closing `"` (09-22's `--format='…'`), or a `\"` inside the message. The 10-04 INCOMING analysis ("overwhelmingly likely" apostrophe path) was therefore too strong. The 10-04 trigger is unconfirmed because the command wasn't captured.
- A reconstruction of the 07-24 multi-line message also passed under the old code. That body is elided in INCOMING, so its exact trigger is likewise unconfirmed. It's kept as a pin test.
- The fix covers every leak shape that is known to occur. If a quoted-`;` DENY recurs after this, it's a different mechanism, and the exact command needs capturing.

## Decisions Made
- `block_bash_chains.py`: the lexer blanks `$(…)` and backticks (same as before, now nesting-aware).
- `block_loop_with_pipe.py`: a quote-only lexer (`_strip_quotes(cmd, keep_double)`). It deliberately does NOT blank `$(…)`, because that hook scans command substitutions for `$var` on purpose. The two lexers are kept separate rather than shared: the semantics differ, and the hooks are standalone symlinked files.
- An unterminated quote is left as-is in both hooks. This is conservative: it never hides an operator.
- Tests: `TestQuoteStateTracking` (12 cases, 6 RED before the fix) and 4 new loop-hook cases (3 RED before). Full pre-commit list: 965 green on Air. Not yet exercised on Pro or tarragon. The hooks are pure Python with no machine-specific paths, so I expect no divergence there.
- INCOMING 2026-10-04 and 2026-09-22 are marked FIXED, with the corrected mechanism recorded.
- Created this work-line's `RESEARCH_LOG.md`. Earlier sessions were logged in STATUS.md under the older convention.

## Results
- Code only: commits `10f100d`, `bcaa061`.

## Open Questions
- The 07-24 and 10-04 triggers are unconfirmed (see above). If either shape recurs, capture the exact command.
- Self-inflicted, not a hook issue: in this session I wrote `$(...)` inside a double-quoted `git commit -m`, and zsh executed it. Use `-F <file>` for commit messages that mention shell syntax.
