#!/usr/bin/env bash
# engram-setup.sh — ENGRAM memory system setup
# Idempotent: safe to run multiple times. Existing files are never overwritten.
# Decisions: D-01=B D-02=A D-03=B D-04=A D-05=B D-06=B
# Machine: MacBook Pro M5 Pro · Apple Silicon · /opt/homebrew
set -euo pipefail

CLAUDE_HOME="$HOME/.claude"
MEMORY_DIR="$CLAUDE_HOME/memory"
ZSHRC="$HOME/.zshrc"
ENGRAM_MARKER="# ── ENGRAM"

# ── helpers ──────────────────────────────────────────────────────────────────
ok()   { printf "  \033[0;32m✓\033[0m %s\n" "$1"; }
skip() { printf "  · %s (exists, skipped)\n" "$1"; }
note() { printf "  %s\n" "$1"; }

write_if_absent() {
  local path="$1"
  local content="$2"
  if [[ ! -f "$path" ]]; then
    printf '%s\n' "$content" > "$path"
    ok "wrote: $path"
  else
    skip "$path"
  fi
}

echo ""
echo "  ENGRAM setup"
echo "  ────────────────────────────────────────────────────"

# ── 1. directory structure ────────────────────────────────────────────────────
mkdir -p "$MEMORY_DIR"
ok "directories: $CLAUDE_HOME/memory/"

# ── 2. global CLAUDE.md ───────────────────────────────────────────────────────
write_if_absent "$CLAUDE_HOME/CLAUDE.md" \
'# Claude Context — Mazze

## How to use this file
Read memory/ files for full context. This file is the entry point Claude reads
automatically. Surface a compact digest at session start using the ENGRAM skill.

## Machine
MacBook Pro M5 Pro · Apple Silicon · Homebrew: /opt/homebrew · Shell: zsh · Terminal: iTerm2

## Active Projects
See memory/projects.md for current status of all six repos:
  secure-pride · mazzeleczzare · merchants-of-war
  context-synapse · thesis-pipeline · tennis-919

## Identity & Preferences
See memory/identity.md

## Conventions
See memory/patterns.md

## Architectural Decisions
See memory/decisions.md

## Memory System
ENGRAM is active. inbox.md is append-only. Consolidate manually via the
consolidate-memory skill when inbox grows unwieldy. Never auto-consolidate.'

# ── 3. memory template files ──────────────────────────────────────────────────
write_if_absent "$MEMORY_DIR/inbox.md" \
'# Inbox
<!-- append-only. never reorganize. run consolidate-memory skill to process. -->'

write_if_absent "$MEMORY_DIR/identity.md" \
'# Identity
<!-- populate via brain-dump session -->

## Name
Mazze

## Machine
MacBook Pro M5 Pro · Apple Silicon
Homebrew prefix: /opt/homebrew
Shell: zsh · Terminal: iTerm2
git memory remote: m3.local:~/engram-memory.git

## Work Style
[TO FILL — brain-dump session]

## Key Tools
[TO FILL — brain-dump session]

## ADHD Notes
[TO FILL — friction points, workflow preferences, what helps]

## Preferences
[TO FILL — brain-dump session]'

write_if_absent "$MEMORY_DIR/projects.md" \
'# Projects
<!-- Claude-specific context per project. Project LIST lives in ~/Code/WORKSPACE.md.
     This file tracks: open questions, active work, decisions — things WORKSPACE.md does not. -->

## Source of truth
Workspace map:  ~/Code/WORKSPACE.md  (~/🚀 PROJECTS/WORKSPACE.md)
GitHub:         mazze93/projects-workspace
Domains:        tools/ · cognitive/ · creative/ · publishing/ · blog/ · secure-pride/ · templates/

## Active (run brain-dump to populate — see references/brain-dump-interview.md)

<!-- For each active project, format:
### {domain}/{name}
Status: active / maintenance / paused
Last worked on: [branch / feature / task]
Open questions: [list]
Next step: [concrete next action]
Hard stops: [any permanent constraints]
-->

### tools/meridian
Stack: Swift · SPM · Automerge-Swift · Tailscale
Status: [TO FILL]
Last worked on: [TO FILL]
Open questions: [TO FILL]
Next step: [TO FILL]

### tools/stele
Stack: React 19 · TS · Vite · Anthropic API
Status: [TO FILL]
Last worked on: [TO FILL]
Open questions: [TO FILL]

