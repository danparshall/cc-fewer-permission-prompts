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
quotes. Tests #2 with a synthesized fake research repo under a temp dir.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).parent / "enforce_pr_discipline.py"

# Reconstructed so this file doesn't contain the literal trigger string
# outside of test data. Same defensive trick as test_block_cd_git.py.
GH_PR_CREATE = "gh" + " " + "pr" + " " + "create"


def run_hook(command: str, cwd: str):
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


def _git(root: str, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True)


def build_research_repo(root: str, branch: str) -> None:
    """Build a fake research repo with feature work as the latest commit."""
    _git(root, "init", "-q", "-b", branch)
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    os.makedirs(os.path.join(root, "docs", "active", branch, "convos"))
    open(os.path.join(root, "README.md"), "w").close()
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "initial")
    # Feature work as the latest commit (no convo yet)
    with open(os.path.join(root, "work.py"), "w") as f:
        f.write("# work\n")
    _git(root, "add", "work.py")
    _git(root, "commit", "-q", "-m", "feature work")


def add_convo_commit(root: str, branch: str) -> None:
    """Add a convo doc as a new commit on top of the branch."""
    convo = os.path.join(
        root, "docs", "active", branch, "convos", "20260515_test.md"
    )
    with open(convo, "w") as f:
        f.write("# convo\n")
    _git(root, "add", convo)
    _git(root, "commit", "-q", "-m", "finish-convo")


def touch(root: str, name: str) -> None:
    with open(os.path.join(root, name), "w") as f:
        f.write("# uncommitted\n")


class TestRegexAnchoring(unittest.TestCase):
    """cwd is not a research repo, so the ONLY way the hook could engage is
    a regex false-positive. Every case must pass silently."""

    NON_RESEARCH_CWD = tempfile.gettempdir()

    def assertPasses(self, command: str) -> None:
        blocked, reason = run_hook(command, self.NON_RESEARCH_CWD)
        self.assertFalse(blocked, f"{command!r} unexpectedly denied: {reason}")

    def test_no_trigger(self):
        self.assertPasses("echo hello")

    def test_trigger_inside_single_quoted_echo(self):
        self.assertPasses(f"echo '{GH_PR_CREATE} --title foo'")

    def test_trigger_inside_double_quoted_echo(self):
        self.assertPasses(f'echo "{GH_PR_CREATE} --title foo"')

    def test_trigger_as_grep_argument(self):
        self.assertPasses(f"grep '{GH_PR_CREATE}' /tmp/notes.txt")


class TestResearchBranchGating(unittest.TestCase):
    """Synthesized research repo: docs/active/<branch>/ exists, so the hook
    engages and its two conditions (clean tree, convo on top) are tested."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="enforce_pr_discipline_test_")
        self.repo = os.path.join(self.tmpdir, "fake_research")
        os.makedirs(self.repo)
        self.branch = "research_branch"
        build_research_repo(self.repo, self.branch)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_dirty_tree_denies(self):
        touch(self.repo, "dirty.py")
        blocked, _ = run_hook(f"{GH_PR_CREATE} --title foo", self.repo)
        self.assertTrue(blocked)

    def test_clean_tree_but_work_commit_on_top_denies(self):
        blocked, _ = run_hook(f"{GH_PR_CREATE} --title foo", self.repo)
        self.assertTrue(blocked)

    def test_clean_tree_with_convo_on_top_passes(self):
        add_convo_commit(self.repo, self.branch)
        blocked, reason = run_hook(f"{GH_PR_CREATE} --title foo", self.repo)
        self.assertFalse(blocked, reason)

    def test_trigger_after_chain_operator_engages(self):
        add_convo_commit(self.repo, self.branch)
        blocked, reason = run_hook(
            f"echo ok && {GH_PR_CREATE} --title foo", self.repo
        )
        self.assertFalse(blocked, reason)

        touch(self.repo, "dirty2.py")
        blocked, _ = run_hook(f"echo ok && {GH_PR_CREATE} --title foo", self.repo)
        self.assertTrue(blocked)

    def test_non_research_branch_in_repo_with_docs_active_passes(self):
        # The dotfiles scenario: repo has docs/active/ but the current
        # branch has no docs/active/<branch>/. Even dirty + matching
        # trigger must pass silently.
        _git(self.repo, "checkout", "-q", "-b", "main")
        touch(self.repo, "scratch.py")
        blocked, reason = run_hook(f"{GH_PR_CREATE} --title foo", self.repo)
        self.assertFalse(blocked, reason)


if __name__ == "__main__":
    unittest.main()
