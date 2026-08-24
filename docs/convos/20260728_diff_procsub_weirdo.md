# 20260728_diff_procsub_weirdo

**Date:** 2026-07-28
**Branch:** main (work-line: `chain-hook-maintenance`, main-direct)
**Machine:** Dans-MacBook-Pro  <!-- which machine ran this session; commit author carries a matching tag via ~/.gitconfig.local -->

## Summary

Dan forwarded a permission-prompted command from another session: `diff <(sed 's|{{skills_dir}}|/Users/dan/.claude/skills|g' ~/code/dotfiles/nori-researcher/skills/write-a-plan/SKILL.md) ~/.claude/skills/write-a-plan/SKILL.md`. The chain-matcher-curator agent recorded it in INCOMING.md (commit `545335d`): all eight PreToolUse hooks pass it silently, and `Bash(diff *)` is in the live allow list — so matcher-side, with primary hypothesis a Family-3 static-analysis bail on the `process_substitution` node and a secondary path-scope hypothesis linking to the 2026-07-14 grep entry.

With Dan at the keyboard capturing prompt reason-text, three discriminator probes settled it: control `diff` (cwd-only) silent; plain `diff` against a `~/.claude/skills/` path silent; `diff <(echo a) <(echo b)` **prompted with verbatim reason-text "Contains process_substitution"**. That confirms `process_substitution` as the **sixth known Family-3 bail node** (after `file_redirect`, `pipeline`, `simple_expansion`, `brace_expansion`, `string`), in the bare "Contains \<node\>" format matching `simple_expansion`. The curator triaged the INCOMING entry, annotated the 2026-07-14 grep entry (probe 2 *down-weights* its cwd-tree secondary rather than settling it — `diff` was on that entry's own untested-verbs list), and added the dated FINDINGS.md entry (commit `d55e38b`). Disposition: **Strategy-0** — first procsub sighting, so the deny-hook gate (frequent AND clean-alternative) fails on frequency; the clean alternative (materialize procsub inputs to /tmp, then plain `diff`) is recorded for recurrence, and a `block_process_substitution.py` remedy sketch sits in the entry if it recurs.

Side thread: actually running the diff (hook-friendly, via /tmp) revealed the installed `write-a-plan` is content-current but carries a raw `{{skills_dir}}` placeholder — and installed skills split cleanly by vintage: Jul 6/12 installs (incl. upstream Tilework skills) have **raw** placeholders, while two skills stamped Jul 28 09:49 (`finishing-a-research-branch`, `update-docs`) were **hand-substituted** to absolute paths by a prior session's manual sync. Since upstream skills are raw too, `sks switch` (0.26) demonstrably copies SKILL.md bodies verbatim; only AGENTS.md gets template resolution. Dan ruled sources must keep the variable form; discussion landed on **raw-is-canonical for installed copies too** (churn: next `sks switch` reverts anyway; dogfooding parity: vanilla registry users see raw). Norm + empirical finding written into `nori-researcher/NORI_NOTES.md` (commit `e6ce24f`), including a correction to the "What each command does" line that had claimed blanket template resolution.

## Topics Explored

- Why `diff <(sed …)` prompted despite `Bash(diff *)` allow rule — hook trace, allow-list check, Family-3 hypothesis
- Three-probe HITL discrimination with captured prompt reason-text (first Family-3 row with the node name verbatim from the UI)
- Whether the 2026-07-14 grep entry's path-scope cell is settled by probe 2 (curator: no — only down-weighted)
- `{{skills_dir}}` substitution behavior of `sks switch` 0.26 (verbatim copy for skill bodies; AGENTS.md exception)
- Deny-hook gate applied to procsub (frequency half not met → Strategy-0)

## Provisional Findings

- `process_substitution` is a Family-3 static-analysis bail node — confirmed by single HITL probe with captured reason-text "Contains process_substitution" (high confidence for current matcher; matcher drifts, so dated in FINDINGS.md)
- An `additionalDirectories` path outside cwd did NOT prompt for `diff` — but this only down-weights the Family-2 path-scope hypothesis (diff may simply not be path-scope-checked); grep-against-`/Users/dan/data/…` discriminator remains open
- `sks switch` 0.26 copies SKILL.md bodies verbatim (raw `{{skills_dir}}` survives install); AGENTS.md → CLAUDE.md managed block is the only observed template-resolution path

## Decisions Made

- **Strategy-0 for process_substitution** — logged with remedy sketch; revisit if it recurs (Dan: "we have this logged, so we'll see if it comes up again")
- **Raw `{{skills_dir}}` is canonical in `~/.claude/skills/`** — hand-syncs must copy verbatim, never substitute; norm recorded in NORI_NOTES.md (`e6ce24f`); the two Jul-28-substituted copies left in place (self-correct at next switch)
- No RESEARCH_LOG.md created for this work-line — its README defines FINDINGS.md/INCOMING.md as the dated record; this convo file + STATUS.md one-liner are the session-level index

## Results

- `docs/active/chain-hook-maintenance/INCOMING.md` — procsub entry recorded + triaged; 2026-07-14 grep entry annotated (curator commits `545335d`, `d55e38b`)
- `docs/active/chain-hook-maintenance/FINDINGS.md` — dated entry: sixth Family-3 node, 3-probe matrix, reason-text format note
- `nori-researcher/NORI_NOTES.md` — new "`{{skills_dir}}` stays raw in installed skill bodies" section (`e6ce24f`)

## Open Questions

- Does the Family-2 path-scope inspector cover any verb beyond the known set? (grep discriminator probe still open in the 2026-07-14 entry)
- Will procsub recur often enough to flip Strategy-0 → Strategy-2? (`block_process_substitution.py` sketch ready in INCOMING)
- Does any sks version substitute `{{skills_dir}}` in skill bodies, or is the placeholder purely reader-resolved by convention? (0.31 on the Air unchecked; upstream intent undocumented)
- Session-start housekeeping still pending Dan: Horizon #45 outcome (AI for Science deadline 2026-07-31), `claude-exit log` ack (1 unacknowledged since 2026-07-18), and whether `end_conversation` leaving `permissions.allow` was deliberate (lines up with commit `018a95a`)
