#!/bin/zsh
# on-prompt.sh v4 — UserPromptSubmit hook
# v4 (2026-07-25): dropped tier-2 memory injection — Claude Code's own auto-memory
#     now loads MEMORY.md at session start and recalls memory files on demand, so
#     injecting them here duplicated context. The MEM_MAP it used had also rotted:
#     it pointed at praxis.md / secure-pride.md (neither exists) under project keys
#     that no longer match any directory (ContextSynapse, aegis-dns).
# v3: portable MEMORY_DIR derivation (no hardcoded username)
# Tier 1 (always): classify + signal. Tier 2 (conditional): git context.

# ── JSON parsing (jq fast path, python3 fallback) ────────────────────────────
INPUT=$(cat 2>/dev/null)
_jval() {
  if command -v jq &>/dev/null; then
    printf '%s' "$INPUT" | jq -r --arg k "$1" '.[$k] // empty' 2>/dev/null
  else
    printf '%s' "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$1',''))" 2>/dev/null
  fi
}

PROMPT=$(_jval prompt)
CWD=$(_jval cwd)
SESSION_ID=$(_jval session_id)
[[ -z "$CWD" ]] && CWD="$PWD"

# ── Project resolution — worktree-aware ──────────────────────────────────────
if [[ "$CWD" =~ "\.claude-worktrees" ]]; then
  PROJECT=$(basename "${CWD%%/.claude-worktrees*}")
else
  PROJECT=$(basename "$CWD")
fi

# ═══════════════════════════════════════════════════════════════════════════════
# TIER 1 — fast path, pure zsh
# ═══════════════════════════════════════════════════════════════════════════════

P="${PROMPT:l}"

