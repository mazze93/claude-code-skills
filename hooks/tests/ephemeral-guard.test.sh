#!/usr/bin/env bash
# Fixture tests for hooks/ephemeral-guard.sh.  Run: bash hooks/tests/ephemeral-guard.test.sh
# Prints one line per case; exits non-zero if any case disagrees with its expectation.
# Expectations: DENY (permissionDecision deny), WARN (additionalContext), silent.
set -uo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/ephemeral-guard.sh"
fail=0; n=0

check() {
  local want="$1" tool="$2" val="$3" key json out got
  case "$tool" in
    Bash) key=command ;;
    NotebookEdit) key=notebook_path ;;
    *) key=file_path ;;
  esac
  json="$(jq -n --arg t "$tool" --arg k "$key" --arg v "$val" '{tool_name:$t, tool_input:{($k):$v}}')"
  out="$(printf '%s' "$json" | bash "$HOOK")"
  if   [[ "$out" == *'"deny"'* ]]; then got=DENY
  elif [[ "$out" == *additionalContext* ]]; then got=WARN
  elif [[ -z "$out" ]]; then got=silent
  else got="OTHER"; fi
  n=$((n+1))
  if [[ "$got" == "$want" ]]; then printf 'ok    %-6s %-5s %s\n' "$got" "$tool" "$val"
  else printf 'FAIL  want %s got %s  %-5s %s\n' "$want" "$got" "$tool" "$val"; fail=$((fail+1)); fi
}

SP=/private/tmp/claude-501/-Users-x-Desktop/0000/scratchpad

# ── File tools ────────────────────────────────────────────────────────────────
check DENY   Write        /tmp/x
check DENY   Write        "$SP/a.md"
check DENY   Edit         //tmp//y
check DENY   Write        /var/folders/ab/T/z
check DENY   NotebookEdit /tmp/n.ipynb
check silent Write        /tmpfoo/x
check silent Write        /Users/d/Projects/tmp/x
check silent Write        /Users/d/Projects/inbox/2026-11-25/a.md

# ── Bash: the 2026-11-24 slip, verbatim shape ─────────────────────────────────
check DENY Bash "D=$SP/ptk-assets; mkdir -p \$D && cd \$D
for f in a.js; do curl -sfL -o \$f \"https://example.invalid/\$f\"; done"
check DENY Bash "D=$SP/ptk; curl -so \"\$D/a.js\" https://example.invalid/a.js"
check DENY Bash "export OUT=\"$SP\"; cp report.md \${OUT}/"

# ── Bash: write targets ───────────────────────────────────────────────────────
check DENY Bash "curl -so /tmp/f https://example.invalid"
check DENY Bash "curl -s https://example.invalid -o/tmp/f"
check DENY Bash "echo hi >/tmp/f"
check DENY Bash "echo hi >> \"$SP/log\""
check DENY Bash "echo hi >| /tmp/f"
check DENY Bash "ls | tee -a /tmp/list"
check DENY Bash "wget -O /tmp/x https://example.invalid"
check DENY Bash "cp evidence.json /tmp/"
check DENY Bash "mv a b /private/tmp/keep && ls"
check DENY Bash "rsync -a src/ /tmp/mirror"
check DENY Bash "cp -t /tmp a b"
check DENY Bash "mkdir -p /tmp/work"
check DENY Bash "touch \$TMPDIR/flag"
check DENY Bash "tar -xzf a.tgz -C /tmp/x"
check DENY Bash "unzip a.zip -d /tmp/x"
check DENY Bash "git clone https://example.invalid/r.git /tmp/r"
check DENY Bash "git worktree add /tmp/wt feature"
check DENY Bash "f=\$(mktemp)"
check DENY Bash "d=\$(mktemp -d)"
check DENY Bash "mktemp -t probe"
check DENY Bash "cd /tmp && echo hi > out.txt"
check DENY Bash "cd \"$SP\"; curl -sO https://example.invalid/a.js"

check DENY Bash "dd if=/dev/zero of=/tmp/x bs=1 count=1"
check DENY Bash "cat <<EOF > /tmp/x
body
EOF"
check DENY Bash "echo hi > \"/tmp/a b\""
check DENY Bash "cat <<<x; curl -so /tmp/y https://example.invalid"   # here-string is not a heredoc
check DENY Bash "cd ~/Projects && ls; cd /tmp && echo hi > out.txt"

# ── touchstone 2026-11-25: text that only QUOTES a write is not a write ───────
check silent Bash "git commit -F - <<EOF
docs: example shows echo hi > /tmp/f
EOF"
check silent Bash "git commit -m \"docs: never echo hi > /tmp/f\""
check silent Bash "jq -n --arg c 'curl -o /tmp/x u' '{c:\$c}'"
check WARN   Bash "cd /tmp && ls; cd ~/Projects/x && mkdir foo"   # later cd resets
# re-pass: quoted payloads that ARE commands must still be judged
check DENY   Bash "bash -c \"curl -so /tmp/x https://example.invalid\""
check DENY   Bash "zsh -c 'mkdir -p /tmp/w'"
check DENY   Bash "eval \"echo hi > /tmp/f\""
check silent Bash "zsh -c 'git status'"

# ── Bash: mentions that are not writes into a root → WARN ─────────────────────
check WARN Bash "ls /tmp"
check WARN Bash "cat /tmp/x"
check WARN Bash "cp /tmp/x ~/Projects/inbox/2026-11-25/"
check WARN Bash "cd /private/tmp && ls"
check WARN Bash "grep foo /tmp/x 2>/dev/null"
check WARN Bash "ls \$TMPDIR"
check WARN Bash "command rm -rf -- $SP/ptk-assets"
check WARN Bash "cp a /tmp/x 2>/dev/null"   # documented gap: dest not last arg

# ── Bash: unrelated → silent ──────────────────────────────────────────────────
check silent Bash "git status"
check silent Bash "ls ~/Projects/tmp/"
check silent Bash "echo hi > ~/Projects/inbox/x.md"
check silent Bash "f=\$(mktemp ~/Projects/inbox/x.XXXX)"
check silent Bash "make 2>/dev/null"
check silent Read "/tmp/x"

# ── Fail-open: must allow (systemMessage only), never deny ────────────────────
failopen() {
  local label="$1" out; out="$(cat)"
  n=$((n+1))
  if [[ "$out" == *systemMessage* && "$out" != *'"deny"'* ]]; then printf 'ok    OPEN   %s\n' "$label"
  else printf 'FAIL  want OPEN got: %s  (%s)\n' "$out" "$label"; fail=$((fail+1)); fi
}
printf 'not json' | /bin/bash "$HOOK" | failopen "malformed input"
# Precondition: jq must really be unreachable (macOS ships /usr/bin/jq, so PATH=/usr/bin:/bin is NOT enough).
if env PATH=/var/empty /bin/bash -c 'command -v jq' >/dev/null 2>&1; then
  n=$((n+1)); fail=$((fail+1)); echo "FAIL  precondition: jq still reachable with PATH=/var/empty"
else
  printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"/tmp/x"}}' \
    | env PATH=/var/empty /bin/bash "$HOOK" | failopen "jq missing"
fi

echo "---"
echo "$((n-fail))/$n passed"
[[ $fail -eq 0 ]]
