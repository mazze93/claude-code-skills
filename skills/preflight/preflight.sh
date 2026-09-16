#!/usr/bin/env bash
# preflight.sh — probe the session environment for commit/sign/deploy readiness.
#
# Design rules (do not relax these):
#   1. Read-only by default. Only idempotent *runtime* fixes are auto-applied
#      (e.g. launching gpg-agent). Anything that edits a dotfile or needs a
#      human is emitted as an exact command for the user's own terminal.
#   2. No secret ever reaches stdout. Private key files are never read. Every
#      external command's output goes through redact(). Fingerprints and key
#      IDs are public and are shown; passphrases and tokens are not.
#   3. Nothing may block. Every probe that could prompt is forced into a
#      non-interactive mode that fails fast instead of waiting on input.
#
# Exit: 0 = ready, 1 = at least one ACTION item needs the user.

set -uo pipefail

FIX=0
[ "${1:-}" = "--fix" ] && FIX=1

ACTIONS=0
WARNS=0
declare -a ACTION_CMDS=()

# ── output helpers ───────────────────────────────────────────────────────────
if [ -t 1 ]; then
  B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; C=$'\033[36m'; Z=$'\033[0m'
else
  B=""; G=""; Y=""; R=""; C=""; Z=""
fi

hdr()  { printf '\n%s── %s %s\n' "$C" "$1" "$Z"; }
ok()   { printf '  %s✓%s %s\n' "$G" "$Z" "$1"; }
warn() { WARNS=$((WARNS + 1)); printf '  %s!%s %s\n' "$Y" "$Z" "$1"; }
bad()  { printf '  %s✗%s %s\n' "$R" "$Z" "$1"; }
info() { printf '    %s\n' "$1"; }
fixed(){ printf '  %s✓%s %s %s(auto-fixed)%s\n' "$G" "$Z" "$1" "$B" "$Z"; }

# Record something only the human can do, with the exact command to paste.
action() {
  bad "$1"
  printf '    %srun in your own terminal:%s %s\n' "$B" "$Z" "$2"
  ACTION_CMDS+=("$2")
  ACTIONS=$((ACTIONS + 1))
}

# Mask anything that looks like a credential. Belt and braces: no probe below
# is supposed to emit one, this is the net under that assumption.
redact() {
  sed -E \
    -e 's/gh[pousr]_[A-Za-z0-9]{16,}/<redacted-gh-token>/g' \
    -e 's/github_pat_[A-Za-z0-9_]{20,}/<redacted-gh-pat>/g' \
    -e 's/(AKIA|ASIA)[A-Z0-9]{12,}/<redacted-aws-key>/g' \
    -e 's/xox[abprs]-[A-Za-z0-9-]{10,}/<redacted-slack-token>/g' \
    -e 's/(-----BEGIN[A-Z ]*PRIVATE KEY-----).*/<redacted-private-key>/g' \
    -e 's/(passphrase|password|secret|token)([=: ]+)[^ ]+/\1\2<redacted>/gI'
}

has() { command -v "$1" >/dev/null 2>&1; }

# Run a command with a hard time limit when one is available, so a probe can
# never hang the session even if a prompt slips past the non-interactive flags.
cap() {
  local secs="$1"; shift
  if has timeout;  then timeout  "$secs" "$@"; return $?; fi
  if has gtimeout; then gtimeout "$secs" "$@"; return $?; fi
  "$@"
}

printf '%s╭─ session preflight ─────────────────────────────────╮%s\n' "$B" "$Z"
printf '  host: %s · shell: %s\n' "$(hostname -s 2>/dev/null)" "${SHELL##*/}"
printf '  cwd:  %s\n' "$PWD"

# ── 1. controlling TTY ───────────────────────────────────────────────────────
hdr "controlling TTY"
TTY_NAME="$(tty 2>/dev/null)"
HAS_TTY=0
if [ -t 0 ] && [ "$TTY_NAME" != "not a tty" ]; then
  HAS_TTY=1
  ok "controlling TTY present: $TTY_NAME"
