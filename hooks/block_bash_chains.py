#!/usr/bin/env python3
"""PreToolUse hook: hard-fail Bash chains (&&, ||, ;) that contain at
least one segment whose leading verb isn't in BLANKET_VERBS.

Empirical model (FINDINGS 2026-06-04, second consecutive positive data
point after 2026-05-30): Claude Code's permission matcher per-segment-
checks chains. Chains where every segment's leading verb has a blanket
allow rule (or is one of Claude Code's built-in always-allowed verbs)
pass silently. Chains with at least one non-blanket segment PROMPT.

This hook mirrors that with one upgrade: PROMPT → DENY. Per Dan, the
training data biases hard toward chaining commands ("until I put the
hook in you would do ten chains IN A ROW"). The hook is a Claude-
behavior training tool, not a matcher-faithfulness wrapper — hard-
failing mixed chains pushes Claude to split into separate Bash tool
calls, where cwd persists across calls and atomic-if-then-fail
semantics fall out of checking the first call's output.

BLANKET_VERBS is codegen'd into ``_blanket_verbs.py`` by
``update_claude_permissions.py`` on every run (install.sh runs it).
The set unions ALLOW_RULES-derived single-word verbs (e.g. ``echo``,
``git``, ``mkdir``) with a small hardcoded BUILTIN_BLANKET_VERBS set
(currently ``date``, ``hostname``) for matcher built-ins that aren't
in user ALLOW_RULES. See docs/active/chain-hook-maintenance/
FINDINGS.md 2026-06-04 + plans/01_blanket_verb_chain_redesign.md.

Existing skip + prefix-exception logic is unchanged:
  - CD_GIT_RE defers to block_cd_git.py (richer nastygram)
  - FLOW_CONTROL_RE skips for/while/etc. (`;` is syntax, not chain)
  - HEREDOC_RE skips heredoc bodies (semicolons are language syntax)
  - CD_CODE_RE / CD_TMP_RE / ENV_PREFIX_RE: prefix matches, tail must
    be chain-free. Strict in v1 — any chain in the tail still BLOCKS
    even if all tail-verbs are blanket. Plan 01 § 2.2 deliberate scope.
"""
import json
import os
import re
import sys

# Make the codegen'd _blanket_verbs module importable. Claude Code invokes
# the hook via a ~/.claude/hooks/ symlink; sys.path[0] is normally the
# symlink's directory. Resolve to this source file's actual directory so
# the import works regardless of how we're invoked. Plan 01 Open Risk 1.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
try:
    from _blanket_verbs import BLANKET_VERBS
except ImportError:
    # Fresh checkout, update_claude_permissions.py / install.sh hasn't
    # run yet. Empty set = no chain has all-blanket segments = all
    # chains hard-fail. Matches pre-redesign behavior; safe fallback.
    # Plan 01 Open Risk 3.
    BLANKET_VERBS = frozenset()

# --- Whitelist: command prefixes whose chains the matcher actually accepts. ---

# `cd <known-code-dir>` (and subpaths) — followed by /, whitespace, or EOL.
#
# The set of "known" dirs is computed at module load: by default it's
# `$HOME/{code,work,src,dev,projects}` (auto-detect); if the env var
# `CC_HOOK_CD_ALLOWED_PREFIXES` is set to a non-empty colon-separated
# list, that REPLACES the auto-detect (explicit-over-implicit). The
# fallback for missing HOME is `/Users/dan` (Dan's real setup) so the
# hook keeps working in unusual env states.
#
# Renamed 2026-08-04 from a hardcoded `/Users/dan/code` regex — Corpus-
# spinoff Plan 01 Phase 2, so the exported public-repo hook is Dan-
# agnostic without requiring users to hand-edit the regex.
_DEFAULT_CD_CODE_SUBDIRS = ("code", "work", "src", "dev", "projects")


def _build_cd_code_re() -> "re.Pattern[str]":
    """Compile CD_CODE_RE from $HOME + CC_HOOK_CD_ALLOWED_PREFIXES.

    Precedence:
      1. If `CC_HOOK_CD_ALLOWED_PREFIXES` parses to one or more non-empty
         colon-separated entries, those are the sole prefixes (auto-detect
         is off). Trailing slashes are stripped so `/opt/work/` matches
         `/opt/work` and its subpaths.
      2. Otherwise (unset, empty, or all separators): `$HOME/{code,work,
         src,dev,projects}`, with HOME falling back to the running user's
         home directory if unset.
    """
    override = os.environ.get("CC_HOOK_CD_ALLOWED_PREFIXES", "")
    prefixes = [p.rstrip("/") for p in override.split(":") if p.rstrip("/")]
    if not prefixes:
        home = os.environ.get("HOME") or os.path.expanduser("~")
        prefixes = [f"{home}/{sub}" for sub in _DEFAULT_CD_CODE_SUBDIRS]
    alternation = "|".join(re.escape(p) for p in prefixes)
    return re.compile(rf'^\s*cd\s+(?:{alternation})(?:/\S*)?\s')


CD_CODE_RE = _build_cd_code_re()
# `cd /tmp` (and subpaths) — followed by /, whitespace, or EOL.
CD_TMP_RE = re.compile(r'^\s*cd\s+/tmp(?:/\S*)?\s')
# Env-var assignments at the start: FOO=bar BAZ=qux command ...
ENV_PREFIX_RE = re.compile(r'^\s*[A-Za-z_]\w*=\S+\s')

# --- Skip: more specific hooks own these patterns. ---

# cd <path> && git <subcmd> — owned by block_cd_git.py for a specific message.
CD_GIT_RE = re.compile(
    r'(?:^|[;&|]+\s*)cd\s+(?:"[^"]*"|\'[^\']*\'|\S+)\s+&&\s+git\b'
)

