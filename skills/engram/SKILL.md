---
name: engram
description: >-
  Memory-as-first-class system for Claude sessions across a multi-domain
  workspace (~15+ active projects). USE THIS SKILL for: (1) setting up ENGRAM
  on a new device ("set up ENGRAM", "install memory system", "set up my
  context", "set up memory"); (2) capturing thoughts in-session ("remember X",
  "add to memory", "note that", "log that", "capture this"); (3) surfacing
  project context ("what's my context", "surface my memory", "what am I working
  on", "restore context", "what do I know about X"); (4) inbox consolidation
  ("consolidate my memory", "process my inbox", "clean up memory"); (5) creating
  per-repo CLAUDE.md stubs. Trigger when any workspace project is mentioned and
  context appears missing. Trigger on new-device setup and memory restoration.
  Workspace source of truth: ~/Code/WORKSPACE.md
---

# ENGRAM — Memory System

Inbox-first, file-native memory layer for Claude sessions. Plain Markdown in
`~/.claude/`. Claude reads it automatically. You capture without decisions.

---

## Locked Configuration

These decisions are final. Do not re-litigate them.

| ID | Decision | Choice |
|----|----------|--------|
| D-01 | Capture interface | Both: shell alias + natural language in-session |
| D-02 | Storage format | Pure Markdown — no YAML frontmatter |
| D-03 | Project scoping | Global + per-repo on demand (15+ projects — stubs created as needed) |
| D-04 | Consolidation | Manual on-demand only |
| D-05 | Session ritual | zsh `precmd` hook — auto-surface on terminal open |
| D-06 | Memory decay | Soft: `[STALE]` prefix after 60 days, at consolidation time |

Machine constants: MacBook Pro M5 Pro · Apple Silicon · `/opt/homebrew` · iTerm2 · zsh
Workspace: `~/🚀 PROJECTS` (alias `~/Code`) · Map: `~/Code/WORKSPACE.md` · Repo: `mazze93/projects-workspace`

---

## File Architecture

```
~/.claude/
├── CLAUDE.md              ← Claude reads this automatically (Claude Code + Cowork)
└── memory/
    ├── inbox.md           ← append-only capture log; never reorganized manually
    ├── identity.md        ← who Mazze is, machine config, preferences
    ├── projects.md        ← Claude-specific context per project (status, open questions, decisions)
    ├── patterns.md        ← recurring conventions across projects
    └── decisions.md       ← architectural decisions log

~/Code/{repo}/
└── CLAUDE.md              ← per-repo scoped context; created on demand via engram-stub-repo

~/Code/WORKSPACE.md        ← authoritative project registry (source of truth for project list/domains)
```

---

## Mode Routing

Identify the mode from user intent, then execute that mode's steps in full.

| User signal | Mode |
|-------------|------|
| "set up ENGRAM", "install memory system", first-time setup on new device | → **Setup** |
| "run brain-dump", "rebuild my context", "interview me for context" | → **Brain-dump** |
| "remember X", "add to memory", "note that", "log that", "capture this" | → **Capture** |
| "consolidate", "process my inbox", "clean up memory" | → **Consolidate** |
| "what's my context", "surface memory", session start, project name + missing context | → **Surface** |

---

## Mode 1 — Setup

Run on first-time setup or reinstall on a new device.

1. Read `references/setup-script.sh`.
2. Write the script to `~/engram-setup.sh` using the Write tool, or present it for the user to copy if write access is unavailable.
3. Tell the user to run:
   ```bash
   chmod +x ~/engram-setup.sh && ~/engram-setup.sh
   ```
4. After the script completes, ask: "Run brain-dump session now to populate memory files, or continue later?"
5. If now → go to **Brain-dump** mode.

**If M3 is accessible (transfer path):**
Run this first, before the setup script, so existing files are not overwritten:
```bash
rsync -av --progress ~/.claude/ mazze@m3.local:~/.claude/
# direction: M3 → M5 Pro (you are on M5 Pro, pulling from M3)
rsync -av --progress mazze@m3.local:~/.claude/ ~/.claude/
```
Then run the setup script to scaffold any missing files and install shell additions.

---

## Mode 2 — Brain-dump

Populate all memory files from scratch via structured interview.

Read `references/brain-dump-interview.md` and run the full interview. Do not skip or batch sections. After each section, write the corresponding file before moving to the next. All writes use the Write tool (or Bash echo for appends).

Files produced in order:
1. `~/.claude/memory/identity.md`
2. `~/.claude/memory/projects.md`
3. `~/.claude/memory/patterns.md`
4. `~/.claude/memory/decisions.md`
5. `~/.claude/CLAUDE.md` — synthesized last, from the four above

**Post-M3-transfer variant:** Use the interview to *update* files rather than replace. Identify stale content, add missing context, and prefix outdated entries with `[STALE]`.

---

## Mode 3 — Capture

Handle natural-language memory capture mid-session.

1. Extract the core fact, decision, or context item from the user's message.
2. Format it: `YYYY-MM-DD HH:MM: [content]`
3. Append to `~/.claude/memory/inbox.md` via Bash:
   ```bash
   echo "$(date '+%Y-%m-%d %H:%M'): [content]" >> ~/.claude/memory/inbox.md
   ```
4. Confirm: `→ captured to inbox`

**Rules:**
- Never categorize, tag, or route at capture time. Inbox is append-only.
- Never modify any file other than `inbox.md` in this mode.
- If running in Cowork without shell access to `~/.claude/`, output the formatted entry as text for the user to paste manually.

**Shell path** (wired by setup script — no action needed):
```bash
remember "text here"
```

---

## Mode 4 — Consolidate

Run when the user explicitly requests consolidation. Never run automatically.

1. Invoke the `consolidate-memory` skill to process `inbox.md` → structured files.
2. After consolidation, run stale decay marking:
   ```bash
   engram-mark-stale   # installed by setup script
   ```
3. If git remote is configured, push:
   ```bash
   push-memory         # installed by setup script
   ```
4. Report: entries processed, stale items flagged, git push status.

**Stale decay rule:** Any dated entry (line beginning `YYYY-MM-DD`) older than 60 days receives a `[STALE]` prefix. Items are never deleted automatically. The user triages `[STALE]` items manually at the next consolidation.

---

## Mode 5 — Surface

Present a compact context digest. Read directly from files — never infer or fabricate.

**Format:**
```
── ENGRAM ────────────────────────────────────────
Machine: M5 Pro · /opt/homebrew · iTerm2 · zsh

Active projects:
  · [list from projects.md ## ACTIVE section]

Last inbox entries:
  [last 3 non-blank, non-comment lines from inbox.md]

[If project-scoped]: {Project} context:
  Stack:          [from per-repo CLAUDE.md]
  Status:         [active / maintenance / paused]
  Open questions: [list]

[If stale items exist]: ⚠ stale items present — run consolidation
──────────────────────────────────────────────────
```

If a memory file is missing, say so explicitly: `identity.md not found — run brain-dump to populate.` Do not guess at content.

---

## Guardrails

- **Never overwrite** existing memory file content outside of Mode 2. Inbox is append-only. Structured files are updated only via the consolidate-memory skill.
- **Never fabricate** project context not present in memory files. Missing context is surfaced as a gap, not filled in.
- **No auto-consolidation.** D-04 = manual. Consolidation requires explicit user request.
- **precmd digest stays compact:** ≤8 lines. Verbose terminal output defeats the purpose.
- **All paths use `$HOME`** — never hardcode `/Users/mazze/`.
- **`[STALE]` is additive:** prefixes are added, never removed automatically.
- **Per context-synapse:** operational context inference is a permanent hard stop. Never suggest, implement, or discuss it.
- **Per secure-pride:** any auth, identity, or data-handling change requires explicit GDPR/CCPA/SOGI compliance check before proceeding.

---

## References

- `references/setup-script.sh` — complete idempotent bash setup script
- `references/brain-dump-interview.md` — structured interview, 5 sections, workspace-aware (reads WORKSPACE.md)
- `references/repo-stubs.md` — generic + domain-specific CLAUDE.md templates; use engram-stub-repo for any project
