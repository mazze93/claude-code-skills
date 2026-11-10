# Backwalk: CurriculumRL — "Matching GPT-4 Reasoning at 3B Parameters"

**Source:** *CurriculumRL: Matching Frontier Model Reasoning at 3B Parameters*, Anon et al., arXiv:2611.XXXXX (preprint, 2026-11-01).
**Reviewed:** 2026-11-07 · backwalk · adversarial read for a thesis-pivot decision.
**Tag:** `curriculumrl-gpt4`
**Compute envelope assumed for probes:** 1x A100 (80 GB) for ~1 week; otherwise an M4 Ultra (unified memory, MPS). Released model: `anon/CurriculumRL-3B`; released benchmark: `anon/StepBench-Hard`; released code: `anon/curriculum-rl`.

> **Note on reading register.** This is an adversarial read: a surface
> for probes, not a verdict. The paper's numbers may reproduce; the method
> may transfer. The point here is to isolate the things that would have
> to be true for the headline — "reasoning performance competitive with
> GPT-4" — to mean what a reader would casually take it to mean, and to
> size the cheapest empirical check for each one against your group's
> hardware. A thesis pivot that follows from *passed probes* is a
> different decision from a pivot that follows from the headline.

---

## 1. Claims as stated

| Claim | Scope / population | Effect size (reported) | Qualifier |
| --- | --- | --- | --- |
| CurriculumRL-3B matches GPT-4 reasoning | Qwen-3B-Instruct, fine-tuned on 50k SFT + 400k RL steps + 40k polish, evaluated on *StepBench-Hard* (2,500 items, GPT-4-generated, GPT-4-filtered) | **81.7 vs 84.3 pass@1** (GPT-4-judged); ~96% of the gap between the 34.6 base and GPT-4 closed | "competitive with"; implicitly "on multi-step logical reasoning" |
| Compute-efficient alternative to a 70B RL fine-tune | Same method | 1,200 H100-hours vs ~10,000+ est. | Comparison target is an estimate, not a run |
| Curriculum structure matters | Same method, ablation | 81.7 full -> 61.4 shuffled; 58.3 SFT-only | "on StepBench-Hard" |
| GPT-4-class reward model matters | Same, ablation | 81.7 -> 68.2 when GPT-4 reward model is replaced by Mixtral-8x7B | Same |
| Capability generalises but benchmark specificity remains | Qwen-3B-Instruct + CurriculumRL, GSM8K and MATH | 74.3 (vs base 68.1, GPT-4 92.0) and 28.6 (vs base 23.0, GPT-4 50.4) | Authors' own framing |

The headline compresses two things that pull apart on inspection: a
*StepBench-Hard* result (3-point gap to GPT-4) and a cross-benchmark
result (17.7 and 21.8 points behind GPT-4 on GSM8K and MATH). The
paper's own data already contains the counterfactual — see §3.A.

---

## 2. Trace to the evaluation harness

GPT-4 appears **eight distinct times** in the training-and-evaluation
pipeline:

| Stage | GPT-4's role |
| --- | --- |
| Phase 1 — SFT data | GPT-4 **generates** 50k multi-step problems |
| Phase 1 — SFT data | GPT-4 **verifies** each generated problem against its own reference solution |
| Phase 2 — curriculum | GPT-4 **assigns difficulty labels** (Tiers I-V) |
| Phase 2 — RL | GPT-4-class instance is the **reward model** scoring candidate solutions |
| Phase 3 — polish | Same reward signal, mixed-tier |
| StepBench-Hard construction | GPT-4 **generates** the 2,500 problems |
| StepBench-Hard filtering | Problems **retained only if a reference GPT-4 trace can solve them** ("manually reviewed for solvability by a reference GPT-4 trace") |
| StepBench-Hard scoring | GPT-4 Turbo is the **judge** that assigns correct / partial / incorrect |

The comparison target (84.3) is **GPT-4 judging GPT-4**. The student's
score (81.7) is **GPT-4 judging a model that was RL-trained to
produce outputs a GPT-4-class model scores highly, on problems GPT-4
wrote and GPT-4 confirmed it could solve.**