else
  # This is a property of the agent shell, not a misconfiguration. It is only
  # a problem when something wants to prompt *in the terminal*.
  warn "no controlling TTY (expected for an agent shell)"
  info "consequence: any tool that prompts on the terminal (pinentry-curses,"
  info "ssh-add, sudo -S) cannot receive input here and will fail or hang."
  info "GUI prompts are unaffected — they don't need a TTY."
fi

# ── 2. GPG ───────────────────────────────────────────────────────────────────
hdr "GPG signing"
if ! has gpg; then
  action "gpg not installed" "brew install gnupg pinentry-mac"
else
  ok "gpg present: $(gpg --version 2>/dev/null | head -1 | redact)"

  AGENT_CONF="${GNUPGHOME:-$HOME/.gnupg}/gpg-agent.conf"

  # 2a. agent reachable — launching it is idempotent, so auto-fix it.
  AGENT_SOCK="$(gpgconf --list-dirs agent-socket 2>/dev/null)"
  if [ -S "$AGENT_SOCK" ] && cap 5 gpg-connect-agent /bye >/dev/null 2>&1; then
    ok "gpg-agent reachable"
  else
    if cap 10 gpgconf --launch gpg-agent >/dev/null 2>&1; then
      fixed "gpg-agent was not running — launched it"
    else
      action "gpg-agent unreachable and could not be launched" "gpgconf --launch gpg-agent"
    fi
  fi

  # 2b. which pinentry — this decides whether the missing TTY actually matters.
  PINENTRY="$(grep -E '^[[:space:]]*pinentry-program' "$AGENT_CONF" 2>/dev/null | awk '{print $2}' | tail -1)"
  PIN_KIND="unknown"
  case "$PINENTRY" in
    *pinentry-mac|*pinentry-gtk*|*pinentry-qt*|*pinentry-gnome*) PIN_KIND="gui" ;;
    *pinentry-curses|*pinentry-tty)                              PIN_KIND="terminal" ;;
    "")                                                          PIN_KIND="default" ;;
  esac

  if [ "$PIN_KIND" = "gui" ]; then
    ok "pinentry is GUI (${PINENTRY##*/}) — works without a TTY"
  elif [ "$PIN_KIND" = "terminal" ] && [ "$HAS_TTY" -eq 0 ]; then
    action "pinentry is terminal-based (${PINENTRY##*/}) but this shell has no TTY" \
      "brew install pinentry-mac && echo 'pinentry-program /opt/homebrew/bin/pinentry-mac' >> $AGENT_CONF && gpgconf --kill gpg-agent"
  else
    warn "pinentry program not pinned in gpg-agent.conf (using gpg's default)"
    info "on a TTY-less shell a GUI pinentry is the reliable choice:"
    info "echo 'pinentry-program /opt/homebrew/bin/pinentry-mac' >> $AGENT_CONF"
  fi

  # 2c. GPG_TTY. Only load-bearing for terminal pinentry. Saying "set GPG_TTY"
  #     to someone using pinentry-mac is cargo-culted advice — it fixes nothing.
  if [ -n "${GPG_TTY:-}" ]; then
    ok "GPG_TTY is set ($GPG_TTY)"
  elif [ "$PIN_KIND" = "gui" ]; then
    ok "GPG_TTY unset — not required, pinentry is GUI"
  elif [ "$HAS_TTY" -eq 0 ]; then
    warn "GPG_TTY unset and there is no TTY to point it at"
    info "setting it here would not help; the fix is a GUI pinentry (above)."
  else
    warn "GPG_TTY unset"
    info "persist it:  echo 'export GPG_TTY=\$(tty)' >> ~/.zshenv"
  fi

  # 2d. loopback. Deliberately NOT auto-enabled — see SKILL.md. Loopback means
  #     the *caller* supplies the passphrase, i.e. it would have to be typed
  #     into the agent transcript. Report its status, never turn it on for use.
  if grep -qE '^[[:space:]]*allow-loopback-pinentry' "$AGENT_CONF" 2>/dev/null; then
    info "note: allow-loopback-pinentry is enabled in gpg-agent.conf."
    info "      left alone. Not used for signing here — loopback requires the"
    info "      passphrase to come from the calling process, which would put it"
    info "      in this transcript. GUI pinentry + agent cache is the safe path."
  fi

  # 2e. signing key configured and actually in the keyring.
  SIGNKEY="$(git config --get user.signingkey 2>/dev/null)"
  GPGSIGN="$(git config --get commit.gpgsign 2>/dev/null)"
  if [ -z "$SIGNKEY" ]; then
    if [ "$GPGSIGN" = "true" ]; then
      action "commit.gpgsign=true but user.signingkey is unset" \
        "git config --global user.signingkey <YOUR_KEY_ID>   # gpg --list-secret-keys --keyid-format=long"
    else
      info "no signing key configured and signing not required here"
    fi
  else
    if gpg --list-secret-keys "$SIGNKEY" >/dev/null 2>&1; then
      ok "signing key $SIGNKEY present in keyring (commit.gpgsign=${GPGSIGN:-unset})"

      # 2f. Is the passphrase cached? --pinentry-mode error makes gpg fail
      #     instantly rather than prompting, so this probe can neither hang
      #     nor pop a dialog. It answers exactly one question: can we sign
      #     right now without human interaction?
      if echo preflight | cap 10 gpg --batch --no-tty --pinentry-mode error \
           --local-user "$SIGNKEY" --sign -o /dev/null >/dev/null 2>&1; then
        ok "passphrase is cached — signing works non-interactively right now"
      else
        TTL="$(grep -E '^[[:space:]]*default-cache-ttl' "$AGENT_CONF" 2>/dev/null | awk '{print $2}' | tail -1)"
        warn "signing key is locked (passphrase not cached)"
        [ -n "$TTL" ] && info "agent cache ttl: ${TTL}s once unlocked"
        if [ "$PIN_KIND" = "gui" ]; then
          info "a commit from here will raise a GUI passphrase dialog — that will"
          info "work, it just needs you at the machine. To pre-warm it instead:"
        fi
        info "unlock once, in your own terminal, and the cache covers the session:"
        printf '    %sunlock:%s echo preflight | gpg --local-user %s --sign -o /dev/null && echo unlocked\n' \
          "$B" "$Z" "$SIGNKEY"
      fi
    else
      action "user.signingkey $SIGNKEY is NOT in the keyring — every commit will fail" \
        "gpg --list-secret-keys --keyid-format=long   # then: git config --global user.signingkey <ID>"
    fi
  fi
