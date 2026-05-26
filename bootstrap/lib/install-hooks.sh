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
for hook in on-prompt.sh on-session-end.sh post-tool-use.sh; do
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

# Ensure mem-map.conf exists (machine-specific, not version-controlled)
MEM_MAP="$HOOKS_DST/mem-map.conf"
if [[ ! -f "$MEM_MAP" ]]; then
  _run "cat > '$MEM_MAP' << 'CONF'
# mem-map.conf — project → memory file mapping for on-session-end.sh
# Format: project_name  filename.md (relative to MEMORY_DIR)
# Edit this file to add project-specific memory routing.
typeset -A MEM_MAP
MEM_MAP=(
  secure-pride              secure-pride.md
  secure-pride-aegis-icons  secure-pride.md
  praxis-aegis              praxis.md
  aegis-dns                 praxis.md
  ContextSynapse            praxis.md
  daedalus                  praxis.md
)
CONF"
  _ok "created mem-map.conf (edit to add project mappings)"
else
  _skip "mem-map.conf"
fi