# --- Skip: shell flow control with internal semicolons that aren't chains. ---

FLOW_CONTROL_RE = re.compile(r'^\s*(for|while|until|if|case|function)\b')

# --- Skip: heredocs. The body might contain semicolons as language syntax
# (e.g. Python `import os; print(os.getcwd())` inside `python3 <<'PY' ... PY`).
# Matching `<<` followed by an identifier (with optional quoting / dash).
HEREDOC_RE = re.compile(r'<<-?\s*[\'"]?\w+[\'"]?')

# --- Chain operator detection (after stripping quotes/substitutions). ---

CHAIN_RE = re.compile(r'&&|\|\||;')

# Leading verb of a chain segment: optional whitespace, then a letter-led
# identifier (alphanumeric/underscore/hyphen), required to be followed by
# whitespace or end-of-segment. The lookahead is what excludes inline
# env-var assignments (`FOO=bar` fails because the char after `FOO` is `=`,
# not whitespace); a "no extractable verb" segment is treated as non-
# blanket and falls into the BLOCK path.
LEADING_VERB_RE = re.compile(r'^\s*([a-zA-Z][\w-]*)(?=\s|$)')


def strip_inert(cmd: str) -> str:
    """Replace single-quoted, double-quoted, $(...), and `...` segments
    with empty placeholders so chain operators inside them don't match.
    Naive: doesn't handle escaped quotes or nested substitutions, but
    covers the common cases."""
    cmd = re.sub(r"'[^']*'", "''", cmd)
    cmd = re.sub(r'"[^"]*"', '""', cmd)
    cmd = re.sub(r'\$\([^)]*\)', '$()', cmd)
    cmd = re.sub(r'`[^`]*`', '``', cmd)
    return cmd


NASTYGRAM = (
    "Blocked: Bash chain (&&, ||, ;) with at least one segment whose "
    "leading verb isn't blanket-allowed.\n\n"
    "The matcher per-segment-checks chains (FINDINGS 2026-06-04): all-"
    "blanket chains pass silently, mixed chains PROMPT. This hook upgrades "
    "PROMPT to DENY for mixed chains so you split into SEPARATE Bash tool "
    "calls instead of habitually chaining. Working directory persists "
    "across calls, so `cd` in one call and the action in the next works "
    "fine. For if-then-fail semantics, check the first call's exit/output "
    "before deciding whether to run the second.\n\n"
    "BLANKET_VERBS is the union of ALLOW_RULES single-word `Bash(<verb> *)` "
    "rules + a small hardcoded set of Claude-Code built-ins (date, "
    "hostname). Codegen'd into claude-hooks/_blanket_verbs.py by "
    "update_claude_permissions.py.\n\n"
    "See docs/active/chain-hook-maintenance/ for the empirical basis and "
    "the workflow for reporting unexpected prompts.\n\n"
    "If this is the second time you've tripped this hook in one session, "
    "re-read CLAUDE.md's chain-matching section before your next Bash call."
)


def emit_block() -> None:
    """Emit the deny decision and exit."""
    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": NASTYGRAM,
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
    if not command:
        sys.exit(0)

    # Let block_cd_git handle cd+git with its more specific message.
    if CD_GIT_RE.search(command):
        sys.exit(0)

    # Flow control: semicolons are syntax, not chains. Checked before the
    # prefix exceptions so an env-prefixed flow-control statement isn't
    # misread as a chain.
    if FLOW_CONTROL_RE.match(command):
        sys.exit(0)

    # Heredocs: body may contain language-level semicolons, not shell chains.
    # Checked before the prefix exceptions so e.g. `FOO=bar python3 <<'PY' …`
    # doesn't get its heredoc body re-scanned for chains below.
    if HEREDOC_RE.search(command):
        sys.exit(0)

    # Whitelist prefixes (cd into ~/code or /tmp, or env-var assignments).
    # The matcher may accept the prefix itself, but we must NOT blanket-pass a
    # trailing chain: `cd /Users/dan/code 2>/dev/null; rm -rf x` once slipped
    # through because the prefix matched and the tail was never examined (see
    # docs/active/chain-hook-maintenance/, 2026-06-03). Strip the recognized
    # prefix and re-scan only the remainder; pass through only if the tail is
    # itself chain-free.
    # Pad with a trailing space so the prefix regexes' trailing `\s` can match
    # commands that end exactly at the path / assignment.
    padded = command + " "
    prefix = (
        CD_CODE_RE.match(padded)
        or CD_TMP_RE.match(padded)
        or ENV_PREFIX_RE.match(padded)
    )
    if prefix:
        tail = padded[prefix.end():]
        if not CHAIN_RE.search(strip_inert(tail)):
            sys.exit(0)
        emit_block()

    # Strip quoted segments and command substitutions, then look for chain ops.
    stripped = strip_inert(command)
    if not CHAIN_RE.search(stripped):
        sys.exit(0)

    # Chain detected. Per FINDINGS 2026-06-04, the matcher per-segment-
    # checks: all-blanket-verb chains run silently, mixed chains PROMPT.
    # Mirror that here with PROMPT-upgraded-to-DENY: pass through if every
    # segment's leading verb is in BLANKET_VERBS; hard-fail otherwise so
    # Claude learns to split into separate Bash tool calls.
    for segment in CHAIN_RE.split(stripped):
        match = LEADING_VERB_RE.match(segment)
        if not match or match.group(1) not in BLANKET_VERBS:
            emit_block()
    sys.exit(0)


if __name__ == "__main__":
    main()
