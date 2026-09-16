---
name: preflight
description: Probe session environment readiness for committing, signing, or deploying — TTY, GPG/pinentry, ssh-agent, git remote↔auth match, and MCP connectivity. Reports an applied fix or an exact paste-into-your-own-terminal command for every failure. Use at the start of any session that will commit, sign, tag, push, or deploy, or when a commit/push fails for environment reasons.
---

# /preflight

Environment failures are the most expensive kind, because they surface *after*
the work is done — at the commit, at the push, at the deploy — when there is
finished work sitting in a dirty tree and a session limit approaching. This
skill front-loads them into the first thirty seconds.

Run `bash "$(dirname "$0")/preflight.sh"` — in practice:

```bash
bash /Users/Shared/claude-code-skills/skills/preflight/preflight.sh
```

Exit code `0` means safe to proceed; `1` means at least one item needs the
human. Pass `--fix` to opt into the (few) persistent fixes; without it only
idempotent runtime fixes are applied.

## Hard rules — these are not style preferences

1. **Never ask the user to type a passphrase, token, or private key into the
   conversation.** If a step needs a secret, print the exact command and stop.
   A passphrase pasted into a transcript is a compromised passphrase and must be
   rotated. This has actually happened; that is why this skill exists.
2. **Never echo credential material.** Fingerprints, key IDs, and public keys
   are fine — they are public by construction. Private key contents, tokens, and
   passphrases are not. All probe output passes through `redact()`.
3. **Never read a private key file** to determine whether it exists. Use the
   directory listing and the agent.
4. **Never conclude a key is absent from one failed command.** Check `~/.ssh`
   *and* the agent, and distinguish "no agent" from "agent with no keys" from
   "key present but locked" — three different problems with three different fixes.
5. **Never downgrade auth to route around a lock.** If the remote is SSH and the
   key is merely locked, fix the agent. Switching the remote to HTTPS to dodge an
   unlock trades thirty seconds for a credential you now have to manage.

## What it probes, and why each one earns its place

| Probe | Question it answers |
| --- | --- |
| Controlling TTY | Can anything prompt in this shell at all? |
| pinentry kind | Does the missing TTY actually matter here? |
| `GPG_TTY` | Only load-bearing for terminal pinentry |
| gpg-agent socket | Is the agent up? (auto-launched — idempotent) |
| signing key in keyring | Does `user.signingkey` resolve to a real secret key? |
| passphrase cached | Can we sign *right now* without a human? |
| `~/.ssh` contents | Which keys exist, by fingerprint |
| key file mode | Is a private key group/world-readable? (ssh hard-refuses these, and the error masquerades as an auth failure) |
| ssh-agent state | Agent absent / empty / loaded — three distinct states |
| `ssh -T git@github.com` | Does GitHub actually accept us? |
| remote protocol ↔ auth | Does the remote's protocol match the auth we have? |
| `claude mcp list` | Which MCP servers are actually connected? |

## On loopback pinentry — deliberately not enabled

The obvious-looking fix for "no TTY for pinentry" is `--pinentry-mode loopback`.
**It is the wrong fix for an agent shell, and this skill will not use it for
signing.**

Loopback means gpg stops asking its own pinentry and instead takes the
passphrase *from the calling process*. In a terminal that is fine. Here, the
calling process is the agent — so the passphrase would have to be supplied by
Claude, which means it would have to appear in the transcript. That is precisely
the failure mode rule 1 exists to prevent.

The correct arrangement on macOS is a **GUI pinentry** (`pinentry-mac`), which
needs no controlling TTY because it draws its own window, plus a generous
`default-cache-ttl` so one unlock covers a working session. If
`allow-loopback-pinentry` is already present in `gpg-agent.conf` the skill
reports it and leaves it alone — it is legitimately needed by some CI tooling —
but it is never the mechanism used to sign from here.

The one non-interactive use of pinentry-mode that *is* safe is
`--pinentry-mode error`, used by the cache probe: it makes gpg fail instantly
instead of prompting, which is how the skill asks "is this key unlocked?"
without risking a hang or a dialog.

## Reporting

For each failure emit exactly one of:

- **auto-fixed** — what was done, and that it was idempotent.
- **an exact single command** — copy-pasteable, for the user's own terminal,
  with any placeholder in obvious `<ANGLE_BRACKETS>`.

Never emit a vague instruction ("make sure your agent is running"). Never emit
a multi-step narrative where one command would do. If a fix's applicability
depends on OS or tool version, verify against `--help` or the man page on this
machine rather than recalling it — deprecated advice (`spctl --add`) has burned
this workspace before.

End with the one-line verdict: ready, or N items needing the human.
