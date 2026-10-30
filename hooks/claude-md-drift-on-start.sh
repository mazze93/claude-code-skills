#!/usr/bin/env bash
# SessionStart(startup) drift check: runs the claude-md-audit deterministic scan
# (skills/claude-md-audit/scan.py) on the project being opened, before work starts.
# Drifted CLAUDE.md files are worse than none, because agents follow them
# confidently. Directed by Mazze 2026-10-30; Stratum log context-synapse,
# dec-mvu9o3g7-4485.
#
# Quiet when clean. On findings, injects them as session context and shows a
# one-line systemMessage. Flags only, never rewrites: each CLAUDE.md change
# alters agent behaviour and needs review in that repo's context.
#
# Fails LOUD, not closed: a missing scan.py, python3 or jq produces a visible
# message instead of silently skipping. A drift guard that goes dark without
# telling anyone is the failure it exists to prevent. It never blocks the
# session; SessionStart can't, and a broken scanner shouldn't stop work.
#
# Scope: the scan's checks (dead backticked paths, stale workspace roots, old
# model strings, ~/.claude/CLAUDE.md existence). Dead-path hits include known
# false positives (shorthand refs, enum-like tokens); the injected context
# says so. Lane 2 (Ollama summaries) and the full audit stay on demand via
# /workspace:claude-md-audit.
set -uo pipefail

warn() { printf '{"systemMessage":"claude-md drift hook: %s"}\n' "$1"; exit 0; }

command -v jq >/dev/null || warn "jq missing; drift scan skipped"
command -v python3 >/dev/null || warn "python3 missing; drift scan skipped"

input=$(cat 2>/dev/null || true)
src=$(printf '%s' "$input" | jq -r '.source // "startup"' 2>/dev/null || echo startup)
[ "$src" = "startup" ] || exit 0

project=${CLAUDE_PROJECT_DIR:-$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)}
[ -n "$project" ] && [ -d "$project" ] || exit 0
top=$(git -C "$project" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$project")
[ -f "$top/CLAUDE.md" ] || exit 0

# Resolve scan.py next to this script's real location (it is symlinked into
# ~/.claude/scripts by bootstrap/lib/install-hooks.sh).
self=$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || printf '%s' "${BASH_SOURCE[0]}")
scan="$(dirname "$(dirname "$self")")/skills/claude-md-audit/scan.py"
[ -f "$scan" ] || warn "scan.py not found at $scan; the drift scan did not run (is claude-code-skills checked out at main?)"

# No `timeout`: macOS doesn't ship one. The settings entry sets a hook timeout instead.
out=$(cd /tmp && python3 -I "$scan" "$top" 2>&1) || warn "scan.py failed: $(printf '%s' "$out" | tail -1 | tr '"\\' "'/")"

# Findings are "   - " lines; a missing global CLAUDE.md is critical.
findings=$(printf '%s\n' "$out" | grep -E '^   - ' || true)
missing_global=$(printf '%s\n' "$out" | grep -F '~/.claude/CLAUDE.md: MISSING' || true)
[ -z "$findings" ] && [ -z "$missing_global" ] && exit 0

n=$(printf '%s\n' "$findings" | grep -c . || true)
ctx=$(printf 'CLAUDE.md drift scan for %s found %s issue line(s) before this session started.\n\n%s\n%s\n\nVerify each hit before trusting the instruction it touches: dead-path hits include false positives (shorthand refs, enum-like tokens). For a confirmed stale reference, fix it or name it as outstanding, per the global "see rot, fix rot" rule. Flag, do not auto-rewrite. Full audit: /workspace:claude-md-audit.' \
  "$top" "$n" "$findings" "${missing_global:+CRITICAL: $missing_global}")

msg="claude-md drift: $n finding(s) in $(basename "$top")/CLAUDE.md, added to context; run /workspace:claude-md-audit to review"
[ -n "$missing_global" ] && msg="claude-md drift: CRITICAL, ~/.claude/CLAUDE.md is missing (postures and hard stops are gone); $n finding(s) in $(basename "$top")/CLAUDE.md"
jq -n --arg ctx "$ctx" --arg msg "$msg" \
  '{systemMessage: $msg, hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
