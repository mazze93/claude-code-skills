---
name: touchstone
description: Apply an adversarial verification posture to any claim of correctness, completeness, or "passing" status — tests, proofs, invariants, security reviews, audits, or a "this is resolved" / "this is safe" assertion. touchstone does not accept N/N passing as sufficient; it enumerates the boundaries the existing proof doesn't reach, builds concrete probes against the highest-risk ones, and reports honestly whether they held. Use this skill whenever the user asks to verify, audit, stress-test, adversarially probe, or sanity-check a claim of correctness or completion — including phrases like "is this actually done," "does this actually work," "find the hole in this," "before I ship this," "is this really verified," or when reviewing test suites, security findings, proofs, invariants, or any status marked "closed," "verified," or "resolved." Also trigger when a claim is stated with unusually high confidence (100%, all tests green, fully verified, no known issues) — exactly the pattern this skill exists to challenge.
---

# touchstone

A touchstone is the stone historically used to assay gold — rub the metal across it, read the streak, tell real from fool's gold. It also means "the standard by which a thing is judged." Both senses apply here.

## What this skill is for

touchstone adversarially challenges a claim of correctness, completeness, or "passing" status before it gets treated as settled. It does not accept N/N-style proof (all tests green, 100% coverage, "fully verified," "closed") as sufficient on its own. Its job is to find the boundaries the existing proof doesn't reach, probe the ones that matter, and report the result honestly — including when the probes hold and the original claim was right.

The pattern this skill exists to catch, stated plainly: 8/8 tests passing missed five real cases. 16/16 was genuinely verified, but the 17th case was a boundary nothing had named. The tool built to prove the headline invariant turned out blind to its own failure mode. None of these are failures of rigor exactly — they're the predictable shape of what verification misses when "all checks passed" gets treated as the finish line instead of a snapshot.

## Workflow

1. **Name the claim.** State precisely what is being asserted — correct, complete, safe, resolved, passing, verified. Vague claims ("this should work") get made precise before anything else happens. Include the claim's declared scope: a claim of "correct on macOS" has a different perimeter than "correct."
2. **Name the proof.** What evidence is being offered — a test suite, a formal invariant, a security review, a "closed" status, a human sign-off?
3. **Enumerate the boundaries the proof doesn't reach.** Every proof has assumptions — input shapes, orderings, environments, threat models — that it doesn't cover by construction. List the candidate boundaries explicitly (the taxonomy below is the working checklist), then rank them by likelihood-of-gap × impact-if-wrong. Don't stop at the first boundary that comes to mind; the first one is usually the one the original authors also thought of.
4. **Probe the highest-ranked boundaries — concretely.** Scale to stakes: one probe for a routine claim, two or three for security-critical or ship-blocking claims. A probe is not a hypothetical — it is an actual test case, adversarial input, script, or fully walked-through scenario that could fail if the claim is wrong. If code is involved, write it and run it. If nothing runnable exists (a design doc, a process claim), the probe is a concrete counterexample scenario traced step by step to its outcome — not a vibe of doubt.
5. **Report the result plainly.** If the probes hold, say so — don't manufacture doubt to look rigorous. If one fails, name exactly what broke, why the original proof didn't catch it, and whether it's a real gap or an inherent, acceptable perimeter given the claim's declared scope.
6. **Bounded recursion on fixes.** A failed probe leads to a fix, and the fix is itself a new correctness claim. Run one more touchstone pass on the fix — probe that it resolves the found gap without narrowing the original proof (regressions, weakened assertions, deleted tests). One re-pass, not an infinite spiral; if the second pass also fails, the finding is "unstable under repair" and the claim escalates to the human rather than looping.
7. **Document the remaining perimeter.** State what this pass did *not* check. A touchstone that claims to have verified everything has become the next hollow checkmark.

## Boundary taxonomy

The classes of assumption proofs are structurally blind to. Use as a checklist in step 3 — most claims have live boundaries in two or three of these:

- **Input domain edges** — empty, maximal, malformed, zero/negative, encoding and Unicode normalization, boundary-of-the-boundary (N works; what about N−1 and N+1?)
- **State and ordering** — operations in an unexpected sequence, re-entry, idempotency under retry, partial failure midway through a sequence
- **Concurrency and time** — races, clock skew, timeout edges, check-then-act windows
- **Environment** — the delta between where the proof ran and where the claim will live: config drift, permissions, locale, missing dependencies, platform differences
- **Adversarial vs. accidental** — the proof assumed honest inputs; the probe assumes an attacker shaping them
- **Spec–implementation gap** — the tests verify what the code *does*, not what it *should* do; the oracle (expected values, fixtures) may itself encode the bug
- **The verifier's own blind spot** — who tests the test harness; mocks that hide real behavior; coverage counted in lines rather than behaviors; the assay tool blind to its own failure mode
- **Composition** — each unit verified in isolation; the seam between them never exercised together

