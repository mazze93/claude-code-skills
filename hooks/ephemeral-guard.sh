#!/usr/bin/env bash
# ephemeral-guard.sh v2 — PreToolUse on Write|Edit|NotebookEdit|Bash.
#
# Why: records kept landing in the session scratchpad or /tmp and dying with
# the session (evidence, payloads, worktrees, drafts). A CLAUDE.md rule and a
# feedback memory both existed and both lost to the harness's own default
# ("use the scratchpad for temp files"). Text competes; a hook runs every time.
#
#   Write/Edit/NotebookEdit into an ephemeral root -> DENY, with the durable
#     alternatives in the reason.
#   Bash command that WRITES into an ephemeral root -> DENY, naming the rule
#     (redirect, tee, -o, cp/mv/rsync destination, mkdir/touch, tar -C,
#     unzip -d, git clone/worktree add, mktemp, cd-into-root-then-write).
#     Variables assigned an ephemeral path are expanded first, so
#     `D=/private/tmp/x; mkdir -p $D` is caught (v1 missed exactly this: the
#     2026-11-24 PTK triage evidence went into the scratchpad via curl -o).
#     Copying OUT of /tmp into a durable place is not a write into it.
#   Bash command that otherwise mentions a root    -> allow, with a reminder
#     as additionalContext (reads, ls, harness task-output files).
#   Anything else                                  -> silent.
#
# Tests: bash hooks/tests/ephemeral-guard.test.sh
#
# Ephemeral roots: /tmp, /private/tmp (holds the session scratchpad),
# /var/folders and /private/var/folders (macOS $TMPDIR, mktemp's default).
#
# Fails OPEN (unlike credential-guard / tool-seam): this is hygiene, not a
# security control, and blocking every Write because jq broke would cost more
# than a missed reminder. The failure is still visible via systemMessage.
#
# Known gaps (accepted): matching is lexical. A path that reaches /tmp through
# `..` segments or a symlink is not resolved; writes made inside a script file,
# python, node, or via eval/indirection are not seen in the command text; a
# copy whose destination is not the last argument (`cp a /tmp/x 2>/dev/null`)
# is only warned. The thing being guarded against is a habit, not an adversary.
set -uo pipefail

if ! command -v jq >/dev/null 2>&1; then
  printf '{"systemMessage":"ephemeral-guard: jq not on PATH; /tmp and scratchpad writes are NOT being checked."}\n'
  exit 0
fi

input="$(cat)"
tool="$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null)" || tool=""
if [[ -z "$tool" ]]; then
  printf '{"systemMessage":"ephemeral-guard: could not parse hook input; this call was not checked."}\n'
  exit 0
fi

DURABLE='Durable homes: repo files in the repo; records, evidence and backups via ~/.claude/scripts/inbox-drop.sh (-> ~/Projects/inbox/<date>/); worktrees in ~/Projects/tools/worktrees/<repo>-<branch>; research in ~/Research.'

