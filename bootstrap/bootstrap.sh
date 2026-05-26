#!/usr/bin/env bash
# bootstrap.sh — Claude Code environment cold-start
#
# Idempotent: safe to run multiple times, only acts on what's missing or wrong.
# Transferrable: uses $HOME throughout — no hardcoded usernames or machine paths.
# Elegant: each sub-script is self-contained; the main entry just orchestrates.
#
# Usage:
#   ./bootstrap.sh              # apply everything
#   ./bootstrap.sh --dry-run    # preview without writing
#   ./bootstrap.sh --help       # this message

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN="--dry-run" ;;
    --help|-h)
      echo ""
      echo "  bootstrap.sh — Claude Code cold-start"
      echo ""
      echo "  What it does:"
      echo "    1. Symlinks hook scripts (on-prompt, on-session-end, post-tool-use)"
      echo "       from this repo into ~/.claude/scripts/"
      echo "    2. Symlinks skills from skills/ into ~/.claude/skills/"
      echo "    3. Adds PostToolUse antipattern hook to ~/.claude/settings.json"
      echo ""
      echo "  Options:"
      echo "    --dry-run    Preview changes without writing"
      echo "    --help       This message"
      echo ""
      echo "  Prerequisites: bash, jq, git"
      echo "  Restart Claude Code after running."
      echo ""
      exit 0
      ;;
  esac
done

# ── Prerequisites ─────────────────────────────────────────────────────────────
for cmd in jq git bash; do
  command -v "$cmd" >/dev/null || { echo "✗ Required: $cmd (install via brew)"; exit 1; }
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Claude Code Bootstrap"
echo "  repo: $REPO_DIR"
echo "  home: $HOME"
[[ -n "$DRY_RUN" ]] && echo "  mode: DRY RUN — no files will be written"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

bash "$REPO_DIR/bootstrap/lib/install-hooks.sh"    $DRY_RUN
bash "$REPO_DIR/bootstrap/lib/install-skills.sh"   $DRY_RUN
bash "$REPO_DIR/bootstrap/lib/install-settings.sh" $DRY_RUN

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ -n "$DRY_RUN" ]]; then
  echo "  Dry run complete. Re-run without --dry-run to apply."
else
  echo "  Bootstrap complete."
  echo "  → Restart Claude Code to activate hook changes."
  echo "  → Edit ~/.claude/scripts/mem-map.conf if needed."
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
