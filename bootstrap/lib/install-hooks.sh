#!/usr/bin/env bash
# install-hooks.sh — Idempotent hook script setup
# Symlinks versioned hooks from repo into ~/.claude/scripts/
# Safe to run multiple times.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOKS_SRC="$REPO_DIR/hooks"
HOOKS_DST="$HOME/.claude/scripts"
DRY_RUN="${1:-}"

_log()  { echo "  [hooks] $*"; }
_ok()   { echo "  [hooks] ✓ $*"; }
_skip() { echo "  [hooks] · $* (already linked)"; }
_run()  { [[ "$DRY_RUN" == "--dry-run" ]] && echo "  [hooks] dry: $*" || eval "$*"; }

echo ""
echo "── Install hooks ──────────────────────────────"

mkdir -p "$HOOKS_DST"

# Symlink each hook from the repo into ~/.claude/scripts/
for hook in on-prompt.sh on-session-end.sh post-tool-use.sh credential-guard.sh; do
  src="$HOOKS_SRC/$hook"
  dst="$HOOKS_DST/$hook"

  [[ -f "$src" ]] || { _log "SKIP $hook — not found in repo"; continue; }

  if [[ -L "$dst" && "$(readlink "$dst")" == "$src" ]]; then
    _skip "$hook"
  else
    _run "rm -f '$dst' && ln -s '$src' '$dst' && chmod +x '$src'"
    _ok "linked $hook"
  fi
done

# mem-map.conf was generated here through on-session-end.sh v4. Dropped in v5:
# memory is topic-scoped (an index plus named files) rather than one file per
# project, so a project→file map had nothing real to point at — every entry it
# shipped with named a memory file that does not exist. Remove the stale copy if
# a previous bootstrap left one behind.
STALE_MEM_MAP="$HOOKS_DST/mem-map.conf"
if [[ -f "$STALE_MEM_MAP" ]]; then
  _run "rm -f '$STALE_MEM_MAP'"
  _ok "removed stale mem-map.conf (unused since on-session-end.sh v5)"
fi
