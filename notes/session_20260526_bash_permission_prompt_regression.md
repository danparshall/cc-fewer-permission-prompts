# Bash permission allowlist stopped being honored mid-session

**Status:** resolved-in-practice — regression no longer reproduces on
Claude Code 2.1.150 with broadened `additionalDirectories`. Root cause
not isolated (version vs. config); isolation test deferred. See
"Second fresh-session probe results" below for the empirical update.
**Discovered:** 2026-05-26, mid-session in `/Users/dan/code/dotfiles`.
**Session context:** original session started 2026-05-25 evening UTC,
rolled past midnight to 2026-05-26 (system reminder reported the date
change). Fresh-session follow-up: 2026-05-26 ~18:10 UTC on
`Dans-MacBook-Air`, Claude Code 2.1.144.

## Symptom

Bash commands matching well-established allowlist rules started
prompting Dan for permission, mid-session. The allowlist itself is
intact (`Bash(cp *)`, `Bash(ls *)`, etc. all present in
`~/.claude/settings.json`), but the matcher is no longer honoring them
for commands that include file path arguments or shell operators.

Originally noticed via:
```
cp /tmp/wi_grid_all.html /Users/dan/code/lobby_analysis/.worktrees/wi-disclosure-explore/tests/fixtures/wi/lobbyist_grid_2025REG.html
```
in a parallel lobby_analysis session. Reproduced from this dotfiles
session too.

## What's been confirmed

**Allowlist structure intact** (verified via `json.load` of
`~/.claude/settings.json`):
- `Bash(cp *)` present in `permissions.allow`
- `Bash(ls *)` present
- `Bash(echo *)` present
- 126 allow rules total, no parse errors
- No DENY rule matches cp/ls
- No ASK rule matches cp/ls
- Project-level `/Users/dan/code/dotfiles/.claude/settings.local.json`
  only ADDS rules (3 specific `cp` paths and 1 `Bash` script) — no
  restrictions

**Project-level overrides** are minimal and additive only.

**Hooks audited:**
- `block_cd_git.py` — fires on `cd <path> && git ...`, doesn't match cp/ls.
- `block_bash_chains.py` — `CHAIN_RE = re.compile(r'&&|\|\||;')`. Single
  `|` (pipe) does NOT match (`\|\|` is the alternation for `||`, not
  single pipe). cp/ls without operators don't fire it.
- `use_uv_run_python.py` — only matches `.venv/bin/python(3)`. Doesn't
  match cp/ls.
- `require_finish_convo.py` — gates `gh pr create` only, not cp/ls.
- `commit-author.js` (nori-skillsets) — **NOT AUDITED.** Description
  says "Replace Claude Code co-author attribution with Nori in git
  commits" — sounds like a transform, but I didn't read the source.
  Possible source of misfiring `permissionDecision: "ask"` outputs.

## Empirical test results (this session)

All commands run from cwd `/Users/dan/code/dotfiles`.

| Command | Prompted? | Notes |
|---|---|---|
| `echo hello` | NO | Plain output, no args with paths. |
| `whoami` | NO | No args. |
| `pwd` | NO | No args. |
| `cp /tmp/cp_perm_diag.html /tmp/cp_perm_diag_dest.html` | **YES** | Both source and dest in /tmp. |
| `cp /tmp/cp_perm_diag.html /Users/dan/code/dotfiles/cp_perm_diag.html` | **YES** | Dest inside session cwd. |
| `cp /tmp/cp_perm_diag.html /Users/dan/code/lobby_analysis/.worktrees/wi-disclosure-explore/tests/fixtures/wi/cp_perm_diag.html` | **YES** | Cross-repo dest. |
| `echo '...' \| ~/.claude/hooks/block_bash_chains.py` | **YES** | Pipe + script-at-absolute-path. |
| `echo '...' \| ~/.claude/hooks/use_uv_run_python.py` | **YES** | Same shape. |
| `ls -la /tmp/X /Users/dan/code/dotfiles/Y /Users/dan/code/lobby_analysis/.../Z` | **YES** | ls with multiple absolute paths. |

**Earlier in the session** (before the regression appeared), commands
matching these same shapes ran without prompting:
- `ls -la /Users/dan/.claude/hooks/` — clean
- `grep -n "ensure_.*_hook" /Users/dan/code/dotfiles/update_claude_permissions.py` — clean
- Many cp/ls/grep with absolute paths during the use_uv_run_python and
  block_bash_chains hook implementation work — all clean

So the behavior **changed mid-session**. Exact transition point not
pinpointed; might correlate with the midnight UTC roll detected by the
system-reminder date change.

## Pattern in the data

Commands with **no path arguments and no shell operators** pass clean.
Anything with file paths or pipes prompts.

