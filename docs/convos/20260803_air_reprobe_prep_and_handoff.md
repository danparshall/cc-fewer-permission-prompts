# 20260803_air_reprobe_prep_and_handoff

**Date:** 2026-08-03
**Branch:** main (work-line: `chain-hook-maintenance`, main-direct)
**Machine:** Dans-MacBook-Air  <!-- which machine ran this session; commit author carries a matching tag via ~/.gitconfig.local -->

## Summary

Short Air-side prep session. Dan opened with "run the HITL matcher re-probe per `docs/active/chain-hook-maintenance/probes/TEST_PLAN.md` (59 days stale, threshold 30), then bump `MATCHER_LAST_VERIFIED`." Nori pre-flight ran clean (`main` synced to `65ce270`; 22 fired reminders surfaced from `danparshall/dotfiles` — Dan chose to defer triage and stay on the reprobe task). Read STATUS.md, README.md, TEST_PLAN.md, METHODOLOGY.md, and enough of FINDINGS.md to understand the current Family-3 six-node landscape.

Two blockers surfaced before firing any HITL probe. **(1)** `probes/.claude/settings.json` was missing allow rules for the min-viable set: test 17 (`diff <(echo a) <(echo b)`) needs `Bash(diff *)`, test 20 (`find /Users/dan -maxdepth 1 -name .bashrc`) needs `Bash(find *)`, and speculative S2 needs `Bash(grep *)`. Fix: added all three (commit `bb82999`). **(2)** Dan pushed back mid-session — he was on the Air but wanted to actually drive the paste-and-report loop on Pro where he has dual monitors. So Air's role converted from "run the probe" to "prep + hand off to Pro."

Wrote the handoff runbook (`probes/REPROBE_2026-08-03.md`, commit `281fa10`) — self-contained enough that a fresh Pro session Claude can pick it up from cold: Why-now (staleness numbers), Pre-flight (confirm Air commit landed, capture `claude --version` and `hostname`), Protocol (Mode B `--setting-sources project`), the 8 min-viable rows with expected outcomes and family labels, Interpretation (all-8-match → bump; any deviation → full FINDINGS entry), Post-probe steps (bump `MATCHER_LAST_VERIFIED`, clear expired `MATCHER_NAG_SNOOZE_UNTIL = "2026-07-25"` → `None`, run test trio, write FINDINGS entry, commit + push), and a drift-found branch. Dan initially asked "what should I ask from Pro?" — was going to hand him a paste-ready prompt; corrected when he flagged the cross-machine copy-paste constraint, and shifted the answer to "commit the runbook doc so Pro just needs the one-line invocation."

Finished with `finish-convo`. Between drafting the runbook and this convo, Pro session picked up the handoff — the reprobe first aborted at row 1 (the runbook's expectations assumed user-level `additionalDirectories` trust that `--setting-sources project` strips), then completed cleanly on a v2 runsheet with three corrections (path-scope fix, row-14 heredoc-open-line correction, deny-canary load-proof). 8/8 no drift, `MATCHER_LAST_VERIFIED` bumped to 2026-08-03 in commit `4bbcc17` (Pro/Fable session). So Air's tiny contribution to today's work was the settings.json additions and the runbook — corrected mid-flight by Pro's execution.

## Topics Explored

- `MATCHER_LAST_VERIFIED` staleness accounting (59 days vs. 30-day threshold; snooze expired 9 days ago)
- Missing allow rules for TEST_PLAN.md min-viable set (tests 17, 20 needed diff+find; grep added for speculative S2)
- Handoff format — paste-ready prompt (Dan can't copy-paste cross-machine) vs. committed runbook doc (Pro pulls, reads, executes)
- Runbook structure for a fresh Pro-session Claude — Why-now, Pre-flight, Protocol pointer, 8-row test set with expected outcomes, drift interpretation, post-probe steps in both branches

## Provisional Findings

- The Air-side handoff runbook's ALLOW expectations for rows 1/3 were **wrong** — assumed user-level `additionalDirectories: ["/tmp"]` would carry through `--setting-sources project`, but that flag strips user-level trusted roots. Pro's aborted-then-completed run surfaced this. The June 2026 loop-reenable probe (only prior Mode B pass) happened to use only cwd-agnostic commands, so this trap had always existed but never been hit.
- The runbook's row 14 command (`python3 <<'PY'` … `PY 2>&1`) was **shell-malformed** — a redirect on the heredoc terminator line is body text, not shell syntax; parses as no redirect and correctly ALLOWs. Corrected shape (`python3 <<'PY' 2>&1` … `PY`) puts the redirect on the open line and produces the expected Family-3 `file_redirect` prompt. Pro fixed this in TEST_PLAN.md + the runbook itself.
- Pro's completed run also confirmed 8/8 no drift on CC **2.1.220** — the model established across June 2026 (CC 2.1.165 era) and the 2026-07-28 process_substitution finding still holds under the current runtime.

## Decisions Made

- **Hand off actual probe execution to Pro** — Dan's decision to drive HITL from the dual-monitor machine rather than the Air laptop; Air's role capped at prep + runbook authoring.
- **Commit the runbook rather than paste a prompt** — Dan can't cross-machine copy-paste, so the runbook lives in the repo and Pro's invocation becomes a one-line "run the reprobe per REPROBE_2026-08-03.md" reference.
- **Speculative S2 rule added preemptively** — `Bash(grep *)` included in the settings.json commit even though the min-viable set doesn't need it, so a follow-up S2 run wouldn't need another commit + pull cycle.

## Results

- `docs/active/chain-hook-maintenance/probes/.claude/settings.json` — added `Bash(diff *)`, `Bash(find *)`, `Bash(grep *)` (commit `bb82999`)
- `docs/active/chain-hook-maintenance/probes/REPROBE_2026-08-03.md` — handoff runbook v1 (commit `281fa10`); superseded intra-day by Pro's v2 corrections (path-scope, row 14, deny-canary) captured in the top-of-doc "EXECUTED" banner

## Open Questions

- None from Air's slice — Pro's completed run resolved all the day's drift/re-probe questions. Cross-reference the FINDINGS "2026-08-03 (later)" entry for the authoritative record. Task-remind fired items still deferred (all 22 dated reminders remain for a future triage session).
