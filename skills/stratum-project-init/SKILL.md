---
name: stratum-project-init
description: Stand up a project (new or existing) with the full Stratum-backed build-journal workflow — git init, a dedicated Stratum epistemic decision log, BUILD_JOURNAL.md cookbook, and the burst-summary/stratum-link correlation scripts that tie git commits to Stratum decisions without adding live network calls to the auto-commit hook. Use this whenever the user asks to "set up a project like lockdown-exploitability-triage", "wire up Stratum for this project", "add a build journal", "set up append-only decision logging", "let me commit and iterate on this autonomously without losing work", or wants a project to support checkpointed, resumable, agent-driven bursts of work. Every step is idempotent — safe to re-run on a project that's already partially or fully set up; it detects existing state and only does what's missing.
---

# Stratum Project Init

Reproduces, for any project, the setup done for `lockdown-exploitability-triage`:
a git repo with automatic per-file checkpointing, a dedicated Stratum decision log,
a `BUILD_JOURNAL.md` cookbook, and two scripts that correlate git history with the
Stratum ledger on demand instead of on every keystroke.

**Read this whole file before starting.** Every step below is idempotent by design —
check current state first, report what already exists, only act on what's missing.
Never blindly overwrite `BUILD_JOURNAL.md`, `.stratum-log`, or an existing git repo's
history. Re-running this skill on an already-set-up project should be a no-op that
confirms everything is in place, not a second genesis.

## Why two separate ledgers, not one

This matters enough to explain before you touch anything, because it's tempting to
"simplify" by merging them and that would break the design:

- **git** (plus the machine's auto-commit hook, if present) is the fast, complete,
  low-friction artifact trail. It fires on every file save and should never depend on
  a network call — that's what makes it safe as a loss-prevention net for autonomous
  or unattended bursts.
- **Stratum** is the sparse, deliberate reasoning trail — *why* a choice was made, what
  was rejected, how sure it really was. It's meant to hold only real decisions, not
  every mechanical edit.

Wiring the auto-commit hook directly into Stratum (a live Cloudflare Worker call on
every Edit/Write) would make routine file saves depend on a remote endpoint — exactly
the failure mode the hook is built to avoid — and would flood the ledger with noise,
destroying the signal that makes it worth reading later. The correlation scripts below
solve this properly: on-demand, explicit, never hook-triggered.

## Setup steps

Work through these in order. At each step, check state before acting.

### 1. Confirm the target project directory

Get the absolute path from the user if not already clear from context. It can be a
brand-new empty directory or an existing project with files already in it — this skill
doesn't care what's inside, only about the scaffolding around it.

### 2. Git repo

Check: `git -C <path> rev-parse --is-inside-work-tree 2>&1`.

- Already a repo → report it and move on. Do not re-init.
- Not a repo → `git init`. If there are existing untracked files worth an initial
  commit, stage and commit them (GPG-signed — check `git config --get
  user.signingkey`; if commit signing fails, stop and surface the error rather than
  falling back to `--no-gpg-sign`). This becomes the genesis commit referenced in
  `BUILD_JOURNAL.md`.

### 3. CLAUDE.md

Check: does `CLAUDE.md` already exist in the project root?

- Yes → leave it alone. Don't touch it as part of this skill.
- No → this skill doesn't author it (that's a separate concern — the `init` skill
  covers analyzing a codebase and writing `CLAUDE.md`). Mention to the user that
  running `/init` afterward would be a reasonable follow-up, but don't block on it.

### 4. Dedicated Stratum log

Check: does `.stratum-log` exist in the project root?

- Yes → read the log id from it, reuse it. Confirm the `stratum` CLI is configured
  (`~/.config/stratum/config.json` exists) and the log is reachable
  (`stratum tessera --log <id>`). Report what's already recorded; do not create a
  second genesis decision.
