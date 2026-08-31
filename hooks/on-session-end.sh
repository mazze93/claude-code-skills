#!/bin/zsh
# on-session-end.sh v5 — Stop hook
# Outputs JSON with systemMessage so Claude Code displays the summary.
# v5 (2026-07-25): dropped the mem-map.conf project→memory lookup. Memory is now
#     topic-scoped (MEMORY.md index + named files), not one file per project, so
#     a project→file map had nothing real to point at. Lists what actually exists
#     instead. Also warns on unpushed commits, not just uncommitted files —
#     work that only exists on this laptop is the failure mode that matters.
# Portable across machines: derives MEMORY_DIR from $HOME.

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

# Git state nudge — only if CWD is inside a repo.
# Two distinct failures: work not committed, and work committed but never pushed.
# The second is the one that loses a machine's worth of work silently.
GIT_NUDGE=""
GIT_PUSH_NUDGE=""
if [[ -d "$CWD/.jj" ]]; then
  # jj-colocated repo: git HEAD is detached by design, so the @{upstream} /
  # branch-tracking checks below report nonsense here. Muster jj's own
  # stranded-work signals instead (dirty @, unpushed bookmarks, unnamed local
  # work). Script lives in the workspace container; guarded so a missing one
  # just means no jj nudge.
  _MUSTER="$HOME/Projects/scripts/ops/jj_muster.sh"
  if [[ -x "$_MUSTER" ]]; then
    _JJ=$(bash "$_MUSTER" "$CWD" 2>/dev/null | sed $'s/\x1b\\[[0-9;]*m//g')
    [[ -n "$_JJ" && "$_JJ" != *"nothing stranded"* ]] && \
      GIT_PUSH_NUDGE="⚠ jj muster — work that could be stranded:"$'\n'"${_JJ}"
  fi
elif git -C "$CWD" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  UNCOMMITTED=$(git -C "$CWD" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  BRANCH=$(git -C "$CWD" rev-parse --abbrev-ref HEAD 2>/dev/null)
  if (( UNCOMMITTED > 0 )); then
    GIT_NUDGE="⚠ ${UNCOMMITTED} uncommitted on ${BRANCH} — review before stepping away."
  fi
  # Unpushed commits: only meaningful when the branch actually tracks a remote.
  if git -C "$CWD" rev-parse --abbrev-ref '@{upstream}' >/dev/null 2>&1; then
    AHEAD=$(git -C "$CWD" rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo 0)
    (( AHEAD > 0 )) && GIT_PUSH_NUDGE="⚠ ${AHEAD} commit(s) on ${BRANCH} exist only on this machine — git push."
  else
    HAS_REMOTE=$(git -C "$CWD" remote 2>/dev/null | head -1)
    LOCAL_COMMITS=$(git -C "$CWD" rev-list --count HEAD 2>/dev/null || echo 0)
    if [[ -n "$HAS_REMOTE" ]]; then
      GIT_PUSH_NUDGE="⚠ ${BRANCH} tracks no upstream — git push -u origin ${BRANCH}."
    elif (( LOCAL_COMMITS > 0 )); then
      GIT_PUSH_NUDGE="⚠ this repo has no remote — ${LOCAL_COMMITS} commit(s) exist nowhere else."
    fi
  fi
fi

# Open intent row for today — session-journal Phase 0 records the stated ask in
# docs/journal/INTENTS.md with outcome "—"; closing out sets it. Only nudges
# when a row for today is still open, so it's silent on sessions that never
# opened one.
INTENT_NUDGE=""
_INTENTS="$HOME/Projects/docs/journal/INTENTS.md"
if [[ -f "$_INTENTS" ]] && grep -qE "^\| *$(date '+%Y-%m-%d') *\|.*\| *— *\|" "$_INTENTS" 2>/dev/null; then
  INTENT_NUDGE="◑ INTENTS.md has an open row from today — set its outcome (as-stated / diverged / abandoned) before you go."
fi

lines=()
lines+=("◆ SESSION END $(date '+%Y-%m-%d %H:%M') | ${PROJECT} | ${TOOL_CALLS} tools | ${TOTAL_CHANGES} file changes")

if (( TOTAL_CHANGES == 0 && TOOL_CALLS < 5 )); then
  lines+=("Light session — no memory save needed.")
  [[ -n "$GIT_NUDGE" ]]      && lines+=("$GIT_NUDGE")
  [[ -n "$GIT_PUSH_NUDGE" ]] && lines+=("$GIT_PUSH_NUDGE")
  [[ -n "$INTENT_NUDGE" ]]   && lines+=("$INTENT_NUDGE")
else
  (( TOTAL_CHANGES > 0 )) && lines+=("${EDITS} edits, ${WRITES} writes — consider what's non-obvious from the diff.")
  (( TOOL_CALLS >= 15 ))  && lines+=("Heavy session — likely contains design decisions worth preserving.")
  [[ -n "$GIT_NUDGE" ]]      && lines+=("$GIT_NUDGE")
  [[ -n "$GIT_PUSH_NUDGE" ]] && lines+=("$GIT_PUSH_NUDGE")
  [[ -n "$INTENT_NUDGE" ]]   && lines+=("$INTENT_NUDGE")

  # Memory is topic-scoped, not per-project: an index plus named files, written
  # by Claude Code itself. Point at what is actually on disk rather than guessing
  # a filename from the project name.
  if [[ -d "$MEMORY_DIR" ]]; then
    lines+=("")
    lines+=("Memory targets:")
    lines+=("  Index: ${MEMORY_DIR}/MEMORY.md")
    for m in "${MEMORY_DIR}"/*.md(N); do
      [[ "$(basename "$m")" == "MEMORY.md" ]] && continue
      lines+=("  $(basename "$m")")
    done
  fi
fi

# Clean up session memory injection flags
[[ -n "$SESSION_ID" ]] && rm -f /tmp/claude-ctx/mem-${SESSION_ID}-*(N) 2>/dev/null

# Emit JSON systemMessage
MSG="${(j:\n:)lines}"
printf '%s' "$MSG" | jq -Rs '{"systemMessage": .}'