fi

# ── 3. SSH ───────────────────────────────────────────────────────────────────
hdr "SSH authentication"
SSH_OK=0
SSH_DIR="$HOME/.ssh"

# 3a. On-disk keys. Presence is established by listing the directory — never by
#     inferring absence from one failed command, and never by reading a key.
if [ -d "$SSH_DIR" ]; then
  PUBKEYS="$(find "$SSH_DIR" -maxdepth 1 -name '*.pub' -type f 2>/dev/null | sort)"
  if [ -n "$PUBKEYS" ]; then
    ok "key material in $SSH_DIR:"
    while IFS= read -r pk; do
      [ -z "$pk" ] && continue
      FPR="$(ssh-keygen -lf "$pk" 2>/dev/null | redact)"
      PRIV="${pk%.pub}"
      if [ -f "$PRIV" ]; then MARK="private+public"; else MARK="public only"; fi
      info "${pk##*/}  [$MARK]  ${FPR:-<unreadable>}"

      # Permissions are checked here rather than inferred from a failed
      # connection. OpenSSH hard-refuses a private key that is group- or
      # world-readable, and the resulting error ("UNPROTECTED PRIVATE KEY
      # FILE") looks like an auth failure, which sends people off switching
      # remotes to HTTPS when the real fix is one chmod. It is also a live
      # exposure on a multi-account machine: mode 640 means every other local
      # account in the file's group can read the key.
      if [ -f "$PRIV" ]; then
        PMODE="$(stat -f '%A' "$PRIV" 2>/dev/null || stat -c '%a' "$PRIV" 2>/dev/null)"
        case "$PMODE" in
          600|400) : ;;
          *)
            # Tightening permissions on a key you already own needs no secret
            # and no privilege, so --fix may apply it. It stays an ACTION by
            # default: a loosened mode is occasionally deliberate (shared
            # group access across local accounts), and silently reversing an
            # intentional choice is worse than one extra prompt.
            if [ "$FIX" -eq 1 ] && chmod 600 "$PRIV" 2>/dev/null; then
              fixed "private key $PRIV was mode $PMODE — tightened to 600"
            else
              action "private key $PRIV is mode $PMODE — readable beyond its owner; ssh will refuse it" \
                "chmod 600 $PRIV"
            fi
            ;;
        esac
      fi
    done <<< "$PUBKEYS"

    DMODE="$(stat -f '%A' "$SSH_DIR" 2>/dev/null || stat -c '%a' "$SSH_DIR" 2>/dev/null)"
    case "$DMODE" in
      700|500) : ;;
      *) warn "$SSH_DIR is mode $DMODE (700 recommended):  chmod 700 $SSH_DIR" ;;
    esac
  else
    warn "no *.pub files in $SSH_DIR"
  fi