The two numbers on the headline row of the results table are not drawn
from independent measurement processes. They are two readings of the
same instrument, one of them on its own reflection.

Where the harness does touch ground truth: GSM8K (human-written word
problems, human-verified answers) and MATH (competition problems, exact
answer matching). On those, the gap to GPT-4 is 17.7 and 21.8 points.
The authors label this "benchmark specificity." It is also what the
*StepBench-Hard* measurement looks like when GPT-4 is removed from the
measuring apparatus.

---

## 3. What each claim rests on — load-bearing assumptions

### A. Distributional: training signal and evaluation signal share a single instrument (GPT-4)

The RL reward model and the StepBench-Hard judge are both GPT-4 (or
GPT-4-class, same lineage, same training data, same preferences).
Phase-1 SFT data is GPT-4 output; the method has been trained for
400,440 gradient-signal-bearing steps to produce completions a
GPT-4-class model rates "correct." It is then evaluated by a GPT-4
instance on a benchmark GPT-4 wrote.

What a reader takes from the headline — "a 3B model can reason like
GPT-4" — presumes the StepBench-Hard score is an estimate of some
reasoning construct that exists outside GPT-4's score distribution.
That presumption is what the probe set should put pressure on.

The paper's own evidence that the presumption is shaky is already on
the page:
- Ablation: GPT-4 -> Mixtral-8x7B as reward model drops 81.7 -> 68.2
  (a 13.5-point drop, on the *same* GPT-4-judged benchmark). GPT-4 in
  the training loop is worth ~13 points of the final score.
- Generalisation table: on GSM8K and MATH (no GPT-4 generation, no
  GPT-4 judge, exact-match or human verification), the gap widens from
  3 points to 17.7-21.8 points. This is a ~6-7x expansion in the
  reported gap as soon as the measurement leaves GPT-4's lineage.

**Counterfactual.** If matching GPT-4 on StepBench-Hard is primarily a
function of (method, GPT-4-as-judge) rather than (method, reasoning
construct), replacing the judge with an independent judge will move
81.7 by a magnitude on the order of the Detoxify/ToxiGen gap in
IF-Guide — enough to collapse the "competitive with GPT-4" framing to
"closes much of the gap to the base model on a benchmark GPT-4 likes."

### B. Definitional: "correct" is a GPT-4 classification, not an answer-key match

StepBench-Hard problems are released with "reference GPT-4 traces," not
with gold answer keys verified against a ground-truth source
(mathematical proof, formal verifier, human expert panel). The judge
prompt is told to compare candidate against the reference GPT-4 trace
and emit {correct, partial, incorrect}. There is no mechanism in the
protocol that corrects for cases where GPT-4's reference is itself
wrong, or where a candidate's correct answer disagrees with GPT-4's
reasoning but reaches the same endpoint.

The RL objective in Phase 2 is literally: produce outputs this
GPT-4-class instance will label "correct." The eval objective is:
produce outputs a GPT-4 Turbo instance will label "correct." These are
the same objective evaluated at two checkpoints of the same model
family. An 81.7 against an 84.3 under this definition is close to a
tautology about how well the RL signal transferred to the test
distribution, not a measurement of reasoning.

**Counterfactual.** If an outcome-based grader with no LLM in the loop
(numeric-answer extraction + exact match, or a symbolic/programmatic
verifier where problems admit one) is run on the same completions, the
3-point gap should either (i) hold within noise — in which case the
definitional concern is weaker than it looks — or (ii) invert or widen
substantially. The paper's own GSM8K/MATH numbers predict (ii).

### C. Operational: the comparison target is zero-shot default-API GPT-4; the student is RL-trained for the test distribution

GPT-4 was called "default GPT-4 Turbo configuration via the public API,
as of August 2026." No chain-of-thought prompt, no few-shot exemplars,
no self-consistency / majority-vote, no system prompt engineered for
step-by-step reasoning, no scratchpad. On GSM8K and MATH the literature
has consistently shown GPT-4 improves 10-15+ points with CoT and
majority-vote over its default-API zero-shot number; the 84.3 reported
here is almost certainly a floor, not a ceiling, for what GPT-4 can do
on StepBench-Hard.

