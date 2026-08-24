# SESSION_2026-08-03 — probe run aborted, sanity row failed. Handoff for fresh review.

**Status:** The scheduled 30-day drift check did **NOT** complete. 2 of 8 rows were run
(both recorded PROMPT); 6 were not. **Do not bump `MATCHER_LAST_VERIFIED`.** Do not treat
anything here as a drift verdict — the run was halted at the sanity row and the remaining
rows are unrun, not passed.

Written by the probe session itself at Dan's request, so a fresh dotfiles agent can review
without replaying the whole conversation. It records what was observed, what was inferred,
and — importantly — **which inferences were wrong**, so they aren't re-derived.

---

## 1. Session configuration (confirmed)

- Launched by Dan as `claude --setting-sources project` from
  `/Users/dan/code/dotfiles/docs/active/chain-hook-maintenance/probes` (Dan confirmed
  explicitly; an earlier guess that this was the *coordinating* session was **wrong** —
  see §5.2).
- `pwd` verified: `/Users/dan/code/dotfiles/docs/active/chain-hook-maintenance/probes`.
- Therefore only `probes/.claude/settings.json` should be in effect: no user-level hooks
  (`block_bash_chains.py` etc. inert), no user-level allow rules, **and no
  `additionalDirectories`** — which turns out to matter a great deal (§4.1).
- Dan drove this manually rather than via a second terminal; the probe Claude and the
  paste-and-report loop were the same session.
- Claude Code version was **not** captured. REPROBE pre-flight step 2 requires it
  (`claude --version`) since matcher behavior is version-scoped. **Capture it before any
  re-run** — it is likely the single most important missing datum, because the Bash sandbox
  (§4.2) did not exist during the June probes.

## 2. Dan's operating convention (record this — it is protocol, not trivia)

- **Anything that PROMPTS, Dan denies.** A "user rejected" tool result therefore means
  **PROMPT**, not disapproval of the work. Record it and continue; do not stop to re-plan.
- **Dan pastes the displayed prompt back** (command + description + any logic/reason line)
  to aid troubleshooting.

