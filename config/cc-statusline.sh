#!/bin/zsh
# cc-statusline — Claude Code project orientation + skill hints

INPUT=$(< /dev/stdin)
[[ -z "$INPUT" ]] && exit 0

# Single jq pass — all fields at once
IFS=$'\t' read -r CWD CTX_USED CTX_MAX < <(
  printf '%s' "$INPUT" | jq -r '[
    (.cwd // ""),
    ((.context_window.used_tokens // .context_window.input_tokens // 0) | tostring),
    ((.context_window.max_tokens // 200000) | tostring)
  ] | join("\t")' 2>/dev/null
)
[[ -z "$CWD" ]] && exit 0

# CWD → project key, relative to the workspace root.
# ~/Code is a symlink to ~/Projects and Claude Code reports the resolved path,
# so stripping only "$HOME/Code/" never matched anything. Strip either form.
if [[ "$CWD" == */.claude-worktrees/* ]]; then
  PROJECT=$(basename "${CWD%%/.claude-worktrees*}")
else
  REL="${CWD#$HOME/Projects}"   # no trailing slash, so the bare root maps too
  REL="${REL#$HOME/Code}"
  REL="${REL#/}"
  case "$REL" in
    blog/mazze-leczzare-blog*)     PROJECT="blog" ;;
    secure-pride/secure-pride*)    PROJECT="secure-pride" ;;
    cognitive/praxis-aegis*)       PROJECT="praxis-aegis" ;;
    cognitive/context-synapse*)    PROJECT="context-synapse" ;;
    cognitive/daedalus-switch*)    PROJECT="daedalus-switch" ;;
    cognitive/stratum*)            PROJECT="stratum" ;;
    tools/stele*)                  PROJECT="stele" ;;
    tools/adaptive-response*)      PROJECT="adaptive-response" ;;
    tools/meridian*)               PROJECT="meridian" ;;
    apps/Tennis919-app*)           PROJECT="Tennis919-app" ;;
    skills/claude-code-skills*)    PROJECT="claude-code-skills" ;;
    "")                            PROJECT="workspace" ;;
    *)                             PROJECT=$(basename "$CWD") ;;
  esac
fi

# Project → skill hints. Names are the skills actually installed as of
# 2026-07-25 — the previous set named skills that no longer exist
# (superpowers:*, cloudflare:wrangler, revise-claude-md), so it suggested
# things that could not be invoked.
typeset -A HINTS
HINTS=(
  blog               "run-mazze-leczzare-blog · web-perf · ship"
  secure-pride       "security-review · touchstone · ship"
  praxis-aegis       "session-journal · touchstone · ship"
  context-synapse    "touchstone · session-journal"
  daedalus-switch    "update-config"
  stratum            "session-journal · ship"
  stele              "claude-api · ship"
  adaptive-response  "cloudflare · touchstone"
  meridian           "touchstone"
  Tennis919-app      "ship"
  claude-code-skills "update-config · ship"
  workspace          "workspace-sync · disk-audit"
)

# Git state (non-blocking)
BRANCH=$(git -C "$CWD" rev-parse --abbrev-ref HEAD 2>/dev/null)
DIRTY=$(git -C "$CWD" status --porcelain 2>/dev/null | wc -l | tr -d ' ')

# Context window bar
CTX_BAR="" CTX_LABEL=""
if (( CTX_MAX > 0 && CTX_USED > 0 )); then
  PCT=$(( CTX_USED * 100 / CTX_MAX ))
  FILLED=$(( PCT * 5 / 100 ))
  for (( i = 0; i < 5; i++ )); do
    (( i < FILLED )) && CTX_BAR+="▓" || CTX_BAR+="░"
  done
  CTX_LABEL="  ${CTX_BAR} ${PCT}%"
fi

# Assemble output
GIT=""
[[ -n "$BRANCH" && "$BRANCH" != "HEAD" ]] && GIT=" · ${BRANCH}"
(( DIRTY > 0 )) && GIT+=" [${DIRTY}]"

HINT="${HINTS[$PROJECT]:-}"
if [[ -n "$HINT" ]]; then
  printf '%s%s%s\n→  %s' "$PROJECT" "$GIT" "$CTX_LABEL" "$HINT"
else
  printf '%s%s%s' "$PROJECT" "$GIT" "$CTX_LABEL"
fi
