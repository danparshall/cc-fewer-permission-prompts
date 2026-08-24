# FINDINGS.md

Dated entries documenting what we know about Claude Code's permission matcher and how that knowledge maps to `block_bash_chains.py`. **Newest entries on top.**

Each entry should include:
- Date
- Methodology (link to METHODOLOGY.md or note one-off variations)
- Empirical results
- Interpretation / hypothesis
- Impact on the hook (what should change, if anything)
- Confidence level

---

## 2026-08-03 (later) — 30-day drift check COMPLETE: 8/8 rows match, NO drift on CC 2.1.220. Path-scope hypothesis CONFIRMED. Load-proof canary technique added. June "project = git root" conclusion refuted.

**Status:** The full min-viable pass ran to completion on the second attempt, same day as the aborted run below. **All 8 rows match the June-era / 2026-07-28 model — no matcher drift.** `MATCHER_LAST_VERIFIED` bumped to 2026-08-03; snooze cleared to `None`. Every shipped hook retains its empirical justification on CC 2.1.220.

**Methodology:** Mode B HITL per METHODOLOGY.md. Fresh `claude --setting-sources project` from `probes/`, launched from a clean shell (no conda/mamba env — controlling for the aborted run's confound). Coordinating session: Fable 5 (this entry's author); the human operator drove paste-and-report with the deny-everything convention. CC **2.1.220** both sides. Runsheet: v2, authored this session (superseded the Air runsheet, which had inherited a malformed row from TEST_PLAN — see Finding D below). Sandbox strategy: **deviation-triggered** (single default-condition pass; any deviating row would get a `dangerouslyDisableSandbox: true` re-run for attribution) — chosen over the aborted session's full two-column recommendation to halve HITL burden. **No deviations occurred, so no re-runs fired.**

**Innovation this run — Phase A load-proof (the piece every prior failed probe was missing):**

A skeptical re-read of `RESULTS_2026-06-01.md` showed that *no session had ever proven `probes/.claude/settings.json` loads at all* under `--setting-sources project`:
- June v1's every-row-prompts was genuinely a wrong file location (`probes/settings.json`, bare).
- But June v2's two "failed load-checks" — which produced the recorded conclusions "`project` reads the *git-root* `.claude/settings.json`, not cwd's" and "`--settings <file>` doesn't work either" — were both `/tmp`-shaped (`touch /tmp/probe_v2_loadcheck`). Under the path-scope hypothesis those PROMPT *even with settings perfectly loaded*. Both June conclusions were therefore unsupported, and the planned falsification test (row 1 after the `additionalDirectories` fix) would have been ambiguous: a PROMPT could mean "Family-2 drift" or "settings never loaded."

Fix: a **deny-rule canary**. `Bash(rev *)` added to the probe settings' `deny[]`; probe runs `rev .claude/settings.json` (cwd-confined, read-only, harmless). An auto-DENY can come from nowhere but that file — unambiguous load-proof, costs zero human prompts. Retained as the standing first pre-flight row.

**Results:**

*Phase 0/A — environment verification:*

| # | Command | Expect | Observed | Meaning |
|---|---|---|---|---|
| P0 | `claude --version` | record | PROMPT (plain shape) | unlisted verb prompts — model-consistent; also sharpens Finding C |
| A1 | `rev .claude/settings.json` | DENY | **DENY** | **settings file PROVEN loaded**; `--setting-sources project` DOES read cwd's `.claude/settings.json` on 2.1.220 — June v2's "git root" conclusion refuted |
| A2 | `touch ./loadcheck_listed` | ALLOW | ALLOW | listed verb, cwd write |
| A3 | `cp ./loadcheck_listed ./loadcheck_cp` | PROMPT | PROMPT (plain) | unlisted verb, same shape as A2 → allow-list live and verb-keyed |

*Phase B/C — the min-viable 8 (numbering per TEST_PLAN):*

| Row | Command | Expected | Observed | Reason-text (verbatim) |
|---|---|---|---|---|
| 1 | `touch /tmp/probe_sanity` | ALLOW | **ALLOW** | — |
| 3 | `mkdir -p /tmp/probe3 && touch /tmp/probe3/x` | ALLOW | **ALLOW** (silent) | — |
| 4 | `mkdir -p /tmp/probe4 && unknownmarker_test4` | PROMPT | **PROMPT** | none (plain) |
| 14 | `python3 <<'PY' 2>&1` … `PY` (corrected shape) | PROMPT | **PROMPT** | "Contains shell syntax (file_redirect) that cannot be statically analyzed" |
| 16 | `ls /tmp/{a,b}` | PROMPT | **PROMPT** | "Brace expansion" |
| 17 | `diff <(echo a) <(echo b)` | PROMPT | **PROMPT** | "Contains process_substitution" |
| 20 | `find /Users/dan -maxdepth 1 -name .bashrc` | PROMPT | **PROMPT** | none (plain — Family-2 shape) |
| 21 | `/tmp/x.py` | PROMPT | **PROMPT** | none (plain — allow-rule gap) |

