# STRATEGIES.md

How we respond to a prompted command Dan thinks shouldn't have prompted, once the cause is understood from `INCOMING.md` analysis. Two-approach framework.

## The two strategies

### Strategy 1 — Add an Allow permission

**When to use:** The prompt fired because **no allow rule matched** what the matcher was looking at. Adding a rule (or a more specific rule) lets the matcher pass it.

**How:**
- Edit `update_claude_permissions.py` `ALLOW_RULES` (or `ADDITIONAL_DIRECTORIES`, or the tool-specific rules at `Read(...)` / `Write(...)` / `Edit(...)`).
- Run `pytest tests/test_sync_to_basic_config.py tests/test_update_claude_permissions.py` — both must pass.
- Apply to live settings: `bash install.sh` (idempotent, runs `update_claude_permissions.py` to merge new rules into `~/.claude/settings.json`).

**Tradeoffs:**
- ✅ Minimal code change — one or two lines.
- ✅ Lives in the rules system; integrates with Claude Code's normal flow.
- ✅ Self-documenting via the rule itself (subject to the comment you add).
- ❌ Doesn't always work — many prompts are NOT "no rule matched" but rather Claude Code's own heuristic checks (anti-obfuscation, `\n#` detection, etc.) that fire regardless of allow rules.
- ❌ Can become a sprawl problem if you add too many narrow rules — each new rule is one more thing that might drift or conflict with future matcher updates.

**Example (resolved this way):** the `cd /Users/dan/code/<subpath>` weirdo. Original rule `Bash(cd /Users/dan/code *)` requires a space then content. Subpath cd's have a slash. Added `Bash(cd /Users/dan/code/*)` adjacent. Done.

### Strategy 2 — Add our own Deny rule (PreToolUse hook with nastygram)

**When to use:** The matcher has its own heuristic that fires regardless of allow rules — typical for "this command looks dangerous / suspicious" detectors like:
- Brace-with-quote ("expansion obfuscation")
- `\n#` patterns in `-c` quoted bodies
- `find -delete`, `eval`, other already-deny-listed patterns
- Any case where no allow rule could possibly help

Our hook intercepts BEFORE the matcher runs, returns an explicit deny, and includes a useful message Claude can act on (typically: "use this alternate pattern instead").

**How:**
- Write a new hook in `claude-hooks/<name>.py` (model: `block_bash_chains.py`, `block_cd_git.py`).
- **`chmod +x claude-hooks/<name>.py` immediately after creation.** Claude Code invokes hooks as `"type": "command"` and the kernel checks the +x bit on the resolved source file — missing +x is a silent failure where the hook never fires and the normal permission flow takes over with no error visible. `install.sh` does a defensive chmod loop and `test_hooks_executable.py` is a second line of defense, but neither catches a brand-new hook that hasn't been committed yet. See FINDINGS 2026-05-31 for the diagnostic story.
- The hook reads the tool input, detects the offending pattern (regex over the command string), and returns `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "<nastygram>"}}`.
- Register the hook in `update_claude_permissions.py` via an `ensure_<name>_hook()` function (model: `ensure_block_cd_git_hook`, `ensure_block_bash_chains_hook`). This makes the hook survive `sks switch` clobbering of `settings.json`.
- Add the hook's path to `install.sh`'s symlink list so `~/.claude/hooks/<name>.py` points at `claude-hooks/<name>.py`.
- Run the test suite (`pytest tests/test_sync_to_basic_config.py tests/test_update_claude_permissions.py claude-hooks/test_hooks_executable.py`). Add a characterization test for the new `ensure_*_hook()` function. `test_hooks_executable.py` will auto-cover the new hook with no edits.
- **Verify in a fresh Claude session** that the hook actually fires on a triggering command — registration + symlink + +x all correct *and* the deny-JSON nastygram appearing in the tool result. Without this end-to-end verification, you've only confirmed the plumbing, not the behavior.

