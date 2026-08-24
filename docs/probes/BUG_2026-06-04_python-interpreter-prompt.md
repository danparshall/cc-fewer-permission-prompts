# Bug: permission matcher prompts for `ls <python-interpreter>` despite `Bash(ls *)` allow rule

**For filing at:** https://github.com/anthropics/claude-code/issues

**Date drafted:** 2026-06-04
**Claude Code version:** 2.1.150
**OS:** macOS 15.7.4 (Apple Silicon)

---

## Summary

Bare `ls <path>` (and other read-class verbs like `head`) prompt for permission whenever `<path>` is a **real, on-disk Python interpreter** — e.g. `/usr/bin/python3` or `<project>/.venv/bin/python` — despite `Bash(ls *)` being an explicit allow rule in `settings.json`, and despite the target being inside `additionalDirectories`.

The matcher appears to be inspecting the target file's metadata or contents pre-execution and overriding the explicit allow rule. No diagnostic surfaces in the prompt UI indicating *why* the matcher overrode the rule.

## Minimal repro

`~/.claude/settings.json` contains (relevant excerpt):

```json
{
  "permissions": {
    "allow": ["Bash(ls *)"],
    "additionalDirectories": ["/Users/<user>/code", "/tmp"]
  }
}
```

In any Claude Code session, run:

```
ls /usr/bin/python3
```

**Expected:** silently allowed (matches `Bash(ls *)`).
**Actual:** permission prompt fires.

## Probe table (full discriminator pass, 2026-06-04)

cwd for all probes: `/Users/<user>/code/dotfiles`. Target paths under `/Users/<user>/code/lobby_analysis/` are cross-project from the session's perspective.

| # | Command | Target exists? | Result | Purpose |
|---|---|---|---|---|
| 1 | `ls ~/code/lobby_analysis/.worktrees/wi-tier1-direct-read/.venv/bin/python` | yes (real interp) | **PROMPT** | original in-the-wild trigger |
| 2 | same + `2>&1` | yes | **PROMPT** | original observed shape |
| 3 | same + `2>/dev/null` | yes | **PROMPT** | rules out `2>&1` specifically |
| 4 | `ls ~/code/lobby_analysis/.venv/bin/python 2>&1` | yes | **PROMPT** | one dotdir variant (no `.worktrees/`) |
| 5 | `ls /tmp/x 2>&1` | yes (empty) | silent | redirect outside `~/code` |
| 6 | `ls ~/code/lobby_analysis/Makefile` | no | silent | top-level neighbor, no python |
| 7 | `ls /tmp/.hidden_probe/y` | yes (empty) | silent | dotdir under `/tmp` |
| 8 | `ls ~/code/dotfiles/CLAUDE.md` | yes | silent | in-cwd-project, no python |
| 9 | `ls ~/code/dotfiles/.git/HEAD` | yes | silent | dotdir in cwd-project |
| 10 | `head -n 1 ~/code/lobby_analysis/.worktrees/.../.venv/bin/python` | yes (real interp) | **PROMPT** | verb-agnostic: `head` also prompts |
| 11 | `cat /tmp/.hidden_probe/y` | yes | silent | cross-verb `/tmp` dotdir |
| 12 | `ls ~/code/lobby_analysis/.git/HEAD` | yes | silent | cross-project `.git/HEAD` is silent |
| 13 | `ls ~/code/lobby_analysis/.venv` | yes (dir) | silent | terminal `.venv` dir |
| 14 | `ls ~/code/lobby_analysis/.venv/pyvenv.cfg` | yes | silent | `.venv/` config file |
| 15 | `ls ~/code/lobby_analysis/.git/config` | yes | silent | `.git/` config file |
| 16 | `ls ~/code/lobby_analysis/.venv/bin/activate` | yes (mode 644, no +x) | silent | same `bin/` dir, non-interpreter |
| 17 | `ls ~/code/lobby_analysis/.venv/bin/pip` | no | silent | python-adjacent name, fake path |
| 18 | `ls /usr/bin/python3` | yes (real interp) | **PROMPT** | system python outside `~/code` |
| 19 | `ls /usr/bin/ls` | no (Mac has `/bin/ls`) | silent | `/usr` scope control |
| 20 | `ls ~/data/foo/bin/python` | no | silent | additionalDir + python, fake path |
| 21 | `ls ~/test/foo/bin/python` | no | silent | non-additionalDir + python, fake path |
| 24 | `ls /tmp/fake_pyhome/bin/python` (0-byte) | yes (0 bytes, mode 644) | silent | basename match alone, no `+x` |
| 25 | same after `chmod +x` (0-byte, +x) | yes (0 bytes, +x) | silent | basename + `+x` alone |

