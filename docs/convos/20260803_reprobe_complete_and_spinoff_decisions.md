# Reprobe complete (8/8 no drift) + open-source spinoff decisions

**Date:** 2026-08-03
**Branch:** main (main-direct work-line: `chain-hook-maintenance`)
**Machine:** Dans-MacBook-Pro

## Summary

Completed the 30-day matcher drift check that the same-day Opus session aborted at the
sanity row. The technical record is in `FINDINGS.md` "2026-08-03 (later)" (authoritative)
and the STATUS.md session entry — this convo doc doesn't duplicate it. Headline: 8/8
min-viable rows match the June-era/2026-07-28 model on CC 2.1.220; no drift; all hooks
re-justified; `MATCHER_LAST_VERIFIED` bumped to 2026-08-03. Two harness defects were found
and fixed en route (no-proof-of-settings-load → deny-canary technique; malformed TEST_PLAN
rows 14/15), and the aborted session's three open findings were all resolved (path-scope
CONFIRMED; sandbox non-interfering across the pass; `claude --help` anomaly = narrow CC
self-special-case).

The session then pivoted (Dan mid-session) to **prepping the corpus for an open-source
spinoff**: sensitivity sweep, README Portability section + newcomer quickstart, and a
sequencing decision on issue #68. This doc's main job is to carry the spinoff design state
to the next session, since that discussion is otherwise recorded only partially (issue #68
comment covers sequencing, not the design leans).

## Topics Explored

- Probe run (see FINDINGS): Phase-A load-proof design, 8-row pass, D-row anomaly matrix
- Spinoff-prep: sensitivity sweep of the work-line docs (result: nothing hot; two
  borderline items), README portability framing
- Issue #68 (TEST_PLAN reorg): status audit + resequencing into the spinoff
- Spinoff design space: scope, source-of-truth, history handling (discussion only — no
  plan doc yet)

## Decisions Made

- **Dan: open-source the corpus as a standalone repo BEFORE 2026-08-17** (issue #68's
  fire date). #68's reorg becomes the new repo's first work item, in the new repo's
  layout; the fire date is now a backstop deadline for the split. Recorded in
  [#68 comment](https://github.com/danparshall/dotfiles/issues/68#issuecomment-5170482270).
- Sandbox probe strategy: deviation-triggered (Dan's pick), now METHODOLOGY default.
- Deny-canary + `additionalDirectories: ["/tmp"]` retained as standing probe harness.
- Borderline sensitive strings (`.env.<CLIENT>` filename, `<private-project>` repo name in
  historical FINDINGS/INCOMING entries) left intact for record fidelity — Dan to set the
  redaction threshold at copy time. (METHODOLOGY guidance prose was genericized where the
  name carried no information.)

## Open Questions (the spinoff design set — next session starts here)

Claude's leans were stated in-session; none are decided except the timeline:

1. **Scope:** corpus-only vs corpus + `reference-hooks/`. Claude's lean: ship corpus +
   hooks-as-reference-implementations now ("these encode one user's policy; adapt, don't
   install"), park hook parameterization as the new repo's issue #2 — the repo's value is
   the empirical record and method, not packaging.
2. **Source of truth afterward:** Claude's lean: corpus (FINDINGS/METHODOLOGY/INCOMING/
   STRATEGIES/probes) moves upstream to the new repo; dotfiles' `chain-hook-maintenance/`
   becomes a thin consumer (hooks + installer stay in dotfiles; curator agent + INCOMING
   capture redirect to the new repo's local checkout). Avoids public/private drift.
3. **History:** fresh repo (copy, no git history) vs `git filter-repo` extraction.
   Claude's strong lean: fresh — it's the natural sensitivity boundary, docs are
   internally dated, and filter-repo on a busy mixed repo is high-risk/low-reward.
4. **Name** (unpicked; candidates not yet brainstormed), **license** (MIT floated,
   undecided), **redaction calls** (item above) at copy time.
5. **Reorg specifics** absorbed into #68's comment: Phase-A pre-flight as numbered rows;
   drift-check subset as a standing paste-ready runsheet (hand-copying runbooks is how
   the row-14 defect propagated); a home for built-in special cases (`claude --help`
   self-case, per-command analyzer, cd+git heuristic — "Family 4: built-ins"?); old→new
   row-number mapping table so historical FINDINGS references stay resolvable.

**Recommended next step (per Dan's workflow):** brainstorming skill → `write-a-plan` →
plan doc in `docs/active/chain-hook-maintenance/plans/` referencing this convo → fresh
agent executes the split.

## Results

- No results/ files — technical outputs live in FINDINGS.md ("2026-08-03 (later)" entry),
  probes/TEST_PLAN.md (corrected rows), probes/REPROBE_2026-08-03.md (execution banner),
  probes/.claude/settings.json (standing harness). All committed in `4bbcc17`.
