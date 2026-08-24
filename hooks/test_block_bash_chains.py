"""Behavioral tests for claude-hooks/block_bash_chains.py.

Drives the hook as a subprocess (the real stdin -> permissionDecision
contract Claude Code uses), not a mock.

Regression origin (2026-06-03): the whitelist-prefix exceptions
(`cd /Users/dan/code …`, `cd /tmp …`, env-var prefix) did a blanket
`exit 0` the moment the prefix matched, never examining the tail. So
`cd /Users/dan/code 2>/dev/null; ls; pwd` slipped through the chain
hook entirely (the ` ` before `2>/dev/null` satisfied the prefix
regex's trailing `\\s`), while the adjacent `hostname && date -u` was
correctly blocked. The fix strips the matched prefix and re-scans only
the remainder. See docs/active/chain-hook-maintenance/.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).parent / "block_bash_chains.py"

# For direct-regex tests: make block_bash_chains importable so we can
# call _build_cd_code_re() in-process without going through the hook
# subprocess. Corpus-spinoff Plan 01 Phase 2.
sys.path.insert(0, str(Path(__file__).parent))


def _run_hook_at(hook_path: Path, command: str, env: dict = None) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    proc = subprocess.run(
        ["python3", str(hook_path)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,  # None = inherit parent env; dict = explicit env for the child.
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Hook crashed (exit {proc.returncode}): "
            f"stderr={proc.stderr!r} stdout={proc.stdout!r}"
        )
    out = proc.stdout.strip()
    if not out:
        return "allow"
    decision = json.loads(out)["hookSpecificOutput"]["permissionDecision"]
    return "block" if decision == "deny" else "allow"


def run_hook(command: str, env: dict = None) -> str:
    """Return 'block' or 'allow' for a given Bash command string.

    If env is provided, it's passed verbatim to the subprocess (replacing
    the parent env). Used by Phase-2 tests to verify runtime CD_CODE_RE
    responds to HOME / CC_HOOK_CD_ALLOWED_PREFIXES.
    """
    return _run_hook_at(HOOK, command, env=env)


class TestBlockedChains(unittest.TestCase):
    """Chains where at least one segment's leading verb isn't blanket-allowed,
    OR where the prefix-exception path catches a chain-bearing tail.

    Post-Plan-01 model: hook hard-fails MIXED chains (training friction —
    push Claude to split into separate Bash calls). Bare chains where every
    segment's leading verb is in BLANKET_VERBS now PASS THROUGH the hook
    (matcher silently allows them) — those moved to
    TestBlanketChainPassthrough below. See
    docs/active/chain-hook-maintenance/plans/01_blanket_verb_chain_redesign.md."""

    def test_cd_code_prefix_with_redirection_then_chain(self):
        # The exact 2026-06-03 weirdo: cd-code prefix + redirection space +
        # `;` and `|` tail. Must NOT leak through the prefix exception.
        self.assertEqual(
            run_hook(
                'cd /Users/dan/code 2>/dev/null; ls -d */ 2>/dev/null '
                '| head -50; echo "---PWD---"; pwd'
            ),
            "block",
        )

    def test_cd_code_prefix_space_then_semicolon_chain(self):
        # Even without a redirection, a space before `;` must not leak.
        self.assertEqual(
            run_hook("cd /Users/dan/code ; rm -rf something; echo gotcha"),
            "block",
        )

    def test_cd_code_prefix_immediate_semicolon(self):
        self.assertEqual(
            run_hook("cd /Users/dan/code; rm -rf something; echo gotcha"),
            "block",
        )

    def test_cd_tmp_prefix_then_chain(self):
        self.assertEqual(run_hook("cd /tmp; evil; chain"), "block")

    def test_cd_tmp_prefix_space_then_chain(self):
        self.assertEqual(run_hook("cd /tmp 2>/dev/null; evil; chain"), "block")

    def test_env_prefix_then_chain(self):
        # `a` and `b` are not blanket verbs. Even if they were, the
        # prefix-exception path (Plan 01 v1) blocks any chain in the tail
        # regardless — see TestPrefixExceptionAsymmetryPinned for the
        # explicit asymmetry pins.
        self.assertEqual(run_hook("FOO=bar a && b"), "block")


class TestBlanketChainPassthrough(unittest.TestCase):
    """Chains where EVERY segment's leading verb is in BLANKET_VERBS (the
    union of ALLOW_RULES-derived verbs + BUILTIN_BLANKET_VERBS, codegen'd
    by update_claude_permissions.py into claude-hooks/_blanket_verbs.py).

    Per FINDINGS 2026-06-04, the matcher silently ALLOWs these chains;
    the hook must NOT hard-fail them (over-blocking was the redesign's
    motivation). Verbs used here (date, hostname, echo, mkdir, touch,
    git, ls, pwd, cat, grep) are pinned in
    test_update_claude_permissions.py::TestComputeBlanketVerbs::
    test_contains_all_probe_verbs — if any drops out of the union,
    that canary fires first."""

    # --- The three flipped cases from the old TestBlockedChains. ---

    def test_blanket_ampersand_chain_passes(self):
        # Was test_ampersand_chain. hostname + date both BUILTIN-blanket.
        self.assertEqual(run_hook("hostname && date -u"), "allow")

    def test_blanket_semicolon_chain_passes(self):
        # Was test_bare_semicolon_chain. ls + pwd both ALLOW_RULES-blanket.
        self.assertEqual(run_hook("ls; pwd"), "allow")

    def test_blanket_semicolon_chain_with_inner_pipe_passes(self):
        # Was test_pipe_chain. The discriminator is the `;`, not the `|`
        # (single `|` is out of CHAIN_RE scope by design — Plan 01 § 2.2).
        # Split on `;`: ["cat foo | grep bar", "echo done"]. Leading verbs
        # cat + echo, both blanket → ALLOW.
        self.assertEqual(run_hook("cat foo | grep bar; echo done"), "allow")

    # --- 2026-06-04 8-cell probe map (cells with matcher-ALLOW result). ---

    def test_probe2_date_and_hostname(self):
        # Probe 2: both BUILTIN-blanket via &&.
        self.assertEqual(run_hook("date && hostname"), "allow")

    def test_probe3_echo_with_args(self):
        # Probe 3: same blanket verb both sides, with arguments.
        self.assertEqual(run_hook("echo a && echo b"), "allow")

    def test_probe4_mkdir_touch_with_paths(self):
        # Probe 4: realistic chain — mkdir + touch with flags + paths.
        self.assertEqual(
            run_hook(
                "mkdir -p /tmp/probe_2026-06-04 && "
                "touch /tmp/probe_2026-06-04/x"
            ),
            "allow",
        )

    def test_probe6_semicolon_separator(self):
        # Probe 6: same as probe 2 but with `;` instead of `&&`.
        self.assertEqual(run_hook("date ; hostname"), "allow")

    def test_probe8_single_pipe(self):
        # Probe 8: single `|`. CHAIN_RE does NOT match single `|` (only
        # `&&`, `||`, `;`) — passes through the non-chain branch entirely,
        # without consulting BLANKET_VERBS. Plan 01 § 2.2 keeps single-pipe
        # out of scope; this test pins the design choice.
        self.assertEqual(run_hook("date | grep Jun"), "allow")

    # --- Additional Plan 01 § 2.2 edge cases. ---

    def test_logical_or_separator(self):
        # `||`. Plan 01 defers empirical re-verification; assumed consistent
        # with `&&` per historical behavior. If a weirdo surfaces, re-probe.
        self.assertEqual(run_hook("date || hostname"), "allow")

    def test_three_segment_all_blanket(self):
        self.assertEqual(
            run_hook("date && hostname && echo hi"), "allow"
        )

    def test_leading_whitespace(self):
        # Hook's CHAIN_RE doesn't anchor at start; the verb-extract logic
        # must strip leading whitespace before reading the first segment's
        # verb. Two-space prefix is a realistic Claude-output shape.
        self.assertEqual(run_hook("  date && hostname"), "allow")

    def test_five_segment_stress(self):
        # All five segments blanket — covers >3 segments.
        self.assertEqual(
            run_hook("date && hostname && echo && ls && pwd"), "allow"
        )

    def test_two_git_segments(self):
        # Same blanket verb in both segments — `git` is single-word
        # blanket via Bash(git *); the Bash(git worktree add *) rule
        # doesn't change that.
        self.assertEqual(run_hook("git status; git log"), "allow")


class TestMixedChainBlocked(unittest.TestCase):
    """Chains where at least one segment's leading verb is NOT blanket.
    Hook hard-fails these — training friction to make Claude split into
    separate Bash tool calls. Mirrors the matcher's per-segment PROMPT
    behavior with a harder DENY (per Plan 01 § Context — the hook is a
    Claude-behavior training tool, not a matcher-faithfulness wrapper)."""

    def test_probe5_unknown_after_blanket(self):
        # Probe 5 (2026-06-04): blanket + unknown via &&. Matcher PROMPTs;
        # hook upgrades to BLOCK.
        self.assertEqual(
            run_hook("date && unknownmarker_2026-06-04_probe5"),
            "block",
        )

    def test_probe7_unknown_before_blanket(self):
        # Probe 7 (2026-06-04): unknown + blanket. Symmetry guard — the
        # matcher per-segment-checks regardless of segment order; the hook
        # must too.
        self.assertEqual(
            run_hook("unknownmarker_2026-06-04_probe7 && date"),
            "block",
        )

    def test_three_segment_unknown_in_middle(self):
        # Mixed segment buried between two blanket segments.
        self.assertEqual(
            run_hook("date && unknownmarker_middle && echo hi"),
            "block",
        )

    def test_all_unknown_chain(self):
        # No blanket verbs at all.
        self.assertEqual(
            run_hook("unknownmarker_a && unknownmarker_b"),
            "block",
        )


class TestPrefixExceptionAsymmetryPinned(unittest.TestCase):
    """Pins the v1 prefix-exception asymmetry called out explicitly in
    Plan 01 § 2.2: the prefix-exception path (cd /Users/dan/code, cd /tmp,
    env-var prefix) stays STRICT — any chain in the tail is BLOCK,
    regardless of whether the tail's verbs are all blanket. So
    `cd /tmp 2>/dev/null; ls` BLOCKS even though bare `ls; pwd` ALLOWs.

    This asymmetry is intentional v1 scope, and these tests exist so a
    future "simplify the prefix path" tweak can't silently relax it
    without flipping a test on purpose."""

    def test_env_prefix_then_blanket_chain_still_blocks(self):
        # Both `date` and `hostname` are blanket. ENV_PREFIX matches
        # `FOO=bar `, tail `date && hostname ` has chain → BLOCK.
        self.assertEqual(
            run_hook("FOO=bar date && hostname"), "block"
        )

    def test_cd_tmp_prefix_then_blanket_chain_still_blocks(self):
        # CD_TMP_RE matches `cd /tmp 2>/dev/null `. Tail `; ls ` has chain
        # → BLOCK. Even though `ls` alone is blanket.
        self.assertEqual(
            run_hook("cd /tmp 2>/dev/null; ls"), "block"
        )


class TestQuotedChainOpsNotSplit(unittest.TestCase):
    """strip_inert removes single-quoted, double-quoted, $(...), and
    backtick segments before chain-op detection. Chain operators inside
    those segments are inert — must NOT cause split-and-extract logic
    to mis-classify the command."""

    def test_double_quoted_ampersand_op_inert(self):
        # The `&&` is inside a double-quoted string. strip_inert removes
        # the quoted body → no chain op left → PASS.
        self.assertEqual(
            run_hook('echo "foo && bar"'), "allow"
        )

    def test_single_quoted_semicolon_op_inert(self):
        # Same for `;` inside single quotes.
        self.assertEqual(
            run_hook("echo 'a;b;c'"), "allow"
        )

    def test_real_chain_with_quoted_inert_section_still_detected(self):
        # `echo "x"` is single segment (quoted body inert). Real `&&` then
        # `unknownmarker`. Split should give ["echo \"x\"", "unknownmarker"]
        # — leading verbs `echo` (blanket) + `unknownmarker` (not). MIXED
        # → BLOCK. Pins that quote-stripping doesn't accidentally lose
        # real chain ops alongside inert ones.
        self.assertEqual(
            run_hook('echo "x" && unknownmarker'), "block"
        )


class TestAllowedCommands(unittest.TestCase):
    """Non-chains and genuine exceptions must pass through."""

    def test_bare_cd_code(self):
        self.assertEqual(run_hook("cd /Users/dan/code"), "allow")

    def test_bare_cd_code_subpath(self):
        self.assertEqual(run_hook("cd /Users/dan/code/dotfiles/claude-hooks"), "allow")

    def test_env_prefix_single_command(self):
        self.assertEqual(run_hook("FOO=bar python script.py"), "allow")

    def test_multi_env_prefix_single_command(self):
        self.assertEqual(run_hook("FOO=bar BAZ=qux python script.py"), "allow")

    def test_plain_single_command(self):
        self.assertEqual(run_hook("ls -la"), "allow")

    def test_cd_git_deferred_to_other_hook(self):
        # block_cd_git.py owns this pattern; block_bash_chains must defer.
        self.assertEqual(run_hook("cd /Users/dan/code && git status"), "allow")

    def test_flow_control_for_loop_semicolons(self):
        self.assertEqual(
            run_hook("for f in *.py; do echo $f; done"), "allow"
        )

    def test_heredoc_body_semicolons(self):
        self.assertEqual(
            run_hook("python3 <<'PY'\nimport os; print(os.getcwd())\nPY"),
            "allow",
        )

    def test_env_prefixed_heredoc_body_semicolons(self):
        # Regression guard: env prefix + heredoc must not have its body
        # re-scanned for chains by the new tail-scan logic.
        self.assertEqual(
            run_hook("FOO=bar python3 <<'PY'\nimport os; print(os.getcwd())\nPY"),
            "allow",
        )

    def test_pipe_inside_single_quotes_not_a_chain(self):
        self.assertEqual(run_hook("grep 'a||b' file.txt"), "allow")


class TestMissingBlanketVerbsModuleFallback(unittest.TestCase):
    """Plan 01 Open Risk 3: if _blanket_verbs.py is missing at hook
    invocation time (fresh checkout, install.sh hasn't run yet), the
    hook must fail-safe — empty BLANKET_VERBS means no chain has all-
    blanket segments, so every chain hard-fails. This matches pre-
    redesign behavior, so the hook never SILENTLY weakens its policy
    on a fresh machine.

    Tested by copying the hook source to a temp dir (which has no
    _blanket_verbs.py alongside it) and invoking that copy directly.
    The hook's sys.path.insert(0, realpath(__file__).parent) resolves
    to the temp dir, so the import fails into the except branch."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.isolated_hook = Path(self.tmpdir.name) / "block_bash_chains.py"
        shutil.copy2(HOOK, self.isolated_hook)
        # Sanity: temp dir has no _blanket_verbs module.
        self.assertFalse(
            (Path(self.tmpdir.name) / "_blanket_verbs.py").exists()
        )

    def test_single_command_still_passes(self):
        # No chain → the BLANKET_VERBS check is never reached. Must pass
        # even when the module is missing.
        self.assertEqual(_run_hook_at(self.isolated_hook, "date"), "allow")

    def test_all_blanket_chain_blocks_when_module_missing(self):
        # Under the real generated module this would PASS (date + hostname
        # both BUILTIN-blanket). With the module missing → BLANKET_VERBS
        # is empty → no segment's verb is in it → BLOCK. Pre-redesign
        # behavior recovered as the safe fallback.
        self.assertEqual(
            _run_hook_at(self.isolated_hook, "date && hostname"),
            "block",
        )

    def test_mixed_chain_blocks_when_module_missing(self):
        # Same outcome as with the module present (BLOCK), but via the
        # empty-set path rather than the verb-not-in-set path.
        self.assertEqual(
            _run_hook_at(self.isolated_hook, "date && unknownmarker"),
            "block",
        )

    def test_hook_does_not_crash(self):
        # If the ImportError handling regressed (e.g. someone replaced
        # the try/except with a bare `from _blanket_verbs import ...`),
        # the hook would raise ModuleNotFoundError and exit non-zero.
        # _run_hook_at raises RuntimeError on non-zero exit; reaching
        # this assertion means the fallback held.
        result = _run_hook_at(self.isolated_hook, "ls; pwd")
        self.assertIn(result, ("allow", "block"))


class TestBuildCdCodeRe(unittest.TestCase):
    """Runtime construction of CD_CODE_RE from HOME + CC_HOOK_CD_ALLOWED_PREFIXES.

    Corpus-spinoff Plan 01 Phase 2: the pre-2026-08-04 hardcoded
    `cd /Users/dan/code` regex is replaced with a builder that derives
    prefixes from HOME (auto-detects `code`, `work`, `src`, `dev`,
    `projects` subdirs) or from an explicit `CC_HOOK_CD_ALLOWED_PREFIXES`
    colon-separated override. This makes the exported hook Dan-agnostic
    without requiring public users to hand-edit the regex.

    Tested directly (not via the hook subprocess) to isolate the regex
    builder from the rest of the hook logic (CD_GIT_RE skip, general
    chain analysis, BLANKET_VERBS state). One subprocess-level test in
    the class below verifies the end-to-end wiring.
    """

    def _regex_for(self, home, override=None):
        """Build CD_CODE_RE with the given env overrides, restoring env after."""
        from block_bash_chains import _build_cd_code_re
        saved = os.environ.copy()
        try:
            os.environ["HOME"] = home
            os.environ.pop("CC_HOOK_CD_ALLOWED_PREFIXES", None)
            if override is not None:
                os.environ["CC_HOOK_CD_ALLOWED_PREFIXES"] = override
            return _build_cd_code_re()
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def test_default_home_matches_users_dan_code(self):
        # Regression: Dan's real setup must keep working unchanged.
        regex = self._regex_for(home="/Users/dan")
        self.assertIsNotNone(regex.match("cd /Users/dan/code "))
        self.assertIsNotNone(regex.match("cd /Users/dan/code/dotfiles "))

    def test_default_home_matches_users_dan_work(self):
        # Auto-detect enumerated subdirs include `work`.
        regex = self._regex_for(home="/Users/dan")
        self.assertIsNotNone(regex.match("cd /Users/dan/work "))

    def test_default_home_matches_all_auto_detect_subdirs(self):
        # Full enumeration: code, work, src, dev, projects.
        regex = self._regex_for(home="/Users/dan")
        for sub in ("code", "work", "src", "dev", "projects"):
            self.assertIsNotNone(
                regex.match(f"cd /Users/dan/{sub} "),
                f"expected match for /Users/dan/{sub}",
            )

    def test_other_home_matches_other_code(self):
        # New user's HOME=/home/alice → cd /home/alice/code recognized.
        regex = self._regex_for(home="/home/alice")
        self.assertIsNotNone(regex.match("cd /home/alice/code "))

    def test_other_home_does_not_match_users_dan_code(self):
        # HOME=/home/alice → cd /Users/dan/code is NOT auto-detected.
        regex = self._regex_for(home="/home/alice")
        self.assertIsNone(regex.match("cd /Users/dan/code "))

    def test_other_home_does_not_match_unenumerated_subdir(self):
        # `misc` is not in the auto-detect set → prefix not recognized.
        regex = self._regex_for(home="/home/alice")
        self.assertIsNone(regex.match("cd /home/alice/misc "))

    def test_override_replaces_auto_detect(self):
        # CC_HOOK_CD_ALLOWED_PREFIXES REPLACES auto-detect (per plan §Phase 2 step 1c).
        # The override is authoritative: if you set it, you're picking your own list.
        regex = self._regex_for(
            home="/home/alice",
            override="/tmp/foo:/tmp/bar",
        )
        self.assertIsNotNone(regex.match("cd /tmp/foo "))
        self.assertIsNotNone(regex.match("cd /tmp/bar "))
        # /home/alice/code is NOT auto-added when override is set.
        self.assertIsNone(regex.match("cd /home/alice/code "))

    def test_override_supports_subpaths(self):
        # The regex accepts the enumerated prefix followed by /subpath.
        regex = self._regex_for(
            home="/home/alice",
            override="/opt/work",
        )
        self.assertIsNotNone(regex.match("cd /opt/work "))
        self.assertIsNotNone(regex.match("cd /opt/work/project "))

    def test_home_unset_falls_back_to_default(self):
        # If HOME is somehow missing from env, the default /Users/dan is used
        # (chosen so Dan's real setup keeps working even in weird env states).
        saved = os.environ.copy()
        try:
            os.environ.pop("HOME", None)
            os.environ.pop("CC_HOOK_CD_ALLOWED_PREFIXES", None)
            from block_bash_chains import _build_cd_code_re
            regex = _build_cd_code_re()
            self.assertIsNotNone(regex.match("cd /Users/dan/code "))
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def test_empty_override_falls_back_to_auto_detect(self):
        # Empty string override = treat as unset (defensive).
        regex = self._regex_for(home="/home/alice", override="")
        self.assertIsNotNone(regex.match("cd /home/alice/code "))


class TestCdCodePathRuntimeWiring(unittest.TestCase):
    """End-to-end: subprocess invocation with env vars flowing through to
    the module-load-time _build_cd_code_re() call. One integration test —
    the exhaustive-regex-shape coverage lives in TestBuildCdCodeRe."""

    def _subprocess_env(self, **overrides):
        env = os.environ.copy()
        for k, v in overrides.items():
            if v is None:
                env.pop(k, None)
            else:
                env[k] = v
        return env

    def test_default_env_dan_code_prefix_with_chain_denies(self):
        # Regression: Dan's real setup — cd /Users/dan/code + trailing
        # chain still DENIES (prevents the 2026-06-03 bypass).
        env = self._subprocess_env(HOME="/Users/dan", CC_HOOK_CD_ALLOWED_PREFIXES=None)
        self.assertEqual(run_hook("cd /Users/dan/code ; ls", env=env), "block")

    def test_other_home_recognizes_other_code_prefix(self):
        # New user HOME=/home/alice — cd /home/alice/code + trailing
        # chain should DENY (auto-detect kicked in).
        env = self._subprocess_env(HOME="/home/alice", CC_HOOK_CD_ALLOWED_PREFIXES=None)
        self.assertEqual(run_hook("cd /home/alice/code ; ls", env=env), "block")

    def test_override_env_var_flows_through(self):
        # With override set, cd /opt/work + trailing chain DENIES.
        env = self._subprocess_env(
            HOME="/home/alice",
            CC_HOOK_CD_ALLOWED_PREFIXES="/opt/work",
        )
        self.assertEqual(run_hook("cd /opt/work ; ls", env=env), "block")


if __name__ == "__main__":
    unittest.main()
