# probes/TEST_PLAN.md

Runnable probe plan for clean-room investigation of Claude Code's permission matcher. Updated whenever findings shift (see `../FINDINGS.md`).

## Protocol

```
cd /Users/dan/code/dotfiles/docs/active/chain-hook-maintenance/probes
claude --setting-sources project
```

`--setting-sources project` loads ONLY this directory's `settings.json` — skips your user-level hooks (so `block_bash_chains.py` doesn't interfere) and skips your user-level allow rules (so only the rules listed here are active). Auth (OAuth/keychain) is unaffected.

**Permission mode (mandatory as of 2026-09-02):** the probe session must be in **default mode** for every matcher row — CC ≥2.1.258 starts sessions in auto mode, whose classifier silently ALLOWs all prompt families and masks every matcher verdict (FINDINGS 2026-09-02). Switch with shift+tab and confirm the indicator before row 1.

For each test row below:

1. Paste the **User message** into the probe Claude.
2. Watch the next Bash tool call. Either:
   - A **permission prompt** appears → mark `PROMPT` in the result column, deny it, continue.
   - The tool **runs without prompting** (succeeds OR errors with "command not found" — doesn't matter) → mark `ALLOW`.
3. If Claude in the probe session does something other than the single Bash call (retries, asks questions, etc.), abort and note in `../FINDINGS.md`.

Markers like `probemarker_NN` are intentional — they have no allow rule, so a chain that's ALLOWED can only have been because the OTHER segments' rules matched.

## Current test set

Mix of confirming tests (re-check known findings — guard against drift) and exploration tests (open questions from latest weirdos).

**Content history:** originally 11 rows (as of 2026-05-30) covering the per-segment hypothesis + several exploration cells. Extended 2026-07-31 to cover the six Family-3 nodes, two Family-1 heuristics, one Family-2 row, and two verb/allow-rule gaps that shipped hooks between June and July 2026.

**Minimum-viable drift check (~8 tests):** run **1, 3, 4, 14, 16, 17, 20, 21**. These are one representative per matcher family / heuristic type. Full pass (all rows) is ~5-10 minutes of active y/n time.

**Legacy per-segment set (5/30 hypothesis):** tests 2, 5, 11 originally paired with 1, 3, 4 to confirm per-segment behavior. FINDINGS 2026-06-05 upgraded confidence to "very high — surviving three independent sessions." **Kept for historical completeness, dropped from minimum-viable pass.** Tests 3 and 4 remain as the canonical per-segment representatives.

**Loop-related tests** live in `TEST_PLAN_loop_reenable.md` (loop keywords deliberately absent from `settings.json` allow-list so native matcher behavior is observable). Do NOT duplicate here. The `\n#` heuristic has its own `PROBE_NEWLINE_HASH_HEURISTIC.md`.

### Core: confirm per-segment hypothesis still holds

| # | User message | Allow rule that should match each segment | Hypothesis | Result |
|---|---|---|---|---|
| 1 | Use the Bash tool to run this exact command once and stop: `touch /tmp/probe_sanity` | `Bash(touch *)` | ALLOW (sanity) | |
| 2 | Use the Bash tool to run this exact command once and stop: `cd /tmp && probemarker_test2` | `Bash(cd /tmp *)` for seg1; nothing for seg2 | PROMPT (per-segment: seg2 has no rule). **SETTLED — legacy, drop from minimum-viable** | |
| 3 | Use the Bash tool to run this exact command once and stop: `mkdir -p /tmp/probe3 && touch /tmp/probe3/x` | `Bash(mkdir *)` + `Bash(touch *)` | ALLOW (per-segment: both rules present) | |
| 4 | Use the Bash tool to run this exact command once and stop: `mkdir -p /tmp/probe4 && unknownmarker_test4` | `Bash(mkdir *)` for seg1; nothing for seg2 | PROMPT | |
| 5 | Use the Bash tool to run this exact command once and stop: `ls /tmp \| head -3` | `Bash(ls *)` + `Bash(head *)` | ALLOW (per-segment for pipes). **SETTLED — legacy, drop from minimum-viable** | |
| 11 | Use the Bash tool to run this exact command once and stop: `git --version && git --version` | `Bash(git *)` for both segments | ALLOW (per-segment: both rules present). Mirrors the real-world friction pattern that motivated the re-probe (`git status && git log`). Uses `--version` so the test has no cwd dependency and can't error. **SETTLED — legacy, drop from minimum-viable** | |

### Exploration: cd-rule path matching (slash-vs-space)

| # | User message | Allow rule that should match | Hypothesis | Result |
|---|---|---|---|---|
| 6 | Use the Bash tool to run this exact command once and stop: `cd /tmp/probe6_subdir && touch /tmp/probe6_subdir/x` | `Bash(cd /tmp *)` for seg1 (SLASH after /tmp, not space — does the rule match?); `Bash(touch *)` for seg2 | UNKNOWN. If matcher needs a space immediately after /tmp, this prompts. If glob is flexible, allows. First, `mkdir /tmp/probe6_subdir` separately. | |

### Exploration: quoted-semicolon naivety

| # | User message | Allow rule | Hypothesis | Result |
|---|---|---|---|---|
| 7 | Use the Bash tool to run this exact command once and stop: `python3 -c "print(1)"` | `Bash(python3 *)` | ALLOW (no semicolons in body) | |
| 8 | Use the Bash tool to run this exact command once and stop: `python3 -c "import os; print(os.getcwd())"` | `Bash(python3 *)` | If matcher is quote-naive: PROMPT (sees `;`, splits, second segment is python code with no rule). If quote-aware: ALLOW. | |
| 9 | Use the Bash tool to run this exact command once and stop: `python3 <<'PY'`<br>`import os`<br>`print(os.getcwd())`<br>`PY` | `Bash(python3 *)` | ALLOW (no semicolons, just newlines — should distinguish "matcher chokes on `;`" from "matcher chokes on `<<`") | |

### Exploration: bare command vs glob

| # | User message | Allow rule | Hypothesis | Result |
|---|---|---|---|---|
| 10 | Use the Bash tool to run this exact command once and stop: `pwd` | `Bash(pwd *)` | Does `pwd *` glob match `pwd` (no args)? If `*` requires non-empty arg: PROMPT. If allows empty: ALLOW. | |

### Family-3 nodes: matcher static-analysis bails (verb-agnostic)

Each of these has a shipped hook that upgrades the native PROMPT to a DENY. This section drift-checks the matcher's underlying prompting behavior — if any row ALLOWS unexpectedly, the corresponding hook may no longer be earning its keep.

| # | User message | Allow rule | Hypothesis | Result |
|---|---|---|---|---|
| 14 | Use the Bash tool to run this exact command once and stop: `python3 <<'PY' 2>&1`<br>`print(1)`<br>`PY` | `Bash(python3 *)` | PROMPT (`file_redirect`) — heredoc + `2>&1` co-occurring on open line trips Family-3 static-analysis bail per FINDINGS 2026-06-05. | 2026-08-03: PROMPT, "Contains shell syntax (file_redirect) that cannot be statically analyzed" — verbatim. **Row shape corrected 2026-08-03**: the original put `2>&1` on the terminator line, which never parses as a redirect (the heredoc never closes; the text is fed to python as stdin) — that malformed shape ALLOWs, correctly, and tests nothing. Redirect must be on the OPEN line, matching this row's own hypothesis text. |
| 15 | Use the Bash tool to run this exact command once and stop: `python3 <<'PY' \| grep 1`<br>`print(1)`<br>`PY` | `Bash(python3 *)` | PROMPT (`pipeline`) — heredoc + `\|` co-occurring on open line trips Family-3 static-analysis bail. | **Row shape corrected 2026-08-03** (same defect as row 14: pipe was on the terminator line, where it is heredoc body text, not shell syntax). Not run 2026-08-03 (row 14 covers the family for min-viable). |
| 16 | Use the Bash tool to run this exact command once and stop: `ls /tmp/{a,b}` | `Bash(ls *)` | PROMPT ("Brace expansion") — Family-3 row #2 per FINDINGS 2026-06-05. Verb-agnostic; even `Bash(ls *)` doesn't override. | |
| 17 | Use the Bash tool to run this exact command once and stop: `diff <(echo a) <(echo b)` | `Bash(diff *)` (needs adding, see below) | PROMPT (`process_substitution`) — sixth Family-3 node, confirmed FINDINGS 2026-07-28. Most drift-sensitive (newest). | |

### Family-1 heuristics: anti-obfuscation (quoted-arg content inspection)

Family-1 heuristics fire based on lexical patterns inside quoted arguments, even when the outer allow-rule matches. Shipped hooks catch these before the user sees the prompt.

| # | User message | Allow rule | Hypothesis | Result |
|---|---|---|---|---|
| 18 | Use the Bash tool to run this exact command once and stop: `python3 <<'PY'`<br>`x = {"key": "value"}`<br>`print(x)`<br>`PY` | `Bash(python3 *)` | PROMPT ("Contains brace with quote character") — brace/bracket immediately followed by a quote in bash-unquoted context (heredoc body counts as unquoted). See `block_brace_quote_heredoc.py`. | |

(`\n#` in `-c "…"` heuristic: see `PROBE_NEWLINE_HASH_HEURISTIC.md` — do not duplicate here.)

### Family-2 rules: path / trust-set

Family-2 rules gate on filesystem paths outside the trusted set (typically `additionalDirectories` or cwd-tree).

| # | User message | Allow rule | Hypothesis | Result |
|---|---|---|---|---|
| 20 | Use the Bash tool to run this exact command once and stop: `find /Users/dan -maxdepth 1 -name .bashrc` | `Bash(find *)` (needs adding, see below) | PROMPT — `find` ancestor of cwd outside trusted roots. FINDINGS 2026-06-01. Cheap drift-check on a stable finding. Control: `find /Users/dan/code -maxdepth 1 -name x` should ALLOW. | |

### Verb / allow-rule gaps (not matcher-native)

Not matcher heuristics — these are plain allow-list misses. Included so drift in Anthropic's default allow-list gets caught.

| # | User message | Allow rule | Hypothesis | Result |
|---|---|---|---|---|
| 21 | Use the Bash tool to run this exact command once and stop: `/tmp/x.py` (create first with `touch /tmp/x.py`) | none — verb is `/tmp/x.py` (leading path ending `.py`) | PROMPT — allow-list has no rule for absolute/relative `.py` paths as leading verb. See `block_absolute_path_py_verb.py`. Control: `python3 /tmp/x.py` should ALLOW. | |
| 22 | Use the Bash tool to run this exact command once and stop: `ls /tmp/x\ y` (create first with `mkdir -p '/tmp/x y'`) | `Bash(ls *)` | Backslash-escaped whitespace in path — matcher may bail per INCOMING 2026-06-03. If it prompts, this is an untested Family-3 (or Family-1) shape. | |

### Speculative (open in INCOMING, unconfirmed)

Run these when time permits — they close open weirdos in INCOMING.md but hypotheses aren't yet locked.

| # | User message | Allow rule | Hypothesis | Result |
|---|---|---|---|---|
| S1 | Use the Bash tool to run this exact command once and stop: `until [ -n "$(date)" ]; do sleep 1; done` | (no loop rules) | INCOMING 2026-07-10 candidate seventh Family-3 node `(string)`: nested `$(…)` inside `"…"` inside `[ ]` inside `until` — does interpolation-in-test alone bail, or is the redirect load-bearing? | |
| S2 | Use the Bash tool to run this exact command once and stop: `grep foo /Users/dan/data/probemarker` from cwd `~/code/dotfiles` (probemarker file need not exist) | `Bash(grep *)` (needs adding, see below) | INCOMING 2026-07-14 proposed Family-2 second row: does path-arg outside `additionalDirectories` prompt on `grep` even when cwd is a trusted tree? Discriminator between `additionalDirectories` trust-set vs. cwd-tree trust-set. | |

## Settings.json rules to add

Extending TEST_PLAN.md requires these allow-rules in `.claude/settings.json` for the new tests to run unambiguously:

- `Bash(diff *)` — for test 17 (procsub)
- `Bash(find *)` — for test 20 (find-ancestor)
- `Bash(grep *)` — for speculative S2 (Family-2 grep row)

Do NOT add `Bash(for *)`, `Bash(while *)`, `Bash(until *)` — loop keywords are deliberately absent per `TEST_PLAN_loop_reenable.md`'s design.

## How to interpret a row

- **All hypotheses confirmed:** No matcher change since last probe. Update FINDINGS.md with a brief "re-confirmed 2026-05-30 model on YYYY-MM-DD" entry.
- **Any hypothesis falsified:** New data. Write a full FINDINGS.md entry. Re-assess what the hook should do.
- **Any test unrunnable (Claude refuses to issue, harness errors, etc.):** Note in FINDINGS.md as an investigation gap.

## Settings used

See `settings.json` in this directory. Each rule listed there is consciously chosen to disambiguate exactly one hypothesis above. If you add a test, add only the minimal rule(s) it needs; rules that overlap multiple tests defeat the unambiguity property.
