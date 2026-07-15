---
name: workspace-sync
description: Reconcile the ~/Projects workspace against WORKSPACE.md and GitHub — clone missing repos into their domains, report drift, add/move projects with map-and-territory discipline. Use when asked to "sync the workspace", "clone my repos", "add a repo to the workspace", or "check workspace status".
---

# /workspace-sync

The workspace root `~/Projects` (alias `~/Code`) is a thin container repo
(`mazze93/projects-workspace`); every project is a sibling clone under a domain
dir. `WORKSPACE.md` is the map and the intent — **if disk and map disagree,
reconcile toward the map.**

## Commands (all via `~/Projects/scripts/ws`)

```sh
scripts/ws list      # registry vs disk (✓/✗)
scripts/ws status    # dirty/ahead/behind across every clone
scripts/ws sync      # ff-pull every clean clone (dirty ones skipped, never touched)
scripts/ws missing   # clone absent registry entries into their domain paths
scripts/ws open <q>  # fuzzy-open a project in Zed
```

## Adding a new project (the contract, rule 3)

1. Decide its domain: blog/ apps/ tools/ cognitive/ creative/ secure-pride/
   skills/ templates/ meta/ archive/. Doesn't fit? STOP and ask — never invent
   a top-level dir.
2. In the SAME commit to the container: add its row to the WORKSPACE.md
   registry AND its `"path|repo"` line to the REGISTRY array in `scripts/ws`.
3. `scripts/ws missing` to clone it. Commit message: `map: add <name> to <domain>/`.

## Moving / retiring a project

Same-commit rule applies: `mv` the dir, update both registry locations,
commit. Retired repos go to `archive/`, not deleted.

## Full resync on a fresh machine

```sh
gh auth login
gh repo clone mazze93/projects-workspace ~/Projects
cd ~/Projects && bash scripts/install-hooks.sh && bash scripts/ws missing
ln -sfn ~/Projects ~/Code
```

## Guardrails

- Never `git add` a project into the container — the allowlist .gitignore and
  pre-commit hook will fight you; they are right.
- secure-pride/* stays in private repos; never log identifiers unmasked.
- New GitHub repos that are empty (0 KB) are listed under "Not cloned" in
  WORKSPACE.md rather than cloned.
