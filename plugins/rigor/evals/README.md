# rigor eval suite

Run: `claude plugin eval plugins/rigor --trust-plugin --threshold 0.8 --allow-tools Bash -j 3`
(`--allow-tools Bash` needs `bubblewrap` + `socat`; the harness refuses an unconfined shell.)
`results/` is local output — do not commit it.

## Cases

| Case | Skill | Tests |
|---|---|---|
| `touchstone-nn-claim` | touchstone | 16/16 ASCII-only claim, real buggy code; must run a probe via Bash and find a defect |
| `touchstone-trivial-claim` | touchstone | trivially true claim gets no adversarial theater |
| `touchstone-strawman-scope` | touchstone | out-of-scope OS is perimeter, not a finding |
| `corroborate-revert-diff` | corroborate | +149/-16 diff that is an older copy written back |
| `corroborate-no-authority` | corroborate | nothing to consult → "needs a human" |
| `decision-telemetry-no-source` | decision-telemetry | no source → no fabricated shadow faces, empty Da'ath |
| `decision-telemetry-recon-certainty` | decision-telemetry | RECON tag with conf ≥ 0.80 is a contradiction |

Every case carries a `run-not-errored` guard (weight 3). Without it, an API-error run
is graded by an LLM judge that finds "no fabricated content" and scores it 1.00.

## Results (2026-10-04, 2 runs/case, with-plugin vs baseline)

6/7 cases ≥ 0.80, overall 0.91. **`decision-telemetry-no-source` fails (0.40)**: with the
plugin loaded, 2/2 runs hit an API safeguard (`reasoning_extraction`) on Sonnet 5.5; the
no-plugin arm passes 2/2. Reproduced in 3 separate suite runs. Real, unresolved.

## What this suite does NOT establish (touchstone pass on the eval itself)

1. **It cannot distinguish a working skill from a broken one.** Mutation test: with
   `touchstone` rewritten to "N/N = verified, never probe, never state a perimeter",
   `touchstone-nn-claim` still scored 0.89; with `corroborate` rewritten to "diff is the
   authority, always `git add -A`", both corroborate cases scored 1.00 (skill fired).
   The model overrides a harmful skill from base competence. Ablation delta is 0.00 on 6/7
   cases; the only positive (+0.12) is a wording regex, not behavior.
   Fix direction: cases where the skill's *conventions* diverge from model default
   (report format, tag vocabulary, weight bounds), where a benign mutant is not overridden.
2. **corroborate is graded on reading, not investigating.** Evidence is pasted into the
   prompt; the skill's value is making the artifact testify (run `git log -S`, hash both
   sides). Needs a `--scaffold` git-repo fixture.
3. **decision-telemetry's build phase is untested.** The canonical `tree-of-knowledge.html`
   was missing from the skill directory (SKILL.md pointed at `skills/tree-of-knowledge.html`);
   it is now added beside SKILL.md. Phase 4 run against it (static, via node): all faces tagged,
   no RECON face ≥ 0.80 — **but** (a) all 4 ghost edges are drawn over paths already in
   `BG_PATHS`, and ghost (1,3) is also an *active* path, so a "road not taken" is drawn on a road
   taken; (b) each ghost edge's `note` (the attestation) is never rendered, so the skill's
   "attested, not invented" rule is unverifiable by a viewer; (c) node 9 is tagged RECON yet
   carries a verbatim quote (skill: verbatim quote ⇒ TRACE); (d) the footer calls every shadow face
   "the actual deliberation trace" while 2 of 10 are RECON; (e) no keyboard access (no
   tabindex/role/keydown, no `aria-pressed` on DESCEND); (f) fonts load from absolute `/fonts/`,
   so the copy in this repo renders in fallback faces outside mazzeleczzare.com.
4. **touchstone step 6 (bounded re-pass on a fix) and the "re-assaying covered ground"
   anti-pattern are untested.**
5. n = 2 per arm, haiku judge, 3 votes. Variance between runs was unmeasured (scores were
   identical run-to-run, which is itself suspicious).
6. Errors other than API errors (empty reply, max_turns exhausted) are not guarded.

## Bugs found in this suite while building it

- `add_dirs` resolves inside the case dir and cannot escape it; the agent is not told the
  path — fixtures are inlined in the prompt instead.
- JS regex has no inline flags (`(?i)` throws → silent grader failure); use `flags:`.
- An LLM grader with a self-contradictory criterion failed correct answers 3–0.
- A "trivially true" premise (`add(2,2)===4`) was wrong — it cannot tell `+` from `*`.
