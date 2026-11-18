# 20261110_claude_path_vscode_xfer_env_prompts

**Date:** 2026-11-10 (ran into 2026-11-11 UTC)
**Branch:** main (work-line is main-direct)
**Surface:** claude-code
**Machine:** Dans-MacBook-Air (air)
**Session:** Dan (air, dotfiles, 20261110T2239, opus-5.5) · /Users/dan/.claude/projects/-Users-dan-code-dotfiles/60b56e93-4243-46b7-83d9-4fd0c64822a1.jsonl · —

## Summary

Dan pasted four permission prompts from other live sessions (autograntor-replication and verification), one at a time, and asked why each fired. Each was triaged against the allow list in `~/.claude/settings.json` and the existing FINDINGS record. Two were tested with in-session probes under Dan's deny-and-paste HITL convention.

1. **`cp ~/.claude/skills/init-research-repo/templates/history_seed.md.tmpl …`** prompted as an "edit" of a "sensitive file", even though every relevant allow rule was present. The probes showed that any `~/.claude/` path in a Bash command prompts, even as `cp`'s read-only source; the symlink into dotfiles is not the trigger. Fixed by rewording `init-research-repo` and `init-paper-collection` to seed with Read + Write instead of `cp`, and by adding a habits bullet to the CLAUDE-PERMISSIONS block. Along the way, my first explanation overstated the scope; Dan's pushback ("smells like bullshit") led to the probes that pinned it down.
2. **`vscode <workspace>`**: plain allow-rule miss. `vscode` is a zsh alias; the matcher sees the unexpanded word. Added `Bash(vscode *)`.
3. **`ls … ~/xfer/envs …`**: path scope, since `~/xfer` is outside the trusted folders. Dan's question ("shouldn't the skill point at the readable location?") surfaced a real bug in `sync-repo-data` Step 2: it re-seeded from the old Aug-10 store whenever `~/xfer/envs/` existed, which would `cp -a` stale env files over newer store copies. Step 2 now runs only when `~/data/_envs/` is missing or empty.
4. **`TARGETED_OUT=… uv run python …`**: an unlisted `VAR=val` prefix breaks verb-anchored allow rules. The probes showed that `env VAR=val cmd` runs silently, but that it also gets a denied `git clean -n` past its DENY rule. Given Dan's threat model (habit-catching, not deliberate evasion), this was recorded only. Dan is returning to auto mode for now.

## Topics Explored

- Claude Code's protected `~/.claude/` path check vs. allow rules
- How the matcher treats shell aliases and leading env assignments
- Path scope for reads outside `additionalDirectories`
- Whether `env` wrapping bypasses deny rules
- Where the template source should live (dotfiles source vs. the `claude_researcher` build artifact): stays dotfiles, per `notes/profile_skill_export.md`

## Provisional Findings

- Any `~/.claude/` path in a Bash command prompts, regardless of allow rules or symlinks; `cp`'s source is treated as a write target (the mechanism is inferred from prompt wording). FINDINGS 2026-11-10.
- `env VAR=val cmd` bypasses both allow-rule anchoring and at least one deny rule. FINDINGS 2026-11-11.
- The HITL denial convention was already written in METHODOLOGY.md, but scoped to probe sessions; I stopped after the first rejected probe. METHODOLOGY now says it applies in any session running an approved probe.

## Decisions Made

- Init skills seed templates with Read + Write, never `cp` (`51ca982`).
- `Bash(vscode *)` allowed (`bc078eb`).
- `sync-repo-data` seeds only into an empty store (`5293e3c`).
- Env-wrapper deny gap: known, low priority, no hook, no plan (Dan). The "use `env VAR=val`" habit-line change was considered and not made; side effects recorded in FINDINGS 2026-11-11.
- Logs: `b66e43f` (FINDINGS 2026-11-10 + METHODOLOGY), `28aabc8` (FINDINGS 2026-11-11).

## Results

- None saved separately; the probe tables live in FINDINGS.md (2026-11-10 and 2026-11-11 entries).

## Open Questions

- `notes/repo_data_env_sync.md` says the Air migration hasn't run, but `~/data/_envs/` has held 13 repos since Nov 3. Stale note, or Pro seeded it? Dan to say.
- Does a read-only verb (`cat`, `ls`) on a `~/.claude/` path also prompt? Untested.
- Does the env-wrapper bypass extend to other DENY entries and to the env-prefix allow rules (`Bash(PATH=*)`)? Inferred, untested.
