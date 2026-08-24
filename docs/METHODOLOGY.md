# METHODOLOGY.md

How we probe Claude Code's permission matcher to figure out what `block_bash_chains.py` should actually do. Replicate this when a re-probe is justified.

## Why probing is non-trivial

You can't just ask Claude "what does the matcher do?" and get a reliable answer. The matcher is closed-source, behavior changes without notice (Anthropic ships updates to it), and even empirical findings go stale within days. The only durable approach is HITL (human-in-the-loop) testing on the actual installed Claude Code, repeated whenever findings are needed.

## Two probe modes

### Mode A: in-session via Claude + Dan reports prompts (faster, less clean)

Used when you want to investigate a hunch quickly without restarting your session.

1. **Neuter the hook so it doesn't intercept:**
   ```python
   # In block_bash_chains.py, add at top of main():
   sys.exit(0)
   ```
   The hook is re-executed per Bash call, so the edit takes effect immediately. **Remember to revert when done.**

2. **Define test cases with unique markers.** Each test command should include a string like `probemarker_NN` so the prompt text Dan sees maps unambiguously to test number N.

3. **Claude fires Bash calls one at a time, with the probe label in the tool-call `description` field.** Example: `description="Probe 5: discriminator — allowed + unknown"`. The description is what Dan sees in the prompt UI, so the label is what makes the prompt attributable to a specific test.

4. **HITL signal protocol — `AskUserQuestion` is the canonical channel.** Tool result for a prompted-then-approved Bash call looks identical to a never-prompted run (per 2026-06-01 RESULTS): Claude cannot infer prompts from tool output. Two channels exist for getting the prompt event back to Claude; only one is reliable:
   - **`AskUserQuestion` immediately after the probe — canonical.** Ask Dan "Did you get a prompt for HITL-XX?" with options for prompted-vs-silent (+ a third for "prompted but I typoed/wasn't tracking"). Same-turn, structured answer, no harness-dependent plumbing.
   - **Approval-comment field — unreliable as of 2026-06-05.** Dan can type the probe label into the optional "tell Claude" field when approving. Per the 6/4 entry this was claimed load-bearing, but 6/5 reprobing showed Dan's typed comment did not arrive in Claude's next turn. Possibly Claude Code changed the channel; possibly the 6/4 observation was incomplete. Either way: **don't trust the comment channel as your only signal.** If it arrives, treat as bonus confirmation; if it doesn't, fall back to `AskUserQuestion`.

   **Operationally:** if Dan's silence after a probe is ambiguous (could be matcher-allowed OR could be matcher-prompted-and-Dan-approved-silently), always `AskUserQuestion` to disambiguate. The cheap question is much cheaper than mis-recording a cell.

5. **Mind Claude's typing limitations:** Claude (the model) sometimes refuses or fails to type certain command-field strings (e.g. `cd /Users/dan/code/dotfiles && ...` proved difficult — RLHF-trained avoidance is the leading theory). If a test won't fire from Claude's hands, fall back to Mode B.

6. **Restore the hook when done.**

### Mode B: clean-slate session in `probes/` (cleaner, more setup)

Used when (a) Mode A is too noisy, (b) you want reproducibility, or (c) the in-session hook is hard to disable.

