# INCOMING.md

Paste-target for real-world prompts that Dan thinks "shouldn't have happened." Curator agent (or any session) triages from here. Once analyzed and the lesson is captured in `FINDINGS.md`, move the entry to a **Triaged** section below or delete it.

Format for each entry:

```
### YYYY-MM-DD — short label

**Command:**
<paste exact command here>

**Context:** which agent / workspace / session was running, what permission state was loaded (pclaude vs mclaude vs vanilla, recent updates to settings.json, etc.)

**Segments + rules I think should match:** quick analysis

**Hypothesis:** why it actually prompted
```

---

## Pending

### 2026-08-16 — env-prefixed `claude -p "…" --model haiku --debug > out 2> err` prompted — probable plain rule-miss (no allow rule for the `claude` verb); env-var prefix + long quoted prompt-arg as secondary candidates (Strategy 0 at n=1)

**Command:**
```
CLAUDE_CODE_AUTO_COMPACT_WINDOW=100000 claude -p "You are in a probe session. [long quoted prompt ~700 chars, contains parentheses, colons, e.g. '03:2000'] " --model haiku --debug > /tmp/precompact-probes/probe1_control_out.txt 2> /tmp/precompact-probes/probe1_control_debug.txt
```
(Tool-call `description`: *"Run sacrificial control session: 150k tokens of reads, allow-hook, debug captured"*. Full command preserved in the claude_researcher convo `20260813_precompact_update_docs_hook`; launched via Bash `run_in_background` from cwd `/tmp/precompact-probes/probe1-control`.)

**Context:** claude_researcher session on `Dans-MacBook-Pro`, CC 2.1.233, 2026-08-15/16, running sacrificial hook-behavior probes. Dan reported the prompt; the session Claude had anticipated a possible prompt and judged it acceptable rather than unexpected. Recorded per the flag-it-log-it rule. Note: a second, simpler launch (`claude -p "Say exactly: PROBE2 MAIN SESSION OK" --model haiku --debug > … 2> …`, no env prefix) launched moments later — Dan reported only the first; whether the second also prompted was not captured.

**Segments + rules I think should match:** Single segment (no `&&`/`||`/`;`/`|`; the two `>`/`2>` redirects are same-segment). Leading construct is an env-var assignment prefix, then verb `claude`. **No `Bash(claude *)` allow rule exists** in `~/.claude/settings.json` or `update_claude_permissions.py` ALLOW_RULES (the `claude` CLI predates none of this — it's just never been allowlisted; sessions launching sessions is a new shape). No hook applies: `block_bash_chains.py` sees one segment; no heredoc/brace/loop/cd-git/`.py`-verb/newline-hash.

**Hypothesis:** ~~Plain rule-miss on the `claude` verb~~ **FALSIFIED same session (2026-08-16)** by a sacrificial session's `--debug` permission dump: **`Bash(claude *)` IS in the userSettings ALLOW list** (sits between `Bash(code *)` and `Bash(open *)` in the 125-rule dump). Discriminating evidence: a same-session launch of `claude -p "Say exactly: PROBE2 MAIN SESSION OK" --model haiku --debug > … 2> …` with **no env prefix ran silently**; all three prompting launches carried the `CLAUDE_CODE_AUTO_COMPACT_WINDOW=100000` prefix. **Revised PRIMARY: the unlisted env-assignment prefix breaks verb-anchoring** — the ALLOW list carries specific env-prefix rules (`Bash(PYTHONPATH=*)`, `Bash(NODE_ENV=*)`, `Bash(PATH=*)`, `Bash(CI=*)`, `Bash(FORCE_COLOR=*)`, `Bash(DEBUG=*)`, `Bash(TERM=*)`, `Bash(HOME=*)`, `Bash(VIRTUAL_ENV=*)`, `Bash(UV_=*)`), implying the matcher treats `VAR=val cmd` as anchored on the assignment, not the verb; `CLAUDE_CODE_*` has no such rule → fall-through to default-for-Bash. Note the existing env-prefix rules appear to allow *any* command behind the listed prefixes (e.g. `Bash(PATH=*)` — worth its own audit line: that's a broad grant). Redirects and the long quoted arg are exonerated (probe-2 launch had both redirects, no prefix, silent).

**Impact:** Hooks: none apply, working as designed. Allow-rule side (post-falsification): `Bash(claude *)` already exists — the security-posture question flagged in the first draft of this entry (child sessions can be spawned silently, incl. with `--dangerously-skip-permissions`) is **already the live state**, worth Dan's deliberate review as its own item rather than as this entry's fix. For the env-prefix miss itself: candidate narrow rule `Bash(CLAUDE_CODE_AUTO_COMPACT_WINDOW=*)` (mirroring the existing env-prefix rule family) if probe work recurs; the in-session workaround that needs no rule is the CLAUDE.md-sanctioned Write-then-run pattern (env prefix inside a launcher script, invoked via allowlisted `bash /tmp/…`) — used for launch n=4 this session, which ran silent as predicted. **Strategy 0 on the rule; the launcher-script pattern absorbs the friction.**

**Classification:** matcher-side default-for-Bash rule-miss (probable). NOT a hook problem. NOT a matcher weirdo unless the UI text says otherwise on recurrence.

**Recurrence log:** n=2, then n=3 same session (2026-08-16) — probe-1 *block* variant and probe-3 *agent-rehearsal* variant (identical shape each time: env prefix + `claude -p` + long quoted arg + `--model haiku --debug` + two redirects) prompted identically. Consistent with default-for-Bash (fires every launch, no per-shape learning). Frequency conjunct now met *within* the probe work-line (3 approvals in one session) but still nil outside it; if sacrificial-session probing recurs across sessions, promote the narrow `Bash(claude -p *)` allow-rule question to a deliberate Dan decision (trust-surface: prompt-injection into child sessions; the dangerous flags live behind the bare verb, which stays unlisted either way).

---

### 2026-08-14 — `ls -la '<path with $125 inside single quotes>'` prompted with matcher reason *"Shell expansion syntax in paths requires manual approval"* — likely NEW verb-scoped-or-agnostic quote-INSENSITIVE `$`-in-path-arg inspector; architectural sibling of the 2026-06-05 `find`-path-operand glob inspector (Strategy 0 at n=1; Strategy 2 remedy sketched)

**Command:**
```
ls -la 'biorisk_2/Behind the cancellation of a $125 million US virus hunting program _ Vox.pdf' 'biorisk_2/978-1-4939-8678-1_29.pdf' 'biorisk_2/Risk and Benefit Analysis of Gain of Function Research - Draft Final Report.pdf'
```

**Prompt UI text reported by Dan (verbatim):**
> Shell expansion syntax in paths requires manual approval

**Context:** Dan-reported real-world prompt today (2026-08-14). Papers-download-shaped workspace (`biorisk_2/` subdirectory of a research-collection cwd). Standard `~/.claude/settings.json` assumed (no pclaude/mclaude alias noted). CC version not captured — most likely 2.1.220 (last verified drift-check version, FINDINGS 2026-08-03).

**Permission state at trigger (verified live this session on Dans-MacBook-Pro):**
- **ALLOW:** `Bash(ls *)` at line 12 of `~/.claude/settings.json` (blanket verb; also in `_blanket_verbs.py`).
- **ASK / DENY:** no `ls`-specific ASK or DENY entry.
- **additionalDirectories:** `/Users/dan/.nori/profiles`, `/Users/dan/code`, `/Users/dan/data`, `/Users/dan/.claude/skills`, `/tmp`. The `biorisk_2/` path is a relative cwd-descendant — cwd-trust would apply under any of the standing candidate trust models — so the path-scope Family-2 mechanism from FINDINGS 2026-08-03 Finding A / INCOMING 2026-07-14 is NOT the trigger here.

**Hooks currently loaded (per standing session context):** `block_absolute_path_py_verb`, `block_bash_chains`, `block_brace_expansion`, `block_brace_quote_heredoc`, `block_cd_git`, `block_heredoc_with_pipe_or_redirect`, `block_loop_with_pipe`, `block_newline_hash_in_quoted_arg`, `use_uv_run_python`, `api_budget`, `enforce_pr_discipline`. **None should fire on this command:** single-segment `ls` (no `&&`/`||`/`;`/`|` → chain hook silent), no heredoc, no brace expansion (the `{` in `978-1-4939-...` filename is NOT brace-expansion — no `,` or `..` inside — so `block_brace_expansion.py`'s `(?<!\$)\{[^{}\s]*(?:,|\.\.)[^{}\s]*\}` misses it), no loop, no `cd <path> && git`, no `.py`-path verb, no `\n#` in quoted arg. The `$125` sits inside single quotes so `block_newline_hash_in_quoted_arg.py` (targets `\n#` specifically, not `$`) also passes. Verdict: matcher-side prompt, not a hook nastygram — consistent with the prompt UI text (which is a reason-phrase, not one of our hook's nastygrams).

**Segments + rules I think should match:** One segment. Leading verb `ls`, three quoted path args, all under a relative cwd-descendant subtree. Verb-level `Bash(ls *)` should cover it silently under the standing model (per FINDINGS 2026-06-04 per-segment matching + 2026-08-03 blanket-verb reconfirmation). Nothing lexical/structural in the command that any currently-modelled Family-1/2/3 heuristic should catch.

**Hypothesis stack:**