**Tradeoffs:**
- ✅ Full control over the deny message — you can give Claude a concrete remedy ("Use Write+run instead: `Write(/tmp/script.py)` then `python3 /tmp/script.py`").
- ✅ Pedagogically trains Claude (the model) to use the better pattern, since the deny message is specific and actionable.
- ✅ Fires before the matcher, so it's predictable even when the matcher itself shifts under us.
- ❌ More code: a new hook script + ensure function + tests + install.sh wiring.
- ❌ More maintenance: the regex that detects the offending pattern can over- or under-fire. Real-world misfires need their own INCOMING.md flow.
- ❌ Risks compounding: if you deny too aggressively, you create a hook-stack that itself prompts Dan more than the matcher would have.

**Example (planned this way):** the brace-quote anti-obfuscation prompt. The matcher will fire on any `{"x":"y"}` literal regardless of allow rules — Strategy 1 cannot help. The hook (TBD: `block_brace_quote_obfuscation_prompts.py` or similar) detects brace+quote in the command string and denies with: "This will trip Claude Code's anti-obfuscation heuristic. Use `Write(/tmp/script.py)` then `python3 /tmp/script.py` instead — see chain-hook-maintenance/INCOMING.md."

## Write-then-run as the default for non-trivial Python / jq / etc.

For multi-statement Python (or jq, awk, perl — any embedded code), default to:

```python
Write('/tmp/script.py', '<source>')
# then in a separate Bash call:
python3 /tmp/script.py
```

This pattern sidesteps **three distinct named matcher anti-obfuscation heuristics**, plus the semicolon-tokenization-inside-quoted-body bug, all of which fire on code embedded in `-c "..."` or `<<'PY'` heredocs:

