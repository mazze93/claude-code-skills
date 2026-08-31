#!/bin/zsh
# post-tool-use.sh v2 — PostToolUse hook, matcher: Edit|Write
# Lightweight antipattern scanner + project-aware validation reminder.
# Fast: grep only, no builds. Returns JSON systemMessage on findings; exits silently otherwise.
#
# v2 (2026-07-25):
#   - Dropped "(CLAUDE.md hard stop)" citations from the innerHTML and SQL checks.
#     The reconstructed ~/.claude/CLAUDE.md carries no such rules, so the citation
#     pointed at nothing. The checks are worth keeping on their own merits.
#   - Added a secrets check, which IS a live hard stop ("never commit or print
#     secrets/credentials/certs unmasked"). Complements credential-guard.sh:
#     that hook catches Bash commands that PRINT secrets, this catches files
#     being WRITTEN with one embedded.
#   - Rebuilt the validation map against directories that actually exist.

command -v jq >/dev/null || exit 0

INPUT=$(cat 2>/dev/null)
_jval() { printf '%s' "$INPUT" | jq -r --arg k "$1" '.[$k] // empty' 2>/dev/null; }

TOOL=$(_jval tool_name)
[[ "$TOOL" == "Edit" || "$TOOL" == "Write" ]] || exit 0

FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null)
[[ -z "$FILE" || ! -f "$FILE" ]] && exit 0

CWD=$(_jval cwd)
[[ -z "$CWD" ]] && CWD="$PWD"

# ── Container journal edited → keep the stamp + backlinks current on disk ──────
# In-session half of the journal-mechanics pair (the pre-commit hook is the
# authoritative rebuild + gate). CONTAINER ONLY: the "append at bottom" +
# "Updated:" header conventions these scripts assume are ~/Projects/docs/journal
# specific — context-synapse's journal prepends newest-first, and stratum is MAX
# posture. Pure side effect, no output.
if [[ "$FILE" == "$HOME/Projects/docs/journal/"*.md ]]; then
  for _s in journal_stamp journal_backlinks; do
    _script="$HOME/Projects/scripts/ops/${_s}.sh"
    [[ -x "$_script" ]] && bash "$_script" "$HOME/Projects/docs/journal" >/dev/null 2>&1 || true
  done
fi

WARNINGS=()

# ── innerHTML antipattern — variable assignment (CLAUDE.md hard stop) ──────────
if [[ "$FILE" =~ \.(js|ts|jsx|tsx|mjs|cjs)$ ]]; then
  if grep -qE 'innerHTML\s*[+]?=\s*[^"'"'"'`]' "$FILE" 2>/dev/null; then
    WARNINGS+=("⚠ innerHTML assignment with non-literal RHS in $(basename $FILE) — use textContent or a vetted sanitizer")
  fi
fi

# ── Linux /home/ path — wrong OS (macOS uses /Users/) ─────────────────────────
if grep -qE '"/home/[a-z_-]+/' "$FILE" 2>/dev/null; then
  WARNINGS+=("⚠ Linux /home/ path in $(basename $FILE) — this machine uses /Users/\$USER or \$HOME")
fi

# ── SQL string interpolation — parameterized queries only ────────────────────
if [[ "$FILE" =~ \.(py|ts|js|rb|go|swift)$ ]]; then
  if grep -qE '(execute|query|run)\s*\(\s*f["\x27]|\.format\s*\(|%\s*\(' "$FILE" 2>/dev/null; then
    WARNINGS+=("⚠ Possible SQL string interpolation in $(basename $FILE) — use parameterized queries")
  fi
fi

# ── Hardcoded secret — live hard stop ────────────────────────────────────────
# Deliberately narrow: assignment of a long opaque literal to a secret-ish name,
# plus unmistakable key headers. Placeholders and env lookups are excluded so
# this stays quiet enough to be worth listening to.
# Two independent signals:
#   1. a recognisable credential prefix, whatever it is assigned to
#   2. a long opaque literal assigned to a secret-ish name (case-insensitive,
#      so apiKey / API_KEY / api_key all match)
SECRET_PREFIX='(-----BEGIN [A-Z ]*PRIVATE KEY-----|\bsk-(live|proj|ant)?-?[A-Za-z0-9]{16,}|\bghp_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}|\bxox[baprs]-[A-Za-z0-9-]{10,}|\bAKIA[0-9A-Z]{16}\b)'
SECRET_NAMED='(api[_-]?key|secret|password|passwd|token|bearer|credential)[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9/+_.-]{20,}["'"'"']'
if grep -qiE "$SECRET_PREFIX" "$FILE" 2>/dev/null || grep -qiE "$SECRET_NAMED" "$FILE" 2>/dev/null; then
  if ! grep -qiE '(example|placeholder|dummy|xxx+|your[_-]|<[a-z_]+>|process\.env|import\.meta\.env|os\.environ|\$\{)' "$FILE" 2>/dev/null; then
    WARNINGS+=("⚠ Possible hardcoded secret in $(basename $FILE) — hard stop: never commit credentials unmasked. Use env/secret storage.")
  fi
fi

# ── Project-aware validation reminder ────────────────────────────────────────
# Keyed on directories that exist in ~/Projects as of 2026-07-25.
if [[ "${#WARNINGS[@]}" -gt 0 ]]; then
  case "$CWD" in
    */meridian*|*/context-synapse*)
      WARNINGS+=("→ Validate: swift build") ;;
    */mazze-leczzare-blog*|*/Tennis919-app*|*/stratum*)
      WARNINGS+=("→ Validate: npm run check") ;;
    */stele*)
      WARNINGS+=("→ Validate: npm run lint && npm test") ;;
    */secure-pride/*|*/praxis-aegis*|*/praxis-api*)
      WARNINGS+=("→ MAX posture project — verify before anything outward-facing; keep identifiers masked") ;;
  esac
fi

[[ "${#WARNINGS[@]}" -eq 0 ]] && exit 0

MSG="${(j:\n:)WARNINGS}"
printf '%s' "$MSG" | jq -Rs '{"systemMessage": .}'
