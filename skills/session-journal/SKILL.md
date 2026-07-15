---
name: session-journal
description: Checkpoint discipline for long autonomous sessions — journal plan/decisions/progress to disk and commit at phase boundaries so a dropped connection or usage cutoff never loses work. Use when starting any multi-phase autonomous task, or when asked to "work with checkpoints", "make it recoverable", or "track your decisions".
---

# /session-journal

Sessions die: API drops, usage limits, closed laptops. Work that lives only in
conversation context dies with them. This skill makes every phase of a long
task independently recoverable.

## Setup (first minutes of the session, before real work)

In the repo you're working in (the workspace container uses `docs/journal/`):

- `PLAN.md` — phases, each small enough to finish and commit; known constraints.
- `DECISIONS.md` — append-only log: `date · decision · why · how to reverse`.
- `CHECKPOINT.md` — checkbox per phase, "To resume" instructions, and a
  deferred/needs-user list (auth, approvals, push queue).

Commit the scaffold immediately — the plan itself must survive a drop.

## During work

1. **Commit at every phase boundary**, not at the end. Message = phase label +
   what changed. Push if a remote exists and pushing is authorized.
2. **Decisions go in DECISIONS.md at the moment they're made** — especially
   reversals and things future-you will question ("why is X gitignored?").
3. **Tick CHECKPOINT.md in the same commit** that completes the phase.
4. Anything requiring the user (logins, destructive approvals) goes to the
   deferred list instead of blocking — keep working on other phases.
5. Sub-results that are cheap to regenerate (scans, summaries) still get
   written to files — regeneration costs budget.

## Resuming after a drop

Read CHECKPOINT.md → PLAN.md → DECISIONS.md, in that order, then continue at
the first unchecked phase. Never re-derive decisions already logged; if one
proves wrong, append a reversal entry rather than editing history.
