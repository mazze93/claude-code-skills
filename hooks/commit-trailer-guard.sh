#!/usr/bin/env bash
# commit-trailer-guard.sh v1 — PreToolUse on Bash. Denies a `git commit`
# whose message would land without mazze's name on it.
#
# Why: mazze's global CLAUDE.md requires every commit Claude writes to carry
# `Signed-off-by: Mazze LeCzzare Frazer`, but Claude Code's own attribution
# reminder lists only Claude's lines and says not to add others. The two
# conflict on every commit; a rule held only in memory loses that conflict
# sooner or later. Replaying 788 real transcript commits found 181 without it.
#
#   git commit whose message lacks the Signed-off-by line          -> DENY
#   anything else                                                  -> silent
#
# Where the Signed-off-by line may come from: the command text (-m, heredoc,
# -F - <<EOF), -s/--signoff (git builds it from user.name), a -F/--file
# message file, or the reused message of --no-edit (HEAD) /
# -C/-c/--reuse-message (that rev). Paths and revs resolve in the repo the
# command commits in (git -C dir, else the last `cd dir`, else the hook's cwd).
#
# Not checked: author/committer email. A noreply check was drafted and
# dropped on 2026-11-26: GitHub accepted CLI pushes with the real address
# that day, so it would have denied 143 of 788 real commits for nothing.
#
# Tests: bash hooks/tests/commit-trailer-guard.test.sh
#
# Fails CLOSED for commits only: if jq is missing or the input can't be read
# and the raw input mentions git commit, it denies. Non-commit commands are
# never blocked by a failure here.
#
# Known gaps (accepted): lexical only. A commit run from a script file, an
# alias, `git -c alias.x=commit x`, or a variable-built command is not seen.
# A message that opens an editor (no -m/-F) can't be read and is denied.
# Commits made through the GitHub gateway are authored by mazze's account
# server-side and are out of scope by design.
set -uo pipefail

SIGNOFF='Signed-off-by: Mazze LeCzzare Frazer'

deny() {
  local reason="commit-trailer-guard: $1"
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg r "$reason" \
      '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  else
    reason="${reason//\\/\\\\}"; reason="${reason//\"/\\\"}"
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
  fi
  exit 0
}

input="$(cat)"
mentions_commit() { printf '%s' "$1" | grep -Eq 'git[^;&|]*[[:space:]]commit([^-[:alnum:]]|$)'; }

if ! command -v jq >/dev/null 2>&1; then
  mentions_commit "$input" && deny "jq is not on PATH, so this git commit could not be checked. Restore jq and retry."
  exit 0
fi
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)" || cmd=""
cwd="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)" || cwd=""
if [[ -z "$cmd" ]]; then
  mentions_commit "$input" && deny "could not read the command from the hook input, and it mentions git commit."
  exit 0
fi
[[ -n "$cwd" ]] || cwd="$PWD"