CurriculumRL-3B, by contrast, was explicitly trained for 400k RL steps
on problems drawn from the same distribution as StepBench-Hard, with a
reward model that is a sibling of the judge. The comparison is an
RL-tuned student against an un-prompt-engineered teacher on the
student's training distribution.

**Counterfactual.** If GPT-4 with CoT + self-consistency (k=5-10)
reaches, say, 91-93 on StepBench-Hard, the 3-point gap in the
headline becomes an 8-12 point gap — large enough that the "competitive
with GPT-4" framing stops carrying the paper.

### D. Sampling: StepBench-Hard and Phase-1 SFT data come from the same generator with overlapping instructions

Phase-1 SFT data: "50k multi-step reasoning problems" from GPT-4 using
seed templates for "syllogistic reasoning, arithmetic chains,
constraint satisfaction, causal inference, combinatorial counting."
StepBench-Hard: 2,500 problems from GPT-4 with instructions to produce
problems "at least as hard as the hardest GSM8K items while requiring
at least 4 distinct reasoning steps."

Both are GPT-4 samples from an underlying "multi-step reasoning
problem" distribution GPT-4 has internalised. Nothing in the protocol
decontaminates SFT from StepBench-Hard — not an embedding-distance
filter, not a MinHash n-gram check, not a surface-form match. Given
50k x 2,500 pairings and the limited template space that GPT-4 draws
from under identical instructions, near-duplicates are an empirical
question, not a settled issue.

This is not a classic train-test leak claim. It's an "index-disjoint
but generator-overlapping" leak of the kind IF-Guide exhibited at the
record level: records that the method's selection stage saw, under a
different label, reappeared on the other side of the measurement. The
analogue here is "problem structures the student optimised against in
Phase 1 reappear in StepBench-Hard."

**Counterfactual.** If an embedding-nearest-neighbour or MinHash-overlap
audit finds that >10% of StepBench-Hard items have a near-duplicate in
the Phase-1 SFT set, the 81.7 number is partly a memorised-pattern
score. The *size* of the memorisation contribution is what the probe
measures.

### E. Comparison-target configuration: "GPT-4" is one API checkpoint, held still

The 84.3 reports GPT-4 Turbo "as of August 2026." Model versions behind
the public API drift (silent snapshots, moderation-layer changes,
system-message defaults). The judge calls — made at an unspecified
later date — may or may not be against the same underlying checkpoint
as the baseline calls. A model that scored 84.3 as baseline could be a
different model at judge time.

The paper does not pin the judge checkpoint or the reference-trace
checkpoint by snapshot ID. That omission makes the headline
non-reproducible in a strict sense: a reader running the released code
against the current GPT-4 API in 2027 is not guaranteed to measure what
the paper measured.

**Counterfactual.** If the judge-call API version is pinned and
re-scored (same completions, same prompts, newest GPT-4 Turbo snapshot),
and the numbers move by more than a point, the "within 3 points of
GPT-4" claim was dependent on a checkpoint that no longer exists.

---

## 4. Code vs. paper

The paper names `anon/curriculum-rl` on GitHub, `anon/CurriculumRL-3B`
and `anon/StepBench-Hard` on HuggingFace. A proper code audit is a
prerequisite to running any probe — specifically:

- The **judge prompt** (verbatim). A judge told "be lenient" or "give
  partial credit for correct intermediate steps" scores differently
  from one told the opposite. The paper reports {correct, partial,
  incorrect} and calls pass rate "the fraction classified correct" —
  but if "partial" is counted anywhere, the number changes.
- The **reward-model prompt and scoring aggregation** in Phase 2. "A
  GPT-4-class instance that scores candidate solutions for correctness
  against generated reference solutions" is underspecified: is the
  score a logprob, a rubric rating, a binary, an ELO? How are ties
  broken on the >70% tier-advance threshold?
- The **snapshot IDs** for every GPT-4 and GPT-4-Turbo call. If the
  code has these as string literals vs. environment variables vs.
  "whatever the API gave us," the reproducibility posture is already
  set.
