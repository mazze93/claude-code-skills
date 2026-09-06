#!/usr/bin/env bash
# skill-writethrough-check — catch an installer writing through a symlink into a git repo.
#
# ~/.claude/skills mixes two kinds of entry in one flat namespace:
#   symlinks  -> into ~/Projects/skills/claude-code-skills (the repo IS the source)
#   real dirs -> installed copies
#
# Anything that installs a skill by name will happily write THROUGH a symlink
# into the repo's working tree. That is silent, and it looks like ordinary local
# edits afterwards. On 2026-08-31 it re-vendored the pre-consolidation Cloudflare
# set over a 10->2 consolidation; the revert sat undetected until a fleet sweep.
#
# Exit 0 clean, 1 if a symlinked skill has uncommitted changes.
set -uo pipefail
SKILLS="${SKILLS_DIR:-$HOME/.claude/skills}"
found=0

for entry in "$SKILLS"/*; do
  [ -L "$entry" ] || continue
  target=$(readlink "$entry")
  repo=$(git -C "$target" rev-parse --show-toplevel 2>/dev/null) || continue
  rel=${target#"$repo"/}
  dirty=$(GIT_OPTIONAL_LOCKS=0 git -C "$repo" status --porcelain -- "$rel" 2>/dev/null)
  if [ -n "$dirty" ]; then
    found=1
    echo "WRITETHROUGH: $(basename "$entry") — symlinked into $(basename "$repo"), working tree modified"
    echo "$dirty" | sed 's/^/    /'
  fi
done

if [ "$found" = "0" ]; then
  echo "ok — no symlinked skill has uncommitted changes"
  exit 0
fi
cat <<'HINT'

These may be your edits, or an installer writing through the symlink.
Before committing, corroborate the direction:
    git log -S "<an exact added string>" -- <path>
A hit on an older commit means it is a revert, not new work.
HINT
exit 1