## Anti-patterns

Two degenerate moves defeat the skill while looking like rigor:

- **Re-assaying covered ground.** Probing a boundary the existing proof already exercises produces a guaranteed "held" and verifies nothing new. The probe must target territory the proof does not reach — that's the whole point of step 3.
- **Strawman boundaries.** Probing something the claim explicitly excludes ("the macOS-only tool fails on Windows!") and reporting it as a finding. Out-of-scope boundaries belong in the perimeter report as scope confirmation, not in the verdict as failures. The distinction from step 5 applies: a real gap violates the claim *as scoped*; an acceptable perimeter sits outside it.

## Probe-harness gotchas

Once you are actually building probes, these are the ways a probe lies. Each one came from a real pass where the first reading was wrong.

- **Assert the precondition before reading the result.** A probe whose setup failed silently reports "held" for a test that never ran. In one pass, three of four attempts to create a concurrent-writer state failed: one CLI flag didn't exist in that version, `ls` was aliased to a tool with different flags (so a captured ID came back empty), and zsh `noclobber` refused a redirect. Each time the "after" state matched the "before" state, which looks exactly like a pass. Print the state the probe depends on (`expect heads=2`) and confirm it before reading anything else. Inside a probe, call binaries by full path (`/bin/ls`), and don't trust captured values that could be empty.
- **Measure the store, not the flag.** For claims like "read-only", "no side effects" or "doesn't write", count the state directly before and after: files in the store, op-log length, row count, mtime. Don't infer it from what an option is documented to do. Documentation describes the common path. A flag that skips one kind of write (a working-copy snapshot) can leave another enabled: under contention, the "read-only" query still wrote a reconciliation record.
- **The author's verification probe is part of the proof, not a probe.** When the claim arrives with its own check ("I tested it; the operation ID didn't change"), name the state that check ran in. Authors test the easy state: one writer, a clean tree, a quiet system. Re-create the state the claim has to survive in production: contention, divergence, partial failure. Re-running their check is the re-assaying anti-pattern applied to someone else's work.
- **Ask what the real producer emits that a hand-written fixture never would.** Fixtures are written by someone who imagines meaningful input, so every fixture has content. Real workflows produce degenerate-but-routine items constantly: empty placeholders, zero-length records, auto-created stubs. A collector "verified" against fixtures that all had content recorded every empty placeholder change as a full-value event. These items aren't rare edge cases; in normal use they are the commonest input.
- **Swap the side-effecting dependency for a recorder.** To see what a script *would* do without letting it do it, point it at a stub that just appends its arguments to a log, and run it in a disposable copy of the environment (a scratch repo, a throwaway user, a temp home dir). This turns "it would record X" into an observed line of output. It also keeps the probe off real data.
- **When a probe fails, check whether real data is already affected.** Before reporting, look at whether the defect has already reached production data, and count how much, read-only. A ledger already holding one invalid event changes the finding from "latent bug" to "data needs a dated correction". Report it as evidence; don't quietly clean it up.

## Worked example (compact)

- **Claim:** `sanitizeFilename` is fully verified — 16/16 tests pass.
- **Proof:** unit suite covering path traversal, null bytes, length limits. All inputs ASCII.
- **Boundaries enumerated:** Unicode normalization (NFC/NFD collision), platform-reserved names, composition with the downstream writer. Ranked: reserved names highest — cross-platform is in the claim's scope and untested.
- **Probe:** `sanitizeFilename("CON.txt")` → passes through unchanged.
- **Verdict:** did not hold. Valid filename on macOS, unwritable on Windows; the proof's boundary was "ASCII, POSIX semantics" and nothing had named it. Real gap, because the claim was cross-platform. Had the claim been scoped macOS-only, this would be perimeter, not failure.

## Reporting format

Lead with the verdict, not the process:
- **Held / did not hold** — one line.
- **Boundaries enumerated and which were probed** — the ranking reasoning, briefly.
- **What broke, if anything** — specific, not general.
- **Perimeter** — what this pass did not check, including out-of-scope boundaries confirmed as out of scope.

Skip the ceremony if the claim is trivially true. This skill is for claims with real stakes — security, correctness-critical logic, "ready to ship" status — not for wrapping adversarial theater around simple facts.

## Perimeter of this skill itself

This is a reasoning discipline, not a formal verification tool — it can only find boundaries the reviewer (human or Claude) can actually conceive of; the taxonomy widens that reach but does not complete it. It does not guarantee exhaustive coverage. Applying it superficially — one token probe against the first boundary named, declared sufficient — recreates the exact failure mode it exists to prevent. It works best on claims with definite, checkable structure (code, protocols, proofs); on subjective or open-ended claims it degrades into ordinary skepticism, which is still useful but should not be mistaken for the same rigor.