# Heredoc bodies and multi-line quoted strings are data (a README being written,
# a PR body), not commands: blank them before looking for commands, except a
# heredoc fed to a shell (`bash <<EOF`, `cat <<EOF | sh` run their body; a
# shell counts only at command position, so `cat > x.sh <<EOF` is text). Newlines
# are kept so line numbers still line up. The Signed-off-by check below still
# reads the raw command, where the message text lives.
y="$(printf '%s\n' "$cmd" | perl -0777 -pe '
  s/(^[^\n]*?)(?<!<)(<<-?[ \t]*(["\x27]?)([A-Za-z_][A-Za-z0-9_]*)\3[^\n]*\n)(.*?)(^[ \t]*\4[ \t]*$)/do { my ($pre, $hd, $body, $end) = ($1, $2, $5, $6); ("$pre$hd" =~ m{(?:^|[;&|(`]|\$\()\s*(?:(?:sudo|env|exec|command)\s+)*(?:\S*\/)?(?:bash|sh|zsh|ksh|dash)(?![^\s;&|)])}m) ? "$pre$hd$body$end" : $pre . $hd . ($body =~ tr|\n||cdr) . $end }/gsme;
  s/"((?:[^"\\\n]|\\.)*\n(?:[^"\\]|\\.)*)"/"\"" . ($1 =~ tr|\n||cdr) . "\""/gse;
  s/\x27([^\x27\n]*\n[^\x27]*)\x27/"\x27" . ($1 =~ tr|\n||cdr) . "\x27"/gse;
' 2>/dev/null)" || y="$cmd"
[[ -n "$y" ]] || y="$cmd"

# ── Is there a `git commit` at command position? ──────────────────────────────
START='(^|[;&|({`]|\$\()[[:space:]]*'
ASSIGN='([A-Za-z_][A-Za-z0-9_]*=("[^"]*"|'"'[^']*'"'|[^[:space:]]*)[[:space:]]+)*'
GITOPTS='([[:space:]]+(-[cC][[:space:]]+[^[:space:]]+|--?[[:alnum:]-]+(=[^[:space:]]+)?))*'
COMMIT_RE="${START}(env[[:space:]]+)?${ASSIGN}git${GITOPTS}[[:space:]]+commit([[:space:]]|\$|[;&|)])"
printf '%s\n' "$y" | grep -Eq "$COMMIT_RE" || exit 0

# Quoted strings stripped (per line), for flag scanning only.
x="$(printf '%s\n' "$y" | sed -E -e 's/"[^"]*"/QSTR/g' -e "s/'[^']*'/QSTR/g")"
# Arguments after `commit` on the commit line.
args="$(printf '%s\n' "$x" | grep -E 'git.*[[:space:]]commit([[:space:]]|$)' | head -1 \
  | sed -E 's/.*[[:space:]]commit([[:space:]]|$)/ /')"
raw_args="$(printf '%s\n' "$y" | grep -E 'git.*[[:space:]]commit([[:space:]]|$)' | head -1 \
  | sed -E 's/.*[[:space:]]commit([[:space:]]|$)/ /')"
# Message values are text, not flags: `-m "see -C HEAD"` must not read as -C.
raw_args="$(printf '%s\n' "$raw_args" | sed -E \
  "s/(^|[[:space:]])(-[[:alpha:]]*m|--message)(=|[[:space:]]+)?(\"[^\"]*\"|'[^']*'|[^[:space:]]+)/\\1/g")"
has_msg=""; printf '%s\n' "$args" | grep -Eq '(^|[[:space:]])(-[[:alpha:]]*[mF]|--message|--file)([=[:space:]]|$)' && has_msg=yes

unquote() { local v="$1"; v="${v#\"}"; v="${v%\"}"; v="${v#\'}"; v="${v%\'}"; printf '%s' "$v"; }
resolve() {  # resolve path $2 against dir $1
  local p; p="$(unquote "$2")"
  [[ "$p" == "~" || "$p" == "~/"* ]] && p="$HOME${p#\~}"
  [[ "$p" == /* ]] && printf '%s' "$p" || printf '%s/%s' "$1" "$p"
}

# ── Which repo does it commit in? ─────────────────────────────────────────────
dir="$cwd"
QV='("[^"]*"|'"'[^']*'"'|[^[:space:];&|)]+)'
cdp="$(printf '%s\n' "$y" | grep -oE "(^|[;&|(])[[:space:]]*cd[[:space:]]+${QV}" | tail -1 \
  | sed -E 's/^[;&|(]?[[:space:]]*cd[[:space:]]+//')"
[[ -n "$cdp" ]] && dir="$(resolve "$dir" "$cdp")"
gcp="$(printf '%s\n' "$y" | grep -oE "git[[:space:]]+-C[[:space:]]+${QV}" | tail -1 \
  | sed -E 's/^git[[:space:]]+-C[[:space:]]+//')"
[[ -n "$gcp" ]] && dir="$(resolve "$dir" "$gcp")"
gitd() { git -C "$dir" "$@" 2>/dev/null; }

# ── Check 1: Signed-off-by ────────────────────────────────────────────────────
signed=""
if printf '%s' "$cmd" | grep -Fq "$SIGNOFF"; then
  signed=yes
elif printf '%s\n' "$args" | grep -Eq '(^|[[:space:]])(--signoff|-[[:alpha:]]*s[[:alpha:]]*)([[:space:]]|$)'; then
  name="$(gitd config user.name)"
  [[ "$name" == "Mazze LeCzzare Frazer" ]] && signed=yes
fi
if [[ -z "$signed" ]]; then
  ffile="$(printf '%s\n' "$raw_args" | grep -oE "(^|[[:space:]])(-F|--file)(=|[[:space:]]+)${QV}" | tail -1 \
    | sed -E 's/^[[:space:]]*(-F|--file)(=|[[:space:]]+)//')"
  if [[ -n "$ffile" && "$(unquote "$ffile")" != "-" ]]; then
    f="$(resolve "$dir" "$ffile")"
    [[ -r "$f" ]] && grep -Fq "$SIGNOFF" "$f" && signed=yes
  fi
fi
if [[ -z "$signed" ]]; then
  rev=""
  if [[ -z "$has_msg" ]] && printf '%s\n' "$args" | grep -Eq '(^|[[:space:]])--no-edit([[:space:]]|$)'; then
    if printf '%s\n' "$args" | grep -Eq '(^|[[:space:]])--amend([[:space:]]|$)'; then
      rev=HEAD
    else  # finishing a merge/cherry-pick: git uses MERGE_MSG, not HEAD
      mm="$(gitd rev-parse --git-path MERGE_MSG)"
      [[ -n "$mm" && "$mm" != /* ]] && mm="$dir/$mm"
      [[ -n "$mm" && -r "$mm" ]] && grep -Fq "$SIGNOFF" "$mm" && signed=yes
    fi
  fi
  r="$(printf '%s\n' "$raw_args" | grep -oE "(^|[[:space:]])(-C|-c|--reuse-message|--reedit-message)(=|[[:space:]]+)${QV}" | tail -1 \
    | sed -E 's/^[[:space:]]*(-C|-c|--reuse-message|--reedit-message)(=|[[:space:]]+)//')"
  [[ -n "$r" ]] && rev="$(unquote "$r")"
  # The rev comes from the command text: a dashed token (`-C --output=/path`)
  # would be an option to git log and write files before any approval. Reject
  # it, resolve to a commit id first, and hand git log only that id.
  if [[ -n "$rev" && "$rev" != -* ]]; then
    sha="$(gitd rev-parse --verify --quiet "${rev}^{commit}")"
    if [[ "$sha" =~ ^[0-9a-f]{40,64}$ ]] && gitd log -1 --format=%B "$sha" | grep -Fq "$SIGNOFF"; then signed=yes; fi
  fi
fi
[[ -n "$signed" ]] || deny "this commit message has no '$SIGNOFF <mazze@mazzeleczzare.com>' line. mazze's CLAUDE.md requires it on every commit Claude writes, above the Co-Authored-By line. Add it to the message (or pass -s) and retry."

exit 0
