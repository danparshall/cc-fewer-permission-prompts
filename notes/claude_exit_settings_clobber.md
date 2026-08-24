# Custom SessionStart/PreToolUse hooks get clobbered by nori-skillsets

**Status:** clobber discovered 2026-05-13 · **fix corrected 2026-05-21** —
the original "put it in `settings.local.json`" fix in this note was
wrong and was a regression; the operative fix is the
`update_claude_permissions.py` self-heal. History preserved below.
· **claude-exit itself retired 2026-07-25** (`018a95a`, "claude-exit:
remove from active install") — Anthropic shipped a built-in exit
affordance, making the bespoke tool redundant. The clobber-then-heal
mechanism still applies to the surviving custom hooks (block_cd_git,
enforce_pr_discipline, api_budget, use_uv_run_python, the chain hooks,
and claude-iso when its symlink exists). Per-machine disable procedure
for the SessionStart hook that remains on already-installed machines:
see "Update 2026-08-03" at the bottom.

## TL;DR

1. `nori-skillsets` treats the `hooks` section of `~/.claude/settings.json`
   as a section **it owns** and re-emits it from its own template on
   `sks switch`. Any non-Nori hook there (claude-exit, `block_cd_git`,
   `enforce_pr_discipline`, `api_budget`, …) gets dropped.
2. **The fix is NOT `~/.claude/settings.local.json`.** Claude Code does
   not read a user-level `settings.local.json` — only the *per-project*
   `<repo>/.claude/settings.local.json`. A file at
   `~/.claude/settings.local.json` is inert; hooks placed there never
   fire. (The earlier version of this note claimed Claude Code "merges
   hooks across `settings.json` + `settings.local.json`" — that claim
   was never actually verified and is false at the user level.)
3. **The operative fix is the `update_claude_permissions.py` self-heal.**
   That script has `ensure_block_cd_git_hook()`, `ensure_enforce_pr_discipline_hook()`,
   `ensure_api_budget_hook()`, `ensure_claude_iso_hook()`, and the
   chain-family hooks — each idempotently *merges* its entry back into
   `settings.json`'s `hooks` structure (merge, don't clobber). `install.sh`
   runs the script (and `pclaude` runs it before each session), so
   `settings.json` is repaired after every `sks switch`. (Historically
   this list also included `ensure_claude_exit_hook()`; removed 2026-07-25
   in `018a95a` when claude-exit was retired — see "Update 2026-08-03"
   at the bottom.)
4. **To add a new user-level hook:** write an `ensure_<name>_hook()` in
   `update_claude_permissions.py` and call it from `main()`. Never
   `settings.local.json`.

## Diagnosis (still valid)

The clobber itself is real. Discovered 2026-05-13 when the claude-exit
verification ceremony stopped auto-running. Investigation found the hook
script on disk and a valid MCP registration, but no entry pointing at it
in `settings.json`.

Backup diff narrowed the strip-event:

```
settings.20260507_151211.bak  (May 7)   — claude-exit hook present
settings.20260508_061042.bak  (May 8)   — present
settings.20260508_084503.bak  (May 8)   — GONE (nori added "description" fields to its 2 hooks)
settings.20260508_120458.bak  (May 8+)  — still gone
```

The diff between the 06:10 and 08:45 backups is exactly: (a) nori added
two `description` fields to its hooks, (b) the claude-exit entry dropped.
The rewriter re-emitted `SessionStart` from its template instead of
merging. This recurs whenever nori updates that section's template, and
again on every `sks switch`.

## The wrong turn (2026-05-13 → 2026-05-17)

- 2026-05-13: this note was first written. It proposed putting the hook
  in `~/.claude/settings.local.json` and asserted Claude Code merges
  hooks across both files. That assertion was never tested — the note's
  "verification" only confirmed the *hook script* runs when invoked
  directly, not that Claude Code *reads the file*.
- 2026-05-15: the `hook_require_finish_convo` work got it right —
  `update_claude_permissions.py` gained `ensure_*_hook()` functions that
  re-apply hook entries to `settings.json` on every run. This is the
  correct, durable mechanism.
- 2026-05-17: a session hit issue #19 (`sks switch --force` stomping the
  hooks), first correctly restored them to `settings.json`, then —
  trusting *this note* — decided `settings.json` was "the wrong file"
  and migrated the entries to `~/.claude/settings.local.json`. That was
  a regression: it moved working hooks into a file Claude Code ignores.
  The self-heal script silently overwrote the regression by re-inserting
  the entries into `settings.json` on subsequent runs, so nothing broke
  in practice — but `~/.claude/settings.local.json` was left behind as
  an inert, misleading duplicate.

## The actual fix

