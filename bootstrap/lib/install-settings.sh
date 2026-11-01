#!/usr/bin/env bash
# install-settings.sh — Idempotent settings.json merge
# Adds the PostToolUse antipattern hook to ~/.claude/settings.json.
# Uses jq to surgically add only missing entries — preserves all existing config.
# Safe to run multiple times.

set -euo pipefail

SETTINGS="$HOME/.claude/settings.json"
DRY_RUN="${1:-}"

_ok()   { echo "  [settings] ✓ $*"; }
_skip() { echo "  [settings] · $* (already present)"; }
_run()  { [[ "$DRY_RUN" == "--dry-run" ]] && echo "  [settings] dry: $*" || eval "$*"; }

echo ""
echo "── Install settings ───────────────────────────"

command -v jq >/dev/null || { echo "  [settings] ✗ jq required — install with: brew install jq"; exit 1; }

# A real install needs settings.json to exist — Claude Code writes it on first
# launch. A --dry-run must not fail for it, though: dry-run is a preview and is
# how CI exercises bootstrap on a machine that has never run Claude Code.
if [[ ! -f "$SETTINGS" ]]; then
  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo "  [settings] dry: $SETTINGS absent — would be created by Claude Code's first launch; skipping"
    exit 0
  fi
  echo "  [settings] ✗ $SETTINGS not found — launch Claude Code first"
  exit 1
fi

# ── PostToolUse antipattern hook ──────────────────────────────────────────────
HOOK_CMD="zsh ~/.claude/scripts/post-tool-use.sh"
HOOK_MATCHER="Edit|Write"

already=$(jq --arg cmd "$HOOK_CMD" '
  .hooks.PostToolUse // [] |
  map(select(.hooks[]?.command == $cmd)) |
  length
' "$SETTINGS" 2>/dev/null || echo 0)

if [[ "$already" -gt 0 ]]; then
  _skip "PostToolUse antipattern hook"
else
  TMPFILE=$(mktemp)
  jq --arg cmd "$HOOK_CMD" --arg matcher "$HOOK_MATCHER" '
    .hooks.PostToolUse = (
      (.hooks.PostToolUse // []) +
      [{"matcher": $matcher, "hooks": [{"type": "command", "command": $cmd}]}]
    )
  ' "$SETTINGS" > "$TMPFILE"

  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo "  [settings] dry: would add PostToolUse hook to $SETTINGS"
    rm -f "$TMPFILE"
  else
    cp "$SETTINGS" "${SETTINGS}.bak.$(date +%Y%m%d-%H%M%S)"
    mv "$TMPFILE" "$SETTINGS"
    _ok "added PostToolUse antipattern hook (matcher: $HOOK_MATCHER)"
    _ok "backup saved: ${SETTINGS}.bak.*"
  fi
fi

# ── SessionStart CLAUDE.md drift hook ─────────────────────────────────────────
# The guard means a missing script (e.g. the source checkout isn't on main yet)
# says so in the session instead of failing silently.
DRIFT_SCRIPT="~/.claude/scripts/claude-md-drift-on-start.sh"
DRIFT_CMD="f=$DRIFT_SCRIPT; [ -e \"\$f\" ] && bash \"\$f\" || echo '{\"systemMessage\":\"claude-md drift hook not active: $DRIFT_SCRIPT missing. Run bootstrap from a claude-code-skills checkout on main.\"}'"

already=$(jq --arg s "claude-md-drift-on-start.sh" '
  .hooks.SessionStart // [] |
  map(select(any(.hooks[]?; .command | contains($s)))) |
  length
' "$SETTINGS" 2>/dev/null || echo 0)

if [[ "$already" -gt 0 ]]; then
  _skip "SessionStart CLAUDE.md drift hook"
else
  TMPFILE=$(mktemp)
  jq --arg cmd "$DRIFT_CMD" '
    .hooks.SessionStart = (
      (.hooks.SessionStart // []) +
      [{"matcher": "startup", "hooks": [{"type": "command", "command": $cmd, "timeout": 15}]}]
    )
  ' "$SETTINGS" > "$TMPFILE"

  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo "  [settings] dry: would add SessionStart(startup) drift hook to $SETTINGS"
    rm -f "$TMPFILE"
  else
    cp "$SETTINGS" "${SETTINGS}.bak.$(date +%Y%m%d-%H%M%S)"
    mv "$TMPFILE" "$SETTINGS"
    _ok "added SessionStart(startup) CLAUDE.md drift hook"
    _ok "backup saved: ${SETTINGS}.bak.*"
  fi
fi

# ── Verify minimum version ─────────────────────────────────────────────────────
CURRENT_MIN=$(jq -r '.minimumVersion // empty' "$SETTINGS" 2>/dev/null)
REQUIRED_MIN="2.1.150"
if [[ -z "$CURRENT_MIN" ]]; then
  _skip "minimumVersion (not set — leaving as-is)"
else
  _skip "minimumVersion ($CURRENT_MIN)"
fi