- No → pick a log id. Default to the project's directory name in kebab-case (drop a
  redundant "stratum-" or generic suffix if the directory name already suggests one).
  Confirm the id with the user if it's not obvious from context — this becomes a
  standing identifier, worth getting right once rather than renaming later. Write it
  to `.stratum-log` (plain text, single line, no trailing content beyond the id).

  Then record the genesis decision:
  ```
  stratum decide "Genesis: <project> stood up with git + a dedicated Stratum log for its build decisions. <one sentence on what the project actually is>." \
    --log <log-id> --shadow "…why a dedicated log rather than the default workspace log, any other genesis context worth recording…"
  ```
  Capture the returned `dec-…` id — it goes into `BUILD_JOURNAL.md`'s Genesis section.

### 5. Correlation scripts

Check: does `scripts/burst-summary.sh` (or `stratum-link.sh`) already exist?

- Yes → diff against this skill's `assets/burst-summary.sh` / `assets/stratum-link.sh`.
  If materially different, tell the user rather than overwriting silently — they may
  have customized it.
- No → copy both from this skill's `assets/` directory into `scripts/` in the target
  project, then `chmod +x` both. They read `.stratum-log` automatically (falling back
  to the repo directory name), so no per-project editing is needed — that's the whole
  point of writing `.stratum-log` in step 4 first.

### 6. BUILD_JOURNAL.md

Check: does `BUILD_JOURNAL.md` already exist?

- Yes → leave it alone. If the user specifically asks to refresh it, diff against the
  template in `assets/BUILD_JOURNAL.md.template` and discuss changes rather than
  overwriting.
- No → render `assets/BUILD_JOURNAL.md.template`, substituting:
  - `{{PROJECT_NAME}}` — the project's name (directory name, or a nicer display name
    if the user gives one)
  - `{{OWNER}}` — the user's name if known, else a generic "you"
  - `{{LOG_ID}}` — the Stratum log id from `.stratum-log`
  - `{{GENESIS_DEC_ID}}` — the dec-id from step 4
  - `{{GENESIS_COMMIT}}` — the short hash of the genesis commit from step 2

  Write the rendered result to `BUILD_JOURNAL.md` in the project root.

  Note the auto-commit-hook paragraph in the template is written to work whether or
  not the target machine has `~/.claude/scripts/auto-commit.sh` — it tells the reader
  to check, rather than assuming. Don't hardcode an assumption about hook presence.

### 7. Checkpoint

If the auto-commit hook is present on this machine, the new/changed files from steps
2–6 will already be getting committed as you write them — no separate action needed.
If not, or once all files are in place, do one deliberate commit covering the whole
setup (`git add -A && git commit -S`) referencing the genesis decision id
(`Ref: dec-…`).

### 8. GitHub (optional)

Only if the user asks. Ask about visibility explicitly — don't default to public or
private without reasoning about the project's actual content (unverified/speculative
research, security-sensitive material, and early-stage work generally favor private;
match an existing precedent only if the user says so). Use `gh repo create <owner>/<name>
--private|--public --source=. --push`. If the push fails with an SSH `Permission denied
(publickey)` error, don't debug the SSH agent unprompted — check `ssh-add -l` first; if
it reports no identities, that's almost certainly the cause. Offer the fallback of
switching the remote to HTTPS (`git remote set-url origin
https://github.com/<owner>/<name>.git`), which works immediately if `gh` is already
authenticated, and say so plainly rather than silently changing protocols. Record
whichever choice was made (and why) as a Stratum decision.

## Verifying the setup worked

Before telling the user it's done, actually confirm rather than assume:

- `stratum tessera --log <log-id>` shows the genesis decision.
- `scripts/burst-summary.sh` runs without error from the project root.
- `git log --oneline -1` shows a real commit.
- `cat .stratum-log` matches what's referenced in `BUILD_JOURNAL.md`.

Report what was created vs. what already existed and was left alone — the user should
be able to tell at a glance whether this was a fresh setup or a confirm-only re-run.
