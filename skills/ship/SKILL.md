---
name: ship
description: Ship the current project — validate, commit, push, and verify deploy. Use when asked to "ship", "release", "commit and push", or "get this live". Commits after each milestone so session-limit cutoffs never lose progress.
---

# /ship

Encodes the full release pipeline as committed milestones. Each step commits before moving to the next — a session cutoff loses at most one step, never everything.

## What it does

1. **Validate** — run the project's check/test command; surface failures before touching git
2. **Stage + commit** — stage changed files, write a descriptive commit, commit (GPG-signed if configured)
3. **Push** — push to origin main (or current branch)
4. **Verify** — confirm the remote accepted the push; note deploy URL if known

## How to use

When the user says `/ship` or asks to "ship", "commit and push", or "get this live":

1. Identify the project's validation command (from CLAUDE.md or `package.json` scripts):
   - Astro/blog: `npm run check`
   - TypeScript: `npx tsc --noEmit`
   - Generic: `npm test` or `make test`

2. Run validation first. **Do not proceed if it fails.** Show the error, stop.

3. Check git status — list what's staged and unstaged. Confirm with the user if unexpected files are present.

4. Commit with a meaningful message. Follow the project's commit style (check `git log --oneline -5`). Always include the standard trailer:
   ```
   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
   ```

5. Push. Show the exact push output (`To <remote> <sha>..<sha> main -> main`).

6. State the deploy URL if known (e.g., Cloudflare Pages auto-deploys on push to main).

## Commit discipline (milestone commits)

For multi-step work, commit after each logical unit — don't batch everything into one commit at the end. Pattern:

```
feat: add X component
fix: correct Y behavior  
chore: update Z config
```

Not:

```
WIP: lots of changes
```

## Astro/blog specific

Validation: `npm run check` (astro build + tsc — must pass)
Deploy: Cloudflare Pages auto-deploys on push to `mazze93/mazze-leczzare-blog` main
Verify live: `curl -sf https://mazzeleczzare.com/ | grep -o '<title>[^<]*</title>'`

## Gotchas

**GPG signing failures** — if `git commit` fails with a signing error:
- `gpg-agent` not running → `gpgconf --launch gpg-agent`
- Passphrase cache expired → `gpg --card-status` (if using a hardware key)
- Wrong key configured → `git config --global user.signingkey` to check

**Uncommitted changes in the wrong worktree** — always confirm `git status` output before staging. Worktrees share the remote but have separate working trees.

**`npm run check` takes 10–30s on cold build** — expected; Astro rebuilds the full static site.