else
  warn "$SSH_DIR does not exist"
fi

# 3b. The agent. ssh-add exit codes: 0 = keys loaded, 1 = agent up but empty,
#     2 = cannot reach an agent. These are distinct problems with distinct fixes.
if [ -z "${SSH_AUTH_SOCK:-}" ]; then
  warn "SSH_AUTH_SOCK unset — no agent advertised to this shell"
else
  info "agent socket: $SSH_AUTH_SOCK"
fi
cap 8 ssh-add -l >/dev/null 2>&1
case $? in
  0)
    ok "ssh-agent has keys loaded:"
    cap 8 ssh-add -l 2>/dev/null | redact | while IFS= read -r l; do info "$l"; done
    SSH_OK=1
    ;;
  1)
    # Loading a key can require a passphrase, which needs a prompt this shell
    # cannot serve. Hand it back rather than attempting it.
    warn "ssh-agent is running but holds no keys"
    printf '    %srun in your own terminal:%s ssh-add --apple-use-keychain %s/id_ed25519\n' "$B" "$Z" "$SSH_DIR"
    info "(ssh-add may prompt for a passphrase — it must be your terminal, not this one)"
    ;;
  *)
    warn "cannot reach an ssh-agent"
    printf '    %srun in your own terminal:%s eval "$(ssh-agent -s)" && ssh-add --apple-use-keychain %s/id_ed25519\n' "$B" "$Z" "$SSH_DIR"
    ;;
esac

# 3c. Does GitHub actually accept us? BatchMode guarantees no prompt.
if has ssh; then
  GH_SSH_OUT="$(cap 12 ssh -o BatchMode=yes -o ConnectTimeout=6 -T git@github.com 2>&1 | redact)"
  if printf '%s' "$GH_SSH_OUT" | grep -q 'successfully authenticated'; then
    ok "github.com accepts this SSH identity"
    SSH_OK=1
  elif printf '%s' "$GH_SSH_OUT" | grep -qi 'host key verification failed'; then
    action "github.com host key not trusted yet" \
      "ssh-keyscan github.com >> ~/.ssh/known_hosts"
  elif printf '%s' "$GH_SSH_OUT" | grep -qi 'UNPROTECTED PRIVATE KEY'; then
    # Already reported with the exact chmod in the permissions check above;
    # say why the connection failed rather than repeating the fix, and do not
    # let the ASCII warning banner through — it renders as noise.
    warn "github.com refused the identity because of the key permissions above"
    info "this is a permissions problem, not an auth problem — do not switch the remote."
  else
    warn "github.com did not accept an SSH identity"
    # Collapse to one clean line: strip the '@@@@' banner rows and blank lines.
    info "$(printf '%s' "$GH_SSH_OUT" | grep -vE '^[@[:space:]]*$|^@+$' | tr -s ' ' | head -2 | tr '\n' ' ')"
  fi
fi