Three things could produce this pattern:
1. Matcher now splits commands on path tokens / shell operators and
   checks each segment, where additional segments aren't matched by
   any allow rule.
2. A separate write/read path-permission domain (not the Bash allow
   rules) is now gating Bash commands that touch paths. The `Read(...)`
   and `Write(...)` allow rules cover the relevant paths, but maybe
   only for the Read/Edit/Write *tools*, not for Bash commands.
3. A hook is returning `permissionDecision: "ask"` on commands with
   paths/operators. Less likely given the audited hooks; only
   `commit-author.js` is unaudited.

## Remaining hypotheses, ranked

1. **Claude Code self-updated mid-session and changed matcher behavior.**
   Most likely. Easy to verify: compare `claude --version` against
   what was running before. If a version changed, that's almost
   certainly it. Symptom shape (path-touching commands prompt, pure
   commands don't) suggests a new path-permission gate for Bash.
2. **`commit-author.js` is the misbehaving hook.** Less likely because
   that hook is supposedly git-only, but it's the one I didn't audit.
   A fresh session that disables that hook would isolate it.
3. **Midnight UTC token/auth state went stale.** Speculative — no
   mechanism I can name.

## Fresh-session test plan

In order; stop as soon as a step gives a clear answer.

1. `claude --version` — record. Compare to whatever version was
   running before this session if you can find it (the api_budget
   hook's invocation log might capture it indirectly).
2. `cp /tmp/cp_perm_diag.html /tmp/cp_perm_diag_dest2.html` — does
   this prompt in a fresh session?
   - **Doesn't prompt** → it was session-level state (cache, token,
     or hook process leak). No further investigation needed; the
     restart fixed it.
   - **Still prompts** → it's a real matcher change. Continue.
3. Run `ls -la /tmp/cp_perm_diag.html` — does ls-with-path prompt?
4. If still prompting: try disabling hooks one at a time (move them
   out of `~/.claude/hooks/` temporarily) to identify whether any
   hook is the source.
5. If hooks aren't the source: this is an upstream Claude Code change.
   File an issue at anthropics/claude-code with this writeup as the
   reproducer.

## Fresh-session update (2026-05-26, ~18:10 UTC)

A fresh Claude Code session was started to execute the test plan above.
The fixture files at `/tmp/cp_perm_diag.html` (and the others listed in
the cleanup section below) are still in place and have not yet been
removed — they remain useful for the next round of testing.

### Regression reproduces across restart

`ls -la /tmp/cp_perm_diag.html` (single absolute path, simpler than the
ls-with-multiple-paths case from the prior empirical table) prompted in
the fresh session. This **kills hypothesis 3** from the original
ranking (midnight-UTC token staleness) — the regression survives a
process restart, so it isn't session-level state.

Claude Code version observed: **2.1.144**. No prior-version anchor was
available to compare against in this session; the `api_budget` hook's
invocation log was not inspected.

### Documentation findings — and a corrected mis-claim

Fetched the official permissions docs at
https://code.claude.com/docs/en/permissions (Configure permissions
page). Two findings that change the analysis materially:

1. **`ls` is documented as unconditionally read-only.** Quoting:
   > "Claude Code recognizes a built-in set of Bash commands as
   > read-only and runs them without a permission prompt in every mode.
   > These include `ls`, `cat`, `echo`, `pwd`, `head`, `tail`, `grep`,
   > `find`, `wc`, `which`, `diff`, `stat`, `du`, `cd`, and read-only
   > forms of `git`."

   `ls -la /tmp/X` prompting on 2.1.144 is therefore a direct
   violation of documented behavior — not a missing config rule. Per
   the docs no allow rule, no `additionalDirectories` entry, and no
   mode change should be required to make `ls` run silently.

