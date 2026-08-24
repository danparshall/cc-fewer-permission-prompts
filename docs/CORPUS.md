# Chain-hook maintenance

**Work-line type:** main-direct (no dedicated branch). Long-running.

## What this folder is

**The thesis.** A permission prompt is a tax Dan pays in approvals — and because Dan runs many Claude sessions in parallel, every prompt *serializes one of them*. So when a prompt fires on a command **format** that has a clean, already-documented correct alternative, we convert it into a hard **DENY** that fires **before** the matcher. The friction then moves from Dan (who would otherwise re-approve the same shape dozens of times a session) onto Claude: the deny returns a nastygram reminding Claude of the alternative it *already knows*, and Claude reformulates. The earlier CLAUDE.md "please don't do X" approach failed precisely because Claude ignored it and left the approvals on Dan; a DENY puts the burden back where the already-documented-correct-behavior says it belongs.

**The gate is a conjunction, not either half.** We deny-hook a format only when it is **both** (a) frequent **and** (b) backed by a clean, already-documented alternative. Dan's words: he minds approving *"often, for things which already have a clean alternative"* — that intersection is the whole target. Either half alone is **not** a deny:
- **No clean alternative** (even if frequent) → legitimate friction; Dan will approve it, repeatedly if need be — that's the matcher doing its job, and a deny would have nowhere to send Claude.
- **Clean alternative but rare** → **Strategy 0**, not worth a hook.

So "clean alternative" is *necessary but not sufficient* — **frequency is what flips a Strategy-0 into a Strategy-2.** (Example: the `find` path-operand glob already has its clean alternative — `-name` — so it sits at Strategy 0 purely waiting on the frequency half; see its INCOMING entry.)

Chains were the first instance and the namesake — `claude-hooks/block_bash_chains.py` (and the closely related `block_cd_git.py`) hard-fail Bash chains (`&&`, `||`, `;`) the matcher would have prompted on. But the work-line has **outgrown its name**: it now covers the whole family of matcher prompts (brace-quote, `\n#`-in-quoted-body, `file_redirect`/heredoc-with-pipe, path-aware heuristics, backslash-escaped whitespace, `find` path-operand globs, …), most of which aren't chains at all. The response framework for every one of them is the three strategies in `STRATEGIES.md` (Strategy 1 allow-rule / Strategy 2 deny-hook / Strategy 0 leave-it).

The problem that makes this a *standing* work-line rather than a one-time fix: **Anthropic keeps changing the permission matcher's behavior**, so any hook's assumptions go stale. Today's empirically-correct hook becomes tomorrow's over-blocker. The original durable note (`notes/bash_chain_matching.md`, dated 2026-05-25) was already partially wrong after 5 days — see `FINDINGS.md`. This folder turns hook maintenance into an explicit, evidence-driven loop instead of a hope-the-note-is-still-true situation.

## Files

| File | Purpose |
|---|---|
| `README.md` | This. |
| `METHODOLOGY.md` | How we probe matcher behavior (two modes, HITL conventions, pre-flight load-proof). Replicate this when re-probing. |
| `FINDINGS.md` | Dated entries: probe results, hypotheses, what the matcher does at that point in time. Append-only; new findings go on top. |
| `STRATEGIES.md` | The response framework: Strategy 1 (allow rule) / Strategy 2 (deny hook) / Strategy 0 (leave it), plus the catalog of known clean alternatives (Write-then-run, `git -C`, etc.). |
| `INCOMING.md` | Paste-target for real-world weirdos ("got prompted on X but I didn't think I should have"). Triage / curate; resolved entries get annotated or moved to the Triaged section, durable lessons go to FINDINGS.md. |
| `probes/.claude/settings.json` | Controlled per-project settings for clean-room probe sessions (`claude --setting-sources project` launched from `probes/`). No hooks; tightly-scoped allow rules; a `Bash(rev *)` deny-canary for load-proof; `/tmp` in `additionalDirectories` (both documented in-file). |
| `probes/TEST_PLAN.md` | The runnable probe plan. Refined whenever we learn the matcher does something new. |
| `probes/REPROBE_*.md`, `probes/RESULTS_*.md`, `probes/SESSION_*.md` | Per-run runbooks, results, and session logs — the historical record of each probe pass, including the failed ones (the failures taught the pre-flight discipline). |