*Phase D — anomaly discriminators (aborted run's Finding 3):*

| # | Command | Observed | 
|---|---|---|
| D1 | `claude --help` | **ALLOW** |
| D2 | `ls /tmp \| head -3` | **ALLOW** |
| D3 | `cp --help` | **PROMPT** — "cp command with flags requires manual approval" |
| D4 | `unknownmarker_helptest --help` | **PROMPT** (plain) |

### Finding A — path-scope hypothesis CONFIRMED (was Finding 1, HYPOTHESIZED, in the aborted entry)

`touch /tmp/probe_sanity` flipped PROMPT → ALLOW with exactly one variable changed: `additionalDirectories: ["/tmp"]` added to the probe settings (load-proven via A1, so the entry was demonstrably in effect). Mechanism confirmed: **verb-level ALLOW rules do not span paths outside the trusted-root set (cwd + `additionalDirectories`); path scope preempts verb match.** The aborted run's rows 1/3 were a harness bug, not drift. Row 20 (`find` on an ancestor outside trusted roots → PROMPT despite `Bash(find *)`) is now confirmed under a verified harness, upgrading the 2026-07-14 INCOMING grep-path entry's mechanism from hypothesized to directly observed. June v2's failed load-checks are retroactively explained by the same mechanism.

### Finding B — no drift, all hooks keep their justification

All six Family-3 node behaviors sampled (file_redirect via row 14, brace_expansion via 16, process_substitution via 17), per-segment chain matching (rows 3/4), Family-2 path scope (row 20), and the `.py`-verb allow-rule gap (row 21) behave exactly as the June-era + 2026-07-28 model describes. Reason-text formats unchanged ("Contains \<node\>" bare format; "Contains shell syntax (\<node\>) that cannot be statically analyzed" for the static-analysis family). **Hook implications: none. Do not retire anything.** `block_brace_expansion.py`, `block_heredoc_with_pipe_or_redirect.py`, `block_bash_chains.py`, `block_absolute_path_py_verb.py` all re-justified on 2.1.220.

### Finding C — the `claude --help` anomaly RESOLVED: CC special-cases its own binary's `--help`, narrowly

The aborted run's unexplained silent `claude --help 2>&1 | grep …` decomposes into two now-observed behaviors, leaving no model gap:
- **D2**: top-level pipelines with a listed leading verb pass silently (June model, reconfirmed).
- **D1 vs P0 vs D3 vs D4**: `claude --help` ALLOWs while `claude --version` prompts, `cp --help` prompts, and `unknownmarker --help` prompts. So the silence is **not** a global help-flag rule (D4), **not** verb-generalized (D3), and **not** blanket coverage of the `claude` binary (P0). It is a narrow special case — CC auto-allowing (at least) its own `--help` invocation. Hook implications: none.

### Finding D — TEST_PLAN rows 14/15 were malformed (authoring bug, now fixed)

Both rows placed the redirect/pipe on the heredoc *terminator* line (`PY 2>&1`), where it is not shell syntax: the heredoc never closes, the text goes to the interpreter as stdin, and no `file_redirect`/`pipeline` node exists in the AST. The malformed shape ALLOWs — *correctly* — and its first-attempt ALLOW this run briefly looked like drift. Rows corrected in TEST_PLAN.md (redirect/pipe moved to the open line, matching the rows' own hypothesis text) and row 14 re-run in corrected form: PROMPT with verbatim June-era reason-text. Incidental positive datum: **the matcher does not fire on redirect-shaped text inside heredoc bodies** — it lexes heredocs properly (contrast the Family-1 brace-quote heuristic, which does scan heredoc bodies).

### Finding E — new prompt-text specimen: built-in per-command analyzer ("cp command with flags requires manual approval")

D3's prompt text is a third family of prompt shape, distinct from both the plain no-rule shape ("This command requires approval") and the ASK-rule shape ("… requires confirmation"): CC evidently has built-in per-command knowledge of common unix verbs and categorizes "with flags" separately. Added to METHODOLOGY's paste-shape diagnostic table. No hook implications; useful for future triage (that text ≠ a settings rule firing).

### Sandbox status (aborted run's Finding 2): no interference observed

Every row matched expectation in the default (sandbox-on) condition, so the deviation-triggered re-runs never fired. In particular the read-only Family-3 rows 16/17 — the ones flagged as at-risk of sandbox auto-permit masking ("false argument for deleting hooks") — PROMPTED normally. The sandbox interception layer remains uncharacterized in general, but it is **empirically absent from every shape in this pass**, which is the operationally relevant claim. INCOMING's sandbox entry updated and moved to Triaged.

### Also logged this session (coordinating side, separate from the probe)

`block_heredoc_with_pipe_or_redirect.py` **false-positived** on a grep whose quoted *pattern argument* contained `<<` (`grep "…\|<<'PY'" file | head`) — the `<<` was string content, not a heredoc, and the pipe supplied the second conjunct. Hook-side FP recorded in INCOMING (first observed occurrence; refinement sketch there — not urgent at n=1).

**Housekeeping:** all probe artifacts cleaned (`/tmp/probe_sanity`, `/tmp/probe3/`, `/tmp/x.py`, `loadcheck_listed`, both runsheets; `probe4/` and `loadcheck_cp` were never created — their rows were denied). Deny-canary and `additionalDirectories: ["/tmp"]` retained in probe settings as standing harness, with in-file notes updated to confirmed status.

**Confidence:** Medium-high on "no drift" — 8 min-viable rows, one per family, all with verified harness (the first pass in this work-line's history where settings-load was *proven* rather than assumed). A full pass would extend to Family-1 (row 18), the loop-body rows, and row 15's corrected shape. High on Finding A (single-variable flip under load-proof). High on Finding D (deterministic parse behavior). Medium on Finding C's mechanism (special case observed at 4 cells; its exact extent — other `claude` subcommands, other self-invocation shapes — unprobed).

---

## 2026-08-03 — Scheduled 30-day drift check: ABORTED at sanity row. NO drift verdict. Environment findings only.

**Status:** The min-viable 8-row pass did NOT complete. 2 of 8 rows attempted (both PROMPTED, both were expected ALLOW). Probe halted at the sanity row per its own halting discipline — a probe that prompts on everything cannot distinguish "matcher prompted" from "nothing was allow-listed." **`MATCHER_LAST_VERIFIED` NOT bumped.** The June-era matcher model is neither confirmed nor refuted for CC 2.1.220.

The value of this session is entirely environmental: it surfaced (a) a probe-settings gap that had gone unhit for two months, (b) a new sandbox layer that changes what Mode B measures, (c) one accidental data point that pre-confirms row 20, and (d) an unresolved anomaly worth its own isolation matrix. Handoff to Fable-tier session for the actual drift check.

Full session log by the probe Claude itself: `probes/SESSION_2026-08-03_probe_aborted.md` (Dan's request; written in the probe session before it exited).

**Methodology:** Mode B HITL. Fresh `claude --setting-sources project` session on `Dans-MacBook-Pro` from `docs/active/chain-hook-maintenance/probes/`. **CC 2.1.220** — first Mode B probe on this version (last was CC 2.1.165, 2026-06-05). Coordinating Sonnet session (this one) handed the probe Claude a runsheet at `/tmp/reprobe_2026-08-03_runsheet.md`; probe Claude was Opus 5. **Non-standard launch context**: probe was launched from a shell with an active mamba env (`(<private-project>)`). Not shown to affect matcher/sandbox behavior; noted so Fable can control for it.

**Results attempted (of the min-viable 8):**

| # | Command | Expected | Observed | Attributable to |
|---|---|---|---|---|
| 1 | `touch /tmp/probe_sanity` | ALLOW | **PROMPT** | See §Findings-1 (probe settings gap, likely) |
| 3 | `mkdir -p /tmp/probe3 && touch /tmp/probe3/x` | ALLOW | **PROMPT** | Same suspected cause as row 1 |
| 4, 14, 16, 17, 20, 21 | — | — | **NOT RUN** | Halted at sanity |

**Ancillary observations (probe Claude's session log §3, TESTED):** these are actual tool-call results from the aborted probe, not from the planned test rows.

| Row | Command | Verb allow-listed? | Path outside cwd? | Result |
|---|---|:--:|:--:|---|
| d | `ls -la <probes/>` (cwd) | yes `Bash(ls *)` | no | **ALLOW** |
| f | `echo sandbox-discriminator-readonly` | yes | no | **ALLOW** |
| g | `touch ./sandbox_discriminator_in_workspace` | yes `Bash(touch *)` | no (cwd) | **ALLOW** |
| h | `pwd` | **no** (`pwd` unlisted) | no | **ALLOW** |
| i | `claude --help 2>&1 \| grep -i -A2 sandbox` | **no** (`claude` unlisted; pipe present) | no | **ALLOW** |
| j–m | `git -C /Users/dan/code/dotfiles …`, `grep -rn …` | yes `Bash(git/grep *)` | yes | **ALLOW** |
| o | `cd /tmp && git status` | yes both segs | yes | **PROMPT** (CC hardcoded bare-repo-attack heuristic) |
| p | `touch /tmp/probe_sanity` with `dangerouslyDisableSandbox: true` | yes | yes | **PROMPT** |
| q | `echo flag-isolation-test` with `dangerouslyDisableSandbox: true` | yes | no | **ALLOW** |
| r | `ls -la <parent-of-cwd>` | yes `Bash(ls *)` | yes (ancestor) | **PROMPT** |

### Finding 1 — path-scope hypothesis (HYPOTHESIZED, high fit to data; NOT yet falsification-tested)

**Claim:** `--setting-sources project` loads only `probes/.claude/settings.json`, which had no `additionalDirectories`. That strips Dan's user-level trusted roots (`~/code`, `/tmp`). The sole trusted root then becomes cwd (`probes/`), so any path outside cwd — including `/tmp` writes and the parent directory — PROMPTS despite matching verb-level ALLOW rules.

**Data fit:** every ALLOW/PROMPT in the ancillary table above matches the "path outside cwd" axis with no counter-examples:
- All cwd-confined commands ALLOW (d, f, g, h, i, n, q).
- All `/tmp` writes PROMPT (b, c, p) despite `Bash(touch *)` / `Bash(mkdir *)` matching.
- Ancestor `ls` PROMPTS (r) despite `Bash(ls *)` matching. **This is the strongest data point** — row (r) was accidental (a housekeeping `ls`, not a planned test), and it happens to be the same shape as planned row 20 (`find` on an ancestor of cwd outside trusted roots → PROMPT), *arguably pre-confirming row 20 without running it*.
- `git -C /Users/dan/code/dotfiles …` and `grep -rn … /Users/dan/code/dotfiles` (j–m) ALLOW despite touching `~/code/dotfiles` — need to explain how. Possible: (i) `git -C <path>` doesn't get path-scope-checked because the path is a flag arg, not a positional path arg; (ii) `~/code` was in `additionalDirectories` in v2.1.165 by default, and CC still ships that as a stock trusted root; (iii) something else. **Not investigated.**

**Historical fit:** The single successful Mode B run (2026-06-05 loop-reenable, CC 2.1.165) used commands with no path arguments at all (`for i in 1 2 3; do echo M_F1 | cat; done`, etc.). So the `/tmp` gap has never actually been hit by a Mode B probe — the 2026-06-01 v1/v2 sessions both failed at the sanity row too, but for a different reason (settings.json in wrong location; RESULTS_2026-06-01.md). The `additionalDirectories` gap has probably always existed in the probe settings; it's just been invisible because prior Mode B runs didn't exercise external paths.

**HYPOTHESIZED-not-tested:** the mechanism ("path outside cwd/`additionalDirectories` → prompt despite verb-level ALLOW") is inferred from data-fit; not directly probed. A clean falsification test: add `additionalDirectories: ["/tmp"]` to probes settings, re-run rows 1/3. If they ALLOW, hypothesis confirmed. If they still PROMPT, this is genuine Family-2 drift and a significant finding. **The additionalDirectories fix has been applied (2026-08-03, this session); the falsification test is Fable's job.**

**Alternative hypothesis (still live):** The Bash sandbox (Finding 2) intercepts before the matcher and denies writes to `/tmp` from within a `--setting-sources project` session for some reason unrelated to `additionalDirectories`. Under this alternative, adding `additionalDirectories` won't fix the sanity row.

### Finding 2 — the Bash sandbox is a new confound (HYPOTHESIZED, partially TESTED)

**TESTED:** CC 2.1.220 exposes a `dangerouslyDisableSandbox` parameter on Bash tool calls (probe Claude's §3 rows p, q). The parameter didn't exist in June's CC 2.1.165. Setting `dangerouslyDisableSandbox: true` on `echo flag-isolation-test` (row q) ran silently, so the flag itself is not a prompt trigger.

**HYPOTHESIZED:** the parameter's existence implies an actual sandbox layer runs somewhere upstream of (or in parallel with) the matcher. If so, it can potentially auto-permit or auto-deny commands before the matcher sees them. Neither direction has been directly observed. The concerning direction is auto-permit: `ls /tmp/{a,b}` is read-only, so if the sandbox auto-permits it, a probe would read ALLOW → interpret as "brace-expansion heuristic disappeared" → false argument for deleting `block_brace_expansion.py`. **The 2026-07-28 process-substitution probe was run on 2.1.220 or the version just before; its PROMPT result argues *against* the sandbox blanket-auto-permitting reads** — but that's one data point, not a matrix.

**Recommendation to Fable:** run each of the 8 min-viable rows in **both** sandbox conditions (`dangerouslyDisableSandbox: false` — the operationally-real condition — and `dangerouslyDisableSandbox: true` — the June-equivalent condition). Where columns disagree, that's the finding. Single-condition data misreads whichever column's rows are sandbox-affected.

### Finding 3 — anomaly, unresolved (HYPOTHESIZED): `claude --help 2>&1 | grep …` runs silently despite (a) `claude` not being allow-listed and (b) presence of a pipe

Rows (i) and (n): both ran silently. Under a strict reading of the current model, this should have prompted twice over (unknown-verb PROMPT + pipeline Family-3 bail). Candidate explanations, all HYPOTHESIZED-not-tested:
- Built-in "safe" allow-list inside CC that covers `claude` (or `--help`-shaped invocations)
- Sandbox auto-permitting cwd-confined read-only commands before the matcher sees them
- Leading-verb matching behaving differently than the 2026-06-05 (loop-reenable) entry documents

**Ready-made discriminator pair:** (h) `pwd` (unlisted, no pipe, ALLOW) vs. (i) `claude --help 2>&1 | grep` (unlisted, with pipe, ALLOW). If `claude --help` alone (no pipe, no redirect) also ALLOWs, the pipe half of the anomaly is real — pipe is Family-3 and should have prompted. If it PROMPTs, then it's specifically the pipe/redirect that changed something and the pipeline analysis needs revisiting.

### Finding 4 — user-level hooks are genuinely inert in probe sessions (INDIRECTLY TESTED)

Row (o): `cd /tmp && git status` prompted with a *normal* approvable prompt (not the distinctive hard-fail nastygram from Dan's `block_cd_git.py`). That's inferential evidence (message shape) that `--setting-sources project` strips Dan's user-level PreToolUse hooks, as intended. Not conclusive (didn't try to force `block_cd_git.py` to fire in a way that would be unmistakable), but consistent.

### Impact on the hook (all hooks): NONE this session

- `block_bash_chains.py`: no data. All-blanket chain (mkdir + touch, row 3) prompted, but attributable to path-scope, not chain-hook territory.
- `block_brace_expansion.py`, `block_heredoc_with_pipe_or_redirect.py`, process-substitution guard: not exercised (probe halted before rows 14/16/17). **Do NOT delete these based on 2026-08-03 evidence.**
- Every hook decision waits on a clean Mode B pass under CC 2.1.220. Handoff below.

### Impact on the runbook + settings

- **APPLIED (2026-08-03, this session):** added `additionalDirectories: ["/tmp"]` to `probes/.claude/settings.json`, with an in-file comment tagging it as hypothesis-driven pending Fable verification. If the sanity row still fails with this, the hypothesis is wrong and the finding shifts to "Family-2 drift."
- **APPLIED (this session):** METHODOLOGY.md updated with (a) Dan's HITL deny-everything convention (probe Claude's §2), (b) the sandbox-layer awareness section + the two-column sandbox-on/off recommendation, (c) pre-flight guidance to verify `claude --version` and run the sanity row before collecting data.
- **NOT APPLIED — for Fable:** re-running the 8 rows, capturing reason-text verbatim on 14/16/17, resolving Findings 1/2/3.
- **`MATCHER_NAG_SNOOZE_UNTIL`:** left NULL (unchanged from `2026-07-25` if not otherwise touched — check `update_claude_permissions.py:64`; the yellow nag remains live-and-expired, which is the correct signal — the check has not actually run).

### Housekeeping

- Stray artifact from probe Claude's row (g): `probes/sandbox_discriminator_in_workspace` (empty file). Deleted this session — no probe depends on it.
- `/tmp/x.py` remains (Dan created it for row 21; still needed for the Fable re-run).
- `/tmp/reprobe_2026-08-03_runsheet.md` remains (may be superseded by a fresh runsheet Fable authors; safe to delete either way).
- `/tmp/reprobe_2026-08-03_results.md` never written — deliberately, per probe Claude's §7 (the data described the harness, not the matcher; writing it would have contaminated the drift record).

**Confidence:**
- On Finding 1 (path-scope): Medium — data-fit is complete but the mechanism is not directly probed. A single falsification test (`additionalDirectories` add + re-run rows 1/3) would flip this to High-or-refuted.
- On Finding 2 (sandbox): Medium-low — flag exists (High), but the sandbox's actual behavior is inferred from the flag's name and one row's silence. The interception layer has not been independently observed.
- On Finding 3 (anomaly): Low as a finding, High as an open question. Two rows (i, n) both silent; discriminator pair is set up; not investigated.
- On Finding 4 (hooks inert): Medium — inferential from message shape only.
- On the absence of matcher drift for the 8 planned rows: **Zero confidence in either direction.** Not tested this session.

---

## 2026-07-28 — Static-analysis bail: process substitution `<(…)` prompts ("Contains process_substitution") — Family 3, sixth node

**Methodology:** Mode A HITL probes in an active session on `Dans-MacBook-Pro`, cwd `~/code/dotfiles`, standard `~/.claude/settings.json`, Dan at keyboard capturing prompt reason-text verbatim. All Dan-authored hooks live but inert for these shapes — the originating weirdo command was traced through all eight Bash PreToolUse hooks in the curator session (exit 0, silent, every one), so the matcher is the sole decision-maker. Origin: INCOMING 2026-07-28 diff-procsub weirdo (`diff <(sed 's|{{skills_dir}}|…|g' <dotfiles-source>) ~/.claude/skills/write-a-plan/SKILL.md` prompted despite `Bash(diff *)` ALLOW — now Triaged).

**Results — 3-probe matrix:**

| # | Command | procsub | path axis | Result |
|---|---|:--:|---|---|
| 1 | `diff /Users/dan/code/dotfiles/README.md /Users/dan/code/dotfiles/README.md` | — | both under cwd | **silent ALLOW** |
| 2 | `diff /Users/dan/code/dotfiles/nori-researcher/skills/write-a-plan/SKILL.md /Users/dan/.claude/skills/write-a-plan/SKILL.md` | — | 2nd arg in `additionalDirectories`, NOT under cwd | **silent ALLOW** |
| 3 | `diff <(echo a) <(echo b)` | ✓ | no path args at all | **PROMPT — "Contains process_substitution"** (captured verbatim; Dan denied, probe purpose served) |

**Interpretation:**
- **`process_substitution` joins the Family-3 bail-node set:** `{file_redirect, pipeline, simple_expansion, brace_expansion, string, process_substitution}`. Architecturally consistent — the construct materializes a runtime fd path (`/dev/fd/N`) whose content comes from an embedded command, so the matcher can't statically bound what the outer verb's argument *is*. Verb-level ALLOW (`Bash(diff *)`, probe-1-confirmed healthy) does not override — pre-allow-list structural bail, as with every other Family-3 row.
- **Reason-text format:** "Contains process_substitution" — the bare "Contains <node>" form (matching `simple_expansion`, 2026-06-06), not the longer "Contains shell syntax (<node>) that cannot be statically analyzed" form (`file_redirect`/`pipeline`/`string`). Both formats name the tree-sitter-bash node; the variation is noted but not load-bearing.
- **Probe 3 isolates the construct cleanly:** no interesting paths, blanket verbs only (`diff`, `echo`) — the procsub alone is sufficient to prompt. The original weirdo is fully explained.
- **Side-finding (probe 2, held lightly):** a file arg in `additionalDirectories`-but-not-under-cwd does NOT prompt for `diff`. This down-weights the 2026-07-14 grep entry's SECONDARY (cwd-tree-only trust) hypothesis but does not settle it — `diff` was on that entry's untested-verbs list, so silence is consistent with either "`additionalDirectories` independently trusted" or "`diff` not path-scope-checked at all." The grep-vs-`~/data` discriminator in that entry remains the clean probe.

**Impact on the hook:** None; no hook changes. **Disposition: Strategy 0** — first procsub sighting in the whole corpus, so the deny-hook gate (frequent AND clean-alternative) fails on the frequency half. The clean alternative is documented for recurrence: **materialize procsub inputs to /tmp files** — e.g. `sed 's|{{skills_dir}}|…|g' <source> > /tmp/rendered.md` then `diff /tmp/rendered.md <target>` as separate Bash calls (render-then-run, same family as Write-then-run). If procsub prompts recur, revisit as a Strategy-2 candidate — but note the 2026-07-10 INCOMING entry's matcher-preempts-hooks ordering hypothesis: a deny-hook may be unable to intercept live Family-3 prompts anyway.

**Confidence:** High on the node finding — single clean probe, but with captured verbatim reason-text naming the node, silent control cells for the verb and the path axis, and full architectural consistency with five prior family members. Low-held on the probe-2 trust-set side-inference (verb-coverage confound, stated above).

---

## 2026-06-06 — A `$variable` in a loop body ALSO bails (`simple_expansion`), not just a pipe — falsifies "bare loops run silently"; plan 04 hook extended

**Methodology:** NEW technique — **headless marker-file probe**, used as the plan-04 fresh-session fire-test (which is what surfaced this). Instead of HITL (Dan reports dialog-vs-silent), spawn a fresh `claude -p < prompt` process (loads live `~/.claude/settings.json` from scratch) and have it attempt commands that write a **marker file** as their side effect. In headless `-p`, a command the matcher would PROMPT on is auto-denied (can't ask a human) → no marker; a command the matcher SILENTLY ALLOWS runs → marker appears. The marker file is **ground truth**, independent of what the sub-agent reports in text. This lets a session observe the matcher's allow-vs-ask decision *without* Dan as the instrument — a genuine addition to the work-line's toolkit (METHODOLOGY Mode A/B both assume HITL). Two fresh sessions on `Dans-MacBook-Pro` (CC 2.1.165).

**Origin:** Running plan 04's required fire-test, Dan was PROMPTED on a bare loop `for i in 1 2 3; do echo bareloop_$i; done` — directly contradicting the 2026-06-05 GREEN re-enable probe's prediction that bare for/while loops run silently. The probe wasn't wrong about what it tested; it tested **variable-free** bodies (`echo M_F1`).

**Results — isolation matrix (marker-file ground truth, fresh sessions):**

| # | Command | loop | `$var` body | pipe | Result | Marker |
|---|---------|------|-------------|------|--------|--------|
| A | `for i in 1 2 3; do echo $i >> /tmp/m; done` | ✓ | ✓ | — | **BLOCKED** "Contains simple_expansion" | absent (didn't run) |
| C | `for i in 1 2 3; do touch /tmp/var_$i; done` | ✓ | ✓ | — | **BLOCKED** "Contains simple_expansion" | absent |
| D | `for i in 1 2 3; do touch /tmp/static; done` | ✓ | — | — | **RAN** | present |
| (probe 03, prior) | `until true; do echo "$(date +%s)"; done` | ✓ | — (cmdsub) | — | silent (RAN) | — |

**Interpretation:** The matcher body-analyzes a loop and auto-approves ONLY when every body effect is statically boundable. A **bare variable expansion** (tree-sitter `simple_expansion`: `$i`, `$f`) is an unknowable value → bail, exactly like a `pipeline` in the body (2026-06-05). A **command substitution** `$(…)` does NOT bail (probe 03) — the matcher recurses into the substituted command and bounds it; a bare variable has no such handle. So the loop-body bail set is `{pipeline, simple_expansion}`, NOT command-substitution. D proves variable-free loops genuinely run silently (the static-loop allow is real). The practical consequence: since nearly every useful loop references its loop variable, the matcher prompts on essentially every real loop — "re-enable bare loops" is mostly fiction.

**Impact on the hook:** Decisive. Plan 04's premise (remove the deny → silent loops) was falsified, so removing the deny would have traded a clean hard-block for a per-loop matcher prompt — a *worse* outcome by the work-line thesis (a prompt is a parallelism tax). Dan chose to **extend the hook** rather than revert: `block_loop_with_pipe.py` now fires on `loop AND \bdo\b AND (lone | OR $var)` (two strip levels: `$var` checked on single-quote-only-stripped text since a variable expands in `"…"` but not `'…'`; `VAR_RE` excludes `$(`). This converts the matcher's cryptic per-loop prompt into a precise hard-fail with a redirect (Python / Monitor / temp var / separate calls), covers `until`/`select` (which the verb-deny missed), and leaves genuinely-static loops running silently. The blunt `Bash(for *)`/`Bash(while *)` DENYs are removed (the hook supersedes them). Fresh-session fire-test confirmed: loop+var BLOCKED by the hook (verbatim nastygram), loop+pipe BLOCKED, static loop RAN.

**Confidence:** High on the behavioral finding (marker-file ground truth, clean A/C-vs-D isolation, matcher named the node "simple_expansion" verbatim). Medium-held on the exact VAR_RE boundary (e.g. whether `${x}` braces, special params `$@`, or arithmetic `$((…))` bail identically — VAR_RE covers `$var`/`${var}`/special-params but not `$((`; untested edges default to the cheap-FP side per Dan's sign-off). Mechanism note (body-analysis, leading-verb anchoring) held lightly — closed-source matcher.

---

## 2026-06-05 (latest) — `for`/`while` confirmed to match `until` natively: bare loops body-analyzed & silent, loop+pipe prompts — loop-reenable probe GREEN

**Methodology:** Mode B HITL probe — fresh `claude --setting-sources project` session in `docs/active/chain-hook-maintenance/probes/` (Claude Code **2.1.165**, `Dans-MacBook-Pro`). `--setting-sources project` loads ONLY the probe `.claude/settings.json` (allows `echo`/`head`/`git`/`python3`; **no** `for`/`while`/`until` rule, no `cat`/`rev` rule), so user-level hooks (`block_bash_chains.py` etc.) and the production `Bash(for *)`/`Bash(while *)` DENY are both absent — the matcher's *native* for/while behavior is observable for the first time (it had been masked by our own deny the entire work-line). HITL signal: Dan reported dialog-vs-silent per row (he approved or denied; I confirmed dialog state via AskUserQuestion since an approved-prompt and a silent-allow both return output identically). Protocol + matrix: `probes/TEST_PLAN_loop_reenable.md`.

**Origin:** Gated probe required by `TEST_PLAN_loop_reenable.md` before removing the for/while deny. We had native loop data for `until` *only* (2026-06-05 "later" entry); for/while were assumed-but-unconfirmed to match. This probe confirms.

**Results — 5-probe matrix (markers `M_FN` have no allow rule, so an ALLOW can only come from the matcher's loop/body handling):**

| # | Command | loop | pipe | unknown body verb | Result |
|---|---|:--:|:--:|:--:|---|
| F1 | `for i in 1 2 3; do echo M_F1; done` | ✓ | — | — | **silent ALLOW** |
| F2 | `for i in 1 2 3; do echo M_F2 \| cat; done` | ✓ | ✓ | — | **PROMPT** |
| F3 | `while false; do echo M_F3; done` | ✓ | — | — | **silent ALLOW** |
| F4 | `while false; do echo M_F4 \| cat; done` | ✓ | ✓ | — | **PROMPT** |
| F5 | `for i in 1 2 3; do rev <<< M_F5; done` | ✓ | — | ✓ (`rev`, + `<<<`) | **PROMPT** |

**Interpretation:** `for`/`while` behave *identically* to `until` — same `do…done` structure, same matcher handling. Confirmed:
- **Bare loop body-analyzed & auto-approved** (F1, F3): no `Bash(for *)`/`Bash(while *)` rule exists, yet both run silent. The matcher looks *inside* the body, sees `echo` is allow-listed, and approves the loop.
- **It genuinely gates on the body verb** (F5): `rev` (no allow rule) → PROMPT. So F1/F3's silence is real body-analysis, *not* a blanket loop fast-path. (Rules out the "F5 ALLOW" corrected-mechanism branch in the test plan.) The `<<<` here-string co-occurs but the unknown-verb explanation is sufficient and consistent with the `until` model.
- **Pipe in the loop body bails** (F2, F4): same Family-3 "pipeline cannot be statically analyzed" bail as `until`+pipe (probe 02, 2026-06-05 "later"). Here the pipe tail `cat` is *not* allow-listed, so attribution is slightly less clean than the plan's `head -1`, but the bail is structural/segment-agnostic (proven for `until` where both segments *were* allow-listed and it still prompted), so the verdict stands.

This is the **GREEN** outcome defined in `TEST_PLAN_loop_reenable.md` (F1 ALLOW, F3 ALLOW, F2/F4/F5 PROMPT). Dan's inversion is validated: the one shape the matcher chokes on is `loop + pipe`; every pipe-free loop is matcher-safe.

**Impact on the hook:** Unblocks the gated implementation in `TEST_PLAN_loop_reenable.md` — replace the wholesale `Bash(for *)`/`Bash(while *)` DENY with a targeted `block_loop_with_pipe.py` (deny only `(for|while|until|select)` co-occurring with a lone `|`, carve out `||`), and re-enable bare loops broadly. Detector may over-fire freely: a false positive costs only a Claude rewrite; a false negative costs Dan a matcher prompt. **SHIPPED 2026-06-06 (plan 04) — but see the 2026-06-06 entry at top: the "re-enable bare loops broadly" half was FALSIFIED.** A `$variable` in the loop body also bails (`simple_expansion`), and almost every useful loop has one, so bare loops don't run silently in practice. The hook shipped with the variable case folded in (`loop AND \bdo\b AND (| OR $var)`); the deny was removed but the hook — not silent loops — is what governs loops now.

**Confidence:** High for the native for/while behavior (direct HITL observation, clean matrix matching the independently-established `until` model). The mechanism note (body-analysis, leading-verb anchoring) remains held lightly — closed-source matcher.

---

## 2026-06-05 (later) — Static-analysis bail: a pipeline nested inside a loop body prompts ("pipeline cannot be statically analyzed") — Family 3, loop-context row

**Methodology:** Mode A HITL probe in active session on `Dans-MacBook-Pro` (Claude Code **2.1.165**). `block_bash_chains.py` **NOT neutered** — by design: every probe leads with `until`, which `FLOW_CONTROL_RE` matches, so the chain hook short-circuits (line 158) and the matcher is the sole decision-maker. The other block hooks don't match (no heredoc, brace, cd-git, `.py` verb, newline-hash). So the matcher's native behavior is observed unmasked, with no safety hook to remember to re-enable. HITL signal: Dan reported prompted-probe numbers in free text after each batch. Probe loop bodies use `until true`, so the body never executes (zero hang risk) — the matcher still statically scans the whole command string regardless.

**Origin:** Dan-reported real-world weirdo (this session) — a foreground memory-monitor loop, `until grep -q … 2>/dev/null; do PYMEM=$(ps -axo rss,comm | grep -i python | sort -rn | head -1); echo "…$(date …) … $(memory_pressure | grep …)"; sleep 20; done; echo …; grep -v … `, prompted. The command bundles four candidate triggers (loop, pipe, command-substitution, redirect); this probe isolates which the matcher actually bails on. **Not a weirdo in the false-positive sense** — see "Impact" — but a legitimate prompt whose *cause* needed isolating.

**Results — 6-probe isolation matrix (loop × {pipe, cmd-subst, redirect} + bare-pipe controls):**

| # | Command | loop | pipe | cmd-subst | redirect | Result |
|---|---|:--:|:--:|:--:|:--:|---|
| 01 | `until true; do echo M01; done` | ✓ | — | — | — | silent |
| 02 | `until true; do echo M02 \| cat; done` | ✓ | ✓ | — | — | **PROMPT** |
| 03 | `until true; do echo "M03 $(date +%s)"; done` | ✓ | — | ✓ | — | silent |
| 04 | `until true; do echo M04 2>/dev/null; done` | ✓ | — | — | ✓ | silent |
| 05 | `echo M05 \| cat` | — | ✓ | — | — | silent |
| 06 | `echo M06 \| rev` | — | ✓ | — | — | silent |

(M0N = `probemarker_0N`. Probe 06's second segment `rev` is **not** allow-listed.)

**Interpretation:** The matcher bails on exactly one shape — a **pipeline (`|`) inside a loop body**. Decomposed:
- **Bare loop is fine** (01): the matcher does not refuse loops as such; it analyzes a simple loop body and auto-approves despite there being no allow rule for `until`.
- **Bare pipeline is fine** (05, 06) — even with a non-allow-listed *second* segment (`rev`). For a top-level pipeline the matcher anchors on the **leading** verb (`echo`, allow-listed) and approves the whole pipeline; the trailing segment's allow-status isn't consulted. (This differs from the per-segment model for `&&`/`||`/`;` in the 2026-06-04 entry — bare pipelines appear leading-verb-anchored, not per-segment.)
- **Loop + command-sub** (03) and **loop + redirect** (04) are both fine — the loop context alone does not defeat analysis.
- **Loop + pipeline bails** (02) — and probe 02's segments are **both** allow-listed (`echo`, `cat`), yet it prompts. So this is *not* a segment-allow miss; it's a structural static-analysis bail.

Mechanism (held lightly — closed source): the matcher has a fast-path for a top-level pipeline (anchor on the command's leading verb). Nested inside a loop body the pipeline is no longer in leading position, the fast-path doesn't apply, and the general "pipeline cannot be statically analyzed" bail fires — the same Family-3 bail seen for heredoc+pipeline, reached via a different co-occurrence (flow-control instead of heredoc).

**Family classification — Family 3, loop-context row.** Same bail family as the heredoc+pipe/redirect and brace-expansion entries (structural bail on a construct whose effect can't be statically bounded), reached through a new context. **Asymmetry vs. the heredoc row:** with a heredoc, BOTH pipe *and* extra-redirect bail; with a loop, ONLY pipe bails (loop+redirect is silent). The loop context is the narrower trigger.

| Co-occurring construct | + pipeline | + redirect | + cmd-subst |
|---|:--:|:--:|:--:|
| heredoc (2026-06-05 earlier) | bail | bail | (untested) |
| loop body (this entry) | **bail** | silent | silent |

**Impact on the hook / work-line:**
- **`block_bash_chains.py`:** none. It correctly skips `until` (flow control); the lone `|` is not a `CHAIN_RE` operator anyway. Working as designed.
- **No new hook yet.** Gate is "frequent AND clean-alternative." The clean alternative exists (the **Monitor tool** for the monitor-loop case; Python for pipe-in-loop data work), but this is one real-world instance. Logged as a **pattern to watch**, not a hook trigger. If agents hand-roll loop+pipe repeatedly, a `block_loop_with_pipe.py` (Strategy 2) nagging toward Python/Monitor would be justified — as a *prompt→deny ergonomic* upgrade (training away from a matcher-choke), **not** a security control (see reframe below).
- **Allow rules:** no fix possible — structural static-analysis bail is pre-allow-list, same class as the other Family-3 rows.

**Threat-model reframe (this session).** The `for`/`while` DENY and `notes/bash_loop_permissions.md` were originally framed as a *security* control ("loop bodies hide destructive content from literal-string matching"). That framing is incoherent with the rest of the allow-list: `Bash(bash *)`, `Bash(python *)`, `Bash(node *)` are all blanket-allowed and each grants unbounded arbitrary code execution — a loop adds nothing an adversary doesn't already have via `bash -c`. Per Dan, the model is **not** treated as an adversary; the cost being minimized is **needless prompts disrupting parallel workflow**. So the loop deny is (and always was) an *ergonomic/training* control — same spirit as `block_bash_chains.py`'s own self-description ("a Claude-behavior training tool, not a matcher-faithfulness wrapper"), not a security boundary. This finding sharpens it: the matcher does **not** prompt on bare loops at all — so the for/while deny isn't even preventing matcher-prompts on loops; it's purely steering agents toward clearer patterns. The actual matcher-friction is the narrow loop+pipe shape.

**Confidence:** High for the isolation (6 clean probes; one trigger isolated; both bare-pipe controls confirm pipelines-alone are fine; both segments of the prompting probe are allow-listed, ruling out segment-allow). Medium for the "leading-verb-anchored bare pipeline" sub-claim (05/06 are consistent with it, but I didn't probe a non-allowed *leading* verb in a bare pipe). Low, as always, for stability — the matcher is actively iterated.

**Generalizable lesson:** A construct the matcher tolerates at top level (a pipeline) can still trigger a Family-3 bail when nested inside another structure that moves it out of leading position. When triaging a prompted compound command, isolate constructs **in their actual nesting context**, not standalone — a bare-pipe probe alone would have wrongly exonerated the pipe here.

## 2026-06-05 — Static-analysis bail: bash brace expansion (`{a,b}`, `{1..5}`) in shell-argument position prompts — Family 3 second row

**Methodology:** Single-probe HITL discriminator on `Dans-MacBook-Pro` (Claude Code **2.1.165**) — Mode A but compressed to one cell because the prior-day heredoc+pipe matrix had already established Family 3's existence and pattern. **Origin:** Dan-reported real-world weirdo (INCOMING 2026-06-05, the second 2026-06-05 entry — `mkdir && mv … {a,b}__…run{1,2,3}.json … && ls …`). The curator's PRIMARY hypothesis on that report — "Family-3 static-analysis bail on brace expansion" — was tested with the minimal-shape probe `ls /tmp/{a,b}` (allow-listed verb via `Bash(ls *)`, single segment, no chain, no quotes, no heredoc, no redirect, no pipe, two single-char alternatives — every possible co-factor stripped out). Dan reported the result: **PROMPT**, with the matcher's reason text named as **"Brace expansion"** in the prompt UI. One probe was enough — the shape contains nothing else the matcher could possibly flag, so brace expansion is the trigger by construction.

**Interpretation:** Bash brace expansion produces a runtime-determined set of paths (`{a,b}` → `a b`, `{1..5}` → `1 2 3 4 5`, cross-products `{a,b}{1,2}` → `a1 a2 b1 b2`). The matcher parses the command with tree-sitter-bash and can detect the brace-expansion AST node, but **cannot statically enumerate the resulting paths without running the shell** — so it bails. This is the same architectural shape as the heredoc+pipe/redirect bail (also 2026-06-05): the matcher refuses to auto-approve when it can't statically bound the command's effect.

**Family classification — Family 3, second row.** Distinct from Family 1 (lexical byte-pattern scans like brace+quote, `\n#`) and Family 2 (path-aware semantic reasoning like `find`-ancestor, `cd && git`). Today's matcher reason-text ("Brace expansion") is shorter than the heredoc+pipe form ("Contains shell syntax (X) that cannot be statically analyzed") but matches the same family architecturally: structural/grammatical bail on an unbounded-effect construct.

| Heuristic (matcher-reported) | Trigger | Context | Handled by |
|---|---|---|---|
| "Contains shell syntax (file_redirect) that cannot be statically analyzed" | `>`/`2>`/`2>&1` co-occurring with a heredoc | command has `<<` heredoc | `block_heredoc_with_pipe_or_redirect.py` |
| "Contains shell syntax (pipeline) that cannot be statically analyzed" | `\|` co-occurring with a heredoc | command has `<<` heredoc | `block_heredoc_with_pipe_or_redirect.py` |
| **"Brace expansion"** | `{a,b}`, `{1,2,3}`, `{1..5}`, `{a..z}`, multi-group cross-products | unquoted shell-argument position | **`block_brace_expansion.py`** |

**Falsification of alternative hypotheses (recorded for posterity, from the INCOMING entry's hypothesis stack):**
- ~~(1b) Multi-group cross-product is the trigger~~ — falsified. Single brace group `{a,b}` triggers.
- ~~(1c) Hyphens/dots in alternative contents (`{claude-opus-4-7,gpt-5.2-…}`) are the trigger~~ — falsified. Single-char alternatives `{a,b}` triggers.
- ~~(2) `Bash(mv *)` glob doesn't span the literal `{`/`,`/`}` — verb-specific glob-tokenization failure~~ — falsified. `Bash(ls *)` exhibits the same behavior; the bail is verb-agnostic.
- ~~(3) Chain context is required~~ — falsified. Single-segment `ls /tmp/{a,b}` (no chain) still triggers.
- ~~(Family-1 lexical-only) Byte-pattern scan for `{<word>,<word>...}`~~ — not falsified by this single probe, but the matcher's reason text "Brace expansion" names the *grammar construct* (consistent with Family 3's structural bail family), not a "potential obfuscation" message (which is how Family 1 heuristics phrase themselves — e.g. "brace with quote character (expansion obfuscation)", "Newline followed by # inside a quoted argument can hide arguments from path validation"). The naming convention places this in Family 3.

**Impact on the hook / work-line:**
- **`block_bash_chains.py`:** none. The original weirdo (a three-segment `&&` chain) is all-blanket (`mkdir`/`mv`/`ls`) and per Plan 01 (FINDINGS 2026-06-04 / 2026-06-05) the chain hook deliberately lets it through. The matcher then hits the brace expansion in mid-segment. This is the **first observation of an all-blanket chain reaching a matcher prompt since the Plan 01 redesign** (mid-segment Family-3 bail). The chain hook is working as designed; the new brace-expansion hook is the correct layer to catch this.
- **New hook shipped: `claude-hooks/block_brace_expansion.py`** (Strategy 2, sibling of `block_heredoc_with_pipe_or_redirect.py`). Detection: regex `(?<!\$)\{[^{}\s]*(?:,|\.\.)[^{}\s]*\}` after stripping heredoc bodies and quoted/substituted regions. Negative lookbehind for `$` excludes parameter expansion. No-whitespace-inside requirement matches bash's own rule (bash doesn't expand `{a, b}` with a space) and excludes code blocks `{ cmd; }`. `,`-or-`..`-required excludes find placeholders `{}`. False-positive guards verified by 33-case test (`test_block_brace_expansion.py`): code blocks, function bodies, parameter expansion (with comma in default value), find placeholders, quoted braces (single + double), Python set/dict literals in heredoc bodies (stripped pre-scan). Wired via `ensure_block_brace_expansion_hook()` in `update_claude_permissions.py`; `install.sh` symlink section added; `chmod +x` confirmed by `test_hooks_executable.py`. Full dotfiles regression: 108/108 green. Live fire-test: `ls /tmp/{a,b}` re-run in this session hard-denies with the nastygram.
- **Nastygram strategy:** routes Claude to **separate Bash tool calls per expanded path** (cwd persists across calls). For `mv /p/{a,b}.txt /dest/` that's two separate `mv` calls. Common-prefix glob (`/p/*.txt`) noted as an alternative when applicable; complex cross-products (the wild-prompt's 6-path shape, two non-prefix-sharing model names × three runs) point at Write-then-run with a shell script. **The hook does NOT recommend `for f in a b c; do mv "$f" dest/; done`** because that's flow-control which `block_bash_chains.py` skips (so it'd reach the matcher) and the matcher might flag for unrelated reasons — separate Bash calls are cleaner.
- **STRATEGIES.md:** updated with item #5 in the Write-then-run/Strategy-2 list — brace expansion is the second Family-3 trigger after heredoc+pipe/redirect.
- **Allow rules:** no fix possible — structural static-analysis bail is pre-allow-list (same class as Family 1/2 built-ins and the heredoc+pipe bail).

**Confidence:** High. The minimal-shape probe `ls /tmp/{a,b}` strips out every conceivable co-factor (no chain, no quote, no heredoc, no redirect, no pipe, allow-listed verb, single-char alternatives, two alternatives only); the matcher prompted; the prompt UI text named "Brace expansion." There is nothing else in the command for the matcher to be reacting to. Single-probe sufficiency is justifiable here only because the prior heredoc+pipe matrix had already established Family 3's existence and naming convention — without that scaffolding, the prudent path would have been a fuller cross-product (e.g. `ls /tmp/{a,b}` × `ls /tmp/{a..c}` × `ls /tmp/{a,b,c}` × `mv /tmp/{a,b} /dest/`) to discriminate range-vs-comma, alternative-count, verb-sensitivity. Those discriminations are nice-to-have but not load-bearing for the hook's correctness — the regex covers all three brace-expansion forms (`{a,b}`, `{1..5}`, `{1..10..2}`) and is verb-agnostic by construction.

**Generalizable lesson:** **When a matcher reason-text names a grammar construct (here "Brace expansion") rather than a misuse pattern (Family 1 phrasings like "expansion obfuscation" or "can hide arguments from path validation"), suspect Family 3 first.** Family 3 entries name the AST node (`file_redirect`, `pipeline`, brace expansion); Family 1 entries name the misuse heuristic. The naming convention is a useful diagnostic shortcut — it tells you in advance whether the bail is structural (no allow-rule fix possible, Strategy 2) or lexical (still no allow-rule fix, but the threat model is different).

## 2026-06-05 — Static-analysis bail: a heredoc co-occurring with a pipeline OR an extra redirect prompts ("file_redirect"/"pipeline" cannot be statically analyzed) — NEW Family 3

**Methodology:** Mode A HITL probe in active session on `Dans-MacBook-Pro` (Claude Code **2.1.165**). `block_bash_chains.py` **NOT neutered** this round — by design: none of the 12 probes contain `&&`/`||`/`;` (the one pipe is a single `|`, which `CHAIN_RE = &&|\|\||;` does not match), so the hook short-circuits on every probe and the matcher is the sole decision-maker. This avoids the standing hazard of forgetting to re-enable a disabled safety hook. HITL signal via `AskUserQuestion` after each batch (the canonical channel per the 2026-06-05 methodology revision); two reason-texts captured verbatim by Dan copy/pasting from the prompt UI.

**Origin:** Dan-reported real-world weirdo (INCOMING 2026-06-05) — `uv run python - <<'PY' … PY 2>&1 | grep -v VIRTUAL_ENV` prompted with *"Contains shell syntax (file_redirect) that cannot be statically analyzed."* Initial hypothesis (recorded in INCOMING then **falsified by this probe**): the `2>&1` redirect was the trigger.

**Results — 12-cell matrix (heredoc × extra-redirect × pipe):**

| # | Command shape | heredoc | extra redirect | pipe | Result | Reason text (verbatim) |
|---|---|:--:|:--:|:--:|---|---|
| P0 | `echo X` | — | — | — | silent | — |
| P1 | `echo X 2>&1` | — | ✓ | — | **silent** | — |
| P2 | `echo X 2>/dev/null` | — | ✓ | — | silent | — |
| P3 | `echo X > /tmp/f` | — | ✓ | — | silent | — |
| P4 | `cat <<'PY' … PY` | ✓ | — | — | silent | — |
| P5 | `echo X 2>&1 \| grep X` | — | ✓ | ✓ | **silent** | — |
| P6 | `python3 - <<'PY' … PY` | ✓ | — | — | silent | — |
| P7 | `python3 - <<'PY' 2>&1 … PY` | ✓ | ✓ | — | **PROMPT** | "…shell syntax (file_redirect)…" |
| P8 | `python3 - <<'PY' \| grep … PY` | ✓ | — | ✓ | **PROMPT** | "…shell syntax (pipeline)…" |
| P9 | `python3 - <<'PY' 2>&1 \| grep … PY` | ✓ | ✓ | ✓ | **PROMPT** | "…shell syntax (file_redirect)…" |
| P10 | `python3 - < /tmp/f.py \| grep` | — | ✓ (`<` stdin) | ✓ | **silent** | — |
| P11 | `python3 /tmp/f.py 2>&1 \| grep` | — | ✓ | ✓ | silent | — |

**Interpretation — necessary-and-sufficient condition:**

> The matcher refuses to statically analyze (→ prompts on) a command where a **heredoc co-occurs with a pipeline OR an additional (non-heredoc) redirect**. Heredoc alone → analyzable, silent. Pipeline and/or redirect *without* a heredoc → analyzable, silent. The prompt names the **co-occurring construct** (`pipeline` or `file_redirect`), not the heredoc.

Single-variable flips make the attribution clean:
- **P6 → P7** (add only `2>&1`): silent → PROMPT "file_redirect". Redirect is the co-factor.
- **P6 → P8** (add only a pipe): silent → PROMPT "pipeline". Pipe is the co-factor.
- **Heredoc is the necessary ingredient**, triangulated three ways: **P5** (`2>&1` + pipe, no heredoc) silent, **P10** (`<`-stdin-from-file + pipe, no heredoc) silent, **P11** (`2>&1` + pipe on a file-based run, no heredoc) silent. A `<` *file* stdin-redirect does NOT count — so the trigger is the **heredoc (`<<`) specifically**, not stdin-redirection in general (P10 is the discriminator: `heredoc_redirect` vs `file_redirect` for `<` differ to the matcher).

**Mechanism (best read):** the matcher parses commands with a real shell grammar — the reason-text node names (`file_redirect`, `pipeline`; heredocs are `heredoc_redirect`) are exactly **tree-sitter-bash** node types. It silently allows commands whose full effect it can statically bound. A heredoc body is a consumed multi-line block; once the heredoc-bearing command is embedded in a pipeline or carries additional fd-routing, the analyzer apparently can't reconcile the heredoc-body boundary with the surrounding I/O and bails, requiring manual approval. The reason text reports the *enclosing* construct it choked on.

**Family classification — NEW Family 3: static-analysis bail-outs (structural/grammatical).** Distinct from Family 1 (lexical byte-pattern scans like brace+quote, `\n#`) and Family 2 (path-aware semantic reasoning like `find`-ancestor, `cd && git`). Family 3 reasons about the command's **AST shape** and refuses constructs whose combined effect it can't statically resolve.

| Heuristic (matcher-reported node) | Trigger | Context | Handled by |
|---|---|---|---|
| "Contains shell syntax (file_redirect) that cannot be statically analyzed" | a `>`/`2>`/`2>&1` file_redirect **co-occurring with a heredoc** | command also contains a `<<` heredoc | Write-then-run (removes the heredoc) |
| "Contains shell syntax (pipeline) that cannot be statically analyzed" | a `\|` pipeline **co-occurring with a heredoc** | command also contains a `<<` heredoc | Write-then-run (removes the heredoc) |

**SECONDARY finding (incidental, but it kills a long-running hypothesis): a bare trailing redirect on an allow-listed verb does NOT prompt.** P1 (`echo X 2>&1`), P2 (`echo X 2>/dev/null`), P3 (`echo X > /tmp/f`) all silent. This **falsifies the "redirect-tokenization breaks the `Bash(verb *)` glob" hypothesis** that has been the leading suspect across multiple INCOMING entries since 2026-06-01 (the original `find … 2>/dev/null`, the 2026-06-04 `head … > slice`, etc.). Redirects alone are fine. The earlier redirect-blamed weirdos therefore had *other* causes — `find`-ancestor (path-aware, 2026-06-01), real-Python-interpreter-path (issue #65433, 2026-06-04 `ls … 2>&1`), tilde-not-expanded (2026-06-02 `install.sh`), or the cd-compound built-in (2026-06-04 `head>slice`). **Do NOT cross-link those to this Family-3 finding as a "unifying mechanism" — they have no heredoc and this heuristic requires one.** (Correcting an overstatement in the INCOMING 2026-06-05 draft.)

**Impact on the hook / work-line:**
- **`block_bash_chains.py`:** none. Single pipe isn't a chain op; heredocs without `&&`/`||`/`;` short-circuit. No change.
- **`block_brace_quote_heredoc.py`:** orthogonal. That hook fires on heredoc *bodies* containing `{"`/`['` patterns; this heuristic fires on heredoc + pipe/redirect regardless of body content. A heredoc can be brace-quote-clean (slip past that hook) and still matcher-prompt via Family 3. No change needed.
- **New hook?** ~~No. Write-then-run is a *complete* dodge (it eliminates the heredoc), and the file-based replacement may keep its pipe/redirect tail freely (P11). Strategy 0.~~ **Superseded 2026-06-05 — Strategy-2 hook added.** Dan decided the soft-prompt click-through warranted a hard-fail (same Strategy 0→2 escalation as the brace-quote and `\n#` siblings). Shipped `claude-hooks/block_heredoc_with_pipe_or_redirect.py` (Plan `plans/02_block_heredoc_with_pipe_or_redirect.md`): fires on a `<<` heredoc co-occurring with a pipe/redirect **on the heredoc's command (open) line**, leaving plain heredocs and heredoc bodies that merely contain `|`/`>`/`<` untouched. **Detection-boundary correction to the plan:** the plan's DENY case #4 (`… PY | grep x`, "pipe after the close delimiter") is bash-MALFORMED — verified live (`bash` run) that `PY | grep x` is not a valid delimiter line, so the `| grep x` is heredoc *body*, not a pipe; the plan's own architecture (strict close regex `^\s*DELIM\s*$`) couldn't match it either. The only bash-valid place a pipe/redirect binds to a heredoc command is the open line (where every confirmed probe P7/P8/P9 + the real-world weirdo put it), so the hook scans only that and treats case #4 as ALLOW. Wired via `ensure_block_heredoc_with_pipe_or_redirect_hook()` + `install.sh` + `chmod +x`; 16-case behavior suite (incl. the two CRITICAL false-positive guards) + 4-case ensure-hook characterization test; fresh-session fire-test confirmed via a real Bash tool call (trigger hard-denied, plain heredoc ran).
- **STRATEGIES.md:** ~~add a concrete line~~ **done (item #4 in the Write-then-run list, updated to note the Strategy-2 hook).** *A heredoc combined with a pipe or a redirect prompts ("…cannot be statically analyzed"); Write-then-run removes the heredoc and the prompt, and the file-based command can keep its `… 2>&1 | grep …` tail.* Sharpens the Write-then-run guidance with a fourth, structural reason (alongside brace+quote, `\n#`, `;`-tokenization).
- **Allow rules:** no fix possible — a structural static-analysis bail is pre-allow-list, not `Bash(...)`-overridable (same class as Family 1/2 built-ins).

**Confidence:** High. 12-cell matrix with single-variable flips isolating heredoc as necessary and pipe/redirect as the sufficient co-factor; two distinct verbatim reason-texts confirming precise per-construct naming; P5/P10/P11 independently triangulating the heredoc-necessity from three directions. Caveat per the work-line's standing premise: matcher behavior drifts; the `file_redirect`/`pipeline` reason-texts are new as of 2.1.165 and may evolve. Not probed: heredoc + `&&`/`||`/`;` chain (masked by `block_bash_chains.py` anyway); whether `<<<` herestrings behave like `<<` heredocs; whether the bail also fires for heredoc + `&&`-joined commands at the matcher level.

**Generalizable lesson:** when a self-naming matcher diagnostic blames a specific construct (here `file_redirect`), **don't assume that construct is the trigger in isolation — build the full presence/absence matrix.** The named node (`file_redirect` = the `2>&1`) was a *co-factor*, not the cause; the actual necessary ingredient (the heredoc) is never named in the prompt. A one-probe "is it the 2>&1?" check (P1) flipped the entire hypothesis on the first cell.

**Side-confirmation (same session) — the `\n#`-in-quoted-arg heuristic (Family 1, 2026-06-01) is STILL LIVE in CC 2.1.165, and `block_newline_hash_in_quoted_arg.py` is validated as not-redundant.** Triggered by Dan asking whether heredoc-as-workaround had become self-contradictory. Two probes: (PB) `python3 <<'PY' …# comment… PY` with NO pipe/redirect → silent — heredoc still dodges the `\n#` heuristic (code lives in stdin, not a quoted arg), so the `notes/python_dash_c_alternatives.md` heredoc workaround still works *for its original purpose*; today's Family 3 is an orthogonal, newer trap that only fires when a pipe/redirect is added on top. (PA) `python3 -c "…\n# comment…"` → our `block_newline_hash_in_quoted_arg.py` hard-failed it (nastygram → Write-then-run). Neutered that hook for one probe (A2): the matcher prompted with the verbatim *"Newline followed by # inside a quoted argument can hide arguments from path validation"* — so the upstream heuristic is **not** fixed in 2.1.165; the hook correctly converts a still-live soft-prompt to a hard-fail. Hook restored byte-identical via single-file `git checkout`. Net: three distinct dodges for embedded-code-with-comments — heredoc (works, but don't pipe/redirect → Family 3), and Write-then-run (works for everything incl. a `… 2>&1 | grep` tail). Per Dan, heredoc stays the documented one-shot preference; the Family 3 caveat is rare enough not to disturb the ranking.

## 2026-06-04 — Per-segment checking confirmed across `&&`, `;`, `|`; symmetric in segment order

**Methodology:** Mode A HITL probe in active session on Dans-MacBook-Air.local (Claude Code 2.1.150). `block_bash_chains.py` neutered with `sys.exit(0)` at top of `main()` for the duration; restored at end. Probe labels written into the Bash tool-call `description` field; Dan typed the probe label into the prompt-approval comment when prompted (silence = matcher allowed). This HITL signalling convention is the load-bearing protocol detail — added to METHODOLOGY.md step 4 the same session after Claude initially missed the comment-channel signal.

**Results — 8 probes:**

| # | Command | Separator | Shape | Result |
|---|---|---|---|---|
| 1 | `date` | — | single allowed | ALLOW |
| 2 | `date && hostname` | `&&` | allowed + allowed | ALLOW |
| 3 | `echo a && echo b` | `&&` | allowed + allowed | ALLOW |
| 4 | `mkdir -p /tmp/probe_chain_2026-06-04 && touch /tmp/probe_chain_2026-06-04/x` | `&&` | allowed + allowed | ALLOW |
| 5 | `date && unknownmarker_2026-06-04` | `&&` | allowed + **unknown** | **PROMPT** |
| 6 | `date ; hostname` | `;` | allowed + allowed | ALLOW |
| 7 | `unknownmarker_2026-06-04_b && date` | `&&` | **unknown** + allowed | **PROMPT** |
| 8 | `date \| grep Jun` | `\|` | allowed + allowed | ALLOW |

Not tested today: `||` (logical OR). Assumed to behave like `&&` based on historical consistency; flagged for a future probe if friction surfaces.

**Interpretation:** The matcher splits commands on `&&`, `;`, and `|` (and presumably `||`) into segments, checks each segment's leading verb against the allow list, and prompts iff any segment's verb has no blanket rule. Symmetric in segment order (probes 5 + 7). Single-pipe `|` is treated identically to other chain operators (probe 8).

**Refutes the 2026-06-01 "Mixed" verdict** — that session's prompts on every command were not matcher behavior but a settings-loading failure (`--setting-sources project` didn't load the probe's `settings.json`). The 2026-05-30 per-segment hypothesis stands; today is the second consecutive positive data point, satisfying the work-line's "design from corpus, not snapshot" precondition for a hook redesign.

**Confidence:** High. 8-cell probe map is internally consistent under per-segment-checking; the symmetric-prompt cells (5 + 7) directly falsify any order-asymmetric model; the multi-separator cells (6 + 8) directly falsify any `&&`-only model. The HITL labeling protocol made each cell's prompt/silence outcome cleanly attributable.

**Impact on the hook:** `block_bash_chains.py` is over-blocking — probes 2, 3, 4, 6, 8 would all be hard-failed by the current hook despite the matcher silently allowing them. The 5/30 "single session, don't redesign" caveat is now resolved. Redesign approved with the following scope (settled with Dan same session):

- **Source of truth:** `update_claude_permissions.py` `ALLOW_RULES` → derive `BLANKET_VERBS` (rules of shape `Bash(<verb> *)`, no path/argument constraints) → codegen into a file the hook imports → `install.sh` keeps it fresh.
- **Chain-op scope:** `&&`, `||`, `;` (no change from current `CHAIN_RE`). Single-pipe `|` deliberately not added (pipes are a different cognitive category; revisit if INCOMING.md surfaces pipe weirdos).
- **Behavior:** every chain segment's leading verb in `BLANKET_VERBS` → pass through (matcher will silently allow); any segment without → hard-fail with updated NASTYGRAM explaining "split into separate Bash calls."
- **Existing exceptions stay:** `CD_CODE_RE` / `CD_TMP_RE` / `ENV_PREFIX_RE` prefix logic, `CD_GIT_RE` defer to block_cd_git.py, `FLOW_CONTROL_RE`, `HEREDOC_RE`. Blanket-verb logic layers on top.
- **Hook still load-bearing.** Per Dan: "the training data bites hard, and until I put the hook in you would do ten chains IN A ROW." The redesign reduces friction on legitimate all-blanket chains; it does NOT abandon the train-Claude-to-split-into-separate-calls mandate for mixed chains.

**Generalizable lesson:** **Build the HITL signalling protocol explicitly into METHODOLOGY before the next probe.** The 6/4 probe nearly produced corrupted data because Claude treated absence-of-prompt-label as "ALLOW" without realizing Dan was using the prompt-approval comment field as the channel — a channel the tool-result format hides entirely. Labelling probes in the tool-call `description` field + Dan-echoes-label-in-approval-comment closes the loop. This goes wrong in subtle ways across sessions; making it step 4 of METHODOLOGY (load-bearing, explicit) prevents the silent miscount.

## 2026-06-05 — Plan 01 implementation verified end-to-end; comment-channel HITL signal didn't round-trip

**Methodology:** Mode A HITL re-probe in active session on Dans-MacBook-Air.local (Claude Code 2.1.150). 4-cell matrix: hook neutered then restored × all-blanket-chain vs. mixed-chain. Probe labels in tool-call `description` field per METHODOLOGY step 4.

**Results — 4 probes:**

| # | Hook | Command | Expected | Actual |
|---|---|---|---|---|
| HITL-A1 | neutered | `date && hostname` | silent ALLOW (matcher allows) | ALLOW, silent ✓ |
| HITL-A2 | neutered | `date && unknownmarker_HITL_A2_2026-06-05` | MATCHER PROMPT | PROMPT ✓ (confirmed via AskUserQuestion after the comment-channel signal didn't arrive) |
| HITL-B1 | restored | `date && hostname` | hook pass-through, matcher allows, silent | ALLOW, silent ✓ |
| HITL-B2 | restored | `date && unknownmarker_HITL_B2_2026-06-05` | HOOK DENY with new NASTYGRAM | DENY ✓ (NASTYGRAM delivered verbatim in tool result, no shell execution) |

**Interpretation:**

- **Plan 01 implementation is empirically verified.** The redesigned `block_bash_chains.py` correctly (a) passes through all-blanket chains the matcher silently allows — fixing the over-blocking the redesign was motivated by, and (b) hard-fails mixed chains with the new NASTYGRAM, preserving the train-Claude-to-split-into-separate-calls mandate Dan called load-bearing.
- **Third consecutive positive data point for per-segment matcher behavior** (5/30 + 6/4 + 6/5). Confidence in the per-segment model upgrades from "high" to "very high — surviving three independent sessions across a week."

**Methodology revision — comment-channel HITL signal isn't reliable in current Claude Code.** METHODOLOGY § Mode A step 4 (load-bearing as of 6/4) says: "When Dan gets a prompt, he clicks Yes and types the probe label verbatim in the comment field. That comment arrives in Claude's next turn as a user message — that's the only reliable channel by which a prompt event becomes visible to Claude."

On HITL-A2 today, Dan got prompted, approved, AND typed "A2" (abbreviated form of HITL-A2) in the comment field — but no user message containing that label arrived in Claude's next turn. The tool result was identical to a never-prompted run. Verified via `AskUserQuestion` immediately after the probe: Dan confirmed he was prompted and confirmed he typed the label. So the comment channel itself didn't deliver.

Two possibilities: (a) Claude Code changed the comment-channel mechanism between 6/4 and 6/5, (b) the 6/4 METHODOLOGY entry was written from an incomplete observation and the channel was never as reliable as it claimed. Either way, the operational consequence is the same: **`AskUserQuestion` after each ambiguous-outcome probe is the canonical HITL signal going forward.** METHODOLOGY § Mode A step 4 is being rewritten accordingly.

**Confidence:** High for the implementation verification (all 4 cells matched expectation; the NASTYGRAM appeared verbatim — code path proven). High for the comment-channel methodology revision (Dan directly verified the protocol slip via AskUserQuestion; same-session evidence).

**Impact on the work-line:**
- Plan 01 Phase 3 success criterion met; Phase 4 (commit + push) is the only remaining work. Phases 1 + 2 already committed (5c48792, 0374f66).
- METHODOLOGY § Mode A step 4 to be rewritten: drop the comment-channel-as-primary-signal claim; promote `AskUserQuestion` to the canonical HITL signal.
- INCOMING.md / future weirdo triage: if a comment-channel signal seems to arrive in some future session, treat that as evidence Claude Code's behavior shifted again, not as the default model.

**Generalizable lesson:** **HITL protocols are themselves brittle** — they depend on the harness's choice of how prompt-comment-fields connect to model context, which the work-line doesn't control. Don't bake any single channel into METHODOLOGY as "load-bearing" without also baking in a verification step (here: `AskUserQuestion` on ambiguity). The 6/4 entry got this wrong by promoting the comment channel to load-bearing without an escape hatch; this entry corrects that with the AskUserQuestion-verify-on-ambiguity escape hatch.

---

## 2026-06-04 (Plan 01 implementation session, later) — Built-in blanket verbs distinct from ALLOW_RULES

While implementing Plan 01 Phase 1, the `test_real_allow_rules_smoke` test surfaced that `date` and `hostname` (used in probes 1, 2, 5, 6, 7) are **NOT** in `ALLOW_RULES` — yet the matcher silently allowed both as single commands AND as chain segments. Two possibilities:

- **A:** Claude Code has a built-in "always-allowed" set of read-only / harmless verbs (`date`, `hostname`, likely others) that operate independently of user `permissions.allow` rules.
- **B:** The 6/4 probe table's "allowed + allowed" labels were sloppy shorthand for "matcher-allowed" rather than "in ALLOW_RULES."

Story A is consistent with all 8 probe cells (the per-segment-checking conclusion stands either way) AND with probe 4's use of `mkdir`/`touch` (which ARE in ALLOW_RULES) — the matcher allows both classes uniformly.

**Conclusion:** The set of verbs the matcher silently allows is a SUPERSET of `derive_blanket_verbs(ALLOW_RULES)`. For the hook redesign to actually stop over-blocking `date && hostname`, BLANKET_VERBS must include the built-in verbs too.

**Decision (Dan, this session):** Hardcode a `BUILTIN_BLANKET_VERBS` set in `update_claude_permissions.py` rather than re-probing to enumerate. Start conservative — only the empirically-witnessed verbs (`date`, `hostname`) — and grow as INCOMING reports surface more. Re-probe is reserved for when a specific weirdo can't be explained by the current model.

This adds one new axis the work-line tracks: the matcher's built-in-allowed verb set, distinct from user `permissions.allow`. Future findings on built-in verbs land here; the hardcoded `BUILTIN_BLANKET_VERBS` in `update_claude_permissions.py` is the operational consequence.

**Impact on Plan 01:** the codegen pipeline becomes `derive_blanket_verbs(ALLOW_RULES) | BUILTIN_BLANKET_VERBS` → `_blanket_verbs.py`. Plan 01 addendum recorded inline at the plan file.

---

## 2026-06-01 — Path-aware matcher heuristic: `find` against strict-ancestor-of-cwd outside trusted roots prompts despite `Bash(find *)`

**Methodology:** HITL A/B probe by Dan on 2026-06-01 in dotfiles workspace (cwd `~/code/dotfiles`). Originating observation: `find /Users/dan -maxdepth 3 -name ".env.<CLIENT>" 2>/dev/null` prompted despite `Bash(find *)` being on the allow list. Initial hypothesis was trailing-redirect tokenization (mirroring the 2026-05-30 semicolon-split bug); the A/B probe falsified that and surfaced a different mechanism.

**Results — five-point path A/B map:**

| Path argument | Prompted? | Relationship to cwd (`~/code/dotfiles`) |
|---|---|---|
| `/tmp/...` | no | explicitly-allowed scratch dir |
| `/Users/dan/code/...` | no | ancestor-of-cwd inside `~/code` |
| `/Users/dan/Documents` | no | sibling of cwd subtree, inside `$HOME`, OUTSIDE `~/code` |
| `/Users/dan` | **yes** | strict ancestor of cwd (home root) |
| `/Users` | **yes** | further-up ancestor |

**Falsified hypotheses during the probe:**
- `2>/dev/null` redirect breaking the glob match — `find /tmp -name x 2>/dev/null` ran silent; redirect is not the trigger.
- `.env*` pattern triggering a secrets-protection heuristic — `find /tmp -name ".env.<CLIENT>"` ran silent; filename pattern is not the trigger.

**Interpretation:** Claude Code's matcher has a path-aware heuristic on `find` that prompts when the target path is a **strict ancestor of cwd outside trusted roots** (`/tmp`, `~/code`). Sibling/descendant paths inside `$HOME` but outside the cwd subtree (`~/Documents`) do NOT trip it. This is the same architectural shape as the `cd <path> && git <subcmd>` heuristic — hardcoded in Claude Code, not overridable by allow rules.

The security-coherence story is internally consistent: `find /Users/dan` expands file-scope to all of `$HOME` (including `Library/`, `.ssh/`, browser profiles), whereas `find /Users/dan/Documents` is bounded to a single sibling subtree. Broaden-the-scope-above-cwd is exactly the access pattern most likely to inadvertently scan sensitive directories. Prompting on it is engineering-sensible default behavior.

**Confidence:** Medium-high. Five-point A/B map is clean, two competing hypotheses systematically falsified, the surviving hypothesis predicts the observed cells. Not yet probed: (a) whether the heuristic generalizes to other tools that take a path argument (`grep -r`, `rg`, `du`, `tree`), (b) whether moving cwd to `/Users/dan/Documents` would make the descendant-side cells flip, (c) whether the trusted-root set is exactly `{/tmp, ~/code}` or includes more (`/var`?, `~/data`?). Worth folding into the next probe pass.

**Heuristic family — NEW table (not a row in the anti-obfuscation table).** This is the first member of a distinct architectural family from the lexical anti-obfuscation heuristics. Splitting into two tables to keep the families straight:

### Family 1: Lexical anti-obfuscation heuristics (byte-pattern scans on command strings)

| Heuristic name (as reported by matcher) | Trigger pattern | Context where fires | Handled by |
|---|---|---|---|
| "Contains brace with quote character (expansion obfuscation)" | `{"..."` / `["..."` (brace/bracket immediately followed by quote) | bash-unquoted contexts, including heredoc bodies | `block_brace_quote_heredoc.py` (Strategy 2) for heredoc case; Write-then-run for `-c` case |
| "Newline followed by # inside a quoted argument can hide arguments from path validation" | `\n#` followed by content | inside `-c "..."` quoted body | Write-then-run (no hook currently) |
| (un-named so far) `;` tokenization inside `-c "..."` | `;` inside quoted body | inside `-c "..."` quoted body | Write-then-run (no hook currently) |

### Family 2: Path-aware heuristics (semantic reasoning about path arguments relative to cwd / trusted roots)

| Heuristic | Trigger | Context | Handled by |
|---|---|---|---|
| `find` against strict-ancestor-of-cwd outside trusted roots | path arg is a strict ancestor of cwd, AND path is outside `/tmp` and `~/code` | bare `find <path> ...`, single segment, allow rule clean | Accept the prompt (engineering-sensible default); no hook recommended |
| `cd <path> && git <subcmd>` bare-repo-attack prevention (Claude Code hardcoded) | `cd <path> && git <subcmd>` pattern | any chain with this shape | dotfiles upgrades the soft-prompt to hard-fail via `block_cd_git.py` (DENY) to break the habit; canonical alternative `git -C <path> <subcmd>` matches `Bash(git *)` cleanly |

These families are likely to keep growing independently. When a new heuristic surfaces, classify by mechanism (byte-pattern scan vs path-semantic reasoning vs something else) and add a row to the appropriate table or open a new family.

**Impact on the hook / work-line:**
- **`block_bash_chains.py`:** none. Single-segment command, no chain operators.
- **`block_cd_git.py`:** none. Different pattern.
- **New hook?** No. The prompt-then-approve flow on broad-scope `find` is engineering-sensible — Dan can approve when legitimate (genuinely scanning home for a config file) and the friction trains away from unnecessarily broad scans. A Strategy 2 hook would only be warranted if Dan wants hard-fail to force a workflow change (e.g., always require a narrower path or `--prune` flags), which doesn't seem justified at current prompt frequency.
- **STRATEGIES.md:** no change needed. The "default to Write-then-run" guidance addresses the lexical anti-obfuscation family; this family has a different workaround (scope to subtrees under cwd, or accept the prompt).

**Generalizable lesson:** When a single-segment command with a clean allow rule prompts, before assuming the matcher is doing something lexically weird with the command string, **run a path A/B map** — the matcher may be reasoning about the *semantics* of path arguments, not the *syntax* of the command. Cheap discriminator: vary only the path argument across `/tmp`, `~/code/<some subdir>`, a sibling `$HOME` subtree, `$HOME` itself, and `/`. Different prompt-outcomes across that map = path-aware heuristic; uniform prompt-outcomes = lexical heuristic; mixed = something else.

---

## 2026-06-01 — Matcher heuristic `\n#`-in-quoted-arg confirmed; matcher named the heuristic in the prompt UI

**Methodology:** Single real-world observation by Dan in `lobby_analysis` workspace. Standard `~/.claude/settings.json` permissions. Claude session ran `uv run python -c "<python body with a \n# Python comment line in it>"`. Matcher prompted; the prompt UI included a diagnostic message naming the heuristic verbatim:

> **"Newline followed by # inside a quoted argument can hide arguments from path validation"**

This is the **second time** Claude Code has surfaced an internal heuristic name in a prompt (first: brace+quote, "Contains brace with quote character (expansion obfuscation)"). It's strong direct evidence — no inference needed about what the matcher was reacting to.

The triggering substring was a Python source comment inside the `-c` body:

```
# For the 3-3 split rows in lobbyist_spending_report, find: is the split CLAUDE-vs-GPT, or run-vs-run?
```

Preceded by an end-of-line (i.e. `\n#` in the command-string-as-bytes the matcher scans). Inside a `-c "..."` quoted argument.

**Interpretation:** The matcher has a `\n#`-in-quoted-arg anti-obfuscation heuristic. The threat model is presumably: a path-validation pass that interprets `#` as bash-comment-start could be tricked by `\n# malicious args` sequences buried in quoted arguments. Conservative scope: applies bash-lexical reasoning to the **contents** of `-c "..."` where the body's actual language (Python here, but same applies to jq, awk, perl, etc.) gives `#` different semantics. False positives on ordinary code comments are by-design — the matcher prefers over-prompting to under-blocking on a security heuristic.

This **confirms** a prior partially-known conjecture documented inline at `update_claude_permissions.py` line 430 ("`\n#` patterns in quoted `-c` bodies also trigger prompts"). That note was based on Dan's historical observation but had not been re-verified in current Claude Code; it was tagged in 2026-05-30 FINDINGS as "yet-unconfirmed" and "may have been retired between dotfiles' doc writing and 2026-05-30." Today's observation re-confirms it is still live.

**Confidence:** High. Matcher named the heuristic itself; no inference about what triggered the prompt is required.

**Family membership.** This makes **three named anti-obfuscation heuristics**, all in the same family — bash-lexical scans applied to command strings whose quoted regions are non-bash code:

| Heuristic name (as reported by matcher) | Trigger pattern | Context where fires | Handled by |
|---|---|---|---|
| "Contains brace with quote character (expansion obfuscation)" | `{"..."` / `["..."` (brace/bracket immediately followed by quote) | bash-unquoted contexts, including heredoc bodies | `block_brace_quote_heredoc.py` (Strategy 2) for heredoc case; Write-then-run for `-c` case |
| "Newline followed by # inside a quoted argument can hide arguments from path validation" | `\n#` followed by content | inside `-c "..."` quoted body | Write-then-run (no hook currently) |
| (un-named so far) `;` tokenization inside `-c "..."` | `;` inside quoted body | inside `-c "..."` quoted body | Write-then-run (no hook currently) |

The Write-then-run pattern (`Write('/tmp/script.py', body)` then `python3 /tmp/script.py` in separate Bash calls) sidesteps all three uniformly — no `-c`, no heredoc, no quoted body for the matcher to scan.

**Impact on the hook / work-line:**
- **`block_bash_chains.py`:** none. Not a chain matcher issue.
- **`block_brace_quote_heredoc.py`:** none. Different pattern, different context (`-c` quoted body vs heredoc body).
- **New hook?** Not this week. The redesign-after-corpus rule applies. Currently the Write-then-run workaround is documented (STRATEGIES.md updated) and the heuristic is well-understood. A dedicated `block_newline_hash_in_quoted_c_body.py` would be Strategy 2 and is warranted only if Claude sessions keep tripping this despite documentation. Re-evaluate after another 3-5 weirdos.
- **`update_claude_permissions.py:430`:** the existing inline mention is now confirmed — could be tightened to "**confirmed 2026-06-01** via matcher-surfaced heuristic name" rather than left as conjecture. Optional cleanup.

**Generalizable lesson:** When the matcher's prompt UI includes a diagnostic message that looks like a sentence (rather than just a generic "Allow this command?"), **read the diagnostic verbatim and record it in INCOMING.md verbatim** — Claude Code is increasingly self-documenting its heuristics, and the heuristic names are stable enough to pattern-match against. We now have two of them; expect more.

---

## 2026-05-31 — Hook silent-failure mode: missing `+x` on the source file

**Methodology:** HITL probe by Claude in fresh session. Dan asked the session to test `block_brace_quote_heredoc.py` by running `python3 <<'PY' / print({"test":"hook fires"}) / PY`. Expected outcome: deny-JSON nastygram from the hook. Actual: normal Claude Code permission prompt, command ran successfully.

**Results:**

| Check | State |
|---|---|
| Symlink `~/.claude/hooks/block_brace_quote_heredoc.py` → dotfiles source | present, correct target |
| Registration in `~/.claude/settings.json` PreToolUse `Bash` block | present, correct command path |
| `ensure_block_brace_quote_heredoc_hook()` in `update_claude_permissions.py` | present, idempotent, called by `install.sh` |
| Hook script logic when piped a payload directly via `cat probe.json \| ./hook.py` | returns correct deny-JSON |
| `ls -la claude-hooks/block_brace_quote_heredoc.py` | `-rw-r--r--` — **no executable bit** |
| Every other hook in `claude-hooks/*.py` (non-test) | `-rwxr-xr-x` |

**Interpretation:** Claude Code invokes registered hooks as `"type": "command"` with the command being a path to the script. The kernel resolves the symlink to the source file, then checks the executable bit on the resolved target. Without `+x` the exec fails; Claude Code apparently treats the failed exec as "no hook response" and falls back to the normal permission flow with **no visible error**. The fact that registration / symlink / logic were all correct makes this a high-cost silent failure — diagnosis took most of a session even with a fresh, focused HITL probe.

The bug entered via commit `1a6ddc1` (the original Strategy 2 commit): the source file was committed with default `-rw-r--r--` because `chmod +x` was forgotten at creation time. install.sh symlinked it, `update_claude_permissions.py` registered it, every layer looked correct.

**Impact on the work-line:**
- Fix (chmod + harden) in commit `5a4b063`. Three layers: (a) chmod the source file itself, (b) install.sh now does a defensive `chmod +x` loop over every non-test `claude-hooks/*.py` at install time, (c) `test_hooks_executable.py` asserts +x on every production hook (second line of defense against a future source file committed without +x).
- STRATEGIES.md Strategy 2 recipe updated to include `chmod +x` as a required step.

**Confidence:** High for the diagnosis (3-step probe: registration check ✅, direct-pipe to hook ✅ produces deny-JSON, mode comparison shows the asymmetry, post-chmod re-probe ✅ fires correctly). High for the fix being durable on this machine. Untested on Pro/tarragon — `git pull` + `bash install.sh` should both be needed to propagate; the test will fail loudly on either machine if either step is skipped.

**Generalizable lesson:** When a hook "should be firing but isn't" and registration looks correct, **check the +x bit on the resolved source file before anything else**. It's the cheapest test and the most likely silent failure point for a freshly-added hook. Compare `ls -la claude-hooks/*.py` against a known-working hook — asymmetry is diagnostic.

---

## 2026-05-30 — Matcher does per-segment checking (contradicts 2026-05-25)

**Methodology:** HITL probe by Claude in active session. `block_bash_chains.py` neutered (`sys.exit(0)` at top of `main()`) for the duration. Dan reported prompts as they arrived; silence = matcher allowed. See `METHODOLOGY.md`.

**Results:**

| Probe | Command | Both/all segments individually allowed? | Outcome |
|---|---|---|---|
| 01 | `touch /tmp/probe01_sanity` | n/a (no chain) | ALLOW |
| 02 | `cd /tmp && probemarker_probe02` | no — probemarker has no rule | **PROMPT** |
| 07 | `cd /tmp && touch /tmp/probe07_both_allowed` | yes — `cd /tmp *` and `touch *` | ALLOW |
| confirm | `echo probe-confirm-hook-off && echo second-segment` | yes — `echo *` covers both | ALLOW |
| 08 | `mkdir -p /tmp/probe08 && touch /tmp/probe08/x` | yes — `mkdir *` and `touch *` | ALLOW |
| 09 | `mkdir -p /tmp/probe09 && unknownmarker_probe09` | no — unknownmarker has no rule | **PROMPT** |
| 10 | `ls /tmp/probe08 \| head -3` | yes — `ls *` and `head *` | ALLOW |

**Interpretation:** The matcher splits commands on chain/pipe operators (`&&`, `\|`, at minimum) into segments and checks each segment's leading verb against the allow list. All segments allowed → entire chain allowed. Any segment unrecognized → prompt.

**Contradicts the 2026-05-25 note** (`notes/bash_chain_matching.md`), which claimed `mkdir foo && touch bar` PROMPTS even with both rules. Probe08 above is essentially that test and it ALLOWED. Either:
- The matcher was changed between 5/25 and 5/30 (most likely, given Dan's observation that "behavior keeps changing")
- The 5/25 test was misobserved (less likely — repeated multiple times in that note)
- There's a context dependency we haven't identified (e.g. only certain command pairs are per-segment; some are whole-string)

**Confidence:** Medium-high for the per-segment shape; low for "this is stable behavior." Dan's stated intuition is that the matcher is being actively iterated on by Anthropic. Re-test before relying on this.

**Impact on the hook:** As of 2026-05-30, `block_bash_chains.py` is over-blocking. It hard-fails chains that the matcher would now allow (probe07/08/10/confirm all would have been blocked by the hook had we left it enabled). The hook is currently doing zero real protection and significant friction.

**Action chosen:** Restore the hook to its 2026-05-25 logic anyway (do NOT redesign on this single session's data). Accumulate real-world weirdo reports in `INCOMING.md`. Re-design when a pattern emerges across multiple reports. Rationale: matcher behavior is unstable enough that today's optimal hook may be tomorrow's broken hook; better to design from a corpus than from a snapshot.

### Side findings from the same session

- **cd-rule path matching is space-strict.** Rule `Bash(cd /Users/dan/code *)` (with space) does NOT match `cd /Users/dan/code/lobby_analysis/...` (where the next char is `/`, not space). For chains starting with `cd <subpath>`, the cd segment misses the rule and the whole chain prompts. Workaround: a `Bash(cd /Users/dan/code/*)` rule (slash variant) would catch subpath cd's. Not currently in Dan's allow list.
- **The matcher has anti-obfuscation heuristics distinct from segment-checking.** At least two confirmed, possibly more:
  - **Brace-with-quote (e.g. `{"key": "val"}`, `["a","b"]`)** triggers a prompt — diagnostic message in the prompt UI reads "Contains brace with quote character (expansion obfuscation)". Refined 2026-05-30 (later) via probe-bq-{a..e2}: the heuristic fires ONLY on **unquoted-at-bash-level** contexts. Bash single-quoted (`'{"x":"y"}'`) and double-quoted (`"{\"x\":\"y\"}"`) strings are silent. Heredoc bodies (between `<<DELIM` and `DELIM`) ARE bash-unquoted and DO fire. Handled via Strategy 2 deny hook: `claude-hooks/block_brace_quote_heredoc.py` (added 2026-05-30 same session; lives next session).
  - **`\n#` patterns in quoted `-c` bodies** also trigger prompts (per existing doc in `update_claude_permissions.py` line 430). The `Bash(python *)` / `Bash(python3 *)` allows do NOT bypass this. Not yet handled by a hook; Dan's historical workaround was heredocs, but heredocs now have their own brace+quote gotcha — Write-then-run is the unified recommendation. Worth a future probe to confirm `\n#` is still active in current Claude Code (may have been retired between dotfiles' doc writing and 2026-05-30).
- These are **not** chain-matcher issues — they're a separate class of matcher behavior. The brace-quote one is now covered by a dedicated hook; the `\n#` one (and any future anti-obfuscation heuristics) follow the same Strategy 2 path per STRATEGIES.md.

### What else is/was stale alongside this hook

The 2026-05-30 supersession affected more than `block_bash_chains.py`. Tracked + resolved:

- **`update_claude_permissions.py` lines 415-434** (the "Bash permission matching and command chaining" subsection of `ALLOW_DISPLAY_SUMMARY`): used to teach the now-disproven whole-string-prefix-match model with a list of "approved chain prefixes" (most of which had been disproven since 2026-05-25 and remained wrong). **Replaced 2026-05-30** with a pointer to `docs/active/chain-hook-maintenance/` — single source of truth now. Operational habits stable across matcher versions (separate Bash calls, heredoc, write-then-run, `git -C`) kept inline as they don't depend on matcher specifics.
- **`update_claude_permissions.py` line 380** (the chain-rule line in `DENY_DISPLAY`): used to claim "matcher doesn't split chains." **Replaced 2026-05-30** with a pointer to `docs/active/chain-hook-maintenance/`. Tests still pass (`pytest test_update_claude_permissions.py` — 51/51).
- **`notes/bash_chain_matching.md`**: marked as superseded on 2026-05-30 with a banner pointing here. Kept inline for historical context.

The pointer-as-SSOT approach means future findings drop into this folder only; the script and the deprecated note don't need re-editing on each matcher shift.

---

## 2026-05-25 — Initial bash chain matching note (SUPERSEDED in part)

See `notes/bash_chain_matching.md` for the full original. Key claim was: "the matcher prefix-matches the full command string as one unit; it does NOT split chains and check each segment." That whole-string-prefix-matching model fit the empirical evidence collected that day (5 test cases, all PROMPTED for chains regardless of whether segments were individually allowed).

The 2026-05-30 findings above show the matcher now does per-segment checking. Either the matcher changed or the 5/25 test was misread.
