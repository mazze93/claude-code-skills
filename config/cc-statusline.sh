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

# CWD → project key (match relative to ~/Code/ to avoid username collision)
if [[ "$CWD" == */.claude-worktrees/* ]]; then
  PROJECT=$(basename "${CWD%%/.claude-worktrees*}")
else
  REL="${CWD#$HOME/Code/}"
  case "$REL" in
    secure-pride/secure-pride-site*) PROJECT="secure-pride" ;;
    cognitive/praxis-aegis*)         PROJECT="praxis-aegis" ;;
    cognitive/ContextSynapse*)       PROJECT="context-synapse" ;;
    cognitive/daedalus*)             PROJECT="daedalus" ;;
    tools/stele*)                    PROJECT="stele" ;;
    secure-pride/aegis-icons*)       PROJECT="aegis-icons" ;;
    blog*)                           PROJECT="blog" ;;
    adaptive-response*)              PROJECT="adaptive-response" ;;
    *)                               PROJECT=$(basename "$CWD") ;;
  esac
fi

# Project → skill hints
# Abbreviated: brainstorm=superpowers:brainstorming, tdd=test-driven-development,
#   debug=systematic-debugging, plan=writing-plans, exec=executing-plans,
#   verify=verification-before-completion, sec-review=security-review,
#   commit-pr=commit-push-pr, config=update-config, revise-md=revise-claude-md,
#   cf=cloudflare:cloudflare, wrangler=cloudflare:wrangler
typeset -A HINTS
HINTS=(
  secure-pride      "brainstorm · sec-review · commit-pr"
  praxis-aegis      "plan · exec · verify · commit"
  context-synapse   "debug · tdd · verify"
  daedalus          "config · revise-md"
  stele             "claude-api · plan · commit-pr"
  aegis-icons       "brainstorm · commit"
  blog              "cf · brainstorm · commit-pr"
  adaptive-response "cf · wrangler · tdd"
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
