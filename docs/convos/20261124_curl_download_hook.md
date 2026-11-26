# 20261124_curl_download_hook

**Date:** 2026-11-24 (closed 2026-11-26)
**Branch:** main (main-direct work-line)
**Surface:** claude-code
**Machine:** Dans-MacBook-Air
**Session:** Dan (air, dotfiles, 20261124T1624, opus-5.5) · /Users/dan/.claude/projects/-Users-dan-code-dotfiles/5c11737f-0799-4d39-9de2-ee4bbf8643e9.jsonl · —

## Summary

Dan pasted a prompted command from a verification session (`curl -sL -o <scratchpad>/offchip.pdf --create-dirs -w "%{…}" "<google-docs export url>"`) and asked for pre-hooks to stop this class of prompt, which he suspected was an Opus 5.5 habit. The prompt turned out to be a plain allow-rule miss: the bundled `-sL` breaks the literal prefix of `Bash(curl -L -o *.pdf *)`. A transcript survey confirmed the frequency: about 200 curl allow-rule misses a month, with Opus 5.5 the largest source and `-s` the most common flag.

The survey also showed that a deny pointing at the existing PDF rule would only cover about 15% of misses; most are non-PDF downloads, link checks with `-w`, and piped reads, which have no allowed form. I offered three designs (parse-and-allow hook, deny plus widened globs, PDF-only deny). Dan ruled differently: the problem is `-s` itself ("we don't WANT silent failures"), `-L -o` is fine, and a deny with a nastygram is enough because the agent learns the right form from it.

Built `claude-hooks/block_curl_silent.py` with TDD (test-quality review by a subagent added `;`, `||`, `-s`-after-URL, `-Los`/`-sLo` bundle and `--no-silent` cases), wired via `ensure_block_curl_silent_hook`, `install.sh`, and a DENY_DISPLAY line, plus allow rules for the canonical `curl -fL -o` form. Committed `7149631`; installed on the Air.

## Topics Explored

- Why the pasted command prompted (prefix broken by `-sL`; `}"` in `-w` possibly a brace-quote trigger, untested)
- Frequency and shape of curl misses across all Air transcripts
- Whether a deny hook passes the "frequent AND clean alternative" test for each kind of miss
- curl's short-option bundle rule (a value-taking option eats the rest of the bundle), needed to avoid false positives

## Provisional Findings

- Curl misses are rising (133 in Aug to 208 in Nov to the 24th) and Opus 5.5 is the largest source; that supports Dan's model-habit hunch but is not controlled for how much each model was used.
- `-s` is not the main silent-failure source: without `-f`, curl saves a 403/404 page as the destination file and exits 0. Hence `-fL` in the nastygram's canonical form (Dan did not object).
- The hook removes the `-s` habit but not most curl prompts: non-PDF downloads, `-A`, `-w`, and piped reads still prompt after the retry, by design.
- Widening the allow globs (`Bash(curl -L -o * *)`) would also admit upload/data flags through the trailing `*`; the existing `*.pdf` rule already does.

## Decisions Made

- Dan: deny `-s`/`--silent` in curl (bundles included); keep `-L -o` allowed; a deny + nastygram is acceptable even where the retry still prompts.
- Canonical form `curl -fL -o <dest> "<url>"`; allow rules added for `.pdf` destinations and arXiv.
- Hook not added to the public `cc-fewer-permission-prompts` export: that list holds matcher-defense hooks, and this is a habit hook (like `block_pull_on_dirty_tree`, also not exported).
- Implemented inline rather than via write-a-plan + fresh agent: one hook copying an existing pattern.

## Results

- [results/20261124_curl_survey.md](../results/20261124_curl_survey.md) — survey tables, with scripts `20261124_curl_survey.py` and `20261124_curl_buckets.py`
- INCOMING.md Triaged entry 2026-11-24 and STRATEGIES.md item #8
- Commit `7149631` (hook, tests, wiring, allow rules)

## Open Questions

- Fresh-session end-to-end check not done: does a live `curl -s` get the nastygram in the tool result?
- Pro and tarragon need `install.sh`.
- If non-PDF curl prompts become the next complaint: Strategy 1 there is a security call (destination and trailing-flag scope), or a parse-and-allow hook.
- Does the `}"` in a `-w "%{…}"` string trip the brace-quote heuristic on its own? Untested.
