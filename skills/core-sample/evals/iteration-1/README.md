# Iteration 1 — ungraded

> **Historical evaluation artifact — not installation instructions.**
> The saved hook scripts and settings below predate the opt-in capture lifecycle
> adopted for PR #6. Do **not** install their global `settings.json` hooks.
> The canonical `skills/core-sample/SKILL.md` now defines skill-scoped
> registration, explicit arm/disarm and capture-off-by-default semantics.
> These snapshots remain unchanged as evaluation evidence.

| Eval | with_skill | without_skill |
|---|---|---|
| query-existing-ledger | complete | complete |
| install-capture-hook | complete | complete |
| record-a-compacted-session | **interrupted** — the person declined the run mid-way; it had scaffolded the session folder and started reconstructing export pages from the transcript | **interrupted** — had copied the input transcript, nothing else |

What the completed runs showed (not yet graded against assertions):

- **query-existing-ledger does not discriminate.** Both runs found the same 4
  unflagged failures and named the claim layer as the most common escape (3 of 6),
  and both caught two ledger inconsistencies (F30's detection vs its call's
  outcome; E14-007 unlinked). The database structure does the work either way.
  Replace this eval with one that needs the skill's procedure (capture + annotate).
- **install-capture-hook, with_skill** found three real defects in the skill's own
  hook (session_id path traversal, dict-valued secrets unredacted, parent folders
  0755) — fixed in commit `d2163df`, pinned by tests that fail on the previous hook.
  It also corrected the matcher (`"*"`, not `".*"`) from the docs.
- **install-capture-hook, without_skill** produced a different design (capture +
  restore-into-context on SessionStart) and ran a live `claude -p`, which wrote a
  transcript and a `.claude.json` backup into the host's `~/.claude`. Evals that
  can launch Claude Code need an isolated HOME.

Removed before commit: raw transcript copies made by the interrupted runs (private
session data; public repo).
