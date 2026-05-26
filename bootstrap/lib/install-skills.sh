#!/usr/bin/env bash
# install-skills.sh — Idempotent skill symlink setup
# Symlinks each skill dir from the repo into ~/.claude/skills/
# Safe to run multiple times.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SKILLS_SRC="$REPO_DIR/skills"
SKILLS_DST="$HOME/.claude/skills"
DRY_RUN="${1:-}"

_ok()   { echo "  [skills] ✓ $*"; }
_skip() { echo "  [skills] · $* (already linked)"; }
_run()  { [[ "$DRY_RUN" == "--dry-run" ]] && echo "  [skills] dry: $*" || eval "$*"; }

echo ""
echo "── Install skills ─────────────────────────────"

mkdir -p "$SKILLS_DST"

# Symlink each skill directory
for skill_dir in "$SKILLS_SRC"/*/; do
  [[ -d "$skill_dir" ]] || continue
  name="$(basename "$skill_dir")"
  src="${skill_dir%/}"
  dst="$SKILLS_DST/$name"

  if [[ -L "$dst" && "$(readlink "$dst")" == "$src" ]]; then
    _skip "$name"
  else
    _run "rm -rf '$dst' && ln -s '$src' '$dst'"
    _ok "linked skill: $name"
  fi
done

# Symlink statusline config
STATUSLINE_SRC="$REPO_DIR/config/cc-statusline.sh"
STATUSLINE_DST="$HOME/.config/iterm2/cc-statusline.sh"
if [[ -f "$STATUSLINE_SRC" ]]; then
  mkdir -p "$(dirname "$STATUSLINE_DST")"
  if [[ -L "$STATUSLINE_DST" && "$(readlink "$STATUSLINE_DST")" == "$STATUSLINE_SRC" ]]; then
    _skip "cc-statusline.sh"
  else
    _run "rm -f '$STATUSLINE_DST' && ln -s '$STATUSLINE_SRC' '$STATUSLINE_DST'"
    _ok "linked cc-statusline.sh"
  fi
fi