### cognitive/ContextSynapse
Stack: Swift 6.0+ · Bayesian · Core ML · local-only
Hard stop: operational context inference PERMANENTLY OUT OF SCOPE
Open questions: affect vector sync vs async (unresolved) · Lighthouse pinning (unresolved)
Status: [TO FILL]
Last worked on: [TO FILL]

### cognitive/daedalus
Stack: zsh · YAML
Status: [TO FILL]
Last worked on: [TO FILL]

### cognitive/praxis-aegis
Stack: TS · Node 20 · Express · Zod · YAML
Status: [TO FILL]
Last worked on: [TO FILL]

### blog
Stack: Astro 6 · React 19 · MDX · Tailwind 4 · Cloudflare
Status: active — PR #124 open (constellation-decay homepage)
Last worked on: [TO FILL]
Open questions: [TO FILL]

### secure-pride/secure-pride-site
Stack: Astro · TS · Cloudflare · FreeRADIUS/step-ca
Compliance: MAX — GDPR · CCPA · SOGI data protection · WCAG 2.1 AA
Status: [TO FILL]
Last worked on: [TO FILL]
Open questions: [TO FILL]

<!-- Add remaining active projects after brain-dump session -->'

write_if_absent "$MEMORY_DIR/patterns.md" \
'# Patterns
<!-- recurring conventions. add any time. consolidate when unwieldy. -->

## Code Style
[TO FILL — brain-dump session]

## Naming Conventions
[TO FILL — files, variables, branches, commits]

## Error Handling
[TO FILL]

## Testing Approach
[TO FILL — per-project or cross-project]

## Things Claude Gets Wrong
[TO FILL — corrections that have come up repeatedly]

## Cross-project Constants
- Functions do one thing
- Early returns over nested conditionals
- Side effects documented explicitly
- No stubs or TODOs in shipped code'

write_if_absent "$MEMORY_DIR/decisions.md" \
"# Decisions
<!-- format: YYYY-MM-DD · [project or global] · decision · rationale -->

$(date -I) · global · ENGRAM memory system · D-01=B D-02=A D-03=B D-04=A D-05=B D-06=B"

# ── 4. zshrc shell additions ──────────────────────────────────────────────────
if grep -qF "$ENGRAM_MARKER" "$ZSHRC" 2>/dev/null; then
  skip ".zshrc ENGRAM block"
else
  cat >> "$ZSHRC" << 'ZSHBLOCK'

# ── ENGRAM ─────────────────────────────────────────────────────────────────────

