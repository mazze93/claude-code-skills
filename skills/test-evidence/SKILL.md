---
name: test-evidence
description: >-
  Decide what is worth testing, prove each test can fail, and turn test runs into
  evidence that survives a rerun. Use when writing, reviewing, or planning tests;
  before declaring a bug fixed; when verifying someone else's fix, including an
  upstream or open-source PR; when probing whether a dependency honours its
  documented contract; when a test is flaky; or when results must be reported to
  maintainers and recorded. Covers what to test and at which level, tests that
  lie, the bug-first rule with a mutation step, observation-count gates for
  probes that record rather than assert, pinned and checksummed evidence runs,
  gated upstream reporting, idempotent recording, and watching a PR to close-out.
  Delegates adversarial challenge of a claim to touchstone and "what is this
  change" to corroborate.
---

# test-evidence

A test is evidence only if it could have failed. Most bad tests are not wrong;
they are unfalsifiable. This skill has two parts: **judgement** (which tests to
write and how to know they bite) and **workflow** (how to turn runs into
evidence someone else can rerun, then report and record it without duplicating).

Where a rigor skill does a step better, hand off:

| Step | Use |
|---|---|
| "Is this fix / suite / PR actually correct?" — enumerate boundaries the tests don't reach, probe them | **touchstone** |
| "What is this diff / branch / PR head, really?" before re-pinning or adopting it | **corroborate** |
| A prose draft going public (issue, PR comment) | a prose-checking skill such as prose-touchstone, if available; otherwise a line-by-line fact check against the evidence |

---

# Part 1 — Test judgement

## The one question

> **If the behaviour broke, would this test fail?**

Ask it of every test, **including your own probes**. Prove the answer by
inversion: fix → green, revert the fix → red. A test that stays green after the
revert is testing something else. Run it more than once: a probe that passes
3 of 4 times is a timing artifact, not a result.

## What earns a test

| Test it | Skip it |
|---|---|
| Logic with branches, state machines, ordering rules | Plumbing, wiring, config pass-through |
| Parsers, serializers, cursors, pagination | Getters/setters, trivial delegation |
| Boundary and validation code (and its *old* edges, see below) | Framework behaviour you don't own |
| Anything that has broken before | Code whose only failure mode is a type error the compiler catches |
| Documented contracts of a dependency you rely on | Restating the implementation line by line |

Coverage is an output, not a target. Chase behaviours, not lines.

## Pick the level by risk

| Level | Use for | Note |
|---|---|---|
| Unit | Pure logic, no I/O | Fast, many |
| Integration | Anything touching a database, storage, queue or runtime | **Real** engine: Postgres in a container; Workers, Durable Objects and D1 in real `workerd` (e.g. `@cloudflare/vitest-pool-workers`). No storage mocks |
| End-to-end | A few critical user paths | Slow and brittle; keep them few |

No ratio is enforced. The level follows where the risk lives.

**Mock only what you don't control:** third-party APIs, the clock, randomness.
A mocked data layer tests your mock. In the worked example below, every finding
came from real `workerd`; none would have shown under a mocked SQL layer.

## Tests that lie

| Lie | Tell | Fix |
|---|---|---|
| Mocks the thing under test | Assertion is on a mock's return value | Test the real unit; mock its edges |
| Snapshot as spec | Snapshot was accepted, never read | Assert the properties that matter |
| Passes with the feature removed | Delete the guard; still green | Mutation step (below) |
| No real assertion | `toBeTruthy()`, "doesn't throw", only `console.log` | Assert the exact value or state |
| Mock cascade | Mocks returning mocks returning mocks | Move it to integration |
| **Passes by coincidence** | Fixtures satisfy the right *and* the wrong implementation (ids `t1`,`t2` already sort in insertion order, so a bad tiebreak still passes) | Choose fixtures where the wrong answer differs from the right one |
| **Fails by timeout, not assertion** | Bug only shows as "test timed out after 10s" | Assert the bad state directly; a hang is slow and ambiguous evidence |
| **Observed nothing** | A probe that *records* behaviour "passed" with zero observations | Observation-count gate (below) |

## Bug-first rule, with mutation