is_ephemeral_path() {
  local p="$1"
  while [[ "$p" == *//* ]]; do p="${p//\/\//\/}"; done
  case "$p" in
    /tmp|/tmp/*|/private/tmp|/private/tmp/*) return 0 ;;
    /var/folders/*|/private/var/folders/*)   return 0 ;;
  esac
  return 1
}

case "$tool" in
  Write|Edit|NotebookEdit)
    path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty')"
    if [[ -n "$path" ]] && is_ephemeral_path "$path"; then
      jq -n --arg p "$path" --arg d "$DURABLE" '{
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: ("ephemeral-guard: " + $p + " is in session-scoped/temp storage and will be lost. " + $d + " This hook cannot be overridden from inside the session: if mazze wants this temp path, they write it themselves.")
        }
      }'
    fi
    ;;
  Bash)
    cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"

    # Ephemeral root (R) and an optional quote (Q). R carries its own tail
    # boundary so /tmpfoo does not match; callers supply the leading boundary.
    Q='["'"'"']?'
    R='((/private)?/tmp([/[:space:]"'"'"'`;)|&]|$)|(/private)?/var/folders/|\$\{?TMPDIR)'
    S='(^|[;&|[:space:](])'   # start of a simple command

    # Text that is not shell syntax must not trip the rules (a commit message
    # or heredoc that merely quotes "echo > /tmp/f"). Drop heredoc bodies (the
    # `cat <<EOF > /tmp/x` header line is kept), then neutralise quoted strings
    # that contain whitespace and do not start with / or $ (a spaced path like
    # "/tmp/a b" is kept so it is still judged). Payloads of `-c` and `eval`
    # ARE commands, so they are unquoted first and judged like any other.
    x="$(printf '%s\n' "$cmd" | awk '
      skip { if ($0 ~ "^[[:space:]]*" tag "[[:space:]]*$") skip=0; next }
      { print }
      match($0, /(^|[^<])<<-?[[:space:]]*["'"'"']?[A-Za-z_][A-Za-z0-9_]*/) {
        t = substr($0, RSTART, RLENGTH); sub(/^[^<]?<<-?[[:space:]]*["'"'"']?/, "", t); tag=t; skip=1 }
    ' | sed -E \
      -e 's/((^|[[:space:]])(-c|eval)[[:space:]]+)"([^"]*)"/\1 \4 /g' \
      -e "s/((^|[[:space:]])(-c|eval)[[:space:]]+)'([^']*)'/\\1 \\4 /g" \
      -e 's/"[^"/$][^"]*[[:space:]][^"]*"/QSTR/g' \
      -e "s/'[^'/\$][^']*[[:space:]][^']*'/QSTR/g")"

    # Expand variables bound to an ephemeral root (D=/private/tmp/x; ... $D)
    # so `mkdir -p $D` is judged like `mkdir -p /tmp/...`. Lexical only.
    vars="$(printf '%s' "$x" \
      | grep -Eo "${S}(export[[:space:]]+|local[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=${Q}${R}" \
      | sed -E 's/^[;&|[:space:](]*(export[[:space:]]+|local[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)=.*/\2/' \
      | sort -u)"
    for v in $vars; do
      x="$(printf '%s' "$x" | sed -E \
        -e "s/\\\$\\{?${v}\\}?([^A-Za-z0-9_])/\\/tmp\\/\\1/g" \
        -e "s/\\\$\\{?${v}\\}?\$/\\/tmp\\//")"
    done

    # Deny rules: an ephemeral root as the WRITE TARGET. Name|ERE pairs.
    rules=(
      "redirect|>[>|]?[[:space:]]*${Q}${R}"
      "tee|(^|[^[:alnum:]_-])tee([[:space:]][^;&|]*)?[[:space:]]${Q}${R}"
      "output flag|(^|[[:space:]])(-[[:alpha:]]*o|--output|--output-document|--output-dir|--directory-prefix)(=|[[:space:]]*)${Q}${R}"
      "wget -O/-P|wget[^;&|]*[[:space:]]-[OP][[:space:]]*${Q}${R}"
      "copy destination|${S}(cp|mv|rsync|ln|install|ditto)[[:space:]]([^;&|]*[[:space:]])?${Q}${R}[^;&|[:space:]]*${Q}[[:space:]]*(\$|[;&|)])"
      "copy -t|${S}(cp|mv|ln|install)[[:space:]][^;&|]*(-t|--target-directory)(=|[[:space:]]+)${Q}${R}"
      "mkdir/touch|${S}(mkdir|touch)[[:space:]]([^;&|]*[[:space:]])?${Q}${R}"
      "extract into|(tar[^;&|]*[[:space:]](-C|--directory)|unzip[^;&|]*[[:space:]]-d)(=|[[:space:]]+)${Q}${R}"
      "git clone/worktree|git[[:space:]]+(clone|worktree[[:space:]]+add)[^;&|]*[[:space:]]${Q}${R}"
      "mktemp default dir|(^|[^[:alnum:]_])mktemp([[:space:]]+-[[:alpha:]]+)*[[:space:]]*(\$|[;&|)\`\"'])"
      "mktemp -t/--tmpdir|(^|[^[:alnum:]_])mktemp[^;&|]*[[:space:]](-[[:alpha:]]*t|--tmpdir)([[:space:]=]|\$)"
      "mktemp in root|(^|[^[:alnum:]_])mktemp[^;&|]*[[:space:]=]${Q}${R}"
      "dd of=|(^|[[:space:]])of=${Q}${R}"
    )
    flat="$(printf '%s' "$x" | tr '\n' ' ')"
    # cd/pushd into a root, then a relative write before the next directory
    # change. Each cd|pushd|popd starts its own line, so a later
    # `cd ~/Projects/x && mkdir foo` is judged against its own directory.
    cdre="^[[:space:]]*(cd|pushd)[[:space:]]+${Q}${R}.*(>[>|]?[[:space:]]*[^&[:space:]/~\$]|${S}(tee|cp|mv|rsync|ln|mkdir|touch|wget|unzip|tar)[[:space:]]|curl[^;&|]*[[:space:]]-[[:alpha:]]*[oO]([[:space:]]|\$)|git[[:space:]]+(clone|init|worktree))"
    cdsplit="$(printf '%s' "$flat" | awk '{ gsub(/(^|[;&|(])[[:space:]]*(cd|pushd|popd)[[:space:]]/, "\n&"); print }')"
    for r in "${rules[@]}" "cd into root, then write|__CD__"; do
      name="${r%%|*}"; re="${r#*|}"
      if [[ "$re" == "__CD__" ]]; then
        printf '%s\n' "$cdsplit" | sed -E 's/^[;&|(]//' | grep -Eq -- "$cdre" || continue
      elif ! printf '%s' "$flat" | grep -Eq -- "$re"; then
        continue
      fi
      jq -n --arg n "$name" --arg d "$DURABLE" '{
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: ("ephemeral-guard: this command writes into /tmp, the scratchpad or $TMPDIR (rule: " + $n + ") and the result will be lost with the session. " + $d + " For output that is worthless once read, use a pipe instead of a file. This hook cannot be overridden from inside the session: if mazze wants this temp path, they run it themselves with ! <command>.")
        }
      }'
      exit 0
    done

    # Any other mention: allow, with a reminder.
    pre='(^|[[:space:]"'"'"'=:(<>|;&])'
    pattern="${pre}(/private)?/tmp([/[:space:]\"'\`;)|&]|\$)"
    pattern+="|${pre}(/private)?/var/folders/"
    pattern+='|\$\{?TMPDIR'
    if printf '%s' "$x" | grep -Eq -- "$pattern"; then
      jq -n --arg d "$DURABLE" '{
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          additionalContext: ("ephemeral-guard: this command touches /tmp, the scratchpad or $TMPDIR. Fine for pipes and output that is worthless once read. If anything it writes is evidence, a record, a draft or a working copy, put it somewhere durable instead. " + $d)
        }
      }'
    fi
    ;;
esac
exit 0