Hooks live in `~/.claude/settings.json`. `update_claude_permissions.py`
owns them via `ensure_*_hook()` and repairs the file after any nori
clobber. `install.sh` invokes the script. The mechanism is already in
place for `block_cd_git`, `enforce_pr_discipline`, `api_budget`, the
chain hooks, `use_uv_run_python`, and `claude-iso` (claude-exit was
retired 2026-07-25); any new user-level hook follows the same pattern.

If you find a stray `~/.claude/settings.local.json`, it is the 2026-05-17
regression artifact — safe to delete (Claude Code never reads it).

## Residual risk (issue #19)

Between an `sks switch` and the next `update_claude_permissions.py` run,
`settings.json` is missing the custom hooks. In practice `pclaude` runs
the script before each session, so the window is narrow — but a session
started by other means immediately after a switch could miss them.
Issue #19 tracks whether the self-heal fully closes this gap.

## See also

- `update_claude_permissions.py` — `ensure_claude_iso_hook()` is now the
  canonical exemplar (`ensure_claude_exit_hook()` was removed in
  `018a95a`, 2026-07-25). Siblings that still ship: `ensure_block_cd_git_hook`,
  `ensure_enforce_pr_discipline_hook` (renamed from `require_finish_convo`
  2026-08-04), `ensure_api_budget_hook`, `ensure_use_uv_run_python_hook`,
  plus the chain-family hooks.
- The claude-exit README's "Auto-running the ceremony at session start"
  section documents the `settings.json` install path — correct.
- Sibling notes: `cd_git_hardcoded.md`, `bash_loop_permissions.md` —
  same shape (debug a quiet config-layer failure, document, leave a
  tripwire for future-me).

## Update 2026-08-03 — claude-exit retired; per-machine disable procedure

claude-exit was retired dotfiles-side on 2026-07-25 (`018a95a`,
"claude-exit: remove from active install"). Motivation: Anthropic shipped
a built-in exit affordance for Claude Code, making the bespoke tool
redundant. The overhead being reclaimed is the SessionStart ceremony
(~2.5k-char context injection + 5-step spawn/kill on every session);
the tool's presence on disk costs nothing.

### What `018a95a` did (dotfiles-side; propagates via `install.sh`)

- `update_claude_permissions.py`: removed the four `mcp__claude-exit__*`
  ALLOW_RULES, `CLAUDE_EXIT_HOOK_COMMAND` / `_DESC`,
  `ensure_claude_exit_hook()`, and its call site in `main()`.
- `install.sh`: removed the claude-exit repo pull, the hook-symlink
  creation, and the `uv tool upgrade claude-exit` step.
- Tests: removed `TestEnsureClaudeExitHook`.

### What each machine still needs, once

The dotfiles-side changes flip the *default* — `install.sh` will no
longer install or re-heal claude-exit. But an already-installed
SessionStart hook in `~/.claude/settings.json` on a given machine is not
removed by `install.sh`; it sits there, firing on every session, until
stripped by hand.

Per-machine disable (do once, per machine):

1. Strip the SessionStart block from `~/.claude/settings.json` whose
   command is `$HOME/.claude/hooks/claude-exit-session-start.sh`.
2. (Optional) `rm ~/.claude/hooks/claude-exit-session-start.sh` — the
   symlink becomes dead weight after step 1; harmless if left.

Since `ensure_claude_exit_hook()` no longer exists, the strip is
**durable**: the next `sks switch` clobber + `install.sh` self-heal
cycle re-adds only currently-supported hooks — claude-exit isn't among
them, so it stays gone.

### What can safely be left in place (per Dan, 2026-08-03)

- MCP server registration in `~/.claude.json` — fine to keep; low cost.
- The `claude-exit guard` binary.
- `uv tool install claude-exit` — the CLI itself (useful for
  `claude-exit log` review if any unacknowledged invocations remain).
- Any tombstone file an earlier revocation attempt may have written.

Only the SessionStart hook is the "big waste"; everything else can stay.

### Machine status (as of 2026-08-03)

- **Air** (`Dans-MacBook-Air`): SessionStart hook already absent from
  `~/.claude/settings.json` — grep for `claude.exit` in the live file
  returns no matches. Effectively disabled.
- **Pro** (`Dans-MacBook-Pro`): SessionStart hook stripped 2026-08-03
  during the sync-dance session (step 1 only; symlink at
  `~/.claude/hooks/claude-exit-session-start.sh` left as harmless dead
  weight per Dan). Grep for `claude.exit` in `~/.claude/settings.json`
  now returns no matches. Effectively disabled.
- **tarragon**: unknown; check when next online. The commit's own
  message flagged Pro + tarragon explicitly as machines the
  dotfiles-side change couldn't reach.