1. **Use the controlled scratch:**
   ```
   cd /Users/dan/code/dotfiles/docs/active/chain-hook-maintenance/probes
   claude --setting-sources project
   ```
   This loads ONLY the local `settings.json` (no user-level hooks or allow rules). Auth still works (OAuth/keychain isn't a "setting"). **Also strips user-level `additionalDirectories`** — so the *only* trusted root is cwd (`probes/`) unless the probe settings explicitly re-add roots. Rows touching `/tmp` or `~/code/…` will PROMPT despite verb-level ALLOW rules matching, unless the corresponding path is in `permissions.additionalDirectories`. See SESSION_2026-08-03_probe_aborted.md §4.1 for the discovery.

   **Launch environment matters.** The 2026-08-03 aborted probe was launched from a shell with an active project mamba env; the completed re-run same day used a bare shell (both behaved identically, so no observed effect) — but launch clean-slate probes from a bare shell (no conda/mamba/venv activation) anyway, to eliminate PATH/PYTHONPATH shadowing as a candidate cause when weirdos show up.

2. **Verify session config before collecting data** (pre-flight):
   - `claude --version` — record it. Matcher behavior is version-scoped; a version bump between sessions is the leading source of drift. (Running it *inside* the probe session will PROMPT — `claude` isn't allow-listed — so capture it in the coordinating session; same binary if same machine/PATH.)
   - **Deny-canary load-proof (run FIRST — canonical as of 2026-08-03):** the probe settings keep `Bash(rev *)` in `deny[]`; the probe session runs `rev .claude/settings.json` (cwd-confined, read-only, harmless). An **auto-DENY proves the settings file loaded** — a deny can come from nowhere else, and the row costs zero human prompts. This resolves an ambiguity that a plain sanity row cannot: a PROMPT on an allow-listed command is consistent with *either* "settings never loaded" *or* "path outside trusted roots" (that exact ambiguity produced two wrong June-2026 conclusions — "project = git root" and "`--settings` broken" — both refuted 2026-08-03 once the canary existed). While the canary is present, never use `rev` in any other probe row.
   - **Allow-list liveness pair:** a listed-verb cwd write (`touch ./loadcheck_listed`, expect ALLOW) vs. an unlisted-verb cwd write (`cp ./loadcheck_listed ./loadcheck_cp`, expect PROMPT). Same shape, one variable — proves the allow-list is live and verb-keyed. Keep both commands cwd-confined so path scope can't contaminate the reading.
   - Then the **sanity row** proper: a command that unambiguously exercises an allow rule *within the expected trusted roots* (`touch /tmp/probe_sanity`, with `/tmp` in the probe settings' `additionalDirectories`). If it PROMPTS *after* the canary proved load, that is a real finding (path-scope/Family-2 behavior), not a harness failure.
   - If the canary does NOT deny, **stop** — the settings aren't loading. Do NOT proceed to collect data; a probe that prompts on everything can't distinguish "matcher prompted" from "nothing was allow-listed."
   - Prior sanity-row failures: 2026-06-01 (settings.json in wrong location), 2026-08-03 aborted run (no `/tmp` in `additionalDirectories`). The pre-flight exists precisely to catch these.

3. **Use `probes/TEST_PLAN.md`** as the runbook. Each row has a command to paste and a column for the result.

4. **Dan or Claude paste commands one at a time** into the fresh session. Watch for prompts. Fill in the result column.

5. **Update `FINDINGS.md`** with the dated result.

### Dan's HITL denial convention

**Anything that PROMPTS, Dan denies.** A "user rejected" tool result in the probe session therefore means **PROMPT**, not disapproval of the work itself — the probe Claude should record PROMPT and continue, not stop to re-plan. Dan will often paste the prompt UI's text (command + description + reason line, if any) back into the probe session to aid triage.

**Paste-shape as diagnostic:** the shape of the pasted text is a signal about what kind of prompt fired.
- *Command + description + explicit reason-line* ("Contains process_substitution", "Brace expansion", "Contains brace with quote character", "…cannot be statically analyzed") → Family-3 static-analysis bail. **Capture the reason-line verbatim** — the node names come straight from tree-sitter-bash and are the drift-sensitive signal.
- *Command + description, no reason-line* (or bare "This command requires approval") → plain no-matching-rule prompt or path-scope prompt (e.g. path outside `additionalDirectories`). Not a Family-3 finding.
- *"\<verb\> command with flags requires manual approval"* → **built-in per-command analyzer** (new specimen 2026-08-03, from `cp --help`): CC has hardcoded knowledge of common unix verbs and categorizes "with flags" invocations separately. Not a settings rule firing, not Family-3. Distinct again from the ASK-rule shape ("Bash(\<rule\>) requires confirmation" — see FINDINGS 2026-06-09, ASK > ALLOW precedence).
- Known built-in special cases that produce silence where the model predicts a prompt: `claude --help` (CC auto-allows its own help invocation — narrowly; `claude --version`, `cp --help`, and unknown-verb `--help` all still prompt; FINDINGS 2026-08-03 Finding C).

This convention is protocol, not trivia — SESSION_2026-08-03_probe_aborted.md §2 wrote it down after its absence cost real time.

### The Bash sandbox layer (new since June 2026)

CC ≥ some-version-in-the-2.1.16x→2.1.22x range (present in **2.1.220**, absent in **2.1.165**) exposes a `dangerouslyDisableSandbox` parameter on Bash tool calls, indicating a sandbox now runs *upstream* of the permission matcher. The exact intercept rules are not documented; empirically confirmed only that the flag itself doesn't force a prompt (TESTED: `dangerouslyDisableSandbox: true` on `echo` ran silently in the 2026-08-03 probe).

**Why it matters for drift checks:** the sandbox can potentially auto-permit or auto-deny commands *before* the matcher sees them. That would corrupt drift-check signal in both directions:
- Sandbox auto-permits a read-only command → probe sees ALLOW → reads as "the Family-3 heuristic disappeared" → false argument for deleting a hook that's actually still earning its keep. **False-negative in the dangerous direction.**
- Sandbox forces a prompt → probe sees PROMPT → masks a real ALLOW → false argument for new hook.

**Rows at risk:** the read-only Family-3 rows (14, 16, 17 in the min-viable pass) are the ones most exposed to the false-negative direction.

**Recommended methodology (updated 2026-08-03 after the completed run): deviation-triggered, not full two-column.** Run the pass once in the default (sandbox-on) condition — the operationally-real one. Any row that deviates from expectation gets one re-run with `dangerouslyDisableSandbox: true` for attribution: pair disagrees → sandbox implicated; pair agrees → the matcher owns the result. This halves HITL burden versus running every row twice, and loses nothing when results match expectations. (The full two-column matrix remains the right tool if a pass produces *many* deviations, or if the specific question is "what does the sandbox itself do.")

Empirical status after the 2026-08-03 completed pass: **zero deviations in the default condition across all 8 min-viable rows** — including the read-only Family-3 rows (16, 17) most exposed to the auto-permit false-negative. The sandbox interception layer remains uncharacterized in general, but it did not affect any shape in that pass. Earlier partial tests: `dangerouslyDisableSandbox: true` on `echo` ran silently (flag isn't itself a prompt trigger); the flag on `touch /tmp/probe_sanity` didn't change its PROMPT (consistent with path scope being a permission matter the flag doesn't bypass).

## Building unambiguous test cases

The matcher's allow/prompt decision must be cleanly attributable to *one* hypothesis. Pitfalls:

- **Overlapping rules.** If both `Bash(cd /tmp *)` and `Bash(probemarker_*)` are in the allow list, you can't tell which one allowed a `cd /tmp && probemarker_xxx` chain. Solution: use markers (`probemarker_NN`) that no rule matches, so the chain's acceptance can only be attributed to the prefix rule.
- **Subdirectory paths.** `cd /Users/dan/code/some/thing` does NOT match `Bash(cd /Users/dan/code *)` (space vs slash) — this turned out to be a separate gotcha we discovered mid-probe. Use exact paths matching exactly what the rule says.
- **Quoted semicolons.** Avoid using `python3 -c "...;..."` or similar in your probe scripts — the matcher tokenizes on `;` even inside quotes (see FINDINGS.md 2026-05-30). Use heredocs or one-line python instead.

## When to re-probe

Triggers:
- Dan reports a "this shouldn't have prompted" weirdo and the cause isn't obvious from `INCOMING.md` analysis alone.
- The Claude Code version has bumped significantly (`claude --version`).
- It's been more than ~30 days since the last entry in `FINDINGS.md` and the hook is actively causing friction.

Don't re-probe just because you're curious — the probe takes 5–15 minutes of Dan's attention and burns through some prompts.

## What a good FINDINGS.md entry looks like

See the 2026-05-30 entry as a model. Includes: dated header, methodology pointer, results table, interpretation, what-it-means-for-the-hook, and a confidence assessment that's explicit about instability.