# Continuation fast-exit — saves full tier-2 cost for follow-up prompts
continuation_phrases=("and also" "one more thing" "also," "nevermind" "scratch that" "wait," "forget that" "ignore that")
for phrase in "${continuation_phrases[@]}"; do
  if [[ "$P" == ${phrase}* && ${#PROMPT} -lt 80 ]]; then
    echo "↩ ${PROJECT} | continuation"
    exit 0
  fi
done

# ── Scoring classifier — each bucket accumulates independent signal weight ────
integer s_plan=0 s_impl=0 s_refact=0 s_debug=0 s_review=0 s_read=0

# plan/architecture
[[ "$P" =~ plan ]]         && (( s_plan  += 3 ))
[[ "$P" =~ design ]]       && (( s_plan  += 3 ))
[[ "$P" =~ architect ]]    && (( s_plan  += 3 ))
[[ "$P" =~ strategy ]]     && (( s_plan  += 2 ))
[[ "$P" =~ approach ]]     && (( s_plan  += 2 ))
[[ "$P" =~ "how should" ]] && (( s_plan  += 2 ))
[[ "$P" =~ "should we" ]]  && (( s_plan  += 2 ))
[[ "$P" =~ structure ]]    && (( s_plan  += 1 ))

# implement/build
[[ "$P" =~ implement ]]    && (( s_impl  += 3 ))
[[ "$P" =~ create ]]       && (( s_impl  += 2 ))
[[ "$P" =~ build ]]        && (( s_impl  += 2 ))
[[ "$P" =~ generate ]]     && (( s_impl  += 2 ))
[[ "$P" =~ scaffold ]]     && (( s_impl  += 3 ))
[[ "$P" =~ write ]]        && (( s_impl  += 2 ))
[[ "$P" =~ " add " ]]      && (( s_impl  += 1 ))
[[ "$P" =~ "new " ]]       && (( s_impl  += 1 ))

# refactor/restructure
[[ "$P" =~ refactor ]]     && (( s_refact += 3 ))
[[ "$P" =~ restructure ]]  && (( s_refact += 3 ))
[[ "$P" =~ reorganize ]]   && (( s_refact += 3 ))
[[ "$P" =~ optimize ]]     && (( s_refact += 2 ))
[[ "$P" =~ "clean up" ]]   && (( s_refact += 2 ))
[[ "$P" =~ migrate ]]      && (( s_refact += 2 ))
[[ "$P" =~ improve ]]      && (( s_refact += 1 ))
[[ "$P" =~ "move " ]]      && (( s_refact += 1 ))

# debug/fix
[[ "$P" =~ debug ]]         && (( s_debug += 3 ))
[[ "$P" =~ " fix " ]]       && (( s_debug += 2 ))
[[ "$P" =~ "^fix" ]]        && (( s_debug += 2 ))
[[ "$P" =~ error ]]         && (( s_debug += 2 ))
[[ "$P" =~ " bug " ]]       && (( s_debug += 3 ))
[[ "$P" =~ broken ]]        && (( s_debug += 3 ))
[[ "$P" =~ failing ]]       && (( s_debug += 2 ))
[[ "$P" =~ crash ]]         && (( s_debug += 3 ))
[[ "$P" =~ "not working" ]] && (( s_debug += 3 ))
[[ "$P" =~ wrong ]]         && (( s_debug += 2 ))
[[ "$P" =~ issue ]]         && (( s_debug += 1 ))

# review/audit
[[ "$P" =~ review ]]   && (( s_review += 3 ))
[[ "$P" =~ audit ]]    && (( s_review += 3 ))
[[ "$P" =~ security ]] && (( s_review += 2 ))
[[ "$P" =~ verify ]]   && (( s_review += 2 ))
[[ "$P" =~ assess ]]   && (( s_review += 2 ))
[[ "$P" =~ inspect ]]  && (( s_review += 2 ))
[[ "$P" =~ "check " ]] && (( s_review += 1 ))

# read/explain
[[ "$P" =~ explain ]]        && (( s_read += 3 ))
[[ "$P" =~ "what is" ]]      && (( s_read += 3 ))
[[ "$P" =~ "what are" ]]     && (( s_read += 3 ))
[[ "$P" =~ "how does" ]]     && (( s_read += 3 ))
[[ "$P" =~ "why " ]]         && (( s_read += 2 ))
[[ "$P" =~ describe ]]       && (( s_read += 2 ))
[[ "$P" =~ "tell me" ]]      && (( s_read += 2 ))
[[ "$P" =~ understand ]]     && (( s_read += 2 ))
[[ "$P" =~ "what was" ]]     && (( s_read += 2 ))
[[ "$P" =~ "show me" ]]      && (( s_read += 1 ))
[[ "$P" =~ "can you show" ]] && (( s_read += 2 ))

# ── Winner selection ──────────────────────────────────────────────────────────
TASK="general"; BUDGET="medium"; BAR="███░░"
HINT="Standard depth. Explore briefly before acting."

best=$s_plan
TASK="plan"; BUDGET="critical"; BAR="█████"
HINT="Architecture/planning — weigh tradeoffs deeply. Use EnterPlanMode if scope is broad."

(( s_impl   > best )) && { best=$s_impl;   TASK="implement"; BUDGET="high";   BAR="████░"; HINT="Implementation — full depth. Thorough exploration, complete output." }
(( s_refact > best )) && { best=$s_refact; TASK="refactor";  BUDGET="high";   BAR="████░"; HINT="Refactor — analyze broadly before changing. Show full impact context." }
(( s_debug  > best )) && { best=$s_debug;  TASK="debug";     BUDGET="medium"; BAR="███░░"; HINT="Debug — systematic diagnosis. Concise once root cause is found." }
(( s_review > best )) && { best=$s_review; TASK="review";    BUDGET="medium"; BAR="███░░"; HINT="Review — thorough but skip narrating obvious findings." }
(( s_read   > best )) && { best=$s_read;   TASK="read";      BUDGET="low";    BAR="██░░░"; HINT="Read/explain — answer directly. No preamble, no recap." }
(( best == 0 ))       && { TASK="general"; BUDGET="medium";  BAR="███░░"; HINT="Standard depth. Explore briefly before acting." }

# ── Tier 1 output ─────────────────────────────────────────────────────────────
echo "◆ ${PROJECT} | ${TASK} | ${BAR} ${BUDGET}"
echo ""
echo "token-budget:${BUDGET}  task:${TASK}  project:${PROJECT}"
echo "${HINT}"

# ═══════════════════════════════════════════════════════════════════════════════
# TIER 2 — conditional enrichment (skipped for low-budget tasks)
# ═══════════════════════════════════════════════════════════════════════════════

[[ "$BUDGET" == "low" ]] && exit 0

# Memory injection lived here through v3. Claude Code now loads MEMORY.md itself
# at session start and surfaces individual memory files on recall, so re-reading
# them here only spent context twice. Removed in v4.

# Git context for high-stakes tasks
if [[ "$TASK" == "implement" || "$TASK" == "refactor" || "$TASK" == "plan" ]]; then
  BRANCH=$(git -C "$CWD" rev-parse --abbrev-ref HEAD 2>/dev/null)
  if [[ -n "$BRANCH" && "$BRANCH" != "HEAD" ]]; then
    CHANGED=$(git -C "$CWD" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    (( CHANGED > 0 )) && GIT_STATE="${CHANGED} uncommitted" || GIT_STATE="clean"
    echo ""
    echo "git:${BRANCH}  ${GIT_STATE}"
  fi
fi
