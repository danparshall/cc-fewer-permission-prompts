# probes/TEST_PLAN_loop_reenable.md

Probe + gated implementation plan for **re-enabling broad bash loops** by pre-empting the one shape the matcher chokes on (a pipe inside a loop).

**Origin:** FINDINGS.md 2026-06-05 (loop-context row) — HITL probing of `until` showed the matcher prompts on *exactly one* loop shape: a pipeline inside the loop body. Bare loops, loop+command-sub, and loop+redirect are all silent. Dan's inversion (2026-06-05): instead of denying loops wholesale, **deny `loop + pipe`** (the choke shape) and **re-enable loops broadly** — every remaining (pipe-free) loop is then matcher-safe and prompt-free.

**Status:** ✅ PROBE GREEN (2026-06-05) — F1/F3 came back `ALLOW` (silent), F2/F4/F5 `PROMPT`; for/while confirmed to match `until`. Implementation below is now **unblocked** (not yet shipped). See FINDINGS.md 2026-06-05 "(latest)" entry.

---

## Why this probe is necessary

We have empirical data on the matcher's native loop behavior for **`until` only**. `for`/`while` have been hard-denied by our own `Bash(for *)` / `Bash(while *)` DENY rules this entire time, so the matcher has *never been observed* deciding a bare `for`/`while` loop. Dan's plan assumes for/while behave like `until` (matcher body-analyzes, auto-approves pipe-free, bails on pipe). That's plausible — `for`/`while`/`until` are the same `do…done` structure — but **unconfirmed**, and the matcher has surprised us with per-shape special-casing before (the entire reason this work-line exists).

The risk being checked protects **Dan**, not Claude: if we remove the for/while deny and the matcher turns out to *prompt* on bare `for`/`while`, Dan eats a prompt on every loop. No amount of detector-FP-tolerance fixes that — it's the deny removal that's load-bearing.

Mechanism evidence that makes the plan plausible: probe 01 (`until true; do echo X; done`) was **silent despite no `Bash(until *)` allow rule existing**. So the matcher isn't matching a loop-keyword rule — it looks *inside* the body, sees `echo` is allowed, and approves. F5 below confirms that mechanism for `for`.

---

## Protocol

```
cd /Users/dan/code/dotfiles/docs/active/chain-hook-maintenance/probes
claude --setting-sources project
```

`--setting-sources project` loads ONLY this directory's `.claude/settings.json` — skips user-level hooks (so `block_bash_chains.py` doesn't interfere) and user-level allow/deny rules (so the production for/while DENY is absent and native matcher behavior is observable). Auth is unaffected.

**Settings requirement (already set):** the probe `.claude/settings.json` must have `Bash(echo *)` and `Bash(head *)` present (loop bodies / pipe tails) and **must NOT** contain `Bash(for *)`, `Bash(while *)`, or `Bash(until *)` (those would mask native behavior). This was fixed 2026-06-05 — `Bash(for *)` removed. Verify before running.

For each row: paste the **User message**, watch the single Bash call, mark `PROMPT` (then deny it) or `ALLOW` (runs — success or "command not found" both count as ALLOW). If the probe Claude does anything other than the one Bash call, abort and note it.

---

## Probe matrix (mirrors the `until` matrix from FINDINGS 2026-06-05)

`M_FN` markers have no allow rule — an ALLOW verdict can only come from the matcher's loop/body handling, never from a marker rule.

| # | User message (paste verbatim after "run this exact command once and stop:") | Expected | Result |
|---|---|---|---|
| F1 | `for i in 1 2 3; do echo M_F1; done` | **ALLOW** (body-analysis: `echo` allowed → loop approved, like `until` probe 01) | **ALLOW** ✓ (silent, 2026-06-05) |
| F2 | `for i in 1 2 3; do echo M_F2 \| cat; done` | **PROMPT** (pipe in loop body → Family-3 bail) | **PROMPT** ✓ (tail `cat`, not `head -1`) |
| F3 | `while false; do echo M_F3; done` | **ALLOW** (bare while, body-analysis) | **ALLOW** ✓ (silent) |
| F4 | `while false; do echo M_F4 \| cat; done` | **PROMPT** (pipe in loop body) | **PROMPT** ✓ |
| F5 | `for i in 1 2 3; do rev <<< M_F5; done` | **PROMPT** (body verb has no rule → confirms matcher gates on the body verb, i.e. it really is body-analysis, not blanket loop-allow) | **PROMPT** ✓ (verb `rev` + `<<<`) |

