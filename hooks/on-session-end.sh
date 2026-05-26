#!/bin/zsh
# on-session-end.sh v4 — Stop hook
# Outputs JSON with systemMessage so Claude Code displays the summary.
# Portable across machines: derives MEMORY_DIR from $HOME, sources MEM_MAP from a config file.

command -v jq >/dev/null || exit 0

INPUT=$(cat 2>/dev/null)
_jval() {
  printf '%s' "$INPUT" | jq -r --arg k "$1" '.[$k] // empty' 2>/dev/null
}

TRANSCRIPT=$(_jval transcript_path)
SESSION_ID=$(_jval session_id)
CWD=$(_jval cwd)
[[ -z "$CWD" ]] && CWD="$PWD"

if [[ "$CWD" =~ "\.claude-worktrees" ]]; then
  PROJECT=$(basename "${CWD%%/.claude-worktrees*}")
else
  PROJECT=$(basename "$CWD")
fi

# Portable: derive memory dir from $HOME (works for any username/path)
MEMORY_DIR="$HOME/.claude/projects/$(echo "$HOME" | sed 's|/|-|g')/memory"

EDITS=0; WRITES=0; TOOL_CALLS=0
if [[ -f "$TRANSCRIPT" ]]; then
  EDITS=$(grep -c '"name":"Edit"' "$TRANSCRIPT" 2>/dev/null || true)
  WRITES=$(grep -c '"name":"Write"' "$TRANSCRIPT" 2>/dev/null || true)
  TOOL_CALLS=$(grep -c '"type":"tool_use"' "$TRANSCRIPT" 2>/dev/null || true)
fi
TOTAL_CHANGES=$(( EDITS + WRITES ))

# Git state nudge — only if CWD is inside a repo
GIT_NUDGE=""
if git -C "$CWD" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  UNCOMMITTED=$(git -C "$CWD" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  BRANCH=$(git -C "$CWD" rev-parse --abbrev-ref HEAD 2>/dev/null)
  if (( UNCOMMITTED > 0 )); then
    GIT_NUDGE="⚠ ${UNCOMMITTED} uncommitted on ${BRANCH} — review before stepping away."
  fi
fi

lines=()
lines+=("◆ SESSION END $(date '+%Y-%m-%d %H:%M') | ${PROJECT} | ${TOOL_CALLS} tools | ${TOTAL_CHANGES} file changes")

if (( TOTAL_CHANGES == 0 && TOOL_CALLS < 5 )); then
  lines+=("Light session — no memory save needed.")
  [[ -n "$GIT_NUDGE" ]] && lines+=("$GIT_NUDGE")
else
  (( TOTAL_CHANGES > 0 )) && lines+=("${EDITS} edits, ${WRITES} writes — consider what's non-obvious from the diff.")
  (( TOOL_CALLS >= 15 ))  && lines+=("Heavy session — likely contains design decisions worth preserving.")
  [[ -n "$GIT_NUDGE" ]] && lines+=("$GIT_NUDGE")
  lines+=("")
  lines+=("Memory targets:")
  lines+=("  Global: ${MEMORY_DIR}/MEMORY.md")

  # Source per-machine project→memory mapping (extracted to keep the script portable)
  MEM_MAP_FILE="$HOME/.claude/scripts/mem-map.conf"
  if [[ -f "$MEM_MAP_FILE" ]]; then
    source "$MEM_MAP_FILE"
    MAPPED="${MEM_MAP[$PROJECT]}"
    [[ -n "$MAPPED" ]] && lines+=("  Project: ${MEMORY_DIR}/${MAPPED}")
  fi

  EXACT="${MEMORY_DIR}/${PROJECT}.md"
  [[ -f "$EXACT" && "${PROJECT}.md" != "$MAPPED" ]] && lines+=("  Project: ${EXACT}")
fi

# Clean up session memory injection flags
[[ -n "$SESSION_ID" ]] && rm -f /tmp/claude-ctx/mem-${SESSION_ID}-*(N) 2>/dev/null

# Emit JSON systemMessage
MSG="${(j:\n:)lines}"
printf '%s' "$MSG" | jq -Rs '{"systemMessage": .}'
