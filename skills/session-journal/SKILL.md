---
name: session-journal
description: Checkpoint discipline for long autonomous sessions — journal plan/decisions/progress to disk and commit at phase boundaries so a dropped connection or usage cutoff never loses work. Use when starting any multi-phase autonomous task, or when asked to "work with checkpoints", "make it recoverable", or "track your decisions".
---

# /session-journal

Sessions die: API drops, usage limits, closed laptops. Work that lives only in
conversation context dies with them. This skill makes every phase of a long
task independently recoverable.

## Phase 0 — pre-flight (before the scaffold)

Deliver four things, then stop and wait for go-ahead:

1. The request restated in your own words.
2. The exact files/repos the work will modify.
3. One load-bearing assumption that could be wrong.
4. The result of checking that assumption against the filesystem or docs.

Write all four into the scaffold, not just into the conversation: (1) and (2)
become PLAN.md's header, (3) and (4) become DECISIONS.md's first dated entry. A
verification that lives only in chat dies with the session.

**Also append one row to `docs/journal/INTENTS.md`** (create it from the header
in an existing copy if absent): today's date, the restated ask (1), the
load-bearing assumption (3), `outcome: —`, blank last column. This is the
stated intent, recorded before contact — so the gap between it and what ships
is measurable instead of forgotten. Do this even for a single-phase task.

The assumption most worth checking is almost always **whether the thing you're
about to build already exists.** Prompts and generated reports describe generic
gaps, not this machine — this skill, the container's journal, and the
unpushed-work Stop hook have each been proposed as new work after they already
existed.

## Setup (first minutes of the session, before real work)

In the repo you're working in (the workspace container uses `docs/journal/`):

- `PLAN.md` — phases, each small enough to finish and commit; known constraints.
- `DECISIONS.md` — append-only log: `date · decision · why · how to reverse`.
- `CHECKPOINT.md` — checkbox per phase, "To resume" instructions, and a
  deferred/needs-user list (auth, approvals, push queue).

Commit the scaffold immediately — the plan itself must survive a drop.

### When there's no git repo (e.g. a cleanup/ops task in a plain directory)

The journal's value was never the git history — it's that **state lives on disk
instead of in conversation context**. With no repo you lose the phase-boundary
commit trail, so compensate:

- Put the three files in a durable, non-scratchpad location (a dedicated
  `*-journal/` dir under the task's working area). Scratchpad dirs are
  session-scoped and won't survive the drop you're guarding against.
- **Date-stamp every entry** and keep DECISIONS.md strictly append-only, so
  recovery order is reconstructable from timestamps alone — the stamps stand in
  for the commit trail.
- Update CHECKPOINT.md's "Last updated" line as your ordering signal in place of
  the commit that would otherwise tick it.

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

## Closing out

Before the session ends — the moment work is done, or the moment you realise it
won't be — set the `outcome` on this session's `docs/journal/INTENTS.md` row:

- `as-stated` — shipped roughly what was asked, as specified.
- `diverged` — shipped something else; say what, in the last column. (This is
  the common case. It is not a failure — it is the record being honest.)
- `abandoned` — stopped without shipping. Blocked, out of budget, superseded.

A row left `—` means the session dropped before it could close itself out —
which is itself the record. Do not backfill someone else's `—` row with a
guess; leave it, and let `ws abandoned` surface it.

## Resuming after a drop

Read CHECKPOINT.md → PLAN.md → DECISIONS.md, in that order, then continue at
the first unchecked phase. Never re-derive decisions already logged; if one
proves wrong, append a reversal entry rather than editing history.

If this session's own `INTENTS.md` row diverged from the row you're resuming
under, that divergence is the point — record it in the last column at close,
don't quietly rewrite the intent to match what happened.
