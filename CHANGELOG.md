# Changelog

## [Unreleased]

### Added
- `skills/cloudflare/` and `skills/cloudflare-one/` — Cloudflare-authored skills, vendored for local versioning. Third-party content with no bundled LICENSE; verify redistribution terms before pushing this repo publicly.

### Changed
- Consolidated the Cloudflare skill set 10 → 2. `agents-sdk`, `cloudflare-email-service`, `durable-objects`, `sandbox-sdk`, `turnstile-spin`, `wrangler`, `workers-best-practices` folded into `cloudflare/references/` (each former `SKILL.md` preserved as `<product>/guide.md`, Turnstile as `turnstile/spin.md` with its `scripts/` and `tests/`); `cloudflare-one-migrations` folded into `cloudflare-one/references/migrations.md`. `cloudflare-one/SKILL.md` split 22KB → 3KB router + `references/{assessment,guardrails,validation,migrations}.md`.
- Skill listing cost: ~2,525 → ~1,671 est. resident tokens per session, back under the ~1% context budget where entries start being truncated.

- `hooks/post-tool-use.sh` v1 — PostToolUse(Edit|Write) antipattern scanner: innerHTML assignment with non-literal RHS, Linux `/home/` paths, SQL string interpolation; project-aware validation reminders (npm run check / swift build)
- `hooks/on-prompt.sh` v3 — portability fix: MEMORY_DIR path derived from `$HOME` via sed instead of hardcoded slug
- `hooks/on-session-end.sh` v4 — canonical copy of `~/.claude/scripts/on-session-end.sh`; already portable
- `bootstrap/bootstrap.sh` — orchestrator; idempotent, portable (`$HOME` throughout), dry-run safe; calls install-hooks/install-skills/install-settings
- `bootstrap/lib/install-hooks.sh` — symlinks on-prompt/on-session-end/post-tool-use into `~/.claude/scripts/`; creates `mem-map.conf` if missing
- `bootstrap/lib/install-skills.sh` — symlinks each `skills/*/` dir into `~/.claude/skills/`; symlinks `cc-statusline.sh` into `~/.config/iterm2/`
- `bootstrap/lib/install-settings.sh` — surgically adds PostToolUse antipattern hook to `settings.json` via jq; backs up settings before writing; preserves all existing config

### Context
Implemented from `/insights` session analysis (2026-05-26). All scripts are idempotent (check before act), transferrable (`$HOME` throughout, no hardcoded paths), and elegant (each sub-script self-contained; main entry orchestrates only).

## [1.0.0] — 2026-05-22

### Added
- Initial repo: `skills/git-forensics/` — adversarial git forensics skill
- `config/cc-statusline.sh` — Claude Code statusLine command (iTerm2 integration)
