#!/usr/bin/env bash
# PreToolUse guard on Bash: blocks commands whose documented job is to print
# a secret (password/token) to stdout, so it never lands in the transcript.
# Scoped to the 2026-07-18 incident (git credential helpers, OS keychain
# reads) plus adjacent secret-manager CLIs, gh's own token-printing
# subcommands, raw reads of well-known credential files, and obfuscated
# decode-and-execute pipelines.
#
# Fails CLOSED: if jq is missing or the hook input can't be parsed, this
# denies the Bash call rather than silently allowing it. That is a
# deliberate tradeoff (a broken environment blocks Bash entirely until
# fixed) chosen over the alternative of a security control that goes dark
# without telling anyone.
#
# Known residual gap (accepted, not fixed here): variable/eval indirection
# split across tokens (e.g. `a=git; b=...; $a $b`) and wrapping the same
# syscall in another interpreter (python subprocess, etc.) can still evade
# plain-text matching. Closing that requires parsing shell semantics, which
# is a different (and much heavier) tool than a pattern-matching hook.
# Script-file execution is checked by absolute path only (below); a script
# referenced by a relative path isn't resolved against the real cwd here and
# so isn't inspected — narrower remaining gap than the original "any script,
# any path" hole.
set -uo pipefail

deny_plain() {
  # Pure-bash JSON emission for the path where jq itself may be unavailable.
  local reason="$1"
  reason="${reason//\\/\\\\}"
  reason="${reason//\"/\\\"}"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
}

if ! command -v jq >/dev/null 2>&1; then
  deny_plain "credential-guard: jq is not on PATH, so this hook cannot verify the command is safe. Blocking this Bash call until jq is restored (fail-closed by design)."
  exit 0
fi

input="$(cat)"
if ! cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)"; then
  jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"credential-guard: could not parse hook input as JSON. Blocking this Bash call (fail-closed by design)."}}'
  exit 0
fi

pattern='git[ -]credential(-[A-Za-z0-9_-]+)?[[:space:]]+(get|fill)'
pattern+='|security[[:space:]]+(find-(internet|generic)-password|dump-keychain)'
pattern+='|secret-tool[[:space:]]+lookup'
pattern+='|\bpass[[:space:]]+show\b'
pattern+='|\bop[[:space:]]+(read\b|item[[:space:]]+get\b.*--fields[[:space:]]+password)'
pattern+='|vault[[:space:]]+kv[[:space:]]+get'
pattern+='|gpg[[:space:]]+--export-secret-keys?'
# gh's own token-printing subcommands (relevant the moment gh is on PATH)
pattern+='|\bgh[[:space:]]+auth[[:space:]]+token\b'
pattern+='|\bgh[[:space:]]+auth[[:space:]]+status\b[^\n]*--show-token'
# env-var secret dumps
pattern+='|\b(printenv|env)\b[^\n]*\b([A-Z_]*(TOKEN|SECRET|API_KEY|PASSWORD)[A-Z_]*)\b'
pattern+='|\b(printenv|env)\b[^\n]*\|[^\n]*grep[^\n]*-i[^\n]*\b(token|secret|password|key)\b'
# raw reads of well-known credential files
pattern+='|\b(cat|less|more|head|tail|bat)\b[^\n]*(\.git-credentials|\.netrc|\.npmrc|\.pypirc|\.aws/credentials|\.docker/config\.json|\.ssh/id_[a-z0-9_]+)\b'
# obfuscated decode-and-execute pipelines (heuristic: this shape is rare in
# ordinary agent workflows and disproportionately used to hide a payload)
pattern+='|base64[[:space:]]+(-d|--decode)\b[^\n]*\|[^\n]*\b(bash|sh|zsh)\b'

# Closes the "write a script, then run it in a separate call" bypass: if
# this command executes a script file by absolute path, the file's contents
# get the same check, not just the invoking command string.
script_path=""
# NOTE: bash's [[ =~ ]] regex engine (BSD/POSIX ERE here, not PCRE) does not
# support \b — that cost a debugging round-trip. Boundaries below are done
# explicitly via (^|[;&|[:space:]]) instead.
if [[ "$cmd" =~ (^|[;\&\|[:space:]])(bash|sh|zsh|source|\.)[[:space:]]+(/[^[:space:];\&\|]+) ]]; then
  script_path="${BASH_REMATCH[3]}"
fi
script_content=""
if [[ -n "$script_path" && -f "$script_path" && -r "$script_path" ]]; then
  script_content="$(cat "$script_path" 2>/dev/null || true)"
fi

if printf '%s\n%s' "$cmd" "$script_content" | grep -Eqi "$pattern"; then
  jq -n --arg cmd "$cmd" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("Blocked by credential-guard: \"" + $cmd + "\" is designed to print a secret to stdout (or is an obfuscated pipeline shaped to hide one), which would land in the conversation transcript. Ask the user to run it themselves outside Claude Code, or use a non-printing check instead (e.g. `gh auth status` without --show-token, a dry-run, or asking the user directly).")
    }
  }'
fi
exit 0
