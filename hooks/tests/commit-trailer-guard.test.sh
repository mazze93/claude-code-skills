#!/usr/bin/env bash
# Fixture tests for hooks/commit-trailer-guard.sh.
# Run: bash hooks/tests/commit-trailer-guard.test.sh
# Expectations: DENY (permissionDecision deny) or silent.
# Builds throwaway git repos under mktemp -d; nothing outside them is touched.
set -uo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/commit-trailer-guard.sh"
fail=0; n=0

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
REAL='mazze@mazzeleczzare.com'
NOREPLY='225266999+mazze93@users.noreply.github.com'
SO="Signed-off-by: Mazze LeCzzare Frazer <$REAL>"
NR="GIT_AUTHOR_EMAIL=$NOREPLY GIT_COMMITTER_EMAIL=$NOREPLY"

# Isolate from the machine: no global/system git config, no inherited identity.
printf '[user]\n\tname = Mazze LeCzzare Frazer\n\temail = %s\n' "$REAL" > "$T/gitconfig"
export GIT_CONFIG_GLOBAL="$T/gitconfig" GIT_CONFIG_NOSYSTEM=1
unset GIT_AUTHOR_EMAIL GIT_COMMITTER_EMAIL GIT_AUTHOR_NAME GIT_COMMITTER_NAME

mkrepo() {  # mkrepo <dir> <local email or ""> <local name or ""> <HEAD message or "">
  git init -q "$1"
  [[ -n "$2" ]] && git -C "$1" config user.email "$2"
  [[ -n "$3" ]] && git -C "$1" config user.name "$3"
  if [[ -n "$4" ]]; then
    GIT_AUTHOR_EMAIL=$NOREPLY GIT_COMMITTER_EMAIL=$NOREPLY \
      git -C "$1" commit -q --allow-empty -m "$4"
  fi
}
mkrepo "$T/real"    ""        ""             "init"$'\n\n'"$SO"   # global: real email
mkrepo "$T/nr"      "$NOREPLY" ""            ""                   # local noreply
mkrepo "$T/unsign"  ""        ""             "init, no trailer"
mkrepo "$T/other"   ""        "Someone Else" ""
printf 'subject\n\n%s\n' "$SO" > "$T/real/msg-ok.txt"
printf 'subject only\n' > "$T/real/msg-bad.txt"

check() {  # check <DENY|silent> <cwd> <command>
  local want="$1" cwd="$2" cmd="$3" out got
  out="$(jq -n --arg c "$cmd" --arg d "$cwd" '{tool_name:"Bash", cwd:$d, tool_input:{command:$c}}' | bash "$HOOK")"
  if   [[ "$out" == *'"deny"'* ]]; then got=DENY
  elif [[ -z "$out" ]]; then got=silent
  else got=OTHER; fi
  n=$((n+1))
  local shown="${cmd//$'\n'/⏎}"; shown="${shown//$T/\$T}"; shown="${shown//$NOREPLY/NOREPLY}"
  if [[ "$got" == "$want" ]]; then printf 'ok    %-6s %s\n' "$got" "$shown"
  else printf 'FAIL  want %s got %s  %s\n      %s\n' "$want" "$got" "$shown" "$out"; fail=$((fail+1)); fi
}
R="$T/real"

# ── not a commit: always silent ───────────────────────────────────────────────
check silent "$R" 'ls'
check silent "$R" 'git status'
check silent "$R" 'git log --grep commit'
check silent "$R" 'echo "git commit"'
check silent "$R" 'git commit-tree abc -m x'
check silent "$R" 'git show HEAD:hooks/commit-trailer-guard.sh'
check silent "$R" "cat > README.md <<'EOF'
Usage:
git commit -m \"message\"
EOF"
check silent "$R" "gh pr create --title t --body \"Steps:
git commit -m x
done\""
check silent "$R" "printf '%s\\n' 'first
git commit -m x'"

# ── compliant commits: silent ─────────────────────────────────────────────────
check silent "$R" "$NR git commit -m \"subject"$'\n\n'"$SO\""
check silent "$R" "$NR git commit -m \"\$(cat <<'EOF'
subject

body line

$SO
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)\""
check silent "$R" "git add -A && $NR git commit -m \"x $SO\""
check silent "$R" "export $NR; git commit -m \"x $SO\""
check silent "$R" "env $NR git commit -m \"x $SO\""
check silent "$T/nr" "git commit -m \"x $SO\""
check silent "$R" "cd $T/nr && git commit -m \"x $SO\""
check silent "$R" "git -C $T/nr commit -m \"x $SO\""
check silent "$R" "git -c user.email=$NOREPLY commit -m \"x $SO\""
check silent "$R" "$NR git commit -s -m x"
check silent "$R" "$NR git commit -sm x"
check silent "$R" "$NR git commit --signoff -m x"
check silent "$R" "$NR git commit -F msg-ok.txt"
check silent "$R" "$NR git commit --file=$R/msg-ok.txt"
check silent "$R" "$NR git commit --amend --no-edit"
check silent "$R" "$NR git commit -C HEAD"
check silent "$R" "GIT_COMMITTER_EMAIL=$NOREPLY git commit --author=\"Mazze <$NOREPLY>\" -m \"x $SO\""

# ── missing Signed-off-by: DENY ───────────────────────────────────────────────
check DENY "$R" "$NR git commit -m x"
check DENY "$R" "bash <<'EOF'
$NR git commit -m unsigned
EOF"
check DENY "$R" "zsh -s <<EOF
cd $T/real && git commit -m unsigned
EOF"
check silent "$R" "git commit -m \"x $SO\""
check silent "$T/nr" "cd $R && git commit -m \"x $SO\""
check DENY "$R" "cat > notes.md <<'EOF'
git commit -m doc-line
EOF
$NR git commit -m real-unsigned"
check DENY "$R" "ls && $NR git commit -m \"fix: thing\""
check DENY "$R" "$NR git commit -m \"Co-Authored-By: Claude <noreply@anthropic.com>\""
check DENY "$R" "$NR git commit -F msg-bad.txt"
check DENY "$R" "$NR git commit -F missing.txt"
check DENY "$T/unsign" "$NR git commit --amend --no-edit"
check DENY "$T/other" "$NR git commit -s -m x"
check DENY "$R" "$NR git commit"
check DENY "$R" "$NR git commit -m \"Signed-off-by: Someone Else <a@b.c>\""

# ── fail-closed on unreadable input only when it mentions git commit ──────────
out="$(printf 'not json git commit -m x' | bash "$HOOK")"; n=$((n+1))
[[ "$out" == *'"deny"'* ]] && echo "ok    DENY   <unparseable input mentioning git commit>" \
  || { echo "FAIL  want DENY  <unparseable input mentioning git commit>"; fail=$((fail+1)); }
out="$(printf 'not json at all' | bash "$HOOK")"; n=$((n+1))
[[ -z "$out" ]] && echo "ok    silent <unparseable input, no commit>" \
  || { echo "FAIL  want silent  <unparseable input, no commit>"; fail=$((fail+1)); }

echo
echo "$((n-fail))/$n passed"
[[ $fail -eq 0 ]]