- The **StepBench-Hard "manual review"** step. Who reviewed, how many
  items were cut, what was the inter-rater agreement, and is the
  pre-filter pool released?
- The **generator-seed / decoding settings** for StepBench-Hard
  problem generation (temperature, top-p, seed). If temperature was
  0 or low with a small seed set, the benchmark's effective diversity
  is below 2,500.
- The **tier boundaries**. "GPT-4-assigned difficulty labels" is a
  distribution; the paper does not say how a continuous label was
  turned into five tiers, and that choice interacts with the
  >70%-pass advancement rule.
- Whether the `anon/CurriculumRL-3B` weights on HuggingFace are the
  exact Phase-3 checkpoint from the reported run, or a re-run.

This section is deferred — the audit itself is Probe 0 below
(reproducibility, not a probe in the hypothesis-falsification sense).
Run it before Probes 1-6.

---

## 5. Probes

Ordered by (cutting power) / (cost), cheapest-and-most-cutting first.
The A100-week is spent sparingly; Probes 1-3 fit on the M4 Ultra and
preserve the A100 for any probe you choose to escalate.

### Probe 0 · Reproducibility floor (0.5-1 day, M4 Ultra)

Not a hypothesis probe — a prerequisite. Clone `anon/curriculum-rl`,
load `anon/CurriculumRL-3B`, re-run StepBench-Hard end-to-end using
the released judge prompt and the API snapshot the code pins. Record
whether the 81.7 reproduces to ±1 point.

If it does not reproduce, **stop**: Probes 1-6 are meaningless until
the baseline matches. If it does, continue.

Also record during this run: judge prompt verbatim, reward-model
prompt verbatim, API snapshot IDs, manual-review provenance. These
feed §4 and Probes 1, 5, 6.

**Compute.** Inference-only on a 3B model for 2,500 problems x ~1
completion each ≈ hours on M4 Ultra (paper's own 180 tok/s on consumer
GPU suggests ~2-4 hours of generation; judge API calls are serial on
rate limit, add ~1-3 hours). API cost on GPT-4 Turbo judge for 2,500
items: on the order of US$50-150 depending on completion length.

### Probe 1 · Judge triangulation (1-2 days, M4 Ultra + external API)

**Hypothesis.** The 81.7 vs 84.3 gap is a joint function of (model,
GPT-4-as-judge). If the *same* candidate completions and reference
solutions are re-scored by three judges outside GPT-4's lineage —
Claude Opus 4, Llama-3.1-70B-Instruct (via Together / Groq / Fireworks
API), and a programmatic grader where applicable — the CurriculumRL-3B
pass rate will drop by **at least 10 points more than GPT-4's own pass
rate drops**, and the inter-judge agreement between the three
alternative judges will be higher than between any one of them and
GPT-4.

**Protocol.**
1. From Probe 0, retain the 2,500 CurriculumRL-3B completions and the
   2,500 GPT-4 baseline completions. Retain the reference traces.
2. Build a judge prompt identical to the paper's (verbatim from code
   audit), parameterised over judge model.
3. Score all 2 x 2,500 = 5,000 completions with each of:
   - Claude Opus 4 (API)
   - Llama-3.1-70B-Instruct (external API; pin the snapshot)
   - A "programmatic grader" that runs on the subset of items with a
     uniquely extractable final answer (regex-extract final numeric or
     symbolic answer, exact match against the reference-trace answer).
     Mark the fraction of StepBench-Hard that admits this.
4. Also report inter-judge kappa / Krippendorff's alpha across the four
   judges (GPT-4 Turbo + three alternatives) on the pooled 5,000
   completions.
5. Metrics: pass@1 under each judge for each model; per-judge-pair
   agreement; the score-gap (CurriculumRL vs GPT-4 completions) under
   each judge.

**Falsification.**
- **Confirms the distributional/definitional concern.** If the mean
  across {Claude, Llama-70B, programmatic} of (GPT-4-completion-score
  - CurriculumRL-completion-score) is >= 10 points, *and* the GPT-4
  Turbo judge gap (3 points per the paper) is more than 3x smaller
  than the mean alternative-judge gap, the headline is substantially
  judge-dependent.
