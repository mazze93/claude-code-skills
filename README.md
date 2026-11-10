# claude-code-skills

![Claude Code Skills](.images/claude-code-skills.png)

Personal Claude Code skills and config scripts, developed as part of [Praxis](../../cognitive/praxis/).

Skills are symlinked into `~/.claude/skills/` — Claude Code loads them automatically.
Config scripts are symlinked from their expected locations (e.g. `~/.config/iterm2/`).

## Structure

```
skills/          # ~/.claude/skills/<name> → here (symlinked)
  git-forensics/ # adversarial git forensics
config/          # operational scripts
  cc-statusline.sh  # Claude Code statusLine command
                    # ~/.config/iterm2/cc-statusline.sh → here (symlinked)
hooks/           # versioned hook scripts → ~/.claude/scripts/ (symlinked by bootstrap)
  on-prompt.sh      # v3 — UserPromptSubmit: memory injection + task classifier
  on-session-end.sh # v4 — Stop: project-aware memory write-back
  post-tool-use.sh  # v1 — PostToolUse(Edit|Write): antipattern scanner
bootstrap/       # cold-start installer — idempotent, portable, dry-run safe
  bootstrap.sh      # main entry: ./bootstrap.sh [--dry-run]
  lib/
    install-hooks.sh    # symlinks hooks/ → ~/.claude/scripts/
    install-skills.sh   # symlinks skills/ → ~/.claude/skills/
    install-settings.sh # adds PostToolUse antipattern hook to settings.json
```

## Adding a skill

```zsh
mkdir skills/<name>
# write skills/<name>/SKILL.md
bash bootstrap/bootstrap.sh   # re-run to pick up the new skill symlink
```

## Cold-start / new machine

```zsh
git clone https://github.com/mazze93/claude-code-skills.git ~/Code/tools/claude-code-skills
bash ~/Code/tools/claude-code-skills/bootstrap/bootstrap.sh
# Restart Claude Code to activate hook changes.
```

## Skill format

```markdown
---
name: skill-name
description: One-line trigger description — shown in skill list, used for invocation matching.
---

# Skill content here
```

## Marketplace

This repo is a Claude Code plugin marketplace. Add it once, then install the
bundles you want:

```
/plugin marketplace add mazze93/claude-code-skills
/plugin install rigor@mazze93
```

Six plugins over 23 skills — see [INDEX.md](INDEX.md), which is generated.

| plugin | for |
|---|---|
| `rigor` | establish what a change is, challenge a claim that it is correct |
| `workspace` | fleet and repository operations across many repos |
| `continuity` | memory and handoff so work survives a dropped context window |
| `cloudflare-suite` | Cloudflare platform and Zero Trust |
| `frontend` | design, components, performance, the blog surface |
| `lab` | probes and research aids |

### One source of truth

`.claude-plugin/skill-map.json` is the only file a human edits.
`marketplace.json`, every `plugin.json`, the plugin skill symlinks and
`INDEX.md` are generated from it:

```
python3 scripts/build_marketplace.py           # regenerate
python3 scripts/build_marketplace.py --check   # CI gate: fail on drift
```

Plugin skills are **relative symlinks** into `skills/`, not copies. Copies mean
every skill exists twice, and the day the two disagree is the day nobody can
tell which one is loaded.

**Versions are generated too.** Each `plugin.json` carries
`0.2.0-c<12 hex>`: a SHA-256 over every file the plugin ships, read through the
symlinks. Claude Code caches a plugin per version and `claude plugin update`
only refreshes it when the version string changes, so the version must move
whenever content does. Never hand-bump it; regenerate. To pick up changes on a
machine: `claude plugin marketplace update mazze93`, then
`claude plugin update <plugin>@mazze93`.

### Guards

Every one of these exists because of a failure that already happened here.

| guard | defends against |
|---|---|
| `scripts/check_revert.py` | a change that silently restores an older version of a file. On 2026-08-31 a skill install wrote through a symlink and replaced two consolidated `SKILL.md` files with pre-consolidation copies — a `+149/-16` diff that read as new work and was a revert of a 10-into-2 consolidation |
| `scripts/validate_marketplace.py` | name collisions, double-claimed skills, orphans that ship to nobody, missing or too-thin frontmatter, dangling symlinks. It caught a plugin named the same as a skill on its first run |
| `scripts/build_marketplace.py --check` | a generated artefact hand-edited into drift |
| `scripts/tests/test_build_marketplace.py` | a plugin version that doesn't move when its content does. Until 2026-11-10 every plugin was hardcoded `0.1.0`, so `claude plugin update` never refreshed an install: `rigor` stayed at an October copy missing three of its skills. The tests follow the skill symlinks, and three of them were mutation-checked |
| `scripts/skill_writethrough_check.sh` | an installer writing through a `~/.claude/skills` symlink into this working tree — the mechanism behind the 2026-08-31 incident |

Install the pre-commit hook so the first three run before every commit:

```
ln -sf ../../scripts/hooks/pre-commit .git/hooks/pre-commit
```

CI runs the same three on every push and PR, with `fetch-depth: 0` because
`check_revert` needs history rather than a shallow clone.

### Why the installed namespace matters

`~/.claude/skills` is flat, and mixes symlinks into this repo with real
installed directories. Anything installing a skill *by name* will write
**through** a symlink into this working tree, silently, and it looks like
ordinary local edits afterwards. That is the whole reason for the collision
guard and the revert detector.