**Diagnostic value of the paste shape:** a paste carrying *command + description but no
reason-line* is the signature of a plain no-matching-rule / path-scope prompt. A Family-3
heuristic bail always names its reason ("Brace expansion", "Contains brace with quote
character", "…cannot be statically analyzed"). Every paste in this session was the former —
**no Family-3 reason-text was elicited at any point.**

This belongs in `METHODOLOGY.md` (it outlives this runbook); it was not previously written
down anywhere, and its absence cost real time this session.

## 3. Complete observation log

Chronological. "ALLOW" = ran silently. "PROMPT" = Dan was prompted and denied per §2.

| # | Command | Flag | Result | Allow-listed verb? | Touches path outside cwd? |
|---|---|---|---|---|---|
| a | `Read /tmp/reprobe_2026-08-03_runsheet.md` | — | **PROMPT** | n/a (Read; no Read rules exist) | yes |
| b | `touch /tmp/probe_sanity` *(row 1)* | — | **PROMPT** | **yes** `Bash(touch *)` | yes |
| c | `mkdir -p /tmp/probe3 && touch /tmp/probe3/x` *(row 3)* | — | **PROMPT** | **yes** (both segs) | yes |
| d | `ls -la <probes/>` (cwd itself) | — | ALLOW | yes `Bash(ls *)` | no |
| e | `Read probes/.claude/settings.json` | — | ALLOW | n/a | no |
| f | `echo sandbox-discriminator-readonly` | — | ALLOW | yes `Bash(echo *)` | no |
| g | `touch ./sandbox_discriminator_in_workspace` | — | ALLOW | yes `Bash(touch *)` | no |
| h | `pwd` | — | ALLOW | **NO** — `pwd` is not in the allow-list | no |
| i | `claude --help 2>&1 \| grep -i -A2 sandbox` | — | ALLOW | **NO** — leading verb `claude` not listed; also contains a pipe | no |
| j | `git -C /Users/dan/code/dotfiles log …` (×2) | — | ALLOW | yes `Bash(git *)` | yes (via `-C`) |
| k | `git -C … show 9f3b8e6 --stat` / `log -1 a6fd086` | — | ALLOW | yes | yes (via `-C`) |
| l | `grep -rn -i sandbox /Users/dan/code/dotfiles --include=…` | — | ALLOW | yes `Bash(grep *)` | yes |
| m | `grep -n -i -B3 -A12 … update_claude_permissions.py` | — | ALLOW | yes | yes |
| n | `claude --help 2>&1 \| grep -n -i -C6 sandbox` | — | ALLOW | **NO** (see i) | no |
| o | `cd /tmp && git status` | — | **PROMPT** | yes (`Bash(cd /tmp *)`, `Bash(git *)`) | yes |
| p | `touch /tmp/probe_sanity` *(row 1 retry)* | `dangerouslyDisableSandbox: true` | **PROMPT** | yes | yes |
| q | `echo flag-isolation-test` | `dangerouslyDisableSandbox: true` | ALLOW | yes | no |
| r | `ls -la <chain-hook-maintenance/>` (**parent of cwd**) | — | **PROMPT** | **yes** `Bash(ls *)` | yes (ancestor) |
| s | `Write` this file | — | (see §7) | n/a | no |

### Probe rows status

| Row | Command | Expected | Observed | Note |
|---|---|---|---|---|
| 1 | `touch /tmp/probe_sanity` | ALLOW | **PROMPT** | sanity row **FAILED** — run halted here |
| 3 | `mkdir -p /tmp/probe3 && touch /tmp/probe3/x` | ALLOW | **PROMPT** | same suspected cause as row 1 |
| 4, 14, 16, 17, 20, 21 | — | — | **NOT RUN** | not attempted |

## 4. Findings and live hypotheses

### 4.1 Leading hypothesis: no `additionalDirectories` ⇒ only cwd is a trusted root

`--setting-sources project` loads *only* `probes/.claude/settings.json`, which declares no
`additionalDirectories`. Dan's user-level config normally supplies the trusted roots
(`~/code`, `/tmp`). Stripped of it, the sole trusted root is cwd (`probes/`).

This single mechanism explains the whole ALLOW/PROMPT split in §3 with **no other
assumptions**, via the "path outside cwd" column:

- Everything confined to cwd → ALLOW (d, e, f, g, h, i, n, q).
- Writes to `/tmp` → PROMPT despite `Bash(touch *)` / `Bash(mkdir *)` (b, c, p).
- `ls` of the **parent directory** → PROMPT despite `Bash(ls *)` (r).

Row (r) is the strongest and cleanest data point in the session, and it was **accidental** —
it was an ordinary housekeeping `ls`, not a planned row. It is the same shape as planned
**row 20** (`find` on an ancestor of cwd, outside trusted roots → PROMPT) and matches the
2026-07-14 INCOMING entry (`017e51a`: grep on paths outside `additionalDirectories` prompts
despite `Bash(grep *)` ALLOW). **Row (r) is consistent with the existing Family-2 model and
arguably pre-confirms row 20.**

**If this hypothesis is right, the runsheet's expectations for rows 1 and 3 are simply
wrong** — they were authored assuming `/tmp` is reachable, which is true in Dan's normal
sessions but false under `--setting-sources project`. That is a **bug in the runsheet, not
matcher drift**, and rows 1/3 should be rewritten to use cwd-relative paths (or the probe
settings should gain an explicit `additionalDirectories: ["/tmp"]`).

**Tension to resolve:** the June probes reportedly used `/tmp` paths under the same Mode B
and expected/observed ALLOW. Either (i) June's probe settings differed, (ii) path scoping
has since tightened to cover writes (= genuine Family-2 drift, significant), or (iii) the
sandbox (§4.2) is responsible. **Unresolved.** Check `RESULTS_2026-06-01.md` and the June
`settings.json` at commit time — `git log -p probes/.claude/settings.json` — before
concluding anything.

### 4.2 Confound: the Bash sandbox did not exist in June

This session's Bash tool exposes a `dangerouslyDisableSandbox` parameter, so sandbox mode is
active. Nothing in dotfiles enables it (`grep -rn -i sandbox` over `*.py`/`*.json`/`*.sh`
returns only a Chrome bookmarks file), and `update_claude_permissions.py` never emits a
sandbox key — **it is a stock Claude Code default that arrived with the binary.**

It matters because it can sit upstream of the matcher and overwrite the ALLOW/PROMPT signal
in *both* directions:

- Commands the sandbox auto-permits never reach the matcher → look like ALLOW → would read
  as "the Family-3 heuristic disappeared" (**false drift, in the dangerous direction** — it
  would argue for deleting `block_brace_expansion.py`, `block_heredoc_with_pipe_or_redirect.py`,
  and the process-substitution guard, all probably still needed).
- Escapes the sandbox → forced PROMPT regardless of allow rules → masks a real ALLOW.

Rows 14/16/17 are read-only and would be the ones at risk of the false-negative reading.

**Partially tested.** Adding `dangerouslyDisableSandbox: true` to `echo` (q) ran silently, so
**the flag does not itself trigger a prompt**. But the same flag on `touch /tmp/probe_sanity`
(p) still PROMPTED — consistent with §4.1 (path scope is a permission matter the flag does
not bypass) and with the flag working as intended. Not yet proven equivalent to a genuinely
pre-sandbox session.

**Two questions the methodology now needs to separate**, because they want opposite settings:

1. *"Does this hook still earn its keep?"* → sandbox **ON**. A hypothetical hookless Dan
   still has the sandbox, so this is the operationally real condition. Concretely:
   `ls /tmp/{a,b}` is read-only, so if the sandbox auto-allows it, deleting
   `block_brace_expansion.py` would cost Dan *no* prompts — the hook may now be pure friction
   for read-only brace commands. Only visible with the sandbox on.
2. *"Has the Family-3 node set drifted?"* → sandbox **OFF**. Reason-text is emitted by the
   matcher; if the sandbox intercepts, no node name is ever produced. This is also the
   condition the June baseline was collected under, so it preserves continuity.

Recommendation: run all 8 rows **twice, once per condition, as two columns**. Where the
columns disagree, the disagreement is the finding. A single-condition run misreads the other
column's rows.

### 4.3 Unexplained anomaly — flag for the fresh agent

Rows (i) and (n): `claude --help 2>&1 | grep …` ran **silently**, but `claude` is not an
allow-listed verb, and the command contains a **pipe** (a documented Family-3 node). Under a
strict reading of the model this should have prompted twice over.

Candidate explanations: a built-in safe-command path; the sandbox auto-permitting a
cwd-confined read-only command before the matcher sees it; or leading-verb matching behaving
unexpectedly. **Not investigated.** If real, it is a meaningful gap in the Family-3 model and
deserves its own isolation matrix — `pwd` (h) is the same shape (unlisted verb, ALLOW) minus
the pipe, so the pair (h) vs (i) is a ready-made discriminator.

### 4.4 Confirmed-as-expected

- `cd /tmp && git status` (o) → PROMPT. Expected: Claude Code's hardcoded bare-repo-attack
  heuristic prompts on `cd`+`git` regardless of allow rules. Also confirms **Dan's custom
  hooks are genuinely inert here** — `block_cd_git.py` would have hard-failed with its own
  distinctive message and no approve option; instead a normal approvable prompt appeared.
  That is the only direct evidence collected that `--setting-sources project` stripped the
  user-level hooks, and it is inferential (message shape), not conclusive.

## 5. Wrong turns taken this session — do not repeat

### 5.1 "The sandbox is decisively masking the matcher"
Asserted after observing that `touch ./x` (cwd) ALLOWed while `touch /tmp/x` PROMPTed with
the same `Bash(touch *)` rule. The verb-keyed matcher cannot produce that split — but a
**path-scoped allow-list can**, exactly as a sandbox can. The two hypotheses key on the same
cwd boundary and that observation does not separate them. §4.1 now looks like the better
explanation. The sandbox is real and is a genuine confound, but it was not shown to be the
primary cause.

### 5.2 "I am the coordinating session, not the probe session"
Inferred from `REPROBE_2026-08-03.md` line 20 ("in a separate terminal (not the coordinating
session)") plus the runsheet's second-person address. **Dan corrected this: he did launch
with `--setting-sources project`.** The Mode B two-terminal split describes an option, not
what happened; Dan ran the probe session directly and drove the loop by hand.

### 5.3 Over-reading `pwd`
`pwd` running silently (h) was initially read as "the sandbox auto-allows all read-only
commands, so no allow rule is in effect." But `ls` of the parent (r) — also read-only —
**PROMPTed**. So read-only status alone does not confer ALLOW; path scope dominates. This is
what turned §4.1 into the leading hypothesis, and it inverted the earlier reading.

## 6. Recommended next steps

1. **Capture `claude --version` first.** Every conclusion is version-scoped and June's
   comparison predates the sandbox.
2. **Resolve §4.1 against history**: `git log -p -- probes/.claude/settings.json` and
   `RESULTS_2026-06-01.md`. Did June's probe reach `/tmp`? That decides
   "runsheet bug" vs. "Family-2 drift."
3. **Fix the sanity row.** It must be a command that provably exercises the allow-list *and*
   is expected to ALLOW under project-only settings — i.e. cwd-relative
   (`touch ./probe_sanity`), or add `additionalDirectories: ["/tmp"]` to the probe settings
   and keep `/tmp` paths. **No row's result means anything until the sanity row passes** —
   that is the lesson of this session, and it worked exactly as designed.
4. **Then run the 8 rows in both sandbox conditions** (§4.2), capturing reason-text verbatim
   on 14/16/17.
5. **Investigate §4.3** ((h) vs (i)) if the Family-3 model is to be trusted.
6. **Write the convention (§2) into `METHODOLOGY.md`.**

## 7. Housekeeping / side effects

- **Created:** `probes/sandbox_discriminator_in_workspace` (empty, from row g). Stray test
  artifact — **safe to delete**, no probe depends on it.
- **Created:** this file.
- **NOT created:** `/tmp/probe_sanity`, `/tmp/probe3/` — both denied, so the filesystem is
  clean of them. A re-run of rows 1/3 starts from a clean slate.
- **Pre-existing:** `/tmp/x.py` (Dan created it before the session for row 21).
- **`/tmp/reprobe_2026-08-03_results.md` was deliberately NOT written.** The runsheet asks
  for it, but the data describes the harness, not the matcher; writing it would have put a
  false drift baseline into the 30-day record.
- **No changes made** to `update_claude_permissions.py`, `FINDINGS.md`, `INCOMING.md`,
  `MATCHER_LAST_VERIFIED`, or `MATCHER_NAG_SNOOZE_UNTIL`. The nag remains live and expired,
  which is correct — the check genuinely has not run.
