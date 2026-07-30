#!/usr/bin/env zsh
# run-pr-triage.sh — Discover all mazze93 repos with open PRs, then run triage.
#
# Usage:
#   ./run-pr-triage.sh                     # terminal output
#   ./run-pr-triage.sh --render slack      # Slack JSON (pipe to webhook)
#   ./run-pr-triage.sh --render github     # GitHub Markdown
#   ./run-pr-triage.sh --output report.md  # Write to file
#
# Requirements: gh CLI installed + authenticated (gh auth login)

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
CONFIG_FILE="${SCRIPT_DIR}/.claude/pr-triage.json"

# ── Preflight ────────────────────────────────────────────────────────────────

if ! command -v gh &>/dev/null; then
  print -u2 "[pr-triage] gh CLI not found. Install: brew install gh"
  exit 1
fi

if ! gh auth status &>/dev/null; then
  print -u2 "[pr-triage] Not authenticated. Run: gh auth login"
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  print -u2 "[pr-triage] python3 not found. Install: brew install python"
  exit 1
fi

# ── Discover repos with open PRs ────────────────────────────────────────────

print -u2 "[pr-triage] Discovering mazze93 repos with open PRs..."

# Fetch all repos for the mazze93 account (limit 200 covers most cases)
ALL_REPOS=$(gh repo list mazze93 --limit 200 --json nameWithOwner --jq '.[].nameWithOwner' 2>/dev/null)

if [[ -z "$ALL_REPOS" ]]; then
  print -u2 "[pr-triage] No repos found for mazze93. Check: gh auth status"
  exit 1
fi

REPO_COUNT=$(echo "$ALL_REPOS" | wc -l | tr -d ' ')
print -u2 "[pr-triage] Found ${REPO_COUNT} repos. Checking for open PRs..."

# Filter to only repos that have at least one open PR (parallel, silent errors)
REPOS_WITH_PRS=()
while IFS= read -r repo; do
  count=$(gh pr list --repo "$repo" --state open --limit 1 --json number --jq 'length' 2>/dev/null || echo 0)
  if [[ "$count" -gt 0 ]]; then
    REPOS_WITH_PRS+=("\"$repo\"")
  fi
done <<< "$ALL_REPOS"

if [[ ${#REPOS_WITH_PRS[@]} -eq 0 ]]; then
  print -u2 "[pr-triage] No open PRs found across any mazze93 repos."
  exit 0
fi

print -u2 "[pr-triage] ${#REPOS_WITH_PRS[@]} repo(s) have open PRs."

# ── Build temp config ────────────────────────────────────────────────────────

REPO_JSON=$(IFS=,; echo "${REPOS_WITH_PRS[*]}")
TEMP_CONFIG=$(mktemp /tmp/pr-triage-XXXXXX.json)
trap "rm -f ${TEMP_CONFIG}" EXIT

cat > "$TEMP_CONFIG" <<EOF
{
  "repos": [${REPO_JSON}],
  "reviewer_response_hours": 48,
  "abandon_days": 5,
  "staleness_warning_days": 3,
  "render": "terminal"
}
EOF

# ── Run triage ───────────────────────────────────────────────────────────────

PYTHONPATH="${SCRIPT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" python3 "${SCRIPT_DIR}/pr_triage.py" --config "$TEMP_CONFIG" "$@"