## Workflow

### When Dan gets an unexpected prompt

1. Dan pastes the prompted command into `INCOMING.md` (or hands to the `chain-matcher-curator` agent — see `.claude/agents/chain-matcher-curator.md`).
2. The curator agent (or any Claude session) records:
   - Exact command that triggered the prompt
   - Which segments matched which allow rules (best-effort analysis)
   - Snapshot of current `~/.claude/settings.json` permissions (or relevant subset)
   - Current state of `block_bash_chains.py` (revision hash if useful)
   - Hypothesis about *why* it prompted
3. Entry goes in `INCOMING.md` with a date.

### When enough weirdos accumulate (Dan's judgment)

1. Review `INCOMING.md` entries.
2. Look for patterns — is the matcher doing X now? Has a rule format stopped matching?
3. Re-run the probe (`probes/TEST_PLAN.md`) to confirm hypotheses against current matcher.
4. Update `block_bash_chains.py` if needed.
5. Move `INCOMING.md` entries that informed the update into `FINDINGS.md` (dated and explained).

### When we close this work-line

This is a long-running line. It doesn't get "completed" the way a feature does. Archive only if you decide the hook is permanently retired (e.g. matcher behavior stabilizes, or the hook is deleted in favor of a different mitigation).

## Portability — reusing this corpus outside this repo

This folder is being prepared for a standalone open-source spinoff. What travels and what doesn't:

**Portable as-is:**
- The thesis and strategy framework (this README, `STRATEGIES.md`) — nothing in them is user-specific beyond the examples.
- `METHODOLOGY.md` — the probe protocol (Mode A/B, deny-canary load-proof, paste-shape diagnostics, deviation-triggered sandbox attribution) works for any Claude Code user. HITL is inherent: the matcher's prompt/allow decision is visible only to the human, so every probe needs a human driving approvals.
- `probes/` — the harness (`.claude/settings.json` + TEST_PLAN) is self-contained. A new user launches `claude --setting-sources project` from `probes/` and runs the pre-flight rows; nothing else on their machine matters.
- `FINDINGS.md` / `INCOMING.md` — the empirical record. **Version-scoped, not machine-scoped:** every entry names the Claude Code version it was observed on; matcher behavior is a property of the CC binary, so results transfer to any machine on the same version — and go stale on every version bump, which is the entire reason the corpus exists.

**Not portable (this-repo-specific) — needs parameterization or replacement in a spinoff:**
- The shipped hooks (`claude-hooks/block_*.py`) and their installer (`update_claude_permissions.py`, `install.sh`) are shaped to one user's allow-list and multi-session workflow. In a spinoff they're *reference implementations* of Strategy 2, not drop-ins: the blanket-verb list, DENY inventory, and nastygram texts all encode local policy.
- `MATCHER_LAST_VERIFIED` / the staleness nag lives in the installer — a spinoff wants an equivalent freshness marker, wherever its install path is.
- The curator agent (`.claude/agents/chain-matcher-curator.md`) references this repo's paths.
- Absolute paths (`/Users/dan/...`) and machine names (`Dans-MacBook-Pro`, etc.) in historical entries are reproduction context, not requirements — read them as "the operator's home dir / machine."

**New-user/agent quickstart:** read this README's thesis → `STRATEGIES.md` → `METHODOLOGY.md`. To find out what *your* CC version's matcher does: `cd probes/ && claude --setting-sources project`, run the Phase-A pre-flight (deny-canary first — do not collect data until it proves your settings loaded), then the min-viable rows from the latest `REPROBE_*.md`. Compare against the newest FINDINGS entry; deviations are findings.

## Cross-references

- The hook itself: `claude-hooks/block_bash_chains.py`. Header comment links back here.
- The sibling hook: `claude-hooks/block_cd_git.py` shares the same matcher-drift risk; weirdos there go here too.
- Original durable note (now partially wrong): `notes/bash_chain_matching.md`.
- The curator agent: `.claude/agents/chain-matcher-curator.md`.