- **Falsifies.** If at least two of the three alternative judges give
  CurriculumRL-3B within ±3 points of GPT-4 (matching the headline),
  the claim is judge-robust, and §3.A/B are overstated.
- **Inconclusive.** One alternative judge agrees, two disagree, or the
  three alternatives disagree among themselves by >10 points. Report
  as "partial judge-dependence"; do not claim either way.

**Compute.** No local training. Inference for judging is API-bound.
Budget on the order of US$100-300 for Claude Opus 4 + Llama-70B API
calls across 5,000 completions, 1-2 wall-clock days end-to-end.
Programmatic grader is CPU-seconds. No A100 time used.

### Probe 2 · Cross-benchmark adversarial evaluation (2-4 days, M4 Ultra)

**Hypothesis.** The StepBench-Hard 81.7 does not generalise to
reasoning benchmarks GPT-4 did not generate or judge. On GSM8K (74.3
reported), MATH (28.6 reported), BIG-Bench Hard (BBH, not reported),
LogicQA, ARC-Challenge, and MMLU-STEM, the gap to GPT-4 will be >= 15
points on average, *and* on at least one of these the gap will be
larger than the base-model Qwen-3B-Instruct gap (i.e. the fine-tune
hurt, not helped).

**Protocol.**
1. Load `anon/CurriculumRL-3B` and base `Qwen-3B-Instruct` locally.
2. Run both, plus GPT-4 Turbo under default-API zero-shot (matching
   the paper's baseline posture), on: full GSM8K test, MATH test,
   BBH (23 tasks), LogicQA, ARC-Challenge, MMLU-STEM subset.
3. Use the standard task-specific graders released with each
   benchmark — exact-match where applicable, letter-match for MCQ.
   No LLM judge anywhere in this probe.
4. Report pass@1 for each model on each benchmark; report mean-gap
   (GPT-4 - CurriculumRL-3B) across benchmarks; report per-benchmark
   whether the fine-tune beat or lost to its own base model.

**Falsification.**
- **Confirms.** Mean cross-benchmark gap >= 15 points *and* >= 1
  benchmark shows CurriculumRL-3B below Qwen-3B-Instruct base -> the
  method is StepBench-Hard-specific; "general reasoning" framing
  fails.
- **Falsifies.** Mean gap <= 8 points and no benchmark regression ->
  the method generalises; §3.A's "distributional" story is weaker
  than the paper's own GSM8K/MATH numbers predicted.
- **Inconclusive.** 8-15 point mean gap, or mixed regression pattern.

**Compute.** Inference-only on a 3B model. M4 Ultra at ~180 tok/s
clears the suites in 2-4 days wall clock. GPT-4 API calls ≈ US$100-200.
No A100 time used.

### Probe 3 · Phase-1 <-> StepBench-Hard contamination audit (0.5-1 day, M4 Ultra or CPU)

**Hypothesis.** StepBench-Hard contains near-duplicates of Phase-1 SFT
problems at a rate >= 5%. "Near-duplicate" is defined by one of:
MinHash Jaccard >= 0.7 on normalised token shingles; or sentence-
embedding cosine >= 0.9 under a strong sentence encoder; or 7-gram
overlap >= 40% of the longer item.

**Protocol.**
1. If Phase-1's 50k SFT problems are released with the repo, load
   them. If not, regenerate them by re-running Phase-1 data generation
   with the released seeds (code audit required).
2. Compute sentence embeddings for all 50k + 2,500 problem statements
   (`all-mpnet-base-v2` or `bge-large-en-v1.5`, both released, both
   run on M4 Ultra in minutes).
3. For each StepBench-Hard item, find its nearest Phase-1 neighbour by
   cosine; report the distribution.
4. In parallel, MinHash on token 5-shingles; report Jaccard
   distribution and top-k pairs.
5. Spot-check the top 50 overlapping pairs by hand (reasonable in an
   afternoon).

**Falsification.**
- **Confirms.** >= 5% of StepBench-Hard items have a Phase-1 near-
  duplicate under any of the three similarity criteria -> the pass
  rate includes a memorisation component the paper does not account
  for; probe 1's judge-triangulation numbers and probe 2's cross-
  benchmark gaps become the honest signal.
- **Falsifies.** < 2% near-duplicate rate across all three criteria ->
  the GPT-4 generator is producing enough diversity that
  memorisation is a weak contributor.
- **Inconclusive.** 2-5% rate.

**Compute.** Embedding + MinHash + k-NN on ~52,500 short strings is
CPU-bound; M4 Ultra finishes in 1-2 hours. No A100 time used.

### Probe 4 · Fair-baseline GPT-4 reconfiguration (0.5-1 day, external API only)

**Hypothesis.** The 84.3 reported for GPT-4 is a default-API floor.
GPT-4 Turbo with chain-of-thought prompting, 3-shot in-context
exemplars, and self-consistency over k=5 samples will score >= 90.0 on
StepBench-Hard — opening the gap from 3 points to >= 8 points.

**Protocol.**
1. Lift StepBench-Hard problems and judge prompt from Probe 0.
2. Run GPT-4 Turbo (snapshot pinned by Probe 0) with:
   - a `Let's think step by step` system prompt and scratchpad output
   - 3-shot in-context exemplars drawn from a held-out GPT-4-generated
     set (to match the problem distribution; not from StepBench-Hard
     itself)
   - self-consistency: k=5 completions, majority-vote final-answer
     extraction
3. Score with the same judge prompt (GPT-4 Turbo as judge, per
   paper).
4. Also run GPT-4 with CoT alone (no SC) and with SC alone (no CoT)
   as ablations.
5. Metric: pass@1 (SC-aggregated) for each condition.

**Falsification.**
- **Confirms.** Any configuration reaches >= 90.0 -> the baseline was
  handicapped; "competitive with GPT-4" was framed against the wrong
  bar.
- **Falsifies.** Best configuration <= 86.0 -> GPT-4 is close to its
  ceiling on StepBench-Hard under this judge, and the 3-point gap is
  as tight as the paper suggests.
- **Inconclusive.** 86-90 range.

**Compute.** External API only. ~5 x 2,500 ≈ 12,500 generation calls +
judge calls. Budget on the order of US$300-600. No local hardware.

### Probe 5 · Reward-model substitution on Phase 3 only (5-7 days, 1x A100)

**Hypothesis.** The paper's own ablation (GPT-4 -> Mixtral-8x7B as
reward model, full retrain, 81.7 -> 68.2) understates how much of the
headline depends on GPT-4-as-reward because the ablation retrains
Phases 2+3 jointly; the dominant coupling is between reward model and
*final-polish distribution*. A bounded version — swap the reward model
in Phase 3 only, starting from a saved Phase-2 checkpoint — will drop
by >= 5 points if the coupling is diffuse, and by >= 10 points if the
coupling is concentrated in polish.

