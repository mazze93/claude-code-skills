#!/bin/zsh
# post-tool-use.sh v1 — PostToolUse hook, matcher: Edit|Write
# Lightweight antipattern scanner + project-aware validation reminder.
# Fast: grep only, no builds. Returns JSON systemMessage on findings; exits silently otherwise.

command -v jq >/dev/null || exit 0

INPUT=$(cat 2>/dev/null)
_jval() { printf '%s' "$INPUT" | jq -r --arg k "$1" '.[$k] // empty' 2>/dev/null; }

TOOL=$(_jval tool_name)
[[ "$TOOL" == "Edit" || "$TOOL" == "Write" ]] || exit 0

FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null)
[[ -z "$FILE" || ! -f "$FILE" ]] && exit 0

CWD=$(_jval cwd)
[[ -z "$CWD" ]] && CWD="$PWD"

WARNINGS=()

# ── innerHTML antipattern — variable assignment (CLAUDE.md hard stop) ──────────
if [[ "$FILE" =~ \.(js|ts|jsx|tsx|mjs|cjs)$ ]]; then
  if grep -qE 'innerHTML\s*[+]?=\s*[^"'"'"'`]' "$FILE" 2>/dev/null; then
    WARNINGS+=("⚠ innerHTML assignment with non-literal RHS in $(basename $FILE) — use textContent or a vetted sanitizer (CLAUDE.md hard stop)")
  fi
fi

# ── Linux /home/ path — wrong OS (macOS uses /Users/) ─────────────────────────
if grep -qE '"/home/[a-z_-]+/' "$FILE" 2>/dev/null; then
  WARNINGS+=("⚠ Linux /home/ path in $(basename $FILE) — this machine uses /Users/\$USER or \$HOME")
fi

# ── SQL string interpolation — parameterized queries only ────────────────────
if [[ "$FILE" =~ \.(py|ts|js|rb|go|swift)$ ]]; then
  if grep -qE '(execute|query|run)\s*\(\s*f["\x27]|\.format\s*\(|%\s*\(' "$FILE" 2>/dev/null; then
    WARNINGS+=("⚠ Possible SQL string interpolation in $(basename $FILE) — use parameterized queries (CLAUDE.md hard stop)")
  fi
fi

# ── Project-aware validation reminder ────────────────────────────────────────
if [[ "${#WARNINGS[@]}" -gt 0 ]]; then
  if [[ "$CWD" =~ "/blog" ]]; then
    WARNINGS+=("→ Validate: npm run check")
  elif [[ "$CWD" =~ "/meridian" ]]; then
    WARNINGS+=("→ Validate: swift build")
  elif [[ "$CWD" =~ "/secure-pride" || "$CWD" =~ "/praxis-aegis" ]]; then
    WARNINGS+=("→ Validate before shipping — MAX posture project")
  fi
fi

[[ "${#WARNINGS[@]}" -eq 0 ]] && exit 0

MSG="${(j:\n:)WARNINGS}"
printf '%s' "$MSG" | jq -Rs '{"systemMessage": .}'