2. **`additionalDirectories` is documented as a file-access mechanism
   for the Read/Edit/Write tools, not a Bash gate in default mode.**
   The only documented interaction with Bash is in `acceptEdits` mode,
   where it scopes which filesystem-modifying commands (`mkdir`,
   `touch`, `mv`, `cp`, etc.) auto-accept. In default mode (which is
   what's running), the docs do not describe `additionalDirectories`
   as gating Bash commands at all.

**Corrected mis-claim:** earlier in this fresh session, before reading
the docs, I (the agent) had asserted that "Claude Code recently
extended `additionalDirectories` enforcement to Bash" as a confident
explanation for the symptom. I had no source for that claim — I built
a narrative that fit the data and presented it as a finding. The docs
lookup falsified the framing. Recording this so the durable note
doesn't propagate the confusion: the symptom is **not** explained by
the documented behavior of `additionalDirectories`.

### Hypothesis test applied (pending verification on next restart)

Per Dan's call: even though the docs don't support
`additionalDirectories` as a Bash gate, the configuration change is
cheap, and the implementation may diverge from the docs. The test is
to add the relevant paths and see whether prompts change.

Change applied to `update_claude_permissions.py` `ADDITIONAL_DIRECTORIES`
list, then script run in reset mode:

```python
ADDITIONAL_DIRECTORIES = [
    "/Users/dan/.nori/profiles",
    "/Users/dan/code",            # broadened from /Users/dan/code/ebtn
    "/Users/dan/data",
    "/Users/dan/.claude/skills",
    "/tmp",                       # added
]
```

Backup of prior settings.json at `~/.claude/settings.20260526_142854.bak`.

**Verification requires another fresh session** — Claude Code reads
settings.json at startup. Predicted outcomes:

- **`ls -la /tmp/X` still prompts** → `additionalDirectories` isn't
  what's gating Bash in default mode (consistent with docs). The bug
  is elsewhere in the matcher. Next step is hook isolation (test plan
  step 4) or an upstream issue.
- **`cp` prompts go away, `ls` still prompts** → implementation may
  consult `additionalDirectories` for write-capable Bash commands in
  default mode (undocumented), while still violating the
  read-only-commands list for `ls`. Two upstream issues to file.
- **Everything stops prompting** → implementation gates *all*
  path-touching Bash on `additionalDirectories` in default mode,
  contradicting the docs. File as docs-vs-implementation gap.

### Updated hypothesis ranking

1. **Bash matcher in Claude Code 2.1.144 diverges from the documented
   read-only-commands behavior.** Most defensible reading given the
   new evidence: `ls` of an absolute path should never prompt per
   docs, and does. (Previously listed as hypothesis 1, but with the
   wrong mechanism — `additionalDirectories` extension to Bash — now
   removed.)
2. **`commit-author.js` is the misbehaving hook.** Lower-ranked but
   not ruled out. A hook returning `permissionDecision: "ask"` could
   produce ask-prompts, but the symptom pattern (every path-touching
   Bash, including `ls`) is more parsimoniously explained by a matcher
   bug. To isolate: temporarily disable the hook in
   `~/.claude/settings.json` and re-test.
3. ~~Midnight UTC token staleness.~~ **Killed** by fresh-session
   reproduction.

### Cross-machine notes

- All testing on `Dans-MacBook-Air`. Behavior on `Dans-MacBook-Pro`
  and `tarragon` unknown — same Claude Code version may or may not
  be installed.
- The `update_claude_permissions.py` edit propagates via dotfiles
  auto-sync; once committed and pulled on the other machines,
  they'll get the same `additionalDirectories` baseline.
- Side effect of the edit: `/Users/dan/code/ebtn` was replaced by
  the broader `/Users/dan/code`. Strict superset; nothing that
  worked under `ebtn` should regress.

## Second fresh-session probe results (2026-05-26 ~19:10 UTC, Claude Code 2.1.150)

A second fresh-session test was run after Claude Code self-updated from
2.1.144 → 2.1.150. The `additionalDirectories` baseline from the prior
hypothesis test was still in place at session start.

### Setup state at probe time

- Claude Code version: **2.1.150** (up from 2.1.144 in prior fresh
  session; the version delta is independent of the deliberate config
  change and is itself a candidate fix per Dan).
- `additionalDirectories` in `~/.claude/settings.json`:
  `['/Users/dan/.nori/profiles', '/Users/dan/code', '/Users/dan/data',
   '/Users/dan/.claude/skills', '/tmp']` — matches what the prior
  session's hypothesis test installed.
- Test fixtures from prior session still present at
  `/tmp/cp_perm_diag.html` et al. (verified via `Read` before probing,
  to avoid muddying the `ls` signal).
- Working from `/Users/dan/code/dotfiles` on `main`, in sync with
  `origin/main` at `48d2589`.

### Probe results

| Command | 2.1.144 (prior session) | 2.1.150 (this session) |
|---|---|---|
| `ls -la /tmp/cp_perm_diag.html` | prompted | **clean** |
| `cp /tmp/cp_perm_diag.html /tmp/cp_perm_diag_dest3.html` | prompted | **clean** |
| `cp /tmp/cp_perm_diag.html /Users/dan/code/dotfiles/cp_perm_diag_v2.html` | prompted | **clean** |
| `ls -la /tmp/cp_perm_diag.html /Users/dan/code/dotfiles/cp_perm_diag.html` | prompted | **clean** |

**Binary signal flipped: the regression no longer reproduces.**

### What this evidence supports — and where it stops

What it supports: the state we're currently in (Claude Code 2.1.150 +
broadened `additionalDirectories`) does not exhibit the bug. Documented
behavior for `ls` (built-in read-only Bash, never prompts) is restored.