**Protocol.**
1. Request or reconstruct the Phase-2 end-of-training checkpoint from
   the authors (or train Phase 2 to convergence — not feasible in a
   week on 1 A100).
2. Re-run Phase 3 (40k steps) twice:
   - Baseline: GPT-4-class reward model (paper's setup).
   - Treatment: Claude Opus 4 as reward model (lineage-independent).
3. Score both resulting checkpoints with Probe 0's protocol.
4. Metric: delta pass@1 between the two Phase-3 variants, and both minus
   81.7.

**Falsification.**
- **Confirms strong Phase-3 coupling.** Treatment drops >= 10 points.
- **Confirms diffuse coupling.** Treatment drops 5-10 points (then
  the full-retrain ablation's 13.5-point drop is mostly earlier).
- **Falsifies.** Treatment within 3 points of baseline -> GPT-4 in
  Phase 3 specifically is not load-bearing.

**Compute.** 80 H100-hours (paper's Phase-3 figure) x 2 runs x ~2x for
A100 vs H100 ≈ 320 A100-hours ≈ 13.3 days. **Does not fit the
A100-week budget** for both runs. Drop to one run (treatment only,
compare against the released checkpoint for baseline): 6-7 days of
A100 time, feasible. Depends entirely on getting the Phase-2 end
checkpoint from the authors; if not released, probe is blocked on
request.

### Probe 6 · Programmatic verifier on the answer-extractable subset (1-2 days, M4 Ultra + CPU)

**Hypothesis.** On the subset of StepBench-Hard problems whose final
answer is a single extractable value (number, closed-form, list), a
non-LLM grader will show the CurriculumRL-3B vs GPT-4 gap is >= 8
points — materially larger than the LLM-judge gap of 3.

**Protocol.**
1. Classify the 2,500 StepBench-Hard items into "answer-extractable"
   (final answer is a number, a yes/no, a specific entity, or a
   list) vs "free-form reasoning" by rule + a short manual pass.
   Report the split.
2. For the extractable subset: extract the final answer from each
   candidate completion by regex / structured parsing from the
   reference trace. Compare against the reference answer by exact
   match (for numbers: normalised to a canonical form).
3. Report pass@1 on the extractable subset for CurriculumRL-3B and
   GPT-4 — no LLM anywhere in the grading path.
4. Separately, on the free-form subset, re-score with Probe 1's
   alternative-judge ensemble.

**Falsification.**
- **Confirms.** Programmatic gap on extractable >= 8 points.
- **Falsifies.** Programmatic gap on extractable <= 4 points (close to
  the LLM-judge gap).
- **Inconclusive.** 4-8 points.

**Compute.** Pure parsing + exact-match. CPU-seconds. Human labelling
for the extractable/free-form split is ~1 day. No A100 time.

---

## 6. Probe ordering

| Rank | Probe | Cutting power | Cost | First-run priority |
| --- | --- | --- | --- | --- |
| 0 | Reproducibility floor | Gate | Low (hours, M4 Ultra + ~US$100) | Required before any other probe |
| 1 | Judge triangulation | **Very high** — collapses the headline if the gap widens under independent judges | Low (M4 Ultra + ~US$200 API) | Yes |
| 2 | Cross-benchmark adversarial eval | Very high — the paper's own GSM8K/MATH data already predicts this will bite | Low-medium (2-4 days M4 Ultra + ~US$150 API) | Yes, in parallel with Probe 1 |
| 3 | Phase-1 <-> StepBench-Hard contamination audit | Medium-high — a positive result reframes probe 1/2 outputs | Very low (hours, M4 Ultra) | Yes, run alongside Probe 1 — it's essentially free |
| 4 | Fair-baseline GPT-4 reconfiguration | Medium-high — changes the *bar* the claim is measured against | Low (external API only, ~US$500) | After 1-3 |
| 5 | Programmatic verifier on extractable subset | Medium — independent *grader*, not just independent *judge* | Very low (CPU + 1 day human) | Yes, run alongside Probe 1 |
| 6 | Phase-3 reward-model substitution | High — but mostly a mechanism confirmation of what Probe 1 will already reveal | **High** (6-7 days of your A100 week, blocked on Phase-2 checkpoint) | Only if Probes 1-2 give an ambiguous picture and you still want to commit the A100 week |

**One-sentence rationale.** Probes 1, 2, 3, and 5 together cost well
under your A100 week in wall-clock time, use **zero** of your A100
hours, and jointly put pressure on every load-bearing assumption in
§3.A/B/D. If after running them the picture is still ambiguous, Probe
6 is where the A100 earns its keep. If the picture is already clear,
save the week.

---

## 7. Relevance to the thesis pivot

Your student is deciding whether to build a thesis on top of this
paper. The question "is the headline real" and the question "should
they pivot" are not the same question — a tight headline that
generalises would support a pivot; a leaky headline whose generalisation
is already contradicted by the paper's own GSM8K/MATH numbers would
not. The probe set above is what makes either answer defensible, in
writing, to a committee.

Three framings that come out of the backwalk, usable in your next
conversation with the student:

1. **The paper's own data already contains most of the counterfactual.**
   On benchmarks GPT-4 didn't make or judge (GSM8K, MATH), the gap to
   GPT-4 widens by ~6x relative to the headline. A thesis-committee
   member will ask about this; the student should have a view before
   it comes up.

2. **The `anon/CurriculumRL-3B` weights plus `anon/StepBench-Hard` are
   released.** That is a real gift: Probes 0, 1, 2, 3, 5 are
   inference-only on released artefacts. Your group can confirm
   (or falsify) the headline on your M4 Ultra in **one week of
   wall-clock time, with zero A100 hours spent and ~US$1k of API
   budget**. A pivot made after that evidence exists is a different
   artefact than a pivot made from the preprint.

3. **The pivot's value depends on what you're pivoting *to*.** If the
   thesis would build on the *method* (curriculum RL as a technique
   for small-model reasoning), Probes 1-2 are load-bearing: a
   judge-dependent 81.7 that collapses to 68 under independent
   grading means the method is a StepBench-Hard trick. If the thesis
   would build on *the artefact* (using CurriculumRL-3B as a
   released model for downstream task X), Probe 2 is load-bearing:
   whether the model actually reasons well on tasks outside the
   training distribution is the only question that matters. If the
   thesis is *on evaluation methodology* (circular LLM-as-judge
   pipelines), the paper is itself a useful specimen — probes 1, 3,
   5 produce the evidence and the thesis writes itself.

The decision is not here. The probes above are.

---

## 8. What this is not

- Not a verdict on CurriculumRL. The method's numbers may reproduce;
  the curriculum structure may transfer; the fine-tune may be useful.
  None of §3 says it isn't.
- Not a review of the paper. A review would also engage the compute
  comparison, the ablation design, the base-model choice. The scope
  here is the central claim.
- Not a critique of the authors. The Limitations section explicitly
  names the GPT-4 circularity. The backwalk is an extension of that
  acknowledgement, not an accusation.
- Not a verdict on the pivot. The user asked explicitly for a probe
  surface, not a recommendation. The probe outcomes are what should
  decide the pivot.
- Not a reproduction (yet). Probe 0 is the reproduction. Only after it
  passes does the rest of this artefact mean anything.

---

## 9. Key references to follow

1. **Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and
   Chatbot Arena* (NeurIPS 2023).** The canonical paper on LLM-judge
   bias. Required reading before running Probe 1; frames which biases
   (position, verbosity, self-preference) to anticipate.
2. **Hendrycks et al., *Measuring Massive Multitask Language
   Understanding* (ICLR 2021) and the MATH paper (NeurIPS 2021).**
   Baseline for what independent-benchmark gap sizes look like when
   the frontier gap is real; feeds Probe 2's ">= 15 points" threshold.
3. **Wei et al., *Chain-of-Thought Prompting Elicits Reasoning in
   Large Language Models* (NeurIPS 2022) and Wang et al., *Self-
   Consistency Improves Chain of Thought Reasoning* (ICLR 2023).**
   Direct inputs to Probe 4's protocol; set the magnitude of the
   "GPT-4 default-API floor vs ceiling" delta to expect.
4. **Carlini et al., *Quantifying Memorization Across Neural Language
   Models* (ICLR 2023) and the data-contamination literature from
   Oren et al. / Golchin & Surdeanu (2024).** MinHash and
   embedding-overlap methodology for Probe 3, plus the framing that
   "generator-overlapping but index-disjoint" leaks are a real class.
5. **Shumailov et al., *The Curse of Recursion: Training on Generated
   Data Makes Models Forget* (Nature 2024).** The deeper structural
   reason the student should also care about this paper's pipeline:
   training on GPT-4-generated data while being judged by GPT-4 is a
   specific case of a well-studied distributional trap.

---

**Session note.** Preprint read from
`/home/user/skills-work/backwalk/evals/paper-matches-gpt4-claim/files/preprint_excerpt.md`.
This backwalk lives at
`/home/user/skills-work/backwalk-workspace/iteration-1/paper-matches-gpt4-claim/with_skill/outputs/analysis.md`.
A natural follow-up is to run Probe 0 against `anon/curriculum-rl`
and `anon/CurriculumRL-3B` on the M4 Ultra and report the
reproduced numbers back into §4 (Code vs. paper) before committing
any A100 hours.
