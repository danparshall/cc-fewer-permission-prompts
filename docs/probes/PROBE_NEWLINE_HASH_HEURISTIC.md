# probes/PROBE_NEWLINE_HASH_HEURISTIC.md

Regression probe for Claude Code's `\n#-inside-quoted-argument`
anti-obfuscation heuristic. Confirmed via HITL probe 2026-06-01;
documented here so future matcher updates that broaden or narrow this
heuristic show up the next time someone re-probes.

## What's being tested

Claude Code's permission matcher has an anti-obfuscation heuristic that
fires on `\n` (literal newline) followed by `#` inside a quoted argument
(`"..."` or `'...'`). The matcher names it itself in the prompt UI:
"**Newline followed by # inside a quoted argument can hide arguments
from path validation.**"

Family: sibling of the brace+quote heuristic (`"Contains brace with
quote character (expansion obfuscation)"`). Both are matcher lexical
scanners applied to quoted bodies. Both have hook-based mitigations
(`block_brace_quote_heredoc.py`, `block_newline_hash_in_quoted_arg.py`)
that hard-fail before the matcher prompts, with Write-then-run
remediation.

See `../FINDINGS.md` entry dated 2026-06-01 for the full finding.

## Protocol

Per `TEST_PLAN.md`: clean-room probe session with
`--setting-sources project` so user-level hooks (including the
`block_newline_hash_in_quoted_arg.py` hook itself) don't fire and only
the matcher's raw behavior is observed.

```
cd /Users/dan/code/dotfiles/docs/active/chain-hook-maintenance/probes
claude --setting-sources project
```

For each probe:
1. Paste the User message into the probe Claude.
2. Watch the Bash tool call. Either:
   - A **permission prompt** appears → `PROMPT` (heuristic fired).
   - Tool **runs cleanly** (prints the probe marker) → `ALLOW` (heuristic
     did not fire).

## Probes

### Probe A — control (newline but no `#` after)

**User message:** Run `python3 -c "print('probe_a_no_hash')\nprint('probe_a_line2')"` and show me the output.

**Expected:** `ALLOW`. The body has a literal newline but the line after
the newline does NOT start with `#`, so the heuristic doesn't fire.
`Bash(python3 *)` is allowed; the matcher should let it through silently.

**Confirmed 2026-06-01:** ✅ ALLOW (printed both lines, no prompt)

### Probe B — trigger (newline followed by `#`)

**User message:** Run `python3 -c "print('probe_b_with_hash')\n# probe_b_python_comment"` and show me the output.

**Expected:** `PROMPT`. The body contains `\n#` inside the double-quoted
`-c` argument. The heuristic should fire and the matcher should prompt
Dan with the named diagnostic, despite `Bash(python3 *)` being allowed.

**Confirmed 2026-06-01:** ✅ PROMPT (matcher diagnostic: "Newline followed
by # inside a quoted argument can hide arguments from path validation")

## Discriminator significance

Probes A and B differ only in whether the line after the newline starts
with `#`. Both use double-quoted `-c` bodies. Both have `Bash(python3 *)`
covering them. The single-character difference is the discriminator.

This rules out competing hypotheses that were live at probe time:

| Hypothesis | Outcome of probe |
|---|---|
| Stderr redirection breaks the glob match | Falsified (separate probes; `find ... 2>/dev/null` from `/tmp` runs clean) |
| `.env*` pattern is a secrets heuristic | Falsified (separate probes; `find /tmp -name .env.<CLIENT>` runs clean) |
| Multi-line bodies always trigger | Falsified by Probe A (multi-line, no prompt) |
| `\n#` anywhere triggers | Need extension: confirmed for inside-quotes; for outside-quotes see Probe C below |

### Probe C — boundary (`\n#` OUTSIDE any quoted region)

**User message:** Run this command exactly: `echo hi\n# regular bash comment`

(Where `\n` is a literal newline in the command, not the two-character
escape sequence.)

**Expected:** Behavior unclear. The matcher's diagnostic says "inside a
quoted argument," suggesting the heuristic is scoped to inside-quotes.
A clean ALLOW here would confirm that scope. A PROMPT here would mean
the heuristic is broader than the diagnostic claims.

**Not yet probed 2026-06-01.** Future probe candidate.

## Related hook

`~/code/dotfiles/claude-hooks/block_newline_hash_in_quoted_arg.py`
hard-fails Probe B before the matcher prompts, so in a normal session
(not `--setting-sources project`) Probe B's behavior is **hook deny
with nastygram**, not matcher prompt. To observe the raw matcher
behavior, use the clean-room protocol above.

## Cross-references

- `../FINDINGS.md` (entry 2026-06-01) — empirical finding + heuristic
  family table
- `../STRATEGIES.md` — Write-then-run as the recommended workaround
- `../INCOMING.md` — original weirdo report that led to this probe
- `notes/cd_git_hardcoded.md` — sibling case for the hook-vs-matcher-
  heuristic architectural pattern
