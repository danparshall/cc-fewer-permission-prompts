# `python3 -c "<multiline with # comments>"` triggers path-validation prompt

**Status:** documented 2026-05-12 during a permission-prompt-reduction session ·
**Triggering event:** Dan flagged this as a frequent friction point.
Concrete example from cogel-extraction (May 2026):

```bash
python3 -c "
import csv
# (b) auth_impose_administrative_penalties_amount distribution
with open('docs/active/cogel-extraction/results/cogel_1990_table31.csv') as f:
    rows = list(csv.DictReader(f))
from collections import Counter
vals = Counter(r['auth_impose_administrative_penalties_amount'] for r in rows)
...
"
```

Claude Code prompted with:
> "Newline followed by # inside a quoted argument can hide arguments
> from path validation"

This pattern (multi-line `python -c "..."` containing Python `#`
comments) shows up constantly in research work and creates persistent
friction.

## TL;DR

**Never use `python3 -c "..."` with `#` comments inside.** Use one of three
pre-approved alternatives instead:

1. **Heredoc** (preferred for one-shot): `python3 <<'PY' ... PY` or
   `uv run python <<'PY' ... PY`. Already in the allow list. Comments are
   inside stdin, not a quoted bash argument, so the validator doesn't fire.
2. **Write tool → run file** (preferred for non-throwaway work):
   `Write(/tmp/script.py)` then `python3 /tmp/script.py`. Durable,
   debuggable, re-runnable.
3. **One-liner with `;` separators** (only for ≤3 short statements, no
   comments): `python3 -c "import csv; rows=list(csv.DictReader(open('foo.csv'))); print(len(rows))"`. Validator
   doesn't fire because no `\n#` pattern exists. Loses comments entirely.

## Why the prompt fires

The validator's threat model: command injection via newline-comment
trick. Suppose a path-restricted ALLOW like `Bash(rm /Users/dan/code *)`.
A malicious string like

```
rm /Users/dan/code/foo
# rm -rf /
```

could fool the path validator into matching only the first line while
the shell executes both. The validator scans for `\n#` inside any
quoted bash argument and prompts.

Legitimate multi-line Python with `#` comments matches the same
structural pattern (`\n#` inside a quoted arg), so it gets caught even
though `Bash(python3 *)` and `Bash(python *)` are broad ALLOWs. The
validator runs *after* allow matching and is hardcoded — settings rules
can't bypass it. Same shape as the cd+git heuristic.

## Concrete rewrites

| Wrong (prompts) | Right |
|---|---|
| `python3 -c "<br>import os<br># list files<br>print(os.listdir('.'))<br>"` | `python3 <<'PY'<br>import os<br># list files<br>print(os.listdir('.'))<br>PY` |
| `python3 -c "<br>import csv<br># load and count<br>rows = list(csv.DictReader(open('x.csv')))<br>print(len(rows))<br>"` | Write `/tmp/inspect.py`, then `python3 /tmp/inspect.py` |
| `python3 -c "print(1+1)  # quick check"` | `python3 -c "print(1+1)"` (drop the comment) |
| `python3 -c "x=1; print(x)"` | unchanged — works fine (no `#`, no newline) |

## Why this is documented but not yet DENY'd

Following the same lifecycle as the bash-loop case (see
`bash_loop_permissions.md`):

1. **Step 1 (this note):** Document the rule + the alternatives.
2. **Step 2 (observe):** See whether the agent reaches for the
   alternatives once the rule is documented. The auto-generated
   CLAUDE.md managed block surfaces this guidance at session start
   (via `ALLOW_DISPLAY_SUMMARY` in `update_claude_permissions.py`).
3. **Step 3 (escalate if needed):** If the agent keeps tripping the
   validator despite the documented rule — i.e., if this becomes
   "cd+git all over again" — add a DENY to make it a hard-fail and
   force the alternative route.

This is the right sequence because we don't yet know whether a
documented rule is sufficient. cd+git skipped step 1 (the rule was
documented but ineffectively) and went straight to DENY because the
pattern had persisted for weeks. The bash-loop case did step 1 first
(2026-05-08?) and only later added DENY (2026-05-11) when the rule
clearly wasn't sticking on its own.

If after a week or two the validator keeps firing on `python -c` with
comments, the candidate DENY patterns are documented in the convo at
`docs/active/compendium-source-extracts/convos/20260512_*` (or
revisit this note).

## Candidate DENY patterns (for future use)

Two shapes to consider when escalating:

**Surgical** (catches only the problematic form):
```python
"Bash(python -c *#*)",
"Bash(python3 -c *#*)",
"Bash(*python -c *#*)",   # uv run python -c "...#..."
"Bash(*python3 -c *#*)",
```

Catches `python -c` invocations containing `#` anywhere. Allows clean
one-liners. Open question: whether `*` in Claude Code's deny pattern
matcher spans newlines (would need to test before committing — same
as the cd+git ALLOW test).

**Blanket** (kills `python -c` entirely):
```python
"Bash(python -c *)",
"Bash(python3 -c *)",
"Bash(*python -c *)",
"Bash(*python3 -c *)",
```

Unambiguous. Forces heredoc or write-to-file even for trivial one-liners.
Higher cost, zero false negatives.

## See also

- Sibling note: `bash_loop_permissions.md` — same lifecycle
  (document the pre-approved alternatives, escalate to DENY when the
  rule isn't sticking).
- Sibling note: `cd_git_hardcoded.md` — different lifecycle
  (rule already documented for weeks, agent ignored, escalated
  directly to DENY).
