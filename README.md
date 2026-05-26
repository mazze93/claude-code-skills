# claude-code-skills

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