1. **Brace-with-quote (`{"x":"y"}`, `["a","b"]`) → "Contains brace with quote character (expansion obfuscation)"** — fires on any bash-unquoted brace+quote, including heredoc bodies. Common in pandas, JSON construction, dict literals. Handled at the heredoc layer by `block_brace_quote_heredoc.py`; `-c` quoted bodies still rely on Write-then-run as workaround.
2. **`\n#`-in-quoted-arg → "Newline followed by # inside a quoted argument can hide arguments from path validation"** — fires on a Python (or other-language) source comment inside `-c "..."`. Confirmed by direct heuristic-name surfacing 2026-06-01. Workaround: Write-then-run. No hook currently.
3. **Semicolon tokenization inside quoted `-c` body** — matcher splits naively on `;` regardless of shell quoting, so `python3 -c "a; b; c"` becomes four phantom segments, three of which have no allow rule. Workaround: Write-then-run.
4. **Heredoc + pipe/redirect → "Contains shell syntax (file_redirect)/(pipeline) that cannot be statically analyzed"** (Family 3, FINDINGS 2026-06-05) — a `<<` heredoc *co-occurring* with a pipeline (`| grep …`) or an extra redirect (`2>&1`, `> out`) makes the whole command unanalyzable to the matcher → prompt. NOTE this one is **structural, not about the heredoc body's content** (unlike #1) — even a brace-quote-clean heredoc trips it once you pipe or redirect it. The canonical example is `uv run python - <<'PY' … PY 2>&1 | grep …`. **Now hard-failed by `block_heredoc_with_pipe_or_redirect.py` (Strategy 2, added 2026-06-05)** — the hook detects a pipe/redirect on the heredoc's command (open) line and denies with a Write-then-run nastygram; plain heredocs and heredoc bodies containing `|`/`>`/`<` are left untouched. Write-then-run dodges it by **removing the heredoc**, and — importantly — the file-based command may **keep its `2>&1 | grep …` tail** (a redirect/pipe without a heredoc is silent; verified). So `uv run python /tmp/script.py 2>&1 | grep -v VIRTUAL_ENV` runs clean.
5. **Brace expansion → "Brace expansion"** (Family 3 row #2, FINDINGS 2026-06-05) — `{a,b}`, `{1,2,3}`, `{1..5}`, `{a..z}`, multi-group cross-products like `{a,b}__run{1,2,3}.json` in unquoted shell-argument position trip the matcher's static-analysis bail. The matcher can detect the brace-expansion AST node (tree-sitter-bash) but cannot statically enumerate the runtime-determined set of paths, so it bails. **Verb-agnostic** — `ls /tmp/{a,b}` triggers identically to `mv /tmp/{a,b} /dest/`; allow rules don't help. **Now hard-failed by `block_brace_expansion.py` (Strategy 2, added 2026-06-05)** — regex `(?<!\$)\{[^{}\s]*(?:,|\.\.)[^{}\s]*\}` after stripping heredoc bodies and quoted/substituted regions. False-positive guards for bash code blocks (`{ cmd; }`), parameter expansion (`${VAR:-default,foo}`), find placeholders (`{}`), and Python set/dict literals in heredoc bodies. **Workaround is SEPARATE Bash calls, not Write-then-run** — `mv /p/{a,b}.txt /dest/` becomes two `mv` calls (one per expanded path); cwd persists across calls. Common-prefix glob (`mv /p/*.txt /dest/`) works when applicable. Cross-product brace expansions with no shared prefix (the wild-prompt's 2×3 case) genuinely benefit from a Write-then-run shell script as the one Bash call.
6. **`.py` path as leading verb (allow-rule miss, NOT a matcher heuristic)** — `/Users/.../foo.py`, `./foo.py`, or `subdir/script.py arg` in leading-verb position has no matching allow rule (`Bash(python *)` / `Bash(python3 *)` cover the interpreter when it's the verb, not the path). **Epistemically distinct from items #1–#5 above:** those close matcher heuristics (Family 1/3 static-analysis bails) that allow rules CANNOT override; this one closes a plain allow-rule MISS that Strategy 1 (`Bash(/Users/.../*.py *)`) could in principle have closed. **Dan chose Strategy 2 deliberately** to train the canonical `python3 <path>` interpreter-leading form rather than expand the allow surface — same training-pressure rationale as the chain hook's mixed-chain hard-fail. **Now hard-failed by `block_absolute_path_py_verb.py` (Strategy 2, added 2026-06-05)** — regex `^\s*['"]?\S*/\S*\.py['"]?(?:\s|$)` anchored at command start; the required `/` distinguishes a path from a bare-verb `foo.py` (out of scope). No `strip_inert` helper — the anchor + boundary already prevent the cases strip would defensively cover, and stripping would break leading-quote DENY cases. **Workaround is the canonical interpreter-leading form** — `/Users/dan/foo.py 2>&1 | tail -3` becomes `python3 /Users/dan/foo.py 2>&1 | tail -3`; the `2>&1 | tail` (or any other) tail can be kept verbatim. Strategy-1 fallback (a path-allow-rule) remains viable if the training-pressure judgment ever changes.

7. **Loop with a pipe OR a `$variable` in its body → "Contains shell syntax (pipeline)/(simple_expansion) that cannot be statically analyzed"** (Family 3, loop-context; `pipeline` FINDINGS 2026-06-05, `simple_expansion` FINDINGS 2026-06-06). The matcher *body-analyzes* a loop and silently auto-approves it ONLY when every effect is statically boundable — so a bare static loop (`for i in 1 2 3; do echo hi; done`) runs silent with no allow rule. But a **pipe** or a **bare variable expansion** in the body is unboundable and bails. A **command substitution `$(…)` does NOT bail** (the matcher recurses into it; probe 03). Since nearly every useful loop references its loop variable, this fires on essentially every real loop. **Now hard-failed by `block_loop_with_pipe.py` (Strategy 2, added 2026-06-05, extended to variables 2026-06-06; replaced the blunt `Bash(for *)`/`Bash(while *)` DENYs — plan 04).** Detector: fire iff `LOOP_RE (for|while|until|select) AND \bdo\b AND (lone | OR $var)`, with two strip levels — pipe/loop/do checked on both-quotes-stripped, `$var` on single-quote-only-stripped (a variable expands in `"…"` but not `'…'`); `VAR_RE` excludes `$(`. The **`\bdo\b` conjunct is load-bearing** — without it the detector would tax ordinary commands that merely contain a loop-word and a `$var` (`echo "cost $total"`, `grep for x | head`). **Workaround is NOT Write-then-run-keeping-the-loop** — it's eliminate the loop: do the work in one `uv run python <script>`, unroll to separate Bash calls (one per item; cwd persists), or use the **Monitor tool** for wait-until-condition loops. (Filename keeps the historical "with_pipe" — it now covers variables too; see the hook docstring.) **Methodology note:** the variable bail was isolated with a new technique worth reusing — a fresh **headless `claude -p` session attempting marker-file-writing commands**: a silently-allowed command creates its marker, a prompt-requiring one is auto-denied in headless and leaves no marker. This lets a session *observe* the matcher's allow-vs-ask decision without needing Dan as the HITL instrument (the marker file is ground truth, independent of what the sub-agent reports).

The unified payoff of Write-then-run: the bash command becomes the trivial `python3 /tmp/script.py`, which the matcher cleanly accepts via `Bash(python3 *)`; the code lives in a file rather than a quoted argument, so no anti-obfuscation scan applies. The Write tool's `Write(//tmp/**)` rule blanket-allows the file creation.

## Strategy 0 — No action (do nothing)

Sometimes a prompt is fine and not worth automating around. Examples:
- One-time use of an unusual command — the prompt is the right friction.
- Cases where the user genuinely should pause to consider (e.g. `rm -rf /Users/dan/somewhere`).
- Edge cases that fire rarely.

When you decide on Strategy 0, write the decision in the `INCOMING.md` entry's resolution note so future-you doesn't re-debate.

## Picking between strategies — quick decision tree

1. Does an allow rule (or rule pattern) exist that would have prevented this prompt?
   - YES → **Strategy 1**.
   - NO → continue.
2. Is the matcher firing on a hardcoded heuristic (not a missing rule)?
   - YES → **Strategy 2** (deny hook).
   - NO → reconsider — maybe Strategy 1 works after all with a different rule format.
3. Is the prompt fine, just annoying once or twice?
   - YES → **Strategy 0** (do nothing).
4. Mixed (e.g. a chain where one segment is a missing-rule problem AND another segment trips a heuristic)?
   - Strategy 1 for the missing-rule part, Strategy 2 for the heuristic part. Both can stack.

## Things to ALWAYS do regardless of strategy

- Capture the original prompt + diagnostic message verbatim in INCOMING.md before fixing.
- After fixing, move the INCOMING entry to "Triaged" with a resolution note.
- If the fix produced a durable lesson (e.g. "the matcher tokenizes on `;` inside quoted strings"), append it to FINDINGS.md.
- Update `probes/TEST_PLAN.md` if the weirdo revealed a hypothesis worth probing in a controlled session (e.g. "does `pwd` bare-arg-less match `Bash(pwd *)`?").

## Anti-patterns

- **Don't redesign the chain-block hook on a single weirdo.** Per the work-line's design, redesign waits for an accumulated corpus.
- **Don't edit `update_claude_permissions.py` user-facing displays (`ALLOW_DISPLAY_SUMMARY`, `DENY_DISPLAY`) with specific claims about matcher behavior.** Those subsections now point to this folder as SSOT; keep the SSOT here.
- **Don't add hook logic that REPLICATES matcher behavior** ("if the matcher would prompt, I'll deny first"). That requires the hook to track matcher behavior, which is unstable. Hooks are for cases where the matcher's behavior is the problem, not for mimicry.
