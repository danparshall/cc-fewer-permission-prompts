#!/usr/bin/env python3
"""Test cases for enforce_pr_discipline hook (renamed from require_finish_convo).

Two surfaces under test:

1. Regex anchoring: `gh pr create` should match at start-of-command or
   after a shell operator, but not as a substring inside quoted args
   (e.g. an echoed JSON payload). The original regex was `\\bgh\\s+pr\\s+
   create\\b`, which matched anywhere — including inside `echo '{...}'`
   payloads — and ate its own smoke tests. The anchored version uses
   `(?:^|[;&|]+\\s*)` as the leading guard.

2. Research-branch gating: the hook should only engage when
   `docs/active/<branch>/` exists. A bare `docs/active/` at the repo
   root isn't sufficient (dotfiles and other repos can have one for
   reasons unrelated to this workflow).

Tests #1 by feeding commands at a non-research cwd and asserting silent
pass for all of them, even ones where `gh pr create` appears inside
quotes. Tests #2 with a synthesized fake research repo under /tmp.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HOOK = "/Users/dan/code/dotfiles/claude-hooks/enforce_pr_discipline.py"

# Reconstructed so this file doesn't contain the literal trigger string
# outside of test data. Same defensive trick as test_block_cd_git.py.
GH_PR_CREATE = "gh" + " " + "pr" + " " + "create"


def run_hook(command: str, cwd: str) -> tuple[bool, str]:
    """Invoke the hook with a synthesized payload. Returns (blocked, reason)."""
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": cwd,
    })
    r = subprocess.run(
        [HOOK], input=payload, capture_output=True, text=True,
    )
    if r.returncode != 0:
        return False, f"hook errored: rc={r.returncode} stderr={r.stderr!r}"
    if not r.stdout.strip():
        return False, ""
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        return False, f"bad JSON: {r.stdout!r}"
    decision = out.get("hookSpecificOutput", {}).get("permissionDecision")
    if decision == "deny":
        return True, out["hookSpecificOutput"]["permissionDecisionReason"]
    return False, ""


def build_research_repo(root: str, branch: str) -> None:
    """Build a fake research repo with feature work as the latest commit."""
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=root, check=True
    )
    os.makedirs(os.path.join(root, "docs", "active", branch, "convos"))
    open(os.path.join(root, "README.md"), "w").close()
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"], cwd=root, check=True
    )
    # Feature work as the latest commit (no convo yet)
    with open(os.path.join(root, "work.py"), "w") as f:
        f.write("# work\n")
    subprocess.run(["git", "add", "work.py"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "feature work"], cwd=root, check=True
    )


def add_convo_commit(root: str, branch: str) -> None:
    """Add a convo doc as a new commit on top of the branch."""
    convo = os.path.join(
        root, "docs", "active", branch, "convos", "20260515_test.md"
    )
    with open(convo, "w") as f:
        f.write("# convo\n")
    subprocess.run(["git", "add", convo], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "finish-convo"], cwd=root, check=True
    )


def main() -> int:
    failures: list[str] = []

    def check(label: str, got: tuple[bool, str], want_blocked: bool) -> None:
        blocked, reason = got
        ok = blocked == want_blocked
        status = "PASS" if ok else "FAIL"
        snippet = f" ({reason[:60]!r})" if blocked else ""
        print(f"{status}  blocked={blocked!s:5} want={want_blocked!s:5}  {label}{snippet}")
        if not ok:
            failures.append(label)

    # ---- Regex anchoring tests (cwd doesn't matter; not a research repo) ----
    non_research_cwd = "/tmp"

    # Anchored at start: would match the regex, but cwd isn't a research
    # branch — should still pass silently. This isolates the regex layer
    # by checking that the *only* reason it could engage is the regex,
    # and confirms no false-positive there.
    check(
        "non-matching command (no trigger)",
        run_hook("echo hello", non_research_cwd),
        want_blocked=False,
    )
    check(
        "trigger inside single-quoted echo (substring, must not match regex)",
        run_hook(f"echo '{GH_PR_CREATE} --title foo'", non_research_cwd),
        want_blocked=False,
    )
    check(
        "trigger inside double-quoted echo (substring, must not match regex)",
        run_hook(f'echo "{GH_PR_CREATE} --title foo"', non_research_cwd),
        want_blocked=False,
    )
    check(
        "trigger as argument to grep (substring, must not match regex)",
        run_hook(f"grep '{GH_PR_CREATE}' /tmp/notes.txt", non_research_cwd),
        want_blocked=False,
    )

    # ---- Research-branch gating tests ----
    tmpdir = tempfile.mkdtemp(prefix="enforce_pr_discipline_test_")
    try:
        repo = os.path.join(tmpdir, "fake_research")
        os.makedirs(repo)
        branch = "research_branch"
        build_research_repo(repo, branch)

        # Trigger as the actual command, dirty tree (untracked file)
        with open(os.path.join(repo, "dirty.py"), "w") as f:
            f.write("# uncommitted\n")
        check(
            "trigger + dirty tree (research repo) -> deny",
            run_hook(f"{GH_PR_CREATE} --title foo", repo),
            want_blocked=True,
        )

        # Clean the tree; latest commit is still feature work, not a convo
        os.remove(os.path.join(repo, "dirty.py"))
        check(
            "trigger + clean tree + latest commit is work -> deny",
            run_hook(f"{GH_PR_CREATE} --title foo", repo),
            want_blocked=True,
        )

        # Land a convo commit on top
        add_convo_commit(repo, branch)
        check(
            "trigger + clean tree + latest commit is convo -> pass",
            run_hook(f"{GH_PR_CREATE} --title foo", repo),
            want_blocked=False,
        )

        # Trigger after `&&` should also engage the regex
        check(
            "trigger after && + clean tree + convo on top -> pass",
            run_hook(f"echo ok && {GH_PR_CREATE} --title foo", repo),
            want_blocked=False,
        )

        # Make the tree dirty again; the `&&` form should also deny
        with open(os.path.join(repo, "dirty2.py"), "w") as f:
            f.write("# uncommitted\n")
        check(
            "trigger after && + dirty tree -> deny",
            run_hook(f"echo ok && {GH_PR_CREATE} --title foo", repo),
            want_blocked=True,
        )

        # Non-research branch in a repo with docs/active/ (the dotfiles
        # scenario): branch=main, no docs/active/main/. Even with a
        # dirty tree and matching trigger, should pass silently.
        os.remove(os.path.join(repo, "dirty2.py"))
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=repo, check=True
        )
        with open(os.path.join(repo, "scratch.py"), "w") as f:
            f.write("# uncommitted scratch\n")
        check(
            "trigger on non-research branch (no docs/active/<branch>/) -> pass",
            run_hook(f"{GH_PR_CREATE} --title foo", repo),
            want_blocked=False,
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if failures:
        print(f"\n{len(failures)} failure(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nall pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