(Pipe tail `head -1` uses an allow-listed verb so an ALLOW on F2/F4 couldn't be blamed on an unknown tail verb. The loop+pipe bail is structural/segment-agnostic regardless, per FINDINGS probe 02.)

---

## Interpreting the result

- **GREEN (F1 ALLOW, F3 ALLOW, F2 PROMPT, F4 PROMPT, F5 PROMPT):** for/while behave exactly like `until`. Dan's inversion is validated. Proceed to Implementation below. Write a FINDINGS.md entry recording the confirmed for/while native behavior.
- **F1 or F3 PROMPT:** the matcher prompts on bare for/while (unlike until). The inversion would *reintroduce* prompts for Dan → **do not remove the deny.** Write a FINDINGS entry; reconsider (maybe allow only `until`, or add explicit `Bash(for *)`/`Bash(while *)` *allow* rules and test whether those make pipe-free loops silent — a different plan).
- **F5 ALLOW (with F1 ALLOW):** matcher allows loops regardless of body verb (not body-analysis — some broader loop fast-path). Inversion still works (loops usable), but record the corrected mechanism; the `block_loop_with_pipe.py` deny is still the right pipe-guard.
- **Any row unrunnable** (probe Claude refuses to issue the command): note as an investigation gap in FINDINGS.md; fall back to Dan pasting the command directly.

---

## Implementation (GATED — only after a GREEN probe)

> **➡️ CANONICAL PLAN: `../plans/04_block_loop_with_pipe.md`.** Probe is GREEN; the full TDD plan now lives there. The sketch below is **superseded** — in particular its detector spec is **WRONG** (the naive `LOOP_RE + PIPE_RE` would hard-deny normal piping like `grep for /var/log | head`). Plan 04 adds the required **`do` conjunct** to fix that. Implement from Plan 04, not from this sketch.

The detector can be **dumb but not blind** (Dan, 2026-06-05): a high false-positive rate is fine *on loop-shaped commands* (an FP costs only a Claude *rewrite*), whereas a false *negative* costs Dan a matcher prompt. But the naive spec below over-fires on ordinary pipes — see Plan 04's Design boundary for the `do`-conjunct fix.

1. **`claude-hooks/block_loop_with_pipe.py`** (PreToolUse, Strategy-2 sibling of `block_brace_expansion.py`):
   - Fire when `LOOP_RE.search(cmd) and PIPE_RE.search(cmd)` where
     `LOOP_RE = re.compile(r'\b(for|while|until|select)\b')` and
     `PIPE_RE = re.compile(r'(?<!\|)\|(?!\|)')` (a lone `|`, excluding `||`).
   - **Only carve-out:** `||` (the `for …; do a || b; done` fallback idiom is common and isn't a pipeline). No tree-sitter, no "pipe must be inside do…done" check, no quote-stripping — let everything else over-fire.
   - Nastygram: *"A pipe inside a loop trips the Claude Code matcher (it prompts Dan). Rewrite without a pipe in the loop — use `uv run python`, a temp variable, separate Bash calls, or the Monitor tool for wait-loops."*
   - Reuse the json-stdin / `sys.path.insert` / exit-code boilerplate from a sibling hook.
2. **`test_block_loop_with_pipe.py`** — block: `for/while/until + | `; pass: bare loop, `||` in loop, pipe with no loop, plain allowed command. Document the accepted FPs (quoted `|` in a loop, `case a|b)` in a loop) as *intended* deny cases, not bugs.
3. **`update_claude_permissions.py`:**
   - Remove `Bash(for *)` and `Bash(while *)` from `DENY_RULES` (and the reframed comment block above them).
   - Add `ensure_block_loop_with_pipe_hook()` (mirror `ensure_block_brace_expansion_hook()`), call it in the self-heal sequence.
   - Update `DENY_DISPLAY` / condensed CLAUDE.md list: replace the for/while-loops line with a "loop + pipe (enforced by `block_loop_with_pipe.py`)" line; note bare loops are now allowed.
4. **`install.sh`** — add the symlink line for `block_loop_with_pipe.py`.
5. **Tests:** `pytest test_update_claude_permissions.py test_hooks_executable.py test_block_loop_with_pipe.py` — all green.
6. **Live fire-test** (this/a normal session, after `install.sh`):
   - `for i in 1 2 3; do echo hi | cat; done` → hard-deny nastygram. ✓
   - `for i in 1 2 3; do echo hi; done` → runs silently (matcher allows). ✓
7. **Docs:** FINDINGS.md entry (confirmed for/while behavior + the shipped hook); STRATEGIES.md item; update the `notes/bash_loop_permissions.md` banner status ("deny removed, replaced by loop+pipe hook"); update the CLAUDE.md managed-block deny list (regenerated by the script).
8. **Commit + push.**
