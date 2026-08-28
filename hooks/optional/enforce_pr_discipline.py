#!/usr/bin/env python3
"""PreToolUse hook: enforce researcher-workflow PR discipline.

Gates `gh pr create` on research branches so a PR can't be opened until
the current convo is committed and the working tree is clean. Two
conditions must both hold or the call is denied:

1. Working tree is clean (no modified, staged, or untracked files per
   `git status --porcelain`).
2. The most recent commit on the current branch touches a file under
   docs/active/<branch>/convos/ — i.e., the last thing committed was
   the convo doc, not work code.

Together these guarantee: every line of code about to be presented for
merge is also narratively checkpointed in the convo for this branch.
Clean alternative when denied: run `/finish-convo` to checkpoint the
session (commits the convo doc alongside any other research state),
then retry `gh pr create`.

Engages only on branches that have been set up as research lines —
specifically, branches with a `docs/active/<branch>/` directory in the
repo. No-ops in code-only repos or on branches that don't follow the
research-workflow convention.

Renamed 2026-08-04 from `require_finish_convo.py` — the new name names
the goal (PR discipline) rather than the mechanism (finish-convo
checkpoint). Behavior unchanged.
"""
import json
import os
import re
import subprocess
import sys

# Match `gh pr create` at start-of-command or after a shell operator
# (`;`, `&&`, `||`, `|`). Avoids false positives where the literal
# string appears inside a quoted argument (e.g. an echoed JSON payload).
#
# Known gap: subshell forms like `$(gh pr create ...)` or backtick-
# substitution won't match. Capturing output of `gh pr create` is rare
# in real workflows, so we accept the gap rather than add `(` to the
# operator class (which would re-introduce quoted-substring false
# positives — `echo "$(gh pr create)"` etc.).
GH_PR_CREATE_RE = re.compile(r"(?:^|[;&|]+\s*)gh\s+pr\s+create\b")


def run(cmd: list[str], cwd: str) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def deny(reason: str) -> None:
    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(response))
    sys.exit(0)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if not GH_PR_CREATE_RE.search(command):
        sys.exit(0)

    cwd = payload.get("cwd") or os.getcwd()

    # Confirm we're in a git repo
    rc, _ = run(["git", "rev-parse", "--git-dir"], cwd)
    if rc != 0:
        sys.exit(0)

    rc, repo_root = run(["git", "rev-parse", "--show-toplevel"], cwd)
    if rc != 0:
        sys.exit(0)

    rc, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if rc != 0 or not branch:
        sys.exit(0)

    # Gate only engages on branches set up as research lines, signalled
    # by the existence of docs/active/<branch>/. A bare docs/active/ at
    # the repo root isn't sufficient — dotfiles and other repos can have
    # one for reasons unrelated to this workflow.
    if not os.path.isdir(os.path.join(repo_root, "docs", "active", branch)):
        sys.exit(0)

    convos_path = f"docs/active/{branch}/convos/"

    # Condition 1: working tree clean
    rc, porcelain = run(["git", "status", "--porcelain"], cwd)
    if rc != 0:
        sys.exit(0)
    if porcelain:
        deny(
            f"Blocked: working tree is not clean. Uncommitted changes:\n"
            f"{porcelain}\n\n"
            f"Run /finish-convo to checkpoint the session (it will commit "
            f"the convo doc along with any other research state), then retry."
        )

    # Condition 2: latest commit touches a convo doc on this branch.
    # Uses `--name-only` so rename detection emits the new path only —
    # `--name-status` would format renames as `R\told -> new` and break
    # the startswith() check below.
    rc, files = run(
        ["git", "log", "-1", "--name-only", "--pretty=format:"], cwd
    )
    if rc != 0:
        sys.exit(0)
    touched_convo = any(
        f.startswith(convos_path) for f in files.splitlines() if f.strip()
    )
    if not touched_convo:
        deny(
            f"Blocked: latest commit on `{branch}` does not touch "
            f"`{convos_path}`. Work has been committed after (or instead "
            f"of) the convo checkpoint, so the convo is stale relative to "
            f"the branch state.\n\n"
            f"Run /finish-convo to refresh the convo doc, then retry."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
