# cc-fewer-permission-prompts

[![tests](https://github.com/danparshall/cc-fewer-permission-prompts/actions/workflows/tests.yml/badge.svg)](https://github.com/danparshall/cc-fewer-permission-prompts/actions/workflows/tests.yml)

**Verified against Claude Code 2.1.220** (2026-08-03 drift check, 8/8 rows unchanged — [`docs/FINDINGS.md`](docs/FINDINGS.md), newest entry on top). Matcher behavior drifts on version bumps; see [When to distrust this](#when-to-distrust-this).

Fewer Claude Code permission prompts **without** `--dangerously-skip-permissions`.

## What this is

Claude Code's permission matcher prompts you on more than "commands with no allow rule." It also has a family of hard-coded heuristics — anti-obfuscation scans, path-scope checks, and static-analysis bails on shell syntax it can't bound (`&&` chains with an unlisted verb, heredoc + pipe, brace expansion, loops with a `$var` in the body, …). **No allow rule overrides those.** They fire on ordinary, well-formed commands the agent reaches for constantly, and every prompt is a tax: you approve the same shape dozens of times a session, and if you run sessions in parallel, each prompt serializes one of them.

This repo turns the ones that have a *clean, already-known alternative* into a **hard fail before the matcher** — a `PreToolUse` hook that denies the command and tells the agent exactly which alternative to use instead (`git -C <path>` instead of `cd <path> && git`, separate tool calls instead of a chain, write-a-script-then-run instead of `python3 -c "…"`). The agent reformulates on the spot; you never see the prompt. Friction moves from you to the agent, which is where the already-documented correct behavior says it belongs.

Alongside the hooks, the repo carries the **evidence** they rest on: a probe methodology, a version-scoped record of what the matcher actually does, and the strategy framework for deciding when a prompt deserves a hook, an allow rule, or nothing.

## Quick install (agent-driven)

The intended install path is to hand this repo to your Claude Code and ask it to do the work:

```
git clone https://github.com/danparshall/cc-fewer-permission-prompts.git
cd cc-fewer-permission-prompts
claude
> Install the hooks from this repo into my Claude Code config.
```

What the agent should do (and what you'd do by hand):

1. **Copy the hooks** into `~/.claude/hooks/` and make them executable:
   ```
   mkdir -p ~/.claude/hooks
   cp hooks/*.py ~/.claude/hooks/
   chmod +x ~/.claude/hooks/*.py
   ```
   `hooks/_blanket_verbs.py` must come along — `block_bash_chains.py` imports it at startup (and read the [caveat](#_blanket_verbspy-is-a-snapshot-of-someone-elses-allow-list) below before you rely on it). The test files (`hooks/test_*.py`) are for CI; copying them is harmless but unnecessary.

   A hook without the executable bit **fails silently** — Claude Code logs nothing, the hook just never runs (`docs/FINDINGS.md`, 2026-05-31). If a hook seems inert, check `chmod` first.

2. **Register one `PreToolUse` entry per hook** in `~/.claude/settings.json`, matcher `Bash`. Order doesn't matter — Claude Code runs every matching hook, and the chain hook deliberately stands down on `cd … && git …` so the cd/git hook's more specific message is the one the agent sees:
   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Bash",
           "hooks": [
             { "type": "command", "command": "$HOME/.claude/hooks/block_cd_git.py" },
             { "type": "command", "command": "$HOME/.claude/hooks/block_bash_chains.py" },
             { "type": "command", "command": "$HOME/.claude/hooks/block_brace_quote_heredoc.py" },
             { "type": "command", "command": "$HOME/.claude/hooks/block_newline_hash_in_quoted_arg.py" },
             { "type": "command", "command": "$HOME/.claude/hooks/block_heredoc_with_pipe_or_redirect.py" },
             { "type": "command", "command": "$HOME/.claude/hooks/block_loop_with_pipe.py" },
             { "type": "command", "command": "$HOME/.claude/hooks/block_brace_expansion.py" },
             { "type": "command", "command": "$HOME/.claude/hooks/block_absolute_path_py_verb.py" }
           ]
         }
       ]
     }
   }
   ```
   If you already have a `PreToolUse` block, merge into it rather than replacing it.

3. **Restart the session.** Hooks are read at session start.

Each hook's module docstring (top of the `.py` file) explains what it blocks, why the matcher prompts on that shape, and the clean alternative it redirects to. The docstrings are the spec — ask your agent to summarize them if you want to opt out of specific hooks before installing.

**`hooks/optional/` is opt-in.** Two hooks there are workflow preferences, not prompt-reducers: `enforce_pr_discipline.py` (gates `gh pr create` on a clean tree + a committed session note, for a specific research workflow) and `use_uv_run_python.py` (hard-fails `.venv/bin/python` in favor of `uv run python`). Install them only if you want that behavior; nothing else depends on them.

## Starter `permissions` block

The hooks only pay off in proportion to the allow-list they sit on top of. `block_bash_chains.py` denies a chain and tells the agent to split it into separate tool calls — but the split-out calls run silently **only because each verb has a blanket allow rule**. With an empty allow-list you'd trade one chain prompt for three single-command prompts.

So start from something like this in `~/.claude/settings.json` (trim to taste; this is the shape the hooks were developed against, generalized). Substitute your own absolute paths where marked — `Bash(...)` rules are literal globs on the command string, so `~` is not expanded for you.

```json
{
  "permissions": {
    "additionalDirectories": ["/tmp"],
    "allow": [
      "Bash(git *)",
      "Bash(git worktree add *)",
      "Bash(cd /ABS/PATH/TO/your/code *)",
      "Bash(cd /ABS/PATH/TO/your/code/*)",
      "Bash(cd /tmp *)",
      "Bash(ls *)", "Bash(cat *)", "Bash(head *)", "Bash(tail *)",
      "Bash(grep *)", "Bash(find *)", "Bash(sed *)", "Bash(awk *)",
      "Bash(echo *)", "Bash(pwd *)", "Bash(which *)", "Bash(env *)",
      "Bash(wc *)", "Bash(sort *)", "Bash(uniq *)", "Bash(diff *)", "Bash(cut *)",
      "Bash(mkdir *)", "Bash(cp *)", "Bash(mv *)", "Bash(touch *)", "Bash(chmod *)",
      "Bash(rm /ABS/PATH/TO/your/code *)", "Bash(rm -r /ABS/PATH/TO/your/code *)",
      "Bash(rm /tmp *)", "Bash(rm -r /tmp *)",
      "Bash(python *)", "Bash(python3 *)", "Bash(uv *)", "Bash(uvx *)", "Bash(pytest *)",
      "Bash(node *)", "Bash(npm *)", "Bash(npx *)",
      "Bash(gh *)", "Bash(jq *)",
      "Bash(ps *)", "Bash(kill *)",
      "Bash(PYTHONPATH=*)",
      "Read(//ABS/PATH/TO/your/code/**)",
      "Read(//tmp/**)",
      "Edit(//ABS/PATH/TO/your/code/**)",
      "Edit(//tmp/**)"
    ],
    "deny": [
      "Bash(git clean *)", "Bash(git clean)",
      "Bash(git add -A *)", "Bash(git add . *)", "Bash(git add .)",
      "Bash(git push --force *)", "Bash(git push -f *)",
      "Bash(git reset --hard *)", "Bash(git branch -D *)",
      "Bash(git checkout .)", "Bash(git checkout -- .)", "Bash(git restore .)",
      "Bash(rm -rf / *)", "Bash(rm -rf ~ *)",
      "Bash(*find * -delete*)", "Bash(*-exec * rm *)",
      "Bash(*eval *)",
      "Bash(*--dangerously-skip-permissions*)", "Bash(*bypassPermissions*)",
      "Bash(cd * && git *)"
    ],
    "ask": [
      "Bash(git stash drop *)", "Bash(git stash clear *)",
      "Bash(ssh *)", "Bash(scp *)", "Bash(rsync *)",
      "Bash(brew *)"
    ]
  }
}
```

Three things in there that aren't obvious:

- **`additionalDirectories: ["/tmp"]`** — the matcher's path-scope check preempts verb allow rules. `touch /tmp/x` prompts even with `Bash(touch *)` allowed unless `/tmp` is a trusted root (`docs/FINDINGS.md`, 2026-08-03, "Family 2"). Write-then-run (below) depends on `/tmp` being writable without a prompt.
- **`Bash(git worktree add *)`** next to `Bash(git *)` — Claude Code has a hard-coded git-plus-filesystem-creation heuristic that prompts on `worktree add` even under a blanket git rule.
- **The deny list is a safety net, not the mechanism.** `Bash(cd * && git *)` is denied here *and* hard-failed by `block_cd_git.py` — settings-level denies survive a hook being broken (Python missing, lost x-bit), and the hook gives a far better message than the canned one.

## What the hooks do

Every hook reads the Bash tool's JSON on stdin, matches a regex against `tool_input.command`, and — when it fires — prints a `hookSpecificOutput` object with `permissionDecision: "deny"` and a `permissionDecisionReason` that names the alternative. The agent sees the reason and retries with it. Otherwise the hook exits silently. Nothing here calls out to a network or a model.

| Hook | Shape it hard-fails | Why the matcher prompts on it | Do this instead |
|---|---|---|---|
| `block_cd_git.py` | `cd <path> && git <subcmd>` | Hard-coded bare-repo-attack heuristic; deny rules and allow rules don't override it | `git -C <path> <subcmd>` |
| `block_bash_chains.py` | `a && b`, `a \|\| b`, `a; b` where any segment's leading verb lacks a blanket allow rule | The matcher checks chains per segment; one unlisted verb prompts the whole chain | Separate tool calls — cwd persists across them; check the first call's result for if-then semantics. All-blanket chains still pass |
| `block_brace_quote_heredoc.py` | `{"k":"v"}` / `['a','b']` inside a heredoc body | Anti-obfuscation heuristic: brace immediately followed by a quote, in any bash-unquoted context | Write the code to a file, run the file ("Write-then-run") |
| `block_newline_hash_in_quoted_arg.py` | A newline followed by `#` inside a quoted argument (a Python comment in `python3 -c "…"`) | Anti-obfuscation heuristic ("can hide arguments from path validation") | Write-then-run |
| `block_heredoc_with_pipe_or_redirect.py` | `cmd <<'EOF' … EOF 2>&1 \| grep x` — a heredoc *and* a pipe/redirect on the same open line | Static-analysis bail ("file_redirect / pipeline cannot be statically analyzed"); either alone is fine, the pair isn't | Write-then-run — the file-based command may keep its `2>&1 \| grep` tail |
| `block_loop_with_pipe.py` | `for/while/until … do … done` with a pipe or a `$variable` in the body | The matcher body-analyzes loops and bails on anything it can't bound; nearly every useful loop uses its variable | A short Python script, unrolled separate calls, or a wait-until-condition monitor tool. Static loops (no pipe, no `$var`) still run |
| `block_brace_expansion.py` | `mv /p/{a,b}.txt /dest/`, `{1..5}` | Static-analysis bail ("Brace expansion") — verb-agnostic, even `ls` | Enumerate: one call per expanded path, or a common-prefix glob |
| `block_absolute_path_py_verb.py` | `./script.py args`, `/abs/path/x.py` as the leading verb | Plain allow-rule miss — the verb is the path, not `python3`. Chosen as a hook (not a path allow rule) to train the interpreter-leading form | `python3 ./script.py args` |
| *optional* `enforce_pr_discipline.py` | `gh pr create` on a dirty tree, or before the session's note is committed | Not a matcher issue — a workflow gate | Commit the session note, then retry |
| *optional* `use_uv_run_python.py` | `.venv/bin/python …` | No allow rule matches the path form | `uv run python …` |

**Write-then-run** is the recurring alternative: put the code in a file with the Write tool (`Write(//tmp/**)` is allowed above), then run `python3 /tmp/script.py`. The bash command becomes trivial, the code never sits inside a quoted argument, and no anti-obfuscation scan applies. [`docs/STRATEGIES.md`](docs/STRATEGIES.md) has the full catalog of shapes and their alternatives, and the decision tree for *whether* a prompt deserves a hook (Strategy 2), an allow rule (Strategy 1), or nothing (Strategy 0). The gate for a hook is a conjunction: the shape is **frequent** *and* it has a **clean alternative**. Either half alone is not a hook.

### `block_bash_chains.py` and your code directory

The chain hook lets `cd <dir> && <cmd>` through when `<dir>` is under one of your code roots, because the matcher does too. It auto-detects `$HOME/{code,work,src,dev,projects}` (whichever exist). If your code lives elsewhere, set `CC_HOOK_CD_ALLOWED_PREFIXES` to a colon-separated list of absolute prefixes in the environment Claude Code runs in.

### `_blanket_verbs.py` is a snapshot of someone else's allow-list

This is a **behavioral** caveat, not just provenance. `hooks/_blanket_verbs.py` is generated upstream from the author's `Bash(<verb> *)` allow rules; `block_bash_chains.py` uses it to decide whether a chain is "all-blanket" (let the matcher see it — it will pass) or "mixed" (hard-fail). So out of the box, the hook's pass/deny boundary reflects *the author's* allow-list, not yours:

- A verb in the set that you **haven't** allowed → the hook lets the chain through, the matcher prompts anyway (a prompt leaks past the hook).
- A verb you allow that **isn't** in the set → the hook denies a chain your matcher would have accepted (extra friction, no prompt).

Neither is dangerous — the hook never *grants* anything — but the point of the hook is accuracy at that boundary. **Edit `BLANKET_VERBS` to match your own allow rules**: one entry per verb that has a blanket `Bash(<verb> *)` rule, plus the matcher's built-in always-allowed verbs (`date`, `hostname` as far as we've observed). Upstream the file is regenerated from the author's allow-list on every install; in your copy there is no generator, and the module docstring says the same.

## How the corpus is maintained

The matcher is closed-source and Anthropic changes it without notice — the first durable note in this repo was partly wrong five days after it was written. So the hooks are backed by an explicit evidence loop rather than a belief:

- **Probes.** [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) describes two human-in-the-loop probe modes (the matcher's allow/prompt decision is visible only to the human, so every probe needs someone driving approvals) and the conventions that make results attributable. [`docs/probes/`](docs/probes/) holds the runnable plan (`TEST_PLAN.md`), a self-contained `.claude/settings.json` for clean-room sessions (`claude --setting-sources project` from that directory), and every past runbook and results file — including the failed runs, which are where the pre-flight discipline came from.
- **Load-proof canary.** The probe settings carry a `Bash(rev *)` deny rule so the first row of any probe (`rev .claude/settings.json` → auto-DENY) proves the settings file actually loaded. Two earlier sessions drew wrong conclusions because a prompt on the sanity row was ambiguous between "settings never loaded" and "path outside trusted roots."
- **Version-scoped record.** [`docs/FINDINGS.md`](docs/FINDINGS.md) is append-only, newest on top; each entry names the Claude Code version it was observed on, the methodology, the raw results, the interpretation, and the impact on each hook. Matcher behavior is a property of the CC binary, so a finding transfers to any machine on the same version and goes stale on a version bump.
- **Snapshots.** [`notes/`](notes/) are the dated standalone write-ups that preceded the corpus — kept as historical snapshots; where they've been superseded, `FINDINGS.md` says so.
- [`docs/CORPUS.md`](docs/CORPUS.md) is the corpus's own README: the thesis, the file map, the workflow.

## When to distrust this

Compare your `claude --version` with the version at the top of this file. Same version: the findings apply. Newer version: every hook still *works* (they're regex on a command string) but the matcher may have changed on the other side — a shape we hard-fail might now pass, or a new shape might prompt. The cost of a stale hook is a rewrite the agent didn't need; the cost of a missing one is a prompt you didn't expect.

To find out what *your* version does: `cd docs/probes && claude --setting-sources project`, run the pre-flight (canary first), then the minimum-viable rows in `TEST_PLAN.md` (about ten minutes of y/n). Compare against the newest `FINDINGS.md` entry. Deviations are findings — see Contributing.

## Contributing

- **An unexpected prompt.** Paste the exact command, your Claude Code version, and what you expected into an issue, or add an entry to [`docs/INCOMING.md`](docs/INCOMING.md) in the format shown there. [`agents/chain-matcher-curator.md`](agents/chain-matcher-curator.md) is a Claude Code subagent definition that does the triage — copy it into `.claude/agents/` in a checkout of this repo, then hand it the command.
- **A probe result.** A dated `FINDINGS.md`-style entry (version, methodology, results, interpretation, hook impact, confidence) is the most useful thing you can send.
- **How publishing works, so a PR lands where it can stick.** `docs/`, `hooks/`, `notes/`, and `agents/` are exported automatically from the author's private configuration repo; each publish commit carries a `Source: dotfiles@<sha>` trailer and **replaces those four directories wholesale**. A PR that edits files there will be overwritten on the next publish — open an issue with the change instead and it'll be applied upstream. `README.md`, `LICENSE`, and `.github/` are authored here and are safe to PR directly.

## License

MIT — see [`LICENSE`](LICENSE).