**PRIMARY hypothesis — NEW matcher heuristic: a verb-scoped-or-agnostic quote-INSENSITIVE `$`-in-path-arg inspector.** The `$125` inside the first path argument's single-quoted string is bash-inert at runtime — single quotes disable ALL expansion (variable, arithmetic, command-sub, tilde). Any reader who models actual shell semantics would see zero shell expansion in this command. But the prompt reason-text names "shell expansion syntax in paths" — the matcher appears to be doing a **lexical scan of the argument value** for `$`-prefixed sequences that *look like* shell expansion (`$VAR`, `$1`, `${…}`, `$(…)`), and flagging without respecting bash quote context. **Architecturally a direct sibling of the 2026-06-05 `find`-path-operand glob inspector** (INCOMING 2026-06-05 resolved entry): both fire on the argument's literal *value*, both are quote-INSENSITIVE (cell 5 of that probe: `find 'docs/historical/wi-*'` prompts identically to the unquoted form), both are pre-allow-list (`Bash(<verb> *)` doesn't override), and both use the "syntax in path could expand to something dangerous" threat framing in the reason-text. **New here vs the find-glob row:** metacharacter class is `$` (expansion syntax), not `*`/`?`/`[` (globs); verb is `ls` (or possibly verb-agnostic — untested), not `find`.

**SECONDARY hypothesis — same as PRIMARY but VERB-AGNOSTIC.** The find-glob inspector was empirically `find`-scoped (probe cell 6: `ls docs/historical/wi-*` silent). This new `$`-in-path inspector might not be — Dan's original observation was on `ls`. Whether the same shape prompts on other verbs (`cat`, `head`, `stat`, `find`, `cp`, `mv`) is untested. If verb-agnostic, this is a strictly-broader-scope heuristic than the find-glob one (which was verb-scoped) — a distinct security-model choice by Anthropic. **Discriminator (cheap, 3 cells):** `cat '/tmp/foo $1 bar.txt'`, `stat '/tmp/foo $1 bar.txt'`, `find /tmp -name 'foo $1 bar.txt'`. Silent on all → `ls`-scoped; prompts on all → verb-agnostic; mixed → per-verb list to enumerate.

**TERTIARY hypothesis — the metacharacter class is broader than just `$`.** Reason-text says "shell expansion syntax" (plural framing). May also cover: backticks `` ` ``, `$(…)` command-sub literals inside strings, `${…}` parameter-expansion literals, tilde `~` in unusual positions. Untested. **Discriminator:** `ls '/tmp/foo bar.txt'` (no metachars) silent baseline, then `ls '/tmp/foo `bar` baz.txt'`, `ls '/tmp/foo ${x} baz.txt'`, `ls '/tmp/foo $(cmd) baz.txt'` — see which prompt.

**Ranking: PRIMARY confidence high, SECONDARY untested-but-plausible, TERTIARY held lightly.** The reason-text ("Shell expansion **syntax in paths** requires manual approval") lexically fits PRIMARY cleanly and echoes the find-glob inspector's phrasing framework almost word-for-word (the find one said *"contains unquoted glob characters — could glob-expand to a dangerous action before find runs"*; this one drops the "before X runs" clause and uses "shell expansion syntax" as the metachar-class name).

**Falsified alternatives (from this session's live-state check):**
- ~~Chain-hook issue~~ — single-segment command, `block_bash_chains.py` short-circuits.
- ~~Allow-rule miss~~ — `Bash(ls *)` present and blanket; `ls` is in `_blanket_verbs.py`.
- ~~Path-scope Family-2 (INCOMING 2026-07-14, FINDINGS 2026-08-03)~~ — path args are relative cwd-descendants (`biorisk_2/…`); cwd-tree would cover them under any trust model. Not the trigger.
- ~~`block_brace_expansion.py` FP~~ — the `{` in `978-1-4939-...` (which isn't in the paths anyway, but noting for completeness) has no `,` or `..` inside so the hook regex misses; also, would produce the hook's nastygram, not the matcher-phrased prompt Dan reported.
- ~~Quote-context bug in the matcher~~ — not a "bug" per se; matches the find-glob inspector's confirmed quote-INSENSITIVE design. Anthropic's choice.

**Practical workarounds (Dan already discussed, recorded for the corpus):**
- **(a) Rename the source file** to remove `$` — e.g. `Behind the cancellation of a 125 million US virus hunting program _ Vox.pdf`. Fixes the trigger at the source; also friendlier to any shell tooling that would eventually need to handle the filename. Preferred if the file is Dan-owned.
- **(b) Reformulate the `ls` as a `find`** — `find biorisk_2 -name 'Behind*.pdf' -ls`. The `$` never appears in the command string because the filename comes from the filesystem, not the args. Note: this needs `-name` to not contain a glob-metachar plus a `$`-literal itself; `Behind*.pdf` is glob-only, no `$`, and the target path `biorisk_2` (no glob) sidesteps the sibling 2026-06-05 find-glob inspector.
- **(NOT a workaround) double-quoting or single-quoting the path** — quote-INSENSITIVE per PRIMARY (mirroring find-glob cell 5). Would still prompt.
- **(NOT a workaround) escaping the `$` as `\$`** — untested. Under a pure-lexical-scan model the backslash likely does not save it (matcher walks the argument value, sees `$1` even inside `\$1`). Probeable but not worth chasing at n=1.

**Impact:**
- **Hook (`block_bash_chains.py` and all sibling hooks):** none apply. Working as designed.
- **Matcher-side:** if PRIMARY confirms via any recurrence, **candidate NEW Family-2 sibling row** — verb-scoped-or-agnostic `$`-in-path-arg inspector, quote-insensitive, argument-value-lexical (same architecture as the 2026-06-05 find-glob inspector). Reason-text specimen captured verbatim above. Would join the growing Family-2 verb-scoped-argument-value-inspector cluster (find-ancestor, cd-and-git, find-path-glob, and now this).
- **Allow-rule side:** **no fix possible via `Bash(...)` shape** — same as every other Family-2 content-inspector row. `Bash(ls *)` already blanket-allows the verb; the heuristic runs on the argument value pre-allow.
- **Strategy verdict at n=1: Strategy 0 — leave it and watch for recurrence.** Same posture as the 2026-06-05 find-glob inspector when it first appeared (Dan explicitly chose Strategy 0 there, deferring Strategy 2 until frequency warranted; find-glob has not recurred often enough since to trigger the escalation). The deny-hook gate — *frequent AND clean-alternative* — currently fails on frequency; clean alternatives exist (rename, or `find` with `-name`).
- **Strategy 2 remedy sketch (deferred, for when/if frequency picks up):** `claude-hooks/block_dollar_in_path_arg.py`. Deny an `ls`/`cat`/`stat`/... command with a `$`-followed-by-word-char sequence in any positional path argument (i.e. arguments not preceded by an option flag consuming a value, and not the leading verb itself). Would need false-positive guards for legitimate variable references in bash-unquoted position (which under matcher semantics presumably prompt anyway — the hook isn't wrong to intercept, just doesn't help there), and would need to be applied AFTER strip-single-and-double-quotes to see the raw `$` the matcher sees. Nastygram would recommend: (1) rename the source file, (2) reformulate as `find <literal-dir> -name '<pattern-without-$>' [-ls|-exec ls -la {} +]`. Full Strategy-2 checklist per STRATEGIES.md §"Strategy 2".
- **STRATEGIES.md:** no addition at n=1. If the heuristic recurs, worth a bullet: "`ls`/`cat`/etc. prompt on `$`-followed-by-word-char inside path arguments; quoting does NOT help (matcher inspects the argument value, not shell-expandability). Rename the file to remove `$`, or reformulate as `find <dir> -name '<pattern>'` so the filename comes from the filesystem instead of the args."

**Corpus cross-links (prior heuristics the curator considered before landing on PRIMARY):**
- **2026-06-05 `find` PATH-OPERAND glob inspector** (INCOMING resolved entry, Family-2 sibling): tightest architectural match — quote-INSENSITIVE, argument-value-lexical, verb-scoped, "syntax in path could expand" reason-text framing. This new entry is the same class of check, different metacharacter set (`$` vs `*`/`?`/`[`), possibly different verb-scope.
- **2026-06-01 `\n#`-in-quoted-arg** (Family 1, matcher-named heuristic): distant cousin — lexical byte-scan on quoted argument body — but that one fires inside `-c "..."` and is about `\n#`, not path args.
- **FINDINGS 2026-08-03 Finding A (path-scope prompt)** — RULED OUT above; path args are cwd-descendants here.
- **FINDINGS 2026-08-03 Finding E ("cp command with flags requires manual approval")** — different reason-text family (per-command built-in analyzer wording), but the "requires manual approval" tail is a shared phrase. Worth noting as a possibly-shared prompt-UI family — both use the "…requires manual approval" ending, distinct from the Family-1 named-heuristic wording and the Family-3 "cannot be statically analyzed" wording. Loose observation; not load-bearing.

**Prior-corpus grep result (what curator searched and found, for provenance):**
- Explicit search terms: "Shell expansion", "shell expansion syntax", "dollar sign in path", "$.*path", "expansion syntax", "manual approval" across FINDINGS.md, STRATEGIES.md, and INCOMING.md.
- **No prior entry describes a `$`-in-path-arg matcher heuristic.** The find-glob entry (INCOMING 2026-06-05 resolved) is the closest architectural precedent but is metachar-class-different. FINDINGS 2026-08-03 Finding E ("cp command with flags requires manual approval") is prompt-UI-adjacent (shared "…requires manual approval" tail) but semantically unrelated. **This heuristic shape is NEW to the corpus.**

**Classification:** **matcher-side prompt; candidate NEW Family-2 sibling — verb-scoped-or-agnostic `$`-in-path-arg inspector, quote-insensitive, architecturally a direct analog of the 2026-06-05 `find`-path-operand glob inspector.** NOT a hook problem. NOT a fixable allow-rule shape gap. **Strategy 0 at n=1 (deny-hook gate fails on frequency, clean alternatives exist).** Promotion path: if the shape recurs (particularly with a captured verb-scope discriminator — same prompt on `cat`/`stat` vs. silent), promote to FINDINGS as a Family-2 row with the reason-text specimen; Strategy-2 sketch ready in the "Impact" section above.

---

### 2026-08-14 — `gs --version` prompted; no `Bash(gs *)` allow rule exists — plain rule-miss, fall-through to default-for-Bash prompt (Strategy 0 candidate — verb too rare + no clean alternative)

**Command:**
```
gs --version
```

**Context:** Dan-reported real-world prompt on 2026-08-14. Interpretation ambiguous at the source: could be Ghostscript (`gs`, the standard command-line PostScript/PDF interpreter installed via Homebrew) or muscle-memory for `git status` (some users alias `gs=git status`; Dan does NOT — verified: no `gs` alias in `/Users/dan/code/dotfiles/zsh/*.zsh` or `/Users/dan/.zshrc`). The `--version` flag suggests Ghostscript (an aliased `git status --version` wouldn't parse), so treat this as a Ghostscript invocation.

**Permission state at trigger (verified live this session):**
- **ALLOW:** No `Bash(gs *)`, `Bash(gs)`, or `Bash(gs --version)` entry in `~/.claude/settings.json` (grep returned only `Bash(xargs *)` — substring match, not a rule). No `gs` entry in `/Users/dan/code/dotfiles/update_claude_permissions.py`'s `ALLOW_RULES`.
- **ASK / DENY:** none for `gs`.
- **Blanket verbs:** `gs` is not in `/Users/dan/code/dotfiles/claude-hooks/_blanket_verbs.py` (grep miss).
- **additionalDirectories:** N/A — no path arg.

**Hooks currently loaded:** `block_absolute_path_py_verb`, `block_bash_chains`, `block_brace_expansion`, `block_brace_quote_heredoc`, `block_cd_git`, `block_heredoc_with_pipe_or_redirect`, `block_loop_with_pipe`, `block_newline_hash_in_quoted_arg`, `use_uv_run_python`, `api_budget`, `enforce_pr_discipline`. **None fire on this command** — no chain (single verb, no `&&`/`||`/`;`/`|`), no heredoc, no brace expansion, no loop, no `cd <path> && git`, no `.py`-path verb, no `\n#` in quoted arg, no absolute-path Python invocation.

**Segments + rules I think should match:** One segment, leading verb `gs`, one arg (`--version`). No allow rule covers the verb; no hook applies. Nothing in the current model should silence this.

**Hypothesis:** Plain **rule-miss → CC default-for-Bash prompt.** Per FINDINGS 2026-06-09 (the curl resolution), when no allow rule matches and no ASK rule preempts, CC prompts with `"Bash(<full-command>)"` framing — no `"requires confirmation"` ASK-rule wrapping, no Family-3 `"cannot be statically analyzed"` reason-text, no path-scope Family-2 attribution-less prompt. Dan didn't report the prompt UI text; if it was `"Bash(gs --version)"` bare, that confirms the default-for-Bash mechanism. No mystery here — the matcher is doing its job: `gs` is a real command with side effects (Ghostscript can render/rasterize/convert files), and there's no allow rule saying it's trusted, so it prompts. **This is not a hook problem, not a matcher weirdo — it's a rule-inventory gap.**

**Impact:**
- **Hook (`block_bash_chains.py` and all sibling hooks):** none apply. Working as designed.
- **Matcher-side:** working as designed (default-for-Bash on rule-miss).
- **Allow-rule side (Strategy 1 candidate?):** could add `Bash(gs --version)` (narrow) or `Bash(gs *)` (blanket, matching how `Bash(git *)` etc. are structured) to `ALLOW_RULES`. But per the work-line's deny-hook gate framework in STRATEGIES.md, the mirror question for Strategy 1 is **is this frequent AND is there a clean alternative?** Ghostscript invocations are rare in Dan's workflow (this is the first `gs` prompt in the INCOMING record); one-off approval is engineering-coherent friction, same posture as the 2026-06-01 `find` conclusion. Verdict: **Strategy 0 — leave it.** If Dan finds himself approving `gs` repeatedly, revisit and add a narrow `Bash(gs --version)` or the blanket `Bash(gs *)` (Ghostscript has file-write capabilities via `-sOutputFile=`; blanket may be too much trust).
- **STRATEGIES.md:** no addition needed — this is the canonical "rare verb, no allow rule, one-off approve" pattern the strategy framework already covers by omission (nothing to do = Strategy 0).

**Classification:** **matcher-side prompt via default-for-Bash rule-miss.** NOT a hook problem. NOT a matcher heuristic firing. NOT a bug. Just the absence of an allow rule for a verb Dan uses rarely enough that adding one hasn't paid for itself yet. **Strategy 0 — leave it unless frequency picks up.** Sibling note if it recurs: the `gs`-as-`git status`-alias reading is worth ruling in/out again — if Dan finds himself typing `gs` expecting `git status` and getting Ghostscript-shaped prompts, the fix is a shell alias tweak, not a permission-rule change.

---

### 2026-08-03 — `block_heredoc_with_pipe_or_redirect.py` FALSE POSITIVE: `<<` inside a quoted grep *pattern argument* + a real pipe tail

**Command:**
```
grep -n -B2 -A6 "file_redirect\|<<'PY'" /Users/dan/code/dotfiles/docs/active/chain-hook-maintenance/probes/TEST_PLAN.md | head -40
```

**Context:** Coordinating (normal, full-settings) session on `Dans-MacBook-Pro`, CC 2.1.220, during the 2026-08-03 completed drift check. The hook hard-failed the command with its standard nastygram.

**Analysis:** Hook-side FP, not a matcher weirdo. The `<<` is string content inside a double-quoted pattern argument — there is no heredoc in this command — and the `| head -40` supplied the hook's pipe/redirect conjunct. The hook's detection is lexical (`<<` co-occurring with `|`/`>` on the open line) and doesn't strip quoted regions before scanning. Ironic detail: the quoted pattern was *searching for* heredoc test rows in TEST_PLAN.md — this FP class will recur precisely when maintaining this work-line's own docs.

**Whether the matcher would have prompted:** unknown (hook fired first). Plausibly not — the 2026-08-03 probe (Finding D) showed the *matcher* lexes heredocs/quotes properly and does not fire on redirect-shaped text in non-syntax positions, so the hook is likely stricter than the thing it's shielding against here.

**Remedy sketch (Strategy-2 refinement, deferred at n=1):** strip single- and double-quoted spans before the `<<` scan (the hook already has quote-stripping precedent in `block_loop_with_pipe.py`'s two-level strip). Clean alternative exists (search a literal without `<<`, or Grep tool instead of Bash grep), so the deny-hook gate's "clean-alternative" conjunct still holds; frequency conjunct not yet met.

### 2026-07-14 — bare `grep -c <literal> <abs-path>` prompts despite `Bash(grep *)` ALLOW when the path arg is outside `additionalDirectories` — **hypothesized NEW Family 2 row: file-path-arg trusted-directory allowlist check preempts `Bash(<verb> *)` ALLOW, verb-generalized well beyond `find` (2026-06-01)**; extends & possibly tightens the 2026-06-01 `find`-ancestor mechanism into a set-membership check against `additionalDirectories`; CC **2.1.209** on `Dans-MacBook-Pro`

> **MECHANISM CONFIRMED 2026-08-03** (FINDINGS 2026-08-03 completed run, Finding A): under a load-*proven* harness, verb-level ALLOW does not span paths outside cwd + `additionalDirectories` — observed as a single-variable PROMPT→ALLOW flip on `touch /tmp/…` when `/tmp` was added to `additionalDirectories`, plus row 20 (`find /Users/dan …` → PROMPT despite `Bash(find *)`). The core mechanism this entry hypothesized is now directly observed. Entry stays Pending only for its unfinished sub-question (cwd-*tree* vs `additionalDirectories` set-membership discriminator for read verbs in normal sessions).

**Command (original weirdo Dan reported from concurrent session):**
```
grep -c "target_parent_check" /Users/dan/.local/share/uv/tools/claude-exit/lib/python3.12/site-packages/claude_exit/server.py 2>/dev/null; grep -c "\"verification\"" /Users/dan/.local/share/uv/tools/claude-exit/lib/python3.12/site-packages/claude_exit/server.py 2>/dev/null; ls ~/.local/share/uv/tools/claude-exit/lib/ 2>/dev/null
```
(Tool-call `description` field: *"Check field names in the installed uv-tool server source"*.)

**Prompt UI text (Dan-reported verbatim from a P1-shape retry):**
> `grep -c target_parent_check /Users/dan/.local/share/uv/tools/claude-exit/lib/python3.12/site-packages/claude_exit/server.py   P1 retry: baseline grep outside ~/code, no redirect, no chain, no escaped quote — please capture matcher reason-text from UI`

**UI-format observation (itself a data point):** the prompt is just the *command + Dan's tool-call `description` field* — no `"Bash(grep *) requires confirmation"` ASK-rule wrapping (as seen in the 2026-06-09 curl entry pre-resolution), no `"Contains shell syntax (…) cannot be statically analyzed"` Family-3 framing, no `"Bash(<verb> <full-command>)"` default-for-Bash format documented in the 2026-06-09 curl resolution. Two readings: (a) the UI changed in some 2.1.x post-2.1.165 revision to hide rule attribution, (b) *no rule attribution because no rule matched* — the prompt was raised by a path-scope check that fires **outside the normal allow-rule resolution path** entirely. Reading (b) is architecturally consistent with the 2026-06-01 Family 2 find-ancestor observation (which also fired with `Bash(find *)` present and did not quote a heuristic reason-text). Held lightly — the two readings aren't fully discriminable without a Family-1/3 side-by-side probe in the same UI version.

**Context:** Dan-reported real-world prompt on 2026-07-14, on `Dans-MacBook-Pro`. Concurrent session was auditing whether the installed `claude-exit` MCP server source uses field name `verification` (as an old SessionStart hook text references) or `target_parent_check` (which is what step=1 actually returns in the current server). Dan flagged it to a sibling session; that session ran the Mode A HITL probe matrix below (fresh session, `Dans-MacBook-Pro`, Claude Code **2.1.209**, cwd `~/code/dotfiles`, standard `~/.claude/settings.json`, no pclaude/mclaude alias, all Dan-authored hooks live and executable, no project-local `.claude/settings.local.json` in dotfiles that touches grep).

**Permission state at trigger (verified live this session):**
- **ALLOW:** `Bash(grep *)` at line 11 of settings.json; `Bash(ls *)` at line 12. Both blanket, both should silently allow every probe under the standing verb-based model.
- **ASK:** no `grep` or `ls` entry. Rules Dan out the 2026-06-09 curl mechanism (ASK > ALLOW precedence).
- **additionalDirectories:** `/Users/dan/.nori/profiles`, `/Users/dan/code`, `/Users/dan/data`, `/Users/dan/.claude/skills`, `/tmp`. **`/Users/dan/.local` is NOT in this list.** No path-allow-rule for `~/.local` in settings.json either (grepped).
- **Hooks:** all Dan-authored hooks loaded, symlinked, executable. `block_bash_chains.py` short-circuits on the ORIGINAL (all-blanket `;`-chain: `grep`/`grep`/`ls` are all blanket) — verified by inspection. No other hook matches (no heredoc, no brace expansion, no loop, no cd-git, no `.py` verb, no newline-hash, no brace-quote).

**Probe matrix (Mode A HITL, this session; probes ran by the sibling curator-adjacent session on Dan's report; each row varies exactly one axis vs. its neighbors):**

| # | Command | Path in `additionalDirectories`? | # tokens after verb | Chain / redirect | Result |
|---|---|:--:|:--:|:--:|---|
| P7 | `grep --version` | n/a (no path arg) | 1 | — | **silent** |
| P8 | `grep foo /etc/hosts` | **no** | 2 | — | **PROMPT** |
| P6 | `grep -c target_parent_check /etc/hosts` | **no** | 3 | — | **PROMPT** |
| P1 | `grep -c target_parent_check /Users/dan/.local/share/uv/tools/claude-exit/lib/python3.12/site-packages/claude_exit/server.py` | **no** | 3 | — | **PROMPT** |
| P9 | `grep foo /Users/dan/code/dotfiles/CLAUDE.md` | **yes** (`~/code`) | 2 | — | **silent** |
| P10 | `echo "target_parent_check foo" > /tmp/probe10_marker.txt; grep -c target_parent_check /tmp/probe10_marker.txt` | **yes** (`/tmp`) | 2 per grep | `;` chain + `>` redirect | **silent** |
| P5 (repro) | Original 3-segment `;` chain | **no** (`~/.local`) | 3 per grep, 1 per ls | `;` chain + `2>/dev/null` per segment | **PROMPT** |

(P2/P3/P4 chain-variants also PROMPTED; redundant given P1/P6/P8/P10 isolate the key axis.)

**Segments + rules I think should match:** The original weirdo is an all-blanket `;`-chain — `grep`/`grep`/`ls` all in `BLANKET_VERBS`. Per Plan 01 (FINDINGS 2026-06-04/05) the chain hook passes it through, and the matcher's per-segment allow-check should silently ALLOW each segment on `Bash(grep *)` / `Bash(ls *)`. That it PROMPTED even for the reduced-to-single-segment P1 shape means the mechanism is at the **segment (single command)** level, not at the chain-combining layer — the chain isn't the trigger; the file-path arg is.

**Update 2026-07-28 (partial evidence from the diff-procsub probes — see Triaged 2026-07-28 entry + FINDINGS 2026-07-28):** `diff /Users/dan/code/dotfiles/nori-researcher/skills/write-a-plan/SKILL.md /Users/dan/.claude/skills/write-a-plan/SKILL.md` (no procsub; second arg IN `additionalDirectories`, NOT under cwd `~/code/dotfiles`) ran **SILENT**. This **down-weights SECONDARY** (cwd-tree-only trust): if cwd-tree-only were the universal trust set for file-reading verbs, that cell should have prompted. Caveat — the inference is confounded by verb coverage: `diff` is on this entry's untested-verbs list, so silence is consistent with EITHER "`additionalDirectories` is independently trusted (PRIMARY)" OR "`diff` isn't path-scope-checked at all." The clean SECONDARY discriminator remains probe 1 below (grep a `/Users/dan/data/…` file from cwd `~/code/dotfiles`) using the *confirmed-covered* verb `grep`. Status: SECONDARY down-weighted, not eliminated; PRIMARY unchanged.

**Hypothesis stack:**

**PRIMARY: NEW Family 2 row — file-path arg outside `additionalDirectories` triggers a path-scope prompt, verb-generalized past `find`, preempting `Bash(<verb> *)` ALLOW.**

The three cleanest single-axis flips:
- **P8 → P9 (path only, 2-arg grep):** `/etc/hosts` PROMPT → `/Users/dan/code/dotfiles/CLAUDE.md` silent. Same verb, same shape, same token count — only the *path arg* changes. The one-in-the-trusted-set is silent; the one outside prompts. Textbook path-aware discriminator.
- **P6 → P1 (path only, 3-arg grep):** `/etc/hosts` PROMPT → `~/.local/…/server.py` PROMPT. Both PROMPT — both outside `additionalDirectories`, one is a system path, one is a user path. Rules out "/etc-specific system-file protection" and localizes the trigger to *set-membership against `additionalDirectories`*, not path prefix.
- **P7 → P8 (no-path → path-outside):** `grep --version` silent → `grep foo /etc/hosts` PROMPT. Confirms the trigger is a path arg's presence-and-location, not the verb itself.

This is architecturally the **same family** as the 2026-06-01 `find`-ancestor entry — path-aware semantic reasoning, preempts `Bash(<verb> *)` ALLOW rules, no matcher-named reason-text in UI, no allow-rule fix possible via `Bash(...)` shape. But it **extends the family in two directions:**
1. **Verb generalization:** 2026-06-01 explicitly flagged "(a) whether the heuristic generalizes to other tools that take a path argument (`grep -r`, `rg`, `du`, `tree`)" as untested. Dan's probes are direct evidence for *yes* — `grep` (a file-content-reading verb) trips it. That opens the question of *which* verbs are covered (see uncertainty below).
2. **Trigger evolution — set-membership, not strict-ancestor-of-cwd.** Under 2026-06-01 semantics, `/etc/hosts` is NOT a strict ancestor of cwd `~/code/dotfiles` — it's an unrelated absolute path — so `find /etc -name hosts` from cwd `~/code/dotfiles` would (per 2026-06-01) have run silent. Under the current probe data, an outside-`additionalDirectories` path *does* prompt. This is either:
   - **(evolution / tightening)** — the matcher's path-scope check has broadened from "strict-ancestor-outside-trusted" to "any-path-outside-trusted." Version gap 2.1.150–165 (2026-06-01) → 2.1.209 (now) is nontrivial; matches Dan's version-pinning uncertainty flag.
   - **(mechanism differentiation)** — `find` (broad-scope scanner) and `grep` (specific-file reader) are treated by *different* path-scope checks. Under this reading both mechanisms are simultaneously live and the 2026-06-01 finding on `find` still holds unchanged. Distinguishable by a probe cell: does 2026-06-01's `find /Users/dan/Documents -name x` (sibling-of-cwd, in-$HOME, NOT in additionalDirectories) still run silent in 2.1.209? If yes → mechanism-differentiation; if no → evolution.

**SECONDARY: cwd-relative trust (rather than additionalDirectories-explicit trust).** P9 passes because `/Users/dan/code/dotfiles/CLAUDE.md` is under cwd `~/code/dotfiles` — a strict descendant. Under this alternate model, the matcher trusts (a) cwd's own subtree ∪ (b) `additionalDirectories` — and P9 could be silent for reason (a), not (b). Discriminator: **grep a file in `/Users/dan/data/<something>` from cwd `~/code/dotfiles`.** `/Users/dan/data` is in `additionalDirectories` but NOT under cwd. If silent → `additionalDirectories` is independently trusted (PRIMARY confirmed). If PROMPT → cwd-tree is the actual trust, `additionalDirectories` may be a Read/Edit/Write-tool concept that doesn't carry over to Bash — a stronger and more consequential finding.

**TERTIARY: version-2.1.209-specific tightening.** Whether or not the mechanism-differentiation reading of PRIMARY holds, the fact that the trigger is now "any-path-outside-set" rather than "strict-ancestor-outside-set" suggests a matcher-side tightening in a recent CC release. Worth pinning down separately (e.g. by scanning the 2.1.x changelog if there is one, or downgrading a session and re-running P8/P9). Distinct from the mechanism question — even if mechanism-differentiation is the right primary read, the *scope* of the grep check may still have tightened.

**QUATERNARY (long-shot): mechanism is not Bash-side at all — it's the tool-call `description` field.** Dan's UI-text observation showed only *command + description*. Wildly speculative, but: if the matcher checks the `description` field for path-suggestive content ("outside ~/code", ".local", server-side words), that could raise a prompt at a layer above the Bash verb/arg parse. Ruled unlikely by P7 (which has no path-suggestive description and was still generated from a session that could have had any description string). Listed only for the audit trail.

**Ranking: PRIMARY >> SECONDARY > TERTIARY (as complement to PRIMARY) > QUATERNARY.** PRIMARY is the parsimonious extension of the existing Family 2 row and predicts all seven probe cells cleanly. SECONDARY is a meaningfully different model that P9 alone cannot distinguish from PRIMARY.

**Falsified alternatives (from Dan's independent triage + this session's verification):**
- **`*` doesn't span whitespace in `Bash(<verb> *)`** — falsified by P9 (2-token grep, path in `additionalDirectories`, silent). Same token count as P8 (which prompted); if whitespace-spanning were the trigger, both would prompt uniformly.
- **ASK-rule preemption (2026-06-09 curl precedence)** — no `grep` ASK rule (verified live).
- **Family-3 structural bail** — probes P1/P6/P7/P8/P9 are all structurally trivial (single verb + args, no chain, no heredoc, no brace, no loop); no Family-3 reason-text seen in the UI attribution. P8 (bare 2-arg grep, no redirect, no chain, no quote) already prompts, so Family-3 is ruled out.
- **Chain/redirect/escaped-quote triggers** — P8 has none of those and still prompts.
- **`/etc`-specific system-file protection** — P1 (user path `~/.local/...`) prompts identically to P6 (system path `/etc/hosts`).
- **Verb-specific quirk on `grep`** — untested here directly, but the 2026-06-01 finding on `find` already established that at least *two* verbs (`find` and `grep`) can be path-scope-preempted, so this isn't grep-specific. Untested for other verbs (see uncertainty).

**Uncertainty / known unknowns (be explicit):**
- **Whether `~/.claude`-path prompts Dan may have approved in earlier sessions are affecting probe outcomes.** Dan flagged this — he doesn't remember whether he ever session-approved individual paths that might be persisting. Probes P1/P6/P8 all fresh-prompted, so the answer for those paths appears to be "not persisting" — but a longer-lived session with per-path approvals could show apparent silences that are actually caches. Fresh-session probes are the clean control.
- **Which verbs are covered?** Confirmed: `find` (2026-06-01), `grep` (this entry). Untested: `cat`, `head`, `tail`, `wc`, `stat`, `ls`, `du`, `file`, `readlink`, `diff`. P10's `ls ~/.local/share/uv/tools/claude-exit/lib/` inside the original weirdo did seem to also prompt (part of the composite `;`-chain) but wasn't cleanly isolated as a single-verb `ls <outside-path>` probe. **This is the biggest missing cell** — if `cat <outside-path>` prompts, this is a broad, near-universal check on file-reading verbs; if only `find` and `grep` prompt, it's a narrower per-verb list.
- **Write-target scoping.** P10 wrote to `/tmp` (in `additionalDirectories`) and was silent. Untested: `echo foo > /Users/dan/.local/marker.txt` — does a *write* to an outside path prompt? Would generalize the mechanism beyond just read-target args. Important for the security-coherence story.
- **stdin-redirect (`<`) from outside paths.** Untested — `grep foo < /Users/dan/.local/...`.
- **`-r`/`-R` recursive grep with a directory arg** vs. `grep <literal> <file>` — untested. May behave differently since recursive grep is closer to `find`'s "broad-scope scanner" semantics.
- **Whether the trust set is exactly `additionalDirectories` or is `additionalDirectories ∪ cwd-tree ∪ <something else>`.** The SECONDARY hypothesis probe (grep a `~/data/...` file from cwd `~/code/dotfiles`) is the key discriminator. Also untested: `/var`, `~/Library`, `/opt/homebrew`, or other paths Dan may or may not care about.
- **UI attribution absence — real or artifact of paste protocol?** Dan reported the UI showed just *command + description*. Whether that's the matcher's real UI (attribution-less because the path-scope check runs outside the allow-rule system) or an artifact of the current CC UI layer's rendering when it can't attribute the prompt to a specific rule is not clear from a single observation.
- **Version pinning.** CC **2.1.209** here; 2026-06-01 finding was on 2.1.150–165. The mechanism may have tightened in a specific intermediate release; sub-version bisection would be nice-to-have but expensive.

**Cheap discriminator probes (recommended for a follow-up session; NOT run here — curator role):**

Design principle: use METHODOLOGY Mode C **headless marker-file probes** to sidestep dialog fatigue. In headless `claude -p`, a prompt-requiring command is auto-denied → no marker file; a silently-allowed command runs → marker file appears. The marker file is ground truth, independent of what the sub-agent's text output claims.

1. **SECONDARY discriminator (highest priority — trust source is cwd-tree vs `additionalDirectories`):** From cwd `~/code/dotfiles`, `grep foo /Users/dan/data/<any-file>; touch /tmp/probe_data_marker`. If marker appears → `additionalDirectories` is trusted independently of cwd (PRIMARY confirmed). If marker missing → cwd-tree may be the actual trust (SECONDARY confirmed; would be a stronger, more consequential finding — means `additionalDirectories` may not carry to Bash).
2. **Verb-family generalization matrix:** run `cat <outside-path>`, `head <outside-path>`, `tail <outside-path>`, `wc <outside-path>`, `stat <outside-path>`, `file <outside-path>`, `ls <outside-path>/`, `du <outside-path>` each with a marker probe. Reveals whether this is a broad "any-file-reading-verb" check or a narrow per-verb list. Highest-signal single-run experiment.
3. **Write-target scoping:** `echo foo > /Users/dan/.local/tmp_marker_write.txt; touch /tmp/probe_write_marker`. If the outer `touch /tmp` marker appears → the outside-write ran (or was auto-denied but not fatal — need to check the marker semantics carefully). Alternative: use a two-marker design that distinguishes "outside-write ran" from "outside-write blocked but chain continued."
4. **stdin-redirect scoping:** `grep foo < /Users/dan/.local/<file>; touch /tmp/probe_stdin_marker`.
5. **Regression check on 2026-06-01 `find` cells (version-tightening test):** re-run `find /Users/dan/Documents -maxdepth 1 -name x` (sibling of cwd, in $HOME but NOT in additionalDirectories) from cwd `~/code/dotfiles`. In 2026-06-01 (CC 2.1.150–165) this was silent. If silent in 2.1.209 → mechanism-differentiation (find and grep use different path-scope checks). If PROMPT → wholesale evolution to set-membership across both verbs.
6. **UI-attribution check (for a fully-current Family-1/2/3 comparison):** run three side-by-side probes with a KNOWN Family-1 trigger (e.g. `python3 -c "print(1) # comment"` if `\n#` is still live), a KNOWN Family-3 trigger (e.g. `ls /tmp/{a,b}` — hook-hard-fails, so use a non-hooked path like a marker-file headless probe of a construct that bypasses our hooks), and P1. Compare UI attribution across all three to see whether the "bare command + description" UI is unique to this new mechanism or a global 2.1.209 UI shift. This is the discriminator between UI-format reading (a) and (b).

**Impact:**
- **Hook (`block_bash_chains.py`):** none. Original weirdo is all-blanket `;`-chain; hook correctly passes it through. Working as designed.
- **All other hooks:** none apply — no heredoc, no brace expansion, no loop, no cd-git, no `.py` verb, no newline-hash. Not a hook problem.
- **Matcher-side:** if PRIMARY confirms via probes 1+2, **new Family 2 row** — generalizes the 2026-06-01 `find`-ancestor mechanism to arbitrary file-path-taking Bash verbs (or a specific subset TBD by probe 2), with the trust set being `additionalDirectories` (or `additionalDirectories ∪ cwd-tree` if SECONDARY holds). Would be a load-bearing FINDINGS entry.
- **Allow-rule side:** if PRIMARY confirms, **Strategy 1 IS possible in principle** for this class — adding paths to `additionalDirectories` in settings.json (via `update_claude_permissions.py`'s `ADDITIONAL_DIRECTORIES`) would move a subtree into the trusted set and silence the prompts. Concrete case for the weirdo: adding `/Users/dan/.local` (or a narrower subtree like `/Users/dan/.local/share/uv/tools`) to `ADDITIONAL_DIRECTORIES` would silence the original probe. But this is a *scope-of-trust* decision (uv-tool installs contain arbitrary third-party code), not a rule-writing decision — Dan should own it consciously, not reflex-add. Strategy 2 (a hook that rewrites-or-blocks) doesn't obviously fit here because the *alternative* isn't "reformulate this command" but "add the path to trust" or "accept the prompt as engineering-sensible friction" — same posture as 2026-06-01's no-hook conclusion for `find`.
- **STRATEGIES.md:** if PRIMARY confirms, add a line — *"File-path args outside `additionalDirectories` (grep, and likely other file-reading verbs — see FINDINGS 2026-07-14) trigger a path-scope prompt that preempts `Bash(<verb> *)` ALLOW. Strategy 1 fix: add the subtree to `ADDITIONAL_DIRECTORIES` if you trust it; otherwise accept the prompt as engineering-sensible."*
- **CLAUDE.md standing-context update:** **RECOMMEND WAIT for FINDINGS promotion.** The hypothesis is strong from Dan's probe map but the SECONDARY vs PRIMARY discriminator (`additionalDirectories` vs cwd-tree) hasn't been run, and the verb-family generalization is untested past grep. Standing context is high-visibility real estate — a wrong or incomplete rule there taxes every session. Once probes 1 + 2 run and the mechanism is pinned down (probably one 15-min headless probe pass), a one-bullet CLAUDE.md addition is warranted.

**Classification:** **matcher-side prompt; probable NEW Family 2 row extending the 2026-06-01 `find`-ancestor entry to arbitrary file-reading Bash verbs, with the trust set being (at minimum) `additionalDirectories`.** NOT a hook problem. NOT a fixable allow-rule shape gap — Strategy 1 via `ADDITIONAL_DIRECTORIES` is possible if Dan wants to expand trust, but the current prompt is engineering-coherent friction (uv-tool installs live outside Dan's writable subtree and could contain arbitrary third-party code). **Promotion path to FINDINGS: run headless probes 1 + 2 (SECONDARY discriminator + verb-family matrix) in a single follow-up session; promote if PRIMARY holds and probe 2 pins down the verb-family scope.** Once promoted, worth a one-bullet CLAUDE.md standing-context addition.

---

### 2026-07-10 — canonical `until <check>; do sleep 15; done; grep … | tail -20` polling loop matcher-prompted with reason `"Contains shell syntax (string) that cannot be statically analyzed"` — NEW Family-3 node-name `(string)`; ALSO surfaces likely matcher-preempts-PreToolUse-hooks ordering for Family-3 bails

**Command:**
```
until [ -n "$(grep -E 'Recall|Traceback|Error|SystemExit' /tmp/harness_v9_run.log 2>/dev/null)" ]; do sleep 15; done; grep -E 'Injected|Review done|HIT|MISS|Recall|Traceback|Error' /tmp/harness_v9_run.log | tail -20
```

(Tool-call `description` field: *"v9 harness run outcome (recall or crash)"*.)

**Matcher prompt UI text (Dan-reported verbatim):**
> Contains shell syntax (string) that cannot be statically analyzed

**Context:** Dan-reported real-world matcher prompt, 2026-07-10, on `Dans-MacBook-Pro`. Command was the canonical "wait until background job completes" pattern — the exact `until <check>; do sleep 2; done` shape that the Bash tool description explicitly endorses for polling. Session was watching a v9 harness log for a completion marker, then printing a recall/error summary once the log resolved. Standard `~/.claude/settings.json` permission state (no pclaude/mclaude alias noted). **Dan explicitly confirmed on triage** that the trailing `; grep … | tail -20` WAS part of the submitted command (so the pasted string above is verbatim what the tool call sent), and that he saw the matcher's `(string)` prompt, NOT a hook nastygram.

**Allow-rule inventory (relevant):** `Bash(grep *)`, `Bash(sleep *)`, `Bash(tail *)` all present in the global ALLOW list (verified live). No `Bash(until *)` rule, no `Bash([ *)` rule — but per FINDINGS 2026-06-05 the matcher body-analyzes bare loops and auto-approves them when every effect is statically boundable, without needing a `Bash(<loop-kw> *)` rule.

**Hooks currently loaded (per `ls -la ~/.claude/hooks/`):** all Dan-authored hooks are symlinked in — `block_bash_chains`, `block_loop_with_pipe`, `block_brace_expansion`, `block_brace_quote_heredoc`, `block_cd_git`, `block_heredoc_with_pipe_or_redirect`, `block_newline_hash_in_quoted_arg`, `block_absolute_path_py_verb`, `api_budget`, `require_finish_convo`, `use_uv_run_python`. All are symlinks to the dotfiles source. `block_loop_with_pipe.py` is present in `settings.json` under `PreToolUse` with `matcher: "Bash"` (verified live via `python3 -c "import json; …"`), and both the symlink and its target have the executable bit set (`-rwxr-xr-x` on target).

**Segments + rules I think should match:**
The `;`-chain splits into two segments:
1. `until [ -n "$(grep -E '…' /tmp/harness_v9_run.log 2>/dev/null)" ]; do sleep 15; done` — an `until`-loop whose body is bare `sleep 15` (blanket verb, no `$var`, no pipe) and whose condition is `[ -n "<string>" ]`. Interior of the condition string: `$(grep -E '…' /tmp/harness_v9_run.log 2>/dev/null)` — a command substitution containing a `grep` (blanket) with a `2>/dev/null` file_redirect.
2. `grep -E '…' /tmp/harness_v9_run.log | tail -20` — a top-level pipeline, both segments blanket-allowed (`grep`, `tail`). Per FINDINGS 2026-06-05 (leading-verb-anchored fast-path), a top-level pipeline of blanket verbs runs silently.

None of the segments look independently problematic under the current model. The loop body has no pipe and no bare variable (so `block_loop_with_pipe.py` per its own docstring shouldn't fire on the *body*), and the trailing top-level pipe is fast-pathed.

**Hook trace (empirical, run this session against the dotfiles hook files):**

Ran the exact command through both `block_bash_chains.py` (via `sys.exit(0)` on FLOW_CONTROL_RE matching `until`) and `block_loop_with_pipe.py` on this session's laptop. Trace results:

- `block_bash_chains.py` → exits 0 (short-circuits on `FLOW_CONTROL_RE.match(command)` at line 158, since `until` is a flow-control keyword). Correct per its design — a leading flow-control command exempts the whole `;`-chain from chain-hook processing, even if the tail has non-loop content.
- `block_loop_with_pipe.py` → **emits DENY when invoked directly with the payload**. Trace:
  - `strip_all_quotes` → `until [ -n "" ]; do sleep 15; done; grep -E '' /tmp/harness_v9_run.log | tail -20`
  - `has_loop` (LOOP_RE `\b(for|while|until|select)\b` on full-strip) → True (`until`)
  - `has_do` (DO_RE `\bdo\b`) → True
  - `has_pipe` (PIPE_RE `(?<!\|)\|(?!\|)` on full-strip) → **True** — matches the `|` in the *trailing* `| tail -20`, which is OUTSIDE the loop body but the hook is a DUMB regex detector (explicitly documented as such in the docstring: *"a bare loop alongside an unrelated pipe or variable (…`for …; done; ls | head`) over-fires"*)
  - `has_var` (VAR_RE on single-quote-strip) → False (`$(` doesn't match `\$\{?[\w@*?#!-]`)
  - Conjunct `has_loop AND has_do AND (has_pipe OR has_var)` = True → hook returns `{"permissionDecision":"deny"}` + nastygram

**Discrepancy triage — three possibilities investigated:**

**(2) Hook not installed/active — RULED OUT.** Live inspection this session:
- `~/.claude/hooks/block_loop_with_pipe.py` is a symlink to `~/code/dotfiles/claude-hooks/block_loop_with_pipe.py`.
- Target file has `-rwxr-xr-x` (executable bit set).
- `~/.claude/settings.json` contains the entry under `PreToolUse` with `matcher: "Bash"` and `command: $HOME/.claude/hooks/block_loop_with_pipe.py`.
- Direct invocation with Dan's command via stdin produces `{"permissionDecision": "deny", …}` on stdout.

**(3) Hook shape-mismatch (body-scoped) — RULED OUT.** Re-reading the hook code without re-invoking it: every `has_*` check uses `re.search()` on the FULL command string (either `strip_all_quotes(command)` or `strip_single_quotes(command)`), NOT just the region between `do` and `done`. The docstring is explicit about this over-fire class: *"This is a DUMB-BUT-NOT-BLIND detector: regex-only, no nesting/AST analysis. It does not verify the pipe/variable is literally between do and done, so a bare loop alongside an unrelated pipe or variable (`x=$foo; for i …; do :; done`, or `for …; done; ls | head`) over-fires. Accepted: cost is a cheap rewrite."* The `; grep … | tail -20` after `done` DOES match PIPE_RE. My earlier empirical result was correct — the hook is genuinely body-un-scoped and does fire on this shape when invoked.

**(1) Order-of-operations: matcher preempts PreToolUse hooks for Family-3 bails — REMAINING HYPOTHESIS, likely.** Given (2) and (3) are ruled out, the only explanation for Dan seeing the matcher's `(string)` prompt instead of the hook's nastygram is that **the matcher's static-analysis bail fires BEFORE the PreToolUse hook stack is dispatched** — at least for this command. Architecturally plausible: Family-3 bails are structural / grammar-level (matcher can't even tokenize/parse the command sufficiently to route it into the permission system), so they may be evaluated at the parse-time layer BEFORE Claude Code invokes hooks with a well-formed tool payload. Under this model:
- Commands that Family-3-bail → matcher prompts DIRECTLY, hook layer never sees them.
- Commands that parse cleanly → hook layer sees them first, can deny before matcher runs.

This has real consequences for the work-line thesis. It means **for every Family-3 shape, our Strategy-2 deny-hooks CAN'T actually intercept the matcher prompt** — the matcher prompts first regardless of what our hook says. The Strategy-2 hooks we've shipped for Family-3 shapes (`block_heredoc_with_pipe_or_redirect.py`, `block_brace_expansion.py`, `block_loop_with_pipe.py`) may only be firing on the *headless / dry-run* / direct-invocation paths, not on the actual live matcher-preemption path. This deserves its own re-probe: pick a known-triggering shape from each of those hooks, submit it live, see if the hook nastygram OR the matcher prompt fires. If matcher-first is real, the hooks are mostly "belt and suspenders" for the model-training angle (Claude reads the nastygram and rewrites) but AREN'T actually saving Dan prompts on the shapes that Family-3-bail. Worth a deliberate FINDINGS-level probe.

**Hypothesis (matcher-side, on the `(string)` reason itself):**

Building on Dan's original read and given the discrepancy resolves to matcher-first ordering: the interesting question is what the matcher choked on. The reason-text node name `(string)` is a **new Family-3 tree-sitter-bash node** we have not seen. Existing Family-3 node names in FINDINGS: `file_redirect`, `pipeline`, `simple_expansion`, `brace_expansion`. `string` is the tree-sitter-bash node for a double-quoted string literal (with possible interpolation).

**PRIMARY hypothesis:** the matcher, walking the `until` loop's *condition*, hits the double-quoted string `"$(grep -E 'Recall|Traceback|Error|SystemExit' /tmp/harness_v9_run.log 2>/dev/null)"`. That string contains an interpolated command substitution (`$(…)`), which itself contains a `file_redirect` (`2>/dev/null`). Per prior Family-3 findings, a `file_redirect` is one of the constructs whose effect the matcher can't statically bound. Nested inside the interpolation, inside the string, inside a test condition, inside a loop — the matcher can't reduce that stack and bails, naming the outermost problematic node: **`string`**. This is architecturally the same family as `heredoc + file_redirect` (2026-06-05) and `loop + pipeline` (2026-06-05 later): a construct that's individually fine bails when nested inside another construct that moves it out of a fast-path.

**SECONDARY hypothesis:** the matcher bails on any interpolated `string` node in a `test` / `[ ]` condition, regardless of what's inside the interpolation. Distinguishable from PRIMARY by probing `until [ -n "$(date)" ]; do sleep 5; done` — if that prompts with "(string)", any interpolation-in-test bails; if it runs silent, the `2>/dev/null` inside is load-bearing (PRIMARY).

**TERTIARY hypothesis (Dan's original read):** the specific culprit is the `2>/dev/null` file_redirect being nested inside a `$(...)` inside a `[ ... ]` test bracket inside an `until` loop condition — a stack of four nestings the matcher can't reason across. Same family as PRIMARY but attributes the failure to the deepest-buried construct.

**Relative likelihood:** PRIMARY > TERTIARY > SECONDARY. PRIMARY and TERTIARY are close variants of "nested unbounded construct bails and the matcher names the outermost enclosing node it can identify" — the standard Family-3 architecture. SECONDARY would be a new "bail on any interpolated string in test-context" heuristic, less parsimonious.

**Cheap discriminator probes (NOT run — curator role):**
- `until [ -n "$(date)" ]; do sleep 5; done` — same structure, but the substitution has no redirect. If silent: PRIMARY/TERTIARY confirmed (redirect is the load-bearer). If prompts "(string)": SECONDARY (any interpolation-in-test bails).
- `[ -n "$(grep -E 'foo' /tmp/x 2>/dev/null)" ]` bare (no loop, no `until`) — isolates whether the loop context is needed. If prompts: bail happens at the test-condition level, loop context is incidental. If silent: loop context is load-bearing (the "moves out of fast-path" story).
- `[ -n "$(grep -E 'foo' /tmp/x)" ]` — same as above without the `2>/dev/null`. Discriminates whether the redirect matters at all.
- Same command without the `[ -n … ]` — e.g. `until grep -q 'foo' /tmp/x 2>/dev/null; do sleep 5; done`. If silent: the `[` test is what breaks fast-path (existing FINDINGS say `until <cmd>` fast-paths cleanly). If prompts: the deeper `2>&…`/`2>/dev/null` inside a condition is the trigger.
- **Ordering probe (matcher-first hypothesis):** submit a KNOWN Family-3 trigger for one of our hooks (e.g. `ls /tmp/{a,b}` for `block_brace_expansion`, or `python3 - <<'PY' … PY 2>&1 | grep x` for `block_heredoc_with_pipe_or_redirect`) live and see whether the hook nastygram appears or a matcher prompt appears. If matcher prompt: matcher-first ordering confirmed for that shape too; means our Strategy-2 hooks for Family-3 shapes don't actually intercept live prompts on their target shapes.

**Impact:**
- **Hook (`block_bash_chains.py`):** none. Working as designed — flow-control leader exempts the chain, matcher takes over.
- **Hook (`block_loop_with_pipe.py`):** empirically fires on this command in direct invocation. If matcher-first ordering is real, the hook can't actually intercept the live prompt on this specific shape (matcher goes first), so no user-visible over-fire is happening in practice — the hook's docstring-declared FP class is a phantom on this path. That's an interesting inversion of the earlier concern: what looked like an over-fire risk turns out to be inert because the matcher gets there first. No hook change indicated; the hook's coverage is still useful on parseable-but-body-analyzable shapes (probe D from FINDINGS 2026-06-06 style).
- **Matcher-side (new Family-3 node):** **new Family-3 tree-sitter node name `(string)` joins the row list** — extends the family with a fifth known node. Would be worth promoting to FINDINGS with the probe cells above once run.
- **Matcher-side (ordering / hook precedence):** if the "matcher preempts hooks for Family-3 bails" hypothesis holds, that's an INDEPENDENT durable finding worth its own FINDINGS entry and a note in STRATEGIES.md — it changes the Strategy-2 threat model (deny-hooks CAN'T prevent Family-3 matcher prompts in practice; they only train the model on non-Family-3 misuse). This is the most consequential piece to promote if confirmed.
- **Allow rules:** no fix possible — structural static-analysis bail is pre-allow-list.
- **STRATEGIES.md:** if PRIMARY on `(string)` confirms, add a line — *"Polling loops that use `until [ -n \"$(…)\" ]; do sleep N; done` may prompt on `(string)` if the interpolated command substitution contains a redirect or other unbounded construct. Simpler forms — `until <bare-cmd>; do sleep N; done` or the Monitor tool — sidestep it."* If matcher-first ordering confirms, add a separate line qualifying the reach of Strategy-2 hooks for Family-3 shapes.

**Classification:** matcher-side prompt. TWO distinct promotable findings if the probes confirm: (a) NEW Family-3 node name `(string)` extending the existing family; (b) NEW work-line-level ordering finding — matcher preempts PreToolUse hooks for Family-3 static-analysis bails, meaning our Strategy-2 hooks for those shapes are pedagogically useful (training via nastygram on any path that DOES reach them, e.g. headless/dry-run) but architecturally can't intercept live matcher prompts on their target shapes. **Ready for a deliberate probe session; NOT a hook problem to fix.**

---

### 2026-06-09 — `curl -L -o papers/<long-pdf-name> https://arxiv.org/pdf/<id>` prompts as `Bash(curl *)` despite multiple seemingly-matching arxiv allow rules — RESOLVED 2026-06-09: real cause is CC matcher precedence (ASK > ALLOW), not glob `/`-spanning; fix = removed `Bash(curl *)` from `ASK_RULES`

**Resolution (2026-06-09, verified same session):** All four discriminator probes prompted, including the simplest single-`*` ALLOW (`curl https://arxiv.org/probe-fake-noslash` → prompted as `Bash(curl *) requires confirmation`) and a non-URL-specific ALLOW (`curl -L -o test.pdf https://example.com` should match `Bash(curl -L -o *.pdf *)` — prompted anyway). That falsified Hypothesis 1 (`*` doesn't span `/`) — a true basename with no `/` in the middle `*` slot still prompted — and ruled out 2/3/4 in one stroke. The real cause is **CC matcher precedence: DENY > ASK > ALLOW**. The broad `Bash(curl *)` in ASK preempted every arxiv/PDF ALLOW above it, so the specific allows were architecturally inert.

**Fix:** Removed `Bash(curl *)` from `ASK_RULES` in `update_claude_permissions.py` (kept `Bash(wget *)` — Dan's preference, narrower attack surface). The specific arxiv/PDF ALLOWs now actually fire; unmatched curls fall through to CC's default-for-Bash, which prompts. The prompt-UI text is the discriminator: ASK-rule match shows `"Bash(curl *) requires confirmation"`; default-prompt shows `"Bash(curl <full-command>)"` with no `requires confirmation` framing.

**Behavior matrix (verified mid-session after settings regen):**
| Command | Before | After |
| --- | --- | --- |
| `curl -L -o papers/<name>.pdf https://arxiv.org/pdf/<id>` | prompts `Bash(curl *)` | silent (matches `Bash(curl -L -o * https://arxiv.org/*)`) |
| `curl https://arxiv.org/<path>` | prompts `Bash(curl *)` | silent (matches `Bash(curl https://arxiv.org/*)`) |
| `curl https://example.com` | prompts `Bash(curl *)` | prompts `Bash(curl https://example.com)` (default-for-Bash) |

**Promotable to durable note?** Yes — ASK > ALLOW precedence is a load-bearing CC matcher fact, first concretely pinned down by this incident. Worth a `notes/cc_matcher_ask_preempts_allow.md` if it survives a Claude Code version bump (precedence semantics have shifted in past CC releases). Holding off until cross-session confirmation; the comment in `update_claude_permissions.py` near `ASK_RULES` carries the immediate context.

---

**Original investigation (preserved for posterity — Hypothesis 1 was wrong):**

**Command:**
```
curl -L -o papers/WangX_Plank__2505.17306__polyrefuse_refusal_direction_universal.pdf https://arxiv.org/pdf/2505.17306
```

**Prompt UI text reported by Dan (verbatim):**
> Permission rule Bash(curl *) requires confirmation for this command.

**Context:** Dan-reported real-world prompt on 2026-06-09. Issued from cwd `/Users/dan/code/general-ai-abilities` (academic-paper-download workspace, descendant of `~/code`, inside the trusted root). Standard `~/.claude/settings.json` (global) plus the project's own `.claude/settings.json`. `curl` is in the **global ASK** list (`Bash(curl *)`, settings.json line 196) — so the matcher prompting on `Bash(curl *)` is the documented fall-through when no higher-priority allow rule matches.

**Allow-rule inventory (curl-relevant, verified live this session):**

Global `~/.claude/settings.json` ALLOW (lines 104-111):
- `Bash(curl -o * https://arxiv.org/*)`
- `Bash(curl -L -o * https://arxiv.org/*)` ← **shape-matches today's command literally**
- `Bash(curl https://arxiv.org/*)`
- `Bash(curl -L https://arxiv.org/*)`
- `Bash(curl *arxiv.org*)`
- `Bash(curl -o *.pdf *)`
- `Bash(curl -L -o *.pdf *)`

Project `general-ai-abilities/.claude/settings.json` (per Dan's grep):
- `Bash(curl * arxiv.org*)`
- `Bash(curl * https://arxiv.org/*)`

Project `.claude/settings.local.json`: no curl rules.

**Segments + rules I think should match:** Single segment, no chain (`block_bash_chains.py` short-circuits — no `&&`/`||`/`;`/`|`; non-`curl`-specific hooks N/A). The interesting question is purely matcher-side: which of the seven ALLOW rules above *should* have caught this?

The cleanest candidate is the **global** `Bash(curl -L -o * https://arxiv.org/*)`. Naive fnmatch trace:
- `curl -L -o ` — literal ✓
- `*` → `papers/WangX_Plank__2505.17306__polyrefuse_refusal_direction_universal.pdf` (single whitespace-free token, but contains one `/`)
- ` https://arxiv.org/` — literal ✓
- `*` → `pdf/2505.17306` (contains one `/`)

If `*` is true fnmatch-style (spans any character including `/`), this is a clean match and shouldn't have prompted. It prompted anyway. Likewise `Bash(curl -L -o *.pdf *)` should match if `*.pdf` is allowed to span `/`.

**Hypothesis (ranked):**

1. **(PRIMARY) The matcher's `*` does not span `/`** — i.e. it behaves like a shell **pathname** glob, not fnmatch. Under this model, the middle `*` in `Bash(curl -L -o * https://arxiv.org/*)` would only match `papers` (stopping at the first `/`), not the full `papers/WangX_...universal.pdf` filename arg, so the literal ` https://arxiv.org/` that follows wouldn't line up. Same failure for the per-repo `Bash(curl * https://arxiv.org/*)` and for `Bash(curl -L -o *.pdf *)` (the `*` in `*.pdf` couldn't reach past `papers/`). This single mechanism would explain why **all seven** ALLOW rules silently fail and the matcher falls through to the ASK `Bash(curl *)`. The most parsimonious read. Sibling concern: the same model predicts `Bash(curl -L https://arxiv.org/*)` would also fail on `https://arxiv.org/pdf/2505.17306` because the trailing `*` would have to span `pdf/2505.17306` (one `/`). If trailing `*` IS special-cased (greedy-to-end-of-arg or to-end-of-command), the pattern is "`*` spans `/` only when terminal." That sub-variant is the cheapest to probe.
2. **(SECONDARY) The matcher's `*` does not span whitespace** (Dan's lead) — i.e. each `*` is bounded to one whitespace-separated argv token. Falsified on the strict reading by the global rule `Bash(curl -L -o * https://arxiv.org/*)`: under this model, the middle `*` only has to swallow ONE whitespace-free token (`papers/WangX_...universal.pdf`), which it can do. So pure whitespace-non-spanning doesn't explain the prompt by itself. Holds only as a contributor to (1) (i.e. *both* whitespace and `/` are token-internal boundaries), not as a sole cause.
3. **(TERTIARY) Per-repo `settings.json` *replaces* global ALLOW rather than augmenting it** — i.e. when `/Users/dan/code/general-ai-abilities/.claude/settings.json` exists, only its two curl rules are checked, not the seven global ones. Under this model the global `Bash(curl -L -o * https://arxiv.org/*)` is invisible to the matcher in this session; only `Bash(curl * arxiv.org*)` (which fails — the URL is `/arxiv.org` not ` arxiv.org`) and `Bash(curl * https://arxiv.org/*)` (which needs the middle `*` to span `-L -o papers/.../...pdf`, multiple tokens AND `/`s) are in play, both fail, falls through to ASK. Less likely given CC's documented additive permission semantics, but cheap to discriminate: same command run from a project with NO `.claude/settings.json` of its own would behave differently.
4. **(LONG-SHOT) Anti-obfuscation heuristic on the filename token** — `WangX_Plank__2505.17306__polyrefuse_refusal_direction_universal.pdf` contains `__` (double underscores) and `.17306` (number-segment between dots). Unlikely (no brace/bracket/quote-adjacency, no `\n#`, doesn't match any Family-1 shape we have), but listed because the filename is unusually long and structured. If today's prompt is reproducible with a *shorter* filename in the same shape, this hypothesis dies.

(1) > (3) > (2) > (4) in likelihood. (1) is the architecturally-cleanest read; (3) would be a much bigger finding (changes the mental model of CC's settings hierarchy); (2) is mechanically weaker than (1) and probably folded into it; (4) is the long-tail.

**Cheap discriminator probes (NOT run — curator role):**
- `curl -L -o x.pdf https://arxiv.org/pdf/2505.17306` — basename-only filename token, no `/` after the `-o`. If silent, **(1) is confirmed** (the `/` inside `papers/...` is the trigger). If still prompts, (1) needs further refinement.
- `curl -L -o /tmp/x.pdf https://arxiv.org/abs/2505.17306` — `abs/` instead of `pdf/`; tests whether the trailing-URL `*` spans `/`. If `https://arxiv.org/*` rules silently fail on multi-segment URLs, basically every arxiv pdf URL would prompt — which Dan has *not* reported, suggesting trailing `*` IS greedy-to-end-of-arg (sub-variant of (1)).
- `curl -L -o papers/short.pdf https://arxiv.org/pdf/2505.17306` — same shape as today, short filename. If still prompts, (4) dies and (1) is confirmed.
- Same command run from `/tmp` or a project with no `.claude/settings.json` — discriminator for (3). If today's command becomes silent there, the project's `settings.json` IS subtracting the global rules (or shadowing them somehow).

**Workaround (without probing):** put the URL first — `curl https://arxiv.org/pdf/2505.17306 -L -o papers/...` — matches `Bash(curl https://arxiv.org/*)` on the literal-prefix path, the `-L -o papers/...` tail rides on the terminal `*` (which under the (1)-sub-variant *is* greedy-to-end). Awkward (non-canonical curl arg order), and Dan shouldn't have to reorder args. Alternative: add a project-level allow rule with the filename-path literalized — `Bash(curl -L -o papers/* https://arxiv.org/*)` — which under (1) would split correctly (`papers/` literal, `*` swallows the basename, doesn't need to cross `/`). Cheap if (1) holds.

**Impact:**
- **Hook (`block_bash_chains.py` and all sibling hooks):** none — single-segment plain command, no hook applies. Not a hook problem.
- **Matcher-side:** if (1) confirms, the **`*`-doesn't-span-`/`** model is a load-bearing fact for how every URL/path allow rule should be written — touches lots of existing rules across global+repo settings. Probably promotable to FINDINGS once probed (it isn't a single-construct heuristic like Family 2/3; it's a glob-semantics rule about the matcher's pattern language itself).
- **Allow rules:** if (1) holds, the right-shaped rule for this download workflow is something like `Bash(curl -L -o papers/* https://arxiv.org/*)` (project-level) — preserves the `papers/` literal so the `*` only has to swallow the basename. Strategy 1, not Strategy 2.
- **STRATEGIES.md:** if confirmed, worth a line: "Allow-rule `*` doesn't span `/` (likely shell-pathname-glob, not fnmatch). Write rules with literal directory prefixes when the arg is a path."

**Classification:** matcher-side prompt; no hook applies. Most likely a **glob-semantics finding** (the `*` in allow rules behaves like a shell pathname glob, doesn't span `/`) — would explain seven seemingly-matching rules all silently failing in one mechanism. **NOT a hook problem; NOT a missing rule per se (rules exist but their `*`s can't reach across the `/` in the filename); a rule-authoring guideline once the matcher's glob semantics are pinned down.** Held in Pending; promotion bar is the basename-vs-path discriminator (`curl -L -o x.pdf https://arxiv.org/pdf/<id>` silent vs prompt).

---

### 2026-06-12 — `gh issue create --title '… hardware-eval …'` denied; `hardware-evaluation` runs — refined hypothesis: matcher `Bash(eval)` DENY fires on the **shape `\beval\s+\S`** anywhere in command string

**Status:** Pending → ready-to-promote-to-FINDINGS. Hypothesis discriminated by HITL probe round 2026-06-12. The original "5-cell probe" plan (numbered 1–5 in the prior draft) is **RESOLVED** — probes complete, mechanism pinned down to a more specific shape than the original substring-scan framing.

**Command (Attempt 1 — heredoc body, DENIED):**
```
gh issue create --repo danparshall/dotfiles --title '[2026-06-12] Respond to Cambridge hardware-eval follow-up invitation' --label task --body "$(cat <<'EOF'
Got an email follow-up invitation for the Cambridge hardware evaluation program (July 2026 cohort I applied to). Respond TODAY. Career-track item — sits alongside MATS Autumn 2026 (applied) and Anthropic Fellows (dotfiles#26) as parallel applied-AI pathways.

Details to fill in when responding:
- Cohort dates / location confirmation
- What the follow-up specifically asks (interview slot, written response, references?)
- Deadline on the invitation itself

Convo: none
Branch: main
EOF
)"
```

**Command (Attempt 2 — same title, body-file instead of heredoc, DENIED):**
```
gh issue create --repo danparshall/dotfiles --title '[2026-06-12] Respond to Cambridge hardware-eval follow-up invitation' --label task --body-file /tmp/cambridge_task_body.md
```

**Command (Control — `hardware-eval` → `hardware-evaluation`, otherwise identical body-file command, RAN; filed as https://github.com/danparshall/dotfiles/issues/39):**
```
gh issue create --repo danparshall/dotfiles --title '[2026-06-12] Respond to Cambridge hardware-evaluation follow-up invitation' --label task --body-file /tmp/cambridge_task_body_v2.md
```

**Context:** Dan-reported real-world deny on 2026-06-12. Session was filing a career-track task issue in the dotfiles repo (cwd `~/code/dotfiles`). Standard global `~/.claude/settings.json` permission state (no pclaude/mclaude alias noted). Both `gh issue create` calls earlier in the same session ran cleanly with titles that did NOT contain `eval`:
- `[2026-06-12] Purge "napkin" references from dotfiles`
- `[2026-06-15] Read Trammell & Korinek (2023) "Economic Growth Under Transformative AI"`

A concurrent agent in `lobby_analysis` also filed an issue in the same time window (`tests/conftest.py: autouse Postgres fixture fires on whole suite, not just backend tests`) — no `eval` substring, no problem. Both attempts above were denied with the bare "has been denied" pattern (no hook nastygram). The body-file second attempt has no heredoc, so heredoc-class hooks are mechanically inapplicable.

**Permission state at deny:**
- `Bash(eval)` in global DENY list (CLAUDE.md: *"eval (dynamic code execution — defeats literal-string deny matching)"*)
- `Bash(gh *)` in global ALLOW list
- No project-local `.claude/settings.local.json` in `~/code/dotfiles`

**Hooks loaded (per `claude-hooks/`):** `block_absolute_path_py_verb`, `block_bash_chains`, `block_brace_expansion`, `block_brace_quote_heredoc`, `block_cd_git`, `block_heredoc_with_pipe_or_redirect`, `block_loop_with_pipe`, `block_newline_hash_in_quoted_arg`, `use_uv_run_python`, `require_finish_convo`, `api_budget`. **None fired the deny** — the diagnostic was generic ("has been denied"), unlike our nastygrams. So this is built-in matcher behavior, NOT a dotfiles hook.

**Segments + rules I think should match:**
- One segment, leading verb `gh`. `Bash(gh *)` should cleanly swallow the entire rest of the command line.
- No `&&`/`||`/`;`/`|` chain → `block_bash_chains.py` short-circuits.
- No heredoc on attempt 2 (body-file) → `block_brace_quote_heredoc.py` / `block_heredoc_with_pipe_or_redirect.py` cannot apply.
- Attempt 1 has a heredoc body, but the body contains no `{"`/`['` brace-quote pattern and no `<<` co-occurring with `|`/`>` on the open line — so neither heredoc-class hook matches that either.

Per current FINDINGS, this should run silently. That it didn't — and that flipping ONE substring (`eval` → `evaluation`) inside a quoted `--title` argument flipped deny→approve — was the puzzle. Now resolved by the 2026-06-12 probe round below.

**Refined hypothesis (PRIMARY, post-probe):** The matcher's actual rule for `Bash(eval)` DENY is roughly:

> **`\beval\s+\S`** — the literal word `eval` as a complete word (per `\b`, which treats `-` as a word boundary), followed by whitespace, followed by at least one non-whitespace character.

In plain English: *"the literal word `eval` followed by another argument, anywhere in the command string, including inside quoted args."* The matcher is modeling "eval being invoked with arguments" — and it fires on any text that *looks* like that, including innocent natural-language phrases where a hyphenated word ends in `-eval` and the next word starts after a space.

The original "substring scan" framing in the pre-probe draft was too broad. The actual scope is narrower (requires whole-word `eval` + whitespace + non-whitespace next) but more specific in its trigger shape: it's modeling an *invocation shape*, not just a token presence.

**Full probe scoreboard (2026-06-12 HITL; all probes run as bare `echo '...'` to control for verb-specificity; outcomes are matcher-level — no hooks involved, verified separately):**

| Command | Outcome | Mechanism |
|---|---|---|
| `echo eval` | ALLOW | `eval` complete word at end, no following arg |
| `echo evaluator` | ALLOW | `eval` not a complete word (no right boundary in `evaluator`) |
| `echo 'hardware-eval'` | ALLOW | `eval` complete word at end of quoted string |
| `echo 'foo eval'` | ALLOW | `eval` complete word, but at end — no following arg |
| `echo 'Cambridge hardware-eval'` | ALLOW | same — `eval` at end |
| `echo '[2026-06-12]'` | ALLOW | bracket-only control, no `eval` |
| `echo '[2026-06-12] hardware-eval'` | ALLOW | `eval` at end despite bracket |
| `echo '[xyz] hardware-eval'` | ALLOW | non-date bracket; still `eval` at end |
| `echo 'evaluator follow-up'` | ALLOW | `eval` not whole word (no `\b` on right of `eval` in `evaluator`) |
| `echo 'hardware-eval-foo follow-up'` | ALLOW | `eval` whole word (bounded by `-` both sides), but next char is `-` not whitespace |
| `echo 'eval foo'` | **DENY** | classic `eval <arg>` shape |
| `echo 'hardware-eval follow-up'` | **DENY** | `-eval` then space then `follow-up` — fits `\beval\s+\S` |
| `echo 'hardware-eval invitation'` | **DENY** | same pattern |
| `echo 'hardware-eval follow-up invitation'` | **DENY** | same |
| `echo '[2026-06-12] Respond to Cambridge hardware-eval follow-up invitation'` | **DENY** | original failing string |
| `gh issue list --search 'hardware-eval'` | ALLOW | `eval` at end of quoted search term (consistent — not gh-specific) |

**Cross-check with the original Cambridge denial:** the rule matches at `hardware-eval follow-up` — `eval` whole-word (bounded by `-` left, ` ` right), then ` `, then `follow-up`. DENY. The control rename to `hardware-evaluation` clears because `eval` is not a complete word in `evaluation` (no `\b` on the right — `u` follows). ALLOW. Fully consistent.

**Word-boundary semantics confirmed:** the matcher's `\b` treats `-` as a word boundary (matching standard regex semantics) — that's why `hardware-eval` parses `eval` as a complete word even though the left neighbor is `-`. Probes also confirm a third-char-after-`eval` requirement: a *bare* `eval` (no following arg) is silent regardless of context; and an `eval-XXX` shape (no whitespace before next token) is silent. The shape it pattern-matches is specifically "invocation with at least one arg."

**Refined workaround ladder** (replaces the previous "expand `eval` → `evaluation`" one-liner):

1. **Write `evaluation` instead of `eval`** — best; also reads better in policy prose anyway. Universal fix because `evaluation` never has `\b` on the right of `eval`.
2. **Put `eval` at the end of the string** — works (no following arg = no match), but fragile to editing.
3. **Compound-hyphenate further** — `hardware-eval-XX` works because `eval` ends in `-` not whitespace, but ugly.
4. **Use a different word entirely** — `assessment`, `review`, `audit` (the AI-policy domain has plenty of synonyms).

**Impact:**
- **Hooks:** none fired; no hook change recommended. This is matcher-side.
- **Matcher-side:** **NEW Family-1 sub-row** — DENY-rule verb tokens matched as `\b<verb>\s+\S` (whole-word + whitespace + next-token) anywhere in the command string. Architecturally distinct from existing Family-1 rows (which scan for *patterns* like `{"` or `\n#`); this scans for the *shape of an invocation* using a user-supplied DENY verb literal. Verb-agnostic across the *leading* verb of the command (confirmed identical behavior on `echo` and `gh`); the trigger is the *DENY verb* token inside the args.
- **User-CLAUDE.md (`Bash(eval)` DENY entry):** the comment *"eval (dynamic code execution — defeats literal-string deny matching)"* is correct about the threat — and the implementation is at least *trying* to model invocation shape (not pure substring). It still over-fires on natural-language `<word>-eval <next-word>` constructions, but the over-fire surface is narrower than feared.
- **STRATEGIES.md:** worth a line — *"Natural-language `<word>-eval <next-word>` constructions in any quoted argument trigger the `Bash(eval)` DENY (pattern: `\beval\s+\S`). Workaround: write `evaluation` instead — universal fix, reads better in policy prose anyway. Secondary dodges: put `eval` at end of string; compound-hyphenate (`hardware-eval-XX`); use synonyms (`assessment`, `review`, `audit`)."* Real cost on `gh issue create` / `git commit -m` / `gh pr create` flows where AI-policy work (which talks about *evaluations* a lot) routinely puts the word `eval` in argument text.
- **Allow rules:** no allow-rule fix possible — a DENY-rule shape match is by construction pre-allow-list (DENY > ALLOW). The only structural fix would be a different DENY-rule shape (e.g. an option to scope DENY to argv[0]), which Dan doesn't control.

**Original 5-cell probe plan: RESOLVED.** The discriminating cells were run in the 2026-06-12 HITL round (scoreboard above). Specifically: `echo evaluator` (= cell-2-analog) ALLOWED → matcher is `\b`-anchored on the right, not pure substring. `echo 'hardware-eval'` (= cell-4) ALLOWED → verb-agnostic across leading verb, but also reveals the *additional* `\s+\S` constraint (the trailing context matters, not just the boundary). The probe outcomes refined the framing beyond what cells 1–5 alone would have shown: the rule is `\b<verb>\s+\S`, not just `\b<verb>\b`.

**Classification:** matcher-side built-in. **Family-1 sub-row, shape `\b<verb>\s+\S`.** Not pure substring (the original entry's framing); not verb-position-specific on the leading verb. Specifically pattern-matching the *shape* of an invocation of a DENY-listed verb token, anywhere in the command string. Held in **Pending → ready-to-promote-to-FINDINGS** at Dan's discretion. NOT a hook bug. NOT a fixable allow-rule gap. The user-workflow workaround (write `evaluation`) is cheap and immediate; the structural fix isn't user-controllable.

---

### 2026-06-05 — apparent A/B asymmetry in `;`-chain blocking (`ps;echo;ps` ran vs. `echo;ls;for…done;sks` DENIED) — RESOLVED on inspection: NOT an anomaly, `ps` IS blanket (`Bash(ps *)`), and Command B contains a mid-chain `for`-loop

**Command A — ran without prompt or deny (early-session claude-exit verification ceremony):**
```
ps -p 46352 -o pid,ppid,comm; echo "---"; ps -p 71693 -o pid,ppid,comm,command
```

**Command B — DENIED by `block_bash_chains.py` (same session, later):**
```
echo "=== profile dir now ==="; ls -la /Users/dan/.nori/profiles/researcher/ 2>&1; echo "=== are custom files still symlinks? ==="; for f in AGENTS.md CLAUDE.md nori.json; do printf "%s -> " "$f"; readlink /Users/dan/.nori/profiles/researcher/$f 2>&1 || echo "(REAL FILE, symlink stomped)"; done; echo "=== active skillset ==="; sks current 2>&1
```

**Context:** Dan-reported, 2026-06-05, machine `Dans-MacBook-Pro`. Standard `~/.claude/settings.json` permission state (no pclaude/mclaude alias noted). Command A ran during the claude-exit SessionStart verification ceremony; Command B was an interactive Nori-profile-symlink inspection later in the same session. Report framed both as a hook-behavior *asymmetry* — two structurally similar `;`-chains, one passed, one denied — under the premise that `ps` is NOT allow-listed (Dan checked `update_claude_permissions.py` lines 66-169) and so Command A *should* have been a mixed chain and denied like Command B.

**Segments + rules — Command A (`ps`, `echo`, `ps`):**
- `ps -p 46352 -o pid,ppid,comm` → leading verb `ps`
- `echo "---"` → `echo`
- `ps -p 71693 -o pid,ppid,comm,command` → `ps`

All three leading verbs are in `BLANKET_VERBS`. **`ps` is blanket** — `_blanket_verbs.py` line 56 — derived from the `Bash(ps *)` ALLOW rule at `update_claude_permissions.py` **line 182** (`Bash(psql *)` is the nearby line 387). The premise that `ps` is not allow-listed is the error: the rule sits *below* the 66-169 line range Dan inspected. So Command A is an **all-blanket `;`-chain**: `block_bash_chains.py` traces to `sys.exit(0)` (pass-through per Plan 01), the matcher per-segment-allows `ps`/`echo`/`ps`, and it runs silently. Working exactly as designed.

**Segments + rules — Command B:** Command B does NOT begin with `for`, so `FLOW_CONTROL_RE` (anchored `^\s*(for|while|…)`) does **not** exempt it — it begins with `echo`. The hook therefore proceeds to `strip_inert` + `CHAIN_RE.split` (`&&|\|\||;`), which shreds the embedded `for … do … done` loop into pseudo-segments by splitting on its internal `;` and `||`. Leading tokens across the resulting segments: `echo`, `ls`, `echo`, **`for`**, **`do`** (`printf`), **`readlink`**, `echo`, **`done`**, `echo`, `sks`. `readlink` (line 61) and `sks` (line 66) ARE blanket — but `for`, `do`/`printf`, and `done` are NOT. The first non-blanket leading verb (`for`) trips `emit_block()` → DENY. Also working as designed.

**Hypothesis:** No anomaly. The report's own candidate (c) — "`ps` is being treated as blanket via some path I'm not seeing" — is exactly correct: `Bash(ps *)` → `BLANKET_VERBS`. Candidates (a) parse-fail-default-open, (b) ceremony special-casing, and (d) SessionStart timing are all unnecessary; the hook has no path-default-open and no ceremony/timing branch — an all-blanket chain passes by design regardless of when it runs. The two commands are NOT structurally similar in the way that matters to the hook: A is all-blanket; B carries a mid-`;`-chain `for`-loop whose keywords (`for`/`do`/`done`) and `printf` are non-blanket. The asymmetry is the hook drawing exactly the line it's designed to draw.

**Secondary observation worth flagging (the one real hook nuance here):** B was denied because a `for`-loop sitting **mid-chain** (not at command position 0) escapes `FLOW_CONTROL_RE` (which only anchors at the start) and gets treated by `CHAIN_RE.split` as if its `;`-delimited loop body were chain segments. The deny outcome is arguably *correct* (Dan should split this into separate Bash calls anyway), but the *mechanism* is incidental — the hook isn't recognizing "this is a loop," it's mis-segmenting the loop and catching `for`/`do`/`done` as non-blanket verbs. A loop whose every body-verb happened to be blanket (e.g. `echo a; for f in x y; do echo "$f"; done`) would still deny on the bare `for`/`do`/`done` tokens. Not a bug given the train-to-split mandate, but it means "mid-chain flow control" is denied via a different code path than "leading flow control" (which is exempted). If a future weirdo reports a *legitimate* mid-chain loop being denied, this is the mechanism.

**Impact:**
- **Hook (`block_bash_chains.py`):** none. Both outcomes are working-as-designed (A: all-blanket pass-through; B: mixed-chain DENY, driven by the mis-segmented loop keywords). No change.
- **Matcher-side:** none. Command A never reached a matcher *prompt* — it was silently allowed.
- **Allow rules:** none. `Bash(ps *)` already exists and already feeds `BLANKET_VERBS`.
- **Doc nuance:** the standing "mixed chains PROMPT/DENY; all-blanket chains pass silently" model held perfectly here once `ps`'s blanket status is recognized. The only thing to carry forward is the secondary observation above (leading vs. mid-chain flow-control are handled by different code paths).

**Classification:** NOT a hook problem, NOT a matcher problem, NOT a missing allow-rule. **User-premise error** — `ps` is allow-listed (`Bash(ps *)`, line 182, below the inspected range) and is a blanket verb; both A and B behaved per the documented Plan-01 model. Recorded for the audit trail and for the mid-chain-flow-control mechanism note.

---

### 2026-06-05 — three smoke-check prompts on direct `.py` invocation — **RESOLVED via Strategy-2 hook**

**Resolution (2026-06-05, same day):** Strategy 2 (deny hook). **Not a matcher heuristic** — plain allow-rule miss; no Family-3 / Family-1 / built-in bail involved. Dan chose Strategy 2 over Strategy 1 (path-allow-rule like `Bash(/Users/dan/code/dotfiles/*.py *)`) to train the canonical `python3 <path>` interpreter-leading form rather than expand the allow surface — same training-pressure rationale as the chain hook's mixed-chain hard-fail.

Shipped `claude-hooks/block_absolute_path_py_verb.py` (sibling architecture of `block_brace_expansion.py` / `block_heredoc_with_pipe_or_redirect.py`, distinct epistemic class). Regex anchored at command start: `^\s*['"]?\S*/\S*\.py['"]?(?:\s|$)`. The required `/` distinguishes a path (`./foo.py`, `/abs/foo.py`, `subdir/foo.py`) from a bare-verb `foo.py` (out of scope; normal allow-rule miss without our intervention). The boundary `(?:\s|$)` after `.py` prevents `path.py.bak` from matching. **No `strip_inert` helper** — the anchor + boundary already prevent the cases strip would defensively cover (`cat "/path/to/foo.py"` — leading verb `cat` has no `/`; `$(/path/to/foo.py)` — `)` after `.py` fails the boundary), and stripping would BREAK the leading-quote DENY cases (`"/Users/dan/foo.py" arg` would become `"" arg` after strip, no match — divergence from Plan 03 §46 noted in implementation). 37-case behavior test (`test_block_absolute_path_py_verb.py`) green; full dotfiles suite 109/109 green. Wired via `ensure_block_absolute_path_py_verb_hook()` in `update_claude_permissions.py` + install.sh symlink section.

Live fire-test confirmed: re-running `/Users/dan/code/dotfiles/claude-hooks/test_block_brace_expansion.py` in this session hard-denies with the nastygram; `python3 <same-path> 2>&1 | tail -3` runs silent; `cat <.py file>` silent; the chained shape (`<.py path> && echo done`) is hard-denied (both block_bash_chains and our hook emit a deny when invoked directly; in the live test our nastygram surfaced — a minor deviation from Plan 03 §210's assumption about hook ordering, but functionally a hard-deny either way).

Lesson captured in `STRATEGIES.md` (new item #6) and `CLAUDE.md` standing-context bullet. **NOT added to FINDINGS.md** — this is allow-rule-miss territory, not a matcher heuristic; adding it would dilute that file's epistemic precision. Provenance link from STRATEGIES + this INCOMING entry + Plan 03 is sufficient.

---

**Commands (three redundant smoke-checks during the brace-expansion ship session, all prompted Dan):**
```
/Users/dan/code/dotfiles/claude-hooks/test_block_brace_expansion.py 2>&1 | tail -3
/Users/dan/code/dotfiles/claude-hooks/test_block_brace_expansion.py 2>&1 | tail -1
/Users/dan/code/dotfiles/claude-hooks/test_block_brace_expansion.py 2>&1 | tail -5
```
(All three were variations of the same brace-expansion-hook test invocation, run for verification during the just-shipped hook's smoke phase.)

**Context:** Dan-reported triple-prompt on 2026-06-05 during smoke-checks of the just-shipped `block_brace_expansion.py`. Standard `~/.claude/settings.json` permission state, no pclaude/mclaude alias. The repeated-shape detection itself (three identical-shape prompts within minutes) is what triggered the report.

**Diagnosis:** Live verification against `~/.claude/settings.json` allow list — confirmed contains `Bash(python *)` / `Bash(python3 *)` / `Bash(bash *)` and a path-allow-rule `Bash(/Users/dan/code/dotfiles/*.sh *)` (which is why `./install.sh 2>&1 | tail -50` runs silent), but **no rule covers `.py` paths in verb position**. So invoking a `.py` script directly via its absolute or relative path puts an unrecognized "verb" at command start → matcher soft-prompts. The 2026-06-05 Family-3 matrix already established that `2>&1 | tail` on an allow-listed verb is silent, so the redirect/pipe tail is not the trigger. Discriminator confirmed by inspection (no probe needed).

**Hook trace (by inspection):**
- `block_bash_chains.py` → exits 0 (no chain operators).
- `block_brace_quote_heredoc.py` / `block_heredoc_with_pipe_or_redirect.py` / `block_brace_expansion.py` → all exit 0 (no heredoc, no brace expansion, no brace+quote).
- `block_cd_git.py` / `use_uv_run_python.py` → not applicable.

So all existing hooks correctly pass through. The prompt was a normal matcher allow-rule miss on the leading `.py`-path token.

**Classification:** allow-rule miss, NOT a matcher heuristic. Fixable in principle by Strategy 1 (path-allow-rule) but resolved via Strategy 2 (hook) for training reasons. The Strategy-1 option remains viable if Dan ever changes the training-pressure judgment.

---

### 2026-06-05 — `mkdir && mv … {a,b}__…__run{1,2,3}.json … && ls …` — three-segment `&&` chain with brace-expansion in the `mv` segment — **RESOLVED via Strategy-2 hook**

**Resolution (2026-06-05, same day):** Strategy 2 (deny hook). HITL discriminator probe `ls /tmp/{a,b}` (minimal possible shape — allow-listed verb via `Bash(ls *)`, single segment, no chain, no quotes, no heredoc, no redirect, no pipe) PROMPTED with Dan reporting the matcher's reason text as **"Brace expansion"**. This falsifies all of the secondary hypotheses ((1b) multi-group cross-product, (1c) hyphens/dots in alternative contents, (2) glob-tokenization failure on `mv`, (3) chain-context interaction) and confirms hypothesis (1a) — **brace expansion alone, in any unquoted shell-argument position, triggers a Family-3 static-analysis bail**. This is the second Family-3 row after heredoc+pipe/redirect (FINDINGS 2026-06-05); the bail is structural/grammatical (matcher cannot statically enumerate runtime brace expansion), pre-allow-list, not overridable via `Bash(...)` rules.

Shipped `claude-hooks/block_brace_expansion.py` (sibling of `block_heredoc_with_pipe_or_redirect.py`): regex `(?<!\$)\{[^{}\s]*(?:,|\.\.)[^{}\s]*\}` after stripping heredoc bodies and quoted/substituted regions. False-positive guards: bash code blocks (`{ cmd; }` — space after `{`), parameter expansion (`${VAR:-default,foo}` — negative lookbehind), find placeholders (`{}` — no `,` or `..`), Python set/dict literals in heredoc bodies (stripped). Wired via `ensure_block_brace_expansion_hook()` in `update_claude_permissions.py`, install.sh symlink section added, `chmod +x` confirmed by `test_hooks_executable.py`. 33-case behavior test (`test_block_brace_expansion.py`) green; full dotfiles suite 108/108 green. Live fire-test confirmed: re-running `ls /tmp/{a,b}` in this session is now hard-denied with the nastygram, which routes to enumerate-as-separate-Bash-calls (`mv /p/a /dest/` then `mv /p/b /dest/`).

Lesson captured in `FINDINGS.md` (entry 2026-06-05, NEW Family-3 row #2) and `STRATEGIES.md` (new item #5 in the Write-then-run/Strategy-2 list).

---

**Command:**
```
mkdir -p /Users/dan/code/lobby_analysis/.worktrees/wi-ralph-cpi-renewal-cadence/docs/active/wi-tier1-direct-read/results/tier_1/WI_2025/_pre_v2_1_binarycell_vocab_fix && mv /Users/dan/code/lobby_analysis/.worktrees/wi-ralph-cpi-renewal-cadence/docs/active/wi-tier1-direct-read/results/tier_1/WI_2025/{claude-opus-4-7,gpt-5.2-2025-12-11}__enforcement_and_audits__run{1,2,3}.json /Users/dan/code/lobby_analysis/.worktrees/wi-ralph-cpi-renewal-cadence/docs/active/wi-tier1-direct-read/results/tier_1/WI_2025/_pre_v2_1_binarycell_vocab_fix/ && ls /Users/dan/code/lobby_analysis/.worktrees/wi-ralph-cpi-renewal-cadence/docs/active/wi-tier1-direct-read/results/tier_1/WI_2025/_pre_v2_1_binarycell_vocab_fix/
```
(description line shown: "Archive yes/no-prompt dispatch results (negative-result evidence for BinaryCell vocab finding)")

Dan's annotation on the report: **"Brace expansion"** — flagging the two brace-expansion patterns in the `mv` segment:
- `{claude-opus-4-7,gpt-5.2-2025-12-11}` (2 alternatives)
- `{1,2,3}` (3 alternatives)
Together they expand at shell-runtime to 2 × 3 = 6 source filenames the `mv` would touch.

**Prompt UI text reported by Dan:** not captured this round (Dan only annotated "Brace expansion"). The single most-valuable missing datum — same lesson as the 2026-06-04 cd-compound entry. If the reason text named something like `"Contains shell syntax (brace_expansion) that cannot be statically analyzed"` (Family 3 shape, FINDINGS 2026-06-05) it discriminates immediately.

**Context:** Dan-reported real-world prompt on 2026-06-05. Issued by a Claude session doing `lobby_analysis` work (cwd: a worktree under `/Users/dan/code/lobby_analysis/.worktrees/wi-ralph-cpi-renewal-cadence` — note path is descendant of `~/code`, inside the trusted root, no path-ancestor heuristic applicable). Standard `~/.claude/settings.json` permission state (no pclaude/mclaude alias noted). All three verbs (`mkdir`, `mv`, `ls`) are in the current `BLANKET_VERBS` set (verified live in `/Users/dan/code/dotfiles/claude-hooks/_blanket_verbs.py`).

**Hook trace (by inspection — not piped this session; curator no-probe rule):**
- `block_bash_chains.py` → **exits 0 (pass-through)** per the post-Plan-01 logic (FINDINGS 2026-06-04 / 2026-06-05): no `cd`/`git`, no flow control, no heredoc, no whitelisted prefix; `CHAIN_RE` matches `&&`; split into 3 segments (`mkdir -p …`, `mv … {a,b}__…run{1,2,3}.json …`, `ls …`); `LEADING_VERB_RE` extracts `mkdir`, `mv`, `ls`; **all three are in BLANKET_VERBS**, so the loop never calls `emit_block()` and the hook `sys.exit(0)`s. The chain hook is **correctly** letting this through to the matcher — this is exactly the "all-blanket chain passes silently" case the redesign was built for. **So the chain hook is NOT the source of the prompt** (answering the report's first-order question — the chain hook did NOT hard-block; it correctly passed the all-blanket chain to the matcher, which is the actor that prompted).
- `block_brace_quote_heredoc.py` → not applicable. No heredoc; the brace-quote pattern it checks for is literally `{`/`[` immediately followed by `"`/`'`, and our braces here are followed by `c` (`{claude-…`) and `1` (`{1,2,3}`). Different brace pattern, different hook.
- `block_heredoc_with_pipe_or_redirect.py` → not applicable. No heredoc.
- `block_newline_hash_in_quoted_arg.py` → not applicable.
- `block_cd_git.py` → not applicable.
- `use_uv_run_python.py` → not applicable.

So the chain reached the matcher with all hooks correctly short-circuiting. **The prompt is matcher-side, not hook-side.**

**Resolving Dan's first-order question explicitly:** the report framed this as "why did a 3-segment `&&` chain reach permissioning instead of being hard-blocked." Answer: because the chain hook **was redesigned on 2026-06-04 to NOT hard-block all-blanket chains** (Plan 01 / `block_bash_chains.py` line 196 onward) — that's the documented current behavior. The hard-block applies only to *mixed* chains (at least one segment with a non-blanket leading verb). All three verbs here (`mkdir`/`mv`/`ls`) are blanket, so the hook deliberately let the chain through. **No anomaly on the hook side.** What looks at first glance like "the chain hook let an `&&` chain through to a prompt" is actually the redesign working as intended; the second-order question (why the matcher then prompted on the brace-expansion) is the real puzzle.

**Hypothesis (matcher-side; ranked):**

1. **(PRIMARY) Family-3 static-analysis bail on brace expansion** — same architectural family as FINDINGS 2026-06-05 (heredoc + pipe/redirect → "cannot be statically analyzed"). A brace expansion `{a,b,c}` in an `mv` argument expands at shell-runtime into multiple distinct filenames the matcher cannot enumerate without running the shell. The matcher, doing a real-grammar AST parse (tree-sitter-bash has a `concatenation` / brace-expansion node), can detect the brace-expansion construct but **cannot statically bound the set of file paths it will produce** — which is exactly the unbounded-effect shape the Family-3 heuristic refuses to auto-approve. Cleanest fit for the architecture pattern already established; the reason text (if it followed the Family-3 form) would likely read `"Contains shell syntax (brace_expansion) that cannot be statically analyzed"` or equivalent. This would be a **NEW Family-3 trigger** (Family-3 currently has only heredoc-co-occurring-with-pipe/redirect).
2. **(SECONDARY) `Bash(mv *)` glob doesn't span the literal `{`/`,`/`}` characters** — the trailing-glob hypothesis: the matcher tokenizes the command and the `*` in `Bash(mv *)` doesn't swallow argument-words containing brace-expansion syntax. Less parsimonious; would also predict prompts on `mv foo{1,2}` in arbitrary contexts, which we haven't observed (though we also haven't probed). Architecturally weaker than (1) — globs usually swallow everything until end-of-word/end-of-command, including unusual characters.
3. **(TERTIARY) Brace expansion treated as a Family-1 lexical anti-obfuscation pattern** — analogous to brace+quote / `\n#` / backslash-whitespace, the matcher might run a byte-pattern scan for `{<word>,<word>...}` shapes and flag them as potential shell-expansion obfuscation. The threat model would be: `{rm,/tmp/x}` or `${IFS}`-style trickery. Less likely because plain alphabetic brace expansion is a standard bash feature with no obvious obfuscation angle (unlike `{"...":"..."}` which mimics shell parameter expansion `${...}`), but worth keeping on the table — Family 1 has surprised us before.

(1) > (3) > (2). (1) and (3) are not mutually exclusive — (1) is a structural/grammatical bail; (3) is a lexical scan. Distinguishing them: (1) would also fire on a brace-expansion with a single comma (`{a,b}`) regardless of where it appears in the command line; (3) might specifically fire on brace expansions matching some byte-pattern heuristic.

**Important note on the first-order question (chain hook timing):** This case is a **deliberate consequence of the Plan 01 redesign**, not a bug. Before 2026-06-04 the chain hook hard-blocked any chain on `&&`/`||`/`;`. After 2026-06-04 (current state) it only hard-blocks *mixed* chains — chains where at least one segment's leading verb isn't blanket. The matcher then handles all-blanket chains itself (silent-allow if it's happy, prompt if some other heuristic fires). The redesign was justified by FINDINGS 2026-06-04 showing the matcher per-segment-checks chains, so all-blanket chains were being friction-blocked when the matcher would have allowed them. **Today's weirdo is the first observation of a matcher prompt on an all-blanket chain since the redesign** — i.e., the matcher heuristic that fired today is one that *survives* per-segment-blanket-checking. That's noteworthy independent of which specific heuristic it is.

**Cheap discriminator probes (NOT run — curator role; deferred to next deliberate probe session):**
- `mv /tmp/foo{1,2}.txt /tmp/dest/` after `touch /tmp/foo1.txt /tmp/foo2.txt /tmp/dest/` — single-segment, no chain, isolates brace expansion in an `mv`. If it prompts → brace-expansion-in-mv is the trigger and chain context is irrelevant. If silent → today's prompt needs the chain context too, more like a compound interaction (cf. the 2026-06-03 cd-compound built-in).
- `ls /tmp/{a,b}` after `touch /tmp/a /tmp/b` — even cleaner: brace expansion on `ls`, no destructive verb. If this prompts, brace expansion alone is the trigger regardless of verb (consistent with Family-3 static-analysis bail).
- `ls /tmp/{a,b,c,d,e,f,g}` — does the *count* of alternatives matter? Family-3 says no (any unbounded-set construct triggers); a "many alternatives = suspicious" heuristic would say yes.
- `mv "/tmp/foo1.txt" "/tmp/dest/"; mv "/tmp/foo2.txt" "/tmp/dest/"` — no brace expansion, two literal `mv`s instead. Should be silent (modulo `;`-chain — would need separate calls anyway). Establishes the no-brace baseline.
- If today's command had been broken into three SEPARATE Bash calls (the chain-hook's training pressure pre-Plan-01), the brace-expansion `mv` would have still prompted on its own — confirming the trigger is brace-expansion, not chain context. Worth re-running the command as a single-`mv` call in a clean session.

**Workaround (without running a probe):** if Claude legitimately needs to move 6 files matching a brace-pattern, the safe path is either (a) `for f in file1 file2 ...; do mv "$f" dest/; done` — but that's flow-control which `block_bash_chains.py` would skip but the matcher might flag for unrelated reasons, and 6 separate `mv` calls is cleaner; (b) glob-then-mv: `mv /path/to/{prefix}*.json /dest/` if the desired files share a common prefix not shared with others — but here the file set is two *non-prefix-sharing* model names × three runs, which doesn't reduce to a single glob; (c) **six separate `mv` Bash tool calls** — boring, but each is a single-segment plain-arg `mv` that should pass cleanly. Worth a STRATEGIES.md line: "Brace expansion in destructive verbs (mv/cp/rm) may trip a static-analysis bail; expand it to separate Bash tool calls."

**Impact:**
- **Hook (`block_bash_chains.py`):** none — working as designed per Plan 01. The all-blanket pass-through is the correct behavior; the prompt is the matcher's, not the hook's. **Confirms a class of real-world prompt the redesigned hook deliberately doesn't catch.**
- **Hook (`block_brace_quote_heredoc.py`, `block_heredoc_with_pipe_or_redirect.py`, others):** none — none applicable.
- **Matcher-side:** if (PRIMARY) holds, **NEW Family-3 row**: brace-expansion in any verb context → static-analysis bail. Same family as the heredoc+pipe/redirect row added 2026-06-05. Architecturally clean and would tie up a real class of false positives. Worth promoting if even one targeted probe lands.
- **Allow rules:** no allow-rule fix possible if (1) holds — static-analysis bails are pre-allow-list (same class as Family 1/2 built-ins and the heredoc+pipe bail). If (2) holds (glob-tokenization), a narrower rule wouldn't help either — `Bash(mv {…} …)` literal isn't a thing.
- **STRATEGIES.md:** worth adding a line under the static-analysis-bail / Family-3 discussion: "Brace expansion (`{a,b,c}`, `{1,2,3}`) in shell arguments may also trigger a static-analysis bail prompt (pending probe confirmation). Workaround: separate Bash tool calls per expanded path."
- **Probe priority:** medium-high. Cheap 5-variant discriminator above; (1) vs (2) vs (3) is well-shaped and the outcome materially expands the FINDINGS map. If (1) confirms, Family 3 gains a second row and the family's predictive power (static-analysis bail on unbounded-effect constructs) gets stronger evidence.

**Classification:** matcher-side prompt, NOT a hook bug (chain hook deliberately allowed the all-blanket chain per Plan 01; no other hook applies), NOT a fixable allow-rule gap (any matcher built-in bail is pre-allow). The most architecturally-coherent read is a NEW Family-3 static-analysis bail on brace expansion; pending probe confirmation. The first-order "why did the chain hook let this through" question has a clean answer (deliberate Plan-01 behavior on all-blanket chains); the second-order "why did the matcher prompt" question is the real open puzzle.

---

### 2026-06-05 — all-blanket `&&`/`;` chain SOFT-PROMPTS (not hard-fails) on `find … docs/historical/wi-*` — matcher reason "find contains unquoted glob characters" — RESOLVED (probed): `find` PATH-OPERAND glob inspector

**RESOLVED (2026-06-05, same day) — HITL probed, 7-cell factorial (glob position × quoting × redirect), verb held = `find` except cell 6. Both anomalies are now settled.**

**Anomaly #1 (chain soft-prompted instead of hard-failing) = working as designed.** Confirmed by inspection in the original draft and unchanged by the probe: the chain is all-blanket-verb (`echo`/`find`/`head` all ∈ `_blanket_verbs.py`), so `block_bash_chains.py` traces to `sys.exit(0)` and passes it through to the matcher. Positive real-world confirmation of the Plan-01 redesign (all-blanket chains reach the matcher instead of being hard-failed). No hook change needed.

**Anomaly #2 (the "glob characters" reason) = a distinct NEW heuristic, matcher-side**, now fully characterized. It is a **`find` PATH-OPERAND glob inspector** — a verb-scoped, quote-INSENSITIVE, position-sensitive check on the *value* of `find`'s search-root operand. No `find`/glob hook exists in `claude-hooks/`, so this is matcher-side. The redirect-tokenization hypothesis floated in the draft below is REFUTED by the probe (cells 1 vs 2, 3 vs 4: `2>/dev/null` is irrelevant). The verb-agnostic lexical-scan alternative is also REFUTED (cell 6: the same bare glob handed to `ls` is silent → `find`-scoped).

**The probe (7 cells, zsh on the laptop, 2026-06-05; Dan was the instrument — reported which commands triggered a permission prompt; the session agent cannot observe the matcher decision directly):**

| Cell | Command | Glob position | Quoted | Redirect | PROMPTED? |
|------|---------|---------------|--------|----------|-----------|
| 1 | `find docs/historical/wi-* -maxdepth 2 -type f 2>/dev/null` | path operand | no | yes | **YES** |
| 2 | `find docs/historical/wi-* -maxdepth 2 -type f` | path operand | no | no | **YES** |
| 3 | `find docs/historical -maxdepth 2 -type f 2>/dev/null` | none | — | yes | no |
| 4 | `find docs/historical -maxdepth 2 -type f` | none | — | no | no |
| 5 | `find 'docs/historical/wi-*' -type f` | path operand | YES (single-quoted) | no | **YES** |
| 6 | `ls docs/historical/wi-*` | ls arg | no | no | no |
| 7 | `find docs/historical -name 'wi-*' -type f` | -name predicate | yes | no | no |

**Reason-text nuance (the matcher inspects the argument VALUE, not the raw command lexeme):** cells 1/2 (unquoted operand) reported *"find contains unquoted glob characters — could glob-expand to a dangerous action before find runs"*; cell 5 (quoted operand) reported *"find argument 'docs/historical/wi-*' contains glob characters — could glob-expand to a dangerous action"* — note it dropped "unquoted" and "before find runs", and **named the argument value** `'docs/historical/wi-*'`. So the matcher parses `find`'s args and inspects the operand's value; the quote marks change only the wording, not the trigger.

**Resolved model — a `find` PATH-OPERAND glob inspector:**
- **Fires** only when a **path operand** (search-root) argument of `find` contains a glob metacharacter (`*` / `?` / `[`). (cells 1, 2, 5)
- **Quote-insensitive** — single-quoting the operand does NOT suppress it (cell 5 still prompts). It is not modeling shell expansion; it inspects the argument value lexically.
- **`find`-scoped, NOT verb-agnostic** — the identical bare glob handed to `ls` is silent (cell 6). Refutes the "verb-agnostic lexical scan" alternative.
- **Position-sensitive** — a glob in the `-name` PREDICATE is exempt (cell 7, silent). Only the path/search-root operand triggers.
- **Redirect-independent** — `2>/dev/null` is irrelevant (cells 1 vs 2; 3 vs 4). REFUTES the "glob + redirect combination" hypothesis floated in the draft.

**Over-fire note (worth recording).** The heuristic over-fires relative to its own stated rationale ("could glob-expand to a dangerous action before find runs", which describes shell expansion of the operand). Cell 5 is single-quoted (the shell will never expand it) and still fires; and the session shell is **zsh**, where an unquoted non-matching glob *aborts* the command (`(eval):1: no matches found`) rather than expanding it. So it is a conservative lexical check on the operand value, not a faithful model of shell behavior. Consequence: it will keep prompting on perfectly safe read-only `find` calls whose path operand contains a glob.

**Confirmed dodge:** `find <literal-dir> -name '<glob>'` — move the glob out of the path operand and into the `-name` predicate (cell 7, silent). This is the idiomatic `find` form anyway. **Quoting the operand is NOT a valid dodge** (cell 5 refutes the natural first guess) — single-quoting `'docs/historical/wi-*'` still prompts because the check is on the value, not on shell-expandability.

**Family classification — a Family 2 sibling: verb-scoped argument-value inspector (`find` path-operand glob).** Closest to **Family 2** (path-aware / argument-semantic, verb-scoped — like the `find`-ancestor and `cd && git` rows) rather than Family 1 (verb-agnostic lexical byte-scan; refuted by cell 6) or Family 3 (AST static-analysis bail; this needs no heredoc/pipe and is purely about one argument's value). It is a **distinct new heuristic within that family**: the construct is a glob-in-`find`-path-operand, the trigger is the operand's literal value, and it is quote-insensitive. Whoever next touches FINDINGS.md should add it as a new Family-2 row (or a clearly-labeled Family-2 sibling) — ready to promote, no further probe needed.

**Impact (updated):**
- **Hook (`block_bash_chains.py`):** none, and none wanted. Behaved exactly per Plan 01 (all-blanket chain → pass through). Incidentally a positive real-world confirmation that the redesign works.
- **Matcher-side:** new heuristic, fully characterized (above). Ready to promote to FINDINGS.md as a Family-2 sibling.
- **Allow rules:** no allow-rule fix — a content heuristic on `find`'s operand value is pre-allow-list, not `Bash(find *)`-overridable.
- **STRATEGIES.md / user-workflow:** add a line — "`find` prompts when its **path/search-root operand** contains a glob (`*`/`?`/`[`); quoting does NOT help. Use `find <literal-dir> -name '<glob>'` instead (glob in the `-name` predicate is exempt)."

**Classification:** RESOLVED. (1) Hook control-flow: working as designed (Plan-01 all-blanket pass-through). (2) Matcher-side: a NEW, fully-characterized **`find` path-operand glob inspector** — verb-scoped, quote-insensitive, position-sensitive, redirect-independent; a Family-2 sibling. Confirmed dodge is `-name`; quoting is not a dodge. NOT a hook bug, NOT a missing allow rule. No further probe needed; ready for FINDINGS promotion.

**Strategy decision (2026-06-05): Strategy 0 *for now*, Strategy 2 is the documented remedy.** Dan is deferring the hook to see how often `find`-glob actually recurs — approvals are tolerable while rare; the hook earns its keep only once the prompt is frequent. **When it does recur often, the fix is Strategy 2 (deny hook), NOT Strategy 1** — an allow rule cannot override a matcher *content* heuristic on `find`'s operand value (see the "Allow rules" bullet above). Implementation sketch for when we build it:
- **Hook:** `claude-hooks/block_find_glob_in_path_operand.py`. Deny a `find` invocation that has a glob metacharacter (`*` / `?` / `[`) in a **path operand** — a token after `find` and *before* the first `-`-led primary (or `!` / `(`). Nastygram → *"`find` prompts when its search-root operand contains a glob; quoting does not help. Use `find <dir> -name '<glob>'` instead."*
- **CRITICAL over-fire guard:** must NOT fire when the glob sits inside a `-name` / `-path` / `-iname` predicate **value** — that's exactly the reformulation the nastygram points to (probe cell 7, silent). A hook that denies its own escape hatch is strictly worse than the prompt it replaces. This is the one real care-point in the regex.
- **Wiring:** full Strategy-2 checklist per `STRATEGIES.md` §"Strategy 2" — new hook script + `chmod +x` + `ensure_block_find_glob_in_path_operand_hook()` in `update_claude_permissions.py` + symlink in `install.sh` + characterization test + `test_hooks_executable.py` auto-coverage + **fresh-session end-to-end verify** that the deny actually fires.
- **Live precedent (cross-link):** the concurrent session just shipped `claude-hooks/block_brace_expansion.py` — a Strategy-2 deny hook for a *related but distinct* construct (brace expansion, a Family-3 static-analysis bail; find-glob is a Family-2 path-operand-glob inspector). When find-glob crosses the recurrence threshold, the Strategy-2 build is a well-trodden path: a sibling deny hook now exists to model the wiring on. Caveat — different families; `block_brace_expansion.py` does NOT cover find-glob, so this is a structural template, not a substitute.

---

(Original curator draft below preserved for audit trail. The "candidate new family / unclassified pending probe" framing and the redirect/verb-agnostic alternatives are superseded by the probe above.)

**Command:**
```
echo "=== wi-tier1 docs/active ===" && find .worktrees/wi-tier1-direct-read/docs/active -maxdepth 2 2>/dev/null | head -50; echo "=== historical wi docs ===" && find docs/historical/wi-* -maxdepth 2 -type f 2>/dev/null
```

**Prompt UI text reported by Dan (verbatim):**
> find contains unquoted glob characters — could glob-expand to a dangerous action before find runs

**Context:** Dan-reported real-world prompt on 2026-06-05. Workspace not specified by Dan, but the relative paths point at a `lobby_analysis`-style cwd (`.worktrees/wi-tier1-direct-read/...`, `docs/historical/wi-*`) — the same `wi-tier1` work that produced the 2026-06-04 `ls … python 2>&1` weirdo. Standard `~/.claude/settings.json` permission state assumed. `echo`, `find`, `head` are all in `BLANKET_VERBS` (confirmed against `claude-hooks/_blanket_verbs.py` this session).

**Segments + rules I think should match (per-segment model + chain-hook trace):**
- Seg 1: `echo "=== wi-tier1 docs/active ==="` — `echo` ∈ BLANKET_VERBS. ✓
- Seg 2 (after `&&`, runs to the `;`): `find .worktrees/wi-tier1-direct-read/docs/active -maxdepth 2 2>/dev/null | head -50` — leading verb `find` ∈ BLANKET_VERBS. NOTE: the `| head -50` is **inside this segment** — `block_bash_chains.py`'s `CHAIN_RE = &&|\|\||;` does NOT split on a single `|`, so the hook sees one segment with leading verb `find`. The matcher does per-segment-check on `|` (FINDINGS 2026-06-04), so to the *matcher* `head` is its own segment; `head` ∈ BLANKET too. ✓
- Seg 3 (after `;`): `echo "=== historical wi docs ==="` — `echo` ∈ BLANKET. ✓
- Seg 4 (after `&&`): `find docs/historical/wi-* -maxdepth 2 -type f 2>/dev/null` — leading verb `find` ∈ BLANKET. Contains the **unquoted glob `docs/historical/wi-*`**. This is the named-trigger segment.

**Hook trace (`block_bash_chains.py`, by inspection this session — NOT piped per curator no-probe rule):**
- Not cd/git, not flow-control-led, no heredoc, no `cd /code`/`cd /tmp`/env prefix → falls through to the chain-split branch.
- `strip_inert` blanks the four double-quoted `echo` strings; the `&&` (×2) and `;` survive → `CHAIN_RE.search` matches (it IS a chain).
- Splits on `&&|\|\||;` → segments with leading verbs `echo`, `find`, `echo`, `find`. **Every one is in `BLANKET_VERBS`** (verified against `_blanket_verbs.py` lines 26, 30, 34). The loop finds no non-blanket segment → `sys.exit(0)`. **The hook PASSES IT THROUGH — it does NOT emit_block().**

**Hypothesis:**

**Anomaly #1 (why a soft prompt, not a hard-fail) is RESOLVED by inspection and is working-as-designed, not a bug.** The repo's *old* mental model ("any `&&`/`;` chain hard-fails") is stale — it predates Plan 01. Post-Plan-01 (FINDINGS 2026-06-04), `block_bash_chains.py` deliberately **passes through all-blanket chains** to mirror the matcher's per-segment silent-allow, hard-failing only chains with at least one *non*-blanket segment. This chain is all-blanket (`echo`/`find`/`head`), so the hook correctly let it reach the matcher. The matcher then per-segment-allowed `echo`/`find`/`head` on the *verb* axis but **independently prompted on a `find`-specific content heuristic** (the unquoted glob). So: hook pass-through (by design) → matcher soft-prompt (new heuristic). No hook fired; nothing was hard-failed; the report is describing the *matcher's* prompt, which is exactly what reaches the user once the hook waves an all-blanket chain through. **The "chains should hard-fail" surprise is an artifact of the pre-Plan-01 model; under the current model this is the expected control flow.**

**Anomaly #2 (the named heuristic) is a CANDIDATE NEW FAMILY — not previously logged.** I searched INCOMING / FINDINGS / STRATEGIES / all hooks for "unquoted glob" / "glob character" / "glob-expand" — **zero prior hits.** This is the first observation of a `find`-with-unquoted-glob heuristic. The trigger is almost certainly the **`docs/historical/wi-*`** argument in seg 4 — an unquoted `*` glob passed to `find` (as opposed to a quoted `-name 'wi-*'` pattern). The matcher's stated threat model ("could glob-expand to a dangerous action before find runs") is coherent: an unquoted `wi-*` is expanded *by the shell* before `find` ever runs, so the actual argv `find` receives depends on cwd contents — the matcher can't statically know what paths `find` will be handed, nor whether a later `find` primary (`-exec`, `-delete`) might act on them. That is a genuine static-analysis gap, architecturally sibling to **Family 3** (static-analysis bail-outs, 2026-06-05): "I can't statically bound this construct's effect, so I require approval." But it's a *different construct* (an unquoted-glob argument, not a heredoc+pipe/redirect), and on a *specific verb* (`find`) — so I'd open it as either a new Family-3 row or, if probing shows it's `find`-specific and path-semantic, a Family-2 (path-aware) row. **Classification pending a probe.**

Note the asymmetry within this very command: seg 2's `find .worktrees/wi-tier1-direct-read/docs/active …` has **no glob** (literal path) and presumably didn't trigger the heuristic; seg 4's `find docs/historical/wi-*` has the unquoted `*` and is the named culprit. That internal A/B (same verb, glob vs no-glob) is suggestive but not conclusive — the prompt is per-command, so I can't be certain seg 2 wouldn't also have contributed.

**Open question for a probe (NOT run — curator role):** is the trigger (a) *any* unquoted shell glob (`*`, `?`, `[...]`) in a `find` path argument, (b) specifically a glob in the path *operand* vs inside a quoted `-name`/`-path` pattern, or (c) broader than `find` (does `ls docs/historical/wi-*`, `cat foo-*` also prompt)? Cheap discriminators, all single-segment, no chain (hook uninvolved):
- `find docs/historical/wi-* -maxdepth 2 -type f` (today's seg 4, isolated) — does it prompt alone? Confirms seg 4 is the culprit.
- `find 'docs/historical/wi-*' -maxdepth 2 -type f` (glob quoted) — if silent, quoting is the dodge.
- `find docs/historical/wi-tier1-direct-read -maxdepth 2 -type f` (no glob, literal) — should be silent; confirms the `*` is the trigger.
- `ls docs/historical/wi-*` — tests whether the heuristic is `find`-specific or fires on any verb with an unquoted glob. **Highest-value cell** for family classification (Family 2 path-aware would likely be verb-scoped; a Family-1-style lexical glob scan would be verb-agnostic).

**Impact:**
- **Hook (`block_bash_chains.py`):** none, and no change wanted. It behaved exactly as Plan 01 specifies (all-blanket chain → pass through). This entry is incidentally a **positive real-world confirmation that the Plan 01 redesign works** — an all-blanket `&&`/`;` chain reached the matcher instead of being hard-failed, which is the over-blocking fix the redesign was for. Worth noting in the next FINDINGS touch.
- **Matcher-side:** candidate **new heuristic** — `find` (at least) prompts on an **unquoted glob in a path argument**, reason "could glob-expand to a dangerous action before find runs." Not in any existing family table. Likely Family 3 (static-analysis bail) or Family 2 (path-aware) depending on the `ls …`-probe outcome. **First observation; held in Pending, not promoted.**
- **Allow rules:** no allow-rule fix — a content/structure heuristic on `find` arguments is pre-allow-list, not `Bash(find *)`-overridable (same class as every other matcher built-in).
- **User-workflow / STRATEGIES:** if confirmed, the dodge is **quote the glob** (`find 'docs/historical/wi-*' …`) or **pass a literal directory + let `find` do the matching** (`find docs/historical -maxdepth 1 -name 'wi-*' -type f` — `find`'s own `-name` matching instead of a shell glob). Both keep the `*` out of the shell's pre-expansion. Don't add a STRATEGIES line until probed.

**Classification:** TWO findings in one report. (1) **Hook control-flow: working as designed** — the all-blanket chain pass-through is Plan 01 behavior, NOT a hook bug; the "should have hard-failed" expectation is the stale pre-Plan-01 model. (2) **Matcher-side: candidate NEW heuristic** ("find contains unquoted glob characters"), not previously in the corpus, probably a Family 3 sibling but unclassified pending a probe. NOT a missing allow rule. Promotion bar: the four-cell discriminator probe above (isolate seg 4, test quoting, test literal path, test `ls` for verb-scope).

---

### 2026-06-05 — heredoc-fed `uv run python - <<'PY' … PY 2>&1 | grep …` — matcher NAMES "Contains shell syntax (file_redirect) that cannot be statically analyzed"

**RESOLVED (2026-06-05, same day) — HITL probed, 12-cell matrix, PROMOTED to FINDINGS.md.** The trigger is **NOT `2>&1`** (the PRIMARY hypothesis below is FALSIFIED: `echo X 2>&1` runs silent — a bare redirect on an allow-listed verb does not prompt). The actual necessary-and-sufficient condition is **a heredoc (`<<`) co-occurring with a pipeline OR an extra redirect** → the matcher can't statically analyze it → prompt, naming the co-occurring construct (`file_redirect` for `2>&1`, `pipeline` for `|`; both reason-texts captured verbatim). Heredoc alone is silent; redirect/pipe without a heredoc is silent (proven by `echo X 2>&1 | grep` silent, `python3 - < file | grep` silent). Two further corrections to the draft below: (1) **Write-then-run is a COMPLETE workaround, not partial** — it removes the heredoc, and the file-based command may keep its `2>&1 | grep` tail (verified silent); the draft's "you must ALSO drop the redirect" is wrong. (2) The draft's "probably the unifying mechanism behind the whole redirect-weirdo family" is **wrong/overstated** — this heuristic *requires* a heredoc, and the prior redirect-blamed weirdos (`install.sh 2>&1 | tail`, `ls … 2>&1`, `head … > slice`) have no heredoc and have other causes. The probe also incidentally **killed the long-running "redirect-tokenization breaks the glob" hypothesis** corpus-wide. New **Family 3 (static-analysis bail-outs)** opened in FINDINGS.md (2026-06-05 entry). Probes P0–P11; methodology Mode A, `AskUserQuestion` channel, CC 2.1.165 on Dans-MacBook-Pro.

---

(Original curator draft below preserved for audit trail. Its PRIMARY hypothesis and the two flagged corrections above are superseded by the probe.)

**Command:**
```
uv run python - <<'PY' 2>&1 | grep -v VIRTUAL_ENV
import json, re
from pathlib import Path
from collections import Counter

by_rid = {}
for p in Path("data/oh_portal/extracted").rglob("filing.json"):
    by_rid.setdefault(p.parent.parent.name, p)
docs = [json.loads(p.read_text()) for p in by_rid.values()]

hdr = Counter()
has_rt = 0
for d in docs:
    rt = d.get("raw_text") or ""
    if rt:
        has_rt += 1
    m = re.search(r"View Agent (\w+) AER", rt)
    hdr[m.group(1) if m else ("(no raw_text)" if not rt else "(other)")] += 1
print(f"docs={len(docs)}  with raw_text={has_rt}")
print("AER header type:", dict(hdr))

# reporting_period labels present
print("periods:", dict(Counter(
    (d.get('raw_text') or '').split('Reporting Period:')[1].split('\n')[1].strip()
    if 'Reporting Period:' in (d.get('raw_text') or '') else '(n/a)'
    for d in docs)))
PY
```
(description line shown: "Check legislative vs executive AER header distribution")

**Prompt UI text reported by Dan (verbatim):**
> Contains shell syntax (file_redirect) that cannot be statically analyzed

**Context:** Dan-reported real-world prompt on 2026-06-05 (machine `Dans-MacBook-Pro`). Issued by a Claude session doing `oh_portal` lobbying-data analysis (cwd appears to be a `lobby_analysis` repo or worktree — relative path `data/oh_portal/extracted`). Standard `~/.claude/settings.json` permission state. `Bash(uv *)` is on the allow list and the `*` should cover the `run python - <<'PY' …` tail. This is the **first observation of the `file_redirect` diagnostic** — a NEW named matcher reason not previously in the corpus.

**Why this is high-value:** the matcher *named the AST node it choked on* — `file_redirect`. That terminology is essentially diagnostic of the parser: `file_redirect` is the **tree-sitter-bash** node type for `> file`, `< file`, `2> file`, and `2>&1` (heredocs are a *separate* node, `heredoc_redirect`; pipes are `pipeline`). So the matcher is parsing commands with a real shell grammar and **refusing to statically approve any command that contains a `file_redirect` node it can't prove the effect of** — because a redirect can silently repoint a "safe" verb's output at an arbitrary file (`echo … > ~/.ssh/authorized_keys`). The reason text is honest and architecturally coherent: "I can't statically bound where this redirect sends bytes, so I won't auto-approve."

**Which token is the named `file_redirect`?** Three coincident shell-syntax features in this one command — ranked by fit to the `file_redirect` label:
1. **(PRIMARY) `2>&1`** — this is a `file_redirect` node in tree-sitter-bash. Cleanest match for the named reason. The heredoc and pipe are *different* node types, so if the matcher named `file_redirect` specifically, `2>&1` is the most likely referent.
2. **(confound, probably NOT the named node) the heredoc `<<'PY'`** — parses as `heredoc_redirect`, not `file_redirect`. The matcher would presumably name it `heredoc_redirect` if that were the trigger. It may independently be unanalyzable, but the *named* reason points away from it.
3. **(confound, NOT a redirect at all) the `| grep -v VIRTUAL_ENV` pipe** — a `pipeline` node, not a redirect. Not the named trigger.

So PRIMARY read: **`2>&1` is the `file_redirect`**, and the heredoc + pipe are coincident noise.

**The tension that blocks immediate FINDINGS promotion:** this *directly contradicts* the 2026-06-01 `find` probe map, where `find /tmp -name x 2>/dev/null` was **silent**. If "any `file_redirect` → prompt" were a stable policy, that probe should have prompted too. Three candidate reconciliations, ranked:
- (i) **The matcher changed between 2026-06-01 and 2026-06-05.** Most likely — "Anthropic ships matcher updates frequently" is the work-line's founding premise, and a brand-new self-naming diagnostic ("file_redirect") is exactly the footprint of a new code path. The 2026-06-01 silent-`2>/dev/null` result may simply predate this policy.
- (ii) **`2>&1` (fd-duplication) is treated as opaque, while `2>/dev/null` (concrete known-safe sink) is exempted.** Counterintuitive — a literal `/dev/null` target is *more* statically analyzable than an fd-dup, so if anything you'd expect the reverse exemption. Possible but it requires the matcher to whitelist `/dev/null` specifically.
- (iii) **The `find` 2>/dev/null was on a single command; today's is inside a *pipeline*.** Maybe the matcher only inspects redirects when they sit inside a multi-stage pipeline / compound. Lower probability — the reason text says "file_redirect," not "pipeline."

(i) > (ii) > (iii). Resolving this is a one-probe job (see below).

**Hook trace (by inspection — not piped this session; curator no-probe rule):**
- `block_bash_chains.py` → **exits 0.** `CHAIN_RE = r'&&|\|\||;'` matches `&&`, `||`, `;` — a **single** `|` is not matched (`\|\|` requires two). One pipe, no `&&`/`||`/`;`, so the hook short-circuits. The prompt is matcher-side, not this hook.
- `block_brace_quote_heredoc.py` → **exits 0 (by inspection).** The heredoc body has no brace-immediately-followed-by-quote (`{"`) or bracket-quote (`['"`) literal. The dict literals here are `{}` (empty), `dict(hdr)`, f-strings `f"docs={len(docs)}"` (brace then `l`, not quote) — none match the `{`/`[`-then-quote anti-obfuscation pattern. So this heredoc slips past the brace-quote hook, yet still prompts at the matcher for a *different* reason (the `2>&1`). **Lesson: a heredoc can be brace-quote-clean and still get matcher-prompted via its redirect tail.**
- `block_cd_git.py`, `use_uv_run_python.py` → not applicable (no `cd`/`git`; `uv run python` is the *approved* form, not a bare `python`).

**Workaround (and the subtlety):** Write-then-run is the standing dotfiles default for heredocs — BUT here it's only a *partial* fix. `Write('/tmp/aer.py', body)` then `uv run python /tmp/aer.py` drops the heredoc, but if you keep the ` 2>&1 | grep -v VIRTUAL_ENV` tail, the `2>&1` `file_redirect` **still prompts** (it's the named trigger, not the heredoc). Full dodge: Write the script AND drop the redirect — run `uv run python /tmp/aer.py` plain and tolerate the one `VIRTUAL_ENV` warning line, or filter it inside Python, or suppress uv's warning via env. The `grep -v VIRTUAL_ENV` was only cosmetic (stripping uv's "VIRTUAL_ENV mismatch" stderr note); it isn't worth a prompt.

**Discriminator probes (NOT run — for the next deliberate probe session):**
- `echo hi 2>&1` — allow-listed verb, `2>&1` only, no heredoc, no pipe. If it prompts with the **same** "file_redirect" reason → `2>&1` confirmed as the sole trigger; heredoc + pipe are noise. **This is the single highest-value probe.**
- `echo hi 2>/dev/null` — tests reconciliation (ii): does a concrete `/dev/null` target get exempted while `2>&1` does not? Re-runs the 2026-06-01 shape under the (possibly new) 2026-06-05 policy.
- `echo hi > /tmp/x` — stdout-to-file `file_redirect`; does a plain `>` prompt the same way?
- `cat <<'PY'` / `hi` / `PY` (heredoc only, no `2>&1`, no pipe) — is a bare `heredoc_redirect` independently a trigger, or only `file_redirect`?
- `uv run python /tmp/aer.py` (Write-then-run, no redirect, no pipe) — should be **silent**; confirms the workaround.
If `echo hi 2>&1` prompts and `uv run python /tmp/aer.py` is silent, the model is settled: **any `file_redirect` node → matcher prompt, regardless of verb/path; redirect-free invocation is clean.**

**Impact:**
- **Hook:** none recommended yet. If `2>&1`/`>`-redirect prompts become frequent enough to be a workflow tax, a Strategy-2 hook could hard-fail redirect-bearing commands with a "split the redirect off / Write-then-run + drop the redirect" nastygram — but only after the probe confirms `file_redirect`-alone is the trigger and characterizes the `/dev/null` exemption (if any). Premature on one observation.
- **Matcher-side:** **first verbatim confirmation** of the long-suspected "redirect breaks an otherwise-clean match" family (open since the 2026-06-01 `find`, 2026-06-02 `install.sh 2>&1 | tail`, 2026-06-04 `ls … 2>&1`, 2026-06-04 `head … > slice` entries). The earlier entries *guessed* at "naive `>`-tokenization breaking the glob"; this entry replaces that guess with the matcher's own framing — it's not a tokenization bug, it's a deliberate "redirects are unanalyzable → require approval" policy. That reframes ~4 prior Pending entries: they may all be instances of this one mechanism. **Cross-link them on promotion.**
- **Allow rules:** no allow-rule fix possible — a "refuse to statically analyze redirects" policy is pre-allow-list and not `Bash(...)`-overridable (same class as the brace-quote / `\n#` / `cd && git` built-ins).
- **STRATEGIES.md:** add a line — "A redirect (`2>&1`, `> file`, `2>/dev/null`?) prompts even on an allow-listed verb; Write-then-run dodges the heredoc but you must ALSO drop the redirect tail." This is the subtle gap: Write-then-run alone is not sufficient when a redirect rides along.

**Classification:** matcher-side, self-named diagnostic (`file_redirect`), highest evidence tier (matcher named the AST node). NOT a hook bug (all hooks correctly short-circuit — single pipe, brace-quote-clean heredoc). NOT a fixable allow-rule gap. **Probably the unifying mechanism behind the whole redirect-weirdo family**, but held in Pending (not promoted) pending the one-probe resolution of the 2026-06-01 silent-`2>/dev/null` tension. Promotion bar: run `echo hi 2>&1` + `echo hi 2>/dev/null` and record which prompt.

---

### 2026-06-04 — bare `ls <abs-path-under-~/code> 2>&1` prompts despite single segment + `Bash(ls *)` + trusted-root path

**RESOLUTION (2026-06-04, same day) — probed empirically across 25 variants. Both leading hypotheses (a) `2>&1` redirect token and (c) hidden-directory-component) FALSIFIED. The actual discriminator is that the target path resolves to a real on-disk Python interpreter — verb-agnostic (`head -n 1` of the same path also prompts), independent of project boundary, independent of `~/code` scope, independent of the redirect operator. Basename + `+x` alone are NOT enough; the matcher inspects file content/realness pre-execution and overrides `Bash(ls *)`. Bug report filed: `probes/BUG_2026-06-04_python-interpreter-prompt.md`, submitted as [anthropics/claude-code#65433](https://github.com/anthropics/claude-code/issues/65433).**

---

(Original entry text below preserved for audit trail.)

**Command:**
```
ls /Users/dan/code/lobby_analysis/.worktrees/wi-tier1-direct-read/.venv/bin/python 2>&1
```
(description line shown: "Check worktree venv exists")

**Context:** Dan-reported real-world prompt on 2026-06-04. Standard `~/.claude/settings.json` permission state (no pclaude/mclaude alias noted in the report). `Bash(ls *)` confirmed on the allow list at `~/.claude/settings.json` line 11. The target path is inside `/Users/dan/code/` — one of the broadly-permitted areas per `additionalDirectories` (line 205) and explicitly a trusted root in the path-aware FINDINGS entry (2026-06-01). Source workspace not given; the path itself points at `lobby_analysis`. None of our PreToolUse hooks should apply: no chain ops (`&&`/`||`/`;`/`|`), no `cd ... && git`, no heredoc body, no brace-with-quote pattern, no `\n#`, no backslash-escaped whitespace, no tilde, no relative path.

**Segments + rules I think should match:**
- One segment, leading verb `ls`. `Bash(ls *)` glob should cleanly swallow ` /Users/dan/code/lobby_analysis/.worktrees/wi-tier1-direct-read/.venv/bin/python 2>&1`.
- The path is a descendant of `~/code` (a trusted root for the `find` path-aware heuristic; presumably also for any analogous `ls` heuristic if one exists).
- Only non-standard token: `2>&1` (merge stderr into stdout). No `2>/dev/null`, no `>file`, no pipe.

Per current FINDINGS, this should NOT have prompted. That's the interesting part.

**Hypothesis (ranked):**

- (a) **PRIMARY: `2>&1` redirect token is being treated as outside the `Bash(ls *)` glob match.** This is the same shape as the SUPERSEDED `find ... 2>/dev/null` hypothesis from 2026-06-01 — but in that case the A/B probe map falsified the redirect-as-trigger story and surfaced a path-aware heuristic instead. The path-aware story does NOT cover today's command: `/Users/dan/code/lobby_analysis/...` is *descendant* of `~/code` (inside the trusted root), not strict-ancestor-of-cwd, so the `find`-family heuristic should not fire. That leaves the redirect token as the leading remaining suspect for this `ls` command. Possible mechanisms: (i) matcher tokenizes `2>&1` as separate from `ls`'s arg list, leaving an unmatched tail; (ii) `Bash(ls *)` glob's `*` doesn't span the `>` character (lexical split on `>` similar to the known `;`-split-in-`-c`-bodies bug); (iii) anti-obfuscation pre-pass treats `&` (inside `2>&1`) as a backgrounding token. Mechanism (ii) is most parsimonious — structurally identical to the known semicolon-split bug.
- (b) **SECONDARY: `Bash(ls *)` glob requires a literal trailing space-then-character, and `2>&1` doesn't qualify.** Less plausible — `*` should be greedy through any chars including `>` and digits. Listed only because (a) and (b) are not mutually exclusive.
- (c) **TERTIARY: a path-aware heuristic on `ls` *into* a hidden directory (`.worktrees/`, `.venv/`) inside `~/code`.** The `.claude/`-write hypothesis from the 2026-05-30 `cp` weirdo posited matcher special-casing on paths containing `.<dotdir>/` substrings. If that generalizes beyond `.claude/`, both `.worktrees/` and `.venv/` would trip it. Lower probability because no FINDINGS entry has confirmed this generalization yet, but worth keeping on the list because the path here has *two* dotdir components.
- (d) **Could-not-rule-out: source workspace's settings.json overlay differs.** Dan didn't specify the workspace; if `ls` was issued from a project that loads `.claude/settings.local.json` overrides, the effective allow rule for `ls` could differ from the global. Lowest probability — `Bash(ls *)` is global and unlikely to be removed locally.

(a) > (c) > (b) > (d) in likelihood. (a) is the parsimony pick; (c) is the more-interesting-if-true outcome.

**Notes for triage:**
- This is the **first observation of a single-segment, no-chain, no-quoted-body, allow-listed verb with a trusted-root path** prompting on a trailing `2>&1`. The 2026-06-01 `find ... 2>/dev/null` weirdo had a different cause (path-aware) and `2>/dev/null`; the 2026-06-02 `~/code/dotfiles/install.sh 2>&1 | tail -80` weirdo had a tilde-leading verb confound. Today's command isolates `2>&1` as the only non-trivial feature on a path that is *not* an ancestor-of-cwd.
- The 2026-06-01 path-aware probe table did not include any case combining a trusted-root path WITH a `2>&1` redirect on a non-`find` verb. So this is genuinely new territory.
- Cheap discriminator probe (not run — curator role): vary just the redirect token while holding the path constant.
  - `ls /Users/dan/code/lobby_analysis/.worktrees/wi-tier1-direct-read/.venv/bin/python` (no redirect)
  - `ls /Users/dan/code/lobby_analysis/.worktrees/wi-tier1-direct-read/.venv/bin/python 2>&1` (today's command)
  - `ls /Users/dan/code/lobby_analysis/.worktrees/wi-tier1-direct-read/.venv/bin/python 2>/dev/null` (other stderr-redirect form)
  - `ls /Users/dan/code/lobby_analysis/.venv/bin/python 2>&1` (only one dotdir, not two)
  - `ls /tmp/x 2>&1` after `touch /tmp/x` (no `~/code`, no dotdirs, isolates redirect)
  If only `2>&1` cases prompt → (a) confirmed. If only the two-dotdir case prompts → (c) confirmed. If all redirect forms prompt regardless of path → (a)(ii) (lexical `>`-split) is the right read.

**Impact:**
- **Hook (`block_bash_chains.py`):** none. Single segment, no chain operators, hook short-circuits at `CHAIN_RE.search(stripped)` returning None.
- **Hook (`block_brace_quote_heredoc.py`):** none. No heredoc, no brace+quote.
- **Hook (`block_cd_git.py`):** none. No `cd`, no `git`.
- **Matcher-side:** if (a) confirmed, this is a **new finding** distinct from both the 2026-06-01 path-aware-`find` heuristic and the 2026-06-03 cd-with-redirection-in-compound heuristic. It would say "trailing `2>&1` (and possibly other stderr/stdout redirects) on a single-segment allow-listed verb can break the glob match" — a much broader class of false positive than either prior entry. Worth probing soon (cheap, well-shaped, one A/B variation).
- **User-workflow:** trivial workaround — drop the `2>&1` for an `ls` check (the merge is rarely needed for `ls`, since `ls` writes most useful output to stdout anyway; the use case here was presumably suppressing the "No such file or directory" stderr line, which can be done with `2>/dev/null` if needed — though that may have its own issues). Alternative: shell-quote the path *and* the redirect inside a `bash -c` (probably trips other heuristics; not recommended).
- **Allow rules:** no allow-rule fix possible if (a)(ii) holds — a lexical `>`-split heuristic is matcher-internal, not allow-overridable. If (b) holds (glob anchoring), a narrower rule wouldn't help either.
- **Probe priority:** medium-high. Five-variant discriminator is cheap and would either confirm (a) (likely a NEW lexical anti-obfuscation entry in FINDINGS Family 1, mechanism: `>` tokenization) or surface (c) (new path-aware heuristic on hidden-directory components). Either outcome materially expands the FINDINGS map.

**Classification:** matcher-side weirdo, single-segment-with-trailing-redirect on a trusted-root path. NOT a hook bug (verified by inspection: all three hooks correctly short-circuit). NOT a missing allow rule (`Bash(ls *)` is present, and if mechanism is lexical-`>`-split no allow rule could override). Probably a new matcher heuristic — the leading candidate is a `2>&1` (or more generally trailing redirect) tokenization that takes the redirect out of the `*` glob's swallowed tail. The redirect-as-trigger hypothesis was killed for `find` on 2026-06-01, but the falsification rested on a path-aware finding that doesn't apply here, so the hypothesis is back on the table for this verb/path combination. Worth a deliberate probe pass.

---

### 2026-06-04 — newline-separated `cd <worktree> ⏎ head … > slice ⏎ cut …` prompts; no `&&`/`;`, all verbs allow-listed

**Command (three statements on separate lines — newlines, NOT chain operators):**
```
cd /Users/dan/code/lobby_analysis/.worktrees/oh-portal-aprime-batch
head -3 data/oh_portal/discover/validation_5272.tsv > data/oh_portal/discover/_slice2.tsv
cut -f1,4,8 data/oh_portal/discover/_slice2.tsv
```
(description line shown: "Build 2-row slice and show it" — that's the human label for the Bash call, not part of the command)

**Context:** Dan-reported real-world prompt on 2026-06-04. Issued by a Claude session in the **`lobby_analysis`** repo — specifically inside the git worktree `/Users/dan/code/lobby_analysis/.worktrees/oh-portal-aprime-batch`. **NOT in dotfiles.** Standard `~/.claude/settings.json` permission state (no pclaude/mclaude alias noted). Note that `lobby_analysis` is under `~/code`, so it IS covered by the same `~/code`-scoped rules — the allow list is global, not dotfiles-only; the cwd being a different repo does not change which rules apply. The cd target is under `/Users/dan/code/...`, covered by both `Bash(cd /Users/dan/code *)` (space) and `Bash(cd /Users/dan/code/*)` (slash) — the slash variant matches the `/lobby_analysis/...` continuation cleanly. `Bash(head *)` and `Bash(cut *)` both confirmed present in settings.json this session.

**Hook trace (done this session — all local hooks ruled out):** I built the exact payload as JSON (real newline characters between the three statements) and piped it to every registered PreToolUse Bash hook individually:
- `block_bash_chains.py` → **exit 0, no output.** Traced branch-by-branch: `CD_CODE_RE` matches the `cd /Users/dan/code/lobby_analysis/.worktrees/oh-portal-aprime-batch\n` prefix (the trailing `\n` satisfies the regex's `\s`), the post-prefix tail is re-scanned by `CHAIN_RE` (`&&|\|\||;`) and is chain-free (newlines are NOT in `CHAIN_RE`), so it `sys.exit(0)` at line 169. The post-2026-06-03 "strip prefix and re-scan the tail" logic does the right thing here.
- `block_cd_git.py`, `block_brace_quote_heredoc.py`, `block_newline_hash_in_quoted_arg.py`, `use_uv_run_python.py` → all **exit 0, no output** on the payload.

So **no local hook produced this prompt.** (Caveat I tripped myself on while tracing: several of these hooks fired on MY OWN diagnostic Bash commands — the `; echo $?` and `&&` I appended, and a `\n#` comment inside an early probe script. Those are the hooks working correctly on my commands, not on Dan's payload. Worth flagging because it nearly produced a false "the chain hook is blocking it" reading. The clean redirect-only `python3 hook.py < payload.json` invocation is the trustworthy test; anything with a `;`/`&&`/`#`/`{"` in the *wrapper* command contaminates the result.)

**Segments + rules I think should match (per-segment model):**
- Stmt 1: `cd /Users/dan/code/lobby_analysis/.worktrees/oh-portal-aprime-batch` — `Bash(cd /Users/dan/code/*)`. ✓
- Stmt 2: `head -3 data/oh_portal/discover/validation_5272.tsv > data/oh_portal/discover/_slice2.tsv` — `Bash(head *)`. The `*` should swallow the args; the `>` redirect to a *relative* path is the one non-trivial feature.
- Stmt 3: `cut -f1,4,8 data/oh_portal/discover/_slice2.tsv` — `Bash(cut *)`. ✓

On a naive per-segment / per-statement model where each leading verb has a covering rule, this should NOT have prompted.

**Hypothesis:**

Most likely a **matcher-side** prompt, with two live candidates, ranked:

1. **(favored) The `>` redirect on statement 2 breaks the `head *` match — the long-suspected "trailing-redirect tokenization" mechanism, here with `>` (stdout) rather than `2>/dev/null` (stderr).** This is the open, twice-logged suspicion from the 2026-06-01 entries (`find … 2>/dev/null`, `ls … 2>&1 | head`). The mechanism (iii) proposed there — the matcher naive-splits on `>` regardless of shell semantics, leaving a right-hand fragment (`data/oh_portal/discover/_slice2.tsv`) with no allow rule — predicts exactly this prompt. NOTE the partial tension: the 2026-06-01 `find` entry was *superseded* by the path-aware-ancestor finding for the `2>/dev/null` *stderr* case specifically. But `>` to a file (stdout redirect to a write target) was never isolated; the path-ancestor heuristic doesn't obviously apply here (the redirect target is a descendant of cwd, not an ancestor). So the stdout-`>`-redirect-tokenization mechanism is still unrefuted and is the most parsimonious fit. If true, the trigger is statement 2 alone.

2. **(alternative) The matcher treats the three newline-separated statements as a multi-statement command and applies whole-string anti-obfuscation/compound reasoning** — analogous to the 2026-06-03 "Compound command contains cd …" built-in, except here the cd carries no redirect (the `>` is on `head`, statement 2). A "compound command writes to a file via a redirect after a cd" shape could plausibly trip a path-resolution-bypass style built-in: the cwd was changed by statement 1, and statement 2 writes to a *relative* path that only resolves correctly if the cd succeeded. That is structurally the same concern the 2026-06-03 built-in's reason text named ("path resolution bypass"). If this is the mechanism, the cd+relative-write combination across statements is the trigger, not statement 2 in isolation.

I do not have the verbatim prompt reason text for this one (Dan didn't paste it). **That text is the single most valuable missing datum** — the 2026-06-03 and 2026-06-01 built-ins both named themselves in the prompt UI. If Dan can recall/recapture whether the prompt said anything like "compound command", "redirect", or "path resolution bypass", it discriminates (1) from (2) immediately. Without it, I lean (1) on parsimony but flag genuine uncertainty.

**What this is NOT:**
- NOT a hook over-block. All five local hooks exit clean on the payload (traced this session).
- NOT a missing allow rule that's fixable by adding a verb rule — `head` and `cut` are both present, and if the cause is a built-in (candidate 2) or redirect-tokenization (candidate 1), no allow rule overrides it.
- NOT the cd-rule space-vs-slash strictness (2026-05-30 side finding) — the slash-variant rule `Bash(cd /Users/dan/code/*)` was added precisely to cover `/lobby_analysis/...` continuations and matches here.
- The "different repo / outside dotfiles" framing is a **red herring for the rules**: the allow list lives in the global `~/.claude/settings.json` and applies regardless of cwd. `lobby_analysis` being under `~/code` means it's inside the trusted root, same as dotfiles. (It would only matter if the cwd were *outside* `~/code` and a path-ancestor heuristic like the 2026-06-01 `find` one came into play — not the case here.)

**Impact:**
- **Hook (`block_bash_chains.py` and siblings):** none — confirmed clean by direct payload trace. No change recommended.
- **Matcher-side:** if candidate (1) holds, this is the long-deferred confirmation that **stdout `>`-redirect (not just stderr `2>`) breaks an otherwise-clean per-segment match** — which would be a high-impact FINDINGS entry (every `cmd … > out` would prompt). If candidate (2) holds, it's a sibling of the 2026-06-03 cd-compound built-in. Either way it belongs in the next deliberate probe session, NOT promoted on this single observation.
- **Cheap discriminator probes (for the next probe session, NOT run now per the no-probe rule):**
  - `head -3 /tmp/a.tsv > /tmp/b.tsv` as a SINGLE statement, cwd anywhere — if it prompts, candidate (1) (stdout-redirect tokenization) is confirmed and statement 2 alone is the trigger; the newlines/cd are irrelevant.
  - `head -3 /tmp/a.tsv` (no redirect) vs `head -3 /tmp/a.tsv > /tmp/b.tsv` (redirect) — isolates the `>` as the sole variable.
  - If the single-statement redirect is *silent*, the trigger is the multi-statement/cd-relative-write combination → candidate (2); then probe `cd /tmp\nhead -3 a.tsv > b.tsv` vs `cd /tmp\nhead -3 a.tsv` (newline-joined, no redirect) to confirm.
- **User-workflow:** split into separate Bash tool calls (cwd persists): `cd` in call 1, `head … > slice` in call 2, `cut …` in call 3. Or drop the `>` redirect by using `head -3 … | cut …` directly if the intermediate slice file isn't needed — though if the matcher tokenizes `|` and `>` similarly, the pipe may prompt too; the safest dodge is separate calls. The intermediate-file write itself (Write tool, or `head > slice` in its own call) is unaffected.

**Classification:** matcher-side prompt, NOT a hook bug and NOT a fixable user-rule gap. Two live candidate mechanisms (stdout-`>`-redirect tokenization vs cd-compound built-in); discriminable by the verbatim prompt text (not captured) or by the cheap probes above. Medium confidence it's candidate (1) on parsimony with the two prior redirect weirdos; flagged as genuinely unresolved.

---

### 2026-06-03 — `ls <path-with-backslash-escaped-space>` — matcher names "Contains backslash-escaped whitespace" heuristic

**Command:**
```
ls /Users/dan/Library/Application\ Support/Code/User/settings.json 2>/dev/null
```

**Prompt UI text reported by Dan:**
- Headline: "Check VS Code user settings exists"
- Diagnostic: **"Contains backslash-escaped whitespace"**

**Context:** Issued by a Claude session on 2026-06-03 (workspace not specified by Dan; report received via the curator handoff). Standard `~/.claude/settings.json` permission state — `Bash(ls *)` is on the allow list (verified: `~/.claude/settings.json` line 11). No chain operators outside the path. `2>/dev/null` trailing stderr-redirect is present (same shape as the now-triaged `find ... 2>/dev/null` weirdo, where the redirect was shown to be a red herring — the cause there was a path-aware heuristic on `find` ancestor-of-cwd paths).

**Segments + rules I think should match:**
- One segment, leading verb `ls`. `Bash(ls *)` glob should cleanly swallow `-la?`-free arg `/Users/dan/Library/Application\ Support/Code/User/settings.json` plus the trailing `2>/dev/null`.
- The path `/Users/dan/Library/Application Support/...` is a standard macOS user-config path containing a literal space in `Application Support`. The `\ ` is the standard POSIX shell escape so the space stays part of one argument. Shell-semantically this is a single-token path — no obfuscation, no second command, no redirect tampering.

**Hypothesis:** Matcher-side anti-obfuscation heuristic on **backslash-escaped whitespace** (`\<whitespace>`), distinct from the brace+quote and `\n#`-in-quoted-`-c`-body heuristics already cataloged in FINDINGS.md but structurally the same family: a bash-lexical pattern scan against the command string that fires regardless of whether the surrounding command is otherwise allow-listed. The matcher's reasoning is presumably "backslash escapes can be used to hide arguments from path validation / disguise command structure," but the heuristic is over-broad: it fires on any `\ ` in a path, which is the canonical and only POSIX-portable way to embed a space in a path argument.

This is the **third named anti-obfuscation heuristic** Claude Code has surfaced in its prompt UI:
1. "Contains brace with quote character (expansion obfuscation)" — brace+quote in unquoted bash context (heredocs, bare args). FINDINGS-promoted 2026-05-30.
2. "Newline followed by # inside a quoted argument can hide arguments from path validation" — `\n#` in `-c "..."` body. FINDINGS-promoted 2026-06-01.
3. **"Contains backslash-escaped whitespace"** — backslash+whitespace anywhere in the command. NEW, this entry.

All three follow the same architectural pattern: bash-lexical byte-pattern scan over the full command string, fires regardless of allow-rule match, names itself in the prompt UI. Likely all three are anchored in the same matcher code path (anti-obfuscation pre-filter that runs before allow-list matching).

**Falsifiers / probes (not run — curator role):**
- Cheap discriminator: `ls "/Users/dan/Library/Application Support/Code/User/settings.json" 2>/dev/null` (double-quoted path instead of backslash-escape). If silent → confirms the trigger is the `\ ` specifically and double-quoting the path dodges it. If still prompts → the heuristic also catches quoted whitespace and the workaround is harder.
- Sibling: `ls /tmp/foo\ bar` after `touch /tmp/foo\ bar`. Isolates the backslash-escape on a path with no `.claude`-like / no-Library overlay. If prompts → trigger is purely lexical, not path-aware.
- Hook trace: `block_bash_chains.py` has no `\ ` matching logic (current `CHAIN_RE = r'&&|\|\||;'`) and would short-circuit. `block_brace_quote_heredoc.py` doesn't match either. The prompt is matcher-side, not hook-side. Verified by inspection only — not piped to the hook in this session per the curator no-probe rule.

**Impact:**
- **Hook:** none. Neither `block_bash_chains.py` nor `block_brace_quote_heredoc.py` is involved. If this heuristic keeps firing frequently enough to be annoying, a Strategy-2 hook (`block_backslash_whitespace.py`) could hard-fail with a workaround suggestion, but that only makes sense if the workaround is well-defined (probably "use double-quotes around paths with spaces" — pending probe confirmation).
- **Matcher-side:** confirms a third member of the anti-obfuscation family. Family is now: brace+quote, `\n#`-in-quoted-`-c`, backslash-escaped whitespace. Reinforces the model from FINDINGS.md that the matcher runs a bash-lexical anti-obfuscation pre-pass before allow-list matching.
- **User-workflow:** double-quote the path instead of backslash-escaping. `ls "/Users/dan/Library/Application Support/..."` should sidestep the heuristic (pending probe). Macs are the only platform where this comes up routinely (Linux paths almost never have spaces), so the workaround is reasonable.
- **Allow rules:** no allow-rule fix possible — anti-obfuscation heuristics are pre-allow-list and not overridable by `Bash(...)` entries. Same as the brace+quote case.
- **STRATEGIES.md:** worth adding a line under the "Mac path gotchas" section (if it exists; if not, a short note alongside the brace+quote workaround). One-liner: "Quote paths containing spaces; don't backslash-escape."

**Classification:** matcher-side anti-obfuscation heuristic, third confirmed member of a known family. NOT a hook bug, NOT a missing allow rule. Same shape as brace+quote and `\n#`-in-quoted-`-c`-body — bash-lexical pattern scan over the full command string, fires regardless of allow-list match, names itself in the prompt UI. Likely directly promotable to FINDINGS.md without a probe, given the prompt UI named the heuristic verbatim (same evidence bar as the `\n#` entry that was FINDINGS-promoted same-day).

---

### 2026-06-03 — `cd ... 2>/dev/null; ls ...; echo ...; pwd` — HOOK BUG (cd-prefix exception leaked the chain) + new built-in heuristic

**RESOLUTION (2026-06-03, same day) — the flagged hook-coverage question is answered, and it was a real `block_bash_chains.py` bug, now fixed.**

Dan confirmed the prompt fired on **Dans-MacBook-Pro (laptop), `_private-notes` workspace**, with `block_bash_chains.py` provably active — the *immediately preceding* command in the same session (`hostname && date -u`) got the chain hook's hard-fail nastygram. So this is **not** the +x silent-failure (FINDINGS 2026-05-31), not a missing registration, and not `--setting-sources project`. The hook was live and still let the command through.

**Root cause:** the whitelist-prefix exception did a blanket `sys.exit(0)` the moment `CD_CODE_RE`/`CD_TMP_RE`/`ENV_PREFIX_RE` matched the *prefix*, **never examining the tail for chain operators.** `CD_CODE_RE = ^\s*cd\s+/Users/dan/code(?:/\S*)?\s` requires only `cd /Users/dan/code` + whitespace. The ` ` before `2>/dev/null` satisfied that trailing `\s`, the prefix matched, and the entire `; ls | head; echo; pwd` tail was waved through unseen. The discriminator is **a space after the path**: `cd /Users/dan/code 2>/dev/null; …` (space → leaked) vs `cd /Users/dan/code; …` (immediate `;`, no space → correctly blocked). The `2>/dev/null` was incidental to the *hook* bug — any space before the `;` (e.g. `cd /Users/dan/code ; rm`) opened the same hole. This is exactly the "exceptions no longer load-bearing" failure the hook's own header (lines 8–17) warned about, now with a concrete repro.

**Fix (committed this session):** `block_bash_chains.py` no longer blanket-exits on a prefix match. It strips the matched prefix and re-scans only the remainder (`strip_inert(tail)` + `CHAIN_RE`); it passes through only if the tail is itself chain-free. Flow-control and heredoc exceptions were moved *above* the prefix check so env-prefixed heredocs (`FOO=bar python3 <<'PY' … import os; … PY`) don't get their bodies re-scanned and falsely blocked. The NASTYGRAM footer was corrected — it previously advertised `cd /…/code && …` and `cd /tmp && …` as "approved chain prefixes that DO pass," which is no longer true (and was the conceptual source of the bug). New behavioral test file `test_block_bash_chains.py` (19 cases: the 5-case probe table + env/heredoc/flow-control/cd-git non-regression). Full suite 92/92 green.

**Behavior change to be aware of:** `cd /Users/dan/code && <cmd>` and `cd /tmp && <cmd>` (single-`&&` chains that used to pass) are now **blocked** by this hook. That's intended — cwd persists across separate Bash calls, so the workaround is cd-in-one-call / run-in-the-next. The env-var prefix (`FOO=bar python …`) still passes because it's not a chain at all.

**Still open (matcher-side, now masked):** the built-in "cd with output redirection → path resolution bypass" heuristic (analysis below) is still real, but the hook now hard-blocks this command shape *before* the matcher ever renders its prompt — so Dan won't see the built-in prompt for this shape again. The two cheap discriminator probes below remain valid if we want to characterize the built-in for the FINDINGS path-aware family, but priority drops to low since it's masked in practice. **Not yet promoted to FINDINGS** — left for a deliberate probe session.

---

_Original curator entry follows (hypothesis #1 — new built-in heuristic — confirmed; hypothesis #3 — +x silent-failure — ruled out by Dan's machine confirmation above)._

**Command:**
```
cd /Users/dan/code 2>/dev/null; ls -d */ 2>/dev/null | head -50; echo "---PWD---"; pwd
```
(description line shown: "List repos and current directory")

**Reason text shown in the prompt (verbatim):**
> Compound command contains cd with output redirection - manual approval required to prevent path resolution bypass

**Context:** Dan-reported real-world prompt on 2026-06-03. Standard `~/.claude/settings.json` permission state (no pclaude/mclaude alias noted). The cd target `/Users/dan/code` is one of the additional working directories and is covered by `Bash(cd /Users/dan/code *)` / `Bash(cd /Users/dan/code/*)`. All non-cd verbs are individually allow-listed: `Bash(ls *)`, `Bash(head *)`, `Bash(echo *)`, `Bash(pwd *)` (confirmed present in settings.json this session).

**Segments + rules I think should match (per-segment model):**
- Seg 1: `cd /Users/dan/code 2>/dev/null` — `Bash(cd /Users/dan/code *)` (space variant) should swallow the ` 2>/dev/null` tail. ✓ should match on naive glob.
- Seg 2: `ls -d */ 2>/dev/null` — `Bash(ls *)`. ✓ (modulo the redirect-tokenization question, see below).
- Seg 3 (after `|`): `head -50` — `Bash(head *)`. ✓
- Seg 4: `echo "---PWD---"` — `Bash(echo *)`. ✓
- Seg 5: `pwd` (bare) — `Bash(pwd *)`. Bare-arg-less-vs-`cmd *`-glob question (the long-standing secondary suspicion), but not the cited reason here.

Per the per-segment model, every segment has a covering rule. On that model this should NOT have prompted — which is exactly why the cited reason text is the interesting part.

**Hypothesis:**

This reason text does **not** match any of Dan's local PreToolUse hooks:
- It is NOT `block_bash_chains.py`. That hook's nastygram talks about "Bash chain operator (&&, ||, or ;)" and "use SEPARATE Bash tool calls" — I re-confirmed the exact wording this session by tripping it three times on my own `;`/`||` commands. Nothing about "path resolution bypass."
- It is NOT `block_cd_git.py`. That hook keys on the `cd <path> && git <subcmd>` shape and its message is about `git -C`. This command has no `git` segment.
- The phrasing "Compound command contains cd with output redirection" and "prevent path resolution bypass" reads like a **Claude Code BUILT-IN matcher heuristic** — same self-documenting-diagnostic style as the previously-observed built-ins ("Contains brace with quote character (expansion obfuscation)", "Newline followed by # inside a quoted argument..."). This appears to be a **distinct, possibly-new built-in heuristic** not yet in either FINDINGS family table.

**Trigger surface (best read):** the heuristic keys on **`cd` paired with an output/stderr redirection (`2>/dev/null`) inside a compound command**. The command has `cd ... 2>/dev/null` as the first segment of a `;`-separated compound. The threat model implied by "path resolution bypass" is plausibly: a `cd` whose failure/stderr is suppressed (`2>/dev/null`) could silently NOT change directory (e.g. target missing), leaving subsequent segments to run against an unexpected cwd — i.e. the redirect hides the signal that path resolution didn't go as the rule-author assumed. So the matcher refuses to auto-approve any compound where a `cd` segment carries a redirect. This is architecturally a **Family-2 (path-aware) heuristic**, not a Family-1 lexical byte-scan — it's reasoning about cd + redirection semantics, not scanning for a byte pattern like `{"`.

**Layering / ordering ambiguity (flag for triage):** This command ALSO contains `;` and `|` chain operators, so `block_bash_chains.py` *should* have hard-blocked it before the matcher ever rendered an approve/deny prompt — yet Dan saw an approvable prompt with the cd-redirection reason text, not the chain-hook's hard-fail nastygram. Possible explanations, unresolved:
1. The command ran in a workspace/session where `block_bash_chains.py` is NOT registered (e.g. a project using `--setting-sources project`, or a machine where install.sh hasn't propagated the hook), so only the built-in matcher saw it.
2. The built-in matcher's heuristic surfaced the prompt and the chain hook was bypassed/disabled for that context.
3. The +x silent-failure mode (see FINDINGS 2026-05-31) recurred on another machine — chain hook exec-failed silently, matcher fell through to the cd-redirection prompt.
We can't disambiguate without knowing the workspace and machine. **Dan: which workspace/agent and which machine did this fire on, and was `block_bash_chains.py` active there?** If the chain hook WAS active and still didn't fire, that's a separate (and higher-priority) finding than the new built-in heuristic.

**Impact:**
- **Hook (`block_bash_chains.py`):** by its own rules it should have hard-failed this (multiple `;` + `|`). If it didn't, root-cause the ordering ambiguity above before anything else — that's a hook-coverage gap, not a matcher curiosity.
- **Matcher-side:** likely a NEW built-in heuristic — "cd with output redirection in a compound command → manual approval." If confirmed, it's a new row in FINDINGS Family 2 (path-aware), distinct from the `find`-ancestor and `cd && git` rows. No allow rule can override a hardcoded built-in (same as `cd && git`), so the workaround is structural: drop the `2>/dev/null` off the `cd`, or (canonical) replace the whole compound with separate Bash tool calls — `cd` in one call (cwd persists), `ls -d */ | head -50` in the next, `pwd` in a third. None of those carry a redirect on a `cd` inside a compound.
- **Probe priority:** medium-high. Cheap discriminator for the next deliberate probe session: `cd /tmp; pwd` (no redirect on cd) vs `cd /tmp 2>/dev/null; pwd` (redirect on cd) — if only the second prompts, the heuristic is confirmed as keyed on cd+redirect-in-compound. Second probe: `cd /tmp 2>/dev/null` as a SINGLE non-compound command — if that is silent, the "compound" qualifier in the reason text is load-bearing (heuristic only fires when cd+redirect is part of a multi-segment command).

**Classification:** primarily matcher-side (new built-in heuristic, well-typed reason text, NOT one of our hooks). BUT with a flagged hook-coverage question — the chain hook should have pre-empted this and apparently didn't, which needs Dan's workspace/machine context to resolve. NOT a missing allow rule (built-ins aren't allow-overridable).

---

### 2026-06-02 — `~/code/dotfiles/install.sh 2>&1 | tail -80` — tilde-prefixed path, pipe, and stderr-redirect all coincident

**Command:**
```
~/code/dotfiles/install.sh 2>&1 | tail -80
```

**Context:** Issued by a Claude session (curator-adjacent, dotfiles work-line) on 2026-06-02. Standard `~/.claude/settings.json` permission state, no recent rule changes since the 2026-06-01 finds. Dan explicitly flagged the prompt: "note that I'm getting prompted for this???" The expectation was clean pass — single pipe, both verbs allow-listed, no chain ops, no brace-quote, no `\n#`, no `cd && git`.

**Segments + rules I think should match:**
- Seg 1: `~/code/dotfiles/install.sh 2>&1` — leading "verb" is the tilde-prefixed path `~/code/dotfiles/install.sh`. Allow list has `Bash(/Users/dan/code/dotfiles/*.sh *)` AND `Bash(/Users/dan/code/dotfiles/*.sh)` (both lines 115-116 of `~/.claude/settings.json`) — but those are **absolute paths**, not tilde-expanded. **Whether the matcher tilde-expands before glob-matching is unknown.** This is the prime suspect.
- Seg 2: `tail -80` — `Bash(tail *)` is on the allow list (line 33). ✓ should be allowed
- The `2>&1` stderr-merge redirect attaches to seg 1. The `find ... 2>/dev/null` weirdo from 2026-06-01 (now triaged in FINDINGS as path-heuristic) initially looked like a trailing-redirect bug; the A/B probe falsified that and the redirect-as-trigger hypothesis is dead for `find`. Whether it's also dead for other commands is not certain.

**Hypothesis (ranked):**
- (a) **PRIMARY: tilde (`~`) is not expanded before allow-list matching.** The matcher receives the literal string `~/code/dotfiles/install.sh ...`, glob-matches against `Bash(/Users/dan/code/dotfiles/*.sh *)`, the literal `~` doesn't match `/Users/dan`, segment misses. Same architectural shape as the 2026-05-30 `bash /Users/dan/code/dotfiles/install.sh | tail -5` weirdo (triaged): allow rule existed for the script-as-direct-invocation, but the matcher was looking at the leading verb (`bash` there, `~/...` here) which didn't match any rule. **Most parsimonious — single mechanism explains the whole prompt.**
- (b) **SECONDARY: `2>&1` trailing redirect tokenization.** The `find ... 2>/dev/null` entry above (now FINDINGS-promoted as a path-heuristic, NOT a redirect bug) leaves this hypothesis partially deflated for *that* command, but doesn't rule it out across all commands. If the matcher splits on `>` or treats `2>&1` as a separate token outside the `*` glob, seg 1 could miss even with an absolute path. Less parsimonious than (a) here because there's already a known issue with the leading verb.
- (c) **TERTIARY: pipe `|` triggers the same chain-split machinery as `&&`.** Would mean the matcher per-segments-on-pipe, which is consistent with the 2026-05-30 probe-10 (`ls /tmp/probe08 | head -3` ALLOWED when both segments individually allowed). Probe-10 *succeeded* — both `ls *` and `head *` matched — so pipe-as-segment-splitter is consistent with prior observation. That means (c) is **not really a new hypothesis** — it's the known model. The interesting question is *which segment fails*: (a) says seg 1's tilde, (b) says seg 1's redirect.

(a) > (b) > (c) in likelihood. (a) and (b) are independent and could both be true; (c) is consistent with current findings and doesn't add weirdness.

**Cheap discriminator probe (not run — curator role):** Re-issue the same command with absolute path: `/Users/dan/code/dotfiles/install.sh 2>&1 | tail -80`. If silent → (a) confirmed, tilde-not-expanded is the cause. If still prompts → (b) live, the `2>&1` is the cause (or both). If silent only when BOTH the tilde is expanded AND the redirect is dropped → (a) and (b) both required. Three variants total:
- `/Users/dan/code/dotfiles/install.sh 2>&1 | tail -80` (abs path, redirect)
- `~/code/dotfiles/install.sh | tail -80` (tilde, no redirect)
- `/Users/dan/code/dotfiles/install.sh | tail -80` (abs, no redirect)

Adding to probe TODO. The tilde-expansion question is broader than `install.sh` — it affects whether `~/...` paths can ever match absolute-path allow rules.

**Impact:**
- **Hook:** none. `block_bash_chains.py` short-circuits — there's a `|` but no `&&`/`||`/`;` (current hook regex `r'&&|\|\||;'`). Verified by reading the hook: the pipe alone isn't matched by `CHAIN_RE`, so the hook exits 0. **The prompt came from the matcher, not the hook.**
- **Matcher-side:** if (a) holds, tilde-expansion-before-match is missing. Workaround: always use absolute paths in Bash tool calls for script invocations (matches the existing allow rules). Long-term: would warrant a one-line fix in Claude Code (call `os.path.expanduser` on the command before allow-list match), but that's upstream-out-of-scope.
- **User-workflow:** trivial fix — use `/Users/dan/code/dotfiles/install.sh 2>&1 | tail -80` instead of the tilde form. Worth a STRATEGIES.md note alongside the existing "use absolute paths for `cd`" guidance.
- **Allow rules:** if (a) confirmed, could add `Bash(~/code/dotfiles/*.sh *)` and the tilde variant siblings — but only if the matcher matches literal-tilde at all, which is the open question. The clean fix is upstream tilde-expansion; the workaround is "stop using tildes in Bash calls."

**Classification:** matcher-side weirdo. Single-segment-leading-verb-miss is the most likely mechanism, same shape as the triaged 2026-05-30 `bash /path/install.sh` entry. Lateral evidence: probe-10 from 2026-05-30 confirms pipe-as-segment-splitter, so per-segment matching here is the operative model and (a) reduces to "seg 1's leading verb (`~/...`) doesn't match any rule because the matcher reads `~` literally."

---

### 2026-06-01 — `find` against ancestor-of-cwd home-dir path prompts despite `Bash(find *)` allow rule (path heuristic, not anti-obfuscation lexer)

**Command:**
```
find /Users/dan -maxdepth 3 -name ".env.<CLIENT>" 2>/dev/null
```

**Context:** Dan-reported prompt during HITL probe session on 2026-06-01 in dotfiles workspace (cwd `~/code/dotfiles`). Standard `~/.claude/settings.json` permission state. `Bash(find *)` IS on the allow list (`update_claude_permissions.py` line 75). No chain operators in the command. **This entry replaces the earlier `find ... 2>/dev/null` redirect-tokenization hypothesis** logged below — that hypothesis was falsified by the A/B map described below.

**Segments + rules I think should match:**
- One segment, leading verb `find`. `Bash(find *)` glob cleanly swallows the entire command including the `2>/dev/null` tail.
- Allow list should match this on naive glob-against-full-command-string semantics.

**A/B probe map (run in HITL session, hook-allowed cases only — no chain ops, hook not involved):**

| Path argument | Prompted? | Relationship to cwd (`~/code/dotfiles`) |
|---|---|---|
| `/tmp/...` | no | explicitly-allowed scratch dir |
| `/Users/dan/code/...` | no | ancestor-of-cwd inside `~/code` |
| `/Users/dan/Documents` | no | sibling of cwd subtree, inside home, OUTSIDE `~/code` |
| `/Users/dan` | **yes** | strict ancestor of cwd (home root) |
| `/Users` | **yes** | further-up ancestor |

**Hypotheses falsified during the probe:**
- `2>/dev/null` redirection breaking the glob match — falsified by single-segment probes WITH redirection that did NOT prompt (e.g., `find /tmp -name x 2>/dev/null` was silent).
- `.env*` pattern triggering a secrets-protection heuristic — falsified by `find /tmp -name ".env.<CLIENT>"` running clean.

**Surviving hypothesis:** Claude Code's matcher has a **path-aware heuristic on `find`** that prompts when the target path is a **strict ancestor of cwd outside trusted roots** (`/tmp`, `~/code`). Sibling/descendant paths inside `$HOME` but outside the cwd subtree (`~/Documents`) do NOT trip it. This is the same architectural shape as the `cd <path> && git <subcmd>` heuristic — hardcoded in Claude Code, not overridable by allow rules.

Security-coherence note: `find /Users/dan` expands the file-scope enormously (all of `$HOME` including `Library/`, `.ssh/`, etc.), whereas `find /Users/dan/Documents` is bounded to one sibling subtree. The asymmetry makes engineering sense — broaden-the-scope-above-cwd is exactly the access pattern most likely to leak secrets or scan sensitive dirs.

**Impact:**
- **Hook:** none. `block_bash_chains.py` not involved (no chain operators). `block_cd_git.py` not involved (no cd-git pattern). No new hook recommended — the prompt-then-approve flow for `find` on home-dir is probably the right default; Dan can approve when legitimate. A hook would only be needed if Dan wants hard-fail to force a workflow change, which doesn't seem warranted at current prompt frequency.
- **Matcher-side:** new heuristic family discovered. This is **path-aware**, not lexical anti-obfuscation. Distinct architectural shape from the `\n#` / brace-quote / `;`-tokenization family (those scan command strings for byte patterns; this one reasons about path semantics relative to cwd).
- **User-workflow:** if a `find` over `$HOME` is genuinely needed, accept the prompt. Otherwise scope to subtrees under cwd or `/tmp` and the prompt won't fire.

**Classification:** matcher-side path heuristic, well-understood, working as intended (security-coherent). NOT a hook bug, NOT a missing allow rule, NOT a matcher false-positive — the prompt is correct behavior for an unusually broad filesystem scan.

**Promotion notes:** Promoted to FINDINGS.md same-day. Bar: five-point A/B map, two competing hypotheses systematically falsified, surviving hypothesis is internally consistent with a coherent security story. Promoted to a NEW section in FINDINGS.md ("Path-aware matcher heuristics") rather than the existing anti-obfuscation table, because the architectural shape is different.

---

### 2026-06-01 — `python -c` body with `\n#` Python comment trips matcher heuristic NAMED in the prompt

**Command:**
```
uv run python -c "
import json
from pathlib import Path
from collections import defaultdict
RESULTS = Path('/Users/dan/code/lobby_analysis/.worktrees/wi-tier1-direct-read/docs/active/wi-tier1-direct-read/results/tier_1/WI_2025')
# For the 3-3 split rows in lobbyist_spending_report, find: is the split CLAUDE-vs-GPT, or run-vs-run?
target_rows = ['lobbyist_spending_report_includes_total_compensation',
               'lobbyist_spending_report_includes_total_expenditures',
               'lobbyist_spending_report_required',
               'lobbyist_spending_report_includes_general_issues']
by_row = defaultdict(list)
for p in sorted(RESULTS.glob('*lobbyist_spending_report*.json')):
    model = p.stem.split('__')[0]
    run = p.stem.split('__')[2]
    d = json.loads(p.read_text())
    for inst in d['instantiated_cells']:
        cid = inst['cell']['cell_id']
        if cid[0] in target_rows:
            by_row[cid[0]].append((model, run, inst['cell']['value']))
for row in target_rows:
    print(f'{row}:')
    for m, r, v in by_row[row]:
        print(f'  {m:25} {r}  value={v}')
    print()
"
```

**Context:** Claude session in `lobby_analysis` workspace, 2026-06-01. Standard `~/.claude/settings.json` permissions. Hook layer did not fire — the matcher itself prompted, and the prompt UI included a diagnostic message naming the heuristic verbatim: **"Newline followed by # inside a quoted argument can hide arguments from path validation"**. This is the first observation where Claude Code surfaced an internal heuristic name in the prompt UI; the brace+quote heuristic's name ("Contains brace with quote character (expansion obfuscation)") is the only prior comparable artifact.

**Segments + rules I think should match:**
- One shell command: `uv run python -c "<long python body>"`. `Bash(uv *)` is on the allow list and the `*` cleanly covers the `-c "..."` tail. No `&&`, `||`, `;`, or `|` outside the quoted body. The matcher should naively allow this on a per-segment basis.

**Hypothesis:** This is a matcher-side anti-obfuscation heuristic distinct from chain matching, the brace+quote detector, and the redirect-split conjecture. The matcher scans the command string for `\n` followed by `#` *inside a quoted argument* and flags it as potential arg-hiding from path validation. The threat model: a path-validation pass that stops at the first `#` (treating it as a bash comment) could be tricked by `\n# ...` sequences buried in a quoted argument. The heuristic is conservative — applies bash-lexical reasoning to the contents of `-c "..."` where the body is actually Python and `#` has Python-comment semantics, not bash-comment semantics. The triggering substring here is the `\n# For the 3-3 split rows...` line inside the `-c` body, a benign Python source comment.

This is **structurally the same family of false positive** as the brace+quote heuristic — the matcher does bash-lexical pattern scans against command strings whose quoted regions are actually code in a different language (Python, jq, awk, etc.).

The mention in `update_claude_permissions.py` line 430 ("`\n#` patterns in quoted `-c` bodies also trigger prompts") was already noted in the 2026-05-30 FINDINGS side-findings as a "yet-unconfirmed" anti-obfuscation heuristic. **This entry confirms it directly, with the matcher itself naming the heuristic.**

**Impact:**
- **Hook:** none — `block_bash_chains.py` not involved (no chain operators outside the quoted body). The existing `block_brace_quote_heredoc.py` doesn't catch this case either (different pattern, and this is a `-c` quoted body, not a heredoc).
- **Matcher-side:** confirmed third named anti-obfuscation heuristic. Family is growing: brace+quote, `\n#`-in-quoted-arg, and likely more.
- **User-workflow:** Write-then-run dodges this trivially — `Write('/tmp/script.py', body)` then `python3 /tmp/script.py` in a separate Bash call. No `-c "..."`, no quoted body for the matcher to scan, no false positive.
- **STRATEGIES.md:** this is a third concrete reason to default to Write-then-run for non-trivial Python (alongside (a) brace+quote literals tripping the brace-quote heuristic and (b) semicolons-in-quoted-body tokenizing wrongly).

**Classification:** matcher-side anti-obfuscation heuristic firing on benign code. NOT a hook bug, NOT a missing allow rule. Strategy 0 (no hook action this week) is fine because the Write-then-run workaround is already documented and the heuristic is just a third member of an already-known family; Strategy 2 (a dedicated `block_newline_hash_in_quoted_c_body.py` hook) becomes worthwhile only if Claude sessions keep tripping this despite the documented workaround.

**Promotion notes:**
- FINDINGS.md: promoted same-day. The evidence is direct (Claude Code named the heuristic) and matches a prior partially-confirmed conjecture (`update_claude_permissions.py:430`). This clears the bar for promotion.
- STRATEGIES.md: Write-then-run gets a third reason added to the rationale section.

---

### 2026-06-01 — bare `find` with `2>/dev/null` stderr redirect — single-segment, no chain — SUPERSEDED

**SUPERSEDED 2026-06-01 (later same day):** The trailing-redirect-tokenization hypothesis below was falsified by an A/B probe map. Single-segment probes WITH `2>/dev/null` against `/tmp` and `~/code` paths did NOT prompt, while `/Users/dan` and `/Users` DID. The real cause is a path-aware matcher heuristic on `find` ancestor-of-cwd paths — see the new entry **"find against ancestor-of-cwd home-dir path"** at the top of Pending. The redirect was a red herring here; the chained `ls ... 2>&1` weirdo logged below this entry also needs the redirect hypothesis demoted as a result (segment (a) `pwd` bare match is now the more likely live suspicion for that one).

Original entry follows for audit trail.

**Command:**
```
find /Users/dan -maxdepth 3 -name ".env.<CLIENT>" 2>/dev/null
```

**Context:** Dan-reported prompt on 2026-06-01 in dotfiles session. Standard `~/.claude/settings.json` permission state. `Bash(find *)` IS on the allow list (confirmed: `~/.claude/settings.json` line 15, `update_claude_permissions.py` line 75). No chain operators (`&&`, `||`, `;`, `|`) in the command — single segment.

**Segments + rules I think should match:**
- One segment, leading verb `find`. `Bash(find *)` glob should match the entire `find /Users/dan -maxdepth 3 -name ".env.<CLIENT>" 2>/dev/null` string.
- Only "unusual" feature: trailing `2>/dev/null` stderr redirect.
- Allow list cleanly covers this if the matcher does naive glob match against the full command string.

**Hypothesis (primary):** **The matcher does not strip / does not handle trailing redirection operators (`2>/dev/null`, `2>&1`, possibly `>file`, `<file`) when matching against `Bash(<cmd> *)` glob rules.** The literal `2>/dev/null` is included in the command string the matcher compares against the glob; for whatever reason the trailing-redirect tail isn't being accepted as part of the `*` swallow.

Several mechanisms could produce this:
- (i) The matcher tokenizes the command, treats `2>/dev/null` as a separate token *not* belonging to `find`'s arg list, leaving an unmatched tail.
- (ii) The matcher's glob is anchored or the `*` doesn't span the `>` character.
- (iii) The matcher splits on `>` similarly to how it splits on `;` (see 2026-05-30 `python3 -c` with semicolons-in-body weirdo) — naive lexical splitting regardless of shell semantics. After splitting on `>`, the right-hand fragment is `/dev/null` which has no allow rule. **This mirrors the semicolon-tokenization shape exactly** and would be the most parsimonious explanation given prior matcher behavior.

(iii) is favored — it's structurally identical to the known semicolon-split bug and would predict that *any* `>` or `<` outside quotes breaks the segment match. The `2>` form is just a special case (stderr fd-prefix + `>`).

**Cross-reference:** The prior `cd ... && pwd && ls -la .venv/bin/python 2>&1 | head -2` weirdo (logged just below as the next entry) had `2>&1` on its `ls` segment. Backup hypothesis (b) there blamed `2>&1` for breaking the `ls *` segment match; with this new single-segment observation that has the SAME shape (allow-list-clean bare command + trailing redirect → prompts), the redirect hypothesis is much better supported. The chained command is noisier (4 segments, multiple uncertainty sources); this one isolates the redirect as the sole non-trivial feature.

**Cheap aside-probe (not run — see Don'ts):** Dan suggested testing `find /tmp -name x` (no redirect, should be silent) vs `find /tmp -name x 2>/dev/null` (should prompt if hypothesis holds) as cheap confirmation. Deferred to the next deliberate probe session per the curator role's no-probe rule. Adding to probe TODO list (`probes/TEST_PLAN.md` should pick this up).

**Impact:**
- **Hook:** none — `block_bash_chains.py` not involved (no chain operators). Single segment, no `&&`/`||`/`;`/`|`, hook short-circuits.
- **Matcher-side:** if (iii) holds, this is a fourth class of matcher anti-pattern (after per-segment chain checking, cd-space-strictness, anti-obfuscation brace-quote). Affects far more commands than the previous three combined — every `cmd ... 2>/dev/null` or `cmd ... > out.txt` would prompt despite a clean `Bash(cmd *)` rule.
- **User-workflow:** if confirmed, drop the `2>/dev/null` tail or move it onto a separate Bash call wrapper. Or use Python's `subprocess` with `stderr=subprocess.DEVNULL` in a temp script (Write-then-run pattern).
- **Probe priority:** HIGH. This hypothesis explains both today's weirdos and likely a lot of "weirdly chained prompts in normal-looking commands" that haven't been individually logged. Worth promoting to FINDINGS.md if even one targeted probe confirms.

**Classification:** matcher-side weirdo, not hook-side. Single-segment makes this a clean discriminator — no chain-segment confound, no path-heuristic confound, no anti-obfuscation confound. Strong corroborator for hypothesis (b) on the prior `ls -la` entry.

---

### 2026-06-01 — absolute-path script invocation with stdin redirect — single-segment, no chain

**Command:**
```
/Users/dan/code/dotfiles/claude-hooks/block_bash_chains.py < /tmp/probe_chain.json
```

**Context:** Issued by Claude (chain-matcher-curator agent) inside the dotfiles work-line on 2026-06-01, while investigating the weirdo logged just below this entry. Standard `~/.claude/settings.json` permission state.

**Segments + rules I think should match:**
- One segment (no `&&`, `||`, `;`, or `|` — only an `<` stdin redirect).
- Leading verb: the absolute path `/Users/dan/code/dotfiles/claude-hooks/block_bash_chains.py`.
- Allow list contains nothing like `Bash(/Users/dan/code/dotfiles/claude-hooks/* *)` or `Bash(/Users/dan/* *)`. **No rule matches this leading verb.**

**Hypothesis:** Not a chain-matcher weirdo and not a hook weirdo — `block_bash_chains.py` correctly skips this (it has no chain operator). The matcher prompts because no allow rule matches the bare-absolute-path invocation form. This is the same shape as the 2026-05-30 `bash /Users/dan/code/dotfiles/install.sh ... | tail -5` weirdo above, minus the pipe: per-segment matching looks at the first token, and that token here is an absolute filesystem path with no corresponding `Bash(...)` rule.

**Impact:**
- **Hook:** none — block_bash_chains.py is not involved (verified by piping the recorded payload directly to the hook script; exits 0 / no output).
- **User-workflow / allow-rules:** confirms a pattern. Allow rules like `Bash(python3 *)` or `Bash(bash *)` are needed even when the script being invoked is shebang-self-executable. The hook's `Bash(<script-path> *)` form (project-local rule for `install.sh`) is narrow and won't match if Claude invokes a *different* script by absolute path. Generalizable fix would be `Bash(/Users/dan/code/dotfiles/claude-hooks/* *)` if direct-invoke of hooks becomes common, but most direct invocations of dotfiles scripts will continue to be one-offs and a separate prompt is fine.

**Classification:** matcher behaving correctly given the rules; user-rule gap, not a hook bug.

---

### 2026-06-01 — `cd <worktree-subpath> && pwd && ls ... 2>&1 | head -2`

**Command:**
```
cd /Users/dan/code/lobby_analysis/.worktrees/wi-tier1-direct-read && pwd && ls -la .venv/bin/python 2>&1 | head -2
```

**Context:** Issued by a Claude session in the `lobby_analysis` workspace (per Dan's report), not in dotfiles. Standard `~/.claude/settings.json` permission state. Date 2026-06-01.

**Segments + rules I think should match (per-segment model from 2026-05-30 FINDINGS):**
- Seg 1: `cd /Users/dan/code/lobby_analysis/.worktrees/wi-tier1-direct-read` — `Bash(cd /Users/dan/code/*)` (slash variant, added 2026-05-30) should match. ✓ should be allowed
- Seg 2: `pwd` (bare, no args) — `Bash(pwd *)`. Unknown whether bare-arg-less matches the `cmd *` glob; this exact uncertainty is the secondary suspicion logged on the 2026-05-30 triaged entry (`cd ... && pwd && git status ...`). ✗ POSSIBLE MISS
- Seg 3: `ls -la .venv/bin/python 2>&1` — `Bash(ls *)`. The `*` should swallow `-la .venv/bin/python`, but `2>&1` is a shell-syntax redirect, not a normal arg. Unknown whether the matcher tokenizes redirects as part of the segment or treats them as terminating the verb. ✗ POSSIBLE MISS
- Seg 4 (after pipe): `head -2` — `Bash(head *)`. ✓ should be allowed

**Hook trace:** I piped the literal payload to `block_bash_chains.py` (after writing it to a JSON file to avoid the brace+quote trip). The hook **exits cleanly with no output** — it correctly recognizes the `cd /Users/dan/code/...` prefix (`CD_CODE_RE` matches the padded command, span 0-66) and short-circuits at line 130. **So this is NOT the hook over-blocking; the matcher itself is what prompted Dan.**

**Hypothesis (REVISED 2026-06-01 later same day):** The matcher's per-segment check is failing on one of the middle segments. Three live candidates, ranking updated based on the `find ... 2>/dev/null` weirdo logged above:
- (b) **`2>&1` breaks the `ls *` segment match** — *PROMOTED to primary suspicion.* The single-segment `find /Users/dan -maxdepth 3 -name ".env.<CLIENT>" 2>/dev/null` weirdo logged above isolates trailing stderr-redirect as the sole non-trivial feature on a command with a clean allow rule (`Bash(find *)`) — and it still prompts. That's a much cleaner discriminator than the chained `ls` segment here. If the matcher naively-splits on `>` (mirroring the 2026-05-30 semicolon-split-inside-quoted-`-c`-body bug), then `ls -la .venv/bin/python 2>&1` becomes `ls -la .venv/bin/python 2`  / `&1` after the split, and the right-hand fragment has no allow rule. Same root cause as the `find` entry above.
- (a) **`pwd` (bare) doesn't match `Bash(pwd *)`** — demoted to secondary suspicion. Still plausible; the `find` weirdo doesn't address this. Same secondary suspicion as the 2026-05-30 `cd ... && pwd && git status ...` triaged entry. A `cmd *` glob requiring at least one trailing character (even a space) would explain it. Workaround would be allowing `Bash(pwd)` (no glob). Both (a) and (b) could be true simultaneously — they're not mutually exclusive.
- (c) **`.worktrees/` hidden-prefix path triggers a matcher heuristic** — paths containing hidden-dir components (leading `.` after a slash) might be treated specially. Lower-probability; nothing in current FINDINGS suggests this. Unchanged.

Promotion to FINDINGS.md priority: (b) is now ready for one targeted probe to confirm (`find /tmp -name x` vs `find /tmp -name x 2>/dev/null`). If that probe lands clean, the redirect-split lesson goes straight into FINDINGS.md and supersedes both this entry's segment-3 confusion and the `find` entry above.

**Impact:**
- **Hook:** none — block_bash_chains.py correctly allows this through. Confirmed by direct piping.
- **Allow rules:** if (b) is right (favored after the `find ... 2>/dev/null` corroboration above), there's no allow-rule fix — redirects-in-segments need a matcher-side fix or a workflow change (move the redirect out of the chained call). If (a) is also true, adding `Bash(pwd)` (no glob) to ALLOW_RULES is the cheapest fix for that sub-issue.
- **Probe priority:** HIGH. The existing probes/TEST_PLAN.md test #10 covers "bare `pwd` against `pwd *` glob." A new probe for "trailing `2>/dev/null` on an allow-listed verb" should be added — see the `find` entry above. Both should run in the next probe session.

**Classification:** matcher-side weirdo, not hook-side. Possibly resolved by an allow-rule addition pending probe.

---

### 2026-05-30 (later) — `bash <path> | tail -5` prompts; `bash` itself has no allow rule

**Command:**
```
bash /Users/dan/code/dotfiles/install.sh 2>&1 | tail -5
```

**Context:** Issued by Claude in dotfiles work-line build session. Standard perms (no pclaude/mclaude alias).

**Segments + rules:**
- Seg 1: `bash /Users/dan/code/dotfiles/install.sh 2>&1` — Dan has `Bash(/Users/dan/code/dotfiles/install.sh *)` (project-local rule) but the command starts with `bash` not with the script path. No `Bash(bash *)` rule exists. **Segment misses all rules.** ← root cause.
- Seg 2: `tail -5` — `Bash(tail *)`. ✓

**Hypothesis:** Per-segment matching from 5/30 findings holds. The pipe causes split; the `bash` invocation form is unrecognized; prompt fires.

**Resolution candidates (Strategy 1):**
- (a) Add `Bash(bash *)` to ALLOW_RULES — broad; risky for similar reasons we don't have `Bash(sh *)` etc.
- (b) Add `Bash(bash /Users/dan/code/dotfiles/* *)` — narrow.
- (c) **No code change**; just invoke as `/Users/dan/code/dotfiles/install.sh` directly (matches existing rule). Lowest-risk option since `install.sh` self-shebangs anyway.

Leaning toward (c) — the canonical invocation is the direct one. (b) as backup if Claude habitually adds `bash` prefix.

---

### 2026-05-30 — `python3 -c` with semicolons in body

**Command:**
```
python3 -c "
import json, re
d = json.load(open('/Users/dan/.claude/settings.json'))
rules = d['permissions']['allow']
... (lots more code with semicolons in dict literals and statements)
"
```

**Context:** Issued by Claude (me) inside the chain-hook design session. Dan's standard perms. Hook was NEUTERED at the time (so the matcher fully owned the decision).

**Segments + rules I think should match:**
- The whole command should be one segment: `python3 -c "<long string>"`, covered by `Bash(python3 *)`.

**Hypothesis:** Matcher does naive `;`-tokenization regardless of shell quoting. It sees the semicolons inside the python `-c` string literal, splits the command on them, and treats each post-semicolon fragment as a separate "segment" needing an allow rule. The fragments are python code (`d['permissions']['allow']`, `print(real)`, etc.), which obviously have no Bash allow rule. → PROMPT.

**Impact:** Significant. Any `python3 -c "...; ..."` or `sh -c "...; ..."` etc. that contains semicolons in the body will prompt, even though shell-semantically the `-c` argument is one quoted string. Implication for the hook: when re-designed, the hook should NOT try to match the matcher's behavior here — the matcher is wrong, and the hook should be smarter (use `strip_inert()` to ignore quoted semicolons, which it already does for blocking purposes; never-block-when-strip-inert-shows-no-real-chain logic could be useful).

---

### 2026-05-30 — `uv run --with pandas python <<'PY'` heredoc — anti-obfuscation detector — RESOLVED via deny hook

**Resolution (2026-05-30, later):** Strategy 2 (PreToolUse deny hook). Wrote `claude-hooks/block_brace_quote_heredoc.py` that detects `[\{\[]\s*['\"]` in heredoc bodies and denies with a nastygram pointing to Write-then-run. Registered via `ensure_block_brace_quote_heredoc_hook()` in `update_claude_permissions.py`; symlinked via `install.sh`; 4 characterization tests added (72/72 pass total). Live in next session — won't fire in the session where it was built (settings.json loaded at session start).

The empirical refinement: heuristic fires ONLY on unquoted-at-bash-level brace+quote (heredoc bodies, possibly bare unquoted args). Single-quoted (`'{"x":"y"}'`) and double-quoted (`"{\"x\":\"y\"}"`) contexts are silent — confirmed via probe-bq-{a,b,c,d,e2} in this session. So the hook is scoped to heredoc bodies only.


**Command:**
```
uv run --with pandas python <<'PY'
import pandas as pd
df = pd.read_csv("releases/wi/WI_lobbyist_filings.tsv", sep="\t", dtype={"lobbyist_id": "Int64"})
print(f"total rows: {len(df)}")
print(f"distinct lobbyist_id: {df['lobbyist_id'].nunique()}")
print(f"rows per (period_start, period_end):")
print(df.groupby(["reporting_period_start", "reporting_period_end"]).size())
... (more pandas / f-string code with braces and quotes) ...
PY
```

**Context:** Dan reported during chain-hook-maintenance design session: "things like this prompt me too, even though in theory the 'PY' thing means it shouldn't." Standard perms. The prompt UI included a diagnostic message: **"Contains brace with quote character (expansion obfuscation)"**.

**Segments + rules I think should match:**
- One shell command: `uv run --with pandas python` (covered by `Bash(uv *)`) reading stdin from the heredoc. Should match cleanly.

**Hypothesis (CORRECTED — initial hypothesis was wrong):** The matcher has an **anti-obfuscation heuristic** distinct from chain/segment matching. It flags commands containing brace-with-quote patterns (e.g. `{"key": "val"}`, `["a", "b"]`, `dtype={"foo": "bar"}`) as potential shell-expansion-trick obfuscation. The concern is presumably preventing things like `${IFS}` or `${PATH:0:1}` style obfuscation, but the heuristic is over-broad — it fires on ordinary python dict and list literals containing string keys/values.

The matcher doesn't seem to care that the braces are inside a heredoc body (which is just stdin to a different program); the heuristic scans the full command-string for the pattern regardless of shell context.

(My initial hypothesis blamed semicolon-tokenization of the heredoc body — that was wrong. The actual diagnostic Dan saw explicitly identified brace+quote as the trigger.)

**Impact:**
- This is a **third** class of matcher behavior we now know about: (1) per-segment allow checking on chains, (2) cd-rule space-vs-slash strictness, (3) anti-obfuscation brace-quote detection.
- Hook-side: nothing `block_bash_chains.py` can or should do here. This is matcher-side anti-obfuscation, not chain-related.
- User-workflow: any python/jq/other-DSL code with `{"...": "..."}` or `["...", "..."]` literals will trip this. Workaround: write a temp script file, then `python3 /tmp/script.py` (no embedded literals in the bash command itself).
- Probe TODO: confirm the trigger is brace+quote specifically (not just brace, not just quote) by running controlled tests.

#### Corroboration 2026-05-30 (later) — second uv heredoc, same diagnostic

Another instance of the same heuristic on a similar pandas-via-heredoc command. Same diagnostic text from the matcher: **"Contains brace with quote character (expansion obfuscation)"**. Command contained typical pandas patterns: `dtype={"lobbyist_id":"Int64","principal_id":"Int64"}`, `value_counts(dropna=False)`, `auths[["lobbyist_id","principal_id"]].drop_duplicates()`. Same hypothesis confirmed: the heuristic fires on any `{"...":"..."}` or `["...","..."]` substring in the command (including inside heredoc bodies). Strengthens the case that this is a stable, broadly-firing rule — not session-specific. **Reproducible: any non-trivial pandas / numpy / JSON-construction code in a `python -c` or heredoc-fed interpreter will hit it.**

---

### 2026-05-30 — `cp` writing into a path containing `.claude/`

**Command:**
```
cp /tmp/perm_probe/.claude/settings.json /Users/dan/code/dotfiles/docs/active/chain-hook-maintenance/probes/settings.json
```

**Context:** Issued by Claude inside chain-hook-maintenance design session. Dan: "I'm being asked for perms to write to '/tmp/perm_probe/.claude/' even though IIRC /tmp/ is already blanket granted?"

**Segments + rules that DO match (confirmed by reading the script):**
- One segment: `cp <src> <dst>`.
- `Bash(cp *)` is present in `update_claude_permissions.py` at line 110 (verified by grep, not guessed). The glob should match the full `cp <src> <dst>` string.
- `/tmp` is in `additionalDirectories` in the script (line 53), plus `Read(//tmp/**)`, `Edit(//tmp/**)`, `Write(//tmp/**)` rules at lines 234/239/244. So /tmp filesystem operations via Read/Edit/Write tools are broadly allowed — but this is a Bash `cp` call, which routes through Bash permission matching, not those.

**Confirmed false hypotheses:**
- ~~`Bash(cp *)` not in rules~~ — present, confirmed via grep.
- ~~"/tmp/ is blanket-granted via a `Bash(* /tmp/*)` rule"~~ — no such rule exists. Dan's mental model overstates what's automated. The dotfiles script does grant broad Read/Edit/Write to /tmp via tool-specific rules, but Bash commands operating on /tmp paths still need command-specific rules like `Bash(cp *)`.

**Live hypotheses:**
- (a) The matcher special-cases paths containing the literal string `.claude/`, treating writes to anything-with-.claude as sensitive regardless of which `.claude` directory it is. The cp's source `/tmp/perm_probe/.claude/settings.json` contains `.claude/`. This would be a "matcher anti-footgun" heuristic — protect users from clobbering their Claude Code config. Plausible.
- (b) Combined path length tripped a heuristic (~140 chars total).
- (c) Some interaction with the Write/Edit `(//tmp/**)` rules and Bash routing — unlikely but possible.

**Worth probing:** Two targeted tests would disambiguate (a) from (b):
- Test 1: `cp /tmp/x.txt /Users/dan/code/dotfiles/y.txt` (no `.claude` in either path, similar length). If silent → likely (a).
- Test 2: `cp /tmp/foo /tmp/.claude/bar` (mkdir parent first). If prompts → strongly supports (a).

**Classification:** This is not a chain-matcher weirdo — it's a separate matcher heuristic class (anti-footgun for sensitive paths, hypothesized). Worth keeping the entry here for now since it surfaced during this session, but if (a) is confirmed, the lesson belongs in a different note (proposed: `notes/permission_matcher_path_heuristics.md`).

---

## Triaged

(Move entries here once their lesson is captured in `FINDINGS.md`. Keep the original text for audit trail. Resolution note added at top of entry.)

### 2026-05-30 — Multi-segment `cd ... && pwd && git status && git log` — RESOLVED via Allow rule

**Resolution (2026-05-30):** Strategy 1 (add Allow rule). Added `Bash(cd /Users/dan/code/*)` (slash variant) to `update_claude_permissions.py` `ALLOW_RULES`, adjacent to the existing `Bash(cd /Users/dan/code *)` (space variant). Tests pass (68/68). Applied to live settings via `install.sh`. Lesson captured in `FINDINGS.md`'s 2026-05-30 side findings. The secondary `pwd` bare-arg-less suspicion is unresolved — left in `probes/TEST_PLAN.md` test #10 for next probe session.

---

**Command:**
```
cd /Users/dan/code/lobby_analysis/.worktrees/wi-allocation-matrix && pwd && git status && git log --oneline -10
```

**Context:** A different agent/workspace (per Dan: "this just triggered on a different agent/workspace"). Standard `~/.claude/settings.json` permission state (not bypassed). Triggered during chain-hook-maintenance design session.

**Segments + rules I think should match:**
- `cd /Users/dan/code/lobby_analysis/.worktrees/wi-allocation-matrix` — Dan has `Bash(cd /Users/dan/code *)` BUT the rule's `*` is preceded by a space; the command has `/` right after `code`. So **this segment does NOT match** the rule (space vs. slash mismatch). Workaround: add `Bash(cd /Users/dan/code/*)` (slash variant) to perms.
- `pwd` — Dan has `Bash(pwd *)`. Glob `pwd *` would match `pwd ` + anything. Bare `pwd` (no trailing args) **may or may not match** depending on whether the matcher treats trailing space-then-empty as a match. Worth a targeted probe.
- `git status` — matches `Bash(git *)`. ✓
- `git log --oneline -10` — matches `Bash(git *)`. ✓

**Hypothesis:** First-segment failure (cd-rule space-strictness) triggers prompt; per-segment matching from 5/30 findings holds, the failing segment is the cd. Secondary suspicion: `pwd` segment may also miss. Confirmed neither by isolated probe yet.

**Impact:** Two specific weirdos here — (a) space-strict cd-rule path matching, (b) possibly bare-arg-less commands not matching `cmd *` glob. Both worth confirming in a future probe session.


### 2026-07-24 — semicolons inside quoted `git commit -m "<msg>"` body tripped block_bash_chains hook DENY (single command, no chain)

**Command:**
```
git -C /Users/dan/code/websites/canary-drafts/.claude/worktrees/frontier-act-release commit -am "Apply mechanical fixes from verification pass (Dan-approved: errors 1-7 + typos + link fills)

- six->seven weeks (x3); 'last week' -> 'two days ago' (x3, GAAIA post was 7/22)
... (multi-line -m body containing several `;` chars and parens) ...
Voice-sensitive rewrites deliberately NOT applied (seams protocol) - see results doc."
```

**Context:** canary-drafts `frontier-act-release` session on `Dans-MacBook-Pro`, 2026-07-24. Single `git commit -am` with a multi-line quoted message. No shell chain: every `;` is inside the double-quoted `-m` argument.

**Segments + rules I think should match:** one segment, leading verb `git` (blanket ALLOW `Bash(git *)`). Should run silently.

**Hypothesis:** `block_bash_chains.py` splits on `;` without quote-awareness (or its quote-stripping missed multi-line double-quoted bodies), so quoted-data semicolons were treated as chain separators, producing segments whose "leading verbs" are message words (e.g. `'last`, `AIID:`) — not blanket → DENY. Hook-side bug/over-fire, not matcher-side.

**Workaround used:** Write message to /tmp file, `git commit -aF <file>` — worked, single blanket-verb command. (Also generally the safer pattern for multi-line commit messages.)

**Impact suggestion:** quote-strip before splitting on chain separators in `block_bash_chains.py`, or special-case `-m "<...>"` bodies. Curator to triage.

---

### 2026-07-28 — `diff <(sed …) <file>` prompts despite `Bash(diff *)` ALLOW — process substitution `<(…)` is a candidate NEW Family-3 node (`process_substitution`); ALSO a live data cell for the 2026-07-14 Family-2 cwd-tree-vs-`additionalDirectories` discriminator (second diff arg is in `additionalDirectories` but NOT under cwd)

**RESOLVED 2026-07-28 (same day; HITL probes, Dan at keyboard capturing prompt reason-text):** PRIMARY confirmed — **`process_substitution` is a Family-3 static-analysis bail node, the sixth known** (after `file_redirect`, `pipeline`, `simple_expansion`, `brace_expansion`, `string`). Probe results:
1. Control `diff /Users/dan/code/dotfiles/README.md /Users/dan/code/dotfiles/README.md` — **SILENT**, ran. `Bash(diff *)` fires normally.
2. Path-scope cell `diff /Users/dan/code/dotfiles/nori-researcher/skills/write-a-plan/SKILL.md /Users/dan/.claude/skills/write-a-plan/SKILL.md` (no procsub; second arg in `additionalDirectories`, NOT under cwd) — **SILENT**, ran (exit 0; files byte-identical, irrelevant to the permission result). Kills SECONDARY *for this weirdo*; also feeds the 2026-07-14 grep entry's trust-set question (with a verb-coverage caveat — see the update note there).
3. Procsub isolation `diff <(echo a) <(echo b)` — **PROMPTED**; captured reason-text verbatim: **"Contains process_substitution"**. Dan denied (probe purpose served).

The original weirdo's prompt is fully explained by the procsub alone. Lesson promoted to FINDINGS.md 2026-07-28. **Disposition: Strategy 0** — first procsub sighting; the deny-hook gate (frequent AND clean-alternative) fails on frequency. Clean alternative when it recurs: materialize procsub inputs to /tmp files (render-then-run). No hook changes.


**Command:**
```
diff <(sed 's|{{skills_dir}}|/Users/dan/.claude/skills|g' ~/code/dotfiles/nori-researcher/skills/write-a-plan/SKILL.md) ~/.claude/skills/write-a-plan/SKILL.md
```

**Intent:** diff the write-a-plan skill's dotfiles source (with the `{{skills_dir}}` template placeholder substituted) against the installed copy in `~/.claude/skills/`.

**Prompt UI text: NOT captured.** Dan reported the prompt but not the reason-text. This is the single most discriminating missing datum — "Contains shell syntax (process_substitution) that cannot be statically analyzed" would confirm a Family-3 bail; attribution-less command+description (as in the 2026-07-14 grep entry) would point at the path-scope mechanism; `Bash(diff *) requires confirmation` framing would point at rule-level weirdness. Capture it if this shape recurs.

**Context:** Dan-reported real-world prompt, 2026-07-28, on `Dans-MacBook-Pro`, cwd `~/code/dotfiles`. Standard `~/.claude/settings.json`, all Dan-authored hooks live.

**Permission state at trigger (verified live this session):**
- **ALLOW:** `Bash(diff *)` IS present in the global allow list (blanket file-op verb, alongside `sed`, `cat`, etc.). `Bash(sed *)` also present. So "diff has no allow rule" is **falsified** — the verb is covered.
- **ASK:** no `diff` or `sed` ASK entry (rules out 2026-06-09 curl-style ASK > ALLOW preemption).
- **additionalDirectories:** `/Users/dan/.nori/profiles`, `/Users/dan/code`, `/Users/dan/data`, `/Users/dan/.claude/skills`, `/tmp`. Both file args are inside this set: the sed source is under `/Users/dan/code` (also under cwd), and `~/.claude/skills/write-a-plan/SKILL.md` is under `/Users/dan/.claude/skills` — **in `additionalDirectories` but NOT under cwd `~/code/dotfiles`.** That asymmetry is load-bearing for the hypothesis ranking below.
- **Hooks:** traced the exact command through all eight Bash PreToolUse hooks this session (`block_bash_chains`, `block_brace_expansion`, `block_brace_quote_heredoc`, `block_loop_with_pipe`, `block_heredoc_with_pipe_or_redirect`, `block_cd_git`, `block_absolute_path_py_verb`, `block_newline_hash_in_quoted_arg`) — **all exit 0, silent.** No `&&`/`||`/`;`/top-level-`|` (the `|`s are sed-delimiters inside single quotes), no heredoc, no loop, no `.py` verb; `{{skills_dir}}` has no comma/`..` so brace-expansion guards correctly pass it. Hook version: `block_bash_chains.py` @ 0374f66 (2026-06-05). **NOT a hook problem.**

**Segments + rules I think should match:** Single top-level segment, leading verb `diff` → `Bash(diff *)` should swallow the whole command under the standing verb-anchored model. Nested inside the process substitution: `sed 's|…|…|g' <trusted-path>` — itself blanket-allowed and structurally trivial. Under the pre-2026-07-14 model this runs silent. Two structurally novel elements relative to everything in FINDINGS: (a) the process substitution `<(…)` — a tree-sitter-bash `process_substitution` node we have never probed; (b) a file arg in `additionalDirectories`-but-not-cwd-tree for a verb (`diff`) that the 2026-07-14 entry explicitly listed as untested for the Family-2 path-scope check.

**Hypothesis stack:**

**PRIMARY: Family-3 static-analysis bail on `process_substitution` — candidate NEW node joining `file_redirect`, `pipeline`, `simple_expansion`, `brace_expansion`, `string`.** Process substitution is architecturally exactly what Family 3 bails on: the construct materializes a runtime fd path (`/dev/fd/N`) whose content is produced by an embedded command, so the matcher cannot statically bound what `diff`'s first argument *is*, nor fold the inner `sed`'s effects into the outer verb's analysis. Same "construct that's individually fine breaks the fast-path when nested" architecture as heredoc+redirect and loop+pipeline. Parsimonious: explains the prompt with `Bash(diff *)` present and both paths trusted.

**SECONDARY: Family-2 path-scope prompt — this cell is evidence FOR the 2026-07-14 entry's own SECONDARY (cwd-tree trust) hypothesis.** The 2026-07-14 grep probes could not distinguish "trust = `additionalDirectories`" from "trust = cwd subtree" (its P9 pass was consistent with both). Here, `~/.claude/skills/write-a-plan/SKILL.md` is IN `additionalDirectories` but NOT under cwd. If the path-scope mechanism covers `diff` (untested there; plausible — it's a file-content-reading verb like `grep`) and the trust set is **cwd-tree**, this command prompts *even without the procsub*. If the trust set is `additionalDirectories`, this path is trusted and SECONDARY predicts silence — pushing the explanation back to PRIMARY. So the two hypotheses are cleanly discriminable, and *whichever way the probe falls, it also advances the 2026-07-14 entry.* Sub-variant worth noting: the command used tilde forms (`~/.claude/…`, `~/code/…`); if the matcher does set-membership on the *unexpanded literal* rather than the expanded path, even an `additionalDirectories`-trusting matcher could miss. Cheap to control for by probing absolute-path forms.

**TERTIARY: leading-verb parse failure — the procsub makes the matcher unable to anchor `diff` as the verb at all, so NO rule matches and it default-prompts.** Mechanically distinct from PRIMARY (rule-resolution failure rather than an explicit static-analysis bail) but observationally similar; discriminated by prompt UI text (default-for-Bash `Bash(diff <full-command>)` framing vs. Family-3 reason-text).

**FALSIFIED: plain allow-rule miss on the verb.** `Bash(diff *)` is present (verified live). The prompt is not explained by a missing rule.

**Ranking: PRIMARY > SECONDARY > TERTIARY.** PRIMARY needs no assumptions beyond the well-established Family-3 architecture. SECONDARY requires two currently-unconfirmed extensions at once (verb coverage of `diff` + cwd-tree trust semantics), but is live because both are open questions from 2026-07-14. TERTIARY is a UI-discriminable long-shot.

**Cheap discriminator probes (NOT run — curator role):**
1. **`diff /tmp/a /tmp/b`** (both trusted, under no reading of the trust set contested, no procsub) — baseline. If silent: verb + rule healthy; if PROMPT: something deeper is wrong with `diff` handling, all hypotheses reopen.
2. **`diff /Users/dan/code/dotfiles/README.md /Users/dan/.claude/skills/write-a-plan/SKILL.md`** (no procsub, absolute paths, second arg in `additionalDirectories`-not-cwd) — **the key cell.** PROMPT → SECONDARY confirmed here AND resolves the 2026-07-14 PRIMARY-vs-SECONDARY discriminator toward cwd-tree trust for verb `diff` (major finding). Silent → path-scope exonerated; procsub is the trigger (PRIMARY).
3. **`diff <(echo a) <(echo b)`** from cwd `/tmp` — minimal procsub, no interesting paths at all. PROMPT → procsub bails on its own (PRIMARY confirmed); capture the reason-text for the node name. Silent → procsub per se is fine and the path/tilde axis carries the weirdo.
4. **Tilde control:** re-run probe 2 with `~/`-literal forms. Discriminates unexpanded-literal set-membership.
5. Whichever probe prompts, **capture the UI reason-text** — the missing datum from this report.

**Impact:**
- **Hooks:** none fire; none should. Not a hook problem, no hook change indicated (and per the 2026-07-10 matcher-preempts-hooks ordering hypothesis, a Strategy-2 hook for Family-3 shapes may be unable to intercept the live prompt anyway).
- **Matcher-side:** if PRIMARY confirms → **NEW Family-3 node `process_substitution`**, sixth known node. If SECONDARY confirms → resolves the 2026-07-14 trust-set question toward cwd-tree, which would be the more consequential finding (implies `additionalDirectories` doesn't carry to Bash path args).
- **Allow rules:** no rule-shape fix available under PRIMARY (structural bail is pre-allow-list) or SECONDARY (path-scope preempts `Bash(<verb> *)`).
- **Workaround (usable today, either way):** Write-then-run the substitution — `sed 's|{{skills_dir}}|…|g' <source> > /tmp/write-a-plan.rendered.md` then `diff /tmp/write-a-plan.rendered.md ~/.claude/skills/write-a-plan/SKILL.md` as separate Bash calls. Both are single blanket-verb commands with `/tmp` targets. (If SECONDARY holds, the second call may still prompt on the `~/.claude/skills` arg — which would itself be diagnostic.)
- **STRATEGIES.md:** wait for probes. If PRIMARY confirms, add a line: *"Process substitution `<(…)` triggers a Family-3 static-analysis bail regardless of the outer verb's ALLOW rule. Render to a /tmp file first, then run the outer command on the file."* Frequency check for the Strategy-2 gate: procsub-diff is an occasional pattern, not a per-session one — likely Strategy 0 even once confirmed.

**Classification:** matcher-side prompt; NOT a hook problem; NOT a missing allow rule (`Bash(diff *)` exists). Most likely a **candidate NEW Family-3 node (`process_substitution`)**, with a live alternative that this is instead the 2026-07-14 Family-2 path-scope mechanism resolving toward cwd-tree trust — probes 2 and 3 discriminate cleanly, and each outcome advances one of the two open entries. Prompt UI reason-text was not captured; flag it for capture on recurrence.

---

### 2026-08-03 — Bash sandbox layer in CC 2.1.220 — TRIAGED 2026-08-03 (same day): no interference observed across the completed 8-row pass; methodology switched to deviation-triggered

**Original concern (from the aborted 2026-08-03 probe):** CC 2.1.220's Bash tool exposes a `dangerouslyDisableSandbox` parameter (absent in 2.1.165), implying a sandbox layer upstream of the permission matcher that could corrupt drift checks in both directions — most dangerously by auto-permitting read-only Family-3 shapes, producing false "the heuristic disappeared, delete the hook" readings. An isolation matrix (S1–S6) was drafted.

**Resolution (FINDINGS 2026-08-03 completed run):** the full min-viable pass ran in the default (sandbox-on) condition with **zero deviations** — in particular:
- S1 `ls /tmp/{a,b}` → PROMPT "Brace expansion" (sandbox did NOT auto-permit; `block_brace_expansion.py` safe)
- S2 `diff <(echo a) <(echo b)` → PROMPT "Contains process_substitution"
- S3 corrected heredoc+redirect → PROMPT "Contains shell syntax (file_redirect)…"
- S4 `touch /tmp/probe_sanity` → resolved as path-scope, CONFIRMED via `additionalDirectories` flip (Finding A)
- S6 `claude --help |…` silence → resolved as CC self-`--help` special case + top-level-pipe fast-path (Finding C), not sandbox

The interception layer remains uncharacterized *in general* (the flag's true bypass semantics were never directly observed), but it demonstrably did not affect any probed shape, which was the operational worry. METHODOLOGY.md updated: default practice is now a single sandbox-on pass with deviation-triggered `dangerouslyDisableSandbox: true` re-runs, not the full two-column matrix.

**Version-scope note:** sandbox behavior is a CC-binary property, identical across machines at the same CC version. For any spinoff/public reuse of this corpus: re-check on each CC version bump; the deviation-triggered protocol makes that cheap.