1. Write the test that reproduces the bug.
2. Run it: it **fails, and for the expected reason** (read the message, not just the red).
3. Fix.
4. It passes.
5. **Mutate:** delete or weaken the guard the fix depends on. Some test must go
   red. If nothing fails, the fix is unguarded, whatever the test names say.
6. Commit test and fix together.

Keep step 5 as a **script**, not a one-off, so it can be rerun on a later commit
(e.g. after the PR merges or a maintainer rewrites the test). Shape:

```text
check-guard.sh <sha> — is <guard> covered by the project's OWN tests on <sha>?
baseline must pass unmutated, or exit non-zero ("verdict means nothing")
apply exactly ONE mutation; refuse if the site matches 0 or >1 times
save the mutation diff; refuse if the diff is empty
run the same tests → any failure = GUARDED, all pass = UNGUARDED
write verdict + both test-count lines + raw logs; restore the file in an EXIT trap
```

Don't grep for a test name to decide whether a guard exists; tests get renamed.

## Observation-count gate

A probe that records behaviour (logs what happened per version) instead of
asserting it can "pass" while observing nothing: a filtered console, a skipped
file, a setup step that silently failed. Declare the expected count per version
and **fail the run** if it differs. Make the conditions it depends on explicit
(e.g. vitest's workers pool drops console output unless run with
`--silent=false --reporter=verbose`).

## Probe the old edges of new validation

A fix that adds validation can turn inputs that used to work into throws, and
ship it as a patch release. For every new check, probe the inputs just outside
it on the **old** version too: `Infinity`, numeric strings, negatives, zero,
`NaN`. "Worked before, throws now" is a behaviour change worth one line in the
changelog, even when the fix is right.

## Speed and determinism

- No `sleep`, no real network, no wall-clock time, no unseeded randomness.
- Order-independent and parallel-safe: each test builds its own state.
- **Flaky test:** quarantine it (skip with a reason, an owner and an **expiry
  date**), file the fix, and fail CI when the expiry passes. Don't delete it
  silently and don't leave it retrying until green.

## CI tiers

| Tier | Runs | Budget |
|---|---|---|
| Pre-commit | Unit + lint for touched code | seconds |
| PR | Full unit + integration on real engines | minutes |
| Main / nightly | E2E, mutation checks, long probes | as needed |

## Anti-patterns

- Coverage percentage as a KPI.
- Asserting implementation (which function was called) instead of behaviour (what state resulted).
- Tests that depend on another test's leftovers or run order.
- Giant shared fixtures nobody can read; build the minimum each test needs.
- Retrying until green.

---

# Part 2 — Evidence workflow

For verifying a fix you don't own (an upstream PR, a dependency's contract), or
any result someone else must be able to rerun. Everything is keyed by **one
slug** (e.g. `<org>-<repo>-<topic>-<issue>`) used for the folder, cache dir and
every record.

## Stage 1 — Run

| Rule | Why |
|---|---|
| **Pin everything in one file**: upstream SHA, PR head SHA, tool versions, and the runtime as a **range with an upper bound** (e.g. Node 22–24) | A newer runtime broke a native dependency's build; no upper bound meant no warning |
| **Disposable clone outside the workspace** (a cache dir); results live in the evidence folder | The clone is rebuildable from pins; results are not |
| Refuse to run on a dirty clone; restore it in an `EXIT` trap | A leftover edit silently changes what "upstream" means |
| **Prove the version swap by blob hash** (`git show <sha>:<f>` then compare `git rev-parse <sha>:<f>` to `git hash-object <f>`) | Checking out the wrong file looks identical to checking out the right one |
| **Append-only runs**: `results/<UTC>-<kind>/` with raw logs, JSONL observations, `manifest.json` (pins, versions, exit codes, file hashes), `summary.md`, `SHA256SUMS`. Never edit an old run | A rerun is new evidence, not a correction |
| **Never discard install/build output** (`>/dev/null`); print the tail on failure | An install failure on an unsupported runtime was swallowed by `>/dev/null` and surfaced only later |
| **Judge success by an artifact** (the built file exists, N observations recorded), not a wrapper's exit code | A backgrounded setup died with its shell and reported nothing |
| Scripts run under `bash` with `unalias -a`; overwrite with `>|` | User shell aliases and `noclobber` break ad-hoc scripts |
| **Compare reruns by diffing sorted observations** against the previous run of the same kind | "Same result" is a diff, not a feeling |