Where it stops: two levers changed simultaneously between the prior
fresh session and this one — version and config. We can't disentangle
them from this probe alone. The decision-tree outcomes in the
"Fresh-session update" section above were written for the case where
only `additionalDirectories` changed; with version moving too, all
three predicted outcomes collapse into "everything stops prompting"
without telling us which lever did the work.

### Updated hypothesis ranking

1. **2.1.144 had a matcher bug that 2.1.150 fixed.** Most parsimonious
   explanation given the symptom pattern (every path-touching Bash,
   including documented-as-never-prompts `ls`, was prompting). Promoted
   from "candidate" to "leading" but not confirmed without isolation.
2. **`additionalDirectories` extension was the operative fix.** Would
   imply Claude Code's Bash gate actually consults `additionalDirectories`
   in default mode despite the docs. Possible but less consistent with
   the `ls` symptom (which shouldn't be gated at all per docs).
3. **Both contributed** (e.g. `ls` fixed by 2.1.150, `cp` quieted by
   `additionalDirectories`). Compatible with the data; only the
   isolation test can distinguish from (1) alone.
4. **`commit-author.js` hook.** Still formally alive but increasingly
   improbable; the version-correlated timing of fix-after-update is
   more suggestive of an upstream bug than a hook misfire.
5. ~~Midnight UTC token staleness.~~ Killed by the prior fresh-session
   reproduction (still recorded for posterity).

### Deferred: isolation via revert + restart

Per Dan's call 2026-05-26 — no functional pressure to disentangle right
now; the system works. The cleanest follow-up to distinguish hypotheses
1 vs. 2 (when motivation arises):

1. Revert `ADDITIONAL_DIRECTORIES` in `update_claude_permissions.py`
   to its pre-fix state (remove `/tmp`, restore `/Users/dan/code/ebtn`
   instead of broadened `/Users/dan/code`).
2. Run the script (reset mode) to write `settings.json` with the old
   config.
3. Restart Claude Code (settings read at startup).
4. Re-run the four-probe matrix above. Test fixtures should still be in
   place — see cleanup section below; do **not** clean them up until
   the isolation test runs.

Predicted outcomes:
- **Probes still clean** → 2.1.150 fixed the bug; the
  `additionalDirectories` extension was harmless overprovisioning.
  Decide whether to keep it as belt-and-suspenders or revert.
- **Probes prompt again** → `additionalDirectories` was the operative
  fix and the bug persists in 2.1.150, just gated by config. File an
  upstream issue (docs say `additionalDirectories` doesn't gate Bash in
  default mode) and keep the config.
- **Mixed (e.g. cp clean, ls prompts)** → both levers contribute;
  documented behavior for read-only Bash is still violated even in
  2.1.150 when `additionalDirectories` is narrow. File upstream.

Pick this up if the regression reappears or if anyone needs to know
which lever does the work for cross-machine setup (the
`additionalDirectories` change propagates via dotfiles auto-sync; the
version delta does not).

## Cleanup commands for the fresh session

**Updated 2026-05-26 (later) — defer the cleanup until the deferred
isolation test runs**, since those fixtures are reused for the same
probe matrix. Two new fixtures were added during the second probe
session (`/tmp/cp_perm_diag_dest3.html` and
`/Users/dan/code/dotfiles/cp_perm_diag_v2.html`). Full inventory:

```
rm /tmp/cp_perm_diag.html
rm /tmp/cp_perm_diag_dest.html
rm /tmp/cp_perm_diag_dest3.html
rm /Users/dan/code/dotfiles/cp_perm_diag.html
rm /Users/dan/code/dotfiles/cp_perm_diag_dest_in_repo.html
rm /Users/dan/code/dotfiles/cp_perm_diag_v2.html
rm /Users/dan/code/lobby_analysis/.worktrees/wi-disclosure-explore/tests/fixtures/wi/cp_perm_diag.html
```

(Run as separate Bash calls; `block_bash_chains` will hard-fail
chained rm commands.)

## What the session DID accomplish before the regression

Shipped 2026-05-25/26 in this session, all committed and pushed:

- `claude-hooks/use_uv_run_python.py` + tests + symlink + settings.json
  registration. Hard-fails `.venv/bin/python(3)` invocations. Commit
  `fd418d1`.
- VS Code workspace files for canary + websites. Commit `5840d3e`.
- Branch-creation / archiving discipline added to
  `nori-researcher/CLAUDE.md` (ships to researcher-profile users) and
  to dotfiles `CLAUDE.md`. STATUS.md migrated to (Work-line, Branch,
  Status, Summary) schema with retrofitted rows for the previously-
  footnoted `merged, pending archive` branches. Commit `eb196b1`.
- Parallel session also shipped `block_bash_chains.py` + companion
  notes/docs. Commit `0fa4f55`.