The six promptees (1, 2, 3, 4, 10, 18) all share one feature: the final path component resolves to a **real Python interpreter executable**. Every other probe — including paths with the *same string-level features* but no real interpreter at the target — is silent.

## What this rules out

The probe matrix rules out simpler explanations that we initially hypothesized:

- **Not the redirect operator.** PROBE 1 prompts with no redirect at all. PROBE 5 has the same `2>&1` against a different path and is silent. PROBE 3 uses `2>/dev/null` (no `&`) and still prompts.
- **Not the project boundary.** PROBE 12 reads `.git/HEAD` in a cross-project repo and is silent.
- **Not hidden-directory components in the path.** PROBES 9, 12, 13, 14, 15 all involve `.git/` or `.venv/` and are silent.
- **Not `ls`-specific.** PROBE 10 uses `head` against the same path and also prompts.
- **Not a basename string match alone.** PROBES 20 and 21 target `bin/python` paths that don't exist and are silent.
- **Not a basename match + file-exists.** PROBE 24 creates a 0-byte file literally named `python` at a `bin/`-shaped path and `ls` is silent.
- **Not a basename match + file-exists + `+x`.** PROBE 25 adds the executable bit and `ls` is still silent.
- **Not `additionalDirectories` scope.** PROBE 18 prompts on `/usr/bin/python3`, which is *not* under any `additionalDirectories` member; PROBE 19 (`/usr/bin/ls`, also out of scope) is silent. So `/usr` being out-of-scope is not what flipped PROBE 18.

The only hypothesis consistent with every row is that the matcher inspects the target file's metadata or contents (`stat`, `realpath`, magic-byte sniffing, or similar) before applying the allow rule, and treats "the file at this path is a real Python interpreter" as a reason to override `Bash(ls *)`.

## Impact

1. **Surprising prompts in routine workflows.** `ls /usr/bin/python3`, `head <venv>/bin/python`, and similar inspections — all completely standard developer operations — prompt for permission, with no diagnostic explaining why.
2. **Explicit allow rules don't mean what they say.** Users who add `Bash(ls *)` reasonably expect any `ls` invocation to be allowed. A silent override based on undocumented file-inspection heuristics is hard to discover, hard to debug, and hard to work around.
3. **No diagnostic surface.** The permission prompt UI does not explain which heuristic fired. Users see a generic "permission needed" and have to guess.
4. **Threat model unclear.** If the intent is to prevent inadvertent execution of a foreign Python binary, blocking `ls` and `head` is a strange place to enforce that — neither verb executes the target file.

## Hypothesis (for the maintainer's benefit, not required to triage)

Pre-execution pipeline reads the target file's metadata or content, recognizes "this is a real Python interpreter" (probably via Mach-O magic bytes, shebang inspection, or `realpath` against a known-interpreter list), and routes the call through a stricter permission decision that ignores `Bash(ls *)`. We didn't pin down which of those signals (magic bytes vs. shebang vs. realpath) is the actual discriminator — the next probe in that direction would be making `/tmp/symtest/bin/python` a symlink to `/usr/bin/python3` and `ls`ing it.

## Suggested resolution shapes

In rough priority order:

1. **Honor explicit allow rules.** `Bash(ls *)` should match any `ls`. If a file-inspection heuristic exists, it should not silently override the user's explicit grants.
2. **Surface the diagnostic.** If a heuristic does override, the prompt should say *which* heuristic and *why* — e.g., "blocked: target path is a Python interpreter; the matcher overrides `Bash(ls *)` for interpreter paths." Users can then decide whether to add a narrower rule or report the override as a bug.
3. **Document the heuristic.** Whatever the heuristic is, it should be documented in the public permission-rules reference.
4. **Scope the heuristic to actually-risky verbs.** Reading an interpreter (`ls`, `head`, `cat`) is not the same as executing it. If the threat is execution, the heuristic should target execution verbs, not read verbs.

## Environment

- Claude Code: `2.1.150 (Claude Code)`
- OS: macOS 15.7.4 (Build 24G517), Apple Silicon
- Shell: zsh
- `additionalDirectories`: `["/Users/<user>/code", "/Users/<user>/data", "/Users/<user>/.nori/profiles", "/Users/<user>/.claude/skills", "/tmp"]`
- Relevant allow rules present: `Bash(ls *)`, `Read(//Users/<user>/code/**)`, `Read(//tmp/**)`
- No `settings.local.json` overrides relevant to `ls`.

## Original in-the-wild trigger

The probe pass started from a real prompt observed by the user, on this command:

```
ls /Users/<user>/code/lobby_analysis/.worktrees/wi-tier1-direct-read/.venv/bin/python 2>&1
```

(Description shown in the prompt UI: "Check worktree venv exists.")

That command is PROBE 2 in the table above.
