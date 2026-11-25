#!/usr/bin/env bash
# Fixture tests for hooks/rm-ask.sh.  Run: bash hooks/tests/rm-ask.test.sh
# Expectations: ASK (permissionDecision ask) or silent.
set -uo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/rm-ask.sh"
fail=0; n=0

check() {
  local want="$1" cmd="$2" out got
  out="$(jq -n --arg c "$cmd" '{tool_name:"Bash", tool_input:{command:$c}}' | bash "$HOOK")"
  if   [[ "$out" == *'"ask"'* ]]; then got=ASK
  elif [[ -z "$out" ]]; then got=silent
  else got=OTHER; fi
  n=$((n+1))
  if [[ "$got" == "$want" ]]; then printf 'ok    %-6s %s\n' "$got" "${cmd//$'\n'/⏎}"
  else printf 'FAIL  want %s got %s  %s\n' "$want" "$got" "${cmd//$'\n'/⏎}"; fail=$((fail+1)); fi
}

# ── rm at command position ────────────────────────────────────────────────────
check ASK 'rm x'
check ASK 'rm -rf build/'
check ASK 'cd a && rm -f b'
check ASK 'ls; rm x'
check ASK 'true || rm x'
check ASK 'command rm -rf x'
check ASK '/bin/rm x'
check ASK '\rm x'
check ASK 'sudo rm x'
check ASK 'sudo -n rm x'
check ASK 'FOO=1 rm x'
check ASK 'env -i rm x'
check ASK 'if true; then rm x; fi'
check ASK 'for f in *.o; do rm "$f"; done'
check ASK 'echo $(rm x)'
check ASK '( rm x )'
check ASK $'echo a\nrm b'
check ASK 'printf "%s\0" a | xargs -0 rm'
check ASK 'xargs rm < list.txt'
check ASK "bash -c 'rm -rf y'"
check ASK 'zsh -c "rm y"'
check ASK "eval 'rm y'"
check ASK 'rm'
check ASK 'sudo -u root rm x'
check ASK 'nice -n 5 rm x'
check ASK 'timeout 5 rm x'
check ASK 'env FOO=1 rm x'
check ASK $'rm\tx'
check ASK 'a&&rm x'
check ASK '{ rm x; }'
# ── find deletes ──────────────────────────────────────────────────────────────
check ASK "find . -name '*.o' -delete"
check ASK 'find . -type f -exec rm {} +'
check ASK 'find . -execdir /bin/rm -f {} \;'
# ── heredoc bodies are not stripped (bash <<EOF runs them) ────────────────────
check ASK $'bash <<EOF\nrm x\nEOF'

# ── not a delete, or rm only as text ──────────────────────────────────────────
check silent 'echo "rm x"'
check silent "printf 'rm -rf /'"
check silent 'git rm --cached f'
check silent 'git commit -m "rm stale file"'
check silent "grep -rn 'rm -rf' ."
check silent 'rmdir emptydir'
check silent 'npm rm left-pad'
check silent 'ls ~/rm-notes'
check silent 'cat rm.txt'
check silent 'rsync -a --delete a/ b/'
check silent 'git branch --delete old'
check silent 'mise rm node'
check silent 'trash x'
check silent 'ls -la'
check silent 'command -v rm'
check silent 'type rm'
check silent 'which rm'
check silent 'env | grep -c rm'

# ── fail toward ASK ───────────────────────────────────────────────────────────
n=$((n+1))
out="$(printf 'not json' | bash "$HOOK")"
if [[ "$out" == *'"ask"'* ]]; then printf 'ok    ASK    <unparseable input>\n'
else printf 'FAIL  want ASK  <unparseable input> got: %s\n' "$out"; fail=$((fail+1)); fi

n=$((n+1))
out="$(printf '{"tool_input":{"command":"ls"}}' | PATH=/var/empty /bin/bash "$HOOK")"
if [[ "$out" == *'"ask"'* ]] && printf '%s' "$out" | /usr/bin/python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null; then
  printf 'ok    ASK    <jq missing, valid JSON>\n'
else printf 'FAIL  want ASK+valid JSON  <jq missing> got: %s\n' "$out"; fail=$((fail+1)); fi

printf '\n%d/%d passed\n' "$((n-fail))" "$n"
exit $((fail>0))
