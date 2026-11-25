#!/usr/bin/env bash
# rm-ask.sh v1 — PreToolUse on Bash. Turns any `rm` into a permission prompt.
#
# Why: mazze's zsh aliases rm='rm -i'. In an agent shell nobody can answer
# rm -i: on 2026-11-24 it hung a session for 120 s on a stdin pipe held open.
# The dotfiles now drop that alias when CLAUDECODE/AI_AGENT is set, which also
# removes the soft brake on deletes. This hook puts the brake back where an
# agent can't hang on it: Claude Code's own permission prompt, which a human
# answers (or which is refused when nobody is there, e.g. `claude -p`).
#
#   Bash command that runs rm (at command position, incl. sudo/command/env/
#     xargs prefixes, \rm, /bin/rm, `-c`/eval payloads), or find -delete /
#     find -exec rm                                    -> ASK, with the reason.
#   Anything else                                      -> silent.
#
# Tests: bash hooks/tests/rm-ask.test.sh
#
# Bias: asking too often costs one click; missing a delete can cost evidence.
# So heredoc bodies are NOT stripped (`bash <<EOF` runs them) and a heredoc
# line that starts with "rm " will ask. Quoted strings outside -c/eval are
# treated as text (`git commit -m "rm stale file"` stays silent).
#
# Fails toward ASK: if the input cannot be parsed, the call asks rather than
# passing silently, because this hook replaces a safety prompt.
#
# Known gaps (accepted): lexical only. rm inside a script file, python
# (os.remove, shutil.rmtree), node, a function or alias defined earlier, or
# built through variable indirection is not seen. rsync --delete, git clean,
# unlink and truncation by redirect are out of scope. ephemeral-guard and the
# permission rules still apply on top of this.
set -uo pipefail

ask() {
  local reason="$1"
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg r "$reason" \
      '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"ask",permissionDecisionReason:$r}}'
  else
    # reason is a fixed string from this file: no characters need escaping.
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$reason"
  fi
  exit 0
}

command -v jq >/dev/null 2>&1 || ask "rm-ask: jq not on PATH, so this command could not be checked for rm. Approve only if it deletes nothing you need."

input="$(cat)"
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)" || cmd=""
[[ -n "$cmd" ]] || ask "rm-ask: could not read the command from the hook input. Approve only if it deletes nothing you need."

# Unquote -c / eval payloads (they are commands; the `;` puts their first word
# at command position), then treat every other quoted string as text.
x="$(printf '%s\n' "$cmd" | sed -E \
  -e 's/((^|[[:space:]])(-c|eval)[[:space:]]+)"([^"]*)"/\1; \4 ;/g' \
  -e "s/((^|[[:space:]])(-c|eval)[[:space:]]+)'([^']*)'/\\1; \\4 ;/g" \
  -e 's/"[^"]*"/QSTR/g' \
  -e "s/'[^']*'/QSTR/g")"

START='(^|[;&|({`]|\$\()[[:space:]]*'
WORD='[^[:space:]]+'
# Wrappers that run their trailing words as a command may take arguments of
# their own (sudo -u root, nice -n 5, timeout 5): any words may sit between
# them and rm. `command` only takes -p before a command; `command -v rm` is a
# lookup and stays silent.
LOOSE='(sudo|doas|nohup|time|nice|timeout|env|xargs|caffeinate|stdbuf)([[:space:]]+[^;&|()[:space:]]+)*'
STRICT='(command([[:space:]]+-p)?|builtin|exec|then|do|else|!)'
ASSIGN="[A-Za-z_][A-Za-z0-9_]*=${WORD}"
PREFIX="((${LOOSE}|${STRICT}|${ASSIGN})[[:space:]]+)*"
RM='\\?((/usr)?/bin/)?rm([[:space:]]|$|[;&|)])'
FIND_RM='[[:space:]]-(delete([[:space:]]|$|[;&|)])|exec(dir)?[[:space:]]+((/usr)?/bin/)?rm([[:space:]]|$))'

if printf '%s\n' "$x" | grep -Eq "${START}${PREFIX}${RM}"; then
  ask "rm-ask: this command deletes files with rm (agent shells no longer alias rm to rm -i). Check the targets before approving; deleted files do not go to the Trash."
fi
if printf '%s\n' "$x" | grep -Eq "${FIND_RM}"; then
  ask "rm-ask: this command deletes files via find -delete or find -exec rm. Check what the find matches before approving."
fi
exit 0