# Capture a thought to inbox without any decisions
remember() {
  if [[ $# -eq 0 ]]; then
    echo "usage: remember <text>"
    return 1
  fi
  echo "$(date '+%Y-%m-%d %H:%M'): $*" >> "$HOME/.claude/memory/inbox.md"
  echo "  → captured"
}

# Commit and push all memory files to M3 bare remote
push-memory() {
  git -C "$HOME/.claude" add -A \
    && git -C "$HOME/.claude" commit -m "consolidate $(date -I)" \
    && git -C "$HOME/.claude" push \
    && echo "  → memory pushed"
}

# Mark entries older than 60 days with [STALE] prefix (run at consolidation time)
engram-mark-stale() {
  local cutoff
  # macOS date syntax
  cutoff=$(date -v-60d '+%Y-%m-%d' 2>/dev/null \
    || date -d '60 days ago' '+%Y-%m-%d' 2>/dev/null \
    || { echo "  ✗ could not determine cutoff date"; return 1; })

  local f changed=0
  for f in "$HOME/.claude/memory"/*.md; do
    [[ -f "$f" ]] || continue
    # Add [STALE] to dated lines older than cutoff that don't already have it
    if perl -i -pe \
      'if (/^(\d{4}-\d{2}-\d{2})/ && $1 lt "'"$cutoff"'" && !/\[STALE\]/) {
         s/^/[STALE] /; $changed = 1
       }' "$f" 2>/dev/null; then
      changed=1
    fi
  done
  echo "  → stale items marked (threshold: $cutoff)"
}

# Compact digest shown on each new terminal session (D-05=B)
_engram_digest() {
  local projects="$HOME/.claude/memory/projects.md"
  local inbox="$HOME/.claude/memory/inbox.md"
  [[ -f "$projects" ]] || return 0

  echo ""
  echo "  ┄ memory ─────────────────────────────────────────────"

  # Active projects (up to 5)
  local active
  active=$(awk '/^## ACTIVE/{f=1; next} /^## /{f=0} f && /^- /{print}' \
    "$projects" 2>/dev/null | head -5 | sed 's/^-/  ·/')
  [[ -n "$active" ]] && echo "$active"

  # Last 3 inbox entries
  if [[ -f "$inbox" ]]; then
    local recent
    recent=$(grep -v '^#\|^<!--\|^[[:space:]]*$' "$inbox" 2>/dev/null \
      | tail -3 | sed 's/^/    /')
    if [[ -n "$recent" ]]; then
      echo "  inbox:"
      echo "$recent"
    fi
  fi

  # Stale warning
  local stale_count
  stale_count=$(grep -rl '\[STALE\]' "$HOME/.claude/memory/" 2>/dev/null \
    | wc -l | tr -d ' ')
  [[ "$stale_count" -gt 0 ]] \
    && echo "  ⚠  $stale_count file(s) have stale items — run consolidation"

  echo "  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
  echo ""
}

# Append to precmd array (safe on first run and idempotent thereafter)
if [[ -z "${precmd_functions[(r)_engram_digest]}" ]]; then
  precmd_functions+=(_engram_digest)
fi

# ───────────────────────────────────────────────────────────────────────────────
ZSHBLOCK
  ok ".zshrc: ENGRAM block appended"
fi

# ── 5. git init ───────────────────────────────────────────────────────────────
if [[ ! -d "$CLAUDE_HOME/.git" ]]; then
  git -C "$CLAUDE_HOME" init -q
  ok "git repo initialized: $CLAUDE_HOME"
  echo ""
  note "Set up M3 as bare remote (run these on M3 first, then here):"
  note "  M3:  git init --bare ~/engram-memory.git"
  note "  M5:  git -C ~/.claude remote add origin mazze@m3.local:~/engram-memory.git"
  note "  M5:  push-memory"
  echo ""
else
  skip "git repo ($CLAUDE_HOME/.git exists)"
fi

# ── 6. engram-stub-repo on-demand function ───────────────────────────────────
# Per-repo stubs are created on demand — workspace has 15+ projects so bulk
# creation is impractical. Use: engram-stub-repo ~/Code/{project}
# Project list is authoritative in: ~/Code/WORKSPACE.md
if grep -qF "engram-stub-repo" "$ZSHRC" 2>/dev/null; then
  skip ".zshrc engram-stub-repo function"
else
  cat >> "$ZSHRC" << 'STUBBLOCK'

# ENGRAM: create a CLAUDE.md stub in a given repo (idempotent)
# Usage: engram-stub-repo ~/Code/meridian
engram-stub-repo() {
  local repo="${1:?usage: engram-stub-repo <repo-path>}"
  local stub="$repo/CLAUDE.md"
  local name
  name=$(basename "$repo")
  if [[ ! -d "$repo" ]]; then
    echo "  ✗ not found: $repo"; return 1
  fi
  if [[ -f "$stub" ]]; then
    echo "  · $stub already exists (skipped)"; return 0
  fi
  cat > "$stub" << STUBEOF
# $name — Claude Context

Global context: ~/.claude/CLAUDE.md
Workspace map: ~/Code/WORKSPACE.md → $name

## Stack
[TO FILL]

## Compliance & Posture
[TO FILL — see WORKSPACE.md for domain posture]

## Current Status
[TO FILL]

## Active Work
[TO FILL]

## Open Questions
[TO FILL]

## Key Conventions
[TO FILL]
STUBEOF
  echo "  ✓ wrote: $stub"
}
STUBBLOCK
  ok ".zshrc: engram-stub-repo function appended"
fi

echo ""
note "Per-repo stubs: use engram-stub-repo for any project as needed."
note "  Example:  engram-stub-repo ~/Code/meridian"
note "  Full list: grep '| ' ~/Code/WORKSPACE.md | head -40"

# ── done ──────────────────────────────────────────────────────────────────────
echo ""
echo "  ────────────────────────────────────────────────────"
echo "  ENGRAM setup complete."
echo ""
echo "  Next steps:"
echo "    1.  source ~/.zshrc"
echo "    2.  Run brain-dump session to populate memory files"
echo "    3.  Set up M3 git remote (instructions above)"
echo ""