# ── 4. git remote protocol vs available auth ─────────────────────────────────
hdr "git remote ↔ auth match"
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  info "not inside a git repository — skipping remote check"
else
  ORIGIN="$(git remote get-url origin 2>/dev/null | redact)"
  if [ -z "$ORIGIN" ]; then
    warn "no 'origin' remote configured"
  else
    ok "origin: $ORIGIN"
    GH_TOKEN_OK=0
    if has gh && cap 10 gh auth status >/dev/null 2>&1; then GH_TOKEN_OK=1; fi

    case "$ORIGIN" in
      git@*|ssh://*)
        if [ "$SSH_OK" -eq 1 ]; then
          ok "protocol SSH, and SSH auth is working — matched"
        else
          # The important half of this check: do NOT recommend switching to
          # HTTPS. Keys exist; the agent is the thing that needs fixing.
          bad "protocol is SSH but no working SSH identity was proven"
          info "fix the agent (section 3) rather than switching the remote to HTTPS."
          info "switching protocol to dodge an unlocked-key problem trades a"
          info "30-second unlock for a credential you then have to manage."
        fi
        ;;
      https://*)
        if [ "$GH_TOKEN_OK" -eq 1 ]; then
          ok "protocol HTTPS, and gh has a valid token — matched"
        else
          HELPER="$(git config --get credential.helper 2>/dev/null)"
          if [ -n "$HELPER" ]; then
            warn "protocol HTTPS; no gh token, but credential.helper=$HELPER is configured"
          else
            action "protocol HTTPS with no gh token and no credential helper — pushes will fail" \
              "gh auth login"
          fi
          if [ "$SSH_OK" -eq 1 ]; then
            info "note: SSH auth works. You could switch: git remote set-url origin git@github.com:<owner>/<repo>.git"
          fi
        fi
        ;;
      *) warn "unrecognised remote protocol" ;;
    esac
  fi
fi

# ── 5. MCP connectivity ──────────────────────────────────────────────────────
hdr "MCP servers"
if ! has claude; then
  info "claude CLI not on PATH — skipping"
else
  MCP_OUT="$(cap 25 claude mcp list 2>&1 | redact)"
  if [ -z "$MCP_OUT" ]; then
    warn "no output from 'claude mcp list'"
  else
    # Tolerate both "✓ Connected" and "- Failed to connect" shapes.
    FAILED="$(printf '%s\n' "$MCP_OUT" | grep -iE 'fail|error|disconnect|not connected' || true)"
    CONNECTED="$(printf '%s\n' "$MCP_OUT" | grep -ciE 'connected' || true)"
    if [ -n "$FAILED" ]; then
      warn "some MCP servers are not connected:"
      printf '%s\n' "$FAILED" | head -8 | while IFS= read -r l; do info "$l"; done
      info "re-auth an OAuth server from inside Claude Code with:  /mcp"
    else
      ok "no MCP failures reported (${CONNECTED} connected)"
    fi
  fi
fi

# ── summary ──────────────────────────────────────────────────────────────────
printf '\n%s╰─ summary ──────────────────────────────────────────╯%s\n' "$B" "$Z"
if [ "$ACTIONS" -eq 0 ]; then
  if [ "$WARNS" -eq 0 ]; then
    ok "clean — safe to commit, sign, and deploy"
  else
    # A warning is something that is not blocking *this* repo's workflow but
    # would block a different one (e.g. an empty ssh-agent under an HTTPS
    # remote). Saying "no issues" here would be the same over-claim this
    # skill exists to prevent.
    ok "nothing blocking commit/sign/deploy for this repo"
    warn_total=$WARNS
    printf '  %s!%s %s advisory item(s) above — not blocking here, but they would\n' "$Y" "$Z" "$warn_total"
    info "bite on a repo with a different remote protocol or a locked key."
  fi
  exit 0
else
  bad "$ACTIONS item(s) need you. Commands to paste into your own terminal:"
  for c in "${ACTION_CMDS[@]}"; do printf '    %s\n' "$c"; done
  printf '\n  %sNever paste a passphrase, token, or key into the Claude transcript.%s\n' "$B" "$Z"
  exit 1
fi
