---
name: ship
description: Ship work end-to-end — validate, prove the change behaves, commit in milestones, push, and handle protected-main/PR-only repos. Use when asked to "ship", "ship it", "release", "commit and push", "open a PR", or "get this live". Commits after each milestone so session-limit cutoffs never lose progress.
---

# /ship (v2 — full workflow)

Encodes the whole shipping pipeline as committed milestones: a session cutoff
loses at most one step, never everything. v2 adds what real repos demanded:
behavioral proof before commit, and branch-protection-aware delivery
(PR-only mains, required signatures, squash-only merges).

## The pipeline

```
0. Preflight   → where am I, what branch, what's dirty, what do the rules allow
1. Validate    → build + tests green, zero NEW warnings
2. Prove       → drive the actual change end-to-end and observe the behavior
3. Commit      → milestone commits, project style, rich message
4. Deliver     → push to main when allowed; branch + PR when protected
5. Verify      → remote accepted it; CI/deploy noted; journal updated
```

### 0 · Preflight

- `git status --short` + `git log --oneline -5` — know the tree and the
  commit style before touching anything. Confirm with the user if unexpected
  files are staged.
- Respect the repo's branch model (check its CLAUDE.md). If it says
  "feature branches, PRs against main" — start on a branch, don't discover
  the rule at push time.

### 1 · Validate

Find the project's real check command (CLAUDE.md, then `package.json`
scripts, then `Package.swift`/Makefile):
- Astro/blog: `npm run check` · TypeScript: `npx tsc --noEmit` ·
  Swift: `swift build && swift test --parallel` · generic: `npm test`/`make test`
- **Do not proceed on failure.** Show the error, stop.
- Treat new warnings as failures-in-waiting (Swift 6 mode, deprecations) —
  fix them now or state why not.

### 2 · Prove (the step everyone skips)

Tests passing is not the change working. Exercise the actual surface once:
run the CLI with real flags, curl the endpoint, load the page. Capture the
observed output — it goes in the commit/PR body as evidence. If the change
can't be driven end-to-end, say so explicitly rather than implying it was.

### 3 · Commit

- Milestone commits per logical unit (`feat: …`, `fix: …`, `test: …`,
  `docs: …`) — never one `WIP: lots of changes` at the end.
- Message body says WHY and cites the proof ("verified end-to-end: <observed>").
- Follow the project's style from `git log`; include the current model's
  standard `Co-Authored-By: Claude …` trailer.
- If the work invalidates any CLAUDE.md claim (backlog items done, files
  moved), update it **in the same commit** — map and territory together.

### 4 · Deliver — the protection decision tree

Try `git push origin main` only when the repo allows it. On rejection, read
the error — it tells you the rules:

| Rejection says | It means | Do |
|---|---|---|
| `Changes must be made through a pull request` | PR-only main | branch → push branch → `gh pr create` |
| `Commits must have verified signatures` (GH013) | unsigned local commits can't land on main directly | PR flow; a **squash merge via GitHub** produces a GitHub-signed commit |
| `Waiting for Code Scanning results` | required check | PR flow and let CI run |
| `Merge commits are not allowed` | squash/rebase-only repo | `gh pr merge --squash` (never `--merge`) |

PR body = what/why + the end-to-end proof + anything the reviewer must know.
Merge only when the user asked you to; otherwise leave the PR open and hand
over the URL.

### 5 · Verify

- Show the actual push/merge output — never claim delivery without it.
- Note the deploy surface (e.g. Cloudflare Pages auto-deploys on push to
  main; verify: `curl -sf <url> | grep -o '<title>[^<]*</title>'`).
- Watch for post-push remote warnings (Dependabot alerts ride in on
  `git push` output) — relay them, don't swallow them.
- If a workspace journal exists (`docs/journal/DECISIONS.md`), record what
  shipped and why.

## Gotchas (all field-tested)

- **Pipes eat exit codes.** `gh pr merge … | tail -2 || fallback` never runs
  the fallback — the pipeline's status is `tail`'s. Check `$?` on the command
  itself, or use `set -o pipefail`. A "merged" that wasn't is the worst
  failure mode this skill exists to prevent.
- **After a squash merge**, local `main` doesn't have the squash commit:
  `git checkout main && git pull` before building on top; delete the branch
  with `--delete-branch` at merge time.
- **GPG signing failures** — `gpg-agent` not running → `gpgconf --launch
  gpg-agent`; expired passphrase cache → `gpg --card-status`; wrong key →
  `git config user.signingkey`.
- **Beta toolchains lie.** A frontend crash compiling tests (Xcode-beta) can
  masquerade as your bug — get a real diagnostic with a direct
  `swift build --build-tests` before assuming fault.
- **Worktrees share the remote, not the tree** — confirm `git status` is the
  worktree you think it is before staging.
- **`npm run check` takes 10–30s cold** on Astro — expected, full rebuild.

## Project quick-reference

- **mazze-leczzare-blog**: validate `npm run check`; Cloudflare Pages
  auto-deploys main; verify title via curl on mazzeleczzare.com.
- **context-synapse**: `swift build && swift test --parallel`; main is
  PR-only + signed + squash-only + Code Scanning — always the PR path.
- **stele**: pnpm (`pnpm build`, `pnpm test`); main is PR-only + signed —
  PR path.
