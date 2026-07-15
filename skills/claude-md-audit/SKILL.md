---
name: claude-md-audit
description: Audit CLAUDE.md files across one or many repos for stale information — dead path references, obsolete workspace roots, old model names, drifted file maps. Use when asked to "audit CLAUDE.md", "check for stale docs/instructions", or after restructuring a repo.
---

# /claude-md-audit

CLAUDE.md files drift: repos get restructured, machines get replaced, and the
instructions keep describing a world that no longer exists. Drifted agent
instructions are worse than none — agents obey them confidently.

## Method (two lanes, budget-aware)

**Lane 1 — deterministic (cloud Claude or plain script; this is the verdict lane):**

Run `scan.py` from this skill's directory against the workspace root:

```sh
python3 ~/.claude/skills/claude-md-audit/scan.py ~/Projects
```

It flags, per CLAUDE.md:
- backticked path references that don't exist on disk (verify each hit —
  shorthand like `blog/PullQuote.astro` and enums like `plan/implement/review`
  are false positives)
- stale workspace roots (`🚀 PROJECTS`, submodule-era language)
- old model-generation strings (claude-3, sonnet-3, …)
- last-updated dates

**Lane 2 — on-device summaries (Ollama, zero budget):** POST each file to
`http://localhost:11434/api/generate` (model `gemma4` or better) asking for a
2-3 sentence summary + anything time-sensitive. Summaries give reviewers
orientation; they are NOT verdicts — a small model's staleness opinions are
unreliable. Never let Lane 2 output change a verdict without Lane 1 evidence.

## Always check first

`~/.claude/CLAUDE.md` **exists**. Every repo defers postures/hard-stops to it;
on a fresh machine it silently vanishes and 90% of the posture goes with it
(this happened — see the tessera-claude-anchor record).

## Output

Write `docs/audits/claude-md-audit-<date>.md` in the container: a Critical
section, a per-repo verdict table (STALE/clean + evidence lines), and a
recommended-fixes list. **Flag, don't auto-rewrite**: each CLAUDE.md rewrite
changes agent behavior in that repo and deserves review in that repo's context.
