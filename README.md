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
```

## Adding a skill

```zsh
mkdir skills/<name>
# write skills/<name>/SKILL.md
ln -s ~/Code/tools/claude-code-skills/skills/<name> ~/.claude/skills/<name>
```

## Skill format

```markdown
---
name: skill-name
description: One-line trigger description — shown in skill list, used for invocation matching.
---

# Skill content here
```