## Stage 2 — Report upstream

1. **Channel check.** Read the target's `SECURITY.md`, `CONTRIBUTING.md` and
   code of conduct. Classify: vulnerability (private channel) or correctness
   (public issue/PR comment). Write the reasoning down, including who controls
   each input.
2. **Draft** in `drafts/<name>.md`. Claims cite a results run, with counts as
   observed ("3 of 3 runs", not "every time").
3. **Gates, in order:**
   1. Re-run the evidence on the **current** PR head (heads move while you draft).
   2. Prose check of the draft (prose-touchstone if available).
   3. **touchstone** on the claims: what did the draft leave out? (In the worked
      example it found that `read()` was affected too, not only `readBatches()`.)
4. **Explicit human go-ahead** in the current context. Never inferred from an
   earlier "sounds good" or from the task description.
5. **Post**, then **fetch the posted body back and diff it** against the file.
6. **Archive**: move the file from `drafts/` to a never-edit location, record
   URL and time, refresh `SHA256SUMS`.

Idempotency: if the archived copy already exists, it was posted. **Refuse to
post it again** and say where it went. Etiquette: one substantive comment per
stage, findings batched, no pings, no "any update?".

## Stage 3 — Record

Write durable records (your claim ledger, notes vault, or tracker, if you keep
one) as **upserts keyed by the slug**:

- **Read before write.** Fetch the existing record; skip any entry whose
  content hash is already there. A rerun must never duplicate.
- Append-only stores: append only the new phase, never rewrite old ones.
- Label the class honestly: a correctness finding filed in a security ledger
  says "correctness, not a vulnerability".
- Set a final verdict only at a terminal state (merged **and** mutation check run).

## Stage 4 — Watch, then close out

Check PR state and head on a schedule or by hand:

| Event | Action |
|---|---|
| Head changed | **corroborate** what changed; re-pin the PR SHA; re-run Stage 1; diff observations against the last run |
| Merged | Run the mutation script on the merge commit. GUARDED → record verdict, close out. UNGUARDED → draft **one** follow-up issue (back to Stage 2 gates) |
| Mutation site not found | Upstream refactored; read the code by hand before concluding anything |
| Closed unmerged | Record it; findings stay valid for the pinned SHAs |

Nothing in watch mode posts without the Stage 2 go-ahead.

---

## Worked example (compact)

cloudflare/agents issue #2853 / PR #2854 (Streams API, public). Four contract
gaps (wrong row on a `created_at` tie, async `commit` leaving neither message
nor stream, fractional `from` throwing a JSON error, `batchSize: NaN` yielding
nothing) were reproduced in real `workerd`, 3 of 3 runs, no mocks.

- **Passes by coincidence:** the tag-ordering test used ids that sort in
  insertion order, so it passed under the buggy tiebreak. That is how the first
  bug shipped.
- **Mutation:** with the `continue` after `onUpToDate` deleted, no upstream
  test failed, on the base commit or on the PR head (61 of 61 still passing).
  Kept as `check-h1.sh`, to be rerun on merge.
- **Inversion on own probes:** one probe passed 3 of 4 times (timing); another
  stayed green after reverting the fix (wrong mechanism). Both rewritten.
- **Observation gate:** probes "passed" with zero observations until the vitest
  flags above were required and the count was gated at 14 per version.
- **Fails by timeout:** on unfixed code, the PR's own validation test only failed
  on the 10s timeout, because `NaN` parked the reader.
- **Old edges:** the fix made `batchSize: Infinity` and `from: "2"` throw where
  they had worked; reported as one note after re-run, prose check, touchstone,
  and go-ahead.
- **touchstone on our own fix:** it closed the reported hole but let a late
  async write land after rollback. Superseded by upstream's fix; recorded, not
  posted.

## Perimeter

This skill decides which tests matter and makes runs trustworthy; it does not
find the boundaries a suite misses (touchstone) or establish what a change is
(corroborate). A mutation check proves one guard is covered, not that the suite
is adequate. Pinning and checksums make a run reproducible, not correct: a
wrong probe reruns wrong, which is why inversion comes first. Watch mode assumes
the upstream history isn't force-pushed; if it is, re-pin from scratch.
